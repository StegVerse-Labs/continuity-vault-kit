# KV-SKAP-LEDGER-LOCATION-001: the KV and SKAP Vault receipt ledgers

Task KV-SKAP-LEDGER-LOCATION-001 sits under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324). Following Rigel's model, each receipt ledger is a repository ledger on the Org Ledger. Both use StegVerse-org/LLM-adapter#431's `repository_ledger_location` shape exactly, with no new ref type and no new mechanism.

| consumer key (TVC#542 `org_ledger.custody_ledgers`) | storage location | #431 repository | namespace on `StegVerse-org/.github` `refs/stegverse/organization-ledger` | carries | contract |
|---|---|---|---|---|---|
| `kv` | `01_KV_Ledger` | `StegVerse-org/01_KV_Ledger` | `repository-ledger/StegVerse-org/01_KV_Ledger` | stegverse.kv-access-receipt/v1 (L1) | `.stegverse/receipt-ledgers/01_KV_Ledger.contract.json` sha256:c32fbde7f4e159f44a294feaf34dd0a9c7a8a5eff9ca6ef97312473ff176a611 |
| `skap_vault` | `02_SKAP_Vault_Ledger` | `StegVerse-org/02_SKAP_Vault_Ledger` | `repository-ledger/StegVerse-org/02_SKAP_Vault_Ledger` | stegverse.skap-access-receipt/v1 (L2), stegverse.tvc.skap-custody-reference-issuance/v1 (TVC#537), stegverse.tvc.skap-custody-operation-result/v1 | `.stegverse/receipt-ledgers/02_SKAP_Vault_Ledger.contract.json` sha256:71b665d49e97ba2eb0c965cc392266511c029badd9251bd58c696302ce40bcc5 |

Naming (Coordination's provisional ruling, Oct 23 6:20 PM, pending Rigel's confirmation):
- The namespace keeps the real org segment, `repository-ledger/StegVerse-org/##_<name>`, as #431 does.
- `##_<name>` is the storage-location segment. The `##_` prefix only keeps data-location names distinct for human review.
- `_StegVerse-org` is the Org as the coordination and presentation of this data (e.g. MyKV WorkSpace). It appears only as presentation metadata (`presented_under`), never as a path segment.

Genesis:
- `expected_genesis_receipt_sha256` is null.
- It is written only by the REPOSITORY_LEDGER_GENESIS_PIN transition (#431), after the REPOSITORY_LEDGER_INITIALIZATION genesis is observed (StegVerse-org/.github#162 comment 6371352606).
- Until then, every read and both finish-point rows are six-field FAIL_CLOSED `ORG_LEDGER_GENESIS_NOT_PINNED` (class B), with `next_attempt` naming REPOSITORY_LEDGER_GENESIS_PIN.

How the layers use these ledgers (`runtime/kv_receipt_ledgers.py`):
- Layer 1 (`KVInterlockRuntime.receipt_ledger`, plus each kv-access receipt's `receipt_ledger`) reads from `kv`.
- Layer 2 (`SkapLayer2Gate.receipt_ledger`, plus each skap-access receipt's `receipt_ledger` and `layer1_receipt_ledger`) reads from `skap_vault`.
- The custody binding (`receipt_ledger` on CUSTODY_KEY_REFERENCE_BOUND) also reads from `skap_vault`.
- Layer 2 refuses a layer-1 receipt that names a different ledger.
- `custody_ledgers_config()` gives the designations in TVC#542's config shape.

Read-back reuses #432's pinned code:
- the `org_ledger_location` tree unpack;
- `healthy_node_evaluator.read_chain`;
- the published ORG_LEDGER_HEAD attesters and the stdlib Ed25519 verify.

The read-back writes nothing, and it does not import `cryptography`.

Reproduce:

```
python -m pytest -q tests/test_kv_ladder_conformance_lc_kv.py -k KvSkapLedgerLocation
python -m runtime.kv_skap_vault finish-point   # rc 2; receipt_ledger_prerequisites: kv, skap_vault ORG_LEDGER_GENESIS_NOT_PINNED
```
