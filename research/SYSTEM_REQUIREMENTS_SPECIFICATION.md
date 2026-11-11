# System Requirements Specification (SRS)

**Document Version:** 1.0 (Phase 2 Formalization)
**System:** Blockchain-Based Lightweight Secure P2P Communication Framework for Resource-Constrained IoT Networks

---

## 1. System Objectives and Scope

The system provides an autonomous, decentralized, tamper-proof, and resilient communication and consensus framework for resource-constrained IoT swarms. It encompasses peer-to-peer authenticated messaging, off-chain content storage, DAG ledger sequencing, trust-weighted Byzantine consensus, metaheuristic committee optimization, and machine learning anomaly detection.

---

## 2. Functional Requirements (FR)

* **FR-1: Cryptographic Node Identity & Key Management**
  * FR-1.1: Each virtual node must generate an Ed25519 keypair for signing and an X25519 keypair for ephemeral ECDH key exchange.
  * FR-1.2: All outbound messages must include a cryptographically secure monotonic nonce ($nonce_{k} > nonce_{k-1}$) and an Ed25519 digital signature over the canonical serialization.
  * FR-1.3: Message confidentiality must be enforced using AES-128-GCM or ChaCha20-Poly1305 with session keys derived via HKDF (HMAC-based Extract-and-Expand Key Derivation).

* **FR-2: Directed Acyclic Graph (DAG) Ledger**
  * FR-2.1: Transactions must be structured as vertices in a directed acyclic graph, referencing between 1 and 3 parent transaction hashes.
  * FR-2.2: Cycle detection must be strictly enforced via incremental topological tracking. Any cyclic transaction proposal must be rejected immediately.
  * FR-2.3: The ledger engine must maintain cumulative transaction weights to establish confirmation confidence.

* **FR-3: Off-Chain Content-Addressed Storage (IPFS Integration)**
  * FR-3.1: Large application payloads ($> 256\text{ bytes}$) must not be stored on the DAG ledger.
  * FR-3.2: Payloads must be hashed using SHA-256 and wrapped in a standard multihash Content Identifier (CIDv1).
  * FR-3.3: The system must provide a unified storage adapter supporting both an operational local Kubo IPFS daemon and an in-memory high-fidelity mock store.

* **FR-4: Multi-Dimensional Dynamic Trust Management**
  * FR-4.1: The trust engine must calculate a normalized trust score $T_i(t) \in [0.0, 1.0]$ for each active node using direct communication history, consensus participation, and anomaly feedback.
  * FR-4.2: Asymmetric slashing must be applied: positive trust builds incrementally ($\Delta T^+ \le 0.05$), while confirmed Byzantine infractions inflict steep penalties ($\Delta T^- \ge 0.40$).
  * FR-4.3: Inactive or newly joined nodes must undergo probationary bounding ($T_{init} = 0.50$).

* **FR-5: Trust-Aware nPBFT Consensus Protocol**
  * FR-5.1: The consensus protocol must execute three deterministic phases: `PRE-PREPARE`, `PREPARE`, and `COMMIT`.
  * FR-5.2: For committee size $R$, the Byzantine tolerance limit is $f = \lfloor (R - 1) / 3 \rfloor$. A quorum certificate strictly requires $\ge 2f + 1$ verified cryptographic signatures.
  * FR-5.3: A deterministic view-change protocol must be triggered if the round timer expires without reaching quorum or if the current leader equivocates.

* **FR-6: ATHO Hybrid Metaheuristic Committee Optimizer**
  * FR-6.1: ATHO must optimize the validator committee allocation vector $\mathbf{x} \in \{0, 1\}^N$ across a multi-objective fitness function minimizing latency and communication overhead while maximizing average committee trust and entropy.
  * FR-6.2: The optimizer must dynamically synthesize GWO exploration, PSO velocity convergence, and SA Metropolis stochastic escape governed by the coordination parameter $\kappa_t$.
  * FR-6.3: Hard constraints ($R = 3f + 1$ and minimum node trust floor) must be verified on all candidate solutions.

* **FR-7: Reinforcement Learning Anomaly Detection**
  * FR-7.1: The RL agent must observe a continuous 6-dimensional state vector reflecting traffic rates, signature validation failures, replay attempts, latency anomalies, equivocation flags, and historical trust.
  * FR-7.2: The agent must select among three discrete mitigation policies: `ALLOW` (0), `RATE_LIMIT` (1), and `QUARANTINE` (2).
  * FR-7.3: Rewards must penalize false positives and false negatives with asymmetric loss functions.

* **FR-8: Attack Simulation & Telemetry Engine**
  * FR-8.1: The simulator must support on-the-fly injection of five attack vectors: Message Replay, Signature Tampering, Byzantine Equivocation / Double-Voting, Message Flooding (DoS), and Sybil/Collusion.
  * FR-8.2: All network events, consensus phases, DAG appends, and agent actions must be streamed to the telemetry bus.

---

## 3. Non-Functional Requirements (NFR)

* **NFR-1 (Lightweight Memory Footprint):** The core transaction ledger header must not exceed 320 bytes in memory per vertex.
* **NFR-2 (Sub-second Consensus Latency):** In a 20-node network with committee size $R=7$, 3-phase nPBFT consensus must complete within $< 350\text{ ms}$ under simulated typical wireless latency.
* **NFR-3 (Cryptographic Verification Throughput):** Ed25519 signature verification must complete in $< 1.5\text{ ms}$ per transaction on standard hardware.
* **NFR-4 (Reproducibility & Seed Control):** Every simulation run must accept a deterministic pseudo-random seed to allow exact replay and experimental verification.
* **NFR-5 (Defensive Isolation):** A quarantined node must have all inbound consensus ballots and DAG proposals discarded at the transport boundary.
* **NFR-6 (Auditability):** Every state transition in the DAG ledger must be traceable to a signed Quorum Certificate ($Q_{cert}$).

---

## 4. Threat Model & Security Assumptions

1. **Network Synchrony:** The network is weakly synchronous; message delivery delay is bounded by $\Delta$ during periods of stability.
2. **Adversary Capability:** An adversary may control up to $f$ out of $R$ elected validators ($f < R/3$) and may inject arbitrary corrupt, delayed, or conflicting ballots.
3. **Cryptographic Hardness:** Standard cryptographic primitives (SHA-256, Ed25519, Curve25519) are assumed computationally unbreakable within the simulation scope.
4. **Independent Channel Noise:** Unintentional packet loss and latency follow normal and Bernoulli distributions, distinct from malicious tampering.
