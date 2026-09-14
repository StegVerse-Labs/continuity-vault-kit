# KV AI Persistence Classes Mirror Handoff

Status: ACTIVE / PERSONAL-KV-MEMORY-SOURCE-COMPLETE / RESIDENT-BINDING-VALIDATED / LIVE-INTR-ACTIVATION-OPEN
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-AI-PERSISTENCE-001
Canonical Task Registry: StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json
COSV task.v1: 20111110110000
Created: 2026-08-27
Last updated: 2026-09-13

## Goal

Formalize distinct persistent KV ecosystems for Personal Assistant AI, Organizational AI, StegVerse ecosystem AI, and machine execution agents while keeping the AI/model/runtime replaceable and the applicable KV persistent within its authority domain.

The first operationalized memory profile is `PERSONAL_KV / PERSON / PERSONAL_ASSISTANT_AI`: KnowledgeVault is the durable memory substrate while Auri or another model receives only bounded, provenance-preserving context. Model/provider memory is non-canonical and grants no authority.

## Canonical coordination

- canonical task record: `StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json`;
- source task vector: `StegVerse-Labs/.github/control/task-vectors/SV-KV-AI-PERSISTENCE-001.json`;
- task-vector index fragment: `StegVerse-Labs/.github/control/task-vector-index.d/SV-KV-AI-PERSISTENCE-001.json`;
- current COSV `task.v1`: `20111110110000`;
- registry coordination state: `IN_PROGRESS`;
- provider-ingress bridge: `StegVerse-org/LLM-adapter/docs/KV_AI_MEMORY_CONTEXT_BRIDGE_MIRROR_HANDOFF.md`;
- resident binding: `StegVerse-Labs/.github/docs/KV_AI_MEMORY_RESIDENT_EXECUTION_MIRROR_HANDOFF.md`.

Task Registry, source state, COSV, request files, and CI do not mint runtime authority. WorkerCoordinator claim/fence authority and authentic Interlock/InTr admission remain separate requirements.

## Implemented Personal-KV source

Persistence-class foundation:

- `schemas/kv-ai-persistence-classes.schema.json`
- `specs/kv-ai-persistence-classes.v1.json`
- `scripts/validate_kv_ai_persistence_classes.py`
- `tests/test_kv_ai_persistence_classes.py`

AI-memory substrate:

- `schemas/kv-ai-memory-context-request.schema.json`
- `schemas/kv-ai-memory-context-packet.schema.json`
- `schemas/kv-ai-memory-write-proposal.schema.json`
- `specs/kv-ai-memory-substrate.v1.json`
- `runtime/kv_ai_memory_substrate.py`
- `scripts/validate_kv_ai_memory_substrate.py`
- `tests/test_kv_ai_memory_substrate.py`
- `docs/KV_AI_MEMORY_SUBSTRATE.md`

Private resident-input staging:

- `scripts/stage_kv_ai_memory_resident_inputs.py`
- `tests/test_stage_kv_ai_memory_resident_inputs.py`

Evidence-gated target-KV writeback:

- `runtime/kv_ai_memory_writeback_store.py`
- `tests/test_kv_ai_memory_writeback_store.py`

Provider-ingress bridge in `StegVerse-org/LLM-adapter`:

- `llm_adapter/kv_memory_context_bridge.py`
- `scripts/materialize_kv_memory_provider_request.py`
- `tests/test_kv_memory_context_bridge.py`
- `tests/test_kv_memory_provider_request_materializer.py`
- `docs/KV_AI_MEMORY_CONTEXT_BRIDGE_MIRROR_HANDOFF.md`

Resident execution binding in `StegVerse-Labs/.github`:

- `docs/KV_AI_MEMORY_RESIDENT_EXECUTION_MIRROR_HANDOFF.md`
- `handoffs/SV-KV-AI-PERSISTENCE-001.json`
- `workers/kv_ai_memory_resident_worker.py`
- `scripts/consume_kv_ai_memory_resident_request.py`
- `control/worker-registry.d/kv-ai-memory-resident-001.json`
- `control/process-worker-adapters.d/kv-ai-memory-resident-001.json`
- `control/resident-execution-request.d/kv-ai-memory-resident-001.json`
- `tests/test_kv_ai_memory_resident_binding.py`

## Canonical classes

```text
PERSONAL_KV       authority: PERSON                     AI role: PERSONAL_ASSISTANT_AI
ORGANIZATIONAL_KV authority: ORGANIZATION               AI role: ORGANIZATIONAL_AI
STEGVERSE_KV      authority: STEGVERSE_ECOSYSTEM        AI role: STEGVERSE_AI
MACHINE_KV        authority: MACHINE_EXECUTION_ENTITY   AI role: EXECUTION_AGENT
```

## Personal Assistant memory source path

```text
PERSONAL_KV readable entry projections
-> bounded context request
-> deterministic same-authority selection
-> private resident staging of exact context packet
-> authentic memory-packet Interlock/InTr admission
-> existing WorkerCoordinator fresh fenced execution
-> fenced bound-state ProviderRequest materialization
-> existing provider-request Interlock/InTr admission
-> existing TV/TVC provider operation when required
-> PERSONAL_ASSISTANT_AI / Auri response
-> exact-response egress admission
-> optional non-authorizing memory write proposal
-> authentic target-KV ADMITTED/ALLOW evidence
-> write-once/idempotent target-KV materialization
-> exact-byte readback receipt
```

`runtime/kv_ai_memory_substrate.py` owns deterministic KV context selection and non-authorizing write-proposal construction. `scripts/stage_kv_ai_memory_resident_inputs.py` stages the exact context packet and provider request input into private resident state but deliberately does **not** create `inputs/memory-packet-admission.json`; that file must come from authentic Interlock/InTr admission.

The `.github` resident lane uses `ProcessWorkerAdapter` fenced bound state at `~/.stegverse/state/kv-ai-memory-resident`. The request consumer checks only for the presence of private files and does not read their bytes. Once all three exist, the existing WorkerCoordinator may claim/fence the canonical task and use the already-local LLM-adapter materializer.

`runtime/kv_ai_memory_writeback_store.py` closes the target-side source loop without creating admission authority. It accepts only an already-admitted exact write proposal whose proposal ID, target KV instance, and content hash match the admission; requires both Interlock and InTr receipt references plus explicit persistence authorization; then writes new exact bytes or accepts an idempotent exact-byte replay, reads the bytes back, verifies SHA-256 identity, and emits a receipt. Different-byte collisions fail closed.

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

AI-eligible secret-marked content, class crossing, and authority crossing fail closed. Selection is deterministic and lexical; it does not claim semantic/vector retrieval. Oversized entries are skipped rather than silently truncated. Provider-request staging rejects credential-like fields. A memory write proposal fixes `execution_authorized=false`, `model_is_authority=false`, and `authority_effect=NONE_PROPOSAL_ONLY`.

## Hosted validation state

KV memory baseline:

- run `34798372339` / job `103835833007` — SUCCESS;
- run `34798372325` / job `103835832752` — KV guardrails SUCCESS;
- run `34798372302` / job `103835832491` — security baseline SUCCESS.

LLM bridge/materializer head `920fedd13a182636c80a30fc10d9482ee21de57a`:

- run `34803228613` / job `103849905207` — SUCCESS;
- run `34803228620` / job `103849906564` — SUCCESS.

Resident `.github` binding:

- run `34803483965` / job `103850649371` — SUCCESS.

Current KV staging/writeback validation head `c74069dc635b26768ce8cd1b75609a0ed6f3fa39`:

- job `103851605536` — validation SUCCESS, including private resident staging tests and evidence-gated writeback tests;
- security, guardrail, and release-integrity checks are independently required and must retain their own conclusions.

The immediately preceding stager workflow failure was traced to pytest not being installed; adding the explicit pytest install repaired the workflow. It was not a stager logic failure.

No CI result is live Auri/KV execution evidence.

## Remaining work

For the Personal-KV/Auri memory lane, source implementation is now complete through exact target-KV readback. Remaining completion work is authentic same-execution runtime evidence:

1. materialize private resident packet + provider request input from real readable Personal-KV state;
2. obtain authentic memory-packet InTr `ALLOW` bound to that exact packet;
3. let the existing `kv_ai_memory` consumer + WorkerCoordinator materialize the exact ProviderRequest in fenced bound state;
4. continue through existing provider ingress, TV/TVC operation where applicable, response, Master Records continuation, and egress InTr evidence;
5. create the non-authorizing memory write proposal from the resulting interaction;
6. obtain authentic target-KV admission bound to the exact proposal;
7. run the evidence-gated writeback store and preserve its exact-byte readback receipt.

Broader goal work remains for concrete Organizational-KV, StegVerse-KV, and Machine-KV layouts, cross-class fixtures, provider reconstruction proof, and HeartBeat observation binding without state authority. These are distinct from completing the first Personal-KV/Auri memory profile.

When release-ready, tag/release and create a separate propagation-verification task for Site, Publisher, admissibility-wiki, and stegguardian-wiki.

## State distinctions

```text
architecture: CANONICALIZED
canonical task registry: INSTALLED / IN_PROGRESS
COSV task.v1: 20111110110000
Personal-KV context selection/packet source: IMPLEMENTED / VALIDATED
private resident input stager: IMPLEMENTED / VALIDATED
LLM memory bridge: IMPLEMENTED / VALIDATED
LLM exact resident ProviderRequest materializer: IMPLEMENTED / VALIDATED
WorkerCoordinator resident binding: IMPLEMENTED / VALIDATED
memory write proposal source: IMPLEMENTED / VALIDATED
evidence-gated target-KV writeback/readback store: IMPLEMENTED / VALIDATED
private resident input bytes: NOT OBSERVED
memory packet live InTr admission: NOT OBSERVED
live ProviderRequest materialization: NOT OBSERVED
live Auri/model consumption: NOT OBSERVED
live target-KV writeback/readback: NOT OBSERVED
released/tagged: NOT PERFORMED
activated: NOT ACTIVATED
```
