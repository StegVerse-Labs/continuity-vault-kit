# StegVerse.me Personal KnowledgeVault Mirror Handoff

Status: DOMAIN_ACQUIRED_DNS_UNCONFIGURED / PERSONAL_KV_PORTAL_CANDIDATE
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-PERSONAL-DOMAIN-001
Created: 2026-08-28

## Purpose

Define `stegverse.me` as the preferred human-facing namespace candidate for an individual's StegVerse / KnowledgeVault experience without making DNS, a web host, or the domain itself a custody or execution authority.

Canonical product meaning:

```text
stegverse.org -> ecosystem / governance / public infrastructure
stegverse.ai  -> governed AI / agent-facing entry point
stegverse.me  -> individual user's governed StegVerse / My KV portal
```

The preferred end-user framing is "My StegVerse" with the KnowledgeVault as the durable center.

## Observed domain state — 2026-08-28

User-provided Cloudflare DNS dashboard evidence shows:

```text
domain: stegverse.me
DNS setup: Full
DNS records used: 0 of 200
DNS records present: none
www.stegverse.me reachable: no
```

Therefore the domain is acquired / present in DNS management but is not yet routed to a web origin.

This observation does not prove registrar custody details, nameserver independence, TLS readiness, hosted service readiness, or production KV runtime activation.

## Architectural invariant

`stegverse.me` is an entrance, not the vault.

The domain MUST NOT become:

- KnowledgeVault custody authority;
- SKAP credential authority;
- TV/TVC credential authority;
- identity authority;
- Interlock/InTr execution authority;
- HeartBeat authority;
- receipt authority;
- recovery authority.

Loss, migration, or temporary unavailability of `stegverse.me` must not destroy the user's KV, receipts, credentials, identity continuity, or ability to reconstruct the governed operating environment.

## Intended user route

Initial product surface:

```text
stegverse.me
  -> My StegVerse
      -> My KV
      -> Personal
      -> Devices
      -> Connections
      -> Modules
      -> Receipts / History
      -> Settings
```

Examples:

```text
My KV -> Personal -> Email Addresses
      -> Add Address
      -> Authorize
      -> SKAP Vault credential completion
      -> governed email ingress

My KV -> Devices
      -> Register Device
      -> Receipt #1
      -> local/offline history
      -> Node evidence export
```

Do not expose raw repository paths, GitHub concepts, or internal runtime topology to ordinary users unless they intentionally open an advanced evidence/debug view.


## Canonical device-node route — accepted 2026-08-28

The preferred durable user route is:

```text
https://stegverse.me/n/<opaque-node>/
```

The web edge may internally serve `index.html`, but `index.html` is not required to be part of the permanent user-visible URL. A compatibility form such as `/n/<opaque-node>/index.html` may resolve to the same resource.

The `<opaque-node>` component is a routing handle only. It MUST NOT contain or directly expose:

- the user's real name;
- email address;
- phone number;
- raw device serial / hardware identifier;
- raw KV identifier;
- credential identifier;
- any other directly identifying or authority-bearing value.

The route MUST NOT itself confer device, KV, identity, SKAP, Interlock, or execution authority.

Required resolution flow:

```text
stegverse.me/n/<opaque-node>/
  -> authenticate / establish authorized user session
  -> verify node registration and current node/KV binding
  -> verify applicable Receipt #1 / continuity evidence
  -> evaluate current Interlock / readiness state
  -> resolve the associated KnowledgeVault
  -> render the node-specific My KV / StegOS projection
```

Possession or discovery of the URL alone is insufficient for access.

The node-specific page is the natural location for:

- My KV;
- device registration state;
- last StegOS synchronization;
- last KV synchronization;
- local/offline state;
- node receipt/history view;
- module availability/readiness;
- Node Evidence export.

A device-node route remains reconstructable and replaceable. The opaque route handle is not the durable source of truth; the KnowledgeVault plus admitted identity/node/receipt continuity remains authoritative.


## Device recognition and primary action state — accepted 2026-08-28

The device-node page MUST determine whether the current device has previously established a valid StegVerse node relationship before presenting the primary action.

The page should resolve a bounded local/device continuity signal first, then reconcile that signal against the governed node/KV receipt state when connectivity is available.

Canonical UI states:

```text
recognized prior device / valid node continuity:
  primary status/action label: Established Node

no valid prior device/node continuity:
  primary action label: Register Device
```

The displayed wording is intentionally user-facing:

- `Established Node` means the device has a previously admitted node identity/continuity relationship that can be verified or reconstructed from valid local + governed receipt evidence.
- `Register Device` means no valid established-node evidence is available for this device and a new governed registration flow is required.

The page MUST NOT infer `Established Node` merely from:

- possession of the node URL;
- a cookie alone;
- browser local storage alone;
- an unverified opaque-node handle;
- a claimed device name;
- a stale or revoked receipt;
- network/IP similarity.

Preferred state-resolution sequence:

```text
page opens
  -> inspect bounded local node continuity marker
  -> inspect cached last-known receipt/hash if available
  -> when online, reconcile against canonical KV/node continuity state
  -> validate non-revoked node binding
  -> render one of:
       Established Node
       Register Device
```

If the device is offline and a previously validated local continuity bundle exists, the page may render `Established Node` with an explicit local/offline state indicator. It must not claim fresh network validation until reconciliation occurs.

If evidence is missing, contradictory, revoked, or unverifiable, fail closed to `Register Device` or an explicit recovery/reverification path rather than silently treating the device as established.

A successful `Register Device` action should create the governed node registration transition and Receipt #1, persist the bounded local continuity marker required for future recognition, and then transition the page to `Established Node`.

The recognition mechanism is continuity evidence, not fingerprinting. Do not use covert browser/device fingerprinting as device authority.


## Node services page — accepted 2026-08-28

The canonical node-scoped services surface is:

```text
https://stegverse.me/n/<opaque-node>/services.html
```

A compatibility alias using case-insensitive web-server handling may accept `services.HTML`, but the canonical route should be lowercase `services.html`.

This page lists the individual's available StegVerse services as separate cards.

Default presentation:

```text
service installed/known but not activated in this individual's KV:
  card visible
  card visually grayed out
  card state: Inactive / Not Activated
  service action unavailable unless the user intentionally enters the governed activation flow

service activated in this individual's KV:
  card active
  card state: Active
  service entry/action available subject to current readiness and governance checks
```

The services page MUST derive card state from the individual's KnowledgeVault service/module state and current readiness projection. The web page MUST NOT maintain a separate authoritative activation registry.

Canonical authority rule:

```text
services.html displays state
KnowledgeVault owns persistent service activation state
Interlock/InTr governs admissible activation/action transitions
web UI owns no activation authority
```

A grayed card means the service is available to the user but is not presently activated for that individual's KV. It does not mean the service is globally unavailable.

A visually active card does not by itself prove that every external/provider action is currently executable. The card should distinguish, where applicable:

- Activated in KV;
- Ready locally;
- Governed action ready;
- Temporarily blocked / provider unavailable;
- Reverification required.

This prevents conflating `ACTIVE_IN_KV` with live provider/runtime readiness.

Preferred card contents:

- service name;
- concise plain-language description;
- activation state;
- readiness/availability indicator;
- optional setup-required indicator;
- link to service details;
- link to relevant receipt/history in an advanced view.

The page should be readable without repository, GitHub, schema, workflow, or internal architecture knowledge.

For inactive cards, activation should route through the individual's KV governance flow, not directly toggle client-side state. Successful activation must produce the appropriate governed KV state transition and receipt before the card changes from grayed to active.

Offline behavior:

- previously validated service states may be shown from the local node continuity/cache;
- the page must visibly indicate local/offline or stale state;
- no fresh activation should be claimed until the governed transition is reconciled.

Negative invariant: modifying HTML/CSS/JavaScript, local storage, cookies, or client-side card state MUST NOT activate a service in the KnowledgeVault.


## Canonical service governance states — accepted 2026-08-28

The services page is a governance projection, not merely a catalog.

Each service card MUST display one canonical user-facing service state:

```text
ACTIVE
INACTIVE
UNAVAILABLE
REVIEW
```

These are intentionally analogous to, but distinct from, the lower-level governance verdicts used by StegVerse.

Recommended semantic relationship:

```text
ALLOW       -> service may be ACTIVE when activation and readiness prerequisites are satisfied
DENY        -> requested activation/action is not admitted; service may remain INACTIVE
FAIL_CLOSED -> service/action is UNAVAILABLE because required evidence, authority, continuity, or runtime proof is missing or invalid
REVIEW      -> service is in REVIEW and requires user/governance attention before a transition may proceed
```

Do not collapse the two vocabularies into one field. A service lifecycle/status value describes the card's current state; a governance verdict describes the decision on a particular proposed transition or action.

Canonical card semantics:

```text
ACTIVE
  service is activated in this individual's KV
  card is visually active
  entry may still be bounded by action-specific readiness checks

INACTIVE
  service is known/available but not activated in this individual's KV
  card is grayed out
  card MUST visibly say "INACTIVE"
  user may enter the governed activation flow where permitted

UNAVAILABLE
  service cannot currently be used or activated because a required dependency, runtime, authority proof, continuity proof, provider/session, or other fail-closed prerequisite is absent/invalid
  card remains visible but non-operable
  reason should be explainable in plain language

REVIEW
  service or its activation state requires explicit review/reverification before proceeding
  card remains visible and non-operable except for the review/recovery action
```

### Device-continuity recovery action

`RE-REGISTER DEVICE` is a required recovery/action directive, not a fifth service lifecycle state and not a substitute for `REVIEW`.

When a service cannot safely rely on the current device continuity binding, the preferred projection is:

```text
service_state: REVIEW
required_action: RE-REGISTER DEVICE
```

If the missing/invalid device binding makes the service impossible to evaluate safely, the projection may instead be:

```text
service_state: UNAVAILABLE
required_action: RE-REGISTER DEVICE
```

The choice between REVIEW and UNAVAILABLE must be derived from the governing rule:

- use REVIEW when a valid human/governance decision or reverification can resolve the ambiguity;
- use UNAVAILABLE when the system must fail closed because the required continuity/authority evidence is absent or invalid.

A successful re-registration must produce a new governed device continuity transition/receipt before dependent service cards can advance.

### Display invariant

Color is never the only status signal.

Every card MUST show the text state explicitly:

- `ACTIVE`
- `INACTIVE`
- `UNAVAILABLE`
- `REVIEW`

Inactive cards are both grayed out and labeled `INACTIVE`.

The UI may additionally show the most recent governance verdict and required action in a details area, for example:

```text
Status: REVIEW
Decision: FAIL_CLOSED
Action: RE-REGISTER DEVICE
Reason: device continuity receipt is stale
```

This preserves the separation between service state, governance verdict, and recovery instruction while keeping the user-facing experience simple.

## Privacy / addressing constraint

Do not encode a user's real name, email address, precise identity, or raw KV identifier into public DNS labels or public URLs by default.

Preferred public/authenticated routes should use opaque session or account-safe identifiers and resolve user state only after authentication/governance admission.

## DNS activation rule

Do not add production A/AAAA/CNAME records merely to make the domain resolve.

The next DNS mutation should occur only after a canonical personal-KV web edge/origin is identified and validated.

Required before production routing:

1. identify the canonical `My KV` web origin / edge runtime;
2. confirm it does not make a third-party host the KV custody or execution authority;
3. confirm TLS/certificate path;
4. confirm authenticated landing behavior;
5. confirm fail-closed behavior when KV / Interlock runtime is unavailable;
6. confirm no plaintext credentials or KV secrets are exposed to the web origin;
7. confirm domain loss/migration is recoverable;
8. publish a durable observation receipt after routing.

## Preferred DNS shape once origin is proven

The minimal public shape should be:

```text
stegverse.me      -> canonical personal-KV web edge
www.stegverse.me  -> redirect or alias to stegverse.me
```

Additional subdomains should be created only for a real product boundary. Avoid premature DNS sprawl.

## Relationship to existing KnowledgeVault work

This goal consumes, but does not redefine:

- `CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`
- `PACKAGEABLE_USER_KV_MIRROR_HANDOFF.md`
- `KV_ACTIVATION_READINESS_MIRROR_HANDOFF.md`
- `KV_EMAIL_INGRESS_MIRROR_HANDOFF.md`
- `KV_INTERLOCK_RUNTIME_ENDPOINT_MIRROR_HANDOFF.md`

Packageability is already proven separately. Production InTr / Interlock / SKAP / provider activation remains separately gated and must not be inferred from DNS activation.

## Remaining machine-executable work

- locate or create the canonical My KV web shell / Site integration owner;
- define a domain-to-runtime routing contract;
- add an authenticated `My StegVerse` landing surface;
- expose read-only KV state first;
- bind device registration / Receipt #1 flow through the existing governed receipt model;
- add fail-closed runtime health/readiness projection;
- add domain migration/recovery tests;
- add DNS observation receipt schema;
- add negative tests proving domain/web-origin compromise does not grant KV, SKAP, identity, or execution authority.

## External/manual gate

DNS records cannot be safely finalized until the canonical web origin is selected and observed.

Current manual state:

```text
domain ownership/presence: OBSERVED
DNS routing: NOT CONFIGURED
www routing: NOT CONFIGURED
TLS production proof: NOT OBSERVED
My KV hosted surface: NOT OBSERVED
production KV activation: NOT CLAIMED
```

## Completion definition

This goal is complete only when:

```text
domain acquired: YES
canonical origin identified: YES
My KV shell implemented: YES
authenticated user route: VALIDATED
domain routing: OBSERVED
TLS: OBSERVED
fail-closed behavior: VALIDATED
domain migration/recovery: VALIDATED
no authority transfer to DNS/web host: VALIDATED
production receipt: DURABLE
```

Until then, `stegverse.me` is the preferred personal-KV namespace candidate with DNS intentionally unconfigured.
