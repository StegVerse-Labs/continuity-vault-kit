# ZRE (Zodiac Reflection Engine) Overview

ZRE provides symbolic reflection prompts based on user-controlled astrology-style profiles.

It operates in three modes:

## ZRE Lite
Uses only a zodiac sign (e.g., ♎️ Libra) for general reflection prompts.
No birth date/time/location required at runtime.

## ZRE Enhanced
Uses a translated profile (`_Entities/Self/ZRE_Profile.json`) containing derived symbolic values
(e.g., Sun/Moon/Rising, element/modality balances).
No raw birth date/time/location is required once the translated profile exists.

## ZRE Recompute (Rare)
Requires explicit user permission to access raw birth data in order to regenerate the translated profile.
This is never automatic.

---

🔒 Layer: Vault Template | KV
