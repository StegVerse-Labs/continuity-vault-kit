# Governed Connector Capability Contract

Status: PROPOSED_CANONICAL_SOURCE_CONTRACT
Repository: `StegVerse-Labs/continuity-vault-kit`
Authority effect: NONE
Activation effect: false
Credential authority: TV/TVC

## Core principle

A visible connector is not a capability.

A connector is a discoverable communication route. Operational capability exists only for the exact governed transition whose current predicates have been independently established.

Connector presence, credential possession, prior success, or provider integration must never be collapsed into present authority.

## Governed state progression

The following states are intentionally non-transitive. Each state establishes only itself and never proves the next state:

```text
AVAILABLE
 -> CONNECTED
 -> AUTHORIZED
 -> SCOPED
 -> IDENTIFIED
 -> COMMUNICABLE
 -> VERIFIED
 -> CURRENTLY_AUTHORIZED
 -> CONSEQUENCE_ADMISSIBLE
```

Meaning:

- `AVAILABLE`: the platform exposes the connector as an option.
- `CONNECTED`: an account or endpoint relationship has been established.
- `AUTHORIZED`: the relevant Human Authority has granted approved access.
- `SCOPED`: the exact resource boundary and operation class are bounded.
- `IDENTIFIED`: the exact object/resource can be stably distinguished.
- `COMMUNICABLE`: deterministic retrieval or transmission is presently possible through the governed route.
- `VERIFIED`: returned data/object/version can be checked against an authoritative record or declared integrity basis.
- `CURRENTLY_AUTHORIZED`: freshness, revocation, source drift, credential/session state, and human intent have been re-evaluated for the present operation.
- `CONSEQUENCE_ADMISSIBLE`: the requested state-changing consequence is separately permitted. Read, write, send, delete, trade, payment, publication, and other consequential operations are distinct capabilities.

A prior `VERIFIED` state must never silently become present permission. Conditions, permissions, sources, objects, credentials, and human intent can change.

## Component responsibilities

### Interlock

Interlock evaluates whether a proposed transition is eligible to advance. It must fail closed when any required predicate is absent, stale, contradictory, or indeterminate.

Connector visibility may establish `AVAILABLE` only. Interlock must not infer connection, authorization, scope, identity, retrieval, integrity, freshness, or consequence authority from availability.

### KnowledgeVault (KV)

KV is the durable governed context and reconstruction plane for non-secret connector state, including:

- user intent and policy;
- admitted provider/source identifiers;
- permitted resources and operation classes;
- exact resource identifiers after legitimate discovery;
- source/provider compatibility facts;
- continuity and provenance references;
- revocation and freshness state;
- prior receipts and transition lineage;
- non-secret route assembly metadata.

KV does not become credential authority and must not store reusable provider secrets merely because a connector exists.

### SKAP Vault

SKAP Vault provides bounded custody/session handling for security-bearing material needed to exercise an approved route. Possession or availability of credential material is not authority to use it for an arbitrary operation.

TV/TVC remains the credential authority. SKAP Vault must not independently manufacture authorization.

### InTr

InTr carries the exact governed transition after Interlock predicates pass. It should receive a bounded operation contract such as:

```text
subject
resource
operation
purpose
scope
credential/session reference
freshness basis
expected integrity basis
consequence class
```

The connector is therefore a transport endpoint underneath the governed transition rather than an authority-bearing object.

## Reference path

```text
AI / Human / Service
 -> proposed operation
 -> Interlock
    -> KV intent/policy/current state
    -> exact capability predicates
    -> exact object/scope predicates
    -> TV/TVC credential authority
    -> SKAP Vault credential/session material
    -> freshness/revocation checks
    -> consequence-admissibility checks
 -> InTr governed transition
 -> narrowly-scoped connector communication
 -> external provider/source
 -> response / far-side evidence
 -> identity + integrity + provenance verification
 -> receipt / transition lineage
 -> KV durable governed state
```

## Capability reconstruction at time of use

Communication authority is reconstructed at the moment of use rather than inherited from possession of a connector credential.

A token, session, linked account, or previously successful request may contribute evidence, but cannot alone establish:

- present human intent;
- present authorization;
- exact scope;
- exact object identity;
- current source compatibility;
- current credential/session validity;
- admissible operation class;
- acceptable consequence;
- canonical transition authority.

A representative decision shape is:

```text
if connector_visible:
    state = AVAILABLE

if (
    human_intent_current
    and kv_policy_allows
    and capability_allowed
    and scope_matches
    and exact_object_matches
    and tvc_authority_valid
    and skap_session_available
    and source_compatibility_current
    and revocation_checks_pass
    and consequence_class_admissible
):
    Interlock may admit the exact InTr transition candidate
```

Even this admission does not grant unrelated operations or future authority.

## Provider-neutral capability projection

Google Drive, GitHub, Gmail, health-data systems, financial systems, social networks, local filesystems, local models, StegVerse Nodes, and future providers should project into the same provider-neutral capability contract.

A capability consumer should ask:

> Can governed operation X be performed on resource Y for purpose Z under current authority A?

It should not ask:

> Does a connector or token exist?

## StegIndex projection

StegIndex should be able to represent connector discovery and exact operational capability separately. Example:

```text
provider_connector: DISCOVERED
account_relationship: CONNECTED
resource_identity: VERIFIED
read_capability: ACTIVE
write_capability: DENIED
integrity_verification: ACTIVE
current_authorization: ACTIVE
consequence_admissibility: READ_ONLY
```

A discovered connector must make a capability a candidate, not make it operationally available.

## Non-authority invariants

```text
connector visibility != connection
connection != authorization
authorization != scope
scope != object identity
object identity != deterministic communication
communication != integrity verification
prior verification != current authorization
credential possession != operation authority
current authorization != consequence admissibility
connector route != canonical transition authority
SKAP custody != credential authority
KV policy != credential authority
InTr transport != independent authority
HB/liveness != connector authority
```

## Relationship to existing KV connection assembly

This contract specializes the existing KV connection-assembly model. The assembly remains responsible for deterministic non-secret route reconstruction and source-change compatibility handling. This contract adds an explicit epistemic and authority state model so that a connector's visible or connected state cannot be promoted into operational capability without independently demonstrated predicates.

## Runtime evidence boundary

This document defines source semantics only. It does not establish that any provider connector is currently connected, authorized, scoped, retrievable, verified, fresh, consequence-admissible, or active. Authentic runtime capability must be demonstrated through the live authority-owned path and preserved as corresponding receipts/evidence.
