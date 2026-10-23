"""E0 test harness for the two credential layers (StegVerse-Labs/.github#3330 rev 1). Used by tests only.

Layer 1 is KVInterlockRuntime.handle (INTR_DEVICE_KV) and layer 2 is SkapLayer2Gate (INTR_KV_SKAP).

``e0_standin_healthy_node_evaluator`` is a STAND-IN for the pinned InTr evaluator
(StegVerse-org/LLM-adapter llm_adapter.node_ingress_boundary.evaluate_requester_is_currently_admitted_healthy_node,
LC-KV-13/14). That evaluator is not implemented on any observed head: LLM-adapter main ece815b1 has no PR for it.
* The stand-in implements only the pinned interface. It carries the pinned identity so the finish-point evidence
  path can be exercised end to end at E0.
* It is never installed as a module and never resolved by the runtime. The runtime resolves only the real import
  path, and with that absent, layer 1 is a six-field FAIL_CLOSED.
* Real healthy-node receipts are UNKNOWN_NOT_AUTHENTICALLY_OBSERVED.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime import kv_interlock_endpoint as ep  # noqa: E402
from runtime import kv_skap_vault as kv  # noqa: E402
from runtime.kv_skap_layer2 import SkapLayer2Gate, kv_skap_transition  # noqa: E402

E0_EVIDENCE_SCHEMA = "stegverse.e0-standin.healthy-node-evidence/v1"
NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)


def healthy_evidence(node_ref: str, *, admitted: bool = True, healthy: bool = True) -> dict[str, Any]:
    return {"schema": E0_EVIDENCE_SCHEMA, "node_ref": node_ref, "admitted": admitted, "healthy": healthy,
            "ingress_receipt_sha256": kv.sha256_uri({"e0_standin_ingress": node_ref})}


def e0_standin_healthy_node_evaluator(evidence: Any, *, requester_node_ref: str) -> dict[str, Any]:
    if not isinstance(evidence, dict) or evidence.get("schema") != E0_EVIDENCE_SCHEMA \
            or evidence.get("node_ref") != requester_node_ref or evidence.get("admitted") is not True \
            or evidence.get("healthy") is not True:
        return {"disposition": "DENY", "failure_code": ep.HEALTHY_NODE_REFUSAL_CODE,
                "failed_predicate": ep.HEALTHY_NODE_PREDICATE,
                "required_evidence_or_repair": f"{requester_node_ref} is not a currently admitted healthy node",
                "retry_entrypoint": "llm_adapter.node_ingress_boundary (E0 stand-in)",
                "owning_existing_goal": "LC-KV-13/14", "next_attempt": "on the node's next healthy ingress"}
    body = {**ep._HEALTHY_RECEIPT_EXACT, "node_ref": requester_node_ref,
            "ingress_receipt_sha256": evidence["ingress_receipt_sha256"]}
    return {"disposition": "ALLOW", "healthy_node_receipt": {**body, "receipt_sha256": kv.sha256_uri(body)}}


# the stand-in answers to the pinned interface identity (never installed in sys.modules)
e0_standin_healthy_node_evaluator.__module__ = ep.PINNED_HEALTHY_NODE_EVALUATOR["module"]
e0_standin_healthy_node_evaluator.__qualname__ = ep.PINNED_HEALTHY_NODE_EVALUATOR["callable"]


def intr_receipt(transition_id: str, principal: str = "principal:test", outcome: str = "ADMITTED") -> dict[str, Any]:
    content = {"transition_id": transition_id, "admitted_by": "Interlock/InTr"}
    return {"schema": kv.INTR_RECEIPT_SCHEMA, "transition_id": transition_id, "transition_sequence": 1,
            "subject_or_correlation_id": principal, "transition_outcome": outcome, "prior_state_ref_or_hash": None,
            "required_evidence_manifest": [{
                "evidence_id": "intr_admission", "evidence_type": "INTR_TRANSITION_ADMISSION",
                "origin_transition_id": transition_id, "encoding": "canonical-json", "content": content,
                "sha256": hashlib.sha256(kv.canonical_json(content).encode()).hexdigest()}]}


def request_and_envelope(n: int, node: str, verification_state: str = "VERIFIED"):
    request = {"schema_version": "kv.interlock.request.v1", "operation": "REQUEST", "request_id": f"req-{n}",
               "requester": {"module": "KV", "component": "kv-skap-vault-test"}, "purpose": "Test.",
               "record_class": "KV_SKAP_VAULT", "requested_scope": ["skap_vault"],
               "minimum_necessary_justification": "Test.", "authority_ref": "owner-assertion-1",
               "disclosure_mode": "BOUNDED_CONTEXT"}
    envelope = {"schema": ep.ENVELOPE_SCHEMA, "protocol": "InTr", "packet_id": f"packet-{n}", "direction": "REQUEST",
                "source_role": "DEVICE", "next_role": "KV", "request_id": request["request_id"],
                "operation": "REQUEST", "payload_schema_version": ep.REQUEST_SCHEMA,
                "payload_hash": ep.sha256_uri(request), "sealed_material_ref": "urn:stegverse:sealed:test",
                "authority": {"authority_transfer": False, "transport_grants_execution_authority": False,
                              "model_output_grants_execution_authority": False, "credential_authority_effect": "NONE"},
                "boundary_proof": {"required": True, "source_identity_ref": node,
                                   "next_boundary_identity_ref": "kv:test", "verification_state": verification_state},
                "receipt_policy": {"receipt_required": True, "receipt_contains_payload_plaintext": False,
                                   "receipt_chain_required": True, "ambiguous_disposition": "FAIL_CLOSED"}}
    return request, envelope


class TwoLayers:
    """Both gates wired together with the E0 stand-in evaluator. It collects every receipt for evidence bundles."""

    def __init__(self, principal: str = "principal:test", node: str = "device:test:1", evaluator: Any = "standin",
                 intr_edit: Any = None):
        self.principal, self.node, self.n = principal, node, 0
        self.intr_edit = intr_edit
        self.layer1 = ep.KVInterlockRuntime(
            authority_validator=lambda ref, request, envelope: ref == "owner-assertion-1",
            policy_evaluator=lambda r: {"decision": "ALLOW_BOUNDED_CONTEXT", "granted_scope": list(r["requested_scope"]),
                                        "context": {}, "source_refs": [], "policy_profile": "test"},
            receipt_store=lambda receipt: "urn:test:" + receipt["receipt_id"], clock=lambda: NOW,
            healthy_node_evaluator=e0_standin_healthy_node_evaluator if evaluator == "standin" else evaluator)
        self.gate = SkapLayer2Gate(self.layer1)
        self.intr_receipts: list[dict[str, Any]] = []
        self.layer1_receipts: list[dict[str, Any]] = []

    def kv_access(self, *, evidence: Any = "healthy", verification_state: str = "VERIFIED") -> dict[str, Any]:
        self.n += 1
        request, envelope = request_and_envelope(self.n, self.node, verification_state)
        intr = intr_receipt(f"t{self.n}", self.principal)
        if self.intr_edit is not None:
            self.intr_edit(intr)
        self.intr_receipts.append(intr)
        out = self.layer1.handle(request, intr_envelope=envelope, intr_receipt_ref=kv.sha256_uri(intr),
                                 healthy_node_evidence=healthy_evidence(self.node) if evidence == "healthy" else evidence)
        if out.get("kv_access_receipt"):
            self.layer1_receipts.append(out["kv_access_receipt"])
        return out

    def kv_hash(self) -> str:
        out = self.kv_access()
        assert out["decision"] == "ALLOW_BOUNDED_CONTEXT", out
        return out["kv_access_receipt"]["receipt_hash"]

    def skap_hash(self, operation: str, subject: str, principal: str | None = None) -> str:
        out = self.gate.admit(kv_skap_transition(principal_ref=principal or self.principal, operation=operation,
                                                 subject_ref=str(subject), prior_receipt_hash=self.kv_hash()))
        assert out["disposition"] == "ALLOW", out
        return out["skap_access_receipt"]["receipt_hash"]

    def vault(self) -> "kv.KVSkapVault":
        return kv.KVSkapVault(self.principal, skap_gate=self.gate)

    # one gated call per vault operation; refusals inside the vault still raise VaultRefusal
    def bind(self, vault, **kw):
        return vault.bind_custody_key_reference(
            skap_access_receipt_hash=self.skap_hash("BIND_CUSTODY_KEY_REFERENCE", kw.get("custody_key_ref"),
                                                    vault.principal_ref), **kw)

    def grant(self, vault, **kw):
        return vault.grant_consent(skap_access_receipt_hash=self.skap_hash(
            "CONSENT_GRANT", kv.consent_subject(kw.get("projection_ids")), vault.principal_ref), **kw)

    def write(self, vault, **kw):
        return vault.write_projection(skap_access_receipt_hash=self.skap_hash(
            "SKAP_WRITE", kw.get("projection_id"), vault.principal_ref), **kw)

    def read(self, vault, **kw):
        return vault.read_projection(skap_access_receipt_hash=self.skap_hash(
            "SKAP_READ", kw.get("projection_id"), vault.principal_ref), **kw)

    def revoke(self, vault, **kw):
        return vault.revoke_consent(skap_access_receipt_hash=self.skap_hash(
            "CONSENT_REVOKE", kw.get("consent_receipt_hash"), vault.principal_ref), **kw)

    def reconstruct(self, exported):
        return kv.KVSkapVault.reconstruct(exported, skap_gate=self.gate, skap_access_receipt_hash=self.skap_hash(
            "RECONSTRUCT", exported.get("head"), exported.get("principal_ref")))

    def access_evidence(self) -> dict[str, Any]:
        return {"layer1_kv_access_receipts": list(self.layer1_receipts),
                "layer2_skap_access_receipts": self.gate.export_receipts()}
