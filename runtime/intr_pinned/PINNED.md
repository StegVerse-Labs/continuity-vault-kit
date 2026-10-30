# Pinned InTr code (vendored byte-identical, digest-pinned; not a dependency)

Everything under `runtime/intr_pinned/` is a byte copy of StegVerse-org/LLM-adapter at
`919851cb092d353bfe6a4271d3893f129dbc1c91` (StegVerse-org/LLM-adapter#430, which carried #429 @`6a51553a` and
#428 @`f2ccfc28`) and byte-identical at LLM-adapter main `649f0775a1c4a6203bbbca835234453c9b6aee1f` (the merge of #430), except `llm_adapter/supplied_epoch.py` (see below). Each file is checked by sha256 before every
resolution (`PINNED_INTR_FILES["vendored_files"]`, `PINNED_HEALTHY_NODE_EVALUATOR` in `runtime/kv_interlock_endpoint.py`).
Stdlib only: `llm_adapter/ed25519_verify.py` is the stdlib Ed25519 verify from #430.

## Dependency and admission order

The chain is merged, in the upstream's admission order: StegVerse-Labs/StegOS#430 (supersedes #426) as `d7b23eb5`, then
StegVerse-org/LLM-adapter#430 as `649f0775` (its head carried #429 and #428, so it admitted all three as one unit), then
this repository's #289 as `3d68fe1e`. The vendored evaluator and producer bytes equal LLM-adapter main, so
`PINNED_HEALTHY_NODE_EVALUATOR["on_upstream_main"]` is `True` and `layer1_prerequisites()` no longer records
`HEALTHY_NODE_EVALUATOR_STACK_NOT_ON_LLM_ADAPTER_MAIN`. A change to those bytes upstream is a re-vendor: the pin in
`runtime/kv_interlock_endpoint.py` and this file change together.

## What layer 1 reads

The pinned bare `evaluate(node_id, *, ledger_root, transport_state, report_receipt_sha256, require_admission,
repository)` over the requesting node's OWN transition ledger. The deployment binds
`{kind: NODE_OWN_LEDGER_CHAIN, ledger_root, genesis_receipt_sha256}`; a requester never names either. There is no org ledger,
no org-to-adapter crossing and no endpoint-kind model (Coordination's ruling (b) on StegVerse-org/.github#162).

| file | sha256 |
| --- | --- |
| `llm_adapter/healthy_node_evaluator.py` (evaluate; identical at #428, #429 and #430) | `fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58` |
| `llm_adapter/ed25519_verify.py` | `ab05e39a3e40b99f02ff199b178554e0ba435c3ff387dca3f896619770770232` |
| `llm_adapter/node_existence_readback.py` | `cbed113d7fe59fc0919953bad5a0a08cdaeba3ad70a4e728e572c360f6fb2fb7` |
| `llm_adapter/node_health_check_projection.py` | `97cb7043c3f43d9aab2f0a591e1eefb94d3b127efc542d75be8d7574ce561ae8` |
| `llm_adapter/node_health_report_producer.py` | `21249f2505505afd60eb14188ea638202f2926b207d64cfcf8c3bc5db2d9f361` |
| `llm_adapter/node_identity_binding_producer.py` | `ab578c921c6de5f50b9ecca50a71645e10582a051d2dd3417faa62d0dfdec01a` |
| `llm_adapter/node_ingress_boundary.py` (hashed, never executed; four constants read by AST) | `86bae0426956581b862dd085c4ac64bf0a4f7dc37b0309ca9d223a3306754339` |
| `llm_adapter/node_receipt_common.py` | `7e73b65b649c7238aa6ae47409282b2fb729157de083c093fe595611966e43c7` |
| `llm_adapter/supplied_epoch.py` (not in #430; see below) | `be91daad3d5557f810872731c3ea8cc36e1f13af569e1b7634f487fd36f44534` |
| `.stegverse/transition-ledger/emit.py` | `9579726de7ef915ac8cd61be1ba1c5ef6e34de4ca996504374b0dce7f7c2c9c3` |
| `.stegverse/transition-ledger/contract.json` (supporting data) | `a59040e8cabe6dc618af0ba340cb5563ce726f645a76248ccb354961d29144e7` |
| `.stegverse/heartbeat-awareness.json` (supporting data) | `87b1c4006d3829ea70626d481012791c557e97bcd580a6c3d5ccc61389a6951b` |

`supplied_epoch.py` is the shared supplied-epoch rule that KV's own receipt ledgers and crossing records call. #430 does
not carry it. Its bytes are the ones first published on the closed, unmerged #432 branch. Nothing in them places a ledger on
an organization or the adapter. Its provenance needs a home upstream (open item below).

## Removed on Coordination's ruling (b)

The vendored copies of the retired org-ledger / endpoint-anchor path, with their orphaned companions and every reference, test,
pin and digest naming them, are removed from the tree (StegVerse-org/.github#162 c6509636142: there is never an InTr hop inside
one org). None was a ledger-receipted record, and no ledger receipt on any org or KV ledger was touched. Git history and the
closed LLM-adapter#432 branch keep the bytes. `tests/test_kv_receipt_ledgers_no_431_and_crossing_wording.py` guards that they stay
gone. KV's own root-level `.stegverse/node-ledger/kv-ledger-head-signers.v1.json` is KV's own file and stays.

## Open items (FAIL_CLOSED, class D; owner Lane B, upstream)

* `llm_adapter/node_receipt_common.py` line 48 carries `LEDGER_LOCATION`, a string naming an organization-ledger ref and
  an adapter namespace. It is a byte copy of the same line in #429 and #430, so KV cannot edit it and keep the pin. The
  evaluator does not read it for KV's layer 1. The repair is an upstream change to #429/#430 that drops it, then a
  re-vendor that updates the digest here.
* `llm_adapter/supplied_epoch.py` provenance: it needs a home on a branch that will be merged, then a re-vendor.

The retired-name guard test skips this file because it has to name the removed files.
