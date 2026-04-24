# Safety Notes

KnowledgeVault is a **file and documentation template**.
It is not encryption.
It is not a security product.

If you store sensitive information, you are responsible for how it is protected.

---

## Minimum safety guidance

- Assume files stored in plain text can be read if someone gets access to your device or cloud storage.
- Use device passcodes and full-disk encryption where available.
- Use a secure backup strategy (at least 2 copies).

---

## What not to store in plain text

See:
- [`DO_NOT_STORE_HERE.md`](./DO_NOT_STORE_HERE.md)

If you must store sensitive items, consider:
- encrypted containers
- password managers
- separate secure vaults

---

## Threat model (simple)

Ask:
- Who do I want to keep this from?
- What happens if it leaks?
- Where is it stored (device, cloud, shared family drive)?

Then choose protections accordingly.

---

## Data sharing safety

If you later opt into the optional data-sharing ecosystem:

- **You choose what to share** — not all vault content, only categories you explicitly select
- **Metadata is separate from content** — you can share location or date patterns without sharing the actual note text
- **Aggregation protects privacy** — your individual data is combined with others' matching data before any commercial use
- **You can audit** — `_Policy/Data_Sharing_Policy.md` in your vault tracks what you have opted to share
- **Withdrawal is immediate** — opt-out stops future sharing; already-aggregated data may remain in datasets per the policy
- **No sensitive categories** — `03_Records/` (health, finance, legal) is excluded from sharing by default and cannot be overridden

Before opting in, read:
- [`docs/DATA_SHARING.md`](./docs/DATA_SHARING.md)
- [`vault_template/KnowledgeVault/_Policy/Data_Sharing_Policy.md`](./vault_template/KnowledgeVault/_Policy/Data_Sharing_Policy.md)

---

## StegVerse philosophy note

StegVerse favors **clarity and replaceability**.
Safety should be improved over time, without locking users into one vendor or one app.
