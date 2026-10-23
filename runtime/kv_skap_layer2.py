"""Layer 2 of the two credential layers: the SKAP Vault is reachable only through InTr from inside KV (E0, stdlib only).

StegVerse-Labs/.github#3330 rev 1, LC-KV-07/08/11/12, for KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324).

Layer 1 is ``KVInterlockRuntime.handle`` (runtime/kv_interlock_endpoint.py), the DEVICE->KV InTr entry (INTR_DEVICE_KV).
It admits only a currently admitted healthy node, and it mints a KV-access receipt into its own receipt store.

Layer 2 is ``SkapLayer2Gate.admit``, the KV->SKAP InTr entry (INTR_KV_SKAP), and it is a separate gate:
* It admits a transition only when its ``prior_receipt_hash`` is a KV-access receipt that the layer-1 runtime
  minted and still re-derives. The gate looks the receipt up through ``verify_kv_access_receipt`` and never
  recomputes or accepts a caller-asserted one.
* Each layer-1 receipt admits one transition. The gate then mints a SKAP-access receipt, bound to one principal,
  one operation and one subject, into its own store.
* The SKAP Vault consumes that receipt exactly once (``consume``).
* No single call mints both hops, and nothing here decides a node's health.
* Every refusal is a six-field FAIL_CLOSED ``SKAP_ACCESS_LAYER2_REFUSED``, returned and not raised.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

GOAL_REF = "KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324)"
LAYER2_REFUSAL_CODE = "SKAP_ACCESS_LAYER2_REFUSED"
LAYER1_REFUSAL_CODE = "KV_ACCESS_LAYER1_REFUSED"
LAYER2_BOUNDARY = "INTR_KV_SKAP"
LAYER1_BOUNDARY = "INTR_DEVICE_KV"
TRANSITION_SCHEMA = "stegverse.intr-kv-skap-transition/v1"
SKAP_ACCESS_RECEIPT_SCHEMA = "stegverse.skap-access-receipt/v1"
KV_ACCESS_RECEIPT_SCHEMA = "stegverse.kv-access-receipt/v1"
PREDICATE_REACHABLE_FROM_KV = "SKAP_VAULT_REACHABLE_ONLY_VIA_INTR_FROM_KV"
PREDICATE_PRIOR_LAYER1 = "SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT"
PREDICATE_HEALTHY_NODE = "KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE"
RETRY = "runtime.kv_skap_layer2.SkapLayer2Gate.admit (StegVerse-Labs/continuity-vault-kit)"
OPERATIONS = ("BIND_CUSTODY_KEY_REFERENCE", "SKAP_WRITE", "SKAP_READ", "RECONSTRUCT", "CONSENT_GRANT",
              "CONSENT_REVOKE", "SKAP_SEALED_CREDENTIAL_APPEND", "SKAP_SEALED_CREDENTIAL_READ")
_TRANSITION_KEYS = {"schema", "boundary", "from_role", "to_role", "principal_ref", "operation", "subject_ref",
                    "prior_receipt_hash"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_uri(value: Any) -> str:
    raw = value if isinstance(value, str) else canonical_json(value)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def layer2_refusal(cause: str, detail: str, *, predicate: str = PREDICATE_REACHABLE_FROM_KV,
                   failure_class: str = "C", code: str = LAYER2_REFUSAL_CODE) -> dict[str, Any]:
    return {
        "disposition": "FAIL_CLOSED",
        "layer": LAYER2_BOUNDARY if code == LAYER2_REFUSAL_CODE else LAYER1_BOUNDARY,
        "failure_code": code,
        "failed_predicate": predicate,
        "required_evidence_or_repair": f"{cause}: {detail}",
        "retry_entrypoint": RETRY,
        "owning_existing_goal": GOAL_REF,
        "next_attempt": "on the next KV->SKAP InTr transition whose prior_receipt_hash is a layer-1 KV-access receipt",
        "failure_class": failure_class,
        "refusal_cause": cause,
        "skap_access_receipt": None,
        "authority_effect": "NONE",
    }


def kv_skap_transition(*, principal_ref: str, operation: str, subject_ref: str,
                       prior_receipt_hash: str) -> dict[str, Any]:
    """The INTR_KV_SKAP transition a KV-side caller submits to layer 2 (it asserts nothing about either hop)."""
    return {"schema": TRANSITION_SCHEMA, "boundary": LAYER2_BOUNDARY, "from_role": "KV", "to_role": "SKAP_VAULT",
            "principal_ref": principal_ref, "operation": operation, "subject_ref": subject_ref,
            "prior_receipt_hash": prior_receipt_hash}


class SkapLayer2Gate:
    """The KV->SKAP InTr gate. It holds its own receipt store, apart from the layer-1 runtime's store."""

    def __init__(self, layer1: Any) -> None:
        self._layer1 = layer1
        self._receipts: dict[str, dict[str, Any]] = {}
        self._consumed: set[str] = set()
        self._priors_used: set[str] = set()
        self._payloads: dict[str, str] = {}

    @property
    def layer1(self) -> Any:
        return self._layer1

    def _layer1_conforms(self, receipt: dict[str, Any]) -> str | None:
        """LC-KV-10/15: the layer-1 receipt was minted by the real KVInterlockRuntime through #432's evaluate_anchored
        over the pinned evaluator, the installed transport, the contract-location org ledger with an anchored node root
        and the trust anchors in force.
        None when it conforms, else the refusal cause."""
        from runtime.kv_interlock_endpoint import (KVInterlockRuntime, layer1_receipt_conformance,
                                                   pinned_decider_identity)
        if type(self._layer1) is not KVInterlockRuntime:  # noqa: E721 - a subclass could re-implement minting
            return "LAYER1_RUNTIME_NOT_KV_INTERLOCK_RUNTIME"
        why = layer1_receipt_conformance(receipt)
        if why is None and pinned_decider_identity(getattr(self._layer1, "healthy_node_evaluator", None)) is None:
            # LC-KV-10: the layer-1 runtime's decider must BE the loaded evaluate_anchored, not just name itself so
            return "LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED"
        return why

    def _verify_kv_access_receipt(self, receipt_hash: Any) -> tuple[dict[str, Any] | None, str]:
        verify = getattr(self._layer1, "verify_kv_access_receipt", None)
        if verify is None or self._layer1 is self:
            return None, "LAYER1_KV_ACCESS_RECEIPT_NOT_MINTED_BY_LAYER1"
        try:
            receipt = verify(receipt_hash)
        except Exception:
            return None, "LAYER1_KV_ACCESS_RECEIPT_NOT_MINTED_BY_LAYER1"
        if not isinstance(receipt, dict) or receipt.get("schema") != KV_ACCESS_RECEIPT_SCHEMA \
                or receipt.get("boundary") != LAYER1_BOUNDARY or receipt.get("minted_by") != "KVInterlockRuntime.handle" \
                or receipt.get("receipt_hash") != receipt_hash \
                or not isinstance(receipt.get("healthy_node_receipt"), dict) \
                or receipt["healthy_node_receipt"].get("healthy_node_established") is not True:
            return None, "LAYER1_KV_ACCESS_RECEIPT_NOT_MINTED_BY_LAYER1"
        why = self._layer1_conforms(receipt)
        if why is not None:
            return None, why
        return receipt, ""

    def verify_kv_access_receipt(self, receipt_hash: Any) -> dict[str, Any] | None:
        """A layer-1 receipt minted and still held by the layer-1 runtime, and minted under the pinned evaluator and
        the trust anchors in force (LC-KV-10/15), or None."""
        return self._verify_kv_access_receipt(receipt_hash)[0]

    def admit(self, transition: Any) -> dict[str, Any]:
        """ALLOW with a SKAP-access receipt, or a six-field FAIL_CLOSED SKAP_ACCESS_LAYER2_REFUSED."""
        from runtime.kv_interlock_endpoint import ANCHOR_REFUSAL_CODE, ENDPOINT_KIND_SCHEMA
        if not isinstance(transition, dict) or set(transition) != _TRANSITION_KEYS \
                or transition.get("schema") != TRANSITION_SCHEMA or transition.get("boundary") != LAYER2_BOUNDARY \
                or transition.get("from_role") != "KV" or transition.get("to_role") != "SKAP_VAULT":
            return layer2_refusal("INTR_KV_SKAP_TRANSITION_MALFORMED",
                                  f"submit a {TRANSITION_SCHEMA} KV->SKAP_VAULT transition (kv_skap_transition)")
        if transition["operation"] not in OPERATIONS:
            return layer2_refusal("INTR_KV_SKAP_OPERATION_UNKNOWN", f"operation must be one of {OPERATIONS}")
        for field in ("principal_ref", "subject_ref"):
            if not isinstance(transition[field], str) or not transition[field]:
                return layer2_refusal("INTR_KV_SKAP_TRANSITION_MALFORMED", f"{field} is required")
        prior = transition["prior_receipt_hash"]
        if not isinstance(prior, str) or not prior.startswith("sha256:"):
            return layer2_refusal("LAYER1_KV_ACCESS_RECEIPT_ABSENT", (
                "prior_receipt_hash must be the layer-1 KV-access receipt minted by KVInterlockRuntime.handle for a "
                "currently admitted healthy node"), predicate=PREDICATE_PRIOR_LAYER1)
        layer1_receipt, why = self._verify_kv_access_receipt(prior)
        if layer1_receipt is None:
            if why == "LAYER1_KV_ACCESS_RECEIPT_NOT_MINTED_BY_LAYER1":
                return layer2_refusal(why, (
                    f"{prior} is not a KV-access receipt held by the layer-1 runtime; a caller-minted, recomputed or "
                    "health-less layer-1 receipt is refused"), predicate=PREDICATE_PRIOR_LAYER1)
            return layer2_refusal(why, (
                f"{prior} was not minted by the real KVInterlockRuntime under the pinned healthy-node evaluator "
                "(runtime/intr_pinned, sha256:fdaa2005...1f58) reached through #432's evaluate_anchored "
                "(sha256:2d80e443...b6b8), the installed InTr transport, the contract-location org ledger with a node "
                "root evaluate_anchored admitted, and the trust anchors in force; it is refused"),
                predicate=PREDICATE_HEALTHY_NODE, failure_class="B" if why in (
                    "LAYER1_TRANSPORT_NOT_THE_INSTALLED_ONE", "LAYER1_LEDGER_NOT_BOUND_BY_CONTRACT_LOCATION",
                    ANCHOR_REFUSAL_CODE) else "C")
        if prior in self._priors_used:
            return layer2_refusal("LAYER1_KV_ACCESS_RECEIPT_ALREADY_USED", (
                f"{prior} already admitted one KV->SKAP transition; each SKAP operation needs its own DEVICE->KV "
                "InTr transition from a currently admitted healthy node"), predicate=PREDICATE_PRIOR_LAYER1)
        self._priors_used.add(prior)
        body = {
            "schema": SKAP_ACCESS_RECEIPT_SCHEMA,
            "boundary": LAYER2_BOUNDARY,
            "layer": 2,
            "hop_index": 1,
            "from_role": "KV",
            "to_role": "SKAP_VAULT",
            "minted_by": "SkapLayer2Gate.admit",
            "endpoint_kind": "SKAP_VAULT",  # Org InTr endpoint model, #432 enum
            "endpoint_kind_schema": ENDPOINT_KIND_SCHEMA,
            "layer1_endpoint_kind": layer1_receipt.get("endpoint_kind"),
            "principal_ref": transition["principal_ref"],
            "operation": transition["operation"],
            "subject_ref": transition["subject_ref"],
            "prior_receipt_hash": prior,
            "layer1_intr_receipt_ref": layer1_receipt["intr_receipt_ref"],
            "layer1_requester_node_ref": layer1_receipt["requester_node_ref"],
            "layer1_healthy_node_evaluator": layer1_receipt["healthy_node_evaluator"],
            "sequence": len(self._receipts),
            "authority_effect": "NONE",
        }
        receipt = {**body, "receipt_hash": sha256_uri(body)}
        self._receipts[receipt["receipt_hash"]] = copy.deepcopy(receipt)
        return {"disposition": "ALLOW", "skap_access_receipt": receipt, "authority_effect": "NONE"}

    def verify_skap_access_receipt(self, receipt_hash: Any) -> dict[str, Any] | None:
        receipt = self._receipts.get(receipt_hash) if isinstance(receipt_hash, str) else None
        if receipt is None or sha256_uri({k: v for k, v in receipt.items() if k != "receipt_hash"}) != receipt_hash:
            return None
        if self.verify_kv_access_receipt(receipt["prior_receipt_hash"]) is None:
            return None
        return copy.deepcopy(receipt)

    def consume(self, receipt_hash: Any, *, principal_ref: str, operation: str,
                subject_ref: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """(receipt, None) once for a matching admitted receipt, else (None, six-field refusal)."""
        receipt = self.verify_skap_access_receipt(receipt_hash)
        if receipt is None:
            return None, layer2_refusal("SKAP_ACCESS_RECEIPT_NOT_MINTED_BY_LAYER2", (
                "the SKAP Vault is reached only with a SKAP-access receipt minted by SkapLayer2Gate.admit on a "
                "verified layer-1 KV-access receipt"))
        if receipt_hash in self._consumed:
            return None, layer2_refusal("SKAP_ACCESS_RECEIPT_ALREADY_CONSUMED",
                                        "each SKAP-access receipt admits one operation; submit a new transition")
        if (receipt["principal_ref"], receipt["operation"], receipt["subject_ref"]) != (principal_ref, operation,
                                                                                       subject_ref):
            return None, layer2_refusal("SKAP_ACCESS_RECEIPT_SCOPE_MISMATCH", (
                f"the receipt admits {receipt['operation']} on {receipt['subject_ref']} for {receipt['principal_ref']}, "
                f"not {operation} on {subject_ref} for {principal_ref}"))
        self._consumed.add(receipt_hash)
        return receipt, None

    def bind_payload(self, receipt_hash: Any, payload_sha256: Any) -> bool:
        """LC-KV-07: record, once, the payload a consumed SKAP_SEALED_CREDENTIAL_APPEND receipt admitted, so a read can
        verify a stored record's provenance at this gate instead of trusting the store."""
        receipt = self.verify_skap_access_receipt(receipt_hash)
        if receipt is None or receipt_hash not in self._consumed or receipt_hash in self._payloads \
                or receipt["operation"] != "SKAP_SEALED_CREDENTIAL_APPEND" \
                or not (isinstance(payload_sha256, str) and payload_sha256.startswith("sha256:")):
            return False
        self._payloads[receipt_hash] = payload_sha256
        return True

    def verify_payload(self, receipt_hash: Any, *, principal_ref: str, subject_ref: str, payload_sha256: Any) -> bool:
        """True only when receipt_hash is a consumed append receipt of this gate, for that principal and subject, whose
        bound payload is payload_sha256. A forged or replayed record fails this."""
        receipt = self.verify_skap_access_receipt(receipt_hash)
        return bool(receipt is not None and receipt_hash in self._consumed
                    and receipt["operation"] == "SKAP_SEALED_CREDENTIAL_APPEND"
                    and receipt["principal_ref"] == principal_ref and receipt["subject_ref"] == subject_ref
                    and self._payloads.get(receipt_hash) == payload_sha256)

    def verify_access_chain(self, kv_access_receipt_hash: Any, skap_access_receipt_hash: Any) -> dict[str, Any]:
        """The access_receipt_verifier the sovereign-KV custody validator consumes: layer 2 chained to layer 1."""
        if self.verify_kv_access_receipt(kv_access_receipt_hash) is None:
            return layer2_refusal("LAYER1_KV_ACCESS_RECEIPT_NOT_MINTED_BY_LAYER1",
                                  f"{kv_access_receipt_hash!r} is not a layer-1 KV-access receipt",
                                  predicate=PREDICATE_HEALTHY_NODE, code=LAYER1_REFUSAL_CODE)
        receipt = self.verify_skap_access_receipt(skap_access_receipt_hash)
        if receipt is None or receipt["prior_receipt_hash"] != kv_access_receipt_hash:
            return layer2_refusal("LAYER2_RECEIPT_NOT_CHAINED_TO_LAYER1",
                                  "the SKAP-access receipt's prior_receipt_hash must be that layer-1 receipt",
                                  predicate=PREDICATE_PRIOR_LAYER1)
        return {"disposition": "ALLOW", "kv_access_receipt_hash": kv_access_receipt_hash,
                "skap_access_receipt_hash": skap_access_receipt_hash, "authority_effect": "NONE"}

    def export_receipts(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(r) for r in self._receipts.values()]
