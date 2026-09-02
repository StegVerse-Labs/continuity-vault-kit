from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from cross_platform_recovery import evaluate  # noqa: E402

data = json.loads((ROOT / "fixtures" / "kv_cross_platform_recovery_cases.json").read_text())
base = data["cases"][0]["package"]
receipt = evaluate("IPHONE_ICLOUD_TO_SAMSUNG_BROWSER", copy.deepcopy(base))
print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
if receipt["decision"] != "ALLOW_WITH_SIGNOFF":
    raise SystemExit(1)
