"""Run the KV/SKAP loader node test (tests/loader/kv_skap_loader.test.mjs).

The node test evaluates the loader's inline script in a vm sandbox and checks it
against fixtures/skap/portable-envelope-v2.vectors.json and the digest-pinned TVC
POLICY_ADMISSION vectors.

This file is the SKAP loader callable test set. It is diff-selected by
.github/workflows/skap-loader-tests.yml (skap/loader/**, tests/loader/**, this file and
the fixtures the node test reads), and that job provides node 22. When the set is
selected and no suitable node runtime is present, it is never skipped: it emits a six-field
FAIL_CLOSED record (SKAP_LOADER_TEST_RUNTIME_NOT_PRESENT, StegVerse-org/.github#167
issuecomment-6372524861) and fails. It never reports a pass it did not run.
"""

import hashlib
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "skap/loader/kv-skap-loader.html"
NODE_TEST = ROOT / "tests/loader/kv_skap_loader.test.mjs"
NODE_SKIP_EXIT = 77
SELECTOR_WORKFLOW = ".github/workflows/skap-loader-tests.yml"


def runtime_not_present(detail):
    """Six-field FAIL_CLOSED record for a selected loader set whose node runtime is absent."""
    return {
        "disposition": "FAIL_CLOSED",
        "failure_code": "SKAP_LOADER_TEST_RUNTIME_NOT_PRESENT",
        "failed_predicate": "SKAP_LOADER_TEST_RUNTIME_PRESENT",
        "required_evidence_or_repair": "node >= 20 with globalThis.crypto.subtle, the runtime already declared for the loader surface "
                                       "(actions/setup-node node-version 22 in " + SELECTOR_WORKFLOW + "; locally set KV_SKAP_NODE); "
                                       "no new dependency",
        "retry_entrypoint": SELECTOR_WORKFLOW + " / python3 -m unittest tests.test_skap_loader_js -v",
        "owning_existing_goal": "SV-KV-AI-PERSISTENCE-001",
        "next_attempt": "on the next run of the selected loader set with the node runtime present",
        "detail": detail,
    }


def _find_node():
    for candidate in (os.environ.get("KV_SKAP_NODE"), shutil.which("node"), "/opt/node22/bin/node"):
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


class SKAPLoaderManifestTests(unittest.TestCase):
    def test_recorded_sha256_matches_loader_bytes(self):
        recorded = (ROOT / "skap/loader/kv-skap-loader.sha256").read_text(encoding="ascii").strip()
        self.assertRegex(recorded, r"^[0-9a-f]{64}$")
        self.assertEqual(hashlib.sha256(LOADER.read_bytes()).hexdigest(), recorded)


class SKAPLoaderJSTests(unittest.TestCase):
    def test_node_loader_suite(self):
        node = _find_node()
        if node is None:
            self._fail_closed("node not found (set KV_SKAP_NODE or install node >= 20); loader JS tests NOT run")
        version = subprocess.run([node, "-p", "process.versions.node"], capture_output=True, text=True, timeout=30)
        major = int(version.stdout.strip().split(".")[0]) if version.returncode == 0 and version.stdout.strip() else 0
        if major < 20:
            self._fail_closed(f"node {version.stdout.strip() or 'unknown'} lacks a stable globalThis.crypto.subtle; loader JS tests NOT run")
        result = subprocess.run([node, str(NODE_TEST)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        if result.returncode == NODE_SKIP_EXIT:
            self._fail_closed("node reported WebCrypto unavailable; loader JS tests NOT run: " + result.stdout.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("passed", result.stdout)

    def _fail_closed(self, detail):
        self.fail("FAIL_CLOSED " + json.dumps(runtime_not_present(detail), sort_keys=True))


class SKAPLoaderRuntimeAbsentTests(unittest.TestCase):
    """The absent-runtime path is a six-field FAIL_CLOSED failure, never a skip."""

    SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint", "owning_existing_goal", "next_attempt")

    def test_absent_runtime_fails_closed_not_skipped(self):
        from unittest import mock
        case = SKAPLoaderJSTests("test_node_loader_suite")
        result = unittest.TestResult()
        with mock.patch(__name__ + "._find_node", return_value=None):
            case.run(result)
        self.assertEqual(result.skipped, [])
        self.assertEqual(len(result.failures), 1)
        message = result.failures[0][1]
        record = json.loads(message[message.index("FAIL_CLOSED {") + len("FAIL_CLOSED "):].splitlines()[0])
        self.assertEqual(record["disposition"], "FAIL_CLOSED")
        self.assertEqual(record["failure_code"], "SKAP_LOADER_TEST_RUNTIME_NOT_PRESENT")
        for field in self.SIX:
            self.assertTrue(record[field], field)

    def test_no_skip_call_remains(self):
        self.assertNotIn("skip" + "Test(", Path(__file__).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
