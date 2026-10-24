python3 - <<'PY'
from pathlib import Path
text=Path('.github/workflows/validation-dispatcher.yml').read_text(encoding='utf-8')
forbidden = ['contents:' + ' write', 'git' + ' push', 'secrets' + '.']
assert 'contents: read' in text
for marker in forbidden:
    assert marker not in text, marker
print('KV_INTR_HOSTED_VALIDATION_NON_AUTHORIZING_PASS')
PY
