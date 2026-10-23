# Pinned InTr healthy-node evaluator (vendored, digest-pinned; not a dependency)

`healthy_node_evaluator.py` is a byte-identical copy of `llm_adapter/healthy_node_evaluator.py` at
StegVerse-org/LLM-adapter@0b37fe3b786a2de687235f5d9d146af49ffee9cd (draft PR StegVerse-org/LLM-adapter#428,
LC-KV-13/14, owned by the InTr and Mesh Destinations lane, StegVerse-org/.github#162).

* Source sha256: `fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58`.
* Interface: `docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md` at the same commit, sha256 `757d697ca385f5d4709d8b26e51119330bb685b4770512312313fc42460bb76d`.
* Do not edit the vendored file. `runtime.kv_interlock_endpoint.resolve_pinned_healthy_node_evaluator` re-derives the
  sha256 of these bytes before every resolution. On a mismatch, layer 1 fails closed.
* To re-pin, copy the file from the new LLM-adapter commit and update `PINNED_HEALTHY_NODE_EVALUATOR` in
  `runtime/kv_interlock_endpoint.py`.

Layer 1 (`KVInterlockRuntime.handle`, INTR_DEVICE_KV) calls
`evaluate(node_id, ledger_root=<the KV-bound node-exchange transition ledger>, transport_state="INSTALLED",
report_receipt_sha256=<cited report or None>, require_admission=True)`.
* It maps any non-ALLOW to `KV_ACCESS_LAYER1_REFUSED` and keeps the evaluator's six fields as `health_evaluation`.
* KV never decides health itself.
* No `NODE_HEALTH_REPORTED` producer exists yet, so the real path is FAIL_CLOSED. Either no ledger is bound to KV
  (`LEDGER_HEAD_UNREADABLE`), or a bound ledger has no report (`HEALTH_REPORT_MISSING`).
