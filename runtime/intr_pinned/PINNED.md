# Pinned InTr healthy-node evaluator (vendored, digest-pinned; not a dependency)

`healthy_node_evaluator.py` is a byte-identical copy of `llm_adapter/healthy_node_evaluator.py` at
StegVerse-org/LLM-adapter@0b37fe3b786a2de687235f5d9d146af49ffee9cd (draft PR StegVerse-org/LLM-adapter#428,
LC-KV-13/14, owned by the InTr and Mesh Destinations lane, StegVerse-org/.github#162).

* Provenance: the same bytes are at StegVerse-org/LLM-adapter#429 @5f5f7bbeea96d5f313effaa02f86b01196465247.
  #429 is the NODE_HEALTH_REPORTED producer and contains #428; it lands with or before #428. At #429 the interface doc
  only gains the producer section, sha256 `a363ff9bb498aa816adf9cc9d64559a389dec6acd3d02144056ee9c2540b91f0`.
  The same bytes are also at #430 @4e1499ab88144e8eae341058f7360b0d2a805b56, which carries #429 and adds the class B
  inputs; the ALLOW shape is unchanged. Its interface doc adds a section, sha256
  `6b523e3949d89a4cb85904559d5bb458b9796ec910fde2c26296096f0d3f8b62`. The #430 head has since moved to
  3c106de4d9b87da498e620e5db33f8b922773c26 with the evaluator bytes unchanged (interface doc sha256
  `d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de`).
* Producer pin: `llm_adapter/node_health_report_producer.py`, sha256
  `21249f2505505afd60eb14188ea638202f2926b207d64cfcf8c3bc5db2d9f361`, observed at #429 @5f5f7bbe and #430 @3c106de4
  (`PINNED_NODE_HEALTH_REPORT_PRODUCER`). Not vendored: KV only checks that an anchored temporary ledger's health
  receipts carry this digest and the evaluator digest.
  A final re-vendor follows once Lane B's stack (#429, #430, #431) settles.
* Source sha256: `fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58`.
* Interface: `docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md` at the same commit, sha256 `757d697ca385f5d4709d8b26e51119330bb685b4770512312313fc42460bb76d`.
* Do not edit the vendored file. `runtime.kv_interlock_endpoint.resolve_pinned_healthy_node_evaluator` re-derives the
  sha256 of these bytes before every resolution. On a mismatch, layer 1 fails closed.
* To re-pin, copy the file from the new LLM-adapter commit and update `PINNED_HEALTHY_NODE_EVALUATOR` in
  `runtime/kv_interlock_endpoint.py`.

Layer 1 (`KVInterlockRuntime.handle`, INTR_DEVICE_KV), after P1's LC-KV-15 DENY on cvk#258 @61104a57
(StegVerse-Labs/.github#3330 @578583be):
* Ledger binding (`bind_healthy_node_ledger`, the single binding function). The deployment binds a git repository of
  StegVerse-org/.github. KV reads `refs/stegverse/organization-ledger` at the head it observes now, materializes only
  `repository-ledger/StegVerse-org/LLM-adapter` from that commit, and requires the chain's genesis to equal the pinned
  `TRUST_ANCHORS["healthy_node_ledger_genesis_receipt_sha256"]`. The binding (repository, ref, namespace,
  observed_head, genesis, chain head) is recorded on the KV-access receipt. A bare directory, a scratch ledger root or
  any other caller root is refused. There is no new ref and no new ledger root.
* Anchored temporary node ledger (steering 2). `{"kind": "ANCHORED_TEMPORARY_NODE_LEDGER", "ledger_root",
  "node_ledger_opened"}` binds only with a NODE_LEDGER_OPENED anchor issued by the org ledger or TV/TVC. The anchor
  must bind node_id, node_identity_key (both equal to the transport-authenticated identity) and the ledger's genesis
  hash, and every NODE_HEALTH_REPORTED receipt on it must carry `evidence.pinned_digests` =
  {evaluator_source_sha256, producer_source_sha256}. Otherwise: failure_code `TEMP_NODE_LEDGER_NOT_ANCHORED`, owner
  KV-SKAP-VAULT-FUNCTIONAL-001, retry = Lane B's anchor and dissolution transition. The anchor shape
  (`NODE_LEDGER_OPENED_FIELDS`) is minimal and PENDING Lane B's schema; no issuer verifier is pinned in production.
* Identity. The requester node is the identity the installed InTr transport authenticates from the envelope, never
  the caller's claim; a mismatch with `boundary_proof.source_identity_ref` is refused (class C).
* Transport. `transport_state` passed to the evaluator is the installed transport's observed state. No transport is
  installed today, so it is `UNKNOWN_NOT_AUTHENTICALLY_OBSERVED` and layer 1 refuses
  (`INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED`, class B, Lane B).
* `TRUST_ANCHORS` is the single seam. Production: label PRODUCTION, genesis None, transport None, no anchor issuers,
  so the real path FAILS_CLOSED until StegVerse-Labs/.github#3255 and StegVerse-org/LLM-adapter#429/#431 are admitted.
  Tests swap in labelled `E0_STANDIN_TEST_ONLY_NOT_EVIDENCE` anchors (tests/kv_two_layer_e0.py) only inside
  setUpModule/tearDownModule or a context manager. Every receipt records its trust_anchors_label; layer 2 and the
  finish point refuse receipts minted under other anchors.
* Layer 2 (`SkapLayer2Gate`) re-checks every layer-1 receipt with `layer1_receipt_conformance` (evaluator id and source
  sha256 pin, anchors label, endpoint_kind KV, INSTALLED transport, transport-authenticated identity, contract-location
  or anchored binding) and accepts only an exact `KVInterlockRuntime` (LC-KV-10).
* It maps any non-ALLOW to `KV_ACCESS_LAYER1_REFUSED` and keeps the evaluator's six fields as `health_evaluation`.
* KV never decides health itself.
* Until the chain is onboarded with a genesis, layer 1 is FAIL_CLOSED class B `HEALTHY_NODE_LEDGER_NOT_ONBOARDED` (or
  `HEALTHY_NODE_LEDGER_GENESIS_NOT_PINNED` once readable but not pinned). Its retry entrypoint is
  StegVerse-org/LLM-adapter#431, the organization-ledger onboarding (Lane B draft, like StegVerse-SDK#558), which is
  FAIL_CLOSED until genesis and an admitted append route exist (StegVerse-Labs/.github#3255).
* Residual risk (LC-KV-08, class C, TV/TVC and Lane C): ledger receipts are unsigned (TVC#537), so a forged local copy
  of the org-ledger repository that keeps the real genesis and appends forged receipts is not detectable by KV.
