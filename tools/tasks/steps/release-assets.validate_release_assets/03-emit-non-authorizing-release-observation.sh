python - <<'PY'
import json
from pathlib import Path
observation = {
    "schema": "stegverse.kv.hosted-release-observation/v1",
    "state": "BLOCKED_DEPENDENCY",
    "reason": "HOSTED_RELEASE_PUBLICATION_PROHIBITED_USE_TVC_ADMITTED_RELEASE_CAPABILITY",
    "credential_authority": "TV/TVC",
    "github_actions_role": "VALIDATION_TRANSPORT_ONLY",
    "release_publication_performed": False,
    "tag_mutation_performed": False,
    "authority_effect": "NONE",
}
Path("dist/HOSTED_RELEASE_OBSERVATION.json").write_text(
    json.dumps(observation, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
