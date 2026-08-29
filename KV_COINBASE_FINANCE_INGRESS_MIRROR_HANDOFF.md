# KV Coinbase Finance Ingress Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / LIVE_PROVIDER_AND_PRIVATE_KV_PROOF_PENDING  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#111`  
Merged PR: `#112`  
Validated head: `2c1dc52fe6cc9123dbbfeb752eff8342da31a78d`  
Updated: 2026-08-29  
Authority effect: NONE  
Activation effect: false

## Purpose

Implement the first finance-specific direct-source normalization adapter using Coinbase as the source, while reusing the existing TVC + SKAP/InTr Coinbase session path rather than creating a new credential architecture.

Canonical flow:

```text
existing TVC/SKAP Coinbase session
 -> non-secret authenticated Coinbase read result
 -> Coinbase finance adapter
 -> canonical Personal Finance snapshot
 -> private KV persistence
 -> readback
```

## Credential and authority boundary

1. This adapter does not log in to Coinbase.
2. This adapter does not accept passwords, API keys, OAuth tokens, private keys, recovery material, or provider secrets.
3. Provider authentication/session establishment remains owned by the existing TVC Coinbase SKAP/InTr lane.
4. The adapter requires explicit non-secret proof that the direct source and provider session were verified.
5. Access is read-only and minimum-necessary.
6. No trading, payment, transfer, borrowing, card-spending, staking-action, withdrawal, or account-management authority is created.
7. Real values belong only in the connected private KV or an admitted private runtime.
8. Repository fixtures remain synthetic.

## Normalized source coverage

The first adapter represents provider-returned:

- crypto/cash-equivalent balances;
- available vs locked balances;
- secured-card collateral relationships;
- reward/yield observations with as-of timestamps;
- read-only transaction history;
- masked account/product references;
- source/session/provenance evidence.

The adapter preserves provider-native distinctions rather than flattening locked collateral, available cash, reward value, and liabilities into one balance.

## Upstream dependencies

- `KV_PERSONAL_FINANCE_MIRROR_HANDOFF.md`
- `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md`
- `runtime/personal_finance.py`
- `runtime/direct_source_ingress.py`
- TVC canonical Coinbase SKAP/InTr handoff and provider-session evidence.

## Implemented source

- `KV_COINBASE_FINANCE_INGRESS_MIRROR_HANDOFF.md`
- `runtime/coinbase_finance_ingress.py`
- `tests/test_coinbase_finance_ingress.py`
- `tools/check_kv_coinbase_finance_ingress.py`
- `.github/workflows/kv-coinbase-finance-ingress.yml`

## Validation and merge state

Source implementation merged through PR #112 from exact head `2c1dc52fe6cc9123dbbfeb752eff8342da31a78d`.

GitHub Actions reports seven completed validation runs for that exact head. The observed run set includes `Automation candidate implementation - Validation Only` with conclusion `success`; no failed conclusion was observed in the exact-head run set before merge.

Repository source completion is therefore `MERGED_VALIDATED`. This does not authenticate to Coinbase and does not prove private-KV persistence/readback.

## Completion gates

- finance secret-field guard false-positive repair: VALIDATED / MERGED;
- synthetic Coinbase provider result normalizes deterministically: VALIDATED / MERGED;
- direct-source/session verification required: VALIDATED / MERGED;
- secret-bearing source payload rejected: VALIDATED / MERGED;
- locked collateral remains separate from liquid balance: VALIDATED / MERGED;
- execution authority remains false: VALIDATED / MERGED;
- exact-head hosted validation: PASSED;
- PR merged: SATISFIED via #112;
- live SKAP provider session: SEPARATE RUNTIME GATE / NOT YET PROVEN;
- real private-KV write/readback: SEPARATE RUNTIME GATE / NOT YET PROVEN.

## Remaining machine/runtime work

1. establish the real Coinbase provider session through the existing TVC/SKAP/InTr authority path;
2. retain non-secret proof that provider/source/session verification is current and read-only;
3. feed the authenticated provider result through `runtime/coinbase_finance_ingress.py` without exposing reusable credentials to the adapter;
4. persist the normalized result only into the private connected KnowledgeVault;
5. verify readback against the canonical Personal Finance schema and retain non-secret provenance/receipt evidence;
6. keep all trade, payment, transfer, withdrawal, borrowing, staking-action, and account-management authority outside this read-only lane;
7. propagate only source/release facts to Site, Publisher, admissibility-wiki, and stegguardian-wiki after an admitted release transition.

## Current boundary

Issue #111 repository source implementation is complete and merged and may be closed as a source-adapter task.

No live Coinbase login, credential resolution, provider operation, or real finance observation is performed by this repository lane.
Live SKAP provider-session evidence and authentic private-KV write/readback remain the next activation gates.
