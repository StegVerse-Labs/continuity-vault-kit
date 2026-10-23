"""KV-SKAP-LEDGER-LOCATION-001: KV's own recorded receipt chains, behind KV's own InTr endpoint (E0, stdlib only).

Under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324). Governing correction: StegVerse-org/.github#167
comment 6372442705, which defers to the documented model in this repository (@bcc2d75):

* docs/KV_AI_PERSISTENCE_LAYOUTS.md / specs/kv-ai-persistence-layouts.v1.json: STEGVERSE_KV (logical root
  ``_StegVerse/``, receipt_root ``_StegVerse/Receipts``) is the ecosystem's own KV. Provider != authority.
* KV_STORAGE_ENDPOINT_V2_MIRROR_HANDOFF.md / runtime/kv_storage_provider_adapter.py: ``KV instance -> storage
  endpoint -> access adapter -> location``. STEGVERSE_KV is the existing Google Drive KV #2 lineage
  SITE-CLOUD-KV-4347408852127319cbda574f02e03edb, still PENDING_INTERLOCK_INTR (not regenerated, rehashed or treated
  as executed). This module adds no adapter interface: it reuses the documented descriptor and registry.
* README "Safety": the KV baseline file structure is not encryption; ciphertext lives only behind SKAP
  (``_Vault/SKAP``). The receipt chains are recorded receipts, not encrypted objects.
* SKAP_PORTABLE_ENVELOPE_V2_MIRROR_HANDOFF.md: the root key is wrapped at
  ``_Vault/SKAP/Root/wrapped-root-envelope.json`` and unwrapped only by the owner-only recovery secret. Its line 55
  (@d749bb2) matches CAPTURE's two-event crossing model: the SKAP chain genesis is recorded in KV storage and a
  digest-only InTr crossing receipt (pointer/digest plus SUPPLIED_HB_EPOCH) on the Org ledger is the exactly-once
  fence for that crossing only (``GENESIS_CROSSING``). SKAP genesis is never held on the Org ledger.

Two chains, each designated in StegVerse-org/LLM-adapter#431's repository_ledger_location key shape (values KV-owned)
plus a per-endpoint ``ledger_designation`` in #431 @a2237bc3 endpoint_ledger_designation's field names, with one
store of the proposed ``store_type`` KV_STORAGE_ENDPOINT:

* ``kv``: ``_StegVerse/Receipts``. KV layer-1 receipts (stegverse.kv-access-receipt/v1, INTR_DEVICE_KV).
* ``skap_vault``: ``_Vault/SKAP/Receipts``. Layer-2 receipts (stegverse.skap-access-receipt/v1, INTR_KV_SKAP),
  TV/TVC custody-reference issuance (TVC#537) and custody-result receipts. Read only through
  ``SkapLayer2Gate.receipt_ledger``.

Read-back layout: ``<location>/HEAD.json`` + ``<location>/receipts/<sha256 hex>.json``, walked by the vendored #432
``healthy_node_evaluator.read_chain`` (unchanged). Nothing here writes a receipt chain.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from runtime import kv_storage_provider_adapter as spa

ALLOW, FAIL_CLOSED, DENY = "ALLOW", "FAIL_CLOSED", "DENY"
CORRECTION = "StegVerse-org/.github#167 comment 6372442705"
KV_REPOSITORY = "STEGVERSE_KV"          # the KV class/instance (logical root _StegVerse/), not a GitHub repository
KV_ROUTE = "KV_INTR_ENDPOINT"           # the only access route to KV's receipt chains
KV2_REQUEST_ID = "SITE-CLOUD-KV-4347408852127319cbda574f02e03edb"
KV2_GOVERNANCE_STATE = "PENDING_INTERLOCK_INTR"   # KV_STORAGE_ENDPOINT_V2_MIRROR_HANDOFF.md, as documented @bcc2d75
TASK = "KV-SKAP-LEDGER-LOCATION-001 under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324)"
KV2_GOAL = (f"KV-CONNECTION-REVALIDATION-WORKER-001 (KV #2 request {KV2_REQUEST_ID}; SV-KV-AI-PERSISTENCE-001, "
            "TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001)")
GENESIS_CLASS = "REPOSITORY_LEDGER_INITIALIZATION"
#: StegVerse-org/LLM-adapter#431's repository_ledger_location keys, in order (contract fixture d97cd4dc)
LOCATION_SHAPE = ("repository", "ref", "namespace", "locator_form", "new_ledger_root", "designation_source",
                  "initialization", "rule", "expected_genesis_receipt_sha256", "expected_genesis_note")
CONTRACT_SCHEMA = "stegverse.repo-transition-ledger-contract/v1"
#: LLM-adapter#431 @a2237bc3 llm_adapter/endpoint_ledger_designation.py (sha256:cc03dfdc...) field names
DESIGNATION_SCHEMA = "stegverse.endpoint-ledger-designation/v1"
DESIGNATION_KEYS = ("schema", "endpoint_id", "endpoint_kind", "stores", "provider_selection", "genesis_class",
                    "expected_genesis_receipt_sha256", "head_signer_source", "rollback_watermark_source")
STORE_TYPE = "KV_STORAGE_ENDPOINT"      # proposed to Lane B (#167 comment 6372442705: storage endpoint v2 names only)
STORE_KEYS = ("store_type", "storage_endpoint_schema", "provider_id", "access_adapter", "kv_class", "kv_request_id",
              "location")
#: The rollback watermark comes from KV's own recorded receipt chain head, the name kv_ledger_head_signer signs
#: (TVC#542 @4c2504da): KV is independent of the Orgs (Coordination's provisional class A repair, StegVerse-org/.github#167).
WATERMARK_SOURCE = "KV_RECORDED_RECEIPT_CHAIN_HEAD"
#: The Org's side of a crossing may appear only as an optional digest-only cross-check, never as the watermark source.
ORG_CROSS_CHECK_SOURCE = "ORG_LEDGER_LINKED_RECEIPTS_ENDPOINT_HEAD"
CROSS_CHECK_ROLE = "DIGEST_ONLY_CROSS_CHECK_NEVER_WATERMARK"
ORG_SOURCED_CODE = "KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED"
HEAD_ATTESTATION_SCHEMA = "stegverse.kv-ledger-head-attestation/v1"
HEAD_ATTESTATION_FIELDS = ("schema", "endpoint_id", "store_location", "genesis_receipt_sha256", "head_receipt_sha256",
                           "signer_role")
SIGNER_ROLE = "kv_ledger_head_signer"
#: StegVerse-Labs/TVC#542 @4c2504da kv_ledger_head_signer.signs: the head digest the InTr crossing receipt carries to the
#: Org ledger (digest-only, with SUPPLIED_HB_EPOCH); here it is head_receipt_sha256 of the head attestation
HEAD_DIGEST_NAME = "KV_RECORDED_RECEIPT_CHAIN_HEAD"
HEAD_SIGNERS_SCHEMA = "stegverse.published-public-key-references/v1"
_ROOT = Path(__file__).resolve().parents[1]
HEAD_SIGNERS_REL = ".stegverse/node-ledger/kv-ledger-head-signers.v1.json"
HEAD_SIGNERS_PATH = _ROOT / HEAD_SIGNERS_REL
CORRESPONDENCE_RULE = ("CORRESPONDENCE_NOT_STORAGE: an Org/KV interaction is two linked receipts, one in each side's "
                       "own chain, linked by receipt_sha256; a receipt naming another repository is never KV input "
                       "and neither ledger is copied across the boundary")
ORG_MARKERS = ("GIT_REF", "StegVerse-org/.github", "refs/stegverse/organization-ledger",
               "repository-ledger/")
KV_LEDGER, SKAP_VAULT_LEDGER = "kv", "skap_vault"  # consumer keys (TVC#542 org_ledger.custody_ledgers, to be rebound)
RECEIPT_LEDGERS: dict[str, dict[str, Any]] = {
    KV_LEDGER: {
        "storage_location": "_StegVerse/Receipts",
        "contract_path": ".stegverse/receipt-chains/stegverse-kv-receipts.contract.json",
        "contract_sha256": "sha256:610377f21f7ae6e4953fd2324473c00bbe37cc7896f99e35ea572ead035dfaf2",
        "repository": "STEGVERSE_KV:_StegVerse/Receipts",
        "carries": ["stegverse.kv-access-receipt/v1 (L1)"],
        "read_by": "runtime.kv_interlock_endpoint.KVInterlockRuntime (layer 1)",
        "not_designated_code": "KV_RECEIPT_CHAIN_NOT_DESIGNATED",
        "endpoint_kind": "KV",
        "via_kv_intr_only": False,
    },
    SKAP_VAULT_LEDGER: {
        "storage_location": "_Vault/SKAP/Receipts",
        "contract_path": ".stegverse/receipt-chains/skap-receipts.contract.json",
        "contract_sha256": "sha256:83e30008addc557875f9cadf7f587a852e262d09ac50be9ecc041e9863d0b822",
        "repository": "STEGVERSE_KV:_Vault/SKAP/Receipts",
        "carries": ["stegverse.skap-access-receipt/v1 (L2)",
                    "stegverse.tvc.skap-custody-reference-issuance/v1 (TVC#537)",
                    "stegverse.tvc.skap-custody-operation-result/v1"],
        "read_by": "runtime.kv_skap_layer2.SkapLayer2Gate.receipt_ledger (layer 2, via KV's InTr only)",
        "not_designated_code": "CUSTODY_RECEIPT_CHAIN_NOT_DESIGNATED",
        "endpoint_kind": "SKAP_VAULT",
        "via_kv_intr_only": True,
    },
}
PREDICATE = "KV_RECEIPTS_READ_BACK_FROM_KV_OWN_RECEIPT_CHAIN_ONLY"
RETRY = ("runtime.kv_receipt_ledgers.read_receipt_ledger('kv', <storage endpoint adapter>, <readback root>, "
         "<head attestation>, <org-recorded head>); skap_vault only via "
         "runtime.kv_skap_layer2.SkapLayer2Gate.receipt_ledger")
PIN_MECHANISM_CODE = "KV_RECEIPT_CHAIN_GENESIS_PIN_MECHANISM_ORG_HOSTED"
GENESIS_CROSSING = ('Genesis follows the existing two-event crossing model (SKAP_PORTABLE_ENVELOPE_V2_MIRROR_HANDOFF.md '
                    "line 55 @d749bb2, CAPTURE): event 1, the SKAP chain's REPOSITORY_LEDGER_INITIALIZATION genesis "
                    'receipt recorded in KV storage at _Vault/SKAP/Receipts; event 2, a digest-only InTr crossing receipt'
                    ' (pointer/digest plus SUPPLIED_HB_EPOCH) appended to and read back from the Org ledger, which is the'
                    ' exactly-once fence for that crossing only. The SKAP genesis itself is never held on the Org ledger.')


def _sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _refuse(which: str, code: str, klass: str, repair: str, next_attempt: str, detail: str,
            owner: str = TASK, predicate: str = PREDICATE, retry: str = RETRY,
            disposition: str = FAIL_CLOSED) -> dict[str, Any]:
    spec = RECEIPT_LEDGERS.get(which) or {}
    return {"disposition": disposition, "receipt_ledger": which, "storage_location": spec.get("storage_location"),
            "failure_code": code, "failure_class": klass, "failed_predicate": predicate,
            "required_evidence_or_repair": repair, "retry_entrypoint": retry, "owning_existing_goal": owner,
            "next_attempt": next_attempt, "detail": detail, "ledger_written": False, "authority_effect": "NONE"}


def kv2_pending(which: str) -> dict[str, Any]:
    """Six-field FAIL_CLOSED: STEGVERSE_KV's storage endpoint (KV #2) has no admitted provider execution."""
    return _refuse(which, "KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR", "B",
                   f"authentic Interlock/InTr governance and provider execution of the existing KV #2 request "
                   f"{KV2_REQUEST_ID} (google-drive, provider-or-file-provider; KV_STORAGE_ENDPOINT_V2_MIRROR_HANDOFF.md)"
                   ", then a READ of the recorded receipt chain through that storage endpoint",
                   "on the KV #2 governance/provider-execution event in the canonical runtime lane (event-driven)",
                   f"KV #2 is {KV2_GOVERNANCE_STATE}; source/CI/merge grants no provider access",
                   owner=KV2_GOAL, predicate="KV_STORAGE_ENDPOINT_PROVIDER_EXECUTION_ADMITTED",
                   retry="runtime.kv_storage_provider_adapter.build_operation_request(operation='READ', ...) under "
                         "the admitted KV #2 lineage")


def pin_mechanism_org_hosted(which: str) -> dict[str, Any]:
    """Six-field FAIL_CLOSED: the only genesis-pin mechanism is org-hosted (Lane B holds KV wiring)."""
    return _refuse(which, PIN_MECHANISM_CODE, "B",
                   "a per-endpoint genesis pin from Lane B that accepts a KV-owned location contract: "
                   "StegVerse-org/LLM-adapter#431 @66a098fa's planner (contract_shape_failure) and receiver still "
                   "require StegVerse-org/.github refs/stegverse/organization-ledger; per #167 comment 6372442705 "
                   "item 6 the pin is computed in advance once #431's genesis aligns with SUPPLIED_HB_EPOCH "
                   "(StegVerse-Labs/.github#3263/#3290)",
                   "when Lane B posts the per-endpoint, SUPPLIED_HB_EPOCH-aligned pin; no KV wiring before then",
                   f"{RECEIPT_LEDGERS[which]['storage_location']}: no mechanism can pin a KV-owned genesis yet",
                   owner="StegVerse-org/.github#162 / StegVerse-org/LLM-adapter#431 (Lane B)",
                   predicate="GENESIS_PIN_MECHANISM_ACCEPTS_KV_OWNED_LOCATION",
                   retry="StegVerse-org/LLM-adapter#431 REPOSITORY_LEDGER_GENESIS_PIN (per-endpoint form, Lane B)")


def _not_pinned(which: str, location: str) -> dict[str, Any]:
    return _refuse(which, "KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED", "B",
                   f"expected_genesis_receipt_sha256 in {RECEIPT_LEDGERS[which]['contract_path']} (both the #431 "
                   f"location and the ledger_designation), set by an admitted change from the {GENESIS_CLASS} genesis "
                   "computed in advance (SUPPLIED_HB_EPOCH) and checked on read-back; never by hand and never invented",
                   f"after {PIN_MECHANISM_CODE} clears (Lane B); event-driven, no cron, no polling",
                   f"{location}: expected_genesis_receipt_sha256 is null; any store can mint a genesis, so none is "
                   "accepted", owner=f"{TASK}; dependency owner Lane B (#162 / LLM-adapter#431)")


MEMBERSHIP_CODE = "ENDPOINT_ORG_MEMBERSHIP_REFUSED"
#: Rigel's rule (via Coordination, StegVerse-org/.github#160): no endpoint (KV, SKAP Vault, node or gateway) is ever a
#: GitHub Organization member. KV reaches the Orgs only through InTr (KV_INTR_ENDPOINT, intr-destination path_ids).
UNKNOWN_KEY_CODE = "KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY"
#: Closed key schema (LC-KV-24): the only keys permitted at each level of a KV receipt-chain contract. Any other key
#: refuses: ENDPOINT_ORG_MEMBERSHIP_REFUSED when the key is membership-like (MEMBERSHIP_TOKENS), otherwise
#: KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY. ``None`` marks a leaf (a value with no keys of its own); a tuple marks a
#: leaf whose value must be one of the tuple's (rollback_watermark_source.source is only KV_RECORDED_RECEIPT_CHAIN_HEAD).
NOTES_KEYS = ("store_type_note", "head_signers_path", "append_route", "path_ids_note", "refuses",
              "org_crossing_receipts", "head_digest_name", "genesis_crossing", "org_membership")
WATERMARK_KEYS = ("source", "org_crossing_cross_check")
CROSS_CHECK_KEYS = ("source", "path_ids", "role")
CONTRACT_KEY_SCHEMA: dict[str, Any] = {
    "schema": None, "repository": None, "ledger_level": None, "receipt_schema": None, "append_only_receipts": None,
    "required_fields": None, "replay_rule": None,
    "repository_ledger_location": {k: None for k in LOCATION_SHAPE},
    "ledger_designation": {**{k: None for k in DESIGNATION_KEYS},
                           "stores": [{k: None for k in STORE_KEYS}],
                           "rollback_watermark_source": {
                               "source": (WATERMARK_SOURCE,),
                               "org_crossing_cross_check": {"source": (ORG_CROSS_CHECK_SOURCE,), "path_ids": None,
                                                            "role": (CROSS_CHECK_ROLE,)}}},
    "designation_notes": {k: None for k in NOTES_KEYS},
    "propagation_rule": None, "authority_effect": None,
}
MEMBERSHIP_TOKENS = frozenset({"org", "orgs", "organization", "organizations", "organisation", "member", "members",
                               "membership", "memberships", "team", "teams", "install", "installation",
                               "installations", "app", "apps", "permission", "permissions", "owner", "owners",
                               "ownership", "collaborator", "collaborators", "role", "roles", "github",
                               "enterprise", "admin", "admins", "seat", "seats", "scope", "scopes"})


def _membership_like(key: str) -> bool:
    tokens = re.split(r"[^a-z0-9]+", re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", key).lower())
    return any(t in MEMBERSHIP_TOKENS for t in tokens)


def _closed_schema(contract: Any) -> tuple[str, str] | None:
    """(code, reason) for the first key outside CONTRACT_KEY_SCHEMA, or None. Leaves must not carry keys."""
    def walk(node: Any, schema: Any, path: str) -> tuple[str, str] | None:
        if isinstance(node, Mapping):
            allowed = schema if isinstance(schema, Mapping) else {}
            for k, v in node.items():
                if not isinstance(k, str) or k not in allowed:
                    key = str(k)
                    if _membership_like(key):
                        return MEMBERSHIP_CODE, (f"{path}{key} is not a permitted key and is membership-like (an "
                                                 "org, membership, team, app-installation, permission or owner binding)")
                    return UNKNOWN_KEY_CODE, f"{path}{key} is not a permitted key of the closed designation schema"
                hit = walk(v, allowed[k], f"{path}{k}.")
                if hit:
                    return hit
        elif isinstance(node, list):
            item = schema[0] if isinstance(schema, list) and schema else None
            for i, v in enumerate(node):
                hit = walk(v, item, f"{path}{i}.")
                if hit:
                    return hit
        return None
    return walk(contract, CONTRACT_KEY_SCHEMA, "") if isinstance(contract, Mapping) else None
_GH_REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$")


def _org_membership(contract: Any) -> str | None:
    """Why this contract binds the endpoint to a GitHub org repository or ref, or None (keys are closed by
    _closed_schema): the location's repository must be the KV class, never owner/repo; the ref must be the InTr route."""
    if not isinstance(contract, Mapping):
        return None
    loc = contract.get("repository_ledger_location")
    loc = loc if isinstance(loc, Mapping) else {}
    repo = loc.get("repository")
    if isinstance(repo, str) and (_GH_REPO.match(repo) or repo != KV_REPOSITORY):
        return f"repository_ledger_location.repository {repo!r} is not the KV class {KV_REPOSITORY} (an org repository)"
    if loc.get("ref") not in (None, KV_ROUTE):
        return f"repository_ledger_location.ref {loc.get('ref')!r} is not {KV_ROUTE} (an org ref)"
    return None


def org_membership_refused(which: str, reason: str) -> dict[str, Any]:
    """Six-field FAIL_CLOSED (class C): an endpoint is never a GitHub Organization member."""
    return _refuse(which, MEMBERSHIP_CODE, "C",
                   f"a {STORE_TYPE} designation with no org repository, org-membership, team or app-installation "
                   f"binding and no org ref; KV reaches the Orgs only through InTr ({KV_ROUTE}, intr-destination "
                   "path_ids)",
                   "on an admitted change that removes the binding and re-pins the contract digest",
                   f"no endpoint (KV, SKAP Vault, node or gateway) is ever a GitHub Organization member: {reason}",
                   owner="Lane D (StegVerse-Labs/continuity-vault-kit); KV-SKAP-VAULT-FUNCTIONAL-001",
                   predicate="ENDPOINT_NOT_A_GITHUB_ORGANIZATION_MEMBER")


def _org_designation(contract: Any) -> str | None:
    """Why this contract designates an org ledger ref or git-ref store, or None. Structured fields only."""
    if not isinstance(contract, Mapping):
        return None
    loc = contract.get("repository_ledger_location")
    loc = loc if isinstance(loc, Mapping) else {}
    ld = contract.get("ledger_designation")
    ld = ld if isinstance(ld, Mapping) else {}
    stores = ld.get("stores") if isinstance(ld.get("stores"), list) else []
    values = [loc.get("repository"), loc.get("ref"), loc.get("namespace"), ld.get("endpoint_id")]
    for s in stores:
        if isinstance(s, Mapping):
            values += [s.get(k) for k in ("store_type", "location", "repository", "ref", "namespace", "provider_id")]
            if any(k in s for k in ("repository", "ref", "namespace")):
                return "a store carries git-ref fields (repository/ref/namespace)"
    for v in values:
        if isinstance(v, str) and any(m in v for m in ORG_MARKERS):
            return f"the contract designates {v!r}"
    return None


def designation(which: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """(designation, None) from the committed, digest-pinned contract, or (None, six-field refusal). Never caller-chosen."""
    spec = RECEIPT_LEDGERS.get(which)
    if spec is None:
        return None, _refuse(which, "RECEIPT_LEDGER_UNKNOWN", "A", f"one of {sorted(RECEIPT_LEDGERS)}",
                             "on the corrected call", f"{which!r} is not a designated receipt chain")
    code = spec["not_designated_code"]
    repair = (f"{spec['contract_path']} at {spec['contract_sha256']}: #431 repository_ledger_location keys designating "
              f"{KV_REPOSITORY}#{KV_ROUTE}:{spec['storage_location']}, plus a one-store {STORE_TYPE} ledger_designation")
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
        return None, _refuse(which, "KV_RECEIPT_CHAIN_DESIGNATED_ON_ORG_LEDGER", "C",
                             f"a {STORE_TYPE} designation of KV's own location {spec['storage_location']}; an org, "
                             "or git-ref designation is refused for KV and SKAP_VAULT; the org ledger carries only digest-only crossing "
                             "receipts (pointer/digest plus SUPPLIED_HB_EPOCH)",
                             "never for an org designation; on a KV-owned contract", org,
                             predicate="INDEPENDENT_ENDPOINT_LEDGER_NOT_ORG_HOSTED")
    loc = contract.get("repository_ledger_location") if isinstance(contract, Mapping) else None
    closed = _closed_schema(contract)
    if closed and closed[0] == MEMBERSHIP_CODE:
        return None, org_membership_refused(which, closed[1])
    if closed:
        return None, _refuse(which, UNKNOWN_KEY_CODE, "C",
                             "a contract whose every key is in the closed schema runtime.kv_receipt_ledgers."
                             "CONTRACT_KEY_SCHEMA (LC-KV-24)",
                             "on an admitted change that removes the key and re-pins the contract digest", closed[1],
                             predicate="KV_RECEIPT_CHAIN_DESIGNATION_KEYS_CLOSED")
    member = _org_membership(contract)
    if member:
        return None, org_membership_refused(which, member)
    if not isinstance(loc, Mapping) or tuple(loc) != LOCATION_SHAPE or contract.get("schema") != CONTRACT_SCHEMA \
            or contract.get("repository") != spec["repository"] or loc.get("repository") != KV_REPOSITORY \
            or loc.get("ref") != KV_ROUTE or loc.get("namespace") != spec["storage_location"] \
            or loc.get("new_ledger_root") is not True:
        return None, _refuse(which, code, "C", repair, "on a KV-owned contract in #431's shape",
                             "the contract is not a KV-owned repository_ledger_location for this chain")
    ld = contract.get("ledger_designation")
    stores = ld.get("stores") if isinstance(ld, Mapping) else None
    genesis = loc.get("expected_genesis_receipt_sha256")
    if isinstance(stores, list) and len(stores) > 1:
        return None, _refuse(which, "ENDPOINT_LEDGER_MULTI_PROVIDER_NOT_SUPPORTED", "C",
                             "exactly one store under SINGLE_PROVIDER_V1 (multi-provider redundancy is a later, "
                             "separately registered task)", "on the admission of a multi-provider selection rule",
                             f"{len(stores)} stores designated", predicate="ONE_STORE_PROVIDER_UNDER_SINGLE_PROVIDER_V1")
    store = stores[0] if isinstance(stores, list) and stores and isinstance(stores[0], Mapping) else None
    descriptor = None
    if store is not None:
        try:
            descriptor = spa.default_registry().get(store.get("provider_id")).descriptor()
        except spa.KVStorageProviderError:
            descriptor = None
    w = ld.get("rollback_watermark_source") if isinstance(ld, Mapping) else None
    if isinstance(w, Mapping) and w.get("source") != WATERMARK_SOURCE and _org_sourced(w.get("source")):
        return None, watermark_org_sourced(which, f"ledger_designation.rollback_watermark_source.source is "
                                                  f"{w.get('source')!r}")
    xc = w.get("org_crossing_cross_check") if isinstance(w, Mapping) else None
    if store is None or tuple(ld) != DESIGNATION_KEYS or ld.get("schema") != DESIGNATION_SCHEMA \
            or tuple(store) != STORE_KEYS or store.get("store_type") != STORE_TYPE \
            or store.get("storage_endpoint_schema") != spa.STORAGE_ENDPOINT_SCHEMA or descriptor is None \
            or store.get("access_adapter") != descriptor["access_adapter"] or store.get("kv_class") != KV_REPOSITORY \
            or store.get("location") != spec["storage_location"] \
            or ld.get("endpoint_id") != spec["repository"] or ld.get("endpoint_kind") != spec["endpoint_kind"] \
            or ld.get("provider_selection") != "SINGLE_PROVIDER_V1" or ld.get("genesis_class") != GENESIS_CLASS \
            or ld.get("expected_genesis_receipt_sha256") != genesis or ld.get("head_signer_source") != "KV_LEDGER_HEAD_SIGNER" \
            or not isinstance(w, Mapping) or w.get("source") != WATERMARK_SOURCE \
            or (xc is not None and (not isinstance(xc, Mapping) or xc.get("source") != ORG_CROSS_CHECK_SOURCE
                                    or xc.get("role") != CROSS_CHECK_ROLE or not xc.get("path_ids"))):
        return None, _refuse(which, "KV_RECEIPT_CHAIN_STORE_NOT_STORAGE_ENDPOINT_V2", "C", repair,
                             "on a KV-owned contract whose single store is a documented storage endpoint v2 descriptor",
                             f"ledger_designation is not the one-store {STORE_TYPE} designation for this chain")
    pinned = isinstance(genesis, str) and len(genesis) == 71 and genesis.startswith("sha256:")
    return {"receipt_ledger": which, "ledger_designation": json.loads(json.dumps(ld)), "store": dict(store),
            "storage_location": spec["storage_location"], "repository": spec["repository"],
            "repository_ledger_location": dict(loc), "kv_endpoint": loc["repository"], "route": loc["ref"],
            "namespace": loc["namespace"], "location": f"{loc['repository']}#{loc['ref']}:{loc['namespace']}",
            "store_location": f"storage-endpoint:{store['provider_id']}/{store['location']}",
            "contract_path": spec["contract_path"], "contract_sha256": spec["contract_sha256"],
            "via_kv_intr_only": spec["via_kv_intr_only"],
            "expected_genesis_receipt_sha256": genesis if pinned else None}, None


def receipt_ledger_binding(which: str) -> dict[str, Any]:
    """What a minted receipt records about the chain it belongs on (where, under which contract, pinned or not)."""
    d, refusal = designation(which)
    if refusal:
        return {"receipt_ledger": which, "disposition": FAIL_CLOSED, "failure_code": refusal["failure_code"]}
    out = {k: d[k] for k in ("receipt_ledger", "storage_location", "repository", "location", "contract_sha256",
                             "expected_genesis_receipt_sha256")}
    out["disposition"] = "DESIGNATED_GENESIS_PINNED" if d["expected_genesis_receipt_sha256"] else FAIL_CLOSED
    if not d["expected_genesis_receipt_sha256"]:
        out["failure_code"] = "KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED"
    return out


def _pinned():
    from runtime.kv_interlock_endpoint import load_pinned_intr  # lazy: kv_interlock_endpoint imports this module
    return load_pinned_intr()


def load_head_signers() -> list[dict[str, Any]]:
    """Published kv_ledger_head_signer references (TVC#542 pattern); empty until published."""
    try:
        published = json.loads(HEAD_SIGNERS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(published, Mapping) or published.get("schema") != HEAD_SIGNERS_SCHEMA:
        return []
    return [dict(k) for k in published.get("signers") or []
            if isinstance(k, Mapping) and k.get("signs") == HEAD_DIGEST_NAME]


def head_attestation_body(endpoint_id: str, store_location: str, genesis_sha: str, head_sha: str) -> dict[str, Any]:
    """The kv-ledger-head-attestation/v1 body, field for field as LLM-adapter#431 @a2237bc3 reads it. Pure."""
    return {"schema": HEAD_ATTESTATION_SCHEMA, "endpoint_id": endpoint_id, "store_location": store_location,
            "genesis_receipt_sha256": genesis_sha, "head_receipt_sha256": head_sha, "signer_role": SIGNER_ROLE}


def _head_failure(modules: dict[str, Any], which: str, d: Mapping[str, Any] | None, attestation: Any,
                  genesis_sha: str, head_sha: str) -> dict[str, Any] | None:
    signers = load_head_signers()
    where = d["store_location"] if d else which
    if not signers:
        return _refuse(which, "KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED", "B",
                       f"a kv_ledger_head_signer public-key reference published in {HEAD_SIGNERS_REL} by an admitted "
                       "change (the TVC#542 head-signer pattern applied to KV)",
                       "on the kv_ledger_head_signer publication event", f"{where}: no head signer is published",
                       owner=f"{TASK}; dependency owner Lane C (StegVerse-Labs/TVC#542 kv_ledger_head_signer)",
                       predicate="KV_LEDGER_HEAD_SIGNED_BY_KV_LEDGER_HEAD_SIGNER")
    not_auth = "KV_LEDGER_HEAD_NOT_AUTHENTICATED"
    repair = f"a {HEAD_ATTESTATION_SCHEMA} over exactly this endpoint, store location, genesis and head"
    if not isinstance(attestation, Mapping):
        return _refuse(which, not_auth, "C", repair, "on the next signed head", "no head attestation")
    body = {k: attestation.get(k) for k in HEAD_ATTESTATION_FIELDS}
    if body != head_attestation_body(d["repository"], d["store_location"], genesis_sha, head_sha):
        return _refuse(which, not_auth, "C", repair, "on the next signed head",
                       f"the attestation names another endpoint, location, genesis or head (head {head_sha})")
    key = next((k for k in signers if k.get("key_id") == attestation.get("key_id")), None)
    try:
        public = base64.b64decode(key.get("public_key_b64"), validate=True) if key else None
        signature = base64.b64decode(attestation.get("signature_b64"), validate=True)
    except (binascii.Error, ValueError, TypeError):
        public, signature = None, None
    message = HEAD_ATTESTATION_SCHEMA.encode("utf-8") + b"\n" + modules["healthy_node_evaluator"].canon(body)
    if public is None or len(public) != 32 or signature is None or len(signature) != 64 \
            or not modules["ed25519_verify"].verify(public, message, signature):
        return _refuse(which, not_auth, "C", repair, "on the next signed head",
                       "the attestation does not verify under a published kv_ledger_head_signer key")
    return None


def _via_kv_intr_failure(d: Mapping[str, Any], via_kv_intr: Any) -> str | None:
    if not d["via_kv_intr_only"]:
        return None
    if not isinstance(via_kv_intr, Mapping) or via_kv_intr.get("schema") != "stegverse.kv-access-receipt/v1" \
            or via_kv_intr.get("receipt_ledger") != receipt_ledger_binding(KV_LEDGER):
        return "no layer-1 KV-access receipt minted by KV's InTr ingress was presented by SkapLayer2Gate"
    return None


WATERMARK_MISSING_CODE = "KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING"


def watermark_missing(which: str, detail: str = "no recorded_head supplied") -> dict[str, Any]:
    """Six-field FAIL_CLOSED (class A, LC-KV-23): the rollback watermark is required. Without the newest head KV
    itself recorded on its own receipt chain, an older signed head cannot be told apart."""
    return _refuse(which, WATERMARK_MISSING_CODE, "A",
                   f'recorded_head = {{"source": "{WATERMARK_SOURCE}", "head_receipt_sha256": "sha256:<64 hex>"}}: '
                   "the newest head KV recorded on its own receipt chain (optionally with a digest-only "
                   '"org_crossing_cross_check" of the Org\'s side of a crossing, never the watermark)',
                   "on the corrected call", detail, predicate="ROLLBACK_WATERMARK_SUPPLIED")


def _org_sourced(value: Any) -> bool:
    """A watermark source that names the Org ledger (or any Org-side head) rather than KV's own chain."""
    if not isinstance(value, str):
        return False
    tokens = set(re.split(r"[^A-Z0-9]+", value.upper()))
    return value == ORG_CROSS_CHECK_SOURCE or bool(tokens & {"ORG", "ORGANIZATION"}) \
        or any(m in value for m in ORG_MARKERS)


def watermark_org_sourced(which: str, detail: str) -> dict[str, Any]:
    """Six-field FAIL_CLOSED (class A): the rollback watermark must come from KV's own recorded receipt chain head."""
    return _refuse(which, ORG_SOURCED_CODE, "A",
                   f"a rollback watermark sourced from KV's own recorded receipt chain head ({WATERMARK_SOURCE}); an "
                   f"Org-linked head ({ORG_CROSS_CHECK_SOURCE}) may appear only as the optional digest-only "
                   f"org_crossing_cross_check ({CROSS_CHECK_ROLE}), never as the watermark source",
                   "on the corrected designation or call", detail,
                   predicate="ROLLBACK_WATERMARK_SOURCED_FROM_KV_OWN_RECEIPT_CHAIN")


def _external(which: str, detail: str) -> dict[str, Any]:
    return _refuse(which, "EXTERNAL_STORAGE_RECORD_REFUSED", "C",
                   "only HEAD.json and the on-chain receipts/<sha256 hex>.json KV computed; the storage provider's own "
                   "records (file ids, revisions, owners, sharing, metadata files) never cross into KV",
                   "never: an external record is not KV input", detail,
                   predicate="EXTERNAL_RECORDS_NEVER_CROSS_INTO_KV")


WATERMARK_INPUT_KEYS = ("source", "head_receipt_sha256", "org_crossing_cross_check")


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") \
        and all(c in "0123456789abcdef" for c in value[7:])


def _watermark(which: str, recorded_head: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """The rollback watermark input: {"source": KV_RECORDED_RECEIPT_CHAIN_HEAD, "head_receipt_sha256": sha256,
    optional "org_crossing_cross_check": sha256 (digest-only, authority NONE, never compared as the watermark)}."""
    if recorded_head is None:
        return None, watermark_missing(which)
    if not isinstance(recorded_head, Mapping):
        return None, watermark_missing(which, f"recorded_head {recorded_head!r} does not declare its source "
                                              f"(expected a mapping with source {WATERMARK_SOURCE})")
    source = recorded_head.get("source")
    if source != WATERMARK_SOURCE and _org_sourced(source):
        return None, watermark_org_sourced(which, f"recorded_head.source is {source!r}")
    xc = recorded_head.get("org_crossing_cross_check")
    if source != WATERMARK_SOURCE or set(recorded_head) - set(WATERMARK_INPUT_KEYS) \
            or not _is_sha(recorded_head.get("head_receipt_sha256")) or (xc is not None and not _is_sha(xc)):
        return None, watermark_missing(which, f"recorded_head {dict(recorded_head)!r} is not a {WATERMARK_SOURCE} "
                                              "watermark with head_receipt_sha256 sha256:<64 hex>")
    out = {"source": WATERMARK_SOURCE, "head_receipt_sha256": recorded_head["head_receipt_sha256"]}
    if xc is not None:
        out["org_crossing_cross_check"] = {"digest": xc, "role": CROSS_CHECK_ROLE, "authority_effect": "NONE"}
    return out, None


def _read(which: str, storage_endpoint: Any, readback_root: Any, head_attestation: Any, via_kv_intr: Any,
          recorded_head: Any = None) -> dict[str, Any]:
    d, refusal = designation(which)
    if refusal:
        return refusal
    why = _via_kv_intr_failure(d, via_kv_intr)
    if why:
        return _refuse(which, "SKAP_RECEIPT_CHAIN_NOT_VIA_KV_INTR", "A",
                       "read the SKAP receipt chain only through runtime.kv_skap_layer2.SkapLayer2Gate.receipt_ledger "
                       "with a layer-1 KV-access receipt the KV runtime minted (two-layer access rule)",
                       "on the corrected call, through KV's InTr", why, predicate="SKAP_VAULT_REACHED_ONLY_VIA_KV_INTR")
    store = d["store"]
    if store["kv_request_id"] == KV2_REQUEST_ID and KV2_GOVERNANCE_STATE == "PENDING_INTERLOCK_INTR":
        return kv2_pending(which)
    if d["expected_genesis_receipt_sha256"] is None:
        return _not_pinned(which, d["location"])
    if getattr(storage_endpoint, "provider_id", None) != store["provider_id"] \
            or not callable(getattr(storage_endpoint, "descriptor", None)) \
            or storage_endpoint.descriptor().get("access_adapter") != store["access_adapter"]:
        return _refuse(which, "KV_STORAGE_ENDPOINT_NOT_THE_DESIGNATED_ONE", "C",
                       f"the storage endpoint {store['provider_id']} ({store['access_adapter']}) the designation names",
                       "with the designated storage endpoint",
                       f"storage endpoint {getattr(storage_endpoint, 'provider_id', None)!r}")
    modules, why = _pinned()
    if modules is None:
        return _refuse(which, "PINNED_INTR_CODE_UNAVAILABLE", "C", "the digest-pinned #432 modules", "on re-vendor", why)
    unreadable = "KV_RECEIPT_CHAIN_UNREADABLE"
    root = Path(readback_root) / store["location"] if readback_root is not None else None
    if root is None or not root.is_dir():
        return _refuse(which, unreadable, "D", f"the {store['location']} read back through the storage endpoint",
                       "on the next storage endpoint READ", f"no read-back at {root}")
    hne = modules["healthy_node_evaluator"]
    chain, failure, detail = hne.read_chain(root, d["repository"])
    if failure == "RECEIPT_REPOSITORY_MISMATCH":
        return _refuse(which, "KV_RECEIPT_CHAIN_FOREIGN_RECORD_REFUSED", "C",
                       f"only KV's own receipts for {d['repository']}, computed on KV's side ({CORRESPONDENCE_RULE})",
                       "never: a foreign record is not KV input", detail,
                       predicate="EXTERNAL_RECORDS_NEVER_CROSS_INTO_KV")
    if failure or not chain or chain[-1].get("transition_class") != GENESIS_CLASS:
        return _refuse(which, unreadable, "C", f"one KV-computed chain at {store['location']} back to its "
                       f"{GENESIS_CLASS} genesis (an empty location is never a genesis)", "on an intact chain",
                       f"{failure or 'no genesis'} {detail}")
    on_chain = {"HEAD.json"} | {"receipts/" + r["receipt_sha256"][7:] + ".json" for r in chain}
    stray = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
                   and p.relative_to(root).as_posix() not in on_chain)
    if stray:
        return _external(which, f"{store['location']} holds records KV did not compute: {stray[:5]}")
    if chain[-1]["receipt_sha256"] != d["expected_genesis_receipt_sha256"]:
        return _refuse(which, "KV_RECEIPT_CHAIN_GENESIS_MISMATCH", "C", "the genesis must be the contract's pin",
                       "never: a store that minted its own genesis is not this chain",
                       f"the store's genesis is {chain[-1]['receipt_sha256']}")
    head = _head_failure(modules, which, d, head_attestation, chain[-1]["receipt_sha256"], chain[0]["receipt_sha256"])
    if head:
        return head
    watermark, failure = _watermark(which, recorded_head)
    if failure:
        return failure
    if watermark["head_receipt_sha256"] not in {r["receipt_sha256"] for r in chain}:
        return _refuse(which, "KV_LEDGER_HEAD_ROLLBACK_DETECTED", "C",
                       f"present a chain that contains the newest head KV recorded on its own receipt chain "
                       f"({WATERMARK_SOURCE}); an older or forked head is refused",
                       "on a read-back at or after the recorded head (event-triggered)",
                       f"KV recorded {watermark['head_receipt_sha256']}; the read-back head is "
                       f"{chain[0]['receipt_sha256']}",
                       predicate="ENDPOINT_HEAD_NOT_OLDER_THAN_THE_NEWEST_KV_RECORDED_HEAD", disposition=DENY)
    out = {**receipt_ledger_binding(which), "disposition": ALLOW, "head_receipt_sha256": chain[0]["receipt_sha256"],
           "store_location": d["store_location"], "chain": chain, "rollback_watermark": watermark,
           "authority_effect": "NONE"}
    return out


def read_receipt_ledger(which: str, storage_endpoint: Any = None, readback_root: Any = None,
                        head_attestation: Any = None, recorded_head: Any = None) -> dict[str, Any]:
    """Read one recorded receipt chain back from KV's own location. ALLOW carries the chain (newest first). Read-only.

    Refusal order: not designated (incl. org / git-ref designation, a store other than KV_STORAGE_ENDPOINT, more than one store); SKAP chain not
    reached via KV's InTr (always, on this entrypoint); KV #2 storage endpoint PENDING_INTERLOCK_INTR;
    genesis not pinned; storage endpoint not the designated one; read-back
    unreadable or foreign; external storage records; genesis mismatch; head not signed by a published
    kv_ledger_head_signer; rollback watermark (``recorded_head``: {"source": KV_RECORDED_RECEIPT_CHAIN_HEAD,
    "head_receipt_sha256": ...}, the newest head KV recorded on its own chain) required: absent or malformed ->
    FAIL_CLOSED KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING (A); Org-sourced -> FAIL_CLOSED
    KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED (A);
    not on the chain -> DENY KV_LEDGER_HEAD_ROLLBACK_DETECTED."""
    return _read(which, storage_endpoint, readback_root, head_attestation, None, recorded_head)


def receipt_on_ledger(which: str, receipt_sha256: Any, storage_endpoint: Any = None, readback_root: Any = None,
                      head_attestation: Any = None, recorded_head: Any = None, *,
                      _read_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """ALLOW only if a receipt whose evidence carries receipt_sha256 is on the read-back chain (watermark required)."""
    read = dict(_read_result) if _read_result is not None else read_receipt_ledger(
        which, storage_endpoint, readback_root, head_attestation, recorded_head)
    if read["disposition"] != ALLOW:
        return read
    for r in read["chain"]:
        evidence = r.get("evidence") if isinstance(r.get("evidence"), Mapping) else {}
        if evidence.get("receipt_sha256") == receipt_sha256 or evidence.get("receipt_hash") == receipt_sha256:
            return {"disposition": ALLOW, "receipt_ledger": which, "ledger_receipt_sha256": r["receipt_sha256"],
                    "head_receipt_sha256": read["head_receipt_sha256"], "authority_effect": "NONE"}
    return _refuse(which, "RECEIPT_NOT_ON_DESIGNATED_RECEIPT_CHAIN", "C",
                   f"a receipt on {read['location']} whose evidence carries {receipt_sha256}",
                   "after KV records it through its own InTr ingress", f"{receipt_sha256} is not on the read-back chain")


SIX_FIELDS = ("failure_code", "failure_class", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
              "owning_existing_goal", "next_attempt")


def receipt_ledger_prerequisites() -> list[dict[str, Any]]:
    """One row per receipt chain for the finish point, with every production prerequisite still FAIL_CLOSED."""
    rows = []
    for which in RECEIPT_LEDGERS:
        d, refusal = designation(which)
        blocking: list[dict[str, Any]] = []
        if refusal:
            blocking.append(refusal)
        if d and d["store"]["kv_request_id"] == KV2_REQUEST_ID and KV2_GOVERNANCE_STATE == "PENDING_INTERLOCK_INTR":
            blocking.append(kv2_pending(which))
        if d and d["expected_genesis_receipt_sha256"] is None:
            blocking += [_not_pinned(which, d["location"]), pin_mechanism_org_hosted(which)]
        if not load_head_signers():
            blocking.append(_head_failure({}, which, d, None, "", ""))
        row = {"prerequisite": "KV_RECEIPT_CHAIN_DESIGNATED_READABLE_AND_GENESIS_PINNED", "receipt_ledger": which,
               "storage_location": RECEIPT_LEDGERS[which]["storage_location"],
               "contract_path": RECEIPT_LEDGERS[which]["contract_path"],
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
    "repository_ledger_location": {#431 key shape, KV-owned values}, "ledger_designation": {...}}}. A chain whose
    contract is not designated is given with both null."""
    out: dict[str, Any] = {}
    for which, spec in RECEIPT_LEDGERS.items():
        d, _ = designation(which)
        out[which] = {"carries": list(spec["carries"]), "storage_location": spec["storage_location"],
                      "contract_path": spec["contract_path"], "contract_sha256": spec["contract_sha256"],
                      "via_kv_intr_only": spec["via_kv_intr_only"],
                      "repository_ledger_location": d["repository_ledger_location"] if d else None,
                      "ledger_designation": d["ledger_designation"] if d else None}
    return out


__all__ = ["CORRESPONDENCE_RULE", "KV_LEDGER", "SKAP_VAULT_LEDGER", "RECEIPT_LEDGERS", "STORE_KEYS", "STORE_TYPE",
           "GENESIS_CROSSING", "custody_ledgers_config", "designation", "head_attestation_body",
           "CONTRACT_KEY_SCHEMA", "MEMBERSHIP_CODE", "UNKNOWN_KEY_CODE", "ORG_SOURCED_CODE", "WATERMARK_MISSING_CODE", "WATERMARK_SOURCE", "watermark_org_sourced", "watermark_missing", "kv2_pending", "load_head_signers", "org_membership_refused", "pin_mechanism_org_hosted", "read_receipt_ledger",
           "receipt_ledger_binding", "receipt_ledger_prerequisites", "receipt_on_ledger"]
