"""
NexusCore — مدير مفاتيح التشفير
يولد ويخزن ويدير مفاتيح التشفير بأمان.
"""
import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.encryption.keys")


@dataclass
class KeyRecord:
    key_id: str
    name: str
    algorithm: str
    key_length_bits: int
    created_at: float
    expires_at: Optional[float]
    active: bool = True
    purpose: str = "general"
    # المفتاح مشفر داخل الذاكرة فقط — لا يُكتب على القرص
    _key_bytes: Optional[bytes] = field(default=None, repr=False)


class KeyManager:
    """يدير دورة حياة مفاتيح التشفير"""

    def __init__(self, storage_path: str = "nexus_data/keys"):
        self._storage = Path(storage_path)
        self._storage.mkdir(parents=True, exist_ok=True)
        self._keys: Dict[str, KeyRecord] = {}
        self._master_key: bytes = os.urandom(32)   # مفتاح التشفير الرئيسي
        logger.info("🗝️ KeyManager initialized")

    def generate_key(self, name: str, algorithm: str = "AES-256",
                     ttl_days: Optional[int] = None,
                     purpose: str = "general") -> KeyRecord:
        import uuid
        key_id   = uuid.uuid4().hex[:16]
        key_len  = {"AES-128": 16, "AES-256": 32, "RSA-2048": 256}.get(algorithm, 32)
        key_bytes = os.urandom(key_len)
        record   = KeyRecord(
            key_id=key_id, name=name, algorithm=algorithm,
            key_length_bits=key_len * 8,
            created_at=time.time(),
            expires_at=time.time() + ttl_days * 86400 if ttl_days else None,
            purpose=purpose, _key_bytes=key_bytes,
        )
        self._keys[key_id] = record
        logger.info(f"🔑 Key generated: {name} ({algorithm})")
        return record

    def get_key_bytes(self, key_id: str) -> Optional[bytes]:
        record = self._keys.get(key_id)
        if not record or not record.active:
            return None
        if record.expires_at and time.time() > record.expires_at:
            record.active = False
            logger.warning(f"Key expired: {record.name}")
            return None
        return record._key_bytes

    def rotate_key(self, key_id: str) -> Optional[KeyRecord]:
        old = self._keys.get(key_id)
        if not old:
            return None
        old.active = False
        new_key = self.generate_key(
            name=old.name + "_rotated",
            algorithm=old.algorithm,
            purpose=old.purpose,
        )
        logger.info(f"🔄 Key rotated: {old.name} → {new_key.name}")
        return new_key

    def revoke_key(self, key_id: str) -> bool:
        key = self._keys.get(key_id)
        if key:
            key.active = False
            key._key_bytes = None
            logger.warning(f"🚫 Key revoked: {key.name}")
            return True
        return False

    def list_keys(self, active_only: bool = True) -> List[Dict]:
        return [
            {"key_id": k.key_id, "name": k.name, "algorithm": k.algorithm,
             "bits": k.key_length_bits, "active": k.active,
             "purpose": k.purpose, "created_at": k.created_at}
            for k in self._keys.values()
            if not active_only or k.active
        ]

    def cleanup_expired(self) -> int:
        now = time.time()
        count = 0
        for key in self._keys.values():
            if key.expires_at and now > key.expires_at and key.active:
                key.active = False
                key._key_bytes = None
                count += 1
        return count
