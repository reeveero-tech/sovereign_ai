# -*- coding: utf-8 -*-
"""R-815 (أمر المالك 2026-10-29 «إحياء كل ما هو ميت»): الحارس المعزول حي في الإنتاج.

قبل R-815: `backend/supervisor_daemon.py` عملية مستقلة كاملة (نبض + مراقبة +
وعي) لكن لا أحد يشغلها في حاوية الإنتاج — نقطة الدخول كانت تشغّل التطبيق فقط،
فنبض الحارس غائب دائمًا (العيب `supervisor_heartbeat_missing` — الوحيد المفتوح
في defects.scan على الإنتاج الحي، 42 رصدًا متتاليًا). ملف الخدمة وcompose
كانا للجهاز المحلي فقط — «غير منجز: تفعيل الحارس كخدمة» في PROJECT_STATE.

بعد R-815: عند ضبط `SOVEREIGN_SUPERVISOR=1` تُطلق نقطة الدخول الحارس كعملية
مرافقة كمستخدم التطبيق (لا جذر) قبل تنفيذ أمر التطبيق. العقد R-687 محفوظ:
لا استيراد متبادل ولا مشاركة عملية — الحارس يراقب عبر HTTP فقط. وموت الحارس
لا يوقف الإقلاع أبدًا (الإطلاق best-effort بلا set -e داخل المسار).
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRY = REPO_ROOT / "scripts" / "container_entrypoint.sh"
FLY_TOML = REPO_ROOT / "fly.toml"


def test_entrypoint_has_gated_supervisor_launch():
    src = ENTRY.read_text(encoding="utf-8")
    # البوابة الصارمة: لا إطلاق إلا بقرار صريح من البيئة
    assert '[ "${SOVEREIGN_SUPERVISOR:-0}" = "1" ]' in src
    # أمر الحارس نفسه: الوحدة الحقيقية + العنوان الداخلي + الفاصل المضبوط
    assert re.search(
        r"SUP_CMD=\"cd '\$\{APP_ROOT\}' && nohup python3 -m backend\.supervisor_daemon "
        r"--url 'http://127\.0\.0\.1:\$\{PORT:-8080\}' "
        r"--interval '\$\{SOVEREIGN_SUPERVISOR_INTERVAL:-30\}'", src), \
        "أمر إطلاق الحارس ناقص (وحدة/عنوان/فاصل)"
    # جذر → امتياز مسقوط للحارس أيضًا (لا عملية جذر أبدًا)؛ غير جذر → مباشرة
    assert re.search(
        r"setpriv --reuid=\"\$APP_UID\" --regid=\"\$APP_UID\" --clear-groups -- \\\n"
        r"\s*sh -c \"\$SUP_CMD\" \|\| true", src), \
        "الحارس يُطلق جذرًا أو بلا setpriv — مخالفة R-760"
    assert re.search(r"\n\s*sh -c \"\$SUP_CMD\" \|\| true", src), \
        "تشغيل غير جذري (--user) بلا إطلاق الحارس — الحارس يموت معه"
    # الفاصل الافتراضي داخل النطاق (0، 60] الذي يقبله /n
    assert "SOVEREIGN_SUPERVISOR_INTERVAL:-30" in src
    # فشل الإطلاق لا يوقف التطبيق — best-effort صريح في الفرعين
    assert src.count('sh -c "$SUP_CMD" || true') == 2, \
        "موت الحارس يجب ألا يوقف الإقلاع (best-effort)"
    # لا عنوان خاص في نقطة الدخول — العنوان الداخلي للتطبيق فقط
    assert "127.0.0.1" in src and not re.search(r"192\.168\.", src)


def test_fly_toml_enables_supervisor_sidecar():
    text = FLY_TOML.read_text(encoding="utf-8")
    assert re.search(r"^  SOVEREIGN_SUPERVISOR = '1'$", text, re.M), \
        "الإنتاج لا يفعّل الحارس المرافق — النبض سيبقى غائبًا"
    assert re.search(r"^  SOVEREIGN_SUPERVISOR_INTERVAL = '30'$", text, re.M)


def test_supervisor_interval_within_accepted_heartbeat_range(tmp_path, monkeypatch):
    """فاصل الحارس 30ث داخل النطاق (0، 60] — خارجه يُعدّ /n النبض تالفًا."""
    import config
    from app import _load_heartbeat

    p = tmp_path / "supervisor" / "status.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(
        {"epoch": time.time(), "interval": 30.0, "active_alerts": 0}),
        encoding="utf-8")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    hb = _load_heartbeat()
    assert hb is not None and hb["interval"] == 30.0


def _fake_python(tmp_path: Path, marker: Path) -> Path:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    fake_py = fake_bin / "python3"
    fake_py.write_text(
        "#!/bin/sh\n"
        'echo "args=$*" >> "' + str(marker) + '"\n'
        'while [ ! -f "' + str(tmp_path / "stop") + '" ]; do sleep 0.2; done\n',
        encoding="utf-8")
    fake_py.chmod(0o755)
    return fake_bin


def test_entrypoint_launches_supervisor_when_enabled(tmp_path):
    """سلوكي: مع SOVEREIGN_SUPERVISOR=1 تُطلق نقطة الدخول الحارس المرافق فعلًا.

    يُستبدل python3 ببرنامج وهمي يكتب علامة — الإثبات أن نقطة الدخول تمرر
    الوسائط الصحيحة (الوحدة والعنوان الداخلي) وتُبقي التطبيق يعمل.
    """
    app_root = tmp_path / "app"
    (app_root / "backend").mkdir(parents=True)
    (app_root / "backend" / "supervisor_daemon.py").write_text("# fake\n", encoding="utf-8")
    marker = tmp_path / "launched.txt"
    fake_bin = _fake_python(tmp_path, marker)
    data_dir = tmp_path / "data"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "SOVEREIGN_SUPERVISOR": "1",
        "SOVEREIGN_APP_ROOT": str(app_root),
        "SOVEREIGN_CONTAINER_DATA": str(data_dir),
        "SOVEREIGN_SUPERVISOR_INTERVAL": "30",
        "PORT": "8080",
    }
    try:
        out = subprocess.run(
            ["sh", str(ENTRY), "sh", "-c", "echo app-ran"],
            env=env, capture_output=True, text=True, timeout=30)
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == "app-ran", "التطبيق نفسه توقف — ممنوع"
        for _ in range(50):  # الكتابة قد تسبق عودة نقطة الدخول — مهلة قصيرة
            if marker.exists():
                break
            time.sleep(0.1)
        assert marker.exists(), "الحارس لم يُطلق مع SOVEREIGN_SUPERVISOR=1"
        launched = marker.read_text(encoding="utf-8")
        assert "-m backend.supervisor_daemon" in launched
        assert "--url http://127.0.0.1:8080" in launched
        assert "--interval 30" in launched
        # سجل الحارس داخل جذر البيانات الدائم — يبقى عبر إعادة النشر
        assert (data_dir / "supervisor").is_dir()
    finally:
        (tmp_path / "stop").write_text("x", encoding="utf-8")


def _fake_root_tools(tmp_path: Path) -> Path:
    """أدوات وهمية لدخول فرع الجذر بلا جذر فعلي: id يُبلغ 0، وchown يسجّل
    استدعاءاته (عقد الإصلاح R-815b)، وsetpriv ينفّذ أمره مباشرة بلا إسقاط
    امتياز حقيقي (المستخدم واحد أصلًا في بيئة الاختبار)."""
    fake_bin = tmp_path / "rbin"
    fake_bin.mkdir(exist_ok=True)
    (fake_bin / "id").write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-u" ]; then echo 0; exit 0; fi\n'
        'exec /usr/bin/id "$@"\n', encoding="utf-8")
    (fake_bin / "chown").write_text(
        "#!/bin/sh\n"
        'echo "chown $*" >> "' + str(tmp_path / "chown_log.txt") + '"\n'
        "exit 0\n", encoding="utf-8")
    (fake_bin / "setpriv").write_text(
        "#!/bin/sh\n"
        'while [ "$1" != "--" ] && [ $# -gt 0 ]; do shift; done\n'
        '[ $# -gt 0 ] && shift\n'
        'exec "$@"\n', encoding="utf-8")
    for name in ("id", "chown", "setpriv"):
        (fake_bin / name).chmod(0o755)
    return fake_bin


def test_entrypoint_chowns_supervisor_dir_when_root(tmp_path):
    """R-815b (درس النشر الأول): في فرع الجذر يُنشأ مجلد الحارس بعد تملّك جذر
    البيانات — بلا تملّكٍ للمجلد الجديد تفشل إعادة توجيه سجل الحارس (بمستخدم
    التطبيق) قبل انطلاقه، فيغيب النبض كليًا رغم نجاح الفحوص. العقد: قبل الإطلاق
    يُملَّك المجلد لمستخدم التطبيق صراحةً، والإطلاق نفسه ينجح (السجل يُنشأ)."""
    app_root = tmp_path / "app"
    (app_root / "backend").mkdir(parents=True)
    (app_root / "backend" / "supervisor_daemon.py").write_text("# fake\n", encoding="utf-8")
    marker = tmp_path / "launched.txt"
    fake_bin = _fake_python(tmp_path, marker)
    root_bin = _fake_root_tools(tmp_path)
    data_dir = tmp_path / "data"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{root_bin}:{os.environ['PATH']}",
        "SOVEREIGN_SUPERVISOR": "1",
        "SOVEREIGN_APP_ROOT": str(app_root),
        "SOVEREIGN_CONTAINER_DATA": str(data_dir),
        "SOVEREIGN_SUPERVISOR_INTERVAL": "30",
        "PORT": "8080",
    }
    try:
        out = subprocess.run(
            ["sh", str(ENTRY), "sh", "-c", "echo app-ran"],
            env=env, capture_output=True, text=True, timeout=30)
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == "app-ran", "التطبيق نفسه توقف — ممنوع"
        # عقد R-815b: تملّك مجلد الحارس لمستخدم التطبيق قبل الإطلاق
        chown_log = (tmp_path / "chown_log.txt").read_text(encoding="utf-8")
        assert "1001:1001" in chown_log, "لا تملّيك لمستخدم التطبيق — النشر الأول سيتكرر"
        assert str(data_dir / "supervisor") in chown_log, \
            "التملّيك لا يستهدف مجلد الحارس"
        for _ in range(50):
            if marker.exists():
                break
            time.sleep(0.1)
        assert marker.exists(), "الحارس لم يُطلق رغم التملّيك — فرع الجذر مكسور"
        # إعادة توجيه السجل نجحت فعلًا (هي التي كانت تفشل قبل R-815b)
        assert (data_dir / "supervisor" / "supervisor_stdout.log").exists(), \
            "سجل الحارس لم يُنشأ — الإطلاق بلا كتابة سجل"
    finally:
        (tmp_path / "stop").write_text("x", encoding="utf-8")


def test_supervisor_dir_unwritable_keeps_app_alive(tmp_path):
    """توثيق نمط الفشل الصامت: مجلد حارس غير قابل للكتابة لمستخدم التطبيق يجعل
    الإطلاق يفشل بصمت (لا علامة إطلاق ولا سجل) — لكن الإقلاق نفسه لا يتوقف
    أبدًا (best-effort). هذا هو سبب فحص النبض الحي في سير النشر (R-815b)."""
    app_root = tmp_path / "app"
    (app_root / "backend").mkdir(parents=True)
    (app_root / "backend" / "supervisor_daemon.py").write_text("# fake\n", encoding="utf-8")
    marker = tmp_path / "launched.txt"
    fake_bin = _fake_python(tmp_path, marker)
    data_dir = tmp_path / "data"
    (data_dir / "supervisor").mkdir(parents=True)
    (data_dir / "supervisor").chmod(0o555)  # موجود لكن غير قابل للكتابة
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "SOVEREIGN_SUPERVISOR": "1",
        "SOVEREIGN_APP_ROOT": str(app_root),
        "SOVEREIGN_CONTAINER_DATA": str(data_dir),
        "SOVEREIGN_SUPERVISOR_INTERVAL": "30",
        "PORT": "8080",
    }
    try:
        out = subprocess.run(
            ["sh", str(ENTRY), "sh", "-c", "echo app-ran"],
            env=env, capture_output=True, text=True, timeout=30)
        # التطبيق نجح رغم فشل إطلاق الحارس — الإقلاع لا يتوقف أبدًا
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == "app-ran"
        time.sleep(0.8)
        assert not marker.exists(), \
            "إطلاق في مجلد غير قابل للكتابة — نمط الفشل تغير (حدّث الاختبار)"
        assert not (data_dir / "supervisor" / "supervisor_stdout.log").exists(), \
            "السجل كُتب رغم منع الكتابة — الفرضية خاطئة"
    finally:
        (tmp_path / "stop").write_text("x", encoding="utf-8")


def test_entrypoint_skips_supervisor_when_disabled(tmp_path):
    """الافتراضي المحلي: بلا SOVEREIGN_SUPERVISOR لا يُطلق شيء — سلوك R-760 كما كان."""
    marker = tmp_path / "launched.txt"
    fake_bin = _fake_python(tmp_path, marker)
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "SOVEREIGN_APP_ROOT": str(tmp_path / "app"),
        "SOVEREIGN_CONTAINER_DATA": str(tmp_path / "data"),
    }
    out = subprocess.run(
        ["sh", str(ENTRY), "sh", "-c", "echo app-ran"],
        env=env, capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "app-ran"
    time.sleep(0.6)
    assert not marker.exists(), "إطلاق بلا قرار صريح من البيئة — مخالفة"
