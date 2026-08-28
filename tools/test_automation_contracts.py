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
        "name: Automated release readiness - Validation Only",
        "workflow_run:",
        "Determine whether a release candidate is required",
        "## [Unreleased]",
        "TVC_ADMITTED_RELEASE_CONTINUATION_REQUIRED",
        "VALIDATION_TRANSPORT_ONLY",
        "actions/upload-artifact@v4",
    },
    "release-cycle-outcome.yml": {
        "name: Release cycle outcome - Validation Only",
        'workflows: ["Automated release readiness - Validation Only"]',
        "VALIDATION_TRANSPORT_ONLY",
        "repository_mutation_performed",
        "canonical_evidence_transition_performed",
        "actions/upload-artifact@v4",
    },
    "reconcile-published-release.yml": {
        "name: Reconcile published release evidence - Validation Only",
        "contents: read",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "TVC_ADMITTED_RELEASE_RECONCILIATION",
        "actions/upload-artifact@v4",
    },
    "reconcile-release-activation.yml": {
        "name: Activate release reconciliation - Validation Only",
        "contents: read",
        "VALIDATION_TRANSPORT_ONLY",
        "TVC_ADMITTED_RELEASE_RECONCILIATION_REQUIRED",
        "actions/upload-artifact@v4",
    },
    "release-cycle-recovery.yml": {
        "name: Release cycle recovery - Validation Only",
        'workflows: ["Release cycle outcome - Validation Only"]',
        "TVC_ADMITTED_RELEASE_CONTINUATION_REQUIRED",
        "VALIDATION_TRANSPORT_ONLY",
        "workflow_dispatch_performed",
        "actions/upload-artifact@v4",
    },
    "downstream-propagation.yml": {
        "name: Downstream release propagation - Validation Only",
        "contents: read",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_DOWNSTREAM_PROPAGATION_REVIEW",
        "actions/upload-artifact@v4",
    },
    "onboarding-friction-bootstrap.yml": {
        "name: Onboarding friction bootstrap - Validation Only",
        "workflow_dispatch:",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_LABEL_PROVISIONING_IF_REQUIRED",
        "actions/upload-artifact@v4",
    },
    "onboarding-friction.yml": {
        "name: Onboarding friction triage - Validation Only",
        "issues:",
        "threshold",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_FRICTION_RECONCILIATION",
        "actions/upload-artifact@v4",
    },
    "onboarding-friction-maintenance.yml": {
        "name: Onboarding friction maintenance - Validation Only",
        "schedule:",
        "workflow_dispatch:",
        "threshold",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_FRICTION_RECONCILIATION",
        "actions/upload-artifact@v4",
    },
    "automation-candidate-lifecycle.yml": {
        "name: Automation candidate lifecycle - Validation Only",
        "automation-candidate",
        "threshold",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_CANDIDATE_RECONCILIATION",
        "actions/upload-artifact@v4",
    },
    "production-provider-activation.yml": {
        "name: Production Provider Activation - Validation Only",
        "contents: read",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "TVC_ADMITTED_RESIDENT_PROVIDER_ACTIVATION",
        "actions/upload-artifact@v4",
    },
    "kv-format-branch.yml": {
        "name: KV Format Branch - Validation Only",
        "contents: read",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_FORMAT_PATCH_APPLICATION",
        "actions/upload-artifact@v4",
    },
    "sync-knowledgevault-overlay-from-stegdb.yml": {
        "contents: read",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_REPOSITORY_SYNC_REQUIRED",
        "actions/upload-artifact@v4",
    },
    "sync-overlay-from-stegdb.yml": {
        "contents: read",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_REPOSITORY_SYNC_REQUIRED",
        "actions/upload-artifact@v4",
    },
    "automation-candidate-implementation.yml": {
        "name: Automation candidate implementation - Validation Only",
        "pull_request:",
        "types: [closed]",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_CANDIDATE_RECONCILIATION",
        "candidate_lifecycle_mutation_performed",
        "repository_mutation_performed",
        "actions/upload-artifact@v4",
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


def validate_hosted_release_cycle_boundary() -> None:
    workflow_root = REPO_ROOT / ".github" / "workflows"
    for filename in (
        "release-integrity.yml",
        "automated-release.yml",
        "release-cycle-outcome.yml",
        "release-cycle-recovery.yml",
    ):
        text = read_text(workflow_root / filename)
        forbidden = {
            "contents: write",
            "actions: write",
            "git push",
            "github.token",
            "GH_TOKEN:",
            "gh workflow run",
            "gh release create",
            "git commit",
            "git tag",
            "git pull",
        }
        present = sorted(token for token in forbidden if token in text)
        if present:
            fail(f"{filename} reintroduces hosted release-cycle authority: {', '.join(present)}")
        required = {
            "contents: read",
            "persist-credentials: false",
            "VALIDATION_TRANSPORT_ONLY",
            "authority_effect",
            "NONE",
            "actions/upload-artifact@v4",
        }
        missing = sorted(token for token in required if token not in text)
        if missing:
            fail(f"{filename} missing validation-only boundary tokens: {', '.join(missing)}")


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







def validate_all_hosted_workflows_non_authorizing() -> None:
    workflow_root = REPO_ROOT / ".github" / "workflows"
    forbidden = {
        "contents: write",
        "actions: write",
        "issues: write",
        "pull-requests: write",
        "id-token: write",
        "packages: write",
        "deployments: write",
        "git push",
        "git commit",
        "git tag",
        "gh release ",
        "gh workflow run",
        "github.token",
        "GH_TOKEN:",
        "${{ secrets.",
        "aws-actions/configure-aws-credentials",
        "terraform apply",
        "kubectl apply",
        "helm upgrade",
        "repository_dispatch",
    }
    workflows = sorted(workflow_root.glob("*.yml"))
    if len(workflows) < 1:
        fail("no hosted workflows found for authority audit")
    for path in workflows:
        text = read_text(path)
        if "permissions:" not in text:
            fail(f"{path.name} must declare explicit permissions")
        present = sorted(token for token in forbidden if token in text)
        if present:
            fail(f"{path.name} reintroduces hosted authority: {', '.join(present)}")


def validate_kv_format_hosted_boundary() -> None:
    workflow = read_text(REPO_ROOT / ".github" / "workflows" / "kv-format-branch.yml")
    forbidden = {
        "contents: write",
        "git push",
        "git commit",
        "github.token",
        "GH_TOKEN:",
        "${{ secrets.",
    }
    present = sorted(token for token in forbidden if token in workflow)
    if present:
        fail("kv-format branch reintroduces hosted repository mutation: " + ", ".join(present))
    required = {
        "contents: read",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_FORMAT_PATCH_APPLICATION",
        "repository_mutation_performed",
        "git_push_performed",
        "actions/upload-artifact@v4",
        "authority_effect",
        "NONE",
    }
    missing = sorted(token for token in required if token not in workflow)
    if missing:
        fail("kv-format branch missing validation-only formatting tokens: " + ", ".join(missing))


def validate_stegdb_overlay_hosted_boundary() -> None:
    workflow_root = REPO_ROOT / ".github" / "workflows"
    for filename in ("sync-knowledgevault-overlay-from-stegdb.yml", "sync-overlay-from-stegdb.yml"):
        text = read_text(workflow_root / filename)
        forbidden = {
            "contents: write",
            "git push",
            "git commit",
            "github.token",
            "GH_TOKEN:",
            "${{ secrets.",
        }
        present = sorted(token for token in forbidden if token in text)
        if present:
            fail(f"{filename} reintroduces hosted StegDB overlay writeback: {', '.join(present)}")
        required = {
            "contents: read",
            "persist-credentials: false",
            "VALIDATION_TRANSPORT_ONLY",
            "NON_HOSTED_REPOSITORY_SYNC_REQUIRED",
            "repository_mutation_performed",
            "git_push_performed",
            "actions/upload-artifact@v4",
            "authority_effect",
            "NONE",
        }
        missing = sorted(token for token in required if token not in text)
        if missing:
            fail(f"{filename} missing validation-only overlay tokens: {', '.join(missing)}")


def validate_release_reconciliation_hosted_boundary() -> None:
    workflow_root = REPO_ROOT / ".github" / "workflows"
    files = (
        "downstream-propagation.yml",
        "reconcile-published-release.yml",
        "reconcile-release-activation.yml",
    )
    forbidden = {
        "contents: write",
        "actions: write",
        "issues: write",
        "git push",
        "git commit",
        "gh issue ",
        "gh workflow run",
        "github.token",
        "GH_TOKEN:",
        "${{ secrets.",
        "gh release ",
    }
    for filename in files:
        text = read_text(workflow_root / filename)
        present = sorted(token for token in forbidden if token in text)
        if present:
            fail(f"{filename} reintroduces hosted release/downstream authority: {', '.join(present)}")
        required = {
            "contents: read",
            "VALIDATION_TRANSPORT_ONLY",
            "authority_effect",
            "NONE",
            "actions/upload-artifact@v4",
        }
        if "actions/checkout@v4" in text:
            required.add("persist-credentials: false")
        missing = sorted(token for token in required if token not in text)
        if missing:
            fail(f"{filename} missing validation-only reconciliation tokens: {', '.join(missing)}")


def validate_production_provider_hosted_boundary() -> None:
    workflow = read_text(REPO_ROOT / ".github" / "workflows" / "production-provider-activation.yml")
    forbidden = {
        "id-token: write",
        "aws-actions/configure-aws-credentials",
        "role-to-assume:",
        "terraform plan",
        "terraform apply",
        "confirm_apply",
        "PROVIDER_ACTIVATION_AWS_ROLE_ARN",
        "github.token",
        "GH_TOKEN:",
        "${{ secrets.",
    }
    present = sorted(token for token in forbidden if token in workflow)
    if present:
        fail("production-provider activation reintroduces hosted production authority: " + ", ".join(present))
    required = {
        "contents: read",
        "persist-credentials: false",
        "terraform init -backend=false",
        "terraform validate",
        "VALIDATION_TRANSPORT_ONLY",
        "TVC_ADMITTED_RESIDENT_PROVIDER_ACTIVATION",
        "cloud_identity_acquired",
        "terraform_apply_performed",
        "provider_mutation_performed",
        "authority_effect",
        "NONE",
        "actions/upload-artifact@v4",
    }
    missing = sorted(token for token in required if token not in workflow)
    if missing:
        fail("production-provider activation missing validation-only boundary tokens: " + ", ".join(missing))


def validate_candidate_implementation_boundary() -> None:
    workflow = read_text(
        REPO_ROOT / ".github" / "workflows" / "automation-candidate-implementation.yml"
    )
    forbidden = {
        "contents: write",
        "actions: write",
        "issues: write",
        "git push",
        "git commit",
        "gh issue ",
        "gh workflow run",
        "github.token",
        "GH_TOKEN:",
        "CHANGELOG.md",
    }
    present = sorted(token for token in forbidden if token in workflow)
    if present:
        fail("candidate implementation reintroduces hosted mutation authority: " + ", ".join(present))
    required = {
        "contents: read",
        "pull-requests: read",
        "persist-credentials: false",
        "VALIDATION_TRANSPORT_ONLY",
        "NON_HOSTED_CANDIDATE_RECONCILIATION",
        "candidate_lifecycle_mutation_performed",
        "issue_mutation_performed",
        "changelog_mutation_performed",
        "repository_mutation_performed",
        "workflow_dispatch_performed",
        "actions/upload-artifact@v4",
        "authority_effect",
        "NONE",
    }
    missing = sorted(token for token in required if token not in workflow)
    if missing:
        fail("candidate implementation missing validation-only boundary tokens: " + ", ".join(missing))



def validate_hosted_onboarding_control_plane_boundary() -> None:
    workflow_root = REPO_ROOT / ".github" / "workflows"
    files = (
        "onboarding-friction.yml",
        "onboarding-friction-maintenance.yml",
        "onboarding-friction-bootstrap.yml",
        "automation-candidate-lifecycle.yml",
    )
    forbidden = {
        "contents: write",
        "actions: write",
        "issues: write",
        "pull-requests: write",
        "github.token",
        "GH_TOKEN:",
        "${{ secrets.",
        "gh label ",
        "gh issue ",
        "gh workflow run",
        "git push",
        "git commit",
        "git tag",
    }
    for filename in files:
        text = read_text(workflow_root / filename)
        present = sorted(token for token in forbidden if token in text)
        if present:
            fail(f"{filename} reintroduces hosted onboarding/candidate authority: {', '.join(present)}")
        required = {
            "contents: read",
            "VALIDATION_TRANSPORT_ONLY",
            "authority_effect",
            "NONE",
            "actions/upload-artifact@v4",
        }
        if "actions/checkout@v4" in text:
            required.add("persist-credentials: false")
        missing = sorted(token for token in required if token not in text)
        if missing:
            fail(f"{filename} missing validation-only hosted-control tokens: {', '.join(missing)}")


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
        "no undeclared outbound transmission",
        "explicit, revocable, scoped delegation",
        "standing preferences",
        "smallest repository-native correction",
        "repository automation does not independently grant authority",
    }
    missing = sorted(token for token in required if token not in handoff)
    if missing:
        fail("handoff missing delegated-authority boundaries: " + ", ".join(missing))


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
        validate_hosted_release_cycle_boundary,
        validate_release_cycle_outcome,
        validate_all_hosted_workflows_non_authorizing,
        validate_kv_format_hosted_boundary,
        validate_stegdb_overlay_hosted_boundary,
        validate_release_reconciliation_hosted_boundary,
        validate_production_provider_hosted_boundary,
        validate_candidate_implementation_boundary,
        validate_hosted_onboarding_control_plane_boundary,
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