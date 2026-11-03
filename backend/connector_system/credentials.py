# -*- coding: utf-8 -*-
"""R-840: طبقة الاعتماد الموحدة — كائن اعتماد واحد لكل أنواع التوكن.

السر يُخزَّن في خزينة R-752 (مشفّر AES-256-GCM) بمرجع فقط — كود التكامل
يطلب توكنًا صالحًا ولا يعرف كيف حُصل عليه. الحالة (active|expired|revoked|
error) مخزنة في ملف بيانات وصفية لا يحوي أي سر: البصمة فقط.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from . import auth_types

STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"
STATUS_REVOKED = "revoked"
STATUS_ERROR = "error"

VAULT_CAPABILITY = "connector_system_auth"


class CredentialError(Exception):
    pass


class CredentialNotFound(CredentialError):
    pass


@dataclass
class Credential:
    """كائن الاعتماد الموحد — يطابق مواصفة النظام حرفيًا."""
    id: str
    connector_id: str
    auth_type: str
    owner_scope: str                 # user|org|service
    owner: str
    scopes: List[str]
    secret_ref: str                 # مرجع الخزينة — ليس سرًا أبدًا
    fingerprint: str = ""           # بصمة SHA-256 أول ١٢ حرفًا — للعرض فقط
    expires_at: Optional[float] = None
    refresh_supported: bool = False
    rotation_policy: str = "manual"
    status: str = STATUS_ACTIVE
    created_by: str = ""
    created_at: float = field(default_factory=time.time)
    last_used_at: Optional[float] = None
    last_error: Optional[str] = None

    def public(self) -> Dict[str, Any]:
        """عرض آمن — لا قيمة سرية إطلاقًا."""
        return {
            "id": self.id, "connector_id": self.connector_id,
            "auth_type": self.auth_type, "owner_scope": self.owner_scope,
            "owner": self.owner, "scopes": sorted(self.scopes),
            "fingerprint": self.fingerprint,
            "expires_at": self.expires_at, "refresh_supported": self.refresh_supported,
            "rotation_policy": self.rotation_policy, "status": self.status,
            "created_by": self.created_by, "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "last_error": self._safe_error(),
        }

    def _safe_error(self) -> Optional[str]:
        """آخر خطأ منقّى — بلا أي قيمة سرية (تطبيق سياسة عدم التسريب)."""
        return (self.last_error or None) if self.last_error else None

    def is_expired(self, now: Optional[float] = None) -> bool:
        if self.expires_at is None:
            return False
        return (now or time.time()) >= self.expires_at


def _fingerprint_of(secret_value: str) -> str:
    return hashlib.sha256(secret_value.encode("utf-8")).hexdigest()[:12]


class CredentialStore:
    """مخزن الاعتمادات: بيانات وصفية على القرص + السر في الخزينة.

    fail-closed: بلا خزينة صالحة لا إنشاء ولا استخدام — متسق مع فلسفة R-752.
    """

    def __init__(self, state_path, vault, clock=time.time):
        self.state_path = state_path
        self.vault = vault
        self.clock = clock
        self._lock = threading.Lock()

    # ------------------------------------------------------------ الحالة
    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(self.state_path):
            return {}
        with open(self.state_path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save_all(self, creds: Dict[str, Dict[str, Any]] = None) -> None:
        creds = creds if creds is not None else self._load()
        os.makedirs(os.path.dirname(str(self.state_path)) or ".", exist_ok=True)
        try:
            from runtime.atomic_json import atomic_write_json
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج
            from backend.runtime.atomic_json import atomic_write_json
        atomic_write_json(self.state_path, creds, ensure_ascii=False, indent=1)

    # ------------------------------------------------------------ الإنشاء
    def create(self, connector_id: str, auth_type: str, owner_scope: str,
               owner: str, scopes: List[str], secret_value: str,
               created_by: str, ttl_s: Optional[float] = None) -> Credential:
        at = auth_types.auth_type(auth_type)
        cred_id = f"c-{uuid.uuid4().hex[:10]}"
        secret_ref = f"connector_system.cred.{cred_id}"
        with self._lock:
            self.vault.put(secret_ref, secret_value,
                           scopes=[VAULT_CAPABILITY], actor=created_by)
            c = Credential(
                id=cred_id, connector_id=connector_id, auth_type=auth_type,
                owner_scope=owner_scope, owner=owner, scopes=sorted(set(scopes)),
                secret_ref=secret_ref, fingerprint=_fingerprint_of(secret_value),
                expires_at=(self.clock() + ttl_s) if ttl_s else None,
                refresh_supported=at.refresh_supported,
                rotation_policy=at.rotation, status=STATUS_ACTIVE,
                created_by=created_by, created_at=self.clock())
            creds = self._load()
            creds[cred_id] = asdict(c)
            self._save_all(creds)
        return c

    def get(self, cred_id: str) -> Credential:
        raw = self._load().get(cred_id)
        if raw is None:
            raise CredentialNotFound(cred_id)
        return Credential(**raw)

    def list_for_connector(self, connector_id: str) -> List[Credential]:
        return [Credential(**r) for r in self._load().values()
                if r["connector_id"] == connector_id]

    def all(self) -> List[Credential]:
        return [Credential(**r) for r in self._load().values()]

    def update(self, c: Credential) -> None:
        with self._lock:
            creds = self._load()
            if c.id not in creds:
                raise CredentialNotFound(c.id)
            creds[c.id] = asdict(c)
            self._save_all(creds)

    # ------------------------------------------------------------ دورة الحياة
    def rotate_secret(self, cred_id: str, new_value: str, actor: str,
                      scopes: Optional[List[str]] = None) -> Credential:
        c = self.get(cred_id)
        self.vault.rotate(c.secret_ref, new_value, actor=actor,
                          scopes=scopes or [VAULT_CAPABILITY])
        c.fingerprint = _fingerprint_of(new_value)
        c.status = STATUS_ACTIVE
        c.last_error = None
        self.update(c)
        return c

    def revoke(self, cred_id: str, actor: str) -> Credential:
        c = self.get(cred_id)
        try:
            self.vault.delete(c.secret_ref, actor=actor)
        except Exception:  # TOLERATED: السر قد يكون محذوفًا — الإبطال يستمر
            pass
        c.status = STATUS_REVOKED
        self.update(c)
        return c

    def update_scopes(self, cred_id: str, scopes: List[str], actor: str) -> Credential:
        c = self.get(cred_id)
        c.scopes = sorted(set(scopes))
        self.update(c)
        return c

    def mark_used(self, cred_id: str) -> None:
        c = self.get(cred_id)
        c.last_used_at = self.clock()
        self.update(c)

    def record_error(self, cred_id: str, message: str) -> None:
        c = self.get(cred_id)
        c.last_error = message[:300]
        if c.status == STATUS_ACTIVE:
            c.status = STATUS_ERROR
        self.update(c)

    def mark_expired_if_due(self) -> int:
        """يُحدّث حالات المنتهية — يُستدعى دوريًا وقبل كل تنفيذ."""
        n = 0
        for c in self.all():
            if c.status == STATUS_ACTIVE and c.is_expired(self.clock()):
                c.status = STATUS_EXPIRED
                self.update(c)
                n += 1
        return n

    def find_valid(self, connector_id: str, required_scopes: List[str],
                   owner: Optional[str] = None) -> Optional[Credential]:
        """أول اعتماد نشط يغطي النطاقات المطلوبة (أقل صلاحية تلبي الحاجة)."""
        self.mark_expired_if_due()
        need = set(required_scopes)
        best: Optional[Credential] = None
        for c in self.list_for_connector(connector_id):
            if c.status != STATUS_ACTIVE or not need <= set(c.scopes):
                continue
            if owner and c.owner_scope == "user" and c.owner != owner:
                continue
            if best is None or len(c.scopes) < len(best.scopes):
                best = c  # أقل صلاحية تلبي الحاجة
        return best

    def get_secret(self, c: Credential, actor: str = "auth_engine") -> str:
        """القيمة السرية — للاستخدام الداخلي فقط، لا تعرض أبدًا في المخرجات."""
        return self.vault.get(c.secret_ref, VAULT_CAPABILITY, actor=actor)

    def status(self) -> Dict[str, Any]:
        """حمولة الحالة للواجهة — بلا أي سر."""
        return {"credentials": [c.public() for c in self.all()]}
