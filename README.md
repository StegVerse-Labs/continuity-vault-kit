# KnowledgeVault Kit

KnowledgeVault is the StegVerse continuity and knowledge layer: a portable, inspectable vault for preserving notes, records, research, projects, media references, policy, and enough context to reconstruct ongoing work across devices and sessions.

Baseline use is file-based. No account, hosted service, SDK, or AI provider is required.

## Start here

### Install

**Desktop, verified initializer:**

```bash
python3 tools/init_vault.py /path/to/parent-folder
```

The default command creates **KV #1** at `KnowledgeVault/`.

A second isolated instance can be created beside it without overwriting KV #1:

```bash
python3 tools/init_vault.py /path/to/parent-folder --instance 2 --storage-medium icloud-drive
```

That creates **KV #2** at `KnowledgeVault-2/`. The same rule extends to any positive instance number: KV #n is created at `KnowledgeVault-n/` unless `--vault-name` supplies another isolated folder name.

`--storage-medium` is descriptive metadata and may identify any owner-controlled storage medium, such as `icloud-drive`, `google-drive`, `onedrive`, `dropbox`, `local-disk`, or `removable-encrypted-volume`. It does not activate a provider session or grant provider authority. `--storage-locator` may record a non-secret path/provider locator; credentials and tokens must never be supplied there.

**Any device:** copy or unzip `vault_template/KnowledgeVault/` somewhere you control.

The initializer refuses to overwrite an existing instance root, verifies the installed template file set and immutable hashes, writes `_System/installation.receipt.json`, and creates `_System/Instances/instance.json` with a unique instance ID, storage metadata, and an initial `NOT_CONNECTED` relationship state.

### KV #1 / KV #2 / KV #n relationship

KV numbering identifies **instances**, not authority.

```text
Owner continuity set
├── KV #1  -> storage medium A
├── KV #2  -> storage medium A or B
├── KV #3  -> storage medium C
└── KV #n  -> any admitted owner-controlled storage medium
```

Instances sharing a `kv_set_id` belong to the same owner continuity set but begin **NOT_CONNECTED**. Sharing a set ID or storage provider does not itself authorize inter-instance communication.

The relationship model has four cumulative capability tiers:

```text
NOT_CONNECTED
  no inter-comms; no data movement; no replication; no unified AI corpus

CONNECTED
  inter-comms aware; admitted data can move between separately rooted KVs

SYNCED
  CONNECTED capabilities plus admitted replication between participating KVs

AI_INTERACTION
  SYNCED capabilities plus all participating KV data considered one logical corpus
  for the authorized AI interaction
```

`AI_INTERACTION` does not physically merge the vaults, erase provenance, or make the AI canonical authority. Physical roots and source identity remain distinct even when retrieval/reasoning treats the admitted set as one logical corpus.

KV #2 does not inherit authority from KV #1, and a higher or lower instance number does not make one vault canonical, subordinate, primary, backup, or replica. Operational roles are a separate dimension from relationship tier and are established by policy/Interlock/InTr rather than by instance ordinal.

This separation allows same-provider multi-instance use immediately—for example KV #1 and KV #2 can both live in iCloud Drive—while provider-specific adapters and governed relationship transitions can be integrated later without changing the instance identity model.

Relationship state is durably represented inside each KV at `_System/Instances/Relationships/relationship-state.json`. Transition requests are stored separately under `_System/Instances/Relationships/Requests/`. Persisting a request never changes the current tier. A state transition can be materialized only from an already-admitted request carrying both Interlock and InTr receipt references; source code does not decide admission and does not claim runtime activation, provider authority, data movement, replication, or AI exposure by itself.

MyKV-facing source may consume a bounded multi-instance projection rather than private KV content. `runtime/kv_my_kv_projection.py` projects instance identity, storage metadata, current relationship tier, governance state, pending relationship request IDs, provider connection/verification state, and pending provider-operation request identifiers. It fixes `private_content_included=false`, `credential_material_included=false`, provider/relationship mutation authority to false, and `authority_effect=NONE_STATUS_ONLY`. Provider status projection explicitly omits SKAP credential references and Interlock/InTr receipt references. The projection supports rendering and governed request initiation; it does not itself connect/disconnect storage, change tiers, move data, replicate content, or expose a unified AI corpus.

The storage-provider adapter layer in `runtime/kv_storage_provider_adapter.py` provides a provider-neutral request contract for iCloud Drive, Google Drive, Microsoft OneDrive, and Dropbox. Each adapter can represent `CONNECT`, `VERIFY`, `READ`, `WRITE`, `SYNC`, and `DISCONNECT` intents without embedding credentials or claiming provider execution. Every request remains `PENDING_INTERLOCK_INTR`, requires a SKAP credential reference at runtime, fixes raw credential material absent, and fixes provider-session/operation/data-movement/replication effects false until an admitted runtime performs them.

Provider-operation state is durably represented inside each KV at `_System/Instances/Providers/provider-state.json`, with pending requests under `Requests/` and admitted operation receipts under `Receipts/`. Persisting a provider request does not connect a provider or change provider state. `runtime/kv_provider_operation_store.py` will materialize a result only when the supplied evidence is `ADMITTED`, bound to the same request and KV instance, contains Interlock and InTr receipt references, contains a SKAP credential reference, proves provider-operation execution, and contains no raw credential material. `READ`, `WRITE`, and `SYNC` fail closed unless the provider is already connected; `SYNC` additionally requires replication evidence. This store records admitted evidence but never authenticates a provider, resolves credentials, performs remote I/O, or decides admission.

See [`docs/KV_MULTI_INSTANCE_RELATIONSHIPS.md`](./docs/KV_MULTI_INSTANCE_RELATIONSHIPS.md) for the complete relationship contract.

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
├── _System/       receipts, instance identity, execution state, guides, migrations
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

## KV-bound ephemeral browser projection

For governed browser actions, KV remains the private continuity boundary while the physical browser/container is an ephemeral capability and presentation surface. The source producer `scripts/materialize_ephemeral_browser_projection_context.py` consumes an already-admitted KV entry-transition receipt and a compatible browser-capability observation from the same KV lineage, then emits only opaque SHA-256 commitments plus purpose/state metadata for the StegOS projection gate.

The producer does not decide Interlock/InTr admission, infer capability from browser identity, persist browser state, expose the KV lineage identifier, authenticate TV/TVC, or grant execution authority. Missing admission, mismatched KV lineage, non-KV continuity, or browser-identity authority fails closed.

See [`docs/KV_EPHEMERAL_BROWSER_PROJECTION_MIRROR_HANDOFF.md`](./docs/KV_EPHEMERAL_BROWSER_PROJECTION_MIRROR_HANDOFF.md) and [`docs/KV_PRIVACY_STATE_TRANSITION_CONTINUITY.md`](./docs/KV_PRIVACY_STATE_TRANSITION_CONTINUITY.md).

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
