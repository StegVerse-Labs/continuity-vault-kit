"""LC-KV-26, the Org end: the reader behind ``kv_receipt_ledgers.ORG_CROSSING_READER``.

SKAP Vault inside KV is the only PII and credential store for every user, the ecosystem's own included; the
ecosystem holds none (HST citation pending P1 #163).

``read(designation, which) -> list | None`` returns the public Org ledger's existing digest-only records of genuine
crossings between distinct orgs, each exactly ``{path_id, receipt_sha256, endpoint_head_sha256, supplied_hb_epoch}``.

Boundaries (StegVerse-org/.github#162 handoff c6393962100; ruling #167 c6374130335):
- Read-only. This module only reads files of an already-fetched, anonymously read snapshot of
  ``refs/stegverse/organization-ledger``; it never opens a socket, never reads a clock and never holds a credential.
  The anonymous network fetch lives in the observer layer, ``tools/observers/org_ledger_observer.py``.
- No new InTr path and no hop inside an org: a record is emitted only when its path_id is
  ``<OrgA>-><OrgB>:intr-destination`` with OrgA and OrgB distinct organization names. Anything else (for example a
  path to a non-org endpoint) is never emitted.
- Never fabricated: ``endpoint_head_sha256`` is taken only where the Org record itself carries it (in ``evidence``,
  ``evidence.boundary_evidence`` or ``boundary_evidence``). A record without it is not emitted.
- Refuse-only: the caller (``kv_receipt_ledgers._org_crossing``) uses these records only to refuse; this reader grants
  nothing (authority_effect NONE).
- Fail closed: an absent, unreadable, unsealed or broken-chain snapshot returns ``None`` (not observable) and leaves
  the six-field FAIL_CLOSED in ``LAST_READ``.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

SNAPSHOT_ENV = "STEGVERSE_ORG_LEDGER_SNAPSHOT"
LEDGER_REF = "refs/stegverse/organization-ledger"
ORG_LEDGER_SOURCE = "https://github.com/StegVerse-org/.github.git"
SNAPSHOT_SCHEMA = "stegverse.org-ledger-anonymous-snapshot/v1"
ORG_CROSSING_KEYS = ("path_id", "receipt_sha256", "endpoint_head_sha256", "supplied_hb_epoch")
PATH_SUFFIX = ":intr-destination"
ENDPOINT_HEAD_KEY = "endpoint_head_sha256"
MIN_EPOCH = 32
OWNING_GOAL = "StegVerse-org/.github#162 (both sides record each InTr crossing; #162 comment 6372641743; Lane B)"
FAILURE_CODE = "KV_CROSSING_RECORD_NOT_OBSERVED"
FAILED_PREDICATE = "ORG_SIDE_OF_EACH_CROSSING_OBSERVED_BY_THE_READER"
RETRY_ENTRYPOINT = ("python tools/observers/org_ledger_observer.py --out <dir>; "
                    f"{SNAPSHOT_ENV}=<dir> runtime.org_crossing_reader.read(designation, which)")
#: GitHub organization names: alphanumerics and single hyphens. A non-org endpoint such as STEGVERSE_KV never matches.
_ORG = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")

#: The outcome of the most recent read: None before any read, else {"observed": True, ...} or a six-field FAIL_CLOSED.
LAST_READ: dict[str, Any] | None = None


def _is_sha(v: Any) -> bool:
    return isinstance(v, str) and bool(_SHA.match(v))


def seal(body: Mapping[str, Any]) -> str:
    """The Org ledger's seal rule (StegVerse-org/.github scripts/intr_post_genesis_replay.py seal_verifies)."""
    rest = {k: v for k, v in body.items() if k != "receipt_sha256"}
    raw = json.dumps(rest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def distinct_org_path(path_id: Any) -> bool:
    """True only for ``<OrgA>-><OrgB>:intr-destination`` with two distinct organization names."""
    if not isinstance(path_id, str) or not path_id.endswith(PATH_SUFFIX):
        return False
    ends = path_id[: -len(PATH_SUFFIX)].split("->")
    return len(ends) == 2 and all(_ORG.match(e) for e in ends) and ends[0] != ends[1]


def failure(detail: str, which: str | None = None) -> dict[str, Any]:
    return {"disposition": "FAIL_CLOSED", "receipt_ledger": which, "failure_code": FAILURE_CODE,
            "failed_predicate": FAILED_PREDICATE,
            "required_evidence_or_repair": ("an anonymously read snapshot of the public StegVerse-org "
                                            f"{LEDGER_REF} whose every receipt verifies its seal and whose chain "
                                            "links from HEAD.json by previous_receipt_sha256"),
            "retry_entrypoint": RETRY_ENTRYPOINT, "owning_existing_goal": OWNING_GOAL,
            "next_attempt": "on the next observer snapshot of the Org ledger (event-triggered)",
            "detail": detail, "authority_effect": "NONE"}


def _holders(r: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    out = []
    ev = r.get("evidence")
    if isinstance(ev, Mapping):
        out.append(ev)
        if isinstance(ev.get("boundary_evidence"), Mapping):
            out.append(ev["boundary_evidence"])
    if isinstance(r.get("boundary_evidence"), Mapping):
        out.append(r["boundary_evidence"])
    return out


def _field(r: Mapping[str, Any], key: str) -> Any:
    for h in _holders(r):
        if key in h:
            return h[key]
    return None


def crossing_record(r: Mapping[str, Any]) -> dict[str, str] | None:
    """The digest-only crossing record an Org receipt carries, or None. Pure: no clock, no network."""
    path_id = _field(r, "path_id")
    head = _field(r, ENDPOINT_HEAD_KEY)
    hb = r.get("hb_reference")
    if not (distinct_org_path(path_id) and _is_sha(head) and _is_sha(r.get("receipt_sha256"))
            and isinstance(hb, Mapping) and hb.get("derived_from_clock") is False):
        return None
    epoch = hb.get("epoch")
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < MIN_EPOCH:
        return None
    return {"path_id": path_id, "receipt_sha256": r["receipt_sha256"], "endpoint_head_sha256": head,
            "supplied_hb_epoch": str(epoch)}


def walk(head: Any, receipts: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Walk the chain from ``head`` by previous_receipt_sha256, verifying each seal. Raises ValueError if broken."""
    if not _is_sha(head):
        raise ValueError(f"HEAD.json receipt_sha256 {head!r} is not a sha256 digest")
    chain, seen, cur = [], set(), head
    while cur is not None:
        if cur in seen:
            raise ValueError(f"chain cycles at {cur}")
        seen.add(cur)
        r = receipts.get(cur)
        if not isinstance(r, Mapping):
            raise ValueError(f"receipt {cur} is not in the snapshot")
        if r.get("receipt_sha256") != cur or seal(r) != cur:
            raise ValueError(f"receipt {cur} does not verify its seal")
        chain.append(dict(r))
        cur = r.get("previous_receipt_sha256")
        if cur is not None and not _is_sha(cur):
            raise ValueError(f"previous_receipt_sha256 {cur!r} is not a sha256 digest")
    return chain


def crossings(head: Any, receipts: Mapping[str, Mapping[str, Any]], path_ids: Any = None) -> list[dict[str, str]]:
    """Every distinct-org crossing record on the verified chain (newest first), optionally filtered to path_ids."""
    keep = None if path_ids is None else set(path_ids)
    out = []
    for r in walk(head, receipts):
        c = crossing_record(r)
        if c is not None and (keep is None or c["path_id"] in keep):
            out.append(c)
    return out


def load_snapshot(root: Path) -> tuple[Any, dict[str, dict[str, Any]], dict[str, Any]]:
    meta = json.loads((root / "snapshot.json").read_text(encoding="utf-8"))
    if not isinstance(meta, dict) or meta.get("schema") != SNAPSHOT_SCHEMA or meta.get("ledger_ref") != LEDGER_REF:
        raise ValueError("snapshot.json is not an anonymous Org ledger snapshot")
    head = json.loads((root / "HEAD.json").read_text(encoding="utf-8")).get("receipt_sha256")
    receipts = {}
    for p in sorted((root / "receipts").glob("*.json")):
        body = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(body, dict) and _is_sha(body.get("receipt_sha256")):
            receipts[body["receipt_sha256"]] = body
    return head, receipts, meta


def _designated_path_ids(designation: Mapping[str, Any]) -> list[str]:
    ids = designation["rollback_watermark_source"]["org_crossing_cross_check"]["path_ids"]
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise ValueError("org_crossing_cross_check.path_ids is not a list of strings")
    return ids


def read(designation: Mapping[str, Any], which: str, snapshot: str | os.PathLike | None = None) -> list | None:
    """``ORG_CROSSING_READER(designation, which) -> list | None``. None means not observable (see LAST_READ)."""
    global LAST_READ
    root = snapshot if snapshot is not None else os.environ.get(SNAPSHOT_ENV)
    if not root:
        LAST_READ = failure(f"no anonymous Org ledger snapshot is supplied ({SNAPSHOT_ENV} is unset)", which)
        return None
    try:
        ids = _designated_path_ids(designation)
        head, receipts, meta = load_snapshot(Path(root))
        found = crossings(head, receipts, ids)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        LAST_READ = failure(f"the Org ledger snapshot at {root} could not be read: {exc}", which)
        return None
    LAST_READ = {"observed": True, "receipt_ledger": which, "org_ledger_head": head,
                 "org_ledger_ref_tip": meta.get("ledger_ref_tip"), "records": len(found),
                 "designated_path_ids_between_distinct_orgs": [i for i in ids if distinct_org_path(i)],
                 "authority_effect": "NONE"}
    return found
