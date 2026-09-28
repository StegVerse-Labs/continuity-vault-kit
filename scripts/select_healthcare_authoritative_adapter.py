#!/usr/bin/env python3
"""Select an authoritative healthcare adapter and preserve governing source evidence."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from scripts.resolve_healthcare_applicability import resolve, REGISTRY

ADAPTERS={
 "CMS-HPT-2026":"CMS_HPT_MACHINE_READABLE_FILE",
 "CMS-TIC-MRF-2.0":"CMS_TIC_V2_MACHINE_READABLE_FILE",
 "CMS-TIC-COST-COMPARISON":"MEMBER_AUTHORIZED_COST_COMPARISON",
}

def preserve_source(source: bytes, content_type: str, source_locator: str) -> dict:
    return {
      "source_locator":source_locator,
      "content_type":content_type,
      "source_sha256":hashlib.sha256(source).hexdigest(),
      "source_size_bytes":len(source),
      "raw_source_preserved":True,
      "governing_fields_renamed":False,
    }

def select_and_preserve(entity_class,jurisdiction,evidence_purpose,source,content_type,source_locator,registry):
    applicable=resolve(entity_class,jurisdiction,evidence_purpose,registry)
    if applicable["disposition"]!="ALLOW":
        return applicable
    if len(applicable["matches"])!=1:
        return {"disposition":"FAIL_CLOSED","predicate":"AUTHORITATIVE_ADAPTER_UNAMBIGUOUS","reason":"MULTIPLE_APPLICABLE_AUTHORITIES","matches":applicable["matches"],"authority_effect":"NONE"}
    authority=applicable["matches"][0]
    adapter=ADAPTERS.get(authority["authority_id"])
    if not adapter:
        return {"disposition":"FAIL_CLOSED","predicate":"AUTHORITATIVE_ADAPTER_RESOLVED","reason":"NO_ADAPTER_FOR_APPLICABLE_AUTHORITY","authority":authority,"authority_effect":"NONE"}
    evidence=preserve_source(source,content_type,source_locator)
    return {"disposition":"ALLOW","predicate":"AUTHORITATIVE_SOURCE_PRESERVED","authority":authority,"adapter_id":adapter,"evidence":evidence,"authority_effect":"NONE"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--entity-class",required=True); p.add_argument("--jurisdiction",required=True); p.add_argument("--evidence-purpose",required=True)
    p.add_argument("--source-file",required=True); p.add_argument("--content-type",required=True); p.add_argument("--source-locator",required=True)
    a=p.parse_args(); registry=json.loads(REGISTRY.read_text()); source=Path(a.source_file).read_bytes()
    print(json.dumps(select_and_preserve(a.entity_class,a.jurisdiction,a.evidence_purpose,source,a.content_type,a.source_locator,registry),indent=2,sort_keys=True))
if __name__=="__main__": main()
