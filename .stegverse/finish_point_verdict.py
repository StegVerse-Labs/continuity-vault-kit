"""Finish-point verdict for a callable test set: a sealed SELECTED or NOT_SELECTED record (StegVerse-org/.github#166).

The finish step always runs. It reads this verdict: NOT_SELECTED (a sealed DIFF selection from the pinned
StegVerse-Labs selector, with the diff available and the finish set not among the selected sets) is receipted and
the step ends 0 without running the test; every other case is SELECTED and the finish test runs with no skips.
Anything that cannot be shown complete widens to SELECTED: a non pull_request event, a selector that was not
fetched or did not match its sha256 pin, a missing or unreadable record, a seal that does not verify, mode ALL,
an unavailable diff, or any error here. Stdlib only, no clock, no network, authority effect NONE.

  decide       --event E --spec S [--selection R] [--selector P] [--head H] [--base B] [--pr-head P] --out V
               prints run=true|false (always exits 0)
  not-selected V   exits 0 only when V is a sealed NOT_SELECTED verdict, printing it; otherwise exits 1
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from typing import Any, Mapping

SCHEMA = "stegverse.finish-point-set-verdict/v1"
SEAL = "receipt_sha256"
GOAL = "StegVerse-org/.github#166 ENTERPRISE-HOST-PROVIDER-ERADICATION-001"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def seal(body: Mapping[str, Any]) -> dict:
    clean = {k: v for k, v in body.items() if k != SEAL}
    return {**clean, SEAL: "sha256:" + hashlib.sha256(canonical(clean)).hexdigest()}


def seal_verifies(record: Any) -> bool:
    return isinstance(record, Mapping) and seal(record).get(SEAL) == record.get(SEAL)


def load_selector(path: str | None):
    """The pinned selector module (already sha256-checked by the step), or None."""
    if not path:
        return None
    try:
        spec = importlib.util.spec_from_file_location("pinned_test_set_selection", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module if callable(getattr(module, "seal_verifies", None)) else None
    except Exception:  # noqa: BLE001 - an unloadable selector widens to SELECTED
        return None


def decide(event: str, set_id: str | None, record: Any, selector: Any, head: str | None = None,
           base: str | None = None, pr_head: str | None = None) -> dict:
    rec = record if isinstance(record, Mapping) else {}
    detail: Any = None
    if not set_id:
        verdict, reason = "SELECTED", "FINISH_POINT_SET_ID_UNAVAILABLE"
    elif event != "pull_request":
        verdict, reason = "SELECTED", "EVENT_ALWAYS_RUNS_THE_SET"
    elif selector is None:
        verdict, reason = "SELECTED", "PINNED_LABS_SELECTOR_UNAVAILABLE"
    elif not isinstance(record, Mapping):
        verdict, reason = "SELECTED", "SELECTION_RECORD_UNAVAILABLE"
    elif not selector.seal_verifies(record):
        verdict, reason = "SELECTED", "SELECTION_SEAL_DOES_NOT_VERIFY"
    elif rec.get("mode") != "DIFF":
        verdict, reason = "SELECTED", "SELECTION_MODE_ALL"
        detail = list(rec.get("all_reasons") or [])[:5]
    elif rec.get("diff_available") is not True:
        verdict, reason = "SELECTED", "DIFF_UNAVAILABLE"
    else:
        hit = [s for s in rec.get("selected") or [] if isinstance(s, Mapping) and s.get("id") == set_id]
        if hit:
            verdict, reason = "SELECTED", "DIFF_PATH_IN_SET_CLOSURE"
            detail = list(hit[0].get("reasons") or [])[:5]
        else:
            verdict, reason = "NOT_SELECTED", "NO_DIFF_PATH_IN_SET_CLOSURE"
            detail = {"selected_count": rec.get("selected_count"), "sets_total": rec.get("sets_total")}
    return seal({
        "schema": SCHEMA,
        "authority_effect": "NONE",
        "owning_existing_goal": GOAL,
        "set_id": set_id,
        "verdict": verdict,
        "run": verdict != "NOT_SELECTED",
        "reason": reason,
        "detail": detail,
        "event": event,
        "head_sha": rec.get("head_sha") or head,
        "base_sha": rec.get("base_sha") or base,
        "pr_head_sha": rec.get("pr_head_sha") or pr_head,
        "selection_mode": rec.get("mode"),
        "selection_disposition": rec.get("disposition"),
        "selection_receipt_sha256": rec.get(SEAL),
    })


def _read_json(path: str | None) -> Any:
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--event", default="")
    d.add_argument("--spec", required=True)
    d.add_argument("--selection")
    d.add_argument("--selector")
    d.add_argument("--head")
    d.add_argument("--base")
    d.add_argument("--pr-head")
    d.add_argument("--out", required=True)
    n = sub.add_parser("not-selected")
    n.add_argument("verdict")
    a = parser.parse_args(argv)
    if a.command == "not-selected":
        v = _read_json(a.verdict)
        ok = (seal_verifies(v) and v.get("schema") == SCHEMA and v.get("verdict") == "NOT_SELECTED"
              and v.get("run") is False and v.get("event") == "pull_request")
        if ok:
            print(json.dumps(v, indent=1, sort_keys=True))
        return 0 if ok else 1
    try:
        spec = _read_json(a.spec)
        set_id = spec.get("finish_point_set") if isinstance(spec, Mapping) else None
        verdict = decide(a.event, set_id, _read_json(a.selection), load_selector(a.selector), a.head, a.base,
                         a.pr_head)
    except Exception as exc:  # noqa: BLE001 - any error widens to SELECTED
        verdict = seal({"schema": SCHEMA, "authority_effect": "NONE", "owning_existing_goal": GOAL,
                        "verdict": "SELECTED", "run": True, "reason": "VERDICT_ERROR",
                        "detail": f"{type(exc).__name__}: {exc}", "event": a.event})
    try:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(verdict, indent=1, sort_keys=True) + "\n")
    except OSError:
        verdict = {**verdict, "run": True}
    print(f"run={'true' if verdict['run'] else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
