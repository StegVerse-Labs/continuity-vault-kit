python3 tools/incident_index.py query tests/fixtures/actionable_incidents.synthetic.jsonl --term communication --term failure > /tmp/query.json
python3 - <<'PY'
import json
data = json.load(open('/tmp/query.json', encoding='utf-8'))
assert data['matched'] == 1
assert data['source_records_opened'] == 0
assert data['query_path'] == 'HANDOFF->INCIDENT_INDEX->INCIDENT->EVIDENCE_REFS'
print('PASS bounded retrieval: source_records_opened=0')
PY
