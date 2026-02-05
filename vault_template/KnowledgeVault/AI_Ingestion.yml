#!/usr/bin/env python3
"""
KnowledgeVault AI Ingestion (Phase 1: safe, local, heuristic)

What it does:
- Reads 00_Inbox/Quick_Notes.md (and optionally other inbox md files)
- Splits entries by timestamp headings (e.g., "## YYYY-MM-DD HH:MM")
- Extracts lightweight signals (date/time, people, place hints, media filenames)
- Writes suggestion files ONLY to _AI/Suggestions/
- Writes logs ONLY to _AI/Logs/
- NEVER edits, moves, or deletes any existing vault files

Designed to follow:
- _Policy/AI_Ingestion_Behavior.md
- _Policy/AI_Suggestion_Approval_Mechanism.md

No external services required.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional

TS_HEADER_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?\s*$")
MEDIA_HINT_RE = re.compile(r"\b([\w\-\s]+\.(?:jpg|jpeg|png|heic|gif|mp4|mov|m4a|mp3|wav|pdf))\b", re.IGNORECASE)

STOPWORDS = {
    "I","I'm","Im","We","We've","You","Your","The","A","An","And","Or","But","To","Of","In","On","At","For","With","From",
    "Today","Yesterday","Tomorrow","AM","PM","Ok","Okay","Yeah","Yes","No","Home","Work"
}

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

def now_utc_stamp() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d_%H%M")

def parse_quick_notes(md_text: str) -> List[Dict[str, str]]:
    lines = md_text.splitlines()
    entries: List[Dict[str, str]] = []
    cur = None

    for line in lines:
        m = TS_HEADER_RE.match(line.strip())
        if m:
            if cur:
                cur["raw"] = "\n".join(cur["raw_lines"]).strip() + "\n"
                cur["body"] = cur["raw"]
                entries.append(cur)
            cur = {"date": m.group(1), "time": m.group(2) or "", "raw_lines": []}
            continue
        if cur is not None:
            cur["raw_lines"].append(line)

    if cur:
        cur["raw"] = "\n".join(cur["raw_lines"]).strip() + "\n"
        cur["body"] = cur["raw"]
        entries.append(cur)

    return entries

def extract_people(body: str) -> List[str]:
    text = re.sub(r"[^\w\s\-']", " ", body)
    tokens = [t for t in text.split() if t]
    people: List[str] = []

    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t[0].isupper() and t not in STOPWORDS and len(t) > 1:
            name_tokens = [t]
            j = i + 1
            while j < len(tokens):
                t2 = tokens[j]
                if t2[0].isupper() and t2 not in STOPWORDS and len(t2) > 1:
                    name_tokens.append(t2)
                    j += 1
                else:
                    break
            name = " ".join(name_tokens)
            if not (len(name) <= 4 and name.isupper()):
                people.append(name)
            i = j
        else:
            i += 1

    seen = set()
    out = []
    for p in people:
        k = p.lower()
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out[:8]

def extract_place(body: str) -> Optional[str]:
    m = re.search(r"^(?:Place|Location)\s*\(?.*?\)?:\s*(.+)$", body, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        place = m.group(1).strip()
        return place[:80] if place else None

    m2 = re.search(r"\bat\s+([A-Z][\w\-\s]{2,60})\b", body)
    if m2:
        candidate = m2.group(1).strip()
        candidate = re.split(r"\b(?:and|with|for|from)\b", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if candidate and candidate.lower() not in {"home","work"}:
            return candidate[:80]
    return None

def extract_media_hints(body: str) -> List[str]:
    matches = MEDIA_HINT_RE.findall(body)
    out = []
    seen = set()
    for m in matches:
        f = " ".join(m.split()).strip()
        key = f.lower()
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out[:10]

def confidence_for(people: List[str], place: Optional[str], media: List[str]) -> Dict[str, str]:
    ppl = "High" if len(people) >= 1 else "Low"
    plc = "Medium" if place else "Low"
    ev = "High" if (len(people) >= 1 and (place or media)) else ("Medium" if len(people) >= 1 else "Low")
    tags = "Medium" if (people or place or media) else "Low"
    return {"Event": ev, "People": ppl, "Place": plc, "Project": "Low", "Tags": tags}

def propose_tags(people: List[str], place: Optional[str], media: List[str]) -> List[str]:
    tags = []
    if people:
        tags.append("#type:memory")
        if len(people) >= 2:
            tags.append("#group:multi-person")
    if place:
        tags.append("#has:place")
    if media:
        tags.append("#has:media")
    if not tags:
        tags.append("#type:inbox-capture")
    return tags[:6]

def build_suggestion_md(source_file: str, entry_date: str, entry_time: str, people: List[str], place: Optional[str], media: List[str]) -> str:
    title_bits = []
    if people:
        title_bits.append("with " + " & ".join(people[:2]))
    if place:
        title_bits.append("at " + place)
    if not title_bits and media:
        title_bits.append("media capture")
    if not title_bits:
        title_bits.append("quick note")
    event_title = f"{entry_date} â " + " ".join(title_bits)

    conf = confidence_for(people, place, media)
    tags = propose_tags(people, place, media)

    lines = []
    lines.append("# AI Organization Suggestions\n")
    lines.append("## Source\n")
    lines.append(f"- File: `{source_file}`")
    ts = f"{entry_date} {entry_time}".strip()
    lines.append(f"- Entry Timestamp: {ts}\n")
    lines.append("---\n")
    lines.append("## Proposed Event Link\n")
    lines.append(f"Event name: **{event_title}**")
    lines.append("Reason: People/place/media signals detected from inbox entry.\n")
    lines.append("---\n")
    lines.append("## Proposed People Links\n")
    if people:
        for p in people:
            lines.append(f"- [[{p}]]")
        lines.append("Reason: Capitalized name-like tokens detected.\n")
    else:
        lines.append("- (none)")
        lines.append("Reason: No confident person tokens detected.\n")
    lines.append("---\n")
    lines.append("## Proposed Place Links\n")
    if place:
        lines.append(f"- [[{place}]]")
        lines.append("Reason: Location/Place hint detected.\n")
    else:
        lines.append("- (none)")
        lines.append("Reason: No explicit place hint detected.\n")
    lines.append("---\n")
    lines.append("## Proposed Project Links (if applicable)\n")
    lines.append("- (none)")
    lines.append("Reason: Project inference is disabled in heuristic mode.\n")
    lines.append("---\n")
    lines.append("## Proposed Tags\n")
    for t in tags:
        lines.append(f"- {t}")
    lines.append("Reason: Tags are conservative defaults based on available signals.\n")
    lines.append("---\n")
    lines.append("## Media Hints\n")
    if media:
        for m in media:
            lines.append(f"- `{m}`")
        lines.append("Reason: Filename-like strings detected in the entry.\n")
    else:
        lines.append("- (none)")
        lines.append("Reason: No media filenames detected in the entry.\n")
    lines.append("---\n")
    lines.append("## Confidence Levels\n")
    lines.append(f"- Event: {conf['Event']}")
    lines.append(f"- People: {conf['People']}")
    lines.append(f"- Place: {conf['Place']}")
    lines.append(f"- Project: {conf['Project']}")
    lines.append(f"- Tags: {conf['Tags']}")
    lines.append("\n---\n")
    lines.append("Status: Awaiting Review\n")
    return "\n".join(lines)

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def load_state(state_path: Path) -> Dict:
    if state_path.exists():
        try:
            import json
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(state_path: Path, state: Dict) -> None:
    import json
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser(description="KnowledgeVault safe AI ingestion (heuristic)")
    ap.add_argument("--vault", required=True, help="Path to your KnowledgeVault root (folder containing 00_Inbox, _AI, etc.)")
    ap.add_argument("--inbox", default="00_Inbox/Quick_Notes.md", help="Inbox markdown file relative to vault root")
    ap.add_argument("--dry-run", action="store_true", help="Do not write suggestions/logs; print what would happen")
    ap.add_argument("--max", type=int, default=25, help="Maximum number of new suggestions to write")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    inbox_path = (vault / args.inbox).resolve()

    suggestions_dir = vault / "_AI" / "Suggestions"
    logs_dir = vault / "_AI" / "Logs"
    state_path = vault / "_AI" / "ingest_state.json"

    ensure_dir(suggestions_dir)
    ensure_dir(logs_dir)

    if not inbox_path.exists():
        print(f"ERROR: Inbox file not found: {inbox_path}")
        return 2

    md = inbox_path.read_text(encoding="utf-8", errors="ignore")
    entries = parse_quick_notes(md)

    state = load_state(state_path)
    processed = set(state.get("processed", [])) if isinstance(state.get("processed", []), list) else set()

    written = 0
    new_hashes = []

    for e in entries:
        raw = f"{e.get('date','')}|{e.get('time','')}|{e.get('body','')}".strip()
        h = sha256_text(raw)
        if h in processed:
            continue

        people = extract_people(e.get("body",""))
        place = extract_place(e.get("body",""))
        media = extract_media_hints(e.get("body",""))

        stamp = now_utc_stamp()
        desc = "inbox_suggestion"
        if people:
            desc = re.sub(r"[^a-z0-9\-]+", "-", people[0].lower())[:40].strip("-") or desc
        fname = f"{stamp}_{desc}.md"
        out_path = suggestions_dir / fname

        md_out = build_suggestion_md(
            source_file=str(Path(args.inbox)),
            entry_date=e.get("date",""),
            entry_time=e.get("time",""),
            people=people,
            place=place,
            media=media,
        )

        if args.dry_run:
            print(f"[DRY RUN] Would write: {out_path.name}")
            print(md_out[:400] + ("\n...\n" if len(md_out) > 400 else "\n"))
        else:
            out_path.write_text(md_out, encoding="utf-8")
            written += 1
            new_hashes.append(h)

        if written >= args.max:
            break

    log_text = "\n".join([
        "# Ingestion Run Log\n",
        f"- Ran at (UTC): {dt.datetime.utcnow().isoformat(timespec='seconds')}Z",
        f"- Vault: `{vault}`",
        f"- Inbox: `{inbox_path}`",
        f"- New suggestions written: **{written}**",
        "",
        "## New Entry Hashes" if new_hashes else "## New Entry Hashes",
        *([f"- {h}" for h in new_hashes] if new_hashes else ["- (none)"]),
        ""
    ])

    if args.dry_run:
        print("[DRY RUN] Would update state and write run log.")
    else:
        processed.update(new_hashes)
        save_state(state_path, {"processed": sorted(processed)})
        log_name = f"{now_utc_stamp()}_ingest_run.md"
        (logs_dir / log_name).write_text(log_text, encoding="utf-8")

    print(f"Done. Suggestions written: {written}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
