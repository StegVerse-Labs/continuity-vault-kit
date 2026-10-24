set -o pipefail
python3 -m unittest tests.test_skap_loader_js -v 2>&1 | tee loader-set.log
if grep -Eq "skipped=|\.\.\. skipped" loader-set.log; then
  echo "FAIL_CLOSED SELECTED_TESTS_ZERO_SKIPPED: the loader set reported a skip" >&2
  exit 1
fi
