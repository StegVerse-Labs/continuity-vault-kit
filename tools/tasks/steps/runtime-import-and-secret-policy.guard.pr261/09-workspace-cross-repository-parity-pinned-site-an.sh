set -o pipefail
if [ "$RUN" = false ] && python3 .stegverse/finish_point_verdict.py not-selected "$RUNNER_TEMP/workspace-parity-verdict.json" --spec .stegverse/test-set-spec.json --set-key workspace_parity_sets | tee -a "$GITHUB_STEP_SUMMARY"; then
  echo "WORKSPACE_PARITY_SET NOT_SELECTED: the sealed verdict above shows no path of this change is in either set's closure; the step passes on it"
  exit 0
fi
python3 .stegverse/cross_repo_inputs.py materialize .stegverse/workspace-parity-pin.json --root .
parity=$(python3 .stegverse/cross_repo_inputs.py tests .stegverse/workspace-parity-pin.json)
n=$(printf '%s\n' "$parity" | grep -c .)
python -m pytest -v -rs $parity 2>&1 | tee /tmp/parity.txt
if grep -Eq "[0-9]+ skipped|SKIPPED" /tmp/parity.txt; then
  echo "::error::a cross-repository parity test was skipped; skips are never accepted"; exit 1
fi
grep -Eq "= $n passed in " /tmp/parity.txt
