# Systematic Literature Review and Research Gap Analysis

**Project Title:** Blockchain-Based Lightweight Secure Peer-to-Peer Communication Framework for Resource-Constrained IoT Networks Using Trust-Aware PBFT Consensus and Machine Learning-Based Anomaly Detection
**Date:** November 2026
**Field:** Distributed Ledger Technology, Byzantine Fault Tolerance, Metaheuristic Optimization, Reinforcement Learning, IoT Security

---

## 1. Context and Problem Statement

The Internet of Things (IoT) encompasses billions of interconnected sensing and actuation nodes operating under extreme constraints: microcontrollers with clock rates below 200 MHz, less than 512 KB of SRAM, low battery reserves, and unreliable, lossy wireless channels (IEEE 802.15.4, LoRaWAN, BLE, NB-IoT). Securing P2P communication, guaranteeing data integrity, and achieving Byzantine consensus across decentralized IoT swarms remains an open challenge.

Conventional Proof-of-Work (PoW) blockchains impose unsustainable energy and computational burdens. Proof-of-Stake (PoS) variants suffer from capital centralization and lack physical grounding in IoT environments. Classical Practical Byzantine Fault Tolerance (PBFT) avoids compute-intensive puzzle solving but exhibits $O(N^2)$ message complexity, rapidly saturating wireless channels when node count $N > 20$. Furthermore, PBFT assumes static validator identities and cannot inherently distinguish between honest, compromised, or intermittently faulty nodes.

---

## 2. Comprehensive Comparative Matrix of Related Approaches

| Ref ID | Method / Publication | Core Mechanism | Key Strengths | Critical Limitations in Resource-Constrained IoT | Difference from Proposed Framework |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CL-99** | Castro & Liskov (1999, 2002), *PBFT* | 3-phase consensus (Pre-prepare, Prepare, Commit) with static $3f+1$ replica group | Provable safety under asynchrony with $f < N/3$ Byzantine nodes; zero mining overhead | $O(N^2)$ communication complexity; static leader susceptible to targeted DoS; no node trust metric | Proposed **nPBFT** uses dynamic, trust-optimized committees ($R \ll N$) elected via ATHO, lowering messaging to $O(R^2)$ while strictly verifying the $3f+1$ safety threshold. |
| **PO-18** | Popov (2018), *IOTA Tangle 1.0/2.0* | Directed Acyclic Graph (DAG) with Markov Chain Monte Carlo (MCMC) tip selection | High concurrent throughput; zero transaction fees; continuous asynchronous appending | Requires client-side Proof-of-Work to attach tips; vulnerable to split/parasite attacks without central coordinator | Replaces PoW with cryptographic Ed25519 signatures and trust-weighted validation; anchors DAG tips via periodic lightweight nPBFT quorum certificates. |
| **LI-20** | Li et al. (2020), *Credit-PBFT for IoT* | Dynamic validator selection using scalar credit score derived from voting history | Reduces validator set size; rewards active participation | Greedy top-$K$ credit selection causes oligarchic centralization and validator grinding; vulnerable to collusive credit boosting | Introduces multi-dimensional trust with Bayesian decay, asymmetric Byzantine slashing, and ATHO entropy constraints that mathematically prevent monopolization. |
| **ZG-21** | Zhang et al. (2021), *GWO-PBFT Hybrid* | Standard Grey Wolf Optimizer for PBFT primary node election | Faster convergence than random leader selection | GWO easily gets trapped in local optima during high network variance; lacks adaptive escape mechanism | Combines GWO exploration with PSO social velocity and SA Metropolis escape in an integrated adaptive coordination framework (**ATHO**). |
| **AL-22** | Al-Daweri et al. (2022), *RL-based IoT IDS* | Deep Q-Network for network anomaly detection | Learns dynamic traffic patterns without fixed manual rules | Standalone detector disconnected from consensus; high false-positive rate degrades network throughput without penalty feedback | Tightly couples RL anomaly detection directly into the consensus and trust pipeline with asymmetric penalty feedback and 3-tier actions (Allow, Throttle, Quarantine). |

---

## 3. Systematic Research Gaps Identified

1. **Gap 1: The Consensus-Overhead Tradeoff in Constrained Swarms**
   Existing trust-based PBFT algorithms either sacrifice formal Byzantine fault tolerance by arbitrarily shrinking quorums without mathematical guarantees, or they maintain standard quorums but fail to bound message overhead across dense IoT meshes.
2. **Gap 2: Single-Metaheuristic Stagnation in Validator Optimization**
   Isolated metaheuristics (standalone GWO or PSO) lack the dual capability of wide exploration in multi-modal landscapes while avoiding premature convergence when network topology fluctuates dynamically.
3. **Gap 3: Ledger Bloat vs. Edge Storage Limits**
   Storing raw sensor telemetry on-chain leads to rapid disk and RAM exhaustion on edge gateways. Existing off-chain solutions (IPFS) are rarely integrated natively into DAG consensus headers with verifiable integrity checks.
4. **Gap 4: Decoupled Security Policies**
   Anomaly detection, reputation/trust modeling, and consensus voting are traditionally treated as isolated subsystems, creating vulnerability windows where malicious nodes can exploit unshared state between the IDS and the consensus engine.

---

## 4. Defensible Research Contributions of this Project

1. **Formulation of ATHO (Adaptive Trust-Aware Hybrid Optimizer):**
   An optimization framework synthesizing GWO, PSO, and SA through a continuous diversity-dependent coordination factor $\kappa_t$ that shifts seamlessly between exploration and local refinement while enforcing hard Byzantine safety constraints.
2. **Design and Verification of nPBFT (Trust-Aware PBFT Variant):**
   A mathematically proven Byzantine consensus protocol that achieves sub-$O(N^2)$ message complexity via dynamic committee partitioning while guaranteeing that at least $2f+1$ valid cryptographic signatures are required for every state transition.
3. **Decoupled DAG-IPFS Storage Architecture:**
   A dual-tier storage paradigm where large arbitrary payloads are pinned via content identifiers (CIDs) in an IPFS abstraction layer, and only fixed-size 256-byte cryptographic headers are validated and appended to the DAG.
4. **Closed-Loop RL Anomaly-to-Trust Feedback Pipeline:**
   A lightweight Deep Q-Network whose actions directly modulate the direct trust score $D_i(t)$ and anomaly discount factor $A_i(t)$, instantaneously revoking validator eligibility upon confirmed Byzantine detection.
