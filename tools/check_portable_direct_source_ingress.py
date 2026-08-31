#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
runtime=(ROOT/"runtime/portable_direct_source_ingress.py").read_text()
tests=(ROOT/"tests/test_portable_direct_source_ingress.py").read_text()
schema=(ROOT/"schemas/kv-portable-direct-source-canonical-admission-receipt.schema.json").read_text()

for marker in (
    "def promote_portable_direct_source(",
    '"state": "CANONICAL_ADMITTED"',
    '"canonical_kv_persistence_observed": True',
    '"exact_canonical_readback_verified": True',
    '"trusted_semantic_admission": True',
    '"provider_session_required": False',
    '"credential_material_present": False',
    '"provider_operation_authorized": False',
    '"compatibility_state": "VERIFIED"',
    '"authority_effect": "NONE"',
):
    if marker not in runtime:
        raise SystemExit("PORTABLE_CANONICAL_ADMISSION_RUNTIME_MISSING:"+marker)

for marker in (
    "test_staged_owner_controlled_batch_promotes_to_canonical_kv_and_readback",
    "test_canonical_promotion_is_idempotent",
    "test_canonical_promotion_detects_staged_tamper",
    "test_canonical_promotion_rejects_staging_receipt_drift",
):
    if marker not in tests:
        raise SystemExit("PORTABLE_CANONICAL_ADMISSION_TEST_MISSING:"+marker)

for marker in (
    "stegverse.kv.portable-direct-source-canonical-admission/v1",
    "CANONICAL_ADMITTED",
    "exact_canonical_readback_verified",
):
    if marker not in schema:
        raise SystemExit("PORTABLE_CANONICAL_ADMISSION_SCHEMA_MISSING:"+marker)

print("PORTABLE_DIRECT_SOURCE_CANONICAL_ADMISSION_PASS")
