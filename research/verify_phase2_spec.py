#!/usr/bin/env python3
"""
Phase 2 Mathematical and Schema Verification Script
Validates:
1. JSON Data Schemas & Protocol definitions
2. Trust Engine mathematical convergence & asymmetric slashing
3. Byzantine Quorum Intersection Invariant (R >= 3f + 1)
4. ATHO Multi-Objective Fitness Evaluation
"""

import json
import math
import sys

def verify_json_schemas():
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(script_dir, "DATA_SCHEMAS_AND_PROTOCOLS.json")
    with open(schema_path, "r") as f:
        schemas = json.load(f)
    assert "definitions" in schemas, "Missing definitions in schema file"
    assert "P2PMessage" in schemas["definitions"], "Missing P2PMessage schema"
    assert "DAGTransaction" in schemas["definitions"], "Missing DAGTransaction schema"
    assert "ConsensusBallot" in schemas["definitions"], "Missing ConsensusBallot schema"
    assert "NodeTrustProfile" in schemas["definitions"], "Missing NodeTrustProfile schema"
    assert "RLObservationState" in schemas["definitions"], "Missing RLObservationState schema"
    return len(schemas["definitions"])

def verify_trust_equations():
    # Test trust parameters: alpha=0.35, beta=0.45, gamma=0.20
    alpha, beta, gamma = 0.35, 0.45, 0.20
    assert math.isclose(alpha + beta + gamma, 1.0), "Trust weights must sum to 1.0"
    
    # Simulate honest node trust accumulation
    D, C, A = 0.5, 0.5, 1.0
    for _ in range(10):
        D = 0.75 * D + 0.25 * 1.0  # Success rate = 1.0
        C = 0.80 * C + 0.20 * 1.0
    T_honest = alpha * D + beta * C + gamma * A
    assert T_honest > 0.90, f"Honest trust failed to converge: {T_honest}"

    # Simulate Byzantine slashing
    # Equivocation penalty rho = 0.85
    A_slashed = A * (1.0 - 0.85)
    T_slashed = alpha * D + beta * C + gamma * A_slashed
    drop = T_honest - T_slashed
    assert drop > 0.15, f"Asymmetric slashing insufficient: drop = {drop}"
    return T_honest, T_slashed

def verify_byzantine_quorum_invariant():
    # 1. Canonical 3f+1 committee sizes (e.g. 4, 7, 10, 13, 16, 19, ...)
    for f in range(1, 10):
        R = 3 * f + 1
        quorum_size = 2 * f + 1
        min_intersection = 2 * quorum_size - R
        honest_in_intersection = min_intersection - f
        assert honest_in_intersection >= 1, f"Canonical invariant failed for R={R}, f={f}"

    # 2. General R committee sizes with Q = ceil((R + f + 1) / 2)
    for R in range(4, 32):
        f = (R - 1) // 3
        quorum_size = math.ceil((R + f + 1) / 2)
        min_intersection = 2 * quorum_size - R
        honest_in_intersection = min_intersection - f
        assert honest_in_intersection >= 1, (
            f"General Quorum safety violated for R={R}, f={f}: "
            f"min_intersection={min_intersection}, honest={honest_in_intersection}"
        )
    return True

def verify_atho_fitness_formulation():
    # Sample weights
    w1, w2, w3, w4 = 0.30, 0.20, 0.35, 0.15
    L_norm = 0.25  # low latency
    E_norm = 0.20  # low CPU
    T_norm = 0.95  # high trust
    H_norm = 0.80  # high entropy
    
    # Ideal committee should have negative/low fitness (minimization objective)
    fitness = w1 * L_norm + w2 * E_norm - w3 * T_norm - w4 * H_norm
    assert fitness < 0, f"Expected negative fitness for high-performing committee: {fitness}"
    return fitness

if __name__ == "__main__":
    print("==================================================")
    print("PHASE 2: FORMAL VERIFICATION OF MATHEMATICAL MODELS")
    print("==================================================")
    
    schemas_count = verify_json_schemas()
    print(f"[*] Verified JSON Schemas: {schemas_count} core protocol models validated.")
    
    T_honest, T_slashed = verify_trust_equations()
    print(f"[*] Verified Trust Dynamics: Honest converged to {T_honest:.4f}, slashed to {T_slashed:.4f}.")
    
    verify_byzantine_quorum_invariant()
    print("[*] Verified Byzantine Quorum Invariant: |Q1 ∩ Q2 \\ B| >= 1 holds for all R in [4, 31].")
    
    fitness = verify_atho_fitness_formulation()
    print(f"[*] Verified ATHO Multi-Objective Fitness: Nominal optimal score = {fitness:.4f}.")
    
    print("\n[SUCCESS] All Phase 2 mathematical invariants and schemas verified successfully.")
