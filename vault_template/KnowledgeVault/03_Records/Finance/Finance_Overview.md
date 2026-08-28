# Personal Finance Overview

Status: USER_CONTROLLED_PRIVATE_KV_DOCUMENT  
Scope: Personal KnowledgeVault finance continuity  
Execution authority: NONE

This is the top-level human-readable finance document for the owner's KnowledgeVault.

It is intended to summarize private finance state persisted elsewhere in the Personal KV finance model and related finance directory files. It does not store provider credentials and does not grant payment, trading, transfer, borrowing, tax-filing, or account-management authority.

## Accounts

Summarize active financial accounts and their purpose.

Suggested fields:

- institution / provider display name;
- masked account identifier;
- account type;
- current balance;
- available balance;
- credit limit where applicable;
- liability balance where applicable;
- observation date;
- notes about account role.

## Spending habits and analysis

Summarize observed spending patterns.

Suggested analysis:

- monthly spending trend;
- spending by category;
- recurring bills and subscriptions;
- large or unusual expenses;
- discretionary vs required spending;
- cash-flow observations;
- credit-card utilization and payoff behavior.

## Savings analysis

Summarize liquid savings and reserve posture.

Suggested analysis:

- emergency reserve;
- checking/savings cash levels;
- savings rate;
- short-term goals;
- yield earned on cash/cash-equivalent positions;
- locked or collateralized funds separately from available savings.

## Retirement analysis

Summarize retirement-oriented assets and progress.

Suggested analysis:

- retirement accounts;
- contribution rate;
- employer match where applicable;
- current allocation;
- concentration observations;
- target-date or goal assumptions;
- projected gap or surplus using explicitly recorded assumptions.

## Income tax analysis

### Federal

Summarize federal income-tax observations and planning inputs.

Suggested analysis:

- year-to-date taxable income inputs;
- withholding;
- estimated payments;
- realized gains/losses where available;
- deductible or credit-relevant items tracked by the owner;
- projected liability using explicitly recorded assumptions.

### State

Summarize state income-tax observations using the owner's applicable state jurisdiction and assumptions.

Suggested analysis:

- state taxable-income inputs;
- withholding / estimated payments;
- state-specific deductions or credits recorded by the owner;
- projected state liability.

Tax sections are analytical continuity records, not filing authority or a substitute for official tax forms or qualified advice.

## Rewards, yield, and collateral

Track rewards and yield without collapsing them into liquid cash.

Examples:

- cash/USDC yield rate and earned rewards;
- card-spend BTC or other rewards;
- locked collateral;
- secured credit relationships;
- observation timestamps because rates and program terms may change.

## Analysis provenance

Every generated or imported analysis should identify:

- data sources;
- observation / coverage period;
- last refresh time;
- assumptions;
- incomplete or unavailable data;
- whether the section is owner-entered, provider-imported, or derived.

## Related canonical machine-readable state

The normalized machine-readable finance snapshot is governed by:

- `_Entities/Self/Personal_Finance.json`
- `schemas/kv-personal-finance-snapshot.schema.json` in the source kit

Private values belong in the connected KnowledgeVault, not the public source repository.
