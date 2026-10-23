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

Until #431's contract designation is on this branch and the genesis is published on
the ref, this refuses: ORG_LEDGER_LOCATION_NOT_DESIGNATED or
ORG_LEDGER_LOCATION_UNREADABLE (six fields, via endpoint_ledger_anchor.non_allow).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Mapping

from llm_adapter import healthy_node_evaluator as hne

ROOT = Path(__file__).resolve().parents[1]
#: the repository_ledger_location designation (#431) is read from here, never from a caller
CONTRACT_PATH = ROOT / ".stegverse/transition-ledger/contract.json"
REPOSITORY = hne.REPOSITORY
ORGANIZATION = "StegVerse-org"
ORG_LEDGER_LOCATION = "refs/stegverse/organization-ledger:repository-ledger/StegVerse-org/LLM-adapter"
GENESIS_CLASS = "REPOSITORY_LEDGER_INITIALIZATION"


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
    return {"repository": location["repository"], "ref": location["ref"], "namespace": location["namespace"]}


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
def designated_org_ledger(org_ledger_git_dir: Any):
    """Yield (org_ledger_root, None) read back from the designated ref and namespace, or (None, (reason, detail)).

    The caller names only where a local StegVerse-org/.github object store is; the ref and the namespace come from
    the contract. `git archive` reads local objects only (no fetch, no network); the tree is unpacked read-only into
    a scratch directory that is deleted on exit.
    """
    location = org_ledger_location()
    if location is None:
        yield None, ("ORG_LEDGER_LOCATION_NOT_DESIGNATED", f"{CONTRACT_PATH.name} has no repository_ledger_location "
                     f"designating {ORG_LEDGER_LOCATION}")
        return
    if not isinstance(org_ledger_git_dir, (str, Path)) or not str(org_ledger_git_dir):
        yield None, ("ORG_LEDGER_LOCATION_UNREADABLE", "no StegVerse-org/.github object store named")
        return
    git = ["git", "--git-dir", str(org_ledger_git_dir), "-c", "protocol.allow=never"]
    try:
        tree = subprocess.run(git + ["archive", "--format=tar", location["ref"] + "^{commit}", location["namespace"]],
                              capture_output=True, check=False, timeout=60,
                              env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GIT_TERMINAL_PROMPT": "0",
                                   "GIT_CONFIG_NOSYSTEM": "1", "HOME": "/nonexistent"})
    except (OSError, subprocess.SubprocessError) as exc:
        yield None, ("ORG_LEDGER_LOCATION_UNREADABLE", f"git unavailable: {type(exc).__name__}")
        return
    if tree.returncode != 0 or not tree.stdout:
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
        yield root, None


__all__ = ["CONTRACT_PATH", "ORG_LEDGER_LOCATION", "designated_org_ledger", "org_ledger_location"]
