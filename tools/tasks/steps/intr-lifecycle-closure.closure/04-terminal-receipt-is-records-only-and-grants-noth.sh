python - <<'PY'
from runtime.intr_lifecycle_closure import close_lifecycle, sha_uri
mid = "MR-CI-CLOSURE-CHECK"
entry = {
    "schema": "stegos.node_intr_outbox_entry.v1",
    "state": "LOCAL_OUTBOX_PENDING_NETWORK_DELIVERY",
    "materialization_id": mid,
    "node_id": "stegnode-web-ci",
    "interlock_id": "SV-IL-ci",
    "network_delivery_observed": False,
    "runtime_materialization_observed": False,
    "receiver_receipt_observed": False,
    "tvc_receipt_observed": False,
    "claim_or_fence_minted": False,
    "credential_authority": "TV/TVC",
    "github_token_runtime_authority": "NONE",
    "authority_effect": "NONE_LOCAL_CONTINUITY_ONLY",
}
entry["outbox_entry_hash"] = sha_uri(entry)
ingress = {
    "schema": "stegverse.stegbrowser-intr-materialization-ingress/v1",
    "state": "INGRESS_ADMITTED",
    "materialization_id": mid,
    "outbox_entry_hash": entry["outbox_entry_hash"],
    "claim_or_fence_minted": False,
    "credential_authority": "TV/TVC",
    "authority_effect": "NONE_INGRESS_ONLY",
}
materialization = {
    "schema": "stegverse.stegbrowser-intr-materialization-consumption/v1",
    "state": "MATERIALIZATION_EXECUTION_ATTEMPTED",
    "materialization_id": mid,
    "claim_or_fence_minted": False,
    "credential_authority": "TV/TVC",
    "authority_effect": "NONE_CONSUMPTION_ONLY",
}
result = close_lifecycle(
    outbox_entry=entry,
    ingress_receipt=ingress,
    materialization_receipt=materialization,
)
receipt = result["terminal_receipt"]
assert receipt["terminal_state"]["records_only"] is True
assert receipt["terminal_state"]["continued_authority"] is False
assert receipt["closure_grants_execution_authority"] is False
assert receipt["claim_or_fence_minted"] is False
assert receipt["authority_effect"] == "NONE_RECORDING_ONLY"
assert result["far_end_observation"]["authority_effect"] == "NONE_OBSERVATION_ONLY"
assert entry["receiver_receipt_observed"] is False, "node entry must not be mutated"
print("INTR_LIFECYCLE_CLOSURE_NON_AUTHORIZING_PASS")
PY
