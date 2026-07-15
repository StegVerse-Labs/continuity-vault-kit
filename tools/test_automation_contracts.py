#!/usr/bin/env python3
"""Validate repository automation contracts without third-party dependencies."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THRESHOLD = 3

WORKFLOWS = {
    "release-integrity.yml": {
        "name: Release integrity",
        "python3 tools/test_release_tools.py",
        "python3 tools/test_init_vault.py",
        "python3 tools/test_automation_contracts.py",
        "actions/upload-artifact@v4",
        '"release_required": release_required',
    },
    "automated-release.yml": {
        "name: Automated verified release",
        "workflow_run:",
        "Determine whether a release is required",
        "## [Unreleased]",
        "gh release create",
    },
    "release-cycle-outcome.yml": {
        "name: Release cycle outcome",
        'workflows: ["Automated verified release"]',
        "latest_cycle.json",
        "latest_cycle.md",
        "PUBLISHED",
        "SKIPPED",
        "FAILED",
        "INCOMPLETE",
    },
    "downstream-propagation.yml": {"release:", "evidence/downstream-propagation"},
    "onboarding-friction-bootstrap.yml": {"workflow_dispatch:", "onboarding-friction"},
    "onboarding-friction.yml": {
        "name: Onboarding friction triage",
        "issues:",
        "automation-candidate",
        "evidence/onboarding-friction/latest.json",
    },
    "onboarding-friction-maintenance.yml": {"schedule:", "needs-reproduction", "workflow_dispatch"},
    "automation-candidate-lifecycle.yml": {
        "automation-candidate",
        "candidate-supported",
        "candidate-insufficient-evidence",
        "evidence/onboarding-friction/candidates",
    },
    "automation-candidate-implementation.yml": {
        "pull_request:",
        "types: [closed]",
        "candidate-supported",
        "contents: write",
        "Record implemented corrections in Unreleased changelog",
        "CHANGELOG.md",
        "git commit -m \"chore: record implemented automation candidate\"",
    },
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}")
    if not isinstance(value, dict):
        fail(f"expected object in {path.relative_to(REPO_ROOT)}")
    return value


def validate_workflows() -> None:
    workflow_root = REPO_ROOT / ".github" / "workflows"
    for filename, required_tokens in WORKFLOWS.items():
        text = read_text(workflow_root / filename)
        missing = sorted(token for token in required_tokens if token not in text)
        if missing:
            fail(f"{filename} missing contract tokens: {', '.join(missing)}")
        if "permissions:" not in text:
            fail(f"{filename} must declare permissions")
        if "runs-on:" not in text:
            fail(f"{filename} must declare a runner")
        if re.search(r"uses:\s+actions/(checkout|setup-python|upload-artifact)@(v1|v2|v3)\b", text):
            fail(f"{filename} uses an obsolete first-party action major")


def validate_release_cycle() -> None:
    integrity = read_text(REPO_ROOT / ".github" / "workflows" / "release-integrity.yml")
    release = read_text(REPO_ROOT / ".github" / "workflows" / "automated-release.yml")
    combined = integrity + "\n" + release
    forbidden = (
        "gh issue view 7",
        "gh issue view 8",
        "gh issue comment 7",
        "gh issue comment 8",
        "gh issue comment 10",
        "gh issue close 7",
        "gh issue close 8",
    )
    present = [token for token in forbidden if token in combined]
    if present:
        fail("release cycle contains historical issue gates: " + ", ".join(present))
    required = {
        "CHANGELOG.md",
        "## [Unreleased]",
        "release_required",
        "no unreleased changes; release skipped",
        "automation_contract_test",
    }
    missing = sorted(token for token in required if token not in combined)
    if missing:
        fail("release cycle missing issue-free gate tokens: " + ", ".join(missing))
    if "issues: write" in release:
        fail("automated release must not require issue-write permission")


def validate_release_cycle_outcome() -> None:
    receipt = read_json(REPO_ROOT / "docs" / "release_evidence" / "latest_cycle.json")
    required = {
        "schema_version",
        "outcome",
        "reason",
        "repository",
        "source_workflow",
        "source_workflow_conclusion",
        "source_workflow_run_id",
        "source_workflow_run_url",
        "source_head_sha",
        "current_version",
        "release_required_after_run",
        "generated_utc",
        "scope",
    }
    missing = sorted(required - receipt.keys())
    if missing:
        fail("release-cycle outcome receipt missing fields: " + ", ".join(missing))
    allowed = {"PUBLISHED", "SKIPPED", "FAILED", "INCOMPLETE", "RECONCILED"}
    outcome = receipt["outcome"]
    if outcome not in allowed:
        fail("release-cycle outcome is not recognized")
    expected_source = (
        "Reconcile published release evidence"
        if outcome == "RECONCILED"
        else "Automated verified release"
    )
    if receipt["source_workflow"] != expected_source:
        fail(
            "release-cycle receipt source workflow does not match outcome: "
            f"expected {expected_source!r} for {outcome!r}"
        )
    if not isinstance(receipt["release_required_after_run"], bool):
        fail("release_required_after_run must be boolean")
    scope = str(receipt["scope"]).lower()
    if "no certification of user-authored content" not in scope:
        fail("release-cycle outcome scope must preserve the content-certification boundary")
    read_text(REPO_ROOT / "docs" / "release_evidence" / "latest_cycle.md")


def validate_candidate_release_bridge() -> None:
    workflow = read_text(
        REPO_ROOT / ".github" / "workflows" / "automation-candidate-implementation.yml"
    )
    required = {
        "candidate-supported",
        "candidate-implemented",
        "CHANGELOG.md",
        "## [Unreleased]",
        "Automated onboarding correction",
        "git push origin HEAD:main",
    }
    missing = sorted(token for token in required if token not in workflow)
    if missing:
        fail("candidate implementation is not connected to release activation: " + ", ".join(missing))
    if "[skip ci]" in workflow:
        fail("candidate changelog commit must not suppress release-integrity validation")


def validate_friction_registry() -> None:
    registry = read_json(REPO_ROOT / "evidence" / "onboarding-friction" / "latest.json")
    required = {
        "schema_version",
        "generated_utc",
        "report_count",
        "threshold",
        "signature_counts",
        "reports",
        "privacy_scope",
    }
    missing = sorted(required - registry.keys())
    if missing:
        fail("friction registry missing fields: " + ", ".join(missing))
    if registry["threshold"] != THRESHOLD:
        fail(f"friction threshold must remain {THRESHOLD}")
    reports = registry["reports"]
    counts = registry["signature_counts"]
    if not isinstance(reports, list) or not isinstance(counts, dict):
        fail("friction reports/signature_counts have invalid types")
    if registry["report_count"] != len(reports):
        fail("friction report_count does not match reports")
    if "private vault content prohibited" not in str(registry["privacy_scope"]).lower():
        fail("friction privacy scope must prohibit private vault content")


def validate_issue_form() -> None:
    text = read_text(REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "onboarding-friction.yml")
    required = {
        "name: Onboarding friction",
        "onboarding-friction",
        "Platform",
        "Setup path",
        "Failure stage",
        "What you attempted",
        "What happened",
        "What you expected",
        "private vault content",
    }
    missing = sorted(token for token in required if token.lower() not in text.lower())
    if missing:
        fail("onboarding issue form missing fields/boundaries: " + ", ".join(missing))


def validate_threshold_consistency() -> None:
    paths = [
        REPO_ROOT / ".github" / "workflows" / "onboarding-friction.yml",
        REPO_ROOT / ".github" / "workflows" / "automation-candidate-lifecycle.yml",
        REPO_ROOT / "evidence" / "onboarding-friction" / "README.md",
        REPO_ROOT / "docs" / "CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md",
    ]
    joined = "\n".join(read_text(path).lower() for path in paths)
    if not any(phrase in joined for phrase in ("threshold: 3", "threshold = 3", "three reports", ">= 3")):
        fail("automation-candidate threshold is not durably represented")


def validate_scope_boundaries() -> None:
    handoff = read_text(REPO_ROOT / "docs" / "CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md").lower()
    required = {
        "standalone by default",
        "does not certify",
        "does not phone home",
        "smallest repository-native correction",
        "never authorizes access to or mutation of user vault content",
    }
    missing = sorted(token for token in required if token not in handoff)
    if missing:
        fail("handoff missing automation scope boundaries: " + ", ".join(missing))


def validate_downstream_config() -> None:
    config = read_json(REPO_ROOT / "automation" / "downstream-propagation.json")
    destinations = config.get("destinations")
    if not isinstance(destinations, list) or len(destinations) != 4:
        fail("downstream propagation must define exactly four destinations")
    serialized = json.dumps(config)
    required = {
        "StegVerse-Labs/Site",
        "GCAT-BCAT-Engine/Publisher",
        "StegVerse-Labs/admissibility-wiki",
        "StegVerse-002/stegguardian-wiki",
    }
    missing = sorted(item for item in required if item not in serialized)
    if missing:
        fail("downstream propagation missing destinations: " + ", ".join(missing))


def main() -> int:
    checks = [
        validate_workflows,
        validate_release_cycle,
        validate_release_cycle_outcome,
        validate_candidate_release_bridge,
        validate_friction_registry,
        validate_issue_form,
        validate_threshold_consistency,
        validate_scope_boundaries,
        validate_downstream_config,
    ]
    try:
        for check in checks:
            check()
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"OK: validated {len(checks)} automation contract groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
