# -*- coding: utf-8 -*-
"""
المرحلة ٤ (R-695): مصنف الأخطاء ومقترح الرقع — اختبارات الوحدة.

مواصفة المالك 2026-10-19: (أ) تصنيف حادثة معروفة إلى الفئة الصحيحة،
(ب) رفض اقتراح إصلاح لو لم تكن هناك حادثة مصنفة، (ج) اقتراح لا يُطبق
تلقائيًا. واعتراضات المراجع (تخطيط R-695): الصيغة من مدخلات سجل الحارس
القائم (لا اختراع)، الخاصة قبل العامة، السطر السليم ليس حادثة، الرفض
بالتصنيف غير المرتبط، والرقعة تغيير حقيقي لا تعليق — تُفحص على نسخة
اختبارية فقط.
"""

import re
import sys
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.repair import (  # noqa: E402
    _import_guard_transform,
    build_proposal,
    classify_incident,
    incident_from_monitor_line,
    process_incident,
)


def _health_error_line(error: str) -> dict:
    """سطر سجل مراقبة بصيغة R-687 القائمة — حادثة جلب فعلية."""
    return {
        "ts": 1792380000.0, "target": "http://127.0.0.1:9999",
        "health": {"error": error}, "status": {"error": error},
    }


def test_healthy_line_is_not_an_incident():
    """السطر السليم ليس حادثة (اعتراض المراجع) — التحويل يستخرج حقول
    الخطأ الفعلية لا كامل JSON كنص."""
    healthy = {
        "ts": 1792380000.0, "target": "http://127.0.0.1:9999",
        "health": {"status": "ok"}, "status": {"state": "healthy"},
    }
    assert incident_from_monitor_line(healthy) is None


def test_incident_extracted_from_error_fields():
    """الحادثة تُستخرج من health.error/status.error بتمثيل داخلي موحد
    (معرف + مصدر + نص الخطأ الفعلي) — لا النص الكامل."""
    line = _health_error_line("URLError: connection refused (errno 111)")
    incident = incident_from_monitor_line(line)
    assert incident is not None
    assert incident["error_text"] == "URLError: connection refused (errno 111)"
    assert incident["source"] == "supervisor"
    assert incident["id"]  # معرف حادثة موجود


def test_awareness_change_is_integrity_incident():
    """changes_detected حادثة تغيّر سلامة — لا خطأ استيراد أو شبكة
    (اعتراض المراجع)."""
    line = {
        "ts": 1792380000.0, "target": "http://x",
        "health": {"status": "ok"}, "status": {"state": "healthy"},
        "awareness": {"event": "changes_detected", "changes": {
            "added": [], "removed": [], "modified": ["src/app.py"]}},
    }
    incident = incident_from_monitor_line(line)
    assert incident is not None
    assert incident["kind"] == "integrity_change"


def test_classify_known_incidents():
    """(أ) تصنيف حادثات معروفة إلى فئاتها الصحيحة + إجراء مقترح لكل
    فئة، والخاصة قبل العامة (OSError بذكر اتصال = شبكة لا IO)، والمجهولة
    تبقى غير مصنفة."""
    cases = [
        ("ModuleNotFoundError: No module named 'predictive'",
         "import_error"),
        ("ImportError: cannot import name 'engine' from 'memory'",
         "import_error"),
        ("URLError: <urlopen error [Errno 111] Connection refused>",
         "network_error"),
        ("ConnectionError: HTTPConnectionPool timeout of 5s exceeded",
         "network_error"),
        ("OSError [Errno 111] Connection refused by peer — network",
         "network_error"),  # الخاصة قبل العامة: ذكر اتصال داخل OSError
        ("ValueError: Invalid key (Fernet) — decryption failed",
         "encryption_error"),
        ("SyntaxError: invalid syntax (line 42)",
         "syntax_error"),
        ("PermissionError: [Errno 13] Permission denied: /data/x.json",
         "io_error"),
    ]
    for error_text, expected_class in cases:
        incident = incident_from_monitor_line(_health_error_line(error_text))
        classification = classify_incident(incident)
        assert classification is not None, f"لم تُصنف: {error_text}"
        assert classification["class"] == expected_class, (
            f"{error_text} → {classification['class']} ≠ {expected_class}"
        )
        assert classification["action"], "إجراء مقترح غائب"
        assert classification["incident_id"] == incident["id"], (
            "التصنيف غير مرتبط بالحادثة نفسها"
        )
    # المجهولة تبقى غير مصنفة بلا اقتراح
    unknown = incident_from_monitor_line(
        _health_error_line("خطأ غير معروف النمط إطلاقًا")
    )
    assert classify_incident(unknown) is None


def test_proposal_rejected_without_classification(tmp_path):
    """(ب) رفض الاقتراح بلا تصنيف، وبالتصنيف غير المرتبط بالحادثة نفسها —
    ولا يُكتب أي ملف اقتراح."""
    incident = incident_from_monitor_line(
        _health_error_line("ModuleNotFoundError: No module named 'xyz'")
    )
    # بلا تصنيف إطلاقًا
    with pytest.raises(ValueError):
        build_proposal(incident, None, "predictive", tmp_path, tmp_path)
    # تصنيف مرتبط بحادثة أخرى (معرّف مختلف)
    other = dict(incident)
    other["id"] = "different-incident-id"
    classification = classify_incident(other)
    with pytest.raises(ValueError):
        build_proposal(incident, classification, "predictive",
                       tmp_path, tmp_path)
    # لا ملف اقتراح كُتب
    assert not (tmp_path / "proposals").exists() or not any(
        (tmp_path / "proposals").rglob("*.diff")
    ), "ملف رقعة كُتب رغم الرفض"


def test_import_guard_transform_applicability():
    """قاعدة التحويل المعلنة: تنطبق على سطر استيراد الوحدة الناقصة نفسها
    فقط — ولا تنطبق على غيره (مراجعة يدوية بلا رقعة شكلية)."""
    source = textwrap.dedent(
        """\
        import json
        import predictive
        from memory import engine


        def run():
            pass
        """
    )
    new_text = _import_guard_transform(source, "predictive", "import_error")
    assert new_text is not None, "لم تنطبق القاعدة على استيراد موجود"
    assert "try:" in new_text and "except ImportError" in new_text
    assert "import predictive" in new_text  # الاستيراد الأصلي باقٍ داخل الحرس
    assert "R-695" in new_text  # الاقتراح موسوم لمصدر المراجعة
    # الوحدات الأخرى لا تُمس
    assert "import json" in new_text and "from memory import engine" in new_text
    # لا انطباق على وحدة غير مستوردة في المصدر
    assert _import_guard_transform(source, "nonexistent_mod", "import_error") is None


def test_proposal_not_applied_and_patch_is_real(tmp_path):
    """(ج) الاقتراح لا يُطبق تلقائيًا: المصدر المعزول لا يتغير، والرقعة
    ملف .diff فعلي يُحفظ في مخزن مخرجات الحارس ويُشار إليه من السجل،
    وتُفحص الرقعة على نسخة اختبارية فقط (تغيير سلوك حقيقي)."""
    repo = tmp_path / "repo"
    (repo / "backend" / "predictive").mkdir(parents=True)
    source_text = "import predictive\nimport json\n"
    component_src = repo / "backend" / "predictive" / "__init__.py"
    component_src.write_text(source_text, encoding="utf-8")
    incident = incident_from_monitor_line(
        _health_error_line("ModuleNotFoundError: No module named 'predictive'")
    )
    classification = classify_incident(incident)
    proposal = build_proposal(incident, classification, "predictive",
                              repo, tmp_path / "data")
    # الاقتراح مكتوب: وصف + ملف رقعة + سجل
    assert proposal["description"], "وصف الإصلاح غائب"
    diff_file = tmp_path / "data" / "proposals" / proposal["diff_file"]
    assert diff_file.is_file(), "ملف الرقعة غير موجود فعلًا"
    diff_text = diff_file.read_text(encoding="utf-8")
    assert diff_text.startswith("--- "), "الرقعة ليست unified diff"
    assert "+++ " in diff_text, "الرقعة بلا جهة الهدف"
    log = (tmp_path / "data" / "proposals" / "proposals_log.jsonl")
    assert log.is_file(), "سجل الاقتراحات غائب"
    assert proposal["diff_file"] in log.read_text(encoding="utf-8"), (
        "السجل لا يشير إلى ملف الرقعة"
    )
    # المصدر المعزول لم يتغير حرفيًا — لا تطبيق تلقائي
    assert component_src.read_text(encoding="utf-8") == source_text, (
        "المصدر المعزول تغير — تطبيق تلقائي ممنوع"
    )
    # فحص الرقعة على نسخة اختبارية: التغيير حقيقي (استيراد محروس)
    # استرجاع النص الجديد من الرقعة (hunk واحد بسيط بصيغة unified diff)
    new_lines = _apply_unified_diff(source_text, diff_text)
    assert "except ImportError" in new_lines, "الرقعة لا تنتج الحرس المقصود"
    assert "import predictive" in new_lines, "الاستيراد الأصلي ضاع في الرقعة"


def _apply_unified_diff(original_text: str, diff_text: str) -> str:
    """تطبيق الرقعة في الاختبار فقط (الإنتاج ممنوع من التطبيق) — hunk
    واحد بسيط بصيغة unified diff القياسية."""
    lines = diff_text.splitlines()
    # رؤوس unified diff: --- a/... +++ b/... @@ ... @@
    hunk_start = next(i for i, l in enumerate(lines) if l.startswith("@@"))
    header = lines[hunk_start]
    old_count = int(re.search(r"-(\d+),(\d+)", header).group(2))
    removed, added = [], []
    for l in lines[hunk_start + 1:]:
        if l.startswith("-"):
            removed.append(l[1:])
        elif l.startswith("+"):
            added.append(l[1:])
        elif l.startswith(" "):
            removed.append(l[1:]); added.append(l[1:])
    assert len(removed) == old_count, "hunk غير متسق"
    return "\n".join(added) + ("\n" if original_text.endswith("\n") else "")


def test_process_incident_pipeline(tmp_path):
    """خط الحارس كاملًا: حادثة مصنفة + مكوّن معزول منطبق → اقتراح؛
    حادثة بلا مرجع كود → إجراء تشغيلي بلا رقعة (لا اختراع تعديل)."""
    repo = tmp_path / "repo"
    (repo / "backend" / "predictive").mkdir(parents=True)
    (repo / "backend" / "predictive" / "__init__.py").write_text(
        "import predictive\n", encoding="utf-8")
    data = tmp_path / "data"
    # سجل العزل: مصدر المكونات المعزولة الوحيد (حالة منطقية — R-687)
    loyalty = data / "loyalty"
    loyalty.mkdir(parents=True, exist_ok=True)
    (loyalty / "quarantine_log.jsonl").write_text(
        '{"time": 1.0, "kind": "quarantine", "detail": "خلل", '
        '"component": "predictive"}\n',
        encoding="utf-8",
    )
    incident = incident_from_monitor_line(
        _health_error_line("ModuleNotFoundError: No module named 'predictive'")
    )
    result = process_incident(incident, repo, data)
    assert result["status"] == "proposed", f"الخط لم يقترح: {result}"
    assert result["classification"]["class"] == "import_error"
    # حادثة شبكة بلا مرجع كود معزول منطبق → إجراء تشغيلي بلا رقعة جديدة
    proposals_dir = data / "proposals"
    before_diffs = set(proposals_dir.rglob("*.diff")) if proposals_dir.exists() else set()
    net_incident = incident_from_monitor_line(
        _health_error_line("URLError: connection refused (errno 111)")
    )
    result2 = process_incident(net_incident, repo, data)
    assert result2["status"] == "classified_no_proposal", (
        f"حادثة بلا مرجع كود أنتجت رقعة: {result2}"
    )
    assert result2["classification"]["class"] == "network_error"
    after_diffs = set(proposals_dir.rglob("*.diff")) if proposals_dir.exists() else set()
    assert after_diffs == before_diffs, (
        "رقعة اختُرعت لحادثة بلا مرجع كود"
    )


def test_default_log_path_defined_and_isolated(tmp_path, monkeypatch):
    """اختبار انحدار لعلة كامنة مكتشفة أثناء R-695: _default_log_path كانت
    مستدعاة من main وغير معرفة (تشغيل الحارس بلا --log ينهار بـNameError —
    من تعديل R-694؛ الاختبارات القائمة تمرر --log دائمًا فلم تنكشف).
    الدالة موجودة وتحترم SOVEREIGN_DATA_ROOT (عزل الاختبارات)."""
    from backend import supervisor_daemon
    assert hasattr(supervisor_daemon, "_default_log_path"), (
        "_default_log_path غير معرفة — تشغيل الحارس بلا --log ينهار"
    )
    monkeypatch.setenv("SOVEREIGN_DATA_ROOT", str(tmp_path))
    path = supervisor_daemon._default_log_path()
    assert path == tmp_path / "supervisor" / "monitor_log.jsonl", (
        f"مسار السجل الافتراضي لا يحترم جذر البيانات: {path}"
    )
