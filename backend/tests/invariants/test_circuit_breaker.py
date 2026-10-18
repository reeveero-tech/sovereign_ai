# -*- coding: utf-8 -*-
"""
مدخل التوجيه (Circuit Breaker) — المرحلة ٢ من META_SYSTEM (R-687)

أمر المالك 2026-10-18: «مدخل يقرأ من سجل العزل ويرفض توجيه الطلبات
للمكونات المعزولة (يرجع خطأ محدد)، بينما تستمر بقية المكونات بالعمل».

يُختبر التطبيق الحي نفسه (TestClient على backend/app.py): المكوّن المعزول
يرجع 503 بجسم خطأ محدد (error=component_quarantined + اسم المكوّن)،
وبقية المكونات والمسارات غير المكوّنية تمر. الحارس المعزول (supervisor)
ممنوع استيراده في app.py — يُختبر في tests/test_supervisor_isolated.py.

تصميم العزل (تصويب بعد RED): لا monkeypatch لجذر البيانات إطلاقًا —
التطبيق يقلع على جذر الجلسة ومفتاحها المعروف (R-634) فيبقى سجل الجلسة
نظيفًا (حارس R-682 يفحص توقيع الأحداث في نهاية الجلسة). عزل كل اختبار
يتم باستعادة سجل العزل حوله: لقطة قبل (وجود + محتوى) ← استعادة بعد —
سجل الجلسة سقالة اختبار (جذر مؤقت) لا دليل جنائي؛ خاصية append-only
الإنتاجية محروسة بذاتها في test_quarantine_log.py على جذور معزولة.
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for _p in (str(_REPO_ROOT), str(_BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi.testclient import TestClient

from app import app  # noqa: E402
from backend.loyalty_log import append_entry, quarantine_log_path  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_session_quarantine_log():
    """عزل الاختبارات عن بعضها: لقطة لسجل عزل الجلسة قبل الاختبار ← استعادة
    بعده (حذف إن لم يكن موجودًا / إعادة المحتوى الأصلي إن كان) — يعمل حتى
    عند فشل الاختبار في منتصفه (finally). يشمل تفريغ احتياط الذاكرة لمسار
    الجلسة وتصفير كاش المدخل وفحص القناة (لا تسريب حالة بين الاختبارات —
    R-689)."""
    log = quarantine_log_path()
    existed = log.exists()
    original = log.read_text(encoding="utf-8") if existed else None
    from backend.loyalty_log import clear_fallback
    clear_fallback(log)
    import backend.circuit_breaker as _cb
    with _cb._CACHE_LOCK:
        _cb._CACHE.update(path=None, stamp=None, components=set())
    with _cb._PROBE_LOCK:
        _cb._PROBE.update(ts=0.0, ok=True)
    yield
    clear_fallback(log)
    with _cb._CACHE_LOCK:
        _cb._CACHE.update(path=None, stamp=None, components=set())
    with _cb._PROBE_LOCK:
        _cb._PROBE.update(ts=0.0, ok=True)
    if existed:
        log.write_text(original, encoding="utf-8")
    elif log.exists():
        log.unlink()


def test_quarantined_component_request_rejected():
    """الطلب لمكوّن معزول يُرفض بأمان: 503 + جسم خطأ محدد."""
    assert append_entry("quarantine", "خلل جسيم", component="predictive") is True
    with TestClient(app) as client:
        resp = client.get("/components/predictive")
        assert resp.status_code == 503, (
            f"المكوّن المعزول يجب أن يُرفض 503 — أعيد {resp.status_code}"
        )
        body = resp.json()
        assert body["error"] == "component_quarantined", f"جسم غير محدد: {body}"
        assert body["component"] == "predictive", f"اسم المكوّن مفقود: {body}"
        assert isinstance(body.get("detail"), str) and body["detail"], (
            f"تفصيل الخطأ مفقود: {body}"
        )


def test_other_components_pass_while_one_quarantined():
    """بينما مكوّن معزول: بقية المكونات تعمل — الأمر نصًّا."""
    append_entry("quarantine", "خلل جسيم", component="predictive")
    with TestClient(app) as client:
        for component in ("memory", "consciousness", "simulation"):
            resp = client.get(f"/components/{component}")
            assert resp.status_code == 200, (
                f"المكوّن غير المعزول {component} يجب أن يمر — "
                f"أعيد {resp.status_code}: {resp.text[:200]}"
            )


def test_non_component_routes_not_gated():
    """المدخل يعزل مكونات فقط: /health و/ (الواجهة) لا يُحجبان حتى مع
    وجود مكوّن معزول."""
    append_entry("quarantine", "خلل", component="consciousness")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 200


def test_release_restores_routing():
    """الرفع المصرح (سطر رفع في السجل) يعيد توجيه المكوّن — دورة كاملة."""
    append_entry("quarantine", "خلل", component="quantum")
    with TestClient(app) as client:
        assert client.get("/components/quantum").status_code == 503
        assert append_entry(
            "release", "رفع بتفويض السيد", component="quantum"
        ) is True
        resp = client.get("/components/quantum")
        assert resp.status_code == 200, (
            f"الرفع يجب أن يعيد التوجيه — أعيد {resp.status_code}: {resp.text[:200]}"
        )


def test_no_quarantine_all_components_pass():
    """بلا سجل عزل: كل المكونات تعمل (ضابط — لا حجب بلا سبب)."""
    with TestClient(app) as client:
        for component in (
            "consciousness", "memory", "predictive", "simulation",
            "sovereign", "quantum", "nexus", "defense",
        ):
            resp = client.get(f"/components/{component}")
            assert resp.status_code == 200, (
                f"بلا عزل يجب أن يمر {component} — أعيد {resp.status_code}"
            )


# ---------- اعتراضات المراجع (R-688): لا سماح صامت عند فشل السجل ----------

def test_quarantine_write_failure_is_not_silent_allow():
    """اعتراض المراجع: فشل كتابة سجل العزل يجب ألا يتحول سماحًا صامتًا —
    المكوّن المعزول يُرفض رغم فشل التوثيق على القرص (الحدث محفوظ في ذاكرة
    العملية كاحتياط مرئي)، وبقية المكونات تستمر (الأمر نصًّا)."""
    import stat as stat_mod
    log = quarantine_log_path()
    blocker = log.parent  # مجلد loyalty
    blocker.mkdir(parents=True, exist_ok=True)
    file_existed = log.exists()
    restored_modes = []
    # منع الكتابة في الحالتين: إنشاء ملف جديد (يحتاج كتابة المجلد) وإلحاق
    # بملف موجود (يحتاج كتابة الملف نفسه) — الحجبان معًا للاستقلال عن الترتيب
    blocker.chmod(0o500)
    if file_existed:
        restored_modes.append((log, log.stat().st_mode & 0o777))
        log.chmod(0o444)
    try:
        ok = append_entry("quarantine", "خلل مع فشل توثيق", component="predictive")
        assert ok is False, "الكتابة يجب أن تفشل هنا (المجلد/الملف للقراءة فقط) — وإلا فالاختبار لا يختبر شيئًا"
        with TestClient(app) as client:
            r1 = client.get("/components/predictive")
            assert r1.status_code == 503, (
                f"سماح صامت ممنوع: المكوّن المعزول يُرفض رغم فشل التوثيق — "
                f"أعيد {r1.status_code}: {r1.text[:200]}"
            )
            assert r1.json()["error"] == "component_quarantined", r1.text[:200]
            r2 = client.get("/components/memory")
            assert r2.status_code == 200, (
                f"بقية المكونات تستمر رغم فشل السجل — أعيد {r2.status_code}"
            )
    finally:
        from backend.loyalty_log import clear_fallback
        blocker.chmod(0o700)
        for p, m in restored_modes:
            p.chmod(m)
        clear_fallback(log)


def test_unreadable_log_fails_closed_not_silent_allow():
    """اعتراض المراجع: سجل موجود لكنه غير قابل للقراءة = حالة لا يمكن إثباتها —
    الإغلاق على مسارات المكونات بخطأ محدد (لا سماح صامت ولا إسقاط لعزل مثبت)،
    والتطبيق حي (المسارات غير المكوّنية تعمل)."""
    import stat as stat_mod
    log = quarantine_log_path()
    assert append_entry("quarantine", "عزل مثبت قبل التعطيل", component="quantum") is True
    log.chmod(0)  # غير قابل للقراءة حتى لصاحبه — الحالة تصير غير قابلة للإثبات
    try:
        import backend.circuit_breaker as cb
        with cb._CACHE_LOCK:  # اختبار المسار البارد: بلا ذاكرة سابقة
            cb._CACHE.update(path=None, stamp=None, components=set())
        with TestClient(app) as client:
            r1 = client.get("/components/quantum")
            assert r1.status_code == 503, (
                f"لا سماح صامت عند سجل غير مقروء — أعيد {r1.status_code}"
            )
            assert r1.json()["error"] == "quarantine_log_unreadable", (
                f"خطأ محدد مطلوب: {r1.text[:200]}"
            )
            r2 = client.get("/components/memory")
            assert r2.status_code == 503 and r2.json()["error"] == "quarantine_log_unreadable", (
                "حالة غير قابلة للإثبات = إغلاق على كل مسارات المكونات بخطأ محدد"
            )
            assert client.get("/health").status_code == 200, "التطبيق حي — الإغلاق على المسار لا العملية"
    finally:
        log.chmod(stat_mod.S_IRUSR | stat_mod.S_IWUSR | stat_mod.S_IRGRP | stat_mod.S_IROTH)
        import backend.circuit_breaker as cb
        with cb._CACHE_LOCK:
            cb._CACHE.update(path=None, stamp=None, components=set())


def test_component_routes_fully_covered_by_breaker():
    """اعتراض المراجع (نطاق التوجيه): كل مسار مسجل يخاطب مكوّنًا باسمه
    (/components/...) يجب أن يقع داخل تغطية المدخل — لا مسار مكوّن يهرب."""
    from backend.circuit_breaker import _COMPONENT_ROUTE
    comp_routes = [
        getattr(r, "path", "") for r in app.routes
        if getattr(r, "path", "").startswith("/components/")
    ]
    assert comp_routes, "لا مسارات مكونات — المسح نفسه معطوب"
    for p in comp_routes:
        assert _COMPONENT_ROUTE.match(p), (
            f"مسار مكون خارج تغطية المدخل (سماح محتمل): {p}"
        )


def test_feature_routes_of_quarantined_component_rejected():
    """R-688 (مسح نطاق التوجيه): مسارات الميزات التي تخاطب مكوّنًا بالاسم —
    /nexus/recommendations/* (نكسس) و/sovereign/command (سيادي) — تُرفض
    بأمان عندما يكون مكوّنها معزولًا (الطلب موجه للمكوّن فعلًا، لا عرض حالة
    فقط)، وبقية المسارات غير المكوّنية تعمل."""
    assert append_entry("quarantine", "عزل نكسس", component="nexus") is True
    assert append_entry("quarantine", "عزل السيادي", component="sovereign") is True
    with TestClient(app) as client:
        r1 = client.get("/nexus/recommendations/pending")
        assert r1.status_code == 503, (
            f"مسار ميزة نكسس يجب أن يُرفض والمكوّن معزول — أعيد "
            f"{r1.status_code}: {r1.text[:200]}"
        )
        assert r1.json()["error"] == "component_quarantined", r1.text[:200]
        assert r1.json()["component"] == "nexus", r1.text[:200]
        r2 = client.post("/sovereign/command", json={})
        assert r2.status_code == 503, (
            f"مسار أوامر السيادي يجب أن يُرفض والمكوّن معزول — أعيد {r2.status_code}"
        )
        assert r2.json()["error"] == "component_quarantined", r2.text[:200]
        # بقية التطبيق: مسارات غير مكوّنية ومكونات غير معزولة
        assert client.get("/health").status_code == 200
        r3 = client.get("/components/memory")
        assert r3.status_code == 200, "المكونات غير المعزولة تستمر"


def test_feature_route_map_has_no_stale_entries():
    """حارس خريطة مسارات المكونات: كل مسار في الخريطة مسجل فعلًا في
    التطبيق (لا بقايا مسارات محذوفة تحجب بلا هدف)."""
    from backend.circuit_breaker import _COMPONENT_PATH_MAP
    registered = {getattr(r, "path", None) for r in app.routes}
    for path in _COMPONENT_PATH_MAP:
        assert path in registered, f"مسار في خريطة المدخل غير مسجل: {path}"


# ---------- R-689 (اعتراض المراجع ج2): الكاش الدافئ والاختفاء والاستدعاء الداخلي ----------

def test_warm_cache_consults_fallback():
    """اعتراض المراجع: كاش دافئ + إلحاق فشل توثيقه (ذهب للاحتياط) — الطلب
    اللاحق يجب ألا يُخدم من الكاش القديم بلا استشارة الاحتياط (بصمة الكاش
    تشمل نسخة الاحتياط)."""
    import stat as stat_mod
    log = quarantine_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    # ١) سجل مقروء + طلب — تسخين الكاش (بلا عزل: الكاش فارغ)
    with TestClient(app) as client:
        assert client.get("/components/predictive").status_code == 200
    # ٢) منع الإلحاق ثم عزل يفشل توثيقه → الاحتياط
    log.chmod(0o444)
    try:
        ok = append_entry("quarantine", "عزل بعد التسخين", component="predictive")
        assert ok is False, "يجب أن يفشل التوثيق هنا (الملف للقراءة فقط)"
        # ٣) الطلب مجددًا — الكاش الدافئ يجب ألا يحجب رؤية الاحتياط
        with TestClient(app) as client:
            r = client.get("/components/predictive")
            assert r.status_code == 503, (
                f"الكاش الدافئ خدم الحالة القديمة وتجاهل الاحتياط — سماح "
                f"صامت. أعيد {r.status_code}"
            )
            assert r.json()["error"] == "component_quarantined", r1_json(r)
    finally:
        log.chmod(0o644)
        from backend.loyalty_log import clear_fallback
        clear_fallback(log)


def r1_json(r):
    return r.text[:200]


def test_log_deletion_keeps_proven_quarantine():
    """اعتراض المراجع: اختفاء السجل بعد قراءة عزل مثبت — لا يُستبدل بحالة
    فارغة (سجل append-only لا يختفي مشروعًا؛ الحالة المثبتة تُحفظ وتحذير
    يُسجل، والحذف المقصود مسار الترميم الرسمي: سطر رفع)."""
    assert append_entry("quarantine", "عزل مثبت", component="quantum") is True
    with TestClient(app) as client:
        assert client.get("/components/quantum").status_code == 503  # إثبات + تسخين
        log = quarantine_log_path()
        original = log.read_text(encoding="utf-8")
        log.unlink()  # اختفاء السجل بعد الإثبات
        try:
            r = client.get("/components/quantum")
            assert r.status_code == 503, (
                f"اختفاء السجل أسقط عزلًا مثبتًا — سماح صامت. أعيد {r.status_code}"
            )
        finally:
            log.write_text(original, encoding="utf-8")  # استعادة للاختبارات اللاحقة


def test_quarantined_component_not_invoked_inside_cycle():
    """اعتراض المراجع (حد التنفيذ الداخلي): /chat يستدعي orchestrator.run_cycle
    فعليًا والدورة تستدعي مكونات حية — عزل المكوّن يجب أن يمنع استدعاءه داخل
    الدورة بينما تستمر بقية المكونات (تخطٍّ موثق في نتيجة الدورة).
    R-690 (تصويب المراجع): عدّادات للتنبؤ والوعي والذاكرة معًا + نجاح الدورة
    صراحةً — الادعاء كله مُثبت لا مفترض."""
    assert append_entry("quarantine", "عزل التنبؤ", component="predictive") is True
    with TestClient(app) as client:
        orch = app.state.orchestrator
        assert orch is not None
        pred_calls = {"n": 0}
        cons_calls = {"n": 0}
        mem_calls = {"n": 0}
        pred_engine = orch.predictive.get("engine")
        cons_field = orch.consciousness.get("field")
        mem_core = orch.memory_core
        assert pred_engine is not None and cons_field is not None, (
            "المنسق بلا مكونات — الاختبار لا يختبر شيئًا"
        )
        orig_pred = pred_engine.compute_future_map
        orig_cons = cons_field.get_consciousness_status
        orig_mem = mem_core.append_event

        def rec_pred(*a, **k):
            pred_calls["n"] += 1
            return orig_pred(*a, **k)

        def rec_cons(*a, **k):
            cons_calls["n"] += 1
            return orig_cons(*a, **k)

        def rec_mem(*a, **k):
            mem_calls["n"] += 1
            return orig_mem(*a, **k)

        pred_engine.compute_future_map = rec_pred
        cons_field.get_consciousness_status = rec_cons
        mem_core.append_event = rec_mem
        try:
            result = orch.run_cycle({"type": "chat", "text": "اختبار عزل"})
            # المكوّن المعزول لم يُستدع إطلاقًا
            assert pred_calls["n"] == 0, (
                f"التنبؤ المعزول استُدعي {pred_calls['n']} مرة داخل الدورة — "
                "المنع عند حد التنفيذ مفقود"
            )
            # بقية المكونات استمرت فعلًا (وعي + ذاكرة)
            assert cons_calls["n"] > 0, "الوعي لم يُستدع — الدورة لم تعمل"
            assert mem_calls["n"] > 0, "الذاكرة لم تُستدع — الدورة لم تعمل"
            # الدورة نفسها أكملت بنجاح صراحةً (لا مجرد نتيجة غير معدومة)
            assert result is not None and result.success is True, (
                f"الدورة لم تكتمل بنجاح — success={getattr(result, 'success', '?')}"
            )
        finally:
            pred_engine.compute_future_map = orig_pred
            cons_field.get_consciousness_status = orig_cons
            mem_core.append_event = orig_mem


# ---------- R-690 (اعتراض المراجع ج3): الرفع الفاشل + الاحتياط والعزل المثبت ----------

def test_failed_release_does_not_open_gate():
    """اعتراض المراجع ج3: رفعٌ فاشل التوثيق (ذهب للاحتياط) يجب ألا يفتح
    التوجيه — العزل المثبت على القرص يبقى محجوبًا (الرفع غير الموثق غير
    منفذ — اتجاه آمن)."""
    # ١) عزل موثق على القرص
    assert append_entry("quarantine", "عزل مثبت", component="predictive") is True
    log = quarantine_log_path()
    with TestClient(app) as client:
        assert client.get("/components/predictive").status_code == 503
        log.chmod(0o444)  # منع الكتابة — الرفع سيفتش توثيقه ويذهب للاحتياط
        try:
            # ٢) رفع يفشل توثيقه (يذهب للاحتياط — لا يفتح شيئًا)
            ok = append_entry("release", "رفع فاشل التوثيق", component="predictive")
            assert ok is False, "التوثيق يجب أن يفشل هنا (الملف للقراءة فقط)"
            # ٣) الطلب مجددًا — يجب أن يبقى محجوبًا
            r = client.get("/components/predictive")
            assert r.status_code == 503, (
                f"رفع فاشل التوثيق فتح التوجيع — ممنوع. أعيد {r.status_code}"
            )
            assert r.json()["error"] == "component_quarantined", r.text[:200]
        finally:
            log.chmod(0o644)
            from backend.loyalty_log import clear_fallback
            clear_fallback(log)


def test_unreadable_log_with_fallback_keeps_proven():
    """اعتراض المراجع ج3: وجود احتياط لمكوّن لا يُسقط عزلًا مثبتًا على القرص —
    سجل موجود غير مقروء = حالة غير قابلة للإثبات = إغلاق بخطأ محدد، مهما
    كان في الاحتياط."""
    # ١) إثبات عزل quantum على القرص + تسخين
    assert append_entry("quarantine", "عزل مثبت", component="quantum") is True
    with TestClient(app) as client:
        assert client.get("/components/quantum").status_code == 503
        log = quarantine_log_path()
        log.chmod(0o444)  # منع الكتابة (الإلحاق سيفشل → الاحتياط)
        try:
            ok = append_entry("quarantine", "عزل فاشل التوثيق", component="predictive")
            assert ok is False, "الإلحاق يجب أن يفشل هنا"
            log.chmod(0o000)  # منع القراءة أيضًا — الحالة غير قابلة للإثبات
            try:
                r = client.get("/components/quantum")
                assert r.status_code == 503, (
                    f"الاحتياط أسقط عزلًا مثبتًا على القرص — ممنوع. "
                    f"أعيد {r.status_code}"
                )
                assert r.json()["error"] == "quarantine_log_unreadable", r.text[:200]
            finally:
                log.chmod(0o644)
        finally:
            from backend.loyalty_log import clear_fallback
            clear_fallback(log)


def test_cycle_keeps_known_quarantine_on_read_failure():
    """اعتراض المراجع ج3: فشل قراءة السجل لا يُسقط عزلًا معروفًا داخل الدورة —
    آخر حالة معروفة تبقى مفروضة، والبقية تعمل، والدورة تكتمل."""
    assert append_entry("quarantine", "عزل التنبؤ", component="predictive") is True
    log = quarantine_log_path()
    with TestClient(app) as client:
        orch = app.state.orchestrator
        pred_calls = {"n": 0}
        cons_calls = {"n": 0}
        pred_engine = orch.predictive.get("engine")
        cons_field = orch.consciousness.get("field")
        orig_pred = pred_engine.compute_future_map
        orig_cons = cons_field.get_consciousness_status

        def rec_pred(*a, **k):
            pred_calls["n"] += 1
            return orig_pred(*a, **k)

        def rec_cons(*a, **k):
            cons_calls["n"] += 1
            return orig_cons(*a, **k)

        pred_engine.compute_future_map = rec_pred
        cons_field.get_consciousness_status = rec_cons
        try:
            # دورة أولى: العزل مفروض (قراءة ناجحة)
            r1 = orch.run_cycle({"type": "chat", "text": "دورة أولى"})
            assert pred_calls["n"] == 0 and cons_calls["n"] > 0
            # عطّل قراءة السجل — آخر حالة معروفة يجب أن تبقى مفروضة
            log.chmod(0o000)
            try:
                r2 = orch.run_cycle({"type": "chat", "text": "دورة ثانية"})
                assert pred_calls["n"] == 0, (
                    f"فشل القراءة أسقط عزلًا معروفًا — استُدعي "
                    f"{pred_calls['n']} مرة"
                )
                assert cons_calls["n"] > 0, "بقية المكونات توقفت"
                assert r2.success is True, "الدورة يجب أن تكتمل"
            finally:
                log.chmod(0o644)
        finally:
            pred_engine.compute_future_map = orig_pred
            cons_field.get_consciousness_status = orig_cons


def test_sovereign_quarantine_blocks_cycle_sovereign_layer():
    """اعتراض المراجع ج3 (تتبع self.sovereign): المتحكم السيادي يُستدعى فعلًا
    داخل الدورة (controller_cycle في _make_decision وget_controller_status في
    _evaluate_sovereign) — عزل «sovereign» يجب أن يمنع استدعاءه والبقية
    تعمل والدورة تكتمل."""
    assert append_entry("quarantine", "عزل السيادي", component="sovereign") is True
    with TestClient(app) as client:
        orch = app.state.orchestrator
        controller = (orch.sovereign or {}).get("controller")
        assert controller is not None, "بلا متحكم سيادي — الاختبار لا يختبر شيئًا"
        calls = {"n": 0}
        orig = controller.controller_cycle

        def rec(*a, **k):
            calls["n"] += 1
            return orig(*a, **k)

        controller.controller_cycle = rec
        try:
            result = orch.run_cycle({"type": "chat", "text": "اختبار السيادي"})
            assert calls["n"] == 0, (
                f"المتحكم السيادي المعزول استُدعي {calls['n']} مرة داخل الدورة"
            )
            assert result.success is True, "الدورة يجب أن تكتمل"
        finally:
            controller.controller_cycle = orig
