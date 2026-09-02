"""Provider-neutral Personal KnowledgeVault binding and minimal Google Drive materialization.

This module never owns credentials. A Google Drive bearer token may only be supplied by
a TV/TVC-owned ephemeral session file at runtime. The token is read for request use and
is never copied into the KnowledgeVault, receipts, logs, or materialized files.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

BINDING_SCHEMA="stegverse.kv.personal-provider-binding/v1"
ALLOWED_SCOPES={
    "_System/installation.receipt.json",
    "_System/Workspace/**",
    "_Entities/Self/Personal_Contact_Profile.json",
    "_Entities/Self/Personal_Form_Profile.json",
}
GOOGLE_DRIVE_API="https://www.googleapis.com/drive/v3/files"
GOOGLE_FOLDER_MIME="application/vnd.google-apps.folder"

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
    _require(value["credential_reference_class"]=="TVC_EPHEMERAL_PROVIDER_SESSION","binding_credential_reference_invalid")
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
        "credential_reference_class":"TVC_EPHEMERAL_PROVIDER_SESSION",
        "compatibility_state":compatibility_state,
        "last_connection_proof_ref":None,
        "last_readback_proof_ref":None,
        "credential_material_present":False,
        "provider_operation_authorized":False,
        "authority_effect":"NONE",
        "activation_effect":False,
    }
    return validate_binding(value)

def _read_tvc_bearer(token_file:Path)->str:
    path=token_file.expanduser().resolve()
    _require(path.is_file(),"tvc_provider_session_file_missing")
    mode=stat.S_IMODE(path.stat().st_mode)
    _require(mode & 0o077 == 0,"tvc_provider_session_file_permissions_too_broad")
    token=path.read_text(encoding="utf-8").strip()
    _require(bool(token) and len(token)<=8192,"tvc_provider_session_token_invalid")
    return token

def _drive_json(url:str,token:str)->dict[str,Any]:
    request=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,"Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=20) as response:
        payload=response.read()
    result=json.loads(payload.decode("utf-8"))
    _require(isinstance(result,dict),"google_drive_response_invalid")
    return result

def _drive_bytes(file_id:str,token:str)->bytes:
    url=GOOGLE_DRIVE_API+"/"+urllib.parse.quote(file_id,safe="")+"?alt=media"
    request=urllib.request.Request(url,headers={"Authorization":"Bearer "+token})
    with urllib.request.urlopen(request,timeout=30) as response:
        return response.read()

def _children(parent_id:str,token:str)->list[dict[str,Any]]:
    items=[];page_token=None
    while True:
        params={
            "q":f"'{parent_id}' in parents and trashed = false",
            "fields":"nextPageToken,files(id,name,mimeType,size,modifiedTime)",
            "pageSize":"1000",
            "spaces":"drive",
        }
        if page_token: params["pageToken"]=page_token
        result=_drive_json(GOOGLE_DRIVE_API+"?"+urllib.parse.urlencode(params),token)
        files=result.get("files",[])
        _require(isinstance(files,list),"google_drive_children_invalid")
        items.extend(files)
        page_token=result.get("nextPageToken")
        if not page_token: return items

def _child_named(parent_id:str,name:str,token:str)->dict[str,Any]:
    matches=[item for item in _children(parent_id,token) if item.get("name")==name]
    _require(len(matches)==1,"google_drive_path_component_not_unique:"+name)
    return matches[0]

def _resolve_path(root_id:str,path:str,token:str)->dict[str,Any]:
    current={"id":root_id,"name":"KnowledgeVault","mimeType":GOOGLE_FOLDER_MIME}
    for part in [p for p in path.split("/") if p]:
        _require(current.get("mimeType")==GOOGLE_FOLDER_MIME,"google_drive_nonfolder_in_path:"+part)
        current=_child_named(current["id"],part,token)
    return current

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

def materialize_google_drive_scope(*,binding:dict[str,Any],token_file:Path,destination_root:Path)->dict[str,Any]:
    b=validate_binding(binding)
    token=_read_tvc_bearer(token_file)
    root_id=b["root_locator"]["value"]
    destination=destination_root.expanduser().resolve();destination.mkdir(parents=True,exist_ok=True)
    records=[]
    try:
        if "_System/installation.receipt.json" in b["materialization_scope"]:
            item=_resolve_path(root_id,"_System/installation.receipt.json",token)
            _require(item.get("mimeType")!=GOOGLE_FOLDER_MIME,"installation_receipt_not_file")
            records.append(_write_exact(destination,"_System/installation.receipt.json",_drive_bytes(item["id"],token)))
        if "_Entities/Self/Personal_Contact_Profile.json" in b["materialization_scope"]:
            item=_resolve_path(root_id,"_Entities/Self/Personal_Contact_Profile.json",token)
            _require(item.get("mimeType")!=GOOGLE_FOLDER_MIME,"personal_profile_not_file")
            records.append(_write_exact(destination,"_Entities/Self/Personal_Contact_Profile.json",_drive_bytes(item["id"],token)))
        if "_Entities/Self/Personal_Form_Profile.json" in b["materialization_scope"]:
            item=_resolve_path(root_id,"_Entities/Self/Personal_Form_Profile.json",token)
            _require(item.get("mimeType")!=GOOGLE_FOLDER_MIME,"personal_form_profile_not_file")
            records.append(_write_exact(destination,"_Entities/Self/Personal_Form_Profile.json",_drive_bytes(item["id"],token)))
        if "_System/Workspace/**" in b["materialization_scope"]:
            folder=_resolve_path(root_id,"_System/Workspace",token)
            _require(folder.get("mimeType")==GOOGLE_FOLDER_MIME,"workspace_not_folder")
            for item in _children(folder["id"],token):
                _require(item.get("mimeType")!=GOOGLE_FOLDER_MIME,"workspace_nested_folder_not_supported")
                name=str(item.get("name") or "")
                _require(bool(re.fullmatch(r"[A-Za-z0-9._-]+",name)),"workspace_filename_invalid")
                records.append(_write_exact(destination,"_System/Workspace/"+name,_drive_bytes(item["id"],token)))
    finally:
        token=""
    receipt={
        "schema":"stegverse.kv.provider-materialization-receipt/v1",
        "binding_id":b["binding_id"],
        "provider":"GOOGLE_DRIVE",
        "materialized_root":str(destination),
        "records":records,
        "exact_readback_verified":True,
        "credential_authority":"TV/TVC",
        "credential_material_persisted":False,
        "provider_operation":"READ_ONLY_MATERIALIZATION",
        "provider_operation_authorized_by_session":True,
        "provider_operation_authority_transferred":False,
        "authority_effect":"NONE",
        "activation_effect":False,
    }
    return receipt
