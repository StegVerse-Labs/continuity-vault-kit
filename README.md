# KnowledgeVault Kit

KnowledgeVault is the StegVerse continuity and knowledge layer: a portable, inspectable vault for preserving notes, records, research, projects, media references, policy, and enough context to reconstruct ongoing work across devices and sessions.

Baseline use is file-based. No account, hosted service, SDK, or AI provider is required.

## Start here

### Install

**Desktop, verified initializer:**

```bash
python3 tools/init_vault.py /path/to/parent-folder
```

**Any device:** copy or unzip `vault_template/KnowledgeVault/` somewhere you control.

The initializer refuses to overwrite an existing vault, verifies the installed file set and immutable hashes, and writes `_System/installation.receipt.json`.

### Use

1. Capture something in `00_Inbox/` or `01_Notes/`.
2. Add the date, why it matters, and what should be remembered next.
3. Organize only when useful.
4. Index important material in `_Index/` so it can be found and reconstructed later.

For the complete operating guide, including iPhone/iPad, Android, desktop, AI continuity, backup, SKAP Vault, HANDOFF/receipt boundaries, sharing, and troubleshooting, read **[`USER_GUIDE.md`](./USER_GUIDE.md)**.

## Core vault structure

```text
KnowledgeVault/
├── 00_Inbox/      quick capture
├── 01_Notes/      notes and observations
├── 02_Research/   research and evidence
├── 03_Records/    durable records
├── 04_Media/      media and references
├── 05_Projects/   active work
├── 06_Archive/    completed/dormant material
├── _AI/           AI suggestions and review state
├── _Entities/     people, places, organizations, projects, self
├── _Index/        indexes and cross-references
├── _Meta/         manifest and integrity metadata
├── _Policy/       vault policy
├── _System/       receipts, execution state, guides, migrations
├── _Templates/    reusable templates
└── docs/          vault-local documentation
```

## StegVerse boundary model

KnowledgeVault is not the secret store, device runtime, or network itself. The intended governed topology is:

```text
SKAP Vault ←InTr→ KnowledgeVault ←InTr→ Device/StegOS Node ←InTr→ External Network ←InTr→ Endpoint
```

Each independently governed ingress boundary evaluates its own HANDOFF and, when admitted, produces its own HANDOFF_RECEIPT. Success at one boundary does not automatically authorize the next.

- **KnowledgeVault** preserves continuity and knowledge state.
- **SKAP Vault** is the secret-custody boundary for credentials, keys, recovery material, and equivalent secrets.
- **Device / StegOS Node** is an execution and interaction boundary.
- **External Network** is a separately governed transport boundary.
- **Endpoint** independently admits or rejects the requested operation.

The full runtime Interlock/InTr integration is an activation lane separate from baseline file-only KnowledgeVault use.

## Safety

KnowledgeVault's baseline file structure is not itself encryption. Do not place passwords, private keys, seed phrases, authentication recovery codes, or equivalent secrets into ordinary plaintext KV files. In the StegVerse architecture, those belong behind the SKAP Vault boundary.

For repository and deployment security posture, see [`SECURITY.md`](./SECURITY.md).

## AI continuity

KnowledgeVault can preserve reloadable conversation and project state without making an AI system canonical authority over the vault.

See:

- [`docs/CONVERSATION_CONTINUITY.md`](./docs/CONVERSATION_CONTINUITY.md)
- [`docs/EXAMPLES.md`](./docs/EXAMPLES.md)
- [`docs/AI_COMPATIBLE.md`](./docs/AI_COMPATIBLE.md)

## Historical provenance across storage providers

KnowledgeVault can represent historical evidence that remains in more than one owner-controlled storage provider. A legacy artifact may remain in iCloud, Google Drive, local storage, or another admitted source while KV records its exact-byte identity, source/provider provenance, chronology, and explicit copy/mirror/derived relationships.

The governing distinction is:

```text
storage location != authority
copy != original
historical evidence != current doctrine
import receipt != truth certification
```

A historical record must keep the exact source artifact separate from later copies, normalized projections, interpretations, derived claims, and present-day canonical StegVerse doctrine. Provider credentials remain behind SKAP, and source implementation does not itself authorize provider access, migration, publication, governance, or execution.

See [`KV_HISTORICAL_PROVENANCE_MIRROR_HANDOFF.md`](./KV_HISTORICAL_PROVENANCE_MIRROR_HANDOFF.md) for the bounded source contract.

## Owner-authorized historical imports and custody

A historical artifact may enter the governed KV import path only when the runtime has an explicit owner-authorization evidence reference, exact bytes matching the historical artifact record, an admitted InTr receipt, and a persistence receipt. The resulting historical import receipt proves that those evidence references and exact-byte identity were bound together; it does **not** certify the historical artifact as true, current doctrine, publishable, or authoritative.

A KV historical import may also produce a **Master Records custody-request candidate**. That candidate is only a request from the source repository. It must state that destination custody has not yet been accepted, destination acknowledgement has not been minted, and independent destination validation has not yet completed. Only the Master Records destination may independently validate and create its own custody acknowledgement.

Site/MyKV may receive a bounded status projection containing artifact and receipt identifiers, import state, lineage/contradiction state, and custody-request state. The status projection does not contain historical source bytes or private content and grants no publication authority.

```text
owner authorization != reusable credential
import receipt != truth certification
custody request != destination custody acceptance
bounded status != private historical content
```

See [`KV_HISTORICAL_CORPUS_IMPORT_MIRROR_HANDOFF.md`](./KV_HISTORICAL_CORPUS_IMPORT_MIRROR_HANDOFF.md) for the source and activation boundaries.

## Technical review

Developers and reviewers should start with [`docs/TECHNICAL_REVIEW_PATH.md`](./docs/TECHNICAL_REVIEW_PATH.md), [`SECURITY.md`](./SECURITY.md), and [`stegverse.architecture.json`](./stegverse.architecture.json).

Release history and integrity remain in [`CHANGELOG.md`](./CHANGELOG.md), `VERSION`, and release evidence under `docs/`.

## License

See [`LICENSE`](./LICENSE).
