set +e
python3 tools/emoji_lint.py --strict > emoji-diagnostics.txt 2>&1
echo "exit_code=$?" >> emoji-diagnostics.txt
exit 0
