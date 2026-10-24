python - <<'PY'
from pathlib import Path
src=Path('runtime/cloud_peer_adoption_provider_binding.py').read_text(encoding='utf-8')
required=[
  'SITE-CLOUD-KV-',
  'PENDING_INTERLOCK_INTR',
  'ADMITTED_GOOGLE_DRIVE_CONNECT_RESULT',
  'ADMITTED_GOOGLE_DRIVE_VERIFY_RESULT',
  'interlock_receipt_ref',
  'intr_receipt_ref',
  'skap_credential_ref',
  'provider_result_ref',
  'SET_MEMBERSHIP_ORDINAL_BINDING_PRESERVE_CLOUD_IDENTITY',
  'cloud_identity_rewrite_required',
  'private_content_rewrite_authorized',
  'NONE_READINESS_ONLY',
]
missing=[x for x in required if x not in src]
if missing:
  raise SystemExit('missing provider-binding markers: '+', '.join(missing))
forbidden=[
  '"instance_materialization_authorized": True',
  '"private_content_rewrite_authorized": True',
  '"cloud_identity_rewrite_required": True',
  'credential_material_present": True',
]
present=[x for x in forbidden if x in src]
if present:
  raise SystemExit('prohibited provider-binding markers: '+', '.join(present))
print('KV_CLOUD_PEER_ADOPTION_PROVIDER_BINDING=PASS')
print('GOOGLE_DRIVE_CONNECT_VERIFY_EVIDENCE=REQUIRED')
print('KV2_CLOUD_IDENTITY_REWRITE=NONE')
print('KV2_MATERIALIZATION_FROM_SOURCE_ONLY=PROHIBITED')
PY
