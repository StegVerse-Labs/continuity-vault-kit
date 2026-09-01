# KnowledgeVault Workspace Projection Mirror Handoff

Updated: 2026-08-31
Repository: StegVerse-Labs/continuity-vault-kit
State: ACTIVE_IMPLEMENTATION
Authority effect: NONE
Credential authority: TV/TVC

## Goal
Provide a bounded, read-only Workspace projection from the owner's actual Personal KnowledgeVault without turning Site, a provider, or the projection itself into identity or access authority.

## Personal KV source
Runtime/user Workspace state is read only from `_System/Workspace/` under the current `STEGVERSE_KV_ROOT`. Absence is a valid empty Workspace and must not be replaced with sample/fabricated principals.

Files:
- `workspace.json`
- `principals.json`
- `relationships.json`
- `organizations.json`
- `memberships.json`
- `feed.json`
- `assistant.json`

Every present file is schema-validated, secret-field rejected, and authority-bounded. `AI_ENTITY` labeling is derived from principal type. The projection contains references/metadata only and never credential material.

## Organizational boundary
This lane does not reinterpret Personal KV as Org-KV. Organizational Workspace projection requires a distinct Org-KV / Org-Emp-KV runtime and the conjunctive employee+machine+membership+capability+transition admission contract owned by StegOS.

## Claimed surfaces
- `runtime/workspace_projection.py`
- `tests/test_workspace_projection.py`
- `WORKSPACE_PROJECTION_MIRROR_HANDOFF.md`

## Completion boundary
Source implementation and deterministic tests do not prove a resident KV is mounted, a Workspace registry exists, or a Site request has been observed. Authentic data requires current `STEGVERSE_KV_ROOT` plus an admitted DEVICE_KV query.