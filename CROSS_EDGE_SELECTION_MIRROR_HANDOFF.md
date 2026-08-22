# KnowledgeVault Cross-Edge Selection Mirror Handoff

Status: ACTIVE
Repository: StegVerse-Labs/continuity-vault-kit
Integration: StegVerse-Labs/StegTalk ST-031 + StegVerse-Labs/StegWhisper SW-013

## Source of truth

This handoff is the task-specific source of truth for durable KnowledgeVault hosting of StegTalk cross-edge selection evidence.

The repository-wide installation/source state remains governed by `CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`.

## Implemented source state

KnowledgeVault already provides `_System/Execution/{Attempts,Extensions,Receipts,Recovery}` through `execution/vault_store.py` and a matching structure exists in the connected KnowledgeVault instance.

The cross-edge slice adds:

```text
schemas/cross-edge-selection-receipt.schema.json
tests/test_cross_edge_selection_receipt.py
.github/workflows/execution-recovery.yml  (expanded)
```

The canonical receipt binds:

```text
attempt_id
policy_version
communication posture
recipient capability state
candidate-set hash
selected edge
selected bearer
score + component vector
ordered fallback set
excluded paths + reasons
selected edge-advertisement hash
decision time
multipath authorization
remote-edge execution authorization
selection hash
```

`KnowledgeVaultExecutionStore.append_receipt()` is the durable storage path. The new test proves selection records append to the KV receipt stream, survive read/reconstruction, preserve order, and remain covered by the store's per-record hash verification.

## Authority boundary

```text
KnowledgeVault = durable attempt/selection/recovery truth
StegWhisper messenger surface = posture + user constraints
StegTalk ST-031 = admissibility + scoring + edge/bearer selection + lease/fallback logic
Edge device = ephemeral capability advertisement + execution
```

A capability advertisement never grants execution authority. A selection receipt never grants new user authority. A timeout/indeterminate post-dispatch result cannot become permission to execute an ordered fallback until side-effect state is externally resolved.

## Live state / activation boundary

Implemented:

- canonical selection-receipt schema;
- portable KV receipt persistence path;
- receipt-stream round-trip/reconstruction test;
- CI coverage expanded to the cross-edge receipt test.

Not yet proven:

- an actual StegTalk ST-031 selection receipt written into the connected live KnowledgeVault;
- a live edge lease persisted/reconstructed in KV;
- a real two-edge selection with one edge restarted/replaced;
- confirmed-failure fallback and ambiguous-dispatch suppression observed against real edges;
- production activation.

## Required continuation

1. Observe KnowledgeVault execution-recovery CI for this head and repair any failures.
2. Persist a real ST-031 selection receipt into the connected KnowledgeVault receipt surface.
3. Persist lease epoch/state with the associated execution attempt.
4. Execute through the selected edge and append execution/delivery evidence.
5. Restart/replace the edge and reconstruct selection + attempt state from KV.
6. Prove confirmed pre-side-effect failure can advance exactly once to the ordered fallback.
7. Prove ambiguous post-dispatch state produces verification rather than duplicate fallback execution.
8. Keep task OPEN until those runtime proofs exist.
