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

## Auri / StegWhisper reusable peripheral profiles — source proposal 2026-09-25

Source-review-only extension under the existing device-backed capability owner (issue #53) and typed transport owner (issue #124). This proposed branch does not modify the connected owner's KV, execute any MyKV/SKAP registration or obtain a new task checkout. Canonical Registry main reconciled through generation 248 on 2026-09-25; recheck latest generation before any canonical state mutation. Source edits/tests/reviewed merge proceed independently of any unavailable AI_SESSION_GATE interface; authentic Interlock/InTr receipts remain mandatory for real transitions. Its global device-interchangeability and KV/SKAP user-verification invariants remain unchanged.

New source contract:
- `specs/kv-auri-peripheral-capability-profiles.v1.json`: independently scoped display, touch/gesture, microphone input, speaker output, camera input, visual/AR output and optional flexible-glass capability composition.
- `schemas/kv-auri-peripheral-capability-profiles.schema.json`: non-authorizing schema.
- `scripts/validate_kv_auri_peripheral_profiles.py` and `tests/test_kv_auri_peripheral_profiles.py`: deterministic source-only invariant/mode checks.
- Existing `auri-ecosystem-chat` and `stegwhisper` registry entries now reference the reusable profile contract, preserving their original module IDs, KV surfaces, `INSTALLED_INACTIVE` states and `authority_effect=NONE`.

Three candidate mode intents use one existing KV conversation and require a freshly scoped manifest for changes:
`live_audio` (microphone + audio output), `live_video` (camera + visual output), and `live_audio_video` (independent admission for both). Direct stop/mute is independent of inference. Input permission is never inferred from output permission, device pairing or registration.

The source-only evaluator deliberately returns `CANDIDATE_ALLOW_REQUIRES_REAL_RUNTIME_DISPOSITION` or `CANDIDATE_NON_ALLOW`; it cannot mint authentic ALLOW/DENY or Master Records receipts. Existing checked-out `STEGOS-DEVICE-KV-SKAP-ROUNDTRIP-001`, `KV-BOUND-EPHEMERAL-BROWSER-PROJECTION-001`, Ecosystem Chat and the shared voice owners retain all implementation/runtime custody. Existing typed transport classes must be observed and each actual adjacent hop admitted through Interlock/InTr. TV/TVC remains credential authority; MyKV/SKAP remains sole user verifier. Flexible glass is an optional hardware composition with unobserved material/electrical/capture capabilities, not an activation dependency or proof that photovoltaics make a display.

This document records a non-authorizing source proposal only; exact-head CI, canonical existing-owner source approval/merge, authentic device/peripheral execution, SKAP relationship readback, transport/transition dispositions and Master Records reconstruction remain separate evidence classes.
