# AI Review Prompt Behavior — Specification

This document defines how and when AI systems may prompt the user to review, update, or maintain KnowledgeVault content.

The goal is to support continuity **without becoming intrusive, repetitive, or overwhelming**.

AI may suggest reviews. Humans decide when to act.

---

## 1. Purpose

The AI Review Prompt system exists to:

- Surface meaningful gaps or stale areas
- Encourage gentle maintenance of active life areas
- Help keep the vault current over long periods
- Avoid notification fatigue

Prompts are **invitations**, not reminders or alerts.

---

## 2. Where Prompts May Appear

AI review prompts may appear in:

- `_LightMode/Health.md` (or similar dashboard)
- `_Index/Reviews/`
- Periodic review summaries generated in `_AI/Review_Summaries/`

AI must not use external notification systems without explicit user consent.

---

## 3. When AI May Suggest a Review

AI may suggest review when:

### Projects
- An **active** project has no updates for 90+ days
- A project marked active shows no recent events or notes

### Timeline
- A year has many memories but no timeline summary
- A major life transition is detected (move, job change, milestone event)

### People
- A person marked “seen often” has no recent linked memories
- A key relationship file has not been updated for 12+ months

### Places
- A frequently visited place has new memories but no recent place notes

### Inbox
- `00_Inbox/` contains items older than a user-defined period (e.g., 30 days)

---

## 4. Frequency Rules

AI should:

- Combine multiple prompts into a **single periodic summary**
- Avoid prompting more than once per week by default
- Reduce frequency if prompts are ignored repeatedly

The system should feel helpful, not demanding.

---

## 5. Tone & Style

Prompts must be:

- Gentle
- Optional
- Non-urgent
- Framed as supportive suggestions

Example:

> “It’s been a few months since your last update to **Health Recovery Project** — want to add a quick note?”

Not:

> “You haven’t updated your project. Please do so.”

---

## 6. User Control

Users must be able to:

- Dismiss a prompt permanently
- Snooze a prompt
- Turn off review prompts entirely
- Adjust frequency and sensitivity

AI must respect user settings and past dismissals.

---

## 7. Privacy Limits

AI must never prompt about:

- Files marked `Privacy Level: restricted`
- Sensitive medical or financial data unless the user explicitly enabled related reviews

Prompts must focus on structure and continuity, not personal judgment.

---

## 8. Learning Behavior

AI should:

- Learn which types of prompts are consistently ignored
- Reduce similar future prompts
- Increase relevance over time rather than frequency

The goal is **fewer, higher-quality prompts**.

---

## 9. Output Format for Review Summaries

Periodic summaries should be written to:

```
_AI/Review_Summaries/
```

Filename format:

```
YYYY-MM-DD_review_summary.md
```

---

## 10. Portability Principle

This review system must rely only on:

- Markdown files
- Folder structure
- Human-readable prompts

No app-specific notification system is required.

---

## 11. Final Rule

If uncertainty exists about whether a prompt is appropriate:

**The AI should remain silent.**
