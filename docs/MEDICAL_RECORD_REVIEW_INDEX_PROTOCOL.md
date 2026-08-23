# Medical Record Review Index Protocol

Status: active implementation
Repository: `StegVerse-Labs/continuity-vault-kit`
Related schema: `schemas/actionable-incident.schema.json`

## Purpose

Reduce repeated full-record review by maintaining a governed, machine-readable incident index over owner-controlled personal records in KnowledgeVault.

The index is not a substitute for the source records. It is a retrieval layer that identifies, characterizes, and links incidents so later queries can retrieve the smallest relevant evidence set for care-history review, VA claims, provider disputes, continuity analysis, or governed public experience publication.

## Canonical model

```text
source personal records in KnowledgeVault
  -> incident characterization
  -> machine-readable incident object
  -> domain review index
  -> actionable HANDOFF update
  -> minimum-necessary interlock retrieval
```

Raw medical records, VA correspondence, screenshots, PDFs, provider messages, claims documents, and other PII/PHI remain in owner-controlled KnowledgeVault custody.

## Incident object

Each incident should be represented by one `kv.actionable-incident.v1` object containing at minimum:

- incident ID;
- incident class;
- title and date/range;
- current status;
- concise summary;
- fact statements separated by evidence basis (`DOCUMENTED`, `FIRSTHAND`, `REPORTED_STATEMENT`, `INFERENCE`, `OPINION`);
- opaque evidence references;
- discontinuity characterization when applicable;
- related incident IDs;
- claim-relevance tags;
- open actions/deadlines/waiting-on state;
- applicable HANDOFF reference;
- optional governed public-derivative reference.

## Review directory / index

A personal KnowledgeVault may maintain a logical health review surface such as:

```text
03_Records/
  Health/
    Review/
      HANDOFF.md
      INCIDENT_INDEX.jsonl
      INCIDENTS/
        <incident-id>.json
      CARE_HISTORY_INDEX.md
      CLAIM_RELEVANCE_INDEX.json
```

This is a recommended runtime layout, not a requirement for public framework parity. Exact personal paths remain owner-controlled.

### `INCIDENT_INDEX.jsonl`

One compact machine-readable record per incident, optimized for search/filtering without opening every source file.

### `INCIDENTS/<incident-id>.json`

Full machine-readable incident characterization conforming to `kv.actionable-incident.v1`.

### `CARE_HISTORY_INDEX.md`

Human-readable chronology of notable care transitions, unresolved issues, discontinuities, corrections, outcomes, and links to incident IDs. This should be concise enough to read before deeper record retrieval.

### `CLAIM_RELEVANCE_INDEX.json`

Optional mapping from claim issue/topic to incident IDs and evidence references. This is an indexing aid, not a legal determination of entitlement or probative weight.

## HANDOFF integration

The applicable KnowledgeVault `HANDOFF.md` is the first semantic contact for a newly connected LLM. It should summarize:

- current active matters;
- newest or materially changed incidents;
- unresolved actions and deadlines;
- relevant incident IDs;
- known conflicts or missing records;
- minimum records likely needed next;
- authority/writeback boundaries.

The HANDOFF should reference incident IDs rather than restating all sensitive details.

## Retrieval behavior

Example query: `show examples of VA care discontinuity involving referral or communication failures`.

Preferred retrieval path:

```text
HANDOFF
 -> INCIDENT_INDEX filter
 -> incident objects
 -> minimum necessary evidence refs
 -> source records only where needed
```

A full-record scan should be a fallback when the index is missing, stale, conflicting, or insufficient.

## VA claim preparation

For a future VA claim, the model should first query claim-relevance tags and incident relationships rather than rereading the entire health archive. Relevant source records may then be retrieved through the interlock for verification and packet construction.

The index must never imply that a tagged incident proves service connection, negligence, causation, entitlement, or any other legal/medical conclusion. It identifies potentially relevant evidence for review.

## Veteran Experiences publication path

An incident may later become input to the governed Veteran Experiences publication system.

```text
private incident + evidence refs
 -> governed publication request
 -> privacy/evidence review
 -> public derivative
```

The public derivative is never the private incident object and must not expose source PII/PHI merely because the incident is indexed.

## Update rule

When a newly documented interaction materially changes an actionable matter:

1. preserve or reference the source record in KnowledgeVault;
2. create or append the incident object;
3. update index entries;
4. update the applicable HANDOFF current state;
5. preserve prior states rather than silently rewriting history;
6. create a receipt for any governed writeback when runtime support exists.

## Staleness and conflict

An interlock client must not trust an index blindly. If source timestamps, incident state, or HANDOFF state conflict, return a bounded conflict state such as `HANDOFF_STALE`, `INDEX_STALE`, or `RECORD_CONFLICT` and retrieve only what is needed to reconcile it.

## Acceptance criteria

This protocol is runtime-proven only when a test corpus demonstrates that a second LLM can:

1. read the HANDOFF first;
2. locate a relevant incident without scanning all records;
3. retrieve only the evidence needed for the query;
4. distinguish documented facts from reported statements and inference;
5. update an incident and HANDOFF through a governed writeback path;
6. prepare a public derivative request without exposing private records;
7. reconstruct relevant VA claim evidence from indexes plus bounded source retrieval.
