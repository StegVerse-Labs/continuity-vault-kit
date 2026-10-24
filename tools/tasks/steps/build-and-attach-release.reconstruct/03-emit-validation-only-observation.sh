python - <<'PY'
import json
from pathlib import Path
observation = {
    "schema": "stegverse.kv.published-release-reconstruction/v1",
    "state": "SOURCE_RECONSTRUCTED_RELEASE_NOT_MUTATED",
    "credential_authority": "TV/TVC",
    "github_actions_role": "VALIDATION_TRANSPORT_ONLY",
    "release_asset_mutation_performed": False,
    "release_publication_performed": False,
    "authority_effect": "NONE",
}
Path("dist/HOSTED_RELEASE_OBSERVATION.json").write_text(
    json.dumps(observation, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
