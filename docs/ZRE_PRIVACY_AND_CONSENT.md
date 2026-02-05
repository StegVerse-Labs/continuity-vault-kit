# ZRE Privacy & Consent Model

ZRE separates raw identity data from symbolic reflection data.

## Raw Birth Data
Stored in `_Private/ZRE/Birth_Data.md`  
Never accessed automatically.

## Translated Profile
Stored in `_Entities/Self/ZRE_Profile.json`  
Contains only derived symbolic values.

## Consent File
`_AI/Consent/consent.json` determines:
- whether ZRE runs
- which mode is active
- whether translated profile may be used
