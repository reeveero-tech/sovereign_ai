"""R-838.2: رابط حساب GitHub بلا مستودع ⇒ سرد مستودعاته لا 404 ولا استسلام.

الدافع (لوحة مراقبة إنتاج أرسلها المالك 2026-11-02): «قم بتحليل المشروع
واستكشافه واعطني عنه تحليل مفصل https://github.com/perplexityai قم بتحليل كل
مستودعات هذا الرابط» — أداة github.repo فرّغت الرابط بتعبير غير مثبّت إلى
owner="github.com"/repo="perplexityai" فنادت /repos/github.com/perplexityai
فارتطمت بـ 404 واستسلم العقل معتذرًا.

المثبت هنا (لا نداء شبكة — كل واجهة GitHub مُقيسة):
- رابط الحساب (مؤسسة أو مستخدم) عبر الأداة والجسر معًا ⇒ سرد مستودعات صادق.
- الروابط العادية owner/repo وصيغة owner/repo النصية لم تتغير سلوكًا.
- التعبير القديم لا يعود يلتقط "github.com" مالكًا.
- الطلب غير المفهوم يبقى خطأً صريحًا (لا تخليقًا).
"""

import pytest

import app  # noqa: F401 — الاستيراد يسجّل الأدوات الحقيقية في السجل الموحد
import chat_tools

#: طلب الإنتاج حرفيًا — هو نفسه اختبار الانحدار
PROD_UTTERANCE = ("قم بتحليل المشروع واستكشافه واعطني عنه تحليل مفصل "
                  "https://github.com/perplexityai قم بتحليل كل مستودعات هذا الرابط")

_ORG_META = {
    "login": "perplexityai", "type": "Organization", "name": "Perplexity AI",
    "description": "Perplexity AI — an answer engine",
    "public_repos": 2, "followers": 900,
}

_ORG_REPOS = [
    {"full_name": "perplexityai/pplx-api-quickstart", "language": "Python",
     "stargazers_count": 120, "pushed_at": "2026-10-20T00:00:00Z",
     "description": "quickstart"},
    {"full_name": "perplexityai/design-system", "language": "TypeScript",
     "stargazers_count": 80, "pushed_at": "2026-09-01T00:00:00Z",
     "description": "تصميم"},
]


def _fake_org_gh_get(url):
    """واجهة GitHub مُقيسة: ملف مؤسسة + قائمة مستودعاتها."""
    if url.startswith("https://api.github.com/users/perplexityai"):
        return dict(_ORG_META)
    if url.startswith("https://api.github.com/orgs/perplexityai/repos"):
        return [dict(r) for r in _ORG_REPOS]
    raise AssertionError(f"نداء غير متوقع: {url}")


def test_account_url_lists_repos(monkeypatch):
    """طلب الإنتاج الحرفي عبر الأداة: سرد المستودعات لا 404."""
    monkeypatch.setattr(chat_tools, "_gh_get", _fake_org_gh_get)
    out = app._github_repo_tool(url="https://github.com/perplexityai")
    assert "perplexityai" in out
    assert "مؤسسة" in out
    assert "pplx-api-quickstart" in out and "design-system" in out
    assert "★120" in out  # مرتبة بالنجوم


def test_account_url_via_bridge(monkeypatch):
    """مسار /chat (الجسر): الرابط نفسه داخل الجملة ينتج سردًا لا page_context."""
    monkeypatch.setattr(chat_tools, "_gh_get", _fake_org_gh_get)
    g = chat_tools.gather(PROD_UTTERANCE)
    assert "سرد مستودعات GitHub: perplexityai" in g["tools_used"]
    assert "pplx-api-quickstart" in g["context"]


def test_account_url_no_scheme_not_misparsed(monkeypatch):
    """جذر الخطأ: github.com/perplexityai بلا مخطط لم يعد يُفسَّر github.com مالكًا."""
    calls = []

    def spy(url):
        calls.append(url)
        return _fake_org_gh_get(url)

    monkeypatch.setattr(chat_tools, "_gh_get", spy)
    out = app._github_repo_tool(url="github.com/perplexityai")
    assert "pplx-api-quickstart" in out
    assert all("repos/github.com" not in c for c in calls), calls
    assert any("/users/perplexityai" in c for c in calls)


def test_user_account_uses_user_repos(monkeypatch):
    """حساب مستخدم (لا مؤسسة) يُسرد عبر /users/{owner}/repos."""
    def fake(url):
        if url.startswith("https://api.github.com/users/helallao/repos"):
            return [{"full_name": "helallao/perplexity-ai", "language": "Python",
                     "stargazers_count": 3, "pushed_at": "2026-10-01T00:00:00Z",
                     "description": "خادم وكيل"}]
        if url.startswith("https://api.github.com/users/helallao"):
            return {"login": "helallao", "type": "User", "name": "HL",
                    "description": "", "public_repos": 1, "followers": 2}
        raise AssertionError(f"نداء غير متوقع: {url}")

    monkeypatch.setattr(chat_tools, "_gh_get", fake)
    out = app._github_repo_tool(repo="helallao")
    assert "مستخدم" in out and "helallao/perplexity-ai" in out


def test_owner_repo_url_unchanged(monkeypatch):
    """رابط مستودع عادي يمر كما كان إلى github_context — لا انحدار."""
    seen = {}

    def fake_github_context(owner, repo):
        seen["args"] = (owner, repo)
        return "سياق المستودع"

    monkeypatch.setattr(chat_tools, "github_context", fake_github_context)
    assert app._github_repo_tool(url="https://github.com/owner/repo") == "سياق المستودع"
    assert seen["args"] == ("owner", "repo")
    assert app._github_repo_tool(repo="owner/name.git") == "سياق المستودع"
    assert seen["args"] == ("owner", "name")
    # رابط عميق داخل المستودع لا يزال يُفرَّغ إلى المستودع نفسه
    assert app._github_repo_tool(url="https://github.com/owner/repo/issues/1") == "سياق المستودع"
    assert seen["args"] == ("owner", "repo")


def test_bad_input_still_raises(monkeypatch):
    """مدخل بلا معنى يبقى خطأً صريحًا — الصدق لا التخليق."""
    with pytest.raises(ValueError):
        app._github_repo_tool(url="ليس رابطًا ولا اسمًا")
    with pytest.raises(ValueError):
        app._github_repo_tool(url="")


def test_account_context_sorts_and_declares_truncation(monkeypatch):
    """الترتيب بالنجوم وسقف 200 مُعلنان — لا خفاء ولا اختلاق."""
    def fake(url):
        if url.startswith("https://api.github.com/users/big/repos"):
            # دفعتان من 100 ⇒ 200 مستودعًا ⇒ يُعلن الاقتطاع عند السقف
            if "page=2" in url:
                return [{"full_name": f"big/r{i}", "language": None,
                         "stargazers_count": 1, "pushed_at": "2026-01-01",
                         "description": ""} for i in range(100)]
            return [{"full_name": f"big/top{i}", "language": "Rust",
                     "stargazers_count": 10 + i, "pushed_at": "2026-01-02",
                     "description": ""} for i in range(100)]
        if url.startswith("https://api.github.com/users/big"):
            return {"login": "big", "type": "User", "name": "B", "description": "",
                    "public_repos": 350, "followers": 1}
        raise AssertionError(f"نداء غير متوقع: {url}")

    monkeypatch.setattr(chat_tools, "_gh_get", fake)
    out = chat_tools.github_account_context("big", limit=5)
    assert "big/top99" in out          # الأعلى نجومًا أولًا
    assert "(5 من 350" in out
    assert "مقطوعة عند 200" in out     # السقف مُعلن صادقًا
    assert "big/r0" not in out          # خارج الحد المعروض
