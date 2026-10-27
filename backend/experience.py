# -*- coding: utf-8 -*-
"""R-790 (ROADMAP_V6 ٦.٩.١ + ٦.٩.٥): الخبرة والمعرفة المكتسبة.

سؤال المالك (2026-10-27): «هل يستطيع أن يكتسب خبرة ومعرفة؟» — قبل هذه الوحدة: لا.
كل تشغيل للوكيل كان يبدأ من الصفر؛ لا شيء يتذكر ما نجح وما فشل.

الآن:
- **الخبرة:** كل تشغيل (محادثة، عامل، مدير، هدف) يُسجَّل حقيقةً كما وقع: الهدف، الأدوات
  التي استُدعيت بالترتيب، الحالة، الزمن، الخطأ الفعلي. لا يُكتب «درس» مختلق: الدرس هو الوقائع.
- **الاسترجاع:** `recall(goal)` يعيد أقرب التجارب السابقة (تشابه كلمات) — يُحقن في تعليمات
  الموجّه والمدير، فيتعلم العقل من نتائجه: أي أداة أجابت عن سؤال مشابه، وأيها فشلت ولماذا.
- **إحصاء الأدوات:** نسبة نجاح كل أداة من الوقائع المسجلة.
- **المعرفة:** حقائق يحفظها الوكيل بمصدرها (`remember`) وتسترجع بالسؤال (`recall_facts`).

الضمانات (المادة ٨ — الذاكرة لا تُفقد أبدًا):
- إلحاق فقط (JSONL + fsync)، لا إعادة كتابة ولا حذف؛ سلسلة تجزئة prev_hash → hash.
- سطر تالف لا يُسقط غيره (يُعدّ ويُعلن في stats، ولا يُمحى).
- الجذر: SOVEREIGN_EXPERIENCE_DIR، وإلا SOVEREIGN_DATA_ROOT/experience، وإلا data/experience.
- لا أسرار: النصوص تُقتطع، والمدخلات تُحفظ مفاتيح فقط لا قيمًا.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_TOKEN = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
# حروف عربية زائدة شائعة تُنزع لتقارب الكلمات (ال التعريف، و/ف/ب/ل)
_PREFIXES = ("وال", "بال", "فال", "كال", "لل", "ال")
_STOP = frozenset({"في", "من", "على", "عن", "إلى", "الى", "ما", "هل", "هو", "هي", "أن", "ان",
                   "the", "a", "an", "of", "to", "is", "and", "or", "كم", "كيف", "لماذا", "متى",
                   "أين", "اين", "هذا", "هذه", "ذلك", "تلك", "مع", "او", "أو", "لا", "نعم"})
TEXT_CAP = 600


def _norm_token(t: str) -> str:
    t = t.lower()
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    for p in _PREFIXES:
        if t.startswith(p) and len(t) - len(p) >= 2:
            t = t[len(p):]
            break
    return t


def tokens(text: str) -> set:
    out = set()
    for raw in _TOKEN.findall(text or ""):
        t = _norm_token(raw)
        if len(t) >= 2 and t not in _STOP:
            out.add(t)
    return out


def grams(text: str) -> set:
    """مقاطع ثلاثية الأحرف لكل كلمة — تقارب صيغ الكلمة العربية (ذاكرتك/الذاكرة)."""
    out = set()
    for t in tokens(text):
        if len(t) <= 3:
            out.add(t)
        else:
            out.update(t[i:i + 3] for i in range(len(t) - 2))
    return out


def similarity(a: str, b: str) -> float:
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / float(len(ga | gb))


def _cap(s: Any, n: int = TEXT_CAP) -> Optional[str]:
    if s is None:
        return None
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "…"


def default_root() -> str:
    explicit = os.environ.get("SOVEREIGN_EXPERIENCE_DIR")
    if explicit:
        return explicit
    data_root = os.environ.get("SOVEREIGN_DATA_ROOT")
    if data_root:
        return os.path.join(data_root, "experience")
    return str(Path(__file__).resolve().parents[1] / "data" / "experience")


class ExperienceStore:
    """مخزن إلحاقي للخبرة والمعرفة — ملف لكل نوع."""

    # R-791: أحداث الأهداف (goals.GoalStore) في الملف الإلحاقي الثالث
    FILES = {"experience": "experience.jsonl", "fact": "knowledge.jsonl", "goal": "goals.jsonl"}

    def __init__(self, root: str):
        self.root = Path(root)
        self._lock = threading.Lock()
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._corrupt: Dict[str, int] = {}
        self._mtime: Dict[str, float] = {}

    # -------------------------------------------------------------- تخزين
    def _path(self, kind: str) -> Path:
        return self.root / self.FILES[kind]

    def _load(self, kind: str) -> List[Dict[str, Any]]:
        p = self._path(kind)
        try:
            st = p.stat()
        except FileNotFoundError:
            self._cache[kind], self._corrupt[kind] = [], 0
            return []
        key = st.st_mtime_ns + st.st_size
        if kind in self._cache and self._mtime.get(kind) == key:
            return self._cache[kind]
        rows, bad = [], 0
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    bad += 1          # سطر تالف يُعدّ ولا يُمحى (المادة ٨)
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
                else:
                    bad += 1
        self._cache[kind], self._corrupt[kind], self._mtime[kind] = rows, bad, key
        return rows

    def _append(self, kind: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            rows = self._load(kind)
            prev = rows[-1].get("hash") if rows else None
            entry = dict(entry)
            entry.setdefault("id", uuid.uuid4().hex[:12])
            entry.setdefault("ts", time.time())
            entry["prev_hash"] = prev
            body = json.dumps(entry, ensure_ascii=False, sort_keys=True, default=str)
            entry["hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()[:24]
            self.root.mkdir(parents=True, exist_ok=True)
            line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
            with open(self._path(kind), "a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
            self._mtime.pop(kind, None)   # يُعاد التحميل عند القراءة التالية
            return entry

    # -------------------------------------------------------------- الخبرة
    def record(self, *, source: str, goal: str, status: str,
               tools: Iterable[str] = (), duration_s: Optional[float] = None,
               error: Any = None, answer: Any = None,
               steps: Optional[List[Dict[str, Any]]] = None,
               meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """تسجيل ما وقع فعلًا — لا تفسير ولا درس مختلق."""
        step_view = []
        for s in steps or []:
            step_view.append({"tool": s.get("tool"), "ok": s.get("ok"),
                              "inputs": sorted((s.get("inputs") or {}).keys()),
                              "error": _cap(s.get("error"), 200)})
        return self._append("experience", {
            "source": str(source)[:60], "goal": _cap(goal, 400), "status": str(status),
            "tools": [str(t) for t in tools if t], "duration_s": duration_s,
            "error": _cap(error, 300), "answer": _cap(answer, 400),
            "steps": step_view, "meta": meta or {}})

    def recall(self, goal: str, k: int = 4, min_score: float = 0.12) -> List[Dict[str, Any]]:
        rows = self._load("experience")
        scored = []
        for r in rows:
            sc = similarity(goal, r.get("goal") or "")
            if sc >= min_score:
                scored.append((sc, r.get("ts") or 0, r))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        out = []
        for sc, _ts, r in scored[:max(0, int(k))]:
            out.append({"goal": r.get("goal"), "status": r.get("status"),
                        "tools": r.get("tools"), "error": r.get("error"),
                        "answer": _cap(r.get("answer"), 200),
                        "score": round(sc, 3), "ts": r.get("ts")})
        return out

    def tool_stats(self) -> Dict[str, Dict[str, Any]]:
        stats: Dict[str, Dict[str, Any]] = {}
        for r in self._load("experience"):
            for s in r.get("steps") or []:
                t = s.get("tool")
                if not t:
                    continue
                d = stats.setdefault(t, {"calls": 0, "ok": 0, "failed": 0, "last_error": None})
                d["calls"] += 1
                if s.get("ok"):
                    d["ok"] += 1
                else:
                    d["failed"] += 1
                    d["last_error"] = s.get("error") or d["last_error"]
        for d in stats.values():
            d["success_rate"] = round(d["ok"] / d["calls"], 3) if d["calls"] else None
        return stats

    # -------------------------------------------------------------- المعرفة
    def remember(self, fact: str, source: str = "", *, by: str = "agent",
                 topic: str = "") -> Dict[str, Any]:
        fact = (fact or "").strip()
        if not fact:
            raise ValueError("حقيقة فارغة لا تُحفظ")
        for r in self._load("fact"):
            if (r.get("fact") or "").strip() == fact[:TEXT_CAP]:
                return {**r, "duplicate": True}
        return self._append("fact", {"fact": _cap(fact), "source": _cap(source, 300),
                                     "by": str(by)[:60], "topic": _cap(topic, 120)})

    def recall_facts(self, query: str, k: int = 5, min_score: float = 0.1) -> List[Dict[str, Any]]:
        scored = []
        for r in self._load("fact"):
            sc = similarity(query, (r.get("fact") or "") + " " + (r.get("topic") or ""))
            if sc >= min_score:
                scored.append((sc, r.get("ts") or 0, r))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [{"fact": r.get("fact"), "source": r.get("source"), "by": r.get("by"),
                 "score": round(sc, 3), "ts": r.get("ts")} for sc, _t, r in scored[:k]]

    # -------------------------------------------------------------- الحالة
    def verify_chain(self, kind: str = "experience") -> Dict[str, Any]:
        rows = self._load(kind)
        prev, broken = None, []
        for i, r in enumerate(rows):
            body = {k: v for k, v in r.items() if k != "hash"}
            h = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                          default=str).encode("utf-8")).hexdigest()[:24]
            if r.get("prev_hash") != prev or r.get("hash") != h:
                broken.append(i)
            prev = r.get("hash")
        return {"entries": len(rows), "broken": broken[:20], "intact": not broken}

    def stats(self) -> Dict[str, Any]:
        exp = self._load("experience")
        facts = self._load("fact")
        by_status: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        for r in exp:
            by_status[r.get("status") or "?"] = by_status.get(r.get("status") or "?", 0) + 1
            src = (r.get("source") or "?").split(":")[0]
            by_source[src] = by_source.get(src, 0) + 1
        return {"root": str(self.root), "experiences": len(exp), "facts": len(facts),
                "by_status": by_status, "by_source": by_source,
                "corrupt_lines": {k: v for k, v in self._corrupt.items() if v},
                "chain": self.verify_chain("experience"),
                "last": (exp[-1].get("goal") if exp else None)}


_STORE: Optional[ExperienceStore] = None
_STORE_ROOT: Optional[str] = None


def get_store() -> ExperienceStore:
    global _STORE, _STORE_ROOT
    root = default_root()
    if _STORE is None or _STORE_ROOT != root:
        _STORE, _STORE_ROOT = ExperienceStore(root), root
    return _STORE


def record_run(source: str, goal: str, res: Dict[str, Any], **extra) -> Optional[Dict[str, Any]]:
    """تسجيل نتيجة AgentLoop — فشل التسجيل لا يكسر التشغيل لكنه يُعاد للمستدعي صادقًا."""
    steps = res.get("steps") or []
    try:
        return get_store().record(source=source, goal=goal, status=res.get("status") or "?",
                                  tools=[s.get("tool") for s in steps],
                                  duration_s=res.get("duration_s"), error=res.get("error"),
                                  answer=res.get("answer"), steps=steps, meta=extra or None)
    except Exception as exc:  # TOLERATED: الخبرة إضافة؛ فشلها يُعلن في النتيجة لا يُخفى
        res["experience_warning"] = f"تعذر تسجيل الخبرة: {type(exc).__name__}"
        return None


def lessons_text(goal: str, k: int = 3) -> str:
    """التجارب السابقة المشابهة كأسطر وقائع — تُحقن في تعليمات العقل."""
    try:
        items = get_store().recall(goal, k=k)
    except Exception:  # TOLERATED: بلا خبرة يعمل العقل كما كان
        return ""
    lines = []
    for it in items:
        tools = "، ".join(it.get("tools") or []) or "بلا أدوات"
        line = f"- «{_cap(it.get('goal'), 120)}» ⇒ الأدوات: {tools} ⇒ {it.get('status')}"
        if it.get("error"):
            line += f" (الخطأ: {_cap(it.get('error'), 120)})"
        lines.append(line)
    return "\n".join(lines)
