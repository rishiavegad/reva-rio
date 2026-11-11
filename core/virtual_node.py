"""
Virtual IoT Node Implementation
Simulates:
- Cryptographic identity (Ed25519 keypair, session keys)
- Node behavioral archetypes: HONEST, FLAKY, REPLAY_ATTACKER, TAMPER_ATTACKER, EQUIVOCATOR, FLOOD_ATTACKER
- Simulated hardware resource monitoring (CPU time, memory footprint, transmission counters)
- Telemetry sensor generation and off-chain IPFS payload packaging
"""

import time
import random
import json
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

from core.crypto_primitives import (
    generate_keypair,
    sign_message,
    verify_signature,
    sha256_digest
)
from core.secure_channel import SecureChannel
from core.ipfs_client import IPFSAdapter
from core.dag_ledger import DAGLedger
from core.trust import TrustEngine

class NodeBehavior(str, Enum):
    HONEST = "HONEST"
    FLAKY = "FLAKY"
    REPLAY_ATTACKER = "REPLAY_ATTACKER"
    TAMPER_ATTACKER = "TAMPER_ATTACKER"
    EQUIVOCATOR = "EQUIVOCATOR"
    FLOOD_ATTACKER = "FLOOD_ATTACKER"

class VirtualIoTNode:
    def __init__(
        self,
        node_id: str,
        behavior: NodeBehavior = NodeBehavior.HONEST,
        sensor_type: str = "ENVIRONMENTAL",
        battery_level: float = 100.0,
        cpu_frequency_mhz: int = 160,
        ram_kb: int = 320
    ):
        self.node_id = node_id
        self.behavior = behavior
        self.sensor_type = sensor_type
        self.battery_level = battery_level
        self.cpu_frequency_mhz = cpu_frequency_mhz
        self.ram_kb = ram_kb

        # Cryptographic Identity
        self.sk, self.pk = generate_keypair()
        self.pk_hex = self.pk.hex()
        self.secure_channel = SecureChannel(node_id=self.node_id)

        # Resource Accounting
        self.cpu_time_ms: float = 0.0
        self.memory_used_bytes: int = 4096  # base runtime state
        self.messages_sent: int = 0
        self.messages_received: int = 0
        self.packets_dropped: int = 0
        self.tx_counter: int = 0
        self.last_sent_frame: Optional[dict] = None

    def read_sensors(self) -> dict:
        """Simulates sampling physical environmental sensors."""
        t_start = time.perf_counter()
        data = {
            "node_id": self.node_id,
            "sensor_type": self.sensor_type,
            "temperature_c": round(22.0 + random.uniform(-4.0, 6.0), 2),
            "relative_humidity_pct": round(55.0 + random.uniform(-10.0, 15.0), 2),
            "pressure_hpa": round(1013.25 + random.uniform(-5.0, 5.0), 2),
            "battery_pct": max(0.0, round(self.battery_level, 2)),
            "timestamp": time.time()
        }
        # Microcontroller energy expenditure
        self.battery_level = max(0.0, self.battery_level - 0.005)
        self.cpu_time_ms += (time.perf_counter() - t_start) * 1000.0
        return data

    def create_transaction_proposal(
        self,
        ipfs_client: IPFSAdapter,
        dag_ledger: DAGLedger
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Gathers sensor data, puts large payload off-chain into IPFS,
        constructs DAG vertex with parents, signs with Ed25519, and packages proposal.
        """
        t_start = time.perf_counter()
        sensor_data = self.read_sensors()

        # Step 1: Upload raw payload to IPFS (off-chain)
        cid, raw_size, ref_size = ipfs_client.upload_payload(sensor_data)
        self.memory_used_bytes += ref_size

        # Step 2: Select parents from DAG tips
        parents = dag_ledger.get_tips(max_tips=2)

        self.tx_counter += 1
        nonce = self.tx_counter
        timestamp = time.time()

        # Step 3: Check behavioral injection
        if self.behavior == NodeBehavior.TAMPER_ATTACKER:
            # Inject forged signature
            signature = "00" * 64
        else:
            canonical_str = f"{sorted(parents)}:{cid}:{raw_size}:{self.pk_hex}:{nonce}:{timestamp}"
            sig_bytes = sign_message(self.sk, canonical_str.encode('utf-8'))
            signature = sig_bytes.hex()

        proposal = {
            "parents": parents,
            "payload_cid": cid,
            "payload_size_bytes": raw_size,
            "sender_pubkey": self.pk_hex,
            "nonce": nonce,
            "timestamp": timestamp,
            "signature": signature,
            "sensor_summary": f"T={sensor_data['temperature_c']}C, H={sensor_data['relative_humidity_pct']}%"
        }

        self.cpu_time_ms += (time.perf_counter() - t_start) * 1000.0
        return True, proposal, None

    def package_p2p_message(
        self,
        receiver_id: str,
        message_type: str,
        payload: Any
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Encapsulates payload into an encrypted & authenticated P2P frame."""
        t_start = time.perf_counter()

        if self.behavior == NodeBehavior.REPLAY_ATTACKER and self.last_sent_frame is not None:
            # Replay past frame
            replayed = dict(self.last_sent_frame)
            self.messages_sent += 1
            self.cpu_time_ms += (time.perf_counter() - t_start) * 1000.0
            return True, replayed, None

        ok, frame, err = self.secure_channel.encrypt_and_frame(receiver_id, message_type, payload)
        if ok and frame:
            if self.behavior == NodeBehavior.TAMPER_ATTACKER:
                # Corrupt 1 hex byte of ciphertext
                ct = frame["ciphertext"]
                frame["ciphertext"] = ("00" if ct[:2] != "00" else "ff") + ct[2:]
            
            self.last_sent_frame = dict(frame)
            self.messages_sent += 1

        self.cpu_time_ms += (time.perf_counter() - t_start) * 1000.0
        return ok, frame, err

    def receive_p2p_message(
        self,
        frame: dict,
        trust_engine: TrustEngine
    ) -> Tuple[bool, Optional[Any], Optional[str]]:
        """Verifies, decrypts, and updates trust based on channel response."""
        t_start = time.perf_counter()
        sender_id = frame.get("sender_id")
        self.messages_received += 1

        ok, payload, err = self.secure_channel.verify_and_decrypt(frame)
        if not ok:
            self.packets_dropped += 1
            if "Replay" in (err or ""):
                trust_engine.record_infraction(sender_id, "REPLAY")
            elif "Tamper" in (err or ""):
                trust_engine.record_infraction(sender_id, "FORGERY")
            else:
                trust_engine.record_direct_interaction(sender_id, success=False)
            self.cpu_time_ms += (time.perf_counter() - t_start) * 1000.0
            return False, None, err

        trust_engine.record_direct_interaction(sender_id, success=True)
        self.cpu_time_ms += (time.perf_counter() - t_start) * 1000.0
        return True, payload, None

    def get_status(self) -> dict:
        return {
            "node_id": self.node_id,
            "behavior": self.behavior.value,
            "battery_level": round(self.battery_level, 2),
            "cpu_time_ms": round(self.cpu_time_ms, 2),
            "memory_used_bytes": self.memory_used_bytes,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "packets_dropped": self.packets_dropped,
            "tx_counter": self.tx_counter,
            "public_key": self.pk_hex[:16] + "..."
        }
