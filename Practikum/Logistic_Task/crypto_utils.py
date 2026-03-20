"""
AES-GCM encryption utilities for offline task pack.
Keys are 256-bit, expire after OFFLINE_KEY_TTL_HOURS hours.
"""
import os
import json
import base64
import hashlib
import hmac
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


OFFLINE_KEY_TTL_HOURS = 24


def _derive_task_key(task_id: int, master_secret: bytes, expiry_ts: int) -> bytes:
    """
    Derives a unique 256-bit AES key per task using HMAC-SHA256.
    Key is bound to task_id and expiry timestamp so it auto-expires.
    """
    material = f"{task_id}:{expiry_ts}".encode()
    return hmac.new(master_secret, material, hashlib.sha256).digest()


def encrypt_value(plaintext: str, key: bytes) -> str:
    """
    Encrypts a string with AES-GCM (256-bit key).
    Returns base64-encoded nonce+ciphertext.
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce, unique per encryption
    ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return base64.b64encode(nonce + ct).decode('ascii')


def decrypt_value(b64_payload: str, key: bytes) -> str:
    """
    Decrypts AES-GCM payload produced by encrypt_value.
    """
    raw = base64.b64decode(b64_payload)
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode('utf-8')


def build_offline_pack(tasks_testcases: dict, master_secret: bytes) -> dict:
    """
    Builds the full offline pack:
    {
      "expires_at": <unix_ts>,
      "tasks": {
        "<task_id>": {
          "key_b64": "<base64 AES key>",   # sent to client, used by WebCrypto
          "tests": [
            {"input_enc": "...", "expected_enc": "..."}
          ]
        }
      }
    }
    Hidden test input/expected are encrypted. Open tests (is_hidden=False)
    have input in plaintext but expected still encrypted, so the correct
    answer is never exposed.
    """
    now = datetime.now(timezone.utc)
    expiry_ts = int(now.timestamp()) + OFFLINE_KEY_TTL_HOURS * 3600

    pack = {"expires_at": expiry_ts, "tasks": {}}

    for task_id, testcases in tasks_testcases.items():
        key = _derive_task_key(int(task_id), master_secret, expiry_ts)
        key_b64 = base64.b64encode(key).decode('ascii')

        encrypted_tests = []
        for tc in testcases:
            encrypted_tests.append({
                # Input of open tests shown as-is; hidden inputs encrypted
                "input_enc": encrypt_value(tc['input'], key) if tc['is_hidden'] else tc['input'],
                "is_hidden": tc['is_hidden'],
                # Expected answer ALWAYS encrypted — never visible to client
                "expected_enc": encrypt_value(tc['expected'], key),
            })

        pack["tasks"][str(task_id)] = {
            "key_b64": key_b64,
            "tests": encrypted_tests,
        }

    return pack
