# KnowledgeVault Workspace Projection Mirror Handoff

Updated: 2026-08-31
Repository: StegVerse-Labs/continuity-vault-kit
State: CONNECTED_KV_WORKSPACE_ROOT_CREATED_QUERY_OBSERVATION_PENDING
Authority effect: NONE
Credential authority: TV/TVC

## Goal
Provide a bounded, read-only Workspace projection from the owner's actual Personal KnowledgeVault without turning Site, a provider, or the projection itself into identity or access authority.

## Personal KV source
`runtime/workspace_projection.py` reads runtime/user Workspace state only from `_System/Workspace/` under the current `STEGVERSE_KV_ROOT`. Absence returns `KV_WORKSPACE_EMPTY`; it is never replaced with sample/fabricated principals.

Supported files are `workspace.json`, `principals.json`, `relationships.json`, `organizations.json`, `memberships.json`, `feed.json`, and `assistant.json`. Every present file is schema-validated, secret-field rejected, and authority-bounded. `AI_ENTITY` labeling is derived from principal type. Assistant identity must be `AI_ENTITY` with `WORKSPACE_ASSISTANT` role.

Relationships must bind known principals. Organizations must be typed `ORGANIZATION`. Membership state is bounded to ACTIVE/PENDING/SUSPENDED/REVOKED. Feed actors must resolve to known principals and visibility must use the canonical Workspace visibility vocabulary.

## Connected owner-KV state
On 2026-08-31 the existing connected owner KnowledgeVault was inspected before mutation. `_System` did not contain a Workspace directory. `_System/Workspace` was then created in that existing KnowledgeVault. No principal, relationship, organization, membership, feed, assistant, credential, or authority data was fabricated or inserted. Therefore the authentic current Workspace registry content is empty until governed interactions populate it.

This is runtime/user state under `_System`; it is not added to the source installation template and does not convert provider storage into authority.

## Projection metadata — Site#1509 P3 (2026-10-10)
Every projection now carries `projection_metadata` (`stegverse.kv.workspace-projection-metadata/v1`), approved as P3 by the ChatGPT final review on Site#1509 (comment 6092132771):
- `observed_at`: when this producer read and projected the KV sources (`observed_at_semantics: KV_PROJECTION_PRODUCTION_TIME`). It is never a source-event time. The clock is UTC and injectable for tests; a naive clock fails closed.
- `source_revision` / `provenance_ref`: SHA-256 over the canonical JSON of the seven validated source records (absent files bound as null), so rows and metadata share one source revision.
- `workspace_type: PERSONAL`; `workspace_id` / `owner_principal_id` only when present in `workspace.json`.
- `grant_state: UNKNOWN` and `revocation_epoch: null`. Personal KV Workspace records hold no verified grant or revocation source, so `ACTIVE` is never asserted. `source_cursor` is omitted because no genuine cursor exists.
- `authority_effect: NONE`. The `.github` receiver (`scripts/workspace_device_kv_query_extension.py`) is unchanged: it still calls with `kv_data_root` only and checks the same authority fields.
- Focused test: `tests/test_workspace_projection.py`, now run by the unfiltered guard `.github/workflows/runtime-import-and-secret-policy.yml` (no new workflow; `EXPECTED_WORKFLOW_COUNT` unchanged).

## Organizational boundary
This lane does not reinterpret Personal KV as Org-KV. Organizational Workspace projection requires a distinct Org-KV / Org-Emp-KV runtime and the conjunctive employee+machine+membership+capability+transition admission contract owned by StegOS.

## Implemented surfaces
- `runtime/workspace_projection.py` — commit `79b968237185cf00ae61764fea1532d08cba44ab`
- `tests/test_workspace_projection.py` — commit `ffeca16657f7d64287077ae5651d8cbe34ea7219`
- `WORKSPACE_PROJECTION_MIRROR_HANDOFF.md`
- `.github/workflows/runtime-import-and-secret-policy.yml` (workspace projection step)
- `data/session-work-claims.d/cvk-workspace-projection-metadata-20261010.json`

## Remaining evidence gates
Resident source must refresh to the current CVK + Labs `.github` Workspace query extension; an authentic registered-node request must then return `KV_WORKSPACE_EMPTY` (or later governed content) through the persisted HB-derived DEVICE_KV response and Site must recover those exact bytes.