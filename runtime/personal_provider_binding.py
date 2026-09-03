"""Provider-neutral Personal KnowledgeVault binding and secret-free TVC broker materialization.

Credential-bearing Google Drive processing occurs only inside the TV/TVC-owned
non-exportable provider broker. This module accepts no bearer token, refresh
token, provider credential file, or Authorization header.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

BINDING_SCHEMA="stegverse.kv.personal-provider-binding/v1"
BROKER_RESULT_SCHEMA="stegverse.tvc.google-drive-personal-kv-materialization/v1"
ALLOWED_SCOPES={
    "_System/installation.receipt.json",
    "_System/Workspace/**",
    "_Entities/Self/Personal_Contact_Profile.json",
    "_Entities/Self/Personal_Form_Profile.json",
}
CREDENTIAL_REFERENCE_CLASS="TVC_NONSECRET_PROVIDER_MATERIALIZATION_BROKER"

class PersonalProviderBindingError(ValueError): pass

def _require(ok:bool,msg:str)->None:
    if not ok: raise PersonalProviderBindingError(msg)

def deterministic_binding_id(provider:str,root_locator:str)->str:
    material=(provider.strip().upper()+"|"+root_locator.strip()).encode("utf-8")
    return "kvpb_"+hashlib.sha256(material).hexdigest()[:24]

def validate_binding(value:dict[str,Any])->dict[str,Any]:
    _require(isinstance(value,dict),"binding_object_required")
    allowed={"schema","binding_id","kv_kind","provider","root_locator","canonical_root_name","materialization_scope","credential_authority","credential_reference_class","compatibility_state","last_connection_proof_ref","last_readback_proof_ref","credential_material_present","provider_operation_authorized","authority_effect","activation_effect"}
    _require(set(value)==allowed,"binding_field_set_invalid")
    _require(value["schema"]==BINDING_SCHEMA,"binding_schema_invalid")
    _require(value["kv_kind"]=="PERSONAL_KV","binding_kv_kind_invalid")
    _require(value["provider"]=="GOOGLE_DRIVE","binding_provider_invalid")
    locator=value["root_locator"]
    _require(isinstance(locator,dict) and set(locator)=={"locator_type","value"},"binding_root_locator_invalid")
    _require(locator["locator_type"]=="GOOGLE_DRIVE_FOLDER_ID","binding_locator_type_invalid")
    _require(isinstance(locator["value"],str) and 10<=len(locator["value"])<=256,"binding_locator_value_invalid")
    _require(value["binding_id"]==deterministic_binding_id(value["provider"],locator["value"]),"binding_id_invalid")
    _require(value["canonical_root_name"]=="KnowledgeVault","binding_root_name_invalid")
    scope=value["materialization_scope"]
    _require(isinstance(scope,list) and scope and len(scope)==len(set(scope)),"binding_scope_invalid")
    _require(set(scope).issubset(ALLOWED_SCOPES),"binding_scope_expansion")
    _require(value["credential_authority"]=="TV/TVC","binding_credential_authority_invalid")
    _require(value["credential_reference_class"]==CREDENTIAL_REFERENCE_CLASS,"binding_credential_reference_invalid")
    _require(value["compatibility_state"] in {"ASSEMBLED_UNVERIFIED","VERIFIED","BLOCKED_SESSION","BLOCKED_RUNTIME","REVALIDATION_REQUIRED"},"binding_compatibility_state_invalid")
    _require(value["credential_material_present"] is False,"binding_credential_material_prohibited")
    _require(value["provider_operation_authorized"] is False,"binding_provider_authority_prohibited")
    _require(value["authority_effect"]=="NONE" and value["activation_effect"] is False,"binding_authority_invalid")
    return dict(value)

def build_binding(*,root_folder_id:str,compatibility_state:str="ASSEMBLED_UNVERIFIED",materialization_scope:Iterable[str]|None=None)->dict[str,Any]:
    scope=list(materialization_scope or [
        "_System/installation.receipt.json",
        "_System/Workspace/**",
        "_Entities/Self/Personal_Contact_Profile.json",
        "_Entities/Self/Personal_Form_Profile.json",
    ])
    value={
        "schema":BINDING_SCHEMA,
        "binding_id":deterministic_binding_id("GOOGLE_DRIVE",root_folder_id),
        "kv_kind":"PERSONAL_KV",
        "provider":"GOOGLE_DRIVE",
        "root_locator":{"locator_type":"GOOGLE_DRIVE_FOLDER_ID","value":root_folder_id},
        "canonical_root_name":"KnowledgeVault",
        "materialization_scope":scope,
        "credential_authority":"TV/TVC",
        "credential_reference_class":CREDENTIAL_REFERENCE_CLASS,
        "compatibility_state":compatibility_state,
        "last_connection_proof_ref":None,
        "last_readback_proof_ref":None,
        "credential_material_present":False,
        "provider_operation_authorized":False,
        "authority_effect":"NONE",
        "activation_effect":False,
    }
    return validate_binding(value)

def _safe_destination(root:Path,relative:str)->Path:
    _require(".." not in Path(relative).parts and not Path(relative).is_absolute(),"materialization_path_escape")
    target=(root/relative).resolve();resolved_root=root.resolve()
    _require(target==resolved_root or resolved_root in target.parents,"materialization_destination_escape")
    return target

def _write_exact(root:Path,relative:str,data:bytes)->dict[str,Any]:
    target=_safe_destination(root,relative);target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",dir=target.parent,delete=False) as handle:
        handle.write(data);temp_name=handle.name
    os.replace(temp_name,target)
    readback=target.read_bytes()
    _require(readback==data,"materialization_exact_readback_failed")
    return {"path":relative,"sha256":"sha256:"+hashlib.sha256(data).hexdigest(),"size_bytes":len(data)}

def _path_admitted(path:str,scope:list[str])->bool:
    if path in scope:
        return True
    if "_System/Workspace/**" in scope and re.fullmatch(r"_System/Workspace/[A-Za-z0-9._-]+",path):
        return True
    return False

def validate_broker_materialization(*,binding:dict[str,Any],broker_response:dict[str,Any])->dict[str,Any]:
    b=validate_binding(binding)
    _require(isinstance(broker_response,dict),"broker_response_object_required")
    _require(broker_response.get("decision")=="ALLOW_OPERATION_RESULT","broker_result_not_allowed")
    result=broker_response.get("result");receipt=broker_response.get("use_receipt")
    _require(isinstance(result,dict) and isinstance(receipt,dict),"broker_result_receipt_required")
    _require(result.get("schema")==BROKER_RESULT_SCHEMA,"broker_result_schema_invalid")
    _require(result.get("provider")=="GOOGLE_DRIVE","broker_result_provider_invalid")
    _require(result.get("binding_id")==b["binding_id"],"broker_result_binding_mismatch")
    _require(result.get("read_only") is True and result.get("provider_mutation_performed") is False,"broker_result_not_read_only")
    _require(result.get("credential_material_returned") is False,"broker_result_credential_material_prohibited")
    _require(result.get("credential_authority")=="TV/TVC","broker_result_credential_authority_invalid")
    _require(result.get("authority_effect")=="NONE","broker_result_authority_invalid")
    _require(receipt.get("provider")=="google_drive" and receipt.get("operation")=="personal_kv_materialize","broker_use_receipt_operation_invalid")
    for key in ("secret_material_returned","secret_material_logged","secret_material_retained","wallet_contacted","signed","broadcast"):
        _require(receipt.get(key) is False,"broker_use_receipt_boundary_invalid:"+key)
    _require(receipt.get("single_use_consumed") is True,"broker_use_receipt_single_use_missing")
    records=result.get("records")
    _require(isinstance(records,list),"broker_result_records_invalid")
    seen=set();validated=[]
    for row in records:
        _require(isinstance(row,dict),"broker_record_object_required")
        path=row.get("canonical_path")
        _require(isinstance(path,str) and _path_admitted(path,b["materialization_scope"]),"broker_record_path_not_admitted")
        _require(path not in seen,"broker_record_duplicate_path");seen.add(path)
        file_id=row.get("provider_file_id");encoded=row.get("content_base64");claimed_hash=row.get("sha256");size=row.get("size_bytes")
        _require(isinstance(file_id,str) and bool(file_id),"broker_record_provider_file_id_invalid")
        _require(isinstance(encoded,str),"broker_record_content_invalid")
        try:data=base64.b64decode(encoded.encode("ascii"),validate=True)
        except Exception as exc: raise PersonalProviderBindingError("broker_record_content_base64_invalid") from exc
        _require(isinstance(size,int) and size==len(data),"broker_record_size_mismatch")
        actual="sha256:"+hashlib.sha256(data).hexdigest()
        _require(claimed_hash==actual,"broker_record_hash_mismatch")
        validated.append({"path":path,"data":data,"sha256":actual,"size_bytes":len(data)})
    for exact in (set(b["materialization_scope"])-{"_System/Workspace/**"}):
        _require(exact in seen,"broker_result_required_path_missing:"+exact)
    return {"binding":b,"records":validated,"broker_use_receipt":dict(receipt)}

def materialize_broker_result(*,binding:dict[str,Any],broker_response:dict[str,Any],destination_root:Path)->dict[str,Any]:
    validated=validate_broker_materialization(binding=binding,broker_response=broker_response)
    b=validated["binding"]
    destination=destination_root.expanduser().resolve();destination.mkdir(parents=True,exist_ok=True)
    written=[]
    for row in validated["records"]:
        receipt=_write_exact(destination,row["path"],row["data"])
        _require(receipt["sha256"]==row["sha256"] and receipt["size_bytes"]==row["size_bytes"],"materialization_broker_readback_binding_failed")
        written.append(receipt)
    return {
        "schema":"stegverse.kv.provider-materialization-receipt/v2",
        "binding_id":b["binding_id"],
        "provider":"GOOGLE_DRIVE",
        "materialized_root":str(destination),
        "records":written,
        "exact_readback_verified":True,
        "credential_authority":"TV/TVC",
        "credential_material_persisted":False,
        "consumer_received_provider_credential":False,
        "provider_operation":"READ_ONLY_MATERIALIZATION_VIA_TVC_BROKER",
        "provider_operation_authority_transferred":False,
        "broker_use_receipt_sha256":"sha256:"+hashlib.sha256(repr(sorted(validated["broker_use_receipt"].items())).encode("utf-8")).hexdigest(),
        "authority_effect":"NONE",
        "activation_effect":False,
    }

def materialize_google_drive_scope(**_:Any)->dict[str,Any]:
    raise PersonalProviderBindingError("consumer_bearer_token_path_retired_use_tvc_broker_materialization")
