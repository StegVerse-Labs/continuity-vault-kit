# KV Legacy Continuity Mirror Handoff

Status: CONNECTED_KV_LEGACY_DIRECTORIES_MATERIALIZED_READBACK_VERIFIED_FULL_PARITY_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Parent handoff: `CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`
Upstream contract: `StegVerse-Labs/Continuity/docs/LEGACY_CONTINUITY_MIRROR_HANDOFF.md`
Goal: `KV-LEGACY-CONTINUITY-001`
Authority effect: NONE
Activation effect: false

## Goal

Make Personal KnowledgeVault a private custody surface for governed legacy artifacts without making the repository, Site, recipient discovery, heartbeat, or candidate identity a disclosure authority.

## Implemented source surface

- `schemas/kv-legacy-capsule.schema.json`
- `runtime/legacy_capsule.py`
- `tests/test_legacy_capsule.py`
- `vault_template/KnowledgeVault/_Entities/Self/Legacy/README.md`
- `vault_template/KnowledgeVault/_Entities/Self/Legacy/Capsules/.gitkeep`
- `vault_template/KnowledgeVault/_Entities/Self/Legacy/Policies/.gitkeep`
- `vault_template/KnowledgeVault/_Entities/Self/Legacy/Recipients/.gitkeep`

## Connected private-KV materialization — observed 2026-09-04

The connected KnowledgeVault root was directly inspected through the authorized connected Drive surface. `_Entities/Self` did not contain a `Legacy` folder before this continuation.

This continuation created the inactive directory structure:

```text
KnowledgeVault/_Entities/Self/Legacy/
  Capsules/
  Policies/
  Recipients/
```

A direct provider readback immediately after creation observed exactly those three directories.

Repository evidence:

`evidence/legacy/connected-kv-legacy-directory-readback-2026-09-04.json`

Provider object identifiers are intentionally not copied into this bounded evidence record.

### Exact-template parity boundary

The repository template also requires:

`KnowledgeVault/_Entities/Self/Legacy/README.md`

That exact unconverted text file has **not** yet been installed through the available Drive file-import path in this continuation. Therefore:

```text
Legacy directory structure materialized: true
Legacy directory readback verified: true
Legacy README source present: true
Legacy README connected-KV install observed: false
full Legacy template parity: false
```

Do not promote directory presence into full template-parity completion.

This establishes **connected-KV directory materialization/readback only**. It does not establish sealed payload custody, a legacy recipient, a release policy, authentic capsule arming, death evidence, TVC authorization, InTr admissibility, recipient notification, Site activation, or economic transfer.

## Custody rule

The KV record stores a sealed payload reference/hash plus participant-authored policies and recipient references. Runtime helpers reject embedded plaintext payload fields and secret-bearing credential/key fields.

```text
private KV custody != recipient authorization
capsule exists != recipient may know it exists
candidate located != identity verified
identity verified != participation qualified
participation qualified != release admissible
release admissible != token-ledger mutation
```

## Disclosure evaluation

The source runtime supports progressive disclosure stages:

```text
UNKNOWN
INVITED
PARTICIPATING
QUALIFIED
CAPSULE_EXISTS
ORIGINATOR_IDENTITY
ASSET_CLASS
TERMS
FULL_PAYLOAD
```

A caller must present explicit verified evidence predicates. Missing predicates fail closed. The runtime never manufactures participation, identity, death, or release evidence.

## Economic reference boundary

A capsule may reference a `STEGCOIN` or `STEGTOKEN` bequest class, but this KV source does not reserve, issue, vest, transfer, burn, or promise either instrument. Economic release remains owned by the canonical StegFin/token-ledger path.

## Remaining work

1. Install exact unconverted `Legacy/README.md` into the already-materialized connected Legacy folder and verify direct filename/MIME/content-size readback.
2. Validate the KV legacy source through an existing credential-compliant validation surface; do not infer source validation from Drive materialization.
3. Add an owner-authorized private capsule write/readback path only after the sealed payload storage representation is admitted.
4. Bind recipient identity evidence from StegID.
5. Bind TV/TVC authorization and InTr release-admissibility receipts after their governing prerequisites clear.
6. Bind participation evidence to existing ecosystem activity/standing receipts.
7. Add Site Legacy & Continuity UX only after Site orchestrator admission.
8. Add delivery only after disclosure authorization.
9. Ingest actual private legacy payloads only through an owner-authorized KV write path.
10. Keep all authentic capsules NOT_ARMED until explicit participant activation and applicable legal disposition requirements are satisfied.

## Completion boundary

The Legacy directory structure is genuinely present in the connected private KV and directly read back. Full template parity, source validation, and authentic payload custody remain separate incomplete predicates. No authentic bequest has been armed or released.
