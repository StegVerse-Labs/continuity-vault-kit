# Health-Record Chronology Example

Use this pattern to preserve a sequence of health events without turning summaries into medical authority.

## Scope

- **Purpose:** reconstruct what happened, when, and which source records support it.
- **Not included:** diagnosis, treatment instruction, emergency guidance, or replacement for a clinician.

## Chronology

| Date | Event | Source record | Confidence |
|---|---|---|---|
| 2026-02-04 | Symptom first recorded | `03_Records/Health/notes/2026-02-04.md` | Direct note |
| 2026-02-11 | Appointment occurred | `03_Records/Health/visits/2026-02-11-summary.pdf` | Source document |
| 2026-02-14 | Medication list updated | `03_Records/Health/medications.md` | Owner-maintained |

## Facts versus interpretations

### Supported facts

- The dated records above exist.
- The appointment summary lists the recorded observations.
- The medication list changed on the stated date.

### Interpretations requiring review

- Whether one event caused another.
- Whether a symptom represents a diagnosis.
- Whether a treatment was effective.

## Missing or conflicting records

- Record absent: laboratory result referenced by the visit summary.
- Conflict: owner note and visit summary list different symptom start dates.

## Next permitted action

Request or locate the missing source record, then append it without overwriting the earlier chronology. A future person or AI may summarize the records but must not resolve clinical conflicts without qualified review.

## Privacy boundary

Use local references instead of copying unnecessary sensitive content into a handoff intended for sharing.

---

🔒 Layer: Framework | KV
