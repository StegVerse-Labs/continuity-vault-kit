"""Guard (ruling StegVerse-org/.github#167, LC-KV-29): KV's own ledger module and its two contracts carry no reference to
StegVerse-org/LLM-adapter#431 or StegVerse-org#235, nor with the LLM-adapter endpoint_ledger_designation module (Coordination
follow-up ruling YES: wrong content goes from every source bots read: the two receipt-chain contracts, the head-signers
reference and docs/kv-skap-ledger-location.md), and the Org<->KV crossing is worded as unruled with the Org->KV
path_id undeclared. Wording only: no behavior, no Org->KV path declared."""
import hashlib
import json
import re
from pathlib import Path

from runtime import kv_receipt_ledgers as ledgers

ROOT = Path(__file__).resolve().parents[1]
GUARDED = (
    "runtime/kv_receipt_ledgers.py",
    ".stegverse/receipt-chains/stegverse-kv-receipts.contract.json",
    ".stegverse/receipt-chains/skap-receipts.contract.json",
)
#: every other source of KV's ledger location that bots read (no Org-ledger or LLM-adapter reference either)
GUARDED_SOURCES = GUARDED + (
    ".stegverse/node-ledger/kv-ledger-head-signers.v1.json",
    "docs/kv-skap-ledger-location.md",
)
RETIRED_REFS = (re.compile(r"LLM-adapter\s*#?\s*431", re.I), re.compile(r"(?<![\w/#])#431\b"),
                re.compile(r"StegVerse-org\s*#?\s*235", re.I), re.compile(r"endpoint_ledger_designation\.py", re.I))
UNRULED = ("Org↔KV crossing status is unruled; the Org→KV path_id is undeclared under protocol.json:174 "
           "(FAIL_CLOSED ORG_KV_CROSSING_INTR_STATUS_UNRULED)")


def test_guarded_files_carry_no_431_or_235_reference():
    for rel in GUARDED_SOURCES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for pattern in RETIRED_REFS:
            assert not pattern.search(text), f"{rel}: new/retained reference matching {pattern.pattern}"


def test_crossing_is_worded_unruled_and_no_org_kv_path_is_declared():
    source = (ROOT / "runtime/kv_receipt_ledgers.py").read_text(encoding="utf-8")
    assert "Org↔KV crossing status is unruled" in source and "ORG_KV_CROSSING_INTR_STATUS_UNRULED" in source
    doc = (ROOT / "docs/kv-skap-ledger-location.md").read_text(encoding="utf-8")
    assert "Org↔KV crossing status is unruled" in doc
    for rel in GUARDED[1:]:
        body = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        assert "ORG_KV_CROSSING_INTR_STATUS_UNRULED" in json.dumps(body, ensure_ascii=False), rel
        assert "STEGVERSE_KV" not in {k for k in body.get("path_ids", {})} if isinstance(body.get("path_ids"), dict) else True


def test_refusal_text_does_not_claim_kv_reaches_orgs_through_intr():
    refusal = ledgers.org_membership_refused("kv", "guard")
    assert "KV reaches the Orgs only through InTr" not in json.dumps(refusal, ensure_ascii=False)
    assert "ORG_KV_CROSSING_INTR_STATUS_UNRULED" in json.dumps(refusal, ensure_ascii=False)


def test_contract_digests_are_the_sha256_of_the_checked_in_bytes():
    for which, spec in ledgers.RECEIPT_LEDGERS.items():
        digest = "sha256:" + hashlib.sha256((ROOT / spec["contract_path"]).read_bytes()).hexdigest()
        assert spec["contract_sha256"] == digest, which
