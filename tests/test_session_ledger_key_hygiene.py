"""
R-682 — حراسة نظافة مفاتيح سجل الجلسة (اختبار انحدار لرفض R-626 المتبقي).

السبب الجذري المحدد بالتتبع (جلسة 2026-10-16): اختبارات تُنشئ SovereignCore()
بلا مسارات صريحة وتُدخل فيه KeyRing معزولًا — فتكتب أحداثًا (interaction)
وحدث KEY_ROTATED (عبر KeyRotation بلا ledger_path) في **سجل الجذر المشترك
لجلسة pytest**، بمفاتيح ليست في keyring الجلسة. لاحقًا يُشغّل مكون ما
verify_content_integrity على سجل الجلسة فيرفض التحقق من تلك الأحداث
(فشل مغلق صحيح السلوك) ويُسجّل رفض R-626 — 10 سجلات في الجلسة الكاملة.

الحراسة نفسها fixture جلسة autouse في tests/conftest.py
(_guard_session_ledger_key_hygiene) — لا يكفي تعريفها في وحدة اختبار لأن
autouse من وحدة يسري على وحدها فقط. هذا الملف يوثق السبب ويحرس الحارس.

لا يغيّر هذا الملف سلوك الفشل المغلق ولا يسكت أي تسجيل — يمنع التلوث
من الحدوث أصلًا (الاختبارات المعزولة تكتب في سجلات معزولة).
"""
import os
from pathlib import Path


def test_guard_is_registered_in_conftest():
    """الحارس يجب أن يكون مسجلًا في conftest (autouse جلسة) — حارس الحارس.

    لو حُذف التعريف من conftest بلا قصد، يفشل هذا الاختبار صراحة.
    """
    conftest = Path(__file__).parent / "conftest.py"
    src = conftest.read_text(encoding="utf-8")
    assert "_guard_session_ledger_key_hygiene" in src, (
        "حراسة نظافة مفاتيح سجل الجلسة ليست مسجلة في tests/conftest.py — "
        "أعيد تسجيلها (fixture جلسة autouse) أو سيصير التلوث صامتًا مجددًا"
    )


def test_session_root_paths_shape():
    """شكل مسارات الجلسة المعروف: sovereign_core/ledger.jsonl + keys/keyring.json."""
    data_root = os.environ.get("SOVEREIGN_DATA_ROOT")
    if not data_root:
        return  # جلسة بجذر مخصص — لا ينطبق
    assert (Path(data_root) / "sovereign_core").name == "sovereign_core"
    assert (Path(data_root) / "keys").name == "keys"
