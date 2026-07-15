from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from typing import Mapping, Protocol, Sequence
from urllib.request import Request, urlopen

from .provider_activation import ProductionActivationProfile, ProviderSelection
from .provider_conformance import ProviderProbeResult


def _commit(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + sha256(payload).hexdigest()


class CommandRunner(Protocol):
    def run_json(self, argv: Sequence[str]) -> Mapping[str, object]: ...


class HttpProbeClient(Protocol):
    def head(self, url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str]]: ...


class UrlLibHttpProbeClient:
    def head(self, url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str]]:
        request = Request(url, method="HEAD", headers=dict(headers))
        with urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers.items())


@dataclass(frozen=True)
class AwsCliProbe:
    role: str
    selection_name: str
    service: str
    operation: str
    runner: CommandRunner

    def run(self, profile: ProductionActivationProfile, *, checked_at: int) -> ProviderProbeResult:
        selection: ProviderSelection = getattr(profile, self.selection_name)
        argv = ["aws", self.service, self.operation, "--region", selection.region, "--output", "json"]
        if self.service == "kms":
            argv += ["--key-id", selection.identity_ref]
        elif self.service == "dynamodb":
            argv += ["--table-name", selection.identity_ref]
        try:
            observed = self.runner.run_json(argv)
            identity = str(observed.get("KeyMetadata", observed.get("Table", observed)))
            success = True
            failure = None
        except Exception as exc:  # adapter converts provider errors into bounded evidence
            identity = selection.identity_ref
            success = False
            failure = type(exc).__name__.upper()
            observed = {"error_type": type(exc).__name__}
        result = ProviderProbeResult(
            role=self.role,
            resource_id=selection.identity_ref,
            observed_identity=identity,
            capability=f"{self.service}:{self.operation}",
            success=success,
            evidence_commitment=_commit(observed),
            checked_at=checked_at,
            failure_code=failure,
        ).with_hash()
        result.verify()
        return result


@dataclass(frozen=True)
class SpiffeWorkloadProbe:
    socket_env: str = "SPIFFE_ENDPOINT_SOCKET"

    def run(self, profile: ProductionActivationProfile, *, checked_at: int) -> ProviderProbeResult:
        selection = profile.ai_attestation
        socket = os.environ.get(self.socket_env, "")
        success = bool(socket and socket.startswith("unix://") and "UNCONFIGURED" not in selection.identity_ref)
        observed = {"socket": socket, "spiffe_id": selection.identity_ref}
        result = ProviderProbeResult(
            role="ai-entity-attestation",
            resource_id=selection.identity_ref,
            observed_identity=selection.identity_ref if success else "SPIFFE_ID_UNOBSERVED",
            capability="spiffe:workload-api-socket",
            success=success,
            evidence_commitment=_commit(observed),
            checked_at=checked_at,
            failure_code=None if success else "SPIFFE_WORKLOAD_API_UNAVAILABLE",
        ).with_hash()
        result.verify()
        return result


@dataclass(frozen=True)
class HttpsEndpointProbe:
    role: str
    selection_name: str
    client: HttpProbeClient
    token_env: str

    def run(self, profile: ProductionActivationProfile, *, checked_at: int) -> ProviderProbeResult:
        selection: ProviderSelection = getattr(profile, self.selection_name)
        token = os.environ.get(self.token_env, "")
        headers = {"Authorization": "Bearer " + token} if token else {}
        try:
            status, response_headers = self.client.head(selection.identity_ref, headers)
            success = 200 <= status < 400 and bool(token)
            failure = None if success else "ENDPOINT_AUTHENTICATION_FAILED"
            observed = {"status": status, "headers": dict(sorted(response_headers.items()))}
        except Exception as exc:
            success = False
            failure = type(exc).__name__.upper()
            observed = {"error_type": type(exc).__name__}
        result = ProviderProbeResult(
            role=self.role,
            resource_id=selection.identity_ref,
            observed_identity=selection.identity_ref,
            capability="https:authenticated-head",
            success=success,
            evidence_commitment=_commit(observed),
            checked_at=checked_at,
            failure_code=failure,
        ).with_hash()
        result.verify()
        return result


def default_live_probes(*, runner: CommandRunner, http_client: HttpProbeClient | None = None) -> tuple[object, ...]:
    client = http_client or UrlLibHttpProbeClient()
    return (
        AwsCliProbe("steg-id-signature", "steg_id", "kms", "describe-key", runner),
        SpiffeWorkloadProbe(),
        AwsCliProbe("key-custody", "key_custody", "kms", "describe-key", runner),
        AwsCliProbe("replicated-state", "state_store", "dynamodb", "describe-table", runner),
        HttpsEndpointProbe("ecosystem-chat", "chat_transport", client, "ECOSYSTEM_CHAT_PROBE_TOKEN"),
        HttpsEndpointProbe("master-records", "master_records", client, "MASTER_RECORDS_PROBE_TOKEN"),
    )
