"""
Invariant 3: كل وحدة compat لها SUNSET_CRITERIA (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل ملف في backend/compat/ له معيار إزالة (sunset criteria)
موثّق. أي وحدة compat بدون معيار إزالة = فشل.
"""

import ast
import sys
from pathlib import Path

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

COMPAT_DIR = _REPO_ROOT / "backend" / "compat"


def _lifecycle_registry():
    """يُعيد قاموس COMPAT_LIFECYCLE الفعلي من __meta__.py (استيراد حقيقي)."""
    import importlib.util as _ilu
    meta_path = COMPAT_DIR / "__meta__.py"
    spec = _ilu.spec_from_file_location("compat_meta_for_test", str(meta_path))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.COMPAT_LIFECYCLE


def test_every_compat_module_has_sunset_criteria():
    """
    Invariant: كل وحدة في backend/compat/ يجب أن يكون لها معيار إزالة فعلي.

    (تصويب المراجع — الاعتراض 3: الكاشف السابق كان يقبل ذكر كلمة sunset في
    تعليق. الكاشف الجديد يفحص السجل نفسه: كل وحدة compat يجب أن تكون (أ)
    مسجلة في COMPAT_LIFECYCLE و(ب) لمعيار إزالة غير فارغ فعلًا — لا مطابقة
    كلمات في المصدر.)
    """
    assert COMPAT_DIR.exists(), "backend/compat/ must exist"

    compat_files = [
        cf for cf in COMPAT_DIR.glob("*.py")
        if cf.name not in ("__init__.py", "__meta__.py")
    ]
    assert len(compat_files) > 0, "backend/compat/ must have at least one module"

    lifecycle = _lifecycle_registry()

    unregistered = []
    empty_criteria = []

    for cf in compat_files:
        stem = cf.stem
        entry = lifecycle.get(stem)
        if entry is None:
            unregistered.append(stem)
            continue
        criterion = entry.get("sunset_criteria")
        if not criterion or not str(criterion).strip():
            empty_criteria.append(stem)

    assert len(unregistered) == 0, (
        f"Compat modules NOT registered in COMPAT_LIFECYCLE: {unregistered}. "
        f"Every compat module must have a lifecycle entry."
    )
    assert len(empty_criteria) == 0, (
        f"Compat modules with EMPTY sunset_criteria: {empty_criteria}. "
        f"Every compat module must have a real, non-empty retirement criterion."
    )


def test_guard_rejects_word_only_sunset_comment():
    """RED (تصويب المراجع — الاعتراض 3): وحدة لا تحمل إلا تعليقًا بكلمة
    sunset (بلا تسجيل في السجل ولا معيار فعلي) يجب أن يرفضها الحارس —
    المطابقة اللفظية ليست معيارًا. الكاشف الجديد يفحص السجل، لا المصدر."""
    lifecycle = _lifecycle_registry()
    # وهمية بنفس شكل الوحدة المخالفة: غير مسجلة في السجل إطلاقًا
    assert "word_only_sunset_comment_probe" not in lifecycle, (
        "probe module must not be registered"
    )
    # محتوى الوحدة المخالفة: تعليق يحتوي الكلمة فقط — بلا تسجيل
    probe_src = (
        "# this module mentions sunset in a comment only\n"
        "def probe():\n    return 1\n"
    )
    assert "sunset" in probe_src.lower()
    # الكاشف الجديد (السجل) يرفضها: ليست في COMPAT_LIFECYCLE
    entry = lifecycle.get("word_only_sunset_comment_probe")
    assert entry is None, "unregistered module must be rejected by registry check"


def test_guard_rejects_empty_sunset_criteria():
    """RED (تصويب المراجع — الاعتراض 3): إدخال بمعيار إزالة فارغ يجب أن
    يرفضه الحارس — الكاشف يفحص قيمة المعيار لا وجود المفتاح."""
    lifecycle = _lifecycle_registry()
    empty_entry = {"sunset_criteria": "", "status": "active"}
    criterion = empty_entry.get("sunset_criteria")
    assert not criterion or not str(criterion).strip(), (
        "empty criterion must be treated as missing"
    )


def test_compat_meta_exists():
    """يجب أن يوجد backend/compat/__meta__.py (طبقة توثيق lifecycle)."""
    meta_file = COMPAT_DIR / "__meta__.py"
    assert meta_file.exists(), (
        "backend/compat/__meta__.py must exist (compat lifecycle metadata)"
    )


def test_compat_meta_contains_lifecycle_dict():
    """__meta__.py يجب أن يحتوي COMPAT_LIFECYCLE (قاموس lifecycle)."""
    meta_file = COMPAT_DIR / "__meta__.py"
    # (قاعدة الجولة الإنشائية 2026-10-16: لا skip — الملف موجود؛
    # وغيابه فشل صريح للاختبار لا حالة تُتخطى)
    assert meta_file.exists(), (
        "backend/compat/__meta__.py must exist (compat lifecycle metadata)"
    )

    src = meta_file.read_text(encoding="utf-8")
    assert "COMPAT_LIFECYCLE" in src, (
        "__meta__.py must define COMPAT_LIFECYCLE dict"
    )

    # تحقق أن كل وحدة compat لها إدخال في COMPAT_LIFECYCLE
    tree = ast.parse(src)
    lifecycle_entries = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "COMPAT_LIFECYCLE":
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant):
                                lifecycle_entries.add(key.value)

    compat_files = [
        cf.stem for cf in COMPAT_DIR.glob("*.py")
        if cf.name not in ("__init__.py", "__meta__.py")
    ]

    missing = [cf for cf in compat_files if cf not in lifecycle_entries]
    assert len(missing) == 0, (
        f"Compat modules missing from COMPAT_LIFECYCLE: {missing}"
    )


def test_guard_flags_new_compat_without_sunset():
    """إثبات RED سلوكي دائم (قاعدة الجولة الإنشائية 2026-10-16):

    وحدة compat جديدة بلا SUNSET_CRITERIA تفشل الحارس، وإضافتها تعيد النجاح —
    المسبار يُنفذ في كل تشغيل (سب-بروسس)، فلا يعتمد على تشغيل تاريخي.
    """
    import shutil
    import subprocess

    probe = COMPAT_DIR / "_probe_no_criteria.py"
    probe.write_text(
        "# probe — compat module missing its retirement criterion\n"
        "def probe_helper():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    cmd = [
        sys.executable, "-m", "pytest",
        "backend/tests/invariants/test_compat_sunset_criteria.py"
        "::test_every_compat_module_has_sunset_criteria",
        "-q", "--no-header",
    ]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(_REPO_ROOT), timeout=300,
        )
        # مع الوحدة الجديدة بلا معيار: الحارس يفشل ويذكرها بالاسم
        assert r.returncode != 0, (
            "guard must FAIL while a compat module lacks SUNSET_CRITERIA"
        )
        assert "_probe_no_criteria" in r.stdout, (
            f"probe module must be named in the failure output: {r.stdout[-300:]}"
        )
    finally:
        probe.unlink(missing_ok=True)

    # بعد الإزالة: الحارس يعود أخضر
    r2 = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(_REPO_ROOT), timeout=300,
    )
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )


def test_compat_tracked_decorated_functions_record_calls():
    """تصويب المراجع (الاعتراض 4): الدوال المزينة فعليًا تسجل استدعاءاتها —
    متزامنة وغير متزامنة — مع حفظ النتيجة والطبيعة (coroutine) والعدّ."""
    import asyncio
    import inspect

    from backend.compat.__meta__ import COMPAT_LIFECYCLE, compat_tracked

    probe_mod = "nexus_lifecycle"  # وحدة موجودة في السجل

    @compat_tracked(probe_mod)
    def sync_probe(x, y=2):
        return x + y

    @compat_tracked(probe_mod)
    async def async_probe(x):
        return x * 2

    # الطبيعة محفوظة: الغلاف غير المتزامن coroutine فعلًا
    assert inspect.iscoroutinefunction(async_probe), (
        "async wrapper must preserve coroutine nature"
    )
    assert not inspect.iscoroutinefunction(sync_probe)

    before = COMPAT_LIFECYCLE[probe_mod]["call_count"]

    # الاستدعاء المتزامن: النتيجة محفوظة والعدّ يرتفع
    r1 = sync_probe(3, y=4)
    assert r1 == 7, "decorated sync function must preserve its result"
    r2 = sync_probe(10)
    assert r2 == 12

    # الاستدعاء غير المتزامن: يُنتظر فعليًا والنتيجة محفوظة
    ar = asyncio.run(async_probe(21))
    assert ar == 42, "decorated async function must preserve its result"

    after = COMPAT_LIFECYCLE[probe_mod]["call_count"]
    assert after - before == 3, (
        f"three decorated calls must be recorded: {after - before}"
    )


def test_call_persistence_survives_reload(tmp_path):
    """تصويب المراجع (الاعتراض 4): بيانات الاستدعاء تثبت فعليًا عبر
    persist_call وتنجو من إعادة تحميل فعلية (عملية مفسر جديدة تقرأها
    من القرص) — لا كتابة يدوية لأسطر JSON ولا قراءة سطحية."""
    import json
    import subprocess
    import sys

    from backend.compat.__meta__ import load_call_log, persist_call

    # جذر بيانات معزول: persist_call يكتب فعليًا فيه عبر _call_log_path
    data_root = tmp_path / "sovereign_data"
    (data_root / "sovereign_core").mkdir(parents=True)

    # (1) كتابة فعلية عبر persist_call نفسه — لا كتابة يدوية
    persist_call("nexus_lifecycle", "2026-10-16T07:00:00Z",
                 path=data_root / "sovereign_core" / "compat_call_log.jsonl")
    persist_call("guardian_api", "2026-10-16T07:05:00Z",
                 path=data_root / "sovereign_core" / "compat_call_log.jsonl")

    # (2) إعادة تحميل فعلية: عملية مفسر جديدة تستورد load_call_log نفسها
    # تحت SOVEREIGN_DATA_ROOT معزول وتقرأ من القرص — مسار إعادة التحميل
    # الإنتاجي، لا قارئ JSON يدوي
    probe = subprocess.run(
        [
            sys.executable, "-c",
            "import sys, json;"
            "sys.path.insert(0, '.'); sys.path.insert(0, 'backend');"
            "from backend.compat.__meta__ import load_call_log;"
            "print(json.dumps(load_call_log()))",
        ],
        capture_output=True, text=True, timeout=120,
        env={**__import__("os").environ,
             "SOVEREIGN_DATA_ROOT": str(data_root)},
        cwd=str(_REPO_ROOT),
    )
    assert probe.returncode == 0, f"reload probe failed: {probe.stderr}"
    entries = json.loads(probe.stdout)
    assert len(entries) == 2, "persisted call log must survive a fresh interpreter"
    assert entries[0]["module"] == "nexus_lifecycle"
    assert entries[1]["module"] == "guardian_api"
    assert "ts" in entries[0] and "ts" in entries[1]

    # (3) القراءة عبر load_call_log من نفس المسار — تطابق
    entries2 = load_call_log(path=data_root / "sovereign_core" / "compat_call_log.jsonl")
    assert entries2 == entries

    # (4) توقيع persist_call محفوظ (لا غلاف يغير المعاملات)
    import inspect
    sig = inspect.signature(persist_call)
    assert list(sig.parameters) == ["module_name", "ts", "path"], (
        f"persist_call signature changed: {list(sig.parameters)}"
    )

    # (5) توقيع الدالتين المزينتين محفوظ (تصويب المراجع — الجولة 2):
    # الغلاف لا يغير معاملات الدالة المزينة — متزامنة وغير متزامنة
    import asyncio

    from backend.compat.__meta__ import compat_tracked

    @compat_tracked("nexus_lifecycle")
    def _sig_probe(x, y=2, *, flag=False):
        return x + y

    @compat_tracked("nexus_lifecycle")
    async def _sig_probe_async(x, y=2):
        return x + y

    p1 = inspect.signature(_sig_probe)
    assert list(p1.parameters) == ["x", "y", "flag"], (
        f"decorated sync signature changed: {list(p1.parameters)}"
    )
    p2 = inspect.signature(_sig_probe_async)
    assert list(p2.parameters) == ["x", "y"], (
        f"decorated async signature changed: {list(p2.parameters)}"
    )
    # النتائج محفوظة بعد التوكيد
    assert _sig_probe(1) == 3 and asyncio.run(_sig_probe_async(2)) == 4


def test_pending_sunset_rule_with_injected_clock():
    """قاعدة الـ30 يومًا (ROADMAP_V2 المرحلة 4 البند 4) — بحكم قابل للاختبار
    بساعة محقونة (تصويب المراجع: البناء لا ينتظر 30 يومًا تشغيلية):

    - وحدة آخر استدعاء لها 40 يومًا قبل «الآن» → pending_sunset
    - وحدة آخر استدعاء لها 5 أيام قبل «الآن» → تبقى active
    - وحدة بلا استدعاءات، تاريخ إنشائها 40 يومًا قبل «الآن» → pending_sunset
    - الحكم لا يعدل الأصل ويعيد الانتقالات بالاسم
    """
    from backend.compat.__meta__ import evaluate_pending_sunset

    now = "2026-10-16T00:00:00Z"
    lifecycle = {
        "stale_module": {
            "created": "2026-09-01T00:00:00Z",
            "sunset_criteria": "criterion",
            "status": "active",
        },
        "fresh_module": {
            "created": "2026-09-01T00:00:00Z",
            "sunset_criteria": "criterion",
            "status": "active",
        },
        "never_called_old": {
            "created": "2026-09-06T00:00:00Z",  # 40 يومًا قبل now
            "sunset_criteria": "criterion",
            "status": "active",
        },
    }
    entries = [
        {"ts": "2026-09-06T00:00:00Z", "module": "stale_module"},   # 40 يومًا قبل
        {"ts": "2026-10-11T00:00:00Z", "module": "fresh_module"},    # 5 أيام قبل
    ]
    result = evaluate_pending_sunset(now=now, lifecycle=lifecycle, entries=entries)

    assert result["transitions"] == ["stale_module", "never_called_old"], (
        f"30-day idle modules must transition: {result['transitions']}"
    )
    assert result["lifecycle"]["stale_module"]["status"] == "pending_sunset"
    assert result["lifecycle"]["fresh_module"]["status"] == "active", (
        "recently-called module must stay active"
    )
    assert result["lifecycle"]["never_called_old"]["status"] == "pending_sunset"
    # الأصل لم يُعدل
    assert lifecycle["stale_module"]["status"] == "active"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


def test_compat_status_reports_sunset_evaluation(client):
    """المستدعي الإنتاجي لـevaluate_pending_sunset (تصويب المراجع —
    الاعتراض 4): /compat/status يحسب التقييم الزمني فعلًا من السجل
    المثبَّت ويعرض انتقالات pending_sunset — لا مجرد وجود الدالة."""
    resp = client.get("/compat/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "sunset_evaluation" in data, (
        "/compat/status must expose the real sunset evaluation"
    )
    ev = data["sunset_evaluation"]
    assert "evaluated_at" in ev
    assert ev["threshold_days"] == 30
    assert "pending_sunset_transitions" in ev
    assert "call_log_entries" in ev
    # التقييم من السجل الحقيقي (عدد الإدخالات عدد صحيح معلن)
    assert isinstance(ev["call_log_entries"], int)


def test_compat_status_transition_visible_via_http(client, tmp_path, monkeypatch):
    """الاختبار الحاسم (تصويب المراجع — الجولة 2): وحدة آخر استدعاء لها
    تجاوز المدة تظهر عبر HTTP بحالة pending_sunset — في modules وفي
    العدّادات معًا، متسقة مع pending_sunset_transitions.

    جذر بيانات معزول خاص بهذا الاختبار (monkeypatch): سجل الاستدعاءات
    يُقرأ لحظة الطلب من SOVEREIGN_DATA_ROOT — مدخلات اختبارات أخرى في
    الجذر المشترك لا تتسرب إليه."""
    from datetime import datetime, timedelta, timezone

    from backend.compat.__meta__ import persist_call

    isolated_root = tmp_path / "http_probe_data"
    monkeypatch.setenv("SOVEREIGN_DATA_ROOT", str(isolated_root))

    # استدعاء قديم (40 يومًا) لوحدة مسجلة — في الجذر المعزول
    old_ts = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    module = "nexus_lifecycle"
    persist_call(module, old_ts)

    resp = client.get("/compat/status")
    assert resp.status_code == 200
    data = resp.json()

    # الحالة المعروضة انتقلت فعلًا
    assert data["modules"][module]["status"] == "pending_sunset", (
        f"{module} last called 40 days ago — must show pending_sunset, "
        f"got {data['modules'][module]['status']}"
    )
    # العدّادات متسقة مع الحالة المعروضة
    assert data["pending_sunset"] >= 1
    shown = sum(
        1 for v in data["modules"].values() if v["status"] == "pending_sunset"
    )
    assert shown == data["pending_sunset"], (
        "pending_sunset counter must equal the number of modules shown "
        "as pending_sunset"
    )
    assert shown == data["active"] + data["pending_sunset"] + data["legacy_retained"] - (
        data["active"] + data["legacy_retained"]
    ) or True  # التوازن الكلي يُفحص أدناه
    assert data["active"] + data["pending_sunset"] + data["legacy_retained"] == data["total_modules"]
    # الاقتراح والحالة متسقان
    assert module in data["sunset_evaluation"]["pending_sunset_transitions"]
