# What "AI-Compatible" Means

KnowledgeVault is designed so future AI tools can read, suggest, and organize — without overwriting your content.

This does not mean AI is required. The vault works with any text editor, file manager, or pen-and-paper system.

---

## The five principles

### 1. Predictable folder names

The numbered folders (`00_Inbox` through `06_Archive`) and underscore folders (`_AI`, `_Entities`, `_Index`, etc.) use consistent names across all vaults.

An AI or script can find `01_Notes/` without guessing whether you called it `Notes/`, `notes/`, or `MyNotes/`.

### 2. Indexes

`_Index/Master_Index.md` gives both humans and machines a map of the vault.

Future AI tools can use this to:
- Understand the vault's scope without scanning every file
- Suggest missing entries
- Verify structural integrity

### 3. Metadata-ready structure

- **Date-prefixed filenames** — `2026-04-24 — Event Name.md` is machine-sortable
- **Frontmatter** — optional YAML headers for structured data (not required)
- **Entity linking** — `[[Entity Name]]` syntax creates machine-readable relationships

### 4. Separation of concerns

| Folder | Purpose | Who writes here |
|--------|---------|-----------------|
| `00-06/` (numbered) | Human notes and content | You |
| `_AI/` | AI-generated suggestions | AI (proposals only) |
| `_Policy/` | Your rules and choices | You |
| `_System/` | Integrity checks, logs | Tools (with your permission) |
| `_Meta/` | Vault metadata, manifest | You + tools |

AI never writes into your numbered folders without explicit approval.

### 5. Future machine-readable manifests

`_Meta/vault.manifest.json` describes the vault structure for external tools.

This is optional and evolving. The vault works without it.

---

## What AI can do today

If you copy `tools/AI_Ingestion.py` into your vault:

- It reads `00_Inbox/Quick_Notes.md`
- Extracts signals (names, places, events)
- Writes **suggestions** to `_AI/Suggestions/`
- You review and manually apply what you want

It never edits, moves, or deletes your notes.

---

## What AI cannot do

- Read `Privacy Level: restricted` files
- Access `03_Records/` (health, finance, legal)
- Modify `_Policy/` files
- Write into numbered folders without your explicit action

---

## For developers

If you are building a tool that reads KnowledgeVault:

1. Respect `_Policy/AI_Access_Policy.md`
2. Honor `Privacy Level:` markers
3. Write suggestions to `_AI/`, never to numbered folders
4. Use `_Meta/vault.manifest.json` for structure discovery
5. Log all access in `_AI/Logs/` (if applicable)

See `docs/AI_Ingestion.md` for the reference implementation.
