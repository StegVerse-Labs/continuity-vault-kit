#!/usr/bin/env python3
"""Resolve which authoritative healthcare transparency surface applies.

Source-only evaluator. It does not infer legal compliance, execute provider I/O,
or grant transition authority.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "data" / "healthcare-authority-schema-registry.v1.json"

def resolve(entity_class: str, jurisdiction: str, evidence_purpose: str, registry: dict) -> dict:
    matches=[]
    for row in registry["authorities"]:
        if entity_class not in row["entity_classes"]: continue
        if evidence_purpose not in row["evidence_purposes"]: continue
        if row["jurisdiction"] not in {jurisdiction, "US_FEDERAL"}: continue
        matches.append(row)
    if not matches:
        return {"disposition":"FAIL_CLOSED","predicate":"APPLICABLE_AUTHORITY_RESOLVED","reason":"NO_REGISTERED_APPLICABLE_AUTHORITY","matches":[],"authority_effect":"NONE"}
    return {"disposition":"ALLOW","predicate":"APPLICABLE_AUTHORITY_RESOLVED","matches":matches,"authority_effect":"NONE"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--entity-class",required=True)
    p.add_argument("--jurisdiction",required=True)
    p.add_argument("--evidence-purpose",required=True)
    a=p.parse_args()
    registry=json.loads(REGISTRY.read_text())
    print(json.dumps(resolve(a.entity_class,a.jurisdiction,a.evidence_purpose,registry),indent=2,sort_keys=True))
if __name__=="__main__": main()
