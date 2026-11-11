"""
Unit and Integration Tests for Optimization Suite (GWO, PSO, SA, and ATHO)
"""

import unittest
from core.optimization import (
    ValidatorSelectionProblem,
    run_gwo,
    run_pso,
    run_sa,
    run_atho,
    benchmark_all_optimizers
)

class TestOptimizationSuite(unittest.TestCase):
    def setUp(self):
        self.node_ids = [f"node_{i:02d}" for i in range(20)]
        # Nodes 0-14 have decent to high trust, 15-19 have poor trust (< 0.40)
        self.trust_scores = {
            f"node_{i:02d}": (0.75 + (i % 5) * 0.04 if i < 15 else 0.25)
            for i in range(20)
        }
        self.cpu_loads = {
            f"node_{i:02d}": (0.15 + (i % 4) * 0.10)
            for i in range(20)
        }
        # Synthetic latency matrix
        self.lat_mat = {}
        for u in self.node_ids:
            self.lat_mat[u] = {}
            for v in self.node_ids:
                if u == v:
                    self.lat_mat[u][v] = 0.0
                else:
                    self.lat_mat[u][v] = 10.0 + abs(int(u[-2:]) - int(v[-2:])) * 2.0

        self.problem = ValidatorSelectionProblem(
            node_ids=self.node_ids,
            trust_scores=self.trust_scores,
            cpu_loads=self.cpu_loads,
            latency_matrix=self.lat_mat,
            target_size=7,
            min_trust_floor=0.50
        )

    def test_atho_convergence_and_constraints(self):
        selection, best_fit, history = run_atho(self.problem, pop_size=15, max_iter=30, seed=42)
        
        # Verify cardinality
        self.assertEqual(len(selection), 7, "ATHO must select exactly target_size=7 validators")
        
        # Verify Byzantine trust floor constraint
        for idx in selection:
            nid = self.node_ids[idx]
            self.assertGreaterEqual(
                self.trust_scores[nid], 0.50,
                f"Selected validator {nid} violated Byzantine trust floor (trust={self.trust_scores[nid]})"
            )
        
        # Verify convergence monotonicity of best history
        self.assertLessEqual(history[-1], history[0], "Fitness should improve or stay equal over iterations")

    def test_benchmark_all_optimizers(self):
        results = benchmark_all_optimizers(self.problem, runs=3)
        self.assertIn("ATHO (Proposed)", results)
        self.assertIn("GWO", results)
        self.assertIn("PSO", results)
        self.assertIn("SA", results)

        atho_mean = results["ATHO (Proposed)"]["mean_fitness"]
        print(f"\n[OPTIMIZATION BENCHMARK SUMMARY]")
        for algo, res in results.items():
            print(f" - {algo:16s}: Mean Fit = {res['mean_fitness']:.4f}, Min = {res['min_fitness']:.4f}, Runtime = {res['mean_runtime_ms']:.2f} ms")

        # Confirm ATHO achieves valid competitive fitness
        self.assertLess(atho_mean, 0.0, "ATHO mean fitness should be negative (indicating healthy objective satisfaction)")

if __name__ == "__main__":
    unittest.main()
