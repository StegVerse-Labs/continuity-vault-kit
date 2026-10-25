"""No intra-org InTr hop between KV and the SKAP Vault (stdlib only).

InTr runs only between distinct orgs and never inside one org. The SKAP Vault sits inside KV, so KV reaching it is
the in-KV gate KV_INTERNAL_SKAP_GATE, never an InTr crossing. This guard keeps the retired KV->SKAP InTr boundary
and its predicates from coming back anywhere in the tree. Historical evidence and reports (evidence/, reports/) are
receipts and are never rewritten, so they are not scanned. The tokens are assembled at runtime so this file does
not match itself.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "evidence", "reports", "__pycache__", "node_modules"}
RETIRED = (
    "INTR_" + "KV_SKAP",
    "KV_SKAP_" + "INTR_ONLY",
    '"KV_SKAP_' + 'INTR"',
    "SKAP_VAULT_REACHABLE_ONLY_VIA_" + "INTR_FROM_KV",
    "SKAP_VAULT_REACHED_ONLY_VIA_" + "KV_INTR",
    "SKAP_RECEIPT_CHAIN_NOT_VIA_" + "KV_INTR",
    "intr-" + "kv-skap-transition",
    "through InTr " + "from inside KV",
)


def _files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not (set(path.relative_to(ROOT).parts[:-1]) & SKIP_DIRS):
            yield path


class NoIntraOrgIntrHop(unittest.TestCase):
    def test_no_retired_kv_skap_intr_token_in_the_tree(self):
        hits = []
        for path in _files():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            hits += [f"{path.relative_to(ROOT)}: {token}" for token in RETIRED if token in text]
        self.assertEqual(hits, [])

    def test_double_interlock_topology_has_one_intr_boundary(self):
        contract = json.loads((ROOT / "specs/skap-vault-double-interlock.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["canonical_topology"], ["DEVICE", "INTR_DEVICE_KV", "KV", "SKAP_VAULT"])
        self.assertEqual([b for b in contract["canonical_topology"] if b.startswith("INTR_")], ["INTR_DEVICE_KV"])
        self.assertEqual(contract["boundaries"]["kv_skap"]["connector"], "KV_INTERNAL_SKAP_GATE")
        self.assertIs(contract["boundaries"]["kv_skap"]["intr_hop"], False)

    def test_layer2_gate_is_the_in_kv_gate(self):
        from runtime import kv_skap_layer2, kv_skap_vault
        self.assertEqual(kv_skap_layer2.LAYER2_BOUNDARY, "KV_INTERNAL_SKAP_GATE")
        self.assertEqual(kv_skap_layer2.LAYER1_BOUNDARY, "INTR_DEVICE_KV")
        self.assertIn("SKAP_VAULT_REACHABLE_ONLY_FROM_INSIDE_KV", kv_skap_vault.PREDICATES)
        self.assertIn("SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT", kv_skap_vault.PREDICATES)
        self.assertIn("KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE", kv_skap_vault.PREDICATES)


if __name__ == "__main__":
    unittest.main()
