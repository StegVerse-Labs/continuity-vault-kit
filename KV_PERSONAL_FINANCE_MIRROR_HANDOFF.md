# KV Personal Finance Mirror Handoff

Status: SOURCE_IMPLEMENTED_ON_BRANCH / VALIDATION_PENDING  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#106`  
Branch: `feature/kv-personal-finance-106`  
Updated: 2026-08-28

## Purpose

Add a bounded Personal KnowledgeVault finance-tracking model that can represent accounts, balances, liabilities, transactions, recurring activity, rewards/yield, and collateral relationships without turning KnowledgeVault into a credential store or provider authority.

This lane establishes the canonical source contract for:

```text
Financial provider / owner entry
 -> governed account reference
 -> normalized finance snapshot
 -> private Personal KV persistence
 -> optional governed analysis/readback
```

## Privacy and authority invariants

1. Real user financial values belong only in the user's private connected KnowledgeVault or an admitted private runtime; they must never be committed to this public repository.
2. Ordinary KV finance records must not contain passwords, OAuth tokens, refresh tokens, private keys, recovery codes, card PANs, CVVs, full bank-account numbers, routing numbers, or equivalent reusable secrets.
3. Provider/account connection credentials belong behind SKAP Vault or another explicitly admitted credential boundary.
4. A provider/account reference grants no payment, trading, transfer, borrowing, card-spending, or account-management authority.
5. Read access to finance records does not imply transaction execution authority.
6. Imported provider data must preserve source/as-of provenance.
7. Ambiguous provider state or absent canonical KV persistence fails closed.
8. Rewards/yield metadata is descriptive and may change; persisted rates must carry observation timestamps.
9. Locked/collateral balances must remain distinguishable from liquid/available balances.
10. Liabilities must remain distinguishable from assets and cash-equivalents.
11. Historical finance records are user-controlled private data, not repository fixtures.
12. Repository tests may use synthetic values only.

## Implemented source

- `KV_PERSONAL_FINANCE_MIRROR_HANDOFF.md` — canonical lane handoff.
- `schemas/kv-personal-finance-snapshot.schema.json` — normalized finance snapshot contract.
- `vault_template/KnowledgeVault/_Entities/Self/Personal_Finance.json` — empty/private-KV initialization shape with no real values.
- `runtime/personal_finance.py` — deterministic IDs, canonical snapshot hashing, secret-field rejection, execution-authority fail-closed enforcement.
- `tests/test_personal_finance.py` — synthetic-only tests for normalization, deterministic IDs, secret rejection, authority rejection, rewards, and collateral.
- `tools/check_kv_personal_finance.py` — source-presence/static boundary checker.

## Initial normalized model

The first schema slice supports:

- account identity/reference metadata;
- account class/subtype and masked display identifier;
- current / available balance and credit limit;
- liabilities and amount owed;
- transactions and recurring activity;
- reward/yield positions such as USDC APY and card-spend crypto rewards;
- locked/collateral relationships;
- observation timestamp / provider/source metadata;
- user labels and notes without authority effect.

The model intentionally separates:

```text
current balance
available balance
credit limit
amount owed
earning balance
locked/collateral balance
earned reward value
```

so collateral, debt, liquidity, and rewards cannot silently collapse into one value.

## Connected-KV destination

Canonical private destination candidate:

```text
/KnowledgeVault/_Entities/Self/Personal_Finance.json
```

The repository template contains only an empty initialization shape. Real values are installed or updated only through a private owner-authorized KV path.

## Validation state

Implemented-on-branch source exists, but hosted/exact-head validation has not yet been observed.

Required validation before merge:

- schema parse/validation against synthetic finance fixtures;
- `tests/test_personal_finance.py`;
- `tools/check_kv_personal_finance.py`;
- existing Security Baseline;
- existing KV Guardrails;
- existing Release Integrity / repository diagnostics as applicable;
- current-main reconciliation if main advances.

## Completion gates

- finance-specific handoff exists before implementation: SATISFIED;
- schema/source/template/runtime/tests/static checker installed: SATISFIED_ON_BRANCH;
- secret-bearing fields fail closed: IMPLEMENTED / VALIDATION_PENDING;
- real provider credentials absent from ordinary KV: IMPLEMENTED / VALIDATION_PENDING;
- runtime normalizer produces deterministic account identities and snapshot hashes: IMPLEMENTED / VALIDATION_PENDING;
- collateral/locked and available balances remain distinct: IMPLEMENTED / VALIDATION_PENDING;
- transaction execution authority remains false: IMPLEMENTED / VALIDATION_PENDING;
- tests use synthetic values only: SATISFIED_ON_BRANCH;
- connected-KV write/readback: NOT YET PERFORMED;
- automatic/provider import adapter: NOT YET IMPLEMENTED;
- Site / My KV finance projection: NOT YET IMPLEMENTED;
- downstream Publisher / admissibility / stegguardian propagation: NOT YET DUE.

## Remaining source/integration work

1. run deterministic source validation and repair any failures;
2. merge the canonical KV contract only after exact-head validation;
3. install the empty `Personal_Finance.json` template into the connected private KnowledgeVault and restore source-template parity;
4. add an owner-authorized read-only finance-ingress adapter that maps connected finance-provider data into this schema without storing credentials;
5. add My KV / Site finance display and consent controls as a downstream projection, not a competing schema authority;
6. verify readback from the private KV;
7. only then begin writing real owner financial observations into the private KV.

## Current live boundary

Issue #106 and this branch establish the finance-tracking source contract only.

No real financial values have been written to the public repository.
No real financial values have yet been written to the connected KnowledgeVault by this lane.
No provider connector, payment authority, trading authority, transfer authority, borrowing authority, card-spending authority, or credential capability is activated by this source work.
