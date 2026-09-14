# KV Ephemeral Browser Projection Mirror Handoff

Updated: 2026-09-14

Goal Task ID: `KV-BOUND-EPHEMERAL-BROWSER-PROJECTION-001`
Canonical issue: `StegVerse-Labs/.github#1299`
Status: `ACTIVE / DEVICE-BOUND PURPOSE LABEL SUPERSEDED / PROVIDER-NEUTRAL ANY-DEVICE CONTINUITY REQUIRED`

## Mandatory device-replaceability rule

The canonical `.github` device-replaceability invariant governs this handoff. Any historical use of `CURRENT_IPHONE_TESTFLIGHT_SIGNING`, `current-iPhone`, or `same-device` in producer/consumer symbols is a non-normative implementation label only.

KV continuity is provider-neutral and device-independent. A KV instance hosted in Google Drive, iCloud, or another configured provider is the same continuity source regardless of whether it is accessed from iOS, Android, macOS, Windows, Linux, or another authorized client.

No browser, OS, phone, service worker, IndexedDB instance, or local browser session may become the continuity root or required continuation surface.

## Purpose

Produce a narrow, non-authorizing, purpose-bound projection context only after KV has an admitted entry transition and compatible client-capability evidence from the same KV lineage.

The canonical purpose class is now:

```text
AUTHORIZED_USER_DEVICE_TESTFLIGHT_SIGNING
```

Legacy alias accepted only for compatibility/historical evidence:

```text
CURRENT_IPHONE_TESTFLIGHT_SIGNING
```

The legacy alias MUST NOT be interpreted as requiring an iPhone.

## Producer contract

`script/materialize_ephemeral_browser_projection_context.py` does not decide admission and does not own provider access. It consumes already-established KV receipts bound to one KV lineage and emits only an ephemeral projection gate.

Required authority semantics:

- `KV` is the continuity boundary;
- provider access is normalized through the provider-neutral KV adapter contract;
- browser/device identity has no continuity or user-verification authority;
- projection persistence effect remains ephemeral only;
- changing devices must not invalidate previously authentic KV/claim/transition evidence.

## Authority boundary

The producer cannot mint Interlock/InTr admission, cannot infer authority from browser/device identity, cannot persist canonical continuity in browser-local state, cannot authenticate TV/TVC, cannot sign an IPA, and cannot claim TestFlight/runtime execution.

The user device is an interchangeable access/transport endpoint only.

## Existing source compatibility

Existing source/schema fields may retain `CURRENT_IPHONE_TESTFLIGHT_SIGNING` until consumer migration is complete. Those values are compatibility labels only and may not be used to enforce device identity.

Any future source mutation must move toward the canonical `AUTHORIZED_USER_DEVICE_TESTFLIGHT_SIGNING` semantic without changing already-authentic evidence bytes or inventing a second continuity/runtime authority.

## Remaining integration

1. Rebind the consumer to provider-neutral KV reconstruction rather than one browser/device session.
2. Preserve exact KV lineage and retained canonical receipts across device replacement.
3. Project ephemeral signing context to whichever authorized user device is currently used, or to another admitted execution surface, without binding continuity to that endpoint.
4. Continue TV/TVC signing/upload and authentic runtime observation separately.

No specific device, browser, signing, TestFlight installation, or resident execution is claimed by this source contract.
