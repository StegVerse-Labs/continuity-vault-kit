"""Email-family Workspace projection produced only from ADMIT ingress receipts (Site#1509 lane A).

Schema decision: the existing family-projection delivery contract
(``runtime/workspace_family_projections.py``, ``stegverse.kv.workspace-family-projections/v1``) already
carries any PERSONAL, non-authorizing ``stegverse.kv.<family>-projection/vN`` file under
``_System/Workspace/projections/``. This module therefore adds no new query or record class: it emits one
``stegverse.kv.email-family-projection/v1`` document that the existing reader accepts verbatim.

Inputs are payload-free ``stegverse.kv.email-ingress-receipt/v1`` receipts (``runtime/email_ingress_pipeline``),
``stegverse.kv.email-account-mapping/v1`` mappings (``runtime/email_continuity``), the prior email-family
projection, and a caller-supplied integer provider position per mailbox. Nothing here reads mail, contacts a
provider, resolves a SKAP reference, writes a file or grants authority. Every refusal is DENY or FAIL_CLOSED and
carries the six actionable fields (failure_code, failed_predicate, required_evidence_or_repair, retry_entrypoint,
owning_existing_goal, next_attempt). A produced projection is SOURCE/LOCAL evidence only, never runtime activation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from runtime.email_continuity import EmailMappingError, mapping_id_for
from runtime.workspace_projection import FORBIDDEN, METADATA_SCHEMA

SCHEMA = "stegverse.kv.email-family-projection/v1"
RECEIPT_SCHEMA = "stegverse.kv.email-ingress-receipt/v1"
MAPPING_SCHEMA = "stegverse.kv.email-account-mapping/v1"
OWNING_GOAL = "StegVerse-org/.github#164 (P2-workspace-cryptobot); coordination StegVerse-Labs/Site#1509"
RETRY_ENTRYPOINT = "runtime.email_family_projection.project_email_family"
RETRY_ENTRYPOINTS_TEXT = RETRY_ENTRYPOINT + " (local test: tests/test_email_family_projection.py)"

RECEIPT_KEYS = frozenset({
    "schema", "receipt_id", "mapping_id", "canonical_message_id", "staged_content_hash", "decision", "reason",
    "trusted_projection_created", "payload_retained_in_receipt", "authority_effect",
})
MAPPING_KEYS = frozenset({
    "schema", "mapping_id", "email_address", "provider_id", "provider_route", "mapping_state",
    "skap_credential_ref", "credential_secret_present_in_kv", "authority_effect",
})
# Contract keys whose names contain a forbidden word but whose values are references or booleans, never secrets.
_CONTRACT_KEYS = frozenset({"skap_credential_ref", "credential_secret_present_in_kv"})
FLAG_KEYS = ("credential_material_present", "provider_operation_authorized", "workspace_grants_authority")

REPAIRS = {
    "EMAIL_ADMIT_RECEIPT_ABSENT": "a complete stegverse.kv.email-ingress-receipt/v1 receipt for the message, as decide() emits it",
    "EMAIL_ADMIT_RECEIPT_STALE": "a receipt issued by the current ingress pipeline (stegverse.kv.email-ingress-receipt/v1, payload-free, authority NONE)",
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
    "EMAIL_PROVIDER_CURSOR_INVALID": "a non-negative integer provider position (opaque provider cursors are not supported by this producer)",
    "EMAIL_PROVIDER_CURSOR_ROLLBACK": "a provider position at or after the last accepted one (strictly after it when new receipts are projected)",
    "EMAIL_PROJECTION_ROLLBACK": "the last accepted email-family projection as prior; an older or absent prior never replaces the accepted head",
    "EMAIL_PRIOR_PROJECTION_INVALID": "the prior email-family projection exactly as this producer emitted it",
    "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT": "the prior projection unaltered; its projection_digest and cursor chains must recompute",
    "EMAIL_PRIOR_ACCOUNT_UNMAPPED": "the mapping for every mailbox already present in the prior projection",
    "EMAIL_PROJECTION_CLOCK_INVALID": "a timezone-aware UTC clock",
    "EMAIL_INPUT_MALFORMED": "inputs in the shapes this producer documents (lists of receipt and mapping objects, a position map, a prior projection)",
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


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _scan_secrets(value: Any, path: str, allowed: frozenset[str] = frozenset()) -> None:
    if isinstance(value, list):
        for i, item in enumerate(value):
            _scan_secrets(item, f"{path}[{i}]", allowed)
    elif isinstance(value, dict):
        for key, item in value.items():
            low = str(key).lower()
            if key not in allowed and any(word in low for word in FORBIDDEN):
                raise _fail("EMAIL_SECRET_FIELD_PRESENT", "NO_SECRET_FIELDS", f"{path}.{key}")
            _scan_secrets(item, f"{path}.{key}", allowed)


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
    ref = mapping["skap_credential_ref"]
    if ref is not None and (not isinstance(ref, str) or not ref.startswith("skap://") or len(ref) <= len("skap://")):
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
    material = {k: receipt[k] for k in ("mapping_id", "canonical_message_id", "staged_content_hash", "decision", "reason")}
    if receipt["receipt_id"] != "kv-email-receipt:" + _sha(material):
        raise _fail("EMAIL_ADMIT_RECEIPT_DIGEST_DRIFT", "RECEIPT_ID_RECOMPUTES", str(receipt["receipt_id"]))
    if receipt["decision"] != "ADMIT" or receipt["trusted_projection_created"] is not True:
        raise _deny("EMAIL_MESSAGE_UNADMITTED", "MESSAGE_ADMITTED", f"{receipt['decision']}:{receipt['receipt_id']}")
    return receipt


def _body(accounts: list[dict[str, Any]], messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema": SCHEMA, "workspace_type": "PERSONAL", "accounts": accounts, "messages": messages}


def _chain(previous: str | None, receipt_id: str) -> str:
    return _sha({"previous": previous, "receipt_id": receipt_id})


def _validate_prior(prior: Any, mappings: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if prior is None:
        return {}, []
    if not isinstance(prior, dict) or prior.get("schema") != SCHEMA:
        raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION")
    _scan_secrets({k: v for k, v in prior.items() if k not in FLAG_KEYS}, "prior")
    accounts, messages = prior.get("accounts"), prior.get("messages")
    if not isinstance(accounts, list) or not isinstance(messages, list):
        raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION")
    if prior.get("projection_digest") != _sha(_body(accounts, messages)):
        raise _fail("EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT", "PRIOR_DIGEST_RECOMPUTES")
    by_mapping: dict[str, dict[str, Any]] = {}
    for account in accounts:
        mid = account.get("mapping_id") if isinstance(account, dict) else None
        if mid in by_mapping:
            raise _fail("EMAIL_PRIOR_PROJECTION_INVALID", "PRIOR_IS_EMAIL_FAMILY_PROJECTION", str(mid))
        if mid not in mappings:
            raise _fail("EMAIL_PRIOR_ACCOUNT_UNMAPPED", "PRIOR_ACCOUNTS_MAPPED", str(mid))
        by_mapping[mid] = account
    heads: dict[str, tuple[int, str | None]] = {mid: (0, None) for mid in by_mapping}
    for message in messages:
        mid = message.get("mapping_id") if isinstance(message, dict) else None
        if mid not in heads:
            raise _fail("EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT", "PRIOR_DIGEST_RECOMPUTES", str(mid))
        seq, head = heads[mid]
        if message.get("sequence") != seq + 1:
            raise _fail("EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT", "PRIOR_DIGEST_RECOMPUTES", str(mid))
        heads[mid] = (seq + 1, _chain(head, str(message.get("receipt_id"))))
    for mid, account in by_mapping.items():
        cursor = account.get("cursor") or {}
        seq, head = heads[mid]
        if cursor.get("sequence") != seq or cursor.get("chain_digest") != head:
            raise _fail("EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT", "PRIOR_DIGEST_RECOMPUTES", str(mid))
    return by_mapping, [dict(m) for m in messages]


def _position(value: Any, mid: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
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
    prior: dict[str, Any] | None = None,
    accepted_head_digest: str | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> dict[str, Any]:
    """Return ``{disposition: ALLOW, projection}`` or a six-field DENY / FAIL_CLOSED record. Pure; writes nothing."""
    try:
        return _project(list(receipts), list(mappings), provider_positions, prior, accepted_head_digest, clock)
    except _Refusal as refusal:
        return _refusal_record(refusal)
    except (TypeError, KeyError, AttributeError, ValueError) as exc:
        # Any input shape this producer does not recognise is refused, never projected and never raised past the caller.
        return _refusal_record(_fail("EMAIL_INPUT_MALFORMED", "INPUT_SHAPE_RECOGNISED", type(exc).__name__))


def _project(receipts, mappings_in, provider_positions, prior, accepted_head_digest, clock) -> dict[str, Any]:
    mappings: dict[str, dict[str, Any]] = {}
    for mapping in mappings_in:
        m = _validate_mapping(mapping)
        if m["mapping_id"] in mappings:
            raise _fail("EMAIL_MAPPING_INVALID", "MAPPING_IS_CONTRACT_OBJECT", m["mapping_id"])
        mappings[m["mapping_id"]] = m

    if accepted_head_digest is not None:
        presented = prior.get("projection_digest") if isinstance(prior, dict) else None
        if presented != accepted_head_digest:
            raise _deny("EMAIL_PROJECTION_ROLLBACK", "PRIOR_IS_ACCEPTED_HEAD", str(presented))
    prior_accounts, messages = _validate_prior(prior, mappings)
    by_message = {m["canonical_message_id"]: m for m in messages}

    if not isinstance(provider_positions, dict):
        raise _fail("EMAIL_PROVIDER_CURSOR_INVALID", "PROVIDER_CURSOR_IS_ORDERED_POSITION")
    for mid in provider_positions:
        if mid not in mappings:
            raise _deny("EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH", "PROVENANCE_BOUND_TO_SUPPLIED_MAPPING", str(mid))

    new_by_mapping: dict[str, list[dict[str, Any]]] = {}
    for raw in receipts:
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

    accounts: list[dict[str, Any]] = []
    for mid in sorted(set(prior_accounts) | set(new_by_mapping)):
        mapping = mappings[mid]
        old = (prior_accounts.get(mid) or {}).get("cursor") or {"sequence": 0, "head_receipt_id": None, "chain_digest": None, "provider_position": None}
        old_pos = old.get("provider_position")
        fresh = new_by_mapping.get(mid, [])
        if mid in provider_positions:
            pos = _position(provider_positions[mid], mid)
        elif fresh:
            raise _fail("EMAIL_PROVIDER_CURSOR_ABSENT", "PROVIDER_CURSOR_PRESENT", mid)
        else:
            pos = old_pos
        if old_pos is not None and pos is not None and (pos < old_pos or (fresh and pos == old_pos)):
            raise _deny("EMAIL_PROVIDER_CURSOR_ROLLBACK", "PROVIDER_CURSOR_ADVANCES", mid)
        seq, head, head_id = old["sequence"], old["chain_digest"], old["head_receipt_id"]
        for row in fresh:
            seq += 1
            head = _chain(head, row["receipt_id"])
            head_id = row["receipt_id"]
            row["sequence"] = seq
            messages.append(row)
        ref = mapping["skap_credential_ref"]
        accounts.append({
            "mapping_id": mid,
            "provider_id": mapping["provider_id"],
            "mapping_state": mapping["mapping_state"],
            "skap_ref": ref,
            "cursor": {"sequence": seq, "head_receipt_id": head_id, "chain_digest": head, "provider_position": pos},
        })

    produced = clock()
    if not isinstance(produced, datetime) or produced.tzinfo is None:
        raise _fail("EMAIL_PROJECTION_CLOCK_INVALID", "PROJECTION_CLOCK_TIMEZONE_AWARE")
    body = _body(accounts, messages)
    digest = _sha(body)
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
            "source_revision": digest,
            "provenance_ref": "kv-email-ingress-admit-receipts:sha256:" + digest,
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
