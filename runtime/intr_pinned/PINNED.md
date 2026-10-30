# Pinned InTr code (vendored byte-identical, digest-pinned; not a dependency)

Everything under `runtime/intr_pinned/` is a byte copy of StegVerse-org/LLM-adapter main
`fb5ae1cbf7d41de82653394fa09cab7039e7312e` (the merge of StegVerse-org/LLM-adapter#436, parents `649f0775` and `33506b99`;
`PINNED_INTR_FILES["upstream_main_commit"]`). #436 changed only `llm_adapter/node_receipt_common.py` (it dropped the org-ledger
`LEDGER_LOCATION` constant), so every other vendored file is also byte-identical at `649f0775` (the merge of #430) and at
`919851cb092d353bfe6a4271d3893f129dbc1c91` (StegVerse-org/LLM-adapter#430, which carried #429 @`6a51553a` and #428 @`f2ccfc28`).
Only `node_receipt_common.py` differs from those earlier heads, by that dropped constant. Every file under this directory is a
byte copy of LLM-adapter main (`supplied_epoch.py` moved out; see below). Each file is checked by sha256 before every
resolution (`PINNED_INTR_FILES["vendored_files"]`, `PINNED_HEALTHY_NODE_EVALUATOR` in `runtime/kv_interlock_endpoint.py`).
Stdlib only: `llm_adapter/ed25519_verify.py` is the stdlib Ed25519 verify from #430.

## Dependency and admission order

The chain is merged, in the upstream's admission order: StegVerse-Labs/StegOS#430 (supersedes #426) as `d7b23eb5`, then
StegVerse-org/LLM-adapter#430 as `649f0775` (its head carried #429 and #428, so it admitted all three as one unit), then
this repository's #289 as `3d68fe1e` and #290 as `44e7ae56`, and LLM-adapter#436 as `fb5ae1cb`. The vendored evaluator and producer bytes equal LLM-adapter main, so
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
| `llm_adapter/node_receipt_common.py` (LLM-adapter main @fb5ae1cb, after #436; zero `LEDGER_LOCATION`) | `3e1141f0be7b00b88d47bc60d84bbb3e5ba36ad43c38a621d6a0acc8c2ae1c12` |
| `.stegverse/transition-ledger/emit.py` | `9579726de7ef915ac8cd61be1ba1c5ef6e34de4ca996504374b0dce7f7c2c9c3` |
| `.stegverse/transition-ledger/contract.json` (supporting data) | `a59040e8cabe6dc618af0ba340cb5563ce726f645a76248ccb354961d29144e7` |
| `.stegverse/heartbeat-awareness.json` (supporting data) | `87b1c4006d3829ea70626d481012791c557e97bcd580a6c3d5ccc61389a6951b` |

`node_receipt_common.py` was re-vendored byte for byte from LLM-adapter main @`fb5ae1cb`; its previous digest was
`7e73b65b649c7238aa6ae47409282b2fb729157de083c093fe595611966e43c7` (at #429, #430 and main @`649f0775`).

`supplied_epoch.py` is no longer here. It was never on LLM-adapter main (its bytes came from the closed, unmerged #432 branch) and
nothing in the adapter uses it, so it is not a pinned byte copy of an adapter file. KV's own receipt ledgers and crossing records
call it, so it is owned natively as `runtime/kv_supplied_epoch.py` (same functions; `supplied_epoch_failure` is byte-identical to
StegVerse-org/.github `resident-runtime/organization_egress_boundary.py`'s, whose `ast.get_source_segment` + newline digest is
`7f36f0e697cadc91acd27af121eee3fc460b887ec67cfa258727bfccec0ca5f8`). It has no digest pin and no upstream-pin claim.

## Removed on Coordination's ruling (b)

The vendored copies of the retired org-ledger / endpoint-anchor path, with their orphaned companions and every reference, test,
pin and digest naming them, are removed from the tree (StegVerse-org/.github#162 c6509636142: there is never an InTr hop inside
one org). None was a ledger-receipted record, and no ledger receipt on any org or KV ledger was touched. Git history and the
closed LLM-adapter#432 branch keep the bytes. `tests/test_kv_receipt_ledgers_no_431_and_crossing_wording.py` guards that they stay
gone. KV's own root-level `.stegverse/node-ledger/kv-ledger-head-signers.v1.json` is KV's own file and stays.

## Open items

None. The two former open items are closed: `LEDGER_LOCATION` was dropped upstream (LLM-adapter#436, `fb5ae1cb`) and re-vendored
here, and `supplied_epoch.py` is native to this repository (above).

The retired-name guard test skips this file because it has to name the removed files.
