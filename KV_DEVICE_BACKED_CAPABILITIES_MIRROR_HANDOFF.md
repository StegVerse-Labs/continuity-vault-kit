# KV Device-Backed Capability Installation Mirror Handoff

Status: INSTALLED_INACTIVE_CONNECTED_KV
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #53
Updated: 2026-08-26

## Decision

Device-backed capability state MAY be installed into KnowledgeVault before Interlock/InTr activation.

Installation means durable KV surfaces and a capability registry are present. It does not activate execution, identity, governance, credentials, providers, network access, or external side effects.

Canonical invariant:

```text
KV holds what persists.
Device/StegOS supplies what happens.
Interlock/InTr governs transitions when activated.
Installation != activation.
```

## Canonical registry

- `specs/kv-device-backed-capability-registry.v1.json`
- `schemas/kv-device-backed-capability-registry.schema.json`

All registry entries are `INSTALLED_INACTIVE`, `authority_effect=NONE`, and reuse existing KV surfaces instead of creating duplicate domain stores.

## Installed modules

```text
stegid-continuity
governance-steggate
stegtalk
stegwhisper
steghealth
stegfin-wallet-pay
genealogy
media-playlists-reading
family-sharing
organization-context
auri-ecosystem-chat
stegteacher-onboarding
erl-research
```

## Live connected-KV installation

Connected KnowledgeVault root:

`1c8OdhJeLD6E4ALmi-aR7dXvG8PjDLSfi`

Installed runtime registry surface:

`/KnowledgeVault/_System/Modules/`

Drive folder:

`1v7qTxizuaN385fD-GZHr_HMmgJpgTJxM`

Registry projection:

`module-registry`
Drive file id: `1afD641cUGtQK7Bco2b9YL9ZXT77bLB9VAQFJeYz4SHI`

Direct Drive enumeration observed the registry plus all 13 module folders.

Direct registry readback observed:

```text
schema=stegverse.kv.device-backed-capability-registry/v1
state=INSTALLED_INACTIVE
interlock_activation_required_for_install=false
runtime_activation_claimed=false
network_activation_claimed=false
credential_activation_claimed=false
provider_activation_claimed=false
authority_effect=NONE
device_role=EPHEMERAL_ACTIVITY_EDGE
kv_role=DURABLE_STATE_CONTINUITY_AND_RECONSTRUCTION
```

The Drive registry document is a connected-KV projection/index. The canonical portable machine-readable registry remains the repository JSON source.

## Activation boundary

A module may become active only after its listed Interlock/authority/provider prerequisites are actually observed. Folder presence or registry installation cannot satisfy those predicates.

No Interlock activation, InTr activation, execution authority, identity authority, governance authority, credential authority transfer, provider activation, network activation, or external side effect is claimed by this installation.

## Completion

```text
canonical registry source: COMPLETE_ON_BRANCH
schema: COMPLETE_ON_BRANCH
connected KV Modules surface: COMPLETE
13 module slots: COMPLETE
connected registry projection: COMPLETE
connected registry readback: PASS
Interlock/InTr activation: NOT CLAIMED / SEPARATE
module runtime activation: NOT CLAIMED / SEPARATE
```


## Personal Services extension

A separate Personal Services registry now extends this module layer without converting services into app-owned data silos.

Canonical handoff:

`KV_PERSONAL_SERVICES_MIRROR_HANDOFF.md`

Canonical source:

`specs/kv-personal-services-registry.v1.json`

Connected KV surface:

`/KnowledgeVault/_System/Services/`

The service layer follows the same installation boundary as this capability registry:

```text
service installation may occur before Interlock/InTr activation
service installation does not grant authority
service data remains in existing semantic KV surfaces
device/StegOS supplies activity
```
