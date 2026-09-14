# KV AI Persistence Classes Mirror Handoff

Status: ACTIVE / FOUR-CLASS-SOURCE-COMPLETE / PERSONAL-KV-MEMORY-SOURCE-COMPLETE / MACHINE-RECONSTRUCTION-VERIFIER-VALIDATED / HB-RECEIPT-OBSERVER-VALIDATED / LIVE-EVIDENCE-OPEN
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-AI-PERSISTENCE-001
Canonical Task Registry: StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json
COSV task.v1: 20111110110000
Created: 2026-08-27
Last updated: 2026-09-13

## Goal

Formalize distinct persistent KV ecosystems for Personal Assistant AI, Organizational AI, StegVerse ecosystem AI, and machine execution agents while keeping the AI/model/runtime replaceable and each KV persistent within its own authority domain.

The first fully source-complete operational profile is `PERSONAL_KV / PERSON / PERSONAL_ASSISTANT_AI`: KnowledgeVault is the durable memory substrate while Auri or another model receives only bounded, provenance-preserving context. Model/provider memory is non-canonical and grants no authority.

## Canonical coordination

- canonical task record: `StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json`;
- current COSV `task.v1`: `20111110110000`;
- registry coordination state: `IN_PROGRESS`;
- provider-ingress bridge: `StegVerse-org/LLM-adapter/docs/KV_AI_MEMORY_CONTEXT_BRIDGE_MIRROR_HANDOFF.md`;
- resident binding: `StegVerse-Labs/.github/docs/KV_AI_MEMORY_RESIDENT_EXECUTION_MIRROR_HANDOFF.md`.

Task Registry, source state, COSV, request files, layouts, fixtures, reconstruction verifiers, HeartBeat observers, and CI do not mint runtime authority. WorkerCoordinator claim/fence authority and authentic Interlock/InTr admission remain separate requirements.

## Four canonical classes and concrete layouts

Machine-readable source:

- `schemas/kv-ai-persistence-layouts.schema.json`;
- `specs/kv-ai-persistence-layouts.v1.json`;
- `scripts/validate_kv_ai_persistence_layouts.py`;
- `tests/test_kv_ai_persistence_layouts.py`;
- `docs/KV_AI_PERSISTENCE_LAYOUTS.md`.

```text
PERSONAL_KV / PERSON / PERSONAL_ASSISTANT_AI
  01_Notes
  03_Records
  05_Projects
  _AI
  _System/AI/Memory/Receipts

ORGANIZATIONAL_KV / ORGANIZATION / ORGANIZATIONAL_AI
  _Organization/Policy
  _Organization/Roles
  _Organization/Delegations
  _Organization/SharedResources
  _Organization/Workflows
  _Organization/InstitutionalMemory
  _Organization/Receipts

STEGVERSE_KV / STEGVERSE_ECOSYSTEM / STEGVERSE_AI
  _StegVerse/EcosystemState
  _StegVerse/ServiceRegistry
  _StegVerse/GovernanceState
  _StegVerse/WorkerState
  _StegVerse/Evidence
  _StegVerse/Recovery
  _StegVerse/Receipts

MACHINE_KV / MACHINE_EXECUTION_ENTITY / EXECUTION_AGENT
  _Machine/Identity
  _Machine/Workloads
  _Machine/Assignments
  _Machine/ExecutionState
  _Machine/Liveness
  _Machine/Checkpoints
  _Machine/Reconstruction
  _Machine/Receipts
```

Each state domain is mutable only after applicable InTr admission. Provider authority, model authority, and direct cross-class mutation are false. These are logical provider-neutral layouts; validation does not instantiate provider storage or activate an AI/runtime.

## Complete directed cross-class matrix

All 12 directed source→target class pairs are implemented in:

- `specs/kv-cross-class-intr-transition-fixtures.v1.json`;
- `scripts/validate_kv_cross_class_intr_fixtures.py`;
- `tests/test_kv_cross_class_intr_fixtures.py`.

Every pair requires InTr + Interlock, exact source-state and target-admission hash binding, and a receipt. Direct mutation, authority transfer, context-as-authority, model/provider authority, and secret plaintext in receipts are forbidden. Negative tests reject missing/duplicate/same-class pairs and each authority weakening.

## Personal-KV/Auri source path

```text
PERSONAL_KV readable entry projections
-> deterministic bounded context packet
-> authentic memory-packet InTr ALLOW
-> existing WorkerCoordinator fresh fenced execution
-> exact ProviderRequest materialization in bound state
-> existing provider-request InTr / TVC / response / egress path
-> optional NONE_PROPOSAL_ONLY memory write proposal
-> authentic target-KV ADMITTED/ALLOW evidence
-> write-once/idempotent target-KV materialization
-> exact-byte readback receipt
```

Source surfaces include `runtime/kv_ai_memory_substrate.py`, `scripts/stage_kv_ai_memory_resident_inputs.py`, `runtime/kv_ai_memory_writeback_store.py`, the LLM-adapter memory bridge/materializer, and the `.github` fenced resident worker. No source module decides admission, authenticates a provider, resolves provider credentials, mints a WorkerCoordinator claim/fence, or promotes model output into KV authority.

## Machine-KV provider-neutral reconstruction

`runtime/machine_kv_reconstruction.py` now implements the deterministic reconstruction decision contract for Machine-KV. It requires:

- distinct source and target providers;
- provider authority false on both sides;
- one exact canonical Machine-KV state-manifest hash observed on both sides;
- the same `machine_kv_id` at source, manifest, and target;
- separate source and target InTr `ALLOW` receipt references;
- credential material absent;
- provider sessions unable to transfer Machine-KV identity.

It performs no provider I/O and grants no transition authority. Passing tests prove the verifier contract only. The goal still requires authentic observations from two real provider executions before `MACHINE_KV_CROSS_PROVIDER_RECONSTRUCTION_OBSERVED` can be satisfied.

## HeartBeat receipt observation

`runtime/kv_heartbeat_receipt_observer.py` binds HeartBeat timing/freshness/correlation only to the exact hash of an already-verified KV receipt. It rejects any HeartBeat claim to execution, transition, or KV-state authority and performs no admission, state mutation, or receipt minting.

```text
verified KV receipt first
-> exact receipt hash
-> HeartBeat observation second
-> FRESH / STALE / UNKNOWN correlation projection
-> NONE_OBSERVATION_ONLY
```

The observer source is validated. An authentic HB observation bound to a real verified KV transition remains an evidence predicate and is not inferred from tests.

## Shared safety invariants

```text
SKAP required: true
InTr required: true
provider is authority: false
model is authority: false
HeartBeat is state authority: false
context sharing transfers authority: false
direct cross-class state mutation: false
memory packet source != memory packet admission
write proposal != write authorization
writeback source != admission authority
cross-class InTr receipt required: true
least authority: true
ambiguous scope: FAIL_CLOSED
```

## Hosted validation evidence

Previously validated source:

- KV memory baseline `34798372339` — SUCCESS;
- LLM bridge/materializer `34803228613`, `34803228620` — SUCCESS;
- resident `.github` binding `34803483965` — SUCCESS;
- private staging/writeback `34803817371` — SUCCESS;
- four-class layouts + 12-pair matrix `34804237690` — SUCCESS; security `34804237681` and guardrails `34804237711` — SUCCESS.

Machine reconstruction + HB observer combined source head `f00401fa2e0fda6c285acf3d32b30e2d9d6d8fa6`:

- validation run `34804394797` / job `103853270280` — SUCCESS;
- security baseline `34804394870` / job `103853270510` — SUCCESS;
- KV guardrails `34804394755` / job `103853270143` — SUCCESS;
- release integrity `34804394746` / job `103853270230` — SUCCESS;
- release-readiness validation `34804406677` / job `103853304092` — SUCCESS;
- outcome observation `34804416022` / job `103853334399` — SUCCESS.

The validation run passed persistence classes, concrete layouts, all cross-class fixtures, seven Machine-KV reconstruction tests, seven HeartBeat observer tests, Personal-KV memory substrate, resident staging, and evidence-gated writeback.

No CI result is live Auri/KV execution, provider reconstruction, or HeartBeat observation evidence.

## Remaining work

Source construction for the original persistence-class checklist is now materially complete. Remaining goal completion is evidence/integration:

1. **Personal-KV live proof:** real packet admission → current WorkerCoordinator ProviderRequest materialization → provider/model path → target-KV admitted writeback/readback.
2. **Machine-KV authentic reconstruction:** obtain source and target provider observations for the same exact Machine-KV state manifest and verify them with the source-complete reconstruction verifier.
3. **Authentic HeartBeat observation:** bind an actual HB observation to a verified KV transition receipt using the source-complete observer.
4. Instantiate/use Organizational-KV and StegVerse-KV layouts only through their own authority/admission paths; source layout validity does not claim runtime instances.
5. Do not release/tag until applicable runtime evidence predicates are satisfied. When release-ready, create the required separate propagation-verification task for Site, Publisher, admissibility-wiki, and stegguardian-wiki.

## State distinctions

```text
architecture: CANONICALIZED
canonical task registry: INSTALLED / IN_PROGRESS
COSV task.v1: 20111110110000
four persistence classes: CANONICALIZED
four concrete logical layouts: IMPLEMENTED / HOSTED VALIDATED
all 12 directed cross-class fixtures: IMPLEMENTED / HOSTED VALIDATED
Personal-KV memory source loop: IMPLEMENTED / HOSTED VALIDATED
fenced resident ProviderRequest binding: IMPLEMENTED / HOSTED VALIDATED
Machine-KV reconstruction verifier: IMPLEMENTED / HOSTED VALIDATED
HeartBeat verified-receipt observer: IMPLEMENTED / HOSTED VALIDATED
private resident input bytes: NOT OBSERVED
live memory-packet InTr admission: NOT OBSERVED
live ProviderRequest materialization: NOT OBSERVED
live Auri/model consumption: NOT OBSERVED
live target-KV writeback/readback: NOT OBSERVED
Machine-KV authentic cross-provider reconstruction: NOT OBSERVED
authentic HB-to-KV receipt observation: NOT OBSERVED
released/tagged: NOT PERFORMED
activated: NOT ACTIVATED
```
