# Index Auto-Linking Rules — Specification

This document defines how approved AI suggestions become structured links inside KnowledgeVault.

The purpose is to strengthen navigation across the vault without changing original memory content.

Auto-linking only occurs AFTER human approval during a review session.

---

## Guiding Principle

Link structure may grow.
Original memory files must remain untouched.

AI never edits the body of personal notes.  
It only updates structured index and entity reference files.

---

## What Can Be Auto-Linked

After approval, the system may create or update links in:

• _Index/Timeline/  
• _Index/Relationships/  
• _Entities/People/  
• _Entities/Places/  
• _Entities/Projects/  

---

## Event Linking Rules

If an approved suggestion includes an Event:

1. If the event already exists in Timeline  
   → Add a link to the source note/media

2. If the event does not exist  
   → Create a new Timeline entry using event template

Event titles should follow:
YYYY-MM-DD — Event Description

---

## People Linking Rules

For each approved person:

• If person already exists in _Entities/People/  
  → Add backlink to the event or note

• If person does not exist  
  → Create a new People entity file using template

Never merge two people automatically.

---

## Place Linking Rules

For each approved place:

• Match against known places list
• If a match exists → link
• If not → create new place entity

GPS coordinates may be stored only in Place entity files, not memory entries.

---

## Project Linking Rules

Projects are only linked when:

• The note clearly references work
• The AI confidence is High
• User approval confirms relevance

Project links go to:
_Entities/Projects/Project_Name.md

---

## Tag Handling

Tags may be added to:

• Timeline entries
• Entity files

Tags must follow naming standards:

#type:event  
#group:family  
#project:stegverse  

AI should prefer existing tags over creating new ones.

---

## Backlink Structure

Each entity file may contain:

## Related Events
• [[2026-02-03 — Dinner with Sam]]

## Related Notes
• [[2026-02-03 Quick Note]]

This keeps navigation bidirectional.

---

## Duplicate Prevention

Before creating any entity:

AI must check for:

• Exact filename matches
• Close name matches
• Existing backlinks

If uncertainty exists, suggest instead of auto-creating.

---

## Version Safety

All auto-linking actions should:

• Be logged in _AI/Logs/
• Be reversible
• Avoid overwriting manual edits

---

## Long-Term Goal

Over time, linking should make the vault:

• Easier to explore
• Rich in connections
• Still readable as plain Markdown

Structure should enhance memory — not replace it.
