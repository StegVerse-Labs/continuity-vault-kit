# KV Native InTr Custody Boundary — Source Candidate

Updated: 2026-09-24
Canonical coordination: StegVerse-Labs/.github PR #2662
Original KV Goal: KV-CONNECTION-REVALIDATION-WORKER-001
COSV: 50000000102000 (unchanged)
Existing native KV owner: StegVerse-Labs/continuity-vault-kit
Source candidate PR: StegVerse-Labs/continuity-vault-kit#222
Authority effect: NONE_SOURCE_VALIDATION_ONLY
Runtime activation: NOT AUTHENTICALLY OBSERVED
Owner admission: AWAIT AUTHENTIC GENERATION-BOUND AI_SESSION_GATE

## Source defect and narrow repair

Previous `runtime/intr_lifecycle_closure.py` locally built a proposed
`stegverse.master_records.intr_lifecycle_custody/v1` record, labeled it
`ACCEPTED_FOR_CUSTODY`, and used its own computed hash to create
`MASTER_RECORDS_CUSTODY_RECORDED` and `COMPLETE`, without an independent
native Master Records acceptance. These local bytes proved no destination write.

The candidate now returns `PENDING_MASTER_RECORDS_CUSTODY` and a
`PROPOSED_FOR_CUSTODY` record by default: terminal_receipt=null,
master_records_custody_record=null, far_end_observation=null. It never promotes
an absent destination acknowledgement. The existing canonical Master Records
state-transition client, not CVK, must be supplied by the authorized resident
through the `native_custody_client` interface. The native client exposes exactly its existing three functions:
`build_state_receipt`, `submit_state_receipt` and
`reconstruct_state_receipt`. It does **not** expose
`replay_state_receipt`; the draft originally expected that nonexistent method.
The repaired CVK source invokes exactly these three functions. It returns
`MASTER_RECORDS_CUSTODY_RECORDED_AWAITING_INTR_REPLAY` only when the
real recording and independent reconstruction both verify exact digest,
proposal, predecessor and materialization identity. Even then it emits
**no terminal receipt or far-end completion observation**. The existing
Universal InTr/SDK manifest-result path separately owns full replay,
transition-closure equality and result lineage. That existing replay interface
is not replaced, mocked as live or added to the MR client.

The candidate checks the native receipt's canonical schema, exact source
proposal SHA-256, exact materialization identity, immediate predecessor,
no authority grant, returned RECORDED and required-evidence/reconstruction
PASS, exact receipt/reconstructed digest equality, independent destination
readback of the original receipt and retained native master_record_ref.
Native receipt digest is distinct from the nonauthorizing proposal digest.
The existing Universal InTr/SDK route must independently verify complete
graph replay before any terminal result can be returned.

The public function does not emit a terminal receipt from native acceptance
alone. The local proposed record hash and the native accepted state-transition
receipt digest are separately retained. The pure terminal-shape verifier is
exercised only with inert TEST_ONLY_NOT_AUTHENTIC_MASTER_RECORDS fixtures;
it cannot satisfy production runtime predicates.

## Existing owners and boundaries

- CVK revalidation proof owner #119 and .github original worker #366 / proof intake #424 remain distinct from general InTr lifecycle closure.
- SDK 1.4-development manifest/result-lineage client already enforces exact ordered native Master Records closures; no KV-specific SDK route is installed by this patch. Evaluate compatibility with existing Universal InTr first and require canonical authorization before installing a new route.
- LLM-adapter #271 owns active Service Gateway query-secret-safe logging proof.
- TVC #317/#328 owns callback/credential authority. Owner-present Google consent, CONNECT/VERIFY and identity-preserving KV #2 set membership are not authorized by this source.
- Device/KV/SKAP proof has a separate existing Goal. Healer is optional carrier, never a KV completion predicate.
- No new runner, runtime, scheduler, dispatcher, ledger, credential authority or second device.

## Adversarial tests and exact-head validation

`tests/test_intr_lifecycle_closure.py` now tests local proposal pending,
synthetic native success, wrong predecessor, wrong proposal digest, wrong
materialization ID, missing reconstruction, tampered native acceptance,
incorrect independently reconstructed bytes, wrong destination reference,
missing replay and authority escalation. Hosted `intr-lifecycle-closure.yml`
verifies that default public API no longer self-issues terminal custody.
Exact PR head must be validated before merge. This source candidate must remain
unmerged until authentic AI_SESSION_GATE/owner disposition and all required
source checks are green. No provider or actual Master Records runtime effect
is asserted by CI fixtures.

## Original identities

Google Drive request:
SITE-CLOUD-KV-4347408852127319cbda574f02e03edb

Existing cloud identity:
kvi_a31335d2cc3745fa987b635432cfed2c

Existing local KV #1:
kvi_0d5d4cfd531db51bbcf7fdfc0311f5dc

Original TVC reusable invocation:
KV-CONNECTION-REVALIDATION-WORKER-001:TVC-CAPABILITY-RUNTIME-002:QUERY-SECRET-SAFE-INGRESS-001

All remain unchanged. No Google owner consent, CONNECT/VERIFY or KV #2
materialization before authentic active query-secret-safe ingress, TVC callback
preflight, provider-result evidence, Interlock/InTr admission, native Master
Records closure and separately required roundtrip proof.
