"""
Unit and Integration Tests for Reinforcement Learning Anomaly Detection
"""

import unittest
from core.anomaly_detection import (
    DenseLayer,
    DoubleDQNAgent,
    compute_reward,
    ThresholdBaselineDetector,
    StatisticalCentroidDetector,
    benchmark_anomaly_detectors,
    train_dqn_agent
)
from core.trust import TrustEngine

class TestRLAnomalyDetection(unittest.TestCase):
    def test_dense_layer_backprop(self):
        layer = DenseLayer(in_features=4, out_features=2, activation="relu")
        x = [1.0, 0.5, -0.2, 0.8]
        out = layer.forward(x)
        self.assertEqual(len(out), 2)
        
        # Test backward update
        w_before = layer.weights[0][0]
        layer.backward(d_out=[1.0, -0.5], lr=0.1)
        w_after = layer.weights[0][0]
        self.assertNotEqual(w_before, w_after, "Weights must update via gradient descent")

    def test_asymmetric_rewards(self):
        # True Positive: Byzantine + Quarantine (Action 2) -> +10
        r_tp = compute_reward("BYZANTINE", action=2)
        self.assertEqual(r_tp, 10.0)

        # False Negative: Byzantine + Allow (Action 0) -> -15 (severe penalty)
        r_fn = compute_reward("BYZANTINE", action=0)
        self.assertEqual(r_fn, -15.0)

        # False Positive: Benign + Quarantine (Action 2) -> -12
        r_fp = compute_reward("BENIGN", action=2)
        self.assertEqual(r_fp, -12.0)

        # True Negative: Benign + Allow (Action 0) -> +1
        r_tn = compute_reward("BENIGN", action=0)
        self.assertEqual(r_tn, 1.0)

    def test_dqn_agent_training_and_inference(self):
        agent = train_dqn_agent(episodes=60, seed=42)
        
        # Benign state: [low freq, 0 sig_fail, 0 replay, normal lat, 0 equiv, high trust]
        benign_state = [0.20, 0.0, 0.0, 1.0, 0.0, 0.90]
        action_benign = agent.select_action(benign_state, eval_mode=True)
        # Should NOT quarantine benign node
        self.assertNotEqual(action_benign, 2, "DQN should not quarantine clearly benign state")

        # Byzantine state with high signature failures and low trust
        byz_state = [0.40, 0.95, 0.0, 1.2, 0.0, 0.20]
        action_byz = agent.select_action(byz_state, eval_mode=True)
        # Should trigger quarantine (action 2) or rate limit (action 1)
        self.assertIn(action_byz, (1, 2), "DQN should throttle or quarantine Byzantine node")

    def test_benchmark_all_detectors(self):
        results = benchmark_anomaly_detectors(seed=999)
        self.assertIn("Double-DQN (Proposed)", results)
        self.assertIn("Rule Threshold Baseline", results)
        self.assertIn("Statistical Centroid Baseline", results)

        print("\n[ANOMALY DETECTION BENCHMARK SUMMARY]")
        for name, metrics in results.items():
            print(f" - {name:30s}: F1 = {metrics['f1_score']:.4f}, Prec = {metrics['precision']:.4f}, "
                  f"Rec = {metrics['recall']:.4f}, FPR = {metrics['false_positive_rate']:.4f}, "
                  f"Latency = {metrics['avg_inference_latency_us']:.2f} us")

        dqn_res = results["Double-DQN (Proposed)"]
        self.assertGreater(dqn_res["recall"], 0.70, "DQN recall should be above 70%")
        self.assertLess(dqn_res["false_positive_rate"], 0.25, "DQN false positive rate should be bounded")

    def test_integration_with_trust_engine(self):
        trust_engine = TrustEngine()
        node_id = "test_adversary"
        trust_engine.record_direct_interaction(node_id, True)
        init_trust = trust_engine.get_trust(node_id)

        # RL Agent detects severe anomaly and triggers quarantine
        agent_action = 2  # QUARANTINE
        if agent_action == 2:
            trust_engine.record_infraction(node_id, "EQUIVOCATION")
            trust_engine.set_quarantine(node_id, True)

        self.assertTrue(trust_engine.records[node_id].quarantined)
        self.assertLess(trust_engine.get_trust(node_id), init_trust * 0.5)
        self.assertFalse(trust_engine.is_eligible_validator(node_id))

if __name__ == "__main__":
    unittest.main()
