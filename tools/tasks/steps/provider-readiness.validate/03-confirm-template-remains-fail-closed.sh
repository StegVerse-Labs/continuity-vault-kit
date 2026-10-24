set +e
python3 tools/check_provider_readiness.py config/production-provider-profile.template.json
code=$?
test "$code" -eq 1
