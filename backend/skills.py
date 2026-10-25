# -*- coding: utf-8 -*-
"""R-757 (ROADMAP_V5 ٤.٢ + ٤.٣): اكتساب المهارات.

المهارة حزمة موثقة: name/version/source/description/inputs/permissions/steps/
output/eval. الخطوات إجراء مركب فوق أدوات مسجلة بقوالب `{{input}}` و
`{{steps.N.key}}`، تُنفذ عبر حلقة الوكيل (R-753) مقيدة بأذونات الحزمة (أداة خارج
الأذونات → invalid_step).

الدورة (لا اختصار):
  propose  → حالة proposed + بصمة محتوى SHA-256 (أثر skill.propose)
  evaluate → كل حالة مرجعية تُشغل وتُقارن بالمتوقع؛ نجاح الكل = evaluated وإلا
             failed_eval (أثر skill.evaluate؛ البصمة المقيمة تُحفظ)
  approve  → المالك فقط؛ يشترط evaluated + بصمة المحتوى الحالية = المقيمة؛
             الأثر أولًا (فشله = لا تفعيل) ثم active.json ثم أداة skill.<name>
  rollback → الإصدار المفعّل السابق (أثر skill.rollback)
  load_active → عند الإقلاع: المهارات المفعلة تُسجل من القرص (لا يُعاد تعلمها)

٤.٣ اكتشاف ≠ اكتساب: أدوات mcp.* المكتشفة تُعلن learned=False حتى تدرجها حزمة
مهارة مفعّلة في أذوناتها.

حد صادق: «التقييم» هنا مقارنة بحالات مرجعية في الحزمة نفسها (يكتبها المؤلف)؛
المقارنة بمرجع خارجي مستقل (٣.٤/R-746) تتطلب العقل الحي. والدوام عبر إعادة
النشر على Fly يتطلب ١.٤.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,48}$")
VERSION_RE = re.compile(r"^[0-9A-Za-z.\-]{1,32}$")
FORBIDDEN_PREFIXES = ("agent.run", "skills.", "skill.", "tasks.")
REQUIRED = ("name", "version", "source", "description", "permissions", "steps", "output", "eval")
_TPL = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


class SkillError(Exception):
    pass


def content_hash(manifest: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def _lookup(path: str, inputs: Dict[str, Any], history: List[Dict[str, Any]]):
    parts = path.split(".")
    if parts[0] == "steps":
        if len(parts) < 2 or not parts[1].isdigit() or int(parts[1]) >= len(history):
            raise SkillError(f"مرجع خطوة غير متاح: {path}")
        val: Any = history[int(parts[1])].get("result")
        for p in parts[2:]:
            if not isinstance(val, dict) or p not in val:
                raise SkillError(f"مفتاح غير موجود في ناتج الخطوة: {path}")
            val = val[p]
        return val
    if parts[0] not in inputs:
        raise SkillError(f"مدخل غير معطى: {parts[0]}")
    return inputs[parts[0]]


def render(value: Any, inputs: Dict[str, Any], history: List[Dict[str, Any]]):
    if isinstance(value, str):
        m = _TPL.fullmatch(value.strip())
        if m:                                   # قالب كامل → يحفظ النوع
            return _lookup(m.group(1), inputs, history)
        return _TPL.sub(lambda mm: str(_lookup(mm.group(1), inputs, history)), value)
    if isinstance(value, dict):
        return {k: render(v, inputs, history) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, inputs, history) for v in value]
    return value


class SkillPlanner:
    """يحول خطوات الحزمة إلى خطوات الحلقة — عديم الحالة (موضعه = طول السجل)."""

    kind = "skill"

    def __init__(self, manifest: Dict[str, Any], inputs: Dict[str, Any]):
        self.m, self.inputs = manifest, inputs

    def next_step(self, goal, tools, history):
        steps = self.m["steps"]
        i = len(history)
        if i >= len(steps):
            return {"action": "finish",
                    "answer": render(self.m["output"], self.inputs, history)}
        s = steps[i]
        return {"action": "call", "tool": s["tool"],
                "inputs": render(s.get("inputs") or {}, self.inputs, history),
                "check": s.get("check") or {"type": "ok"}}


def validate(m: Dict[str, Any]) -> None:
    if not isinstance(m, dict):
        raise SkillError("الحزمة ليست كائنًا")
    missing = [k for k in REQUIRED if k not in m or m[k] in (None, "", [])]
    if missing:
        raise SkillError(f"حقول ناقصة في الحزمة: {missing}")
    if not NAME_RE.match(str(m["name"])) or not VERSION_RE.match(str(m["version"])):
        raise SkillError("اسم أو إصدار غير صالح")
    if not isinstance(m["permissions"], list) or not isinstance(m["steps"], list):
        raise SkillError("الأذونات والخطوات قوائم")
    for s in m["steps"]:
        tool = (s or {}).get("tool", "")
        if not tool or any(tool == p or tool.startswith(p) for p in FORBIDDEN_PREFIXES):
            raise SkillError(f"أداة ممنوعة أو فارغة في خطوة: {tool!r}")
    cases = (m.get("eval") or {}).get("cases") or []
    if not cases:
        raise SkillError("حالات التقييم المرجعية إلزامية")


def _audit(op: str, payload: Dict[str, Any]) -> None:
    from memory.core import get_core
    get_core().append_event("skill_lifecycle", {"op": op, **payload},
                            user=payload.get("actor"))


class SkillLibrary:
    def __init__(self, root, registry, *, max_steps: int = 16):
        self.root = Path(root)
        self.registry = registry
        self.max_steps = max_steps

    # ------------------------------------------------------------ تخزين
    def _write(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".skill-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1, default=str)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def _pkg_path(self, name: str, version: str) -> Path:
        if not NAME_RE.match(name) or not VERSION_RE.match(version):
            raise SkillError("اسم أو إصدار غير صالح")
        return self.root / name / f"{version}.json"

    def _load_pkg(self, name: str, version: str) -> Dict[str, Any]:
        p = self._pkg_path(name, version)
        if not p.exists():
            raise SkillError(f"حزمة غير موجودة: {name}@{version}")
        return json.loads(p.read_text(encoding="utf-8"))

    def _active(self, name: str) -> Dict[str, Any]:
        p = self.root / name / "active.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else \
            {"active": None, "history": []}

    # ------------------------------------------------------------ تنفيذ
    def _execute(self, m: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        from agent_loop import AgentLoop
        loop = AgentLoop(self.registry, SkillPlanner(m, inputs),
                         max_steps=min(self.max_steps, len(m["steps"]) + 1),
                         allowed_tools=m["permissions"], caller=f"skill:{m['name']}")
        return loop.run(f"skill {m['name']}@{m['version']}")

    def _make_handler(self, m: Dict[str, Any]):
        lib = self

        def handler(**inputs):
            res = lib._execute(m, inputs)
            if res["status"] != "completed":
                raise SkillError(f"المهارة توقفت: {res['status']} — {res.get('error')}")
            return {"output": res["answer"], "version": m["version"],
                    "steps": len(res["steps"])}
        return handler

    def _install_tool(self, m: Dict[str, Any]) -> str:
        from tool_registry import ToolSpec
        name = f"skill.{m['name']}"
        self.registry.replace(ToolSpec(
            name=name, description=f"مهارة مكتسبة: {m['description']} (v{m['version']}، "
                                   f"المصدر: {m['source']})",
            inputs=dict(m.get("inputs") or {}), outputs="output/version/steps",
            handler=self._make_handler(m)))
        return name

    # ------------------------------------------------------------ الدورة
    def propose(self, manifest: Dict[str, Any], actor: str) -> Dict[str, Any]:
        validate(manifest)
        h = content_hash(manifest)
        name, ver = manifest["name"], str(manifest["version"])
        p = self._pkg_path(name, ver)
        if p.exists():
            raise SkillError(f"الإصدار موجود: {name}@{ver} — إصدار جديد لأي تغيير")
        _audit("skill.propose", {"skill": name, "version": ver, "content_hash": h,
                                 "source": manifest["source"], "actor": actor})
        pkg = {"manifest": manifest, "content_hash": h, "state": "proposed",
               "proposed_at": time.time(), "proposed_by": actor, "eval": None}
        self._write(p, pkg)
        return {"skill": name, "version": ver, "state": "proposed", "content_hash": h}

    def evaluate(self, name: str, version: str) -> Dict[str, Any]:
        pkg = self._load_pkg(name, version)
        m = pkg["manifest"]
        h = content_hash(m)
        if h != pkg["content_hash"]:
            raise SkillError("بصمة المحتوى لا تطابق المقترح — تلاعب")
        results = []
        for case in m["eval"]["cases"]:
            res = self._execute(m, dict(case.get("inputs") or {}))
            ok = res["status"] == "completed" and res["answer"] == case.get("expect")
            results.append({"inputs": case.get("inputs"), "expect": case.get("expect"),
                            "got": res.get("answer"), "status": res["status"], "pass": ok})
        passed = sum(r["pass"] for r in results)
        state = "evaluated" if passed == len(results) else "failed_eval"
        _audit("skill.evaluate", {"skill": name, "version": version, "content_hash": h,
                                  "passed": passed, "total": len(results), "state": state})
        pkg.update(state=state, eval={"content_hash": h, "passed": passed,
                                      "total": len(results), "results": results,
                                      "reference": m["eval"].get("reference"),
                                      "at": time.time()})
        self._write(self._pkg_path(name, version), pkg)
        return {"skill": name, "version": version, "state": state, "passed": passed,
                "total": len(results), "results": results}

    def approve(self, name: str, version: str, actor: str) -> Dict[str, Any]:
        pkg = self._load_pkg(name, version)
        if pkg["state"] != "evaluated":
            raise SkillError(f"لا اعتماد بلا تقييم ناجح (الحالة: {pkg['state']})")
        h = content_hash(pkg["manifest"])
        if h != pkg["content_hash"] or h != (pkg.get("eval") or {}).get("content_hash"):
            raise SkillError("المحتوى تغير بعد التقييم — اعتماد مرفوض")
        _audit("skill.approve", {"skill": name, "version": version, "content_hash": h,
                                 "actor": actor})       # الأثر أولًا: فشله = لا تفعيل
        act = self._active(name)
        if act["active"] and act["active"] != version:
            act["history"].append(act["active"])
        act["active"] = version
        self._write(self.root / name / "active.json", act)
        pkg.update(state="active", approved_by=actor, approved_at=time.time())
        self._write(self._pkg_path(name, version), pkg)
        tool = self._install_tool(pkg["manifest"])
        return {"skill": name, "active": version, "tool": tool}

    def rollback(self, name: str, actor: str) -> Dict[str, Any]:
        act = self._active(name)
        if not act["history"]:
            raise SkillError("لا إصدار سابق للتراجع إليه")
        prev = act["history"][-1]
        pkg = self._load_pkg(name, prev)
        if content_hash(pkg["manifest"]) != pkg["content_hash"]:
            raise SkillError("الإصدار السابق تغير على القرص — تراجع مرفوض")
        _audit("skill.rollback", {"skill": name, "from": act["active"], "to": prev,
                                  "actor": actor})
        act["history"].pop()
        act["active"] = prev
        self._write(self.root / name / "active.json", act)
        tool = self._install_tool(pkg["manifest"])
        return {"skill": name, "active": prev, "tool": tool}

    def load_active(self) -> List[str]:
        """عند الإقلاع: تسجيل المهارات المفعلة من القرص — بصمة تُفحص، لا إعادة تعلم."""
        loaded = []
        if not self.root.exists():
            return loaded
        for d in sorted(p for p in self.root.iterdir() if p.is_dir()):
            act = self._active(d.name)
            if not act["active"]:
                continue
            try:
                pkg = self._load_pkg(d.name, act["active"])
            except SkillError:  # TOLERATED: حزمة مفعلة مفقودة على القرص — لا تحميل (تظهر في status)
                continue
            if pkg.get("state") != "active" or content_hash(pkg["manifest"]) != pkg["content_hash"]:
                continue                                 # تلاعب أو حالة غير مفعلة → لا تحميل
            loaded.append(self._install_tool(pkg["manifest"]))
        return loaded

    def status(self) -> Dict[str, Any]:
        skills, learned_tools = [], set()
        if self.root.exists():
            for d in sorted(p for p in self.root.iterdir() if p.is_dir()):
                act = self._active(d.name)
                versions = []
                for f in sorted(d.glob("*.json")):
                    if f.name == "active.json":
                        continue
                    pkg = json.loads(f.read_text(encoding="utf-8"))
                    versions.append({"version": pkg["manifest"]["version"],
                                     "state": pkg["state"],
                                     "content_hash": pkg["content_hash"][:16],
                                     "eval": None if not pkg.get("eval") else
                                     f"{pkg['eval']['passed']}/{pkg['eval']['total']}"})
                    if pkg["state"] == "active" and pkg["manifest"]["version"] == act["active"]:
                        learned_tools |= set(pkg["manifest"]["permissions"])
                skills.append({"name": d.name, "active": act["active"],
                               "rollback_to": act["history"][-1] if act["history"] else None,
                               "versions": versions})
        discovered = [{"tool": t["name"], "learned": t["name"] in learned_tools,
                       "note": "متاحة ومُستخدمة في مهارة مفعلة" if t["name"] in learned_tools
                       else "متاحة غير مُتعلمة (اكتشاف ≠ اكتساب — ٤.٣)"}
                      for t in self.registry.list_tools() if t["name"].startswith("mcp.")]
        return {"skills": skills, "discovered": discovered}


_LIB: Optional[SkillLibrary] = None


def get_library() -> SkillLibrary:
    global _LIB
    if _LIB is None:
        from tool_registry import get_registry
        root = os.environ.get("SOVEREIGN_SKILLS_DIR") or str(
            Path(__file__).resolve().parents[1] / "data" / "skills")
        _LIB = SkillLibrary(root, get_registry())
    return _LIB
