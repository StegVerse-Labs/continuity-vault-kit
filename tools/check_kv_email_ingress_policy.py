#!/usr/bin/env python3
"""Validate the canonical KnowledgeVault governed email-ingress policy."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "specs" / "kv-email-ingress-policy.v1.json"

REQUIRED_DECISIONS = {"ADMIT", "QUARANTINE", "REVIEW", "REJECT", "FAIL_CLOSED"}


def load_policy(path: Path = POLICY) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate(policy: dict) -> list[str]:
    errors: list[str] = []

    if policy.get("schema") != "stegverse.kv.email-ingress-policy/v1":
        errors.append("unexpected schema")
    if policy.get("service_id") != "email-continuity":
        errors.append("policy must bind to email-continuity")
    if policy.get("authority_effect") != "NONE":
        errors.append("email ingress must not grant authority")

    provider = policy.get("provider_session", {})
    if provider.get("authorization_required") is not True:
        errors.append("provider authorization must be required")
    if provider.get("credential_storage") != "REFERENCE_ONLY_NO_PLAINTEXT_SECRETS":
        errors.append("plaintext/reusable mailbox credentials are prohibited")
    if provider.get("provider_neutral") is not True:
        errors.append("canonical contract must remain provider-neutral")

    skap = policy.get("skap_credential_binding", {})
    if skap.get("required_for_activation") is not True:
        errors.append("SKAP Vault credential binding must be required for activation")
    if skap.get("vault") != "SKAP_VAULT":
        errors.append("credential binding must target SKAP Vault")
    if skap.get("kv_stores_secret") is not False:
        errors.append("KnowledgeVault must not store the mailbox secret")
    if skap.get("user_prompt_after_mapping") is not True:
        errors.append("user must be prompted to complete credential setup after mailbox mapping")

    staging = policy.get("staging", {})
    if staging.get("required") is not True:
        errors.append("pre-admission staging is required")
    if staging.get("trusted_kv_content_before_decision") is not False:
        errors.append("staged mail must not be trusted KV content")

    governance = policy.get("governance", {})
    if governance.get("default_on_ambiguity") != "FAIL_CLOSED":
        errors.append("ambiguous ingress must fail closed")

    rules = governance.get("rules", [])
    if not isinstance(rules, list) or not rules:
        errors.append("at least one governance rule is required")
    else:
        actions = {rule.get("action") for rule in rules if rule.get("enabled") is True}
        if "ADMIT" not in actions:
            errors.append("an enabled ADMIT path is required")
        if not ({"REJECT", "QUARANTINE", "REVIEW"} & actions):
            errors.append("an enabled non-admit governance path is required")

    admission = policy.get("admission", {})
    decisions = set(admission.get("allowed_decisions", []))
    if decisions != REQUIRED_DECISIONS:
        errors.append("allowed decisions must exactly match canonical decision vocabulary")
    if admission.get("trusted_content_decision") != "ADMIT":
        errors.append("only ADMIT may promote content to trusted KV state")

    receipt = policy.get("receipt", {})
    if receipt.get("required_for_every_evaluation") is not True:
        errors.append("every evaluated message requires a governance receipt")
    if receipt.get("retain_rejected_payload") is not False:
        errors.append("rejected payloads must not be retained by default")

    return errors


def main() -> int:
    errors = validate(load_policy())
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: governed KV email-ingress policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
