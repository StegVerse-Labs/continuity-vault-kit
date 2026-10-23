"""KV-SKAP-LEDGER-LOCATION-001: KV's own receipt ledgers, behind KV's own InTr endpoint (E0, stdlib only).

Under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324). Binding rulings (Rigel via Coordination):

* StegVerse-org/.github#160 comment 6371986288: KV is independent of the ecosystem Orgs. KV keeps its own ledger at a
  KV-owned location behind its own InTr ingress/egress endpoint (endpoint_kind KV); it is never stored on any Org
  ledger ref. The SKAP Vault ledger lives inside KV and is reachable only through KV's InTr. Org/KV interactions are
  linked receipts in each side's own ledger; neither ledger is copied across.
* StegVerse-org/.github#160 comment 6372045430: KV has no hosted storage of its own. Its ledger's backing bytes live,
  sealed, in storage the KV user already owns, through a GATEWAY node (runtime.kv_gateway_storage). The external
  storage's own records never cross into KV. SVKV (ECOSYSTEM-OWN-KV-001) is backed by the StegVerse@gmail.com Google
  Drive; until it is provisioned every access is FAIL_CLOSED SVKV_GATEWAY_STORAGE_NOT_PROVISIONED.
* StegVerse-org/.github#167 comment 6372136062 (G8, provisional): the root key stays in TV/TVC custody, the SKAP Vault
  holds only wrapped data keys, and unwrapping is a custody transition.

Two ledgers, each a ``##_<name>`` storage location inside KV, in StegVerse-org/LLM-adapter#431's
repository_ledger_location key shape, values KV-owned. The ledger form is final (Rigel, #160 comment 6372216673):
encrypted, content-addressed objects in the user's storage, verified on KV's side, with signed heads and recorded
head digests guarding against rollback. Order lives in KV's ledger, never in a provider's file history.

* ``kv`` = ``01_KV_Ledger``: KV layer-1 receipts (stegverse.kv-access-receipt/v1, INTR_DEVICE_KV).
* ``skap_vault`` = ``02_SKAP_Vault_Ledger``: layer-2 receipts (stegverse.skap-access-receipt/v1, INTR_KV_SKAP), TV/TVC
  custody-issuance (stegverse.tvc.skap-custody-reference-issuance/v1, StegVerse-Labs/TVC#537) and custody-result
  receipts (stegverse.tvc.skap-custody-operation-result/v1). Read only through ``SkapLayer2Gate.receipt_ledger``.

Genesis is null (pin after observe, #162 comment 6371352606, triggered by KV's own InTr ingress). Lane B holds the
pin wiring: #431's planner and receiver still assume the org-ledger shape, recorded as six-field FAIL_CLOSED
KV_LEDGER_GENESIS_PIN_MECHANISM_ORG_HOSTED. Nothing here writes a ledger.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from runtime import kv_gateway_storage as gw

ALLOW, FAIL_CLOSED = "ALLOW", "FAIL_CLOSED"
DESIGNATED_BY = "StegVerse-Labs/continuity-vault-kit"
RULING = ("StegVerse-org/.github#160 comments 6371986288 (KV independent of the Orgs) and 6372045430 (KV only over "
          "user-owned storage via a GATEWAY node)")
KV_REPOSITORY = "KV"                    # the KV endpoint (endpoint_kind KV), not a GitHub repository
KV_ROUTE = "KV_INTR_ENDPOINT"           # the only access route to KV's ledgers
TASK = "KV-SKAP-LEDGER-LOCATION-001 under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324)"
GENESIS_CLASS = "REPOSITORY_LEDGER_INITIALIZATION"
GENESIS_PIN_TRANSITION = "REPOSITORY_LEDGER_GENESIS_PIN"
GENESIS_PIN_RULING = "StegVerse-org/.github#162 comment 6371352606 (pin after observe; here KV's own InTr ingress)"
#: StegVerse-org/LLM-adapter#431's repository_ledger_location keys, in order (contract fixture d97cd4dc)
LOCATION_SHAPE = ("repository", "ref", "namespace", "locator_form", "new_ledger_root", "designation_source",
                  "initialization", "rule", "expected_genesis_receipt_sha256", "expected_genesis_note")
CONTRACT_SCHEMA = "stegverse.repo-transition-ledger-contract/v1"
HEAD_ATTESTATION_SCHEMA = "stegverse.kv-ledger-head-attestation/v1"
HEAD_ATTESTATION_FIELDS = ("schema", "kv_ledger_location", "genesis_receipt_sha256", "head_receipt_sha256",
                           "blob_set_sha256", "appended_through")
APPEND_ROUTE = "KV_INTR_INGRESS"
HEAD_SIGNERS_SCHEMA = "stegverse.kv-ledger-head-signers/v1"
STORAGE_BINDING_SCHEMA = "stegverse.kv-gateway-storage-binding/v1"
_ROOT = Path(__file__).resolve().parents[1]
HEAD_SIGNERS_PATH = _ROOT / ".stegverse/kv-ledger/kv-ledger-head-signers.v1.json"
STORAGE_BINDING_REL = ".stegverse/kv-gateway/storage-binding.v1.json"   # what each contract's store names
HEAD_SIGNERS_REL = ".stegverse/kv-ledger/kv-ledger-head-signers.v1.json"
STORAGE_BINDING = {"path": STORAGE_BINDING_REL,
                   "sha256": "sha256:4fe1b58a216f5d4c48db670d36d4b40f6506fd1a12eea48e66f9edef6ebed869"}
CORRESPONDENCE_RULE = ("CORRESPONDENCE_NOT_STORAGE: an Org/KV interaction is two linked receipts, one in each side's "
                       "own ledger, linked by receipt_sha256; a receipt naming another ledger's repository is never "
                       "KV ledger input and no ledger is copied across the boundary")
KV_LEDGER, SKAP_VAULT_LEDGER = "kv", "skap_vault"  # consumer keys (TVC#542 org_ledger.custody_ledgers, to be rebound)
RECEIPT_LEDGERS: dict[str, dict[str, Any]] = {
    KV_LEDGER: {
        "storage_location": "01_KV_Ledger",
        "contract_path": ".stegverse/receipt-ledgers/01_KV_Ledger.contract.json",
        "contract_sha256": "sha256:f8c3f6e457dc1208e1ec8f7e50fb7851905816c3894cb694be038b0f0b88025b",
        "repository": "KV/01_KV_Ledger",
        "carries": ["stegverse.kv-access-receipt/v1 (L1)"],
        "read_by": "runtime.kv_interlock_endpoint.KVInterlockRuntime (layer 1)",
        "not_designated_code": "KV_RECEIPT_NAMESPACE_NOT_DESIGNATED",
        "endpoint_kind": "KV",
        "via_kv_intr_only": False,
    },
    SKAP_VAULT_LEDGER: {
        "storage_location": "02_SKAP_Vault_Ledger",
        "contract_path": ".stegverse/receipt-ledgers/02_SKAP_Vault_Ledger.contract.json",
        "contract_sha256": "sha256:963731204b2b64b8833ee12a364d969704aa23ebcd2c12f8c08edf6c717ad087",
        "repository": "KV/02_SKAP_Vault_Ledger",
        "carries": ["stegverse.skap-access-receipt/v1 (L2)",
                    "stegverse.tvc.skap-custody-reference-issuance/v1 (TVC#537)",
                    "stegverse.tvc.skap-custody-operation-result/v1"],
        "read_by": "runtime.kv_skap_layer2.SkapLayer2Gate.receipt_ledger (layer 2, via KV's InTr only)",
        "not_designated_code": "CUSTODY_RECEIPT_NAMESPACE_NOT_DESIGNATED",
        "endpoint_kind": "SKAP_VAULT",
        "via_kv_intr_only": True,
    },
}
PREDICATE = "KV_RECEIPTS_READ_BACK_FROM_KV_OWN_LEDGER_ONLY"
RETRY = ("runtime.kv_receipt_ledgers.read_receipt_ledger('kv', <GatewayStorageAdapter>, <head attestation>, "
         "<BlobOpener>); skap_vault only via runtime.kv_skap_layer2.SkapLayer2Gate.receipt_ledger")
PIN_MECHANISM_CODE = "KV_LEDGER_GENESIS_PIN_MECHANISM_ORG_HOSTED"


def _sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _refuse(which: str, code: str, klass: str, repair: str, next_attempt: str, detail: str,
            owner: str = TASK, predicate: str = PREDICATE, retry: str = RETRY) -> dict[str, Any]:
    spec = RECEIPT_LEDGERS.get(which) or {}
    return {"disposition": FAIL_CLOSED, "receipt_ledger": which, "storage_location": spec.get("storage_location"),
            "failure_code": code, "failure_class": klass, "failed_predicate": predicate,
            "required_evidence_or_repair": repair, "retry_entrypoint": retry, "owning_existing_goal": owner,
            "next_attempt": next_attempt, "detail": detail, "ledger_written": False, "authority_effect": "NONE"}


def pin_mechanism_org_hosted(which: str) -> dict[str, Any]:
    """Six-field FAIL_CLOSED: the only genesis-pin mechanism is org-hosted (Lane B holds KV wiring)."""
    return _refuse(which, PIN_MECHANISM_CODE, "B",
                   f"a per-endpoint {GENESIS_PIN_TRANSITION} planner and receiver from Lane B that accept a KV-owned "
                   "location contract and KV's own InTr ingress as the trigger; StegVerse-org/LLM-adapter#431 "
                   "@66a098fa's planner (contract_shape_failure) and receiver still require StegVerse-org/.github "
                   "refs/stegverse/organization-ledger and LLM-adapter's location",
                   "when Lane B posts the per-endpoint fix on StegVerse-org/.github#162; no KV wiring before then",
                   f"{RECEIPT_LEDGERS[which]['storage_location']}: no mechanism can pin a KV-owned genesis yet",
                   owner="StegVerse-org/.github#162 / StegVerse-org/LLM-adapter#431 (Lane B)",
                   predicate="GENESIS_PIN_MECHANISM_ACCEPTS_KV_OWNED_LOCATION",
                   retry=f"StegVerse-org/LLM-adapter#431 {GENESIS_PIN_TRANSITION} (per-endpoint form, Lane B)")


def _not_pinned(which: str, location: str) -> dict[str, Any]:
    return _refuse(which, "KV_LEDGER_GENESIS_NOT_PINNED", "B",
                   f"repository_ledger_location.expected_genesis_receipt_sha256 in "
                   f"{RECEIPT_LEDGERS[which]['contract_path']}, written by the {GENESIS_PIN_TRANSITION} transition "
                   f"from the {GENESIS_CLASS} genesis KV reads back at {location}, triggered by KV's own InTr "
                   f"ingress; never by hand and never invented ({GENESIS_PIN_RULING})",
                   f"when the {GENESIS_PIN_TRANSITION} transition runs on KV's observed genesis, after "
                   f"{PIN_MECHANISM_CODE} clears (Lane B per-endpoint fix, #162); event-driven, no cron, no polling",
                   f"{location}: expected_genesis_receipt_sha256 is null; any store can mint a genesis, so none is "
                   "accepted", owner=f"{TASK}; dependency owner Lane B (#162 / LLM-adapter#431)")


def storage_binding() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """The digest-pinned gateway storage binding, or a six-field refusal."""
    repair = f"{STORAGE_BINDING['path']} at {STORAGE_BINDING['sha256']}"
    try:
        raw = (_ROOT / STORAGE_BINDING["path"]).read_bytes()
    except OSError as exc:
        return None, gw.refusal("KV_GATEWAY_STORAGE_BINDING_UNREADABLE", "D", "KV_GATEWAY_STORAGE_BOUND", repair,
                                "when the binding is committed", f"unreadable: {exc}")
    if _sha_bytes(raw) != STORAGE_BINDING["sha256"]:
        return None, gw.refusal("KV_GATEWAY_STORAGE_BINDING_CHANGED", "C", "KV_GATEWAY_STORAGE_BOUND", repair,
                                "on an admitted change that re-pins the binding digest",
                                f"the binding is {_sha_bytes(raw)}")
    binding = json.loads(raw)
    if binding.get("schema") != STORAGE_BINDING_SCHEMA or binding.get("external_records_cross_into_kv") is not False \
            or binding.get("contents") != "SEALED_BLOBS_ONLY" or binding.get("storage_node_endpoint_kind") != "GATEWAY":
        return None, gw.refusal("KV_GATEWAY_STORAGE_BINDING_CHANGED", "C", "KV_GATEWAY_STORAGE_BOUND", repair,
                                "on a well-formed binding", "the binding is not a sealed-blob GATEWAY binding")
    if not binding.get("gateway_storage_adapter_ref") or not binding.get("gateway_node_id"):
        return binding, gw.not_provisioned(f"{binding.get('kv_deployment')}: gateway_storage_adapter_ref and "
                                           "gateway_node_id are null (backing storage "
                                           f"{(binding.get('backing_storage') or {}).get('state')})")
    return binding, None


STORE_TYPE = "GATEWAY_ENCRYPTED_BLOB"   # Lane B's per-endpoint store_type for KV and SKAP_VAULT (#162 comment 6372170864)
DESIGNATION_SHAPE = ("endpoint_id", "endpoint_kind", "store", "genesis_class", "expected_genesis_receipt_sha256",
                     "head_signers_path", "append_route", "refuses")
STORE_SHAPE = ("store_type", "location", "adapter_interface", "adapter_ref", "storage_binding_path",
               "content_addressing", "head_pointer", "plaintext", "external_records_cross_into_kv")
ORG_MARKERS = ("GIT_REF", "StegVerse-org/.github", "refs/stegverse/organization-ledger", "repository-ledger/")


def _org_designation(contract: Any) -> str | None:
    """Why this contract designates an org (or any git-ref) store, or None. Checked on the structured fields."""
    if not isinstance(contract, Mapping):
        return None
    loc = contract.get("repository_ledger_location") if isinstance(contract.get("repository_ledger_location"),
                                                                   Mapping) else {}
    ld = contract.get("ledger_designation") if isinstance(contract.get("ledger_designation"), Mapping) else {}
    store = ld.get("store") if isinstance(ld.get("store"), Mapping) else {}
    values = [loc.get("repository"), loc.get("ref"), loc.get("namespace"), store.get("store_type"),
              store.get("location"), store.get("adapter_ref"), ld.get("endpoint_id"),
              *(store.get(k) for k in ("repository", "ref", "namespace"))]
    for v in values:
        if isinstance(v, str) and any(m in v for m in ORG_MARKERS):
            return f"the contract designates {v!r}"
    if any(k in store for k in ("repository", "ref", "namespace")):
        return "the store carries git-ref fields (repository/ref/namespace)"
    return None


def designation(which: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """(designation, None) from the committed, digest-pinned contract, or (None, six-field refusal). Never caller-chosen."""
    spec = RECEIPT_LEDGERS.get(which)
    if spec is None:
        return None, _refuse(which, "RECEIPT_LEDGER_UNKNOWN", "A", f"one of {sorted(RECEIPT_LEDGERS)}",
                             "on the corrected call", f"{which!r} is not a designated receipt ledger")
    code = spec["not_designated_code"]
    repair = (f"{spec['contract_path']} in #431's repository_ledger_location key shape at {spec['contract_sha256']}, "
              f"designating {KV_REPOSITORY}#{KV_ROUTE}:{spec['storage_location']}")
    try:
        raw = (_ROOT / spec["contract_path"]).read_bytes()
    except OSError as exc:
        return None, _refuse(which, code, "D", repair, "when the designation is committed", f"unreadable: {exc}")
    if _sha_bytes(raw) != spec["contract_sha256"]:
        return None, _refuse(which, code, "C", repair, "on an admitted change that re-pins the contract digest",
                             f"{spec['contract_path']} is {_sha_bytes(raw)}, the pin is {spec['contract_sha256']}")
    try:
        contract = json.loads(raw)
    except ValueError:
        return None, _refuse(which, code, "C", repair, "on a well-formed contract", "the contract is not JSON")
    org = _org_designation(contract)
    if org:
        return None, _refuse(which, "KV_LEDGER_DESIGNATED_ON_ORG_LEDGER", "C",
                             f"a {STORE_TYPE} designation of KV's own location {spec['storage_location']}; an org "
                             "designation (GIT_REF, StegVerse-org/.github, refs/stegverse/organization-ledger) is "
                             "refused for KV and SKAP_VAULT", "never for an org designation; on a KV-owned contract",
                             org, predicate="INDEPENDENT_ENDPOINT_LEDGER_NOT_ORG_HOSTED")
    loc = contract.get("repository_ledger_location") if isinstance(contract, Mapping) else None
    if not isinstance(loc, Mapping) or tuple(loc) != LOCATION_SHAPE or contract.get("schema") != CONTRACT_SCHEMA \
            or contract.get("repository") != spec["repository"] or loc.get("repository") != KV_REPOSITORY \
            or loc.get("ref") != KV_ROUTE or loc.get("namespace") != spec["storage_location"] \
            or loc.get("new_ledger_root") is not True:
        return None, _refuse(which, code, "C", repair, "on a KV-owned contract in #431's shape",
                             "the contract is not a KV-owned repository_ledger_location for this ledger")
    ld = contract.get("ledger_designation")
    store = ld.get("store") if isinstance(ld, Mapping) else None
    genesis = loc.get("expected_genesis_receipt_sha256")
    if not isinstance(store, Mapping) or tuple(ld) != DESIGNATION_SHAPE or tuple(store) != STORE_SHAPE \
            or ld.get("endpoint_id") != spec["repository"] or ld.get("endpoint_kind") != spec["endpoint_kind"] \
            or store.get("store_type") != STORE_TYPE or store.get("location") != spec["storage_location"] \
            or store.get("plaintext") is not False or store.get("external_records_cross_into_kv") is not False \
            or store.get("storage_binding_path") != STORAGE_BINDING_REL or ld.get("genesis_class") != GENESIS_CLASS \
            or ld.get("expected_genesis_receipt_sha256") != genesis \
            or ld.get("head_signers_path") != HEAD_SIGNERS_REL \
            or not str(ld.get("append_route", "")).startswith(APPEND_ROUTE):
        return None, _refuse(which, code, "C", repair, "on a KV-owned contract with a per-endpoint ledger_designation",
                             f"ledger_designation is not the {STORE_TYPE} designation for this ledger")
    pinned = isinstance(genesis, str) and len(genesis) == 71 and genesis.startswith("sha256:")
    return {"receipt_ledger": which, "ledger_designation": dict(ld), "storage_location": spec["storage_location"], "repository": spec["repository"],
            "repository_ledger_location": dict(loc), "kv_endpoint": loc["repository"], "route": loc["ref"],
            "namespace": loc["namespace"], "location": f"{loc['repository']}#{loc['ref']}:{loc['namespace']}",
            "contract_path": spec["contract_path"], "contract_sha256": spec["contract_sha256"],
            "via_kv_intr_only": spec["via_kv_intr_only"],
            "expected_genesis_receipt_sha256": genesis if pinned else None}, None


def receipt_ledger_binding(which: str) -> dict[str, Any]:
    """What a minted receipt records about the ledger it belongs on (where, under which contract, pinned or not)."""
    d, refusal = designation(which)
    if refusal:
        return {"receipt_ledger": which, "disposition": FAIL_CLOSED, "failure_code": refusal["failure_code"]}
    out = {k: d[k] for k in ("receipt_ledger", "storage_location", "repository", "location", "contract_sha256",
                             "expected_genesis_receipt_sha256")}
    out["disposition"] = "DESIGNATED_GENESIS_PINNED" if d["expected_genesis_receipt_sha256"] else FAIL_CLOSED
    if not d["expected_genesis_receipt_sha256"]:
        out["failure_code"] = "KV_LEDGER_GENESIS_NOT_PINNED"
    return out


def _pinned():
    from runtime.kv_interlock_endpoint import load_pinned_intr  # lazy: kv_interlock_endpoint imports this module
    return load_pinned_intr()


def load_head_signers() -> list[dict[str, Any]]:
    """KV's own published ledger head attester references (TV/TVC pattern, TVC#542); empty until published."""
    try:
        published = json.loads(HEAD_SIGNERS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(published, Mapping) or published.get("schema") != HEAD_SIGNERS_SCHEMA:
        return []
    return [dict(k) for k in published.get("signers") or []
            if isinstance(k, Mapping) and k.get("signs") == "KV_LEDGER_HEAD"]


def blob_set_sha256(addresses: list[str]) -> str:
    return _sha_bytes("\n".join(sorted(addresses)).encode("ascii"))


def head_attestation_body(location: str, genesis_sha: str, head_sha: str, blob_set: str) -> dict[str, Any]:
    """KV's ledger head attestation body for this location. Pure."""
    return {"schema": HEAD_ATTESTATION_SCHEMA, "kv_ledger_location": location, "genesis_receipt_sha256": genesis_sha,
            "head_receipt_sha256": head_sha, "blob_set_sha256": blob_set, "appended_through": APPEND_ROUTE}


def _head_failure(modules: dict[str, Any], which: str, location: str, attestation: Any, genesis_sha: str,
                  head_sha: str, blob_set: str) -> dict[str, Any] | None:
    signers = load_head_signers()
    if not signers:
        return _refuse(which, "KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED", "B",
                       "a TV/TVC-custodied Ed25519 KV_LEDGER_HEAD key published in "
                       ".stegverse/kv-ledger/kv-ledger-head-signers.v1.json (the TVC#542 head-signer pattern, "
                       "applied to KV's own ledger)", "when TV/TVC publishes KV's head attester; event-driven",
                       f"{location}: no KV ledger head attester is published, so no head is authenticated",
                       owner=f"{TASK}; dependency owner TV/TVC + Lane C (TVC#542)")
    not_auth = "KV_LEDGER_HEAD_NOT_AUTHENTICATED"
    repair = f"a {HEAD_ATTESTATION_SCHEMA} by a published attester over exactly this genesis, head and blob set"
    if not isinstance(attestation, Mapping):
        return _refuse(which, not_auth, "C", repair, "with KV's ingress attestation", "no head attestation")
    body = {k: attestation.get(k) for k in HEAD_ATTESTATION_FIELDS}
    if body != head_attestation_body(location, genesis_sha, head_sha, blob_set):
        return _refuse(which, not_auth, "C", repair, "with KV's ingress attestation",
                       f"the attestation names another location, genesis, head or blob set (head {head_sha})")
    key = next((k for k in signers if k.get("key_id") == attestation.get("key_id")), None)
    try:
        public = base64.b64decode(key.get("public_key_b64"), validate=True) if key else None
        signature = base64.b64decode(attestation.get("signature_b64"), validate=True)
    except (binascii.Error, ValueError, TypeError):
        public, signature = None, None
    message = HEAD_ATTESTATION_SCHEMA.encode("utf-8") + b"\n" + modules["healthy_node_evaluator"].canon(body)
    if public is None or len(public) != 32 or signature is None or len(signature) != 64 \
            or not modules["ed25519_verify"].verify(public, message, signature):
        return _refuse(which, not_auth, "C", repair, "with KV's ingress attestation",
                       "the attestation does not verify under a published KV_LEDGER_HEAD key")
    return None


def _six(which: str, r: Mapping[str, Any]) -> dict[str, Any]:
    return {**r, "receipt_ledger": which, "storage_location": RECEIPT_LEDGERS[which]["storage_location"]}


def _foreign(which: str, detail: str) -> dict[str, Any]:
    return _refuse(which, "KV_LEDGER_FOREIGN_RECORD_REFUSED", "C",
                   f"only KV's own receipts for {RECEIPT_LEDGERS[which]['repository']}, computed on KV's side "
                   f"({CORRESPONDENCE_RULE})", "never: a foreign or external record is not KV ledger input", detail,
                   predicate="EXTERNAL_RECORDS_NEVER_CROSS_INTO_KV")


def _via_kv_intr_failure(d: Mapping[str, Any], via_kv_intr: Any) -> str | None:
    if not d["via_kv_intr_only"]:
        return None
    if not isinstance(via_kv_intr, Mapping) or via_kv_intr.get("schema") != "stegverse.kv-access-receipt/v1" \
            or via_kv_intr.get("receipt_ledger") != receipt_ledger_binding(KV_LEDGER):
        return "no layer-1 KV-access receipt minted by KV's InTr ingress was presented by SkapLayer2Gate"
    return None


def _read(which: str, gateway: Any, head_attestation: Any, opener: Any, via_kv_intr: Any,
          recorded_head: Any = None) -> dict[str, Any]:
    d, refusal = designation(which)
    if refusal:
        return refusal
    why = _via_kv_intr_failure(d, via_kv_intr)
    if why:
        return _refuse(which, "SKAP_VAULT_LEDGER_NOT_VIA_KV_INTR", "A",
                       "read the SKAP Vault ledger only through runtime.kv_skap_layer2.SkapLayer2Gate.receipt_ledger "
                       "with a layer-1 KV-access receipt the KV runtime minted (two-layer access rule)",
                       "on the corrected call, through KV's InTr", why, predicate="SKAP_VAULT_REACHED_ONLY_VIA_KV_INTR")
    binding, refused = storage_binding()
    if refused:
        return _six(which, refused)
    if d["expected_genesis_receipt_sha256"] is None:
        return _not_pinned(which, d["location"])
    if getattr(gateway, "adapter_ref", None) != binding["gateway_storage_adapter_ref"]:
        return _refuse(which, "KV_GATEWAY_ADAPTER_NOT_THE_BOUND_ONE", "C",
                       f"the gateway storage adapter {binding['gateway_storage_adapter_ref']} named by the binding",
                       "with the bound adapter", f"adapter {getattr(gateway, 'adapter_ref', None)!r}")
    modules, why = _pinned()
    if modules is None:
        return _refuse(which, "PINNED_INTR_CODE_UNAVAILABLE", "C", "the digest-pinned #432 modules", "on re-vendor", why)
    store, ns = gw.GatewayStore(gateway), d["namespace"]
    addresses, failed = store.list_blobs(ns)
    if failed:
        return _six(which, failed)
    if not isinstance(opener, gw.BlobOpener):
        opener = gw.NullBlobOpener()
    receipts: list[dict[str, Any]] = []
    by_address: dict[str, dict[str, Any]] = {}
    for address in addresses:
        blob, failed = store.get_blob(ns, address)
        if failed:
            return _six(which, failed)
        try:
            plain = opener.open(blob)
        except gw.GatewayStorageRefused as exc:
            return _six(which, exc.refusal)
        try:
            receipt = json.loads(plain.decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, ValueError):
            return _foreign(which, f"blob {address} does not open to a receipt")
        if not isinstance(receipt, dict) or receipt.get("repository") != d["repository"] \
                or not isinstance(receipt.get("receipt_sha256"), str):
            return _foreign(which, f"blob {address} opens to a record for "
                                   f"{receipt.get('repository') if isinstance(receipt, dict) else type(receipt).__name__}")
        receipts.append(receipt)
        by_address[address] = receipt
    hne = modules["healthy_node_evaluator"]
    referenced = {r.get("previous_receipt_sha256") for r in receipts}
    heads = [r["receipt_sha256"] for r in receipts if r["receipt_sha256"] not in referenced]
    unreadable = "KV_LEDGER_UNREADABLE"
    if len(heads) != 1:
        return _refuse(which, unreadable, "C", f"one KV-computed chain at {ns}", "on an intact chain",
                       f"{len(heads)} chain heads among {len(receipts)} receipts")
    pointer, failed = store.head(ns)
    if failed:
        return _six(which, failed)
    if pointer not in by_address or by_address[pointer]["receipt_sha256"] != heads[0]:
        return _refuse(which, unreadable, "C", f"the append-only head pointer at {ns}/HEAD on KV's computed head",
                       "on an intact chain", f"head pointer {pointer!r} is not the blob of head {heads[0]}")
    with tempfile.TemporaryDirectory(prefix="kv-ledger-readback-") as scratch:
        (Path(scratch) / "receipts").mkdir()
        for r in receipts:
            (Path(scratch) / "receipts" / (r["receipt_sha256"].split(":")[-1] + ".json")).write_text(
                json.dumps(r), encoding="utf-8")
        (Path(scratch) / "HEAD.json").write_text(json.dumps({"receipt_sha256": heads[0]}), encoding="utf-8")
        chain, failure, detail = hne.read_chain(Path(scratch), d["repository"])
    if failure or len(chain) != len(receipts) or chain[-1].get("transition_class") != GENESIS_CLASS \
            or chain[-1].get("previous_receipt_sha256") is not None:
        return _refuse(which, unreadable, "C", f"one KV-computed chain at {ns} back to its {GENESIS_CLASS} genesis",
                       "on an intact chain", f"{failure or 'stray or missing receipts'} {detail}")
    if chain[-1]["receipt_sha256"] != d["expected_genesis_receipt_sha256"]:
        return _refuse(which, "KV_LEDGER_GENESIS_MISMATCH", "C", f"the {ns} genesis must be the contract's pin",
                       "never: a store that minted its own genesis is not this ledger",
                       f"the store's genesis is {chain[-1]['receipt_sha256']}")
    if recorded_head is not None and recorded_head not in {r["receipt_sha256"] for r in chain}:
        # rollback guard: the head is monotonic; a head digest already recorded (e.g. in an Org's correspondence
        # receipt, or the last verified local receipt) must still be on the chain read back now
        return _refuse(which, "KV_LEDGER_ROLLBACK_DETECTED", "C",
                       f"a chain at {ns} that still contains the recorded head {recorded_head}",
                       "never on this store state: KV marks it UNKNOWN and fails closed",
                       f"the read-back head {chain[0]['receipt_sha256']} does not descend from {recorded_head}",
                       predicate="KV_LEDGER_HEAD_MONOTONIC")
    blob_set = blob_set_sha256(addresses)
    head = _head_failure(modules, which, d["location"], head_attestation, chain[-1]["receipt_sha256"],
                         chain[0]["receipt_sha256"], blob_set)
    if head:
        return head
    return {**receipt_ledger_binding(which), "disposition": ALLOW, "head_receipt_sha256": chain[0]["receipt_sha256"],
            "blob_set_sha256": blob_set, "chain": chain, "authority_effect": "NONE"}


def read_receipt_ledger(which: str, gateway: Any = None, head_attestation: Any = None,
                        opener: Any = None, recorded_head: Any = None) -> dict[str, Any]:
    """Read one KV ledger back from KV's own location. ALLOW carries the chain (newest first). Read-only.

    Refusal order: not designated; SKAP Vault not reached via KV's InTr (always, on this entrypoint); gateway storage
    not provisioned; genesis not pinned; adapter not the bound one; gateway values (location, content address,
    sealing, external records); blob key not custodied; foreign record; chain; genesis mismatch; head not
    authenticated (KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED while no attester is published). ``recorded_head`` is a head
    receipt digest already recorded elsewhere (an Org-recorded correspondence digest or KV's last verified receipt):
    a read-back chain that no longer contains it is KV_LEDGER_ROLLBACK_DETECTED."""
    return _read(which, gateway, head_attestation, opener, None, recorded_head)


def receipt_on_ledger(which: str, receipt_sha256: Any, gateway: Any = None, head_attestation: Any = None,
                      opener: Any = None, *, _read_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """ALLOW only if a receipt whose evidence carries receipt_sha256 is on the read-back chain of this ledger."""
    read = dict(_read_result) if _read_result is not None else read_receipt_ledger(which, gateway, head_attestation,
                                                                                   opener)
    if read["disposition"] != ALLOW:
        return read
    for r in read["chain"]:
        evidence = r.get("evidence") if isinstance(r.get("evidence"), Mapping) else {}
        if evidence.get("receipt_sha256") == receipt_sha256 or evidence.get("receipt_hash") == receipt_sha256:
            return {"disposition": ALLOW, "receipt_ledger": which, "ledger_receipt_sha256": r["receipt_sha256"],
                    "head_receipt_sha256": read["head_receipt_sha256"], "authority_effect": "NONE"}
    return _refuse(which, "RECEIPT_NOT_ON_DESIGNATED_LEDGER", "C",
                   f"a receipt on {read['location']} whose evidence carries {receipt_sha256}",
                   "after KV appends it through its own InTr ingress", f"{receipt_sha256} is not on the read-back chain")


SIX_FIELDS = ("failure_code", "failure_class", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
              "owning_existing_goal", "next_attempt")


def receipt_ledger_prerequisites() -> list[dict[str, Any]]:
    """One row per KV ledger for the finish point, with every production prerequisite still FAIL_CLOSED."""
    rows = []
    _, storage_refusal = storage_binding()
    for which in RECEIPT_LEDGERS:
        d, refusal = designation(which)
        blocking: list[dict[str, Any]] = []
        if refusal:
            blocking.append(refusal)
        if storage_refusal:
            blocking.append(_six(which, storage_refusal))
        if d and d["expected_genesis_receipt_sha256"] is None:
            blocking += [_not_pinned(which, d["location"]), pin_mechanism_org_hosted(which)]
        if not load_head_signers():
            blocking.append(_head_failure({}, which, d["location"] if d else which, None, "", "", ""))
        row = {"prerequisite": "KV_LEDGER_DESIGNATED_PROVISIONED_AND_GENESIS_PINNED", "receipt_ledger": which,
               "storage_location": RECEIPT_LEDGERS[which]["storage_location"],
               "contract_sha256": RECEIPT_LEDGERS[which]["contract_sha256"], "tracked_by": TASK}
        if d:
            row["location"] = d["location"]
        if blocking:
            row.update({"disposition": FAIL_CLOSED, **{k: blocking[0][k] for k in SIX_FIELDS},
                        "fail_closed": [{k: b[k] for k in SIX_FIELDS} for b in blocking]})
        else:
            row.update(disposition=ALLOW, expected_genesis_receipt_sha256=d["expected_genesis_receipt_sha256"])
        rows.append(row)
    return rows


def custody_ledgers_config() -> dict[str, Any]:
    """The designations for consumers (TVC#540/#541/#542 rebind, Lane C): {"kv"|"skap_vault": {"carries": [...],
    "repository_ledger_location": {#431 key shape, KV-owned values}, "storage_binding": {...}}}. A ledger whose contract
    is not designated is given with repository_ledger_location null."""
    binding, _ = storage_binding()
    out: dict[str, Any] = {}
    for which, spec in RECEIPT_LEDGERS.items():
        d, _ = designation(which)
        out[which] = {"carries": list(spec["carries"]), "storage_location": spec["storage_location"],
                      "contract_path": spec["contract_path"], "contract_sha256": spec["contract_sha256"],
                      "via_kv_intr_only": spec["via_kv_intr_only"],
                      "repository_ledger_location": d["repository_ledger_location"] if d else None,
                      "storage_binding": {"path": STORAGE_BINDING["path"], "sha256": STORAGE_BINDING["sha256"],
                                          "gateway_storage_adapter_ref":
                                              (binding or {}).get("gateway_storage_adapter_ref")}}
    return out


__all__ = ["CORRESPONDENCE_RULE", "KV_LEDGER", "SKAP_VAULT_LEDGER", "RECEIPT_LEDGERS", "custody_ledgers_config",
           "designation", "load_head_signers", "pin_mechanism_org_hosted", "read_receipt_ledger",
           "receipt_ledger_binding", "receipt_ledger_prerequisites", "receipt_on_ledger", "storage_binding"]
