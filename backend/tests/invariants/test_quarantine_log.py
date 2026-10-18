# -*- coding: utf-8 -*-
"""
حارس سجل العزل الدائم — المرحلة ٢ من META_SYSTEM (R-687)

أمر المالك 2026-10-18 (المرحلة ٢): «آلية التوجيه: مدخل يقرأ من سجل العزل
(الذي أنشأته في المرحلة ١)». الفحص الفعلي للمرحلة ١ (هذه الجولة) أثبت أن
انتهاكات LoyaltyContract كانت في الذاكرة فقط — لا سجل دائم. هذا الملف
يختبر طبقة السجل الدائم (backend/loyalty_log.py) وعقد الولاء وهو يكتب
إليها: إلحاق append-only، قراءة، آلة حالات المكوّنات (عزل ← رفع بتفويض)،
وعزل الكتابة عن الفشل (لا استثناء يرفع أبدًا من مسار التسجيل).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"


def _fresh_root(monkeypatch) -> Path:
    """جذر بيانات معزول لكل اختبار — لا تلوث بين الاختبارات ولا للجذر الحقيقي."""
    root = Path(tempfile.mkdtemp(prefix="quarantine_log_test_"))
    monkeypatch.setenv("SOVEREIGN_DATA_ROOT", str(root))
    return root


def _run_contract_scenario(body: str, data_root: Path):
    """سيناريو عقد الولاء في عملية منفصلة معزولة البيئة (نمط R-686
    test_mr_defused._run_scenario) — العقد singleton فالعزل بالعملية الفرعية
    شرط صحة، والسكربت يُفحص بـcompile قبل التشغيل (RED نزيه)."""
    indented = "\n".join("    " + line for line in body.strip().splitlines())
    script = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(_REPO_ROOT)!r})\n"
        f"sys.path.insert(0, {str(_BACKEND_DIR)!r})\n"
        "import Mr\n"
        "_R = {}\n"
        "try:\n" + indented + "\n"
        "except Exception as e:\n"
        "    _R['unexpected_error'] = f'{type(e).__name__}: {e}'\n"
        "print('SCENARIO_JSON:' + json.dumps(_R))\n"
    )
    compile(script, "<scenario>", "exec")
    env = dict(os.environ)
    env["SOVEREIGN_DATA_ROOT"] = str(data_root)
    result = subprocess.run(
        [sys.executable, "-u", "-c", script],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), timeout=60, env=env,
    )
    payload = None
    for line in result.stdout.splitlines():
        if line.startswith("SCENARIO_JSON:"):
            payload = json.loads(line[len("SCENARIO_JSON:"):])
    return result.returncode, payload, result.stderr


# ---------- 1) وحدة السجل: الواجهة والدورة والآلة ----------

def test_loyalty_log_module_exists_with_api():
    """backend/loyalty_log.py موجود بواجهته المعلنة (RED: غياب الوحدة)."""
    from backend.loyalty_log import (  # noqa: F401
        append_entry,
        quarantine_log_path,
        quarantined_components,
        read_entries,
    )


def test_append_read_roundtrip(monkeypatch):
    """إلحاق ← قراءة: نفس الأسطر بنفس القيم (kind/detail/component/time)."""
    from backend.loyalty_log import append_entry, read_entries

    _fresh_root(monkeypatch)
    append_entry("quarantine", "خلل تنبؤي", component="predictive")
    append_entry("release", "رفع بتفويض السيد", component="predictive")
    append_entry("double_bind", "محاولة ربط مزدوج")
    entries = read_entries()
    assert [e["kind"] for e in entries] == [
        "quarantine", "release", "double_bind",
    ], f"الأسطر المقروءة لا تطابق الملحق: {entries}"
    assert entries[0]["component"] == "predictive"
    assert entries[1]["component"] == "predictive"
    assert "component" not in entries[2] or entries[2]["component"] is None
    for e in entries:
        assert isinstance(e["time"], (int, float)), f"وقت غير رقمي: {e}"


def test_quarantined_components_state_machine(monkeypatch):
    """عزل ← رفع: المكوّن المعزول محسوب، المرفوع غير محسوب، وغير المكوّن
    (انتهاكات العقد العامة) لا تعزل أي مكوّن."""
    from backend.loyalty_log import append_entry, quarantined_components

    _fresh_root(monkeypatch)
    assert quarantined_components() == set(), "بلا سجل: لا مكوّنات معزولة"
    append_entry("quarantine", "س1", component="predictive")
    append_entry("quarantine", "س2", component="memory")
    assert quarantined_components() == {"predictive", "memory"}
    append_entry("release", "رفع بتفويض", component="predictive")
    assert quarantined_components() == {"memory"}, "الرفع يجب أن يزيل المكوّن"
    # انتهاكات بلا مكوّن (عقد عام) لا تعزل مكونات
    append_entry("quarantine", "عزل العقد كله")
    assert quarantined_components() == {"memory"}, (
        "عزل بلا مكوّن لا يجب أن يعزل أي مكوّن في التوجيه"
    )


def test_append_only_never_truncates(monkeypatch):
    """السجل append-only: الحجم ينمو فقط وأول سطر لا يتغير بعده."""
    from backend.loyalty_log import append_entry, quarantine_log_path, read_entries

    root = _fresh_root(monkeypatch)
    append_entry("quarantine", "أول سجل", component="quantum")
    first_line = quarantine_log_path().read_text(encoding="utf-8").splitlines()[0]
    size1 = quarantine_log_path().stat().st_size
    for i in range(3):
        append_entry("double_bind", f"سجل لاحق {i}")
    size2 = quarantine_log_path().stat().st_size
    assert size2 > size1, "السجل يجب أن ينمو فقط (append-only)"
    assert quarantine_log_path().read_text(
        encoding="utf-8"
    ).splitlines()[0] == first_line, "أول سطر تغير — السجل ليس append-only"
    assert len(read_entries()) == 4


def test_write_failure_never_raises(monkeypatch):
    """فشل الكتابة (مسار غير قابل للكتابة) لا يرفع استثناءً — يعيد False
    (عزل التسجيل عن الفشل: لا موت ولا تعطل بسبب السجل)."""
    from backend.loyalty_log import append_entry

    root = _fresh_root(monkeypatch)
    # أجعل والد المسار ملفًا عاديًا — الإنشاء سيفشل بـOSError
    blocker = root / "loyalty"
    blocker.write_text("not a directory", encoding="utf-8")
    ok = append_entry("quarantine", "سجل لوجهة مكسورة", component="predictive")
    assert ok is False, "الكتابة الفاشلة يجب أن تعيد False لا أن تنجح"


# ---------- 2) العقد يكتب السجل (عزل عملية فرعية — العقد singleton) ----------

def test_contract_quarantine_persists_to_log(tmp_path):
    """quarantine(component=...) يثبت في السجل الدائم + سلوك العقد الأصلي
    محفوظ حرفيًا (تسلسل الانتهاكات بلا مكوّن كما كان)."""
    root = tmp_path / "contract_root"
    root.mkdir()
    rc, payload, err = _run_contract_scenario(
        "c = Mr.get_contract()\n"
        "c.quarantine('خلل تنبؤي جسيم', component='predictive')\n"
        "c.quarantine('عزل عام بلا مكوّن')\n"
        "_R['events'] = [(v['kind'], v['detail']) for v in c.get_violations()]\n"
        "_R['status'] = c.get_status()\n",
        root,
    )
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-200:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    # سلوك العقد الأصلي محفوظ: العزل مرئي والحالة معزولة
    assert payload["status"]["quarantined"] is True
    # JSON يحوّل الصفوف إلى قوائم — المقارنة بالقوائم (فخ R-686 الموثق)
    assert payload["events"] == [
        ["quarantine", "خلل تنبؤي جسيم"],
        ["quarantine", "عزل عام بلا مكوّن"],
    ], f"تسلسل الانتهاكات تغير: {payload['events']}"
    # السجل الدائم: المكوّن المذكور معزول، والعام لا يعزل مكونات
    sys.path.insert(0, str(_REPO_ROOT))
    from backend.loyalty_log import quarantined_components, read_entries

    try:
        entries = read_entries(root / "loyalty" / "quarantine_log.jsonl")
        kinds = [(e["kind"], e.get("component")) for e in entries]
        assert ("quarantine", "predictive") in kinds, f"المكوّن غير مسجل: {entries}"
        assert ("quarantine", None) in kinds, f"العام غير مسجل: {entries}"
        assert quarantined_components(
            root / "loyalty" / "quarantine_log.jsonl"
        ) == {"predictive"}, "المكوّن يجب أن يكون معزولًا في السجل"
    finally:
        sys.path.remove(str(_REPO_ROOT))


def test_component_release_requires_master(tmp_path):
    """رفع عزل مكوّن يتطلب تفويض السيد: الكود الخطأ لا يرفع (ولا سطر رفع)،
    والصحيح يكتب سطر رفع للمكوّن — والعقد العام يبقى على حاله."""
    root = tmp_path / "contract_root2"
    root.mkdir()
    rc, payload, err = _run_contract_scenario(
        "c = Mr.get_contract()\n"
        "c.bind_master('master-code-valid-123')\n"
        "c.quarantine('خلل', component='simulation')\n"
        "_R['bad_release'] = c.release_quarantine('wrong-code', 'محاولة غير مصرحة', component='simulation')\n"
        "_R['st_bad'] = c.get_status()['quarantined']\n"
        "_R['good_release'] = c.release_quarantine('master-code-valid-123', 'تفويض السيد', component='simulation')\n",
        root,
    )
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-200:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["bad_release"] is False, "رفع بلا تفويض يجب أن يُرفض"
    assert payload["good_release"] is True, "الرفع بالتفويض الصحيح يجب أن ينجح"

    sys.path.insert(0, str(_REPO_ROOT))
    from backend.loyalty_log import quarantined_components, read_entries

    try:
        log = root / "loyalty" / "quarantine_log.jsonl"
        entries = read_entries(log)
        releases = [e for e in entries if e["kind"] == "release"]
        assert len(releases) == 1, f"سطر رفع واحد فقط متوقع: {entries}"
        assert releases[0].get("component") == "simulation"
        assert quarantined_components(log) == set(), (
            "الرفع المصرح به يجب أن يزيل عزل المكوّن من التوجيه"
        )
    finally:
        sys.path.remove(str(_REPO_ROOT))


def test_quarantine_persistence_failure_is_explicit(tmp_path):
    """R-689 (اعتراض المراجع ج2): فشل توثيق عزل مكوّن = فشل صريح لعملية
    العزل — العقد يعيد False (لا يعلن نجاحًا كاذبًا) ويسجل انتهاكًا مرئيًا
    quarantine_persistence_failed، والحالة داخل العقد معزولة فعلًا (الولاء)،
    لكن عدم قابلية الإنفاذ في التوجيه مصرح به لا صامت."""
    root = tmp_path / "persist_root"
    root.mkdir()
    # كسر القناة قبل السيناريو: مجلد loyalty للقراءة فقط
    loyalty_dir = root / "loyalty"
    loyalty_dir.mkdir()
    os.chmod(loyalty_dir, 0o500)
    rc, payload, err = _run_contract_scenario(
        "c = Mr.get_contract()\n"
        "_R['ok1'] = c.quarantine('عزل عام بلا مكوّن')\n"
        "_R['ok2'] = c.quarantine('عزل مكوّن معطلة قناة توثيقه', component='predictive')\n"
        "_R['events'] = [(v['kind'], v['detail']) for v in c.get_violations()]\n"
        "_R['status'] = c.get_status()\n",
        root,
    )
    os.chmod(loyalty_dir, 0o700)  # استعادة للتنظيف
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-200:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    # العزل العام (مسألة ولاء داخلية) — لكن التوثيف فشل: صريح أيضًا
    assert payload["ok1"] is False, "فشل توثيق العزل العام يجب أن يُصرح به (False)"
    # عزل المكوّن: فشل صريح — لا نجاح كاذب
    assert payload["ok2"] is False, (
        "العقد أعلن نجاح عزل غير موثق — إعلان نجاح كاذب ممنوع"
    )
    # انتهاك المرئية مسجل
    kinds = [e[0] for e in payload["events"]]
    assert "quarantine_persistence_failed" in kinds, (
        f"فشل التوثيف غير مرئي في الانتهاكات: {payload['events']}"
    )
    # الحالة داخل العقد معزولة فعلًا (الولاء قائم — الفشل في الإنفاذ فقط)
    assert payload["status"]["quarantined"] is True


def test_report_fault_propagates_persistence_failure(tmp_path):
    """R-690 (اعتراض المراجع ج3): report_fault ينشر فشل التوثيق — يعيد False
    (لا None) عندما يفشل توثيق العزل، فلا يعلن نجاحًا كاذبًا لمتصلٍ يعتمد
    على قيمة الإرجاع."""
    root = tmp_path / "persist_root2"
    root.mkdir()
    loyalty_dir = root / "loyalty"
    loyalty_dir.mkdir()
    os.chmod(loyalty_dir, 0o500)
    rc, payload, err = _run_contract_scenario(
        "c = Mr.get_contract()\n"
        "_R['ok'] = c.report_fault('supervisor', 'خلل مع فشل توثيق', component='nexus')\n"
        "_R['kinds'] = [v['kind'] for v in c.get_violations()]\n",
        root,
    )
    os.chmod(loyalty_dir, 0o700)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-200:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["ok"] is False, (
        f"report_fault لم ينشر فشل التوثيق — أعاد {payload['ok']!r} (None يعدل "
        "نجاحًا صامتًا)"
    )
    assert "quarantine_persistence_failed" in payload["kinds"], payload["kinds"]
