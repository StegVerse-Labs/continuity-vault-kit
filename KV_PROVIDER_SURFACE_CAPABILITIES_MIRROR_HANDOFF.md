# KV Provider / Access-Surface Capability Registry Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: #56  
State: IMPLEMENTED_ON_BRANCH_UNVERIFIED_FACT_SET  
Authority effect: NONE

## Purpose

Provide one canonical, provider-neutral registry that describes KnowledgeVault access behavior by:

`provider × device × platform × access surface × browser/runtime`

This extends the existing device-backed capability model. It does not replace it.

## Canonical files

- `specs/kv-provider-surface-capability-registry.v1.json`
- `schemas/kv-provider-surface-capability-registry.schema.json`
- `tools/check_provider_surface_capability_registry.py`

## Current implementation state

The schema, empty canonical registry, and fail-closed validator are installed on branch `feat/provider-surface-capability-56`.

The initial registry deliberately contains no provider capability claims. Provider families are enumerated, but observations remain empty until evidence is gathered. This prevents provider marketing text or model memory from becoming a verified capability claim.

## Required observation dimensions

- provider
- device class
- optional device model/capability profile
- platform / OS
- platform version when relevant
- access surface
- browser name / engine / version where applicable
- capability values
- limitations
- preferred route
- fallback route
- provenance and observation/version date

## Downstream contract

`StegVerse-org/LLM-adapter#140` consumes this registry for Ecosystem Chat public-knowledge resolution.

`StegVerse-Labs/Site#239` projects resolved facts into My KV, My Node / StegOS, and progressive troubleshooting UI.

Downstream consumers must not create independent provider-fact registries.

## Validation rule

A `VERIFIED` observation must carry a non-unknown evidence type, source reference, observation date, and version. Missing evidence fails closed.

## Boundary

This registry describes access-path capabilities only. It grants no provider access, credential authority, KV-content inspection authority, execution authority, or activation effect.

Private user-authored vault contents remain outside repository automation scope.
