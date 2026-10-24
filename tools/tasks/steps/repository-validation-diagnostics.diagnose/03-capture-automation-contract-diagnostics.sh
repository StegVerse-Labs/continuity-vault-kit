set +e
python3 tools/test_automation_contracts.py > automation-contract-diagnostics.txt 2>&1
echo "exit_code=$?" >> automation-contract-diagnostics.txt
exit 0
