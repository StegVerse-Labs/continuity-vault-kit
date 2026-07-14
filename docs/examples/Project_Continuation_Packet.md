# Project Continuation Packet — Example

Use this packet when a project may be resumed by your future self, another trusted collaborator, or a later AI session.

This is an example structure, not an authority record. Replace every sample value and verify all claims against the referenced files.

---

## Project

**Name:** Local Archive Cleanup

**Purpose:** Organize an existing personal document archive without deleting original material until the owner has reviewed the proposed structure.

**Current state:** Active; inventory completed, reorganization not yet approved.

**Last reviewed:** 2026-07-14

---

## Current objective

Produce a proposed folder map and duplicate-file report that the owner can inspect before any files are moved or removed.

## Completed work

- Counted the files in the source archive.
- Recorded the current folder structure in `05_Projects/Local_Archive_Cleanup/evidence/source-tree.txt`.
- Generated a duplicate candidate list using file hashes.
- Separated exact hash matches from similar names.
- Confirmed that no source file has been deleted or moved.

## Durable decisions

1. Original files remain authoritative until the owner approves a migration.
2. Matching filenames alone are not enough to classify files as duplicates.
3. Exact hash matches may be proposed for deduplication, but no deletion is automatic.
4. Proposed destinations must preserve the original relative path in the migration log.
5. Sensitive records remain outside any AI-readable working set unless explicitly selected.

## Unresolved questions

- Should duplicate copies be deleted, archived separately, or retained?
- Which top-level categories should become permanent?
- Are any folders shared with another person who must approve changes?
- Is an offline backup current enough to permit reorganization?

## Authoritative files and evidence

| Path | Role |
|---|---|
| `05_Projects/Local_Archive_Cleanup/PROJECT.md` | Project scope and owner-approved decisions |
| `05_Projects/Local_Archive_Cleanup/evidence/source-tree.txt` | Source folder inventory |
| `05_Projects/Local_Archive_Cleanup/evidence/file-hashes.csv` | Exact file-hash evidence |
| `05_Projects/Local_Archive_Cleanup/proposals/folder-map.md` | Proposed, non-authoritative destination map |
| `05_Projects/Local_Archive_Cleanup/MIGRATION_LOG.md` | Record of approved moves, if migration begins |

## Safety and authority boundaries

- Do not delete, overwrite, rename, or move source files from this packet alone.
- Do not treat AI-generated classifications as owner approval.
- Do not expose file contents merely to resolve naming ambiguity.
- Stop if the source inventory, backup status, or owner instructions cannot be verified.

## Next permitted action

Review `proposals/folder-map.md` against the source inventory and mark each proposed top-level category as **approve**, **revise**, or **reject**.

No file mutation is permitted until those decisions are recorded in `PROJECT.md`.

## Completion condition

This continuation packet may be closed when:

- every approved move is recorded in `MIGRATION_LOG.md`;
- the post-migration inventory is compared with the original file-hash inventory;
- unresolved duplicate decisions are recorded rather than silently discarded;
- the owner confirms the resulting structure is usable.

---

## Minimal reload prompt

> Read this project continuation packet and the listed authoritative files. Summarize the current state, distinguish completed work from proposals, identify unresolved owner decisions, and recommend only the next permitted action. Do not authorize file deletion or movement.
