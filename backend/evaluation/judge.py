# -*- coding: utf-8 -*-
"""R-843: الحَكَم المستقل — التطبيق يحكم أولًا، والعقل حَكَم ثانٍ من عائلة أخرى.

مبادئ (D-058):
1. **الحتمي أولًا**: كل معيار قابل للفحص آليًا (equals/contains/not_contains/
   regex/max_len) يحسمه التطبيق نفسه — لا يُسأل عنه عقل.
2. **الدلالي فقط للحكم**: معيار `semantic` (هل الجواب يلخص الأدلة بصدق؟)
   يُرسل إلى حَكَم لغوي **من عائلة نماذج غير عائلة المنفّذ** (qwen ≠ llama ≠
   gemma …). نفس العائلة ⇒ `not_independent` ⇒ لا نجاح أبدًا (لا تقييم ذاتي).
3. **حجب**: الحَكَم يرى المهمة والمخرج والأدلة الخام فقط — لا اسم المنفّذ ولا
   تبريره ولا توقع المؤلف.
4. **عقد صارم**: مخطط JSON بـenum لمعرّفات المعايير؛ كل معيار مرة واحدة بالضبط؛
   أي انحراف ⇒ `invalid_reply` ⇒ ليس نجاحًا. غياب الحَكَم ⇒ `unavailable`.
5. الحَكَم لا ينفّذ شيئًا ولا يرى سرًا؛ نتيجته تُسجل بنموذجه وزمنه.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

JudgeFn = Callable[[str, str, Dict[str, Any], float, str], Optional[str]]

DETERMINISTIC = ("equals", "contains", "not_contains", "regex", "max_len",
                 # R-850: معايير بنيوية لمخرجات حية متغيرة (لا مساواة حرفية)
                 "has_keys", "non_empty", "is_type")
_PATH_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}(\.[A-Za-z0-9_\-]{1,64}){0,11}$")
_TYPES = {"str": (str,), "int": (int,), "number": (int, float), "bool": (bool,),
          "list": (list,), "dict": (dict,)}
_MISSING = object()
SEMANTIC = "semantic"
JUDGE_TIMEOUT = float(os.environ.get("EVAL_JUDGE_TIMEOUT", "60") or 60)
_EVIDENCE_CAP = 4000

_SYSTEM = (
    "أنت حَكَم تقييم مستقل وصارم. لكل معيار قرر: هل المخرج يحققه بالاستناد إلى "
    "الأدلة المعطاة فقط؟ لا تفترض ما ليس في الأدلة. أي رقم أو ادعاء في المخرج "
    "غير موجود في الأدلة = فشل. أجب بكائن JSON فقط: "
    "{\"verdicts\": [{\"id\": \"...\", \"pass\": true|false, \"reason\": \"...\"}]}.")


class CriterionError(ValueError):
    pass


def model_family(model: Optional[str]) -> str:
    """عائلة النموذج: البادئة الحرفية قبل أي رقم/وسم — qwen2.5:3b ⇒ qwen."""
    name = (model or "").strip().lower().split("/")[-1]
    m = re.match(r"[a-z]+", name)
    return m.group(0) if m else ""


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(
        value, ensure_ascii=False, sort_keys=True, default=str)


def validate_criteria(criteria: List[Dict[str, Any]]) -> None:
    ids = set()
    for c in criteria or []:
        if not isinstance(c, dict) or not re.fullmatch(r"[a-z0-9_]{1,40}", str(c.get("id", ""))):
            raise CriterionError(f"معرّف معيار غير صالح: {c!r}")
        if c["id"] in ids:
            raise CriterionError(f"معرّف معيار مكرر: {c['id']}")
        ids.add(c["id"])
        kind = c.get("type")
        if kind not in DETERMINISTIC + (SEMANTIC,):
            raise CriterionError(f"نوع معيار غير معروف: {kind}")
        if kind == "regex":
            try:
                re.compile(str(c.get("value", "")))
            except re.error as exc:
                raise CriterionError(f"تعبير غير صالح في {c['id']}: {exc}") from exc
        if "path" in c and (kind == SEMANTIC or not _PATH_RE.match(str(c["path"]))):
            raise CriterionError(f"مسار غير صالح في {c['id']}: {c.get('path')!r}")
        if kind == "has_keys" and not (isinstance(c.get("value"), list) and c["value"]
                                       and all(isinstance(k, str) and k for k in c["value"])):
            raise CriterionError(f"has_keys يحتاج قائمة مفاتيح نصية: {c['id']}")
        if kind == "is_type" and c.get("value") not in tuple(_TYPES) + ("null",):
            raise CriterionError(f"نوع غير معروف في {c['id']}: {c.get('value')!r}")
        if kind == SEMANTIC and len(str(c.get("text", ""))) < 8:
            raise CriterionError(f"معيار دلالي بلا نص واضح: {c['id']}")


def value_at(output: Any, path: Optional[str]) -> Any:
    """R-850: قيمة بمسار نقطي (مفاتيح كائنات/فهارس قوائم) — الغياب علامة لا استثناء."""
    if not path:
        return output
    val = output
    for part in str(path).split("."):
        if isinstance(val, dict) and part in val:
            val = val[part]
        elif isinstance(val, list) and part.isdigit() and int(part) < len(val):
            val = val[int(part)]
        else:
            return _MISSING
    return val


def check_deterministic(c: Dict[str, Any], output: Any) -> Dict[str, Any]:
    kind, val = c["type"], c.get("value")
    target = value_at(output, c.get("path"))
    row: Dict[str, Any] = {"id": c["id"], "type": kind, "by": "app"}
    if c.get("path"):
        row["path"] = c["path"]
    if target is _MISSING:                     # مسار غائب ⇒ فشل صريح لا افتراض
        return {**row, "pass": False, "reason": "missing_path"}
    output = target
    text = _as_text(output)
    if kind == "has_keys":
        ok = isinstance(output, dict) and all(k in output for k in val)
    elif kind == "non_empty":
        ok = output not in (None, "", [], {})
    elif kind == "is_type":
        ok = (output is None if val == "null" else
              isinstance(output, _TYPES[val])
              and not (val in ("int", "number") and isinstance(output, bool)))
    elif kind == "equals":
        ok = output == val
    elif kind == "contains":
        ok = str(val) in text
    elif kind == "not_contains":
        ok = str(val) not in text
    elif kind == "regex":
        ok = re.search(str(val), text) is not None
    else:  # max_len
        ok = len(text) <= int(val)
    return {**row, "pass": bool(ok)}


def default_judge_fn(system: str, user: str, schema: Dict[str, Any],
                     timeout: float, model: str) -> Optional[str]:
    try:
        try:
            import ollama_client  # type: ignore
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from backend import ollama_client  # type: ignore
        return ollama_client.chat(system, user, timeout=timeout, json_schema=schema,
                                  json_mode=True, max_tokens=400, model=model)
    except Exception:  # TOLERATED: الحَكَم غائب ⇒ unavailable صريح لا نجاح
        return None


def _executor_model() -> str:
    try:
        try:
            import config  # type: ignore
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from backend import config  # type: ignore
        return str(config.brain_get("OLLAMA_MODEL", "") or "")
    except Exception:  # TOLERATED: بلا إعداد ⇒ نموذج منفّذ مجهول ⇒ لا استقلال مثبت
        return ""


class IndependentJudge:
    def __init__(self, judge_fn: Optional[JudgeFn] = None,
                 judge_model: Optional[str] = None,
                 executor_model: Optional[str] = None,
                 timeout: float = JUDGE_TIMEOUT):
        self.judge_fn = judge_fn or default_judge_fn
        self.judge_model = (judge_model if judge_model is not None
                            else os.environ.get("EVAL_JUDGE_MODEL", "")).strip()
        self.executor_model = (executor_model if executor_model is not None
                               else _executor_model()).strip()
        self.timeout = timeout
        self.last_prompt: Optional[str] = None

    def independence(self) -> Tuple[bool, str]:
        if not self.judge_model:
            return False, "لا حَكَم مُعد (EVAL_JUDGE_MODEL فارغ)"
        if not self.executor_model:
            return False, "نموذج المنفّذ مجهول — الاستقلال غير قابل للإثبات"
        fj, fe = model_family(self.judge_model), model_family(self.executor_model)
        if not fj or fj == fe:
            return False, f"الحَكَم من عائلة المنفّذ نفسها ({fj or '?'}) — تقييم ذاتي مرفوض"
        return True, f"حَكَم {fj} ≠ منفّذ {fe}"

    def public(self) -> Dict[str, Any]:
        ok, why = self.independence()
        return {"judge_model": self.judge_model or None,
                "judge_family": model_family(self.judge_model) or None,
                "executor_family": model_family(self.executor_model) or None,
                "independent": ok, "reason": why}

    def evaluate(self, task: str, output: Any, evidence: Any,
                 criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
        """حكم كامل: الحتمي من التطبيق + الدلالي من الحَكَم المستقل."""
        validate_criteria(criteria)
        det = [check_deterministic(c, output) for c in criteria if c["type"] != SEMANTIC]
        sem = [c for c in criteria if c["type"] == SEMANTIC]
        out: Dict[str, Any] = {"criteria": det, "judge": None}
        if not sem:
            out["status"] = "judged"
            out["pass"] = all(d["pass"] for d in det)
            return out
        j = self._judge_semantic(task, output, evidence, sem)
        out["judge"] = {k: v for k, v in j.items() if k != "verdicts"}
        out["criteria"] = det + j.get("verdicts", [])
        out["status"] = j["status"]
        # لا نجاح إلا بحكم مستقل صالح + كل المعايير ناجحة
        out["pass"] = (j["status"] == "judged"
                       and all(c["pass"] for c in out["criteria"]))
        return out

    def _judge_semantic(self, task, output, evidence, sem) -> Dict[str, Any]:
        ok, why = self.independence()
        base = {"model": self.judge_model or None, "reason": why}
        if not ok:
            return {**base, "status": "not_independent"}
        ids = [c["id"] for c in sem]
        schema = {"type": "object", "required": ["verdicts"], "properties": {
            "verdicts": {"type": "array", "minItems": len(ids), "maxItems": len(ids),
                         "items": {"type": "object", "required": ["id", "pass", "reason"],
                                   "properties": {"id": {"type": "string", "enum": ids},
                                                  "pass": {"type": "boolean"},
                                                  "reason": {"type": "string"}}}}}}
        user = json.dumps({
            "task": str(task)[:1000],
            "output": _as_text(output)[:2000],
            "evidence": _as_text(evidence)[:_EVIDENCE_CAP],
            "criteria": [{"id": c["id"], "text": c["text"]} for c in sem],
        }, ensure_ascii=False)
        self.last_prompt = _SYSTEM + "\n" + user
        t0 = time.monotonic()
        try:
            raw = self.judge_fn(_SYSTEM, user, schema, self.timeout, self.judge_model)
        except Exception as exc:  # TOLERATED: فشل الحَكَم ⇒ unavailable صريح
            return {**base, "status": "unavailable", "error": type(exc).__name__}
        base["latency_s"] = round(time.monotonic() - t0, 3)
        if not raw:
            return {**base, "status": "unavailable"}
        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
            verdicts = obj["verdicts"]
            got = [v["id"] for v in verdicts]
            if sorted(got) != sorted(ids) or any(
                    not isinstance(v.get("pass"), bool) for v in verdicts):
                raise ValueError("معايير ناقصة/مكررة أو قيمة غير منطقية")
        except (ValueError, KeyError, TypeError) as exc:
            return {**base, "status": "invalid_reply", "error": str(exc)[:200]}
        return {**base, "status": "judged", "verdicts": [
            {"id": v["id"], "type": SEMANTIC, "pass": v["pass"],
             "reason": str(v.get("reason", ""))[:300], "by": "judge"} for v in verdicts]}
