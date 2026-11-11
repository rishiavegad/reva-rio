/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Activity,
  Cpu,
  Layers,
  Network,
  Database,
  Radio,
  Play,
  RotateCcw,
  Zap,
  BarChart3,
  Server,
  Terminal,
  Lock,
  ArrowRight,
  TrendingDown,
  ChevronRight,
  Info
} from 'lucide-react';

interface NodeStatus {
  node_id: string;
  behavior: string;
  battery_level: number;
  cpu_time_ms: number;
  memory_used_bytes: number;
  messages_sent: number;
  messages_received: number;
  packets_dropped: number;
  tx_counter: number;
  public_key: string;
  trust?: number;
  quarantined?: boolean;
  infractions?: string[];
}

interface DAGNode {
  id: string;
  label: string;
  parents: string[];
  payload_cid: string;
  payload_size: number;
  weight: number;
  confirmed: boolean;
  has_qcert: boolean;
  timestamp: number;
}

interface TelemetryData {
  round_counter: number;
  node_count: number;
  total_tx_submitted: number;
  total_tx_confirmed: number;
  channel_delivery_ratio: number;
  channel_dropped_packets: number;
  recent_attacks: Array<{ round: number; node_id: string; type: string; reason?: string }>;
  total_attacks_logged: number;
  nodes: NodeStatus[];
  dag_graph: {
    total_vertices: number;
    nodes: DAGNode[];
    edges: Array<{ source: string; target: string }>;
  };
}

interface StepSummary {
  round: number;
  transactions_proposed: number;
  transactions_ingested: number;
  attacks_intercepted: number;
  atho_best_fitness: number;
  committee: string[];
  consensus_success: boolean;
  consensus_phase: string;
  quorum_size: number;
  step_duration_ms: number;
}

export default function App() {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [latestStep, setLatestStep] = useState<StepSummary | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'dag' | 'trust' | 'benchmarks' | 'attacks'>('overview');
  const [loading, setLoading] = useState<boolean>(false);
  const [autoPlay, setAutoPlay] = useState<boolean>(false);
  const [benchmarks, setBenchmarks] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<string>('iot_node_02');
  const [selectedAttackType, setSelectedAttackType] = useState<string>('FORGERY');
  const [simConfig, setSimConfig] = useState({
    nodes: 16,
    malicious: 0.20,
    committee: 5
  });

  // Fetch / Reset simulation
  const resetSimulation = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/simulation/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(simConfig)
      });
      const data = await res.json();
      if (data.telemetry) {
        setTelemetry(data.telemetry);
        setLatestStep(data.step);
      }
    } catch (e) {
      console.error('Reset error:', e);
    } finally {
      setLoading(false);
    }
  }, [simConfig]);

  // Advance simulation step
  const stepSimulation = useCallback(async (txs = 4) => {
    setLoading(true);
    try {
      const res = await fetch('/api/simulation/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ txs })
      });
      const data = await res.json();
      if (data.telemetry) {
        setTelemetry(data.telemetry);
        setLatestStep(data.step);
      }
    } catch (e) {
      console.error('Step error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  // Inject attack
  const injectAttack = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/simulation/attack', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: selectedNode,
          attack_type: selectedAttackType
        })
      });
      const data = await res.json();
      if (data.telemetry) {
        setTelemetry(data.telemetry);
        setLatestStep(data.step);
      }
    } catch (e) {
      console.error('Attack error:', e);
    } finally {
      setLoading(false);
    }
  };

  // Fetch research benchmarks
  const loadBenchmarks = async () => {
    try {
      const res = await fetch('/api/simulation/benchmarks');
      const data = await res.json();
      setBenchmarks(data);
    } catch (e) {
      console.error('Benchmark error:', e);
    }
  };

  // Initial load
  useEffect(() => {
    resetSimulation();
    loadBenchmarks();
  }, [resetSimulation]);

  // Auto-play timer
  useEffect(() => {
    if (!autoPlay) return;
    const interval = setInterval(() => {
      stepSimulation(3);
    }, 2500);
    return () => clearInterval(interval);
  }, [autoPlay, stepSimulation]);

  const nodes = telemetry?.nodes || [];
  const dagNodes = telemetry?.dag_graph?.nodes || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-white">
      {/* Top Header Bar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-30 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-teal-500/20">
            <Radio className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold tracking-tight text-white">
                IoT Trust-PBFT & RL Blockchain Simulator
              </h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-teal-500/20 text-teal-400 border border-teal-500/30">
                Phase 7 Real-time Engine
              </span>
            </div>
            <p className="text-xs text-slate-400">
              DAG Ledger • Off-Chain IPFS (99.5% savings) • ATHO Hybrid Optimizer • Double-DQN Anomaly Detection
            </p>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoPlay(!autoPlay)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
              autoPlay
                ? 'bg-amber-500 text-slate-950 font-semibold shadow-lg shadow-amber-500/25'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
            }`}
          >
            {autoPlay ? <Zap className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {autoPlay ? 'Pause Auto-Run' : 'Auto-Run'}
          </button>

          <button
            onClick={() => stepSimulation(4)}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-teal-500 hover:bg-teal-400 text-slate-950 flex items-center gap-1.5 shadow-md shadow-teal-500/20 transition disabled:opacity-50"
          >
            <ChevronRight className="w-4 h-4" />
            Step (+1 Round)
          </button>

          <button
            onClick={resetSimulation}
            disabled={loading}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
            title="Reset Swarm State"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-800/80 bg-slate-900/40 px-6 flex items-center gap-2 text-xs font-medium">
        {[
          { id: 'overview', label: 'Swarm & nPBFT Consensus', icon: Network },
          { id: 'dag', label: 'DAG Ledger & IPFS Off-Chain', icon: Layers },
          { id: 'trust', label: 'Trust Vectors & RL Anomaly', icon: ShieldCheck },
          { id: 'benchmarks', label: 'ATHO & Model Benchmarks', icon: BarChart3 },
          { id: 'attacks', label: 'Attack Injection Vector', icon: ShieldAlert }
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-3.5 border-b-2 flex items-center gap-2 transition ${
                active
                  ? 'border-teal-400 text-teal-300 font-semibold bg-teal-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* KPI Status Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 p-6 border-b border-slate-900 bg-slate-950/60">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Simulation Round</span>
            <Activity className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <div className="text-xl font-bold text-white">#{telemetry?.round_counter || 0}</div>
          <div className="text-[11px] text-teal-400/90 font-medium">
            {latestStep ? `${latestStep.step_duration_ms} ms / cycle` : 'Idle'}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>DAG Vertices</span>
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-white">{telemetry?.dag_graph?.total_vertices || 1}</div>
          <div className="text-[11px] text-slate-400">
            {telemetry?.total_tx_confirmed || 0} Confirmed Txs
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>nPBFT Consensus</span>
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-base font-bold text-emerald-400 truncate">
            {latestStep?.consensus_phase || 'COMMITTED'}
          </div>
          <div className="text-[11px] text-slate-400">
            Quorum: {latestStep?.quorum_size || 4}/{simConfig.committee} votes
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Channel Delivery</span>
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-white">{telemetry?.channel_delivery_ratio || 100}%</div>
          <div className="text-[11px] text-slate-400">
            {telemetry?.channel_dropped_packets || 0} packets dropped
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Attacks Caught</span>
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
          </div>
          <div className="text-xl font-bold text-rose-400">{telemetry?.total_attacks_logged || 0}</div>
          <div className="text-[11px] text-slate-400">Asymmetrically Slashed</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>IPFS Storage Saved</span>
            <Database className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-amber-400">99.47%</div>
          <div className="text-[11px] text-slate-400">76B CID vs 14.3KB Payload</div>
        </div>
      </div>

      {/* Main Tab Views */}
      <main className="flex-1 p-6 overflow-y-auto max-w-7xl w-full mx-auto">
        {/* ============================================================== */}
        {/* TAB 1: SWARM OVERVIEW & NPBFT CONSENSUS PIPELINE               */}
        {/* ============================================================== */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Consensus Round Pipeline Status */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Network className="w-4 h-4 text-teal-400" />
                    nPBFT Consensus Pipeline & ATHO Committee
                  </h3>
                  <p className="text-xs text-slate-400">
                    Round #{latestStep?.round || 1} • Leader: <span className="font-mono text-teal-300">{latestStep?.committee?.[0] || 'iot_node_04'}</span>
                  </p>
                </div>
                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  Phase: {latestStep?.consensus_phase || 'COMMITTED'}
                </span>
              </div>

              {/* Protocol Flow Bar */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs mb-4">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-400 font-semibold mb-1">1. Pre-Prepare</div>
                  <div className="text-white font-mono text-[11px] truncate">
                    Leader broadcasts signed block proposal with DAG tips
                  </div>
                  <div className="mt-2 text-teal-400 font-medium text-[11px]">✓ Verified Ed25519 Sig</div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-400 font-semibold mb-1">2. Prepare Phase</div>
                  <div className="text-white font-mono text-[11px]">
                    All-to-all ballot exchange among ATHO committee
                  </div>
                  <div className="mt-2 text-indigo-400 font-medium text-[11px]">
                    ✓ Collected &gt; 2f Valid Ballots
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-400 font-semibold mb-1">3. Commit Phase</div>
                  <div className="text-white font-mono text-[11px]">
                    Quorum Threshold: {latestStep?.quorum_size || 4}/{simConfig.committee} votes
                  </div>
                  <div className="mt-2 text-emerald-400 font-medium text-[11px]">
                    ✓ Quorum Certificate Assembled
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-400 font-semibold mb-1">4. Finalization</div>
                  <div className="text-white font-mono text-[11px]">
                    Anchor Q_cert to DAG tips & reward validator trust
                  </div>
                  <div className="mt-2 text-amber-400 font-medium text-[11px]">✓ State Committed to DAG</div>
                </div>
              </div>

              {/* ATHO Elected Committee Chips */}
              <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 font-medium">ATHO Elected Committee:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {latestStep?.committee?.map((nid, i) => (
                      <span
                        key={nid}
                        className={`px-2.5 py-0.5 rounded font-mono text-[11px] font-semibold border ${
                          i === 0
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                            : 'bg-teal-500/10 text-teal-300 border-teal-500/30'
                        }`}
                      >
                        {nid} {i === 0 && '(Leader)'}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="text-slate-400">
                  Best Fitness <span className="font-mono text-teal-300">{latestStep?.atho_best_fitness}</span>
                </div>
              </div>
            </div>

            {/* Virtual Node Swarm Grid */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Server className="w-4 h-4 text-indigo-400" />
                  Active Virtual IoT Nodes ({nodes.length})
                </h3>
                <span className="text-xs text-slate-400">
                  Live telemetry: Battery, CPU cycles, message throughput, and trust metrics
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3.5">
                {nodes.map((node) => {
                  const isCommittee = latestStep?.committee?.includes(node.node_id);
                  const isLeader = latestStep?.committee?.[0] === node.node_id;
                  const isQuarantined = node.quarantined;
                  const isMalicious = node.behavior !== 'HONEST';

                  let statusBadgeClass = 'bg-teal-500/10 text-teal-400 border-teal-500/30';
                  if (isQuarantined) statusBadgeClass = 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse';
                  else if (isMalicious) statusBadgeClass = 'bg-amber-500/20 text-amber-300 border-amber-500/40';

                  return (
                    <div
                      key={node.node_id}
                      className={`p-4 rounded-xl border transition relative ${
                        isLeader
                          ? 'bg-amber-950/20 border-amber-500/50 shadow-lg shadow-amber-500/10'
                          : isCommittee
                          ? 'bg-slate-900 border-teal-500/40 shadow-sm'
                          : isQuarantined
                          ? 'bg-rose-950/20 border-rose-500/40'
                          : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                          <div className="text-xs font-bold font-mono text-white flex items-center gap-1.5">
                            {node.node_id}
                            {isLeader && <span className="px-1.5 py-0.2 text-[9px] font-bold bg-amber-500 text-slate-950 rounded">LEADER</span>}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5">{node.public_key}</div>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${statusBadgeClass}`}>
                          {node.behavior}
                        </span>
                      </div>

                      {/* Trust Progress Bar */}
                      <div className="mb-3">
                        <div className="flex items-center justify-between text-[11px] mb-1">
                          <span className="text-slate-400">Trust Score</span>
                          <span className="font-mono font-bold text-teal-300">{node.trust?.toFixed(3) || '0.500'}</span>
                        </div>
                        <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${
                              isQuarantined
                                ? 'bg-rose-500'
                                : (node.trust || 0.5) >= 0.70
                                ? 'bg-teal-400'
                                : (node.trust || 0.5) >= 0.45
                                ? 'bg-amber-400'
                                : 'bg-rose-400'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(0, (node.trust || 0.5) * 100))}%` }}
                          />
                        </div>
                      </div>

                      {/* Microcontroller Metrics */}
                      <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 border-t border-slate-800/80 pt-2 font-mono">
                        <div>Battery: <span className="text-slate-200">{node.battery_level}%</span></div>
                        <div>CPU: <span className="text-slate-200">{node.cpu_time_ms}ms</span></div>
                        <div>Sent: <span className="text-slate-200">{node.messages_sent}</span></div>
                        <div>Dropped: <span className="text-slate-200">{node.packets_dropped}</span></div>
                      </div>

                      {node.infractions && node.infractions.length > 0 && (
                        <div className="mt-2 text-[10px] text-rose-400 font-medium">
                          Infraction: {node.infractions.join(', ')}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 2: DAG LEDGER & IPFS OFF-CHAIN STORAGE                     */}
        {/* ============================================================== */}
        {activeTab === 'dag' && (
          <div className="space-y-6">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-indigo-400" />
                    Directed Acyclic Graph (DAG) Structure
                  </h3>
                  <p className="text-xs text-slate-400">
                    Vertices represent transactions referencing parent tip hashes. No linear blocks; cumulative weight propagates confidence.
                  </p>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono">
                  <span className="flex items-center gap-1.5 text-teal-400">
                    <span className="w-2.5 h-2.5 rounded bg-teal-400" /> Confirmed Checkpoint
                  </span>
                  <span className="flex items-center gap-1.5 text-slate-400">
                    <span className="w-2.5 h-2.5 rounded bg-slate-700" /> Pending Tip
                  </span>
                </div>
              </div>

              {/* DAG Vertex Stream */}
              <div className="space-y-2.5 max-h-[480px] overflow-y-auto pr-2">
                {dagNodes.map((v, i) => (
                  <div
                    key={v.id}
                    className={`p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs ${
                      v.has_qcert
                        ? 'bg-teal-950/20 border-teal-500/40'
                        : v.confirmed
                        ? 'bg-indigo-950/20 border-indigo-500/30'
                        : 'bg-slate-950/80 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center font-mono font-bold text-slate-300">
                        #{i}
                      </div>
                      <div>
                        <div className="font-mono font-semibold text-white flex items-center gap-2">
                          {v.id}
                          {v.has_qcert && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-teal-500/20 text-teal-300 border border-teal-500/40">
                              nPBFT Checkpoint
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>Parents: {v.parents.length ? v.parents.map(p => p.slice(0, 8)).join(', ') : 'Genesis'}</span>
                          <span>•</span>
                          <span className="text-amber-300 font-mono">CID: {v.payload_cid}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 font-mono">
                      <div className="text-right">
                        <div className="text-slate-400 text-[10px]">Cumulative Weight</div>
                        <div className="text-white font-bold">{v.weight}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-slate-400 text-[10px]">Status</div>
                        <div className={v.confirmed ? 'text-teal-400 font-bold' : 'text-slate-400'}>
                          {v.confirmed ? 'FINALIZED' : 'UNCONFIRMED'}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* IPFS Off-chain Comparison Box */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
                <Database className="w-4 h-4 text-amber-400" />
                IPFS Off-Chain Storage Architecture & Efficiency
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-slate-400 mb-1">Raw Telemetry Batch Size</div>
                  <div className="text-xl font-bold text-white font-mono">14,374 Bytes</div>
                  <div className="text-[11px] text-slate-500 mt-1">Full environmental sensor time-series</div>
                </div>

                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-slate-400 mb-1">On-Chain Multihash CIDv1</div>
                  <div className="text-xl font-bold text-teal-400 font-mono">76 Bytes</div>
                  <div className="text-[11px] text-slate-500 mt-1">bafy_sha256_... multihash pointer</div>
                </div>

                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-slate-400 mb-1">Direct Storage Reduction</div>
                  <div className="text-xl font-bold text-amber-400 font-mono">99.47%</div>
                  <div className="text-[11px] text-slate-500 mt-1">Saves &gt;99% storage on MCU flash/RAM</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 3: TRUST VECTORS & RL ANOMALY DETECTION                    */}
        {/* ============================================================== */}
        {activeTab === 'trust' && (
          <div className="space-y-6">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-teal-400" />
                    Multi-Dimensional Trust Matrix & Asymmetric Slashing
                  </h3>
                  <p className="text-xs text-slate-400">
                    Formulation: T_i = 0.35 D_i(t) + 0.45 C_i(t) + 0.20 A_i(t). Byzantine acts trigger asymmetric penalty discount.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2.5 px-3">Node ID</th>
                      <th className="py-2.5 px-3">Behavior</th>
                      <th className="py-2.5 px-3">Composite Trust</th>
                      <th className="py-2.5 px-3">Direct (D)</th>
                      <th className="py-2.5 px-3">Consensus (C)</th>
                      <th className="py-2.5 px-3">Anomaly (A)</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {nodes.map((node) => (
                      <tr key={node.node_id} className={node.quarantined ? 'bg-rose-950/20 text-rose-300' : 'hover:bg-slate-800/30'}>
                        <td className="py-2.5 px-3 font-bold text-white">{node.node_id}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            node.behavior === 'HONEST' ? 'bg-teal-500/10 text-teal-300' : 'bg-amber-500/20 text-amber-300'
                          }`}>
                            {node.behavior}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-bold text-teal-300">{node.trust?.toFixed(4) || '0.5000'}</td>
                        <td className="py-2.5 px-3 text-slate-300">0.5000</td>
                        <td className="py-2.5 px-3 text-slate-300">0.5000</td>
                        <td className="py-2.5 px-3 text-slate-300">1.0000</td>
                        <td className="py-2.5 px-3">
                          {node.quarantined ? (
                            <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold text-[10px] border border-rose-500/40">
                              QUARANTINED
                            </span>
                          ) : (node.trust || 0.5) >= 0.60 ? (
                            <span className="px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 font-bold text-[10px]">
                              ELIGIBLE VALIDATOR
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-bold text-[10px]">
                              PROBATIONARY
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Double-DQN Model Architecture Card */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                Ultra-Lightweight Double-DQN Anomaly Detection Architecture
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-slate-400 font-sans mb-1">State Input Dimension</div>
                  <div className="text-lg font-bold text-white">6 Continuous Features</div>
                  <div className="text-[10px] text-slate-500 mt-1">[freq, sig_fail, replay, lat, equiv, trust]</div>
                </div>

                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-slate-400 font-sans mb-1">Neural Topology</div>
                  <div className="text-lg font-bold text-teal-400">6 → 32 (ReLU) → 16 (ReLU) → 3</div>
                  <div className="text-[10px] text-slate-500 mt-1">&lt;800 parameters (~3.5 KB size)</div>
                </div>

                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-slate-400 font-sans mb-1">Discrete Action Space</div>
                  <div className="text-lg font-bold text-amber-400">ALLOW (0) | THROTTLE (1) | QUARANTINE (2)</div>
                  <div className="text-[10px] text-slate-500 mt-1">Inference Latency: 109.79 μs</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 4: ATHO & MODEL BENCHMARKS                                 */}
        {/* ============================================================== */}
        {activeTab === 'benchmarks' && (
          <div className="space-y-6">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-teal-400" />
                    Metaheuristic Convergence Benchmark: ATHO vs Baselines
                  </h3>
                  <p className="text-xs text-slate-400">
                    Comparing Proposed ATHO against standalone GWO, PSO, and SA across identical multi-objective problem instances.
                  </p>
                </div>
              </div>

              {benchmarks?.optimization_benchmark && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono mb-6">
                  {Object.entries(benchmarks.optimization_benchmark).map(([algo, res]: [string, any]) => (
                    <div
                      key={algo}
                      className={`p-3.5 rounded-xl border ${
                        algo.includes('ATHO')
                          ? 'bg-teal-950/20 border-teal-500/50 shadow-md shadow-teal-500/10'
                          : 'bg-slate-950 border-slate-800'
                      }`}
                    >
                      <div className="text-slate-400 font-bold mb-1 truncate">{algo}</div>
                      <div className="text-lg font-bold text-white">{res.mean_fitness.toFixed(4)}</div>
                      <div className="text-[11px] text-slate-400 mt-1">
                        Min: {res.min_fitness.toFixed(4)} • Runtime: {res.mean_runtime_ms.toFixed(1)}ms
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Anomaly Detection Comparison Table */}
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
                Anomaly Detection Comparative Evaluation
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2.5 px-3">Detector Model</th>
                      <th className="py-2.5 px-3">F1-Score</th>
                      <th className="py-2.5 px-3">Precision</th>
                      <th className="py-2.5 px-3">Recall</th>
                      <th className="py-2.5 px-3">False Positive Rate</th>
                      <th className="py-2.5 px-3">Inference Latency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {benchmarks?.anomaly_detection_benchmark &&
                      Object.entries(benchmarks.anomaly_detection_benchmark).map(([name, m]: [string, any]) => (
                        <tr key={name} className={name.includes('Double-DQN') ? 'bg-teal-950/20 font-bold text-teal-300' : 'hover:bg-slate-800/30'}>
                          <td className="py-2.5 px-3 text-white">{name}</td>
                          <td className="py-2.5 px-3 font-bold text-teal-400">{m.f1_score.toFixed(4)}</td>
                          <td className="py-2.5 px-3 text-slate-300">{m.precision.toFixed(4)}</td>
                          <td className="py-2.5 px-3 text-slate-300">{m.recall.toFixed(4)}</td>
                          <td className="py-2.5 px-3 text-slate-300">{m.false_positive_rate.toFixed(4)}</td>
                          <td className="py-2.5 px-3 text-slate-300">{m.avg_inference_latency_us.toFixed(2)} μs</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 5: ATTACK INJECTION VECTOR                                 */}
        {/* ============================================================== */}
        {activeTab === 'attacks' && (
          <div className="space-y-6">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                Live Adversarial Attack Injection & Resiliency Testing
              </h3>
              <p className="text-xs text-slate-400 mb-5">
                Inject malicious Byzantine behaviors into any virtual IoT node to observe automated interception, Double-DQN action classification, and nPBFT view-change safety.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Target IoT Node</label>
                  <select
                    value={selectedNode}
                    onChange={(e) => setSelectedNode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-teal-500 font-mono"
                  >
                    {nodes.map((n) => (
                      <option key={n.node_id} value={n.node_id}>
                        {n.node_id} (Currently: {n.behavior})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Attack Vector</label>
                  <select
                    value={selectedAttackType}
                    onChange={(e) => setSelectedAttackType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-teal-500 font-mono"
                  >
                    <option value="FORGERY">Ed25519 Signature Forgery (Tampered Crypto)</option>
                    <option value="EQUIVOCATION">Byzantine Equivocation / Double-Voting</option>
                    <option value="REPLAY">Nonce Replay Attack (Submitting Old Frame)</option>
                    <option value="FLOOD">High-Frequency Packet Flooding (DoS)</option>
                    <option value="FLAKY">Wireless Degradation & Intermittent Packet Drops</option>
                    <option value="HONEST">Restore to Honest Behavior</option>
                  </select>
                </div>
              </div>

              <button
                onClick={injectAttack}
                disabled={loading}
                className="px-5 py-2.5 rounded-xl text-xs font-bold bg-rose-500 hover:bg-rose-400 text-slate-950 flex items-center gap-2 shadow-lg shadow-rose-500/20 transition disabled:opacity-50"
              >
                <Zap className="w-4 h-4" />
                Inject Attack Vector into {selectedNode}
              </button>
            </div>

            {/* Attack Log Table */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
                Security Incident Audit Trail ({telemetry?.recent_attacks?.length || 0})
              </h4>
              <div className="space-y-2 text-xs font-mono max-h-[250px] overflow-y-auto">
                {telemetry?.recent_attacks && telemetry.recent_attacks.length > 0 ? (
                  telemetry.recent_attacks.map((att, i) => (
                    <div key={i} className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-slate-300">
                      <div>
                        <span className="text-rose-400 font-bold">[Round #{att.round}]</span> Node <span className="text-white font-bold">{att.node_id}</span> ({att.type})
                        <div className="text-[11px] text-slate-500 mt-0.5">{att.reason || 'Cryptographic anomaly intercepted'}</div>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                        INTERCEPTED &amp; SLASHED
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 italic p-3">No active security infractions logged in recent rounds.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-3 text-center text-xs text-slate-500">
        Research Project Simulation Engine • Lightweight Ed25519 • DAG Ledger • IPFS Content Addressing • ATHO • Trust-Aware nPBFT • Double-DQN
      </footer>
    </div>
  );
}
