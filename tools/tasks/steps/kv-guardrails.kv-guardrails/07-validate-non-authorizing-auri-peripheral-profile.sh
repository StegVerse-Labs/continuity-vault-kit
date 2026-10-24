python3 - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator
schema = json.loads(Path('schemas/kv-auri-peripheral-capability-profiles.schema.json').read_text(encoding='utf-8'))
profiles = json.loads(Path('specs/kv-auri-peripheral-capability-profiles.v1.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(schema)
Draft202012Validator(schema).validate(profiles)
print('AURI_PERIPHERAL_SOURCE_SCHEMA_PASS')
PY
python3 scripts/validate_kv_auri_peripheral_profiles.py
python3 -m unittest tests.test_kv_auri_peripheral_profiles -v
