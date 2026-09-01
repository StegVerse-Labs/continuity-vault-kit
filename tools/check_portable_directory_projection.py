#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
runtime=(ROOT/"runtime/portable_directory_projection.py").read_text()
tests=(ROOT/"tests/test_portable_directory_projection.py").read_text()
for marker in (
    "def list_admitted_directory(",
    "def get_directory_health(",
    "def get_installation_status(",
    '"schema":"stegverse.kv.installation-status-projection/v1"',
    '"state":"KV_INSTALLATION_VERIFIED"',
    '"current_cloud_provider_observation":False',
    '"state":"KV_LISTED"',
    '"compatibility_state":"VERIFIED"',
    '"provider_operation_authorized":False',
    '"credential_material_present":False',
):
    if marker not in runtime:
        raise SystemExit("PORTABLE_DIRECTORY_PROJECTION_MISSING:"+marker)
for marker in (
    "test_lists_only_canonical_admitted_metadata",
    "test_staged_only_batch_is_not_listed",
    "test_unassembled_health_is_explicit",
    "test_receipt_authority_drift_fails_closed",
    "test_installation_status_projects_bounded_verified_receipt",
    "test_installation_status_missing_receipt_is_explicit_not_verified",
    "test_installation_status_authority_drift_fails_closed",
):
    if marker not in tests:
        raise SystemExit("PORTABLE_DIRECTORY_PROJECTION_TEST_MISSING:"+marker)
print("PORTABLE_DIRECTORY_PROJECTION_PASS")
