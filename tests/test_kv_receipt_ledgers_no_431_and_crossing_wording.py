"""Guard: KV's receipt-chain code, contracts, head-signers reference and ledger-location doc carry none of the retired wording.

Retired: references to StegVerse-org/LLM-adapter#431, StegVerse-org#235 and the LLM-adapter endpoint_ledger_designation module
(an LLM-adapter InTr crossing), "KV reaches the Orgs only through InTr", and any claim that the Org<->KV crossing status is
"unruled". The ruling (StegVerse-org/.github#162 c6394603737, LC-KV-29) is: KV is its own ledger-holding party, an Org<->KV
crossing is between distinct parties (never an intra-org InTr hop) and is recorded on both ledgers, KV's end required.
Wording only: no behavior change, and no Org->KV intr-destination path_id is declared by this change."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from runtime import kv_receipt_ledgers as ledgers

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = (
    ".stegverse/receipt-chains/stegverse-kv-receipts.contract.json",
    ".stegverse/receipt-chains/skap-receipts.contract.json",
)
GUARDED = ("runtime/kv_receipt_ledgers.py",) + CONTRACTS + (
    ".stegverse/node-ledger/kv-ledger-head-signers.v1.json",
    "docs/kv-skap-ledger-location.md",
)
RETIRED = (
    re.compile(r"LLM-adapter\s*#?\s*431", re.I), re.compile(r"(?<![\w/#])#431\b"),
    re.compile(r"StegVerse-org\s*#?\s*235", re.I), re.compile(r"endpoint_ledger_designation\.py", re.I),
    re.compile(r"unruled", re.I), re.compile(r"ORG_KV_CROSSING_INTR_STATUS_UNRULED"),
    re.compile(r"KV reaches the Orgs only through InTr", re.I),
    re.compile(r"(?:LLM-adapter|llm_adapter)[^.\n]{0,60}InTr (?:destination|hop|crossing)", re.I),
)
RULING = ("KV is its own ledger-holding party; an Org↔KV crossing is between distinct parties (never an intra-org hop) "
          "and is recorded on both ledgers, KV's end required (StegVerse-org/.github#162 c6394603737)")
NO_PATH_ID = "No Org→KV intr-destination path_id is declared until the KV-side crossing records are in code with tests"


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_guarded_files_carry_no_retired_reference_or_wording():
    for rel in GUARDED:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for pattern in RETIRED:
            assert not pattern.search(text), f"{rel}: retired wording matching {pattern.pattern}"


def test_crossing_is_worded_per_the_lc_kv_29_ruling_and_declares_no_org_kv_path_id():
    for rel in ("runtime/kv_receipt_ledgers.py", "docs/kv-skap-ledger-location.md"):
        text = _flat((ROOT / rel).read_text(encoding="utf-8"))
        assert RULING in text and NO_PATH_ID in text, rel
    for rel in CONTRACTS:
        body = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        text = json.dumps(body, ensure_ascii=False)
        assert RULING in text and NO_PATH_ID in text, rel
        # the pre-existing inert cross-check ids are unchanged: this change adds no Org->KV path_id
        ids = body["ledger_designation"]["rollback_watermark_source"]["org_crossing_cross_check"]["path_ids"]
        assert len(ids) == 1 and ids[0].endswith(":intr-destination"), rel


def test_refusal_text_states_the_ruling_not_a_superseded_status():
    refusal = json.dumps(ledgers.org_membership_refused("kv", "guard"), ensure_ascii=False)
    assert RULING in refusal and NO_PATH_ID in refusal
    for pattern in RETIRED:
        assert not pattern.search(refusal), pattern.pattern


def test_contract_digests_are_the_sha256_of_the_checked_in_bytes():
    for which, spec in ledgers.RECEIPT_LEDGERS.items():
        digest = "sha256:" + hashlib.sha256((ROOT / spec["contract_path"]).read_bytes()).hexdigest()
        assert spec["contract_sha256"] == digest, which
