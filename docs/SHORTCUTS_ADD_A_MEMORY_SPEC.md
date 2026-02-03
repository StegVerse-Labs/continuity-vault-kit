# Shortcuts Spec — Add a Memory (v0.1)

This document describes the exact Apple Shortcuts actions to build an iOS-friendly “Add a Memory” capture flow for KnowledgeVault.

Goal:
- Minimal typing
- Optional contact selection for “People Present”
- Optional location selection from known places OR GPS OR new place
- Optional “Event Type” quick picks
- Save a Markdown note into the correct folder with clean naming

---

## Required Vault Paths (defaults)

- Vault root: `iCloud Drive/KnowledgeVault/`
- Event notes: `01_Notes/`
- Templates: `_Templates/`
- Meta: `_Meta/` (create if missing)

Recommended file:
- `_Meta/places.txt` — one place per line

---

## Shortcut: Add a Memory

### Step 1 — Menu: Memory Type
Action: **Choose from Menu**
- Daily Note
- Event / Experience
- Emotional Moment
- Photo or Video Memory
- General Life Event
- Cancel

Branch to the selected flow.

---

# Event / Experience Flow

## A) Collect the basics

1) Action: **Ask for Input** (Text)
Prompt: `Event name`
Variable: `EventName`

2) Action: **Get Current Date**
Format: `yyyy-MM-dd`
Variable: `DateStr`

3) Action: **Get Current Date**
Format: `HH:mm`
Variable: `TimeStr`

4) Action: **Device Details**
Use: Model Name (or Device Name if preferred)
Variable: `DeviceStr`

---

## B) People Present (Contacts-assisted)

1) Action: **Choose from Menu**
Prompt: `People Present`
- Select from Contacts
- Type names manually
- Skip

### If “Select from Contacts”:
- Action: **Select Contacts** (multiple = ON)
- Action: **Repeat with Each Item** (Contacts)
  - Action: **Get Details of Contacts** → Name
  - Action: **Add to Variable** `PeopleList` (as lines like `- Full Name`)

Then:
- Action: **Choose from Menu**
Prompt: `Anyone else (not in contacts)?`
- Add another name
- No

If “Add another name”:
- Action: **Ask for Input** (Text) → `ExtraName`
- Action: **Add to Variable** `PeopleList` line: `- [Add Contact Later] ExtraName`

Optional convenience:
- Action: **Choose from Menu**
Prompt: `Add this person to Contacts?`
- Add now
- Later

If “Add now”:
- Action: **Create Contact** (pre-fill name = ExtraName)

### If “Type names manually”:
- Action: **Ask for Input** (Text)
Prompt: `Enter names separated by commas`
Variable: `NamesCSV`
- Action: **Split Text** by `,`
- Action: **Repeat with Each Item**
  - Trim whitespace (optional)
  - Add line to `PeopleList` as `- Name`

### If “Skip”:
Set `PeopleList` to `- (not recorded)`

---

## C) Location (Known / GPS / New)

1) Action: **Choose from Menu**
Prompt: `Location`
- Choose known place
- Use current GPS
- Enter new place
- Skip

### If “Choose known place”:
- Action: **Get File** `_Meta/places.txt` (from Vault root)
  - If file missing: set contents to `Home\nWork\n`
- Action: **Get Text from Input**
- Action: **Split Text** by New Lines
- Action: **Choose from List** (the lines)
Variable: `LocationStr`

### If “Use current GPS”:
- Action: **Get Current Location**
- Action: **Get Details of Locations** → Latitude, Longitude
- Set:
  - `GPSStr` = `lat, lon`
  - `LocationStr` = `Current Location`
(Optionally add “Get Street Address” if you want readable addresses; it may be slower.)

### If “Enter new place”:
- Action: **Ask for Input** (Text) prompt: `Place name`
Variable: `NewPlace`
Set `LocationStr` = `NewPlace`
Then ask:
- Action: **Choose from Menu** prompt: `Save to known places list?`
  - Yes
  - No
If Yes:
  - Read `_Meta/places.txt` (or create)
  - Append `NewPlace` on a new line
  - Save file back

### If “Skip”:
Set `LocationStr` = `(not recorded)` and `GPSStr` = `(not recorded)`

---

## D) Event Type quick picks

Action: **Choose from Menu**
Prompt: `Event type`
- Hanging out with friends
- Family time
- Date night
- Kids milestone
- Work / meeting
- Health / appointment
- Travel / outing
- Exercise / outdoors
- Celebration
- Errands / routine
- Other…

If “Other…”:
- Ask for Input (Text) → `EventTypeStr`
Else:
- Set `EventTypeStr` to chosen menu item

---

## E) Narrative

1) Action: **Ask for Input** (Text, multiline)
Prompt: `What happened?`
Variable: `WhatHappened`

2) Action: **Ask for Input** (Text, optional)
Prompt: `Any highlights? (one line each; separate with semicolons)`
Variable: `HighlightsRaw`
- Split by `;` and format as bullet list (optional)
Variable: `HighlightsList`

---

## F) Build the Markdown note

Use “Text” action to assemble:

Filename:
`{DateStr} Event — {EventName}.md`

Content template includes:
- Date, Time, Device
- LocationStr, GPSStr
- EventTypeStr
- PeopleList
- WhatHappened
- Highlights bullets

---

## G) Save

Action: **Save File**
- Destination: Vault root → `01_Notes/`
- Ask Where to Save: OFF
- Overwrite if Exists: OFF

Action: **Show Notification**
`Saved: {Filename}`

Optional:
- Action: **Open File** (so user can review)

---

## Notes on Apple limitations

- Shortcuts can’t “auto-match typed names to contacts” in a live search box.
- “Create Contact” requires user confirmation (privacy by design).
- GPS requires location permission; allow “Skip” always.
