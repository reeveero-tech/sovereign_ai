"""R-838: المحلل الدلالي متعدد اللغات — فهم من النص الأصلي بلا ترجمة وسيطة.

المعمارية الإلزامية 4.2: استخراج النية والكيانات والمراجع والعلاقات الخطابية
وأفعال الكلام والغموض من النص الأصلي مباشرة، بعقد JSON إلزامي.

قرارات التصميم (ADR-001):
- التحليل صرفي-دلالي حتمي على النص الأصلي: العربية تُحلَّل بخصائصها
  (ال تعريف، تاء التأنيث، جمع/مثنى، ضمائر متصلة/منفصلة، حذف فاعل) والإنجليزية
  بخصائصها (the/a، agreement، ضمائر) — لا يمر النص بأي مترجم.
- الضمير المتصل جزء من الكلمة («سكانها») يُستخرج بمورفولوجيا عربية صريحة.
- حذف الفاعل يُكشف بأفعال شائعة مصرفة؛ الفاعل يُسترجع من جدول الكيانات لاحقًا.
- الجملة المختلطة (تبديل شيفرة) تُحلَّل كإطار واحد موحد من مقاطعها.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from . import detector as _det
from . import lexicon as _lex
from . import scripts as _sc

# R-838: نمط الروابط — كيان URL كامل قبل التقطيع (المقطع يمزق الروابط)
_URL_RE = re.compile(r"https?://[^\s،,؛;]+|www\.[^\s،,؛;]+")

# ---------------------------------------------------------------------------
# جداول مورفولوجية
# ---------------------------------------------------------------------------

_DETACHED_PRON_AR: Dict[str, Dict[str, str]] = {
    "هو": {"person": "3", "gender": "m", "number": "sg"},
    "هي": {"person": "3", "gender": "f", "number": "sg"},
    "هما": {"person": "3", "gender": "unknown", "number": "du"},
    "هم": {"person": "3", "gender": "m", "number": "pl"},
    "هن": {"person": "3", "gender": "f", "number": "pl"},
    "أنا": {"person": "1", "gender": "unknown", "number": "sg"},
    "انا": {"person": "1", "gender": "unknown", "number": "sg"},
    "نحن": {"person": "1", "gender": "unknown", "number": "pl"},
    "أنت": {"person": "2", "gender": "m", "number": "sg"},
    "انت": {"person": "2", "gender": "m", "number": "sg"},
    "أنتِ": {"person": "2", "gender": "f", "number": "sg"},
    "أنتما": {"person": "2", "gender": "unknown", "number": "du"},
    "أنتم": {"person": "2", "gender": "m", "number": "pl"},
    "انتم": {"person": "2", "gender": "m", "number": "pl"},
    "أنتن": {"person": "2", "gender": "f", "number": "pl"},
}

# لواحق الضمائر المتصلة (الأطول أولًا)
_ATTACHED_PRON_AR: List[Tuple[str, Dict[str, str]]] = [
    ("هما", {"person": "3", "gender": "unknown", "number": "du"}),
    ("كما", {"person": "2", "gender": "unknown", "number": "du"}),
    ("كم", {"person": "2", "gender": "m", "number": "pl"}),
    ("كن", {"person": "2", "gender": "f", "number": "pl"}),
    ("هم", {"person": "3", "gender": "m", "number": "pl"}),
    ("هن", {"person": "3", "gender": "f", "number": "pl"}),
    ("نا", {"person": "1", "gender": "unknown", "number": "pl"}),
    ("ها", {"person": "3", "gender": "f", "number": "sg"}),
    ("ه", {"person": "3", "gender": "m", "number": "sg"}),
    ("ك", {"person": "2", "gender": "unknown", "number": "sg"}),
    ("ي", {"person": "1", "gender": "unknown", "number": "sg"}),
]

_DEMONSTRATIVES_AR: Dict[str, Dict[str, str]] = {
    "هذا": {"gender": "m", "number": "sg"},
    "هذه": {"gender": "f", "number": "sg"},
    "ذلك": {"gender": "m", "number": "sg"},
    "تلك": {"gender": "f", "number": "sg"},
    "هذان": {"gender": "m", "number": "du"},
    "هاتان": {"gender": "f", "number": "du"},
    "هؤلاء": {"gender": "unknown", "number": "pl"},
    "أولئك": {"gender": "unknown", "number": "pl"},
    "اولئك": {"gender": "unknown", "number": "pl"},
}

_EN_PRONOUNS: Dict[str, Dict[str, str]] = {
    "he": {"person": "3", "gender": "m", "number": "sg"},
    "him": {"person": "3", "gender": "m", "number": "sg"},
    "his": {"person": "3", "gender": "m", "number": "sg"},
    "she": {"person": "3", "gender": "f", "number": "sg"},
    "her": {"person": "3", "gender": "f", "number": "sg"},
    "hers": {"person": "3", "gender": "f", "number": "sg"},
    "it": {"person": "3", "gender": "n", "number": "sg"},
    "its": {"person": "3", "gender": "n", "number": "sg"},
    "they": {"person": "3", "gender": "unknown", "number": "pl"},
    "them": {"person": "3", "gender": "unknown", "number": "pl"},
    "their": {"person": "3", "gender": "unknown", "number": "pl"},
    "we": {"person": "1", "gender": "unknown", "number": "pl"},
    "i": {"person": "1", "gender": "unknown", "number": "sg"},
    "you": {"person": "2", "gender": "unknown", "number": "unknown"},
    "this": {"person": "3", "gender": "unknown", "number": "sg"},
    "that": {"person": "3", "gender": "unknown", "number": "sg"},
    "these": {"person": "3", "gender": "unknown", "number": "pl"},
    "those": {"person": "3", "gender": "unknown", "number": "pl"},
}

_QUESTION_AR = {"ما", "ماذا", "ماهو", "ماهي", "من", "متى", "أين", "اين", "كيف",
                "لماذا", "ليش", "ليه", "كم", "أي", "اي", "هل", "وش", "إيش", "ايش",
                "مين"}
_QUESTION_EN = {"what", "who", "whom", "when", "where", "why", "how", "which",
                "whose", "does", "do", "did", "is", "are", "can"}

_REQUEST_AR = {"أعطني", "اعطني", "أعطي", "عطني", "اشرح", "وضح", "وضّح", "فصل",
               "فصّل", "لخص", "لخّص", "ترجم", "اكتب", "ابحث", "أنشئ", "انشئ",
               "اصنع", "ابن", "ابني", "أصلح", "اصلح", "صحح", "راجع", "دقق",
               "واصل", "تابع", "أكمل", "اكمل", "أعد", "اعد", "زد", "زودني", "أضف",
               "اضف", "احذف", "افتح", "اقفل", "فعّل", "نظّف", "نظف", "نظم",
               "بيّن", "بين", "اذكر", "ساعدني", "ساعد", "نفّذ", "نفذ", "استخرج",
               "جهّز", "جهز", "شوف", "دور", "جيب", "هات", "ابدأ", "ابدا"}
_REQUEST_EN = {"please", "give", "show", "explain", "summarize", "translate",
               "write", "create", "build", "fix", "review", "continue", "find",
               "search", "add", "remove", "delete", "open", "run", "deploy",
               "check", "list", "compare", "generate", "make", "help", "tell"}
_WISH_AR = {"أريد", "اريد", "أبي", "ابي", "أحتاج", "احتاج", "ممكن", "لو سمحت",
            "من فضلك", "بغيت", "ابغى", "رغبت"}
_GREETING = {"مرحبا", "مرحبتين", "أهلا", "اهلا", "السلام", "سلام", "هلا", "hi",
             "hello", "hey"}
_THANKS = {"شكرا", "شكرًا", "مشكور", "thanks", "thank"}
_CONFIRM = {"نعم", "ايوه", "اكيد", "تمام", "طيب", "حسنا", "حسنًا", "اوكي", "ok",
            "okay", "yes", "sure", "صح"}
_MORE_WORDS = {"المزيد", "أكثر", "اكثر", "more", "continue", "استمر"}

_DISCOURSE_AR: List[Tuple[Tuple[str, ...], str]] = [
    (("لكن", "بس", "غير", "بالمقابل"), "contrast"),
    (("إذن", "اذاً", "إذاً", "بالتالي", "لذلك", "وبالتالي"), "result"),
    (("يعني", "مثلًا", "مثلا"), "elaboration"),
    (("لأن", "لأنه", "لأنها", "بسبب", "لان"), "cause"),
    (("أيضاً", "أيضًا", "كذلك", "بالإضافة"), "addition"),
]
_DISCOURSE_EN: List[Tuple[Tuple[str, ...], str]] = [
    (("but", "however", "although"), "contrast"),
    (("so", "therefore", "thus", "hence"), "result"),
    (("meaning", "example", "basically"), "elaboration"),
    (("because", "since", "due"), "cause"),
    (("also", "moreover", "additionally"), "addition"),
]

_AR_STOP_EXTRA = {
    "شيء", "شي", "الشي", "واحد", "واحدة", "اثنان", "اثنين", "كثير", "قليل",
    "جميع", "بعض", "هذا", "هذه", "ذلك", "تلك", "هو", "هي", "هم", "هن", "هما",
    "أنا", "انا", "نحن", "أنت", "انت", "أنتم", "انتم", "أنتن",
    "لا", "ما", "لم", "لن", "قد", "هل", "كل", "بعد", "قبل", "الآن", "الان",
    "أيضا", "ايضا", "فقط", "جدا", "جداً", "شوي", "مره", "مرة",
    "الحين", "البارحة", "غدا", "غدًا", "اليوم", "امس", "أمس",
    "عندي", "عنده", "عندهم", "عندك", "معي", "معه", "معها", "لي", "لك", "له",
    "لها", "لهم", "فيها", "فيه", "منه", "منها", "عليه", "عليها", "إليه", "إليها",
    "به", "بها", "ذات", "نفس", "حال", "اللي", "الذي", "التي", "الذين", "اللاتي",
    "كان", "كانت", "يكون", "تكون", "ليس", "ليست", "صار", "اصبح", "أصبح", "بقى",
    # صفات شائعة — ليست كيانات (إحالة الضمائر يجب أن تصل للكيان لا الصفة)
    "سعيد", "سعيدة", "سعيدا", "كبير", "كبيرة", "صغير", "صغيرة", "جديد", "جديدة",
    "قديم", "قديمة", "جميل", "جميلة", "سريع", "سريعة", "بطيء", "بطيئة", "جيد",
    "جيدة", "جيدةً", "سيء", "سيئة", "سهل", "سهلة", "صعب", "صعبة", "ممتاز",
    "ممتازة", "رائع", "رائعة", "طويل", "طويلة", "قصير", "قصيرة", "قوي", "قوية",
    "ضعيف", "ضعيفة", "غني", "غنية", "فقير", "فقيرة", "مشهور", "مشهورة", "مهم",
    "مهمة", "خطير", "خطيرة", "مميز", "مميزة", "محترم", "محترمة", "لطيف", "لطيفة",
    "ذكي", "ذكية", "متعب", "متعبا", "مرتاح", "مرتاحة", "زعلان", "فرحان", "فرحانة",
    "جاهز", "جاهزة", "مفتوح", "مفتوحة", "مغلق", "مغلقة", "كامل", "كاملة", "ناقص",
    "مختلف", "مختلفة", "متشابه", "أحمر", "حمراء", "أزرق", "زرقاء", "أخضر",
    "خضراء", "أصفر", "صفراء", "أبيض", "بيضاء", "أسود", "سوداء", "عالي", "عالية",
    "منخفض", "منخفضة", "كثيرة", "قليل", "قليلا", "ممتازةً", "مريح", "مريحة",
    "مشغول", "مشغولة", "متأخر", "متأخرة", "مبكر", "مبكرة", "غالي", "رخيص",
    "رخيصة", "شغالة", "شغال", "خامل", "نشيط", "نشيطه", "هادئ", "هادئة", "صاخب",
    # مشاريع/أحوال شائعة — ليست كيانات
    "موافق", "موافقة", "موافقًا", "معترض", "معترضة", "مستمر", "مستمرة", "موجود",
    "موجودة", "مطلوب", "مطلوبة", "منتهي", "منتهية", "قائم", "قائمة", "منتظر",
    "منزعج", "منزعجة", "خايف", "خايفة", "زعلان", "زعلانة", "معصب", "معصبة",
    "فرح", "فرحة", "حزين", "حزينة", "متأكد", "متأكدة", "قادر", "قادرة", "عارف",
    "عارفة", "فاهم", "فاهمة", "شايف", "شايفة", "قاعد", "واقف", "واقفة", "ناسي",
    "ناسية", "معجب", "معجبة", "سعيدًا", "سعيدةً", "معجبًا", "المكان", "مكان",
}
_EN_STOP_EXTRA = {
    "thing", "things", "stuff", "one", "ones", "much", "many", "few", "all",
    "some", "now", "today", "yesterday", "tomorrow", "time", "way", "ways",
    "something", "anything", "nothing", "someone", "anyone", "me", "my", "our",
}

# أفعال عربية شائعة مصرفة — لكشف حذف الفاعل
_AR_VERB_ROOTS = (
    "ذهب", "جاء", "قال", "أراد", "اراد", "استخدم", "فتح", "أرسل", "ارسل",
    "راجع", "درس", "عمل", "وصل", "انتهى", "انتها", "بدأ", "بدات", "بدا", "وافق",
    "رفض", "سأل", "سال", "أجاب", "اجاب", "أعطى", "اعطى", "اشترى", "اشترا",
    "سافر", "عاد", "غادر", "قابل", "عرف", "فهم", "شرح", "وضح", "لخص",
    "ترجم", "كتب", "قرأ", "قرا", "سمع", "رأى", "راى", "أحب", "احب", "كره",
    "احتاج", "قدر", "اعتقد", "ظن", "خاف", "أكل", "اكل", "شرب", "نام", "صحا",
    "استيقظ", "جرب", "أصلح", "اصلح", "حدث", "تغير", "صار", "أصبح", "اصبح",
    "بقي", "بقا", "وجد", "لقى", "لقي", "حصل", "استلم", "سلم", "رد", "أشار",
    "اشار", "ذكر", "نسي", "نسا", "تعلم", "نشر", "أكد", "اكد", "أعلن", "اعلن",
    "أصدر", "اصدر", "أطلق", "اطلق", "جدد", "أضاف", "اضاف", "حذف", "بدل",
    "تحدث", "تكلم", "ناقش", "اتفق", "وصلت",
    # R-838: جذور شائعة إضافية — أفعال شعور/طلب/سكن تظهر كثيرًا مع ضمائر متصلة
    "عجب", "سكن", "طلب", "شكر", "وصف", "اهتم", "احترم", "استقبل", "استحق",
    "استمر", "استمتع", "استفاد", "استغرب", "دهش", "فرح", "حزن", "غضب",
    "خجل", "فخر", "افتخر", "انبهر", "بهر", "اشتاق", "افتقد", "احب",
)
_AR_VERB_INFLECTIONS = ("", "ت", "وا", "نا", "تم", "تما", "تن", "ات", "ها", "ه",
                        "هم", "هن", "هما", "كم", "كن", "ك", "ته", "تها", "تها", "ا")
_AR_VERBS: set = set()
for _r in _AR_VERB_ROOTS:
    for _s in _AR_VERB_INFLECTIONS:
        _AR_VERBS.add(_r + _s)
# R-838: صيغ المضارع (سوابق تـ/يـ/أ/نـ + جذر) — «تعجبني» فعل مضارع لا اسم
for _r in _AR_VERB_ROOTS:
    for _p in ("ت", "ي", "أ", "ن"):
        _AR_VERBS.add(_p + _r)
_AR_VERBS |= {"يوجد", "توجد", "يعمل", "تعمل", "أعمل", "نقول", "يقول", "أقول",
              "أستخدم", "تستخدم", "نستخدم", "يستخدم", "أحتاج", "تحتاج", "نحتاج",
              "يحتاج", "يرسل", "ترسل", "نرسل", "يستطيع", "تستطيع", "أستطيع"}

_AR_STOP = _AR_STOP_EXTRA | _det._AR_FUNCWORDS | _QUESTION_AR
_EN_STOP = _EN_STOP_EXTRA | _REQUEST_EN | _GREETING | _THANKS | _CONFIRM


def _normset(words) -> set:
    return {_sc.norm_for_match(w) for w in words}


_N_QUESTION_AR = _normset(_QUESTION_AR)
_N_REQUEST_AR = _normset(_REQUEST_AR)
_N_WISH_AR = _normset(_WISH_AR)
_N_GREETING = _normset(_GREETING)
_N_THANKS = _normset(_THANKS)
_N_CONFIRM = _normset(_CONFIRM)
_N_MORE = _normset(_MORE_WORDS)
_N_AR_STOP = _normset(_AR_STOP) | _AR_STOP


def _ar_features(noun: str) -> Dict[str, str]:
    """جنس/عدد من مورفولوجيا الاسم العربي (بعد تجريد الضمير المتصل)."""
    w = noun
    for suf, _feat in _ATTACHED_PRON_AR:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    if w.endswith("ات") and len(w) > 3:
        return {"gender": "f", "number": "pl"}
    if w.endswith(("ون", "ين")) and len(w) > 4:
        return {"gender": "m", "number": "pl"}
    if w.endswith("ان") and len(w) > 4:
        return {"gender": "m", "number": "du"}
    if w.endswith("ة"):
        return {"gender": "f", "number": "sg"}
    return {"gender": "m", "number": "sg"}


def _ar_definiteness(token: str) -> str:
    if token.startswith("ال") and len(token) > 3:
        return "def"
    return "indef"


class SemanticAnalyzer:
    """يحلل نصًا أصليًا (أي لغة/مختلطًا) إلى إطار دلالي بالعقد الإلزامي.

    بلا حالة بين الاستدعاءات — الحالة (جدول الكيانات/الذاكرة) مسؤولية
    طبقة المحادثة (pipeline.ConversationState).
    """

    def __init__(self, utterance_id: str = ""):
        self.utterance_id = utterance_id

    def analyze(self, text: str, utterance_id: str = "") -> Dict[str, Any]:
        uid = utterance_id or self.utterance_id or "utt_0"
        detection = _det.detect(text)
        # R-838: الروابط كيانات كاملة قبل التقطيع (التقطيع يمزقها) — «هو» بعد
        # ذكر مستودع GitHub تعني المستودع نفسه (عقد R-834/R-835 محفوظ)
        urls = _URL_RE.findall(text)
        tokens = _sc.tokenize(_URL_RE.sub(" ", text))

        entities: List[Dict[str, Any]] = []
        references: List[Dict[str, Any]] = []
        ambiguities: List[Dict[str, Any]] = []

        for _u in dict.fromkeys(urls):
            _u_pos = len(_sc.tokenize(text[: text.find(_u)])) if _u in text else 0
            entities.append({
                "surface": _u, "lang": "unknown", "type": "url",
                "concept_key": None, "role": "object",
                "gender": "unknown", "number": "sg", "definiteness": "def",
                "pos": _u_pos,
            })

        if _sc.has_arabic(text):
            ar_entities, ar_refs, ar_amb = self._analyze_arabic(tokens, text)
            ar_refs, ar_amb = self._analyze_arabic_post(ar_refs, ar_entities, ar_amb)
            entities.extend(ar_entities)
            references.extend(ar_refs)
            ambiguities.extend(ar_amb)
        if _sc.has_latin(text):
            en_entities, en_refs = self._analyze_latin(tokens)
            entities.extend(en_entities)
            references.extend(en_refs)

        # تكرار السطح نفسه ⇒ كيان واحد
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for e in entities:
            key = _sc.norm_for_match(e["surface"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(e)
        for i, e in enumerate(uniq, 1):
            e["id"] = f"ent_{i}"

        intent, speech_act = self._classify(text, tokens)

        return {
            "utterance_id": uid,
            "languages": detection.languages or ["en"],
            "segments": [s.to_dict() for s in detection.segments],
            "intent": {"label": intent, "confidence": 0.9 if intent != "unknown" else 0.3},
            "speech_act": speech_act,
            "entities": uniq,
            "references": references,
            "discourse_relations": self._discourse(tokens),
            "ambiguities": ambiguities,
            "confidence": round(0.5 + 0.5 * detection.confidence, 3),
            "detection": detection.to_dict(),
            "analysis_path": "original_text",  # إثبات: لا ترجمة وسيطة
        }

    # ------------------------------------------------------------------
    def _analyze_arabic(self, tokens: List[str], text: str):
        entities: List[Dict[str, Any]] = []
        references: List[Dict[str, Any]] = []
        ambiguities: List[Dict[str, Any]] = []
        subject_seen_before_verb = False
        saw_content_word = False

        _FUNC = _DETACHED_PRON_AR | _DEMONSTRATIVES_AR
        _PREPS = ("على", "في", "إلى", "الى", "من", "ب", "ل", "مع", "عند", "حول",
                  "عن", "إلى", "رغم", "خلال", "بعد", "قبل")

        def _role_for_entity() -> str:
            """دور الذكر النحوي: فاعل أو مفعول — يراعي الترتيب العربي VSO.

            - اسم قبل أول فعل (SVO نادر) ⇒ فاعل.
            - أول اسم بعد الفعل (VSO القياسي: «أرسل أحمدُ التقريرَ») ⇒ فاعل.
            - ما بعده ⇒ مفعول.
            """
            if not saw_first_verb:
                return "subject"
            return "subject" if not saw_subject_after_verb else "object"

        saw_first_verb = False
        saw_subject_after_verb = False
        after_prep = False   # الاسم بعد حرف جر مفعول به مجرور لا فاعل

        for idx, tok in enumerate(tokens):
            self._cur_pos = idx   # R-838: موقع الذكر — للإحالة والكيان
            # الكلمة كاملة أولًا — «وصلتها» فعلٌ جذره يبدأ بالواو، لا سابقة عطف
            base = tok
            if base not in _FUNC and base not in _AR_VERBS and base not in _AR_STOP \
                    and base not in _QUESTION_AR:
                stripped = tok[1:] if tok[:1] in ("و", "ف") and len(tok) >= 3 else tok
                if stripped in _FUNC or stripped in _AR_VERBS or stripped in _AR_STOP \
                        or stripped in _QUESTION_AR:
                    base = stripped

            # ١) ضمير منفصل
            if base in _DETACHED_PRON_AR:
                references.append(self._ref(tok, "pronoun", _DETACHED_PRON_AR[base]))
                subject_seen_before_verb = True
                continue

            # ٢) إشارة
            if base in _DEMONSTRATIVES_AR:
                references.append(self._ref(tok, "demonstrative", _DEMONSTRATIVES_AR[base]))
                subject_seen_before_verb = True
                continue

            nb = _sc.norm_for_match(base)

            # ٣) فعل ⇒ (أ) ضمير مفعول متصل بالفعل يُستخرج دائمًا
            #     (ب) إن كان أول كلمة محتوى بلا فاعل قبلها ⇒ حذف فاعل
            # R-838: «تعجبني» = فعل + مفعول «ني» — الجذر بعد نزع «ني» فعل
            # معروف ⇒ فعل لا اسم (وإلا لَصِقَ الضمير خطأً وقُطِع الفعل)
            _stem_ni = base[:-2] if base.endswith("ني") else None
            if base in _AR_VERBS or nb in _normset(_AR_VERBS) or (
                _stem_ni and (_stem_ni in _AR_VERBS
                              or _sc.norm_for_match(_stem_ni) in _normset(_AR_VERBS))):
                saw_first_verb = True
                saw_subject_after_verb = False   # فاعل جديد محتمل بعد هذا الفعل
                for suf, feat in _ATTACHED_PRON_AR:
                    if base.endswith(suf) and len(base) - len(suf) >= 3:
                        pref = self._ref(base, "pronoun", feat)
                        pref["attached_to"] = "verb"   # مفعول متصل بفعل — لا يُستبدل
                        references.append(pref)
                        break
                if not subject_seen_before_verb and not saw_content_word:
                    feat = self._verb_subject_features(base)
                    references.append(self._ref(f"[فاعل محذوف: {base}]", "ellipsis", feat))
                    ambiguities.append({
                        "span": base,
                        "reason": "فاعل محذوف — يُسترجع من جدول الكيانات",
                        "options": ["speaker", "salient_entity"],
                    })
                continue

            # ٤) كلمة وظيفية/استفهام — ليست كيانًا
            if base in _AR_STOP or nb in _N_AR_STOP:
                if base in _PREPS:
                    after_prep = True   # الاسم التالي مجرور لا فاعل
                continue
            # ظرف منون (مبكرًا/سريعًا) — ليس كيانًا
            if tok.endswith(("ً", "اً", "ًا")):
                continue

            # كلمة محتوى (اسم) — الفاعل الصريح أصبح ممكنًا
            if not saw_content_word:
                saw_content_word = True
                subject_seen_before_verb = True
            # دور هذه الكلمة: أول اسم بعد الفعل (VSO) فاعل، وما بعده مفعول —
            # إلا المجرور بعد حرف جر فهو مفعول به دائمًا لا فاعل
            if after_prep:
                role_now = "object"
                after_prep = False
            else:
                role_now = "subject" if (not saw_first_verb or not saw_subject_after_verb) else "object"
                if saw_first_verb and not saw_subject_after_verb:
                    saw_subject_after_verb = True

            # ٥) ضمير متصل (لاحق الاسم/الحرف) — قبل المعجم: «سكانها» اسم+ضمير
            #     لا كيان معجمي واحد
            stem = base
            pron_ref = None
            for suf, feat in _ATTACHED_PRON_AR:
                if base.endswith(suf) and len(base) - len(suf) >= 2:
                    # «ي» المتصلة تُتجنب مع الأسماء المعرفة (الرئيسي صفة لا «رئيس+ي»)
                    if suf == "ي" and base.startswith("ال"):
                        continue
                    pron_ref = self._ref(base, "pronoun", feat)
                    stem = base[: -len(suf)]
                    break
            if pron_ref:
                # حرف جر + ضمير («عليه/فيها/منها») ⇒ تفضيل المفعول في الحل
                for p in _PREPS:
                    if stem == p or (stem.startswith(p) and len(stem) - len(p) <= 1):
                        pron_ref["prep"] = p
                        break
                references.append(pron_ref)
                base = stem  # واصل التحليل على الجذر

            # ٦) كيان: المعجم أولًا — لكن مسندات المعجم (ACT:/PROP:) ليست
            #     مراجع تنازع: «راجع/عاصمة» أفعال وخصائص سؤال لا كيانات
            hit = _lex.lookup_token(base)
            if hit and hit[0].startswith(("ACT:", "PROP:")):
                continue   # مسند سؤال — ليس كيانًا ولا اسمًا عامًا
            if hit:
                key, typ = hit
                # أسماء الأعلام المعجمية: المورفولوجيا العامة لا تنطبق عليها
                # (اليابان ليست مثنى رغم «ان») — الخصائص من نوعها لا لاحقاتها
                if typ in ("country", "city", "org", "product"):
                    feats = {"gender": "unknown", "number": "sg"}
                else:
                    feats = _ar_features(base)
                entities.append({
                    "surface": stem if pron_ref else tok,
                    "lang": "ar", "type": typ, "concept_key": key,
                    "role": role_now, "pos": self._cur_pos,
                    **feats,
                    "definiteness": "def" if base.startswith("ال") else "indef",
                })
                continue

            # ٧) اسم عربي عام (معرف أو نكرة أول ذكر — التنكير يخدم الإحالة لاحقًا)
            if len(base) >= 3:
                entities.append({
                    "surface": base, "lang": "ar", "type": "unknown",
                    "role": role_now, "pos": self._cur_pos,
                    **_ar_features(base),
                    "definiteness": "def" if base.startswith("ال") else "indef",
                })

        return entities, references, ambiguities

    def _analyze_arabic_post(self, references, entities, ambiguities):
        """VSO: إن وُجد فاعل اسمي صريح بعد الفعل فلا حذف فاعل — يُسقط المرجع الزائف."""
        if any(e.get("role") == "subject" and e.get("surface") not in ("", None)
               for e in entities):
            # فاعل صريح موجود ⇒ أزل إحالات الحذف (كانت مبدئية)
            references[:] = [r for r in references if r.get("type") != "ellipsis"]
            ambiguities[:] = [a for a in ambiguities if "فاعل محذوف" not in a.get("reason", "")]
        return references, ambiguities

    # ------------------------------------------------------------------
    def _analyze_latin(self, tokens: List[str]):
        entities: List[Dict[str, Any]] = []
        references: List[Dict[str, Any]] = []
        for i, tok in enumerate(tokens):
            self._cur_pos = i   # R-838: موقع الذكر — للإحالة والكيان
            clean = tok.strip(".,!?;:()[]\"'")
            if not clean:
                continue
            lw = clean.lower()
            if lw in _EN_PRONOUNS:
                references.append(self._ref(clean, "pronoun", _EN_PRONOUNS[lw]))
                continue
            if lw in _EN_STOP or lw in {"the", "a", "an", "is", "are", "was", "were",
                                       "and", "or", "but", "to", "of", "in", "on",
                                       "at", "for", "with", "by", "it", "this", "that"}:
                continue
            hit = _lex.lookup_surface(clean)
            if hit and hit[0].startswith(("ACT:", "PROP:")):
                continue   # مسند سؤال — ليس كيانًا
            if hit:
                key, typ = hit
                entities.append({
                    "surface": clean, "lang": "en", "type": typ, "concept_key": key,
                    "gender": "unknown", "number": "unknown", "pos": self._cur_pos,
                    "definiteness": ("def" if i > 0 and tokens[i - 1].lower() == "the"
                                     else "indef"),
                })
                continue
            if clean[:1].isupper() and i > 0 and lw not in _EN_STOP and len(clean) > 1:
                entities.append({"surface": clean, "lang": "en", "type": "unknown",
                                 "gender": "unknown", "number": "unknown",
                                 "pos": self._cur_pos, "definiteness": "unknown"})
        return entities, references

    # ------------------------------------------------------------------
    def _verb_subject_features(self, verb: str) -> Dict[str, str]:
        """خصائص الفاعل المحذوف من صرف الفعل الماضي."""
        if verb.endswith("وا"):
            return {"person": "3", "gender": "m", "number": "pl"}
        if verb.endswith("ا") and len(verb) > 3:
            return {"person": "3", "gender": "unknown", "number": "du"}
        if verb.endswith("نا"):
            return {"person": "1", "gender": "unknown", "number": "pl"}
        if verb.endswith("تما"):
            return {"person": "2", "gender": "unknown", "number": "du"}
        if verb.endswith("تن"):
            return {"person": "2", "gender": "f", "number": "pl"}
        if verb.endswith("ت"):
            return {"person": "unknown", "gender": "unknown", "number": "sg"}
        return {"person": "3", "gender": "m", "number": "sg"}

    # ------------------------------------------------------------------
    def _classify(self, text: str, tokens: List[str]) -> Tuple[str, str]:
        t = (text or "").strip()
        norm_tokens = [_sc.norm_for_match(x) for x in tokens]
        if not norm_tokens:
            return "unknown", "unknown"
        first = norm_tokens[0]
        firsts = set(norm_tokens[:3])

        if "؟" in t or "?" in t or first in _N_QUESTION_AR:
            return "question", "question"
        if tokens[0].lower().strip(".,!?") in _QUESTION_EN - {"is", "are", "do", "does", "did", "can"}:
            return "question", "question"
        # طلب استزادة: «اشرح أكثر/المزيد/أكمل» — قبل الطلب العام
        if first in _N_MORE or t in _N_MORE:
            return "request_more", "request"
        if norm_tokens[-1] in _N_MORE and (first in _N_REQUEST_AR or first in _N_WISH_AR):
            return "request_more", "request"
        if first in _N_REQUEST_AR:
            return "request", "request"
        cap_first = tokens[0].strip(".,!?").lower()
        if cap_first in _REQUEST_EN and cap_first not in {"please"}:
            return "request", "request"
        if any(x in _N_WISH_AR for x in firsts):
            return "request", "request"
        if first in _N_GREETING and len(tokens) <= 4:
            return "greeting", "greeting"
        if first in _N_THANKS and len(tokens) <= 4:
            return "thanks", "thanks"
        if first in _N_CONFIRM and len(tokens) <= 3:
            return "confirmation", "confirmation"
        return "assertion", "assertion"

    # ------------------------------------------------------------------
    def _discourse(self, tokens: List[str]) -> List[Dict[str, Any]]:
        if not tokens:
            return []
        first = tokens[0]
        base = first[1:] if first[:1] in ("و", "ف") and len(first) > 3 else first
        nb = _sc.norm_for_match(base)
        for words, rel in _DISCOURSE_AR:
            if base in words or nb in _normset(words):
                return [{"type": rel, "target": "prev"}]
        lw = base.lower().strip(".,!?")
        for words, rel in _DISCOURSE_EN:
            if lw in words:
                return [{"type": rel, "target": "prev"}]
        if first.startswith("و"):
            return [{"type": "continuation", "target": "prev"}]
        return []

    # ------------------------------------------------------------------
    def _ref(self, mention: str, rtype: str, feat: Dict[str, str]) -> Dict[str, Any]:
        return {
            "mention": mention,
            "type": rtype,
            "person": feat.get("person", "unknown"),
            "gender": feat.get("gender", "unknown"),
            "number": feat.get("number", "unknown"),
            # R-838: موقع الإحالة — الإحالة لا تشير إلا لما قبلها (اتجاه الإحالة)
            "pos": getattr(self, "_cur_pos", 0),
            "candidate_entity_ids": [],
            "confidence": 0.0,
        }


def analyze(text: str, utterance_id: str = "utt_0") -> Dict[str, Any]:
    """واجهة مباشرة: نص أصلي => إطار دلالي (عقد JSON الإلزامي)."""
    return SemanticAnalyzer().analyze(text, utterance_id)
