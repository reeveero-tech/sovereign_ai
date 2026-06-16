"""
NexusCore — الاتصال الآمن
توقيع الرسائل والتحقق منها لضمان السلامة.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger("nexus.encryption.comm")


@dataclass
class SignedMessage:
    payload: str
    signature: str
    timestamp: float
    sender_id: str
    version: int = 1


class SecureCommunication:
    """يوقّع الرسائل ويتحقق منها بين مكونات النظام"""

    def __init__(self, secret: Optional[bytes] = None):
        self._secret = secret or os.urandom(32)
        self._nonces: Dict[str, float] = {}   # للحماية من replay attacks
        logger.info("📡 SecureCommunication initialized")

    def sign_message(self, data: Any, sender_id: str) -> SignedMessage:
        if not isinstance(data, str):
            data = json.dumps(data, ensure_ascii=False, sort_keys=True)
        ts  = time.time()
        payload = f"{sender_id}|{ts}|{data}"
        sig = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        return SignedMessage(
            payload=data, signature=sig,
            timestamp=ts, sender_id=sender_id,
        )

    def verify_message(self, msg: SignedMessage,
                       max_age_seconds: int = 300) -> bool:
        # تحقق من العمر
        if time.time() - msg.timestamp > max_age_seconds:
            logger.warning("Message too old (possible replay)")
            return False
        # تحقق من nonce
        nonce_key = f"{msg.sender_id}:{msg.timestamp}"
        if nonce_key in self._nonces:
            logger.warning("Duplicate nonce (replay attack detected)")
            return False
        # تحقق من التوقيع
        payload = f"{msg.sender_id}|{msg.timestamp}|{msg.payload}"
        expected = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        valid = hmac.compare_digest(msg.signature, expected)
        if valid:
            self._nonces[nonce_key] = msg.timestamp
            self._cleanup_nonces()
        else:
            logger.error(f"❌ Invalid signature from {msg.sender_id}")
        return valid

    def _cleanup_nonces(self) -> None:
        cutoff = time.time() - 600
        self._nonces = {k: v for k, v in self._nonces.items() if v > cutoff}

    def encode_payload(self, data: Any) -> str:
        text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
        return base64.urlsafe_b64encode(text.encode()).decode()

    def decode_payload(self, encoded: str) -> Optional[Any]:
        try:
            text = base64.urlsafe_b64decode(encoded.encode()).decode()
            try:
                return json.loads(text)
            except Exception:
                return text
        except Exception as exc:
            logger.error(f"Decode error: {exc}")
            return None
