# KV Layer Boundary Rules (kv.layer.v1)

This repo enforces a **hard boundary** between:

- **FRAMEWORK** (public kit docs + tooling)
- **RUNTIME_TEMPLATE** (seed files that will exist inside a user's personal KnowledgeVault)

## ✅ Goal

Make it *obvious* what belongs where, and make CI fail fast if something drifts.

---

## 🧭 Layers

### FRAMEWORK
**Where:** root docs + `docs/**` + `tools/**` + `.github/**`

**Meaning:** public starter kit only — **no personal data**.

### RUNTIME_TEMPLATE
**Where:** `vault_template/KnowledgeVault/**`

**Meaning:** safe placeholder seed files users copy into their private vault.

---

## 🔒 Hard-fail markers

If any of these appear in any Markdown file, CI fails:

- `Privacy Level: restricted`
- `BEGIN:VCARD`
- `SSN`
- `Social Security`
- `Driver's License`
- `Passport`

Tune in `.stegdb/kv-layer.v1.json`.

---

## 🏷️ Footer labeling

Markdown docs in either layer get a standard footer at the bottom.

Example:

```md

---

🔒 Layer: Framework | KV
