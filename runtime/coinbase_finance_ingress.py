"""Coinbase direct-source finance normalization.

This adapter consumes a non-secret, already-authenticated Coinbase read result from
an existing TVC/SKAP provider-session boundary. It does not perform login, token
exchange, provider mutation, trading, transfer, withdrawal, or account management.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from runtime.personal_finance import (
    PersonalFinanceError,
    deterministic_id,
    normalize_snapshot,
    reject_secret_fields,
)

PROVIDER_NAME = "Coinbase"


class CoinbaseFinanceIngressError(PersonalFinanceError):
    pass


def _require_verified(result: Dict[str, Any]) -> None:
    if not isinstance(result, dict):
        raise CoinbaseFinanceIngressError("Coinbase provider result must be an object")
    reject_secret_fields(result, "$.coinbase_result")
    if result.get("provider") != "coinbase":
        raise CoinbaseFinanceIngressError("FAIL_CLOSED: Coinbase direct source required")
    if result.get("direct_source_verified") is not True:
        raise CoinbaseFinanceIngressError("FAIL_CLOSED: direct source verification required")
    if result.get("session_verified") is not True:
        raise CoinbaseFinanceIngressError("FAIL_CLOSED: provider session verification required")
    if not result.get("retrieved_at"):
        raise CoinbaseFinanceIngressError("FAIL_CLOSED: retrieval timestamp required")
    if result.get("access") not in (None, "READ_ONLY"):
        raise CoinbaseFinanceIngressError("FAIL_CLOSED: Coinbase finance ingress is read-only")
    if result.get("provider_operation_authorized") not in (None, False):
        raise CoinbaseFinanceIngressError("FAIL_CLOSED: provider operation authority prohibited")


def _map_accounts(rows: Iterable[Dict[str, Any]], retrieved_at: str) -> list[Dict[str, Any]]:
    mapped = []
    for row in rows or []:
        reject_secret_fields(row, "$.coinbase_result.accounts[]")
        source_ref = str(row.get("source_ref") or "").strip()
        if not source_ref:
            raise CoinbaseFinanceIngressError("Coinbase account source_ref required")
        display_name = str(row.get("display_name") or row.get("asset") or "Coinbase account").strip()
        account_type = row.get("account_type") or "crypto"
        mapped.append({
            "account_id": deterministic_id("acct", PROVIDER_NAME, source_ref, display_name, row.get("mask")),
            "display_name": display_name,
            "account_type": account_type,
            "subtype": row.get("subtype"),
            "mask": row.get("mask"),
            "currency": row.get("currency") or row.get("asset"),
            "current_balance": row.get("current_balance"),
            "available_balance": row.get("available_balance"),
            "credit_limit": row.get("credit_limit"),
            "as_of": row.get("as_of") or retrieved_at,
            "source": {
                "provider_name": PROVIDER_NAME,
                "external_reference": source_ref,
                "source_type": "DIRECT_PROVIDER",
            },
            "notes": row.get("notes"),
        })
    return mapped


def _map_transactions(rows: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    mapped = []
    for row in rows or []:
        reject_secret_fields(row, "$.coinbase_result.transactions[]")
        source_ref = str(row.get("source_ref") or "").strip()
        if not source_ref:
            raise CoinbaseFinanceIngressError("Coinbase transaction source_ref required")
        mapped.append({
            "transaction_id": deterministic_id("txn", PROVIDER_NAME, source_ref),
            "account_id": row.get("account_id"),
            "posted_at": row.get("posted_at"),
            "description": row.get("description"),
            "amount": row.get("amount"),
            "currency": row.get("currency"),
            "category": row.get("category"),
            "pending": bool(row.get("pending", False)),
            "source": {
                "provider_name": PROVIDER_NAME,
                "external_reference": source_ref,
                "source_type": "DIRECT_PROVIDER",
            },
        })
    return mapped


def _map_rewards(rows: Iterable[Dict[str, Any]], retrieved_at: str) -> list[Dict[str, Any]]:
    mapped = []
    for row in rows or []:
        reject_secret_fields(row, "$.coinbase_result.rewards[]")
        reward_ref = str(row.get("source_ref") or "").strip()
        if not reward_ref:
            raise CoinbaseFinanceIngressError("Coinbase reward source_ref required")
        mapped.append({
            "reward_id": deterministic_id("reward", PROVIDER_NAME, reward_ref),
            "account_id": row.get("account_id"),
            "reward_type": row.get("reward_type") or "other",
            "asset": row.get("asset"),
            "rate": row.get("rate"),
            "rate_unit": row.get("rate_unit"),
            "earned_amount": row.get("earned_amount"),
            "earned_asset": row.get("earned_asset"),
            "as_of": row.get("as_of") or retrieved_at,
            "source": {
                "provider_name": PROVIDER_NAME,
                "external_reference": reward_ref,
                "source_type": "DIRECT_PROVIDER",
            },
            "notes": row.get("notes"),
        })
    return mapped


def _map_collateral(rows: Iterable[Dict[str, Any]], retrieved_at: str) -> list[Dict[str, Any]]:
    mapped = []
    for row in rows or []:
        reject_secret_fields(row, "$.coinbase_result.collateral[]")
        source_ref = str(row.get("source_ref") or "").strip()
        if not source_ref:
            raise CoinbaseFinanceIngressError("Coinbase collateral source_ref required")
        mapped.append({
            "relationship_id": deterministic_id("collateral", PROVIDER_NAME, source_ref),
            "collateral_account_id": row.get("collateral_account_id"),
            "secured_account_id": row.get("secured_account_id"),
            "asset": row.get("asset"),
            "locked_amount": row.get("locked_amount"),
            "purpose": row.get("purpose"),
            "as_of": row.get("as_of") or retrieved_at,
            "source": {
                "provider_name": PROVIDER_NAME,
                "external_reference": source_ref,
                "source_type": "DIRECT_PROVIDER",
            },
        })
    return mapped


def normalize_coinbase_finance_result(provider_result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize verified, non-secret Coinbase read data into Personal Finance."""

    _require_verified(provider_result)
    retrieved_at = provider_result["retrieved_at"]

    snapshot = {
        "schema_version": "stegverse.kv.personal-finance/v1",
        "updated_at": retrieved_at,
        "accounts": _map_accounts(provider_result.get("accounts", []), retrieved_at),
        "liabilities": [],
        "transactions": _map_transactions(provider_result.get("transactions", [])),
        "recurring_activity": [],
        "rewards": _map_rewards(provider_result.get("rewards", []), retrieved_at),
        "collateral_relationships": _map_collateral(provider_result.get("collateral", []), retrieved_at),
        "provenance": [{
            "provider_name": PROVIDER_NAME,
            "source_type": "DIRECT_PROVIDER",
            "retrieved_at": retrieved_at,
            "coverage_start": provider_result.get("coverage_start"),
            "coverage_end": provider_result.get("coverage_end"),
            "adapter_version": provider_result.get("adapter_version") or "coinbase-finance-ingress/v1",
            "session_evidence_ref": provider_result.get("session_evidence_ref"),
            "direct_source_verified": True,
            "intermediary_used": bool(provider_result.get("intermediary_used", False)),
        }],
        "execution_authority": False,
    }
    return normalize_snapshot(snapshot)
