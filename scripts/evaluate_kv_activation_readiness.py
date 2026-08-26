#!/usr/bin/env python3
"""Evaluate KV module/service readiness without activating anything."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "specs" / "kv-device-backed-capability-registry.v1.json"
SERVICES = ROOT / "specs" / "kv-personal-services-registry.v1.json"
FACTS = ROOT / "specs" / "kv-activation-readiness-facts.v1.json"
POLICY = ROOT / "specs" / "kv-module-activation-policy.v1.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def missing_requirements(requirements, facts):
    return [name for name in requirements if facts.get(name) is not True]

def evaluate():
    modules = load(MODULES)["modules"]
    services = load(SERVICES)["services"]
    facts = load(FACTS)
    policy = {x["module_id"]: x for x in load(POLICY)["modules"]}

    entries = []
    for module in modules:
        p = policy[module["module_id"]]
        blockers = missing_requirements(p["governed_requires"], facts)
        entries.append({
            "entry_type":"MODULE",
            "entry_id":module["module_id"],
            "install_state":module["install_state"],
            "local_materialization":p["local_materialization"],
            "governed_action_readiness":"READY_FOR_GOVERNED_ACTION" if not blockers else "BLOCKED",
            "governed_blockers":blockers,
            "activation_performed":False,
            "authority_effect":"NONE",
        })

    for service in services:
        cls = service["service_class"]
        provider = service["provider_dependency"]
        if cls == "KV_NATIVE":
            local = "READY_FOR_LOCAL_MATERIALIZATION"
        elif cls == "KV_DEVICE":
            local = "READY_FOR_DEVICE_MATERIALIZATION"
        else:
            local = "READY_FOR_LOCAL_UI"

        governed_requires = ["production_interlock_runtime_activated"]
        if cls == "KV_DEVICE_PROVIDER" or provider != "NONE":
            governed_requires.append("provider_session_evidence_observed")
        blockers = missing_requirements(governed_requires, facts)
        entries.append({
            "entry_type":"SERVICE",
            "entry_id":service["service_id"],
            "service_class":cls,
            "install_state":service["install_state"],
            "local_materialization":local,
            "governed_action_readiness":"READY_FOR_GOVERNED_ACTION" if not blockers else "BLOCKED",
            "governed_blockers":blockers,
            "activation_performed":False,
            "authority_effect":"NONE",
        })

    snapshot = {
        "schema":"stegverse.kv.activation-readiness-snapshot/v1",
        "facts_observed_at":facts["observed_at"],
        "entry_count":len(entries),
        "module_count":sum(1 for e in entries if e["entry_type"]=="MODULE"),
        "service_count":sum(1 for e in entries if e["entry_type"]=="SERVICE"),
        "baseline_intr_complete":facts["baseline_intr_rc01_rc05_complete"],
        "production_interlock_runtime_activated":facts["production_interlock_runtime_activated"],
        "activation_performed":False,
        "authority_effect":"NONE",
        "summary":{
            "local_ready":sum(1 for e in entries if e["local_materialization"].startswith("READY")),
            "local_blocked":sum(1 for e in entries if not e["local_materialization"].startswith("READY")),
            "governed_ready":sum(1 for e in entries if e["governed_action_readiness"]=="READY_FOR_GOVERNED_ACTION"),
            "governed_blocked":sum(1 for e in entries if e["governed_action_readiness"]=="BLOCKED"),
        },
        "entries":entries,
    }
    return snapshot

def main():
    snapshot = evaluate()
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
