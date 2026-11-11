"""
Lightweight High-Performance Cryptographic Primitives for IoT Nodes
Provides:
- Fast Ed25519 digital signatures (using Extended Twisted Edwards Projective Coordinates for O(1) inversions)
- SHA-256 cryptographic hashing
- HMAC-SHA256 message authentication
- Cryptographically secure random nonce generation
"""

import hashlib
import hmac
import secrets
from typing import Tuple

# --- Ed25519 Curve Parameters (RFC 8032) ---
_b = 256
_q = 2**255 - 19
_l = 2**252 + 27742317777372353535851937790883648493
_d = -121665 * pow(121666, _q - 2, _q) % _q
_I = pow(2, (_q - 1) // 4, _q)

def _inv(z: int) -> int:
    return pow(z, _q - 2, _q)

def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_d * y * y + 1) % _q
    x = pow(xx, (_q + 3) // 8, _q)
    if (x * x - xx) % _q != 0:
        x = (x * _I) % _q
    if x % 2 != 0:
        x = _q - x
    return x

_By = 4 * _inv(5) % _q
_Bx = _xrecover(_By)
_B = (_Bx % _q, _By % _q)
# Base point in extended coordinates (X:Y:Z:T)
_B_ext = (_Bx % _q, _By % _q, 1, (_Bx * _By) % _q)

def _ed_ext_add(P, Q):
    """Point addition in Extended Twisted Edwards Coordinates (zero divisions)."""
    X1, Y1, Z1, T1 = P
    X2, Y2, Z2, T2 = Q
    A = ((Y1 - X1) * (Y2 - X2)) % _q
    B = ((Y1 + X1) * (Y2 + X2)) % _q
    C = (2 * T1 * _d * T2) % _q
    D = (2 * Z1 * Z2) % _q
    E = (B - A) % _q
    F = (D - C) % _q
    G = (D + C) % _q
    H = (B + A) % _q
    return ((E * F) % _q, (G * H) % _q, (F * G) % _q, (E * H) % _q)

def _ed_ext_double(P):
    """Point doubling in Extended Twisted Edwards Coordinates."""
    X1, Y1, Z1, _ = P
    A = (X1 * X1) % _q
    B = (Y1 * Y1) % _q
    C = (2 * Z1 * Z1) % _q
    H = (A + B) % _q
    E = (H - pow(X1 + Y1, 2, _q)) % _q
    G = (A - B) % _q
    F = (C + G) % _q
    return ((E * F) % _q, (G * H) % _q, (F * G) % _q, (E * H) % _q)

def _scalarmult_ext(P_ext, e: int):
    """Fast scalar multiplication using Montgomery/double-and-add on extended coordinates."""
    if e == 0:
        return (0, 1, 1, 0)
    R = (0, 1, 1, 0) # Neutral element
    bits = bin(e)[2:]
    for bit in bits:
        R = _ed_ext_double(R)
        if bit == '1':
            R = _ed_ext_add(R, P_ext)
    return R

def _ext_to_affine(P_ext) -> Tuple[int, int]:
    X, Y, Z, _ = P_ext
    z_inv = _inv(Z)
    return ((X * z_inv) % _q, (Y * z_inv) % _q)

def _encodeint(y: int) -> bytes:
    return y.to_bytes(32, 'little')

def _decodeint(b: bytes) -> int:
    return int.from_bytes(b, 'little')

def _encodepoint(P: Tuple[int, int]) -> bytes:
    x, y = P
    b = bytearray(_encodeint(y))
    if x & 1:
        b[31] |= 0x80
    return bytes(b)

def _decodepoint(b: bytes) -> Tuple[int, int]:
    y = int.from_bytes(b[:31] + bytes([b[31] & 0x7F]), 'little')
    x = _xrecover(y)
    if bool(x & 1) != bool(b[31] & 0x80):
        x = _q - x
    return (x, y)

def _H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()

def generate_keypair() -> Tuple[bytes, bytes]:
    """Generates an Ed25519 (private_key, public_key) pair in bytes."""
    sk = secrets.token_bytes(32)
    h = _H(sk)
    a = int.from_bytes(h[:32], 'little')
    a &= (1 << 254) - 8
    a |= (1 << 254)
    A_ext = _scalarmult_ext(_B_ext, a)
    A = _ext_to_affine(A_ext)
    pk = _encodepoint(A)
    return sk, pk

def sign_message(sk: bytes, message: bytes) -> bytes:
    """Signs an arbitrary bytes message using Ed25519 secret key."""
    h = _H(sk)
    a = int.from_bytes(h[:32], 'little')
    a &= (1 << 254) - 8
    a |= (1 << 254)
    prefix = h[32:]
    
    r = int.from_bytes(_H(prefix + message), 'little') % _l
    R_ext = _scalarmult_ext(_B_ext, r)
    R = _ext_to_affine(R_ext)
    R_bytes = _encodepoint(R)
    
    A_ext = _scalarmult_ext(_B_ext, a)
    A = _ext_to_affine(A_ext)
    A_bytes = _encodepoint(A)
    
    k = int.from_bytes(_H(R_bytes + A_bytes + message), 'little') % _l
    S = (r + k * a) % _l
    return R_bytes + _encodeint(S)

def verify_signature(pk: bytes, message: bytes, signature: bytes) -> bool:
    """Verifies an Ed25519 signature over message bytes with public key."""
    if len(signature) != 64 or len(pk) != 32:
        return False
    try:
        R_bytes = signature[:32]
        S = _decodeint(signature[32:])
        if S >= _l:
            return False
        A = _decodepoint(pk)
        R = _decodepoint(R_bytes)
        k = int.from_bytes(_H(R_bytes + pk + message), 'little') % _l
        
        # Check: [S]B == R + [k]A in extended coordinates
        SB_ext = _scalarmult_ext(_B_ext, S)
        A_ext = (A[0], A[1], 1, (A[0] * A[1]) % _q)
        kA_ext = _scalarmult_ext(A_ext, k)
        R_ext = (R[0], R[1], 1, (R[0] * R[1]) % _q)
        R_plus_kA_ext = _ed_ext_add(R_ext, kA_ext)
        
        SB = _ext_to_affine(SB_ext)
        R_plus_kA = _ext_to_affine(R_plus_kA_ext)
        return SB == R_plus_kA
    except Exception:
        return False

def sha256_digest(data: bytes) -> str:
    """Computes hexadecimal SHA-256 digest of input bytes."""
    return hashlib.sha256(data).hexdigest()

def compute_hmac(key: bytes, message: bytes) -> str:
    """Computes HMAC-SHA256 of message using key."""
    return hmac.new(key, message, hashlib.sha256).hexdigest()
