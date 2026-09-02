# KV Connection Assembly Source Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / LIVE_CONNECTION_OBSERVATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #113
Branch: `main`
Updated: 2026-08-28
Authority effect: NONE
Activation effect: false

## Purpose

Evolve Personal KnowledgeVault from only a durable continuity destination into a governed connection-assembly source for its own ingress and egress Interlock/InTr paths.

The KV should retain enough non-secret source/provider knowledge to deterministically assemble, validate, monitor, and repair the connection contract for each admitted data source without turning KV into credential authority or external-provider execution authority.

Canonical model:

```text
provider/source facts
 -> provider capability registry
 -> source-specific connection assembly profile
 -> SKAP/TVC credential/session references
 -> Interlock/InTr ingress/egress route
 -> live conformance observation
 -> KV data/readback
 -> source-change monitoring
 -> compatibility impact assessment
 -> route repair/revalidation when required
```

## Governing principles

1. The external provider remains factual source authority.
2. TV/TVC remains credential/secret/token authority.
3. SKAP remains reusable credential custody/session boundary.
4. KnowledgeVault may own durable non-secret connection metadata, route assembly intent, compatibility evidence, and source-change history.
5. Site/My KV may display connection health and compatibility state but does not own provider execution.
6. Provider capability facts remain canonical in `KV_PROVIDER_SURFACE_CAPABILITIES_MIRROR_HANDOFF.md`; this lane consumes that registry and must not create a duplicate provider-fact registry.
7. Direct-source ingress remains governed by `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md`.
8. Any provider mutation/write/send/trade/payment/delete authority remains a separate governed capability.

## Connection assembly record

A provider connection assembly should be derivable from bounded, non-secret records describing:

- provider/source identifier;
- provider product/account class;
- direct source route class;
- required authentication mechanism class;
- SKAP credential/session reference class, never reusable secret value;
- device/platform/browser/runtime requirements where relevant;
- ingress endpoint/surface;
- egress endpoint/surface where separately authorized;
- required Interlock/InTr hops;
- normalization adapter/version;
- canonical KV target path/domain;
- source provenance requirements;
- expected refresh/observation cadence;
- provider capability version/date;
- known limitations;
- compatibility state;
- last successful connection proof;
- last successful data readback proof;
- change-monitor state;
- repair/revalidation state.

## Source-change monitoring

The connection assembly must support monitoring of authoritative source/provider changes that can affect KV/InTr compatibility, including:

- API version changes;
- authentication/OAuth changes;
- MFA/session changes;
- endpoint changes;
- deprecation notices;
- provider changelogs;
- SDK/library compatibility notices where an adapter depends on them;
- rate-limit changes;
- permission/scope changes;
- product/account model changes;
- data-schema changes;
- file/export format changes;
- browser/platform support changes;
- provider outage/service-health changes where relevant.

Monitoring evidence must identify source, observation time, affected connection assembly IDs, compatibility impact, and whether revalidation is required.

## Compatibility states

Initial state model:

```text
UNASSEMBLED
ASSEMBLED_UNVERIFIED
VERIFIED
DEGRADED
REVALIDATION_REQUIRED
BLOCKED_SOURCE_CHANGE
BLOCKED_SESSION
BLOCKED_RUNTIME
RETIRED
```

A source change may never silently remain `VERIFIED` when its declared compatibility assumptions have changed.

## Repair semantics

Connection repair is a governed reconstruction process, not an ad hoc reconnect:

```text
source change observed
 -> determine impacted assumptions
 -> invalidate stale verification
 -> rebuild bounded route/profile if source contract permits
 -> re-run conformance proof
 -> re-establish SKAP/TVC session binding if required
 -> prove KV readback
 -> emit new connection receipt
```

Credential values remain inaccessible to the assembly record.

## Planned canonical artifacts

- `KV_CONNECTION_ASSEMBLY_SOURCE_MIRROR_HANDOFF.md`
- `schemas/kv-connection-assembly.schema.json`
- `schemas/kv-connection-assembly-registry.schema.json`
- `specs/kv-connection-assembly-registry.v1.json`
- `schemas/kv-source-change-observation.schema.json`
- `schemas/kv-connection-health-receipt.schema.json`
- `runtime/connection_assembly.py`
- `runtime/source_change_monitor.py`
- `tests/test_connection_assembly.py`
- `tests/test_source_change_monitor.py`
- `tools/check_kv_connection_assembly.py`
- read-only validation workflow

## Non-goals

This lane does not:

- store passwords/tokens/private keys;
- replace TV/TVC or SKAP;
- perform provider login by itself;
- create a second provider capability registry;
- make GitHub Actions production monitoring authority;
- grant provider write/mutation authority;
- claim live provider compatibility without observed conformance evidence.

## Immediate implementation order

1. Define the connection assembly schema referencing the existing provider capability registry.
2. Define source-change observation and connection-health receipt schemas.
3. Implement deterministic assembly validation and compatibility-state transitions.
4. Add synthetic provider-change tests.
5. Bind Coinbase as the first source-specific assembly consumer after the existing SKAP/TVC runtime is live-proven.
6. Later project connection health into My KV Site.

## Current boundary

Machine-executable source contract is implemented on this branch. No source monitoring process is live, no provider change has been observed by this lane, no connection has been activated, and no credential or provider execution authority is granted.


## Post-merge canonical reconciliation — 2026-08-28

```text
issue: #113
pull_request: #114
merge_commit: 660861d98f7ec57ee85baa6f53540d79584dcc10
source_state: MERGED_VALIDATED
authority_effect: NONE
activation_effect: false
```

Validation evidence:

```text
Validate KV Connection Assembly run 33191143644: SUCCESS
Security Baseline run 33191143335: SUCCESS
Repository validation diagnostics run 33191143584: SUCCESS
KV Guardrails run 33191143383: SUCCESS
```

Source contract, schemas, runtime assembly logic, synthetic tests, and validation are merged. No live provider connection, provider login, credential resolution, or production provider monitoring is claimed.

GitHub Actions remain validation-only. TV/TVC remains credential authority. These source merges do not prove resident execution, provider compatibility, private-KV user state, provider login, or external provider operation.


## Personal KV provider-binding reconciliation — 2026-09-02

Canonical specialized handoff: `PERSONAL_KV_PROVIDER_BINDING_MIRROR_HANDOFF.md`.

Current source already contains a bounded Google Drive Personal-KV materializer under `runtime/personal_provider_binding.py`, consumed downstream by `StegVerse-Labs/.github/scripts/materialize_personal_kv_provider_root.py` before DEVICE_KV query execution when no local `STEGVERSE_KV_ROOT` exists.

This does not create a new credential path. Automatic provider-backed Personal-KV execution remains blocked until an existing TVC-owned ephemeral provider session is legitimately active under the current TVC credential-model consistency rules. Missing session therefore fails closed; Site/DEVICE_KV must not invent or persist a provider token.
