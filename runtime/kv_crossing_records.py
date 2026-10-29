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
successor policy, and the check is made again under the append lock, so two writers cannot both record it.

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
  is read or written. No Org->KV intr-destination path_id is declared by this module.
"""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from runtime import kv_receipt_ledgers as rl

ALLOW, FAIL_CLOSED = rl.ALLOW, rl.FAIL_CLOSED
CROSSING_CLASS = rl.INGRESS_CLASS                       # INTR_MESH_PATH_INGRESS: the existing InTr class, none minted
RECEIPT_SCHEMA = "stegverse.repo-transition-receipt/v1"
EVIDENCE_SCHEMA = "stegverse.intr-path-ingress-evidence/v1"
#: A boundary_evidence label (not a transition class) for KV's end; the Org's end is ORGANIZATION_INTR_DESTINATION_INGRESS.
OPERATION = "KV_INTR_DESTINATION_INGRESS"
CROSSING_KEYS = ("path_id", "communication_id", "source_repository_receipt_sha256")
ALREADY_RECORDED_CODE = "INTR_PATH_DESTINATION_CROSSING_ALREADY_RECORDED"
RIGEL_RULE = ('Rigel, 2026-10-29 3:08 PM CDT (Lane B\'s chat, relayed at StegVerse-org/.github#162 c6508050206): '
              '"This shouldn\'t be possible without being a literal duplicate."')
GOAL = ("StegVerse-org/.github#162 (KV-side crossing records, LC-KV-29 c6394603737; Lane B owns the Org side, "
        "StegVerse-org/.github#261); " + rl.TASK)
RETRY = ("runtime.kv_crossing_records.plan_crossing_record('kv', <designated storage endpoint adapter>, <readback root>, "
         "{path_id, communication_id, source_repository_receipt_sha256}, hb_epoch=<SUPPLIED_HB_EPOCH>); "
         "append_crossing_record takes the same arguments")
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


def _supplied(which: str, modules: Mapping[str, Any], hb_epoch: Any) -> dict[str, Any] | None:
    failure = modules["supplied_epoch"].supplied_epoch_failure(hb_epoch)
    if failure:
        return _refuse(which, failure[0], "C", "SUBMISSION_CARRIES_THE_SUPPLIED_HB_EPOCH",
                       "the SUPPLIED_HB_EPOCH the record is computed with (ASCII [0-9]+, >= 32)",
                       "on the corrected call with the supplied epoch; no clock is read", failure[1])
    return None


def plan_crossing_record(which: str, storage_endpoint: Any = None, readback_root: Any = None, crossing: Any = None,
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
            "hb_reference": hb, "observed_at": modules["supplied_epoch"].observed_at_from_hb_reference(hb),
            "observed_at_is_descriptive_not_ordering": True, "previous_receipt_sha256": head["receipt_sha256"]}
    receipt = {**body, "receipt_sha256": hne.sha(body)}
    previous = None
    for line in (root / rl.HEAD_RECORD).read_text(encoding="utf-8").splitlines():
        previous = json.loads(line)["record_sha256"]
    entry_body = {"schema": rl.HEAD_RECORD_SCHEMA, "head_receipt_sha256": receipt["receipt_sha256"],
                  "previous_record_sha256": previous}
    entry = {**entry_body, "record_sha256": hne.sha(entry_body)}
    return {"disposition": ALLOW, "receipt_ledger": which, "crossing": dict(crossing), "receipt": receipt,
            "receipt_sha256": receipt["receipt_sha256"], "previous_receipt_sha256": head["receipt_sha256"],
            "head_record_entry": entry, "location": d["location"], "store_location": d["store_location"],
            "signed_by_this_module": False, "ledger_written": False, "appended": False, "authority_effect": "NONE"}


def _put(path: Path, text: str, tmp_dir: Path) -> None:
    fd, tmp = tempfile.mkstemp(dir=tmp_dir, prefix=".kv-crossing-")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def append_crossing_record(which: str, storage_endpoint: Any = None, readback_root: Any = None, crossing: Any = None,
                           hb_epoch: Any = None) -> dict[str, Any]:
    """Append the one KV-side record for ``crossing`` to KV's own chain, or return the plan's six-field refusal.

    The plan is made twice: once outside, and again under an exclusive lock held across the write, so a concurrent
    writer for the same crossing is refused as a duplicate after the first one lands. A first record is written as
    receipts/<hex>.json (created exclusively), then HEAD.json, then KV's head record. Nothing else is written. Nothing
    here signs the head. Where the designated endpoint is KV #2 (PENDING_INTERLOCK_INTR) this is refused before any read
    or write."""
    first = plan_crossing_record(which, storage_endpoint, readback_root, crossing, hb_epoch)
    if first["disposition"] != ALLOW:
        return first
    store = rl.designation(which)[0]["store"]
    root = Path(readback_root) / store["location"]
    lock = Path(readback_root) / LOCK_NAME
    with open(lock, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            plan = plan_crossing_record(which, storage_endpoint, readback_root, crossing, hb_epoch)
            if plan["disposition"] != ALLOW:
                return plan
            receipt, entry = plan["receipt"], plan["head_record_entry"]
            target = root / "receipts" / (receipt["receipt_sha256"][7:] + ".json")
            with open(target, "x", encoding="utf-8") as out:       # exclusive: a collision is an error, never an overwrite
                out.write(json.dumps(receipt))
            _put(root / "HEAD.json", json.dumps({"receipt_sha256": receipt["receipt_sha256"]}), Path(readback_root))
            records = (root / rl.HEAD_RECORD).read_text(encoding="utf-8")
            _put(root / rl.HEAD_RECORD, records + json.dumps(entry) + "\n", Path(readback_root))
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
    return {**plan, "ledger_written": True, "appended": True, "head_receipt_sha256": receipt["receipt_sha256"]}


__all__ = ["ALREADY_RECORDED_CODE", "CROSSING_CLASS", "CROSSING_KEYS", "OPERATION", "append_crossing_record",
           "crossing_key", "plan_crossing_record"]
