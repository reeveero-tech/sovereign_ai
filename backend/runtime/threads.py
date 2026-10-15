"""
R-682 — إدارة موحدة لخيوط الخلفية (daemon).

لماذا هذا الملف:
- قبل R-682 كانت الوحدات تطلق خيوطها بنفسها (Thread + start) دون تسجيل
  مرجع ولا انضمام عند الإنهاء، فتبقى حية بعد انتهاء جلسة pytest وتكتب
  في ملفات سجل مغلقة («--- Logging error ---»).
- خيط خلفي قديم يظل يحمل بيئة اختبار سابقة فيوقّع أحداثًا بمفاتيح لم
  تعد موجودة في KeyRing الحالي، فيرفض التوقيع (R-626) — «خيط خارج عمر
  بيئته»، لا «سلوك مقصود».

ما يوفره هذا الملف (بند ٥ من جولة R-682):
- start_managed(): إنشاء خيط daemon + تسجيل مرجعه + تسجيل دالة إيقافه
  (تُنزل أعلام الحلقات _active/_processing/_dead) ثم تشغيله.
- stop_all_and_join(): إيقاف كل الخيوط المسجلة والانتظار بانضمام محدود
  المدة (deadline واحد للجميع)، وتُستدعى من fixture جلسة pytest
  (tests/conftest.py) وقبل إغلاق العملية عبر atexit.

مفتاح بيئة الاختبار (بند ٦):
- SOVEREIGN_DISABLE_BACKGROUND_THREADS=1 يمنع إنشاء خيوط الخلفية
  تمامًا في بيئة الاختبار (تُختبر الوحدات في جلسة نظيفة بلا خيوط
  توقّع بمفاتيح قديمة). يضبطه tests/conftest.py قبل أي استيراد للنظام.

الإنتاج لا يتأثر: المتغير غير مضبوط افتراضيًا فتعمل الخيوط كالمعتاد،
ويظل atexit يشغّل الإنهاء المنظم عند خروج العملية.
"""
import atexit
import os
import threading

_THREADS: list = []   # مراجع الخيوط الحية المسجلة
_STOPPERS: list = []   # دوال الإيقاف — كل دالة تُنزل أعلام حلقة خيط واحد
_STOP_EVENT = threading.Event()  # يوقظ كل النوم المقاطع (interruptible_sleep)


def interruptible_sleep(seconds: float) -> bool:
    """نوم خيط خلفي قابل للمقاطعة — بدل time.sleep داخل حلقات الخلفية.

    المشكلة: حلقة تحرس على علم _active لكنها داخل time.sleep(3600) لا
    ترى العلم إلا بعد ساعة — فلا يتوقف الخيط عند الإنهاء المنظم. هذه
    الدالة تستيقظ فورًا عند طلب الإيقاف (stop_all_and_join يضبط الحدث
    العام قبل ضبط الأعلام). تعيد True إن طُلب الإيقاف.
    """
    return _STOP_EVENT.wait(seconds)


def background_threads_enabled() -> bool:
    """هل خيوط الخلفية مسموحة في هذه البيئة؟"""
    return os.environ.get("SOVEREIGN_DISABLE_BACKGROUND_THREADS") != "1"


def _stopper_for(owner) -> "object":
    """دالة إيقاف تُنزل كل أعلام الحلقات المعروفة في الكائن المالك."""
    def stop() -> None:
        # أعلام الحلقات المعروفة عبر النظام: _active (الأغلبية)،
        # _processing (الذاكرة الديناميكية)، _monitoring (حارس الدفاع watcher.py)
        for attr in ("_active", "_processing", "_monitoring"):
            try:
                setattr(owner, attr, False)
            except Exception:  # TOLERATED: R-682 — إيقاف خيط لا يجب أن يفشل كله إن رُفض ضبط علم واحد
                pass
        try:
            setattr(owner, "_dead", True)  # علم Mr.py (while not self._dead)
        except Exception:  # TOLERATED: R-682 — علم Mr.py اختياري في بقية الوحدات
            pass
    return stop


def start_managed(target, owner=None, name=None, stop_event=None):
    """إنشاء خيط daemon مسجّل + تشغيله. يعيد الخيط أو None إن كانت الخيوط معطلة.

    stop_event: threading.Event تُضبط عند الإيقاف — للحلقات التي لا تحرس
    على علم _active بل تنام بـ wait() قابل للمقاطعة.
    """
    if not background_threads_enabled():
        return None
    t = threading.Thread(target=target, daemon=True, name=name)
    _THREADS.append(t)
    if owner is not None:
        _STOPPERS.append(_stopper_for(owner))
    if stop_event is not None:
        _STOPPERS.append(stop_event.set)
    t.start()
    return t


def active_count() -> int:
    """عدد الخيوط المسجلة التي لا تزال حية."""
    return sum(1 for t in _THREADS if t.is_alive())


def stop_all_and_join(timeout: float = 8.0) -> int:
    """إيقاف كل الخيوط المسجلة والانتظار حتى انتهائها (deadline واحد).

    تعيد عدد الخيوط التي لم تتوقف خلال المدة — المفروض صفر.
    """
    import time
    deadline = time.monotonic() + timeout
    _STOP_EVENT.set()  # إيقاظ كل النوم المقاطع قبل ضبط الأعلام
    for s in list(_STOPPERS):
        try:
            s()
        except Exception:  # TOLERATED: R-682 — استثناء إيقاف خيط لا يوقف إيقاف البقية
            pass
    for t in list(_THREADS):
        if t.is_alive():
            t.join(timeout=max(0.0, deadline - time.monotonic()))
    remaining = sum(1 for t in _THREADS if t.is_alive())
    _THREADS.clear()
    _STOPPERS.clear()
    return remaining


# شبكة أمان أخيرة: إن لم تستدعِ الجلسة stop_all_and_join بنفسها
# (كما في الإنتاج)، تُستدعى عند خروج العملية — الخيوط daemon فتموت
# أصلًا مع العملية، لكن هذا يمنع الكتابة بعد إغلاق ملفات السجل.
atexit.register(lambda: stop_all_and_join(timeout=2.0))
