"""Guard: KV's receipt-chain code, contracts, head-signers reference and ledger-location doc carry none of the retired wording.

Retired: references to StegVerse-org/LLM-adapter#431, StegVerse-org#235 and the LLM-adapter endpoint_ledger_designation module
(an LLM-adapter InTr crossing), "KV reaches the Orgs only through InTr", and any claim that the Org<->KV crossing status is
"unruled". The ruling (StegVerse-org/.github#162 c6394603737, LC-KV-29) is: KV is its own ledger-holding party, an Org<->KV
crossing is between distinct parties (never an intra-org InTr hop) and is recorded on both ledgers, KV's end required.
Wording only: no behavior change. The Org->KV intr-destination path_ids stay designated (Coordination, StegVerse-org/.github#167:
the :intr-destination designation is valid under LC-KV-29); no contract is changed."""
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
#: the retired sentence: it no longer appears in the runtime, the docs, the refusal text or the two contracts.
SEALED_CONTRACT_SENTENCE = "No Org→KV intr-destination path_id is declared until the KV-side crossing records are in code with tests"
CONTRACT_DESIGNATED = ("The Org→KV crossing is designated :intr-destination in org_crossing_cross_check.path_ids: an InTr crossing "
                       "between distinct parties (LC-KV-29), recorded on both ledgers")
#: the two contract notes that carried the retired sentence; the sentence was the ONLY change to the contract
SENTENCE_NOTES = ("org_membership", "path_ids_note")
#: sha256 of each contract (canonical JSON, sorted keys) without those two notes. The same value was computed on the pre-change
#: contract bytes (contract sha256 62244b5c / af70e4a3), so nothing else in the contract changed.
CONTRACT_WITHOUT_SENTENCE_NOTES_SHA256 = {
    ".stegverse/receipt-chains/skap-receipts.contract.json": "5e41dd8f83222814f4972cf5b4a40490ed635211d1ca1000bf0027a0979d65ca",
    ".stegverse/receipt-chains/stegverse-kv-receipts.contract.json": "d1c259ac5fa06087b6b87faf80274c334385af9aa275d05f944eebafbc632c0c",
}
DESIGNATED = ("The Org→KV intr-destination path_ids in org_crossing_cross_check.path_ids designate that crossing, a legitimate InTr "
              "crossing between distinct parties (LC-KV-29)")
#: wording that describes the designated Org->KV crossing as absent, inert, or not an InTr crossing
STALE_CROSSING = (
    re.compile(r"path_ids\s+stay\s+inert", re.I), re.compile(r"no\s+Org\W{1,3}KV\s+intr-destination\s+path_id\s+is\s+declared", re.I),
    re.compile(r"declared\s+until\s+the\s+KV-side\s+crossing\s+records", re.I),
    re.compile(r"Org\W{1,3}KV\s+(?:crossing\s+)?(?:is|as)\s+an?\s+intra-org", re.I),
)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_guarded_files_carry_no_retired_reference_or_wording():
    for rel in GUARDED:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for pattern in RETIRED:
            assert not pattern.search(text), f"{rel}: retired wording matching {pattern.pattern}"


def test_crossing_is_worded_per_the_lc_kv_29_ruling_and_the_designated_path_ids_are_a_legitimate_crossing():
    for rel in ("runtime/kv_receipt_ledgers.py", "docs/kv-skap-ledger-location.md"):
        text = _flat((ROOT / rel).read_text(encoding="utf-8"))
        assert RULING in text and DESIGNATED in text, rel
        assert SEALED_CONTRACT_SENTENCE not in text, rel
    for rel in CONTRACTS:
        body = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        text = json.dumps(body, ensure_ascii=False)
        assert RULING in text and CONTRACT_DESIGNATED in text and SEALED_CONTRACT_SENTENCE not in text, rel
        # the designation is valid and unchanged: one Org->KV intr-destination path_id per contract
        ids = body["ledger_designation"]["rollback_watermark_source"]["org_crossing_cross_check"]["path_ids"]
        assert len(ids) == 1 and re.fullmatch(r"StegVerse-org->STEGVERSE_KV:[^:]+:intr-destination", ids[0]), rel


def test_no_runtime_or_doc_wording_describes_the_designated_crossing_as_absent_inert_or_intra_org():
    scanned = list((ROOT / "runtime").glob("*.py")) + list((ROOT / "docs").rglob("*.md"))
    assert scanned
    for path in scanned:
        text = _flat(path.read_text(encoding="utf-8"))
        for pattern in STALE_CROSSING:
            assert not pattern.search(text), f"{path.relative_to(ROOT)}: {pattern.pattern}"


def test_refusal_text_states_the_ruling_not_a_superseded_status():
    refusal = json.dumps(ledgers.org_membership_refused("kv", "guard"), ensure_ascii=False)
    assert RULING in refusal and DESIGNATED in refusal and SEALED_CONTRACT_SENTENCE not in refusal
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
#: The six byte copies of the retired LLM-adapter#432 org-ledger / endpoint-anchor path that runtime/intr_pinned and the tests
#: once carried (sha256 of each, for the record). Coordination ruled (b) on StegVerse-org/.github#162 c6509636142: there is never an
#: InTr hop inside one org, and these modules functionally encoded the retired Org->adapter path and an adapter ledger designation
#: (their upstream, #432, was closed unmerged). They are removed from every source bots read; git history and the #432 branch keep
#: the bytes.
REMOVED_COPIES = {
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
#: Other files that existed only to serve those six (same upstream, same removal).
REMOVED_COMPANIONS = (
    "runtime/intr_pinned/.stegverse/node-ledger/node-ledger-opened-signers.v1.json",
    "runtime/intr_pinned/.stegverse/node-ledger/org-ledger-head-signers.v1.json",
    "runtime/intr_pinned/.stegverse/node-ledger/pinned-code-digests.v1.json",
    "runtime/intr_pinned/schemas/endpoint-kind.v1.json",
    "runtime/intr_pinned/schemas/node-ledger-opened.v1.json",
    "runtime/intr_pinned/schemas/node-ledger-opened-signed.v1.json",
    "runtime/intr_pinned/schemas/node-ledger-opened-generation.v1.json",
    "tests/fixtures/intr_pinned_test_only/contract_with_431_repository_ledger_location.json",
    "tests/fixtures/intr_pinned_test_only/org_ledger_harness.py",
    "tests/fixtures/intr_pinned_test_only/org_ledger_test_genesis.json",
    "tests/fixtures/intr_pinned_test_only/node.designation.json",
)
#: Names that identify the removed content. No tracked source may name them (PINNED.md and this guard record the removal).
RETIRED_NAMES = tuple(re.compile(x) for x in (
    r"endpoint_ledger_anchor", r"endpoint_ledger_designation", r"intr_transport_carrier", r"org_ledger_location",
    r"org_ledger_harness", r"evaluate_anchored", r"node-ledger-opened", r"org-ledger-head-signers",
    r"endpoint-kind\.v1", r"pinned-code-digests", r"contract_with_431", r"org_ledger_test_genesis",
    r"node\.designation\.json", r"intr_pinned/\.stegverse/node-ledger"))
RETIRED_DIGESTS = tuple(d[:12] for rel, d in REMOVED_COPIES.items() if not rel.endswith("kv-ledger-head-signers.v1.json"))


def test_the_six_removed_copies_and_their_companions_are_gone():
    for rel in list(REMOVED_COPIES) + list(REMOVED_COMPANIONS):
        assert not (ROOT / rel).exists(), f"{rel} must stay removed (ruling StegVerse-org/.github#162 c6509636142)"
    assert not (ROOT / "runtime/intr_pinned/.stegverse/node-ledger").exists()
    present = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "runtime/intr_pinned/llm_adapter").glob("*.py"))
    assert present == sorted("runtime/intr_pinned/llm_adapter/" + n for n in (
        "ed25519_verify.py", "healthy_node_evaluator.py", "node_existence_readback.py",
        "node_health_check_projection.py", "node_health_report_producer.py", "node_identity_binding_producer.py",
        "node_ingress_boundary.py", "node_receipt_common.py", "supplied_epoch.py")), present
    # KV's own head-signers file is KV's own, not the vendored copy
    assert (ROOT / ".stegverse/node-ledger/kv-ledger-head-signers.v1.json").is_file()


def _tracked_sources():
    import subprocess
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout.decode()
    for rel in filter(None, out.split("\0")):
        if rel in ("runtime/intr_pinned/PINNED.md", "tests/test_kv_receipt_ledgers_no_431_and_crossing_wording.py"):
            continue
        path = ROOT / rel
        if path.is_file() and path.suffix in {".py", ".md", ".json", ".yml", ".yaml", ".txt", ".toml", ""}:
            yield rel, path.read_text(encoding="utf-8", errors="replace")


def test_no_source_references_a_removed_copy_by_name_or_digest():
    checked = 0
    for rel, text in _tracked_sources():
        checked += 1
        for pattern in RETIRED_NAMES:
            hit = pattern.search(text)
            assert not hit, f"{rel}: {text[max(0, hit.start() - 40):hit.end() + 40]!r} names a removed copy"
        for digest in RETIRED_DIGESTS:
            assert digest not in text, f"{rel} pins the removed digest {digest}"
    assert checked > 20


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


def test_no_file_under_intr_pinned_carries_the_retired_wording():
    for path in (ROOT / "runtime/intr_pinned").rglob("*"):
        rel = path.relative_to(ROOT).as_posix()
        if not path.is_file() or rel.endswith("PINNED.md"):
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in RETIRED_431:
            assert not pattern.search(text), f"{rel} matches {pattern.pattern}"


def test_contract_change_is_only_the_retired_sentence_and_the_pins_follow_the_bytes():
    for rel, expected in CONTRACT_WITHOUT_SENTENCE_NOTES_SHA256.items():
        body = json.loads((ROOT / rel).read_bytes())
        assert all(CONTRACT_DESIGNATED in body["designation_notes"][k] for k in SENTENCE_NOTES), rel
        for k in SENTENCE_NOTES:
            body["designation_notes"].pop(k)
        assert hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == expected, rel
    for entry in ledgers.RECEIPT_LEDGERS.values():
        assert entry["contract_sha256"] == "sha256:" + hashlib.sha256((ROOT / entry["contract_path"]).read_bytes()).hexdigest()
