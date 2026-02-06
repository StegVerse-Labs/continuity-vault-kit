#!/usr/bin/env python3
"""
kv_layer_check.py — StegDB-style layer boundary enforcement for KnowledgeVault.

- validate   : fail CI if boundaries/labels violated
- auto-label : add/update footers only (no moves/deletes)
- suggest    : report conservative suggestions (no moves/deletes)
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
COMMENT_RE = re.compile(r"<!--\s*StegDB:\s*kv\.layer\.v1\s*\|\s*LAYER=([A-Z_]+)\s*\|\s*SCOPE=([^>]+?)\s*-->")

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
    fw = cfg["layers"]["FRAMEWORK"]
    if rel in fw.get("paths", []):
        return "FRAMEWORK"
    if match_any(rel, fw.get("globs", [])):
        return "FRAMEWORK"
    rt = cfg["layers"]["RUNTIME_TEMPLATE"]
    if match_any(rel, rt.get("globs", [])):
        return "RUNTIME_TEMPLATE"
    return "UNKNOWN"

def parse_footer(text: str) -> Tuple[str|None, str|None]:
    m = COMMENT_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    em = re.search(r"🧭\s*\*\*KV Layer:\*\*\s*([A-Z_]+)", text)
    sc = re.search(r"🏷️\s*\*\*KV Scope:\*\*\s*(.+)", text)
    return (em.group(1).strip() if em else None, sc.group(1).strip() if sc else None)

def strip_existing_footer(text: str) -> str:
    # Remove existing footer block if present, by truncating from the nearest separator above it.
    idx = text.find("StegDB: kv.layer.v1")
    if idx == -1:
        idx = text.find("🧬 **StegDB:** managed • rule=kv.layer.v1")
    if idx == -1:
        return text
    sep_idx = text.rfind("\n---", 0, idx)
    if sep_idx == -1:
        return text[:idx].rstrip() + "\n"
    return text[:sep_idx].rstrip() + "\n"

def build_footer(layer: str, cfg: dict) -> str:
    d = cfg["defaults"]
    if layer == "RUNTIME_TEMPLATE":
        scope = d["scope_runtime"]
        safety = d["safety_runtime"]
    else:
        scope = d["scope_framework"]
        safety = d["safety_framework"]

    mf = cfg["enforce"]["markdown_footer"]
    sep = mf.get("footer_separator", "---")
    comment = mf["comment_footer_template"].format(LAYER=layer, SCOPE=scope)
    emoji_lines = [ln.format(LAYER=layer, SCOPE=scope, SAFETY=safety) for ln in mf["emoji_footer_template"]]
    emoji = "\n".join(emoji_lines)

    parts = ["", sep, "", comment, "", emoji, ""]
    return "\n".join(parts)

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

    violations = []
    suggestions = []
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

        if p.suffix.lower() != ".md":
            continue

        text = p.read_text(encoding="utf-8", errors="replace")
        hits = [mk for mk in cfg["enforce"].get("hard_fail_markers", []) if mk in text]
        if hits:
            violations.append((r, "HARD_FAIL_MARKER", f"Found: {', '.join(hits)}"))
            continue

        layer = expected_layer(r, cfg)
        if layer in ("FRAMEWORK", "RUNTIME_TEMPLATE"):
            found_layer, _ = parse_footer(text)
            if found_layer is None:
                violations.append((r, "MISSING_FOOTER", f"Expected footer for {layer}"))
                if args.mode == "auto-label":
                    new_text = strip_existing_footer(text).rstrip() + build_footer(layer, cfg)
                    p.write_text(new_text, encoding="utf-8")
                    touched += 1
            elif found_layer != layer:
                violations.append((r, "FOOTER_MISMATCH", f"Expected {layer}, found {found_layer}"))
                if args.mode == "auto-label":
                    new_text = strip_existing_footer(text).rstrip() + build_footer(layer, cfg)
                    p.write_text(new_text, encoding="utf-8")
                    touched += 1

        if args.mode == "suggest":
            if r.startswith("docs/") and ("vault_template" in text or "00_Inbox" in text or "_Index" in text):
                suggestions.append((r, "MAYBE_TEMPLATE_DOC", "Consider moving to vault_template/KnowledgeVault/ or rewriting as framework doc."))

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

    return 1 if (violations and args.mode == "validate") else 0

if __name__ == "__main__":
    raise SystemExit(main())
