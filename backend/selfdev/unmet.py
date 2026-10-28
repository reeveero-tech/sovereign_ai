"""R-798: محرك الأهداف المتعذرة — ما عجز عنه النظام لا يُنسى ولا يُخفى.

الأصول (origin):
  repair_exhausted   إصلاح استنفد محاولاته في محرك التطوير (RED/تحقق/CI)
  owner_request      طلب من المالك استنفد محاولاته
  goal_blocked       هدف استقلال أعلن العقل تعذّره بالأدوات المتاحة
  component_failure  خلل مكوّن متكرر عبر دورات النواة رغم المعالجة
  unresolved         إشارة لم يستطع عقل الاقتراح توجيهها إلى ملف قابل للتعديل
  operational        خلل تشغيلي لا يحله تعديل الشيفرة (شبكة/عقل/مورد)
  owner_action       يحتاج قرار المالك أو سرًا أو إعدادًا

سُلّم التصعيد (جولة لكل خطوة؛ كل جولة تترك أثرًا في disk_log «selfdev_unmet»):
  1. widen      إعادة الطلب لمحرك التطوير بسياق موسّع: كل أسباب الفشل السابقة حرفيًا،
                واستبعاد الملفات المجرَّبة (exclude_files) ليبحث في موضع آخر.
  2. decompose  العقل يفكك الهدف إلى 1-3 مهام أصغر مستقلة (مخطط JSON)؛ كل منها طلب.
  3. owner      needs_owner: تقرير صادق بكل ما جُرِّب ولماذا فشل — القرار للمالك.
operational/owner_action ⇒ owner مباشرة (لا تعديل شيفرة يحلها).

الحل (resolved): مهمة مولَّدة صارت promoted، أو الإشارة المصدر اختفت من النظام
(للأصول المرتبطة بإشارة حية). لا «حل» بلا دليل.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

NAMESPACE = "selfdev_unmet"
LADDER = ("widen", "decompose", "owner")
DIRECT_OWNER = ("operational", "owner_action")
SIGNAL_BOUND = ("component_failure", "unresolved", "operational", "owner_action")
DONE_TASK = ("promoted",)
FAILED_TASK = ("exhausted",)

DECOMPOSE_SYSTEM = (
    "أنت مهندس برمجيات. هدف عجز النظام عن تحقيقه بعد محاولات فاشلة (أسبابها حرفيًا أدناه). "
    "فكّكه إلى مهمة واحدة حتى ثلاث مهام أصغر مستقلة، كل منها تعديل صغير واحد قابل "
    "للاختبار في ملف واحد. لا تكرر ما فشل. أجب JSON فقط."
)
DECOMPOSE_SCHEMA = {
    "type": "object",
    "properties": {"subtasks": {"type": "array", "items": {
        "type": "object",
        "properties": {"title": {"type": "string"}, "detail": {"type": "string"},
                       "file": {"type": "string"}},
        "required": ["title", "detail"]}}},
    "required": ["subtasks"],
}


def unmet_id(origin: str, ref: str) -> str:
    return "U-" + hashlib.sha256(f"{origin}:{ref}".encode("utf-8")).hexdigest()[:8]


class UnmetGoals:
    def __init__(self, engine, brain: Optional[Callable[[str, str, Dict[str, Any]], Optional[str]]] = None,
                 disk: Any = None) -> None:
        self.engine = engine
        self._brain = brain
        self._disk = disk
        self._lock = threading.Lock()
        self._goals: Dict[str, Dict[str, Any]] = {}
        self._hydrated = False
        self.cycles = 0
        self.last_cycle: Optional[Dict[str, Any]] = None
        self.persist_errors = 0

    # ---------- الدوام ----------
    def _disk_client(self):
        if self._disk is not None:
            return self._disk or None
        try:
            from sovereign.cloud_disk import get_cloud_disk
            return get_cloud_disk()
        except Exception:  # TOLERATED: بلا قرص سحابي — ذاكرة فقط وdurable=false معلن
            return None

    def _persist(self, g: Dict[str, Any]) -> None:
        disk = self._disk_client()
        if disk is None:
            return
        try:
            if not disk.append_log(NAMESPACE, {"kind": "unmet", "goal": g}):
                self.persist_errors += 1
        except Exception:  # TOLERATED: يُعد في persist_errors ويُعلن في الحالة
            self.persist_errors += 1

    def hydrate(self) -> None:
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
                g = (r.get("payload") or {}).get("goal")
                if isinstance(g, dict) and g.get("id"):
                    self._goals[g["id"]] = g
            if len(rows) < 1000:
                break

    # ---------- الإدخال ----------
    def raise_goal(self, origin: str, ref: str, title: str, detail: str = "",
             files_tried: Optional[List[str]] = None, signal_key: Optional[str] = None,
             now: Optional[float] = None) -> Dict[str, Any]:
        self.hydrate()
        now = time.time() if now is None else now
        gid = unmet_id(origin, ref)
        with self._lock:
            g = self._goals.get(gid)
            if g is not None:
                return dict(g)
            g = {"id": gid, "origin": origin, "ref": ref, "title": str(title)[:300],
                 "detail": str(detail)[:3000], "signal_key": signal_key,
                 "files_tried": [f for f in (files_tried or []) if f][:20],
                 "failures": [], "round": 0, "status": "open", "tasks": [],
                 "strategies": [], "created_at": now, "updated_at": now}
            self._goals[gid] = g
            snap = json.loads(json.dumps(g))
        self._persist(snap)
        return snap

    def sync_from_engine(self, now: Optional[float] = None) -> int:
        """مهام استنفدت محاولاتها (ليست من هذا المحرك) ⇒ أهداف متعذرة."""
        n = 0
        st = self.engine.status()
        for t in st.get("tasks") or []:
            if t.get("status") != "exhausted" or t.get("source") == "unmet":
                continue
            origin = "owner_request" if t.get("source") == "owner" else (
                "goal_blocked" if t.get("source") == "goal" else "repair_exhausted")
            gid = unmet_id(origin, t["id"])
            if gid in self._goals:
                continue
            errs = ", ".join(t.get("errors") or []) or str((t.get("ci") or {}).get("reason") or "")
            g = self.raise_goal(origin, t["id"], t.get("title") or t["id"],
                          detail=f"المهمة {t['id']} استنفدت {t.get('attempts')} محاولات",
                          files_tried=[t.get("file")] if t.get("file") else [], now=now)
            with self._lock:
                self._goals[g["id"]]["failures"].append(f"{t['id']}: {errs}"[:600])
            n += 1
        return n

    # ---------- التصعيد ----------
    def _step(self, g: Dict[str, Any], now: float) -> str:
        if g["origin"] in DIRECT_OWNER:
            return "owner"
        return LADDER[min(g["round"], len(LADDER) - 1)]

    def _spawn(self, g: Dict[str, Any], strategy: str, now: float) -> List[str]:
        failures = "\n".join(g.get("failures") or [])[-1500:]
        base = (f"{g['detail']}\nهدف متعذر ({g['origin']}) — الجولة {g['round'] + 1} "
                f"({strategy}). ما فشل سابقًا حرفيًا:\n{failures or 'لا شيء مسجل'}")
        ids: List[str] = []
        if strategy == "widen":
            t = self.engine.request(f"[{g['id']} r{g['round'] + 1}] {g['title']}"[:300], base,
                                    source="unmet", ref=f"{g['id']}:r{g['round'] + 1}", now=now,
                                    exclude_files=g.get("files_tried"))
            ids.append(t["id"])
        elif strategy == "decompose":
            subs = self._decompose(g, base)
            for i, sub in enumerate(subs[:3]):
                hint = [sub["file"]] if sub.get("file") else None
                t = self.engine.request(
                    f"[{g['id']} r{g['round'] + 1}.{i + 1}] {sub['title']}"[:300],
                    f"{sub.get('detail', '')}\nجزء من هدف متعذر: {g['title']}\n{base}",
                    source="unmet", ref=f"{g['id']}:r{g['round'] + 1}:{i}", now=now,
                    files_hint=hint, exclude_files=g.get("files_tried"))
                ids.append(t["id"])
        return ids

    def _decompose(self, g: Dict[str, Any], base: str) -> List[Dict[str, Any]]:
        if self._brain is None:
            return []
        raw = self._brain(DECOMPOSE_SYSTEM, f"الهدف: {g['title']}\n{base}", DECOMPOSE_SCHEMA)
        try:
            m = re.search(r"\{.*\}", raw or "", re.S)
            d = json.loads(m.group(0)) if m else {}
        except ValueError:  # TOLERATED: رد غير صالح = لا تفكيك (يُسجل في الاستراتيجية)
            d = {}
        subs = []
        for s in (d.get("subtasks") or [])[:3]:
            if isinstance(s, dict) and str(s.get("title") or "").strip():
                subs.append({"title": str(s["title"])[:200], "detail": str(s.get("detail") or "")[:1500],
                             "file": str(s.get("file") or "") or None})
        return subs

    def _advance(self, g: Dict[str, Any], now: float) -> Dict[str, Any]:
        step = self._step(g, now)
        if step == "owner":
            g["status"] = "needs_owner"
            g["strategies"].append({"round": g["round"] + 1, "strategy": "owner", "at": now,
                                    "tasks": [], "outcome": "escalated"})
            g["owner_report"] = (f"عجز النظام عن «{g['title']}» ({g['origin']}) بعد {g['round']} "
                                 f"جولة. ما جُرِّب: {[s['strategy'] for s in g['strategies'][:-1]]}. "
                                 f"الإخفاقات: {(g.get('failures') or [])[-3:]}")
            return {"goal": g["id"], "step": "owner"}
        ids = self._spawn(g, step, now)
        g["strategies"].append({"round": g["round"] + 1, "strategy": step, "at": now,
                                "tasks": ids, "outcome": "spawned" if ids else "nothing_spawned"})
        g["tasks"].extend(ids)
        g["round"] += 1
        g["status"] = "retrying" if ids else "open"
        return {"goal": g["id"], "step": step, "tasks": ids}

    def _review(self, g: Dict[str, Any], active_keys: Optional[set]) -> Optional[str]:
        """retrying ⇒ resolved/open حسب نتائج المهام الحقيقية؛ None = ما زال ينتظر."""
        if (active_keys is not None and g["origin"] in SIGNAL_BOUND and g.get("signal_key")
                and g["signal_key"] not in active_keys):
            return "resolved_signal_gone"
        cur = g["strategies"][-1] if g["strategies"] else None
        if g["status"] != "retrying" or not cur:
            return None
        tasks = [self.engine.get(t) for t in cur.get("tasks") or []]
        tasks = [t for t in tasks if t]
        if any(t["status"] in DONE_TASK for t in tasks):
            return "resolved_promoted"
        if tasks and all(t["status"] in FAILED_TASK for t in tasks):
            for t in tasks:
                if t.get("file"):
                    g["files_tried"].append(t["file"])
                g["failures"].append(f"{t['id']}: {', '.join(t.get('errors') or [])} "
                                     f"{(t.get('ci') or {}).get('reason') or ''}"[:600])
            cur["outcome"] = "failed"
            return "round_failed"
        return None

    def cycle(self, active_keys: Optional[set] = None, now: Optional[float] = None,
              max_advance: int = 1) -> Dict[str, Any]:
        self.hydrate()
        now = time.time() if now is None else now
        self.cycles += 1
        synced = self.sync_from_engine(now=now)
        resolved, advanced = [], []
        changed: List[Dict[str, Any]] = []
        with self._lock:
            goals = sorted(self._goals.values(), key=lambda x: x.get("created_at") or 0)
        for g in goals:
            if g["status"] in ("resolved", "needs_owner"):
                continue
            verdict = self._review(g, active_keys)
            if verdict and verdict.startswith("resolved"):
                g["status"], g["resolution"], g["updated_at"] = "resolved", verdict, now
                resolved.append(g["id"])
                changed.append(g)
            elif verdict == "round_failed":
                g["status"], g["updated_at"] = "open", now
                changed.append(g)
        for g in goals:
            if len(advanced) >= max_advance:
                break
            if g["status"] == "open":
                advanced.append(self._advance(g, now))
                g["updated_at"] = now
                changed.append(g)
        for g in changed:
            self._persist(json.loads(json.dumps(g)))
        self.last_cycle = {"at": now, "synced": synced, "resolved": resolved, "advanced": advanced}
        return dict(self.last_cycle)

    def status(self) -> Dict[str, Any]:
        self.hydrate()
        with self._lock:
            items = [json.loads(json.dumps(g)) for g in self._goals.values()]
        items.sort(key=lambda g: g.get("updated_at") or 0, reverse=True)
        counts: Dict[str, int] = {}
        for g in items:
            counts[g["status"]] = counts.get(g["status"], 0) + 1
        return {"engine": "R-798 unmet", "cycles": self.cycles, "last_cycle": self.last_cycle,
                "durable": self._disk_client() is not None, "persist_errors": self.persist_errors,
                "ladder": list(LADDER), "counts": counts, "goals": items[:50]}
