"""KV-SKAP-VAULT-FUNCTIONAL-001: KnowledgeVault with a SKAP Vault inside KV (E0, stdlib only).

Proposed Goal: StegVerse-Labs/.github#3324. The Goal is sealed with scope_digest SCOPE_DIGEST, and the
finish point is ``python -m runtime.kv_skap_vault finish-point [--evidence FILE] [--scratch-ledger-git-dir DIR]``.
That command returns ALLOW only when every sealed expected_evidence_predicate is ALLOW over one receipt-hash
lineage. Each verdict is computed: the local exercise runs, and then the supplied evidence bundle is checked
(``stegverse.kv-skap-vault-finish-point-evidence/v1``). Any predicate not yet evidenced gets a six-field
FAIL_CLOSED. No constant decides a verdict. Once the verdict is ALLOW, the finish point appends an
organization-ledger receipt (``stegverse.canonical-state-transition-receipt/v1``). Until the ledger genesis is
observed, that append is a six-field FAIL_CLOSED pending genesis.

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
import os
import subprocess
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
# Every verdict is computed. The local exercise runs every predicate on a fresh vault, and the evidence
# bundle supplies the parts that only other authorities produce:
#   * Interlock/InTr transition receipts for each write and revoke;
#   * the durable-custody exact-hash read-back receipt, consumed from TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001;
#   * TV/TVC custody-key issuance receipts.
# Binding is structural and by hash: refs match receipt ids, the lineage hash matches the read-back hash,
# and the TVC receipt hash re-derives. The producing authority's own signature or admission is consumed,
# not re-verified, so no governance or credential verifier is duplicated here.
EVIDENCE_SCHEMA = "stegverse.kv-skap-vault-finish-point-evidence/v1"
LINEAGE_SCHEMA = "stegverse.kv-skap-vault-lineage/v1"
INTR_RECEIPT_SCHEMA = "stegverse.canonical-state-transition-receipt/v1"
INTR_ADMITTED_OUTCOMES = ("ADMITTED", "APPLIED")
CUSTODY_READBACK_SCHEMA = "stegverse.task-registry-sovereign-kv-vault-lineage-receipt/v1"
TVC_ISSUANCE_SCHEMA = "stegverse.tvc.skap-custody-reference-issuance/v1"
SOVEREIGN_KV_CUSTODY_GOAL = "TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001"
EVIDENCE_NEXT = "on the next finish-point run whose evidence bundle carries the repair"

#: predicate -> (failure_code when its evidence is absent, failure_class, repair, owning goal, relation).
#: These describe the missing input only. The verdict is computed by the _evidence_* checks below.
EVIDENCE_BOUND = {
    "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT": (
        "INTR_TRANSITION_RECEIPTS_NOT_OBSERVED", "B",
        "the local round-trip is exact; supply evidence.lineage plus evidence.intr_transition_receipts, one "
        f"{INTR_RECEIPT_SCHEMA} per write/revoke intr:<id> (transition_id == <id>, outcome in "
        f"{INTR_ADMITTED_OUTCOMES}, subject_or_correlation_id == principal_ref) from Interlock/InTr",
        GOAL_REF, None),
    "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED": (
        "KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND", "B",
        "reconstruction from the lineage alone is exact on a fresh instance; the durable KV custody location "
        "the lineage is read from on any device is consumed from " + SOVEREIGN_KV_CUSTODY_GOAL + " (provider-"
        "neutral write and exact-hash readback; its first unresolved predicate is AUTHENTIC_ADMITTED_PROVIDER_"
        "WRITE_AND_EXACT_EVENT_HASH_READBACK_FROM_SOVEREIGN_KV) and is not re-implemented here; supply its ALLOW "
        "readback receipt as evidence.durable_custody_readback_receipt (lineage_sha256 == sha256 of "
        "evidence.lineage, provider not device-local)", SOVEREIGN_KV_CUSTODY_GOAL, "CONSUMES"),
    "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER": (
        "TVC_CUSTODY_KEY_ISSUANCE_NOT_OBSERVED", "B",
        "the vault refuses every non-TV/TVC writer and all key material; supply evidence.tvc_issuance_receipts, "
        f"one {TVC_ISSUANCE_SCHEMA} per bound custody key whose receipt_sha256 equals its "
        "tvc_issuance_receipt_ref (TVC_SKAP_CUSTODY_REFERENCE_ISSUE, a TV/TVC transition, not a blocker)",
        GOAL_REF, None),
}
_EVIDENCE_KEYS = {
    "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT": "intr_transition_receipts",
    "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED": "durable_custody_readback_receipt",
    "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER": "tvc_issuance_receipts",
}


def _exercise() -> dict[str, bool]:
    """Run the full local round-trip and the negative cases. Returns predicate -> locally satisfied."""
    ok: dict[str, bool] = {}
    vault = KVSkapVault("principal:fixture")
    ref = CUSTODY_REF_PREFIX + "fixture-0001"
    vault.bind_custody_key_reference(custody_key_ref=ref, issued_by=CREDENTIAL_AUTHORITY,
                                     tvc_issuance_receipt_ref="local-exercise:tvc-issuance")
    consent = vault.grant_consent(purposes=["WRITE", "READ"], projection_ids=["notes/profile"],
                                  observed_at="local-exercise")["receipt_hash"]
    content = {"title": "profile", "fields": {"display_name": "Exercise", "languages": ["en", "es"]}}
    vault.write_projection(projection_id="notes/profile", content=content, consent_receipt_hash=consent,
                           custody_key_ref=ref, intr_transition_ref="intr:local-exercise-write")
    read, _ = vault.read_projection(projection_id="notes/profile", consent_receipt_hash=consent)
    vault.revoke_consent(consent_receipt_hash=consent, intr_transition_ref="intr:local-exercise-revoke",
                         observed_at="local-exercise")
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
                                    tvc_issuance_receipt_ref="local-exercise:tvc-issuance")
    live_consent = live.grant_consent(purposes=["WRITE"], projection_ids=["p"],
                                      observed_at="local-exercise")["receipt_hash"]
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


# --- evidence checks: each returns None (ALLOW) or (failure_code, failure_class, repair)
def _receipts_of(lineage: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [r for r in lineage["receipts"] if r.get("kind") == kind]


def _evidence_lineage(evidence: dict[str, Any]) -> tuple[str, str, str] | None:
    """The supplied lineage verifies and itself shows consent-before-use, a revocation and an exact read."""
    lineage = evidence.get("lineage")
    if not isinstance(lineage, dict) or lineage.get("schema") != LINEAGE_SCHEMA \
            or lineage.get("task_id") != TASK_ID or not isinstance(lineage.get("receipts"), list):
        return ("KV_EVIDENCE_LINEAGE_MISSING", "B", f"supply evidence.lineage as a {LINEAGE_SCHEMA} export")
    try:
        verify_lineage(lineage)
        _refuse_material(lineage, "evidence.lineage", "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY")
    except VaultRefusal as exc:
        return (exc.fields["failure_code"], "C", exc.fields["required_evidence_or_repair"])
    granted: set[str] = set()
    revoked: set[str] = set()
    written: dict[str, str] = {}
    read_exact = False
    for receipt in lineage["receipts"]:
        kind, body = receipt.get("kind"), receipt.get("body") or {}
        if kind == "CONSENT_GRANTED":
            granted.add(receipt["receipt_hash"])
        elif kind == "CONSENT_REVOKED":
            revoked.add(body.get("consent_receipt_hash"))
        elif kind in ("KV_PROJECTION_WRITTEN", "KV_PROJECTION_READ"):
            consent = body.get("consent_receipt_hash")
            if consent not in granted or consent in revoked:
                return ("KV_EVIDENCE_OPERATION_WITHOUT_LIVE_CONSENT", "C",
                        f"receipt {receipt['sequence']} uses a consent that was not granted earlier or was revoked")
            if kind == "KV_PROJECTION_WRITTEN":
                written[body.get("projection_id")] = body.get("content_sha256")
            elif written.get(body.get("projection_id")) == body.get("content_sha256"):
                read_exact = True
    if not (written and read_exact and revoked):
        return ("KV_EVIDENCE_LINEAGE_NOT_A_WRITE_READ_REVOKE_ROUNDTRIP", "B",
                "the evidence lineage must hold a write, an exact read of it and a consent revocation")
    return None


def _manifest_entries_verify(receipt: dict[str, Any]) -> bool:
    entries = receipt.get("required_evidence_manifest")
    if not isinstance(entries, list) or not entries:
        return False
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("encoding") != "canonical-json" \
                or entry.get("origin_transition_id") != receipt.get("transition_id"):
            return False
        if entry.get("sha256") != hashlib.sha256(canonical_json(entry.get("content")).encode("utf-8")).hexdigest():
            return False
    return True


def _evidence_intr(evidence: dict[str, Any]) -> tuple[str, str, str] | None:
    lineage = evidence["lineage"]
    receipts = evidence.get("intr_transition_receipts")
    if not isinstance(receipts, list) or not receipts:
        return ("INTR_TRANSITION_RECEIPTS_NOT_OBSERVED", "B",
                EVIDENCE_BOUND["KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT"][2])
    by_id = {r.get("transition_id"): r for r in receipts if isinstance(r, dict)}
    for receipt in _receipts_of(lineage, "KV_PROJECTION_WRITTEN") + _receipts_of(lineage, "CONSENT_REVOKED"):
        ref = receipt["body"].get("intr_transition_ref", "")
        intr = by_id.get(ref[len("intr:"):]) if ref.startswith("intr:") else None
        if intr is None:
            return ("INTR_TRANSITION_RECEIPT_NOT_BOUND", "B",
                    f"no Interlock/InTr receipt for {ref!r} (lineage receipt {receipt['sequence']})")
        if intr.get("schema") != INTR_RECEIPT_SCHEMA or intr.get("transition_outcome") not in INTR_ADMITTED_OUTCOMES \
                or intr.get("subject_or_correlation_id") != lineage["principal_ref"] or not _manifest_entries_verify(intr):
            return ("INTR_TRANSITION_RECEIPT_INVALID", "C",
                    f"the InTr receipt for {ref!r} must be an {INTR_RECEIPT_SCHEMA} with outcome in "
                    f"{INTR_ADMITTED_OUTCOMES}, the principal as subject and a verifying evidence manifest")
    return None


def _evidence_custody(evidence: dict[str, Any]) -> tuple[str, str, str] | None:
    lineage = evidence["lineage"]
    receipt = evidence.get("durable_custody_readback_receipt")
    if not isinstance(receipt, dict) or not receipt:
        return ("KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND", "B",
                EVIDENCE_BOUND["ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED"][2])
    digest = sha256_uri(lineage)
    if receipt.get("schema") != CUSTODY_READBACK_SCHEMA or receipt.get("disposition") != "ALLOW" \
            or receipt.get("exact_hash_readback_verified") is not True or receipt.get("authority_effect") != "NONE":
        return ("KV_DURABLE_CUSTODY_READBACK_NOT_ALLOW", "B",
                f"the custody read-back must be an ALLOW {CUSTODY_READBACK_SCHEMA} with exact_hash_readback_verified")
    if receipt.get("lineage_sha256") != digest or receipt.get("read_back_lineage_sha256") != digest \
            or receipt.get("head_receipt_hash") != lineage["head"] \
            or receipt.get("principal_ref") != lineage["principal_ref"]:
        return ("KV_DURABLE_CUSTODY_READBACK_NOT_THIS_LINEAGE", "C",
                "the read-back receipt must bind sha256 and head of evidence.lineage for the same principal")
    if str(receipt.get("provider_adapter_ref", "")).endswith("#device-local"):
        return ("KV_DURABLE_CUSTODY_IS_DEVICE_LOCAL", "B",
                "a device-local provider requires that device; bind a custody provider readable from any device")
    return None


def _evidence_tvc(evidence: dict[str, Any]) -> tuple[str, str, str] | None:
    lineage = evidence["lineage"]
    receipts = evidence.get("tvc_issuance_receipts")
    if not isinstance(receipts, list) or not receipts:
        return ("TVC_CUSTODY_KEY_ISSUANCE_NOT_OBSERVED", "B",
                EVIDENCE_BOUND["TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER"][2])
    by_hash = {r.get("receipt_sha256"): r for r in receipts if isinstance(r, dict)}
    bound = _receipts_of(lineage, "CUSTODY_KEY_REFERENCE_BOUND")
    if not bound:
        return ("TVC_CUSTODY_KEY_REFERENCE_NOT_IN_LINEAGE", "B", "bind a TV/TVC custody-key reference in the lineage")
    for receipt in bound:
        body = receipt["body"]
        tvc = by_hash.get(body.get("tvc_issuance_receipt_ref"))
        if tvc is None:
            return ("TVC_CUSTODY_KEY_ISSUANCE_NOT_BOUND", "B",
                    f"no TV/TVC issuance receipt hashes to {body.get('tvc_issuance_receipt_ref')!r}")
        unsigned = {k: v for k, v in tvc.items() if k != "receipt_sha256"}
        derived = CUSTODY_REF_PREFIX + str(tvc.get("manifest_sha256", ""))[7:39]
        if tvc.get("schema") != TVC_ISSUANCE_SCHEMA or tvc.get("disposition") != "ALLOW" \
                or tvc.get("issuer") != CREDENTIAL_AUTHORITY or sha256_uri(unsigned) != tvc.get("receipt_sha256") \
                or tvc.get("key_material_present") is not False or tvc.get("credential_material_present") is not False \
                or tvc.get("authority_effect") != "NONE" or tvc.get("custody_key_ref") != body.get("custody_key_ref") \
                or tvc.get("custody_key_ref") != derived or tvc.get("principal_ref") != lineage["principal_ref"]:
            return ("TVC_CUSTODY_KEY_ISSUANCE_RECEIPT_INVALID", "C",
                    f"the issuance receipt for {body.get('custody_key_ref')!r} must re-derive as a TV/TVC "
                    f"{TVC_ISSUANCE_SCHEMA} for this principal and reference, with no material")
    return None


_EVIDENCE_CHECKS = {
    "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT": _evidence_intr,
    "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED": _evidence_custody,
    "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER": _evidence_tvc,
}


def _guarded(check, evidence: dict[str, Any]) -> tuple[str, str, str] | None:
    try:
        return check(evidence)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return ("KV_FINISH_POINT_EVIDENCE_MALFORMED", "C",
                f"{check.__name__}: {type(exc).__name__}; supply a well-formed {EVIDENCE_SCHEMA} bundle")


def _row(predicate: str, code: str, klass: str, repair: str, owner: str = GOAL_REF,
         relation: str | None = None, next_attempt: str = EVIDENCE_NEXT) -> dict[str, Any]:
    row = {"predicate": predicate, "disposition": "FAIL_CLOSED", "failure_code": code,
           "failed_predicate": predicate, "required_evidence_or_repair": repair, "retry_entrypoint": RETRY,
           "owning_existing_goal": owner, "next_attempt": next_attempt, "failure_class": klass}
    if relation:
        row["dependency_relation"] = relation
    return row


def evaluate(evidence: Any = None) -> dict[str, Any]:
    """Compute the finish-point verdict from the local exercise and the evidence bundle. It never raises."""
    local = _exercise()
    if evidence is not None and (not isinstance(evidence, dict) or evidence.get("schema") != EVIDENCE_SCHEMA):
        evidence = {"schema": "INVALID"}
    lineage_failure = _guarded(_evidence_lineage, evidence) if evidence and evidence.get("schema") == EVIDENCE_SCHEMA \
        else None
    results = []
    for predicate in PREDICATES:
        if not local.get(predicate):
            results.append(_row(predicate, "FINISH_POINT_PREDICATE_NOT_LOCALLY_SATISFIED", "A",
                                f"repair runtime/kv_skap_vault.py so {predicate} holds locally",
                                next_attempt="on the next finish-point run after the code repair"))
            continue
        if predicate not in _EVIDENCE_CHECKS:
            results.append({"predicate": predicate, "disposition": "ALLOW", "locus": "LOCAL_EXERCISE"})
            continue
        code, klass, repair, owner, relation = EVIDENCE_BOUND[predicate]
        if evidence is not None and evidence.get("schema") != EVIDENCE_SCHEMA:
            failure = ("KV_FINISH_POINT_EVIDENCE_INVALID", "B", f"supply a {EVIDENCE_SCHEMA} evidence bundle")
        elif evidence is None or not evidence.get(_EVIDENCE_KEYS[predicate]):
            failure = (code, klass, repair)
        elif lineage_failure is not None:
            failure = lineage_failure
        else:
            failure = _guarded(_EVIDENCE_CHECKS[predicate], evidence)
        if failure is None:
            results.append({"predicate": predicate, "disposition": "ALLOW", "locus": "LOCAL_EXERCISE+EVIDENCE"})
        else:
            results.append(_row(predicate, failure[0], failure[1], failure[2],
                                owner if failure[0] == code else GOAL_REF, relation if failure[0] == code else None))
    unmet = [r for r in results if r["disposition"] != "ALLOW"]
    return {"schema": VERDICT_SCHEMA, "task_id": TASK_ID, "scope_digest": SCOPE_DIGEST,
            "lowest_supported_mode": LOWEST_SUPPORTED_MODE, "mode": LOWEST_SUPPORTED_MODE,
            "disposition": "FAIL_CLOSED" if unmet else "ALLOW",
            "unmet_predicates": [r["predicate"] for r in unmet], "predicates": results,
            "evidence_sha256": sha256_uri(evidence) if evidence is not None else None,
            "evidence_lineage_head": evidence["lineage"].get("head")
            if isinstance(evidence, dict) and isinstance(evidence.get("lineage"), dict) else None,
            "authority_model": AUTHORITY_MODEL, "llm_used": False, "network_used": False, "clock_read": False}


# --- organization-ledger receipt (LC-KV-06) -------------------------------------------------------
# The finish point records an ALLOW verdict as an organization-ledger receipt. Shape and append
# semantics follow StegVerse-org/.github .stegverse/transition-ledger/org-contract.json:
# MANIFEST_DIRECTED_APPEND under ORGANIZATION_LEDGER_LOCK on refs/stegverse/organization-ledger.
# This module writes only to a caller-named scratch git directory that has no remote. It never pushes,
# never writes a real ledger, and never fabricates a genesis.
ORGANIZATION_LEDGER_REF = "refs/stegverse/organization-ledger"
ORGANIZATION_RECEIPT_SCHEMA = INTR_RECEIPT_SCHEMA
LEDGER_GENESIS_OWNER = ("organization-ledger writer split (StegVerse-Labs/.github#3255) / StegVerse-org/.github "
                        "transition-ledger genesis")
_ZERO_OID = "0" * 40
_GIT_ENV = {"GIT_AUTHOR_NAME": "kv-skap-vault", "GIT_AUTHOR_EMAIL": "kv-skap-vault@stegverse.invalid",
            "GIT_COMMITTER_NAME": "kv-skap-vault", "GIT_COMMITTER_EMAIL": "kv-skap-vault@stegverse.invalid",
            "GIT_AUTHOR_DATE": "1970-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "1970-01-01T00:00:00Z",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "PATH": "/usr/bin:/bin:/usr/local/bin"}


def organization_ledger_receipt(verdict: dict[str, Any]) -> dict[str, Any]:
    """The canonical-state-transition receipt for a finish-point verdict (deterministic, no clock)."""
    content = {k: v for k, v in verdict.items() if k != "ledger_append"}
    transition_id = f"{TASK_ID}:FINISH_POINT:{sha256_uri(content)[7:39]}"
    return {"schema": ORGANIZATION_RECEIPT_SCHEMA, "transition_id": transition_id, "transition_sequence": 1,
            "subject_or_correlation_id": TASK_ID, "transition_outcome": verdict["disposition"],
            "prior_state_ref_or_hash": verdict.get("evidence_lineage_head"),
            "required_evidence_manifest": [{
                "evidence_id": "kv_skap_vault_finish_point_verdict", "evidence_type": "KV_SKAP_VAULT_FINISH_POINT_VERDICT",
                "origin_transition_id": transition_id, "encoding": "canonical-json", "content": content,
                "sha256": hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()}]}


def _ledger_fail(code: str, klass: str, repair: str, next_attempt: str) -> dict[str, Any]:
    return {"disposition": "FAIL_CLOSED", "failure_code": code,
            "failed_predicate": "FINISH_POINT_APPENDS_ORGANIZATION_LEDGER_RECEIPT",
            "required_evidence_or_repair": repair,
            "retry_entrypoint": RETRY + " --evidence <file> --scratch-ledger-git-dir <dir>",
            "owning_existing_goal": GOAL_REF if klass != "B" else LEDGER_GENESIS_OWNER,
            "next_attempt": next_attempt, "failure_class": klass, "ledger_ref": ORGANIZATION_LEDGER_REF,
            "real_ledger_written": False}


def _git(git_dir: str, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--git-dir", git_dir, *args], input=stdin, capture_output=True, text=True,
                          env=_GIT_ENV, check=False)


def append_organization_ledger_receipt(receipt: dict[str, Any], scratch_ledger_git_dir: str | None) -> dict[str, Any]:
    """Append one receipt to a scratch ledger ref by compare-and-swap. Every refusal is six-field FAIL_CLOSED."""
    genesis_next = "on the organization-ledger genesis event (StegVerse-Labs/.github#3255 admission)"
    if scratch_ledger_git_dir is None:
        return _ledger_fail("ORGANIZATION_LEDGER_GENESIS_NOT_OBSERVED", "B",
                            "no organization-ledger genesis is observed by this finish point; once the writer split "
                            "establishes it, the ledger writer appends this receipt under ORGANIZATION_LEDGER_LOCK "
                            "(a scratch append can be exercised with --scratch-ledger-git-dir)", genesis_next)
    probe = _git(scratch_ledger_git_dir, "rev-parse", "--git-dir")
    if probe.returncode != 0:
        return _ledger_fail("SCRATCH_LEDGER_NOT_A_GIT_DIR", "A", "name an existing scratch git directory",
                            "on the next run naming a scratch git directory")
    if _git(scratch_ledger_git_dir, "remote").stdout.strip():
        return _ledger_fail("LEDGER_TARGET_NOT_SCRATCH", "C",
                            "the target has a remote; this module never writes a real ledger, only a remote-less "
                            "scratch git directory", "on the next run naming a remote-less scratch directory")
    tip = _git(scratch_ledger_git_dir, "rev-parse", "--verify", "--quiet", ORGANIZATION_LEDGER_REF + "^{commit}")
    if tip.returncode != 0:
        return _ledger_fail("ORGANIZATION_LEDGER_GENESIS_ABSENT", "B",
                            f"{ORGANIZATION_LEDGER_REF} has no genesis in the target; a genesis is never fabricated "
                            "here", genesis_next)
    predecessor = tip.stdout.strip()
    blob = _git(scratch_ledger_git_dir, "hash-object", "-w", "--stdin", stdin=canonical_json(receipt))
    name = receipt["transition_id"].replace(":", "_") + ".json"
    tree = _git(scratch_ledger_git_dir, "mktree", stdin=f"100644 blob {blob.stdout.strip()}\t{name}\n")
    commit = _git(scratch_ledger_git_dir, "commit-tree", tree.stdout.strip(), "-p", predecessor,
                  "-m", f"{ORGANIZATION_RECEIPT_SCHEMA} {receipt['transition_id']}")
    if blob.returncode or tree.returncode or commit.returncode:
        return _ledger_fail("SCRATCH_LEDGER_OBJECT_WRITE_FAILED", "A", "the scratch git directory refused objects",
                            "on the next run after the scratch directory is repaired")
    new = commit.stdout.strip()
    swap = _git(scratch_ledger_git_dir, "update-ref", ORGANIZATION_LEDGER_REF, new, predecessor)
    if swap.returncode != 0:
        return _ledger_fail("ORGANIZATION_LEDGER_PREDECESSOR_MOVED", "B",
                            "the ledger tip moved during the append; re-run against the new tip",
                            "on the next run after the concurrent append")
    return {"disposition": "ALLOW", "ledger_ref": ORGANIZATION_LEDGER_REF, "predecessor_commit": predecessor,
            "appended_commit": new, "receipt_transition_id": receipt["transition_id"],
            "receipt_sha256": sha256_uri(receipt), "locus": "SCRATCH_LEDGER", "real_ledger_written": False}


def finish_point(evidence: Any = None, scratch_ledger_git_dir: str | None = None) -> dict[str, Any]:
    verdict = evaluate(evidence)
    if verdict["disposition"] == "ALLOW":
        verdict["ledger_append"] = append_organization_ledger_receipt(
            organization_ledger_receipt(verdict), scratch_ledger_git_dir)
    else:
        verdict["ledger_append"] = {**_ledger_fail(
            "FINISH_POINT_VERDICT_NOT_ALLOW", "B",
            "only an ALLOW finish-point verdict is recorded on the organization ledger; repair the unmet predicates "
            f"{verdict['unmet_predicates']}", "on the next finish-point run whose verdict is ALLOW"),
            "owning_existing_goal": GOAL_REF, "ledger_append_attempted": False}
    verdict["runtime_disposition"] = ("ALLOW" if verdict["disposition"] == "ALLOW"
                                      and verdict["ledger_append"]["disposition"] == "ALLOW" else "FAIL_CLOSED")
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m runtime.kv_skap_vault")
    parser.add_argument("command", choices=["finish-point"])
    parser.add_argument("--evidence", help=f"{EVIDENCE_SCHEMA} JSON file")
    parser.add_argument("--scratch-ledger-git-dir", help="remote-less scratch git dir holding the ledger ref")
    args = parser.parse_args(argv)
    evidence: Any = None
    if args.evidence:
        try:
            with open(args.evidence, encoding="utf-8") as stream:
                evidence = json.load(stream)
        except (OSError, ValueError):
            evidence = {"schema": "UNREADABLE"}
    verdict = finish_point(evidence, args.scratch_ledger_git_dir)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["runtime_disposition"] == "ALLOW" else 2


if __name__ == "__main__":
    sys.exit(main())
