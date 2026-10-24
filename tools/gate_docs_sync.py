#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس D-040 المقوى (R-748 — بأمر المالك 2026-10-24 «القاعدة الحاكمة»).

القاعدة الحرفية للمالك: «لا دفع إلى المستودع ولا عمل فيه إلا بتوثيق …
تحدث خارطة الطريق وحالة المشروع ووثائقه بما تم عمله … ولكن لا يتم ذلك بعد
دفع العمل ولكن معه — العمل يدفع وفي نفس الدفعة يدفع التوثيق وليس منفصلًا».

التطبيق الواحد للحارس — تستدعيه:
  1) بوابة CI (ci.yml) عند الدفع وعند PR — على الالتزام/المدى.
  2) الـ pre-commit المحلي (.githooks/pre-commit) على الفهرس قبل الالتزام.
  3) اختباره السلوكي (tests/test_gate_docs_sync.py) عبر مستودعات مؤقتة.

ما كان قبله (الفجوة الموثقة في R-748): البوابة القديمة كانت تقبل أي ملف تحت
docs/ أو forensics/ — حتى لو لم تُحدَّث خارطة الطريق ولا حالة المشروع ولا
سجل التغييرات. المعنى الحرفي لأمر المالك أضيق: أي تغيير كود يلزمه في نفس
الالتزام تحديث الثلاثة:
  - docs/PROJECT_STATE.md   (حالة المشروع)
  - docs/CHANGELOG.md       (سجل التغييرات — مصدر الحقيقة GOVERNANCE §9)
  - docs/ROADMAP*.md        (خارطة الطريق النشطة — واحد على الأقل)

الاستخدام:
  python tools/gate_docs_sync.py [SHA]          # فحص التزام (الافتراضي HEAD)
  python tools/gate_docs_sync.py --staged       # فحص الفهرس (pre-commit)
  python tools/gate_docs_sync.py --diff BASE HEAD   # فحص مدى (بوابة PR)

رمز الخروج: 0 = مطابق، 1 = مخالفة القاعدة. stdlib خالص.
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys

# بادئات «الكود» — اتحاد قائمتي بوابة الدفع وبوابة PR القديمتين
CODE_PREFIXES = (
    "backend/", "frontend/", "tools/", "tests/", ".github/", "nexus/",
    "guardian/", "main.py", "start.sh", "Dockerfile",
    "fly.toml", "verify.sh", "requirements.txt", "pytest.ini",
)

# الوثائق الثلاثة المطلوبة حرفيًا بأمر المالك — الخارطة بأي إصدار
REQUIRED_DOCS = ("docs/PROJECT_STATE.md", "docs/CHANGELOG.md")
ROADMAP_GLOB = "docs/ROADMAP*.md"


def _git(args: list[str]) -> str:
    out = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False)
    if out.returncode != 0:
        sys.stderr.write(f"git {' '.join(args)} فشل: {out.stderr.strip()}\n")
        sys.exit(2)
    return out.stdout


def _is_code(path: str) -> bool:
    return path.startswith(CODE_PREFIXES)


def _merge_commit(sha: str) -> bool:
    parents = _git(["rev-list", "--parents", "-n", "1", sha]).split()
    return len(parents) > 2


def _files_of_commit(sha: str) -> list[str]:
    if _merge_commit(sha):
        return []  # الالتزامات الدمجية تُفحص بمعايير خاصة عند وقوعها
    return [l.strip() for l in
            _git(["show", "--name-only", "--format=", sha]).splitlines()
            if l.strip()]


def _files_staged() -> list[str]:
    return [l.strip() for l in
            _git(["diff", "--cached", "--name-only"]).splitlines() if l.strip()]


def _files_of_range(base: str, head: str) -> list[str]:
    return [l.strip() for l in
            _git(["diff", "--name-only", base, head]).splitlines() if l.strip()]


def check_files(files: list[str], origin: str) -> int:
    """الفحص الواحد لقائمة ملفات متغيرة — يعيد رمز الخروج المناسب."""
    code = [f for f in files if _is_code(f)]
    if not code:
        print(f"✅ [{origin}] لا تغييرات كود — لا يلزم توثيق (D-040)")
        return 0

    missing = [d for d in REQUIRED_DOCS if d not in files]
    roadmaps = [f for f in files if fnmatch.fnmatch(f, ROADMAP_GLOB)]
    if roadmaps:
        print(f"✅ [{origin}] خارطة الطريق محدثة: {roadmaps[0]}")
    else:
        missing.append(ROADMAP_GLOB)

    if missing:
        print(f"❌ [D-040 — القاعدة الحاكمة بأمر المالك] الالتزام/الدفعة يغيّر "
              f"كودًا ({len(code)} ملفًا: {code[:3]}...) دون تحديث المطلوب "
              "حرفيًا في نفس الدفعة:")
        for m in missing:
            print(f"   - ناقص: {m}")
        print("القاعدة: أي تغيير كود يلزمه تحديث حالة المشروع وسجل التغييرات "
              "وخارطة الطريق النشطة في نفس الالتزام — لا دفعة توثيق منفصلة.")
        return 1

    print(f"✅ [{origin}] الدفعة ذرية: كود ({len(code)} ملفًا) + "
          "PROJECT_STATE + CHANGELOG + خارطة الطريق في نفس الالتزام (D-040)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "--diff":
        files = _files_of_range(argv[1], argv[2])
        return check_files(files, f"مدى {argv[1]}..{argv[2]}")
    if argv and argv[0] == "--staged":
        return check_files(_files_staged(), "الفهرس (pre-commit)")
    sha = argv[0] if argv else "HEAD"
    return check_files(_files_of_commit(sha), f"التزام {sha}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
