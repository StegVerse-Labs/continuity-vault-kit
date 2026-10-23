"""TEST-ONLY organization-ledger harness shared by #432 and #433 (byte-identical in both).

The org ledger in these suites is a scratch bare git object store. llm_adapter.org_ledger_location
accepts it only at the contract's pinned genesis and with a head attestation by a published
append-route attester (LC-KV-16 rev 5). Production publishes no attester: the append route is not
admitted, so every production read is FAIL_CLOSED MERGE_APPEND_PATH_NOT_ADMITTED.

`append_route()` stands in for the admitted append route in a test's scope only: it publishes a
TEST-ONLY attester (a public seed; TV/TVC custody holds real keys, bots never do) and `attest`
signs the head and namespace tree of a store the harness itself published. A suite's setUp never
enters it, so a probe that drives setUp() and the helpers gets the production refusal.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import subprocess
from pathlib import Path
from unittest import mock

from llm_adapter import org_ledger_location as location
from tests import ed25519_test_signer as signer

FIXTURES = Path(__file__).resolve().parent / "fixtures/node_receipts"
#: the org genesis every suite writes, and the contract fixture that pins its digest
GENESIS = json.loads((FIXTURES / "org_ledger_test_genesis.json").read_text(encoding="utf-8"))
CONTRACT_PINNED = FIXTURES / "contract_with_431_location_and_pinned_genesis.json"
CONTRACT_431 = FIXTURES / "contract_with_431_repository_ledger_location.json"
ROUTE_SEED = hashlib.sha256(b"org-ledger harness: TEST-ONLY append-route attester public seed").digest()
ROUTE_REF = {"key_id": "test-org-ledger-append-route", "algorithm": "Ed25519", "custody": "TV/TVC",
             "signs": "ORG_LEDGER_HEAD", "public_key_b64": base64.b64encode(signer.public_key(ROUTE_SEED)).decode()}
GIT_ENV = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1"}


def write_genesis(org_root) -> dict:
    """Write the fixture genesis as the org namespace's first receipt and HEAD."""
    org_root = Path(org_root)
    (org_root / "receipts").mkdir(parents=True, exist_ok=True)
    (org_root / "receipts" / (GENESIS["receipt_sha256"][7:] + ".json")).write_text(
        json.dumps(GENESIS, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (org_root / "HEAD.json").write_text(json.dumps({"repository": GENESIS["repository"],
                                                    "receipt_sha256": GENESIS["receipt_sha256"]}) + "\n",
                                        encoding="utf-8")
    return GENESIS


def _git(git_dir, *args) -> str:
    return subprocess.run(["git", "--git-dir", str(git_dir), *args], check=True, capture_output=True,
                          env=GIT_ENV).stdout.decode().strip()


def store_head(git_dir) -> tuple[str, str]:
    """(head receipt, namespace tree oid) as published in the store at the designated ref."""
    ref, namespace = location.ORG_LEDGER_LOCATION.split(":")
    commit = _git(git_dir, "rev-parse", "--verify", ref + "^{commit}")
    tree = _git(git_dir, "rev-parse", "--verify", f"{commit}:{namespace}")
    head = json.loads(_git(git_dir, "show", f"{commit}:{namespace}/HEAD.json"))["receipt_sha256"]
    return head, tree


def attest(git_dir, seed: bytes = ROUTE_SEED, key_id: str = ROUTE_REF["key_id"], **override) -> dict:
    """The append route's head attestation for what the store holds (TEST-ONLY seed by default)."""
    head, tree = store_head(git_dir)
    body = {**location.head_attestation_body(GENESIS["receipt_sha256"], head, tree), **override}
    signature = signer.sign_b64(location.head_attestation_message(body), seed)
    return {**body, "key_id": key_id, "signature_b64": signature}


@contextlib.contextmanager
def append_route():
    """TEST-ONLY: publish the harness attester for this scope, as an admitted append route would."""
    with mock.patch.object(location, "load_head_signers", return_value=[dict(ROUTE_REF)]):
        yield


def with_append_route(cls):
    """Run every test_ method of `cls` inside append_route() (setUp itself stays production)."""
    for name in [n for n in vars(cls) if n.startswith("test_")]:
        method = getattr(cls, name)

        def run(self, _method=method):
            with append_route():
                return _method(self)
        run.__name__, run.__doc__ = name, method.__doc__
        setattr(cls, name, run)
    return cls
