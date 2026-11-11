/**
 * Full-Stack Express Server with Vite Middleware
 * Bridges HTTP REST endpoints to the Python IoT Research Simulator Engine.
 */

import express from 'express';
import { createServer as createViteServer } from 'vite';
import { execFile } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(express.json());

// Helper function to invoke Python API bridge
function runPythonBridge(args: string[]): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonScript = path.resolve(__dirname, 'core/api_bridge.py');
    execFile('python3', [pythonScript, ...args], { cwd: __dirname }, (error, stdout, stderr) => {
      if (error) {
        console.error('Python bridge error:', stderr || error.message);
        return reject(new Error(stderr || error.message));
      }
      try {
        const json = JSON.parse(stdout.trim());
        resolve(json);
      } catch (parseErr) {
        console.error('Failed to parse stdout:', stdout);
        reject(parseErr);
      }
    });
  });
}

// ---------------- API Endpoints ----------------

app.get('/api/status', (req, res) => {
  res.json({
    framework: 'IoT P2P Trust-PBFT & RL Blockchain Framework',
    status: 'ONLINE',
    version: '1.0.0',
    crypto: 'RFC 8032 Ed25519 & SHA-256',
    consensus: 'Trust-Aware nPBFT',
    optimizer: 'ATHO (Adaptive Trust-Aware Hybrid Optimizer)',
    anomaly_detection: 'Double-DQN'
  });
});

app.post('/api/simulation/reset', async (req, res) => {
  try {
    const nodes = req.body.nodes || 16;
    const malicious = req.body.malicious || 0.20;
    const committee = req.body.committee || 5;
    const result = await runPythonBridge([
      'reset',
      '--nodes', String(nodes),
      '--malicious', String(malicious),
      '--committee', String(committee)
    ]);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/simulation/step', async (req, res) => {
  try {
    const txs = req.body.txs || 4;
    const result = await runPythonBridge(['step', '--txs', String(txs)]);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/simulation/attack', async (req, res) => {
  try {
    const nodeId = req.body.node_id || 'iot_node_02';
    const attackType = req.body.attack_type || 'FORGERY';
    const result = await runPythonBridge([
      'attack',
      '--node_id', String(nodeId),
      '--attack_type', String(attackType)
    ]);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/simulation/benchmarks', async (req, res) => {
  try {
    const result = await runPythonBridge(['benchmarks']);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// ---------------- Vite Middleware / Static Serve ----------------

async function setupServer() {
  const isDev = process.env.NODE_ENV !== 'production';

  if (isDev) {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.resolve(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[IoT Framework] Server running at http://0.0.0.0:${PORT}`);
  });
}

setupServer();
