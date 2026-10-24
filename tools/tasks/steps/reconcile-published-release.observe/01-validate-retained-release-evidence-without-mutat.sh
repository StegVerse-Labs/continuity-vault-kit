mkdir -p reports/release_reconciliation
python3 - <<'PY'
import json, os
from datetime import datetime, timezone
from pathlib import Path
version=Path("VERSION").read_text(encoding="utf-8").strip()
release_path=Path("docs/release_evidence/latest_release.json")
release=json.loads(release_path.read_text(encoding="utf-8")) if release_path.exists() else {}
retained_tag=release.get("tag")
requested=os.environ.get("INPUT_TAG") or None
consistent=(not requested or requested==retained_tag)
payload={
    "schema":"stegverse.kv.release-reconciliation-observation/v1",
    "repository":os.environ["REPOSITORY"],
    "persistent_version":version,
    "retained_release_tag":retained_tag,
    "requested_release_tag":requested,
    "retained_evidence_consistent_with_request":consistent,
    "canonical_release_evidence_mutation_performed":False,
    "repository_mutation_performed":False,
    "issue_mutation_performed":False,
    "release_publication_performed":False,
    "github_actions_role":"VALIDATION_TRANSPORT_ONLY",
    "credential_authority":"TV/TVC",
    "canonical_next_transition":"TVC_ADMITTED_RELEASE_RECONCILIATION" if requested and not consistent else "NONE",
    "authority_effect":"NONE",
    "observed_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
}
Path("reports/release_reconciliation/observation.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(payload,sort_keys=True))
PY
