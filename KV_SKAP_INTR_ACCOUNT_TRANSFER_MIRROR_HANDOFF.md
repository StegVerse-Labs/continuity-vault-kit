# KV → SKAP InTr Account Transfer Mirror Handoff

Updated: 2026-09-10
Goal Task ID: `SS-SKAP-AUTHENTIC-ACCOUNT-METADATA-POPULATION-001`
Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `task/kv-skap-intr-account-transfer-20260910`
Status: `IMPLEMENTATION_ACTIVE / VALIDATION_PENDING`

## Finding

The existing architecture states `SKAP Vault ←InTr→ KnowledgeVault`, but the implemented `KV-INTERLOCK-v1` runtime core is DEVICE→KV oriented and explicitly grants no direct SKAP authority. No canonical exact KV→SKAP account-metadata transfer packet and receiving-boundary binding was found. That gap prevented the My KV Connected Accounts selector from being bound correctly to internal SKAP population.

## Implemented source contract

Added:

- `schemas/kv-skap-account-metadata-transfer.schema.json`
- `schemas/intr-boundary-transfer.schema.json`
- `runtime/kv_skap_account_transfer.py`
- `tests/test_kv_skap_account_transfer.py`
- `docs/KV_SKAP_INTR_ACCOUNT_TRANSFER_PROTOCOL.md`

The transfer is intentionally split into three layers:

1. owner-selected, non-secret KV transfer packet;
2. canonical `kv.interlock.request.v1` `COMMIT_CANDIDATE` referencing the exact payload hash;
3. exact `stegverse.intr.boundary-transfer/v1` envelope binding request hash + transfer-packet hash + payload hash from `KnowledgeVault` to `SKAP_Vault`.

The boundary envelope fixes `canonical_state_changed=false` and `credential_material_transferred=false`. It is not a SKAP admission receipt. The receiving SKAP side must independently validate the same hashes and an applicable InTr decision before creating account state or a SKAP receipt.

## Required receiving-side continuation

TVC/SKAP must implement a consumer for `SKAP_ACCOUNT_METADATA_ADMIT` that:

- validates the exact transfer packet and boundary envelope;
- requires a retained InTr decision/receipt bound to the exact request/packet hashes;
- rejects missing owner-selection evidence, secret-bearing fields, raw provider account ids, hash drift, replay mutation, and synthetic/test elevation;
- persists only bounded non-secret SKAP account metadata;
- emits a receipt compatible with `TVC/tools/skap_account_inventory_projection.py`;
- proves idempotent exact replay and refuses conflicting replay.

## Runtime truth

No authentic KV→SKAP account transfer is claimed from this source work. Completion requires an owner-selected real account from the My KV Connected Accounts UI to traverse this protocol, yield an InTr receipt and SKAP receipt, and appear in the TVC account-inventory projection.

## Manual work

None.
