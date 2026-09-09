# KV Ephemeral Browser Projection Mirror Handoff

Updated: 2026-09-09

Goal Task ID: `KV-BOUND-EPHEMERAL-BROWSER-PROJECTION-001`
Canonical issue: `StegVerse-Labs/.github#1299`
Consumer PR: `StegVerse-Labs/StegOS#314`

## Purpose

Produce the narrow, non-authorizing, purpose-bound projection context consumed by the current-iPhone TestFlight bootstrap only after KV has an admitted entry transition and a compatible browser-capability observation from the same KV lineage.

## Producer contract

`script/materialize_ephemeral_browser_projection_context.py` does not decide admission and does not observe a browser. It consumes two already-established KV receipts:

```text
stegverse.kv.entry-transition-admission/v1
stegverse.kv.browser-capability-observation/v1
```

Both receipts must:

- be bound to purpose `CURRENT_IPHONE_TESTFLIGHT_SIGNING`;
- name `KV` as the continuity boundary;
- have `authority_effect=NONE`;
- carry the same non-empty `kv_lineage_id`.

The entry receipt must be `ADMITTED` and carry an exact SHA-256 transition commitment. The capability receipt must be `OBSERVED_COMPATIBLE`, carry an exact SHA-256 capability commitment, and explicitly set `browser_identity_authority=false`.

The producer emits only:

```text
stegos.kv-bound-ephemeral-projection-context/v1
purpose=CURRENT_IPHONE_TESTFLIGHT_SIGNING
entry_state=ADMITTED
kv_transition_commitment=<opaque sha256>
admission_commitment=<derived opaque sha256>
browser_capability_state=OBSERVED_COMPATIBLE
browser_capability_commitment=<opaque sha256>
persistence_effect=NONE_EPHEMERAL_CONTEXT_ONLY
authority_effect=NONE_PROJECTION_GATE_ONLY
```

The raw KV lineage identifier is deliberately not exported into the browser projection.

## Authority boundary

The producer cannot mint an Interlock/InTr admission, cannot infer browser compatibility from user-agent identity, cannot persist browser state, cannot authenticate TV/TVC, cannot sign an IPA, and cannot claim TestFlight/runtime execution.

The emitted context is a one-purpose projection gate input only. Missing, mismatched, cross-lineage, non-KV, non-admitted, or browser-authorizing source evidence fails closed.

## Files

- `scripts/materialize_ephemeral_browser_projection_context.py`
- `schemas/kv-ephemeral-browser-projection-context.schema.json`
- `tests/test_materialize_ephemeral_browser_projection_context.py`

## Remaining integration

1. Establish the authentic runtime producers of the KV entry-transition admission receipt and browser-capability observation receipt.
2. Package or transfer the resulting projection context to the StegOS current-iPhone bootstrap without browser-local durable storage.
3. Validate consumer/producer exact-schema compatibility.
4. Merge both source slices only after CI is green.
5. Continue TVC signing/upload and authentic current-iPhone execution separately.

No runtime admission, browser observation, signing, TestFlight installation, or resident execution is claimed by this source contract.
