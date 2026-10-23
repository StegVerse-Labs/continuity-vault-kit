#!/usr/bin/env python3
"""Append this repository's transition receipts, serialized and heartbeat-ordered.

Two defects made this ledger unusable as the record of ingress.

It published HEAD with no lock and no atomic replacement. Eight concurrent
appends produced eight receipts, five of them bound to a null predecessor -- each
believing it was genesis -- and one reachable from HEAD. The other seven were
orphaned. `StegVerse-org/.github` repaired exactly this in its own emitter; this
one never got the repair, and an HTTP ingress boundary takes concurrent arrivals
as its normal case rather than its edge case.

It also ordered by a host clock. `observed_at` was stamped unconditionally from
`datetime.now()` while `hb_reference` was an optional free-text flag, so the
chain was clock-ordered. Progression is `OSCILLATOR_ONLY`: the heartbeat
parameters are read from `.stegverse/heartbeat-awareness.json`, whose
`canonical_owner` is `StegVerse-Labs/.github`, rather than restated here. A
reference derived from a clock sample says so, so a supplied epoch and a derived
one can be told apart.

`observed_at` stays because this repository's ledger contract requires it, and it
is descriptive only -- `ordering` names what the chain is ordered by.

The lock mechanics mirror `.github`'s repaired emitter: an advisory lock around
the HEAD read and publication, a temporary file replaced atomically, and an fsync
of the file and its directory. Consolidating both repositories onto one ledger
store is worth doing and is not required to make this correct.
"""
import argparse, fcntl, hashlib, json, os, tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = json.loads((ROOT / ".stegverse/transition-ledger/contract.json").read_text())
AWARENESS = ROOT / ".stegverse/heartbeat-awareness.json"
ORDERING = "OSCILLATOR_HEARTBEAT_EPOCH_ONLY"


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(v):
    return "sha256:" + hashlib.sha256(v if isinstance(v, (bytes, bytearray)) else canon(v)).hexdigest()


def lr():
    o = os.getenv("STEGVERSE_REPO_LEDGER_ROOT")
    if o:
        return Path(o).expanduser().resolve()
    return (Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state")))
            / "stegverse/repo-ledgers" / C["repository"]).resolve()


def heartbeat_parameters():
    """The declared heartbeat, read off this repository's own awareness record.

    The parameters belong to `canonical_owner`; reading them means a change at
    the owner surfaces here instead of this file quietly disagreeing with it.
    """
    declared = json.loads(AWARENESS.read_text())["heartbeat"]
    if declared.get("progression_dependency") != "OSCILLATOR_ONLY":
        raise SystemExit("heartbeat progression must be OSCILLATOR_ONLY")
    return declared


def hb_reference(epoch=None):
    """The heartbeat reference this receipt is ordered by.

    A supplied epoch is reproducible: the same transition at the same epoch
    yields the same digest. Deriving one from a clock sample is permitted and
    marks itself, because an NTP step moves or reverses it and two nodes with
    skewed clocks would assign different epochs to one event.
    """
    p = heartbeat_parameters()
    anchor, period_ms = int(p["anchor_epoch"]), int(p["period_ms"])
    if epoch is not None:
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < anchor:
            raise SystemExit(f"epoch must be an integer of at least the anchor {anchor}")
        return {"epoch": epoch, "heartbeat_id": f"HB:{epoch}", "frequency_hz": p["rate_hz"],
                "period_ms": period_ms, "progression_dependency": "OSCILLATOR_ONLY",
                "derived_from_clock": False, "authority_effect": "NONE"}
    sampled_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    return {"epoch": anchor + sampled_ns // (period_ms * 1_000_000),
            "heartbeat_id": None, "frequency_hz": p["rate_hz"], "period_ms": period_ms,
            "progression_dependency": "OSCILLATOR_ONLY", "derived_from_clock": True,
            "sampled_unix_ns": sampled_ns, "authority_effect": "NONE"}


@contextmanager
def _exclusive(root):
    """Serialize appenders so one HEAD is read and published per append."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".append.lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


def _sync_directory(directory):
    fd = os.open(str(directory), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _put(path, value):
    """Write atomically, so a reader never sees a half-written receipt or HEAD."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".repo-append-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps(value, indent=2, sort_keys=True).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        _sync_directory(path.parent)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def append(transition_id, transition_class, predecessor_state_sha256,
           successor_state_sha256, evidence=None, authority_effect="NONE", hb_epoch=None):
    """Append one repository transition receipt and publish HEAD atomically."""
    root = lr()
    with _exclusive(root):
        head_path = root / "HEAD.json"
        prev = json.loads(head_path.read_text()).get("receipt_sha256") if head_path.is_file() else None
        body = {"schema": "stegverse.repo-transition-receipt/v1",
                "repository": C["repository"],
                "transition_id": transition_id,
                "transition_class": transition_class,
                "predecessor_state_sha256": predecessor_state_sha256,
                "successor_state_sha256": successor_state_sha256,
                "evidence": evidence if evidence is not None else {},
                "authority_effect": authority_effect,
                "hb_reference": hb_reference(hb_epoch),
                "ordering": ORDERING,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "observed_at_is_descriptive_not_ordering": True,
                "previous_receipt_sha256": prev}
        digest = sha(body)
        receipt = {**body, "receipt_sha256": digest}
        path = root / "receipts" / (digest.split(":", 1)[1] + ".json")
        if path.is_file() and json.loads(path.read_text()) != receipt:
            raise SystemExit("receipt collision")
        if not path.is_file():
            _put(path, receipt)
        _put(head_path, {"repository": C["repository"], "receipt_sha256": digest,
                         "receipt_path": str(path)})
        return receipt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--transition-id", required=True)
    p.add_argument("--transition-class", required=True)
    p.add_argument("--predecessor-state-sha256", required=True)
    p.add_argument("--successor-state-sha256", required=True)
    p.add_argument("--evidence-json", default="{}")
    p.add_argument("--authority-effect", default="NONE")
    p.add_argument("--hb-epoch", type=int, default=None,
                   help="heartbeat epoch; derived from a clock sample, and marked as derived, when absent")
    a = p.parse_args()
    print(json.dumps(append(a.transition_id, a.transition_class, a.predecessor_state_sha256,
                            a.successor_state_sha256, json.loads(a.evidence_json),
                            a.authority_effect, a.hb_epoch), sort_keys=True))


if __name__ == "__main__":
    main()
