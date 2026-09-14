# KV AI Persistence Classes Mirror Handoff

Status: ACTIVE / AI-MEMORY-SOURCE-VALIDATED / PRIVATE-RESIDENT-STAGING-IMPLEMENTED / RESIDENT-PROVIDERREQUEST-BINDING-VALIDATED / LIVE-INTR-ACTIVATION-OPEN
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-AI-PERSISTENCE-001
Canonical Task Registry: StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json
COSV task.v1: 20111110110000
Created: 2026-08-27
Last updated: 2026-09-13

## Goal

Formalize distinct persistent KV ecosystems for Personal Assistant AI, Organizational AI, StegVerse ecosystem AI, and machine execution agents while keeping the AI/model/runtime replaceable and the applicable KV persistent within its authority domain.

The first operationalized memory profile is `PERSONAL_KV / PERSON / PERSONAL_ASSISTANT_AI`: KnowledgeVault is the durable memory substrate while Auri or another model receives only a bounded, provenance-preserving context packet. Model/provider memory is non-canonical and grants no authority.

## Canonical coordination

- canonical task record: `StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json`;
- source task vector: `StegVerse-Labs/.github/control/task-vectors/SV-KV-AI-PERSISTENCE-001.json`;
- task-vector index fragment: `StegVerse-Labs/.github/control/task-vector-index.d/SV-KV-AI-PERSISTENCE-001.json`;
- current COSV `task.v1`: `20111110110000`;
- registry coordination state: `IN_PROGRESS`;
- provider-ingress bridge: `StegVerse-org/LLM-adapter/docs/KV_AI_MEMORY_CONTEXT_BRIDGE_MIRROR_HANDOFF.md`;
- resident binding: `StegVerse-Labs/.github/docs/KV_AI_MEMORY_RESIDENT_EXECUTION_MIRROR_HANDOFF.md`.

Task Registry, source state, COSV, request files, and CI do not mint runtime authority. WorkerCoordinator claim/fence authority and authentic Interlock/InTr admission remain separate requirements.

## Implemented source

Persistence-class foundation:

- `schemas/kv-ai-persistence-classes.schema.json`
- `specs/kv-ai-persistence-classes.v1.json`
- `scripts/validate_kv_ai_persistence_classes.py`
- `tests/test_kv_ai_persistence_classes.py`
- `schemas/kv-cross-class-intr-transition.schema.json`
- `specs/kv-cross-class-intr-transition.example.v1.json`
- `scripts/validate_kv_cross_class_intr_transition.py`

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

## Shared invariants

```text
SKAP required: true
InTr required: true
provider is authority: false
model is authority: false
context sharing transfers authority: false
direct cross-class state mutation: false
cross-class InTr receipt required: true
least authority: true
ambiguous scope: FAIL_CLOSED
```

## KV-backed Personal Assistant memory path

```text
PERSONAL_KV readable entry projections
-> bounded context request
-> deterministic same-authority selection
-> private resident staging of exact context packet
-> authentic memory-packet Interlock/InTr admission
-> existing WorkerCoordinator fresh fenced execution
-> fenced bound-state ProviderRequest materialization
-> existing external provider-request Interlock/InTr admission
-> existing TV/TVC provider operation when required
-> PERSONAL_ASSISTANT_AI / Auri response
-> exact-response egress admission
-> optional non-authorizing memory write proposal
-> Interlock/InTr target-KV admission
-> exact PERSONAL_KV persistence/readback receipt
```

`runtime/kv_ai_memory_substrate.py` owns deterministic KV context selection and write-proposal construction. `scripts/stage_kv_ai_memory_resident_inputs.py` now stages the exact context packet and provider request input into a caller-selected private resident-state root. It deliberately does **not** create `inputs/memory-packet-admission.json`; that file must come from authentic Interlock/InTr admission.

The stager rejects provider-request credential-like fields and refuses an empty memory selection. Its staging receipt fixes admission, provider execution, provider-request materialization, and KV writeback false.

The resident `.github` lane uses `ProcessWorkerAdapter` fenced bound state at `~/.stegverse/state/kv-ai-memory-resident`. The non-authorizing request consumer checks only for the presence of the three required private files and does not read their bytes. Once all three exist, the existing WorkerCoordinator may claim/fence the canonical task and use the already-local LLM-adapter materializer.

## Context and writeback safety

An entry is selectable only when its source instance is allowlisted and `ai_context_allowed=true`. AI-eligible secret-marked content, class crossing, and authority crossing fail closed. Selection is deterministic and lexical; it does not claim semantic/vector retrieval. Oversized entries are skipped rather than silently truncated.

Every packet preserves source KV instance, relative path, exact content SHA-256 identity, provenance reference, retention class, request hash, and selected-entry-set hash. The packet fixes `model_is_authority=false`, `context_transfers_authority=false`, `secret_material_included=false`, `cross_authority_content_included=false`, and `authority_effect=NONE_CONTEXT_ONLY`.

An AI result can become only a `stegverse.kv.ai-memory-write-proposal/v1`. It fixes `execution_authorized=false`, `model_is_authority=false`, `intr_admission_required=true`, and `authority_effect=NONE_PROPOSAL_ONLY`. A proposal is not a write receipt.

## Hosted validation state

KV memory source baseline:

- run `34798372339` / job `103835833007` — memory persistence validation SUCCESS;
- run `34798372325` / job `103835832752` — KV guardrails SUCCESS;
- run `34798372302` / job `103835832491` — security baseline SUCCESS.

LLM bridge/materializer head `920fedd13a182636c80a30fc10d9482ee21de57a`:

- run `34803228613` / job `103849905207` — SUCCESS;
- run `34803228620` / job `103849906564` — SUCCESS.

Resident `.github` binding:

- run `34803483965` / job `103850649371` — SUCCESS, including `tests/test_kv_ai_memory_resident_binding.py` and Python compilation of resident worker/consumer/dispatcher.

The new KV private-input stager is included in the current `validate-kv-ai-persistence-classes.yml`; hosted conclusion for its latest source head must be observed before the stager itself is marked hosted-validated.

No CI result is live Auri/KV execution evidence.

## Remaining build

For the Personal-KV/Auri lane, the implementation gap has narrowed to authentic runtime transitions and the final writeback loop:

1. Observe/repair hosted validation for the new private resident stager.
2. Produce resident-local packet and provider request input from private KV/readable-entry state using the stager.
3. Obtain authentic memory-packet InTr `ALLOW` bound to that exact packet; do not synthesize it.
4. Allow the existing `kv_ai_memory` resident consumer + WorkerCoordinator lane to materialize the exact ProviderRequest in fenced bound state.
5. Continue that same execution through existing provider ingress, TV/TVC, provider response, Master Records continuation, and egress InTr evidence.
6. Exercise one non-authorizing memory write proposal through target-KV admission and exact-byte readback.

Broader persistence-class work remains: concrete Organizational-KV, StegVerse-KV, and Machine-KV layouts; cross-class fixtures; provider reconstruction proof; and HeartBeat observation binding without state authority.

When stable and release-ready, tag/release and create a separate propagation-verification task for Site, Publisher, admissibility-wiki, and stegguardian-wiki.

## Live activation proof required

```text
KV readable object(s)
-> deterministic context packet
-> authentic packet admission ALLOW
-> current WorkerCoordinator claim/fence
-> exact ProviderRequest materialized in fenced bound state
-> provider-request ingress ALLOW
-> AI delivery/consumption observation
-> provider response + egress ALLOW where external provider is used
-> optional write proposal
-> target-KV admission
-> exact persisted-object readback receipt
```

No stage may be inferred from repository source, CI, a model response, or provider availability.

## State distinctions

```text
architecture: CANONICALIZED
canonical task registry: INSTALLED / IN_PROGRESS
COSV task.v1: 20111110110000
persistence schema/source: IMPLEMENTED
AI memory request/packet/write-proposal source: IMPLEMENTED
private resident input stager: IMPLEMENTED / HOSTED RESULT PENDING
LLM ProviderRequest memory bridge: IMPLEMENTED / HOSTED PASS
LLM exact resident materializer: IMPLEMENTED / HOSTED PASS
WorkerCoordinator resident binding: IMPLEMENTED / HOSTED PASS
private resident input bytes: NOT OBSERVED
memory packet live InTr admission: NOT OBSERVED
live ProviderRequest materialization: NOT OBSERVED
live Auri/model consumption: NOT OBSERVED
live KV writeback/readback: NOT OBSERVED
released/tagged: NOT PERFORMED
activated: NOT ACTIVATED
provider reconstruction proof: OPEN
```
