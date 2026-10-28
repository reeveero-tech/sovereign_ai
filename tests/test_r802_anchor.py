"""R-802 (أمر المالك «مواصلة التطوير» 2026-10-28): مرساة مسودات التطوير الذاتي.

الدليل الحي قبل الإصلاح: /selfdev/status على الإنتاج — كل المسودات `search_occurs_0_times`
(3 مهام exhausted، 0 وصلت CI). العقل الصغير ينسخ النافذة بإزاحة أو فراغات أو حرف مختلف.
المثبت: تصحيح حتمي إلى نص الملف الحقيقي (أو رفض كما كان)، ثم validate_draft نفسه، ثم
تطبيق CI الحرفي ينتج الملف الصحيح؛ والتغذية الراجعة تحمل النص الحقيقي الأقرب؛ ولا تسريب للشيفرة.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import self_develop as sd  # noqa: E402
from selfdev import anchor  # noqa: E402

SRC = (
    "import math\n"
    "\n"
    "\n"
    "class Calc:\n"
    "    def add(self, a, b):\n"
    "        return a - b\n"
    "\n"
    "    def area(self, r):\n"
    "        return math.pi * r * r\n"
    "\n"
    "\n"
    "def helper(x):\n"
    "    return x\n"
    "\n"
    "\n"
    "def other(y):\n"
    "    return x\n"
)


def _apply(orig, fix):
    assert orig.count(fix["search"]) == 1
    return orig.replace(fix["search"], fix["replace"], 1)


def test_exact_is_unchanged():
    f = anchor.anchor(SRC, "        return a - b\n", "        return a + b\n")
    assert f["method"] == "exact" and "return a + b" in _apply(SRC, f)


def test_trailing_whitespace_and_crlf():
    f = anchor.anchor(SRC, "        return a - b   \r\n", "        return a + b\n")
    assert f["method"] == "rstrip"
    out = _apply(SRC, f)
    assert "        return a + b\n\n    def area" in out
    compile(out, "x.py", "exec")


def test_indent_shift_reindents_replace():
    # العقل نسخ الكتلة بلا إزاحة الصنف
    f = anchor.anchor(SRC, "def add(self, a, b):\n    return a - b\n",
                      "def add(self, a, b):\n    return a + b\n")
    assert f["method"] == "indent"
    out = _apply(SRC, f)
    assert "    def add(self, a, b):\n        return a + b\n" in out
    compile(out, "x.py", "exec")


def test_fuzzy_small_typo_accepted_unique():
    f = anchor.anchor(SRC, "    def area(self, r):\n        return math.pi*r*r\n",
                      "    def area(self, r):\n        return math.pi * r ** 2\n")
    assert f and f["method"].startswith("fuzzy:") and f["score"] >= anchor.FUZZY_MIN
    out = _apply(SRC, f)
    assert "math.pi * r ** 2" in out and "math.pi * r * r" not in out
    compile(out, "x.py", "exec")


def test_fuzzy_rejects_invented_text():
    assert anchor.anchor(SRC, "def totally_new():\n    return 42\n", "x") is None


def test_duplicate_disambiguated_by_task_window():
    dup = "    return x\n"
    assert SRC.count(dup) == 2
    lines = SRC.splitlines()
    second = [i for i, ln in enumerate(lines) if ln == "    return x"][1]
    f = anchor.anchor(SRC, dup, "    return y\n", window=(second - 2, second + 3))
    assert f["method"] == "context"
    out = _apply(SRC, f)
    assert "def helper(x):\n    return x\n" in out and "def other(y):\n    return y\n" in out
    assert anchor.anchor(SRC, dup, "    return y\n", window=None) is None  # بلا نافذة لا تخمين


def test_nearest_returns_real_file_text():
    near = anchor.nearest(SRC, "def add(self, a, b):\n    return a - b\n")
    assert near and near in SRC and "def add" in near


# ---------------- الربط بالمحرك ----------------
CALC = "class Calc:\n    def add(self, a, b):\n        return a - b\n"
TEST = "import calc\n\ndef test_add():\n    assert calc.Calc().add(2, 3) == 5\n"


def _repo(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "calc.py").write_text(CALC, encoding="utf-8")
    return tmp_path


def _brain(search, replace):
    def brain(system, user, schema):
        if "keywords" in schema.get("properties", {}):
            return json.dumps({"file": "backend/calc.py", "keywords": ["add"]})
        brain.users.append(user)
        return json.dumps({"summary": "إصلاح الجمع", "search": search, "replace": replace,
                           "test_name": "test_add", "test_code": TEST})
    brain.users = []
    return brain


def test_engine_anchors_misindented_draft_and_ci_applies_it(tmp_path):
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path),
                           brain=_brain("def add(self, a, b):\n    return a - b", "def add(self, a, b):\n    return a + b"),
                           disk=False)
    t = eng.request("دالة add في calc تطرح", "Calc().add(2,3) يعيد -1")
    out = eng.tick(now=1.0)
    assert out["status"] == "drafted", out
    d = eng._tasks[t["id"]]["draft"]
    assert d["anchor"] == "indent"
    assert sd.validate_draft(d, CALC) == []  # نفس فحص CI
    new = CALC.replace(d["search"], d["replace"], 1)  # تطبيق CI الحرفي (tools/selfdev_ci.py)
    ns = {}
    exec(compile(new, "calc.py", "exec"), ns)
    assert ns["Calc"]().add(2, 3) == 5
    st = json.dumps(eng.status(), ensure_ascii=False)
    assert "return a + b" not in st and "return a - b" not in st  # لا تسريب للشيفرة


def test_engine_feedback_carries_nearest_real_text(tmp_path):
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path),
                           brain=_brain("def add(self, x, y, z):\n    return x * y * z - 1\n", "pass\n"),
                           disk=False)
    t = eng.request("دالة add في calc تطرح", "Calc().add(2,3) يعيد -1")
    assert eng.tick(now=1.0)["status"] == "invalid"
    fb = eng._tasks[t["id"]]["feedback"]
    assert "search_occurs_0_times" in fb and "def add(self, a, b):" in fb
    eng.tick(now=2.0)
    assert "def add(self, a, b):" in eng._brain.users[-1]  # المحاولة التالية رأت النص الحقيقي
    assert "def add(self, a, b)" not in json.dumps(eng.status(), ensure_ascii=False)  # لا تسريب


def test_status_declares_anchor_method(tmp_path):
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path),
                           brain=_brain("def add(self, a, b):\n    return a - b", "def add(self, a, b):\n    return a + b"),
                           disk=False)
    t = eng.request("دالة add في calc تطرح", "Calc().add(2,3) يعيد -1")
    eng.tick(now=1.0)
    task = next(x for x in eng.status()["tasks"] if x["id"] == t["id"])
    assert task["anchor"] == "indent"


def test_exhausted_search_failures_revived_once_only(tmp_path):
    """مهام استُنفدت قبل R-802 بعدم المطابقة فقط تُحيا مرة؛ غيرها وما بعد المرساة لا."""
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path), brain=_brain("لا يوجد هذا النص", "x"), disk=False)
    legacy = eng.request("دالة add في calc تطرح", "Calc().add(2,3) يعيد -1")
    other = eng.request("مهمة أخرى", "تفصيل")
    eng._tasks[legacy["id"]].update(status="exhausted", attempts=3, errors=["search_occurs_0_times"])
    eng._tasks[other["id"]].update(status="exhausted", attempts=3, errors=["test_without_assert"])
    out = eng.tick(now=10.0)
    assert out["revived"] == 1 and out["task"] == legacy["id"]
    assert eng._tasks[other["id"]]["status"] == "exhausted"
    for i in range(sd.MAX_ATTEMPTS):
        eng.tick(now=20.0 + i)
    assert eng._tasks[legacy["id"]]["status"] == "exhausted"
    assert eng.tick(now=40.0)["revived"] == 0  # لا إحياء ثانٍ
    assert "R-802" in [h["by"] for h in eng._tasks[legacy["id"]]["history"]]
