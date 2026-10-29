# Pinned InTr code (vendored byte-identical, digest-pinned; not a dependency)

## Sealed byte copies that still carry retired LLM-adapter#431 wording (six-field note, 2026-10-29)

Rule: every byte copy below is a receipt of StegVerse-org/LLM-adapter#432 @eecf4843 (or of a TEST-ONLY upstream fixture)
and is checked by sha256 at load (`PINNED_ANCHORED_EVALUATOR["vendored_files"]`, `PINNED_HEALTHY_NODE_EVALUATOR`) and by the
E0 harness. The retired wording lives inside those bytes. KV does not edit them: an edited copy would no longer be the
byte copy of `eecf4843:<path>`, and `endpoint_ledger_anchor.py` itself names the head-signers copy by its digest
(`758d7983...`). Every live KV reader (runtime, docs, tests, comments) has had its reference replaced and is guarded by
`tests/test_kv_receipt_ledgers_no_431_and_crossing_wording.py`. The bytes below are the only places the wording remains.

| file | receipt (sha256 of the sealed bytes) |
| --- | --- |
| `runtime/intr_pinned/llm_adapter/endpoint_ledger_anchor.py` | `153cf121a51199da8432735d4b2fb34b396f7eaa24da80f1bf9c77040013ac09` (LLM-adapter#432 @eecf4843) |
| `runtime/intr_pinned/llm_adapter/endpoint_ledger_designation.py` | `d69dbb22a1446a22e84b86532f93d9698ac6dc3c82e6aa6ee20882c6764049d8` (LLM-adapter#432 @eecf4843) |
| `runtime/intr_pinned/llm_adapter/intr_transport_carrier.py` | `9d3e69c838d7e20533f0c5a06401b018948cb12a4201889f6b41d4b497df720f` (LLM-adapter#432 @eecf4843) |
| `runtime/intr_pinned/llm_adapter/org_ledger_location.py` | `b51e6a8bd39ba6fd83044222a3858a2cb0c437020e3e9abbe97c4494d41f2681` (LLM-adapter#432 @74509fec, unchanged since) |
| `runtime/intr_pinned/.stegverse/node-ledger/kv-ledger-head-signers.v1.json` | `758d798388599171c145e3d19ca4eb155ad3d3762a3721804da65c08ebc1fe72` (LLM-adapter#432 @c4cfc145, unchanged since) |
| `tests/fixtures/intr_pinned_test_only/contract_with_431_location_and_pinned_genesis.json` (TEST-ONLY) | `ea81ca135bfd3b8e86a69251cf63d6f5aaa86fa46777dcec9370971dd0c5208a` (LLM-adapter#432 @74509fec) |

* CODE: `PINNED_BYTE_COPIES_CARRY_RETIRED_431_WORDING`
* CLASS: B (the repair is an upstream re-vendor owned by Lane B; KV cannot change those bytes and keep its receipts)
* OBSERVED: the six files above carry references to the retired LLM-adapter#431 organization-to-adapter route
  (closed unmerged by the owner, edge removed by StegVerse-org/.github#249). Their digests match the pins in
  `runtime/kv_interlock_endpoint.py`. The anchor module's own refusal fields (`RETRY_431`, `OWNING_431`, `NEXT_431`) can
  therefore still appear inside `health_evaluation`, which KV carries unchanged from `evaluate_anchored`.
* EXPECTED: an upstream LLM-adapter commit without the retired wording, re-vendored byte-for-byte, with the pins in
  `runtime/kv_interlock_endpoint.py` and the tables in this file updated in the same PR.
* BLOCKS: nothing in KV's own behavior (the production path is already FAIL_CLOSED); it blocks only a claim that no byte
  under `runtime/intr_pinned/` or its test-only fixture mentions the retired route.
* NEXT: Lane B publishes the LLM-adapter commit without the wording; KV then re-vendors in one PR and removes the
  exemption in the guard test. Event-driven by that commit; no cron, no polling.

## Pin entry 2026-10-23: StegVerse-org/LLM-adapter#432 @eecf4843 (current)

Source PR StegVerse-org/LLM-adapter#432 (draft), head `eecf4843e4ec2ec05ea5dbf6582e7d92080e8f9e`, re-pinned by Lane B to
cvk#263 @9bc54d05 (StegVerse-org/.github#162 comment 6374660708; #431 @`64121f4d7dafd04a7ad926a2c20165bcd73d2ff4`,
#433 unchanged @3f15a691). Every file below is a byte copy of `eecf4843:<path>` (checked byte-for-byte and by sha256).
Q-PERMANENT-REPOSITORY-LEDGER / LC-KV-25: PERMANENT is designated on the node's own storage endpoint (store_type
`NODE_STORAGE_ENDPOINT`, watermark `NODE_RECORDED_RECEIPT_CHAIN_HEAD`); no node storage-endpoint descriptor or reader is
documented, so production is FAIL_CLOSED `NODE_STORAGE_ENDPOINT_READER_NOT_DOCUMENTED` (class B, reader id
UNKNOWN_NOT_AUTHENTICALLY_OBSERVED). A PERMANENT org GIT_REF is DENY `ENDPOINT_ORG_MEMBERSHIP_REFUSED` (class A). The
Org-side crossing readback (`ORG_CROSSING_READER`) is unset in production (`KV_CROSSING_RECORD_NOT_OBSERVED`, class B).
The carrier is v2: the INTR_MESH_PATH_TRANSFER source half lives on the sender's own ledger, and nothing is retained on
the org ledger (`retain` / `read_retained` are removed). The cvk#263 @9bc54d05 contracts #432 carries as test fixtures
(`tests/fixtures/endpoint-ledger-designation/cvk263-9bc54d05/`) are kv `c9cc8913...89ce1` and skap `7f0a0536...a86f`,
equal to cvk#263's own; they are not vendored here.

Changed at eecf4843 (previous digest from the c4cfc145 entry below):

| file | sha256 at eecf4843 | at c4cfc145 |
| --- | --- | --- |
| `llm_adapter/endpoint_ledger_anchor.py` (evaluate_anchored) | `153cf121a51199da8432735d4b2fb34b396f7eaa24da80f1bf9c77040013ac09` | `2d80e443...b6b8` |
| `llm_adapter/endpoint_ledger_designation.py` (= #431 @64121f4d) | `d69dbb22a1446a22e84b86532f93d9698ac6dc3c82e6aa6ee20882c6764049d8` | `35217d33...b883` |
| `llm_adapter/intr_transport_carrier.py` (carrier v2, digest-only) | `9d3e69c838d7e20533f0c5a06401b018948cb12a4201889f6b41d4b497df720f` | `81ad9d3b...1aca6` |
| `schemas/endpoint-kind.v1.json` | `592bb3e5d67685912426a331769c44f60e75ff914138e0b0afc279c0c177b7a7` | `9952a545...dda27` |

Every other vendored file is byte-identical at eecf4843 (same digests); the changed modules add no imports, so the load
order is unchanged. KV's E0 harness adds one TEST-ONLY fixture, `tests/fixtures/intr_pinned_test_only/node.designation.json`
(byte copy of `eecf4843:tests/fixtures/endpoint-ledger-designation/node.designation.json`,
`d004bb72cba3143b2a4a544851eff1ae688094a44ceb72c9b4c1b5a41e091b15`), and TEST-ONLY `NODE_STORAGE_ENDPOINT` reader and
`ORG_CROSSING_READER` stand-ins in force only with the labelled E0 anchors (as #432's own tests do).

## Pin entry (history): StegVerse-org/LLM-adapter#432 @c4cfc145 (superseded by eecf4843 above; kept unedited)

Source PR StegVerse-org/LLM-adapter#432 (draft), head `c4cfc14566786e9da43d7a6d45d569745a582a3d`, re-pinned by Lane B to
cvk#263 @bf684aad (StegVerse-org/.github#162 comment 6373907403; #431 @`2494d75a02751ec534d613e000e97ad8bf68180f`,
#433 unchanged @d9164df9). Every file below is a byte copy of `c4cfc145:<path>` (checked byte-for-byte and by sha256).
Rule (1): no endpoint chain is anchored on the org ledger; KV and SKAP_VAULT are `STEGVERSE_KV:<location>` designations
read by `endpoint_ledger_designation` (cvk#263), GATEWAY is refused `GATEWAY_CARRIER_LEDGER_NOT_DESIGNATED`; per-kind
failure_code (`EPHEMERAL_NODE_LEDGER_NOT_ANCHORED` for EPHEMERAL only; `ENDPOINT_LEDGER_NOT_ANCHORED` or the org-ledger
reason for PERMANENT; rule (1) reasons are their own code), which KV now carries instead of overriding.

Changed or added at c4cfc145 (previous digest from the 74509fec entry below):

| file | sha256 at c4cfc145 | at 74509fec |
| --- | --- | --- |
| `llm_adapter/endpoint_ledger_anchor.py` (evaluate_anchored) | `2d80e443a96df667ba93da91e271549ee763d3eb570dfea9a808103f4b1ab6b8` | `d47cd0a4...c6f4` |
| `llm_adapter/endpoint_ledger_designation.py` (NEW; also = #431 @2494d75a) | `35217d335ae6c054e1d0dfb0ffb72befc9ded184c93dee105093df5cd1b2b883` | not vendored |
| `llm_adapter/supplied_epoch.py` (NEW; imported by the designation module; no imports) | `be91daad3d5557f810872731c3ea8cc36e1f13af569e1b7634f487fd36f44534` | not vendored |
| `llm_adapter/intr_transport_carrier.py` (adds destination_evidence_failure / refusal) | `81ad9d3b42076c991443f3d79ec82c5f306eb8a8aa5f21228fe9faeb8b21aca6` | `9f460c07...01bf` |
| `schemas/endpoint-kind.v1.json` (ledger_model OWN_LEDGER / STEGVERSE_KV_DESIGNATION / NOT_DESIGNATED / ORGANIZATION_LEDGER) | `9952a54526bf71809968ed719fcb5ea2fc55e865a1fbd0d67449d50561fdda27` | `94fe6fe1...3d60` |
| `.stegverse/node-ledger/kv-ledger-head-signers.v1.json` (NEW, supporting data; signers `[]`) | `758d798388599171c145e3d19ca4eb155ad3d3762a3721804da65c08ebc1fe72` | not vendored |

Every other file in the 74509fec table is byte-identical at c4cfc145 (same digests). The pinned-code-digests file
(`9ed1e817...30f8`, canonical map `sha256:86f8b5d0...3360`) and the interface doc (`d4a53471...c6de`) are unchanged.
`node_ledger_dissolution.py` is still not imported by evaluate_anchored and is not vendored. Load order adds
`supplied_epoch` and `endpoint_ledger_designation` before `intr_transport_carrier`.

## Pin entry (history): StegVerse-org/LLM-adapter#432 @74509fec (superseded by c4cfc145 above; kept unedited)

Everything under `runtime/intr_pinned/` is a byte-identical copy of StegVerse-org/LLM-adapter at
`74509feca062d5f17dbefe5730cbb1304ab6b318` (draft PR StegVerse-org/LLM-adapter#432, Lane B anchored-root check with
LC-KV-16 inside evaluate_anchored, published v1 schemas; code byte-identical to @a2ee67e6, which reworked the failure
precedence, pinned the org genesis by the #431 contract, required an append-route head attestation and the InTr
carrier; 73316297 changed only #432's #431 contract fixtures; 74509fec changed only endpoint_ledger_anchor's
ORG_LEDGER_GENESIS_NOT_PINNED retry/next_attempt, which now name the REPOSITORY_LEDGER_GENESIS_PIN transition),
LC-KV-13, InTr and Mesh Destinations lane, StegVerse-org/.github#162), kept at its upstream-relative layout because
#432's `pinned_code_failure` hashes `ROOT/<path>` for every entry of its pinned-code-digests file (ROOT =
`runtime/intr_pinned`). Stdlib only: `llm_adapter/ed25519_verify.py` is Lane B's stdlib Ed25519 verify (#430/#432).

| file | sha256 |
| --- | --- |
| `llm_adapter/endpoint_ledger_anchor.py` (evaluate_anchored) | `d47cd0a4a0409ae79161be64c79e28e147f98ead55687ddeb2e744d3537fc6f4` |
| `llm_adapter/org_ledger_location.py` (designated org ledger, #431 location, pinned genesis, head attestation) | `b51e6a8bd39ba6fd83044222a3858a2cb0c437020e3e9abbe97c4494d41f2681` |
| `llm_adapter/intr_transport_carrier.py` (InTr path pair that carries the ingress signal; stdlib) | `9f460c078f5aba3a25edfecaf7e240334d943c3bf0b0cecc5972fc59e47501bf` |
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
| `.stegverse/node-ledger/org-ledger-head-signers.v1.json` (signers `[]`: MERGE_APPEND_PATH_NOT_ADMITTED, LC-KV-18) | `3be27ff079433995d5eba111a5bb8cbe058e492938fb2b7ca299fe7bf6b69297` |
| `schemas/endpoint-kind.v1.json` (KV's `ENDPOINT_KINDS` is its enum) | `94fe6fe18a38f33d9a1730b81d1f92ded06df288262b22e7d01cc11119d93d60` |
| `schemas/node-ledger-opened.v1.json` (issued anchor) | `2ef662f3cbe5da67aeae3732e526b86e71010c51a95887686d24d65ce919a352` |
| `schemas/node-ledger-opened-signed.v1.json` (signed envelope) | `74cdc7e520d55f1bc1f964485ecada2a3953e331b1a87cca6dc9d36f74c5efa1` |
| `schemas/node-ledger-opened-generation.v1.json` (StegOS generation record) | `7012ff4993213ce2ecbfa17ec01eeb149d2c0b999152a37e65f6205e6f48f0d4` |

The canonical digests map in the pinned-code-digests file hashes to
`sha256:86f8b5d008a5e70e7843238388fbddf6975ec994f9fcc1b115d56dd3f40a3360`; an anchored genesis binds that value.
Evaluator provenance (same bytes): #428 @0b37fe3b, #429 @5f5f7bbe, #430 @4e1499ab and @3c106de4, #432 @c2c57505,
@1cbad77e, @a2ee67e6, @73316297 and @74509fec. `node_ledger_dissolution.py` (117f9c0c) is not imported by evaluate_anchored at
74509fec and is not vendored. The genesis-bound pins evaluate_anchored returns on ALLOW (`anchor.pinned_digests`) are evaluator
`fdaa2005...1f58` and producer `21249f25...f361`; health receipts carry no per-receipt pinned_digests.

TEST-ONLY copies (under `tests/fixtures/intr_pinned_test_only/`, byte-identical at 74509fec, never loaded by the
runtime): `ed25519_test_signer.py` (`tests/ed25519_test_signer.py`) `3173bfcf...6fe52`;
`contract_with_431_repository_ledger_location.json` (a byte copy of #431's contract, `expected_genesis_receipt_sha256`
null) `d97cd4dc...5e89f`; `contract_with_431_location_and_pinned_genesis.json` (the same with the test genesis pinned)
`ea81ca13...0c5208a`; `org_ledger_test_genesis.json` `a2c01a2e...a6a7`; `org_ledger_harness.py` `3bbf7f7d...b945`
(provenance only, never executed: it imports `tests.ed25519_test_signer`). The E0 harness checks each digest; only while
E0 anchors are in force it points `org_ledger_location.CONTRACT_PATH` at the pinned-genesis fixture and
`load_head_signers` at the harness's TEST-ONLY append-route attester (same public seed and key_id as
`org_ledger_harness.py`). Production: the vendored contract.json (LLM-adapter main) has no `repository_ledger_location`
(`ORG_LEDGER_LOCATION_NOT_DESIGNATED`); with #431's contract it would be `ORG_LEDGER_GENESIS_NOT_PINNED`; with both,
the empty head-signers file gives `MERGE_APPEND_PATH_NOT_ADMITTED` (LC-KV-18, owner TV/TVC + Lane C).
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
  `repository-ledger/StegVerse-org/LLM-adapter`. KV pins no genesis (LC-KV-15): since #432 @a2ee67e6 evaluate_anchored
  accepts the store only at the #431 contract's `expected_genesis_receipt_sha256` and with a published append-route
  attestation of its head and namespace tree (`org_ledger_head_attestation`, carried in the deployment's binding,
  never the requester's), so KV's former genesis derivation and label check were dropped as duplicates. The head pin
  handed to evaluate_anchored is that tree's HEAD.json. Unobserved: six-field FAIL_CLOSED `HEALTHY_NODE_LEDGER_NOT_ONBOARDED`.
* Node root. The deployment's endpoint `{endpoint_kind, ledger_root}` (#432 enum: EPHEMERAL, PERMANENT, GATEWAY, KV,
  SKAP_VAULT, ORG). Only evaluate_anchored decides whether it is anchored (InTr path receipt pair for own ledgers,
  StegOS's signed NODE_LEDGER_OPENED envelope for EPHEMERAL (signer must be published; none is), org-root derivation for GATEWAY; ORG is never a node root). Its refusal is
  `EPHEMERAL_NODE_LEDGER_NOT_ANCHORED` with evaluate_anchored's own result carried as `health_evaluation`.
* Identity and transport (LC-KV-16, enforced inside evaluate_anchored; precedence at a2ee67e6: location and store,
  pinned code and anchor, identity, health and admission, transport record, InTr carrier). The org ledger is read by
  `org_ledger_location.designated_org_ledger` from the contract designation (#431). Identity: the transport hands over
  the node's `stegverse.node-identity-proof/v1`, an Ed25519 signature by the anchored node_identity_key over
  `identity_challenge` (node, kind, genesis, chain head, anchor and org head); absent is `NODE_IDENTITY_NOT_PROVEN` /
  `NODE_IDENTITY_PROOF_ABSENT` (class B), a bad or stale proof `NODE_IDENTITY_PROOF_INVALID` (class C). Transport is
  read from the node's latest NODE_INGRESS_ADMITTED receipt (`transport: INTERLOCK_INTR`, `transport_state:
  INSTALLED`, `signal_sha256`), and counts only when an INTR_MESH_PATH_INGRESS on the authenticated org chain, newer
  than the anchor, carried that signal (retained INTR_MESH_PATH_TRANSFER source); otherwise
  `INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED` (class B, Lane B), with `intr_carrier_refusal` for the carrier stage. KV keeps its stricter checks on
  top: the transport-authenticated key must equal the anchored genesis key, the ALLOW's `identity.node_id` must be the
  requester, and `anchor.pinned_digests` must be the genesis pins. (The ALLOW-shape `observed_transport`
  INTERLOCK_INTR/INSTALLED re-check was dropped as a duplicate of #432's transport-record and carrier stages.)
* `TRUST_ANCHORS` holds only the label and the observed transport object (None in production). Tests put labelled
  `E0_STANDIN_TEST_ONLY_NOT_EVIDENCE` anchors in force only inside setUpModule/tearDownModule or a context manager.
* The finish point expects a PERMANENT node (LC-KV-13; EPHEMERAL generation is a separate task).
* Residual risk (LC-KV-08, class C, TV/TVC and Lane C): ledger receipts are unsigned (TVC#537).
