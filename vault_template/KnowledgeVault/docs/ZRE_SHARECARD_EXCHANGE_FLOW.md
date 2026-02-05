# ZRE ShareCard Exchange Flow (Two Vaults)

This document describes a simple, human-friendly way to exchange compatibility inputs
without sharing raw birth data.

## Files
Each person produces a share card:
- `_AI/Share/ZRE_ShareCard.json`

## Flow (Manual, Simple)
1. Person A exports their ShareCard file.
2. Person A sends it to Person B (AirDrop, iMessage attachment, email, etc.).
3. Person B saves it to:
   - `/_AI/Share/Incoming/PersonA_ZRE_ShareCard.json`
4. Person B runs a compatibility reflection (manually or via an AI tool).
5. Output is written to:
   - `/_AI/Reflections/Compatibility/YYYY-MM-DD_A+B.md`

## Minimal Compatibility Output Structure
- Both signs (and optional moon/rising)
- Shared themes (if provided)
- 5–10 reflection prompts
- Reminder disclaimer

## Privacy Notes
- ShareCard contains no DOB/time/location.
- Users should only share what they are comfortable with.
- You may optionally omit moon/rising for additional privacy.
