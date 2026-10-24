rm -rf dist
python3 tools/build_release.py
python3 tools/verify_release.py "dist/ContinuityVault_v$(cat VERSION).zip"
