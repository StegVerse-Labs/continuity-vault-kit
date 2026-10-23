# KV-SKAP-LEDGER-LOCATION-001: KV's own KV and SKAP Vault receipt ledgers

Task KV-SKAP-LEDGER-LOCATION-001 sits under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324).

Rulings:
- StegVerse-org/.github#160 comment 6371986288: KV is independent of the ecosystem Orgs.
- #160 comment 6372045430: KV is a governed layer over user-owned storage via a GATEWAY node.
- #160 comment 6372216673 (**final**): the ledger lives encrypted in the user's storage.
- Lane B, #162 comment 6372170864: per-endpoint `ledger_designation`.

KV keeps its own two ledgers behind its own InTr endpoint (endpoint_kind KV). They are **never** on `StegVerse-org/.github` `refs/stegverse/organization-ledger` or any other git ref. Storage adapter design: `docs/kv-gateway-storage-adapter.md`.

| consumer key | storage location | contract | repository_ledger_location (#431 keys) | ledger_designation.store |
|---|---|---|---|---|
| `kv` | `01_KV_Ledger` | `.stegverse/receipt-ledgers/01_KV_Ledger.contract.json` | repository `KV`, ref `KV_INTR_ENDPOINT`, namespace `01_KV_Ledger`, new_ledger_root true, genesis null | `GATEWAY_ENCRYPTED_BLOB` at `01_KV_Ledger`, head `01_KV_Ledger/HEAD`, adapter_ref null |
| `skap_vault` | `02_SKAP_Vault_Ledger` | `.stegverse/receipt-ledgers/02_SKAP_Vault_Ledger.contract.json` | repository `KV`, ref `KV_INTR_ENDPOINT`, namespace `02_SKAP_Vault_Ledger`, new_ledger_root true, genesis null | `GATEWAY_ENCRYPTED_BLOB` at `02_SKAP_Vault_Ledger`, append route `KV_INTR_INGRESS` then layer 2 |

The contract sha256s are pinned in `runtime/kv_receipt_ledgers.py` `RECEIPT_LEDGERS` and reported in the PR body.

Rules:
- **Locations.** `##_<name>` names stay inside KV. `_StegVerse-org` / `presented_under` is dropped, because KV isn't presented under an Org.
- **SKAP Vault access.** The SKAP Vault ledger is inside KV and reachable only through KV's InTr (layer 2). `read_receipt_ledger('skap_vault')` is always `SKAP_VAULT_LEDGER_NOT_VIA_KV_INTR`. Only `SkapLayer2Gate.receipt_ledger(kv_access_receipt_hash, ...)` with a layer-1 receipt that this KV runtime minted proceeds.
- **Correspondence, not storage.** An Org↔KV interaction is a pair of hash-linked receipts, one in each side's own ledger. Neither ledger is copied across the boundary. A receipt whose `repository` isn't `KV/<name>` is `KV_LEDGER_FOREIGN_RECORD_REFUSED`.
- **Org designations refused.** An org or git-ref designation (GIT_REF, StegVerse-org/.github, refs/stegverse/organization-ledger, repository-ledger/...) is `KV_LEDGER_DESIGNATED_ON_ORG_LEDGER` (class C).
- **External storage records.** These are refused as KV ledger input (`EXTERNAL_STORAGE_RECORD_REFUSED`).
- **Rollback protections.** These are kept: append-only head pointer, signed head (`.stegverse/kv-ledger/kv-ledger-head-signers.v1.json`, empty), and the recorded-head check (`KV_LEDGER_ROLLBACK_DETECTED`).
- **Genesis.** It stays null and fails closed. It would be written only by the pin-after-observe transition (#162 comment 6371352606), triggered by KV's own ingress. #431's planner hard-codes the Org ref, so the wiring is HELD (Lane B).

## FAIL_CLOSED (six-field, all class B unless noted)
| failure_code | owner | next attempt |
|---|---|---|
| SVKV_GATEWAY_STORAGE_NOT_PROVISIONED | ECOSYSTEM-OWN-KV-001 (SVKV) | on the gateway registration once the Drive is provisioned |
| KV_LEDGER_GENESIS_NOT_PINNED | KV-SKAP-LEDGER-LOCATION-001 | after the pin-after-observe transition by KV's own ingress |
| KV_LEDGER_GENESIS_PIN_MECHANISM_ORG_HOSTED | Lane B (StegVerse-org/.github#162, LLM-adapter#431) | when Lane B posts the per-endpoint fix |
| KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED | TV/TVC; Lane C (TVC#540/#542 rebind) | when a KV_LEDGER_HEAD attester is published |
| KV_LEDGER_BLOB_KEY_NOT_CUSTODIED | TV/TVC custody (G8); SKAP-UNDECLARED-CRYPTOGRAPHY-001 | when a wrapped data key is custodied |

## Superseded (cvk#263 @f5f971a5 and earlier)
These values are superseded and are refused if they reappear:
- namespaces `repository-ledger/StegVerse-org/01_KV_Ledger` and `.../02_SKAP_Vault_Ledger` on `StegVerse-org/.github` `refs/stegverse/organization-ledger`;
- repositories `StegVerse-org/01_KV_Ledger` and `StegVerse-org/02_SKAP_Vault_Ledger`;
- `presented_under: _StegVerse-org`;
- contract sha256 `c32fbde7f4e159f44a294feaf34dd0a9c7a8a5eff9ca6ef97312473ff176a611` (01) and `71b665d49e97ba2eb0c965cc392266511c029badd9251bd58c696302ce40bcc5` (02);
- the ORG_LEDGER_GENESIS_NOT_PINNED / ORG_LEDGER_HEAD attester reading.

TVC#542's org-shape consumer rule therefore no longer accepts these ledgers, so Lane C must rebind it.
