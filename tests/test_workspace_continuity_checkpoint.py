from runtime.workspace_continuity_checkpoint import (
    CHECKPOINT_SCHEMA, checkpoint_digest, validate_checkpoint, verify_transition, CheckpointError,
)

REV_A = "a" * 64
REV_B = "b" * 64
CTX = {"principal_id": "user:1", "workspace_type": "PERSONAL", "workspace_id": "ws:personal:1"}

def accept_all(anchor): return True

def make(*, seq=0, epoch=0, grant=0, rev=REV_A, prev=None, observed="2026-10-10T12:00:00Z", principal="user:1", anchor=None, **extra):
    cp = {"schema": CHECKPOINT_SCHEMA, "principal_id": principal, "workspace_type": "PERSONAL", "workspace_id": "ws:personal:1",
          "grant_epoch": grant, "source_epoch": epoch, "sequence": seq, "source_revision": rev,
          "previous_checkpoint_digest": prev, "observed_at": observed,
          "anchor": anchor or {"kind": "RECEIPT_REF", "ref": "receipt:%d:%d" % (epoch, seq)}, "authority_effect": "NONE", **extra}
    cp["checkpoint_digest"] = checkpoint_digest(cp)
    return cp

def verify(prev, cur, **kw):
    kw.setdefault("anchor_verifier", accept_all)
    return verify_transition(prev, cur, **CTX, **kw)

def test_first_checkpoint_and_sequence_advance_verified():
    first = make()
    d = verify(None, first)
    assert d["disposition"] == "ALLOW" and d["predicate"] == "FIRST_CHECKPOINT" and d["replay_status"] == "VERIFIED" and d["authority_effect"] == "NONE"
    second = make(seq=1, prev=first["checkpoint_digest"], rev=REV_B)
    assert verify(first, second)["predicate"] == "SEQUENCE_ADVANCED"

def test_changed_source_requires_link_and_old_content_replay_is_refused():
    first = make(); second = make(seq=1, prev=first["checkpoint_digest"], rev=REV_B)
    replay_old = make(seq=0, rev=REV_A, observed="2026-10-10T13:00:00Z")
    assert verify(second, replay_old)["predicate"] == "CHECKPOINT_REPLAY_OR_ROLLBACK"
    unlinked_new_revision = make(seq=2, prev=first["checkpoint_digest"], rev=REV_A)
    assert verify(second, unlinked_new_revision)["predicate"] == "CHECKPOINT_FORK"

def test_fork_at_same_sequence_and_idempotent_reobservation():
    first = make()
    assert verify(first, make(rev=REV_B))["predicate"] == "CHECKPOINT_FORK"
    assert verify(first, dict(first))["predicate"] == "IDEMPOTENT_REOBSERVATION"

def test_clock_regression_is_tolerated_when_order_and_links_hold():
    first = make(observed="2026-10-10T12:00:00Z")
    later = make(seq=1, prev=first["checkpoint_digest"], observed="2026-10-10T11:00:00Z")
    d = verify(first, later)
    assert d["disposition"] == "ALLOW" and d["replay_status"] == "VERIFIED"

def test_valid_restart_links_to_last_accepted_and_unlinked_restart_is_denied():
    first = make(); second = make(seq=1, prev=first["checkpoint_digest"])
    restart = make(epoch=1, seq=0, prev=second["checkpoint_digest"])
    assert verify(second, restart)["predicate"] == "VALID_RESTART"
    assert verify(second, make(epoch=1, seq=0, prev=None))["predicate"] == "CHECKPOINT_RESTART_UNLINKED"
    assert verify(second, make(epoch=1, seq=3, prev=second["checkpoint_digest"]))["predicate"] == "CHECKPOINT_RESTART_UNLINKED"
    assert verify(restart, make(epoch=0, seq=2, prev=second["checkpoint_digest"]))["predicate"] == "CHECKPOINT_SOURCE_EPOCH_REGRESSED"

def test_cross_device_continuation_is_device_independent():
    first = make(anchor={"kind": "RECEIPT_REF", "ref": "receipt:iphone"})
    from_other_device = make(seq=1, prev=first["checkpoint_digest"], anchor={"kind": "SIGNATURE", "ref": "sig:laptop"})
    assert verify(first, from_other_device)["disposition"] == "ALLOW"
    assert verify(first, make(seq=1, prev=first["checkpoint_digest"], device_id="x"))["predicate"].startswith("CHECKPOINT_MALFORMED:checkpoint_field_forbidden:device_id")

def test_cross_session_other_principal_or_context_is_denied():
    first = make()
    other_user = make(seq=1, prev=first["checkpoint_digest"], principal="user:2")
    d = verify(first, other_user)
    assert d["disposition"] == "DENY" and d["predicate"] == "CHECKPOINT_CONTEXT_MISMATCH" and d["replay_status"] == "REFUSED"
    org = dict(make(seq=1, prev=first["checkpoint_digest"]), workspace_type="ORGANIZATIONAL"); org["checkpoint_digest"] = checkpoint_digest(org)
    assert verify(first, org)["predicate"] == "CHECKPOINT_CONTEXT_MISMATCH"

def test_revoked_or_regressed_grant_is_denied():
    first = make(grant=2)
    assert verify(first, make(seq=1, grant=2, prev=first["checkpoint_digest"]), revoked_grant_epochs={2})["predicate"] == "CHECKPOINT_GRANT_REVOKED"
    assert verify(first, make(seq=1, grant=1, prev=first["checkpoint_digest"]))["predicate"] == "CHECKPOINT_GRANT_EPOCH_REGRESSED"
    assert verify(first, make(seq=1, grant=3, prev=first["checkpoint_digest"]))["disposition"] == "ALLOW"

def test_gap_and_unknown_prior_fail_closed():
    first = make()
    assert verify(first, make(seq=3, prev="c" * 64))["predicate"] == "CHECKPOINT_CHAIN_GAP"
    d = verify(None, make(seq=5, prev="c" * 64))
    assert d["disposition"] == "FAIL_CLOSED" and d["predicate"] == "CHECKPOINT_PRIOR_UNKNOWN" and d["replay_status"] == "UNKNOWN"

def test_anchor_is_never_assumed():
    first = make()
    no_verifier = verify_transition(None, first, **CTX)
    assert no_verifier["disposition"] == "FAIL_CLOSED" and no_verifier["replay_status"] == "UNKNOWN" and no_verifier["predicate"].startswith("CHECKPOINT_ANCHOR_VERIFIER_UNAVAILABLE")
    assert verify(None, first, anchor_verifier=lambda a: False)["predicate"].startswith("CHECKPOINT_ANCHOR_UNVERIFIED")
    assert verify(None, first, anchor_verifier=lambda a: "yes")["disposition"] == "FAIL_CLOSED"
    def boom(a): raise RuntimeError("x")
    assert verify(None, first, anchor_verifier=boom)["disposition"] == "FAIL_CLOSED"

def test_malformed_and_tampered_checkpoints_fail_closed():
    first = make()
    tampered = dict(first, sequence=7)
    assert verify(None, tampered)["predicate"] == "CHECKPOINT_MALFORMED:checkpoint_digest_mismatch"
    for bad in [None, "x", dict(first, schema="other"), dict(first, authority_effect="ALLOW"), dict(first, sequence=-1), dict(first, sequence=True), dict(first, source_revision="zz"), dict(first, anchor={"kind": "NONE", "ref": ""})]:
        assert verify(None, bad)["disposition"] == "FAIL_CLOSED"
    try: validate_checkpoint(dict(first, replay_status="VERIFIED")); assert False
    except CheckpointError as exc: assert "checkpoint_field_forbidden:replay_status" in str(exc)
    assert verify(dict(first, sequence=9), make(seq=1, prev=first["checkpoint_digest"]))["predicate"].startswith("PREVIOUS_CHECKPOINT_MALFORMED")
