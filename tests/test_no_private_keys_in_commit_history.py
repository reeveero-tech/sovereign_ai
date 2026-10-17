"""
اختبار D-032: لا مفاتيح خاصة في تاريخ الالتزامات

الحادثة: الالتزام 05704efa تضمّن ملف data/keys/keyring.json وفيه
مفتاح خاص (مفتاح anchor لـ R-615). بقرار المالك D-032 يُعتبر المفتاح
مخترقًا، ولا إعادة كتابة للتاريخ (القاعدة ٧) — لذا:

1. الحارس يرفض أي التزام مستقبلي يحتوي نمط مفاتيح خاصة
   (رؤوس PEM، أو قيم base64 طويلة تحت مفاتيح private_*).
2. الحادثة المعروفة 05704ef مدرجة في قائمة مسموحة موثقة
   (KNOWmN_COMPROMISED) — لا لإخفائها بل لأن التاريخ لا يُعاد
   كتابته؛ بصمة المفتاح مثبتة في docs/SECURITY.md.
3. اختبار سلوكي: الحارس يكشف مادة اصطناعية مُحقونة في مستودع
   مؤقت (فشل محقون + مسار سليم + تأكيدات محددة)، والقائمة
   المسموحة لا تتعفن (كل إدخال فيها يجب أن يطابق كشفًا فعليًا
   وبصمة مطابقة للمادة المكتشفة).
4. استثناء واحد موثق: هذا الملف نفسه مستثنى من الفحص —
   fixtures الحارس اصطناعية بالتعريف (مادة PEM وقيمة base64
   اصطناعيتان للتحقق الإيجابي). ممنوع وضع أي مادة حقيقية هنا؛
   القيمة الاصطناعية أدناه لا تطابق أي سر معروف.
"""

import hashlib
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# الحادثة المعروفة — لا يُحذف التاريخ (القاعدة ٧)، بل يُدار المفتاح كمسرّب
KNOWN_COMPROMISED = {
    "05704efa36bac3ebdcf59e81ea75f5a1df6df53b": {
        "reason": "R-615: مفتاح anchor خاص التُزم بالخطأ في data/keys/keyring.json "
                  "وأُزيل لاحقًا من الشجرة — معلن مخترق بقرار المالك D-032 (2026-10-17)",
        "fingerprint": "b8bf12ab28abfc011ddab1c17136eeadc6db18fa9b88cfe76a5b85337a5ef9d2",
    },
}

# نمط ١: رؤوس PEM للمفاتيح الخاصة (كل الأنواع الشائعة)
_PEM_PRIVATE = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
)
# نمط ٢: حقل مفتاح خاص (JSON أو بايثون) بقيمة base64/64url طويلة
_SECRET_FIELD = re.compile(
    r"""["'](?:private_key|privateKey|secret_key|signing_key|master_key|seed)["']"""
    r"""\s*[:=]\s*["']([A-Za-z0-9+/_-]{32,})["']"""
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


GUARD_TEST_PATH = "tests/test_no_private_keys_in_commit_history.py"


def _scan_commit(repo: Path, sha: str) -> dict:
    """يفحص سطور الإضافة في التزام واحد (وضع الدمج: فرق ضد كل أب).

    يعيد {"pem": [أسطر...], "secret_fields": [(الحقل، القيمة، البصمة)...]}

    استثناء موثق: ملف الحارس نفسه لا يُفحص — fixtures اصطناعية بالتعريف.
    """
    out = _git(repo, "diff-tree", "--no-commit-id", "-r", "-m", "--root", "-p", sha)
    hits = {"pem": [], "secret_fields": []}
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
        if current_path == GUARD_TEST_PATH:
            continue
        added = line[1:]
        if _PEM_PRIVATE.search(added):
            hits["pem"].append(added.strip())
        m = _SECRET_FIELD.search(added)
        if m:
            secret = m.group(1)
            fp = hashlib.sha256(secret.encode()).hexdigest()
            hits["secret_fields"].append((m.group(0).split(":")[0].strip("\"'"), secret, fp))
    return hits


def _is_clean(hits: dict) -> bool:
    return not hits["pem"] and not hits["secret_fields"]



def _make_commit(repo: Path, filename: str, content: str) -> str:
    (repo / filename).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=test", "-c", "user.email=t@t", "commit", "-q", "-m", "t")
    return _git(repo, "rev-parse", "HEAD").strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.name=test", "-c", "user.email=t@t", "commit", "-q",
         "--allow-empty", "-m", "root")


# ---------------------------------------------------------------- سلوك الحارس

def test_guard_detects_injected_private_keys(tmp_path):
    """فشل محقون: مادة خاصة في مستودع مؤقت يجب أن تُكشف بأنماط محددة."""
    repo = tmp_path / "mini"
    _init_repo(repo)

    clean_sha = _make_commit(repo, "clean.py", "x = 1\n")
    assert _is_clean(_scan_commit(repo, clean_sha)), "التزام سليم لا يجب أن يُعلَّم"

    pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAK\n-----END RSA PRIVATE KEY-----\n"
    bad_json = '{"private_key": "SYNTHETIC_guard_fixture_key_1234567890abcdefABCDEF"}\n'
    dirty_sha = _make_commit(repo, "leak.txt", pem + bad_json)

    hits = _scan_commit(repo, dirty_sha)
    assert len(hits["pem"]) == 1, "رأس PEM واحد يجب أن يُكشف"
    assert "BEGIN RSA PRIVATE KEY" in hits["pem"][0], "سطر PEM المكتشف يجب أن يحمل النص المحقون"
    assert len(hits["secret_fields"]) == 1, "حقل private_key واحد يجب أن يُكشف"
    field, secret, fp = hits["secret_fields"][0]
    assert "private_key" in field, "الحقل المكتشف هو private_key نفسه"
    assert secret == "SYNTHETIC_guard_fixture_key_1234567890abcdefABCDEF", \
        "القيمة المكتشفة هي القيمة المحقونة نصًّا"
    assert fp == hashlib.sha256(b"SYNTHETIC_guard_fixture_key_1234567890abcdefABCDEF").hexdigest(), \
        "بصمة المادة المكتشفة تُحسب من القيمة المحقونة"


def test_guard_ignores_short_and_public_values(tmp_path):
    """مسار سليم: القيم القصيرة والمفاتيح العامة لا تُعلَّم (لا إنذارات زائفة)."""
    repo = tmp_path / "mini2"
    _init_repo(repo)
    ok_sha = _make_commit(repo, "ok.json", "\n".join([
        '{"public_key": "963f5d3ca0f4b9f3b9d1d23693a0fd644dbf7244dc5a39ed2cd5c7e65aad20f4"',
        ' "key_hint": "short_token_value",',
        ' "private_key": "too_short"}',
    ]) + "\n")
    hits = _scan_commit(repo, ok_sha)
    assert _is_clean(hits), "القيم العامة/القصيرة يجب ألا تُعلَّم"


# ------------------------------------------------------------ الحارس على الواقع

def test_no_private_keys_in_commit_history():
    """تاريخ main (من HEAD) خالٍ من المفاتيح الخاصة إلا الحادثة الموثقة 05704ef."""
    shas = _git(REPO_ROOT, "log", "HEAD", "--format=%H").split()
    assert shas, "يجب أن يكون للتاريخ التزامات"
    detections = {}
    for sha in shas:
        hits = _scan_commit(REPO_ROOT, sha)
        if not _is_clean(hits):
            detections[sha] = hits
    undocumented = set(detections) - set(KNOWN_COMPROMISED)
    assert not undocumented, (
        "التزامات تحوي أنماط مفاتيح خاصة غير موثقة في قائمة الحوادث المعروفة "
        f"(D-032 يوجب بصمة كل حادثة في docs/SECURITY.md): {sorted(undocumented)} "
        f"المكتشف: { {s: detections[s]['secret_fields'][:1] for s in undocumented} }"
    )


def test_allowlist_entries_match_real_detections():
    """القائمة المسموحة لا تتعفن: كل إدخال يطابق كشفًا فعليًا وبصمة مطابقة للمادة."""
    for sha, meta in KNOWN_COMPROMISED.items():
        hits = _scan_commit(REPO_ROOT, sha)
        assert hits["secret_fields"] or hits["pem"], (
            f"إدخال القائمة المسموحة {sha[:8]} لم يعد يطابق كشفًا فعليًا — "
            "إما تغيّر التاريخ (ممنوع: القاعدة ٧) أو الحارس معطوب"
        )
        if hits["secret_fields"]:
            assert hits["secret_fields"][0][2] == meta["fingerprint"], (
                f"بصمة المادة المكتشفة في {sha[:8]} لا تطابق البصمة الموثقة في "
                "docs/SECURITY.md — سجل الحادثة غير متطابق"
            )
