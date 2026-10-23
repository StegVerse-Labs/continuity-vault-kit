# KV-SKAP-LEDGER-LOCATION-001: STEGVERSE_KV's own recorded receipt chains

Task KV-SKAP-LEDGER-LOCATION-001 sits under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324).

**Governing correction:** StegVerse-org/.github#167 comment 6372442705. It supersedes the earlier #160, #167 and
#162 rulings that this PR followed at `ddbe7c7f` (the withdrawn ecosystem-KV designation, the dropped storage module, the encrypted
ledger, G8). It defers to the documented model in this repository:

- `docs/KV_AI_PERSISTENCE_LAYOUTS.md` and `specs/kv-ai-persistence-layouts.v1.json` define STEGVERSE_KV, with logical
  root `_StegVerse/` and receipt_root `_StegVerse/Receipts`.
- `KV_STORAGE_ENDPOINT_V2_MIRROR_HANDOFF.md` and `runtime/kv_storage_provider_adapter.py` define the chain
  `KV instance -> storage endpoint -> access adapter -> location`.
- `specs/skap-kv-storage-layout.v2.json` and `SKAP_PORTABLE_ENVELOPE_V2_MIRROR_HANDOFF.md` define `_Vault/SKAP` and
  the wrapped-root-envelope.
- The README "Safety" section says the KV baseline file structure is not encryption.

## Where the chains live

| consumer key | location (in STEGVERSE_KV) | contract | carries |
|---|---|---|---|
| `kv` | `_StegVerse/Receipts` (receipt_root) | `.stegverse/receipt-chains/stegverse-kv-receipts.contract.json` | stegverse.kv-access-receipt/v1 (L1) |
| `skap_vault` | `_Vault/SKAP/Receipts` (SKAP access_receipts) | `.stegverse/receipt-chains/skap-receipts.contract.json` | L2 receipts, TVC#537 custody-reference issuance, custody-result receipts |

### STEGVERSE_KV and the KV #2 lineage

STEGVERSE_KV is the existing Google Drive KV #2 lineage, federation contract
**SITE-CLOUD-KV-4347408852127319cbda574f02e03edb**. That request is PENDING_INTERLOCK_INTR. This PR does not
regenerate it, rehash it, or treat it as executed.

### The designated store

Each contract keeps:

- the `repository_ledger_location` keys of StegVerse-org/LLM-adapter#431, with KV-owned values: repository
  `STEGVERSE_KV`, ref `KV_INTR_ENDPOINT`, and the location above as the namespace;
- a `ledger_designation` that uses the field names of #431 @a2237bc3 `llm_adapter/endpoint_ledger_designation.py`.

Each designation names exactly one store, under `SINGLE_PROVIDER_V1`. That store is one documented storage endpoint
v2 descriptor:

```json
{"store_type": "KV_STORAGE_ENDPOINT", "storage_endpoint_schema": "stegverse.kv.storage-endpoint-descriptor/v2",
 "provider_id": "google-drive", "access_adapter": "provider-or-file-provider", "kv_class": "STEGVERSE_KV",
 "kv_request_id": "SITE-CLOUD-KV-4347408852127319cbda574f02e03edb", "location": "_StegVerse/Receipts"}
```

The provider is not authority. Multi-provider redundancy is out of scope here: more than one store is refused with
`ENDPOINT_LEDGER_MULTI_PROVIDER_NOT_SUPPORTED`.

## Reuse, not a new adapter

The receipt-chain reader takes a `KVStorageProviderAdapter` from `default_registry()` and a read-back root. Both come
from `runtime/kv_storage_provider_adapter.py`. The adapter must be the one the designation names, with the same
`provider_id` and `access_adapter`.

The reader defines no storage or adapter interface of its own. The storage module that `ddbe7c7f` added
duplicated this seam, so it has been dropped.

The read-back layout is `HEAD.json` plus `receipts/<sha256 hex>.json`. It is walked by the vendored #432
`read_chain`, which is unchanged.

**Scope.** This PR defines only the read seam on the documented storage endpoint. KV infrastructure (the SKAP
Vault, KV, and the StegOS boundaries through a healthy node) is built by Lane D under KV-SKAP-VAULT-FUNCTIONAL-001
and does not depend on SV-011. SV-011 is the governed-AI-Entity package that the KV AI assistant will consume later.

**No endpoint is an Org member.** No endpoint (KV, SKAP Vault, node or gateway) is ever a GitHub Organization
member. STEGVERSE_KV is the KV class, not a GitHub repository. The contracts carry no org repository, no
org-membership, team or app-installation binding, and no org ref. KV reaches the Orgs only through InTr
(`KV_INTR_ENDPOINT`, intr-destination path_ids). A contract that binds any of these is refused with six-field
FAIL_CLOSED `ENDPOINT_ORG_MEMBERSHIP_REFUSED` (class C), right after the org-ledger-ref check.

**Closed key schema (LC-KV-24).** The contract keys are an allow-list at every level, in
`runtime.kv_receipt_ledgers.CONTRACT_KEY_SCHEMA`. The levels are:

- top level;
- `repository_ledger_location`;
- `ledger_designation`;
- each store;
- `rollback_watermark_source` (keys `source`, `org_crossing_cross_check`) and its required
  `org_crossing_cross_check` (keys `source`, `path_ids`, `role`);
- `designation_notes`.

Any other key is refused, whatever it is called:

- **Membership-like keys get `ENDPOINT_ORG_MEMBERSHIP_REFUSED`.** A key is membership-like when one of its
  snake/camel tokens is in `MEMBERSHIP_TOKENS`, for example `organization`, `github_app_installation_id`,
  `permissions`, `owner` or `team_slug`.
- **Every other unknown key gets six-field FAIL_CLOSED `KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY`** (class C,
  predicate `KV_RECEIPT_CHAIN_DESIGNATION_KEYS_CLOSED`).

The token test only chooses which refusal code applies. It never admits a key.

Some leaves also have closed values. `rollback_watermark_source.source` allows only `KV_RECORDED_RECEIPT_CHAIN_HEAD`
(an Org-ledger source is refused with `KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED`, class A). In the required cross-check,
`source` allows only `ORG_LEDGER_LINKED_RECEIPTS_ENDPOINT_HEAD`, `role` only
`DIGEST_ONLY_CROSS_CHECK_NEVER_WATERMARK`, and `path_ids` must be a non-empty list whose every entry ends in
`:intr-destination` (Lane B's rule at LLM-adapter#432 @c4cfc145, adopted; otherwise
`KV_RECEIPT_CHAIN_STORE_NOT_STORAGE_ENDPOINT_V2`, class C).

## What is not claimed

- **No ledger-wide encryption.** The receipt chains are recorded receipts, not encrypted objects. Ciphertext lives
  only behind SKAP, at `_Vault/SKAP/Sealed`.
- **SKAP's root key.** ENVELOPE v2 governs it. The root is wrapped at `_Vault/SKAP/Root/wrapped-root-envelope.json`
  and is unwrapped only by the owner-only recovery secret. That secret is never stored in KV, SKAP or TV/TVC.
- **The MyKV AI Assistant (WORKSPACE_ASSISTANT).** It proposes; it never transitions a receipt chain. Every mutation
  needs InTr admission.

## What the Org ledger carries

No KV or SKAP Vault recorded receipt chain is on any Org organization-ledger ref (LC-KV-21,
StegVerse-org/.github#163 comment 6372658597). The Org ledger carries only digest-only InTr crossing receipts: a
pointer/digest plus SUPPLIED_HB_EPOCH. The digest is **`KV_RECORDED_RECEIPT_CHAIN_HEAD`**, the name
StegVerse-Labs/TVC#542 @4c2504da gives to what `kv_ledger_head_signer` signs. Here it is the head attestation's
`head_receipt_sha256`.

## Rules

- **Correspondence, not storage.** An Org/KV interaction is two linked receipts, one in each side's own chain. A
  receipt naming another repository is refused with `KV_RECEIPT_CHAIN_FOREIGN_RECORD_REFUSED`.
- **External records stay out.** The provider's own records, such as file metadata and revisions, never cross into
  KV. They are refused with `EXTERNAL_STORAGE_RECORD_REFUSED`.
- **Rollback protection.**
  - The genesis is pinned.
  - The head is signed by a published `kv_ledger_head_signer`, listed in
    `.stegverse/node-ledger/kv-ledger-head-signers.v1.json`.
  - The watermark is KV's own recorded receipt chain head, `KV_RECORDED_RECEIPT_CHAIN_HEAD` (the head
    `kv_ledger_head_signer` signs, TVC#542 @4c2504da). KV is independent of the Orgs, so the watermark never comes
    from the Org ledger. LC-KV-23 is class A per Coordination's ruling on StegVerse-org/.github#167, comment
    6374130335.
  - **The reader reads the watermark itself.** It comes from KV's own append-only head record behind the storage
    endpoint, `.stegverse/node-ledger/head-record.v1.jsonl` beside each chain's `HEAD.json`. Each line has schema
    `stegverse.kv-recorded-head/v1` and is hash-linked to the line before it (`previous_record_sha256`,
    `record_sha256`). Every recorded head must be on the read-back chain, in order. The newest recorded head must be
    the chain head. If it is not, or the chain head has regressed behind it, the read is DENY
    `KV_LEDGER_HEAD_ROLLBACK_DETECTED`. If the record is absent, empty or malformed, the read is six-field
    FAIL_CLOSED `KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING` (class A, Coordination accepted the B→A reclass). A
    properly signed older head is therefore never accepted on its signature alone.
  - **A caller's `recorded_head` is only a claim.** It is optional. When present it must be
    `{"source": "KV_RECORDED_RECEIPT_CHAIN_HEAD", "head_receipt_sha256": "sha256:<64 hex>"}` and must equal the
    head the reader read; otherwise DENY `KV_LEDGER_HEAD_ROLLBACK_DETECTED` (a caller presenting the regressed head
    is refused). It is never echoed as evidence.
  - A watermark or designation sourced from the Org ledger (for example `ORG_LEDGER_LINKED_RECEIPTS_ENDPOINT_HEAD`)
    is refused with six-field FAIL_CLOSED `KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED` (class A, predicate
    `ROLLBACK_WATERMARK_SOURCED_FROM_KV_OWN_RECEIPT_CHAIN`, owned by KV-SKAP-VAULT-FUNCTIONAL-001).
  - **The Org crossing record is compared only to refuse.** The designation must declare
    `rollback_watermark_source.org_crossing_cross_check` (source `ORG_LEDGER_LINKED_RECEIPTS_ENDPOINT_HEAD`, the
    intr-destination path_ids, role `DIGEST_ONLY_CROSS_CHECK_NEVER_WATERMARK`). The reader obtains the Org's
    digest-only crossing records itself through `ORG_CROSSING_READER` (an injected reader at E0; in production,
    whatever the existing InTr readback exposes, currently UNKNOWN_NOT_AUTHENTICALLY_OBSERVED, so it is `None`).
    Caller input is never relied on. Each record carries `path_id`, `receipt_sha256`, `endpoint_head_sha256` and
    `supplied_hb_epoch`.
    - If a record names a head newer than KV's, or a head that is not an ancestor of KV's head, the read is DENY
      `KV_LEDGER_HEAD_ROLLBACK_DETECTED`. This refuses a whole-chain rollback that rewrote both `HEAD.json` and the
      head record.
    - If no crossing record is observable (no reader, reader error, malformed or empty result): when KV's chain
      shows it has never crossed (no `INTR_MESH_PATH_TRANSFER` or `INTR_MESH_PATH_INGRESS` record), the comparison
      is skipped and the read is ALLOW at E0. Otherwise it is six-field FAIL_CLOSED
      `KV_CROSSING_RECORD_NOT_OBSERVED` (class B, predicate `ORG_SIDE_OF_EACH_CROSSING_OBSERVED_BY_THE_READER`,
      owner .github#162), never ALLOW.
    - Both sides record each crossing (Lane B's rule at LLM-adapter#432 @c4cfc145, adopted, under the two-event
      model of ENVELOPE v2 line 55 @d749bb2). When the Org side is observed but an ingress crossing on KV's chain has
      no matching Org record, the read is FAIL_CLOSED `INTR_CROSSING_NOT_RECORDED_BY_BOTH_SIDES` (class B).
    - The Org never grants: the comparison result is echoed with authority NONE and can only refuse.
    - Residual limit, stated rather than hidden: a whole-storage rollback to a point before the first crossing,
      with no Org record observable, still reaches ALLOW at E0. That is what the ruling's never-crossed rule
      permits.
- **The SKAP chain is reached only through KV's InTr.** A read goes through `SkapLayer2Gate.receipt_ledger` with a
  layer-1 receipt minted by KV. Otherwise it is refused with `SKAP_RECEIPT_CHAIN_NOT_VIA_KV_INTR`.
- **Org designations are refused.** Any org ledger ref or git-ref designation is refused with
  `KV_RECEIPT_CHAIN_DESIGNATED_ON_ORG_LEDGER`.

## Production state: every read is FAIL_CLOSED

Every failure below is six-field: failure_code, failure_class, failed_predicate, required_evidence_or_repair,
retry_entrypoint, owning_existing_goal and next_attempt.

| failure_code | class | owner | next attempt |
|---|---|---|---|
| KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR | B | KV-CONNECTION-REVALIDATION-WORKER-001 (KV #2 SITE-CLOUD-KV-4347…) | on KV #2 governance and provider execution |
| KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED | B | this task; Lane B dependency | after the pin mechanism clears |
| KV_RECEIPT_CHAIN_GENESIS_PIN_MECHANISM_ORG_HOSTED | B | #162 / LLM-adapter#431 (Lane B) | on the per-endpoint pin aligned with SUPPLIED_HB_EPOCH |
| KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED | B | this task; TVC#542 head-signer pattern (Lane C) | on signer publication |

### The genesis pin

The genesis stays `null`. Once #431's genesis aligns with SUPPLIED_HB_EPOCH (StegVerse-Labs/.github#3263/#3290),
the pin is computed in advance. Pin-after-observe then remains only as the read-back check.

### Genesis crossing: the two-event model

SKAP_PORTABLE_ENVELOPE_V2_MIRROR_HANDOFF.md line 55 (@d749bb2) already matches CAPTURE's two-event crossing model,
and ENVELOPE v2 is not amended. The two events are:

1. The chain's REPOSITORY_LEDGER_INITIALIZATION genesis receipt is recorded in KV storage, at `_Vault/SKAP/Receipts`
   for SKAP and `_StegVerse/Receipts` for KV.
2. A digest-only InTr crossing receipt (pointer/digest plus SUPPLIED_HB_EPOCH) is appended to the Org ledger and read
   back.

The Org ledger's append and readback is the exactly-once fence for that crossing receipt only. The SKAP genesis itself
is never held on the Org ledger. The constant is `runtime.kv_receipt_ledgers.GENESIS_CROSSING`.

## LC-KV-09: the finish point's sealed predicates

LC-KV-09 (class A, StegVerse-Labs/.github#3330 `scoped-tasks/LC-KV-09.json` @7fb472a2) reseals
KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324) from `sha256:d68e239b...` to
`sha256:d4a98dc0c0ff9db7dbc05b1b97d93573dda7b59dcd2a7628e2cf6620e26c7ef2`. Four predicates join the sealed
`expected_evidence_predicates`, and `runtime.kv_skap_vault` (SCOPE_DIGEST, PREDICATES) evaluates each with real checks:

- `KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE`: the local exercise refuses KV access without a healthy-node ALLOW,
  and a healthy node gets a layer-1 receipt minted by `KVInterlockRuntime.handle` on the `INTR_DEVICE_KV` boundary.
  The evidence is the `access_constraints` row of the same name (`layer1_kv_access_receipts`).
- `SKAP_VAULT_REACHABLE_ONLY_VIA_INTR_FROM_KV`: an ungated bind, a direct read, a caller-asserted InTr ref and an
  ungated reconstruct are all refused (`SKAP_ACCESS_LAYER2_REFUSED`). The evidence is `layer2_skap_access_receipts`.
- `SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT`: SKAP entry with a forged or missing layer-1 prior is refused.
  The evidence is each layer-2 `prior_receipt_hash` equalling its layer-1 KV-access receipt.
- `ENDPOINT_NOT_A_GITHUB_ORGANIZATION_MEMBER`: reuses this PR's closed membership schema (`_closed_schema`,
  `_org_membership`, `_org_designation`). Membership probes must be refused, and both digest-pinned contracts must
  load through `designation()`. It is decided at E0 without evidence.

Each access row now fails its own sealed predicate as well as the predicate it was mapped to before the reseal
(`ACCESS_CONSTRAINT_PREDICATE`, kept). In production the three access predicates are FAIL_CLOSED, class B, because no
access receipts are observed. `ENDPOINT_NOT_A_GITHUB_ORGANIZATION_MEMBER` is ALLOW. With the E0 evidence fixture all
13 predicates are ALLOW.

## E0 testing

The E0 tests use the documented `device-local` storage endpoint (LOCAL_ROOT, `resident-device-local`). It points at
a TEST-ONLY scratch KV root, outside the KV #2 lineage. Production files are never touched.
