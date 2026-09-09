# KV Privacy and State-Transition Continuity

Updated: 2026-09-09

## Canonical principle

KnowledgeVault (KV) is the private continuity boundary for user-associated state. KV continuity is established through governed state-transition lineage, not through persistence of a particular physical device, browser, carrier, network, provider account, or storage location.

The governing principle is:

> Nodes persist through admitted state-transition lineage. Devices interoperate. Browsers present. Storage providers hold materialization. KV preserves private continuity.

## KV as the privacy boundary

Any information related to the user belongs inside the KV privacy boundary unless a specific admitted operation requires a minimal disclosure.

The same rule applies, to the maximum technically possible extent, to device-, browser-, carrier-, network-, provider-, and session-derived information so that StegVerse does not create avoidable cross-channel linkability.

Examples of information that should remain private to KV whenever possible include:

- user-associated records and preferences;
- device characteristics and local identifiers;
- browser/container observations;
- carrier/network observations;
- IP/SSID and comparable network metadata when observable;
- provider-account identity and provider relationships;
- capability observations;
- session history and presentation state;
- cross-channel correlation data.

Outside KV, prefer purpose-scoped opaque references, commitments, proofs, and the minimum routing information necessary for the admitted operation. A hash of a fingerprint remains a fingerprint and should not be propagated merely because it is hashed.

StegVerse cannot prevent a carrier, browser vendor, storage provider, or network intermediary from observing information inherently required by that intermediary. The StegVerse requirement is that StegVerse does not unnecessarily preserve, correlate, reproduce, or propagate those observations.

## State-transition continuity

KV is not merely persistent storage. It is a private governed state-transition continuity node.

For prior admitted state `S_n`, an observed or proposed change `O_n` is resolved against:

- applicable KV governance `G_n`;
- constraints `C_n`;
- admissibility resolution `A_n`;
- permitted-action matrix `M_n`;
- consequence-state rules.

Conceptually:

```text
S_(n+1) = R(S_n, O_n, G_n, C_n, A_n, M_n)
```

where `R` is the governed resolution function.

An observation alone does not advance state. Resolution may produce, for example:

```text
ADMIT_AND_TRANSITION
DENY_AND_RETAIN
NO_ACTION_AND_RETAIN
DEFER_PENDING_EVIDENCE
ROLLBACK_OR_RECONSTRUCT
```

Each resolved outcome can preserve continuity when the resolution and consequence state are bound into the append-only transition lineage.

A complete transition should be able to bind, as applicable:

```text
prior_state_commitment
observation_commitment
governance_resolution
constraint_resolution
admissibility_result
action_matrix_resolution
action_or_result_commitment
consequence_state_commitment
prior_transition_commitment
transition_commitment
```

Continuity therefore follows the KV transition lineage rather than temporal adjacency, file presence, browser persistence, or device persistence.

## KV entry-boundary invariant

No entity outside the KV entry boundary may enter solely on externally supplied identity or context.

Entry requires fresh, purpose-bound admission material whose provenance resolves to an already-admitted state inside KV.

Externally observable identifiers are not sufficient by themselves, including:

- username;
- device identifier;
- browser identity;
- browser-local IndexedDB state;
- node URL;
- provider account;
- storage locator;
- carrier/network identity.

The preferred entry material is derived proof rather than raw intrinsic private data. It may take the form of a purpose-scoped capability, challenge response, proof of possession, commitment, or equivalent artifact that can only be validly produced from admitted KV state.

A KV entry decision should resolve provenance, freshness, purpose, governance, constraints, admissibility, action matrix, and consequence state. Successful entry does not create open-ended authorization; the admitted operation remains another bounded state transition.

## Device interchangeability

The physical device is an interoperability node, not the root of user continuity.

A device may establish an interoperability relationship to an existing KV when the user demonstrates control sufficient to locate, read, validate, and reconstruct the KV from an admitted storage relationship.

The preferred proof is proof of control, not disclosure of provider-account ownership identity.

A replacement device can therefore continue the same KV lineage:

```text
new device
-> prove control of admitted storage relationship
-> discover existing KV
-> reconstruct and validate KV state-transition lineage
-> establish new device interoperability relationship
-> continue the same KV continuity
```

The prior device need not remain available. Device replacement does not mint a new user identity or a new KV identity.

## Storage-provider role

A storage provider is custody/materialization for a KV instance, not the identity or authority root of KV.

Provider identity, account identity, and raw credentials should remain private. StegVerse should receive only the minimum provider relationship and control/admission evidence required for the current transition.

This rule applies across KV #1/#2/#n and across iCloud Drive, Google Drive, OneDrive, Dropbox, local storage, or future admitted storage media.

## StegOS and StegBrowser relationship

The preferred continuity hierarchy is:

```text
PRIVATE KV CONTINUITY
        ↓
DEVICE INTEROPERABILITY NODE
        ↓
STEGOS RUNTIME NODE
        ↓
STEGBROWSER CAPABILITY NODE
        ↓
EPHEMERAL PRESENTATION / ACTION
```

StegOS carries runtime continuity for the admitted device relationship. StegBrowser carries browser-capability continuity. Neither a browser application nor a browser-local store is user continuity.

Safari, Chrome, Opera, Google-app browser surfaces, ChatGPT internal browser/webviews, and comparable browser containers are transition/presentation surfaces. They may be recorded as diagnostic observations when useful, but browser/container identity is not a sovereign identity root.

Historical bootstrap observations from different browsers on the same device are therefore not presumed to represent different device or KV identities. If browser identity was not recorded historically, it must not be invented retrospectively.

## Ephemeral browser presentation

The substantive browser presentation should be materialized only after the required node/KV entry state-transition dependency is satisfied and the actual browser/container capability is observed.

A minimal public rendezvous may exist to initiate discovery or confirmation, but it must not contain or become the private StegVerse environment.

After KV entry/admission, the system may derive an ephemeral presentation packet containing only the code and bindings needed for the current admitted operation, such as:

```text
projection_ref
node/KV commitment
capability observation or commitment
required UI modules
required WASM/code modules
allowed InTr routes
task/action bindings
expected return schema
expiry/session constraint
integrity commitments
```

The presentation packet grants no authority. Authority remains with the appropriate governance/transition/credential systems.

When the session/transition ends, browser-local presentation/session state is disposable. Durable continuity remains in KV and the admitted node transition histories.

## KV-protected browser projection

Browser/container observations and presentation-selection data should live behind the KV boundary whenever technically possible.

Outside KV, downstream StegOS/StegBrowser evidence should prefer opaque projection/capability/KV references or commitments rather than raw browser identity, user-agent details, device fingerprints, or other correlatable metadata.

This means the browser does not hold the user's private environment. KV projects the private environment into the browser only when an admitted state transition requires it.

## Current bootstrap implications

Current iOS bootstrap/TestFlight/signing work must not make Safari, a particular browser-local IndexedDB, or a permanently materialized public browser bootstrap the continuity or privacy root.

The current signer/bootstrap distribution must evolve toward:

```text
minimal rendezvous
-> KV/device continuity confirmation
-> KV entry transition/admission
-> browser/container capability observation
-> ephemeral private projection materialization
-> governed action
-> consequence-state commitment
-> projection/session disposal
```

Exact static code/WASM materialization may still be required before the first native TestFlight installation, but static source availability does not make that source a persistent private presentation or an identity/authority root.

## Non-authority rules

None of the following grants governance, execution, credential, publication, or custody authority by itself:

- KV persistence;
- device presence;
- browser presence;
- storage-provider access;
- HB observation;
- projection materialization;
- source/build validation;
- static WASM availability;
- a successful prior session.

Interlock/InTr remains responsible for governed transition admission, TV/TVC remains credential authority, WorkerCoordinator remains fresh claim/fence authority where applicable, and Master Records remains the reality/custody/reconstruction authority for evidence assigned to it.

## Implementation consequence

Existing implementations that treat browser-local persistence or a specific device as the continuity root are compatibility surfaces, not the target architecture. Migration must preserve historical provenance while moving canonical continuity and private browser/device/carrier metadata behind KV state-transition governance.
