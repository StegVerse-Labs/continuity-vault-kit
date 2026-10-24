set -euo pipefail
test -n "$(ls -1 dist/*.zip 2>/dev/null | head -n 1)"
test -n "$(ls -1 dist/*.sha256 2>/dev/null | head -n 1)"
