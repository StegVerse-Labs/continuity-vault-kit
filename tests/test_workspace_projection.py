import json
from pathlib import Path
from runtime.workspace_projection import WorkspaceProjectionError,get_personal_workspace_projection

def write(root:Path,name:str,value:dict):
    p=root/'_System'/'Workspace'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value),encoding='utf-8')

def base(schema,**extra): return {'schema':schema,'authority_effect':'NONE',**extra}

def test_absent_workspace_is_empty(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    p=get_personal_workspace_projection(kv_data_root=root)
    assert p['state']=='KV_WORKSPACE_EMPTY' and p['principals']==[] and p['authority_effect']=='NONE'

def test_ai_identity_and_relationships_are_preserved(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    people=[{'principal_id':'user:1','principal_type':'HUMAN','display_name':'User'},{'principal_id':'ai:1','principal_type':'AI_ENTITY','display_name':'Agent'}]
    write(root,'principals.json',base('stegverse.kv.workspace-principals/v1',principals=people))
    write(root,'relationships.json',base('stegverse.kv.workspace-relationships/v1',relationships=[{'subject_principal_id':'user:1','object_principal_id':'ai:1','relationship':'FRIEND'}]))
    p=get_personal_workspace_projection(kv_data_root=root)
    assert p['principals'][1]['ai_label_required'] is True
    assert p['relationships'][0]['relationship']=='FRIEND'

def test_workspace_assistant_must_be_ai(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    write(root,'assistant.json',base('stegverse.kv.workspace-assistant/v1',assistant={'principal_id':'user:1','principal_type':'HUMAN','display_name':'No','roles':['WORKSPACE_ASSISTANT']}))
    try: get_personal_workspace_projection(kv_data_root=root);assert False
    except WorkspaceProjectionError as exc: assert 'workspace_assistant_must_be_ai' in str(exc)

def test_secret_bearing_fields_fail_closed(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    write(root,'principals.json',base('stegverse.kv.workspace-principals/v1',principals=[{'principal_id':'x','principal_type':'HUMAN','display_name':'X','access_token':'bad'}]))
    try: get_personal_workspace_projection(kv_data_root=root);assert False
    except WorkspaceProjectionError as exc: assert 'secret_field_forbidden' in str(exc)
