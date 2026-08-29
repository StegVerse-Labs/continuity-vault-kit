# KV Direct-Source SKAP Ingress Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / LIVE_PROVIDER_ACTIVATION_PENDING  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#108`  
Merged PR: `#110`  
Validated head: `fa53f2ffda1783858a86bf34e4f0920c92f783a5`  
Updated: 2026-08-29  
Authority effect: NONE  
Activation effect: false

## Purpose

Define the canonical ingress rule for Personal KnowledgeVault continuity data:

```text
owner chooses direct source
 -> SKAP Vault resolves bounded credential/session reference
 -> source-native provider login/session
 -> minimum-necessary read
 -> source-specific normalization
 -> governance/admission
 -> canonical KV directory/state projection
 -> provenance + receipt
```

The direct provider/source remains the factual source of imported data. KnowledgeVault remains the durable user-controlled continuity store. SKAP Vault remains the reusable credential boundary.

## Canonical rule

Continuity data intended to populate Personal KV directories should be obtained from the direct authoritative source wherever such a source exists and the owner authorizes access.

Examples:

- finance / assets / liabilities: source financial institution, brokerage, card issuer, lender, exchange, payroll/tax source, or other direct account provider;
- email: source mailbox provider;
- pictures/media: source photo/media provider or owner-controlled storage;
- music: source music provider or owner-controlled library;
- future continuity domains: the original system of record or owner-controlled source.

An intermediary aggregator may not silently become canonical source authority. If an intermediary is explicitly admitted as transport or convenience, provenance must still identify the underlying source and the intermediary role, and direct-source unavailability must not be hidden.

## SKAP credential boundary

1. Passwords, OAuth refresh tokens, API secrets, private keys, app passwords, recovery codes, and reusable authentication material remain behind SKAP Vault.
2. Ordinary KV content stores only bounded `skap://` references, non-secret provider/session metadata, and receipts where required.
3. A source adapter requests credential resolution from SKAP; it does not receive permission to persist the reusable secret into KV.
4. Site/My KV never renders reusable credentials.
5. Credential/session revocation must prevent subsequent source access.
6. A SKAP reference does not itself grant data-write, payment, trading, sending, deletion, or provider-management authority.

## Access authority

Default ingress is:

```text
READ_ONLY
MINIMUM_NECESSARY
OWNER_AUTHORIZED
DIRECT_SOURCE_REQUIRED
```

Any write/transaction/send/delete capability is a separate governed capability and is outside this ingress contract.

## Fail-closed behavior

Ingress fails closed when:

- no supported direct-source adapter exists;
- SKAP credential reference is absent or revoked;
- provider login/session verification fails;
- the provider cannot prove the requested owner/account binding;
- returned data violates the adapter schema;
- source identity/provenance is ambiguous;
- governance/admission is unavailable or ambiguous;
- canonical KV persistence cannot be confirmed.

No synthetic or stale fallback data may be presented as fresh direct-source state.

## Provenance

Every admitted import must preserve:

- provider/source identifier;
- direct source URL/origin class or provider route identifier;
- owner/account binding reference using a masked/non-secret identifier;
- retrieval timestamp;
- source coverage period where applicable;
- adapter/version;
- whether any intermediary transport was used;
- normalization receipt/reference;
- admission/persistence receipt/reference;
- freshness state.

## Implemented source artifacts

- `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md`
- `schemas/kv-direct-source-ingress-request.schema.json`
- `schemas/kv-direct-source-ingress-receipt.schema.json`
- `runtime/direct_source_ingress.py`
- `tests/test_direct_source_ingress.py`
- `tools/check_kv_direct_source_ingress.py`

## Validation and merge state

Source implementation merged through PR #110 from exact head `fa53f2ffda1783858a86bf34e4f0920c92f783a5`.

GitHub Actions reports six completed validation runs for that exact head. The observed run set includes `Automation candidate implementation - Validation Only` with conclusion `success`; no failed conclusion was observed in the exact-head run set before merge.

Repository source completion is therefore `MERGED_VALIDATED`. This does not create a provider session or satisfy any live SKAP/provider/private-KV proof gate.

## Downstream dependencies

This contract governs or is consumed by:

- `KV_PERSONAL_FINANCE_MIRROR_HANDOFF.md`;
- `KV_COINBASE_FINANCE_INGRESS_MIRROR_HANDOFF.md`;
- `KV_EMAIL_INGRESS_MIRROR_HANDOFF.md`;
- continuity directory population under `03_Records/**` and `04_Media/**`;
- Site/My KV directory and connection UX.

## Remaining machine/runtime work

1. establish an admitted resident provider session through the existing TVC/SKAP boundary for each concrete provider lane;
2. obtain direct-source/session verification evidence without persisting reusable secrets in ordinary KV;
3. execute the source-specific normalization path;
4. persist only admitted canonical output into the private KV;
5. verify private-KV readback and provenance/receipt binding;
6. preserve explicit fail-closed state for unsupported, revoked, ambiguous, or stale provider paths;
7. after admitted release transitions, verify downstream projections without claiming live activation from source merge alone.

## Current boundary

Issue #108 repository source implementation is complete and merged and may be closed as a source-contract task.

No real provider login has been performed by this repository lane.
No user credential or private source data is committed to the repository.
No provider session is activated.
No payment, trading, transfer, email-send, delete, upload, or account-management authority is granted.
