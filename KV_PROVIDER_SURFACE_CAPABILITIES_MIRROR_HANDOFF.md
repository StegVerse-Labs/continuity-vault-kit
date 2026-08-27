# KV Provider / Access-Surface Capability Registry Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: #56  
State: IMPLEMENTED_VALIDATED_MERGED / DOCUMENTED_FACT_POPULATION_ON_BRANCH  
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

The canonical registry foundation is merged. On branch `feat/provider-surface-documented-facts-56`, the first provider-documentation fact set is populated with state `DOCUMENTED_UNVERIFIED`.

Eight observations are represented across:
- iCloud Files on iPhone / iOS;
- iCloud Files on iPad / iPadOS;
- Google Drive native app on iPhone;
- Google Drive native app on iPad;
- Google Drive desktop browser offline posture for Chrome/Edge;
- OneDrive native app on iPhone;
- OneDrive native app on iPad;
- OneDrive Files On-Demand / sync-client posture on Windows.

Every observation is `DOCUMENTED`, not `VERIFIED`. Unsupported capability fields remain `UNKNOWN`; no preferred route or fallback route is inferred where provider documentation does not establish one.

Provider-documentation evidence references are retained directly in each observation. The top-level state `DOCUMENTED_UNVERIFIED` is deliberately distinct from `PARTIALLY_VERIFIED` so documentation evidence cannot be mistaken for StegVerse conformance proof.

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

1. Validate and merge the first eight provider-documentation observations.
2. Continue provider-documentation population for AWS/object storage, self-hosted/private cloud, and future StegCloud only when authoritative public sources exist.
3. Add StegVerse-observed/conformance-tested records separately; documentation evidence alone never becomes `VERIFIED`.
4. Merge and release the LLM-adapter#140 canonical-registry consumer.
5. Project resolved provider-route explanations into Site#239 after Site machine admission.
6. Keep actual user-specific route selection separate from generic provider capability facts.

## Boundary

This registry describes access-path capabilities only. It grants no provider access, credential authority, KV-content inspection authority, execution authority, or activation effect.

Private user-authored vault contents remain outside repository automation scope.

## Documented-fact evidence semantics

The validator now enforces:

- `DOCUMENTED` requires provider-documentation source type, source reference, and observation date;
- `OBSERVED` requires StegVerse observation or conformance-test evidence;
- `VERIFIED` requires evidence and may not be inferred from documentation alone;
- `INSTALLED_UNVERIFIED` cannot contain observations;
- `DOCUMENTED_UNVERIFIED` cannot contain verified observations;
- `PARTIALLY_VERIFIED` requires at least one actually verified observation;
- `VERIFIED` requires every observation to be verified.

Negative tests exercise documented-without-evidence and partially-verified-without-verified-observation failures.
