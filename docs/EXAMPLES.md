# KnowledgeVault Examples

This page indexes small, inspectable examples that show how the vault preserves continuity without requiring an account, service, database, or StegVerse integration.

## Available examples

- [`examples/Reload_Packet_Example.md`](./examples/Reload_Packet_Example.md) — a compact handoff that a future person or AI session can use to reconstruct the current state of a conversation, project, or decision.
- [`examples/Project_Continuation_Packet.md`](./examples/Project_Continuation_Packet.md) — a project handoff that separates completed work, evidence, unresolved owner decisions, mutation boundaries, and the next permitted action.
- [`examples/Device_Migration_Packet.md`](./examples/Device_Migration_Packet.md) — a device-to-device vault transfer packet with source authority, difference reconciliation, rollback, and owner-acceptance boundaries.
- [`examples/Health_Record_Chronology.md`](./examples/Health_Record_Chronology.md) — a dated health-event register that separates source-supported facts, interpretations, missing records, and qualified-review boundaries.
- [`examples/Research_Evidence_Review.md`](./examples/Research_Evidence_Review.md) — a source register that separates observations, interpretations, conflicts, and unresolved evidence gaps.
- [`examples/Multi_Session_AI_Collaboration.md`](./examples/Multi_Session_AI_Collaboration.md) — a collaboration packet that prevents AI-session proposals from silently becoming accepted authority.
- [`examples/Version_Replacement_and_Migration.md`](./examples/Version_Replacement_and_Migration.md) — a non-destructive adoption pattern for reviewing and merging a newer kit without replacing an existing vault silently.

A reload or continuation packet should make five things recoverable:

1. What was being attempted.
2. What has already been decided or completed.
3. What remains unresolved.
4. Which files or evidence are authoritative.
5. What the next permitted action is.

## How to use an example

1. Copy the closest example into your private vault.
2. Replace the sample content with your own facts and references.
3. Store supporting material in the appropriate vault folders.
4. Link the packet from `_Index/` or the relevant project index.
5. Review it before loading it into an AI system; never assume generated summaries are authoritative.

## Integrity and privacy boundaries

Examples demonstrate structure, not a requirement to expose private information. Do not place credentials, recovery codes, private keys, or unnecessary sensitive data in a reload packet. Use references or local pointers where the source material should remain separated.

Release manifests and checksums verify packaged files; they do not certify that user-authored content is true, safe, complete, or appropriate to share.

New examples should remain small, manually understandable, and usable without optional StegVerse tooling.

---

🔒 Layer: Framework | KV
