"""R-824: محلّل سياق المحادثة الحتمي — لا ينسى النظام ما قيل قبل قليل حتى بلا نموذج لغوي.

بأمر المالك (2026-10-31): «هناك هلوسة أو أن المشروع ينسى سياق المحادثة».

المشكلة الحية: الواجهة ترسل سجل المحادثة، لكن حين يتعذر العقل (Ollama) يمر الطلب بالجسر
الحتمي والبحث العالمي وكلاهما يرى الرسالة الحالية وحدها: «ما عاصمة اليابان؟» ثم «وكم عدد
سكانها؟» ⇒ يُبحث عن «كم عدد سكانها» بلا كيان فيأتي جواب عن شيء آخر (هلوسة ظاهرية).

الحل: resolve(text, history) يعيد سؤالًا قائمًا بذاته (standalone) بقواعد صريحة قابلة للاختبار:
- ضمير متصل بخاصية («سكانها/مساحتها/عاصمتها»، its/their) ⇒ يُستبدل بالكيان السابق.
- حذف/عطف («وماذا عن فرنسا؟»، what about France) ⇒ نفس السؤال السابق بكيان جديد.
- طلب استزادة («اشرح أكثر/المزيد/أكمل») ⇒ السؤال السابق نفسه بعمق أكبر.
- إشارة إلى الرد السابق («ترجمه/لخصه/ترجم الرد للإنجليزية») ⇒ عملية على نص الرد السابق.
- أي رسالة مكتملة بذاتها تبقى كما هي حرفيًا (لا تخمين).
الأسئلة السابقة تُحل بالتسلسل (سلسلة متابعات: اليابان ⇒ وفرنسا؟ ⇒ وكم مساحتها؟).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_AR_DIAC = re.compile(r"[\u064B-\u0652\u0640]")
_WS = re.compile(r"\s+")
_PUNCT_END = re.compile(r"[\s؟?!.،,:;]+$")

# كلمات السؤال والربط (لا تُعد كيانًا)
_AR_STOP = {
    "ما", "ماذا", "هي", "هو", "هم", "كم", "من", "متى", "أين", "اين", "هل", "كيف", "لماذا", "لما", "عن",
    "في", "على", "إلى", "الى", "مع", "أو", "او", "ثم", "هذا", "هذه", "ذلك", "تلك", "التي", "الذي", "اي",
    "أي", "أكثر", "اكثر", "أفضل", "افضل", "عدد", "ماهي", "ماهو", "يا", "لي", "لنا", "بين", "كل", "قد",
    "ان", "أن", "إن", "كان", "يكون", "تكون", "طيب", "حسنا", "اذا", "إذا", "و",
}
_EN_STOP = {
    "what", "which", "who", "whom", "when", "where", "why", "how", "is", "are", "was", "were", "the", "a",
    "an", "of", "in", "on", "at", "to", "for", "and", "or", "do", "does", "did", "many", "much", "tell",
    "me", "about", "its", "their", "it", "they", "there", "his", "her", "please", "give", "with", "by",
    "number", "best", "most", "more", "can", "you", "i", "we",
}
# خصائص يُسأل عنها عن كيان (جذور عربية بلا «ال» وبلا تاء مربوطة/مبسوطة؛ وإنجليزية)
_AR_PROPS = (
    "عاصم", "سكان", "مساح", "عمل", "لغ", "رئيس", "ملك", "حاكم", "تاريخ", "عمر", "طول", "ارتفاع", "مؤسس",
    "تأسيس", "موقع", "سعر", "فوائد", "فائد", "أضرار", "اضرار", "ضرر", "مكونات", "أعراض", "اعراض", "علاج",
    "أسباب", "اسباب", "سبب", "عيوب", "مميزات", "ميزات", "خصائص", "استخدامات", "عاصمت", "مساحت", "عملت",
    "لغت", "عدد", "حجم", "وزن", "قيم", "ثمن", "مدة", "مد", "مكان", "عنوان", "نتائج", "تعريف", "معنى",
    "مقر", "شعار", "علم", "نشيد", "اقتصاد", "مناخ", "طقس", "جغرافي", "حدود", "ديان", "مدن", "أشهر", "اشهر",
)
_EN_PROPS = (
    "capital", "population", "people", "area", "size", "currency", "language", "president", "king",
    "leader", "history", "age", "height", "founder", "founded", "location", "price", "benefits",
    "risks", "side effects", "ingredients", "symptoms", "treatment", "causes", "pros", "cons",
    "features", "uses", "weather", "climate", "economy", "flag", "cities", "borders", "religion",
)
_AR_PRON_SUFFIX = ("هما", "هم", "هن", "ها", "ه")
_EN_PRONOUNS = {"it", "its", "they", "their", "them", "there", "he", "she", "his", "her", "this", "that"}

_MORE = re.compile(
    r"^(?:و\s*)?(?:اشرح|وضح|وضّح|فصل|فصّل|زدني|اعطني|أعطني|عطني|أريد|اريد|ابي|أبي)?\s*"
    r"(?:أكثر|اكثر|المزيد|بالتفصيل|تفصيل(?:ا|اً)?|مزيد(?:ا|اً)?)\s*$|"
    r"^(?:أكمل|اكمل|كمل|كمّل|تابع|استمر|واصل)\s*$|"
    r"^(?:tell me )?(?:more|elaborate|continue|go on|explain more|more details?)\s*$", re.I)
_PREV_REF = re.compile(
    r"^(?:من فضلك\s+|لو سمحت\s+)?(ترجم|لخص|لخّص|اختصر|اعد صياغة|أعد صياغة|translate|summari[sz]e|shorten)"
    r"(?:ه|ها|ي)?\s*(.*)$", re.I)
_PREV_TARGET_WORDS = ("الرد", "الجواب", "الإجابة", "الاجابة", "هذا", "ذلك", "الكلام", "النص", "it", "this",
                      "that", "the answer", "your answer")
_LANG_NAMES = {
    "الإنجليزية": "en", "الانجليزية": "en", "الانجليزي": "en", "الإنجليزي": "en", "انجليزي": "en",
    "english": "en", "الفرنسية": "fr", "فرنسي": "fr", "french": "fr", "الإسبانية": "es", "الاسبانية": "es",
    "spanish": "es", "الألمانية": "de", "الالمانية": "de", "german": "de", "العربية": "ar", "عربي": "ar",
    "arabic": "ar", "التركية": "tr", "turkish": "tr", "الأردية": "ur", "الاردية": "ur", "urdu": "ur",
    "الصينية": "zh", "chinese": "zh", "الروسية": "ru", "russian": "ru", "الهندية": "hi", "hindi": "hi",
    "اليابانية": "ja", "japanese": "ja", "الإيطالية": "it", "الايطالية": "it", "italian": "it",
}
_SWAP_AR = re.compile(r"^(?:و\s*)?(?:ماذا|ماذا\s+عن|ما\s+بال|طيب|وش|ايش|إيش)\s*(?:عن|بـ|ب)?\s+(.+)$")
_SWAP_EN = re.compile(r"^(?:and\s+)?(?:what|how)\s+about\s+(.+)$", re.I)
_LEAD_AND_AR = re.compile(r"^و(?=(?:كم|ما|ماذا|من|متى|أين|اين|هل|كيف|لماذا|ماهي|ماهو)\b)")
_PROMPT_LINE = re.compile(r"الوصف المستخدم(?: للتوليد)?:\s*(.+)")


def _norm(s: str) -> str:
    return _WS.sub(" ", _AR_DIAC.sub("", str(s or ""))).strip()


def _strip_end(s: str) -> str:
    return _PUNCT_END.sub("", s).strip()


def _is_ar(s: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", s or ""))


def _ar_root(w: str) -> str:
    w = w[2:] if w.startswith("ال") and len(w) > 4 else w
    return w[:-1] if w.endswith(("ة", "ت")) and len(w) > 3 else w


def _is_prop_word(w: str) -> bool:
    lw = w.lower()
    if _is_ar(w):
        base = lw[1:] if lw.startswith("و") and len(lw) > 3 else lw
        for suf in _AR_PRON_SUFFIX:
            if base.endswith(suf) and len(base) - len(suf) >= 2:
                base = base[: -len(suf)]
                break
        r = _ar_root(base)
        return any(r.startswith(p) or base.startswith(p) for p in _AR_PROPS)
    return any(lw.startswith(p) for p in _EN_PROPS)


def _pron_word(w: str) -> Optional[str]:
    """كلمة عربية بضمير متصل لخاصية ⇒ اسم الخاصية بلا ضمير (سكانها ⇒ سكان، مساحتها ⇒ مساحة)."""
    if not _is_ar(w):
        return None
    base = w[1:] if w.startswith("و") and len(w) > 4 else w
    for suf in _AR_PRON_SUFFIX:
        if base.endswith(suf) and len(base) - len(suf) >= 2:
            stem = base[: -len(suf)]
            if not _is_prop_word(stem) and not _is_prop_word(stem + "ة"):
                return None
            if stem.endswith("ت") and len(stem) > 2:
                stem = stem[:-1] + "ة"
            return stem
    return None


def entity_of(question: str) -> str:
    """الكيان المسؤول عنه في سؤال مكتمل: ما يبقى بعد حذف أدوات السؤال وكلمات الخصائص."""
    try:
        import world_search
        q = world_search.core_question(question)
    except Exception:  # TOLERATED: بلا وحدة البحث ⇒ النص كما هو
        q = question
    q = _strip_end(_norm(q))
    if not _is_ar(q):
        m = re.search(r"\b(?:of|in|about|for)\s+(?:the\s+)?([A-Z][\w\-]*(?:\s+[A-Z][\w\-]*)*)", q)
        if m:
            return m.group(1)
    out: List[str] = []
    for w in q.split():
        lw = w.lower().strip("؟?!.,،")
        if not lw:
            continue
        if lw.startswith("و") and _is_ar(lw) and lw[1:] in _AR_STOP:
            continue
        if lw in _AR_STOP or lw in _EN_STOP or _is_prop_word(lw) or _pron_word(lw):
            if out:
                break  # الكيان متصل — أول فاصل بعده ينهيه («اليابان وكم…»)
            continue
        if lw.startswith("و") and _is_ar(lw) and out and len(lw) > 3:
            break  # «و» عطف بداية جملة تالية
        out.append(w.strip("؟?!.,،"))
    return " ".join(out[:5]).strip()


def _user_turns(history) -> List[str]:
    return [str(t.get("content") or "") for t in (history or [])
            if isinstance(t, dict) and t.get("role") == "user" and str(t.get("content") or "").strip()]


def _last_assistant(history) -> str:
    for t in reversed(list(history or [])):
        if isinstance(t, dict) and t.get("role") == "assistant" and str(t.get("content") or "").strip():
            return str(t["content"])
    return ""


def last_media_prompt(history) -> Optional[str]:
    """وصف آخر وسائط ولّدها النظام (يُكتب في الرد «الوصف المستخدم: …») — لتعديلها بالمتابعة."""
    for t in reversed(list(history or [])):
        if isinstance(t, dict) and t.get("role") == "assistant":
            m = _PROMPT_LINE.search(str(t.get("content") or ""))
            if m:
                return m.group(1).strip()
    return None


def target_lang_in(text: str, default: Optional[str] = None) -> Optional[str]:
    low = _norm(text).lower()
    for name, code in _LANG_NAMES.items():
        if re.search(r"(?:^|\s|[لب]|إلى\s*|الى\s*|to\s+|into\s+)" + re.escape(name) + r"(?:\s|$)", low):
            return code
    return default


def _resolve_one(text: str, prev_standalone: Optional[str]) -> Dict[str, Any]:
    raw = _norm(text)
    res = {"original": text, "standalone": text, "followup": False, "kind": "none", "entity": None}
    if not raw or not prev_standalone:
        return res
    body = _strip_end(raw)
    words = body.split()
    prev = _strip_end(_norm(prev_standalone))
    ent = entity_of(prev)

    # ١) استزادة
    if _MORE.match(body):
        res.update(standalone=prev, followup=True, kind="more", entity=ent or None)
        return res
    # ٢) تبديل الكيان: «وماذا عن فرنسا» / what about France
    m = _SWAP_AR.match(body) or _SWAP_EN.match(body)
    if m and len(words) <= 7:
        new_ent = _strip_end(m.group(1))
        if new_ent and not any(_pron_word(w) for w in new_ent.split()):
            if ent and ent in prev:
                res.update(standalone=prev.replace(ent, new_ent, 1), followup=True, kind="entity_swap",
                           entity=new_ent)
            else:
                res.update(standalone=f"{prev} — {new_ent}", followup=True, kind="entity_swap", entity=new_ent)
            return res
    if not ent:
        return res
    # ٣) ضمير متصل بخاصية (عربي)
    changed, out = False, []
    for w in words:
        stem = _pron_word(w)
        if stem:
            out.append(f"{stem} {ent}")
            changed = True
        else:
            out.append(w)
    if changed:
        s = " ".join(out)
        s = _LEAD_AND_AR.sub("", s).strip()
        res.update(standalone=s, followup=True, kind="pronoun", entity=ent)
        return res
    # ٣ب) ضمائر إنجليزية
    if not _is_ar(body):
        toks = re.findall(r"[\w'\-]+|[^\w\s]", body)
        lowt = [t.lower() for t in toks]
        if any(t in _EN_PRONOUNS for t in lowt) and len(toks) <= 14:
            rep = []
            for t in toks:
                lt = t.lower()
                if lt in ("its", "their", "his", "her"):
                    rep.append(f"{ent}'s")
                elif lt in ("it", "they", "them", "there", "he", "she", "this", "that"):
                    rep.append(ent)
                else:
                    rep.append(t)
            s = re.sub(r"^\s*and\s+", "", " ".join(rep), flags=re.I)
            res.update(standalone=s, followup=True, kind="pronoun", entity=ent)
            return res
    # ٤) سؤال خاصية محذوف الكيان: «وكم المساحة؟» / «والعملة؟» (قصير، يبدأ بعطف، بلا كيان جديد)
    lead_and = body.startswith("و") or body.lower().startswith("and ")
    if lead_and and len(words) <= 4 and any(_is_prop_word(w) for w in words) and not entity_of(body):
        s = _LEAD_AND_AR.sub("", body).strip()
        s = re.sub(r"^and\s+", "", s, flags=re.I)
        if s.startswith("و") and not re.match(r"^و(?:كم|ما|من)", s):
            s = s[1:]
        res.update(standalone=f"{s} {ent}", followup=True, kind="elliptic", entity=ent)
        return res
    return res


def resolve(text: str, history=None) -> Dict[str, Any]:
    """الرسالة الحالية ⇒ سؤال قائم بذاته من سياق المحادثة (حتمي، بلا نموذج لغوي)."""
    users = _user_turns(history)
    prev_standalone: Optional[str] = None
    for u in users[-8:]:  # حل السلسلة بالتتابع (متابعة على متابعة)
        r = _resolve_one(u, prev_standalone)
        if r["kind"] not in ("prev_op",):
            prev_standalone = r["standalone"]
    raw = _strip_end(_norm(text))
    m = _PREV_REF.match(raw)
    prev_answer = _last_assistant(history)
    if m and prev_answer:
        verb, rest = m.group(1).lower(), _norm(m.group(2))
        refers = (not rest) or any(rest.startswith(w) or (" " + w) in (" " + rest) for w in _PREV_TARGET_WORDS) \
            or bool(target_lang_in(rest)) and len(rest.split()) <= 4
        if refers:
            op = "translate" if verb.startswith(("ترجم", "translate")) else "summarize"
            return {"original": text, "standalone": text, "followup": True, "kind": "prev_op", "op": op,
                    "target_lang": target_lang_in(rest, "en" if _is_ar(raw) else "ar"),
                    "previous_answer": prev_answer, "entity": None}
    return _resolve_one(text, prev_standalone)


def summarize_extractive(text: str, max_sentences: int = 4) -> str:
    """تلخيص استخلاصي حتمي: الجمل/النقاط الأعلى كثافة بمفردات النص (بلا نموذج لغوي)."""
    body = re.split(r"\n\s*(?:المصادر|Sources)\b", str(text or ""), maxsplit=1)[0]
    parts = [p.strip(" •-*\t") for p in re.split(r"(?<=[.!؟?])\s+|\n+", body) if len(p.strip()) > 25]
    if not parts:
        return str(text or "").strip()[:600]
    from collections import Counter
    toks = lambda s: [w for w in re.findall(r"[\w\u0600-\u06FF]{3,}", s.lower())
                      if w not in _AR_STOP and w not in _EN_STOP]
    freq = Counter(w for p in parts for w in toks(p))
    scored = sorted(range(len(parts)), key=lambda i: -sum(freq[w] for w in set(toks(parts[i])))
                    / (1 + len(toks(parts[i])) ** 0.5))
    keep = sorted(scored[:max_sentences])
    return "\n".join("• " + re.sub(r"\s*\[\d+\]\s*", " ", parts[i]).strip() for i in keep)
