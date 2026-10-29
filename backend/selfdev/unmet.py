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

بوابة الدليل (R-804) قبل كل جولة توسيع/تفكيك: محدد المواضع يجمع من الشيفرة الحقيقية مواضع
قابلة للتعديل (ليست مصدر الإنذار، ولا مجرَّبة سابقًا) مع نص السطر حرفيًا. بلا دليل ⇒ لا مهمة
غامضة (outcome=no_evidence) ويتقدم السُلّم بصدق نحو المالك. التفكيك: ملف كل مهمة فرعية من
قائمة الدليل (enum)، واقتباسها الحرفي يجب أن يوجد في الملف فعلًا وإلا تُرفض وتُسجَّل.

الحل (resolved): مهمة مولَّدة صارت promoted، أو الإشارة المصدر اختفت من النظام
(للأصول المرتبطة بإشارة حية). لا «حل» بلا دليل.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from pathlib import Path
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
                       "file": {"type": "string"}, "evidence": {"type": "string"}},
        "required": ["title", "detail"]}}},
    "required": ["subtasks"],
}


MAX_EVIDENCE = 3
MIN_QUOTE = 8
MIN_IDENT = 5
RARE_MIN_FILES = 3
RARE_FRACTION = 0.03
FILE_SUFFIXES = (".py", ".json", ".md", ".txt", ".yml", ".yaml", ".js", ".html")
EVIDENCE_RULE = ("لكل مهمة فرعية: file من قائمة الملفات المعروضة فقط، وevidence سطر منسوخ حرفيًا "
                 "من ذلك الملف يثبت موضع الخلل. مهمة بلا ملف أو باقتباس غير موجود تُرفض.")


CODE_LIKE = re.compile(r"_|\.|[a-z][A-Z]")


def _word(ident: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(ident) + r"(?![A-Za-z0-9_])")


def sd_allowed(rel: str) -> bool:
    import self_develop
    return self_develop.is_allowed(rel)


def unmet_id(origin: str, ref: str) -> str:
    return "U-" + hashlib.sha256(f"{origin}:{ref}".encode("utf-8")).hexdigest()[:8]


class UnmetGoals:
    def __init__(self, engine, brain: Optional[Callable[[str, str, Dict[str, Any]], Optional[str]]] = None,
                 disk: Any = None, locator: Any = None) -> None:
        self.engine = engine
        self._locator = locator
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
            # R-804: الهدف يرث نص المهمة الأصلي ودليلها (كان يرث «استنفدت N محاولات» فقط).
            b = self.engine.brief(t["id"]) if hasattr(self.engine, "brief") else {}
            orig = (f"\nنص المهمة الأصلية:\n{b['detail'][:1800]}" if b.get("detail") else "")
            g = self.raise_goal(origin, t["id"], t.get("title") or t["id"],
                          detail=f"المهمة {t['id']} استنفدت {t.get('attempts')} محاولات{orig}",
                          files_tried=[t.get("file")] if t.get("file") else [], now=now)
            with self._lock:
                self._goals[g["id"]].setdefault("source_files", list(b.get("files_hint") or [])[:5])
                if t.get("source") == "nucleus" and t.get("ref"):
                    # مفتاح الإنذار الأصلي — كي يبقى مصدره خارج الدليل (R-803) في الجولات اللاحقة
                    self._goals[g["id"]].setdefault("alarm_key", str(t["ref"]))
            with self._lock:
                self._goals[g["id"]]["failures"].append(f"{t['id']}: {errs}"[:600])
            n += 1
        return n

    # ---------- التصعيد ----------
    def _step(self, g: Dict[str, Any], now: float) -> str:
        if g["origin"] in DIRECT_OWNER:
            return "owner"
        return LADDER[min(g["round"], len(LADDER) - 1)]

    # ---------- بوابة الدليل (R-804) ----------
    def _get_locator(self):
        if self._locator is None:
            from .locator import Locator
            self._locator = Locator(repo_root=self.engine.repo_root, engine=self.engine)
        return self._locator

    def _file_text(self, rel: str) -> Optional[str]:
        return self.engine.read(rel) if hasattr(self.engine, "read") else None

    def _rare_identifiers(self, text: str) -> List[str]:
        """معرّفات النص النادرة في الشيفرة (تظهر في ملفات قليلة) مرتبة من الأندر — الكلمات العامة
        مثل data/json/backend ليست دليلًا (دليل حي R-804: كانت تجرّ ملفات لا علاقة لها)."""
        from .locator import identifiers
        loc = self._get_locator()
        files = loc.index()
        cap = max(RARE_MIN_FILES, int(len(files) * RARE_FRACTION))
        stems = {Path(m).stem for m in re.findall(r"[\w./-]+\.(?:py|json|md|js|html|ya?ml)", text or "")}
        out = []
        for ident in dict.fromkeys(i.strip(".") for i in identifiers(text)):
            if ident.endswith(FILE_SUFFIXES) or len(ident) < MIN_IDENT or ident in stems:
                continue
            if not CODE_LIKE.search(ident):  # كلمة إنجليزية عادية (waiting/props) ليست معرّفًا
                continue
            pat = _word(ident)
            df = sum(1 for rel in files if pat.search(loc._read(rel) or ""))
            if 0 < df <= cap:
                out.append((df, ident))
        out.sort(key=lambda x: (x[0], -len(x[1])))
        return [i for _, i in out]

    def evidence(self, g: Dict[str, Any]) -> List[Dict[str, Any]]:
        """مواضع حقيقية قابلة للتعديل: سطر يحوي معرّفًا نادرًا من نص الهدف، منسوخ حرفيًا.
        لا مصدر الإنذار (R-803) ولا ملف مجرَّب سابقًا."""
        loc = self._get_locator()
        alarm = {"key": g.get("signal_key") or g.get("alarm_key") or "",
                 "evidence": g.get("detail") or ""}
        rare = self._rare_identifiers(" ".join([g.get("title") or "", g.get("detail") or ""]))
        if not rare:
            return []
        tried = set(g.get("files_tried") or [])
        order = list(g.get("source_files") or []) + [l["file"] for l in loc.locate(
            {"key": "", "title": g.get("title") or "", "evidence": " ".join(rare)})]
        order += loc.index()
        out: List[Dict[str, Any]] = []
        seen = set()
        for rel in order:
            if rel in seen:
                continue
            seen.add(rel)
            if rel in tried or not sd_allowed(rel) or loc.is_detector(rel, alarm):
                continue
            text = self._file_text(rel)
            if not text:
                continue
            hit = next((i for i in rare if _word(i).search(text)), None)
            if hit is None:
                continue
            lines = text.splitlines()
            n = next(k for k, ln in enumerate(lines) if _word(hit).search(ln))
            quote = lines[n].strip()
            if len(quote) < MIN_QUOTE:
                continue
            out.append({"file": rel, "line": n + 1, "why": f"يحوي المعرّف النادر {hit}",
                        "ident": hit, "quote": quote[:300]})
            if len(out) >= MAX_EVIDENCE:
                break
        return out

    @staticmethod
    def _evidence_block(ev: List[Dict[str, Any]]) -> str:
        return "الدليل الفعلي من الشيفرة (موضع: نص حرفي):\n" + "\n".join(
            f"- {e['file']}:{e['line']}: {e['quote']}  ({e['why']})" for e in ev)

    def _spawn(self, g: Dict[str, Any], strategy: str, now: float) -> List[str]:
        failures = "\n".join(g.get("failures") or [])[-1500:]
        base = (f"{g['detail']}\nهدف متعذر ({g['origin']}) — الجولة {g['round'] + 1} "
                f"({strategy}). ما فشل سابقًا حرفيًا:\n{failures or 'لا شيء مسجل'}")
        ids: List[str] = []
        ev = self.evidence(g)
        g["evidence"] = ev
        if not ev:
            # R-804: لا ملف ولا سطر حقيقي ⇒ لا مهمة غامضة تستهلك العقل والمحرك.
            g["last_gate"] = "no_evidence"
            return ids
        g["last_gate"] = "evidence"
        base = f"{base}\n{self._evidence_block(ev)}"
        ev_files = [e["file"] for e in ev]
        if strategy == "widen":
            t = self.engine.request(f"[{g['id']} r{g['round'] + 1}] {g['title']}"[:300], base,
                                    source="unmet", ref=f"{g['id']}:r{g['round'] + 1}", now=now,
                                    files_hint=ev_files, exclude_files=g.get("files_tried"))
            ids.append(t["id"])
        elif strategy == "decompose":
            subs = self._decompose(g, base, ev_files)
            for i, sub in enumerate(subs[:3]):
                hint = [sub["file"]]
                t = self.engine.request(
                    f"[{g['id']} r{g['round'] + 1}.{i + 1}] {sub['title']}"[:300],
                    f"{sub.get('detail', '')}\nالاقتباس المثبت من {sub['file']}: {sub['evidence']}\n"
                    f"جزء من هدف متعذر: {g['title']}\n{base}",
                    source="unmet", ref=f"{g['id']}:r{g['round'] + 1}:{i}", now=now,
                    files_hint=hint, exclude_files=g.get("files_tried"))
                ids.append(t["id"])
        return ids

    def _decompose(self, g: Dict[str, Any], base: str,
                   ev_files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if self._brain is None:
            return []
        ev_files = list(ev_files or [])
        schema = json.loads(json.dumps(DECOMPOSE_SCHEMA))
        item = schema["properties"]["subtasks"]["items"]
        item["properties"]["file"]["enum"] = ev_files
        item["required"] = ["title", "detail", "file", "evidence"]
        snippets = "\n\n".join(f"### {f}\n{self._get_locator().snippet({'file': f, 'line': e['line']})}"
                                for f, e in ((e["file"], e) for e in g.get("evidence") or []))
        raw = self._brain(DECOMPOSE_SYSTEM + " " + EVIDENCE_RULE,
                          f"الهدف: {g['title']}\n{base}\nالملفات المسموحة: {ev_files}\n{snippets}", schema)
        try:
            m = re.search(r"\{.*\}", raw or "", re.S)
            d = json.loads(m.group(0)) if m else {}
        except ValueError:  # TOLERATED: رد غير صالح = لا تفكيك (يُسجل في الاستراتيجية)
            d = {}
        subs, rejected = [], []
        for s in (d.get("subtasks") or [])[:3]:
            if not (isinstance(s, dict) and str(s.get("title") or "").strip()):
                continue
            rel, quote = str(s.get("file") or ""), str(s.get("evidence") or "").strip()
            title = str(s["title"])[:200]
            # R-804: ملف من قائمة الدليل فقط، واقتباس حرفي موجود فعلًا في ذلك الملف.
            if rel not in ev_files:
                rejected.append({"title": title, "reason": f"file_not_in_evidence:{rel}"[:200]})
                continue
            if len(quote) < MIN_QUOTE or quote not in (self._file_text(rel) or ""):
                rejected.append({"title": title, "reason": "quote_not_found_in_file"})
                continue
            subs.append({"title": title, "detail": str(s.get("detail") or "")[:1500],
                         "file": rel, "evidence": quote[:300]})
        g["rejected_subtasks"] = rejected
        return subs

    def _advance(self, g: Dict[str, Any], now: float) -> Dict[str, Any]:
        step = self._step(g, now)
        if step == "owner":
            g["status"] = "needs_owner"
            g["strategies"].append({"round": g["round"] + 1, "strategy": "owner", "at": now,
                                    "tasks": [], "outcome": "escalated"})
            g["owner_report"] = (f"عجز النظام عن «{g['title']}» ({g['origin']}) بعد {g['round']} "
                                 f"جولة. ما جُرِّب: {[s['strategy'] for s in g['strategies'][:-1]]}. "
                                 f"الإخفاقات: {(g.get('failures') or [])[-3:]}"
                                 + ("، ولم يُعثر على دليل في الشيفرة (ملف/سطر قابل للتعديل)"
                                    if any(s.get("outcome") == "no_evidence" for s in g["strategies"])
                                    else ""))
            return {"goal": g["id"], "step": "owner"}
        ids = self._spawn(g, step, now)
        outcome = "spawned" if ids else (
            "no_evidence" if g.get("last_gate") == "no_evidence" else "nothing_spawned")
        g["strategies"].append({"round": g["round"] + 1, "strategy": step, "at": now,
                                "tasks": ids, "outcome": outcome,
                                "evidence": [f"{e['file']}:{e['line']}" for e in g.get("evidence") or []],
                                "rejected": list(g.pop("rejected_subtasks", []) or [])})
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
