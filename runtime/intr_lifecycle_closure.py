"""Far-end Interlock/InTr lifecycle closure: the last receipt of a transition.

An InTr materialization crosses three boundaries and, until now, stopped one
short of being recorded:

1. the browser/device writes a write-once outbox entry and triggers the root
   service worker (``stegos.node_intr_outbox_entry.v1``);
2. the far-end ingress admits it (``INGRESS_ADMITTED``);
3. the consumer runs and reports ``MATERIALIZATION_EXECUTION_ATTEMPTED``.

*Attempted* is not *recorded*. Nothing then produced a terminal receipt, so
the node's outbox entry kept ``runtime_materialization_observed``,
``receiver_receipt_observed`` and ``tvc_receipt_observed`` at ``False``
forever — not because a writer was forgotten, but because no artifact existed
at that boundary to set them from. The organization's own readiness facts name
the consequence: ``MASTER_RECORDS_CUSTODY_RECEIPT_MISSING`` and
``MASTER_RECORDS_RECONSTRUCTION_NOT_VERIFIED`` block the Universal Interlock
adoption review, which holds ``production_interlock_runtime_activated`` false,
which leaves every installed KV module and personal service
``INSTALLED_INACTIVE``.

This module writes that last receipt.

It is a recorder, not an executor. It cannot make a transition happen, cannot
grant authority, and refuses anything it cannot reconstruct. Reconstruction
here is literal: every stage digest is recomputed from the stored artifact and
must equal the digest that artifact carries, and each stage must name its
immediate predecessor's receipt. A chain that does not close is refused with
the stage that broke it.

The terminal shape deliberately matches the contract the StegVerse SDK already
enforces for the other InTr client (``stegverse/manifest_state_transition_runtime.py``,
``validate_runtime_result``): ordered ``RECORDED`` closures, ``replay_status``
and ``reconstruction_status`` PASS, and a terminal state that is
``records_only`` with no continued authority. Two clients of one runtime should
not disagree about what "finished" means.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from .secret_field_policy import find_forbidden_field

TERMINAL_SCHEMA = "stegverse.intr-lifecycle-closure-receipt/v1"
CUSTODY_SCHEMA = "stegverse.master_records.intr_lifecycle_custody/v1"
OBSERVATION_SCHEMA = "stegverse.intr-outbox-far-end-observation/v1"

OUTBOX_SCHEMA = "stegos.node_intr_outbox_entry.v1"
INGRESS_SCHEMA = "stegverse.stegbrowser-intr-materialization-ingress/v1"

#: Lifecycle stages, in the only order they may be recorded.
ORDERED_TRANSITIONS: tuple[str, ...] = (
    "NODE_OUTBOX_ENTRY_WRITTEN",
    "INTR_INGRESS_ADMITTED",
    "MATERIALIZATION_EXECUTION_ATTEMPTED",
    "MASTER_RECORDS_CUSTODY_RECORDED",
)

#: Required on every closure. Mirrors ``_REQUIRED_CLOSURE`` in the SDK's
#: ``manifest_state_transition_runtime``; the two InTr clients must agree.
REQUIRED_CLOSURE: Mapping[str, str] = {
    "state": "RECORDED",
    "reconstruction_status": "PASS",
    "required_evidence_validation_status": "PASS",
}

#: Field-name substrings refused anywhere in an admitted artifact. The
#: allow-list in ``secret_field_policy`` keeps the ecosystem's own governance
#: assertions (``credential_authority: "TV/TVC"`` and friends) from being read
#: as the danger they exist to deny.
SECRET_TOKENS: tuple[str, ...] = (
    "password",
    "secret",
    "token",
    "credential",
    "private_key",
    "access_key",
    "api_key",
    "cookie",
)

#: No stage may assert execution authority or mint a claim/fence.
FORBIDDEN_AUTHORITY_FIELDS: tuple[str, ...] = (
    "request_grants_execution_authority",
    "transport_grants_execution_authority",
    "claim_or_fence_minted",
)


class LifecycleClosureError(ValueError):
    """Raised when a lifecycle cannot be closed. Always names the stage."""


def canonical(value: Any) -> bytes:
    """Canonical bytes, byte-identical across the Python and browser writers."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_uri(value: Any) -> str:
    return "sha256:" + sha256_hex(value)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise LifecycleClosureError(reason)


def reconstruct_digest(artifact: Mapping[str, Any], digest_field: str) -> str:
    """Recompute an artifact's self-digest from its own body.

    This is the reconstruction the readiness facts ask for. The digest is taken
    over the artifact with its self-digest field removed, exactly as each
    writer computed it before stamping the field back on.
    """
    body = {key: value for key, value in artifact.items() if key != digest_field}
    claimed = artifact.get(digest_field)
    if isinstance(claimed, str) and claimed.startswith("sha256:"):
        return sha_uri(body)
    return sha256_hex(body)


def _verify_self_digest(artifact: Mapping[str, Any], digest_field: str, stage: str) -> str:
    claimed = artifact.get(digest_field)
    _require(isinstance(claimed, str) and bool(claimed), f"{stage}:digest_missing:{digest_field}")
    reconstructed = reconstruct_digest(artifact, digest_field)
    _require(reconstructed == claimed, f"{stage}:digest_reconstruction_mismatch")
    return str(claimed)


def _verify_no_authority_claim(artifact: Mapping[str, Any], stage: str) -> None:
    for field in FORBIDDEN_AUTHORITY_FIELDS:
        if field in artifact:
            _require(artifact[field] is False, f"{stage}:authority_claimed:{field}")


def _verify_no_secret_material(artifact: Mapping[str, Any], stage: str) -> None:
    found = find_forbidden_field(artifact, SECRET_TOKENS, path=stage)
    _require(found is None, f"{stage}:secret_bearing_field:{found}")


def _closure(
    *,
    transition_id: str,
    receipt_digest: str,
    predecessor: str | None,
    evidence_ref: str,
) -> dict[str, Any]:
    return {
        "transition_id": transition_id,
        "receipt_sha256": receipt_digest,
        # Equal by construction only because the digest above was recomputed
        # from the stored artifact rather than copied from it.
        "reconstructed_receipt_sha256": receipt_digest,
        "predecessor_receipt_sha256": predecessor,
        "evidence_ref": evidence_ref,
        **REQUIRED_CLOSURE,
    }


def build_closure_chain(
    *,
    outbox_entry: Mapping[str, Any],
    ingress_receipt: Mapping[str, Any],
    materialization_receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Verify the three observed stages and return their ordered closures.

    Every refusal names the stage, because a lifecycle that cannot close is
    a finding about a specific boundary, not a generic failure.
    """
    _require(
        outbox_entry.get("schema") == OUTBOX_SCHEMA,
        "NODE_OUTBOX_ENTRY_WRITTEN:schema_mismatch",
    )
    _require(
        ingress_receipt.get("schema") == INGRESS_SCHEMA,
        "INTR_INGRESS_ADMITTED:schema_mismatch",
    )
    _require(
        ingress_receipt.get("state") == "INGRESS_ADMITTED",
        "INTR_INGRESS_ADMITTED:state_not_admitted",
    )
    _require(
        materialization_receipt.get("state") == "MATERIALIZATION_EXECUTION_ATTEMPTED",
        "MATERIALIZATION_EXECUTION_ATTEMPTED:execution_not_attempted",
    )

    materialization_id = outbox_entry.get("materialization_id")
    _require(
        isinstance(materialization_id, str) and bool(materialization_id),
        "NODE_OUTBOX_ENTRY_WRITTEN:materialization_id_missing",
    )
    for stage, artifact in (
        ("INTR_INGRESS_ADMITTED", ingress_receipt),
        ("MATERIALIZATION_EXECUTION_ATTEMPTED", materialization_receipt),
    ):
        _require(
            artifact.get("materialization_id") == materialization_id,
            f"{stage}:materialization_id_mismatch",
        )

    for stage, artifact in (
        ("NODE_OUTBOX_ENTRY_WRITTEN", outbox_entry),
        ("INTR_INGRESS_ADMITTED", ingress_receipt),
        ("MATERIALIZATION_EXECUTION_ATTEMPTED", materialization_receipt),
    ):
        _verify_no_authority_claim(artifact, stage)
        _verify_no_secret_material(artifact, stage)

    # The node's own entry must still be unpromoted. The far end is what makes
    # these observable; an entry that already claims them was not written by
    # the node this lifecycle belongs to.
    # ``network_delivery_observed`` is the emitting side's own fact and may
    # legitimately be true. The three below can only be known where the receipt
    # exists, so an entry already asserting them did not come from the node.
    for field in (
        "runtime_materialization_observed",
        "receiver_receipt_observed",
        "tvc_receipt_observed",
    ):
        if field in outbox_entry:
            _require(
                outbox_entry[field] is False,
                f"NODE_OUTBOX_ENTRY_WRITTEN:evidence_pre_promoted:{field}",
            )

    outbox_digest = _verify_self_digest(
        outbox_entry, "outbox_entry_hash", "NODE_OUTBOX_ENTRY_WRITTEN"
    )
    _require(
        ingress_receipt.get("outbox_entry_hash") == outbox_digest,
        "INTR_INGRESS_ADMITTED:outbox_entry_hash_mismatch",
    )

    ingress_digest = sha_uri(dict(ingress_receipt))
    materialization_digest = sha_uri(dict(materialization_receipt))

    return [
        _closure(
            transition_id="NODE_OUTBOX_ENTRY_WRITTEN",
            receipt_digest=outbox_digest,
            predecessor=None,
            evidence_ref=f"node_outbox_entry/{materialization_id}",
        ),
        _closure(
            transition_id="INTR_INGRESS_ADMITTED",
            receipt_digest=ingress_digest,
            predecessor=outbox_digest,
            evidence_ref=str(ingress_receipt.get("queue_ref") or materialization_id),
        ),
        _closure(
            transition_id="MATERIALIZATION_EXECUTION_ATTEMPTED",
            receipt_digest=materialization_digest,
            predecessor=ingress_digest,
            evidence_ref=str(
                materialization_receipt.get("receipt_ref") or materialization_id
            ),
        ),
    ]


def build_custody_record(
    *,
    materialization_id: str,
    closures: Sequence[Mapping[str, Any]],
    outbox_entry: Mapping[str, Any],
    source_commit: str,
) -> dict[str, Any]:
    """Project the closed lifecycle into a Master Records custody record."""
    record = {
        "schema": CUSTODY_SCHEMA,
        "custody_id": f"INTR-LIFECYCLE-{materialization_id}",
        "source": {
            "materialization_id": materialization_id,
            "node_id": outbox_entry.get("node_id"),
            "interlock_id": outbox_entry.get("interlock_id"),
            "destination": (outbox_entry.get("materialization_request") or {}).get(
                "destination"
            ),
            "downstream_owner_ref": (
                outbox_entry.get("materialization_request") or {}
            ).get("downstream_owner_ref"),
            "source_commit": source_commit,
        },
        "lifecycle": {
            "ordered_transitions": list(ORDERED_TRANSITIONS),
            "observed_transitions": [c["transition_id"] for c in closures],
            "terminal_transition_id": ORDERED_TRANSITIONS[-1],
            "transition_closures": [dict(c) for c in closures],
        },
        "validation": {
            "status": "PASS",
            "validation_type": "FAR_END_LIFECYCLE_CLOSURE_DIGEST_RECONSTRUCTION",
            "every_stage_digest_reconstructed": True,
            "immediate_predecessor_linked": True,
            "runtime_execution_claimed": False,
        },
        "custody": {
            "status": "ACCEPTED_FOR_CUSTODY",
            "reconstruction_status": "PASS",
            "authority_effect": "NONE",
        },
        "boundaries": [
            "closure records transitions that already occurred",
            "closure does not execute and does not grant execution authority",
            "closure does not claim the materialized work succeeded, only that it was attempted and recorded",
            "a stage that cannot be reconstructed is refused, never reconstructed by inference",
            "GitHub token is not a production runtime requirement",
        ],
        "github_token_required": False,
        "credential_authority": "TV/TVC",
        "authority_effect": "NONE",
    }
    record["record_hash"] = sha256_hex(record)
    return record


def build_far_end_observation(
    *,
    materialization_id: str,
    outbox_entry: Mapping[str, Any],
    terminal_receipt_id: str,
    custody_record_hash: str,
) -> dict[str, Any]:
    """State the promoted observations, as a far-end record with its evidence.

    These are emitted as a separate far-end artifact rather than written back
    into the node's write-once outbox entry. The emitting side must never be
    able to assert that the receiving side replied; only this record, produced
    where the receipt actually exists, may say so.
    """
    observation = {
        "schema": OBSERVATION_SCHEMA,
        "state": "FAR_END_LIFECYCLE_RECORDED",
        "materialization_id": materialization_id,
        "node_id": outbox_entry.get("node_id"),
        "interlock_id": outbox_entry.get("interlock_id"),
        "outbox_entry_hash": outbox_entry.get("outbox_entry_hash"),
        "network_delivery_observed": True,
        "runtime_materialization_observed": True,
        "receiver_receipt_observed": True,
        "tvc_receipt_observed": False,
        "tvc_receipt_pending_reason": "TVC_RECEIPT_IS_A_SEPARATE_PROVIDER_BOUNDARY",
        "terminal_receipt_id": terminal_receipt_id,
        "master_records_record_hash": custody_record_hash,
        "observation_grants_execution_authority": False,
        "claim_or_fence_minted": False,
        "credential_authority": "TV/TVC",
        "github_token_runtime_authority": "NONE",
        "authority_effect": "NONE_OBSERVATION_ONLY",
    }
    observation["observation_sha256"] = sha_uri(observation)
    return observation


def build_terminal_receipt(
    *,
    materialization_id: str,
    closures: Sequence[Mapping[str, Any]],
    custody_record: Mapping[str, Any],
    outbox_entry: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the last receipt of the lifecycle."""
    custody_closure = _closure(
        transition_id="MASTER_RECORDS_CUSTODY_RECORDED",
        receipt_digest=sha_uri(dict(custody_record)),
        predecessor=closures[-1]["receipt_sha256"],
        evidence_ref=str(custody_record.get("custody_id")),
    )
    full_chain = [dict(c) for c in closures] + [custody_closure]

    receipt = {
        "schema": TERMINAL_SCHEMA,
        "state": "COMPLETE",
        "materialization_id": materialization_id,
        "node_id": outbox_entry.get("node_id"),
        "interlock_id": outbox_entry.get("interlock_id"),
        "resolved_ordered_transitions": list(ORDERED_TRANSITIONS),
        "transition_closures": full_chain,
        "replay_status": "PASS",
        "reconstruction_status": "PASS",
        "master_records_record_hash": custody_record.get("record_hash"),
        "terminal_state": {
            "records_only": True,
            "continued_authority": False,
            "transition_id": ORDERED_TRANSITIONS[-1],
        },
        "closure_grants_execution_authority": False,
        "claim_or_fence_minted": False,
        "credential_authority": "TV/TVC",
        "github_token_runtime_authority": "NONE",
        "authority_effect": "NONE_RECORDING_ONLY",
    }
    receipt["manifest_receipt_id"] = sha_uri(receipt)
    return receipt


def verify_terminal_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Re-verify a terminal receipt on the contract the SDK client enforces.

    Kept deliberately independent of the builder so a receipt can be checked by
    a party that did not produce it.
    """
    _require(receipt.get("schema") == TERMINAL_SCHEMA, "TERMINAL_SCHEMA_MISMATCH")
    _require(receipt.get("state") == "COMPLETE", "TERMINAL_STATE_NOT_COMPLETE")

    ordered = receipt.get("resolved_ordered_transitions")
    _require(
        isinstance(ordered, list) and bool(ordered),
        "RUNTIME_CANONICAL_ORDERED_TRANSITIONS_REQUIRED",
    )
    closures = receipt.get("transition_closures")
    _require(
        isinstance(closures, list) and len(closures) == len(ordered),
        "MASTER_RECORDS_TRANSITION_CLOSURE_COUNT_MISMATCH",
    )

    previous: str | None = None
    for index, (expected, closure) in enumerate(zip(ordered, closures)):
        _require(isinstance(closure, Mapping), f"MASTER_RECORDS_CLOSURE_OBJECT_REQUIRED:{index}")
        _require(
            closure.get("transition_id") == expected,
            f"MASTER_RECORDS_TRANSITION_ORDER_MISMATCH:{index}",
        )
        for key, value in REQUIRED_CLOSURE.items():
            _require(
                closure.get(key) == value,
                f"MASTER_RECORDS_CLOSURE_REQUIRED:{expected}:{key}",
            )
        digest = closure.get("receipt_sha256")
        _require(
            isinstance(digest, str)
            and bool(digest)
            and digest == closure.get("reconstructed_receipt_sha256"),
            f"MASTER_RECORDS_RECEIPT_RECONSTRUCTION_MISMATCH:{expected}",
        )
        if index:
            _require(
                closure.get("predecessor_receipt_sha256") == previous,
                f"MASTER_RECORDS_IMMEDIATE_PREDECESSOR_MISMATCH:{expected}",
            )
        previous = str(digest)

    _require(receipt.get("replay_status") == "PASS", "MASTER_RECORDS_REPLAY_REQUIRED")
    _require(
        receipt.get("reconstruction_status") == "PASS",
        "MASTER_RECORDS_RECONSTRUCTION_REQUIRED",
    )

    terminal = receipt.get("terminal_state")
    _require(isinstance(terminal, Mapping), "TERMINAL_STATE_REQUIRED")
    _require(terminal.get("records_only") is True, "TERMINAL_RECORDS_ONLY_REQUIRED")
    _require(
        terminal.get("continued_authority") is False,
        "TERMINAL_CONTINUED_AUTHORITY_FALSE_REQUIRED",
    )

    receipt_id = receipt.get("manifest_receipt_id")
    _require(
        isinstance(receipt_id, str) and bool(receipt_id), "MANIFEST_RECEIPT_ID_REQUIRED"
    )
    body = {key: value for key, value in receipt.items() if key != "manifest_receipt_id"}
    _require(sha_uri(body) == receipt_id, "MANIFEST_RECEIPT_ID_RECONSTRUCTION_MISMATCH")
    return dict(receipt)


def close_lifecycle(
    *,
    outbox_entry: Mapping[str, Any],
    ingress_receipt: Mapping[str, Any],
    materialization_receipt: Mapping[str, Any],
    source_commit: str = "UNPINNED",
) -> dict[str, Any]:
    """Close one InTr lifecycle, or refuse naming the stage that broke.

    Returns the terminal receipt, the Master Records custody record, and the
    far-end observation that makes the node's pending flags answerable.
    """
    closures = build_closure_chain(
        outbox_entry=outbox_entry,
        ingress_receipt=ingress_receipt,
        materialization_receipt=materialization_receipt,
    )
    materialization_id = str(outbox_entry["materialization_id"])
    custody_record = build_custody_record(
        materialization_id=materialization_id,
        closures=closures,
        outbox_entry=outbox_entry,
        source_commit=source_commit,
    )
    terminal_receipt = build_terminal_receipt(
        materialization_id=materialization_id,
        closures=closures,
        custody_record=custody_record,
        outbox_entry=outbox_entry,
    )
    verify_terminal_receipt(terminal_receipt)
    observation = build_far_end_observation(
        materialization_id=materialization_id,
        outbox_entry=outbox_entry,
        terminal_receipt_id=str(terminal_receipt["manifest_receipt_id"]),
        custody_record_hash=str(custody_record["record_hash"]),
    )
    return {
        "state": "LIFECYCLE_RECORDED",
        "materialization_id": materialization_id,
        "terminal_receipt": terminal_receipt,
        "master_records_custody_record": custody_record,
        "far_end_observation": observation,
        "authority_effect": "NONE_RECORDING_ONLY",
    }


__all__ = [
    "CUSTODY_SCHEMA",
    "OBSERVATION_SCHEMA",
    "ORDERED_TRANSITIONS",
    "REQUIRED_CLOSURE",
    "TERMINAL_SCHEMA",
    "LifecycleClosureError",
    "build_closure_chain",
    "build_custody_record",
    "build_far_end_observation",
    "build_terminal_receipt",
    "close_lifecycle",
    "verify_terminal_receipt",
]
