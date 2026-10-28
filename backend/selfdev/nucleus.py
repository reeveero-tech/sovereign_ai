"""R-798: النواة — تجمع وتصيغ وتوجّه.

الدورة:
  1. جمع: signals.gather من كل مصادر النظام الحقيقية.
  2. ذاكرة الظواهر: لكل مفتاح first_seen/last_seen/cycles/evidence_hash — التكرار عبر
     الدورات يرفع الأولوية، واختفاء الإشارة يُسجَّل (تحقق ذاتي من جدوى الإصلاح).
  3. أولوية: وزن الشدة × (1 + log2(cycles)) × عامل العمر، والإصلاحات أولًا.
  4. صياغة: عقل الاقتراح يحلل الأعلى أولوية (max_analyses لكل دورة — العقل بطيء)،
     ولا يُعاد تحليل مفتاح قبل cooldown ما لم يتغير دليله.
  5. توجيه:
       code_fix          ⇒ محرك التطوير (source=nucleus، files_hint=الملف الهدف، والتفصيل
                            = السبب الجذري + الخطة + اختبار القبول + الدليل)
       operational/owner ⇒ محرك الأهداف المتعذرة (تصعيد صادق للمالك)
       unresolved        ⇒ محرك الأهداف المتعذرة (سُلّم: توسيع ⇒ تفكيك ⇒ المالك)
       unmet (إشارة)     ⇒ محرك الأهداف المتعذرة مباشرة (أهداف متعذرة/إصلاح مستنفد)
       no_action         ⇒ يُسجَّل فقط
  6. أثر: كل تحليل يُلحق بـ disk_log «selfdev_nucleus» (لا شيفرة، لا سر).
"""

from __future__ import annotations

import json
import math
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from . import signals as S

NAMESPACE = "selfdev_nucleus"
COOLDOWN_SECONDS = 6 * 3600
PERSIST_CYCLES = 6  # ظاهرة باقية بعد انتهاء مهمتها هذا العدد من الدورات ⇒ خلل مكوّن
KIND_BONUS = {"code_fix": 1.5, "unmet": 1.3}


def priority(sig: Dict[str, Any], mem: Dict[str, Any], now: float) -> float:
    w = S.SEVERITY_WEIGHT.get(sig.get("severity"), 1.0)
    cycles = max(1, int(mem.get("cycles") or 1))
    age_h = max(0.0, (now - float(mem.get("first_seen") or now)) / 3600.0)
    return round(w * (1 + math.log2(cycles)) * (1 + min(age_h, 48) / 48)
                 * KIND_BONUS.get(sig.get("kind_hint"), 1.0), 4)


class Nucleus:
    def __init__(self, sources: Dict[str, Callable[[], Any]], brain, engine, unmet,
                 disk: Any = None, cooldown: float = COOLDOWN_SECONDS, max_analyses: int = 1) -> None:
        self.sources = sources
        self.brain = brain
        self.engine = engine
        self.unmet = unmet
        self._disk = disk
        self.cooldown = cooldown
        self.max_analyses = max_analyses
        self._lock = threading.Lock()
        self._mem: Dict[str, Dict[str, Any]] = {}
        self._journal: List[Dict[str, Any]] = []
        self._hydrated = False
        self.cycles = 0
        self.last_cycle: Optional[Dict[str, Any]] = None
        self.persist_errors = 0

    def _disk_client(self):
        if self._disk is not None:
            return self._disk or None
        try:
            from sovereign.cloud_disk import get_cloud_disk
            return get_cloud_disk()
        except Exception:  # TOLERATED: بلا قرص سحابي — ذاكرة فقط وdurable=false معلن
            return None

    def hydrate(self) -> None:
        """استعادة آخر تحليل لكل مفتاح بعد الإقلاع — لا يُعاد تحليل ما حُلل حديثًا."""
        if self._hydrated:
            return
        self._hydrated = True
        disk = self._disk_client()
        if disk is None:
            return
        since = 0
        for _ in range(50):
            rows = disk.pull_log(NAMESPACE, since_id=since, limit=1000) or []
            for r in rows:
                since = max(since, int(r.get("id") or 0))
                a = (r.get("payload") or {}).get("analysis")
                if isinstance(a, dict) and a.get("key"):
                    m = self._mem.setdefault(a["key"], {"first_seen": a.get("at"), "cycles": 0})
                    m.update(last_analysis_at=a.get("at"), analyzed_hash=a.get("evidence_hash"),
                             route=a.get("route"), routed_to=a.get("routed_to"))
                    self._journal.append(a)
            if len(rows) < 1000:
                break
        self._journal = self._journal[-100:]

    def _persist(self, a: Dict[str, Any]) -> None:
        disk = self._disk_client()
        if disk is None:
            return
        try:
            if not disk.append_log(NAMESPACE, {"kind": "analysis", "analysis": a}):
                self.persist_errors += 1
        except Exception:  # TOLERATED: يُعد في persist_errors ويُعلن في الحالة
            self.persist_errors += 1

    def _due(self, sig: Dict[str, Any], now: float) -> bool:
        m = self._mem.get(sig["key"]) or {}
        if m.get("last_analysis_at") is None:
            return True
        if m.get("analyzed_hash") != S.evidence_hash(sig):
            return True
        return now - float(m["last_analysis_at"]) >= self.cooldown

    def _route(self, sig: Dict[str, Any], analysis: Dict[str, Any], now: float) -> str:
        route = analysis.get("route")
        if sig.get("kind_hint") == "unmet":
            if sig["key"].startswith("selfdev_exhausted:"):
                # مصدر واحد للحقيقة: محرك الأهداف يقرأ المهام المستنفدة من المحرك نفسه.
                self.unmet.sync_from_engine(now=now)
                t = self.engine.get(sig.get("ref") or "") or {}
                origin = {"owner": "owner_request", "goal": "goal_blocked"}.get(
                    t.get("source"), "repair_exhausted")
                from .unmet import unmet_id
                return unmet_id(origin, sig.get("ref") or "")
            g = self.unmet.raise_goal("goal_blocked", sig.get("ref") or sig["key"], sig["title"],
                                detail=sig.get("evidence", ""), files_tried=sig.get("files_hint"),
                                signal_key=sig["key"], now=now)
            return g["id"]
        if route == "code_fix" and "proposals" in (sig.get("origins") or []) and sig.get("ref"):
            from self_develop import task_id
            existing = self.engine.get(task_id("proposal", sig["ref"]))
            if existing:
                return existing["id"]
        if route == "code_fix" and analysis.get("target_file"):
            plan = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(analysis.get("plan") or []))
            detail = (f"السبب الجذري: {analysis.get('root_cause') or 'غير محدد (بلا عقل)'}\n"
                      f"الخطة:\n{plan or '—'}\nاختبار القبول: {analysis.get('acceptance_test') or '—'}\n"
                      f"الدليل الحرفي ({', '.join(sig.get('origins') or [])}): {sig.get('evidence')}")
            t = self.engine.request(sig["title"], detail, source="nucleus", ref=sig["key"],
                                    now=now, files_hint=[analysis["target_file"]])
            return t["id"]
        if route == "no_action":
            return "none"
        if route not in ("operational", "owner_action") and sig.get("severity") == "low":
            # ظاهرة منخفضة الشدة بلا سبب جذري مؤكد: مراقبة فقط، لا هدف يستهلك المحرك.
            return "observed"
        origin = route if route in ("operational", "owner_action") else "unresolved"
        g = self.unmet.raise_goal(origin, sig["key"], sig["title"],
                            detail=f"{analysis.get('root_cause') or ''}\nالدليل: {sig.get('evidence')}",
                            files_tried=[], signal_key=sig["key"], now=now)
        return g["id"]

    def _component_failures(self, sigs: List[Dict[str, Any]], now: float) -> List[str]:
        """الإصلاح وُجِّه وانتهت مهمته (رُقّيت أو استُنفدت) والظاهرة ما زالت تتكرر ⇒ عجز حقيقي."""
        out = []
        for sig in sigs:
            m = self._mem.get(sig["key"]) or {}
            tid = m.get("routed_to")
            if not tid or not str(tid).startswith("SD-"):
                continue
            t = self.engine.get(tid)
            if not t or t.get("status") not in ("promoted", "exhausted"):
                continue
            m["after_task_cycles"] = int(m.get("after_task_cycles") or 0) + 1
            if m["after_task_cycles"] >= PERSIST_CYCLES and not m.get("unmet_id"):
                g = self.unmet.raise_goal("component_failure", sig["key"], sig["title"],
                                    detail=(f"المهمة {tid} انتهت بحالة {t.get('status')} والظاهرة باقية "
                                            f"{m['after_task_cycles']} دورة. الدليل: {sig.get('evidence')}"),
                                    files_tried=[t["file"]] if t.get("file") else [],
                                    signal_key=sig["key"], now=now)
                m["unmet_id"] = g["id"]
                out.append(g["id"])
        return out

    def cycle(self, now: Optional[float] = None) -> Dict[str, Any]:
        self.hydrate()
        now = time.time() if now is None else now
        sigs, errors = S.gather(self.sources)
        self.cycles += 1
        with self._lock:
            for s in sigs:
                m = self._mem.setdefault(s["key"], {"first_seen": now, "cycles": 0})
                m["cycles"] = int(m.get("cycles") or 0) + 1
                m["last_seen"] = now
                m["evidence_hash"] = S.evidence_hash(s)
                m["severity"] = s["severity"]
                m["title"] = s["title"]
            active = {s["key"] for s in sigs}
            for k, m in self._mem.items():
                if k not in active and m.get("last_seen") and not m.get("gone_at"):
                    m["gone_at"] = now
                elif k in active:
                    m.pop("gone_at", None)
        component_failures = self._component_failures(sigs, now)
        ranked = sorted(sigs, key=lambda s: priority(s, self._mem[s["key"]], now), reverse=True)
        due = [s for s in ranked if self._due(s, now)]
        analyzed: List[Dict[str, Any]] = []
        for sig in due[: self.max_analyses]:
            if sig.get("kind_hint") == "unmet":
                analysis = {"route": "unmet", "target_file": None, "brain": None,
                            "root_cause": None, "plan": [], "acceptance_test": None}
            else:
                analysis = self.brain.analyze(sig)
            try:
                routed = self._route(sig, analysis, now)
            except Exception as exc:  # TOLERATED: فشل التوجيه يُسجَّل في الأثر ولا يُسقط الدورة
                routed = f"route_error:{type(exc).__name__}: {str(exc)[:160]}"
            rec = {"key": sig["key"], "at": now, "evidence_hash": S.evidence_hash(sig),
                   "priority": priority(sig, self._mem[sig["key"]], now),
                   "origins": sig.get("origins"), "severity": sig.get("severity"),
                   "title": sig.get("title"), "route": analysis.get("route"),
                   "brain": analysis.get("brain"),
                   "target_file": analysis.get("target_file"),
                   "root_cause": (analysis.get("root_cause") or "")[:600],
                   "plan": (analysis.get("plan") or [])[:6],
                   "acceptance_test": (analysis.get("acceptance_test") or "")[:400],
                   "notes": analysis.get("validation_notes") or analysis.get("reason"), "routed_to": routed}
            with self._lock:
                self._mem[sig["key"]].update(last_analysis_at=now, analyzed_hash=rec["evidence_hash"],
                                             route=rec["route"], routed_to=routed)
                self._journal.append(rec)
                self._journal = self._journal[-100:]
            self._persist(rec)
            analyzed.append(rec)
        self.last_cycle = {"at": now, "signals": len(sigs), "due": len(due),
                           "source_errors": errors, "component_failures": component_failures,
                           "analyzed": [a["key"] for a in analyzed],
                           "routes": {a["key"]: a["routed_to"] for a in analyzed}}
        return {"cycle": dict(self.last_cycle), "active_keys": sorted(active)}

    def status(self) -> Dict[str, Any]:
        self.hydrate()
        now = time.time()
        with self._lock:
            mem = json.loads(json.dumps(self._mem))
            journal = list(self._journal[-30:])
        board = sorted(({"key": k, **v} for k, v in mem.items() if not v.get("gone_at")),
                       key=lambda x: (x.get("cycles") or 0), reverse=True)[:50]
        return {"engine": "R-798 nucleus", "cycles": self.cycles, "last_cycle": self.last_cycle,
                "durable": self._disk_client() is not None, "persist_errors": self.persist_errors,
                "sources": sorted(self.sources), "cooldown_seconds": self.cooldown,
                "max_analyses_per_cycle": self.max_analyses,
                "brain": {"calls": self.brain.calls, "failures": self.brain.failures},
                "active_signals": board, "resolved_signals":
                    [{"key": k, "gone_at": v["gone_at"], "route": v.get("route")}
                     for k, v in mem.items() if v.get("gone_at")][:50],
                "journal": journal, "now": now}
