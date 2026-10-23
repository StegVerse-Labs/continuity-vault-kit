from __future__ import annotations

import copy
import hashlib
import importlib
import inspect
import json
from datetime import datetime, timezone
from typing import Any, Callable

from runtime.secret_field_policy import field_name_is_forbidden


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
REQUEST_ALLOWED = REQUEST_REQUIRED | {"time_scope", "candidate_writeback", "selector"}
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


# --- Layer 1 of the two credential layers (StegVerse-Labs/.github#3330 rev 1, LC-KV-07/08/10/11) -------------------
# KV is reachable only through InTr from a currently admitted healthy node. handle() is the DEVICE->KV InTr entry
# (INTR_DEVICE_KV). It first requires REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE, decided by the healthy-node
# evaluator that InTr owns: LC-KV-13/14, Lane B, StegVerse-org/LLM-adapter llm_adapter/healthy_node_evaluator.py at the
# pinned commit. It is vendored byte-identical in runtime/intr_pinned/ and verified by sha256 before every resolution.
# This runtime never decides health itself.
# * It calls the evaluator with require_admission=True over the node-exchange transition ledger bound to this runtime.
#   The ledger is never supplied by the requester.
# * It accepts only the evaluator's exact ALLOW shape for the InTr source identity.
# * Anything else is the six-field FAIL_CLOSED KV_ACCESS_LAYER1_REFUSED, carrying the evaluator's six fields as
#   health_evaluation.
# An admitted request mints one KV-access receipt into this runtime's own layer-1 receipt store. The separate layer-2
# gate (runtime/kv_skap_layer2.py) verifies against that store.
GOAL_REF = "KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324)"
LAYER1_REFUSAL_CODE = "KV_ACCESS_LAYER1_REFUSED"
LAYER1_BOUNDARY = "INTR_DEVICE_KV"
LAYER1_PREDICATE = "KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE"
LAYER1_RETRY = "runtime.kv_interlock_endpoint.KVInterlockRuntime.handle (StegVerse-Labs/continuity-vault-kit)"
KV_ACCESS_RECEIPT_SCHEMA = "stegverse.kv-access-receipt/v1"
HEALTHY_NODE_PREDICATE = "REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE"
HEALTHY_NODE_REFUSAL_CODE = "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY"
HEALTHY_NODE_RECEIPT_SCHEMA = "stegverse.healthy-node-evaluation/v1"  # the pinned evaluator's RESULT_SCHEMA
HEALTHY_NODE_GATE = "CURRENT_NODE_HEALTH"
#: The pinned InTr-owned evaluator (LC-KV-13/14). The interface is documented in docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md
#: at the commit below:
#:   evaluate(node_id, *, ledger_root, transport_state, report_receipt_sha256, require_admission, repository) -> dict
PINNED_HEALTHY_NODE_EVALUATOR = {
    "repository": "StegVerse-org/LLM-adapter",
    "commit": "0b37fe3b786a2de687235f5d9d146af49ffee9cd",
    "pull_request": "StegVerse-org/LLM-adapter#428 (draft)",
    "module": "llm_adapter.healthy_node_evaluator",
    "callable": "evaluate",
    "source_path": "llm_adapter/healthy_node_evaluator.py",
    "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
    "interface_doc": "docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md",
    "interface_doc_sha256": "sha256:757d697ca385f5d4709d8b26e51119330bb685b4770512312313fc42460bb76d",
    "vendored_module": "runtime.intr_pinned.healthy_node_evaluator",
    "owning_task": "LC-KV-13/LC-KV-14 (InTr and Mesh Destinations lane, StegVerse-org/.github#162)",
}
PINNED_HEALTHY_NODE_EVALUATOR_ID = (PINNED_HEALTHY_NODE_EVALUATOR["module"] + "."
                                    + PINNED_HEALTHY_NODE_EVALUATOR["callable"])
#: The exact fields of the pinned evaluator's ALLOW result when called with require_admission=True.
_HEALTHY_RECEIPT_EXACT = {
    "schema": HEALTHY_NODE_RECEIPT_SCHEMA,
    "disposition": "ALLOW",
    "predicate": HEALTHY_NODE_PREDICATE,
    "gate": HEALTHY_NODE_GATE,
    "healthy_node_established": True,
    "health_status": "HEALTHY",
    "admission_required": True,
    "authority_effect": "NONE_EVALUATION_ONLY",
}


def _file_sha256(path: Any) -> str | None:
    try:
        with open(path, "rb") as handle:
            return "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    except Exception:
        return None


def _callable_source_sha256(fn: Any) -> str | None:
    """sha256 of the bytes of the file that defines fn (the observed source, never the pin's claim)."""
    try:
        return _file_sha256(inspect.getsourcefile(fn))
    except Exception:
        return None


def resolve_pinned_healthy_node_evaluator() -> tuple[Callable[..., Any] | None, str]:
    """(the pinned evaluator, "") when the vendored bytes re-derive the pinned sha256, else (None, why not)."""
    try:
        module = importlib.import_module("runtime.intr_pinned.healthy_node_evaluator")
    except Exception as exc:
        return None, f"the vendored pinned evaluator does not import ({type(exc).__name__})"
    observed = _file_sha256(getattr(module, "__file__", None))
    if observed != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"]:
        return None, (f"the vendored evaluator source hashes to {observed}, not the pinned "
                      f"{PINNED_HEALTHY_NODE_EVALUATOR['source_sha256']}")
    candidate = getattr(module, PINNED_HEALTHY_NODE_EVALUATOR["callable"], None)
    return (candidate, "") if callable(candidate) else (None, "the vendored evaluator has no evaluate callable")


def evaluator_identity(evaluator: Any) -> str:
    module = getattr(evaluator, "__module__", "?")
    if module == PINNED_HEALTHY_NODE_EVALUATOR["vendored_module"]:
        module = PINNED_HEALTHY_NODE_EVALUATOR["module"]
    return f"{module}.{getattr(evaluator, '__qualname__', type(evaluator).__name__)}"


def layer1_refusal(request: Any, cause: str, detail: str, *, predicate: str = LAYER1_PREDICATE,
                   failure_class: str = "B", next_attempt: str | None = None,
                   health_evaluation: Any = None) -> dict[str, Any]:
    """Six-field FAIL_CLOSED for layer 1, returned (never raised) by handle()."""
    request_id = request.get("request_id") if isinstance(request, dict) else None
    return {
        "schema_version": RESPONSE_SCHEMA,
        "request_id": request_id,
        "decision": "FAIL_CLOSED",
        "disposition": "FAIL_CLOSED",
        "layer": LAYER1_BOUNDARY,
        "failure_code": LAYER1_REFUSAL_CODE,
        "failed_predicate": predicate,
        "required_evidence_or_repair": f"{cause}: {detail}",
        "retry_entrypoint": LAYER1_RETRY,
        "owning_existing_goal": GOAL_REF,
        "next_attempt": next_attempt or "on the next DEVICE->KV InTr transition that carries the repair",
        "failure_class": failure_class,
        "refusal_cause": cause,
        "granted_scope": [],
        "context": {},
        "kv_access_receipt": None,
        "health_evaluation": health_evaluation,
        "authority_effect": "NONE",
    }


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


def _contains_forbidden_name(name: str, value: Any = None) -> bool:
    return field_name_is_forbidden(name, value, FORBIDDEN_FIELD_TOKENS)


def _context_is_safe(value: Any) -> bool:
    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and not _contains_forbidden_name(key, child)
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
    projection = {
        "schema_version": response.get("schema_version"),
        "request_id": response.get("request_id"),
        "decision": response.get("decision"),
        "granted_scope": response.get("granted_scope"),
        "context": response.get("context"),
        "source_refs": response.get("source_refs"),
    }
    return sha256_hex(projection)


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
        healthy_node_evaluator: Callable[..., Any] | None = None,
        healthy_node_ledger_root: Any = None,
    ) -> None:
        self.authority_validator = authority_validator
        self.policy_evaluator = policy_evaluator
        self.receipt_store = receipt_store
        self.candidate_store = candidate_store
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        # Layer 1 consumes the InTr-owned evaluator; it never supplies one of its own. An injected evaluator (tests
        # only) is recorded with its own identity and source digest, never with the pin's.
        if healthy_node_evaluator is None:
            healthy_node_evaluator, self._evaluator_unavailable = resolve_pinned_healthy_node_evaluator()
        else:
            self._evaluator_unavailable = ""
        self.healthy_node_evaluator = healthy_node_evaluator
        # The node-exchange transition ledger the evaluator reads, bound by KV, never supplied by a requester.
        self.healthy_node_ledger_root = healthy_node_ledger_root
        self._kv_access_receipts: dict[str, dict[str, Any]] = {}

    def verify_kv_access_receipt(self, receipt_hash: Any) -> dict[str, Any] | None:
        """The layer-1 receipt this runtime minted under receipt_hash, re-derived, or None. Layer 2 calls this."""
        receipt = self._kv_access_receipts.get(receipt_hash) if isinstance(receipt_hash, str) else None
        if receipt is None:
            return None
        if sha256_uri({k: v for k, v in receipt.items() if k != "receipt_hash"}) != receipt_hash:
            return None
        return copy.deepcopy(receipt)

    def _healthy_node(self, request: dict[str, Any], envelope: dict[str, Any],
                      evidence: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """(the pinned evaluator's verified ALLOW, None) or (None, six-field refusal).

        ``evidence`` is what the requester may cite: None, or {"health_report_receipt_sha256": <sha256>}. Health is
        decided only by the evaluator over the KV-bound ledger.
        """
        node_ref = envelope["boundary_proof"]["source_identity_ref"]
        pin = PINNED_HEALTHY_NODE_EVALUATOR
        if self.healthy_node_evaluator is None:
            return None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, (
                f"no {HEALTHY_NODE_PREDICATE} evaluator is available ({self._evaluator_unavailable}); the pinned "
                f"InTr evaluator is {pin['repository']}@{pin['commit'][:8]}:{pin['source_path']} "
                f"({pin['source_sha256']}), and KV never asserts a node's health itself"),
                predicate=HEALTHY_NODE_PREDICATE,
                next_attempt="when runtime/intr_pinned/ is re-vendored at a pinned LLM-adapter commit (LC-KV-13/14)")
        cite = None
        if evidence is not None:
            cite = evidence.get("health_report_receipt_sha256") if isinstance(evidence, dict) else evidence
            if not (isinstance(evidence, dict) and set(evidence) <= {"health_report_receipt_sha256"}
                    and (cite is None or _is_sha256_uri(cite))):
                return None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, (
                    "healthy_node_evidence may only cite health_report_receipt_sha256 (a sha256 receipt address); "
                    "health itself is never caller-asserted"), predicate=HEALTHY_NODE_PREDICATE, failure_class="C")
        try:
            out = self.healthy_node_evaluator(node_ref, ledger_root=self.healthy_node_ledger_root,
                                              transport_state="INSTALLED", report_receipt_sha256=cite,
                                              require_admission=True)
        except Exception as exc:  # an evaluator fault is a refusal, never an admission
            out = {"disposition": "FAIL_CLOSED", "failure_code": HEALTHY_NODE_REFUSAL_CODE, "reason": "EVALUATOR_FAULT",
                   "required_evidence_or_repair": f"the evaluator raised {type(exc).__name__}"}
        if not isinstance(out, dict) or out.get("disposition") != "ALLOW":
            evaluation = copy.deepcopy(out) if isinstance(out, dict) else None
            reason = (evaluation or {}).get("reason")
            # No NODE_HEALTH_REPORTED producer exists yet, and no ledger is bound: class B (a producer to assign).
            failure_class = "B" if reason in ("HEALTH_REPORT_MISSING", "LEDGER_HEAD_UNREADABLE") else "C"
            return None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, (
                f"the pinned healthy-node evaluator did not ALLOW {node_ref!r}"
                + (f" ({(evaluation or {}).get('disposition')} {reason}: "
                   f"{(evaluation or {}).get('required_evidence_or_repair')})" if evaluation else "")),
                predicate=HEALTHY_NODE_PREDICATE, failure_class=failure_class, health_evaluation=evaluation,
                next_attempt=(evaluation or {}).get("next_attempt") or "on the node's next receipted HEALTHY report")
        problem = None
        if any(out.get(k) != v for k, v in _HEALTHY_RECEIPT_EXACT.items()):
            problem = "the evaluator's ALLOW does not carry the pinned interface fields (require_admission=True)"
        elif out.get("node_id") != node_ref:
            problem = "the evaluator's ALLOW names another node than the InTr source identity"
        elif not _is_sha256_uri(out.get("health_report_receipt_sha256")) \
                or not _is_sha256_uri(out.get("chain_head_receipt_sha256")):
            problem = "the evaluator's ALLOW binds no receipted health report on a ledger chain"
        elif cite is not None and out.get("health_report_receipt_sha256") != cite:
            problem = "the evaluator's ALLOW is for another health report than the one cited"
        if problem:
            return None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, problem,
                                        predicate=HEALTHY_NODE_PREDICATE, failure_class="C",
                                        health_evaluation=copy.deepcopy(out))
        return copy.deepcopy(out), None

    def _mint_kv_access_receipt(self, request: dict[str, Any], envelope: dict[str, Any], intr_receipt_ref: str,
                                healthy: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        body = {
            "schema": KV_ACCESS_RECEIPT_SCHEMA,
            "boundary": LAYER1_BOUNDARY,
            "layer": 1,
            "hop_index": 0,
            "from_role": "DEVICE",
            "to_role": "KV",
            "minted_by": "KVInterlockRuntime.handle",
            "request_id": request["request_id"],
            "operation": request["operation"],
            "packet_id": envelope["packet_id"],
            "intr_receipt_ref": intr_receipt_ref,
            "requester_node_ref": envelope["boundary_proof"]["source_identity_ref"],
            "kv_boundary_ref": envelope["boundary_proof"]["next_boundary_identity_ref"],
            "healthy_node_predicate": HEALTHY_NODE_PREDICATE,
            "healthy_node_receipt": healthy,
            "healthy_node_evaluator": evaluator_identity(self.healthy_node_evaluator),
            "healthy_node_evaluator_source_sha256": _callable_source_sha256(self.healthy_node_evaluator),
            "granted_scope": list(response["granted_scope"]),
            "response_hash": response["receipt"]["response_hash"],
            "prior_receipt_hash": None,
            "authority_effect": "NONE",
        }
        receipt = {**body, "receipt_hash": sha256_uri(body)}
        self._kv_access_receipts[receipt["receipt_hash"]] = copy.deepcopy(receipt)
        return receipt

    def handle(
        self,
        request: dict[str, Any],
        *,
        intr_envelope: dict[str, Any],
        intr_receipt_ref: str,
        healthy_node_evidence: Any = None,
    ) -> dict[str, Any]:
        """Layer 1 (INTR_DEVICE_KV). Every refusal is returned as a six-field FAIL_CLOSED, never raised."""
        try:
            self._validate_request(request)
            self._validate_intr_admission(request, intr_envelope, intr_receipt_ref)
        except KVInterlockRuntimeError as exc:
            return layer1_refusal(request, "INTR_DEVICE_KV_TRANSITION_NOT_ADMITTED", str(exc), failure_class="C")
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            return layer1_refusal(request, "INTR_DEVICE_KV_TRANSITION_MALFORMED", f"{type(exc).__name__}: {exc}",
                                  failure_class="C")
        healthy, refusal = self._healthy_node(request, intr_envelope, healthy_node_evidence)
        if refusal is not None:
            return refusal
        try:
            response = self._decide(request, intr_envelope, intr_receipt_ref)
        except KVInterlockRuntimeError as exc:
            return layer1_refusal(request, "KV_INTERLOCK_RECEIPT_NOT_PERSISTED", str(exc), failure_class="A")
        if response["decision"] == "ALLOW_BOUNDED_CONTEXT":
            response["kv_access_receipt"] = self._mint_kv_access_receipt(
                request, intr_envelope, intr_receipt_ref, healthy, response)
        return response

    def _decide(self, request: dict[str, Any], intr_envelope: dict[str, Any],
                intr_receipt_ref: str) -> dict[str, Any]:
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
        selector = request.get("selector")
        if selector is not None:
            if request["operation"] != "REQUEST":
                raise KVInterlockRuntimeError("selector only allowed for REQUEST")
            if (
                not isinstance(selector, dict)
                or set(selector) != {"directory_id", "canonical_path"}
                or not all(isinstance(selector.get(key), str) and selector.get(key) for key in ("directory_id", "canonical_path"))
            ):
                raise KVInterlockRuntimeError("selector invalid")
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
