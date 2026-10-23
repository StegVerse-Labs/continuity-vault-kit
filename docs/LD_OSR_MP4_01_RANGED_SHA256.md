# LD-OSR-MP4-01: streaming / HTTP Range sha256 measurement

Lane D (KV and WorkSpace), class B. Owning existing goal: `OPTICAL-PHYSICAL-STATE-REPLAY-RESEARCH-001`.

**Not truth, not a legal determination, not execution authority.** A receipt records only the
bytes a run actually read. It writes no registry or ledger entry.

## Why
The Drive connector caps downloads at 10 MB and 100 MB, so Lane D could not hash
KV `1h-UE…` (7,271,648,696 B) through it, and the PAT-003 primary clip
`DP_free_drop_video.mp4` (481,804,387 B) is also above the cap. This module removes the cap as a
limit on *measurement*: it hashes any size in fixed chunks without holding the source in memory.

## What
`runtime/ranged_sha256_measurement.py`, standard library only.

| Source | Transport | Fail-closed checks |
|---|---|---|
| `LocalFileSource(path)` | `LOCAL_FILE_STREAM` | EOF before declared size (`SOURCE_TRUNCATED`); size/mtime change (`SOURCE_CHANGED_DURING_MEASUREMENT`) |
| `HttpRangeSource(url, headers)` | `HTTP_RANGE_GET` | `200` to a Range request (`RANGE_NOT_HONOURED`); malformed/missing `Content-Range`; range not as requested (`CONTENT_RANGE_MISMATCH`); `Content-Length` ≠ range (`CONTENT_LENGTH_MISMATCH`); total changes (`TOTAL_INCONSISTENT`); total ≠ `--expected-total` (`TOTAL_MISMATCH_EXPECTED`); ETag/Last-Modified changes; resumes exhausted (`TRANSFER_INCOMPLETE`) |

Dropped connections and short bodies resume from the last byte received (`Range: bytes=<pos>-<end>`).
Caller headers (for example `Authorization`) are passed from environment variables
(`--header-env Authorization=ENV_VAR`), never forwarded to a different host on redirect, and never
recorded: the source descriptor keeps the scheme, host, port, path, query *keys* and header *names* only.

Every refusal is a six-field FAIL_CLOSED record (`failure_code`, `failed_predicate`,
`required_evidence_or_repair`, `retry_entrypoint`, `owning_existing_goal`, `next_attempt`).

### Chunk manifest
`stegverse.kv.sha256-chunk-manifest/v1`: `chunk_size`, `total_bytes`, `chunk_count`, overall
`sha256`, and per chunk `{index, offset, length, sha256}`. Its digest is the sha256 of canonical JSON
(sorted keys, `,`/`:` separators). `verify_chunk_manifest(source, manifest, indices)` re-measures any
subset of chunks by range, so a partial measurement is reproducible and checkable.

### Receipt
`stegverse.kv.ranged-sha256-measurement/v1`, transition `KV_RANGED_SHA256_MEASUREMENT`: source
descriptor (no secrets), `total_bytes`, `chunk_size`, `chunk_count`, `chunk_manifest_sha256`,
`sha256`, `method`, transfer stats, disclaimer, `authority_effect: NONE`, and `receipt_sha256`
(canonical JSON of the receipt without that field). Output files are created exclusively and never overwritten.

```
python -m runtime.ranged_sha256_measurement --file clip.mp4 --expected-total 481804387 \
    --manifest-out clip.manifest.json --receipt-out clip.receipt.json
python -m runtime.ranged_sha256_measurement --url "https://…" --header-env Authorization=DRIVE_BEARER \
    --chunk-size 67108864 --expected-total 7271648696 --receipt-out kv-1h-UE.receipt.json
python -m runtime.ranged_sha256_measurement --file clip.mp4 --verify-manifest clip.manifest.json --chunks 0,7
```
Exit codes: `0` measured / manifest match, `2` FAIL_CLOSED, `3` manifest mismatch.

## Not done here
- The real clips were **not** measured: their bytes are not observed by Lane D (owner export of the
  481,804,387 B clip is pending, LD-OSR-MP4-03 / RIGHTS-03, class C). Which sanctioned credential and
  URL reach KV `1h-UE…` by Range is a separate custody question; this PR adds no credential.
- **LD-OSR-MP4-02 (Lane A)** can consume this: hash the primary clip on arrival, fill
  manifest v2 `sha256` and chart KV-8 from the receipt's `sha256`, and cite `receipt_sha256` and
  `chunk_manifest_sha256`.
