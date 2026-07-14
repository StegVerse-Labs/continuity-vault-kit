#!/usr/bin/env python3
"""Exercise dry-run, verified initialization, receipt creation, and overwrite refusal."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "tools/init_vault.py", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expect:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(
            f"initializer returned {result.returncode}, expected {expect}: {' '.join(args)}"
        )
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="continuity-vault-init-") as temp:
        target = Path(temp)

        dry_run = run(str(target), "--dry-run")
        if "DRY RUN" not in dry_run.stdout:
            raise RuntimeError("dry-run did not report its plan")
        if (target / "KnowledgeVault").exists():
            raise RuntimeError("dry-run created a vault")

        initialized = run(str(target))
        vault = target / "KnowledgeVault"
        receipt_path = vault / "_System" / "installation.receipt.json"
        if "Initialized and verified" not in initialized.stdout:
            raise RuntimeError("initializer did not report verification")
        if not receipt_path.is_file():
            raise RuntimeError("initializer did not create an installation receipt")

        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        verification = receipt.get("verification", {})
        if not verification.get("file_set_matches"):
            raise RuntimeError("receipt does not confirm matching file sets")
        if not verification.get("immutable_file_hashes_match"):
            raise RuntimeError("receipt does not confirm copied file hashes")
        if verification.get("overwrote_existing_vault") is not False:
            raise RuntimeError("receipt does not preserve overwrite refusal")

        refused = run(str(target), expect=5)
        if "Refusing to overwrite existing" not in refused.stdout:
            raise RuntimeError("initializer did not explain overwrite refusal")

    print("OK: vault initializer self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
