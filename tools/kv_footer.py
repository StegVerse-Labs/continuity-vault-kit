#!/usr/bin/env python3
"""
kv_footer.py

Enforces a standardized footer on Markdown files to prevent layer confusion.

Supported footers:
- "🔒 Layer: Framework | KV"
- "🔒 Layer: Vault Template | KV"

Usage:
  python3 tools/kv_footer.py check
  python3 tools/kv_footer.py apply
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Tuple

FOOTER_FRAMEWORK = "🔒 Layer: Framework | KV"
FOOTER_VAULT_TEMPLATE = "🔒 Layer: Vault Template | KV"

MD_EXT = ".md"

# Where we expect each footer type to be used
FRAMEWORK_PATH_PREFIXES = [
    "",         # repo root markdown files
    "docs",     # docs/**
]

VAULT_TEMPLATE_PREFIXES = [
    os.path.join("vault_template", "KnowledgeVault"),
]

# Files we skip (generated, vendor, etc.) — add as needed
SKIP_DIRS = {
    ".git",
    ".github",
    "dist",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

def iter_markdown_files(repo_root: Path) -> List[Path]:
    files: List[Path] = []
    for p in repo_root.rglob(f"*{MD_EXT}"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if not p.is_file():
            continue
        files.append(p)
    return files

def rel_posix(repo_root: Path, p: Path) -> str:
    return p.relative_to(repo_root).as_posix()

def expected_footer_for(path_rel: str) -> str | None:
    # Vault template area -> vault template footer
    for prefix in VAULT_TEMPLATE_PREFIXES:
        if path_rel.startswith(Path(prefix).as_posix() + "/") or path_rel == Path(prefix).as_posix():
            return FOOTER_VAULT_TEMPLATE

    # Framework docs + root markdown -> framework footer
    # Root markdown: no "/" in path
    if "/" not in path_rel:
        return FOOTER_FRAMEWORK
    for prefix in FRAMEWORK_PATH_PREFIXES:
        if prefix == "":
            continue
        if path_rel.startswith(Path(prefix).as_posix() + "/"):
            return FOOTER_FRAMEWORK

    # Everything else: no enforcement (e.g., nested templates you may add later)
    return None

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8", newline="\n")

def normalize_newlines(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")

def ensure_footer(content: str, footer: str) -> Tuple[str, bool]:
    """
    Returns (new_content, changed?)
    Ensures the content ends with:
      \n---\n\n{footer}\n
    """
    content = normalize_newlines(content)

    # Trim trailing whitespace-only lines
    lines = content.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()

    # Detect existing footer line at end
    if lines and lines[-1].strip() in {FOOTER_FRAMEWORK, FOOTER_VAULT_TEMPLATE}:
        # Ensure separator exists immediately above (allow blank line between)
        # We'll rebuild cleanly to guarantee canonical formatting.
        # Remove any existing footer + optional preceding separator block.
        lines.pop()
        while lines and lines[-1].strip() == "":
            lines.pop()
        if lines and lines[-1].strip() == "---":
            lines.pop()
        while lines and lines[-1].strip() == "":
            lines.pop()

    # Rebuild with canonical footer
    rebuilt = "\n".join(lines).rstrip()
    if rebuilt:
        rebuilt += "\n\n---\n\n" + footer + "\n"
    else:
        rebuilt = "---\n\n" + footer + "\n"
    return rebuilt, (rebuilt != content)

def check_footer(content: str, expected_footer: str) -> bool:
    """
    True if content ends with canonical footer block.
    """
    content = normalize_newlines(content)

    # Remove trailing whitespace-only lines
    lines = content.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()

    if not lines:
        return False

    if lines[-1].strip() != expected_footer:
        return False

    # Find the nearest non-empty line above footer
    i = len(lines) - 2
    while i >= 0 and lines[i].strip() == "":
        i -= 1
    if i < 0:
        return False
    return lines[i].strip() == "---"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "apply"], help="check = validate; apply = modify files in-place")
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    md_files = iter_markdown_files(repo_root)

    failures: List[str] = []
    changed_files: List[str] = []

    for p in md_files:
        rel = rel_posix(repo_root, p)
        expected = expected_footer_for(rel)
        if expected is None:
            continue

        content = read_text(p)

        if args.cmd == "check":
            ok = check_footer(content, expected)
            if not ok:
                failures.append(f"{rel} (expected footer: {expected})")
        else:  # apply
            new_content, changed = ensure_footer(content, expected)
            if changed:
                write_text(p, new_content)
                changed_files.append(rel)

    if args.cmd == "apply":
        if changed_files:
            print("Updated footer in:")
            for f in changed_files:
                print(f"  - {f}")
        else:
            print("No changes needed.")
        return 0

    # check
    if failures:
        print("Footer check failed. Missing or incorrect footer in:")
        for f in failures:
            print(f"  - {f}")
        print("\nFix locally with:")
        print("  python3 tools/kv_footer.py apply")
        return 2

    print("Footer check passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
