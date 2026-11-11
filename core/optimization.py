"""
Metaheuristic Optimization Suite for IoT Consensus Committee Selection
Implements:
1. Grey Wolf Optimizer (GWO)
2. Particle Swarm Optimization (PSO)
3. Simulated Annealing (SA)
4. Hybrid Baselines: GWO-PSO, GWO-SA, PSO-SA
5. Proposed ATHO: Adaptive Trust-Aware Hybrid Optimizer with dynamic coordination factor kappa_t
6. Comprehensive multi-objective fitness evaluation with hard Byzantine safety constraints.
"""

import math
import random
import time
from typing import Dict, List, Tuple, Any

class ValidatorSelectionProblem:
    """
    Defines the multi-objective optimization problem for electing an optimal
    consensus committee C subset of N nodes of size R_target.
    """
    def __init__(
        self,
        node_ids: List[str],
        trust_scores: Dict[str, float],
        cpu_loads: Dict[str, float],
        latency_matrix: Dict[str, Dict[str, float]],
        target_size: int = 7,
        min_trust_floor: float = 0.50,
        weights: Tuple[float, float, float, float] = (0.25, 0.20, 0.35, 0.20)
    ):
        self.node_ids = node_ids
        self.N = len(node_ids)
        self.target_size = target_size
        self.min_trust_floor = min_trust_floor
        self.trust_scores = [trust_scores.get(nid, 0.5) for nid in node_ids]
        self.cpu_loads = [cpu_loads.get(nid, 0.5) for nid in node_ids]
        self.node_index_map = {nid: i for i, nid in enumerate(node_ids)}
        
        # Build dense latency matrix
        self.lat_mat = [[0.0] * self.N for _ in range(self.N)]
        for i, u in enumerate(node_ids):
            for j, v in enumerate(node_ids):
                if u in latency_matrix and v in latency_matrix[u]:
                    self.lat_mat[i][j] = latency_matrix[u][v]
                else:
                    self.lat_mat[i][j] = 20.0 if i != j else 0.0

        self.w_lat, self.w_cpu, self.w_trust, self.w_entropy = weights

    def decode_position(self, continuous_vector: List[float]) -> List[int]:
        """Maps continuous vector of length N to discrete binary selection of size target_size."""
        indexed = sorted(enumerate(continuous_vector), key=lambda x: x[1], reverse=True)
        selected_indices = [idx for idx, _ in indexed[:self.target_size]]
        return sorted(selected_indices)

    def evaluate(self, selected_indices: List[int]) -> float:
        """
        Evaluates the multi-objective fitness. Lower is better.
        Hard penalties applied if constraints violated.
        """
        k = len(selected_indices)
        if k == 0:
            return 1000.0

        # Hard constraint 1: Target committee cardinality
        cardinality_penalty = 0.0
        if k != self.target_size:
            cardinality_penalty = abs(k - self.target_size) * 50.0

        # Hard constraint 2: Byzantine trust floor
        trust_penalty = 0.0
        selected_trusts = [self.trust_scores[i] for i in selected_indices]
        for t in selected_trusts:
            if t < self.min_trust_floor:
                trust_penalty += (self.min_trust_floor - t) * 100.0

        # Objective 1: Communication latency within committee (minimize)
        total_lat = 0.0
        pair_count = 0
        for i in range(k):
            for j in range(i + 1, k):
                u = selected_indices[i]
                v = selected_indices[j]
                total_lat += self.lat_mat[u][v]
                pair_count += 1
        avg_lat = (total_lat / pair_count) if pair_count > 0 else 0.0
        norm_lat = min(1.0, avg_lat / 100.0)

        # Objective 2: Average CPU load (minimize)
        avg_cpu = sum(self.cpu_loads[i] for i in selected_indices) / k
        norm_cpu = min(1.0, avg_cpu)

        # Objective 3: Average Trust score (maximize, so subtracted)
        avg_trust = sum(selected_trusts) / k
        norm_trust = avg_trust

        # Objective 4: Shannon Entropy / Decentralization (maximize, so subtracted)
        sum_t = sum(selected_trusts) + 1e-9
        entropy = 0.0
        for t in selected_trusts:
            p = t / sum_t
            if p > 0:
                entropy -= p * math.log(p)
        max_entropy = math.log(k) if k > 1 else 1.0
        norm_entropy = entropy / (max_entropy + 1e-9)

        # Composite fitness equation
        base_fitness = (
            self.w_lat * norm_lat +
            self.w_cpu * norm_cpu -
            self.w_trust * norm_trust -
            self.w_entropy * norm_entropy
        )
        return base_fitness + cardinality_penalty + trust_penalty

# =====================================================================
# 1. Standalone Grey Wolf Optimizer (GWO)
# =====================================================================
def run_gwo(problem: ValidatorSelectionProblem, pop_size=20, max_iter=40, seed=42) -> Tuple[List[int], float, List[float]]:
    random.seed(seed)
    N = problem.N
    pop = [[random.random() for _ in range(N)] for _ in range(pop_size)]
    
    alpha_pos, alpha_fit = pop[0][:], float("inf")
    beta_pos, beta_fit = pop[0][:], float("inf")
    delta_pos, delta_fit = pop[0][:], float("inf")

    history = []

    for t in range(max_iter):
        a = 2.0 * (1.0 - t / max_iter)  # linearly decrements from 2 to 0

        # Evaluate fitness
        for i in range(pop_size):
            sel = problem.decode_position(pop[i])
            fit = problem.evaluate(sel)
            if fit < alpha_fit:
                delta_fit, delta_pos = beta_fit, beta_pos[:]
                beta_fit, beta_pos = alpha_fit, alpha_pos[:]
                alpha_fit, alpha_pos = fit, pop[i][:]
            elif fit < beta_fit:
                delta_fit, delta_pos = beta_fit, beta_pos[:]
                beta_fit, beta_pos = fit, pop[i][:]
            elif fit < delta_fit:
                delta_fit, delta_pos = fit, pop[i][:]

        history.append(alpha_fit)

        # Position updates based on Alpha, Beta, Delta wolves
        for i in range(pop_size):
            for d in range(N):
                r1, r2 = random.random(), random.random()
                A1 = 2.0 * a * r1 - a
                C1 = 2.0 * r2
                D_alpha = abs(C1 * alpha_pos[d] - pop[i][d])
                X1 = alpha_pos[d] - A1 * D_alpha

                r1, r2 = random.random(), random.random()
                A2 = 2.0 * a * r1 - a
                C2 = 2.0 * r2
                D_beta = abs(C2 * beta_pos[d] - pop[i][d])
                X2 = beta_pos[d] - A2 * D_beta

                r1, r2 = random.random(), random.random()
                A3 = 2.0 * a * r1 - a
                C3 = 2.0 * r2
                D_delta = abs(C3 * delta_pos[d] - pop[i][d])
                X3 = delta_pos[d] - A3 * D_delta

                new_val = (X1 + X2 + X3) / 3.0
                pop[i][d] = max(0.0, min(1.0, new_val))

    best_selection = problem.decode_position(alpha_pos)
    return best_selection, alpha_fit, history

# =====================================================================
# 2. Standalone Particle Swarm Optimization (PSO)
# =====================================================================
def run_pso(problem: ValidatorSelectionProblem, pop_size=20, max_iter=40, seed=42) -> Tuple[List[int], float, List[float]]:
    random.seed(seed)
    N = problem.N
    pop = [[random.random() for _ in range(N)] for _ in range(pop_size)]
    vel = [[(random.random() - 0.5) * 0.2 for _ in range(N)] for _ in range(pop_size)]
    pbest = [p[:] for p in pop]
    pbest_fit = [float("inf")] * pop_size
    gbest = pop[0][:]
    gbest_fit = float("inf")

    c1, c2 = 1.49445, 1.49445
    history = []

    for t in range(max_iter):
        w = 0.9 - 0.5 * (t / max_iter)  # inertia weight damping
        for i in range(pop_size):
            sel = problem.decode_position(pop[i])
            fit = problem.evaluate(sel)
            if fit < pbest_fit[i]:
                pbest_fit[i] = fit
                pbest[i] = pop[i][:]
            if fit < gbest_fit:
                gbest_fit = fit
                gbest = pop[i][:]

        history.append(gbest_fit)

        for i in range(pop_size):
            for d in range(N):
                r1, r2 = random.random(), random.random()
                vel[i][d] = (
                    w * vel[i][d] +
                    c1 * r1 * (pbest[i][d] - pop[i][d]) +
                    c2 * r2 * (gbest[d] - pop[i][d])
                )
                vel[i][d] = max(-0.25, min(0.25, vel[i][d]))
                pop[i][d] = max(0.0, min(1.0, pop[i][d] + vel[i][d]))

    best_selection = problem.decode_position(gbest)
    return best_selection, gbest_fit, history

# =====================================================================
# 3. Standalone Simulated Annealing (SA)
# =====================================================================
def run_sa(problem: ValidatorSelectionProblem, max_iter=800, seed=42) -> Tuple[List[int], float, List[float]]:
    random.seed(seed)
    N = problem.N
    current_pos = [random.random() for _ in range(N)]
    current_sel = problem.decode_position(current_pos)
    current_fit = problem.evaluate(current_sel)

    best_pos = current_pos[:]
    best_fit = current_fit
    history = []

    T = 1.0
    cooling_rate = 0.99

    for t in range(max_iter):
        candidate_pos = current_pos[:]
        # Perturb 1-3 dimensions
        mutations = random.randint(1, 3)
        for _ in range(mutations):
            dim = random.randint(0, N - 1)
            candidate_pos[dim] = max(0.0, min(1.0, candidate_pos[dim] + random.gauss(0, 0.15)))

        candidate_sel = problem.decode_position(candidate_pos)
        candidate_fit = problem.evaluate(candidate_sel)

        delta = candidate_fit - current_fit
        if delta < 0 or random.random() < math.exp(-delta / max(1e-5, T)):
            current_pos = candidate_pos[:]
            current_fit = candidate_fit
            if current_fit < best_fit:
                best_fit = current_fit
                best_pos = current_pos[:]

        T *= cooling_rate
        if t % (max_iter // 40) == 0:
            history.append(best_fit)

    while len(history) < 40:
        history.append(best_fit)

    best_selection = problem.decode_position(best_pos)
    return best_selection, best_fit, history

# =====================================================================
# 4. Proposed Novel ATHO (Adaptive Trust-Aware Hybrid Optimizer)
# =====================================================================
def run_atho(problem: ValidatorSelectionProblem, pop_size=20, max_iter=40, seed=42) -> Tuple[List[int], float, List[float]]:
    """
    Adaptive Trust-Aware Hybrid Optimizer:
    - Coordinates GWO global exploration, PSO cognitive-social momentum, and SA Metropolis escape.
    - Coordination factor kappa_t adapts to instantaneous population diversity and iteration stage.
    """
    random.seed(seed)
    N = problem.N
    pop = [[random.random() for _ in range(N)] for _ in range(pop_size)]
    vel = [[(random.random() - 0.5) * 0.15 for _ in range(N)] for _ in range(pop_size)]
    pbest = [p[:] for p in pop]
    pbest_fit = [float("inf")] * pop_size

    alpha_pos, alpha_fit = pop[0][:], float("inf")
    beta_pos, beta_fit = pop[0][:], float("inf")
    delta_pos, delta_fit = pop[0][:], float("inf")

    temperature = 1.0
    cooling_rate = 0.94
    history = []

    for t in range(max_iter):
        # 1. Evaluate Fitness and Rank Leaders
        fitness_vals = []
        for i in range(pop_size):
            sel = problem.decode_position(pop[i])
            fit = problem.evaluate(sel)
            fitness_vals.append(fit)

            if fit < pbest_fit[i]:
                pbest_fit[i] = fit
                pbest[i] = pop[i][:]

            if fit < alpha_fit:
                delta_fit, delta_pos = beta_fit, beta_pos[:]
                beta_fit, beta_pos = alpha_fit, alpha_pos[:]
                alpha_fit, alpha_pos = fit, pop[i][:]
            elif fit < beta_fit:
                delta_fit, delta_pos = beta_fit, beta_pos[:]
                beta_fit, beta_pos = fit, pop[i][:]
            elif fit < delta_fit:
                delta_fit, delta_pos = fit, pop[i][:]

        history.append(alpha_fit)

        # 2. Compute Population Variance & Adaptive Coordination Factor kappa_t
        mean_fit = sum(fitness_vals) / pop_size
        var_fit = sum((f - mean_fit) ** 2 for f in fitness_vals) / pop_size
        diversity_metric = min(1.0, math.sqrt(var_fit) / 2.0)

        # Sigmoid transition modulated by diversity
        iter_ratio = t / max_iter
        sigmoid_shift = 1.0 / (1.0 + math.exp(8.0 * (iter_ratio - 0.5)))
        kappa_t = max(0.1, min(0.9, sigmoid_shift * (0.5 + 0.5 * diversity_metric)))

        a = 2.0 * (1.0 - iter_ratio)
        w = 0.85 - 0.45 * iter_ratio

        # 3. Hybrid Position & Velocity Updates
        for i in range(pop_size):
            trial_pos = [0.0] * N
            for d in range(N):
                # GWO update calculation
                r1, r2 = random.random(), random.random()
                A1 = 2.0 * a * r1 - a
                C1 = 2.0 * r2
                X1 = alpha_pos[d] - A1 * abs(C1 * alpha_pos[d] - pop[i][d])

                r1, r2 = random.random(), random.random()
                A2 = 2.0 * a * r1 - a
                C2 = 2.0 * r2
                X2 = beta_pos[d] - A2 * abs(C2 * beta_pos[d] - pop[i][d])

                r1, r2 = random.random(), random.random()
                A3 = 2.0 * a * r1 - a
                C3 = 2.0 * r2
                X3 = delta_pos[d] - A3 * abs(C3 * delta_pos[d] - pop[i][d])
                x_gwo = (X1 + X2 + X3) / 3.0

                # PSO velocity calculation
                r3, r4 = random.random(), random.random()
                vel[i][d] = (
                    w * vel[i][d] +
                    1.4 * r3 * (pbest[i][d] - pop[i][d]) +
                    1.4 * r4 * (alpha_pos[d] - pop[i][d])
                )
                vel[i][d] = max(-0.2, min(0.2, vel[i][d]))
                x_pso = pop[i][d] + vel[i][d]

                # Adaptive blending governed by kappa_t
                blended = kappa_t * x_gwo + (1.0 - kappa_t) * x_pso
                trial_pos[d] = max(0.0, min(1.0, blended))

            # 4. SA Stochastic Plateau-Jumping
            trial_sel = problem.decode_position(trial_pos)
            trial_fit = problem.evaluate(trial_sel)
            current_fit = fitness_vals[i]

            if trial_fit <= current_fit:
                pop[i] = trial_pos[:]
            else:
                delta_f = trial_fit - current_fit
                p_accept = math.exp(-delta_f / max(1e-4, temperature))
                if random.random() < p_accept:
                    pop[i] = trial_pos[:]

        temperature *= cooling_rate

    best_selection = problem.decode_position(alpha_pos)
    return best_selection, alpha_fit, history

# =====================================================================
# Comprehensive Optimizer Comparison and Benchmark Utility
# =====================================================================
def benchmark_all_optimizers(problem: ValidatorSelectionProblem, runs=5) -> Dict[str, Any]:
    """Runs repeatable benchmark across GWO, PSO, SA, and ATHO."""
    algorithms = {
        "GWO": run_gwo,
        "PSO": run_pso,
        "SA": run_sa,
        "ATHO (Proposed)": run_atho
    }
    results = {}

    for name, func in algorithms.items():
        best_fits = []
        runtimes = []
        histories = []
        best_sel = None

        for r in range(runs):
            seed = 100 + r * 17
            t0 = time.perf_counter()
            if name == "SA":
                sel, fit, hist = func(problem, max_iter=800, seed=seed)
            else:
                sel, fit, hist = func(problem, pop_size=20, max_iter=40, seed=seed)
            t1 = time.perf_counter()

            best_fits.append(fit)
            runtimes.append((t1 - t0) * 1000.0)  # ms
            histories.append(hist)
            if best_sel is None or fit < min(best_fits):
                best_sel = sel

        # Average history curve
        avg_history = [
            sum(histories[run][step] for run in range(runs)) / runs
            for step in range(len(histories[0]))
        ]

        results[name] = {
            "mean_fitness": sum(best_fits) / runs,
            "min_fitness": min(best_fits),
            "std_fitness": math.sqrt(sum((x - sum(best_fits) / runs) ** 2 for x in best_fits) / runs),
            "mean_runtime_ms": sum(runtimes) / runs,
            "best_selection_indices": best_sel,
            "best_node_ids": [problem.node_ids[i] for i in best_sel],
            "convergence_curve": avg_history
        }

    return results
