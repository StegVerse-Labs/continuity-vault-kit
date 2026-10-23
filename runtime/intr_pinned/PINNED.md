# Pinned InTr healthy-node evaluator (vendored, digest-pinned; not a dependency)

`healthy_node_evaluator.py` is a byte-identical copy of `llm_adapter/healthy_node_evaluator.py` at
StegVerse-org/LLM-adapter@0b37fe3b786a2de687235f5d9d146af49ffee9cd (draft PR StegVerse-org/LLM-adapter#428,
LC-KV-13/14, owned by the InTr and Mesh Destinations lane, StegVerse-org/.github#162).

* Provenance: the same bytes are at StegVerse-org/LLM-adapter#429 @5f5f7bbeea96d5f313effaa02f86b01196465247.
  #429 is the NODE_HEALTH_REPORTED producer and contains #428; it lands with or before #428. At #429 the interface doc
  only gains the producer section, sha256 `a363ff9bb498aa816adf9cc9d64559a389dec6acd3d02144056ee9c2540b91f0`.
  The same bytes are also at #430 @4e1499ab88144e8eae341058f7360b0d2a805b56, which carries #429 and adds the class B
  inputs; the ALLOW shape is unchanged. Its interface doc adds a section, sha256
  `6b523e3949d89a4cb85904559d5bb458b9796ec910fde2c26296096f0d3f8b62`.
  A final re-vendor follows once Lane B's stack (#429, #430, #431) settles.
* Source sha256: `fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58`.
* Interface: `docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md` at the same commit, sha256 `757d697ca385f5d4709d8b26e51119330bb685b4770512312313fc42460bb76d`.
* Do not edit the vendored file. `runtime.kv_interlock_endpoint.resolve_pinned_healthy_node_evaluator` re-derives the
  sha256 of these bytes before every resolution. On a mismatch, layer 1 fails closed.
* To re-pin, copy the file from the new LLM-adapter commit and update `PINNED_HEALTHY_NODE_EVALUATOR` in
  `runtime/kv_interlock_endpoint.py`.

Layer 1 (`KVInterlockRuntime.handle`, INTR_DEVICE_KV) calls
`evaluate(node_id, ledger_root=<checkout>/repository-ledger/StegVerse-org/LLM-adapter, transport_state="INSTALLED",
report_receipt_sha256=<cited report or None>, require_admission=True, repository="StegVerse-org/LLM-adapter")`.
* The chain is bound by contract location to the existing org-ledger contract location: StegVerse-org/.github
  `refs/stegverse/organization-ledger`, namespace `repository-ledger/StegVerse-org/LLM-adapter`. There is no new ref
  and no new ledger root.
* It maps any non-ALLOW to `KV_ACCESS_LAYER1_REFUSED` and keeps the evaluator's six fields as `health_evaluation`.
* KV never decides health itself.
* Until that chain is onboarded with a genesis, layer 1 is FAIL_CLOSED class B `HEALTHY_NODE_LEDGER_NOT_ONBOARDED`.
  Its retry entrypoint is StegVerse-org/LLM-adapter#431, the organization-ledger onboarding (Lane B draft, like
  StegVerse-SDK#558). #431 is FAIL_CLOSED until genesis and an admitted append route exist. Its contract's
  repository_ledger_location equals the binding above.
