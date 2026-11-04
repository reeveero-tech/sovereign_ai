# -*- coding: utf-8 -*-
"""R-849: مجموعة مجمّدة skills.durability — دوام المهارات عبر إعادة النشر.

الحالات مكتوبة من القاعدة (المواصفة أعلاه) قبل أول تشغيل وتُجمّد ببصمة
sha256 في suites.py — بوابة CI (tools/gate_eval.py) ترفض النشر تحت الأرضية
1.0. كل سيناريو مكتوب ليقرأ كمواصفة قابلة للفحص، لا ككود اختبار فقط:
كل سيناريو يبني دوره الخاصة في tmp معقد نظيف — لا حالة مشتركة بين الحالات
(عزل كما في R-847). من المتوقع أن يكون لكل سيناريو صفر منطق شرطي غير
الإعلان المحدد أدناه.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from skills_durable import SkillsDurable  # noqa: E402


class MemStore:
    """مخزن دائم مزيف — عقد SupabaseDisk نفسه (save/load/list)."""

    backend = "fake-memory"

    def __init__(self, fail: bool = False):
        self.blobs: Dict[str, Any] = {}
        self.fail = fail

    def save_blob(self, namespace: str, key: str, payload: Dict[str, Any]) -> bool:
        if self.fail:
            return False
        self.blobs[f"{namespace}/{key}"] = json.loads(json.dumps(payload))
        return True

    def load_blob(self, namespace: str, key: str):
        return self.blobs.get(f"{namespace}/{key}")

    def list_blobs(self, namespace: str, limit: int = 1000, offset: int = 0):
        if self.fail:
            raise RuntimeError("unreachable")
        return [{"key": k.split("/", 1)[1], "payload": v}
                for k, v in self.blobs.items() if k.startswith(f"{namespace}/")]


def _manifest(version: str = "1.0.0", expect: int = 10) -> Dict[str, Any]:
    return {
        "name": "add_then_double", "version": version,
        "source": "owner-authored (eval)", "description": "(a+b)*2",
        "inputs": {"a": "عدد", "b": "عدد"},
        "permissions": ["math.add", "math.mul"],
        "steps": [
            {"tool": "math.add", "inputs": {"a": "{{a}}", "b": "{{b}}"},
             "check": {"type": "non_empty"}},
            {"tool": "math.mul", "inputs": {"a": "{{steps.0.sum}}", "b": 2},
             "check": {"type": "non_empty"}},
        ],
        "output": "{{steps.1.product}}",
        "eval": {"reference": "حساب يدوي", "cases": [
            {"inputs": {"a": 2, "b": 3}, "expect": expect},
            {"inputs": {"a": 0, "b": 0}, "expect": 0},
        ]},
    }


def _reg():
    from tool_registry import ToolRegistry, ToolSpec
    reg = ToolRegistry()
    reg.register(ToolSpec(name="math.add", description="", inputs={"a": "", "b": ""},
                         outputs="sum", handler=lambda a, b: {"sum": int(a) + int(b)}))
    reg.register(ToolSpec(name="math.mul", description="", inputs={"a": "", "b": ""},
                         outputs="product", handler=lambda a, b: {"product": int(a) * int(b)}))
    return reg


def _audit():
    """سجل أحداث مزيف — نفس عدة R-757 (patch لـ memory.core.get_core وقت النداء)."""
    import memory.core as core_mod

    class FC:
        def append_event(self, t, p, user=None):
            events.append((str(t), p))

        def ledgers(self):
            return {"skill_lifecycle": {"after_commit": False}}

    events: List = []

    def rec(op: str, payload: Dict[str, Any]) -> None:
        events.append((op, payload))

    orig = getattr(core_mod, "get_core", None)
    core_mod.get_core = lambda: FC()
    return events, rec, orig


def _restore_core(orig) -> None:
    import memory.core as core_mod
    if orig is not None:
        core_mod.get_core = orig


def _cycle(lib, version="1.0.0", expect=10):
    lib.propose(_manifest(version, expect), actor="author")
    lib.evaluate("add_then_double", version)
    lib.evaluate_independent(
        "add_then_double", version,
        [{"inputs": {"a": 5, "b": 1}, "expect": 12},
         {"inputs": {"a": -1, "b": 4}, "expect": 6}], actor="owner")
    return lib.approve("add_then_double", version, actor="owner")


def _lib(tmp, store):
    from skills import SkillLibrary
    ev, rec, _ = _audit()
    dur = SkillsDurable(tmp / "skills", store, audit=rec)
    return SkillLibrary(tmp / "skills", _reg(), durable=dur), dur, ev


# ----------------------------------------------------------------- السيناريوهات
def s_wipe_survives(tmp):
    """S-D1: محو القرص (إعادة نشر) + إقلاع جديد ⇒ المهارة تعود من البعيد."""
    lib, dur, _ = _lib(tmp, MemStore())
    _cycle(lib)
    shutil.rmtree(lib.root)
    out, _, _ = _lib(tmp, dur.store)
    loaded = out.load_active()
    return {"survived": loaded == ["skill.add_then_double"],
            "active": out.status()["skills"][0]["active"]}


def s_write_through_propose(tmp):
    """S-D2: propose يظهر في البعيد فورًا — الكتابة النافذة تبدأ من أول تحول."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    lib.propose(_manifest(), actor="author")
    return {"pushed": "skills/pkg:add_then_double:1.0.0" in store.blobs,
            "state": (store.blobs.get("skills/pkg:add_then_double:1.0.0") or {})
            .get("state")}


def s_full_cycle_write_through(tmp):
    """S-D3: نهاية الدورة: البعيد state=active وactive.json مدفوع."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib)
    pkg = store.blobs["skills/pkg:add_then_double:1.0.0"]
    return {"state": pkg["state"],
            "active": store.blobs["skills/active:add_then_double"]["active"],
            "versions": 1}


def s_tampered_remote_refused(tmp):
    """S-D4: حزمة بعيدة مزوّرة (بصمة لا تطابق) تُرفض — لا تُكتب محليًا."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib)
    store.blobs["skills/pkg:add_then_double:1.0.0"]["manifest"]["steps"][0]["tool"] = "math.mul"
    shutil.rmtree(lib.root)
    lib2, dur, ev = _lib(tmp, store)
    rep = dur.restore()
    ops = [e[0] for e in ev]
    return {"refused": rep["refused"] == ["pkg:add_then_double:1.0.0"],
            "not_written": not (lib2.root / "add_then_double").exists(),
            "audited": "skills_durable.refused_remote" in ops}


def s_tampered_local_repaired(tmp):
    """S-D5: حزمة محلية تالفة تُعاد سليمة من البعيد — إصلاح ذاتي."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib)
    p = lib.root / "add_then_double" / "1.0.0.json"
    pkg = json.loads(p.read_text(encoding="utf-8"))
    pkg["manifest"]["steps"][0]["tool"] = "math.mul"
    p.write_text(json.dumps(pkg, ensure_ascii=False), encoding="utf-8")
    lib2, dur, _ = _lib(tmp, store)
    rep = dur.restore()
    fixed = json.loads(p.read_text(encoding="utf-8"))
    return {"repaired": rep["repaired"] == ["pkg:add_then_double:1.0.0"],
            "restored_tool": fixed["manifest"]["steps"][0]["tool"]}


def s_valid_local_kept(tmp):
    """S-D6: المحلي السليم لا يُستبدل — الاستعادة للغائب والتالف فقط."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib)
    lib2, dur, _ = _lib(tmp, store)
    rep = dur.restore()
    return {"restored": len(rep["restored"]), "repaired": len(rep["repaired"]),
            "refused": len(rep["refused"])}


def s_store_down_local_recovery(tmp):
    """S-D7: المخزن معطوب: الدورة كاملة محليًا والحالة تعلن الخطأ — لا انهيار."""
    store = MemStore(fail=True)
    lib, _, _ = _lib(tmp, store)
    out = _cycle(lib)
    st = lib.status()["durable"]
    return {"approved": out["active"] == "1.0.0",
            "honest": bool(st["last_error"]), "enabled": st["enabled"]}


def s_secret_blocked(tmp):
    """S-D8: سر في الحمولة ⇒ رفض مغلق: لا يغادر القرص، محليًا تعمل."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    m = _manifest()
    import uuid
    m["source"] = f"leak rnd_{uuid.uuid4().hex}"
    lib.propose(m, actor="author")
    return {"nothing_remote": len(store.blobs) == 0,
            "local_works": (lib.root / "add_then_double" / "1.0.0.json").exists(),
            "declared": lib.status()["durable"]["last_error"] == "secret_in_payload"}


def s_rollback_syncs(tmp):
    """S-D9: التراجع يحدث active البعيد — لا رجوع للقديم بعد نشر جديد."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib, "1.0.0")
    _cycle(lib, "2.0.0")
    lib.rollback("add_then_double", actor="owner")
    return {"remote_active": store.blobs["skills/active:add_then_double"]["active"],
            "local_active": json.loads(
                (lib.root / "add_then_double" / "active.json")
                .read_text(encoding="utf-8"))["active"]}


def s_two_versions_fresh_boot(tmp):
    """S-D10: نشر جديد بقرص نظيف ⇒ الإصداران يعودان والفعال محفوظ."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib, "1.0.0")
    _cycle(lib, "2.0.0")
    shutil.rmtree(lib.root)
    lib2, dur, _ = _lib(tmp, store)
    rep = dur.restore()
    files = sorted(p.name for p in (lib2.root / "add_then_double").glob("*.json"))
    return {"restored": len(rep["restored"]),
            "files": files == ["1.0.0.json", "2.0.0.json", "active.json"],
            "active": json.loads((lib2.root / "add_then_double" / "active.json")
                                 .read_text(encoding="utf-8"))["active"]}


def s_conflict_local_wins(tmp):
    """S-D11: active بعيد مختلف والمحلي سليم ⇒ المحلي يبقى ثم يُدفع بsync."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib, "1.0.0")
    _cycle(lib, "2.0.0")
    store.blobs["skills/active:add_then_double"] = {"active": "1.0.0", "history": []}
    lib2, dur, _ = _lib(tmp, store)
    dur.restore()
    lib2.sync()          # الدفع يعيد البعيد طازجًا (بلا متغير مهمل)
    return {"local": json.loads((lib2.root / "add_then_double" / "active.json")
                                .read_text(encoding="utf-8"))["active"],
            "pushed": store.blobs["skills/active:add_then_double"]["active"]}


def s_status_declares(tmp):
    """S-D12: الصدق — الحالة تعلن المخزن، وبلا دوام تُعلن None لا وهمًا."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    st = lib.status()["durable"]
    plain = _lib(tmp / "plain", None)[0]
    return {"backend": st["backend"], "enabled": st["enabled"],
            "plain_honest": plain.status()["durable"] is None}


def s_sync_pushes_missing(tmp):
    """S-D13: البعيد مُمحى وsync يعيد بناءه من المحلي — تقرير بعدد المدفوع."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib)
    store.blobs.clear()
    rep = lib.sync()
    return {"pushed": rep["pushed"], "restored": rep["restored"] == [],
            "recovered": "skills/pkg:add_then_double:1.0.0" in store.blobs}


def s_boot_loads_and_runs(tmp):
    """S-D14: إقلاع كامل بقرص نظيف: المهارة مسجلة وتنفذ نتيجتها الصحيحة."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib)
    shutil.rmtree(lib.root)
    out, dur, _ = _lib(tmp, store)
    loaded = out.load_active()
    res = out.registry.invoke("skill.add_then_double", caller="owner",
                              inputs={"a": 2, "b": 3})
    return {"loaded": loaded == ["skill.add_then_double"],
            "result": res["result"]["output"]}


def s_hashless_remote_refused(tmp):
    """S-D15: حزمة بعيدة بلا بصمة صالحة تُرفض حتى لو غابت محليًا."""
    store = MemStore()
    lib, _, _ = _lib(tmp, store)
    _cycle(lib)
    del store.blobs["skills/pkg:add_then_double:1.0.0"]["content_hash"]
    shutil.rmtree(lib.root)
    lib2, dur, _ = _lib(tmp, store)
    rep = dur.restore()
    return {"refused": rep["refused"] == ["pkg:add_then_double:1.0.0"],
            "not_restored": not (lib2.root / "add_then_double").exists()}


SCENARIOS = {f.__name__[2:]: f for f in (
    s_wipe_survives, s_write_through_propose, s_full_cycle_write_through,
    s_tampered_remote_refused, s_tampered_local_repaired, s_valid_local_kept,
    s_store_down_local_recovery, s_secret_blocked, s_rollback_syncs,
    s_two_versions_fresh_boot, s_conflict_local_wins, s_status_declares,
    s_sync_pushes_missing, s_boot_loads_and_runs, s_hashless_remote_refused)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r849-e-"))
    _ev, _rec, orig = _audit()          # عدة السجل: مزيف في هذه الحالة فقط
    try:
        try:
            got = SCENARIOS[case["scenario"]](tmp)
        except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
            got = {"error": f"{type(exc).__name__}: {exc}"}
        exp = case["expect"]
        failed = [{"check": k, "want": v, "got": got.get(k)}
                  for k, v in exp.items() if got.get(k) != v]
        return {"id": case["id"], "rule": case["rule"], "pass": not failed,
                "got": got, "failed_checks": failed}
    finally:
        _restore_core(orig)
        shutil.rmtree(tmp, ignore_errors=True)


def run(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [run_case(c) for c in cases]
    passed = sum(r["pass"] for r in results)
    return {"score": round(passed / len(results), 4) if results else 0.0,
            "passed": passed, "n": len(results),
            "failures": [r for r in results if not r["pass"]]}
