# backend/compat/__meta__.py
# نمط التين الخانق (Strangler Fig) — طبقة توثيق lifecycle لطبقة التوافق
# (المرحلة 4 من ROADMAP_V2)
#
# الغرض: منح طبقة compat أفقاً — كل وحدة توافق لها معيار إزالة (sunset
# criteria) موثّق. أي وحدة بدون معيار = لا أفق = فشل الاختبار الثابت.
#
# القاعدة الصارمة: حتى بعد sunset، لا يُحذف الملف. يُنقل إلى
# backend/compat/_legacy/ ويُبقى. الدستور يمنع الحذف.
#
# القاعدة الثانية: أي وحدة compat جديدة يجب أن تُضاف هنا مع معيار
# إزالة واضح. الاختبار test_compat_sunset_criteria.py يفشل بدونها.

from datetime import datetime, timezone
from pathlib import Path

# وقت إنشاء طبقة التوافق (أول التزام: 97ea6f1 — 2026-10-14)
_COMPAT_LAYER_CREATED = "2026-10-14T00:00:00Z"

# قاموس lifecycle لكل وحدة توافق
COMPAT_LIFECYCLE = {
    "nexus_lifecycle": {
        "created": _COMPAT_LAYER_CREATED,
        "reason": "initialize_nexus() لا يستدعي engine.start() — الحالة تبقى initializing",
        "target_replacement": "nexus/main.py:initialize_nexus",
        "sunset_criteria": (
            "engine.start() مُدمج مباشرة في initialize_nexus() في "
            "nexus/main.py + 30 يوماً بدون استدعاء لـ backend/compat/nexus_lifecycle.py"
        ),
        "call_count": 0,
        "status": "active",
    },
    "guardian_api": {
        "created": _COMPAT_LAYER_CREATED,
        "reason": "guardian/ (5 ملفات) غير مربوطة بأي مدخل حي — إحياء عبر /guardian/status",
        "target_replacement": "backend/app.py (نقطة /guardian/status مباشرة)",
        "sunset_criteria": (
            "guardian/ يُستورد مباشرة في backend/app.py + نقطة /guardian/status "
            "مُسجّلة بدون طبقة توافق + 30 يوماً بدون استدعاء لـ compat"
        ),
        "call_count": 0,
        "status": "active",
    },
    "nexus_recommendations": {
        "created": "2026-10-14T00:00:00Z",  # الالتزام 9c6eb3c
        "reason": (
            "GET /nexus/recommendations الأصلي يعيد قائمة فارغة ثابتة رغم أن "
            "RecommendationEngine مسجل — توليد توصيات فعلية"
        ),
        "target_replacement": "nexus/api_gateway/router.py:get_recommendations",
        "sunset_criteria": (
            "المسار الأصلي /nexus/recommendations يُعيد التوصيات الفعلية مباشرة "
            "من router.py + 30 يوماً بدون استدعاء لـ compat"
        ),
        "call_count": 0,
        "status": "active",
    },
    "nexus_router_compat": {
        "created": "2026-10-14T00:00:00Z",  # الالتزام 213b224
        "reason": (
            "Middleware يُصلح المسار الأصلي GET /nexus/recommendations "
            "(FastAPI يُطابق أول route مسجّل أولاً)"
        ),
        "target_replacement": "nexus/api_gateway/router.py:get_recommendations",
        "sunset_criteria": (
            "المسار الأصلي يُعيد توصيات فعلية بدون middleware + "
            "30 يوماً بدون استدعاء"
        ),
        "call_count": 0,
        "status": "active",
    },
}


def get_lifecycle_summary() -> dict:
    """يُعيد ملخص lifecycle لكل وحدة compat (للعرض في /compat/status)."""
    return {
        "total_modules": len(COMPAT_LIFECYCLE),
        "active": sum(1 for v in COMPAT_LIFECYCLE.values() if v["status"] == "active"),
        "pending_sunset": sum(1 for v in COMPAT_LIFECYCLE.values() if v["status"] == "pending_sunset"),
        "legacy_retained": sum(1 for v in COMPAT_LIFECYCLE.values() if v["status"] == "legacy_retained"),
        "modules": COMPAT_LIFECYCLE,
    }


def record_call(module_name: str) -> None:
    """يُسجّل استدعاءً لوحدة compat (يُستخدم من decorator @compat_tracked).

    تصويب المراجع (الاعتراض 4): التسجيل ذاكرة + تثبيت append-only
    (persist_call) — يبقى العدّ الحي في الذاكرة لـ/compat/status،
    والسجل المثبَّت أساس الحكم الزمني (evaluate_pending_sunset).
    """
    if module_name in COMPAT_LIFECYCLE:
        COMPAT_LIFECYCLE[module_name]["call_count"] += 1
        from datetime import datetime, timezone
        persist_call(module_name, datetime.now(timezone.utc).isoformat())


def compat_tracked(name: str):
    """
    Decorator يُسجّل عدد الاستدعاءات لوحدة compat.
    يُستخدم على كل دالة/كلاس في compat لقياس الاستخدام الفعلي.

    (الجولة الإنشائية 2026-10-16: functools.wraps يحفظ توقيع الدالة
    وبياناتها للـintrospection. تصويب المراجع — الاعتراض 4: الدوال
    غير المتزامنة يلفها غلاف غير متزامن يحفظ طبيعتها coroutine —
    inspect.iscoroutinefunction(wrapper) صادقة، والانتظار يعمل.)
    """
    import inspect
    from functools import wraps

    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                record_call(name)
                return await func(*args, **kwargs)
            async_wrapper.__compat_tracked__ = name
            return async_wrapper

        @wraps(func)
        def wrapper(*args, **kwargs):
            record_call(name)
            return func(*args, **kwargs)
        # الحفاظ على اسم الدالة الأصلية (لا حذف للواجهة)
        wrapper.__compat_tracked__ = name
        return wrapper
    return decorator


# ----------------------------------------------------------------------
# تصويب المراجع (الاعتراض 4): تثبيت الاستدعاءات + حكم الانتقال الزمني
# pending_sunset — قابلان للبناء الآن (لا ينتظران 30 يومًا تشغيلية):
# التثبيت سجل append-only (ts + module)، والحكم يقبل ساعة محقونة
# للاختبار. التاريخ التشغيلي الحقيقي يبدأ من أول تثبيت فعلي.
# ----------------------------------------------------------------------
CALL_LOG_FILENAME = "compat_call_log.jsonl"


def _call_log_path() -> "Path":
    """مسار سجل الاستدعاءات — جذر بيانات معزول إن وُجد (لا يلوث data/
    الحقيقي في الاختبارات)، وإلا جذر المستودع data/."""
    import os
    from pathlib import Path
    data_root = os.getenv("SOVEREIGN_DATA_ROOT")
    base = Path(data_root) if data_root else Path(__file__).resolve().parent.parent.parent / "data"
    return base / "sovereign_core" / CALL_LOG_FILENAME


def persist_call(module_name: str, ts: str, path=None) -> None:
    """يُلحق استدعاءً بالسجل المثبَّت (append-only — سطر لكل استدعاء).

    path اختياري: للاختبار المعزول على مسار صريح؛ الافتراضي جذر البيانات
    (SOVEREIGN_DATA_ROOT إن ضُبط، وإلا data/sovereign_core)."""
    import json
    from pathlib import Path as _P
    p = _P(path) if path else _call_log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": ts, "module": module_name}) + "\n")


def load_call_log(path=None) -> "list":
    """يقرأ سجل الاستدعاءات المثبَّت (سطر لكل استدعاء — ts + module)."""
    import json
    from pathlib import Path
    p = Path(path) if path else _call_log_path()
    out = []
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:  # TOLERATED: سطر سجل تالف — يُتخطى (الحارس يرفض الارتباط الزمني بلا سجل)
            continue
    return out


def last_call_at(module_name: str, entries=None, now=None) -> "str | None":
    """آخر استدعاء موثق لوحدة (من السجل المثبَّت)."""
    if entries is None:
        entries = load_call_log()
    times = [e["ts"] for e in entries if e.get("module") == module_name and e.get("ts")]
    return max(times) if times else None


def evaluate_pending_sunset(now: str, lifecycle=None, entries=None,
                            threshold_days: int = 30):
    """قاعدة ROADMAP_V2 (المرحلة 4، البند 4) — بحكم قابل للاختبار:

    أي وحدة compat لم تُستدعى لمدة threshold_days (افتراضيًا 30) تُنتقل
    إلى pending_sunset (توثيقًا — لا حذف أبدًا). الوحدة بلا أي استدعاء
    موثق تُقاس من تاريخ إنشائها (created). يعيد قاموسًا جديدًا — لا يعدل
    الأصل. ساعة محقونة (now) للاختبار القبلي/البعدي.
    """
    from datetime import datetime, timedelta
    from datetime import timezone as _tz

    if lifecycle is None:
        lifecycle = dict(COMPAT_LIFECYCLE)
    if entries is None:
        entries = load_call_log()

    now_dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
    threshold = timedelta(days=threshold_days)
    result = {}
    transitions = []

    for mod, entry in lifecycle.items():
        current_status = entry.get("status", "active")
        last = last_call_at(mod, entries=entries)
        reference = last or entry.get("created")
        if reference is None:
            result[mod] = dict(entry)
            continue
        ref_dt = datetime.fromisoformat(str(reference).replace("Z", "+00:00"))
        idle = now_dt - ref_dt
        new_status = current_status
        if current_status == "active" and idle >= threshold:
            new_status = "pending_sunset"
            transitions.append(mod)
        updated = dict(entry)
        updated["status"] = new_status
        updated["last_call_at"] = last
        updated["idle_days"] = round(idle.total_seconds() / 86400, 2)
        result[mod] = updated

    return {"lifecycle": result, "transitions": transitions,
            "now": now, "threshold_days": threshold_days}
