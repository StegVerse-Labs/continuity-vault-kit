python3 - <<'PY'
import os
forbidden = [
    'COINBASE_API_KEY','COINBASE_API_SECRET','COINBASE_API_PRIVATE_KEY',
    'SKAP_ROOT_KEY','SKAP_BROWSER_RECIPIENT_P256_PRIVATE','GITHUB_TOKEN','GH_TOKEN'
]
exposed=[name for name in forbidden if os.environ.get(name)]
if exposed:
    raise SystemExit('credential-bearing validation environment: ' + ','.join(exposed))
print('HOSTED_VALIDATION_CREDENTIAL_AUTHORITY=NONE')
PY
