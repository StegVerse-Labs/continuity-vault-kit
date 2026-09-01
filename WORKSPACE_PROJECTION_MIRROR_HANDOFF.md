# KnowledgeVault Workspace Projection Mirror Handoff

Updated: 2026-08-31
Repository: StegVerse-Labs/continuity-vault-kit
State: SOURCE_IMPLEMENTED_RUNTIME_OBSERVATION_PENDING
Authority effect: NONE
Credential authority: TV/TVC

## Goal
Provide a bounded, read-only Workspace projection from the owner's actual Personal KnowledgeVault without turning Site, a provider, or the projection itself into identity or access authority.

## Personal KV source
`runtime/workspace_projection.py` reads runtime/user Workspace state only from `_System/Workspace/` under the current `STEGVERSE_KV_ROOT`. Absence returns `KV_WORKSPACE_EMPTY`; it is never replaced with sample/fabricated principals.

Supported files are `workspace.json`, `principals.json`, `relationships.json`, `organizations.json`, `memberships.json`, `feed.json`, and `assistant.json`. Every present file is schema-validated, secret-field rejected, and authority-bounded. `AI_ENTITY` labeling is derived from principal type. Assistant identity must be `AI_ENTITY` with `WORKSPACE_ASSISTANT` role.

Relationships must bind known principals. Organizations must be typed `ORGANIZATION`. Membership state is bounded to ACTIVE/PENDING/SUSPENDED/REVOKED. Feed actors must resolve to known principals and visibility must use the canonical Workspace visibility vocabulary.

## Organizational boundary
This lane does not reinterpret Personal KV as Org-KV. Organizational Workspace projection requires a distinct Org-KV / Org-Emp-KV runtime and the conjunctive employee+machine+membership+capability+transition admission contract owned by StegOS.

## Implemented surfaces
- `runtime/workspace_projection.py` — commit `79b968237185cf00ae61764fea1532d08cba44ab`
- `tests/test_workspace_projection.py` — commit `ffeca16657f7d64287077ae5651d8cbe34ea7219`
- `WORKSPACE_PROJECTION_MIRROR_HANDOFF.md`

## Completion boundary
Source implementation and deterministic test source do not prove a resident KV is mounted, a Workspace registry exists, or a Site request has been observed. Authentic data requires current `STEGVERSE_KV_ROOT` plus an admitted DEVICE_KV query and exact response recovery.