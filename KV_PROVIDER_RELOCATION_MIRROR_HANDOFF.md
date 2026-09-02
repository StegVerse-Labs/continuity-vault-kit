# KV Provider Relocation Mirror Handoff

Status: SOURCE_IMPLEMENTATION_IN_PROGRESS
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #177
Branch: feature/kv-provider-relocation-177

## Goal

Prove relocation of an already-recovered KnowledgeVault between storage providers without transferring KV, device, credential, execution, recovery, or governance authority to either provider.

Initial deterministic case:

iCloud -> Google Drive

## Invariants

- provider access != KV authority
- storage relocation != device enrollment
- KV identity persists across provider change
- continuity root must be preserved or advance through an explicit governed transition
- Interlock/InTr binds the relocation transition
- TV/TVC remains credential authority
- browser/provider access cannot become an execution surface
- source/CI completion does not prove live provider migration

## Required outcomes

Use only:
ALLOW
ALLOW_WITH_SIGNOFF
DENY
FAIL_CLOSED
REDIRECT
ESCALATE

## Current state

provider relocation issue: OPEN
source implementation: IN_PROGRESS
hosted validation: NOT YET RUN
merged: NO
live provider migration: NOT OBSERVED
runtime activation: NOT CLAIMED
authority_effect: NONE
