#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

FORWARD = ["SKAP", "KV", "DEVICE", "EXTERNAL_NETWORK", "ENDPOINT"]
RETURN = list(reversed(FORWARD))


def validate(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if packet.get("schema") != "stegverse.intr.packet.review_candidate/v1":
        errors.append("unsupported schema")
    if packet.get("status") != "REVIEW_CANDIDATE":
        errors.append("status must remain REVIEW_CANDIDATE")
    if packet.get("protocol") != "InTr":
        errors.append("protocol must be InTr")

    env = packet.get("envelope", {})
    direction = env.get("direction")
    path = FORWARD if direction == "FORWARD" else RETURN if direction == "RETURN" else []
    src, nxt = env.get("source_role"), env.get("next_role")
    if path:
        try:
            i = path.index(src)
        except ValueError:
            errors.append("source role is not on canonical path")
        else:
            if i + 1 >= len(path) or path[i + 1] != nxt:
                errors.append("next role must be the canonical adjacent InTr boundary")

    if env.get("authority", {}).get("authority_transfer") is not False:
        errors.append("InTr packet must not transfer authority")
    if env.get("authority", {}).get("model_output_grants_execution_authority") is not False:
        errors.append("model output must not grant execution authority")
    if env.get("authority", {}).get("transport_grants_execution_authority") is not False:
        errors.append("transport must not grant execution authority")

    protected = env.get("protected_payload", {})
    if protected.get("sealed") is not True or protected.get("plaintext_present") is not False:
        errors.append("protected payload must remain sealed and plaintext-free in transit")
    if protected.get("resolution_policy") != "ENDPOINT_SESSION_VERIFIED_AND_GRANT_VALID":
        errors.append("endpoint/session verification plus valid grant is required before resolution")

    replay = env.get("replay", {})
    max_uses, use_index = replay.get("max_uses"), replay.get("use_index")
    if not isinstance(max_uses, int) or not isinstance(use_index, int) or use_index >= max_uses:
        errors.append("replay use_index must remain below max_uses")

    try:
        issued = datetime.fromisoformat(env["issued_at"])
        expires = datetime.fromisoformat(env["expires_at"])
        if expires <= issued:
            errors.append("expires_at must be after issued_at")
    except Exception:
        errors.append("packet timestamps must be valid ISO-8601 values")

    boundary = env.get("boundary_proof", {})
    if boundary.get("required") is not True:
        errors.append("boundary proof is required")
    if boundary.get("verification_state") == "VERIFIED" and not boundary.get("next_boundary_identity_ref"):
        errors.append("verified boundary requires next-boundary identity proof")

    grant = env.get("credential_grant", {})
    endpoint = grant.get("authorized_endpoint", {})
    if not str(grant.get("credential_ref", "")).startswith("skap://"):
        errors.append("credential must be referenced through SKAP")
    if endpoint.get("scheme") != "https":
        errors.append("credential-bearing endpoint must use https")
    if grant.get("revocation_check_required_immediately_before_resolution") is not True:
        errors.append("revocation must be rechecked immediately before resolution")
    if grant.get("same_authenticated_session_required_for_resolution_and_submission") is not True:
        errors.append("resolution and credential submission must use the same authenticated session")

    receipts = env.get("receipt_policy", {})
    if receipts.get("receipt_required_each_hop") is not True or receipts.get("receipt_chain_required") is not True:
        errors.append("each InTr hop requires a chained receipt")
    if receipts.get("receipt_contains_secret_plaintext") is not False:
        errors.append("receipts must not contain secret plaintext")
    if receipts.get("ambiguous_submission_disposition") != "VERIFY_EXTERNALLY":
        errors.append("ambiguous post-submission state must be VERIFY_EXTERNALLY")

    endpoint_states = packet.get("endpoint_resolution_state_machine", [])
    required_order = ["ARRIVED_SEALED","ENDPOINT_SESSION_VERIFIED","GRANT_REVALIDATED","CREDENTIAL_RESOLVED_TRANSIENTLY","SUBMITTED_ON_SAME_SESSION","PLAINTEXT_DISCARDED","RECEIPTED"]
    if endpoint_states != required_order:
        errors.append("endpoint resolution state machine order mismatch")

    failures = packet.get("failure_invariants", {})
    for key in ("wrong_boundary","expired_packet","replay_detected","authority_mismatch","endpoint_mismatch","revoked_credential","session_changed_after_verification"):
        if failures.get(key) != "FAIL_CLOSED":
            errors.append(f"{key} must FAIL_CLOSED")
    if failures.get("ambiguous_after_submission") != "VERIFY_EXTERNALLY":
        errors.append("ambiguous_after_submission must VERIFY_EXTERNALLY")
    return errors


def reject(base: dict[str, Any], mutator, fragment: str) -> None:
    value = copy.deepcopy(base)
    mutator(value)
    errs = validate(value)
    if not any(fragment in e for e in errs):
        raise AssertionError(f"expected rejection containing {fragment!r}; got {errs!r}")


def self_test(base: dict[str, Any]) -> None:
    assert not validate(base), validate(base)
    reject(base, lambda x: x["envelope"].__setitem__("next_role", "DEVICE"), "canonical adjacent")
    reject(base, lambda x: x["envelope"]["authority"].__setitem__("authority_transfer", True), "must not transfer authority")
    reject(base, lambda x: x["envelope"]["protected_payload"].__setitem__("plaintext_present", True), "plaintext-free")
    reject(base, lambda x: x["envelope"]["replay"].__setitem__("use_index", 1), "below max_uses")
    reject(base, lambda x: x["envelope"]["credential_grant"].__setitem__("same_authenticated_session_required_for_resolution_and_submission", False), "same authenticated session")
    reject(base, lambda x: x["envelope"]["credential_grant"].__setitem__("revocation_check_required_immediately_before_resolution", False), "revocation")
    reject(base, lambda x: x["envelope"]["receipt_policy"].__setitem__("receipt_contains_secret_plaintext", True), "must not contain secret plaintext")
    reject(base, lambda x: x["failure_invariants"].__setitem__("ambiguous_after_submission", "RETRY"), "VERIFY_EXTERNALLY")
    print("INTR_PACKET_REVIEW_CANDIDATE_SELF_TEST_PASS")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("packet", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    value = json.loads(args.packet.read_text(encoding="utf-8"))
    errors = validate(value)
    if errors:
        print(json.dumps({"decision":"BLOCK","errors":errors}, indent=2, sort_keys=True))
        return 1
    if args.self_test:
        self_test(value)
    print(json.dumps({"decision":"ALLOW_REVIEW","protocol":"InTr","status":"REVIEW_CANDIDATE","semantic_errors":[]}, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
