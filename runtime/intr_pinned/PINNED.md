# Pinned InTr code (vendored byte-identical, digest-pinned; not a dependency)

Everything under `runtime/intr_pinned/` is a byte-identical copy of StegVerse-org/LLM-adapter at
`1cbad77eaff3254ea30fb9d3377d40abcf6728df` (draft PR StegVerse-org/LLM-adapter#432, Lane B anchored-root check with
LC-KV-16 inside evaluate_anchored, published v1 schemas,
LC-KV-13, InTr and Mesh Destinations lane, StegVerse-org/.github#162), kept at its upstream-relative layout because
#432's `pinned_code_failure` hashes `ROOT/<path>` for every entry of its pinned-code-digests file (ROOT =
`runtime/intr_pinned`). Stdlib only: `llm_adapter/ed25519_verify.py` is Lane B's stdlib Ed25519 verify (#430/#432).

| file | sha256 |
| --- | --- |
| `llm_adapter/endpoint_ledger_anchor.py` (evaluate_anchored) | `7a998544707e8fce7164d9229116942501b141b13a4f5af8772a3dbd8feb8403` |
| `llm_adapter/org_ledger_location.py` (designated org ledger, #431 location) | `2ffaa91a606d18c45f239930e0e50292cb12461be22dc370fb6343037e3fce78` |
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
| `.stegverse/node-ledger/node-ledger-opened-signers.v1.json` (signers `[]`, NONE_PUBLISHED) | `478174cb89dc173e9bf7e8deb1db8b3881161e5a2fd10d6435298f74b6d3c63d` |
| `schemas/endpoint-kind.v1.json` (KV's `ENDPOINT_KINDS` is its enum) | `94fe6fe18a38f33d9a1730b81d1f92ded06df288262b22e7d01cc11119d93d60` |
| `schemas/node-ledger-opened.v1.json` (issued anchor) | `2ef662f3cbe5da67aeae3732e526b86e71010c51a95887686d24d65ce919a352` |
| `schemas/node-ledger-opened-signed.v1.json` (signed envelope) | `74cdc7e520d55f1bc1f964485ecada2a3953e331b1a87cca6dc9d36f74c5efa1` |
| `schemas/node-ledger-opened-generation.v1.json` (StegOS generation record) | `7012ff4993213ce2ecbfa17ec01eeb149d2c0b999152a37e65f6205e6f48f0d4` |

The canonical digests map in the pinned-code-digests file hashes to
`sha256:86f8b5d008a5e70e7843238388fbddf6975ec994f9fcc1b115d56dd3f40a3360`; an anchored genesis binds that value.
Evaluator provenance (same bytes): #428 @0b37fe3b, #429 @5f5f7bbe, #430 @4e1499ab and @3c106de4, #432 @c2c57505 and
@1cbad77e. The genesis-bound pins evaluate_anchored returns on ALLOW (`anchor.pinned_digests`) are evaluator
`fdaa2005...1f58` and producer `21249f25...f361`; health receipts carry no per-receipt pinned_digests.

TEST-ONLY copies (not executed by the runtime; under `tests/fixtures/intr_pinned_test_only/`, byte-identical at 1cbad77e):
`ed25519_test_signer.py` (Lane B's stdlib signer, `tests/ed25519_test_signer.py`) sha256
`3173bfcfca33129cd31942783b9e3e4c9380022f308f2fc31ccdda3dc2f6fe52`, and
`contract_with_431_repository_ledger_location.json` (`tests/fixtures/node_receipts/`) sha256
`b52ee0faa32db00d2f61a1f78a2f40380c4dcb212004d527a51b1e8fb05972d9`. The E0 harness checks both digests and points
`org_ledger_location.CONTRACT_PATH` at the fixture only while E0 anchors are in force; the vendored contract.json has
no `repository_ledger_location` yet, so production refuses `ORG_LEDGER_LOCATION_NOT_DESIGNATED` (#431).
Interface doc `docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md` sha256 `d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de`.

* Do not edit these files. `runtime.kv_interlock_endpoint.load_pinned_intr` reads every file once, checks its sha256
  against `PINNED_ANCHORED_EVALUATOR["vendored_files"]`, and compiles the executed modules from exactly those bytes
  (never re-read from disk), under the names `llm_adapter.*` with an empty package search path, removing them from
  `sys.modules` afterwards. A process that already imported another `llm_adapter` is refused.
* `node_ingress_boundary.py` imports the StegVerse SDK, which is not a cvk dependency, so it is never executed: KV reads
  its four string constants (ADMITTED_CLASS, REFUSED_CLASS, RECORD_SCHEMA, INTERLOCK_INTR) from the pinned bytes by AST.
* LC-KV-10 (pinned by identity): layer 1 accepts only the `evaluate_anchored` function object produced by that load,
  whose code object still hashes (a deterministic view of bytecode, constants and names; not marshal, whose output
  depends on reference counts) to the digest recorded at load. A callable's `__module__`, `__qualname__` or
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
  StegOS's signed NODE_LEDGER_OPENED envelope for EPHEMERAL (signer must be published; none is), org-root derivation for GATEWAY; ORG is never a node root). Its refusal is
  `EPHEMERAL_NODE_LEDGER_NOT_ANCHORED` with evaluate_anchored's own result carried as `health_evaluation`.
* Identity and transport (LC-KV-16, enforced inside evaluate_anchored at 1cbad77e). The org ledger is read by
  `org_ledger_location.designated_org_ledger` from the contract designation (#431). Identity: the transport hands over
  the node's `stegverse.node-identity-proof/v1`, an Ed25519 signature by the anchored node_identity_key over
  `identity_challenge` (node, kind, genesis, chain head, anchor and org head); absent is `NODE_IDENTITY_NOT_PROVEN` /
  `NODE_IDENTITY_PROOF_ABSENT` (class B), a bad or stale proof `NODE_IDENTITY_PROOF_INVALID` (class C). Transport is
  read from the node's latest NODE_INGRESS_ADMITTED receipt (`transport: INTERLOCK_INTR`, `transport_state:
  INSTALLED`); otherwise `INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED` (class B, Lane B). KV keeps its stricter checks on
  top: the transport-authenticated key must equal the anchored genesis key, the ALLOW's `identity.node_id` must be the
  requester, `observed_transport` must be INTERLOCK_INTR/INSTALLED, and `anchor.pinned_digests` must be the genesis pins.
* `TRUST_ANCHORS` holds only the label and the observed transport object (None in production). Tests put labelled
  `E0_STANDIN_TEST_ONLY_NOT_EVIDENCE` anchors in force only inside setUpModule/tearDownModule or a context manager.
* The finish point expects a PERMANENT node (LC-KV-13; EPHEMERAL generation is a separate task).
* Residual risk (LC-KV-08, class C, TV/TVC and Lane C): ledger receipts are unsigned (TVC#537).
