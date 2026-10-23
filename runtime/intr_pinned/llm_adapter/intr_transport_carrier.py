"""The InTr path pair that carried a signal to this boundary (LLM-ADAPTER-INTERLOCK-INTR-TRANSPORT-ENABLEMENT-001).

`node_ingress_boundary.TRANSPORTS[INTERLOCK_INTR]` is INSTALLED, but a caller
that names INTERLOCK_INTR has not thereby arrived over it. A crossing counts as
an InTr crossing only when the path pair that carried it is on receipts:

  1. INTR_MESH_PATH_TRANSFER (evidence stegverse.intr-path-transfer-evidence/v1),
     retained on the organization ledger at source-receipts/<hex>.json, then
  2. INTR_MESH_PATH_INGRESS, operation ORGANIZATION_INTR_DESTINATION_INGRESS
     (evidence stegverse.intr-path-ingress-evidence/v1), on the organization ledger
     at #431's location, addressed to that location, linking the source half by seal,

with the communication body digest equal to the arriving signal's digest. These
are the existing InTr classes (StegVerse-org/.github data/intr-protocol/v1 and
resident-runtime/intr_path_ingress.py) in the emit.py receipt shape
(stegverse.repo-transition-receipt/v1), with the same evidence fields and
payload_sha256 rule as #432's endpoint_ledger_anchor. Nothing here mints a class.

`verify` is pure: no clock, no network, no file or process access. It is given
the org chain already read back (newest first, seals checked by
healthy_node_evaluator.read_chain), the retained source copy, and the head the
caller pinned. `observe` is the I/O step that reads those through
org_ledger_location.designated_org_ledger and then calls `verify`. That read-back
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
SOURCE_INCLUSION = "READ_BACK_FROM_THE_ENDPOINT_LEDGER_AND_RETAINED"
#: #432's dissolution class (endpoint_ledger_anchor.DISSOLVED_CLASS), reused by value.
DISSOLVED_CLASS = "NODE_LEDGER_DISSOLVED"

#: The six-field code and predicate for a transport that was named but not observed.
FAILURE_CODE = "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED"
PREDICATE = "INSTALLED_INTR_TRANSPORT_OBSERVED_ON_RECEIPTS"
OWNING_GOAL = "StegVerse-org/.github#162 (LLM-ADAPTER-INTERLOCK-INTR-TRANSPORT-ENABLEMENT-001)"
RETRY_ENTRYPOINT = ("llm_adapter.node_ingress_boundary.admit(signal, transport='INTERLOCK_INTR', "
                    "intr_carrier={destination_receipt_sha256, org_ledger_head_receipt_sha256, "
                    "org_ledger_head_attestation}, "
                    "org_ledger_git_dir=<local StegVerse-org/.github object store>)")
NEXT_ATTEMPT = ("Event-triggered: when the carrying INTR_MESH_PATH_INGRESS is on the organization ledger at "
                "#431's location; no clock, no polling.")
REPAIR = ("Carry the signal over InTr: retain its INTR_MESH_PATH_TRANSFER source half at source-receipts/<hex>.json "
          "and append the INTR_MESH_PATH_INGRESS (ORGANIZATION_INTR_DESTINATION_INGRESS) at " + ORG_LEDGER_LOCATION +
          " whose message body is the signal, then cite that destination receipt and the org ledger head.")


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


def destination_evidence(source: Mapping[str, Any]) -> dict[str, Any]:
    """The destination half's evidence for a sealed source receipt (#432's destination_evidence shape)."""
    ev = source["evidence"]
    core = {"schema": DESTINATION_EVIDENCE_SCHEMA, "repository": REPOSITORY, "path_id": ev["path_id"],
            "source_repository": source["repository"], "source_repository_receipt_sha256": source["receipt_sha256"],
            "message": ev["message"], "message_sha256": ev["message_sha256"],
            "addressed_location": ORG_LEDGER_LOCATION, "endpoint_kind": ev["endpoint_kind"],
            "source_inclusion": SOURCE_INCLUSION}
    return {**core, "payload_sha256": sha(core), "disposition": "ALLOW", "communication_id": ev["communication_id"],
            "boundary_evidence": {"operation": DESTINATION_OPERATION, "path_id": ev["path_id"],
                                  "communication_id": ev["communication_id"],
                                  "source_repository_receipt_sha256": source["receipt_sha256"]}}


def _sealed(receipt: Any) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return receipt.get("schema") == RECEIPT_SCHEMA and receipt.get("receipt_sha256") == sha(body)


def verify(signal: Any, *, destination_receipt_sha256: Any, org_ledger_head_receipt_sha256: Any,
           org_chain: Any, retained_source: Any) -> tuple[str, str] | None:
    """Pure check that one InTr path pair at #431's location carried exactly this signal."""
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
    if ev.get("addressed_location") != ORG_LEDGER_LOCATION:
        return "INTR_DESTINATION_WRONG_LOCATION", f"addressed {ev.get('addressed_location')!r}, not {ORG_LEDGER_LOCATION}"
    source_sha = ev.get("source_repository_receipt_sha256")
    if (not _sealed(retained_source) or retained_source.get("receipt_sha256") != source_sha
            or retained_source.get("transition_class") != SOURCE_CLASS):
        return "INTR_SOURCE_NOT_RETAINED", f"no sealed {SOURCE_CLASS} retained at source-receipts for {source_sha!r}"
    sev = retained_source.get("evidence") if isinstance(retained_source.get("evidence"), Mapping) else {}
    if (sev.get("schema") != SOURCE_EVIDENCE_SCHEMA or not payload_ok(sev)
            or sev.get("destination_location") != ORG_LEDGER_LOCATION
            or sev.get("destination_organization") != ORGANIZATION
            or (sev.get("boundary_evidence") or {}).get("operation") != SOURCE_CLASS):
        return "INTR_SOURCE_NOT_A_TRANSFER", f"{source_sha} is not an {SOURCE_EVIDENCE_SCHEMA} to {ORG_LEDGER_LOCATION}"
    message = sev.get("message") if isinstance(sev.get("message"), Mapping) else {}
    if message.get("message_class") != MESSAGE_CLASS or sev.get("message_sha256") != sha(dict(message)):
        return "INTR_MESSAGE_UNSEALED", "message is not a sealed " + MESSAGE_CLASS
    if not payload_ok(ev) or ev != destination_evidence(retained_source):
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


def read_retained(org_ledger_root: Any, digest: Any) -> Any:
    if not isinstance(digest, str) or not digest.startswith("sha256:") or "/" in digest:
        return None
    try:
        return json.loads((Path(org_ledger_root) / "source-receipts" / (digest[7:] + ".json")).read_text("utf-8"))
    except Exception:
        return None


def observe(signal: Any, intr_carrier: Any, org_ledger_git_dir: Any) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    """Read the pair back from #431's location, then `verify`. Returns (carrier, None) or (None, (reason, detail))."""
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
        retained = read_retained(root, source_sha)
        refused = verify(signal, destination_receipt_sha256=intr_carrier.get("destination_receipt_sha256"),
                         org_ledger_head_receipt_sha256=intr_carrier.get("org_ledger_head_receipt_sha256"),
                         org_chain=chain, retained_source=retained)
    if refused:
        return None, refused
    return {"destination_receipt_sha256": intr_carrier["destination_receipt_sha256"],
            "source_receipt_sha256": source_sha,
            "org_ledger_head_receipt_sha256": intr_carrier["org_ledger_head_receipt_sha256"],
            "org_ledger_location": ORG_LEDGER_LOCATION, "org_ledger_head_authenticated": True,
            "carrier_classes": [SOURCE_CLASS, DESTINATION_CLASS]}, None


__all__ = ["DESTINATION_CLASS", "FAILURE_CODE", "ORG_LEDGER_LOCATION", "PREDICATE", "SOURCE_CLASS",
           "destination_evidence", "observe", "payload_ok", "path_id", "source_evidence", "verify"]
