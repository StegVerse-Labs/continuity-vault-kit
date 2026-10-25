# KV → SKAP Vault Account Transfer Mirror Handoff (in-KV SKAP gate)

Updated: 2026-09-10
Goal Task ID: `SS-SKAP-AUTHENTIC-ACCOUNT-METADATA-POPULATION-001`
Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `task/kv-skap-intr-account-transfer-20260910`
Status: `IMPLEMENTATION_ACTIVE / VALIDATION_PENDING`

## Finding

The architecture then stated a KV ↔ SKAP Vault InTr link (retired: the SKAP Vault sits inside KV and is reached through the in-KV SKAP gate), but the implemented `KV-INTERLOCK-v1` runtime core is DEVICE→KV oriented and explicitly grants no direct SKAP authority. No canonical exact KV→SKAP account-metadata transfer packet and receiving-boundary binding was found. That gap prevented the My KV Connected Accounts selector from being bound correctly to internal SKAP population.

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
3. exact `stegverse.kv-skap-gate.account-transfer-envelope/v1` in-KV SKAP gate envelope binding request hash + transfer-packet hash + payload hash from `KnowledgeVault` to `SKAP_Vault`.

The boundary envelope fixes `canonical_state_changed=false` and `credential_material_transferred=false`. It is not a SKAP admission receipt. The receiving SKAP side must independently validate the same hashes and an applicable in-KV SKAP gate decision before creating account state or a SKAP receipt.

## Required receiving-side continuation

TVC/SKAP must implement a consumer for `SKAP_ACCOUNT_METADATA_ADMIT` that:

- validates the exact transfer packet and boundary envelope;
- requires a retained in-KV SKAP gate decision/receipt bound to the exact request/packet hashes;
- rejects missing owner-selection evidence, secret-bearing fields, raw provider account ids, hash drift, replay mutation, and synthetic/test elevation;
- persists only bounded non-secret SKAP account metadata;
- emits a receipt compatible with `TVC/tools/skap_account_inventory_projection.py`;
- proves idempotent exact replay and refuses conflicting replay.

## Runtime truth

No authentic KV→SKAP account transfer is claimed from this source work. Completion requires an owner-selected real account from the My KV Connected Accounts UI to traverse this protocol, yield an in-KV SKAP gate receipt and SKAP receipt, and appear in the TVC account-inventory projection.

## In-KV SKAP gate framing (KV_SKAP_ACCOUNT_TRANSFER_INTR_ENVELOPE_RESIDUAL)

Updated 2026-10-25 under this Goal Task (Coordination ruling, StegVerse-org/.github#167 comment 6392591875 (b)). The SKAP Vault sits inside KV, so the KV → SKAP Vault transfer is the in-KV SKAP gate (`KV_INTERNAL_SKAP_GATE`), never an InTr hop. The envelope schema is `stegverse.kv-skap-gate.account-transfer-envelope/v1` (retired: the InTr boundary-transfer schema), and the builders are `build_kv_interlock_request` and `build_skap_gate_envelope`. The envelope field is `gate_receipt_ref`, and the conformance fixture keys are `kv_skap_gate_envelope` and `gate_receipt`. There is no alias. The receiving side, TVC `tools/skap_kv_account_metadata_ingress.py`, moves in the same coordinated change. The declared file paths of this task are kept as they are (`schemas/intr-boundary-transfer.schema.json`, `docs/KV_SKAP_INTR_ACCOUNT_TRANSFER_PROTOCOL.md` and this handoff). Renaming them is left to the task owner (class D note on #167).
Item `KV_SKAP_ACCOUNT_TRANSFER_INTR_ENVELOPE_RESIDUAL` and its closure are recorded on StegVerse-org/.github#167.

## Manual work

None.
