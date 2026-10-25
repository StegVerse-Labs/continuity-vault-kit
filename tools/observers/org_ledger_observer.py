"""Observer layer for LC-KV-26: the anonymous fetch of the public Org ledger, kept out of the clock-free,
network-free reader (runtime/org_crossing_reader.py).

SKAP Vault inside KV is the only PII and credential store for every user, the ecosystem's own included; the
ecosystem holds none (HST citation pending P1 #163).

It runs ``git fetch`` of ``refs/stegverse/organization-ledger`` from the public StegVerse-org/.github repository with
no credential (a throwaway HOME, no system git config, an empty credential helper, no terminal prompt), then writes a
snapshot directory (HEAD.json, receipts/*.json, snapshot.json) for ``STEGVERSE_ORG_LEDGER_SNAPSHOT``. It writes
nothing back to any ledger. On any failure it prints the six-field FAIL_CLOSED and exits 1.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from runtime import org_crossing_reader as ocr  # noqa: E402


def _git(args, cwd, env):
    return subprocess.run(["git", "-c", "credential.helper=", *args], cwd=cwd, env=env, check=True,
                          capture_output=True).stdout


def observe(out: Path, source: str = ocr.ORG_LEDGER_SOURCE) -> dict:
    with tempfile.TemporaryDirectory() as home:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home, "GIT_TERMINAL_PROMPT": "0",
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_ASKPASS": "/bin/false", "SSH_ASKPASS": "/bin/false"}
        bare = Path(home) / "org.git"
        _git(["init", "-q", "--bare", str(bare)], home, env)
        _git(["fetch", "-q", "--depth=1", source, f"+{ocr.LEDGER_REF}:{ocr.LEDGER_REF}"], bare, env)
        tip = _git(["rev-parse", ocr.LEDGER_REF], bare, env).decode().strip()
        (out / "receipts").mkdir(parents=True, exist_ok=True)
        (out / "HEAD.json").write_bytes(_git(["show", f"{tip}:HEAD.json"], bare, env))
        for name in _git(["ls-tree", "--name-only", f"{tip}:receipts"], bare, env).decode().split():
            if name.endswith(".json"):
                (out / "receipts" / name).write_bytes(_git(["show", f"{tip}:receipts/{name}"], bare, env))
    meta = {"schema": ocr.SNAPSHOT_SCHEMA, "source": source, "ledger_ref": ocr.LEDGER_REF, "ledger_ref_tip": tip,
            "read_route": "ANONYMOUS_PUBLIC_LEDGER_READ", "credential": None, "authority_effect": "NONE"}
    (out / "snapshot.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--source", default=ocr.ORG_LEDGER_SOURCE)
    a = ap.parse_args(argv)
    try:
        meta = observe(a.out, a.source)
        head, receipts, _ = ocr.load_snapshot(a.out)
        chain = ocr.walk(head, receipts)
        found = ocr.crossings(head, receipts)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps(ocr.failure(f"anonymous observation failed: {exc}"), indent=2, sort_keys=True))
        return 1
    print(json.dumps({**meta, "org_ledger_head": head, "chain_length": len(chain),
                      "distinct_org_crossing_records_with_endpoint_head": len(found)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
