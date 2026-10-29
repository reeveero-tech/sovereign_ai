"""R-812 (المالك — البندان ٤ و٥ و٦): سير عمل التفتيش الذاتي المدمج.

الدافع (2026-10-29): «يجب أن يكون الذكاء الاصطناعي مساعد أو مرجع فقط، بينما
المشروع بنفسه يقوم بكل شي» + «لا يوجد وكلاء ذكاء اصطناعي مدمجين يستخدمون
كمراجعين ومنفذين» + «لا توجد أدوات كافيه».

المثبت هنا (الشريحة الوظيفية المحدودة — كما رسمها المراجع):
- المنفّذ = التطبيق حتميًا: يجمع أدوات مسجلة بلا أي ذكاء، والحاكم هو التطبيق.
- المراجع = الذكاء الاصطناعي كمرجع فقط: حكم JSON مسجل، لا تنفيذ بيده.
- إثباتان: سير يكتمل كاملًا مع عقل معطل (المشروع يقوم بكل شيء — البند ٤)،
  وسير يتأثر فيه حكم المراجع (يسجل ويظهر في الحالة) مع عقل حي.
- فشل صادق: رد غير JSON من العقل → لا حكم مختلق أبدًا (المادة ١).
- الأداة مسجلة في السجل الموحد وتظهر في واجهة الوكلاء (البند ٦ — أداة
  لغاية، لا لعدد).
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import mkdtemp

import pytest

import config
import review_workflow
from memory import core as core_mod
from memory.core import SovereignCore
from sovereign.keys import KeyRing


@pytest.fixture
def fresh_core(monkeypatch, tmp_path):
    kr = KeyRing(keys_dir=tmp_path / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-812 test")
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


@pytest.fixture
def register_system_tools(monkeypatch):
    """تسجيل أدوات فحص وهمية بلا أي ذكاء — عزل تام عن النقاط الحية.

    _gather_find يستورد get_registry من وحدة tool_registry داخل الدالة،
    لذا يُرقّع السجل الموحد نفسه (المصدر الوحيد) — لا سجل موازٍ.
    """
    import tool_registry as tr_mod
    from tool_registry import ToolRegistry, ToolSpec

    registry = ToolRegistry()
    for name in review_workflow.EXECUTOR_TOOLS:
        registry.register(ToolSpec(
            name=name, description=f"أداة فحص اختبارية {name}",
            inputs={}, outputs="ok", handler=lambda **kw: {"ok": True, "tool": "stub"}))
    monkeypatch.setattr(tr_mod, "get_registry", lambda: registry)
    monkeypatch.setattr(tr_mod, "_REGISTRY", registry)
    return registry


# ---------------- البند ٤: المشروع يقوم بكل شيء بنفسه ----------------

def test_workflow_completes_with_brain_disabled(fresh_core, register_system_tools, monkeypatch):
    """مع عقل معطل: السير يكتمل كاملًا — المنفّذ التطبيق، ولا مراجع."""
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    out = review_workflow.run_self_review(caller="test")
    assert out["workflow"] == "self_review"
    assert out["executor"] == "application"
    assert out["status"] in ("completed", "completed_with_issues")
    assert out["reviewer_verdict"]["reviewer"] == "skipped_brain_off"
    # الأدلة الحتمية من الأدوات الأربع — لا ذكاء في التنفيذ
    tools = out["executor_findings"]["components"]
    assert tools == list(review_workflow.EXECUTOR_TOOLS)
    # أثر موقّع في السجل
    events = list(fresh_core.iterate_events())
    assert any(e["type"] == "self_review" for e in events)


def test_app_is_the_judge_on_tool_failure(fresh_core, register_system_tools, monkeypatch):
    """التطبيق هو الحاكم: فشل أداة حتمي → completed_with_issues بلا أي ذكاء."""
    from tool_registry import ToolRegistry, ToolSpec

    def boom():
        raise RuntimeError("أداة معطوبة عمدًا")

    import tool_registry as tr_mod
    from tool_registry import ToolRegistry, ToolSpec

    broken = ToolRegistry()
    broken.register(ToolSpec(name="vault.status", description="x", inputs={},
                             outputs="ok", handler=boom))
    for name in review_workflow.EXECUTOR_TOOLS:
        if name != "vault.status":
            broken.register(ToolSpec(name=name, description="x", inputs={},
                                     outputs="ok", handler=lambda **kw: {"ok": True}))
    monkeypatch.setattr(tr_mod, "get_registry", lambda: broken)
    monkeypatch.setattr(tr_mod, "_REGISTRY", broken)
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    out = review_workflow.run_self_review(caller="test")
    assert out["status"] == "completed_with_issues"
    assert "vault.status" in out["executor_findings"]["app_failures"]


# ---------------- البند ٥: المراجع الذكي — مرجع فقط ----------------

def _fake_brain(reply_body):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            data = json.dumps(reply_body).encode()
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


def test_brain_reviewer_verdict_is_recorded(fresh_core, register_system_tools, monkeypatch):
    """مع عقل حي: حكم المراجع يُسجل ويظهر — ولا يُنفّذ شيئًا بنفسه."""
    srv = _fake_brain({"message": {"role": "assistant", "content": json.dumps(
        {"ok": False, "issues": ["القرص قارب الامتلاء"], "summary": "عيوب مرصودة"}, ensure_ascii=False)},
        "done": True})
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "test-model")
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
    monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 5.0)
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    out = review_workflow.run_self_review(caller="test")
    verdict = out["reviewer_verdict"]
    assert verdict["reviewer"] == "brain"
    assert verdict["ok"] is False
    assert "القرص قارب الامتلاء" in verdict["issues"]
    # حكم المراجع السلبي يظهر في الحالة — لكنه لا ينفّذ شيئًا (مرجع فقط)
    assert out["status"] == "completed_with_issues"
    srv.shutdown()


def test_brain_garbage_reply_no_invented_verdict(fresh_core, register_system_tools, monkeypatch):
    """رد غير JSON من العقل → لا حكم مختلق (المادة ١ — فشل صادق)."""
    srv = _fake_brain({"message": {"role": "assistant", "content": "ليس JSON إطلاقاً"},
                       "done": True})
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "test-model")
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
    monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 5.0)
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    out = review_workflow.run_self_review(caller="test")
    assert out["reviewer_verdict"]["reviewer"] == "invalid_review_reply"
    assert out["reviewer_verdict"]["ok"] is None  # لا حكم مختلق
    srv.shutdown()


# ---------------- البند ٦: أداة مسجلة + ظاهرة في الواجهة ----------------

def test_self_review_tool_registered_in_registry():
    """system.self_review في السجل الموحد — مصدر حقيقة واحد للقدرات."""
    import app as app_mod

    app_mod._register_real_tools()
    from tool_registry import get_registry
    names = [t["name"] for t in get_registry().list_tools()]
    assert "system.self_review" in names


def test_self_review_agent_card_in_ui():
    """بطاقة الوكيل المدمج ظاهرة في واجهة الأدوات والوكلاء."""
    ui = (Path(__file__).resolve().parent.parent / "frontend" / "chat" / "index.html").read_text(encoding="utf-8")
    assert "system.self_review" in ui
    assert "الوكيل المدمج: منفّذ + مراجع" in ui
