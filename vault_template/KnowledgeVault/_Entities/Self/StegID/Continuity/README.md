# StegID Continuity

This directory is the owner-facing personal-information surface for StegID identity-continuity state.

It is intentionally separate from the machine-governed backing records under:

`_System/Identity/Continuity/`

## Role

Files here are projections for the vault owner to inspect and carry forward. A projection may include:

- the continuity identifier;
- current/prior state hashes;
- the reference to the verified StegID continuity receipt;
- the path and hash of the corresponding `_System/Identity/Continuity` record;
- a bounded continuity status.

## Authority boundary

This directory does not mint identity, continuity, execution, wallet, governance, or device authority.

Canonical responsibility remains separated:

- StegID verifies identity receipts and identity-continuity evidence.
- Continuity defines and reconstructs continuity relationships.
- KnowledgeVault preserves the resulting personal and machine records.
- `_Entities/Self/StegID/Continuity` is a personal projection only.
- `_System/Identity/Continuity` is the machine persistence layer.

A personal projection is valid only when its `system_record_hash` matches the referenced system record and its own projection hash verifies.

## Privacy

Do not place private keys, authentication secrets, provider credentials, wallet secrets, biometric material, or raw cryptographic key material here.

The directory should contain only bounded continuity metadata and references required for owner inspection and reconstruction.
