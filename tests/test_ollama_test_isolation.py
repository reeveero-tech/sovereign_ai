"""R-720 — عزل عقل Ollama عن الاختبارات (بأمر المالك: «اريد ان يكون للمشروع عقل»).

المشكلة المكتشفة: تفعيل العقل عبر `backend/.env` (خادم صديق المالك على شبكته
المحلية) يجعل أي اختبار يمر في `build_reply` يستدعي النموذج الحقيقي — بطيء،
شبكي، ويكسر اختبارات الردود المنظمة (النص الحر من LLM لا يطابق عقود
الأدلة). مبدأ R-704 نصّ: «لا اتصال ضمني في الاختبارات».

الحل: `tests/conftest.py` يفرض `OLLAMA_ENABLED=false` عبر متغير البيئة قبل أي
استيراد لـconfig (المتغير البيئي يعلو على `.env` بحكم `_ollama_env` نفسها) —
فالتطبيق الحقيقي يقرأ `.env` ويعمل عقله، والاختبارات معزولة بالبناء لا
بالصدفة. هذا الحارس يثبت العزل من طرفين:

1. متغير البيئة مفروض في جلسة الاختبار (يمس القاعدة في conftest نفسها).
2. config داخل جلسة الاختبار يرى العقل معطلًا حتى لو ملف `.env` يفعّله
   (المسار الحقيقي لا الاستعارة: ملف `.env` حقيقي موجود على جهاز المالك).
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"


def test_conftest_forces_ollama_disabled_in_test_session():
    """قاعدة العزل مفروضة: متغير البيئة OLLAMA_ENABLED=false في جلسة
    الاختبار (البيئة تعلو على .env في `_ollama_env` — R-704)."""
    val = os.environ.get("OLLAMA_ENABLED")
    assert val == "false", (
        f"conftest يجب أن يفرض OLLAMA_ENABLED=false في الاختبارات؛ وُجد: {val!r}. "
        "بدون هذا، أي تفعيل عبر backend/.env يجعل الاختبارات تستدعي النموذج الحقيقي."
    )


def test_config_in_test_session_sees_brain_disabled():
    """config المستورد في جلسة الاختبار يرى العقل معطلًا — حتى مع وجود ملف
    `.env` يفعّله (مسار المالك الحقيقي). حارس انحدار: إزالة سطر conftest
    تفشل هذا الاختبار."""
    sys.path.insert(0, str(BACKEND_DIR))
    import config
    assert config.OLLAMA_ENABLED is False, (
        "config داخل الاختبارات يجب أن يرى OLLAMA_ENABLED=False "
        "(عزل conftest) — العقل يعمل في التشغيل الفعلي فقط."
    )


def test_ollama_client_is_best_effort_on_unreachable(monkeypatch, tmp_path):
    """خادم بعيد/غير موجود → سقوط آمن للمحرك القالبي (لا استثناء يكسر الرد) —
    أفضل جهد لا fail-closed. R-721 (تصويبي): محاكاة فشل الاتصال بلا شبكة
    حقيقية (حقن ConnectError في httpx.Client — المراجع: لا اتصال ضمني في
    الاختبارات حتى للفشل)."""
    import httpx
    sys.path.insert(0, str(BACKEND_DIR))
    monkeypatch.setattr("config.OLLAMA_ENABLED", True)
    monkeypatch.setattr("config.OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setattr("config.OLLAMA_BASE_URL", "http://ollama-unreachable.invalid")
    monkeypatch.setattr("config.OLLAMA_TIMEOUT_SECONDS", 0.2)

    class _FailingClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k):
            raise httpx.ConnectError("simulated unreachable (no real network)")

    monkeypatch.setattr(httpx, "Client", _FailingClient)
    import ollama_client
    reply = ollama_client.chat("أنت مساعد", "مرحبا")
    # عقد السقوط الموثق (R-704): لا استثناء أبدًا — None تعني «استخدم القوالب»
    # في build_reply (المتكامل لا الأساس)، أو نص الرد إن نجح.
    assert reply is None or isinstance(reply, str)
