# KV AI Persistence Classes Mirror Handoff

Status: ACTIVE / AI-MEMORY-SOURCE-IMPLEMENTED / HOSTED-VALIDATION-OBSERVATION-PENDING / LIVE-INTR-ACTIVATION-OPEN
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

The goal is now installed in the GitHub canonical Task Registry rather than existing only as a repository-local handoff:

- canonical task record: `StegVerse-Labs/.github/data/canonical-task-records/SV-KV-AI-PERSISTENCE-001.json`;
- source task vector: `StegVerse-Labs/.github/control/task-vectors/SV-KV-AI-PERSISTENCE-001.json`;
- task-vector index fragment: `StegVerse-Labs/.github/control/task-vector-index.d/SV-KV-AI-PERSISTENCE-001.json`;
- current COSV `task.v1`: `20111110110000`;
- registry coordination state: `IN_PROGRESS`.

Task Registry, source state, and COSV do not mint runtime authority. WorkerCoordinator claim/fence authority and authentic Interlock/InTr admission remain separate requirements.

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
  -> Interlock/InTr admission (runtime requirement)
  -> PERSONAL_ASSISTANT_AI / Auri
  -> optional memory write proposal
  -> Interlock/InTr target admission (runtime requirement)
  -> PERSONAL_KV persistence/readback receipt
```

`runtime/kv_ai_memory_substrate.py` implements the repository-owned portion through context-packet and write-proposal construction. It deliberately does not authenticate storage providers, resolve SKAP credentials, decide admission, call an AI provider, or write a private KV.

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

Earlier deterministic persistence-class validation passed against the baseline and five negative mutations:
- baseline: PASS;
- context-share authority transfer attempt: rejected;
- direct cross-class mutation attempt: rejected;
- provider-authority attempt: rejected;
- model-authority attempt: rejected;
- MACHINE_KV impersonating PERSON authority domain: rejected.

The AI-memory continuation adds deterministic tests for:
- relevant context selection with provenance;
- packet determinism independent of input ordering;
- AI-eligible secret material rejection;
- cross-class/cross-authority rejection;
- consumer role mismatch rejection;
- non-authorizing write proposals;
- byte-budget handling without content truncation.

The workflow now runs both the persistence-class and AI-memory validators/tests on push and pull request. Hosted completion must be observed from GitHub Actions before this handoff may claim hosted validation PASS.

## Remaining build

Machine-owned source work that can continue without private owner data:

1. Observe hosted workflow result for the new memory source head and repair any failure.
2. Add concrete Organizational-KV layout and policy/role/delegation semantics.
3. Add StegVerse-KV concrete layout for ecosystem AI persistence.
4. Add Machine-KV concrete layout for node identity, execution state, liveness, checkpoints, reconstruction, and SKAP capability references.
5. Add positive and negative cross-class fixtures for all meaningful class pairs.
6. Add reconstruction proof: instantiate Machine KV on one provider, reconstruct on a second provider, preserve identity/state continuity without provider authority.
7. Bind HeartBeat observations to verified KV transition receipts without granting HeartBeat state authority.
8. Compose the live Auri/KV adapter with existing Device/KV and Interlock/InTr runtime surfaces so an authentic context-delivery receipt can be observed.
9. After live context delivery, exercise one non-authorizing memory write proposal through target-KV admission and exact-byte readback.
10. When stable and release-ready, tag/release and create a separate propagation-verification task for Site, Publisher, admissibility-wiki, and stegguardian-wiki.

## Live activation proof required

Source and CI are insufficient for activation. A live Personal Assistant memory claim requires evidence for the adjacent chain:

```text
KV readable object(s)
-> admitted context request
-> admitted context packet
-> AI delivery/consumption observation
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
repository documentation: UPDATED
README: UPDATED
deterministic source tests: IMPLEMENTED
GitHub hosted workflow result for memory continuation: OBSERVATION_PENDING
merged: direct commits on main
released/tagged for this goal: NOT PERFORMED
deployed: NOT APPLICABLE TO SOURCE CONTRACT
live Auri/KV context delivery: NOT YET OBSERVED
live KV writeback/readback: NOT YET OBSERVED
activated: NOT ACTIVATED
provider reconstruction proof: OPEN
```
