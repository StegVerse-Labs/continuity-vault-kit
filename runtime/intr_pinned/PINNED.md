# Pinned InTr code (vendored byte-identical, digest-pinned; not a dependency)

Everything under `runtime/intr_pinned/` is a byte-identical copy of StegVerse-org/LLM-adapter at
`c2c57505535fb89ee88477eda1378c5fc610e0f7` (draft PR StegVerse-org/LLM-adapter#432, Lane B anchored-root check,
LC-KV-13, InTr and Mesh Destinations lane, StegVerse-org/.github#162), kept at its upstream-relative layout because
#432's `pinned_code_failure` hashes `ROOT/<path>` for every entry of its pinned-code-digests file (ROOT =
`runtime/intr_pinned`). Stdlib only: `llm_adapter/ed25519_verify.py` is Lane B's stdlib Ed25519 verify (#430/#432).

| file | sha256 |
| --- | --- |
| `llm_adapter/endpoint_ledger_anchor.py` (evaluate_anchored) | `5fcc9018e18d709ab5b9c9ea5195e751abf2d01b4c124cf4fafdcfb617023d10` |
| `llm_adapter/healthy_node_evaluator.py` (evaluate, unchanged since #428) | `fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58` |
| `llm_adapter/ed25519_verify.py` | `ab05e39a3e40b99f02ff199b178554e0ba435c3ff387dca3f896619770770232` |
| `llm_adapter/node_existence_readback.py` | `cbed113d7fe59fc0919953bad5a0a08cdaeba3ad70a4e728e572c360f6fb2fb7` |
| `llm_adapter/node_health_check_projection.py` | `97cb7043c3f43d9aab2f0a591e1eefb94d3b127efc542d75be8d7574ce561ae8` |
| `llm_adapter/node_health_report_producer.py` | `21249f2505505afd60eb14188ea638202f2926b207d64cfcf8c3bc5db2d9f361` |
| `llm_adapter/node_identity_binding_producer.py` | `ab578c921c6de5f50b9ecca50a71645e10582a051d2dd3417faa62d0dfdec01a` |
| `llm_adapter/node_ingress_boundary.py` (hashed, never executed) | `86bae0426956581b862dd085c4ac64bf0a4f7dc37b0309ca9d223a3306754339` |
| `llm_adapter/node_receipt_common.py` | `7e73b65b649c7238aa6ae47409282b2fb729157de083c093fe595611966e43c7` |
| `.stegverse/node-ledger/pinned-code-digests.v1.json` | `9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8` |
| `.stegverse/transition-ledger/emit.py` | `9579726de7ef915ac8cd61be1ba1c5ef6e34de4ca996504374b0dce7f7c2c9c3` |
| `.stegverse/transition-ledger/contract.json` (supporting data) | `a59040e8cabe6dc618af0ba340cb5563ce726f645a76248ccb354961d29144e7` |
| `.stegverse/heartbeat-awareness.json` (supporting data) | `87b1c4006d3829ea70626d481012791c557e97bcd580a6c3d5ccc61389a6951b` |

The canonical digests map in the pinned-code-digests file hashes to
`sha256:86f8b5d008a5e70e7843238388fbddf6975ec994f9fcc1b115d56dd3f40a3360`; an anchored genesis binds that value.
Evaluator provenance (same bytes): #428 @0b37fe3b, #429 @5f5f7bbe, #430 @4e1499ab and @3c106de4, #432 @c2c57505.
Interface doc `docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md` sha256 `d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de`.

* Do not edit these files. `runtime.kv_interlock_endpoint.load_pinned_intr` reads every file once, checks its sha256
  against `PINNED_ANCHORED_EVALUATOR["vendored_files"]`, and compiles the executed modules from exactly those bytes
  (never re-read from disk), under the names `llm_adapter.*` with an empty package search path, removing them from
  `sys.modules` afterwards. A process that already imported another `llm_adapter` is refused.
* `node_ingress_boundary.py` imports the StegVerse SDK, which is not a cvk dependency, so it is never executed: KV reads
  its three string constants (ADMITTED_CLASS, REFUSED_CLASS, RECORD_SCHEMA) from the pinned bytes by AST.
* LC-KV-10 (pinned by identity): layer 1 accepts only the `evaluate_anchored` function object produced by that load,
  whose code object still hashes (marshal) to the digest recorded at load. A callable's `__module__`, `__qualname__` or
  source filename is never consulted; anything else is refused at layer 1
  (`LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED`) and, if it ever minted a receipt, at layer 2 and the finish point.
* To re-pin, copy the files from the new LLM-adapter commit and update `PINNED_HEALTHY_NODE_EVALUATOR` and
  `PINNED_ANCHORED_EVALUATOR` in `runtime/kv_interlock_endpoint.py`. A final re-vendor follows once Lane B's stack
  (#429, #430, #431 onboarding, #432) settles.

Layer 1 (`KVInterlockRuntime.handle`, INTR_DEVICE_KV):
* Org ledger. The deployment binds a git repository of StegVerse-org/.github. KV reads
  `refs/stegverse/organization-ledger` at the head it observes now and materializes only
  `repository-ledger/StegVerse-org/LLM-adapter`. No genesis constant is pinned (LC-KV-15, P1 rev 4): the genesis is
  derived from the org chain's own oldest receipt, which must be the LLM-adapter repository-ledger initialization in
  the pinned receipt body, and a genesis labelled for other trust anchors is refused. The head pin handed to
  evaluate_anchored is that tree's HEAD.json. Unobserved: six-field FAIL_CLOSED `HEALTHY_NODE_LEDGER_NOT_ONBOARDED`.
* Node root. The deployment's endpoint `{endpoint_kind, ledger_root}` (#432 enum: EPHEMERAL, PERMANENT, GATEWAY, KV,
  SKAP_VAULT, ORG). Only evaluate_anchored decides whether it is anchored (InTr path receipt pair for own ledgers,
  StegOS NODE_LEDGER_OPENED for EPHEMERAL, org-root derivation for GATEWAY; ORG is never a node root). Its refusal is
  `EPHEMERAL_NODE_LEDGER_NOT_ANCHORED` with evaluate_anchored's own result carried as `health_evaluation`.
* Identity and transport. The requester is the identity the installed InTr transport authenticates; its
  node_identity_key must equal the anchored genesis key. The observed transport state is passed; unobserved is
  `INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED` (class B, Lane B).
* `TRUST_ANCHORS` holds only the label and the observed transport object (None in production). Tests put labelled
  `E0_STANDIN_TEST_ONLY_NOT_EVIDENCE` anchors in force only inside setUpModule/tearDownModule or a context manager.
* The finish point expects a PERMANENT node (LC-KV-13; EPHEMERAL generation is a separate task).
* Residual risk (LC-KV-08, class C, TV/TVC and Lane C): ledger receipts are unsigned (TVC#537).
