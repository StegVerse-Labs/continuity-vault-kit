"""Per-endpoint recorded receipt chain designation and the access-adapter seam (ENDPOINT-LEDGER-DESIGNATION-001).

KV is independent of the Orgs (Rigel, StegVerse-org/.github#160 comments 6371986288 and 6372216673): it keeps its
own recorded receipt chain behind its own InTr ingress/egress endpoint, and that chain is never stored on an org's
refs/stegverse/organization-ledger. Corrected by Coordination (#167 comment 6372442705; SVKV, ECOSYSTEM-OWN-KV-001
and KV-LEDGER-STORE-READER-001 withdrawn): the ecosystem KV is STEGVERSE_KV (``_StegVerse/``, cvk
KV_AI_PERSISTENCE_LAYOUTS.md), and KV storage follows the KV Storage Endpoint v2 model (cvk
KV_STORAGE_ENDPOINT_V2_MIRROR_HANDOFF.md, goal KV-CONNECTION-REVALIDATION-WORKER-001)::

    KV instance -> storage endpoint -> access adapter -> location

KnowledgeVault's file structure is not itself encryption; ciphertext belongs only behind the SKAP Vault boundary
(``_Vault/SKAP``; cvk README). So the recorded receipt chain is read through the endpoint's access adapter as
receipts, not decrypted here, and nothing here claims encryption.

Both sides record every crossing (Rigel, #162 comment 6372641743; CAPTURE lines 72-76; NODE_INGRESS line 176): the
egress record on the source side and the ingress record on the destination side, each pointing at the other's
record by digest (never a copied body) and each carrying a supplied heartbeat epoch (SUPPLIED_HB_EPOCH). Those paired
records carry continuity between Orgs, and ENVELOPE v2 line 55 (the Org's own append and read-back of the genesis
crossing) stands as the Org's record of the crossing (#167 comment 6372591635).

A designation names, per endpoint, where its recorded receipt chain is and what authenticates it. It is read from
the endpoint's own contract, never from a caller::

    {"schema": "stegverse.endpoint-ledger-designation/v1", "endpoint_id": str,
     "endpoint_kind": "ORG" | "PERMANENT" | "KV" | "SKAP_VAULT",
     "stores": [<exactly one store entry>], "provider_selection": "SINGLE_PROVIDER_V1",
     "genesis_class": str, "expected_genesis_receipt_sha256": null | "sha256:<hex>",
     "head_signer_source": "ORG_LEDGER_HEAD_SIGNER" | "KV_LEDGER_HEAD_SIGNER",
     "rollback_watermark_source": null | {"source": "KV_RECORDED_RECEIPT_CHAIN_HEAD",
                                          ["org_crossing_cross_check": {
                                              "source": "ORG_LEDGER_LINKED_RECEIPTS_ENDPOINT_HEAD",
                                              "path_ids": [str, ...],
                                              "role": "DIGEST_ONLY_CROSS_CHECK_NEVER_WATERMARK"}]}}

Keys are closed at every level (continuity-vault-kit#263 @bf684aad runtime/kv_receipt_ledgers.py CONTRACT_KEY_SCHEMA,
LC-KV-24; mirrored here as CONTRACT_KEY_SCHEMA and, for a bare designation, DESIGNATION_KEY_SCHEMA). An unknown key
is six-field ENDPOINT_ORG_MEMBERSHIP_REFUSED when it is membership-like (one of its snake/camel tokens is in Lane D's
MEMBERSHIP_TOKENS), otherwise KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY. The token test only picks the code; it never
admits a key. ``rollback_watermark_source.source`` is only KV_RECORDED_RECEIPT_CHAIN_HEAD: KV's own recorded receipt
chain head (KV is independent of the Orgs). An Org-sourced watermark is KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED
(class A). The Org-linked head and the ``:intr-destination`` path_ids appear only under the optional
``org_crossing_cross_check``, a digest-only cross-check of the Org's side of a crossing, never the watermark, so the
watermark does not depend on any declared path (StegVerse-org/.github#235).

store_type (an enum), mapped to the documented endpoint model:

* ``GIT_REF``: {store_type, provider "git", repository, ref, namespace}. Read by the existing git reader,
  llm_adapter.org_ledger_location.designated_org_ledger, unchanged (it pins the genesis and authenticates the head
  with the org-ledger head signers). Used for ORG only: PERMANENT (a node) is refused with six fields
  ENDPOINT_NOT_AN_ORG_LEDGER_SOURCE, since no endpoint is an org-ledger source (#160 comment 6372871021).
* ``KV_STORAGE_ENDPOINT``: {store_type, storage_endpoint_schema, provider_id, access_adapter, kv_class,
  kv_request_id, location}, exactly Lane D's store (StegVerse-Labs/continuity-vault-kit#263 @706877b6
  runtime/kv_receipt_ledgers.py STORE_KEYS; the storage endpoint is reused unchanged from cvk
  runtime/kv_storage_provider_adapter.py): storage_endpoint_schema stegverse.kv.storage-endpoint-descriptor/v2,
  provider_id and access_adapter a documented registry pair (google-drive / provider-or-file-provider, KV #2
  SITE-CLOUD-KV-4347408852127319cbda574f02e03edb; E0 only device-local / resident-device-local), kv_class
  STEGVERSE_KV, and location KV's own chain: ``_StegVerse/Receipts`` (KV) or ``_Vault/SKAP/Receipts``
  (SKAP_VAULT), laid out as HEAD.json + receipts/<hex>.json, on no org ref. Required for KV and SKAP_VAULT; GIT_REF
  is refused for them. The reader is cvk's, referenced not vendored: runtime.kv_receipt_ledgers.read_receipt_ledger
  (which, storage_endpoint, readback_root, head_attestation, recorded_head), KVInterlockRuntime.receipt_ledger and
  SkapLayer2Gate.receipt_ledger. Its reader id is not documented (UNKNOWN_NOT_AUTHENTICALLY_OBSERVED), so every
  such read here is six-field FAIL_CLOSED KV_RECEIPT_CHAIN_READER_ID_NOT_DOCUMENTED (#167 comment 6372772397).

Several storage endpoints per KV instance (designed for, not supported): ``stores`` is an ordered list. The
selection rule is deterministic: list order is the only selector, never health, latency, a clock or the caller.
SINGLE_PROVIDER_V1 (the only rule now) selects ``stores[0]`` and requires exactly one entry; more than one is
six-field ENDPOINT_LEDGER_MULTI_PROVIDER_NOT_SUPPORTED. A multi-endpoint rule is its own admitted change.

The access-adapter seam: ``READERS`` maps store_type to a reader. A reader is a context manager factory
``reader(designation, store, source, head_attestation)`` that yields ``(chain, None)`` (receipts newest first, as
the endpoint's access adapter reads them) or ``(None, (reason, detail))``. Whatever a reader yields is checked again
here by the pure ``chain_admission_failure``, for every store type:

1. an empty or missing chain is never taken as a genesis (ENDPOINT_LEDGER_EMPTY_NOT_A_GENESIS);
2. every receipt is sealed and linked, and the chain ends at the designated genesis class;
3. the genesis equals the designation's pin (null: ENDPOINT_LEDGER_GENESIS_NOT_PINNED);
4. KV and SKAP_VAULT: the head is signed by kv_ledger_head_signer (TVC#542), a key published in
   .stegverse/node-ledger/kv-ledger-head-signers.v1.json (none published yet:
   KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED). GIT_REF heads were authenticated by the git reader;
5. KV and SKAP_VAULT: the rollback watermark is required, ``recorded_head = {"source":
   "KV_RECORDED_RECEIPT_CHAIN_HEAD", "head_receipt_sha256": "sha256:<64 hex>"[, "org_crossing_cross_check":
   "sha256:<64 hex>"]}``, the newest head KV recorded on its own receipt chain. Absent or malformed:
   KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING (class A); Org-sourced: KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED
   (class A); not on the presented chain: DENY KV_LEDGER_HEAD_ROLLBACK_DETECTED. The cross-check digest is echoed
   with authority NONE and never compared as the watermark;
6. both sides recorded each crossing: every Org-side record for the designation's cross-check path_ids points at an
   endpoint head that is on the presented chain, every endpoint-side ingress record points at a record on the Org
   chain (an endpoint crossing record with no Org chain supplied is one-sided), and each such record carries a
   supplied epoch. A one-sided crossing is FAIL_CLOSED INTR_CROSSING_NOT_RECORDED_BY_BOTH_SIDES;
   a crossing record without a supplied epoch is HB_EPOCH_NOT_SUPPLIED / HB_EPOCH_INVALID.

Pure apart from the reader it hands off to. No clock, no network, no randomness, stdlib only. Tests use fixture
keys only; bots never hold keys.
"""
from __future__ import annotations

import base64
import binascii
import contextlib
import json
import re
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping

from llm_adapter import ed25519_verify
from llm_adapter import healthy_node_evaluator as hne
from llm_adapter import org_ledger_location
from llm_adapter import supplied_epoch

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "stegverse.endpoint-ledger-designation/v1"
RESULT_SCHEMA = "stegverse.endpoint-ledger-read/v1"
ALLOW, FAIL_CLOSED, DENY = "ALLOW", "FAIL_CLOSED", "DENY"

GIT_REF, KV_STORAGE_ENDPOINT = "GIT_REF", "KV_STORAGE_ENDPOINT"
STORE_TYPES = (GIT_REF, KV_STORAGE_ENDPOINT)
ORG, PERMANENT, KV, SKAP_VAULT = "ORG", "PERMANENT", "KV", "SKAP_VAULT"
STORE_TYPE_OF = {ORG: GIT_REF, PERMANENT: GIT_REF, KV: KV_STORAGE_ENDPOINT, SKAP_VAULT: KV_STORAGE_ENDPOINT}
INDEPENDENT_KINDS = (KV, SKAP_VAULT)
#: cvk#263 @706877b6 runtime/kv_receipt_ledgers.py STORE_KEYS (in that order there; sorted here)
STORE_KEYS = {GIT_REF: ("namespace", "provider", "ref", "repository", "store_type"),
              KV_STORAGE_ENDPOINT: ("access_adapter", "kv_class", "kv_request_id", "location", "provider_id",
                                    "storage_endpoint_schema", "store_type")}
#: cvk runtime/kv_storage_provider_adapter.py STORAGE_ENDPOINT_SCHEMA (line 25)
STORAGE_ENDPOINT_SCHEMA = "stegverse.kv.storage-endpoint-descriptor/v2"
#: documented (provider_id, access_adapter) pairs the reader consumes (cvk default_registry lines 150 and 152)
ACCESS_ADAPTERS = {"google-drive": "provider-or-file-provider", "device-local": "resident-device-local"}
KV_CLASS = "STEGVERSE_KV"
KV2_REQUEST_ID = "SITE-CLOUD-KV-4347408852127319cbda574f02e03edb"
#: KV's own recorded receipt chains (cvk specs/kv-ai-persistence-layouts.v1.json; kv_receipt_ledgers RECEIPT_LEDGERS)
KV_CHAIN_LOCATIONS = {"KV": "_StegVerse/Receipts", "SKAP_VAULT": "_Vault/SKAP/Receipts"}
#: the head digest the InTr crossing receipt carries to the Org ledger (StegVerse-Labs/TVC#542 @4c2504da)
HEAD_DIGEST_NAME = "KV_RECORDED_RECEIPT_CHAIN_HEAD"
#: the reader id; the KV Storage Endpoint v2 docs define none (#167 comment 6372772397)
READER_ID = "UNKNOWN_NOT_AUTHENTICALLY_OBSERVED"
#: Lane D's reader entrypoints (cvk#263 @706877b6), referenced, never vendored
READER_ENTRYPOINTS = (
    "runtime.kv_receipt_ledgers.read_receipt_ledger(which, storage_endpoint, readback_root, head_attestation, "
    "recorded_head)",   # cvk#263 @bf684aad, recorded_head = the KV_RECORDED_RECEIPT_CHAIN_HEAD watermark
    "runtime.kv_interlock_endpoint.KVInterlockRuntime.receipt_ledger(...)",
    "runtime.kv_skap_layer2.SkapLayer2Gate.receipt_ledger(...)",
)


def kv_path_id(location: str) -> str:
    """The Org-side path_id for a crossing with KV's chain at ``location`` (cvk#263 contracts)."""
    return f"StegVerse-org->{KV_CLASS}:{location}:intr-destination"
CROSSING_CLASSES = ("INTR_MESH_PATH_TRANSFER", "INTR_MESH_PATH_INGRESS")
INGRESS_CLASS = "INTR_MESH_PATH_INGRESS"
SINGLE_PROVIDER_V1 = "SINGLE_PROVIDER_V1"
SELECTION_RULES = (SINGLE_PROVIDER_V1,)
DESIGNATION_KEYS = ("endpoint_id", "endpoint_kind", "expected_genesis_receipt_sha256", "genesis_class",
                    "head_signer_source", "provider_selection", "rollback_watermark_source", "schema", "stores")

ORG_LEDGER_HEAD_SIGNER, KV_LEDGER_HEAD_SIGNER = "ORG_LEDGER_HEAD_SIGNER", "KV_LEDGER_HEAD_SIGNER"
HEAD_SIGNER_OF = {ORG: ORG_LEDGER_HEAD_SIGNER, PERMANENT: ORG_LEDGER_HEAD_SIGNER,
                  KV: KV_LEDGER_HEAD_SIGNER, SKAP_VAULT: KV_LEDGER_HEAD_SIGNER}
#: head-signer set sources: public-key reference files, TV/TVC custody, empty until published
HEAD_SIGNER_FILES = MappingProxyType({
    ORG_LEDGER_HEAD_SIGNER: (ROOT / ".stegverse/node-ledger/org-ledger-head-signers.v1.json", "ORG_LEDGER_HEAD"),
    KV_LEDGER_HEAD_SIGNER: (ROOT / ".stegverse/node-ledger/kv-ledger-head-signers.v1.json", HEAD_DIGEST_NAME),
})
SIGNERS_SCHEMA = "stegverse.published-public-key-references/v1"
KV_HEAD_ATTESTATION_SCHEMA = "stegverse.kv-ledger-head-attestation/v1"
KV_HEAD_ATTESTATION_FIELDS = ("schema", "endpoint_id", "store_location", "genesis_receipt_sha256",
                              "head_receipt_sha256", "signer_role")
KV_SIGNER_ROLE = "kv_ledger_head_signer"
#: continuity-vault-kit#263 @bf684aada366e227714c6f67ac52a7a4ec6933d4 runtime/kv_receipt_ledgers.py (Lane D), values
#: unchanged: the watermark is KV's own recorded receipt chain head; the Org-linked head is only a digest-only
#: cross-check, never the watermark
WATERMARK_SOURCE = "KV_RECORDED_RECEIPT_CHAIN_HEAD"
ORG_CROSS_CHECK_SOURCE = "ORG_LEDGER_LINKED_RECEIPTS_ENDPOINT_HEAD"
CROSS_CHECK_ROLE = "DIGEST_ONLY_CROSS_CHECK_NEVER_WATERMARK"
ORG_SOURCED_CODE = "KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED"
WATERMARK_MISSING_CODE = "KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING"
UNKNOWN_KEY_CODE = "KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY"
WATERMARK_KEYS = ("source", "org_crossing_cross_check")
CROSS_CHECK_KEYS = ("source", "path_ids", "role")
WATERMARK_INPUT_KEYS = ("source", "head_receipt_sha256", "org_crossing_cross_check")
ORG_MARKERS = ("GIT_REF", "StegVerse-org/.github", "refs/stegverse/organization-ledger", "repository-ledger/")
ENDPOINT_HEAD_KEY = "endpoint_head_sha256"

ENTRYPOINT = "llm_adapter.endpoint_ledger_designation.read_designated(designation, source=..., ...)"
GOAL = "StegVerse-org/.github#162 (ENDPOINT-LEDGER-DESIGNATION-001; KV independence, .github#160 comment 6372216673)"
READER_GOAL = ("KV-SKAP-LEDGER-LOCATION-001 under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324; reader "
               "StegVerse-Labs/continuity-vault-kit#263)")
CROSSING_GOAL = "StegVerse-org/.github#162 (both sides record each InTr crossing; #162 comment 6372641743; Lane B)"
#: Rigel, relayed on StegVerse-org/.github#160 comment 6372871021: no endpoint (KV, SKAP Vault, node or gateway,
#: externally or ecosystem maintained) is a GitHub Organization member or a source of org-ledger records.
ORG_SOURCE_GOAL = ("StegVerse-org/.github#162 (no endpoint is an Organization member or a source of org-ledger "
                   "records; #160 comment 6372871021; Lane B)")
#: the only keys an Org-chain crossing receipt for an endpoint path may carry: pointers and digests, never a body
ORG_CROSSING_EVIDENCE_KEYS = frozenset({"schema", "path_id", "communication_id", "source_repository_receipt_sha256",
                                        "destination_location", "boundary_evidence"})
ORG_CROSSING_BOUNDARY_KEYS = frozenset({"operation", "path_id", "communication_id", ENDPOINT_HEAD_KEY})
#: keys that would make an endpoint the originator of an Org-chain record
ORIGINATOR_KEYS = ("node_id", "node_ref", "originator", "author", "repository", "source_repository")
#: LC-KV-25 (P1 rev 10, #163 comment 6373389075): no endpoint is a GitHub Organization member. The code and its
#: predicate are Lane D's (StegVerse-Labs/continuity-vault-kit#263 @bf684aad runtime/kv_receipt_ledgers.py
#: MEMBERSHIP_CODE / org_membership_refused, predicate ENDPOINT_NOT_A_GITHUB_ORGANIZATION_MEMBER; Lane C
#: TVC#540/#542). LC-KV-24: keys are closed (CONTRACT_KEY_SCHEMA); an unknown key is membership-like when a token
#: of it is in MEMBERSHIP_TOKENS (Lane D's set, unchanged). Only the designation's own keys are read: no membership
#: data source is consulted. Distinct from ENDPOINT_NOT_AN_ORG_LEDGER_SOURCE (an endpoint emitting org-ledger
#: records; Coordination's provisional ruling).
MEMBERSHIP_CODE = "ENDPOINT_ORG_MEMBERSHIP_REFUSED"
MEMBERSHIP_TOKENS = frozenset({"org", "orgs", "organization", "organizations", "organisation", "member", "members",
                               "membership", "memberships", "team", "teams", "install", "installation",
                               "installations", "app", "apps", "permission", "permissions", "owner", "owners",
                               "ownership", "collaborator", "collaborators", "role", "roles", "github",
                               "enterprise", "admin", "admins", "seat", "seats", "scope", "scopes"})
LANE_D_GOAL = ("KV-SKAP-VAULT-FUNCTIONAL-001 (Lane D, StegVerse-Labs/continuity-vault-kit#263 @bf684aad; "
               "KV-SKAP-LEDGER-LOCATION-001, StegVerse-Labs/.github#3324)")
MEMBERSHIP_GOAL = ("KV-SKAP-VAULT-FUNCTIONAL-001 (Lane D, StegVerse-Labs/continuity-vault-kit#263 @bf684aad "
                   "ENDPOINT_ORG_MEMBERSHIP_REFUSED; Lane C StegVerse-Labs/TVC#540/#542)")
#: cvk#263 @bf684aad: LOCATION_SHAPE, DESIGNATION_KEYS, STORE_KEYS and NOTES_KEYS in cvk's order
LOCATION_SHAPE = ("repository", "ref", "namespace", "locator_form", "new_ledger_root", "designation_source",
                  "initialization", "rule", "expected_genesis_receipt_sha256", "expected_genesis_note")
CVK_DESIGNATION_KEYS = ("schema", "endpoint_id", "endpoint_kind", "stores", "provider_selection", "genesis_class",
                        "expected_genesis_receipt_sha256", "head_signer_source", "rollback_watermark_source")
CVK_STORE_KEYS = ("store_type", "storage_endpoint_schema", "provider_id", "access_adapter", "kv_class",
                  "kv_request_id", "location")
NOTES_KEYS = ("store_type_note", "head_signers_path", "append_route", "path_ids_note", "refuses",
              "org_crossing_receipts", "head_digest_name", "genesis_crossing", "org_membership")
#: ``None`` is a leaf; a tuple is a leaf whose value must be one of the tuple's
WATERMARK_KEY_SCHEMA: Mapping[str, Any] = MappingProxyType({
    "source": (WATERMARK_SOURCE,),
    "org_crossing_cross_check": {"source": (ORG_CROSS_CHECK_SOURCE,), "path_ids": None, "role": (CROSS_CHECK_ROLE,)}})
#: the closed key schema of a KV receipt-chain contract, equal to cvk#263 @bf684aad CONTRACT_KEY_SCHEMA
CONTRACT_KEY_SCHEMA: Mapping[str, Any] = MappingProxyType({
    "schema": None, "repository": None, "ledger_level": None, "receipt_schema": None, "append_only_receipts": None,
    "required_fields": None, "replay_rule": None,
    "repository_ledger_location": {k: None for k in LOCATION_SHAPE},
    "ledger_designation": {**{k: None for k in CVK_DESIGNATION_KEYS},
                           "stores": [{k: None for k in CVK_STORE_KEYS}],
                           "rollback_watermark_source": dict(WATERMARK_KEY_SCHEMA)},
    "designation_notes": {k: None for k in NOTES_KEYS},
    "propagation_rule": None, "authority_effect": None,
})
SIGNER_GOAL = "StegVerse-Labs/TVC#542 (kv_ledger_head_signer; ORG-LEDGER-HEAD-SIGNER-001 pattern)"
ON_CHANGE = "on the admission of a corrected designation in the endpoint's own contract (event-triggered)"

#: (failed_predicate, required_evidence_or_repair, owning_existing_goal, next_attempt, disposition)
CODES: Mapping[str, tuple[str, str, str, str, str]] = MappingProxyType({
    "ENDPOINT_LEDGER_DESIGNATION_INVALID": (
        "ENDPOINT_LEDGER_DESIGNATION_WELL_FORMED",
        "a stegverse.endpoint-ledger-designation/v1 with exactly the designation keys, a designated endpoint_kind "
        "(ORG, PERMANENT, KV, SKAP_VAULT), its store_type, head_signer_source and genesis_class", GOAL, ON_CHANGE,
        FAIL_CLOSED),
    "ENDPOINT_LEDGER_STORE_TYPE_UNDECLARED": (
        "STORE_TYPE_IS_A_DECLARED_STORE_TYPE", "store_type GIT_REF or KV_STORAGE_ENDPOINT", GOAL, ON_CHANGE,
        FAIL_CLOSED),
    "KV_LEDGER_DESIGNATED_ON_GIT_REF": (
        "INDEPENDENT_ENDPOINT_LEDGER_NOT_ORG_HOSTED",
        "KV and SKAP_VAULT designate store_type KV_STORAGE_ENDPOINT (their own recorded receipt chain at a location "
        "on their KV storage endpoint, KV Storage Endpoint v2); it is never a git ref and never on "
        "refs/stegverse/organization-ledger", GOAL,
        ON_CHANGE, FAIL_CLOSED),
    "ENDPOINT_ORG_MEMBERSHIP_REFUSED": (
        "ENDPOINT_NOT_A_GITHUB_ORGANIZATION_MEMBER",
        "a designation with no org-membership, team or app-installation binding: no endpoint (KV, SKAP Vault, node "
        "or gateway) is ever a GitHub Organization member; it reaches the Orgs only through InTr (intr-destination "
        "path_ids)", MEMBERSHIP_GOAL,
        "on an admitted change to the endpoint's own contract that removes the binding (event-triggered)",
        FAIL_CLOSED),
    "ENDPOINT_NOT_AN_ORG_LEDGER_SOURCE": (
        "NO_ENDPOINT_IS_A_SOURCE_OF_ORG_LEDGER_RECORDS",
        "no endpoint (KV, SKAP Vault, node or gateway, externally or ecosystem maintained) designates, writes or "
        "originates a record on refs/stegverse/organization-ledger: only endpoint_kind ORG is designated there; an "
        "endpoint keeps its own recorded receipt chain and its data crosses only through InTr, recorded at both ends, "
        "the Org side as the org's own digest-only crossing receipt", ORG_SOURCE_GOAL,
        "on an admitted endpoint store type off the org ledger for that kind (event-triggered)", FAIL_CLOSED),
    "ORG_CROSSING_RECEIPT_NOT_DIGEST_ONLY": (
        "ORG_CHAIN_CROSSING_RECEIPT_IS_DIGEST_ONLY_ON_THE_ORGS_OWN_PATH",
        "an Org-chain crossing receipt for an endpoint path carries only pointers and digests (schema, path_id, "
        "communication_id, source_repository_receipt_sha256, destination_location, boundary_evidence {operation, "
        "path_id, communication_id, endpoint_head_sha256}) and a supplied hb epoch, is recorded by the org's own "
        "path, and names no endpoint as its originator", ORG_SOURCE_GOAL,
        "on the next org-ledger read-back with a corrected crossing receipt (event-triggered)", FAIL_CLOSED),
    "ENDPOINT_LEDGER_MULTI_PROVIDER_NOT_SUPPORTED": (
        "ONE_STORE_PROVIDER_UNDER_SINGLE_PROVIDER_V1",
        "designate exactly one store; more than one provider needs its own admitted selection rule (list order "
        "only), which is not built", GOAL, "on the admission of a multi-provider selection rule", FAIL_CLOSED),
    "KV_RECEIPT_CHAIN_READER_ID_NOT_DOCUMENTED": (
        "SUCCESSOR_READER_ID_DEFINED_BY_THE_KV_STORAGE_ENDPOINT_V2_MODEL",
        "an admitted reader id for the access-adapter read of the recorded receipt chain at the designated location "
        "(_StegVerse/Receipts or _Vault/SKAP/Receipts); the reader is cvk's runtime.kv_receipt_ledgers."
        "read_receipt_ledger (continuity-vault-kit#263), referenced not vendored; reader id is "
        "UNKNOWN_NOT_AUTHENTICALLY_OBSERVED", READER_GOAL,
        "on continuity-vault-kit#263's admission or a #167 ruling that names the id (event-triggered)", FAIL_CLOSED),
    "ENDPOINT_LEDGER_EMPTY_NOT_A_GENESIS": (
        "ENDPOINT_LEDGER_HAS_A_SEALED_GENESIS",
        "an endpoint ledger whose head walks back to a sealed genesis of the designated genesis_class; an empty or "
        "missing ledger is never taken as a genesis", GOAL,
        "on the endpoint's genesis append and its read-back (event-triggered)", FAIL_CLOSED),
    "ENDPOINT_LEDGER_UNREADABLE": (
        "ENDPOINT_LEDGER_CHAIN_SEALED_AND_LINKED", "every receipt sealed (receipt_sha256 is the digest of the rest) "
        "and linked to its predecessor, ending at a genesis of the designated genesis_class", GOAL,
        "on the next read-back of the designated store", FAIL_CLOSED),
    "ENDPOINT_LEDGER_GENESIS_NOT_PINNED": (
        "ENDPOINT_LEDGER_GENESIS_PINNED_BY_DESIGNATION",
        "expected_genesis_receipt_sha256 set from the receipted genesis by the endpoint's own genesis-pin "
        "transition (the #431 pre-pin receiver pattern)", GOAL,
        "after the endpoint's genesis pin transition is admitted (event-triggered)", FAIL_CLOSED),
    "ENDPOINT_LEDGER_GENESIS_MISMATCH": (
        "ENDPOINT_LEDGER_GENESIS_PINNED_BY_DESIGNATION", "the store's genesis equal to the designation's pin", GOAL,
        "on the next read-back of the designated store", FAIL_CLOSED),
    "KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED": (
        "KV_LEDGER_HEAD_SIGNED_BY_KV_LEDGER_HEAD_SIGNER",
        "a kv_ledger_head_signer public-key reference published in .stegverse/node-ledger/"
        "kv-ledger-head-signers.v1.json by an admitted change carrying TV/TVC's publication receipt", SIGNER_GOAL,
        "on the kv_ledger_head_signer publication event", FAIL_CLOSED),
    "KV_LEDGER_HEAD_NOT_AUTHENTICATED": (
        "KV_LEDGER_HEAD_SIGNED_BY_KV_LEDGER_HEAD_SIGNER",
        "a stegverse.kv-ledger-head-attestation/v1 over exactly this endpoint, store location, genesis and head, "
        "Ed25519-signed by a published kv_ledger_head_signer key", SIGNER_GOAL,
        "on the next signed head (event-triggered)", FAIL_CLOSED),
    "KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY": (
        "KV_RECEIPT_CHAIN_DESIGNATION_KEYS_CLOSED",
        "a designation whose every key is in the closed schema (continuity-vault-kit#263 @bf684aad "
        "runtime.kv_receipt_ledgers.CONTRACT_KEY_SCHEMA, LC-KV-24; DESIGNATION_KEY_SCHEMA here)", LANE_D_GOAL,
        "on an admitted change to the endpoint's own contract that removes the key (event-triggered)", FAIL_CLOSED),
    "KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED": (
        "ROLLBACK_WATERMARK_SOURCED_FROM_KV_OWN_RECEIPT_CHAIN",
        f"a rollback watermark sourced from KV's own recorded receipt chain head ({WATERMARK_SOURCE}); an Org-linked "
        f"head ({ORG_CROSS_CHECK_SOURCE}) may appear only as the optional digest-only org_crossing_cross_check "
        f"({CROSS_CHECK_ROLE}), never as the watermark source", LANE_D_GOAL,
        "on the corrected designation or call (event-triggered)", FAIL_CLOSED),
    "KV_LEDGER_HEAD_ROLLBACK_WATERMARK_MISSING": (
        "ROLLBACK_WATERMARK_SUPPLIED",
        f'recorded_head = {{"source": "{WATERMARK_SOURCE}", "head_receipt_sha256": "sha256:<64 hex>"}}: the newest '
        'head KV recorded on its own receipt chain (optionally with a digest-only "org_crossing_cross_check" of the '
        "Org's side of a crossing, never the watermark)", LANE_D_GOAL, "on the corrected call", FAIL_CLOSED),
    "KV_LEDGER_HEAD_ROLLBACK_DETECTED": (
        "ENDPOINT_HEAD_NOT_OLDER_THAN_THE_NEWEST_KV_RECORDED_HEAD",
        f"present a ledger whose chain contains the newest head KV recorded on its own receipt chain "
        f"({WATERMARK_SOURCE}); an older or forked head is refused", GOAL,
        "on a read-back at or after the recorded head (event-triggered)", DENY),
    "INTR_CROSSING_NOT_RECORDED_BY_BOTH_SIDES": (
        "EACH_CROSSING_RECORDED_BY_BOTH_ENDPOINTS",
        "the crossing's egress record on the source side and its ingress record on the destination side, each "
        "pointing at the other's record by digest (never a copied body); a one-sided crossing is not continuity",
        CROSSING_GOAL, "on the read-back of the missing side's record (event-triggered)", FAIL_CLOSED),
    "HB_EPOCH_NOT_SUPPLIED": (
        supplied_epoch.EPOCH_PREDICATE,
        "the crossing record's hb_reference with a supplied epoch (derived_from_clock false) and observed_at "
        "SUPPLIED_HB_EPOCH:<epoch> (StegVerse-Labs/.github#3263/#3290)", CROSSING_GOAL,
        "on a crossing record appended with the supplied epoch (event-triggered)", FAIL_CLOSED),
    "HB_EPOCH_INVALID": (
        supplied_epoch.EPOCH_PREDICATE,
        "a supplied epoch: ASCII [0-9]+, at least 32, derived_from_clock exactly false, observed_at "
        "SUPPLIED_HB_EPOCH:<epoch>", CROSSING_GOAL,
        "on a crossing record appended with the supplied epoch (event-triggered)", FAIL_CLOSED),
})
#: cvk#263 @bf684aad failure_class for the codes it shares
FAILURE_CLASS = MappingProxyType({ORG_SOURCED_CODE: "A", WATERMARK_MISSING_CODE: "A", UNKNOWN_KEY_CODE: "C",
                                  MEMBERSHIP_CODE: "C"})


def refusal(code: str, detail: str, **extra: Any) -> dict[str, Any]:
    predicate, repair, goal, next_attempt, disposition = CODES[code]
    if code in FAILURE_CLASS:
        extra = {"failure_class": FAILURE_CLASS[code], **extra}
    return {"schema": RESULT_SCHEMA, "disposition": disposition, "failure_code": code,
            "failed_predicate": predicate, "required_evidence_or_repair": f"{repair} ({detail})",
            "retry_entrypoint": ENTRYPOINT, "owning_existing_goal": goal, "next_attempt": next_attempt, **extra,
            "ledger_written": False, "authority_effect": "NONE_READ_ONLY"}


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") \
        and all(c in "0123456789abcdef" for c in value[7:])


def _membership_like(key: str) -> bool:
    """cvk#263 @bf684aad _membership_like: a snake/camel token of `key` is in MEMBERSHIP_TOKENS. Pure."""
    tokens = re.split(r"[^a-z0-9]+", re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", key).lower())
    return any(t in MEMBERSHIP_TOKENS for t in tokens)


def _store_key_schema(store: Any) -> dict[str, None]:
    keys = STORE_KEYS[GIT_REF] if isinstance(store, Mapping) and store.get("store_type") == GIT_REF \
        else CVK_STORE_KEYS
    return {k: None for k in keys}


#: a bare designation's closed key schema: cvk's ledger_designation level (a GIT_REF store, ORG only, has its keys)
DESIGNATION_KEY_SCHEMA: Mapping[str, Any] = MappingProxyType({
    **{k: None for k in CVK_DESIGNATION_KEYS}, "stores": [_store_key_schema],
    "rollback_watermark_source": dict(WATERMARK_KEY_SCHEMA)})


def closed_key_failure(node: Any, schema: Any = DESIGNATION_KEY_SCHEMA, path: str = "") -> tuple[str, str] | None:
    """(code, reason) for the first key outside the closed schema, or None (cvk#263 @bf684aad _closed_schema). A
    membership-like unknown key is ENDPOINT_ORG_MEMBERSHIP_REFUSED, any other KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY.
    Leaves must not carry keys. Pure."""
    if callable(schema):
        schema = schema(node)
    if isinstance(node, Mapping):
        allowed = schema if isinstance(schema, Mapping) else {}
        for k, v in node.items():
            if not isinstance(k, str) or k not in allowed:
                key = str(k)
                if _membership_like(key):
                    return MEMBERSHIP_CODE, (f"{path}{key} is not a permitted key and is membership-like (an org, "
                                             "membership, team, app-installation, permission or owner binding)")
                return UNKNOWN_KEY_CODE, f"{path}{key} is not a permitted key of the closed designation schema"
            hit = closed_key_failure(v, allowed[k], f"{path}{k}.")
            if hit:
                return hit
    elif isinstance(node, list):
        item = schema[0] if isinstance(schema, list) and schema else None
        for i, v in enumerate(node):
            hit = closed_key_failure(v, item, f"{path}{i}.")
            if hit:
                return hit
    return None


def contract_key_failure(contract: Any) -> dict[str, Any] | None:
    """Six-field refusal for a KV receipt-chain contract with a key outside CONTRACT_KEY_SCHEMA, else None. Pure."""
    hit = closed_key_failure(contract, CONTRACT_KEY_SCHEMA) if isinstance(contract, Mapping) else None
    return refusal(*hit) if hit else None


def org_membership_binding(designation: Any) -> str | None:
    """Why an endpoint designation binds the endpoint as an Org member (a membership-like key outside the closed
    schema, at any depth), or None. The ORG designation is the Org's own and is not an endpoint. Pure."""
    if not isinstance(designation, Mapping) or designation.get("endpoint_kind") == ORG:
        return None
    hit = closed_key_failure(designation)
    return hit[1] if hit and hit[0] == MEMBERSHIP_CODE else None


def _org_sourced(value: Any) -> bool:
    """cvk#263 @bf684aad _org_sourced: a watermark source naming the Org ledger or an Org-side head. Pure."""
    if not isinstance(value, str):
        return False
    tokens = set(re.split(r"[^A-Z0-9]+", value.upper()))
    return value == ORG_CROSS_CHECK_SOURCE or bool(tokens & {"ORG", "ORGANIZATION"}) \
        or any(m in value for m in ORG_MARKERS)


def crossing_path_ids(designation: Mapping[str, Any]) -> list[str]:
    """The cross-check path_ids (optional; never the watermark). Pure."""
    w = designation.get("rollback_watermark_source")
    xc = w.get("org_crossing_cross_check") if isinstance(w, Mapping) else None
    ids = xc.get("path_ids") if isinstance(xc, Mapping) else None
    return list(ids) if isinstance(ids, list) else []


def watermark_source_failure(designation: Mapping[str, Any]) -> dict[str, Any] | None:
    """Six-field refusal unless rollback_watermark_source is {source: KV_RECORDED_RECEIPT_CHAIN_HEAD} with at most
    the digest-only org_crossing_cross_check (KV, SKAP_VAULT), or null (ORG). Pure."""
    kind, w = designation.get("endpoint_kind"), designation.get("rollback_watermark_source")
    if kind not in INDEPENDENT_KINDS:
        return None if w is None else refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"{kind} carries no "
                                              f"rollback_watermark_source; got {w!r}")
    source = w.get("source") if isinstance(w, Mapping) else None
    if source != WATERMARK_SOURCE and _org_sourced(source):
        return refusal(ORG_SOURCED_CODE, f"ledger_designation.rollback_watermark_source.source is {source!r}")
    xc = w.get("org_crossing_cross_check") if isinstance(w, Mapping) else None
    ids = xc.get("path_ids") if isinstance(xc, Mapping) else None
    if not isinstance(w, Mapping) or source != WATERMARK_SOURCE \
            or (xc is not None and (not isinstance(xc, Mapping) or xc.get("source") != ORG_CROSS_CHECK_SOURCE
                                    or xc.get("role") != CROSS_CHECK_ROLE or not isinstance(ids, list) or not ids
                                    or not all(isinstance(p, str) and p.endswith(":intr-destination")
                                               for p in ids))):
        return refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"rollback_watermark_source must be {{source: "
                       f"{WATERMARK_SOURCE}}} with an optional org_crossing_cross_check {{source: "
                       f"{ORG_CROSS_CHECK_SOURCE}, path_ids: [..:intr-destination], role: {CROSS_CHECK_ROLE}}} "
                       f"(required for KV and SKAP_VAULT); got {w!r}"[:400])
    return None


def designation_failure(designation: Any) -> dict[str, Any] | None:
    """Six-field refusal unless `designation` is well formed for its endpoint kind. Pure.

    Order (cvk#263 @bf684aad designation()): a KV or SKAP_VAULT store on a git ref (KV_LEDGER_DESIGNATED_ON_GIT_REF);
    then the closed key schema: a membership-like unknown key (ENDPOINT_ORG_MEMBERSHIP_REFUSED), any other unknown
    key (KV_RECEIPT_CHAIN_DESIGNATION_UNKNOWN_KEY); then an Org-sourced watermark
    (KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED); then the exact shape."""
    d = designation
    if not isinstance(d, Mapping):
        return refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"got {d!r}"[:400])
    kind = d.get("endpoint_kind")
    stores = d.get("stores") if isinstance(d.get("stores"), list) else []
    if kind in INDEPENDENT_KINDS:
        for store in stores:
            if isinstance(store, Mapping) and (store.get("store_type") == GIT_REF
                                               or any(k in store for k in ("repository", "ref", "namespace"))):
                return refusal("KV_LEDGER_DESIGNATED_ON_GIT_REF", f"{kind} {d.get('endpoint_id')} designates "
                               f"{dict(store)!r}")
    if kind != ORG:
        hit = closed_key_failure(d)
        if hit:
            return refusal(hit[0], f"{kind} {d.get('endpoint_id')!r}: {hit[1]}")
        failed = watermark_source_failure(d)
        if failed and failed["failure_code"] == ORG_SOURCED_CODE:
            return failed
    if tuple(sorted(d)) != DESIGNATION_KEYS or d.get("schema") != SCHEMA \
            or not isinstance(d.get("endpoint_id"), str) or not d["endpoint_id"] \
            or kind not in STORE_TYPE_OF or not isinstance(d.get("genesis_class"), str) \
            or not d["genesis_class"] or d.get("provider_selection") not in SELECTION_RULES \
            or not stores or not all(isinstance(s, Mapping) for s in stores):
        return refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"got {d!r}"[:400])
    if kind != ORG:   # a node (PERMANENT) ledger on the org ledger would make the node an org-ledger source
        if kind not in INDEPENDENT_KINDS:
            return refusal("ENDPOINT_NOT_AN_ORG_LEDGER_SOURCE", f"{kind} {d['endpoint_id']} would be designated on "
                           f"{[s.get('ref') for s in stores]}; {kind} has no admitted store type off the org "
                           "ledger yet")
    for store in stores:
        st = store.get("store_type")
        if st not in STORE_TYPES:
            return refusal("ENDPOINT_LEDGER_STORE_TYPE_UNDECLARED", f"store_type {st!r}")
        if st != STORE_TYPE_OF[kind]:
            return refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"{kind} uses {STORE_TYPE_OF[kind]}, not {st}")
        if tuple(sorted(store)) != STORE_KEYS[st] or not all(isinstance(store[k], str) and store[k] for k in store):
            return refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"a {st} store has exactly {list(STORE_KEYS[st])}"
                           " as non-empty strings (no storage-side record or external ledger ref)")
        if st == KV_STORAGE_ENDPOINT and (store["storage_endpoint_schema"] != STORAGE_ENDPOINT_SCHEMA
                                          or ACCESS_ADAPTERS.get(store["provider_id"]) != store["access_adapter"]
                                          or store["kv_class"] != KV_CLASS
                                          or store["location"] != KV_CHAIN_LOCATIONS[kind]):
            return refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"a {KV_STORAGE_ENDPOINT} store names "
                           f"storage_endpoint_schema {STORAGE_ENDPOINT_SCHEMA}, a documented provider_id/access_adapter "
                           f"pair {ACCESS_ADAPTERS}, kv_class {KV_CLASS} and location {KV_CHAIN_LOCATIONS[kind]} for "
                           f"{kind}; got {dict(store)!r}")
    if d["head_signer_source"] != HEAD_SIGNER_OF[kind]:
        return refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"{kind} heads are signed by "
                       f"{HEAD_SIGNER_OF[kind]}, not {d['head_signer_source']!r}")
    failed = watermark_source_failure(d)
    if failed:
        return failed
    g = d["expected_genesis_receipt_sha256"]
    if g is not None and not _is_digest(g):
        return refusal("ENDPOINT_LEDGER_DESIGNATION_INVALID", f"expected_genesis_receipt_sha256 {g!r}")
    return None


def select_store(designation: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """SINGLE_PROVIDER_V1: exactly one store, selected by list order (stores[0]). Pure."""
    failed = designation_failure(designation)
    if failed:
        return None, failed
    stores = designation["stores"]
    if len(stores) != 1:
        return None, refusal("ENDPOINT_LEDGER_MULTI_PROVIDER_NOT_SUPPORTED", f"{len(stores)} stores designated "
                             f"({[s.get('provider_id', s.get('provider')) for s in stores]}); {SINGLE_PROVIDER_V1} "
                             "accepts one")
    return dict(stores[0]), None


def store_location(store: Mapping[str, Any]) -> str:
    if store["store_type"] == GIT_REF:
        return f"{store['ref']}:{store['namespace']}"
    return f"storage-endpoint:{store['provider_id']}/{store['location']}"   # cvk#263 designation()["store_location"]


# -- head signers and the KV head attestation ---------------------------------------------------------------

def load_head_signers(source: str) -> list[dict[str, Any]]:
    """Published head-signer references for a designated source (empty until published)."""
    path, signs = HEAD_SIGNER_FILES[source]
    try:
        published = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(published, Mapping) or published.get("schema") != SIGNERS_SCHEMA:
        return []
    return [dict(k) for k in published.get("signers") or [] if isinstance(k, Mapping) and k.get("signs") == signs]


def kv_head_attestation_body(designation: Mapping[str, Any], store: Mapping[str, Any], genesis_sha: str,
                             head_sha: str) -> dict[str, Any]:
    return {"schema": KV_HEAD_ATTESTATION_SCHEMA, "endpoint_id": designation["endpoint_id"],
            "store_location": store_location(store), "genesis_receipt_sha256": genesis_sha,
            "head_receipt_sha256": head_sha, "signer_role": KV_SIGNER_ROLE}


def kv_head_attestation_message(body: Mapping[str, Any]) -> bytes:
    return KV_HEAD_ATTESTATION_SCHEMA.encode("utf-8") + b"\n" + hne.canon(dict(body))


def _b64(value: Any) -> bytes | None:
    try:
        return base64.b64decode(value, validate=True) if isinstance(value, str) else None
    except (binascii.Error, ValueError):
        return None


def kv_head_failure(designation: Mapping[str, Any], store: Mapping[str, Any], genesis_sha: str, head_sha: str,
                    attestation: Any, signers: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Six-field refusal unless a published kv_ledger_head_signer signed exactly this head. Pure."""
    if not signers:
        return refusal("KV_LEDGER_HEAD_SIGNER_NOT_PUBLISHED", "kv-ledger-head-signers.v1.json is NONE_PUBLISHED")
    if not isinstance(attestation, Mapping):
        return refusal("KV_LEDGER_HEAD_NOT_AUTHENTICATED", f"no {KV_HEAD_ATTESTATION_SCHEMA} for head {head_sha}")
    body = {k: attestation.get(k) for k in KV_HEAD_ATTESTATION_FIELDS}
    if body != kv_head_attestation_body(designation, store, genesis_sha, head_sha):
        return refusal("KV_LEDGER_HEAD_NOT_AUTHENTICATED", "the attestation names another endpoint, location, "
                       f"genesis or head than the store holds (head {head_sha})")
    key = next((k for k in signers if k.get("key_id") == attestation.get("key_id")), None)
    public, signature = _b64((key or {}).get("public_key_b64")), _b64(attestation.get("signature_b64"))
    if key is None or public is None or len(public) != 32 or signature is None or len(signature) != 64 \
            or not ed25519_verify.verify(public, kv_head_attestation_message(body), signature):
        return refusal("KV_LEDGER_HEAD_NOT_AUTHENTICATED", "not by a published key, or the signature does not verify")
    return None


# -- the rollback watermark ---------------------------------------------------------------------------------

def kv_watermark(recorded_head: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """The rollback watermark input (cvk#263 @bf684aad _watermark): {"source": KV_RECORDED_RECEIPT_CHAIN_HEAD,
    "head_receipt_sha256": sha256[, "org_crossing_cross_check": sha256]}, or (None, six-field refusal). The
    cross-check digest is echoed with authority NONE and never compared as the watermark. Pure."""
    if recorded_head is None:
        return None, refusal(WATERMARK_MISSING_CODE, "no recorded_head supplied")
    if not isinstance(recorded_head, Mapping):
        return None, refusal(WATERMARK_MISSING_CODE, f"recorded_head {recorded_head!r} does not declare its source "
                                                     f"(expected a mapping with source {WATERMARK_SOURCE})")
    source = recorded_head.get("source")
    if source != WATERMARK_SOURCE and _org_sourced(source):
        return None, refusal(ORG_SOURCED_CODE, f"recorded_head.source is {source!r}")
    xc = recorded_head.get("org_crossing_cross_check")
    if source != WATERMARK_SOURCE or set(recorded_head) - set(WATERMARK_INPUT_KEYS) \
            or not _is_digest(recorded_head.get("head_receipt_sha256")) or (xc is not None and not _is_digest(xc)):
        return None, refusal(WATERMARK_MISSING_CODE, f"recorded_head {dict(recorded_head)!r} is not a "
                                                     f"{WATERMARK_SOURCE} watermark with head_receipt_sha256 "
                                                     "sha256:<64 hex>")
    out = {"source": WATERMARK_SOURCE, "head_receipt_sha256": recorded_head["head_receipt_sha256"]}
    if xc is not None:
        out["org_crossing_cross_check"] = {"digest": xc, "role": CROSS_CHECK_ROLE, "authority_effect": "NONE"}
    return out, None


def _boundary_fields(receipt: Any) -> dict[str, Any]:
    """path_id and endpoint_head_sha256 as an Org record carries them: in boundary_evidence (the receipt's, or its
    evidence's), or, for records written before the typed body moved them there, in evidence. Pure."""
    if not isinstance(receipt, Mapping):
        return {}
    ev = receipt.get("evidence") if isinstance(receipt.get("evidence"), Mapping) else {}
    out: dict[str, Any] = {}
    for holder in (ev, ev.get("boundary_evidence"), receipt.get("boundary_evidence")):
        if isinstance(holder, Mapping):
            out.update({k: holder[k] for k in ("path_id", ENDPOINT_HEAD_KEY) if k in holder})
    return out


def _org_crossings(org_chain: list[Mapping[str, Any]], path_ids: set[str]) -> list[tuple[Mapping[str, Any], Any]]:
    """(Org record, endpoint head digest or None) for this endpoint's path_ids, org-chain order. Pure."""
    out = []
    for receipt in org_chain:
        fields = _boundary_fields(receipt)
        if fields.get("path_id") in path_ids:
            head = fields.get(ENDPOINT_HEAD_KEY)
            out.append((receipt, head if _is_digest(head) else None))
    return out


def org_crossing_receipt_failure(record: Mapping[str, Any], designation: Mapping[str, Any]) -> dict[str, Any] | None:
    """Six-field refusal unless an Org-chain crossing receipt for an endpoint path is digest-only and the org's own
    (no endpoint originates it; #160 comment 6372871021). Pure."""
    ev = record.get("evidence") if isinstance(record.get("evidence"), Mapping) else {}
    be = ev.get("boundary_evidence") if isinstance(ev.get("boundary_evidence"), Mapping) else {}
    endpoint = designation.get("endpoint_id")
    named = [k for k in ORIGINATOR_KEYS for where in (record, ev, be) if where.get(k) not in (None, "")
             and (where.get(k) == endpoint or str(where.get(k)).startswith(KV_CLASS))]
    if named:
        return refusal("ENDPOINT_NOT_AN_ORG_LEDGER_SOURCE", f"Org record {record.get('receipt_sha256')} names "
                       f"{endpoint} as its originator ({sorted(set(named))})")
    extra = sorted(set(ev) - ORG_CROSSING_EVIDENCE_KEYS) + sorted(f"boundary_evidence.{k}"
                                                                 for k in set(be) - ORG_CROSSING_BOUNDARY_KEYS)
    digests = [k for k in ("source_repository_receipt_sha256",) if k in ev and not _is_digest(ev[k])]
    if extra or digests:
        return refusal("ORG_CROSSING_RECEIPT_NOT_DIGEST_ONLY", f"Org record {record.get('receipt_sha256')} carries "
                       f"{extra + digests} (a copied body or a non-digest), not only pointers and digests")
    return None


def crossing_failure(chain: list[Mapping[str, Any]], org_chain: list[Mapping[str, Any]],
                     designation: Mapping[str, Any]) -> dict[str, Any] | None:
    """Both sides recorded each crossing of this endpoint's paths, each with a supplied epoch. Pure.

    Org side -> endpoint side: every Org record for the designation's cross-check path_ids names an endpoint_head_sha256 (a digest
    pointer) that is on the presented chain. Endpoint side -> Org side: every endpoint ingress record names, by
    digest, the Org-side record it ingested (source_repository_receipt_sha256 or organization_receipt_sha256), and
    that record is on the Org chain."""
    path_ids = set(crossing_path_ids(designation))
    on_chain = {r.get("receipt_sha256") for r in chain}
    org_digests = set()
    for r in org_chain:
        if isinstance(r, Mapping):
            org_digests |= {r.get("receipt_sha256"), r.get("repo_receipt_sha256")}
    org_digests.discard(None)
    for record, head in _org_crossings(org_chain, path_ids):
        failed = org_crossing_receipt_failure(record, designation)
        if failed:
            return failed
        if head is None or head not in on_chain:
            return refusal("INTR_CROSSING_NOT_RECORDED_BY_BOTH_SIDES", f"the Org record "
                           f"{record.get('receipt_sha256')} names endpoint head {head}, which the presented chain does "
                           "not hold", one_sided="ORG_ONLY")
        failed = supplied_epoch.record_epoch_failure(record)
        if failed:
            return refusal(failed[0], f"Org record {record.get('receipt_sha256')}: {failed[1]}")
    for record in chain:
        if record.get("transition_class") not in CROSSING_CLASSES:
            continue
        ev = record.get("evidence") if isinstance(record.get("evidence"), Mapping) else {}
        if record.get("transition_class") == INGRESS_CLASS:
            peer = ev.get("source_repository_receipt_sha256") or ev.get("organization_receipt_sha256")
            if not _is_digest(peer) or peer not in org_digests:
                return refusal("INTR_CROSSING_NOT_RECORDED_BY_BOTH_SIDES", f"the endpoint ingress record "
                               f"{record.get('receipt_sha256')} points at {peer!r}, which the Org chain does not hold",
                               one_sided="ENDPOINT_ONLY")
        failed = supplied_epoch.record_epoch_failure(record)
        if failed:
            return refusal(failed[0], f"endpoint record {record.get('receipt_sha256')}: {failed[1]}")
    return None


def rollback_failure(chain: list[Mapping[str, Any]], watermark: Mapping[str, Any]) -> dict[str, Any] | None:
    """DENY KV_LEDGER_HEAD_ROLLBACK_DETECTED when the newest head KV recorded on its own receipt chain (the
    kv_watermark) is not on the presented chain (the presented head is older, or a fork). Pure."""
    newest = watermark["head_receipt_sha256"]
    if newest in {r.get("receipt_sha256") for r in chain}:
        return None
    return refusal("KV_LEDGER_HEAD_ROLLBACK_DETECTED", f"KV recorded {newest} on its own receipt chain; the presented "
                   f"head is {chain[0].get('receipt_sha256') if chain else None}", recorded_head_sha256=newest)


# -- what every reader's output must satisfy ----------------------------------------------------------------

def chain_failure(designation: Mapping[str, Any], chain: Any) -> dict[str, Any] | None:
    """Empty, unsealed, unlinked or wrong-genesis chains are refused, for every store type. Pure."""
    if not isinstance(chain, list) or not chain:
        return refusal("ENDPOINT_LEDGER_EMPTY_NOT_A_GENESIS", "the store holds no receipts")
    for i, r in enumerate(chain):
        body = {k: v for k, v in r.items() if k != "receipt_sha256"} if isinstance(r, Mapping) else None
        if body is None or not _is_digest(r.get("receipt_sha256")) or hne.sha(body) != r["receipt_sha256"]:
            return refusal("ENDPOINT_LEDGER_UNREADABLE", f"receipt {i} is not sealed")
        expected_previous = chain[i + 1]["receipt_sha256"] if i + 1 < len(chain) else None
        if r.get("previous_receipt_sha256") != expected_previous:
            return refusal("ENDPOINT_LEDGER_UNREADABLE", f"receipt {i} does not link to its predecessor")
    if chain[-1].get("transition_class") != designation["genesis_class"]:
        return refusal("ENDPOINT_LEDGER_EMPTY_NOT_A_GENESIS", f"the chain ends at "
                       f"{chain[-1].get('transition_class')!r}, not a {designation['genesis_class']} genesis")
    pin = designation["expected_genesis_receipt_sha256"]
    if pin is None:
        return refusal("ENDPOINT_LEDGER_GENESIS_NOT_PINNED", "expected_genesis_receipt_sha256 is null")
    if chain[-1]["receipt_sha256"] != pin:
        return refusal("ENDPOINT_LEDGER_GENESIS_MISMATCH", f"the store's genesis is {chain[-1]['receipt_sha256']}, "
                       f"the designation pins {pin}")
    return None


def chain_admission_failure(designation: Mapping[str, Any], store: Mapping[str, Any], chain: Any, *,
                            head_attestation: Any, signers: list[Mapping[str, Any]],
                            org_chain: list[Mapping[str, Any]] | None,
                            recorded_head: Any = None) -> dict[str, Any] | None:
    """The checks every store type's reader output passes before anything reads it. Pure.

    KV and SKAP_VAULT: head signed, then the required KV-recorded watermark (independent of any Org chain or
    declared path), then both sides of each crossing."""
    failed = chain_failure(designation, chain)
    if failed:
        return failed
    if designation["endpoint_kind"] not in INDEPENDENT_KINDS:
        return None
    failed = kv_head_failure(designation, store, chain[-1]["receipt_sha256"], chain[0]["receipt_sha256"],
                             head_attestation, signers)
    if failed:
        return failed
    watermark, failed = kv_watermark(recorded_head)
    if failed:
        return failed
    failed = rollback_failure(chain, watermark)
    if failed:
        return failed
    if isinstance(org_chain, list):
        return crossing_failure(chain, org_chain, designation)
    crossing = next((r for r in chain if r.get("transition_class") in CROSSING_CLASSES), None)
    if crossing is not None:
        return refusal("INTR_CROSSING_NOT_RECORDED_BY_BOTH_SIDES", f"the endpoint crossing record "
                       f"{crossing.get('receipt_sha256')} cannot be matched: no Org chain supplied",
                       one_sided="ENDPOINT_ONLY")
    return None


# -- the reader seam ----------------------------------------------------------------------------------------

@contextlib.contextmanager
def _git_ref_reader(designation: Mapping[str, Any], store: Mapping[str, Any], source: Any,
                    head_attestation: Any) -> Iterator[tuple[list[dict[str, Any]] | None, tuple[str, str] | None]]:
    """GIT_REF: the existing git reader, unchanged, for the location the repository contract designates."""
    designated = org_ledger_location.org_ledger_location()
    if designated is None or (store["repository"], store["ref"], store["namespace"]) != \
            (designated["repository"], designated["ref"], designated["namespace"]):
        yield None, ("ORG_LEDGER_LOCATION_NOT_DESIGNATED", f"{store_location(store)} is not the location the "
                     "repository contract designates")
        return
    with org_ledger_location.designated_org_ledger(source, head_attestation) as (root, failed):
        if failed:
            yield None, failed
            return
        chain, failure, detail = hne.read_chain(root)
        yield (None, ("ENDPOINT_LEDGER_UNREADABLE", f"{failure}: {detail}")) if failure else (chain, None)


#: store_type -> reader. KV_STORAGE_ENDPOINT has none until an access adapter is admitted by its own change.
_READERS: dict[str, Any] = {GIT_REF: _git_ref_reader}
READERS = MappingProxyType(_READERS)


@contextlib.contextmanager
def read_designated(designation: Any, *, source: Any, head_attestation: Any = None,
                    org_chain: list[Mapping[str, Any]] | None = None,
                    recorded_head: Any = None) -> Iterator[tuple[Any, Any]]:
    """Yield (chain, None) for an admitted read of the designated ledger, or (None, six-field refusal)."""
    store, failed = select_store(designation)
    if failed:
        yield None, failed
        return
    reader = READERS.get(store["store_type"])
    if reader is None:
        yield None, refusal("KV_RECEIPT_CHAIN_READER_ID_NOT_DOCUMENTED", f"no admitted {store['store_type']} reader "
                            f"for {store_location(store)} ({store.get('provider_id')}); cvk's "
                            f"{READER_ENTRYPOINTS[0]} is referenced, not vendored",
                            store_type=store["store_type"], reader_id=READER_ID,
                            reader_entrypoints=list(READER_ENTRYPOINTS))
        return
    with reader(designation, store, source, head_attestation) as (chain, reason):
        if reason:
            code, detail = reason
            if code in CODES:
                yield None, refusal(code, detail)
            else:   # the git reader's own six-field codes (ORG_LEDGER_*, MERGE_APPEND_PATH_NOT_ADMITTED)
                yield None, {**refusal("ENDPOINT_LEDGER_UNREADABLE", f"{code}: {detail}"), "failure_code": code,
                             "reader_failure_code": code}
            return
        if not chain:
            yield None, refusal("ENDPOINT_LEDGER_EMPTY_NOT_A_GENESIS", "the reader yielded no receipts")
            return
        signers = load_head_signers(designation["head_signer_source"])
        failed = chain_admission_failure(designation, store, chain, head_attestation=head_attestation,
                                         signers=signers, org_chain=org_chain, recorded_head=recorded_head)
        yield (None, failed) if failed else (chain, None)


__all__ = ["CODES", "CONTRACT_KEY_SCHEMA", "CROSS_CHECK_ROLE", "DESIGNATION_KEY_SCHEMA", "GIT_REF",
           "KV_STORAGE_ENDPOINT", "MEMBERSHIP_CODE", "MEMBERSHIP_TOKENS", "ORG_CROSS_CHECK_SOURCE", "ORG_SOURCED_CODE",
           "READERS", "SCHEMA", "SINGLE_PROVIDER_V1", "STORE_TYPES", "UNKNOWN_KEY_CODE", "WATERMARK_MISSING_CODE",
           "WATERMARK_SOURCE", "chain_admission_failure", "chain_failure", "closed_key_failure",
           "contract_key_failure", "crossing_failure", "crossing_path_ids", "designation_failure",
           "kv_head_attestation_body", "kv_head_attestation_message", "kv_head_failure", "kv_watermark",
           "load_head_signers", "org_membership_binding", "read_designated", "refusal", "rollback_failure",
           "select_store", "store_location", "watermark_source_failure"]
