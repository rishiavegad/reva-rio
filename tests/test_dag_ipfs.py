"""
Unit and Integration Tests for DAG Ledger, IPFS Storage, and Secure Channel
"""

import unittest
import time
from core.crypto_primitives import generate_keypair, sign_message
from core.ipfs_client import IPFSAdapter
from core.dag_ledger import DAGLedger
from core.secure_channel import SecureChannel

class TestDAGAndIPFS(unittest.TestCase):
    def setUp(self):
        self.ipfs = IPFSAdapter()
        self.ledger = DAGLedger(confirmation_weight_threshold=3)
        self.sk, self.pk = generate_keypair()
        self.pk_hex = self.pk.hex()

    def test_ipfs_storage_and_reduction(self):
        # Generate 15 KB simulated sensor batch payload
        large_payload = {
            "sensor_readings": [
                {"sensor_id": f"s_{i}", "temp": 24.5 + i * 0.1, "humidity": 60.0 + i * 0.05}
                for i in range(250)
            ],
            "firmware_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
            "timestamp": time.time()
        }
        cid, raw_size, ref_size = self.ipfs.upload_payload(large_payload)
        self.assertIsNotNone(cid)
        self.assertGreater(raw_size, 5000, "Raw payload should be multi-kilobyte")
        self.assertLess(ref_size, 100, "CID reference size should be under 100 bytes")

        # Measure storage savings
        savings = self.ipfs.calculate_storage_savings(raw_size, ref_size)
        print(f"\n[IPFS STORAGE EFFICIENCY] Raw: {raw_size} bytes -> On-Chain CID: {ref_size} bytes -> Savings: {savings:.2f}%")
        self.assertGreater(savings, 95.0, "Storage savings must exceed 95%")

        # Verify exact retrieval
        retrieved_bytes = self.ipfs.retrieve_payload(cid)
        self.assertIsNotNone(retrieved_bytes)
        import json
        retrieved_obj = json.loads(retrieved_bytes.decode('utf-8'))
        self.assertEqual(len(retrieved_obj["sensor_readings"]), 250)

    def test_dag_append_and_weight_propagation(self):
        tips = self.ledger.get_tips()
        self.assertEqual(len(tips), 1)
        self.assertEqual(tips[0], self.ledger.genesis_id)

        # 1. Add Transaction 1 referencing Genesis
        cid1 = "bafy_sha256_mockdata11111111111111111111111111111111111111111111111"
        ts = time.time()
        canonical_str = f"{sorted(tips)}:{cid1}:120:{self.pk_hex}:1:{ts}"
        sig1 = sign_message(self.sk, canonical_str.encode('utf-8')).hex()

        ok, tx1_id, err = self.ledger.add_transaction(
            parents=tips,
            payload_cid=cid1,
            payload_size_bytes=120,
            sender_pubkey=self.pk_hex,
            nonce=1,
            timestamp=ts,
            signature=sig1
        )
        self.assertTrue(ok, f"Failed to add transaction: {err}")
        self.assertIn(tx1_id, self.ledger.vertices)
        
        # Genesis cumulative weight should have incremented to 2
        self.assertEqual(self.ledger.vertices[self.ledger.genesis_id].cumulative_weight, 2)

        # 2. Add Transaction 2 referencing Tx 1
        new_tips = self.ledger.get_tips()
        self.assertIn(tx1_id, new_tips)
        cid2 = "bafy_sha256_mockdata22222222222222222222222222222222222222222222222"
        ts2 = time.time() + 1.0
        canonical_str2 = f"{sorted([tx1_id])}:{cid2}:150:{self.pk_hex}:2:{ts2}"
        sig2 = sign_message(self.sk, canonical_str2.encode('utf-8')).hex()

        ok2, tx2_id, err2 = self.ledger.add_transaction(
            parents=[tx1_id],
            payload_cid=cid2,
            payload_size_bytes=150,
            sender_pubkey=self.pk_hex,
            nonce=2,
            timestamp=ts2,
            signature=sig2
        )
        self.assertTrue(ok2, f"Failed to add transaction 2: {err2}")
        
        # Tx1 weight is now 2, Genesis weight is now 3 (threshold reached -> confirmed)
        self.assertEqual(self.ledger.vertices[tx1_id].cumulative_weight, 2)
        self.assertEqual(self.ledger.vertices[self.ledger.genesis_id].cumulative_weight, 3)
        self.assertTrue(self.ledger.vertices[self.ledger.genesis_id].confirmed)

    def test_dag_cycle_prevention(self):
        # Attempt to insert a vertex whose parents form an illegal cycle
        tx_fake = "deadbeef" * 8
        is_safe = self.ledger.validate_acyclicity(tx_fake, [tx_fake])
        self.assertFalse(is_safe, "Self-referencing cycle must be detected and rejected")

    def test_secure_channel_confidentiality_and_anti_replay(self):
        node_a = SecureChannel(node_id="node_alpha")
        node_b = SecureChannel(node_id="node_beta")

        # Establish symmetric pairwise session via 32-byte master secret
        master_secret = b"PreSharedOrDiffieHellmanSecret32B"
        node_a.establish_session("node_beta", master_secret)
        node_b.establish_session("node_alpha", master_secret)

        # 1. Honest Encrypt and Decrypt
        test_payload = {"command": "ACTUATE_VALVE", "level": 90, "auth_pin": 4321}
        ok, frame, err = node_a.encrypt_and_frame("node_beta", "CONTROL_MSG", test_payload)
        self.assertTrue(ok)
        self.assertIsNotNone(frame)
        self.assertNotEqual(frame["ciphertext"], str(test_payload))

        # Decrypt at node B
        dec_ok, dec_payload, dec_err = node_b.verify_and_decrypt(frame)
        self.assertTrue(dec_ok, f"Decryption failed: {dec_err}")
        self.assertEqual(dec_payload["command"], "ACTUATE_VALVE")

        # 2. Anti-Replay Defense: Re-submitting the exact same frame must be rejected
        replay_ok, _, replay_err = node_b.verify_and_decrypt(frame)
        self.assertFalse(replay_ok, "Replayed frame with identical nonce must be rejected")
        self.assertIn("Replay detected", replay_err)

        # 3. Tamper Detection: Altering 1 character of ciphertext must fail HMAC verification
        tampered_frame = dict(frame)
        # Advance nonce to bypass replay check, but ciphertext tag won't match
        tampered_frame["nonce"] = 999
        tampered_frame["ciphertext"] = "ff" + tampered_frame["ciphertext"][2:]
        tamper_ok, _, tamper_err = node_b.verify_and_decrypt(tampered_frame)
        self.assertFalse(tamper_ok, "Tampered ciphertext must fail authentication")
        self.assertIn("Tamper detected", tamper_err)

if __name__ == "__main__":
    unittest.main()
