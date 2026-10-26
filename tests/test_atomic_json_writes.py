"""R-781 (ROADMAP_V6 ٦.١.٨) — كتابة JSON ذرية موحدة بدل `with open(p, 'w'): json.dump(...)`.

الخلل: `open(p, 'w')` يقتطع الملف أولًا ثم يكتب تدريجيًا. أي فشل في المنتصف — قيمة غير قابلة
للتسلسل، أو قتل العملية (OOM حدث مرتين على الإنتاج: R-770 و2026-10-26T02:48Z) — يترك ملفًا نصف
مكتوب. مثال حي: `SafetyGuard._save_approval_cache` يبتلع الخطأ، ثم `_load_approval_cache` يعيد `{}`
بصمت ⇒ ضياع كل الموافقات السابقة.
"""
import ast
import json
import os
import stat
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

# سقف تنازلي (ratchet): عدد مواضع `json.dump(` الباقية في backend/ (خارج الاختبارات).
# يجوز أن ينقص فقط؛ كل موضع باقٍ مُراجع في forensics/R-781_json_dump_sites.txt.
MAX_REMAINING_JSON_DUMP = 5


def _json_dump_calls():
    sites = []
    for py in BACKEND.rglob("*.py"):
        if "tests" in py.relative_to(BACKEND).parts:
            continue
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "dump" and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "json"):
                sites.append(f"{py.relative_to(BACKEND).as_posix()}:{node.lineno}")
    return sites


def test_json_dump_sites_only_decrease():
    sites = _json_dump_calls()
    assert len(sites) <= MAX_REMAINING_JSON_DUMP, f"{len(sites)} > {MAX_REMAINING_JSON_DUMP}: {sites}"


def test_no_truncate_then_dump_pattern():
    """الشكل الخطِر بعينه: `with open(X, 'w'...) as f:` جسمه `json.dump(obj, f)` وحده."""
    bad = []
    for py in BACKEND.rglob("*.py"):
        if "tests" in py.relative_to(BACKEND).parts:
            continue
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.With) or len(node.items) != 1 or len(node.body) != 1:
                continue
            ce = node.items[0].context_expr
            if not (isinstance(ce, ast.Call) and isinstance(ce.func, ast.Name) and ce.func.id == "open"):
                continue
            mode = ce.args[1] if len(ce.args) > 1 else next(
                (k.value for k in ce.keywords if k.arg == "mode"), None)
            if not (isinstance(mode, ast.Constant) and mode.value == "w"):
                continue
            b = node.body[0]
            if (isinstance(b, ast.Expr) and isinstance(b.value, ast.Call)
                    and isinstance(b.value.func, ast.Attribute) and b.value.func.attr == "dump"):
                bad.append(f"{py.relative_to(BACKEND).as_posix()}:{node.lineno}")
    assert not bad, f"اقتطاع ثم json.dump (غير ذري): {bad}"


def test_failed_save_keeps_previous_approvals(tmp_path):
    from backend.safety import SafetyGuard
    g = SafetyGuard.__new__(SafetyGuard)
    g.approval_cache_file = tmp_path / "approval_cache.json"
    g.approval_cache = {"approved::a": {"ok": True}}
    g._save_approval_cache()
    g.approval_cache = {"approved::a": {"ok": True}, "approved::b": {"bad": object()}}
    g._save_approval_cache()  # يفشل التسلسل ويُبتلع الخطأ عمدًا
    assert g._load_approval_cache() == {"approved::a": {"ok": True}}


def test_helper_is_atomic_and_preserves_mode(tmp_path):
    from runtime.atomic_json import atomic_write_json
    p = tmp_path / "s.json"
    atomic_write_json(p, {"a": 1}, ensure_ascii=False, indent=2)
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": 1}
    os.chmod(p, 0o640)
    with pytest.raises(TypeError):
        atomic_write_json(p, {"a": object()})
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": 1}
    assert [x.name for x in tmp_path.iterdir()] == ["s.json"]  # لا ملفات مؤقتة يتيمة
    atomic_write_json(p, {"a": 2})
    assert stat.S_IMODE(p.stat().st_mode) == 0o640
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": 2}


def test_secrets_vault_save_fsyncs_before_replace(tmp_path, monkeypatch):
    """الخزينة كانت تكتب المؤقت ثم os.replace بلا fsync — انقطاع الطاقة قد يترك خزينة فارغة."""
    from backend.sovereign import secrets_vault as sv
    order = []
    real_fsync, real_replace = os.fsync, os.replace
    monkeypatch.setattr(sv.os, "fsync", lambda fd: (order.append("fsync"), real_fsync(fd))[1])
    monkeypatch.setattr(sv.os, "replace", lambda a, b: (order.append("replace"), real_replace(a, b))[1])
    v = sv.SecretsVault.__new__(sv.SecretsVault)
    v.path = tmp_path / "vault.json"
    v._save({"format": 1, "secrets": {}})
    assert order[:2] == ["fsync", "replace"], order
    assert stat.S_IMODE(v.path.stat().st_mode) == 0o600
