set -o pipefail
python -m unittest -v tests.test_finish_point_verdict 2>&1 | tee /tmp/finish-point-verdict.log
if grep -Eq 'skipped|expected failure' /tmp/finish-point-verdict.log; then
  echo "::error::a finish-point verdict test was skipped; skips are never accepted"; exit 1
fi
