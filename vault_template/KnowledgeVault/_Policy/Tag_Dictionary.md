# KnowledgeVault Tag Dictionary

This file defines the official tags used in this KnowledgeVault.

Purpose:
- Avoid duplicate or drifting tag meanings
- Keep tags consistent across decades
- Help AI understand the meaning and scope of tags
- Make search and grouping reliable

---

## Tag Format

All tags should follow this pattern:

`#namespace:slug`

Examples:
- `#group:family-core`
- `#place:zilker-park`
- `#time:saturday`
- `#type:birthday`

Rules:
- Lowercase only
- Hyphen-separated words
- No spaces
- Stable over time (don’t rename casually)

---

## Namespaces

### 👥 People Groups — `#group:`
Used when the same people appear together repeatedly.

Examples:
- `#group:family-core`
- `#group:saturday-crew`
- `#group:work-team`

Do NOT use for:
- One-time gatherings
- Temporary combinations

---

### 📍 Places — `#place:`
Used for meaningful or recurring locations.

Examples:
- `#place:home`
- `#place:zilker-park`
- `#place:grandmas-house`

Use when:
- Location has emotional or narrative importance
- Appears repeatedly in memories

---

### 🕒 Time Patterns — `#time:`
Used for recurring time-based patterns.

Examples:
- `#time:saturday`
- `#time:summer`
- `#time:late-night`

Do NOT overuse — only when it helps group memories meaningfully.

---

### 🎉 Event Types — `#type:`
Used for categories of life events.

Examples:
- `#type:birthday`
- `#type:wedding`
- `#type:reunion`
- `#type:vacation`
- `#type:milestone`

This is about the *kind* of event, not the specific instance.

---

### 💭 Emotional Tone — `#mood:` (optional)
Used sparingly for strong emotional themes.

Examples:
- `#mood:joy`
- `#mood:grief`
- `#mood:peaceful`

Do NOT auto-suggest these without explicit user input.

---

## Tag Lifecycle Rules

### Adding a New Tag
Before adding a tag:
1. Check if a similar tag already exists
2. Decide if it fits an existing namespace
3. Add it to this dictionary with a short description

---

### Avoid These Anti-Patterns

❌ `#fun-day` (too vague)  
❌ `#friends` (too broad)  
❌ `#park` (use a specific place tag)  
❌ `#birthday-party-lily` (instance-specific, belongs in event, not tag)

Tags are for **patterns**, not individual memories.

---

## How AI Should Use This File

AI systems should:
- Prefer existing tags over creating new ones
- Suggest tags from this dictionary when patterns are detected
- Avoid inventing new namespaces without user approval

---

🔒 Layer: Vault Template | KV
