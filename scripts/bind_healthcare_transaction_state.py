#!/usr/bin/env python3
"""Immutable pre-service healthcare state and post-service reconciliation."""
from __future__ import annotations
import hashlib,json

def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def seal_pre_service(service,evaluation,patient_terms,evidence_refs):
    if evaluation.get("disposition")!="ALLOW":
        return {"disposition":"FAIL_CLOSED","predicate":"PRE_SERVICE_EVALUATION_ADMISSIBLE","reason":"EVALUATION_NOT_ALLOW"}
    state={"schema":"stegverse.healthcare-pre-service-state/v1","service":service,"evaluation":evaluation,"patient_terms":patient_terms,"evidence_refs":evidence_refs,"patient_decision":evaluation.get("patient_decision")}
    digest=hashlib.sha256(canonical(state)).hexdigest()
    return {"disposition":"ALLOW","predicate":"PRE_SERVICE_STATE_SEALED","state":state,"state_sha256":digest,"immutable":True,"authority_effect":"NONE"}

def reconcile(pre,actual_services=None,claim=None,eob=None,payment=None):
    if pre.get("disposition")!="ALLOW" or not pre.get("immutable"):
        return {"disposition":"FAIL_CLOSED","predicate":"PRE_SERVICE_STATE_AUTHENTIC","reason":"PRE_SERVICE_STATE_NOT_SEALED"}
    if hashlib.sha256(canonical(pre["state"])).hexdigest()!=pre.get("state_sha256"):
        return {"disposition":"FAIL_CLOSED","predicate":"PRE_SERVICE_STATE_HASH_VALID","reason":"PRE_SERVICE_STATE_MUTATED"}
    actual_services=actual_services or []
    scheduled=pre["state"]["service"]
    expected_code=str(scheduled.get("code"))
    variances=[]
    for row in actual_services:
        if str(row.get("code"))!=expected_code:
            variances.append({"type":"ACTUAL_SERVICE_VARIANCE","assertion":row,"status":"VALIDATION_REQUIRED"})
    assertion_objects=[x for x in (claim,eob,payment) if x is not None]
    unsupported=[]
    for obj in assertion_objects:
        if not obj.get("evidence_refs"):
            unsupported.append({"type":obj.get("type","ECONOMIC_ASSERTION"),"assertion":obj,"state":"PRESUMPTIVE_FRAUD / VALIDATION_REQUIRED"})
    status="CONFLICTING_EVIDENCE" if variances or unsupported else "VERIFIED"
    return {"disposition":"ALLOW","predicate":"POST_SERVICE_RECONCILIATION_ASSEMBLED","pre_service_state_sha256":pre["state_sha256"],"actual_services":actual_services,"claim":claim,"eob":eob,"payment":payment,"variances":variances,"unsupported_assertions":unsupported,"evidence_status":status,"patient_responsibility_inferred":False,"authority_effect":"NONE"}
