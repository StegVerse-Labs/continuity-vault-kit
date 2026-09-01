# KnowledgeVault Installation Status Projection Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `feat/kv-installation-status-projection-20260831`
Updated: 2026-08-31T21:11:00-05:00
State: MERGED_VALIDATED / DEVICE_KV_RUNTIME_OBSERVATION_PENDING
Credential authority: TV/TVC
Authority effect: NONE

## Goal

Expose one bounded read-only projection of the canonical resident KnowledgeVault installation receipt so the existing DEVICE_KV query/return lane can determine whether the current resident KV root is a validated canonical installation.

Canonical path:

```text
<STEGVERSE_KV_ROOT>/_System/installation.receipt.json
```

This projection is for My KV onboarding Step 2. It is not Step 5 cloud-provider revalidation.

## Required semantics

A successful projection requires the current resident KV root to contain a canonical installation receipt with:

- `schema_version=1.1`;
- canonical Continuity Vault Kit source binding;
- verified source tree SHA;
- destination ending in `/KnowledgeVault`;
- full recursive/source-defined file+directory presence;
- `full_template_parity=VALIDATED`;
- `authority_effect=NONE`;
- `activation_effect=false`;
- non-empty source census.

Returned projection must exclude provider file/folder IDs, credentials, secrets, private file contents, and full destination path.

## Output

```text
schema=stegverse.kv.installation-status-projection/v1
state=KV_INSTALLATION_VERIFIED | KV_INSTALLATION_NOT_VERIFIED
resident_kv_root_observed=true
installation_receipt_present=true|false
source_tree_sha=<bounded hash|null>
receipt_sha256=<content digest|null>
receipt_verified_utc=<timestamp|null>
full_template_parity=VALIDATED|null
source_census=<bounded counts|null>
destination_kind=<bounded scheme/category|null>
current_cloud_provider_observation=false
credential_material_present=false
provider_operation_authorized=false
authority_effect=NONE
```

The projection proves only what is observable from the current resident KV root. It does not claim current provider/session observation, credential authority, mutation authority, or runtime activation.

## Claimed surfaces

- `runtime/portable_directory_projection.py`
- `tests/test_portable_directory_projection.py`
- `tools/check_portable_directory_projection.py`
- this handoff

## Completion boundary

Source implementation, deterministic validation, merge. DEVICE_KV transport exposure and Site Step 2 consumption are separate downstream integrations.


## Merge evidence

```text
PR #168
merge b62387bb5ddb13dcca6ff5c7c24e5a14a2a10d23
KV Guardrails (Layer + Footer + Emoji + InTr): SUCCESS
Security Baseline: SUCCESS
Repository validation diagnostics: SUCCESS
```

Source lifecycle:

```text
implemented=true
validated=true
merged=true
resident DEVICE_KV query observation=false
public-device observation=false
```

Downstream endpoint integration merged in `StegVerse-Labs/.github` PR #725 at `0ffe6a5ea61b2a0c24a28b702545ffbd8f6c0ec7`.
Site live-first Step 2 integration merged in `StegVerse-Labs/Site` PR #881 at `8e5540917531dd34219ada22a568024817c3e956`.
