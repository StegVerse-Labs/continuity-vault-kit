# Emoji Relationship Grammar (StegDB Rule)

This project uses **simple, universal Apple-keyboard emojis** as *visual context cues*.

## 👤 Relationship Shorthand

Use these sequences to describe relationship directionality:

- 👤➡️👤  one-way connection (A → B)
- 👤⬅️👤  one-way connection (B → A)
- 👤↔️👤  two-way connection (mutual)

Group variants:

- 👤➡️👥  person → group
- 👤⬅️👥  group → person
- 👤↔️👥  person ↔ group

## 🧑‍🧑‍🧒 / 🚻 Group Context

Optional group markers that can prefix a line:

- 🧑‍🧑‍🧒 family context
- 🚻 mixed/other group context (non-family)

Example:

- 🧑‍🧑‍🧒 👤↔️👤 — Sibling relationship
- 🚻 👤➡️👥 — Member of an org / community

## ➡️ Arrow Character Rule

Some editors insert non-standard arrow characters, including Unicode code points U+2794, U+21D2, and U+27F6. Those are **not reliably typed** and can differ across fonts and editors.

**Prefer:**
- Relationship emoji sequences (👤➡️👤 etc), or
- Plain ASCII arrows: `-->` or `->`

## Enforcement

- CI runs a lint that **warns** when disallowed arrow characters are detected.
- To make CI **fail** on warnings, set repository variable:
  - `STEGDB_EMOJI_LINT_STRICT=1`
