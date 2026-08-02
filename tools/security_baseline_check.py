#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "security/security-baseline.v1.json"

def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)

def main() -> int:
    try:
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid security baseline: {exc}")
    if cfg.get("profile") != "FEDERAL_FLOOR_PLUS":
        fail("profile must be FEDERAL_FLOOR_PLUS")
    missing = [p for p in cfg.get("required_files", []) if not (ROOT / p).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))
    workflow = (ROOT / ".github/workflows/security-baseline.yml").read_text(encoding="utf-8")
    if "contents: read" not in workflow or "permissions:" not in workflow:
        fail("security workflow must declare least-privilege contents: read")
    for pattern in cfg.get("forbidden_patterns", []):
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            if pattern in path.read_text(encoding="utf-8", errors="replace"):
                fail(f"forbidden permission pattern in {path.relative_to(ROOT)}")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    required_phrases = ["Federal Floor Plus", "No workflow may inspect", "Personal-vault repair boundary"]
    for phrase in required_phrases:
        if phrase not in security:
            fail(f"SECURITY.md missing boundary: {phrase}")
    for receipt in cfg.get("required_release_evidence", []):
        path = ROOT / receipt
        if not path.is_file():
            fail(f"missing release evidence: {receipt}")
        json.loads(path.read_text(encoding="utf-8"))
    print("OK: Federal Floor Plus security baseline validated")
    return 0

if __name__ == "__main__":
    sys.exit(main())
