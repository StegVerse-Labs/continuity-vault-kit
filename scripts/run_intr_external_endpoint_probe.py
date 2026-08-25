#!/usr/bin/env python3
"""Non-secret provider-bound InTr external endpoint probe.

This proves the transport/session boundary to an actual intended provider endpoint
without using any credential material. It is an RC-14 precursor, not credential
resolution or production trading proof.
"""
from __future__ import annotations

import hashlib
import json
import socket
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from intr_hop_receipt import FORWARD, RETURN, build_receipt, verify_chain
from run_intr_synthetic_runtime import run_direction

ROOT = Path(__file__).resolve().parents[1]
HOST = "api.coinbase.com"
PORT = 443
PATH = "/api/v3/brokerage/time"
MAX_RESPONSE = 1024 * 1024


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_uri(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def parse_status_and_headers(raw: bytes) -> tuple[int, dict[str, str], bytes]:
    head, sep, body = raw.partition(b"\r\n\r\n")
    if not sep:
        raise RuntimeError("HTTP response missing header terminator")
    lines = head.decode("iso-8859-1").split("\r\n")
    parts = lines[0].split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise RuntimeError("invalid HTTP status line")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    return int(parts[1]), headers, body


def probe_tls_https() -> dict[str, Any]:
    context = ssl.create_default_context()
    addresses = socket.getaddrinfo(HOST, PORT, type=socket.SOCK_STREAM)
    if not addresses:
        raise RuntimeError("provider DNS resolution returned no addresses")

    with socket.create_connection((HOST, PORT), timeout=10) as raw_sock:
        with context.wrap_socket(raw_sock, server_hostname=HOST) as tls_sock:
            peer_cert = tls_sock.getpeercert(binary_form=True)
            if not peer_cert:
                raise RuntimeError("provider TLS peer certificate missing")
            peer_ip = tls_sock.getpeername()[0]
            tls_version = tls_sock.version()
            cipher = tls_sock.cipher()
            if not tls_version or not cipher:
                raise RuntimeError("provider TLS session metadata missing")

            request = (
                f"GET {PATH} HTTP/1.1\r\n"
                f"Host: {HOST}\r\n"
                "User-Agent: StegVerse-InTr-RC14/1\r\n"
                "Accept: application/json\r\n"
                "Cache-Control: no-cache\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode("ascii")
            tls_sock.sendall(request)
            chunks: list[bytes] = []
            total = 0
            while total < MAX_RESPONSE:
                chunk = tls_sock.recv(min(65536, MAX_RESPONSE - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
            response = b"".join(chunks)

    status, headers, body = parse_status_and_headers(response)
    location = headers.get("location")
    if 300 <= status < 400 or location:
        raise RuntimeError("provider endpoint redirect is not permitted")
    if status < 200 or status >= 500:
        raise RuntimeError(f"provider endpoint returned unacceptable status {status}")

    binding_material = canonical_bytes({
        "host": HOST,
        "port": PORT,
        "peer_ip": peer_ip,
        "tls_version": tls_version,
        "cipher": cipher[0],
        "certificate_sha256": sha256_uri(peer_cert),
        "path": PATH,
        "status": status,
    })
    return {
        "authorized_endpoint_ref": f"https://{HOST}{PATH}",
        "resolved_host": HOST,
        "resolved_peer_ip": peer_ip,
        "scheme": "https",
        "port": PORT,
        "path": PATH,
        "tls_version": tls_version,
        "cipher": cipher[0],
        "peer_certificate_sha256": sha256_uri(peer_cert),
        "tls_session_binding_hash": sha256_uri(binding_material),
        "http_status": status,
        "response_body_sha256": sha256_uri(body),
        "response_body_bytes": len(body),
        "redirect_observed": False,
        "credential_material_sent": False,
        "authorization_header_sent": False,
        "endpoint_session_verified": True,
    }


def main() -> int:
    packet = json.loads((ROOT / "specs/intr-packet-review-candidate.v1.json").read_text(encoding="utf-8"))
    envelope = packet["envelope"]
    packet_id = envelope["packet_id"] + "-coinbase-rc14"
    operation_hash = sha256_uri(canonical_bytes({
        "operation": "NON_SECRET_EXTERNAL_ENDPOINT_PROBE",
        "provider": "coinbase",
        "endpoint": f"https://{HOST}{PATH}",
        "credential_required": False,
    }))
    sealed_payload_hash = sha256_uri(canonical_bytes({
        "provider": "coinbase",
        "probe": "server-time",
        "secret_plaintext_present": False,
        "authority_transfer": False,
    }))

    # Exercise the internal adjacent boundaries using the already-validated transport harness.
    internal_forward_edges = FORWARD[:-1]
    forward_observations, forward_receipts = run_direction(
        direction="FORWARD",
        edges=internal_forward_edges,
        packet_id=packet_id,
        operation_hash=operation_hash,
        payload_hash=sealed_payload_hash,
    )

    endpoint = probe_tls_https()
    prior = forward_receipts[-1]["receipt_hash"] if forward_receipts else None
    external_receipt = build_receipt(
        receipt_id="external-forward-coinbase-0",
        packet_id=packet_id,
        hop_index=len(internal_forward_edges),
        direction="FORWARD",
        from_role="EXTERNAL_NETWORK",
        to_role="ENDPOINT",
        operation_hash=operation_hash,
        payload_hash=sealed_payload_hash,
        prior_receipt_hash=prior,
        boundary_identity_ref=endpoint["authorized_endpoint_ref"],
        boundary_verification="VERIFIED",
        transition_state="TERMINAL",
        recorded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    forward_receipts.append(external_receipt)
    if verify_chain(forward_receipts):
        raise RuntimeError("provider-bound forward InTr receipt chain failed")

    # Return starts from the verified endpoint and traverses the remaining adjacent domains.
    return_payload_hash = endpoint["response_body_sha256"]
    return_observations, return_receipts = run_direction(
        direction="RETURN",
        edges=RETURN,
        packet_id=packet_id + "-return",
        operation_hash=operation_hash,
        payload_hash=return_payload_hash,
    )

    evidence = {
        "schema": "stegverse.intr.external_endpoint_probe_evidence/v1",
        "state": "PASS",
        "review_gate": "RC-14-EXTERNAL-RUNTIME-PRECURSOR",
        "runtime_class": "EXTERNAL_TLS_NON_SECRET_PROVIDER_PROBE",
        "provider": "coinbase",
        "production_credential_operation": False,
        "real_credential_used": False,
        "third_party_endpoint_contacted": True,
        "credential_resolution_attempted": False,
        "credential_resolution_permitted": False,
        "canonical_topology": "SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint",
        "packet_id": packet_id,
        "operation_hash": operation_hash,
        "sealed_payload_hash": sealed_payload_hash,
        "forward_observations": forward_observations + [{"from_role": "EXTERNAL_NETWORK", "to_role": "ENDPOINT", **endpoint}],
        "return_observations": return_observations,
        "forward_receipts": forward_receipts,
        "return_receipts": return_receipts,
        "endpoint_session": endpoint,
        "secret_plaintext_present": False,
        "authority_transfer": False,
        "redirect_permitted": False,
        "failure_disposition": "FAIL_CLOSED",
        "non_claims": [
            "external_endpoint_probe_is_not_real_skap_custody",
            "external_endpoint_probe_is_not_credential_admission",
            "external_endpoint_probe_is_not_trading_activation",
        ],
    }
    out = ROOT / "reports" / "skap_intr" / "external-endpoint-probe-coinbase.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("INTR_EXTERNAL_ENDPOINT_PROBE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
