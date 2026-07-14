#!/usr/bin/env python3
"""Run an end-to-end self-test of release building and verification."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
ZIP_PATH = REPO_ROOT / "dist" / f"ContinuityVault_v{VERSION}.zip"
CHECKSUM_PATH = ZIP_PATH.with_suffix(ZIP_PATH.suffix + ".sha256")
MANIFEST_PATH = ZIP_PATH.with_suffix(ZIP_PATH.suffix + ".manifest.json")


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expect:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(
            f"command returned {result.returncode}, expected {expect}: {' '.join(args)}"
        )
    return result


def main() -> int:
    run("tools/build_release.py")

    for path in (ZIP_PATH, CHECKSUM_PATH, MANIFEST_PATH):
        if not path.is_file():
            raise RuntimeError(f"build did not create {path.relative_to(REPO_ROOT)}")

    verified = run("tools/verify_release.py", str(ZIP_PATH))
    if "OK: verified" not in verified.stdout:
        raise RuntimeError("verifier did not report full file verification")

    hidden_checksum = CHECKSUM_PATH.with_name(CHECKSUM_PATH.name + ".test-hidden")
    CHECKSUM_PATH.replace(hidden_checksum)
    try:
        missing_sidecar = run(
            "tools/verify_release.py",
            str(ZIP_PATH),
            expect=4,
        )
        if "missing checksum sidecar" not in missing_sidecar.stdout:
            raise RuntimeError("verifier did not explain the missing checksum failure")
    finally:
        hidden_checksum.replace(CHECKSUM_PATH)

    run("tools/verify_release.py", str(ZIP_PATH))
    print("OK: release tooling self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
