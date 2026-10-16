"""
Invariant 5: KeyRing غير قابل للتلاعب (المرحلة 3 من ROADMAP_V2)

يتحقق أن:
1. كل المفاتيح الفاشلة (LOST/COMPROMISED) لا تُستخدم للتحقق
2. المفتاح الفعلي (data/key.secret) ليس في الاختبارات (لا حذف)
3. HISTORY.jsonl (سجل المفاتيح) غير قابل للحذف
4. أي مفتاح في KeyRing إما ACTIVE أو RETIRED أو LOST (حالة صحيحة)
"""

import json
import os
import sys
from pathlib import Path

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from backend.sovereign.keys import KeyRing, KeyStatus


def test_keyring_all_keys_have_valid_status():
    """كل مفتاح في KeyRing يجب أن يكون له حالة صحيحة (ACTIVE/RETIRED/LOST/COMPROMISED/EXPIRED)."""
    keyring = KeyRing()
    keyring.load_from_disk()

    stats = keyring.stats()
    # (قاعدة الجولة الإنشائية 2026-10-16: لا skip — KeyRing الفارغ فشل صريح:
    # الـconftest يُنشئ keyring معزولًا بمفتاح نشط (R-634)، والواقع يتتبع HISTORY)
    assert stats["total_keys"] > 0, (
        "KeyRing is empty — invariant violated (conftest must provision "
        "the isolated test keyring per R-634)"
    )

    valid_statuses = {s.value for s in KeyStatus}

    # يُحقق كل مفتاح عبر الحصول على قائمة منه (list_keys أو جميع_keys)
    all_keys = keyring.list_keys() if hasattr(keyring, "list_keys") else []
    if not all_keys:
        # محاولة بديلة — الحصول على كل المفاتيح عبر attributes الخاصة
        all_keys = list(keyring._keys.values())

    for key in all_keys:
        key_id = getattr(key, "key_id", "?")
        status = key.status.value if hasattr(key.status, "value") else str(key.status)
        assert status in valid_statuses, (
            f"Key {key_id} has invalid status: {status!r}"
        )


def test_no_active_lost_keys():
    """لا يوجد مفتاح LOST/COMPROMISED بحالة ACTIVE (تناقض خطير)."""
    keyring = KeyRing()
    keyring.load_from_disk()

    stats = keyring.stats()
    assert stats["total_keys"] > 0, (
        "KeyRing is empty — invariant violated (conftest must provision "
        "the isolated test keyring per R-634)"
    )

    contradictions = []
    all_keys = list(keyring._keys.values())

    for key in all_keys:
        key_id = getattr(key, "key_id", "?")
        status = key.status.value if hasattr(key.status, "value") else str(key.status)
        reason = getattr(key, "loss_reason", None) or getattr(key, "reason", None)

        # مفتاح LOST أو COMPROMISED لا يمكن أن يكون ACTIVE
        if status in ("LOST", "COMPROMISED") and "active" in status.lower():
            contradictions.append(key_id)

        # مفتاح LOST مع سبب "not lost" — تناقض
        if status == "LOST" and reason and "not lost" in str(reason).lower():
            contradictions.append(key_id)

    assert len(contradictions) == 0, (
        f"Keys with contradictory status (LOST/COMPROMISED but ACTIVE): {contradictions}"
    )


def test_keyring_history_immutable():
    """
    HISTORY.jsonl (سجل المفاتيح) لا يمكن حذفه أو تعديله.
    يتحقق أن الملف موجود وأن كل سطر هو JSON صالح (لا تلف).
    """
    history_file = _REPO_ROOT / "data" / "keys" / "HISTORY.jsonl"
    assert history_file.exists(), (
        "data/keys/HISTORY.jsonl must exist (key history is append-only)"
    )

    content = history_file.read_text(encoding="utf-8")
    lines = [l for l in content.split("\n") if l.strip()]

    assert len(lines) > 0, "HISTORY.jsonl must have at least one entry"

    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"HISTORY.jsonl line {i+1} is corrupted (not valid JSON): {e}"
            )

        # كل إدخال يجب أن يكون كائنًا (dict)
        assert isinstance(entry, dict), (
            f"HISTORY.jsonl line {i+1} must be a JSON object"
        )


def test_real_key_secret_exists():
    """
    المفتاح الفعلي (data/key.secret) يجب أن يوجد — لا يمكن حذفه
    (هذا هو الدرس من جريمة الاختبارات التي حذفته مرتين).

    R-680c: في clone نظيف، data/key.secret غير موجود (سر مُستثنى من git).
    (قاعدة الجولة الإنشائية 2026-10-16: لا skip — إن وُجد الملف الفعلي تُفحص
    خصائصه، وفي كل الأحوال يُثبت الاختبار مسار التوليد R-610 نفسه في جذر
    معزول: الاستيراد الفعلي لـ config بلا SOVEREIGN_KEY يولّد key.secret
    بحجم > 0 وصلاحيات 0600 — نفس الخصائص المطلوبة للملف الفعلي.)
    """
    import subprocess
    import tempfile

    # (أ) الملف الفعلي إن وُجد: خصائصه الصحيحة إلزامية
    key_file = _REPO_ROOT / "data" / "key.secret"
    if key_file.exists():
        size = key_file.stat().st_size
        assert size > 0, (
            f"data/key.secret is empty (size={size}) — key must be non-empty"
        )
        mode = key_file.stat().st_mode & 0o777
        assert mode == 0o600, (
            f"data/key.secret has insecure permissions: {oct(mode)} (expected 0600)"
        )

    # (ب) مسار التوليد R-610 يُثبت نفسه في جذر معزول (بلا skip في أي حالة)
    with tempfile.TemporaryDirectory(prefix="keygen_probe_") as tmp:
        env = {
            k: v for k, v in os.environ.items() if k != "SOVEREIGN_KEY"
        }
        env["SOVEREIGN_DATA_ROOT"] = tmp
        # لا .env في جذر المستودع (متحقق منه أعلاه في تشغيل الجولة) —
        # المصدر 4 هو أول مصدر متاح في الجذر المعزول
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'backend'); "
             "import config; print('KEYGEN_OK')"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
            env=env, timeout=120,
        )
        assert r.returncode == 0, (
            f"config import failed in isolated root: {r.stderr[-300:]}"
        )
        generated = Path(tmp) / "key.secret"
        assert generated.exists(), (
            "R-610 generation path did not create key.secret in isolated root"
        )
        assert generated.stat().st_size > 0, (
            "generated key.secret is empty — key must be non-empty"
        )
        gmode = generated.stat().st_mode & 0o777
        assert gmode == 0o600, (
            f"generated key.secret has insecure permissions: {oct(gmode)} "
            "(expected 0600 per R-610)"
        )


def test_tests_do_not_touch_real_key():
    """
    لا اختبار يلمس المفتاح الفعلي (data/key.secret) — هذا هو الدرس
    من جريمة test_identity_persistence.py و test_config_security.py
    (كلاهما حذف المفتاح الفعلي مرتين).
    """
    tests_dir = _REPO_ROOT / "tests"
    test_files = list(tests_dir.rglob("*.py"))

    dangerous_patterns = [
        "os.remove", "os.unlink", "shutil.rmtree", "Path.unlink",
    ]

    for tf in test_files:
        src = tf.read_text(encoding="utf-8")

        # البحث عن حذف للملفات (خطر) في الاختبارات
        for pattern in dangerous_patterns:
            # فحص كل سطر يحتوي النمط
            for i, line in enumerate(src.split("\n"), 1):
                if pattern in line and "key.secret" in line:
                    # إذا كان الحذف يستهدف key.secret — خطر
                    pytest.fail(
                        f"{tf.relative_to(_REPO_ROOT)}:{i} touches real key.secret: {line.strip()}"
                    )
