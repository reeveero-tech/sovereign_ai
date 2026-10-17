"""
NexusCore — محرك التشفير الآمن
تشفير AES-256-CBC (Encrypt-then-MAC) — يتطلب pycryptodome.
⚠️ لا يوجد وضع سقوط XOR: غياب المكتبة = فشل صريح (جولة المجلس <1>).
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
    # ⚠️ SECURITY (جولة المجلس <1> — أمين 5.1/بصير BAS-S02/حكيم):
    # لا سقوط صامت إلى XOR — فشل صريح عند الإنشاء/التشفير.
    logger.critical("pycryptodome not available — encryption UNAVAILABLE (no XOR fallback)")


@dataclass
class EncryptedPayload:
    ciphertext_b64: str
    iv_b64: str
    tag_b64: str
    algorithm: str
    version: int = 1


class EncryptionEngine:
    """محرك تشفير آمن ومعياري"""

    ALGORITHM = "AES-256-CBC"

    def __init__(self, master_key: Optional[bytes] = None):
        # ⚠️ SECURITY (جولة المجلس <1>): فشل مغلق عند غياب المكتبة — لا XOR
        if not HAS_PYCRYPTO:
            raise RuntimeError(
                "EncryptionEngine: pycryptodome غير متوفر — التشفير غير متاح "
                "(لا يوجد وضع سقوط XOR — فشل صريح، جولة المجلس <1>)"
            )
        self._master_key = master_key or os.urandom(32)
        logger.info(f"🔒 EncryptionEngine initialized ({self.ALGORITHM})")

    def encrypt(self, plaintext: str) -> EncryptedPayload:
        data = plaintext.encode("utf-8")
        iv   = os.urandom(16)
        cipher     = AES.new(self._master_key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(data, AES.block_size))
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
            # ⚠️ SECURITY (جولة المجلس <1> — حكيم): حقل الخوارزمية مُتحقَّق —
            # لا يُفك مظروف معلن بخوارزمية غير معتمدة.
            if payload.algorithm != self.ALGORITHM:
                logger.error(
                    f"❌ Unsupported algorithm in payload: {payload.algorithm!r} "
                    f"— expected {self.ALGORITHM}"
                )
                return None
            ciphertext = base64.b64decode(payload.ciphertext_b64)
            iv         = base64.b64decode(payload.iv_b64)
            expected   = hmac.new(self._master_key,
                                   ciphertext + iv, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(payload.tag_b64, expected):
                logger.error("❌ HMAC verification failed — tampered payload")
                return None
            cipher    = AES.new(self._master_key, AES.MODE_CBC, iv)
            plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
            return plaintext.decode("utf-8")
        except Exception as exc:
            logger.exception(
                f"R-682 [SECURITY]: Decryption error — silently swallowing may hide "
                f"tampered payload or corrupted ciphertext. exc={exc}"
            )
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

    def hash_data(self, data: str, algorithm: str = "sha256") -> str:
        # ⚠️ SECURITY (جولة المجلس <1> — حكيم): خوارزميات معتمدة فقط
        if algorithm not in ("sha256", "sha384", "sha512"):
            raise ValueError(f"hash_data: خوارزمية غير معتمدة: {algorithm}")
        h = hashlib.new(algorithm)
        h.update(data.encode())
        return h.hexdigest()
