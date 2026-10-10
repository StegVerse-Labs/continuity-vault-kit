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

## Continuity checkpoint contract — Site#1509 P5 (2026-10-10)
`runtime/workspace_continuity_checkpoint.py` defines `stegverse.kv.workspace-continuity-checkpoint/v1` and `verify_transition(previous, current, ...)`. ChatGPT's cycle-4 final review (Site#1509 comment 6092798251) named P5 as the next executable item; the decision against browser-persisted replay state comes from its cycle-3 review (6092615946).
- **Checkpoint fields:**
  - context binding: principal_id, workspace_type, workspace_id;
  - grant_epoch;
  - source_epoch, which increments when the producer restarts;
  - sequence within the epoch;
  - source_revision;
  - previous_checkpoint_digest;
  - observed_at;
  - anchor (`RECEIPT_REF` or `SIGNATURE`);
  - checkpoint_digest, a SHA-256 over the canonical body;
  - authority_effect NONE.

  Any other field is rejected, including a device id or a self-declared replay_status.
- **Ordering:** checkpoints are ordered by (source_epoch, sequence) and digest links, never by wall clock, so clock regression is tolerated. A valid restart has `source_epoch+1`, `sequence 0`, and links to the last accepted digest.
- **Refused cases:**
  - fork, rollback/replay, an unlinked restart, and epoch or grant regression → DENY;
  - a revoked grant epoch or a context mismatch → DENY;
  - a chain gap, an unknown prior, or malformed or tampered input → FAIL_CLOSED.
- **Anchors are never assumed:** without a caller-supplied anchor verifier that returns `True`, the result is FAIL_CLOSED with `replay_status: UNKNOWN`. `VERIFIED` is reachable only with a real anchor check.
- **Not implemented here (owner work):**
  - producing and persisting checkpoints in KV, which is blocked on registry decision BLK3-WORKSPACE-KV-STORE-WRITER;
  - choosing and verifying the anchor (signature custody or receipt);
  - enforcement in the `.github` DEVICE_KV receiver or the governed admission layer;
  - Site mapping the decision's `replay_status`.

  The module writes nothing and holds no keys.
- **Test:** `tests/test_workspace_continuity_checkpoint.py`, run by the unfiltered guard workflow.

## MyKV assistant binding contract — Site#1509 W4 (2026-10-10)
- **Module:** `runtime/workspace_assistant_binding.py` defines `stegverse.kv.workspace-assistant-binding/v1`. It is pure and storage-free.
- **What it decides:** whether an authenticated WorkSpace session (principal_id, workspace_type, workspace_id, all supplied by the caller's own authentication) resolves to the user's existing MyKV AI Assistant. The assistant is the single `AI_ENTITY` with role `WORKSPACE_ASSISTANT` that this producer projects from `_System/Workspace/assistant.json`.
- **It never creates or substitutes an assistant.** `generic_llm_fallback` is always `FORBIDDEN`.
- **Refused cases:**
  - a missing assistant, or a missing owner binding → FAIL_CLOSED;
  - organizational context → FAIL_CLOSED, because it needs a distinct Org-KV projection and Personal KV is never reused;
  - another user, another workspace, a revoked grant, or a relationship declaration whose parties do not match or that is not active → DENY;
  - a second assistant candidate, or a malformed or authority-asserting projection → FAIL_CLOSED.
- **On ALLOW** it returns the binding:
  - the assistant and owner ids;
  - a continuity key of (owner, assistant, workspace), never a device or page session;
  - source_revision and provenance from the projection metadata;
  - the checkpoint schema, with `replay_status: UNKNOWN`;
  - `relationship_state`, which is `ACTIVE_DECLARED` only when a valid mutual relationship declaration names both parties.

  ALLOW means only that the session may show the assistant: `action_eligible` is false and `authority_effect` is NONE.
- **Reported as NOT_AVAILABLE, not assumed:** `invocation_route` and `ephemeral_inference`. No MyKV assistant invocation manifest route and no StegBrowser consent contract exists yet.
- **Not implemented here (owner work):**
  - populating `assistant.json`, and `workspace.json` `owner_principal_id`, under the authorized KV writer. The owner KV Workspace is currently empty.
  - the assistant invocation route through the SDK and Interlock/InTr;
  - the StegBrowser ephemeral-inference consent and redaction policy;
  - Site consumption of the binding decision.
- **Test:** `tests/test_workspace_assistant_binding.py`, run by the unfiltered guard workflow and built from real `get_personal_workspace_projection` output.

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