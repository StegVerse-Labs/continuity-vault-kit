python3 - <<'PY'
import json
from pathlib import Path
contract=json.loads(Path('specs/skap-vault-double-interlock.v1.json').read_text())
assert contract['canonical_topology'] == ['DEVICE','INTR_DEVICE_KV','KV','INTR_KV_SKAP','SKAP_VAULT']
assert contract['boundaries']['device_kv']['connector'] == 'InTr'
assert contract['boundaries']['kv_skap']['connector'] == 'InTr'
assert contract['boundaries']['device_kv']['receipt_required'] is True
assert contract['boundaries']['kv_skap']['receipt_required'] is True
assert contract['boundaries']['kv_skap']['kv_decryption_authority'] is False
assert contract['boundaries']['device_kv']['device_durable_secret_custody'] is False
assert contract['storage']['credential_objects'] == '_Vault/SKAP/Credentials'
assert contract['access_contract']['all_credential_reads_require_both_interlocks'] is True
assert contract['access_contract']['all_credential_writes_require_both_interlocks'] is True
assert contract['transition_receipts']['second_receipt_must_bind_first_receipt_hash'] is True
print('SKAP_VAULT_DEVICE_KV_INTR_REQUIRED=true')
print('SKAP_VAULT_KV_SKAP_INTR_REQUIRED=true')
print('SKAP_VAULT_KV_DECRYPTION_AUTHORITY=false')
print('SKAP_VAULT_DEVICE_SECRET_CUSTODY=false')
print('SKAP_VAULT_DOUBLE_RECEIPT_CHAIN_REQUIRED=true')
PY
