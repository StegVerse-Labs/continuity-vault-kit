"""LC-KV-26, the Org end: runtime/org_crossing_reader.py (StegVerse-org/.github#162 c6393962100).

SKAP Vault inside KV is the only PII and credential store for every user, the ecosystem's own included; the
ecosystem holds none (HST citation pending P1 #163).
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import kv_receipt_ledgers as rl  # noqa: E402
from runtime import org_crossing_reader as ocr  # noqa: E402

A, B, C = "sha256:" + "a" * 64, "sha256:" + "b" * 64, "sha256:" + "c" * 64
PATH = "SV-011->StegVerse-org:intr-destination"
SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")


def _hb(epoch=446655631, clock=False):
    return {"epoch": epoch, "derived_from_clock": clock, "authority_effect": "NONE"}


def _receipt(prev, boundary, epoch=446655631, clock=False, holder="boundary_evidence"):
    body = {"schema": "stegverse.organization-transition-receipt/v1", "previous_receipt_sha256": prev,
            "hb_reference": _hb(epoch, clock), "authority_effect": "NONE"}
    if holder == "boundary_evidence":
        body["boundary_evidence"] = boundary
    elif holder == "evidence":
        body["evidence"] = boundary
    else:
        body["evidence"] = {"boundary_evidence": boundary}
    body["receipt_sha256"] = ocr.seal(body)
    return body


def _chain(*boundaries, **kw):
    prev, out = None, {}
    for b in boundaries:
        r = _receipt(prev, b, **kw)
        out[r["receipt_sha256"]] = r
        prev = r["receipt_sha256"]
    return prev, out


def _designation(*ids):
    return {"rollback_watermark_source": {"org_crossing_cross_check": {"path_ids": list(ids)}}}


def _write(tmp, head, receipts, meta=None):
    (tmp / "receipts").mkdir()
    (tmp / "HEAD.json").write_text(json.dumps({"receipt_sha256": head}))
    for d, r in receipts.items():
        (tmp / "receipts" / f"{d[7:]}.json").write_text(json.dumps(r, ensure_ascii=False))
    (tmp / "snapshot.json").write_text(json.dumps(meta or {"schema": ocr.SNAPSHOT_SCHEMA, "ledger_ref": ocr.LEDGER_REF,
                                                           "ledger_ref_tip": "0" * 40}))
    return tmp


def test_production_reader_is_wired_and_shares_the_record_shape():
    assert rl.ORG_CROSSING_READER is ocr.read
    assert tuple(rl.ORG_CROSSING_KEYS) == ocr.ORG_CROSSING_KEYS


@pytest.mark.parametrize("path_id,ok", [
    (PATH, True), ("StegVerse-Labs->SV-011:intr-destination", True),
    ("StegVerse-org->StegVerse-org:intr-destination", False),  # never a hop inside one org
    ("StegVerse-org->STEGVERSE_KV:_StegVerse/Receipts:intr-destination", False),  # not an org
    ("SV-011->StegVerse-org:intr-egress", False), ("SV-011:intr-destination", False), (None, False)])
def test_only_paths_between_distinct_orgs(path_id, ok):
    assert ocr.distinct_org_path(path_id) is ok


@pytest.mark.parametrize("holder", ["boundary_evidence", "evidence", "evidence.boundary_evidence"])
def test_emits_exactly_the_four_digest_only_fields(tmp_path, holder):
    head, rs = _chain({"path_id": PATH, "endpoint_head_sha256": A}, holder=holder)
    got = ocr.read(_designation(PATH), "kv", snapshot=_write(tmp_path, head, rs))
    assert got == [{"path_id": PATH, "receipt_sha256": head, "endpoint_head_sha256": A,
                    "supplied_hb_epoch": "446655631"}]
    assert ocr.LAST_READ["observed"] is True and ocr.LAST_READ["authority_effect"] == "NONE"
    assert all(rl._is_sha(r["receipt_sha256"]) and rl._epoch_ok(r["supplied_hb_epoch"]) for r in got)


def test_never_fabricates_an_endpoint_head_and_filters_to_the_designation(tmp_path):
    head, rs = _chain({"path_id": PATH, "source_organization_receipt_sha256": B},  # no endpoint head: not emitted
                      {"path_id": "StegVerse-Labs->SV-011:intr-destination", "endpoint_head_sha256": A},
                      {"path_id": "StegVerse-org->StegVerse-org:intr-destination", "endpoint_head_sha256": C},
                      {"path_id": PATH, "endpoint_head_sha256": B})
    got = ocr.read(_designation(PATH, "StegVerse-org->StegVerse-org:intr-destination"), "kv",
                   snapshot=_write(tmp_path, head, rs))
    assert [r["endpoint_head_sha256"] for r in got] == [B]


@pytest.mark.parametrize("epoch,clock", [(31, False), (446655631, True), ("446655631", False), (True, False)])
def test_clock_derived_or_low_or_non_int_epochs_are_not_emitted(tmp_path, epoch, clock):
    head, rs = _chain({"path_id": PATH, "endpoint_head_sha256": A}, epoch=epoch, clock=clock)
    assert ocr.read(_designation(PATH), "kv", snapshot=_write(tmp_path, head, rs)) == []


def _assert_six(which="kv"):
    f = ocr.LAST_READ
    assert f["disposition"] == "FAIL_CLOSED" and f["failure_code"] == "KV_CROSSING_RECORD_NOT_OBSERVED"
    assert all(isinstance(f[k], str) and f[k] for k in SIX) and f["authority_effect"] == "NONE"


def test_no_snapshot_is_none_with_six_fields(monkeypatch):
    monkeypatch.delenv(ocr.SNAPSHOT_ENV, raising=False)
    assert ocr.read(_designation(PATH), "kv") is None
    _assert_six()


def test_missing_snapshot_dir_is_none_with_six_fields(tmp_path):
    assert ocr.read(_designation(PATH), "kv", snapshot=tmp_path / "absent") is None
    _assert_six()


def test_broken_seal_is_none_with_six_fields(tmp_path):
    head, rs = _chain({"path_id": PATH, "endpoint_head_sha256": A})
    rs[head]["boundary_evidence"]["endpoint_head_sha256"] = B  # tampered after sealing
    assert ocr.read(_designation(PATH), "kv", snapshot=_write(tmp_path, head, rs)) is None
    _assert_six()


def test_broken_chain_is_none_with_six_fields(tmp_path):
    head, rs = _chain({"path_id": PATH, "endpoint_head_sha256": A}, {"path_id": PATH, "endpoint_head_sha256": B})
    first = next(d for d, r in rs.items() if r["previous_receipt_sha256"] is None)
    del rs[first]
    assert ocr.read(_designation(PATH), "kv", snapshot=_write(tmp_path, head, rs)) is None
    _assert_six()


def test_snapshot_without_observer_metadata_is_none(tmp_path):
    head, rs = _chain({"path_id": PATH, "endpoint_head_sha256": A})
    assert ocr.read(_designation(PATH), "kv", snapshot=_write(tmp_path, head, rs, meta={"schema": "x"})) is None
    _assert_six()


def test_reader_is_clock_free_and_network_free():
    tree = ast.parse((ROOT / "runtime" / "org_crossing_reader.py").read_text(encoding="utf-8"))
    names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
             for a in n.names} | {n.module.split(".")[0] for n in ast.walk(tree)
                                  if isinstance(n, ast.ImportFrom) and n.module}
    assert not names & {"socket", "subprocess", "urllib", "http", "requests", "time", "datetime", "ssl"}


def test_observer_fetch_is_anonymous():
    src = (ROOT / "tools" / "observers" / "org_ledger_observer.py").read_text(encoding="utf-8")
    for needle in ("credential.helper=", '"GIT_TERMINAL_PROMPT": "0"', '"GIT_CONFIG_NOSYSTEM": "1"', '"HOME": home'):
        assert needle in src
    assert "TOKEN" not in src and "push" not in src


@pytest.mark.parametrize("which", ["kv", "skap_vault"])
def test_designated_kv_paths_are_not_distinct_org_paths(which):
    """The KV designations' cross-check path targets STEGVERSE_KV, not an org, so the reader emits nothing for it and
    the LC-KV-26 outcome stays six-field FAIL_CLOSED, refuse-only (never an ALLOW sourced from the Org)."""
    d, refusal = rl.designation(which)
    assert refusal is None
    ids = d["ledger_designation"]["rollback_watermark_source"]["org_crossing_cross_check"]["path_ids"]
    assert ids and not any(ocr.distinct_org_path(i) for i in ids)
