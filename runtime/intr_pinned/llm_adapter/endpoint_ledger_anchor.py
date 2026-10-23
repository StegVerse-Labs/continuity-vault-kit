"""LC-KV-13: bind healthy_node_ledger_root only to an endpoint ledger the organization ledger anchors.

This is the Org InTr protocol extended to ecosystem edges, not a new mechanism.
Every endpoint (an organization's .github, KV, SKAP Vault, a permanent node, a
temporary node) runs the same InTr ingress/egress with its own ledger that
corresponds to the Org Ledger. Gateway nodes, which are only ingress/egress for
external frameworks, are different: the external endpoint's ledger never
crosses the boundary, and the Org Ledger carries the node's ledger.

Endpoint kinds (`endpoint_kind`) and how each is anchored
--------------------------------------------------------
* ``EPHEMERAL``: a temporary StegApp, StegBrowser or StegNode generated through
  StegOS. It has its own ledger with ``ledger_lifetime``
  BOUNDED_UNTIL_DISSOLUTION. Its anchor is the NODE_LEDGER_OPENED record that
  StegOS emits at generation time (StegVerse-Labs/StegOS
  stegos/ephemeral_node_ledger_open.py, on the #426 profile path). The record
  binds node_id, node_identity_key and the ledger's genesis hash, and it is
  carried to the org ledger as the body of the InTr path pair below. At
  NODE_DISSOLUTION the whole chain is disbursed back to the org ledger
  (llm_adapter.node_ledger_dissolution), after which the root is inadmissible.
* ``PERMANENT``, ``KV``, ``SKAP_VAULT`` (own ledger, no dissolution). The
  ledger corresponds to the org ledger for as long as it exists. Its anchor body
  is stegverse.endpoint-ledger-anchor/v1 {node_id, endpoint_kind,
  ledger_lifetime, node_identity_key, genesis_receipt_sha256,
  pinned_code_digests_sha256}.
  Every own-ledger kind opens with a REPOSITORY_LEDGER_INITIALIZATION genesis
  naming the node, its kind, its lifetime, its ``node_identity_key`` (a
  public-key reference only) and the pinned code digests. It is anchored by an
  InTr path receipt pair, the same two halves as StegVerse-org/.github
  data/intr-protocol/v1/protocol.json ``mesh_path_transfer``:
    - source half, on the endpoint ledger: an INTR_MESH_PATH_TRANSFER receipt
      (evidence stegverse.intr-path-transfer-evidence/v1) carrying an
      ecosystem.communication message whose body is the anchor body;
    - destination half, on the org-ledger location
      repository-ledger/StegVerse-org/LLM-adapter (#431): an
      INTR_MESH_PATH_INGRESS receipt, operation
      ORGANIZATION_INTR_DESTINATION_INGRESS (evidence
      stegverse.intr-path-ingress-evidence/v1) linking the source half by seal,
      with the source half retained under source-receipts/<hex>.json (the
      protocol's dual-ledger retained copy).
* ``GATEWAY`` (org-carried). The node's chain is a location inside the org
  ledger, node-ledger/StegVerse-org/<node_id>, like
  repository-ledger/<org>/<repo>. Its anchor is that location's
  REPOSITORY_LEDGER_INITIALIZATION genesis. The root is derived from the org
  ledger root and the node_id, never taken from the caller, and no external
  chain is ever imported (an INTR_MESH_PATH_TRANSFER on it is refused).
* ``ORG``: an organization's .github ledger itself. It is not a node health
  root, so binding it here is FAIL_CLOSED.

What counts on an anchored ledger
---------------------------------
Every receipt after genesis must be one the pinned code writes
(.stegverse/node-ledger/pinned-code-digests.v1.json; the evaluator digest is
fdaa2005...1f58), and the running files must hash to those pins. A
NODE_HEALTH_REPORTED receipt must carry the producer's exact transition
manifest and re-derive from the receipts it cites. A receipt is not proof that
those bytes ran: the anchor binds the pin set and this module checks shape,
seal and re-derivation (``producer_provenance`` NOT_PROVEN_BEYOND_PINNED_SHAPE).

Anything unanchored, mismatched, foreign or dissolved is a six-field
FAIL_CLOSED, failure_code EPHEMERAL_NODE_LEDGER_NOT_ANCHORED.

The issued anchor (stegverse.node-ledger-opened/v1, schemas/node-ledger-opened.v1.json)
---------------------------------------------------------------------------------------
For an EPHEMERAL ledger, an ALLOW from ``verify_anchor`` carries
``node_ledger_opened``: exactly {schema, transition_class NODE_LEDGER_OPENED,
node_id, node_identity_key, genesis_receipt_sha256, issuer ORGANIZATION_LEDGER,
issuer_receipt_ref, receipt_sha256}, the shape StegVerse-Labs/continuity-vault-kit
#258 consumes. ``issuer_receipt_ref`` is the org ledger's own INTR_MESH_PATH_INGRESS
receipt that carried StegOS's generation record. ``verify_node_ledger_opened_anchor``
is the ORGANIZATION_LEDGER issuer verifier: it re-derives that anchor from the
pinned org-ledger head and the endpoint ledger, and accepts nothing else.

LC-KV-15 and LC-KV-16 inside the wrapper (``evaluate_anchored``)
-----------------------------------------------------------------
LC-KV-16 (StegVerse-Labs/.github#3330 @c8b8d156) closes three holes:
* Org ledger: only the contract location. The org ledger is read from
  .stegverse/transition-ledger/contract.json ``repository_ledger_location``
  (repository, ref refs/stegverse/organization-ledger, namespace
  repository-ledger/StegVerse-org/LLM-adapter, as #431 designates), through
  llm_adapter.org_ledger_location.designated_org_ledger: a local
  ``git archive`` of that ref and namespace only, from the object store the
  caller names (``org_ledger_git_dir``). No caller-chosen org-ledger path is
  accepted. No designation is ORG_LEDGER_LOCATION_NOT_DESIGNATED; a missing
  ref, namespace or REPOSITORY_LEDGER_INITIALIZATION genesis is
  ORG_LEDGER_LOCATION_UNREADABLE. The head is pinned as before.
* Anchor: signed. An EPHEMERAL anchor body must be
  stegverse.node-ledger-opened-signed/v1 (schemas/node-ledger-opened-signed.v1.json):
  StegOS's record plus an Ed25519 signature verified with the stdlib verifier
  under a key published in
  .stegverse/node-ledger/node-ledger-opened-signers.v1.json (TV/TVC custody;
  bots never hold keys, tests use fixture keys only). Unsigned is
  NODE_LEDGER_OPENED_UNSIGNED, an unpublished key_id
  NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED, a bad signature
  NODE_LEDGER_OPENED_SIGNATURE_INVALID. No signer is published yet.
* Identity: derived from the proof. The node_id comes only from a
  node_identity_key proof, an Ed25519 signature (llm_adapter.ed25519_verify,
  stdlib only) under the anchored genesis key over ``identity_challenge``: a
  deterministic challenge bound to the node, its genesis, the endpoint chain
  head, the anchor receipt and the pinned org-ledger head. ``claimed_node_id``
  is optional, recorded, decides nothing, and must equal the proven node.
  No proof is NODE_IDENTITY_PROOF_ABSENT; a non-verifying one or a different
  claim is NODE_IDENTITY_PROOF_INVALID (failure_code NODE_IDENTITY_NOT_PROVEN).
* Transport: read from receipts, no default. The node's current
  NODE_INGRESS_ADMITTED record on the anchored chain must say transport
  INTERLOCK_INTR with transport_state INSTALLED. Anything else, an absent
  state or a caller-asserted ``transport_state`` included, is six-field
  FAIL_CLOSED INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED. The caller's value is
  recorded and decides nothing.
* Root: only the anchored root above; never a caller-supplied one.
Then llm_adapter.healthy_node_evaluator.evaluate runs unchanged on the anchored
root, with the observed transport state passed explicitly and require_admission
True, so this closes LC-KV-15 without touching the evaluator Lane D vendors
byte-identical.

Determinism: ``plan_*``, ``verify_anchor`` and the checks in
``evaluate_anchored`` read files only, with no clock, network or randomness.
The one I/O boundary is llm_adapter.org_ledger_location: a local
``git archive`` subprocess (protocol.allow=never, no network, minimal env) into
a temporary directory. ``append_*`` write through the repository emitter's lock
and atomic-replace helpers at the target chain's own epoch (no clock sample;
observed_at is null and descriptive). They are run on temporary directories
only; the org-ledger append route is not admitted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

from llm_adapter import ed25519_verify
from llm_adapter import healthy_node_evaluator as hne
from llm_adapter import node_existence_readback as readback
from llm_adapter import node_health_check_projection as health_check
from llm_adapter import node_health_report_producer as producer
from llm_adapter import node_identity_binding_producer as binding
from llm_adapter import node_ingress_boundary as boundary
from llm_adapter import node_receipt_common as common
from llm_adapter.org_ledger_location import designated_org_ledger, org_ledger_location

ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / ".stegverse/node-ledger/pinned-code-digests.v1.json"
#: published public-key references of NODE_LEDGER_OPENED signers (TV/TVC custody; no key material)
OPENED_SIGNERS_PATH = ROOT / ".stegverse/node-ledger/node-ledger-opened-signers.v1.json"
EVALUATOR_SHA256 = "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58"

ALLOW, DENY, FAIL_CLOSED = hne.ALLOW, hne.DENY, hne.FAIL_CLOSED
REPOSITORY = hne.REPOSITORY
ORGANIZATION = "StegVerse-org"
ORG_LEDGER_LOCATION = "refs/stegverse/organization-ledger:repository-ledger/StegVerse-org/LLM-adapter"
GATEWAY_LOCATION_PREFIX = "node-ledger/" + ORGANIZATION

ORG, EPHEMERAL, PERMANENT, GATEWAY, KV, SKAP_VAULT = "ORG", "EPHEMERAL", "PERMANENT", "GATEWAY", "KV", "SKAP_VAULT"
ENDPOINT_KINDS = (EPHEMERAL, PERMANENT, GATEWAY, KV, SKAP_VAULT, ORG)
OWN_LEDGER_KINDS = (EPHEMERAL, PERMANENT, KV, SKAP_VAULT)
EPHEMERAL_NODE_KINDS = ("StegApp", "StegBrowser", "StegNode")
UNBOUNDED = "UNBOUNDED"
BOUNDED = "BOUNDED_UNTIL_DISSOLUTION"
#: Only an EPHEMERAL ledger is bounded, and only it dissolves.
LIFETIME_OF = {EPHEMERAL: BOUNDED, PERMANENT: UNBOUNDED, GATEWAY: UNBOUNDED, KV: UNBOUNDED, SKAP_VAULT: UNBOUNDED}

# Existing classes and schemas reused (StegVerse-org/.github data/intr-protocol/v1/protocol.json @907f4305,
# resident-runtime/intr_path_ingress.py sha256 056ba906...; #431 genesis class).
GENESIS_CLASS = "REPOSITORY_LEDGER_INITIALIZATION"
SOURCE_CLASS = "INTR_MESH_PATH_TRANSFER"
SOURCE_EVIDENCE_SCHEMA = "stegverse.intr-path-transfer-evidence/v1"
DESTINATION_CLASS = "INTR_MESH_PATH_INGRESS"
DESTINATION_OPERATION = "ORGANIZATION_INTR_DESTINATION_INGRESS"
DESTINATION_EVIDENCE_SCHEMA = "stegverse.intr-path-ingress-evidence/v1"
MESSAGE_CLASS = "ecosystem.communication"
CAPABILITY = "intr-destination"
# New, documented in the PR body: nothing existing closes a ledger location.
DISSOLVED_CLASS = "NODE_LEDGER_DISSOLVED"

GENESIS_SCHEMA = "stegverse.endpoint-ledger-genesis/v1"
ANCHOR_BODY_SCHEMA = "stegverse.endpoint-ledger-anchor/v1"
# Emitted by StegOS at EPHEMERAL node generation (stegos/ephemeral_node_ledger_open.py); mirrored here, not imported.
# Schema: schemas/node-ledger-opened-generation.v1.json.
OPENED_CLASS = "NODE_LEDGER_OPENED"
GENERATION_SCHEMA = "stegverse.node-ledger-opened-generation/v1"
OPENED_EMITTER = "stegos.ephemeral_node_ledger_open"
# The issued anchor KV consumes (continuity-vault-kit#258). Schema: schemas/node-ledger-opened.v1.json.
SIGNED_OPENED_SCHEMA = "stegverse.node-ledger-opened-signed/v1"   # schemas/node-ledger-opened-signed.v1.json
OPENED_SIGNATURE_DOMAIN = "stegverse.node-ledger-opened-signature/v1"
OPENED_SIGNERS_SCHEMA = "stegverse.published-public-key-references/v1"
OPENED_ANCHOR_SCHEMA = "stegverse.node-ledger-opened/v1"
OPENED_ANCHOR_FIELDS = ("schema", "transition_class", "node_id", "node_identity_key", "genesis_receipt_sha256",
                        "issuer", "issuer_receipt_ref", "receipt_sha256")
ISSUER_ORGANIZATION_LEDGER = "ORGANIZATION_LEDGER"
#: The schema's issuer enum. Only ORGANIZATION_LEDGER is issued or verified here: TV/TVC receipts are unsigned
#: (TVC#537, LC-KV-08), so a TV/TVC-issued anchor is refused until a verifier exists.
ANCHOR_ISSUERS = (ISSUER_ORGANIZATION_LEDGER, "TV/TVC")
ENDPOINT_KIND_SCHEMA = "stegverse.endpoint-kind/v1"   # schemas/endpoint-kind.v1.json
DISBURSEMENT_BODY_SCHEMA = "stegverse.node-ledger-disbursement/v1"
RESULT_SCHEMA = "stegverse.endpoint-ledger-anchor-result/v1"
RECEIPT_SCHEMA = "stegverse.repo-transition-receipt/v1"

FAILURE_CODE = "EPHEMERAL_NODE_LEDGER_NOT_ANCHORED"
TRANSPORT_FAILURE_CODE = "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED"   # Lane D's code (cvk#258)
IDENTITY_FAILURE_CODE = "NODE_IDENTITY_NOT_PROVEN"
IDENTITY_CHALLENGE_SCHEMA = "stegverse.node-identity-challenge/v1"
IDENTITY_PROOF_SCHEMA = "stegverse.node-identity-proof/v1"
RETRY_ENTRYPOINT = ("llm_adapter.endpoint_ledger_anchor.evaluate_anchored(endpoint=..., org_ledger_git_dir=..., "
                    "org_ledger_head_receipt_sha256=..., identity_proof=...) on the next anchor or org-ledger head event")
OWNING_GOAL = ("KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324) via LC-KV-13 (closes LC-KV-15's "
               "caller-supplied root), InTr and Mesh Destinations lane StegVerse-org/.github#162")
NEXT_ATTEMPT = ("re-evaluate when the endpoint's anchor (InTr path receipt pair, or the gateway location genesis) is "
                "observed on the pinned org-ledger head; event-driven, never on a timer")

#: reason -> (failed_predicate, required evidence or repair)
REASONS: dict[str, tuple[str, str]] = {
    "ENDPOINT_INVALID": ("ENDPOINT_KIND_DECLARED", "endpoint {endpoint_kind: EPHEMERAL|PERMANENT|KV|SKAP_VAULT|GATEWAY; "
                         "ledger_root for an own-ledger kind; none for GATEWAY}"),
    "ENDPOINT_KIND_NOT_A_NODE_ROOT": ("ENDPOINT_KIND_DECLARED", "an ORG (.github) ledger is not a node health root; bind a "
                                      "node's own ledger or its gateway location"),
    "PINNED_CODE_DIGEST_MISMATCH": ("PINNED_CODE_DIGESTS_MATCH", "the evaluator and producer files must hash to "
                                    ".stegverse/node-ledger/pinned-code-digests.v1.json (evaluator fdaa2005...1f58)"),
    "ORG_LEDGER_HEAD_NOT_PINNED": ("ORG_LEDGER_HEAD_PINNED", "org_ledger_head_receipt_sha256 read back from "
                                   + ORG_LEDGER_LOCATION + ", equal to the supplied copy's HEAD.json"),
    "ORG_LEDGER_LOCATION_NOT_DESIGNATED": ("ORG_LEDGER_LOCATION_FROM_CONTRACT", "the repository_ledger_location "
                                           "(repository, ref, namespace) in .stegverse/transition-ledger/contract.json, "
                                           "as StegVerse-org/LLM-adapter#431 designates; a caller-chosen path is never "
                                           "the org ledger"),
    "ORG_LEDGER_LOCATION_UNREADABLE": ("ORG_LEDGER_LOCATION_FROM_CONTRACT", "the designated ref and namespace read back "
                                       "from a local StegVerse-org/.github object store (git archive <ref> <namespace>; "
                                       "no network), with a REPOSITORY_LEDGER_INITIALIZATION genesis for this repository"),
    "ORG_LEDGER_UNREADABLE": ("ORG_LEDGER_READ_BACK", "a sealed, intact org-ledger chain at " + ORG_LEDGER_LOCATION),
    "ENDPOINT_LEDGER_UNREADABLE": ("ENDPOINT_LEDGER_READ_BACK", "a sealed, intact endpoint chain from HEAD.json to genesis"),
    "ENDPOINT_GENESIS_INVALID": ("ENDPOINT_GENESIS_DECLARES_THE_NODE", "a REPOSITORY_LEDGER_INITIALIZATION genesis "
                                 "(stegverse.endpoint-ledger-genesis/v1) naming this node_id, endpoint_kind, a "
                                 "well-formed node_identity_key, the pinned code digests and, for EPHEMERAL, a StegApp/StegBrowser/StegNode node_kind"),
    "UNANCHORED": ("ENDPOINT_LEDGER_ANCHORED_ON_ORG_LEDGER", "an InTr path receipt pair: INTR_MESH_PATH_TRANSFER on the "
                   "endpoint ledger and INTR_MESH_PATH_INGRESS (ORGANIZATION_INTR_DESTINATION_INGRESS) on the org "
                   "ledger, linked by seal, with the source half retained; for EPHEMERAL its body is the StegOS NODE_LEDGER_OPENED "
                   "record emitted at generation"),
    "NODE_LEDGER_OPENED_UNSIGNED": ("NODE_LEDGER_OPENED_SIGNED_BY_PUBLISHED_KEY", "the InTr pair must carry a "
                                    "stegverse.node-ledger-opened-signed/v1 envelope: StegOS's record plus an Ed25519 "
                                    "signature over it by a key in .stegverse/node-ledger/node-ledger-opened-signers.v1.json"),
    "NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED": ("NODE_LEDGER_OPENED_SIGNED_BY_PUBLISHED_KEY", "the signature's key_id "
                                                "must be a published public-key reference in "
                                                ".stegverse/node-ledger/node-ledger-opened-signers.v1.json (TV/TVC "
                                                "custody publishes it; none is published yet)"),
    "NODE_LEDGER_OPENED_SIGNATURE_INVALID": ("NODE_LEDGER_OPENED_SIGNED_BY_PUBLISHED_KEY", "the Ed25519 signature "
                                             "(llm_adapter.ed25519_verify) must verify over the record under the "
                                             "published public key it names"),
    "GENESIS_MISMATCH": ("ANCHOR_BINDS_ENDPOINT_GENESIS", "the anchor must name this endpoint ledger's genesis hash"),
    "KEY_MISMATCH": ("ANCHOR_BINDS_NODE_IDENTITY_KEY", "the anchor, the genesis and the node's existence and binding "
                     "receipts must carry the same node_identity_key"),
    "ANCHOR_LINK_UNVERIFIED": ("ANCHOR_HALVES_LINKED_BY_SEAL", "the org-ledger ingress receipt must link the source "
                               "half on the endpoint ledger by seal and carry its payload digest"),
    "FOREIGN_PRODUCER_RECEIPT": ("RECEIPTS_FROM_PINNED_PRODUCERS_ONLY", "every receipt on the endpoint chain must be "
                                 "one the pinned evaluator/producer code writes; remove nothing, open a new anchored "
                                 "ledger instead"),
    "EXTERNAL_CHAIN_IMPORTED": ("GATEWAY_LEDGER_NEVER_IMPORTS", "a gateway node's org-carried chain carries no InTr "
                                "transfer of an external ledger"),
    "EPHEMERAL_NODE_LEDGER_DISSOLVED": ("ENDPOINT_LEDGER_NOT_DISSOLVED", "a dissolved ledger is not admissible; anchor a "
                                        "new endpoint ledger"),
    "NODE_LEDGER_OPENED_ANCHOR_NOT_ISSUED": ("NODE_LEDGER_OPENED_ANCHOR_ISSUED_BY_ORGANIZATION_LEDGER",
                                             "a stegverse.node-ledger-opened/v1 anchor with exactly its eight fields, "
                                             "issuer ORGANIZATION_LEDGER and issuer_receipt_ref the org ledger's "
                                             "INTR_MESH_PATH_INGRESS that carried StegOS's generation record, re-derived "
                                             "at the pinned org-ledger head"),
}
TRANSPORT_PREDICATE = "INSTALLED_INTR_TRANSPORT_OBSERVED_ON_RECEIPTS"
TRANSPORT_REASONS: dict[str, tuple[str, str]] = {
    TRANSPORT_FAILURE_CODE: (TRANSPORT_PREDICATE, "the node's current NODE_INGRESS_ADMITTED record on the anchored chain "
                             "must say transport INTERLOCK_INTR, transport_state INSTALLED (llm_adapter.node_ingress_"
                             "boundary); a caller-asserted transport_state is never accepted"),
}
TRANSPORT_RETRY = ("llm_adapter.endpoint_ledger_anchor.evaluate_anchored(...) after the node arrives over the installed "
                   "InTr transport and the boundary records it (node_ingress_boundary INTERLOCK_INTR is NOT_YET_ENABLED "
                   "on main)")
TRANSPORT_NEXT = "on the next NODE_INGRESS_ADMITTED receipt carried by an installed InTr transport; never on a timer"
IDENTITY_PREDICATE = "NODE_IDENTITY_PROVEN_BY_NODE_IDENTITY_KEY_SIGNATURE"
IDENTITY_REASONS: dict[str, tuple[str, str]] = {
    "NODE_IDENTITY_PROOF_ABSENT": (IDENTITY_PREDICATE, "a stegverse.node-identity-proof/v1 signature by the anchored "
                                   "node_identity_key over identity_challenge(...); an asserted identity is not proof"),
    "NODE_IDENTITY_PROOF_INVALID": (IDENTITY_PREDICATE, "the proof must name the anchored key_id and the current "
                                    "challenge digest, and its Ed25519 signature must verify under the anchored "
                                    "public key"),
}
IDENTITY_RETRY = ("llm_adapter.endpoint_ledger_anchor.evaluate_anchored(..., identity_proof=...) with a proof over the "
                  "challenge for the current endpoint and org-ledger heads")
IDENTITY_NEXT = "when the node signs the current challenge with its TV/TVC-held key; event-driven, never on a timer"

PINNED_FILES_PRODUCING = {
    readback.TRANSITION_CLASS: "llm_adapter/node_existence_readback.py",
    binding.TRANSITION_CLASS: "llm_adapter/node_identity_binding_producer.py",
    health_check.TRANSITION_CLASS: "llm_adapter/node_health_check_projection.py",
    producer.REPORT_CLASS: "llm_adapter/node_health_report_producer.py",
    boundary.ADMITTED_CLASS: "llm_adapter/node_ingress_boundary.py",
    boundary.REFUSED_CLASS: "llm_adapter/node_ingress_boundary.py",
}


# -- shared ------------------------------------------------------------------------------------------

def sha(value: Any) -> str:
    return hne.sha(value)


def _ev(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    return common.evidence(receipt)


def non_allow(reason: str, detail: str, *, node_id: Any = None, schema: str = RESULT_SCHEMA,
              failure_code: str = FAILURE_CODE, reasons: Mapping[str, tuple[str, str]] = REASONS,
              retry_entrypoint: str = RETRY_ENTRYPOINT, owning_existing_goal: str = OWNING_GOAL,
              next_attempt: str = NEXT_ATTEMPT, **extra: Any) -> dict[str, Any]:
    predicate, repair = reasons[reason]
    return {"schema": schema, "disposition": FAIL_CLOSED, "node_id": node_id if isinstance(node_id, str) else None,
            "healthy_node_established": False, "reason": reason, "detail": detail,
            "failure_code": failure_code, "failed_predicate": predicate, "required_evidence_or_repair": repair,
            "retry_entrypoint": retry_entrypoint, "owning_existing_goal": owning_existing_goal,
            "next_attempt": next_attempt, "authority_effect": "NONE_EVALUATION_ONLY", **extra}


def load_pins() -> dict[str, Any]:
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))


def pinned_digests_sha256() -> str:
    return sha(load_pins()["digests"])


def pinned_code_failure() -> str | None:
    """None when every pinned file hashes to its pin and the evaluator is the fdaa2005 bytes."""
    pins = load_pins()["digests"]
    if pins.get("llm_adapter/healthy_node_evaluator.py") != EVALUATOR_SHA256:
        return "the pin set does not name the evaluator fdaa2005...1f58"
    for path, want in sorted(pins.items()):
        try:
            got = "sha256:" + hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        except OSError as exc:
            return f"{path} unreadable: {type(exc).__name__}"
        if got != want:
            return f"{path} is {got}, pinned {want}"
    return None


def payload_ok(evidence: Mapping[str, Any]) -> bool:
    """intr_path_ingress._payload_ok's rule, with boundary_evidence also outside the digest."""
    core = {k: v for k, v in evidence.items()
            if k not in ("payload_sha256", "disposition", "communication_id", "boundary_evidence")}
    return evidence.get("payload_sha256") == sha(core)


def path_id(node_id: str) -> str:
    return f"{node_id}->{ORGANIZATION}:{CAPABILITY}"


def message(communication_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
    return {"message_class": MESSAGE_CLASS, "communication_id": communication_id, "body": dict(body)}


def gateway_location(node_id: str) -> str:
    return f"{GATEWAY_LOCATION_PREFIX}/{node_id}"


def gateway_root(org_ledger_root: Any, node_id: str) -> Path:
    return Path(org_ledger_root) / gateway_location(node_id)


def epoch_of(chain: list[dict[str, Any]]) -> int:
    epoch = common.chain_epoch(chain)
    if epoch is None:
        raise ValueError("chain head has no integer heartbeat epoch")
    return epoch


def _emitter():
    spec = importlib.util.spec_from_file_location("repo_transition_emit_for_endpoint_ledgers",
                                                  ROOT / ".stegverse/transition-ledger/emit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_receipt(ledger_root: Any, transition_class: str, transition_id: str, predecessor: str, evidence: Mapping[str, Any],
                   hb_epoch: int) -> dict[str, Any]:
    """Append one stegverse.repo-transition-receipt/v1 to ledger_root (HEAD.json + receipts/<hex>.json).

    Same body, lock and atomic publication as .stegverse/transition-ledger/emit.py, at a supplied epoch, with no
    clock sample: observed_at is null (descriptive only). Temporary directories only in this draft."""
    emit = _emitter()
    root = Path(ledger_root)
    with emit._exclusive(root):
        head_path = root / "HEAD.json"
        prev = json.loads(head_path.read_text()).get("receipt_sha256") if head_path.is_file() else None
        body = {"schema": RECEIPT_SCHEMA, "repository": REPOSITORY, "transition_id": transition_id,
                "transition_class": transition_class, "predecessor_state_sha256": predecessor,
                "successor_state_sha256": sha(dict(evidence)), "evidence": dict(evidence), "authority_effect": "NONE",
                "hb_reference": emit.hb_reference(hb_epoch), "ordering": emit.ORDERING, "observed_at": None,
                "observed_at_is_descriptive_not_ordering": True, "previous_receipt_sha256": prev}
        digest = sha(body)
        receipt = {**body, "receipt_sha256": digest}
        path = root / "receipts" / (digest[7:] + ".json")
        if path.is_file() and json.loads(path.read_text()) != receipt:
            raise SystemExit("receipt collision")
        if not path.is_file():
            emit._put(path, receipt)
        emit._put(head_path, {"repository": REPOSITORY, "receipt_sha256": digest, "receipt_path": str(path)})
        return receipt


def retain(org_ledger_root: Any, receipt: Mapping[str, Any]) -> Path:
    """The protocol's dual-ledger retained copy: source-receipts/<hex>.json on the org ledger."""
    emit = _emitter()
    path = Path(org_ledger_root) / "source-receipts" / (receipt["receipt_sha256"][7:] + ".json")
    if path.is_file() and json.loads(path.read_text()) != dict(receipt):
        raise SystemExit("retained copy collision")
    if not path.is_file():
        emit._put(path, dict(receipt))
    return path


def read_retained(org_ledger_root: Any, digest: Any) -> dict[str, Any] | None:
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        return None
    try:
        copy = json.loads((Path(org_ledger_root) / "source-receipts" / (digest[7:] + ".json")).read_text())
    except Exception:
        return None
    body = {k: v for k, v in copy.items() if k != "receipt_sha256"} if isinstance(copy, dict) else None
    return copy if body is not None and copy.get("receipt_sha256") == digest and sha(body) == digest else None


# -- open (genesis) ----------------------------------------------------------------------------------

def plan_open(node_id: Any, endpoint_kind: Any, node_identity_key: Any, node_kind: Any = None) -> dict[str, Any]:
    """The genesis an endpoint ledger (or a gateway location) opens with. Pure."""
    if endpoint_kind not in LIFETIME_OF or (endpoint_kind == EPHEMERAL) != (node_kind is not None) \
            or (node_kind is not None and node_kind not in EPHEMERAL_NODE_KINDS):
        return non_allow("ENDPOINT_INVALID", f"endpoint_kind {endpoint_kind!r}, node_kind {node_kind!r}",
                         node_id=node_id)
    ledger_lifetime = LIFETIME_OF[endpoint_kind]
    key_failure = common.node_identity_key_failure(node_identity_key)
    if not isinstance(node_id, str) or key_failure or node_identity_key.get("node_id") != node_id:
        return non_allow("ENDPOINT_GENESIS_INVALID", f"node_identity_key: {key_failure or 'node_id differs'}",
                         node_id=node_id)
    evidence = {"schema": GENESIS_SCHEMA, "node_id": node_id, "endpoint_kind": endpoint_kind,
                "ledger_lifetime": ledger_lifetime, "node_identity_key": dict(node_identity_key),
                "ledger_location": (ORG_LEDGER_LOCATION.split(":")[0] + ":" + gateway_location(node_id)
                                    if endpoint_kind == GATEWAY else "ENDPOINT_OWN_LEDGER"),
                "corresponds_to": ORG_LEDGER_LOCATION, "pinned_code_digests_sha256": pinned_digests_sha256(),
                "pinned_code_digests_ref": ".stegverse/node-ledger/pinned-code-digests.v1.json",
                "credential_held_or_minted": False, "authority_effect": "NONE"}
    if endpoint_kind == EPHEMERAL:
        evidence["node_kind"] = node_kind
        evidence["dissolution"] = {"on_event": "NODE_DISSOLUTION", "disbursed_to": ORG_LEDGER_LOCATION}
    return {"schema": RESULT_SCHEMA, "disposition": ALLOW, "node_id": node_id, "transition_class": GENESIS_CLASS,
            "transition_id": f"{GENESIS_CLASS}:{endpoint_kind}:{node_id}", "receipt_evidence": evidence,
            "predecessor_state_sha256": sha({"node_id": node_id, "endpoint_ledger": None}),
            "hb_epoch": common.chain_epoch([])}


def open_ledger(ledger_root: Any, node_id: str, endpoint_kind: str, node_identity_key: Mapping[str, Any],
                node_kind: str | None = None) -> dict[str, Any]:
    planned = plan_open(node_id, endpoint_kind, node_identity_key, node_kind)
    if planned["disposition"] != ALLOW:
        return planned
    root = Path(ledger_root)
    if (root / "HEAD.json").exists():
        return non_allow("ENDPOINT_GENESIS_INVALID", "the ledger is not empty; a genesis opens an empty ledger",
                         node_id=node_id)
    receipt = append_receipt(root, GENESIS_CLASS, planned["transition_id"], planned["predecessor_state_sha256"],
                             planned["receipt_evidence"], planned["hb_epoch"])
    return {**planned, "outcome": "EMITTED", "receipt_sha256": receipt["receipt_sha256"], "genesis": receipt}


def open_gateway_location(org_ledger_root: Any, node_id: str, node_identity_key: Mapping[str, Any]) -> dict[str, Any]:
    """Open node-ledger/StegVerse-org/<node_id> inside the org ledger: the gateway node's anchor."""
    return open_ledger(gateway_root(org_ledger_root, node_id), node_id, GATEWAY, node_identity_key)


# -- the InTr path pair (source half on the endpoint, destination half on the org ledger) ------------

def source_evidence(node_id: str, endpoint_kind: str, communication_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
    msg = message(communication_id, body)
    core = {"schema": SOURCE_EVIDENCE_SCHEMA, "repository": REPOSITORY, "path_id": path_id(node_id),
            "destination_organization": ORGANIZATION, "destination_location": ORG_LEDGER_LOCATION,
            "endpoint_kind": endpoint_kind, "message": msg, "message_sha256": sha(msg)}
    return {**core, "payload_sha256": sha(core), "disposition": ALLOW, "communication_id": communication_id,
            "boundary_evidence": {"operation": SOURCE_CLASS, "path_id": path_id(node_id),
                                  "communication_id": communication_id}}


def destination_evidence(source: Mapping[str, Any]) -> dict[str, Any]:
    ev = _ev(source)
    core = {"schema": DESTINATION_EVIDENCE_SCHEMA, "repository": REPOSITORY, "path_id": ev.get("path_id"),
            "source_repository": source.get("repository"),
            "source_repository_receipt_sha256": source.get("receipt_sha256"),
            "message": ev.get("message"), "message_sha256": ev.get("message_sha256"),
            "addressed_location": ORG_LEDGER_LOCATION, "endpoint_kind": ev.get("endpoint_kind"),
            "source_inclusion": "READ_BACK_FROM_THE_ENDPOINT_LEDGER_AND_RETAINED"}
    return {**core, "payload_sha256": sha(core), "disposition": ALLOW, "communication_id": ev.get("communication_id"),
            "boundary_evidence": {"operation": DESTINATION_OPERATION, "path_id": ev.get("path_id"),
                                  "communication_id": ev.get("communication_id"),
                                  "source_repository_receipt_sha256": source.get("receipt_sha256")}}


def append_source(ledger_root: Any, node_id: str, communication_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
    chain, failure, detail = hne.read_chain(ledger_root)
    if failure:
        raise ValueError(f"{failure}: {detail}")
    kind = _ev(chain[-1]).get("endpoint_kind")
    return append_receipt(ledger_root, SOURCE_CLASS, f"{SOURCE_CLASS}:{path_id(node_id)}@{communication_id}",
                          chain[0]["receipt_sha256"], source_evidence(node_id, kind, communication_id, body),
                          epoch_of(chain))


def append_destination(org_ledger_root: Any, source: Mapping[str, Any]) -> dict[str, Any]:
    """The org-side half. In production this is the organization's own append (route not admitted)."""
    chain, failure, detail = hne.read_chain(org_ledger_root)
    if failure:
        raise ValueError(f"{failure}: {detail}")
    retain(org_ledger_root, source)
    ev = _ev(source)
    return append_receipt(org_ledger_root, DESTINATION_CLASS,
                          f"{DESTINATION_OPERATION}:{ev.get('path_id')}@{ev.get('communication_id')}",
                          chain[0]["receipt_sha256"], destination_evidence(source), epoch_of(chain))


def anchor_body(genesis: Mapping[str, Any]) -> dict[str, Any]:  # PERMANENT, KV, SKAP_VAULT
    g = _ev(genesis)
    return {"schema": ANCHOR_BODY_SCHEMA, "node_id": g.get("node_id"), "endpoint_kind": g.get("endpoint_kind"),
            "ledger_lifetime": g.get("ledger_lifetime"), "node_identity_key": g.get("node_identity_key"),
            "genesis_receipt_sha256": genesis.get("receipt_sha256"),
            "pinned_code_digests_sha256": g.get("pinned_code_digests_sha256")}


def opened_record_sha256(record: Mapping[str, Any]) -> str:
    """The seal of StegOS's generation record or of an issued anchor (receipt_sha256 excluded)."""
    return sha({k: v for k, v in record.items() if k != "receipt_sha256"})


def opened_record_failure(record: Any, genesis: Mapping[str, Any]) -> tuple[str, str] | None:
    """(reason, detail) when `record` is not StegOS's NODE_LEDGER_OPENED for this genesis, or None. Pure."""
    g = _ev(genesis)
    if not isinstance(record, Mapping) or record.get("schema") != GENERATION_SCHEMA \
            or record.get("transition_class") != OPENED_CLASS \
            or record.get("disposition") != ALLOW or record.get("emitted_by") != OPENED_EMITTER \
            or "issuer" in record or "issuer_receipt_ref" in record \
            or record.get("receipt_sha256") != opened_record_sha256(record):
        return "ANCHOR_LINK_UNVERIFIED", "the anchor body is not a sealed StegOS NODE_LEDGER_OPENED record"
    if record.get("genesis_receipt_sha256") != genesis.get("receipt_sha256"):
        return "GENESIS_MISMATCH", f"NODE_LEDGER_OPENED names genesis {record.get('genesis_receipt_sha256')}"
    if record.get("node_identity_key") != g.get("node_identity_key"):
        return "KEY_MISMATCH", "NODE_LEDGER_OPENED binds another node_identity_key than the genesis"
    if (record.get("node_id"), record.get("endpoint_kind"), record.get("node_kind"), record.get("ledger_lifetime")) != \
            (g.get("node_id"), EPHEMERAL, g.get("node_kind"), BOUNDED):
        return "ENDPOINT_GENESIS_INVALID", "NODE_LEDGER_OPENED names another node, kind or lifetime than the genesis"
    return None


def load_opened_signers() -> list[dict[str, Any]]:
    """The published NODE_LEDGER_OPENED signer public-key references (empty until TV/TVC publishes one)."""
    try:
        published = json.loads(OPENED_SIGNERS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(published, Mapping) or published.get("schema") != OPENED_SIGNERS_SCHEMA:
        return []
    return [dict(k) for k in published.get("signers") or [] if isinstance(k, Mapping)]


def opened_signing_message(record: Mapping[str, Any]) -> bytes:
    """The bytes a NODE_LEDGER_OPENED signer signs: the domain line, then StegOS's sealed record. Pure."""
    return common.signed_message(OPENED_SIGNATURE_DOMAIN, dict(record))


def signed_opened(record: Mapping[str, Any], signature: Mapping[str, Any]) -> dict[str, Any]:
    """The InTr body for an EPHEMERAL anchor: StegOS's record plus a published signer's detached signature.

    The signature is produced by the TV/TVC custody signer; this module never holds or touches key material.
    """
    return {"schema": SIGNED_OPENED_SCHEMA, "genesis_receipt_sha256": record.get("genesis_receipt_sha256"),
            "node_ledger_opened": dict(record), "signature": dict(signature)}


def opened_signature_failure(body: Mapping[str, Any]) -> tuple[str, str] | None:
    """(reason, detail) unless `body` is StegOS's record signed by a published key, else None. Pure."""
    if body.get("schema") != SIGNED_OPENED_SCHEMA or not isinstance(body.get("signature"), Mapping) \
            or not isinstance(body.get("node_ledger_opened"), Mapping):
        return "NODE_LEDGER_OPENED_UNSIGNED", "the anchor body carries no signed NODE_LEDGER_OPENED envelope"
    signature, record = body["signature"], body["node_ledger_opened"]
    if sorted(body) != ["genesis_receipt_sha256", "node_ledger_opened", "schema", "signature"] \
            or body.get("genesis_receipt_sha256") != record.get("genesis_receipt_sha256"):
        return "ANCHOR_LINK_UNVERIFIED", "the signed envelope does not name its record's genesis"
    signer = next((k for k in load_opened_signers() if k.get("key_id") == signature.get("key_id")
                   and k.get("algorithm") == "Ed25519" and signature.get("algorithm") == "Ed25519"), None)
    if signer is None:
        return "NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED", f"key_id {signature.get('key_id')!r} is not a published signer"
    public, raw = common.b64(signer.get("public_key_b64")), common.b64(signature.get("signature_b64"))
    if public is None or len(public) != 32 or raw is None or len(raw) != 64 \
            or not ed25519_verify.verify(public, opened_signing_message(record), raw):
        return "NODE_LEDGER_OPENED_SIGNATURE_INVALID", f"the signature does not verify under {signer.get('key_id')}"
    return None


def anchor_communication_id(node_id: str, genesis_sha: str) -> str:
    return f"endpoint-ledger-anchor:{node_id}@{genesis_sha[7:23]}"


def anchor(ledger_root: Any, org_ledger_root: Any, node_id: str, node_ledger_opened: Any = None) -> dict[str, Any]:
    """Run both halves of the anchor path for an own-ledger endpoint (temporary directories only).

    EPHEMERAL: the body is the NODE_LEDGER_OPENED record StegOS emitted when it generated the node, inside
    the signed envelope ``signed_opened`` builds from the custody signer's signature.
    """
    chain, failure, detail = hne.read_chain(ledger_root)
    if failure:
        raise ValueError(f"{failure}: {detail}")
    genesis = chain[-1]
    if _ev(genesis).get("endpoint_kind") == EPHEMERAL:
        if node_ledger_opened is None:
            raise ValueError("an EPHEMERAL ledger is anchored by StegOS's signed NODE_LEDGER_OPENED record")
        body = dict(node_ledger_opened)
    else:
        body = anchor_body(genesis)
    source = append_source(ledger_root, node_id, anchor_communication_id(node_id, genesis["receipt_sha256"]), body)
    destination = append_destination(org_ledger_root, source)
    return {"source_receipt_sha256": source["receipt_sha256"], "destination_receipt_sha256": destination["receipt_sha256"]}


# -- verification ------------------------------------------------------------------------------------

def _org_chain(org_ledger_root: Any, head: Any):
    if not isinstance(head, str) or not head.startswith("sha256:"):
        return None, ("ORG_LEDGER_HEAD_NOT_PINNED", "no org-ledger head pin supplied")
    try:
        actual = json.loads((Path(org_ledger_root) / "HEAD.json").read_text())["receipt_sha256"]
    except Exception as exc:
        return None, ("ORG_LEDGER_UNREADABLE", f"org HEAD.json unreadable: {type(exc).__name__}")
    if actual != head:
        return None, ("ORG_LEDGER_HEAD_NOT_PINNED", f"org HEAD is {actual}, pinned {head}")
    chain, failure, detail = hne.read_chain(org_ledger_root)
    if failure:
        return None, ("ORG_LEDGER_UNREADABLE", f"{failure}: {detail}")
    if chain[-1].get("previous_receipt_sha256") is not None:
        return None, ("ORG_LEDGER_UNREADABLE", "org chain does not end at a genesis")
    return chain, None


def dissolution_on(chain: list[dict[str, Any]], genesis_sha: str) -> dict[str, Any] | None:
    return next((r for r in chain if r.get("transition_class") == DISSOLVED_CLASS
                 and _ev(r).get("genesis_receipt_sha256") == genesis_sha), None)


def _key_of_receipt(receipt: Mapping[str, Any]) -> Any:
    ev = _ev(receipt)
    if receipt.get("transition_class") == readback.TRANSITION_CLASS:
        return (ev.get("observation") or {}).get("node_identity_key")
    if receipt.get("transition_class") == binding.TRANSITION_CLASS:
        return {"key_id": (ev.get("key_ref") or {}).get("key_id"), "public_key_b64": ev.get("public_key_b64")}
    return None


def _key_matches(key: Mapping[str, Any], seen: Any) -> bool:
    return isinstance(seen, Mapping) and all(seen.get(k) == key.get(k) for k in seen)


def provenance_failure(chain: list[dict[str, Any]], node_id: str, kind: str) -> tuple[str, str] | None:
    """(reason, detail) for the first receipt the pinned code does not write, or None. Oldest first."""
    ordered = list(reversed(chain))
    position = {r["receipt_sha256"]: i for i, r in enumerate(ordered)}
    last_report = None
    for i, r in enumerate(ordered[1:], start=1):
        cls, ev, addr = r.get("transition_class"), _ev(r), r["receipt_sha256"]
        if r.get("successor_state_sha256") != sha(dict(ev)):
            return "FOREIGN_PRODUCER_RECEIPT", f"{addr} successor_state_sha256 is not the digest of its evidence"
        if cls == SOURCE_CLASS:
            if kind == GATEWAY:
                return "EXTERNAL_CHAIN_IMPORTED", f"{addr} is an InTr transfer on a gateway node's org-carried chain"
            body = (ev.get("message") or {}).get("body") or {}
            if (ev.get("schema") != SOURCE_EVIDENCE_SCHEMA or not payload_ok(ev) or ev.get("path_id") != path_id(node_id)
                    or body.get("schema") not in ((SIGNED_OPENED_SCHEMA, GENERATION_SCHEMA, DISBURSEMENT_BODY_SCHEMA) if kind == EPHEMERAL
                                                  else (ANCHOR_BODY_SCHEMA,))):
                return "FOREIGN_PRODUCER_RECEIPT", f"{addr} is not an anchor or disbursement path receipt for {node_id}"
            continue
        if cls not in PINNED_FILES_PRODUCING:
            return "FOREIGN_PRODUCER_RECEIPT", f"{addr} class {cls!r} is written by no pinned producer"
        if cls in (boundary.ADMITTED_CLASS, boundary.REFUSED_CLASS):
            node = ((ev.get("node_endpoint") or {}).get("node_id") if cls == boundary.ADMITTED_CLASS
                    else ev.get("evaluated_node_id"))
            if ev.get("schema") != boundary.RECORD_SCHEMA or node not in (node_id, None) \
                    or (cls == boundary.ADMITTED_CLASS and node != node_id):
                return "FOREIGN_PRODUCER_RECEIPT", f"{addr} is not an ingress record for {node_id}"
            continue
        if ev.get("node_id") != node_id or not str(r.get("transition_id", "")).startswith(f"{cls}:{node_id}:"):
            return "FOREIGN_PRODUCER_RECEIPT", f"{addr} names another node or a foreign transition_id"
        schema = {readback.TRANSITION_CLASS: readback.EVIDENCE_SCHEMA, binding.TRANSITION_CLASS: binding.EVIDENCE_SCHEMA,
                  health_check.TRANSITION_CLASS: health_check.EVIDENCE_SCHEMA,
                  producer.REPORT_CLASS: producer.REPORT_SCHEMA}[cls]
        if ev.get("schema") != schema:
            return "FOREIGN_PRODUCER_RECEIPT", f"{addr} evidence schema {ev.get('schema')!r} is not {schema}"
        if cls == producer.REPORT_CLASS:
            manifest = {"schema": producer.TRANSITION_MANIFEST_SCHEMA, "intended_action": producer.INTENDED_ACTION,
                        "transition_class": producer.REPORT_CLASS, "inputs_are_receipts_on_chain": True,
                        "producer": producer.PRODUCER, "producer_version": producer.PRODUCER_VERSION}
            cited = ev.get("evidence_receipts") or {}
            wanted = (("authenticated_reciprocal_node_existence", readback.TRANSITION_CLASS),
                      ("node_identity_binding", binding.TRANSITION_CLASS), ("health_check", health_check.TRANSITION_CLASS))
            ok = ev.get("transition_manifest") == manifest and ev.get("previous_health_report_receipt_sha256") == last_report
            ok = ok and (ev.get("trigger") or {}).get("receipt_sha256") in position \
                and position[(ev.get("trigger") or {}).get("receipt_sha256")] < i
            for field, want_cls in wanted:
                j = position.get(cited.get(field))
                ok = ok and j is not None and j < i and ordered[j].get("transition_class") == want_cls
            if ok:
                check = ordered[position[cited["health_check"]]]
                observed = _ev(check).get("status")
                ok = ev.get("observed_health_check_status") == observed and \
                    ev.get("status") == (hne.HEALTHY if observed == hne.HEALTHY else producer.UNHEALTHY)
            if not ok:
                return "FOREIGN_PRODUCER_RECEIPT", f"{addr} does not re-derive as the pinned producer's report"
            last_report = addr
    return None


def verify_anchor(node_id: Any, *, endpoint: Any, org_ledger_root: Any,
                  org_ledger_head_receipt_sha256: Any, check_provenance: bool = True) -> dict[str, Any]:
    """ALLOW with the anchored `ledger_root`, or six-field FAIL_CLOSED EPHEMERAL_NODE_LEDGER_NOT_ANCHORED. Pure."""
    kind = endpoint.get("endpoint_kind") if isinstance(endpoint, Mapping) else None
    if kind == ORG:
        return non_allow("ENDPOINT_KIND_NOT_A_NODE_ROOT", "endpoint_kind ORG", node_id=node_id)
    if not isinstance(node_id, str) or not node_id or kind not in ENDPOINT_KINDS \
            or (kind == GATEWAY and endpoint.get("ledger_root") is not None) \
            or (kind != GATEWAY and endpoint.get("ledger_root") is None):
        return non_allow("ENDPOINT_INVALID", f"endpoint {endpoint!r}", node_id=node_id)
    code = pinned_code_failure()
    if code:
        return non_allow("PINNED_CODE_DIGEST_MISMATCH", code, node_id=node_id)
    org_chain, failed = _org_chain(org_ledger_root, org_ledger_head_receipt_sha256)
    if failed:
        return non_allow(*failed, node_id=node_id)
    root = gateway_root(org_ledger_root, node_id) if kind == GATEWAY else Path(endpoint["ledger_root"])
    chain, failure, detail = hne.read_chain(root)
    if failure:
        return non_allow("ENDPOINT_LEDGER_UNREADABLE", f"{failure}: {detail}", node_id=node_id)
    genesis = chain[-1]
    g = _ev(genesis)
    if (genesis.get("transition_class") != GENESIS_CLASS or genesis.get("previous_receipt_sha256") is not None
            or g.get("schema") != GENESIS_SCHEMA or g.get("node_id") != node_id or g.get("endpoint_kind") != kind
            or common.node_identity_key_failure(g.get("node_identity_key"))
            or g.get("pinned_code_digests_sha256") != pinned_digests_sha256()
            or g.get("ledger_lifetime") != LIFETIME_OF[kind]
            or (kind == EPHEMERAL) != (g.get("node_kind") in EPHEMERAL_NODE_KINDS)):
        return non_allow("ENDPOINT_GENESIS_INVALID", f"genesis {genesis.get('receipt_sha256')} does not declare "
                         f"{node_id} as {kind} with the pinned digests", node_id=node_id)
    key, genesis_sha = g["node_identity_key"], genesis["receipt_sha256"]
    anchor_info: dict[str, Any] = {"endpoint_kind": kind, "ledger_lifetime": g.get("ledger_lifetime"),
                                   "genesis_receipt_sha256": genesis_sha, "ledger_root": str(root)}
    if kind == EPHEMERAL:
        anchor_info["node_kind"] = g.get("node_kind")
    if kind == GATEWAY:
        anchor_info.update(anchor="ORG_LEDGER_LOCATION_GENESIS", location=gateway_location(node_id))
    else:
        if dissolution_on(org_chain, genesis_sha) is not None:
            return non_allow("EPHEMERAL_NODE_LEDGER_DISSOLVED", f"genesis {genesis_sha} was dissolved on the org ledger",
                             node_id=node_id, **anchor_info)
        want_body = (SIGNED_OPENED_SCHEMA, GENERATION_SCHEMA) if kind == EPHEMERAL else (ANCHOR_BODY_SCHEMA,)
        ingresses = [r for r in org_chain if r.get("transition_class") == DESTINATION_CLASS
                     and _ev(r).get("path_id") == path_id(node_id)
                     and ((_ev(r).get("message") or {}).get("body") or {}).get("schema") in want_body]
        if not ingresses:
            return non_allow("UNANCHORED", f"no anchor ingress for {path_id(node_id)} on the org ledger",
                             node_id=node_id, **anchor_info)
        bodies = [((_ev(r).get("message") or {}).get("body") or {}) for r in ingresses]
        match = [(r, b) for r, b in zip(ingresses, bodies) if b.get("genesis_receipt_sha256") == genesis_sha]
        if not match:
            return non_allow("GENESIS_MISMATCH", f"anchors name {[b.get('genesis_receipt_sha256') for b in bodies]}, "
                             f"the ledger's genesis is {genesis_sha}", node_id=node_id, **anchor_info)
        ingress, body = match[0]
        ev = _ev(ingress)
        source_sha = ev.get("source_repository_receipt_sha256")
        source = next((r for r in chain if r["receipt_sha256"] == source_sha), None)
        retained = read_retained(org_ledger_root, source_sha)
        if (source is None or retained != source or not payload_ok(ev) or ev.get("schema") != DESTINATION_EVIDENCE_SCHEMA
                or (ev.get("boundary_evidence") or {}).get("operation") != DESTINATION_OPERATION
                or ev != destination_evidence(source) or not payload_ok(_ev(source))):
            return non_allow("ANCHOR_LINK_UNVERIFIED", f"ingress {ingress['receipt_sha256']} does not link a source half "
                             "on this endpoint ledger by seal", node_id=node_id, **anchor_info)
        if kind == EPHEMERAL:
            unsigned = opened_signature_failure(body)
            if unsigned:
                return non_allow(*unsigned, node_id=node_id, **anchor_info)
            record = body["node_ledger_opened"]
            opened = opened_record_failure(record, genesis)
            if opened:
                return non_allow(*opened, node_id=node_id, **anchor_info)
            anchor_info.update(node_ledger_opened_signer_key_id=body["signature"]["key_id"],
                               node_ledger_opened_generation_receipt_sha256=record["receipt_sha256"],
                               node_ledger_opened=issued_anchor(node_id, key, genesis_sha, ingress["receipt_sha256"]))
        else:
            if body.get("node_identity_key") != key:
                return non_allow("KEY_MISMATCH", "the anchor binds another node_identity_key than the genesis",
                                 node_id=node_id, **anchor_info)
            if body != anchor_body(genesis):
                return non_allow("ENDPOINT_GENESIS_INVALID", "the anchor body differs from the genesis it names",
                                 node_id=node_id, **anchor_info)
        anchor_info.update(anchor=("NODE_LEDGER_OPENED_VIA_INTR_PATH_RECEIPT_PAIR" if kind == EPHEMERAL
                                   else "INTR_PATH_RECEIPT_PAIR"), anchor_source_receipt_sha256=source_sha,
                           anchor_destination_receipt_sha256=ingress["receipt_sha256"])
    for r in chain:
        seen = _key_of_receipt(r)
        if seen is not None and not _key_matches(key, seen):
            return non_allow("KEY_MISMATCH", f"{r['receipt_sha256']} carries another node_identity_key",
                             node_id=node_id, **anchor_info)
    if check_provenance:
        foreign = provenance_failure(chain, node_id, kind)
        if foreign:
            return non_allow(*foreign, node_id=node_id, **anchor_info)
    return {"schema": RESULT_SCHEMA, "disposition": ALLOW, "node_id": node_id, **anchor_info,
            "chain_head_receipt_sha256": chain[0]["receipt_sha256"],
            "org_ledger_head_receipt_sha256": org_ledger_head_receipt_sha256,
            "pinned_code_digests_sha256": pinned_digests_sha256(), "evaluator_sha256": EVALUATOR_SHA256,
            "pinned_digests": pinned_digests(),
            "producer_provenance": "NOT_PROVEN_BEYOND_PINNED_SHAPE", "authority_effect": "NONE_EVALUATION_ONLY"}


def pinned_digests() -> dict[str, str]:
    """The evaluator and producer digests, as KV names them (evidence.pinned_digests in cvk#258)."""
    pins = load_pins()["digests"]
    return {"evaluator_source_sha256": pins["llm_adapter/healthy_node_evaluator.py"],
            "producer_source_sha256": pins["llm_adapter/node_health_report_producer.py"]}


def issued_anchor(node_id: str, node_identity_key: Mapping[str, Any], genesis_sha: str,
                  ingress_sha: str) -> dict[str, Any]:
    """The stegverse.node-ledger-opened/v1 anchor the org ledger's ingress issues. Pure."""
    body = {"schema": OPENED_ANCHOR_SCHEMA, "transition_class": OPENED_CLASS, "node_id": node_id,
            "node_identity_key": dict(node_identity_key), "genesis_receipt_sha256": genesis_sha,
            "issuer": ISSUER_ORGANIZATION_LEDGER, "issuer_receipt_ref": ingress_sha}
    return {**body, "receipt_sha256": opened_record_sha256(body)}


def verify_node_ledger_opened_anchor(anchor_receipt: Any, *, ledger_root: Any, org_ledger_git_dir: Any,
                                     org_ledger_head_receipt_sha256: Any) -> dict[str, Any]:
    """The ORGANIZATION_LEDGER issuer verifier: ALLOW only for the anchor the designated org ledger re-derives.

    The org ledger is the contract's repository_ledger_location read back from the object store, at the pinned head.
    """
    node_id = anchor_receipt.get("node_id") if isinstance(anchor_receipt, Mapping) else None
    if not isinstance(anchor_receipt, Mapping) or tuple(sorted(anchor_receipt)) != tuple(sorted(OPENED_ANCHOR_FIELDS)) \
            or anchor_receipt.get("schema") != OPENED_ANCHOR_SCHEMA \
            or anchor_receipt.get("transition_class") != OPENED_CLASS \
            or anchor_receipt.get("issuer") != ISSUER_ORGANIZATION_LEDGER \
            or anchor_receipt.get("receipt_sha256") != opened_record_sha256(anchor_receipt):
        return non_allow("NODE_LEDGER_OPENED_ANCHOR_NOT_ISSUED", "not a sealed stegverse.node-ledger-opened/v1 anchor "
                         "issued by ORGANIZATION_LEDGER", node_id=node_id)
    with designated_org_ledger(org_ledger_git_dir) as (org_root, failed):
        if failed:
            return non_allow(*failed, node_id=node_id)
        verified = verify_anchor(node_id, endpoint={"endpoint_kind": EPHEMERAL, "ledger_root": ledger_root},
                                 org_ledger_root=org_root, org_ledger_head_receipt_sha256=org_ledger_head_receipt_sha256)
    if verified["disposition"] != ALLOW:
        return verified
    if verified["node_ledger_opened"] != dict(anchor_receipt):
        return non_allow("NODE_LEDGER_OPENED_ANCHOR_NOT_ISSUED", "the anchor differs from the one the org ledger's "
                         f"ingress {verified['anchor_destination_receipt_sha256']} issues", node_id=node_id)
    return {"schema": RESULT_SCHEMA, "disposition": ALLOW, "node_id": node_id, "issuer": ISSUER_ORGANIZATION_LEDGER,
            "issuer_receipt_ref": anchor_receipt["issuer_receipt_ref"], "anchor": verified,
            "org_ledger_location": ORG_LEDGER_LOCATION, "authority_effect": "NONE_EVALUATION_ONLY"}


def identity_challenge(anchored: Mapping[str, Any]) -> dict[str, Any]:
    """The deterministic challenge a node signs to prove its identity, bound to the receipt chain. Pure."""
    return {"schema": IDENTITY_CHALLENGE_SCHEMA, "node_id": anchored.get("node_id"),
            "endpoint_kind": anchored.get("endpoint_kind"),
            "genesis_receipt_sha256": anchored.get("genesis_receipt_sha256"),
            "chain_head_receipt_sha256": anchored.get("chain_head_receipt_sha256"),
            "anchor_receipt_sha256": anchored.get("anchor_destination_receipt_sha256")
            or anchored.get("genesis_receipt_sha256"),
            "org_ledger_head_receipt_sha256": anchored.get("org_ledger_head_receipt_sha256")}


def identity_challenge_message(challenge: Mapping[str, Any]) -> bytes:
    """The bytes the node signs (the same domain-separated encoding as NODE_IDENTITY_BINDING's claim)."""
    return common.signed_message(IDENTITY_CHALLENGE_SCHEMA, dict(challenge))


def _genesis_key(anchored: Mapping[str, Any]) -> Mapping[str, Any]:
    chain, _, _ = hne.read_chain(anchored["ledger_root"])
    return _ev(chain[-1]).get("node_identity_key") or {}


def identity_proof_failure(proof: Any, anchored: Mapping[str, Any]) -> tuple[str, str] | None:
    """(reason, detail) unless `proof` is the anchored key's signature over the current challenge, else None."""
    if not isinstance(proof, Mapping) or proof.get("schema") != IDENTITY_PROOF_SCHEMA:
        return "NODE_IDENTITY_PROOF_ABSENT", "no stegverse.node-identity-proof/v1; identity is never taken as asserted"
    key = _genesis_key(anchored)
    challenge = identity_challenge(anchored)
    public = common.b64(key.get("public_key_b64"))
    signature = common.b64(proof.get("signature_b64"))
    if proof.get("node_id") != anchored.get("node_id") or proof.get("key_id") != key.get("key_id"):
        return "NODE_IDENTITY_PROOF_INVALID", "the proof names another node or key than the anchored genesis"
    if proof.get("challenge_sha256") != sha(challenge):
        return "NODE_IDENTITY_PROOF_INVALID", "the proof is over another challenge (stale chain or org-ledger head)"
    if public is None or len(public) != 32 or signature is None or len(signature) != 64 \
            or not ed25519_verify.verify(public, identity_challenge_message(challenge), signature):
        return "NODE_IDENTITY_PROOF_INVALID", "the Ed25519 signature does not verify under the anchored public key"
    return None


def observed_transport(ledger_root: Any, node_id: str) -> dict[str, Any] | None:
    """The transport the node's current NODE_INGRESS_ADMITTED record says carried it, or None. Pure."""
    chain, failure, _ = hne.read_chain(ledger_root)
    if failure:
        return None
    for r in chain:   # newest first: the node's latest ingress record decides
        if r.get("transition_class") in (boundary.ADMITTED_CLASS, boundary.REFUSED_CLASS):
            ev = _ev(r)
            node = ((ev.get("node_endpoint") or {}).get("node_id") if r["transition_class"] == boundary.ADMITTED_CLASS
                    else ev.get("evaluated_node_id"))
            if node == node_id:
                return {"transport": ev.get("transport"), "transport_state": ev.get("transport_state"),
                        "receipt_sha256": r["receipt_sha256"], "transition_class": r["transition_class"]}
    return None


def evaluate_anchored(claimed_node_id: Any = None, *, endpoint: Any, org_ledger_git_dir: Any,
                      org_ledger_head_receipt_sha256: Any, identity_proof: Any = None,
                      transport_state: Any = None, report_receipt_sha256: Any = None) -> dict[str, Any]:
    """healthy_node_evaluator.evaluate, unchanged, over the anchored root, the observed transport and a proven identity.

    LC-KV-16: the node_id is the one the verified node_identity_key proof establishes; ``claimed_node_id`` only has
    to agree with it and selects nothing. ``transport_state`` is a caller assertion and decides nothing; there is no
    transport default. The org ledger is the contract's designated location read from ``org_ledger_git_dir``.
    """
    asserted = {"asserted_transport_state": transport_state, "asserted_transport_state_decides": False,
                "claimed_node_id": claimed_node_id, "claimed_node_id_decides": False}
    gate = {"predicate": hne.PREDICATE, "gate": hne.GATE}

    def identity_refusal(reason, detail, node_id=None, **extra):
        return {**non_allow(reason, detail, node_id=node_id, failure_code=IDENTITY_FAILURE_CODE,
                            reasons=IDENTITY_REASONS, retry_entrypoint=IDENTITY_RETRY, next_attempt=IDENTITY_NEXT,
                            **extra, **asserted), **gate}

    if not isinstance(identity_proof, Mapping) or identity_proof.get("schema") != IDENTITY_PROOF_SCHEMA \
            or not isinstance(identity_proof.get("node_id"), str) or not identity_proof.get("node_id"):
        return identity_refusal("NODE_IDENTITY_PROOF_ABSENT", "no stegverse.node-identity-proof/v1; the node_id is "
                                "derived only from a verified proof, never taken as asserted")
    node_id = identity_proof["node_id"]      # a candidate until the signature below verifies
    with designated_org_ledger(org_ledger_git_dir) as (org_root, failed):
        if failed:
            return {**non_allow(*failed, node_id=node_id, **asserted), **gate}
        anchored = verify_anchor(node_id, endpoint=endpoint, org_ledger_root=org_root,
                                 org_ledger_head_receipt_sha256=org_ledger_head_receipt_sha256)
        if anchored["disposition"] != ALLOW:
            return {**anchored, **asserted, **gate}
        anchored = {**anchored, "org_ledger_location": ORG_LEDGER_LOCATION}
        failed = identity_proof_failure(identity_proof, anchored)
        if failed:
            return {**identity_refusal(*failed, node_id=node_id, identity_challenge=identity_challenge(anchored)),
                    "anchor": anchored}
        if claimed_node_id is not None and claimed_node_id != node_id:
            return {**identity_refusal("NODE_IDENTITY_PROOF_INVALID", f"claimed node_id {claimed_node_id!r} is not "
                                       f"the proven {node_id}", node_id=node_id), "anchor": anchored}
        seen = observed_transport(anchored["ledger_root"], node_id)
        if seen is None or seen.get("transition_class") != boundary.ADMITTED_CLASS \
                or seen.get("transport") != boundary.INTERLOCK_INTR or seen.get("transport_state") != hne.INSTALLED:
            return {**non_allow(TRANSPORT_FAILURE_CODE, f"observed on receipts: {seen!r}; no installed InTr transport "
                                "receipt for this node's current ingress", node_id=node_id,
                                failure_code=TRANSPORT_FAILURE_CODE, reasons=TRANSPORT_REASONS,
                                retry_entrypoint=TRANSPORT_RETRY, next_attempt=TRANSPORT_NEXT,
                                observed_transport=seen, **asserted), **gate, "anchor": anchored}
        observed_state = seen["transport_state"]     # from the receipt; passed explicitly, never the evaluator default
        result = hne.evaluate(node_id, ledger_root=anchored["ledger_root"], transport_state=observed_state,
                              report_receipt_sha256=report_receipt_sha256, require_admission=True)
        key_id = _genesis_key(anchored).get("key_id")
    return {**result, "anchor": anchored, "observed_transport": seen, **asserted,
            "identity": {"node_id": node_id, "key_id": key_id, "established_by": "NODE_IDENTITY_KEY_ED25519_PROOF",
                         "challenge_sha256": sha(identity_challenge(anchored))}}


__all__ = ["ENDPOINT_KINDS", "EPHEMERAL", "FAILURE_CODE", "GATEWAY", "IDENTITY_FAILURE_CODE", "OWN_LEDGER_KINDS",
           "REASONS", "TRANSPORT_FAILURE_CODE", "anchor", "append_destination", "append_receipt", "append_source",
           "designated_org_ledger", "evaluate_anchored", "identity_challenge", "identity_challenge_message", "issued_anchor",
           "load_opened_signers", "open_gateway_location", "opened_signature_failure", "opened_signing_message",
           "org_ledger_location", "signed_opened",
           "open_ledger", "opened_record_failure", "plan_open", "verify_anchor", "verify_node_ledger_opened_anchor"]
