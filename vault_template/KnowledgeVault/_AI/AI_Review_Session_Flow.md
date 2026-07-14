# AI Review Session Flow — Specification

This document defines the step-by-step flow for reviewing AI-generated suggestions inside KnowledgeVault.

The goal is to make reviewing organization suggestions feel lightweight, safe, and fully under human control.

---

## Purpose

The AI Review Session allows the user to:

• See what the AI noticed  
• Decide what to accept  
• Ignore or reject suggestions  
• Keep full ownership of their memories  

No automatic changes ever occur.

---

## When a Review Session Happens

A review session may begin when:

• The user taps “Review Suggestions”
• A reminder notification is tapped
• The user opens the _AI/Suggestions/ folder manually

---

## Step 1 — Session Overview Screen

The system shows:

• Number of new suggestions
• Oldest suggestion date
• Categories involved (Events, People, Places, Tags, Projects)

Options:

[Start Review]  
[Remind Me Later]  
[Dismiss All]

---

## Step 2 — Suggestion Card View

Each suggestion appears as a card.

Each card includes:

• Source file or media reference  
• Detected date/time  
• AI-proposed links:
  - Event
  - People
  - Place
  - Project
  - Tags
• Confidence indicators

Buttons:

[Accept All]  
[Edit]  
[Reject]

---

## Step 3 — Edit Mode (Optional)

If “Edit” is selected:

User may:

• Remove individual suggestions
• Change suggested names
• Add missing tags
• Adjust event title

Then:

[Save Changes]  
[Cancel]

---

## Step 4 — Confirmation

After accepting suggestions:

The system proposes:

• Creating new index entries if needed
• Adding links to existing entities
• Writing approved suggestions into structured index files

User confirms:

[Apply Changes]  
[Go Back]

---

## Step 5 — Completion Screen

When review session ends:

• Show number of suggestions applied
• Show number rejected
• Offer next reminder schedule

Message:

“Your vault is now more organized and easier to navigate.”

---

## Design Principles

• No silent changes
• Always reversible
• Calm, minimal UI
• Respect user pace

---

## Long-Term Goal

Review sessions should become:

• Less frequent
• More precise
• Faster to complete

As AI improves pattern recognition over time.

---

🔒 Layer: Vault Template | KV
