# KnowledgeVault Workspace Projection Mirror Handoff

Updated: 2026-10-17
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

## Session-authentication contract mirror — Site#1509 W4 (2026-10-10)
- **Module:** `runtime/workspace_session_authentication.py` defines `stegverse.workspace.session-authentication/v1`, the producer-side mirror of Site `assets/workspace-session-authentication.js` (Site#1516, #1518): same predicates, same order, same output fields. It is pure and reads the session only; the KV projection, device registration and process state are never inputs.
- **What it decides:** whether a caller session may be handed to `resolve_assistant_binding`. A principal copied from KV ownership data (`KV_OWNERSHIP_IS_NOT_AUTHENTICATION`), a node registration (`DEVICE_REGISTRATION_IS_NOT_AUTHENTICATION`), browser or page state (`BROWSER_STATE_IS_NOT_AUTHENTICATION`), or a bare `principal_id` without a TV/TVC-backed caller-authentication receipt is refused `FAIL_CLOSED` before the binding resolver runs.
- **ALLOW semantics (ChatGPT review Site#1509 comment 6102365201):** `CALLER_AUTHENTICATION_RECEIPT_PRESENT` is an informational acceptance of caller-supplied receipt fields. Every decision carries `admission_class: CALLER_SUPPLIED_FIELDS_ACCEPTED`, `verification: CALLER_SUPPLIED_NOT_PAGE_VERIFIED`, `runtime_authentication_evidence: false`, `action_eligible: false`, `authority_effect: NONE`. No TV/TVC verification is performed here.
- **Not implemented here (owner work):** the TV/TVC caller-authentication issuer and an independently verified receipt transport.
- **Test:** `tests/test_workspace_session_authentication.py` (28 refusal cases, ALLOW shape, session-only input, binding integration built from real `get_personal_workspace_projection` output, optional cross-repository predicate-name parity when a Site checkout is present), run by the unfiltered guard workflow.

## Tasks and commitments projection — Site#1509 WS-TASKS (2026-10-11)
- **Directive:** owner/ChatGPT parallel implementation plan (Site#1509 comment 6104154989) item WS-TASKS: tasks/commitments projection presentation, timelines and proposed-action composition only.
- **Module:** `runtime/workspace_tasks_projection.py` defines `stegverse.kv.workspace-tasks-projection/v1`, produced read-only from `_System/Workspace/tasks.json` (`stegverse.kv.workspace-tasks/v1`: `tasks[]` with task_id, title, status ∈ OPEN/IN_PROGRESS/BLOCKED/DONE/CANCELLED, optional timezone-aware due_at/created_at, source_ref; `commitments[]` with commitment_id, statement, status ∈ PROPOSED/ACTIVE/FULFILLED/WITHDRAWN/REVOKED, counterparty_principal_id, due_at, source_ref). Output: tasks, commitments, a derived `timeline` (dated items by due_at, then undated), and `stegverse.kv.workspace-projection-metadata/v1` whose source_revision digests the exact context and tasks source bytes (`provenance_ref: kv-workspace-tasks-source:sha256:…`).
- **Invariants:** every row and timeline item is `action_eligible: false` with `execution_requires_admitted_manifest: true`; `action_authority: NONE`; revoked commitments are projected as `REVOKED`, never hidden; secrets, invalid statuses, naive timestamps, duplicate ids and authority claims fail closed; the producer writes nothing.
- **Not implemented here (owner work):** populating `tasks.json` under the authorized KV writer; carrying this projection through the DEVICE_KV Workspace query; any task transition route (a WorkSpace "propose completion" stays a FAIL_CLOSED, unsubmitted draft until an admitted manifest route exists).
- **Test:** `tests/test_workspace_tasks_projection.py`, run by the unfiltered guard workflow.

## Delivery readers: family projections and continuity checkpoint — Site#1509 (2026-10-11)
- `runtime/workspace_family_projections.py` — `get_personal_family_projections(kv_data_root, clock)` → `stegverse.kv.workspace-family-projections/v1`: reads `_System/Workspace/projections/*.json` (persisted by the authorized KV writer from each family producer, e.g. the CryptoBot `stegverse.kv.cryptobot-portfolio-projection/v1`), requires every file to be a PERSONAL, non-authorizing projection (`credential_material_present`, `provider_operation_authorized`, `workspace_grants_authority` false; `trade_authority_granted` false when present) carrying its own `stegverse.kv.workspace-projection-metadata/v1` with `observed_at`; refuses the reserved personal/tasks/checkpoint schemas, duplicate schemas (`family_projection_schema_ambiguous`), unsafe names, secrets and malformed files with stable reasons; empty or missing directory → `KV_FAMILY_PROJECTIONS_EMPTY`. Projections are returned verbatim (never re-stamped); the delivery carries its own metadata over the exact source bytes.
- `runtime/workspace_continuity_checkpoint_projection.py` — `get_personal_continuity_checkpoint(kv_data_root, clock)` → `stegverse.kv.workspace-continuity-checkpoint-delivery/v1`: reads `_System/Workspace/continuity-checkpoint.json` (current) and `continuity-checkpoint.previous.json` (last accepted), both `stegverse.kv.workspace-continuity-checkpoint/v1`, and returns `{checkpoint, decision}` where `decision` is `verify_transition(previous, current, principal=workspace owner, PERSONAL, workspace_id, anchor_verifier=None)`. No anchor verifier exists here, so the decision is never `ALLOW`/`VERIFIED`: a well-linked chain yields `FAIL_CLOSED · CHECKPOINT_ANCHOR_VERIFIER_UNAVAILABLE:<link>` with replay `UNKNOWN`; chain faults yield the verifier's `DENY`; `anchor_verified: false`. Absent checkpoint → `KV_CHECKPOINT_ABSENT`; a previous without a current fails closed.
- Both readers write nothing and grant nothing. Consumers: StegVerse-Labs/.github DEVICE_KV extension record classes `WORKSPACE_FAMILY_PROJECTIONS` and `WORKSPACE_CONTINUITY_CHECKPOINT`; Site bridge `loadPersonalProjections` / `loadAssistantCheckpoint`.
- Owner gaps unchanged: the KV writer (BLK3) that persists these files, an anchor verifier, and the sovereign ingress / TVC Drive session for runtime delivery.
- Tests: `tests/test_workspace_family_projections.py`, `tests/test_workspace_continuity_checkpoint_projection.py`.

## Plain-language decision reasons — .github#3106 explanation contract / Site#1509 (2026-10-11)
- `runtime/workspace_decision_reasons.py` — `SESSION_REASONS` and `BINDING_REASONS`: one plain-language reason per predicate that `resolve_session_authentication` and `resolve_assistant_binding` can return, plus `explanation_record(...)`. Every decision from both modules now carries `explanation_record` (disposition, predicate, requested action, authority source NONE, consequence NOT_AUTHENTICALLY_OBSERVED, `why`), ready for the universal explanation contract (`stegverse.user-facing-explanation/v1`, StegVerse-Labs/.github). Without it an explanation could only restate the predicate.
- Reasons are explanatory only: dispositions, predicates, `action_eligible` and `authority_effect` are unchanged.
- **Receipt invariant (#251, 2026-10-13):** there is no ALLOW without a receipt. `explanation_record` explains a held ALLOW, which has no receipt, as `UNKNOWN`. The decision itself is unchanged.
- **Actionable dispositions (#253, 2026-10-13, Organization Role item 5):** every explanation record (all non-ALLOW) carries `failure_code`, `failed_predicate`, `required_evidence_or_repair`, `retry_entrypoint`, `owning_existing_goal` (`STEGVERSE-WORKSPACE-ANY-DEVICE-KV-SURFACE-001`) and `next_attempt`. These mirror explanation contract v1.2.0 in StegVerse-Labs/.github.
- **Open owner repair (WorkSpace WU1):** a device-independent verified-user continuity query path, so the Site Personal WorkSpace request no longer binds to a device-local node registration. Until then the Site precondition holds a registered exemption in StegVerse-Labs/.github `data/organization-role-exemption-register.json`.
- Site mirrors the same text (`reasons` on `StegVerseWorkspaceSessionAuthentication` and `StegVerseWorkspaceAssistantBinding`) and uses it for the DR2 and DR4 device-continuity "Why?".
- Tests: `tests/test_workspace_decision_reasons.py` (every reachable predicate has a reason and every reason a reachable predicate; reasons are plain language; every session decision path carries a matching record; with a .github checkout, each record builds a conformant explanation whose "Why" is the reason; with a Site checkout, the Site text is identical).

## Email-family projection from ADMIT receipts — Site#1509 lane A / Goal StegVerse-org/.github#164 (2026-10-28)
- **Schema decision:** the existing family-projection contract carries email. `runtime/email_family_projection.py` emits one `stegverse.kv.email-family-projection/v1` document that `get_personal_family_projections` accepts verbatim under `_System/Workspace/projections/`. No new query class, record class or DEVICE_KV extension is added. One file covers every mapped mailbox, because the reader refuses duplicate schemas.
- **Call:** `project_email_family(receipts, mappings, provider_positions, accepted_head_digest, prior=None, provider_cursor_refs=None, clock)`.
  - `accepted_head_digest` is required. For the first projection it is `GENESIS_HEAD` (`GENESIS:stegverse.kv.email-family-projection/v1`) with no prior. After that it is the last accepted `projection_digest`, and the prior presented must be that projection.
- **Inputs** are only:
  - payload-free `stegverse.kv.email-ingress-receipt/v1` receipts, supplied in admission order. The per-mailbox `sequence`, `head_receipt_id` and `chain_digest` depend on that order;
  - `stegverse.kv.email-account-mapping/v1` mappings.
- **Output:**
  - **Rows** carry ids, the receipt id, `staged_content_hash` and `payload_present: false`. They never carry the message body or the email address.
  - **Each account** carries `skap_ref`, which must fully match `skap://\S+`.
  - **Each account's cursor** carries `sequence`, `head_receipt_id`, `chain_digest`, `provider_position` and `provider_cursor_ref`.
  - **Digest format:** `chain_digest` and `projection_digest` are `sha256:<64 hex>`.
- **Provider position:**
  - It is a non-negative integer, never a bool. Pass a StegAgents Gmail `history_id`, which is a decimal string, as `int(history_id)`.
  - An equal position with new message ids is accepted, because Gmail can deliver several pages at one history id (StegAgents #46). Replays are still refused by message-id dedupe. Only a strictly lower position is `EMAIL_PROVIDER_CURSOR_ROLLBACK`.
  - The optional `provider_cursor_refs[mapping_id]` is the StegAgents cursor receipt's `cursor_sha256` (`sha256:<64 hex>`). It is validated, then carried forward, and is null when it has never been supplied.
- **Integrity, not authentication:** receipt ids, `chain_digest` and `projection_digest` are unkeyed SHA-256 digests. They detect alteration, but anyone can recompute them. Authentication stays with the authorized KV writer and TV/TVC.
- **Account identity:** the source of truth is `mapping_id`. The table below maps fields to the StegAgents and Notifs consumers.

  | Consumer field | Source |
  |---|---|
  | StegAgents `account_ref` | `mapping_id` |
  | Notifs `account_id` | `mapping_id` |
  | Notifs `receipt_ref` | `receipt_id` |
  | Notifs `receipt_digest` | `"sha256:"` + hex SHA-256 of `receipt_id` |
  | Notifs `message_digest` | `staged_content_hash` |
  | Notifs `provider` | `provider_id` |
  | Notifs `authenticated` | `mapping_state == "SESSION_VERIFIED"` |

- **Refused cases** (DENY or FAIL_CLOSED, each with the six fields `failure_code`, `failed_predicate`, `required_evidence_or_repair`, `retry_entrypoint`, `owning_existing_goal`, `next_attempt`):
  - an unadmitted message;
  - a revoked mapping, or a session that is not verified;
  - a replayed or duplicate ADMIT;
  - content drift under the same message id;
  - a provider-cursor rollback, or a cursor that is absent or not an integer;
  - a cursor reference in the wrong format;
  - a projection rollback against the accepted head, including a missing or genesis head presented with a prior;
  - cross-account provenance;
  - an absent or stale receipt;
  - a receipt field in the wrong format: `kv-email-message:<64 hex>` or `sha256:<64 hex>` not fully matched, or a reason that is not text;
  - a secret key (NFKC-normalised and case-folded), or a credential-shaped string value: bearer, `gh[pousr]_`, `github_pat_`, PEM, AKIA, `xox?-`, or JWT;
  - a credential reference that is not `skap://`;
  - receipt, mapping or prior digest drift;
  - prior rows or cursors that are not exactly this producer's shape;
  - a scan depth above 32;
  - any raised exception from the inputs, the iterable or the clock, which becomes `EMAIL_INPUT_MALFORMED`;
  - a clock without a UTC offset.
- **Evidence class:** SOURCE + LOCAL_TEST. No mailbox, provider, SKAP resolution or KV write is involved. ALLOW carries `runtime_evidence: false` and `action_eligible: false`.
- **Open gaps (owner work):**
  - the authorized KV writer (BLK3), which persists `projections/email-family.json` and the accepted head digest;
  - opaque provider cursors such as Graph delta links. They fail closed as `EMAIL_PROVIDER_CURSOR_INVALID`;
  - live ADMIT receipts, which depend on email activation predicates 8 and 11.
- **Test:** `tests/test_email_family_projection.py` (unittest), run by the existing `validate-kv-email-ingress-policy.validate` step 03. No new workflow is added.

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