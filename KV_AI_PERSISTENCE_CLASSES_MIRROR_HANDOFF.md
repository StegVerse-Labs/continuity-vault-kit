# KV AI Persistence Classes Mirror Handoff

Status: ACTIVE / FOUR-CLASS-SOURCE-COMPLETE / PERSONAL-KV-MEMORY-SOURCE-COMPLETE / MEMORY-PACKET-INTR-SOURCE-VALIDATED / MACHINE-RECONSTRUCTION-VERIFIER-VALIDATED / HB-RECEIPT-OBSERVER-VALIDATED / LIVE-EVIDENCE-OPEN
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
- resident binding and packet-admission lane: `StegVerse-Labs/.github/docs/KV_AI_MEMORY_RESIDENT_EXECUTION_MIRROR_HANDOFF.md`.

Task Registry, source state, COSV, request files, layouts, fixtures, reconstruction verifiers, HeartBeat observers, route installers, submitters, and CI do not mint runtime authority. WorkerCoordinator claim/fence authority and authentic Interlock/InTr admission remain separate requirements.

## Four canonical classes and concrete layouts

Machine-readable source:

- `schemas/kv-ai-persistence-layouts.schema.json`;
- `specs/kv-ai-persistence-layouts.v1.json`;
- `scripts/validate_kv_ai_persistence_layouts.py`;
- `tests/test_kv_ai_persistence_layouts.py`;
- `docs/KV_AI_PERSISTENCE_LAYOUTS.md`.

```text
PERSONAL_KV / PERSON / PERSONAL_ASSISTANT_AI
ORGANIZATIONAL_KV / ORGANIZATION / ORGANIZATIONAL_AI
STEGVERSE_KV / STEGVERSE_ECOSYSTEM / STEGVERSE_AI
MACHINE_KV / MACHINE_EXECUTION_ENTITY / EXECUTION_AGENT
```

Each state domain is mutable only after applicable InTr admission. Provider authority, model authority, and direct cross-class mutation are false. These are logical provider-neutral layouts; validation does not instantiate provider storage or activate an AI/runtime.

## Complete directed cross-class matrix

All 12 directed source→target class pairs are implemented and hosted-validated through `specs/kv-cross-class-intr-transition-fixtures.v1.json`, `scripts/validate_kv_cross_class_intr_fixtures.py`, and `tests/test_kv_cross_class_intr_fixtures.py`.

Every pair requires InTr + Interlock, exact source-state and target-admission hash binding, and a receipt. Direct mutation, authority transfer, context-as-authority, model/provider authority, and secret plaintext in receipts are forbidden.

## Personal-KV/Auri source path

```text
PERSONAL_KV readable entry projections
-> deterministic bounded context packet
-> resident-local exact packet submission to shared Universal InTr
-> authentic memory-packet InTr ALLOW receipt
-> existing WorkerCoordinator fresh fenced execution
-> exact ProviderRequest materialization in bound state
-> existing provider-request InTr / TVC / response / egress path
-> optional NONE_PROPOSAL_ONLY memory write proposal
-> authentic target-KV ADMITTED/ALLOW evidence
-> write-once/idempotent target-KV materialization
-> exact-byte readback receipt
```

The source path now includes bounded context selection, private staging, exact memory-packet admission submission, fenced ProviderRequest construction, and evidence-gated writeback/readback.

### Shared Universal InTr packet-admission lane

The previously missing source transition between private packet staging and `inputs/memory-packet-admission.json` is now implemented in `StegVerse-Labs/.github` without creating a second listener or scheduler:

- `workers/kv_ai_memory_intr_profile.py` validates the exact Personal-KV packet and may emit only a non-authorizing `ALLOW` admission receipt when invoked by the authentic shared listener;
- `workers/kv_ai_memory_intr_transport.py` requires resident-local InTr JSON transport, exact raw-body SHA-256, and explicitly forbids relay/TVC authorization on this local hop;
- `scripts/install_kv_ai_memory_universal_intr_route.py` idempotently composes the profile into the existing `workers/universal_intr_profiled_ingress.py` source surface;
- `scripts/submit_kv_ai_memory_packet_local.py` reads the packet only from private bound state, requires an explicit loopback `/intr/materialization` URL, submits the exact packet, validates the returned receipt, and writes the compatible admission artifact back into private bound state;
- `scripts/consume_kv_ai_memory_resident_request.py` can now invoke that source preparation/submission automatically when packet + provider-input exist but the admission file does not. The consumer itself still does not read private packet bytes.

The submitter cannot create an ALLOW receipt when ingress is absent or rejects the packet. The route/profile does not mint WorkerCoordinator claim/fence authority, provider credentials, provider execution, model execution, or KV writeback.

## Machine-KV provider-neutral reconstruction

`runtime/machine_kv_reconstruction.py` implements the deterministic reconstruction decision contract for Machine-KV. It requires distinct source and target providers, provider authority false, one exact canonical Machine-KV state-manifest hash observed on both sides, the same Machine-KV identity, separate source/target InTr ALLOW receipt references, credential material absent, and no provider-driven identity transfer.

Passing tests prove the verifier contract only. Authentic observations from two real provider executions remain required before `MACHINE_KV_CROSS_PROVIDER_RECONSTRUCTION_OBSERVED` can be satisfied.

## HeartBeat receipt observation

`runtime/kv_heartbeat_receipt_observer.py` binds HeartBeat timing/freshness/correlation only to the exact hash of an already-verified KV receipt. HeartBeat cannot admit a transition, mutate KV, mint the underlying receipt, or become execution/transition/state authority.

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
shared ingress receipt != provider request admission
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
- four-class layouts + 12-pair matrix `34804237690` — SUCCESS;
- Machine reconstruction + HB observer `34804394797` — SUCCESS; security `34804394870`, guardrails `34804394755`, release integrity `34804394746`, release readiness `34804406677`, outcome observer `34804416022` — SUCCESS.

Shared memory-packet InTr admission source head `7e95e58c0f6ebfa839dbaa6a475b8df7ca06ab01`:

- `.github` validation run `34804928451` / job `103854827156` — SUCCESS;
- tests passed for the prior resident binding plus `tests/test_kv_ai_memory_intr_admission.py`;
- Python compilation passed for the resident worker, packet-admission profile/transport, route installer, local submitter, resident consumer, and dispatcher.

No CI result is a live packet admission, Auri/model execution, provider reconstruction, HeartBeat observation, or KV writeback receipt.

## Remaining work

Source construction for the original persistence-class and first Personal-KV memory path is materially complete through the packet-admission submission layer. Remaining goal completion is authentic evidence/integration:

1. materialize real private Personal-KV packet + provider request input;
2. observe the shared Universal InTr listener return an authentic exact-packet `ALLOW` and preserve it in private bound state;
3. let the existing `kv_ai_memory` consumer + WorkerCoordinator materialize the exact ProviderRequest under a current claim/fence;
4. continue through provider-request ingress, TV/TVC operation where applicable, response, Master Records continuation, and egress admission;
5. obtain target-KV admission for the resulting write proposal and preserve exact-byte readback;
6. obtain authentic two-provider Machine-KV reconstruction evidence;
7. bind one authentic HeartBeat observation to an already-verified KV receipt;
8. instantiate/use Organizational-KV and StegVerse-KV only through their own authority/admission paths;
9. release/tag only after applicable runtime evidence predicates are satisfied; then create the required separate propagation-verification task for Site, Publisher, admissibility-wiki, and stegguardian-wiki.

## State distinctions

```text
architecture: CANONICALIZED
canonical task registry: INSTALLED / IN_PROGRESS
COSV task.v1: 20111110110000
four persistence classes/layouts: IMPLEMENTED / HOSTED VALIDATED
all 12 directed cross-class fixtures: IMPLEMENTED / HOSTED VALIDATED
Personal-KV context/packet/staging source: IMPLEMENTED / HOSTED VALIDATED
shared memory-packet InTr route/profile/submitter: IMPLEMENTED / HOSTED VALIDATED
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
