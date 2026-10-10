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

from datetime import datetime, timedelta, timezone
from runtime.workspace_projection import _reject_secrets

FIXED=datetime(2026,10,10,12,0,0,123456,tzinfo=timezone.utc)

def test_projection_metadata_is_producer_bound_and_non_authorizing(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    p=get_personal_workspace_projection(kv_data_root=root,clock=lambda:FIXED)
    m=p['projection_metadata']
    assert m['schema']=='stegverse.kv.workspace-projection-metadata/v1'
    assert m['observed_at']=='2026-10-10T12:00:00Z' and m['observed_at_semantics']=='KV_PROJECTION_PRODUCTION_TIME'
    assert m['grant_state']=='UNKNOWN' and m['revocation_epoch'] is None and m['authority_effect']=='NONE'
    assert m['workspace_type']=='PERSONAL' and m['workspace_id'] is None and m['owner_principal_id'] is None
    assert m['provenance_ref']=='kv-workspace-source:sha256:'+m['source_revision'] and len(m['source_revision'])==64
    assert 'source_cursor' not in m
    _reject_secrets(m)
    assert p['authority_effect']=='NONE' and p['workspace_grants_authority'] is False

def test_source_revision_binds_exact_source_records(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    empty=get_personal_workspace_projection(kv_data_root=root,clock=lambda:FIXED)['projection_metadata']['source_revision']
    people=[{'principal_id':'user:1','principal_type':'HUMAN','display_name':'User'}]
    write(root,'principals.json',base('stegverse.kv.workspace-principals/v1',principals=people))
    first=get_personal_workspace_projection(kv_data_root=root,clock=lambda:FIXED)['projection_metadata']
    later=get_personal_workspace_projection(kv_data_root=root,clock=lambda:FIXED+timedelta(hours=1))['projection_metadata']
    assert first['source_revision']!=empty
    assert later['source_revision']==first['source_revision'] and later['observed_at']=='2026-10-10T13:00:00Z'
    people[0]['display_name']='Renamed'
    write(root,'principals.json',base('stegverse.kv.workspace-principals/v1',principals=people))
    changed=get_personal_workspace_projection(kv_data_root=root,clock=lambda:FIXED)['projection_metadata']
    assert changed['source_revision']!=first['source_revision']

def test_workspace_context_identity_is_bound_when_present(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    write(root,'workspace.json',base('stegverse.kv.workspace-context/v1',workspace_id='ws:personal:1',owner_principal_id='user:1'))
    m=get_personal_workspace_projection(kv_data_root=root,clock=lambda:FIXED)['projection_metadata']
    assert m['workspace_id']=='ws:personal:1' and m['owner_principal_id']=='user:1' and m['grant_state']=='UNKNOWN'

def test_naive_clock_fails_closed(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    try: get_personal_workspace_projection(kv_data_root=root,clock=lambda:datetime(2026,10,10,12,0,0));assert False
    except WorkspaceProjectionError as exc: assert 'projection_clock_must_be_timezone_aware' in str(exc)

def test_default_clock_is_current_utc(tmp_path):
    root=tmp_path/'KnowledgeVault';(root/'_System').mkdir(parents=True)
    m=get_personal_workspace_projection(kv_data_root=root)['projection_metadata']
    observed=datetime.fromisoformat(m['observed_at'].replace('Z','+00:00'))
    assert abs((datetime.now(timezone.utc)-observed).total_seconds())<5
