"""Non-controlling planner for storage-budget policy inspection.

The planner produces an advisory plan only. It does not activate sensors, change
retention, grant authority, or access protected evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.validate_storage_budget_policy import validate_policy


@dataclass(frozen=True)
class BudgetPlan:
    policy_id: str
    reconstruction_goal: str
    estimated_enabled_bytes_per_hour: int
    max_bytes_per_hour: int | None
    within_hourly_budget: bool | None
    required_properties: tuple[str, ...]
    enabled_streams: tuple[str, ...]
    exhaustion_behavior: str
    advisory_only: bool = True


def build_budget_plan(policy: dict[str, Any]) -> BudgetPlan:
    """Validate a policy and return a deterministic advisory summary."""
    validate_policy(policy)
    streams = [s for s in policy["capture_plan"]["streams"] if s["enabled"]]
    estimated = sum(int(s["estimated_bytes_per_hour"]) for s in streams)
    hourly = policy["capacity_budget"].get("max_bytes_per_hour")
    within = None if hourly is None else estimated <= int(hourly)
    required = tuple(sorted(
        item["property"] for item in policy["material_properties"]
        if item["requirement"] == "required"
    ))
    return BudgetPlan(
        policy_id=policy["policy_id"],
        reconstruction_goal=policy["reconstruction_goal"],
        estimated_enabled_bytes_per_hour=estimated,
        max_bytes_per_hour=hourly,
        within_hourly_budget=within,
        required_properties=required,
        enabled_streams=tuple(sorted(s["stream_ref"] for s in streams)),
        exhaustion_behavior=policy["budget_exhaustion_behavior"],
    )
