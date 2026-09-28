#!/usr/bin/env python3
"""Bounded substantiation and escalation for unsupported healthcare assertions."""
from __future__ import annotations
import hashlib,json

def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def open_validation(pre_state_sha256, assertion, required_evidence):
    if not pre_state_sha256 or not assertion.get("type"):
        return {"disposition":"FAIL_CLOSED","predicate":"VALIDATION_REQUEST_BOUND","reason":"MISSING_PRE_STATE_OR_ASSERTION_TYPE"}
    basis={"pre_service_state_sha256":pre_state_sha256,"assertion":assertion,"required_evidence":required_evidence}
    request_id=hashlib.sha256(canonical(basis)).hexdigest()
    return {"disposition":"ALLOW","predicate":"VALIDATION_REQUEST_BOUND","request_id":request_id,"basis":basis,"state":"PRESUMPTIVE_FRAUD / VALIDATION_REQUIRED","authority_effect":"NONE"}

def resolve_validation(request,rebuttal_evidence):
    if request.get("disposition")!="ALLOW":
        return {"disposition":"FAIL_CLOSED","predicate":"VALIDATION_REQUEST_AUTHENTIC","reason":"REQUEST_NOT_ALLOW"}
    refs=[x for x in rebuttal_evidence if x.get("evidence_ref") and x.get("sha256")]
    missing=[r for r in request["basis"]["required_evidence"] if not any(x.get("kind")==r for x in refs)]
    evidence_digest=hashlib.sha256(canonical(refs)).hexdigest()
    if missing:
        return {"disposition":"DENY","predicate":"ASSERTION_SUBSTANTIATED","request_id":request["request_id"],"pre_service_state_sha256":request["basis"]["pre_service_state_sha256"],"state":"UNRESOLVED_SUSPECTED_FRAUD / ESCALATION_REQUIRED","missing_evidence":missing,"rebuttal_evidence":refs,"rebuttal_evidence_sha256":evidence_digest,"original_state_mutated":False,"authority_effect":"NONE"}
    return {"disposition":"ALLOW","predicate":"ASSERTION_SUBSTANTIATED","request_id":request["request_id"],"pre_service_state_sha256":request["basis"]["pre_service_state_sha256"],"state":"PRESUMPTION_REBUTTED","rebuttal_evidence":refs,"rebuttal_evidence_sha256":evidence_digest,"original_state_mutated":False,"authority_effect":"NONE"}

def escalation_package(resolution, oversight_authority):
    if resolution.get("state")!="UNRESOLVED_SUSPECTED_FRAUD / ESCALATION_REQUIRED":
        return {"disposition":"DENY","predicate":"ESCALATION_REQUIRED","reason":"VALIDATION_NOT_UNRESOLVED","authority_effect":"NONE"}
    package={"request_id":resolution["request_id"],"pre_service_state_sha256":resolution["pre_service_state_sha256"],"missing_evidence":resolution["missing_evidence"],"rebuttal_evidence_sha256":resolution["rebuttal_evidence_sha256"],"oversight_authority":oversight_authority}
    return {"disposition":"ALLOW","predicate":"ESCALATION_PACKAGE_ASSEMBLED","package":package,"package_sha256":hashlib.sha256(canonical(package)).hexdigest(),"submission_effect":"NONE_NOT_SUBMITTED","authority_effect":"NONE"}
