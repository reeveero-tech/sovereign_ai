#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة الحذف الموحدة — قرار المالك Issue #8 (R-751 — ROADMAP_V5 ١.١-ب).

القاعدة: أي التزام يحذف سطرًا بلا `# DELETION-JUSTIFIED` في نفس الالتزام
(رسالته أو محتوى فرقه) يُرفض.

الأوضاع:
  gate_deletions.py SHA                 — التزام واحد
  gate_deletions.py --range BASE HEAD   — كل التزام في المدى بنفسه (CI: الدفع وPR)
  gate_deletions.py --staged MSGFILE    — الفهرس + رسالة الالتزام (hook commit-msg)

تبرير متأخر: `forensics/DELETION_LATE_JUSTIFIED.txt` (سطر لكل SHA كامل + سبب)
يُعفي التزامًا تاريخيًا فقط إن كان له مدخل في `forensics/DELETED_LINES_AUDIT.md`
(قسم «## » يذكر أول 7 محارف من SHA في عنوانه ويحمل العلامة في متنه). القائمة صريحة ومراجعة في الفرق —
لا إعفاء صامت.

الالتزامات الدمجية تُتجاوز (تُفحص التزاماتها الأصلية بنفسها).
"""

import subprocess
import sys
from pathlib import Path

MARK = "# DELETION-JUSTIFIED"
LATE_FILE = Path("forensics/DELETION_LATE_JUSTIFIED.txt")
AUDIT_FILE = Path("forensics/DELETED_LINES_AUDIT.md")


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def _deletions(numstat: str) -> int:
    total = 0
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1].isdigit():
            total += int(parts[1])
    return total


def _late_justified(sha: str) -> bool:
    if not LATE_FILE.is_file() or not AUDIT_FILE.is_file():
        return False
    listed = {ln.split()[0] for ln in LATE_FILE.read_text(encoding="utf-8").splitlines()
              if ln.strip() and not ln.startswith("#")}
    if sha not in listed:
        return False
    short = sha[:7]
    # قسم تدقيق (يبدأ بـ «## ») يذكر SHA في عنوانه ويحمل العلامة في متنه
    sections = AUDIT_FILE.read_text(encoding="utf-8").split("\n## ")
    return any(short in sec.splitlines()[0] and MARK in sec
               for sec in sections if sec.strip())


def check_commit(sha: str) -> bool:
    sha = _git("rev-parse", sha).strip()
    parents = _git("rev-list", "--parents", "-n", "1", sha).split()
    if len(parents) > 2:
        print(f"⏭️ {sha[:7]}: التزام دمجي — تُفحص التزاماته الأصلية بنفسها")
        return True
    dels = _deletions(_git("show", "--numstat", "--format=", sha))
    if dels == 0:
        print(f"✅ {sha[:7]}: لا حذوفات")
        return True
    if MARK in _git("log", "-1", "--format=%B", sha) or MARK in _git("show", sha):
        print(f"✅ {sha[:7]}: {dels} سطر محذوف مبرر في نفس الالتزام")
        return True
    if _late_justified(sha):
        print(f"⚠️ {sha[:7]}: {dels} سطر — تبرير متأخر موثق (DELETION_LATE_JUSTIFIED + مدخل تدقيق)")
        return True
    print(f"❌ {sha[:7]}: يحذف {dels} سطرًا بلا {MARK} في نفس الالتزام — قرار المالك (Issue #8)")
    return False


def check_staged(msg_file: str) -> bool:
    dels = _deletions(_git("diff", "--cached", "--numstat"))
    if dels == 0:
        print("✅ [commit-msg] لا حذوفات في الفهرس")
        return True
    msg = Path(msg_file).read_text(encoding="utf-8")
    if MARK in msg or MARK in _git("diff", "--cached"):
        print(f"✅ [commit-msg] {dels} سطر محذوف مبرر في نفس الالتزام")
        return True
    print(f"❌ [commit-msg] الالتزام يحذف {dels} سطرًا بلا {MARK} في رسالته أو فرقه — "
          "قرار المالك (Issue #8). أضف العلامة مع السبب، ومدخلًا في "
          "forensics/DELETED_LINES_AUDIT.md.")
    return False


def main(argv: list) -> int:
    if len(argv) == 2 and argv[0] == "--staged":
        return 0 if check_staged(argv[1]) else 1
    if len(argv) == 3 and argv[0] == "--range":
        shas = _git("rev-list", "--reverse", f"{argv[1]}..{argv[2]}").split()
        results = [check_commit(s) for s in shas]  # كلها تُفحص — لا توقف عند أول فشل
        return 0 if all(results) else 1
    if len(argv) == 1:
        return 0 if check_commit(argv[0]) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
