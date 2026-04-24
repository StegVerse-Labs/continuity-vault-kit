# KnowledgeVault Kit (continuity-vault-kit)

KnowledgeVault is a **device-agnostic personal vault**: a folder structure + guidance you can copy onto any device to preserve notes, documents, and context over time.

This is not a productivity system.
It is an attempt to formalize personal cognitive continuity in a replaceable, versioned, AI-compatible structure.

No accounts. No services. No lock-in.

## Start here

➡️ **Read:** [`WELCOME.md`](./WELCOME.md)

That file contains a 30-second start path for **iOS, Android, Windows, macOS, and Linux**.

## What this is

- A portable vault template you can copy anywhere
- A way to preserve context, intent, and memory across devices and time
- A starting point designed to be forked, adapted, or replaced
- **AI-compatible by design** — predictable structure for future tooling (see [`docs/AI_COMPATIBLE.md`](./docs/AI_COMPATIBLE.md))
- **Optional data-sharing ecosystem** — if you later choose to share anonymized data, you may participate in revenue generated from its use (see [`docs/DATA_SHARING.md`](./docs/DATA_SHARING.md))

## What this is not

- Not a product
- Not a platform
- Not surveillance
- Not identity verification
- Not permanent authority
- Not a financial scheme — any revenue participation is strictly opt-in and secondary to the vault's core purpose

## What's in this repo

### The vault template

```
vault_template/KnowledgeVault/
├── 00_Inbox/          → Quick captures, drafts, unprocessed notes
├── 01_Notes/          → Daily notes, events, memories
├── 02_Research/       → Reading, learning, investigations
├── 03_Records/        → Health, finance, legal (sensitive — see SAFETY.md)
├── 04_Media/          → Photos, videos, audio
├── 05_Projects/       → Active work, creative output
├── 06_Archive/        → Completed or dormant material
├── _AI/               → AI-generated suggestions (never auto-applied)
├── _Entities/         → People, places, organizations you reference
│   ├── People/
│   ├── Places/
│   ├── Projects/
│   ├── Organizations/
│   └── Self/
├── _Index/            → Master indexes and cross-references
├── _LightMode/        → Minimal, distraction-free view files
├── _Meta/             → Vault metadata, places list, manifest
├── _Policy/           → Your own rules for this vault
├── _System/           → Integrity checks, migration logs, guides
├── _Templates/        → Reusable note templates
├── _migration/        → Version-to-version migration helpers
└── docs/              → Your own documentation about this vault
```

### Framework files

- `WELCOME.md` — first-contact onboarding (start here)
- `GETTING_STARTED.md` — deeper walkthrough and recommended structure
- `SAFETY.md` — safety notes and threat-model guidance
- `DO_NOT_STORE_HERE.md` — what not to keep in plain text
- `STATUS.md` — current state + next steps
- `CHANGELOG.md` + `VERSION` — change tracking
- `tools/` — optional scripts for release building, AI ingestion, and verification
- `docs/` — detailed guides (iOS setup, multi-device usage, backup, AI compatibility, data sharing)

## Verifying your download (optional)

Each release includes a `.sha256` checksum file and a `.manifest.json`. To verify a release bundle:

```bash
python3 tools/verify_release.py dist/ContinuityVault_vX.Y.Z.zip
```

This is optional. The vault works the same whether you verify or not.

## Relationship to StegVerse

This kit is part of **StegVerse**: an open framework for expectations, identity, boundaries, continuity, and replaceability — not control or permanence.

- `canon/` inside the vault template is synced from StegDB (authoritative doctrine + contract templates)
- All other vault content is user-facing and evolves for usability
- StegVerse SDK, StegDB, and TVC can validate or index this vault later — but baseline use requires none of them

## License

See [`LICENSE`](./LICENSE).
