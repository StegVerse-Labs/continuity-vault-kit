#!/usr/bin/env python3
"""Static checks for the Personal KV finance source lane."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "KV_PERSONAL_FINANCE_MIRROR_HANDOFF.md"
SCHEMA = ROOT / "schemas" / "kv-personal-finance-snapshot.schema.json"
TEMPLATE = ROOT / "vault_template" / "KnowledgeVault" / "_Entities" / "Self" / "Personal_Finance.json"
RUNTIME = ROOT / "runtime" / "personal_finance.py"
TESTS = ROOT / "tests" / "test_personal_finance.py"

REQUIRED = (HANDOFF, SCHEMA, TEMPLATE, RUNTIME, TESTS)


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
    if missing:
        raise SystemExit("missing personal-finance source files: " + ", ".join(missing))

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    if schema.get("$id") != "https://stegverse.org/schemas/kv-personal-finance-snapshot.schema.json":
        raise SystemExit("unexpected personal-finance schema id")
    if template.get("schema_version") != "stegverse.kv.personal-finance/v1":
        raise SystemExit("unexpected template schema version")
    if template.get("execution_authority") is not False:
        raise SystemExit("template must not grant execution authority")

    forbidden_literals = (
        '"password"',
        '"access_token"',
        '"refresh_token"',
        '"private_key"',
        '"card_number"',
        '"account_number"',
        '"routing_number"',
        '"cvv"',
    )
    template_text = TEMPLATE.read_text(encoding="utf-8").lower()
    for token in forbidden_literals:
        if token in template_text:
            raise SystemExit(f"secret-bearing field present in KV template: {token}")

    print("KV personal finance static checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
