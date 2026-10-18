"""حارس data/keys الحقيقي — يمنع تكرار واقعة R-621 (بند OWNER_REQUIRED ٥).

الواقعة: اختبار كتب سطر KEY_CREATED في data/keys/HISTORY.jsonl الحقيقي
المتتبع (المفتاح 979e95cbd4469226 — «R-621 test»؛ التوثيق في
forensics/council/round-1/RAW_ameen.md بند 3.10). العزل الافتراضي
(R-619 — SOVEREIGN_DATA_ROOT) يمنع الكتابة العابرة من المسارات الافتراضية،
لكنه لا يمنع اختبارًا يتجاوز العزل صراحة.

طبقتا المنع (بند ٥: «حارس يمنع تكرار الكتابة من الاختبارات»):
1. **منع الكتابة** (protect_real_keys): الملفان المحميان يُجعلان للقراءة
   فقط طوال الجلسة — أي محاولة كتابة (اختبارًا أو عند الاستيراد) تُرفض
   بـ PermissionError صريح يسمي الملف. هذا يمنع أيضًا نمط «اكتب ثم استعد
   الأصل» الذي تفلت منه مقارنة الحالة النهائية.
2. **كشف أثر التغيير** (snapshot/violations): بصمة البايتات عند بدء الجلسة
   تُقارن عند نهايتها — أي تغيير متبقٍ (إضافة/تعديل/حذف/إنشاء) يفشل
   الجلسة برسالة تشخيصية.

الأمان في الرسائل والمخرجات: محتوى keyring.json محمي — لا يُعرض نصًا
أبدًا (قد يحوي مادة المفاتيح)؛ يوصف تغييره بنوعه وبصمة SHA-256 قصيرة
فقط، والبايتات تُلفّ في ProtectedContent ذا repr آمن كي لا تعرضها pytest
عند فشل توكيد (اكتشفه مسبار عدم التسريب — تسريب حقيقي أصلح قبل الالتزام).
HISTORY.jsonl يحتوي مادة عامة (key_id/public_key/reason) فتُقتبس أسطره
المضافة نصًا للتشخيص.

حدود معلنة (لا ادعاء أوسع من المثبت): اختبار يتعمّد chmod الملف ثم يكتب
ثم يستعيد كامل الأصل يتجاوز الطبقتين — هذا هدم متعمد للحارس لا إهمال،
ويوثَّق هنا صراحة.
"""
import hashlib
import os
import stat
from pathlib import Path

# الملفات المحمية — نسبية لجذر المستودع.
# HISTORY.jsonl: السجل المفتاحي المتتبع (ملطخ تاريخيًا بواقعة R-621).
# keyring.json: حلقة المفاتيح الحقيقية (غير متتبعة — إنشاؤها من اختبار
# تلوث صريح كذلك).
PROTECTED_FILES = ("data/keys/HISTORY.jsonl", "data/keys/keyring.json")

# الملفات التي لا يُعرض محتواها في رسائل الفشل أبدًا (مادة محمية)
CONTENT_HIDDEN_FILES = ("data/keys/keyring.json",)

# بادئة رسالة الفشل — تُستخدم نصًا في الاختبارات السلوكية
# (backend/tests/invariants/test_real_keys_guard.py) وعند تشخيص فشل جلسة.
GUARD_MESSAGE_PREFIX = "R-621-لا-تتكرر: تلوث data/keys الحقيقي أثناء جلسة الاختبار"


def _short_digest(data: bytes) -> str:
    """بصمة SHA-256 قصيرة (8 خانات) — تعريف آمن للمحتوى دون عرضه."""
    return hashlib.sha256(data).hexdigest()[:8]


class ProtectedContent:
    """غلاف بايتات محمية — المادة لا تُعرض أبدًا.

    السبب: عند فشل توكيد الحارس، يعرض pytest المتغيرات المحلية بتقديمها
    (repr) — فلو مرّت البايتات الخام لظهر محتوى keyring.json (مادة
    المفاتيح) في مخرجات CI. هذا الغلاف يجعل repr آمنًا: البصمة والطول
    فقط، والمادة تُستعاد بدالة bytes() عند الحاجة للمقارنة.
    """

    __slots__ = ("_data", "_digest")

    def __init__(self, data: bytes):
        self._data = data
        self._digest = _short_digest(data)

    def __repr__(self) -> str:
        return f"<protected-content digest={self._digest} len={len(self._data)}>"

    def bytes(self) -> bytes:
        return self._data

    def __eq__(self, other) -> bool:
        if isinstance(other, ProtectedContent):
            return self._data == other._data
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._data)


def snapshot(repo_root) -> dict:
    """بصمة الملفات المحمية قبل الجلسة.

    تُقرأ البايتات كاملة (لا الوجود فقط) — التعديل داخل سطر قائم
    انتهاك كالإضافة — لكنها تُلفّ في ProtectedContent (repr آمن) كي لا
    تعرضها pytest عند فشل توكيد لاحق. الملف غير الموجود يُسجَّل None
    (إنشاؤه لاحقًا انتهاك).
    """
    root = Path(repo_root)
    return {
        rel: (
            ProtectedContent((root / rel).read_bytes())
            if (root / rel).exists()
            else None
        )
        for rel in PROTECTED_FILES
    }


def violations(repo_root, before: dict) -> list:
    """مقارنة الحالة بعد الجلسة بالبصمة قبلها — قائمة الانتهاكات الموصوفة.

    HISTORY.jsonl: تُقتبس الأسطر المضافة/المحذوفة نصًا (مادة عامة).
    keyring.json: لا يُقتبس المحتوى (مادة محمية) — نوع التغيير + بصمة
    SHA-256 قصيرة قبل/بعد فقط.
    """
    root = Path(repo_root)
    found = []
    for rel in PROTECTED_FILES:
        p = root / rel
        now = ProtectedContent(p.read_bytes()) if p.exists() else None
        was = before.get(rel)
        if now == was:
            continue
        if was is None and now is not None:
            found.append(f"{rel}: أُنشئ أثناء الجلسة (لم يكن موجودًا عند بدئها)")
        elif now is None:
            found.append(f"{rel}: حُذف أثناء الجلسة")
        elif rel in CONTENT_HIDDEN_FILES:
            was_d = was._digest if was is not None else "-"
            now_d = now._digest if now is not None else "-"
            found.append(
                f"{rel}: عُدّل أثناء الجلسة (المحتوى محمي لا يُعرض — "
                f"بصمة قبل: {was_d} ← بعد: {now_d})"
            )
        else:
            was_lines = was.bytes().decode("utf-8", errors="replace").splitlines()
            now_lines = now.bytes().decode("utf-8", errors="replace").splitlines()
            added = [ln for ln in now_lines if ln not in was_lines]
            removed = [ln for ln in was_lines if ln not in now_lines]
            parts = [f"{rel}: عُدّل أثناء الجلسة"]
            if added:
                parts.append(f"أسطر مضافة: {added[:3]}")
            if removed:
                parts.append(f"أسطر محذوفة: {removed[:3]}")
            found.append(" — ".join(parts))
    return found


def assert_untouched(repo_root, before: dict) -> None:
    """فشل صريح إن لُطخت الملفات المحمية — تُستدعى عند نهاية الجلسة.

    الاستدعاء الوحيد للرفض: AssertionError برسالة الحارس كاملة — لا صمت
    ولا ابتلاع (قواعد النزاهة: الفشل المحقون يُثبت التسجيل لا الصمت).
    """
    found = violations(repo_root, before)
    assert not found, GUARD_MESSAGE_PREFIX + ":\n" + "\n".join(found)


# الدليل الحاوي للملفات المحمية — حمايته تمنع الإنشاء والحذف والاستبدال
# الذري داخل data/keys (كلها عمليات كتابة على الدليل، لا على الملف)
PROTECTED_DIR = "data/keys"


def _remove_write_bits(path):
    """إزالة بتات الكتابة فقط — دون توسيع القراءة أبدًا.

    chmod 0o444 الثابت كان يوسّع القراءة: ملف وضعه 0600 (مادة مفاتيح —
    قراءة المالك فقط) يصير 0444 (قراءة للجماعة والآخرين أيضًا) — توسيع
    أمني فعلي (اعتراض المراجع). الإزالة الجراحية: الوضع الجديد =
    الأصل & ~0o222 — فـ 0600 تصير 0400 و0644 تصير 0444، بلا أي بت يُضاف.
    يُرجع الوضع الأصلي إن غُيّر، None إن كان محميًا أصلًا.
    """
    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & 0o222:  # به بتات كتابة — غير محمي بعد
        os.chmod(path, mode & ~0o222)
        return mode
    return None


def protect_real_keys(repo_root) -> dict:
    """منع الكتابة: إزالة بتات الكتابة من الدليل والملفات المحمية — يُستدعى
    عند تحميل conftest (قبل أي استيراد لملفات الاختبار).

    يحمي: (1) الدليل data/keys نفسه — فيُمنع الإنشاء والحذف والاستبدال الذري
    داخله (كلها كتابة على الدليل)، وذلك يشمل الملفات الغائبة أصلًا
    (keyring.json ليس في clone نظيف — إنشاؤه من اختبار تلوث)؛ (2) كل ملف
    محمي موجود — إزالة بتات الكتابة فقط دون أي توسيع للقراءة (0600 تصير
    0400، لا 0444).

    يُرجع خريطة {المسار_النسبي: الوضع_الأصلي} لاستعادتها عند نهاية الجلسة —
    لما غيّره هذا الاستدعاء فقط (idempotent): إن كان محميًا بالفعل (حارس
    conftest آخر سبقه بالتحميل) لا يُلمس ولا يُسجل — كي لا يستعيد حارسٌ
    لاحقٌ وضع الحماية كأنه «الأصلي» (اكتشاف حقيقي من تشغيل الحزمة).

    اتجاه الفشل الآمن: إن تعطلت الجلسة قبل الاستعادة تبقى الحماية قائمة —
    محميًا لا مكشوفًا (git لا يتتبع إلا بتة التنفيذ؛ لا أثر للوضع).
    """
    root = Path(repo_root)
    modes = {}
    keys_dir = root / PROTECTED_DIR
    if keys_dir.is_dir():
        dir_mode = _remove_write_bits(keys_dir)
        if dir_mode is not None:
            modes[PROTECTED_DIR] = dir_mode
    for rel in PROTECTED_FILES:
        p = root / rel
        if p.exists():
            m = _remove_write_bits(p)
            if m is not None:
                modes[rel] = m
    return modes


def restore_real_keys(repo_root, modes: dict) -> None:
    """استعادة الأوضاع الأصلية (الدليل والملفات) عند نهاية الجلسة.

    تُستدعى من pytest_sessionfinish — بعمر الجلسة نفسها لا بعمر fixtures:
    فتعمل مع --collect-only ومع إخفاقات التجميع (fixtures لا تشغل أصلًا
    هناك؛ خلل سابق كان يترك الملفات محمية بعد جمعٍ فقط).
    """
    root = Path(repo_root)
    for rel, mode in modes.items():
        p = root / rel
        if p.exists():
            os.chmod(p, mode)
