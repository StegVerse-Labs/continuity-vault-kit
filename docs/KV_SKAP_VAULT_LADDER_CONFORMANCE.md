# KV-SKAP-VAULT-FUNCTIONAL-001: ladder conformance (LC-KV) and the Org InTr endpoint model

Goal: KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324). Lowest supported mode: E0. This note answers P1's
DENYs on continuity-vault-kit#258 (StegVerse-Labs/.github#3330 @578583be and rev 4 @c8b8d156; StegVerse-org/.github#163)
and binds layer 1 to Lane B's evaluate_anchored (StegVerse-org/LLM-adapter#432 @1cbad77e, vendored byte-identical in
`runtime/intr_pinned/`, see `runtime/intr_pinned/PINNED.md`).

## Admission order (LC-KV-03, tracked by P1 as LC-KV-05)

`runtime.kv_skap_vault.ADMISSION_ORDER`, recorded on every finish-point verdict: continuity-vault-kit#258 and #259 are
admitted together (ADMITTED_TOGETHER), never one without the other.

## What each finding now enforces

| Finding | Enforced in | Negative tests |
|---|---|---|
| LC-KV-10 (rev 4, class A): the decider is pinned by identity, never by name | `load_pinned_intr` compiles the vendored modules from the digest-checked bytes; `pinned_decider_identity` requires `decider is` the loaded `evaluate_anchored` and the sha256 of a deterministic view of its code object (bytecode, constants, names; not marshal, whose output depends on reference counts) equal to the one recorded at load. Layer 1 refuses any other decider (`LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED`); `layer1_receipt_conformance` (layer 2 and the finish point) re-checks ids, source and code digests; layer 2 also refuses a runtime whose decider is no longer the pinned object, and accepts only an exact `KVInterlockRuntime` | spoofed `__module__`/`__qualname__`/`co_filename`, bare `evaluate`, a re-wrapped copy of the pinned code, injected callables, edited pin and code-digest fields, decider swapped after minting, subclassed runtime, receipt minted under other trust anchors |
| Layer 1 goes through evaluate_anchored | `KVInterlockRuntime._evaluate_health` calls the pinned `evaluate_anchored` with the deployment's endpoint, the org-ledger root at the observed head and its HEAD pin, the observed transport state and `require_admission=True` | a foreign-producer ledger that bare `evaluate` ALLOWs is refused `EPHEMERAL_NODE_LEDGER_NOT_ANCHORED`; spy on `verify_anchor`; unanchored root; key mismatch |
| LC-KV-15 (rev 4, class B): anchors from receipts, not constants | `bind_healthy_node_ledger` reads `refs/stegverse/organization-ledger` at the observed head, materializes `repository-ledger/StegVerse-org/LLM-adapter` and derives the genesis from that chain's own initialization receipt (`_org_genesis_failure`); `TRUST_ANCHORS` holds only the label and the observed transport | scratch root / bare dir / unbound dict, genesis labelled for other anchors, edited genesis receipt fields, transport absent or not INSTALLED, unenrolled and mis-claimed identity |
| LC-KV-13: the finish point expects a PERMANENT node | `_check_layer1` (`LAYER1_NODE_NOT_THE_PERMANENT_ENDPOINT_THE_FINISH_POINT_EXPECTS`) | an EPHEMERAL node binds at layer 1 but does not complete the finish point |
| LC-KV-07: gated `read_stream` and `append_extension` (now owned by TV/TVC; unchanged here) | `execution/vault_store.py` | as before |
| LC-KV-03: custody verifier is the real layer-2 gate | `validate_vault_lineage_custody_result` → `_require_access_layers` → `pinned_layer2_gate` | arbitrary callables, lenient gate subclasses and their bound methods |
| LC-KV-08, LC-KV-16 | not changed here (TV/TVC and Lane C; Lane B owns evaluate_anchored's holes) | reported as six-field FAIL_CLOSED |

Tests: `tests/test_kv_ladder_conformance_lc_kv.py` plus the updated suites; 0 skipped. Stdlib only: no test or runtime
file of #258 imports `cryptography` (the SKAP persistence tests use a static synthetic sealed fixture,
`tests/fixtures/skap_sealed_material.synthetic.json`; the stdlib Ed25519 verify is vendored from #430/#432).

## Trust anchors and E0

`runtime.kv_interlock_endpoint.TRUST_ANCHORS` is the only seam: label `PRODUCTION` and no installed InTr transport. No
genesis or issuer constant exists. The real path therefore FAILS_CLOSED (`HEALTHY_NODE_LEDGER_NOT_ONBOARDED` /
`HEALTHY_NODE_LEDGER_GENESIS_NOT_DERIVABLE` / `INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED`) until StegVerse-Labs/.github#3255
and StegVerse-org/LLM-adapter#431 are admitted and Lane B's transport exists. The E0 stand-ins (`tests/kv_two_layer_e0.py`,
label `E0_STANDIN_TEST_ONLY_NOT_EVIDENCE`) are in force only inside setUpModule/tearDownModule or a context manager.
Receipts carry `trust_anchors_label`; layer 2 and the finish point refuse receipts minted under other anchors.

## Org InTr endpoint model (#432 v1)

`endpoint_kind` is taken from Lane B's published `schemas/endpoint-kind.v1.json` (`$defs.endpoint_kind.enum`, read
from the digest-checked vendored bytes; never a hand-written list): EPHEMERAL, PERMANENT, GATEWAY, KV, SKAP_VAULT, ORG
(`ENDPOINT_KINDS`, equal to #432's). Schemas (all vendored at 1cbad77e): `stegverse.endpoint-kind/v1`,
`stegverse.endpoint-ledger-genesis/v1`, `stegverse.endpoint-ledger-anchor/v1` (PERMANENT, KV, SKAP_VAULT anchor body),
`stegverse.node-ledger-opened/v1` (the issued anchor; only it carries `issuer` and `issuer_receipt_ref`),
`stegverse.node-ledger-opened-signed/v1` (the signed envelope) and `stegverse.node-ledger-opened-generation/v1` (StegOS's
generation record for an EPHEMERAL node: a temporary StegApp/StegBrowser/StegNode). `node_identity_key` is the 5-field
object (algorithm, custody, key_id, node_id, public_key_b64). GATEWAY roots derive from the org root; ORG is never a node
root. The endpoint-kind schema is no longer pending (closed with #432 @1cbad77e).

* EPHEMERAL anchors must be signed envelopes whose key is published in
  `.stegverse/node-ledger/node-ledger-opened-signers.v1.json`. That file is empty (TV/TVC custody publishes it), so an
  EPHEMERAL node is a six-field FAIL_CLOSED `EPHEMERAL_NODE_LEDGER_NOT_ANCHORED` / `NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED`,
  class B, owner TV/TVC. This does not block the finish point, which completes with a PERMANENT node (LC-KV-13).
* Pins: health receipts carry no per-receipt `evidence.pinned_digests` (adding them would change producer 21249f25). The
  pins are bound in the genesis; KV checks the `anchor.pinned_digests` evaluate_anchored returns on ALLOW against
  `PINNED_DIGESTS_FROM_GENESIS` (evaluator fdaa2005, producer 21249f25).
* KV-access receipts carry `endpoint_kind: KV`; SKAP-access receipts carry `endpoint_kind: SKAP_VAULT` and
  `layer1_endpoint_kind: KV`.
* The ledger binding is `ANCHORED_ENDPOINT_LEDGER`: the org ledger by contract location plus the node endpoint, its
  anchored genesis and key, and the anchor evaluate_anchored returned.

## Naming (documentation only; nothing is renamed)

* `_<org>` names an Org: a coordination of data as presented, e.g. MyKV WorkSpace.
* `##_<name>` names a storage surface that Orgs interact with. The `##` prefix only keeps data-location names distinct
  for human review; it carries no semantics.

## Residual risk

Ledger receipts are unsigned (TVC#537) and TVC `build_chain` self-asserts its hops (LC-KV-08). A forged local copy of
the org-ledger repository that keeps the real genesis and appends forged receipts is not detectable by KV until signed
receipts exist. Gate payload bindings (`bind_payload`) are in-memory, so gated reads do not verify across a process
restart until durable custody exists (TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001). A store-local hash chain of those
bindings was considered and not added: whoever can write the vault directory can rewrite such a chain end to end, so
restoring gate provenance from it on load would turn a local file into authority. `KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND`
stays until a bound durable custody location exists.
