# KnowledgeVault Module Integrations Mirror Handoff

Status: ACTIVE
Updated: 2026-08-23
Repository: StegVerse-Labs/continuity-vault-kit

## Purpose

Record KnowledgeVault module integration surfaces while distinguishing static template content from dynamic runtime state.

The StegID/Continuity integration now deliberately spans both categories:

- `_Entities/Self/StegID/Continuity/` is now an authoritative template personal-information surface;
- `_System/Identity/Continuity/` remains a dynamic machine backing-record surface.

Governance and execution runtime surfaces remain dynamic unless separately added to the authoritative template.

## Live KnowledgeVault integration topology

```text
_Entities/
  Self/
    StegID/
      Continuity/        # personal-information projection surface; now template-backed

_System/
  Execution/
    Attempts/
    Extensions/
    Receipts/
    Recovery/
  Identity/
    Continuity/          # machine backing records
  Governance/
    Decisions/
```

The connected Drive has been directly inspected/created for these surfaces. Folder presence proves destination topology, not runtime activation.

## Continuity / StegID binding

Canonical implementation owners:

- `StegVerse-Labs/StegID`: cryptographic identity-receipt verification and bounded handoff;
- `StegVerse-Labs/Continuity`: continuity semantics plus paired KV persistence.

StegID source:

- `src/stegid/knowledge_vault_continuity.py`
- tests `tests/test_knowledge_vault_continuity.py`
- binding handoff `docs/KNOWLEDGEVAULT_CONTINUITY_BINDING_MIRROR_HANDOFF.md`

Continuity source:

- `scripts/knowledge_vault_continuity.py`
- initial adapter commit `67d7d3fd5c667077dea57234642177128d8bd0f0`
- validator integration commit `f79467a4edd257ddb63a001b4694c61b83e6233e`
- paired personal-projection implementation commit `9e42c877348528d678f20c9a19b82106d40e9754`
- specialized handoff `docs/KNOWLEDGEVAULT_CONTINUITY_MIRROR_HANDOFF.md`

KnowledgeVault template source:

- `vault_template/KnowledgeVault/_Entities/Self/StegID/Continuity/README.md`
- template-addition commit `2630ce5e274d3e7f83fd99a0428a731d0d28ad5e`

Live Drive paths:

- `_Entities/Self/StegID/Continuity/` — folder id `1tfkUcPLevPd8UiTzgm-NqX4lbxAwSGK4`;
- `_System/Identity/Continuity/` — folder id `1amLwj70SVqUbbU_1PIF-06NzOQ3Ck6aM`.

The live personal directory README is installed as unconverted `text/plain`.

### Two-layer invariant

For one identity-continuity event, Continuity may persist:

```text
_System/Identity/Continuity/<continuity_id>.json
_Entities/Self/StegID/Continuity/<continuity_id>.json
```

The owner-facing personal projection contains bounded status/reference information and must be hash-linked to the machine record through `system_record_ref` + `system_record_hash`, with its own `projection_hash`.

Boundary:

- StegID verifies identity-continuity evidence.
- Continuity defines/reconstructs continuity and writes the paired KV representation.
- KnowledgeVault preserves both representations.
- The personal projection does not mint identity, continuity, execution, wallet, governance, or device authority.
- The machine backing record does not make KnowledgeVault identity authority.
- Private keys, raw biometric material, credentials, wallet secrets, or authentication secrets must not be stored in the personal projection directory.

## Governance / StegGate binding

Canonical implementation owner: `StegVerse-Labs/Governance`.

Source:
- `scripts/knowledge_vault_gdr.py`
- adapter commit `1208bdc5ed0785fc3f13f33c9bf5997187af62c8`
- validator integration commit `702c0084278f1aad18091afb3d0b9a8224936418`
- specialized handoff commit `83dbd2d3c739af9fd3bb323b3613b7280313d785`
- handoff path `docs/governance/KNOWLEDGEVAULT_GOVERNANCE_MIRROR_HANDOFF.md`

Durable KV path:
- `_System/Governance/Decisions/`
- Drive folder id `1ocQIxFbOfoIKXrAZelEbZ4qqVgRtCAaN`

Boundary:
- KnowledgeVault preserves the GDR package; it does not issue the GDR.
- Governance does not mint or cryptographically verify Continuity receipts.
- KnowledgeVault/Governance persistence grants no execution authority.
- Historical GDR packages are immutable-by-decision-id in the adapter: a byte-different overwrite is refused.

## Actionable handoff-first interlock

Canonical protocol: `docs/KNOWLEDGEVAULT_ACTIONABLE_HANDOFF_PROTOCOL.md`.

For actionable personal matters such as VA claims, provider interactions, insurer/pharmacy matters, legal/financial/benefits matters, or any record with an unresolved action/deadline, the first semantic contact for a newly connected LLM is the applicable `*_HANDOFF.md`, not underlying private source records.

Required first-contact sequence:

```text
INTERLOCK_CONNECT
 -> DISCOVER_ACTIONABLE_HANDOFF
 -> READ_HANDOFF
 -> VERIFY_CURRENT_STATE
 -> REQUEST_MINIMUM_NECESSARY_RECORDS
 -> ASSIST
```

StegVerse Ecosystem Chat is the preferred primary LLM interlock client when available, but compatible clients may connect if they honor the same interlock, privacy, continuity, and authority contracts.

## Validation posture

StegID includes direct receipt-binding tests. Continuity includes executable persistence and authority-boundary validation. Governance includes positive persistence verification plus negative authority-escalation testing.

The paired personal/system Continuity source is implemented, but **runtime activation is not yet proven**. Required proof still includes a real StegID-verified receipt, live paired Drive write/read, hash-link verification, and interruption/reconstruction evidence.

No fabricated identity-continuity event has been written into the live personal KnowledgeVault. First live event records must originate from actual owner-authorized activity.

## Open activation predicates

Continuity / StegID:
1. observe current-main StegID and Continuity validation success;
2. verify a real current StegID identity-continuity receipt;
3. persist both paired records into live KV;
4. read back and verify system record hash, personal projection hash, and cross-link hash;
5. reconstruct across actual interruption/replacement without KV/device authority transfer.

Governance / StegGate:
1. observe current-main validator success;
2. consume an actually validated Continuity reference;
3. produce a real GDR using the existing canonical GDR contract;
4. persist/read-back/hash-verify it in live KV;
5. prove later reevaluation creates a new/superseding GDR rather than rewriting history;
6. prove persistence alone cannot authorize downstream execution.

## Installation-parity separation

Static template installation continues under `CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`.

The newly added `_Entities/Self/StegID/Continuity/README.md` **is now part of authoritative template source** and therefore must be included in future template-parity reconciliation. The live Drive already contains it.

`_System/Identity/**`, `_System/Governance/**`, and `_System/Execution/**` remain runtime extension surfaces unless/until their paths are explicitly added to authoritative template source.

Do not count dynamic runtime records as static template parity merely because their directories exist.
