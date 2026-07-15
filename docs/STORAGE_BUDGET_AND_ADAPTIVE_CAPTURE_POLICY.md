# Storage Budget and Adaptive Capture Policy

## Status

Version: `0.1-draft`  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#28 Define storage budgets and adaptive multimodal capture policy`

## 1. Purpose

This policy defines how a governed multimodal system selects capture, retention, fidelity, and sensor substitution within an explicit storage budget while preserving the material properties required by a declared reconstruction goal.

The system must not silently convert a high-assurance reconstruction goal into a lower-fidelity record merely because capacity is constrained. When the declared goal can no longer be met, the system must fail closed for that goal, preserve a decision receipt, and declare the resulting capability loss.

## 2. Core decision model

Every adaptive capture decision binds four declarations:

1. **Reconstruction goal** — what later use must remain possible.
2. **Material properties** — which properties of the experience must survive.
3. **Capacity budget** — how much durable storage and replication are authorized.
4. **Capture policy** — which sensors, sampling rates, fidelity classes, and escalation triggers may be used.

A valid policy decision is:

```text
reconstruction goal
+ required material properties
+ authorized sensor set
+ explicit capacity budget
+ retention and replication limits
+ declared omissions
+ failure behavior
= governed capture plan
```

## 3. Reconstruction goals

Supported initial goals:

### 3.1 Semantic recall

Preserve what was said, decided, referenced, or changed.

Typical minimum representation:

- canonical text or transcript;
- speaker or participant references;
- event order and timestamps;
- provenance and consent transitions;
- material missing-evidence declarations.

Original audio or video is not required unless separately declared.

### 3.2 Spatial and object-state recall

Preserve where relevant participants and objects were located and how those states changed.

Typical minimum representation:

- selected images or keyframes;
- object identities and trajectories;
- camera or sensor pose;
- approximate scene geometry or depth;
- synchronized event timing.

### 3.3 Approximate experiential playback

Preserve enough visual, temporal, and acoustic structure to generate an explicitly labeled approximation of the experience.

Typical minimum representation:

- sparse video reconstruction package;
- keyframes, motion, pose, scene state, transcript, and sound events;
- source links and completeness declarations.

This goal never authorizes presentation as original evidence.

### 3.4 Protected evidentiary preservation

Preserve original or high-fidelity media for an authorized scope.

Typical minimum representation:

- protected original or high-fidelity evidence;
- integrity commitments;
- synchronized timestamps and device declarations;
- custody, access, retention, and deletion policy.

Budget exhaustion must not silently replace this goal with generated or sparse reconstruction.

## 4. Material properties

A policy declares each property as `required`, `preferred`, or `omitted`.

Initial material-property vocabulary:

- spoken semantic content;
- exact original audio waveform;
- speaker timing and overlap;
- visual identity evidence;
- body pose and gesture;
- object identity;
- object position and trajectory;
- scene geometry;
- text visible in the environment;
- ambient sound events;
- precise event ordering;
- bounded clock synchronization;
- environmental measurements;
- original pixel-level video evidence.

An omission must be explicit. A lower-cost representation is acceptable only when all required properties remain supported for the declared goal.

## 5. Capacity budget

The budget must define:

- maximum bytes per episode;
- optional maximum bytes per hour and per day;
- local allocation;
- protected-evidence allocation;
- archival allocation;
- replication allowance;
- retention duration by artifact class;
- reserved continuity and receipt allocation;
- whether temporary capture may exceed the durable budget before governed reduction;
- excluded ephemeral processing state.

Continuity records and required decision receipts must have a reserved allocation. A policy may not consume all capacity with raw media and then omit the evidence needed to explain retention or deletion decisions.

## 6. Sensor substitution

A sensor substitution is valid only when it preserves every required material property for the declared reconstruction goal.

Examples:

- transcript plus speaker timing may substitute for original audio for semantic recall;
- low-frame-rate video plus depth and object tracking may substitute for continuous HD video for spatial recall;
- event-triggered keyframes plus motion and device location may substitute for continuous video where exact visual evidence is not required.

Each substitution declares:

- replaced sensor or stream;
- substitute sensor set;
- properties preserved;
- properties lost;
- expected uncertainty;
- validation basis;
- conditions requiring temporary restoration of higher fidelity.

## 7. Adaptive sampling

The system may reduce sampling during stable, redundant, or low-information intervals only when the active reconstruction goal remains satisfiable.

Possible adaptive inputs:

- scene-change rate;
- object motion;
- participant arrival or departure;
- speech activity;
- new topic or decision boundary;
- sensor disagreement;
- clock uncertainty;
- consent transition;
- user marker;
- safety or dispute trigger;
- available capacity.

Adaptive sampling decisions must be deterministic or reproducible from a declared policy version and input summary.

## 8. Temporary fidelity elevation

A policy may temporarily increase capture fidelity when a governed trigger occurs.

Initial trigger classes:

- explicit user request;
- safety event;
- dispute or contradiction;
- new participant;
- material object movement;
- consent change;
- evidence-preservation request;
- sensor disagreement;
- reconstruction confidence below threshold;
- boundary or authority transition.

Each elevation records:

- trigger;
- start and end time;
- prior and elevated capture plan;
- expected storage impact;
- authority and policy reference;
- resulting retained artifact class;
- reduction or deletion outcome after the elevated interval.

## 9. Budget exhaustion

Budget exhaustion behavior must be selected in advance.

Permitted initial behaviors:

- `stop_nonessential_capture`;
- `reduce_preferred_properties_only`;
- `request_additional_capacity`;
- `end_episode_capture`;
- `preserve_continuity_only`;
- `fail_closed_for_declared_goal`.

Prohibited behavior:

- silently dropping a required property;
- silently replacing protected evidence with generated reconstruction;
- deleting source data while claiming reversibility;
- continuing to claim the original reconstruction goal remains satisfied.

When exhaustion prevents the goal from being met, the policy emits a capability-loss declaration containing the affected goal, missing properties, effective time, cause, and remaining reconstruction class.

## 10. Decision receipts

Durable receipts are required for:

- initial capture-plan selection;
- sensor substitution;
- adaptive sampling change;
- temporary fidelity elevation;
- budget threshold crossing;
- budget exhaustion;
- fidelity reduction;
- deletion;
- capability loss;
- later policy revision.

A receipt identifies the policy version, episode, actor or controller, authority reference, inputs, decision, expected capacity effect, integrity commitments, and effective interval.

## 11. Storage accounting

Accounting distinguishes:

1. original payload bytes;
2. derived searchable bytes;
3. reconstruction-package bytes;
4. continuity and receipt bytes;
5. replica bytes;
6. temporary buffer bytes;
7. excluded ephemeral compute state.

The policy must not count deleted or unavailable payloads as recoverable capacity. Deduplication savings may be recorded only when the shared content remains durably available under compatible custody and retention rights.

## 12. Required invariants

1. Every policy has one declared reconstruction goal.
2. Every required material property is mapped to at least one authorized stream or derived representation.
3. Capacity limits use explicit byte values and retention durations.
4. Replication is separately budgeted.
5. Ephemeral compute state is excluded from durable storage totals.
6. Sensor substitutions declare preserved and lost properties.
7. Adaptive reduction cannot remove a required property.
8. Fidelity elevation requires a governed trigger and receipt.
9. Budget exhaustion has a predeclared behavior.
10. Capability loss is explicit and cannot coexist with a claim that the original goal remains satisfied.
11. Protected evidentiary preservation cannot degrade into generated-only recall without a new authorized goal.
12. Ordinary recall rights do not grant protected raw-evidence access.

## 13. Initial implementation targets

1. `schemas/storage-budget-policy.schema.json`.
2. Reference fixtures for semantic recall, spatial recall, adaptive video, and evidentiary preservation.
3. Dependency-light validator.
4. Tests for required-property coverage, budget arithmetic, substitution, exhaustion, and capability-loss consistency.
5. Dedicated CI workflow.
6. Optional planner that produces a governed capture plan without directly controlling sensors.
7. Integration with `ExperienceCapsule` and the multimodal access adapter.

## 14. Non-goals

This policy does not:

- grant surveillance authority;
- select sensors without consent or authorization;
- guarantee that a generated reconstruction is accurate;
- make inferred emotion a fact;
- remove the physical cost of raw-media storage;
- authorize access to protected evidence;
- establish legal admissibility;
- autonomously purchase storage or compute capacity.

---

🔒 Layer: Framework | KV