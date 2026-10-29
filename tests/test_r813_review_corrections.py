# -*- coding: utf-8 -*-
"""R-813 — تصحيحات مراجعة المستشار النهائية (دفعة تصحيحية لأمر العمل).

يغطي العيوب الحاجبة التي أثبتتها مراجعة المستشار على R-812:
١) بقاء النموذج لكل محادثة (النموذج في قلب الرسالة والنقل والتخزين والقائمة)
٢) حفظ جزئي لبراءات العقل بلا محو (brain_set لا يمسح ما لم يُرسل)
٣) فشل الكتابة في ملف براءات العقل يظهر كاستثناء (لا كتم)
٤) مفتاح مزود العقل في الخزنة (لا ينطبع ولا يُسرّب)
٥) أثر حكم المراجع: رفضه ⇒ إعادة فحص واحدة محدودة موقعة في السجل
٦) فحوص واعية لصحة المكونات (ليست مجرد نجاح الاستدعاء)
٧) فشل جمع النتائج يُسجل كحالة — لا ابتلاع
٨) مسار النموذج في الدردشة والواجهة بلا حجب حلقة التنفيذ
"""

import base64
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import config  # noqa: E402
import review_workflow  # noqa: E402
import tool_registry as tr_mod  # noqa: E402
from tool_registry import ToolRegistry, ToolSpec  # noqa: E402


# ---------------- أدوات مساعدة (نمط test_r812) ----------------

@pytest.fixture
def fresh_core(monkeypatch, tmp_path):
    from memory import core as core_mod
    from memory.core import SovereignCore
    from sovereign.keys import KeyRing

    kr = KeyRing(keys_dir=tmp_path / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-813 test")
    kr.save_to_disk()
    sc = tmp_path / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    fc = SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr,
    )
    monkeypatch.setattr(core_mod, "get_core", lambda: fc)
    return fc


def _install_registry(monkeypatch, handler):
    """سجل موحد موقّع بأداة فحص بيد الاختبار — عزل تام عن الأدوات الحية."""
    registry = ToolRegistry()
    for name in review_workflow.EXECUTOR_TOOLS:
        registry.register(ToolSpec(
            name=name, description=f"أداة فحص اختبارية {name}",
            inputs={}, outputs="ok", handler=handler))
    monkeypatch.setattr(tr_mod, "get_registry", lambda: registry)
    monkeypatch.setattr(tr_mod, "_REGISTRY", registry)
    return registry


def _last_self_review_event(core):
    events = [e for e in core.iterate_events() if e.get("type") == "self_review"]
    assert events, "لا حدث self_review في السجل"
    payload = core.get_payload(events[-1])
    assert payload, "لا حمولة للحدث"
    return {"payload": payload}


# ---------------- ١) الحفظ الجزئي لبراءات العقل (عيب ٢) ----------------

def test_brain_set_partial_update_preserves_other_keys(tmp_path, monkeypatch):
    """تحديث حقل واحد لا يمحو بقية الحقول — الحفظ جزئي دائمًا."""
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", tmp_path / "brain.json")
    config.brain_set({"OLLAMA_MODEL": "m-a", "OLLAMA_PROTOCOL": "ollama"})
    # تحديث النموذج فقط — البروتوكول يبقى
    config.brain_set({"OLLAMA_MODEL": "m-b"})
    rt = config.brain_runtime_read()
    assert rt["OLLAMA_MODEL"] == "m-b"
    assert rt["OLLAMA_PROTOCOL"] == "ollama"
    # تحديث السياق فقط — كل ما سبق يبقى
    config.brain_set({"OLLAMA_NUM_CTX": 8192})
    rt = config.brain_runtime_read()
    assert rt["OLLAMA_MODEL"] == "m-b"
    assert rt["OLLAMA_PROTOCOL"] == "ollama"
    assert rt["OLLAMA_NUM_CTX"] == 8192


def test_brain_set_write_failure_propagates(tmp_path, monkeypatch):
    """فشل كتابة ملف براءات العقل يظهر كاستثناء — لا يبتلَع (عيب ٣)."""
    # ملف عادي في مسار المجلد الأب ⇒ فشل كتابة حتمي
    blocker = tmp_path / "brain.json"
    blocker.write_text("not a dir", encoding="utf-8")
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE",
                        blocker / "nested" / "brain.json")
    with pytest.raises(OSError):
        config.brain_set({"OLLAMA_MODEL": "m-x"})


# ---------------- ٢) مفتاح العقل في الخزنة (عيب ٤) ----------------

def _patch_vault(monkeypatch, vault):
    """تركيب خزينة اختبار في مساري الاستيراد الممكنين (لا مؤثر خارجي)."""
    import sovereign.secrets_vault as sv
    monkeypatch.setattr(sv, "get_vault", lambda: vault)
    try:
        import backend.sovereign.secrets_vault as bsv  # مسار الاستيراد المزدوج
        monkeypatch.setattr(bsv, "get_vault", lambda: vault)
    except ImportError:
        pass


def test_brain_api_key_lives_in_vault_never_in_file(tmp_path, monkeypatch):
    """المفتاح في الخزنة المشفرة — لا يظهر في ملف التشغيل أبدًا،
    والقراءة عبر brain_get تمر بالخزنة أولًا، والقيمة الفارغة تحذف صراحةً."""
    from sovereign.secrets_vault import SecretsVault

    key_b64 = base64.b64encode(os.urandom(32)).decode()
    vault = SecretsVault(path=tmp_path / "vault.json", master_key_b64=key_b64,
                          audit=lambda ev, payload: None)
    _patch_vault(monkeypatch, vault)

    cfg_path = tmp_path / "brain.json"
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", cfg_path)
    monkeypatch.setattr(config, "OLLAMA_API_KEY", "plain-key")
    config._BRAIN_API_KEY_CACHE.pop("value", None)

    # وضع المفتاح ⇒ يذهب للخزنة لا للملف
    assert config.brain_api_key_set("vault-key-1", actor="owner") is True
    assert vault.get(config.BRAIN_API_KEY_SECRET,
                     capability=config.BRAIN_API_KEY_SCOPE,
                     actor="owner") == "vault-key-1"
    assert config.brain_get("OLLAMA_API_KEY") == "vault-key-1"  # الخزنة أولًا

    # brain_set لا يكتب المفتاح في الملف أبدًا (مساره الخزينة فقط)
    config.brain_set({"OLLAMA_API_KEY": "should-not-be-written"})
    raw = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else "{}"
    assert "vault-key-1" not in raw
    assert "should-not-be-written" not in raw
    assert config.brain_get("OLLAMA_API_KEY") == "vault-key-1"

    # التدوير
    assert config.brain_api_key_set("vault-key-2", actor="owner") is True
    assert config.brain_get("OLLAMA_API_KEY") == "vault-key-2"

    # القيمة الفارغة تحذف صراحةً — عودة لقيمة البيئة
    assert config.brain_api_key_set("", actor="owner") is False
    assert config.brain_get("OLLAMA_API_KEY") == "plain-key"

    # لا خزينة ⇒ لا تخزين — صادق لا صامت
    _patch_vault(monkeypatch, None)
    with pytest.raises(RuntimeError):
        config.brain_api_key_set("x", actor="owner")
    assert config.brain_api_key_get() is None


# ---------------- ٣) النموذج في قلب الرسالة (عيب ١) ----------------

def test_chat_message_carries_model_and_planner_passes_it():
    """النموذج يقبل في قلب الرسالة، والمخطط يمرره لكل نداء للعقل."""
    import app as app_module
    from chat_agent import ChatPlanner

    msg = app_module.ChatMessage(text="مرحب", model="m-per-conv")
    assert msg.model == "m-per-conv"

    captured = []

    def chat_fn(system, user, **kw):
        captured.append(kw.get("model"))
        return json.dumps({"ok": True, "answer": "أهلًا", "issues": [],
                          "summary": "تم"}, ensure_ascii=False)

    planner = ChatPlanner(chat_fn=chat_fn, model="m-conv-777")
    planner._call("نظام", "مستخدم")
    assert "m-conv-777" in captured


def test_respond_passes_model_to_every_brain_call():
    """مسار الدردشة الكامل يمرر النموذج المختار للمحادثة إلى كل نداء عقل."""
    from chat_agent import respond

    captured = []

    def chat_fn(system, user, **kw):
        captured.append(kw.get("model"))
        # موجّه: لا أداة مطلوبة
        return json.dumps({"tool": "none", "inputs": {}}, ensure_ascii=False)

    registry = _StubRegistry()
    out = respond("ما أخبارك؟", history=[], owner=False, registry=registry,
                  chat_fn=chat_fn, model="m-e2e-9", max_seconds=3)
    assert out, "لا رد"
    assert "m-e2e-9" in captured, "النموذج لم يصل إلى نداءات العقل"


class _StubRegistry:
    def list_tools(self):
        return [{"name": "health.snapshot", "description": "صحة",
                 "inputs": {}}]

    def invoke(self, name, inputs=None, caller=None):
        return {"ok": True, "result": {"ok": True}, "source": "stub"}


def test_workspace_conversation_keeps_model(tmp_path):
    """النموذج يُحفظ مع المحادثة ويُعاد في القائمة، والتحديث بلا
    نموذج لا يمحوه — فتح المحادثة يعيد نموذجها."""
    from workspace.service import Workspace
    from workspace.storage import LocalStorage

    ws = Workspace(LocalStorage(tmp_path / "files"), None, local_root=tmp_path / "idx")
    c = ws.save_conversation(None, "عنوان", [{"role": "user", "content": "مرحبا"}],
                             None, model="m-keep")
    listed = ws.list_conversations()
    assert any(x.get("model") == "m-keep" for x in listed)
    # تحديث بلا نموذج ⇒ النموذج يبقى (لا محو ضمني)
    ws.save_conversation(c["id"], "عنوان",
                         [{"role": "user", "content": "مرحبا"},
                          {"role": "assistant", "content": "أهلًا"}], None)
    assert ws.get_conversation(c["id"])["model"] == "m-keep"


# ---------------- ٤) أثر حكم المراجع: إعادة فحص محدودة موقعة (عيب ٥) ----------------

def _fake_brain(payload):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._json({"models": [{"name": "test-model"}]})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            self._json(payload)

        def _json(self, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _brain_on(monkeypatch, srv):
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "test-model")
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
    monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 5.0)
    monkeypatch.setattr(config, "OLLAMA_BASE_URL",
                        f"http://127.0.0.1:{srv.server_address[1]}")


def test_reviewer_rejection_triggers_bounded_recheck(fresh_core, monkeypatch):
    """رفض المراجع مع فحوص ناجحة كلها ⇒ إعادة فحص واحدة محدودة،
    موقعة في النتيجة والسجل، والحالة «completed_with_issues» —
    لا مجرد تسمية مقلوبة بلا أثر (عيب ٥: تمييز حقيقي)."""
    _install_registry(monkeypatch, lambda **kw: {"ok": True, "tool": "stub"})
    verdict = {"ok": False, "issues": ["شيء مقلق"], "summary": "رفض"}
    srv = _fake_brain({"message": {"role": "assistant",
                                   "content": json.dumps(verdict, ensure_ascii=False)},
                       "done": True})
    _brain_on(monkeypatch, srv)
    out = review_workflow.run_self_review(caller="test")
    # الحكم مسجل كما هو
    assert out["reviewer_verdict"]["ok"] is False
    # الأثر: إعادة فحص موقعة بسببها
    assert out["recheck"]["trigger"] == "reviewer_rejected"
    assert isinstance(out["recheck"]["checks"], list)
    # الحالة تميّز الحالة السلبية (كل الفحوص ناجحة لكن المراجع رفض)
    assert out["status"] == "completed_with_issues"
    # السجل يحمل القضية والأثر
    ev = _last_self_review_event(fresh_core)
    assert ev["payload"]["reviewer_ok"] is False
    assert ev["payload"]["recheck_triggered"] is True
    srv.shutdown()


def test_checks_are_health_aware_not_just_call_success(fresh_core, monkeypatch):
    """أداة تعيد نجاح الاستدعاء مع نتيجة «غير سليمة» ⇒ الفحص يفشل —
    الوعي بصحة المكون، لا بنجاح الاستدعاء (عيب ٦)."""
    _install_registry(monkeypatch, lambda **kw: {
        "ok": True, "status": "unhealthy", "error_count": 3})
    out = review_workflow.run_self_review(caller="test")
    failed = {c["tool"] for c in out["executor_findings"]["checks"] if not c["passed"]}
    assert failed == set(review_workflow.EXECUTOR_TOOLS)
    assert out["status"] == "completed_with_issues"
    ev = _last_self_review_event(fresh_core)
    assert ev["payload"]["status"] == "completed_with_issues"


def test_gather_findings_failure_recorded_not_swallowed(fresh_core, monkeypatch):
    """فشل أداة تنفيذية (استثناء داخلها) ⇒ يُسجل كعيب ويفشل الفحص —
    لا ابتلاع ولا نجاح زائف (عيب ٧)."""
    def _boom(**kw):
        raise ValueError("أداة رفضت التنفيذ")

    _install_registry(monkeypatch, _boom)
    out = review_workflow.run_self_review(caller="test")
    failed = {c["tool"] for c in out["executor_findings"]["checks"] if not c["passed"]}
    assert failed == set(review_workflow.EXECUTOR_TOOLS)
    assert out["status"] == "completed_with_issues"


def test_gather_findings_runtime_error_propagates(fresh_core, monkeypatch):
    """عطل تنفيذي غير متوقع (RuntimeError من السجل) ينتشر — لا يبتلعه
    الجامع (fail-closed: بلا سجل صادق لا تفتيش)."""
    class _BrokenRegistry:
        def list_tools(self):
            return [{"name": n} for n in review_workflow.EXECUTOR_TOOLS]

        def invoke(self, name, inputs=None, caller=None):
            raise RuntimeError("انفجار غير متوقع")

    monkeypatch.setattr(tr_mod, "get_registry", lambda: _BrokenRegistry())
    with pytest.raises(RuntimeError):
        review_workflow.run_self_review(caller="test")


# ---------------- ٥) مسار الواجهة — إصلاحات المحادثة (عيب ١ + العرق) ----------------

def _fn_block(src, name):
    i = src.index("function " + name + "(")
    return src[i:src.index("\n  }", i)]


def test_frontend_conversation_fixes_present():
    """إصلاحات واجهة الدردشة المطلوبة موجودة كمصدر:
    حماية العرق (هوية الجلسة)، الحفظ قبل التبديل، النموذج في الطلب،
    والسقف غير الكارثي (أرشفة لا حذفًا)."""
    src = (REPO_ROOT / "frontend" / "chat" / "index.html").read_text(encoding="utf-8")
    # حماية العرق: persistConv يلتقط هوية الجلسة المستهدفة ويحرسها في الرد
    block = _fn_block(src, "persistConv")
    assert "var targetSession = state.sessionId" in block
    assert "if (state.sessionId !== targetSession) return false;" in block  # قديم = إلغاء لا نجاح
    # نتيجة الحفظ الفعلية تعود للمنادي (تصحيح المراجعة الرابعة): persistConv وعد —
    # فشل الخادم يوقف التبديل ويعاد للمنادي برسالة، والجارية تبقى سليمة
    assert "return persistConv(); // R-809" in _fn_block(src, "keepCurrentConversationBeforeNew")
    assert "return false;" in block and "Promise.resolve(true)" in block
    # الحفظ قبل التبديل في المسارين (محادثة خادم ومحادثة زائر) — وفشل الحفظ
    # يوقف التبديل (تصحيح المراجعة الثالثة): لا تفريغ جارية غير محفوظة
    # (تصحيح المراجعة الرابعة: النتيجة تُنتظر في المسارات الثلاثة)
    assert "var myNav = ++navSeq;" in _fn_block(src, "openLocalConv")  # كل اختيار عملية تنقل — حتى الحالية
    assert "if (state.sessionId === c.id) return;" in _fn_block(src, "openLocalConv")  # الحالية: إلغاء الأقدم دون إعادة تحميل
    assert "if (!(await keepCurrentConversationBeforeNew())) return;" in _fn_block(src, "openConv")
    assert "var myNav = ++navSeq;" in _fn_block(src, "openConv")  # المعرّف قبل انتظار GET
    assert _fn_block(src, "openConv").count("if (myNav !== navSeq) return;") == 2  # بعد GET وبعد الحفظ
    assert "if (!(await keepCurrentConversationBeforeNew())) return;" in \
        src[src.find('newBtn").addEventListener'):]  # زر محادثة جديدة أيضًا
    # النموذج لكل محادثة: يُرسل في الطلب ويُحفظ مع المحادثة ويُستعاد
    assert "if (state.model) body.model = state.model;" in src
    assert "model: state.model || null" in _fn_block(src, "persistConv")
    assert "state.model = c.model || null;" in _fn_block(src, "openLocalConv")
    assert "state.model = c.model || null;" in _fn_block(src, "openConv")
    # السقف غير الكارثي (تصحيح المراجعة الثانية): المخزن يحفظ الجميع كاملة —
    # لا اقتطاط ولا حذف أبدًا؛ وفهرس العرض يعرض أحدث ١٠٠ وقابل للتوسيع
    cap = _fn_block(src, "upsertLocalConv")
    assert ".slice(0, 2)" not in cap, "لا اقتطاط رسائل في التخزين"
    assert "archived: true" not in cap or "ws/files" in cap, "لا وسماً بالأرشفة في مسار الضيف"
    assert "CONV_DISPLAY_CAP = 100" in src
    assert "localConvs.slice(0, showAllLocalConvs ? localConvs.length : CONV_DISPLAY_CAP)" in src
    assert 'localConvs.length > CONV_DISPLAY_CAP' in src  # مؤشر صادق قابل للتوسيع


def test_backend_routes_no_event_loop_blocking_and_model_flow():
    """مسارات براءات العقل لا تحجب حلقة التنفيذ: القِراءات الخالصة متزامنة
    (def — تجري في threadpool تلقائيًا)، والكتابة async مع خروج الأعمال
    الحاجبة عبر asyncio.to_thread. والنموذج يمر في /chat إلى العقل."""
    import inspect

    import app as app_module
    # القراءات: def متزامن — تُنفذ في threadpool بلا حجب الحلقة
    for fn_name in ("brain_models", "brain_settings_get"):
        fn = getattr(app_module, fn_name, None)
        assert fn is not None, fn_name
        assert not inspect.iscoroutinefunction(fn), f"{fn_name} يجب أن يكون متزامنًا (def)"
    # الكتابة: async لكن كل عمل القرص/الخزينة يخرج من الحلقة عبر to_thread
    put = app_module.brain_settings_put
    assert inspect.iscoroutinefunction(put)
    src = inspect.getsource(put)
    assert "asyncio.to_thread(_config.brain_api_key_set" in src
    assert "asyncio.to_thread(_config.brain_set" in src
    # النموذج من الرسالة يصل فعليًا إلى نداء العقل في /chat
    chat_src = inspect.getsource(app_module.chat)
    assert "model=message.model" in chat_src


# ---------------- ٦) تصحيح المراجعة الثانية: عقد أصرم + ترحيل النسخ القديمة ----------------

def test_reviewer_contract_rejects_wrong_field_types(fresh_core, monkeypatch):
    """المراجع: أي حقل ناقص أو من نوع خاطئ (issues ليست قائمة، summary ليست
    نصًا) ⇒ invalid_review_reply — لا حكم مختلق ولا قيم مبتلعة."""
    _install_registry(monkeypatch, lambda **kw: {"ok": True, "tool": "stub"})
    cases = [
        {"ok": True, "issues": "ليست قائمة", "summary": "س"},      # issues نص
        {"ok": True, "issues": [], "summary": 42},                  # summary رقم
        {"ok": True, "issues": []},                                 # summary ناقص
        {"ok": True, "summary": "س"},                               # issues ناقص
        {"issues": [], "summary": "س"},                             # ok ناقص
        {"ok": "yes", "issues": [], "summary": "س"},               # ok غير منطقي
        {"ok": True, "issues": [42, {}], "summary": "س"},           # عناصر غير نصية
    ]
    for verdict in cases:
        srv = _fake_brain({"message": {"role": "assistant",
                                       "content": json.dumps(verdict, ensure_ascii=False)},
                           "done": True})
        _brain_on(monkeypatch, srv)
        out = review_workflow.run_self_review(caller="test")
        assert out["reviewer_verdict"]["reviewer"] == "invalid_review_reply", verdict
        assert out["reviewer_verdict"]["ok"] is None
        assert out["reviewer_verdict"]["issues"] == []
        srv.shutdown()


def test_reviewer_contract_rejects_padded_and_non_object_replies(fresh_core, monkeypatch):
    """الرد يُحلَّل كاملًا كما ورد: نص قبل/بعد الكائن ⇒ رفض، ومصفوفة بدل
    كائن ⇒ رفض — لا استخراج نمطي ولا تسامح."""
    _install_registry(monkeypatch, lambda **kw: {"ok": True, "tool": "stub"})
    padded = ("مقدمة غير مطلوبة " + json.dumps({"ok": True, "issues": [],
                                                 "summary": "س"}, ensure_ascii=False)
              + " خاتمة غير مطلوبة")
    for reply in (padded,
                  json.dumps([{"ok": True, "issues": [], "summary": "س"}]),  # مصفوفة
                  "ليس JSON إطلاقًا"):
        srv = _fake_brain({"message": {"role": "assistant", "content": reply},
                           "done": True})
        _brain_on(monkeypatch, srv)
        out = review_workflow.run_self_review(caller="test")
        assert out["reviewer_verdict"]["reviewer"] == "invalid_review_reply", reply[:40]
        assert out["reviewer_verdict"]["ok"] is None
        srv.shutdown()


def test_reviewer_contract_accepts_full_valid_object(fresh_core, monkeypatch):
    """المراجع: الكائن الكامل الصحيح يُقبل كاملًا — issues وsummary كما وردا."""
    _install_registry(monkeypatch, lambda **kw: {"ok": True, "tool": "stub"})
    verdict = {"ok": True, "issues": ["ملاحظة صغيرة"], "summary": "سليم عمومًا"}
    srv = _fake_brain({"message": {"role": "assistant",
                                   "content": json.dumps(verdict, ensure_ascii=False)},
                       "done": True})
    _brain_on(monkeypatch, srv)
    out = review_workflow.run_self_review(caller="test")
    v = out["reviewer_verdict"]
    assert v["reviewer"] == "brain" and v["ok"] is True
    assert v["issues"] == ["ملاحظة صغيرة"]
    assert v["summary"] == "سليم عمومًا"
    srv.shutdown()


def test_legacy_file_api_key_migrates_to_vault(tmp_path, monkeypatch):
    """النسخة القديمة (R-810): مفتاح نص صريح في ملف التشغيل ⇒ يُرحّل إلى
    الخزينة المشفرة وتُحذف نسخته الصريحة من الملف — والقراءة تخدمه فورًا."""
    from sovereign.secrets_vault import SecretsVault

    key_b64 = base64.b64encode(os.urandom(32)).decode()
    vault = SecretsVault(path=tmp_path / "vault.json", master_key_b64=key_b64,
                         audit=lambda ev, payload: None)
    _patch_vault(monkeypatch, vault)

    cfg = tmp_path / "brain.json"
    cfg.write_text(json.dumps({"OLLAMA_MODEL": "m-old",
                              "OLLAMA_API_KEY": "legacy-plain-key"}, ensure_ascii=False),
                   encoding="utf-8")
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", cfg)
    config._BRAIN_API_KEY_CACHE.pop("value", None)

    # القراءة نفسها تُرحّل: الخزينة تخدم القيمة، والملف يفقد النسخة الصريحة
    assert config.brain_get("OLLAMA_API_KEY") == "legacy-plain-key"
    assert vault.get(config.BRAIN_API_KEY_SECRET,
                     capability=config.BRAIN_API_KEY_SCOPE,
                     actor="migration") == "legacy-plain-key"
    assert "legacy-plain-key" not in cfg.read_text(encoding="utf-8")
    # بقية الحقول تبقى — الترحيل لا يمس شيئًا غير المفتاح
    rt = config.brain_runtime_read()
    assert rt.get("OLLAMA_MODEL") == "m-old"
    assert "OLLAMA_API_KEY" not in rt
    # الكتابات اللاحقة لا تعيد النسخة الصريحة أبدًا
    config.brain_set({"OLLAMA_NUM_CTX": 4096})
    assert "legacy-plain-key" not in cfg.read_text(encoding="utf-8")
    assert config.brain_get("OLLAMA_API_KEY") == "legacy-plain-key"


def test_legacy_file_api_key_never_replaces_newer_vault_value(tmp_path, monkeypatch):
    """الخزينة تحمل مفتاحًا أحدث والملف نسخة قديمة مختلفة ⇒ الترحيل لا يستبدل
    قيمة الخزينة (الأحدث)، ويكتفي بتنظيف النسخة الصريحة من الملف."""
    from sovereign.secrets_vault import SecretsVault

    key_b64 = base64.b64encode(os.urandom(32)).decode()
    vault = SecretsVault(path=tmp_path / "vault.json", master_key_b64=key_b64,
                         audit=lambda ev, payload: None)
    _patch_vault(monkeypatch, vault)
    cfg = tmp_path / "brain.json"
    cfg.write_text(json.dumps({"OLLAMA_API_KEY": "legacy-old"}, ensure_ascii=False),
                   encoding="utf-8")
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", cfg)
    config._BRAIN_API_KEY_CACHE.pop("value", None)

    # المالك حدّث المفتاح أولًا (الخزينة تحمل الأحدث)
    config.brain_api_key_set("vault-new", actor="owner")

    # قراءة تُطلق الترحيل: القيمة الأحدث تبقى، والنسخة القديمة تُنظف من الملف
    assert config.brain_get("OLLAMA_API_KEY") == "vault-new"
    assert config.brain_get("OLLAMA_API_KEY") == "vault-new"  # قراءة ثانية — لا رجوع
    assert "legacy-old" not in cfg.read_text(encoding="utf-8")
    assert vault.get(config.BRAIN_API_KEY_SECRET,
                     capability=config.BRAIN_API_KEY_SCOPE,
                     actor="owner") == "vault-new"


def test_legacy_file_api_key_cleanup_failure_does_not_replay_store(tmp_path, monkeypatch):
    """فشل تنظيف الملف لا يجعل الترحيل يستبدل مفتاحًا حدّثه المالك لاحقًا:
    المالك يحدّث المفتاح، ثم قراءة تالية مع فشل تنظيف مستمر — قيمة المالك
    الجديدة تبقى (لا يعاد تخزين القديمة)."""
    from sovereign.secrets_vault import SecretsVault

    key_b64 = base64.b64encode(os.urandom(32)).decode()
    vault = SecretsVault(path=tmp_path / "vault.json", master_key_b64=key_b64,
                         audit=lambda ev, payload: None)
    _patch_vault(monkeypatch, vault)
    cfg = tmp_path / "brain.json"
    cfg.write_text(json.dumps({"OLLAMA_API_KEY": "legacy-old"}, ensure_ascii=False),
                   encoding="utf-8")
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", cfg)
    config._BRAIN_API_KEY_CACHE.pop("value", None)

    # فشل التنظيف حتمي (محاكاة عطل القرص/الصلاحية)
    def _boom(*a, **kw):
        raise OSError("قرص محمي")
    monkeypatch.setattr(config, "atomic_write_json", _boom)  # مرجع config المستورد
    # قراءة: التخزين يحدث (الخزينة فارغة) لكن التنظيف يفشل — لا فقد
    assert config.brain_get("OLLAMA_API_KEY") == "legacy-old"
    assert vault.get(config.BRAIN_API_KEY_SECRET,
                     capability=config.BRAIN_API_KEY_SCOPE,
                     actor="migration") == "legacy-old"

    # المالك يحدّث المفتاح الآن
    config.brain_api_key_set("owner-new", actor="owner")
    # قراءة تالية والتنظيف ما زال فاشلًا: لا يعاد تخزين legacy-old
    assert config.brain_get("OLLAMA_API_KEY") == "owner-new"
    assert vault.get(config.BRAIN_API_KEY_SECRET,
                     capability=config.BRAIN_API_KEY_SCOPE,
                     actor="owner") == "owner-new"


def test_legacy_file_api_key_survives_without_vault(tmp_path, monkeypatch):
    """لا خزينة ⇒ لا فقد: النسخة الصريحة تبقى في الملف وتُقرأ منها حتى
    تتاح الخزينة (الترحيل مؤجل لا مُلغى) — bلا حذف بلا بديل."""
    cfg = tmp_path / "brain.json"
    cfg.write_text(json.dumps({"OLLAMA_API_KEY": "legacy-plain-key"},
                              ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(config, "BRAIN_RUNTIME_FILE", cfg)
    monkeypatch.setattr(config, "OLLAMA_API_KEY", "")
    config._BRAIN_API_KEY_CACHE.pop("value", None)
    _patch_vault(monkeypatch, None)

    assert config.brain_get("OLLAMA_API_KEY") == "legacy-plain-key"
    assert "legacy-plain-key" in cfg.read_text(encoding="utf-8")  # لم يُفقد
