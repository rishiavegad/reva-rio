"""
Virtual P2P Network Simulator for IoT Swarms
Provides:
- VirtualChannel with synthetic latency distribution and Bernoulli packet loss
- Node swarm coordinator managing lifecycle, key exchange, and messaging
- Integrated simulation loop executing sensing -> DAG proposal -> ATHO election -> nPBFT consensus -> Trust update
- Comprehensive telemetry tracking (throughput, delivery ratio, dropped packets, attack logs)
"""

import time
import random
import math
from typing import Dict, List, Optional, Tuple, Any

from core.virtual_node import VirtualIoTNode, NodeBehavior
from core.crypto_primitives import sha256_digest
from core.ipfs_client import IPFSAdapter
from core.dag_ledger import DAGLedger
from core.trust import TrustEngine
from core.optimization import ValidatorSelectionProblem, run_atho
from core.npbft import NPBFTConsensusEngine, PBFTValidator

class VirtualChannel:
    def __init__(
        self,
        mean_delay_ms: float = 15.0,
        jitter_ms: float = 5.0,
        packet_loss_rate: float = 0.02
    ):
        self.mean_delay_ms = mean_delay_ms
        self.jitter_ms = jitter_ms
        self.packet_loss_rate = packet_loss_rate
        self.total_transmitted: int = 0
        self.total_dropped: int = 0

    def transmit(self, frame: dict, sender_node: VirtualIoTNode) -> Tuple[bool, float]:
        """
        Simulates channel transmission.
        Returns: (delivered: bool, delay_ms: float)
        """
        self.total_transmitted += 1

        # Check for node flakiness
        effective_loss = self.packet_loss_rate
        if sender_node.behavior == NodeBehavior.FLAKY:
            effective_loss = max(effective_loss, 0.25)

        # Random loss check
        if random.random() < effective_loss:
            self.total_dropped += 1
            return False, 0.0

        # Normal distribution delay clamped >= 1.0 ms
        delay = max(1.0, random.gauss(self.mean_delay_ms, self.jitter_ms))
        if sender_node.behavior == NodeBehavior.FLAKY:
            delay += random.uniform(20.0, 80.0)

        return True, delay

class IoTNetworkSimulator:
    def __init__(
        self,
        node_count: int = 20,
        malicious_ratio: float = 0.20,
        committee_size: int = 7,
        mean_delay_ms: float = 12.0,
        packet_loss_rate: float = 0.02,
        seed: int = 42
    ):
        random.seed(seed)
        self.node_count = node_count
        self.committee_size = committee_size
        self.channel = VirtualChannel(
            mean_delay_ms=mean_delay_ms,
            jitter_ms=4.0,
            packet_loss_rate=packet_loss_rate
        )
        self.ipfs = IPFSAdapter()
        self.dag = DAGLedger(confirmation_weight_threshold=4)
        self.trust_engine = TrustEngine()

        self.nodes: Dict[str, VirtualIoTNode] = {}
        self.node_ids: List[str] = []
        self._initialize_swarm(malicious_ratio)

        # Telemetry & History
        self.round_counter: int = 0
        self.total_transactions_submitted: int = 0
        self.total_transactions_confirmed: int = 0
        self.attack_events: List[dict] = []
        self.consensus_history: List[dict] = []
        self.latency_samples: List[float] = []

    def _initialize_swarm(self, malicious_ratio: float):
        """Creates nodes, sets up pairwise keys, and assigns behaviors."""
        malicious_count = int(self.node_count * malicious_ratio)
        honest_count = self.node_count - malicious_count

        behaviors = [NodeBehavior.HONEST] * honest_count
        
        # Distribute attack archetypes among malicious subset
        attack_types = [
            NodeBehavior.REPLAY_ATTACKER,
            NodeBehavior.TAMPER_ATTACKER,
            NodeBehavior.EQUIVOCATOR,
            NodeBehavior.FLOOD_ATTACKER,
            NodeBehavior.FLAKY
        ]
        for i in range(malicious_count):
            behaviors.append(attack_types[i % len(attack_types)])
        random.shuffle(behaviors)

        for i in range(self.node_count):
            nid = f"iot_node_{i:02d}"
            self.node_ids.append(nid)
            node = VirtualIoTNode(node_id=nid, behavior=behaviors[i])
            self.nodes[nid] = node
            self.trust_engine.register_node(nid)

        # Pairwise shared secrets setup for SecureChannel
        for i, u in enumerate(self.node_ids):
            for j, v in enumerate(self.node_ids):
                if i != j:
                    shared_secret = sha256_digest(f"SWARM_SECRET:{min(u, v)}:{max(u, v)}".encode('utf-8')).encode('utf-8')
                    self.nodes[u].secure_channel.establish_session(v, shared_secret)

    def run_simulation_step(self, transactions_per_step: int = 5) -> dict:
        """
        Executes an end-to-end simulation cycle:
        1. Nodes sense telemetry and propose transactions.
        2. Transactions verified and ingested into DAG ledger.
        3. ATHO algorithm solves for optimal validator committee.
        4. Trust-aware nPBFT runs consensus on new DAG tips.
        5. Quorum Certificate checkpoint anchored to DAG.
        6. Node trust scores refreshed.
        """
        t_start = time.perf_counter()
        self.round_counter += 1
        step_tx_ids = []
        step_attack_count = 0

        # Step 1: Generate Proposals
        proposing_nodes = random.sample(self.node_ids, min(transactions_per_step, self.node_count))
        for nid in proposing_nodes:
            node = self.nodes[nid]
            # Flooding attacker sends burst
            burst_size = 4 if node.behavior == NodeBehavior.FLOOD_ATTACKER else 1
            for _ in range(burst_size):
                self.total_transactions_submitted += 1
                ok, prop, err = node.create_transaction_proposal(self.ipfs, self.dag)
                if ok and prop:
                    # Ingest into DAG
                    dag_ok, tx_id, dag_err = self.dag.add_transaction(
                        parents=prop["parents"],
                        payload_cid=prop["payload_cid"],
                        payload_size_bytes=prop["payload_size_bytes"],
                        sender_pubkey=prop["sender_pubkey"],
                        nonce=prop["nonce"],
                        timestamp=prop["timestamp"],
                        signature=prop["signature"]
                    )
                    if dag_ok and tx_id:
                        step_tx_ids.append(tx_id)
                        self.total_transactions_confirmed += 1
                    else:
                        step_attack_count += 1
                        self.attack_events.append({
                            "round": self.round_counter,
                            "node_id": nid,
                            "type": node.behavior.value,
                            "reason": dag_err
                        })
                        if "Signature" in (dag_err or ""):
                            self.trust_engine.record_infraction(nid, "FORGERY")

        # Step 2: ATHO Committee Election
        trust_map = {nid: self.trust_engine.get_trust(nid) for nid in self.node_ids}
        cpu_map = {nid: (self.nodes[nid].cpu_time_ms / 1000.0) % 1.0 for nid in self.node_ids}
        
        # Build synthetic dynamic latency matrix based on channel
        lat_map = {}
        for u in self.node_ids:
            lat_map[u] = {}
            for v in self.node_ids:
                lat_map[u][v] = 0.0 if u == v else max(2.0, self.channel.mean_delay_ms + (hash(u + v) % 8))

        problem = ValidatorSelectionProblem(
            node_ids=self.node_ids,
            trust_scores=trust_map,
            cpu_loads=cpu_map,
            latency_matrix=lat_map,
            target_size=self.committee_size,
            min_trust_floor=0.45
        )

        selected_indices, best_fit, _ = run_atho(problem, pop_size=15, max_iter=25, seed=self.round_counter * 13)
        committee_ids = [self.node_ids[idx] for idx in selected_indices]

        # Step 3: Run nPBFT Consensus Round
        validators = {
            nid: PBFTValidator(nid, self.nodes[nid].sk, self.nodes[nid].pk)
            for nid in committee_ids
        }

        # Check if any elected validator is an attacker
        adversary_config = {}
        unresponsive_in_committee = [
            nid for nid in committee_ids
            if self.nodes[nid].behavior in (NodeBehavior.FLAKY, NodeBehavior.FLOOD_ATTACKER)
        ]
        if unresponsive_in_committee:
            adversary_config["unresponsive_nodes"] = unresponsive_in_committee

        equivocating_in_committee = [
            nid for nid in committee_ids
            if self.nodes[nid].behavior == NodeBehavior.EQUIVOCATOR
        ]
        # If leader is an equivocator, inject equivocation
        leader_id = committee_ids[0]
        if leader_id in equivocating_in_committee:
            adversary_config["equivocating_leader"] = True

        consensus_engine = NPBFTConsensusEngine(
            committee_node_ids=committee_ids,
            validators=validators,
            trust_engine=self.trust_engine,
            view=self.round_counter % self.committee_size,
            sequence_number=self.round_counter
        )

        block_proposal = {
            "round": self.round_counter,
            "dag_tips": self.dag.get_tips(2),
            "ingested_tx_count": len(step_tx_ids),
            "timestamp": time.time()
        }

        consensus_ok, qcert, c_metrics = consensus_engine.execute_round(
            block_proposal=block_proposal,
            adversary_config=adversary_config
        )

        # Step 4: If Consensus Succeeded, Anchor Quorum Certificate to DAG Tips
        if consensus_ok and qcert:
            for tid in block_proposal["dag_tips"]:
                self.dag.attach_checkpoint(tid, {
                    "view": qcert.view,
                    "seq": qcert.sequence_number,
                    "digest": qcert.digest,
                    "signatures_count": len(qcert.signatures)
                })

        # Record metrics
        elapsed_step_ms = (time.perf_counter() - t_start) * 1000.0
        self.latency_samples.append(elapsed_step_ms)

        step_summary = {
            "round": self.round_counter,
            "transactions_proposed": len(proposing_nodes),
            "transactions_ingested": len(step_tx_ids),
            "attacks_intercepted": step_attack_count,
            "atho_best_fitness": round(best_fit, 4),
            "committee": committee_ids,
            "consensus_success": consensus_ok,
            "consensus_phase": c_metrics.get("phase", "UNKNOWN"),
            "quorum_size": c_metrics.get("quorum_size", 0),
            "step_duration_ms": round(elapsed_step_ms, 2)
        }
        self.consensus_history.append(step_summary)
        return step_summary

    def get_network_telemetry(self) -> dict:
        """Returns full network state and metrics for dashboard & analytics."""
        node_summaries = [node.get_status() for node in self.nodes.values()]
        trust_profiles = self.trust_engine.export_profiles()

        # Merge trust profiles into node summaries
        for ns in node_summaries:
            nid = ns["node_id"]
            if nid in trust_profiles:
                ns["trust"] = trust_profiles[nid]["composite_trust"]
                ns["quarantined"] = trust_profiles[nid]["quarantined"]
                ns["infractions"] = trust_profiles[nid]["infractions"]

        delivery_ratio = (
            (self.channel.total_transmitted - self.channel.total_dropped) / self.channel.total_transmitted
            if self.channel.total_transmitted > 0 else 1.0
        )

        return {
            "round_counter": self.round_counter,
            "node_count": self.node_count,
            "total_tx_submitted": self.total_transactions_submitted,
            "total_tx_confirmed": self.total_transactions_confirmed,
            "channel_delivery_ratio": round(delivery_ratio * 100.0, 2),
            "channel_dropped_packets": self.channel.total_dropped,
            "recent_attacks": self.attack_events[-10:],
            "total_attacks_logged": len(self.attack_events),
            "nodes": node_summaries,
            "dag_graph": self.dag.export_graph()
        }
