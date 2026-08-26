# KV Provider / Access-Surface Capability Registry Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: #56  
State: IMPLEMENTED_VALIDATED_MERGED / FACT_POPULATION_OPEN  
Authority effect: NONE

## Purpose

Provide one canonical, provider-neutral registry that describes KnowledgeVault access behavior by:

`provider × device × platform × access surface × browser/runtime`

This extends the existing device-backed capability model. It does not replace it.

## Canonical files

- `specs/kv-provider-surface-capability-registry.v1.json`
- `schemas/kv-provider-surface-capability-registry.schema.json`
- `tools/check_provider_surface_capability_registry.py`
- `tests/test_provider_surface_capability_registry.py`
- `.github/workflows/provider-surface-capability-registry.yml`

## Implementation evidence

Implementation PR: `#63`  
Implementation head: `0eebc3e77a17fcc4c75779730615b24ffa295bf2`  
Merge commit: `8934e123b33b600d1e5c78acf642ae15de89f4c7`

Exact-head validation:
- KV Provider Surface Capability Registry run `33023812113`: PASS
- Security Baseline run `33023811994`: PASS
- Repository validation diagnostics run `33023812024`: PASS
- Release integrity run `33023812064`: PASS
- KV Guardrails run `33023811986`: PASS

## Current fact state

The canonical registry is intentionally `INSTALLED_UNVERIFIED` with an empty `observations` list.

Provider families are enumerated, but no concrete provider/browser/device capability claim is admitted until evidence is gathered. This prevents provider marketing text, generic model memory, or undocumented assumptions from becoming verified capability facts.

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

## Remaining work

1. Gather provider-documentation and StegVerse-observation evidence for iCloud, Google Drive, OneDrive, AWS/object-storage, self-hosted/private cloud, and future StegCloud.
2. Populate device/platform/access-surface observations without overgeneralizing across device classes.
3. Add negative tests proving unsupported VERIFIED claims fail closed.
4. Feed the canonical registry into LLM-adapter#140.
5. Project resolved provider-route explanations into Site#239.
6. Keep actual user-specific route selection separate from generic provider capability facts.

## Boundary

This registry describes access-path capabilities only. It grants no provider access, credential authority, KV-content inspection authority, execution authority, or activation effect.

Private user-authored vault contents remain outside repository automation scope.
