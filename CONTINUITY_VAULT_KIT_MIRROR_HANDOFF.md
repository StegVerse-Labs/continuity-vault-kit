# continuity-vault-kit Mirror Handoff

Status: ACTIVE
Repository: StegVerse-Labs/continuity-vault-kit
Default branch: main
Created: 2026-08-22
Last updated: 2026-08-26

## Live source of truth

- Repository is public, active, and writable through the connected GitHub authority.
- `VERSION` on `main` is `0.1.9`.
- `STATUS.md` is reconciled to v0.1.9 and current release-cycle state.
- Latest release evidence records v0.1.9 as PUBLISHED with `release_required_after_run=false`.
- Latest integrity evidence records a 131-file release manifest and PASS initializer / automation-contract self-tests.
- Template root tree SHA used for this installation: `13ac73d64bb96bf80cb790d205b29962b6913310`.
- Issue #39 has advanced from issue-only definition into implemented recoverable-execution / communication-extension source, but runtime proof remains open.
- Issue #16 remains a separate external activation gate and is not a baseline KnowledgeVault installation requirement.
- Root user-operation documentation is now consolidated into `README.md` plus `USER_GUIDE.md`; `SECURITY.md` remains the separate repository/deployment security policy.

## Root user-document consolidation completed

Completed 2026-08-26:

- rewrote `README.md` as the concise KnowledgeVault front door;
- added `USER_GUIDE.md` as the complete user-operation guide;
- folded first-use material from `WELCOME.md` and `GETTING_STARTED.md` into the two-document user path;
- folded user safety / plaintext-secret guidance from `SAFETY.md` and `DO_NOT_STORE_HERE.md` into `USER_GUIDE.md` while preserving `SECURITY.md` as the repository/deployment security authority;
- removed obsolete duplicate `PATCH_README.md` / `Patch_README.md` root artifacts;
- documented the evolving StegVerse topology as `SKAP Vault ←InTr→ KnowledgeVault ←InTr→ Device/StegOS Node ←InTr→ External Network ←InTr→ Endpoint`, with separate independently governed ingress HANDOFF / HANDOFF_RECEIPT boundaries and explicit language that runtime Interlock/InTr activation remains separate from baseline file-only KV use.

Follow-up validation remains required for any stale internal links in historical/developer documentation that referenced the removed root onboarding files. Do not treat documentation consolidation as runtime activation.

## Claimed installation task

Install a real KnowledgeVault instance from `vault_template/KnowledgeVault/` into the connected Google Drive. Preserve exact source text/path names. Do not substitute placeholders, converted Google Docs, or documentation-only approximations.

Destination: connected Google Drive `/KnowledgeVault`
Drive folder id: `1c8OdhJeLD6E4ALmi-aR7dXvG8PjDLSfi`

All expected top-level template folders are present, including numbered folders, `_AI`, `_Entities`, `_Index`, `_LightMode`, `_Meta`, `_Policy`, `_System`, `_Templates`, `_migration`, and `docs`.

## Verified Drive import method

1. Fetch exact UTF-8 source content from the live repository.
2. Materialize it as a runtime-managed `.txt` artifact so the connector presents MIME `text/plain`.
3. Import with `upload_mode=keep_source_file_type` while setting the destination title to the original `.md` / `.json` filename.
4. Result remains unconverted `text/plain`.
5. Move into the exact destination folder using Drive parent IDs.
6. Verify filename, MIME type, destination, and available byte size.

The runtime sometimes requires one-file-at-a-time artifact registration. That is an execution quirk, not a source or Drive fidelity blocker.

## Verified installation parity completed

Manifest-required core files:

- `_Index/Master_Index.md`
- `_Index/Timeline_Index.md`
- `_Index/Topics_Index.md`
- `_Meta/vault.manifest.json`

Numbered/template payload verified installed:

- `00_Inbox/README.md`
- `00_Inbox/Quick_Notes.md`
- `01_Notes/README.md`
- `01_Notes/_Templates/Note Template.md`
- `02_Research/README.md`
- `02_Research/_Templates/Research Template.md`
- `03_Records/README.md`
- `03_Records/_Templates/Records Template.md`
- `04_Media/README.md`
- `05_Projects/README.md`
- `05_Projects/_Templates/Projects Template.md`
- `05_Projects/_Events/README.md`
- `05_Projects/_Events/_Templates/Capture_Playbook.md`
- `05_Projects/_Events/_Templates/Consent_and_Permissions.md`
- `05_Projects/_Events/_Templates/Event_Manifest.md`
- `05_Projects/_Events/_Templates/Media_Index.md`
- `05_Projects/_Events/_Templates/Participants.md`
- `06_Archive/README.md`

`_Meta` is fully populated relative to the live template directory, with the installed manifest intentionally installation-mutated:

- `_Meta/FORMAT_VERSION.md` — 96 bytes
- `_Meta/link_integrity.md` — 385 bytes
- `_Meta/places.txt` — 45 bytes
- `_Meta/vault.manifest.json`

`_Policy` is now fully populated relative to the live template directory. Drive enumeration after the latest installation pass confirms all 12 policy files are present as unconverted `text/plain`, with the newly installed source sizes matching GitHub:

- `AI_Access_Policy.md` — 546 bytes
- `AI_Ingestion_Behavior.md` — 4034 bytes
- `AI_Review_Prompt_Behavior.md` — 3288 bytes
- `AI_Suggestion_Approval_Mechanism.md` — 3384 bytes
- `Data_Sharing_Policy.md` — 2666 bytes
- `Intake_Workflow.md` — 619 bytes
- `Legacy_and_Export.md` — 1590 bytes
- `Naming_Standard.md` — 298 bytes
- `Retention_and_Preservation.md` — 296 bytes
- `Tag_Dictionary.md` — 2430 bytes
- `Vault_Evolution_Vault_Migration.md` — 2906 bytes
- `Vault_Health_Check.md` — 460 bytes

The six policy files completed in the latest pass are `AI_Review_Prompt_Behavior.md`, `AI_Suggestion_Approval_Mechanism.md`, `Data_Sharing_Policy.md`, `Legacy_and_Export.md`, `Tag_Dictionary.md`, and `Vault_Evolution_Vault_Migration.md`.

## Remaining installation parity work

Continue exact-source installation for:

- additional `_Index/**` content including Now, Onboarding, Relationships, Reviews, Timeline, and auxiliary indexes;
- `_AI/**` consent, logs, reflections, share-card, queue/applied/rule content;
- `_Entities/**` People, Places, Projects, Organizations, Self, and templates;
- `_LightMode/**`;
- `_System/Guides/**`;
- `_Templates/**`;
- `_migration/**`;
- `docs/**` and nested policy/templates.

After all source files are installed:

1. enumerate authoritative source paths;
2. enumerate destination paths;
3. reconcile missing and unexpected files;
4. verify source sizes/hashes wherever Drive exposes sufficient raw-byte evidence;
5. refresh `_System/installation.receipt.json` with the final verified result;
6. only then mark full-template parity complete.

## Recoverable execution and communication-extension host

Issue #39 now has implemented source slices:

- `schemas/execution-attempt-journal.schema.json`
- `schemas/execution-recovery-decision.schema.json`
- `schemas/communication-extension.schema.json`
- `execution/recovery.py`
- `execution/extensions.py`
- `execution/vault_store.py`
- `tests/test_execution_recovery.py`
- `tests/test_vault_store.py`
- `.github/workflows/execution-recovery.yml`

Implemented recovery invariants include monotonic STARTED / DISPATCHED / OBSERVING / TERMINAL / ABANDONED state handling; hash binding to the exact execution envelope and idempotency key; stale/concurrent worker lease protection; EXECUTED duplicate suppression; VERIFY_EXTERNALLY for INDETERMINATE; RETRY_EXACT only after confirmed side-effect absence; no recovery-created authority; and no credentials stored in journals.

KnowledgeVault now has a portable durable backing layout under:

```text
_System/Execution/
    Attempts/
    Extensions/
    Receipts/
    Recovery/
```

The connected Drive KnowledgeVault contains that live directory structure. This proves the durable backing location exists in the actual personal vault. It does not yet prove that a real communication attempt has been persisted and recovered through it.

KnowledgeVault is an explicit communication-extension host for StegTalk and StegWhisper. The device remains an ephemeral transport edge: `device_authority=false` and `device_continuity_authority=false`; KnowledgeVault remains the continuity host. Cross-repository source bindings exist in `StegVerse-Labs/StegTalk` and `StegVerse-Labs/StegWhisper`, but source implementation is not runtime/cloud activation proof.

## Open completion boundaries

- Full-template Drive parity remains ACTIVE until the complete recursive template payload is present and reconciled against the authoritative release/template source.
- Root documentation consolidation is implemented, but stale-link validation across historical/developer docs remains OPEN until checked against current `main`.
- Issue #39 runtime validation remains OPEN until observed CI plus a real durable KnowledgeVault-backed StegTalk/StegWhisper attempt survives and reconstructs across an actual edge-device interruption/restart or replacement.
- Issue #16 external provider activation remains OPEN / externally gated.

Durable handoff, task assignment, folder presence, source implementation, documentation cleanup, or workflow existence does not by itself satisfy activation or completion.
