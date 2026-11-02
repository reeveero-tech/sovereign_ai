# -*- coding: utf-8 -*-
"""R-836: عدّ ملفات مستودع GitHub في الشجرة كاملة — من محادثة إنتاج أرسلها المالك.

«كم يوجد ملف فيه؟» عن مستودع InvokeAI أُجيب «لا أعرف... قد يتجاوز مئتين» ثم
ادّعى العقل أنه لا يستطيع الوصول للإنترنت أصلًا — بينما الأداة قرأت المستودع
فعلاً. الجذر فقط كان يُعرض؛ الشجرة التامة (8409 ملفًا) معلنة في نداء واحد.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import chat_tools  # noqa: E402


def _mock(monkeypatch, tree_payload, *, meta=None, contents=None):
    """محاكاة نداءات github_context: الشجرة عبر _fetch_tree_json والبقية عبر _fetch_json."""
    meta = meta or {"full_name": "invoke-ai/InvokeAI", "default_branch": "main",
                    "description": "creative engine", "language": "TypeScript",
                    "stargazers_count": 28957, "size": 451534,
                    "created_at": "2022-08-17", "pushed_at": "2026-11-02"}
    contents = contents if contents is not None else [
        {"name": "README.md", "type": "file"}, {"name": "docs", "type": "dir"}]

    def fake_fetch_json(url):
        if url.endswith("/languages"):
            return {"TypeScript": 57, "Python": 42}
        if url.endswith("/contents"):
            return contents
        if "/commits" in url:
            return [{"sha": "abc1234", "commit": {"message": "fix", "author": {"date": "2026-11-02"}}}]
        return meta

    monkeypatch.setattr(chat_tools, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(chat_tools, "_fetch_tree_json",
                        lambda owner, repo, branch: tree_payload)


class TestTreeFileCount:
    """عدد ملفات الشجرة كاملة يظهر مبكرًا في سياق المستودع."""

    def test_production_case_invokeai(self, monkeypatch):
        """حالة الإنتاج: الشجرة الكاملة ⇒ رقم حقيقي لا اعتذار."""
        tree = {"truncated": False, "tree": [
            {"path": "a.ts", "type": "blob"}, {"path": "b.py", "type": "blob"},
            {"path": "c.py", "type": "blob"}, {"path": "src", "type": "tree"},
            {"path": "src/d.tsx", "type": "blob"}]}
        _mock(monkeypatch, tree)
        out = chat_tools.github_context("invoke-ai", "InvokeAI")
        assert "عدد الملفات في كامل الشجرة: 4 ملفًا في 1 مجلد" in out
        assert "أكثر الامتدادات" in out and "py×2" in out

    def test_count_early_before_root_files(self, monkeypatch):
        """العدد يُدرج مبكرًا — سقف السياق (2200) لا يقتطعه في المستودعات الغنية."""
        tree = {"truncated": False, "tree": [{"path": f"f{i}.py", "type": "blob"} for i in range(50)]}
        _mock(monkeypatch, tree)
        out = chat_tools.github_context("invoke-ai", "InvokeAI")
        assert out.index("عدد الملفات في كامل الشجرة") < out.index("الملفات والمجلدات الجذرية")

    def test_truncated_tree_honest_note(self, monkeypatch):
        """شجرة مقطوعة (مستودع ضخم) ⇒ إعلان صادق أن العدد حد أدنى."""
        tree = {"truncated": True, "tree": [{"path": "a.py", "type": "blob"}]}
        _mock(monkeypatch, tree)
        out = chat_tools.github_context("invoke-ai", "InvokeAI")
        assert "الشجرة مقطوعة" in out and "حد أدنى" in out

    def test_tree_failure_honest_and_rest_intact(self, monkeypatch):
        """فشل نداء الشجرة ⇒ إعلان صادق والبقية (وصف/لغات/جذر) كما هي."""
        def boom(owner, repo, branch):
            raise RuntimeError("rate limit")

        _mock(monkeypatch, {"tree": []})
        monkeypatch.setattr(chat_tools, "_fetch_tree_json", boom)
        out = chat_tools.github_context("invoke-ai", "InvokeAI")
        assert "تعذر عدّ الشجرة الكاملة" in out
        assert "الوصف: creative engine" in out and "اللغات: TypeScript 58%" in out


class TestTreeFetchAuth:
    """نداء الشجرة: مصادقة مفتاح المالك إن ضُبط وسقف قراءة الويب لا يلمسه."""

    def test_token_used_when_set(self, monkeypatch):
        """GITHUB_TOKEN يصل رأس المصادقة (حد المعدل الأعلى من عنوان Render المشترك)."""
        captured = {}

        class _FakeResp:
            def read(self):
                return json.dumps({"tree": [], "truncated": False}).encode()
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=0):
            captured["headers"] = dict(req.header_items())
            captured["url"] = req.full_url
            return _FakeResp()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        out = chat_tools._fetch_tree_json("invoke-ai", "InvokeAI", "main")
        assert out == {"tree": [], "truncated": False}
        auth = captured["headers"].get("Authorization", "")
        assert auth == "Bearer ghp_test123", auth
        assert "recursive=1" in captured["url"]
        assert captured["url"].startswith("https://api.github.com/repos/invoke-ai/InvokeAI/git/trees/")

    def test_no_token_no_auth_header(self, monkeypatch):
        """بلا مفتاح ⇒ النداء مجهول كما كان، لا رأس مصادقة فارغ."""
        captured = {}

        class _FakeResp:
            def read(self):
                return b'{"tree": []}'
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=0):
            captured["headers"] = dict(req.header_items())
            return _FakeResp()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        chat_tools._fetch_tree_json("invoke-ai", "InvokeAI", "main")
        assert "Authorization" not in captured["headers"]
