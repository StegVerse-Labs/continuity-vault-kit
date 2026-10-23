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

## Additive: vault-lineage record type (class B consumes-extension)

KV-SKAP-VAULT-FUNCTIONAL-001 (finish point continuity-vault-kit#258) consumes this Goal for
`KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND`: the durable custody location a vault's receipt-hash lineage is read
from on any device. This binding now carries a second record type, `KV_SKAP_VAULT_LINEAGE`:

- `build_vault_lineage_record` wraps an exported `stegverse.kv-skap-vault-lineage/v1` lineage as
  `stegverse.task-registry-sovereign-kv-vault-lineage-record/v1`, re-deriving every receipt hash, the chain
  and the head, and refusing credential or key material.
- `build_vault_lineage_custody_binding` produces the existing v1 provider WRITE request
  (object_ref = lineage hash) plus a v1 READ request from `build_vault_lineage_readback_request`
  (runtime/kv_storage_provider_adapter.py), so any device reads the lineage back by its exact hash.
- `validate_vault_lineage_custody_result` requires the admitted WRITE receipt and that the read-back
  lineage re-derives to the bound hash and head.

The projection-request schema, the event binding, its receipt and the adapter's v1 request builder are
byte-unchanged; `tests/test_sovereign_kv_vault_lineage_record.py` pins their digests as observed at main
`bcc2d75`. No provider I/O, credential, or authority is added (`authority_effect: NONE`).

## Ladder conformance (StegVerse-Labs/.github#3330, LC-KV-02 and LC-KV-03(a))

- **LC-KV-02.** `validate_vault_lineage_custody_result` is the E0 terminal of the durable-custody validation
  handoff and now returns a disposition instead of raising. On success it returns the custody receipt with
  `disposition: ALLOW`. Otherwise it returns a six-field FAIL_CLOSED: `failure_code`, `failed_predicate`
  (`AUTHENTIC_ADMITTED_PROVIDER_WRITE_AND_EXACT_EVENT_HASH_READBACK_FROM_SOVEREIGN_KV`),
  `required_evidence_or_repair`, `retry_entrypoint`, `owning_existing_goal` (this Goal) and `next_attempt`.
  The raise stays internal in `_validate_vault_lineage_custody_result_strict`.
- **LC-KV-03, revision 1 (withdrawal).** The ecosystem git-ref custody adapter
  (`refs/stegverse/kv-custody/<principal>`, formerly `runtime/kv_ecosystem_git_ref_custody.py`) is removed:
  it reached custody without passing either credential layer. `vault_lineage_registry()` is `default_registry()`
  again, and no provider is an access path. A provider may at most carry the sealed lineage below the gates.
- **Two credential layers (LC-KV-03 rev 1, LC-KV-08).** `validate_vault_lineage_custody_result` now also
  requires the provider receipt to bind `kv_access_receipt_hash` and `skap_access_receipt_hash`:
  - The first is the layer-1 INTR_DEVICE_KV receipt, minted by `KVInterlockRuntime.handle` for a currently
    admitted healthy node.
  - The second is the layer-2 INTR_KV_SKAP receipt. A separate gate inside KV mints it, and its
    `prior_receipt_hash` is the layer-1 receipt.
  - The caller supplies `access_receipt_verifier`, which is the layer-2 gate's `verify_access_chain` in
    continuity-vault-kit#258. The verifier checks both receipts against the gates' own receipt stores; a
    non-empty string is never accepted.
  - A missing or unverified layer returns a six-field FAIL_CLOSED that names the refusing layer:
    `KV_ACCESS_LAYER1_REFUSED` (failed_predicate `KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE`) or
    `SKAP_ACCESS_LAYER2_REFUSED` (failed_predicate `SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT`).
  - This module mints neither receipt.
