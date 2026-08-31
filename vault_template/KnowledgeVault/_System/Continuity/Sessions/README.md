# Persistent Session Continuity

This directory is the private KnowledgeVault destination for bounded semantic session continuity.

User-specific session heads must not be committed to the public source repository.

Canonical layout:

```text
Sessions/
  <session_id>/
    head.json
    history/
    receipts/
```

A session head preserves enough semantic state to reconstruct work after a client, conversation, network, or device interruption. It is deliberately not a transcript archive.

Allowed content includes active goals, repository and handoff references, blockers, machine-task references, evidence references, last verified observations, authorization boundaries, the next executable action, and predecessor/provenance metadata.

Do not store passwords, tokens, cookies, private keys, recovery material, provider secrets, raw biometric material, credential values, or other reusable secrets here.

Every reconstructed head requires independent live repository/runtime verification before work continues. Stored completion or runtime claims are evidence references, not authority.

Successor heads must be monotonic and hash-linked to the exact predecessor. Stale, replayed, ambiguous, or authority-expanding updates fail closed.

Governed DEVICE↔KV access remains subject to KV-INTERLOCK-v1 and InTr. COMMIT_CANDIDATE does not itself mutate canonical state.
