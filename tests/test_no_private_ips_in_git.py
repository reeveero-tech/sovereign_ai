"""حارس العناوين الخاصة — لا عنوان شبكة داخلية في أي ملف متتبع.

بأمر المالك (2026-10-20، جولة R-705): بعد تسريب HIST-02 (عنوان شبكة
خاصة في وثائق R-704)، هذا الحارس يفشل البناء إذا ظهر أي عنوان في
النطاقات المحجوزة للشبكات الداخلية في أي ملف متتبع:
- نطاق 192.168/16 (النطاق الخاص الذي سُرِّب تاريخيًا)
- نطاق 10/8
- نطاق 172.16/12 (172.16–172.31)

ملاحظة صياغية إلزامية: يُمنع كتابة أي عنوان رباعي كامل (حتى ما ينتهي
بـ .0) داخل هذا الملف — الحارس يفحص كل الملفات المتتبعة بما فيها ملفه
نفسه، فأي مثال حرفي يجعله يمسك نفسه. النطاقات تُذكر بصيغة CIDR
المختصرة أعلاه فقط، والصيغة المقنعة (192.168.0.x) آمنة أيضًا.

ملاحظات التصميم:
- يفحص قائمة git المتتبعة كاملة (وليس الشجرة العاملية فقط) — ما يُلتزم
  هو ما يتحقق.
- الملف غير المقروء يُفشل الاختبار (لا تخطيًا صامتًا).
- الصيغ المقنّعة (مثل 192.168.0.x) لا تطابق — توثيق HIST-02 في
  docs/SECURITY.md يعتمد الصيغة المقنّعة بقرار المالك الصريح.
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# نطاقات المالك الثلاثة تحديدًا (وليس is_private وحده — يشمل نطاقات أخرى)
PRIVATE_IP_PATTERN = re.compile(
    r"\b(?:"
    r"192\.168\.\d{1,3}\.\d{1,3}"      # نطاق 192.168/16
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"   # نطاق 10/8
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"  # نطاق 172.16/12
    r")\b"
)


def _tracked_files():
    """قائمة الملفات المتتبعة كاملة — فشل الأمر نفسه يفشل الاختبار."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(REPO_ROOT),
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"git ls-files failed: {result.stderr.decode(errors='ignore')[:300]}"
    )
    return [f for f in result.stdout.decode(errors="ignore").split("\0") if f]


def test_no_private_ips_in_tracked_files():
    """يفشل عند أي عنوان خاص في أي ملف متتبع — بلا استثناءات ولا تخطي."""
    violations = []
    files = _tracked_files()
    assert files, "قائمة الملفات المتتبعة فارغة — خلل في تنفيذ الحارس"

    for rel_path in files:
        file_path = REPO_ROOT / rel_path
        try:
            content = file_path.read_bytes().decode(errors="ignore")
        except OSError as e:
            # ملف غير مقروء يُفشل الحارس — لا تخطيًا صامتًا
            violations.append(f"{rel_path}: غير مقروء ({e})")
            continue
        for match in PRIVATE_IP_PATTERN.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            violations.append(f"{rel_path}:{line_no}: {match.group(0)}")

    assert not violations, (
        "عناوين شبكة داخلية في ملفات متتبعة (HIST-02 — ممنوعة بأمر المالك):\n"
        + "\n".join(violations)
    )
