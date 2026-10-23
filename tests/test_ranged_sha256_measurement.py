"""LD-OSR-MP4-01: streaming / HTTP Range sha256 measurement (stdlib only, 0 skipped)."""
import hashlib
import http.server
import io
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import ranged_sha256_measurement as R  # noqa: E402

LARGE_BYTES = int(os.environ.get("LD_OSR_LARGE_TEST_BYTES", str(112 * 1024 * 1024 + 7)))  # > 100 MB cap


def write_synthetic(path, size, seed=b"ld-osr-mp4-01"):
    """Deterministic, non-repeating-ish bytes written in 1 MiB blocks (never held whole)."""
    block = hashlib.sha512(seed).digest() * 16384  # 1 MiB
    h = hashlib.sha256()
    with open(path, "wb") as fh:
        written, i = 0, 0
        while written < size:
            tag = i.to_bytes(8, "big")
            b = (tag + block[8:])[: min(len(block), size - written)]
            fh.write(b)
            h.update(b)
            written += len(b)
            i += 1
    return h.hexdigest()


def hashlib_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class RangeHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *a):
        pass

    def do_GET(self):
        srv = self.server
        srv.hits += 1
        if self.path.startswith("/redirect"):
            self.send_response(302)
            self.send_header("Location", "/file?sig=secretvalue")
            self.end_headers()
            return
        size = os.path.getsize(srv.path)
        mode = srv.mode
        rng = self.headers.get("Range")
        srv.seen_headers.append(dict(self.headers))
        if mode == "no_range" or not rng:
            self.send_response(200)
            self.send_header("Content-Length", str(size))
            self.end_headers()
            with open(srv.path, "rb") as fh:
                self.wfile.write(fh.read())
            return
        m = re.match(r"bytes=(\d+)-(\d+)$", rng)
        a, b = int(m.group(1)), min(int(m.group(2)), size - 1)
        total = size
        if mode == "total_drift" and srv.hits > 1:
            total = size + 1
        if mode == "wrong_range":
            a2 = a + 1 if a + 1 <= b else a
        else:
            a2 = a
        n = b - a2 + 1
        clen = n - 1 if mode == "short_content_length" else n
        self.send_response(206)
        self.send_header("Content-Range", f"bytes {a2}-{b}/{total}")
        self.send_header("Content-Length", str(clen))
        if mode == "etag_change":
            self.send_header("ETag", f'"v{srv.hits}"')
        else:
            self.send_header("ETag", '"stable"')
        self.end_headers()
        with open(srv.path, "rb") as fh:
            fh.seek(a2)
            body = fh.read(n)
        cut = None
        if mode == "truncate_once" and n > 1 and a2 not in srv.truncated:
            cut = n // 2  # one dropped connection per chunk; client must resume
        elif mode == "truncate_at_fixed_offset" and b >= srv.dead_offset:
            cut = max(0, srv.dead_offset - a2)  # bytes past dead_offset never arrive
        if cut is not None:
            srv.truncated.add(a2)
            self.wfile.write(body[:cut])
            self.wfile.flush()
            self.close_connection = True
            return
        self.wfile.write(body[:clen])


class Server:
    def __init__(self, path, mode="ok"):
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RangeHandler)
        self.httpd.daemon_threads = True
        self.httpd.path, self.httpd.mode = path, mode
        self.httpd.hits, self.httpd.truncated, self.httpd.seen_headers = 0, set(), []
        self.httpd.dead_offset = 500_000
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.t.start()
        return self

    def url(self, p="/file"):
        return f"http://127.0.0.1:{self.httpd.server_address[1]}{p}"

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()


def http_src(srv, **kw):
    kw.setdefault("sleep", lambda s: None)
    kw.setdefault("timeout", 10)
    return R.HttpRangeSource(srv.url(kw.pop("p", "/file")), **kw)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.tmp.name
        cls.small = os.path.join(d, "small.bin")
        cls.small_sha = write_synthetic(cls.small, 1_000_003)
        cls.empty = os.path.join(d, "empty.bin")
        open(cls.empty, "wb").close()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class LocalEquivalenceTests(Base):
    def test_small_file_equals_hashlib_for_many_chunk_sizes(self):
        for cs in (1 << 10, 4096, 65536, 1_000_003, 1_000_004, R.DEFAULT_CHUNK_SIZE, 333_333):
            m = R.measure(R.LocalFileSource(self.small), cs)
            self.assertEqual(m.sha256, self.small_sha, cs)
            self.assertEqual(m.sha256, hashlib_file(self.small))
            self.assertEqual(m.total_bytes, 1_000_003)
            self.assertEqual(m.chunk_count, -(-1_000_003 // cs))
            self.assertEqual(sum(c["length"] for c in m.chunks), 1_000_003)

    def test_chunk_hashes_equal_hashlib_of_each_slice(self):
        m = R.measure(R.LocalFileSource(self.small), 300_000)
        data = Path(self.small).read_bytes()
        for c in m.chunks:
            self.assertEqual(c["sha256"], hashlib.sha256(data[c["offset"]:c["offset"] + c["length"]]).hexdigest())

    def test_empty_file(self):
        m = R.measure(R.LocalFileSource(self.empty), 1024)
        self.assertEqual(m.sha256, hashlib.sha256(b"").hexdigest())
        self.assertEqual((m.total_bytes, m.chunk_count), (0, 0))

    def test_large_file_over_100mb_streamed_without_loading_whole(self):
        p = os.path.join(self.tmp.name, "large.bin")
        expect = write_synthetic(p, LARGE_BYTES, seed=b"large")
        self.assertGreater(LARGE_BYTES, 100 * 1024 * 1024)
        src = R.LocalFileSource(p)
        biggest = []
        orig = src.iter_range

        def spy(start, length):
            for b in orig(start, length):
                biggest.append(len(b))
                yield b
        src.iter_range = spy
        m = R.measure(src, 16 * 1024 * 1024)
        self.assertEqual(m.sha256, expect)
        self.assertEqual(m.sha256, hashlib_file(p))
        self.assertLessEqual(max(biggest), R.READ_BLOCK)
        self.assertEqual(m.total_bytes, LARGE_BYTES)
        os.remove(p)

    def test_invalid_chunk_size_refused(self):
        for cs in (0, -1, True, 1.5):
            with self.assertRaises(R.MeasurementRefused) as cm:
                R.measure(R.LocalFileSource(self.small), cs)
            self.assertEqual(cm.exception.failure_code, "CHUNK_SIZE_INVALID")

    def test_missing_file_refused(self):
        with self.assertRaises(R.MeasurementRefused) as cm:
            R.LocalFileSource(os.path.join(self.tmp.name, "nope.bin"))
        self.assertEqual(cm.exception.failure_code, "SOURCE_NOT_READABLE")

    def test_local_file_truncated_mid_measurement_refused(self):
        p = os.path.join(self.tmp.name, "shrinks.bin")
        write_synthetic(p, 200_000)
        src = R.LocalFileSource(p)
        with open(p, "r+b") as fh:
            fh.truncate(150_000)
        with self.assertRaises(R.MeasurementRefused) as cm:
            R.measure(src, 64 * 1024)
        # FAIL_CLOSED either at EOF or at the post-chunk size/mtime check, whichever fires first
        self.assertIn(cm.exception.failure_code, ("SOURCE_TRUNCATED", "SOURCE_CHANGED_DURING_MEASUREMENT"))


class ManifestAndReceiptTests(Base):
    def test_manifest_digest_and_partial_verification(self):
        src = R.LocalFileSource(self.small)
        m = R.measure(src, 100_000)
        man = m.manifest()
        self.assertEqual(man["chunk_count"], 11)
        self.assertEqual(m.manifest_sha256(), hashlib.sha256(R.canonical_json(man).encode()).hexdigest())
        res = R.verify_chunk_manifest(src, man, [0, 5, 10])
        self.assertEqual((res["result"], res["mismatched_indices"]), ("MATCH", []))
        self.assertEqual(res["manifest_sha256"], m.manifest_sha256())
        self.assertEqual(R.verify_chunk_manifest(src, man)["verified_indices"], list(range(11)))

    def test_manifest_detects_tampered_chunk_and_bad_layout(self):
        src = R.LocalFileSource(self.small)
        man = R.measure(src, 100_000).manifest()
        bad = json.loads(json.dumps(man))
        bad["chunks"][3]["sha256"] = "0" * 64
        self.assertEqual(R.verify_chunk_manifest(src, bad, [3])["mismatched_indices"], [3])
        bad2 = json.loads(json.dumps(man))
        bad2["chunks"][2]["length"] += 1
        with self.assertRaises(R.MeasurementRefused) as cm:
            R.verify_chunk_manifest(src, bad2)
        self.assertEqual(cm.exception.failure_code, "MANIFEST_LAYOUT_INVALID")
        bad3 = json.loads(json.dumps(man))
        bad3["total_bytes"] += 1
        bad3["chunks"][-1]["length"] += 1
        with self.assertRaises(R.MeasurementRefused) as cm:
            R.verify_chunk_manifest(src, bad3)
        self.assertEqual(cm.exception.failure_code, "TOTAL_MISMATCH_MANIFEST")

    def test_receipt_fields_disclaimer_and_digest(self):
        src = R.LocalFileSource(self.small)
        m = R.measure(src, 250_000)
        r = R.build_receipt(src, m, observed_at="2026-10-23T00:00:00Z")
        for k in ("source", "total_bytes", "chunk_size", "chunk_count", "chunk_manifest_sha256", "sha256", "method"):
            self.assertIn(k, r)
        self.assertEqual(r["sha256"], self.small_sha)
        self.assertEqual(r["chunk_count"], 5)
        self.assertEqual(r["chunk_manifest_sha256"], m.manifest_sha256())
        self.assertEqual(r["method"]["transport"], "LOCAL_FILE_STREAM")
        disc = r["disclaimer"].lower()
        for phrase in ("not truth", "not a legal determination", "not execution authority"):
            self.assertIn(phrase, disc)
        self.assertEqual(r["authority_effect"], "NONE")
        self.assertTrue(R.receipt_digest_ok(r))
        r2 = dict(r, sha256="0" * 64)
        self.assertFalse(R.receipt_digest_ok(r2))
        self.assertNotIn(self.tmp.name, json.dumps(r))  # only the basename is recorded

    def test_refusal_record_has_six_fields(self):
        e = R.MeasurementRefused("X", "p", "r")
        rec = e.to_record()
        for k in ("failure_code", "failed_predicate", "required_evidence_or_repair",
                  "retry_entrypoint", "owning_existing_goal", "next_attempt"):
            self.assertTrue(rec[k], k)
        self.assertEqual(rec["disposition"], "FAIL_CLOSED")


class HttpRangeTests(Base):
    def test_http_range_equals_hashlib_small_many_chunk_sizes(self):
        with Server(self.small) as s:
            for cs in (4096, 99_999, 1_000_003, R.DEFAULT_CHUNK_SIZE):
                m = R.measure(http_src(s), cs)
                self.assertEqual(m.sha256, self.small_sha, cs)
                self.assertEqual(m.total_bytes, 1_000_003)
            local = R.measure(R.LocalFileSource(self.small), 99_999)
            remote = R.measure(http_src(s), 99_999)
            self.assertEqual(local.manifest(), remote.manifest())
            self.assertEqual(local.manifest_sha256(), remote.manifest_sha256())

    def test_http_range_large_over_100mb(self):
        p = os.path.join(self.tmp.name, "large_http.bin")
        expect = write_synthetic(p, LARGE_BYTES, seed=b"large-http")
        with Server(p) as s:
            src = http_src(s)
            m = R.measure(src, 32 * 1024 * 1024)
            self.assertEqual(m.sha256, expect)
            self.assertEqual(m.total_bytes, LARGE_BYTES)
            r = R.build_receipt(src, m)
            self.assertEqual(r["method"]["transport"], "HTTP_RANGE_GET")
            self.assertEqual(r["transfer"]["bytes_received"], LARGE_BYTES)
        os.remove(p)

    def test_http_resumes_after_truncated_body(self):
        with Server(self.small, "truncate_once") as s:
            src = http_src(s)
            m = R.measure(src, 300_000)
            self.assertEqual(m.sha256, self.small_sha)
            self.assertGreaterEqual(src.stats()["resumes"], 4)
            self.assertEqual(src.stats()["bytes_received"], 1_000_003)

    def test_http_partial_chunk_verification_against_local_manifest(self):
        man = R.measure(R.LocalFileSource(self.small), 200_000).manifest()
        with Server(self.small) as s:
            res = R.verify_chunk_manifest(http_src(s), man, [1, 4])
        self.assertEqual(res["result"], "MATCH")

    def test_redirect_followed_and_query_secrets_redacted(self):
        with Server(self.small) as s:
            src = R.HttpRangeSource(s.url("/redirect?token=abc123"), {"Authorization": "Bearer s3cr3t"},
                                    sleep=lambda x: None)
            m = R.measure(src, 500_000)
            self.assertEqual(m.sha256, self.small_sha)
            r = R.build_receipt(src, m)
            text = json.dumps(r)
            for secret in ("abc123", "s3cr3t", "secretvalue", "Bearer"):
                self.assertNotIn(secret, text)
            self.assertEqual(r["source"]["query_keys"], ["token"])
            self.assertEqual(r["source"]["request_header_names"], ["Authorization"])
            self.assertGreaterEqual(r["transfer"]["redirects"], 1)

    def test_userinfo_not_recorded(self):
        d = R.redact_url("https://user:pw@example.org:8443/a/b.mp4?X-Amz-Signature=zzz&k=1#frag")
        self.assertEqual(d["url_redacted"], "https://example.org:8443/a/b.mp4?X-Amz-Signature=REDACTED&k=REDACTED")
        self.assertTrue(d["userinfo_present"])
        self.assertNotIn("pw", json.dumps(d))

    # ---- negative (FAIL_CLOSED)
    def _refused(self, mode, code, cs=300_000, **kw):
        with Server(self.small, mode) as s:
            with self.assertRaises(R.MeasurementRefused) as cm:
                R.measure(http_src(s, **kw), cs)
        self.assertEqual(cm.exception.failure_code, code)
        rec = cm.exception.to_record()
        self.assertEqual(rec["disposition"], "FAIL_CLOSED")
        return cm.exception

    def test_server_ignoring_range_refused(self):
        self._refused("no_range", "RANGE_NOT_HONOURED")

    def test_server_ignoring_range_refused_even_when_one_chunk_covers_file(self):
        self._refused("no_range", "RANGE_NOT_HONOURED", cs=R.DEFAULT_CHUNK_SIZE)

    def test_truncated_source_refused_after_retries(self):
        e = self._refused("truncate_at_fixed_offset", "TRANSFER_INCOMPLETE", max_retries=2)
        self.assertIn("stopped at byte 500000", e.detail)

    def test_content_length_shorter_than_range_refused(self):
        self._refused("short_content_length", "CONTENT_LENGTH_MISMATCH")

    def test_total_changes_between_responses_refused(self):
        self._refused("total_drift", "TOTAL_INCONSISTENT")

    def test_expected_total_mismatch_refused(self):
        self._refused("ok", "TOTAL_MISMATCH_EXPECTED", expected_total=481_804_387)

    def test_content_range_not_matching_request_refused(self):
        self._refused("wrong_range", "CONTENT_RANGE_MISMATCH")

    def test_validator_change_refused(self):
        self._refused("etag_change", "SOURCE_CHANGED_DURING_MEASUREMENT")

    def test_non_http_url_refused(self):
        with self.assertRaises(R.MeasurementRefused) as cm:
            R.HttpRangeSource("ftp://example.org/x")
        self.assertEqual(cm.exception.failure_code, "SOURCE_URL_INVALID")


class CliTests(Base):
    def test_cli_file_writes_new_manifest_and_receipt_and_refuses_overwrite(self):
        out = tempfile.mkdtemp(dir=self.tmp.name)
        man, rec = os.path.join(out, "m.json"), os.path.join(out, "r.json")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = R.main(["--file", self.small, "--chunk-size", "100000", "--manifest-out", man, "--receipt-out", rec])
        self.assertEqual(rc, 0)
        r = json.loads(Path(rec).read_text())
        self.assertEqual(r["sha256"], self.small_sha)
        self.assertEqual(r["chunk_manifest_sha256"],
                         hashlib.sha256(R.canonical_json(json.loads(Path(man).read_text())).encode()).hexdigest())
        before = Path(rec).read_bytes()
        with redirect_stdout(io.StringIO()) as b2:
            rc = R.main(["--file", self.small, "--receipt-out", rec])
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads(b2.getvalue())["failure_code"], "OUTPUT_EXISTS")
        self.assertEqual(Path(rec).read_bytes(), before)
        with redirect_stdout(io.StringIO()) as b3:
            rc = R.main(["--file", self.small, "--verify-manifest", man, "--chunks", "0,9"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(b3.getvalue())["result"], "MATCH")

    def test_cli_header_from_env_value_never_printed(self):
        with Server(self.small) as s:
            os.environ["LD_OSR_TEST_TOKEN"] = "Bearer t0ps3cret"
            try:
                with redirect_stdout(io.StringIO()) as b:
                    rc = R.main(["--url", s.url(), "--header-env", "Authorization=LD_OSR_TEST_TOKEN",
                                 "--chunk-size", "400000"])
            finally:
                del os.environ["LD_OSR_TEST_TOKEN"]
            self.assertEqual(s.httpd.seen_headers[-1].get("Authorization"), "Bearer t0ps3cret")
        self.assertEqual(rc, 0)
        self.assertNotIn("t0ps3cret", b.getvalue())
        self.assertEqual(json.loads(b.getvalue())["sha256"], self.small_sha)

    def test_cli_refusal_exit_code(self):
        with Server(self.small, "no_range") as s:
            with redirect_stdout(io.StringIO()) as b:
                rc = R.main(["--url", s.url()])
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads(b.getvalue())["failure_code"], "RANGE_NOT_HONOURED")


if __name__ == "__main__":
    unittest.main()
