# KV Legacy Continuity Mirror Handoff

Status: SOURCE_IMPLEMENTED_PENDING_HOSTED_VALIDATION
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

1. Install the new Legacy template paths into the connected private KV and verify exact readback.
2. Bind recipient identity evidence from StegID.
3. Bind TV/TVC authorization and InTr release-admissibility receipts.
4. Bind participation evidence to existing ecosystem activity/standing receipts.
5. Add Site Legacy & Continuity UX.
6. Add delivery only after disclosure authorization.
7. Ingest actual private legacy payloads only through an owner-authorized KV write path.
8. Keep all authentic capsules NOT_ARMED until explicit participant activation and legal disposition requirements are satisfied.

## Completion boundary

Source implementation is not live private-KV custody and not an armed bequest.
