"""Run the KV/SKAP loader node test (tests/loader/kv_skap_loader.test.mjs).

The node test evaluates the loader's inline script in a vm sandbox and checks it
against fixtures/skap/portable-envelope-v2.vectors.json and the digest-pinned TVC
POLICY_ADMISSION vectors. When no suitable node is available the test SKIPS with an
explicit reason; it never reports a pass it did not run.
"""

import hashlib
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "skap/loader/kv-skap-loader.html"
NODE_TEST = ROOT / "tests/loader/kv_skap_loader.test.mjs"
NODE_SKIP_EXIT = 77


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
            self.skipTest("node not found (set KV_SKAP_NODE or install node >= 20); loader JS tests NOT run")
        version = subprocess.run([node, "-p", "process.versions.node"], capture_output=True, text=True, timeout=30)
        major = int(version.stdout.strip().split(".")[0]) if version.returncode == 0 and version.stdout.strip() else 0
        if major < 20:
            self.skipTest(f"node {version.stdout.strip() or 'unknown'} lacks a stable globalThis.crypto.subtle; loader JS tests NOT run")
        result = subprocess.run([node, str(NODE_TEST)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        if result.returncode == NODE_SKIP_EXIT:
            self.skipTest("node reported WebCrypto unavailable; loader JS tests NOT run: " + result.stdout.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
