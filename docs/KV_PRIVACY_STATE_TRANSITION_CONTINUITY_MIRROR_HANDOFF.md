# KV Privacy / State-Transition Continuity Mirror Handoff

Updated: 2026-09-09

Canonical architecture: `docs/KV_PRIVACY_STATE_TRANSITION_CONTINUITY.md`
Related goal: `KV-BOUND-EPHEMERAL-BROWSER-PROJECTION-001`
Related COSV: `50000010100000`
Related canonical issue: `StegVerse-Labs/.github#1299`

## Doctrine established

KV is the private governed state-transition continuity boundary for user-associated state. Continuity is implied only through resolution of each observed/proposed state change against KV governance, applicable constraints, admissibility, permitted-action matrices, and the resulting consequence state, with prior/resulting state bound into the transition lineage.

A physical device is an interchangeable interoperability node, not the root of user continuity. A new device may continue an existing KV after proof of control sufficient to discover, reconstruct, and validate the KV lineage from an admitted storage relationship. Provider account identity and raw credentials are not continuity roots.

Outside entities may not enter KV solely through external identity/context. Entry requires fresh purpose-bound admission material whose provenance resolves to admitted state inside KV. Prefer derived proof/capability over raw intrinsic KV data.

User, device, browser/container, carrier/network, provider, session, and other linkable metadata remain inside KV whenever technically possible. Outside KV, expose only the minimum purpose-scoped opaque references/commitments/proofs needed for the admitted transition.

Browser applications and embedded browser containers are ephemeral presentation/transition surfaces. Browser-local IndexedDB, service workers, cookies, profiles, or historical bootstrap state do not define user/KV/device continuity. Browser identity should be retained only as private/diagnostic transition information when materially useful; historical browser identity must not be invented when it was not recorded.

StegOS is the runtime node relationship; StegBrowser is the browser-capability node relationship; substantive browser presentation materializes only after the KV entry transition dependency is satisfied and the current browser/container capability is observed.

## Multi-instance effect

KV #1/#2/#n remain independently rooted members of a continuity set. Storage providers remain provider-neutral custody/materialization relationships. The new continuity doctrine does not collapse instance provenance or relationship tiers; it changes what acts as the durable continuity/privacy root and how devices/browsers enter that boundary.

## Migration implication

Current `device-local-browser-indexeddb` owner-observed KV state remains historical runtime evidence, but `BEST_EFFORT_BROWSER_ORIGIN` must be treated as a compatibility materialization surface rather than the target continuity root. Migration must preserve its provenance while moving durable continuity, private browser/device/carrier metadata, and entry admission behind KV state-transition governance.

## Next implementation work

1. Reconcile KV schemas/runtime stores with explicit prior-state, governance, constraint, admissibility, action-matrix, consequence-state, and transition commitments where not already represented.
2. Define purpose-bound KV-originating admission artifacts for external entry.
3. Define device interoperability admission/replacement semantics based on KV reconstruction/proof of control.
4. Minimize externally projected user/device/browser/carrier/provider/session metadata.
5. Bind MyKV/browser presentation to post-entry ephemeral projection rather than browser-local continuity.
6. Preserve multi-instance/provider-neutral behavior and existing historical provenance.

## Authority

This documentation does not itself grant Interlock/InTr admission, provider authority, credential authority, execution, publication, or custody. Interlock/InTr remains transition authority; TV/TVC remains credential authority; SKAP remains secret custody; Master Records remains reality/custody/reconstruction authority where assigned.
