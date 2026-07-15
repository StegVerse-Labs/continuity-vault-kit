from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


REQUIRED_PROVIDERS = (
    "stegid_verify",
    "ai_entity_attestation",
    "key_custody",
    "authoritative_state",
    "ecosystem_chat",
    "master_records",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _commitment(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


def _configured(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value != "UNCONFIGURED"


@dataclass(frozen=True)
class ReadinessReport:
    environment: str
    ready: bool
    failures: tuple[str, ...]
    profile_commitment: str

    def payload(self) -> Mapping[str, object]:
        return {
            "environment": self.environment,
            "ready": self.ready,
            "failures": list(self.failures),
            "profile_commitment": self.profile_commitment,
        }


def validate_provider_profile(profile: Mapping[str, object]) -> ReadinessReport:
    failures: list[str] = []
    environment = str(profile.get("environment", ""))
    if environment not in {"staging", "production"}:
        failures.append("environment must be staging or production")

    providers = profile.get("providers")
    if not isinstance(providers, Mapping):
        providers = {}
        failures.append("providers object is required")

    for name in REQUIRED_PROVIDERS:
        provider = providers.get(name)
        if not isinstance(provider, Mapping):
            failures.append(f"provider missing: {name}")
            continue
        for field in ("technology", "resource_id", "evidence_commitment"):
            if not _configured(provider.get(field)):
                failures.append(f"{name}.{field} is unconfigured")
        if name in {"stegid_verify", "key_custody", "authoritative_state"} and not _configured(provider.get("region")):
            failures.append(f"{name}.region is unconfigured")
        if name == "ai_entity_attestation" and not _configured(provider.get("trust_domain")):
            failures.append("ai_entity_attestation.trust_domain is unconfigured")
        if name in {"ecosystem_chat", "master_records"}:
            endpoint = provider.get("endpoint")
            if not _configured(endpoint):
                failures.append(f"{name}.endpoint is unconfigured")
            else:
                parsed = urlparse(str(endpoint))
                if parsed.scheme != "https" or not parsed.netloc:
                    failures.append(f"{name}.endpoint must be an absolute HTTPS URL")

    rollback = profile.get("rollback")
    if not isinstance(rollback, Mapping):
        failures.append("rollback object is required")
    else:
        for field in ("procedure_ref", "revocation_receipt_ref"):
            if not _configured(rollback.get(field)):
                failures.append(f"rollback.{field} is unconfigured")

    return ReadinessReport(
        environment=environment,
        ready=not failures,
        failures=tuple(failures),
        profile_commitment=_commitment(profile),
    )


def load_and_validate(path: str | Path) -> ReadinessReport:
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(profile, Mapping):
        raise ValueError("provider profile must be a JSON object")
    return validate_provider_profile(profile)
