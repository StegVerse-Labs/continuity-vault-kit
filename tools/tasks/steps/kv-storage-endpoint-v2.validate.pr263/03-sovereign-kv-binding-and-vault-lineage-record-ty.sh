python -m pip install --disable-pip-version-check pytest
set -o pipefail
python -m pytest -q -rs tests/test_task_registry_event_sovereign_kv_binding.py \
  tests/test_sovereign_kv_vault_lineage_record.py \
  tests/test_kv_storage_provider_adapter.py \
  tests/test_cloud_peer_adoption_provider_binding.py tests/test_kv_provider_operation_store.py \
  tests/test_kv_my_kv_projection.py | tee /tmp/pytest.txt
! grep -Eq "[0-9]+ skipped" /tmp/pytest.txt
