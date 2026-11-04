# -*- coding: utf-8 -*-
"""R-848 (D-063): حارس الأسرار — اختبارات تكمل المجموعة المجمّدة ``security.secrets``.

ثلاثة منها تقتل طفرات نجت من الحالات المجمّدة (متوقعة قبل التشغيل):
M06 (تجاهل العشوائية)، M08 (التنقية تتخطى قواعد القيمة المقتبسة)، M28 (البوابة تفحص
آخر التزام في المدى فقط). لا قيم سرية حرفية: كل مادة تُركّب وقت التشغيل.
"""
from __future__ import annotations

import json
import random
import string
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from secret_guard import catalog  # noqa: E402
from observability.redact import redact as obs_redact  # noqa: E402
from notifications import events as nev  # noqa: E402
from job_queue import worker as jworker  # noqa: E402

GATE = ROOT / "tools" / "gate_secrets.py"
_rnd = random.Random(8480)


def _mixed(n: int) -> str:
    s = [_rnd.choice(string.ascii_letters), _rnd.choice(string.digits)]
    s += [_rnd.choice(string.ascii_letters + string.digits) for _ in range(n - 2)]
    _rnd.shuffle(s)
    return "".join(s)


def _token(prefix_parts, n):
    return "".join(prefix_parts) + "".join(_rnd.choice(string.ascii_letters + string.digits) for _ in range(n))


def _repo(tmp: Path) -> Path:
    d = tmp / "r"
    d.mkdir()
    for c in (["init", "-q"], ["config", "user.email", "t@example.invalid"], ["config", "user.name", "t"],
              ["config", "commit.gpgsign", "false"]):
        subprocess.run(["git", *c], cwd=d, check=True)
    (d / "README").write_text("x\n")
    _commit(d, "base")
    return d


def _commit(d: Path, msg: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=d, check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", msg], cwd=d, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, check=True, capture_output=True,
                          text=True).stdout.strip()


def _gate(d: Path, tmp: Path, *args: str) -> subprocess.CompletedProcess:
    bl = tmp / "bl.json"
    if not bl.exists():
        bl.write_text(json.dumps({"entries": []}))
    return subprocess.run([sys.executable, str(GATE), "--repo", str(d), "--baseline", str(bl), *args],
                          capture_output=True, text=True, timeout=120)


# ------------------------------------------------------------ قتل الطفرات الناجية

def test_m06_low_entropy_assignment_is_not_a_secret():
    """قيمة مختلطة منخفضة العشوائية (نمط مكرر) ليست سرًا — يقتل M06."""
    val = "ab" * 9 + "12"       # عشوائية ~1.4 بت، لا حرف يتجاوز النصف
    assert catalog.entropy(val) < 3.5 and not catalog.is_placeholder(val)
    assert catalog.find(f'DB_PASSWORD = "{val}"') == []
    hi = _mixed(32)
    assert [h.rule for h in catalog.find(f'DB_PASSWORD = "{hi}"')] == ["generic_assignment"]


def test_m08_quoted_secret_value_in_json_log_is_redacted():
    """JSON في سجل: ``"client_secret": "…"`` لا يلتقطه key=value — قاعدة القيمة المقتبسة تخفيه. يقتل M08."""
    v = _mixed(32)
    line = json.dumps({"client_secret": v, "user": "u1"})
    assert v not in obs_redact(line)
    assert v not in nev.scrub(line) and v not in jworker.scrub(line)
    assert '"user": "u1"' in obs_redact(line)     # لا إفراط خارج القيمة


def test_m28_range_scans_every_commit_not_only_the_last(tmp_path):
    """سر في أول التزام من مدى من ثلاثة يُكشف ولو نظفه الأخير. يقتل M28."""
    d = _repo(tmp_path)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, capture_output=True, text=True).stdout.strip()
    v = _token(["rn", "d_"], 32)
    (d / "a.env").write_text(f"RENDER={v}\n")
    _commit(d, "leak")
    (d / "b.txt").write_text("unrelated\n")
    _commit(d, "other")
    (d / "a.env").write_text("RENDER=${RENDER_API_KEY}\n")
    head = _commit(d, "cleanup")
    p = _gate(d, tmp_path, "--range", base, head)
    assert p.returncode == 1 and "render_api_key" in p.stdout
    assert v not in p.stdout + p.stderr


# ------------------------------------------------------------ المستودع نفسه

def test_repository_tree_matches_baseline_exactly():
    """كل كشف في الشجرة المتتبعة مغطى ببصمة مراجعة، ولا إدخال متعفن."""
    p = subprocess.run([sys.executable, str(GATE), "--tree"], cwd=ROOT, capture_output=True, text=True,
                       timeout=600)
    assert p.returncode == 0, p.stdout[-2000:]


def test_baseline_entries_are_literal_reasoned_and_valueless():
    data = json.loads((ROOT / "tools" / "secrets_baseline.json").read_text(encoding="utf-8"))
    assert data["entries"], "خط الأساس فارغ؟ الشجرة فيها مواد مضمّنة معروفة"
    for e in data["entries"]:
        assert set(e) == {"rule", "path", "fingerprint", "reason"}
        assert not any(c in e["path"] for c in "*?[") and len(e["fingerprint"]) == 24
        assert "R-848" in e["reason"]
    raw = (ROOT / "tools" / "secrets_baseline.json").read_text(encoding="utf-8")
    assert catalog.find(raw) == [], "خط الأساس نفسه لا يحمل قيمًا"


def test_single_source_all_scrubbers_use_catalog():
    """RED R3: لا نسخ مستقلة من نمط الأسرار بعد اليوم."""
    for f in ("backend/observability/redact.py", "backend/notifications/events.py",
              "backend/job_queue/worker.py"):
        s = (ROOT / f).read_text(encoding="utf-8")
        assert "secret_guard import catalog" in s
        assert "sbp_[" not in s and "re.compile(" not in s, f


def test_gate_output_never_contains_value_and_head_mode_works(tmp_path):
    d = _repo(tmp_path)
    v = _token(["gh", "p_"], 36)
    (d / "x.py").write_text(f'T = "{v}"\n')
    head = _commit(d, "leak")
    p = _gate(d, tmp_path, head)
    assert p.returncode == 1 and "github_token" in p.stdout and v not in p.stdout + p.stderr


def test_gate_staged_mode(tmp_path):
    d = _repo(tmp_path)
    v = _token(["sb", "p_"], 40)
    (d / "s.txt").write_text(f"k={v}\n")
    subprocess.run(["git", "add", "-A"], cwd=d, check=True)
    p = _gate(d, tmp_path, "--staged")
    assert p.returncode == 1 and "supabase_pat" in p.stdout


@pytest.mark.parametrize("args", [[], ["--tree", "--staged"]])
def test_gate_requires_exactly_one_mode(tmp_path, args):
    d = _repo(tmp_path)
    p = _gate(d, tmp_path, *args)
    assert p.returncode == 2


def test_redaction_keeps_plain_text_intact():
    s = "loop 9d4b43d5 finished in 12.3s with 4 steps"
    assert obs_redact(s) == s and nev.scrub(s) == s and jworker.scrub(s) == s


def test_security_suite_registered_with_26_cases():
    from evaluation import suites
    s = suites.get("security.secrets")
    assert s.floor == 1.0 and suites.file_sha256(s.data_path) == s.sha256
    assert len(json.loads(s.data_path.read_text(encoding="utf-8"))["cases"]) == 26
