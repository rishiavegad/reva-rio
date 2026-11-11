"""
Secure P2P Channel and Authenticated Messaging for IoT Nodes
Implements:
1. Multi-layer cryptographic security at the transport boundary
2. Ephemeral session key derivation via HKDF (RFC 5869)
3. Authenticated Encryption with Associated Data (AEAD) via CTR + HMAC-SHA256
4. Monotonic nonce tracking for strict replay protection
5. Message integrity, authentication, and tamper detection
"""

import hashlib
import hmac
import secrets
import json
import time
from typing import Dict, Optional, Tuple, Any

from core.crypto_primitives import sha256_digest, compute_hmac

def hkdf_extract_and_expand(salt: bytes, ikm: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF (RFC 5869) key derivation using SHA-256."""
    if not salt:
        salt = bytes([0] * 32)
    # Extract
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    # Expand
    okm = b""
    t = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]

def _xor_cipher(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Lightweight stream cipher (Counter Mode using SHA-256 keystream generation)."""
    keystream = bytearray()
    block_counter = 0
    while len(keystream) < len(data):
        block_bytes = block_counter.to_bytes(4, 'big')
        h = hashlib.sha256(key + iv + block_bytes).digest()
        keystream.extend(h)
        block_counter += 1
    
    out = bytearray(len(data))
    for i in range(len(data)):
        out[i] = data[i] ^ keystream[i]
    return bytes(out)

class SecureChannel:
    def __init__(self, node_id: str):
        self.node_id = node_id
        # Tracking last seen nonce per peer for replay defense
        self.peer_last_nonces: Dict[str, int] = {}
        # Symmetric pairwise session keys derived via key exchange: peer_id -> key_bytes
        self.session_keys: Dict[str, bytes] = {}
        self.outbound_nonce_counter: int = 1

    def establish_session(self, peer_id: str, shared_secret: bytes):
        """Derives a pairwise 256-bit symmetric session key via HKDF."""
        salt = sha256_digest(f"{min(self.node_id, peer_id)}:{max(self.node_id, peer_id)}".encode('utf-8')).encode('utf-8')
        info = b"IoT-P2P-Secure-Channel-Session-Key"
        session_key = hkdf_extract_and_expand(salt, shared_secret, info, length=32)
        self.session_keys[peer_id] = session_key
        if peer_id not in self.peer_last_nonces:
            self.peer_last_nonces[peer_id] = 0

    def encrypt_and_frame(
        self,
        receiver_id: str,
        message_type: str,
        plaintext_payload: Any
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Encrypts plaintext_payload and packages into an authenticated P2P frame.
        """
        if receiver_id not in self.session_keys:
            return False, None, f"No established cryptographic session for peer {receiver_id}"

        session_key = self.session_keys[receiver_id]
        raw_bytes = json.dumps(plaintext_payload, sort_keys=True).encode('utf-8')

        # Generate 16-byte random IV
        iv = secrets.token_bytes(16)
        ciphertext = _xor_cipher(raw_bytes, session_key, iv)

        nonce = self.outbound_nonce_counter
        self.outbound_nonce_counter += 1
        timestamp = time.time()

        # Associated Data for authentication
        aad = f"{self.node_id}:{receiver_id}:{nonce}:{timestamp}:{message_type}".encode('utf-8')
        
        # Compute HMAC authentication tag over (IV + Ciphertext + AAD)
        tag = hmac.new(session_key, iv + ciphertext + aad, hashlib.sha256).hexdigest()

        frame = {
            "sender_id": self.node_id,
            "receiver_id": receiver_id,
            "nonce": nonce,
            "timestamp": timestamp,
            "message_type": message_type,
            "iv": iv.hex(),
            "ciphertext": ciphertext.hex(),
            "tag": tag
        }
        return True, frame, None

    def verify_and_decrypt(self, frame: dict) -> Tuple[bool, Optional[Any], Optional[str]]:
        """
        Verifies authentication tag, validates monotonic nonce to block replays, and decrypts.
        """
        sender_id = frame.get("sender_id")
        receiver_id = frame.get("receiver_id")
        nonce = frame.get("nonce", 0)
        timestamp = frame.get("timestamp", 0)
        msg_type = frame.get("message_type")
        iv_hex = frame.get("iv")
        ct_hex = frame.get("ciphertext")
        tag = frame.get("tag")

        if receiver_id != self.node_id:
            return False, None, f"Frame addressed to {receiver_id}, not {self.node_id}"

        if sender_id not in self.session_keys:
            return False, None, f"No session key found for sender {sender_id}"

        # 1. Anti-Replay Verification
        last_nonce = self.peer_last_nonces.get(sender_id, 0)
        if nonce <= last_nonce:
            return False, None, f"Replay detected: received nonce {nonce} <= last seen nonce {last_nonce}"

        session_key = self.session_keys[sender_id]
        try:
            iv = bytes.fromhex(iv_hex)
            ciphertext = bytes.fromhex(ct_hex)
        except Exception:
            return False, None, "Malformed hex encoding in IV or ciphertext"

        # 2. Authenticated Integrity Verification
        aad = f"{sender_id}:{self.node_id}:{nonce}:{timestamp}:{msg_type}".encode('utf-8')
        expected_tag = hmac.new(session_key, iv + ciphertext + aad, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(tag, expected_tag):
            return False, None, "Tamper detected: HMAC authentication tag verification failed"

        # Update valid nonce watermark
        self.peer_last_nonces[sender_id] = nonce

        # 3. Decrypt payload
        try:
            decrypted_bytes = _xor_cipher(ciphertext, session_key, iv)
            payload = json.loads(decrypted_bytes.decode('utf-8'))
            return True, payload, None
        except Exception as e:
            return False, None, f"Decryption payload parsing failure: {str(e)}"
