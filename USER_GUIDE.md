# KnowledgeVault User Guide

KnowledgeVault is the StegVerse continuity and knowledge layer: a portable, inspectable structure for preserving notes, records, research, projects, media references, indexes, policies, and enough context to reconstruct ongoing work across devices and sessions.

Baseline KnowledgeVault use is file-based and does not require an account, hosted service, SDK, or AI provider. StegVerse runtime integrations add governed transport, receipt, reconstruction, and secret-custody boundaries as those capabilities are activated.

## 1. Install a KnowledgeVault

### Desktop: verified initializer

From a checked-out copy of this repository:

```bash
python3 tools/init_vault.py /path/to/parent-folder
```

The initializer refuses to overwrite an existing `KnowledgeVault`, copies the complete template, verifies the installed file set and immutable hashes, updates the creation timestamp, and writes `_System/installation.receipt.json`.

Preview without writing:

```bash
python3 tools/init_vault.py /path/to/parent-folder --dry-run
```

### Any device: file-only setup

1. Download a release ZIP or copy `vault_template/KnowledgeVault/`.
2. Place the `KnowledgeVault` folder somewhere you control.
3. Keep the supplied structure intact unless you intentionally migrate it.
4. Open Markdown and text files with any editor or file manager you prefer.

On iPhone or iPad, the Files app is sufficient for file-only use. On Android, use the system file manager or another file manager. On Windows, macOS, or Linux, either use the initializer or copy the template directly.

## 2. Start using it

You do not need to organize everything before beginning.

Start with one note in `00_Inbox/` or `01_Notes/` containing:

- the date;
- what happened or what you are working on;
- why it matters;
- what should be remembered next.

For long-running AI or project work, preserve the current objective, constraints, completed work, unresolved questions, and next tasks. See [`docs/CONVERSATION_CONTINUITY.md`](./docs/CONVERSATION_CONTINUITY.md) for the full reconstruction pattern.

A simple operating loop is:

**Capture → organize lightly → index what matters → preserve enough context to reconstruct later.**

## 3. What the main folders mean

```text
KnowledgeVault/
├── 00_Inbox/      quick capture and unprocessed material
├── 01_Notes/      notes, events, memories, observations
├── 02_Research/   reading, investigations, evidence, learning
├── 03_Records/    durable personal or administrative records
├── 04_Media/      media and media references
├── 05_Projects/   active work and project state
├── 06_Archive/    completed or dormant material
├── _AI/           AI suggestions, queues, logs, and review state
├── _Entities/     people, places, organizations, projects, self
├── _Index/        master indexes and cross-references
├── _LightMode/    minimal views and reduced working surfaces
├── _Meta/         manifest, format, places, integrity metadata
├── _Policy/       user and system policy for this vault
├── _System/       receipts, execution state, guides, migration state
├── _Templates/    reusable templates
├── _migration/    version and migration helpers
└── docs/          vault-local documentation
```

Use the numbered folders for ordinary human content. Use `_Index/` to make important material discoverable. Treat `_System/`, `_Policy/`, `_Meta/`, and other underscore-prefixed areas as structured system surfaces rather than casual storage locations.

## 4. KnowledgeVault and StegVerse

KnowledgeVault is the continuity and knowledge state layer. It is not the same thing as secret custody, device execution, or network transport.

The intended StegVerse boundary model is:

```text
SKAP Vault ←InTr→ KnowledgeVault ←InTr→ Device/StegOS Node ←InTr→ External Network ←InTr→ Endpoint
```

Each independently governed ingress boundary is expected to evaluate its own HANDOFF and produce its own HANDOFF_RECEIPT when a transition is admitted. A successful transition at one boundary does not automatically authorize the next boundary.

In practical terms:

- **KnowledgeVault** preserves durable knowledge and continuity state.
- **SKAP Vault** is the secret-custody boundary for credentials, keys, recovery material, and other secret values.
- **Device / StegOS Node** is an execution and interaction boundary.
- **External Network** is a separately governed transport boundary.
- **Endpoint** independently decides whether to admit the requested operation.
- **Interlock/InTr** is the governed transition path as those runtime lanes are activated.
- **HANDOFF_RECEIPTs** are durable evidence of admitted transitions; runtime success alone does not create canonical standing.

Do not bypass those boundaries merely because direct file or network access is technically possible.

## 5. Sensitive information and secrets

KnowledgeVault may contain sensitive records, but the baseline file structure is not itself encryption.

Do not place passwords, private keys, seed phrases, authentication recovery codes, or equivalent secret material into ordinary plaintext KV files. In the StegVerse architecture, that material belongs behind the SKAP Vault secret-custody boundary and should be referenced from KV only through governed bindings or receipts.

Until a SKAP-backed runtime is active for a given deployment, protect sensitive KV content using the security controls of the device or storage provider you actually use, and avoid storing secret material in plaintext.

For repository and deployment security requirements, see [`SECURITY.md`](./SECURITY.md).

## 6. AI and conversation continuity

AI is optional. KnowledgeVault is designed so AI tools can work with predictable structure without becoming canonical authority over the vault.

Useful patterns include:

- saving a reload packet for a long-running conversation;
- preserving project state before changing sessions or devices;
- recording AI suggestions separately from approved human-authored state;
- retaining source links and evidence alongside conclusions;
- keeping policy in `_Policy/` rather than encoding it only in prompts.

AI-generated suggestions should remain inspectable and should not silently overwrite owner-authored state.

See:

- [`docs/CONVERSATION_CONTINUITY.md`](./docs/CONVERSATION_CONTINUITY.md)
- [`docs/EXAMPLES.md`](./docs/EXAMPLES.md)
- [`docs/AI_COMPATIBLE.md`](./docs/AI_COMPATIBLE.md)

## 7. Indexing and retrieval

Indexes are what make a growing vault reconstructable.

Use `_Index/Master_Index.md` as the broad map and add topic, timeline, relationship, or project indexes when they reduce retrieval friction. You do not need to index every file immediately. Index the material you expect to need again or whose relationship to other material matters.

Prefer durable references, clear filenames, dates where useful, and open formats such as Markdown, text, PDF, PNG, and JPEG.

## 8. Backup, migration, and replacement

KnowledgeVault is designed to be replaceable and portable.

Good practice:

- keep more than one copy of important content;
- do not silently overwrite an existing vault during repair or migration;
- preserve the old vault as evidence until the replacement is accepted;
- use installation or migration receipts where provided;
- verify release manifests and checksums when integrity assurance matters.

Release verification is optional for ordinary use but available with:

```bash
python3 tools/verify_release.py dist/ContinuityVault_vX.Y.Z.zip
```

Migration helpers live under `_migration/` and repository tooling under `tools/`.

## 9. Optional sharing and modules

KnowledgeVault may participate in broader StegVerse modules and sharing flows, but sharing must remain explicit and policy-bounded. The existence of data in KV does not imply permission to disclose it.

When module or sharing integrations are active, the user should be able to determine:

- what category of information is being requested;
- who or what is requesting it;
- the allowed scope and duration;
- whether content, metadata, or both are included;
- what receipt records the decision;
- how the permission can be withdrawn or superseded.

See [`docs/DATA_SHARING.md`](./docs/DATA_SHARING.md) for the current documented sharing model.

## 10. Troubleshooting

If setup fails, first determine which stage failed: download, unzip/copy, initialization, verification, permissions, or first use.

For repository-supported onboarding problems, use the structured onboarding-friction issue form. Do not attach private vault content, credentials, recovery material, medical records, financial records, or other sensitive personal data to a public issue.

If the vault already exists, do not run a repair process that silently overwrites owner-authored files. Preserve the existing vault and use a new destination or an explicit migration path.

## 11. Deeper technical review

Most users should not need the internal architecture documents.

For technical review, start with:

- [`docs/TECHNICAL_REVIEW_PATH.md`](./docs/TECHNICAL_REVIEW_PATH.md)
- [`SECURITY.md`](./SECURITY.md)
- [`stegverse.architecture.json`](./stegverse.architecture.json)

Repository development state, release evidence, implementation handoffs, schemas, fixtures, and tests remain separate from this user guide so that ordinary KV operation stays understandable.
