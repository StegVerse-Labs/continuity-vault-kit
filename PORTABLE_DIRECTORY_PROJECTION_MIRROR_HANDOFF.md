# Portable Directory Projection Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: `#164`
Branch: `feat/portable-directory-projection-164`
State: ACTIVE_IMPLEMENTATION
Updated: 2026-08-31T11:41:00-05:00
Credential authority: TV/TVC
Authority effect: NONE

## Goal

Expose a bounded read-only machine projection of canonical owner-controlled portable admissions for My KV directory listing and connection-health display.

## Rules

- canonical path must remain beneath an admitted KnowledgeVault domain;
- only batches with `CANONICAL_ADMITTED` + exact canonical readback are listed;
- staged-only content is excluded;
- directory listings expose metadata and opaque canonical refs, not file bytes;
- connection-health projection must be `VERIFIED` and non-authorizing;
- no provider session or credential resolution is performed.

## Claimed surfaces

- `runtime/portable_directory_projection.py`
- `tests/test_portable_directory_projection.py`
- `tools/check_portable_directory_projection.py`
- `PORTABLE_DIRECTORY_PROJECTION_MIRROR_HANDOFF.md`

## Completion boundary

Source validation and merge. Resident exposure through the existing DEVICE_KV runtime remains the next bounded step.
