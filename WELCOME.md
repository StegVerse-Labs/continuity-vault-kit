# Welcome to KnowledgeVault

KnowledgeVault is a **device-agnostic personal vault**: a simple folder structure + guidance you can use to store notes, documents, and context over time.

It is also designed for a specific long-running problem: preserving enough conversation state that your future self and future AI sessions can continue without starting over.

You control the files.
Nothing here phones home.
You are not enrolling into anything.

---

## Start in 30 seconds

### Automated setup on Windows, macOS, or Linux

From a checked-out copy of this repository, run:

```bash
python3 tools/init_vault.py /path/to/parent-folder
```

The initializer:

- refuses to overwrite an existing `KnowledgeVault`;
- copies the complete template;
- verifies the destination file set and immutable file hashes;
- updates the new vault's creation timestamp;
- writes `_System/installation.receipt.json` with the verification result;
- removes a partial destination if initialization fails.

Preview the action without writing files:

```bash
python3 tools/init_vault.py /path/to/parent-folder --dry-run
```

### File-only setup on any device

1. Download this repository as a ZIP or copy `vault_template/KnowledgeVault/`.
2. Place the vault somewhere you control.
3. Rename it only when your file manager or note application requires a different outer folder name.

The automated initializer is optional. The vault remains usable without Python, an account, a service, or StegVerse tooling.

### Add one continuity note

Inside your vault, add one short note that explains what you want your future self or future AI session to remember.

Example:

```text
2026-06-18 — First Continuity Note.md
```

If you can open a text or Markdown file, you can use KnowledgeVault.

---

## If you are here for AI conversation continuity

Read:

➡️ [`docs/CONVERSATION_CONTINUITY.md`](./docs/CONVERSATION_CONTINUITY.md)

That guide explains how to create reload packets for long-running AI chats so new sessions can continue from a preserved working state.

---

## Device notes

### iPhone / iPad (iOS)

- Use the **Files** app to unzip or copy folders.
- Open `.md` files directly in Files, or with any notes or Markdown app you prefer.
- See [`docs/IOS_SETUP.md`](./docs/IOS_SETUP.md) for detailed setup notes.

### Android

- Use the Files app or a file manager to unzip or copy folders.
- Open `.md` files with a notes or Markdown app.

### Windows / macOS / Linux

- Use the verified initializer above, or unzip and copy the template manually.
- Open `.md` files in any editor.

---

## What this is

- A portable structure for preserving context and intent
- A template you can fork, edit, and carry across devices
- A starting point that does not assume any specific app or platform
- Designed so future AI tools can read and suggest — but never overwrite — your content
- A way to create reloadable continuity for long-running conversations and projects

## What this is not

- Not a product
- Not an account system
- Not identity verification
- Not surveillance
- Not permanent authority
- Not a way to make money — any future data-sharing revenue is strictly opt-in and secondary

---

## Safety

Before storing sensitive information, read:

- [`SAFETY.md`](./SAFETY.md)
- [`DO_NOT_STORE_HERE.md`](./DO_NOT_STORE_HERE.md)

KnowledgeVault is **a structure**, not encryption.

---

## Optional data sharing and revenue

Later, if you choose, you may opt into sharing anonymized data from your vault. If that data generates revenue, you may receive compensation. This is:

- **Entirely optional** — default is off
- **Transparent** — you choose what categories and metadata to share
- **Reversible** — you can withdraw
- **Secondary** — the vault exists for you first

See [`docs/DATA_SHARING.md`](./docs/DATA_SHARING.md) for full details.

---

## Next

For more structure and examples, read:

➡️ [`GETTING_STARTED.md`](./GETTING_STARTED.md)
