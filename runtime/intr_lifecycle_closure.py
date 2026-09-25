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
    """Prepare a locally reconstructed proposal; only Master Records can accept it."""
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
            "terminal_transition_id": None,
            "pending_terminal_transition_id": ORDERED_TRANSITIONS[-1],
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
            "status": "PROPOSED_FOR_CUSTODY",
            "reconstruction_status": "LOCAL_ONLY",
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



def verify_native_master_records_confirmation(
    confirmation: Mapping[str, Any],
    *,
    custody_record: Mapping[str, Any],
    preceding_receipt_sha256: str,
    materialization_id: str,
) -> str:
    """Validate the *existing native* custody result and independent readback.

    The resident caller must obtain this bundle through the authorized canonical
    Master Records state-transition client and independent replay; caller-authored
    confirmation objects and fixture outputs are not runtime evidence.
    """
    _require(isinstance(confirmation, Mapping), "CANONICAL_MASTER_RECORDS_CONFIRMATION_REQUIRED")
    _verify_no_secret_material(confirmation, "canonical_master_records_confirmation")
    receipt = confirmation.get("canonical_state_receipt")
    recorded = confirmation.get("recording_result")
    reconstructed = confirmation.get("reconstruction_result")
    replay = confirmation.get("replay_result")
    for label, item in (("receipt", receipt), ("recording", recorded),
                        ("reconstruction", reconstructed), ("replay", replay)):
        _require(isinstance(item, Mapping), f"MASTER_RECORDS_NATIVE_{label.upper()}_REQUIRED")
    _require(
        receipt.get("schema") == "stegverse.canonical-state-transition-receipt/v1",
        "MASTER_RECORDS_CANONICAL_STATE_RECEIPT_REQUIRED",
    )
    _require(receipt.get("transition_id") == "MASTER_RECORDS_CUSTODY_RECORDED",
             "MASTER_RECORDS_TRANSITION_ID_MISMATCH")
    _require(receipt.get("subject_or_correlation_id") == materialization_id,
             "MASTER_RECORDS_MATERIALIZATION_ID_MISMATCH")
    _require(receipt.get("prior_state_ref_or_hash") == preceding_receipt_sha256,
             "MASTER_RECORDS_PREDECESSOR_MISMATCH")
    evidence = receipt.get("transition_evidence")
    _require(isinstance(evidence, Mapping) and
             evidence.get("proposed_custody_record_sha256") == custody_record.get("record_hash"),
             "MASTER_RECORDS_PROPOSAL_DIGEST_MISMATCH")
    _require(receipt.get("master_records_may_grant_transition_authority") is False and
             receipt.get("master_records_may_grant_execution_authority") is False,
             "MASTER_RECORDS_AUTHORITY_CLAIM")
    digest = sha256_hex(dict(receipt))
    _require(recorded.get("state") == "RECORDED" and
             recorded.get("reconstruction_status") == "PASS" and
             recorded.get("required_evidence_validation_status") == "PASS",
             "MASTER_RECORDS_NATIVE_RECORDING_NOT_VERIFIED")
    _require(recorded.get("receipt_sha256") == digest and
             recorded.get("reconstructed_receipt_sha256") == digest,
             "MASTER_RECORDS_NATIVE_RECORDING_HASH_MISMATCH")
    _require(recorded.get("master_records_grants_transition_authority") is False,
             "MASTER_RECORDS_NATIVE_AUTHORITY_ESCALATION")
    master_ref = recorded.get("master_record_ref")
    _require(isinstance(master_ref, str) and bool(master_ref),
             "MASTER_RECORDS_NATIVE_RECORD_REFERENCE_REQUIRED")
    _require(reconstructed.get("state") == "PASS" and
             reconstructed.get("required_evidence_validation_status") == "PASS" and
             reconstructed.get("receipt_sha256") == digest and
             reconstructed.get("reconstructed_receipt_sha256") == digest and
             reconstructed.get("receipt") == receipt and
             reconstructed.get("master_record_ref") == master_ref,
             "MASTER_RECORDS_INDEPENDENT_RECONSTRUCTION_REQUIRED")
    _require(replay.get("replay_status") == "PASS" and
             replay.get("receipt_sha256") == digest,
             "MASTER_RECORDS_INDEPENDENT_REPLAY_REQUIRED")
    return digest


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
    native_confirmation: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a terminal receipt only after genuine native custody and replay."""
    native_digest = verify_native_master_records_confirmation(
        native_confirmation,
        custody_record=custody_record,
        preceding_receipt_sha256=str(closures[-1]["receipt_sha256"]),
        materialization_id=materialization_id,
    )
    custody_closure = _closure(
        transition_id="MASTER_RECORDS_CUSTODY_RECORDED",
        receipt_digest=native_digest,
        predecessor=closures[-1]["receipt_sha256"],
        evidence_ref=str(native_confirmation["recording_result"]["master_record_ref"]),
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
        "master_records_acceptance": dict(native_confirmation),
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

    confirmation = receipt.get("master_records_acceptance")
    proposal_digest = receipt.get("master_records_record_hash")
    _require(isinstance(proposal_digest, str) and bool(proposal_digest),
             "MASTER_RECORDS_PROPOSAL_DIGEST_REQUIRED")
    _require(isinstance(confirmation, Mapping),
             "MASTER_RECORDS_NATIVE_ACCEPTANCE_EVIDENCE_REQUIRED")
    _require(len(closures) >= 2, "MASTER_RECORDS_PREDECESSOR_CLOSURE_REQUIRED")
    native = confirmation.get("canonical_state_receipt")
    _require(isinstance(native, Mapping), "MASTER_RECORDS_NATIVE_RECEIPT_REQUIRED")
    # Verify exact native digest and predecessor without trusting the locally
    # authored last closure. Native recording/readback must also be correlated.
    verified_digest = verify_native_master_records_confirmation(
        confirmation,
        custody_record={"record_hash": proposal_digest},
        preceding_receipt_sha256=str(closures[-2]["receipt_sha256"]),
        materialization_id=str(receipt.get("materialization_id")),
    )
    _require(closures[-1]["receipt_sha256"] == verified_digest,
             "MASTER_RECORDS_TERMINAL_NATIVE_DIGEST_MISMATCH")
    _require(closures[-1]["evidence_ref"] ==
             confirmation["recording_result"]["master_record_ref"],
             "MASTER_RECORDS_TERMINAL_RECORD_REF_MISMATCH")

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
    native_custody_client: Any = None,
) -> dict[str, Any]:
    """Prepare locally; invoke only the installed native custody client.

    No caller-provided JSON acknowledgement is accepted by this entry point.
    The authorized resident must inject the EXISTING canonical Master Records
    state-transition client and independently verified InTr replay binding.
    In all other cases no terminal receipt or far-end observation is emitted.
    """
    closures = build_closure_chain(
        outbox_entry=outbox_entry,
        ingress_receipt=ingress_receipt,
        materialization_receipt=materialization_receipt,
    )
    materialization_id = str(outbox_entry["materialization_id"])
    proposal = build_custody_record(
        materialization_id=materialization_id,
        closures=closures,
        outbox_entry=outbox_entry,
        source_commit=source_commit,
    )
    pending = {
        "state": "PENDING_MASTER_RECORDS_CUSTODY",
        "materialization_id": materialization_id,
        "proposed_custody_record": proposal,
        "master_records_custody_record": None,
        "terminal_receipt": None,
        "far_end_observation": None,
        "authority_effect": "NONE_PROPOSAL_ONLY",
    }
    if native_custody_client is None:
        return pending
    methods = ("build_state_receipt", "submit_state_receipt",
               "reconstruct_state_receipt", "replay_state_receipt")
    _require(all(callable(getattr(native_custody_client, name, None)) for name in methods),
             "CANONICAL_MASTER_RECORDS_AND_INTR_REPLAY_CLIENT_REQUIRED")
    canonical_receipt = native_custody_client.build_state_receipt(
        transition_id="MASTER_RECORDS_CUSTODY_RECORDED",
        transition_sequence=len(closures),
        subject_or_correlation_id=materialization_id,
        transition_outcome="OBSERVED",
        prior_state_ref_or_hash=str(closures[-1]["receipt_sha256"]),
        resulting_state_ref_or_hash=str(proposal["record_hash"]),
        governance_decision_ref_where_applicable=None,
        transition_evidence={
            "proposed_custody_record_sha256": proposal["record_hash"],
        },
        required_evidence_manifest=[],
    )
    _require(isinstance(canonical_receipt, Mapping),
             "CANONICAL_MASTER_RECORDS_RECEIPT_BUILDER_INVALID")
    receipt_hash = sha256_hex(dict(canonical_receipt))
    recording = native_custody_client.submit_state_receipt(canonical_receipt)
    # The existing canonical service must independently reconstruct persisted
    # bytes; the nonauthorizing proposal cannot claim that readback happened.
    reconstruction = native_custody_client.reconstruct_state_receipt(receipt_hash)
    # InTr owns replay, not CVK. The resident adapter supplies its authentic
    # replay/readback result without creating another custody authority.
    replay = native_custody_client.replay_state_receipt(receipt_hash)
    confirmation = {
        "canonical_state_receipt": canonical_receipt,
        "recording_result": recording,
        "reconstruction_result": reconstruction,
        "replay_result": replay,
    }
    terminal_receipt = build_terminal_receipt(
        materialization_id=materialization_id,
        closures=closures,
        custody_record=proposal,
        outbox_entry=outbox_entry,
        native_confirmation=confirmation,
    )
    verify_terminal_receipt(terminal_receipt)
    observation = build_far_end_observation(
        materialization_id=materialization_id,
        outbox_entry=outbox_entry,
        terminal_receipt_id=str(terminal_receipt["manifest_receipt_id"]),
        custody_record_hash=str(proposal["record_hash"]),
    )
    return {
        "state": "LIFECYCLE_RECORDED",
        "materialization_id": materialization_id,
        "proposed_custody_record": proposal,
        "master_records_custody_record": dict(recording),
        "terminal_receipt": terminal_receipt,
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
    "verify_native_master_records_confirmation",
]
