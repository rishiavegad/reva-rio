# Blockchain-Based Lightweight Secure Peer-to-Peer Communication Framework for Resource-Constrained IoT Networks

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Consensus](https://img.shields.io/badge/Consensus-Trust--Aware%20nPBFT-059669?style=flat)](https://github.com/)
[![Optimization](https://img.shields.io/badge/Optimizer-ATHO%20(GWO--PSO--SA)-7C3AED?style=flat)](https://github.com/)
[![Storage](https://img.shields.io/badge/Storage-DAG%20%2B%20IPFS%20(97.7%25%20Saved)-D97706?style=flat)](https://ipfs.tech/)
[![Anomaly Detection](https://img.shields.io/badge/AI--IDS-Double--DQN%20(F1=1.00)-2563EB?style=flat)](https://github.com/)

An end-to-end, reproducible research software framework and interactive telemetry dashboard designed for decentralized, resource-constrained Internet of Things (IoT) swarms. The system resolves the classical scalability and storage bottlenecks of decentralized ledgers by synthesizing:
1. **Trust-Aware nPBFT:** A Byzantine Fault Tolerant consensus protocol reducing messaging from $O(N^2)$ to $O(R^2)$ ($98.18\%$ overhead reduction at $N=50$).
2. **ATHO (Adaptive Trust-Aware Hybrid Optimizer):** A multi-objective metaheuristic synthesizing Grey Wolf Optimization (GWO), Particle Swarm Optimization (PSO), and Simulated Annealing (SA) to elect optimal validator committees while strictly upholding Byzantine safety floors ($3f+1$).
3. **Decoupled DAG-IPFS Storage:** Off-chain content addressing storing large telemetry payloads in IPFS while committing only 76-byte multihash CIDs to a Directed Acyclic Graph ledger, achieving **$97.73\% - 99.47\%$ on-chain storage savings**.
4. **Lightweight Double-DQN Anomaly Detection:** An ultra-compact neural agent ($<800$ parameters, $<4\text{ KB}$, $117\ \mu\text{s}$ latency) executing inline mitigation policies (`ALLOW`, `RATE_LIMIT`, `QUARANTINE`) with closed-loop asymmetric trust slashing.

---

## Architecture Overview

```
+---------------------------------------------------------------------------------------+
|                       Interactive Research Dashboard (React 19 + Tailwind)            |
|  - Real-time Swarm Topology                - Consensus Timeline & View Rotation       |
|  - DAG Ledger Vertex Explorer              - IPFS CID Multihash Payload Inspector     |
|  - ATHO Convergence Curves                 - Double-DQN Mitigation Matrix             |
|  - On-the-fly Multi-Vector Attack Injector - System Storage & Latency Gauges          |
+---------------------------------------------------------------------------------------+
                                           ▲
                                           │ REST / JSON-RPC
                                           ▼
+---------------------------------------------------------------------------------------+
|                       Full-Stack Express & Vite Application Server                    |
|  - /api/status                             - /api/simulation/reset                    |
|  - /api/simulation/step                    - /api/simulation/attack                   |
|  - /api/simulation/benchmarks              - Static Bundle Delivery                   |
+---------------------------------------------------------------------------------------+
                                           ▲
                                           │ Subprocess CLI Bridge
                                           ▼
+---------------------------------------------------------------------------------------+
|                         Python Core Research Simulation Engine                        |
|                                                                                       |
|  [core/crypto_primitives.py]  RFC 8032 Ed25519 (Projective Coordinates) & SHA-256     |
|  [core/trust.py]              Multi-dimensional Trust: T_i = 0.35 D + 0.45 C + 0.20 A |
|  [core/optimization.py]       ATHO Hybrid Optimizer (GWO + PSO + SA + kappa_t)        |
|  [core/npbft.py]              Trust-Aware nPBFT (Pre-prepare, Prepare, Commit, Quorum) |
|  [core/dag_ledger.py]         Directed Acyclic Graph with Topological Cycle Checking  |
|  [core/ipfs_client.py]        Unified IPFS Adapter (Kubo Daemon + In-Memory Mock)     |
|  [core/secure_channel.py]     AEAD (CTR + HMAC-SHA256) & Anti-Replay Nonce Tracking   |
|  [core/virtual_node.py]       Simulated Hardware (CPU time, RAM, Battery, Behaviors)  |
|  [core/network_simulator.py]  Gaussian Latency & Bernoulli Loss Channel Coordinator   |
|  [core/anomaly_detection.py]  Double-DQN Anomaly Detector (<800 params, 117 us)       |
+---------------------------------------------------------------------------------------+
```

---

## Directory Structure

```
├── core/                           # Python Core Research Engine
│   ├── __init__.py
│   ├── crypto_primitives.py        # RFC 8032 Ed25519 in Extended Projective Coordinates
│   ├── trust.py                    # Dynamic Bayesian Trust Engine with Asymmetric Slashing
│   ├── optimization.py             # ATHO, GWO, PSO, SA Metaheuristics & Ablation Tools
│   ├── npbft.py                    # Trust-Aware nPBFT Consensus State Machine
│   ├── dag_ledger.py               # Directed Acyclic Graph Ledger & Cumulative Weighting
│   ├── ipfs_client.py              # Kubo IPFS Adapter & In-Memory Content-Addressed Store
│   ├── secure_channel.py           # HKDF Session Derivation & Authenticated AEAD Framing
│   ├── virtual_node.py             # Virtual IoT Node with Hardware Metering & Behaviors
│   ├── network_simulator.py        # Channel Coordinator & Integrated Simulation Loop
│   ├── anomaly_detection.py        # Double-DQN Agent, Static Threshold & Centroid Baselines
│   └── api_bridge.py               # CLI / JSON-RPC Bridge for Backend Communication
├── tests/                          # Automated Unit & Integration Tests (20 Suites)
│   ├── __init__.py
│   ├── test_optimization.py        # ATHO Convergence & Constraint Compliance Tests
│   ├── test_npbft.py               # nPBFT 3-Phase Consensus & Byzantine Fault Tests
│   ├── test_dag_ipfs.py            # DAG Cycle Check, Weight Propagation & IPFS Tests
│   ├── test_simulator.py           # Virtual Swarm Sensing & Channel Dynamics Tests
│   └── test_anomaly_detection.py   # Double-DQN Backprop, Reward Matrix & Baselines
├── experiments/                    # Automated Empirical Benchmark Suite
│   ├── run_comprehensive_evaluation.py # 5 Automated Research Experiments
│   ├── EXPERIMENTAL_RESULTS.json   # Numerical Measurement Output
│   └── PERFORMANCE_EVALUATION_REPORT.md # Generated Thesis Benchmark Report
├── research/                       # Research Specifications & Mathematical Proofs
│   ├── RESEARCH_GAP_AND_LITERATURE_REVIEW.md
│   ├── SYSTEM_REQUIREMENTS_SPECIFICATION.md
│   ├── MATHEMATICAL_MODEL_SPECIFICATION.md
│   ├── DATA_SCHEMAS_AND_PROTOCOLS.json
│   └── SYSTEM_ARCHITECTURE_AND_FLOWCHARTS.md
├── docs/                           # Final Documentation & Defense Material
│   ├── FINAL_RESEARCH_REPORT.md    # Comprehensive Major Project Final Report
│   └── PRESENTATION_MATERIAL.md    # Slide-by-Slide Defense Presentation Script
├── src/                            # Frontend React Application
│   ├── App.tsx                     # Interactive Telemetry Dashboard
│   ├── main.tsx                    # Entry Point
│   └── index.css                   # Tailwind Global Directives
├── server.ts                       # Full-Stack Express Server & Vite Middleware
├── package.json                    # Dependencies & Run Scripts
├── tsconfig.json                   # TypeScript Compiler Options
└── vite.config.ts                  # Vite Configuration
```

---

## Key Experimental Results

| Metric | Traditional Baseline | Proposed System | Empirical Improvement |
| :--- | :--- | :--- | :--- |
| **Consensus Messages ($N=50$)** | 4,949 messages (Standard PBFT) | **90 messages** (Trust-Aware nPBFT) | **98.18% reduction** |
| **Consensus Latency ($N=50$)** | 930.82 ms | **59.13 ms** | **15.7× speedup** |
| **On-Chain Storage ($1,000$ txs)** | 14.28 MB (Monolithic Linear Block) | **324.22 KB** (DAG + IPFS CID) | **97.73% reduction** |
| **Off-Chain Payload Savings** | 14,374 bytes raw telemetry | **76 bytes** multihash pointer | **99.47% reduction** |
| **Optimizer Stability (Std Dev)** | 0.0064 (SA), 0.0048 (GWO) | **0.0024 (ATHO)** | **Lowest variance / most stable** |
| **Byzantine Constraint Satisfaction**| Variable | **100.0%** (Hard $3f+1$ floor) | **Zero safety violations** |
| **Anomaly Detection F1-Score** | 0.5550 (Statistical Centroid) | **1.0000 (Double-DQN)** | **Zero false alarms / 100% recall** |
| **Anomaly Inference Latency** | Heavy DNNs ($>50\text{ ms}$) | **117.57 μs** (Ultra-compact DQN) | **Feasible for MCUs ($<4\text{ KB}$)** |
| **Byzantine Attack Resilience** | Vulnerable to Equivocation & DoS | **100% Interception & Slashing** | **Zero invalid commits** |

---

## Setup and Execution Guide

### 1. Prerequisites
* Python 3.10 or higher (standard library includes all cryptographic, mathematical, and socket dependencies)
* Node.js v18 or higher with npm

### 2. Installation
Clone the repository and install frontend dependencies:
```bash
npm install
```

### 3. Running the Interactive Full-Stack Application
Start the full-stack development server running Express on port 3000 with Vite middleware:
```bash
npm run dev
```
Open your browser and navigate to:
```
http://localhost:3000
```

### 4. Running the Automated Unit & Integration Tests
Execute all 20 test suites verifying cryptography, optimization, consensus, DAG, IPFS, simulation, and RL anomaly detection:
```bash
python3 -m unittest discover tests
```

### 5. Running the Automated Scientific Evaluation Experiments
Run the full automated benchmark suite to reproduce all 5 research experiments and generate `experiments/PERFORMANCE_EVALUATION_REPORT.md`:
```bash
python3 experiments/run_comprehensive_evaluation.py
```

### 6. Command Line Simulation Interface
You can also interact directly with the Python simulation engine via the CLI bridge:
```bash
# Advance 1 simulation cycle (propose, ingest, ATHO elect, nPBFT commit, trust update)
python3 core/api_bridge.py step --txs 4

# Reset network swarm with 20 nodes and 25% malicious ratio
python3 core/api_bridge.py reset --nodes 20 --malicious 0.25 --committee 7

# Inject an on-the-fly Byzantine equivocation attack into node 3
python3 core/api_bridge.py attack --node_id iot_node_03 --attack_type EQUIVOCATION

# Run real-time optimization and anomaly benchmarks
python3 core/api_bridge.py benchmarks
```

---

## License & Attribution
Developed as an advanced engineering research project in Decentralized Systems, Byzantine Fault Tolerance, Metaheuristic Optimization, and Autonomous IoT Cybersecurity.
Licensed under the Apache-2.0 License.
