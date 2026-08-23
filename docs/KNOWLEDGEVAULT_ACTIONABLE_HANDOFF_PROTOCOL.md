# KnowledgeVault Actionable Handoff Protocol

Status: ACTIVE IMPLEMENTATION
Updated: 2026-08-23
Repository: `StegVerse-Labs/continuity-vault-kit`

## Purpose

Define the first-contact contract for any LLM or StegVerse module that connects through the KnowledgeVault interlock to assist with an actionable personal matter.

Actionable matters include, but are not limited to:

- VA claims, appeals, examinations, evidence requests, decisions, and deadlines;
- VA Community Care, scheduling, authorization, referral, billing, and administrative interactions;
- provider, hospital, pharmacy, insurer, benefits, and care-management interactions;
- legal, employment, financial, identity, housing, education, government, or other matters where a record may require follow-up, response, submission, escalation, deadline tracking, or evidence preservation.

## Handoff-first invariant

```text
INTERLOCK_CONNECT
  -> DISCOVER_ACTIONABLE_HANDOFF
  -> READ_HANDOFF
  -> VERIFY_CURRENT_STATE
  -> REQUEST_MINIMUM_NECESSARY_RECORDS
  -> ASSIST
```

A connected LLM must not begin by scanning raw personal records when an applicable actionable `*_HANDOFF.md` exists.

The actionable handoff is the first semantic contact surface. It tells the assisting system what the matter is, what state it is in, what remains open, what source records exist, and which additional records may be requested through the interlock.

## Canonical custody

The handoff and source records remain in the owner's KnowledgeVault or another explicitly approved private persistence boundary.

Public repositories, StegHealth, StegVerse modules, and model-session histories are not canonical custodians of PII, PHI, claims files, provider records, or other private source evidence.

## Required actionable handoff fields

Each actionable handoff should identify, at minimum:

- `matter_id` — stable opaque identifier;
- `matter_type` — e.g. VA_CLAIM, VA_INTERACTION, PROVIDER_INTERACTION;
- `status` — current governed state;
- `updated_at` — last material state update;
- `summary` — concise current-state account without unnecessary sensitive detail;
- `open_actions` — unresolved actions, deadlines, or decisions;
- `last_action` — most recent meaningful event;
- `next_expected_event` — if known;
- `authority_boundary` — who can approve, submit, publish, disclose, or execute;
- `record_refs` — opaque KnowledgeVault references for source evidence;
- `related_matter_refs` — linked matters where useful;
- `risk_flags` — deadline, cancellation, appeal window, safety, privacy, or other bounded risk signals;
- `minimum_context_request` — recommended first record subset if additional context is necessary;
- `handoff_version` and content hash.

PII/PHI should not be duplicated into the handoff unless necessary for the handoff's function and expressly permitted by owner policy.

## Handoff update rule

Every material actionable event must append or update the applicable handoff state after the underlying source record has been preserved.

Examples:

```text
new VA decision received
 -> preserve decision in KV
 -> update VA claim HANDOFF

provider states authorization is missing
 -> preserve interaction record/reference
 -> update provider/VA interaction HANDOFF

secure-message response received
 -> preserve message in KV
 -> update current state + unresolved actions in HANDOFF
```

The handoff is not a substitute for the source evidence. It is the governed continuity surface that points to the evidence.

## Model connection policy

StegVerse Ecosystem Chat is the preferred primary LLM interlock client when available because it can provide a StegVerse-native continuity and governance surface.

This preference is not an exclusivity requirement.

Any compatible LLM, local model, agent, or future conversational system may connect if it conforms to the same interlock contract and receives no broader authority merely because it can read the handoff.

```text
preferred_client = StegVerse Ecosystem Chat
required_client = none
required_contract = KnowledgeVault interlock + handoff-first rules
```

## Read semantics

The first successful interlock response for an actionable matter should contain the applicable handoff or a bounded handoff index, not the entire underlying record set.

After reading the handoff, the model may request additional source records using purpose-bound, minimum-necessary requests.

The interlock may return:

- exact source objects;
- redacted derivatives;
- extracted chronology;
- bounded evidence packets;
- hashes/receipts only;
- denial when policy or authority does not permit disclosure.

## Writeback semantics

A model may propose a handoff update as a `COMMIT_CANDIDATE`, but model output does not independently authorize mutation of the owner's personal records.

A permitted writeback must preserve:

- previous handoff version;
- proposed transition;
- supporting source references;
- authority used;
- resulting version/hash;
- write receipt.

## Failure behavior

If an actionable matter lacks a handoff, the connector should return `HANDOFF_MISSING` and recommend creation of the smallest valid handoff before broad record retrieval.

If the handoff is stale relative to newer source records, return `HANDOFF_STALE` and identify the newer record references without silently treating stale state as current.

If multiple handoffs conflict, return `HANDOFF_CONFLICT` and do not collapse the conflict into a single inferred state.

## Privacy rule

The handoff must be useful enough to resume work without becoming a duplicate private-record repository.

Preferred pattern:

```text
HANDOFF = state + chronology pointers + open actions + authority boundaries
SOURCE RECORDS = KnowledgeVault private custody
LLM CONTEXT = minimum necessary interlock return
```

## Acceptance criteria

Activation requires proof that:

1. a new LLM connection can discover the correct actionable handoff before source records;
2. the handoff is sufficient to understand current state and open actions;
3. additional PII/PHI is withheld until purpose-bound request;
4. a stale handoff is detected;
5. model writeback cannot bypass owner/governance authority;
6. the same matter can be resumed by a different compatible LLM without relying on prior session history;
7. StegVerse Ecosystem Chat can act as the preferred client without making it the only supported client.

## Relationship to other KnowledgeVault rules

This protocol extends, rather than replaces:

- KnowledgeVault personal-vault separation;
- `KNOWLEDGEVAULT_INTERLOCK_PROTOCOL.md`;
- Continuity/StegID binding;
- Governance/StegGate binding;
- AI access policy and privacy markers.

Persistence, retrieval, or familiarity with a matter never grants execution authority.