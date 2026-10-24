python - <<'PY'
from runtime.kv_storage_provider_adapter import default_registry, build_operation_request
r=default_registry()
ids={d['provider_id'] for d in r.descriptors()}
required={'device-local','icloud-drive','google-drive','onedrive','dropbox','nas','removable-storage'}
assert required <= ids
g=build_operation_request(adapter=r.get('google-drive'),instance_id='kvi_a31335d2cc3745fa987b635432cfed2c',kv_set_id='personal',operation='VERIFY',storage_locator='/KnowledgeVault')
assert g['schema']=='stegverse.kv.storage-provider-operation-request/v1'
assert g['governance_state']=='PENDING_INTERLOCK_INTR'
assert g['provider_operation_executed'] is False
assert g['authority_effect']=='NONE'
d=build_operation_request(adapter=r.get('device-local'),instance_id='kvi_11111111111111111111111111111111',kv_set_id='personal',operation='VERIFY',storage_locator='KnowledgeVault')
assert d['skap_credential_ref_required'] is False
print('KV_STORAGE_ENDPOINT_V2=PASS')
print('LEGACY_OPERATION_REQUEST_V1=PASS')
print('RUNTIME_AUTHORITY=NONE')
PY
