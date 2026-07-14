# Light Mode Dashboard — Specification

The Light Mode Dashboard is the calm, low-friction interface layer of KnowledgeVault.

It is designed to help users gently maintain their vault without needing to understand the underlying folder structure or AI mechanics.

This dashboard surfaces only what needs attention — never overwhelming the user.

---

## 🎯 Purpose

Light Mode exists to:

• Show what needs review  
• Surface incomplete memories  
• Present AI organization suggestions  
• Encourage light, ongoing maintenance  
• Keep the vault feeling alive and cared for  

It is not a control panel.  
It is a *gentle assistant view*.

---

## 🧩 Core Sections

### 1. AI Suggestions Waiting

Shows count and quick links to:

_AI/Suggestions/

Display example:

> **3 Organization Suggestions Ready for Review**  
> Last suggestion: *Dinner with Sam & Lily*

Actions:
• Review Now  
• Remind Me Later  

---

### 2. Incomplete Memories

Identifies entries missing useful context:

Examples:
• Events without people tagged  
• Media without notes  
• Entries without location  
• Placeholder titles like “IMG_4821”

Display example:

> **5 Memories Could Use More Detail**  
> Add names, places, or notes to make them easier to find later.

Actions:
• Review Memories  
• Ignore for Now  

---

### 3. Inbox Status

Tracks unprocessed captures in:

00_Inbox/

Display example:

> **12 Items in Inbox**  
> These are recent captures waiting to be organized.

Actions:
• Process Inbox  
• Snooze  

---

### 4. Recent Activity

Shows last structural changes (not content changes):

Examples:
• New event created  
• Suggestion approved  
• New person added  
• Tag added

Display example:

> **Recent Updates**
> • Event created: “2026-02-04 — Beach Day”  
> • Person added: [[Lily]]

---

### 5. Gentle Prompts

Occasional soft nudges such as:

• “You haven’t reviewed suggestions in a while.”  
• “There are 20+ inbox items waiting.”  
• “Several recent photos have no notes.”

Prompts must be:
• Infrequent  
• Non-urgent  
• Dismissible  

No red alerts. No pressure.

---

## 🧠 AI Role in Light Mode

The AI system may:

• Count suggestion files  
• Detect missing metadata patterns  
• Detect inbox growth  
• Detect stale review cycles  

The AI must not:
• Apply changes automatically  
• Modify files  
• Reclassify memories  

Light Mode is awareness, not automation.

---

## 🎛 Interaction Style

Light Mode should feel:

• Calm  
• Non-technical  
• Encouraging  
• Optional  

It should never feel like:
• A task manager  
• A backlog  
• A responsibility list  

This is memory stewardship, not productivity tracking.

---

## 🔄 Update Frequency

Light Mode may refresh:
• When the vault is opened  
• During scheduled review sessions  
• When new AI suggestions are generated  

It should not trigger constant notifications.

---

## 🔒 Privacy Boundary

Light Mode reads structure only:

• Counts files  
• Checks metadata presence  
• Detects missing links  

It does not read personal content unless the user enters review mode.

---

## 🌿 Design Philosophy

Light Mode is the “garden path” through KnowledgeVault.

The vault can be deep and complex beneath the surface.  
Light Mode ensures the user only sees what needs gentle care — nothing more.

It exists to make long-term continuity sustainable, not burdensome.

---

🔒 Layer: Vault Template | KV
