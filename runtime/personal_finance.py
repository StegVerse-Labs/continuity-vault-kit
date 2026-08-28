"""Personal KnowledgeVault finance helpers.

This module normalizes user-controlled finance snapshots without creating payment,
trading, transfer, borrowing, or provider authority. It intentionally rejects
secret-bearing fields from ordinary KV finance content.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict

SCHEMA_VERSION = "stegverse.kv.personal-finance/v1"

FORBIDDEN_KEY_FRAGMENTS = {
    "password",
    "passcode",
    "pin",
    "cvv",
    "cvc",
    "card_number",
    "pan",
    "account_number",
    "routing_number",
    "private_key",
    "recovery_code",
    "refresh_token",
    "access_token",
    "oauth_token",
    "api_key",
    "secret",
}

SAFE_TOP_LEVEL_ARRAYS = (
    "accounts",
    "liabilities",
    "transactions",
    "recurring_activity",
    "rewards",
    "collateral_relationships",
    "provenance",
)


class PersonalFinanceError(ValueError):
    """Raised when a finance payload violates the bounded KV contract."""


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def reject_secret_fields(value: Any, path: str = "$") -> None:
    """Fail closed when an ordinary KV payload contains a secret-bearing field."""

    if isinstance(value, dict):
        for key, child in value.items():
            normalized = _normalized_key(str(key))
            if any(fragment == normalized or fragment in normalized for fragment in FORBIDDEN_KEY_FRAGMENTS):
                raise PersonalFinanceError(f"forbidden secret-bearing field at {path}.{key}")
            reject_secret_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_secret_fields(child, f"{path}[{index}]")


def deterministic_id(namespace: str, *parts: Any) -> str:
    """Create a stable non-secret identifier from already-bounded reference metadata."""

    material = "|".join("" if part is None else str(part).strip().lower() for part in parts)
    digest = hashlib.sha256(f"{namespace}|{material}".encode("utf-8")).hexdigest()[:24]
    return f"kvfin_{namespace}_{digest}"


def _ensure_account_ids(snapshot: Dict[str, Any]) -> None:
    for account in snapshot["accounts"]:
        if not account.get("account_id"):
            source = account.get("source") or {}
            account["account_id"] = deterministic_id(
                "acct",
                source.get("provider_name"),
                source.get("external_reference"),
                account.get("display_name"),
                account.get("mask"),
            )


def canonical_snapshot_hash(snapshot: Dict[str, Any]) -> str:
    """Hash canonical finance state without including the hash field itself."""

    material = copy.deepcopy(snapshot)
    material["snapshot_hash"] = None
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Personal KV finance snapshot and compute its integrity hash."""

    if not isinstance(payload, dict):
        raise PersonalFinanceError("finance snapshot must be an object")

    reject_secret_fields(payload)
    snapshot = copy.deepcopy(payload)

    schema_version = snapshot.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise PersonalFinanceError(f"unsupported schema_version: {schema_version}")
    snapshot["schema_version"] = SCHEMA_VERSION

    for field in SAFE_TOP_LEVEL_ARRAYS:
        value = snapshot.setdefault(field, [])
        if not isinstance(value, list):
            raise PersonalFinanceError(f"{field} must be a list")

    if snapshot.get("execution_authority") not in (None, False):
        raise PersonalFinanceError("finance snapshot cannot grant execution authority")
    snapshot["execution_authority"] = False
    snapshot.setdefault("updated_at", None)

    _ensure_account_ids(snapshot)
    snapshot["snapshot_hash"] = canonical_snapshot_hash(snapshot)
    return snapshot


def assert_read_only_finance_contract(snapshot: Dict[str, Any]) -> None:
    """Re-check the most important authority and credential invariants."""

    reject_secret_fields(snapshot)
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise PersonalFinanceError("unexpected finance schema version")
    if snapshot.get("execution_authority") is not False:
        raise PersonalFinanceError("execution_authority must remain false")
    for field in SAFE_TOP_LEVEL_ARRAYS:
        if not isinstance(snapshot.get(field), list):
            raise PersonalFinanceError(f"{field} must be a list")
