# Conversation Continuity MVP

This repository now contains a local-first, standard-library-only vertical slice for preserving and searching the continuity of a conversation without requiring every session to remain a permanent transcript.

## What is built

`tools/conversation_continuity.py` provides four commands:

- `build` — canonicalizes JSONL source events, applies retention-class behavior, creates an append-only SHA-256 event chain, calculates a Merkle root, and writes a searchable index;
- `verify` — independently recalculates sequence, previous-event links, event hashes, chain tip, event count, and Merkle root;
- `search` — searches structured continuity records rather than requiring a remembered transcript title or phrase;
- `reconstruct` — returns the accepted decision for a topic with fidelity, source event, supporting events, artifact, and Merkle provenance.

No account, hosted service, database, SDK, or third-party Python package is required.

## Retention classes

### `integrity-only`

Stores event identity, sequence, metadata, and a content commitment. It can verify a later-presented payload but cannot independently recreate discarded content.

### `reconstructable`

Stores a structured semantic summary sufficient to recover the substance of a decision or state transition without preserving every original word.

### `full-fidelity`

Stores the exact event content in the chained record.

Search and reconstruction disclose the applicable fidelity rather than presenting every result as exact recall.

## Run the demonstration

```bash
python3 tools/conversation_continuity.py build \
  examples/conversation_continuity/sample_session.jsonl \
  /tmp/continuity-demo

python3 tools/conversation_continuity.py verify /tmp/continuity-demo

python3 tools/conversation_continuity.py search \
  /tmp/continuity-demo \
  "bundle retention"

python3 tools/conversation_continuity.py reconstruct \
  /tmp/continuity-demo \
  "bundle retention"
```

## Run the adversarial test

```bash
python3 tools/test_conversation_continuity.py
```

The test builds and verifies a four-event conversation, searches it, reconstructs the accepted decision, mutates the accepted summary without updating its commitment, and requires verification to fail with an event-hash mismatch.

## Output surfaces

A build writes:

```text
events.chained.jsonl
continuity.index.jsonl
manifest.json
```

The manifest records the event count, chain tip, Merkle root, source fixture, and retention-class counts.

## What this release proves

This MVP proves that the repository can:

1. convert structured conversation events into deterministic canonical records;
2. bind those records into a mutation-evident ordered chain;
3. summarize the event set with a Merkle root;
4. retain different events at different fidelity levels;
5. search decisions, claims, artifacts, actors, dates, and statuses through a derived index;
6. reconstruct an accepted historical conclusion with explicit provenance;
7. detect unauthorized mutation through an independently runnable verifier.

## What it does not yet prove

This is not yet a production conversational-memory platform. It does not currently provide:

- automatic capture from ChatGPT or another conversation provider;
- signatures or external timestamp anchoring;
- Merkle inclusion-proof export for individual leaves;
- encrypted payload custody;
- access-control policy enforcement;
- semantic embeddings or natural-language ranking;
- distributed replication;
- deletion and jurisdictional compliance workflows;
- a graphical interface;
- independent third-party validation.

The correct public claim is therefore:

> A working local-first prototype is built and publicly verifiable. It creates canonical conversation events, commits them into a Merkle-verifiable chain, applies distinct retention classes, indexes durable consequences, and reconstructs historical decisions with provenance. The larger production architecture remains under development.

🔒 Layer: Framework | KV
