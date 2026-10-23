"""Materialize pinned cross-repository test inputs, anonymously and byte-checked (StegVerse-org/.github#166, E0, stdlib).

A pin file (stegverse.cross-repo-input-pin/v1) names, per input, a public repository url, a commit, the directory
the tests read it from (relative to --root) and the sha256 of every file they read. materialize fetches exactly that
commit with no credential (depth 1, no tags), checks the commit and every listed file, and exits nonzero on any
mismatch or fetch failure: a selected parity test then fails with the reason, it is never skipped. An existing
destination is never overwritten: it is only verified.

  materialize PIN [--root .]   fetch (or verify) every input; prints one line per file
  verify PIN [--root .]        verify only, fetch nothing
  tests PIN                    the pinned test node ids, one per line
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "stegverse.cross-repo-input-pin/v1"


class InputUnavailable(Exception):
    pass


def load(path: str | Path) -> dict:
    pin = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(pin, Mapping) or pin.get("schema") != SCHEMA:
        raise InputUnavailable(f"{path}: schema must be {SCHEMA}")
    for name, decl in sorted(pin.get("inputs", {}).items()):
        for key in ("url", "commit", "dest", "files"):
            if not decl.get(key):
                raise InputUnavailable(f"input {name}: {key} is missing")
        if len(decl["commit"]) != 40:
            raise InputUnavailable(f"input {name}: commit must be a full 40-character sha")
    return dict(pin)


def verify_files(dest: Path, files: Mapping[str, str]) -> list[str]:
    lines = []
    for rel, want in sorted(files.items()):
        p = dest / rel
        if not p.is_file():
            raise InputUnavailable(f"{p}: pinned file is absent")
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != want:
            raise InputUnavailable(f"{p}: sha256 {got} is not the pinned {want}")
        lines.append(f"{p} {got}")
    return lines


def fetch(decl: Mapping[str, Any], dest: Path) -> None:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    def git(*args: str) -> str:
        done = subprocess.run(["git", "-C", str(dest), *args], env=env, capture_output=True, text=True)
        if done.returncode != 0:
            raise InputUnavailable(f"git {' '.join(a for a in args if not a.startswith('http') and a != '-c')[:80]} failed: {done.stderr.strip()[-300:]}")
        return done.stdout

    dest.mkdir(parents=True)
    git("init", "-q")
    git("-c", "credential.helper=", "-c", "http.https://github.com/.extraheader=", "fetch", "--no-tags", "--quiet",
        "--depth=1", decl["url"], decl["commit"])
    git("checkout", "-q", "--detach", "FETCH_HEAD")
    head = git("rev-parse", "HEAD").strip()
    if head != decl["commit"]:
        raise InputUnavailable(f"fetched {head} is not the pinned commit {decl['commit']}")


def materialize(pin: Mapping[str, Any], root: Path, *, allow_fetch: bool = True) -> list[str]:
    lines = []
    for name, decl in sorted(pin["inputs"].items()):
        dest = (root / decl["dest"]).resolve()
        if not dest.exists():
            if not allow_fetch:
                raise InputUnavailable(f"input {name}: {dest} is absent")
            fetch(decl, dest)
            lines.append(f"{name}: fetched {decl['repository'] if 'repository' in decl else decl['url']} @{decl['commit']}")
        else:
            lines.append(f"{name}: {dest} exists; verified, not overwritten")
        lines += verify_files(dest, decl["files"])
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("materialize", "verify", "tests"))
    parser.add_argument("pin")
    parser.add_argument("--root", default=".")
    a = parser.parse_args(argv)
    try:
        pin = load(a.pin)
        if a.command == "tests":
            print("\n".join(pin["tests"]))
            return 0
        for line in materialize(pin, Path(a.root), allow_fetch=a.command == "materialize"):
            print(line)
    except (InputUnavailable, OSError, ValueError, KeyError) as exc:
        print(f"::error::REQUIRED_VERIFICATION_INPUT_UNAVAILABLE: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
