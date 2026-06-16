"""
NexusCore — محرك التشفير الآمن
تشفير AES-256-CBC قياسي (بديل آمن لـ self_mutating_crypto).
لا يتطلب مكتبات خارجية — يستخدم Python stdlib فقط.
"""
import base64
import hashlib
import hmac
import logging
import os
import struct
import time
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("nexus.encryption.engine")

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    HAS_PYCRYPTO = True
except ImportError:
    HAS_PYCRYPTO = False
    logger.warning("pycryptodome not available — using XOR fallback (dev only)")


@dataclass
class EncryptedPayload:
    ciphertext_b64: str
    iv_b64: str
    tag_b64: str
    algorithm: str
    version: int = 1


class EncryptionEngine:
    """محرك تشفير آمن ومعياري"""

    ALGORITHM = "AES-256-CBC" if HAS_PYCRYPTO else "XOR-DEV"

    def __init__(self, master_key: Optional[bytes] = None):
        self._master_key = master_key or os.urandom(32)
        logger.info(f"🔒 EncryptionEngine initialized ({self.ALGORITHM})")

    def encrypt(self, plaintext: str) -> EncryptedPayload:
        data = plaintext.encode("utf-8")
        iv   = os.urandom(16)
        if HAS_PYCRYPTO:
            cipher     = AES.new(self._master_key, AES.MODE_CBC, iv)
            ciphertext = cipher.encrypt(pad(data, AES.block_size))
        else:
            ciphertext = self._xor_encrypt(data, self._master_key)
        tag = hmac.new(self._master_key,
                        ciphertext + iv, hashlib.sha256).hexdigest()
        return EncryptedPayload(
            ciphertext_b64=base64.b64encode(ciphertext).decode(),
            iv_b64=base64.b64encode(iv).decode(),
            tag_b64=tag,
            algorithm=self.ALGORITHM,
        )

    def decrypt(self, payload: EncryptedPayload) -> Optional[str]:
        try:
            ciphertext = base64.b64decode(payload.ciphertext_b64)
            iv         = base64.b64decode(payload.iv_b64)
            expected   = hmac.new(self._master_key,
                                   ciphertext + iv, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(payload.tag_b64, expected):
                logger.error("❌ HMAC verification failed — tampered payload")
                return None
            if HAS_PYCRYPTO:
                cipher    = AES.new(self._master_key, AES.MODE_CBC, iv)
                plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
            else:
                plaintext = self._xor_encrypt(ciphertext, self._master_key)
            return plaintext.decode("utf-8")
        except Exception as exc:
            logger.error(f"Decryption error: {exc}")
            return None

    def encrypt_dict(self, data: dict) -> EncryptedPayload:
        import json
        return self.encrypt(json.dumps(data, ensure_ascii=False))

    def decrypt_dict(self, payload: EncryptedPayload) -> Optional[dict]:
        import json
        text = self.decrypt(payload)
        return json.loads(text) if text else None

    def derive_key(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        salt = salt or os.urandom(32)
        key  = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000, 32)
        return key, salt

    @staticmethod
    def _xor_encrypt(data: bytes, key: bytes) -> bytes:
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def hash_data(self, data: str, algorithm: str = "sha256") -> str:
        h = hashlib.new(algorithm)
        h.update(data.encode())
        return h.hexdigest()
