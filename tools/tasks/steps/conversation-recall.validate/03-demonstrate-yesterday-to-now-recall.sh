python continuity/recall.py fixtures/conversation-recall/example-vault/events.jsonl \
  "What changed between yesterday and now about ingestion storage?" \
  --since 2026-07-16T00:00:00Z \
  --until 2026-07-17T23:59:59Z \
  --index-out /tmp/conversation-index.json
