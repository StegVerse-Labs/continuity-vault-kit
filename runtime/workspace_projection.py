from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

WORKSPACE_REL=Path("_System/Workspace")
SCHEMAS={
    "workspace.json":"stegverse.kv.workspace-context/v1",
    "principals.json":"stegverse.kv.workspace-principals/v1",
    "relationships.json":"stegverse.kv.workspace-relationships/v1",
    "organizations.json":"stegverse.kv.workspace-organizations/v1",
    "memberships.json":"stegverse.kv.workspace-memberships/v1",
    "feed.json":"stegverse.kv.workspace-feed/v1",
    "assistant.json":"stegverse.kv.workspace-assistant/v1",
}
FORBIDDEN=("password","secret","token","credential","private_key","seed","mnemonic","recovery_code")
PRINCIPAL_TYPES={"HUMAN","AI_ENTITY","ORGANIZATION","SERVICE"}
METADATA_SCHEMA="stegverse.kv.workspace-projection-metadata/v1"

class WorkspaceProjectionError(ValueError): pass

def _require(ok:bool, reason:str)->None:
    if not ok: raise WorkspaceProjectionError(reason)

def _root(kv_data_root:Path)->Path:
    root=kv_data_root.expanduser().resolve()
    _require(root.name=="KnowledgeVault" or (root/"_System").exists(),"kv_data_root_not_knowledgevault")
    return root

def _reject_secrets(value:Any,path:str="root")->None:
    if isinstance(value,list):
        for i,item in enumerate(value): _reject_secrets(item,f"{path}[{i}]")
    elif isinstance(value,dict):
        for key,item in value.items():
            low=str(key).lower()
            _require(not any(word in low for word in FORBIDDEN),"secret_field_forbidden:"+path+"."+str(key))
            _reject_secrets(item,path+"."+str(key))

def _read_optional(root:Path,name:str)->dict[str,Any]|None:
    path=(root/WORKSPACE_REL/name).resolve()
    _require(root in path.parents,"workspace_path_escape")
    if not path.is_file(): return None
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: raise WorkspaceProjectionError("workspace_file_unreadable:"+name) from exc
    _require(isinstance(value,dict),"workspace_file_object_required:"+name)
    _require(value.get("schema")==SCHEMAS[name],"workspace_file_schema_invalid:"+name)
    _require(value.get("authority_effect")=="NONE","workspace_file_authority_invalid:"+name)
    _reject_secrets(value,name)
    return value

def _rows(value:dict[str,Any]|None,key:str)->list[dict[str,Any]]:
    if value is None: return []
    rows=value.get(key,[])
    _require(isinstance(rows,list),"workspace_rows_invalid:"+key)
    _require(all(isinstance(row,dict) for row in rows),"workspace_row_object_required:"+key)
    return [dict(row) for row in rows]

def _principal(row:dict[str,Any])->dict[str,Any]:
    _require(isinstance(row.get("principal_id"),str) and row["principal_id"],"principal_id_required")
    _require(row.get("principal_type") in PRINCIPAL_TYPES,"principal_type_invalid")
    _require(isinstance(row.get("display_name"),str) and row["display_name"],"principal_display_name_required")
    result=dict(row)
    result["ai_label_required"]=row["principal_type"]=="AI_ENTITY"
    result["authority_effect"]="NONE"
    return result

def _utc_now()->datetime: return datetime.now(timezone.utc)

def _source_revision(sources:dict[str,dict[str,Any]|None])->str:
    # Digest of the exact validated source records the rows were projected from; absent files are bound as null.
    canonical=json.dumps({name:sources.get(name) for name in sorted(SCHEMAS)},sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _context_ref(context:dict[str,Any]|None,key:str)->str|None:
    value=(context or {}).get(key)
    return value if isinstance(value,str) and value else None

def _projection_metadata(sources:dict[str,dict[str,Any]|None],context:dict[str,Any]|None,clock:Callable[[],datetime])->dict[str,Any]:
    produced=clock()
    _require(isinstance(produced,datetime) and produced.tzinfo is not None,"projection_clock_must_be_timezone_aware")
    revision=_source_revision(sources)
    return {
        "schema":METADATA_SCHEMA,
        # observed_at is when this producer read and projected the KV sources, never a source-event time.
        "observed_at":produced.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "observed_at_semantics":"KV_PROJECTION_PRODUCTION_TIME",
        "source_revision":revision,
        "provenance_ref":"kv-workspace-source:sha256:"+revision,
        "workspace_type":"PERSONAL",
        "workspace_id":_context_ref(context,"workspace_id"),
        "owner_principal_id":_context_ref(context,"owner_principal_id"),
        # No verified grant or revocation-epoch source exists in Personal KV Workspace records; never assert ACTIVE.
        "grant_state":"UNKNOWN",
        "revocation_epoch":None,
        "authority_effect":"NONE",
    }

def get_personal_workspace_projection(*,kv_data_root:Path,clock:Callable[[],datetime]=_utc_now)->dict[str,Any]:
    root=_root(kv_data_root)
    sources={name:_read_optional(root,name) for name in SCHEMAS}
    metadata=_projection_metadata(sources,sources["workspace.json"],clock)
    context=sources["workspace.json"]
    principals=[_principal(row) for row in _rows(sources["principals.json"],"principals")]
    relationships=_rows(sources["relationships.json"],"relationships")
    organizations=[_principal(row) for row in _rows(sources["organizations.json"],"organizations")]
    for org in organizations: _require(org["principal_type"]=="ORGANIZATION","organization_principal_type_invalid")
    memberships=_rows(sources["memberships.json"],"memberships")
    feed=_rows(sources["feed.json"],"events")
    assistant_file=sources["assistant.json"]
    assistant=None
    if assistant_file is not None:
        assistant=_principal(assistant_file.get("assistant") or {})
        _require(assistant["principal_type"]=="AI_ENTITY","workspace_assistant_must_be_ai")
        roles=assistant.get("roles") or []
        _require(isinstance(roles,list) and "WORKSPACE_ASSISTANT" in roles,"workspace_assistant_role_required")
    known={row["principal_id"]:row for row in principals+organizations}
    if assistant is not None: known[assistant["principal_id"]]=assistant
    for rel in relationships:
        _require(rel.get("subject_principal_id") in known and rel.get("object_principal_id") in known,"relationship_principal_unknown")
        _require(isinstance(rel.get("relationship"),str) and rel["relationship"],"relationship_kind_required")
        rel["authority_effect"]="NONE"
    for membership in memberships:
        _require(isinstance(membership.get("organization_id"),str) and membership["organization_id"],"membership_organization_required")
        _require(isinstance(membership.get("member_principal_id"),str) and membership["member_principal_id"],"membership_principal_required")
        _require(membership.get("status") in {"ACTIVE","PENDING","SUSPENDED","REVOKED"},"membership_status_invalid")
        membership["authority_effect"]="NONE"
    for event in feed:
        _require(event.get("actor_id") in known,"feed_actor_unknown")
        _require(event.get("visibility") in {"PRIVATE","FRIENDS","KNOWN_USERS","ORGANIZATION_MEMBERS","SPECIFIC_USERS","SPECIFIC_ORGANIZATIONS","ECOSYSTEM","PUBLIC"},"feed_visibility_invalid")
        event["actor_type"]=known[event["actor_id"]]["principal_type"]
        event["ai_label_required"]=event["actor_type"]=="AI_ENTITY"
        event["authority_effect"]="NONE_OBSERVATION_ONLY"
    return {
        "schema":"stegverse.kv.personal-workspace-projection/v1",
        "state":"KV_WORKSPACE_PROJECTED" if any((context,principals,relationships,organizations,memberships,feed,assistant)) else "KV_WORKSPACE_EMPTY",
        "workspace_type":"PERSONAL",
        "workspace":context,
        "principals":principals,
        "relationships":relationships,
        "organizations":organizations,
        "memberships":memberships,
        "feed":feed,
        "assistant":assistant,
        "credential_material_present":False,
        "provider_operation_authorized":False,
        "workspace_grants_authority":False,
        "projection_metadata":metadata,
        "authority_effect":"NONE",
    }
