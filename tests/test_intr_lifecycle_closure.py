"""Far-end InTr lifecycle closure.

These tests pin the boundary that was missing: a materialization that reached
``MATERIALIZATION_EXECUTION_ATTEMPTED`` and stopped, leaving the node's outbox
flags unanswerable and the organization's Master Records blockers standing.
"""

from __future__ import annotations

import copy

import pytest

from runtime.intr_lifecycle_closure import (
    CUSTODY_SCHEMA,
    OBSERVATION_SCHEMA,
    ORDERED_TRANSITIONS,
    REQUIRED_CLOSURE,
    TERMINAL_SCHEMA,
    LifecycleClosureError,
    build_closure_chain,
    close_lifecycle,
    sha_uri,
    verify_terminal_receipt,
)

MATERIALIZATION_ID = "MR-STEGBROWSER-CUSTODY-0123456789abcdef01234567"


def make_outbox_entry(**overrides):
    """An entry shaped as site/assets/stegbrowser-master-records-custody.js writes it."""
    request = {
        "schema": "stegverse.universal-intr-materialization-request/v1",
        "state": "QUEUED_FOR_EVENT_EPHEMERAL_MATERIALIZATION",
        "materialization_id": MATERIALIZATION_ID,
        "destination": {
            "boundary": "MASTER_RECORDS",
            "subsystem": "StegBrowser:RuntimeReadinessCustody",
        },
        "downstream_owner_ref": "master-records/orchestration",
        "request_grants_execution_authority": False,
        "transport_grants_execution_authority": False,
        "claim_or_fence_minted": False,
        "credential_authority": "TV/TVC",
        "github_token_runtime_authority": "NONE",
        "authority_effect": "NONE_REQUEST_ONLY",
    }
    entry = {
        "schema": "stegos.node_intr_outbox_entry.v1",
        "state": "LOCAL_OUTBOX_PENDING_NETWORK_DELIVERY",
        "materialization_id": MATERIALIZATION_ID,
        "node_id": "stegnode-web-2d6daa94e496d451d16bd5619bd30a25",
        "interlock_id": "SV-IL-300325da3411909dfa04678b",
        "materialization_request": request,
        "network_delivery_observed": False,
        "runtime_materialization_observed": False,
        "receiver_receipt_observed": False,
        "tvc_receipt_observed": False,
        "request_grants_execution_authority": False,
        "claim_or_fence_minted": False,
        "credential_authority": "TV/TVC",
        "github_token_runtime_authority": "NONE",
        "authority_effect": "NONE_LOCAL_CONTINUITY_ONLY",
    }
    entry.update(overrides)
    entry["outbox_entry_hash"] = sha_uri(entry)
    return entry


def make_ingress_receipt(outbox_entry, **overrides):
    receipt = {
        "schema": "stegverse.stegbrowser-intr-materialization-ingress/v1",
        "state": "INGRESS_ADMITTED",
        "materialization_id": outbox_entry["materialization_id"],
        "node_id": outbox_entry["node_id"],
        "interlock_id": outbox_entry["interlock_id"],
        "outbox_entry_hash": outbox_entry["outbox_entry_hash"],
        "queue_ref": f"intr-requests/{outbox_entry['materialization_id']}.json",
        "exact_request_validated": True,
        "write_once_persisted": True,
        "runtime_execution_attempted": False,
        "claim_or_fence_minted": False,
        "credential_authority": "TV/TVC",
        "github_token_runtime_authority": "NONE",
        "authority_effect": "NONE_INGRESS_ONLY",
    }
    receipt.update(overrides)
    return receipt


def make_materialization_receipt(outbox_entry, **overrides):
    receipt = {
        "schema": "stegverse.stegbrowser-intr-materialization-consumption/v1",
        "state": "MATERIALIZATION_EXECUTION_ATTEMPTED",
        "materialization_id": outbox_entry["materialization_id"],
        "execution_returncode": 0,
        "claim_or_fence_minted": False,
        "credential_authority": "TV/TVC",
        "authority_effect": "NONE_CONSUMPTION_ONLY",
    }
    receipt.update(overrides)
    return receipt


@pytest.fixture
def lane():
    entry = make_outbox_entry()
    return entry, make_ingress_receipt(entry), make_materialization_receipt(entry)


def close(lane, **kwargs):
    entry, ingress, materialization = lane
    return close_lifecycle(
        outbox_entry=entry,
        ingress_receipt=ingress,
        materialization_receipt=materialization,
        **kwargs,
    )


class TestClosure:
    def test_lifecycle_closes_and_terminal_receipt_verifies(self, lane):
        result = close(lane, source_commit="abc123")
        assert result["state"] == "LIFECYCLE_RECORDED"
        receipt = result["terminal_receipt"]
        assert receipt["schema"] == TERMINAL_SCHEMA
        assert receipt["state"] == "COMPLETE"
        # Verification is independent of construction.
        assert verify_terminal_receipt(receipt)["manifest_receipt_id"]

    def test_terminal_state_is_records_only_without_continued_authority(self, lane):
        terminal = close(lane)["terminal_receipt"]["terminal_state"]
        assert terminal["records_only"] is True
        assert terminal["continued_authority"] is False
        assert terminal["transition_id"] == "MASTER_RECORDS_CUSTODY_RECORDED"

    def test_all_four_transitions_are_recorded_in_order(self, lane):
        receipt = close(lane)["terminal_receipt"]
        closures = receipt["transition_closures"]
        assert [c["transition_id"] for c in closures] == list(ORDERED_TRANSITIONS)
        assert len(closures) == 4
        for closure in closures:
            for key, value in REQUIRED_CLOSURE.items():
                assert closure[key] == value

    def test_each_stage_links_its_immediate_predecessor(self, lane):
        closures = close(lane)["terminal_receipt"]["transition_closures"]
        assert closures[0]["predecessor_receipt_sha256"] is None
        for previous, current in zip(closures, closures[1:]):
            assert current["predecessor_receipt_sha256"] == previous["receipt_sha256"]

    def test_master_records_custody_record_is_written_and_self_hashed(self, lane):
        from runtime.intr_lifecycle_closure import sha256_hex

        record = close(lane, source_commit="deadbeef")["master_records_custody_record"]
        assert record["schema"] == CUSTODY_SCHEMA
        assert record["custody"]["status"] == "ACCEPTED_FOR_CUSTODY"
        assert record["validation"]["runtime_execution_claimed"] is False
        assert record["source"]["source_commit"] == "deadbeef"
        body = {k: v for k, v in record.items() if k != "record_hash"}
        assert sha256_hex(body) == record["record_hash"]

    def test_terminal_receipt_binds_the_custody_record(self, lane):
        result = close(lane)
        assert (
            result["terminal_receipt"]["master_records_record_hash"]
            == result["master_records_custody_record"]["record_hash"]
        )

    def test_closure_is_deterministic(self, lane):
        assert close(lane)["terminal_receipt"] == close(lane)["terminal_receipt"]


class TestFarEndObservation:
    """The flags nothing in the ecosystem could previously set."""

    def test_observation_answers_the_pending_flags_with_evidence(self, lane):
        result = close(lane)
        observation = result["far_end_observation"]
        assert observation["schema"] == OBSERVATION_SCHEMA
        assert observation["runtime_materialization_observed"] is True
        assert observation["receiver_receipt_observed"] is True
        assert (
            observation["terminal_receipt_id"]
            == result["terminal_receipt"]["manifest_receipt_id"]
        )
        assert (
            observation["master_records_record_hash"]
            == result["master_records_custody_record"]["record_hash"]
        )

    def test_tvc_receipt_stays_false_with_a_stated_reason(self, lane):
        """A separate provider boundary is not closed by this one."""
        observation = close(lane)["far_end_observation"]
        assert observation["tvc_receipt_observed"] is False
        assert observation["tvc_receipt_pending_reason"]

    def test_observation_grants_nothing(self, lane):
        observation = close(lane)["far_end_observation"]
        assert observation["observation_grants_execution_authority"] is False
        assert observation["claim_or_fence_minted"] is False
        assert observation["authority_effect"] == "NONE_OBSERVATION_ONLY"

    def test_observation_is_a_separate_artifact_not_a_mutation(self, lane):
        """The node's write-once entry must be left exactly as written."""
        entry, ingress, materialization = lane
        before = copy.deepcopy(entry)
        close(lane)
        assert entry == before


class TestFailClosed:
    def test_unreconstructable_outbox_entry_is_refused(self, lane):
        entry, ingress, materialization = lane
        entry["node_id"] = "stegnode-web-tampered"
        with pytest.raises(LifecycleClosureError) as excinfo:
            close((entry, ingress, materialization))
        assert "NODE_OUTBOX_ENTRY_WRITTEN:digest_reconstruction_mismatch" in str(excinfo.value)

    def test_ingress_bound_to_a_different_entry_is_refused(self, lane):
        entry, ingress, materialization = lane
        ingress["outbox_entry_hash"] = sha_uri({"other": "entry"})
        with pytest.raises(LifecycleClosureError) as excinfo:
            close((entry, ingress, materialization))
        assert "INTR_INGRESS_ADMITTED:outbox_entry_hash_mismatch" in str(excinfo.value)

    def test_blocked_materialization_cannot_be_recorded_as_complete(self, lane):
        entry, ingress, _ = lane
        blocked = make_materialization_receipt(
            entry, state="MATERIALIZATION_EXECUTION_BLOCKED", execution_returncode=2
        )
        with pytest.raises(LifecycleClosureError) as excinfo:
            close((entry, ingress, blocked))
        assert "execution_not_attempted" in str(excinfo.value)

    def test_unadmitted_ingress_is_refused(self, lane):
        entry, ingress, materialization = lane
        ingress["state"] = "REFUSED"
        with pytest.raises(LifecycleClosureError) as excinfo:
            close((entry, ingress, materialization))
        assert "state_not_admitted" in str(excinfo.value)

    def test_mismatched_materialization_id_is_refused(self, lane):
        entry, ingress, materialization = lane
        materialization["materialization_id"] = "MR-OTHER-LIFECYCLE"
        with pytest.raises(LifecycleClosureError) as excinfo:
            close((entry, ingress, materialization))
        assert "materialization_id_mismatch" in str(excinfo.value)

    def test_pre_promoted_evidence_is_refused(self, lane):
        """The emitting side may not assert that the receiver replied."""
        entry = make_outbox_entry(receiver_receipt_observed=True)
        with pytest.raises(LifecycleClosureError) as excinfo:
            close((entry, make_ingress_receipt(entry), make_materialization_receipt(entry)))
        assert "evidence_pre_promoted:receiver_receipt_observed" in str(excinfo.value)

    def test_stage_claiming_execution_authority_is_refused(self, lane):
        entry, ingress, materialization = lane
        ingress["claim_or_fence_minted"] = True
        with pytest.raises(LifecycleClosureError) as excinfo:
            close((entry, ingress, materialization))
        assert "authority_claimed:claim_or_fence_minted" in str(excinfo.value)

    def test_secret_bearing_field_is_refused(self, lane):
        entry, ingress, materialization = lane
        ingress["provider_api_key"] = "sk-live-0123456789abcdef"
        with pytest.raises(LifecycleClosureError) as excinfo:
            close((entry, ingress, materialization))
        assert "secret_bearing_field" in str(excinfo.value)

    def test_governance_assertions_are_not_mistaken_for_secrets(self, lane):
        """credential_authority: TV/TVC must survive the secret scan."""
        entry, ingress, materialization = lane
        assert ingress["credential_authority"] == "TV/TVC"
        assert entry["github_token_runtime_authority"] == "NONE"
        assert close((entry, ingress, materialization))["state"] == "LIFECYCLE_RECORDED"


class TestIndependentVerification:
    def test_tampered_terminal_receipt_fails_verification(self, lane):
        receipt = close(lane)["terminal_receipt"]
        receipt["terminal_state"]["continued_authority"] = True
        with pytest.raises(LifecycleClosureError) as excinfo:
            verify_terminal_receipt(receipt)
        assert "TERMINAL_CONTINUED_AUTHORITY_FALSE_REQUIRED" in str(excinfo.value)

    def test_reordered_closures_fail_verification(self, lane):
        receipt = close(lane)["terminal_receipt"]
        receipt["transition_closures"][1], receipt["transition_closures"][2] = (
            receipt["transition_closures"][2],
            receipt["transition_closures"][1],
        )
        with pytest.raises(LifecycleClosureError) as excinfo:
            verify_terminal_receipt(receipt)
        assert "MASTER_RECORDS_TRANSITION_ORDER_MISMATCH" in str(excinfo.value)

    def test_broken_predecessor_link_fails_verification(self, lane):
        receipt = close(lane)["terminal_receipt"]
        receipt["transition_closures"][2]["predecessor_receipt_sha256"] = sha_uri({"x": 1})
        with pytest.raises(LifecycleClosureError) as excinfo:
            verify_terminal_receipt(receipt)
        assert "MASTER_RECORDS_IMMEDIATE_PREDECESSOR_MISMATCH" in str(excinfo.value)

    def test_dropped_closure_fails_verification(self, lane):
        receipt = close(lane)["terminal_receipt"]
        receipt["transition_closures"].pop()
        with pytest.raises(LifecycleClosureError) as excinfo:
            verify_terminal_receipt(receipt)
        assert "MASTER_RECORDS_TRANSITION_CLOSURE_COUNT_MISMATCH" in str(excinfo.value)

    def test_receipt_id_must_reconstruct(self, lane):
        receipt = close(lane)["terminal_receipt"]
        receipt["replay_status"] = "PASS "
        with pytest.raises(LifecycleClosureError):
            verify_terminal_receipt(receipt)


class TestSdkContractConvergence:
    """The two InTr clients must agree on what 'finished' means.

    Values mirror ``_REQUIRED_CLOSURE`` and the terminal checks in the SDK's
    ``stegverse/manifest_state_transition_runtime.py``. If the SDK contract
    moves, this is where the divergence should surface.
    """

    def test_required_closure_matches_sdk(self):
        assert REQUIRED_CLOSURE == {
            "state": "RECORDED",
            "reconstruction_status": "PASS",
            "required_evidence_validation_status": "PASS",
        }

    def test_terminal_receipt_satisfies_the_sdk_result_predicates(self, lane):
        receipt = close(lane)["terminal_receipt"]
        assert receipt["state"] == "COMPLETE"
        assert receipt["replay_status"] == "PASS"
        assert receipt["reconstruction_status"] == "PASS"
        assert receipt["terminal_state"]["records_only"] is True
        assert receipt["terminal_state"]["continued_authority"] is False
        assert isinstance(receipt["manifest_receipt_id"], str)
        assert receipt["manifest_receipt_id"]
        ordered = receipt["resolved_ordered_transitions"]
        assert isinstance(ordered, list) and ordered
        assert all(isinstance(x, str) and x for x in ordered)
        assert len(receipt["transition_closures"]) == len(ordered)
