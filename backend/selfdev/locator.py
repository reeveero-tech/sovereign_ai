"""R-798: محدد المواضع — إشارة ⇒ ملفات وأسطر حقيقية في الشيفرة.

الترتيب (من الأدق إلى الأعم):
1. أداة مذكورة في الإشارة ⇒ ملف وسطر معالجها الفعلي (inspect على ToolSpec.handler).
2. ملفات صريحة في الإشارة (files_hint) إن وُجدت.
3. معرّفات من المفتاح والعنوان والدليل ⇒ بحث في فهرس الشيفرة (أكثر الملفات ورودًا +
   أول سطر ورود).

كل موضع يحمل editable (مسموح للمحرك تعديله أم محمي) — المحمي يُعرض للعقل للفهم فقط.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import self_develop as sd

STOP = {"self", "None", "True", "False", "error", "errors", "status", "result", "calls",
        "success_rate", "last_error", "tool", "tools", "runs", "proposals", "defect",
        "selfmon", "open", "high", "medium", "low", "investigation", "code_fix", "evidence",
        "return", "import", "from", "with", "this", "that", "http", "https"}
MAX_LOCATIONS = 6
SNIPPET_RADIUS = 15


def identifiers(text: str) -> List[str]:
    out, seen = [], set()
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_.]{3,}", text or ""):
        for part in [tok] + tok.split("."):
            if len(part) < 4 or part in STOP or part.lower() in STOP or part in seen:
                continue
            seen.add(part)
            out.append(part)
    return out[:30]


class Locator:
    def __init__(self, repo_root: Path = sd.REPO_ROOT,
                 registry_fn: Optional[Callable[[], Any]] = None,
                 engine: Optional[sd.SelfDevEngine] = None) -> None:
        self.repo_root = Path(repo_root)
        self._registry_fn = registry_fn
        self._engine = engine or sd.SelfDevEngine(repo_root=self.repo_root, brain=None, disk=False)
        self._index: Optional[List[str]] = None

    def _rel(self, path: str) -> Optional[str]:
        try:
            return Path(path).resolve().relative_to(self.repo_root.resolve()).as_posix()
        except ValueError:
            return None

    def tool_location(self, name: str) -> Optional[Dict[str, Any]]:
        if self._registry_fn is None:
            return None
        try:
            spec = getattr(self._registry_fn(), "_tools", {}).get(name)
            if spec is None:
                return None
            fn = inspect.unwrap(spec.handler)
            src = inspect.getsourcefile(fn)
            line = inspect.getsourcelines(fn)[1]
        except (TypeError, OSError):  # TOLERATED: معالج بلا مصدر (مدمج) — لا موضع
            return None
        rel = self._rel(src) if src else None
        if not rel:
            return None
        return {"file": rel, "line": line, "why": f"معالج الأداة {name}",
                "editable": sd.is_allowed(rel)}

    def index(self) -> List[str]:
        if self._index is None:
            files = []
            base = self.repo_root / "backend"
            if base.is_dir():
                for f in base.rglob("*.py"):
                    rel = f.relative_to(self.repo_root).as_posix()
                    if "__pycache__" in rel or "/tests/" in rel:
                        continue
                    files.append(rel)
            self._index = sorted(files)
        return self._index

    def _read(self, rel: str) -> Optional[str]:
        try:
            return (self.repo_root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):  # TOLERATED: ملف غير مقروء يُتجاوز
            return None

    def locate(self, signal: Dict[str, Any]) -> List[Dict[str, Any]]:
        locs: List[Dict[str, Any]] = []
        seen = set()

        def add(loc):
            if loc and loc["file"] not in seen and len(locs) < MAX_LOCATIONS:
                seen.add(loc["file"])
                locs.append(loc)

        for t in signal.get("tools") or []:
            add(self.tool_location(t))
        for f in signal.get("files_hint") or []:
            if (self.repo_root / f).is_file():
                add({"file": f, "line": 1, "why": "ملف مذكور في الإشارة",
                     "editable": sd.is_allowed(f)})
        ids = identifiers(" ".join([signal.get("key", ""), signal.get("title", ""),
                                    signal.get("evidence", "")]))
        if ids:
            scored = []
            for rel in self.index():
                text = self._read(rel)
                if not text:
                    continue
                hits = [(i, text.count(i)) for i in ids if i in text]
                if not hits:
                    continue
                score = sum(min(c, 5) for _, c in hits) + 3 * len(hits)
                first = hits[0][0]
                line = text[:text.index(first)].count("\n") + 1
                scored.append((score, rel, line, [h for h, _ in hits][:4]))
            scored.sort(key=lambda x: (-x[0], x[1]))
            for score, rel, line, words in scored:
                add({"file": rel, "line": line, "why": f"ورود {words}",
                     "editable": sd.is_allowed(rel)})
        # R-803: مصدر الإنذار ليس هدف إصلاح — دليل حي: إشارة selfmon:goal_stuck وُجّهت كود_إصلاح
        # إلى backend/self_monitor.py نفسه (خطة العقل: تعديل شرط الكشف)، أي إسكات الإنذار بدل سببه.
        for loc in locs:
            if loc.get("editable") and self.is_detector(loc["file"], signal):
                loc["editable"] = False
                loc["detector"] = True
                loc["why"] += " — مصدر الإنذار نفسه: تعديله يُسكت الإنذار ولا يصلح السبب"
        return locs

    @staticmethod
    def alarm_literal(key: str) -> str:
        """الجزء الثابت من مفتاح الإشارة كما يُكتب في الكاشف: «selfmon:goal_stuck:G-1» ⇒ «selfmon:goal_stuck:»."""
        key = str(key or "")
        return key.rsplit(":", 1)[0] + ":" if ":" in key else key

    def is_detector(self, rel: str, signal: Dict[str, Any]) -> bool:
        """الملف يُصدر مفتاح هذه الإشارة حرفيًا — إلا إن كان الدليل عطلًا في الملف نفسه (Traceback فيه)."""
        lit = self.alarm_literal(signal.get("key", ""))
        if len(lit) < 6:
            return False
        text = self._read(rel) or ""
        if not any(q + lit in text for q in ('"', "'")):
            return False
        ev = str(signal.get("evidence") or "")
        return not ("Traceback" in ev and Path(rel).name in ev)

    def snippet(self, loc: Dict[str, Any], radius: int = SNIPPET_RADIUS) -> str:
        text = self._read(loc["file"]) or ""
        lines = text.splitlines()
        i = max(0, int(loc.get("line") or 1) - 1)
        lo, hi = max(0, i - radius), min(len(lines), i + radius)
        return "\n".join(f"{n + 1}: {lines[n]}" for n in range(lo, hi))
