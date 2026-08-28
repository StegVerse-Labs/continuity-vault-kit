# KV Coinbase Finance Ingress Mirror Handoff

Status: SOURCE_LANE_OPEN / IMPLEMENTATION_IN_PROGRESS  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#111`  
Branch: `feature/kv-coinbase-finance-ingress-111`  
Updated: 2026-08-28  
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

The first adapter may represent provider-returned:

- crypto/cash-equivalent balances;
- available vs locked balances;
- secured-card collateral relationships;
- reward/yield observations with as-of timestamps;
- read-only transaction history;
- masked account/product references;
- source/session/provenance evidence.

The adapter must preserve provider-native distinctions rather than flattening locked collateral, available cash, reward value, and liabilities into one balance.

## Existing upstream dependencies

- `KV_PERSONAL_FINANCE_MIRROR_HANDOFF.md`
- `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md`
- `runtime/personal_finance.py`
- `runtime/direct_source_ingress.py`
- TVC canonical Coinbase SKAP/InTr handoff and provider-session evidence.

## Planned source

- `KV_COINBASE_FINANCE_INGRESS_MIRROR_HANDOFF.md`
- `runtime/coinbase_finance_ingress.py`
- `tests/test_coinbase_finance_ingress.py`
- `tools/check_kv_coinbase_finance_ingress.py`
- `.github/workflows/kv-coinbase-finance-ingress.yml`

## Completion gates

- finance secret-field guard false-positive repair validated;
- synthetic Coinbase provider result normalizes deterministically;
- direct-source/session verification required;
- secret-bearing source payload rejected;
- locked collateral remains separate from liquid balance;
- execution authority remains false;
- exact-head hosted validation passes;
- PR merged;
- live SKAP provider session: SEPARATE RUNTIME GATE;
- real private-KV write/readback: SEPARATE RUNTIME GATE.

## Current boundary

Source implementation only. No live Coinbase login, credential resolution, provider operation, or real finance observation is performed by this repository lane.
