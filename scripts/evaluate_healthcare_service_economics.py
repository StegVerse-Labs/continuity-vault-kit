#!/usr/bin/env python3
"""Bind a scheduled service to evidenced provider/payer facts and derive patient economics."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation

def _money(v):
    try: return Decimal(str(v))
    except (InvalidOperation,TypeError): return None

def _same_service(service,row):
    code=service.get("code")
    if code is None: return False
    candidates=[row.get("code"),row.get("billing_code"),row.get("billing_code_value")]
    if str(code) not in {str(x) for x in candidates if x is not None}: return False
    modifier=service.get("modifier")
    if modifier is not None and row.get("modifier") not in {None,modifier}: return False
    return True

def _derive(label,amount,refs,formula):
    return {"label":label,"amount":str(amount),"currency":"USD","formula":formula,"evidence_refs":refs}

def evaluate_service(service,provider_rows,payer_rows=None,member_facts=None):
    provider_matches=[r for r in provider_rows if _same_service(service,r)]
    if not provider_matches:
        return {"disposition":"FAIL_CLOSED","predicate":"SCHEDULED_SERVICE_PROVIDER_FACT_BOUND","reason":"NO_PROVIDER_FACT_FOR_SERVICE","service":service}
    if len(provider_matches)>1 and not service.get("bundle_id"):
        return {"disposition":"FAIL_CLOSED","predicate":"SCHEDULED_SERVICE_PROVIDER_FACT_UNAMBIGUOUS","reason":"MULTIPLE_PROVIDER_FACTS_REQUIRE_BUNDLE_OR_FURTHER_PREDICATE","service":service}
    p=provider_matches[0]; results=[]; refs=p.get("_evidence_refs",[])
    cash=_money(p.get("discounted_cash"))
    if cash is not None: results.append(_derive("provider_disclosed_cash_price",cash,refs,"governing provider field: discounted_cash"))

    payer_matches=[r for r in (payer_rows or []) if _same_service(service,r)]
    allowed=None
    if len(payer_matches)==1:
        q=payer_matches[0]; allowed=_money(q.get("negotiated_rate") if q.get("negotiated_rate") is not None else q.get("allowed_amount"))
        if allowed is not None: results.append(_derive("payer_evidenced_allowed_or_negotiated_amount",allowed,q.get("_evidence_refs",[]),"governing payer rate/allowed field"))

    if member_facts:
        responsibility=_money(member_facts.get("patient_responsibility") if member_facts.get("patient_responsibility") is not None else member_facts.get("cost_sharing_estimate"))
        if responsibility is not None:
            results.append(_derive("member_evidenced_patient_responsibility",responsibility,member_facts.get("_evidence_refs",[]),"member-authorized cost-sharing result"))

    cash_result=next((x for x in results if x["label"]=="provider_disclosed_cash_price"),None)
    insured_result=next((x for x in results if x["label"]=="member_evidenced_patient_responsibility"),None)
    comparison={
      "cash_patient_outlay":cash_result,
      "insurance_patient_outlay":insured_result,
      "difference":None,
      "recommendation":None,
    }
    if cash_result and insured_result:
        d=Decimal(insured_result["amount"])-Decimal(cash_result["amount"])
        comparison["difference"]=_derive("insurance_minus_cash_patient_outlay",d,cash_result["evidence_refs"]+insured_result["evidence_refs"],"insurance_patient_outlay - cash_patient_outlay")
    status="VERIFIED" if cash_result and insured_result else ("PARTIALLY_VERIFIED" if results else "NOT_VERIFIED")
    return {"disposition":"ALLOW" if results else "FAIL_CLOSED","predicate":"SERVICE_SPECIFIC_ECONOMIC_EVIDENCE_ASSEMBLED","service":service,"evidence_status":status,"derived_values":results,"comparison":comparison,"patient_decision":None,"patient_decision_required":True,"authority_effect":"NONE"}
