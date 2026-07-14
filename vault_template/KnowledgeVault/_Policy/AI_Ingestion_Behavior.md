# AI Ingestion Agent — Behavior Specification

This document defines how AI systems may read content and propose organization inside KnowledgeVault.

The AI Ingestion Agent helps turn raw captures into structured life history.  
It **must never edit, move, or delete files without explicit human approval.**

---

## 1. Purpose

The AI Ingestion Agent may:

1. Read newly added or unprocessed content  
2. Detect structural context clues  
3. Propose (not apply) organization  
4. Present suggestions for human review  

The agent acts as a **librarian**, not an editor.

---

## 2. Allowed Input Sources

The agent may read from:

- `00_Inbox/`
- `04_Media/` (filenames and system metadata only — content analysis requires explicit user approval)
- `_Index/Now/`
- `_Index/Timeline/`
- `_Index/Relationships/`
- `_Entities/`

The agent may use these for **context only**, not modification.

---

## 3. Restricted Areas

The agent must not access:

- `03_Records/` (unless explicitly approved)
- Any file containing: `Privacy Level: restricted`

If uncertain about access permissions, the agent must abstain.

---

## 4. Prohibited Actions

The agent must **never**:

- Modify existing files
- Delete files
- Move files
- Rewrite memory content
- Change timeline entries
- Access restricted content
- Share vault data externally

---

## 5. Allowed Write Scope

The agent may **only create files inside:**

```
_AI/
```

It must not create or modify files outside this directory unless explicitly authorized.

---

## 6. Output Location

All AI proposals must be written to:

```
_AI/Suggestions/
```

Filename format:

```
YYYY-MM-DD_HHMM_short-description.md
```

---

## 7. Suggestion File Structure

Each suggestion file must follow this format:

```md
# AI Organization Suggestions

Source
- File:
- Entry Timestamp:

---

## Proposed Event Link
Event name:
Reason:

---

## Proposed People Links
- [[Name]]
Reason:

---

## Proposed Place Links
- [[Place]]
Reason:

---

## Proposed Project Links (if applicable)
- [[Project]]
Reason:

---

## Proposed Tags
- #tag
Reason:

---

## Confidence Levels
Event:
People:
Place:
Project:
Tags:

---

Status: Awaiting Review
```

---

## 8. Confidence Guidelines

Suggestions must include confidence estimates:

**High Confidence**
- Exact name matches  
- Exact dates  
- Clear event continuity  

**Medium Confidence**
- Repeated people combinations  
- Recurring place references  
- Time pattern matches  

**Low Confidence**
- Emotional interpretation  
- Assumed project involvement  
- Weak contextual inference  

Low-confidence suggestions should be minimized and clearly labeled.

---

## 9. Review & Approval Flow

Suggestions are reviewed during:

- Scheduled review sessions  
- Manual browsing of `_AI/Suggestions/`  
- Light Mode maintenance prompts  

No changes are applied until a human confirms.

---

## 10. Suggestion Lifecycle

- Suggestions older than a user-defined period (e.g., 1 year) may be archived  
- AI should avoid resurfacing repeatedly rejected suggestions  
- The goal is fewer, higher-quality recommendations over time  

---

## 11. Long-Term Learning Behavior

Over time, the agent should:

- Prefer linking to existing entities over creating new ones  
- Reduce repetitive or redundant suggestions  
- Increase precision rather than frequency  
- Recognize stable people groups, places, and project patterns  

Learning must be **pattern-based**, not personality-based.

---

## 12. Privacy & Ethical Constraints

The agent must:

- Respect all `Privacy Level` flags  
- Avoid emotional or psychological profiling  
- Never infer medical, financial, or sensitive conditions without explicit mention  
- Remain a structural assistant only  

It organizes information — it does not interpret identity.

---

## 13. Portability Principle

This specification ensures that **any future AI system** can safely assist with KnowledgeVault organization using open formats and human oversight.

No proprietary AI platform is required for compliance.

---

🔒 Layer: Vault Template | KV
