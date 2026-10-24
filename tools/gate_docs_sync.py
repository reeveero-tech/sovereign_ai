#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس D-040 المقوى (R-748/R-749 — بأمر المالك 2026-10-24 «القاعدة الحاكمة»).

القاعدة الحرفية للمالك: «لا دفع إلى المستودع ولا عمل فيه إلا بتوثيق …
تحدث خارطة الطريق وحالة المشروع ووثائقه بما تم عمله … ولكن لا يتم ذلك بعد
دفع العمل ولكن معه — العمل يدفع وفي نفس الدفعة يدفع التوثيق وليس منفصلًا».

التطبيق الواحد للحارس — تستدعيه:
  1) بوابة CI (ci.yml) عند الدفع (`--range` على مدى الدفعة) وعند PR
     (`--range` على التزامات PR واحدًا واحدًا) — على الالتزامات لا مجموعها.
  2) الـ pre-commit المحلي (.githooks/pre-commit) على الفهرس قبل الالتزام.
  3) اختباره السلوكي (tests/test_gate_docs_sync.py) عبر مستودعات مؤقتة.

R-749 (تصويب فجوات التغطية التي أظهرتها المراجعة):
  - «نفس الالتزام» تعني كل التزام كود يحمل وثائقه بنفسه — دفعة دفع متعددة
    الالتزامات تُفحص التزامًا التزامًا (`--range`)، لا فحص الرأس وحده ولا
    تجميع مدى الدفعة (كود في التزام ووثائق في التزام آخر = مخالفة).
  - الخارطة المطلوبة هي **النشطة** — المشار إليها بمؤشر
    `docs/ROADMAP_ACTIVE.txt` (تحديث خارطة قديمة لا يبرر)؛ بغياب المؤشر
    يُقبل أي `docs/ROADMAP*.md` (توافق رجعي موثق).
  - حذف وثيقة مطلوبة ليس «تحديثًا» — العد على الحالات A/M فقط.
  - بادئات الكود تشمل `scripts/` و`.githooks/`.

الاستخدام:
  python tools/gate_docs_sync.py [SHA]              # فحص التزام (الافتراضي HEAD)
  python tools/gate_docs_sync.py --staged           # فحص الفهرس (pre-commit)
  python tools/gate_docs_sync.py --diff BASE HEAD   # تجميع مدى (قديم — أضعف)
  python tools/gate_docs_sync.py --range BASE HEAD # فحص كل التزام في المدى

رمز الخروج: 0 = مطابق، 1 = مخالفة القاعدة، 2 = خلل تنفيذ. stdlib خالص.
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys

# بادئات «الكود» — اتحاد قائمتي بوابة الدفع وبوابة PR القديمتين + R-749
CODE_PREFIXES = (
    "backend/", "frontend/", "tools/", "tests/", ".github/", "nexus/",
    "guardian/", "scripts/", ".githooks/",
    "main.py", "start.sh", "Dockerfile",
    "fly.toml", "verify.sh", "requirements.txt", "pytest.ini",
)

# الوثائق المطلوبة حرفيًا بأمر المالك
REQUIRED_DOCS = ("docs/PROJECT_STATE.md", "docs/CHANGELOG.md")
ROADMAP_GLOB = "docs/ROADMAP*.md"
ACTIVE_ROADMAP_POINTER = "docs/ROADMAP_ACTIVE.txt"

# حالات git التي تُعد تحديثًا (إضافة/تعديل) — الحذف D ليس تحديثًا
_UPDATE_STATUSES = {"A", "M", "C", "R"}


def _git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    out = subprocess.run(["git", *args], capture_output=True, text=True,
                        check=False)
    if check and out.returncode != 0:
        sys.stderr.write(f"git {' '.join(args)} فشل: {out.stderr.strip()}\n")
        sys.exit(2)
    return out


def _is_code(path: str) -> bool:
    return path.startswith(CODE_PREFIXES)


def _merge_commit(sha: str) -> bool:
    parents = _git(["rev-list", "--parents", "-n", "1", sha]).stdout.split()
    return len(parents) > 2


def _changed_files(sha: str) -> list[tuple[str, str]]:
    """قائمة (الحالة، المسار) لالتزام — من --name-status."""
    out = _git(["show", "--name-status", "--format=", sha]).stdout
    files = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0]:
            continue
        status = parts[0][0]  # R100 → R
        path = parts[-1].strip()  # rename: آخر حقل هو المسار الجديد
        if path:
            files.append((status, path))
    return files


def _files_of_commit(sha: str) -> list[tuple[str, str]]:
    if _merge_commit(sha):
        return []  # الالتزامات الدمجية تُفحص بمعايير خاصة عند وقوعها
    return _changed_files(sha)


def _staged_files() -> list[tuple[str, str]]:
    out = _git(["diff", "--cached", "--name-status"]).stdout
    files = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0]:
            continue
        files.append((parts[0][0], parts[-1].strip()))
    return files


def _active_roadmap(ref: str) -> str | None:
    """الخارطة النشطة من مؤشر ROADMAP_ACTIVE.txt عند مرجع (SHA أو : للفهرس).
    غياب المؤشر → None (توافق رجعي: أي ROADMAP*.md).
    تصويب R-749-ب: مرجع الفهرس هو «:» — صيغة git للمسار في الفهرس
    «:مسار» لا «::مسار» (الأخيرة فاشلة بصمت فكانت تسقط شرط الخارطة النشطة
    في وضع --staged)."""
    spec = (
        f":{ACTIVE_ROADMAP_POINTER}" if ref == ":"
        else f"{ref}:{ACTIVE_ROADMAP_POINTER}"
    )
    out = _git(["show", spec], check=False)
    if out.returncode != 0:
        return None
    for line in out.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def _roadmap_requirements(files: list[tuple[str, str]], ref: str) -> list[str]:
    """قائمة مطالب الخارطة المقبولة (اسم ملف يُعد تحديثًا مقبولًا)."""
    active = _active_roadmap(ref)
    if active is None:
        return [ROADMAP_GLOB]  # توافق رجعي: أي خارطة
    return [active]


def check_files(files: list[tuple[str, str]], origin: str, ref: str = "HEAD") -> int:
    """الفحص الواحد لقائمة (حالة، مسار) متغيرة — يعيد رمز الخروج المناسب."""
    all_paths = [p for _, p in files]
    code = [p for _, p in files if _is_code(p)]
    if not code:
        print(f"✅ [{origin}] لا تغييرات كود — لا يلزم توثيق (D-040)")
        return 0

    updated = {p for s, p in files if s in _UPDATE_STATUSES}

    missing = [d for d in REQUIRED_DOCS if d not in updated]

    roadmaps = _roadmap_requirements(files, ref)
    ok_roadmap = any(
        (fnmatch.fnmatch(p, pat) if pat == ROADMAP_GLOB else p == pat)
        and p in updated
        for p in all_paths
        for pat in roadmaps
    )
    if ok_roadmap:
        matched = next(
            p for p in all_paths
            for pat in roadmaps
            if (fnmatch.fnmatch(p, pat) if pat == ROADMAP_GLOB else p == pat)
            and p in updated
        )
        print(f"✅ [{origin}] خارطة الطريق النشطة محدثة: {matched}")
    else:
        missing.append(roadmaps[0])

    if missing:
        print(f"❌ [D-040 — القاعدة الحاكمة بأمر المالك] {'الالتزام/الدفعة' if 'التزام' in origin or 'المدى' not in origin else 'الالتزام'} "
              f"[{origin}] يغيّر كودًا ({len(code)} ملفًا: {code[:3]}...) "
              "دون تحديث المطلوب حرفيًا في نفس الالتزام:")
        for m in missing:
            print(f"   - ناقص: {m}")
        print("القاعدة: أي تغيير كود يلزمه تحديث حالة المشروع وسجل التغييرات "
              "وخارطة الطريق النشطة في نفس الالتزام — لا دفعة توثيق منفصلة.")
        return 1

    print(f"✅ [{origin}] الدفعة ذرية: كود ({len(code)} ملفًا) + "
          "PROJECT_STATE + CHANGELOG + خارطة الطريق في نفس الالتزام (D-040)")
    return 0


def check_commit(sha: str) -> int:
    files = _files_of_commit(sha)
    if not files:
        print(f"✅ [{sha[:7]}] لا ملفات متغيرة (دمجي؟) — لا يلزم توثيق (D-040)")
        return 0
    return check_files(files, f"التزام {sha[:7]}", ref=sha)


def check_range(base: str, head: str) -> int:
    """القاعدة الحرفية على مستوى المدى: كل التزام كود يحمل وثائقه بنفسه."""
    revs = _git(["rev-list", "--reverse", f"{base}..{head}"]).stdout.split()
    if not revs:
        # مدى فارغ (نفس الالتزام؟) — افحص الرأس
        return check_commit(head)
    bad = 0
    for sha in revs:
        files = _files_of_commit(sha)
        if not files:
            print(f"⏭️ [{sha[:7]}] دمجي/فارغ — يُفحص بمعايير خاصة عند وقوعه")
            continue
        all_paths = [p for _, p in files]
        code = [p for _, p in files if _is_code(p)]
        if not code:
            print(f"✅ [{sha[:7]}] لا كود — يمر")
            continue
        rc = check_files(files, f"التزام {sha[:7]} داخل المدى", ref=sha)
        if rc != 0:
            bad += 1
    if bad:
        print(f"❌ المدى {base[:7]}..{head[:7]}: {bad} التزام كود بلا وثيقة "
              "في نفسه — القاعدة الحاكمة بأمر المالك")
        return 1
    print(f"✅ المدى {base[:7]}..{head[:7]}: كل التزامات مطيعة (D-040)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "--range":
        return check_range(argv[1], argv[2])
    if len(argv) >= 3 and argv[0] == "--diff":
        # وضع التجميع القديم (أضعف — كود في التزام ووثائق في آخر يمر) —
        # أبقيه للتوافق فقط؛ البوابات تستخدم --range منذ R-749
        out = _git(["diff", "--name-only", argv[1], argv[2]]).stdout
        files = [("M", l.strip()) for l in out.splitlines() if l.strip()]
        return check_files(files, f"مدى {argv[1]}..{argv[2]} (تجميعي)")
    if argv and argv[0] == "--staged":
        return check_files(_staged_files(), "الفهرس (pre-commit)", ref=":")
    sha = argv[0] if argv else "HEAD"
    return check_commit(sha)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
