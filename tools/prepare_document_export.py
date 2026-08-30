#!/usr/bin/env python3
"""Prepare a governed KV document bundle and receipt for Publisher."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.document_export import DocumentExportError, prepare_document_export


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--bundle-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        bundle, receipt = prepare_document_export(request)
    except (OSError, json.JSONDecodeError, DocumentExportError) as exc:
        print(f"KV_DOCUMENT_EXPORT_REJECTED: {exc}", file=sys.stderr)
        return 1
    args.bundle_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.bundle_out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("KV_DOCUMENT_EXPORT_PREPARED_NOT_TRANSMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
