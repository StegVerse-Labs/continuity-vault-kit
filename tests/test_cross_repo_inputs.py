"""Pinned cross-repository inputs of the Workspace parity tests (StegVerse-org/.github#166). Stdlib unittest, E0.

The three parity tests read sibling checkouts of StegVerse-Labs/Site and StegVerse-Labs/.github. The pin names each
commit and the sha256 of every file read; .stegverse/cross_repo_inputs.py fetches exactly that commit anonymously and
fails (never skips) on any mismatch, and never overwrites an existing checkout. These tests use local file:// git
repositories only: no network. They also assert the pin lists exactly the tests whose skip guard reads those
checkouts, and the workflow deselects them from the Workspace step only to run them in the parity step.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".stegverse" / "cross_repo_inputs.py"
PIN_PATH = ROOT / ".stegverse" / "workspace-parity-pin.json"
WORKFLOW = ROOT / ".github" / "workflows" / "runtime-import-and-secret-policy.yml"
SPEC = json.loads((ROOT / ".stegverse" / "test-set-spec.json").read_text(encoding="utf-8"))

_spec = importlib.util.spec_from_file_location("cross_repo_inputs", SCRIPT)
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
PIN = C.load(PIN_PATH)
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t",
       "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout.strip()


def upstream(tmp: Path, files: dict) -> tuple[str, str]:
    repo = tmp / "upstream"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "uploadpack.allowReachableSHA1InWant", "true")
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "pinned")
    return repo.as_uri(), git(repo, "rev-parse", "HEAD")


def pin_for(url, commit, files, dest="../dep"):
    return {"schema": C.SCHEMA, "tests": [], "inputs": {"dep": {
        "url": url, "commit": commit, "dest": dest,
        "files": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()}}}}


class Materialize(unittest.TestCase):
    def test_fetches_the_pinned_commit_and_checks_every_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            files = {"assets/a.js": "A", "scripts/b.py": "B"}
            url, commit = upstream(tmp, files)
            (tmp / "work").mkdir()
            lines = C.materialize(pin_for(url, commit, files), tmp / "work")
            self.assertEqual(git(tmp / "dep", "rev-parse", "HEAD"), commit)
            self.assertEqual(len([l for l in lines if l.startswith(str((tmp / "dep").resolve()))]), 2)
            again = C.materialize(pin_for(url, commit, files), tmp / "work")
            self.assertIn("verified, not overwritten", again[0])

    def test_a_sha256_mismatch_fails_and_an_existing_checkout_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            files = {"assets/a.js": "A"}
            url, commit = upstream(tmp, files)
            (tmp / "work").mkdir()
            with self.assertRaises(C.InputUnavailable):
                C.materialize(pin_for(url, commit, {"assets/a.js": "not A"}), tmp / "work")
            (tmp / "dep" / "assets" / "a.js").write_text("local edit", encoding="utf-8")
            with self.assertRaises(C.InputUnavailable):
                C.materialize(pin_for(url, commit, files), tmp / "work")
            self.assertEqual((tmp / "dep" / "assets" / "a.js").read_text(encoding="utf-8"), "local edit")

    def test_an_unfetchable_commit_or_absent_input_fails_with_the_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            files = {"assets/a.js": "A"}
            url, _ = upstream(tmp, files)
            (tmp / "work").mkdir()
            with self.assertRaises(C.InputUnavailable):
                C.materialize(pin_for(url, "0" * 40, files), tmp / "work")
            with self.assertRaises(C.InputUnavailable):
                C.materialize(pin_for(url, "0" * 40, files, dest="../absent"), tmp / "work", allow_fetch=False)

    def test_cli_exits_nonzero_with_required_verification_input_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, "pin.json")
            bad.write_text(json.dumps({"schema": "other"}), encoding="utf-8")
            r = subprocess.run(["python3", str(SCRIPT), "verify", str(bad)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("REQUIRED_VERIFICATION_INPUT_UNAVAILABLE", r.stderr)


class PinMatchesTheTests(unittest.TestCase):
    def test_pin_shape(self):
        self.assertEqual(PIN["authority_effect"], "NONE")
        for name, decl in PIN["inputs"].items():
            self.assertTrue(decl["url"].startswith("https://github.com/StegVerse-Labs/"), name)
            self.assertRegex(decl["commit"], r"^[0-9a-f]{40}$")
            for digest in decl["files"].values():
                self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_pinned_tests_are_exactly_the_skip_guarded_sibling_checkout_tests(self):
        guarded = []
        for f in sorted((ROOT / "tests").glob("test_workspace_*.py")):
            tree = ast.parse(f.read_text(encoding="utf-8"))
            helpers = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("test_")
                       and "pytest.skip" in ast.unparse(n)}
            for n in tree.body:
                if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
                    src = ast.unparse(n)
                    if "pytest.skip" in src or any(h + "(" in src for h in helpers):
                        guarded.append(f"tests/{f.name}::{n.name}")
        self.assertEqual(sorted(guarded), sorted(PIN["tests"]))

    def test_every_sibling_path_the_tests_read_is_a_pinned_file(self):
        pinned = {(Path(d["dest"]).name, rel) for d in PIN["inputs"].values() for rel in d["files"]}
        needed = {("site", "assets/workspace-session-authentication.js"),
                  ("site", "assets/workspace-assistant-binding.js"),
                  ("gh", "scripts/user_facing_explanation.py"),
                  ("gh", "schemas/user-facing-explanation.v1.schema.json")}
        self.assertEqual(pinned, needed)
        sources = (ROOT / "tests" / "test_workspace_session_authentication.py").read_text(encoding="utf-8") + \
            (ROOT / "tests" / "test_workspace_decision_reasons.py").read_text(encoding="utf-8")
        for repo, rel in needed - {("gh", "schemas/user-facing-explanation.v1.schema.json")}:
            self.assertIn(Path(rel).name, sources)

    def test_parity_sets_are_the_files_holding_the_pinned_tests(self):
        self.assertEqual(sorted(SPEC[PIN["set_key"]]), sorted({t.split("::")[0] for t in PIN["tests"]}))
        for f in SPEC[PIN["set_key"]]:
            self.assertIn(".stegverse/workspace-parity-pin.json", SPEC["extra_surfaces"][f])


class WorkflowUsesThePin(unittest.TestCase):
    def test_workspace_step_deselects_only_the_pinned_ids_and_fails_on_skips(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        step = text.split("- name: Workspace projection contract", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("cross_repo_inputs.py tests .stegverse/workspace-parity-pin.json", step)
        self.assertIn("deselected", step)
        self.assertIn("skips are never accepted", step)
        self.assertNotIn("::test_", step)
        parity = text.split("- name: Workspace cross-repository parity", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("skips are never accepted", parity)
        self.assertNotIn("continue-on-error", text)


if __name__ == "__main__":
    unittest.main()
