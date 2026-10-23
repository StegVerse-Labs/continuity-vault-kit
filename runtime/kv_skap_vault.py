"""KV-SKAP-VAULT-FUNCTIONAL-001: KnowledgeVault with a SKAP Vault inside KV (E0, stdlib only).

Proposed Goal: StegVerse-Labs/.github#3324. The Goal is sealed with scope_digest SCOPE_DIGEST, and the
finish point is ``python -m runtime.kv_skap_vault finish-point``. That command returns ALLOW only when every
sealed expected_evidence_predicate is ALLOW over one receipt-hash lineage. Until then it returns a
six-field FAIL_CLOSED for each unmet predicate.

Authority is unchanged and is not duplicated here:

* KV/SKAP Vault is the only user verifier. This module verifies its own lineage and mints nothing.
* TV/TVC is the credential authority and the sole SKAP ciphertext custody writer. The vault holds
  custody-key *references* only. It refuses key or credential material, and it refuses any writer
  other than TV/TVC.
* Interlock/InTr is the transition authority. Every write and revoke binds an InTr transition reference.
  This module does not issue that reference, and it does not admit one.
* WorkerCoordinator holds claim and fence. This module claims nothing.

Degradation: no model, network, clock or dependency is used anywhere. The verdict is the same on every
rung of the operating-mode ladder, down to E0 (ecosystem only, no LLM). Time is taken only from
caller-supplied ``observed_at`` values.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from typing import Any

from runtime.secret_field_policy import find_forbidden_field

TASK_ID = "KV-SKAP-VAULT-FUNCTIONAL-001"
GOAL_REF = "StegVerse-Labs/.github#3324 (KV-SKAP-VAULT-FUNCTIONAL-001, PROPOSED)"
SCOPE_DIGEST = "sha256:d68e239bd1eeabe6558b52928632e9e1df35656e55b3f899755924e66b862ada"
LOWEST_SUPPORTED_MODE = "E0"
RECEIPT_SCHEMA = "stegverse.kv-skap-vault-receipt/v1"
VERDICT_SCHEMA = "stegverse.kv-skap-vault-finish-point-verdict/v1"
RETRY = "python -m runtime.kv_skap_vault finish-point (StegVerse-Labs/continuity-vault-kit)"
CREDENTIAL_AUTHORITY = "TV/TVC"
CUSTODY_REF_PREFIX = "tvc://skap-custody/"
MATERIAL_TOKENS = ("password", "secret", "token", "private_key", "key_material", "ciphertext",
                   "plaintext", "credential", "mnemonic", "seed_phrase")

#: The sealed expected_evidence_predicates, in sealed order (StegVerse-Labs/.github#3324).
PREDICATES = (
    "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
    "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY",
    "CONSENT_RECEIPT_PRECEDES_EVERY_KV_WRITE_AND_READ",
    "REVOCATION_RECEIPT_ENDS_READ_ACCESS",
    "RECEIPT_HASH_LINEAGE_CONTINUOUS_ACROSS_WRITE_READ_REVOKE",
    "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED",
    "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER",
    "NO_DUPLICATED_GOVERNANCE_CREDENTIAL_VERIFIER_OR_KV_AUTHORITY",
    "FINISH_POINT_VERDICT_REACHED_AT_E0_WITHOUT_LLM",
)

AUTHORITY_MODEL = {
    "user_verifier": "KV/SKAP Vault",
    "credential_authority": CREDENTIAL_AUTHORITY,
    "skap_ciphertext_custody_writer": CREDENTIAL_AUTHORITY,
    "transition_authority": "Interlock/InTr",
    "claim_and_fence_authority": "WorkerCoordinator",
    "mints_execution_authority": False,
    "mints_credentials": False,
    "mints_intr_admission": False,
    "mints_claim_or_fence": False,
    "holds_key_material": False,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_uri(value: Any) -> str:
    raw = value if isinstance(value, str) else canonical_json(value)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class VaultRefusal(Exception):
    """Six-field FAIL_CLOSED refusal (plus failure_class)."""

    def __init__(self, code: str, predicate: str, repair: str, *, failure_class: str = "B",
                 next_attempt: str = "on the next vault operation that carries the repair") -> None:
        super().__init__(code)
        self.fields = {
            "failure_code": code,
            "failed_predicate": predicate,
            "required_evidence_or_repair": repair,
            "retry_entrypoint": RETRY,
            "owning_existing_goal": GOAL_REF,
            "next_attempt": next_attempt,
            "failure_class": failure_class,
        }


def _refuse_material(value: Any, where: str, predicate: str) -> None:
    offending = find_forbidden_field(value, MATERIAL_TOKENS, where)
    if offending is not None:
        raise VaultRefusal("SKAP_VAULT_KEY_OR_CREDENTIAL_MATERIAL_REFUSED", predicate,
                           f"remove {offending}; the vault holds TV/TVC custody-key references only")


class KVSkapVault:
    """One principal's KV with the SKAP Vault inside it. All state is the receipt lineage itself."""

    def __init__(self, principal_ref: str) -> None:
        if not isinstance(principal_ref, str) or not principal_ref:
            raise VaultRefusal("KV_PRINCIPAL_REF_MISSING", "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
                               "name the principal reference")
        self.principal_ref = principal_ref
        self.lineage: list[dict[str, Any]] = []
        self._custody: dict[str, dict[str, Any]] = {}
        self._consents: dict[str, dict[str, Any]] = {}
        self._projections: dict[str, dict[str, Any]] = {}

    # --- lineage
    @property
    def head(self) -> str | None:
        return self.lineage[-1]["receipt_hash"] if self.lineage else None

    def _append(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "task_id": TASK_ID,
            "principal_ref": self.principal_ref,
            "sequence": len(self.lineage),
            "kind": kind,
            "previous_receipt_hash": self.head,
            "body": body,
            "authority_effect": "NONE_RECEIPT_ONLY",
        }
        receipt["receipt_hash"] = sha256_uri(receipt)
        self._apply(receipt)
        self.lineage.append(receipt)
        return copy.deepcopy(receipt)

    def _apply(self, receipt: dict[str, Any]) -> None:
        kind, body = receipt["kind"], receipt["body"]
        if kind == "CUSTODY_KEY_REFERENCE_BOUND":
            self._custody[body["custody_key_ref"]] = body
        elif kind == "CONSENT_GRANTED":
            self._consents[receipt["receipt_hash"]] = {**body, "revoked_by": None}
        elif kind == "CONSENT_REVOKED":
            self._consents[body["consent_receipt_hash"]]["revoked_by"] = receipt["receipt_hash"]
        elif kind == "KV_PROJECTION_WRITTEN":
            self._projections[body["projection_id"]] = body

    # --- SKAP Vault inside KV: custody-key references only
    def bind_custody_key_reference(self, *, custody_key_ref: str, issued_by: str,
                                   tvc_issuance_receipt_ref: str) -> dict[str, Any]:
        pred = "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY"
        if issued_by != CREDENTIAL_AUTHORITY:
            raise VaultRefusal("SKAP_CUSTODY_WRITER_NOT_TV_TVC",
                               "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER",
                               f"only {CREDENTIAL_AUTHORITY} issues SKAP custody keys; obtain the reference from TV/TVC")
        if not isinstance(custody_key_ref, str) or not custody_key_ref.startswith(CUSTODY_REF_PREFIX) \
                or len(custody_key_ref) <= len(CUSTODY_REF_PREFIX):
            raise VaultRefusal("SKAP_CUSTODY_KEY_REFERENCE_INVALID", pred,
                               f"supply a TV/TVC custody-key reference of the form {CUSTODY_REF_PREFIX}<id>")
        if not isinstance(tvc_issuance_receipt_ref, str) or not tvc_issuance_receipt_ref:
            raise VaultRefusal("TVC_CUSTODY_ISSUANCE_RECEIPT_MISSING", pred,
                               "bind the TV/TVC issuance receipt reference for this custody key")
        body = {"custody_key_ref": custody_key_ref, "issued_by": issued_by,
                "tvc_issuance_receipt_ref": tvc_issuance_receipt_ref}
        _refuse_material(body, "custody", pred)
        return self._append("CUSTODY_KEY_REFERENCE_BOUND", body)

    # --- consent and revocation
    def grant_consent(self, *, purposes: list[str], projection_ids: list[str], observed_at: str) -> dict[str, Any]:
        pred = "CONSENT_RECEIPT_PRECEDES_EVERY_KV_WRITE_AND_READ"
        allowed = {"WRITE", "READ"}
        if not purposes or not set(purposes) <= allowed or not projection_ids:
            raise VaultRefusal("KV_CONSENT_SCOPE_INVALID", pred,
                               "consent names purposes within WRITE/READ and at least one projection id")
        body = {"purposes": sorted(set(purposes)), "projection_ids": sorted(set(projection_ids)),
                "observed_at": observed_at}
        return self._append("CONSENT_GRANTED", body)

    def _consent(self, consent_receipt_hash: str, purpose: str, projection_id: str) -> dict[str, Any]:
        consent = self._consents.get(consent_receipt_hash)
        if consent is None:
            raise VaultRefusal("KV_CONSENT_RECEIPT_NOT_FOUND", "CONSENT_RECEIPT_PRECEDES_EVERY_KV_WRITE_AND_READ",
                               "grant consent first and bind its receipt hash")
        if consent["revoked_by"] is not None:
            raise VaultRefusal("KV_CONSENT_REVOKED", "REVOCATION_RECEIPT_ENDS_READ_ACCESS",
                               "a revoked consent cannot be reused; the principal grants a new consent",
                               failure_class="C", next_attempt="after a new consent receipt")
        if purpose not in consent["purposes"] or projection_id not in consent["projection_ids"]:
            raise VaultRefusal("KV_CONSENT_SCOPE_DOES_NOT_COVER_OPERATION",
                               "CONSENT_RECEIPT_PRECEDES_EVERY_KV_WRITE_AND_READ",
                               f"consent must cover {purpose} on {projection_id}")
        return consent

    def revoke_consent(self, *, consent_receipt_hash: str, intr_transition_ref: str, observed_at: str) -> dict[str, Any]:
        if consent_receipt_hash not in self._consents:
            raise VaultRefusal("KV_CONSENT_RECEIPT_NOT_FOUND", "REVOCATION_RECEIPT_ENDS_READ_ACCESS",
                               "revoke a consent receipt that exists in this lineage")
        if self._consents[consent_receipt_hash]["revoked_by"] is not None:
            raise VaultRefusal("KV_CONSENT_ALREADY_REVOKED", "REVOCATION_RECEIPT_ENDS_READ_ACCESS",
                               "nothing to repair; the consent is already revoked", failure_class="C")
        _require_intr(intr_transition_ref)
        return self._append("CONSENT_REVOKED", {"consent_receipt_hash": consent_receipt_hash,
                                                "intr_transition_ref": intr_transition_ref, "observed_at": observed_at})

    # --- KV projection write / read
    def write_projection(self, *, projection_id: str, content: Any, consent_receipt_hash: str,
                         custody_key_ref: str, intr_transition_ref: str) -> dict[str, Any]:
        self._consent(consent_receipt_hash, "WRITE", projection_id)
        if custody_key_ref not in self._custody:
            raise VaultRefusal("SKAP_CUSTODY_KEY_REFERENCE_NOT_BOUND",
                               "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY",
                               "bind the TV/TVC custody-key reference before writing")
        _require_intr(intr_transition_ref)
        _refuse_material(content, "content", "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY")
        body = {"projection_id": projection_id, "content": copy.deepcopy(content),
                "content_sha256": sha256_uri(content), "consent_receipt_hash": consent_receipt_hash,
                "custody_key_ref": custody_key_ref, "intr_transition_ref": intr_transition_ref}
        return self._append("KV_PROJECTION_WRITTEN", body)

    def read_projection(self, *, projection_id: str, consent_receipt_hash: str) -> tuple[Any, dict[str, Any]]:
        self._consent(consent_receipt_hash, "READ", projection_id)
        stored = self._projections.get(projection_id)
        if stored is None:
            raise VaultRefusal("KV_PROJECTION_NOT_FOUND", "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
                               "write the projection first", failure_class="C")
        content = copy.deepcopy(stored["content"])
        receipt = self._append("KV_PROJECTION_READ", {"projection_id": projection_id,
                                                      "content_sha256": sha256_uri(content),
                                                      "consent_receipt_hash": consent_receipt_hash})
        return content, receipt

    # --- continuity: the lineage is the whole state, so any device reconstructs it
    def export_lineage(self) -> dict[str, Any]:
        return {"schema": "stegverse.kv-skap-vault-lineage/v1", "task_id": TASK_ID,
                "principal_ref": self.principal_ref, "head": self.head,
                "receipts": copy.deepcopy(self.lineage)}

    @classmethod
    def reconstruct(cls, exported: dict[str, Any]) -> "KVSkapVault":
        verify_lineage(exported)
        vault = cls(exported["principal_ref"])
        for receipt in exported["receipts"]:
            vault._apply(receipt)
            vault.lineage.append(copy.deepcopy(receipt))
        return vault


def _require_intr(ref: str) -> None:
    if not isinstance(ref, str) or not ref.startswith("intr:"):
        raise VaultRefusal("INTR_TRANSITION_REF_MISSING", "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
                           "bind the Interlock/InTr transition reference (intr:<id>) for this mutation")


def verify_lineage(exported: dict[str, Any]) -> None:
    pred = "RECEIPT_HASH_LINEAGE_CONTINUOUS_ACROSS_WRITE_READ_REVOKE"
    previous = None
    for index, receipt in enumerate(exported.get("receipts") or []):
        body = {k: v for k, v in receipt.items() if k != "receipt_hash"}
        if receipt.get("sequence") != index or receipt.get("previous_receipt_hash") != previous \
                or receipt.get("principal_ref") != exported.get("principal_ref") \
                or sha256_uri(body) != receipt.get("receipt_hash"):
            raise VaultRefusal("KV_RECEIPT_LINEAGE_BROKEN", pred,
                               f"receipt {index} does not chain; reconstruct only from an untampered lineage",
                               failure_class="C")
        previous = receipt["receipt_hash"]
    if exported.get("head") != previous:
        raise VaultRefusal("KV_RECEIPT_LINEAGE_BROKEN", pred, "exported head does not equal the last receipt hash",
                           failure_class="C")


# --- finish point -------------------------------------------------------------------------------
#: Pieces not yet built. Each is reported as an honest six-field FAIL_CLOSED, never as a skip.
NOT_YET_BUILT = {
    "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT": (
        "INTR_TRANSITION_RECEIPTS_NOT_OBSERVED", "B",
        "the local round-trip is exact, but each write and revoke must bind a real Interlock/InTr "
        "transition receipt; bind the InTr adapter (STEGOS-DEVICE-KV-SKAP-ROUNDTRIP-001 lane) and verify "
        "its receipts here"),
    "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED": (
        "KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND", "C",
        "reconstruction from the lineage alone is exact on a fresh instance; bind the durable KV custody "
        "location the lineage is read from on any device (custody path settled on StegVerse-org/.github#163)"),
    "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER": (
        "TVC_CUSTODY_KEY_ISSUANCE_NOT_OBSERVED", "B",
        "the vault refuses every non-TV/TVC writer and all key material; a real TV/TVC custody-key issuance "
        "receipt must be observed and bound (a TV/TVC transition, not a blocker)"),
}


def _exercise() -> dict[str, bool]:
    """Run the full local round-trip and the negative cases. Returns predicate -> locally satisfied."""
    ok: dict[str, bool] = {}
    vault = KVSkapVault("principal:fixture")
    ref = CUSTODY_REF_PREFIX + "fixture-0001"
    vault.bind_custody_key_reference(custody_key_ref=ref, issued_by=CREDENTIAL_AUTHORITY,
                                     tvc_issuance_receipt_ref="fixture:tvc-issuance-unobserved")
    consent = vault.grant_consent(purposes=["WRITE", "READ"], projection_ids=["notes/profile"],
                                  observed_at="fixture")["receipt_hash"]
    content = {"title": "profile", "fields": {"display_name": "Fixture", "languages": ["en", "es"]}}
    vault.write_projection(projection_id="notes/profile", content=content, consent_receipt_hash=consent,
                           custody_key_ref=ref, intr_transition_ref="intr:fixture-write")
    read, _ = vault.read_projection(projection_id="notes/profile", consent_receipt_hash=consent)
    vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="intr:fixture-revoke", observed_at="fixture")
    try:
        vault.read_projection(projection_id="notes/profile", consent_receipt_hash=consent)
        revoked_blocks = False
    except VaultRefusal as exc:
        revoked_blocks = exc.fields["failure_code"] == "KV_CONSENT_REVOKED"
    ok["KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT"] = read == content and revoked_blocks

    def refused(fn, code: str) -> bool:
        try:
            fn()
        except VaultRefusal as exc:
            return exc.fields["failure_code"] == code
        return False

    other = KVSkapVault("principal:fixture")
    live = KVSkapVault("principal:fixture")
    live.bind_custody_key_reference(custody_key_ref=ref, issued_by=CREDENTIAL_AUTHORITY,
                                    tvc_issuance_receipt_ref="fixture:tvc-issuance-unobserved")
    live_consent = live.grant_consent(purposes=["WRITE"], projection_ids=["p"], observed_at="fixture")["receipt_hash"]
    ok["SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY"] = all([
        refused(lambda: other.bind_custody_key_reference(custody_key_ref="raw-bytes", issued_by=CREDENTIAL_AUTHORITY,
                                                         tvc_issuance_receipt_ref="x"), "SKAP_CUSTODY_KEY_REFERENCE_INVALID"),
        refused(lambda: live.write_projection(projection_id="p", content={"private_key": "x"},
                                              consent_receipt_hash=live_consent, custody_key_ref=ref,
                                              intr_transition_ref="intr:x"), "SKAP_VAULT_KEY_OR_CREDENTIAL_MATERIAL_REFUSED"),
        refused(lambda: _refuse_material({"key_material": "x"}, "c", "P"), "SKAP_VAULT_KEY_OR_CREDENTIAL_MATERIAL_REFUSED"),
    ])
    ok["CONSENT_RECEIPT_PRECEDES_EVERY_KV_WRITE_AND_READ"] = all([
        refused(lambda: other.write_projection(projection_id="p", content={}, consent_receipt_hash="sha256:none",
                                               custody_key_ref=ref, intr_transition_ref="intr:x"), "KV_CONSENT_RECEIPT_NOT_FOUND"),
        refused(lambda: other.read_projection(projection_id="p", consent_receipt_hash="sha256:none"), "KV_CONSENT_RECEIPT_NOT_FOUND"),
        [r["kind"] for r in vault.lineage].index("CONSENT_GRANTED") < [r["kind"] for r in vault.lineage].index("KV_PROJECTION_WRITTEN"),
    ])
    ok["REVOCATION_RECEIPT_ENDS_READ_ACCESS"] = revoked_blocks and vault.lineage[-1]["kind"] == "CONSENT_REVOKED"
    exported = vault.export_lineage()
    tampered = copy.deepcopy(exported)
    tampered["receipts"][2]["body"]["content"]["title"] = "changed"
    try:
        verify_lineage(exported)
        intact = True
    except VaultRefusal:
        intact = False
    ok["RECEIPT_HASH_LINEAGE_CONTINUOUS_ACROSS_WRITE_READ_REVOKE"] = intact and refused(
        lambda: verify_lineage(tampered), "KV_RECEIPT_LINEAGE_BROKEN")
    fresh = KVSkapVault.reconstruct(json.loads(canonical_json(exported)))
    ok["ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED"] = (
        fresh.head == vault.head and fresh._projections == vault._projections and fresh._consents == vault._consents)
    ok["TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER"] = refused(
        lambda: other.bind_custody_key_reference(custody_key_ref=ref, issued_by="KV",
                                                 tvc_issuance_receipt_ref="x"), "SKAP_CUSTODY_WRITER_NOT_TV_TVC")
    ok["NO_DUPLICATED_GOVERNANCE_CREDENTIAL_VERIFIER_OR_KV_AUTHORITY"] = (
        not any(v for k, v in AUTHORITY_MODEL.items() if k.startswith(("mints_", "holds_")))
        and AUTHORITY_MODEL["credential_authority"] == CREDENTIAL_AUTHORITY
        and all(r["authority_effect"] == "NONE_RECEIPT_ONLY" for r in vault.lineage))
    ok["FINISH_POINT_VERDICT_REACHED_AT_E0_WITHOUT_LLM"] = True  # this function ran: stdlib only, no model
    return ok


def finish_point() -> dict[str, Any]:
    local = _exercise()
    results = []
    for predicate in PREDICATES:
        if not local.get(predicate):
            code, klass, repair = ("FINISH_POINT_PREDICATE_NOT_LOCALLY_SATISFIED", "A",
                                   f"repair runtime/kv_skap_vault.py so {predicate} holds locally")
        elif predicate in NOT_YET_BUILT:
            code, klass, repair = NOT_YET_BUILT[predicate]
        else:
            results.append({"predicate": predicate, "disposition": "ALLOW"})
            continue
        results.append({"predicate": predicate, "disposition": "FAIL_CLOSED", "failure_code": code,
                        "failed_predicate": predicate, "required_evidence_or_repair": repair,
                        "retry_entrypoint": RETRY, "owning_existing_goal": GOAL_REF,
                        "next_attempt": "on the next finish-point run after the repair is bound",
                        "failure_class": klass})
    unmet = [r for r in results if r["disposition"] != "ALLOW"]
    return {"schema": VERDICT_SCHEMA, "task_id": TASK_ID, "scope_digest": SCOPE_DIGEST,
            "lowest_supported_mode": LOWEST_SUPPORTED_MODE, "mode": LOWEST_SUPPORTED_MODE,
            "disposition": "FAIL_CLOSED" if unmet else "ALLOW",
            "unmet_predicates": [r["predicate"] for r in unmet], "predicates": results,
            "authority_model": AUTHORITY_MODEL, "llm_used": False, "network_used": False, "clock_read": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m runtime.kv_skap_vault")
    parser.add_argument("command", choices=["finish-point"])
    parser.parse_args(argv)
    verdict = finish_point()
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["disposition"] == "ALLOW" else 2


if __name__ == "__main__":
    sys.exit(main())
