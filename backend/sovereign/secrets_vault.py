# -*- coding: utf-8 -*-
"""R-752 (ROADMAP_V5 ١.٥): خزينة أسرار الموصلات العامة.

التصميم (صادق، بلا ادعاء):
- تشفير مصادَق حقيقي AES-256-GCM (pycryptodome) — لا XOR. ملاحظة: الدالة
  encrypt في memory/encoding.py هي XOR بمفتاح مكرر وليست تشفيرًا؛ لا تُستخدم هنا.
- المفتاح الرئيسي من بيئة المالك (SOVEREIGN_VAULT_MASTER_KEY: ٣٢ بايت base64)
  — لا يُكتب في المستودع أبدًا. غيابه أو ضعفه = الخزينة معطلة (fail-closed).
- مفتاح البيانات مشتق عبر HKDF-SHA256؛ مفتاح البصمة مشتق منفصلًا.
- AAD = الاسم + النطاقات + الإصدار: أي تعديل على البيانات الوصفية في الملف
  (توسيع نطاق مثلًا) يكسر التحقق → VaultIntegrityError.
- حصر نطاقي: get(name, capability) يرفض أي قدرة خارج نطاق السر (ScopeDenied).
- تدقيق إلزامي: كل فعل (put/get/rotate/delete/denied) يمر بدالة audit قبل
  أثره؛ فشلها يرفض الفعل (لا أثر = لا تنفيذ، نمط R-635). الأحداث تحمل البصمة
  فقط، لا القيمة.
- تنقية السجلات: redact() وlog_filter() تستبدلان أي قيمة مخزنة ببصمتها.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256

MASTER_KEY_ENV = "SOVEREIGN_VAULT_MASTER_KEY"
VAULT_PATH_ENV = "SOVEREIGN_VAULT_PATH"
FORMAT_VERSION = 1

AuditFn = Callable[[str, Dict[str, Any]], Any]


class VaultError(Exception):
    pass


class VaultDisabled(VaultError):
    pass


class ScopeDenied(VaultError):
    pass


class SecretNotFound(VaultError):
    pass


class VaultIntegrityError(VaultError):
    pass


class VaultAuditError(VaultError):
    pass


def _decode_master(master_key_b64: Optional[str]) -> Optional[bytes]:
    if not master_key_b64:
        return None
    try:
        raw = base64.b64decode(master_key_b64.strip(), validate=True)
    except (binascii.Error, ValueError):
        return None
    return raw if len(raw) == 32 else None


class SecretsVault:
    def __init__(self, path: Path, master_key_b64: Optional[str],
                 audit: AuditFn):
        self.path = Path(path)
        self._audit_fn = audit
        master = _decode_master(master_key_b64)
        self.enabled = master is not None
        if master is not None:
            self._data_key = HKDF(master, 32, b"sovereign-vault", SHA256,
                                  context=b"data-key-v1")
            self._fp_key = HKDF(master, 32, b"sovereign-vault", SHA256,
                                context=b"fingerprint-key-v1")
        else:
            self._data_key = self._fp_key = None
        self._known_values: Dict[str, str] = {}  # للتنقية فقط — في الذاكرة

    # ---------------------------------------------------------- داخلي
    def _require(self) -> None:
        if not self.enabled:
            raise VaultDisabled(
                f"الخزينة معطلة: {MASTER_KEY_ENV} غائب أو ليس ٣٢ بايت base64 "
                "(fail-closed — المفتاح الرئيسي بيد المالك)")

    def _fingerprint(self, value: str) -> str:
        return hmac.new(self._fp_key, value.encode("utf-8"),
                        hashlib.sha256).hexdigest()[:16]

    @staticmethod
    def _aad(name: str, scopes: List[str], version: int) -> bytes:
        return json.dumps({"n": name, "s": sorted(scopes), "v": version,
                           "f": FORMAT_VERSION}, sort_keys=True).encode("utf-8")

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"format": FORMAT_VERSION, "secrets": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".vault-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def _audit(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            self._audit_fn(event, payload)
        except Exception as exc:
            raise VaultAuditError(
                f"تعذر تدقيق {event} — الفعل مرفوض (لا أثر = لا تنفيذ): "
                f"{type(exc).__name__}: {str(exc)[:160]}") from exc

    def _encrypt(self, name: str, value: str, scopes: List[str],
                 version: int) -> Dict[str, Any]:
        nonce = os.urandom(12)
        cipher = AES.new(self._data_key, AES.MODE_GCM, nonce=nonce)
        cipher.update(self._aad(name, scopes, version))
        ct, tag = cipher.encrypt_and_digest(value.encode("utf-8"))
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return {"scopes": sorted(scopes), "version": version,
                "nonce": base64.b64encode(nonce).decode(),
                "ciphertext": base64.b64encode(ct).decode(),
                "tag": base64.b64encode(tag).decode(),
                "fingerprint": self._fingerprint(value), "updated_at": now}

    def _decrypt(self, name: str, entry: Dict[str, Any]) -> str:
        try:
            cipher = AES.new(self._data_key, AES.MODE_GCM,
                             nonce=base64.b64decode(entry["nonce"]))
            cipher.update(self._aad(name, list(entry["scopes"]),
                                    int(entry["version"])))
            pt = cipher.decrypt_and_verify(base64.b64decode(entry["ciphertext"]),
                                           base64.b64decode(entry["tag"]))
        except (ValueError, KeyError, TypeError, binascii.Error) as exc:
            raise VaultIntegrityError(
                f"فشل التحقق من السر {name}: تلاعب أو مفتاح رئيسي خاطئ") from exc
        return pt.decode("utf-8")

    @staticmethod
    def _validate(name: str, scopes: List[str]) -> None:
        if not name or not isinstance(name, str) or len(name) > 128:
            raise VaultError("اسم سر غير صالح")
        if not scopes or not all(isinstance(s, str) and s for s in scopes):
            raise VaultError("النطاق إلزامي: قائمة قدرات غير فارغة")

    # ---------------------------------------------------------- عام
    def put(self, name: str, value: str, scopes: List[str], actor: str) -> Dict[str, Any]:
        self._require()
        self._validate(name, scopes)
        data = self._load()
        if name in data["secrets"]:
            raise VaultError(f"السر {name} موجود — استخدم rotate")
        entry = self._encrypt(name, value, scopes, 1)
        self._audit("vault.put", {"name": name, "scopes": entry["scopes"],
                                  "version": 1, "fingerprint": entry["fingerprint"],
                                  "actor": actor})
        data["secrets"][name] = entry
        self._save(data)
        self._known_values[name] = value
        return self._meta(name, entry)

    def get(self, name: str, capability: str, actor: str) -> str:
        self._require()
        data = self._load()
        entry = data["secrets"].get(name)
        if entry is None:
            self._audit("vault.get_missing", {"name": name, "capability": capability,
                                              "actor": actor})
            raise SecretNotFound(name)
        value = self._decrypt(name, entry)  # يتحقق من النطاق المخزن (AAD) أولًا
        if capability not in entry["scopes"]:
            self._audit("vault.denied", {"name": name, "capability": capability,
                                         "actor": actor})
            raise ScopeDenied(f"القدرة {capability} خارج نطاق السر {name}")
        self._audit("vault.get", {"name": name, "capability": capability,
                                  "version": entry["version"],
                                  "fingerprint": entry["fingerprint"], "actor": actor})
        self._known_values[name] = value
        return value

    def rotate(self, name: str, new_value: str, actor: str,
               scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        self._require()
        data = self._load()
        old = data["secrets"].get(name)
        if old is None:
            raise SecretNotFound(name)
        self._decrypt(name, old)  # لا تدوير فوق سجل متلاعب به
        new_scopes = sorted(scopes) if scopes else list(old["scopes"])
        self._validate(name, new_scopes)
        entry = self._encrypt(name, new_value, new_scopes, int(old["version"]) + 1)
        self._audit("vault.rotate", {"name": name, "scopes": entry["scopes"],
                                     "version": entry["version"],
                                     "old_fingerprint": old["fingerprint"],
                                     "fingerprint": entry["fingerprint"],
                                     "actor": actor})
        data["secrets"][name] = entry
        self._save(data)
        self._known_values[name] = new_value
        return self._meta(name, entry)

    def delete(self, name: str, actor: str) -> None:
        self._require()
        data = self._load()
        entry = data["secrets"].get(name)
        if entry is None:
            raise SecretNotFound(name)
        self._audit("vault.delete", {"name": name, "version": entry["version"],
                                     "fingerprint": entry["fingerprint"], "actor": actor})
        del data["secrets"][name]
        self._save(data)
        self._known_values.pop(name, None)

    @staticmethod
    def _meta(name: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {"name": name, "scopes": list(entry["scopes"]),
                "version": entry["version"], "fingerprint": entry["fingerprint"],
                "updated_at": entry.get("updated_at")}

    def list(self) -> List[Dict[str, Any]]:
        """بيانات وصفية وبصمات فقط — لا قيمة ولا نص مشفر."""
        if not self.path.exists():
            return []
        data = self._load()
        return [self._meta(n, e) for n, e in sorted(data["secrets"].items())]

    def status(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "cipher": "AES-256-GCM",
                "master_key_env": MASTER_KEY_ENV, "secrets": self.list(),
                "audit": "إلزامي عبر السجل السيادي الموقّع — بلا مفتاح توقيع (١.٣) "
                         "يُرفض كل فعل (fail-closed)"}

    def redact(self, text: str) -> str:
        out = str(text)
        for name, value in self._known_values.items():
            if value and value in out:
                out = out.replace(value, f"[secret:{name}:{self._fingerprint(value)}]")
        return out

    def log_filter(self) -> logging.Filter:
        vault = self

        class _Redact(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                record.msg = vault.redact(record.getMessage())
                record.args = ()
                return True
        return _Redact()


def _ledger_audit(event: str, payload: Dict[str, Any]) -> None:
    from memory.core import get_core
    get_core().append_event("vault_access", {"op": event, **payload},
                            user=payload.get("actor"))


_VAULT: Optional[SecretsVault] = None


def get_vault() -> SecretsVault:
    """الخزينة الحية: المفتاح من البيئة، والتدقيق عبر السجل السيادي الموقّع."""
    global _VAULT
    if _VAULT is None:
        default = Path(__file__).resolve().parents[2] / "data" / "vault" / "secrets.json"
        _VAULT = SecretsVault(path=Path(os.environ.get(VAULT_PATH_ENV, str(default))),
                              master_key_b64=os.environ.get(MASTER_KEY_ENV),
                              audit=_ledger_audit)
    return _VAULT
