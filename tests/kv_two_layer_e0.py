"""E0 test harness for the two credential layers (StegVerse-Labs/.github#3330 rev 1). Used by tests only.

Layer 1 is KVInterlockRuntime.handle (INTR_DEVICE_KV) and layer 2 is SkapLayer2Gate (INTR_KV_SKAP).

Health is decided by the REAL pinned InTr evaluator: runtime/intr_pinned/healthy_node_evaluator.py, vendored
byte-identical from StegVerse-org/LLM-adapter#428 @0b37fe3b (LC-KV-13/14), with require_admission=True.
* The only E0 stand-in is ``e0_health_ledger``. It writes a scratch node-exchange transition ledger (HEAD.json plus
  hash-addressed receipts) in a temporary directory, holding a NODE_HEALTH_REPORTED report and a
  NODE_INGRESS_ADMITTED admission.
* It stands in for the NODE_HEALTH_REPORTED producer, which does not exist yet (Lane B asked Coordination to assign
  one).
* It is never the real ledger, and its receipts are E0 test fixtures, not evidence.
* Real health reports are UNKNOWN_NOT_AUTHENTICALLY_OBSERVED. Without a bound ledger, layer 1 is a six-field
  FAIL_CLOSED.
"""
from __future__ import annotations

import atexit
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime import kv_interlock_endpoint as ep  # noqa: E402
from runtime import kv_skap_vault as kv  # noqa: E402
from runtime.kv_skap_layer2 import SkapLayer2Gate, kv_skap_transition  # noqa: E402

NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
LEDGER_REPOSITORY = "StegVerse-org/LLM-adapter"  # the pinned evaluator's expected ledger repository
_SCRATCH: list[str] = []


@atexit.register
def _cleanup() -> None:
    for path in _SCRATCH:
        shutil.rmtree(path, ignore_errors=True)


def _write_receipt(root: Path, previous: str | None, transition_class: str, evidence: dict[str, Any],
                   repository: str = LEDGER_REPOSITORY) -> str:
    body = {"schema": "stegverse.e0-standin.transition-receipt/v1", "repository": repository,
            "transition_class": transition_class, "previous_receipt_sha256": previous, "evidence": evidence,
            "label": "E0_STANDIN_TEST_LEDGER_NOT_EVIDENCE"}
    digest = kv.sha256_uri(body)
    (root / "receipts" / (digest[7:] + ".json")).write_text(json.dumps({**body, "receipt_sha256": digest}),
                                                            encoding="utf-8")
    return digest


def e0_health_ledger(node_id: str, *, status: str = "HEALTHY", admitted: bool = True, report: bool = True,
                     superseded_by: str | None = None, repository: str = LEDGER_REPOSITORY,
                     ) -> tuple[str, str | None]:
    """A scratch E0 ledger read by the real pinned evaluator. Returns (ledger_root, first report sha or None).

    * report=False: the chain has no NODE_HEALTH_REPORTED receipt, which is today's real state (HEALTH_REPORT_MISSING).
    * superseded_by: a newer report with that status follows the first one, so citing the first is superseded.
    """
    root = Path(tempfile.mkdtemp(prefix="e0-health-ledger-"))
    _SCRATCH.append(str(root))
    (root / "receipts").mkdir()
    head = _write_receipt(root, None, "LEDGER_GENESIS", {"label": "E0"}, repository)
    first = None
    if report:
        first = head = _write_receipt(root, head, "NODE_HEALTH_REPORTED", {
            "schema": "stegverse.node-health-report/v1", "node_id": node_id, "status": status}, repository)
        current = first
        if superseded_by is not None:
            current = head = _write_receipt(root, head, "NODE_HEALTH_REPORTED", {
                "schema": "stegverse.node-health-report/v1", "node_id": node_id, "status": superseded_by}, repository)
        head = _write_receipt(root, head, "NODE_INGRESS_ADMITTED" if admitted else "NODE_INGRESS_REFUSED", {
            "node_endpoint": {"node_id": node_id}, "healthy_node_established": admitted,
            "health_report_receipt_sha256": current}, repository)
    (root / "HEAD.json").write_text(json.dumps({"receipt_sha256": head}), encoding="utf-8")
    return str(root), first


def healthy_node_kwargs(node_id: str, **ledger: Any) -> dict[str, Any]:
    """Runtime kwargs binding an E0 health ledger for node_id. The evaluator is the real pinned one."""
    return {"healthy_node_ledger_root": e0_health_ledger(node_id, **ledger)[0]}


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
    """Both gates wired together. Health is decided by the real pinned evaluator over an E0 health ledger (or by an
    injected evaluator, which the finish point refuses). It collects every receipt for evidence bundles."""

    def __init__(self, principal: str = "principal:test", node: str = "device:test:1", evaluator: Any = None,
                 intr_edit: Any = None, ledger_root: Any = "e0"):
        self.principal, self.node, self.n = principal, node, 0
        self.intr_edit = intr_edit
        self.layer1 = ep.KVInterlockRuntime(
            authority_validator=lambda ref, request, envelope: ref == "owner-assertion-1",
            policy_evaluator=lambda r: {"decision": "ALLOW_BOUNDED_CONTEXT", "granted_scope": list(r["requested_scope"]),
                                        "context": {}, "source_refs": [], "policy_profile": "test"},
            receipt_store=lambda receipt: "urn:test:" + receipt["receipt_id"], clock=lambda: NOW,
            healthy_node_evaluator=evaluator,
            healthy_node_ledger_root=e0_health_ledger(node)[0] if ledger_root == "e0" else ledger_root)
        self.gate = SkapLayer2Gate(self.layer1)
        self.intr_receipts: list[dict[str, Any]] = []
        self.layer1_receipts: list[dict[str, Any]] = []

    def kv_access(self, *, evidence: Any = None, verification_state: str = "VERIFIED") -> dict[str, Any]:
        self.n += 1
        request, envelope = request_and_envelope(self.n, self.node, verification_state)
        intr = intr_receipt(f"t{self.n}", self.principal)
        if self.intr_edit is not None:
            self.intr_edit(intr)
        self.intr_receipts.append(intr)
        out = self.layer1.handle(request, intr_envelope=envelope, intr_receipt_ref=kv.sha256_uri(intr),
                                 healthy_node_evidence=evidence)
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
