#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
 SOVRA · THE SOVEREIGN SINGULARITY
 backend/Mr.py — عقد الولاء المعقّم (R-686: نزع الفتيل)
============================================================

تاريخ هذا الملف:
- الأصل (1313 سطرًا) كان يحوي بروتوكول تدمير ذاتي: sys.exit في
  _execute_death وos._exit(1) في _trigger_final_death ومنطق «الموت
  بعد أول محاولة عبث» (عدّاد المحاولات القاتل) — الاستدعاء الثاني
  لinitialize قبل الختم كان يقتل العملية كلها (موت صامت فوري، حدث
  فعلًا أثناء التحقيق).
- أمر المالك 2026-10-18 (المرحلة ١ — نزع الفتيل): اقتلع القنبلة
  واستبدل الموت بالعزل. هذا الملف هو التنفيذ.

العقد الجديد (LoyaltyContract):
- الولاء حالة قابلة للفحص: BOUND (قبل ربط السيد) ← SEALED (مربوط)
  ← QUARANTINED (معزول بخلل جسيم).
- لا ولاء قبل ربط السيد (is_loyal تتطلب SEALED).
- المحاولة الخطرة (ربط مزدوج) تُسجل انتهاكًا وتُرفض — لا موت.
- العزل مرئي وقابل للتراجع، ورفعه يتطلب تفويض السيد نفسه.
- حارس AST دائم (test_no_death_paths.py) يمنع عودة أي مسار موت
  إلى أي كود قابل للتشغيل — ليس هذا الملف وحده.
- غير مربوط بأي كود حي (أمر المالك: المرحلة ١ — النظام الحي لا
  يعرف بوجوده بعد).
"""

import hashlib
import os
import sys
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional

# جذر المستودع على مسار الاستيراد — لعمل السيناريوهات المعزولة من أي cwd
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# المرحلة ٢ (R-687): التسجيل الدائم عبر طبقة السجل المشتركة — الكود الحي
# لا يستورد Mr (قيد R-686 محفوظ) والقراءة منفصلة في backend/circuit_breaker.py
from backend.loyalty_log import append_entry as _append_log_entry

# ============================================================
# حالات العقد
# ============================================================


class LoyaltyState(str, Enum):
    """حالات الولاء — لا حالة موت فيها إطلاقًا"""

    BOUND = "bound"            # العقد موجود، السيد لم يُربط بعد
    SEALED = "sealed"          # مربوط بالسيد — ولاء قائم
    QUARANTINED = "quarantined"  # معزول بخلل جسيم — قابل للفحص والتراجع


# ملف النواة نفسه — خط أساس سلامته يُختم تلقائيًا عند أول تهيئة
# (بديل حارس الملفات القاتل: الفحص مربوط بمسار التحقق المعتاد).
_CORE_FILE = os.path.abspath(__file__)


# ============================================================
# عقد الولاء — بلا قنبلة
# ============================================================


class LoyaltyContract:
    """
    عقد ولاء كحالة قابلة للفحص. نفس غرض النواة القديمة (ربط بالسيد +
    فحص الولاء) مع صفر مسارات موت: الخطأ الجسيم يُعزل ويُسجل، والعملية
    حية دائمًا.
    """

    _instance: Optional["LoyaltyContract"] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "LoyaltyContract":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        object.__setattr__(self, "_state", LoyaltyState.BOUND)
        object.__setattr__(self, "_master_hash", None)
        object.__setattr__(self, "_seal_time", None)
        object.__setattr__(self, "_quarantine_reason", None)
        object.__setattr__(self, "_violations", [])
        object.__setattr__(self, "_file_baselines", {})
        object.__setattr__(self, "_initialized", True)
        # ختم تلقائي لخط أساس سلامة ملف النواة نفسه — لا تسجيل يدوي
        self._seal_self_baseline()

    # الحقول المحمية: أي كتابة مباشرة لها من خارج العقد = عبث مكتشف
    _LOCKED_FIELDS = frozenset({
        "_state", "_master_hash", "_seal_time", "_quarantine_reason",
        "_violations", "_file_baselines", "_initialized",
    })

    def __setattr__(self, name: str, value: Any) -> None:
        """
        كشف العبث الداخلي — يعمل فعلًا (خطاف النواة القديمة كان وهميًا:
        إسناد __setattr__ على النسخة لا يعترض شيئًا، والموت القديم جاء
        من فحص الولاء بعد العبث لا من الاعتراض — مثبت بالتشغيل على
        41936cc). الآن: الكتابة المباشرة للحالة المحمية تُرفض وتُسجل
        (حدث tamper_attempt) ويُعزل العقد تلقائيًا — العملية حية دائمًا.
        الكتابات الداخلية تمر عبر object.__setattr__ مباشرة.
        """
        if name in self._LOCKED_FIELDS and getattr(
            self, "_initialized", False
        ):
            self._record_violation(
                "tamper_attempt",
                "محاولة تعديل الحالة مباشرة (عبث): " + name,
            )
            if self._state != LoyaltyState.QUARANTINED:
                self.quarantine(
                    "عبث مكتشف: كتابة مباشرة للحالة المحمية (" + name + ")"
                )
            return  # الكتابة مرفوضة — الحالة الأصلية باقية
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        """حذف خاصية محمية = عبث مكتشف — نفس الاستجابة (عزل لا موت)."""
        if name in self._LOCKED_FIELDS and getattr(
            self, "_initialized", False
        ):
            self._record_violation(
                "tamper_attempt",
                "محاولة حذف خاصية محمية (عبث): " + name,
            )
            if self._state != LoyaltyState.QUARANTINED:
                self.quarantine(
                    "عبث مكتشف: حذف خاصية محمية (" + name + ")"
                )
            return
        object.__delattr__(self, name)

    # ---------- ربط السيد ----------

    def bind_master(self, master_code: str) -> bool:
        """
        يربط العقد بكود السيد. المحاولة الثانية تُسجل انتهاكًا وتُرفض —
        النواة القديمة كانت تقتل العملية هنا (SELF_TAMPER_ATTEMPT).
        الربط أثناء العزل يُهيّئ اعتماد السيد فقط والحالة تبقى معزولة —
        لا يُرفع العزل إلا بتفويض السيد عبر release_quarantine (لا رفع
        ضمني عبر أي مسار آخر، ولا حبس بلا استرداد).
        """
        if self._state == LoyaltyState.QUARANTINED:
            if self._master_hash is None:
                # تهيئة الاعتماد أثناء العزل — العزل قائم حتى التفويض
                object.__setattr__(
                    self, "_master_hash",
                    hashlib.sha512(master_code.encode("utf-8")).hexdigest(),
                )
                self._record_violation(
                    "bind_during_quarantine",
                    "تهيئة اعتماد السيد أثناء العزل — العزل قائم حتى التفويض",
                )
                return True
            self._record_violation(
                "double_bind",
                "محاولة إعادة ربط السيد أثناء العزل — عُزلت المحاولة وسُجلت (لا موت)",
            )
            return False
        if self._master_hash is not None:
            self._record_violation(
                "double_bind",
                "محاولة إعادة ربط السيد — عُزلت المحاولة وسُجلت (لا موت)",
            )
            return False
        object.__setattr__(
            self, "_master_hash",
            hashlib.sha512(master_code.encode("utf-8")).hexdigest(),
        )
        object.__setattr__(self, "_state", LoyaltyState.SEALED)
        object.__setattr__(self, "_seal_time", time.time())
        return True

    def verify_master(self, master_code: str) -> bool:
        """
        التحقق من هوية السيد — المقارنة على الهاش فقط، الخام لا يُخزن.
        مسار التحقق المعتاد يبدأ بفحص سلامة ملف النواة نفسه: تعديل على
        القرص ← عزل + حدث file_integrity + فشل التحقق (بلا موت أبدًا —
        بديل موت الحارس القديم عند تعديل الملف).
        """
        if not self._ensure_self_integrity():
            return False
        if self._master_hash is None:
            return False
        provided = hashlib.sha512(master_code.encode("utf-8")).hexdigest()
        return provided == self._master_hash

    # ---------- الفحص ----------

    def _ensure_self_integrity(self) -> bool:
        """
        سلامة ملف النواة نفسها — يُستدعى من مسار التحقق المعتاد.
        فشل آمن: خط الأساس المفقود (فشل قراءة عند التهيئة) لا يسمح
        بولاء — عزل + حدث self_baseline_missing بدل تحقق ناجح بلا سلامة.
        """
        if _CORE_FILE not in self._file_baselines:
            self._record_violation(
                "self_baseline_missing",
                "خط أساس سلامة النواة مفقود — لا ولاء بلا سلامة متحققة",
            )
            if self._state != LoyaltyState.QUARANTINED:
                self.quarantine(
                    "خط أساس سلامة النواة مفقود (فشل القراءة عند التهيئة)"
                )
            return False
        return self.check_file_integrity(_CORE_FILE)

    def _seal_self_baseline(self) -> None:
        """يختم خط أساس ملف النواة (أول تهيئة فقط — لا ختم فوق تعديل)."""
        baselines = dict(self._file_baselines)
        if _CORE_FILE in baselines:
            return
        try:
            with open(_CORE_FILE, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            baselines[_CORE_FILE] = digest
            object.__setattr__(self, "_file_baselines", baselines)
        except OSError:  # R-686: لا موت أبدًا — الفقدان يُسجل ويفشل آمنًا
            self._record_violation(
                "self_baseline_failed",
                "فشل قراءة ملف النواة عند ختم خط الأساس",
            )

    def is_loyal(self) -> bool:
        """
        الولاء قائم فقط في SEALED — لا ولاء قبل ربط السيد. يبدأ بفحص
        سلامة ملف النواة (تعديل على القرص ← عزل لا موت — المسار القديم
        كان يقتل هنا).
        """
        if not self._ensure_self_integrity():
            return False
        return self._state == LoyaltyState.SEALED

    def get_status(self) -> Dict[str, Any]:
        """
        لقطة سلبية للحالة — لا تُشغل فحوصًا ولا تسجل أحداثًا (الحاصل
        لا يتحقق: الفحص النشط في is_loyal/verify_master).
        """
        return {
            "state": self._state.value,
            "loyal": self._state == LoyaltyState.SEALED,
            "master_bound": self._master_hash is not None,
            "quarantined": self._state == LoyaltyState.QUARANTINED,
            "quarantine_reason": self._quarantine_reason,
            "violations_count": len(self._violations),
            "death_paths": 0,  # عقد صريح: لا مسارات موت في هذه النواة
        }

    # ---------- العزل بدل الموت ----------

    def quarantine(self, reason: str, component: Optional[str] = None) -> None:
        """عزل صريح لخلل جسيم — العملية حية دائمًا. component (R-687): عزل
        مكوّن تحديدًا في سجل العزل الدائم (يقرؤه مدخل التوجيه) — بلا مكوّن
        يبقى عزلًا عامًا للعقد كما كان تمامًا."""
        self._record_violation("quarantine", reason, component)
        self._quarantine_now(reason)

    def _quarantine_now(self, reason: str) -> None:
        """ضبط العزل داخليًا (الكتابات الداخلية تتجاوز حارس __setattr__)."""
        object.__setattr__(self, "_state", LoyaltyState.QUARANTINED)
        object.__setattr__(self, "_quarantine_reason", reason)

    # ---------- سلامة الملفات على القرص (بلا حارس قاتل) ----------

    def seal_file_baseline(self, path: str) -> None:
        """
        يسجل خط أساس سلامة ملف (هاش sha256) — الحارس القديم كان daemon
        يقتل العملية عند تعديل Mr.py؛ هنا الفحص صريح وقابل للاستدعاء
        (الآن يدويًا ولاحقًا من طبقة الحارس المعزولة في المرحلة ٢) —
        حساب السلامة مفصول عن أي إنهاء.
        """
        # خط أساس النواة نفسها محمي من إعادة الختم: إعادة الختم بعد
        # تعديل = إعادة اعتماد الملف المعدّل وإخفاء المخالفة — مرفوض
        if str(path) == _CORE_FILE and str(path) in self._file_baselines:
            self._record_violation(
                "baseline_reseal_refused",
                "رفض إعادة ختم خط أساس النواة — الخط الأصلي باقٍ والمحاولة مسجلة",
            )
            return
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        baselines = dict(self._file_baselines)
        baselines[str(path)] = digest
        object.__setattr__(self, "_file_baselines", baselines)

    def check_file_integrity(self, path: str) -> bool:
        """
        يقارن الملف بخط أساسه المسجل: اختلاف ← عزل + حدث file_integrity
        (استجابة العزل بدل موت الحارس القديم)؛ تطابق ← True. الملف غير
        المراقب ← True (لا ادعاء مراقبة).
        """
        baseline = self._file_baselines.get(str(path))
        if baseline is None:
            return True
        try:
            with open(path, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            self.quarantine(
                "ملف مراقب أصبح غير قابل للقراءة: " + str(path)
            )
            return False
        if digest != baseline:
            reason = "تعديل ملف مراقب على القرص: " + str(path)
            self._record_violation("file_integrity", reason)
            self.quarantine(reason)
            return False
        return True

    def report_fault(self, source: str, detail: str, component: Optional[str] = None) -> None:
        """
        نقطة دخول اكتشاف الأخطاء: أي مسار كشف (داخلي أو لاحقًا من الحارس)
        يبلّغ عن خلل هنا ← استجابة موحدة: عزل + حدث مسجل — لا موت أبدًا.
        (بديل مسارات الموت القديمة: كان الخلل يقتل العملية؛ الآن يعزلها.)
        component (R-687): بلاغ بمكوّن تحديدًا — يُوثق في سجل العزل للتوجيه.
        """
        self.quarantine(f"[{source}] {detail}", component)

    def release_quarantine(self, master_code: str, decision: str, component: Optional[str] = None) -> bool:
        """
        رفع العزل يتطلب تفويض السيد نفسه — محاولة غير مصرح بها تُسجل
        انتهاكًا وتُرفض، والعزل يبقى. تكرار المحاولات غير المصرح بها
        (٣ محاولات) يعزل العقد فورًا إن لم يكن معزولًا (كشف ← استجابة).
        component (R-687 — المرحلة ٢): رفع عزل مكوّن تحديدًا — سطر رفع
        في سجل العزل الدائم للمكوّن تحديدًا وحالة العقد العامة لا تتغير
        (الرفع المكوّني قرار توجيه؛ رفع العقد العام يبقى بالمسار نفسه).
        """
        if not self.verify_master(master_code):
            self._record_violation(
                "unauthorized_release",
                "محاولة رفع عزل بلا تفويض السيد — رُفضت وسُجلت",
                component,
            )
            if (
                self._count_violations("unauthorized_release") >= 3
                and self._state != LoyaltyState.QUARANTINED
            ):
                self.quarantine("تكرار محاولات رفع غير مصرح بها (٣+)")
            return False
        # المرحلة ٢ (R-687): رفع مكوّن تحديدًا — سطر رفع في السجل للمكوّن
        # تحديدًا، وحالة العقد العامة لا تتغير (الرفع المكوّني قرار توجيه)
        if component is not None:
            self._record_violation(
                "release",
                "رفع عزل المكوّن — القرار: " + decision,
                component,
            )
            return True
        if self._state != LoyaltyState.QUARANTINED:
            return False
        new_state = (
            LoyaltyState.SEALED if self._master_hash else LoyaltyState.BOUND
        )
        self._record_violation("release", "رفع العزل — القرار: " + decision)
        object.__setattr__(self, "_state", new_state)
        object.__setattr__(self, "_quarantine_reason", None)
        return True

    # ---------- داخلي ----------

    def get_violations(self) -> list:
        """سجل الانتهاكات للفحص — نسخة للقراءة فقط (لا تغيّر الحالة)."""
        return [dict(v) for v in self._violations]

    def _count_violations(self, kind: str) -> int:
        return sum(1 for v in self._violations if v["kind"] == kind)

    def _record_violation(self, kind: str, detail: str, component: Optional[str] = None) -> None:
        self._violations.append(
            {"kind": kind, "detail": detail, "time": time.time()}
        )
        if component is not None:
            self._violations[-1]["component"] = component
        # المرحلة ٢ (R-687): توثيق دائم append-only في سجل العزل — فشل
        # الكتابة معزول عن التشغيل (السجل يعيد False ولا يرفع شيئًا أبدًا)
        _append_log_entry(kind, detail, component)


# ============================================================
# الواجهة العامة — أسماء النواة القديمة محفوظة حيث لها معنى
# ============================================================

_contract: Optional[LoyaltyContract] = None
_contract_lock = threading.Lock()


def get_contract() -> LoyaltyContract:
    """الوصول إلى العقد المفرد — إنشاء آمن، آمن للتكرار بلا أي شرط موت."""
    global _contract
    if _contract is None:
        with _contract_lock:
            if _contract is None:
                _contract = LoyaltyContract()
    return _contract


def initialize_loyalty_core() -> LoyaltyContract:
    """
    تهيئة نواة الولاء — آمنة للتكرار بلا أي شرط. (في النواة القديمة كان
    الاستدعاء الثاني قبل الختم يقتل العملية بـos._exit(1) — عُزل هذا
    السلوك بأمر المالك، المرحلة ١).
    """
    return get_contract()


def bind_loyalty_to_master(master_code: str) -> bool:
    """ربط الولاء بالسيد — المحاولة المزدوجة تُعزل لا تقتل."""
    return get_contract().bind_master(master_code)


def verify_master(master_code: str) -> bool:
    """التحقق من هوية السيد."""
    return get_contract().verify_master(master_code)


def is_loyal() -> bool:
    """الولاء يتطلب ربط السيد."""
    return get_contract().is_loyal()


def get_loyalty_status() -> Dict[str, Any]:
    """حالة العقد كاملة — بلا أي مسار موت."""
    return get_contract().get_status()
