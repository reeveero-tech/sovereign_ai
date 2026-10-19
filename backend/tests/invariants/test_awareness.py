# -*- coding: utf-8 -*-
"""
طبقة الوعي (R-694 — المرحلة ٣): خريطة المشروع وكشف العبث — اختبارات الوحدة.

مواصفة المالك: (أ) خريطة تُولَّد بدقة، (ب) تعديل ملف يُكتشف. واعتراضات
المراجع في التخطيط: RED سلوكي لكل اختبار (لا فشل استيراد)، البصمة الكلية
بقيمة متوقعة مستقلة يحسبها الاختبار نفسه (لا مجرد تكرار — التنفيذ الذي
يعيد ثابتًا يُكشف)، لا خريطة ناقصة عند تعذر القراءة، والمرجعية التالفة
ليست «أول تشغيل» صامتًا.
"""

import hashlib
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.awareness import (  # noqa: E402
    build_project_map,
    diff_maps,
    load_map,
    overall_fingerprint,
    save_map,
)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_tree(root: Path) -> None:
    """شجرة معروفة: 3 ملفات مصدر/إعداد + ملف بيانات (غير مستبعد — سياسة
    المراجع: لا استثناء «data» كاملة) + مستبعدات تشغيلية (pycache/.git)."""
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")
    (root / "src" / "config.json").write_text('{"a": 1}\n', encoding="utf-8")
    (root / "README.md").write_text("# t\n", encoding="utf-8")
    (root / "data").mkdir()
    (root / "data" / "runtime.log").write_text("log\n", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "x.pyc").write_bytes(b"\x00\x01")
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")


def test_project_map_generated_accurately(tmp_path):
    """(أ) الخريطة تُولَّد بدقة: تطابق الحسابات المستقلة حرفيًا،
    والمستبعدات التشغيلية مستبعدة، وملفات البيانات داخل النطاق."""
    _make_tree(tmp_path)
    expected = {
        "README.md": _sha_bytes(b"# t\n"),
        "data/runtime.log": _sha_bytes(b"log\n"),
        "src/app.py": _sha_bytes(b"print('x')\n"),
        "src/config.json": _sha_bytes(b'{"a": 1}\n'),
    }
    got = build_project_map(tmp_path)
    assert got == expected, f"الخريطة غير دقيقة:\n{got}\n≠\n{expected}"
    # الدقة تعني أيضًا: لا pycache ولا .git (استثناءات تشغيلية موثقة)
    assert not any(
        "__pycache__" in k or k.startswith(".git") for k in got
    ), "مستبعدات تشغيلية تسربت إلى الخريطة"


def test_overall_fingerprint_matches_independent_expected_value(tmp_path):
    """البصمة الكلية بقيمة متوقعة مستقلة (الصيغة القانونية الموثقة:
    SHA256 لسطور «المسار:الهاش» مفروزة بالمسار) — وتغيير المحتوى يغيرها."""
    _make_tree(tmp_path)
    got_map = build_project_map(tmp_path)
    # حساب مستقل داخل الاختبار — لا استدعاء لدالة التنفيذ
    canonical = "\n".join(
        f"{k}:{v}" for k, v in sorted(got_map.items())
    )
    expected_fp = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    fp = overall_fingerprint(got_map)
    assert fp == expected_fp, "البصمة الكلية لا تطابق الصيغة القانونية"
    # تغيير المحتوى يغير البصمة — التنفيذ الذي يعيد ثابتًا يُكشف هنا
    (tmp_path / "README.md").write_text("# tampered\n", encoding="utf-8")
    fp2 = overall_fingerprint(build_project_map(tmp_path))
    assert fp2 != fp, "تغيير محتوى ملف لم يغير البصمة الكلية"


def test_file_modification_detected(tmp_path):
    """(ب) تعديل ملف يُكتشف — والإضافة والحذف أيضًا (فروق مفروزة)."""
    _make_tree(tmp_path)
    first = build_project_map(tmp_path)
    (tmp_path / "src" / "app.py").write_text("print('tampered')\n", encoding="utf-8")
    (tmp_path / "src" / "new_file.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "README.md").unlink()
    second = build_project_map(tmp_path)
    diff = diff_maps(first, second)
    assert diff == {
        "added": ["src/new_file.py"],
        "removed": ["README.md"],
        "modified": ["src/app.py"],
    }, f"الفروق غير صحيحة: {diff}"


def test_saved_baseline_roundtrip_and_corrupt_not_silent(tmp_path):
    """المرجعية تُحفظ وتُحمّل كما هي — والتالفة تستثني ولا تُستبدل صامتة."""
    _make_tree(tmp_path)
    first = build_project_map(tmp_path)
    store = tmp_path / "map_store" / "project_map.json"
    store.parent.mkdir(parents=True)
    save_map(first, store)
    assert load_map(store) == first, "المرجعية لم تعد كما حُفظت"
    # مرجعية تالفة: الاستثناء هو السلوك الصحيح (المتصل يسجل الخطأ — لا بديل صامت)
    store.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_map(store)


def test_unreadable_file_fails_map_not_partial(tmp_path):
    """تعذر قراءة ملف داخل النطاق = استثناء — لا خريطة ناقصة ناجحة."""
    _make_tree(tmp_path)
    target = tmp_path / "src" / "app.py"
    target.chmod(0o000)
    try:
        with pytest.raises(OSError):
            build_project_map(tmp_path)
    finally:
        target.chmod(0o644)
