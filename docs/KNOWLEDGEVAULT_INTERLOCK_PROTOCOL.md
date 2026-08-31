# KnowledgeVault Interlock Protocol

Status: `ACTIVE_IMPLEMENTATION`
Protocol id: `KV-INTERLOCK-v1`
Repository: `StegVerse-Labs/continuity-vault-kit`
Canonical request schema: `schemas/kv-interlock-request.schema.json`
Canonical response schema: `schemas/kv-interlock-response.schema.json`

## Purpose

Define a governed connector boundary through which StegVerse modules and external LLMs may request bounded access to personal KnowledgeVault records without receiving direct vault filesystem authority.

## Core rule

```text
consumer != vault custodian
context != authority
retrieval != consent to publish
receipt != execution authority
model output != vault write authority
```

A consuming module MUST NOT read `03_Records/**` or other restricted personal-record paths directly. Restricted records are accessed only through an interlock request evaluated against vault policy and explicit owner/delegated authority.

## Personal-record custody

Canonical personal records remain in the owner's KnowledgeVault. Repositories such as StegHealth may keep only:

- schemas and connector code;
- opaque vault object identifiers;
- hashes/receipts where permitted;
- derived non-PII state needed for application behavior;
- public or explicitly disclosed derivatives.

They MUST NOT become the canonical store for health records, legal records, financial records, identity records, or other restricted personal records.

## Canonical machine-readable contract

The model-neutral protocol contract is now represented by:

- `schemas/kv-interlock-request.schema.json` — `kv.interlock.request.v1`;
- `schemas/kv-interlock-response.schema.json` — `kv.interlock.response.v1`;
- `tools/validate_kv_interlock_contract.py`;
- `tests/test_kv_interlock_contract.py`;
- `.github/workflows/validate-kv-interlock-contract.yml`.

A module may add stricter local constraints, such as requiring `requester.module=StegHealth`, but it must not widen the canonical operation/decision vocabulary, bypass required authority/purpose/scope fields, or weaken receipt/minimum-disclosure semantics.

## Operations

### DISCOVER

Returns only permitted metadata about available record classes, schemas, capabilities, and policy boundaries. It does not expose record contents.

### REQUEST

A requester supplies:

- requester/module identity;
- declared purpose;
- requested record class;
- minimum required fields or query scope;
- time/scope constraints;
- optional bounded selector (`directory_id`, `canonical_path`) for exact directory reads;
- requested disclosure mode;
- authority/delegation reference;
- correlation/request id.

A selector does not establish authority. It is valid only for `REQUEST`, must contain exactly `directory_id` and `canonical_path`, and is evaluated only after the same verified InTr admission and injected authority validation as every other restricted-record request.

### RETURN

The interlock returns one of:

- `ALLOW_BOUNDED_CONTEXT` with a scoped context packet;
- `REVIEW_REQUIRED`;
- `DENY`;
- `FAIL_CLOSED`.

Returned packets SHOULD minimize disclosure and SHOULD reference source object ids/hashes rather than duplicate full records when the use case permits.

### COMMIT_CANDIDATE

A model or module may propose a candidate record, annotation, summary, index update, or derived state. The candidate has no write authority by itself.

### COMMIT

A governed authority may accept a candidate into an allowed KnowledgeVault destination. Restricted-record writes require explicit applicable authority and a receipt. Existing originals may not be silently overwritten.

## Health-record specialization

For StegHealth:

```text
StegHealth request
  -> KV Interlock
  -> policy + authority evaluation
  -> minimum necessary health context
  -> StegHealth processing
  -> derived result / action proposal
  -> optional governed writeback candidate
```

StegHealth does not receive direct filesystem credentials to the personal vault and does not persist raw PII/PHI in its repository or public runtime state.

## Required receipt fields

Each restricted-record access should produce a durable receipt containing, at minimum:

- request id;
- requester/module;
- purpose;
- policy profile/version;
- authority/delegation reference;
- requested scope;
- granted scope;
- source object references/hashes where permitted;
- disclosure transformation/redaction profile;
- decision state;
- timestamp;
- response hash;
- writeback candidate reference, if any.

Receipts should avoid restating sensitive values when an opaque reference or hash is sufficient.

## Failure semantics

Missing policy, missing authority, stale authority, scope expansion, unsupported record class, integrity mismatch, or connector ambiguity MUST fail closed for restricted personal records.

## LLM portability

The protocol is model-neutral. ChatGPT, another hosted LLM, or a local StegVerse model may use the same interlock contract. The model is replaceable; the KnowledgeVault remains the continuity/custody substrate.

## Compatibility with existing KnowledgeVault rules

Existing direct-AI rules remain valid: AI tools do not directly access `03_Records/**`. `KV-INTERLOCK-v1` is an explicit governed exception path mediated by policy and authority; it does not weaken the prohibition on direct unrestricted AI access.

## Activation predicates

`KV-INTERLOCK-v1` is not considered runtime-active until:

1. canonical request and response schemas are validated;
2. a policy evaluator enforces restricted-path denial by default;
3. a StegHealth request obtains only bounded test context through the connector;
4. a negative test proves direct StegHealth access to restricted records is unavailable;
5. a receipt is persisted and hash-verified;
6. writeback is demonstrated as candidate-only until separately authorized;
7. no PII/PHI is persisted in StegHealth repository artifacts or public runtime logs.


## Runtime endpoint core — issue #79

The repository now contains a dependency-light runtime endpoint core at `runtime/kv_interlock_endpoint.py`.

It does not establish boundary identity or authority by itself. The caller must provide an already-verified DEVICE->KV InTr envelope plus an opaque durable InTr receipt reference. Authority validation, policy evaluation, candidate persistence, and receipt persistence remain injected governed boundaries.

The core enforces:
- canonical `kv.interlock.request.v1` request shape and operation vocabulary;
- exact DEVICE->KV InTr request/envelope binding and payload hash;
- verified boundary proof plus fail-closed receipt policy;
- no transport/model credential or execution authority transfer;
- authority validation before policy execution;
- granted scope never wider than requested scope;
- bounded context fields limited to granted scope and secret-like field names rejected;
- candidate-only `COMMIT_CANDIDATE` with `canonical_state_changed=false`;
- deterministic response hashing and injected secret-free receipt persistence;
- no direct filesystem, credential, SKAP, provider, or execution authority.

This source implementation is not production activation. A live boundary identity/sealing service, actual runtime deployment, canonical owner/device readback, and real InTr receipts remain separate evidence gates.

## Canonical response-hash projection

For `kv.interlock.response.v1`, `receipt.response_hash` is the lowercase SHA-256 hex digest of canonical JSON over exactly this response projection:

```text
schema_version
request_id
decision
granted_scope
context
source_refs
```

Receipt metadata is not part of the hashed response projection. This keeps the response hash deterministic, non-circular, and compatible with existing consumers such as the StegHealth specialization. Receipt identity, policy, authority, timestamp, and writeback-candidate references remain separately validated receipt fields.

---

🔒 Layer: Framework | KV
