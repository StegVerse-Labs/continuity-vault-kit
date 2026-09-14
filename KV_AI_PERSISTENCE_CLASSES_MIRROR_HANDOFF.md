# KV AI Persistence Classes Mirror Handoff

Status: ACTIVE / FOUR-CLASS-LAYOUTS-VALIDATED / CROSS-CLASS-MATRIX-VALIDATED / PERSONAL-KV-MEMORY-SOURCE-COMPLETE / LIVE-INTR-ACTIVATION-OPEN
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

Task Registry, source state, COSV, request files, layouts, fixtures, and CI do not mint runtime authority. WorkerCoordinator claim/fence authority and authentic Interlock/InTr admission remain separate requirements.

## Canonical classes and concrete layouts

The four persistence classes now have explicit provider-neutral logical layouts in:

- `schemas/kv-ai-persistence-layouts.schema.json`;
- `specs/kv-ai-persistence-layouts.v1.json`;
- `scripts/validate_kv_ai_persistence_layouts.py`;
- `tests/test_kv_ai_persistence_layouts.py`.

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

Each state domain is mutable only after InTr admission. Provider authority, model authority, and direct cross-class state mutation are false. The paths are logical provider-neutral KV layout contracts; source validation does not instantiate or activate any physical provider copy.

## Complete directed cross-class matrix

Cross-class transfer is no longer represented by a single Personal→Organization example. The source now covers all 12 directed class pairs through:

- `specs/kv-cross-class-intr-transition-fixtures.v1.json`;
- `scripts/validate_kv_cross_class_intr_fixtures.py`;
- `tests/test_kv_cross_class_intr_fixtures.py`.

For every source class and every different target class, the expanded fixture requires:

```text
protocol = InTr
Interlock required = true
direct state mutation = false
authority transfer = false
context share grants authority = false
model output grants authority = false
provider grants authority = false
receipt required = true
secret plaintext in receipt = false
exact source-state hash + exact target-admission hash required
```

Negative tests reject missing/duplicate/same-class pairs, authority transfer, direct mutation, secret receipt plaintext, and disabled receipt requirements.

## Personal-KV/Auri source path

Implemented source includes bounded context selection, private resident staging, exact memory-packet admission binding, fenced WorkerCoordinator ProviderRequest materialization, non-authorizing write proposals, and evidence-gated target-KV exact-byte writeback/readback.

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

Key source surfaces:

- `runtime/kv_ai_memory_substrate.py`;
- `scripts/stage_kv_ai_memory_resident_inputs.py`;
- `runtime/kv_ai_memory_writeback_store.py`;
- `StegVerse-org/LLM-adapter/llm_adapter/kv_memory_context_bridge.py`;
- `StegVerse-org/LLM-adapter/scripts/materialize_kv_memory_provider_request.py`;
- `StegVerse-Labs/.github/workers/kv_ai_memory_resident_worker.py`.

No source module decides InTr admission, authenticates a provider, resolves provider credentials, grants a WorkerCoordinator claim/fence, or promotes a model response into KV authority.

## Safety invariants

```text
SKAP required: true
InTr required: true
provider is authority: false
model is authority: false
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

Existing validated Personal-KV path:

- KV memory baseline run `34798372339` — SUCCESS;
- KV guardrails run `34798372325` — SUCCESS;
- security baseline run `34798372302` — SUCCESS;
- LLM bridge/materializer runs `34803228613` and `34803228620` — SUCCESS;
- resident `.github` binding run `34803483965` — SUCCESS;
- staging/writeback validation run `34803817371` — SUCCESS.

Four-class layout and complete cross-class matrix head `64edbec6db816b112c85ce9c721233f62c07439c`:

- validation run `34804237690` / job `103852803777` — SUCCESS;
- security baseline run `34804237681` / job `103852803761` — SUCCESS;
- KV guardrails run `34804237711` / job `103852803979` — SUCCESS.

The successful validation run covered persistence classes, 9 concrete-layout tests, the canonical cross-class transition validator, all 12 directed fixtures and their negative tests, the Personal-KV memory substrate, private staging, and evidence-gated writeback.

The immediately preceding matrix run failed only because the new fixture validator executed as a script without repository-root import resolution. Adding the same fail-safe root insertion pattern used by existing validators repaired the invocation; the repaired head then passed all checks.

No CI result is live Auri/KV execution evidence.

## Remaining work

The major remaining predicates are now runtime/reconstruction integration rather than missing class definitions:

1. **Personal-KV live proof:** real packet admission → current WorkerCoordinator ProviderRequest materialization → provider/model path → target-KV admitted writeback/readback.
2. **Machine-KV reconstruction proof:** reuse existing provider-neutral/cross-platform recovery mechanisms to prove Machine-KV identity and exact state continuity across two storage providers without provider authority.
3. **HeartBeat observation binding:** bind HB observations only to verified KV transition receipts, preserving HB as timing/freshness/observability rather than state authority.
4. Instantiate/use Organizational-KV and StegVerse-KV layouts only through their own authority/admission paths; layout source is validated but runtime instances are not claimed.
5. Release/tag only after the applicable evidence predicates are satisfied; then create a separate propagation-verification task for Site, Publisher, admissibility-wiki, and stegguardian-wiki.

## State distinctions

```text
architecture: CANONICALIZED
canonical task registry: INSTALLED / IN_PROGRESS
COSV task.v1: 20111110110000
four persistence classes: CANONICALIZED
four concrete logical layouts: IMPLEMENTED / HOSTED VALIDATED
all 12 directed cross-class fixtures: IMPLEMENTED / HOSTED VALIDATED
Personal-KV context/packet source: IMPLEMENTED / VALIDATED
private resident stager: IMPLEMENTED / VALIDATED
LLM memory bridge + exact ProviderRequest materializer: IMPLEMENTED / VALIDATED
WorkerCoordinator resident binding: IMPLEMENTED / VALIDATED
evidence-gated target-KV writeback/readback source: IMPLEMENTED / VALIDATED
private resident input bytes: NOT OBSERVED
live memory-packet InTr admission: NOT OBSERVED
live ProviderRequest materialization: NOT OBSERVED
live Auri/model consumption: NOT OBSERVED
live target-KV writeback/readback: NOT OBSERVED
Machine-KV cross-provider reconstruction proof: OPEN
HB receipt observation binding: OPEN
released/tagged: NOT PERFORMED
activated: NOT ACTIVATED
```
