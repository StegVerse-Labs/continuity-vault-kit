#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

FORWARD = [("SKAP","KV"),("KV","DEVICE"),("DEVICE","EXTERNAL_NETWORK"),("EXTERNAL_NETWORK","ENDPOINT")]
RETURN = [(b,a) for a,b in reversed(FORWARD)]
FORMAT = "stegverse.intr.hop_receipt/v1"


def canonical_bytes(v: Any) -> bytes:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_uri(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def build_receipt(*, receipt_id: str, packet_id: str, hop_index: int, direction: str,
                  from_role: str, to_role: str, operation_hash: str, payload_hash: str,
                  prior_receipt_hash: str | None, boundary_identity_ref: str,
                  boundary_verification: str, transition_state: str, recorded_at: str) -> dict[str, Any]:
    value = {
        "schema": FORMAT,
        "receipt_id": receipt_id,
        "packet_id": packet_id,
        "hop_index": hop_index,
        "direction": direction,
        "from_role": from_role,
        "to_role": to_role,
        "operation_hash": operation_hash,
        "payload_hash": payload_hash,
        "prior_receipt_hash": prior_receipt_hash,
        "boundary_identity_ref": boundary_identity_ref,
        "boundary_verification": boundary_verification,
        "transition_state": transition_state,
        "secret_plaintext_present": False,
        "authority_transfer": False,
        "recorded_at": recorded_at,
    }
    value["receipt_hash"] = sha256_uri(canonical_bytes(value))
    return value


def verify_receipt(r: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if r.get("schema") != FORMAT:
        errors.append("unsupported receipt schema")
    direction = r.get("direction")
    edges = FORWARD if direction == "FORWARD" else RETURN if direction == "RETURN" else []
    idx = r.get("hop_index")
    if not isinstance(idx, int) or idx < 0 or idx >= len(edges):
        errors.append("hop_index outside canonical InTr path")
    elif (r.get("from_role"), r.get("to_role")) != edges[idx]:
        errors.append("receipt roles do not match canonical InTr hop")
    if r.get("boundary_verification") != "VERIFIED" and r.get("transition_state") not in {"REJECTED","INDETERMINATE"}:
        errors.append("unverified boundary cannot produce successful transition state")
    if r.get("secret_plaintext_present") is not False:
        errors.append("receipt must not contain secret plaintext")
    if r.get("authority_transfer") is not False:
        errors.append("receipt must not record authority transfer")
    claimed = r.get("receipt_hash")
    body = dict(r); body.pop("receipt_hash", None)
    actual = sha256_uri(canonical_bytes(body))
    if claimed != actual:
        errors.append("receipt hash mismatch")
    return errors


def verify_chain(receipts: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not receipts:
        return ["receipt chain is empty"]
    packet_id = receipts[0].get("packet_id")
    operation_hash = receipts[0].get("operation_hash")
    payload_hash = receipts[0].get("payload_hash")
    for i, r in enumerate(receipts):
        errors.extend(f"receipt[{i}]: {e}" for e in verify_receipt(r))
        if r.get("packet_id") != packet_id: errors.append(f"receipt[{i}]: packet_id chain mismatch")
        if r.get("operation_hash") != operation_hash: errors.append(f"receipt[{i}]: operation_hash chain mismatch")
        if r.get("payload_hash") != payload_hash: errors.append(f"receipt[{i}]: payload_hash chain mismatch")
        if r.get("hop_index") != i: errors.append(f"receipt[{i}]: hop_index must be contiguous")
        expected_prior = None if i == 0 else receipts[i-1].get("receipt_hash")
        if r.get("prior_receipt_hash") != expected_prior:
            errors.append(f"receipt[{i}]: prior_receipt_hash chain mismatch")
    return errors


def main() -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("verify"); v.add_argument("receipt",type=Path)
    c=sub.add_parser("verify-chain"); c.add_argument("chain",type=Path)
    args=p.parse_args()
    if args.cmd=="verify":
        r=json.loads(args.receipt.read_text(encoding="utf-8")); errors=verify_receipt(r)
    else:
        rs=json.loads(args.chain.read_text(encoding="utf-8")); errors=verify_chain(rs)
    print(json.dumps({"decision":"ALLOW" if not errors else "BLOCK","errors":errors},indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__": raise SystemExit(main())
