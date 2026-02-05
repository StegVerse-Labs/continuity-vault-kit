# ZRE (Zodiac Reflection Engine) Overview

ZRE provides symbolic reflection prompts based on user-controlled astrology-style profiles.

It operates in three modes:

## ZRE Lite
Uses only a zodiac sign (e.g., Libra) for general daily reflection prompts.

## ZRE Enhanced
Uses a translated profile (`_Entities/Self/ZRE_Profile.json`) containing derived symbolic traits.
No birth date, time, or location is required once the profile exists.

## ZRE Recompute
Rare mode. Requires explicit permission to access raw birth data to regenerate the translated profile.
