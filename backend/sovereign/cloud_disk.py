"""R-719 — قرص المشروع وذاكرته على Supabase (بأمر المالك 2026-10-22).

طبقة استمرار سحابية فوق PostgREST بسرّ خدمة المشروع (لا يدخل git أبدًا):

- جدول `disk` (KV بالإدراج-التحديث) — «القرص» الدائم: نسخ الذاكرة المخزنة
  (مشفرّة AES-256-GCM قبل الوصول إلى هنا — عقد المخزن «دائم، مشفر» قائم).
- جدول `disk_log` (إلحاقي صرف) — «الذاكرة» الجارية: أحداث لا تُعدل ولا تُحذف.

المبادئ:
- معطلة افتراضيًا (نمط Ollama R-704): لا تُفعّل إلا بـ SUPABASE_URL
  + SUPABASE_SECRET_KEY معًا (fail-closed للإعداد).
- best-effort لا fail-closed: القرص السحابي بعيد → الكتابة المحلية تكتمل
  وتُسجّل تحذيرات مسموعة؛ الاسترجاع عند الإقلاع يحدث فقط عند غياب النسخة
  المحلية (إعادة نشر بقرص فارغ) — الحدودية موثقة في docs/SECURITY.md.
- لا سلاسل مفاتيح في السجلات: البصمة فقط.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------- الإعداد (نمط Ollama R-704: بيئة ثم ملف، والبيئة تعلو) ----------

import os

# R-721 (تصويبي): ملف الإعداد الافتراضي هو .env بجذر المشروع — كما يوثق
# .env.example (كان الكود يقرأ SUPABASE_ENV_FILE فقط — تناقض وثقه المراجع).
# قابل للحقن في الاختبارات عبر monkeypatch لهذا المسار.
_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _supabase_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """قراءة إعداد Supabase: متغير البيئة أولًا ثم ملف الإعداد (SUPABASE_ENV_FILE
    للعزل في الاختبارات، وإلا .env بجذر المشروع — كما في Ollama R-704).
    البيئة تعلو على الملف دائمًا."""
    value = os.getenv(name)
    if value:
        return value
    env_file = os.getenv("SUPABASE_ENV_FILE") or _DOTENV_PATH
    if env_file and Path(env_file).is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(name + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:  # TOLERATED: ملف .env غير مقروء — القيمة الافتراضية (نمط R-680)
            pass
    return default


SUPABASE_URL = _supabase_env("SUPABASE_URL")
SUPABASE_SECRET_KEY = _supabase_env("SUPABASE_SECRET_KEY")
SUPABASE_TIMEOUT_SECONDS = float(_supabase_env("SUPABASE_TIMEOUT_SECONDS", "10"))


def cloud_disk_enabled() -> bool:
    """الطبقة مفعلة فقط إذا توفر الرابط وسرّ الخدمة معًا (لا علم منفصل).
    تُقرأ ديناميكيًا (بيئة/ملف) — لا تُثبت عند الاستيراد، لتنعكس التغييرات
    والاختبارات فورًا."""
    return bool(_supabase_env("SUPABASE_URL") and _supabase_env("SUPABASE_SECRET_KEY"))


def key_fingerprint(secret: str) -> str:
    """بصمة المفتاح للسجلات — لا السر نفسه أبدًا."""
    return hashlib.sha256(secret.encode()).hexdigest()[:16]


def get_cloud_disk() -> Optional["SupabaseDisk"]:
    """المثيل المخزن للطبقة، أو None إذا كانت معطلة (نمط get_* في المشروع).

    R-721 (تصويبي): المثيل يُخزَّن — لا عميل httpx جديد لكل استدعاء (تسريب
    اتصالات وثّقه المراجع). يتجدد المثيل فقط إذا تغير الإعداد."""
    global _CACHED_DISK, _CACHED_SIG
    url = _supabase_env("SUPABASE_URL")
    key = _supabase_env("SUPABASE_SECRET_KEY")
    if not (url and key):
        return None
    sig = (url, key, float(_supabase_env("SUPABASE_TIMEOUT_SECONDS", "10")))
    if _CACHED_DISK is not None and _CACHED_SIG == sig:
        return _CACHED_DISK
    _CACHED_DISK = SupabaseDisk(base_url=sig[0], service_key=sig[1], timeout=sig[2])
    _CACHED_SIG = sig
    return _CACHED_DISK


_CACHED_DISK: Optional["SupabaseDisk"] = None
_CACHED_SIG: Optional[tuple] = None


# ---------- العميل ----------

class SupabaseDisk:
    """عميل PostgREST رفيع لقرص Supabase — لا اعتماديات جديدة (httpx مثبتة).

    قابلة للحقن للنقل (transport) للاختبارات بلا شبكة (httpx.MockTransport).
    """

    def __init__(
        self,
        base_url: str,
        service_key: str,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
        )

    # -------------------------
    # القرص: KV بالإدراج-التحديث
    # -------------------------

    def save_blob(self, namespace: str, key: str, payload: Dict[str, Any]) -> bool:
        """upsert للمفتاح المركّب (namespace, key) — يعيد True عند النجاح."""
        try:
            resp = self._client.post(
                "/rest/v1/disk",
                json={"namespace": namespace, "key": key, "payload": payload},
                headers={"Prefer": "resolution=merge-duplicates"},
            )
            if resp.status_code in (200, 201, 204):
                return True
            logger.warning(
                "R-719 [DISK]: رفض حفظ %s/%s — HTTP %s: %s",
                namespace, key, resp.status_code, resp.text[:200],
            )
            return False
        except httpx.HTTPError as exc:
            logger.warning("R-719 [DISK]: القرص السحابي بعيد (%s/%s): %s",
                           namespace, key, exc)
            return False

    def load_blob(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        """قراءة نسخة بالمفتاح المركّب — None عند الغياب أو الفشل (لا استثناء)."""
        try:
            resp = self._client.get(
                "/rest/v1/disk",
                params={"select": "payload", "namespace": f"eq.{namespace}",
                       "key": f"eq.{key}", "limit": "1"},
            )
            if resp.status_code != 200:
                logger.warning("R-719 [DISK]: فشل قراءة %s/%s — HTTP %s",
                               namespace, key, resp.status_code)
                return None
            rows = resp.json()
            if not rows:
                return None
            return rows[0].get("payload")
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("R-719 [DISK]: فشل قراءة %s/%s: %s", namespace, key, exc)
            return None

    def list_blobs(self, namespace: str, limit: int = 1000, offset: int = 0) -> Optional[List[Dict[str, Any]]]:
        """R-800: كل مفاتيح فضاء أسماء (key + payload) — None عند الفشل (لا استثناء)."""
        try:
            resp = self._client.get(
                "/rest/v1/disk",
                params={"select": "key,payload", "namespace": f"eq.{namespace}",
                        "order": "key.asc", "limit": str(limit), "offset": str(offset)},
            )
            if resp.status_code != 200:
                logger.warning("R-800 [DISK]: فشل سرد %s — HTTP %s", namespace, resp.status_code)
                return None
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("R-800 [DISK]: فشل سرد %s: %s", namespace, exc)
            return None

    # -------------------------
    # الذاكرة الجارية: سجل إلحاقي صرف
    # -------------------------

    def append_log(self, namespace: str, payload: Dict[str, Any]) -> bool:
        """إلحاق حدث — لا تعديل ولا حذف (append-only)."""
        try:
            resp = self._client.post(
                "/rest/v1/disk_log",
                json={"namespace": namespace, "payload": payload},
            )
            if resp.status_code in (200, 201, 204):
                return True
            logger.warning("R-719 [DISK]: رفض إلحاق %s — HTTP %s: %s",
                           namespace, resp.status_code, resp.text[:200])
            return False
        except httpx.HTTPError as exc:
            logger.warning("R-719 [DISK]: القرص السحابي بعيد (إلحاق %s): %s",
                           namespace, exc)
            return False

    def pull_log(self, namespace: str, since_id: int = 0,
                 limit: int = 1000) -> List[Dict[str, Any]]:
        """قراءة تدريجية: الأحداث بعد since_id بالترتيب الصاعد."""
        try:
            resp = self._client.get(
                "/rest/v1/disk_log",
                params={
                    "select": "id,payload,created_at",
                    "namespace": f"eq.{namespace}",
                    "id": f"gt.{since_id}",
                    "order": "id.asc",
                    "limit": str(limit),
                },
            )
            if resp.status_code != 200:
                logger.warning("R-719 [DISK]: فشل سحب السجل %s — HTTP %s",
                               namespace, resp.status_code)
                return []
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("R-719 [DISK]: فشل سحب السجل %s: %s", namespace, exc)
            return []

    # -------------------------
    # فحص
    # -------------------------

    def ping(self) -> bool:
        """فحص حي بلا أثر: عدد صفي الرؤوس — يعيد True إذا ردّ الخادم."""
        try:
            resp = self._client.get(
                "/rest/v1/disk",
                params={"select": "namespace", "limit": "1"},
            )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def status(self) -> Dict[str, Any]:
        """حالة الطبقة للمراقبة — بلا سر في المخرجات (بصمة فقط)."""
        return {
            "enabled": True,
            "base_url": self.base_url,
            "key_fingerprint": key_fingerprint(self.service_key),
            "timeout_seconds": self.timeout,
            "reachable": self.ping(),
        }
