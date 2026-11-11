"""
Dynamic Multi-Dimensional Trust Management Engine for IoT Nodes
Implements:
- Direct Communication Trust D_i(t)
- Consensus Participation Trust C_i(t)
- Anomaly History Slashing A_i(t)
- Overall Composite Trust Score T_i(t) = alpha*D + beta*C + gamma*A
- Asymmetric Slashing and Probationary Cold-Start Protection
"""

import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class TrustRecord:
    node_id: str
    direct_trust: float = 0.50
    consensus_trust: float = 0.50
    anomaly_factor: float = 1.00
    composite_trust: float = 0.50
    success_count: int = 0
    failure_count: int = 0
    consensus_participations: int = 0
    consensus_valid_votes: int = 0
    infractions: List[str] = field(default_factory=list)
    quarantined: bool = False
    last_updated: float = field(default_factory=time.time)

class TrustEngine:
    def __init__(
        self,
        alpha: float = 0.35,
        beta: float = 0.45,
        gamma: float = 0.20,
        decay_rate: float = 0.25,
        quarantine_threshold: float = 0.30,
        min_validator_trust: float = 0.60
    ):
        assert math.isclose(alpha + beta + gamma, 1.0), "Trust weights must sum to 1.0"
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.decay_rate = decay_rate
        self.quarantine_threshold = quarantine_threshold
        self.min_validator_trust = min_validator_trust
        self.records: Dict[str, TrustRecord] = {}

    def register_node(self, node_id: str) -> TrustRecord:
        if node_id not in self.records:
            self.records[node_id] = TrustRecord(node_id=node_id)
        return self.records[node_id]

    def record_direct_interaction(self, node_id: str, success: bool):
        rec = self.register_node(node_id)
        if success:
            rec.success_count += 1
            sample = 1.0
        else:
            rec.failure_count += 1
            sample = 0.0
        
        # Exponential Bayesian moving average
        rec.direct_trust = (1.0 - self.decay_rate) * rec.direct_trust + self.decay_rate * sample
        self._recompute_composite(rec)

    def record_consensus_vote(self, node_id: str, valid: bool):
        rec = self.register_node(node_id)
        rec.consensus_participations += 1
        if valid:
            rec.consensus_valid_votes += 1
            vote_score = 1.0
        else:
            vote_score = 0.0
            
        rec.consensus_trust = (1.0 - self.decay_rate) * rec.consensus_trust + self.decay_rate * vote_score
        self._recompute_composite(rec)

    def record_infraction(self, node_id: str, infraction_type: str, penalty_weight: Optional[float] = None):
        """
        Asymmetrically slash trust based on verified anomaly or Byzantine act.
        Infraction categories:
        - FORGERY: 0.60
        - REPLAY: 0.45
        - EQUIVOCATION: 0.85
        - FLOODING: 0.40
        """
        rec = self.register_node(node_id)
        if penalty_weight is None:
            weights = {
                "FORGERY": 0.60,
                "REPLAY": 0.45,
                "EQUIVOCATION": 0.85,
                "FLOODING": 0.40
            }
            penalty_weight = weights.get(infraction_type, 0.50)

        rec.infractions.append(infraction_type)
        # Multiplicative asymmetric penalty
        rec.anomaly_factor *= (1.0 - penalty_weight)
        # Direct trust also takes an immediate hit
        rec.direct_trust *= (1.0 - penalty_weight * 0.5)
        self._recompute_composite(rec)

    def set_quarantine(self, node_id: str, quarantined: bool):
        rec = self.register_node(node_id)
        rec.quarantined = quarantined
        if quarantined:
            rec.composite_trust = min(rec.composite_trust, self.quarantine_threshold * 0.5)

    def _recompute_composite(self, rec: TrustRecord):
        rec.composite_trust = (
            self.alpha * rec.direct_trust +
            self.beta * rec.consensus_trust +
            self.gamma * rec.anomaly_factor
        )
        rec.composite_trust = max(0.0, min(1.0, rec.composite_trust))
        if rec.composite_trust < self.quarantine_threshold:
            rec.quarantined = True
        rec.last_updated = time.time()

    def get_trust(self, node_id: str) -> float:
        return self.register_node(node_id).composite_trust

    def is_eligible_validator(self, node_id: str) -> bool:
        rec = self.register_node(node_id)
        return (not rec.quarantined) and (rec.composite_trust >= self.min_validator_trust)

    def export_profiles(self) -> Dict[str, dict]:
        return {
            nid: {
                "node_id": r.node_id,
                "composite_trust": round(r.composite_trust, 4),
                "direct_trust": round(r.direct_trust, 4),
                "consensus_trust": round(r.consensus_trust, 4),
                "anomaly_factor": round(r.anomaly_factor, 4),
                "success_count": r.success_count,
                "failure_count": r.failure_count,
                "infractions": r.infractions,
                "quarantined": r.quarantined,
                "last_updated": r.last_updated
            }
            for nid, r in self.records.items()
        }
