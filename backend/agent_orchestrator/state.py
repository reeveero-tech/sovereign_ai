# -*- coding: utf-8 -*-
"""R-841 (4.14): الحالة والاستمرارية — checkpoint عند كل خطوة.

قابلة للاستئناف بعد انقطاع، قابلة للإلغاء، قابلة للتفتيش للتدقيق.
الكتابة ذرّية (مؤقت ثم استبدال) — لا حالة مكسورة في منتصف خطوة.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

from backend.runtime.atomic_json import atomic_write_json  # R-781: كتابة ذرية موحدة


class StateStore:
    """مخزن حالة الحلقات على القرص — كتابة ذرّية لكل checkpoint."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.loops_dir = os.path.join(base_dir, "loops")
        os.makedirs(self.loops_dir, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, loop_id: str) -> str:
        if not loop_id or "/" in loop_id or ".." in loop_id:
            raise ValueError(f"معرّف حلقة غير صالح: {loop_id!r}")
        return os.path.join(self.loops_dir, f"{loop_id}.json")

    def save(self, state: Dict[str, Any]) -> None:
        """checkpoint — يُستدعى بعد كل خطوة وقبل الانتظار. كتابة ذرية عبر R-781."""
        state["updated_at"] = time.time()
        with self._lock:
            atomic_write_json(self._path(state["loop_id"]), state,
                             ensure_ascii=False, indent=1)

    def load(self, loop_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(loop_id)
        with self._lock:
            if not os.path.exists(path):
                return None
            with open(path, encoding="utf-8") as f:
                return json.load(f)

    def delete(self, loop_id: str) -> None:
        path = self._path(loop_id)
        with self._lock:
            if os.path.exists(path):
                os.remove(path)

    def list(self) -> List[Dict[str, Any]]:
        out = []
        with self._lock:
            for name in sorted(os.listdir(self.loops_dir)):
                if not name.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(self.loops_dir, name),
                              encoding="utf-8") as f:
                        out.append(json.load(f))
                except (OSError, ValueError):  # TOLERATED: ملف checkpoint تالف — تخطيه في القائمة خير من تعطيل الاستئناف (الكتابة الحيوية ذرية عبر R-781)
                    continue
        return [{"loop_id": s.get("loop_id"), "status": s.get("status"),
                 "goal": (s.get("request") or {}).get("utterance", "")[:80],
                 "updated_at": s.get("updated_at")}
                for s in out]
