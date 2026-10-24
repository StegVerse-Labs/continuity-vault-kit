"""Read the organization ledger back from the location the repository contract designates (LC-KV-16).

The org ledger an anchor is checked against is never a caller-chosen path. The
location is ``repository_ledger_location`` in ``.stegverse/transition-ledger/contract.json``
(designated by StegVerse-org/LLM-adapter#431): repository StegVerse-org/.github,
ref ``refs/stegverse/organization-ledger``, namespace
``repository-ledger/StegVerse-org/LLM-adapter``. The caller names only where a
local StegVerse-org/.github object store is.

This is the one I/O boundary of the anchored layer-1 path, kept out of the pure
cores (``endpoint_ledger_anchor``, ``node_ledger_dissolution``). It runs one local
command, ``git --git-dir <store> -c protocol.allow=never archive <ref>^{commit} <namespace>``:
local objects only, no fetch, no network, no clock. The tree is unpacked (regular
files under the namespace only) into a scratch directory deleted on exit.

A caller-named object store is never trusted for what it holds (LC-KV-16 rev 5):

* the namespace's REPOSITORY_LEDGER_INITIALIZATION genesis must equal
  ``expected_genesis_receipt_sha256``, pinned in the contract's repository_ledger_location
  (a field #431's contract shape has to add; absent -> ORG_LEDGER_GENESIS_NOT_PINNED);
* the store's head and namespace tree must be authenticated: an Ed25519 org-ledger
  head attestation (``stegverse.org-ledger-head-attestation/v1``) over {location, pinned
  genesis, head receipt, namespace tree oid}, signed by a key published in
  ``.stegverse/node-ledger/org-ledger-head-signers.v1.json`` for the admitted org-ledger
  append route. That route is not admitted, so no key is published and every read
  refuses MERGE_APPEND_PATH_NOT_ADMITTED. Nothing read from a store ALLOWs until then.

Until #431's contract designation is on this branch and the genesis is published on
the ref, this refuses: ORG_LEDGER_LOCATION_NOT_DESIGNATED or
ORG_LEDGER_LOCATION_UNREADABLE (six fields, via endpoint_ledger_anchor.non_allow).
"""
from __future__ import annotations

import base64
import binascii
import contextlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Mapping

from llm_adapter import ed25519_verify
from llm_adapter import healthy_node_evaluator as hne

ROOT = Path(__file__).resolve().parents[1]
#: the repository_ledger_location designation (#431) is read from here, never from a caller
CONTRACT_PATH = ROOT / ".stegverse/transition-ledger/contract.json"
REPOSITORY = hne.REPOSITORY
ORGANIZATION = "StegVerse-org"
ORG_LEDGER_LOCATION = "refs/stegverse/organization-ledger:repository-ledger/StegVerse-org/LLM-adapter"
GENESIS_CLASS = "REPOSITORY_LEDGER_INITIALIZATION"
#: public-key references of the admitted org-ledger append route's head attesters (none published)
HEAD_SIGNERS_PATH = ROOT / ".stegverse/node-ledger/org-ledger-head-signers.v1.json"
HEAD_SIGNERS_SCHEMA = "stegverse.published-public-key-references/v1"
HEAD_ATTESTATION_SCHEMA = "stegverse.org-ledger-head-attestation/v1"
HEAD_ATTESTATION_FIELDS = ("schema", "org_ledger_location", "genesis_receipt_sha256", "head_receipt_sha256",
                           "namespace_tree_oid", "appended_through")
APPEND_ROUTE = "ADMITTED_ORG_LEDGER_APPEND_ROUTE"


def org_ledger_location() -> dict[str, Any] | None:
    """The org-ledger location the repository contract designates (#431), or None. Never caller-chosen."""
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    location = contract.get("repository_ledger_location") if isinstance(contract, Mapping) else None
    if not isinstance(location, Mapping) or contract.get("repository") != REPOSITORY \
            or location.get("repository") != ORGANIZATION + "/.github" \
            or location.get("ref") != ORG_LEDGER_LOCATION.split(":")[0] \
            or location.get("namespace") != ORG_LEDGER_LOCATION.split(":")[1]:
        return None
    genesis = location.get("expected_genesis_receipt_sha256")
    pinned = isinstance(genesis, str) and len(genesis) == 71 and genesis.startswith("sha256:")
    return {"repository": location["repository"], "ref": location["ref"], "namespace": location["namespace"],
            "expected_genesis_receipt_sha256": genesis if pinned else None}


def load_head_signers() -> list[dict[str, Any]]:
    """The published org-ledger head attester references (empty until the append route is admitted)."""
    try:
        published = json.loads(HEAD_SIGNERS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(published, Mapping) or published.get("schema") != HEAD_SIGNERS_SCHEMA:
        return []
    return [dict(k) for k in published.get("signers") or []
            if isinstance(k, Mapping) and k.get("signs") == "ORG_LEDGER_HEAD"]


def head_attestation_body(genesis_sha: str, head_sha: str, tree_oid: str) -> dict[str, Any]:
    """What the append route attests for one org-ledger head. Pure."""
    return {"schema": HEAD_ATTESTATION_SCHEMA, "org_ledger_location": ORG_LEDGER_LOCATION,
            "genesis_receipt_sha256": genesis_sha, "head_receipt_sha256": head_sha,
            "namespace_tree_oid": tree_oid, "appended_through": APPEND_ROUTE}


def head_attestation_message(body: Mapping[str, Any]) -> bytes:
    """The bytes the attester signs: the domain line, then the canonical body. Pure."""
    return HEAD_ATTESTATION_SCHEMA.encode("utf-8") + b"\n" + hne.canon(dict(body))


def _b64(value: Any) -> bytes | None:
    try:
        return base64.b64decode(value, validate=True) if isinstance(value, str) else None
    except (binascii.Error, ValueError):
        return None


def head_attestation_failure(attestation: Any, genesis_sha: str, head_sha: str,
                             tree_oid: str) -> tuple[str, str] | None:
    """(reason, detail) unless a published attester signed exactly this genesis, head and tree, else None. Pure."""
    signers = load_head_signers()
    if not signers:
        return ("MERGE_APPEND_PATH_NOT_ADMITTED", "no org-ledger head attester is published "
                f"({HEAD_SIGNERS_PATH.name} NONE_PUBLISHED): the admitted append route does not exist yet, so a "
                "store's head is never authenticated")
    if not isinstance(attestation, Mapping):
        return "ORG_LEDGER_HEAD_NOT_AUTHENTICATED", "no stegverse.org-ledger-head-attestation/v1 for this head"
    body = {k: attestation.get(k) for k in HEAD_ATTESTATION_FIELDS}
    if body != head_attestation_body(genesis_sha, head_sha, tree_oid):
        return ("ORG_LEDGER_HEAD_NOT_AUTHENTICATED", "the attestation names another genesis, head or namespace tree "
                f"than the store holds (head {head_sha}, tree {tree_oid})")
    key = next((k for k in signers if k.get("key_id") == attestation.get("key_id")), None)
    if key is None:
        return "ORG_LEDGER_HEAD_NOT_AUTHENTICATED", f"attester {attestation.get('key_id')!r} is not published"
    public, signature = _b64(key.get("public_key_b64")), _b64(attestation.get("signature_b64"))
    if public is None or len(public) != 32 or signature is None or len(signature) != 64 \
            or not ed25519_verify.verify(public, head_attestation_message(body), signature):
        return "ORG_LEDGER_HEAD_NOT_AUTHENTICATED", "the attestation signature does not verify under the published key"
    return None


def _unpack(tar_bytes: bytes, scratch: Path, namespace: str) -> None:
    """Unpack regular files and directories under `namespace` only; anything else is refused."""
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as archive:
        for member in archive.getmembers():
            name = member.name
            if name.startswith("/") or ".." in Path(name).parts or not (name + "/").startswith(namespace + "/"):
                if member.isdir() and (namespace + "/").startswith(name.rstrip("/") + "/"):
                    continue
                raise ValueError(f"tree entry {name!r} is outside {namespace}")
            target = scratch / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
            else:
                raise ValueError(f"tree entry {name!r} is not a regular file")


@contextlib.contextmanager
def designated_org_ledger(org_ledger_git_dir: Any, org_ledger_head_attestation: Any = None):
    """Yield (org_ledger_root, None) read back from the designated ref and namespace, or (None, (reason, detail)).

    The caller names only where a local StegVerse-org/.github object store is; the ref and the namespace come from
    the contract. `git archive` reads local objects only (no fetch, no network); the tree is unpacked read-only into
    a scratch directory that is deleted on exit. The store decides nothing by itself: its genesis must equal the
    contract's pinned genesis, and its head and namespace tree must carry a published append-route attestation.
    """
    location = org_ledger_location()
    if location is None:
        yield None, ("ORG_LEDGER_LOCATION_NOT_DESIGNATED", f"{CONTRACT_PATH.name} has no repository_ledger_location "
                     f"designating {ORG_LEDGER_LOCATION}")
        return
    if location["expected_genesis_receipt_sha256"] is None:
        yield None, ("ORG_LEDGER_GENESIS_NOT_PINNED", f"{CONTRACT_PATH.name} repository_ledger_location carries no "
                     "expected_genesis_receipt_sha256; any store can mint a genesis, so none is accepted")
        return
    if not isinstance(org_ledger_git_dir, (str, Path)) or not str(org_ledger_git_dir):
        yield None, ("ORG_LEDGER_LOCATION_UNREADABLE", "no StegVerse-org/.github object store named")
        return
    git = ["git", "--git-dir", str(org_ledger_git_dir), "-c", "protocol.allow=never"]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GIT_TERMINAL_PROMPT": "0",
           "GIT_CONFIG_NOSYSTEM": "1", "HOME": "/nonexistent"}
    try:
        commit = subprocess.run(git + ["rev-parse", "--verify", "--quiet", location["ref"] + "^{commit}"],
                                capture_output=True, check=False, timeout=60, env=env).stdout.decode().strip()
        tree_oid = subprocess.run(git + ["rev-parse", "--verify", "--quiet", f"{commit}:{location['namespace']}"],
                                  capture_output=True, check=False, timeout=60, env=env).stdout.decode().strip() \
            if commit else ""
        tree = subprocess.run(git + ["archive", "--format=tar", commit, location["namespace"]],
                              capture_output=True, check=False, timeout=60, env=env) if tree_oid else None
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
        yield None, ("ORG_LEDGER_LOCATION_UNREADABLE", f"git unavailable: {type(exc).__name__}")
        return
    if tree is None or tree.returncode != 0 or not tree.stdout:
        yield None, ("ORG_LEDGER_LOCATION_UNREADABLE", f"{location['ref']}:{location['namespace']} is not in the object "
                     f"store {org_ledger_git_dir}")
        return
    with tempfile.TemporaryDirectory(prefix="org-ledger-readback-") as scratch:
        try:
            _unpack(tree.stdout, Path(scratch), location["namespace"])
        except (tarfile.TarError, OSError, ValueError) as exc:
            yield None, ("ORG_LEDGER_LOCATION_UNREADABLE", f"unreadable tree: {type(exc).__name__}")
            return
        root = Path(scratch) / location["namespace"]
        chain, failure, _ = hne.read_chain(root)
        if failure or chain[-1].get("transition_class") != GENESIS_CLASS or chain[-1].get("repository") != REPOSITORY:
            yield None, ("ORG_LEDGER_LOCATION_UNREADABLE", f"{location['namespace']} has no {GENESIS_CLASS} genesis "
                         f"for {REPOSITORY}")
            return
        if chain[-1].get("receipt_sha256") != location["expected_genesis_receipt_sha256"]:
            yield None, ("ORG_LEDGER_GENESIS_MISMATCH", f"the store's genesis is {chain[-1].get('receipt_sha256')}, "
                         f"the contract pins {location['expected_genesis_receipt_sha256']}")
            return
        unauthenticated = head_attestation_failure(org_ledger_head_attestation, chain[-1]["receipt_sha256"],
                                                   chain[0]["receipt_sha256"], tree_oid)
        if unauthenticated:
            yield None, unauthenticated
            return
        yield root, None


__all__ = ["CONTRACT_PATH", "HEAD_ATTESTATION_SCHEMA", "HEAD_SIGNERS_PATH", "ORG_LEDGER_LOCATION",
           "designated_org_ledger", "head_attestation_body", "head_attestation_failure", "head_attestation_message",
           "load_head_signers", "org_ledger_location"]
