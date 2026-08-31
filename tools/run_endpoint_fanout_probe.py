#!/usr/bin/env python3
"""Run a loopback endpoint fan-out probe across KV Interlock and Master Records contracts.

This is a TEST_ONLY local integration probe. It does not claim production endpoint
activation, live DEVICE_KV_INTR, or Master Records custody authority.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from runtime.kv_interlock_endpoint import KVInterlockRuntime, canonical_json, sha256_uri


PROBE_SCHEMA = "stegverse.endpoint-fanout-probe.v1"
KV_REPORT_SCHEMA = "stegverse.kv-interlock.endpoint-status-report.v1"
TRAVEL_REPORT_SCHEMA = "stegverse.master-records.travel-report.v1"
CUSTODY_RESULT_SCHEMA = "stegverse.master-records.test-custody-result.v1"


def sha256_hex_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class InMemoryMasterRecordsSink:
    """Contract-shaped local sink matching the governed transition custody intake."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def submit(self, submission: Mapping[str, Any]) -> dict[str, Any]:
        if submission.get("schema_version") != "1.0.0":
            raise ValueError("master records submission schema mismatch")
        if submission.get("submission_type") != "governed_transition_custody_candidate":
            raise ValueError("master records submission type mismatch")
        record = submission.get("record")
        if not isinstance(record, dict):
            raise ValueError("master records record required")
        if record.get("record_type") != "governed_transition_relationship":
            raise ValueError("master records record_type mismatch")
        if record.get("lifecycle_state") != "COMPLETED":
            raise ValueError("master records lifecycle state mismatch")
        governance = record.get("governance") or {}
        if governance.get("admissibility_result") != "ALLOW":
            raise ValueError("master records admissibility must ALLOW in test fixture")
        if governance.get("commit_time_validity") != "VALID":
            raise ValueError("master records commit-time validity must be VALID")
        verification_ref = (record.get("execution") or {}).get("verification_ref")
        if not isinstance(verification_ref, str) or not verification_ref:
            raise ValueError("master records verification ref required")
        continuity = record.get("continuity") or {}
        identity = (
            submission.get("transition_id"),
            submission.get("run_id"),
            submission.get("final_receipt_id"),
        )
        if identity != (
            record.get("transition_id"),
            record.get("run_id"),
            continuity.get("final_receipt_id"),
        ):
            raise ValueError("master records identity mismatch")
        boundary = submission.get("authority_boundary") or {}
        if any(
            boundary.get(key) is not False
            for key in (
                "submission_is_custody",
                "local_persistence_is_custody",
                "client_may_self_issue_custody_receipt",
            )
        ):
            raise ValueError("master records client authority boundary invalid")

        canonical_record = copy.deepcopy(record)
        record_sha256 = sha256_json(canonical_record)
        master_record_ref = f"master-record:sha256:{record_sha256}"
        custody_receipt_id = (
            "test-only-master-records-receipt:sha256:"
            + sha256_json(
                {
                    "transition_id": submission["transition_id"],
                    "run_id": submission["run_id"],
                    "final_receipt_id": submission["final_receipt_id"],
                    "record_sha256": record_sha256,
                }
            )
        )
        self.records.append(canonical_record)
        return {
            "schema": CUSTODY_RESULT_SCHEMA,
            "custody_status": "TEST_ONLY_RECORDED",
            "master_record_ref": master_record_ref,
            "custody_receipt_id": custody_receipt_id,
            "record_sha256": record_sha256,
            "authority_granted": False,
            "production_custody_claimed": False,
        }


def build_probe(value: str, *, probe_id: str) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        raise ValueError("probe value required")
    return {
        "schema": PROBE_SCHEMA,
        "probe_id": probe_id,
        "value": value,
        "classification": "TEST_ONLY_NON_SECRET",
        "authority_effect": "NONE",
    }


def build_request(probe: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "kv.interlock.request.v1",
        "operation": "REQUEST",
        "request_id": f"fanout-probe:{probe['probe_id']}",
        "requester": {
            "module": "continuity-vault-kit",
            "component": "endpoint-fanout-probe",
        },
        "purpose": "Test one probe through KV Interlock and derive two bounded reports.",
        "record_class": "ENDPOINT_FANOUT_PROBE",
        "requested_scope": ["probe_value", "probe_sha256"],
        "minimum_necessary_justification": (
            "Verify endpoint handling plus report fan-out without canonical state mutation."
        ),
        "authority_ref": "test-only-owner-assertion",
        "disclosure_mode": "BOUNDED_CONTEXT",
    }


def build_envelope(request: Mapping[str, Any], *, now: datetime) -> dict[str, Any]:
    return {
        "schema": "stegverse.kv-interlock.intr-envelope/v1",
        "protocol": "InTr",
        "packet_id": f"packet:{request['request_id']}",
        "direction": "REQUEST",
        "source_role": "DEVICE",
        "next_role": "KV",
        "request_id": request["request_id"],
        "operation": request["operation"],
        "payload_schema_version": "kv.interlock.request.v1",
        "payload_hash": sha256_uri(request),
        "sealed_material_ref": f"urn:stegverse:test:sealed:{request['request_id']}",
        "authority": {
            "authority_transfer": False,
            "transport_grants_execution_authority": False,
            "model_output_grants_execution_authority": False,
            "credential_authority_effect": "NONE",
        },
        "boundary_proof": {
            "required": True,
            "source_identity_ref": "device:test:endpoint-fanout-probe",
            "next_boundary_identity_ref": "kv:test:endpoint-fanout-probe",
            "verification_state": "VERIFIED",
        },
        "receipt_policy": {
            "receipt_required": True,
            "receipt_contains_payload_plaintext": False,
            "receipt_chain_required": True,
            "ambiguous_disposition": "FAIL_CLOSED",
        },
        "issued_at": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "expires_at": (
            now.astimezone(timezone.utc).replace(microsecond=0)
        ).isoformat().replace("+00:00", "Z"),
        "nonce": f"nonce:{request['request_id']}",
    }


def run_probe(value: str, *, probe_id: str = "endpoint-fanout-001") -> dict[str, Any]:
    now = datetime(2026, 8, 31, 3, 0, 0, tzinfo=timezone.utc)
    probe = build_probe(value, probe_id=probe_id)
    probe_sha256 = sha256_json(probe)
    stored_receipts: list[dict[str, Any]] = []

    request = build_request(probe)

    def policy(_request: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": "ALLOW_BOUNDED_CONTEXT",
            "granted_scope": ["probe_value", "probe_sha256"],
            "context": {
                "probe_value": probe["value"],
                "probe_sha256": probe_sha256,
            },
            "source_refs": [f"urn:stegverse:test:probe:{probe_id}"],
            "policy_profile": "endpoint-fanout-probe-test-v1",
            "redaction_profile": "test-only-non-secret",
        }

    runtime = KVInterlockRuntime(
        authority_validator=lambda authority_ref, *_: authority_ref == "test-only-owner-assertion",
        policy_evaluator=policy,
        receipt_store=lambda receipt: (
            stored_receipts.append(copy.deepcopy(receipt))
            or f"urn:stegverse:test:kv-receipt:{receipt['receipt_id'].split(':')[-1]}"
        ),
        clock=lambda: now,
    )

    envelope = build_envelope(request, now=now)
    # expires_at must be later than the runtime clock.
    envelope["expires_at"] = "2026-08-31T03:05:00Z"
    intr_receipt_ref = "sha256:" + sha256_hex_bytes(
        canonical_json(
            {
                "probe_id": probe_id,
                "packet_id": envelope["packet_id"],
                "payload_hash": envelope["payload_hash"],
            }
        ).encode("utf-8")
    )

    response = runtime.handle(
        request,
        intr_envelope=envelope,
        intr_receipt_ref=intr_receipt_ref,
    )

    kv_status_report = {
        "schema": KV_REPORT_SCHEMA,
        "probe_id": probe_id,
        "ingress_endpoint": "KVInterlockRuntime.handle",
        "ingress_state": "ACCEPTED",
        "intr_protocol": "InTr",
        "request_id": request["request_id"],
        "packet_id": envelope["packet_id"],
        "input_probe_sha256": probe_sha256,
        "request_payload_sha256": envelope["payload_hash"],
        "intr_receipt_ref": intr_receipt_ref,
        "decision": response["decision"],
        "granted_scope": response["granted_scope"],
        "response_hash": response["receipt"]["response_hash"],
        "kv_receipt_id": response["receipt"]["receipt_id"],
        "receipt_store_count": len(stored_receipts),
        "endpoint_status": (
            "PASS"
            if response["decision"] == "ALLOW_BOUNDED_CONTEXT"
            and response["context"].get("probe_sha256") == probe_sha256
            else "FAIL_CLOSED"
        ),
        "canonical_state_changed": False,
        "credential_authority": "TV/TVC",
        "execution_authority": "NONE",
        "authority_effect": "NONE_OBSERVATION_ONLY",
    }

    travel_hops = [
        {
            "sequence": 1,
            "boundary": "TEST_PROBE_INGRESS",
            "from": "probe-generator",
            "to": "DEVICE",
            "state": "EMITTED",
            "artifact_sha256": probe_sha256,
        },
        {
            "sequence": 2,
            "boundary": "DEVICE->KV",
            "from": "DEVICE",
            "to": "KV",
            "protocol": "InTr",
            "state": "VERIFIED",
            "packet_id": envelope["packet_id"],
            "artifact_sha256": envelope["payload_hash"].split(":", 1)[1],
        },
        {
            "sequence": 3,
            "boundary": "KV_INTERLOCK_RUNTIME",
            "from": "KV",
            "to": "KVInterlockRuntime",
            "state": response["decision"],
            "artifact_sha256": response["receipt"]["response_hash"],
        },
        {
            "sequence": 4,
            "boundary": "REPORT_FANOUT",
            "from": "KVInterlockRuntime",
            "to": "KV_STATUS_REPORT+MASTER_RECORDS_TRAVEL_REPORT",
            "state": "SPLIT_TO_TWO_BOUNDED_REPORTS",
            "artifact_sha256": sha256_json(kv_status_report),
        },
    ]

    travel_report = {
        "schema": TRAVEL_REPORT_SCHEMA,
        "probe_id": probe_id,
        "transition_id": f"ENDPOINT-FANOUT-{probe_id}",
        "run_id": f"RUN-{probe_id}",
        "lifecycle_state": "COMPLETED",
        "input_probe_sha256": probe_sha256,
        "hops": travel_hops,
        "final_kv_status_report_sha256": sha256_json(kv_status_report),
        "final_receipt_id": response["receipt"]["receipt_id"],
        "authority_effect": "NONE",
    }

    master_records_record = {
        "record_type": "governed_transition_relationship",
        "lifecycle_state": "COMPLETED",
        "transition_id": travel_report["transition_id"],
        "run_id": travel_report["run_id"],
        "probe_id": probe_id,
        "probe_sha256": probe_sha256,
        "travel_report": travel_report,
        "kv_interlock_status_report": {
            "schema": kv_status_report["schema"],
            "endpoint_status": kv_status_report["endpoint_status"],
            "report_sha256": travel_report["final_kv_status_report_sha256"],
            "request_id": kv_status_report["request_id"],
            "response_hash": kv_status_report["response_hash"],
        },
        "continuity": {
            "final_receipt_id": travel_report["final_receipt_id"],
        },
        "governance": {
            "admissibility_result": "ALLOW",
            "commit_time_validity": "VALID",
            "authority_effect": "NONE_TEST_FIXTURE",
        },
        "execution": {
            "verification_ref": f"test-only:kv-interlock:{kv_status_report['response_hash']}",
            "production_runtime_observed": False,
        },
    }

    custody_submission = {
        "schema_version": "1.0.0",
        "submission_type": "governed_transition_custody_candidate",
        "transition_id": travel_report["transition_id"],
        "run_id": travel_report["run_id"],
        "final_receipt_id": travel_report["final_receipt_id"],
        "record": master_records_record,
        "requested_result": {
            "custody_receipt_required": True,
            "master_record_ref_required": True,
            "reconstruction_result_required": True,
        },
        "authority_boundary": {
            "submission_is_custody": False,
            "local_persistence_is_custody": False,
            "client_may_self_issue_custody_receipt": False,
        },
    }

    master_records_sink = InMemoryMasterRecordsSink()
    custody_result = master_records_sink.submit(custody_submission)
    travel_report["master_records_submission_sha256"] = sha256_json(custody_submission)
    travel_report["master_records_result"] = custody_result
    travel_report["hops"].append(
        {
            "sequence": 5,
            "boundary": "MASTER_RECORDS_TEST_CUSTODY",
            "from": "MASTER_RECORDS_TRAVEL_REPORT",
            "to": "master-records-compatible-local-sink",
            "state": custody_result["custody_status"],
            "artifact_sha256": custody_result["record_sha256"],
        }
    )

    result = {
        "schema": "stegverse.endpoint-fanout-probe-result.v1",
        "test_mode": "LOCAL_ISOLATED_CONTRACT_INTEGRATION",
        "production_endpoint_claimed": False,
        "probe": probe,
        "reports": {
            "kv_interlock_endpoint_status": kv_status_report,
            "master_records_travel": travel_report,
        },
        "report_count": 2,
        "pass": (
            kv_status_report["endpoint_status"] == "PASS"
            and custody_result["custody_status"] == "TEST_ONLY_RECORDED"
            and len(travel_report["hops"]) == 5
        ),
        "authority_effect": "NONE_TEST_ONLY",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--value", default="stegverse-endpoint-fanout-probe")
    parser.add_argument("--probe-id", default="endpoint-fanout-001")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_probe(args.value, probe_id=args.probe_id)
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
