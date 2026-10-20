# R-706 — التصميم المعماري: القلب واللسان (توثيق ما نُفِّذ + تصميم المطلوب)

**التاريخ:** 2026-10-20 — بتعليمات المالك («التصميم مطلوب الآن في التزام منفصل»).
**الوثيقة الأساسية:** `docs/OLLAMA_INTEGRATION_DESIGN.md` (المنفَّذ/المصمَّم/المخاطر/جداول الاختبارات).
**حوكمة هذه الجولة:** التزام توثيقي فقط — لا كود سلوكي، لا تغيير أوضاع، لا تنفيذ tongue/.
هذا التقرير يحمل أدلة التحقق التي طلبها المالك. العناوين الخاصة معتَّمة هنا؛
النسخ الكاملة غير المعتمة في مرفق خارج git (شاركها الوكيل مع المالك مباشرة).

---

## ١) git show d7cf4a9 --stat (التزام R-704)

```
commit d7cf4a9ee7bbdf47615d156b52b759f637621431
Author: reeveero-tech <noreply@perplexity.ai>
Date:   Tue Oct 20 06:40:26 2026 +0000

    R-704: عقل Ollama المحلي — دمج LLM في مسار رد السيادي (بطلب المالك)
    
    بطلب المالك المباشر: ربط خادم Ollama الخاص به كعقل للمشروع بديلًا عن APIs الخارجية.
    القيمة المزودة عنوان خادم لا مفتاح — عولجت كإعداد تشغيل في .env المستثنى من git.
    
    - الإعدادات (config.py قسم ٦): OLLAMA_ENABLED معطل افتراضيًا (لا اتصال ضمني)،
      OLLAMA_BASE_URL (افتراضي 127.0.0.1:11434)، OLLAMA_MODEL صريح لا افتراضي،
      OLLAMA_API_KEY اختياري، OLLAMA_TIMEOUT_SECONDS؛ قراءة بيئة→.env عبر
      OLLAMA_ENV_FILE المعزول اختباريًا دون مساس بقواعد مفتاح السيد.
    - العميل (ollama_client.py جديد): البروتوكول الرسمي POST /api/chat بـstream:false —
      لا يرفع أبدًا (أي فشل → None)؛ السجلات بلا مفتاح ولا محتوى محادثة.
    - الدمج: build_reply يستخدم نص النموذج عند التفعيل مع سقوط آمن للقوالب القائمة
```

## ٢) ملفات backend/tongue/* وtests/test_ollama_integration.py — غير موجودة (إثبات الغياب)

فحص الشجرة المتتبعة الكاملة:

```
$ git ls-files | rg "tongue|test_ollama_integration"
(فارغ — لا وجود لهما)

$ git ls-files | rg "ollama"
backend/ollama_client.py
tests/test_ollama_brain.py
tests/test_ollama_config.py
```

**إفصاح صريح:** طلب التحقق ذكر «ملفات backend/tongue/* كاملة» و«tests/test_ollama_integration.py كاملة» —
هذين **غير موجودين**: أمر المالك نصّ على التزام توثيقي («لا شيء آخر»)، وتنفيذهما الآن بلا إذن صريح
يكرر التجاوز الذي اعترض عليه المالك. التصميم الكامل لهما في `docs/OLLAMA_INTEGRATION_DESIGN.md`
(§٣ و§٤ و§٨) وجداول اختباراتهما RED→GREEN جاهزة للتنفيذ بإذن. الملفات الموجودة فعلًا مرفقة
كاملة أدناه بأسمائها الصحيحة.

## ٣) الملفات الموجودة فعلًا — كاملة

### backend/ollama_client.py

```
"""عميل Ollama — عقل السيادي المحلي (R-704، بطلب المالك 2026-10-20).

استدعاء خادم Ollama المحلي (البروتوكول الرسمي: POST /api/chat مع
stream:false — الاستجابة {message:{content}}) لتوليد ردود /chat بدل
القوالب. لا استدعاء لأي خدمة خارجية — عقل LLM محلي بالكامل.

مبادئ التصميم:
- لا يرفع أبدًا: أي فشل (شبكة/مهلة/HTTP/فساد استجابة) يعيد None
  والمستدعي يسقط للمحرك القالبي القائم — التطبيق لا يتعطل بغياب العقل.
- لا يُسجل المفتاح ولا محتوى المحادثة في السجلات — فقط نوع الخطأ.
- المعطيات تُقرأ من config ديناميكيًا (على مستوى الاستدعاء) — قابلة
  للرقعة في الاختبارات دون إعادة استيراد.
"""

import logging

logger = logging.getLogger("sovereign.ollama")


def chat(system_prompt: str, user_message: str, timeout=None):
    """توليد رد عبر خادم Ollama — يعيد نص النموذج أو None عند أي فشل.

    لا يُستدعى فعليًا إلا إذا كان العقل مفعّلًا (OLLAMA_ENABLED + نموذج)
    — تحقق المستدعي أو هذا الشرط هنا: كلاهما رخيص.
    """
    import config

    if not (config.OLLAMA_ENABLED and config.OLLAMA_MODEL):
        return None

    timeout = timeout or config.OLLAMA_TIMEOUT_SECONDS
    try:
        import httpx

        headers = {"Content-Type": "application/json"}
        if config.OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {config.OLLAMA_API_KEY}"

        payload = {
            "model": config.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        url = f"{str(config.OLLAMA_BASE_URL).rstrip('/')}/api/chat"
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = (data.get("message") or {}).get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        logger.warning("R-704 [OLLAMA]: رد فارغ/فاسد — سقوط للمحرك القالبي")
        return None
    except Exception as e:
        # لا مفتاح ولا محتوى محادثة في السجلات — نوع الخطأ فقط
        logger.warning(
            "R-704 [OLLAMA]: فشل خادم العقل (%s) — سقوط للمحرك القالبي",
            type(e).__name__,
        )
        return None
```

### tests/test_ollama_brain.py

```
"""R-704: عقل Ollama المحلي — اختبارات العميل والدمج ونقطة /chat الفعلية.

التصميم: خادم HTTP اصطناعي يحاكي بروتوكول Ollama الرسمي
(POST /api/chat — stream:false — الاستجابة {message:{content}})،
لا اعتماد على خادم حقيقي: الحتمية كاملة والفشل محكوم.

المسارات المثبتة:
- العميل: طلب صحيح (النموذج/stream:false/ترويسة الحامل عند وجود مفتاح)،
  نجاح الاستجابة، والسقوط الآمن (None) عند الخطأ أو فساد الاستجابة.
- build_reply: نص النموذج يصل للرد عند التفعيل، والسقوط للقوالب عند العطل.
- نقطة /chat الفعلية: نص النموذج يظهر في استجابة HTTP، والسقوط يبقي ردًا.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import config
from sovereign_response import build_reply


def _make_fake_ollama(content="رد من النموذج الوهمي", status=200, raw_body=None):
    """خادم يحاكي Ollama — يسجل الطلبات ويعيد استجابة محكومة."""
    requests_seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            requests_seen.append({"path": self.path, "headers": dict(self.headers), "body": body})
            if status != 200:
                self.send_response(status)
                self.end_headers()
                return
            payload = raw_body if raw_body is not None else {
                "model": "fake",
                "message": {"role": "assistant", "content": content},
                "done": True,
            }
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, requests_seen


@pytest.fixture
def ollama_enabled(monkeypatch):
    """تفعيل العقل نحو خادم وهمي — يُستدعى بعد إنشائه لمعرفة المنفذ."""
    def _enable(base_url, model="fake-model", api_key=None):
        monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
        monkeypatch.setattr(config, "OLLAMA_MODEL", model)
        monkeypatch.setattr(config, "OLLAMA_BASE_URL", base_url)
        monkeypatch.setattr(config, "OLLAMA_API_KEY", api_key)
        monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 10.0)
    return _enable


def test_client_chat_success(ollama_enabled):
    """العميل يرسل الطلب الصحيح (النموذج، stream:false) ويعيد نص النموذج."""
    import ollama_client
    server, seen = _make_fake_ollama(content="مرحبا يا سيدي")
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        reply = ollama_client.chat("أنت المساعد السيادي", "مرحبا")
        assert reply == "مرحبا يا سيدي", "model content must be returned"
        assert len(seen) == 1
        req = seen[0]
        assert req["path"] == "/api/chat"
        assert req["body"]["model"] == "fake-model"
        assert req["body"]["stream"] is False, "non-streaming request required"
        assert req["body"]["messages"][0]["role"] == "system"
        assert req["body"]["messages"][-1]["content"] == "مرحبا"
        assert "Authorization" not in req["headers"], "no auth header without key"
    finally:
        server.shutdown()


def test_client_sends_bearer_when_key_set(ollama_enabled):
    """ترويسة الحامل تُرسل فقط عند وجود مفتاح API (لخوادم التوثيق)."""
    import ollama_client
    server, seen = _make_fake_ollama()
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}", api_key="secret-key")
        assert ollama_client.chat("sys", "hi") is not None
        auth = seen[0]["headers"].get("Authorization", "")
        assert auth == "Bearer secret-key"
    finally:
        server.shutdown()


def test_client_failure_returns_none(ollama_enabled):
    """أي فشل (خطأ HTTP / استجابة فاسدة / خادم ميت) → None لا استثناء."""
    import ollama_client
    # خطأ HTTP
    server, _ = _make_fake_ollama(status=500)
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        assert ollama_client.chat("sys", "hi") is None, "HTTP error must fall back"
    finally:
        server.shutdown()
    # استجابة فاسدة (بلا message)
    server2, _ = _make_fake_ollama(raw_body={"unexpected": "shape"})
    try:
        ollama_enabled(f"http://127.0.0.1:{server2.server_address[1]}")
        assert ollama_client.chat("sys", "hi") is None, "malformed response must fall back"
    finally:
        server2.shutdown()
    # خادم ميت (منفذ مرفوض فورًا)
    ollama_enabled("http://127.0.0.1:1")
    assert ollama_client.chat("sys", "hi") is None, "dead server must fall back"


def test_build_reply_uses_llm_when_enabled(ollama_enabled):
    """build_reply يعيد نص النموذج عند التفعيل — العقل جزء مسار الرد."""
    server, _ = _make_fake_ollama(content="رد العقل الاصطناعي الحي")
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        reply = build_reply("greet", "مرحبا")
        assert reply == "رد العقل الاصطناعي الحي", "LLM reply must flow through build_reply"
    finally:
        server.shutdown()


def test_build_reply_falls_back_when_ollama_down(ollama_enabled):
    """عطل الخادم → القوالب القائمة كما هي (سقوط آمن مُثبت)."""
    ollama_enabled("http://127.0.0.1:1")  # منفذ ميت — رفض اتصال فوري
    reply = build_reply("greet", "مرحبا")
    assert reply, "fallback reply must be non-empty"
    assert reply.startswith("أهلاً بك"), "rule-engine template must be the fallback"


def test_chat_endpoint_uses_llm(ollama_enabled):
    """نقطة /chat الفعلية: نص النموذج يظهر في استجابة HTTP — دمج كامل."""
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_fake_ollama(content="رد العقل عبر نقطة المحادثة")
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        chat_rate_limiter._requests.clear()  # عزل حد المعدل بين الاختبارات
        with TestClient(fastapi_app) as client:
            r = client.post("/chat", json={"text": "مرحبا"})
            assert r.status_code == 200, r.text
            assert r.json()["reply"] == "رد العقل عبر نقطة المحادثة", (
                "model text must reach the /chat HTTP response"
            )
    finally:
        server.shutdown()


def test_chat_endpoint_falls_back_when_ollama_down(ollama_enabled):
    """نقطة /chat الفعلية: عطل الخادم → رد احتياطي غير فارغ (لا فشل 500)."""
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient

    ollama_enabled("http://127.0.0.1:1")
    chat_rate_limiter._requests.clear()
    with TestClient(fastapi_app) as client:
        r = client.post("/chat", json={"text": "مرحبا"})
        assert r.status_code == 200, r.text
        assert r.json()["reply"], "fallback reply must remain on dead Ollama"
```

### tests/test_ollama_config.py

```
"""اختبارات إعدادات Ollama — OLLAMA_ENABLED/BASE_URL/MODEL/API_KEY/TIMEOUT.

بطلب المالك (2026-10-20، جولة R-704): ربط مستودع السيادي بخادم Ollama
محلي كعقل LLM بديلًا عن APIs الخارجية (OpenAI/DeepSeek/Google).

مبادئ التصميم (مثبتة هنا):
- العقل معطل افتراضيًا (OLLAMA_ENABLED=False) — لا اتصال ضمني في الاختبارات
  ولا افتراض خادم يعمل عند المطور.
- النموذج صريح لا افتراضي (OLLAMA_MODEL=None) — لا يُفترض نموذج غير مثبت.
- القراءة: متغير البيئة أولًا ثم ملف .env (قابل للعزل عبر OLLAMA_ENV_FILE
  للاختبارات) — دون المساس بقواعد مفتاح السيد.
- Ollama المحلي لا يتطلب مفتاح API (يبقى None) — المفتاح لخوادم التوثيق فقط.
"""

import os
import subprocess
import sys


def _run_config(env):
    """عملية مستقلة معزولة — نفس نمط test_config_security.py."""
    command = [
        sys.executable,
        "-c",
        "import config; "
        "print(config.OLLAMA_ENABLED); "
        "print(config.OLLAMA_BASE_URL); "
        "print(config.OLLAMA_MODEL); "
        "print(config.OLLAMA_API_KEY)",
    ]
    return subprocess.run(
        command,
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
    )


def _base_env(tmp_path):
    """بيئة معزولة: لا متغيرات Ollama، لا ملف .env (مسار معدوم)،
    وجذر بيانات مؤقت — لا يُلمس مفتاح التشغيل الحقيقي ولا .env للمطور."""
    env = os.environ.copy()
    for var in ("OLLAMA_BASE_URL", "OLLAMA_API_KEY", "OLLAMA_MODEL", "OLLAMA_ENABLED"):
        env.pop(var, None)
    env["AI_ENVIRONMENT"] = "development"
    # عزل فعلي من .env للمطور: مسار معدوم + جذر بيانات مؤقت
    env["OLLAMA_ENV_FILE"] = str(tmp_path / "nonexistent.env")
    env["SOVEREIGN_DATA_ROOT"] = str(tmp_path / "data")
    return env


def test_ollama_disabled_by_default(tmp_path):
    """العقل معطل افتراضيًا — لا اتصال ضمني عند عدم الضبط الصريح."""
    result = _run_config(_base_env(tmp_path))
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    enabled, _, _, _ = result.stdout.strip().splitlines()
    assert enabled == "False", "OLLAMA_ENABLED must be False by default (explicit opt-in)"


def test_ollama_defaults(tmp_path):
    """بلا ضبط: العنوان الافتراضي 127.0.0.1:11434 والنموذج والمفتاح None."""
    result = _run_config(_base_env(tmp_path))
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    _, base_url, model, api_key = result.stdout.strip().splitlines()
    assert base_url == "http://127.0.0.1:11434", (
        "OLLAMA_BASE_URL must default to the standard local Ollama port"
    )
    assert model == "None", "OLLAMA_MODEL must be explicit (None by default)"
    assert api_key == "None", "OLLAMA_API_KEY must be optional (None by default)"


def test_ollama_base_url_from_env(tmp_path):
    """العنوان يُقرأ من البيئة — خادم على الشبكة المحلية مثالًا (محايد)."""
    env = _base_env(tmp_path)
    env["OLLAMA_BASE_URL"] = "http://127.0.0.1:11499"
    result = _run_config(env)
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    _, base_url, _, _ = result.stdout.strip().splitlines()
    assert base_url == "http://127.0.0.1:11499", (
        "OLLAMA_BASE_URL must be overridable via environment"
    )


def test_ollama_api_key_optional(tmp_path):
    """المفتاح يُقرأ من البيئة إن وُجد — اختياري لأن Ollama المحلي بلا توثيق."""
    env = _base_env(tmp_path)
    env["OLLAMA_API_KEY"] = "test-key-value"
    result = _run_config(env)
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    *_, api_key = result.stdout.strip().splitlines()
    assert api_key == "test-key-value", (
        "OLLAMA_API_KEY must be readable via environment when set"
    )


def test_ollama_reads_env_file(tmp_path):
    """الإعدادات تُقرأ من ملف .env (عبر OLLAMA_ENV_FILE) عند غياب متغير البيئة."""
    env_file = tmp_path / "ollama.env"
    env_file.write_text(
        "OLLAMA_ENABLED=true\n"
        "OLLAMA_BASE_URL=http://127.0.0.1:11498\n"
        "OLLAMA_MODEL=qwen2.5:7b\n",
        encoding="utf-8",
    )
    env = _base_env(tmp_path)
    env["OLLAMA_ENV_FILE"] = str(env_file)
    result = _run_config(env)
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    enabled, base_url, model, _ = result.stdout.strip().splitlines()
    assert enabled == "True", "OLLAMA_ENABLED must load from env file"
    assert base_url == "http://127.0.0.1:11498", "OLLAMA_BASE_URL must load from env file"
    assert model == "qwen2.5:7b", "OLLAMA_MODEL must load from env file"


def test_env_takes_priority_over_env_file(tmp_path):
    """متغير البيئة يعلو على ملف .env عند تعارضهما."""
    env_file = tmp_path / "ollama.env"
    env_file.write_text("OLLAMA_MODEL=from-file\n", encoding="utf-8")
    env = _base_env(tmp_path)
    env["OLLAMA_ENV_FILE"] = str(env_file)
    env["OLLAMA_MODEL"] = "from-env"
    result = _run_config(env)
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    *_, model, _ = result.stdout.strip().splitlines()
    assert model == "from-env", "environment variable must override .env file"
```

## ٤) الفرق على app.py (التزام d7cf4a9)

```
commit d7cf4a9ee7bbdf47615d156b52b759f637621431
Author: reeveero-tech <noreply@perplexity.ai>
Date:   Tue Oct 20 06:40:26 2026 +0000

    R-704: عقل Ollama المحلي — دمج LLM في مسار رد السيادي (بطلب المالك)
    
    بطلب المالك المباشر: ربط خادم Ollama الخاص به كعقل للمشروع بديلًا عن APIs الخارجية.
    القيمة المزودة عنوان خادم لا مفتاح — عولجت كإعداد تشغيل في .env المستثنى من git.
    
    - الإعدادات (config.py قسم ٦): OLLAMA_ENABLED معطل افتراضيًا (لا اتصال ضمني)،
      OLLAMA_BASE_URL (افتراضي 127.0.0.1:11434)، OLLAMA_MODEL صريح لا افتراضي،
      OLLAMA_API_KEY اختياري، OLLAMA_TIMEOUT_SECONDS؛ قراءة بيئة→.env عبر
      OLLAMA_ENV_FILE المعزول اختباريًا دون مساس بقواعد مفتاح السيد.
    - العميل (ollama_client.py جديد): البروتوكول الرسمي POST /api/chat بـstream:false —
      لا يرفع أبدًا (أي فشل → None)؛ السجلات بلا مفتاح ولا محتوى محادثة.
    - الدمج: build_reply يستخدم نص النموذج عند التفعيل مع سقوط آمن للقوالب القائمة
      عند التعطل/التعطيل؛ سياق مسموح فقط (النية + لقطة الحالة الحية) — النموذج يولّد
      نصًا ولا ينفّذ؛ استدعاء /chat عبر asyncio.to_thread فلا حجب لحلقة الأحداث.
    - الاختبارات: 10 جديدة (RED: 13 فشل ضد الحالة الأساسية → GREEN: 13) بخادم وهمي
      بالبروتوكول الرسمي — تشمل نقطة /chat الفعلية (نص النموذج في استجابة HTTP +
      السقوط الاحتياطي 200 عند العطل). الحزمة 740 passed / 1 deselected.
    - خطوات تشغيل خادم المالك في forensics/R-704_OLLAMA_BRAIN.md (وصول خادمه الفعلي
      غير مُثبت من هنا — تحقق تشغيلي عنده). الدفعة (ب-٢) تبقى معلقة على موافقة المالك.
    
    # DELETION-JUSTIFIED: 5 حذوفات فقط — سطر استدعاء build_reply المتزامن (استُبدل بـasyncio.to_thread)، سطر ترويسة قسم في config (أُعيد ترقيمه)، وترويستا وثائق متقادمتان + خلية عدد اختبارات (استُبدلت). التفصيل في forensics/DELETED_LINES_AUDIT.md وforensics/R-704_OLLAMA_BRAIN.md.

diff --git a/backend/app.py b/backend/app.py
index 0852892..cab6418 100644
--- a/backend/app.py
+++ b/backend/app.py
@@ -830,9 +830,12 @@ async def chat(message: ChatMessage, background_tasks: BackgroundTasks):
         intent_name = nexus_perception.get("intent", {}).get("name", "")
         
         # R-614: محرك الردود السيادي — يبني الرد من حالة النظام الحية
+        # R-704: الاستدعاء في خيط عام — توليد عقل Ollama (HTTP) لا يحجب حلقة الأحداث
         try:
             from sovereign_response import build_reply
-            reply = build_reply(intent_name, message.text, result, orchestrator=orchestrator)
+            reply = await asyncio.to_thread(
+                build_reply, intent_name, message.text, result, orchestrator=orchestrator
+            )
         except Exception as e:
             logger.warning(f"sovereign_response failed, falling back: {e}")
             if source == "nexus_intent" and intent_name:
```

## ٥) الفرق على config.py (التزام d7cf4a9 — معتَّم)

الفرق الكامل يحوي مثالًا بعنوان خاص (عولج في R-705) — النسخة المعتمة هنا، والكاملة غير المعتمة تُشارك مع المالك خارج git عند التسليم (لا تُلتزم):

```
commit d7cf4a9ee7bbdf47615d156b52b759f637621431
Author: reeveero-tech <noreply@perplexity.ai>
Date:   Tue Oct 20 06:40:26 2026 +0000

    R-704: عقل Ollama المحلي — دمج LLM في مسار رد السيادي (بطلب المالك)
    
    بطلب المالك المباشر: ربط خادم Ollama الخاص به كعقل للمشروع بديلًا عن APIs الخارجية.
    القيمة المزودة عنوان خادم لا مفتاح — عولجت كإعداد تشغيل في .env المستثنى من git.
    
    - الإعدادات (config.py قسم ٦): OLLAMA_ENABLED معطل افتراضيًا (لا اتصال ضمني)،
      OLLAMA_BASE_URL (افتراضي 127.0.0.1:11434)، OLLAMA_MODEL صريح لا افتراضي،
      OLLAMA_API_KEY اختياري، OLLAMA_TIMEOUT_SECONDS؛ قراءة بيئة→.env عبر
      OLLAMA_ENV_FILE المعزول اختباريًا دون مساس بقواعد مفتاح السيد.
    - العميل (ollama_client.py جديد): البروتوكول الرسمي POST /api/chat بـstream:false —
      لا يرفع أبدًا (أي فشل → None)؛ السجلات بلا مفتاح ولا محتوى محادثة.
    - الدمج: build_reply يستخدم نص النموذج عند التفعيل مع سقوط آمن للقوالب القائمة
      عند التعطل/التعطيل؛ سياق مسموح فقط (النية + لقطة الحالة الحية) — النموذج يولّد
      نصًا ولا ينفّذ؛ استدعاء /chat عبر asyncio.to_thread فلا حجب لحلقة الأحداث.
    - الاختبارات: 10 جديدة (RED: 13 فشل ضد الحالة الأساسية → GREEN: 13) بخادم وهمي
      بالبروتوكول الرسمي — تشمل نقطة /chat الفعلية (نص النموذج في استجابة HTTP +
      السقوط الاحتياطي 200 عند العطل). الحزمة 740 passed / 1 deselected.
    - خطوات تشغيل خادم المالك في forensics/R-704_OLLAMA_BRAIN.md (وصول خادمه الفعلي
      غير مُثبت من هنا — تحقق تشغيلي عنده). الدفعة (ب-٢) تبقى معلقة على موافقة المالك.
    
    # DELETION-JUSTIFIED: 5 حذوفات فقط — سطر استدعاء build_reply المتزامن (استُبدل بـasyncio.to_thread)، سطر ترويسة قسم في config (أُعيد ترقيمه)، وترويستا وثائق متقادمتان + خلية عدد اختبارات (استُبدلت). التفصيل في forensics/DELETED_LINES_AUDIT.md وforensics/R-704_OLLAMA_BRAIN.md.

diff --git a/backend/config.py b/backend/config.py
index c48f21d..f939ab1 100644
--- a/backend/config.py
+++ b/backend/config.py
@@ -236,7 +236,50 @@ if DRIVE_ENABLED and not DRIVE_ENCRYPTION_KEY and DRIVE_ENCRYPTION_ENABLED:
         warnings.warn("⚠️ Drive مفعل ولكن لا يوجد مفتاح تشفير")
 
 # ============================================================
-# 6. إعدادات النواة الذكية (Core Model)
+# 6. إعدادات Ollama (خادم LLM محلي — عقل السيادي R-704)
+# ============================================================
+
+def _ollama_env(name: str, default=None):
+    """قراءة إعداد Ollama: متغير البيئة أولًا ثم ملف .env (القراءة مخصصة
+    لإعدادات Ollama ولا تغيّر قواعد مفتاح السيد). مسار الملف قابل للعزل
+    عبر OLLAMA_ENV_FILE للاختبارات. البيئة تعلو على الملف دائمًا."""
+    val = os.getenv(name)
+    if val is not None:
+        return val
+    env_file = os.getenv("OLLAMA_ENV_FILE") or (BASE_DIR / ".env")
+    try:
+        if os.path.exists(env_file):
+            with open(env_file, "r", encoding="utf-8") as f:
+                for line in f:
+                    if line.startswith(name + "="):
+                        v = line.split("=", 1)[1].strip().strip('"').strip("'")
+                        if v:
+                            return v
+    # TOLERATED: ملف .env غير موجود/غير مقروء — القيمة الافتراضية (نمط R-680)
+    except Exception:
+        pass
+    return default
+
+
+# العقل معطل افتراضيًا — يُفعّل صراحة في إعداد التشغيل (لا اتصال ضمني في الاختبارات)
+OLLAMA_ENABLED = _ollama_env("OLLAMA_ENABLED", "false").lower() == "true"
+
+# عنوان خادم Ollama — المنفذ 11434 هو منفذ Ollama المعياري.
+# مثال لخادم على شبكة محلية (في .env المستثنى من git): OLLAMA_BASE_URL=http://<عنوان-خاص-معتَّم>.5:11434
+OLLAMA_BASE_URL = _ollama_env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
+
+# النموذج صريح لا افتراضي — لا يُفترض نموذج غير مثبت على خادم المالك
+# (مثال: OLLAMA_MODEL=qwen2.5:7b — مناسب للعربية).
+OLLAMA_MODEL = _ollama_env("OLLAMA_MODEL", None)
+
+# مفتاح API اختياري — Ollama المحلي لا يتطلب توثيقًا (يبقى None).
+OLLAMA_API_KEY = _ollama_env("OLLAMA_API_KEY", None)
+
+# مهلة توليد الرد بالثواني — بعدها سقوط آمن للمحرك القالبي
+OLLAMA_TIMEOUT_SECONDS = float(_ollama_env("OLLAMA_TIMEOUT_SECONDS", "60"))
+
+# ============================================================
+# 7. إعدادات النواة الذكية (Core Model)
 # ============================================================
 
 CORE_MODEL_NAME = os.getenv("CORE_MODEL_NAME", "microsoft/Phi-3-mini-4k-instruct")
```

## ٦) rg قبل/بعد التصحيح (معتَّم)

**قبل (R-705 — من مخرجات الحارس RED):** 13 موضعًا في 8 ملفات:
`backend/config.py`، `backend/memory/biological/immune.py` (2)، `backend/memory/defense/fileless.py`،
`backend/memory/defense/polymorphic.py`، `docs/CHANGELOG.md`، `forensics/R-704_OLLAMA_BRAIN.md` (2)،
`tests/test_ollama_config.py` (4) — عناوين معتَّمة: نطاق 192.168.x.x المالك + أمثلة 10.0.0.x + بيانات
defense القديمة (192.168.1.x/10.0.0.x).

**بعد (R-705):**

```
$ git ls-files -z | xargs -0 grep -nE '<النطاقات الثلاثة>'
(فارغ — نظيف)
```

مثبت بحارس دائم: `tests/test_no_private_ips_in_git.py` — GREEN.

## ٧) الحزمة والتحقق

- التزام R-705 (التصحيحي): `5626117` — الحزمة المحلية 741 passed / 1 deselected. **تصويب لاحق (أمانة التوثيق):** تشغيلة CI على `5626117` فشلت — الحارس كان يمسك نفسه (شرح ملفه ذكر نطاقات CIDR كاملة حرفية، وبعد تتبع الملف صار يفحص نفسه) — عُولج في سلسلة R-707/R-708/R-709 (انظر CHANGELOG وforensics/R-705_IP_GUARD_CASCADE.md). أرقام التشغيلات: `5626117` فشل (39385471216)، `485e34e` فشل (39385713542)، `985d7eb` فشل (39386422800)، `d1d4e39` فشل (39385622637). الحالة الختامية الخضراء: `f13c00f` — CI ناجح (39386523944، 741/0/0)، verify.sh --full تطابق ثلاثي (CI=محلي=استنساخ نظيف).
- التزام R-706 (هذا): توثيقي — عدد الاختبارات لا يتغير (741). تشغيلة CI عليه (`d1d4e39`، 39385622637) فشلت لأن ملف الحارس ورث أمثلته الحرفية من `5626117` — لا بسبب نصوص وثائق R-706 (ملفاتها الخمسة خالية من أي مطابقة). أُصلح ملف الحارس في `485e34e` (R-707)، وأول CI أخضر بعد السلسلة `f13c00f` (R-709). **تصويب R-713:** الصياغة السابقة نسبت الفشل لنصوص الوثائق، وادّعت ضمنًا فحصًا للحارس قبل الالتزام بلا دليل.
