# ZRE Daily Reflection Generator — Specification

This spec defines how a tool or AI agent generates reflection prompts in a predictable, portable way.

## Inputs
ZRE may read (depending on consent):
- `/_AI/Consent/consent.json`
- `/_Entities/Self/ZRE_Profile.json` (Enhanced mode only)
- Optional user-chosen themes from `/_AI/ZRE/user_themes.md` (if present)

## Outputs
ZRE writes a single file per run:
- `/_AI/Reflections/YYYY-MM-DD_ZRE.md`

## Output Template
Each reflection file must contain:
- Date (ISO)
- Mode: Lite | Enhanced
- Sign(s): zodiac emoji and/or textual name
- Symbolic Theme (1 line)
- 3–6 Reflection Prompts (bullets)
- Reminder disclaimer (symbolic only)

## Frequency
Controlled by consent.json:
- `daily` → once per day
- `weekly` → once per week (choose a stable day e.g., Monday)
- `seasonal` → quarterly (Mar/Jun/Sep/Dec 1st)

## Idempotency
If today’s reflection file already exists, the generator should not overwrite it by default.
If overwrite is desired, it should create a new file with suffix:
- `YYYY-MM-DD_ZRE_v2.md`

## Safety Guardrails
The generator must avoid:
- predictions
- medical/legal/financial advice
- deterministic personality claims
