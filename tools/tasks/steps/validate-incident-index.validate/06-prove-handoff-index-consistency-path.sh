python3 tools/incident_reconcile.py tests/fixtures/actionable_handoff_state.synthetic.json tests/fixtures/actionable_incidents.synthetic.jsonl > /tmp/reconcile.json
python3 - <<'PY'
import json
data = json.load(open('/tmp/reconcile.json', encoding='utf-8'))
assert data['states'] == ['CLEAR']
assert data['source_records_opened'] == 0
assert data['reconcile_path'] == 'HANDOFF_STATE->INCIDENT_INDEX->CONSISTENCY_CHECK'
print('PASS handoff/index reconciliation: CLEAR')
PY
