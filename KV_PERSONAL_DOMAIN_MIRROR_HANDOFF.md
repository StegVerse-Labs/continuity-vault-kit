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
