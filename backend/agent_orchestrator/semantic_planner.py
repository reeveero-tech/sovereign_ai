# -*- coding: utf-8 -*-
"""R-842: اختيار الأدوات الدلالي — مُرتِّب حتمي + عقل لغوي عند الغموض.

لماذا: مخطط R-841 كان يختار بكلمات مفتاحية مكتوبة في الكود لكل أداة؛ أي أداة
جديدة أو صياغة غير متوقعة (لهجة، إنجليزية، مرادف) تسقط. هنا الاختيار يُستنتج من
عقد الأداة نفسه في السجل (الاسم + الوصف الدلالي + الأمثلة + أنماط الكيانات)،
فإضافة أداة = إضافة بيانات لا كود.

طبقتان:
  1) SemanticRanker — حتمي، بلا شبكة، بلا اعتماديات: تطبيع عربي + جذع خفيف +
     وزن ندرة (IDF) عبر الأدوات + تطابق تقريبي بثلاثيات الحروف + أنماط كيانات
     معلنة في العقد + نية الوصول (قراءة/كتابة) من معجم أفعال عام. يقسّم الطلب
     إلى جمل متتابعة («ثم»، «then»…) ويختار أفضل أداة لكل موصل في كل جملة.
     دون العتبة ⇒ امتناع ⇒ سؤال توضيحي (لا افتراض — المبدأ الحاكم).
  2) BrainPlanner — العقل اللغوي يُستشار عند الغموض فقط (أو دائمًا للتقييم)،
     مقيدًا بمخطط JSON بتعداد معرّفات الأدوات المرشحة. الحراسة:
       - معرّف خارج القائمة/السجل ⇒ رفض ⇒ المرتِّب (لا أداة مخترعة).
       - أداة بلا أي دليل نصي (درجة دون الأرضية) ⇒ رفض (لا هلوسة).
       - العقل لا يحدد المدخلات ولا الموافقة ولا الخطورة: تبقى من السجل
         والاستخراج الحتمي، والبوابات الثلاث كما هي.
       - عقل غير متاح/مهلة/JSON تالف ⇒ سقوط للمرتِّب بقرار مسجل، لا انهيار.
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .tool_registry import ToolDefinition, ToolRegistry

# ------------------------------------------------------------------ معاملات
THRESHOLD = 2.2          # أقل درجة لاعتبار أداة مقصودة في جملة
RELATIVE_FLOOR = 0.45    # أداة موصل آخر تُضم إن بلغت هذه النسبة من الأعلى
EVIDENCE_FLOOR = 0.6     # أقل دليل نصي يقبل به اختيار العقل
PATTERN_WEIGHT = 2.0     # نمط كيان معلن في العقد (رابط، معرّف خدمة…)
CONFIDENT = 0.75         # فوقها لا يُستشار العقل في الوضع الهجين
FUZZY_MIN = 0.6          # أقل تشابه ثلاثيات لقبول تطابق تقريبي

_AR_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")
_TOKEN = re.compile(r"[\w\u0600-\u06FF]+(?:[.\-][\w\u0600-\u06FF]+)*", re.UNICODE)
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# فواصل التتابع — تقسم الطلب إلى جمل مستقلة بالترتيب
_SEQ_SPLIT = re.compile(
    r"\s*[،,;؛]?\s*(?:\bثم\b|\bوبعدين\b|\bبعدين\b|\bوبعد\s+ذلك\b|\bبعد\s+ذلك\b|"
    r"\band\s+then\b|\bthen\b|\bafter\s+that\b|\bوبعدها\b|\bبعدها\b)\s*",
    re.IGNORECASE | re.UNICODE)

_STOP = {
    # عربي (بعد التطبيع)
    "في", "من", "على", "الى", "عن", "مع", "هل", "ما", "ماذا", "لي", "لنا", "عندنا",
    "هذا", "هذه", "او", "كل", "اي", "اللي", "يا", "هو", "هي", "ان", "كان", "لو",
    "قل", "لك", "به", "بها", "فيه", "الان", "حول", "إذا", "اذا", "كان", "منه",
    "ذلك", "تلك", "التي", "الذي", "الذين", "عند", "بعد", "قبل", "حقنا", "ايش",
    "وش", "شو", "ابي", "ابغى", "بغيت", "اريد", "من فضلك", "فضلك", "رجاء",
    # إنجليزي
    "the", "a", "an", "of", "in", "on", "for", "to", "me", "my", "our", "we",
    "is", "are", "this", "that", "and", "or", "please", "from", "with", "all",
    "any", "some", "do", "does", "have", "has", "what", "which", "there", "it",
    "its", "their", "be", "right", "now", "us", "you", "your", "i", "can",
    "could", "would", "about", "into", "as", "by", "at", "whats", "s",
}

# نية الوصول — معجم أفعال عام (لا يخص أداة بعينها)
VERB_WEIGHT = 0.35       # الفعل دليل على نوع الوصول لا على الأداة — وزن محتوى منخفض
DESC_WEIGHT = 0.7        # الوصف الطويل فيه كلمات عرضية؛ الأمثلة والاسم أوثق
EXCLUSIVE_MIN = 2.0      # موصل إضافي في الجملة نفسها يحتاج دليلًا اسميًا خاصًا به (لا أفعال)
_WRITE_VERBS = {
    "انشئ", "انشي", "سو", "سوي", "اضف", "ارفع", "اكتب", "ابلغ", "بلغ", "قدم",
    "سجل", "افتح", "create", "open", "add", "file", "raise", "report",
    "register", "submit", "write", "import", "استورد", "اربط", "ربط", "اسجل",
    "turn", "make", "post", "log",
}
_READ_VERBS = {
    "اعرض", "حلل", "اقرا", "وريني", "شوف", "اشوف", "طالع", "افحص", "تحقق",
    "راجع", "عطني", "اعطني", "show", "list", "read", "view", "check",
    "inspect", "analyze", "analyse", "summarize", "summarise", "fetch",
    "select", "give", "get", "display", "see", "استخرج", "ما", "هل", "كم",
    "which", "what", "is", "are", "وش", "ايش", "تفاصيل",
}


# ------------------------------------------------------------------ معالجة النص
def normalize(text: str) -> str:
    """تطبيع عربي/لاتيني: حذف التشكيل والتطويل، توحيد الألف والياء والتاء."""
    t = unicodedata.normalize("NFKC", text or "").translate(_AR_DIGITS).lower()
    t = _AR_DIACRITICS.sub("", t)
    t = re.sub("[إأآٱ]", "ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return t


_AR_PREFIXES = ("وال", "بال", "فال", "كال", "لل", "ال")
_AR_SUFFIXES = ("ات", "ها", "هم", "نا", "ين", "ون", "كم", "يه", "ه", "ي")
# معرّفات بنيوية (روابط، owner/repo) — أسماء لا كلمات دلالية: لا تُحسب محتوى
_ENTITY_SPAN = re.compile(r"(?:https?://)?[\w.-]+\.[a-z]{2,}/[\w./-]*|"
                          r"(?<![\w/.])[a-z0-9][\w.-]*/[\w.-]+(?![\w/])", re.I)


def _strip_suffix(s: str) -> str:
    for suf in _AR_SUFFIXES:
        if s.endswith(suf) and len(s) - len(suf) >= 3:
            return s[: -len(suf)]
    return s


def variants(tok: str) -> set:
    """أشكال المطابقة لرمز: المطبع + جذع خفيف (+ نزع حرف عطف/جر كبديل لا كبديل وحيد)."""
    out = {tok}
    if re.match(r"^[\u0600-\u06FF]", tok):
        base = tok
        for p in _AR_PREFIXES:
            if base.startswith(p) and len(base) - len(p) >= 3:
                base = base[len(p):]
                break
        out.add(base)
        out.add(_strip_suffix(base))
        if tok[:1] in ("و", "ف", "ب", "ل") and len(tok) >= 5:
            alt = tok[1:]
            for p in _AR_PREFIXES:
                if alt.startswith(p) and len(alt) - len(p) >= 3:
                    alt = alt[len(p):]
                    break
            out.add(alt)
            out.add(_strip_suffix(alt))
    else:
        for suf in ("ies", "ing", "es", "ed", "s"):
            if tok.endswith(suf) and len(tok) - len(suf) >= 3:
                out.add(tok[: -len(suf)] + ("y" if suf == "ies" else ""))
                break
    return {v for v in out if len(v) >= 2}


def stem(tok: str) -> str:
    """أقصر شكل مطابقة — للتوافق والتشابه التقريبي."""
    return min(variants(tok), key=len)


def tokenize(text: str, skip_entities: bool = True) -> List[Tuple[str, str, int]]:
    """(الشكل المطبع، الجذع، الموضع) لكل رمز غير متوقف؛ المعرّفات البنيوية تُستثنى."""
    norm = normalize(text)
    spans = [m.span() for m in _ENTITY_SPAN.finditer(norm)] if skip_entities else []
    out = []
    for m in _TOKEN.finditer(norm):
        if any(a <= m.start() < b for a, b in spans):
            continue
        tok = m.group(0)
        parts = [tok] + ([p for p in re.split(r"[.\-]", tok) if p] if re.search(r"[.\-]", tok) else [])
        for part in parts:
            if part in _STOP or len(part) < 2 or part.isdigit():
                continue
            out.append((part, stem(part), m.start()))
    return out


_STOP = {normalize(w) for w in _STOP}
_WRITE_VERBS = {normalize(w) for w in _WRITE_VERBS}
_READ_VERBS = {normalize(w) for w in _READ_VERBS}
_VERBS = _WRITE_VERBS | _READ_VERBS


def _trigrams(s: str) -> set:
    s = f" {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def access_intent(text: str) -> Dict[str, bool]:
    """هل في الطلب فعل كتابة/قراءة؟ — بالشكل المطبع (لا الجذع: «السجلات» ليست «سجّل»)."""
    forms = set()
    for m in _TOKEN.finditer(normalize(text)):
        tok = m.group(0)
        forms.add(tok)
        if tok[:1] in ("و", "ف") and len(tok) > 3:
            forms.add(tok[1:])
    return {"write": bool(forms & _WRITE_VERBS),
            "read": bool(forms & _READ_VERBS)}


def split_clauses(text: str) -> List[str]:
    parts = [p.strip(" ،,.;؛") for p in _SEQ_SPLIT.split(text or "")]
    return [p for p in parts if p]


# ------------------------------------------------------------------ النتيجة
@dataclass
class Selection:
    tools: List[ToolDefinition]
    scores: Dict[str, float]
    rejected: List[str]
    reason: str
    confidence: float
    planner: str                       # semantic | brain | semantic_fallback | keyword
    brain_outcome: str = "not_consulted"
    clauses: List[str] = field(default_factory=list)

    def public(self) -> Dict[str, Any]:
        return {
            "planner": self.planner,
            "chosen": [t.tool_id for t in self.tools],
            "scores": {k: round(v, 3) for k, v in self.scores.items()},
            "rejected": list(self.rejected),
            "confidence": round(self.confidence, 3),
            "brain_outcome": self.brain_outcome,
            "clauses": list(self.clauses),
            "reason": self.reason,
        }


# ------------------------------------------------------------------ المرتِّب
class SemanticRanker:
    """يقرأ عقود الأدوات من السجل ويبني ملفًا دلاليًا لكل أداة عند الطلب."""

    def __init__(self, tools: ToolRegistry):
        self.tools = tools
        self._cache_key: Optional[Tuple[str, ...]] = None
        self._profiles: Dict[str, Dict[str, float]] = {}
        self._tri: Dict[str, Dict[str, set]] = {}
        self._idf: Dict[str, float] = {}

    # ---- الملفات الدلالية (تُعاد عند تغير السجل — أداة جديدة تُرى فورًا)
    def _active(self) -> List[ToolDefinition]:
        out = []
        for pub in self.tools.list():
            if pub.get("lifecycle") == "deprecated":
                continue
            out.append(self.tools.get(pub["tool_id"]))
        return out

    def _ensure(self) -> List[ToolDefinition]:
        active = self._active()
        key = tuple(sorted(f"{d.tool_id}:{hash((d.description, json.dumps(d.examples, sort_keys=True, ensure_ascii=False), tuple(d.entity_patterns)))}"
                           for d in active))
        if key == self._cache_key:
            return active
        profiles: Dict[str, Dict[str, float]] = {}
        for d in active:
            terms: Dict[str, float] = {}
            texts = [(d.name, 1.0), (d.description, DESC_WEIGHT),
                     (d.tool_id.replace(".", " ").replace("_", " "), 1.0),
                     (d.connector_id.replace("_", " "), 1.0)]
            texts += [(str(ex.get("utterance", "")), 1.0) for ex in d.examples]
            for text, w in texts:
                for norm, _, _ in tokenize(text):
                    for v in variants(norm):
                        terms[v] = max(terms.get(v, 0.0), w)
            profiles[d.tool_id] = terms
        n = max(1, len(profiles))
        df: Dict[str, int] = {}
        for terms in profiles.values():
            for t in terms:
                df[t] = df.get(t, 0) + 1
        self._idf = {t: math.log(1 + n / c) for t, c in df.items()}
        self._profiles = profiles
        self._tri = {tid: {t: _trigrams(t) for t in terms if len(t) >= 4}
                     for tid, terms in profiles.items()}
        self._cache_key = key
        return active

    # ---- درجة أداة لجملة
    def _score(self, d: ToolDefinition, clause: str,
               toks: Sequence[Tuple[str, str, int]],
               intent: Dict[str, bool]) -> Tuple[float, int, Dict[str, float]]:
        """(الدرجة، موضع أول دليل اسمي، أوزان الأدلة) — الأدلة للتفسير وللدليل الخاص."""
        terms = self._profiles.get(d.tool_id, {})
        tri = self._tri.get(d.tool_id, {})
        used: set = set()
        evidence: Dict[str, float] = {}
        first = 10 ** 6
        for norm, st, pos in toks:
            is_verb = norm in _VERBS or (norm[:1] in ("و", "ف") and norm[1:] in _VERBS)
            vw = VERB_WEIGHT if is_verb else 1.0
            best, best_term = 0.0, None
            for v in variants(norm):
                if v in terms and v not in used:
                    w = self._idf.get(v, 0.0) * terms[v] * vw
                    if w > best:
                        best, best_term = w, v
            if best_term is None and len(st) >= 4 and not is_verb:
                qt = _trigrams(st)
                for t, tg in tri.items():
                    if t in used:
                        continue
                    j = _jaccard(qt, tg)
                    if j >= FUZZY_MIN:
                        w = self._idf.get(t, 0.0) * terms[t] * j * 0.7
                        if w > best:
                            best, best_term = w, t
            if best_term is not None and best > 0:
                used.add(best_term)
                evidence[norm] = evidence.get(norm, 0.0) + best
                if not is_verb:
                    first = min(first, pos)
        norm_clause = normalize(clause)
        for pat in getattr(d, "entity_patterns", None) or ():
            m = re.search(pat, norm_clause, re.IGNORECASE)
            if m:  # نمط واحد يكفي — لا عدّ مزدوج للكيان نفسه
                evidence[f"/{pat}/"] = PATTERN_WEIGHT
                first = min(first, m.start())
                break
        score = sum(evidence.values())
        if score > 0:
            if d.access in ("write", "admin"):
                score = score + 1.0 if intent["write"] else score * 0.6
            elif intent["write"] and not intent["read"]:
                score *= 0.8
        return score, first, evidence

    def rank(self, text: str) -> Dict[str, float]:
        """درجة كل أداة على الطلب كاملًا — للقائمة المختصرة والتفسير."""
        active = self._ensure()
        toks = tokenize(text)
        intent = access_intent(text)
        return {d.tool_id: self._score(d, text, toks, intent)[0] for d in active}

    def select(self, semantic: Dict[str, Any]) -> Selection:
        text = semantic.get("utterance") or ""
        active = self._ensure()
        clauses = split_clauses(text) or [text]
        chosen: List[ToolDefinition] = []
        scores: Dict[str, float] = {}
        rejected: List[str] = []
        confs: List[float] = []
        notes: List[str] = []
        for ci, clause in enumerate(clauses):
            toks = tokenize(clause)
            intent = access_intent(clause)
            scored = []
            for d in active:
                sc, first, ev = self._score(d, clause, toks, intent)
                if sc > 0:
                    scored.append((sc, first, d, ev))
                    scores[d.tool_id] = max(scores.get(d.tool_id, 0.0), sc)
            if not scored:
                notes.append(f"ج{ci + 1}: لا دليل")
                continue
            scored.sort(key=lambda x: (-x[0], x[1]))
            # أفضل أداة لكل موصل
            best_by_conn: Dict[str, Any] = {}
            for item in scored:
                c = item[2].connector_id
                if c not in best_by_conn:
                    best_by_conn[c] = item
                else:
                    rejected.append(f"{item[2].tool_id} (أضعف من "
                                    f"{best_by_conn[c][2].tool_id} في الموصل نفسه)")
            ranked = sorted(best_by_conn.values(), key=lambda x: (-x[0], x[1]))
            lead = ranked[0]
            picked = []
            if lead[0] >= THRESHOLD:
                picked.append(lead)
            else:
                rejected.append(f"{lead[2].tool_id} (درجة {lead[0]:.2f} دون العتبة)")
            for it in ranked[1:]:
                # موصل إضافي: درجة كافية + دليل خاص به لا يشاركه فيه الأعلى
                own = sum(w for k, w in it[3].items()
                          if k not in lead[3] and k not in _VERBS
                          and not (k[:1] in ("و", "ف") and k[1:] in _VERBS))
                if picked and it[0] >= THRESHOLD and own >= EXCLUSIVE_MIN:
                    picked.append(it)
                else:
                    rejected.append(f"{it[2].tool_id} (درجة {it[0]:.2f}، دليل خاص "
                                    f"{own:.2f})")
            picked.sort(key=lambda x: x[1])  # ترتيب الظهور في النص
            for sc, _, d, ev in picked:
                if d.tool_id in [c.tool_id for c in chosen]:
                    continue
                chosen.append(d)
                second = max([x[0] for x in scored if x[2] is not d] or [0.0])
                margin = (sc - second) / sc if sc else 0.0
                confs.append(max(0.0, min(1.0, 0.5 * min(1.0, sc / (2 * THRESHOLD))
                                          + 0.5 * margin)))
                notes.append(f"ج{ci + 1}: {d.tool_id}={sc:.2f} دليل={list(ev)[:5]}")
        conf = min(confs) if confs else 0.0
        if not chosen:
            rejected.append("no_tool_matched")
        return Selection(
            tools=chosen, scores=scores, rejected=rejected,
            reason="مرتِّب دلالي: " + ("؛ ".join(notes) or "لا دليل"),
            confidence=conf, planner="semantic", clauses=clauses)


# ------------------------------------------------------------------ العقل
BrainFn = Callable[[str, str, Dict[str, Any], float], Optional[str]]


def default_brain_fn(system: str, user: str, json_schema: Dict[str, Any],
                     timeout: float) -> Optional[str]:
    """العقل الحي عبر عميل المشروع (Ollama/OpenAI-compatible) — None إن تعذر."""
    try:
        try:
            import ollama_client  # type: ignore
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from backend import ollama_client  # type: ignore
        return ollama_client.chat(system, user, timeout=timeout,
                                  json_schema=json_schema, json_mode=True,
                                  max_tokens=200)
    except Exception:  # TOLERATED: العقل اختياري — المرتِّب الحتمي يكفي
        return None


_BRAIN_SYSTEM = (
    "أنت مخطط أدوات. اختر من القائمة فقط الأدوات اللازمة لتنفيذ طلب المستخدم، "
    "بترتيب التنفيذ. إن لم تكن أي أداة مناسبة فأجب [\"none\"]. لا تخترع أداة. "
    "أجب بكائن JSON فقط: {\"tools\": [...], \"reason\": \"...\"}.")


class BrainPlanner:
    """يستشير العقل مقيدًا بالقائمة المختصرة، ويحرس نتيجته قبل القبول."""

    def __init__(self, ranker: SemanticRanker,
                 brain_fn: Optional[BrainFn] = None,
                 mode: Optional[str] = None, timeout: Optional[float] = None):
        self.ranker = ranker
        self.brain_fn = brain_fn or default_brain_fn
        self.mode = (mode or os.environ.get("ORCH_PLANNER_MODE", "semantic")
                     ).strip().lower()
        self.timeout = float(timeout or os.environ.get(
            "ORCH_PLANNER_BRAIN_TIMEOUT", "30"))
        self.last_prompt: Optional[str] = None

    def _shortlist(self, text: str, k: int = 4) -> List[ToolDefinition]:
        ranked = sorted(self.ranker.rank(text).items(), key=lambda x: -x[1])
        out = [self.ranker.tools.get(t) for t, s in ranked[:k] if s > 0]
        return out or [self.ranker.tools.get(t) for t, _ in ranked[:k]]

    def _should_consult(self, sel: Selection) -> bool:
        if self.mode == "brain":
            return True
        if self.mode != "hybrid":
            return False
        if not sel.tools:
            return any(v > 0 for v in sel.scores.values())  # دليل ضعيف = غموض
        return sel.confidence < CONFIDENT

    def select(self, semantic: Dict[str, Any]) -> Selection:
        sel = self.ranker.select(semantic)
        if not self._should_consult(sel):
            return sel
        text = semantic.get("utterance") or ""
        shortlist = self._shortlist(text)
        ids = [d.tool_id for d in shortlist]
        schema = {
            "type": "object", "required": ["tools", "reason"],
            "properties": {
                "tools": {"type": "array", "maxItems": 4,
                          "items": {"type": "string", "enum": ids + ["none"]}},
                "reason": {"type": "string"}},
        }
        catalog = "\n".join(
            f"- {d.tool_id} [{d.access}]: {d.description}" for d in shortlist)
        # لا سياق غير الطلب والأوصاف العامة — لا أسرار ولا مدخلات سابقة
        user = f"الأدوات المتاحة:\n{catalog}\n\nطلب المستخدم: {text}"
        self.last_prompt = _BRAIN_SYSTEM + "\n" + user
        try:
            raw = self.brain_fn(_BRAIN_SYSTEM, user, schema, self.timeout)
        except Exception as exc:  # TOLERATED: فشل العقل يسقط للمرتِّب بقرار مسجل
            raw = None
            sel.brain_outcome = f"error:{type(exc).__name__}"
        if raw is None:
            if sel.brain_outcome == "not_consulted":
                sel.brain_outcome = "unavailable"
            sel.planner = "semantic_fallback"
            sel.reason += f"؛ العقل: {sel.brain_outcome} ⇒ المرتِّب"
            return sel
        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
            picks = obj["tools"]
            if not isinstance(picks, list) or not all(isinstance(p, str) for p in picks):
                raise ValueError("tools ليست قائمة نصوص")
        except (ValueError, KeyError, TypeError) as exc:
            sel.brain_outcome = f"invalid_json:{type(exc).__name__}"
            sel.planner = "semantic_fallback"
            sel.reason += f"؛ العقل أعاد خرجًا تالفًا ⇒ المرتِّب"
            return sel
        picks = [p for p in picks if p != "none"]
        bad = [p for p in picks if p not in ids]
        if bad:
            sel.brain_outcome = f"rejected_unknown_tool:{bad}"
            sel.planner = "semantic_fallback"
            sel.rejected.append(f"اختيار العقل {bad} خارج القائمة — رُفض")
            sel.reason += "؛ العقل اخترع أداة ⇒ رُفض ⇒ المرتِّب"
            return sel
        weak = [p for p in picks if sel.scores.get(p, 0.0) < EVIDENCE_FLOOR]
        if weak:
            sel.brain_outcome = f"rejected_no_evidence:{weak}"
            sel.planner = "semantic_fallback"
            sel.rejected.append(f"اختيار العقل {weak} بلا دليل نصي — رُفض")
            sel.reason += "؛ اختيار العقل بلا دليل ⇒ المرتِّب"
            return sel
        intent = access_intent(text)
        escalate = [p for p in picks
                    if self.ranker.tools.get(p).access != "read"
                    and not intent.get("write")]
        if escalate:  # طلب بلا فعل كتابة لا يصير كتابة باختيار العقل
            sel.brain_outcome = f"rejected_access_escalation:{escalate}"
            sel.planner = "semantic_fallback"
            sel.rejected.append(f"اختيار العقل {escalate} يصعّد إلى كتابة بلا طلب — رُفض")
            sel.reason += "؛ العقل صعّد الوصول ⇒ رُفض ⇒ المرتِّب"
            return sel
        reason = str(obj.get("reason", ""))[:300]
        prev = [t.tool_id for t in sel.tools]
        seen: List[str] = []
        for p in picks:
            if p not in seen:
                seen.append(p)
        tools = [self.ranker.tools.get(p) for p in seen]
        return Selection(
            tools=tools, scores=sel.scores,
            rejected=sel.rejected + [f"اقتراح المرتِّب {prev}" for _ in [0]
                                     if prev != seen],
            reason=f"العقل (مقيد بـ{ids}): {reason}؛ المرتِّب اقترح {prev}",
            confidence=max(sel.confidence, 0.8 if seen else 0.0),
            planner="brain", brain_outcome="accepted" if seen else "none",
            clauses=sel.clauses)


# ------------------------------------------------------------------ المرجع القديم
def keyword_select(planner_obj, semantic: Dict[str, Any]) -> Selection:
    """اختيار R-841 القديم — يُحفظ خط أساس للتقييم فقط."""
    sel = planner_obj._keyword_candidates(semantic, "")
    tools = sel["candidates"]
    return Selection(tools=tools, scores={}, rejected=sel["rejected"],
                     reason="كلمات مفتاحية (R-841)", confidence=1.0 if tools else 0.0,
                     planner="keyword")
