# KV-SKAP-VAULT-FUNCTIONAL-001: ladder conformance (LC-KV) and the Org InTr endpoint model

Goal: KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324). Lowest supported mode: E0. This note answers P1's
DENY on continuity-vault-kit#258 @61104a57 (StegVerse-Labs/.github#3330 @578583be; StegVerse-org/.github#163).

## What each finding now enforces

| Finding | Enforced in | Negative tests |
|---|---|---|
| LC-KV-10: layer 2 re-checks the evaluator pin | `runtime.kv_skap_layer2.SkapLayer2Gate._verify_kv_access_receipt` calls `runtime.kv_interlock_endpoint.layer1_receipt_conformance` (the same pin `_check_layer1` uses: id `PINNED_HEALTHY_NODE_EVALUATOR_ID`, source sha256 `fdaa2005…1f58`) and accepts only an exact `KVInterlockRuntime` | injected evaluator, edited pin fields, subclassed runtime, receipt minted under other trust anchors |
| LC-KV-15: ledger by contract location at an observed head; identity from InTr; real transport state | `bind_healthy_node_ledger`, `_access_context`, `observe_intr_transport` | scratch ledger root / bare dir / unbound dict (also under production anchors), unpinned and foreign genesis, transport absent or not INSTALLED, unenrolled and mis-claimed identity |
| Steering 2: anchored temporary node ledger | `verify_node_ledger_anchor` (failure_code `TEMP_NODE_LEDGER_NOT_ANCHORED`) | no anchor, mismatched node_identity_key, mismatched genesis, health receipts without the pinned digests, unissued / edited / non-org issuer |
| LC-KV-07: gated `read_stream` and `append_extension` | `execution/vault_store.py`: public appends refuse SKAP records; `read_stream` refuses SKAP streams; the gated read verifies every SKAP record's provenance at the gate (`bind_payload` / `verify_payload`) | append_extension/append_receipt with SKAP records; forged records written to the file (payload swap under a real receipt, replay, fabricated hashes, no access block) |
| LC-KV-03: custody verifier is the real layer-2 gate | `validate_vault_lineage_custody_result` → `_require_access_layers` → `pinned_layer2_gate` | arbitrary callables, lenient gate subclasses and their bound methods |
| LC-KV-08 | not changed here (class C, TV/TVC and Lane C) | reported as a six-field FAIL_CLOSED |

Tests: `tests/test_kv_ladder_conformance_lc_kv.py` plus the updated suites; 0 skipped.

## Trust anchors and E0

`runtime.kv_interlock_endpoint.TRUST_ANCHORS` is the only seam. Production: label `PRODUCTION`, no pinned genesis, no
installed InTr transport, no NODE_LEDGER_OPENED issuer verifiers. The real path therefore FAILS_CLOSED
(`HEALTHY_NODE_LEDGER_NOT_ONBOARDED` / `HEALTHY_NODE_LEDGER_GENESIS_NOT_PINNED` / `INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED`)
until StegVerse-Labs/.github#3255 and StegVerse-org/LLM-adapter#429/#431 are admitted and Lane B's transport exists.
The E0 stand-ins (`tests/kv_two_layer_e0.py`, label `E0_STANDIN_TEST_ONLY_NOT_EVIDENCE`) are in force only inside
setUpModule/tearDownModule or a context manager. Receipts carry `trust_anchors_label`; layer 2 and the finish point
refuse receipts minted under other anchors, so the production CLI refuses E0 evidence.

## NODE_LEDGER_OPENED anchor (minimal; PENDING Lane B's schema)

`schema` = `stegverse.node-ledger-opened/PENDING_LANE_B_SCHEMA`, `transition_class` = `NODE_LEDGER_OPENED`, `node_id`,
`node_identity_key`, `genesis_receipt_sha256`, `issuer` ∈ {`ORGANIZATION_LEDGER`, `TV/TVC`}, `issuer_receipt_ref`,
`receipt_sha256` (sha256 of the canonical JSON without `receipt_sha256`). Health receipts on the temporary ledger carry
`evidence.pinned_digests` = {`evaluator_source_sha256`, `producer_source_sha256`}. No IDs are invented; Lane B's schema
replaces this shape.

## Org InTr endpoint model (steering 3, PENDING Lane B's endpoint_kind schema)

The Org InTr model reuses INTR_MESH_PATH_TRANSFER, ORGANIZATION_INTR_DESTINATION_INGRESS, intr_path_ingress and
protocol.json with an `endpoint_kind` of ORG, KV, SKAP_VAULT, PERMANENT, EPHEMERAL or GATEWAY. continuity-vault-kit
references none of those class names today, so only the kinds are declared (`ENDPOINT_KINDS`,
`ENDPOINT_KIND_SCHEMA = PENDING_LANE_B_ENDPOINT_KIND_SCHEMA`) and only two fields are used: `endpoint_kind` and the
ledger binding.

* KV-access receipts carry `endpoint_kind: KV`; SKAP-access receipts carry `endpoint_kind: SKAP_VAULT` (reached only via
  InTr from inside KV, so they also record `layer1_endpoint_kind: KV`).
* The ledger binding is `ORG` (contract location at an observed org-ledger head) or `EPHEMERAL` (a temporary ledger a
  StegApp, StegBrowser or StegNode generated through StegOS, anchored by NODE_LEDGER_OPENED at generation).
* The rest (KV's and the SKAP Vault's own ledgers, ingress/egress through intr_path_ingress) is FAIL_CLOSED
  `ENDPOINT_KIND_SCHEMA_PENDING`, class B, retry = Lane B's endpoint_kind schema draft.

## Naming (documentation only; nothing is renamed)

* `_<org>` names an Org: a coordination of data as presented, e.g. MyKV WorkSpace.
* `##_<name>` names a storage surface that Orgs interact with. The `##` prefix only keeps data-location names distinct
  for human review; it carries no semantics.

## Residual risk

Ledger receipts are unsigned (TVC#537) and TVC `build_chain` self-asserts its hops (LC-KV-08). A forged local copy of
the org-ledger repository that keeps the real genesis and appends forged receipts is not detectable by KV until signed
receipts exist. Gate payload bindings (`bind_payload`) are in-memory, so gated reads do not verify across a process
restart until durable custody exists (TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001).
