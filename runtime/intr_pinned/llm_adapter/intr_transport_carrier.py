"""The InTr path pair that carried a signal to this boundary (LLM-ADAPTER-INTERLOCK-INTR-TRANSPORT-ENABLEMENT-001).

`node_ingress_boundary.TRANSPORTS[INTERLOCK_INTR]` is INSTALLED, but a caller
that names INTERLOCK_INTR has not thereby arrived over it. A crossing counts as
an InTr crossing only when the path pair that carried it is on receipts:

  1. INTR_MESH_PATH_TRANSFER (evidence stegverse.intr-path-transfer-evidence/v1),
     the sender's own egress record, on the sender's own recorded receipt chain
     (a node's own ledger), never copied onto the organization ledger, then
  2. INTR_MESH_PATH_INGRESS, operation ORGANIZATION_INTR_DESTINATION_INGRESS
     (evidence stegverse.intr-path-ingress-evidence/v1), the Org's own record on
     the organization ledger at #431's location: digest-only, exactly {schema,
     path_id, communication_id, source_repository_receipt_sha256,
     destination_location, boundary_evidence {operation, path_id,
     communication_id, endpoint_head_sha256}} (the #432 crossing_evidence shape,
     endpoint_ledger_designation.ORG_CROSSING_EVIDENCE_KEYS), naming the source
     half by its seal and carrying no body,

with the communication body digest (read from the source half) equal to the arriving signal's digest.

Q-PERMANENT-REPOSITORY-LEDGER (StegVerse-org/.github#167 comment 6374130335): the
earlier carrier retained the sender's source half at source-receipts/<hex>.json and
copied the message body into the Org's ingress record, so a node's own egress chain
was written into repository-ledger/StegVerse-org/LLM-adapter. That namespace is
split: LLM-adapter's own repository work and the Org's digest-only crossing records
stay on it (ORG-kind); the node's record stays on the node's own ledger
(ruling 6373412055 item 3). An Org-emitted source half (the genesis-pin ingress,
StegVerse-org/.github's own path) is an Org record and may still be kept by the Org. These
are the existing InTr classes (StegVerse-org/.github data/intr-protocol/v1 and
resident-runtime/intr_path_ingress.py) in the emit.py receipt shape
(stegverse.repo-transition-receipt/v1), with the same evidence fields and
payload_sha256 rule as #432's endpoint_ledger_anchor. Nothing here mints a class.

`verify` is pure: no clock, no network, no file or process access. It is given
the org chain already read back (newest first, seals checked by
healthy_node_evaluator.read_chain), the source half as read back from the
sender's own chain, and the head the caller pinned. `observe` is the I/O step:
it reads the org chain through org_ledger_location.designated_org_ledger and the
source half from the sender's own ledger (``source_ledger_root``, seals checked),
then calls `verify`. That read-back
accepts a store only at the contract's pinned genesis and with a published
append-route head attestation (LC-KV-16 rev 5); none is published, so every
carrier is refused MERGE_APPEND_PATH_NOT_ADMITTED until the route is admitted.

Either returns None (verified) or (reason, detail). The ingress boundary turns a
non-None result into the six-field INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

RECEIPT_SCHEMA = "stegverse.repo-transition-receipt/v1"
REPOSITORY = "StegVerse-org/LLM-adapter"
ORGANIZATION = "StegVerse-org"
ORG_LEDGER_LOCATION = "refs/stegverse/organization-ledger:repository-ledger/StegVerse-org/LLM-adapter"
SOURCE_CLASS = "INTR_MESH_PATH_TRANSFER"
SOURCE_EVIDENCE_SCHEMA = "stegverse.intr-path-transfer-evidence/v1"
DESTINATION_CLASS = "INTR_MESH_PATH_INGRESS"
DESTINATION_OPERATION = "ORGANIZATION_INTR_DESTINATION_INGRESS"
DESTINATION_EVIDENCE_SCHEMA = "stegverse.intr-path-ingress-evidence/v1"
MESSAGE_CLASS = "ecosystem.communication"
CAPABILITY = "intr-destination"
ENDPOINT_KIND = "NODE_INGRESS_SIGNAL"
SOURCE_INCLUSION = "READ_BACK_FROM_THE_SENDER_OWN_LEDGER_NEVER_RETAINED"
#: #432's dissolution class (endpoint_ledger_anchor.DISSOLVED_CLASS), reused by value.
DISSOLVED_CLASS = "NODE_LEDGER_DISSOLVED"

#: Source-evidence fields a source half must carry (destination_evidence takes path_id and communication_id from
#: them); one missing is refused, not raised.
SOURCE_REBUILD_KEYS = ("path_id", "message", "message_sha256", "endpoint_kind", "communication_id")
#: The only keys the Org's own ingress record may carry: pointers and digests (= #432/#431
#: endpoint_ledger_designation.ORG_CROSSING_EVIDENCE_KEYS / ORG_CROSSING_BOUNDARY_KEYS, by value).
ENDPOINT_HEAD_KEY = "endpoint_head_sha256"
DESTINATION_KEYS = frozenset({"schema", "path_id", "communication_id", "source_repository_receipt_sha256",
                              "destination_location", "boundary_evidence"})
DESTINATION_BOUNDARY_KEYS = frozenset({"operation", "path_id", "communication_id", ENDPOINT_HEAD_KEY})

#: The six-field code and predicate for a transport that was named but not observed.
FAILURE_CODE = "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED"
PREDICATE = "INSTALLED_INTR_TRANSPORT_OBSERVED_ON_RECEIPTS"
OWNING_GOAL = "StegVerse-org/.github#162 (LLM-ADAPTER-INTERLOCK-INTR-TRANSPORT-ENABLEMENT-001)"
RETRY_ENTRYPOINT = ("llm_adapter.node_ingress_boundary.admit(signal, transport='INTERLOCK_INTR', "
                    "intr_carrier={destination_receipt_sha256, org_ledger_head_receipt_sha256, "
                    "org_ledger_head_attestation, source_ledger_root}, "
                    "org_ledger_git_dir=<local StegVerse-org/.github object store>)")
NEXT_ATTEMPT = ("Event-triggered: when the carrying INTR_MESH_PATH_INGRESS is on the organization ledger at "
                "#431's location; no clock, no polling.")
REPAIR = ("Carry the signal over InTr: the sender records its INTR_MESH_PATH_TRANSFER source half (message body = the "
          "signal) on its own recorded receipt chain, and the Org records its own digest-only INTR_MESH_PATH_INGRESS "
          "(ORGANIZATION_INTR_DESTINATION_INGRESS) at " + ORG_LEDGER_LOCATION + " naming that source half by seal; "
          "then cite that destination receipt, the org ledger head and the sender's ledger read-back.")


def sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                                 ensure_ascii=False).encode("utf-8")).hexdigest()


def payload_ok(evidence: Mapping[str, Any]) -> bool:
    """intr_path_ingress._payload_ok's rule, with boundary_evidence also outside the digest (as #432)."""
    core = {k: v for k, v in evidence.items()
            if k not in ("payload_sha256", "disposition", "communication_id", "boundary_evidence")}
    return evidence.get("payload_sha256") == sha(core)


def path_id(node_ref: Any) -> str:
    return f"{node_ref}->{ORGANIZATION}:{CAPABILITY}"


def source_evidence(signal: Mapping[str, Any], communication_id: str) -> dict[str, Any]:
    """The source half's evidence, the #432 endpoint_ledger_anchor.source_evidence shape, body = the signal."""
    message = {"message_class": MESSAGE_CLASS, "communication_id": communication_id, "body": dict(signal)}
    pid = path_id(signal.get("node_ref"))
    core = {"schema": SOURCE_EVIDENCE_SCHEMA, "repository": REPOSITORY, "path_id": pid,
            "destination_organization": ORGANIZATION, "destination_location": ORG_LEDGER_LOCATION,
            "endpoint_kind": ENDPOINT_KIND, "message": message, "message_sha256": sha(message)}
    return {**core, "payload_sha256": sha(core), "disposition": "ALLOW", "communication_id": communication_id,
            "boundary_evidence": {"operation": SOURCE_CLASS, "path_id": pid, "communication_id": communication_id}}


def destination_evidence_failure(source: Any) -> tuple[str, str] | None:
    """(reason, detail) when `source` lacks a field the destination half is rebuilt from, else None. Pure."""
    ev = source.get("evidence") if isinstance(source, Mapping) else None
    if not isinstance(ev, Mapping):
        return "INTR_SOURCE_EVIDENCE_INCOMPLETE", "the source half is not a receipt with an evidence object"
    missing = [k for k in SOURCE_REBUILD_KEYS if k not in ev] + \
        [k for k in ("repository", "receipt_sha256") if not isinstance(source.get(k), str)]
    if missing:
        return "INTR_SOURCE_EVIDENCE_INCOMPLETE", (f"{source.get('receipt_sha256')!r} lacks {', '.join(missing)}, so "
                                                   "the destination half cannot be rebuilt from it")
    if not (isinstance(source["receipt_sha256"], str) and source["receipt_sha256"].startswith("sha256:")):
        return "INTR_SOURCE_EVIDENCE_INCOMPLETE", f"{source['receipt_sha256']!r} is not a sha256 seal"
    return None


def refusal(reason: str, detail: str) -> dict[str, Any]:
    """The six-field FAIL_CLOSED for `reason` under FAILURE_CODE (an existing code; nothing new is minted)."""
    return {"disposition": "FAIL_CLOSED", "reason": reason, "detail": detail, "failure_code": FAILURE_CODE,
            "failed_predicate": PREDICATE, "required_evidence_or_repair": f"{REPAIR} ({reason}: {detail})",
            "retry_entrypoint": RETRY_ENTRYPOINT, "owning_existing_goal": OWNING_GOAL, "next_attempt": NEXT_ATTEMPT,
            "authority_effect": "NONE"}


def destination_evidence(source: Mapping[str, Any]) -> dict[str, Any]:
    """The Org's own digest-only ingress evidence for a sealed source half: pointers and digests only, no body, no
    endpoint as originator (the #432 crossing_evidence shape). A source half lacking a field it is built from is the
    six-field FAIL_CLOSED, never a KeyError (LC-KV-20)."""
    failed = destination_evidence_failure(source)
    if failed:
        return refusal(*failed)
    ev, seal = source["evidence"], source["receipt_sha256"]
    return {"schema": DESTINATION_EVIDENCE_SCHEMA, "path_id": ev["path_id"], "communication_id": ev["communication_id"],
            "source_repository_receipt_sha256": seal, "destination_location": ORG_LEDGER_LOCATION,
            "boundary_evidence": {"operation": DESTINATION_OPERATION, "path_id": ev["path_id"],
                                  "communication_id": ev["communication_id"], ENDPOINT_HEAD_KEY: seal}}


def _sealed(receipt: Any) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return receipt.get("schema") == RECEIPT_SCHEMA and receipt.get("receipt_sha256") == sha(body)


def verify(signal: Any, *, destination_receipt_sha256: Any, org_ledger_head_receipt_sha256: Any,
           org_chain: Any, source_record: Any) -> tuple[str, str] | None:
    """Pure check that one InTr path pair carried exactly this signal: the Org's digest-only ingress at #431's
    location names, by seal, ``source_record``, the sender's egress record read back from the sender's own chain."""
    if not isinstance(signal, Mapping):
        return "SIGNAL_NOT_AN_OBJECT", "the arriving signal is not an object"
    if not isinstance(org_chain, list) or not org_chain:
        return "ORG_LEDGER_CHAIN_EMPTY", "no organization ledger chain was read back"
    if org_chain[0].get("receipt_sha256") != org_ledger_head_receipt_sha256:
        return "ORG_LEDGER_HEAD_NOT_PINNED", (f"read-back head {org_chain[0].get('receipt_sha256')} is not the pinned "
                                              f"head {org_ledger_head_receipt_sha256!r}")
    destination = next((r for r in org_chain if r.get("receipt_sha256") == destination_receipt_sha256), None)
    if destination is None:
        return "INTR_DESTINATION_NOT_ON_ORG_LEDGER", f"{destination_receipt_sha256!r} is not on the org ledger chain"
    ev = destination.get("evidence") if isinstance(destination.get("evidence"), Mapping) else {}
    if (not _sealed(destination) or destination.get("transition_class") != DESTINATION_CLASS
            or ev.get("schema") != DESTINATION_EVIDENCE_SCHEMA
            or (ev.get("boundary_evidence") or {}).get("operation") != DESTINATION_OPERATION):
        return "INTR_DESTINATION_NOT_AN_INGRESS", f"{destination_receipt_sha256} is not a sealed {DESTINATION_CLASS}"
    if ev.get("destination_location") != ORG_LEDGER_LOCATION:
        return "INTR_DESTINATION_WRONG_LOCATION", (f"addressed {ev.get('destination_location')!r}, not "
                                                   f"{ORG_LEDGER_LOCATION}")
    be = ev.get("boundary_evidence") if isinstance(ev.get("boundary_evidence"), Mapping) else {}
    if set(ev) != DESTINATION_KEYS or set(be) != DESTINATION_BOUNDARY_KEYS:
        return "INTR_DESTINATION_NOT_DIGEST_ONLY", (f"{destination_receipt_sha256} carries "
                                                    f"{sorted(set(ev) ^ DESTINATION_KEYS)} / boundary_evidence "
                                                    f"{sorted(set(be) ^ DESTINATION_BOUNDARY_KEYS)}: the Org's record "
                                                    "of a crossing holds pointers and digests only, never the body")
    source_sha = ev.get("source_repository_receipt_sha256")
    if (not _sealed(source_record) or source_record.get("receipt_sha256") != source_sha
            or source_record.get("transition_class") != SOURCE_CLASS):
        return "INTR_SOURCE_NOT_ON_SENDER_LEDGER", (f"no sealed {SOURCE_CLASS} {source_sha!r} was read back from the "
                                                    "sender's own recorded receipt chain")
    sev = source_record.get("evidence") if isinstance(source_record.get("evidence"), Mapping) else {}
    if (sev.get("schema") != SOURCE_EVIDENCE_SCHEMA or not payload_ok(sev)
            or sev.get("destination_location") != ORG_LEDGER_LOCATION
            or sev.get("destination_organization") != ORGANIZATION
            or (sev.get("boundary_evidence") or {}).get("operation") != SOURCE_CLASS):
        return "INTR_SOURCE_NOT_A_TRANSFER", f"{source_sha} is not an {SOURCE_EVIDENCE_SCHEMA} to {ORG_LEDGER_LOCATION}"
    # A source half missing a field the destination half is rebuilt from fails closed here (six fields at the
    # caller), never with a KeyError out of destination_evidence (LC-KV-20).
    incomplete = destination_evidence_failure(source_record)
    if incomplete:
        return incomplete
    message = sev.get("message") if isinstance(sev.get("message"), Mapping) else {}
    if message.get("message_class") != MESSAGE_CLASS or sev.get("message_sha256") != sha(dict(message)):
        return "INTR_MESSAGE_UNSEALED", "message is not a sealed " + MESSAGE_CLASS
    if ev != destination_evidence(source_record):
        return "INTR_PAIR_NOT_LINKED", f"{destination_receipt_sha256} does not link {source_sha} by seal and message"
    if sha(message.get("body")) != sha(dict(signal)):
        return "INTR_BODY_IS_NOT_THE_SIGNAL", (f"carried body {sha(message.get('body'))} is not the signal "
                                               f"{sha(dict(signal))}")
    if sev.get("path_id") != path_id(signal.get("node_ref")):
        return "INTR_PATH_NOT_THE_SIGNALS", f"path {sev.get('path_id')!r} is not {path_id(signal.get('node_ref'))}"
    # A carrier issued before the node's NODE_LEDGER_DISSOLVED does not outlive it:
    # the chain is newest first, so anything ahead of the destination is later.
    later = org_chain[:org_chain.index(destination)]
    dissolved = next((r for r in later if r.get("transition_class") == DISSOLVED_CLASS
                      and isinstance(r.get("evidence"), Mapping)
                      and r["evidence"].get("node_id") == signal.get("node_ref")), None)
    if dissolved is not None:
        return "INTR_CARRIER_NODE_DISSOLVED", (f"{destination_receipt_sha256} predates NODE_LEDGER_DISSOLVED "
                                               f"{dissolved.get('receipt_sha256')} for {signal.get('node_ref')!r}")
    return None


def read_source(source_ledger_root: Any, digest: Any) -> Any:
    """The sender's egress record `digest`, read back from the sender's own recorded receipt chain (seals and links
    checked by healthy_node_evaluator.read_chain), or None. Never read from the organization ledger."""
    from llm_adapter import healthy_node_evaluator as hne
    if source_ledger_root is None or not isinstance(digest, str) or not digest.startswith("sha256:"):
        return None
    try:
        chain, failure, _ = hne.read_chain(Path(source_ledger_root))
    except Exception:
        return None
    return None if failure else next((r for r in chain if r.get("receipt_sha256") == digest), None)


def observe(signal: Any, intr_carrier: Any, org_ledger_git_dir: Any) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    """Read the Org's half back from #431's location and the sender's half from the sender's own ledger
    (intr_carrier["source_ledger_root"]), then `verify`. Returns (carrier, None) or (None, (reason, detail))."""
    from llm_adapter import healthy_node_evaluator as hne, org_ledger_location as location
    if not isinstance(intr_carrier, Mapping):
        return None, ("INTR_CARRIER_NOT_CITED", "INTERLOCK_INTR was named; no carrying path pair was cited")
    with location.designated_org_ledger(org_ledger_git_dir, intr_carrier.get("org_ledger_head_attestation")) \
            as (root, failure):
        if failure:
            return None, failure
        chain, chain_failure, detail = hne.read_chain(root)
        if chain_failure:
            return None, (chain_failure, detail)
        destination = next((r for r in chain
                            if r.get("receipt_sha256") == intr_carrier.get("destination_receipt_sha256")), {})
        source_sha = (destination.get("evidence") or {}).get("source_repository_receipt_sha256") \
            if isinstance(destination.get("evidence"), Mapping) else None
        source = read_source(intr_carrier.get("source_ledger_root"), source_sha)
        refused = verify(signal, destination_receipt_sha256=intr_carrier.get("destination_receipt_sha256"),
                         org_ledger_head_receipt_sha256=intr_carrier.get("org_ledger_head_receipt_sha256"),
                         org_chain=chain, source_record=source)
    if refused:
        return None, refused
    return {"destination_receipt_sha256": intr_carrier["destination_receipt_sha256"],
            "source_receipt_sha256": source_sha,
            "org_ledger_head_receipt_sha256": intr_carrier["org_ledger_head_receipt_sha256"],
            "org_ledger_location": ORG_LEDGER_LOCATION, "org_ledger_head_authenticated": True,
            "carrier_classes": [SOURCE_CLASS, DESTINATION_CLASS]}, None


__all__ = ["DESTINATION_BOUNDARY_KEYS", "DESTINATION_CLASS", "DESTINATION_KEYS", "FAILURE_CODE", "ORG_LEDGER_LOCATION",
           "PREDICATE", "SOURCE_CLASS", "destination_evidence", "destination_evidence_failure", "observe", "refusal",
           "payload_ok", "path_id", "read_source", "source_evidence", "verify"]
