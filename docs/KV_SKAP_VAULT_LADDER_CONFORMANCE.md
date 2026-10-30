# KV-SKAP-VAULT-FUNCTIONAL-001: ladder conformance (LC-KV) and the node's own ledger chain

Goal: KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324). Lowest supported mode: E0. This note answers P1's
DENYs on continuity-vault-kit#258 (StegVerse-Labs/.github#3330 @578583be and rev 4 @c8b8d156; StegVerse-org/.github#163)
and binds layer 1 to the pinned healthy-node evaluator `llm_adapter.healthy_node_evaluator.evaluate`
(StegVerse-org/LLM-adapter#430, merged as 649f0775 on LLM-adapter main; it carried #429 and #428), vendored byte-identical in
`runtime/intr_pinned/`, see `runtime/intr_pinned/PINNED.md`. The chain it reads is the requesting node's OWN transition
ledger, bound by the deployment with its pinned genesis. There is no org ledger, no org-to-adapter crossing and no
endpoint-kind model: the Org-to-adapter InTr path and the adapter ledger designation (#432, closed unmerged) were retired
by Coordination's ruling (StegVerse-org/.github#162, ruling (b)), and the six vendored copies of that design were removed.
KV keeps its own ledger (LC-KV-29), `INTR_DEVICE_KV` and `KV_INTERNAL_SKAP_GATE`.

## Admission order (LC-KV-03, tracked by P1 as LC-KV-05)

`runtime.kv_skap_vault.ADMISSION_ORDER`, recorded on every finish-point verdict: continuity-vault-kit#258 and #259 are
admitted together (ADMITTED_TOGETHER), never one without the other.

## What each finding now enforces

| Finding | Enforced in | Negative tests |
|---|---|---|
| LC-KV-10 (rev 4, class A): the decider is pinned by identity, never by name | `load_pinned_intr` compiles the vendored modules from the digest-checked bytes; `pinned_decider_identity` requires `decider is` the loaded `evaluate` and the sha256 of a deterministic view of its code object (bytecode, constants, names; not marshal, whose output depends on reference counts) equal to the one recorded at load. Layer 1 refuses any other decider (`LAYER1_NOT_EVALUATED_THROUGH_THE_PINNED_EVALUATE`); `layer1_receipt_conformance` (layer 2 and the finish point) re-checks ids, source and code digests; layer 2 also refuses a runtime whose decider is no longer the pinned object, and accepts only an exact `KVInterlockRuntime` | spoofed `__module__`/`__qualname__`/`co_filename`, a re-wrapped copy of the pinned code, injected callables, edited pin and code-digest fields, decider swapped after minting, subclassed runtime, receipt minted under other trust anchors |
| Layer 1 goes through the pinned `evaluate` over the node's own chain | `KVInterlockRuntime._evaluate_health` calls the bare pinned `evaluate(node_id, ledger_root=, transport_state=, report_receipt_sha256=, require_admission=True)` over the node's own transition ledger. After the ALLOW, KV checks the exact receipt shape, node id and cite, the chain head against the head read at bind, the genesis against the deployment's pin, that every chain receipt was written by the pinned producers (`NODE_CHAIN_RECEIPT_NOT_WRITTEN_BY_THE_PINNED_PRODUCERS`), and that the transport-authenticated key is the key the chain binds (`REQUESTER_KEY_NOT_THE_BOUND_NODE_IDENTITY_KEY`) | a foreign-producer chain that bare `evaluate` ALLOWs is refused; spy on the evaluate call; key mismatch |
| LC-KV-15 (class B): the chain is bound by the deployment, not by the requester; the only ALLOW path | `bind_healthy_node_ledger` accepts only `{kind: NODE_OWN_LEDGER_CHAIN, ledger_root, genesis_receipt_sha256}` from the deployment and reads the head once; `TRUST_ANCHORS` holds only the label and the observed transport | scratch root / bare dir / unbound dict; a wrong genesis pin (`NODE_LEDGER_GENESIS_MISMATCH`); `LcKv15OwnChainIdentityTransport`; transport absent or not INSTALLED, unenrolled and mis-claimed identity |
| LC-KV-16 class: a foreign chain, a wrong key or a moved head never reaches ALLOW through KV's wrapper | KV's post-ALLOW checks above; a requester can cite only a report receipt | `LcKv16ForeignChainAndKeyNeverAllow`: foreign producers, a key other than the bound one, requester-supplied chain, each leg removed. This is weaker than the retired org-ledger anchoring and the wrapper-internal identity proof, which are not re-created (accepted under Coordination's ruling (b)) |
| LC-KV-18 (class B, owner Lane B): no InTr transport is installed (the evaluator stack is on LLM-adapter main, merged as 649f0775) | `layer1_prerequisites()`, recorded on every finish-point verdict as `layer1_prerequisites` (six fields per unmet leg) | `LcKv18Layer1Prerequisites` |
| LC-KV-13: the finish point expects a node admitted through its own ledger chain | `_check_layer1` (`LAYER1_NODE_NOT_BOUND_THROUGH_ITS_OWN_LEDGER_CHAIN`) | a receipt carrying any other binding kind does not complete the finish point |
| LC-KV-07: gated `read_stream` and `append_extension` (now owned by TV/TVC; unchanged here) | `execution/vault_store.py` | as before |
| LC-KV-03: custody verifier is the real layer-2 gate | `validate_vault_lineage_custody_result` → `_require_access_layers` → `pinned_layer2_gate` | arbitrary callables, lenient gate subclasses and their bound methods |
| LC-KV-08 | not changed here (TV/TVC and Lane C) | reported as six-field FAIL_CLOSED |

Tests: `tests/test_kv_ladder_conformance_lc_kv.py` plus the updated suites; 0 skipped. Stdlib only: no test or runtime
file #258 adds or changes imports `cryptography` (the SKAP persistence tests use a static synthetic sealed fixture,
`tests/fixtures/skap_sealed_material.synthetic.json`; the stdlib Ed25519 verify is vendored from #430).

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
genesis or issuer constant exists. The real path therefore FAILS_CLOSED (`HEALTHY_NODE_LEDGER_NOT_BOUND` /
`INTR_TRANSPORT_NOT_INSTALLED`, class B) until the deployment binds the node's own chain with its pinned genesis and an InTr
transport is installed. The evaluator stack is merged on LLM-adapter main in the order StegVerse-Labs/StegOS#430 (supersedes #426),
then StegVerse-org/LLM-adapter#430 (which carried #429 and #428). The E0 stand-ins (`tests/kv_two_layer_e0.py`,
label `E0_STANDIN_TEST_ONLY_NOT_EVIDENCE`) are in force only inside setUpModule/tearDownModule or a context manager.
Receipts carry `trust_anchors_label`; layer 2 and the finish point refuse receipts minted under other anchors.

## Node's own ledger chain (layer 1)

* Retired: the endpoint-kind enum and schemas, the anchored evaluate, the org-ledger anchor, the designation and the carrier
  (#432, closed unmerged). KV-access receipts carry `endpoint_kind: KV` and SKAP-access receipts `endpoint_kind: SKAP_VAULT`
  with `layer1_endpoint_kind: KV` as plain role labels only; no schema is read for them.
* `node_identity_key` is the key the node's own `NODE_IDENTITY_BINDING` receipt binds; the transport-authenticated key
  must equal it.
* The ledger binding in a layer-1 receipt is `{kind: NODE_OWN_LEDGER_CHAIN, genesis_pinned_by: DEPLOYMENT_BINDING,
  chain_head_receipt_sha256, node_identity_key}`. It has no ledger root.
* The six retired copies stay in git history and on the closed #432 branch; a guard test fails if any returns.

## Naming (documentation only; nothing is renamed)

* `_<org>` names an Org: a coordination of data as presented, e.g. MyKV WorkSpace.
* `##_<name>` names a storage surface that Orgs interact with. The `##` prefix only keeps data-location names distinct
  for human review; it carries no semantics.

## Residual risk

Ledger receipts are unsigned (TVC#537) and TVC `build_chain` self-asserts its hops (LC-KV-08). A forged local copy of
a node's own chain that keeps the pinned genesis and is written with the pinned producers' shape is not detectable by KV
until signed receipts exist. Gate payload bindings (`bind_payload`) are in-memory, so gated reads do not verify across a process
restart until durable custody exists (TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001). A store-local hash chain of those
bindings was considered and not added: whoever can write the vault directory can rewrite such a chain end to end, so
restoring gate provenance from it on load would turn a local file into authority. `KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND`
stays until a bound durable custody location exists.

**KV receipt-chain rollback (LC-KV-26, closed by P1, StegVerse-org/.github#163).** The rule is Coordination's, relayed
to P1 at 05:03Z: "a crossing record held at both ends (the org side and KV's own ledger), never an InTr hop inside one
org" (#167 c6393119202). InTr runs only between distinct organizations (`StegVerse-Labs/.github:data/intr-protocol/v1/protocol.json:174`),
and the SKAP Vault sits inside KV, reached only through the in-KV SKAP gate. SKAP invariant (Labs
`docs/FEDERATION_DIRECTORY.md:3`): "SKAP Vault inside KV is the only PII and credential store for every user, the
ecosystem's own included; the ecosystem holds none (HST citation pending P1 #163)." Nothing here adds a store or a
credential: the Org record stays digest-only and refuse-only.

A read-back head is ALLOW only when it is held at both ends: it is the newest head in KV's own head record and an
observed Org digest-only crossing record names it (`endpoint_head_sha256`). Otherwise the read is six-field
FAIL_CLOSED `KV_CROSSING_RECORD_NOT_OBSERVED` (class B, predicate `KV_HEAD_RECORDED_AT_BOTH_ENDS`). The two
whole-store rollbacks (receipts, `HEAD.json` and KV's head record rolled back together), for kv and for SKAP through
the gate, are now closed:

1. **A rollback to before the first crossing.** A never-crossed chain is no longer skipped. With no Org record its head
   is held only at KV's end, so the read is FAIL_CLOSED. Once the Org side records a head (the genesis/first-head
   crossing), a rollback behind it is DENY `KV_LEDGER_HEAD_ROLLBACK_DETECTED`.
2. **A rollback to after the last crossing, dropping the internal heads but keeping the crossed head** (P1's
   `WHOLE_STORE_AFTER_LAST_CROSSING_INTERNAL_HEADS_ROLLED_BACK`, joint review of #263 @34496af5). An internal head held
   only at KV's end was never readable, so no reader relied on a head that a rollback could drop. Once it is held at
   both ends, dropping it is DENY `KV_LEDGER_HEAD_ROLLBACK_DETECTED`, with or without a caller claim.

That is the one code Coordination's ruling keeps for a rollback, with no alias. The Org never grants. The witnesses are
`tests.test_kv_ladder_conformance_lc_kv`: test_lc_kv_26_rollback_after_the_last_crossing_is_refused_both_ends (case
2) and test_lc_kv_23_whole_chain_rollback_is_refused_by_the_org_crossing_record (case 1). See
`docs/kv-skap-ledger-location.md` ("Both ends").
