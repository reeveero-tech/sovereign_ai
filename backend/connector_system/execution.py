# -*- coding: utf-8 -*-
"""R-840: محرك التنفيذ — مسار واحد لكل الموصلات مع الصمود للفشل.

- تجريدات موحدة: query / execute / sync / webhook.
- Timeouts، backoff أسّي، قاطع دائرة لكل موصل، حد معدل.
- Idempotency keys لكل عملية كتابة.
- 401 → محاولة تجديد واحدة → إعادة، وإلا حالة expired مع إشعار.
- سجل كل استدعاء: الموصل، العملية، النتيجة، الزمن — دون أي سر.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from . import auth_engine
from .contract import ConnectorDefinition
from .credentials import CredentialStore
from .policy import OrgPolicy

logger = logging.getLogger("sovereign.connector_system")

Transport = Callable[..., object]


class ExecutionError(Exception):
    pass


class ScopeDeniedError(ExecutionError):
    pass


class RequiresConnectionError(ExecutionError):
    """الوكيل يحتاج اتصالًا غير موجود — تُرفق بطاقة «يتطلب اتصالًا»."""

    def __init__(self, connector_id: str, operation: str, missing_scopes: List[str]):
        self.connector_id = connector_id
        self.operation = operation
        self.missing_scopes = missing_scopes
        super().__init__(f"يتطلب اتصالًا: {connector_id}.{operation} (نطاقات ناقصة: {missing_scopes})")


class ConnectorExecutionError(ExecutionError):
    pass


class ConnectorUnavailableError(ExecutionError):
    pass


class RateLimitedError(ExecutionError):
    pass


@dataclass
class CircuitBreaker:
    failures: int = 0
    threshold: int = 3
    cooldown_s: float = 60.0
    opened_at: Optional[float] = None

    def allows(self, now: float) -> bool:
        if self.opened_at is None:
            return True
        return (now - self.opened_at) >= self.cooldown_s  # نصف مفتوح

    def record(self, ok: bool, now: float) -> None:
        if ok:
            self.failures, self.opened_at = 0, None
            return
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = now


@dataclass
class TokenBucket:
    rate: float = 10.0
    capacity: float = 10.0
    tokens: float = 10.0
    last: float = 0.0

    def try_acquire(self, now: float) -> bool:
        self.tokens = min(self.capacity,
                          self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class Executor:
    """محرك واحد خلف سجل الموصلات — لا كود تنفيذ خاص بمنصة."""

    def __init__(self, state_dir, credentials: CredentialStore, policy: OrgPolicy,
                 http: Optional[Transport] = None, clock: Callable[[], float] = time.time,
                 registry=None):
        self.state_dir = str(state_dir)
        self.credentials = credentials
        self.policy = policy
        self._http = http or self._default_http
        self.clock = clock
        self.registry = registry
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._idempotency: Dict[str, str] = {}
        self._call_log_path = os.path.join(self.state_dir, "call_log.jsonl")
        self._lock = threading.RLock()  # _log داخل قسم idempotency — إعادة دخول آمنة
        os.makedirs(self.state_dir, exist_ok=True)

    # ------------------------------------------------------------ النقل
    def _default_http(self, method: str, url: str, **kw) -> object:
        import httpx
        timeout = kw.pop("timeout", 20.0)
        cert = kw.pop("cert", None)
        if cert:
            kw["cert"] = cert
        return httpx.request(method, url, timeout=timeout, **kw)

    def _definition(self, connector_id: str) -> ConnectorDefinition:
        if self.registry is None:
            from .registry import default_registry
            self.registry = default_registry()
        return self.registry.get(connector_id)

    # ------------------------------------------------------------ الحواجز
    def _breaker(self, cid: str, d: ConnectorDefinition) -> CircuitBreaker:
        if cid not in self._breakers:
            self._breakers[cid] = CircuitBreaker(cooldown_s=60.0)
        return self._breakers[cid]

    def _bucket(self, cid: str, d: ConnectorDefinition) -> TokenBucket:
        if cid not in self._buckets:
            self._buckets[cid] = TokenBucket(rate=d.rate_limit_rps)
        return self._buckets[cid]

    def _log(self, record: Dict[str, Any]) -> None:
        """سجل الاستدعاء — لا سر إطلاقًا (تطبيق سياسة عدم التسريب رقم ١٩)."""
        safe = {k: v for k, v in record.items() if k not in ("secret", "token")}
        with self._lock:
            with open(self._call_log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(safe, ensure_ascii=False) + "\n")

    def call_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not os.path.exists(self._call_log_path):
            return []
        with open(self._call_log_path, encoding="utf-8") as fh:
            lines = fh.readlines()
        return [json.loads(x) for x in lines[-limit:]]

    # ------------------------------------------------------------ الاختبار
    def test_connection(self, connector_id: str, actor: str = "owner") -> tuple:
        """اختبار اتصال: أرخص عملية قراءة في الموصل — أو ping عام."""
        d = self._definition(connector_id)
        if "test_connection" in d.operations:
            op = d.operations["test_connection"]
            try:
                self.run(connector_id, "test_connection", {}, actor=actor)
                return True, "نجح اختبار الاتصال"
            except ExecutionError as exc:
                return False, str(exc)[:200]
        return True, "لا توجد عملية اختبار معرفة — الموصل مسجل"

    # ------------------------------------------------------------ التنفيذ
    def run(self, connector_id: str, operation: str, inputs: Dict[str, Any],
            actor: str = "agent", idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        d = self._definition(connector_id)
        op = d.operation(operation)

        # ١) سياسة المؤسسة قبل أي شيء
        self.policy.check_execution(connector_id, operation, actor)

        # ٢) قاطع الدائرة وحد المعدل — صحة الموصل أولًا (عزل الفشل)
        now = self.clock()
        br = self._breaker(connector_id, d)
        if not br.allows(now):
            raise ConnectorUnavailableError(
                f"قاطع الدائرة مفتوح لـ{connector_id} — خدمة معطلة (عزل الفشل)")
        if not self._bucket(connector_id, d).try_acquire(now):
            raise RateLimitedError(f"حد المعدل مستنفد لـ{connector_id}")

        # ٣) الصلاحية: أقل نطاق يغطي العملية — لا full access
        cred = self.credentials.find_valid(connector_id, sorted(op.scopes))
        if cred is None:
            # تجديد صامت: اعتماد منتهٍ قابل للتجديد يُجدد قبل الرفض (معيار ١١)
            for cand in self.credentials.list_for_connector(connector_id):
                if cand.status == "expired" and cand.refresh_supported \
                        and set(op.scopes) <= set(cand.scopes):
                    try:
                        cred = auth_engine.refresh_credential(
                            self.credentials, cand, self._http)
                    except auth_engine.RefreshError:
                        break
        if cred is None:
            existing = self.credentials.list_for_connector(connector_id)
            if not existing:
                raise RequiresConnectionError(connector_id, operation,
                                              sorted(op.scopes))
            raise ScopeDeniedError(
                f"صلاحية غير كافية — توسيع النطاق مطلوب: {sorted(op.scopes)}")

        # ٤) Idempotency لعمليات الكتابة
        ikey = idempotency_key or f"{connector_id}:{operation}:{actor}"
        if op.is_write:
            with self._lock:
                if ikey in self._idempotency:
                    self._log({"ts": now, "connector": connector_id,
                               "operation": operation, "actor": actor,
                               "status": "idempotent_replay", "duration_ms": 0.0})
                    return {"ok": True, "idempotent_replay": True}
                self._idempotency[ikey] = "pending"

        handler = d.handlers.get(operation)
        if handler is None:
            raise ExecutionError(f"لا معالج للعملية {connector_id}.{operation}")

        # ٥) التنفيذ مع إعادة المحاولة + 401 → تجديد واحد
        started = time.time()
        last_exc: Optional[Exception] = None
        refreshed = False
        for attempt in range(max(1, d.retry_max_attempts)):
            try:
                material = auth_engine.resolve(self.credentials, cred, self._http)
                result = handler(material, dict(inputs), self._http)
                br.record(True, self.clock())
                self.credentials.mark_used(cred.id)
                duration_ms = round((time.time() - started) * 1000.0, 1)
                self._log({"ts": self.clock(), "connector": connector_id,
                           "operation": operation, "actor": actor,
                           "status": "ok", "duration_ms": duration_ms})
                out = dict(result)
                out.setdefault("ok", True)
                return out
            except _Unauthorized as exc:
                # 401: محاولة تجديد واحدة فقط — ثم حالة expired
                if cred.refresh_supported and not refreshed:
                    refreshed = True
                    try:
                        cred = auth_engine.refresh_credential(
                            self.credentials, cred, self._http)
                        continue
                    except auth_engine.RefreshError as rerr:
                        cred.status = "expired"
                        cred.last_error = str(rerr)[:200]
                        self.credentials.update(cred)
                        self._log({"ts": self.clock(), "connector": connector_id,
                                   "operation": operation, "actor": actor,
                                   "status": "expired", "error": cred.last_error})
                        raise ScopeDeniedError(
                            "انتهت صلاحية التوكن — أعد الاتصال") from rerr
                cred.status = "expired"
                self.credentials.update(cred)
                raise ScopeDeniedError("انتهت صلاحية التوكن — أعد الاتصال") from exc
            except (_Retryable, _RateLimited429) as exc:
                last_exc = exc
                if attempt < d.retry_max_attempts - 1:
                    time.sleep(d.retry_backoff_base_s * (2 ** attempt))  # backoff أسّي
                    continue
            except ExecutionError:
                raise
            except Exception as exc:
                last_exc = exc
                break

        br.record(False, self.clock())
        # لا تسميم حالة الاعتماد بفشل خادم (5xx) — الأثر في السجل والقاطع فقط
        self._log({"ts": self.clock(), "connector": connector_id,
                   "operation": operation, "actor": actor,
                   "status": "error", "error": str(last_exc or "")[:200]})
        raise ConnectorExecutionError(str(last_exc or "فشل التنفيذ"))


class _Unauthorized(Exception):
    pass


class _Retryable(Exception):
    pass


class _RateLimited429(Exception):
    pass


def classify_http(status_code: int) -> Optional[Exception]:
    """تصنيف رد المزود إلى سلوك المحرك — لا إعادة محاولة على 401 بلا تجديد."""
    if status_code == 401:
        return _Unauthorized()
    if status_code == 429:
        return _RateLimited429()
    if 500 <= status_code < 600:
        return _Retryable()
    return None
