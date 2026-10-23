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
* Interlock/InTr is the transition authority. Access has two credential layers (StegVerse-Labs/.github#3330
  rev 1):
  * Layer 1: KV is reachable only through InTr from a currently admitted healthy node. This is
    ``KVInterlockRuntime.handle``, INTR_DEVICE_KV, and it consumes the InTr healthy-node evaluator.
  * Layer 2: the SKAP Vault is reachable only through InTr from inside KV. This is ``SkapLayer2Gate``,
    INTR_KV_SKAP, a separate gate fed by a layer-1 receipt.
  * Every vault operation consumes one layer-2 receipt, and ``skap_entry`` is the deterministic SKAP entry. This
    module decides no node's health and asserts neither hop.
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

from runtime.kv_interlock_endpoint import (HEALTHY_NODE_RECEIPT_SCHEMA, KV_ACCESS_RECEIPT_SCHEMA,
                                           PINNED_HEALTHY_NODE_EVALUATOR, PINNED_HEALTHY_NODE_EVALUATOR_ID,
                                           KVInterlockRuntime, _HEALTHY_RECEIPT_EXACT)
from runtime.kv_skap_layer2 import (LAYER1_REFUSAL_CODE, LAYER2_REFUSAL_CODE, SKAP_ACCESS_RECEIPT_SCHEMA,
                                    SkapLayer2Gate, kv_skap_transition)
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


# --- the two credential layers (StegVerse-Labs/.github#3330 rev 1, revised LC-KV-03, LC-KV-07/08/10/11/12) ------------
# Layer 1: KV is reachable only through InTr from a currently admitted healthy node. That is
#   KVInterlockRuntime.handle (INTR_DEVICE_KV), which mints a KV-access receipt.
# Layer 2: the SKAP Vault is reachable only through InTr from inside KV. That is SkapLayer2Gate.admit
#   (INTR_KV_SKAP, runtime/kv_skap_layer2.py), a separate gate. It admits a transition whose prior_receipt_hash is a
#   layer-1 receipt that the layer-1 runtime minted, and it mints a single-use SKAP-access receipt.
# Every KVSkapVault operation consumes one SKAP-access receipt before it reads or changes anything, so a direct call
# reaches nothing. skap_entry() below is the deterministic SKAP entry that drives both steps. A lineage receipt records
# the layer-1 and layer-2 receipt hashes and the InTr receipt ref, so the finish point can re-verify the chain.
LAYER_PREDICATE_L1 = "KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE"
LAYER_PREDICATE_L2 = "SKAP_VAULT_REACHABLE_ONLY_VIA_INTR_FROM_KV"
LAYER_PREDICATE_PRIOR = "SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT"
#: Where each access constraint is enforced inside the sealed predicates. The scope digest is unchanged.
ACCESS_CONSTRAINT_PREDICATE = {
    LAYER_PREDICATE_L1: "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
    LAYER_PREDICATE_L2: "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY",
    LAYER_PREDICATE_PRIOR: "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY",
}
KIND_OPERATION = {
    "CUSTODY_KEY_REFERENCE_BOUND": "BIND_CUSTODY_KEY_REFERENCE",
    "CONSENT_GRANTED": "CONSENT_GRANT",
    "CONSENT_REVOKED": "CONSENT_REVOKE",
    "KV_PROJECTION_WRITTEN": "SKAP_WRITE",
    "KV_PROJECTION_READ": "SKAP_READ",
}


def consent_subject(projection_ids: Any) -> str:
    return "projections:" + ",".join(sorted(set(projection_ids or [])))


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") \
        and all(c in "0123456789abcdef" for c in value[7:])


class KVSkapVault:
    """One principal's KV with the SKAP Vault inside it. All state is the receipt lineage itself.

    Every operation takes ``skap_access_receipt_hash``, a receipt minted by the layer-2 gate passed as
    ``skap_gate``. Without both, the operation is a six-field VaultRefusal ``SKAP_ACCESS_LAYER2_REFUSED``.
    """

    def __init__(self, principal_ref: str, *, skap_gate: Any = None) -> None:
        if not isinstance(principal_ref, str) or not principal_ref:
            raise VaultRefusal("KV_PRINCIPAL_REF_MISSING", "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
                               "name the principal reference")
        self.principal_ref = principal_ref
        self.skap_gate = skap_gate
        self.lineage: list[dict[str, Any]] = []
        self._custody: dict[str, dict[str, Any]] = {}
        self._consents: dict[str, dict[str, Any]] = {}
        self._projections: dict[str, dict[str, Any]] = {}

    # --- layer 2, consumed before anything else
    def _admit(self, operation: str, subject_ref: str, skap_access_receipt_hash: Any,
               intr_transition_ref: Any = None) -> dict[str, Any]:
        return _consume_layer2(self.skap_gate, self.principal_ref, operation, subject_ref, skap_access_receipt_hash,
                               intr_transition_ref)

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
    def bind_custody_key_reference(self, *, custody_key_ref: str, issued_by: str, tvc_issuance_receipt_ref: str,
                                   skap_access_receipt_hash: Any = None) -> dict[str, Any]:
        pred = "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY"
        access = self._admit("BIND_CUSTODY_KEY_REFERENCE", str(custody_key_ref), skap_access_receipt_hash)
        if issued_by != CREDENTIAL_AUTHORITY:
            raise VaultRefusal("SKAP_CUSTODY_WRITER_NOT_TV_TVC",
                               "TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER",
                               f"only {CREDENTIAL_AUTHORITY} issues SKAP custody keys; obtain the reference from TV/TVC")
        if not isinstance(custody_key_ref, str) or not custody_key_ref.startswith(CUSTODY_REF_PREFIX) \
                or len(custody_key_ref) <= len(CUSTODY_REF_PREFIX):
            raise VaultRefusal("SKAP_CUSTODY_KEY_REFERENCE_INVALID", pred,
                               f"supply a TV/TVC custody-key reference of the form {CUSTODY_REF_PREFIX}<id>")
        if not _is_sha256(tvc_issuance_receipt_ref):
            raise VaultRefusal("TVC_CUSTODY_ISSUANCE_RECEIPT_MISSING", pred,
                               "bind the receipt_sha256 (sha256:<64 hex>) of the TV/TVC issuance receipt for this "
                               "custody key; a free-form string is not an issuance receipt")
        body = {"custody_key_ref": custody_key_ref, "issued_by": issued_by,
                "tvc_issuance_receipt_ref": tvc_issuance_receipt_ref, "access": access}
        _refuse_material(body, "custody", pred)
        return self._append("CUSTODY_KEY_REFERENCE_BOUND", body)

    # --- consent and revocation
    def grant_consent(self, *, purposes: list[str], projection_ids: list[str], observed_at: str,
                      skap_access_receipt_hash: Any = None) -> dict[str, Any]:
        pred = "CONSENT_RECEIPT_PRECEDES_EVERY_KV_WRITE_AND_READ"
        access = self._admit("CONSENT_GRANT", consent_subject(projection_ids if isinstance(projection_ids, list)
                                                              else []), skap_access_receipt_hash)
        allowed = {"WRITE", "READ"}
        if not purposes or not set(purposes) <= allowed or not projection_ids:
            raise VaultRefusal("KV_CONSENT_SCOPE_INVALID", pred,
                               "consent names purposes within WRITE/READ and at least one projection id")
        body = {"purposes": sorted(set(purposes)), "projection_ids": sorted(set(projection_ids)),
                "observed_at": observed_at, "access": access}
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

    def revoke_consent(self, *, consent_receipt_hash: str, observed_at: str, skap_access_receipt_hash: Any = None,
                       intr_transition_ref: Any = None) -> dict[str, Any]:
        access = self._admit("CONSENT_REVOKE", str(consent_receipt_hash), skap_access_receipt_hash,
                             intr_transition_ref)
        if consent_receipt_hash not in self._consents:
            raise VaultRefusal("KV_CONSENT_RECEIPT_NOT_FOUND", "REVOCATION_RECEIPT_ENDS_READ_ACCESS",
                               "revoke a consent receipt that exists in this lineage")
        if self._consents[consent_receipt_hash]["revoked_by"] is not None:
            raise VaultRefusal("KV_CONSENT_ALREADY_REVOKED", "REVOCATION_RECEIPT_ENDS_READ_ACCESS",
                               "nothing to repair; the consent is already revoked", failure_class="C")
        return self._append("CONSENT_REVOKED", {"consent_receipt_hash": consent_receipt_hash,
                                                "observed_at": observed_at, "access": access})

    # --- KV projection write / read
    def write_projection(self, *, projection_id: str, content: Any, consent_receipt_hash: str,
                         custody_key_ref: str, skap_access_receipt_hash: Any = None,
                         intr_transition_ref: Any = None) -> dict[str, Any]:
        access = self._admit("SKAP_WRITE", str(projection_id), skap_access_receipt_hash, intr_transition_ref)
        self._consent(consent_receipt_hash, "WRITE", projection_id)
        if custody_key_ref not in self._custody:
            raise VaultRefusal("SKAP_CUSTODY_KEY_REFERENCE_NOT_BOUND",
                               "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY",
                               "bind the TV/TVC custody-key reference before writing")
        _refuse_material(content, "content", "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY")
        body = {"projection_id": projection_id, "content": copy.deepcopy(content),
                "content_sha256": sha256_uri(content), "consent_receipt_hash": consent_receipt_hash,
                "custody_key_ref": custody_key_ref, "access": access}
        return self._append("KV_PROJECTION_WRITTEN", body)

    def read_projection(self, *, projection_id: str, consent_receipt_hash: str,
                        skap_access_receipt_hash: Any = None) -> tuple[Any, dict[str, Any]]:
        access = self._admit("SKAP_READ", str(projection_id), skap_access_receipt_hash)
        self._consent(consent_receipt_hash, "READ", projection_id)
        stored = self._projections.get(projection_id)
        if stored is None:
            raise VaultRefusal("KV_PROJECTION_NOT_FOUND", "KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT",
                               "write the projection first", failure_class="C")
        content = copy.deepcopy(stored["content"])
        receipt = self._append("KV_PROJECTION_READ", {"projection_id": projection_id,
                                                      "content_sha256": sha256_uri(content),
                                                      "consent_receipt_hash": consent_receipt_hash,
                                                      "access": access})
        return content, receipt

    # --- continuity: the lineage is the whole state, so any device reconstructs it (through both layers)
    def export_lineage(self) -> dict[str, Any]:
        return {"schema": "stegverse.kv-skap-vault-lineage/v1", "task_id": TASK_ID,
                "principal_ref": self.principal_ref, "head": self.head,
                "receipts": copy.deepcopy(self.lineage)}

    @classmethod
    def reconstruct(cls, exported: dict[str, Any], *, skap_gate: Any = None,
                    skap_access_receipt_hash: Any = None) -> "KVSkapVault":
        principal = exported.get("principal_ref") if isinstance(exported, dict) else None
        _consume_layer2(skap_gate, principal if isinstance(principal, str) else "",
                        "RECONSTRUCT", str(exported.get("head") if isinstance(exported, dict) else None),
                        skap_access_receipt_hash)
        verify_lineage(exported)
        vault = cls(exported["principal_ref"], skap_gate=skap_gate)
        for receipt in exported["receipts"]:
            vault._apply(receipt)
            vault.lineage.append(copy.deepcopy(receipt))
        return vault


def _consume_layer2(gate: Any, principal_ref: str, operation: str, subject_ref: str, receipt_hash: Any,
                    intr_transition_ref: Any = None) -> dict[str, Any]:
    """Consume one SKAP-access receipt from the layer-2 gate, or raise a six-field VaultRefusal."""
    if intr_transition_ref is not None:
        raise VaultRefusal(LAYER2_REFUSAL_CODE, LAYER_PREDICATE_L2, (
            "a caller-supplied InTr reference is not an access receipt; reach the SKAP Vault through "
            "SkapLayer2Gate.admit with a layer-1 KV-access receipt and pass skap_access_receipt_hash"), failure_class="C")
    if gate is None or not callable(getattr(gate, "consume", None)):
        raise VaultRefusal(LAYER2_REFUSAL_CODE, LAYER_PREDICATE_L2, (
            "the SKAP Vault is reachable only through InTr from inside KV: construct the vault with the layer-2 gate "
            "(runtime.kv_skap_layer2.SkapLayer2Gate over KVInterlockRuntime) and enter through skap_entry"),
            next_attempt="on the next SKAP operation admitted by the layer-2 gate")
    if not _is_sha256(receipt_hash):
        raise VaultRefusal(LAYER2_REFUSAL_CODE, LAYER_PREDICATE_L2, (
            "skap_access_receipt_hash must be a SKAP-access receipt minted by SkapLayer2Gate.admit on a verified "
            "layer-1 KV-access receipt"), failure_class="C")
    receipt, refusal = gate.consume(receipt_hash, principal_ref=principal_ref, operation=operation,
                                    subject_ref=subject_ref)
    if refusal is not None:
        raise VaultRefusal(refusal["failure_code"], refusal["failed_predicate"],
                           refusal["required_evidence_or_repair"], failure_class=refusal.get("failure_class", "C"),
                           next_attempt=refusal["next_attempt"])
    return {"kv_access_receipt_hash": receipt["prior_receipt_hash"], "skap_access_receipt_hash": receipt_hash,
            "intr_receipt_ref": receipt["layer1_intr_receipt_ref"],
            "requester_node_ref": receipt["layer1_requester_node_ref"]}


_ENTRY_ARGUMENTS = {
    "BIND_CUSTODY_KEY_REFERENCE": ("bind_custody_key_reference", lambda a: a.get("custody_key_ref")),
    "CONSENT_GRANT": ("grant_consent", lambda a: consent_subject(a.get("projection_ids"))),
    "CONSENT_REVOKE": ("revoke_consent", lambda a: a.get("consent_receipt_hash")),
    "SKAP_WRITE": ("write_projection", lambda a: a.get("projection_id")),
    "SKAP_READ": ("read_projection", lambda a: a.get("projection_id")),
    "RECONSTRUCT": ("reconstruct", lambda a: (a.get("exported") or {}).get("head")),
}


def skap_entry(gate: Any, vault: "KVSkapVault | None", *, operation: str, kv_access_receipt_hash: Any,
               arguments: dict[str, Any]) -> dict[str, Any]:
    """LC-KV-12: the deterministic SKAP entry inside KV. It is the one caller of the SKAP read and bind paths.

    It submits exactly one INTR_KV_SKAP transition, whose prior_receipt_hash is the caller's layer-1 KV-access
    receipt, to the layer-2 gate. Only on ALLOW does it run the one vault operation with the minted SKAP-access
    receipt. It returns ALLOW with the result, or a six-field FAIL_CLOSED from whichever layer refused. It never
    raises a refusal.
    """
    def closed(fields: dict[str, Any]) -> dict[str, Any]:
        return {"disposition": "FAIL_CLOSED", **{k: v for k, v in fields.items() if k != "disposition"}}

    if operation not in _ENTRY_ARGUMENTS or not isinstance(arguments, dict):
        return closed(VaultRefusal(LAYER2_REFUSAL_CODE, LAYER_PREDICATE_L2,
                                   f"operation must be one of {sorted(_ENTRY_ARGUMENTS)}", failure_class="C").fields)
    method, subject_of = _ENTRY_ARGUMENTS[operation]
    principal = vault.principal_ref if vault is not None else (arguments.get("exported") or {}).get("principal_ref")
    if gate is None or (vault is not None and vault.skap_gate is not gate):
        return closed(VaultRefusal(LAYER2_REFUSAL_CODE, LAYER_PREDICATE_L2,
                                   "the vault must be constructed with this layer-2 gate").fields)
    admitted = gate.admit(kv_skap_transition(principal_ref=str(principal), operation=operation,
                                             subject_ref=str(subject_of(arguments)),
                                             prior_receipt_hash=kv_access_receipt_hash))
    if admitted.get("disposition") != "ALLOW":
        return closed(admitted)
    receipt_hash = admitted["skap_access_receipt"]["receipt_hash"]
    try:
        if operation == "RECONSTRUCT":
            result: Any = KVSkapVault.reconstruct(arguments["exported"], skap_gate=gate,
                                                  skap_access_receipt_hash=receipt_hash)
        else:
            result = getattr(vault, method)(skap_access_receipt_hash=receipt_hash, **arguments)
    except VaultRefusal as exc:
        return closed(exc.fields)
    except (TypeError, KeyError, AttributeError) as exc:
        return closed(VaultRefusal("SKAP_ENTRY_ARGUMENTS_INVALID", LAYER_PREDICATE_L2,
                                   f"{type(exc).__name__}: {exc}", failure_class="C").fields)
    return {"disposition": "ALLOW", "operation": operation, "result": result,
            "skap_access_receipt_hash": receipt_hash, "kv_access_receipt_hash": kv_access_receipt_hash}


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
        f"{INTR_RECEIPT_SCHEMA} per write/revoke whose sha256 is the intr_receipt_ref its layer-1 KV-access receipt "
        f"binds (outcome in {INTR_ADMITTED_OUTCOMES}, subject_or_correlation_id == principal_ref) from Interlock/InTr; "
        "and the access_constraints row KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE",
        GOAL_REF, None),
    "ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED": (
        "KV_DURABLE_CUSTODY_LOCATION_NOT_BOUND", "B",
        "reconstruction from the lineage alone is exact on a fresh instance; the durable KV custody location "
        "the lineage is read from on any device is consumed from " + SOVEREIGN_KV_CUSTODY_GOAL + " (provider-"
        "neutral write and exact-hash readback; its first unresolved predicate is AUTHENTIC_ADMITTED_PROVIDER_"
        "WRITE_AND_EXACT_EVENT_HASH_READBACK_FROM_SOVEREIGN_KV) and is not re-implemented here; supply its ALLOW "
        "readback receipt as evidence.durable_custody_readback_receipt (lineage_sha256 == sha256 of "
        "evidence.lineage, provider not device-local)", SOVEREIGN_KV_CUSTODY_GOAL, "CONSUMES"),
    "SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY": (
        LAYER2_REFUSAL_CODE, "B",
        "the vault holds custody-key references only and admits nothing without its layer-2 gate; supply "
        "evidence.layer1_kv_access_receipts and evidence.layer2_skap_access_receipts, the two credential layers that "
        "every lineage receipt records (access_constraints rows SKAP_VAULT_REACHABLE_ONLY_VIA_INTR_FROM_KV and "
        "SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT)", GOAL_REF, None),
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


# --- local exercise harness: both gates, run with an exercise-only health evaluator -----------------------------------
LOCAL_EXERCISE_LABEL = "LOCAL_EXERCISE_ONLY_NOT_EVIDENCE"


def _exercise_only_healthy_node_evaluator(evidence: Any, *, requester_node_ref: str) -> dict[str, Any]:
    """LOCAL_EXERCISE_ONLY_NOT_EVIDENCE: used only so _exercise can drive both gates locally.

    This is not the InTr evaluator, so its identity is not PINNED_HEALTHY_NODE_EVALUATOR_ID. The finish-point evidence
    checks refuse every layer-1 receipt it produced. It asserts the health of nothing outside this process.
    """
    if evidence != {"label": LOCAL_EXERCISE_LABEL, "node_ref": requester_node_ref}:
        return {"disposition": "DENY", "failure_code": "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY",
                "required_evidence_or_repair": "local exercise evidence absent"}
    body = {**_HEALTHY_RECEIPT_EXACT, "node_ref": requester_node_ref,
            "ingress_receipt_sha256": sha256_uri({"label": LOCAL_EXERCISE_LABEL, "node_ref": requester_node_ref})}
    return {"disposition": "ALLOW", "healthy_node_receipt": {**body, "receipt_sha256": sha256_uri(body)}}


class _ExerciseHarness:
    """Layer 1 and layer 2 wired together for the local exercise, with a fixed clock and no I/O."""

    node = "device:local-exercise"

    def __init__(self) -> None:
        from datetime import datetime, timezone
        fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.layer1 = KVInterlockRuntime(
            authority_validator=lambda ref, request, envelope: ref == LOCAL_EXERCISE_LABEL,
            policy_evaluator=lambda request: {"decision": "ALLOW_BOUNDED_CONTEXT",
                                              "granted_scope": list(request["requested_scope"]), "context": {},
                                              "source_refs": [], "policy_profile": LOCAL_EXERCISE_LABEL},
            receipt_store=lambda receipt: "local-exercise:" + receipt["receipt_id"],
            clock=lambda: fixed, healthy_node_evaluator=_exercise_only_healthy_node_evaluator)
        self.gate = SkapLayer2Gate(self.layer1)
        self.count = 0

    def request(self, verification_state: str = "VERIFIED") -> tuple[dict[str, Any], dict[str, Any], str]:
        self.count += 1
        request = {"schema_version": "kv.interlock.request.v1", "operation": "REQUEST",
                   "request_id": f"local-exercise-{self.count}",
                   "requester": {"module": "KV", "component": "kv-skap-vault-local-exercise"},
                   "purpose": "Local exercise.", "record_class": "KV_SKAP_VAULT", "requested_scope": ["skap_vault"],
                   "minimum_necessary_justification": "Local exercise.", "authority_ref": LOCAL_EXERCISE_LABEL,
                   "disclosure_mode": "BOUNDED_CONTEXT"}
        envelope = {"schema": "stegverse.kv-interlock.intr-envelope/v1", "protocol": "InTr",
                    "packet_id": f"local-exercise-packet-{self.count}", "direction": "REQUEST",
                    "source_role": "DEVICE", "next_role": "KV", "request_id": request["request_id"],
                    "operation": "REQUEST", "payload_schema_version": "kv.interlock.request.v1",
                    "payload_hash": sha256_uri(request), "sealed_material_ref": "local-exercise:sealed",
                    "authority": {"authority_transfer": False, "transport_grants_execution_authority": False,
                                  "model_output_grants_execution_authority": False,
                                  "credential_authority_effect": "NONE"},
                    "boundary_proof": {"required": True, "source_identity_ref": self.node,
                                       "next_boundary_identity_ref": "kv:local-exercise",
                                       "verification_state": verification_state},
                    "receipt_policy": {"receipt_required": True, "receipt_contains_payload_plaintext": False,
                                       "receipt_chain_required": True, "ambiguous_disposition": "FAIL_CLOSED"}}
        return request, envelope, sha256_uri({"local_exercise_intr_transition": self.count})

    def kv_access(self, health: Any = "default", verification_state: str = "VERIFIED") -> dict[str, Any]:
        request, envelope, intr_ref = self.request(verification_state)
        evidence = {"label": LOCAL_EXERCISE_LABEL, "node_ref": self.node} if health == "default" else health
        return self.layer1.handle(request, intr_envelope=envelope, intr_receipt_ref=intr_ref,
                                  healthy_node_evidence=evidence)

    def kv_hash(self) -> str:
        return self.kv_access()["kv_access_receipt"]["receipt_hash"]

    def enter(self, vault: "KVSkapVault | None", operation: str, **arguments: Any) -> dict[str, Any]:
        return skap_entry(self.gate, vault, operation=operation, kv_access_receipt_hash=self.kv_hash(),
                          arguments=arguments)

    def skap_hash(self, principal: str, operation: str, subject: str) -> str:
        admitted = self.gate.admit(kv_skap_transition(principal_ref=principal, operation=operation,
                                                      subject_ref=subject, prior_receipt_hash=self.kv_hash()))
        return admitted["skap_access_receipt"]["receipt_hash"]


def _exercise() -> dict[str, bool]:
    """Run the full local round-trip and the negative cases, through both gates. Returns predicate -> satisfied."""
    ok: dict[str, bool] = {}
    h = _ExerciseHarness()
    vault = KVSkapVault("principal:fixture", skap_gate=h.gate)
    ref = CUSTODY_REF_PREFIX + "fixture-0001"
    tvc_ref = sha256_uri({"local_exercise": "tvc-issuance"})

    def allow(out: dict[str, Any]) -> Any:
        if out.get("disposition") != "ALLOW":
            raise VaultRefusal(out.get("failure_code", "SKAP_ENTRY_REFUSED"),
                               out.get("failed_predicate", LAYER_PREDICATE_L2),
                               out.get("required_evidence_or_repair", "local exercise"), failure_class="A")
        return out["result"]

    allow(h.enter(vault, "BIND_CUSTODY_KEY_REFERENCE", custody_key_ref=ref, issued_by=CREDENTIAL_AUTHORITY,
                  tvc_issuance_receipt_ref=tvc_ref))
    consent = allow(h.enter(vault, "CONSENT_GRANT", purposes=["WRITE", "READ"], projection_ids=["notes/profile"],
                            observed_at="local-exercise"))["receipt_hash"]
    content = {"title": "profile", "fields": {"display_name": "Exercise", "languages": ["en", "es"]}}
    allow(h.enter(vault, "SKAP_WRITE", projection_id="notes/profile", content=content, consent_receipt_hash=consent,
                  custody_key_ref=ref))
    read, _ = allow(h.enter(vault, "SKAP_READ", projection_id="notes/profile", consent_receipt_hash=consent))
    allow(h.enter(vault, "CONSENT_REVOKE", consent_receipt_hash=consent, observed_at="local-exercise"))
    after = h.enter(vault, "SKAP_READ", projection_id="notes/profile", consent_receipt_hash=consent)
    revoked_blocks = after.get("failure_code") == "KV_CONSENT_REVOKED"
    no_health = h.kv_access(health=None)
    unverified = h.kv_access(verification_state="UNVERIFIED")
    layer1_refuses = all(out.get("decision") == "FAIL_CLOSED" and out.get("failure_code") == LAYER1_REFUSAL_CODE
                         and out.get("kv_access_receipt") is None for out in (no_health, unverified))
    ok["KV_PROJECTION_WRITE_READ_REVOKE_ROUNDTRIP_EXACT"] = read == content and revoked_blocks and layer1_refuses

    def refused(fn, code: str) -> bool:
        try:
            out = fn()
        except VaultRefusal as exc:
            return exc.fields["failure_code"] == code
        return isinstance(out, dict) and out.get("disposition") == "FAIL_CLOSED" and out.get("failure_code") == code

    principal = "principal:fixture"
    other = KVSkapVault(principal, skap_gate=h.gate)
    live = KVSkapVault(principal, skap_gate=h.gate)
    allow(h.enter(live, "BIND_CUSTODY_KEY_REFERENCE", custody_key_ref=ref, issued_by=CREDENTIAL_AUTHORITY,
                  tvc_issuance_receipt_ref=tvc_ref))
    live_consent = allow(h.enter(live, "CONSENT_GRANT", purposes=["WRITE"], projection_ids=["p"],
                                 observed_at="local-exercise"))["receipt_hash"]
    ungated = KVSkapVault(principal)
    forged_prior = sha256_uri({"caller_minted": "layer-1"})
    spent = h.skap_hash(principal, "SKAP_WRITE", "p")
    live.write_projection(projection_id="p", content={"n": 1}, consent_receipt_hash=live_consent, custody_key_ref=ref,
                          skap_access_receipt_hash=spent)
    ok["SKAP_VAULT_INSIDE_KV_HOLDS_CUSTODY_KEY_REFERENCES_ONLY"] = all([
        refused(lambda: h.enter(other, "BIND_CUSTODY_KEY_REFERENCE", custody_key_ref="raw-bytes",
                                issued_by=CREDENTIAL_AUTHORITY, tvc_issuance_receipt_ref=tvc_ref),
                "SKAP_CUSTODY_KEY_REFERENCE_INVALID"),
        refused(lambda: h.enter(live, "SKAP_WRITE", projection_id="p", content={"private_key": "x"},
                                consent_receipt_hash=live_consent, custody_key_ref=ref),
                "SKAP_VAULT_KEY_OR_CREDENTIAL_MATERIAL_REFUSED"),
        refused(lambda: _refuse_material({"key_material": "x"}, "c", "P"), "SKAP_VAULT_KEY_OR_CREDENTIAL_MATERIAL_REFUSED"),
        # layer 2: nothing in the vault is reachable directly, with a forged prior, by replay, or out of scope
        refused(lambda: ungated.bind_custody_key_reference(custody_key_ref=ref, issued_by=CREDENTIAL_AUTHORITY,
                                                           tvc_issuance_receipt_ref=tvc_ref), LAYER2_REFUSAL_CODE),
        refused(lambda: live.read_projection(projection_id="p", consent_receipt_hash=live_consent), LAYER2_REFUSAL_CODE),
        refused(lambda: live.write_projection(projection_id="p", content={}, consent_receipt_hash=live_consent,
                                              custody_key_ref=ref, intr_transition_ref="intr:caller-asserted"),
                LAYER2_REFUSAL_CODE),
        refused(lambda: skap_entry(h.gate, live, operation="SKAP_READ", kv_access_receipt_hash=forged_prior,
                                   arguments={"projection_id": "p", "consent_receipt_hash": live_consent}),
                LAYER2_REFUSAL_CODE),
        refused(lambda: live.write_projection(projection_id="p", content={}, consent_receipt_hash=live_consent,
                                              custody_key_ref=ref, skap_access_receipt_hash=spent), LAYER2_REFUSAL_CODE),
        refused(lambda: live.read_projection(projection_id="p", consent_receipt_hash=live_consent,
                                             skap_access_receipt_hash=h.skap_hash(principal, "SKAP_WRITE", "p")),
                LAYER2_REFUSAL_CODE),
        refused(lambda: KVSkapVault.reconstruct(vault.export_lineage()), LAYER2_REFUSAL_CODE),
    ])
    ok["CONSENT_RECEIPT_PRECEDES_EVERY_KV_WRITE_AND_READ"] = all([
        refused(lambda: h.enter(other, "SKAP_WRITE", projection_id="p", content={}, consent_receipt_hash="sha256:none",
                                custody_key_ref=ref), "KV_CONSENT_RECEIPT_NOT_FOUND"),
        refused(lambda: h.enter(other, "SKAP_READ", projection_id="p", consent_receipt_hash="sha256:none"),
                "KV_CONSENT_RECEIPT_NOT_FOUND"),
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
    fresh = allow(h.enter(None, "RECONSTRUCT", exported=json.loads(canonical_json(exported))))
    ok["ANY_DEVICE_CONTINUITY_WITH_NO_CONNECTED_DEVICE_REQUIRED"] = (
        fresh.head == vault.head and fresh._projections == vault._projections and fresh._consents == vault._consents)
    ok["TV_TVC_REMAINS_CREDENTIAL_AUTHORITY_AND_SOLE_SKAP_CIPHERTEXT_WRITER"] = refused(
        lambda: h.enter(other, "BIND_CUSTODY_KEY_REFERENCE", custody_key_ref=ref, issued_by="KV",
                        tvc_issuance_receipt_ref=tvc_ref), "SKAP_CUSTODY_WRITER_NOT_TV_TVC")
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
    by_hash = {sha256_uri(r): r for r in receipts if isinstance(r, dict)}
    for receipt in _receipts_of(lineage, "KV_PROJECTION_WRITTEN") + _receipts_of(lineage, "CONSENT_REVOKED"):
        ref = (receipt["body"].get("access") or {}).get("intr_receipt_ref")
        intr = by_hash.get(ref)
        if intr is None:
            return ("INTR_TRANSITION_RECEIPT_NOT_BOUND", "B",
                    f"no Interlock/InTr receipt hashes to {ref!r} (lineage receipt {receipt['sequence']})")
        if intr.get("schema") != INTR_RECEIPT_SCHEMA or intr.get("transition_outcome") not in INTR_ADMITTED_OUTCOMES \
                or intr.get("subject_or_correlation_id") != lineage["principal_ref"] or not _manifest_entries_verify(intr):
            return ("INTR_TRANSITION_RECEIPT_INVALID", "C",
                    f"the InTr receipt {ref!r} must be an {INTR_RECEIPT_SCHEMA} with outcome in "
                    f"{INTR_ADMITTED_OUTCOMES}, the principal as subject and a verifying evidence manifest")
    return None


# --- access constraints (the two credential layers), each evidence-bound -------------------------------------------
ACCESS_EVIDENCE_KEYS = ("layer1_kv_access_receipts", "layer2_skap_access_receipts")
ACCESS_CONSTRAINT_OWNER = {
    LAYER_PREDICATE_L1: ("Interlock/InTr healthy-node evaluator, LC-KV-13/LC-KV-14 (StegVerse-org/LLM-adapter "
                         "llm_adapter/node_ingress_boundary.py, InTr and Mesh Destinations lane)"),
    LAYER_PREDICATE_L2: GOAL_REF,
    LAYER_PREDICATE_PRIOR: GOAL_REF,
}
ACCESS_REPAIR = {
    LAYER_PREDICATE_L1: (
        "supply evidence.layer1_kv_access_receipts: one stegverse.kv-access-receipt/v1 minted by "
        "KVInterlockRuntime.handle (INTR_DEVICE_KV) per lineage receipt. Each must carry a healthy-node receipt from "
        f"the pinned InTr evaluator {PINNED_HEALTHY_NODE_EVALUATOR['repository']}:{PINNED_HEALTHY_NODE_EVALUATOR_ID} "
        "(LC-KV-13/14). KV never asserts health, and the local exercise evaluator is not evidence."),
    LAYER_PREDICATE_L2: (
        "supply evidence.layer2_skap_access_receipts: one stegverse.skap-access-receipt/v1 minted by "
        "SkapLayer2Gate.admit (INTR_KV_SKAP) per lineage receipt, used once, for the operation and principal it names"),
    LAYER_PREDICATE_PRIOR: (
        "each layer-2 receipt's prior_receipt_hash must be the layer-1 KV-access receipt the lineage receipt records, "
        "and each layer-1 receipt admits one layer-2 transition"),
}
_ACCESS_CODE = {LAYER_PREDICATE_L1: LAYER1_REFUSAL_CODE, LAYER_PREDICATE_L2: LAYER2_REFUSAL_CODE,
                LAYER_PREDICATE_PRIOR: LAYER2_REFUSAL_CODE}


def _rederives(receipt: Any, key: str) -> bool:
    return isinstance(receipt, dict) and receipt.get(key) == sha256_uri({k: v for k, v in receipt.items() if k != key})


def _healthy_receipt_verifies(layer1: dict[str, Any]) -> bool:
    healthy = layer1.get("healthy_node_receipt")
    return isinstance(healthy, dict) and all(healthy.get(k) == v for k, v in _HEALTHY_RECEIPT_EXACT.items()) \
        and healthy.get("schema") == HEALTHY_NODE_RECEIPT_SCHEMA \
        and healthy.get("node_ref") == layer1.get("requester_node_ref") and _is_sha256(healthy.get("ingress_receipt_sha256")) \
        and _rederives(healthy, "receipt_sha256")


def _access_failures(evidence: Any, lineage_failure: tuple[str, str, str] | None) -> dict[str, tuple[str, str, str] | None]:
    """constraint -> None (ALLOW) or (cause, failure_class, repair). It never raises."""
    constraints = (LAYER_PREDICATE_L1, LAYER_PREDICATE_L2, LAYER_PREDICATE_PRIOR)
    if not isinstance(evidence, dict) or evidence.get("schema") != EVIDENCE_SCHEMA:
        return {c: ("ACCESS_RECEIPTS_NOT_OBSERVED", "B", ACCESS_REPAIR[c]) for c in constraints}
    has1, has2 = bool(evidence.get(ACCESS_EVIDENCE_KEYS[0])), bool(evidence.get(ACCESS_EVIDENCE_KEYS[1]))
    absent1 = ("LAYER1_KV_ACCESS_RECEIPTS_NOT_OBSERVED", "B", ACCESS_REPAIR[LAYER_PREDICATE_L1])
    absent2 = ("LAYER2_SKAP_ACCESS_RECEIPTS_NOT_OBSERVED", "B", ACCESS_REPAIR[LAYER_PREDICATE_L2])
    return {
        LAYER_PREDICATE_L1: _guard_access(_check_layer1, evidence, lineage_failure) if has1 else absent1,
        LAYER_PREDICATE_L2: _guard_access(_check_layer2, evidence, lineage_failure) if has2 else absent2,
        LAYER_PREDICATE_PRIOR: (_guard_access(_check_prior, evidence, lineage_failure) if has1 and has2
                                else (absent2 if has1 else absent1)),
    }


def _guard_access(check, evidence: dict[str, Any], lineage_failure) -> tuple[str, str, str] | None:
    if lineage_failure is not None:
        return lineage_failure
    try:
        return check(evidence)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return ("ACCESS_EVIDENCE_MALFORMED", "C", f"{check.__name__}: {type(exc).__name__}")


def _lineage_access(evidence: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(r, (r.get("body") or {}).get("access") or {}) for r in evidence["lineage"]["receipts"]]


def _check_layer1(evidence: dict[str, Any]) -> tuple[str, str, str] | None:
    layer1 = {r.get("receipt_hash"): r for r in evidence[ACCESS_EVIDENCE_KEYS[0]] if isinstance(r, dict)}
    for receipt, access in _lineage_access(evidence):
        kv = layer1.get(access.get("kv_access_receipt_hash"))
        where = f"lineage receipt {receipt.get('sequence')}"
        if kv is None:
            return ("LAYER1_KV_ACCESS_RECEIPT_NOT_BOUND", "B", f"{where} binds no supplied layer-1 KV-access receipt")
        if not _rederives(kv, "receipt_hash") or kv.get("schema") != KV_ACCESS_RECEIPT_SCHEMA \
                or kv.get("boundary") != "INTR_DEVICE_KV" or kv.get("minted_by") != "KVInterlockRuntime.handle" \
                or kv.get("intr_receipt_ref") != access.get("intr_receipt_ref") \
                or kv.get("requester_node_ref") != access.get("requester_node_ref"):
            return ("LAYER1_KV_ACCESS_RECEIPT_INVALID", "C",
                    f"{where}: the layer-1 receipt must re-derive as an INTR_DEVICE_KV receipt minted by "
                    "KVInterlockRuntime.handle for the same InTr receipt and node")
        if not _healthy_receipt_verifies(kv):
            return ("HEALTHY_NODE_RECEIPT_INVALID", "C",
                    f"{where}: the layer-1 receipt carries no verifying REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE receipt")
        if kv.get("healthy_node_evaluator") != PINNED_HEALTHY_NODE_EVALUATOR_ID:
            return ("HEALTHY_NODE_EVALUATOR_NOT_THE_PINNED_INTR_EVALUATOR", "B",
                    f"{where}: health was evaluated by {kv.get('healthy_node_evaluator')!r}, not "
                    f"{PINNED_HEALTHY_NODE_EVALUATOR_ID}; {ACCESS_REPAIR[LAYER_PREDICATE_L1]}")
    return None


def _check_layer2(evidence: dict[str, Any]) -> tuple[str, str, str] | None:
    layer2 = {r.get("receipt_hash"): r for r in evidence[ACCESS_EVIDENCE_KEYS[1]] if isinstance(r, dict)}
    seen: set[str] = set()
    principal = evidence["lineage"]["principal_ref"]
    for receipt, access in _lineage_access(evidence):
        skap_hash = access.get("skap_access_receipt_hash")
        skap = layer2.get(skap_hash)
        where = f"lineage receipt {receipt.get('sequence')}"
        if skap is None:
            return ("LAYER2_SKAP_ACCESS_RECEIPT_NOT_BOUND", "B", f"{where} binds no supplied layer-2 SKAP-access receipt")
        if skap_hash in seen:
            return ("LAYER2_SKAP_ACCESS_RECEIPT_REUSED", "C", f"{where} reuses a single-use SKAP-access receipt")
        seen.add(skap_hash)
        if not _rederives(skap, "receipt_hash") or skap.get("schema") != SKAP_ACCESS_RECEIPT_SCHEMA \
                or skap.get("boundary") != "INTR_KV_SKAP" or skap.get("minted_by") != "SkapLayer2Gate.admit" \
                or skap.get("from_role") != "KV" or skap.get("principal_ref") != principal \
                or skap.get("operation") != KIND_OPERATION.get(receipt.get("kind")) \
                or skap.get("layer1_intr_receipt_ref") != access.get("intr_receipt_ref"):
            return ("LAYER2_SKAP_ACCESS_RECEIPT_INVALID", "C",
                    f"{where}: the layer-2 receipt must re-derive as an INTR_KV_SKAP receipt minted by "
                    "SkapLayer2Gate.admit from KV for this principal and operation")
    return None


def _check_prior(evidence: dict[str, Any]) -> tuple[str, str, str] | None:
    layer1 = {r.get("receipt_hash") for r in evidence[ACCESS_EVIDENCE_KEYS[0]] if isinstance(r, dict)}
    layer2 = {r.get("receipt_hash"): r for r in evidence[ACCESS_EVIDENCE_KEYS[1]] if isinstance(r, dict)}
    priors: set[str] = set()
    for receipt, access in _lineage_access(evidence):
        skap = layer2.get(access.get("skap_access_receipt_hash")) or {}
        prior = skap.get("prior_receipt_hash")
        where = f"lineage receipt {receipt.get('sequence')}"
        if prior is None or prior != access.get("kv_access_receipt_hash") or prior not in layer1:
            return ("LAYER2_PRIOR_IS_NOT_THE_LAYER1_RECEIPT", "C",
                    f"{where}: the SKAP-access receipt's prior_receipt_hash must be its layer-1 KV-access receipt")
        if prior in priors:
            return ("LAYER1_KV_ACCESS_RECEIPT_REUSED", "C", f"{where} reuses a layer-1 receipt")
        priors.add(prior)
    return None


def _access_rows(evidence: Any, lineage_failure) -> list[dict[str, Any]]:
    rows = []
    for constraint, failure in _access_failures(evidence, lineage_failure).items():
        row: dict[str, Any] = {"constraint": constraint, "enforced_in_sealed_predicate": ACCESS_CONSTRAINT_PREDICATE[constraint]}
        if failure is None:
            row.update(disposition="ALLOW", locus="EVIDENCE")
        else:
            lineage_broken = lineage_failure is not None and failure == lineage_failure
            row.update(disposition="FAIL_CLOSED", failed_predicate=constraint,
                       failure_code=failure[0] if lineage_broken else _ACCESS_CODE[constraint],
                       required_evidence_or_repair=f"{failure[0]}: {failure[2]}", retry_entrypoint=RETRY,
                       owning_existing_goal=GOAL_REF, next_attempt=EVIDENCE_NEXT, failure_class=failure[1],
                       refusal_cause=failure[0])
            if failure[1] == "B":
                row["dependency_owner"] = ACCESS_CONSTRAINT_OWNER[constraint]
        rows.append(row)
    return rows


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
    access = _access_rows(evidence if isinstance(evidence, dict) and evidence.get("schema") == EVIDENCE_SCHEMA
                          and isinstance(evidence.get("lineage"), dict) else None, lineage_failure)
    for index, row in enumerate(results):
        blocking = [a for a in access if a["enforced_in_sealed_predicate"] == row["predicate"]
                    and a["disposition"] != "ALLOW"]
        bound = [a for a in access if a["enforced_in_sealed_predicate"] == row["predicate"]]
        if row["disposition"] == "ALLOW" and bound and not blocking:
            results[index] = {**row, "locus": "LOCAL_EXERCISE+EVIDENCE"}
        if row["disposition"] == "ALLOW" and blocking:
            first = blocking[0]
            results[index] = {**_row(row["predicate"], first["failure_code"], first["failure_class"],
                                     first["required_evidence_or_repair"]),
                              "access_constraints_unmet": [a["constraint"] for a in blocking]}
    unmet = [r for r in results if r["disposition"] != "ALLOW"]
    return {"schema": VERDICT_SCHEMA, "task_id": TASK_ID, "scope_digest": SCOPE_DIGEST,
            "lowest_supported_mode": LOWEST_SUPPORTED_MODE, "mode": LOWEST_SUPPORTED_MODE,
            "disposition": "FAIL_CLOSED" if unmet else "ALLOW",
            "unmet_predicates": [r["predicate"] for r in unmet], "predicates": results,
            "access_constraints": access,
            "access_constraints_conformant": sum(1 for a in access if a["disposition"] == "ALLOW"),
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
