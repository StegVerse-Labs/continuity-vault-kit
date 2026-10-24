python3 - <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path

cycle_path = Path("docs/release_evidence/latest_cycle.json")
if cycle_path.exists():
    cycle = json.loads(cycle_path.read_text(encoding="utf-8"))
else:
    cycle = {}

release_required = cycle.get("release_required_after_run") is True
incomplete = cycle.get("outcome") == "INCOMPLETE"
recommendation = (
    "TVC_ADMITTED_RELEASE_CONTINUATION_REQUIRED"
    if incomplete and release_required
    else "NO_RELEASE_RECOVERY_REQUIRED"
)

out = Path("reports/release_cycle")
out.mkdir(parents=True, exist_ok=True)
payload = {
    "schema": "stegverse.kv.release-cycle-recovery-observation/v1",
    "state": recommendation,
    "source_outcome": cycle.get("outcome"),
    "release_required": release_required,
    "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "credential_authority": "TV/TVC",
    "github_actions_role": "VALIDATION_TRANSPORT_ONLY",
    "repository_mutation_performed": False,
    "workflow_dispatch_performed": False,
    "release_execution_performed": False,
    "authority_effect": "NONE",
}
(out / "hosted-release-recovery-observation.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
