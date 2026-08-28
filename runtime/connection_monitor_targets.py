"""Compile and validate non-secret provider monitoring targets from connection assemblies."""

from __future__ import annotations

import hashlib
from typing import Any, Dict
from urllib.parse import urlparse

from runtime.connection_assembly import ConnectionAssemblyError, reject_secret_fields

SCHEMA="stegverse.kv.provider-monitor-targets/v1"
ALLOWED_SOURCE_TYPES={"provider_documentation","provider_changelog","provider_status"}
ALLOWED_CHANGE_CLASSES={"api_version","authentication","mfa_session","endpoint","deprecation","changelog","sdk_dependency","rate_limit","permission_scope","product_model","data_schema","export_format","browser_platform","service_health"}
ALLOWED_SEVERITY={"INFO","LOW","MEDIUM","HIGH","CRITICAL"}

class ConnectionMonitorTargetError(ConnectionAssemblyError):
    pass

def deterministic_target_id(provider:str,source_ref:str)->str:
    material=f"{provider}|{source_ref}".strip().lower()
    return "kvmon_"+hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

def validate_target(target:Dict[str,Any])->Dict[str,Any]:
    if not isinstance(target,dict): raise ConnectionMonitorTargetError("monitor target must be object")
    reject_secret_fields(target,"$.monitor_target")
    required=("provider","url","allowed_host","source_type","change_class","severity","breaking_on_change","affected_assumptions","source_binding_ref")
    for key in required:
        if key not in target: raise ConnectionMonitorTargetError(f"monitor target missing field: {key}")
    parsed=urlparse(str(target["url"]))
    if parsed.scheme!="https": raise ConnectionMonitorTargetError("monitor target requires HTTPS")
    if parsed.username or parsed.password: raise ConnectionMonitorTargetError("embedded URL credentials prohibited")
    if parsed.hostname!=target["allowed_host"]: raise ConnectionMonitorTargetError("monitor target allowed_host mismatch")
    if target["source_type"] not in ALLOWED_SOURCE_TYPES: raise ConnectionMonitorTargetError("unsupported source_type")
    if target["change_class"] not in ALLOWED_CHANGE_CLASSES: raise ConnectionMonitorTargetError("unsupported change_class")
    if target["severity"] not in ALLOWED_SEVERITY: raise ConnectionMonitorTargetError("unsupported severity")
    result=dict(target)
    result["target_id"]=deterministic_target_id(str(result["provider"]),str(result["source_binding_ref"]))
    return result

def compile_monitor_targets(assemblies:list[Dict[str,Any]],source_catalog:Dict[str,Dict[str,Any]])->Dict[str,Any]:
    if not isinstance(assemblies,list) or not isinstance(source_catalog,dict):
        raise ConnectionMonitorTargetError("assemblies list and source catalog object required")
    targets=[]
    for assembly in assemblies:
        reject_secret_fields(assembly,"$.assembly")
        provider=str(assembly.get("provider") or "")
        monitoring=assembly.get("monitoring") or {}
        refs=list(monitoring.get("authoritative_sources") or [])
        for source_ref in refs:
            descriptor=source_catalog.get(str(source_ref))
            if not isinstance(descriptor,dict):
                raise ConnectionMonitorTargetError(f"monitor source descriptor missing: {source_ref}")
            raw={
                "provider":provider,
                "url":descriptor.get("url"),
                "allowed_host":descriptor.get("allowed_host"),
                "source_type":descriptor.get("source_type"),
                "change_class":descriptor.get("change_class","changelog"),
                "severity":descriptor.get("severity","MEDIUM"),
                "breaking_on_change":bool(descriptor.get("breaking_on_change",False)),
                "affected_assumptions":list(descriptor.get("affected_assumptions") or []),
                "summary_on_change":str(descriptor.get("summary_on_change") or "Authoritative provider source changed."),
                "source_binding_ref":str(source_ref),
            }
            targets.append(validate_target(raw))
    dedup={target["target_id"]:target for target in targets}
    return {"schema":SCHEMA,"authority_effect":"NONE","targets":[dedup[k] for k in sorted(dedup)]}

def validate_target_document(value:Dict[str,Any])->None:
    if not isinstance(value,dict) or value.get("schema")!=SCHEMA: raise ConnectionMonitorTargetError("monitor target document schema invalid")
    if value.get("authority_effect")!="NONE": raise ConnectionMonitorTargetError("monitor target authority effect must remain NONE")
    targets=value.get("targets")
    if not isinstance(targets,list): raise ConnectionMonitorTargetError("targets must be a list")
    ids=set()
    for target in targets:
        validated=validate_target(target)
        if validated["target_id"]!=target.get("target_id"): raise ConnectionMonitorTargetError("monitor target deterministic ID mismatch")
        if target["target_id"] in ids: raise ConnectionMonitorTargetError("duplicate monitor target ID")
        ids.add(target["target_id"])
