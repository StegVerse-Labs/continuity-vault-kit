# KV ↔ SKAP InTr Account Metadata Transfer Protocol

Status: `IMPLEMENTATION_CANDIDATE`
Protocol packet: `stegverse.kv-skap.account-metadata-transfer/v1`
Boundary envelope: `stegverse.intr.boundary-transfer/v1`
Goal Task ID: `SS-SKAP-AUTHENTIC-ACCOUNT-METADATA-POPULATION-001`

## Purpose

Define the internal governed data-transfer seam between KnowledgeVault and the internal SKAP Vault for owner-selected account metadata. This protocol does not transfer provider credentials or raw provider account identifiers. It transfers only the minimum non-secret account metadata needed to establish a SKAP account binding and preserve evidence lineage.

## Required flow

```text
My KV owner selection
  -> bounded provider-account observation
  -> KnowledgeVault non-secret transfer packet
  -> KV-INTERLOCK-v1 COMMIT_CANDIDATE
  -> exact InTr boundary-transfer envelope
  -> InTr decision / durable receipt
  -> SKAP Vault account-metadata admission
  -> SKAP receipt
  -> TVC account-inventory projection
```

## Why this is separate from ordinary KV COMMIT

`KV-INTERLOCK-v1` intentionally grants no direct SKAP or provider authority. Therefore the KV request remains a candidate-only request. The new boundary-transfer envelope binds the exact KV request hash to the exact transfer packet hash and names `SKAP_Vault` as the destination boundary. Canonical state may not change until the receiving InTr/SKAP side produces the separately validated transition/admission receipt.

## Transfer packet

The packet contains only:

- owner selection reference;
- provider organization reference such as `org:linkedin`;
- account class;
- account status;
- source-evidence reference;
- source-evidence SHA-256;
- deterministic payload hash and transfer id;
- explicit `contains_secret_material=false` and `raw_provider_account_identifier_present=false`.

The packet MUST NOT contain provider account ids, usernames used as authentication material, passwords, access/refresh tokens, client secrets, private keys, session cookies, or credential payloads.

## Interlock binding

The KnowledgeVault request uses canonical `kv.interlock.request.v1` with:

- `operation=COMMIT_CANDIDATE`;
- `record_class=SKAP_ACCOUNT_METADATA_TRANSFER`;
- minimum necessary requested scope;
- `disclosure_mode=SOURCE_REFERENCE_ONLY`;
- `candidate_writeback.payload_ref` equal to the exact transfer payload hash;
- `candidate_writeback.requested_destination=skap://internal/account-metadata`.

This request is not itself a SKAP write.

## Boundary-transfer envelope

The InTr envelope binds:

- source boundary `KnowledgeVault`;
- destination boundary `SKAP_Vault`;
- request id;
- exact KV request hash;
- transfer id;
- exact transfer-packet hash;
- exact payload hash;
- InTr receipt reference once available;
- `canonical_state_changed=false` before receiving-side admission;
- `credential_material_transferred=false`.

Any request/packet hash mismatch, destination mismatch, secret-bearing field, raw provider account identifier, or replay with altered payload MUST fail closed.

## Receiving-side requirement

The SKAP-side consumer must independently validate the same packet and envelope hashes, require an applicable InTr decision/receipt for `SKAP_ACCOUNT_METADATA_ADMIT`, and write a receipt whose non-secret fields are sufficient for `TVC/tools/skap_account_inventory_projection.py` to enumerate the account. The receiving side must not invent provider identity or upgrade synthetic/test evidence to authentic population.

## Runtime truth

This source contract does not prove an authentic KV → SKAP runtime transfer has occurred. Runtime completion requires one owner-selected real account to traverse this protocol, produce a retained InTr receipt and retained SKAP account metadata receipt, and then appear in the TVC account inventory projection.
