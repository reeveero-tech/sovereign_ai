"""R-726 (البند ١.٦): نقطة /brain/status — شفافية مصدر الرد (عقل أم قوالب)
+ عنصر واجهة حي يعرضها مع /health و/disk/status (البند ١.٤ — الربط الحي).
لا سر في المخرجات أبدًا (نمط /api-key و/disk/status).
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


def test_brain_status_endpoint_disabled(monkeypatch):
    """العقل معطل (الافتراضي بلا إعداد) → 200 مع enabled=False — النظام
    يعلن صراحة أن ردوده قوالب، لا ينتحل ذكاءً."""
    monkeypatch.delenv("OLLAMA_ENABLED", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        r = client.get("/brain/status")
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] is False
        assert data["reply_source"] == "templates"


def test_brain_status_endpoint_enabled_no_secret_leak(monkeypatch):
    """العقل مفعّل → يعرض النموذج والمصدر بلا أي سر (لا مفتاح ولا عنوان
    كامل بسر) — شفافية كاملة للمالك."""
    monkeypatch.setattr("config.OLLAMA_ENABLED", True)
    monkeypatch.setattr("config.OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setattr("config.OLLAMA_BASE_URL", "http://ollama-server:11434")
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        r = client.get("/brain/status")
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] is True
        assert data["model"] == "qwen2.5:7b"
        assert data["reply_source"] == "ollama"
        assert "OLLAMA_API_KEY" not in r.text


def test_live_status_module_binds_real_endpoints():
    """البند ١.٤ (الربط الحي): وحدة الواجهة الجديدة تستهلك نقاط API فعلية
    (health/disk/brain) — لا نصوص مزروعة — ومحمّلة من index.html."""
    mod = REPO_ROOT / "frontend/js/modules/live-system-status.js"
    assert mod.exists(), "وحدة الحالة الحية مفقودة"
    c = mod.read_text(encoding="utf-8")
    # R-735: /health أُزيلت من هذه اللوحة — الصحة لقسم المراقبة والرأس (عزل الأقسام)
    for ep in ("/disk/status", "/brain/status"):
        assert ep in c, f"الوحدة يجب أن تستهلك {ep} فعليًا (ربط حي لا وهم)"
    idx = (REPO_ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert "live-system-status.js" in idx, "الوحدة غير محملة من index.html"
