# Storage Budget to Experience Capsule Mapping

## Purpose

This mapping binds a validated storage-budget policy to an `ExperienceCapsule` without changing the capsule's authority, consent, provenance, or protected-evidence access rules.

## Mapping

| Storage-budget field | ExperienceCapsule surface | Rule |
|---|---|---|
| `policy_id` and `policy_version` | `retention_policy.policy_id` plus external policy reference | The capsule records the exact accepted policy revision. |
| `capture_plan.streams[].stream_ref` | `streams[].stream_id` | Every enabled durable or ephemeral planned stream must resolve to a capsule stream or an explicit missing-stream declaration. |
| `modality` | `streams[].modality` | Values must agree exactly. |
| `artifact_class` | `streams[].artifact_class` | `ephemeral` plan streams are represented through processing receipts and may not expose a durable payload reference. |
| `fidelity_class` | `streams[].fidelity_class` | Planned and observed fidelity may differ only with a fidelity-transition receipt. |
| `user_recall_available` | `streams[].user_recall_available` | Budget policy cannot broaden recall rights established by the capsule. The more restrictive value wins. |
| `material_properties[].coverage_refs` | stream IDs and missing-evidence declarations | Required coverage must resolve to enabled streams. Lost required coverage changes completeness and emits capability loss. |
| `sensor_substitutions` | fidelity transitions, source stream references, missing evidence | Substitution never rewrites original evidence history. |
| `adaptive_sampling_rules` | processing and fidelity-transition receipts | Sampling changes are events, not silent stream mutation. |
| `fidelity_elevation_rules` | consent transitions, authority references, fidelity transitions | Elevation requires current authority and consent for the affected interval. |
| `capacity_budget.retention` | capsule retention policy and retention events | The capsule remains the record of what was actually retained or deleted. |
| `budget_exhaustion_behavior` | completeness status and missing evidence | Exhaustion cannot leave `complete_for_declared_scope` when required properties are lost. |
| `receipt_policy` | provenance root and linked receipts | Receipt integrity contributes to provenance but does not establish semantic truth. |

## Access rule

The storage-budget policy may propose or summarize capture and retention. It does not:

- activate a device;
- grant sensor permission;
- modify consent;
- authorize access to protected raw evidence;
- convert generated reconstruction into original evidence;
- override reconstructive-memory authorization.

## Completeness transition

When a required property loses coverage, the adapter must:

1. emit a capability-loss declaration;
2. append missing-evidence details for the affected interval;
3. change the capsule completeness state to the most accurate bounded status;
4. preserve the original reconstruction goal and the reason it is no longer satisfied;
5. retain the budget and sampling receipts needed to reconstruct the decision.

## Deterministic precedence

When declarations conflict, apply the most restrictive valid constraint:

1. consent and legal prohibition;
2. authority and protected-evidence access policy;
3. required reconstruction properties;
4. continuity-receipt reserve;
5. explicit capacity ceiling;
6. preferred properties and presentation quality.

Capacity pressure never outranks consent, authority, or an explicit prohibition.

---

🔒 Layer: Framework | KV
