"""Shared plumbing for the three node-receipt producers (LC-KV-13 inputs).

The three producers are node_existence_readback, node_identity_binding_producer
and node_health_check_projection. This module holds what they share:

* six-field non-ALLOW results;
* reading this repository's chain (HEAD.json to genesis, every receipt
  hash-verified) through healthy_node_evaluator.read_chain;
* the heartbeat epoch a new receipt is ordered by, taken from the chain itself
  (the HEAD receipt's epoch, or the declared anchor epoch for an empty ledger),
  so no clock is sampled;
* the single append path through this repository's own emitter, refusing a
  ledger root other than the one that was read.

Everything except `append` is deterministic. It reads files only, with no clock,
network or randomness.
"""
from __future__ import annotations

import base64
import binascii
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Mapping

from llm_adapter import healthy_node_evaluator as hne

ALLOW = hne.ALLOW
FAIL_CLOSED = hne.FAIL_CLOSED
REPOSITORY = hne.REPOSITORY
OWNING_GOAL = hne.OWNING_GOAL
ROOT = Path(__file__).resolve().parents[1]

EXISTENCE_CLASS = "AUTHENTICATED_RECIPROCAL_NODE_EXISTENCE"
BINDING_CLASS = "NODE_IDENTITY_BINDING"
HEALTH_CHECK_CLASS = "NODE_HEALTH_CHECK_OBSERVED"
HEALTH_CHECK_SCHEMA = "stegverse.node-health-check/v1"

#: Field names that would mean private key material reached this boundary.
CREDENTIAL_FIELD_NAMES = frozenset({"private_key", "private_key_b64", "secret_key", "signing_key", "seed",
                                    "secret", "key_seed", "private_key_pem"})

#: The ledger location these producers would write in production. Its onboarding
#: is a separate draft; until it is admitted the producers are exercised on
#: temporary ledgers only.
LEDGER_LOCATION = "refs/stegverse/organization-ledger:repository-ledger/StegVerse-org/LLM-adapter"

LEDGER_REASONS: dict[str, tuple[str, str]] = {
    "LEDGER_HEAD_UNREADABLE": ("CHAIN_READ_BACK", "a readable HEAD.json on this repository's ledger"),
    "RECEIPT_MISSING_ON_CHAIN": ("CHAIN_READ_BACK", "every receipt named by the chain must be present"),
    "RECEIPT_HASH_MISMATCH": ("CHAIN_READ_BACK", "every receipt on the chain must hash to its address"),
    "RECEIPT_REPOSITORY_MISMATCH": ("CHAIN_READ_BACK", "every receipt must belong to this repository"),
    "CHAIN_CYCLE": ("CHAIN_READ_BACK", "a chain from HEAD.json to genesis without cycles"),
    "LEDGER_ROOT_MISMATCH": ("CHAIN_READ_BACK", "produce() must append to the same ledger root it read"),
}


def non_allow(*, schema: str, failure_code: str, reasons: Mapping[str, tuple[str, str]], reason: str,
              detail: str, retry_entrypoint: str, next_attempt: str, node_id: Any = None,
              **extra: Any) -> dict[str, Any]:
    predicate, repair = {**LEDGER_REASONS, **reasons}[reason]
    return {
        "schema": schema,
        "disposition": FAIL_CLOSED,
        "node_id": node_id if isinstance(node_id, str) else None,
        "reason": reason,
        "detail": detail,
        "receipt_emitted": False,
        "failure_code": failure_code,
        "failed_predicate": predicate,
        "required_evidence_or_repair": repair,
        "retry_entrypoint": retry_entrypoint,
        "owning_existing_goal": OWNING_GOAL,
        "next_attempt": next_attempt,
        "authority_effect": "NONE",
        **extra,
    }


def read_chain(ledger_root: Any, repository: str = REPOSITORY, *, allow_empty: bool = False):
    """(chain newest first, failure reason, detail). An absent ledger is empty only if allow_empty."""
    root = Path(ledger_root) if ledger_root is not None else None
    if (allow_empty and root is not None and not (root / "HEAD.json").exists()
            and not any((root / "receipts").glob("*.json"))):
        return [], None, ""
    return hne.read_chain(root, repository)


def evidence(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    value = receipt.get("evidence")
    return value if isinstance(value, Mapping) else {}


def chain_epoch(chain: list[dict[str, Any]]) -> int | None:
    """The epoch a new receipt is ordered by: HEAD's epoch, or the declared anchor for an empty chain."""
    if chain:
        ref = chain[0].get("hb_reference")
        epoch = ref.get("epoch") if isinstance(ref, Mapping) else None
        return epoch if isinstance(epoch, int) and not isinstance(epoch, bool) else None
    declared = json.loads((ROOT / ".stegverse/heartbeat-awareness.json").read_text(encoding="utf-8"))["heartbeat"]
    return int(declared["anchor_epoch"])


def b64(value: Any) -> bytes | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None


#: node_identity_key public-key reference rule, mirrored from StegOS stegos/universal_intr_public_profile.py
#: (StegVerse-Labs/StegOS laneb/node-identity-key-reference). REQUIRED for KV standing, which is every node this
#: repository admits through POST /api/node-standing.
NODE_IDENTITY_KEY_FIELDS = frozenset({"algorithm", "key_id", "node_id", "public_key_b64", "custody"})
KV_STANDING = "KV_STANDING"
_NODE_ID = re.compile(r"^SV-NODE-[0-9A-Za-z]{8,64}$")
_KEY_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def node_identity_key_failure(key: Any) -> str | None:
    """Why `key` is not a well-formed public-key reference (StegOS predicate names), or None."""
    if not isinstance(key, Mapping):
        return "node_identity_key_object_required"
    if set(key) != NODE_IDENTITY_KEY_FIELDS:
        return "node_identity_key_fields_invalid"
    if key.get("algorithm") != "Ed25519":
        return "node_identity_key_algorithm_invalid"
    if not isinstance(key.get("key_id"), str) or not _KEY_ID.match(key["key_id"]):
        return "node_identity_key_key_id_invalid"
    if not isinstance(key.get("node_id"), str) or not _NODE_ID.match(key["node_id"]):
        return "node_identity_key_node_id_invalid"
    if key.get("custody") != "TV/TVC":
        return "node_identity_key_custody_invalid"
    public = b64(key.get("public_key_b64"))
    if public is None or len(public) != 32:
        return "node_identity_key_public_key_invalid"
    return None


def credential_fields(value: Any, path: str = "$") -> list[str]:
    """Paths of any field whose name says it carries private key material."""
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.lower() in CREDENTIAL_FIELD_NAMES:
                found.append(f"{path}.{key}")
            found.extend(credential_fields(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            found.extend(credential_fields(item, f"{path}[{i}]"))
    return found


def signed_message(domain: str, body: Mapping[str, Any]) -> bytes:
    """The exact bytes a node signs: the domain line, then the canonical body."""
    return domain.encode("utf-8") + b"\n" + hne.canon(dict(body))


def _emitter():
    spec = importlib.util.spec_from_file_location("repo_transition_emit_for_node_receipts",
                                                  ROOT / ".stegverse/transition-ledger/emit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append(planned: Mapping[str, Any], transition_class: str, ledger_root: Any) -> dict[str, Any] | None:
    """Append a planned receipt through the repository emitter; None when the roots differ."""
    emit = _emitter()
    if Path(ledger_root).expanduser().resolve() != emit.lr():
        return None
    return emit.append(planned["transition_id"], transition_class, planned["predecessor_state_sha256"],
                       planned["successor_state_sha256"], planned["receipt_evidence"], "NONE",
                       hb_epoch=planned["hb_epoch"])


def produce(planned: dict[str, Any], transition_class: str, ledger_root: Any, mismatch) -> dict[str, Any]:
    if planned["disposition"] != ALLOW:
        return planned
    if planned.get("already_current_receipt_sha256"):
        return {**planned, "outcome": "NOOP_ALREADY_CURRENT", "receipt_emitted": False,
                "receipt_sha256": planned["already_current_receipt_sha256"]}
    receipt = append(planned, transition_class, ledger_root)
    if receipt is None:
        return mismatch()
    return {**planned, "outcome": "EMITTED", "receipt_emitted": True, "receipt_sha256": receipt["receipt_sha256"]}
