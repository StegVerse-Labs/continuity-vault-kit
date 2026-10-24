set -o pipefail
python -m unittest -v tests.test_kv_skap_vault_e0_witnesses 2>&1 | tee /tmp/witness.txt
! grep -Eq "skipped=[0-9]+|\.\.\. skipped" /tmp/witness.txt
