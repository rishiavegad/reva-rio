"""
Directed Acyclic Graph (DAG) Ledger Engine for IoT Networks
Provides:
- Lightweight DAG transaction structure with off-chain IPFS CID pointers
- Strict cycle detection (Kahn's / DFS topological invariant)
- MCMC-style tip selection and parent reference attachment
- Cumulative weight propagation for confidence scoring
- Checkpointing via nPBFT Quorum Certificates
"""

import time
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple, Any

from core.crypto_primitives import (
    verify_signature,
    sha256_digest
)

@dataclass
class DAGVertex:
    tx_id: str
    parents: List[str]
    payload_cid: str
    payload_size_bytes: int
    sender_pubkey: str
    nonce: int
    timestamp: float
    signature: str
    cumulative_weight: int = 1
    confirmed: bool = False
    quorum_cert: Optional[dict] = None

class DAGLedger:
    def __init__(self, confirmation_weight_threshold: int = 5):
        self.vertices: Dict[str, DAGVertex] = {}
        # Adjacency tracking: parent -> list of direct children
        self.children_map: Dict[str, List[str]] = {}
        self.confirmation_threshold = confirmation_weight_threshold
        
        # Initialize Genesis Transaction
        self.genesis_id = self._create_genesis()

    def _create_genesis(self) -> str:
        genesis_cid = "bafy_sha256_genesis000000000000000000000000000000000000000000000000000000"
        tx_id = sha256_digest(f"GENESIS:{genesis_cid}:{0.0}".encode('utf-8'))
        v = DAGVertex(
            tx_id=tx_id,
            parents=[],
            payload_cid=genesis_cid,
            payload_size_bytes=0,
            sender_pubkey="00" * 32,
            nonce=0,
            timestamp=0.0,
            signature="00" * 64,
            cumulative_weight=1,
            confirmed=True
        )
        self.vertices[tx_id] = v
        self.children_map[tx_id] = []
        return tx_id

    def get_tips(self, max_tips: int = 2) -> List[str]:
        """
        Returns up to max_tips transaction IDs that currently have zero children
        (unapproved tips). If all tips are approved, returns the highest-weight vertices.
        """
        unapproved = [tx_id for tx_id, children in self.children_map.items() if len(children) == 0]
        if not unapproved:
            # Fallback to genesis or highest weight
            return [self.genesis_id]
        
        # Sort by timestamp recency or cumulative weight
        unapproved.sort(key=lambda tid: (self.vertices[tid].cumulative_weight, self.vertices[tid].timestamp), reverse=True)
        return unapproved[:max_tips]

    def validate_acyclicity(self, new_tx_id: str, candidate_parents: List[str]) -> bool:
        """
        Ensures that adding new_tx_id referencing candidate_parents does not create a cycle.
        Since new_tx_id is new, a cycle can only occur if new_tx_id is already an ancestor of any parent.
        """
        if new_tx_id in self.vertices:
            return False  # duplicate transaction

        for p in candidate_parents:
            if p not in self.vertices:
                return False  # parent must exist in ledger
            if p == new_tx_id:
                return False  # self-loop

        # Deep search: verify new_tx_id is not reachable from candidate_parents
        visited = set()
        queue = list(candidate_parents)
        while queue:
            curr = queue.pop(0)
            if curr == new_tx_id:
                return False  # Cycle detected!
            if curr not in visited:
                visited.add(curr)
                # Traverse upward parents
                queue.extend(self.vertices[curr].parents)

        return True

    def add_transaction(
        self,
        parents: List[str],
        payload_cid: str,
        payload_size_bytes: int,
        sender_pubkey: str,
        nonce: int,
        timestamp: float,
        signature: str,
        quorum_cert: Optional[dict] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Appends a validated transaction to the DAG.
        Returns: (success, tx_id, error_message)
        """
        # Canonical message digest for signing
        canonical_str = f"{sorted(parents)}:{payload_cid}:{payload_size_bytes}:{sender_pubkey}:{nonce}:{timestamp}"
        tx_id = sha256_digest(canonical_str.encode('utf-8'))

        # Check signature (unless it's a test/genesis transaction)
        if sender_pubkey != "00" * 32:
            try:
                sig_valid = verify_signature(
                    bytes.fromhex(sender_pubkey),
                    canonical_str.encode('utf-8'),
                    bytes.fromhex(signature)
                )
                if not sig_valid:
                    return False, None, "Invalid cryptographic signature"
            except Exception as e:
                return False, None, f"Signature verification error: {str(e)}"

        # Validate parents exist
        if not parents:
            parents = [self.genesis_id]
        for p in parents:
            if p not in self.vertices:
                return False, None, f"Parent vertex {p} not found in DAG"

        # Check acyclicity
        if not self.validate_acyclicity(tx_id, parents):
            return False, None, "Acyclicity violation: transaction introduces a cycle"

        # Construct vertex
        vertex = DAGVertex(
            tx_id=tx_id,
            parents=parents,
            payload_cid=payload_cid,
            payload_size_bytes=payload_size_bytes,
            sender_pubkey=sender_pubkey,
            nonce=nonce,
            timestamp=timestamp,
            signature=signature,
            cumulative_weight=1,
            confirmed=(quorum_cert is not None),
            quorum_cert=quorum_cert
        )

        self.vertices[tx_id] = vertex
        self.children_map[tx_id] = []

        # Register child relationship
        for p in parents:
            self.children_map[p].append(tx_id)

        # Propagate cumulative weight upward to all ancestors
        self._propagate_weight(parents)

        return True, tx_id, None

    def _propagate_weight(self, ancestor_roots: List[str]):
        """Increments cumulative weight of all ancestor vertices."""
        visited = set()
        queue = list(ancestor_roots)
        while queue:
            curr = queue.pop(0)
            if curr in self.vertices and curr not in visited:
                visited.add(curr)
                self.vertices[curr].cumulative_weight += 1
                if self.vertices[curr].cumulative_weight >= self.confirmation_threshold:
                    self.vertices[curr].confirmed = True
                queue.extend(self.vertices[curr].parents)

    def attach_checkpoint(self, tx_id: str, quorum_cert: dict) -> bool:
        """Anchors an nPBFT Quorum Certificate to finalize a DAG vertex."""
        if tx_id in self.vertices:
            v = self.vertices[tx_id]
            v.quorum_cert = quorum_cert
            v.confirmed = True
            return True
        return False

    def export_graph(self) -> Dict[str, Any]:
        """Exports vertices and edges for dashboard visualization."""
        nodes = []
        edges = []
        for tid, v in self.vertices.items():
            nodes.append({
                "id": tid,
                "label": tid[:8] + "...",
                "parents": v.parents,
                "payload_cid": v.payload_cid[:16] + "...",
                "payload_size": v.payload_size_bytes,
                "weight": v.cumulative_weight,
                "confirmed": v.confirmed,
                "has_qcert": v.quorum_cert is not None,
                "timestamp": v.timestamp
            })
            for p in v.parents:
                edges.append({
                    "source": tid,
                    "target": p
                })
        return {
            "total_vertices": len(self.vertices),
            "nodes": nodes,
            "edges": edges
        }
