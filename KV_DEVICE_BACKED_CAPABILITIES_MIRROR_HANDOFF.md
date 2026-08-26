# KV Device-Backed Capability Installation Mirror Handoff

Status: ACTIVE_INSTALLATION
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

## Initial modules

StegID/Continuity; Governance/StegGate; StegTalk; StegWhisper; StegHealth; StegFin/StegWallet/StegPay; Genealogy; Media/Playlists/Reading; Family Sharing; Organization Context; Auri/Ecosystem Chat; StegTeacher/Onboarding; ERL/Research.

## Activation boundary

A module may become active only after its listed Interlock/authority/provider prerequisites are actually observed. Folder presence or registry installation cannot satisfy those predicates.

## Live Drive target

`/KnowledgeVault/_System/Modules/`

The live Drive copy must contain the registry plus per-module directories or equivalent durable slots, and readback must preserve the canonical inactive/no-authority state.
