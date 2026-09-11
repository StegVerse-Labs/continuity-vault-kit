# Task Registry Sovereign KV Event Custody Mirror Handoff

Goal Task ID: `TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001`
Canonical parent handoff: `StegVerse-Labs/.github/docs/TASK_REGISTRY_SOVEREIGN_KV_EVENT_CUSTODY_MIRROR_HANDOFF.md`
Status: `ACTIVE / CROSS-REPO PROVIDER WRITE BINDING IMPLEMENTED / AUTHENTIC ADMITTED WRITE + READBACK PENDING`

## Purpose
Bind the canonical Task Registry sovereign-KV projection request to the existing continuity-vault-kit provider-neutral storage operation contract instead of creating a parallel provider stack.

## Implemented
- `runtime/task_registry_event_sovereign_kv_binding.py`
- `tests/test_task_registry_event_sovereign_kv_binding.py`

The binding consumes `stegverse.task-registry-sovereign-kv-projection-request/v1`, preserves the exact Task Registry event hash, resolves the existing provider adapter from `runtime/kv_storage_provider_adapter.py`, and builds the canonical `stegverse.kv.storage-provider-operation-request/v1` with `operation=WRITE`, `governance_state=PENDING_INTERLOCK_INTR`, `skap_credential_ref_required=true`, no credential material, and `object_ref` equal to the exact Task Registry event SHA-256.

The result validator accepts only an admitted/executed `stegverse.kv.storage-provider-operation-receipt/v1` with Interlock, InTr, SKAP, and provider-result references, plus exact stored-event SHA-256 readback. Only then does it emit the `.github` bridge-compatible `stegverse.task-registry-sovereign-kv-projection-receipt/v1`.

## Authority boundaries
This binding does not authenticate providers, resolve credentials, decide Interlock/InTr admission, execute provider I/O, or grant authority. WorkerCoordinator, Interlock/InTr, TV/TVC, Master Records, and HB authority boundaries remain unchanged.

## Remaining
1. validate this branch and PR;
2. bind an admitted provider WRITE receipt produced by the existing runtime path;
3. obtain exact stored-event hash readback from the target sovereign KV instance;
4. feed that receipt to `.github/scripts/project_task_registry_event_to_sovereign_kv.py` and close the parent unresolved predicate only after exact-hash custody is observed.

## Manual work
None.
