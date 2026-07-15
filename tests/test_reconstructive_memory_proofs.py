import unittest

from reconstructive_memory.core import AuthorizationContext
from reconstructive_memory.proofs import CallableProofVerifier, require_dual_proof


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.auth = AuthorizationContext(
            pair_id="sha256:pair",
            user_proof="signed-user-proof",
            entity_proof="signed-entity-proof",
            policy_ref="policy://memory/v1",
            relationship_epoch=1,
            capability_id="cap-1",
        )

    def test_dual_proof_succeeds_only_when_both_verify(self):
        verifier = CallableProofVerifier(lambda auth: True, lambda auth: True)
        require_dual_proof(self.auth, verifier)

    def test_user_failure_is_rejected(self):
        verifier = CallableProofVerifier(lambda auth: False, lambda auth: True)
        with self.assertRaisesRegex(PermissionError, "StegID"):
            require_dual_proof(self.auth, verifier)

    def test_entity_failure_is_rejected(self):
        verifier = CallableProofVerifier(lambda auth: True, lambda auth: False)
        with self.assertRaisesRegex(PermissionError, "AI-entity"):
            require_dual_proof(self.auth, verifier)


if __name__ == "__main__":
    unittest.main()
