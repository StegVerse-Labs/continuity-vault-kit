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
