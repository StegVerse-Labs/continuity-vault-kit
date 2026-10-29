set -euo pipefail
python -m pip install --disable-pip-version-check pytest
python -m pytest -q -rs tests/test_kv_crossing_records.py \
  tests/test_kv_receipt_ledgers_no_431_and_crossing_wording.py | tee /tmp/pytest.txt
! grep -Eq "[0-9]+ skipped" /tmp/pytest.txt
