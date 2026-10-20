"""قرار المالك د.٣ (2026-10-20): توسيع حارس العناوين الخاصة — جزئيًا.

النطاقات المضافة: IPv6 ULA (fc00::/7) وlink-local (fe80::/10)، + hook محلي
pre-commit يفحص الفهرس قبل الالتزام. النواة: tools/private_ip_guard.py.

ملاحظة صياغية إلزامية (درس R-705..R-709): لا عنوان حرفي في هذا الملف —
كل عنوان اختباري يُبنى وقت التشغيل بالتجزئة، فلا يمسك الحارس ملفه.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD_PATH = REPO_ROOT / "tools" / "private_ip_guard.py"
HOOK_PATH = REPO_ROOT / ".githooks" / "pre-commit"


def _load_guard():
    spec = importlib.util.spec_from_file_location("private_ip_guard", GUARD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


guard = _load_guard()


def _j(*parts):
    return "".join(parts)


ULA_SAMPLES = [
    _j("fd", "12:3456:789a::1"),
    _j("fc", "00::1"),
    _j("FD", "00:0:0:0:0:0:0:1"),
    _j("fd", "ab:1::", "5"),
    _j("fd", "00::1/64"),
]
LINK_LOCAL_SAMPLES = [
    _j("fe", "80::1"),
    _j("fe", "bf::abcd"),
    _j("fe", "80::1%eth0"),
    _j("FE", "9a:0:0:0:1:2:3:4"),
]
NOT_FLAGGED = [
    _j("fe", "c0::1"),        # خارج fe80::/10
    _j("fb", "ff::1"),        # خارج fc00::/7
    _j("2001:", "db8::1"),    # نطاق توثيق عام
    _j("fc", "00::/7"),       # صيغة CIDR لقاعدة النطاق
    _j("fd", "00::/8"),
    _j("fe", "80::/10"),
    _j("fd", "12:3456"),      # ليس عنوان IPv6 صالح الشكل
    _j("abfd", "12::1"),      # جزء من رمز أطول
]


def _kinds(text):
    return {k for k, _, _ in guard.scan_text(text)}


@pytest.mark.parametrize("addr", ULA_SAMPLES)
def test_ula_detected(addr):
    assert "ula" in _kinds(f"server = {addr}\n"), addr


@pytest.mark.parametrize("addr", LINK_LOCAL_SAMPLES)
def test_link_local_detected(addr):
    assert "link_local" in _kinds(f"host: {addr}\n"), addr


@pytest.mark.parametrize("addr", NOT_FLAGGED)
def test_out_of_scope_not_flagged(addr):
    assert not guard.scan_text(f"x {addr} y"), addr


def test_ipv4_pattern_in_sync_with_ci_guard():
    """النواة وحارس CI القائم يستخدمان نمط IPv4 نفسه حرفيًا — لا انجراف."""
    spec = importlib.util.spec_from_file_location(
        "ci_ip_guard", REPO_ROOT / "tests" / "test_no_private_ips_in_git.py")
    ci = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci)
    assert guard.IPV4_PATTERN.pattern == ci.PRIVATE_IP_PATTERN.pattern


def test_no_private_ipv6_in_tracked_files():
    """المقابل IPv6 لـ test_no_private_ips_in_tracked_files — بلا استثناءات."""
    violations = []
    for name, content in guard._files_and_contents("--tracked", cwd=str(REPO_ROOT)):
        for kind, pos, s in guard.scan_text(content):
            if kind in guard.IPV6_RANGES:
                violations.append(f"{name}:{content[:pos].count(chr(10)) + 1}: [{kind}] {s}")
    assert not violations, "عناوين IPv6 خاصة في ملفات متتبعة:\n" + "\n".join(violations)


# ---------- hook pre-commit (مستودع مؤقت معزول) ----------

def _sh(args, cwd, env=None):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, env=env)


@pytest.fixture
def hooked_repo(tmp_path):
    assert HOOK_PATH.exists(), "hook pre-commit غير موجود: .githooks/pre-commit"
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    shutil.copy2(GUARD_PATH, repo / "tools" / "private_ip_guard.py")
    shutil.copy2(HOOK_PATH, repo / ".githooks" / "pre-commit")
    env = dict(os.environ, PYTHON=sys.executable,
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "t@example.invalid"],
                ["git", "config", "user.name", "t"],
                ["git", "config", "core.hooksPath", ".githooks"]):
        assert _sh(cmd, repo, env).returncode == 0
    return repo, env


def _commit(repo, env, content):
    (repo / "note.txt").write_text(content, encoding="utf-8")
    assert _sh(["git", "add", "-A"], repo, env).returncode == 0
    return _sh(["git", "commit", "-q", "-m", "t"], repo, env)


@pytest.mark.parametrize("addr", [
    _j("192", ".168.", "7.9"),
    _j("fd", "12:3456::1"),
    _j("fe", "80::1"),
])
def test_pre_commit_hook_blocks_private_address(hooked_repo, addr):
    repo, env = hooked_repo
    r = _commit(repo, env, f"target = {addr}\n")
    assert r.returncode == 1, f"الالتزام مرّ رغم العنوان الخاص: {addr} ({r.returncode})"
    assert "حارس العناوين الخاصة" in r.stderr and "note.txt" in r.stderr, \
        f"الرفض ليس من الحارس: {r.stderr[:300]}"
    assert _sh(["git", "rev-parse", "--verify", "-q", "HEAD"], repo, env).returncode != 0, \
        "أُنشئ التزام رغم الرفض"


def test_pre_commit_hook_allows_clean_commit(hooked_repo):
    repo, env = hooked_repo
    r = _commit(repo, env, "target = 127.0.0.1\n")
    assert r.returncode == 0, r.stderr
    assert _sh(["git", "rev-parse", "--verify", "-q", "HEAD"], repo, env).returncode == 0
