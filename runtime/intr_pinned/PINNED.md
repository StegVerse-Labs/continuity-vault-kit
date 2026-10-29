# Pinned InTr code (vendored byte-identical, digest-pinned; not a dependency)

Everything under `runtime/intr_pinned/` is a byte copy of StegVerse-org/LLM-adapter at
`919851cb092d353bfe6a4271d3893f129dbc1c91` (draft PR StegVerse-org/LLM-adapter#430, which carries #429 @`6a51553a` and
#428 @`f2ccfc28`), except `llm_adapter/supplied_epoch.py` (see below). Each file is checked by sha256 before every
resolution (`PINNED_INTR_FILES["vendored_files"]`, `PINNED_HEALTHY_NODE_EVALUATOR` in `runtime/kv_interlock_endpoint.py`).
Stdlib only: `llm_adapter/ed25519_verify.py` is the stdlib Ed25519 verify from #430.

## Dependency and admission order

None of #428, #429 or #430 is merged: all are open drafts, and LLM-adapter main (`e6af8c18`) has no
`healthy_node_evaluator.py`. KV layer 1 depends on them in the upstream's admission order:

> StegVerse-Labs/StegOS#426, then StegVerse-org/LLM-adapter#430, then #429, then #428 (#430's head carries #429 and #428,
> so admitting #430 admits all three as one unit).

#428 says "Never admit this PR alone". The cvk PR that carries this pin is not admitted before them. Until the stack is on
LLM-adapter main, `layer1_prerequisites()` records `HEALTHY_NODE_EVALUATOR_STACK_NOT_ON_LLM_ADAPTER_MAIN` (class B), and
the re-vendor that flips `on_upstream_main` is a change to the pin in `runtime/kv_interlock_endpoint.py` and this file.

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

Removed from the tree, together with every reference, test, pin and digest naming them (a guard test now asserts they
are gone): the six byte copies below and their orphaned companions. Git history and the closed #432 branch keep the bytes.
No ledger receipt on any org or KV ledger was touched. None of them was a ledger-receipted record: each was a vendored
copy, or a TEST-ONLY copy, of upstream #432 files.

| removed file | sha256 of the removed bytes |
| --- | --- |
| `runtime/intr_pinned/llm_adapter/endpoint_ledger_anchor.py` | `153cf121a51199da8432735d4b2fb34b396f7eaa24da80f1bf9c77040013ac09` |
| `runtime/intr_pinned/llm_adapter/endpoint_ledger_designation.py` | `d69dbb22a1446a22e84b86532f93d9698ac6dc3c82e6aa6ee20882c6764049d8` |
| `runtime/intr_pinned/llm_adapter/intr_transport_carrier.py` | `9d3e69c838d7e20533f0c5a06401b018948cb12a4201889f6b41d4b497df720f` |
| `runtime/intr_pinned/llm_adapter/org_ledger_location.py` | `b51e6a8bd39ba6fd83044222a3858a2cb0c437020e3e9abbe97c4494d41f2681` |
| `runtime/intr_pinned/.stegverse/node-ledger/kv-ledger-head-signers.v1.json` (the vendored copy only) | `758d798388599171c145e3d19ca4eb155ad3d3762a3721804da65c08ebc1fe72` |
| `tests/fixtures/intr_pinned_test_only/contract_with_431_location_and_pinned_genesis.json` (TEST-ONLY) | `ea81ca135bfd3b8e86a69251cf63d6f5aaa86fa46777dcec9370971dd0c5208a` |

Companions removed with them (same upstream, orphaned once the six are gone):
`runtime/intr_pinned/.stegverse/node-ledger/{node-ledger-opened-signers,org-ledger-head-signers,pinned-code-digests}.v1.json`,
`runtime/intr_pinned/schemas/{endpoint-kind,node-ledger-opened,node-ledger-opened-signed,node-ledger-opened-generation}.v1.json`, and the TEST-ONLY
fixtures `contract_with_431_repository_ledger_location.json`, `node.designation.json`, `org_ledger_harness.py` and
`org_ledger_test_genesis.json`. KV's own root-level `.stegverse/node-ledger/kv-ledger-head-signers.v1.json` is KV's own
file and stays.

## Open items (FAIL_CLOSED, class D; owner Lane B, upstream)

* `llm_adapter/node_receipt_common.py` line 48 carries `LEDGER_LOCATION`, a string naming an organization-ledger ref and
  an adapter namespace. It is a byte copy of the same line in #429 and #430, so KV cannot edit it and keep the pin. The
  evaluator does not read it for KV's layer 1. The repair is an upstream change to #429/#430 that drops it, then a
  re-vendor that updates the digest here.
* `llm_adapter/supplied_epoch.py` provenance: it needs a home on a branch that will be merged, then a re-vendor.

The retired-name guard test skips this file because it has to name the removed files.
