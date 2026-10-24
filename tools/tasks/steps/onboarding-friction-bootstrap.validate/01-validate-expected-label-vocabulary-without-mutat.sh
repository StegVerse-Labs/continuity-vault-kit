mkdir -p reports/onboarding_friction
python3 - <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path
labels=[
    "onboarding-friction","needs-reproduction","automation-candidate",
    "friction:ios","friction:android","friction:windows","friction:macos",
    "friction:linux","friction:other","friction:initializer","friction:unzip",
    "friction:manual-copy","friction:release-verification","friction:markdown",
    "friction:first-use"
]
payload={
    "schema":"stegverse.kv.onboarding-friction-bootstrap-observation/v1",
    "expected_labels":labels,
    "label_mutation_performed":False,
    "issue_mutation_performed":False,
    "repository_mutation_performed":False,
    "github_actions_role":"VALIDATION_TRANSPORT_ONLY",
    "canonical_next_transition":"NON_HOSTED_LABEL_PROVISIONING_IF_REQUIRED",
    "authority_effect":"NONE",
    "observed_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
}
Path("reports/onboarding_friction/bootstrap-observation.json").write_text(
    json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(payload,sort_keys=True))
PY
