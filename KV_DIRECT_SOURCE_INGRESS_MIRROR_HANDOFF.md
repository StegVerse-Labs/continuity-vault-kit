# KV Direct-Source SKAP Ingress Mirror Handoff

Status: SOURCE_LANE_OPEN / IMPLEMENTATION_IN_PROGRESS  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#108`  
Branch: `feature/kv-direct-source-ingress-108`  
Updated: 2026-08-28  
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

## Initial source artifacts

- `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md`
- `schemas/kv-direct-source-ingress-request.schema.json`
- `schemas/kv-direct-source-ingress-receipt.schema.json`
- `runtime/direct_source_ingress.py`
- `tests/test_direct_source_ingress.py`
- `tools/check_kv_direct_source_ingress.py`

## Downstream dependencies

This contract is intended to govern:

- `KV_PERSONAL_FINANCE_MIRROR_HANDOFF.md`;
- `KV_EMAIL_INGRESS_MIRROR_HANDOFF.md`;
- continuity directory population under `03_Records/**` and `04_Media/**`;
- Site/My KV directory and connection UX.

## Current boundary

Source contract only.

No real provider login has been performed by this lane.
No user credential or private source data is committed to the repository.
No provider session is activated.
No payment, trading, transfer, email-send, delete, upload, or account-management authority is granted.
