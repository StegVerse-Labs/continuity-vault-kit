"""The shared supplied-epoch rule and the observed_at rule, for receipts that must be byte-deterministic.

``supplied_epoch_failure`` is a byte copy of StegVerse-org/.github resident-runtime/organization_egress_boundary.py's
(pinned there by intr_hop.py as SUPPLIED_EPOCH_FAILURE_SHA256: sha256 of ast.get_source_segment + "\\n"), the rule
StegVerse-Labs/.github#3290 refuses with. ``observed_at_from_hb_reference`` is StegVerse-Labs/.github#3263's
(resident-runtime/aggregate_repo_transition.py), the same strings emit.py now writes. Pure: no clock is read.
"""
from __future__ import annotations

from typing import Any, Mapping

EPOCH_PREDICATE = "SUBMISSION_CARRIES_THE_SUPPLIED_HB_EPOCH"
SUPPLIED_EPOCH_FAILURE_SHA256 = "7f36f0e697cadc91acd27af121eee3fc460b887ec67cfa258727bfccec0ca5f8"


def supplied_epoch_failure(hb_epoch: Any, reference: Any = None) -> tuple[str, str] | None:
    """The shared supplied-epoch rule (SUBMISSION_CARRIES_THE_SUPPLIED_HB_EPOCH).

    Byte-identical in StegVerse-org/.github#185 and StegVerse-Labs/.github#3212
    and #3213. `hb_epoch` absent (None) is HB_EPOCH_NOT_SUPPLIED. Otherwise it
    must be ASCII [0-9]+ only -- an int is read as its decimal text; a bool, a
    float or anything coerced ('+33', ' 33', '3_3', '33.0') is refused -- with
    integer value >= 32 (the HB32 anchor). `reference`, the carrier frame's
    heartbeat reference when there is one, must be an object, and a
    `derived_from_clock` it carries must be exactly false. Any failure is
    HB_EPOCH_INVALID. Returns (failure_code, detail), or None when the epoch is
    supplied. No clock is read.
    """
    if reference is not None and not isinstance(reference, dict):
        return "HB_EPOCH_INVALID", "the carrier's heartbeat reference is not an object"
    if hb_epoch is None:
        return "HB_EPOCH_NOT_SUPPLIED", "no hb_epoch was supplied and no clock is read"
    if isinstance(hb_epoch, bool):
        text = None
    elif isinstance(hb_epoch, int):
        text = str(hb_epoch)
    elif isinstance(hb_epoch, str):
        text = hb_epoch
    else:
        text = None
    if text is None or not text.isascii() or not text.isdigit():
        return "HB_EPOCH_INVALID", "hb_epoch " + repr(hb_epoch) + " is not ASCII [0-9]+"
    if int(text) < 32:
        return "HB_EPOCH_INVALID", "hb_epoch " + text + " is below the HB32 anchor (32)"
    if reference is not None and "derived_from_clock" in reference \
            and reference["derived_from_clock"] is not False:
        return "HB_EPOCH_INVALID", ("the carrier's derived_from_clock is not exactly false; "
                                    "a clock-derived epoch is not a supplied one")
    return None


def observed_at_from_hb_reference(hb: Mapping[str, Any]) -> str:
    """StegVerse-Labs/.github#3263's rule (also emit.py's): SUPPLIED_HB_EPOCH:<epoch>, or HB_EPOCH_DERIVED_FROM_CLOCK."""
    epoch = hb.get("epoch")
    return ("HB_EPOCH_DERIVED_FROM_CLOCK:%s" if hb.get("derived_from_clock") is True else "SUPPLIED_HB_EPOCH:%s") % epoch


def record_epoch_failure(record: Any) -> tuple[str, str] | None:
    """Why a recorded receipt does not carry a supplied epoch, or None. Its hb_reference must pass the shared rule,
    and an observed_at it carries must be SUPPLIED_HB_EPOCH:<epoch>. Pure."""
    hb = record.get("hb_reference") if isinstance(record, Mapping) else None
    failure = supplied_epoch_failure(hb.get("epoch") if isinstance(hb, dict) else None, hb)
    if failure:
        return failure
    if "observed_at" in record and record["observed_at"] != observed_at_from_hb_reference(hb):
        return "HB_EPOCH_INVALID", (f"observed_at {record['observed_at']!r} is not "
                                    f"{observed_at_from_hb_reference(hb)!r}")
    return None
