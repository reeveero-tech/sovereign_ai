# -*- coding: utf-8 -*-
"""
Invariant: نواة الولاء المعقّمة (R-686 — نزع الفتيل) — سلوك العقد الجديد

أمر المالك 2026-10-18 (المرحلة ١): «اقتلع القنبلة... استبدلها بالعزل: طبّق
منطق LoyaltyContract والحالة QUARANTINED كما صممت» + «الاختبارات: اكتب
اختبارات RED→GREEN تثبت أن الكود القديم كان يقتل النظام، والكود الجديد
يعزل الخطأ ويستمر.»

منهجية السيناريوهات: كل سيناريو يغير الحالة يُشغَّل في عملية منفصلة
(subprocess) — استقلال عن ترتيب الاختبارات (لا اعتماد على singleton
مشترك) + إثبات البقاء على مستوى العملية نفسها. التوكيدات محددة:
نوع الحدث ونصه لكل انتهاك/عزل/رفض/رفع (لا مجرد عدّ >=).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"

# علامات موت النواة القديمة — يجب ألا تظهر أبدًا في مخرجات أي سيناريو
DEATH_MARKERS = ("SOVRA IS DEAD", "CANNOT BE RESURRECTED")


def _run_scenario(body: str):
    """يشغل سيناريو في عملية منفصلة ويعيد (رمز الخروج، JSON، stderr، stdout).

    صلاحية السكربت تُفحص قبل التشغيل (compile) — لا يُقبل فشل لسبب
    خاطئ (منهجية RED النزيهة).
    """
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
    compile(script, "<scenario>", "exec")  # صلاحية السكربت قبل التشغيل
    result = subprocess.run(
        [sys.executable, "-u", "-c", script],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), timeout=60,
    )
    payload = None
    for line in result.stdout.splitlines():
        if line.startswith("SCENARIO_JSON:"):
            payload = json.loads(line[len("SCENARIO_JSON:"):])
    return result.returncode, payload, result.stderr, result.stdout


def _assert_alive_no_death(rc, payload, err, stdout):
    """ربط الأدلة الثلاثة في توكيد واحد: العملية حية (0) + نتيجة موجودة
    (علامة استمرار) + لا علامة موت قديمة في المخرجات — نفس السيناريو."""
    markers = [m for m in DEATH_MARKERS if m in (stdout or "")]
    assert (
        rc == 0 and payload is not None and not markers
    ), (
        f"موت أو فشل في نفس السيناريو: rc={rc} (المتوقع 0)، "
        f"payload={'موجود' if payload is not None else 'غائب — لا علامة استمرار'}، "
        f"علامات الموت الملتقطة={markers}، stderr={err[-200:]!r}"
    )
    assert "unexpected_error" not in payload, (
        f"خطأ غير متوقع داخل السيناريو: {payload['unexpected_error']}"
    )


MASTER = "test-master-code-32-bytes-ok-ok!!"


class TestDefusedContract:
    """العقد الجديد: ربط وفحص وعزل — بلا أي موت"""

    def test_bind_and_verify_master(self):
        rc, r, err, out = _run_scenario(
            "_R['bind'] = Mr.bind_loyalty_to_master(" + repr(MASTER) + ")\n"
            "_R['verify_ok'] = Mr.verify_master(" + repr(MASTER) + ")\n"
            "_R['verify_wrong'] = Mr.verify_master('WRONG')\n"
            "st = Mr.get_loyalty_status()\n"
            "_R['state'] = st['state']\n"
            "_R['loyal'] = st['loyal']\n"
            "_R['master_bound'] = st['master_bound']\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        assert r["bind"] is True
        assert r["verify_ok"] is True
        assert r["verify_wrong"] is False
        assert r["state"] == "sealed"
        assert r["loyal"] is True
        assert r["master_bound"] is True

    def test_is_loyal_requires_binding(self):
        """الولاء يتطلب ربط السيد — لا ولاء قبل الربط (تصويب المراجع)"""
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "_R['loyal_before'] = c.is_loyal()\n"
            "c.bind_master(" + repr(MASTER) + ")\n"
            "_R['loyal_after'] = c.is_loyal()\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        assert r["loyal_before"] is False
        assert r["loyal_after"] is True

    def test_double_bind_isolated_not_fatal(self):
        """التسلسل القاتل في الكود القديم (ربط مزدوج = موت) — الآن عزل وبقاء
        + حدث انتهاك محدد النوع والنص"""
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "_R['first'] = c.bind_master(" + repr(MASTER) + ")\n"
            "_R['second'] = c.bind_master(" + repr(MASTER) + ")\n"
            "st = c.get_status()\n"
            "_R['still_loyal'] = st['loyal']\n"
            "_R['events'] = [(v['kind'], v['detail']) for v in c.get_violations()]\n"
        )
        # العملية نفسها بقيت حية وخرجت 0 — هذا جوهر نزع الفتيل
        _assert_alive_no_death(rc, r, err, out)
        r["events"] = [tuple(e) for e in r["events"]]
        assert r["first"] is True
        assert r["second"] is False
        assert r["still_loyal"] is True
        # توكيد محدد: تسلسل (kind, detail) كاملًا — بلا عدّ >=
        assert r["events"] == [
            ("double_bind", "محاولة إعادة ربط السيد — عُزلت المحاولة وسُجلت (لا موت)"),
        ], f"التسلسل المتوقع بالضبط: {r['events']}"

    def test_old_killer_sequence_now_survives(self):
        """التسلسل الذي قتل النظام القديم فعليًا: تهيئة يدوية ثم ربط
        (initialize ثانٍ قبل الختم ← موت نهائي — المسار في مصدر الأب
        41936cc هو os._exit(1) في السطر 506، حقيقة من قراءة المصدر لا
        استنتاجًا من المخرجات). الإثبات السلوكي: العملية تخرج 0 + لا
        علامة موت في المخرجات + الولاء قائم."""
        rc, r, err, out = _run_scenario(
            "c1 = Mr.initialize_loyalty_core()\n"
            "_R['init_twice_safe'] = Mr.initialize_loyalty_core() is c1\n"
            "_R['bind'] = Mr.bind_loyalty_to_master(" + repr(MASTER) + ")\n"
            "_R['init_after_bind'] = Mr.initialize_loyalty_core() is c1\n"
            "_R['loyal'] = Mr.is_loyal()\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        assert r["init_twice_safe"] is True
        assert r["bind"] is True
        assert r["init_after_bind"] is True
        assert r["loyal"] is True

    def test_quarantine_visible_and_release_requires_master(self):
        """العزل مرئي وقابل للتراجع — ورفعه يتطلب تفويض السيد (تصويب المراجع)
        + أحداث محددة النوع والنص لكل خطوة"""
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "c.bind_master(" + repr(MASTER) + ")\n"
            "c.quarantine('خلل جسيم للاختبار')\n"
            "st = c.get_status()\n"
            "_R['quarantined'] = st['quarantined']\n"
            "_R['not_loyal'] = st['loyal'] is False\n"
            "_R['reason'] = st['quarantine_reason']\n"
            "_R['release_wrong'] = c.release_quarantine('WRONG-CODE', 'محاولة غير مصرح')\n"
            "_R['still_quarantined'] = c.get_status()['quarantined']\n"
            "_R['release_ok'] = c.release_quarantine(" + repr(MASTER) + ", 'قرار موثق')\n"
            "st2 = c.get_status()\n"
            "_R['back_sealed'] = st2['state'] == 'sealed'\n"
            "_R['loyal_again'] = st2['loyal']\n"
            "_R['kinds'] = [v['kind'] for v in c.get_violations()]\n"
            "_R['events'] = [(v['kind'], v['detail']) for v in c.get_violations()]\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        r["events"] = [tuple(e) for e in r["events"]]
        assert r["quarantined"] is True
        assert r["not_loyal"] is True
        assert r["reason"] == "خلل جسيم للاختبار"
        assert r["release_wrong"] is False
        assert r["still_quarantined"] is True
        assert r["release_ok"] is True
        assert r["back_sealed"] is True
        assert r["loyal_again"] is True
        # توكيد محدد: تسلسل (kind, detail) كاملًا — بلا عدّ >=
        assert r["events"] == [
            ("quarantine", "خلل جسيم للاختبار"),
            ("unauthorized_release", "محاولة رفع عزل بلا تفويض السيد — رُفضت وسُجلت"),
            ("release", "رفع العزل — القرار: قرار موثق"),
        ], f"التسلسل المتوقع بالضبط: {r['events']}"

    def test_quarantine_recovery_path(self):
        """تصويب المراجع (جولتان): (١) لا رفع عزل ضمني عبر الربط،
        (٢) لا حبس بلا استرداد — الربط أثناء العزل يهيّئ اعتماد السيد
        والحالة تبقى معزولة، ثم الرفع بالتفويض الصحيح فقط.
        المسار كاملًا: عزل ← تهيئة الاعتماد (العزل قائم) ← تفويض خاطئ
        مرفوض ← التفويض الصحيح يعيد الحالة المسموحة."""
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "c.quarantine('خلل قبل الربط')\n"
            "_R['bind_sets_credential'] = c.bind_master(" + repr(MASTER) + ")\n"
            "st = c.get_status()\n"
            "_R['still_quarantined'] = st['quarantined']\n"
            "_R['master_bound'] = st['master_bound']\n"
            "_R['release_wrong'] = c.release_quarantine('WRONG', 'تفويض خاطئ')\n"
            "_R['still_quarantined2'] = c.get_status()['quarantined']\n"
            "_R['release_ok'] = c.release_quarantine(" + repr(MASTER) + ", 'قرار موثق')\n"
            "st2 = c.get_status()\n"
            "_R['back_sealed'] = st2['state'] == 'sealed'\n"
            "_R['loyal'] = st2['loyal']\n"
            "_R['events'] = [(v['kind'], v['detail']) for v in c.get_violations()]\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        r["events"] = [tuple(e) for e in r["events"]]
        assert r["bind_sets_credential"] is True, "الربط يهيّئ الاعتماد أثناء العزل"
        assert r["still_quarantined"] is True, "لا رفع عزل ضمني — العزل قائم بعد الربط"
        assert r["master_bound"] is True
        assert r["release_wrong"] is False, "التفويض الخاطئ مرفوض"
        assert r["still_quarantined2"] is True
        assert r["release_ok"] is True, "التفويض الصحيح يرفع العزل"
        assert r["back_sealed"] is True
        assert r["loyal"] is True
        assert r["events"] == [
            ("quarantine", "خلل قبل الربط"),
            ("bind_during_quarantine", "تهيئة اعتماد السيد أثناء العزل — العزل قائم حتى التفويض"),
            ("unauthorized_release", "محاولة رفع عزل بلا تفويض السيد — رُفضت وسُجلت"),
            ("release", "رفع العزل — القرار: قرار موثق"),
        ], f"التسلسل المتوقع بالضبط: {r['events']}"

    def test_tamper_attempt_detected_and_quarantined(self):
        """كشف العبث الداخلي يعمل فعلًا حيث كان خطاف الأصل وهميًا (مثبت
        بالتشغيل على 41936cc: الكتابة كانت تنجو والموت جاء من فحص الولاء
        بعدها): الكتابة المباشرة للحقل المحمي تُكتشف وتُرفض فورًا ← عزل
        + حدث مسجل — بلا أي استدعاء يدوي لـquarantine/report_fault."""
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "c.bind_master(" + repr(MASTER) + ")\n"
            "c._master_hash = 'TAMPERED-HASH'\n"  # الخلل الفعلي نفسه
            "st = c.get_status()\n"
            "_R['auto_quarantined'] = st['quarantined']\n"
            "_R['write_refused'] = c._master_hash != 'TAMPERED-HASH'\n"
            "_R['loyal_suspended'] = st['loyal'] is False\n"
            "_R['events'] = [(v['kind'], v['detail']) for v in c.get_violations()]\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        r["events"] = [tuple(e) for e in r["events"]]
        assert r["auto_quarantined"] is True, (
            "الكتابة المباشرة للحالة المحمية يجب أن تعزل تلقائيًا (كشف موروث)"
        )
        assert r["write_refused"] is True, "الكتابة العابثة مرفوضة — الحالة الأصلية باقية"
        assert r["loyal_suspended"] is True
        assert r["events"] == [
            ("tamper_attempt", "محاولة تعديل الحالة مباشرة (عبث): _master_hash"),
            ("quarantine", "عبث مكتشف: كتابة مباشرة للحالة المحمية (_master_hash)"),
        ], f"التسلسل المتوقع بالضبط: {r['events']}"

    def test_report_fault_quarantines_with_logged_event(self):
        """نقطة دخول اكتشاف الأخطاء: report_fault ← عزل + حدث مسجل محدد
        (بديل مسارات الموت القديمة: الخلل يعزل لا يقتل)"""
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "c.bind_master(" + repr(MASTER) + ")\n"
            "c.report_fault('integrity_check', 'فشل فحص السلامة')\n"
            "st = c.get_status()\n"
            "_R['quarantined'] = st['quarantined']\n"
            "_R['reason'] = st['quarantine_reason']\n"
            "_R['q_events'] = [v for v in c.get_violations() if v['kind'] == 'quarantine']\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        assert r["quarantined"] is True
        assert r["reason"] == "[integrity_check] فشل فحص السلامة"
        assert len(r["q_events"]) == 1
        assert r["q_events"][0]["detail"] == "[integrity_check] فشل فحص السلامة"

    def test_repeated_unauthorized_release_auto_quarantines(self):
        """كشف ← استجابة: ٣ محاولات رفع غير مصرح ← عزل تلقائي (إن لم يكن
        معزولًا) + أحداث محددة"""
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "c.bind_master(" + repr(MASTER) + ")\n"
            "for i in range(3):\n"
            "    c.release_quarantine('WRONG-' + str(i), 'محاولة')\n"
            "st = c.get_status()\n"
            "_R['auto_quarantined'] = st['quarantined']\n"
            "_R['reason'] = st['quarantine_reason']\n"
            "_R['events'] = [(v['kind'], v['detail']) for v in c.get_violations()]\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        r["events"] = [tuple(e) for e in r["events"]]
        assert r["auto_quarantined"] is True, (
            "تكرار المحاولات غير المصرح بها (٣+) يجب أن يعزل تلقائيًا"
        )
        assert r["reason"] == "تكرار محاولات رفع غير مصرح بها (٣+)"
        # القائمة كاملة بلا ترشيح — ٣ رفض ثم العزل التلقائي، بالضبط
        assert r["events"] == [
            ("unauthorized_release", "محاولة رفع عزل بلا تفويض السيد — رُفضت وسُجلت"),
            ("unauthorized_release", "محاولة رفع عزل بلا تفويض السيد — رُفضت وسُجلت"),
            ("unauthorized_release", "محاولة رفع عزل بلا تفويض السيد — رُفضت وسُجلت"),
            ("quarantine", "تكرار محاولات رفع غير مصرح بها (٣+)"),
        ], f"التسلسل المتوقع بالضبط: {r['events']}"

    def test_status_declares_zero_death_paths(self):
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "c.bind_master(" + repr(MASTER) + ")\n"
            "_R['death_paths'] = c.get_status()['death_paths']\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        assert r["death_paths"] == 0

    def test_get_violations_is_read_only(self):
        """سجل الانتهاكات للفحص دون تعديل الحالة — نسخة قراءة فقط"""
        rc, r, err, out = _run_scenario(
            "c = Mr.get_contract()\n"
            "c.bind_master(" + repr(MASTER) + ")\n"
            "c.bind_master(" + repr(MASTER) + ")\n"
            "before = c.get_violations()\n"
            "before.append({'kind': 'مزيف', 'detail': 'تلاعب'})\n"
            "_R['internal_untouched'] = len(c.get_violations())\n"
            "_R['count'] = len(before)\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        assert r["internal_untouched"] == 1, (
            "التعديل على النسخة المرجعة يجب ألا يمس السجل الداخلي"
        )
        assert r["count"] == 2

    def test_unreadable_core_at_init_fails_safe(self):
        """فجوة الجولة السادسة (RED أولًا): فشل قراءة ملف النواة أثناء ختم
        خط الأساس لا يجوز أن يترك التحقق ناجحًا بلا خط أساس (فتح مفتوح).
        النتيجة الآمنة: لا ولاء مع سلامة غير متحققة ← عزل + حدث محدد."""
        import json
        mr_src = str(_BACKEND_DIR / "Mr.py")
        script = "\n".join([
            "import sys, shutil, tempfile, pathlib, os, json",
            "core_dir = pathlib.Path(tempfile.mkdtemp()) / 'core'",
            "core_dir.mkdir()",
            f"shutil.copy(r'{mr_src}', core_dir / 'Mr.py')",
            "core_file = core_dir / 'Mr.py'",
            "sys.path.insert(0, str(core_dir))",
            "import Mr",
            "os.chmod(core_file, 0o000)  # القراءة تفشل أثناء ختم خط الأساس",
            "bound = Mr.bind_loyalty_to_master('CORE-MASTER')",
            "os.chmod(core_file, 0o644)  # القراءة تعود — لكن الخط لم يُختم",
            "loyal = Mr.is_loyal()",
            "st = Mr.get_loyalty_status()",
            "events = [(v['kind'], v['detail']) for v in"
            " Mr.get_contract().get_violations()]",
            "print('CORE_JSON:' + json.dumps({'bound': bound, 'loyal': loyal,",
            " 'quarantined': st['quarantined'], 'events': events}))",
        ])
        compile(script, "<unreadable-core>", "exec")
        proc = subprocess.run(
            [sys.executable, "-u", "-c", script],
            capture_output=True, text=True, timeout=60, cwd=str(_REPO_ROOT),
        )
        payload = None
        for line in (proc.stdout or "").splitlines():
            if line.startswith("CORE_JSON:"):
                payload = json.loads(line[len("CORE_JSON:"):])
        assert proc.returncode == 0, f"العملية ماتت: {proc.stderr[-300:]}"
        assert payload is not None, f"لا نتيجة: {proc.stdout!r}"
        assert payload["bound"] is True
        # الفشل الآمن: لا ولاء مع سلامة غير متحققة
        assert payload["loyal"] is False, (
            "فشل ختم خط الأساس يجب أن يمنع إعلان الولاء (فتح مفتوح)"
        )
        assert payload["quarantined"] is True, (
            "فقدان خط الأساس يجب أن يعزل — لا تحقق ناجح بلا سلامة"
        )
        payload["events"] = [tuple(e) for e in payload["events"]]
        # تسلسل (kind, detail) كاملًا — بلا ترشيح يخفي زيادات
        assert payload["events"] == [
            ("self_baseline_failed", "فشل قراءة ملف النواة عند ختم خط الأساس"),
            ("self_baseline_missing",
             "خط أساس سلامة النواة مفقود — لا ولاء بلا سلامة متحققة"),
            ("quarantine",
             "خط أساس سلامة النواة مفقود (فشل القراءة عند التهيئة)"),
        ], f"التسلسل المتوقع بالضبط: {payload['events']}"

    def test_reseal_cannot_hide_core_tamper(self):
        """فجوة الجولة السادسة (RED أولًا): إعادة ختم خط أساس النواة بعد
        تعديلها لا يجوز أن تخفي المخالفة (إعادة اعتماد الملف المعدّل).
        المحاولة تُرفض وتُسجل، والخط الأصلي باقٍ، والتعديل يُكتشف."""
        import json
        mr_src = str(_BACKEND_DIR / "Mr.py")
        script = "\n".join([
            "import sys, shutil, tempfile, pathlib, json",
            "core_dir = pathlib.Path(tempfile.mkdtemp()) / 'core'",
            "core_dir.mkdir()",
            f"shutil.copy(r'{mr_src}', core_dir / 'Mr.py')",
            "core_file = core_dir / 'Mr.py'",
            "sys.path.insert(0, str(core_dir))",
            "import Mr",
            "bound = Mr.bind_loyalty_to_master('CORE-MASTER')",
            "core_file.write_text(core_file.read_text(encoding='utf-8')"
            " + '\\n# TAMPERED\\n', encoding='utf-8')",
            "c = Mr.get_contract()",
            "baseline_before = dict(c._file_baselines)",
            "c.seal_file_baseline(str(core_file))  # محاولة إعادة ختم مخفية",
            "baseline_after = dict(c._file_baselines)",
            "loyal = Mr.is_loyal()",
            "st = c.get_status()",
            "events = [(v['kind'], v['detail']) for v in c.get_violations()]",
            "print('CORE_JSON:' + json.dumps({'bound': bound, 'loyal': loyal,",
            " 'quarantined': st['quarantined'], 'events': events,",
            " 'core_path': str(core_file),",
            " 'baseline_unchanged': baseline_before == baseline_after}))",
        ])
        compile(script, "<reseal-probe>", "exec")
        proc = subprocess.run(
            [sys.executable, "-u", "-c", script],
            capture_output=True, text=True, timeout=60, cwd=str(_REPO_ROOT),
        )
        payload = None
        for line in (proc.stdout or "").splitlines():
            if line.startswith("CORE_JSON:"):
                payload = json.loads(line[len("CORE_JSON:"):])
        assert proc.returncode == 0, f"العملية ماتت: {proc.stderr[-300:]}"
        assert payload is not None, f"لا نتيجة: {proc.stdout!r}"
        assert payload["bound"] is True
        assert payload["loyal"] is False, (
            "إعادة الختم يجب ألا تخفي التعديل — الولاء لا يُعلن"
        )
        assert payload["quarantined"] is True, (
            "التعديل يجب أن يُكتشف رغم محاولة إعادة الختم"
        )
        # خط الأساس الأصلي باقٍ حرفيًا — لم تستبدله محاولة إعادة الختم
        assert payload["baseline_unchanged"] is True, (
            "محاولة إعادة الختم يجب ألا تغيّر خط الأساس الأصلي"
        )
        payload["events"] = [tuple(e) for e in payload["events"]]
        # مقارنة واحدة كاملة بالمسار المتوقع للنواة نفسها — لا توكيد جزئي
        reason = "تعديل ملف مراقب على القرص: " + payload["core_path"]
        assert payload["events"] == [
            (
                "baseline_reseal_refused",
                "رفض إعادة ختم خط أساس النواة — الخط الأصلي باقٍ والمحاولة مسجلة",
            ),
            ("file_integrity", reason),
            ("quarantine", reason),
        ], f"التسلسل المتوقع بالضبط (بمسار النواة): {payload['events']}"

    def test_core_file_modification_detected_by_normal_verification(self):
        """فجوة الجولة الخامسة (RED أولًا): تعديل ملف النواة نفسها يجب أن
        يُكتشف عبر مسار التحقق المعتاد — التهيئة تسجل خط أساس ملفها
        تلقائيًا، وverify_master/is_loyal يفحصانه: تعديل على القرص ← عزل +
        العملية حية. نسخة معزولة من النواة (لا مساس بملف المستودع) وبلا
        أي تسجيل خط أساس يدوي بعد التعديل."""
        import json
        mr_src = str(_BACKEND_DIR / "Mr.py")
        script = "\n".join([
            "import sys, shutil, tempfile, pathlib, json",
            "core_dir = pathlib.Path(tempfile.mkdtemp()) / 'core'",
            "core_dir.mkdir()",
            f"shutil.copy(r'{mr_src}', core_dir / 'Mr.py')",
            "sys.path.insert(0, str(core_dir))",
            "import Mr",
            "bound = Mr.bind_loyalty_to_master('CORE-MASTER')",
            "loyal_before = Mr.is_loyal()",
            "# تعديل ملف النواة على القرص — بعد التهيئة (خط الأساس تلقائي)",
            "core_file = core_dir / 'Mr.py'",
            "core_file.write_text(core_file.read_text(encoding='utf-8')",
            " + '\\n# TAMPERED\\n', encoding='utf-8')",
            "verify_after = Mr.verify_master('CORE-MASTER')",
            "st = Mr.get_loyalty_status()",
            "reason = st['quarantine_reason'] or ''",
            "print('CORE_JSON:' + json.dumps({'bound': bound,",
            " 'loyal_before': loyal_before, 'verify_after': verify_after,",
            " 'quarantined': st['quarantined'], 'reason': reason}))",
        ])
        compile(script, "<core-scenario>", "exec")
        proc = subprocess.run(
            [sys.executable, "-u", "-c", script],
            capture_output=True, text=True, timeout=60, cwd=str(_REPO_ROOT),
        )
        payload = None
        for line in (proc.stdout or "").splitlines():
            if line.startswith("CORE_JSON:"):
                payload = json.loads(line[len("CORE_JSON:"):])
        assert proc.returncode == 0, f"العملية ماتت: {proc.stderr[-300:]}"
        assert payload is not None, f"لا نتيجة: {proc.stdout!r}"
        assert payload["bound"] is True
        assert payload["loyal_before"] is True
        # الفجوة: التعديل يجب أن يُكتشف عبر التحقق المعتاد — لا يدويًا
        assert payload["quarantined"] is True, (
            "تعديل ملف النواة على القرص لم يُكتشف عبر مسار التحقق المعتاد — "
            "الفحص غير مربوط بالنواة"
        )
        assert payload["verify_after"] is False, (
            "التحقق بعد تعديل النواة يجب أن يفشل"
        )
        assert "Mr.py" in payload["reason"], (
            f"سبب العزل يجب أن يوثق ملف النواة: {payload['reason']}"
        )

    def test_file_integrity_check_quarantines_on_modification(self):
        """فحص سلامة الملف على القرص — بديل حارس الملفات القديم القاتل
        (daemon يقتل عند تعديل Mr.py): فحص صريح بلا خيط خلفي وبلا موت —
        اختلاف الملف المراقب ← عزل + حدث مسجل، والمطابقة ← لا شيء.
        (فصل حساب السلامة عن الإنهاء — دون Supervisor ودون daemon.)"""
        rc, r, err, out = _run_scenario(
            "import tempfile, pathlib\n"
            "tmp = pathlib.Path(tempfile.mkdtemp()) / 'watched.py'\n"
            "tmp.write_text('V1', encoding='utf-8')\n"
            "c = Mr.get_contract()\n"
            "c.seal_file_baseline(str(tmp))\n"
            "_R['first_check'] = c.check_file_integrity(str(tmp))\n"
            "_R['not_quarantined'] = c.get_status()['quarantined'] is False\n"
            "tmp.write_text('V2-TAMPERED', encoding='utf-8')\n"
            "_R['second_check'] = c.check_file_integrity(str(tmp))\n"
            "st = c.get_status()\n"
            "_R['auto_quarantined'] = st['quarantined']\n"
            "_R['reason'] = st['quarantine_reason']\n"
            "_R['events'] = [(v['kind'], v['detail']) for v in c.get_violations()]\n"
        )
        _assert_alive_no_death(rc, r, err, out)
        r["events"] = [tuple(e) for e in r["events"]]
        assert r["first_check"] is True, "ملف مطابق لخط الأساس = سلامة"
        assert r["not_quarantined"] is True
        assert r["second_check"] is False, "ملف معدّل = فشل الفحص"
        assert r["auto_quarantined"] is True, (
            "تعديل الملف المراقب يجب أن يعزل (استجابة العزل بدل الموت)"
        )
        assert "watched.py" in r["reason"]
        # حدثان بالضبط: file_integrity محدد + العزل المرئي (نفس النص)
        assert len(r["events"]) == 2, f"حدثان بالضبط: {r['events']}"
        assert r["events"][0][0] == "file_integrity", (
            f"نوع الحدث file_integrity: {r['events']}"
        )
        assert r["events"][0][1].startswith("تعديل ملف مراقب على القرص: "), (
            f"نص الحدث يوثق الملف المعدل: {r['events']}"
        )
        assert "watched.py" in r["events"][0][1]
        assert r["events"][1] == ("quarantine", r["events"][0][1]), (
            f"العزل مرئي بنفس النص: {r['events']}"
        )


class TestMrNotBoundToLiveSystem:
    """«ممنوع ربط Mr.py بـ app.py في هذا الالتزام» — النظام الحي لا يعرفه"""

    def test_no_live_code_imports_mr(self):
        live = [
            p for p in _BACKEND_DIR.rglob("*.py")
            if "tests" not in p.parts and p.name != "Mr.py"
        ]
        live += [p for p in (_REPO_ROOT / "nexus").rglob("*.py")]
        live += [p for p in _REPO_ROOT.glob("*.py")]
        assert live
        for p in live:
            src = p.read_text(encoding="utf-8")
            for banned in ("import Mr", "from Mr import", "backend.Mr"):
                assert banned not in src, (
                    f"ربط ممنوع بالمرحلة ١ (أمر المالك): {p} يحتوي «{banned}»"
                )
