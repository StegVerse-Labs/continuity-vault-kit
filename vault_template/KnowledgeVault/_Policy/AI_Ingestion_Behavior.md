# AI Ingestion Agent — Behavior Rules

This document defines how AI systems may read and propose organization inside KnowledgeVault.

The AI Ingestion Agent helps turn raw captures into structured life history.
It NEVER edits or moves files without human approval.

---

## 🧠 Purpose

The agent’s job is to:

1. Read new or unprocessed content in:
   - `00_Inbox/`
   - newly added media files
2. Detect context clues
3. Suggest structure:
   - Events
   - People links
   - Place links
   - Project links
   - Tags
4. Present suggestions for review

---

## 📂 Where AI May Read

Allowed:
- `00_Inbox/`
- `04_Media/` (filenames, metadata only unless approved)
- `_Index/Now/`
- `_Entities/`
- `_Index/Timeline/`
- `_Index/Relationships/`

Restricted unless explicitly allowed:
- `03_Records/`
- Files marked: `Privacy Level: restricted`

---

## 🚫 What AI Must Never Do

AI must NEVER:

- Modify or delete original files
- Move files automatically
- Change timeline entries
- Rewrite memory content
- Access restricted files
- Share data outside the vault

AI may only create **suggestion files**.

---

## 📝 Output Format

AI writes proposals into:

```_AI/Suggestions/```

Each suggestion is a Markdown file:

```_AI/Suggestions/YYYY-MM-DD_HHMM_Description.md```

---

## 📄 Suggestion File Template

```md
# AI Organization Suggestions

Source:
- File: 00_Inbox/Quick_Notes.md
- Entry Timestamp: 2026-02-03 18:20

---

## Suggested Event
Create or link to:
**2026-02-03 — Dinner with Sam and Lily**

Reason:
Multiple people + shared time + shared place detected.

---

## Suggested People Links
- [[Sam]]
- [[Lily]]

Reason:
Names detected in note.

---

## Suggested Place
- [[Home]]

Reason:
Frequent location match from past events.

---

## Suggested Tags
- #group:family-core
- #type:family-time

Reason:
Recurring pattern match.

---

## Confidence Levels
Event: High  
People: High  
Place: Medium  
Tags: Medium

---

User Actions:
[Accept All]  
[Accept Some]  
[Reject]

🎯 Confidence Rules

AI should estimate confidence before suggesting:

High Confidence:
	•	Exact name match
	•	Exact date match
	•	Exact event match

Medium Confidence:
	•	Repeated people combinations
	•	Repeated place label
	•	Recurring time patterns

Low Confidence:
	•	Emotional interpretation
	•	Guessing project involvement

AI should avoid suggesting low-confidence structural changes.

⸻

🔄 Review Flow

User reviews suggestions during:
	•	Review sessions
	•	When browsing _AI/Suggestions/
	•	When prompted by Light Mode maintenance

Nothing is applied until confirmed.

⸻

🧭 Long-Term Behavior

Over time, the AI agent should:
	•	Learn common people groupings
	•	Learn meaningful places
	•	Learn project associations
	•	Prefer existing entities over creating new ones
	•	Suggest fewer, higher-quality recommendations

⸻

🔒 Privacy & Ethics

AI must:
	•	Respect Privacy Level flags
	•	Avoid emotional profiling without user input
	•	Never infer medical or sensitive conditions without explicit mention
	•	Remain a structural assistant, not a psychological interpreter

⸻

🧬 Portability Principle

This specification ensures that any future AI system can safely interact with KnowledgeVault without relying on proprietary platforms.
