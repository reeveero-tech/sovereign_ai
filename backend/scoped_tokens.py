# -*- coding: utf-8 -*-
"""R-851 (٦.٧.٢): رموز محدودة النطاق بدل المفتاح الواحد الشامل.

المشكلة (forensics/R-851_scoped_tokens_RED.txt): 19 موضع مصادقة كلها تقبل مفتاحًا
واحدًا يفعل كل شيء — من قراءة الإعدادات إلى إعادة ضبط النظام. لا طريقة لمنح
أداة أو جهاز أو مساعد صلاحية محدودة، ولا لإبطال صلاحية مسرّبة دون تدوير الجذر.

التصميم:
- رمز موقّع ``sct1.<claims>.<sig>``: المطالبات (jti/نطاقات/انتهاء/إصدار/وسم)
  بترميز base64url، والتوقيع HMAC-SHA256 بمفتاح مشتق لغرض ``scoped_tokens``
  (HKDF من جذر المالك — D-033). التحقق بلا تخزين: يدوم عبر إعادة النشر.
- النطاقات مغلقة ومعلنة (``SCOPES``)؛ العمليات الإدارية (إصدار/إبطال الرموز،
  إعادة الضبط، أوامر السيد، الولاء، حالة المفتاح) للمفتاح الرئيسي وحده —
  لا رمز يمنحها، فلا رمز يصدر رمزًا أوسع منه.
- عمر محدود إلزامي: 60 ثانية .. 30 يومًا.
- الإبطال: قائمة jti مبطلة محليًا + كتابة نافذة للمخزن الدائم (SupabaseDisk،
  namespace ``auth_tokens``). إن كان المخزن مضبوطًا ولم تُحمّل القائمة منه بعد
  ⇒ كل الرموز مرفوضة (fail-closed) حتى لا يعود رمز مبطل حيًا بعد إعادة نشر.
- السر لا يُخزن ولا يُسجل: السجل (الإصدار/الإبطال) يحمل jti والنطاقات فقط.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

logger = logging.getLogger("sovereign.scoped_tokens")

PREFIX = "sct1"
NAMESPACE = "auth_tokens"
MIN_TTL = 60
MAX_TTL = 30 * 24 * 3600

SCOPES: Dict[str, str] = {
    "read": "قراءة الإعدادات والحالة (ws/settings، brain/models، brain/settings، security/log، orchestrator/modules)",
    "chat": "المحادثة بصلاحيات المالك",
    "tools": "تنفيذ الأدوات عبر /tools/invoke",
    "skills": "دورة المهارات: اقتراح من الكتالوج، تقييم مستقل، مزامنة",
    "skills.approve": "اعتماد مهارة أو التراجع عنها",
    "connectors": "منح الموصلات وسحبها",
    "brain.write": "تعديل إعدادات العقل",
    "orchestrator": "تشغيل دورة المنسق",
}
MASTER_ONLY = ("/auth/tokens (إصدار/إبطال)", "/sovereign/command", "/sovereign/reset",
               "/loyalty/release", "/api-key", "/api-key-header")


class TokenError(ValueError):
    pass


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _default_key() -> bytes:
    try:
        from sovereign.keys.derivation import derive_key
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.sovereign.keys.derivation import derive_key
    return derive_key("scoped_tokens")


def _default_store() -> Optional[Any]:
    try:
        from skills_durable import make_store
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.skills_durable import make_store
    return make_store()


def _default_audit(event: str, payload: Dict[str, Any]) -> None:
    from memory.core import get_core
    get_core().append_event(event, payload)


class TokenManager:
    def __init__(self, root: Path, *, key: Optional[bytes] = None, store: Any = "env",
                 audit: Optional[Callable[[str, Dict[str, Any]], None]] = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.root = Path(root)
        self._key = key
        self.store = _default_store() if store == "env" else store
        self.audit = audit or _default_audit
        self.clock = clock
        self._lock = threading.Lock()
        self._revoked: Dict[str, float] = {}
        self._issued: Dict[str, Dict[str, Any]] = {}
        self._remote_loaded = self.store is None   # بلا مخزن: المحلي هو الحقيقة (يُعلن)
        self._last_load_try = 0.0
        self._load_local()

    # ------------------------------------------------------------- التخزين
    @property
    def key(self) -> bytes:
        if self._key is None:
            self._key = _default_key()
        return self._key

    def _path(self) -> Path:
        return self.root / "auth" / "tokens.json"

    def _load_local(self) -> None:
        p = self._path()
        if p.exists():
            doc = json.loads(p.read_text(encoding="utf-8"))
            self._revoked.update(doc.get("revoked") or {})
            self._issued.update(doc.get("issued") or {})

    def _save_local(self) -> None:
        p = self._path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"revoked": self._revoked, "issued": self._issued},
                                ensure_ascii=False))
        os.replace(tmp, p)

    def _push(self, jti: str) -> bool:
        if self.store is None:
            return False
        meta = dict(self._issued.get(jti) or {"jti": jti})
        meta["revoked_at"] = self._revoked.get(jti)
        try:
            return bool(self.store.save_blob(NAMESPACE, f"tok:{jti}", meta))
        except Exception as exc:  # TOLERATED (R-851): المخزن معطل — يُعلن durable=False
            logger.warning("auth_tokens push failed: %s", type(exc).__name__)
            return False

    def load_remote(self) -> Dict[str, Any]:
        """تحميل السجل الدائم (إصدار/إبطال). فشل التحميل مع مخزن مضبوط ⇒ يبقى
        ``_remote_loaded=False`` فتُرفض كل الرموز (fail-closed)."""
        if self.store is None:
            return {"backend": None, "loaded": True, "revoked": len(self._revoked)}
        try:
            rows = self.store.list_blobs(NAMESPACE)
        except Exception as exc:  # TOLERATED (R-851): يبقى مغلقًا لا مفتوحًا
            rows = None
            logger.warning("auth_tokens load failed: %s", type(exc).__name__)
        self._last_load_try = self.clock()
        if rows is None:
            return {"backend": type(self.store).__name__, "loaded": False}
        with self._lock:
            for row in rows:
                meta = row.get("payload") if isinstance(row, dict) and "payload" in row else row
                if not isinstance(meta, dict) or not meta.get("jti"):
                    continue
                jti = str(meta["jti"])
                self._issued.setdefault(jti, {k: v for k, v in meta.items() if k != "revoked_at"})
                if meta.get("revoked_at"):
                    self._revoked[jti] = float(meta["revoked_at"])
            self._remote_loaded = True
            self._save_local()
        return {"backend": type(self.store).__name__, "loaded": True,
                "revoked": len(self._revoked), "issued": len(self._issued)}

    # ------------------------------------------------------------- الإصدار
    def issue(self, scopes: Iterable[str], ttl_seconds: int, label: str = "") -> Dict[str, Any]:
        scp = sorted(set(scopes or []))
        unknown = [s for s in scp if s not in SCOPES]
        if not scp or unknown:
            raise TokenError(f"نطاقات غير صالحة: {unknown or 'فارغة'} — المتاح: {sorted(SCOPES)}")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) \
                or not MIN_TTL <= ttl_seconds <= MAX_TTL:
            raise TokenError(f"العمر بالثواني بين {MIN_TTL} و{MAX_TTL}")
        label = str(label or "")[:64]
        now = int(self.clock())
        claims = {"jti": secrets.token_hex(12), "scp": scp, "iat": now,
                  "exp": now + ttl_seconds, "lbl": label}
        body = _b64e(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
        sig = _b64e(hmac.new(self.key, f"{PREFIX}.{body}".encode(), hashlib.sha256).digest())
        meta = {k: claims[k] for k in ("jti", "scp", "iat", "exp", "lbl")}
        # الأثر قبل التسليم: سجل لا يوقّع ⇒ لا رمز (RuntimeError يصعد للنقطة ⇒ 503)
        self.audit("auth.token_issued", {"jti": meta["jti"], "scopes": scp,
                                         "exp": meta["exp"], "label": label})
        with self._lock:
            self._issued[meta["jti"]] = meta
            self._save_local()
        durable = self._push(meta["jti"])
        return {"token": f"{PREFIX}.{body}.{sig}", "jti": meta["jti"], "scopes": scp,
                "expires_at": meta["exp"], "label": label, "durable": durable,
                "note": "الرمز يُعرض مرة واحدة ولا يُخزن — احفظه الآن"}

    def revoke(self, jti: str) -> Dict[str, Any]:
        jti = str(jti or "").strip()
        if not jti or len(jti) > 64:
            raise TokenError("معرّف رمز غير صالح")
        self.audit("auth.token_revoked", {"jti": jti})
        with self._lock:
            already = jti in self._revoked
            self._revoked.setdefault(jti, self.clock())
            self._save_local()
        return {"jti": jti, "revoked": True, "already": already,
                "known": jti in self._issued, "durable": self._push(jti)}

    # ------------------------------------------------------------- التحقق
    def check(self, token: Any, scope: str) -> Dict[str, Any]:
        """حكم صريح بسبب — لا استثناء. ``scope`` يجب أن يكون نطاقًا معلنًا."""
        if scope not in SCOPES:
            return {"ok": False, "reason": "scope_not_delegable"}
        if not isinstance(token, str) or not token.startswith(PREFIX + ".") or len(token) > 2048:
            return {"ok": False, "reason": "not_a_token"}
        parts = token.split(".")
        if len(parts) != 3:
            return {"ok": False, "reason": "malformed"}
        try:
            expected = hmac.new(self.key, f"{parts[0]}.{parts[1]}".encode(),
                                hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64d(parts[2])):
                return {"ok": False, "reason": "bad_signature"}
            claims = json.loads(_b64d(parts[1]))
        except (ValueError, TypeError):
            return {"ok": False, "reason": "malformed"}
        if not self._remote_loaded and self.clock() - self._last_load_try >= 30:
            self.load_remote()                 # إعادة محاولة محدودة المعدل
        if not self._remote_loaded:
            return {"ok": False, "reason": "revocations_not_loaded"}
        jti = str(claims.get("jti"))
        if jti in self._revoked:
            return {"ok": False, "reason": "revoked", "jti": jti}
        if self.clock() >= float(claims.get("exp", 0)):
            return {"ok": False, "reason": "expired", "jti": jti}
        if scope not in (claims.get("scp") or []):
            return {"ok": False, "reason": "scope_denied", "jti": jti,
                    "scopes": claims.get("scp")}
        return {"ok": True, "jti": jti, "scopes": claims.get("scp"), "exp": claims.get("exp"),
                "label": claims.get("lbl", "")}

    def introspect(self, token: Any) -> Dict[str, Any]:
        """ما يملكه رمز (بلا كشف سر) — للتحقق قبل الاستعمال."""
        first = next(iter(SCOPES))
        res = self.check(token, first)
        if res["ok"] or res.get("reason") == "scope_denied":
            return {"valid": True, "jti": res["jti"], "scopes": res["scopes"],
                    "exp": res.get("exp") or self._issued.get(res["jti"], {}).get("exp")}
        return {"valid": False, "reason": res["reason"]}

    def list(self) -> List[Dict[str, Any]]:
        now = self.clock()
        out = []
        for jti, meta in sorted(self._issued.items(), key=lambda kv: -kv[1].get("iat", 0)):
            state = "revoked" if jti in self._revoked else (
                "expired" if now >= meta.get("exp", 0) else "active")
            out.append({**meta, "state": state})
        return out

    def status(self) -> Dict[str, Any]:
        states = [t["state"] for t in self.list()]
        return {"scopes": SCOPES, "master_only": list(MASTER_ONLY),
                "ttl_seconds": {"min": MIN_TTL, "max": MAX_TTL},
                "durable_backend": None if self.store is None else type(self.store).__name__,
                "revocations_loaded": self._remote_loaded,
                "tokens": {s: states.count(s) for s in ("active", "expired", "revoked")},
                "legacy_root_key": "مقبول لكل العمليات كالمفتاح الرئيسي (توافق) — "
                                   "يوصى بالمفتاح المشتق ورموز محدودة للأدوات والأجهزة"}


_MGR: Optional[TokenManager] = None


def get_manager() -> TokenManager:
    global _MGR
    if _MGR is None:
        try:
            from config import DATA_DIR
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from backend.config import DATA_DIR
        _MGR = TokenManager(Path(DATA_DIR))
        _MGR.load_remote()
    return _MGR
