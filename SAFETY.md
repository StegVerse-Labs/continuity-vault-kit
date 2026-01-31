# Safety & Privacy Boundary (Read Before Use)

This repository is a **public starter kit** for building a private KnowledgeVault.

It contains:
- folder structure
- templates
- policies
- tooling

It must **not** contain personal data.

---

## ✅ Allowed in this public repo

- Markdown templates
- Documentation
- Policies and schemas
- Tooling scripts
- Example placeholder files (non-sensitive)

---

## ❌ Not allowed in this public repo

Do not commit:
- medical records
- legal records
- financial documents
- IDs (driver’s license, SSN, passport, etc.)
- private photos or receipts
- exported emails containing personal info
- tokens, secrets, API keys
- private conversations that identify real people or contain sensitive details

---

## Recommended setup

### Option A (best): Private vault repo
1. Keep this repo public as the kit.
2. Create a separate **private** repo for your real vault.
3. Copy the `vault_template/KnowledgeVault/` contents into your private vault.

### Option B: Local-only vault folder
1. Download the release zip
2. Unzip into Files app
3. Use Obsidian to navigate locally

---

## iOS note about link behavior

Some iOS editors (notably Pretext) may not behave like “wiki navigation” apps.

If links don’t open reliably:
- use **Obsidian** or **GitHub web UI**
- treat Pretext as an editor

---

## If you accidentally committed sensitive data

1. Remove the files immediately
2. Rotate any exposed credentials
3. Rewrite history if necessary (GitHub docs: “Removing sensitive data from a repository”)
4. Consider making the repo private (but remember forks may exist)
