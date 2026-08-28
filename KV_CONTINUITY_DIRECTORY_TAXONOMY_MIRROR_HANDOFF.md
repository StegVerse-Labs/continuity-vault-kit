# KV Continuity Directory Taxonomy Mirror Handoff

Status: SOURCE_IMPLEMENTED_ON_BRANCH / VALIDATION_PENDING  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Branch: `feature/kv-personal-finance-106`  
Updated: 2026-08-28  
Authority effect: NONE  
Activation effect: false

## Purpose

Add human-navigable continuity-domain directories to the Personal KnowledgeVault so a user-facing My KV surface can link directly to the places where major continuity classes are stored.

This is a storage/navigation taxonomy layer. It does not replace canonical schemas, provider adapters, admission policy, or credential boundaries.

## Initial directory map

```text
KnowledgeVault/
  02_Research/
  03_Records/
    Assets/
      README.md
    Liabilities/
      README.md
    Email/
      README.md
    Finance/
      Finance_Overview.md
      Accounts/
      Spending/
      Savings/
      Retirement/
      Taxes/
  04_Media/
    Pictures/
    Music/
  05_Projects/
  06_Archive/
  _Entities/
    Self/
      Personal_Contact_Profile.json
      Personal_Finance.json
```

## Navigation semantics

- human-facing directory cards may link to these canonical paths;
- machine-readable profile/state files may remain under `_Entities/Self`;
- domain directories hold human-readable continuity documents, exports, summaries, and admitted records;
- a directory link does not imply that every file type is publicly browser-readable;
- Site directory browsing must use a canonical private KV bridge and fail closed when absent.

## Assets and liabilities boundaries

`03_Records/Assets` is the human-readable continuity directory for owned resources such as property, investments, cash-equivalents, business interests, valuables, and other owner-controlled assets.

`03_Records/Liabilities` is the human-readable continuity directory for obligations such as credit cards, auto loans, mortgages, student loans, personal loans, taxes owed, and other debts.

These directories are intentionally separate from `03_Records/Finance`: Finance is the analytical overview and planning layer; Assets and Liabilities are first-class continuity domains that may also be referenced by Finance analysis.

## Finance overview contract

`03_Records/Finance/Finance_Overview.md` is the top-level human-readable finance index.

Its canonical sections are:

1. Accounts
2. Spending habits and analysis
3. Savings analysis
4. Retirement analysis
5. Federal income tax analysis
6. State income tax analysis
7. Rewards, yield, and collateral
8. Analysis provenance

The document summarizes private finance state; machine-readable normalized state remains in `_Entities/Self/Personal_Finance.json`.

## Email boundary

`03_Records/Email` is a governed persistence destination only for content admitted by the canonical email-ingress pipeline. Provider credentials never belong there.

## Media boundary

`04_Media/Pictures` and `04_Media/Music` are continuity-domain directories under the existing media root. Binary/media storage and metadata remain subject to KnowledgeVault media policy.

## Current files

- `vault_template/KnowledgeVault/03_Records/Assets/README.md`
- `vault_template/KnowledgeVault/03_Records/Liabilities/README.md`
- `vault_template/KnowledgeVault/03_Records/Email/README.md`
- `vault_template/KnowledgeVault/03_Records/Finance/Finance_Overview.md`
- `vault_template/KnowledgeVault/03_Records/Finance/Accounts/README.md`
- `vault_template/KnowledgeVault/03_Records/Finance/Spending/README.md`
- `vault_template/KnowledgeVault/03_Records/Finance/Savings/README.md`
- `vault_template/KnowledgeVault/03_Records/Finance/Retirement/README.md`
- `vault_template/KnowledgeVault/03_Records/Finance/Taxes/README.md`
- `vault_template/KnowledgeVault/04_Media/Pictures/README.md`
- `vault_template/KnowledgeVault/04_Media/Music/README.md`

## Remaining gates

- source validation;
- finance schema/runtime validation;
- current-tree parity census update;
- merge;
- private connected-KV installation/parity restoration;
- Site directory landing readback proof.

No live private user data is present in these public source templates.
