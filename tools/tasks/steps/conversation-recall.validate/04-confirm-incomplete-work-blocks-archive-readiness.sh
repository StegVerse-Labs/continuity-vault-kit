output=$(python continuity/recall.py fixtures/conversation-recall/example-vault/events.jsonl readiness --archive-readiness)
echo "$output"
echo "$output" | grep '"ready": false'
