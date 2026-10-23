"""Streaming and HTTP Range sha256 measurement for large media (LD-OSR-MP4-01).

Computes sha256 over a byte source in fixed-size chunks without ever holding the
whole source in memory, so a connector download cap (for example 100 MB) does not
stop Lane D from measuring a multi-GB artifact. Two sources are supported:

* ``LocalFileSource``: a local file read as a stream.
* ``HttpRangeSource``: an HTTP(S) URL read with ``Range: bytes=a-b`` requests. Every
  response must be ``206 Partial Content`` with a ``Content-Range`` that matches the
  request and a ``Content-Length`` that matches the range. The total in
  ``Content-Range`` must stay the same for the whole measurement. Short reads and
  dropped connections are resumed from the last byte received. A server that ignores
  Range (answers ``200``), an inconsistent total, a mismatched range or length, or a
  source whose validator changes mid-measurement is refused (FAIL_CLOSED).

The optional chunk manifest records the sha256 of every chunk plus the total, so a
partial or ranged re-measurement of any chunk subset is reproducible and verifiable
against the manifest (``verify_chunk_manifest``).

Standard library only. No new dependency. The receipt this module emits is a
measurement record: it is not truth, not a legal determination and not execution
authority, and it writes no registry or ledger entry.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterator, List, Mapping, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urljoin

RECEIPT_SCHEMA = "stegverse.kv.ranged-sha256-measurement/v1"
MANIFEST_SCHEMA = "stegverse.kv.sha256-chunk-manifest/v1"
REFUSAL_SCHEMA = "stegverse.kv.ranged-sha256-refusal/v1"
TRANSITION = "KV_RANGED_SHA256_MEASUREMENT"
TASK_ID = "LD-OSR-MP4-01"
OWNING_EXISTING_GOAL = "OPTICAL-PHYSICAL-STATE-REPLAY-RESEARCH-001"
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
MIN_CHUNK_SIZE = 1
MAX_CHUNK_SIZE = 1024 * 1024 * 1024
READ_BLOCK = 1024 * 1024
DISCLAIMER = (
    "Measurement record only. Not truth, not a legal determination and not execution "
    "authority. Records only the bytes this run actually read; anything not read is "
    "UNKNOWN_NOT_AUTHENTICALLY_OBSERVED. No registry or ledger write."
)
REDACTED = "REDACTED"
_CONTENT_RANGE = re.compile(r"^\s*bytes\s+(\d+)-(\d+)/(\d+|\*)\s*$", re.IGNORECASE)


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class MeasurementRefused(Exception):
    """FAIL_CLOSED refusal carrying the six-field record."""

    def __init__(self, failure_code: str, failed_predicate: str,
                 required_evidence_or_repair: str, detail: str = "",
                 retry_entrypoint: str = "python -m runtime.ranged_sha256_measurement (same source) after repair",
                 next_attempt: str = "after the repair is in place"):
        super().__init__(f"{failure_code}: {detail or failed_predicate}")
        self.failure_code = failure_code
        self.failed_predicate = failed_predicate
        self.required_evidence_or_repair = required_evidence_or_repair
        self.retry_entrypoint = retry_entrypoint
        self.next_attempt = next_attempt
        self.detail = detail

    def to_record(self, source_descriptor: Optional[dict] = None) -> dict:
        rec = {
            "schema": REFUSAL_SCHEMA,
            "transition": TRANSITION,
            "disposition": "FAIL_CLOSED",
            "failure_code": self.failure_code,
            "failed_predicate": self.failed_predicate,
            "required_evidence_or_repair": self.required_evidence_or_repair,
            "retry_entrypoint": self.retry_entrypoint,
            "owning_existing_goal": OWNING_EXISTING_GOAL,
            "next_attempt": self.next_attempt,
            "detail": self.detail,
            "disclaimer": DISCLAIMER,
            "authority_effect": "NONE",
        }
        if source_descriptor is not None:
            rec["source"] = source_descriptor
        return rec


def _check_chunk_size(chunk_size: int) -> int:
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or not (MIN_CHUNK_SIZE <= chunk_size <= MAX_CHUNK_SIZE):
        raise MeasurementRefused(
            "CHUNK_SIZE_INVALID", f"chunk size is an integer in [{MIN_CHUNK_SIZE}, {MAX_CHUNK_SIZE}]",
            "pass a valid --chunk-size", detail=repr(chunk_size))
    return chunk_size


def redact_url(url: str) -> dict:
    """Describe a URL without secrets: no userinfo, no query values, no fragment."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    netloc = host + (f":{parts.port}" if parts.port else "")
    query_keys = sorted({k for k, _ in parse_qsl(parts.query, keep_blank_values=True)})
    shown_query = "&".join(f"{k}={REDACTED}" for k in query_keys)
    return {
        "scheme": parts.scheme,
        "host": host,
        "port": parts.port,
        "path": parts.path,
        "query_keys": query_keys,
        "url_redacted": urlunsplit((parts.scheme, netloc, parts.path, shown_query, "")),
        "userinfo_present": bool(parts.username or parts.password),
    }


# --------------------------------------------------------------------------- sources

class ByteSource:
    method: str = "UNSPECIFIED"

    def descriptor(self) -> dict:  # pragma: no cover - interface
        raise NotImplementedError

    def total_size(self) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    def iter_range(self, start: int, length: int) -> Iterator[bytes]:  # pragma: no cover
        raise NotImplementedError

    def stats(self) -> dict:
        return {}


class LocalFileSource(ByteSource):
    method = "LOCAL_FILE_STREAM"

    def __init__(self, path: str, read_block: int = READ_BLOCK):
        self.path = os.path.abspath(path)
        self.read_block = read_block
        try:
            st = os.stat(self.path)
        except OSError as exc:
            raise MeasurementRefused("SOURCE_NOT_READABLE", "the local source exists and is readable",
                                     "provide a readable file path", detail=str(exc)) from None
        self._size = st.st_size
        self._mtime_ns = st.st_mtime_ns

    def descriptor(self) -> dict:
        return {"kind": "local_file", "basename": os.path.basename(self.path),
                "size_bytes_at_open": self._size}

    def total_size(self) -> int:
        return self._size

    def _check_unchanged(self):
        st = os.stat(self.path)
        if st.st_size != self._size or st.st_mtime_ns != self._mtime_ns:
            raise MeasurementRefused(
                "SOURCE_CHANGED_DURING_MEASUREMENT", "the local file size and mtime are unchanged for the whole measurement",
                "re-run on a file that is not being written", detail=f"size {self._size}->{st.st_size}")

    def iter_range(self, start: int, length: int) -> Iterator[bytes]:
        remaining = length
        with open(self.path, "rb") as fh:
            fh.seek(start)
            while remaining > 0:
                block = fh.read(min(self.read_block, remaining))
                if not block:
                    raise MeasurementRefused(
                        "SOURCE_TRUNCATED", "the local file yields every byte up to its declared size",
                        "re-run on a stable file", detail=f"EOF at {start + length - remaining} < {start + length}")
                remaining -= len(block)
                yield block
        self._check_unchanged()


@dataclass
class _HttpStats:
    requests: int = 0
    resumes: int = 0
    redirects: int = 0
    bytes_received: int = 0
    final_host: str = ""


class HttpRangeSource(ByteSource):
    """HTTP(S) byte source read strictly with Range requests (206 only)."""

    method = "HTTP_RANGE_GET"

    def __init__(self, url: str, headers: Optional[Mapping[str, str]] = None, *,
                 timeout: float = 60.0, max_retries: int = 5, retry_backoff: float = 0.5,
                 max_redirects: int = 5, expected_total: Optional[int] = None,
                 probe_block: int = 1, read_block: int = READ_BLOCK,
                 ssl_context: Optional[ssl.SSLContext] = None,
                 sleep: Callable[[float], None] = time.sleep):
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise MeasurementRefused("SOURCE_URL_INVALID", "the source URL is an absolute http(s) URL",
                                     "pass an http:// or https:// URL", detail=redact_url(url)["url_redacted"])
        self.url = url
        self._headers = dict(headers or {})
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.max_redirects = max_redirects
        self.expected_total = expected_total
        self.probe_block = probe_block
        self.read_block = read_block
        self.ssl_context = ssl_context
        self._sleep = sleep
        self._total: Optional[int] = None
        self._validator: Optional[tuple] = None
        self._stats = _HttpStats()
        self._resolved_url: Optional[str] = None

    # -- descriptor (never includes header values or query values)
    def descriptor(self) -> dict:
        d = {"kind": "http_range", **redact_url(self.url),
             "request_header_names": sorted(self._headers)}
        if self.expected_total is not None:
            d["expected_total_bytes"] = self.expected_total
        return d

    def stats(self) -> dict:
        s = self._stats
        return {"http_requests": s.requests, "resumes": s.resumes, "redirects": s.redirects,
                "bytes_received": s.bytes_received, "final_host": s.final_host,
                "validator": None if self._validator is None else self._validator[0]}

    # -- low level
    def _connect(self, parts):
        port = parts.port
        if parts.scheme == "https":
            ctx = self.ssl_context or ssl.create_default_context()
            return http.client.HTTPSConnection(parts.hostname, port, timeout=self.timeout, context=ctx)
        return http.client.HTTPConnection(parts.hostname, port, timeout=self.timeout)

    def _open(self, first: int, last: int):
        """GET bytes=first-last, following redirects; returns (conn, response)."""
        url = self._resolved_url or self.url
        origin_host = urlsplit(self.url).hostname
        for _ in range(self.max_redirects + 1):
            parts = urlsplit(url)
            headers = {"Range": f"bytes={first}-{last}", "Accept-Encoding": "identity"}
            if parts.hostname == origin_host:
                headers.update(self._headers)  # never forward caller headers to another host
            conn = self._connect(parts)
            target = parts.path or "/"
            if parts.query:
                target += "?" + parts.query
            self._stats.requests += 1
            conn.request("GET", target, headers=headers)
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                loc = resp.getheader("Location")
                resp.read()
                conn.close()
                if not loc:
                    raise MeasurementRefused("REDIRECT_WITHOUT_LOCATION", "a redirect response names its Location",
                                             "use a direct URL", detail=str(resp.status))
                url = urljoin(url, loc)
                self._stats.redirects += 1
                continue
            self._stats.final_host = parts.hostname or ""
            self._resolved_url = url
            return conn, resp
        raise MeasurementRefused("TOO_MANY_REDIRECTS", f"the source resolves within {self.max_redirects} redirects",
                                 "use a direct URL")

    def _check_response(self, resp, first: int, last: int) -> int:
        """Validate a ranged response; returns the number of body bytes to read."""
        if resp.status == 200:
            raise MeasurementRefused(
                "RANGE_NOT_HONOURED", "the server answers a Range request with 206 Partial Content",
                "use a source that supports HTTP Range (or a sanctioned transfer path that does)",
                detail="server returned 200 to a Range request")
        if resp.status == 416:
            raise MeasurementRefused("RANGE_NOT_SATISFIABLE", "the requested range lies within the source",
                                     "check the declared total", detail=resp.getheader("Content-Range") or "")
        if resp.status != 206:
            raise MeasurementRefused("HTTP_STATUS_UNEXPECTED", "the server answers 206 Partial Content",
                                     "check the URL and access", detail=f"HTTP {resp.status}")
        enc = (resp.getheader("Content-Encoding") or "identity").strip().lower()
        if enc not in ("", "identity"):
            raise MeasurementRefused("CONTENT_ENCODING_NOT_IDENTITY", "the ranged body is the raw bytes (identity encoding)",
                                     "request identity encoding", detail=enc)
        cr = resp.getheader("Content-Range")
        m = _CONTENT_RANGE.match(cr or "")
        if not m:
            raise MeasurementRefused("CONTENT_RANGE_MISSING_OR_MALFORMED", "a 206 response carries 'Content-Range: bytes a-b/total'",
                                     "use a server with standard Range support", detail=repr(cr))
        s, e, t = int(m.group(1)), int(m.group(2)), m.group(3)
        if t == "*":
            raise MeasurementRefused("TOTAL_NOT_DECLARED", "Content-Range declares the complete length",
                                     "use a server that declares the total", detail=cr)
        total = int(t)
        if self._total is None:
            if self.expected_total is not None and total != self.expected_total:
                raise MeasurementRefused("TOTAL_MISMATCH_EXPECTED", "the server's total equals the expected total",
                                         "confirm which artifact is meant", detail=f"server {total} != expected {self.expected_total}")
            self._total = total
        elif total != self._total:
            raise MeasurementRefused("TOTAL_INCONSISTENT", "every response declares the same total length",
                                     "re-run when the source is stable", detail=f"{total} != {self._total}")
        want_last = min(last, self._total - 1)
        if s != first or e != want_last:
            raise MeasurementRefused("CONTENT_RANGE_MISMATCH", "Content-Range covers exactly the requested range",
                                     "use a server with standard Range support", detail=f"asked {first}-{want_last}, got {s}-{e}")
        clen = resp.getheader("Content-Length")
        n = e - s + 1
        if clen is None or not clen.strip().isdigit() or int(clen) != n:
            raise MeasurementRefused("CONTENT_LENGTH_MISMATCH", "Content-Length equals the length of the Content-Range",
                                     "use a server with standard Range support", detail=f"Content-Length {clen!r} != {n}")
        etag = resp.getheader("ETag")
        lm = resp.getheader("Last-Modified")
        validator = ("ETag", etag) if etag and not etag.startswith("W/") else (("Last-Modified", lm) if lm else None)
        if validator is not None:
            if self._validator is None:
                self._validator = validator
            elif validator != self._validator:
                raise MeasurementRefused("SOURCE_CHANGED_DURING_MEASUREMENT", "the source validator (ETag/Last-Modified) is constant",
                                         "re-run when the source is stable", detail=f"{validator[0]} changed")
        return n

    def total_size(self) -> int:
        if self._total is None:
            last = max(self.probe_block, 1) - 1
            conn, resp = self._open(0, last)
            try:
                n = self._check_response(resp, 0, last)
                resp.read(n)
            finally:
                conn.close()
        return self._total

    def iter_range(self, start: int, length: int) -> Iterator[bytes]:
        if length <= 0:
            return
        end = start + length - 1
        pos = start
        failures = 0
        while pos <= end:
            conn = None
            try:
                conn, resp = self._open(pos, end)
                n = self._check_response(resp, pos, end)
                got = 0
                while got < n:
                    block = resp.read(min(self.read_block, n - got))
                    if not block:
                        raise http.client.IncompleteRead(b"", n - got)
                    got += len(block)
                    pos += len(block)
                    self._stats.bytes_received += len(block)
                    failures = 0
                    yield block
            except MeasurementRefused:
                raise
            except (http.client.HTTPException, OSError, socket.timeout) as exc:
                failures += 1
                if failures > self.max_retries:
                    raise MeasurementRefused(
                        "TRANSFER_INCOMPLETE", f"bytes {start}-{end} arrive completely within {self.max_retries} resumes",
                        "retry later or use a more reliable transfer path",
                        detail=f"stopped at byte {pos}: {type(exc).__name__}") from None
                self._stats.resumes += 1
                self._sleep(self.retry_backoff * failures)
            finally:
                if conn is not None:
                    conn.close()


# --------------------------------------------------------------------------- measurement

@dataclass
class Measurement:
    total_bytes: int
    chunk_size: int
    sha256: str
    chunks: List[dict] = field(default_factory=list)

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    def manifest(self) -> dict:
        return {"schema": MANIFEST_SCHEMA, "algorithm": "sha256", "chunk_size": self.chunk_size,
                "total_bytes": self.total_bytes, "chunk_count": self.chunk_count,
                "sha256": self.sha256, "chunks": self.chunks}

    def manifest_sha256(self) -> str:
        return sha256_hex(canonical_json(self.manifest()).encode("utf-8"))


def chunk_spans(total: int, chunk_size: int) -> List[tuple]:
    return [(i, off, min(chunk_size, total - off)) for i, off in enumerate(range(0, total, chunk_size))]


def measure(source: ByteSource, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Measurement:
    """Stream the whole source once: overall sha256 plus per-chunk sha256."""
    _check_chunk_size(chunk_size)
    total = source.total_size()
    whole = hashlib.sha256()
    chunks = []
    seen = 0
    for idx, off, ln in chunk_spans(total, chunk_size):
        h = hashlib.sha256()
        n = 0
        for block in source.iter_range(off, ln):
            h.update(block)
            whole.update(block)
            n += len(block)
        if n != ln:
            raise MeasurementRefused("CHUNK_LENGTH_MISMATCH", "each chunk yields exactly its length",
                                     "re-run", detail=f"chunk {idx}: {n} != {ln}")
        seen += n
        chunks.append({"index": idx, "offset": off, "length": ln, "sha256": h.hexdigest()})
    if seen != total:
        raise MeasurementRefused("TOTAL_BYTES_MISMATCH", "bytes hashed equal the declared total",
                                 "re-run", detail=f"{seen} != {total}")
    return Measurement(total_bytes=total, chunk_size=chunk_size, sha256=whole.hexdigest(), chunks=chunks)


def verify_chunk_manifest(source: ByteSource, manifest: dict,
                          indices: Optional[Sequence[int]] = None) -> dict:
    """Re-measure some or all chunks of a manifest against a source (ranged reproduction)."""
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise MeasurementRefused("MANIFEST_SCHEMA_UNKNOWN", f"the manifest schema is {MANIFEST_SCHEMA}",
                                 "pass a manifest written by this module")
    cs, total = manifest["chunk_size"], manifest["total_bytes"]
    _check_chunk_size(cs)
    spans = chunk_spans(total, cs)
    rows = manifest["chunks"]
    if len(rows) != len(spans) or any((r["index"], r["offset"], r["length"]) != s for r, s in zip(rows, spans)):
        raise MeasurementRefused("MANIFEST_LAYOUT_INVALID", "manifest chunks tile [0,total) at chunk_size",
                                 "regenerate the manifest")
    src_total = source.total_size()
    if src_total != total:
        raise MeasurementRefused("TOTAL_MISMATCH_MANIFEST", "the source total equals the manifest total",
                                 "confirm which artifact is meant", detail=f"{src_total} != {total}")
    chosen = list(range(len(rows))) if indices is None else sorted(set(indices))
    mismatched = []
    for i in chosen:
        if not 0 <= i < len(rows):
            raise MeasurementRefused("CHUNK_INDEX_OUT_OF_RANGE", "requested chunk indices exist in the manifest",
                                     "pass valid indices", detail=str(i))
        r = rows[i]
        h = hashlib.sha256()
        for block in source.iter_range(r["offset"], r["length"]):
            h.update(block)
        if h.hexdigest() != r["sha256"]:
            mismatched.append(i)
    return {"verified_indices": chosen, "mismatched_indices": mismatched,
            "manifest_sha256": sha256_hex(canonical_json(manifest).encode("utf-8")),
            "result": "MATCH" if not mismatched else "MISMATCH"}


def build_receipt(source: ByteSource, m: Measurement, *, observed_at: Optional[str] = None,
                  context: Optional[dict] = None) -> dict:
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "transition": TRANSITION,
        "task": TASK_ID,
        "owning_existing_goal": OWNING_EXISTING_GOAL,
        "source": source.descriptor(),
        "method": {"algorithm": "sha256", "mode": "SEQUENTIAL_FIXED_CHUNKS_STREAMED",
                   "transport": source.method, "implementation": "runtime/ranged_sha256_measurement.py (stdlib only)"},
        "total_bytes": m.total_bytes,
        "chunk_size": m.chunk_size,
        "chunk_count": m.chunk_count,
        "chunk_manifest_schema": MANIFEST_SCHEMA,
        "chunk_manifest_sha256": m.manifest_sha256(),
        "sha256": m.sha256,
        "transfer": source.stats(),
        "observed_at": observed_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "disposition": "MEASURED",
        "disclaimer": DISCLAIMER,
        "authority_effect": "NONE",
        "ledger_receipt": "NONE (measurement record; no registry or ledger write)",
    }
    if context:
        receipt["context"] = dict(context)
    receipt["receipt_sha256"] = sha256_hex(canonical_json(receipt).encode("utf-8"))
    return receipt


def receipt_digest_ok(receipt: dict) -> bool:
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return receipt.get("receipt_sha256") == sha256_hex(canonical_json(body).encode("utf-8"))


# --------------------------------------------------------------------------- CLI

def _headers_from_env(specs: Sequence[str]) -> Dict[str, str]:
    """--header-env 'Authorization=ENV_VAR': value read from the environment, never from argv."""
    out = {}
    for spec in specs:
        name, sep, var = spec.partition("=")
        if not sep or not name or not var:
            raise MeasurementRefused("HEADER_SPEC_INVALID", "--header-env is NAME=ENV_VAR", "fix the argument", detail=name)
        if var not in os.environ:
            raise MeasurementRefused("HEADER_ENV_MISSING", "the named environment variable is set",
                                     "export the variable", detail=var)
        out[name] = os.environ[var]
    return out


def _write_json(path: str, obj) -> None:
    if os.path.exists(path):
        raise MeasurementRefused("OUTPUT_EXISTS", "outputs are new files (never overwrite)",
                                 "choose a new output path", detail=os.path.basename(path))
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m runtime.ranged_sha256_measurement", description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--url")
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    p.add_argument("--expected-total", type=int)
    p.add_argument("--header-env", action="append", default=[])
    p.add_argument("--max-retries", type=int, default=5)
    p.add_argument("--manifest-out")
    p.add_argument("--receipt-out")
    p.add_argument("--verify-manifest", help="re-measure chunks of an existing manifest instead")
    p.add_argument("--chunks", help="comma-separated chunk indices for --verify-manifest")
    a = p.parse_args(argv)
    src = None
    try:
        if a.file:
            src = LocalFileSource(a.file)
        else:
            src = HttpRangeSource(a.url, _headers_from_env(a.header_env), max_retries=a.max_retries,
                                  expected_total=a.expected_total)
        if a.file and a.expected_total is not None and src.total_size() != a.expected_total:
            raise MeasurementRefused("TOTAL_MISMATCH_EXPECTED", "the source total equals the expected total",
                                     "confirm which artifact is meant", detail=f"{src.total_size()} != {a.expected_total}")
        if a.verify_manifest:
            with open(a.verify_manifest, encoding="utf-8") as fh:
                man = json.load(fh)
            idx = [int(x) for x in a.chunks.split(",")] if a.chunks else None
            res = verify_chunk_manifest(src, man, idx)
            print(json.dumps(res, indent=2, sort_keys=True))
            return 0 if res["result"] == "MATCH" else 3
        m = measure(src, a.chunk_size)
        receipt = build_receipt(src, m)
        if a.manifest_out:
            _write_json(a.manifest_out, m.manifest())
        if a.receipt_out:
            _write_json(a.receipt_out, receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    except MeasurementRefused as exc:
        print(json.dumps(exc.to_record(src.descriptor() if src else None), indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
