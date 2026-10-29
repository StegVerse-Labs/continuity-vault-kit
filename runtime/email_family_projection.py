"""Email-family Workspace projection produced only from ADMIT ingress receipts (Site#1509 lane A).

Schema decision: the existing family-projection delivery contract
(``runtime/workspace_family_projections.py``, ``stegverse.kv.workspace-family-projections/v1``) already
carries any PERSONAL, non-authorizing ``stegverse.kv.<family>-projection/vN`` file under
``_System/Workspace/projections/``. This module therefore adds no new query or record class: it emits one
``stegverse.kv.email-family-projection/v1`` document that the existing reader accepts verbatim.

Inputs are payload-free ``stegverse.kv.email-ingress-receipt/v1`` receipts (``runtime/email_ingress_pipeline``),
``stegverse.kv.email-account-mapping/v1`` mappings (``runtime/email_continuity``), the prior email-family
projection with the accepted head digest (``GENESIS_HEAD`` for the first projection), a caller-supplied integer
provider position per mailbox, and optional provider cursor receipt references. Nothing here reads mail, contacts
a provider, resolves a SKAP reference, writes a file or grants authority. Every refusal is DENY or FAIL_CLOSED and
carries the six actionable fields (failure_code, failed_predicate, required_evidence_or_repair, retry_entrypoint,
owning_existing_goal, next_attempt). A produced projection is SOURCE/LOCAL evidence only, never runtime activation.

Integrity, not authentication: receipt ids, ``chain_digest`` and ``projection_digest`` are unkeyed SHA-256 digests.
They detect accidental or partial alteration; anyone can recompute them, so they do not authenticate who produced a
receipt or projection. Authentication remains the job of the authorized KV writer and TV/TVC.

Ordering: receipts are projected in the order supplied, which must be admission order. Per-mailbox ``sequence``,
``head_receipt_id`` and ``chain_digest`` depend on that order.

Provider position: a non-negative integer that never decreases per mailbox. Several receipt batches may share one
position (Gmail can deliver several pages at one history id); message-id dedupe still refuses replays. A
StegAgents Gmail ``history_id`` (a decimal string) is passed as ``int(history_id)``. ``provider_cursor_refs`` may
carry the StegAgents cursor receipt's ``cursor_sha256`` (``sha256:<64 hex>``) per mapping; it is carried forward.

Account identity: ``mapping_id`` is the account key (StegAgents ``account_ref`` and Notifs ``account_id`` use it).

Writer-side obligations this pure module cannot enforce (owner: the authorized KV writer, BLK3):
- Genesis reset: ``GENESIS_HEAD`` with ``prior=None`` starts a new chain whenever a caller presents it. The writer
  must persist the accepted head and must never pass ``GENESIS_HEAD`` once any projection has been accepted
  (gap EMAIL_PROJECTION_GENESIS_RESET_WRITER_ENFORCED).
- Growth: every admitted row is retained so replay dedupe covers the whole history; the projection grows without
  bound until a compaction/checkpoint with a retained dedupe set exists in KV
  (gap EMAIL_FAMILY_PROJECTION_UNBOUNDED_GROWTH).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from runtime.email_continuity import EmailMappingError, mapping_id_for
from runtime.workspace_projection import FORBIDDEN, METADATA_SCHEMA

SCHEMA = "stegverse.kv.email-family-projection/v1"
RECEIPT_SCHEMA = "stegverse.kv.email-ingress-receipt/v1"
MAPPING_SCHEMA = "stegverse.kv.email-account-mapping/v1"
GENESIS_HEAD = "GENESIS:" + SCHEMA
OWNING_GOAL = "StegVerse-org/.github#164 (P2-workspace-cryptobot); coordination StegVerse-Labs/Site#1509"
RETRY_ENTRYPOINT = "runtime.email_family_projection.project_email_family"
RETRY_ENTRYPOINTS_TEXT = RETRY_ENTRYPOINT + " (local test: tests/test_email_family_projection.py)"
MAX_SCAN_DEPTH = 32

RECEIPT_KEYS = frozenset({
    "schema", "receipt_id", "mapping_id", "canonical_message_id", "staged_content_hash", "decision", "reason",
    "trusted_projection_created", "payload_retained_in_receipt", "authority_effect",
})
MAPPING_KEYS = frozenset({
    "schema", "mapping_id", "email_address", "provider_id", "provider_route", "mapping_state",
    "skap_credential_ref", "credential_secret_present_in_kv", "authority_effect",
})
ROW_KEYS = frozenset({"mapping_id", "canonical_message_id", "receipt_id", "staged_content_hash", "trust_state", "payload_present", "sequence"})
ACCOUNT_KEYS = frozenset({"mapping_id", "provider_id", "mapping_state", "skap_ref", "cursor"})
CURSOR_KEYS = frozenset({"sequence", "head_receipt_id", "chain_digest", "provider_position", "provider_cursor_ref"})
# Contract keys whose names contain a forbidden word but whose values are references or booleans, never secrets.
_CONTRACT_KEYS = frozenset({"skap_credential_ref", "credential_secret_present_in_kv"})
FLAG_KEYS = ("credential_material_present", "provider_operation_authorized", "workspace_grants_authority")

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_MESSAGE_ID = re.compile(r"kv-email-message:[0-9a-f]{64}")
_SKAP_REF = re.compile(r"skap://\S+")
# Token-shaped credential values only (word-bounded), so ordinary text such as "ghp_dev@gmail.com",
# "skap://kv/xoxb-slack" or a route named "bearer auth" is not mistaken for a credential.
_CREDENTIAL_VALUE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"gh[pousr]_[A-Za-z0-9]{36,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|xox[baprs]-[0-9]{6,}-[A-Za-z0-9-]{8,}"
    r"|AKIA[0-9A-Z]{16}(?![A-Za-z0-9])"
    r"|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    r"|(?i:bearer)\s+[A-Za-z0-9._~+/-]{16,}=*"
    r")|-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
_RECEIPT_ID = re.compile(r"kv-email-receipt:[0-9a-f]{64}")
_PROVIDER_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
MAPPING_STATES = frozenset({"MAPPED_CREDENTIAL_REQUIRED", "CREDENTIAL_BOUND", "SESSION_VERIFIED", "REVOKED"})

REPAIRS = {
    "EMAIL_ADMIT_RECEIPT_ABSENT": "a complete stegverse.kv.email-ingress-receipt/v1 receipt for the message, as decide() emits it",
    "EMAIL_ADMIT_RECEIPT_STALE": "a receipt issued by the current ingress pipeline (stegverse.kv.email-ingress-receipt/v1, payload-free, authority NONE)",
    "EMAIL_RECEIPT_FORMAT_INVALID": "receipt fields in the pipeline's formats (kv-email-message:<64 hex>, sha256:<64 hex>, text reason)",
    "EMAIL_ADMIT_RECEIPT_DIGEST_DRIFT": "the receipt exactly as decide() emitted it; its receipt_id must recompute from its own material",
    "EMAIL_MESSAGE_UNADMITTED": "an ADMIT decision from governed ingress; QUARANTINE, REVIEW, REJECT and FAIL_CLOSED messages are never projected",
    "EMAIL_SECRET_FIELD_PRESENT": "inputs without credential material; mailbox credentials stay in SKAP Vault and only a skap:// reference may appear",
    "EMAIL_SKAP_REFERENCE_INVALID": "a mapping whose credential reference is a skap:// reference bound through SKAP Vault",
    "EMAIL_MAPPING_INVALID": "a stegverse.kv.email-account-mapping/v1 mapping exactly as email_continuity emits it",
    "EMAIL_MAPPING_DIGEST_DRIFT": "a mapping whose mapping_id recomputes from its email_address",
    "EMAIL_MAPPING_REVOKED": "a new owner-authorized mapping flow; a revoked mapping admits nothing further",
    "EMAIL_MAPPING_SESSION_UNVERIFIED": "a SESSION_VERIFIED mapping (SKAP reference bound and provider session verified)",
    "EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH": "a receipt, cursor or message bound to a mailbox mapping supplied for this projection",
    "EMAIL_ADMIT_REPLAYED": "a receipt not already projected; a replayed ADMIT is reconciled as ALREADY_EVALUATED, not re-admitted",
    "EMAIL_CONTENT_DRIFT": "the original staged content; a changed message under the same provider identity is never re-admitted silently",
    "EMAIL_PROVIDER_CURSOR_ABSENT": "an integer provider position for every mailbox receiving new receipts",
    "EMAIL_PROVIDER_CURSOR_INVALID": "a non-negative integer provider position (pass a Gmail history_id as int(history_id); opaque cursors are not supported)",
    "EMAIL_PROVIDER_CURSOR_REF_INVALID": "a provider cursor receipt reference of the form sha256:<64 hex> (the StegAgents cursor_sha256)",
    "EMAIL_PROVIDER_CURSOR_REF_UNJUSTIFIED": "a provider cursor reference that changes only with the position advance or new messages it justifies",
    "EMAIL_PROVIDER_CURSOR_ROLLBACK": "a provider position at or after the last accepted one",
    "EMAIL_PROJECTION_ROLLBACK": "the last accepted email-family projection as prior with its projection_digest as accepted_head_digest (GENESIS_HEAD and no prior for the first)",
    "EMAIL_PRIOR_PROJECTION_INVALID": "the prior email-family projection exactly as this producer emitted it",
    "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT": "the prior projection unaltered; its projection_digest and cursor chains must recompute",
    "EMAIL_PRIOR_ACCOUNT_UNMAPPED": "the mapping for every mailbox already present in the prior projection",
    "EMAIL_PROJECTION_CLOCK_INVALID": "a timezone-aware UTC clock",
    "EMAIL_INPUT_MALFORMED": "inputs in the shapes this producer documents (lists of receipt and mapping objects, a position map, a prior projection, a clock)",
}


class _Refusal(Exception):
    def __init__(self, disposition: str, code: str, predicate: str, detail: str = "") -> None:
        super().__init__(code)
        self.disposition, self.code, self.predicate, self.detail = disposition, code, predicate, detail


def _deny(code: str, predicate: str, detail: str = "") -> _Refusal:
    return _Refusal("DENY", code, predicate, detail)


def _fail(code: str, predicate: str, detail: str = "") -> _Refusal:
    return _Refusal("FAIL_CLOSED", code, predicate, detail)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hex(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _digest(value: Any) -> str:
    return "sha256:" + _hex(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _scan_secrets(value: Any, path: str, allowed: frozenset[str] = frozenset()) -> None:
    """Iterative scan: forbidden key words (NFKC-normalised, case-folded) and credential-shaped string values."""
    stack: list[tuple[Any, str, int]] = [(value, path, 0)]
    while stack:
        item, where, depth = stack.pop()
        if depth > MAX_SCAN_DEPTH:
            raise _fail("EMAIL_INPUT_MALFORMED", "INPUT_SHAPE_RECOGNISED", where)
        if isinstance(item, str):
            if _CREDENTIAL_VALUE.search(unicodedata.normalize("NFKC", item)):
                raise _fail("EMAIL_SECRET_FIELD_PRESENT", "NO_SECRET_FIELDS", where)
        elif isinstance(item, list):
            stack.extend((child, f"{where}[{i}]", depth + 1) for i, child in enumerate(item))
        elif isinstance(item, dict):
            for key, child in item.items():
                low = unicodedata.normalize("NFKC", str(key)).casefold()
                if key not in allowed and any(word in low for word in FORBIDDEN):
                    raise _fail("EMAIL_SECRET_FIELD_PRESENT", "NO_SECRET_FIELDS", f"{where}.{key}")
                stack.append((child, f"{where}.{key}", depth + 1))


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_mapping(mapping: Any) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        raise _fail("EMAIL_MAPPING_INVALID", "MAPPING_IS_CONTRACT_OBJECT")
    _scan_secrets(mapping, "mapping", _CONTRACT_KEYS)
    if set(mapping) != MAPPING_KEYS or mapping.get("schema") != MAPPING_SCHEMA:
        raise _fail("EMAIL_MAPPING_INVALID", "MAPPING_IS_CONTRACT_OBJECT", str(mapping.get("mapping_id")))
    if mapping["credential_secret_present_in_kv"] is not False or mapping["authority_effect"] != "NONE":
        raise _fail("EMAIL_SECRET_FIELD_PRESENT", "NO_SECRET_FIELDS", str(mapping["mapping_id"]))
    try:
        expected = mapping_id_for(str(mapping["email_address"]))
    except EmailMappingError:
        raise _fail("EMAIL_MAPPING_INVALID", "MAPPING_IS_CONTRACT_OBJECT", str(mapping["mapping_id"]))
    if mapping["mapping_id"] != expected:
        raise _fail("EMAIL_MAPPING_DIGEST_DRIFT", "MAPPING_ID_RECOMPUTES", str(mapping["mapping_id"]))
    if (mapping["mapping_state"] not in MAPPING_STATES
            or not isinstance(mapping["provider_id"], str) or _PROVIDER_ID.fullmatch(mapping["provider_id"]) is None
            or not isinstance(mapping["provider_route"], str) or not mapping["provider_route"].strip()
            or len(mapping["provider_route"]) > 512 or not mapping["provider_route"].isprintable()):
        raise _fail("EMAIL_MAPPING_INVALID", "MAPPING_IS_CONTRACT_OBJECT", str(mapping["mapping_id"]))
    ref = mapping["skap_credential_ref"]
    if ref is not None and (not isinstance(ref, str) or _SKAP_REF.fullmatch(ref) is None):
        raise _fail("EMAIL_SKAP_REFERENCE_INVALID", "CREDENTIAL_IS_SKAP_REFERENCE_ONLY", str(mapping["mapping_id"]))
    if mapping["mapping_state"] == "SESSION_VERIFIED" and ref is None:
        raise _fail("EMAIL_SKAP_REFERENCE_INVALID", "CREDENTIAL_IS_SKAP_REFERENCE_ONLY", str(mapping["mapping_id"]))
    return mapping


def _validate_receipt(receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, dict) or not receipt:
        raise _fail("EMAIL_ADMIT_RECEIPT_ABSENT", "ADMIT_RECEIPT_PRESENT")
    _scan_secrets(receipt, "receipt")
    missing = RECEIPT_KEYS - set(receipt)
    if missing or any(receipt.get(k) in (None, "") for k in ("receipt_id", "mapping_id", "canonical_message_id", "staged_content_hash", "decision")):
        raise _fail("EMAIL_ADMIT_RECEIPT_ABSENT", "ADMIT_RECEIPT_PRESENT", ",".join(sorted(missing)))
    if (set(receipt) != RECEIPT_KEYS or receipt["schema"] != RECEIPT_SCHEMA
            or receipt["payload_retained_in_receipt"] is not False or receipt["authority_effect"] != "NONE"):
        raise _fail("EMAIL_ADMIT_RECEIPT_STALE", "ADMIT_RECEIPT_CURRENT", str(receipt.get("receipt_id")))
    if (not isinstance(receipt["canonical_message_id"], str) or _MESSAGE_ID.fullmatch(receipt["canonical_message_id"]) is None
            or not isinstance(receipt["staged_content_hash"], str) or _SHA256.fullmatch(receipt["staged_content_hash"]) is None
            or not isinstance(receipt["reason"], str)):
        raise _fail("EMAIL_RECEIPT_FORMAT_INVALID", "RECEIPT_FIELDS_WELL_FORMED", str(receipt["receipt_id"]))
    material = {k: receipt[k] for k in ("mapping_id", "canonical_message_id", "staged_content_hash", "decision", "reason")}
    if receipt["receipt_id"] != "kv-email-receipt:" + _hex(material):
        raise _fail("EMAIL_ADMIT_RECEIPT_DIGEST_DRIFT", "RECEIPT_ID_RECOMPUTES", str(receipt["receipt_id"]))
    if receipt["decision"] != "ADMIT" or receipt["trusted_projection_created"] is not True:
        raise _deny("EMAIL_MESSAGE_UNADMITTED", "MESSAGE_ADMITTED", f"{receipt['decision']}:{receipt['receipt_id']}")
    return receipt


def _body(accounts: list[dict[str, Any]], messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema": SCHEMA, "workspace_type": "PERSONAL", "accounts": accounts, "messages": messages}


def _chain(previous: str | None, receipt_id: str) -> str:
    return _digest({"previous": previous, "receipt_id": receipt_id})


def _validate_prior(prior: Any, mappings: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if prior is None:
        return {}, []
    if not isinstance(prior, dict) or prior.get("schema") != SCHEMA:
        raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION")
    _scan_secrets({k: v for k, v in prior.items() if k not in FLAG_KEYS}, "prior")
    if any(prior.get(flag) is not False for flag in FLAG_KEYS) or prior.get("authority_effect") != "NONE":
        raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION", "authority_flags")
    accounts, messages = prior.get("accounts"), prior.get("messages")
    if not isinstance(accounts, list) or not isinstance(messages, list):
        raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION")
    if prior.get("projection_digest") != _digest(_body(accounts, messages)):
        raise _fail("EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT", "PRIOR_DIGEST_RECOMPUTES")
    by_mapping: dict[str, dict[str, Any]] = {}
    for account in accounts:
        if not isinstance(account, dict) or set(account) != ACCOUNT_KEYS or not isinstance(account["cursor"], dict) or set(account["cursor"]) != CURSOR_KEYS:
            raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION")
        mid = account["mapping_id"]
        if mid in by_mapping:
            raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION", str(mid))
        if mid not in mappings:
            raise _fail("EMAIL_PRIOR_ACCOUNT_UNMAPPED", "PRIOR_ACCOUNTS_MAPPED", str(mid))
        by_mapping[mid] = account
    heads: dict[str, tuple[int, str | None, str | None]] = {mid: (0, None, None) for mid in by_mapping}
    seen_ids: set[str] = set()
    for message in messages:
        if (not isinstance(message, dict) or set(message) != ROW_KEYS or message["payload_present"] is not False
                or message["trust_state"] != "TRUSTED_ADMITTED"
                or not isinstance(message["canonical_message_id"], str) or _MESSAGE_ID.fullmatch(message["canonical_message_id"]) is None
                or not isinstance(message["staged_content_hash"], str) or _SHA256.fullmatch(message["staged_content_hash"]) is None
                or not isinstance(message["receipt_id"], str) or _RECEIPT_ID.fullmatch(message["receipt_id"]) is None):
            raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION")
        if message["canonical_message_id"] in seen_ids:
            raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION", message["canonical_message_id"])
        seen_ids.add(message["canonical_message_id"])
        mid = message["mapping_id"]
        if mid not in heads:
            raise _fail("EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT", "PRIOR_DIGEST_RECOMPUTES", str(mid))
        seq, head, _ = heads[mid]
        if not _is_count(message["sequence"]) or message["sequence"] != seq + 1:
            raise _fail("EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT", "PRIOR_DIGEST_RECOMPUTES", str(mid))
        heads[mid] = (seq + 1, _chain(head, message["receipt_id"]), message["receipt_id"])
    for mid, account in by_mapping.items():
        cursor = account["cursor"]
        seq, head, last = heads[mid]
        if not _is_count(cursor["sequence"]) or cursor["sequence"] != seq or cursor["chain_digest"] != head or cursor["head_receipt_id"] != last:
            raise _fail("EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT", "PRIOR_DIGEST_RECOMPUTES", str(mid))
        if cursor["provider_position"] is not None and not _is_count(cursor["provider_position"]):
            raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION", str(mid))
        ref = cursor["provider_cursor_ref"]
        if ref is not None and (not isinstance(ref, str) or _SHA256.fullmatch(ref) is None):
            raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION", str(mid))
    return by_mapping, [dict(m) for m in messages]


def _position(value: Any, mid: str) -> int:
    if not _is_count(value):
        raise _fail("EMAIL_PROVIDER_CURSOR_INVALID", "PROVIDER_CURSOR_IS_ORDERED_POSITION", mid)
    return value


def _refusal_record(refusal: _Refusal) -> dict[str, Any]:
    return {
        "schema": SCHEMA + "#decision",
        "disposition": refusal.disposition,
        "projection": None,
        "detail": refusal.detail,
        "failure_code": refusal.code,
        "failed_predicate": refusal.predicate,
        "required_evidence_or_repair": REPAIRS[refusal.code],
        "retry_entrypoint": RETRY_ENTRYPOINTS_TEXT,
        "owning_existing_goal": OWNING_GOAL,
        "next_attempt": "the next projection request is decided again from the receipts, mappings and prior it presents; nothing waits",
        "runtime_evidence": False,
        "authority_effect": "NONE",
    }


def project_email_family(
    *,
    receipts: Iterable[Any],
    mappings: Iterable[Any],
    provider_positions: dict[str, Any],
    accepted_head_digest: str,
    prior: dict[str, Any] | None = None,
    provider_cursor_refs: dict[str, Any] | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> dict[str, Any]:
    """Return ``{disposition: ALLOW, projection}`` or a six-field DENY / FAIL_CLOSED record. Pure; writes nothing.

    ``accepted_head_digest`` is required: ``GENESIS_HEAD`` with no prior for the first projection, otherwise the
    ``projection_digest`` of the last accepted projection, which must be the prior presented."""
    try:
        return _project(list(receipts), list(mappings), provider_positions, prior, accepted_head_digest,
                        {} if provider_cursor_refs is None else provider_cursor_refs, clock)
    except _Refusal as refusal:
        return _refusal_record(refusal)
    except Exception as exc:  # noqa: BLE001 - every unrecognised input (or raising clock/iterable) fails closed
        return _refusal_record(_fail("EMAIL_INPUT_MALFORMED", "INPUT_SHAPE_RECOGNISED", type(exc).__name__))


def _project(receipts, mappings_in, provider_positions, prior, accepted_head_digest, cursor_refs, clock) -> dict[str, Any]:
    mappings: dict[str, dict[str, Any]] = {}
    for mapping in mappings_in:
        m = _validate_mapping(mapping)
        if m["mapping_id"] in mappings:
            raise _fail("EMAIL_MAPPING_INVALID", "MAPPING_IS_CONTRACT_OBJECT", m["mapping_id"])
        mappings[m["mapping_id"]] = m

    presented = prior.get("projection_digest") if isinstance(prior, dict) else (GENESIS_HEAD if prior is None else None)
    if presented != accepted_head_digest:
        raise _deny("EMAIL_PROJECTION_ROLLBACK", "PRIOR_IS_ACCEPTED_HEAD", str(presented))
    prior_accounts, messages = _validate_prior(prior, mappings)
    by_message = {m["canonical_message_id"]: m for m in messages}

    if not isinstance(provider_positions, dict):
        raise _fail("EMAIL_PROVIDER_CURSOR_INVALID", "PROVIDER_CURSOR_IS_ORDERED_POSITION")
    if not isinstance(cursor_refs, dict):
        raise _fail("EMAIL_PROVIDER_CURSOR_REF_INVALID", "PROVIDER_CURSOR_REF_IS_SHA256")
    for mid, ref in cursor_refs.items():
        if not isinstance(ref, str) or _SHA256.fullmatch(ref) is None:
            raise _fail("EMAIL_PROVIDER_CURSOR_REF_INVALID", "PROVIDER_CURSOR_REF_IS_SHA256", mid)

    new_by_mapping: dict[str, list[dict[str, Any]]] = {}
    for raw in receipts:  # supplied order is admission order
        receipt = _validate_receipt(raw)
        mid = receipt["mapping_id"]
        if mid not in mappings:
            raise _deny("EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH", "PROVENANCE_BOUND_TO_SUPPLIED_MAPPING", receipt["receipt_id"])
        state = mappings[mid]["mapping_state"]
        if state == "REVOKED":
            raise _deny("EMAIL_MAPPING_REVOKED", "MAPPING_NOT_REVOKED", mid)
        if state != "SESSION_VERIFIED":
            raise _deny("EMAIL_MAPPING_SESSION_UNVERIFIED", "MAPPING_SESSION_VERIFIED", mid)
        known = by_message.get(receipt["canonical_message_id"])
        if known is not None:
            if known["mapping_id"] != mid:
                raise _deny("EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH", "PROVENANCE_BOUND_TO_SUPPLIED_MAPPING", receipt["receipt_id"])
            if known["staged_content_hash"] != receipt["staged_content_hash"]:
                raise _fail("EMAIL_CONTENT_DRIFT", "SAME_MESSAGE_SAME_CONTENT", receipt["canonical_message_id"])
            raise _deny("EMAIL_ADMIT_REPLAYED", "ADMIT_NOT_REPLAYED", receipt["receipt_id"])
        row = {
            "mapping_id": mid,
            "canonical_message_id": receipt["canonical_message_id"],
            "receipt_id": receipt["receipt_id"],
            "staged_content_hash": receipt["staged_content_hash"],
            "trust_state": "TRUSTED_ADMITTED",
            "payload_present": False,
        }
        by_message[row["canonical_message_id"]] = row
        new_by_mapping.setdefault(mid, []).append(row)

    emitted = set(prior_accounts) | set(new_by_mapping)
    for mid in list(provider_positions) + list(cursor_refs):
        if mid not in emitted:  # a position/ref for a mailbox with no account and no receipts would be dropped silently
            raise _deny("EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH", "PROVENANCE_BOUND_TO_SUPPLIED_MAPPING", str(mid))

    accounts: list[dict[str, Any]] = []
    for mid in sorted(emitted):
        mapping = mappings[mid]
        old = (prior_accounts.get(mid) or {}).get("cursor") or {
            "sequence": 0, "head_receipt_id": None, "chain_digest": None, "provider_position": None, "provider_cursor_ref": None}
        old_pos = old["provider_position"]
        fresh = new_by_mapping.get(mid, [])
        if mid in provider_positions:
            pos = _position(provider_positions[mid], mid)
        elif fresh:
            raise _fail("EMAIL_PROVIDER_CURSOR_ABSENT", "PROVIDER_CURSOR_PRESENT", mid)
        else:
            pos = old_pos
        # Equal positions are legitimate (several pages at one provider position); every new message id is
        # already proven new for this mapping above, so only a strictly lower position is a rollback.
        if old_pos is not None and pos is not None and pos < old_pos:
            raise _deny("EMAIL_PROVIDER_CURSOR_ROLLBACK", "PROVIDER_CURSOR_NOT_BEHIND_ACCEPTED", mid)
        ref = cursor_refs.get(mid, old["provider_cursor_ref"])
        advanced = pos is not None and (old_pos is None or pos > old_pos)
        if mapping["mapping_state"] == "REVOKED" and (pos != old_pos or ref != old["provider_cursor_ref"]):
            raise _deny("EMAIL_MAPPING_REVOKED", "MAPPING_NOT_REVOKED", mid)
        if ref != old["provider_cursor_ref"] and not (advanced or fresh):
            raise _deny("EMAIL_PROVIDER_CURSOR_REF_UNJUSTIFIED", "PROVIDER_CURSOR_REF_TIED_TO_POSITION", mid)
        seq, head, head_id = old["sequence"], old["chain_digest"], old["head_receipt_id"]
        for row in fresh:
            seq += 1
            head = _chain(head, row["receipt_id"])
            head_id = row["receipt_id"]
            row["sequence"] = seq
            messages.append(row)
        accounts.append({
            "mapping_id": mid,
            "provider_id": mapping["provider_id"],
            "mapping_state": mapping["mapping_state"],
            "skap_ref": mapping["skap_credential_ref"],
            "cursor": {"sequence": seq, "head_receipt_id": head_id, "chain_digest": head, "provider_position": pos,
                       "provider_cursor_ref": ref},
        })

    produced = clock()
    if not isinstance(produced, datetime) or produced.utcoffset() is None:
        raise _fail("EMAIL_PROJECTION_CLOCK_INVALID", "PROJECTION_CLOCK_TIMEZONE_AWARE")
    body = _body(accounts, messages)
    digest = _digest(body)
    projection = {
        **body,
        "projection_digest": digest,
        "credential_material_present": False,
        "provider_operation_authorized": False,
        "workspace_grants_authority": False,
        "projection_metadata": {
            "schema": METADATA_SCHEMA,
            "observed_at": produced.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "observed_at_semantics": "KV_PROJECTION_PRODUCTION_TIME",
            "source_revision": digest.removeprefix("sha256:"),
            "provenance_ref": "kv-email-ingress-admit-receipts:" + digest,
            "workspace_type": "PERSONAL",
            "workspace_id": None,
            "owner_principal_id": None,
            "grant_state": "UNKNOWN",
            "revocation_epoch": None,
            "authority_effect": "NONE",
        },
        "authority_effect": "NONE",
    }
    return {"schema": SCHEMA + "#decision", "disposition": "ALLOW", "projection": projection,
            "runtime_evidence": False, "action_eligible": False, "authority_effect": "NONE"}
