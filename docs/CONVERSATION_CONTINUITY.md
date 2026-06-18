# Conversation Continuity

KnowledgeVault began as a way to preserve long-running AI-human conversations after a chat session loses context, fills memory, or becomes too large to keep fluid.

This guide explains how to store conversation state so a future AI session can reload the important context without rereading everything.

---

## What this solves

AI chats are useful, but long projects often break because:

- conversation windows get too long
- memory becomes incomplete
- important decisions are buried in old threads
- new sessions require too much re-explanation
- project state drifts across multiple chats

KnowledgeVault gives you a place to preserve the **working state** of a conversation outside the chat system.

The goal is not to store every word forever.

The goal is to preserve enough context that your future self and a future AI session can continue intelligently.

---

## The basic workflow

1. **Talk normally.**  
   Use ChatGPT or another AI tool as usual.

2. **Pause when the conversation becomes important.**  
   When a decision, plan, architecture, or milestone emerges, capture the state.

3. **Create a continuity note.**  
   Save a short summary into your vault.

4. **Create a reload packet when needed.**  
   When starting a new AI session, copy the reload packet into the first prompt.

5. **Continue from the preserved state.**  
   The AI should be able to resume without guessing.

---

## Where to store conversation continuity files

Recommended locations inside the vault:

```text
00_Inbox/                      quick captures before cleanup
01_Notes/                      general conversation summaries
05_Projects/<Project_Name>/    project-specific continuity notes
_Index/                        links to major continuity threads
_Templates/                    reusable continuity templates
```

Use the simplest location that keeps the file findable.

If the conversation belongs to a project, store it with that project.

---

## Recommended file names

Use date-first names so files sort naturally:

```text
2026-06-18 — ChatGPT Continuity — KnowledgeVault Roadmap.md
2026-06-18 — Reload Packet — Fin-Co Pilot Design.md
2026-06-18 — Decision Log — StegID Architecture.md
```

Do not over-optimize naming. Findability matters more than perfection.

---

## Three file types that matter

### 1. Conversation Summary

Use this when you want a human-readable record of what happened.

Include:

- topic
- decisions made
- open questions
- files changed
- next action
- links to related vault files

### 2. Reload Packet

Use this when you want to start a new AI session from a known state.

Keep it shorter than a full transcript.

Include:

- current objective
- important assumptions
- active constraints
- completed work
- next tasks
- what not to revisit

### 3. Decision Log

Use this when a conversation produces a meaningful choice.

Include:

- decision
- reason
- alternatives rejected
- consequences
- date
- related files

---

## Minimal reload packet template

Copy this into a new file when a conversation reaches a stable handoff point:

```md
# Reload Packet — <Topic>

Date: <YYYY-MM-DD>
Project: <Project or Module>

## Current objective
<What we are trying to accomplish now.>

## Current state
<What has already been built, decided, or ruled out.>

## Important constraints
- <Constraint 1>
- <Constraint 2>
- <Constraint 3>

## Files or artifacts involved
- `<path>` — <purpose>
- `<path>` — <purpose>

## Next tasks
1. <Next task>
2. <Next task>
3. <Next task>

## Do not revisit unless necessary
- <Settled issue>
- <Rejected approach>

## First prompt for next AI session
Continue from this reload packet. Preserve the stated constraints. Start with the next task unless a blocking inconsistency is detected.
```

---

## What to preserve

Preserve:

- decisions
- assumptions
- repo/file paths
- version numbers
- public release status
- active constraints
- current next step
- why a choice was made

Do not preserve everything by default.

A useful reload packet is compressed, not exhaustive.

---

## What not to store casually

Do not place sensitive material in plain text unless you understand the risk.

Avoid storing:

- passwords
- secret keys
- private tokens
- full medical records
- financial account numbers
- private information about other people without a clear reason

Read:

- [`../SAFETY.md`](../SAFETY.md)
- [`../DO_NOT_STORE_HERE.md`](../DO_NOT_STORE_HERE.md)

KnowledgeVault is a structure. It is not encryption.

---

## How AI should use continuity notes

AI tools may use continuity notes to:

- reload context
- identify next tasks
- detect contradictions
- suggest missing links
- summarize project state

AI tools must not:

- overwrite human-authored notes without approval
- silently change decisions
- treat summaries as perfect truth
- read restricted files without explicit permission

See:

- [`AI_COMPATIBLE.md`](./AI_COMPATIBLE.md)
- [`AI_Ingestion.md`](./AI_Ingestion.md)

---

## Example: short reload packet

```md
# Reload Packet — KnowledgeVault Public Release

Date: 2026-06-18
Project: continuity-vault-kit

## Current objective
Clarify KnowledgeVault as a reloadable AI-human conversation continuity system while preserving the deeper vault architecture.

## Current state
The repo is public. It already contains AI-compatible structure, entity modeling, indexing, policy docs, tools, and release automation. The current audience is technically versatile systems thinkers, not mass-market casual note users.

## Important constraints
- Do not overwrite the current public release.
- Do not require an app or iOS Shortcut.
- Keep AI suggestions as proposals only.
- Keep first-contact docs practical and lightweight.

## Files involved
- `README.md` — public framing
- `WELCOME.md` — first-contact onboarding
- `docs/CONVERSATION_CONTINUITY.md` — original-use-case guide
- `STATUS.md` — current roadmap

## Next tasks
1. Link this guide from WELCOME and GETTING_STARTED.
2. Update STATUS to remove stale completed items.
3. Verify `_Entities/README.md` exists and is clear.

## First prompt for next AI session
Continue KnowledgeVault public-release work from this packet. Improve first-contact clarity without stripping the advanced architecture.
```

---

## Practical rule

Every long-running project should have at least one current reload packet.

If a future AI session cannot answer “what are we doing next?” within one minute, the continuity layer needs an update.

---

## Relationship to the vault

Conversation continuity is not separate from KnowledgeVault.

It is one of the primary reasons the vault exists.

The vault preserves memory.
The reload packet restores working context.
The human remains the authority.
