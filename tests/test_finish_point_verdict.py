"""Both paths of the callable finish-point set verdict (StegVerse-org/.github#166).

NOT_SELECTED: a sealed DIFF selection, diff available, finish set not selected -> a sealed verdict carrying the
selection digest, head/base sha and reason; the finish step passes on it. SELECTED: everything else, including
every case where selection cannot be shown complete. The selector stub verifies seals with the same rule as the
pinned StegVerse-Labs selector (sha256 over sorted, compact JSON without receipt_sha256); CI loads the pinned
selector itself. The workflow checks assert no step carries an if:, so nothing in the job can be reported skipped.
Stdlib unittest, E0.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".stegverse" / "finish_point_verdict.py"
SPEC = json.loads((ROOT / ".stegverse" / "test-set-spec.json").read_text(encoding="utf-8"))
SET_ID = SPEC["finish_point_set"]
WORKFLOW = ROOT / next(p for p in SPEC["extra_surfaces"][SET_ID] if p.endswith(".yml"))

_spec = importlib.util.spec_from_file_location("finish_point_verdict", SCRIPT)
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)
SELECTOR = types.SimpleNamespace(seal_verifies=V.seal_verifies)
HEAD, BASE, PR_HEAD = "a" * 40, "b" * 40, "c" * 40


def record(**over):
    body = {"schema": "stegverse.test-set-selection/v1", "mode": "DIFF", "diff_available": True,
            "disposition": "ALLOW", "head_sha": HEAD, "base_sha": BASE, "pr_head_sha": PR_HEAD,
            "selected": [{"id": "core", "reasons": [{"reason": "ALWAYS_RUN_CORE"}]}],
            "selected_count": 1, "sets_total": 9, "all_reasons": []}
    body.update(over)
    return V.seal(body)


def cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT)


class NotSelectedPath(unittest.TestCase):
    def test_sealed_diff_without_the_set_is_a_receipted_not_selected(self):
        rec = record()
        v = V.decide("pull_request", SET_ID, rec, SELECTOR)
        self.assertEqual((v["verdict"], v["run"], v["reason"]), ("NOT_SELECTED", False, "NO_DIFF_PATH_IN_SET_CLOSURE"))
        self.assertTrue(V.seal_verifies(v))
        self.assertEqual((v["head_sha"], v["base_sha"], v["pr_head_sha"]), (HEAD, BASE, PR_HEAD))
        self.assertEqual(v["selection_receipt_sha256"], rec["receipt_sha256"])
        self.assertEqual(v["set_id"], SET_ID)

    def test_cli_decides_false_and_the_finish_step_check_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            sel, out = Path(tmp, "selection.json"), Path(tmp, "verdict.json")
            sel.write_text(json.dumps(record()), encoding="utf-8")
            stub = Path(tmp, "selector.py")
            stub.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            r = cli("decide", "--event", "pull_request", "--spec", ".stegverse/test-set-spec.json",
                    "--selection", str(sel), "--selector", str(stub), "--out", str(out))
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "run=false"))
            ok = cli("not-selected", str(out))
            self.assertEqual(ok.returncode, 0)
            self.assertEqual(json.loads(ok.stdout)["verdict"], "NOT_SELECTED")
            tampered = json.loads(out.read_text(encoding="utf-8"))
            tampered["head_sha"] = "d" * 40
            out.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertEqual(cli("not-selected", str(out)).returncode, 1)


class SelectedPath(unittest.TestCase):
    def test_a_diff_path_in_the_closure_selects_the_set(self):
        rec = record(selected=[{"id": SET_ID, "reasons": [{"reason": "DIFF_PATH_MATCHES_SURFACE"}]}])
        v = V.decide("pull_request", SET_ID, rec, SELECTOR)
        self.assertEqual((v["verdict"], v["run"], v["reason"]), ("SELECTED", True, "DIFF_PATH_IN_SET_CLOSURE"))

    def test_every_case_that_cannot_be_shown_complete_widens_to_selected(self):
        tampered = dict(record())
        tampered["selected"] = []
        cases = {
            "EVENT_ALWAYS_RUNS_THE_SET": ("push", SET_ID, record(), SELECTOR),
            "PINNED_LABS_SELECTOR_UNAVAILABLE": ("pull_request", SET_ID, record(), None),
            "SELECTION_RECORD_UNAVAILABLE": ("pull_request", SET_ID, None, SELECTOR),
            "SELECTION_SEAL_DOES_NOT_VERIFY": ("pull_request", SET_ID, tampered, SELECTOR),
            "SELECTION_MODE_ALL": ("pull_request", SET_ID, record(mode="ALL", all_reasons=[{"reason": "UNMAPPED_PATH"}]), SELECTOR),
            "DIFF_UNAVAILABLE": ("pull_request", SET_ID, record(diff_available=False), SELECTOR),
            "FINISH_POINT_SET_ID_UNAVAILABLE": ("pull_request", None, record(), SELECTOR),
        }
        for reason, args in cases.items():
            with self.subTest(reason=reason):
                v = V.decide(*args)
                self.assertEqual((v["verdict"], v["run"], v["reason"]), ("SELECTED", True, reason))
                self.assertTrue(V.seal_verifies(v))

    def test_cli_widens_without_selector_record_or_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp, "verdict.json")
            for args in (["--event", "pull_request", "--spec", ".stegverse/test-set-spec.json"],
                         ["--event", "pull_request", "--spec", str(Path(tmp, "missing.json"))],
                         ["--event", "push", "--spec", ".stegverse/test-set-spec.json"]):
                with self.subTest(args=args):
                    r = cli("decide", *args, "--selection", str(Path(tmp, "none.json")), "--selector", "",
                            "--out", str(out))
                    self.assertEqual((r.returncode, r.stdout.strip()), (0, "run=true"))
                    self.assertEqual(cli("not-selected", str(out)).returncode, 1)


class NoVisibleSkip(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_no_job_or_step_carries_an_if(self):
        self.assertEqual(re.findall(r"^\s*-?\s*if:", self.text, re.M), [])

    def test_select_never_fails_and_the_finish_step_receipts_or_runs(self):
        sel = self.text.split("id: select", 1)[1]
        self.assertIn("finish_point_verdict.py decide", sel)
        self.assertIn("set +e", sel)
        run_body = sel.split("run: |", 1)[1].split("\n      - name:", 1)[0]
        self.assertEqual(run_body.rstrip().splitlines()[-1].strip(), "exit 0")
        finish = sel.split("\n      - name:", 1)[1]
        gate = finish.index("finish_point_verdict.py not-selected")
        test = finish.index("python -m unittest")
        self.assertLess(gate, finish.index("tests.test_", gate))
        self.assertGreater(test, gate)
        self.assertIn("tests.test_finish_point_verdict", self.text.split("id: select", 1)[0])


if __name__ == "__main__":
    unittest.main()
