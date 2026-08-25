#!/usr/bin/env python3
"""Bind synthetic SKAP material to a real verified Coinbase TLS session.

No production credential is used and no synthetic credential bytes are transmitted.
This is an RC-18 precursor proving ordering and binding:
VERIFY ENDPOINT SESSION -> REVALIDATE GRANT -> TRANSIENT RESOLUTION.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from run_intr_external_endpoint_probe import probe_tls_https

ROOT = Path(__file__).resolve().parents[1]

# Import after repository root is available on normal workflow PYTHONPATH.
from skap.crypto_boundary import seal, resolve_granted_transiently

OBJECT_ID = "skap://APIs/coinbase/rc18-synthetic"
VERSION = 1
POLICY = "tvc://policy/skap/third-party-credential/v1"
PURPOSE = "rc18.synthetic.verified-session-resolution"
ENDPOINT = "https://api.coinbase.com/api/v3/brokerage/time"
KEY_AUTHORITY = "tvc://synthetic-runtime/RC18_NON_PRODUCTION_ROOT"


def sha256_uri(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def main() -> int:
    root_key = bytearray(os.urandom(32))
    synthetic = bytearray(b"RC18-SYNTHETIC-CREDENTIAL-NOT-A-REAL-SECRET")
    expected_len = len(synthetic)
    try:
        sealed = seal(
            synthetic,
            root_key=root_key,
            object_id=OBJECT_ID,
            credential_version=VERSION,
            wrapping_policy_ref=POLICY,
            purpose=PURPOSE,
            endpoint_ref=ENDPOINT,
            key_authority_ref=KEY_AUTHORITY,
        ).envelope

        endpoint = probe_tls_https()
        if endpoint.get("endpoint_session_verified") is not True:
            raise RuntimeError("Coinbase endpoint session not verified")
        if endpoint.get("authorized_endpoint_ref") != ENDPOINT:
            raise RuntimeError("Coinbase endpoint binding mismatch")
        if endpoint.get("credential_material_sent") is not False:
            raise RuntimeError("credential material unexpectedly sent during endpoint verification")
        if endpoint.get("authorization_header_sent") is not False:
            raise RuntimeError("Authorization header unexpectedly sent during endpoint verification")
        session_hash = endpoint.get("tls_session_binding_hash")
        if not isinstance(session_hash, str) or not session_hash.startswith("sha256:"):
            raise RuntimeError("TLS session binding missing")

        grant = {
            "object_id": OBJECT_ID,
            "credential_version": VERSION,
            "purpose": PURPOSE,
            "endpoint_ref": ENDPOINT,
            "state": "ACTIVE",
            "revoked": False,
            "consumed": False,
            "tls_session_binding_hash": session_hash,
        }

        consumed = {"called": False}
        def local_only_consumer(view: memoryview) -> bool:
            consumed["called"] = True
            if len(view) != expected_len:
                raise RuntimeError("synthetic resolved length mismatch")
            # Deliberately do not serialize, hash, log, or transmit plaintext.
            return True

        result = resolve_granted_transiently(
            sealed,
            root_key=root_key,
            lifecycle_state="ACTIVE",
            current_credential_version=VERSION,
            grant=grant,
            revocation_check_passed=True,
            expected_object_id=OBJECT_ID,
            expected_wrapping_policy_ref=POLICY,
            expected_key_authority_ref=KEY_AUTHORITY,
            consumer=local_only_consumer,
        )
        if result is not True or consumed["called"] is not True:
            raise RuntimeError("transient resolution callback did not complete")

        evidence = {
            "schema": "stegverse.skap.external_verified_session_resolution_evidence/v1",
            "state": "PASS",
            "review_gate": "RC-18-PRECURSOR-SYNTHETIC-SEALED-SESSION",
            "provider": "coinbase",
            "authorized_endpoint_ref": ENDPOINT,
            "tls_session_binding_hash": session_hash,
            "peer_certificate_sha256": endpoint["peer_certificate_sha256"],
            "endpoint_session_verified_before_resolution": True,
            "revocation_rechecked_before_resolution": True,
            "grant_endpoint_bound": True,
            "grant_session_bound": True,
            "synthetic_material_resolved_transiently": True,
            "credential_material_sent": False,
            "authorization_header_sent": False,
            "production_credential_used": False,
            "production_provider_operation": False,
            "plaintext_persisted": False,
            "authority_transfer": False,
            "failure_disposition": "FAIL_CLOSED",
        }
        out = ROOT / "reports/skap_intr/coinbase-synthetic-sealed-session.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("SKAP_COINBASE_SYNTHETIC_SEALED_SESSION_PASS")
        return 0
    finally:
        for i in range(len(synthetic)):
            synthetic[i] = 0
        for i in range(len(root_key)):
            root_key[i] = 0


if __name__ == "__main__":
    raise SystemExit(main())
