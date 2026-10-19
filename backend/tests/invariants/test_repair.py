# -*- coding: utf-8 -*-
"""
المرحلة ٤ (R-695): مصنف الأخطاء ومقترح الرقع — اختبارات الوحدة.

مواصفة المالك 2026-10-19: (أ) تصنيف حادثة معروفة إلى الفئة الصحيحة،
(ب) رفض اقتراح إصلاح لو لم تكن هناك حادثة مصنفة، (ج) اقتراح لا يُطبق
تلقائيًا. واعتراضات المراجع ج2: شروط الاقتراح صارمة (تصنيف حقيقي ومكوّن
معزول مثبت — لا قاموس يدوي ولا اسم يمرر)، الرقعة صالحة نحويًا بأثر
إصلاحي واضح (تُترجم وتُشغَّل)، وفشل الحفظ ينتشر ولا يختفي.
"""

import json
import sys
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.repair import (  # noqa: E402
    _import_fix_transform,
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


def _make_repo_with_quarantined_component(tmp_path: Path, component: str = "memory"):
    """شجرة اختبار: مستودع بمكوّن معزول في سجل العزل (عبر القارئ القائم)
    ومصدره فيه الاستيراد المعطوب لوحدة موجودة في backend/ — والمكوّن غير
    الوحدة المستهدفة (البرهان غير ذاتي المرجع: ترقيع المكوّن لا يستورد
    المكوّن نفسه)."""
    repo = tmp_path / "repo"
    (repo / "backend" / component).mkdir(parents=True)
    (repo / "backend" / "predictive").mkdir(parents=True)
    source_text = "import json\nimport predictive\n"
    component_src = repo / "backend" / component / "__init__.py"
    component_src.write_text(source_text, encoding="utf-8")
    # الوحدة المستهدفة نظيفة وقابلة للاستيراد — الخلل في مسار الاستيراد
    (repo / "backend" / "predictive" / "__init__.py").write_text(
        "marker = 'predictive-ok'\n", encoding="utf-8")
    data = tmp_path / "data"
    loyalty = data / "loyalty"
    loyalty.mkdir(parents=True)
    (loyalty / "quarantine_log.jsonl").write_text(
        json.dumps({"time": 1.0, "kind": "quarantine", "detail": "خلل",
                    "component": component}) + "\n",
        encoding="utf-8",
    )
    return repo, data, component_src, source_text


def _import_error_incident():
    return incident_from_monitor_line(
        _health_error_line("ModuleNotFoundError: No module named 'predictive'")
    )


def test_healthy_line_is_not_an_incident():
    """السطر السليم ليس حادثة (اعتراض المراجع) — التحويل يستخرج حقول
    الخطأ الفعلية لا كامل JSON كنص."""
    healthy = {
        "ts": 1792380000.0, "target": "http://127.0.0.1:9999",
        "health": {"status": "ok"}, "status": {"state": "healthy"},
    }
    assert incident_from_monitor_line(healthy) is None


def test_incident_extracted_from_error_fields():
    """الحادثة تُستخرج من health.error/status.error بتمثيل داخلي موحد."""
    line = _health_error_line("URLError: connection refused (errno 111)")
    incident = incident_from_monitor_line(line)
    assert incident is not None
    assert incident["error_text"] == "URLError: connection refused (errno 111)"
    assert incident["source"] == "supervisor"
    assert incident["id"]


def test_component_error_reported_by_app_is_incident():
    """خطأ المكوّن الذي يبلغ عنه التطبيق في /status (last_error عبر ملخص
    الحارس) حادثة فعلية — مسار بيانات حقيقي لا نص مصطنع."""
    line = {
        "ts": 1792380000.0, "target": "http://127.0.0.1:9999",
        "health": {"status": "ok"},
        "status": {
            "status": "operational", "components_count": 7,
            "component_error": "ImportError: No module named 'predictive'",
            "timestamp": 1792380000.0,
        },
    }
    incident = incident_from_monitor_line(line)
    assert incident is not None
    assert incident["kind"] == "component_error"
    assert "No module named 'predictive'" in incident["error_text"]


def test_awareness_change_is_integrity_incident():
    """changes_detected حادثة تغيّر سلامة — لا خطأ استيراد أو شبكة."""
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
        assert classification["incident_id"] == incident["id"]
    unknown = incident_from_monitor_line(
        _health_error_line("خطأ غير معروف النمط إطلاقًا")
    )
    assert classify_incident(unknown) is None


def test_proposal_rejected_without_genuine_classification(tmp_path):
    """(ب) رفض الاقتراح: بلا تصنيف، وبالتصنيف غير المرتبط بالحادثة،
    وبالتصنيف المزور (معرف صحيح ومحتوى يدوي)، وبالمكوّن غير المعزول —
    ولا يُكتب أي ملف اقتراح في كل حالات الرفض."""
    repo, data, component_src, source_text = _make_repo_with_quarantined_component(tmp_path)
    incident = _import_error_incident()
    # بلا تصنيف إطلاقًا
    with pytest.raises(ValueError):
        build_proposal(incident, None, "memory", repo, data)
    # تصنيف مرتبط بحادثة أخرى (معرف مختلف)
    other = dict(incident)
    other["id"] = "different-incident-id"
    with pytest.raises(ValueError):
        build_proposal(incident, classify_incident(other), "memory",
                       repo, data)
    # تصنيف مزور: معرف الحادثة الصحيح لكن المحتوى يدوي (اعتراض المراجع ج2)
    forged = {
        "incident_id": incident["id"], "class": "import_error",
        "action": "مزور",
    }
    with pytest.raises(ValueError):
        build_proposal(incident, forged, "memory", repo, data)
    # مكوّن غير معزول (لا سجل عزل يذكره — قارئ العزل القائم هو الحكم)
    with pytest.raises(ValueError):
        build_proposal(incident, classify_incident(incident), "not_quarantined_x",
                       repo, data)
    # لا ملف رقعة كُتب رغم كل المحاولات
    proposals = data / "proposals"
    assert not proposals.exists() or not any(proposals.rglob("*.diff")), (
        "ملف رقعة كُتب رغم الرفض"
    )
    assert component_src.read_text(encoding="utf-8") == source_text


def test_import_fix_transform_applicability_and_validity():
    """قاعدة التحويل المعلنة: جملة استيراد **علوية كاملة** للوحدة الناقصة
    وحدها تُحوَّل (import X → from backend import X، from X import y →
    from backend.X import y) — والناتج صالح نحويًا دائمًا (يُترجم)،
    وخارجها لا انطباق (مراجعة يدوية بلا رقعة شكلية)."""
    source = textwrap.dedent(
        """\
        import json
        import predictive
        from predictive import engine
        from memory import engine as mem


        def run():
            pass
        """
    )
    new_text = _import_fix_transform(source, "predictive")
    assert new_text is not None, "لم تنطبق القاعدة على استيراد موجود"
    # الناتج يُترجم — صلاحية نحوية إلزامية (اعتراض المراجع: لا IndentationError)
    compile(new_text, "<patched>", "exec")
    assert "from backend import predictive" in new_text
    assert "from backend.predictive import engine" in new_text
    # بقية الملف لم تتغير
    assert "import json" in new_text
    assert "from memory import engine as mem" in new_text
    assert "def run():" in new_text
    # لا انطباق على وحدة غير مستوردة أو جملة غير علوية
    assert _import_fix_transform(source, "nonexistent_mod") is None
    indented = "def f():\n    import predictive\n"
    assert _import_fix_transform(indented, "predictive") is None, (
        "جملة غير علوية لا يجب أن تنطبق — الناتج كان سيفسد البنية"
    )


def test_proposal_not_applied_and_patch_is_real(tmp_path):
    """(ج) الاقتراح لا يُطبق تلقائيًا: المصدر المعزول لا يتغير، والرقعة
    ملف .diff فعلي يُحفظ في مخزن مخرجات الحارس ويُشار إليه من السجل،
    وأثرها الإصلاحي يُثبت **بالتنفيذ** على نسخة اختبارية فقط: الأصل يفشل
    بالاستيراد والمرقّع يستورد بنجاح."""
    import difflib
    import subprocess
    import sys as _sys

    repo, data, component_src, source_text = _make_repo_with_quarantined_component(tmp_path)
    incident = _import_error_incident()
    classification = classify_incident(incident)
    proposal = build_proposal(incident, classification, "memory",
                              repo, data)
    assert proposal["status"] == "proposed", f"لم يقترح: {proposal}"
    assert proposal["description"], "وصف الإصلاح غائب"
    diff_file = data / "proposals" / proposal["diff_file"]
    assert diff_file.is_file(), "ملف الرقعة غير موجود فعلًا"
    diff_text = diff_file.read_text(encoding="utf-8")
    assert diff_text.startswith("--- ") and "+++ " in diff_text, (
        "الرقعة ليست unified diff"
    )
    log_text = (data / "proposals" / "proposals_log.jsonl").read_text(
        encoding="utf-8")
    assert proposal["diff_file"] in log_text, "السجل لا يشير إلى ملف الرقعة"
    assert '"applied": false' in log_text, "السجل لا يوثق عدم التطبيق"
    # المصدر المعزول لم يتغير حرفيًا — لا تطبيق تلقائي
    assert component_src.read_text(encoding="utf-8") == source_text, (
        "المصدر المعزول تغير — تطبيق تلقائي ممنوع"
    )
    # استرجاع النص المرقّع من الرقعة (hunk موحد بسيط) — في الاختبار فقط
    new_text = _restore_from_unified_diff(source_text, diff_text)
    # الناتج المرقّع صالح نحويًا + أثره الإصلاحي بالتنفيذ:
    # الأصل يفشل (ImportError) والمرقّع يستورد من مساره الصحيح
    compile(new_text, "<patched>", "exec")
    original_run = subprocess.run(
        [_sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(repo)!r}); exec(open({str(component_src)!r}).read())"],
        capture_output=True, text=True,
    )
    assert original_run.returncode != 0, "الأصل المفروض أنه يفشل بالاستيراد"
    patched = tmp_path / "patched_copy.py"
    patched.write_text(new_text, encoding="utf-8")
    patched_run = subprocess.run(
        [_sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(repo)!r}); exec(open({str(patched)!r}).read())"],
        capture_output=True, text=True,
    )
    assert patched_run.returncode == 0, (
        f"المرقّع فشل — الرقعة لا تصلح: {patched_run.stderr[-300:]}"
    )


def _restore_from_unified_diff(original_text: str, diff_text: str) -> str:
    """استرجاع النص الجديد من رقعة unified diff بسيطة — في الاختبار فقط
    (الإنتاج بلا أي آلية تطبيق)."""
    import re as _re
    lines = diff_text.splitlines()
    hunks = []
    current = None
    for l in lines:
        if l.startswith("@@"):
            current = {"start": int(_re.search(r"@@ -(\d+)", l).group(1)),
                       "added": [], "removed": 0}
            hunks.append(current)
        elif current is not None:
            if l.startswith(("--- ", "+++ ")):
                continue  # رؤوس الملفات
            if l.startswith("+"):
                current["added"].append(l[1:])
            elif l.startswith("-"):
                current["removed"] += 1
            elif l.startswith(" "):
                # سطر سياق: في الجانبين معًا — الجانب القديم يُستبدل أيضًا
                current["added"].append(l[1:])
                current["removed"] += 1
    original = original_text.splitlines()
    # التطبيق من الأخير للأول — مواضع البدايات لا تتزحزح
    for h in reversed(hunks):
        s = h["start"]
        original[s - 1: s - 1 + h["removed"]] = h["added"]
    return "\n".join(original) + "\n"


def test_save_failure_propagates_not_hidden(tmp_path):
    """فشل حفظ الاقتراح ينتشر صراحة — لا يظهر كغياب قاعدة منطبقة ولا
    يُسجل نجاح كاذب (اعتراض المراجع ج3)."""
    repo, data, component_src, source_text = _make_repo_with_quarantined_component(tmp_path)
    incident = _import_error_incident()
    # المخزن للقراءة فقط: الكتابة تفشل (شروط الانطباق كلها متحققة قبله)
    store = data / "proposals"
    store.mkdir(parents=True)
    store.chmod(0o555)
    try:
        result = process_incident(incident, repo, data)
        assert result["status"] == "save_failed", (
            f"فشل الحفظ اختفى: {result}"
        )
        assert "reason" in result, "سبب الفشل غائب"
    finally:
        store.chmod(0o755)
    # ولا نجاح كاذب في السجل
    log = data / "proposals" / "proposals_log.jsonl"
    assert not log.exists() or "applied\": true" not in log.read_text(
        encoding="utf-8")


def test_process_incident_pipeline(tmp_path):
    """خط الحارس كاملًا: حادثة مصنفة + مكوّن معزول منطبق → اقتراح؛
    حادثة بلا مرجع كود → إجراء تشغيلي بلا رقعة (لا اختراع تعديل)."""
    repo, data, *_ = _make_repo_with_quarantined_component(tmp_path)
    incident = _import_error_incident()
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
    assert after_diffs == before_diffs, "رقعة اختُرعت لحادثة بلا مرجع كود"
    # وحدة ناقصة غير موجودة في backend/ → مراجعة يدوية بلا رقعة (ليست
    # خلل مسار بل خلل وجود — إصلاحها ليس قاعدة معلنة)
    ghost = incident_from_monitor_line(
        _health_error_line("ModuleNotFoundError: No module named 'ghost_mod'")
    )
    result3 = process_incident(ghost, repo, data)
    assert result3["status"] == "classified_no_proposal", (
        f"وحدة غير موجودة أنتجت رقعة: {result3}"
    )


def test_default_log_path_defined_and_isolated(tmp_path, monkeypatch):
    """اختبار انحدار لعلة كامنة مكتشفة أثناء R-695: _default_log_path كانت
    مستدعاة من main وغير معرفة (تشغيل الحارس بلا --log ينهار بـNameError —
    من تعديل R-694؛ الاختبارات القائمة تمرر --log دائمًا فلم تنكشف).
    ملاحظة دقة: أُضيف هذا الاختبار بعد الإصلاح — لم يُشهد فشله RED ولا
    يُنسب إليه RED (اعتراض المراجع ج2 على الأدلة)."""
    from backend import supervisor_daemon
    assert hasattr(supervisor_daemon, "_default_log_path"), (
        "_default_log_path غير معرفة — تشغيل الحارس بلا --log ينهار"
    )
    monkeypatch.setenv("SOVEREIGN_DATA_ROOT", str(tmp_path))
    path = supervisor_daemon._default_log_path()
    assert path == tmp_path / "supervisor" / "monitor_log.jsonl", (
        f"مسار السجل الافتراضي لا يحترم جذر البيانات: {path}"
    )
