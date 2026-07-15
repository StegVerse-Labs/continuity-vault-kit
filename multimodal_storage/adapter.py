from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ExperienceAccessPlan:
    experience_id: str
    principal_id: str
    permitted_stream_ids: tuple[str, ...]
    denied_stream_ids: tuple[str, ...]
    may_generate_reconstruction: bool
    completeness_status: str
    raw_access_granted: bool


def plan_experience_access(
    capsule: Mapping[str, Any],
    *,
    principal_id: str,
    requested_raw_access: bool = False,
    requested_generation: bool = False,
) -> ExperienceAccessPlan:
    """Produce a fail-closed access plan for one validated ExperienceCapsule.

    This adapter does not decrypt content and does not consume a reconstructive-
    memory capability. It narrows a capsule to the streams permitted by its own
    reconstruction-right declaration. A caller must still satisfy the existing
    reconstructive-memory proof, capability, lifecycle, and receipt boundaries.
    """

    if not principal_id:
        raise ValueError("principal_id is required")

    rights = [
        right
        for right in capsule.get("reconstruction_rights", [])
        if right.get("principal_id") == principal_id
    ]
    if len(rights) != 1:
        raise PermissionError("exactly one reconstruction-right declaration is required")

    right = rights[0]
    may_access_raw = bool(right.get("may_access_raw", False))
    may_generate = bool(right.get("may_generate_reconstruction", False))

    if requested_raw_access and not may_access_raw:
        raise PermissionError("protected raw-evidence access is not granted")
    if requested_generation and not may_generate:
        raise PermissionError("generated reconstruction is not granted")

    permitted: list[str] = []
    denied: list[str] = []
    for stream in capsule.get("streams", []):
        stream_id = stream.get("stream_id")
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("capsule contains an invalid stream_id")

        is_raw = stream.get("artifact_class") == "protected_raw"
        is_generated = stream.get("artifact_class") == "generated_reconstruction"
        recallable = stream.get("user_recall_available") is True

        allowed = recallable
        if is_raw:
            allowed = requested_raw_access and may_access_raw
        if is_generated:
            allowed = requested_generation and may_generate and recallable

        (permitted if allowed else denied).append(stream_id)

    return ExperienceAccessPlan(
        experience_id=str(capsule.get("experience_id", "")),
        principal_id=principal_id,
        permitted_stream_ids=tuple(permitted),
        denied_stream_ids=tuple(denied),
        may_generate_reconstruction=may_generate,
        completeness_status=str(capsule.get("completeness_status", "materially_incomplete")),
        raw_access_granted=requested_raw_access and may_access_raw,
    )
