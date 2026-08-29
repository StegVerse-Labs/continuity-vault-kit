# KV Personal Finance Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / LIVE_PRIVATE_KV_ACTIVATION_PENDING  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#106`  
Merged PR: `#107`  
Validated head: `5b373708c772cacc538bbf09983e449881040251`  
Updated: 2026-08-29

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

## Direct-source ingestion dependency

Canonical live population must conform to `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md` (issue #108).

For finance, assets, and liabilities, canonical imports should originate from the direct institution/provider source using an owner-authorized provider session whose reusable credential material is resolved through SKAP Vault. An intermediary may be admitted only as explicit transport/convenience and may not silently replace the underlying source in provenance.

Default access is READ_ONLY / minimum-necessary. Provider login/session verification, source/account binding, normalization, admission, and KV persistence receipts are required before imported state is treated as current direct-source data.

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

## Validation and merge state

Source implementation merged through PR #107 from exact head `5b373708c772cacc538bbf09983e449881040251`.

GitHub Actions reports six completed validation runs for that exact head. The observed workflow set includes `Automation candidate implementation - Validation Only` and `Security Baseline`; no failed conclusion was observed in the exact-head run set before merge.

Repository source completion is therefore `MERGED_VALIDATED`. This does not satisfy the separate connected-private-KV or provider-session activation gates.

## Completion gates

- finance-specific handoff exists before implementation: SATISFIED;
- schema/source/template/runtime/tests/static checker installed: SATISFIED / MERGED;
- secret-bearing fields fail closed: VALIDATED;
- real provider credentials absent from ordinary KV: VALIDATED;
- runtime normalizer produces deterministic account identities and snapshot hashes: VALIDATED;
- collateral/locked and available balances remain distinct: VALIDATED;
- transaction execution authority remains false: VALIDATED;
- tests use synthetic values only: VALIDATED;
- exact-head hosted validation: PASSED;
- PR merged: SATISFIED via #107;
- connected-KV write/readback: NOT YET PROVEN FOR REAL FINANCE STATE;
- direct-source SKAP-backed provider import adapter: source dependency implemented separately; live activation NOT YET PROVEN;
- Site / My KV finance projection: NOT YET VERIFIED AS A LIVE USER SURFACE;
- downstream Publisher / admissibility / stegguardian propagation: DUE ONLY AFTER AN ADMITTED RELEASE TRANSITION.

## Remaining machine/runtime work

1. ensure the current connected private KnowledgeVault contains the current empty `Personal_Finance.json` template and retain parity/readback evidence if not already present;
2. establish an owner-authorized direct-source provider session through the existing TVC/SKAP boundary;
3. normalize a real read-only provider result through the canonical finance adapter path;
4. persist the resulting private finance snapshot only inside the connected private KV;
5. verify private-KV readback and retain non-secret provenance/receipt evidence;
6. project the canonical finance state into My KV / Site with consent controls without creating a competing schema authority;
7. after the next admitted release, verify any required propagation to Site, Publisher, admissibility-wiki, and stegguardian-wiki.

## Current live boundary

Issue #106 source implementation is complete and merged. The issue may be closed as a source-contract task without claiming live finance activation.

No real financial values are committed to the public repository.
No provider connector, payment authority, trading authority, transfer authority, borrowing authority, card-spending authority, or credential capability is activated by this source work.
Live provider-session, private-KV persistence/readback, and user-surface activation remain separate gates.
