# Mathematical Model and Algorithmic Specification

**System:** Blockchain-Based Lightweight Secure P2P Communication Framework for Resource-Constrained IoT Networks
**Date:** November 2026

---

## 1. Dynamic Trust Management Model

Let the set of all virtual IoT nodes be $\mathcal{N} = \{n_1, n_2, \dots, n_N\}$. At discrete simulation time $t$, each node $i$ maintains an empirical trust vector for every peer $j \in \mathcal{N} \setminus \{i\}$:

$$T_j(t) = \alpha \cdot D_j(t) + \beta \cdot C_j(t) + \gamma \cdot A_j(t)$$

where $\alpha + \beta + \gamma = 1$ and $\alpha, \beta, \gamma \ge 0$. Standard default hyperparameters: $\alpha = 0.35, \beta = 0.45, \gamma = 0.20$.

### 1.1 Direct Communication Trust $D_j(t)$
Direct trust evaluates low-level transport compliance (valid signatures, correct nonces, message arrival within timeout):

$$D_j(t) = (1 - \lambda_d) \cdot D_j(t-1) + \lambda_d \cdot \left( \frac{S_j(t) - F_j(t)}{S_j(t) + F_j(t) + \epsilon} \right)$$

* $S_j(t)$: Count of valid, non-replayed, authenticated messages received from node $j$ in window $\Delta t$.
* $F_j(t)$: Count of corrupted, delayed, or malformed packets from node $j$.
* $\lambda_d \in (0, 1]$: Exponential decay parameter reflecting temporal recency ($\lambda_d = 0.25$).
* The term is scaled from $[-1, 1]$ to $[0, 1]$ via normalization $D_j(t) \leftarrow \frac{D_j(t) + 1}{2}$.

### 1.2 Consensus Participation Trust $C_j(t)$
Consensus trust measures honest adherence to nPBFT protocol phases:

$$C_j(t) = \frac{\sum_{r=1}^K \mathbb{I}_{valid}(j, r) \cdot e^{-\mu (t - t_r)}}{\sum_{r=1}^K \mathbb{I}_{elected}(j, r) \cdot e^{-\mu (t - t_r)} + \epsilon_{prior}}$$

* $\mathbb{I}_{elected}(j, r) = 1$ if node $j$ was an elected validator in round $r$, else $0$.
* $\mathbb{I}_{valid}(j, r) = 1$ if node $j$ cast timely, non-equivocating Prepare/Commit votes in round $r$.
* $\mu$: Consensus recency half-life parameter ($\mu = 0.05$).

### 1.3 Asymmetric Byzantine Slashing & Anomaly Factor $A_j(t)$
Trust builds slowly via honest participation but drops catastrophically upon verified malicious acts:

$$A_j(t) = A_j(t-1) \cdot \prod_{k \in \mathcal{E}_j(t)} (1 - \rho_k)$$

* $\mathcal{E}_j(t)$: Set of security infractions detected by the RL agent or consensus verifier at time $t$.
* Penalty weights:
  * Signature forgery / invalid crypto: $\rho_{forgery} = 0.60$
  * Replay attack: $\rho_{replay} = 0.45$
  * Consensus equivocation (double-voting): $\rho_{equiv} = 0.85$
  * Flood DoS: $\rho_{flood} = 0.40$

---

## 2. ATHO: Adaptive Trust-Aware Hybrid Optimizer

### 2.1 Optimization Formulation

**Decision Vector:** Binary selection $\mathbf{x} = [x_1, x_2, \dots, x_N]^T \in \{0, 1\}^N$, where $x_i = 1 \iff$ node $i$ is elected to the consensus committee $\mathcal{C}$.

**Fitness Function (to minimize):**
$$\min_{\mathbf{x}} \mathcal{F}(\mathbf{x}) = w_1 \cdot \frac{\mathcal{L}(\mathbf{x})}{\mathcal{L}_{max}} + w_2 \cdot \frac{\mathcal{E}(\mathbf{x})}{\mathcal{E}_{max}} - w_3 \cdot \frac{\bar{T}(\mathbf{x})}{\bar{T}_{max}} - w_4 \cdot \frac{\mathcal{H}(\mathbf{x})}{\mathcal{H}_{max}} + \sum_{k=1}^3 \Omega_k \cdot \phi_k(\mathbf{x})$$

Where:
* **Average Communication Latency:** $\mathcal{L}(\mathbf{x}) = \frac{1}{|\mathcal{C}|(|\mathcal{C}|-1)} \sum_{i \in \mathcal{C}} \sum_{j \in \mathcal{C}, j \ne i} \delta_{ij}$
* **Computational Cost Index:** $\mathcal{E}(\mathbf{x}) = \sum_{i \in \mathcal{C}} \text{CPU\_Load}_i$
* **Committee Trust Score:** $\bar{T}(\mathbf{x}) = \frac{1}{|\mathcal{C}|} \sum_{i \in \mathcal{C}} T_i(t)$
* **Selection Entropy:** $\mathcal{H}(\mathbf{x}) = - \sum_{i \in \mathcal{C}} p_i \ln p_i$, where $p_i = \frac{T_i}{\sum_{j \in \mathcal{C}} T_j}$
* **Hard Penalty Constraints $\phi_k$:**
  1. $\phi_1(\mathbf{x}) = \left| \sum_{i=1}^N x_i - R_{target} \right|$ (Enforces committee cardinality $R_{target} = 3f+1$)
  2. $\phi_2(\mathbf{x}) = \sum_{i \in \mathcal{C}} \max(0, T_{min} - T_i)$ (Enforces trust threshold)
  3. $\phi_3(\mathbf{x}) = \max\left(0, \frac{1}{3} - \frac{\sum_{i \in \mathcal{C}} \mathbb{I}_{malicious\_est}(i)}{R_{target}}\right)$ (Byzantine upper-bound)

### 2.2 Algorithm Dynamics and Phase Coordination

Let candidate solutions be continuous vectors $\mathbf{y}_p \in [0, 1]^N$ for $p \in \{1, \dots, P\}$. Discrete selection $\mathbf{x}_p$ is obtained by setting $x_{p, i} = 1$ for the top $R_{target}$ elements of $\mathbf{y}_p$.

**Dynamic Adaptive Coordination Factor $\kappa_t$:**
$$\kappa_t = \frac{1}{1 + \exp\left( 8 \cdot \left(\frac{t}{T_{max}} - 0.5\right) \right)} \cdot \left( \frac{\sigma_t(\mathcal{F})}{\sigma_0(\mathcal{F}) + \epsilon} \right)$$

* When $\kappa_t > 0.5$: System exhibits high fitness diversity; algorithm prioritizes **GWO Exploration**.
* When $\kappa_t \le 0.5$: Diversity has decreased; algorithm seamlessly shifts to **PSO Local Refinement** combined with **SA Stochastic Escape**.

**Swarm Position Update:**
$$\mathbf{y}_p^{t+1} = \kappa_t \cdot \mathbf{y}_{GWO, p}^{t+1} + (1 - \kappa_t) \cdot (\mathbf{y}_p^t + \mathbf{v}_{PSO, p}^{t+1})$$

Where:
$$\mathbf{y}_{GWO, p}^{t+1} = \frac{\mathbf{y}_1 + \mathbf{y}_2 + \mathbf{y}_3}{3}$$
$$\mathbf{y}_1 = \mathbf{y}_\alpha - \mathbf{A}_1 \odot |\mathbf{C}_1 \odot \mathbf{y}_\alpha - \mathbf{y}_p^t|, \quad \mathbf{A}_1 = 2a\mathbf{r}_1 - a, \quad a = 2(1 - t/T_{max})$$
$$\mathbf{v}_{PSO, p}^{t+1} = \omega(t) \mathbf{v}_p^t + c_1 r_4 (\mathbf{pbest}_p - \mathbf{y}_p^t) + c_2 r_5 (\mathbf{gbest} - \mathbf{y}_p^t)$$

**Metropolis Simulated Annealing Acceptance Criterion:**
If $\mathcal{F}(\mathbf{y}_p^{t+1}) > \mathcal{F}(\mathbf{y}_p^t)$, candidate is retained with probability:
$$P_{accept} = \exp\left( - \frac{\mathcal{F}(\mathbf{y}_p^{t+1}) - \mathcal{F}(\mathbf{y}_p^t)}{\theta_t} \right), \quad \theta_t = \theta_0 \cdot (0.95)^t$$

---

## 3. Trust-Aware nPBFT Protocol State Machine & Invariants

### 3.1 Byzantine Quorum Invariant
For an elected committee of size $R$, the maximum number of tolerable Byzantine nodes is:
$$f = \left\lfloor \frac{R - 1}{3} \right\rfloor$$

To guarantee safety under asynchronous conditions, any two quorums $\mathcal{Q}_1, \mathcal{Q}_2 \subseteq \mathcal{C}$ must intersect in at least one honest node:
$$|(\mathcal{Q}_1 \cap \mathcal{Q}_2) \setminus \mathcal{B}| \ge 1 \iff |\mathcal{Q}_1 \cap \mathcal{Q}_2| \ge f + 1$$

Since $|\mathcal{Q}_1 \cap \mathcal{Q}_2| \ge 2Q - R$, the minimal quorum size $Q(R, f)$ is formally:
$$Q(R, f) = \left\lceil \frac{R + f + 1}{2} \right\rceil$$

* **Special Case ($R = 3f + 1$):**
  $$Q = \left\lceil \frac{3f + 1 + f + 1}{2} \right\rceil = \frac{4f + 2}{2} = 2f + 1$$
* **General Case (arbitrary $R$):**
  For example, when $R = 5$ ($f = 1$), $Q = \lceil 7 / 2 \rceil = 4$, guaranteeing an intersection of $2(4) - 5 = 3 \ge f + 1 = 2$ nodes, containing at least $3 - 1 = 2 \ge 1$ honest validator.

This theorem guarantees that conflicting blocks or duplicate sequence numbers cannot simultaneously obtain Quorum Certificates for any arbitrary committee size $R \ge 4$.

### 3.2 Protocol Transitions
1. **State $S_0$ (IDLE):** Node listens for transactions and proposals.
2. **State $S_1$ (PRE-PREPARED):** Upon receipt of valid message $\langle \text{PRE-PREPARE}, v, n, d, B_k \rangle_{\sigma_L}$ from leader $L$, where $\text{VerifySig}(L, d) = \text{True}$ and $T_L \ge T_{threshold}$. Broadcast $\langle \text{PREPARE}, v, n, d, i \rangle_{\sigma_i}$.
3. **State $S_2$ (PREPARED):** Upon collecting $2f$ valid Prepare ballots matching $\langle v, n, d \rangle$. Assemble Prepared Certificate $P_{cert}(v, n, d)$ and broadcast $\langle \text{COMMIT}, v, n, d, i \rangle_{\sigma_i}$.
4. **State $S_3$ (COMMITTED):** Upon collecting $2f + 1$ valid Commit ballots matching $\langle v, n, d \rangle$. Assemble Quorum Certificate $Q_{cert}(v, n, d)$, commit $B_k$ into the DAG ledger, and increment local sequence counter $n \leftarrow n + 1$.
5. **State $S_4$ (VIEW-CHANGE):** If timeout $\tau_v = \tau_0 \cdot 2^v$ expires before reaching Committed state, broadcast $\langle \text{VIEW-CHANGE}, v+1, n, P_{cert}, i \rangle_{\sigma_i}$. When $2f+1$ view-change messages are collected, new leader $L' = (v+1) \pmod R$ broadcasts $\langle \text{NEW-VIEW}, v+1, \mathcal{V} \rangle_{\sigma_{L'}}$.

---

## 4. Directed Acyclic Graph (DAG) Ledger Formulation

A DAG ledger is formally defined as a directed acyclic graph $\mathcal{G} = (\mathcal{V}_{tx}, \mathcal{E}_{dep})$, where:
* $\mathcal{V}_{tx}$: Set of verified transaction vertices $T_k$.
* $\mathcal{E}_{dep} \subset \mathcal{V}_{tx} \times \mathcal{V}_{tx}$: Directed edges where $(T_k, T_p) \in \mathcal{E}_{dep}$ denotes that $T_k$ approves and references parent transaction $T_p$.

### 4.1 Vertex Schema
$$T_k = \langle \text{tx\_id}, \mathcal{P}_k, \text{payload\_cid}, \text{timestamp}, \text{sender\_pubkey}, \text{nonce}, \sigma_{sender}, Q_{cert} \rangle$$
Where:
* $\text{tx\_id} = \text{SHA256}(\text{CanonicalSerialization}(T_k \setminus \{\sigma_{sender}, Q_{cert}\}))$
* $\mathcal{P}_k = \{parent_1, parent_2\} \subset \mathcal{V}_{tx}$: Set of approved parent tip hashes.
* $\text{payload\_cid}$: 32-byte multihash of the off-chain payload stored in IPFS.

### 4.2 Cumulative Weight and Confidence Propagation
The direct score of vertex $T_k$ is initialized to 1. The cumulative weight $\mathcal{W}(T_k)$ is:
$$\mathcal{W}(T_k) = 1 + \sum_{T_c \in \mathcal{D}(T_k)} 1$$
where $\mathcal{D}(T_k)$ is the set of all direct and indirect descendants of $T_k$. A transaction is finalized when $\mathcal{W}(T_k) \ge \Theta_{threshold}$ or when confirmed by an nPBFT Quorum Certificate.

---

## 5. Reinforcement Learning Anomaly Detection Formulation

### 5.1 Deep Q-Network Bellman Optimality
The Q-function $Q(s, a; \theta)$ approximates the expected discounted cumulative reward:
$$Q^*(s, a) = \mathbb{E} \left[ r + \gamma_{rl} \max_{a'} Q^*(s', a') \;\middle|\; s, a \right]$$

To mitigate overestimation bias, we use Double-DQN:
$$Y_t^{DoubleQ} = r_{t+1} + \gamma_{rl} Q\left( s_{t+1}, \arg\max_a Q(s_{t+1}, a; \theta_t); \theta_t^- \right)$$

**Loss Function:**
$$\mathcal{L}_{DQN}(\theta) = \mathbb{E}_{(s, a, r, s') \sim \mathcal{D}} \left[ \left( Y_t^{DoubleQ} - Q(s, a; \theta) \right)^2 \right]$$

The target network weights $\theta^-$ are updated via soft Polyak averaging every $U$ steps:
$$\theta^- \leftarrow \tau_{target} \theta + (1 - \tau_{target}) \theta^-, \quad \tau_{target} = 0.01$$
