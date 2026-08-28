# KV Personal Finance Mirror Handoff

Status: SOURCE_LANE_OPEN / IMPLEMENTATION_IN_PROGRESS  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#106`  
Branch: `feature/kv-personal-finance-106`  
Updated: 2026-08-28

## Purpose

Add a bounded Personal KnowledgeVault finance-tracking model that can represent accounts, balances, liabilities, transactions, recurring activity, rewards/yield, and collateral relationships without turning KnowledgeVault into a credential store or provider authority.

This lane begins the canonical source contract for:

```text
Financial provider / owner entry
 -> governed account reference
 -> normalized finance snapshot
 -> private Personal KV persistence
 -> optional governed analysis/readback
```

## Privacy and authority invariants

1. Real user financial values belong only in the user's private connected KnowledgeVault or an admitted private runtime; they must never be committed to this public repository.
2. Ordinary KV finance records must not contain passwords, OAuth tokens, refresh tokens, private keys, recovery codes, card PANs, CVVs, full bank-account numbers, or equivalent reusable secrets.
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

## Initial normalized model

The first schema slice supports:

- account identity/reference metadata;
- account class/subtype and masked display identifier;
- current / available balance and credit limit;
- liabilities and amount owed;
- transactions and recurring activity;
- reward/yield positions such as USDC APY and card-spend BTC rewards;
- locked/collateral relationships;
- observation timestamp / provider/source metadata;
- user labels and notes without authority effect.

## Planned source files

- `KV_PERSONAL_FINANCE_MIRROR_HANDOFF.md`
- `schemas/kv-personal-finance-snapshot.schema.json`
- `vault_template/KnowledgeVault/_Entities/Self/Personal_Finance.json`
- `runtime/personal_finance.py`
- `tests/test_personal_finance.py`
- `tools/check_kv_personal_finance.py`
- `CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`
- optional downstream Site projection after canonical KV contract stabilizes

## Connected-KV destination

Canonical private destination candidate:

```text
/KnowledgeVault/_Entities/Self/Personal_Finance.json
```

The repository template contains only an empty/synthetic initialization shape. Real values are installed or updated only through a private owner-authorized KV path.

## Completion gates

- finance-specific handoff exists before implementation;
- schema validates synthetic account/balance/liability/reward/collateral examples;
- secret-bearing fields fail closed;
- real provider credentials are absent from ordinary KV;
- runtime normalizer produces deterministic account identities and snapshot hashes;
- collateral/locked and available balances remain distinct;
- transaction execution authority remains false;
- tests use synthetic values only;
- connected-KV write/readback is separately verified before claiming live tracking;
- downstream Site / Publisher / admissibility / stegguardian propagation is checked when release-worthy.

## Current live boundary

Issue #106 and this source lane establish the finance-tracking contract only.

No real financial values have been written to the public repository.
No provider connector, payment authority, trading authority, transfer authority, borrowing authority, or credential capability is activated by this source work.
