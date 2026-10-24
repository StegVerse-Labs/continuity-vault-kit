python -m unittest -v tests.test_ranged_sha256_measurement 2>&1 | tee unittest.log
test "${PIPESTATUS[0]}" -eq 0
if grep -qiE "skipped|expected failure" unittest.log; then echo "SKIPPED_TESTS_PRESENT"; exit 1; fi
grep -E "^Ran [0-9]+ tests" unittest.log
