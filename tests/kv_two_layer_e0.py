"""E0 test harness for the two credential layers (StegVerse-Labs/.github#3330 rev 1). Used by tests only.

Layer 1 is KVInterlockRuntime.handle (INTR_DEVICE_KV) and layer 2 is SkapLayer2Gate (INTR_KV_SKAP).

Health is decided by the REAL pinned InTr code, vendored byte-identical from StegVerse-org/LLM-adapter#432 @1cbad77e
under runtime/intr_pinned/: layer 1 calls llm_adapter.endpoint_ledger_anchor.evaluate_anchored (Lane B's anchored-root
check with LC-KV-16 inside: org ledger from the contract designation, identity proven by an Ed25519 signature under the
anchored node_identity_key, transport read from the node's NODE_INGRESS_ADMITTED receipt), which runs the unchanged
healthy_node_evaluator.evaluate (fdaa2005...1f58) with require_admission=True over an anchored node root only.

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
  the node_identity_key it enrolled them with, and hands over the node's identity proof (the node's signature over
  evaluate_anchored's identity_challenge, made with a TEST-ONLY public seed through the vendored stdlib test signer,
  tests/fixtures/intr_pinned_test_only/ed25519_test_signer.py; no cryptography package).
* the #431 contract designation: org_ledger_location.CONTRACT_PATH points at Lane B's fixture contract
  (tests/fixtures/intr_pinned_test_only/contract_with_431_repository_ledger_location.json) only while the E0 anchors are
  in force. The vendored production contract.json has no repository_ledger_location yet (ORG_LEDGER_LOCATION_NOT_DESIGNATED).
* the NODE_INGRESS_ADMITTED record says transport INTERLOCK_INTR, transport_state INSTALLED (E0: the boundary is
  NOT_YET_ENABLED on LLM-adapter main).
* EPHEMERAL anchors are StegOS-shaped generation records in the signed envelope, signed with an E0 seed whose key is not
  published. The vendored signers file is empty, so EPHEMERAL is FAIL_CLOSED NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED
  (owner TV/TVC), as in production. The signers file is never patched.
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


TEST_ONLY_DIR = ROOT / "tests" / "fixtures" / "intr_pinned_test_only"
#: Lane B's TEST-ONLY stdlib signer and #431 fixture contract, vendored byte-identical from LLM-adapter#432 @1cbad77e.
TEST_ONLY_PINS = {
    "ed25519_test_signer.py": "sha256:3173bfcfca33129cd31942783b9e3e4c9380022f308f2fc31ccdda3dc2f6fe52",
    "contract_with_431_repository_ledger_location.json":
        "sha256:b52ee0faa32db00d2f61a1f78a2f40380c4dcb212004d527a51b1e8fb05972d9",
}
E0_CONTRACT_431 = TEST_ONLY_DIR / "contract_with_431_repository_ledger_location.json"
_SIGNER: list[Any] = []


def _test_only_bytes(name: str) -> bytes:
    data = (TEST_ONLY_DIR / name).read_bytes()
    if "sha256:" + hashlib.sha256(data).hexdigest() != TEST_ONLY_PINS[name]:
        raise AssertionError(f"tests/fixtures/intr_pinned_test_only/{name} is not the vendored bytes")
    return data


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
            exec(compile(_test_only_bytes("ed25519_test_signer.py"), "ed25519_test_signer.py", "exec"),  # noqa: S102
                 module.__dict__)
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
    """The 5-field node_identity_key object of schemas/node-ledger-opened.v1.json (algorithm, custody, key_id, node_id,
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

    def enroll(self, node_id: str, key: dict[str, Any] | None = None, identity_proof: Any = None) -> None:
        self.enrolled[node_id] = {"key": key or e0_node_identity_key(node_id), "identity_proof": identity_proof}

    def authenticate(self, envelope: dict[str, Any]) -> dict[str, Any] | None:
        proof = envelope.get("boundary_proof") or {}
        node = proof.get("source_identity_ref")
        if proof.get("verification_state") != "VERIFIED" or node not in self.enrolled:
            return None
        enrolled = self.enrolled[node]
        return {"node_id": node, "node_identity_key": dict(enrolled["key"]),
                "identity_proof": dict(enrolled["identity_proof"]) if enrolled["identity_proof"] else None}


E0_TRANSPORT = E0Transport()

E0_TRUST_ANCHORS = {
    "label": E0_LABEL,
    "intr_transport": E0_TRANSPORT,
}
PRODUCTION_TRUST_ANCHORS = dict(ep.TRUST_ANCHORS)
_SAVED: list[dict[str, Any]] = []


_PRODUCTION_CONTRACT_PATH: list[Any] = []


def _set_contract(e0: bool) -> None:
    """The #431 designation stand-in: Lane B's fixture contract while E0 anchors are in force, else the vendored one."""
    location = pinned()["org_ledger_location"]
    if not _PRODUCTION_CONTRACT_PATH:
        _PRODUCTION_CONTRACT_PATH.append(location.CONTRACT_PATH)
    if e0:
        _test_only_bytes(E0_CONTRACT_431.name)
    location.CONTRACT_PATH = E0_CONTRACT_431 if e0 else _PRODUCTION_CONTRACT_PATH[0]


def enter_e0() -> None:
    """Put the labelled E0 anchors in force (setUpModule). Paired with exit_e0."""
    _SAVED.append(dict(ep.TRUST_ANCHORS))
    ep.TRUST_ANCHORS.clear()
    ep.TRUST_ANCHORS.update(E0_TRUST_ANCHORS)
    _set_contract(True)


def exit_e0() -> None:
    previous = _SAVED.pop() if _SAVED else PRODUCTION_TRUST_ANCHORS
    ep.TRUST_ANCHORS.clear()
    ep.TRUST_ANCHORS.update(previous)
    _set_contract(previous.get("label") == E0_LABEL)


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
    _set_contract(False)
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


E0_OPENED_SIGNER_KEY_ID = "e0-standin-node-ledger-opened-signer-NOT-PUBLISHED"


def e0_node_ledger_opened(genesis: dict[str, Any], signed: bool = True) -> dict[str, Any]:
    """An E0 stand-in for StegOS's generation record (schemas/node-ledger-opened-generation.v1.json) inside the signed
    envelope (schemas/node-ledger-opened-signed.v1.json). It carries no issuer fields (those exist only on the issued
    anchor). It is signed with a TEST-ONLY seed whose key is not published, so evaluate_anchored refuses it
    (NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED) while the TV/TVC signers file is empty. Not a StegOS record."""
    a = pinned()["endpoint_ledger_anchor"]
    g = genesis["evidence"]
    record = {"schema": a.GENERATION_SCHEMA, "transition_class": a.OPENED_CLASS, "disposition": "ALLOW",
              "emitted_by": a.OPENED_EMITTER, "emitted_at": "STEGOS_NODE_GENERATION", "node_id": g["node_id"],
              "node_identity_key": g["node_identity_key"], "endpoint_kind": a.EPHEMERAL, "node_kind": g.get("node_kind"),
              "ledger_lifetime": a.BOUNDED, "ledger_opened": True, "genesis_receipt_sha256": genesis["receipt_sha256"],
              "authority_effect": "NONE_RECORD_ONLY", "credential_authority_effect": "NONE", "label": E0_LABEL}
    record = {**record, "receipt_sha256": a.opened_record_sha256(record)}
    if not signed:  # the bare (unsigned) opened record that #432 @c2c57505 admitted (LC-KV-17)
        return record
    seed = e0_seed("node-ledger-opened-signer")
    return a.signed_opened(record, {"algorithm": "Ed25519", "key_id": E0_OPENED_SIGNER_KEY_ID,
                                    "signature_b64": signer().sign_b64(a.opened_signing_message(record), seed)})


def _write_node_chain(node_root: Path, org_ns: Path | None, node_id: str, *, kind: str, key: dict[str, Any],
                      status: str, admitted: bool, report: bool, superseded_by: str | None, foreign: bool,
                      anchored: bool, transport_installed: bool = True, opened_signed: bool = True) -> str | None:
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
                 e0_node_ledger_opened(opened["genesis"], opened_signed) if kind == a.EPHEMERAL else None)

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
    record = {"schema": "stegverse.node-ingress-record/v1", "node_endpoint": {"node_id": node_id},
              "evaluated_node_id": node_id, "healthy_node_established": admitted,
              "health_report_receipt_sha256": current}
    if transport_installed:  # E0: the node arrived over the installed InTr transport (NOT_YET_ENABLED on main)
        record.update(transport="INTERLOCK_INTR", transport_state="INSTALLED")
    put(cls, record, "e0")
    return first


def e0_health_ledger(node_id: str, *, status: str = "HEALTHY", admitted: bool = True, report: bool = True,
                     superseded_by: str | None = None, kind: str = "PERMANENT", foreign: bool = False,
                     anchored: bool = True, enroll: bool = True,
                     transport_key: dict[str, Any] | None = None, transport_installed: bool = True,
                     proof: str | None = "valid", opened_signed: bool = True) -> tuple[dict[str, Any], str | None]:
    """The deployment's ledger source for node_id: an E0 org-ledger git repository (contract location, pinned genesis)
    plus the node's own ledger, anchored to it with the pinned #432 code. Returns (source, first report sha).

    * kind: the node's endpoint_kind. PERMANENT (default) is what the finish point expects; EPHEMERAL is anchored by an
      E0 NODE_LEDGER_OPENED record.
    * report=False: the node chain has no NODE_HEALTH_REPORTED receipt (HEALTH_REPORT_MISSING).
    * superseded_by: a newer report with that status follows the first one, so citing the first is superseded.
    * foreign: the reports are not the pinned producer's (bare evaluate() ALLOWs them; evaluate_anchored refuses).
    * anchored=False: the node ledger is opened but never anchored to the org ledger.
    * enroll: the E0 transport authenticates node_id, with transport_key if given (else the genesis key).
    * transport_installed=False: the node's NODE_INGRESS_ADMITTED record names no installed InTr transport.
    * proof: "valid" (the node's signature over evaluate_anchored's identity_challenge), "other_key" (signed with another
      seed), "stale" (over another challenge) or None (the transport hands over no proof).
    """
    key = e0_node_identity_key(node_id)
    node_root = _mkdtemp("e0-node-ledger-") / "ledger"
    holder: dict[str, Any] = {}

    def populate(repo: Path) -> None:
        org_ns = Path(ep.healthy_node_ledger_root(repo))
        _org_genesis(org_ns)
        holder["first"] = _write_node_chain(node_root, org_ns, node_id, kind=kind, key=key, status=status,
                                            admitted=admitted, report=report, superseded_by=superseded_by,
                                            foreign=foreign, anchored=anchored, transport_installed=transport_installed,
                                            opened_signed=opened_signed)
        _seal_namespace(org_ns)
        holder["proof"] = e0_identity_proof(node_id, {"endpoint_kind": kind, "ledger_root": str(node_root)}, org_ns,
                                            proof)
    repo = _git_repo(populate=populate)
    if enroll:
        E0_TRANSPORT.enroll(node_id, transport_key or key, holder["proof"])
    return {"kind": ep.LEDGER_SOURCE_ANCHORED, "org_ledger_git_dir": repo,
            "endpoint": {"endpoint_kind": kind, "ledger_root": str(node_root)}}, holder["first"]


def e0_identity_proof(node_id: str, endpoint: dict[str, Any], org_ns: Path, mode: str | None = "valid") -> Any:
    """The node's stegverse.node-identity-proof/v1: its TEST-ONLY seed's signature over evaluate_anchored's
    identity_challenge for the current node-chain and org-ledger heads. When the root is not anchored there is no
    challenge; the proof then still names the node, so the anchor refusal is what layer 1 reports."""
    if mode is None:
        return None
    a = pinned()["endpoint_ledger_anchor"]
    head = json.loads((org_ns / "HEAD.json").read_text(encoding="utf-8"))["receipt_sha256"] \
        if (org_ns / "HEAD.json").exists() else None
    anchored = a.verify_anchor(node_id, endpoint=endpoint, org_ledger_root=org_ns, org_ledger_head_receipt_sha256=head)
    key = e0_node_identity_key(node_id)
    if anchored.get("disposition") != "ALLOW":
        return {"schema": a.IDENTITY_PROOF_SCHEMA, "node_id": node_id, "key_id": key["key_id"],
                "challenge_sha256": "sha256:" + "0" * 64, "signature_b64": ""}
    challenge = a.identity_challenge(anchored)
    if mode == "stale":
        challenge = {**challenge, "org_ledger_head_receipt_sha256": "sha256:" + "1" * 64}
    seed = e0_seed(node_id, "another-key:" if mode == "other_key" else "")
    return {"schema": a.IDENTITY_PROOF_SCHEMA, "node_id": node_id, "key_id": key["key_id"],
            "challenge_sha256": a.sha(a.identity_challenge(anchored) if mode != "stale" else challenge),
            "signature_b64": signer().sign_b64(a.identity_challenge_message(challenge), seed)}


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
