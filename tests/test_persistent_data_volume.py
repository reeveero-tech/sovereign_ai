# -*- coding: utf-8 -*-
"""R-760 (ROADMAP_V5 ١.٣ + ١.٧ — بأمر المالك D-044): قرص دائم لبيانات الإنتاج.

قبل R-760: `/app/data` على قرص الآلة المؤقت — كل نشر يمحو حلقة المفاتيح
(`data/keys/keyring.json`) والسجل السيادي وختم الهوية؛ فمفتاح توقيع يُولَّد في
الإنتاج يضيع مع أول إعادة نشر، والسجل الموقّع به يصير غير قابل للتحقق.

الحل: حجم Fly دائم مركّب على `/app/data`، ونقطة دخول تبدأ جذرًا لتملّك الحجم
(Fly ينشئ الحجم مملوكًا للجذر) ثم **تُسقط الامتياز** إلى المستخدم 1001 قبل
تشغيل التطبيق — التطبيق لا يعمل جذرًا أبدًا.
"""

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRY = REPO_ROOT / "scripts" / "container_entrypoint.sh"
DOCKERFILE = REPO_ROOT / "Dockerfile"
FLY_TOML = REPO_ROOT / "fly.toml"


def test_fly_mounts_persistent_volume_on_data_dir():
    text = FLY_TOML.read_text(encoding="utf-8")
    m = re.search(r"^\[mounts\]\s*\n((?:[ \t]+.*\n)+)", text, re.M)
    assert m, "fly.toml بلا [mounts] — بيانات الإنتاج تضيع مع كل نشر"
    block = m.group(1)
    assert re.search(r"source\s*=\s*'sovereign_data'", block)
    assert re.search(r"destination\s*=\s*'/app/data'", block)


def test_dockerfile_uses_privilege_dropping_entrypoint():
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(r'^ENTRYPOINT \["/app/scripts/container_entrypoint.sh"\]', text, re.M)
    assert "chmod 0755 /app/scripts/container_entrypoint.sh" in text
    # المستخدم غير الجذري ما زال مُنشأ بنفس المعرّف
    assert "--uid 1001" in text


def test_entrypoint_root_branch_always_drops_privileges():
    src = ENTRY.read_text(encoding="utf-8")
    assert src.startswith("#!/bin/sh")
    assert "set -eu" in src
    start = src.index('if [ "$(id -u)" = "0" ]')
    root_branch = src[start:src.index("\nfi\n", start)]
    assert 'chown -R "$APP_UID:$APP_UID" "$DATA_DIR"' in root_branch
    # الفرع الجذري ينتهي حتمًا بـsetpriv — لا exec مباشر للتطبيق كجذر
    execs = re.findall(r"^\s*exec .*$", root_branch, re.M)
    assert execs and all("setpriv --reuid=" in e and "--clear-groups" in e for e in execs)
    assert os.access(ENTRY, os.X_OK), "نقطة الدخول غير قابلة للتنفيذ"


def test_entrypoint_non_root_runs_command_unchanged(tmp_path):
    out = subprocess.run(["sh", str(ENTRY), "sh", "-c", "echo ran:$(id -u)"],
                         env={**os.environ, "SOVEREIGN_CONTAINER_DATA": str(tmp_path / "d")},
                         capture_output=True, text=True, timeout=20)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == f"ran:{os.getuid()}"


def test_entrypoint_fails_closed_when_command_missing(tmp_path):
    out = subprocess.run(["sh", str(ENTRY)], capture_output=True, text=True, timeout=20,
                         env={**os.environ, "SOVEREIGN_CONTAINER_DATA": str(tmp_path / "d")})
    assert out.returncode == 64
    assert "R-760" in out.stderr                         # رفض صريح لا خطأ عرضي
