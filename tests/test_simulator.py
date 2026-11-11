"""
Unit and Integration Tests for Virtual IoT Node Simulator and Network Coordinator
"""

import unittest
from core.virtual_node import VirtualIoTNode, NodeBehavior
from core.network_simulator import IoTNetworkSimulator, VirtualChannel
from core.ipfs_client import IPFSAdapter
from core.dag_ledger import DAGLedger

class TestVirtualNodeAndSimulator(unittest.TestCase):
    def setUp(self):
        self.ipfs = IPFSAdapter()
        self.dag = DAGLedger()
        self.honest_node = VirtualIoTNode(node_id="test_honest", behavior=NodeBehavior.HONEST)
        self.tamper_node = VirtualIoTNode(node_id="test_tamper", behavior=NodeBehavior.TAMPER_ATTACKER)

    def test_node_sensing_and_resource_metering(self):
        initial_battery = self.honest_node.battery_level
        initial_cpu = self.honest_node.cpu_time_ms
        sensor_data = self.honest_node.read_sensors()

        self.assertIn("temperature_c", sensor_data)
        self.assertIn("relative_humidity_pct", sensor_data)
        self.assertLess(self.honest_node.battery_level, initial_battery, "Battery should decrease with sensing")
        self.assertGreater(self.honest_node.cpu_time_ms, initial_cpu, "CPU time should be recorded")

    def test_transaction_proposal_creation(self):
        # Honest node proposal
        ok, prop, err = self.honest_node.create_transaction_proposal(self.ipfs, self.dag)
        self.assertTrue(ok)
        self.assertIsNotNone(prop)
        self.assertIn("parents", prop)
        self.assertIn("payload_cid", prop)
        self.assertTrue(prop["payload_cid"].startswith("bafy_sha256_"))
        
        # Tamper attacker proposal should produce invalid signature
        tok, tprop, terr = self.tamper_node.create_transaction_proposal(self.ipfs, self.dag)
        self.assertTrue(tok)
        self.assertEqual(tprop["signature"], "00" * 64, "Tamper node must generate forged zero signature")

    def test_virtual_channel_transmission(self):
        channel = VirtualChannel(mean_delay_ms=10.0, jitter_ms=2.0, packet_loss_rate=0.0)
        delivered, delay = channel.transmit({}, self.honest_node)
        self.assertTrue(delivered)
        self.assertGreaterEqual(delay, 1.0)
        self.assertEqual(channel.total_transmitted, 1)

    def test_end_to_end_network_simulation_steps(self):
        # 15 nodes, 20% malicious ratio
        sim = IoTNetworkSimulator(node_count=15, malicious_ratio=0.20, committee_size=5, seed=42)
        self.assertEqual(len(sim.nodes), 15)

        # Run 3 simulation steps
        for step_idx in range(1, 4):
            summary = sim.run_simulation_step(transactions_per_step=4)
            self.assertEqual(summary["round"], step_idx)
            self.assertEqual(len(summary["committee"]), 5)
            self.assertIn("consensus_phase", summary)
            print(f"\n[SIMULATION STEP {step_idx}] Tx Proposed: {summary['transactions_proposed']}, "
                  f"Ingested: {summary['transactions_ingested']}, Attacks: {summary['attacks_intercepted']}, "
                  f"Consensus: {summary['consensus_phase']}, Duration: {summary['step_duration_ms']} ms")

        # Telemetry verification
        telemetry = sim.get_network_telemetry()
        self.assertGreater(telemetry["total_tx_submitted"], 0)
        self.assertEqual(len(telemetry["nodes"]), 15)
        self.assertGreater(len(telemetry["dag_graph"]["nodes"]), 1)

if __name__ == "__main__":
    unittest.main()
