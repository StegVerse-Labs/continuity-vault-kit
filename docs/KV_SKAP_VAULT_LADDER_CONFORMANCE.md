# KV-SKAP-VAULT-FUNCTIONAL-001: ladder conformance (LC-KV) and the Org InTr endpoint model

Goal: KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324). Lowest supported mode: E0. This note answers P1's
DENYs on continuity-vault-kit#258 (StegVerse-Labs/.github#3330 @578583be and rev 4 @c8b8d156; StegVerse-org/.github#163)
and binds layer 1 to Lane B's evaluate_anchored (StegVerse-org/LLM-adapter#432 @74509fec, code identical to @a2ee67e6 except the GENESIS_NOT_PINNED next_attempt, which names REPOSITORY_LEDGER_GENESIS_PIN, vendored byte-identical in
`runtime/intr_pinned/`, see `runtime/intr_pinned/PINNED.md`).

## Admission order (LC-KV-03, tracked by P1 as LC-KV-05)

`runtime.kv_skap_vault.ADMISSION_ORDER`, recorded on every finish-point verdict: continuity-vault-kit#258 and #259 are
admitted together (ADMITTED_TOGETHER), never one without the other.

## What each finding now enforces

| Finding | Enforced in | Negative tests |
|---|---|---|
| LC-KV-10 (rev 4, class A): the decider is pinned by identity, never by name | `load_pinned_intr` compiles the vendored modules from the digest-checked bytes; `pinned_decider_identity` requires `decider is` the loaded `evaluate_anchored` and the sha256 of a deterministic view of its code object (bytecode, constants, names; not marshal, whose output depends on reference counts) equal to the one recorded at load. Layer 1 refuses any other decider (`LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED`); `layer1_receipt_conformance` (layer 2 and the finish point) re-checks ids, source and code digests; layer 2 also refuses a runtime whose decider is no longer the pinned object, and accepts only an exact `KVInterlockRuntime` | spoofed `__module__`/`__qualname__`/`co_filename`, bare `evaluate`, a re-wrapped copy of the pinned code, injected callables, edited pin and code-digest fields, decider swapped after minting, subclassed runtime, receipt minted under other trust anchors |
| Layer 1 goes through evaluate_anchored | `KVInterlockRuntime._evaluate_health` calls the pinned `evaluate_anchored` with the deployment's endpoint, the org-ledger root at the observed head and its HEAD pin, the observed transport state and `require_admission=True` | a foreign-producer ledger that bare `evaluate` ALLOWs is refused `EPHEMERAL_NODE_LEDGER_NOT_ANCHORED`; spy on `verify_anchor`; unanchored root; key mismatch |
| LC-KV-15 (rev 4 and rev 6, class B): anchors from receipts, not constants; the only ALLOW path | `bind_healthy_node_ledger` reads `refs/stegverse/organization-ledger` at the observed head and materializes `repository-ledger/StegVerse-org/LLM-adapter`; evaluate_anchored (#432 @a2ee67e6) accepts the store only at the #431 contract's pinned genesis with a published append-route head attestation (KV's own genesis derivation was dropped as a duplicate); `TRUST_ANCHORS` holds only the label and the observed transport | scratch root / bare dir / unbound dict; an unlabelled (rev 6) or labelled caller-created store inside E0 (`ORG_LEDGER_GENESIS_MISMATCH`); #431's contract without a pinned genesis (`ORG_LEDGER_GENESIS_NOT_PINNED`); `LcKv15OnlyAllowPath`: the ALLOW reads the contract-located, genesis-pinned, route-attested store, and removing any one leg leaves no ALLOW; transport absent or not INSTALLED, unenrolled and mis-claimed identity |
| LC-KV-16 class: a caller-named store or a caller-appended ingress record never reaches ALLOW through KV's wrapper | inside evaluate_anchored (#432 @a2ee67e6); KV passes only the deployment's store and attestation, and a requester can cite only a report receipt | `LcKv16CallerStoreAndIngressNeverAllow`: unattested head, caller-key attestation, replayed route attestation, attestation for another location (`ORG_LEDGER_HEAD_NOT_AUTHENTICATED`); no admitted route (`MERGE_APPEND_PATH_NOT_ADMITTED`); ingress record without its InTr carrier (`INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED` / `INTR_CARRIER_NOT_ON_AUTHENTICATED_ORG_LEDGER`); requester-supplied attestation |
| LC-KV-18 (class B, owner TV/TVC + Lane C): `org-ledger-head-signers.v1.json` is empty and gates every PERMANENT anchor | `org_ledger_prerequisites()`, recorded on every finish-point verdict as `org_ledger_prerequisites` (six fields per unmet leg, with #431's location and genesis legs) | `LcKv18OrgLedgerPrerequisites` |
| LC-KV-13: the finish point expects a PERMANENT node | `_check_layer1` (`LAYER1_NODE_NOT_THE_PERMANENT_ENDPOINT_THE_FINISH_POINT_EXPECTS`) | an EPHEMERAL node binds at layer 1 but does not complete the finish point |
| LC-KV-07: gated `read_stream` and `append_extension` (now owned by TV/TVC; unchanged here) | `execution/vault_store.py` | as before |
| LC-KV-03: custody verifier is the real layer-2 gate | `validate_vault_lineage_custody_result` → `_require_access_layers` → `pinned_layer2_gate` | arbitrary callables, lenient gate subclasses and their bound methods |
| LC-KV-08 | not changed here (TV/TVC and Lane C) | reported as six-field FAIL_CLOSED |

Tests: `tests/test_kv_ladder_conformance_lc_kv.py` plus the updated suites; 0 skipped. Stdlib only: no test or runtime
file #258 adds or changes imports `cryptography` (the SKAP persistence tests use a static synthetic sealed fixture,
`tests/fixtures/skap_sealed_material.synthetic.json`; the stdlib Ed25519 verify is vendored from #430/#432).

### Reproduce without `cryptography` (P1)

cvk declares no Python dependencies (there is no pyproject.toml, setup.cfg, setup.py or requirements file).
`cryptography` is undeclared: it is installed ad hoc by `.github/workflows/runtime-import-and-secret-policy.yml` and
`kv-guardrails.yml` (both already on main), and imported only by `skap/browser_ingress.py`, `skap/browser_admission.py`,
`skap/crypto_boundary.py`, `skap/portable_envelope.py` and the tests that reach them (`test_skap_browser_admission`,
`test_skap_browser_ingress`, `test_skap_crypto_boundary`, `test_skap_crypto_lifecycle_runtime`,
`test_skap_owner_ingress`, `test_skap_portable_envelope`, `test_skap_tvc_key_provider`). None of those is in either set
below; no module of either set imports it directly or transitively (checked by import and by running both sets with
`import cryptography` failing).

```
python3 -m venv /tmp/cvk-clean
/tmp/cvk-clean/bin/python -c "import cryptography"   # must fail: ModuleNotFoundError
# 1. stdlib only (unittest), 0 skipped
/tmp/cvk-clean/bin/python -m unittest tests.test_kv_interlock_runtime_endpoint tests.test_endpoint_fanout_probe tests.test_kv_skap_vault_finish_point tests.test_kv_skap_vault_e0_witnesses tests.test_sovereign_kv_vault_lineage_record tests.test_skap_kv_persistence tests.test_vault_store tests.test_task_registry_event_sovereign_kv_binding tests.test_kv_interlock_contract tests.test_kv_interlock_intr_envelope tests.test_kv_skap_account_transfer tests.test_portable_direct_source_ingress tests.test_portable_directory_projection tests.test_kv_provider_operation_store tests.test_storage_endpoint_v2 tests.test_communication_runtime tests.test_cross_edge_selection_receipt tests.test_kv_auri_peripheral_profiles tests.test_skap_intr_reconstruction tests.test_skap_loader_js tests.test_kv_ladder_conformance_lc_kv
# 2. the selected set: needs only the pytest runner (7 of its files import pytest), still no cryptography
/tmp/cvk-clean/bin/pip install pytest
/tmp/cvk-clean/bin/python -m pytest -q -rs tests/test_kv_interlock_runtime_endpoint.py tests/test_endpoint_fanout_probe.py tests/test_kv_skap_vault_finish_point.py tests/test_kv_skap_vault_e0_witnesses.py tests/test_sovereign_kv_vault_lineage_record.py tests/test_skap_kv_persistence.py tests/test_vault_store.py tests/test_persistent_session_interlock.py tests/test_kv_storage_provider_adapter.py tests/test_task_registry_event_sovereign_kv_binding.py tests/test_kv_interlock_contract.py tests/test_kv_interlock_intr_envelope.py tests/test_kv_skap_account_transfer.py tests/test_secret_field_policy.py tests/test_portable_direct_source_ingress.py tests/test_portable_directory_projection.py tests/test_intr_lifecycle_closure.py tests/test_cloud_peer_adoption_provider_binding.py tests/test_kv_provider_operation_store.py tests/test_kv_my_kv_projection.py tests/test_storage_endpoint_v2.py tests/test_communication_runtime.py tests/test_admit_tvc_readiness_evidence.py tests/test_cross_edge_selection_receipt.py tests/test_kv_auri_peripheral_profiles.py tests/test_skap_intr_reconstruction.py tests/test_skap_loader_js.py tests/test_kv_ladder_conformance_lc_kv.py
```

## Trust anchors and E0

`runtime.kv_interlock_endpoint.TRUST_ANCHORS` is the only seam: label `PRODUCTION` and no installed InTr transport. No
genesis or issuer constant exists. The real path therefore FAILS_CLOSED (`HEALTHY_NODE_LEDGER_NOT_ONBOARDED` /
`ORG_LEDGER_LOCATION_NOT_DESIGNATED` / `ORG_LEDGER_GENESIS_NOT_PINNED` / `MERGE_APPEND_PATH_NOT_ADMITTED` /
`INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED`) until StegVerse-Labs/.github#3255 and StegVerse-org/LLM-adapter#431 are
admitted (with the observed genesis pinned), TV/TVC publishes the org-ledger head attester and Lane C admits the append
route, and Lane B's transport exists. The E0 stand-ins (`tests/kv_two_layer_e0.py`,
label `E0_STANDIN_TEST_ONLY_NOT_EVIDENCE`) are in force only inside setUpModule/tearDownModule or a context manager.
Receipts carry `trust_anchors_label`; layer 2 and the finish point refuse receipts minted under other anchors.

## Org InTr endpoint model (#432 v1)

`endpoint_kind` is taken from Lane B's published `schemas/endpoint-kind.v1.json` (`$defs.endpoint_kind.enum`, read
from the digest-checked vendored bytes; never a hand-written list): EPHEMERAL, PERMANENT, GATEWAY, KV, SKAP_VAULT, ORG
(`ENDPOINT_KINDS`, equal to #432's). Schemas (vendored at 1cbad77e, unchanged at 74509fec): `stegverse.endpoint-kind/v1`,
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
