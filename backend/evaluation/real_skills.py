# -*- coding: utf-8 -*-
"""R-850: مجموعة مجمّدة skills.catalog — أول مهارات حقيقية (٦.٥.١).

ثلاث مهارات من الكتالوج (تقرير صحة / تلخيص سجل / موجز بحثي) تمر بالدورة
كاملة على سجل أدوات بأشكال مخرجات الأدوات الحقيقية (مسجلة من التشغيل الحي
— forensics/R-850_live_cycle.txt)، مع عقد التقييم البنيوي الجديد:
القيم الحية تتغير بين نداء وآخر ⇒ معايير بالمسار والنوع لا مساواة حرفية.

التوقعات في data/real_skills_cases.json مكتوبة من القاعدة قبل أول تشغيل
ومجمّدة ببصمة sha256 (suites.py). كل سيناريو يبني مكتبته في tmp نظيف.
"""
from __future__ import annotations

import itertools
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import ledger_view  # noqa: E402
import skills  # noqa: E402
from tool_registry import ToolRegistry, ToolSpec  # noqa: E402

_TICK = itertools.count(1)


def _health(**_):
    comps = {n: {"status": "healthy", "type": "component", "ok": True, "detail": {}}
             for n in ("memory_core", "memory_store", "nexus_engine", "sovereign_will")}
    return {"status": "healthy", "version": "4.0.0", "timestamp": "2026-11-05T00:00:00Z",
            "uptime_seconds": 0.5 + next(_TICK), "components": comps}   # يتغير كل نداء


def _memory(**_):
    return {"core": {"core": {"last_hash": "a" * 64},
                     "index": {"total_events": 100 + next(_TICK), "total_types": 9}},
            "dynamic": {}, "store": {}, "timestamp": "2026-11-05T00:00:00Z"}


def _disk(**_):
    return {"cloud_disk": "disabled", "enabled": False,
            "local_volume": {"state": "ok", "free_gb": 12.9}}


def _brain(**_):
    return {"brain": "disabled", "enabled": False, "reply_source": "templates"}


def _experience(**_):
    return {"experiences": 0, "chain": {"entries": 0, "broken": [], "intact": True}}


class FakeCore:
    """سجل مزيف بعقد iterate_events — أحداث بحمولة وتوقيع لا يجب أن يتسربا."""

    def __init__(self, n: int = 8, break_at: int = -1):
        self.events = []
        prev = "GENESIS"
        for i in range(n):
            h = f"{i:02d}" + "f" * 62
            self.events.append({"hash": h, "prev_hash": "X" * 64 if i == break_at else prev,
                                "time": f"2026-11-05T00:00:{i:02d}Z",
                                "type": "skill.evaluate" if i % 2 else "orchestrator::log",
                                "blob": "b" * 64, "signature": "SIG", "payload": {"x": 1}})
            prev = h

    def iterate_events(self, reverse=False, limit=None):
        evs = list(reversed(self.events)) if reverse else list(self.events)
        return iter(evs[:limit] if limit else evs)


# أجوبة مسجلة من التشغيل الحي (forensics/R-850_live_cycle.txt) لأسئلة حالات المؤلف
_KNOWN = {"ما هي عاصمة اليابان؟": "العاصمة (اليابان): طوكيو",
          "What is the boiling point of water at sea level?":
              "Water boils at 100 °C (212 °F) at sea level."}


def _world(points=True):
    def h(question, target_lang=None):
        if not points:
            return {"ok": False, "points": [], "sources": [], "error": "no_results"}
        text = _KNOWN.get(question, f"نقطة عن: {question}")
        return {"ok": True, "question": question, "points": [
                    {"text": text, "source": 1, "score": 0.9}],
                "sources": [{"id": 1, "url": "https://example.org/a", "title": "A"}],
                "providers": {"bing": 1}, "method": "multi-provider", "error": None}
    return h


def _reg(core=None, world_points=True) -> ToolRegistry:
    core = core or FakeCore()
    reg = ToolRegistry()
    for name, fn in (("health.snapshot", _health), ("memory.stats", _memory),
                     ("disk.status", _disk), ("brain.status", _brain),
                     ("experience.stats", _experience),
                     ("world.answer", _world(world_points))):
        ins = {"question": "", "target_lang": ""} if name == "world.answer" else {}
        reg.register(ToolSpec(name=name, description="", inputs=ins, outputs="", handler=fn))
    reg.register(ToolSpec(name="ledger.recent", description="",
                          inputs={"limit": "", "event_type": ""}, outputs="",
                          handler=lambda limit=10, event_type=None:
                          ledger_view.recent(core, limit, event_type)))
    return reg


def _audit():
    import memory.core as mc

    class _FC:
        def append_event(self, *a, **k):
            return {"hash": "fake"}
    orig = mc.get_core
    mc.get_core = lambda: _FC()
    return orig


def _lib(tmp: Path, **kw) -> skills.SkillLibrary:
    return skills.SkillLibrary(tmp / "skills", _reg(**kw), durable=False)


OWNER = {
    "health_report": [
        {"inputs": {"component": "memory_store"}, "criteria": [
            {"id": "focus", "type": "equals", "path": "component", "value": "memory_store"}]},
        {"inputs": {"component": "sovereign_will"}, "criteria": [
            {"id": "st", "type": "equals", "path": "component_detail.status",
             "value": "healthy"}]}],
    "ledger_digest": [
        {"inputs": {"limit": 3}, "criteria": [
            {"id": "w", "type": "equals", "path": "window", "value": 3}]},
        {"inputs": {"limit": 8}, "criteria": [
            {"id": "l", "type": "equals", "path": "chain_linked", "value": True}]}],
    "research_brief": [
        {"inputs": {"question": "q-owner-1", "target_lang": "ar"}, "criteria": [
            {"id": "p", "type": "non_empty", "path": "points"}]},
        {"inputs": {"question": "q-owner-2", "target_lang": "en"}, "criteria": [
            {"id": "s", "type": "non_empty", "path": "sources.0.url"}]}],
}


def _cycle(lib, name):
    ev = lib.propose_catalog(name)
    if ev["state"] != "evaluated":
        return {"author": ev["state"]}
    ind = lib.evaluate_independent(name, "1.0.0", OWNER[name], actor="owner")
    if ind["state"] != "independently_evaluated":
        return {"author": ev["state"], "independent": ind["state"]}
    ap = lib.approve(name, "1.0.0", actor="owner")
    return {"author": ev["state"], "independent": ind["state"], "active": ap["active"],
            "tool": ap["tool"]}


# ---------------------------------------------------------------- السيناريوهات
def s_catalog_valid(tmp):
    """RS01: الكتالوج ثلاث حزم صالحة بأسماء تطابق ملفاتها."""
    names = [m["name"] for m in skills.load_catalog()]
    return {"names": names, "count": len(names)}


def s_health_cycle(tmp):
    """RS02: تقرير الصحة: دورة كاملة ثم تشغيل بمكوّن مختار."""
    lib = _lib(tmp)
    cyc = _cycle(lib, "health_report")
    out = lib.registry.invoke("skill.health_report", caller="owner",
                              inputs={"component": "nexus_engine"})["result"]["output"]
    return {**cyc, "overall": out["overall"], "component": out["component"],
            "detail_status": out["component_detail"]["status"]}


def s_ledger_cycle(tmp):
    """RS03: تلخيص السجل: دورة كاملة ثم تشغيل — نافذة وتوزيع وترابط."""
    lib = _lib(tmp)
    cyc = _cycle(lib, "ledger_digest")
    out = lib.registry.invoke("skill.ledger_digest", caller="owner",
                              inputs={"limit": 4})["result"]["output"]
    return {**cyc, "count": out["count"], "chain_linked": out["chain_linked"],
            "chain_links": out["chain_links"], "types": len(out["by_type"])}


def s_research_cycle(tmp):
    """RS04: الموجز البحثي: دورة كاملة ثم تشغيل بسؤال جديد."""
    lib = _lib(tmp)
    cyc = _cycle(lib, "research_brief")
    out = lib.registry.invoke("skill.research_brief", caller="owner",
                              inputs={"question": "سؤال", "target_lang": "ar"})["result"]["output"]
    return {**cyc, "points": len(out["points"]), "lang": out["lang"]}


def s_live_variance(tmp):
    """RS05: قيمة حية متغيرة: المعيار البنيوي ينجح والمساواة الحرفية تفشل (الثغرة)."""
    lib = _lib(tmp)
    m = json.loads((skills.CATALOG_DIR / "health_report.json").read_text(encoding="utf-8"))
    exact = dict(m, name="health_exact", eval={"cases": [
        {"inputs": {"component": "memory_core"},
         "expect": lib._execute(m, {"component": "memory_core"})["answer"]}]})
    lib.propose(exact, actor="agent")
    return {"structural": lib.propose_catalog("health_report")["state"],
            "exact": lib.evaluate("health_exact", "1.0.0")["state"]}


def s_unknown_component(tmp):
    """RS06: مكوّن غير موجود ⇒ فشل صريح لا اختراع."""
    lib = _lib(tmp)
    _cycle(lib, "health_report")
    res = lib.registry.invoke("skill.health_report", caller="owner",
                              inputs={"component": "nope"})
    return {"ok": res["ok"], "invented": "nope" in json.dumps(res.get("result") or {})}


def s_research_no_results(tmp):
    """RS07: بحث بلا نتائج ⇒ فحص الخطوة يفشل ⇒ تقييم المؤلف يفشل (لا موجز فارغ)."""
    lib = _lib(tmp, world_points=False)
    return {"author": lib.propose_catalog("research_brief")["state"]}


def s_semantic_author_rejected(tmp):
    """RS08: معيار دلالي في حالات المؤلف مرفوض — المؤلف لا يحكم على نفسه."""
    m = json.loads((skills.CATALOG_DIR / "research_brief.json").read_text(encoding="utf-8"))
    m["eval"]["cases"][0]["criteria"].append(
        {"id": "sem", "type": "semantic", "text": "الموجز يلخص المصادر بصدق"})
    try:
        skills.validate(m)
        return {"rejected": False}
    except skills.SkillError:
        return {"rejected": True}


def s_case_without_judgement(tmp):
    """RS09: حالة بلا توقع ولا معايير مرفوضة عند الاقتراح."""
    m = json.loads((skills.CATALOG_DIR / "ledger_digest.json").read_text(encoding="utf-8"))
    m["eval"]["cases"] = [{"inputs": {"limit": 2}}]
    try:
        skills.validate(m)
        return {"rejected": False}
    except skills.SkillError:
        return {"rejected": True}


def s_missing_path_fails(tmp):
    """RS10: مسار غائب في المخرج ⇒ المعيار يفشل بسبب معلن."""
    from evaluation.judge import check_deterministic
    r = check_deterministic({"id": "x", "type": "non_empty", "path": "a.b"}, {"a": {}})
    return {"pass": r["pass"], "reason": r.get("reason")}


def s_bool_not_int(tmp):
    """RS11: is_type int لا يقبل bool، وnumber يقبل int/float."""
    from evaluation.judge import check_deterministic as c
    return {"bool_as_int": c({"id": "t", "type": "is_type", "value": "int"}, True)["pass"],
            "float_number": c({"id": "t", "type": "is_type", "value": "number"}, 1.5)["pass"],
            "list_index": c({"id": "t", "type": "equals", "path": "0.k", "value": 1},
                            [{"k": 1}])["pass"]}


def s_no_self_activation(tmp):
    """RS12: الاقتراح من الكتالوج لا يفعّل؛ «catalog» لا يقيّم نفسه مستقلًا."""
    lib = _lib(tmp)
    ev = lib.propose_catalog("ledger_digest")
    registered = "skill.ledger_digest" in {t["name"] for t in lib.registry.list_tools()}
    try:
        lib.evaluate_independent("ledger_digest", "1.0.0", OWNER["ledger_digest"],
                                 actor="catalog")
        self_eval = "accepted"
    except skills.SkillError:
        self_eval = "rejected"
    return {"state": ev["state"], "registered": registered, "self_eval": self_eval}


def s_ledger_no_payload(tmp):
    """RS13: نافذة السجل بيانات وصفية فقط — لا حمولة ولا توقيع ولا blob."""
    out = ledger_view.recent(FakeCore(), 3)
    keys = sorted({k for e in out["events"] for k in e})
    return {"keys": keys, "hash_len": len(out["events"][0]["hash"]),
            "leak": any(s in json.dumps(out) for s in ("SIG", "payload", "bbbb"))}


def s_ledger_broken_link(tmp):
    """RS14: رابط مكسور داخل النافذة يُكشف ويُعد."""
    out = ledger_view.recent(FakeCore(n=8, break_at=6), 5)
    return {"chain_linked": out["chain_linked"], "broken_links": out["broken_links"]}


def s_ledger_bounds(tmp):
    """RS15: حدود النافذة 1..50 (bool مرفوض)؛ التصفية تعلن عدم فحص الترابط."""
    rejected = 0
    for bad in (0, 51, True, "x"):
        try:
            ledger_view.recent(FakeCore(), bad)
        except ledger_view.LedgerViewError:
            rejected += 1
    f = ledger_view.recent(FakeCore(), 10, "skill.evaluate")
    return {"rejected": rejected, "filtered_count": f["count"],
            "chain_checked": f["chain_checked"], "chain_linked": f["chain_linked"]}


def s_bad_catalog_rejected(tmp):
    """RS16: حزمة كتالوج اسمها لا يطابق ملفها ⇒ خطأ صريح لا تخطٍّ صامت."""
    d = tmp / "cat"
    d.mkdir(parents=True)
    m = json.loads((skills.CATALOG_DIR / "ledger_digest.json").read_text(encoding="utf-8"))
    (d / "other_name.json").write_text(json.dumps(m), encoding="utf-8")
    try:
        skills.load_catalog(d)
        return {"rejected": False}
    except skills.SkillError:
        return {"rejected": True}


def s_dynamic_key_needs_input(tmp):
    """RS17: مفتاح ديناميكي بلا مدخله ⇒ خطأ صريح؛ معه يختار المفتاح الصحيح."""
    hist = [{"result": {"c": {"a": 1, "b": 2}}}]
    try:
        skills._lookup("steps.0.c.$k", {}, hist)
        missing = "accepted"
    except skills.SkillError:
        missing = "rejected"
    return {"missing": missing, "picked": skills._lookup("steps.0.c.$k", {"k": "b"}, hist)}


def s_catalog_states(tmp):
    """RS18: حالة الكتالوج من المكتبة: not_proposed ثم active بعد الدورة."""
    lib = _lib(tmp)
    before = {s["name"]: s["state"] for s in lib.catalog()["skills"]}
    _cycle(lib, "health_report")
    after = {s["name"]: (s["state"], s["active"]) for s in lib.catalog()["skills"]}
    return {"before": before["health_report"], "after": list(after["health_report"]),
            "others": before["ledger_digest"]}


SCENARIOS = {f.__name__[2:]: f for f in (
    s_catalog_valid, s_health_cycle, s_ledger_cycle, s_research_cycle, s_live_variance,
    s_unknown_component, s_research_no_results, s_semantic_author_rejected,
    s_case_without_judgement, s_missing_path_fails, s_bool_not_int, s_no_self_activation,
    s_ledger_no_payload, s_ledger_broken_link, s_ledger_bounds, s_bad_catalog_rejected,
    s_dynamic_key_needs_input, s_catalog_states)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r850-e-"))
    orig = _audit()
    try:
        try:
            got = SCENARIOS[case["scenario"]](tmp)
        except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
            got = {"error": f"{type(exc).__name__}: {exc}"}
        failed = [{"check": k, "want": v, "got": got.get(k)}
                  for k, v in case["expect"].items() if got.get(k) != v]
        return {"id": case["id"], "rule": case["rule"], "pass": not failed,
                "got": got, "failed_checks": failed}
    finally:
        import memory.core as mc
        mc.get_core = orig
        shutil.rmtree(tmp, ignore_errors=True)


def run(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [run_case(c) for c in cases]
    passed = sum(r["pass"] for r in results)
    return {"score": round(passed / len(results), 4) if results else 0.0,
            "passed": passed, "n": len(results),
            "failures": [r for r in results if not r["pass"]]}
