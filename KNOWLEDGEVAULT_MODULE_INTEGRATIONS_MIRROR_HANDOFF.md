# KnowledgeVault Module Integrations Mirror Handoff

Status: ACTIVE
Updated: 2026-08-23
Repository: StegVerse-Labs/continuity-vault-kit

## Purpose

Record KnowledgeVault module integration surfaces while distinguishing static template content from dynamic runtime state.

The StegID/Continuity integration deliberately spans both categories:

- `_Entities/Self/StegID/Continuity/` is an authoritative template personal-information surface;
- `_System/Identity/Continuity/` remains a dynamic machine backing-record surface.

Governance and execution runtime surfaces remain dynamic unless separately added to the authoritative template.

## Live KnowledgeVault integration topology

```text
_Entities/
  Organizations/
  People/
  Places/
  Projects/
  Self/
    ZRE_Profile.json
    StegID/
      Continuity/        # personal-information projection surface; template-backed
        README.md

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

The `_Entities` root is now materially advanced toward template parity. Live Drive contains:

- `README.md` — exact source size 1730 bytes, unconverted `text/plain`;
- `Entity_File_Templates-Standard.md` — exact source size 2535 bytes, unconverted `text/plain`;
- `Organizations/`;
- `People/`;
- `Places/`;
- `Projects/`;
- `Self/`.

The live `_Entities` root therefore matches the authoritative source's top-level entity categories. Nested category payloads remain to be installed.

## Continuity / StegID binding

Canonical implementation owners:

- `StegVerse-Labs/StegID`: cryptographic identity-receipt verification and bounded handoff;
- `StegVerse-Labs/Continuity`: continuity semantics plus paired KV persistence.

StegID source:

- `src/stegid/knowledge_vault_continuity.py`;
- tests `tests/test_knowledge_vault_continuity.py`;
- binding handoff `docs/KNOWLEDGEVAULT_CONTINUITY_BINDING_MIRROR_HANDOFF.md`.

Current StegID binding explicitly preserves:

- `continuity_receipt_ref`;
- `verified_receipt_payload_hash`;
- system consumer contract `stegverse.knowledgevault.continuity/v1`;
- personal projection contract `stegverse.knowledgevault.personal-continuity/v1`;
- exact system target `_System/Identity/Continuity/<continuity_id>.json`;
- exact personal target `_Entities/Self/StegID/Continuity/<continuity_id>.json`.

StegID commits:

- initial binding `68efb2ee44ca8c8c52a41b8bdb6b7979f1370655`;
- initial tests `34e58fd9b154b31c1aba3151a66d2f140eaf4318`;
- explicit dual-target contract `c408e8f0917501b39187c7acb29a7b9a6847b7b2`;
- target/hash-drift tests `b6202863a7bd0e0c1b477712154c0c7fc82009b4`;
- reconciled binding handoff `03f60b9286db24b660c83c8ab88590e73a5bf7ec`.

Continuity source:

- `scripts/knowledge_vault_continuity.py`;
- initial adapter commit `67d7d3fd5c667077dea57234642177128d8bd0f0`;
- validator integration commit `f79467a4edd257ddb63a001b4694c61b83e6233e`;
- paired personal-projection implementation commit `9e42c877348528d678f20c9a19b82106d40e9754`;
- paired integrity verification hardening commit `59b1e894abd1ee601d3ff2298569a8666fc5e3d2`;
- specialized handoff `docs/KNOWLEDGEVAULT_CONTINUITY_MIRROR_HANDOFF.md`, reconciled at `2914e915f8c48f2df9a5c706e96385661b7a00fe`.

KnowledgeVault template source:

- `vault_template/KnowledgeVault/_Entities/Self/StegID/Continuity/README.md`;
- template-addition commit `2630ce5e274d3e7f83fd99a0428a731d0d28ad5e`.

Live Drive paths:

- `_Entities/Self/StegID/Continuity/` — folder id `1tfkUcPLevPd8UiTzgm-NqX4lbxAwSGK4`;
- `_System/Identity/Continuity/` — folder id `1amLwj70SVqUbbU_1PIF-06NzOQ3Ck6aM`.

The live personal directory contains one source-aligned `README.md` as unconverted `text/plain`; duplicate README state discovered during verification was removed.

### Two-layer invariant

For one identity-continuity event, Continuity may persist:

```text
_System/Identity/Continuity/<continuity_id>.json
_Entities/Self/StegID/Continuity/<continuity_id>.json
```

The owner-facing personal projection contains bounded status/reference information and must be hash-linked to the machine record through `system_record_ref` + `system_record_hash`, with its own `projection_hash`.

Verification now treats the pair as one integrity unit when the system record is read from the canonical vault path. Missing personal projection, path drift, subject/state mismatch, hash drift, or authority escalation blocks verification.

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
- `scripts/knowledge_vault_gdr.py`;
- adapter commit `1208bdc5ed0785fc3f13f33c9bf5997187af62c8`;
- validator integration commit `702c0084278f1aad18091afb3d0b9a8224936418`;
- specialized handoff commit `83dbd2d3c739af9fd3bb323b3613b7280313d785`;
- handoff path `docs/governance/KNOWLEDGEVAULT_GOVERNANCE_MIRROR_HANDOFF.md`.

Durable KV path:
- `_System/Governance/Decisions/`;
- Drive folder id `1ocQIxFbOfoIKXrAZelEbZ4qqVgRtCAaN`.

Boundary:
- KnowledgeVault preserves the GDR package; it does not issue the GDR.
- Governance does not mint or cryptographically verify Continuity receipts.
- KnowledgeVault/Governance persistence grants no execution authority.
- Historical GDR packages are immutable-by-decision-id in the adapter: a byte-different overwrite is refused.

## Actionable handoff-first interlock

Canonical protocol: `docs/KNOWLEDGEVAULT_ACTIONABLE_HANDOFF_PROTOCOL.md`.

For actionable personal matters such as provider interactions, insurer/pharmacy matters, legal/financial/benefits matters, or any record with an unresolved action/deadline, the first semantic contact for a newly connected LLM is the applicable `*_HANDOFF.md`, not underlying private source records.

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

StegID includes direct receipt-binding and target/hash-drift tests. Continuity includes executable paired persistence and authority/integrity-boundary validation. Governance includes positive persistence verification plus negative authority-escalation testing.

The paired personal/system Continuity source is implemented, but **runtime activation is not yet proven**. Required proof still includes a real StegID-verified receipt, live paired Drive write/read, hash-link verification, and interruption/reconstruction evidence.

No fabricated identity-continuity event has been written into the live personal KnowledgeVault. First live event records must originate from actual owner-authorized activity.

## Open activation predicates

Continuity / StegID:
1. observe current-main StegID and Continuity validation success;
2. verify a real current StegID identity-continuity receipt;
3. persist both paired records into live KV;
4. read back and verify system record hash, personal projection hash, subject/state/path bindings, and cross-link hash;
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

The `_Entities/Self/StegID/Continuity/README.md` is part of authoritative template source and therefore must be included in future template-parity reconciliation. The live Drive contains it.

The `_Entities` root category folders plus `README.md` and `Entity_File_Templates-Standard.md` are now live and source-aligned. Remaining `_Entities` parity work is the nested payload under Organizations, People, Places, Projects, plus any remaining Self payload beyond the already-installed ZRE profile and StegID continuity README.

`_System/Identity/**`, `_System/Governance/**`, and `_System/Execution/**` remain runtime extension surfaces unless/until their paths are explicitly added to authoritative template source.

Do not count dynamic runtime records as static template parity merely because their directories exist.


## Incoming communications / contact-ledger binding

Canonical producer: `StegVerse-Labs/Comms-Gateway`.

Template-backed personal custody surfaces:

- `_Entities/Self/Communications/PersonalInformationDirectory/`;
- `_Entities/Self/Communications/ContactLedger/`.

Comms-Gateway normalizes inbound events, resolves endpoints against every installed directory communication mode, groups evidence references by attributed subject, and emits hash-bound `COMMIT_CANDIDATE` packages. KnowledgeVault remains the durable custody owner and accepts changes only through the Interlock.

A threshold-qualified composition is a candidate, not filing authority. Sealing requires separate owner authorization. Sealed observation IDs, cutoff, and composition hash are immutable; later events are preserved in an append-only post-filing list, and notice events are separately evidence-bound.

Activation remains unproven until a real provider observation is resolved against the live personal directory, committed and read back through the KV Interlock, and receipt/hash verification succeeds. No synthetic caller evidence may be installed as a live personal record.
