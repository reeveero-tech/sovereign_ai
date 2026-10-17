"""Security regression tests for sovereign-key configuration.

R-615 (المرحلة الثانية — الجريمة الثانية): النسخة السابقة من هذا الاختبار
كانت تحذف data/key.secret الحقيقي مرتين (السطر 37 و54) — أداة جريمة ثانية
اكتُشفت في forensics/KEY_LOSS_TIMELINE.md. الآن الاختبار يعمل في جذر
مؤقت معزول عبر SOVEREIGN_DATA_ROOT (نفس نمط test_identity_persistence.py).
لا يُلمس مفتاح التشغيل الحقيقي إطلاقًا.
"""

import os
import subprocess
import sys
import tempfile


def _run_config(env):
    command = [
        sys.executable,
        "-c",
        "import config; print(config.SOVEREIGN_KEY)",
    ]
    return subprocess.run(
        command,
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
    )


def test_development_without_key_generates_persistent_key():
    """R-610: التطوير بدون مفتاح يولّد مفتاحاً دائماً يُحفظ في data/key.secret.

    الهوية السيادية (ختم الهوية + توقيعات السجل) يجب أن تستمر عبر إعادة التشغيل —
    لذلك المفتاح المولّد يُعاد استخدامه في التشغيل الثاني (نفس القيمة)،
    ولا يُستخدم أي مفتاح افتراضي معروف.

    R-615: عزل فعلي — المفتاح يُنشأ داخل جذر مؤقت (SOVEREIGN_DATA_ROOT)،
    لا يُلمس مفتاح التشغيل الحقيقي.
    """
    # إنشاء جذر مؤقت معزول (نفس نمط test_identity_persistence.py)
    tmp_root = tempfile.mkdtemp(prefix="sovereign_config_test_")
    tmp_data = os.path.join(tmp_root, "data")
    os.makedirs(tmp_data, exist_ok=True)

    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "development"
    # عزل فعلي: config.py سيستخدم tmp_data كـ DATA_DIR
    env["SOVEREIGN_DATA_ROOT"] = tmp_data

    # المفتاح سيُنشأ داخل الجذر المؤقت — لا يُلمس المفتاح الحقيقي
    secret_file = os.path.join(tmp_data, "key.secret")

    first = _run_config(env)
    second = _run_config(env)

    assert first.returncode == 0, f"first config run failed: {first.stderr}"
    assert second.returncode == 0, f"second config run failed: {second.stderr}"
    assert first.stdout.strip()
    assert second.stdout.strip()
    # R-610: المفتاح الدائم يُعاد استخدامه — نفس القيمة عبر عمليات التشغيل
    assert first.stdout.strip() == second.stdout.strip(), (
        "key should be identical across restarts (persistent identity)"
    )
    assert "مفتاح_افتراضي_غير_آمن" not in first.stdout
    # المفتاح الدائم كُتب على القرص (داخل الجذر المؤقت)
    assert os.path.exists(secret_file), (
        f"key.secret should be created in isolated tmp dir {tmp_data}"
    )

    # التحقق من أن المفتاح الحقيقي لم يُلمس (إن كان موجودًا قبل الاختبار)
    # (لو كان موجودًا، ما زال موجودًا — لم نلمسه)
    # (لا نتحقق من المحتوى — سرية)


def test_production_without_key_fails_closed():
    """في الإنتاج، غياب المفتاح يجب أن يمنع التشغيل (فشل مقفل).

    R-615: عزل فعلي — الاختبار يعمل في جذر مؤقت معزول، لا يُلمس المفتاح
    الحقيقي. (بدون العزل، config.py سيجد المفتاح الحقيقي ولن يفشل.)
    """
    tmp_root = tempfile.mkdtemp(prefix="sovereign_prod_test_")
    tmp_data = os.path.join(tmp_root, "data")
    os.makedirs(tmp_data, exist_ok=True)

    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "production"
    # عزل فعلي: المفتاح الحقيقي غير مرئي داخل الجذر المؤقت
    env["SOVEREIGN_DATA_ROOT"] = tmp_data

    result = _run_config(env)

    assert result.returncode != 0, (
        f"production without key should fail (returncode != 0), "
        f"got 0 with key {result.stdout!r}"
    )
    assert "لم يتم تعيين مفتاح السيد" in (result.stderr + result.stdout)


def test_production_with_loose_perm_key_secret_rejected():
    """جولة المجلس <1> (أمين 2.4/بصير BAS-S16/حكيم): في الإنتاج، ملف سر
    مكشوف الأذونات (0644) يُرفض صراحة — لا يُقبل بصمت."""
    tmp_root = tempfile.mkdtemp(prefix="sovereign_loose_perm_test_")
    tmp_data = os.path.join(tmp_root, "data")
    os.makedirs(tmp_data, exist_ok=True)
    key_file = os.path.join(tmp_data, "key.secret")
    with open(key_file, "w", encoding="utf-8") as f:
        f.write("production_key_abcdef0123456789abcdef")
    os.chmod(key_file, 0o644)  # مكشوف للمجموعة والآخرين

    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "production"
    env["SOVEREIGN_DATA_ROOT"] = tmp_data

    result = _run_config(env)
    assert result.returncode != 0, (
        "production with 0644 key.secret must fail closed"
    )
    combined = result.stderr + result.stdout
    assert "أذونات مكشوفة" in combined, (
        f"expected loose-permissions rejection message, got: {combined[-300:]!r}"
    )


def test_production_with_0600_key_secret_loads():
    """الجانب السليم: ملف سر سليم الأذونات (0600) في الإنتاج يُقبل —
    الفشل المغلق لا يعطل التشغيل الصحيح."""
    tmp_root = tempfile.mkdtemp(prefix="sovereign_tight_perm_test_")
    tmp_data = os.path.join(tmp_root, "data")
    os.makedirs(tmp_data, exist_ok=True)
    key_file = os.path.join(tmp_data, "key.secret")
    expected = "production_key_abcdef0123456789abcdef"
    with open(key_file, "w", encoding="utf-8") as f:
        f.write(expected)
    os.chmod(key_file, 0o600)

    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "production"
    env["SOVEREIGN_DATA_ROOT"] = tmp_data

    result = _run_config(env)
    assert result.returncode == 0, (
        f"production with 0600 key.secret must load, stderr: {result.stderr[-300:]!r}"
    )
    assert result.stdout.strip() == expected
