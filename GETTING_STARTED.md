# Getting Started (Deeper Guide)

This guide expands on `WELCOME.md` and suggests a simple way to use KnowledgeVault over time.

Start here first:
- [`WELCOME.md`](./WELCOME.md)

---

## The baseline workflow

### 1) Capture
Add short notes fast. Don't optimize.

### 2) Organize lightly
Use folders only when you feel friction.

### 3) Index for retrieval
Indexes make the vault survivable. Create links.

### 4) Preserve context
When adding a note, include:
- date
- why it matters
- what you believed at the time (intent)

---

## What "AI-compatible" means

KnowledgeVault is designed so future AI tools can understand your vault without guessing:

- **Predictable folder names** — `01_Notes/`, `02_Research/`, etc. are standard across all vaults
- **Indexes** — `_Index/Master_Index.md` gives both humans and machines a map
- **Metadata-ready** — date-prefixed filenames, structured frontmatter where used
- **Separation of concerns** — human notes in numbered folders; AI suggestions in `_AI/`; policy in `_Policy/`
- **Future manifests** — `_Meta/vault.manifest.json` describes the vault structure for external tools (optional)

This does not mean AI is required. The vault works perfectly with pen and paper equivalents.

See [`docs/AI_COMPATIBLE.md`](./docs/AI_COMPATIBLE.md) for the full specification.

---

## Suggested vault structure (example)

Your vault can be as simple as:

- `INDEX.md`
- `entries/`
- `media/`
- `docs/`

If your template already contains a structure, keep it. The goal is consistency, not perfection.

---

## What to write first

Add:
- a "First Note" entry
- a "Why this vault exists" entry
- a "Rules I want my future self to remember" entry

See [`docs/Your First 5 KnowledgeVault Notes.md`](./docs/Your%20First%205%20KnowledgeVault%20Notes.md) for guided first entries.

---

## Portability rules (future-proofing)

- prefer open formats (`.md`, `.txt`, `.pdf`, `.png`, `.jpg`)
- avoid app-locked formats as the only copy
- keep filenames simple
- keep an index at the top of the vault

---

## If you want to fork the system

That's expected. Forking is a feature.

You can:
- change folder names
- add templates
- remove what you don't need

The vault should serve you — not the other way around.

---

## Optional: Connecting to broader systems

Your vault is standalone by default. If you later choose, you can:

- **Share data for revenue** — see [`docs/DATA_SHARING.md`](./docs/DATA_SHARING.md)
- **Connect to StegVerse tools** — see [`docs/STEGVERSE_BRIDGE.md`](./docs/STEGVERSE_BRIDGE.md)
- **Enable AI ingestion** — copy `tools/AI_Ingestion.py` into your vault's `tools/` folder

None of these are required. They exist for users who want them.
