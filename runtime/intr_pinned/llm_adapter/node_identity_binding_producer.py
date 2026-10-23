"""NODE_IDENTITY_BINDING: bind a node's identity key to its receipted existence, by key reference only.

Class B piece (2) of the LC-KV-13 inventory (StegVerse-org/.github#162).

The spec (StegVerse-Labs/.github data/node-exchange/first-executable-conformance-v0.1.json,
gate order 2) asks for an identity claim, cryptographic binding evidence and an
identity disposition. No writer existed. This producer is that writer.

Trigger: a receipted AUTHENTICATED_RECIPROCAL_NODE_EXISTENCE ALLOW on this
repository's chain, cited by its address, delivered with the node's identity
claim and the public InTr profile that the existence observation hashed. Never
a timer or a poll.

What is verified, from public inputs only:
1. The existence receipt is read back on the chain from HEAD.json. It is the
   node's newest existence receipt, and its disposition is ALLOW.
2. The profile document hashes (StegOS canonical sha256) to the existence
   receipt's `observation.profile_sha256`. That ties the key to the profile
   that was reciprocally observed.
3. The profile's `node_identity_key` is the key reference: algorithm Ed25519,
   key_id, public key, `node_id` equal to the node, and custody TV/TVC.
   sha256(public key) equals the claim's `key_ref.public_key_sha256`.
4. The claim (`stegverse.node-identity-claim/v1`) names the node, the existence
   receipt and the profile hash. Its Ed25519 signature verifies under that
   public key. The signed bytes are `stegverse.node-identity-claim/v1\\n` followed
   by the canonical claim without `signature_b64`.

The producer verifies only. It never generates, derives, receives, holds or
stores a private key or any credential: TVC custody holds the node's key. Any
input field named like private key material (CREDENTIAL_FIELD_NAMES) is
refused.

On ALLOW it appends NODE_IDENTITY_BINDING with evidence `{node_id, disposition
ALLOW, existence_receipt_sha256, ...}`, newer than and citing the existence
receipt, which is the shape node_health_report_producer (#429) reads. Anything
unreceipted or unverifiable is a six-field FAIL_CLOSED, and nothing is appended.

`plan()` is the deterministic core: no clock, network or randomness, and it never
writes. `produce()` appends through the repository emitter. The same claim on the
same existence receipt is NOOP_ALREADY_CURRENT.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from llm_adapter import ed25519_verify
from llm_adapter import healthy_node_evaluator as hne
from llm_adapter import node_receipt_common as common

ALLOW = common.ALLOW
REPOSITORY = common.REPOSITORY
TRANSITION_CLASS = common.BINDING_CLASS
EXISTENCE_CLASS = common.EXISTENCE_CLASS
EVIDENCE_SCHEMA = "stegverse.node-identity-binding/v1"
CLAIM_SCHEMA = "stegverse.node-identity-claim/v1"
RESULT_SCHEMA = "stegverse.node-identity-binding-result/v1"
ALGORITHM = "Ed25519"
KEY_CUSTODY = "TV/TVC"
FAILURE_CODE = "NODE_IDENTITY_NOT_BOUND"
RETRY_ENTRYPOINT = ("llm_adapter.node_identity_binding_producer.produce(existence_receipt_sha256, identity_claim, "
                    "profile, ledger_root=...)")
NEXT_ATTEMPT = ("fires again when a receipted existence ALLOW for this node arrives with a signed identity claim "
                "and the observed profile. Never on a timer.")

REASONS: dict[str, tuple[str, str]] = {
    "EXISTENCE_NOT_RECEIPTED": (EXISTENCE_CLASS, "cite an AUTHENTICATED_RECIPROCAL_NODE_EXISTENCE receipt that is "
                                "read back on the chain from HEAD.json"),
    "EXISTENCE_NOT_ALLOW": (EXISTENCE_CLASS, "the cited existence receipt must have disposition ALLOW and name a node"),
    "EXISTENCE_SUPERSEDED": (EXISTENCE_CLASS, "cite the node's newest existence receipt"),
    "CREDENTIAL_MATERIAL_PRESENT": ("NO_CREDENTIAL_HELD", "send public inputs only; private key material stays in "
                                    "TVC custody and is never sent here"),
    "PROFILE_NOT_OBSERVED": ("PROFILE_MATCHES_EXISTENCE_OBSERVATION", "the profile document must hash to the "
                             "existence receipt's observation.profile_sha256"),
    "KEY_REFERENCE_INVALID": ("IDENTITY_KEY_REFERENCE", "the profile's node_identity_key must be an Ed25519 public "
                              "key for this node_id with custody TV/TVC, matching the claim's key_ref"),
    "CLAIM_INVALID": ("IDENTITY_CLAIM", f"a {CLAIM_SCHEMA} claim naming the node, the cited existence receipt and "
                      "the profile hash"),
    "SIGNATURE_INVALID": ("CRYPTOGRAPHIC_BINDING_EVIDENCE", "an Ed25519 signature by the referenced key over the "
                          "domain-separated canonical claim"),
}


def _fail(reason: str, detail: str, node_id: Any = None) -> dict[str, Any]:
    return common.non_allow(schema=RESULT_SCHEMA, failure_code=FAILURE_CODE, reasons=REASONS, reason=reason,
                            detail=detail, retry_entrypoint=RETRY_ENTRYPOINT, next_attempt=NEXT_ATTEMPT,
                            node_id=node_id)


def stegos_profile_sha256(profile: Mapping[str, Any]) -> str:
    """StegOS universal_intr_public_profile.profile_sha256 (bare hex), reproduced without importing StegOS."""
    raw = json.dumps(dict(profile), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def claim_message(claim: Mapping[str, Any]) -> bytes:
    """The bytes the node signs for its identity claim."""
    return common.signed_message(CLAIM_SCHEMA, {k: v for k, v in claim.items() if k != "signature_b64"})


def plan(existence_receipt_sha256: Any, identity_claim: Any, profile: Any, *, ledger_root: Any,
         repository: str = REPOSITORY) -> dict[str, Any]:
    """Deterministic core: verify the binding from public inputs and the chain; never writes."""
    leaked = common.credential_fields({"identity_claim": identity_claim, "profile": profile})
    if leaked:
        return _fail("CREDENTIAL_MATERIAL_PRESENT", f"refused fields: {', '.join(leaked)}")
    chain, failure, detail = common.read_chain(ledger_root, repository)
    if failure:
        return _fail(failure, detail)
    existence = next((r for r in chain if r["receipt_sha256"] == existence_receipt_sha256), None)
    if existence is None or existence.get("transition_class") != EXISTENCE_CLASS:
        return _fail("EXISTENCE_NOT_RECEIPTED", f"{existence_receipt_sha256!r} is not an existence receipt on the chain")
    ev = common.evidence(existence)
    node_id = ev.get("node_id")
    if ev.get("disposition") != ALLOW or not isinstance(node_id, str) or not node_id:
        return _fail("EXISTENCE_NOT_ALLOW", f"existence disposition {ev.get('disposition')!r}", node_id)
    newest = next(r for r in chain if r.get("transition_class") == EXISTENCE_CLASS
                  and common.evidence(r).get("node_id") == node_id)
    if newest["receipt_sha256"] != existence_receipt_sha256:
        return _fail("EXISTENCE_SUPERSEDED", f"newest existence receipt is {newest['receipt_sha256']}", node_id)

    observed = (ev.get("observation") or {}).get("profile_sha256") if isinstance(ev.get("observation"), Mapping) else None
    try:
        profile_hash = stegos_profile_sha256(profile) if isinstance(profile, Mapping) else None
    except (TypeError, ValueError):
        profile_hash = None
    if not isinstance(observed, str) or profile_hash != observed:
        return _fail("PROFILE_NOT_OBSERVED", "the profile does not hash to the observed profile_sha256", node_id)

    key = profile.get("node_identity_key")
    public_key = common.b64(key.get("public_key_b64")) if isinstance(key, Mapping) else None
    if (public_key is None or len(public_key) != 32 or key.get("algorithm") != ALGORITHM
            or key.get("node_id") != node_id or key.get("custody") != KEY_CUSTODY
            or not isinstance(key.get("key_id"), str) or not key["key_id"]):
        return _fail("KEY_REFERENCE_INVALID", "profile node_identity_key is missing or does not name this node", node_id)
    if key != (ev.get("observation") or {}).get("node_identity_key"):
        return _fail("KEY_REFERENCE_INVALID", "profile node_identity_key differs from the one the existence "
                     "read-back recorded", node_id)
    key_ref = {"algorithm": ALGORITHM, "key_id": key["key_id"],
               "public_key_sha256": "sha256:" + hashlib.sha256(public_key).hexdigest()}

    if (not isinstance(identity_claim, Mapping) or identity_claim.get("schema") != CLAIM_SCHEMA
            or identity_claim.get("node_id") != node_id
            or identity_claim.get("existence_receipt_sha256") != existence_receipt_sha256
            or identity_claim.get("profile_sha256") != observed):
        return _fail("CLAIM_INVALID", "the claim does not name this node, existence receipt and profile", node_id)
    if identity_claim.get("key_ref") != key_ref:
        return _fail("KEY_REFERENCE_INVALID", "the claim's key_ref does not match the profile's key", node_id)
    signature = common.b64(identity_claim.get("signature_b64"))
    if signature is None or not ed25519_verify.verify(public_key, claim_message(identity_claim), signature):
        return _fail("SIGNATURE_INVALID", "the claim signature does not verify under the referenced key", node_id)

    epoch = common.chain_epoch(chain)
    claim_sha = hne.sha(dict(identity_claim))
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "node_id": node_id,
        "disposition": ALLOW,
        "existence_receipt_sha256": existence_receipt_sha256,
        "profile_sha256": observed,
        "key_ref": key_ref,
        "public_key_b64": key["public_key_b64"],
        "identity_claim_sha256": claim_sha,
        "signature_verified": True,
        "verification": "ED25519_AGAINST_KEY_REFERENCE_FROM_RECIPROCALLY_OBSERVED_PROFILE",
        "key_custody": KEY_CUSTODY,
        "credential_held_or_minted": False,
        "authority_effect": "NONE",
    }
    previous = next((r for r in chain if r.get("transition_class") == TRANSITION_CLASS
                     and common.evidence(r).get("node_id") == node_id), None)
    already = (previous["receipt_sha256"] if previous is not None
               and common.evidence(previous).get("identity_claim_sha256") == claim_sha
               and common.evidence(previous).get("existence_receipt_sha256") == existence_receipt_sha256 else None)
    return {
        "schema": RESULT_SCHEMA,
        "disposition": ALLOW,
        "node_id": node_id,
        "receipt_evidence": evidence,
        "transition_id": f"{TRANSITION_CLASS}:{node_id}:{existence_receipt_sha256}",
        "predecessor_state_sha256": (previous["receipt_sha256"] if previous
                                     else hne.sha({"node_id": node_id, "identity_binding": None})),
        "successor_state_sha256": hne.sha(evidence),
        "hb_epoch": epoch,
        "already_current_receipt_sha256": already,
        "authority_effect": "NONE",
    }


def produce(existence_receipt_sha256: Any, identity_claim: Any, profile: Any, *, ledger_root: Any,
            repository: str = REPOSITORY) -> dict[str, Any]:
    """Plan, then append NODE_IDENTITY_BINDING (or return NOOP / FAIL_CLOSED)."""
    planned = plan(existence_receipt_sha256, identity_claim, profile, ledger_root=ledger_root, repository=repository)
    return common.produce(planned, TRANSITION_CLASS, ledger_root, lambda: _fail(
        "LEDGER_ROOT_MISMATCH", "the emitter's ledger root is not the ledger root that was read", planned.get("node_id")))


__all__ = ["ALGORITHM", "CLAIM_SCHEMA", "EVIDENCE_SCHEMA", "FAILURE_CODE", "REASONS", "TRANSITION_CLASS",
           "claim_message", "plan", "produce", "stegos_profile_sha256"]
