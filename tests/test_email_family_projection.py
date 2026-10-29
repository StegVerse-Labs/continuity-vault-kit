"""Email-family projection from ADMIT receipts (Site#1509 lane A; Goal StegVerse-org/.github#164).

SOURCE + LOCAL_TEST evidence only: no provider, no mailbox, no SKAP resolution, no KV write outside a temp dir.
Every refusal must fail closed with the six actionable fields, and the ALLOW projection must be accepted
verbatim by the existing family-projection delivery reader (no new query class).
"""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone, tzinfo
from pathlib import Path

from runtime.email_continuity import EmailAccountMapping, bind_skap_credential, create_mapping, mark_session_verified, revoke_mapping
from runtime.email_family_projection import GENESIS_HEAD, SCHEMA, _body, _digest, project_email_family
from runtime.email_ingress_pipeline import decide, stage_message
from runtime.workspace_family_projections import get_personal_family_projections

FIXED = datetime(2026, 10, 28, 23, 40, 0, tzinfo=timezone.utc)
SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint", "owning_existing_goal", "next_attempt")


def clock():
    return FIXED


def verified(address="owner@gmail.com", ref="skap://kv/email/owner-gmail"):
    m = create_mapping(email_address=address, provider_id="google-gmail", provider_route="gmail-api")
    return mark_session_verified(bind_skap_credential(m, skap_credential_ref=ref)).to_dict()


def receipt(mapping, provider_message_id="m-1", payload="hello", signals=()):
    staged = stage_message(mapping_id=mapping["mapping_id"], provider_message_id=provider_message_id,
                           from_address="a@example.com", subject="s", payload=payload)
    r, _ = decide(staged, signals=signals)
    return r.to_dict()


def run(**kw):
    kw.setdefault("clock", clock)
    prior = kw.get("prior")
    kw.setdefault("accepted_head_digest", prior.get("projection_digest") if isinstance(prior, dict) else GENESIS_HEAD)
    return project_email_family(**kw)


class EmailFamilyProjectionTest(unittest.TestCase):
    def setUp(self):
        self.m = verified()
        self.r1 = receipt(self.m, "m-1")
        self.r2 = receipt(self.m, "m-2")

    def first(self):
        d = run(receipts=[self.r1], mappings=[self.m], provider_positions={self.m["mapping_id"]: 10})
        self.assertEqual(d["disposition"], "ALLOW", d)
        return d["projection"]

    def refused(self, d, disposition, code):
        self.assertEqual(d["disposition"], disposition, d)
        self.assertEqual(d["failure_code"], code, d)
        for field in SIX:
            self.assertTrue(isinstance(d.get(field), str) and d[field], field)
        self.assertIsNone(d["projection"])
        self.assertEqual(d["authority_effect"], "NONE")
        self.assertIs(d["runtime_evidence"], False)

    # --- ALLOW shape and reuse of the existing family-projection contract -------------------------------------
    def test_admit_receipt_projects_payload_free_rows_with_skap_reference_only(self):
        p = self.first()
        self.assertEqual(p["schema"], SCHEMA)
        self.assertEqual(p["workspace_type"], "PERSONAL")
        self.assertEqual([m["receipt_id"] for m in p["messages"]], [self.r1["receipt_id"]])
        self.assertIs(p["messages"][0]["payload_present"], False)
        self.assertNotIn("hello", json.dumps(p))
        self.assertNotIn("owner@gmail.com", json.dumps(p))
        acct = p["accounts"][0]
        self.assertEqual(acct["skap_ref"], "skap://kv/email/owner-gmail")
        self.assertEqual(acct["cursor"]["sequence"], 1)
        self.assertEqual(acct["cursor"]["provider_position"], 10)
        self.assertEqual(acct["cursor"]["head_receipt_id"], self.r1["receipt_id"])
        for flag in ("credential_material_present", "provider_operation_authorized", "workspace_grants_authority"):
            self.assertIs(p[flag], False)
        self.assertEqual(p["authority_effect"], "NONE")
        self.assertEqual(p["projection_metadata"]["grant_state"], "UNKNOWN")

    def test_deterministic_and_incremental(self):
        a, b = self.first(), self.first()
        self.assertEqual(a, b)
        d = run(receipts=[self.r2], mappings=[self.m], provider_positions={self.m["mapping_id"]: 11}, prior=a,
                accepted_head_digest=a["projection_digest"])
        self.assertEqual(d["disposition"], "ALLOW", d)
        p = d["projection"]
        self.assertEqual([m["sequence"] for m in p["messages"]], [1, 2])
        self.assertEqual(p["accounts"][0]["cursor"]["head_receipt_id"], self.r2["receipt_id"])

    def test_existing_family_reader_carries_email_projection_verbatim(self):
        p = self.first()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "KnowledgeVault"
            target = root / "_System" / "Workspace" / "projections" / "email-family.json"
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(p, sort_keys=True), encoding="utf-8")
            delivery = get_personal_family_projections(kv_data_root=root, clock=clock)
        self.assertEqual(delivery["state"], "KV_FAMILY_PROJECTIONS_PROJECTED")
        self.assertEqual(delivery["projection_schemas"], [SCHEMA])
        self.assertEqual(delivery["projections"][0], p)

    def test_revoked_account_retained_without_new_receipts(self):
        p = self.first()
        revoked = revoke_mapping(EmailAccountMapping(**self.m)).to_dict()
        d = run(receipts=[], mappings=[revoked], provider_positions={}, prior=p)
        self.assertEqual(d["disposition"], "ALLOW", d)
        self.assertEqual(d["projection"]["accounts"][0]["mapping_state"], "REVOKED")

    # --- negative tests: every guard fails closed with six fields ---------------------------------------------
    def test_unadmitted_messages_are_denied(self):
        for signals in (["spam_or_bulk_abuse"], ["phishing"], ["user_review_required"]):
            d = run(receipts=[receipt(self.m, "m-x", signals=signals)], mappings=[self.m], provider_positions={self.m["mapping_id"]: 1})
            self.refused(d, "DENY", "EMAIL_MESSAGE_UNADMITTED")
        staged = stage_message(mapping_id=self.m["mapping_id"], provider_message_id="m-y", from_address="a@example.com", subject="s", payload="p")
        fc, _ = decide(staged, signals=[], governance_available=False)
        self.refused(run(receipts=[dict(self.r1, trusted_projection_created=False)], mappings=[self.m], provider_positions={self.m["mapping_id"]: 1}),
                     "DENY", "EMAIL_MESSAGE_UNADMITTED")
        self.refused(run(receipts=[fc.to_dict()], mappings=[self.m], provider_positions={self.m["mapping_id"]: 1}), "DENY", "EMAIL_MESSAGE_UNADMITTED")

    def test_revoked_mapping_denies_new_admission(self):
        revoked = revoke_mapping(EmailAccountMapping(**self.m)).to_dict()
        self.refused(run(receipts=[self.r1], mappings=[revoked], provider_positions={self.m["mapping_id"]: 1}), "DENY", "EMAIL_MAPPING_REVOKED")

    def test_unverified_session_denied(self):
        bound = bind_skap_credential(create_mapping(email_address="owner@gmail.com", provider_id="google-gmail", provider_route="gmail-api"),
                                     skap_credential_ref="skap://kv/email/owner-gmail").to_dict()
        self.refused(run(receipts=[self.r1], mappings=[bound], provider_positions={self.m["mapping_id"]: 1}), "DENY", "EMAIL_MAPPING_SESSION_UNVERIFIED")

    def test_duplicate_admit_in_batch_and_replay_against_prior_denied(self):
        self.refused(run(receipts=[self.r1, copy.deepcopy(self.r1)], mappings=[self.m], provider_positions={self.m["mapping_id"]: 1}),
                     "DENY", "EMAIL_ADMIT_REPLAYED")
        p = self.first()
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={self.m["mapping_id"]: 11}, prior=p),
                     "DENY", "EMAIL_ADMIT_REPLAYED")

    def test_content_drift_under_same_message_identity_fails_closed(self):
        p = self.first()
        drifted = receipt(self.m, "m-1", payload="changed")
        self.refused(run(receipts=[drifted], mappings=[self.m], provider_positions={self.m["mapping_id"]: 11}, prior=p),
                     "FAIL_CLOSED", "EMAIL_CONTENT_DRIFT")

    def test_provider_cursor_rollback_and_non_advance_denied(self):
        p = self.first()
        mid = self.m["mapping_id"]
        self.refused(run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 9}, prior=p), "DENY", "EMAIL_PROVIDER_CURSOR_ROLLBACK")
        self.refused(run(receipts=[], mappings=[self.m], provider_positions={mid: 3}, prior=p), "DENY", "EMAIL_PROVIDER_CURSOR_ROLLBACK")

    def test_equal_provider_position_admits_new_messages_but_not_replays(self):
        # Gmail may deliver several pages at one history_id (StegAgents #46): equal position + new message ids is ALLOW.
        p = self.first()
        mid = self.m["mapping_id"]
        d = run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 10}, prior=p)
        self.assertEqual(d["disposition"], "ALLOW", d)
        self.assertEqual(d["projection"]["accounts"][0]["cursor"]["provider_position"], 10)
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: 10}, prior=p), "DENY", "EMAIL_ADMIT_REPLAYED")
        self.refused(run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 9}, prior=p), "DENY", "EMAIL_PROVIDER_CURSOR_ROLLBACK")

    def test_provider_cursor_ref_validated_and_carried_forward(self):
        mid = self.m["mapping_id"]
        ref = "sha256:" + "c" * 64
        p = run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: int("10")}, provider_cursor_refs={mid: ref})["projection"]
        self.assertEqual(p["accounts"][0]["cursor"]["provider_cursor_ref"], ref)
        q = run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 11}, prior=p)["projection"]
        self.assertEqual(q["accounts"][0]["cursor"]["provider_cursor_ref"], ref)
        self.assertIsNone(self.first()["accounts"][0]["cursor"]["provider_cursor_ref"])
        for bad in ("c" * 64, "sha256:" + "C" * 64, "sha256:" + "c" * 63, 5):
            self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: 10}, provider_cursor_refs={mid: bad}),
                         "FAIL_CLOSED", "EMAIL_PROVIDER_CURSOR_REF_INVALID")
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: 10}, provider_cursor_refs=[ref]),
                     "FAIL_CLOSED", "EMAIL_PROVIDER_CURSOR_REF_INVALID")
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: 10}, provider_cursor_refs={"kv-email:" + "f" * 64: ref}),
                     "DENY", "EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH")
        bad_prior = copy.deepcopy(p); bad_prior["accounts"][0]["cursor"]["provider_cursor_ref"] = "not-a-digest"
        bad_prior["projection_digest"] = _digest(_body(bad_prior["accounts"], bad_prior["messages"]))
        self.refused(run(receipts=[], mappings=[self.m], provider_positions={}, prior=bad_prior), "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_INVALID")

    def test_digests_use_sha256_prefix(self):
        p = self.first()
        self.assertRegex(p["projection_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(p["accounts"][0]["cursor"]["chain_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(p["projection_metadata"]["provenance_ref"], "kv-email-ingress-admit-receipts:" + p["projection_digest"])

    def test_accepted_head_is_required_and_genesis_is_explicit(self):
        mid = self.m["mapping_id"]
        with self.assertRaises(TypeError):
            project_email_family(receipts=[self.r1], mappings=[self.m], provider_positions={mid: 1}, clock=clock)
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: 1}, accepted_head_digest=None),
                     "DENY", "EMAIL_PROJECTION_ROLLBACK")
        p = self.first()
        self.refused(run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 11}, prior=p, accepted_head_digest=GENESIS_HEAD),
                     "DENY", "EMAIL_PROJECTION_ROLLBACK")

    def test_raising_inputs_and_deep_nesting_fail_closed(self):
        mid = self.m["mapping_id"]

        def boom():
            raise RuntimeError("clock down")

        def gen():
            yield self.r1
            raise RuntimeError("iterable broke")

        deep = "x"
        for _ in range(100000):
            deep = [deep]
        self.refused(run(receipts=[dict(self.r1, reason=deep)], mappings=[self.m], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_INPUT_MALFORMED")
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: 1}, clock=boom), "FAIL_CLOSED", "EMAIL_INPUT_MALFORMED")
        self.refused(run(receipts=gen(), mappings=[self.m], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_INPUT_MALFORMED")

    def test_receipt_field_formats_enforced_even_with_recomputed_receipt_id(self):
        mid = self.m["mapping_id"]

        def forged(**over):
            r = dict(self.r1, **over)
            material = {k: r[k] for k in ("mapping_id", "canonical_message_id", "staged_content_hash", "decision", "reason")}
            r["receipt_id"] = "kv-email-receipt:" + hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            return r

        for over in ({"staged_content_hash": "sha256:" + "a" * 63}, {"staged_content_hash": "md5:" + "a" * 64},
                     {"staged_content_hash": "sha256:" + "A" * 64}, {"canonical_message_id": "kv-email-message:" + "a" * 65},
                     {"canonical_message_id": "msg-1"}, {"reason": 7}):
            self.refused(run(receipts=[forged(**over)], mappings=[self.m], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_RECEIPT_FORMAT_INVALID")

    def test_credential_shaped_values_and_unicode_keys_fail_closed(self):
        mid = self.m["mapping_id"]
        for value in ("Bearer abc.def", "ghp_" + "a" * 36, "github_pat_11AAA", "-----BEGIN PRIVATE KEY-----", "AKIA" + "A" * 16,
                      "xoxb-123-456", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig"):
            self.refused(run(receipts=[dict(self.r1, reason=value)], mappings=[self.m], provider_positions={mid: 1}),
                         "FAIL_CLOSED", "EMAIL_SECRET_FIELD_PRESENT")
        # Fullwidth "ＴＯＫＥＮ" normalises (NFKC) to "TOKEN".
        self.refused(run(receipts=[dict(self.r1, **{"\uff34\uff2f\uff2b\uff25\uff2e": "x"})], mappings=[self.m], provider_positions={mid: 1}),
                     "FAIL_CLOSED", "EMAIL_SECRET_FIELD_PRESENT")
        for ref in ("skap://a b", "skap://x\n"):
            self.refused(run(receipts=[self.r1], mappings=[dict(self.m, skap_credential_ref=ref)], provider_positions={mid: 1}),
                         "FAIL_CLOSED", "EMAIL_SKAP_REFERENCE_INVALID")

    def test_prior_rows_and_cursor_strictly_checked(self):
        mid = self.m["mapping_id"]
        p = run(receipts=[self.r1, self.r2], mappings=[self.m], provider_positions={mid: 10})["projection"]

        def redigest(q):
            q["projection_digest"] = _digest(_body(q["accounts"], q["messages"])); return q

        cases = [
            (lambda q: q["messages"][0].update(payload_present=True), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["messages"][0].update(trust_state="STAGED_UNTRUSTED"), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["messages"][0].update(subject="leak"), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["messages"][0].pop("payload_present"), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["accounts"][0].update(note="x"), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["accounts"][0]["cursor"].update(extra=1), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["accounts"][0].update(cursor="c"), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["accounts"][0].update(cursor=sorted(q["accounts"][0]["cursor"])), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["accounts"][0]["cursor"].update(head_receipt_id=self.r1["receipt_id"]), "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT"),
            (lambda q: q["accounts"][0]["cursor"].update(provider_position=True), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["accounts"][0]["cursor"].update(provider_position=-1), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["accounts"][0]["cursor"].update(provider_position=10.0), "EMAIL_PRIOR_PROJECTION_INVALID"),
            (lambda q: q["accounts"][0]["cursor"].update(sequence=2.0), "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT"),
        ]
        for mutate, code in cases:
            q = copy.deepcopy(p); mutate(q)
            self.refused(run(receipts=[], mappings=[self.m], provider_positions={}, prior=redigest(q)), "FAIL_CLOSED", code)
        one = run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: 10})["projection"]
        q = copy.deepcopy(one); q["messages"][0]["sequence"] = True
        self.refused(run(receipts=[], mappings=[self.m], provider_positions={}, prior=redigest(q)), "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT")

    def test_provider_cursor_absent_or_opaque_fails_closed(self):
        mid = self.m["mapping_id"]
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={}), "FAIL_CLOSED", "EMAIL_PROVIDER_CURSOR_ABSENT")
        for bad in ("deltaLink-opaque", -1, True, 1.5):
            self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={mid: bad}), "FAIL_CLOSED", "EMAIL_PROVIDER_CURSOR_INVALID")

    def test_projection_rollback_to_older_or_absent_prior_denied(self):
        p1 = self.first()
        p2 = run(receipts=[self.r2], mappings=[self.m], provider_positions={self.m["mapping_id"]: 11}, prior=p1)["projection"]
        r3 = receipt(self.m, "m-3")
        self.refused(run(receipts=[r3], mappings=[self.m], provider_positions={self.m["mapping_id"]: 12}, prior=p1,
                         accepted_head_digest=p2["projection_digest"]), "DENY", "EMAIL_PROJECTION_ROLLBACK")
        self.refused(run(receipts=[r3], mappings=[self.m], provider_positions={self.m["mapping_id"]: 12}, prior=None,
                         accepted_head_digest=p2["projection_digest"]), "DENY", "EMAIL_PROJECTION_ROLLBACK")

    def test_cross_account_provenance_mismatch_denied(self):
        other = verified("other@outlook.com", "skap://kv/email/other")
        foreign = receipt(other, "m-1")
        self.refused(run(receipts=[foreign], mappings=[self.m], provider_positions={self.m["mapping_id"]: 1}),
                     "DENY", "EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH")
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions={self.m["mapping_id"]: 1, other["mapping_id"]: 1}),
                     "DENY", "EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH")
        # Same canonical message id re-presented under another account (receipt re-pointed, digest recomputed).
        p = self.first()
        moved = dict(self.r1, mapping_id=other["mapping_id"])
        material = {k: moved[k] for k in ("mapping_id", "canonical_message_id", "staged_content_hash", "decision", "reason")}
        moved["receipt_id"] = "kv-email-receipt:" + hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.refused(run(receipts=[moved], mappings=[self.m, other], provider_positions={other["mapping_id"]: 1}, prior=p),
                     "DENY", "EMAIL_CROSS_ACCOUNT_PROVENANCE_MISMATCH")

    def test_malformed_or_duplicate_mappings_fail_closed(self):
        mid = self.m["mapping_id"]
        self.refused(run(receipts=[self.r1], mappings=[self.m, dict(self.m)], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_MAPPING_INVALID")
        self.refused(run(receipts=[self.r1], mappings=[dict(self.m, schema="x")], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_MAPPING_INVALID")
        self.refused(run(receipts=[self.r1], mappings=[dict(self.m, note="x")], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_MAPPING_INVALID")
        self.refused(run(receipts=[self.r1], mappings=[dict(self.m, skap_credential_ref=None)], provider_positions={mid: 1}),
                     "FAIL_CLOSED", "EMAIL_SKAP_REFERENCE_INVALID")

    def test_malformed_inputs_fail_closed(self):
        mid = self.m["mapping_id"]
        self.refused(run(receipts=[self.r1], mappings=["owner@gmail.com"], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_MAPPING_INVALID")
        self.refused(run(receipts=[self.r1], mappings=[self.m], provider_positions=[mid]), "FAIL_CLOSED", "EMAIL_PROVIDER_CURSOR_INVALID")
        self.refused(run(receipts=None, mappings=[self.m], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_INPUT_MALFORMED")
        p = self.first()
        self.refused(run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 11}, prior=dict(p, schema="stegverse.kv.other-projection/v1")),
                     "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_INVALID")
        self.refused(run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 11}, prior=dict(p, accounts={})),
                     "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_INVALID")

    def test_prior_structure_drift_fails_closed_even_with_recomputed_digest(self):
        mid = self.m["mapping_id"]
        p = run(receipts=[self.r1, self.r2], mappings=[self.m], provider_positions={mid: 10})["projection"]

        def redigest(q):
            q["projection_digest"] = _digest(_body(q["accounts"], q["messages"])); return q

        dup = copy.deepcopy(p); dup["accounts"].append(copy.deepcopy(dup["accounts"][0]))
        self.refused(run(receipts=[], mappings=[self.m], provider_positions={}, prior=redigest(dup)), "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_INVALID")
        orphan = copy.deepcopy(p); orphan["messages"][0]["mapping_id"] = "kv-email:" + "f" * 64
        self.refused(run(receipts=[], mappings=[self.m], provider_positions={}, prior=redigest(orphan)), "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT")
        reorder = copy.deepcopy(p); reorder["messages"][0]["sequence"], reorder["messages"][1]["sequence"] = 2, 1
        self.refused(run(receipts=[], mappings=[self.m], provider_positions={}, prior=redigest(reorder)), "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT")

    def test_prior_account_without_mapping_fails_closed(self):
        p = self.first()
        other = verified("other@outlook.com", "skap://kv/email/other")
        self.refused(run(receipts=[], mappings=[other], provider_positions={}, prior=p), "FAIL_CLOSED", "EMAIL_PRIOR_ACCOUNT_UNMAPPED")

    def test_absent_and_stale_receipts_fail_closed(self):
        mid = self.m["mapping_id"]
        for absent in (None, {}, {k: v for k, v in self.r1.items() if k != "receipt_id"}, dict(self.r1, staged_content_hash="")):
            self.refused(run(receipts=[absent], mappings=[self.m], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_ADMIT_RECEIPT_ABSENT")
        for stale in (dict(self.r1, schema="stegverse.kv.email-ingress-receipt/v0"), dict(self.r1, payload_retained_in_receipt=True),
                      dict(self.r1, authority_effect="GRANTED"), dict(self.r1, payload="hello")):
            self.refused(run(receipts=[stale], mappings=[self.m], provider_positions={mid: 1}), "FAIL_CLOSED", "EMAIL_ADMIT_RECEIPT_STALE")

    def test_secret_fields_fail_closed_and_only_skap_references_pass(self):
        mid = self.m["mapping_id"]
        for key in ("access_token", "refresh_token", "app_password", "client_secret", "private_key"):
            self.refused(run(receipts=[self.r1], mappings=[dict(self.m, **{key: "x"})], provider_positions={mid: 1}),
                         "FAIL_CLOSED", "EMAIL_SECRET_FIELD_PRESENT")
            self.refused(run(receipts=[dict(self.r1, **{key: "x"})], mappings=[self.m], provider_positions={mid: 1}),
                         "FAIL_CLOSED", "EMAIL_SECRET_FIELD_PRESENT")
        self.refused(run(receipts=[self.r1], mappings=[dict(self.m, credential_secret_present_in_kv=True)], provider_positions={mid: 1}),
                     "FAIL_CLOSED", "EMAIL_SECRET_FIELD_PRESENT")
        for ref in ("ya29.raw-oauth-value", "https://vault/x", "skap://"):
            self.refused(run(receipts=[self.r1], mappings=[dict(self.m, skap_credential_ref=ref)], provider_positions={mid: 1}),
                         "FAIL_CLOSED", "EMAIL_SKAP_REFERENCE_INVALID")
        p = self.first()
        tampered = copy.deepcopy(p)
        tampered["accounts"][0]["oauth_token"] = "x"
        self.refused(run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 11}, prior=tampered),
                     "FAIL_CLOSED", "EMAIL_SECRET_FIELD_PRESENT")

    def test_digest_drift_fails_closed(self):
        mid = self.m["mapping_id"]
        self.refused(run(receipts=[dict(self.r1, reason="edited")], mappings=[self.m], provider_positions={mid: 1}),
                     "FAIL_CLOSED", "EMAIL_ADMIT_RECEIPT_DIGEST_DRIFT")
        self.refused(run(receipts=[self.r1], mappings=[dict(self.m, email_address="someone-else@gmail.com")], provider_positions={mid: 1}),
                     "FAIL_CLOSED", "EMAIL_MAPPING_DIGEST_DRIFT")
        p = self.first()
        body_edit = copy.deepcopy(p); body_edit["messages"][0]["staged_content_hash"] = "sha256:" + "0" * 64
        self.refused(run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 11}, prior=body_edit),
                     "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT")
        chain_edit = copy.deepcopy(p); chain_edit["accounts"][0]["cursor"]["chain_digest"] = "0" * 64
        chain_edit["projection_digest"] = _digest(_body(chain_edit["accounts"], chain_edit["messages"]))
        self.refused(run(receipts=[self.r2], mappings=[self.m], provider_positions={mid: 11}, prior=chain_edit),
                     "FAIL_CLOSED", "EMAIL_PRIOR_PROJECTION_DIGEST_DRIFT")

    def test_naive_clock_fails_closed(self):
        d = project_email_family(receipts=[self.r1], mappings=[self.m], provider_positions={self.m["mapping_id"]: 1},
                                 accepted_head_digest=GENESIS_HEAD, clock=lambda: datetime(2026, 10, 28))
        self.refused(d, "FAIL_CLOSED", "EMAIL_PROJECTION_CLOCK_INVALID")

        class NoOffset(tzinfo):
            def utcoffset(self, dt):
                return None

        d = run(receipts=[self.r1], mappings=[self.m], provider_positions={self.m["mapping_id"]: 1}, clock=lambda: datetime(2026, 10, 28, tzinfo=NoOffset()))
        self.refused(d, "FAIL_CLOSED", "EMAIL_PROJECTION_CLOCK_INVALID")


if __name__ == "__main__":
    unittest.main()
