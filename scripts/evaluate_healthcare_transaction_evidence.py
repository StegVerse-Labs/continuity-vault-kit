#!/usr/bin/env python3
"""Extract governing-schema facts and assemble a provenance-preserving patient evaluation."""
from __future__ import annotations
import hashlib, json
from typing import Any

def _source_ref(raw: bytes, locator: str) -> dict:
    return {"source_locator":locator,"source_sha256":hashlib.sha256(raw).hexdigest(),"source_size_bytes":len(raw)}

def extract_hpt(raw: bytes, locator: str) -> dict:
    doc=json.loads(raw)
    rows=doc.get("standard_charge_information")
    if not isinstance(rows,list):
        return {"disposition":"FAIL_CLOSED","predicate":"GOVERNING_SCHEMA_FACTS_EXTRACTED","reason":"HPT_STANDARD_CHARGE_INFORMATION_MISSING"}
    # Preserve governing field names and values exactly in the extracted facts.
    return {"disposition":"ALLOW","authority_id":"CMS-HPT-2026","governing_facts":{"standard_charge_information":rows},"source":_source_ref(raw,locator),"governing_fields_renamed":False}

def extract_tic_v2(raw: bytes, locator: str) -> dict:
    doc=json.loads(raw)
    required=("reporting_entity_name","reporting_entity_type")
    missing=[k for k in required if k not in doc]
    if missing:
        return {"disposition":"FAIL_CLOSED","predicate":"GOVERNING_SCHEMA_FACTS_EXTRACTED","reason":"TIC_REQUIRED_TOP_LEVEL_FIELDS_MISSING","missing":missing}
    facts={k:v for k,v in doc.items() if k in {"reporting_entity_name","reporting_entity_type","in_network","out_of_network"}}
    return {"disposition":"ALLOW","authority_id":"CMS-TIC-MRF-2.0","governing_facts":facts,"source":_source_ref(raw,locator),"governing_fields_renamed":False}

def extract_member_cost(raw: bytes, locator: str) -> dict:
    doc=json.loads(raw)
    # Member surfaces are plan/issuer contracts, not the public TiC MRF schema.
    if "patient_responsibility" not in doc and "cost_sharing_estimate" not in doc:
        return {"disposition":"FAIL_CLOSED","predicate":"MEMBER_COST_FACT_EXTRACTED","reason":"MEMBER_COST_RESULT_NOT_PRESENT"}
    return {"disposition":"ALLOW","authority_id":"CMS-TIC-COST-COMPARISON","governing_facts":doc,"source":_source_ref(raw,locator),"governing_fields_renamed":False}

def patient_evaluation(provider: dict, payer: dict|None=None, member: dict|None=None) -> dict:
    evidence=[x for x in (provider,payer,member) if x is not None]
    failures=[x for x in evidence if x.get("disposition")!="ALLOW"]
    if failures:
        return {"disposition":"FAIL_CLOSED","predicate":"PATIENT_ECONOMIC_EVIDENCE_VERIFIED","evidence_status":"NOT_VERIFIED","failures":failures,"patient_decision":None,"authority_effect":"NONE"}
    return {
      "disposition":"ALLOW",
      "predicate":"PATIENT_ECONOMIC_EVIDENCE_ASSEMBLED",
      "evidence_status":"VERIFIED" if member is not None else "PARTIALLY_VERIFIED",
      "provider_evidence":provider,
      "payer_evidence":payer,
      "member_evidence":member,
      "patient_decision":None,
      "patient_decision_required":True,
      "authority_effect":"NONE",
    }
