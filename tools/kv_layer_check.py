#!/usr/bin/env python3
"""StegDB-style layer boundary enforcement for continuity-vault-kit.

Modes:
- validate: validate known layer labels and forbidden footer claims.
- auto-label: add or normalize canonical Markdown footers; never move/delete files.
- suggest: emit conservative placement suggestions; never mutate files.

Canonical visible footers:
- 🔒 Layer: Framework | KV
- 🔒 Layer: Vault Template | KV
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
CONFIG_PATH = REPO_ROOT / ".stegdb" / "kv-layer.v1.json"

LEGACY_COMMENT_RE = re.compile(
    r"<!--\s*StegDB:\s*kv\.layer\.v1\s*\|\s*LAYER=([A-Z_]+)\s*\|\s*SCOPE=([^>]+?)\s*-->",
    re.MULTILINE,
)
VISIBLE_FOOTER_RE = re.compile(
    r"^🔒\s*Layer:\s*(Framework|Vault Template|Personal Vault|Personal)\s*\|\s*KV\s*$",
    re.MULTILINE,
)
LEGACY_LAYER_RE = re.compile(r"🧭\s*\*\*KV Layer:\*\*\s*([A-Z_]+)")
LEGACY_SCOPE_RE = re.compile(r"🏷️\s*\*\*KV Scope:\*\*\s*(.+)")

FOOTER_BY_LAYER = {
    "FRAMEWORK": "🔒 Layer: Framework | KV",
    "RUNTIME_TEMPLATE": "🔒 Layer: Vault Template | KV",
}
VISIBLE_TO_LAYER = {
    "Framework": "FRAMEWORK",
    "Vault Template": "RUNTIME_TEMPLATE",
    "Personal Vault": "PERSONAL_VAULT",
    "Personal": "PERSONAL_VAULT",
}
SKIP_PARTS = {".git", "dist", "node_modules", ".venv", "venv", "__pycache__"}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"ERROR: Missing config: {CONFIG_PATH}")
        raise SystemExit(2)
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: Invalid config {CONFIG_PATH}: {exc}")
        raise SystemExit(2) from exc


def relpath(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def match_any(rel: str, globs: List[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pattern.replace(os.sep, "/")) for pattern in globs)


def expected_layer(rel: str, cfg: dict) -> str:
    framework = cfg["layers"]["FRAMEWORK"]
    runtime = cfg["layers"]["RUNTIME_TEMPLATE"]
    if rel in framework.get("paths", []) or match_any(rel, framework.get("globs", [])):
        return "FRAMEWORK"
    if match_any(rel, runtime.get("globs", [])):
        return "RUNTIME_TEMPLATE"
    return "UNKNOWN"


def parse_footer(text: str) -> Tuple[str | None, str | None]:
    visible = list(VISIBLE_FOOTER_RE.finditer(text))
    if visible:
        label = visible[-1].group(1).strip()
        return VISIBLE_TO_LAYER[label], label

    comment = list(LEGACY_COMMENT_RE.finditer(text))
    if comment:
        match = comment[-1]
        return match.group(1).strip(), match.group(2).strip()

    layer = list(LEGACY_LAYER_RE.finditer(text))
    scope = list(LEGACY_SCOPE_RE.finditer(text))
    return (
        layer[-1].group(1).strip() if layer else None,
        scope[-1].group(1).strip() if scope else None,
    )


def strip_existing_footer(text: str) -> str:
    markers = (
        "🔒 Layer:",
        "StegDB: kv.layer.v1",
        "🧭 **KV Layer:**",
        "🧬 **StegDB:** managed • rule=kv.layer.v1",
    )
    index = max((text.rfind(marker) for marker in markers), default=-1)
    if index < 0:
        return text
    separator = text.rfind("\n---", 0, index)
    cut = separator if separator >= 0 else index
    return text[:cut].rstrip() + "\n"


def build_footer(layer: str) -> str:
    return f"\n\n---\n\n{FOOTER_BY_LAYER[layer]}\n"


def has_canonical_footer(text: str, layer: str) -> bool:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines or lines[-1].strip() != FOOTER_BY_LAYER[layer]:
        return False
    index = len(lines) - 2
    while index >= 0 and not lines[index].strip():
        index -= 1
    return index >= 0 and lines[index].strip() == "---"


def is_binary(path: Path) -> bool:
    try:
        return b"\x00" in path.read_bytes()
    except OSError:
        return False


def iter_files() -> List[Path]:
    return [
        path
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and not any(part in SKIP_PARTS for part in path.parts)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["validate", "auto-label", "suggest"], default="validate")
    parser.add_argument("--paths", nargs="*", default=[], help="Optional repository-relative globs")
    args = parser.parse_args()

    cfg = load_config()
    enforcement = cfg.get("enforce", {})
    footer_cfg = enforcement.get("markdown_footer", {})
    footer_required = bool(footer_cfg.get("required", True))
    forbidden_lines = set(enforcement.get("forbidden_footer_lines", []))

    violations: List[Tuple[str, str, str]] = []
    suggestions: List[Tuple[str, str, str]] = []
    touched = 0
    total_binary_bytes = 0

    for path in iter_files():
        rel = relpath(path)
        if args.paths and not match_any(rel, args.paths):
            continue

        binary_cfg = enforcement.get("binary_disallow", {})
        if binary_cfg.get("enabled", False) and is_binary(path):
            total_binary_bytes += path.stat().st_size

        if path.suffix.lower() != ".md":
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        found_forbidden = [line for line in forbidden_lines if re.search(rf"(?m)^\s*{re.escape(line)}\s*$", text)]
        if found_forbidden:
            violations.append((rel, "FORBIDDEN_FOOTER", ", ".join(sorted(found_forbidden))))
            continue

        layer = expected_layer(rel, cfg)
        if layer not in FOOTER_BY_LAYER:
            continue

        found_layer, _ = parse_footer(text)
        missing = found_layer is None
        mismatch = found_layer is not None and found_layer != layer
        noncanonical = found_layer == layer and not has_canonical_footer(text, layer)

        if args.mode == "auto-label" and (missing or mismatch or noncanonical):
            normalized = strip_existing_footer(text).rstrip() + build_footer(layer)
            path.write_text(normalized, encoding="utf-8", newline="\n")
            touched += 1
            continue

        if mismatch:
            violations.append((rel, "FOOTER_MISMATCH", f"expected {layer}, found {found_layer}"))
        elif missing and footer_required:
            violations.append((rel, "MISSING_FOOTER", f"expected {FOOTER_BY_LAYER[layer]}"))
        elif noncanonical:
            violations.append((rel, "NONCANONICAL_FOOTER", f"expected final footer {FOOTER_BY_LAYER[layer]}"))

        if args.mode == "suggest" and rel.startswith("docs/"):
            if any(token in text for token in ("vault_template", "00_Inbox", "_Index")):
                suggestions.append((
                    rel,
                    "MAYBE_TEMPLATE_DOC",
                    "Review whether this is framework guidance or content that belongs under vault_template/KnowledgeVault/.",
                ))

    binary_cfg = enforcement.get("binary_disallow", {})
    limit = int(binary_cfg.get("max_binary_bytes_in_repo", 0) or 0)
    if binary_cfg.get("enabled", False) and limit and total_binary_bytes > limit:
        violations.append(("<repo>", "BINARY_SIZE_LIMIT", f"{total_binary_bytes} bytes exceeds {limit}"))

    if violations:
        print("\nKV Layer Check — Violations")
        for rel, code, message in violations:
            print(f"- {rel}: {code} — {message}")

    if suggestions:
        print("\nKV Layer Check — Suggestions")
        for rel, code, message in suggestions:
            print(f"- {rel}: {code} — {message}")

    if args.mode == "auto-label":
        print(f"\nAuto-label: updated {touched} file(s).")
    elif not violations:
        state = "required" if footer_required else "bootstrap/advisory"
        print(f"KV Layer Check — OK (footer policy: {state}).")

    return 1 if args.mode == "validate" and violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
