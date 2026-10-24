"""E0 test harness for the two credential layers (StegVerse-Labs/.github#3330 rev 1). Used by tests only.

Layer 1 is KVInterlockRuntime.handle (INTR_DEVICE_KV) and layer 2 is SkapLayer2Gate (INTR_KV_SKAP).

Health is decided by the REAL pinned InTr code, vendored byte-identical from StegVerse-org/LLM-adapter#432 @eecf4843
(re-pinned to cvk#263 @9bc54d05) under runtime/intr_pinned/: layer 1 calls
llm_adapter.endpoint_ledger_anchor.evaluate_anchored (Lane B's anchored-root check with LC-KV-16 inside: org ledger from the contract designation at the contract-pinned genesis with an append-route
head attestation, identity proven by an Ed25519 signature under the anchored node_identity_key, health and admission by
the unchanged healthy_node_evaluator.evaluate (fdaa2005...1f58, require_admission=True), then transport read from the
node's NODE_INGRESS_ADMITTED receipt and counted only with its InTr path pair on the authenticated org chain).

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
* the #431 contract designation: org_ledger_location.CONTRACT_PATH points at Lane B's fixture contract with the pinned
  test genesis (tests/fixtures/intr_pinned_test_only/contract_with_431_location_and_pinned_genesis.json; the org namespace
  starts at Lane B's org_ledger_test_genesis.json) only while the E0 anchors are in force. The vendored production
  contract.json has no repository_ledger_location yet (ORG_LEDGER_LOCATION_NOT_DESIGNATED).
* the admitted append route: while the E0 anchors are in force, org_ledger_location.load_head_signers returns the
  TEST-ONLY route attester of Lane B's tests/org_ledger_harness.py (same public seed and key_id), and the deployment
  source carries that attester's head attestation for the store the harness published (``e0_attest``). Production
  publishes none (org-ledger-head-signers.v1.json is empty): MERGE_APPEND_PATH_NOT_ADMITTED.
* the NODE_INGRESS_ADMITTED record says transport INTERLOCK_INTR, transport_state INSTALLED (E0: the boundary is
  NOT_YET_ENABLED on LLM-adapter main), and its signal is carried by an InTr path pair: the INTR_MESH_PATH_TRANSFER on
  the sender's own ledger and the digest-only INTR_MESH_PATH_INGRESS on the org namespace after the anchor (#432
  @eecf4843: nothing is retained on the org ledger).
* the PERMANENT node's own storage endpoint (#432 @eecf4843, Q-PERMANENT-REPOSITORY-LEDGER, #167 comment 6374130335):
  the endpoint carries the node's designation (Lane B's TEST-ONLY node.designation.json for this node and genesis) and
  its recorded head. While the E0 anchors are in force, endpoint_ledger_designation's NODE_STORAGE_ENDPOINT reader is a
  TEST-ONLY stub that reads the node's read-back root (#432's tests/test_endpoint_ledger_anchor.node_reader_stub), and
  ORG_CROSSING_READER reads the E0 org namespace. Production has neither: PERMANENT is FAIL_CLOSED
  NODE_STORAGE_ENDPOINT_READER_NOT_DOCUMENTED (class B).
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
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
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
#: Lane B's TEST-ONLY stdlib signer, #431 fixture contracts, org test genesis and org-ledger harness, vendored
#: byte-identical from LLM-adapter#432 @c4cfc145 and @eecf4843 (org_ledger_harness.py is kept for provenance and never executed: it
#: imports tests.ed25519_test_signer; e0_attest and the E0 route below follow it with the same seed and key_id).
TEST_ONLY_PINS = {
    "ed25519_test_signer.py": "sha256:3173bfcfca33129cd31942783b9e3e4c9380022f308f2fc31ccdda3dc2f6fe52",
    "contract_with_431_repository_ledger_location.json":
        "sha256:d97cd4dc978c7ea02f41137dc85bbf5eb74b2ea6595bc58513be57b4c125e89f",
    "contract_with_431_location_and_pinned_genesis.json":
        "sha256:ea81ca135bfd3b8e86a69251cf63d6f5aaa86fa46777dcec9370971dd0c5208a",
    "org_ledger_test_genesis.json": "sha256:a2c01a2ebaa15aae048c42bb6048bdbf402e682a4c69c11def9d20d97539a6a7",
    "org_ledger_harness.py": "sha256:3bbf7f7da563afd9e7a1da1ee8cdbb04219a655a3dcaff3d3a6b2190ce6db945",
    # #432 @eecf4843 tests/fixtures/endpoint-ledger-designation/node.designation.json (byte copy)
    "node.designation.json": "sha256:d004bb72cba3143b2a4a544851eff1ae688094a44ceb72c9b4c1b5a41e091b15",
}
E0_CONTRACT_431 = TEST_ONLY_DIR / "contract_with_431_repository_ledger_location.json"  # no genesis pin
E0_CONTRACT_PINNED = TEST_ONLY_DIR / "contract_with_431_location_and_pinned_genesis.json"
_SIGNER_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "intr_pinned_test_only",
                              "ed25519_test_signer.py")
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


def _org_genesis(org_ns: Path, own: Any = False) -> str:
    """Write the org namespace's genesis: Lane B's test genesis, which the E0 contract pins. own=True: an unlabelled
    genesis the caller minted itself (P1 rev 6's LC-KV-15 case); own="labelled": the same with the E0 label."""
    if own:
        a = pinned()["endpoint_ledger_anchor"]
        evidence = {"schema": "stegverse.repository-ledger-initialization/v1", "repository": a.REPOSITORY,
                    "authority_effect": "NONE_CALLER_MINTED"}
        if own == "labelled":
            evidence["label"] = E0_LABEL
        return a.append_receipt(org_ns, a.GENESIS_CLASS, "REPOSITORY_LEDGER_INITIALIZATION:caller-minted",
                                a.sha({"repository": a.REPOSITORY, "ledger": None}), evidence, 32)["receipt_sha256"]
    genesis = json.loads(_test_only_bytes("org_ledger_test_genesis.json"))
    (org_ns / "receipts").mkdir(parents=True, exist_ok=True)
    (org_ns / "receipts" / (genesis["receipt_sha256"][7:] + ".json")).write_text(
        json.dumps(genesis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (org_ns / "HEAD.json").write_text(json.dumps({"repository": genesis["repository"],
                                                  "receipt_sha256": genesis["receipt_sha256"]}) + "\n", encoding="utf-8")
    return genesis["receipt_sha256"]


#: The E0 org chain's genesis: Lane B's org_ledger_test_genesis.json, pinned by the E0 contract fixture. KV pins no
#: genesis itself; evaluate_anchored checks the store's genesis against the contract (#432 @a2ee67e6).
E0_GENESIS = json.loads(_test_only_bytes("org_ledger_test_genesis.json"))["receipt_sha256"]
#: Lane B's TEST-ONLY append-route attester (tests/org_ledger_harness.py ROUTE_SEED / ROUTE_REF): a public seed.
E0_ROUTE_SEED = hashlib.sha256(b"org-ledger harness: TEST-ONLY append-route attester public seed").digest()
E0_ROUTE_KEY_ID = "test-org-ledger-append-route"


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


def e0_route_ref() -> dict[str, Any]:
    return {"key_id": E0_ROUTE_KEY_ID, "algorithm": "Ed25519", "custody": "TV/TVC", "signs": "ORG_LEDGER_HEAD",
            "public_key_b64": base64.b64encode(signer().public_key(E0_ROUTE_SEED)).decode()}


def _e0_head_signers() -> list[dict[str, Any]]:
    return [e0_route_ref()]


#: node_id -> the E0 org namespace its ledger was anchored to (for the TEST-ONLY ORG_CROSSING_READER).
_E0_ORG_OF: dict[str, Path] = {}


@contextlib.contextmanager
def _e0_node_reader(designation: Any, store: Any, source: Any, head_attestation: Any):
    """TEST-ONLY stand-in for a NODE_STORAGE_ENDPOINT access adapter (none is documented or admitted; #432 @eecf4843
    tests/test_endpoint_ledger_anchor.node_reader_stub): it reads the read-back root it is handed and the node's own
    head record. Production has no reader (NODE_STORAGE_ENDPOINT_READER_NOT_DOCUMENTED)."""
    m = pinned()
    hne, eld = m["healthy_node_evaluator"], m["endpoint_ledger_designation"]
    chain, failure, detail = hne.read_chain(Path(source)) if source else (None, "NO_SOURCE", "")
    if failure:
        yield None, None, ("ENDPOINT_LEDGER_UNREADABLE", f"{failure}: {detail}")
        return
    yield chain, eld.head_record_entries([chain[0]["receipt_sha256"]] if chain else []), None


def _e0_org_crossings(designation: Any) -> Any:
    """TEST-ONLY Org-side readback (LC-KV-23 (b)): the E0 org namespace the node was anchored to, else None."""
    org_ns = _E0_ORG_OF.get((designation or {}).get("endpoint_id"))
    if org_ns is None or not (org_ns / "HEAD.json").exists():
        return None
    return pinned()["healthy_node_evaluator"].read_chain(org_ns)[0]


_PRODUCTION_NODE_READER: list[Any] = []


def _set_node_reader(e0: bool) -> None:
    eld = pinned()["endpoint_ledger_designation"]
    if not _PRODUCTION_NODE_READER:
        _PRODUCTION_NODE_READER.append((eld._READERS.get(eld.NODE_STORAGE_ENDPOINT), eld.ORG_CROSSING_READER))
    reader, crossings = (_e0_node_reader, _e0_org_crossings) if e0 else _PRODUCTION_NODE_READER[0]
    if reader is None:
        eld._READERS.pop(eld.NODE_STORAGE_ENDPOINT, None)
    else:
        eld._READERS[eld.NODE_STORAGE_ENDPOINT] = reader
    eld.ORG_CROSSING_READER = crossings


@contextlib.contextmanager
def e0_without_node_reader():
    """Inside the E0 anchors: production's NODE_STORAGE_ENDPOINT reader state (none documented or admitted)."""
    _set_node_reader(False)
    try:
        yield
    finally:
        _set_node_reader(ep.TRUST_ANCHORS.get("label") == E0_LABEL)


@contextlib.contextmanager
def _e0_node_reader_in_force():
    """The TEST-ONLY node reader for one harness-side read (building the node's own proof), then the prior state."""
    eld = pinned()["endpoint_ledger_designation"]
    saved = (eld._READERS.get(eld.NODE_STORAGE_ENDPOINT), eld.ORG_CROSSING_READER)
    _set_node_reader(True)
    try:
        yield
    finally:
        if saved[0] is None:
            eld._READERS.pop(eld.NODE_STORAGE_ENDPOINT, None)
        else:
            eld._READERS[eld.NODE_STORAGE_ENDPOINT] = saved[0]
        eld.ORG_CROSSING_READER = saved[1]


def e0_node_endpoint(kind: str, node_root: Path, node_id: str) -> dict[str, Any]:
    """The deployment's endpoint binding. PERMANENT (#432 @eecf4843) carries the node's own designation (Lane B's
    TEST-ONLY node.designation.json for this node, its genesis and its crossing path) and its recorded head."""
    endpoint = {"endpoint_kind": kind, "ledger_root": str(node_root)}
    if kind != "PERMANENT":
        return endpoint
    m = pinned()
    a, hne, eld = m["endpoint_ledger_anchor"], m["healthy_node_evaluator"], m["endpoint_ledger_designation"]
    fixture = json.loads(_test_only_bytes("node.designation.json"))
    chain = hne.read_chain(node_root)[0] if (node_root / "HEAD.json").exists() else []
    watermark = fixture["rollback_watermark_source"]
    designation = {**fixture, "endpoint_id": node_id,
                   "expected_genesis_receipt_sha256": chain[-1]["receipt_sha256"] if chain else None,
                   "rollback_watermark_source": {**watermark, "org_crossing_cross_check": {
                       **watermark["org_crossing_cross_check"], "path_ids": [a.path_id(node_id)]}}}
    return {**endpoint, "designation": designation,
            "recorded_head": {"source": eld.NODE_WATERMARK_SOURCE,
                              "head_receipt_sha256": chain[0]["receipt_sha256"] if chain else None}}


def _set_contract(e0: bool, contract: Any = None) -> None:
    """The #431 designation and append-route stand-ins: Lane B's pinned-genesis fixture contract and the TEST-ONLY route
    attester while E0 anchors are in force, else the vendored contract and the vendored (empty) head-signers file."""
    location = pinned()["org_ledger_location"]
    _set_node_reader(e0)
    if not _PRODUCTION_CONTRACT_PATH:
        _PRODUCTION_CONTRACT_PATH.append((location.CONTRACT_PATH, location.load_head_signers))
    if e0:
        contract = contract or E0_CONTRACT_PINNED
        if Path(contract).parent == TEST_ONLY_DIR:
            _test_only_bytes(contract.name)
    location.CONTRACT_PATH = contract if e0 else _PRODUCTION_CONTRACT_PATH[0][0]
    location.load_head_signers = _e0_head_signers if e0 else _PRODUCTION_CONTRACT_PATH[0][1]


@contextlib.contextmanager
def e0_without_append_route():
    """Inside the E0 anchors: the vendored (empty) org-ledger-head-signers.v1.json, i.e. the append route not admitted."""
    location = pinned()["org_ledger_location"]
    saved = location.load_head_signers
    location.load_head_signers = _PRODUCTION_CONTRACT_PATH[0][1]
    try:
        yield
    finally:
        location.load_head_signers = saved


@contextlib.contextmanager
def e0_contract(contract: Path):
    """Inside the E0 anchors: another TEST-ONLY contract fixture (e.g. #431's copy without a genesis pin)."""
    _set_contract(True, contract)
    try:
        yield
    finally:
        _set_contract(ep.TRUST_ANCHORS.get("label") == E0_LABEL)


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
                      anchored: bool, transport_installed: bool = True, opened_signed: bool = True,
                      carried: bool = True) -> str | None:
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
    signal = {"mode": "ESTABLISH_GENESIS", "node_ref": node_id, "predecessor": None, "node_class": "LLM_ADAPTER"}
    if transport_installed:  # E0: the node arrived over the installed InTr transport (NOT_YET_ENABLED on main)
        record.update(transport="INTERLOCK_INTR", transport_state="INSTALLED", signal_sha256=a.sha(signal))
        if carried and org_ns is not None:
            e0_carry(org_ns, signal, f"e0-node-ingress:{node_id}", sender=node_root)
    put(cls, record, "e0")
    return first


def e0_carry(org_ns: Path, signal: dict[str, Any], communication_id: str, sender: Path | None = None) -> str:
    """The InTr path pair that carried `signal` (#432 @eecf4843 test shape): the INTR_MESH_PATH_TRANSFER source half on
    the sender's own ledger (the node's, once it is open; else a scratch source ledger), then the digest-only
    INTR_MESH_PATH_INGRESS on the org chain. Nothing is retained on the org ledger."""
    m = pinned()
    a, carrier, hne = m["endpoint_ledger_anchor"], m["intr_transport_carrier"], m["healthy_node_evaluator"]
    own = sender is not None and (Path(sender) / "HEAD.json").exists()
    ledger = Path(sender) if own else _mkdtemp("e0-intr-source-ledger-") / "ledger"
    chain = hne.read_chain(ledger)[0] if own else []
    source = a.append_receipt(ledger, carrier.SOURCE_CLASS, f"{carrier.SOURCE_CLASS}:{communication_id}",
                              chain[0]["receipt_sha256"] if chain else a.sha(None),
                              carrier.source_evidence(signal, communication_id), a.epoch_of(chain) if chain else 40)
    org_chain = hne.read_chain(org_ns)[0]
    return a.append_receipt(org_ns, carrier.DESTINATION_CLASS, f"{carrier.DESTINATION_CLASS}:{communication_id}",
                            org_chain[0]["receipt_sha256"], carrier.destination_evidence(source),
                            max(40, a.epoch_of(org_chain)))["receipt_sha256"]


def e0_health_ledger(node_id: str, *, status: str = "HEALTHY", admitted: bool = True, report: bool = True,
                     superseded_by: str | None = None, kind: str = "PERMANENT", foreign: bool = False,
                     anchored: bool = True, enroll: bool = True,
                     transport_key: dict[str, Any] | None = None, transport_installed: bool = True,
                     proof: str | None = "valid", opened_signed: bool = True, carried: bool = True,
                     attest: str | None = "route", own_genesis: Any = False) -> tuple[dict[str, Any], str | None]:
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
    * carried=False: the node's own NODE_INGRESS_ADMITTED claims installed InTr, but no InTr path pair carried its signal
      (a caller-appended ingress record, LC-KV-16 class).
    * attest: "route" (the TEST-ONLY append route attests this store's head), None (no attestation) or "own_key" (the
      caller attests its own store with a key that is not published).
    * own_genesis: the store minted its own org genesis instead of the contract-pinned one (a caller-created store;
      True unlabelled, "labelled" with the E0 label).
    """
    key = e0_node_identity_key(node_id)
    node_root = _mkdtemp("e0-node-ledger-") / "ledger"
    holder: dict[str, Any] = {}

    def populate(repo: Path) -> None:
        org_ns = Path(ep.healthy_node_ledger_root(repo))
        _org_genesis(org_ns, own=own_genesis)
        holder["first"] = _write_node_chain(node_root, org_ns, node_id, kind=kind, key=key, status=status,
                                            admitted=admitted, report=report, superseded_by=superseded_by,
                                            foreign=foreign, anchored=anchored, transport_installed=transport_installed,
                                            opened_signed=opened_signed, carried=carried)
        _seal_namespace(org_ns)
        _E0_ORG_OF[node_id] = org_ns
        holder["endpoint"] = e0_node_endpoint(kind, node_root, node_id)
        holder["proof"] = e0_identity_proof(node_id, holder["endpoint"], org_ns, proof)
    repo = _git_repo(populate=populate)
    if enroll:
        E0_TRANSPORT.enroll(node_id, transport_key or key, holder["proof"])
    source = {"kind": ep.LEDGER_SOURCE_ANCHORED, "org_ledger_git_dir": repo,
              "endpoint": holder["endpoint"]}
    if attest is not None:
        source["org_ledger_head_attestation"] = e0_attest(
            repo, **({} if attest == "route" else {"seed": e0_seed("callers-own-head-attester"),
                                                   "key_id": "callers-own-head-attester"}))
    return source, holder["first"]


def _store_head(repo: str) -> tuple[str, str, str]:
    """(genesis receipt, head receipt, namespace tree oid) as published at the designated ref of the store."""
    loc = ep.HEALTHY_NODE_LEDGER_LOCATION

    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True,
                              env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"}).stdout.decode().strip()
    commit = git("rev-parse", "--verify", loc["ref"] + "^{commit}")
    tree = git("rev-parse", "--verify", f"{commit}:{loc['namespace']}")
    head = json.loads(git("show", f"{commit}:{loc['namespace']}/HEAD.json"))["receipt_sha256"]
    chain = pinned()["healthy_node_evaluator"].read_chain(
        os.path.join(_checkout_tree(repo, commit), *loc["namespace"].split("/")))[0]
    return chain[-1]["receipt_sha256"], head, tree


def _checkout_tree(repo: str, commit: str) -> str:
    out = str(_mkdtemp("e0-store-tree-"))
    data = subprocess.run(["git", "-C", repo, "archive", "--format=tar", commit], check=True, capture_output=True,
                          env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"}).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(out, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))  # noqa: S202
    return out


def e0_attest(repo: str, seed: bytes = E0_ROUTE_SEED, key_id: str = E0_ROUTE_KEY_ID, **override: Any) -> dict[str, Any]:
    """The append route's stegverse.org-ledger-head-attestation/v1 for what the store holds (#432's
    tests/org_ledger_harness.attest; TEST-ONLY public seed by default). The genesis named is the store's own."""
    location = pinned()["org_ledger_location"]
    genesis, head, tree = _store_head(repo)
    body = {**location.head_attestation_body(genesis, head, tree), **override}
    return {**body, "key_id": key_id, "signature_b64": signer().sign_b64(location.head_attestation_message(body), seed)}


def e0_identity_proof(node_id: str, endpoint: dict[str, Any], org_ns: Path, mode: str | None = "valid") -> Any:
    """The node's stegverse.node-identity-proof/v1: its TEST-ONLY seed's signature over evaluate_anchored's
    identity_challenge for the current node-chain and org-ledger heads. When the root is not anchored there is no
    challenge; the proof then still names the node, so the anchor refusal is what layer 1 reports."""
    if mode is None:
        return None
    a = pinned()["endpoint_ledger_anchor"]
    head = json.loads((org_ns / "HEAD.json").read_text(encoding="utf-8"))["receipt_sha256"] \
        if (org_ns / "HEAD.json").exists() else None
    with _e0_node_reader_in_force():  # the node reads its own storage endpoint to sign (TEST-ONLY reader)
        anchored = a.verify_anchor(node_id, endpoint=endpoint, org_ledger_root=org_ns,
                                   org_ledger_head_receipt_sha256=head)
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
