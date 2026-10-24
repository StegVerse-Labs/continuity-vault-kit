set -o pipefail
if [ "$RUN" = false ] && python3 .stegverse/finish_point_verdict.py not-selected "$RUNNER_TEMP/finish-point-verdict.json" | tee -a "$GITHUB_STEP_SUMMARY"; then
  echo "FINISH_POINT_SET NOT_SELECTED: the sealed verdict above shows no path of this change is in the set's closure; the step passes on it"
  exit 0
fi
python -m unittest -v tests.test_kv_skap_vault_finish_point 2>&1 | tee /tmp/finish.txt
! grep -Eq "skipped=[0-9]+|\.\.\. skipped" /tmp/finish.txt
