python3 - <<'PY'
from pathlib import Path
text=Path('.github/workflows/validation-dispatcher.yml').read_text(encoding='utf-8')
assert 'contents: read' in text
for marker in ('contents:' + ' write', 'git' + ' push', 'secrets' + '.'):
    assert marker not in text, marker
print('AUTOMATED_KV_UPGRADE_HOSTED_VALIDATION_NON_AUTHORIZING_PASS')
PY
