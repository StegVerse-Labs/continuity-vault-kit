#!/usr/bin/env python3
"""
kv_layer_check.py — StegDB-style layer boundary enforcement for KnowledgeVault.

Modes:
- validate   : fail CI if boundaries/labels violated
- auto-label : add/update footers only (no moves/deletes)
- suggest    : report conservative suggestions (no moves/deletes)

Footer format enforced (last lines of Markdown files):

---

🔒 Layer: Framework | KV
or
---
🔒 Layer: Vault Template | KV
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

# Legacy footer markers your repo has used before (we'll strip during auto-label)
LEGACY_STEGDB_COMMENT_RE = re.compile(
    r"<!--\s*StegDB:\s*kv\.layer\.v1\s*\|\s*LAYER=([A-Z_]+)\s*\|\s*SCOPE=([^>]+?)\s*-->",
    re.MULTILINE,
)

# New enforced footer (simple + highly visible)
FOOTER_LINE_RE = re.compile(r"^🔒\s*Layer:\s*(Framework|Vault Template)\s*\|\s*KV\s*$", re.MULTILINE)

FOOTER_FRAMEWORK_LINE = "🔒 Layer: Framework | KV"
FOOTER_VAULT_TEMPLATE_LINE = "🔒 Layer: Vault Template | KV"

# Forbidden in this public framework repo (hard fail)
FORBIDDEN_LAYER_PHRASES = [
    "🔒 Layer: Personal Vault | KV",
    "🔒 Layer: Personal | KV",
    "Personal Vault",
    "KV Layer: PERSONAL",
    "KV Layer: PERSONAL_VAULT",
]

def load_config() -> dict:
    cfg_path = REPO_ROOT / ".stegdb" / "kv-layer.v1.json"
    if not cfg_path.exists():
        print(f"ERROR: Missing config: {cfg_path}")
        sys.exit(2)
    return json.loads(cfg_path.read_text(encoding="utf-8"))

def relpath(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT)).replace(os.sep, "/")

def match_any(rel: str, globs: List[str]) -> bool:
    rel = rel.replace(os.sep, "/")
    for g in globs:
        if fnmatch.fnmatch(rel, g.replace(os.sep, "/")):
            return True
    return False

def expected_layer(rel: str, cfg: dict) -> str:
    """
    Returns one of:
      FRAMEWORK
      RUNTIME_TEMPLATE
      UNKNOWN
    """
    fw = cfg["layers"]["FRAMEWORK"]
    if rel in fw.get("paths", []):
        return "FRAMEWORK"
    if match_any(rel, fw.get("globs", [])):
        return "FRAMEWORK"

    rt = cfg["layers"]["RUNTIME_TEMPLATE"]
    if match_any(rel, rt.get("globs", [])):
        return "RUNTIME_TEMPLATE"

    return "UNKNOWN"

def parse_footer(text: str) -> Tuple[str | None, str | None]:
    """
    Returns (layer, scope). Scope is retained for backward compatibility but
    not required for the new footer format.
    """
    # 1) New footer format
    m = FOOTER_LINE_RE.search(text)
    if m:
        val = m.group(1).strip()
        if val.lower() == "framework":
            return "FRAMEWORK", None
        return "RUNTIME_TEMPLATE", None

    # 2) Legacy StegDB HTML comment footer
    m2 = LEGACY_STEGDB_COMMENT_RE.search(text)
    if m2:
        return m2.group(1).strip(), m2.group(2).strip()

    # 3) Legacy emoji footer form (old docs)
    em = re.search(r"🧭\s*\*\*KV Layer:\*\*\s*([A-Z_]+)", text)
    sc = re.search(r"🏷️\s*\*\*KV Scope:\*\*\s*(.+)", text)
    return (em.group(1).strip() if em else None, sc.group(1).strip() if sc else None)

def strip_existing_footer(text: str) -> str:
    """
    Removes known footer blocks (new + legacy) by truncating from the nearest separator above it.
    Conservative: only strips if it finds a recognized footer marker.
    """
    markers = [
        "🔒 Layer:",  # new footer
        "StegDB: kv.layer.v1",  # legacy comment
        "🧭 **KV Layer:**",      # legacy emoji footer
        "🧬 **StegDB:** managed • rule=kv.layer.v1",
    ]

    idx = -1
    for mk in markers:
        j = text.rfind(mk)
        if j > idx:
            idx = j

    if idx == -1:
        return text

    # Find nearest separator above marker
    sep_idx = text.rfind("\n---", 0, idx)
    if sep_idx == -1:
        # fallback: cut from marker itself
        return text[:idx].rstrip() + "\n"
    return text[:sep_idx].rstrip() + "\n"

def build_footer(layer: str) -> str:
    """
    Builds the new simple footer format.
    """
    if layer == "RUNTIME_TEMPLATE":
        line = FOOTER_VAULT_TEMPLATE_LINE
    else:
        line = FOOTER_FRAMEWORK_LINE
    return "\n\n---\n\n" + line + "\n"

def is_binary(p: Path) -> bool:
    try:
        b = p.read_bytes()
    except Exception:
        return False
    return b"\x00" in b

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["validate", "auto-label", "suggest"], default="validate")
    ap.add_argument("--paths", nargs="*", default=[], help="Optional path globs to limit checks")
    args = ap.parse_args()

    cfg = load_config()

    violations: List[Tuple[str, str, str]] = []
    suggestions: List[Tuple[str, str, str]] = []
    touched = 0

    max_bin = cfg["enforce"]["binary_disallow"].get("max_binary_bytes_in_repo", 0)
    total_bin = 0

    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        r = relpath(p)
        if r.startswith(".git/"):
            continue

        if args.paths and not any(fnmatch.fnmatch(r, g.replace(os.sep, "/")) for g in args.paths):
            continue

        # Binary accounting
        if cfg["enforce"]["binary_disallow"].get("enabled", False) and is_binary(p):
            total_bin += p.stat().st_size

        # Only enforce footers on markdown
        if p.suffix.lower() != ".md":
            continue

        text = p.read_text(encoding="utf-8", errors="replace")

        # Hard fail markers from config + forbidden layer phrases
        hits = [mk for mk in cfg["enforce"].get("hard_fail_markers", []) if mk in text]
        for mk in FORBIDDEN_LAYER_PHRASES:
            if mk in text and mk not in hits:
                hits.append(mk)

        if hits:
            violations.append((r, "HARD_FAIL_MARKER", f"Found: {', '.join(hits)}"))
            continue

        layer = expected_layer(r, cfg)

        if layer in ("FRAMEWORK", "RUNTIME_TEMPLATE"):
            found_layer, _ = parse_footer(text)

            # Normalize legacy variants (e.g., legacy footer wrote FRAMEWORK/RUNTIME_TEMPLATE)
            # We only accept correct mapping for this repo.
            if found_layer is None:
                violations.append((r, "MISSING_FOOTER", f"Expected footer for {layer}"))
                if args.mode == "auto-label":
                    new_text = strip_existing_footer(text).rstrip() + build_footer(layer)
                    p.write_text(new_text, encoding="utf-8", newline="\n")
                    touched += 1
            else:
                # If legacy footer says FRAMEWORK/RUNTIME_TEMPLATE, ensure it matches expected layer
                # If legacy footer says something else, it's a mismatch too.
                if found_layer != layer:
                    violations.append((r, "FOOTER_MISMATCH", f"Expected {layer}, found {found_layer}"))
                    if args.mode == "auto-label":
                        new_text = strip_existing_footer(text).rstrip() + build_footer(layer)
                        p.write_text(new_text, encoding="utf-8", newline="\n")
                        touched += 1
                else:
                    # Footer exists and maps correctly — ensure it is in the new simple format when auto-labeling
                    if args.mode == "auto-label":
                        # Only rewrite if not already in new format
                        if not FOOTER_LINE_RE.search(text):
                            new_text = strip_existing_footer(text).rstrip() + build_footer(layer)
                            p.write_text(new_text, encoding="utf-8", newline="\n")
                            touched += 1

        if args.mode == "suggest":
            if r.startswith("docs/") and ("vault_template" in text or "00_Inbox" in text or "_Index" in text):
                suggestions.append(
                    (r, "MAYBE_TEMPLATE_DOC",
                     "Consider moving to vault_template/KnowledgeVault/ or rewriting as framework doc.")
                )

    if cfg["enforce"]["binary_disallow"].get("enabled", False) and max_bin and total_bin > max_bin:
        violations.append(("<repo>", "BINARY_SIZE_LIMIT", f"Binary bytes {total_bin} exceed limit {max_bin}"))

    if violations:
        print("\nKV Layer Check — Violations")
        for r, code, msg in violations:
            print(f"- {r}: {code} — {msg}")

    if suggestions:
        print("\nKV Layer Check — Suggestions")
        for r, code, msg in suggestions:
            print(f"- {r}: {code} — {msg}")

    if args.mode == "auto-label":
        print(f"\nAuto-label: updated {touched} file(s).")

    # In validate mode, any violations should fail CI
    return 1 if (violations and args.mode == "validate") else 0

if __name__ == "__main__":
    raise SystemExit(main())
