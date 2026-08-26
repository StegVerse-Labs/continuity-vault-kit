# Contact Ledger

One ledger record is maintained per attribution key. It contains normalized communication observations and evidence references without embedding call audio or message bodies.

Lifecycle:

1. append idempotent inbound observations;
2. evaluate a versioned threshold profile over a defined time window;
3. create a filing candidate when the threshold is met;
4. seal only after separate owner authorization, freezing included observation IDs, cutoff time, and composition hash;
5. append later communications to `post_filing_observation_ids`;
6. append evidence-bound notice events without changing the sealed filing hash.

Required integrity properties:

- source event ID and evidence hash deduplicate ingestion;
- ambiguous attribution cannot enter automatic filing composition;
- the sealed filing core is immutable;
- post-filing and notice histories are append-only;
- every mutation arrives through the KnowledgeVault Interlock and yields commit/readback receipts;
- ledger state is evidence organization, not a legal conclusion or permission to file.
