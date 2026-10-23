# KV gateway storage adapter

Design for the seam between KV and the storage the KV user already owns. Interface: `runtime/kv_gateway_storage.py`. Stdlib only, no new dependency, no real provider client.

## Rulings this applies
- StegVerse-org/.github#160 comment 6371986288: KV is independent of the ecosystem Orgs and keeps its own ledger behind its own InTr endpoint.
- #160 comment 6372045430: KV is only a governed layer over storage the user already owns, reached through a GATEWAY node. KV has no hosted storage. SVKV (ECOSYSTEM-OWN-KV-001) is backed by the StegVerse@gmail.com Drive.
- #160 comment 6372216673 (**final**): KV's ledger and contents live as encrypted, content-addressed objects in the user's storage, verified on KV's side. Cloud storage behind a GATEWAY is an accepted existing dependency, and KV's baseline encryption exceeds federal PII requirements. Order lives in KV's ledger, never in a provider's file history.
- The KV AI Assistant rule (same comment): the assistant is fully state-dependent. It must self-organize and present the stored data from KV state alone. So everything KV needs to rebuild its view (ledger order, head, receipt chain) is KV state inside sealed blobs, never provider metadata.
- StegVerse-org/.github#162 comment 6372170864 (Lane B): per-endpoint `ledger_designation`, and a store kind a non-git reader can consume. This interface is that seam, with `store_type: "GATEWAY_ENCRYPTED_BLOB"`.
- StegVerse-org/.github#167 comment 6372136062 (G8, provisional): the root key stays in TV/TVC custody. The SKAP Vault holds only wrapped data keys, and unwrapping is a custody transition.

## Provider independence
The adapter must not depend on any one provider. Google Drive is the first backing (SVKV, and Rigel's personal KV example), not part of the contract. Any storage that can keep opaque bytes under a name and do a compare-and-swap on one small pointer can implement it.

Multi-provider redundancy (a StegVerse KV on several major cloud providers) is a later, separately registered task. It is **out of scope** here and not part of ECOSYSTEM-OWN-KV-001's finish point.

## Interface (exact names)
`GatewayStorageAdapter` (what a gateway storage node offers; `adapter_ref` names the binding):

| method | contract |
|---|---|
| `put(location, blob) -> str` | Stores opaque sealed bytes under the `##_<name>` location and returns their sha256 address. |
| `get(location, blob_sha256) -> bytes` | Returns the bytes stored at that address. |
| `list(location) -> list[str]` | Returns the blob addresses (sha256 hex) under the location. Nothing else. |
| `get_head(location) -> str \| None` | Returns the head pointer at `<location>/HEAD`, or None if the ledger is empty. |
| `advance_head(location, expected_previous, new) -> bool` | Compare-and-swap of the head pointer. `new` must already be stored. |

KV's side, `GatewayStore(adapter)`: `put_blob`, `get_blob`, `list_blobs`, `head`, `advance`. Each returns `(value, None)` or `(None, six-field FAIL_CLOSED)`, and never raises past KV.

Opening, `BlobOpener.open(blob) -> bytes`: KV-side only, with a data key unwrapped under TV/TVC custody. The cipher is whatever SKAP-UNDECLARED-CRYPTOGRAPHY-001 settles. KV never imports `cryptography`.

## What KV checks (GatewayStore)
- **Locations.** Only `##_<name>` (`^[0-9]{2}_[A-Za-z0-9][A-Za-z0-9_]*$`), otherwise `KV_STORAGE_LOCATION_INVALID`. There is no `_StegVerse-org` segment and no path separators.
- **No plaintext.** Every blob starts with `stegverse.kv-sealed-blob/v1\n`, and the body must not parse as JSON. Otherwise `KV_GATEWAY_BLOB_NOT_SEALED` on put, and `EXTERNAL_STORAGE_RECORD_REFUSED` on read.
- **Content addressing.** sha256(bytes) must equal the address asked for. A swapped blob is refused.
- **External records never cross.** A listing must be a list of sha256 strings. A get must return bytes. A head must be a sha256 or None. Drive file ids, owners, revisions, modified times and sharing records are refused (`EXTERNAL_STORAGE_RECORD_REFUSED`, class C). The gateway discards them; KV refuses them if they arrive anyway.
- **Append-only head.** `advance` refuses a stale `expected_previous`, or a `new` that isn't stored (`KV_HEAD_POINTER_NOT_APPEND_ONLY`).
- **Adapter failures.** An adapter exception is `KV_GATEWAY_STORAGE_UNREADABLE` (class D), never ALLOW.

## KV computes its receipts from its own side
`runtime/kv_receipt_ledgers.py` reads its two ledgers through this interface:

1. `01_KV_Ledger` (`kv`).
2. `02_SKAP_Vault_Ledger` (`skap_vault`). Reachable only via `SkapLayer2Gate.receipt_ledger` with a layer-1 receipt that this KV's InTr ingress minted.

The read checks the following, in order:
- the digest-pinned contract and designation;
- the pinned storage binding (`.stegverse/kv-gateway/storage-binding.v1.json`);
- genesis pinned;
- the adapter is the bound one;
- opening every blob KV-side;
- every record is a KV receipt for this ledger (a receipt from an Org ledger or a provider record is `KV_LEDGER_FOREIGN_RECORD_REFUSED`);
- a single chain whose head matches the head pointer;
- `read_chain` with the vendored #432 evaluator (unchanged);
- the genesis matches the contract;
- the head is signed by a published `KV_LEDGER_HEAD` attester.

## Rollback protections (kept)
- The head pointer is append-only (compare-and-swap).
- The head is signed (`stegverse.kv-ledger-head-attestation/v1` over the location, genesis, head and the sha256 of the sorted blob-address set).
- `recorded_head`: a head digest already recorded elsewhere (an Org's linked correspondence receipt, or KV's last verified receipt) must still be on the chain read back now. Otherwise the result is `KV_LEDGER_ROLLBACK_DETECTED` (class C).
- Genesis comes from KV's own contract, pinned after observe. A Drive that is empty is never itself a genesis.

## Null implementation (production today)
- `NullGatewayStorageAdapter`: every method raises six-field `SVKV_GATEWAY_STORAGE_NOT_PROVISIONED` (class B, ECOSYSTEM-OWN-KV-001). The binding file pins `gateway_node_id` and `gateway_storage_adapter_ref` as null, and the Drive is `NOT_PROVISIONED`.
- `NullBlobOpener`: `KV_LEDGER_BLOB_KEY_NOT_CUSTODIED` (class B).

Tests (`tests/test_kv_gateway_storage.py`, `tests/kv_gateway_e0.py`) use a TEST-ONLY in-memory adapter and a TEST-ONLY XOR keystream opener. That opener is not encryption.
