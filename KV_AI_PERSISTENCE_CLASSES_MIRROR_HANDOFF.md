# KV AI Persistence Classes Mirror Handoff

Status: ACTIVE / AI-MEMORY-SOURCE-VALIDATED / LLM-BRIDGE-SOURCE-INTEGRATED / LIVE-INTR-ACTIVATION-OPEN
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-AI-PERSISTENCE-001
Canonical Task Registry: StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json
COSV task.v1: 20111110110000
Created: 2026-08-27
Last updated: 2026-09-13

## Goal

Formalize distinct persistent KV ecosystems for:
- Personal Assistant AI;
- Organizational AI;
- StegVerse ecosystem AI;
- machine execution agents.

The AI/model/runtime is replaceable. The applicable KV is the persistent state ecosystem for the authority domain it serves.

The first operationalized memory profile is `PERSONAL_KV / PERSON / PERSONAL_ASSISTANT_AI`: KnowledgeVault is the durable memory substrate while Auri or another model receives only a bounded, provenance-preserving context packet. Model/provider memory is non-canonical and grants no authority.

## Canonical coordination

The goal is installed in the GitHub canonical Task Registry:

- canonical task record: `StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json`;
- source task vector: `StegVerse-Labs/.github/control/task-vectors/SV-KV-AI-PERSISTENCE-001.json`;
- task-vector index fragment: `StegVerse-Labs/.github/control/task-vector-index.d/SV-KV-AI-PERSISTENCE-001.json`;
- current COSV `task.v1`: `20111110110000`;
- registry coordination state: `IN_PROGRESS`;
- provider-ingress bridge: `StegVerse-org/LLM-adapter/docs/KV_AI_MEMORY_CONTEXT_BRIDGE_MIRROR_HANDOFF.md`.

Task Registry, source state, COSV, and CI do not mint runtime authority. WorkerCoordinator claim/fence authority and authentic Interlock/InTr admission remain separate requirements.

## Implemented source

Persistence-class foundation:

- `schemas/kv-ai-persistence-classes.schema.json`
- `specs/kv-ai-persistence-classes.v1.json`
- `scripts/validate_kv_ai_persistence_classes.py`
- `tests/test_kv_ai_persistence_classes.py`
- `schemas/kv-cross-class-intr-transition.schema.json`
- `specs/kv-cross-class-intr-transition.example.v1.json`
- `scripts/validate_kv_cross_class_intr_transition.py`

AI-memory substrate continuation:

- `schemas/kv-ai-memory-context-request.schema.json`
- `schemas/kv-ai-memory-context-packet.schema.json`
- `schemas/kv-ai-memory-write-proposal.schema.json`
- `specs/kv-ai-memory-substrate.v1.json`
- `runtime/kv_ai_memory_substrate.py`
- `scripts/validate_kv_ai_memory_substrate.py`
- `tests/test_kv_ai_memory_substrate.py`
- `docs/KV_AI_MEMORY_SUBSTRATE.md`
- `.github/workflows/validate-kv-ai-persistence-classes.yml`
- `README.md`

Provider-ingress bridge in `StegVerse-org/LLM-adapter`:

- `llm_adapter/kv_memory_context_bridge.py`
- `tests/test_kv_memory_context_bridge.py`
- `.github/workflows/validate-kv-memory-context-bridge.yml`
- `docs/KV_AI_MEMORY_CONTEXT_BRIDGE_MIRROR_HANDOFF.md`

## Canonical classes

```text
PERSONAL_KV
  authority: PERSON
  AI role: PERSONAL_ASSISTANT_AI

ORGANIZATIONAL_KV
  authority: ORGANIZATION
  AI role: ORGANIZATIONAL_AI

STEGVERSE_KV
  authority: STEGVERSE_ECOSYSTEM
  AI role: STEGVERSE_AI

MACHINE_KV
  authority: MACHINE_EXECUTION_ENTITY
  AI role: EXECUTION_AGENT
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

## KV-backed AI memory source path

The bounded source path is now concrete:

```text
PERSONAL_KV
  -> bounded context request
  -> deterministic same-authority selection
  -> context packet with exact content hashes + provenance
  -> exact memory-packet Interlock/InTr admission
  -> provider-neutral ProviderRequest with bound KV context
  -> existing external provider-request Interlock/InTr admission
  -> PERSONAL_ASSISTANT_AI / Auri
  -> optional memory write proposal
  -> Interlock/InTr target admission
  -> PERSONAL_KV persistence/readback receipt
```

`runtime/kv_ai_memory_substrate.py` implements the KV-owned source portion through context-packet and write-proposal construction. `StegVerse-org/LLM-adapter/llm_adapter/kv_memory_context_bridge.py` consumes only an already-admitted exact memory packet and binds its packet ID, canonical packet hash, entry-set hash, provenance, and InTr receipt into the existing deterministic `ProviderRequest`. The ordinary provider request still requires its own existing external ingress ALLOW before any external execution.

Neither component authenticates storage providers, resolves SKAP/provider credentials, decides admission, or treats context as authority.

### Context safety

An entry is selectable only when its source instance is allowlisted and the entry declares `ai_context_allowed=true`. AI-eligible secret-marked content fails closed. KV-class or authority-domain crossing fails closed. Selection is deterministic and lexical; it does not claim semantic/vector retrieval. Oversized entries are skipped rather than silently truncated.

Every delivered packet preserves:
- source KV instance;
- relative path;
- exact content;
- SHA-256 content identity;
- provenance reference;
- retention class;
- canonical request hash and selected-entry-set hash.

The packet fixes `model_is_authority=false`, `context_transfers_authority=false`, `secret_material_included=false`, `cross_authority_content_included=false`, and `authority_effect=NONE_CONTEXT_ONLY`.

### Writeback safety

An AI result can become only a `stegverse.kv.ai-memory-write-proposal/v1`. It fixes `execution_authorized=false`, `model_is_authority=false`, `intr_admission_required=true`, and `authority_effect=NONE_PROPOSAL_ONLY`.

A proposal is not a write receipt. Target-side admission and materialization must still produce authentic governed evidence before persistence is claimed.

## Cross-class transition contract

A cross-class transition must traverse InTr + Interlock, bind source state and target admission by receipt hashes, contain no secret plaintext, and admit no authority transfer. The target KV performs its own admission; a source KV cannot directly mutate another KV's state.

Example implemented path:

```text
PERSONAL_KV
  -> InTr/Interlock
  -> ORGANIZATIONAL_KV admission
  -> receipt
```

The example shares context only. It grants no source authority inside the target domain.

## Validation state

Earlier deterministic persistence-class validation passed against the baseline and five negative mutations. The AI-memory continuation adds deterministic tests for relevant context selection with provenance, packet determinism, secret-material rejection, cross-class/cross-authority rejection, consumer role mismatch rejection, non-authorizing write proposals, and byte-budget handling without truncation.

Hosted GitHub Actions validation is now observed for source head `4053284c203023ed75e81e3312f9c9980b61ced9`:

- run `34798372339` / job `103835833007` — `validate` SUCCESS, including both new AI-memory validator and test suite;
- run `34798372325` / job `103835832752` — `kv-guardrails` SUCCESS;
- run `34798372302` / job `103835832491` — `validate-security-baseline` SUCCESS.

The LLM-adapter memory bridge dedicated workflow initially exposed a repository-import-path CI defect, not a bridge logic defect. The workflow was repaired by binding `PYTHONPATH` to the checked-out workspace; the rerun's dedicated bridge test step then completed SUCCESS. That repair does not constitute live Auri/KV execution evidence.

## Remaining build

The Personal-KV/Auri source path is now substantially implemented and source-validated. Remaining completion work is primarily authentic runtime evidence plus the broader non-Personal KV class implementations:

1. Observe the final post-repair LLM-adapter check-suite conclusions and record the successful run IDs in its scoped handoff.
2. Compose the authentic resident/WorkerCoordinator path so one real Personal-KV packet receives memory-packet InTr ALLOW and then enters the existing provider-neutral request path.
3. Preserve same-execution provider ingress, TV/TVC operation, provider response, Master Records continuation, and egress InTr evidence.
4. Exercise one non-authorizing memory write proposal through target-KV admission and exact-byte readback.
5. Add concrete Organizational-KV layout and policy/role/delegation semantics.
6. Add StegVerse-KV concrete layout for ecosystem AI persistence.
7. Add Machine-KV concrete layout for node identity, execution state, liveness, checkpoints, reconstruction, and SKAP capability references.
8. Add positive and negative cross-class fixtures for all meaningful class pairs and provider reconstruction proof.
9. Bind HeartBeat observations to verified KV transition receipts without granting HeartBeat state authority.
10. When stable and release-ready, tag/release and create a separate propagation-verification task for Site, Publisher, admissibility-wiki, and stegguardian-wiki.

## Live activation proof required

Source and CI are insufficient for activation. A live Personal Assistant memory claim requires evidence for the adjacent chain:

```text
KV readable object(s)
-> admitted context request
-> admitted exact memory context packet
-> bound ProviderRequest
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
canonical task registry: INSTALLED
COSV task.v1: 20111110110000
persistence schema/source: IMPLEMENTED
AI memory request/packet/write-proposal source: IMPLEMENTED
LLM ProviderRequest memory bridge source: IMPLEMENTED
repository documentation: UPDATED
continuity-vault-kit README: UPDATED
KV hosted memory validation: PASS / 34798372339
KV guardrails: PASS / 34798372325
KV security baseline: PASS / 34798372302
LLM bridge dedicated test after CI repair: STEP_SUCCESS / FINAL_SUITE_RECONCILIATION_PENDING
merged: direct commits on main
released/tagged for this goal: NOT PERFORMED
deployed: NOT APPLICABLE TO SOURCE CONTRACT
live Auri/KV context delivery: NOT YET OBSERVED
live KV writeback/readback: NOT YET OBSERVED
activated: NOT ACTIVATED
provider reconstruction proof: OPEN
```
