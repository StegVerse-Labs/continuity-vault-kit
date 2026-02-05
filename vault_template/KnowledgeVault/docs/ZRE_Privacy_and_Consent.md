# ZRE Privacy & Consent Model

ZRE separates raw identity data from symbolic reflection data.

## Raw Birth Data (Private)
Recommended location:
- `_Private/ZRE/Birth_Data.md`

Rules:
- Never accessed automatically
- Only accessed in **Recompute** mode with explicit permission

## Translated Profile (ZRE-Usable)
Recommended location:
- `_Entities/Self/ZRE_Profile.json`

Rules:
- Contains only derived symbolic values (no DOB/time/location)
- Safe to use for Enhanced reflections
- User may choose whether it is shareable with AI

## Consent File (Controls Everything)
ZRE reads:
- `_AI/Consent/consent.json`

This file determines:
- whether ZRE is enabled
- which mode runs (lite/enhanced/off)
- whether translated profile may be used
- frequency (daily/weekly/seasonal)
