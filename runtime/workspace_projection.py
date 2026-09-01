from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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

def get_personal_workspace_projection(*,kv_data_root:Path)->dict[str,Any]:
    root=_root(kv_data_root)
    context=_read_optional(root,"workspace.json")
    principals=[_principal(row) for row in _rows(_read_optional(root,"principals.json"),"principals")]
    relationships=_rows(_read_optional(root,"relationships.json"),"relationships")
    organizations=[_principal(row) for row in _rows(_read_optional(root,"organizations.json"),"organizations")]
    for org in organizations: _require(org["principal_type"]=="ORGANIZATION","organization_principal_type_invalid")
    memberships=_rows(_read_optional(root,"memberships.json"),"memberships")
    feed=_rows(_read_optional(root,"feed.json"),"events")
    assistant_file=_read_optional(root,"assistant.json")
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
        "authority_effect":"NONE",
    }
