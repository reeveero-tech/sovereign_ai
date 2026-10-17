"""
اختبار D-032: لا مفاتيح خاصة في تاريخ الالتزامات

الحادثة: الالتزام 05704efa تضمّن ملف data/keys/keyring.json وفيه
مفتاح خاص (مفتاح anchor لـ R-615). بقرار المالك D-032 يُعتبر المفتاح
مخترقًا، ولا إعادة كتابة للتاريخ (القاعدة ٧) — لذا:

1. الحارس يرفض أي التزام مستقبلي يحتوي نمط مفاتيح خاصة (رؤوس PEM،
   أو قيم base64 طويلة تحت مفاتيح private_* وأخواتها) — في أي مسار
   بلا استثناءات مسارات إطلاقًا.
2. الحوادث التاريخية الموثقة فقط مسموحة، كل واحدة باستثناء محدد
   (التزام + مسار + نوع + بصمة) — لا استثناء ملفات شامل أبدًا.
3. اختبارات سلوكية بمواد مولّدة وقت التشغيل (لا قيم حرفية في
   المصدر تطابق أنماط الحارس): فشل محقون — بما فيه حقن في مسار ملف
   الحارس نفسه (لا ثقب مسار) — ومسار سليم بلا إنذارات زائفة.
4. الاستثناءات التاريخية لا تتعفن: كل إدخال يجب أن يطابق كشفًا
   فعليًا، وكل كشف يجب أن يكون مغطى باستثناء.

الاستثناءات التاريخية الاثنان المضافة لالتزامي 95e1e7b/ad6b105 هي
اقتباسات لقيم اصطناعية أو للمادة المخترقة نفسها في ملف هذا الحارس
(قبل إصلاح fixtures لتُبنى وقت التشغيل) — موثقة هنا وبصماتها
مطابقة، ولا تغطي أي التزام آخر.
"""

import base64
import hashlib
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# الاستثناءات التاريخية: (التزام، مسار، نوع، بصمة) — لا استثناء مسار شامل.
# كل إدخال يتحقق منه اختبار منفصل (لا تعفنًا)، وكل كشف غير مغطى يفشل.
# ------------------------------------------------------------------
HISTORICAL_EXCEPTIONS = [
    {
        "commit": "05704efa36bac3ebdcf59e81ea75f5a1df6df53b",
        "path": "data/keys/keyring.json",
        "kind": "secret",
        "fingerprint": "b8bf12ab28abfc011ddab1c17136eeadc6db18fa9b88cfe76a5b85337a5ef9d2",
        "reason": "HIST-01 (docs/SECURITY.md): مفتاح anchor خاص التُزم بالخطأ — "
                  "معلن مخترق بقرار المالك D-032 (2026-10-17)",
    },
    {
        "commit": "95e1e7bd0fc8bd2df9da8aa075f6ce94357516ad",
        "path": "tests/test_no_private_keys_in_commit_history.py",
        "kind": "pem",
        "fingerprint": "835196ae6ec947b39a8f9cb1d383ddf192a0cbcc8d702bcc64e7086947965a15",
        "reason": "رأس PEM اصطناعي في fixture الحارس قبل تحويله إلى توليد وقت "
                  "التشغيل — لا مادة حقيقية",
    },
    {
        "commit": "95e1e7bd0fc8bd2df9da8aa075f6ce94357516ad",
        "path": "tests/test_no_private_keys_in_commit_history.py",
        "kind": "secret",
        "fingerprint": "b8bf12ab28abfc011ddab1c17136eeadc6db18fa9b88cfe76a5b85337a5ef9d2",
        "reason": "اقتباس لقيمة HIST-01 في fixture الحارس (خطأ وكيل — أُصلح في "
                  "ad6b105 ثم تحوّل للتوليد وقت التشغيل)؛ القيمة مخترقة "
                  "وموثقة أصلًا ولا جديد يكشفه",
    },
    {
        "commit": "ad6b105e49c8d28d096876bfb7fbc29eea9483b0",
        "path": "tests/test_no_private_keys_in_commit_history.py",
        "kind": "secret",
        "fingerprint": "43f7129de32e3cdb6fccdbf276b638a7d7f27382ddfe04571f2cc9a804cc8659",
        "reason": "قيمة اصطناعية استُبدلت بها القيمة الحقيقية في fixture "
                  "الحارس — لا تطابق أي سر معروف",
    },
]

# نمط ١: رؤوس PEM للمفاتيح الخاصة (كل الأنواع الشائعة)
_PEM_PRIVATE = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
)
# نمط ٢: حقل مفتاح خاص (JSON أو بايثون) بقيمة base64/64url طويلة —
# أسماء private_* بأي لاحقة + الحشو '=' الممكن
_SECRET_FIELD = re.compile(
    r"""["'](?:private_[a-z_]+|privateKey|secret_key|signing_key|master_key|seed)["']"""
    r"""\s*[:=]\s*["']([A-Za-z0-9+/_-]{32,}={0,2})["']"""
)


def _git(repo: Path, *args: str) -> str:
    # errors="replace": فروق التاريخ قد تحوي بايتات ثنائية (ملفات غير نصية) —
    # لا يفشل الفحص عليها، والأنماط نصية فلن تتأثر
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))
    return proc.stdout.decode("utf-8", errors="replace")


def _scan_commit(repo: Path, sha: str) -> list:
    """يفحص سطور الإضافة في التزام واحد (وضع الدمج: فرق ضد كل أب).

    يعيد قائمة كشوف: (المسار، النوع، البصمة) — بلا أي استثناء مسار.
    النوع "pem" بصمة سطر الرأس المضاف (مقشرًا)، والنوع "secret"
    بصمة sha256 للقيمة المكتشفة.
    """
    out = _git(repo, "diff-tree", "--no-commit-id", "-r", "-m", "--root", "-p", sha)
    hits = []
    current_path = ""
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:].strip()
            continue
        if line.startswith("+++ "):
            current_path = ""
            continue
        if not line.startswith("+"):
            continue
        added = line[1:]
        if _PEM_PRIVATE.search(added):
            hits.append((
                current_path, "pem",
                hashlib.sha256(added.strip().encode()).hexdigest(),
            ))
        m = _SECRET_FIELD.search(added)
        if m:
            hits.append((
                current_path, "secret",
                hashlib.sha256(m.group(1).encode()).hexdigest(),
            ))
    return hits


def _uncovered(repo: Path, shas: list) -> list:
    """الكشوف غير المغطاة بالاستثناءات التاريخية في التزامات معطاة."""
    allowed = {(e["commit"], e["path"], e["kind"], e["fingerprint"])
               for e in HISTORICAL_EXCEPTIONS}
    out = []
    for sha in shas:
        for hit in _scan_commit(repo, sha):
            if (sha, *hit) not in allowed:
                out.append((sha, *hit))
    return out


def _make_commit(repo: Path, filename: str, content: str) -> str:
    (repo / filename).parent.mkdir(parents=True, exist_ok=True)
    (repo / filename).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=test", "-c", "user.email=t@t",
         "commit", "-q", "-m", "t")
    return _git(repo, "rev-parse", "HEAD").strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.name=test", "-c", "user.email=t@t", "commit", "-q",
         "--allow-empty", "-m", "root")


def _runtime_fixture_material() -> tuple:
    """مواد اختبار مولّدة وقت التشغيل — لا قيم حرفية في المصدر
    تطابق أنماط الحارس (رأس PEM يُركّب قطعًا، والقيمة عشوائية)."""
    secret = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")
    header = "-" * 5 + "BEGIN RSA PRIVATE KEY" + "-" * 5
    footer = "-" * 5 + "END RSA PRIVATE KEY" + "-" * 5
    pem = header + "\nMIIBOgIBAAJBAK\n" + footer + "\n"
    bad_json = '{"private_key": "' + secret + '"}\n'
    return secret, pem, bad_json


# ---------------------------------------------------------------- سلوك الحارس

def test_guard_detects_injected_private_keys(tmp_path):
    """فشل محقون: مادة خاصة مولّدة وقت التشغيل يجب أن تُكشف بدقة."""
    repo = tmp_path / "mini"
    _init_repo(repo)

    clean_sha = _make_commit(repo, "clean.py", "x = 1\n")
    assert _scan_commit(repo, clean_sha) == [], "التزام سليم لا يجب أن يُعلَّم"

    secret, pem, bad_json = _runtime_fixture_material()
    dirty_sha = _make_commit(repo, "leak.txt", pem + bad_json)

    hits = _scan_commit(repo, dirty_sha)
    pem_hits = [h for h in hits if h[1] == "pem"]
    sec_hits = [h for h in hits if h[1] == "secret"]
    assert len(pem_hits) == 1, "رأس PEM واحد يجب أن يُكشف"
    assert pem_hits[0][0] == "leak.txt", "الكشف منسوب للملف المحقون نفسه"
    assert len(sec_hits) == 1, "حقل private_key واحد يجب أن يُكشف"
    assert sec_hits[0][0] == "leak.txt", "الكشف منسوب للملف المحقون نفسه"
    assert sec_hits[0][2] == hashlib.sha256(secret.encode()).hexdigest(), \
        "بصمة المادة المكتشفة تُحسب من القيمة المولدة وقت التشغيل"


def test_guard_detects_material_in_guard_own_path(tmp_path):
    """لا ثقب مسار: مادة خاصة في مسار ملف الحارس نفسه يجب أن تُكشف.

    هذا الاختبار وُجد لأن نسخة سابقة من الحارس استثنت مسار ملفه —
    ثقبًا يسمح بإيداع مفتاح حقيقي فيه بلا كشف (اعتراض المراجع).
    """
    repo = tmp_path / "mini3"
    _init_repo(repo)

    secret, pem, bad_json = _runtime_fixture_material()
    guard_path = "tests/test_no_private_keys_in_commit_history.py"
    dirty_sha = _make_commit(repo, guard_path, pem + bad_json)

    hits = _scan_commit(repo, dirty_sha)
    assert any(h[0] == guard_path and h[1] == "pem" for h in hits), \
        "رأس PEM في مسار الحارس نفسه يجب أن يُكشف — لا استثناء مسار"
    assert any(
        h[0] == guard_path and h[1] == "secret"
        and h[2] == hashlib.sha256(secret.encode()).hexdigest()
        for h in hits
    ), "قيمة خاصة في مسار الحارس نفسه يجب أن تُكشف ببصمة مطابقة"


def test_guard_ignores_short_and_public_values(tmp_path):
    """مسار سليم: القيم القصيرة والمفاتيح العامة لا تُعلَّم (لا إنذارات زائفة)."""
    repo = tmp_path / "mini2"
    _init_repo(repo)
    ok_sha = _make_commit(repo, "ok.json", "\n".join([
        '{"public_key": "963f5d3ca0f4b9f3b9d1d23693a0fd644dbf7244dc5a39ed2cd5c7e65aad20f4"',
        ' "key_hint": "short_token_value",',
        ' "private_key": "too_short"}',
    ]) + "\n")
    assert _scan_commit(repo, ok_sha) == [], "القيم العامة/القصيرة يجب ألا تُعلَّم"


def test_guard_covers_padded_and_backup_names(tmp_path):
    """تغطية الأنماط الموسعة: حشو base64 '=' وأسماء private_* غير الشائعة."""
    repo = tmp_path / "mini4"
    _init_repo(repo)
    secret = base64.b64encode(os.urandom(32)).decode("ascii")  # بحشو '='
    bad = '{"private_backup": "' + secret + '"}\n'
    sha = _make_commit(repo, "backup.json", bad)
    hits = _scan_commit(repo, sha)
    assert any(h[1] == "secret" and h[2] == hashlib.sha256(secret.encode()).hexdigest()
               for h in hits), "حقل private_backup بقيمة بحشو '=' يجب أن يُكشف"


# ------------------------------------------------------------ الحارس على الواقع

def test_no_private_keys_in_commit_history():
    """تاريخ main (من HEAD): كل كشف مغطى باستثناء تاريخي محدد — لا غيره."""
    shas = _git(REPO_ROOT, "log", "HEAD", "--format=%H").split()
    assert shas, "يجب أن يكون للتاريخ التزامات"
    uncovered = _uncovered(REPO_ROOT, shas)
    assert not uncovered, (
        "التزامات تحوي أنماط مفاتيح خاصة غير مغطاة بالاستثناءات التاريخية "
        "المحددة (التزام+مسار+نوع+بصمة) — D-032 يوجب توثيق كل حادثة في "
        f"docs/SECURITY.md: {uncovered}"
    )


def test_historical_exceptions_match_real_detections():
    """الاستثناءات التاريخية لا تتعفن: كل إدخال يطابق كشفًا فعليًا
    في التزامه ومساره وبصمته — وإلا فهو سجل ميت يجب حذفه أو تصحيحه."""
    for e in HISTORICAL_EXCEPTIONS:
        hits = _scan_commit(REPO_ROOT, e["commit"])
        assert any(
            h[0] == e["path"] and h[1] == e["kind"] and h[2] == e["fingerprint"]
            for h in hits
        ), (
            f"الاستثناء التاريخي {e['commit'][:8]}/{e['path']}/{e['kind']} "
            "لم يعد يطابق كشفًا فعليًا — إما تغيّر التاريخ (ممنوع: القاعدة ٧) "
            "أو الحارس معطوب أو السجل ميت"
        )
