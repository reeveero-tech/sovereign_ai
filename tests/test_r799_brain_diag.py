"""R-799: دليل حي من أول دورة R-798 على الإنتاج (2026-10-28):
النواة حلّلت «selfmon:goal_stuck:G-6eeb1d19» ووجّهت المهمة SD-25c6ad42 بملف مرجح
backend/self_monitor.py، ثم فشلت خطوة «locate» في المحرك خلال 0.6ث بـ
brain_unavailable_or_invalid_json:locate و/brain/status = HTTPStatusError بلا رمز الحالة.

المثبت:
1. last_outcome يحمل رمز HTTP الحرفي (HTTPStatusError:<code>) — تشخيص لا تخمين.
2. مهمة بملف مرجح صالح من النواة لا تستدعي العقل لإعادة اختيار الملف (نداء أقل
   على عقل بطيء ونقطة فشل أقل)؛ المرساة من معرّفات المهمة الحقيقية في الملف.
"""

import json
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import self_develop as sd  # noqa: E402

ORIGINAL = "import os\n\n\ndef compute_total(a, b):\n    return a - b\n"
GOOD = {"summary": "إصلاح الجمع", "search": "    return a - b\n",
        "replace": "    return a + b\n", "test_name": "test_total",
        "test_code": "import calc\n\ndef test_total():\n    assert calc.compute_total(2, 3) == 5\n"}


def test_http_status_code_recorded_in_last_outcome(monkeypatch):
    import config
    import ollama_client
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "m")
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", "http://brain.invalid:11434")
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama", raising=False)

    def handler(request):
        return httpx.Response(500, json={"error": "model runner has unexpectedly stopped"})

    real = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    assert ollama_client.chat("s", "u") is None
    out = ollama_client.last_outcome()
    assert out["result"] == "error" and out["error"] == "HTTPStatusError:500"


def test_hinted_task_skips_brain_locate(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "calc.py").write_text(ORIGINAL, encoding="utf-8")
    calls = []

    def brain(system, user, schema):
        calls.append(schema)
        if "keywords" in schema.get("properties", {}):
            return None  # كما حدث حيًا: خطوة locate تفشل
        assert "compute_total" in user  # المرساة على الدالة المذكورة لا بداية الملف
        return json.dumps(GOOD)

    eng = sd.SelfDevEngine(repo_root=tmp_path, brain=brain, disk=False)
    t = eng.request("compute_total يطرح بدل الجمع", "السبب: compute_total", source="nucleus",
                    ref="k", now=0.0, files_hint=["backend/calc.py"])
    res = eng.draft(eng._tasks[t["id"]])
    assert res["ok"] is True and res["file"] == "backend/calc.py"
    assert not any("keywords" in s.get("properties", {}) for s in calls)


def test_unhinted_task_still_uses_brain_locate(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "calc.py").write_text(ORIGINAL, encoding="utf-8")
    calls = []

    def brain(system, user, schema):
        calls.append(schema)
        if "keywords" in schema.get("properties", {}):
            return json.dumps({"file": "backend/calc.py", "keywords": ["compute_total"]})
        return json.dumps(GOOD)

    eng = sd.SelfDevEngine(repo_root=tmp_path, brain=brain, disk=False)
    t = eng.request("compute_total خطأ", "", source="owner", ref="o", now=0.0)
    assert eng.draft(eng._tasks[t["id"]])["ok"] is True
    assert "keywords" in calls[0]["properties"]
