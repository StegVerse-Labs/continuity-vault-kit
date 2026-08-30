# KV Typed Transport Capability Governance Mirror Handoff

Status: IMPLEMENTED_VALIDATED_MERGED / RUNTIME_EVIDENCE_ADMISSION_PENDING
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #124
Branch: docs/reconcile-typed-transport-handoff-20260830
Created: 2026-08-30

## Goal

Make typed transport capability a first-class KnowledgeVault / Device-Node governance object.

This lane formalizes the first governance layer for transport-capable StegVerse interactions:

```text
Device/StegOS Node continuity
  -> KnowledgeVault continuity binding
  -> typed transport capability
  -> Interlock admission
  -> adjacent InTr transport
  -> HANDOFF_RECEIPT / reconstruction evidence
```

The transport capability is not generic network reachability and is not equivalent to its carrier protocol.

## Governing invariants

- A governed transport lane may not become ACTIVE without an admissible Node continuity root and a KV continuity binding or equivalent reconstruction evidence.
- KnowledgeVault is the durable continuity/reconstruction host.
- Device/StegOS is the ephemeral activity edge.
- A transport capability is typed by governed semantics; carrier protocol is recorded separately.
- HTTPS does not imply one generic StegVerse transport capability.
- Capability evidence does not grant execution, identity, credential, governance, provider, or endpoint authority.
- Credential authority remains TV/TVC.
- Each independently governed Interlock/InTr boundary must still admit its own transition and issue its own receipt.
- Valid capability evidence may be reused by later lanes only while its continuity binding and lifecycle state remain valid.
- Revoked, expired, or superseded capability evidence must fail closed.
- Installation/source presence never implies runtime activation or OBSERVED transport.

## Initial capability types

```text
KV_DISTRIBUTION_DOWNLOAD
DEVICE_KV_INTR
PUBLIC_HTTPS_INGRESS
ADJACENT_EXTERNAL_API_EGRESS
NODE_TO_NODE_SYNC
KV_SKAP_INTR
TVC_RELAY
```

These names describe StegVerse transport semantics, not merely carrier technology.

## Reference observations

- Hugging Face / SV-DN-1 is the first successful observed Node-rooted external transport pattern and corresponds to an adjacent external API egress capability.
- HIL is the next governed instantiation and requires a public HTTPS ingress capability.
- KnowledgeVault distribution is itself a transport establishment event in the canonical onboarding path: Node establishment precedes governed distribution/download and later KV binding.

## Automation requirement

For a new evaluator, third party, or user, capability establishment should be protocol-driven where possible:

```text
transport requested
-> establish/recover Device Node
-> bind/reconstruct KV continuity
-> determine required transport type
-> reuse valid capability OR execute capability-establishment protocol
-> emit capability receipt
-> admit requested Interlock/InTr lane
-> execute
-> persist receipts/reconstruction evidence to KV
```

A registration page is one possible UI, not an architectural requirement. Human interaction is required only when a policy/authority/consent predicate actually requires it.

## Source deliverables

- `schemas/kv-transport-capability-registry.schema.json`
- `specs/kv-transport-capability-registry.v1.json`
- `scripts/validate_kv_transport_capability_registry.py`
- `tests/test_kv_transport_capability_registry.py`

## Runtime/non-claims

This lane does not itself activate any Node, transport, Interlock, InTr, provider, credential, endpoint, or external side effect.

The Hugging Face observation remains OBSERVED independently of this source abstraction.
The HIL runtime observation remains a separate live gate.

## Completion evidence

```text
typed transport registry/schema/validator/tests:
  PR #125
  merge: 8755c8db27c6d134a59df1850c065750552d86e6
  exact-head validation: PASS

KV activation-readiness typed transport gating:
  PR #128
  merge: 381b2eb3a37fbd308d2155befac1bab19b01f821
  exact-head validation: PASS

authentic transport observation evidence admission:
  PR #130
  merge: 035716d4ccc8f05466b60bb5bb2bb02bd3ad6b69
  exact-head validation: PASS

downstream StegOS typed transport blocker projection:
  StegVerse-Labs/StegOS PR #97
  merge: 2ab982a4cf0f96d5614a4f2b67265640f5178fee
  StegOS CI: PASS
```

The StegOS propagation deliberately preserves historical `stegverse.kv.activation-readiness-snapshot/v1` replay/digest compatibility. New typed snapshots are strict; historical snapshots are not mutated during validation.

## Current runtime standing

```text
typed transport governance source: IMPLEMENTED
typed transport source validation: VALIDATED
continuity-vault-kit integration: MERGED
StegOS read-only consumer propagation: MERGED
authentic HF transport result: OBSERVED independently in Site
HF observation admitted into KV typed fact: NOT YET — exact authentic bundle bytes not currently present in this repository lane
HIL PUBLIC_HTTPS_INGRESS source/observer: DEPLOYED in Site
HIL PUBLIC_HTTPS_INGRESS authentic observation: NOT YET OBSERVED
transport capability runtime activation by this source work: NONE
authority_effect: NONE
```

## Next executable action

1. Admit the exact authentic current-format SV-DN-1/Hugging Face observation bundle when its bytes are available, advancing only `ADJACENT_EXTERNAL_API_EGRESS`.
2. Execute the deployed HIL established-node observation when the machine-side path is fully ready; if it produces valid canonical evidence, admit only `PUBLIC_HTTPS_INGRESS`.
3. Apply the same typed capability + authentic observation admission pattern to other transport-blocked lanes rather than creating bespoke transport tests.


## Authentic observation evidence admission — issue #129

The typed transport model now has a bounded fail-closed evidence adapter:

- `scripts/admit_transport_capability_evidence.py`
- `schemas/kv-transport-capability-evidence-admission.schema.json`
- `tests/test_admit_transport_capability_evidence.py`

Initial mappings:

```text
stegverse.sv-dn1.browser-resident-observation-bundle/v3
  -> ADJACENT_EXTERNAL_API_EGRESS

stegverse.hil.canonical-observation-evidence/v1
  -> PUBLIC_HTTPS_INGRESS
```

Admission advances only the matching `transport_capabilities_observed.<TYPE>` fact.

It does not advance production Interlock activation, provider/session state, credential state, module/service activation, TVC lifecycle state, execution authority, or any unrelated transport capability.

The HIL ingress capability may be admitted independently of the later TVC lifecycle receipt because the fact being established is specifically public HTTPS ingress capability, not completion of the HIL lifecycle.

The current Hugging Face browser observer source on Site emits the v3 bundle above. Earlier session references to an older canonical-evidence filename/schema are superseded by the live Site source.

No KV fact is advanced merely because the adapter exists. Authentic evidence bytes must be supplied and pass validation.
