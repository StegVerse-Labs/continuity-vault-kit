# KV Layer Boundary Rules (kv.layer.v1)

This repository enforces a clear boundary between:

- **FRAMEWORK** — public kit documentation, tooling, workflows, and repository metadata.
- **RUNTIME_TEMPLATE** — placeholder files copied into a user's private KnowledgeVault.

## Goal

Make intended placement obvious and detect drift without inspecting or mutating user-authored personal vault content.

---

## Layers

### FRAMEWORK

**Where:** root documentation plus `docs/**`, `tools/**`, `.github/**`, and `.stegdb/**`.

**Meaning:** public starter-kit material only. Do not place user-authored personal data here.

### RUNTIME_TEMPLATE

**Where:** `vault_template/KnowledgeVault/**`.

**Meaning:** safe placeholder and policy seed files that users may copy into a private vault.

---

## Forbidden footer claims

The checker rejects exact Markdown footer lines that incorrectly claim a public repository file is part of a personal vault, including:

- `🔒 Layer: Personal Vault | KV`
- `🔒 Layer: Personal | KV`

Ordinary safety documentation may discuss personal vaults, passports, identifiers, restricted records, or other sensitive topics. Those prose references are not treated as evidence that personal data is present.

Configuration lives in `.stegdb/kv-layer.v1.json`.

---

## Footer labeling

Canonical Markdown footers are:

```md
---

🔒 Layer: Framework | KV
```

and:

```md
---

🔒 Layer: Vault Template | KV
```

The dedicated `format/**` workflow may add or normalize these footers. It does not move or delete files.

To apply the same operation in a local checkout:

```bash
python3 tools/kv_layer_check.py --mode auto-label
python3 tools/kv_layer_check.py --mode validate
```

Footer examples inside prose or fenced code must remain untouched. Only a recognized trailing footer block may be replaced.

---

🔒 Layer: Framework | KV
