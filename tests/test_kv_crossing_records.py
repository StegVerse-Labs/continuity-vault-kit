"""KV's own end of an Org->KV crossing (StegVerse-org/.github#162 c6394603737, LC-KV-29): one ingress record per crossing.

Behavior tests for runtime.kv_crossing_records. Rigel's rule (2026-10-29 3:08 PM CDT, Lane B's chat, relayed at
StegVerse-org/.github#162 c6508050206): "This shouldn't be possible without being a literal duplicate." Each crossing
gets exactly one KV-side receipt; a second one is refused as a duplicate, six-field FAIL_CLOSED, with no newest-wins and
no replacement policy. E0 stand-ins are labelled E0_STANDIN_TEST_ONLY_NOT_EVIDENCE: a scratch device-local read-back
root outside the KV #2 lineage, a TEST-ONLY head signer, and a scratch contract re-pinned in memory. Production files
are untouched. No test is skipped."""
from __future__ import annotations

import ast
import contextlib
import hashlib
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from kv_two_layer_e0 import E0_LABEL, E0_ROUTE_SEED, e0_route_ref, pinned, signer  # noqa: E402
from runtime import kv_crossing_records as cr  # noqa: E402
from runtime import kv_receipt_ledgers as rl  # noqa: E402
from runtime import kv_storage_provider_adapter as spa  # noqa: E402

SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")
E0_REQUEST = "E0-TEST-ONLY-NOT-A-KV-REQUEST"
ROUTE_KEY_ID = e0_route_ref()["key_id"]
ORG_SOURCE = "sha256:" + "0c" * 32
KV_PATH = "StegVerse-org->STEGVERSE_KV:_StegVerse/Receipts:intr-destination"


def device_local():
    return spa.default_registry().get("device-local")


def _sha_file(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _genesis_root(which="kv", epoch="40"):
    """TEST-ONLY: a scratch KV root holding the chain's genesis and KV's own head record. Returns (root, genesis)."""
    hne = pinned()["healthy_node_evaluator"]
    spec = rl.RECEIPT_LEDGERS[which]
    body = {"schema": "stegverse.repo-transition-receipt/v1", "repository": spec["repository"],
            "transition_id": "REPOSITORY_LEDGER_INITIALIZATION:e0", "transition_class": rl.GENESIS_CLASS,
            "predecessor_state_sha256": hne.sha({"previous": None}), "successor_state_sha256": hne.sha({"t": "g"}),
            "evidence": {"label": E0_LABEL, "repository": spec["repository"]}, "authority_effect": "NONE",
            "hb_reference": {"epoch": epoch, "derived_from_clock": False}, "observed_at": None,
            "previous_receipt_sha256": None}
    genesis = {**body, "receipt_sha256": hne.sha(body)}
    root = Path(tempfile.mkdtemp(prefix="e0-kv-crossing-"))
    where = root / spec["storage_location"]
    (where / "receipts").mkdir(parents=True)
    (where / "receipts" / (genesis["receipt_sha256"][7:] + ".json")).write_text(json.dumps(genesis), encoding="utf-8")
    (where / "HEAD.json").write_text(json.dumps({"receipt_sha256": genesis["receipt_sha256"]}), encoding="utf-8")
    entry = {"schema": rl.HEAD_RECORD_SCHEMA, "head_receipt_sha256": genesis["receipt_sha256"],
             "previous_record_sha256": None}
    (where / rl.HEAD_RECORD).write_text(json.dumps({**entry, "record_sha256": hne.sha(entry)}) + "\n", encoding="utf-8")
    return root, genesis


@contextlib.contextmanager
def kv_chain(which="kv", edit=None, epoch="40"):
    """TEST-ONLY: the designation pinned at a scratch genesis on the device-local storage endpoint outside the KV #2
    lineage, with a published E0 head signer. Yields (root, genesis). Production files are untouched."""
    root, genesis = _genesis_root(which, epoch)
    spec = rl.RECEIPT_LEDGERS[which]
    contract = json.loads((ROOT / spec["contract_path"]).read_text(encoding="utf-8"))
    pin = genesis["receipt_sha256"]
    contract["repository_ledger_location"]["expected_genesis_receipt_sha256"] = pin
    ld = contract["ledger_designation"]
    ld["expected_genesis_receipt_sha256"] = pin
    ld["stores"][0].update(provider_id="device-local", access_adapter="resident-device-local", kv_request_id=E0_REQUEST)
    if edit:
        edit(contract)
    raw = (json.dumps(contract, indent=2) + "\n").encode()
    scratch = Path(tempfile.mkdtemp(prefix="e0-kv-crossing-contract-"))
    (scratch / "contract.json").write_bytes(raw)
    saved, saved_signers = dict(spec), rl.load_head_signers
    spec.update(contract_path=str(scratch / "contract.json"), contract_sha256=_sha_file(raw))
    rl.load_head_signers = lambda: [{**e0_route_ref(), "signs": "KV_RECORDED_RECEIPT_CHAIN_HEAD"}]
    try:
        yield root, genesis
    finally:
        spec.clear()
        spec.update(saved)
        rl.load_head_signers = saved_signers


def crossing(communication_id="comm-1", digest=ORG_SOURCE, path_id=KV_PATH):
    return {"path_id": path_id, "communication_id": communication_id, "source_repository_receipt_sha256": digest}


def tree(root):
    """Every file under the scratch root with its bytes: what a call changed or left alone."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(Path(root).rglob("*")) if p.is_file()}


def chain_of(root, which="kv"):
    spec = rl.RECEIPT_LEDGERS[which]
    return pinned()["healthy_node_evaluator"].read_chain(Path(root) / spec["storage_location"], spec["repository"])[0]


class Base(unittest.TestCase):
    def assertSix(self, out, code, klass=None):
        self.assertEqual((out["disposition"], out["failure_code"]), ("FAIL_CLOSED", code), out)
        if klass:
            self.assertEqual(out["failure_class"], klass, out)
        for field in SIX:
            self.assertTrue(isinstance(out[field], str) and out[field].strip(), field)
        self.assertEqual((out["ledger_written"], out["authority_effect"]), (False, "NONE"))


class ProductionStaysFailClosed(Base):
    def test_kv_chain_is_kv2_pending_before_anything_is_read_or_written(self):
        out = cr.append_crossing_record("kv", spa.default_registry().get("google-drive"), "/nonexistent", crossing(), 40)
        self.assertSix(out, "KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR", "B")
        self.assertFalse(out["appended"])
        self.assertFalse(Path("/nonexistent").exists())

    def test_skap_chain_takes_no_org_crossing_record(self):
        with kv_chain("skap_vault") as (root, _):
            before = tree(root)
            out = cr.append_crossing_record("skap_vault", device_local(), root,
                                            crossing(path_id=KV_PATH.replace("_StegVerse/Receipts", "_Vault/SKAP/Receipts")), 40)
            self.assertSix(out, "KV_CROSSING_RECORD_NOT_ON_THE_SKAP_CHAIN", "A")
            self.assertEqual(tree(root), before)
        self.assertSix(cr.plan_crossing_record("skap_vault", None, None, crossing(), 40),
                       "KV_CROSSING_RECORD_NOT_ON_THE_SKAP_CHAIN", "A")

    def test_unknown_chain_and_unpinned_genesis(self):
        self.assertSix(cr.plan_crossing_record("org", None, None, crossing(), 40), "KV_RECEIPT_CHAIN_UNKNOWN", "C")
        # the KV #2 lineage is refused first even with the designated endpoint; an E0 store with a null pin is refused next
        self.assertSix(cr.plan_crossing_record("kv", device_local(), "/nonexistent", crossing(), 40),
                       "KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR", "B")

        def unpin(c):
            c["repository_ledger_location"]["expected_genesis_receipt_sha256"] = None
            c["ledger_designation"]["expected_genesis_receipt_sha256"] = None
        with kv_chain(edit=unpin) as (root, _):
            before = tree(root)
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 40)
            self.assertSix(out, "KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED", "B")
            self.assertEqual(tree(root), before)


class OneReceiptPerCrossing(Base):
    def test_plan_returns_the_exact_record_and_writes_nothing(self):
        with kv_chain() as (root, genesis):
            before = tree(root)
            plan = cr.plan_crossing_record("kv", device_local(), root, crossing(), 40)
            self.assertEqual(plan["disposition"], "ALLOW", plan)
            self.assertEqual(tree(root), before)
            self.assertEqual((plan["ledger_written"], plan["appended"], plan["signed_by_this_module"]),
                             (False, False, False))
            r = plan["receipt"]
            self.assertEqual((r["transition_class"], r["repository"], r["authority_effect"]),
                             ("INTR_MESH_PATH_INGRESS", "STEGVERSE_KV:_StegVerse/Receipts", "NONE"))
            self.assertEqual((r["previous_receipt_sha256"], r["predecessor_state_sha256"]),
                             (genesis["receipt_sha256"],) * 2)
            self.assertEqual((r["hb_reference"], r["observed_at"]),
                             ({"epoch": "40", "derived_from_clock": False}, "SUPPLIED_HB_EPOCH:40"))
            ev = r["evidence"]
            self.assertEqual(set(ev), {"schema", "path_id", "communication_id", "source_repository_receipt_sha256",
                                       "destination_location", "boundary_evidence"})
            self.assertEqual(ev["source_repository_receipt_sha256"], ORG_SOURCE)
            self.assertEqual(ev["boundary_evidence"], {"operation": cr.OPERATION, "path_id": KV_PATH,
                                                       "communication_id": "comm-1"})
            self.assertNotIn("body", json.dumps(ev))
            self.assertEqual(r["receipt_sha256"], pinned()["healthy_node_evaluator"].sha(
                {k: v for k, v in r.items() if k != "receipt_sha256"}))
            self.assertEqual(plan, cr.plan_crossing_record("kv", device_local(), root, crossing(), 40))

    def test_append_writes_exactly_the_receipt_head_and_head_record(self):
        with kv_chain() as (root, genesis):
            before = tree(root)
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 40)
            self.assertEqual((out["disposition"], out["appended"], out["ledger_written"]), ("ALLOW", True, True), out)
            after = tree(root)
            new = sorted(set(after) - set(before))
            changed = sorted(k for k in before if after[k] != before[k])
            # the lock file sits beside the chain's location (never inside it, so the reader sees no stray record)
            self.assertEqual(new, [cr.LOCK_NAME, "_StegVerse/Receipts/receipts/" + out["receipt_sha256"][7:] + ".json"])
            self.assertEqual(changed, ["_StegVerse/Receipts/HEAD.json", "_StegVerse/Receipts/" + rl.HEAD_RECORD])
            chain = chain_of(root)
            self.assertEqual([r["transition_class"] for r in chain], ["INTR_MESH_PATH_INGRESS", rl.GENESIS_CLASS])
            self.assertEqual(chain[0], out["receipt"])
            self.assertEqual(chain[1]["receipt_sha256"], genesis["receipt_sha256"])
            self.assertFalse((Path(root) / "_StegVerse" / "Receipts" / cr.LOCK_NAME).exists())
            self.assertEqual(sorted(p.name for p in (Path(root) / "_StegVerse" / "Receipts").iterdir()),
                             ["HEAD.json", rl.HEAD_RECORD, "receipts"])

    def test_second_receipt_for_the_same_crossing_is_refused_as_a_duplicate(self):
        with kv_chain() as (root, _):
            first = cr.append_crossing_record("kv", device_local(), root, crossing(), 40)
            written = tree(root)
            for label, again in (("literal duplicate", crossing()),
                                 ("same crossing, other Org digest", crossing(digest="sha256:" + "0d" * 32)),
                                 ("same Org record, other communication", crossing("comm-2"))):
                with self.subTest(label):
                    out = cr.append_crossing_record("kv", device_local(), root, again, 41)
                    self.assertSix(out, cr.ALREADY_RECORDED_CODE, "C")
                    self.assertEqual((out["appended"], out["existing_receipt_sha256"]), (False, first["receipt_sha256"]))
                    self.assertIn("This shouldn't be possible without being a literal duplicate",
                                  out["required_evidence_or_repair"])
                    self.assertIn("no newest-wins", out["required_evidence_or_repair"])
                    self.assertEqual(tree(root), written)           # nothing written, nothing replaced
            self.assertIn("a literal duplicate of", cr.plan_crossing_record("kv", device_local(), root, crossing(), 40)["detail"])
            self.assertIn("not a literal duplicate", cr.plan_crossing_record(
                "kv", device_local(), root, crossing(digest="sha256:" + "0d" * 32), 40)["detail"])
            self.assertEqual(sum(r["transition_class"] == "INTR_MESH_PATH_INGRESS" for r in chain_of(root)), 1)
            self.assertEqual(chain_of(root)[0]["receipt_sha256"], first["receipt_sha256"])   # no newest-wins

    def test_a_different_crossing_gets_its_own_one_receipt(self):
        with kv_chain() as (root, _):
            a = cr.append_crossing_record("kv", device_local(), root, crossing("comm-1"), 40)
            b = cr.append_crossing_record("kv", device_local(), root, crossing("comm-2", "sha256:" + "0e" * 32), 41)
            self.assertEqual((a["disposition"], b["disposition"]), ("ALLOW", "ALLOW"))
            self.assertEqual(chain_of(root)[0]["previous_receipt_sha256"], a["receipt_sha256"])
            self.assertEqual(cr.append_crossing_record("kv", device_local(), root, crossing("comm-2", "sha256:" + "0e" * 32), 42)
                             ["failure_code"], cr.ALREADY_RECORDED_CODE)

    def test_history_with_two_receipts_for_one_crossing_still_refuses_a_third(self):
        """A chain that already (wrongly) holds two receipts for a crossing grants nothing more: refused, both named."""
        with kv_chain() as (root, _):
            a = cr.append_crossing_record("kv", device_local(), root, crossing(), 40)
            self.assertEqual(a["disposition"], "ALLOW")
            where = Path(root) / "_StegVerse" / "Receipts"
            hne = pinned()["healthy_node_evaluator"]
            head = chain_of(root)[0]
            body = {k: v for k, v in head.items() if k != "receipt_sha256"}
            body.update(transition_id="forged-second", previous_receipt_sha256=head["receipt_sha256"])
            second = {**body, "receipt_sha256": hne.sha(body)}
            (where / "receipts" / (second["receipt_sha256"][7:] + ".json")).write_text(json.dumps(second), encoding="utf-8")
            (where / "HEAD.json").write_text(json.dumps({"receipt_sha256": second["receipt_sha256"]}), encoding="utf-8")
            entry = {"schema": rl.HEAD_RECORD_SCHEMA, "head_receipt_sha256": second["receipt_sha256"],
                     "previous_record_sha256": json.loads((where / rl.HEAD_RECORD).read_text().splitlines()[-1])["record_sha256"]}
            with open(where / rl.HEAD_RECORD, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({**entry, "record_sha256": hne.sha(entry)}) + "\n")
            out = cr.plan_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertSix(out, cr.ALREADY_RECORDED_CODE, "C")
            self.assertIn(second["receipt_sha256"], out["detail"])
            self.assertIn(a["receipt_sha256"], out["detail"])

    def test_concurrent_writers_for_one_crossing_land_exactly_one_receipt(self):
        with kv_chain() as (root, _):
            gate, results = threading.Barrier(6), []

            def write(n):
                gate.wait()
                results.append(cr.append_crossing_record("kv", device_local(), root, crossing(), 40 + n))

            threads = [threading.Thread(target=write, args=(n,)) for n in range(6)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(sorted(r["disposition"] for r in results), ["ALLOW"] + ["FAIL_CLOSED"] * 5, results)
            self.assertTrue(all(r["failure_code"] == cr.ALREADY_RECORDED_CODE for r in results if r["disposition"] != "ALLOW"))
            self.assertEqual(sum(r["transition_class"] == "INTR_MESH_PATH_INGRESS" for r in chain_of(root)), 1)


class InputsAreClosed(Base):
    def refuse(self, root, out, code, klass="C"):
        before = tree(root)
        self.assertSix(out, code, klass)
        self.assertEqual(tree(root), before)

    def test_crossing_keys_and_digest_are_closed(self):
        with kv_chain() as (root, _):
            for bad in (None, {}, {**crossing(), "body": {"x": 1}}, {"path_id": KV_PATH, "communication_id": "c"},
                        crossing(digest="sha256:XY"), crossing(digest="0c" * 32), crossing(digest=None),
                        crossing(" "), crossing("c "), crossing(""), crossing(1), crossing("x" * 201)):
                with self.subTest(bad=bad):
                    self.refuse(root, cr.append_crossing_record("kv", device_local(), root, bad, 40),
                                "KV_CROSSING_INPUT_INVALID")

    def test_path_must_be_a_designated_org_to_kv_path(self):
        with kv_chain() as (root, _):
            for pid in ("StegVerse-Labs->STEGVERSE_KV:_StegVerse/Receipts:intr-destination",
                        "StegVerse-org->STEGVERSE_KV:_Vault/SKAP/Receipts:intr-destination",
                        "STEGVERSE_KV:_StegVerse/Receipts->StegVerse-org:intr-destination", "", "x"):
                with self.subTest(path_id=pid):
                    self.refuse(root, cr.append_crossing_record("kv", device_local(), root, crossing(path_id=pid), 40),
                                "KV_CROSSING_PATH_NOT_DESIGNATED")

    def test_no_crossing_inside_one_party(self):
        own = "STEGVERSE_KV->STEGVERSE_KV:_StegVerse/Receipts:intr-destination"
        edit = lambda c: c["ledger_designation"]["rollback_watermark_source"]["org_crossing_cross_check"]["path_ids"].append(own)
        with kv_chain(edit=edit) as (root, _):
            self.refuse(root, cr.append_crossing_record("kv", device_local(), root, crossing(path_id=own), 40),
                        "KV_CROSSING_WITHIN_ONE_PARTY_REFUSED")

    def test_supplied_epoch_rule(self):
        with kv_chain() as (root, _):
            for epoch, code in ((None, "HB_EPOCH_NOT_SUPPLIED"), ("31", "HB_EPOCH_INVALID"), ("+33", "HB_EPOCH_INVALID"),
                                (" 33", "HB_EPOCH_INVALID"), ("33.0", "HB_EPOCH_INVALID"), (True, "HB_EPOCH_INVALID"),
                                (33.0, "HB_EPOCH_INVALID"), ("٣٣", "HB_EPOCH_INVALID"), (39, "HB_EPOCH_INVALID")):
                with self.subTest(epoch=epoch):
                    self.refuse(root, cr.append_crossing_record("kv", device_local(), root, crossing(), epoch), code)
            self.assertEqual(cr.plan_crossing_record("kv", device_local(), root, crossing(), 40)["receipt"]["observed_at"],
                             "SUPPLIED_HB_EPOCH:40")

    def test_endpoint_and_readback_must_be_the_designated_ones(self):
        with kv_chain() as (root, genesis):
            self.refuse(root, cr.append_crossing_record("kv", spa.default_registry().get("google-drive"), root, crossing(), 40),
                        "KV_STORAGE_ENDPOINT_NOT_THE_DESIGNATED_ONE")
            self.refuse(root, cr.append_crossing_record("kv", None, root, crossing(), 40),
                        "KV_STORAGE_ENDPOINT_NOT_THE_DESIGNATED_ONE")
            empty = Path(tempfile.mkdtemp(prefix="e0-kv-empty-"))
            self.assertSix(cr.append_crossing_record("kv", device_local(), empty, crossing(), 40),
                           "KV_RECEIPT_CHAIN_UNREADABLE", "D")
            self.assertEqual(tree(empty), {})
            self.assertSix(cr.append_crossing_record("kv", device_local(), None, crossing(), 40),
                           "KV_RECEIPT_CHAIN_UNREADABLE", "D")

    def test_a_chain_that_is_not_kv_own_pinned_genesis_is_refused(self):
        with kv_chain() as (root, _):
            other, _ = _genesis_root("kv", "41")
            self.refuse(other, cr.append_crossing_record("kv", device_local(), other, crossing(), 40),
                        "KV_RECEIPT_CHAIN_UNREADABLE")

    def test_rolled_back_head_record_is_refused_not_written_over(self):
        with kv_chain() as (root, genesis):
            first = cr.append_crossing_record("kv", device_local(), root, crossing(), 40)
            where = Path(root) / "_StegVerse" / "Receipts"
            lines = (where / rl.HEAD_RECORD).read_text().splitlines()
            (where / rl.HEAD_RECORD).write_text(lines[0] + "\n", encoding="utf-8")      # head record rolled back
            before = tree(root)
            out = cr.append_crossing_record("kv", device_local(), root, crossing("comm-9", "sha256:" + "0f" * 32), 41)
            # the reader's own rollback refusal (DENY, class C, the one code the ruling keeps), six fields, nothing written
            self.assertEqual((out["disposition"], out["failure_code"]), ("DENY", rl.ROLLBACK_CODE), out)
            for field in SIX:
                self.assertTrue(out[field].strip(), field)
            self.assertEqual(tree(root), before)
            self.assertEqual(first["disposition"], "ALLOW")

    def test_epoch_older_than_kv_head_is_refused(self):
        with kv_chain(epoch="50") as (root, _):
            self.refuse(root, cr.append_crossing_record("kv", device_local(), root, crossing(), 40), "HB_EPOCH_INVALID")
            self.assertEqual(cr.append_crossing_record("kv", device_local(), root, crossing(), 50)["disposition"], "ALLOW")


class ReaderSeesBothEnds(Base):
    """The record is in the shape runtime.kv_receipt_ledgers._org_crossing checks (Org digests observed, never granted)."""

    def attestation(self, chain):
        d = rl.designation("kv")[0]
        body = rl.head_attestation_body(d["repository"], d["store_location"], chain[-1]["receipt_sha256"],
                                        chain[0]["receipt_sha256"])
        message = rl.HEAD_ATTESTATION_SCHEMA.encode() + b"\n" + pinned()["healthy_node_evaluator"].canon(body)
        return {**body, "key_id": ROUTE_KEY_ID, "signature_b64": signer().sign_b64(message, E0_ROUTE_SEED)}

    @contextlib.contextmanager
    def org(self, records):
        saved, rl.ORG_CROSSING_READER = rl.ORG_CROSSING_READER, (lambda d, w: records)
        try:
            yield
        finally:
            rl.ORG_CROSSING_READER = saved

    def org_record(self, receipt, head):
        return {"path_id": KV_PATH, "receipt_sha256": receipt, "endpoint_head_sha256": head, "supplied_hb_epoch": "40"}

    def test_reader_allows_the_chain_when_both_ends_hold_the_crossing(self):
        with kv_chain() as (root, genesis):
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 40)
            head, chain = out["receipt_sha256"], chain_of(root)
            with self.org([self.org_record(ORG_SOURCE, genesis["receipt_sha256"]), self.org_record("sha256:" + "0d" * 32, head)]):
                read = rl.read_receipt_ledger("kv", device_local(), root, self.attestation(chain))
            self.assertEqual(read["disposition"], "ALLOW", read)
            self.assertFalse(read["rollback_watermark"]["org_crossing_cross_check"]["never_crossed"])
            self.assertEqual(read["head_receipt_sha256"], head)

    def test_reader_refuses_when_the_orgs_end_is_not_observed(self):
        with kv_chain() as (root, _):
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 40)
            with self.org(None):
                read = rl.read_receipt_ledger("kv", device_local(), root, self.attestation(chain_of(root)))
            self.assertEqual((read["disposition"], read["failure_code"]), ("FAIL_CLOSED", rl.NOT_OBSERVED_CODE), read)
            with self.org([self.org_record("sha256:" + "0d" * 32, out["receipt_sha256"])]):
                read = rl.read_receipt_ledger("kv", device_local(), root, self.attestation(chain_of(root)))
            self.assertEqual(read["failure_code"], rl.CROSSING_CODE, read)     # the ingress points at an unobserved Org record

    def test_writing_never_calls_the_org_reader_and_never_signs(self):
        with kv_chain() as (root, _):
            def boom(*a, **k):
                raise AssertionError("the writer must not read or write an Org ledger")
            saved, rl.ORG_CROSSING_READER = rl.ORG_CROSSING_READER, boom
            try:
                out = cr.append_crossing_record("kv", device_local(), root, crossing(), 40)
            finally:
                rl.ORG_CROSSING_READER = saved
            self.assertEqual(out["disposition"], "ALLOW")
            self.assertFalse(out["signed_by_this_module"])
            self.assertNotIn("signature", json.dumps(out["receipt"]).lower())
            read = rl.read_receipt_ledger("kv", device_local(), root, None)   # unsigned head: still refused by the reader
            self.assertEqual(read["failure_code"], "KV_LEDGER_HEAD_NOT_AUTHENTICATED", read)


class Crash(BaseException):
    """TEST-ONLY: stands for the process stopping at that point (not an Exception, so nothing in the writer catches it)."""


@contextlib.contextmanager
def crash_when(name, target="_put"):
    """TEST-ONLY crash injection: the process stops when the writer reaches ``name`` (HEAD.json or the head record)."""
    real = getattr(cr, target)

    def stop(path, *args, **kwargs):
        if Path(path).name == name:
            raise Crash(name)
        return real(path, *args, **kwargs)
    setattr(cr, target, stop)
    try:
        yield
    finally:
        setattr(cr, target, real)


def receipt_files(root, which="kv"):
    return sorted(p.name for p in (Path(root) / rl.RECEIPT_LEDGERS[which]["storage_location"] / "receipts").glob("*.json"))


def files_for(root, communication_id, which="kv"):
    """Every receipts/ file, chained or not, that is for this crossing: a crossing must never have two."""
    out = []
    for p in (Path(root) / rl.RECEIPT_LEDGERS[which]["storage_location"] / "receipts").glob("*.json"):
        ev = json.loads(p.read_text(encoding="utf-8")).get("evidence") or {}
        if ev.get("communication_id") == communication_id:
            out.append(p.name)
    return out


class CrashBetweenReceiptAndHead(Base):
    """P4's note on cvk#284: a stop between the receipt write and the HEAD.json update leaves an orphan receipt, and a retry
    at a different epoch must not write a second receipt file for the same crossing (Rigel's one-receipt-per-crossing)."""

    def crash_after_receipt(self, root, comm="comm-1", epoch=41, digest=ORG_SOURCE):
        with crash_when("HEAD.json"), self.assertRaises(Crash):
            cr.append_crossing_record("kv", device_local(), root, crossing(comm, digest), epoch)

    def test_the_crash_leaves_exactly_one_orphan_and_the_old_head(self):
        with kv_chain() as (root, genesis):
            before = tree(root)
            self.crash_after_receipt(root)
            after = tree(root)
            added = sorted(k for k in set(after) - set(before) if k != cr.LOCK_NAME)
            self.assertEqual(len(added), 1, added)
            self.assertTrue(added[0].endswith(".json") and "/receipts/" in added[0], added)
            self.assertEqual({k: v for k, v in after.items() if k not in added and k != cr.LOCK_NAME}, before)
            self.assertEqual(chain_of(root)[0]["receipt_sha256"], genesis["receipt_sha256"])
            self.assertFalse([k for k in after if ".kv-crossing-" in k and k != cr.LOCK_NAME])           # no temp file is left behind

    def test_retry_at_the_same_epoch_adopts_the_identical_orphan_and_writes_no_second_file(self):
        with kv_chain() as (root, genesis):
            self.crash_after_receipt(root, epoch=41)
            orphan = {k: v for k, v in tree(root).items() if k.endswith(".json") and "/receipts/" in k
                      and genesis["receipt_sha256"][7:] not in k}
            self.assertEqual(len(orphan), 1)
            before_plan = tree(root)
            plan = cr.plan_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertEqual((plan["disposition"], plan["adopts_orphan_receipt"]), ("ALLOW", True), plan)
            self.assertEqual(tree(root), before_plan)                                   # the plan wrote nothing
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertEqual((out["disposition"], out["appended"], out["adopts_orphan_receipt"]), ("ALLOW", True, True))
            after = tree(root)
            for k, v in orphan.items():
                self.assertEqual(after[k], v)                                           # the orphan file is untouched
            self.assertEqual(len(receipt_files(root)), 2)                               # genesis + the one receipt
            self.assertEqual(len(files_for(root, "comm-1")), 1)
            self.assertEqual([r["receipt_sha256"] for r in chain_of(root)][0], out["head_receipt_sha256"])
            self.assertEqual(len(chain_of(root)), 2)
            again = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertSix(again, cr.ALREADY_RECORDED_CODE, "C")                        # now it is chained: a plain duplicate

    def test_retry_at_a_different_epoch_is_refused_and_writes_no_second_receipt_file(self):
        with kv_chain() as (root, _):
            self.crash_after_receipt(root, epoch=41)
            before = tree(root)
            for call in (cr.plan_crossing_record, cr.append_crossing_record):
                out = call("kv", device_local(), root, crossing(), 55)
                self.assertSix(out, cr.ORPHAN_CODE, "C")
                self.assertIn("not byte-identical", json.dumps(out))
                self.assertFalse(out["appended"])
            self.assertEqual(tree(root), before)                                         # nothing written, nothing removed
            self.assertEqual(len(files_for(root, "comm-1")), 1)

    def test_the_refusal_stands_for_every_retry_that_is_not_the_identical_receipt(self):
        with kv_chain() as (root, _):
            self.crash_after_receipt(root, epoch=41)
            before = tree(root)
            for epoch, digest in ((40, ORG_SOURCE), (41, "sha256:" + "0d" * 32), (999, ORG_SOURCE)):
                out = cr.append_crossing_record("kv", device_local(), root, crossing("comm-1", digest), epoch)
                self.assertSix(out, cr.ORPHAN_CODE, "C")
            self.assertEqual(tree(root), before)

    def test_the_orphan_is_found_by_the_org_record_even_under_another_communication_id(self):
        with kv_chain() as (root, _):
            self.crash_after_receipt(root, comm="comm-1", epoch=41)
            before = tree(root)
            out = cr.append_crossing_record("kv", device_local(), root, crossing("comm-2", ORG_SOURCE), 41)
            self.assertSix(out, cr.ORPHAN_CODE, "C")
            self.assertEqual(tree(root), before)

    def test_an_orphan_that_is_not_byte_identical_is_refused_even_when_its_hash_is_valid(self):
        with kv_chain() as (root, _):
            plan = cr.plan_crossing_record("kv", device_local(), root, crossing(), 41)
            receipt = plan["receipt"]
            where = Path(root) / rl.RECEIPT_LEDGERS["kv"]["storage_location"] / "receipts"
            (where / (receipt["receipt_sha256"][7:] + ".json")).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            before = tree(root)
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertSix(out, cr.ORPHAN_CODE, "C")
            self.assertEqual(tree(root), before)

    def test_an_orphan_on_a_stale_head_is_refused_and_a_new_crossing_does_not_adopt_it(self):
        with kv_chain() as (root, _):
            self.crash_after_receipt(root, comm="comm-1", epoch=41)
            other = cr.append_crossing_record("kv", device_local(), root,
                                              crossing("comm-2", "sha256:" + "0e" * 32), 42)
            self.assertEqual(other["disposition"], "ALLOW")                              # a different crossing is its own one receipt
            before = tree(root)
            out = cr.append_crossing_record("kv", device_local(), root, crossing("comm-1"), 43)
            self.assertSix(out, cr.ORPHAN_CODE, "C")                                     # comm-1's orphan now sits on a stale head
            self.assertSix(cr.append_crossing_record("kv", device_local(), root, crossing("comm-1"), 41), "HB_EPOCH_INVALID", "C")
            self.assertEqual(tree(root), before)
            self.assertEqual(len(files_for(root, "comm-1")), 1)
            self.assertEqual(len(files_for(root, "comm-2")), 1)

    def test_two_unchained_files_for_one_crossing_are_refused(self):
        with kv_chain() as (root, _):
            self.crash_after_receipt(root, epoch=41)
            plan = cr.plan_crossing_record("kv", device_local(), root, crossing(), 41)
            second = dict(plan["receipt"])
            second.pop("receipt_sha256")
            second["hb_reference"] = {"epoch": "77", "derived_from_clock": False}
            second["receipt_sha256"] = pinned()["healthy_node_evaluator"].sha(second)
            where = Path(root) / rl.RECEIPT_LEDGERS["kv"]["storage_location"] / "receipts"
            (where / (second["receipt_sha256"][7:] + ".json")).write_text(json.dumps(second), encoding="utf-8")
            before = tree(root)
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertSix(out, cr.ORPHAN_CODE, "C")
            self.assertIn("more than one", json.dumps(out))
            self.assertEqual(tree(root), before)

    def test_a_torn_or_foreign_receipts_file_is_refused_not_ignored(self):
        for damage in ("torn", "misnamed"):
            with kv_chain() as (root, _):
                self.crash_after_receipt(root, epoch=41)
                where = Path(root) / rl.RECEIPT_LEDGERS["kv"]["storage_location"] / "receipts"
                orphans = [p for p in where.glob("*.json")
                           if "sha256:" + p.stem not in {r["receipt_sha256"] for r in chain_of(root)}]
                self.assertEqual(len(orphans), 1)
                if damage == "torn":
                    orphans[0].write_text(orphans[0].read_text(encoding="utf-8")[:60], encoding="utf-8")
                else:
                    orphans[0].rename(where / ("ab" * 32 + ".json"))
                before = tree(root)
                out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
                self.assertSix(out, "KV_CROSSING_RECEIPT_FILE_UNREADABLE", "C")
                self.assertEqual(tree(root), before)

    def test_a_crash_after_head_json_before_the_head_record_never_writes_a_second_file(self):
        with kv_chain() as (root, _):
            with crash_when(rl.HEAD_RECORD), self.assertRaises(Crash):
                cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            before = tree(root)
            for epoch in (41, 55):
                out = cr.append_crossing_record("kv", device_local(), root, crossing(), epoch)
                self.assertEqual(out["disposition"], "DENY", out)                       # KV's recorded head is behind HEAD.json
                for field in SIX:
                    self.assertTrue(out[field].strip())
            self.assertEqual(tree(root), before)
            self.assertEqual(len(files_for(root, "comm-1")), 1)

    def test_a_stop_while_the_receipt_file_is_being_made_leaves_no_half_receipt(self):
        with kv_chain() as (root, _):
            before = tree(root)
            real = cr.os.link

            def stop(*args, **kwargs):
                raise Crash("link")
            cr.os.link = stop
            try:
                with self.assertRaises(Crash):
                    cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            finally:
                cr.os.link = real
            leftover = {k: v for k, v in tree(root).items() if k not in before and k != cr.LOCK_NAME}
            self.assertEqual(leftover, {})                                               # no receipt file, no temp file
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 55)   # nothing to adopt, so any epoch is fine
            self.assertEqual((out["disposition"], out["adopts_orphan_receipt"]), ("ALLOW", False))
            self.assertEqual(len(files_for(root, "comm-1")), 1)

    def test_an_existing_receipt_file_name_is_never_overwritten(self):
        with kv_chain() as (root, _):
            plan = cr.plan_crossing_record("kv", device_local(), root, crossing(), 41)
            where = Path(root) / rl.RECEIPT_LEDGERS["kv"]["storage_location"] / "receipts"
            target = where / (plan["receipt"]["receipt_sha256"][7:] + ".json")
            with self.assertRaises(cr.StoreWriteFailed) as caught:
                cr._put_new(target.parent / sorted(p.name for p in where.glob("*.json"))[0], "x", Path(root))
            self.assertEqual(caught.exception.stage, "link")
            self.assertIsInstance(caught.exception.cause, FileExistsError)
            self.assertFalse([k for k in tree(root) if "kv-crossing-" in k])


def _kv_tree_without_lock(root):
    return {k: v for k, v in tree(root).items() if not k.endswith(cr.LOCK_NAME)}


@contextlib.contextmanager
def store_fault(name, error, after=0):
    """TEST-ONLY: make os.<name> raise ``error`` (after ``after`` good calls), then restore it."""
    real, calls = getattr(cr.os, name), {"n": 0}

    def faulty(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] > after:
            raise error
        return real(*args, **kwargs)

    setattr(cr.os, name, faulty)
    try:
        yield
    finally:
        setattr(cr.os, name, real)


class StoreErrorsAreSixFieldRefusals(Base):
    """P4's note on cvk#284/#285: a store that cannot hard-link, or fails a write or sync, is a refusal, not an OSError."""

    def test_a_store_without_hard_links_is_refused_with_the_six_fields_and_nothing_is_written(self):
        for errno_ in (1, 95, 18):   # EPERM, ENOTSUP, EXDEV
            with self.subTest(errno=errno_), kv_chain() as (root, _):
                before = _kv_tree_without_lock(root)
                with store_fault("link", OSError(errno_, "hard links not supported")):
                    out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
                self.assertSix(out, cr.HARDLINK_CODE, "D")
                self.assertEqual((out["appended"], out["stopped_at"], out["receipt_file_written"]), (False, "link", False))
                self.assertEqual(_kv_tree_without_lock(root), before)          # no receipt, no HEAD change, no temp left
                self.assertEqual(out["stray_temp_files"], [])

    def test_a_failed_sync_is_refused_with_the_six_fields_and_nothing_is_written(self):
        with kv_chain() as (root, _):
            before = _kv_tree_without_lock(root)
            with store_fault("fsync", OSError(5, "I/O error")):
                out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertSix(out, cr.WRITE_FAILED_CODE, "D")
            self.assertEqual((out["appended"], out["stopped_at"], out["receipt_file_written"]), (False, "sync", False))
            self.assertEqual(_kv_tree_without_lock(root), before)

    def test_a_failure_after_the_receipt_landed_says_so_and_a_retry_at_the_same_epoch_adopts_it(self):
        with kv_chain() as (root, genesis):
            with store_fault("replace", OSError(5, "I/O error")):             # HEAD.json cannot be replaced
                out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertSix(out, cr.WRITE_FAILED_CODE, "D")
            self.assertEqual((out["stopped_at"], out["receipt_file_written"]), ("replace", True))
            self.assertIn("adopts it", out["detail"])
            self.assertEqual(chain_of(root)[-1]["receipt_sha256"], genesis["receipt_sha256"])    # chain unchanged
            self.assertFalse(out["stray_temp_files"])                          # the writer removed its own temp
            again = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertEqual((again["disposition"], again["appended"], again["adopts_orphan_receipt"]), ("ALLOW", True, True))
            self.assertEqual(len(chain_of(root)), 2)

    def test_a_receipt_name_that_appeared_after_the_plan_is_refused_not_raised(self):
        with kv_chain() as (root, _):
            plan = cr.plan_crossing_record("kv", device_local(), root, crossing(), 41)
            target = (Path(root) / rl.RECEIPT_LEDGERS["kv"]["storage_location"] / "receipts"
                      / (plan["receipt"]["receipt_sha256"][7:] + ".json"))
            real = cr._put_new

            def racing(path, text, tmp_dir):
                path.write_text("someone else's bytes", encoding="utf-8")   # a writer outside this lock got there first
                return real(path, text, tmp_dir)

            cr._put_new = racing
            try:
                out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            finally:
                cr._put_new = real
            self.assertSix(out, cr.FILE_PRESENT_CODE, "C")
            self.assertEqual(target.read_text(encoding="utf-8"), "someone else's bytes")    # never overwritten or deleted

    def test_an_unwritable_read_back_root_is_a_refusal_for_the_lock_too(self):
        with kv_chain() as (root, _):
            real = open

            def deny(path, *a, **k):
                if str(path).endswith(cr.LOCK_NAME):
                    raise PermissionError(13, "denied")
                return real(path, *a, **k)

            cr.open = deny
            try:
                out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            finally:
                del cr.open
            self.assertSix(out, cr.WRITE_FAILED_CODE, "D")


class StrayTempFiles(Base):
    """P4's note on cvk#284/#285: a hard kill can leave a .kv-crossing-* temp file. It is never read as a receipt, never
    deleted by this writer, and its presence is reported so an operator can see it."""

    def _stray(self, root, name=".kv-crossing-abc123", where=None, text="x"):
        folder = Path(root) / where if where else Path(root)
        path = folder / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_stray_temp_holding_a_valid_receipt_is_never_a_receipt_or_an_orphan_or_a_duplicate(self):
        with kv_chain() as (root, _):
            planned = cr.plan_crossing_record("kv", device_local(), root, crossing(), 41)
            receipts = Path(root) / rl.RECEIPT_LEDGERS["kv"]["storage_location"] / "receipts"
            for folder, name in ((None, ".kv-crossing-aaaa"), (rl.RECEIPT_LEDGERS["kv"]["storage_location"], ".kv-crossing-bbbb"),
                                 (Path(rl.RECEIPT_LEDGERS["kv"]["storage_location"]) / "receipts", ".kv-crossing-cccc.json")):
                self._stray(root, name, folder, json.dumps(planned["receipt"]))        # the exact receipt, in a temp file
            before = tree(root)
            plan = cr.plan_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertEqual((plan["disposition"], plan["adopts_orphan_receipt"]), ("ALLOW", False), plan)
            self.assertEqual(len(plan["stray_temp_files"]), 3)
            out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertEqual((out["disposition"], out["appended"], out["adopts_orphan_receipt"]), ("ALLOW", True, False))
            self.assertEqual(len(chain_of(root)), 2)
            self.assertTrue(all(k in tree(root) for k in before))                      # not one stray was deleted or changed
            self.assertTrue(all(tree(root)[k] == v for k, v in before.items() if ".kv-crossing-" in k))
            self.assertEqual(len(list(receipts.glob("*.json"))), 3)                    # genesis, the new receipt, the .json stray

    def test_the_lock_file_is_not_a_stray_and_a_clean_store_reports_none(self):
        with kv_chain() as (root, _):
            self.assertEqual(cr.append_crossing_record("kv", device_local(), root, crossing(), 41)["stray_temp_files"], [])
            self.assertTrue((Path(root) / cr.LOCK_NAME).exists())
            self.assertEqual(cr.stray_temp_files("kv", root), [])
            self.assertEqual(cr.stray_temp_files("kv", None), [])

    def test_every_refusal_names_the_strays_in_its_detail_and_fields_and_deletes_nothing(self):
        with kv_chain() as (root, _):
            self.assertEqual(cr.append_crossing_record("kv", device_local(), root, crossing(), 41)["appended"], True)
            self._stray(root)
            before = _kv_tree_without_lock(root)
            for out in (cr.append_crossing_record("kv", device_local(), root, crossing(), 42),            # duplicate
                        cr.plan_crossing_record("kv", device_local(), root, crossing(digest="sha256:" + "0d" * 32), 41),  # stale epoch
                        cr.plan_crossing_record("kv", device_local(), root, {"path_id": 1}, 41)):             # malformed
                self.assertEqual(out["disposition"], "FAIL_CLOSED", out)
                self.assertEqual(out["stray_temp_files"], [".kv-crossing-abc123"])
                self.assertIn(".kv-crossing-abc123", out["detail"])
                self.assertIn("not deleted", out["detail"])
            self.assertEqual(_kv_tree_without_lock(root), before)

    def test_a_write_refusal_also_reports_the_strays(self):
        with kv_chain() as (root, _):
            self._stray(root)
            with store_fault("link", OSError(1, "no hard links")):
                out = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            self.assertSix(out, cr.HARDLINK_CODE, "D")
            self.assertEqual(out["stray_temp_files"], [".kv-crossing-abc123"])
            self.assertIn(".kv-crossing-abc123", out["detail"])

    def test_a_hard_kill_between_mkstemp_and_unlink_leaves_a_stray_that_the_next_call_reports(self):
        with kv_chain() as (root, _):
            real = cr.os.unlink

            def kill(*a, **k):
                raise Crash()           # the process dies before its temp file is removed

            cr.os.unlink = kill
            try:
                with self.assertRaises(Crash):
                    cr.append_crossing_record("kv", device_local(), root, crossing(), 41)
            finally:
                cr.os.unlink = real
            strays = cr.stray_temp_files("kv", root)
            self.assertTrue(strays and all(s.startswith(".kv-crossing-") for s in strays), strays)
            after = cr.append_crossing_record("kv", device_local(), root, crossing(), 41)    # same epoch: adopts the orphan
            self.assertEqual((after["disposition"], after["appended"]), ("ALLOW", True), after)
            self.assertEqual(after["stray_temp_files"], strays)
            self.assertEqual(sorted(p for p in strays if (Path(root) / p).exists()), strays)    # still there, never deleted


class TornReceiptBlocksEveryCrossingByDesign(Base):
    """P4's note (c): intentional and fail-closed; documented in the module docstring. No behaviour change."""

    def test_a_torn_receipt_file_blocks_every_new_crossing_and_is_neither_repaired_nor_deleted(self):
        with kv_chain() as (root, _):
            torn = (Path(root) / rl.RECEIPT_LEDGERS["kv"]["storage_location"] / "receipts" / ("ab" * 32 + ".json"))
            torn.write_text('{"schema": "stegverse.repo-transition-rec', encoding="utf-8")
            before = _kv_tree_without_lock(root)
            for n in (1, 2):
                out = cr.append_crossing_record("kv", device_local(), root, crossing(f"comm-{n}", "sha256:" + f"{n:02x}" * 32), 41)
                self.assertSix(out, cr.UNREADABLE_CODE, "C")
            self.assertEqual(_kv_tree_without_lock(root), before)
            self.assertIn("blocks every new crossing", cr.__doc__)
            self.assertIn("intentional", cr.__doc__)


class NoOtherSurface(unittest.TestCase):
    def test_module_imports_no_clock_network_process_or_key_code_and_names_no_org_ref_to_write(self):
        tree_ = ast.parse((ROOT / "runtime" / "kv_crossing_records.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree_):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertTrue(imported <= {"__future__", "fcntl", "json", "os", "tempfile", "pathlib", "typing", "runtime"}, imported)
        source = (ROOT / "runtime" / "kv_crossing_records.py").read_text(encoding="utf-8")
        for needle in ("time.time", "datetime", "subprocess", "socket", "urllib", "requests", "ed25519", "private_key",
                       "refs/stegverse/organization-ledger", "git push", "workflow_dispatch"):
            self.assertNotIn(needle, source.replace("organization-ledger ref", ""), needle)

    def test_production_designation_declares_no_new_path_id(self):
        for which in rl.RECEIPT_LEDGERS:
            before = json.loads((ROOT / rl.RECEIPT_LEDGERS[which]["contract_path"]).read_text())
            paths = before["ledger_designation"]["rollback_watermark_source"]["org_crossing_cross_check"]["path_ids"]
            self.assertTrue(paths and all(p.endswith(rl.PATH_ID_SUFFIX) for p in paths), paths)
            cr.plan_crossing_record(which, None, None, crossing(), 40)
            after = json.loads((ROOT / rl.RECEIPT_LEDGERS[which]["contract_path"]).read_text())
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
