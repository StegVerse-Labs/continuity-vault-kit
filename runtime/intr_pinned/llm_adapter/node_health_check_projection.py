"""NODE_HEALTH_CHECK_OBSERVED: project a StegHealth runtime observation into stegverse.node-health-check/v1.

Class B piece (3) of the LC-KV-13 inventory (StegVerse-org/.github#162).

The nearest existing source is StegHealth's `sovereign_runtime_observation`
(`stegverse.steghealth.sovereign-runtime-observation/v1`, StegVerse-Labs/StegHealth
@8508a43c). It is a CLI-only projection with no receipt, and the inventory found
this schema delta from `stegverse.node-health-check/v1`:
* it has no `node_id`;
* it has no `status`; health is boolean predicates plus epoch/tick.
This projection closes the delta without changing StegHealth.
* `node_id` comes from a node health attestation (`stegverse.node-health-attestation/v1`).
  The node signs it with the Ed25519 key its current NODE_IDENTITY_BINDING
  receipt binds. It names the node, that binding receipt and the observation's
  sha256. The signed bytes are `stegverse.node-health-attestation/v1\\n` followed
  by the canonical attestation without `signature_b64`.
* `status` is exactly HEALTHY when every required predicate below holds.
  Otherwise it is UNHEALTHY, and the failing predicates are listed.

Trigger: delivery of a StegHealth observation together with its attestation.
Never a timer or a poll.

What is verified (FAIL_CLOSED, with six fields and nothing appended, otherwise):
* the cited binding receipt is read back on the chain, is the node's newest
  NODE_IDENTITY_BINDING, and is ALLOW;
* the attestation verifies under the bound public key, whose sha256 equals the
  binding's key_ref;
* the observation has the StegHealth schema and no private key material.

An observation that verifies but fails a predicate is still a receipted check,
with status UNHEALTHY. #429's producer turns it into an UNHEALTHY report, which
the evaluator DENYs.

`plan()` is the deterministic core: no clock, network or randomness, and it never
writes. `produce()` appends through the repository emitter. The same observation
for the same node is NOOP_ALREADY_CURRENT. The observation's `observed_at` is
copied as descriptive data only and orders nothing.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from llm_adapter import ed25519_verify
from llm_adapter import healthy_node_evaluator as hne
from llm_adapter import node_receipt_common as common

ALLOW = common.ALLOW
REPOSITORY = common.REPOSITORY
HEALTHY = hne.HEALTHY
UNHEALTHY = "UNHEALTHY"
TRANSITION_CLASS = common.HEALTH_CHECK_CLASS
EVIDENCE_SCHEMA = common.HEALTH_CHECK_SCHEMA
BINDING_CLASS = common.BINDING_CLASS
SOURCE_SCHEMA = "stegverse.steghealth.sovereign-runtime-observation/v1"
ATTESTATION_SCHEMA = "stegverse.node-health-attestation/v1"
RESULT_SCHEMA = "stegverse.node-health-check-projection-result/v1"
FAILURE_CODE = "NODE_HEALTH_CHECK_NOT_OBSERVED"
RETRY_ENTRYPOINT = ("llm_adapter.node_health_check_projection.produce(binding_receipt_sha256, observation, "
                    "attestation, ledger_root=...)")
NEXT_ATTEMPT = ("fires again when the node delivers a new StegHealth runtime observation with a signed attestation. "
                "Never on a timer.")

#: (field, required value) pairs; every one must hold for HEALTHY.
REQUIRED = (
    ("authenticated_sovereign_report", True),
    ("native_service_active", True),
    ("continuous_runtime_live", True),
    ("worker_task_capable_cycle_observed", True),
    ("controlled_restart_observed", True),
    ("state_reconstruction_pass", True),
    ("epoch_and_generation_non_regressing", True),
    ("no_duplicate_claim_or_fence", True),
    ("credential_authority", "TV/TVC"),
    ("credential_requirement", "NONE"),
    ("github_token_runtime_authority", "NONE"),
    ("third_party_runtime_required", False),
    ("authority_effect", "NONE_OBSERVATION_ONLY"),
)

REASONS: dict[str, tuple[str, str]] = {
    "BINDING_NOT_RECEIPTED": (BINDING_CLASS, "cite the node's newest NODE_IDENTITY_BINDING ALLOW receipt, read back "
                              "on the chain from HEAD.json"),
    "CREDENTIAL_MATERIAL_PRESENT": ("NO_CREDENTIAL_HELD", "send public inputs only; private key material stays in "
                                    "TVC custody"),
    "OBSERVATION_INVALID": ("HEALTH_OBSERVATION", f"a {SOURCE_SCHEMA} observation"),
    "ATTESTATION_INVALID": ("HEALTH_ATTESTATION", f"a {ATTESTATION_SCHEMA} naming the node, the cited binding "
                            "receipt and the observation's sha256"),
    "SIGNATURE_INVALID": ("HEALTH_ATTESTATION", "an Ed25519 signature by the bound node key over the "
                          "domain-separated canonical attestation"),
}


def _fail(reason: str, detail: str, node_id: Any = None) -> dict[str, Any]:
    return common.non_allow(schema=RESULT_SCHEMA, failure_code=FAILURE_CODE, reasons=REASONS, reason=reason,
                            detail=detail, retry_entrypoint=RETRY_ENTRYPOINT, next_attempt=NEXT_ATTEMPT,
                            node_id=node_id)


def attestation_message(attestation: Mapping[str, Any]) -> bytes:
    """The bytes the node signs for its health attestation."""
    return common.signed_message(ATTESTATION_SCHEMA, {k: v for k, v in attestation.items() if k != "signature_b64"})


def plan(binding_receipt_sha256: Any, observation: Any, attestation: Any, *, ledger_root: Any,
         repository: str = REPOSITORY) -> dict[str, Any]:
    """Deterministic core: verify and project one observation; never writes."""
    leaked = common.credential_fields({"observation": observation, "attestation": attestation})
    if leaked:
        return _fail("CREDENTIAL_MATERIAL_PRESENT", f"refused fields: {', '.join(leaked)}")
    chain, failure, detail = common.read_chain(ledger_root, repository)
    if failure:
        return _fail(failure, detail)
    binding = next((r for r in chain if r["receipt_sha256"] == binding_receipt_sha256), None)
    ev = common.evidence(binding) if binding else {}
    node_id = ev.get("node_id")
    if binding is None or binding.get("transition_class") != BINDING_CLASS or ev.get("disposition") != ALLOW \
            or not isinstance(node_id, str) or not node_id:
        return _fail("BINDING_NOT_RECEIPTED", f"{binding_receipt_sha256!r} is not a binding ALLOW on the chain")
    newest = next(r for r in chain if r.get("transition_class") == BINDING_CLASS
                  and common.evidence(r).get("node_id") == node_id)
    if newest["receipt_sha256"] != binding_receipt_sha256:
        return _fail("BINDING_NOT_RECEIPTED", f"superseded by {newest['receipt_sha256']}", node_id)
    public_key = common.b64(ev.get("public_key_b64"))
    key_ref = ev.get("key_ref") if isinstance(ev.get("key_ref"), Mapping) else {}
    if public_key is None or "sha256:" + hashlib.sha256(public_key).hexdigest() != key_ref.get("public_key_sha256"):
        return _fail("BINDING_NOT_RECEIPTED", "the binding's public key does not match its key_ref", node_id)

    if not isinstance(observation, Mapping) or observation.get("schema") != SOURCE_SCHEMA:
        return _fail("OBSERVATION_INVALID", "not a StegHealth sovereign runtime observation", node_id)
    observation_sha = hne.sha(dict(observation))
    if (not isinstance(attestation, Mapping) or attestation.get("schema") != ATTESTATION_SCHEMA
            or attestation.get("node_id") != node_id or attestation.get("binding_receipt_sha256") != binding_receipt_sha256
            or attestation.get("observation_sha256") != observation_sha):
        return _fail("ATTESTATION_INVALID", "the attestation does not name this node, binding and observation", node_id)
    signature = common.b64(attestation.get("signature_b64"))
    if signature is None or not ed25519_verify.verify(public_key, attestation_message(attestation), signature):
        return _fail("SIGNATURE_INVALID", "the attestation does not verify under the bound key", node_id)

    failing = [field for field, required in REQUIRED
               if not (type(observation.get(field)) is type(required) and observation.get(field) == required)]
    status = HEALTHY if not failing else UNHEALTHY
    epoch = common.chain_epoch(chain)
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "node_id": node_id,
        "status": status,
        "failing_predicates": failing,
        "required_predicates": [field for field, _ in REQUIRED],
        "source": {
            "schema": SOURCE_SCHEMA,
            "observation_sha256": observation_sha,
            "source_proof_sha256": observation.get("source_proof_sha256"),
            "observed_at_descriptive_only": observation.get("observed_at"),
        },
        "binding_receipt_sha256": binding_receipt_sha256,
        "attestation_sha256": hne.sha(dict(attestation)),
        "attestation_verified": True,
        "health_check_authenticated": "SIGNED_BY_BOUND_NODE_KEY",
        "authority_effect": "NONE",
    }
    previous = next((r for r in chain if r.get("transition_class") == TRANSITION_CLASS
                     and common.evidence(r).get("node_id") == node_id
                     and common.evidence(r).get("schema") == EVIDENCE_SCHEMA), None)
    already = (previous["receipt_sha256"] if previous is not None
               and (common.evidence(previous).get("source") or {}).get("observation_sha256") == observation_sha
               and common.evidence(previous).get("binding_receipt_sha256") == binding_receipt_sha256 else None)
    return {
        "schema": RESULT_SCHEMA,
        "disposition": ALLOW,
        "node_id": node_id,
        "check_status": status,
        "receipt_evidence": evidence,
        "transition_id": f"{TRANSITION_CLASS}:{node_id}:{observation_sha}",
        "predecessor_state_sha256": (previous["receipt_sha256"] if previous
                                     else hne.sha({"node_id": node_id, "health_check": None})),
        "successor_state_sha256": hne.sha(evidence),
        "hb_epoch": epoch,
        "already_current_receipt_sha256": already,
        "authority_effect": "NONE",
    }


def produce(binding_receipt_sha256: Any, observation: Any, attestation: Any, *, ledger_root: Any,
            repository: str = REPOSITORY) -> dict[str, Any]:
    """Plan, then append NODE_HEALTH_CHECK_OBSERVED (or return NOOP / FAIL_CLOSED)."""
    planned = plan(binding_receipt_sha256, observation, attestation, ledger_root=ledger_root, repository=repository)
    return common.produce(planned, TRANSITION_CLASS, ledger_root, lambda: _fail(
        "LEDGER_ROOT_MISMATCH", "the emitter's ledger root is not the ledger root that was read", planned.get("node_id")))


__all__ = ["ATTESTATION_SCHEMA", "EVIDENCE_SCHEMA", "FAILURE_CODE", "REASONS", "REQUIRED", "SOURCE_SCHEMA",
           "TRANSITION_CLASS", "UNHEALTHY", "attestation_message", "plan", "produce"]
