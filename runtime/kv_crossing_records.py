"""KV's own end of an Org->KV InTr crossing: one INTR_MESH_PATH_INGRESS record on KV's own receipt chain.

StegVerse-org/.github#162 c6394603737 (Coordination ruling LC-KV-29): KV is its own ledger-holding party, distinct from
any org; a crossing between an org and KV is a crossing between two distinct parties (never a hop inside one org) and is
recorded on both ledgers, KV's end required. This module is KV's end: it plans, and (only where the designated storage
endpoint is admitted) appends, the digest-only ingress record on KV's own chain (``_StegVerse/Receipts``), in the shape
``runtime.kv_receipt_ledgers._org_crossing`` already checks: transition_class INTR_MESH_PATH_INGRESS, evidence pointing
at the Org's record by digest (``source_repository_receipt_sha256``), SUPPLIED_HB_EPOCH, no body, no copy of the Org's
record.

Exactly one receipt per crossing. Rigel, 2026-10-29 3:08 PM CDT, in Lane B's chat, relayed at
StegVerse-org/.github#162 c6508050206: "This shouldn't be possible without being a literal duplicate." So a crossing
(path_id, communication_id) gets one KV-side receipt; a second record for the same crossing is refused as a duplicate,
six-field FAIL_CLOSED ``INTR_PATH_DESTINATION_CROSSING_ALREADY_RECORDED`` (the code Lane B's Org side uses,
StegVerse-org/.github#261), whether or not it would be byte-identical. There is no newest-wins and no replacement or
successor policy, and the check is made again under the append lock, so two writers cannot both record it. An unchained receipt file for the crossing (a crash between the receipt write and
the HEAD.json update) is found too: adopted only if byte-identical to the receipt this call would write on the current
head, otherwise refused fail-closed, so a crossing never has two receipt files (P4's note on cvk#284).

A torn or misnamed file anywhere in ``receipts/`` blocks every new crossing, not only its own, until the owner of the
chain repairs it. That is intentional and fail-closed: a file that is not a receipt of its own name has a crossing id this
writer cannot read, so it cannot show that recording another crossing leaves that one with a single receipt file. The
refusal is ``KV_CROSSING_RECEIPT_FILE_UNREADABLE``; nothing is repaired, moved or deleted here.

Files named ``.kv-crossing-*`` beside the chain root (the writer's temp files; a hard kill can leave one) are never read
as receipts. This writer deletes nothing in the store: they are ignored when scanning and listed in ``stray_temp_files``
of the plan, the append result and every refusal (and in a refusal's ``detail``) so an operator can see them. The writer's
own lock file (``LOCK_NAME``) is not a stray.

An OSError of the store (the lock, a read under it, a write, a sync, the hard link, a replace) is a six-field refusal, never
a raised error: ``KV_STORAGE_ENDPOINT_HARDLINK_UNSUPPORTED``, ``KV_CROSSING_RECORD_STORE_WRITE_FAILED``,
``KV_CROSSING_RECORD_STORE_LOCK_FAILED``, ``KV_CROSSING_RECORD_STORE_READ_FAILED``, ``KV_CROSSING_RECEIPT_FILE_ALREADY_PRESENT``.
The refusal names the exact step (``stopped_at``: write_receipt, sync_receipt, link_receipt, write_head_json, sync_head_json,
replace_head_json, write_head_record, sync_head_record, replace_head_record, open_lock, flock, read_plan, read_under_lock,
read_head_record) and states the chain as it really is (``chain_state``, ``receipt_file_written``, ``head_json_written``,
``head_record_written``, ``ledger_written`` true only once HEAD.json names the receipt):
* UNCHANGED: nothing reached the chain; a retry at the same supplied epoch writes the record.
* ORPHAN_RECEIPT_FILE_ONLY: the receipt file is on disk, HEAD.json and the head record are not; a retry at the same epoch
  adopts it, a retry at any other epoch is refused as a non-adoptable orphan.
* HEAD_JSON_AHEAD_OF_HEAD_RECORD: HEAD.json names the new receipt and the head record lacks it; NO retry at any epoch
  writes or adopts anything, every call is refused KV_LEDGER_HEAD_ROLLBACK_DETECTED until the owner repairs the head record.
The head record is read before anything is written, so that read can never leave a half-written chain.

What this does not do (each is a refusal or simply absent):
* It never touches an Org ledger or an Org's organization-ledger ref (KV's ledger is its own); the Org's side is read
  only by ``kv_receipt_ledgers.ORG_CROSSING_READER``, which stays refuse-only.
* No hop inside one org: the path_id must be a designated ``<source>->STEGVERSE_KV:<location>:intr-destination`` path
  with a source that is not KV itself.
* The SKAP chain is reached only from inside KV (KV_INTERNAL_SKAP_GATE, no InTr hop): ``skap_vault`` is refused.
* No key handling: the appended head is signed by the published kv_ledger_head_signer, never here, so until that
  attestation is published the reader still refuses (KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED / _NOT_AUTHENTICATED).
* No clock (the epoch is supplied: ASCII [0-9]+, >= 32), no network, no dispatch, no new dependency.
* KV #2 is PENDING_INTERLOCK_INTR and the genesis is not pinned, so production is six-field FAIL_CLOSED before anything
  is read or written. The Org->KV intr-destination path_ids are designated by the contract
  (``org_crossing_cross_check.path_ids``), not by this module; this module only refuses a path_id the contract does not designate.
"""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from runtime import kv_receipt_ledgers as rl
from runtime import kv_supplied_epoch as _supplied_epoch

ALLOW, FAIL_CLOSED = rl.ALLOW, rl.FAIL_CLOSED
CROSSING_CLASS = rl.INGRESS_CLASS                       # INTR_MESH_PATH_INGRESS: the existing InTr class, none minted
RECEIPT_SCHEMA = "stegverse.repo-transition-receipt/v1"
EVIDENCE_SCHEMA = "stegverse.intr-path-ingress-evidence/v1"
#: A boundary_evidence label (not a transition class) for KV's end; the Org's end is ORGANIZATION_INTR_DESTINATION_INGRESS.
OPERATION = "KV_INTR_DESTINATION_INGRESS"
CROSSING_KEYS = ("path_id", "communication_id", "source_repository_receipt_sha256")
ALREADY_RECORDED_CODE = "INTR_PATH_DESTINATION_CROSSING_ALREADY_RECORDED"
UNREADABLE_CODE = "KV_CROSSING_RECEIPT_FILE_UNREADABLE"
ORPHAN_CODE = "INTR_PATH_DESTINATION_CROSSING_ORPHAN_RECEIPT_NOT_ADOPTABLE"
RIGEL_RULE = ('Rigel, 2026-10-29 3:08 PM CDT (Lane B\'s chat, relayed at StegVerse-org/.github#162 c6508050206): '
              '"This shouldn\'t be possible without being a literal duplicate."')
GOAL = ("StegVerse-org/.github#162 (KV-side crossing records, LC-KV-29 c6394603737; Lane B owns the Org side, "
        "StegVerse-org/.github#261); " + rl.TASK)
RETRY = ("runtime.kv_crossing_records.plan_crossing_record('kv', <designated storage endpoint adapter>, <readback root>, "
         "{path_id, communication_id, source_repository_receipt_sha256}, hb_epoch=<SUPPLIED_HB_EPOCH>); "
         "append_crossing_record takes the same arguments")
HARDLINK_CODE = "KV_STORAGE_ENDPOINT_HARDLINK_UNSUPPORTED"
WRITE_FAILED_CODE = "KV_CROSSING_RECORD_STORE_WRITE_FAILED"
LOCK_FAILED_CODE = "KV_CROSSING_RECORD_STORE_LOCK_FAILED"
READ_FAILED_CODE = "KV_CROSSING_RECORD_STORE_READ_FAILED"
FILE_PRESENT_CODE = "KV_CROSSING_RECEIPT_FILE_ALREADY_PRESENT"
TEMP_PREFIX = ".kv-crossing-"
LOCK_NAME = ".kv-crossing-append.lock"                    # beside the chain's location, never inside it


def _refuse(which: str, code: str, klass: str, predicate: str, repair: str, next_attempt: str, detail: str,
            **extra: Any) -> dict[str, Any]:
    return {**rl._refuse(which, code, klass, repair, next_attempt, detail, owner=GOAL, predicate=predicate, retry=RETRY),
            **extra}


def crossing_key(path_id: Any, communication_id: Any) -> tuple[Any, Any]:
    """The identity of one crossing: its path and its communication (the Org side keys it the same way)."""
    return path_id, communication_id


def _bad_input(which: str, detail: str) -> dict[str, Any]:
    return _refuse(which, "KV_CROSSING_INPUT_INVALID", "C", "KV_CROSSING_RECORD_NAMES_ONE_DESIGNATED_CROSSING",
                   "exactly {path_id, communication_id, source_repository_receipt_sha256}: a designated "
                   "<source>-><KV>:<location>:intr-destination path_id, a non-empty communication_id, and the Org's "
                   "record by digest (sha256:<64 hex>), never a body or a copy",
                   "on the corrected call", detail)


def _crossing_failure(which: str, d: Mapping[str, Any], crossing: Any) -> dict[str, Any] | None:
    if not isinstance(crossing, Mapping) or set(crossing) != set(CROSSING_KEYS):
        return _bad_input(which, f"the crossing is not exactly {list(CROSSING_KEYS)}")
    pid, cid, digest = (crossing[k] for k in CROSSING_KEYS)
    if not isinstance(pid, str) or not isinstance(cid, str) or not cid.strip() or cid != cid.strip() or len(cid) > 200:
        return _bad_input(which, "path_id and communication_id must be strings (communication_id non-empty, trimmed)")
    if not rl._is_sha(digest):
        return _bad_input(which, f"source_repository_receipt_sha256 {digest!r} is not sha256:<64 hex>")
    declared = d["ledger_designation"]["rollback_watermark_source"]["org_crossing_cross_check"]["path_ids"]
    suffix = f"->{rl.KV_REPOSITORY}:{d['storage_location']}{rl.PATH_ID_SUFFIX}"
    source = pid[:-len(suffix)] if pid.endswith(suffix) else ""
    if pid not in declared or not source or ":" in source or "->" in source:
        return _refuse(which, "KV_CROSSING_PATH_NOT_DESIGNATED", "C", "ONE_CROSSING_BETWEEN_DISTINCT_PARTIES",
                       f"a path_id the contract designates, of the form <source>{suffix}, from a source other than KV",
                       "on a path designated by an admitted change that re-pins the contract digest",
                       f"{pid!r} is not designated for {d['location']} (designated: {sorted(declared)})")
    if source == rl.KV_REPOSITORY or source.startswith(rl.KV_REPOSITORY):
        return _refuse(which, "KV_CROSSING_WITHIN_ONE_PARTY_REFUSED", "C", "ONE_CROSSING_BETWEEN_DISTINCT_PARTIES",
                       "a source that is not KV itself: InTr runs only between distinct ledger-holding parties",
                       "never: there is no InTr hop inside one party", f"{pid!r} has KV on both ends")
    return None


def _evidence(d: Mapping[str, Any], crossing: Mapping[str, Any]) -> dict[str, Any]:
    pid, cid = crossing["path_id"], crossing["communication_id"]
    return {"schema": EVIDENCE_SCHEMA, "path_id": pid, "communication_id": cid,
            "source_repository_receipt_sha256": crossing["source_repository_receipt_sha256"],
            "destination_location": d["location"],
            "boundary_evidence": {"operation": OPERATION, "path_id": pid, "communication_id": cid}}


def _recorded_for(chain: list[dict[str, Any]], crossing: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every receipt already on the chain for this crossing: the same (path_id, communication_id), or the same Org record."""
    hits = []
    for r in chain:
        if r.get("transition_class") not in rl.CROSSING_CLASSES:
            continue
        ev = r.get("evidence") if isinstance(r.get("evidence"), Mapping) else {}
        be = ev.get("boundary_evidence") if isinstance(ev.get("boundary_evidence"), Mapping) else {}
        same_key = crossing_key(ev.get("path_id", be.get("path_id")),
                                ev.get("communication_id", be.get("communication_id"))) \
            == crossing_key(crossing["path_id"], crossing["communication_id"])
        peer = ev.get("source_repository_receipt_sha256") or ev.get("organization_receipt_sha256")
        if same_key or (peer is not None and peer == crossing["source_repository_receipt_sha256"]):
            hits.append(r)
    return hits


def _already_recorded(which: str, d: Mapping[str, Any], crossing: Mapping[str, Any], hits: list[dict[str, Any]],
                      evidence: Mapping[str, Any]) -> dict[str, Any]:
    literal = [r["receipt_sha256"] for r in hits if r.get("evidence") == evidence]
    return _refuse(which, ALREADY_RECORDED_CODE, "C", "EACH_CROSSING_HAS_EXACTLY_ONE_KV_SIDE_RECEIPT",
                   f"none: crossing {crossing['path_id']}@{crossing['communication_id']} already has its one KV-side "
                   f"receipt {hits[0]['receipt_sha256']}; a later record for it is a duplicate and grants nothing "
                   "(there is no newest-wins, replacement or successor policy). " + RIGEL_RULE,
                   "never: a recorded crossing is not recorded again; a different crossing has a different "
                   "communication_id", f"{d['location']} already holds {[r['receipt_sha256'] for r in hits]} for this "
                   f"crossing" + (f"; a literal duplicate of {literal[0]}" if literal else "; not a literal duplicate"),
                   existing_receipt_sha256=hits[0]["receipt_sha256"], appended=False)


def _orphans(which: str, d: Mapping[str, Any], root: Path, chain: list[dict[str, Any]], hne: Any,
             crossing: Mapping[str, Any]) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any] | None]:
    """Receipt files under receipts/ that are not on the chain and are for this crossing (a crash between the receipt
    write and the HEAD.json update leaves one). A file that cannot be read as a receipt of its own name is refused:
    it might be this crossing's, and a retry could not show otherwise."""
    chained = {r["receipt_sha256"] for r in chain}
    found = []
    for path in sorted((root / "receipts").glob("*.json")):
        if path.name.startswith(TEMP_PREFIX):                       # a temp file of this writer is never read as a receipt
            continue
        if "sha256:" + path.stem in chained:
            continue
        try:
            raw = path.read_bytes()
            receipt = json.loads(raw.decode("utf-8"))
            ok = isinstance(receipt, dict) and receipt.get("receipt_sha256") == "sha256:" + path.stem \
                and receipt["receipt_sha256"] == hne.sha({k: v for k, v in receipt.items() if k != "receipt_sha256"})
        except (OSError, ValueError, TypeError):
            ok = False
        if not ok:
            return [], _refuse(which, UNREADABLE_CODE, "C", "EACH_CROSSING_HAS_EXACTLY_ONE_KV_SIDE_RECEIPT",
                               "a receipts/ file that is a receipt of its own name, or its removal by the owner of the "
                               "chain: an unreadable file could be this crossing's orphan, and recording again could "
                               "give the crossing a second receipt file",
                               "on the owner's repair of the stray file; nothing is written or deleted here",
                               f"{d['location']}/receipts/{path.name} is not a receipt whose hash is its name",
                               appended=False)
        if _recorded_for([receipt], crossing):
            found.append((path, receipt))
    return found, None


def _orphan_refusal(which: str, d: Mapping[str, Any], crossing: Mapping[str, Any],
                    found: list[tuple[Path, dict[str, Any]]], why: str) -> dict[str, Any]:
    names = [p.name for p, _ in found]
    return _refuse(which, ORPHAN_CODE, "C", "EACH_CROSSING_HAS_EXACTLY_ONE_KV_SIDE_RECEIPT",
                   f"none: crossing {crossing['path_id']}@{crossing['communication_id']} already has an unchained "
                   f"receipt file {names} (a write that stopped before HEAD.json); it is adopted only when it is "
                   "byte-identical to the receipt this call would write and sits on the current head, otherwise a "
                   "second receipt file would exist for one crossing. " + RIGEL_RULE,
                   "the same call with the same supplied epoch and the same crossing (adopts the orphan), or the "
                   "owner's repair of the orphan file; nothing is written or deleted here",
                   f"{d['location']}: {why}", orphan_receipt_sha256=[r["receipt_sha256"] for _, r in found],
                   appended=False)


def _supplied(which: str, modules: Mapping[str, Any], hb_epoch: Any) -> dict[str, Any] | None:
    failure = _supplied_epoch.supplied_epoch_failure(hb_epoch)
    if failure:
        return _refuse(which, failure[0], "C", "SUBMISSION_CARRIES_THE_SUPPLIED_HB_EPOCH",
                       "the SUPPLIED_HB_EPOCH the record is computed with (ASCII [0-9]+, >= 32)",
                       "on the corrected call with the supplied epoch; no clock is read", failure[1])
    return None


def _plan(which: str, storage_endpoint: Any = None, readback_root: Any = None, crossing: Any = None,
          hb_epoch: Any = None) -> dict[str, Any]:
    """The one KV-side record for ``crossing``, or a six-field refusal. Pure: writes nothing, reads no clock, no Org ledger.

    ALLOW carries the exact receipt ``append_crossing_record`` would append (hash-linked to KV's own head) and the
    head-record entry that records the new head. Order: unknown chain; not designated; SKAP chain (inside KV only); KV #2
    PENDING_INTERLOCK_INTR; genesis not pinned; crossing input; supplied epoch; storage endpoint; read-back of KV's own
    chain (intact, KV's genesis, KV's recorded head); the crossing already recorded (duplicate)."""
    if which not in rl.RECEIPT_LEDGERS:
        return _refuse(which, "KV_RECEIPT_CHAIN_UNKNOWN", "C", "KV_CROSSING_RECORD_ON_A_DESIGNATED_KV_CHAIN",
                       f"one of {sorted(rl.RECEIPT_LEDGERS)}", "on the corrected call", f"{which!r} is not a KV receipt chain")
    d, refusal = rl.designation(which)
    if refusal:
        return refusal
    if d["via_kv_intr_only"]:
        return _refuse(which, "KV_CROSSING_RECORD_NOT_ON_THE_SKAP_CHAIN", "A", "SKAP_VAULT_REACHED_ONLY_FROM_INSIDE_KV",
                       "no Org crossing record on the SKAP chain: the SKAP Vault is reached only from inside KV through "
                       "the in-KV gate (KV_INTERNAL_SKAP_GATE), with no InTr hop", "never on this entrypoint",
                       f"{d['location']} is the SKAP chain")
    store = d["store"]
    if store["kv_request_id"] == rl.KV2_REQUEST_ID and rl.KV2_GOVERNANCE_STATE == "PENDING_INTERLOCK_INTR":
        return {**rl.kv2_pending(which), "appended": False}
    if d["expected_genesis_receipt_sha256"] is None:
        return {**rl._not_pinned(which, d["location"]), "appended": False}
    failure = _crossing_failure(which, d, crossing)
    if failure:
        return failure
    modules, why = rl._pinned()
    if modules is None:
        return _refuse(which, "PINNED_INTR_CODE_UNAVAILABLE", "C", "KV_CROSSING_RECORD_USES_THE_PINNED_INTR_CODE",
                       "the digest-pinned modules", "on re-vendor", why)
    failure = _supplied(which, modules, hb_epoch)
    if failure:
        return failure
    if getattr(storage_endpoint, "provider_id", None) != store["provider_id"] \
            or not callable(getattr(storage_endpoint, "descriptor", None)) \
            or storage_endpoint.descriptor().get("access_adapter") != store["access_adapter"]:
        return _refuse(which, "KV_STORAGE_ENDPOINT_NOT_THE_DESIGNATED_ONE", "C", "KV_CROSSING_RECORD_ON_KV_OWN_ENDPOINT",
                       f"the storage endpoint {store['provider_id']} ({store['access_adapter']}) the designation names",
                       "with the designated storage endpoint",
                       f"storage endpoint {getattr(storage_endpoint, 'provider_id', None)!r}")
    root = Path(readback_root) / store["location"] if readback_root is not None else None
    if root is None or not root.is_dir():
        return _refuse(which, "KV_RECEIPT_CHAIN_UNREADABLE", "D", "KV_CROSSING_RECORD_ON_KV_OWN_ENDPOINT",
                       f"the {store['location']} read back through the storage endpoint",
                       "on the next storage endpoint READ", f"no read-back at {root}")
    hne = modules["healthy_node_evaluator"]
    chain, failure, detail = hne.read_chain(root, d["repository"])
    if failure or not chain or chain[-1].get("transition_class") != rl.GENESIS_CLASS \
            or chain[-1]["receipt_sha256"] != d["expected_genesis_receipt_sha256"]:
        return _refuse(which, "KV_RECEIPT_CHAIN_UNREADABLE", "C", "KV_CROSSING_RECORD_ON_KV_OWN_ENDPOINT",
                       f"one KV-computed chain at {store['location']} back to the pinned {rl.GENESIS_CLASS} genesis",
                       "on an intact chain", f"{failure or 'chain does not end at the pinned genesis'} {detail}")
    recorded, failure = rl._recorded_head(which, root, chain, hne)
    if failure:
        return failure
    if recorded != chain[0]["receipt_sha256"]:
        return rl._rollback(which, f"KV recorded {recorded}; the read-back head is {chain[0]['receipt_sha256']}")
    evidence = _evidence(d, crossing)
    hits = _recorded_for(chain, crossing)
    if hits:
        return _already_recorded(which, d, crossing, hits, evidence)
    head = chain[0]
    hb_prev = head.get("hb_reference") if isinstance(head.get("hb_reference"), Mapping) else {}
    if str(hb_prev.get("epoch", "")).isdigit() and int(str(hb_prev["epoch"])) > int(str(hb_epoch)):
        return _refuse(which, "HB_EPOCH_INVALID", "C", "SUBMISSION_CARRIES_THE_SUPPLIED_HB_EPOCH",
                       "a supplied epoch not older than KV's newest recorded receipt", "on the corrected call",
                       f"hb_epoch {hb_epoch} is older than KV's head epoch {hb_prev['epoch']}")
    hb = {"epoch": str(hb_epoch), "derived_from_clock": False}
    body = {"schema": RECEIPT_SCHEMA, "repository": d["repository"],
            "transition_id": f"{CROSSING_CLASS}:{crossing['path_id']}@{crossing['communication_id']}",
            "transition_class": CROSSING_CLASS, "predecessor_state_sha256": head["receipt_sha256"],
            "successor_state_sha256": hne.sha(evidence), "evidence": evidence, "authority_effect": "NONE",
            "hb_reference": hb, "observed_at": _supplied_epoch.observed_at_from_hb_reference(hb),
            "observed_at_is_descriptive_not_ordering": True, "previous_receipt_sha256": head["receipt_sha256"]}
    receipt = {**body, "receipt_sha256": hne.sha(body)}
    orphans, failure = _orphans(which, d, root, chain, hne, crossing)
    if failure:
        return failure
    adopts = False
    if orphans:
        path, found = orphans[0]
        if len(orphans) > 1:
            return _orphan_refusal(which, d, crossing, orphans, "more than one unchained receipt file for this crossing")
        if path.read_bytes() != json.dumps(receipt).encode("utf-8"):
            return _orphan_refusal(which, d, crossing, orphans,
                                   f"the unchained receipt {found['receipt_sha256']} is not byte-identical to the "
                                   f"receipt {receipt['receipt_sha256']} this call would write on head "
                                   f"{head['receipt_sha256']} (a different epoch, predecessor or content)")
        adopts = True
    previous = None
    for line in (root / rl.HEAD_RECORD).read_text(encoding="utf-8").splitlines():
        previous = json.loads(line)["record_sha256"]
    entry_body = {"schema": rl.HEAD_RECORD_SCHEMA, "head_receipt_sha256": receipt["receipt_sha256"],
                  "previous_record_sha256": previous}
    entry = {**entry_body, "record_sha256": hne.sha(entry_body)}
    return {"disposition": ALLOW, "receipt_ledger": which, "crossing": dict(crossing), "receipt": receipt,
            "receipt_sha256": receipt["receipt_sha256"], "previous_receipt_sha256": head["receipt_sha256"],
            "head_record_entry": entry, "location": d["location"], "store_location": d["store_location"],
            "signed_by_this_module": False, "ledger_written": False, "appended": False, "authority_effect": "NONE",
            "adopts_orphan_receipt": adopts}


def stray_temp_files(which: str, readback_root: Any) -> list[str]:
    """The ``.kv-crossing-*`` temp files (other than the writer's lock) a hard kill may have left beside the chain root, at
    the chain's location, or in receipts/, as paths relative to the read-back root. Read-only: nothing is opened or deleted."""
    if readback_root is None or which not in rl.RECEIPT_LEDGERS:
        return []
    base = Path(readback_root)
    where = base / rl.RECEIPT_LEDGERS[which]["storage_location"]
    try:
        names = [p for folder in (base, where, where / "receipts") if folder.is_dir()
                 for p in folder.iterdir() if p.name.startswith(TEMP_PREFIX) and p.name != LOCK_NAME]
        return sorted(p.relative_to(base).as_posix() for p in names)
    except OSError:
        return []


def _with_strays(which: str, readback_root: Any, out: dict[str, Any]) -> dict[str, Any]:
    strays = stray_temp_files(which, readback_root)
    out = {**out, "stray_temp_files": strays}
    if strays and out.get("disposition") != ALLOW and isinstance(out.get("detail"), str):
        out["detail"] += (f"; operator: {len(strays)} stray {TEMP_PREFIX}* temp file(s) present, not read as receipts and "
                          f"not deleted by this writer: {strays}")
    return out


def plan_crossing_record(which: str, storage_endpoint: Any = None, readback_root: Any = None, crossing: Any = None,
                         hb_epoch: Any = None) -> dict[str, Any]:
    """The one KV-side record for ``crossing``, or a six-field refusal; see ``_plan`` for the order of the checks. Pure:
    writes nothing, reads no clock, no Org ledger. Every result carries ``stray_temp_files`` (a refusal also names them in
    its ``detail``): ``.kv-crossing-*`` temp files a hard kill left. They are ignored, never read as receipts, never deleted."""
    return _with_strays(which, readback_root,
                        _checked_plan("read_plan", which, storage_endpoint, readback_root, crossing, hb_epoch))


def _drop(own_temp: str) -> None:
    """Remove the temp file this call itself just made (never anything else); if that fails it stays and is reported as stray."""
    try:
        os.unlink(own_temp)
    except OSError:
        pass


class StoreWriteFailed(Exception):
    """A store operation of this writer failed with an OSError. ``stage`` names the exact step (write_receipt, sync_receipt,
    link_receipt, write_head_json, sync_head_json, replace_head_json, write_head_record, sync_head_record,
    replace_head_record, open_lock, flock, read_plan, read_under_lock, read_head_record); ``kind`` is write, lock or read;
    the cause is the OSError. The public entry points turn it into a six-field refusal; it never reaches the caller."""

    def __init__(self, stage: str, cause: OSError, kind: str = "write") -> None:
        super().__init__(f"{stage}: {cause!r}")
        self.stage, self.cause, self.kind = stage, cause, kind


def _stage_temp(text: str, tmp_dir: Path, label: str) -> str:
    """Write ``text`` to a synced temp file in ``tmp_dir`` and return its path; the temp is removed if a stage fails."""
    try:
        fd, tmp = tempfile.mkstemp(dir=tmp_dir, prefix=TEMP_PREFIX)
    except OSError as error:
        raise StoreWriteFailed(f"write_{label}", error) from error
    stage = f"write_{label}"
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            stage = f"sync_{label}"
            os.fsync(handle.fileno())
    except OSError as error:
        _drop(tmp)                                         # this call's own temp file, made a moment ago
        raise StoreWriteFailed(stage, error) from error
    return tmp


def _put(path: Path, text: str, tmp_dir: Path, label: str) -> None:
    """Replace ``path`` (HEAD.json or the head record; ``label`` is head_json or head_record) whole or not at all."""
    tmp = _stage_temp(text, tmp_dir, label)
    try:
        os.replace(tmp, path)
    except OSError as error:
        _drop(tmp)
        raise StoreWriteFailed(f"replace_{label}", error) from error


def _put_new(path: Path, text: str, tmp_dir: Path) -> None:
    """Create the receipt ``path`` whole or not at all: written and synced beside it, then linked into place. A name that
    already exists is an error (never an overwrite), and a stop part-way leaves no half-written receipt file. An OSError of
    the store is raised as StoreWriteFailed (stage write_receipt, sync_receipt or link_receipt)."""
    tmp = _stage_temp(text, tmp_dir, "receipt")
    try:
        os.link(tmp, path)
    except OSError as error:
        raise StoreWriteFailed("link_receipt", error) from error
    finally:
        _drop(tmp)


class _Progress:
    """What this call has put on the chain so far: the receipt file (written by this call or adopted), then HEAD.json."""

    def __init__(self) -> None:
        self.receipt_file = False
        self.head_json = False

    @property
    def chain_state(self) -> str:
        if self.head_json:
            return "HEAD_JSON_AHEAD_OF_HEAD_RECORD"
        return "ORPHAN_RECEIPT_FILE_ONLY" if self.receipt_file else "UNCHANGED"


_STATE_FACTS = {
    "UNCHANGED": ("nothing of this record reached the chain (no receipt file, HEAD.json and head record unchanged)",
                  "on the next call at the same supplied epoch, once the store takes the operation: the record is then written",
                  "a store that takes the operation; nothing was signed or dispatched"),
    "ORPHAN_RECEIPT_FILE_ONLY": (
        "the receipt file is on disk; HEAD.json and the head record are unchanged, so it is an unchained orphan",
        "on the next call at the same supplied epoch, once the store takes the write: the byte-identical orphan is adopted and "
        "only HEAD.json and the head record are written; a call at any other epoch is refused "
        "INTR_PATH_DESTINATION_CROSSING_ORPHAN_RECEIPT_NOT_ADOPTABLE until the owner repairs it",
        "a store that takes the write; nothing was signed or dispatched"),
    "HEAD_JSON_AHEAD_OF_HEAD_RECORD": (
        "the receipt file and HEAD.json are written (HEAD.json names the new receipt); the head record does not yet hold it",
        "none by this writer: every call at any epoch is refused KV_LEDGER_HEAD_ROLLBACK_DETECTED until the owner repairs the "
        "head record (or decides to complete it); nothing is adopted and no retry writes",
        "the owner's repair of KV's head record so it names the receipt HEAD.json holds, then a re-read of the chain; "
        "this writer does not repair, move or delete anything"),
}


def _store_failure(which: str, failed: StoreWriteFailed, progress: _Progress | None = None) -> dict[str, Any]:
    """The six-field refusal for a store error, stating the chain as it really is after the failure (``progress``)."""
    progress = progress or _Progress()
    cause, state = failed.cause, progress.chain_state
    facts, next_attempt, repair = _STATE_FACTS[state]
    if failed.kind == "lock":
        code, klass = LOCK_FAILED_CODE, "D"
    elif failed.kind == "read":
        code, klass = READ_FAILED_CODE, "D"
    elif failed.stage == "link_receipt" and isinstance(cause, FileExistsError):
        code, klass = FILE_PRESENT_CODE, "C"
        repair = "the owner's check of the receipt file that already holds this name; nothing is overwritten or deleted here"
    elif failed.stage == "link_receipt":
        code, klass = HARDLINK_CODE, "D"
        repair = "a designated storage endpoint that supports hard links (the receipt file is linked into place whole or not at all)"
    else:
        code, klass = WRITE_FAILED_CODE, "D"
    where = (rl.RECEIPT_LEDGERS.get(which) or {}).get("storage_location")
    lock_note = "; an empty lock file may exist beside the chain root" if failed.kind == "lock" else ""
    predicate = ("KV_HEAD_RECORD_NAMES_THE_RECEIPT_HEAD_JSON_HOLDS" if state == "HEAD_JSON_AHEAD_OF_HEAD_RECORD"
                 else "EACH_CROSSING_HAS_EXACTLY_ONE_KV_SIDE_RECEIPT_ON_A_STORE_THAT_TAKES_THE_OPERATION")
    return _refuse(which, code, klass, predicate, repair,
                   next_attempt,
                   f"{where}: {failed.stage} failed with {cause.__class__.__name__} errno={getattr(cause, 'errno', None)} "
                   f"({cause.strerror if getattr(cause, 'strerror', None) else cause}); chain state {state}: {facts}{lock_note}",
                   appended=False, stopped_at=failed.stage, chain_state=state,
                   receipt_file_written=progress.receipt_file, head_json_written=progress.head_json,
                   head_record_written=False) | {"ledger_written": progress.head_json}


def _checked_plan(stage: str, which: str, storage_endpoint: Any, readback_root: Any, crossing: Any,
                  hb_epoch: Any) -> dict[str, Any]:
    """_plan with an OSError of a read turned into the six-field refusal (``stage`` says where it was read from)."""
    try:
        return _plan(which, storage_endpoint, readback_root, crossing, hb_epoch)
    except OSError as error:
        return _store_failure(which, StoreWriteFailed(stage, error, "read"))


def append_crossing_record(which: str, storage_endpoint: Any = None, readback_root: Any = None, crossing: Any = None,
                           hb_epoch: Any = None) -> dict[str, Any]:
    """Append the one KV-side record for ``crossing`` to KV's own chain, or return the plan's six-field refusal.

    The plan is made twice: once outside, and again under an exclusive lock held across the write, so a concurrent
    writer for the same crossing is refused as a duplicate after the first one lands. A first record is written as
    receipts/<hex>.json (whole or not at all, never over a name), then HEAD.json, then KV's head record. A crash after
    the receipt and before HEAD.json leaves an orphan; a retry adopts it only if it is byte-identical to the receipt it
    would write (same epoch, on the current head), otherwise it is refused: a crossing never has two receipt files. A
    stop after HEAD.json and before the head record leaves HEAD.json ahead of the head record: every later call is refused
    KV_LEDGER_HEAD_ROLLBACK_DETECTED until the owner repairs the head record. Nothing else is written. Nothing
    here signs the head. Where the designated endpoint is KV #2 (PENDING_INTERLOCK_INTR) this is refused before any read
    or write. An OSError of the store (lock, read, write, sync, link, replace) is a six-field refusal that states the chain
    as it is, never a raised error."""
    first = plan_crossing_record(which, storage_endpoint, readback_root, crossing, hb_epoch)
    if first["disposition"] != ALLOW:
        return first
    d = rl.designation(which)[0]
    store = d["store"]
    root = Path(readback_root) / store["location"]
    lock = Path(readback_root) / LOCK_NAME
    progress = _Progress()
    try:
        handle = open(lock, "a+", encoding="utf-8")
    except OSError as error:
        return _with_strays(which, readback_root, _store_failure(which, StoreWriteFailed("open_lock", error, "lock")))
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX)
        except OSError as error:
            return _with_strays(which, readback_root, _store_failure(which, StoreWriteFailed("flock", error, "lock")))
        try:
            plan = _with_strays(which, readback_root,
                                _checked_plan("read_under_lock", which, storage_endpoint, readback_root, crossing, hb_epoch))
            if plan["disposition"] != ALLOW:
                return plan
            receipt, entry = plan["receipt"], plan["head_record_entry"]
            target = root / "receipts" / (receipt["receipt_sha256"][7:] + ".json")
            try:
                records = (root / rl.HEAD_RECORD).read_text(encoding="utf-8")      # read before anything is written
            except OSError as error:
                return _with_strays(which, readback_root,
                                    _store_failure(which, StoreWriteFailed("read_head_record", error, "read")))
            try:
                if not plan["adopts_orphan_receipt"]:
                    _put_new(target, json.dumps(receipt), Path(readback_root))
                progress.receipt_file = True
                _put(root / "HEAD.json", json.dumps({"receipt_sha256": receipt["receipt_sha256"]}), Path(readback_root),
                     "head_json")
                progress.head_json = True
                _put(root / rl.HEAD_RECORD, records + json.dumps(entry) + "\n", Path(readback_root), "head_record")
            except StoreWriteFailed as failed:
                return _with_strays(which, readback_root, _store_failure(which, failed, progress))
        finally:
            try:
                fcntl.flock(handle, fcntl.LOCK_UN)
            except OSError:
                pass                                       # closing the handle releases the lock
    return {**plan, "ledger_written": True, "appended": True, "head_receipt_sha256": receipt["receipt_sha256"]}


__all__ = ["FILE_PRESENT_CODE", "HARDLINK_CODE", "LOCK_FAILED_CODE", "READ_FAILED_CODE", "UNREADABLE_CODE", "WRITE_FAILED_CODE", "StoreWriteFailed", "stray_temp_files",
           "ALREADY_RECORDED_CODE", "ORPHAN_CODE", "CROSSING_CLASS", "CROSSING_KEYS", "OPERATION", "append_crossing_record",
           "crossing_key", "plan_crossing_record"]
