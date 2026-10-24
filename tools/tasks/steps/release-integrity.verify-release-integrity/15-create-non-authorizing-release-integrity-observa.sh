python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path
version = Path("VERSION").read_text(encoding="utf-8").strip()
zip_name = f"ContinuityVault_v{version}.zip"
manifest = json.loads((Path("dist") / f"{zip_name}.manifest.json").read_text(encoding="utf-8"))
checksum = (Path("dist") / f"{zip_name}.sha256").read_text(encoding="utf-8").split()[0]
changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
section = changelog.split("## [Unreleased]", 1)[1].split("\n---", 1)[0]
normalized = " ".join(section.split()).lower()
release_required = normalized not in {"", "_no unreleased changes._", "no unreleased changes."}
out = Path("reports/release_integrity")
out.mkdir(parents=True, exist_ok=True)
receipt = {
    "schema": "stegverse.kv.release-integrity-hosted-observation/v1",
    "result": "PASS",
    "repository": os.environ["REPOSITORY"],
    "commit_sha": os.environ["COMMIT_SHA"],
    "workflow_run_id": os.environ["RUN_ID"],
    "workflow_run_attempt": os.environ["RUN_ATTEMPT"],
    "version": version,
    "release_required": release_required,
    "release_artifact": zip_name,
    "release_sha256": checksum,
    "manifest_schema_version": manifest["schema_version"],
    "manifest_file_count": manifest["file_count"],
    "initializer_self_test": "PASS",
    "clean_room_user_kv_test": "PASS",
    "automation_contract_test": "PASS",
    "credential_authority": "TV/TVC",
    "github_actions_role": "VALIDATION_TRANSPORT_ONLY",
    "repository_mutation_performed": False,
    "tag_mutation_performed": False,
    "release_publication_performed": False,
    "canonical_evidence_transition_performed": False,
    "authority_effect": "NONE",
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
(out / "release-integrity-observation.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, sort_keys=True))
PY
