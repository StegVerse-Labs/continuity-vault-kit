# Personal Communications

Canonical owner-controlled custody surface for normalized inbound communication records.

- `PersonalInformationDirectory/` resolves communication endpoints to people or organizations.
- `ContactLedger/` groups evidence references by attribution and maintains filing lifecycle state.
- Raw audio, message bodies, credentials, and secrets are never embedded in index records; records reference separately governed evidence by path and hash.
- Producers submit hash-bound `COMMIT_CANDIDATE` packages through the KnowledgeVault Interlock. This directory grants no provider, filing, governance, or execution authority.

Ambiguous endpoint matches remain ambiguous and must not be composed into a filing automatically. Unknown endpoints use a pseudonymous endpoint key until owner-authorized attribution.
