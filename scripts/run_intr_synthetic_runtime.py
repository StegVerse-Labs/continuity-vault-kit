#!/usr/bin/env python3
"""Non-secret synthetic InTr runtime traversal.

This harness uses real TCP socket I/O on loopback to exercise every canonical adjacent
boundary in both directions. It does not contact a third-party provider, carry a real
credential, or establish production runtime proof. Its purpose is to prove that the
same sealed packet/receipt discipline can survive actual transport I/O before any
real SKAP credential is admitted.
"""
from __future__ import annotations

import hashlib
import json
import socket
import threading
from pathlib import Path
from typing import Any

from intr_hop_receipt import FORWARD, RETURN, build_receipt, verify_chain

ROOT = Path(__file__).resolve().parents[1]
MAX_FRAME = 1024 * 1024


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_uri(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def send_frame(sock: socket.socket, value: dict[str, Any]) -> None:
    body = canonical_bytes(value)
    sock.sendall(len(body).to_bytes(4, "big") + body)


def recv_exact(sock: socket.socket, length: int) -> bytes:
    chunks = []
    remaining = length
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("unexpected EOF")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_frame(sock: socket.socket) -> tuple[dict[str, Any], bytes]:
    length = int.from_bytes(recv_exact(sock, 4), "big")
    if length <= 0 or length > MAX_FRAME:
        raise RuntimeError("invalid InTr frame length")
    body = recv_exact(sock, length)
    return json.loads(body), body


def transport_hop(*, from_role: str, to_role: str, payload: dict[str, Any]) -> dict[str, Any]:
    ready = threading.Event()
    result: dict[str, Any] = {}
    failure: list[BaseException] = []
    port_box: list[int] = []

    def server() -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                port_box.append(listener.getsockname()[1])
                ready.set()
                conn, peer = listener.accept()
                with conn:
                    value, wire = recv_frame(conn)
                    if value.get("from_role") != from_role or value.get("to_role") != to_role:
                        raise RuntimeError("InTr boundary role mismatch")
                    if value.get("protected_payload_sealed") is not True:
                        raise RuntimeError("InTr runtime requires sealed protected payload")
                    if value.get("secret_plaintext_present") is not False:
                        raise RuntimeError("secret plaintext detected in InTr runtime frame")
                    if value.get("authority_transfer") is not False:
                        raise RuntimeError("authority transfer detected in InTr runtime frame")
                    result.update({
                        "from_role": from_role,
                        "to_role": to_role,
                        "peer": peer[0],
                        "wire_sha256": sha256_uri(wire),
                        "wire_bytes": len(wire),
                        "boundary_verification": "VERIFIED",
                    })
                    send_frame(conn, {"state": "VERIFIED", "wire_sha256": result["wire_sha256"]})
        except BaseException as exc:
            failure.append(exc)
            ready.set()

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    if not ready.wait(5):
        raise RuntimeError("synthetic InTr boundary did not start")
    if failure:
        raise failure[0]
    with socket.create_connection(("127.0.0.1", port_box[0]), timeout=5) as client:
        send_frame(client, payload)
        ack, _ = recv_frame(client)
    thread.join(timeout=5)
    if thread.is_alive():
        raise RuntimeError("synthetic InTr boundary did not terminate")
    if failure:
        raise failure[0]
    if ack.get("state") != "VERIFIED" or ack.get("wire_sha256") != result.get("wire_sha256"):
        raise RuntimeError("synthetic InTr boundary acknowledgement mismatch")
    return result


def run_direction(*, direction: str, edges: list[tuple[str, str]], packet_id: str,
                  operation_hash: str, payload_hash: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    observations = []
    receipts = []
    prior = None
    for index, (from_role, to_role) in enumerate(edges):
        frame = {
            "schema": "stegverse.intr.synthetic_runtime_frame/v1",
            "packet_id": packet_id,
            "direction": direction,
            "hop_index": index,
            "from_role": from_role,
            "to_role": to_role,
            "operation_hash": operation_hash,
            "payload_hash": payload_hash,
            "protected_payload_sealed": True,
            "secret_plaintext_present": False,
            "authority_transfer": False,
        }
        observation = transport_hop(from_role=from_role, to_role=to_role, payload=frame)
        observations.append(observation)
        receipt = build_receipt(
            receipt_id=f"synthetic-{direction.lower()}-{index}",
            packet_id=packet_id,
            hop_index=index,
            direction=direction,
            from_role=from_role,
            to_role=to_role,
            operation_hash=operation_hash,
            payload_hash=payload_hash,
            prior_receipt_hash=prior,
            boundary_identity_ref=f"synthetic-runtime://{to_role.lower()}",
            boundary_verification="VERIFIED",
            transition_state="TERMINAL" if index == len(edges) - 1 else "FORWARDED",
            recorded_at=f"2026-08-24T21:{index:02d}:00Z" if direction == "FORWARD" else f"2026-08-24T21:{index+10:02d}:00Z",
        )
        receipts.append(receipt)
        prior = receipt["receipt_hash"]
    errors = verify_chain(receipts)
    if errors:
        raise RuntimeError("synthetic InTr receipt chain failed: " + "; ".join(errors))
    return observations, receipts


def main() -> int:
    packet = json.loads((ROOT / "specs/intr-packet-review-candidate.v1.json").read_text(encoding="utf-8"))
    envelope = packet["envelope"]
    operation_hash = envelope["operation_hash"]
    forward_observations, forward_receipts = run_direction(
        direction="FORWARD",
        edges=FORWARD,
        packet_id=envelope["packet_id"],
        operation_hash=operation_hash,
        payload_hash=envelope["payload_hash"],
    )
    return_observations, return_receipts = run_direction(
        direction="RETURN",
        edges=RETURN,
        packet_id=envelope["packet_id"] + "-return",
        operation_hash=operation_hash,
        payload_hash="sha256:" + "e" * 64,
    )
    evidence = {
        "schema": "stegverse.intr.synthetic_runtime_evidence/v1",
        "state": "PASS",
        "runtime_class": "LOOPBACK_TCP_SYNTHETIC_NON_SECRET",
        "production_runtime_proof": False,
        "third_party_endpoint_contacted": False,
        "real_credential_used": False,
        "canonical_topology": "SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint",
        "forward_observations": forward_observations,
        "return_observations": return_observations,
        "forward_receipts": forward_receipts,
        "return_receipts": return_receipts,
        "secret_plaintext_present": False,
        "authority_transfer": False,
    }
    out = ROOT / "reports" / "skap_intr" / "synthetic-runtime-evidence.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("INTR_SYNTHETIC_RUNTIME_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
