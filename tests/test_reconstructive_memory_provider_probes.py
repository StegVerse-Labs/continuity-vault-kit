from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from reconstructive_memory.provider_activation import ProductionActivationProfile, ProviderSelection
from reconstructive_memory.provider_probes import AwsCliProbe, HttpsEndpointProbe, SpiffeWorkloadProbe, default_live_probes


class Runner:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[list[str]] = []

    def run_json(self, argv):
        self.calls.append(list(argv))
        if self.fail:
            raise RuntimeError("provider unavailable")
        return {"KeyMetadata": {"Arn": "arn:observed"}}


class HttpClient:
    def __init__(self, status: int = 204) -> None:
        self.status = status
        self.headers = None

    def head(self, url, headers):
        self.headers = dict(headers)
        return self.status, {"x-provider-id": "observed"}


def selection(role: str, identity: str, region: str = "global") -> ProviderSelection:
    return ProviderSelection(role, "provider", "service", identity, region, "verified")


def profile() -> ProductionActivationProfile:
    return ProductionActivationProfile(
        profile_id="prod-1",
        environment="production",
        steg_id=selection("steg-id-signature", "arn:kms:steg", "us-east-1"),
        ai_attestation=selection("ai-entity-attestation", "spiffe://stegverse/ai"),
        key_custody=selection("key-custody", "arn:kms:custody", "us-east-1"),
        state_store=selection("replicated-state", "table-prod", "us-east-1"),
        chat_transport=selection("ecosystem-chat", "https://chat.example.test/health"),
        master_records=selection("master-records", "https://records.example.test/health"),
        rollback_ref="docs/rollback.md",
        created_at=1,
    ).with_hash()


class ProviderProbeTests(unittest.TestCase):
    def test_aws_probe_uses_configured_resource(self) -> None:
        runner = Runner()
        result = AwsCliProbe("steg-id-signature", "steg_id", "kms", "describe-key", runner).run(profile(), checked_at=2)
        self.assertTrue(result.success)
        self.assertIn("arn:kms:steg", runner.calls[0])
        result.verify()

    def test_aws_failure_is_bounded(self) -> None:
        result = AwsCliProbe("key-custody", "key_custody", "kms", "describe-key", Runner(True)).run(profile(), checked_at=2)
        self.assertFalse(result.success)
        self.assertEqual(result.failure_code, "RUNTIMEERROR")

    def test_spiffe_requires_workload_socket(self) -> None:
        with patch.dict(os.environ, {"SPIFFE_ENDPOINT_SOCKET": "unix:///run/spire/sockets/agent.sock"}, clear=False):
            result = SpiffeWorkloadProbe().run(profile(), checked_at=2)
        self.assertTrue(result.success)

    def test_https_probe_requires_token(self) -> None:
        client = HttpClient()
        with patch.dict(os.environ, {}, clear=True):
            result = HttpsEndpointProbe("ecosystem-chat", "chat_transport", client, "CHAT_TOKEN").run(profile(), checked_at=2)
        self.assertFalse(result.success)
        self.assertNotIn("Authorization", client.headers)

    def test_https_probe_does_not_commit_token(self) -> None:
        client = HttpClient()
        with patch.dict(os.environ, {"CHAT_TOKEN": "secret-value"}, clear=True):
            result = HttpsEndpointProbe("ecosystem-chat", "chat_transport", client, "CHAT_TOKEN").run(profile(), checked_at=2)
        self.assertTrue(result.success)
        self.assertNotIn("secret-value", str(result.payload()))

    def test_default_probe_set_covers_six_roles(self) -> None:
        probes = default_live_probes(runner=Runner(), http_client=HttpClient())
        self.assertEqual(len(probes), 6)


if __name__ == "__main__":
    unittest.main()
