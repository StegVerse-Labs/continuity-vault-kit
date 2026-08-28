from __future__ import annotations
import hashlib, json
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
PRESETS=json.loads((ROOT/"policy/organization-security-postures.v1.json").read_text(encoding="utf-8"))

def canonical_hash(obj:dict[str,Any])->str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def materialize_posture(*,organization_id:str,posture_id:str,version:int,preset:str,effective_at:str,employee_kv_count:int,capability_tier:str,official_use_default:bool=False,constraints:list[str]|None=None)->dict[str,Any]:
    if preset not in PRESETS["presets"]: raise ValueError("UNKNOWN_PRESET")
    if capability_tier not in PRESETS["tier_rules"]: raise ValueError("UNKNOWN_CAPABILITY_TIER")
    surfaces=deepcopy(PRESETS["presets"][preset])
    tier=PRESETS["tier_rules"][capability_tier]
    # Commercial tier gates user-facing operations; posture may never elevate beyond entitlement.
    surfaces["org_replay"]=bool(surfaces["org_replay"] and tier["replay"])
    surfaces["org_reconstruction"]=bool(surfaces["org_reconstruction"] and tier["reconstruction"])
    if surfaces["org_reconstruction"] and not surfaces["org_replay"]: raise ValueError("RECONSTRUCTION_REQUIRES_REPLAY")
    return {
      "schema":"stegverse.kv.organization-security-posture/v1",
      "organization_id":organization_id,"posture_id":posture_id,"version":version,"preset":preset,"effective_at":effective_at,
      "scope":{"employee_kv_count":employee_kv_count,"official_use_default":bool(official_use_default)},
      "capability_tier":capability_tier,"surfaces":surfaces,
      "history_policy":{"retrospective_scope_change":"EXPLICIT_ONLY","historical_access_requires_explicit_decision":True},
      "constraints":list(constraints or []),"authority_effect":"NONE_POLICY_ONLY"
    }

def authorize_operation(posture:dict[str,Any],*,operation:str,actor_role:str,purpose_declared:bool,employee_consent:bool=False,clearance_ok:bool=True,compartment_ok:bool=True)->dict[str,Any]:
    s=posture["surfaces"]
    allowed=False; reason="OPERATION_NOT_ADMITTED"
    if not purpose_declared: reason="PURPOSE_REQUIRED"
    elif s.get("compartment_enforcement") and (not clearance_ok or not compartment_ok): reason="CLEARANCE_OR_COMPARTMENT_DENIED"
    elif operation=="INSPECT":
        allowed=s["admin_inspection"]!="NONE" and actor_role in {"ORG_ADMIN","SECURITY_ADMIN","AUDITOR","IT_ADMIN","INVESTIGATOR"}
        reason="ADMITTED" if allowed else "ROLE_DENIED"
    elif operation=="REPLAY":
        allowed=bool(s["org_replay"]) and actor_role in {"ORG_ADMIN","SECURITY_ADMIN","AUDITOR","INVESTIGATOR"}
        reason="ADMITTED" if allowed else "TIER_OR_ROLE_DENIED"
    elif operation=="RECONSTRUCT":
        allowed=bool(s["org_reconstruction"]) and actor_role in {"SECURITY_ADMIN","AUDITOR","INVESTIGATOR"}
        reason="ADMITTED" if allowed else "TIER_OR_ROLE_DENIED"
    elif operation=="SEARCH":
        allowed=s["cross_kv_search"]!="NONE" and actor_role in {"ORG_ADMIN","SECURITY_ADMIN","AUDITOR","IT_ADMIN","INVESTIGATOR"}
        reason="ADMITTED" if allowed else "ROLE_DENIED"
    if allowed and s.get("employee_consent_required") and not employee_consent:
        allowed=False; reason="EMPLOYEE_CONSENT_REQUIRED"
    return {"schema":"stegverse.kv.organization-access-decision/v1","operation":operation,"allowed":allowed,"reason":reason,"audit_receipt_required":True,"authority_effect":"NONE_POLICY_EVALUATION_ONLY"}

def posture_change_receipt(prior:dict[str,Any]|None,new:dict[str,Any],*,actor_ref:str,role:str,decision_ref:str,historical_scope_effect:str="NONE")->dict[str,Any]:
    prior_hash=canonical_hash(prior) if prior else None
    changed=[]
    if prior:
        keys=set(prior.get("surfaces",{}))|set(new.get("surfaces",{}))
        changed=sorted(k for k in keys if prior.get("surfaces",{}).get(k)!=new.get("surfaces",{}).get(k))
    else: changed=sorted(new.get("surfaces",{}))
    if historical_scope_effect!="NONE" and new["history_policy"]["historical_access_requires_explicit_decision"] and historical_scope_effect!="EXPLICITLY_AUTHORIZED":
        raise ValueError("HISTORICAL_SCOPE_REQUIRES_EXPLICIT_AUTHORIZATION")
    return {
      "schema":"stegverse.kv.organization-posture-change-receipt/v1","organization_id":new["organization_id"],
      "prior_posture_hash":prior_hash,"new_posture_hash":canonical_hash(new),
      "prior_version":None if prior is None else prior["version"],"new_version":new["version"],"effective_at":new["effective_at"],
      "changed_surfaces":changed,"historical_scope_effect":historical_scope_effect,
      "authorized_by":{"actor_ref":actor_ref,"role":role,"decision_ref":decision_ref},"authority_effect":"NONE_POLICY_ONLY"
    }
