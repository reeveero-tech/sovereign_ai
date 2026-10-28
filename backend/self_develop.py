"""R-796 (بأمر المالك 2026-10-28 «أحيِ التطوير الذاتي واربطه بالنظام وحدة واحدة»):
محرك التطوير الذاتي — من «اقتراح نصي» إلى «تعديل كود حقيقي باختبار أحمر ثم أخضر».

الدورة الكاملة (كل مرحلة تترك أثرًا إلحاقيًا في disk_log — namespace «selfdev»):

  مصادر المهام ─┬─ اقتراحات ٤.٥ (kind=code_fix أو قرار المالك approved)
                ├─ طلب المالك (أداة selfdev.request — ومنها المحادثة)
                └─ أهداف الاستقلال التي أعلن العقل أنها «blocked»
        ↓
  pending → صياغة بالعقل على مرحلتين (اختيار ملف من فهرس حقيقي، ثم نافذة الشيفرة
  الحرفية → {summary, search, replace, test_name, test_code})
        ↓  تحقق بنيوي صارم (validate_draft) — مسودة لا تجتاز = محاولة فاشلة بسببها
  drafted → (GitHub Actions: tools/selfdev_ci.py) فرع work/selfdev-* من main:
            الاختبار يجب أن يفشل على الكود الأصلي (RED) ثم ينجح بعد التعديل (GREEN)،
            + بوابة الحذف + بوابة الوثائق + المجموعة الكاملة → دفع الفرع وتشغيل CI
        ↓
  awaiting_promotion (أخضر على فرع) → promoted (البصمة صارت في main بقرار المالك)
  tested_red / invalid → إعادة صياغة مع سبب الفشل الحرفي (حتى MAX_ATTEMPTS) → exhausted

الحدود (الدستور):
- الإنتاج لا يكتب أي ملف ولا يشغّل أي شيفرة (D-041 قائم): المحرك يقرأ ويصوغ فقط؛
  التطبيق والاختبار في بيئة CI معزولة، والترقية إلى main قرار المالك (المادة ٦).
- مسارات محمية لا يقترب منها المحرك أبدًا: الأمان والمفاتيح والبوابات وسير العمل
  والبيانات والوثائق والأدلة والمحرك نفسه (PROTECTED).
- /selfdev/status بيانات وصفية فقط — لا شيفرة ولا سر (المادة ٩).
- لا إجابة مزروعة: كل حالة من حدث حقيقي (عقل/تحقق/CI)، وتعذر العقل يُعلن ولا يُخفى.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMESPACE = "selfdev"
CI_NAMESPACE = "selfdev_ci"
MAX_ATTEMPTS = 3
MAX_FILE_BYTES = 200_000
WINDOW_LINES = 60
MAX_CANDIDATES = 12

ALLOWED_PREFIXES = ("backend/", "frontend/")
ALLOWED_SUFFIXES = (".py", ".js", ".html", ".css")
PROTECTED = (
    "backend/safety.py",
    "backend/secrets_vault.py",
    "backend/self_develop.py",
    "backend/selfdev/",  # R-798: حزمة التطوير الذاتي لا تعدّل نفسها
    "backend/sovereign/keys/",
    "backend/sovereign/signing",
    "backend/tests/",
    "tools/",
    ".github/",
    "data/",
    "docs/",
    "forensics/",
    "tests/",
    "Dockerfile",
    "fly.toml",
    "scripts/",
)
# رموز خطرة لا يُسمح للمسودة بإدخالها إن لم تكن في الملف الأصلي أصلًا
FORBIDDEN_NEW_TOKENS = ("subprocess", "os.system", "eval(", "exec(", "shutil.rmtree",
                        "os.remove", "os.unlink", "__import__('os')", "pickle.loads")
FORBIDDEN_TEST_TOKENS = ("subprocess", "os.system", "shutil", "socket", "httpx",
                         "requests", "urllib", "eval(", "exec(", "os.remove", "os.unlink")

STATUSES = ("pending", "drafted", "invalid", "tested_red", "awaiting_promotion",
            "promoted", "exhausted", "stale")
ACTIVE = ("pending", "invalid", "tested_red", "stale")

LOCATE_SYSTEM = (
    "أنت مهندس برمجيات في مشروع sovereign_ai. مهمتك: تحديد الملف الوحيد الذي يجب "
    "تعديله لحل المهمة، من القائمة المعطاة حرفيًا فقط، وكلمات مفتاحية (أسماء دوال أو "
    "متغيرات أو نصوص) موجودة في ذلك الملف تدل على موضع التعديل. أجب JSON فقط."
)
DRAFT_SYSTEM = (
    "أنت مهندس برمجيات دقيق. ستُعطى مهمة ونافذة حرفية من ملف. أنتج تعديلًا صغيرًا واحدًا:\n"
    "- search: نص منسوخ حرفيًا من النافذة (أسطر كاملة، يظهر مرة واحدة فقط في الملف).\n"
    "- replace: النص البديل الكامل (يُفضَّل الإضافة على الحذف).\n"
    "- test_name: اسم دالة اختبار pytest يبدأ بـ test_.\n"
    "- test_code: ملف pytest كامل يستورد الوحدة «{module}» ويفشل على الكود الحالي "
    "وينجح بعد التعديل، ويحتوي assert. لا شبكة ولا ملفات ولا subprocess.\n"
    "- summary: سطر واحد يصف التعديل.\n"
    "لا تخترع أسماء غير موجودة في النافذة. أجب JSON فقط."
)
DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "search": {"type": "string"},
        "replace": {"type": "string"},
        "test_name": {"type": "string"},
        "test_code": {"type": "string"},
    },
    "required": ["summary", "search", "replace", "test_name", "test_code"],
}


def task_id(source: str, ref: str) -> str:
    return "SD-" + hashlib.sha256(f"{source}:{ref}".encode("utf-8")).hexdigest()[:8]


def is_protected(path: str) -> bool:
    p = path.replace("\\", "/").lstrip("./")
    return any(p == x or p.startswith(x) for x in PROTECTED)


def is_allowed(path: str) -> bool:
    p = path.replace("\\", "/").lstrip("./")
    if ".." in p.split("/") or p.startswith("/"):
        return False
    return p.startswith(ALLOWED_PREFIXES) and p.endswith(ALLOWED_SUFFIXES) and not is_protected(p)


def module_name(path: str) -> str:
    return Path(path).stem


def validate_draft(draft: Dict[str, Any], original: Optional[str]) -> List[str]:
    """أسباب الرفض (قائمة فارغة = مسودة صالحة). نقية وحتمية — يستعملها الإنتاج و CI معًا."""
    errors: List[str] = []
    path = str(draft.get("file") or "")
    if not is_allowed(path):
        errors.append(f"path_not_allowed:{path}")
    if original is None:
        errors.append("file_missing")
        return errors
    search = draft.get("search") or ""
    replace = draft.get("replace")
    if not isinstance(search, str) or not search.strip():
        errors.append("search_empty")
    elif original.count(search) != 1:
        errors.append(f"search_occurs_{original.count(search)}_times")
    if not isinstance(replace, str):
        errors.append("replace_missing")
    elif search and replace == search:
        errors.append("no_change")
    if errors:
        return errors
    result = original.replace(search, replace, 1)
    if path.endswith(".py"):
        try:
            ast.parse(result)
        except SyntaxError as exc:
            errors.append(f"result_syntax_error:line{exc.lineno}")
    for tok in FORBIDDEN_NEW_TOKENS:
        if tok in replace and tok not in original:
            errors.append(f"forbidden_token:{tok}")
    tname = str(draft.get("test_name") or "")
    if not re.fullmatch(r"test_[A-Za-z0-9_]{1,80}", tname):
        errors.append("test_name_invalid")
    code = draft.get("test_code") or ""
    if not isinstance(code, str) or not code.strip():
        errors.append("test_code_empty")
        return errors
    try:
        tree = ast.parse(code)
        funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        if tname and tname not in funcs:
            errors.append("test_name_not_defined")
    except SyntaxError as exc:
        errors.append(f"test_syntax_error:line{exc.lineno}")
    if "assert" not in code:
        errors.append("test_without_assert")
    if module_name(path) not in code:
        errors.append("test_does_not_reference_module")
    for tok in FORBIDDEN_TEST_TOKENS:
        if tok in code:
            errors.append(f"test_forbidden_token:{tok}")
    if len(code) > 20_000 or len(replace) > 20_000:
        errors.append("too_large")
    return errors


def removed_lines(search: str, replace: str) -> List[str]:
    """أسطر في الأصل لا تبقى في البديل — لتدقيق الحذف (المادة ٧)."""
    keep = replace.splitlines()
    return [ln for ln in search.splitlines() if ln not in keep]


def _tokens(text: str) -> List[str]:
    toks = re.findall(r"[A-Za-z_][A-Za-z0-9_.]{2,}|[\u0600-\u06FF]{3,}", text or "")
    seen, out = set(), []
    for t in toks:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out[:40]


class SelfDevEngine:
    def __init__(self, repo_root: Path = REPO_ROOT,
                 brain: Optional[Callable[[str, str, Dict[str, Any]], Optional[str]]] = None,
                 disk: Any = None) -> None:
        self.repo_root = Path(repo_root)
        self._brain = brain
        self._disk = disk
        self._lock = threading.Lock()
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._hydrated = False
        self._ci_since = 0
        self.ticks = 0
        self.last_tick: Optional[Dict[str, Any]] = None
        self.persist_errors = 0

    # ---------- الدوام ----------
    def _disk_client(self):
        if self._disk is not None:
            return self._disk or None
        try:
            from sovereign.cloud_disk import get_cloud_disk
            return get_cloud_disk()
        except Exception:  # TOLERATED: بلا قرص سحابي تعمل الذاكرة وتُعلن durable=false
            return None

    def _persist(self, task: Dict[str, Any]) -> None:
        disk = self._disk_client()
        if disk is None:
            return
        try:
            if not disk.append_log(NAMESPACE, {"kind": "task", "task": task}):
                self.persist_errors += 1
        except Exception as exc:  # TOLERATED: يُعد ويُعلن في الحالة، لا يكسر الدورة
            self.persist_errors += 1
            logger.warning("R-796: تعذر إلحاق مهمة تطوير ذاتي: %s", exc)

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
            for row in rows:
                since = max(since, int(row.get("id") or 0))
                t = (row.get("payload") or {}).get("task")
                if isinstance(t, dict) and t.get("id"):
                    self._tasks[t["id"]] = t
            if len(rows) < 1000:
                break

    def sync_ci(self) -> int:
        """نتائج CI الحقيقية (namespace selfdev_ci) → حالات المهام."""
        disk = self._disk_client()
        if disk is None:
            return 0
        applied = 0
        rows = disk.pull_log(CI_NAMESPACE, since_id=self._ci_since, limit=1000) or []
        for row in rows:
            self._ci_since = max(self._ci_since, int(row.get("id") or 0))
            r = row.get("payload") or {}
            if self.apply_ci_result(r, persist=False):
                applied += 1
        return applied

    def apply_ci_result(self, r: Dict[str, Any], persist: bool = True) -> bool:
        tid = r.get("task_id")
        with self._lock:
            t = self._tasks.get(tid)
            if t is None:
                return False
            res = r.get("result")
            now = float(r.get("at") or time.time())
            t["ci"] = {k: r.get(k) for k in ("result", "attempt", "branch", "sha", "reason",
                                             "red_rc", "green_rc", "ci_dispatched", "at",
                                             "deploy")}
            if res == "promote_skipped":
                # R-797: الترقية الآلية تخطت (قاطع دائرة/رفض الدفع) — الفرع الأخضر ينتظر كما هو
                new = "awaiting_promotion"
            elif res == "promoted":
                new = "promoted"
            elif res == "green":
                new = "awaiting_promotion"
            elif res == "stale":
                new = "stale"
            else:
                t["feedback"] = str(r.get("log_tail") or r.get("reason") or "")[-1500:]
                new = "exhausted" if t.get("attempts", 0) >= MAX_ATTEMPTS else "tested_red"
            self._set(t, new, now, by="ci", note=str(r.get("reason") or res)[:200])
            snap = json.loads(json.dumps(t))
        if persist:
            self._persist(snap)
        return True

    # ---------- إدخال المهام ----------
    def request(self, title: str, detail: str = "", source: str = "owner",
                ref: Optional[str] = None, now: Optional[float] = None,
                files_hint: Optional[List[str]] = None,
                exclude_files: Optional[List[str]] = None) -> Dict[str, Any]:
        title = str(title or "").strip()[:300]
        if not title:
            raise ValueError("عنوان المهمة مطلوب")
        now = time.time() if now is None else now
        tid = task_id(source, ref or title)
        with self._lock:
            existing = self._tasks.get(tid)
            if existing is not None:
                return self.public(existing)
            t = {"id": tid, "source": source, "ref": ref, "title": title,
                 "detail": str(detail or "")[:3000], "status": "pending", "attempts": 0,
                 "created_at": now, "updated_at": now, "draft": None, "errors": [],
                 "feedback": None, "ci": None, "brain_seconds": None,
                 "history": [{"to": "pending", "at": now, "by": source}],
                 # R-798: توجيه من النواة/محرك الأهداف المتعذرة — ملفات مرجحة ومستبعدة
                 "files_hint": [f for f in (files_hint or []) if is_allowed(f)][:5],
                 "exclude_files": [str(f) for f in (exclude_files or [])][:20]}
            self._tasks[tid] = t
            snap = json.loads(json.dumps(t))
        self._persist(snap)
        return self.public(snap)

    def ingest_proposals(self, proposals: List[Dict[str, Any]], now: Optional[float] = None) -> int:
        n = 0
        for p in proposals or []:
            st, kind = p.get("status"), p.get("kind")
            if st == "suppressed" or not p.get("defect_open", True):
                continue
            if st == "approved" or (kind == "code_fix" and st == "proposed"):
                tid = task_id("proposal", p.get("id") or "")
                if tid in self._tasks:
                    continue
                self.request(p.get("title") or p.get("defect_id") or "proposal",
                             detail=f"{p.get('recommendation', '')}\nالدليل: {p.get('evidence', '')}",
                             source="proposal", ref=p.get("id"), now=now)
                n += 1
        return n

    # ---------- الصياغة ----------
    def file_index(self) -> List[str]:
        out = []
        for prefix in ALLOWED_PREFIXES:
            base = self.repo_root / prefix
            if not base.is_dir():
                continue
            for f in base.rglob("*"):
                if not f.is_file() or f.suffix not in ALLOWED_SUFFIXES:
                    continue
                rel = f.relative_to(self.repo_root).as_posix()
                if "__pycache__" in rel or "node_modules" in rel or not is_allowed(rel):
                    continue
                try:
                    if f.stat().st_size > MAX_FILE_BYTES:
                        continue
                except OSError:  # TOLERATED: ملف اختفى أثناء الفهرسة — يُتجاوز من الفهرس فقط
                    continue
                out.append(rel)
        return sorted(out)

    def read(self, rel: str) -> Optional[str]:
        if not is_allowed(rel):
            return None
        f = self.repo_root / rel
        try:
            return f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def candidates(self, task: Dict[str, Any]) -> List[str]:
        toks = _tokens(task.get("title", "") + " " + task.get("detail", ""))
        scored = []
        for rel in self.file_index():
            text = self.read(rel) or ""
            low_path = rel.lower()
            score = 0
            for tok in toks:
                k = tok.lower()
                if k in low_path:
                    score += 5
                score += min(text.count(tok), 5)
            if score:
                scored.append((score, rel))
        scored.sort(key=lambda x: (-x[0], x[1]))
        ranked = [r for _, r in scored]
        # R-798: ملفات النواة المرجحة أولًا، والمجرَّبة سابقًا (محرك الأهداف المتعذرة) تُستبعد
        exclude = set(task.get("exclude_files") or [])
        hints = [f for f in (task.get("files_hint") or [])
                 if f not in exclude and self.read(f) is not None]
        ranked = hints + [r for r in ranked if r not in hints and r not in exclude]
        return ranked[:MAX_CANDIDATES]

    def _ask(self, system: str, user: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self._brain is None:
            return None
        raw = self._brain(system, user, schema)
        if not raw:
            return None
        try:
            m = re.search(r"\{.*\}", raw, re.S)
            return json.loads(m.group(0) if m else raw)
        except (ValueError, AttributeError):
            return None

    def draft(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """صياغة مسودة واحدة — يعيد {ok, draft|None, errors[]} (لا يغيّر الحالة)."""
        cands = self.candidates(task)
        if not cands:
            return {"ok": False, "draft": None, "errors": ["no_candidate_files"]}
        brief = f"المهمة: {task['title']}\n{task.get('detail', '')}"
        if task.get("feedback"):
            brief += f"\nفشل المحاولة السابقة (حرفيًا):\n{task['feedback'][-1500:]}"
        locate_schema = {"type": "object",
                         "properties": {"file": {"type": "string", "enum": cands},
                                        "keywords": {"type": "array", "items": {"type": "string"}}},
                         "required": ["file", "keywords"]}
        hints = [f for f in (task.get("files_hint") or []) if f in cands]
        if hints:
            # R-799: النواة اختارت الملف وتحقق منه عقل الاقتراح — لا نداء ثانٍ للعقل لإعادة
            # اختياره (دليل حي: فشلت هذه الخطوة بالذات)؛ المرساة من معرّفات المهمة الحقيقية.
            loc = {"file": hints[0], "keywords": [t for t in _tokens(brief) if "_" in t or "." in t]
                   + _tokens(brief)}
        else:
            loc = self._ask(LOCATE_SYSTEM, brief + "\nالملفات:\n" + "\n".join(cands), locate_schema)
        if not loc:
            return {"ok": False, "draft": None, "errors": ["brain_unavailable_or_invalid_json:locate"]}
        rel = str(loc.get("file") or "")
        if rel not in cands:
            return {"ok": False, "draft": None, "errors": [f"locate_outside_candidates:{rel}"]}
        original = self.read(rel)
        if original is None:
            return {"ok": False, "draft": None, "errors": ["file_missing"]}
        lines = original.splitlines(keepends=True)
        anchor = 0
        for kw in [str(k) for k in (loc.get("keywords") or []) if str(k).strip()]:
            hit = next((i for i, ln in enumerate(lines) if kw in ln), None)
            if hit is not None:
                anchor = hit
                break
        lo, hi = max(0, anchor - WINDOW_LINES // 2), min(len(lines), anchor + WINDOW_LINES)
        window = "".join(lines[lo:hi])
        mod = module_name(rel)
        d = self._ask(DRAFT_SYSTEM.format(module=mod),
                      f"{brief}\nالملف: {rel} (الوحدة {mod})\nالنافذة الحرفية (أسطر {lo + 1}-{hi}):\n"
                      f"<<<\n{window}\n>>>", DRAFT_SCHEMA)
        if not d:
            return {"ok": False, "draft": None, "errors": ["brain_unavailable_or_invalid_json:draft"]}
        draft = {"file": rel, "summary": str(d.get("summary") or "")[:300],
                 "search": d.get("search"), "replace": d.get("replace"),
                 "test_name": str(d.get("test_name") or ""), "test_code": d.get("test_code"),
                 "base_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest()}
        # R-802: مرساة حتمية — العقل ينسخ النافذة بإزاحة/فراغات/حرف مختلف (دليل حي: كل
        # المسودات search_occurs_0_times). تُصحَّح إلى نص الملف الحقيقي أو تُرفض كما كانت.
        from selfdev import anchor  # كسول: selfdev/__init__ يستورد هذه الوحدة
        fix = anchor.anchor(original, draft["search"] or "", draft["replace"]
                            if isinstance(draft["replace"], str) else "", window=(lo, hi))
        if fix and isinstance(draft["replace"], str):
            draft["search"], draft["replace"] = fix["search"], fix["replace"]
            draft["anchor"] = fix["method"]
        errors = validate_draft(draft, original)
        near = None
        if any(e.startswith("search_occurs_") for e in errors):
            near = anchor.nearest(original, draft.get("search") or "")
        if not errors:
            draft["removed_lines"] = len(removed_lines(draft["search"], draft["replace"]))
        return {"ok": not errors, "draft": draft if not errors else None, "errors": errors,
                "file": rel, "nearest": near}

    # ---------- الدورة ----------
    def _set(self, t: Dict[str, Any], status: str, now: float, by: str, note: str = "") -> None:
        t["status"] = status
        t["updated_at"] = now
        t.setdefault("history", []).append({"to": status, "at": now, "by": by, "note": note})
        t["history"] = t["history"][-20:]

    def next_task(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            act = [t for t in self._tasks.values()
                   if t["status"] in ACTIVE and t.get("attempts", 0) < MAX_ATTEMPTS]
            prio = {"owner": 0, "proposal": 1, "nucleus": 1, "unmet": 1, "goal": 2}
            act.sort(key=lambda t: (prio.get(t.get("source"), 3), t.get("created_at", 0)))
            return act[0] if act else None

    def revive_anchor_failures(self, now: float) -> int:
        """R-802: مهمة استُنفدت **فقط** بعدم مطابقة search (قبل المرساة) تُمنح جولة جديدة مرة واحدة.

        السبب المرفوض أُصلح في المحرك نفسه، فبقاؤها «exhausted» حكم على عيب أُزيل. لا تُحيا
        مهمة فشلت لسبب آخر، ولا تُحيا مرتين (العلَم revived_r802 يدوم مع المهمة)، ولا تُحيا مهمة
        استُنفدت بعد المرساة (anchored_era) — قاعدة R-796 «المستنفدة لا تُعاد» باقية لها.
        """
        snaps = []
        with self._lock:
            for t in self._tasks.values():
                errs = t.get("errors") or []
                if (t.get("status") == "exhausted" and errs and not t.get("revived_r802")
                        and not t.get("anchored_era")
                        and all(str(e).startswith("search_occurs_") for e in errs)):
                    t["revived_r802"] = True
                    t["attempts"] = 0
                    self._set(t, "pending", now, by="R-802",
                              note="إحياء: الرفض كان search_occurs قبل المرساة الحتمية")
                    snaps.append(json.loads(json.dumps(t)))
        for snap in snaps:
            self._persist(snap)
        return len(snaps)

    def tick(self, proposals: Optional[List[Dict[str, Any]]] = None,
             now: Optional[float] = None) -> Dict[str, Any]:
        now = time.time() if now is None else now
        self.hydrate()
        ci_applied = 0
        try:
            ci_applied = self.sync_ci()
        except Exception as exc:  # TOLERATED: تعذر القراءة يُعلن في نتيجة الدورة
            logger.warning("R-796: تعذر سحب نتائج CI: %s", exc)
        ingested = self.ingest_proposals(proposals or [], now=now)
        revived = self.revive_anchor_failures(now)
        self.ticks += 1
        t = self.next_task()
        out: Dict[str, Any] = {"tick": self.ticks, "ci_applied": ci_applied,
                               "ingested": ingested, "revived": revived, "task": None}
        if t is None:
            out["status"] = "idle"
        elif self._brain is None:
            out.update(status="brain_unavailable", task=t["id"])
        else:
            t0 = time.time()
            res = self.draft(t)
            secs = round(time.time() - t0, 1)
            with self._lock:
                t["attempts"] = t.get("attempts", 0) + 1
                t["anchored_era"] = True  # R-802: صيغت بالمرساة الحتمية
                t["brain_seconds"] = secs
                t["errors"] = res["errors"]
                if res["ok"]:
                    t["draft"] = res["draft"]
                    self._set(t, "drafted", now, by="brain", note=res["draft"]["summary"])
                else:
                    t["feedback"] = "مسودة مرفوضة بالتحقق: " + ", ".join(res["errors"])
                    if res.get("nearest"):
                        # R-802: النص الحقيقي الأقرب حرفيًا — المحاولة التالية تنسخه بدل التخمين
                        t["feedback"] += ("\nالنص الحقيقي الأقرب في " + str(res.get("file")) +
                                          " (انسخه حرفيًا في search):\n<<<\n" + res["nearest"][:1200] + "\n>>>")
                    new = "exhausted" if t["attempts"] >= MAX_ATTEMPTS else "invalid"
                    self._set(t, new, now, by="validator", note=", ".join(res["errors"])[:200])
                snap = json.loads(json.dumps(t))
            self._persist(snap)
            out.update(status=snap["status"], task=t["id"], errors=res["errors"],
                       brain_seconds=secs, file=res.get("file"))
        self.last_tick = {k: v for k, v in out.items()}
        self.last_tick["at"] = now
        return out

    def get(self, tid: str) -> Optional[Dict[str, Any]]:
        """R-798: مهمة واحدة (بيانات وصفية) — لمحرك الأهداف المتعذرة."""
        with self._lock:
            t = self._tasks.get(tid)
            return self.public(t) if t else None

    # ---------- العرض (بلا شيفرة) ----------
    @staticmethod
    def public(t: Dict[str, Any]) -> Dict[str, Any]:
        d = t.get("draft") or {}
        return {"id": t["id"], "source": t.get("source"), "ref": t.get("ref"),
                "title": t.get("title"), "status": t.get("status"),
                "attempts": t.get("attempts", 0), "created_at": t.get("created_at"),
                "updated_at": t.get("updated_at"), "file": d.get("file"),
                "summary": d.get("summary"), "removed_lines": d.get("removed_lines"),
                "anchor": d.get("anchor"),  # R-802: طريقة المرساة معلنة (exact/rstrip/indent/context/fuzzy)
                "errors": t.get("errors") or [], "ci": t.get("ci"),
                "brain_seconds": t.get("brain_seconds"),
                "files_hint": t.get("files_hint") or [],
                "exclude_files": t.get("exclude_files") or [],
                "history": [{k: h.get(k) for k in ("to", "at", "by")} for h in t.get("history", [])]}

    def status(self) -> Dict[str, Any]:
        self.hydrate()
        with self._lock:
            items = [self.public(t) for t in self._tasks.values()]
        items.sort(key=lambda x: x.get("updated_at") or 0, reverse=True)
        return {"engine": "R-796", "brain": self._brain is not None,
                "durable": self._disk_client() is not None,
                "persist_errors": self.persist_errors, "ticks": self.ticks,
                "last_tick": self.last_tick, "max_attempts": MAX_ATTEMPTS,
                "counts": {s: sum(1 for i in items if i["status"] == s) for s in STATUSES},
                "tasks": items[:50],
                "boundary": "الإنتاج يصوغ فقط ولا يكتب ملفًا؛ التطبيق والاختبار RED→GREEN في CI "
                            "على فرع work/selfdev-*؛ الترقية إلى main قرار المالك",
                "protected": list(PROTECTED)}


_ENGINE: Optional[SelfDevEngine] = None
_ENGINE_LOCK = threading.Lock()


def _default_brain():
    try:
        import config
        if not (config.OLLAMA_ENABLED and config.OLLAMA_MODEL):
            return None
    except Exception:  # TOLERATED: بلا إعداد = بلا عقل (يُعلن brain=false)
        return None
    import ollama_client

    def brain(system: str, user: str, schema: Dict[str, Any]) -> Optional[str]:
        return ollama_client.chat(system, user, json_schema=schema, max_tokens=1500)
    return brain


def get_engine() -> SelfDevEngine:
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = SelfDevEngine(brain=_default_brain())
        return _ENGINE


def reset_engine(engine: Optional[SelfDevEngine] = None) -> None:
    global _ENGINE
    with _ENGINE_LOCK:
        _ENGINE = engine


def interval_from_env() -> float:
    try:
        v = float(os.environ.get("SOVEREIGN_SELFDEV_INTERVAL", "1800"))
        return v if v >= 1 else 1800.0
    except ValueError:  # TOLERATED: قيمة غير رقمية → الافتراضي المعلن
        return 1800.0
