# AI Suggestion Approval Mechanism — Specification

This document defines how human-approved AI suggestions are safely applied inside KnowledgeVault.

It ensures that structure can evolve **without risking data loss, corruption, or silent modification**.

AI proposes. Humans approve. The system updates safely and transparently.

---

## 1. Purpose

The Suggestion Approval Mechanism exists to:

- Apply accepted AI suggestions in a controlled way  
- Preserve original content integrity  
- Maintain a clear audit trail of structural changes  
- Prevent accidental overwrites or destructive edits  

---

## 2. Core Principles

1. **No silent edits** — every change must be traceable  
2. **Additive by default** — prefer adding links/tags over rewriting content  
3. **Reversible** — changes should be easy to undo  
4. **Human-confirmed** — nothing applies without explicit approval  

---

## 3. What Approval Means

When a user approves a suggestion, the system may:

- Add links to People, Places, Organizations, or Projects  
- Add tags to frontmatter or tag sections  
- Create a new Event file (never rewrite an old one)  
- Add a memory link to an existing Event  
- Log the applied change  

Approval **does not** allow rewriting original narrative text.

---

## 4. Where Changes May Occur

Approved updates may modify:

- Memory files in `01_Notes/`
- Event files in `05_Projects/_Events/`
- Entity files in `_Entities/` (add links only)
- `_Index/Timeline/` (add references only)
- `_Index/Relationships/` (add relationship lines)

No structural files in `_Policy/` may be auto-modified.

---

## 5. Change Logging

Every applied suggestion must be recorded in:

```
_AI/Applied_Suggestions/
```

Filename format:

```
YYYY-MM-DD_HHMM_applied.md
```

---

## 6. Applied Change Log Format

```md
# Applied AI Suggestions

Applied On:
Suggestion File:

---

## Changes Made

### Memory File Updated
File:
Added:
- Tag(s)
- Link(s)

### Event File Updated
File:
Added:
- Linked Memory

### Entity File Updated
File:
Added:
- Linked Event or Memory

---

Status: Completed
```
This creates a permanent audit trail.

---

## 7. Safe Editing Rules

When applying approved changes:

- Links are added at the bottom or in designated sections  
- Tags are appended, not replaced  
- YAML frontmatter is preserved  
- Existing content is never removed  
- Conflicts require manual resolution  

---

## 8. Conflict Handling

If a file structure is unclear or conflicts occur:

The system must:
- Stop automatic application  
- Flag the file in the change log  
- Require manual human edit  

---

## 9. Undo Principle

Because all changes are logged:

- A user can manually remove added tags or links  
- A full rollback is possible using the applied log as reference  

No destructive edits means recovery is always possible.

---

## 10. Privacy Compliance

If a suggestion involves a file marked:

```
Privacy Level: restricted
```

The system must:
- Skip auto-application  
- Record that the suggestion was blocked  

---

## 11. Portability

This mechanism relies only on:

- Markdown edits  
- Folder structure  
- Human-readable logs  

It works without any specific app, plugin, or platform.

---

## 12. Final Safeguard

If any rule is unclear, the system must default to:

**Do nothing and request human input.**

Safety is always preferred over automation.

---

🔒 Layer: Vault Template | KV
