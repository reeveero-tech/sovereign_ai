#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""غلاف البوابة الموثوق (تصويب المراجع — الجولة 3).

الترتيب الصارم: التقاط بصمة محتوى الكود والاختبارات قبل pytest → تشغيل
البوابة بالأمر الفعلي (نفس verify.sh: --junit-prefix) → مقارنة البصمة —
إن تغيرت الشجرة يُرفض الختم (لا يُختم تقرير قديم ببصمة جديدة) → ختم
التقرير بالبصمة الملتقطة → توثيق الفعل كاملًا عبر run_logged (الأمر، رمز
الخروج، الهوية، وقت البدء والنهاية).
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from backend.sovereign.score import _v2_content_fingerprint, seal_junit_identity  # noqa: E402
from tools.action_log import run_logged  # noqa: E402

def _gate_cmd() -> list:
    """أمر البوابة الفعلي — نفس verify.sh: البادئة SHA حقيقي وقت التشغيل."""
    import subprocess
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    ).stdout.strip()
    # نفس أمر verify.sh حرفيًا (المسار الموحد)
    return [
        sys.executable, "-m", "pytest", "tests/", "backend/tests/",
        "-q", "-m", "not operational",
        "--junitxml=forensics/pytest_results.xml",
        f"--junit-prefix=R-682-sha-{head}",
    ]


GATE_CMD = _gate_cmd()


def run_gate(junit_path: str = "forensics/pytest_results.xml") -> dict:
    captured = _v2_content_fingerprint(REPO_ROOT)

    def _run():
        r = subprocess.run(GATE_CMD, capture_output=True, text=True,
                           cwd=str(REPO_ROOT), timeout=1800)
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        outcome = {
            "command": " ".join(GATE_CMD),
            "exit_code": r.returncode,
            "tail": tail,
        }
        if r.returncode != 0:
            raise RuntimeError(f"gate failed (exit {r.returncode}): {tail}")
        # الختم المشروط: البصمة الملتقطة قبل التشغيل فقط — إن تغيرت
        # الشجرة منذ الالتقاط يُرفض الختم
        ident = seal_junit_identity(REPO_ROOT / junit_path, REPO_ROOT, captured)
        outcome["identity"] = ident
        return outcome

    result, rec = run_logged(
        "بوابة الحزمة الكاملة بالأمر الفعلي (junit-prefix) + ختم البصمة الملتقطة قبل التشغيل",
        [junit_path],
        _run,
    )
    return result, rec


if __name__ == "__main__":
    outcome, record = run_gate()
    print("GATE OK:", outcome["tail"])
    print("identity:", outcome["identity"])
