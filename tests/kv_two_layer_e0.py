"""E0 test harness for the two credential layers (StegVerse-Labs/.github#3330 rev 1). Used by tests only.

Layer 1 is KVInterlockRuntime.handle (INTR_DEVICE_KV) and layer 2 is SkapLayer2Gate (INTR_KV_SKAP).

Health is decided by the REAL pinned InTr evaluator: runtime/intr_pinned/healthy_node_evaluator.py, vendored
byte-identical from StegVerse-org/LLM-adapter (LC-KV-13/14), with require_admission=True.

LC-KV-15 (P1 DENY on cvk#258 @61104a57): layer 1 binds its ledger only by contract location at an observed
org-ledger head (or an anchored temporary node ledger), derives the requester identity from the installed InTr
transport, and passes the observed transport state. None of that is authentically observed today, so the production
TRUST_ANCHORS are empty and the real path FAILS_CLOSED. The E0 stand-ins here are:
* ``e0_health_ledger``: a scratch git repository whose refs/stegverse/organization-ledger commit holds the
  repository-ledger/StegVerse-org/LLM-adapter namespace (HEAD.json plus hash-addressed receipts), standing in for the
  #429 producer and the #431 onboarding. Never the real ledger; its receipts are E0 fixtures, not evidence.
* ``E0Transport``: stands in for the installed InTr transport. It authenticates only nodes the harness enrolled.
* ``e0_temporary_node_ledger`` / ``e0_node_ledger_opened``: a temporary node ledger and its NODE_LEDGER_OPENED anchor in
  the minimal shape KV checks, PENDING Lane B's schema, issued by an E0 stand-in issuer.
* ``E0_TRUST_ANCHORS``: labelled E0_STANDIN_TEST_ONLY_NOT_EVIDENCE. They are in force only inside ``e0_trust_anchors()``
  or between ``enter_e0()`` and ``exit_e0()`` (setUpModule/tearDownModule). Importing this module changes nothing.
"""
from __future__ import annotations

import atexit
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
_SCRATCH: list[str] = []


@atexit.register
def _cleanup() -> None:
    for path in _SCRATCH:
        shutil.rmtree(path, ignore_errors=True)


def _receipt_body(previous: str | None, transition_class: str, evidence: dict[str, Any],
                  repository: str = LEDGER_REPOSITORY) -> dict[str, Any]:
    return {"schema": "stegverse.e0-standin.transition-receipt/v1", "repository": repository,
            "transition_class": transition_class, "previous_receipt_sha256": previous, "evidence": evidence,
            "label": "E0_STANDIN_TEST_LEDGER_NOT_EVIDENCE"}


def _write_receipt(root: Path, previous: str | None, transition_class: str, evidence: dict[str, Any],
                   repository: str = LEDGER_REPOSITORY) -> str:
    body = _receipt_body(previous, transition_class, evidence, repository)
    digest = kv.sha256_uri(body)
    (root / "receipts" / (digest[7:] + ".json")).write_text(json.dumps({**body, "receipt_sha256": digest}),
                                                            encoding="utf-8")
    return digest


#: The E0 chain's genesis (deterministic), pinned only in E0_TRUST_ANCHORS.
E0_GENESIS = kv.sha256_uri(_receipt_body(None, "LEDGER_GENESIS", {"label": "E0"}))
PINNED_DIGESTS = {"evaluator_source_sha256": ep.PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"],
                  "producer_source_sha256": ep.PINNED_NODE_HEALTH_REPORT_PRODUCER["source_sha256"]}


def e0_node_identity_key(node_id: str) -> str:
    return "e0-node-identity-key:" + hashlib.sha256(node_id.encode()).hexdigest()[:16]


class E0Transport:
    """Stand-in for the installed InTr DEVICE->KV transport. It authenticates an envelope's source only for a node the
    harness enrolled, and only when the envelope says the boundary proof was VERIFIED."""

    transport_id = "e0-standin-intr-transport"
    state = "INSTALLED"

    def __init__(self) -> None:
        self.enrolled: dict[str, str] = {}

    def enroll(self, node_id: str) -> None:
        self.enrolled[node_id] = e0_node_identity_key(node_id)

    def authenticate(self, envelope: dict[str, Any]) -> dict[str, Any] | None:
        proof = envelope.get("boundary_proof") or {}
        node = proof.get("source_identity_ref")
        if proof.get("verification_state") != "VERIFIED" or node not in self.enrolled:
            return None
        return {"node_id": node, "node_identity_key": self.enrolled[node]}


E0_TRANSPORT = E0Transport()
_E0_ISSUED: set[str] = set()


def _e0_issuer(anchor: dict[str, Any]) -> bool:
    return anchor.get("receipt_sha256") in _E0_ISSUED


E0_TRUST_ANCHORS = {
    "label": E0_LABEL,
    "healthy_node_ledger_genesis_receipt_sha256": E0_GENESIS,
    "intr_transport": E0_TRANSPORT,
    "node_ledger_anchor_issuers": {"ORGANIZATION_LEDGER": _e0_issuer, "TV/TVC": _e0_issuer},
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


def _git_repo(with_ref: bool = True, populate: Any = None) -> str:
    repo = tempfile.mkdtemp(prefix="e0-org-ledger-repo-")
    _SCRATCH.append(repo)
    _run_git("init", "-q", cwd=repo)
    if populate is not None:
        populate(Path(repo))
    (Path(repo) / "README.e0").write_text(E0_LABEL, encoding="utf-8")
    _run_git("add", "-A", cwd=repo)
    _run_git("commit", "-q", "-m", E0_LABEL, cwd=repo)
    if with_ref:
        _run_git("update-ref", ep.HEALTHY_NODE_LEDGER_LOCATION["ref"], "HEAD", cwd=repo)
    return repo


def _write_chain(root: Path, node_id: str, *, status: str = "HEALTHY", admitted: bool = True, report: bool = True,
                 superseded_by: str | None = None, repository: str = LEDGER_REPOSITORY,
                 pinned_digests: Any = None) -> str | None:
    (root / "receipts").mkdir(parents=True)
    head = _write_receipt(root, None, "LEDGER_GENESIS", {"label": "E0"}, repository)
    first = None
    extra = {} if pinned_digests is None else {"pinned_digests": pinned_digests}
    if report:
        first = head = _write_receipt(root, head, "NODE_HEALTH_REPORTED", {
            "schema": "stegverse.node-health-report/v1", "node_id": node_id, "status": status, **extra}, repository)
        current = first
        if superseded_by is not None:
            current = head = _write_receipt(root, head, "NODE_HEALTH_REPORTED", {
                "schema": "stegverse.node-health-report/v1", "node_id": node_id, "status": superseded_by, **extra},
                repository)
        head = _write_receipt(root, head, "NODE_INGRESS_ADMITTED" if admitted else "NODE_INGRESS_REFUSED", {
            "node_endpoint": {"node_id": node_id}, "healthy_node_established": admitted,
            "health_report_receipt_sha256": current}, repository)
    (root / "HEAD.json").write_text(json.dumps({"receipt_sha256": head}), encoding="utf-8")
    return first


def e0_health_ledger(node_id: str, *, status: str = "HEALTHY", admitted: bool = True, report: bool = True,
                     superseded_by: str | None = None, repository: str = LEDGER_REPOSITORY,
                     enroll: bool = True) -> tuple[str, str | None]:
    """A scratch E0 git repository standing in for StegVerse-org/.github, whose refs/stegverse/organization-ledger
    commit holds the LLM-adapter namespace, read by the real pinned evaluator. Returns (repository, first report sha).

    * report=False: the chain has no NODE_HEALTH_REPORTED receipt, which is today's real state (HEALTH_REPORT_MISSING).
    * superseded_by: a newer report with that status follows the first one, so citing the first is superseded.
    * enroll: the E0 transport authenticates node_id.
    """
    holder: dict[str, Any] = {}

    def populate(repo: Path) -> None:
        holder["first"] = _write_chain(Path(ep.healthy_node_ledger_root(repo)), node_id, status=status,
                                       admitted=admitted, report=report, superseded_by=superseded_by,
                                       repository=repository)
    repo = _git_repo(populate=populate)
    if enroll:
        E0_TRANSPORT.enroll(node_id)
    return repo, holder["first"]


def e0_empty_ref_checkout() -> str:
    """A repository without refs/stegverse/organization-ledger, which is today's real state (#3255)."""
    return _git_repo(with_ref=False)


def e0_ref_without_namespace() -> str:
    """The org-ledger ref exists but carries no LLM-adapter namespace (#431 not onboarded)."""
    return _git_repo(with_ref=True)


def e0_scratch_ledger_root(node_id: str) -> str:
    """A bare scratch ledger directory (no git, no contract location), as cvk#258 @61104a57 accepted."""
    root = Path(tempfile.mkdtemp(prefix="e0-scratch-ledger-root-"))
    _SCRATCH.append(str(root))
    _write_chain(root / "repository-ledger" / "StegVerse-org" / "LLM-adapter", node_id)
    E0_TRANSPORT.enroll(node_id)
    return str(root)


def e0_temporary_node_ledger(node_id: str, *, pinned_digests: Any = "pinned", **chain: Any) -> tuple[str, str]:
    """A node's temporary ledger directory. Returns (ledger_root, genesis). pinned_digests="pinned" stamps the pinned
    evaluator and producer digests on its health receipts; None omits them."""
    root = Path(tempfile.mkdtemp(prefix="e0-temporary-node-ledger-"))
    _SCRATCH.append(str(root))
    _write_chain(root, node_id, pinned_digests=PINNED_DIGESTS if pinned_digests == "pinned" else pinned_digests,
                 **chain)
    E0_TRANSPORT.enroll(node_id)
    return str(root), E0_GENESIS


def e0_node_ledger_opened(node_id: str, *, node_identity_key: str | None = None, genesis: str = E0_GENESIS,
                          issuer: str = "ORGANIZATION_LEDGER", issued: bool = True) -> dict[str, Any]:
    """A NODE_LEDGER_OPENED anchor in the minimal shape KV checks (PENDING Lane B's schema). issued=False: an anchor no
    pinned issuer verifies."""
    body = {"schema": ep.NODE_LEDGER_OPENED_SCHEMA, "transition_class": ep.NODE_LEDGER_OPENED_CLASS,
            "node_id": node_id, "node_identity_key": node_identity_key or e0_node_identity_key(node_id),
            "genesis_receipt_sha256": genesis, "issuer": issuer,
            "issuer_receipt_ref": ("e0-standin-issuer-receipt:" if issued else "e0-never-issued:")
            + hashlib.sha256(node_id.encode()).hexdigest()[:16]}
    anchor = {**body, "receipt_sha256": ep.node_ledger_opened_digest(body)}
    if issued:
        _E0_ISSUED.add(anchor["receipt_sha256"])
    return anchor


def e0_temporary_source(node_id: str, **anchor: Any) -> dict[str, Any]:
    root, genesis = e0_temporary_node_ledger(node_id)
    return {"kind": ep.LEDGER_SOURCE_TEMPORARY, "ledger_root": root,
            "node_ledger_opened": e0_node_ledger_opened(node_id, **anchor)}


def healthy_node_kwargs(node_id: str, **ledger: Any) -> dict[str, Any]:
    """Runtime kwargs binding an E0 health ledger for node_id. The evaluator is the real pinned one."""
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
    """Both gates wired together. Health is decided by the real pinned evaluator over an E0 health ledger (or by an
    injected evaluator, which the finish point refuses). It collects every receipt for evidence bundles."""

    def __init__(self, principal: str = "principal:test", node: str = "device:test:1", evaluator: Any = None,
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
