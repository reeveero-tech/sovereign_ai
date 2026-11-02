"""R-838: كشف اللغة على مستوى المقطع/الرمز وتقسيم تبديل الشيفرة.

المطلوب (المعمارية الإلزامية 4.1): كشف اللغة على مستوى المقطع لا الجملة،
كشف النص المختلط وتقسيمه إلى مقاطع لغوية، وإخراج
{segments, languages, script, confidence}.

المنهج حتمي بلا خدمات خارجية:
1. الكتابة (script) من نطاقات يونيكود — قرار أولي فوري.
2. داخل الكتابة اللاتينية: تمييز اللغات بكلمات وظيفية شائعة (en/fr/es/de/tr/it/...).
3. داخل الكتابة العربية: تمييز العربية عن الفارسية/الأردية بالحروف المميزة.
4. الثقة = نسبة الرموز المصنفة بثقة على إجمالي الرموز اللغوية.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from . import scripts as _sc

# كلمات وظيفية شائعة لتمييز اللغات اللاتينية (كلمة => لغة)
_LATIN_FUNCWORDS: Dict[str, str] = {
    # الإنجليزية
    "the": "en", "is": "en", "are": "en", "was": "en", "you": "en", "and": "en",
    "what": "en", "how": "en", "about": "en", "it": "en", "this": "en", "that": "en",
    "please": "en", "me": "en", "my": "en", "can": "en", "do": "en", "did": "en",
    "does": "en", "tell": "en", "with": "en", "for": "en", "of": "en", "to": "en",
    "not": "en", "i": "en", "we": "en", "they": "en", "he": "en", "she": "en",
    # الفرنسية
    "le": "fr", "la": "fr", "les": "fr", "des": "fr", "est": "fr", "et": "fr",
    "que": "fr", "qui": "fr", "dans": "fr", "pour": "fr", "avec": "fr", "je": "fr",
    "tu": "fr", "nous": "fr", "vous": "fr", "mais": "fr", "comment": "fr", "quoi": "fr",
    # الإسبانية
    "el": "es", "los": "es", "las": "es", "es": "es", "y": "es", "que": "es",
    "de": "es", "en": "es", "un": "es", "una": "es", "por": "es", "con": "es",
    "para": "es", "pero": "es", "cómo": "es", "qué": "es", "yo": "es", "tú": "es",
    "hola": "es", "gracias": "es", "está": "es", "estás": "es", "muy": "es",
    # الألمانية
    "der": "de", "die": "de", "das": "de", "den": "de", "und": "de", "ist": "de",
    "nicht": "de", "mit": "de", "für": "de", "ich": "de", "du": "de", "wir": "de",
    "aber": "de", "wie": "de", "was": "de", "sind": "de", "hat": "de",
    # التركية
    "ve": "tr", "bir": "tr", "bu": "tr", "için": "tr", "ile": "tr", "değil": "tr",
    "ama": "tr", "nasıl": "tr", "ne": "tr", "ben": "tr", "sen": "tr", "biz": "tr",
    "var": "tr", "mi": "tr", "mı": "tr",
    # الإيطالية
    "il": "it", "lo": "it", "gli": "it", "e": "it", "è": "it", "non": "it",
    "con": "it", "per": "it", "ma": "it", "come": "it", "cosa": "it", "io": "it",
    # البرتغالية
    "o": "pt", "os": "pt", "as": "pt", "um": "pt", "não": "pt", "com": "pt",
    "para": "pt", "mas": "pt", "como": "pt", "que": "pt", "eu": "pt",
    # الإندونيسية
    "dan": "id", "yang": "id", "tidak": "id", "dengan": "id", "untuk": "id",
    "ini": "id", "itu": "id", "adalah": "id", "apa": "id", "bagaimana": "id",
}

# كلمات عربية وظيفية قصيرة تُقفل تصنيف المقطع العربي (تعزيز الثقة)
_AR_FUNCWORDS = {
    "في", "من", "إلى", "على", "هذا", "هذه", "ذلك", "تلك", "ما", "ماذا", "من",
    "هل", "كيف", "لماذا", "أين", "متى", "كم", "الذي", "التي", "و", "ثم", "أو",
    "هو", "هي", "هم", "هن", "أنا", "نحن", "أنت", "أنتم", "كان", "يكون", "ليس",
    "عن", "مع", "كل", "بعد", "قبل", "عند", "بين", "بدون", "بلا", "قد", "لا",
}


@dataclass
class Segment:
    """مقطع لغوي متجانس داخل نص قد يكون مختلطًا."""
    text: str
    lang: str
    start: int = 0
    end: int = 0
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {"text": self.text, "lang": self.lang,
                "confidence": round(self.confidence, 3)}


@dataclass
class DetectionResult:
    segments: List[Segment] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    script: str = "latin"
    confidence: float = 0.0
    mixed: bool = False

    def to_dict(self) -> dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "languages": self.languages,
            "script": self.script,
            "confidence": round(self.confidence, 3),
            "mixed": self.mixed,
        }


def _classify_latin_token(w: str) -> str:
    """تصنيف كلمة لاتينية عبر الكلمات الوظيفية ثم لواحق مميزة."""
    lw = w.lower().strip(".,!?;:()[]\"'¿¡«»")
    if lw in _LATIN_FUNCWORDS:
        return _LATIN_FUNCWORDS[lw]
    # لواحق لغوية مميزة
    if lw.endswith("zione") or lw.endswith("amente"):
        return "it"
    if lw.endswith("ção") or lw.endswith("ções"):
        return "pt"
    if lw.endswith("ción") or lw.endswith("mente") and lw.endswith("mente"):
        return "es"
    if lw.endswith("ung") or lw.endswith("keit") or lw.endswith("schaften"):
        return "de"
    if lw.endswith("lık") or lw.endswith("lik"):
        return "tr"
    if lw.endswith("ing") or lw.endswith("tion") or lw.endswith("ness"):
        return "en"
    if lw.endswith("ment") or lw.endswith("tion"):
        return "fr"
    return "unknown"


def _classify_arabic_token(w: str) -> str:
    """عربية أم فارسية/أردية — بحروف مميزة ثم كلمات وظيفية."""
    for ch in w:
        if ch in _sc._FA_UR_CHARS:
            return "fa" if ch in "پچژگ" else "ur"
    base = w[1:] if w.startswith("و") and len(w) > 3 else w
    if base in _AR_FUNCWORDS:
        return "ar"
    return "ar"


def _lang_name_for_script(script: str) -> str:
    return {"cjk": "zh", "cyrillic": "ru", "devanagari": "hi", "greek": "el",
            "hebrew": "he", "thai": "th", "hangul": "ko", "arabic": "ar"}.get(script, script)


def detect(text: str) -> DetectionResult:
    """كشف اللغة وتقسيم تبديل الشيفرة — النقطة الوحيدة التي تقسم النص لمقاطع.

    القاعدة: الجملة المختلطة مدخل طبيعي لا خطأ؛ تُقسَّم إلى مقاطع وتُحلَّل
    دلاليًا كلها في إطار واحد موحد (بروتوكول تبديل الشيفرة 5.3).
    """
    result = DetectionResult()
    if not (text or "").strip():
        return result
    result.script = _sc.dominant_script(text)

    # تقسيم إلى رموز مع مواضعها (كلمة، بداية، نهاية)
    spans: List[tuple] = []
    for m in re.finditer(r"\S+", text or ""):
        spans.append((m.group(0), m.start(), m.end()))

    cur_lang: str = ""
    cur_start: int = -1
    cur_end: int = -1
    lang_votes: Dict[str, int] = {}
    classified_tokens = 0
    total_tokens = 0

    def flush():
        nonlocal cur_lang, cur_start, cur_end
        if cur_lang and cur_start >= 0:
            seg_text = text[cur_start:cur_end].strip()
            if seg_text:
                conf = lang_votes.get(cur_lang, 0) / max(1, sum(lang_votes.values()))
                result.segments.append(Segment(seg_text, cur_lang, cur_start, cur_end,
                                               min(1.0, 0.4 + 0.6 * conf)))
        cur_lang = ""
        cur_start = -1
        cur_end = -1

    for w, s, e in spans:
        total_tokens += 1
        # رمز مختلط الكتابة داخل الكلمة («الـPR») ⇒ يُقسَّم عند حدود الكتابة
        if _sc.is_mixed_script_token(w):
            flush()   # الرمز المختلط حدٌّ بين مقطعين — لا يُبتلع في المقطع السابق
            runs: List[tuple] = []   # (نص_الجزء، كتابته)
            buf, buf_script = "", ""
            for ch in w:
                sc_ = _sc.script_of_char(ch) if ch.isalpha() else buf_script
                if buf and sc_ != buf_script:
                    runs.append((buf, buf_script))
                    buf, buf_script = "", sc_
                if ch.isalpha() or buf:
                    buf += ch
                    if ch.isalpha():
                        buf_script = sc_
            if buf:
                runs.append((buf, buf_script))
            offset = s
            for run_text, run_script in runs:
                if run_text.strip():
                    if run_script == "arabic":
                        run_lang = _classify_arabic_token(run_text)
                    elif run_script == "latin":
                        run_lang = _classify_latin_token(run_text) or "en"
                        if run_lang == "unknown":
                            run_lang = "en"
                    else:
                        run_lang = _lang_name_for_script(run_script)
                    result.segments.append(Segment(run_text, run_lang, offset,
                                                   offset + len(run_text), 0.9))
                    lang_votes[run_lang] = lang_votes.get(run_lang, 0) + 1
                offset += len(run_text)
            classified_tokens += 1
            continue
        word_scripts = {c for c in (_sc.script_of_char(ch) for ch in w) if c != "other"}
        lang = ""
        if word_scripts & {"arabic"}:
            lang = _classify_arabic_token(w)
        elif word_scripts & {"latin"}:
            lang = _classify_latin_token(w)
        elif word_scripts:
            # كتابة واحدة غير عربية/لاتينية: اللغة من الكتابة
            lang = _lang_name_for_script(sorted(word_scripts)[0])
        if not lang:
            lang = ""
        if lang and lang != "unknown":
            lang_votes[lang] = lang_votes.get(lang, 0) + 1
            classified_tokens += 1
        else:
            # رمز لاتيني غير مصنف ⇒ يرث لغة المقطع اللاتيني الجاري (will/report)
            if cur_lang and cur_lang not in ("ar",):
                lang = cur_lang
                lang_votes[lang] = lang_votes.get(lang, 0) + 1
                classified_tokens += 1
        # مقاطع متجاورة فقط (فواصل/فراغات لا تكسر المقطع إلا إذا بدلت اللغة)
        if lang != cur_lang:
            flush()
            if lang:
                cur_start, cur_end = s, e
                cur_lang = lang
        else:
            cur_end = e
    flush()

    # مواضع المقاطع تُرتب حسب النص
    result.segments.sort(key=lambda x: x.start)
    result.languages = sorted(lang_votes, key=lang_votes.get, reverse=True)
    result.confidence = round(classified_tokens / max(1, total_tokens), 3)
    result.mixed = len(result.languages) > 1
    if not result.languages and result.script:
        result.languages = [_lang_name_for_script(result.script)]
    return result


def dominant_language(text: str) -> str:
    """اللغة الغالبة — تُستخدم لمطابقة لغة الرد مع لغة المستخدم."""
    d = detect(text)
    return d.languages[0] if d.languages else "en"
