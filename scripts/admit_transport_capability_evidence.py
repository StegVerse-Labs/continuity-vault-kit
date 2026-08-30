#!/usr/bin/env python3
"""Admit authentic Device-Node transport observation evidence into KV readiness facts."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "specs" / "kv-activation-readiness-facts.v1.json"

HF_SCHEMA = "stegverse.sv-dn1.browser-resident-observation-bundle/v3"
HIL_SCHEMA = "stegverse.hil.canonical-observation-evidence/v1"

MAPPING = {
    HF_SCHEMA: "ADJACENT_EXTERNAL_API_EGRESS",
    HIL_SCHEMA: "PUBLIC_HTTPS_INGRESS",
}


def _require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate_hf(payload: dict) -> list[str]:
    failures: list[str] = []
    _require(payload.get("schema") == HF_SCHEMA, "unexpected HF evidence schema", failures)
    _require(payload.get("state") == "OBSERVED", "HF evidence must be OBSERVED", failures)
    _require(payload.get("observation_class") == "AUTHENTIC_ESTABLISHED_STEGVERSE_WEB_NODE", "HF observation class invalid", failures)
    _require(payload.get("authority_effect") == "NONE", "HF authority_effect must be NONE", failures)

    node = payload.get("node_registration")
    _require(isinstance(node, dict), "HF node registration missing", failures)
    if isinstance(node, dict):
        _require(node.get("state") == "ESTABLISHED", "HF node must be ESTABLISHED", failures)
        _require(node.get("credential_authority") == "TV/TVC", "HF credential authority must be TV/TVC", failures)

    resident = payload.get("resident_receipt")
    _require(isinstance(resident, dict), "HF resident receipt missing", failures)
    if isinstance(resident, dict):
        _require(resident.get("state") == "COMPLETE", "HF resident receipt must be COMPLETE", failures)
        _require(resident.get("credential_used") is False, "HF credential_used must be false", failures)
        _require(resident.get("github_token_used") is False, "HF github_token_used must be false", failures)
        _require(resident.get("authority_effect") == "NONE", "HF resident authority_effect must be NONE", failures)

    intr = payload.get("intr_receipt")
    _require(isinstance(intr, dict), "HF InTr receipt missing", failures)
    if isinstance(intr, dict):
        _require(intr.get("state") == "COMPLETE", "HF InTr receipt must be COMPLETE", failures)
        _require(intr.get("transport_profile") == "stegverse.universal-intr.adjacent-hop/v1", "HF transport profile mismatch", failures)
        _require(intr.get("destination_validation") == "PASS", "HF destination validation must PASS", failures)
        _require(intr.get("lineage_verified") is True, "HF lineage must be verified", failures)
        _require(intr.get("authority_effect") == "NONE", "HF InTr authority_effect must be NONE", failures)
        claims = intr.get("claims")
        _require(isinstance(claims, dict), "HF InTr claims missing", failures)
        if isinstance(claims, dict):
            _require(claims.get("credential_used") is False, "HF InTr credential_used must be false", failures)
            _require(claims.get("runtime_activation_claimed") is False, "HF runtime activation may not be claimed", failures)
            _require(claims.get("production_interlock_runtime_activated") is False, "HF production Interlock activation may not be claimed", failures)

    assertions = payload.get("assertions")
    _require(isinstance(assertions, dict), "HF assertions missing", failures)
    if isinstance(assertions, dict):
        for key in (
            "existing_node_reused",
            "public_source_live_fetch",
            "exact_raw_bytes_hashed",
            "universal_intr_adjacent_hop_executed",
            "lineage_verified",
        ):
            _require(assertions.get(key) is True, f"HF assertion {key} must be true", failures)
        _require(assertions.get("new_node_identity_minted") is False, "HF may not mint a new node identity", failures)
        _require(assertions.get("destination_validation") == "PASS", "HF destination validation assertion must PASS", failures)
        _require(assertions.get("global_runtime_activation_claimed") is False, "HF global runtime activation may not be claimed", failures)

    replay = payload.get("journal_replay")
    _require(isinstance(replay, dict) and replay.get("state") == "PASS", "HF journal replay must PASS", failures)
    recon = payload.get("reconstruction_entry")
    if isinstance(recon, dict):
        receipt = recon.get("receipt", recon)
        _require(receipt.get("state") == "PASS", "HF reconstruction must PASS", failures)
        _require(receipt.get("same_execution") is True, "HF reconstruction must preserve same execution", failures)
    else:
        failures.append("HF reconstruction entry missing")

    return failures


def validate_hil(payload: dict) -> list[str]:
    failures: list[str] = []
    _require(payload.get("schema") == HIL_SCHEMA, "unexpected HIL evidence schema", failures)
    _require(payload.get("state") == "OBSERVED", "HIL evidence must be OBSERVED", failures)
    _require(payload.get("observation_class") == "AUTHENTIC_ESTABLISHED_STEGVERSE_WEB_NODE", "HIL observation class invalid", failures)
    _require(payload.get("authority_effect") == "NONE", "HIL authority_effect must be NONE", failures)
    _require(payload.get("existing_node_reused") is True, "HIL must reuse established node", failures)
    _require(payload.get("new_node_identity_minted") is False, "HIL may not mint new node identity", failures)
    _require(payload.get("credential_used") is False, "HIL credential_used must be false", failures)
    _require(payload.get("github_token_used") is False, "HIL github_token_used must be false", failures)
    _require(payload.get("exact_byte_reconstruction") == "PASS", "HIL exact-byte reconstruction must PASS", failures)
    _require(payload.get("custody_state") == "EXACT_BYTES_PERSISTED", "HIL custody must be exact bytes", failures)
    _require(payload.get("registry_state") == "RECORDED", "HIL registry state must be RECORDED", failures)
    _require(payload.get("journal_replay_state") == "PASS", "HIL journal replay must PASS", failures)
    _require(payload.get("next_required_transition") == "HIL_CUSTODY_TVC_INTERLOCK_ADMISSION", "HIL next transition mismatch", failures)
    return failures


def admit(payload: dict, facts: dict) -> tuple[dict, dict]:
    schema = payload.get("schema")
    if schema == HF_SCHEMA:
        failures = validate_hf(payload)
    elif schema == HIL_SCHEMA:
        failures = validate_hil(payload)
    else:
        raise ValueError("unsupported transport observation schema")

    if failures:
        raise ValueError("; ".join(failures))

    capability = MAPPING[schema]
    updated = deepcopy(facts)
    observed = updated.get("transport_capabilities_observed")
    if not isinstance(observed, dict) or capability not in observed:
        raise ValueError("KV readiness facts do not contain mapped transport capability")

    observed[capability] = True
    admission = {
        "schema": "stegverse.kv.transport-capability-evidence-admission/v1",
        "state": "ADMITTED",
        "source_schema": schema,
        "capability_type": capability,
        "facts_advanced": [f"transport_capabilities_observed.{capability}"],
        "unrelated_facts_advanced": [],
        "activation_performed": False,
        "authority_effect": "NONE",
    }
    return updated, admission


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--facts", type=Path, default=FACTS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--admission-output", type=Path)
    args = parser.parse_args()

    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    facts = json.loads(args.facts.read_text(encoding="utf-8"))
    try:
        updated, admission = admit(evidence, facts)
    except ValueError as exc:
        print("KV_TRANSPORT_CAPABILITY_EVIDENCE_ADMISSION_FAIL")
        print(str(exc))
        return 1

    if args.output:
        args.output.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    if args.admission_output:
        args.admission_output.write_text(json.dumps(admission, indent=2) + "\n", encoding="utf-8")

    print("KV_TRANSPORT_CAPABILITY_EVIDENCE_ADMISSION_PASS")
    print(f"CAPABILITY_TYPE={admission['capability_type']}")
    print("ACTIVATION_PERFORMED=false")
    print("AUTHORITY_EFFECT=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
