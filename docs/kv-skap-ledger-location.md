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

- KV's own `repository_ledger_location` keys, with KV-owned values: repository
  `STEGVERSE_KV`, ref `KV_INTR_ENDPOINT`, and the location above as the namespace;
- KV's own `ledger_designation` (schema `stegverse.endpoint-ledger-designation/v1`).

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
org-membership, team or app-installation binding, and no org ref. KV is its own ledger-holding party; an Org↔KV crossing is between distinct parties (never an intra-org hop) and is recorded on both ledgers, KV's end required (StegVerse-org/.github#162 c6394603737). The Org→KV intr-destination path_ids in org_crossing_cross_check.path_ids designate that crossing, a legitimate InTr crossing between distinct parties (LC-KV-29): the Org's end is read by ORG_CROSSING_READER and KV's end is written by runtime/kv_crossing_records.py. A contract that binds any of these is refused with six-field
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
    `runtime/org_crossing_reader.py` (LC-KV-26, the Org end), which reads an anonymously fetched snapshot of the
    public Org ledger supplied by `STEGVERSE_ORG_LEDGER_SNAPSHOT` and written by the observer
    `tools/observers/org_ledger_observer.py`. The reader is clock-free and network-free and verifies every seal and
    the chain from `HEAD.json`. It emits only records whose path_id is `<OrgA>-><OrgB>:intr-destination` between
    distinct orgs and that already carry `endpoint_head_sha256`; it never fabricates one. With no snapshot, or a
    snapshot that fails to verify, it returns `None` and records the six-field FAIL_CLOSED
    `KV_CROSSING_RECORD_NOT_OBSERVED` / `ORG_SIDE_OF_EACH_CROSSING_OBSERVED_BY_THE_READER` in `LAST_READ`).
    SKAP Vault inside KV is the only PII and credential store for every user, the ecosystem's own included; the
    ecosystem holds none (HST citation pending P1 #163).
    Caller input is never relied on. Each record carries `path_id`, `receipt_sha256`, `endpoint_head_sha256` and
    `supplied_hb_epoch`.
    - If a record names a head newer than KV's, or a head that is not an ancestor of KV's head, the read is DENY
      `KV_LEDGER_HEAD_ROLLBACK_DETECTED`. This refuses a whole-chain rollback that rewrote both `HEAD.json` and the
      head record.
    - If no crossing record is observable (no reader, reader error, malformed or empty result) and the chain has
      crossed, the read is six-field FAIL_CLOSED `KV_CROSSING_RECORD_NOT_OBSERVED` (class B, predicate
      `ORG_SIDE_OF_EACH_CROSSING_OBSERVED_BY_THE_READER`, owner .github#162), never ALLOW. A never-crossed chain is
      no longer skipped (LC-KV-26, below).
    - Both sides record each crossing (Lane B's rule at LLM-adapter#432 @c4cfc145, adopted, under the two-event
      model of ENVELOPE v2 line 55 @d749bb2). When the Org side is observed but an ingress crossing on KV's chain has
      no matching Org record, the read is FAIL_CLOSED `INTR_CROSSING_NOT_RECORDED_BY_BOTH_SIDES` (class B).
    - The Org never grants: the comparison result is echoed with authority NONE and can only refuse.
    - **Both ends (LC-KV-26, closed).** Coordination's rule, relayed to P1 at 05:03Z: "a crossing record held at
      both ends (the org side and KV's own ledger), never an InTr hop inside one org" (#167 c6393119202). A
      read-back head is ALLOW only when it is the newest head in KV's own head record and an observed Org
      digest-only crossing record names it (`endpoint_head_sha256`). Otherwise the read is six-field FAIL_CLOSED
      `KV_CROSSING_RECORD_NOT_OBSERVED` (class B, predicate `KV_HEAD_RECORDED_AT_BOTH_ENDS`, owner .github#162).
      This closes the two whole-store rollbacks (receipts, `HEAD.json` and KV's head record rolled back together),
      for kv and for SKAP through `SkapLayer2Gate`:
      1. **Rollback to before the first crossing.** A never-crossed chain with no Org record is FAIL_CLOSED, not
         skipped. Once the Org side records a head (the genesis/first-head crossing), a rollback behind it is DENY
         `KV_LEDGER_HEAD_ROLLBACK_DETECTED`.
      2. **Rollback to after the last crossing, with the internal heads rolled back and the crossed head kept**
         (P1, joint review of #263 @34496af5: `WHOLE_STORE_AFTER_LAST_CROSSING_INTERNAL_HEADS_ROLLED_BACK`). An
         internal head held only at KV's end was never readable, so no reader relied on a head that a rollback
         could drop. Once it is held at both ends, dropping it is DENY `KV_LEDGER_HEAD_ROLLBACK_DETECTED`, with or
         without a caller claim.
      - The Org record stays digest-only and refuse-only; it never grants and is never the watermark. This declares no
        Org→KV path: KV is its own ledger-holding party; an Org↔KV crossing is between distinct parties (never an intra-org hop) and is recorded on both ledgers, KV's end required (StegVerse-org/.github#162 c6394603737). The Org→KV intr-destination path_ids in org_crossing_cross_check.path_ids designate that crossing, a legitimate InTr crossing between distinct parties (LC-KV-29): the Org's end is read by ORG_CROSSING_READER and KV's end is written by runtime/kv_crossing_records.py. The SKAP Vault is reached only through the in-KV gate. SKAP invariant (Labs `docs/FEDERATION_DIRECTORY.md:3`): "SKAP Vault
        inside KV is the only PII and credential store for every user, the ecosystem's own included; the ecosystem
        holds none (HST citation pending P1 #163)."
      - Witnesses: case 1, `test_lc_kv_23_whole_chain_rollback_is_refused_by_the_org_crossing_record`; case 2,
        `test_lc_kv_26_rollback_after_the_last_crossing_is_refused_both_ends`.
      - Under Coordination's ruling, a crossing record ahead of the KV head is DENY
        `KV_LEDGER_HEAD_ROLLBACK_DETECTED`. That is the only code for it, with no alias.
- **The SKAP chain is reached only from inside KV.** A read goes through `SkapLayer2Gate.receipt_ledger` (the
  in-KV gate, never an InTr hop) with a layer-1 receipt minted by KV. Otherwise it is refused with `SKAP_RECEIPT_CHAIN_NOT_FROM_INSIDE_KV`.
- **Org designations are refused.** Any org ledger ref or git-ref designation is refused with
  `KV_RECEIPT_CHAIN_DESIGNATED_ON_ORG_LEDGER`.

## Production state: every read is FAIL_CLOSED

Every failure below is six-field: failure_code, failure_class, failed_predicate, required_evidence_or_repair,
retry_entrypoint, owning_existing_goal and next_attempt.

| failure_code | class | owner | next attempt |
|---|---|---|---|
| KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR | B | KV-CONNECTION-REVALIDATION-WORKER-001 (KV #2 SITE-CLOUD-KV-4347…) | on KV #2 governance and provider execution |
| KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED | B | LC-KV-27 (KV-owned genesis pin) under this task | on KV's own genesis receipt on its storage endpoint (after LC-KV-28), then the admitted cvk pin change |
| KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED | B | this task; TVC#542 head-signer pattern (Lane C) | on signer publication |

### The genesis pin

The genesis stays `null` until KV's own genesis receipt exists. The pin is KV-owned (LC-KV-27). The withdrawn
org-hosted planner row (KV_RECEIPT_CHAIN_GENESIS_PIN_MECHANISM_ORG_HOSTED) is removed: KV's own ledger is never on an
Org ledger ref, and no InTr hop inside an org is involved.

`runtime.kv_receipt_ledgers.plan_genesis_pin(which, storage_endpoint, readback_root, hb_epoch=...)` reads KV's own
chain back from the designated storage endpoint. It requires a hash-intact REPOSITORY_LEDGER_INITIALIZATION genesis
whose `hb_reference` carries the supplied HB epoch (SUPPLIED_HB_EPOCH, the shared supplied-epoch rule). It returns
that receipt_sha256 for both `repository_ledger_location.expected_genesis_receipt_sha256` and
`ledger_designation.expected_genesis_receipt_sha256`. It writes nothing. An admitted continuity-vault-kit change sets
the two fields, and the `contract_sha256` pin moves with them. A fabricated digest is not evidence.

In production the planner fails closed on KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR (LC-KV-28) until KV #2 has
provider execution. Pin-after-observe stays as the read-back check.

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

The no-intra-org-InTr reseal then moves it to
`sha256:95f060fcc2b2455908c838fbcada36eb80b05cad2bf15b8a0b9607cd4672d9dc`: the layer-2 predicate is renamed
`SKAP_VAULT_REACHABLE_ONLY_FROM_INSIDE_KV`. InTr runs only between distinct orgs, and the SKAP Vault sits inside KV, so
KV reaching it is the in-KV gate `KV_INTERNAL_SKAP_GATE`, never an InTr hop.


- `KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE`: the local exercise refuses KV access without a healthy-node ALLOW,
  and a healthy node gets a layer-1 receipt minted by `KVInterlockRuntime.handle` on the `INTR_DEVICE_KV` boundary.
  The evidence is the `access_constraints` row of the same name (`layer1_kv_access_receipts`).
- `SKAP_VAULT_REACHABLE_ONLY_FROM_INSIDE_KV`: an ungated bind, a direct read, a caller-asserted InTr ref and an
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

## KV's end of an Org->KV crossing (`runtime/kv_crossing_records.py`)

KV is its own ledger-holding party, so a crossing between an org and KV is between two distinct parties and is recorded
on both ledgers, KV's end required (StegVerse-org/.github#162 c6394603737). `plan_crossing_record` and
`append_crossing_record` are KV's end: one digest-only `INTR_MESH_PATH_INGRESS` receipt on KV's own `kv` chain
(`_StegVerse/Receipts`), pointing at the Org's record by digest (`source_repository_receipt_sha256`), at a supplied HB
epoch (no clock), in the shape `_org_crossing` already checks. The Org's end is never written here; it is read only by
`ORG_CROSSING_READER`, which stays refuse-only.

Exactly one receipt per crossing, identified by `(path_id, communication_id)`. Rigel's rule (2026-10-29 3:08 PM CDT,
Lane B's chat, relayed at StegVerse-org/.github#162 c6508050206): "This shouldn't be possible without being a literal
duplicate." A second record for the same crossing is refused, six-field FAIL_CLOSED
`INTR_PATH_DESTINATION_CROSSING_ALREADY_RECORDED` (the Org side's code, StegVerse-org/.github#261), literal duplicate or
not. There is no newest-wins and no replacement policy. The check is made again under the append lock.

Not here: the SKAP chain (reached only from inside KV, no InTr hop, so refused), any key handling (the head is signed by
the published `kv_ledger_head_signer`, never by this module), any dispatch or clock, and any designation of an Org->KV `intr-destination`
path_id (the contract designates them, `org_crossing_cross_check.path_ids`; a new one is a separate admitted change). Production is FAIL_CLOSED on KV #2
(`KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR`) before anything is read or written.

A crash between the receipt write and the `HEAD.json` update leaves an orphan receipt file (P4's note on
continuity-vault-kit#284). Before writing, the writer looks at every `receipts/*.json`, chained or not, for the same
crossing (same `(path_id, communication_id)` or the same Org record digest). A chained one is the duplicate refusal above.
An unchained one is adopted only if it is byte-identical to the receipt this call would write now (same supplied epoch, on
the current head), in which case only `HEAD.json` and the head record are written; otherwise it is refused, six-field
FAIL_CLOSED `INTR_PATH_DESTINATION_CROSSING_ORPHAN_RECEIPT_NOT_ADOPTABLE` (a file that is not a receipt of its own name:
`KV_CROSSING_RECEIPT_FILE_UNREADABLE`). Nothing is written or deleted in a refusal. The receipt file is created whole or
not at all (written beside, then linked into place), so a stop never leaves half a receipt. A crossing never has two
receipt files; the owner repairs an unadoptable orphan.

Store errors and stray temp files (P4's non-blocking notes on continuity-vault-kit#284 and #285):

- An `OSError` of the store (the lock, a read under it, a write, a sync, the hard link, a replace) returns a six-field
  FAIL_CLOSED refusal and never raises: `KV_STORAGE_ENDPOINT_HARDLINK_UNSUPPORTED` (D), `KV_CROSSING_RECORD_STORE_WRITE_FAILED`
  (D), `KV_CROSSING_RECORD_STORE_LOCK_FAILED` (D), `KV_CROSSING_RECORD_STORE_READ_FAILED` (D),
  `KV_CROSSING_RECEIPT_FILE_ALREADY_PRESENT` (C, a name that appeared after the plan; never overwritten). `stopped_at` names
  the exact step (`write_receipt`, `sync_receipt`, `link_receipt`, `write_head_json`, `sync_head_json`, `replace_head_json`,
  `write_head_record`, `sync_head_record`, `replace_head_record`, `open_lock`, `flock`, `read_plan`, `read_under_lock`,
  `read_head_record`), and `chain_state` with `receipt_file_written` / `head_json_written` / `head_record_written` /
  `ledger_written` (true only once HEAD.json names the receipt) state the chain as it really is. The head record is read
  before anything is written.
  - `UNCHANGED`: nothing reached the chain; a retry at the same supplied epoch writes the record.
  - `ORPHAN_RECEIPT_FILE_ONLY` (the receipt file is on disk, HEAD.json and the head record are not): a retry at the same
    epoch adopts the byte-identical orphan; a retry at any other epoch is refused as a non-adoptable orphan.
  - `HEAD_JSON_AHEAD_OF_HEAD_RECORD` (HEAD.json names the new receipt, the head record lacks it): no retry at any epoch
    writes or adopts anything; every call is refused `KV_LEDGER_HEAD_ROLLBACK_DETECTED` until the owner repairs the head
    record. The refusal says so and offers no same-epoch retry.
- A `.kv-crossing-*` temp file left by a hard kill is never read as a receipt, and this writer never deletes anything in the
  store. They are ignored when scanning and listed in `stray_temp_files` of the plan, the append result and every refusal
  (and in a refusal's `detail`) so an operator can see them. The writer's own lock file is not a stray.
- A torn or misnamed file in `receipts/` blocks every new crossing, not only its own, until the owner repairs it. This is
  intentional and fail-closed (its crossing id cannot be read, so no new record can show it leaves that one with a single
  receipt file). No behaviour change.
