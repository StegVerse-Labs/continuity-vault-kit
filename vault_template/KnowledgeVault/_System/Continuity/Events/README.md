# Canonical Conversation Continuity Events

This private KnowledgeVault directory holds the canonical append-only conversation continuity event chain used by automated recall and persistent-session reconstruction.

Canonical file:

```text
events.jsonl
```

Each non-empty line is one `schemas/conversation-event.schema.json` event. The chain semantics are owned by `continuity/recall.py`.

The event chain is canonical history. Persistent-session `head.json` files are bounded derived checkpoints and may be rebuilt from this chain plus durable repository/runtime evidence.

Do not store transcript dumps, raw chat messages, passwords, tokens, cookies, private keys, credential values, recovery material, raw biometric material, or other reusable secrets here.

Every append must validate the current chain, bind `previous_event_hash` to the exact terminal event hash, validate the successor chain, persist with compare-and-swap semantics, read the exact bytes back, and verify the same terminal root.

Storage access creates no credential, execution, provider, governance, or completion authority.
