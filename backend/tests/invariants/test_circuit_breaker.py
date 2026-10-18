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


# ---------- R-691 (اعتراض المراجع ج4): طبقة التقييم + الرفع الموثق + الفشل البارد ----------

def test_sovereign_quarantine_blocks_evaluation_layer():
    """اعتراض المراجع ج4: الحارس السالب «if not self.sovereign:» في
    _evaluate_sovereign لم يكن يشمل العزل — عزل السيادي يجب أن يعيد طبقة
    التقييم بالمسار الافتراضي (no_sovereign_layer: لا استدعاء لـwill/
    alignment/directives/controller من مرحلتي التقييم والقرار) والدورة
    تكتمل. ملاحظة معايير: كائنات الطبقات مشتركة — مكونات أخرى قد تستدعيها
    داخليًا (يُمنع ذلك عند عزل تلك المكونات بحواجزها)؛ هذا الاختبار يثبت
    مرحلتي التقييم والقرار تحديدًا كما طلبه المراجع."""
    assert append_entry("quarantine", "عزل السيادي", component="sovereign") is True
    with TestClient(app) as client:
        orch = app.state.orchestrator
        controller = (orch.sovereign or {}).get("controller")
        cc_calls = {"n": 0}
        assert controller is not None and hasattr(controller, "controller_cycle"), (
            "بلا متحكم سيادي — الاختبار لا يختبر شيئًا"
        )
        orig_cc = controller.controller_cycle

        def rec_cc(*a, **k):
            cc_calls["n"] += 1
            return orig_cc(*a, **k)

        controller.controller_cycle = rec_cc
        try:
            result = orch.run_cycle({"type": "chat", "text": "اختبار طبقة التقييم"})
            # مرحلة التقييم: الحارس السالب أشمل العزل — عاد بالمسار الافتراضي
            eval_result = result.sovereign_eval
            assert eval_result.get("decision", {}).get("reason") == (
                "no_sovereign_layer"
            ), f"طبقة التقييم لم تُغلق بالعزل: {eval_result}"
            # مرحلة القرار: المتحكم السيادي لم يُستدع من المنسق
            assert cc_calls["n"] == 0, (
                f"المتحكم السيادي استُدعي من مرحلة القرار {cc_calls['n']} مرة"
            )
            assert result.success is True, "الدورة يجب أن تكتمل"
        finally:
            controller.controller_cycle = orig_cc


def test_documented_release_clears_fallback_quarantine():
    """اعتراض المراجع ج4: الرفع الموثق اللاحق يجب أن ينهي عزلًا سابقًا فشل
    توثيقه (دون clear_fallback — ترتيب الأحداث الفعالة يحسم)."""
    log = quarantine_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.touch(exist_ok=True)  # الملف موجود قبل الحجب (chmod على ملف موجود)
    log.chmod(0o444)  # القناة معطوبة: العزل يفشل توثيقه → الاحتياط
    try:
        ok = append_entry("quarantine", "عزل فاشل التوثيق", component="predictive")
        assert ok is False, "التوثيق يجب أن يفشل هنا"
    finally:
        log.chmod(0o644)  # القناة أُصلحت
    # رفع مأذون ينجح توثيقه (القناة سليمة) — لا clear_fallback في هذا الاختبار
    ok_release = append_entry("release", "رفع موثق بعد إصلاح القناة", component="predictive")
    assert ok_release is True, "التوثيق يجب أن ينجح هنا"
    with TestClient(app) as client:
        r = client.get("/components/predictive")
        assert r.status_code == 200, (
            f"الرفع الموثق لم ينهِ عزل الاحتياط السابق — أعيد {r.status_code}: "
            f"{r.text[:200]}"
        )


def test_cold_read_failure_is_not_internal_allow():
    """اعتراض المراجع ج4: فشل القراءة البارد (قبل أول قراءة ناجحة) لا يجوز أن
    يتحول إذنًا داخليًا — الحالة المجهولة تمنع استدعاء المكونات في الدورة
    (لا موت ولا إسقاط)، مع سجل يحتوي عزلًا موثقًا."""
    assert append_entry("quarantine", "عزل التنبؤ", component="predictive") is True
    log = quarantine_log_path()
    with TestClient(app) as client:
        orch = app.state.orchestrator
        # محاكاة منسق بارد: لم تُثبت أي حالة بعد (لا قراءة ناجحة سابقة)
        orch._quarantine_proven = False
        orch._quarantine_last_known = frozenset()
        orch._quarantine_cache = None
        orch._quarantine_dirty = True
        pred_calls = {"n": 0}
        pred_engine = orch.predictive.get("engine")
        orig = pred_engine.compute_future_map

        def rec(*a, **k):
            pred_calls["n"] += 1
            return orig(*a, **k)

        pred_engine.compute_future_map = rec
        try:
            log.chmod(0o000)  # تعطيل القراءة قبل أول دورة
            try:
                result = orch.run_cycle({"type": "chat", "text": "فشل بارد"})
                assert pred_calls["n"] == 0, (
                    f"الحالة المجهولة تحولت إذنًا — استُدعي التنبؤ "
                    f"{pred_calls['n']} مرة"
                )
                assert result.success is True, "الدورة يجب أن تكتمل"
            finally:
                log.chmod(0o644)
        finally:
            pred_engine.compute_future_map = orig


def test_file_deletion_after_proven_keeps_orchestrator_quarantine():
    """اعتراض المراجع ج4: اختفاء الملف بعد إثبات العزل داخل المنسق — الغياب
    لا يُقرأ فراغًا (تعذر إثبات، لا لا-عزل): آخر حالة معروفة تبقى مفروضة."""
    assert append_entry("quarantine", "عزل التنبؤ", component="predictive") is True
    log = quarantine_log_path()
    with TestClient(app) as client:
        orch = app.state.orchestrator
        pred_calls = {"n": 0}
        pred_engine = orch.predictive.get("engine")
        orig = pred_engine.compute_future_map

        def rec(*a, **k):
            pred_calls["n"] += 1
            return orig(*a, **k)

        pred_engine.compute_future_map = rec
        try:
            # دورة أولى: القراءة ناجحة — العزل مثبت داخل المنسق
            r1 = orch.run_cycle({"type": "chat", "text": "دورة الإثبات"})
            assert pred_calls["n"] == 0
            # حذف الملف (غياب = تعذر إثبات، لا فراغ)
            log.unlink()
            try:
                r2 = orch.run_cycle({"type": "chat", "text": "دورة بعد الحذف"})
                assert pred_calls["n"] == 0, (
                    f"اختفاء الملف أسقط عزلًا مثبتًا داخل المنسق — استُدعي "
                    f"{pred_calls['n']} مرة"
                )
                assert r2.success is True, "الدورة يجب أن تكتمل"
            finally:
                # استعادة السجل للاختبارات اللاحقة (المحتوى الأصلي محفوظ في الـfixture)
                log.parent.mkdir(parents=True, exist_ok=True)
                log.write_text("", encoding="utf-8")
        finally:
            pred_engine.compute_future_map = orig


# ---------- R-692 (اعتراضات المراجع ج5): الاستدعاء غير المباشر + البدء الابتدائي ----------

def test_sovereign_quarantine_blocks_all_layer_invocations():
    """اعتراضا المراجع ج5 وج6: الاستدعاء غير المباشر — طبقات السيادي تُستدعى
    داخل مكونات أخرى (المكدس أثبت المسارات). عزل sovereign وحده عبر طلب
    /chat فعلي (لا run_cycle مباشرًا): يجب ألا تُنفذ دوال الطبقات من أي
    مستدعٍ (الدورة وبناء الرد والعمل الخلفي)، مع استمرار المكونات غير
    المعزولة في وظائفها المستقلة. عدّاد التنفيذ يُلف بين الحاجز والأصل
    (عدّ حقيقي لا محاولات)، وضابط مسموح: الرفع الموثق يعيد التنفيذ — وإلا
    فالعزل تعطيل دائم لا حجب."""
    assert append_entry("quarantine", "عزل السيادي", component="sovereign") is True
    with TestClient(app) as client:
        orch = app.state.orchestrator
        refs = orch.sovereign or {}
        assert refs, "بلا طبقات سيادية — الاختبار لا يختبر شيئًا"
        # عدّاد التنفيذ الفعلي: يُلف بين الحاجز والأصل المحفوظ (gated._orig)
        # — الاستدعاء الناجح يمر بالعدّاد، والمحجوب لا يصل إليه أبدًا
        layer_counter = {"n": 0}
        wrapped = []
        for key in ("will", "alignment", "directives", "controller"):
            layer = refs.get(key)
            if layer is None:
                continue
            for name in dir(layer):
                if name.startswith("_"):
                    continue
                gate = getattr(layer, name, None)
                if gate is None or not callable(gate) or isinstance(gate, type):
                    continue
                if not hasattr(gate, "_component_gate") or not hasattr(gate, "_orig"):
                    continue
                orig = gate._orig

                def counting(*a, _orig=orig, **k):
                    layer_counter["n"] += 1
                    return _orig(*a, **k)

                gate._orig = counting
                wrapped.append((gate, orig))
        assert wrapped, "لا حواجز قابلة للف — الاختبار لا يختبر شيئًا"
        # عدّادات المكونات المستقلة (بين الحاجز والأصل — نفس الآلية)
        pred_engine = orch.predictive.get("engine")
        cons_field = orch.consciousness.get("field")
        pred_counter = {"n": 0}
        cons_counter = {"n": 0}
        for obj, method, counter in (
            (pred_engine, "compute_future_map", pred_counter),
            (cons_field, "get_consciousness_status", cons_counter),
        ):
            gate = getattr(obj, method, None)
            assert gate is not None and hasattr(gate, "_orig"), (
                f"حاجز {method} غير موجود — الاختبار لا يختبر شيئًا"
            )
            orig = gate._orig

            def counting(*a, _orig=orig, _c=counter, **k):
                _c["n"] += 1
                return _orig(*a, **k)

            gate._orig = counting
            wrapped.append((gate, orig))
        try:
            # ١) المعزول: أول طلب /chat فعلي — الدورة + بناء الرد + العمل الخلفي
            r1 = client.post("/chat", json={"text": "اختبار الاستدعاء غير المباشر"})
            assert r1.status_code == 200, f"المحادثة يجب أن تنجح — أعيد {r1.status_code}"
            assert layer_counter["n"] == 0, (
                f"دوال طبقات السيادي المعزول نُفذت {layer_counter['n']} مرة عبر "
                "مسارات غير مباشرة (الدورة/الرد/الخلفي) — الحاجز عند المرجع مفقود"
            )
            # استمرار المكونات غير المعزولة في وظائفها المستقلة
            assert pred_counter["n"] > 0, (
                "التنبؤ غير المعزول لم يُنفذ — المكون المستقل توقف كليًا"
            )
            assert cons_counter["n"] > 0, "الوعي غير المعزول لم يُنفذ"
            # ٢) ضابط مسموح: الرفع الموثق يعيد التنفيذ (وإلا فالحجب تعطيل دائم)
            assert append_entry(
                "release", "رفع موثق يعيد التنفيذ", component="sovereign"
            ) is True
            r2 = client.post("/chat", json={"text": "اختبار الرفع الموثق"})
            assert r2.status_code == 200, f"المحادثة بعد الرفع — أعيد {r2.status_code}"
            assert layer_counter["n"] > 0, (
                "الرفع الموثق لم يعد تنفيذ طبقات السيادي — العزل تحول تعطيلًا "
                "دائمًا (العدّاد نفسه لم يسجل أي تنفيذ مسموح — الاختبار غير صالح)"
            )
        finally:
            # استعادة الأصل: فك العدّاد (الحاجز يبقى كما ركبه التطبيق)
            for gate, orig in wrapped:
                gate._orig = orig


def _run_chat_first_request_scenario(body: str, data_root):
    """سيناريو أول طلب /chat فعلي في عملية جديدة معزولة البيئة — لا طلبات
    تمهيدية (لا /health ولا /components) حتى لا ينشئ فحص القناة السجل ويخفي
    مسار البدء (تنبيه المراجع ج5)."""
    import json
    import os
    import subprocess
    indented = "\n".join("    " + line for line in body.strip().splitlines())
    script = (
        "import sys, json, os\n"
        f"sys.path.insert(0, {str(_REPO_ROOT)!r})\n"
        f"sys.path.insert(0, {str(_BACKEND_DIR)!r})\n"
        "os.environ['SOVEREIGN_DISABLE_BACKGROUND_THREADS'] = '1'\n"
        "from fastapi.testclient import TestClient\n"
        "from app import app\n"
        "_R = {}\n"
        "try:\n" + indented + "\n"
        "except Exception as e:\n"
        "    _R['unexpected_error'] = f'{type(e).__name__}: {e}'\n"
        "print('SCENARIO_JSON:' + json.dumps(_R))\n"
    )
    compile(script, "<chat_scenario>", "exec")
    env = dict(os.environ)
    env["SOVEREIGN_DATA_ROOT"] = str(data_root)
    result = subprocess.run(
        [sys.executable, "-u", "-c", script],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), timeout=120, env=env,
    )
    payload = None
    for line in result.stdout.splitlines():
        if line.startswith("SCENARIO_JSON:"):
            payload = json.loads(line[len("SCENARIO_JSON:"):])
    return result.returncode, payload, result.stderr


def _chat_counters_body(prepare: str) -> str:
    """جسم سيناريو مشترك: عدّادات ملفوفة ثم أول طلب POST /chat فقط."""
    return """
from app import app as _app
with TestClient(_app) as c:
    orch = _app.state.orchestrator
    _R['log_exists_before'] = __import__('backend.loyalty_log', fromlist=['x']).quarantine_log_path().exists()
""" + prepare + """
    pred = orch.predictive.get('engine')
    cons = orch.consciousness.get('field')
    counters = {'pred': 0, 'cons': 0}
    _orig_pred = pred.compute_future_map
    _orig_cons = cons.get_consciousness_status
    def rp(*a, **k):
        counters['pred'] += 1
        return _orig_pred(*a, **k)
    def rc(*a, **k):
        counters['cons'] += 1
        return _orig_cons(*a, **k)
    pred.compute_future_map = rp
    cons.get_consciousness_status = rc
    r = c.post('/chat', json={'text': 'أول طلب محادثة'})
    _R['status'] = r.status_code
    _R['pred'] = counters['pred']
    _R['cons'] = counters['cons']
"""


def test_first_chat_fresh_root_components_run(tmp_path):
    """اعتراض المراجع ج5: غياب السجل الابتدائي ليس اختفاء سجل مثبت — جذر
    جديد قابل للكتابة بلا سجل: أول طلب /chat فعلي يجب أن يشغّل المكونات
    الطبيعية فعليًا (تنفيذ مثبت بعدّادات، لا مجرد نجاح الدورة)."""
    rc, payload, err = _run_chat_first_request_scenario(
        _chat_counters_body(""), tmp_path,
    )
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["log_exists_before"] is False, "السيناريو لم يبدأ بلا سجل"
    assert payload["status"] == 200, f"المحادثة يجب أن تنجح — أعيد {payload['status']}"
    assert payload["pred"] > 0, (
        f"التنبؤ لم يُنفذ في جذر بلا سجل ({payload['pred']}) — البدء الابتدائي "
        "عُامل كحالة مجهولة تمنع التنفيذ"
    )
    assert payload["cons"] > 0, "الوعي لم يُنفذ — البدء الابتدائي ممنوع"


def test_first_chat_unreadable_cold_blocks(tmp_path):
    """اعتراض المراجع ج5: سجل موجود غير مقروء قبل أول دورة (بارد) — الحالة
    المجهولة لا تتحول إذنًا: المكون المعزول موثقًا لا يُستدع عبر أول طلب
    /chat فعلي، والدورة تكتمل (التطبيق حي)."""
    body = _chat_counters_body(
        """
    from backend.loyalty_log import append_entry, quarantine_log_path
    assert append_entry('quarantine', 'عزل التنبؤ', component='predictive') is True
    quarantine_log_path().chmod(0o000)
"""
    )
    rc, payload, err = _run_chat_first_request_scenario(body, tmp_path)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["status"] == 200, f"التطبيق يجب أن يبقى حيًا — أعيد {payload['status']}"
    # الحالة المجهولة إغلاق كامل (اتجاه آمن): لا إذن لأي مكوّن من الجهل —
    # التطبيق حي والدورة تكتمل بمنطق المنسق الذاتي. المطلوب حرفيًا: المعزول
    # الموثق لا يُستدع (لا يتحول الجهل إذنًا)
    assert payload["pred"] == 0, (
        f"الحالة المجهولة تحولت إذنًا عبر أول طلب — استُدعي التنبؤ "
        f"{payload['pred']} مرة"
    )
    assert payload["cons"] == 0, (
        f"الجهل منح إذنًا للوعي أيضًا ({payload['cons']}) — الإغلاق الكامل "
        "هو الاتجاه الآمن الموثق"
    )


def test_first_chat_deletion_after_proven_keeps(tmp_path):
    """اعتراض المراجع ج5: سجل اختفى بعد إثبات العزل — العزل المعروف لا
    يُسقط عبر أول طلب /chat فعلي في عملية جديدة (غياب بعد إثبات ≠ بدء)."""
    body = """
from app import app as _app
from fastapi.testclient import TestClient
from backend.loyalty_log import append_entry, quarantine_log_path
with TestClient(_app) as c:
    orch = _app.state.orchestrator
    pred = orch.predictive.get('engine')
    counters = {'pred': 0}
    _orig = pred.compute_future_map
    def rp(*a, **k):
        counters['pred'] += 1
        return _orig(*a, **k)
    pred.compute_future_map = rp
    # ١) توثيق العزل ثم أول طلب (يثبت الحالة داخل المنسق — التنبؤ محجوب)
    assert append_entry('quarantine', 'عزل التنبؤ', component='predictive') is True
    r1 = c.post('/chat', json={'text': 'دورة الإثبات'})
    _R['status1'] = r1.status_code
    _R['pred1'] = counters['pred']
    # ٢) حذف السجل (غياب بعد إثبات) ثم طلب ثانٍ
    quarantine_log_path().unlink()
    r2 = c.post('/chat', json={'text': 'دورة بعد الحذف'})
    _R['status2'] = r2.status_code
    _R['pred2_total'] = counters['pred']
    _R['cons2'] = counters.setdefault('cons', 0)
"""
    rc, payload, err = _run_chat_first_request_scenario(body, tmp_path)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["status1"] == 200 and payload["status2"] == 200, payload
    assert payload["pred1"] == 0, "العزل الموثق لم يحجب التنبؤ في الدورة الأولى"
    assert payload["pred2_total"] == 0, (
        f"حذف السجل أسقط العزل المثبت — استُدعي التنبؤ {payload['pred2_total']} مرة"
    )


# ---------- R-693 (اعتراضات المراجع ج6): معرفة الاحتياط والاختفاء بعد رصد ----------

def test_first_chat_fallback_quarantine_blocks(tmp_path):
    """اعتراض المراجع ج6: عزل فشل توثيقه بلا ملف (الحدث في احتياط العملية) —
    إصلاح صلاحيات القناة دون تفريغ الاحتياط ودون رفع موثق: أول /chat لا
    ينفذ المعزول (غياب الملف لا يلغي المعرفة المحلية — ليس بدءًا نظيفًا)."""
    body = """
from app import app as _app
from fastapi.testclient import TestClient
from backend.loyalty_log import append_entry, quarantine_log_path
import os
log = quarantine_log_path()
log.parent.mkdir(parents=True, exist_ok=True)
os.chmod(log.parent, 0o500)  # منع إنشاء السجل — التوثيق سيفشل
_R['q'] = append_entry('quarantine', 'عزل فاشل التوثيق', component='predictive')
os.chmod(log.parent, 0o700)  # إصلاح القناة — بلا تفريغ احتياط ولا رفع موثق
_R['file_exists'] = log.exists()
from backend.loyalty_log import fallback_quarantined
_R['fallback_has_predictive'] = 'predictive' in fallback_quarantined()
with TestClient(_app) as c:
    orch = _app.state.orchestrator
    pred = orch.predictive.get('engine')
    cons = orch.consciousness.get('field')
    counters = {'pred': 0, 'cons': 0}
    _orig_pred = pred.compute_future_map
    _orig_cons = cons.get_consciousness_status
    def rp(*a, **k):
        counters['pred'] += 1
        return _orig_pred(*a, **k)
    def rc(*a, **k):
        counters['cons'] += 1
        return _orig_cons(*a, **k)
    pred.compute_future_map = rp
    cons.get_consciousness_status = rc
    r = c.post('/chat', json={'text': 'أول طلب بعد إصلاح القناة'})
    _R['status'] = r.status_code
    _R['pred'] = counters['pred']
    _R['cons'] = counters['cons']
"""
    rc, payload, err = _run_chat_first_request_scenario(body, tmp_path)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["q"] is False, "التوثيق يجب أن يفشل (القناة ممنوعة الكتابة)"
    assert payload["file_exists"] is False, "الملف يجب ألا يوجد — لا رفع موثق ولا توثيق ناجح"
    # إثبات صريح: الحدث موجود في احتياط العملية (كما طلب المراجع)
    assert payload["fallback_has_predictive"] is True, (
        "العزل الفاشل التوثيق غير موجود في الاحتياط — الاختبار لا يختبر شيئًا"
    )
    assert payload["status"] == 200, f"التطبيق يجب أن يبقى حيًا — أعيد {payload['status']}"
    assert payload["pred"] == 0, (
        f"غياب الملف ألغى المعرفة المحلية بالعزل — استُدعي التنبؤ "
        f"{payload['pred']} مرة عبر أول طلب"
    )
    assert payload["cons"] > 0, "المكونات غير المعزولة يجب أن تستمر"


def test_first_chat_unreadable_then_deleted_stays_blocked(tmp_path):
    """اعتراض المراجع ج6: سجل غير مقروء (يُرصد وجوده — مجهول، منع) ثم اختفى —
    اختفاء الدليل ليس تصريحًا بالبدء المشروع: المنع يبقى عبر الطلبين."""
    body = """
from app import app as _app
from fastapi.testclient import TestClient
from backend.loyalty_log import append_entry, quarantine_log_path
with TestClient(_app) as c:
    orch = _app.state.orchestrator
    pred = orch.predictive.get('engine')
    counters = {'pred': 0}
    _orig = pred.compute_future_map
    def rp(*a, **k):
        counters['pred'] += 1
        return _orig(*a, **k)
    pred.compute_future_map = rp
    assert append_entry('quarantine', 'عزل التنبؤ', component='predictive') is True
    log = quarantine_log_path()
    log.chmod(0o000)  # موجود غير مقروء — يُرصد وجوده ثم يمنع (مجهول)
    r1 = c.post('/chat', json={'text': 'طلب المجهول'})
    _R['status1'] = r1.status_code
    _R['pred1'] = counters['pred']
    log.unlink()  # اختفاء الدليل بعد رصده
    r2 = c.post('/chat', json={'text': 'طلب بعد الاختفاء'})
    _R['status2'] = r2.status_code
    _R['pred2_total'] = counters['pred']
"""
    rc, payload, err = _run_chat_first_request_scenario(body, tmp_path)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["status1"] == 200 and payload["status2"] == 200, payload
    assert payload["pred1"] == 0, "الحالة المجهولة (غير مقروء) يجب أن تمنع"
    assert payload["pred2_total"] == 0, (
        f"اختفاء السجل بعد رصده صار بدءًا مشروعًا — استُدعي التنبؤ "
        f"{payload['pred2_total']} مرة"
    )


# ---------- R-693 (اعتراض المراجع ج7): حفظ المعرفة الجديدة في مسارات تعذر الإثبات ----------

_OVERLAP_SEQUENCE = """
from app import app as _app
from fastapi.testclient import TestClient
from backend.loyalty_log import append_entry, quarantine_log_path, fallback_quarantined
with TestClient(_app) as c:
    orch = _app.state.orchestrator
    pred = orch.predictive.get('engine')
    counters = {'pred': 0}
    # R-693 (ج8): العدّ بين الحاجز والأصل — تنفيذ فعلي لا محاولات
    _gate = pred.compute_future_map
    _orig = _gate._orig
    def rp(*a, **k):
        counters['pred'] += 1
        return _orig(*a, **k)
    _gate._orig = rp
    # ١) عزل quantum موثق + طلب يثبت الحالة داخل المنسق
    assert append_entry('quarantine', 'عزل quantum', component='quantum') is True
    r1 = c.post('/chat', json={'text': 'طلب الإثبات'})
    _R['status1'] = r1.status_code
    _R['pred1'] = counters['pred']
    _R['cache1'] = sorted(orch._quarantine_cache or [])
    # ٢) منع الكتابة + عزل predictive يفشل توثيقه (احتياط محلي جديد)
    log = quarantine_log_path()
    log.chmod(0o444)
    _R['q2'] = append_entry('quarantine', 'عزل فاشل التوثيق', component='predictive')
    _R['fallback'] = sorted(fallback_quarantined())
    # ٣) فقدان قابلية الإثبات دون قراءة ناجحة ودون رفع موثق
    __VARIANT__
    # ٤) الطلب مجددًا — المعرفة الجديدة يجب ألا تضيع
    r2 = c.post('/chat', json={'text': 'طلب بعد فقدان الإثبات'})
    _R['status2'] = r2.status_code
    _R['pred2_total'] = counters['pred']
    _R['cache2'] = sorted(orch._quarantine_cache or [])
"""


def _run_overlap_scenario(variant: str, tmp_path):
    body = _OVERLAP_SEQUENCE.replace("__VARIANT__", variant)
    rc, payload, err = _run_chat_first_request_scenario(body, tmp_path)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["q2"] is False, "التوثيق الثاني يجب أن يفشل (الكتابة ممنوعة)"
    assert "predictive" in payload["fallback"], (
        f"العزل الفاشل التوثيق غير موجود في الاحتياط: {payload['fallback']}"
    )
    assert payload["status1"] == 200 and payload["status2"] == 200, payload
    # ضابط موجب: التنبؤ حر في الطلب الأول (المعزول quantum فقط) — العدّاد
    # يسجل تنفيذًا فعليًا، وإلا فالاختبار غير صالح
    assert payload["pred1"] > 0, "التنبؤ الحر لم يُنفذ في الطلب الأول — العدّاد لا يقيس"
    # المعرفة الجديدة لا تضيع: لا تنفيذ جديد بعد العزل الفاشل التوثيق
    # (العدّاد تراكمي — المسموح كله من الطلب الأول قبل العزل)
    assert payload["pred2_total"] == payload["pred1"], (
        f"المعرفة المحلية الجديدة (predictive في الاحتياط) ضاعت في مسار "
        f"تعذر الإثبات — تنفيذات جديدة بعد العزل: "
        f"{payload['pred2_total'] - payload['pred1']}"
    )
    assert "predictive" in payload["cache2"], (
        f"predictive غائب عن الحالة بعد فقدان الإثبات: {payload['cache2']}"
    )
    assert "quantum" in payload["cache2"], (
        f"المعرفة المثبتة سابقًا (quantum) ضاعت: {payload['cache2']}"
    )


def test_disappearance_preserves_new_fallback_knowledge(tmp_path):
    """اعتراض المراجع ج7: حذف السجل بعد إثبات quantum وإضافة عزل predictive
    فاشل التوثيق — الاختفاء لا يُسقط المعرفة الجديدة (الاحتياط) ولا القديمة
    (آخر حالة معروفة): كلاهما يبقى محجوبًا عبر الطلب."""
    _run_overlap_scenario(
        "log.unlink()  # حذف السجل دون قراءة ناجحة أخرى", tmp_path,
    )


def test_unreadable_preserves_new_fallback_knowledge(tmp_path):
    """اعتراض المراجع ج7: نفس التداخل مع بقاء الملف غير مقروء (لا حذف) —
    معالجة OSError نفسها يجب ألا تستعيد اللقطة القديمة وحدها وتُهدر المعرفة
    المحلية الجديدة."""
    _run_overlap_scenario(
        "log.chmod(0o000)  # موجود غير مقروء", tmp_path,
    )


def test_read_window_release_not_reanimated(tmp_path):
    """اعتراض المراجع ج8: عزل يدخل الاحتياط داخل نافذة قراءة ناجحة ثم يُرفع
    توثيقيًا وتشمل القراءة الحدثين (الرفع يحسم العزل) — القراءة المتعذرة
    التالية لا تُحييه (علامة الأحداث المشمولة بالقراءة، لا توقيت بدايتها)."""
    body = """
from app import app as _app
from fastapi.testclient import TestClient
import time
import backend.loyalty_log as ll
with TestClient(_app) as c:
    orch = _app.state.orchestrator
    pred = orch.predictive.get('engine')
    counters = {'n': 0}
    _gate = pred.compute_future_map
    _orig = _gate._orig
    def counting(*a, **k):
        counters['n'] += 1
        return _orig(*a, **k)
    _gate._orig = counting
    # حدث تمهيدي ينشئ الملف (بلا قراءة) — ليصلك الحقن داخل نافذة القراءة
    assert ll.append_entry('quarantine', 'عزل تمهيدي', component='quantum') is True
    # حقن حتمي قبل حساب الحالة (عزل إلى الاحتياط + رفع موثق — القراءة الناجحة
    # ستشمل الحدثين والرفع يحسم العزل) + تعطيل القراءة فورًا بعد الحالة
    # المستهدفة — لا قراءة ناجحة أخرى (الدورة الخلفية تفشل قراءتها)
    _injected = {'done': False}
    def _wrap_state(fn):
        def wrapped(path=None):
            if not _injected['done']:
                _injected['done'] = True
                log = ll.quarantine_log_path()
                with ll._FALLBACK_LOCK:
                    ll._FALLBACK.setdefault(str(log), []).append({
                        'time': time.time(), 'kind': 'quarantine',
                        'component': 'predictive',
                        'detail': 'حقن داخل نافذة القراءة'})
                ll.append_entry('release', 'رفع موثق داخل النافذة', component='predictive')
                result = fn(path)
                ll.quarantine_log_path().chmod(0o000)
                return result
            return fn(path)
        return wrapped
    if hasattr(ll, 'read_quarantine_state'):
        ll.read_quarantine_state = _wrap_state(ll.read_quarantine_state)
    ll.quarantined_components = _wrap_state(ll.quarantined_components)
    # ١) طلب يقرأ بنجاح — القراءة تشمل الحدثين: الرفع الموثق يحسم العزل
    r1 = c.post('/chat', json={'text': 'قراءة النافذة'})
    _R['status1'] = r1.status_code
    _R['pred1'] = counters['n']
    # ٢) لا إحياء للعزل المحسوم في القراءة الناجحة
    r2 = c.post('/chat', json={'text': 'قراءة متعذرة بعد الحسم'})
    _R['status2'] = r2.status_code
    _R['pred2_total'] = counters['n']
    _R['cache2'] = sorted(orch._quarantine_cache or [])
"""
    rc, payload, err = _run_chat_first_request_scenario(body, tmp_path)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["status1"] == 200 and payload["status2"] == 200, payload
    # ضابط موجب: القراءة الناجحة حسمت العزل بالرفع الموثق — التنبؤ حر ونُفذ
    assert payload["pred1"] > 0, (
        "القراءة الناجحة لم تحسم العزل بالرفع الموثق داخل النافذة — التنبؤ "
        "لم يُنفذ في الطلب الأول"
    )
    # لا إحياء: تنفيذ جديد في القراءة المتعذرة (الطلب الثاني كامل الدورة+الرد)
    assert payload["pred2_total"] > payload["pred1"], (
        f"القراءة المتعذرة أحيت عزلًا حسمته قراءة ناجحة (رفع موثق داخل "
        f"النافذة) — تنفيذات جديدة: "
        f"{payload['pred2_total'] - payload['pred1']}"
    )
    assert "predictive" not in payload["cache2"], (
        f"predictive عاد إلى الحالة بعد القراءة المتعذرة: {payload['cache2']}"
    )


def test_marker_boundary_new_knowledge_not_lost(tmp_path):
    """اعتراض المراجع ج9: العلامة ليست من القراءة نفسها — عزل فاشل التوثيق
    يُحقن **بعد حساب الحالة وقبل أخذ العلامة المنفصلة**: العلامة الحالية
    (لقطة مستقلة بعد الحالة) تعلّمه «مشمولًا» رغم أن الحالة لم تعالجه،
    فيضيع عند تعذر القراءة التالية. الإصلاح: الحالة والعلامة معًا من عملية
    واحدة (نسخة الاحتياط نفسها) — الحدث بعد النسخة يبقى غير مشمول.
    الحقن هنا بعد الحالة + تعطيل القراءة فورًا (لا قراءة ناجحة أخرى
    بعدها — الدورة الخلفية تفشل قراءتها)."""
    body = """
from app import app as _app
from fastapi.testclient import TestClient
import time
import backend.loyalty_log as ll
with TestClient(_app) as c:
    orch = _app.state.orchestrator
    pred = orch.predictive.get('engine')
    counters = {'n': 0}
    _gate = pred.compute_future_map
    _orig = _gate._orig
    def counting(*a, **k):
        counters['n'] += 1
        return _orig(*a, **k)
    _gate._orig = counting
    # حدث تمهيدي ينشئ الملف (بلا قراءة)
    assert ll.append_entry('quarantine', 'عزل تمهيدي', component='quantum') is True
    _injected = {'done': False}
    def _inject():
        with ll._FALLBACK_LOCK:
            ll._FALLBACK.setdefault(str(ll.quarantine_log_path()), []).append({
                'time': time.time(), 'kind': 'quarantine',
                'component': 'predictive',
                'detail': 'حقن بعد الحالة قبل العلامة'})
    # لف مسار الحالة (مهما كان اسمه في النسخة): الحقن بعد اكتمال الحساب
    def _wrap_state(fn):
        def wrapped(path=None):
            result = fn(path)
            if not _injected['done']:
                _injected['done'] = True
                _inject()
                # لا قراءة ناجحة أخرى بعد الحالة المستهدفة — التعطيل فورًا
                ll.quarantine_log_path().chmod(0o000)
            return result
        return wrapped
    if hasattr(ll, 'read_quarantine_state'):
        ll.read_quarantine_state = _wrap_state(ll.read_quarantine_state)
    ll.quarantined_components = _wrap_state(ll.quarantined_components)
    r1 = c.post('/chat', json={'text': 'قراءة الحالة'})
    _R['status1'] = r1.status_code
    _R['pred1'] = counters['n']
    from backend.loyalty_log import fallback_quarantined
    _R['fallback_has_predictive'] = 'predictive' in fallback_quarantined()
    # ٢) القراءة معطلة — المعرفة الجديدة يجب ألا تضيع
    r2 = c.post('/chat', json={'text': 'قراءة متعذرة'})
    _R['status2'] = r2.status_code
    _R['pred2_total'] = counters['n']
    _R['cache2'] = sorted(orch._quarantine_cache or [])
"""
    rc, payload, err = _run_chat_first_request_scenario(body, tmp_path)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    assert payload["status1"] == 200 and payload["status2"] == 200, payload
    # إثبات صريح: الحدث في الاحتياط
    assert payload["fallback_has_predictive"] is True, "الحقن لم يصل إلى الاحتياط"
    # ضابط موجب: الحالة المستهدفة لم تشمل الحدث — التنبؤ حر في الطلب الأول
    assert payload["pred1"] > 0, "التنبؤ لم يُنفذ في الطلب الأول — العدّاد لا يقيس"
    # المعرفة الجديدة لا تضيع: لا تنفيذ جديد بعد تعطل القراءة
    assert payload["pred2_total"] == payload["pred1"], (
        f"الحدث المحقون بعد الحالة عُلّم «مشمولًا» بلا معالجة — ضاع عند "
        f"تعذر القراءة: تنفيذات جديدة {payload['pred2_total'] - payload['pred1']}"
    )
    assert "predictive" in payload["cache2"], (
        f"predictive غائب عن الحالة بعد تعذر القراءة: {payload['cache2']}"
    )


# ---------- R-693 (اعتراض المراجع ج10): ترتيب المصدرين داخل العملية الواحدة ----------

def test_source_order_release_witnessed_not_reanimated(tmp_path):
    """اعتراض المراجع ج10: نسخة الاحتياط تُؤخذ قبل قراءة الملف — عزل فاشل
    التوثيق يدخل الاحتياط بين النسخة وقراءة الملف، ثم ينجح توثيق رفعه
    وتشمل قراءة الملف الرفع: الحالة صحيحة (غير معزول) لكن العلامة لا تشمل
    عزل الاحتياط — فعند تعذر القراءة التالي يُصنف «جديدًا» ويُعاد فرضه رغم
    أن القراءة الناجحة شاهدت رفعه. الإصلاح: أحداث الملف أولًا ثم نسخة
    الاحتياط — الحالة والعلامة من النسخة نفسها (عزل الاحتياط السابق لرفعٍ
    شملته قراءة الملف يقع في النسخة فيُحسم معه)."""
    body = """
from app import app as _app
from fastapi.testclient import TestClient
import backend.loyalty_log as ll
with TestClient(_app) as c:
    orch = _app.state.orchestrator
    pred = orch.predictive.get('engine')
    counters = {'n': 0}
    _gate = pred.compute_future_map
    _orig = _gate._orig
    def counting(*a, **k):
        counters['n'] += 1
        return _orig(*a, **k)
    _gate._orig = counting
    # حدث تمهيدي ينشئ الملف (بلا قراءة) — لتصل قراءة العملية إلى مسار الملف
    assert ll.append_entry('quarantine', 'عزل تمهيدي', component='quantum') is True
    _injected = {'done': False}
    _orig_re = ll.read_entries
    def re_injected(path):
        if not _injected['done']:
            _injected['done'] = True
            log = ll.quarantine_log_path()
            log.chmod(0o444)
            # فشل توثيق العزل (False + الاحتياط) — بين نسخة الاحتياط وقراءة الملف
            _R['q'] = ll.append_entry(
                'quarantine', 'عزل داخل نافذة المصدرين', component='predictive')
            log.chmod(0o644)
            # نجاح توثيق الرفع (True + الملف) — القراءة الفعلية ستشهده
            _R['rel'] = ll.append_entry(
                'release', 'رفع موثق داخل النافذة', component='predictive')
            result = _orig_re(path)
            log.chmod(0o000)  # تعطيل القراءة فور الإرجاع — لا قراءة ناجحة أخرى
            return result
        return _orig_re(path)
    ll.read_entries = re_injected
    r1 = c.post('/chat', json={'text': 'قراءة تشهد الرفع'})
    _R['status1'] = r1.status_code
    _R['pred1'] = counters['n']
    from backend.loyalty_log import fallback_quarantined
    _R['fallback_has_predictive'] = 'predictive' in fallback_quarantined()
    r2 = c.post('/chat', json={'text': 'قراءة متعذرة بعد الرفع المشهود'})
    _R['status2'] = r2.status_code
    _R['pred2_total'] = counters['n']
    _R['cache2'] = sorted(orch._quarantine_cache or [])
"""
    rc, payload, err = _run_chat_first_request_scenario(body, tmp_path)
    assert rc == 0 and payload is not None, f"السيناريو فشل: rc={rc} err={err[-300:]}"
    assert "unexpected_error" not in payload, payload["unexpected_error"]
    # إثبات الحقن كما طلب المراجع: False للعزل وTrue للرفع
    assert payload["q"] is False, "توثيق العزل يجب أن يفشل (الكتابة ممنوعة)"
    assert payload["rel"] is True, "توثيق الرفع يجب أن ينجح"
    assert payload["fallback_has_predictive"] is True, "حدث العزل غير موجود في الاحتياط"
    assert payload["status1"] == 200 and payload["status2"] == 200, payload
    # ضابط موجب: الحالة المستهدفة شهدت الرفع — التنبؤ حر ونُفذ في الطلب الأول
    assert payload["pred1"] > 0, "التنبؤ لم يُنفذ في الطلب الأول — العدّاد لا يقيس"
    # استمرار التنفيذ المسموح بعد تعذر القراءة — الرفع المشهود لا يُحيى
    assert payload["pred2_total"] > payload["pred1"], (
        f"الرفع الموثق الذي شاهدته القراءة الناجحة أُحيي عزله عند تعذر "
        f"القراءة — تنفيذات جديدة: "
        f"{payload['pred2_total'] - payload['pred1']}"
    )
    assert "predictive" not in payload["cache2"], (
        f"predictive عاد إلى الحالة رغم رفع موثق شاهدته قراءة ناجحة: "
        f"{payload['cache2']}"
    )
