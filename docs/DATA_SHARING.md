# Data Sharing and Revenue Participation

KnowledgeVault is yours first. Sharing is optional, transparent, and reversible.

This document explains how the optional data-sharing ecosystem works, what you control, and how revenue participation functions.

---

## Core principle: opt-in, not opt-out

- **Default:** nothing is shared
- **Your choice:** you select which categories and metadata to share
- **Your control:** you can change or withdraw at any time
- **Your benefit:** if shared data generates revenue, you may receive compensation

---

## What can be shared

You choose per category. Checkboxes in `_Policy/Data_Sharing_Policy.md` track your choices.

| Category | What it includes | Example value to researchers/advertisers |
|----------|-----------------|------------------------------------------|
| `01_Notes` | Daily notes, events, memories | Life pattern analysis, event trends |
| `02_Research` | Reading, learning, investigations | Interest mapping, knowledge gaps |
| `04_Media` | Photos, videos, audio | Visual trend analysis, location data |
| `05_Projects` | Creative output, work | Innovation patterns, skill trends |
| `_Entities` | People, places, orgs, projects | Relationship networks, location graphs |
| **Metadata only** | Dates, locations, tags, file types | Temporal patterns, geographic trends |

### Hard exclusions (never shareable)

- `03_Records/` — health, finance, legal
- `_Policy/` — your rules and choices
- `_System/` — integrity logs, migration data
- Any file marked `Privacy Level: restricted`

---

## How sharing works

### Step 1: You opt in

In `_Policy/Data_Sharing_Policy.md`, check the categories you are willing to share.

### Step 2: Data is indexed

If you use StegVerse tools, your selected data is structured for matching:
- Entity relationships are mapped
- Temporal patterns are extracted
- Geographic data is normalized
- Content is categorized

### Step 3: Data is aggregated

Your data is combined with data from other users who share matching categories:
- Individual identity is removed
- Patterns emerge from the collective
- Datasets are validated for quality

### Step 4: Datasets are used

Aggregated datasets may be:
- Purchased by companies for market research
- Used by advertisers for trend analysis
- Licensed to content platforms
- Used in academic research
- Published as open data (if you opt into open licensing)

### Step 5: Revenue is shared

If a dataset generates revenue:
- Revenue is calculated at the **dataset level**, not per-user
- Your share is proportional to your contribution
- Payouts are periodic
- You can view estimated earnings through StegVerse tools

---

## What you actually share

### Content sharing

If you share `01_Notes`, the actual text of your notes may be included in aggregated datasets. Personal identifiers are removed, but the content itself contributes to pattern analysis.

### Metadata sharing

If you share "metadata only," your notes' text is never included. Instead:
- File creation dates
- Location tags
- Entity references
- Folder categories
- File types and sizes

These create trend datasets without exposing your private thoughts.

### Media sharing

If you share `04_Media`, your photos/videos may be included in visual datasets. Faces and license plates are automatically blurred by the aggregation process.

---

## Privacy protections

1. **Aggregation before use** — individual data is never sold
2. **Anonymization** — personal identifiers are removed during aggregation
3. **Category separation** — you can share metadata without sharing content
4. **Hard exclusions** — sensitive categories are permanently blocked
5. **Audit trail** — `_Policy/Data_Sharing_Policy.md` records every choice
6. **Withdrawal** — opt-out stops future sharing immediately

---

## Revenue model

### How revenue is generated

- **Research licensing** — aggregated datasets sold to research institutions
- **Advertising insights** — trend data sold to marketing firms
- **Content licensing** — media datasets licensed to platforms
- **Open data sponsorships** — public datasets funded by grants or donors

### How revenue is distributed

- **Dataset-level accounting** — each dataset tracks total revenue
- **Contribution scoring** — your share is based on:
  - Volume of data contributed
  - Uniqueness of your data (rare patterns are more valuable)
  - Quality score (completeness, consistency, accuracy)
- **Periodic payouts** — monthly or quarterly, depending on revenue volume
- **Minimum thresholds** — small amounts accrue until they meet a payout minimum

### What you need to participate

- A valid payout method (set up separately through StegVerse tools)
- Accurate contact information for tax reporting
- Compliance with your jurisdiction's tax laws

**This is not guaranteed income.** Revenue depends on market demand for your data categories. Some users may earn nothing. Others may earn significant amounts if their data fills rare gaps.

---

## Risks and limitations

### Known risks

- **Re-identification** — while aggregation protects privacy, sophisticated analysis might infer individual contributions from rare patterns
- **Data permanence** — once aggregated into a dataset, your data may persist even after you opt out
- **Market volatility** — revenue depends on demand; categories valuable today may be worthless tomorrow
- **Regulatory changes** — data protection laws may restrict sharing in your jurisdiction

### Mitigations

- Share metadata-only for lower risk
- Avoid sharing rare or unique patterns
- Review `_Policy/Data_Sharing_Policy.md` regularly
- Monitor StegVerse updates on regulatory compliance

---

## How to start

1. Read `_Policy/Data_Sharing_Policy.md` in your vault
2. Check the categories you are willing to share
3. Record your consent in the policy file
4. If using StegVerse tools, run the opt-in workflow
5. Monitor your sharing status and estimated earnings

---

## How to stop

1. Uncheck all categories in `_Policy/Data_Sharing_Policy.md`
2. Record your withdrawal date
3. Future sharing stops immediately
4. Already-aggregated data remains in existing datasets per retention policy

---

## Questions?

- See `SAFETY.md` for threat model guidance
- See `docs/PRESENCE_BASED_SHARING.md` for sharing memories with people you know
- See `docs/MULTI_DEVICE_USAGE.md` for managing vaults across devices

---

Last updated: 2026-04-24
