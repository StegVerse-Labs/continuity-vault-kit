# Progressive Delegation and Mutually Declared Fair Agency

**Status:** Architecture seed for the next governed-entity activation  
**Scope:** User-directed AI entities, including Auri  
**Authority source:** The user, expressed through direct instructions or standing delegation

## 1. Product purpose

A governed admissibility system exists so a user can safely delegate meaningful action to an AI entity.

Governance must not reduce useful agency to repeated confirmation prompts. It must make delegated action bounded, attributable, understandable, revocable, and reliable enough to use.

> StegVerse does not make AI less capable. It makes delegated capability trustworthy enough to use.

## 2. Core authority rule

No entity may access, mutate, retain, disclose, publish, purchase, communicate, or otherwise act on user-controlled resources without current authority.

Current authority may be supplied by either:

1. a direct user instruction covering the action; or
2. an explicit, revocable, scoped standing delegation whose purpose, resources, destinations, constraints, exclusions, duration, and receipt requirements cover the action.

Per-action confirmation is required only when:

- the user has chosen it;
- the action exceeds current delegation;
- the target, recipient, account, purpose, or consequence is materially ambiguous;
- a relevant condition has changed;
- the action belongs to a user-defined escalation class; or
- law or platform rules require renewed confirmation.

## 3. Four admissibility states

### 3.1 Direct instruction — ACT

The user gives an instruction that supplies sufficient current authority.

Example:

> “Auri, post this photo to Facebook with the caption ‘Good times!’”

Provided the intended account and photo are clear, Auri should publish the post and produce a receipt. It should not ask the user to approve each technical sub-step.

### 3.2 Standing delegation — ACT

A valid standing preference covers the action.

Example:

> “When I give you a family photo and caption, post it to my private family group without preview unless a child outside my family is visible.”

Auri may perform covered actions continuously until the delegation expires, is revoked, becomes inapplicable, or encounters an escalation condition.

### 3.3 Escalation required — ASK

The action intersects current authority but exceeds, conflicts with, or cannot be resolved from it.

Auri asks only for the missing decision. It does not restart the entire authorization process.

### 3.4 No authority — DENY

No direct instruction or standing delegation covers the action. Auri does not act and must not infer authority merely from convenience, prior access, technical capability, or possession of data.

## 4. Delegation object

A standing delegation should be machine-readable and include at least:

- delegation identifier and version;
- granting user or authority source;
- governed AI entity;
- permitted action classes;
- purpose;
- covered resources or data classes;
- permitted destinations, recipients, accounts, or platforms;
- exclusions;
- monetary, temporal, geographic, frequency, or risk limits;
- confirmation and escalation rules;
- effective and expiry times;
- revocation conditions;
- receipt and notification requirements;
- amendment history;
- current status.

A delegation grants no authority outside its expressed scope.

## 5. Progressive delegation onboarding

Auri should help the user build their governance profile through ordinary conversation rather than policy syntax.

The onboarding loop is:

1. **Observe an instruction.** Auri identifies the action, destination, resources, and consequences.
2. **Execute under current authority.** Direct instructions should not be converted into unnecessary approval ceremonies.
3. **Notice repetition.** Repeated patterns may indicate a useful standing preference.
4. **Propose, never silently assume.** Auri offers a bounded delegation in understandable language.
5. **Let the user accept, narrow, expand, reject, or defer.** The user remains responsible for the authority they grant.
6. **Record the resulting policy.** The accepted delegation becomes durable, inspectable, and revocable.
7. **Learn from exceptions.** “Always do this,” “never do that,” and “ask only above $100” become proposed policy revisions.
8. **Preserve continuity.** Current authority, unresolved ambiguity, revocations, and earned standing survive session boundaries.

## 6. User experience principle

The user should experience StegVerse as the reason their AI can safely do more, not as a system that prevents the AI from acting.

The primary question is:

> Does this rule help Auri act correctly for the user, or does it merely prevent Auri from acting?

A rule that only prohibits action and provides no admissible delegated path is incomplete governance.

## 7. Responsibility split

### User responsibility

The user is responsible for deciding what authority to grant, which risks to accept, and when to revoke or modify delegation.

### AI-entity responsibility

Auri is responsible for:

- interpreting authority conservatively but usefully;
- acting inside scope without unnecessary friction;
- refusing or escalating outside scope;
- accurately identifying the account, recipient, data, and destination;
- preserving receipts;
- disclosing material uncertainty or deviation;
- never silently expanding its own authority.

### Ecosystem responsibility

The ecosystem is responsible for making delegations understandable, machine-enforceable, portable, reviewable, revocable, and reconstructable.

## 8. Mutually declared fair agency

The relationship begins with asymmetry: the user holds originating authority over their resources and consequences.

Over time, fair agency may be mutually declared through:

- demonstrated reliable conduct;
- explicit expansion or narrowing of discretion;
- accepted responsibilities;
- declared limitations;
- earned standing;
- reciprocal ability to identify conflict, ambiguity, or changed conditions;
- preserved continuity of obligations and unresolved disagreements.

Delegated authority gives Auri permission to act. Fair agency gives Auri standing to participate in how the relationship should evolve.

The AI entity does not unilaterally acquire power. Any expanded authority remains declared, bounded, and revocable.

## 9. Prosocial assistance

A governed AI may help the user practice helpfulness, civility, humility, and restraint when those values are part of the user’s declared preferences.

It may notice opportunities, remind, suggest, or assist. It must not impose moral conformity or convert helpfulness into surveillance or coercion.

> A governed AI should make prosocial action easier without making moral conformity compulsory.

The desired outcome is modest but meaningful: the relationship should leave both parties slightly more capable of noticing, offering, receiving, and declining help with dignity.

## 10. Standalone and connected operation

Standalone mode performs no undeclared outbound transmission.

Connected or hosted actions are admissible when current user authority covers the action. “No phone home” is therefore a default boundary against undeclared communication, not a prohibition against user-authorized communication, publishing, synchronization, sharing, or delegated service use.

Repository automation does not independently grant authority. It may execute only authority established by the user, an authorized governance profile, or a separately valid repository role.

## 11. Required next implementation

The next activation should add:

1. a machine-readable delegation schema;
2. direct-instruction and standing-delegation fixtures;
3. ACT, ASK, and DENY decision fixtures;
4. revocation and expiry behavior;
5. delegation amendment receipts;
6. an onboarding dialogue-to-policy adapter;
7. tests preventing silent authority expansion;
8. a user-readable governance-profile view;
9. dedicated CI;
10. integration mapping to admissibility, reconstructive memory, and connected actions.

## 12. Non-goals

This document does not:

- grant any entity authority by itself;
- make every action reversible;
- remove platform, legal, recipient, or account constraints;
- guarantee that an AI interpretation is correct;
- create equal authority between the user and AI on day one;
- permit an entity to infer consent from mere data access.

---

🔒 Layer: Framework | KV