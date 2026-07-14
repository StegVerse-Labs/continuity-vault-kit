# Tag Suggestion Rules v0.1

These are conservative, explainable, opt-in suggestions.

## Memory fields assumed (if present)
- people: [Name, Name]
- location_label: "Place name"
- event: "YYYY-MM-DD — Event Name" or "none"
- tags: ["#tag"]

## Suggestion types

### 1) People-group tag
Trigger:
- The exact same set of people appears together in >= 3 memories within the last 90 days
Suggest:
- #group:<slug>
Examples:
- #group:family-core
- #group:saturday-crew

Reason format:
- "people group repeated N times"

### 2) Location tag
Trigger:
- Same location_label appears in >= 5 memories within the last 180 days
Suggest:
- #place:<slug>
Examples:
- #place:zilker-park
- #place:grandmas-house

Reason:
- "location repeated N times"

### 3) Time-pattern tag (lightweight)
Trigger:
- >= 4 memories occur on the same weekday (e.g., Saturday) within last 60 days
Suggest:
- #time:<weekday>
Examples:
- #time:saturday

Reason:
- "weekday pattern N occurrences"

### 4) Event-type tag (keyword-based)
Trigger:
- Event title contains keywords (birthday, wedding, reunion, trip) >= 2 times total
Suggest:
- #type:<keyword>
Examples:
- #type:birthday
- #type:wedding

Reason:
- "event keyword match"

## Never do (v0.1)
- No automatic writes to memory files
- No inference of sensitive tags (health, politics, finances) without explicit user input
- No face recognition or message scraping

---

🔒 Layer: Vault Template | KV
