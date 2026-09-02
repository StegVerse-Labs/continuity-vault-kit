#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime"))
from physical_recovery_evidence import reconstruct  # noqa: E402

def main()->int:
 p=argparse.ArgumentParser(description="Reconstruct a physical KV recovery evidence bundle without inventing observations.")
 p.add_argument("evidence",help="Path to observed physical recovery evidence JSON")
 args=p.parse_args()
 evidence=json.loads(Path(args.evidence).read_text())
 result=reconstruct(evidence)
 print(json.dumps(result,sort_keys=True,indent=2))
 return 0 if result["physical_recovery_proven"] else 2

if __name__=="__main__": raise SystemExit(main())
