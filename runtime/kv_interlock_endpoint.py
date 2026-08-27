from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable


REQUEST_SCHEMA = "kv.interlock.request.v1"
RESPONSE_SCHEMA = "kv.interlock.response.v1"
ENVELOPE_SCHEMA = "stegverse.kv-interlock.intr-envelope/v1"
ALLOWED_OPERATIONS = {"DISCOVER", "REQUEST", "COMMIT_CANDIDATE"}
ALLOWED_DECISIONS = {"ALLOW_BOUNDED_CONTEXT", "REVIEW_REQUIRED", "DENY", "FAIL_CLOSED"}
REQUEST_REQUIRED = {
    "schema_version", "operation", "request_id", "requester", "purpose",
    "record_class", "requested_scope", "minimum_necessary_justification",
    "authority_ref", "disclosure_mode",
}
REQUEST_ALLOWED = REQUEST_REQUIRED | {"time_scope", "candidate_writeback"}
ENVELOPE_REQUIRED = {
    "schema", "protocol", "packet_id", "direction", "source_role", "next_role",
    "request_id", "operation", "payload_schema_version", "payload_hash",
    "sealed_material_ref", "authority", "boundary_proof", "receipt_policy",
}
ENVELOPE_ALLOWED = ENVELOPE_REQUIRED | {
    "prior_receipt_hash", "issued_at", "expires_at", "nonce",
}
FORBIDDEN_FIELD_TOKENS = {
    "password", "secret", "credential", "credential_value", "token",
    "private_key", "private_key_material", "raw_secret", "seed", "mnemonic",
}


class KVInterlockRuntimeError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_uri(value: Any) -> str:
    return "sha256:" + sha256_hex(value)


def _is_sha256_uri(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") and all(
        ch in "0123456789abcdef" for ch in value[7:]
    )


def _unique_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(set(value))
        and all(isinstance(item, str) and item for item in value)
    )


def _contains_forbidden_name(name: str) -> bool:
    lower = name.lower()
    return any(token in lower for token in FORBIDDEN_FIELD_TOKENS)


def _context_is_safe(value: Any) -> bool:
    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and not _contains_forbidden_name(key)
            and _context_is_safe(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return all(_context_is_safe(child) for child in value)
    return isinstance(value, (str, int, float, bool)) or value is None


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise KVInterlockRuntimeError("invalid time value") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def response_hash(response: dict[str, Any]) -> str:
    value = copy.deepcopy(response)
    receipt = value.get("receipt")
    if not isinstance(receipt, dict):
        raise KVInterlockRuntimeError("response receipt missing")
    receipt.pop("response_hash", None)
    return sha256_hex(value)


class KVInterlockRuntime:
    """Fail-closed KV-INTERLOCK-v1 runtime core.

    The runtime does not establish transport identity itself. The caller must
    provide the exact already-verified DEVICE->KV InTr envelope and an opaque
    durable InTr receipt reference. Authority, policy, candidate persistence,
    and receipt persistence are injected boundaries.
    """

    def __init__(
        self,
        *,
        authority_validator: Callable[[str, dict[str, Any], dict[str, Any]], bool],
        policy_evaluator: Callable[[dict[str, Any]], dict[str, Any]],
        receipt_store: Callable[[dict[str, Any]], str],
        candidate_store: Callable[[dict[str, Any]], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.authority_validator = authority_validator
        self.policy_evaluator = policy_evaluator
        self.receipt_store = receipt_store
        self.candidate_store = candidate_store
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def handle(
        self,
        request: dict[str, Any],
        *,
        intr_envelope: dict[str, Any],
        intr_receipt_ref: str,
    ) -> dict[str, Any]:
        self._validate_request(request)
        self._validate_intr_admission(request, intr_envelope, intr_receipt_ref)

        try:
            authority_ok = self.authority_validator(
                request["authority_ref"], request, intr_envelope
            )
        except Exception:
            authority_ok = False
        if authority_ok is not True:
            return self._fail_closed(
                request, intr_receipt_ref, "AUTHORITY_NOT_ADMITTED"
            )

        try:
            decision = self.policy_evaluator(copy.deepcopy(request))
        except Exception:
            return self._fail_closed(
                request, intr_receipt_ref, "POLICY_EVALUATION_FAILED"
            )

        try:
            return self._apply_policy_decision(request, intr_receipt_ref, decision)
        except KVInterlockRuntimeError:
            return self._fail_closed(
                request, intr_receipt_ref, "POLICY_RESULT_REJECTED"
            )

    def _validate_request(self, request: dict[str, Any]) -> None:
        if not isinstance(request, dict):
            raise KVInterlockRuntimeError("request must be an object")
        if not REQUEST_REQUIRED.issubset(request):
            raise KVInterlockRuntimeError("request missing required fields")
        if not set(request).issubset(REQUEST_ALLOWED):
            raise KVInterlockRuntimeError("request contains unsupported fields")
        if request["schema_version"] != REQUEST_SCHEMA:
            raise KVInterlockRuntimeError("request schema mismatch")
        if request["operation"] not in ALLOWED_OPERATIONS:
            raise KVInterlockRuntimeError("unsupported operation")
        for field in (
            "request_id", "purpose", "record_class",
            "minimum_necessary_justification", "authority_ref",
        ):
            if not isinstance(request[field], str) or not request[field]:
                raise KVInterlockRuntimeError(f"{field} required")
        requester = request["requester"]
        if (
            not isinstance(requester, dict)
            or set(requester) != {"module", "component"}
            or not all(isinstance(requester[key], str) and requester[key] for key in requester)
        ):
            raise KVInterlockRuntimeError("requester invalid")
        if not _unique_strings(request["requested_scope"]):
            raise KVInterlockRuntimeError("requested_scope invalid")
        if any(_contains_forbidden_name(scope) for scope in request["requested_scope"]):
            raise KVInterlockRuntimeError("secret-bearing scope prohibited")
        if request["disclosure_mode"] not in {
            "BOUNDED_CONTEXT", "SOURCE_REFERENCE_ONLY", "ORIGINAL_ARTIFACT_REVIEW"
        }:
            raise KVInterlockRuntimeError("disclosure_mode invalid")
        candidate = request.get("candidate_writeback")
        if request["operation"] == "COMMIT_CANDIDATE":
            if (
                not isinstance(candidate, dict)
                or not isinstance(candidate.get("candidate_type"), str)
                or not candidate.get("candidate_type")
                or not isinstance(candidate.get("payload_ref"), str)
                or not candidate.get("payload_ref")
            ):
                raise KVInterlockRuntimeError("candidate_writeback required")
            if set(candidate) - {"candidate_type", "payload_ref", "requested_destination"}:
                raise KVInterlockRuntimeError("candidate_writeback fields invalid")
        elif candidate is not None:
            raise KVInterlockRuntimeError("candidate_writeback only allowed for COMMIT_CANDIDATE")

    def _validate_intr_admission(
        self,
        request: dict[str, Any],
        envelope: dict[str, Any],
        intr_receipt_ref: str,
    ) -> None:
        if not _is_sha256_uri(intr_receipt_ref):
            raise KVInterlockRuntimeError("verified InTr receipt reference required")
        if not isinstance(envelope, dict):
            raise KVInterlockRuntimeError("InTr envelope required")
        if not ENVELOPE_REQUIRED.issubset(envelope):
            raise KVInterlockRuntimeError("InTr envelope missing required fields")
        if not set(envelope).issubset(ENVELOPE_ALLOWED):
            raise KVInterlockRuntimeError("InTr envelope contains unsupported fields")
        exact = {
            "schema": ENVELOPE_SCHEMA,
            "protocol": "InTr",
            "direction": "REQUEST",
            "source_role": "DEVICE",
            "next_role": "KV",
            "payload_schema_version": REQUEST_SCHEMA,
        }
        for key, expected in exact.items():
            if envelope.get(key) != expected:
                raise KVInterlockRuntimeError(f"InTr envelope {key} mismatch")
        if envelope.get("request_id") != request["request_id"]:
            raise KVInterlockRuntimeError("InTr request binding mismatch")
        if envelope.get("operation") != request["operation"]:
            raise KVInterlockRuntimeError("InTr operation binding mismatch")
        if envelope.get("payload_hash") != sha256_uri(request):
            raise KVInterlockRuntimeError("InTr payload hash mismatch")
        if not isinstance(envelope.get("packet_id"), str) or not envelope["packet_id"]:
            raise KVInterlockRuntimeError("InTr packet id required")
        if not isinstance(envelope.get("sealed_material_ref"), str) or not envelope["sealed_material_ref"]:
            raise KVInterlockRuntimeError("sealed material reference required")
        authority = envelope.get("authority")
        if authority != {
            "authority_transfer": False,
            "transport_grants_execution_authority": False,
            "model_output_grants_execution_authority": False,
            "credential_authority_effect": "NONE",
        }:
            raise KVInterlockRuntimeError("InTr authority boundary mismatch")
        proof = envelope.get("boundary_proof")
        if (
            not isinstance(proof, dict)
            or set(proof) != {
                "required", "source_identity_ref",
                "next_boundary_identity_ref", "verification_state",
            }
            or proof.get("required") is not True
            or proof.get("verification_state") != "VERIFIED"
            or not isinstance(proof.get("source_identity_ref"), str)
            or not proof.get("source_identity_ref")
            or not isinstance(proof.get("next_boundary_identity_ref"), str)
            or not proof.get("next_boundary_identity_ref")
        ):
            raise KVInterlockRuntimeError("verified boundary proof required")
        receipt_policy = envelope.get("receipt_policy")
        if receipt_policy != {
            "receipt_required": True,
            "receipt_contains_payload_plaintext": False,
            "receipt_chain_required": True,
            "ambiguous_disposition": "FAIL_CLOSED",
        }:
            raise KVInterlockRuntimeError("InTr receipt policy mismatch")
        expires_at = envelope.get("expires_at")
        if expires_at is not None and _parse_time(expires_at) <= self.clock():
            raise KVInterlockRuntimeError("InTr envelope expired")

    def _apply_policy_decision(
        self,
        request: dict[str, Any],
        intr_receipt_ref: str,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(policy, dict):
            raise KVInterlockRuntimeError("policy result must be an object")
        decision = policy.get("decision")
        if decision not in ALLOWED_DECISIONS:
            raise KVInterlockRuntimeError("policy decision invalid")
        granted = policy.get("granted_scope", [])
        context = policy.get("context", {})
        source_refs = policy.get("source_refs", [])
        if not _unique_strings(granted):
            raise KVInterlockRuntimeError("granted scope invalid")
        if not set(granted).issubset(request["requested_scope"]):
            raise KVInterlockRuntimeError("policy scope expansion")
        if any(_contains_forbidden_name(scope) for scope in granted):
            raise KVInterlockRuntimeError("secret-bearing grant prohibited")
        if not isinstance(context, dict):
            raise KVInterlockRuntimeError("context must be object")
        if not set(context).issubset(granted):
            raise KVInterlockRuntimeError("context exceeds granted scope")
        if not _context_is_safe(context):
            raise KVInterlockRuntimeError("secret-like context prohibited")
        if not _unique_strings(source_refs):
            raise KVInterlockRuntimeError("source refs invalid")
        policy_profile = policy.get("policy_profile")
        if not isinstance(policy_profile, str) or not policy_profile:
            raise KVInterlockRuntimeError("policy profile required")

        if decision != "ALLOW_BOUNDED_CONTEXT":
            granted = []
            context = {}

        candidate_ref = None
        if request["operation"] == "COMMIT_CANDIDATE":
            if decision == "ALLOW_BOUNDED_CONTEXT":
                if self.candidate_store is None:
                    raise KVInterlockRuntimeError("candidate persistence unavailable")
                candidate_record = {
                    "schema": "kv.interlock.candidate.v1",
                    "request_id": request["request_id"],
                    "authority_ref": request["authority_ref"],
                    "candidate_type": request["candidate_writeback"]["candidate_type"],
                    "payload_ref": request["candidate_writeback"]["payload_ref"],
                    "requested_destination": request["candidate_writeback"].get("requested_destination"),
                    "intr_receipt_ref": intr_receipt_ref,
                    "canonical_state_changed": False,
                    "candidate_only": True,
                    "authority_effect": "NONE",
                }
                candidate_ref = self.candidate_store(candidate_record)
                if not isinstance(candidate_ref, str) or not candidate_ref:
                    raise KVInterlockRuntimeError("candidate store did not return opaque reference")
            context = {}

        return self._build_response(
            request=request,
            intr_receipt_ref=intr_receipt_ref,
            decision=decision,
            granted_scope=granted,
            context=context,
            source_refs=source_refs,
            policy_profile=policy_profile,
            redaction_profile=policy.get("redaction_profile"),
            writeback_candidate_ref=candidate_ref,
        )

    def _fail_closed(
        self,
        request: dict[str, Any],
        intr_receipt_ref: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._build_response(
            request=request,
            intr_receipt_ref=intr_receipt_ref,
            decision="FAIL_CLOSED",
            granted_scope=[],
            context={},
            source_refs=[intr_receipt_ref],
            policy_profile=f"KV-INTERLOCK-v1:{reason}",
            redaction_profile=None,
            writeback_candidate_ref=None,
        )

    def _build_response(
        self,
        *,
        request: dict[str, Any],
        intr_receipt_ref: str,
        decision: str,
        granted_scope: list[str],
        context: dict[str, Any],
        source_refs: list[str],
        policy_profile: str,
        redaction_profile: str | None,
        writeback_candidate_ref: str | None,
    ) -> dict[str, Any]:
        now = self.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        all_source_refs = list(dict.fromkeys([intr_receipt_ref, *source_refs]))
        receipt_seed = {
            "request_id": request["request_id"],
            "decision": decision,
            "timestamp": now,
            "intr_receipt_ref": intr_receipt_ref,
        }
        receipt: dict[str, Any] = {
            "receipt_id": "kv-interlock-receipt:" + sha256_hex(receipt_seed),
            "policy_profile": policy_profile,
            "authority_ref": request["authority_ref"],
            "requested_scope": list(request["requested_scope"]),
            "granted_scope": list(granted_scope),
            "source_refs": all_source_refs,
            "redaction_profile": redaction_profile,
            "decision": decision,
            "timestamp": now,
            "response_hash": "",
            "writeback_candidate_ref": writeback_candidate_ref,
        }
        response = {
            "schema_version": RESPONSE_SCHEMA,
            "request_id": request["request_id"],
            "decision": decision,
            "granted_scope": list(granted_scope),
            "context": copy.deepcopy(context),
            "source_refs": all_source_refs,
            "receipt": receipt,
        }
        receipt["response_hash"] = response_hash(response)
        persisted_ref = self.receipt_store(copy.deepcopy(receipt))
        if not isinstance(persisted_ref, str) or not persisted_ref:
            raise KVInterlockRuntimeError("receipt persistence failed")
        return response
