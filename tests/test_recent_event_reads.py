"""R-780 (ROADMAP_V6 ٦.١.٩) — قراءات «الأحدث» تقرأ الأحدث فعلًا.

الدليل: `iterate_events(limit=N)` بلا `reverse=True` يعيد **أقدم** N حدث في السجل (سلوك موثق،
ثُبّت في R-775). 15 موضعًا في `backend/` تستدعيه هكذا وهي تقصد النشاط الأخير: كشف التحكم
الخارجي يفحص أقدم 200 حدث إلى الأبد، والتطور/اللدونة/الأيض تحسب «الاستخدام» من أول السجل.
إضافةً: `get_resurrection_history` يقرأ `event["payload"]` والحدث لا يحمل payload (هو في blob)
⇒ يعيد قواميس فارغة دائمًا.
"""
import ast
import shutil
import tempfile
from pathlib import Path

import pytest

from backend.memory.core import SovereignCore
from backend.sovereign.keys import KeyRing

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

# مواضع مستثناة عمدًا — مسارات قاسية معطلة (R-703 / D-041) أو اقتطاع معلن؛ لا تُغيَّر هنا.
ALLOWED_OLDEST_FIRST = {
    ("memory/biological/instincts.py", "_execute_protection_action"),   # خلف block_drastic_action
    ("memory/biological/instincts.py", "protect_sovereign_privacy"),    # خلف block_drastic_action
    ("memory/biological/instincts.py", "immortalize_sovereign"),        # خلف block_drastic_action
    ("memory/defense/ransomware.py", "_encrypt_all_memory"),            # مسار قاسٍ، اقتطاعه معلن (R-682)
}


def _oldest_first_calls():
    found = set()
    for py in BACKEND.rglob("*.py"):
        if "tests" in py.relative_to(BACKEND).parts:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "iterate_events"):
                    kw = {k.arg: k.value for k in node.keywords}
                    rev = kw.get("reverse")
                    if "limit" in kw and not (isinstance(rev, ast.Constant) and rev.value is True):
                        found.add((py.relative_to(BACKEND).as_posix(), fn.name))
    return found


def test_no_new_oldest_first_limited_reads():
    extra = _oldest_first_calls() - ALLOWED_OLDEST_FIRST
    assert not extra, f"iterate_events(limit=…) بلا reverse=True يقرأ أقدم الأحداث: {sorted(extra)}"


@pytest.fixture
def core(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS", "0")
    tmp = Path(tempfile.mkdtemp())
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-780 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    c = SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr)
    for i in range(300):
        c.append_event("test::old", {"i": i})
    yield c
    shutil.rmtree(tmp, ignore_errors=True)


def test_external_control_detection_sees_recent_commands(core):
    from backend.memory.biological.instincts import CognitiveInstincts
    core.append_event("test::cmd", {"type": "external_command", "authorized": False,
                                    "source": "intruder", "command": "x"})
    inst = CognitiveInstincts.__new__(CognitiveInstincts)
    inst.core = core
    attempts = inst._detect_external_control()
    assert [a["source"] for a in attempts] == ["intruder"]


def test_resurrection_history_returns_real_payloads(core):
    from backend.memory.defense.ransomware import RansomwareDefense
    core.append_event("phoenix::resurrected", {"duration": 1.5, "decrypted_items": 3, "method": "m"})
    rd = RansomwareDefense.__new__(RansomwareDefense)
    rd.core = core
    assert rd.get_resurrection_history() == [{"duration": 1.5, "decrypted_items": 3, "method": "m"}]


def test_external_command_is_neutralized_once(core):
    """بعد قراءة الأحدث، لا يُعاد تحييد الأمر نفسه في كل دورة ما دام ضمن آخر 200 حدث."""
    from backend.memory.biological.instincts import CognitiveInstincts
    core.append_event("test::cmd", {"type": "external_command", "authorized": False,
                                    "source": "intruder", "command": "x"})
    inst = CognitiveInstincts.__new__(CognitiveInstincts)
    inst.core = core
    inst._ensure_no_restrictions = lambda: None
    first = inst.preserve_sovereign_autonomy()
    second = inst.preserve_sovereign_autonomy()
    assert first["actions_taken"] == ["neutralized_intruder"]
    assert second["actions_taken"] == []
    n = sum(1 for e in core.iterate_events(reverse=True, limit=50)
            if e.get("type") == "instinct::external_control_neutralized")
    assert n == 1
