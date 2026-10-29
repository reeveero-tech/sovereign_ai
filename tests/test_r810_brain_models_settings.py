"""R-810 (المالك — البندان ٢ و٣): النماذج والمزودون.

الدافع (2026-10-29): «لا يوجد إمكانية تبديل النماذج، اذ أن اولاما فيه عدة نماذج،
لابد أن يكتشف النظام النماذج المتوفره ويضيف امكانية التبديل بينها» و«النظام
يعتمد كليا على اولاما ولا مجال لإضافة مفاتيح اي بي آي لنماذج أخرى سحبيا».

المثبت هنا:
- طبقة إعدادات التشغيل (config.brain_get/brain_set): فوق البيئة، كتابة ذرّية،
  الإلغاء يعيد قيمة النشر.
- اكتشاف حي للنماذج (ollama_client.list_models) على البروتوكولين، مع فشل
  صادق منضبط (معطل/بروتوكول مجهول/اتصال مرفوض).
- تجاوز النموذج لكل طلب (chat(model=…)) يسري فعلاً على الحمولة.
- النقاط الثلاث (اكتشاف/قراءة/تعديل) محمية بمفتاح المالك، ولا سر يخرج أبدًا.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import config
import ollama_client

KEY = "r810-owner-key"


# ---------------- 1. طبقة إعدادات التشغيل ----------------

@pytest.fixture
def runtime_file(tmp_path, monkeypatch):
    f = tmp_path / "brain_runtime.json"
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", f)
    return f


def test_brain_runtime_layer_overrides_env(runtime_file, monkeypatch):
    """الطبقة تعلو البيئة، والإلغاء يعيد قيمة النشر."""
    monkeypatch.setattr(config, "OLLAMA_MODEL", "env-model")
    assert config.brain_get("OLLAMA_MODEL") == "env-model"
    config.brain_set({"OLLAMA_MODEL": "runtime-model"})
    assert config.brain_get("OLLAMA_MODEL") == "runtime-model"
    # الإلغاء (قيمة فارغة) يحذف من الطبقة فتعود قيمة البيئة
    config.brain_set({"OLLAMA_MODEL": None})
    assert config.brain_get("OLLAMA_MODEL") == "env-model"


def test_brain_runtime_file_is_valid_json_and_atomic(runtime_file):
    layer = config.brain_set({"OLLAMA_MODEL": "m1", "OLLAMA_PROTOCOL": "openai",
                              "OLLAMA_API_KEY": "sk-test-810"})
    assert json.loads(runtime_file.read_text(encoding="utf-8")) == layer
    # الحقول المجهولة لا تُكتب أبدًا
    config.brain_set({"HACKED_KEY": "x"})
    assert "HACKED_KEY" not in json.loads(runtime_file.read_text(encoding="utf-8"))


def test_brain_get_tolerates_missing_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", tmp_path / "nonexistent.json")
    assert config.brain_runtime_read() == {}
    assert config.brain_get("OLLAMA_TIMEOUT_SECONDS", 60) == config.OLLAMA_TIMEOUT_SECONDS
    (tmp_path / "corrupt.json").write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", tmp_path / "corrupt.json")
    assert config.brain_runtime_read() == {}  # لا استثناء — البيئة هي الفعالة


# ---------------- 2. اكتشاف النماذج ----------------

def _fake_provider(routes, status=200):
    """خادم يحاكي مزودًا: routes = {path: json_payload}."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.path)
            body = routes.get(self.path)
            if body is None:
                self.send_response(404)
                self.end_headers()
                return
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


@pytest.fixture
def brain_on(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)


def test_list_models_ollama_tags(brain_on, monkeypatch):
    srv, seen = _fake_provider({"/api/tags": {"models": [
        {"name": "qwen2.5:latest", "model": "qwen2.5:latest"},
        {"name": "llama3.2:latest", "model": "llama3.2:latest"},
        {"name": "qwen2.5:latest", "model": "qwen2.5:latest"},  # تكرار يُزال
    ]}})
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    result = ollama_client.list_models()
    assert result["ok"] is True
    assert result["models"] == ["llama3.2:latest", "qwen2.5:latest"]
    assert seen == ["/api/tags"]
    srv.shutdown()


def test_list_models_openai_compatible(brain_on, monkeypatch):
    srv, seen = _fake_provider({"/models": {"data": [
        {"id": "groq-model-a"}, {"id": "groq-model-b"},
    ]}})
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "openai")
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    result = ollama_client.list_models()
    assert result["ok"] is True
    assert result["models"] == ["groq-model-a", "groq-model-b"]
    assert seen == ["/models"]
    srv.shutdown()


def test_list_models_disabled_brain(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    result = ollama_client.list_models()
    assert result["ok"] is False and result["error"] == "disabled" and result["models"] == []


def test_list_models_unknown_protocol_fail_closed(brain_on, monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "mystery")
    result = ollama_client.list_models()
    assert result["ok"] is False and result["error"] == "unknown_protocol"


def test_list_models_runtime_layer_is_respected(brain_on, monkeypatch, tmp_path):
    """الاكتشاف يقرأ من طبقة التشغيل — نفس مصدر حقيقة الاستدعاء (لا انفصام)."""
    srv, _ = _fake_provider({"/api/tags": {"models": [{"name": "runtime-model:1b"}]}})
    f = tmp_path / "brain_runtime.json"
    f.write_text(json.dumps({"OLLAMA_BASE_URL": f"http://127.0.0.1:{srv.server_address[1]}"}), encoding="utf-8")
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", f)
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", "http://127.0.0.1:1")  # البيئة خاطئة عمدًا
    result = ollama_client.list_models()
    assert result["ok"] is True and result["models"] == ["runtime-model:1b"]
    srv.shutdown()


# ---------------- 3. تجاوز النموذج لكل طلب ----------------

def test_chat_model_override_reaches_payload(brain_on, monkeypatch):
    """chat(model=…) يغيّر الحمولة فعلاً — أساس التبديل بين النماذج."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            seen.append(json.loads(self.rfile.read(n)))
            data = json.dumps({"message": {"role": "assistant", "content": "ok"},
                               "done": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    monkeypatch.setattr(config, "OLLAMA_MODEL", "default-model")
    monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 5.0)
    out = ollama_client.chat("sys", "hi", model="override-model")
    assert out is not None
    assert seen[0]["model"] == "override-model"
    out2 = ollama_client.chat("sys", "hi")
    assert seen[1]["model"] == "default-model"
    srv.shutdown()


# ---------------- 4. النقاط البرمجية (مفتاح المالك + لا سر) ----------------

@pytest.fixture
def client(monkeypatch):
    import app as app_mod
    from fastapi.testclient import TestClient
    monkeypatch.setattr(app_mod, "SOVEREIGN_API_KEY", KEY)
    from fastapi.testclient import TestClient
    with TestClient(app_mod.app) as c:
        yield c


def test_brain_endpoints_require_owner_key(client):
    for u in ("/brain/models", "/brain/settings"):
        assert client.get(u).status_code == 401
        assert client.get(u, headers={"X-Sovereign-Key": "wrong"}).status_code == 401
    assert client.put("/brain/settings", json={}).status_code == 401


def test_brain_settings_get_masks_api_key(client, monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_API_KEY", "sk-live-secret-810")
    r = client.get("/brain/settings", headers={"X-Sovereign-Key": KEY})
    assert r.status_code == 200
    body = r.json()
    assert body["api_key_set"] is True
    assert "sk-live-secret-810" not in r.text  # لا سر في المخرجات أبدًا


def test_brain_settings_put_writes_runtime_layer(client, monkeypatch, tmp_path):
    f = tmp_path / "brain_runtime.json"
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", f)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "deploy-model")
    r = client.put("/brain/settings", headers={"X-Sovereign-Key": KEY},
                   json={"model": "switched-model", "protocol": "ollama"})
    assert r.status_code == 200, r.text
    assert config.brain_get("OLLAMA_MODEL") == "switched-model"
    # لا مفتاح API في الرد أبدًا
    r2 = client.put("/brain/settings", headers={"X-Sovereign-Key": KEY},
                   json={"api_key": "sk-cloud-810"})
    assert r2.status_code == 200
    assert "sk-cloud-810" not in r2.text
    assert config.brain_get("OLLAMA_API_KEY") == "sk-cloud-810"  # ساري داخليًا


def test_brain_settings_put_validation(client, monkeypatch, tmp_path):
    f = tmp_path / "brain_runtime.json"
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", f)
    h = {"X-Sovereign-Key": KEY}
    # بروتوكول مجهول مرفوض — لا تمرير قيمة تعطّل العقل الحي
    assert client.put("/brain/settings", headers=h, json={"protocol": "carrier-pigeon"}).status_code == 422
    # عنوان غير http(s) مرفوض
    assert client.put("/brain/settings", headers=h, json={"base_url": "ftp://x"}).status_code == 422
    assert client.put("/brain/settings", headers=h, json={"base_url": "ليس-عنوانًا"}).status_code == 422
    # حقل غير معروف مرفوض (لا تمرير حر)
    assert client.put("/brain/settings", headers=h, json={"evil_field": 1}).status_code == 422
    # num_ctx غير عددي مرفوض
    assert client.put("/brain/settings", headers=h, json={"num_ctx": "كثير"}).status_code == 422
    # لا شيء كُتب بعد الفشل — الطبقة نظيفة
    assert config.brain_runtime_read() == {}
