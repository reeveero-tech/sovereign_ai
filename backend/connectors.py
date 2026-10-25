# -*- coding: utf-8 -*-
"""R-756 (ROADMAP_V5 ٤.١): عقد الموصل المعزول.

قالب واحد لكل موصل:
- **مصادقة مملوكة:** السر في خزينة R-752 باسم `connector.<اسم>` ونطاق
  `connector:<اسم>` — الموصل لا يرى إلا سره، ولا سر في الأثر أو المخرجات.
- **أذونات نطاقية لكل فعل:** منحة المالك (`grant`) تحدد الأفعال المسموحة؛ لا
  منحة = لا فعل.
- **انتهاء صلاحية وتجديد ورفض آمن:** منحة بـ`ttl_s` تنتهي فتُرفض حتى `renew`.
- **سحب فوري:** `revoke` يُحفظ على القرص، وحالة المنح تُقرأ من القرص عند **كل**
  استدعاء — سحب من عملية أخرى يقطع الاستدعاء التالي فورًا.
- **عزل الفشل:** قاطع دائرة لكل موصل (عتبة فشل متتالٍ → مفتوح حتى التهدئة، ثم
  محاولة واحدة نصف مفتوحة). فشل موصل لا يمس غيره.
- **أثر:** نية `connector.call` قبل التنفيذ (فشلها = لا تنفيذ) ونتيجة بعده.

أول موصل حقيقي: `webhook_connector` — إشعار HTTP POST بـBearer + Idempotency-Key،
وفحص صحة GET، وحارس SSRF (http/https فقط، لا عناوين خاصة/محلية إلا بإذن صريح
للاختبار).
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import socket
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import urlparse

AuditFn = Callable[[str, Dict[str, Any]], Any]
logger = logging.getLogger("sovereign.connectors")


class ConnectorError(Exception):
    pass


class PermissionDenied(ConnectorError):
    pass


class CredentialError(ConnectorError):
    pass


class ConnectorUnavailable(ConnectorError):
    pass


@dataclass
class ConnectorSpec:
    name: str
    description: str
    # فعل → معالج(credential, **inputs)
    actions: Dict[str, Callable[..., Any]]
    inputs: Dict[str, Dict[str, str]] = field(default_factory=dict)
    external_actions: frozenset = frozenset()

    @property
    def secret_name(self) -> str:
        return f"connector.{self.name}"

    @property
    def scope(self) -> str:
        return f"connector:{self.name}"


def _check_url(url: str, allow_loopback: bool) -> None:
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("عنوان الموصل يجب أن يكون http/https بمضيف")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80))
        addrs = {ipaddress.ip_address(i[4][0]) for i in infos}
    except (socket.gaierror, ValueError):
        addrs = set()
    for a in addrs:
        if (a.is_loopback or a.is_private or a.is_link_local or a.is_reserved
                or a.is_multicast or a.is_unspecified) and not allow_loopback:
            raise ValueError("عنوان الموصل خاص/محلي — مرفوض (حارس SSRF)")


def webhook_connector(name: str, url: str, *, allow_loopback: bool = False,
                      timeout_s: float = 10.0) -> ConnectorSpec:
    _check_url(url, allow_loopback)

    def send(credential: str, text: str, idempotency_key: Optional[str] = None):
        import httpx
        headers = {"Authorization": f"Bearer {credential}",
                   "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        r = httpx.post(url, json={"text": text}, headers=headers, timeout=timeout_s,
                       follow_redirects=False)
        if not (200 <= r.status_code < 300):
            raise ConnectorError(f"HTTP {r.status_code}")
        return {"status": r.status_code, "accepted": True}

    def health(credential: str):
        import httpx
        r = httpx.get(url, headers={"Authorization": f"Bearer {credential}"},
                      timeout=timeout_s, follow_redirects=False)
        if not (200 <= r.status_code < 300):
            raise ConnectorError(f"HTTP {r.status_code}")
        return {"healthy": True}

    return ConnectorSpec(
        name=name, description=f"إشعار webhook ({urlparse(url).hostname})",
        actions={"send": send, "health": health},
        inputs={"send": {"text": "نص الإشعار", "idempotency_key": "مفتاح منع التكرار"},
                "health": {}},
        external_actions=frozenset({"send"}))


class ConnectorHub:
    def __init__(self, vault, state_path, audit: AuditFn, *,
                 failure_threshold: int = 3, cooldown_s: float = 60.0,
                 clock: Callable[[], float] = time.time):
        self.vault = vault
        self.state_path = Path(state_path)
        self._audit_fn = audit
        self.failure_threshold = int(failure_threshold)
        self.cooldown_s = float(cooldown_s)
        self.clock = clock
        self._specs: Dict[str, ConnectorSpec] = {}
        self._breakers: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ الحالة
    def _load(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save(self, grants: Dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.state_path.parent), prefix=".grants-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(grants, fh, ensure_ascii=False, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.state_path)

    def _audit(self, event: str, payload: Dict[str, Any]) -> None:
        self._audit_fn(event, payload)

    def register(self, spec: ConnectorSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"موصل مسجل مرتين: {spec.name}")
        self._specs[spec.name] = spec
        self._breakers[spec.name] = {"failures": 0, "opened_at": None}

    def names(self) -> Iterable[str]:
        return list(self._specs)

    def spec(self, name: str) -> ConnectorSpec:
        if name not in self._specs:
            raise KeyError(name)
        return self._specs[name]

    # ------------------------------------------------------------ المنح
    def grant(self, name: str, actions: Iterable[str], actor: str,
              ttl_s: Optional[float] = None) -> Dict[str, Any]:
        spec = self.spec(name)
        acts = sorted(set(actions))
        unknown = [a for a in acts if a not in spec.actions]
        if unknown:
            raise ValueError(f"أفعال غير معروفة للموصل {name}: {unknown}")
        now = self.clock()
        g = {"actions": acts, "granted_at": now, "granted_by": actor,
             "expires_at": (now + ttl_s) if ttl_s is not None else None,
             "revoked": False}
        self._audit("connector.grant", {"connector": name, "actions": acts,
                                        "expires_at": g["expires_at"], "actor": actor})
        with self._lock:
            grants = self._load()
            grants[name] = g
            self._save(grants)
        return g

    def renew(self, name: str, ttl_s: float, actor: str) -> Dict[str, Any]:
        with self._lock:
            grants = self._load()
            g = grants.get(name)
            if not g or g.get("revoked"):
                raise PermissionDenied(f"لا منحة قائمة للتجديد: {name} (المسحوبة تتطلب منحة جديدة)")
            self._audit("connector.renew", {"connector": name, "ttl_s": ttl_s, "actor": actor})
            g["expires_at"] = self.clock() + ttl_s
            self._save(grants)
        return g

    def revoke(self, name: str, actor: str) -> None:
        self._audit("connector.revoke", {"connector": name, "actor": actor})
        with self._lock:
            grants = self._load()
            g = grants.get(name, {"actions": []})
            g.update(revoked=True, revoked_at=self.clock(), revoked_by=actor)
            grants[name] = g
            self._save(grants)

    def _check_grant(self, name: str, action: str) -> None:
        g = self._load().get(name)               # من القرص عند كل استدعاء — سحب فوري
        reason = None
        if g is None:
            reason = "لا منحة"
        elif g.get("revoked"):
            reason = "التفويض مسحوب"
        elif g.get("expires_at") is not None and self.clock() >= g["expires_at"]:
            reason = "المنحة منتهية — تتطلب تجديدًا"
        elif action not in g.get("actions", []):
            reason = f"الفعل {action} خارج المنحة"
        if reason:
            self._audit("connector.denied", {"connector": name, "action": action,
                                             "reason": reason})
            raise PermissionDenied(f"{name}.{action}: {reason}")

    # ------------------------------------------------------------ الاستدعاء
    def _breaker_allows(self, name: str) -> bool:
        b = self._breakers[name]
        if b["opened_at"] is None:
            return True
        return self.clock() - b["opened_at"] >= self.cooldown_s   # نصف مفتوح

    def _record(self, name: str, ok: bool) -> None:
        b = self._breakers[name]
        if ok:
            b["failures"], b["opened_at"] = 0, None
            return
        b["failures"] += 1
        if b["failures"] >= self.failure_threshold:
            b["opened_at"] = self.clock()

    def call(self, name: str, action: str, inputs: Optional[Dict[str, Any]] = None,
             actor: str = "agent") -> Dict[str, Any]:
        spec = self.spec(name)
        if action not in spec.actions:
            raise PermissionDenied(f"فعل غير معروف: {name}.{action}")
        inputs = dict(inputs or {})
        allowed = set(spec.inputs.get(action, {}))
        unknown = sorted(set(inputs) - allowed)
        if unknown:
            raise ValueError(f"مدخلات غير معلنة: {unknown}")
        self._check_grant(name, action)
        if not self._breaker_allows(name):
            self._audit("connector.unavailable", {"connector": name, "action": action})
            raise ConnectorUnavailable(f"{name}: القاطع مفتوح بعد فشل متتالٍ — معزول")
        try:
            cred = self.vault.get(spec.secret_name, capability=spec.scope,
                                  actor=f"connector:{name}")
        except Exception as exc:
            self._audit("connector.denied", {"connector": name, "action": action,
                                             "reason": f"credential:{type(exc).__name__}"})
            raise CredentialError(f"{name}: سر الموصل غير متاح ({type(exc).__name__})") from exc

        self._audit("connector.call", {"connector": name, "action": action,
                                       "phase": "intent", "actor": actor,
                                       "idempotency_key": inputs.get("idempotency_key")})
        start = time.perf_counter()
        ok, result, error = True, None, None
        try:
            result = spec.actions[action](cred, **inputs)
        except Exception as exc:  # فشل المصدر يُعزل ويُوثق — لا يسقط النظام
            ok, error = False, self.vault.redact(f"{type(exc).__name__}: {exc}")[:200]
        self._record(name, ok)
        fp = hashlib.sha256(json.dumps(result if ok else error, sort_keys=True,
                                       default=str, ensure_ascii=False).encode()).hexdigest()[:16]
        out = {"ok": ok, "connector": name, "action": action, "result": result,
               "error": error, "duration_ms": round((time.perf_counter() - start) * 1000, 2),
               "result_fingerprint": fp}
        self._audit("connector.call", {"connector": name, "action": action,
                                       "phase": "result", "ok": ok, "error": error,
                                       "result_fingerprint": fp, "actor": actor})
        return out

    def status(self) -> Dict[str, Any]:
        grants = self._load()
        now = self.clock()
        out = {}
        for n, s in self._specs.items():
            g = grants.get(n) or {}
            b = self._breakers[n]
            out[n] = {"description": s.description, "actions": sorted(s.actions),
                      "granted": [] if g.get("revoked") else g.get("actions", []),
                      "revoked": bool(g.get("revoked")),
                      "expired": bool(g.get("expires_at") is not None and now >= g["expires_at"]),
                      "breaker": "open" if b["opened_at"] is not None else "closed",
                      "consecutive_failures": b["failures"]}
        return {"connectors": out,
                "contract": "سر في الخزينة بنطاق الموصل + منحة لكل فعل + سحب فوري + قاطع دائرة"}


def _ledger_audit(event: str, payload: Dict[str, Any]) -> None:
    from memory.core import get_core
    get_core().append_event("connector_call", {"op": event, **payload},
                            user=payload.get("actor"))


_HUB: Optional[ConnectorHub] = None


def get_hub() -> ConnectorHub:
    """الموزع الحي: موصلات يضبطها المالك بالبيئة (لا شيء افتراضيًا)."""
    global _HUB
    if _HUB is None:
        try:
            from sovereign.secrets_vault import get_vault
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from backend.sovereign.secrets_vault import get_vault
        root = Path(__file__).resolve().parents[1] / "data" / "connectors"
        hub = ConnectorHub(get_vault(), Path(os.environ.get(
            "SOVEREIGN_CONNECTORS_STATE", str(root / "grants.json"))), _ledger_audit)
        url = os.environ.get("SOVEREIGN_WEBHOOK_URL")
        if url:
            try:
                hub.register(webhook_connector("notify", url=url))
            except ValueError:  # TOLERATED: عنوان مرفوض بحارس SSRF — لا موصل (غيابه ظاهر في الحالة)
                logger.warning("R-756: SOVEREIGN_WEBHOOK_URL مرفوض بحارس SSRF — لا موصل notify")
        _HUB = hub
    return _HUB
