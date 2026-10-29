"""R-814 (المالك — البند ٦): فحص صحة الأدوات المعروضة على المحادثة.

الدافع (2026-10-29): «لا توجد أدوات كفايه في المشروع تحقق غايته».

المثبت هنا:
- كل أداة يعلنها مسار المحادثة للضيف تُستدعى فعلًا عبر سجل الأدوات الموحد
  وتنجح (بمدخلاتها الصحيحة) — لا أداة معلنة وهي ميتة.
- الأداة المعطلة بعلم المالك (قراءة الويب/البحث بلا مزود) لا تُعرض للعقل
  أصلًا — صدق في الإعلان لا وهم قدرة عند النداء.
"""

import pytest

import app  # noqa: F401 — الاستيراد يسجّل الأدوات الحقيقية في السجل الموحد
import chat_agent

#: المدخلات الصحيحة لكل أداة تحتاج مدخلات — الاستدعاء الحقيقي لا الوهمي
TOOL_INPUTS = {
    "experience.recall": {"goal": "فحص صحة الأدوات"},
    "knowledge.recall": {"query": "الذاكرة"},
    "github.repo": {"url": "python/cpython"},
    "defects.scan": {},
    "goals.list": {},
}


def _invoke(name):
    from tool_registry import get_registry
    return get_registry().invoke(name, caller="chat",
                                 inputs=dict(TOOL_INPUTS.get(name) or {}))


@pytest.fixture
def live_app():
    """دورة حياة التطبيق كاملة — أدوات الحالة (health.snapshot) تحتاج المُنسّق."""
    from fastapi.testclient import TestClient
    from app import app as fastapi_app
    with TestClient(fastapi_app) as c:
        yield c


def test_every_advertised_guest_tool_invokes_successfully(live_app):
    """كل أداة معلنة للضيف تعمل فعلًا — استدعاء ناجح بأثر موقّع."""
    failures = []
    advertised = set(chat_agent.allowed_tools(
        __import__("tool_registry").get_registry(), owner=False))
    for name in sorted(advertised):
        out = _invoke(name)
        if not out.get("ok"):
            failures.append((name, str(out.get("error"))[:120]))
    assert not failures, f"أدوات معلنة فاشلة: {failures}"


def test_disabled_web_tools_not_advertised(live_app, monkeypatch):
    """قراءة الويب معطلة بعلم المالك ⇒ أدوات الويب لا تُعرض للعقل أصلًا (ضيفًا ومالكًا)."""
    import config
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", False)
    from tool_registry import get_registry
    guest = chat_agent.allowed_tools(get_registry(), owner=False)
    owner = chat_agent.allowed_tools(get_registry(), owner=True)
    assert "web.fetch" not in guest and "github.repo" not in guest
    assert "web.fetch" not in owner and "github.repo" not in owner


def test_search_tool_hidden_without_provider(live_app):
    """بلا مزود بحث لا تُعرض أداة البحث للعقل — صدق في الإعلان لا وهم قدرة."""
    import chat_tools
    if chat_tools.search_configured():
        pytest.skip("مزود بحث مضبوط في هذه البيئة")
    from tool_registry import get_registry
    names = chat_agent.allowed_tools(get_registry(), owner=False)
    assert "web.search" not in names


def test_owner_tools_superset_of_guest(live_app, monkeypatch):
    """أدوات المالك أوسع من الضيف — والأداة المحظورة (agent.run) مستثناة دائمًا."""
    from tool_registry import get_registry
    monkeypatch.setattr(chat_agent, "search_available", lambda: True)
    monkeypatch.setattr(chat_agent, "web_fetch_available", lambda: True)
    guest = set(chat_agent.allowed_tools(get_registry(), owner=False))
    owner = set(chat_agent.allowed_tools(get_registry(), owner=True))
    assert guest <= owner
    assert "agent.run" not in owner
