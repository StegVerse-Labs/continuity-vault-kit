# Automated Conversation Recall

The executable recall layer complements human-readable reload packets. Normal recall no longer requires copying an entire packet into a new chat when canonical events are available.

## Canonical and derived data

`events.jsonl` is the append-only source. Each event binds its content hash, the previous event hash, the resulting-state hash, retention class, fidelity, actor, topic, and any artifact references. Search indexes are derived data and may be deleted and rebuilt.

The engine rejects duplicate event identifiers, broken previous-event links, out-of-order timestamps, altered retained content, and recoverable-fidelity claims that have no retained payload.

## Result fidelity

Every result is classified as one of:

- `exact`: retained source content is available;
- `semantic_reconstruction`: meaning is reconstructable, but exact wording is not claimed;
- `inference`: the result is derived rather than directly recorded;
- `integrity_only`: hashes can be checked but content cannot be reconstructed;
- `unavailable`: the requested evidence is absent.

## Example query

```bash
python continuity/recall.py \
  fixtures/conversation-recall/example-vault/events.jsonl \
  "What changed between yesterday and now about ingestion storage?" \
  --since 2026-07-16T00:00:00Z \
  --until 2026-07-17T23:59:59Z \
  --index-out /tmp/conversation-index.json
```

The example returns the current non-superseded storage decision, implementation status, exact/reconstructed fidelity, supporting event identifiers, and the chain verification root without reading a transcript.

## Archive readiness

```bash
python continuity/recall.py \
  fixtures/conversation-recall/example-vault/events.jsonl \
  readiness --archive-readiness
```

Archive readiness remains false while a current accepted goal lacks a complete implementation record or retains unresolved release, verification, or propagation work. Superseded goals are not treated as current blockers.

## Example vault contents

`fixtures/conversation-recall/example-vault/` contains:

- `events.jsonl` — canonical continuity events;
- `context-packet.json` — current objective, constraints, and verification root;
- `memory-use-receipt.json` — attributable record of which events supported recall;
- `multimodal-input-manifest.json` — admitted input inventory and authority basis;
- `selected-ai-context.md` — exact user-selected context, explicitly not a transcript.

## Authority boundary

Recall may report, compare, reconstruct, and identify conflicts. It does not silently revise accepted decisions, infer authority from technical access, or convert a summary into authoritative source text.

---

🔒 Layer: Framework | KV
