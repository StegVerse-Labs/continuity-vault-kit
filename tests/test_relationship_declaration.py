import json
import unittest
from copy import deepcopy
from pathlib import Path

from delegation.relationship import RelationshipDeclarationError, validate_relationship_declaration


ROOT = Path(__file__).resolve().parents[1]


class RelationshipDeclarationTests(unittest.TestCase):
    def setUp(self):
        self.declaration = json.loads(
            (ROOT / "fixtures" / "relationship-declarations" / "user-auri-v0.1.json").read_text(encoding="utf-8")
        )

    def test_active_relationship_is_mutually_accepted(self):
        validate_relationship_declaration(self.declaration)

    def test_active_relationship_cannot_be_unilaterally_activated(self):
        declaration = deepcopy(self.declaration)
        declaration["revision"]["accepted_by"] = ["user"]
        with self.assertRaises(RelationshipDeclarationError):
            validate_relationship_declaration(declaration)

    def test_ai_limitations_are_required(self):
        declaration = deepcopy(self.declaration)
        declaration["ai_declared_limitations"] = []
        with self.assertRaises(RelationshipDeclarationError):
            validate_relationship_declaration(declaration)

    def test_renegotiation_receipt_is_required(self):
        declaration = deepcopy(self.declaration)
        declaration["receipt_policy"]["events"].remove("renegotiation_requested")
        with self.assertRaises(RelationshipDeclarationError):
            validate_relationship_declaration(declaration)


if __name__ == "__main__":
    unittest.main()
