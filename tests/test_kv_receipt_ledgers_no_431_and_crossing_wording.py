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


# ---- the remaining live readers (runtime, docs, KV's own test harness) and the sealed byte copies -----------------------
RETIRED_431 = tuple(p for p in RETIRED[:4])
#: the vendored module's own path is a code path KV loads and pins by digest; it is not wording
VENDORED_PATH = re.compile(r'llm_adapter/endpoint_ledger_designation\.py|"llm_adapter", "endpoint_ledger_designation\.py"')
#: the one accurate sentence that tells readers not to revive the closed route (README and the handoff mirror)
ANTI_REVIVAL = re.compile(r"Do not revive LLM-adapter #431.*?\(merge `[0-9a-f]{40}`\)\.", re.S)
WITHDRAWN_ASSERTION = re.compile(r'^.*for withdrawn in \("#431".*$', re.M)
LIVE_READERS = (
    "runtime/kv_interlock_endpoint.py", "runtime/kv_skap_vault.py", "runtime/kv_receipt_ledgers.py",
    "docs/KV_SKAP_VAULT_LADDER_CONFORMANCE.md", "docs/kv-skap-ledger-location.md", "README.md",
    "CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md", "tests/kv_two_layer_e0.py", "tests/test_kv_ladder_conformance_lc_kv.py",
    "tests/test_kv_interlock_runtime_endpoint.py",
)
#: sealed byte copies of upstream receipts (LLM-adapter#432): path -> sha256. Their bytes are never edited here.
SEALED = {
    "runtime/intr_pinned/llm_adapter/endpoint_ledger_anchor.py":
        "153cf121a51199da8432735d4b2fb34b396f7eaa24da80f1bf9c77040013ac09",
    "runtime/intr_pinned/llm_adapter/endpoint_ledger_designation.py":
        "d69dbb22a1446a22e84b86532f93d9698ac6dc3c82e6aa6ee20882c6764049d8",
    "runtime/intr_pinned/llm_adapter/intr_transport_carrier.py":
        "9d3e69c838d7e20533f0c5a06401b018948cb12a4201889f6b41d4b497df720f",
    "runtime/intr_pinned/llm_adapter/org_ledger_location.py":
        "b51e6a8bd39ba6fd83044222a3858a2cb0c437020e3e9abbe97c4494d41f2681",
    "runtime/intr_pinned/.stegverse/node-ledger/kv-ledger-head-signers.v1.json":
        "758d798388599171c145e3d19ca4eb155ad3d3762a3721804da65c08ebc1fe72",
    "tests/fixtures/intr_pinned_test_only/contract_with_431_location_and_pinned_genesis.json":
        "ea81ca135bfd3b8e86a69251cf63d6f5aaa86fa46777dcec9370971dd0c5208a",
}
SIX_FIELD_NOTE = "## Sealed byte copies that still carry retired LLM-adapter#431 wording (six-field note"


def _live_text(rel: str) -> str:
    text = (ROOT / rel).read_text(encoding="utf-8")
    return WITHDRAWN_ASSERTION.sub("", ANTI_REVIVAL.sub("", VENDORED_PATH.sub("", text)))


def test_live_readers_carry_no_retired_431_235_or_designation_module_reference():
    for rel in LIVE_READERS:
        text = _live_text(rel)
        for pattern in RETIRED_431:
            hit = pattern.search(text)
            assert not hit, f"{rel}: {text[max(0, hit.start() - 40):hit.end() + 40]!r} matches {pattern.pattern}"


def test_every_runtime_and_docs_file_outside_the_sealed_copies_is_clean():
    scanned = [p for p in (ROOT / "runtime").glob("*.py")] + [p for p in (ROOT / "docs").rglob("*.md")]
    assert scanned
    for path in scanned:
        rel = path.relative_to(ROOT).as_posix()
        text = _live_text(rel)
        for pattern in RETIRED_431:
            assert not pattern.search(text), f"{rel}: {pattern.pattern}"


def test_sealed_byte_copies_are_unedited_and_recorded_in_the_six_field_note():
    pinned = (ROOT / "runtime/intr_pinned/PINNED.md").read_text(encoding="utf-8")
    assert SIX_FIELD_NOTE in pinned
    note = pinned[pinned.index(SIX_FIELD_NOTE):pinned.index("## Pin entry 2026-10-23")]
    for field in ("CODE", "CLASS", "OBSERVED", "EXPECTED", "BLOCKS", "NEXT"):
        assert f"* {field}: " in note, field
    for rel, digest in SEALED.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, f"{rel} bytes changed"
        assert f"`{rel}`" in note and digest in note, rel


def test_no_unlisted_file_under_intr_pinned_carries_the_retired_wording():
    sealed = set(SEALED)
    for path in (ROOT / "runtime/intr_pinned").rglob("*"):
        rel = path.relative_to(ROOT).as_posix()
        if not path.is_file() or rel in sealed or rel.endswith("PINNED.md"):
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in RETIRED_431:
            assert not pattern.search(text), f"{rel} is not in the sealed list but matches {pattern.pattern}"
