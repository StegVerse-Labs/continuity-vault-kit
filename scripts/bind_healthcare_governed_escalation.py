#!/usr/bin/env python3
"""Bind healthcare escalation to applicable oversight and canonical governed egress."""
from __future__ import annotations
import hashlib,json
from scripts.resolve_healthcare_applicability import resolve

def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def bind_oversight(entity_class,jurisdiction,evidence_purpose,registry):
    x=resolve(entity_class,jurisdiction,evidence_purpose,registry)
    if x.get("disposition")!="ALLOW":
        return x
    authorities={m.get("regulator") for m in x["matches"] if m.get("regulator")}
    if len(authorities)!=1:
        return {"disposition":"FAIL_CLOSED","predicate":"OVERSIGHT_AUTHORITY_UNAMBIGUOUS","reason":"NO_SINGLE_APPLICABLE_OVERSIGHT_AUTHORITY","matches":x["matches"],"authority_effect":"NONE"}
    m=x["matches"][0]
    return {"disposition":"ALLOW","predicate":"OVERSIGHT_AUTHORITY_BOUND","oversight":{"authority_id":m["authority_id"],"regulator":m["regulator"],"regime":m["regime"],"jurisdiction":m["jurisdiction"]},"authority_effect":"NONE"}

def build_egress_candidate(escalation,oversight,task_id,cosv):
    if escalation.get("disposition")!="ALLOW" or escalation.get("predicate")!="ESCALATION_PACKAGE_ASSEMBLED":
        return {"disposition":"DENY","predicate":"ESCALATION_REQUIRED","reason":"NO_ADMISSIBLE_ESCALATION_PACKAGE","authority_effect":"NONE"}
    if oversight.get("disposition")!="ALLOW":
        return {"disposition":"FAIL_CLOSED","predicate":"OVERSIGHT_AUTHORITY_BOUND","reason":"OVERSIGHT_NOT_BOUND","authority_effect":"NONE"}
    packet={"schema":"stegverse.healthcare-governed-escalation-egress/v1","task_id":task_id,"cosv":cosv,"oversight":oversight["oversight"],"escalation_package":escalation["package"],"escalation_package_sha256":escalation["package_sha256"],"requested_transition":"EGRESS","required_components":["RTC-MANIFEST-001","RTC-GOVERNED-PROCESSING-002","RTC-STEGVERSE-EGRESS-007","RTC-INTERLOCK-INTR-TRANSPORT-008","RTC-EVIDENCE-CUSTODY-004"]}
    return {"disposition":"ALLOW","predicate":"GOVERNED_EGRESS_CANDIDATE_ASSEMBLED","packet":packet,"packet_sha256":hashlib.sha256(canonical(packet)).hexdigest(),"execution_disposition":"NOT_ATTEMPTED","submission_effect":"NONE_NOT_SUBMITTED","authority_effect":"NONE"}

def record_egress_result(candidate,intr_receipt=None,organization_receipt=None,master_records=None):
    if candidate.get("disposition")!="ALLOW":
        return {"disposition":"FAIL_CLOSED","predicate":"GOVERNED_EGRESS_CANDIDATE_VALID","reason":"CANDIDATE_NOT_ALLOW"}
    if not intr_receipt:
        return {"disposition":"FAIL_CLOSED","predicate":"AUTHENTIC_INTR_EGRESS_DISPOSITION_OBSERVED","failed_predicate":"AUTHENTIC_INTR_EGRESS_DISPOSITION_OBSERVED","evidence_refs":[],"packet_sha256":candidate["packet_sha256"]}
    decision=intr_receipt.get("disposition")
    if decision not in {"ALLOW","DENY","FAIL_CLOSED"}:
        return {"disposition":"FAIL_CLOSED","predicate":"INTR_EGRESS_DISPOSITION_VALID","failed_predicate":"INTR_EGRESS_DISPOSITION_VALID","evidence_refs":[intr_receipt.get("receipt_ref")]}
    if decision!="ALLOW":
        return {"disposition":decision,"predicate":"INTR_EGRESS_ADMITTED","failed_predicate":intr_receipt.get("failed_predicate"),"evidence_refs":[intr_receipt.get("receipt_ref")]}
    if not organization_receipt:
        return {"disposition":"FAIL_CLOSED","predicate":"EGRESS_ORGANIZATION_RECEIPT_RECORDED","failed_predicate":"ORGANIZATION_RECEIPT_PRESENT","evidence_refs":[intr_receipt.get("receipt_ref")]}
    evidence_refs=[intr_receipt.get("receipt_ref"),organization_receipt.get("receipt_ref")]
    if master_records and master_records.get("reconstruction_ref"):
        evidence_refs.append(master_records.get("reconstruction_ref"))
    return {"disposition":"ALLOW","predicate":"EGRESS_ORGANIZATION_RECEIPT_RECORDED","submission_effect":"AUTHENTIC_SUBMISSION_EVIDENCED","master_records_reconstruction":"OPTIONAL_NON_GATING","evidence_refs":evidence_refs,"packet_sha256":candidate["packet_sha256"]}
