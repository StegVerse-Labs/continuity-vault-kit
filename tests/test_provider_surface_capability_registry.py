import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "specs" / "kv-provider-surface-capability-registry.v1.json"
CHECKER = ROOT / "tools" / "check_provider_surface_capability_registry.py"

class ProviderSurfaceCapabilityRegistryTests(unittest.TestCase):
    def test_canonical_registry_passes(self):
        run = subprocess.run([sys.executable, str(CHECKER)], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("KV_PROVIDER_SURFACE_CAPABILITY_REGISTRY=PASS", run.stdout)

    def test_documented_registry_is_still_unverified(self):
        data = json.loads(REGISTRY.read_text())
        self.assertEqual(data["state"], "DOCUMENTED_UNVERIFIED")
        self.assertEqual(data["authority_effect"], "NONE")
        self.assertEqual(len(data["observations"]), 8)
        self.assertTrue(all(item["knowledge_state"] == "DOCUMENTED" for item in data["observations"]))
        self.assertTrue(all(item["evidence"]["source_type"] == "provider_documentation" for item in data["observations"]))
        self.assertFalse(any(item["knowledge_state"] == "VERIFIED" for item in data["observations"]))

    def test_documented_claim_without_provider_evidence_fails_closed(self):
        data = json.loads(REGISTRY.read_text())
        data["observations"][0]["evidence"]["source_type"] = "unknown"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            run = subprocess.run([sys.executable, str(CHECKER), str(path)], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("documented_without_provider_evidence", run.stdout)

    def test_partially_verified_state_requires_verified_observation(self):
        data = json.loads(REGISTRY.read_text())
        data["state"] = "PARTIALLY_VERIFIED"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad-state.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            run = subprocess.run([sys.executable, str(CHECKER), str(path)], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("partially_verified_without_verified_observation", run.stdout)

if __name__ == "__main__":
    unittest.main()
