#!/usr/bin/env python3
"""
emoji_lint.py — StegDB-style Emoji Grammar Linter (KnowledgeVault / Continuity Vault Kit)

Goals:
- Encourage consistent relationship-emoji grammar:
  👤➡️👤, 👤➡️👥, 👤⬅️👤, 👤⬅️👥, 👤↔️👤, 👤↔️👥
- Flag "obscure editor arrows" (various Unicode arrows) and suggest using:
  - relationship emoji sequences, or
  - plain ASCII arrows: --> or ->

Default behavior: WARN only (exit 0).
Strict mode: set env var STEGDB_EMOJI_LINT_STRICT=1 to fail CI on warnings.

Usage:
  python3 tools/emoji_lint.py
  python3 tools/emoji_lint.py --root .
  python3 tools/emoji_lint.py --strict
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
import re
from typing import List, Tuple

CONFIG_PATHS = [
    Path(".stegdb/emoji-grammar.v1.json"),
    Path("tools/.stegdb/emoji-grammar.v1.json"),
]

def load_config(root: Path) -> dict:
    for rel in CONFIG_PATHS:
        p = root / rel
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("Missing .stegdb/emoji-grammar.v1.json (expected at repo root).")

def iter_md_files(root: Path) -> List[Path]:
    # Skip common heavy dirs
    skip_parts = {".git", "dist", "node_modules", ".venv", "venv", "__pycache__"}
    files: List[Path] = []
    for p in root.rglob("*.md"):
        if any(part in skip_parts for part in p.parts):
            continue
        files.append(p)
    return files

def scan_file(path: Path, disallowed_re: re.Pattern) -> List[Tuple[int, str, str]]:
    """
    Return list of (line_no, kind, message)
    kind: "WARN"
    """
    out: List[Tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Ignore non-utf8 markdown (rare); warn but don't fail.
        out.append((0, "WARN", "File is not UTF-8; skipped emoji lint."))
        return out

    for i, line in enumerate(text.splitlines(), start=1):
        m = disallowed_re.search(line)
        if m:
            ch = m.group(0)
            out.append((i, "WARN", f"Found arrow character '{ch}'. Prefer '-->' / '->' or relationship emoji (👤➡️👤 etc)."))
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repo root")
    ap.add_argument("--strict", action="store_true", help="Fail (non-zero) if any warnings are found.")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cfg = load_config(root)

    strict_env = os.getenv(cfg.get("strict_env_var", "STEGDB_EMOJI_LINT_STRICT"), "").strip()
    strict = args.strict or (strict_env in {"1", "true", "TRUE", "yes", "YES"})

    disallowed_re = re.compile(cfg["disallowed_arrow_chars_regex"])

    warnings = []
    for p in iter_md_files(root):
        issues = scan_file(p, disallowed_re)
        for (line_no, kind, msg) in issues:
            warnings.append((p, line_no, kind, msg))

    if warnings:
        print("🧭 Emoji Grammar Lint — Warnings")
        for p, line_no, kind, msg in warnings:
            loc = f"{p.as_posix()}:{line_no}" if line_no else p.as_posix()
            print(f" - {loc} [{kind}] {msg}")
        print("\nTip: Use relationship emoji grammar (👤➡️👤 / 👤↔️👥) or ASCII arrows (-->/->).")
        if strict:
            print("\nStrict mode enabled — failing.")
            return 2
        return 0

    print("✅ Emoji Grammar Lint — OK (no disallowed arrows found).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
