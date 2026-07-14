# KnowledgeVault AI Ingestion — Phase 1 (Heuristic, Safe)

This drop-in tool generates **suggestion files** from your inbox without modifying any vault content.

## What it does
- Reads `00_Inbox/Quick_Notes.md`
- Splits entries by headings like: `## YYYY-MM-DD HH:MM`
- Extracts conservative signals (people-like names, place hints, media filenames)
- Writes proposals to `_AI/Suggestions/`
- Logs runs to `_AI/Logs/`
- Tracks processed entries in `_AI/ingest_state.json`

## What it NEVER does
- Edits or moves your notes
- Deletes anything
- Reads restricted areas (`03_Records/`, `Privacy Level: restricted`)

## Install (drop-in)
Copy `tools/ai_ingest.py` into your KnowledgeVault repo under `tools/`.

## Run
```bash
python3 tools/ai_ingest.py --vault /path/to/KnowledgeVault
```

Dry run:
```bash
python3 tools/ai_ingest.py --vault /path/to/KnowledgeVault --dry-run
```

Limit suggestions:
```bash
python3 tools/ai_ingest.py --vault /path/to/KnowledgeVault --max 10
```

## iPhone-only note
You can run this later via:
- a computer
- a server
- GitHub Actions (next step)

Output is plain Markdown — portable and safe.

---

🔒 Layer: Framework | KV
