"""عميل الوسائط — توليد الصور (R-747 — البند ٣.٥).

بأمر المالك: «استخدم خدمة وسائط لا تتطلب إرسال البيانات لطرف ثالث».

الخدمة: LocalAI (مفتوح المصدر، MIT، يعمل على عتاد المالك) — يقدّم عقد
OpenAI Images: POST {base}/images/generations → {"data": [{"b64_json"|"url"}]}.
https://localai.io/docs/features/image-generation/

حارس السيادة (جوهر الأمر) — is_self_hosted():
- لا يُرسل أي طلب إلا إلى مضيف ذاتي الاستضافة: loopback، عنوان خاص
  (RFC1918، ULA fc00::/7، link-local)، شبكة Fly الخاصة (.internal /
  .flycast)، .local / .localhost، أو اسم خدمة بلا نقاط (docker compose).
- أي مضيف عام (اسمًا أو عنوانًا) → رفض **قبل أي اتصال**، فلا يغادر الوصف
  ولا المفتاح العملية.
- لا تتبّع لإعادة التوجيه (follow_redirects=False): الخادم لا يستطيع تحويل
  الطلب إلى طرف ثالث.
- الاستجابة بـ url تُجلب فقط من نفس مضيف الخدمة (نفس scheme+host+port).

مبادئ قائمة (نمط R-737/R-739/R-740):
- معطل افتراضيًا (MEDIA_ENABLED) — لا اتصال ضمني.
- لا يرفع أبدًا: أي فشل يعيد None، والسبب في last_outcome() بلا محتوى.
- صورة حقيقية فقط: تحقق base64 صارم + توقيع ملف (PNG/JPEG/WEBP/GIF) + حد حجم.
- لا مفتاح ولا وصف ولا صورة في السجلات — تصنيف الخطأ فقط.
"""

import base64
import ipaddress
import logging
from typing import Optional, Tuple
from urllib.parse import urljoin, urlsplit

logger = logging.getLogger("sovereign.media")

_LAST_OUTCOME = {"result": "none"}
_PRIVATE_SUFFIXES = (".internal", ".flycast", ".local", ".localhost")


def last_outcome() -> dict:
    return dict(_LAST_OUTCOME)


def _set(result: str) -> None:
    global _LAST_OUTCOME
    _LAST_OUTCOME = {"result": result}


def is_self_hosted(url: str) -> bool:
    """هل العنوان يشير إلى مضيف ذاتي الاستضافة؟ (لا DNS — حكم على الشكل)."""
    try:
        parts = urlsplit(str(url))
        host = parts.hostname
        if parts.scheme not in ("http", "https") or not host:
            return False
        parts.port  # يرفع ValueError لمنفذ فاسد
    except ValueError:
        return False
    host = host.lower().rstrip(".")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        return bool(ip.is_loopback or ip.is_private or ip.is_link_local)
    if host == "localhost" or host.endswith(_PRIVATE_SUFFIXES):
        return True
    return "." not in host  # اسم خدمة محلي (docker compose / شبكة خاصة)


def sniff_image(data: bytes) -> Optional[str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def _same_origin(a: str, b: str) -> bool:
    pa, pb = urlsplit(a), urlsplit(b)
    return (pa.scheme, pa.hostname, pa.port) == (pb.scheme, pb.hostname, pb.port)


def generate_image(prompt: str, size: Optional[str] = None,
                   timeout=None) -> Optional[Tuple[bytes, str]]:
    """وصف → (بايتات صورة، نوعها) أو None (fail-closed، بلا طرف ثالث)."""
    import config

    if not config.MEDIA_ENABLED:
        _set("disabled")
        return None
    base = str(config.MEDIA_BASE_URL).rstrip("/")
    if not is_self_hosted(base):
        _set("host_not_self_hosted")
        logger.warning("R-747 [MEDIA]: مضيف الوسائط ليس ذاتي الاستضافة — رفض بلا اتصال")
        return None

    timeout = timeout or config.MEDIA_TIMEOUT_SECONDS
    try:
        import httpx

        headers = {"Content-Type": "application/json"}
        if config.MEDIA_API_KEY:
            headers["Authorization"] = f"Bearer {config.MEDIA_API_KEY}"
        payload = {"prompt": prompt, "size": size or config.MEDIA_IMAGE_SIZE,
                   "n": 1, "response_format": "b64_json"}
        if config.MEDIA_MODEL:
            payload["model"] = config.MEDIA_MODEL
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            resp = client.post(f"{base}/images/generations", json=payload, headers=headers)
            if resp.status_code != 200:
                _set(f"http_{resp.status_code}")
                logger.warning("R-747 [MEDIA]: HTTP %s — لا صورة مختلقة", resp.status_code)
                return None
            items = (resp.json() or {}).get("data") or []
            if not items or not isinstance(items[0], dict):
                _set("no_data")
                return None
            item = items[0]
            if item.get("b64_json"):
                try:
                    data = base64.b64decode(item["b64_json"], validate=True)
                except (ValueError, TypeError):
                    _set("bad_base64")
                    return None
            elif item.get("url"):
                target = urljoin(base + "/", str(item["url"]))
                if not _same_origin(target, base):
                    _set("url_foreign_origin")
                    logger.warning("R-747 [MEDIA]: url الصورة خارج مضيف الخدمة — رفض بلا اتصال")
                    return None
                got = client.get(target, headers=headers)
                if got.status_code != 200:
                    _set(f"url_http_{got.status_code}")
                    return None
                data = got.content
            else:
                _set("no_image_field")
                return None
    except Exception as exc:  # TOLERATED: شبكة/مهلة/JSON — fail-closed بنوع الخطأ فقط
        _set(f"error_{type(exc).__name__}")
        logger.warning("R-747 [MEDIA]: فشل (%s) — لا صورة مختلقة", type(exc).__name__)
        return None

    if len(data) > config.MEDIA_MAX_IMAGE_BYTES:
        _set("too_large")
        return None
    mime = sniff_image(data)
    if mime is None:
        _set("not_an_image")
        return None
    _set("ok")
    return data, mime
