# Medical Record Review / Incident Index Mirror Handoff

Updated: 2026-08-23
Repository: `StegVerse-Labs/continuity-vault-kit`
Workstream: `KV-MEDICAL-REVIEW-001`
State: `ACTIVE_IMPLEMENTATION`

## Goal

Make actionable health/benefits history retrievable without repeatedly scanning an owner's entire record archive.

Every material VA claim event, VA interaction, Community Care event, provider interaction, insurer/pharmacy event, care-coordination failure, or other actionable health-record event may be characterized as a machine-readable incident linked to the underlying owner-controlled KnowledgeVault records.

## First-contact rule

For a compatible LLM connected through the StegVerse interlock, this HANDOFF is the first contact for the medical-record-review/indexing workstream. For an owner's live vault, the applicable personal `HANDOFF.md` remains the first semantic contact for the actual active matters.

```text
INTERLOCK_CONNECT
 -> READ applicable HANDOFF
 -> READ incident index
 -> SELECT relevant incident objects
 -> REQUEST minimum necessary source evidence
 -> ASSIST
```

A full medical-record scan is a fallback, not the default.

## Canonical surfaces

- `schemas/actionable-incident.schema.json` — machine-readable incident object (`kv.actionable-incident.v1`).
- `docs/MEDICAL_RECORD_REVIEW_INDEX_PROTOCOL.md` — index/retrieval/update protocol.
- `docs/KNOWLEDGEVAULT_ACTIONABLE_HANDOFF_PROTOCOL.md` — handoff-first cross-LLM continuity contract.
- `docs/KNOWLEDGEVAULT_INTERLOCK_PROTOCOL.md` — governed KnowledgeVault access boundary.
- `tools/incident_index.py` — executable JSONL validator and bounded index-level query tool.
- `tools/test_incident_index.py` — synthetic-only fail-closed and bounded-retrieval tests.
- `tests/fixtures/actionable_incidents.synthetic.jsonl` — two linked synthetic VA-style incidents with no real PII/PHI.
- `.github/workflows/validate-incident-index.yml` — hosted validation lane for compile, tests, index validation, and zero-source-record bounded retrieval proof.

## Recommended live-vault structure

```text
03_Records/Health/Review/
  HANDOFF.md
  INCIDENT_INDEX.jsonl
  INCIDENTS/<incident-id>.json
  CARE_HISTORY_INDEX.md
  CLAIM_RELEVANCE_INDEX.json
```

This runtime layout is owner-controlled and may vary. The public framework repository must not contain the owner's PII/PHI or source personal records.

## Incident semantics

Each incident separates:

- documented facts;
- firsthand observations;
- reported statements;
- inference;
- opinion;
- evidence references;
- discontinuity type(s);
- action state/deadlines;
- claim-relevance retrieval tags;
- optional governed public-derivative state.

The incident object is an index/retrieval artifact, not a legal or medical conclusion.

## Executable retrieval boundary

`tools/incident_index.py` validates incident-index JSONL and provides index-only filtering without opening source records. Query output deliberately returns bounded incident metadata plus opaque evidence references and reports:

```text
query_path = HANDOFF->INCIDENT_INDEX->INCIDENT->EVIDENCE_REFS
source_records_opened = 0
```

This proves only the repository-level selection boundary against synthetic fixtures. It does not prove live KnowledgeVault access, interlock enforcement, or minimum disclosure against real records.

The validator fails closed on malformed JSON, missing required incident fields, invalid evidence-basis vocabulary, duplicate incident IDs, missing evidence references, and unsupported state values.

## Synthetic validation corpus

The synthetic fixture contains two related incidents:

1. referral/authorization mismatch plus scheduling failure;
2. duplicate-prior-instruction / communication-loop failure.

The corpus intentionally resembles the *class* of actionable continuity problems the system must retrieve, but contains no real veteran, provider, facility, referral, claim, or medical identifiers.

The test suite currently checks:

- schema-level structural validation of both indexed incidents;
- bounded communication-failure retrieval without source-record access;
- claim-relevance retrieval;
- duplicate-ID fail-closed behavior;
- invalid evidence-basis fail-closed behavior.

## Query examples

`Find examples of VA care discontinuity involving communication failures.`

`Show incidents relevant to a future GI-related VA claim.`

`Retrieve Community Care incidents where referral state and executable authorization diverged.`

`Find provider interactions that were followed by unresolved action items.`

The expected path is HANDOFF -> incident index -> incident object -> minimum necessary evidence. The model should not open every medical record merely because records are available.

## Relationship to Veteran Experiences

A private incident may be submitted as input to the governed Veteran Experiences workflow, but publication must create a separate public derivative.

```text
private KV incident
 -> governed Veteran Experiences submission
 -> privacy/evidence review
 -> author/publication authority
 -> public derivative
```

The public system must not expose the private incident object or its source PII/PHI by default.

## Relationship to VA claim preparation

Claim preparation should use `CLAIM_RELEVANCE_INDEX` and incident relationships to select candidate evidence. Source records are then retrieved through the interlock only as needed for verification and packet construction.

This indexing mechanism does not determine service connection, entitlement, causation, negligence, disability rating, or evidentiary weight.

## Update rule

When a new interaction materially changes an active matter:

1. preserve/reference the source record in KnowledgeVault;
2. create or update the incident characterization without overwriting prior history;
3. update `INCIDENT_INDEX.jsonl` and human-readable care history;
4. update the applicable live-vault HANDOFF;
5. record open actions/deadlines/waiting-on state;
6. preserve a receipt for governed writeback when runtime support exists.

## Current implementation state

Completed framework / executable surfaces:

- actionable incident schema installed;
- medical record review/index protocol installed;
- handoff-first interlock protocol installed;
- KnowledgeVault interlock protocol installed;
- executable incident-index validator installed;
- executable bounded index query installed;
- synthetic linked-incident fixture installed;
- fail-closed and bounded-retrieval test suite installed;
- hosted validation workflow installed.

Runtime evidence still required:

- observe hosted validation result for the new lane;
- automatic incident extraction/classification from new records;
- governed writeback into an owner's live KnowledgeVault;
- index staleness/conflict reconciliation;
- live cross-LLM incident retrieval;
- VA-claim evidence selection proof against owner-authorized records;
- Veteran Experiences public-derivative round trip.

## Activation criteria

`KV-MEDICAL-REVIEW-001` is activated only when a real owner-authorized incident can be written to the live KnowledgeVault, the live HANDOFF/index updated, and a second compatible LLM can retrieve the incident and only its necessary evidence without prior conversation history or a full-record scan.

Repository synthetic validation is necessary but not sufficient for activation.
