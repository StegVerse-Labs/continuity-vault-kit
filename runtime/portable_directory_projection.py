from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ALLOWED_ROOTS={"00_Inbox","02_Research","03_Records","04_Media","05_Projects","06_Archive","_Entities"}
ADMISSION_SCHEMA="stegverse.kv.portable-direct-source-canonical-admission/v1"
PROVENANCE_SCHEMA="stegverse.kv.portable-direct-source-provenance/v1"
HEALTH_SCHEMA="stegverse.kv.portable-direct-source-connection-health/v1"

INSTALLATION_STATUS_SCHEMA="stegverse.kv.installation-status-projection/v1"
INSTALLATION_RECEIPT_REL=Path("_System/installation.receipt.json")

def _sha256_file(path:Path)->str:
    import hashlib
    h=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(65536),b""):
            h.update(chunk)
    return "sha256:"+h.hexdigest()

def _validate_installation_receipt(receipt:dict[str,Any])->dict[str,Any]:
    _require(receipt.get("schema_version")=="1.1","installation_receipt_schema_invalid")
    source=receipt.get("source")
    _require(isinstance(source,str) and "continuity-vault-kit:vault_template/KnowledgeVault" in source,"installation_receipt_source_invalid")
    tree=receipt.get("current_verified_source_tree_sha")
    _require(isinstance(tree,str) and len(tree)==40 and all(ch in "0123456789abcdefABCDEF" for ch in tree),"installation_receipt_tree_sha_invalid")
    destination=receipt.get("destination")
    _require(isinstance(destination,str) and destination.endswith("/KnowledgeVault"),"installation_receipt_destination_invalid")
    verification=receipt.get("verification")
    _require(isinstance(verification,dict),"installation_receipt_verification_missing")
    _require(verification.get("full_recursive_source_path_presence") is True,"installation_receipt_recursive_presence_invalid")
    _require(verification.get("source_defined_directories_present") is True,"installation_receipt_directory_presence_invalid")
    _require(verification.get("source_defined_files_present") is True,"installation_receipt_file_presence_invalid")
    _require(verification.get("full_template_parity")=="VALIDATED","installation_receipt_template_parity_invalid")
    _require(receipt.get("authority_effect")=="NONE","installation_receipt_authority_effect_invalid")
    _require(receipt.get("activation_effect") is False,"installation_receipt_activation_effect_invalid")
    census=receipt.get("source_census")
    _require(isinstance(census,dict),"installation_receipt_source_census_missing")
    _require(isinstance(census.get("files"),int) and census["files"]>0,"installation_receipt_file_census_invalid")
    _require(isinstance(census.get("directories"),int) and census["directories"]>0,"installation_receipt_directory_census_invalid")
    return receipt

def get_installation_status(*,kv_data_root:Path)->dict[str,Any]:
    root=_safe_root(kv_data_root)
    receipt_path=(root/INSTALLATION_RECEIPT_REL).resolve()
    _require(root in receipt_path.parents,"installation_receipt_path_escape")
    if not receipt_path.is_file():
        return {
            "schema":INSTALLATION_STATUS_SCHEMA,
            "state":"KV_INSTALLATION_NOT_VERIFIED",
            "resident_kv_root_observed":True,
            "installation_receipt_present":False,
            "source_tree_sha":None,
            "receipt_sha256":None,
            "receipt_verified_utc":None,
            "full_template_parity":None,
            "source_census":None,
            "destination_kind":None,
            "current_cloud_provider_observation":False,
            "credential_material_present":False,
            "provider_operation_authorized":False,
            "authority_effect":"NONE",
        }
    receipt=_validate_installation_receipt(_read_json(receipt_path,"installation_receipt_unreadable"))
    destination=str(receipt.get("destination") or "")
    destination_kind=destination.split(":",1)[0] if ":" in destination else "OWNER_CONTROLLED_STORAGE"
    return {
        "schema":INSTALLATION_STATUS_SCHEMA,
        "state":"KV_INSTALLATION_VERIFIED",
        "resident_kv_root_observed":True,
        "installation_receipt_present":True,
        "source_tree_sha":receipt["current_verified_source_tree_sha"],
        "receipt_sha256":_sha256_file(receipt_path),
        "receipt_verified_utc":receipt.get("verified_utc"),
        "full_template_parity":"VALIDATED",
        "source_census":{
            "files":receipt["source_census"]["files"],
            "directories":receipt["source_census"]["directories"],
        },
        "destination_kind":destination_kind,
        "current_cloud_provider_observation":False,
        "credential_material_present":False,
        "provider_operation_authorized":False,
        "authority_effect":"NONE",
    }


class PortableDirectoryProjectionError(ValueError):
    pass

def _require(ok:bool,reason:str)->None:
    if not ok:
        raise PortableDirectoryProjectionError(reason)

def _safe_root(kv_data_root:Path)->Path:
    root=kv_data_root.expanduser().resolve()
    _require(root.name=="KnowledgeVault" or (root/"_System").exists() or (root/"00_Inbox").exists(),"kv_data_root_not_knowledgevault")
    return root

def _safe_canonical_path(root:Path,canonical_path:str)->Path:
    _require(isinstance(canonical_path,str) and canonical_path,"canonical_path_required")
    _require(not canonical_path.startswith("/") and "\" not in canonical_path,"canonical_path_invalid")
    parts=canonical_path.split("/")
    _require(all(part not in {"",".",".."} for part in parts),"canonical_path_traversal_forbidden")
    _require(parts[0] in ALLOWED_ROOTS,"canonical_path_root_not_admitted")
    candidate=(root/canonical_path).resolve()
    _require(root in candidate.parents or candidate==root,"canonical_path_escape_forbidden")
    return candidate

def _read_json(path:Path,reason:str)->dict[str,Any]:
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PortableDirectoryProjectionError(reason) from exc
    _require(isinstance(value,dict),reason)
    return value

def _validated_batch(root:Path,batch:Path,canonical_path:str)->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    admission=_read_json(batch/"admission-receipt.json","admission_receipt_unreadable")
    provenance=_read_json(batch/"provenance.json","provenance_unreadable")
    health=_read_json(batch/"connection-health.json","connection_health_unreadable")
    expected_admission={
        "schema":ADMISSION_SCHEMA,
        "state":"CANONICAL_ADMITTED",
        "requested_canonical_path":canonical_path,
        "canonical_batch_path":str(batch.relative_to(root)),
        "canonical_kv_persistence_observed":True,
        "exact_canonical_readback_verified":True,
        "trusted_semantic_admission":True,
        "provider_session_required":False,
        "provider_session_observed":False,
        "credential_material_present":False,
        "provider_operation_authorized":False,
        "credential_authority":"TV/TVC",
        "github_token_runtime_authority":"NONE",
        "authority_effect":"NONE",
    }
    for key,value in expected_admission.items():
        _require(admission.get(key)==value,"admission_receipt_binding_mismatch:"+key)
    _require(provenance.get("schema")==PROVENANCE_SCHEMA,"provenance_schema_mismatch")
    for key in ("materialization_id","request_hash","payload_hash","staging_receipt_sha256","ingress_receipt_sha256"):
        _require(provenance.get(key)==admission.get(key),"provenance_binding_mismatch:"+key)
    _require(provenance.get("canonical_batch_path")==str(batch.relative_to(root)),"provenance_canonical_batch_path_mismatch")
    _require(provenance.get("credential_material_present") is False,"provenance_credential_material_forbidden")
    _require(provenance.get("provider_operation_authorized") is False,"provenance_provider_operation_forbidden")
    _require(provenance.get("authority_effect")=="NONE","provenance_authority_effect_invalid")
    _require(health.get("schema")==HEALTH_SCHEMA,"connection_health_schema_mismatch")
    _require(health.get("canonical_path")==canonical_path,"connection_health_path_mismatch")
    _require(health.get("compatibility_state")=="VERIFIED","connection_health_not_verified")
    _require(health.get("credential_material_present") is False,"connection_health_credential_material_forbidden")
    _require(health.get("provider_operation_authorized") is False,"connection_health_provider_operation_forbidden")
    _require(health.get("authority_effect")=="NONE","connection_health_authority_effect_invalid")
    return admission,provenance,health

def list_admitted_directory(*,kv_data_root:Path,directory_id:str,canonical_path:str)->dict[str,Any]:
    root=_safe_root(kv_data_root)
    directory=_safe_canonical_path(root,canonical_path)
    _require(isinstance(directory_id,str) and directory_id,"directory_id_required")
    entries:list[dict[str,Any]]=[]
    health_rows:list[dict[str,Any]]=[]
    if directory.exists():
        _require(directory.is_dir(),"canonical_path_not_directory")
        for batch in sorted((p for p in directory.iterdir() if p.is_dir()),key=lambda p:p.name):
            if not (batch/"admission-receipt.json").is_file():
                continue
            admission,provenance,health=_validated_batch(root,batch,canonical_path)
            _require(admission.get("directory_id")==directory_id,"directory_id_binding_mismatch")
            files=provenance.get("files")
            _require(isinstance(files,list),"provenance_files_invalid")
            for item in files:
                _require(isinstance(item,Mapping),"provenance_file_entry_invalid")
                ref=item.get("canonical_ref")
                _require(isinstance(ref,str) and ref,"canonical_ref_required")
                target=(root/ref).resolve()
                _require(root in target.parents and target.is_file(),"canonical_ref_invalid")
                _require(str(target.relative_to(root)).startswith(str(batch.relative_to(root))+"/files/"),"canonical_ref_batch_escape")
                entries.append({
                    "name":item.get("name"),
                    "kind":"file",
                    "media_type":item.get("media_type"),
                    "size_bytes":item.get("size_bytes"),
                    "sha256":item.get("sha256"),
                    "materialization_id":admission.get("materialization_id"),
                    "canonical_ref":ref,
                    "modified_at":admission.get("observed_at"),
                    "authority_effect":"NONE",
                })
            health_rows.append(health)
    latest_health=max(health_rows,key=lambda row:str(row.get("last_observed_at") or "")) if health_rows else None
    return {
        "schema":"stegverse.kv.portable-directory-projection/v1",
        "state":"KV_LISTED",
        "directory_id":directory_id,
        "canonical_path":canonical_path,
        "entries":entries,
        "connection_health":latest_health,
        "credential_material_present":False,
        "provider_operation_authorized":False,
        "authority_effect":"NONE",
    }

def get_directory_health(*,kv_data_root:Path,directory_id:str,canonical_path:str)->dict[str,Any]:
    listing=list_admitted_directory(kv_data_root=kv_data_root,directory_id=directory_id,canonical_path=canonical_path)
    health=listing["connection_health"]
    if health is None:
        return {
            "schema":"stegverse.kv.portable-direct-source-connection-health/v1",
            "directory_id":directory_id,
            "canonical_path":canonical_path,
            "compatibility_state":"UNASSEMBLED",
            "last_observed_at":None,
            "reason":"NO_CANONICAL_OWNER_CONTROLLED_ADMISSION",
            "revalidation_required":False,
            "connection_proof_ref":None,
            "readback_proof_ref":None,
            "credential_material_present":False,
            "provider_operation_authorized":False,
            "authority_effect":"NONE",
        }
    return dict(health)
