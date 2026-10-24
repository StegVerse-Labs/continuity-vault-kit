set -o pipefail
python -m unittest -v tests.test_kv_skap_vault_finish_point 2>&1 | tee /tmp/finish.txt
! grep -Eq "skipped=[0-9]+|\.\.\. skipped" /tmp/finish.txt
