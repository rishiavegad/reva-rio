"""
Unit and Integration Tests for Trust-Aware nPBFT Protocol Engine
"""

import unittest
from core.crypto_primitives import generate_keypair
from core.trust import TrustEngine
from core.npbft import NPBFTConsensusEngine, PBFTValidator, PBFTPhase

class TestNPBFTConsensus(unittest.TestCase):
    def setUp(self):
        self.trust_engine = TrustEngine()
        self.committee_ids = [f"val_{i:02d}" for i in range(7)]  # R=7, f=2, Quorum=5
        self.validators = {}
        for nid in self.committee_ids:
            sk, pk = generate_keypair()
            self.validators[nid] = PBFTValidator(node_id=nid, sk=sk, pk=pk)
            # Register initial trust
            self.trust_engine.record_direct_interaction(nid, True)

        self.engine = NPBFTConsensusEngine(
            committee_node_ids=self.committee_ids,
            validators=self.validators,
            trust_engine=self.trust_engine,
            view=0,
            sequence_number=1
        )
        self.block_proposal = {
            "block_height": 1,
            "tx_roots": ["0123456789abcdef"],
            "timestamp": 1770000000.0
        }

    def test_honest_consensus_round(self):
        success, qcert, metrics = self.engine.execute_round(self.block_proposal)
        self.assertTrue(success, "Honest consensus round must succeed")
        self.assertIsNotNone(qcert, "Quorum Certificate must be generated")
        self.assertEqual(len(qcert.signatures), 7, "All 7 honest nodes should sign")
        self.assertEqual(metrics["phase"], PBFTPhase.COMMITTED.value)
        self.assertEqual(self.engine.sequence_number, 2, "Sequence number should advance")

    def test_tolerable_byzantine_faults(self):
        # With R=7, f=2: System should survive 2 unresponsive nodes
        adversary = {
            "unresponsive_nodes": ["val_01", "val_02"]
        }
        success, qcert, metrics = self.engine.execute_round(self.block_proposal, adversary_config=adversary)
        self.assertTrue(success, f"Consensus must survive f={self.engine.f} faults")
        self.assertIsNotNone(qcert)
        # 5 out of 7 votes assembled, which meets quorum of 5
        self.assertEqual(len(qcert.signatures), 5)

    def test_catastrophic_byzantine_faults_triggers_view_change(self):
        # With R=7, f=2: If 3 nodes are unresponsive (exceeding f=2), quorum (5) cannot be reached
        adversary = {
            "unresponsive_nodes": ["val_01", "val_02", "val_03"]
        }
        success, qcert, metrics = self.engine.execute_round(self.block_proposal, adversary_config=adversary)
        self.assertFalse(success, "Consensus must fail when faults > f")
        self.assertIsNone(qcert)
        self.assertEqual(self.engine.phase, PBFTPhase.VIEW_CHANGE)
        self.assertEqual(self.engine.view, 1, "View must increment on failure")

    def test_equivocating_leader_slashed_and_rotated(self):
        leader = self.engine.get_leader()
        initial_trust = self.trust_engine.get_trust(leader)
        adversary = {
            "equivocating_leader": True
        }
        success, qcert, metrics = self.engine.execute_round(self.block_proposal, adversary_config=adversary)
        self.assertFalse(success, "Equivocating proposal must be rejected")
        
        # Verify leader was slashed and disqualified from future committees
        slashed_trust = self.trust_engine.get_trust(leader)
        self.assertLess(slashed_trust, initial_trust * 0.70, "Equivocating leader must receive severe trust slashing")
        self.assertFalse(self.trust_engine.is_eligible_validator(leader), "Slashed leader must lose validator eligibility")
        self.assertEqual(self.engine.view, 1, "View change must trigger to rotate leader away")

    def test_signature_forgery_rejection(self):
        adversary = {
            "invalid_signature_nodes": ["val_01"]
        }
        success, qcert, metrics = self.engine.execute_round(self.block_proposal, adversary_config=adversary)
        self.assertTrue(success, "Consensus should still succeed with remaining 6 valid votes")
        self.assertNotIn("val_01", qcert.signatures, "Forged signature must not be included in Quorum Certificate")

if __name__ == "__main__":
    unittest.main()
