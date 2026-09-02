"""Reusable Personal Form Profile model for owner-controlled KnowledgeVault data.

This module validates private form facts. It creates no filing, signing, identity,
credential, provider, or execution authority. Reusable signing material is forbidden;
only a non-secret SKAP reference is permitted and auto-application is always false.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any

SCHEMA="stegverse.kv.personal_form_profile/v1"
IDENTIFIER_KINDS={"TVC_UNIQUE_ID","SSN","ITIN","OTHER"}

def new_profile()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "identity":{"display_name":None,"legal_name":None,"date_of_birth":None},
        "contact":{"phones":[],"emails":[]},
        "addresses":[],
        "identifiers":[],
        "filing_defaults":{
            "organizer_name":None,
            "manager_managed":None,
            "registered_agent_name":None,
            "registered_office_address_label":None,
            "effective_on_filing":None,
            "accounting_year_close_month":None,
        },
        "signature":{"skap_ref":None,"display_name":None,"auto_apply":False},
    }

def _is_opt_string(v:Any)->bool:
    return v is None or isinstance(v,str)

def validate_profile(profile:dict[str,Any])->list[str]:
    e:list[str]=[]
    if not isinstance(profile,dict):
        return ["profile must be object"]
    required={"schema","identity","contact","addresses","identifiers","filing_defaults","signature"}
    if set(profile)!=required: e.append("profile field set invalid")
    if profile.get("schema")!=SCHEMA: e.append("schema mismatch")
    identity=profile.get("identity")
    if not isinstance(identity,dict) or set(identity)!={"display_name","legal_name","date_of_birth"}:
        e.append("identity invalid")
    else:
        for k in ("display_name","legal_name","date_of_birth"):
            if not _is_opt_string(identity.get(k)): e.append(k+" invalid")
    contact=profile.get("contact")
    if not isinstance(contact,dict) or set(contact)!={"phones","emails"}:
        e.append("contact invalid")
    elif not isinstance(contact.get("phones"),list) or not isinstance(contact.get("emails"),list):
        e.append("contact collections invalid")
    if not isinstance(profile.get("addresses"),list): e.append("addresses invalid")
    ids=profile.get("identifiers")
    if not isinstance(ids,list):
        e.append("identifiers invalid")
    else:
        for i,item in enumerate(ids):
            if not isinstance(item,dict) or set(item)!={"kind","value","label"}:
                e.append(f"identifier[{i}] shape invalid"); continue
            if item.get("kind") not in IDENTIFIER_KINDS: e.append(f"identifier[{i}] kind invalid")
            if not isinstance(item.get("value"),str) or not item["value"].strip(): e.append(f"identifier[{i}] value invalid")
            if not _is_opt_string(item.get("label")): e.append(f"identifier[{i}] label invalid")
    defaults=profile.get("filing_defaults")
    expected_defaults={"organizer_name","manager_managed","registered_agent_name","registered_office_address_label","effective_on_filing","accounting_year_close_month"}
    if not isinstance(defaults,dict) or set(defaults)!=expected_defaults:
        e.append("filing_defaults invalid")
    else:
        for k in ("organizer_name","registered_agent_name","registered_office_address_label"):
            if not _is_opt_string(defaults.get(k)): e.append(k+" invalid")
        for k in ("manager_managed","effective_on_filing"):
            if defaults.get(k) is not None and not isinstance(defaults.get(k),bool): e.append(k+" invalid")
        month=defaults.get("accounting_year_close_month")
        if month is not None and (not isinstance(month,int) or isinstance(month,bool) or not 1<=month<=12):
            e.append("accounting_year_close_month invalid")
    sig=profile.get("signature")
    if not isinstance(sig,dict) or set(sig)!={"skap_ref","display_name","auto_apply"}:
        e.append("signature invalid")
    else:
        ref=sig.get("skap_ref")
        if ref is not None and (not isinstance(ref,str) or not ref.startswith("skap://signing/") or len(ref)<=len("skap://signing/")):
            e.append("signature SKAP reference invalid")
        if not _is_opt_string(sig.get("display_name")): e.append("signature display_name invalid")
        if sig.get("auto_apply") is not False: e.append("signature auto_apply must be false")
    return e

def validated_copy(profile:dict[str,Any])->dict[str,Any]:
    errors=validate_profile(profile)
    if errors: raise ValueError("; ".join(errors))
    return deepcopy(profile)
