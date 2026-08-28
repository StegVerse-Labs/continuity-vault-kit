"""Private-KV connection registry persistence helpers.

These helpers operate on local/private filesystem paths supplied by an admitted runtime.
They do not perform provider login, credential resolution, network access, or provider mutation.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

from runtime.connection_assembly import ConnectionAssemblyError, assemble_connection, reject_secret_fields

REGISTRY_SCHEMA="stegverse.kv.connection-assembly-registry/v1"
SOURCE_CHANGE_SCHEMA="stegverse.kv.source-change-observation/v1"
HEALTH_SCHEMA="stegverse.kv.connection-health-receipt/v1"

class ConnectionRegistryStoreError(ConnectionAssemblyError):
    pass

def canonical_paths(kv_root: Path) -> dict[str,Path]:
    root=kv_root.expanduser().resolve()
    base=root/"_System"/"Connections"
    return {
        "root":base,
        "registry":base/"Connection_Assemblies.json",
        "source_changes":base/"Source_Changes",
        "health":base/"Health",
    }

def initialize_store(kv_root: Path) -> dict[str,Path]:
    paths=canonical_paths(kv_root)
    paths["root"].mkdir(parents=True,exist_ok=True)
    paths["source_changes"].mkdir(parents=True,exist_ok=True)
    paths["health"].mkdir(parents=True,exist_ok=True)
    if not paths["registry"].exists():
        paths["registry"].write_text(json.dumps({
            "schema":REGISTRY_SCHEMA,"state":"EMPTY","authority_effect":"NONE","assemblies":[]
        },sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return paths

def load_registry(kv_root: Path) -> Dict[str,Any]:
    paths=initialize_store(kv_root)
    try:
        value=json.loads(paths["registry"].read_text(encoding="utf-8"))
    except Exception as exc:
        raise ConnectionRegistryStoreError("connection registry is unreadable") from exc
    reject_secret_fields(value,"$.connection_registry")
    if value.get("schema")!=REGISTRY_SCHEMA: raise ConnectionRegistryStoreError("unexpected registry schema")
    if value.get("authority_effect")!="NONE": raise ConnectionRegistryStoreError("registry authority effect must remain NONE")
    assemblies=value.get("assemblies")
    if not isinstance(assemblies,list): raise ConnectionRegistryStoreError("assemblies must be a list")
    return value

def _registry_state(assemblies:list[dict[str,Any]])->str:
    if not assemblies: return "EMPTY"
    states={a.get("compatibility_state") for a in assemblies}
    if states=={"VERIFIED"}: return "VERIFIED"
    if "DEGRADED" in states or "BLOCKED_SOURCE_CHANGE" in states or "BLOCKED_SESSION" in states or "BLOCKED_RUNTIME" in states:
        return "DEGRADED"
    if "VERIFIED" in states: return "PARTIALLY_VERIFIED"
    return "ASSEMBLED_UNVERIFIED"

def upsert_assembly(kv_root:Path,assembly:Dict[str,Any])->Dict[str,Any]:
    normalized=assemble_connection(assembly)
    registry=load_registry(kv_root)
    rows=[row for row in registry["assemblies"] if row.get("assembly_id")!=normalized["assembly_id"]]
    rows.append(normalized)
    rows=sorted(rows,key=lambda row:row["assembly_id"])
    registry["assemblies"]=rows
    registry["state"]=_registry_state(rows)
    registry["authority_effect"]="NONE"
    reject_secret_fields(registry,"$.connection_registry")
    canonical_paths(kv_root)["registry"].write_text(json.dumps(registry,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return copy.deepcopy(registry)

def persist_source_change(kv_root:Path,observation:Dict[str,Any])->Path:
    reject_secret_fields(observation,"$.source_change")
    if observation.get("schema")!=SOURCE_CHANGE_SCHEMA: raise ConnectionRegistryStoreError("unexpected source change schema")
    if observation.get("authority_effect")!="NONE": raise ConnectionRegistryStoreError("source change authority effect must remain NONE")
    observation_id=str(observation.get("observation_id") or "")
    if not observation_id.startswith("kvchg_"): raise ConnectionRegistryStoreError("source change observation_id invalid")
    path=initialize_store(kv_root)["source_changes"]/f"{observation_id}.json"
    path.write_text(json.dumps(observation,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return path

def persist_health_receipt(kv_root:Path,receipt:Dict[str,Any])->Path:
    reject_secret_fields(receipt,"$.connection_health")
    if receipt.get("schema")!=HEALTH_SCHEMA: raise ConnectionRegistryStoreError("unexpected health receipt schema")
    if receipt.get("authority_effect")!="NONE": raise ConnectionRegistryStoreError("health authority effect must remain NONE")
    if receipt.get("provider_operation_authorized") is not False: raise ConnectionRegistryStoreError("provider operation authority prohibited")
    if receipt.get("credential_material_present") is not False: raise ConnectionRegistryStoreError("credential material prohibited")
    assembly_id=str(receipt.get("assembly_id") or "")
    observed_at=str(receipt.get("observed_at") or "").replace(":","-")
    if not assembly_id.startswith("kvcxn_") or not observed_at: raise ConnectionRegistryStoreError("health receipt identity invalid")
    path=initialize_store(kv_root)["health"]/f"{assembly_id}__{observed_at}.json"
    path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return path
