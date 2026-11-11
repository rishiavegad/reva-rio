"""
Trust-Aware Novel Practical Byzantine Fault Tolerance (nPBFT) Protocol Engine
Implements:
1. Three-phase consensus: Pre-Prepare -> Prepare -> Commit -> Committed
2. Quorum Certificate (Q_cert) and Prepared Certificate (P_cert) aggregation
3. Mathematical Quorum Threshold: Q(R, f) = ceil((R + f + 1) / 2) with f = (R - 1) // 3
4. Ed25519 digital signature validation on all ballots
5. Dynamic leader election based on view number and committee ranking
6. View Change protocol triggered on timeouts, equivocation, or unresponsiveness
7. Integrated trust-based slashing and validator evaluation
"""

import time
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any

from core.crypto_primitives import (
    generate_keypair,
    sign_message,
    verify_signature,
    sha256_digest
)
from core.trust import TrustEngine

class PBFTPhase(str, Enum):
    IDLE = "IDLE"
    PRE_PREPARED = "PRE_PREPARED"
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"
    VIEW_CHANGE = "VIEW_CHANGE"

@dataclass
class Ballot:
    phase: str  # "PRE_PREPARE", "PREPARE", "COMMIT", "VIEW_CHANGE"
    view: int
    sequence_number: int
    digest: str
    sender_id: str
    signature: str
    timestamp: float = field(default_factory=time.time)
    payload: Optional[dict] = None

@dataclass
class QuorumCertificate:
    view: int
    sequence_number: int
    digest: str
    signatures: Dict[str, str]  # validator_id -> signature
    timestamp: float = field(default_factory=time.time)

class PBFTValidator:
    def __init__(self, node_id: str, sk: bytes, pk: bytes):
        self.node_id = node_id
        self.sk = sk
        self.pk = pk
        self.pk_hex = pk.hex()

    def sign(self, message_str: str) -> str:
        sig_bytes = sign_message(self.sk, message_str.encode('utf-8'))
        return sig_bytes.hex()

class NPBFTConsensusEngine:
    def __init__(
        self,
        committee_node_ids: List[str],
        validators: Dict[str, PBFTValidator],
        trust_engine: TrustEngine,
        view: int = 0,
        sequence_number: int = 1,
        base_timeout_ms: float = 400.0
    ):
        self.committee = sorted(committee_node_ids)
        self.validators = validators
        self.trust_engine = trust_engine
        self.view = view
        self.sequence_number = sequence_number
        self.base_timeout_ms = base_timeout_ms

        self.R = len(self.committee)
        assert self.R >= 4, f"Byzantine consensus requires R >= 4, got {self.R}"
        self.f = (self.R - 1) // 3
        # Strict Byzantine Quorum rule
        self.quorum_size = math.ceil((self.R + self.f + 1) / 2)

        # Message pools for current sequence
        self.pre_prepare_msg: Optional[Ballot] = None
        self.prepare_votes: Dict[str, Ballot] = {}
        self.commit_votes: Dict[str, Ballot] = {}
        self.view_change_votes: Dict[int, Dict[str, Ballot]] = {}

        self.phase = PBFTPhase.IDLE
        self.prepared_cert: Optional[QuorumCertificate] = None
        self.quorum_cert: Optional[QuorumCertificate] = None
        self.logs: List[str] = []

    def get_leader(self) -> str:
        """Deterministically selects leader for current view."""
        return self.committee[self.view % self.R]

    def _log(self, msg: str):
        self.logs.append(f"[{time.strftime('%H:%M:%S')}] [View {self.view} Seq {self.sequence_number}] {msg}")

    def execute_round(
        self,
        block_proposal: dict,
        adversary_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[QuorumCertificate], Dict[str, Any]]:
        """
        Executes a complete 3-phase consensus round on block_proposal.
        adversary_config allows injecting:
        - "equivocating_leader": leader proposes different blocks to different nodes
        - "unresponsive_nodes": list of node IDs that do not vote
        - "invalid_signature_nodes": list of node IDs that forge signatures
        - "tampered_digest_nodes": list of node IDs that vote on a wrong hash
        """
        adversary_config = adversary_config or {}
        equivocating = adversary_config.get("equivocating_leader", False)
        unresponsive = set(adversary_config.get("unresponsive_nodes", []))
        invalid_sig_nodes = set(adversary_config.get("invalid_signature_nodes", []))
        tampered_nodes = set(adversary_config.get("tampered_digest_nodes", []))

        t_start = time.perf_counter()
        leader_id = self.get_leader()
        self._log(f"Starting nPBFT consensus round. Elected Leader: {leader_id}, Quorum threshold: {self.quorum_size}/{self.R}")

        # Compute Block Digest
        raw_digest = sha256_digest(str(sorted(block_proposal.items())).encode('utf-8'))
        
        # -------------------------------------------------------------
        # PHASE 1: PRE-PREPARE
        # -------------------------------------------------------------
        if leader_id in unresponsive:
            self._log(f"Leader {leader_id} is unresponsive. Triggering View Change.")
            self._trigger_view_change()
            return False, None, self._get_round_metrics(t_start, False)

        leader_val = self.validators[leader_id]
        leader_sig = leader_val.sign(f"PRE_PREPARE:{self.view}:{self.sequence_number}:{raw_digest}")
        
        self.pre_prepare_msg = Ballot(
            phase="PRE_PREPARE",
            view=self.view,
            sequence_number=self.sequence_number,
            digest=raw_digest,
            sender_id=leader_id,
            signature=leader_sig,
            payload=block_proposal
        )
        self.phase = PBFTPhase.PRE_PREPARED
        self._log(f"Leader {leader_id} issued valid PRE-PREPARE for digest {raw_digest[:12]}...")

        # If leader is equivocating, simulate equivocation detection
        if equivocating:
            self._log(f"[BYZANTINE ATTACK] Leader {leader_id} produced equivocating dual-proposals!")
            self.trust_engine.record_infraction(leader_id, "EQUIVOCATION", penalty_weight=0.85)
            self._trigger_view_change()
            return False, None, self._get_round_metrics(t_start, False)

        # -------------------------------------------------------------
        # PHASE 2: PREPARE (All-to-All within committee)
        # -------------------------------------------------------------
        valid_prepare_count = 0
        for node_id in self.committee:
            if node_id in unresponsive:
                continue

            v_obj = self.validators[node_id]
            vote_digest = "tampered_digest_deadbeef" if node_id in tampered_nodes else raw_digest
            
            if node_id in invalid_sig_nodes:
                sig = "00" * 64  # forged signature
            else:
                sig = v_obj.sign(f"PREPARE:{self.view}:{self.sequence_number}:{vote_digest}")

            ballot = Ballot(
                phase="PREPARE",
                view=self.view,
                sequence_number=self.sequence_number,
                digest=vote_digest,
                sender_id=node_id,
                signature=sig
            )

            # Verification by committee peers
            is_valid_sig = verify_signature(
                bytes.fromhex(v_obj.pk_hex),
                f"PREPARE:{self.view}:{self.sequence_number}:{vote_digest}".encode('utf-8'),
                bytes.fromhex(sig)
            )

            if is_valid_sig and vote_digest == raw_digest:
                self.prepare_votes[node_id] = ballot
                valid_prepare_count += 1
                self.trust_engine.record_consensus_vote(node_id, True)
            else:
                self._log(f"[REJECTED] Invalid PREPARE from {node_id} (sig_valid={is_valid_sig}, digest_match={vote_digest == raw_digest})")
                self.trust_engine.record_consensus_vote(node_id, False)
                if not is_valid_sig:
                    self.trust_engine.record_infraction(node_id, "FORGERY", penalty_weight=0.60)

        # In PBFT, Prepared state requires 2f PREPARE messages from backup nodes
        if valid_prepare_count >= (2 * self.f):
            self.phase = PBFTPhase.PREPARED
            self.prepared_cert = QuorumCertificate(
                view=self.view,
                sequence_number=self.sequence_number,
                digest=raw_digest,
                signatures={nid: b.signature for nid, b in self.prepare_votes.items()}
            )
            self._log(f"Reached PREPARED state with {valid_prepare_count} valid votes.")
        else:
            self._log(f"Failed to achieve PREPARED state: {valid_prepare_count}/{2*self.f} required. Triggering View Change.")
            self._trigger_view_change()
            return False, None, self._get_round_metrics(t_start, False)

        # -------------------------------------------------------------
        # PHASE 3: COMMIT (All-to-All within committee)
        # -------------------------------------------------------------
        valid_commit_count = 0
        for node_id in self.committee:
            if node_id in unresponsive:
                continue

            v_obj = self.validators[node_id]
            vote_digest = "tampered_digest_deadbeef" if node_id in tampered_nodes else raw_digest

            if node_id in invalid_sig_nodes:
                sig = "00" * 64
            else:
                sig = v_obj.sign(f"COMMIT:{self.view}:{self.sequence_number}:{vote_digest}")

            ballot = Ballot(
                phase="COMMIT",
                view=self.view,
                sequence_number=self.sequence_number,
                digest=vote_digest,
                sender_id=node_id,
                signature=sig
            )

            is_valid_sig = verify_signature(
                bytes.fromhex(v_obj.pk_hex),
                f"COMMIT:{self.view}:{self.sequence_number}:{vote_digest}".encode('utf-8'),
                bytes.fromhex(sig)
            )

            if is_valid_sig and vote_digest == raw_digest:
                self.commit_votes[node_id] = ballot
                valid_commit_count += 1
                self.trust_engine.record_consensus_vote(node_id, True)
            else:
                self._log(f"[REJECTED] Invalid COMMIT from {node_id}")
                self.trust_engine.record_consensus_vote(node_id, False)

        # Check for Quorum threshold Q(R, f)
        if valid_commit_count >= self.quorum_size:
            self.phase = PBFTPhase.COMMITTED
            self.quorum_cert = QuorumCertificate(
                view=self.view,
                sequence_number=self.sequence_number,
                digest=raw_digest,
                signatures={nid: b.signature for nid, b in self.commit_votes.items()}
            )
            self._log(f"[SUCCESS] Reached COMMITTED state. Quorum Certificate assembled ({valid_commit_count}/{self.quorum_size}).")
            self.sequence_number += 1
            return True, self.quorum_cert, self._get_round_metrics(t_start, True)
        else:
            self._log(f"Quorum not reached for COMMIT ({valid_commit_count}/{self.quorum_size}). Triggering View Change.")
            self._trigger_view_change()
            return False, None, self._get_round_metrics(t_start, False)

    def _trigger_view_change(self):
        """Advances view and rotates leader."""
        old_view = self.view
        self.view += 1
        self.phase = PBFTPhase.VIEW_CHANGE
        new_leader = self.get_leader()
        self._log(f"[VIEW CHANGE] Rotated View {old_view} -> {self.view}. New Leader: {new_leader}")
        # Reset current message state
        self.pre_prepare_msg = None
        self.prepare_votes.clear()
        self.commit_votes.clear()

    def _get_round_metrics(self, t_start: float, success: bool) -> Dict[str, Any]:
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        # Calculate theoretical message overhead:
        # Pre-prepare: R-1 messages
        # Prepare: R * (R-1) messages
        # Commit: R * (R-1) messages
        msg_complexity = (self.R - 1) + 2 * (self.R * (self.R - 1))
        return {
            "success": success,
            "elapsed_ms": round(elapsed_ms, 2),
            "view": self.view,
            "sequence_number": self.sequence_number,
            "committee_size": self.R,
            "quorum_size": self.quorum_size,
            "fault_tolerance_f": self.f,
            "message_complexity": msg_complexity,
            "phase": self.phase.value
        }
