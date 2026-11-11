"""
Reinforcement Learning Anomaly Detection Engine for IoT Swarms
Implements:
1. Compact Double-DQN (Deep Q-Network) with Experience Replay
2. 6-dimensional continuous state space and 3 discrete mitigation policies (ALLOW, RATE_LIMIT, QUARANTINE)
3. Asymmetric reward matrix penalizing false positives and false negatives
4. Baseline comparison: Static Rule Threshold Detector & Statistical Distance Detector
5. Evaluation metrics: Precision, Recall, F1-score, False-Positive Rate, Detection Latency, and Memory Footprint
"""

import math
import random
import time
from typing import Dict, List, Tuple, Optional, Any

# =====================================================================
# Pure-Python Ultra-Lightweight Neural Network
# =====================================================================
class DenseLayer:
    def __init__(self, in_features: int, out_features: int, activation: str = "relu"):
        # He initialization
        scale = math.sqrt(2.0 / in_features)
        self.weights = [[random.gauss(0.0, scale) for _ in range(out_features)] for _ in range(in_features)]
        self.biases = [0.01 for _ in range(out_features)]
        self.activation = activation
        
        # Cache for backprop
        self.last_input: Optional[List[float]] = None
        self.last_linear: Optional[List[float]] = None
        self.last_output: Optional[List[float]] = None

    def forward(self, x: List[float]) -> List[float]:
        self.last_input = x[:]
        out = [0.0] * len(self.biases)
        for j in range(len(self.biases)):
            dot = sum(x[i] * self.weights[i][j] for i in range(len(x))) + self.biases[j]
            out[j] = dot

        self.last_linear = out[:]
        if self.activation == "relu":
            self.last_output = [max(0.0, val) for val in out]
        elif self.activation == "linear":
            self.last_output = out[:]
        return self.last_output

    def backward(self, d_out: List[float], lr: float = 0.005) -> List[float]:
        """Backpropagates gradient and updates weights using stochastic gradient descent."""
        # Gradient through activation
        d_linear = [0.0] * len(d_out)
        for j in range(len(d_out)):
            if self.activation == "relu":
                d_linear[j] = d_out[j] if self.last_linear[j] > 0 else 0.0
            else:
                d_linear[j] = d_out[j]

        # Compute gradient w.r.t input
        d_input = [0.0] * len(self.last_input)
        for i in range(len(self.last_input)):
            d_input[i] = sum(self.weights[i][j] * d_linear[j] for j in range(len(d_linear)))

        # Update weights and biases
        for i in range(len(self.last_input)):
            for j in range(len(d_linear)):
                grad = self.last_input[i] * d_linear[j]
                grad = max(-5.0, min(5.0, grad))  # gradient clipping
                self.weights[i][j] -= lr * grad

        for j in range(len(d_linear)):
            self.biases[j] -= lr * max(-5.0, min(5.0, d_linear[j]))

        return d_input

    def copy_weights_from(self, source: 'DenseLayer'):
        for i in range(len(self.weights)):
            for j in range(len(self.weights[0])):
                self.weights[i][j] = source.weights[i][j]
        for j in range(len(self.biases)):
            self.biases[j] = source.biases[j]

# =====================================================================
# Double-DQN Agent
# =====================================================================
class DoubleDQNAgent:
    def __init__(
        self,
        state_dim: int = 6,
        action_dim: int = 3,
        gamma: float = 0.95,
        lr: float = 0.008,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.992,
        buffer_capacity: int = 1000
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.lr = lr
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay

        # Online Network: 6 -> 32 (ReLU) -> 16 (ReLU) -> 3 (Linear)
        self.l1 = DenseLayer(6, 32, "relu")
        self.l2 = DenseLayer(32, 16, "relu")
        self.l3 = DenseLayer(16, 3, "linear")

        # Target Network for Double-DQN stability
        self.t_l1 = DenseLayer(6, 32, "relu")
        self.t_l2 = DenseLayer(32, 16, "relu")
        self.t_l3 = DenseLayer(16, 3, "linear")
        self.sync_target_network()

        # Experience Replay Buffer
        self.buffer: List[Tuple[List[float], int, float, List[float], bool]] = []
        self.buffer_capacity = buffer_capacity

    def sync_target_network(self):
        self.t_l1.copy_weights_from(self.l1)
        self.t_l2.copy_weights_from(self.l2)
        self.t_l3.copy_weights_from(self.l3)

    def forward_online(self, state: List[float]) -> List[float]:
        h1 = self.l1.forward(state)
        h2 = self.l2.forward(h1)
        return self.l3.forward(h2)

    def forward_target(self, state: List[float]) -> List[float]:
        h1 = self.t_l1.forward(state)
        h2 = self.t_l2.forward(h1)
        return self.t_l3.forward(h2)

    def select_action(self, state: List[float], eval_mode: bool = False) -> int:
        if not eval_mode and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        q_values = self.forward_online(state)
        return int(max(range(len(q_values)), key=lambda a: q_values[a]))

    def remember(self, state: List[float], action: int, reward: float, next_state: List[float], done: bool):
        if len(self.buffer) >= self.buffer_capacity:
            self.buffer.pop(0)
        self.buffer.append((state, action, reward, next_state, done))

    def train_step(self, batch_size: int = 16) -> float:
        if len(self.buffer) < batch_size:
            return 0.0

        batch = random.sample(self.buffer, batch_size)
        total_loss = 0.0

        for state, action, reward, next_state, done in batch:
            q_current = self.forward_online(state)
            
            # Double-DQN: target = r + gamma * Q_target(s', argmax Q_online(s', a))
            if done:
                target_val = reward
            else:
                next_online_q = self.forward_online(next_state)
                best_action = max(range(len(next_online_q)), key=lambda a: next_online_q[a])
                next_target_q = self.forward_target(next_state)
                target_val = reward + self.gamma * next_target_q[best_action]

            # Compute error for the chosen action
            error = q_current[action] - target_val
            total_loss += error ** 2

            # Backpropagate gradient for chosen action
            d_out = [0.0] * self.action_dim
            d_out[action] = 2.0 * error

            # Backward pass through online network
            d_h2 = self.l3.backward(d_out, lr=self.lr)
            d_h1 = self.l2.backward(d_h2, lr=self.lr)
            self.l1.backward(d_h1, lr=self.lr)

        # Decay exploration
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        return total_loss / batch_size

# =====================================================================
# Reward Function and Anomaly Evaluator
# =====================================================================
def compute_reward(true_label: str, action: int) -> float:
    """
    true_label: 'BENIGN', 'BURST', or 'BYZANTINE'
    action: 0 (ALLOW), 1 (RATE_LIMIT), 2 (QUARANTINE)
    """
    if true_label == "BYZANTINE":
        if action == 2:  # True Positive Quarantine
            return 10.0
        elif action == 1:
            return 2.0
        else:  # False Negative (Missed Attack)
            return -15.0
    elif true_label == "BURST":
        if action == 1:  # Appropriate Throttle
            return 3.0
        elif action == 0:
            return 0.5
        else:  # Unnecessary Quarantine
            return -6.0
    else:  # BENIGN
        if action == 0:  # True Negative
            return 1.0
        elif action == 1:  # Mild False Alarm
            return -2.0
        else:  # Severe False Alarm (Unfair Quarantine)
            return -12.0

# =====================================================================
# Baseline Detectors for Research Comparison
# =====================================================================
class ThresholdBaselineDetector:
    """Static Rule / Threshold-Based Baseline Detector."""
    def predict(self, state: List[float]) -> int:
        freq, sig_fail, replay, lat_ratio, equiv, trust = state
        if equiv > 0.5 or sig_fail > 0.40 or replay > 0.40 or trust < 0.35:
            return 2  # QUARANTINE
        if freq > 0.70 or lat_ratio > 2.5:
            return 1  # RATE_LIMIT
        return 0  # ALLOW

class StatisticalCentroidDetector:
    """Distance-to-Benign Centroid Baseline Detector."""
    def __init__(self):
        # Benign prototype: [low freq, 0 sig_fail, 0 replay, normal lat, 0 equiv, high trust]
        self.benign_centroid = [0.20, 0.00, 0.00, 1.00, 0.00, 0.85]

    def predict(self, state: List[float]) -> int:
        dist = math.sqrt(sum((s - c) ** 2 for s, c in zip(state, self.benign_centroid)))
        if dist > 1.2:
            return 2  # QUARANTINE
        elif dist > 0.6:
            return 1  # RATE_LIMIT
        return 0  # ALLOW

# =====================================================================
# Training & Benchmarking Harness
# =====================================================================
def generate_synthetic_observation(label: str) -> List[float]:
    """Generates a 6D feature vector for a specified behavioral label."""
    if label == "BENIGN":
        return [
            random.uniform(0.10, 0.40),  # freq
            0.0,                         # sig_fail
            0.0,                         # replay
            random.uniform(0.8, 1.2),    # lat_ratio
            0.0,                         # equiv
            random.uniform(0.70, 0.98)   # trust
        ]
    elif label == "BURST":
        return [
            random.uniform(0.75, 1.00),  # freq high
            0.0,
            0.0,
            random.uniform(1.8, 3.0),    # lat elevated
            0.0,
            random.uniform(0.55, 0.80)
        ]
    else:  # BYZANTINE
        attack_type = random.choice(["FORGERY", "REPLAY", "EQUIVOCATION"])
        if attack_type == "FORGERY":
            return [random.uniform(0.2, 0.6), random.uniform(0.7, 1.0), 0.0, random.uniform(1.0, 1.5), 0.0, random.uniform(0.1, 0.4)]
        elif attack_type == "REPLAY":
            return [random.uniform(0.3, 0.7), 0.0, random.uniform(0.8, 1.0), random.uniform(1.0, 1.5), 0.0, random.uniform(0.1, 0.4)]
        else:
            return [random.uniform(0.4, 0.8), 0.0, 0.0, random.uniform(1.0, 1.5), 1.0, random.uniform(0.1, 0.35)]

def train_dqn_agent(episodes: int = 150, seed: int = 42) -> DoubleDQNAgent:
    """Trains the Double-DQN anomaly agent with experience replay."""
    random.seed(seed)
    agent = DoubleDQNAgent(state_dim=6, action_dim=3)
    labels = ["BENIGN", "BENIGN", "BURST", "BYZANTINE"]

    for ep in range(episodes):
        label = random.choice(labels)
        state = generate_synthetic_observation(label)
        action = agent.select_action(state, eval_mode=False)
        reward = compute_reward(label, action)
        
        next_label = random.choice(labels)
        next_state = generate_synthetic_observation(next_label)
        done = True  # episodic anomaly classification

        agent.remember(state, action, reward, next_state, done)
        agent.train_step(batch_size=16)

        if (ep + 1) % 25 == 0:
            agent.sync_target_network()

    return agent

def evaluate_detector(detector_func, test_samples: List[Tuple[List[float], str]]) -> Dict[str, float]:
    """Evaluates a detector and computes Precision, Recall, F1, and FPR."""
    tp, fp, tn, fn = 0, 0, 0, 0
    t_start = time.perf_counter()

    for state, label in test_samples:
        pred_action = detector_func(state)
        # Binary classification for Byzantine attack: Positive = Action 2 (QUARANTINE)
        is_attack = (label == "BYZANTINE")
        pred_attack = (pred_action == 2)

        if is_attack and pred_attack:
            tp += 1
        elif (not is_attack) and pred_attack:
            fp += 1
        elif (not is_attack) and (not pred_attack):
            tn += 1
        elif is_attack and (not pred_attack):
            fn += 1

    elapsed_ms = (time.perf_counter() - t_start) * 1000.0
    avg_latency_us = (elapsed_ms / len(test_samples)) * 1000.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "avg_inference_latency_us": round(avg_latency_us, 2),
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn}
    }

def benchmark_anomaly_detectors(seed: int = 123) -> Dict[str, Any]:
    """Generates test set and compares Double-DQN against Threshold & Statistical baselines."""
    random.seed(seed)
    # Generate 300 test samples (out-of-sample data)
    test_set = []
    for _ in range(150):
        test_set.append((generate_synthetic_observation("BENIGN"), "BENIGN"))
    for _ in range(50):
        test_set.append((generate_synthetic_observation("BURST"), "BURST"))
    for _ in range(100):
        test_set.append((generate_synthetic_observation("BYZANTINE"), "BYZANTINE"))

    # Train Double-DQN
    dqn_agent = train_dqn_agent(episodes=180, seed=seed)
    threshold_detector = ThresholdBaselineDetector()
    stat_detector = StatisticalCentroidDetector()

    results = {
        "Double-DQN (Proposed)": evaluate_detector(lambda s: dqn_agent.select_action(s, eval_mode=True), test_set),
        "Rule Threshold Baseline": evaluate_detector(threshold_detector.predict, test_set),
        "Statistical Centroid Baseline": evaluate_detector(stat_detector.predict, test_set)
    }
    return results
