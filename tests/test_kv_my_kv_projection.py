from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.kv_instance_relationships import transition_request
from runtime.kv_my_kv_projection import MyKVProjectionError, build_instance_projection, build_set_projection
from runtime.kv_relationship_state_store import initialize_store, persist_transition_request


def _make_instance(root: Path, *, number: int, instance_id: str, set_id: str = "personal") -> None:
    path = root / "_System/Instances/instance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "stegverse.kv.instance/v1",
        "instance_id": instance_id,
        "instance_number": number,
        "logical_name": f"KV #{number}",
        "kv_set_id": set_id,
        "relationship": {"tier": "NOT_CONNECTED"},
        "storage": {"medium": "icloud-drive", "locator": f"icloud-slot-{number}", "provider_authority_effect": "NONE"},
    }), encoding="utf-8")
    initialize_store(root, kv_set_id=set_id, instance_id=instance_id)


def test_projection_exposes_metadata_only(tmp_path: Path) -> None:
    kv1 = tmp_path / "KnowledgeVault"
    _make_instance(kv1, number=1, instance_id="kvi_one")
    projection = build_instance_projection(kv1)
    assert projection["instance_id"] == "kvi_one"
    assert projection["relationship"]["tier"] == "NOT_CONNECTED"
    assert projection["management"]["request_connect_supported"] is True
    assert projection["management"]["provider_mutation_authorized"] is False
    assert projection["private_content_included"] is False
    assert projection["credential_material_included"] is False
    assert projection["authority_effect"] == "NONE_STATUS_ONLY"
    assert "content" not in projection
    assert "credentials" not in projection


def test_pending_request_is_visible_without_changing_tier(tmp_path: Path) -> None:
    kv1 = tmp_path / "KnowledgeVault"
    _make_instance(kv1, number=1, instance_id="kvi_one")
    request = transition_request(
        kv_set_id="personal",
        participant_instance_ids=["kvi_one", "kvi_two"],
        current_tier="NOT_CONNECTED",
        target_tier="CONNECTED",
    )
    persist_transition_request(kv1, request)
    projection = build_instance_projection(kv1)
    assert projection["relationship"]["tier"] == "NOT_CONNECTED"
    assert projection["relationship"]["pending_request_ids"] == [request["request_id"]]


def test_set_projection_orders_instances_and_requires_same_set(tmp_path: Path) -> None:
    kv1 = tmp_path / "KnowledgeVault"
    kv2 = tmp_path / "KnowledgeVault-2"
    _make_instance(kv2, number=2, instance_id="kvi_two")
    _make_instance(kv1, number=1, instance_id="kvi_one")
    projection = build_set_projection([kv2, kv1])
    assert projection["instance_count"] == 2
    assert [item["instance_number"] for item in projection["instances"]] == [1, 2]
    assert projection["private_content_included"] is False

    kv3 = tmp_path / "KnowledgeVault-3"
    _make_instance(kv3, number=3, instance_id="kvi_three", set_id="other")
    with pytest.raises(MyKVProjectionError):
        build_set_projection([kv1, kv3])


def test_relationship_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    kv1 = tmp_path / "KnowledgeVault"
    _make_instance(kv1, number=1, instance_id="kvi_one")
    state_path = kv1 / "_System/Instances/Relationships/relationship-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["instance_id"] = "kvi_tampered"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(MyKVProjectionError):
        build_instance_projection(kv1)
