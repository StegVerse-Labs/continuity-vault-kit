# Entity File Templates — Standard

This document defines the standard structure for entity files inside KnowledgeVault.

Entity files are structured reference points that connect memories across time.

They do NOT replace original notes — they provide context and navigation.

---

## General Rules

• Entity files must be human-readable Markdown  
• AI may suggest additions but never overwrite user-written sections  
• Each entity lives in its appropriate folder under `_Entities/`

Entity categories include:

• People  
• Places  
• Projects  
• Events (via Timeline entries)

---

# 👤 People Template
Location: `_Entities/People/Name.md`

```md
# Name

Type: Person  
Privacy Level: normal  

## About
(Optional user-written description)

## Known Relationships
• [[Person]]
• [[Group or Family]]

## Important Dates
• Birthday:
• First Met:

## Related Events
• [[YYYY-MM-DD — Event Name]]

## Related Notes
• [[Note Title]]

## Tags
#person
```

---

# 📍 Places Template
Location: `_Entities/Places/Place_Name.md`

```md
# Place Name

Type: Place  
Privacy Level: normal  

## Description
(Optional description)

## Location Data
City:
State/Region:
Country:
GPS (optional):

## Related Events
• [[YYYY-MM-DD — Event Name]]

## Related Notes
• [[Note Title]]

## Tags
#place
```

---

# 🛠 Projects Template
Location: `_Entities/Projects/Project_Name.md`

```md
# Project Name

Type: Project  
Privacy Level: normal  

## Description
What this project is about

## Start Date
YYYY-MM-DD

## Status
Active | Paused | Completed

## Related Events
• [[YYYY-MM-DD — Event Name]]

## Related Notes
• [[Note Title]]

## Tags
#project
```

---

# 📅 Event Template (Timeline Entry)
Location: `_Index/Timeline/YYYY-MM-DD — Event Title.md`

```md
# YYYY-MM-DD — Event Title

Type: Event  
Privacy Level: normal  

## Summary
Brief description of what happened

## People Present
• [[Person]]

## Location
• [[Place]]

## Related Project
• [[Project]]

## Source Notes
• [[Note Title]]

## Media
• [[Photo or Video Filename]]

## Tags
#event
```

---

## AI Usage Rules

AI may:
• Add links under Related Events / Notes
• Suggest tags
• Suggest relationships

AI may NOT:
• Rewrite descriptions
• Remove user text
• Change privacy levels

---

## Long-Term Design Goal

These templates ensure:

• Consistency across decades
• Compatibility with future AI tools
• Human readability without special software
• Strong linking without database lock-in

---

🔒 Layer: Vault Template | KV
