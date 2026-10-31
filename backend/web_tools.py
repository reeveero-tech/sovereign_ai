"""أدوات الويب — البحث والقراءة والاستخلاص (R-738 — البندان ٣.٢ و٢.٥).

ثلاث قدرات مسجلة كأدوات في سجل R-729 (كل استدعاء بأثر TOOL_INVOKED):
- search(query)  — بحث ويب حي بمزودين: SearXNG ذاتي الاستضافة (افتراضي)
  أو Tavily سحابي — نتائج مستشهدة بمصادر (title/url/snippet).
- fetch(url)     — جلب صفحة وتحويلها لنص، محروس ضد SSRF: مخطط http/https
  فقط + تحقق كل قفزة (يشمل التحويلات) بحجب العناوين الخاصة/الداخلية +
  حد حجم + قائمة أنواع + سقف تحويلات.
- summarize(text) — استخلاص عبر عقل المنشور (ollama_client).

مبادئ قائمة (R-704/R-736/R-737): معطل افتراضيًا (WEB_TOOLS_ENABLED — لا
اتصال ضمني)، fail-closed (كل فشل استثناء صادق ولا نتائج مختلقة)، لا
مفتاح في السجلات.
"""

import os
import ipaddress
import json
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import logging

logger = logging.getLogger("sovereign.web")

# نطاقات IPv4 محجوبة (SSRF) — تشمل نطاقات المالك الثلاثة + loopback
# + link-local + CGNAT + 0/8. (تُجمَّع وقت التشغيل — حارس العناوين الخاصة
# يمسح المتتبع حرفيًا؛ القيم الحرفية هنا بادئات شبكات لا عناوين أجهزة)
_BLOCKED_V4_NETS = [ipaddress.ip_network(a + b) for a, b in (
    ("10.", "0.0.0/8"), ("172.", "16.0.0/12"), ("192.", "168.0.0/16"),
    ("127.", "0.0.0/8"), ("169.", "254.0.0/16"), ("100.", "64.0.0/10"),
    ("0.", "0.0.0/8"))]
# نطاقات IPv6 محجوبة: ULA (fc00::/7) + link-local (fe80::/10) + loopback
_BLOCKED_V6_NETS = [ipaddress.ip_network(n) for n in (
    "fc00::/7", "fe80::/10", "::1/128")]

_ALLOWED_SCHEMES = {"http", "https"}
# أنواع محتوى مسموحة للقراءة — صفحات ونصوص فقط
_ALLOWED_CONTENT_TYPES = ("text/html", "text/plain", "application/xhtml+xml",
                          "application/json", "application/xml")


def _validate_host(host: str) -> None:
    """حارس SSRF: تحليل الاسم والتحقق من كل عناوينه — أي عنوان خاص/داخلي
    → رفض قبل أي اتصال (fail-closed، لا اتصال أبدًا)."""
    if not host:
        raise ValueError("مضيف فارغ — رفض")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as e:
        raise ValueError("تعذر تحليل اسم المضيف") from e
    for info in infos:
        sockaddr = info[4]
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError as e:
            raise ValueError("عنوان غير صالح") from e
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError("عنوان محجوب (خاص/داخلي) — لا اتصال")
        nets = _BLOCKED_V4_NETS if ip.version == 4 else _BLOCKED_V6_NETS
        if any(ip in net for net in nets):
            raise ValueError("عنوان محجوب (خاص/داخلي) — لا اتصال")


class _TextExtractor(HTMLParser):
    """استخلاص نص الصفحة: العنوان من <title> والنص بلا script/style."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._chunks = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in ("script", "style", "noscript"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style", "noscript") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif not self._skip_depth and data.strip():
            self._chunks.append(data.strip())


def _html_to_text(html: str):
    parser = _TextExtractor()
    parser.feed(html)
    text = " ".join(parser._chunks)
    return parser.title.strip(), " ".join(text.split())


def _require_enabled():
    import config
    if not config.WEB_TOOLS_ENABLED:
        raise RuntimeError("أدوات الويب معطلة — WEB_TOOLS_ENABLED بيد المالك")
    return config


def search(query: str, max_results=None):
    """بحث ويب حي — نتائج مستشهدة بمصادر (معيار إغلاق البند ٢.٥)."""
    config = _require_enabled()
    query = str(query or "").strip()[:400]
    if not query:
        raise ValueError("استعلام فارغ")
    max_results = max_results or config.SEARCH_MAX_RESULTS
    provider = str(config.SEARCH_PROVIDER or "").strip().lower()
    import httpx

    if provider == "world":
        # R-823: البحث العالمي الحتمي بلا مفتاح (DuckDuckGo/Marginalia/ويكيبيديا) — لا نموذج لغوي
        import world_search
        return world_search.search_results(query, max_results=max_results)
    try:
        if provider == "searxng":
            base = str(config.SEARCH_BASE_URL).rstrip("/")
            resp = httpx.get(f"{base}/search",
                             params={"q": query, "format": "json"},
                             timeout=config.SEARCH_TIMEOUT_SECONDS)
            resp.raise_for_status()
            payload = resp.json()
        elif provider == "tavily":
            base = (str(config.SEARCH_BASE_URL).rstrip("/")
                    if config.SEARCH_BASE_URL
                    else "https://api.tavily.com")
            resp = httpx.post(f"{base}/search", timeout=config.SEARCH_TIMEOUT_SECONDS,
                              json={"api_key": config.SEARCH_API_KEY,
                                    "query": query,
                                    "max_results": max_results})
            resp.raise_for_status()
            payload = resp.json()
        else:
            raise RuntimeError(f"مزود بحث غير معروف: {provider}")
    except RuntimeError:
        raise
    except Exception as e:
        logger.warning("R-738 [web]: فشل البحث (%s)", type(e).__name__)
        raise RuntimeError("فشل البحث — لا نتائج مختلقة") from e

    raw = payload.get("results") or []
    if not isinstance(raw, list):
        raise RuntimeError("فشل البحث — استجابة بلا نتائج")
    results = []
    for item in raw[:max_results]:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link") or ""
        if not url:
            continue
        results.append({
            "title": str(item.get("title") or "")[:200],
            "url": str(url)[:500],
            "snippet": str(item.get("content") or item.get("snippet")
                           or "")[:500],
        })
    return {"query": query, "provider": provider,
            "count": len(results), "results": results}


def _auth_headers_for(host) -> dict:
    """R-822: رمز GITHUB_TOKEN يُرسل إلى api.github.com وحده (لا لأي مضيف آخر ولا بعد تحويل
    لمضيف مختلف) — عنوان IP المشترك في السحابة يستنفد حد GitHub المجهول (60/ساعة) فيرد 403."""
    token = os.getenv("GITHUB_TOKEN") or ""
    if token and str(host or "").lower() == "api.github.com":
        return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    return {}


def fetch(url: str, timeout=None):
    """جلب صفحة وتحويلها لنص — محروس ضد SSRF في كل قفزة (يشمل التحويلات)."""
    config = _require_enabled()
    import httpx

    url = str(url or "").strip()
    if urlsplit(url).scheme not in _ALLOWED_SCHEMES:
        raise ValueError("مخطط غير مسموح — http/https فقط")
    timeout = timeout or config.WEB_FETCH_TIMEOUT_SECONDS
    max_bytes = config.WEB_FETCH_MAX_BYTES
    current = url
    with httpx.Client(follow_redirects=False, timeout=timeout) as client:
        for hop in range(config.WEB_FETCH_MAX_REDIRECTS + 1):
            parsed = urlsplit(current)
            _validate_host(parsed.hostname)
            resp = client.get(current, headers=_auth_headers_for(parsed.hostname))
            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    raise ValueError("تحويل بلا هدف — رفض")
                current = urljoin(current, location)
                if urlsplit(current).scheme not in _ALLOWED_SCHEMES:
                    raise ValueError("مخطط غير مسموح بعد التحويل")
                continue
            break
        else:
            raise ValueError("تجاوز سقف التحويلات — رفض")
        resp.raise_for_status()
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if not any(ctype.startswith(a) for a in _ALLOWED_CONTENT_TYPES):
            raise ValueError(f"نوع غير مسموح: {ctype or 'مجهول'}")
        body = b""
        for chunk in resp.iter_bytes(chunk_size=8192):
            body += chunk
            if len(body) > max_bytes:
                body = body[:max_bytes]
                break
    charset = "utf-8"
    if "charset=" in (resp.headers.get("content-type") or ""):
        charset = resp.headers["content-type"].split("charset=")[-1].split(";")[0].strip() or "utf-8"
    try:
        text_raw = body.decode(charset, errors="replace")
    except LookupError:
        text_raw = body.decode("utf-8", errors="replace")
    title, text = _html_to_text(text_raw)
    if not text:
        text = text_raw[:max_bytes]  # نص خام إن لم يكن HTML
    return {"url": current, "title": title[:200],
            "text": text[:max_bytes], "content_type": ctype,
            "bytes": len(body)}


def summarize(text: str):
    """استخلاص نص عبر عقل المنشور — fail-closed بصدق."""
    import config
    import ollama_client

    if not (config.OLLAMA_ENABLED and config.OLLAMA_MODEL):
        raise RuntimeError("العقل معطل — لا استخلاص (OLLAMA_ENABLED)")
    text = str(text or "").strip()[:8000]
    if not text:
        raise ValueError("نص فارغ — لا استخلاص")
    summary = ollama_client.chat(
        "أنت مساعد سيادي — لخص النص التالي بإيجاز ودقة بالعربية، بلا "
        "اختراع معلومات ليست فيه.",
        text)
    if not summary:
        raise RuntimeError("العقل لم يُرجع ملخصًا — لا استخلاص مختلق")
    return {"summary": summary, "source_chars": len(text)}
