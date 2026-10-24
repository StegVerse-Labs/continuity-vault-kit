rm -rf dist
python3 tools/test_release_tools.py
python3 tools/test_init_vault.py
python3 tools/test_automation_contracts.py
python3 -m unittest tests.test_hosted_release_authority_retirement -v
rm -rf dist
python3 tools/build_release.py
python3 tools/verify_release.py "dist/ContinuityVault_v${{ steps.version.outputs.value }}.zip"
