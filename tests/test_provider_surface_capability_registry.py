import json
import subprocess
import sys
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

    def test_initial_registry_is_fact_fail_closed(self):
        data = json.loads(REGISTRY.read_text())
        self.assertEqual(data["state"], "INSTALLED_UNVERIFIED")
        self.assertEqual(data["authority_effect"], "NONE")
        self.assertEqual(data["observations"], [])

if __name__ == "__main__":
    unittest.main()
