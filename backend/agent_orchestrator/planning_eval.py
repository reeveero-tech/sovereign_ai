# -*- coding: utf-8 -*-
"""R-842: تقييم جودة اختيار الأدوات (ROADMAP ٦.٢.٣) — رقم يُقاس لا يُدّعى.

مجموعتان:
  - dev (50 هدفًا) — مجموعة التطوير؛ ضُبط المرتِّب عليها، فهي حارس انحدار.
  - holdout (20 هدفًا) — ثُبّتت بصمتها قبل أول تشغيل للمرتِّب ولم يُضبط عليها؛
    هي الدليل الأصدق على التعميم. أي تعديل عليها يكسر اختبار البصمة عمدًا.

المقياس: تطابق تام لقائمة الأدوات المتوقعة بالترتيب (الامتناع = قائمة فارغة).
الأوضاع: keyword (خط أساس R-841) | semantic (المرتِّب) | brain (العقل الحي).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .planner import Planner
from .semantic_planner import keyword_select
from .tool_registry import ToolRegistry, seed_registry

EVAL_DIR = Path(__file__).resolve().parent / "eval"
SETS = {"dev": "planning_goals.json", "holdout": "planning_holdout.json"}
HOLDOUT_SHA256 = "7eaece466afcdde6ed7af4a42a8e9287f50000cb21ff1326edaa6e9f727020ec"
TARGET = 0.90


def set_path(name: str) -> Path:
    if name not in SETS:
        raise ValueError(f"مجموعة تقييم غير معروفة: {name!r} (المتاح: {list(SETS)})")
    return EVAL_DIR / SETS[name]


def file_sha256(name: str) -> str:
    return hashlib.sha256(set_path(name).read_bytes()).hexdigest()


def load_goals(name: str) -> List[Dict[str, Any]]:
    return json.loads(set_path(name).read_text(encoding="utf-8"))["goals"]


def _semantic(utterance: str) -> Dict[str, Any]:
    # التقييم يقيس الاختيار من النص وحده — لا كيانات محقونة تسهّل المهمة
    return {"utterance": utterance, "intent": {"label": "request"},
            "entities": [], "references": [], "ambiguities": [],
            "languages": ["ar"], "user_lang": "ar"}


def evaluate(set_name: str = "dev", mode: str = "semantic",
             tools: Optional[ToolRegistry] = None, brain_fn=None) -> Dict[str, Any]:
    if mode not in ("keyword", "semantic", "brain"):
        raise ValueError(f"وضع تقييم غير معروف: {mode!r}")
    goals = load_goals(set_name)
    reg = tools or seed_registry()
    planner = Planner(reg, brain_fn=brain_fn,
                      planner_mode="brain" if mode == "brain" else "semantic")
    rows = []
    by_cat: Dict[str, List[int]] = {}
    brain_outcomes: Dict[str, int] = {}
    t0 = time.time()
    for g in goals:
        sem = _semantic(g["utterance"])
        if mode == "keyword":
            sel = keyword_select(planner, sem)
        else:
            sel = planner.selector.select(sem)
        got = [t.tool_id for t in sel.tools]
        ok = got == list(g["expected_tools"])
        by_cat.setdefault(g["category"], []).append(int(ok))
        if mode == "brain":
            key = sel.brain_outcome.split(":")[0]
            brain_outcomes[key] = brain_outcomes.get(key, 0) + 1
        rows.append({"id": g["id"], "utterance": g["utterance"],
                     "expected": g["expected_tools"], "got": got, "ok": ok,
                     "planner": sel.planner,
                     "confidence": round(sel.confidence, 3)})
    n = len(rows)
    correct = sum(r["ok"] for r in rows)
    abstain = [r for r in rows if not r["expected"]]
    acted = [r for r in rows if r["got"]]
    return {
        "set": set_name, "mode": mode, "n": n, "correct": correct,
        "accuracy": round(correct / n, 4) if n else 0.0,
        "target": TARGET, "meets_target": (correct / n) >= TARGET if n else False,
        "by_category": {c: {"n": len(v), "accuracy": round(sum(v) / len(v), 4)}
                        for c, v in sorted(by_cat.items())},
        # امتناع صحيح عن خارج النطاق — لا أداة لطلب لا أداة له
        "abstain_accuracy": round(sum(r["ok"] for r in abstain) / len(abstain), 4)
        if abstain else None,
        # دقة الفعل: من الطلبات التي اختير لها أداة، كم كانت صحيحة
        "action_precision": round(sum(r["ok"] for r in acted) / len(acted), 4)
        if acted else None,
        "brain_outcomes": brain_outcomes or None,
        "file_sha256": file_sha256(set_name),
        "duration_s": round(time.time() - t0, 3),
        "failures": [r for r in rows if not r["ok"]],
    }
