# Entities

Use this folder for people, places, organizations, projects, and yourself — any entity you reference repeatedly across your vault.

## Why entities matter

When you mention "Dr. Smith" in ten different notes, an entity file creates a single reference point:
- Who they are
- How to reach them
- What your relationship is
- Links to every note that mentions them

This makes your vault navigable and keeps context connected over time.

## Folder structure

- `People/` — Individuals you know or reference
- `Places/` — Locations, venues, cities, landmarks
- `Projects/` — Active or past work, creative endeavors
- `Organizations/` — Companies, schools, groups, institutions
- `Self/` — Information about you (health overview, life priorities, current snapshot)

## How to create an entity file

1. Choose the right folder
2. Create a Markdown file named after the entity (e.g., `Dr_Smith.md`)
3. Use the template in `Entity_File_Templates-Standard.md` as a starting point
4. Fill in what you know now; add more later

## Privacy

- Set `Privacy Level: normal` for most entities
- Set `Privacy Level: restricted` for sensitive contacts or locations
- The AI ingestion tool will never read `Privacy Level: restricted` files

## Example

```markdown
# Dr. Smith

Type: Person
Privacy Level: normal

## About
Family physician since 2022

## Known Relationships
- [[Self/Health_Overview]]

## Important Dates
- Birthday: (not recorded)
- First Met: 2022-03-15

## Related Events
- [[2022-03-15 — First Appointment]]

## Related Notes
- [[2023-01-10 — Bloodwork Results]]

## Tags
#person #health
```

This is your personal entity reference. It is not shared with any service unless you explicitly choose to.

---

🔒 Layer: Vault Template | KV
