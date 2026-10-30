"""E0 test harness for the two credential layers (StegVerse-Labs/.github#3330 rev 1). Used by tests only.

Layer 1 is KVInterlockRuntime.handle (INTR_DEVICE_KV) and layer 2 is SkapLayer2Gate (KV_INTERNAL_SKAP_GATE).

Health is decided by the REAL pinned InTr evaluator, vendored byte-identical from StegVerse-org/LLM-adapter#430
@919851cb (merged as 649f0775 on LLM-adapter main; it carried #429 and #428) under runtime/intr_pinned/: layer 1 calls
llm_adapter.healthy_node_evaluator.evaluate (fdaa2005...1f58, require_admission=True) over the requesting node's OWN
transition ledger, which the deployment binds together with the genesis receipt it pins. There is no organization
ledger in this model and no crossing from an organization to LLM-adapter: a machine that has established itself as a
healthy node becomes an endpoint.

LC-KV-15: layer 1 derives the requester identity from the installed InTr transport and passes the observed transport
state. None of that is authentically observed today, so the production TRUST_ANCHORS are empty and the real path
FAILS_CLOSED. The E0 stand-ins here are:
* ``e0_health_ledger``: a scratch directory holding a node's own ledger in the pinned producers' receipt shapes (the
  genesis, then existence read-back, NODE_IDENTITY_BINDING, health check, health report and ingress admission), written
  by this harness directly (the pinned producers are never run). Never a real ledger; its receipts are E0 fixtures, not
  evidence.
* ``E0Transport``: stands in for the installed InTr transport. It authenticates only nodes the harness enrolled, with
  the node_identity_key it enrolled them with (a TEST-ONLY public seed through the vendored stdlib test signer,
  tests/fixtures/intr_pinned_test_only/ed25519_test_signer.py; no cryptography package).
* ``E0_TRUST_ANCHORS``: labelled E0_STANDIN_TEST_ONLY_NOT_EVIDENCE. They are in force only inside ``e0_trust_anchors()``
  or between ``enter_e0()`` and ``exit_e0()`` (setUpModule/tearDownModule). Importing this module puts nothing in force.
"""
from __future__ import annotations

import atexit
import base64
import contextlib
import hashlib
import json
import os
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
E0_LABEL = "E0_STANDIN_TEST_ONLY_NOT_EVIDENCE"
#: E0 node ids, in the node_id shape (^SV-NODE-[0-9A-Za-z]{8,64}$).
NODE = "SV-NODE-E0TEST0001"
OTHER_NODE = "SV-NODE-E0OTHER001"
NEVER_ENROLLED_NODE = "SV-NODE-E0NEVER001"
_SCRATCH: list[str] = []


@atexit.register
def _cleanup() -> None:
    for path in _SCRATCH:
        shutil.rmtree(path, ignore_errors=True)


def pinned() -> dict[str, Any]:
    """The vendored InTr modules, digest-checked (runtime.kv_interlock_endpoint.load_pinned_intr)."""
    modules, why = ep.load_pinned_intr()
    if modules is None:
        raise AssertionError(why)
    return modules


TEST_ONLY_DIR = ROOT / "tests" / "fixtures" / "intr_pinned_test_only"
#: The TEST-ONLY stdlib Ed25519 signer, byte-identical to LLM-adapter's tests/ed25519_test_signer.py.
TEST_ONLY_PINS = {
    "ed25519_test_signer.py": "sha256:3173bfcfca33129cd31942783b9e3e4c9380022f308f2fc31ccdda3dc2f6fe52",
}
_SIGNER_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "intr_pinned_test_only",
                              "ed25519_test_signer.py")
_SIGNER: list[Any] = []


def signer() -> Any:
    """Lane B's TEST-ONLY Ed25519 signer (stdlib), executed against the pinned ed25519_verify."""
    if not _SIGNER:
        import types
        verify = pinned()["ed25519_verify"]
        package = types.ModuleType("llm_adapter")
        package.__path__ = []
        package.ed25519_verify = verify
        module = types.ModuleType("e0_ed25519_test_signer")
        saved = {k: sys.modules.get(k) for k in ("llm_adapter", "llm_adapter.ed25519_verify")}
        try:
            sys.modules.update({"llm_adapter": package, "llm_adapter.ed25519_verify": verify})
            source = Path(_SIGNER_SOURCE).read_bytes()  # a constant path, so the finish-point closure resolves it
            if "sha256:" + hashlib.sha256(source).hexdigest() != TEST_ONLY_PINS["ed25519_test_signer.py"]:
                raise AssertionError("tests/fixtures/intr_pinned_test_only/ed25519_test_signer.py is not the vendored bytes")
            exec(compile(source, _SIGNER_SOURCE, "exec", dont_inherit=True), module.__dict__)  # noqa: S102
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        _SIGNER.append(module)
    return _SIGNER[0]


def e0_seed(node_id: str, salt: str = "") -> bytes:
    """A TEST-ONLY public seed derived from a label (not a secret, never a real key)."""
    return hashlib.sha256(f"e0-node-identity-key:{salt}{node_id}".encode()).digest()


def _mkdtemp(prefix: str) -> Path:
    path = tempfile.mkdtemp(prefix=prefix)
    _SCRATCH.append(path)
    return Path(path)


#: The E0 head attester of KV's own receipt ledger (a TEST-ONLY public seed; never a real key).
E0_ROUTE_SEED = hashlib.sha256(b"kv receipt ledger: TEST-ONLY head attester public seed").digest()
E0_ROUTE_KEY_ID = "test-kv-receipt-ledger-head-attester"


def e0_node_identity_key(node_id: str, salt: str = "") -> dict[str, Any]:
    """The 5-field node_identity_key object of the node's NODE_IDENTITY_BINDING receipt (algorithm, custody, key_id, node_id,
    public_key_b64): a public-key reference only. The public key is the TEST-ONLY seed's Ed25519 key."""
    seed = e0_seed(node_id, salt)
    return {"algorithm": "Ed25519", "custody": "TV/TVC", "key_id": "e0-standin:" + seed.hex()[:16], "node_id": node_id,
            "public_key_b64": base64.b64encode(signer().public_key(seed)).decode()}


class E0Transport:
    """Stand-in for the installed InTr DEVICE->KV transport. It authenticates an envelope's source only for a node the
    harness enrolled, and only when the envelope says the boundary proof was VERIFIED."""

    transport_id = "e0-standin-intr-transport"
    state = "INSTALLED"

    def __init__(self) -> None:
        self.enrolled: dict[str, dict[str, Any]] = {}

    def enroll(self, node_id: str, key: dict[str, Any] | None = None) -> None:
        self.enrolled[node_id] = {"key": key or e0_node_identity_key(node_id)}

    def authenticate(self, envelope: dict[str, Any]) -> dict[str, Any] | None:
        proof = envelope.get("boundary_proof") or {}
        node = proof.get("source_identity_ref")
        if proof.get("verification_state") != "VERIFIED" or node not in self.enrolled:
            return None
        return {"node_id": node, "node_identity_key": dict(self.enrolled[node]["key"])}


E0_TRANSPORT = E0Transport()

E0_TRUST_ANCHORS = {
    "label": E0_LABEL,
    "intr_transport": E0_TRANSPORT,
}
PRODUCTION_TRUST_ANCHORS = dict(ep.TRUST_ANCHORS)
_SAVED: list[dict[str, Any]] = []


def e0_route_ref() -> dict[str, Any]:
    return {"key_id": E0_ROUTE_KEY_ID, "algorithm": "Ed25519", "custody": "TV/TVC", "signs": "KV_RECORDED_RECEIPT_CHAIN_HEAD",
            "public_key_b64": base64.b64encode(signer().public_key(E0_ROUTE_SEED)).decode()}


def enter_e0() -> None:
    """Put the labelled E0 anchors in force (setUpModule). Paired with exit_e0."""
    _SAVED.append(dict(ep.TRUST_ANCHORS))
    ep.TRUST_ANCHORS.clear()
    ep.TRUST_ANCHORS.update(E0_TRUST_ANCHORS)


def exit_e0() -> None:
    previous = _SAVED.pop() if _SAVED else PRODUCTION_TRUST_ANCHORS
    ep.TRUST_ANCHORS.clear()
    ep.TRUST_ANCHORS.update(previous)


@contextlib.contextmanager
def e0_trust_anchors():
    enter_e0()
    try:
        yield E0_TRUST_ANCHORS
    finally:
        exit_e0()


@contextlib.contextmanager
def production_trust_anchors():
    """The production anchors (nothing observed), for negative tests inside an E0 module."""
    _SAVED.append(dict(ep.TRUST_ANCHORS))
    ep.TRUST_ANCHORS.clear()
    ep.TRUST_ANCHORS.update(PRODUCTION_TRUST_ANCHORS)
    try:
        yield ep.TRUST_ANCHORS
    finally:
        exit_e0()


#: The finish-point CLI with the labelled E0 anchors in force (tests only). The plain CLI runs under the production
#: anchors and refuses E0 evidence.
E0_FINISH_POINT_CLI = [sys.executable, "-c", (
    "import sys; sys.path.insert(0, 'tests'); import kv_two_layer_e0 as e0; e0.enter_e0(); "
    "from runtime import kv_skap_vault as kv; sys.exit(kv.main(sys.argv[1:]))")]


def _append(root: Path, cls: str, transition_id: str, evidence: dict[str, Any], epoch: int) -> dict[str, Any]:
    """Append one stegverse.repo-transition-receipt/v1 in the shape the pinned producers' emitter writes (the pinned
    code is never run here), at a supplied epoch."""
    hne = pinned()["healthy_node_evaluator"]
    head_path = root / "HEAD.json"
    prev = json.loads(head_path.read_text())["receipt_sha256"] if head_path.is_file() else None
    chain = hne.read_chain(root, LEDGER_REPOSITORY)[0] if prev else []
    body = {"schema": "stegverse.repo-transition-receipt/v1", "repository": LEDGER_REPOSITORY,
            "transition_id": transition_id, "transition_class": cls,
            "predecessor_state_sha256": chain[0]["successor_state_sha256"] if chain else hne.sha(None),
            "successor_state_sha256": hne.sha(dict(evidence)), "evidence": dict(evidence), "authority_effect": "NONE",
            "hb_reference": {"epoch": epoch, "derived_from_clock": False}, "ordering": "OSCILLATOR_HEARTBEAT_EPOCH_ONLY",
            "observed_at": None, "observed_at_is_descriptive_not_ordering": True, "previous_receipt_sha256": prev}
    receipt = {**body, "receipt_sha256": hne.sha(body)}
    (root / "receipts").mkdir(parents=True, exist_ok=True)
    (root / "receipts" / (receipt["receipt_sha256"][7:] + ".json")).write_text(
        json.dumps(receipt, sort_keys=True), encoding="utf-8")
    head_path.write_text(json.dumps({"repository": LEDGER_REPOSITORY, "receipt_sha256": receipt["receipt_sha256"]}),
                         encoding="utf-8")
    return receipt


def _write_node_chain(node_root: Path, node_id: str, *, key: dict[str, Any], bound_key: dict[str, Any], status: str,
                      admitted: bool, report: bool, superseded_by: str | None, foreign: bool,
                      healthy_ingress_cites: bool = True) -> tuple[str, str | None]:
    """The node's own ledger: a genesis, then (when report) existence, identity binding, health check, health report
    and the ingress record, in the pinned producers' shapes. Returns (genesis sha, first report's sha or None)."""
    m = pinned()
    hne = m["healthy_node_evaluator"]
    common, producer = m["node_receipt_common"], m["node_health_report_producer"]
    n = [31]

    def put(cls: str, evidence: dict[str, Any], suffix: str) -> str:
        n[0] += 1
        return _append(node_root, cls, f"{cls}:{node_id}:{suffix}", evidence, n[0])["receipt_sha256"]

    genesis = put("NODE_LEDGER_GENESIS_E0", {"schema": "e0.node-ledger-genesis/v1", "node_id": node_id,
                                              "label": E0_LABEL}, "genesis")
    if not report:
        return genesis, None
    existence = put(common.EXISTENCE_CLASS, {"schema": m["node_existence_readback"].EVIDENCE_SCHEMA,
                                             "node_id": node_id, "observation": {"node_identity_key": key}}, "e0")
    bound = put(common.BINDING_CLASS, {"schema": m["node_identity_binding_producer"].EVIDENCE_SCHEMA,
                                       "node_id": node_id, "key_ref": {"key_id": bound_key["key_id"]},
                                       "public_key_b64": bound_key["public_key_b64"]}, "e0")
    manifest = {"schema": producer.TRANSITION_MANIFEST_SCHEMA, "intended_action": producer.INTENDED_ACTION,
                "transition_class": producer.REPORT_CLASS, "inputs_are_receipts_on_chain": True,
                "producer": producer.PRODUCER, "producer_version": producer.PRODUCER_VERSION}

    def report_round(check_status: str, previous: str | None, k: int) -> str:
        check = put(common.HEALTH_CHECK_CLASS, {"schema": m["node_health_check_projection"].EVIDENCE_SCHEMA,
                                                "node_id": node_id, "status": check_status}, f"e0-{k}")
        if foreign:  # a report bare evaluate() accepts, but no pinned producer writes (no manifest, no citations)
            return put(producer.REPORT_CLASS, {"schema": producer.REPORT_SCHEMA, "node_id": node_id,
                                               "status": check_status, "label": "E0_FOREIGN_PRODUCER"}, f"e0-{k}")
        return put(producer.REPORT_CLASS, {
            "schema": producer.REPORT_SCHEMA, "node_id": node_id,
            "status": hne.HEALTHY if check_status == hne.HEALTHY else producer.UNHEALTHY,
            "observed_health_check_status": check_status, "transition_manifest": manifest,
            "previous_health_report_receipt_sha256": previous, "trigger": {"receipt_sha256": check},
            "evidence_receipts": {"authenticated_reciprocal_node_existence": existence,
                                  "node_identity_binding": bound, "health_check": check}}, f"e0-{k}")

    first = current = report_round(status, None, 1)
    if superseded_by is not None:
        current = report_round(superseded_by, first, 2)
    cls = hne.INGRESS_ADMITTED_CLASS if admitted else hne.INGRESS_REFUSED_CLASS
    put(cls, {"schema": "stegverse.node-ingress-record/v1", "node_endpoint": {"node_id": node_id},
              "evaluated_node_id": node_id, "healthy_node_established": admitted,
              "health_report_receipt_sha256": current}, "e0")
    return genesis, first


def e0_health_ledger(node_id: str, *, status: str = "HEALTHY", admitted: bool = True, report: bool = True,
                     superseded_by: str | None = None, foreign: bool = False, enroll: bool = True,
                     transport_key: dict[str, Any] | None = None, bound_key: dict[str, Any] | None = None,
                     pin_genesis: str | None = None) -> tuple[dict[str, Any], str | None]:
    """The deployment's node-chain binding for node_id: the node's own E0 ledger plus the genesis the deployment pins
    for it. Returns (source, first report sha).

    * report=False: the node chain has no NODE_HEALTH_REPORTED receipt (HEALTH_REPORT_MISSING).
    * superseded_by: a newer report with that status follows the first one, so citing the first is superseded.
    * foreign: the reports are not the pinned producer's (bare evaluate() ALLOWs them; KV's provenance check refuses).
    * enroll: the E0 transport authenticates node_id, with transport_key if given (else the node's key).
    * bound_key: the key the node's NODE_IDENTITY_BINDING receipt binds (default: the node's key).
    * pin_genesis: the genesis the deployment pins instead of the chain's own (a wrong pin).
    """
    key = e0_node_identity_key(node_id)
    node_root = _mkdtemp("e0-node-ledger-") / "ledger"
    genesis, first = _write_node_chain(node_root, node_id, key=key, bound_key=bound_key or key, status=status,
                                       admitted=admitted, report=report, superseded_by=superseded_by, foreign=foreign)
    if enroll:
        E0_TRANSPORT.enroll(node_id, transport_key or key)
    return {"kind": ep.NODE_CHAIN_SOURCE, "ledger_root": str(node_root),
            "genesis_receipt_sha256": pin_genesis or genesis}, first


def healthy_node_kwargs(node_id: str, **ledger: Any) -> dict[str, Any]:
    """Runtime kwargs binding an E0 node chain for node_id. The evaluator is the real pinned evaluate."""
    return {"healthy_node_chain": e0_health_ledger(node_id, **ledger)[0]}


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
    """Both gates wired together. Health is decided by the real pinned evaluate over an E0 node ledger (or by an injected evaluator, which the finish point refuses). It collects every receipt for evidence bundles."""

    def __init__(self, principal: str = "principal:test", node: str = NODE, evaluator: Any = None,
                 intr_edit: Any = None, chain: Any = "e0"):
        self.principal, self.node, self.n = principal, node, 0
        self.intr_edit = intr_edit
        self.layer1 = ep.KVInterlockRuntime(
            authority_validator=lambda ref, request, envelope: ref == "owner-assertion-1",
            policy_evaluator=lambda r: {"decision": "ALLOW_BOUNDED_CONTEXT", "granted_scope": list(r["requested_scope"]),
                                        "context": {}, "source_refs": [], "policy_profile": "test"},
            receipt_store=lambda receipt: "urn:test:" + receipt["receipt_id"], clock=lambda: NOW,
            healthy_node_evaluator=evaluator,
            healthy_node_chain=e0_health_ledger(node)[0] if chain == "e0" else chain)
        self.gate = SkapLayer2Gate(self.layer1)
        if node not in E0_TRANSPORT.enrolled:
            E0_TRANSPORT.enroll(node)
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
