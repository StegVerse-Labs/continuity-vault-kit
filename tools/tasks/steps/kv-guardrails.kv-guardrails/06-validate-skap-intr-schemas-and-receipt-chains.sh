python3 - <<'PY'
import json
from pathlib import Path
import jsonschema
pairs = [
    ('schemas/skap-intr-review-candidate.schema.json', 'specs/skap-intr-review-candidate.v1.json'),
    ('schemas/intr-packet-review-candidate.schema.json', 'specs/intr-packet-review-candidate.v1.json'),
]
for schema_path, value_path in pairs:
    schema=json.loads(Path(schema_path).read_text(encoding='utf-8'))
    value=json.loads(Path(value_path).read_text(encoding='utf-8'))
    jsonschema.Draft202012Validator(schema).validate(value)
    print('SCHEMA_PASS', value_path)
for schema_path in (
    'schemas/skap-sealed-object.schema.json',
    'schemas/skap-lifecycle-transition-receipt.schema.json',
    'schemas/intr-endpoint-session-proof.schema.json',
    'schemas/intr-hop-receipt.schema.json',
):
    schema=json.loads(Path(schema_path).read_text(encoding='utf-8'))
    jsonschema.Draft202012Validator.check_schema(schema)
    print('SCHEMA_DEFINITION_PASS', schema_path)
receipt_schema=json.loads(Path('schemas/intr-hop-receipt.schema.json').read_text(encoding='utf-8'))
validator=jsonschema.Draft202012Validator(receipt_schema)
for chain_path in (
    'examples/intr-hop-receipt-chain.example.json',
    'examples/intr-hop-return-receipt-chain.example.json',
):
    chain=json.loads(Path(chain_path).read_text(encoding='utf-8'))
    for receipt in chain:
        validator.validate(receipt)
    print('SCHEMA_PASS', chain_path)
PY
