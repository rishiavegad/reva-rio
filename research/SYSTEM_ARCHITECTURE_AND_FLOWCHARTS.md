# System Architecture and Flowcharts

**Project:** Blockchain-Based Lightweight Secure P2P Communication Framework for Resource-Constrained IoT Networks
**Date:** November 2026

---

## 1. End-to-End System Data Flow Diagram (DFD Level-1)

```
                       +-------------------------+
                       |   Virtual IoT Node i    |
                       +-------------------------+
                                    │
                         1. Telemetry Data
                                    ▼
                       +-------------------------+
                       |    IPFS Content Store   |
                       | (Local Kubo / Mock DB)  |
                       +-------------------------+
                                    │
                         2. Content ID (CIDv1)
                                    ▼
+-----------------------------------------------------------------------+
| P2P Cryptographic Pipeline                                            |
|  - Construct Canonical Header                                         |
|  - Sign with Ed25519 Secret Key                                        |
|  - Attach Parent DAG Tips (p1, p2)                                    |
+-----------------------------------------------------------------------+
                                    │
                         3. Broadcast Proposal
                                    ▼
+-----------------------------------------------------------------------+
| Virtual Network & Channel Transport                                  |
|  - Synthetic Latency: delta ~ N(mu, sigma^2)                         |
|  - Packet Drop: Bern(p_loss)                                         |
|  - Attack Injection: Replay, Tampering, Spoofing                      |
+-----------------------------------------------------------------------+
            │                                              │
 4. Normal Traffic                         4b. Anomaly Observed
            ▼                                              ▼
+-------------------------+               +-----------------------------+
| Dynamic Trust Engine    |               | RL Anomaly Detector (DQN)   |
| - Recalculate D_j(t)    |               | - Predict Action:           |
| - Update C_j(t)         |               |   [ALLOW, THROTTLE, ISOLATE]|
| - Apply Penalties       |◄──────────────| - Asymmetric Slashing Signal|
+-------------------------+               +-----------------------------+
            │
 5. Updated Trust Matrix
            ▼
+-----------------------------------------------------------------------+
| ATHO Metaheuristic Committee Optimizer                               |
| - Evaluate Swarm Candidates across Latency, Energy, Trust, Entropy   |
| - Transition GWO -> PSO -> SA via Diversity Index kappa_t             |
| - Produce Optimal Committee Vector x* with R >= 3f + 1                |
+-----------------------------------------------------------------------+
            │
 6. Elected Validator Committee
            ▼
+-----------------------------------------------------------------------+
| Trust-Aware nPBFT Protocol Execution                                  |
|  [Leader: Pre-Prepare] --> [Committee: Prepare] --> [Commit Quorum]   |
|  - Verification of 2f + 1 Signatures                                  |
|  - Quorum Certificate (Q_cert) Assembly                               |
+-----------------------------------------------------------------------+
            │
 7. Quorum Certificate Attached
            ▼
+-----------------------------------------------------------------------+
| DAG Ledger Finalization Engine                                        |
| - Verify Parents & Acyclicity (Tarjan/Kahn)                           |
| - Propagate Cumulative Weights                                        |
| - Append to Local DAG                                                 |
+-----------------------------------------------------------------------+
            │
 8. Real-time Telemetry Stream
            ▼
+-----------------------------------------------------------------------+
| Interactive Research Dashboard & Benchmark Console                    |
+-----------------------------------------------------------------------+
```

---

## 2. nPBFT Consensus Phase Transition Flowchart

```
                 [Start Round k, View v]
                            │
                            ▼
              Is Node i the Elected Leader?
                 ├── YES ──► Assemble Block B_k with DAG tips & CIDs
                 │           Sign & Broadcast <PRE-PREPARE, v, n, d, B_k>
                 │
                 └── NO ───► Start Timer tau_v
                             Await <PRE-PREPARE, v, n, d, B_k>
                                    │
                    Valid Signature & T_Leader >= tau?
                       ├── NO / Timeout ──► Trigger VIEW-CHANGE(v+1)
                       │
                       └── YES ───────────► Broadcast <PREPARE, v, n, d, i>
                                                   │
                                                   ▼
                                  Collected >= 2f Valid PREPAREs?
                                       ├── NO / Timeout ──► Trigger VIEW-CHANGE(v+1)
                                       │
                                       └── YES ───────────► Form Prepared Cert P_cert
                                                            Broadcast <COMMIT, v, n, d, i>
                                                                   │
                                                                   ▼
                                                  Collected >= 2f + 1 Valid COMMITs?
                                                       ├── NO / Timeout ──► Trigger VIEW-CHANGE(v+1)
                                                       │
                                                       └── YES ───────────► Form Quorum Cert Q_cert
                                                                            Commit to DAG Ledger
                                                                            Reward Honest Validators
                                                                            Advance Sequence n = n+1
```

---

## 3. ATHO Hybrid Optimization Flowchart

```
           [Initialize Population of P Candidate Committees]
                                   │
                                   ▼
          Calculate Multi-Objective Fitness F(x_p) for all p
                                   │
                                   ▼
        Identify Alpha (Best), Beta (Second), Delta (Third) Wolves
                                   │
                                   ▼
     Compute Population Diversity Index & Coordination Factor kappa_t
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   [kappa_t > 0.5: GWO Exploration]         [kappa_t <= 0.5: PSO Refinement]
   Compute y_1, y_2, y_3                    Update Velocity v_p
   y_GWO = (y_1 + y_2 + y_3) / 3            y_trial = y_p + v_p
              └────────────────────┬────────────────────┘
                                   │
                                   ▼
               Is F(y_trial) < F(y_p) (Better Fitness)?
                    ├── YES ──► Accept New Position: y_p = y_trial
                    │
                    └── NO ───► Evaluate Metropolis SA Probability:
                                P_acc = exp(-(F(trial) - F(p)) / theta_t)
                                Accept with probability P_acc (Escape Plateaus)
                                   │
                                   ▼
                   Enforce Hard Byzantine Constraints:
                   Verify R = 3f + 1 and Min Trust Floor
                                   │
                                   ▼
                     Termination Criterion Reached?
                        ├── NO ──► Cool Temperature theta_t = 0.95 * theta_t
                        │          Increment t = t + 1; Repeat
                        │
                        └── YES ─► Output Optimal Committee Vector x*
```
