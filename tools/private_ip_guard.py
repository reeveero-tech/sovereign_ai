"""حارس العناوين الخاصة — النواة المشتركة (CI + hook محلي pre-commit).

قرار المالك د.٣ (2026-10-20 — توسيع جزئي): تُضاف إلى نطاقات IPv4 الثلاثة
(192.168/16، 10/8، 172.16/12 — كما في tests/test_no_private_ips_in_git.py)
نطاقا IPv6:
- ULA: fc00::/7 (أول مقطع fc00–fdff)
- link-local: fe80::/10 (أول مقطع fe80–febf)
خارج هذه الدفعة بقرار المالك: 100.64/10 والصيغ المموّهة (الجولة التالية).

ملاحظة صياغية إلزامية (درس R-705..R-709): لا عنوان حرفي كامل في هذا الملف.
الصيغة الوحيدة المسموحة لذكر نطاق IPv6 هي صيغة CIDR لقاعدة النطاق نفسها
(fc00::/7، fd00::/8، fe80::/10) — المقابل الدقيق للصيغة المختصرة في IPv4.
أي عنوان آخر (ولو انتهى بـ ::) يُمسك.

الاستخدام:
  python tools/private_ip_guard.py --staged    # محتوى الفهرس (hook pre-commit)
  python tools/private_ip_guard.py --tracked   # كل الملفات المتتبعة
رمز الخروج: 0 نظيف، 1 مخالفة، 2 خلل في التنفيذ (لا نجاح صامت).
"""

import re
import subprocess
import sys

IPV4_PATTERN = re.compile(
    r"\b(?:"
    r"192\.168\.\d{1,3}\.\d{1,3}"      # نطاق 192.168/16
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"   # نطاق 10/8
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"  # نطاق 172.16/12
    r")\b"
)

# مرشح IPv6: أول مقطع من النطاقات المضافة + مقاطع لاحقة. يُقبل المرشح
# عنوانًا فقط إن كان بصيغة IPv6 صالحة الشكل: يحوي «::» أو 7 نقطتين بالضبط.
_IPV6_FIRST = {
    "ula": r"f[cd][0-9a-f]{2}",          # fc00::/7
    "link_local": r"fe[89ab][0-9a-f]",   # fe80::/10
}
IPV6_RANGES = tuple(_IPV6_FIRST)


def _ipv6_pattern(first):
    return re.compile(
        r"(?<![0-9a-z:.])(?:" + first + r")(?::[0-9a-f]{0,4}){1,7}(?![0-9a-z:])",
        re.IGNORECASE,
    )


IPV6_PATTERNS = {name: _ipv6_pattern(first) for name, first in _IPV6_FIRST.items()}

# صيغ CIDR لقاعدة النطاق — مسموحة فقط متبوعة بـ «/»
# تُبنى وقت التشغيل — كتابتها حرفيًا هنا تجعل الحارس يمسك ملفه (درس R-705)
_RANGE_BASES = {first + "::" for first in ("fc00", "fd00", "fe80")}


def _is_ipv6_shape(s):
    return "::" in s or s.count(":") == 7


def scan_text(text):
    """يعيد قائمة (النوع، الموضع، النص) لكل مخالفة."""
    found = [("ipv4", m.start(), m.group(0)) for m in IPV4_PATTERN.finditer(text)]
    for name, pat in IPV6_PATTERNS.items():
        for m in pat.finditer(text):
            s = m.group(0)
            if not _is_ipv6_shape(s):
                continue
            if s.lower() in _RANGE_BASES and text[m.end():m.end() + 1] == "/":
                continue  # صيغة CIDR لقاعدة النطاق (توثيق)، لا عنوان
            found.append((name, m.start(), s))
    return found


def _git(args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="ignore")[:300])
    return r.stdout


def _files_and_contents(mode, cwd=None):
    if mode == "--staged":
        names = _git(["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"], cwd)
        for name in [n for n in names.decode(errors="ignore").split("\0") if n]:
            yield name, _git(["show", ":" + name], cwd).decode(errors="ignore")
    elif mode == "--tracked":
        root = _git(["rev-parse", "--show-toplevel"], cwd).decode().strip()
        names = _git(["ls-files", "-z"], cwd)
        for name in [n for n in names.decode(errors="ignore").split("\0") if n]:
            with open(f"{root}/{name}", "rb") as fh:
                yield name, fh.read().decode(errors="ignore")
    else:
        raise ValueError(mode)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv not in (["--staged"], ["--tracked"]):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        violations = []
        for name, content in _files_and_contents(argv[0]):
            for kind, pos, s in scan_text(content):
                violations.append(f"{name}:{content[:pos].count(chr(10)) + 1}: [{kind}] {s}")
    except Exception as e:  # خلل التنفيذ يفشل — لا نجاح صامت
        print(f"❌ حارس العناوين الخاصة: خلل في التنفيذ ({e})", file=sys.stderr)
        return 2
    if violations:
        print("❌ حارس العناوين الخاصة: عناوين شبكة داخلية — الالتزام مرفوض:", file=sys.stderr)
        print("\n".join(violations), file=sys.stderr)
        return 1
    print("✅ حارس العناوين الخاصة: نظيف")
    return 0


if __name__ == "__main__":
    sys.exit(main())
