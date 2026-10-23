"""E0 test harness for the two credential layers (StegVerse-Labs/.github#3330 rev 1). Used by tests only.

Layer 1 is KVInterlockRuntime.handle (INTR_DEVICE_KV) and layer 2 is SkapLayer2Gate (INTR_KV_SKAP).

Health is decided by the REAL pinned InTr code, vendored byte-identical from StegVerse-org/LLM-adapter#432 @c2c57505
under runtime/intr_pinned/: layer 1 calls llm_adapter.endpoint_ledger_anchor.evaluate_anchored (Lane B's anchored-root
check), which runs the unchanged healthy_node_evaluator.evaluate (fdaa2005...1f58) with require_admission=True over an
anchored node root only.

LC-KV-15: layer 1 binds the org ledger only by contract location at an observed org-ledger head (genesis pinned),
derives the requester identity from the installed InTr transport, and passes the observed transport state. None of
that is authentically observed today, so the production TRUST_ANCHORS are empty and the real path FAILS_CLOSED. The E0
stand-ins here are:
* ``e0_health_ledger``: a scratch git repository whose refs/stegverse/organization-ledger commit holds the
  repository-ledger/StegVerse-org/LLM-adapter namespace, plus a node's own ledger opened and anchored to it with the
  pinned #432 code (open_ledger, anchor) and health receipts in the pinned producers' shapes. PERMANENT by default (the
  node the finish point expects, LC-KV-13); EPHEMERAL (a StegOS-generated StegApp/StegBrowser/StegNode) uses an E0
  NODE_LEDGER_OPENED record. Never the real ledger; its receipts are E0 fixtures, not evidence.
* ``E0Transport``: stands in for the installed InTr transport. It authenticates only nodes the harness enrolled, with
  the node_identity_key it enrolled them with.
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
import subprocess
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
#: E0 node ids, in the #432 node_id shape (^SV-NODE-[0-9A-Za-z]{8,64}$).
NODE = "SV-NODE-E0TEST0001"
OTHER_NODE = "SV-NODE-E0OTHER001"
NEVER_ENROLLED_NODE = "SV-NODE-E0NEVER001"
_SCRATCH: list[str] = []


@atexit.register
def _cleanup() -> None:
    for path in _SCRATCH:
        shutil.rmtree(path, ignore_errors=True)


def pinned() -> dict[str, Any]:
    """The vendored #432 modules, digest-checked (runtime.kv_interlock_endpoint.load_pinned_intr)."""
    modules, why = ep.load_pinned_intr()
    if modules is None:
        raise AssertionError(why)
    return modules


def _mkdtemp(prefix: str) -> Path:
    path = tempfile.mkdtemp(prefix=prefix)
    _SCRATCH.append(path)
    return Path(path)


def _org_genesis(org_ns: Path) -> str:
    a = pinned()["endpoint_ledger_anchor"]
    return a.append_receipt(org_ns, a.GENESIS_CLASS, "REPOSITORY_LEDGER_INITIALIZATION:e0-standin",
                            a.sha({"repository": a.REPOSITORY, "ledger": None}),
                            {"schema": "stegverse.repository-ledger-initialization/v1", "repository": a.REPOSITORY,
                             "authority_effect": "NONE_E0_STANDIN", "label": E0_LABEL}, 32)["receipt_sha256"]


def _e0_genesis() -> str:
    with tempfile.TemporaryDirectory(prefix="e0-genesis-") as scratch:
        return _org_genesis(Path(scratch) / "ns")


#: The E0 org chain's genesis (deterministic). Not a trust anchor: layer 1 derives the genesis from the org ledger's own
#: receipt (LC-KV-15); tests compare against this value.
E0_GENESIS = _e0_genesis()


def e0_node_identity_key(node_id: str, salt: str = "") -> dict[str, Any]:
    """A #432-shaped node_identity_key (Ed25519, custody TV/TVC). E0 bytes, not a real key."""
    digest = hashlib.sha256(f"e0-node-identity-key:{salt}{node_id}".encode()).digest()
    return {"algorithm": "Ed25519", "key_id": "e0-standin:" + digest.hex()[:16], "node_id": node_id,
            "custody": "TV/TVC", "public_key_b64": base64.b64encode(digest).decode()}


class E0Transport:
    """Stand-in for the installed InTr DEVICE->KV transport. It authenticates an envelope's source only for a node the
    harness enrolled, and only when the envelope says the boundary proof was VERIFIED."""

    transport_id = "e0-standin-intr-transport"
    state = "INSTALLED"

    def __init__(self) -> None:
        self.enrolled: dict[str, dict[str, Any]] = {}

    def enroll(self, node_id: str, key: dict[str, Any] | None = None) -> None:
        self.enrolled[node_id] = key or e0_node_identity_key(node_id)

    def authenticate(self, envelope: dict[str, Any]) -> dict[str, Any] | None:
        proof = envelope.get("boundary_proof") or {}
        node = proof.get("source_identity_ref")
        if proof.get("verification_state") != "VERIFIED" or node not in self.enrolled:
            return None
        return {"node_id": node, "node_identity_key": dict(self.enrolled[node])}


E0_TRANSPORT = E0Transport()

E0_TRUST_ANCHORS = {
    "label": E0_LABEL,
    "intr_transport": E0_TRANSPORT,
}
PRODUCTION_TRUST_ANCHORS = dict(ep.TRUST_ANCHORS)
_SAVED: list[dict[str, Any]] = []


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


def _run_git(*args: str, cwd: str) -> None:
    subprocess.run(["git", "-c", "user.name=E0", "-c", "user.email=e0@invalid", "-c", "commit.gpgsign=false",
                    "-c", "init.defaultBranch=e0", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                        # fixed dates: the observed head (a commit id) is deterministic across E0 runs
                        "GIT_AUTHOR_DATE": "2026-10-23T12:00:00Z", "GIT_COMMITTER_DATE": "2026-10-23T12:00:00Z"})


def _seal_namespace(ns: Path) -> None:
    """Make the namespace committable: drop append locks and store HEAD.json's receipt_path relative."""
    for lock in ns.rglob("*.append.lock"):
        lock.unlink()
    for head in ns.rglob("HEAD.json"):
        body = json.loads(head.read_text(encoding="utf-8"))
        if isinstance(body.get("receipt_path"), str) and os.path.isabs(body["receipt_path"]):
            body["receipt_path"] = os.path.relpath(body["receipt_path"], head.parent)
            head.write_text(json.dumps(body, sort_keys=True), encoding="utf-8")


def _git_repo(with_ref: bool = True, populate: Any = None) -> str:
    repo = str(_mkdtemp("e0-org-ledger-repo-"))
    _run_git("init", "-q", cwd=repo)
    if populate is not None:
        populate(Path(repo))
    (Path(repo) / "README.e0").write_text(E0_LABEL, encoding="utf-8")
    _run_git("add", "-A", cwd=repo)
    _run_git("commit", "-q", "-m", E0_LABEL, cwd=repo)
    if with_ref:
        _run_git("update-ref", ep.HEALTHY_NODE_LEDGER_LOCATION["ref"], "HEAD", cwd=repo)
    return repo


def e0_node_ledger_opened(genesis: dict[str, Any]) -> dict[str, Any]:
    """An E0 stand-in for the NODE_LEDGER_OPENED record StegOS emits when it generates an EPHEMERAL node, in #432's
    stegverse.node-ledger-opened/v1 shape. Not a StegOS record."""
    a = pinned()["endpoint_ledger_anchor"]
    g = genesis["evidence"]
    record = {"schema": a.OPENED_SCHEMA, "event": a.OPENED_EVENT, "disposition": "ALLOW",
              "emitted_by": a.OPENED_EMITTER, "node_id": g["node_id"], "node_identity_key": g["node_identity_key"],
              "endpoint_kind": a.EPHEMERAL, "node_kind": g.get("node_kind"), "ledger_lifetime": a.BOUNDED,
              "ledger_genesis_sha256": genesis["receipt_sha256"], "label": E0_LABEL}
    return {**record, "record_sha256": a.opened_record_sha256(record)}


def _write_node_chain(node_root: Path, org_ns: Path | None, node_id: str, *, kind: str, key: dict[str, Any],
                      status: str, admitted: bool, report: bool, superseded_by: str | None, foreign: bool,
                      anchored: bool) -> str | None:
    """Open the node's own ledger and anchor it to the org namespace with the pinned #432 code, then append health
    receipts in the pinned producers' shapes. Returns the first report's receipt sha256 (or None)."""
    m = pinned()
    a, hne = m["endpoint_ledger_anchor"], m["healthy_node_evaluator"]
    common, producer = m["node_receipt_common"], m["node_health_report_producer"]
    node_kind = "StegNode" if kind == a.EPHEMERAL else None
    opened = a.open_ledger(node_root, node_id, kind, key, node_kind)
    if opened.get("disposition") != "ALLOW":
        raise AssertionError(opened)
    if anchored and org_ns is not None:
        a.anchor(node_root, org_ns, node_id,
                 e0_node_ledger_opened(opened["genesis"]) if kind == a.EPHEMERAL else None)

    def put(cls: str, evidence: dict[str, Any], suffix: str) -> str:
        chain = hne.read_chain(node_root)[0]
        return a.append_receipt(node_root, cls, f"{cls}:{node_id}:{suffix}", chain[0]["successor_state_sha256"],
                                evidence, a.epoch_of(chain))["receipt_sha256"]

    if not report:
        return None
    existence = put(common.EXISTENCE_CLASS, {"schema": m["node_existence_readback"].EVIDENCE_SCHEMA,
                                             "node_id": node_id, "observation": {"node_identity_key": key}}, "e0")
    bound = put(common.BINDING_CLASS, {"schema": m["node_identity_binding_producer"].EVIDENCE_SCHEMA,
                                       "node_id": node_id, "key_ref": {"key_id": key["key_id"]},
                                       "public_key_b64": key["public_key_b64"]}, "e0")
    manifest = {"schema": producer.TRANSITION_MANIFEST_SCHEMA, "intended_action": producer.INTENDED_ACTION,
                "transition_class": producer.REPORT_CLASS, "inputs_are_receipts_on_chain": True,
                "producer": producer.PRODUCER, "producer_version": producer.PRODUCER_VERSION}

    def report_round(check_status: str, previous: str | None, n: int) -> str:
        check = put(common.HEALTH_CHECK_CLASS, {"schema": m["node_health_check_projection"].EVIDENCE_SCHEMA,
                                                "node_id": node_id, "status": check_status}, f"e0-{n}")
        if foreign:  # a report bare evaluate() accepts, but no pinned producer writes (no manifest, no citations)
            return put(producer.REPORT_CLASS, {"schema": producer.REPORT_SCHEMA, "node_id": node_id,
                                               "status": check_status, "label": "E0_FOREIGN_PRODUCER"}, f"e0-{n}")
        return put(producer.REPORT_CLASS, {
            "schema": producer.REPORT_SCHEMA, "node_id": node_id,
            "status": hne.HEALTHY if check_status == hne.HEALTHY else producer.UNHEALTHY,
            "observed_health_check_status": check_status, "transition_manifest": manifest,
            "previous_health_report_receipt_sha256": previous, "trigger": {"receipt_sha256": check},
            "evidence_receipts": {"authenticated_reciprocal_node_existence": existence,
                                  "node_identity_binding": bound, "health_check": check}}, f"e0-{n}")

    first = current = report_round(status, None, 1)
    if superseded_by is not None:
        current = report_round(superseded_by, first, 2)
    cls = hne.INGRESS_ADMITTED_CLASS if admitted else hne.INGRESS_REFUSED_CLASS
    put(cls, {"schema": "stegverse.node-ingress-record/v1", "node_endpoint": {"node_id": node_id},
              "evaluated_node_id": node_id, "healthy_node_established": admitted,
              "health_report_receipt_sha256": current}, "e0")
    return first


def e0_health_ledger(node_id: str, *, status: str = "HEALTHY", admitted: bool = True, report: bool = True,
                     superseded_by: str | None = None, kind: str = "PERMANENT", foreign: bool = False,
                     anchored: bool = True, enroll: bool = True,
                     transport_key: dict[str, Any] | None = None) -> tuple[dict[str, Any], str | None]:
    """The deployment's ledger source for node_id: an E0 org-ledger git repository (contract location, pinned genesis)
    plus the node's own ledger, anchored to it with the pinned #432 code. Returns (source, first report sha).

    * kind: the node's endpoint_kind. PERMANENT (default) is what the finish point expects; EPHEMERAL is anchored by an
      E0 NODE_LEDGER_OPENED record.
    * report=False: the node chain has no NODE_HEALTH_REPORTED receipt (HEALTH_REPORT_MISSING).
    * superseded_by: a newer report with that status follows the first one, so citing the first is superseded.
    * foreign: the reports are not the pinned producer's (bare evaluate() ALLOWs them; evaluate_anchored refuses).
    * anchored=False: the node ledger is opened but never anchored to the org ledger.
    * enroll: the E0 transport authenticates node_id, with transport_key if given (else the genesis key).
    """
    key = e0_node_identity_key(node_id)
    node_root = _mkdtemp("e0-node-ledger-") / "ledger"
    holder: dict[str, Any] = {}

    def populate(repo: Path) -> None:
        org_ns = Path(ep.healthy_node_ledger_root(repo))
        _org_genesis(org_ns)
        holder["first"] = _write_node_chain(node_root, org_ns, node_id, kind=kind, key=key, status=status,
                                            admitted=admitted, report=report, superseded_by=superseded_by,
                                            foreign=foreign, anchored=anchored)
        _seal_namespace(org_ns)
    repo = _git_repo(populate=populate)
    if enroll:
        E0_TRANSPORT.enroll(node_id, transport_key or key)
    return {"kind": ep.LEDGER_SOURCE_ANCHORED, "org_ledger_git_dir": repo,
            "endpoint": {"endpoint_kind": kind, "ledger_root": str(node_root)}}, holder["first"]


def e0_empty_ref_checkout() -> str:
    """A repository without refs/stegverse/organization-ledger, which is today's real state (#3255)."""
    return _git_repo(with_ref=False)


def e0_ref_without_namespace() -> str:
    """The org-ledger ref exists but carries no LLM-adapter namespace (#431 not onboarded)."""
    return _git_repo(with_ref=True)


def e0_scratch_ledger_root(node_id: str) -> str:
    """A bare scratch directory holding an org namespace (no git, no contract location), as cvk#258 @61104a57
    accepted."""
    root = _mkdtemp("e0-scratch-ledger-root-")
    _org_genesis(Path(ep.healthy_node_ledger_root(root)))
    E0_TRANSPORT.enroll(node_id)
    return str(root)


def healthy_node_kwargs(node_id: str, **ledger: Any) -> dict[str, Any]:
    """Runtime kwargs binding an E0 ledger source for node_id. The evaluator is the real pinned evaluate_anchored."""
    return {"healthy_node_ledger_checkout": e0_health_ledger(node_id, **ledger)[0]}


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
    """Both gates wired together. Health is decided by the real pinned evaluate_anchored over an E0 anchored PERMANENT
    node ledger (or by an injected evaluator, which the finish point refuses). It collects every receipt for evidence bundles."""

    def __init__(self, principal: str = "principal:test", node: str = NODE, evaluator: Any = None,
                 intr_edit: Any = None, ledger_checkout: Any = "e0"):
        self.principal, self.node, self.n = principal, node, 0
        self.intr_edit = intr_edit
        self.layer1 = ep.KVInterlockRuntime(
            authority_validator=lambda ref, request, envelope: ref == "owner-assertion-1",
            policy_evaluator=lambda r: {"decision": "ALLOW_BOUNDED_CONTEXT", "granted_scope": list(r["requested_scope"]),
                                        "context": {}, "source_refs": [], "policy_profile": "test"},
            receipt_store=lambda receipt: "urn:test:" + receipt["receipt_id"], clock=lambda: NOW,
            healthy_node_evaluator=evaluator,
            healthy_node_ledger_checkout=e0_health_ledger(node)[0] if ledger_checkout == "e0" else ledger_checkout)
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
