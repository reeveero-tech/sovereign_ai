"""R-838: أدوات نصوص متعددة اللغات — توحيد الترميز دون طمس الخصائص اللغوية.

مبدأ حاكم: اللغة واجهة والتمثيل الدلالي هو الأساس. كل توحيد هنا يحافظ على
الخصائص المورفولوجية (ال تعريف، تاء التأنيث، علامات الجمع والمثنى، الضمائر
المتصلة) لأن المحلل الدلالي يعتمد عليها في الإحالة وتتبع الكيانات.

قرارات التصميم:
- تطبيع العربية يوحّد الألف (أ/إ/آ←ا) وهمزات القطع لأغراض المطابقة فقط، ولا يُطبَّق
  على النص الأصلي أبدًا؛ النص الأصلي يُحفظ كما ورد في كل إطار دلالي.
- التقسيم إلى كلمات يحترم علامات الترقيم العربية (،؛؟) واللاتينية.
- لا اعتماد على أي خدمة خارجية — كله حتمي قابل للاختبار.
"""
from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple

# نطاقات يونيكود (كتابات) — كشف مستوى الرمز لا الجملة
SCRIPT_RANGES: Tuple[Tuple[str, int, int], ...] = (
    ("latin", 0x0000, 0x024F),      # أساسي + امتدادات لاتينية
    ("greek", 0x0370, 0x03FF),
    ("cyrillic", 0x0400, 0x04FF),
    ("hebrew", 0x0590, 0x05FF),
    ("arabic", 0x0600, 0x06FF),
    ("syriac", 0x0700, 0x074F),
    ("thaana", 0x0780, 0x07BF),
    ("nko", 0x07C0, 0x07FF),
    ("devanagari", 0x0900, 0x097F),
    ("bengali", 0x0980, 0x09FF),
    ("gurmukhi", 0x0A00, 0x0A7F),
    ("gujarati", 0x0A80, 0x0AFF),
    ("oriya", 0x0B00, 0x0B7F),
    ("tamil", 0x0B80, 0x0BFF),
    ("telugu", 0x0C00, 0x0C7F),
    ("kannada", 0x0C80, 0x0CFF),
    ("malayalam", 0x0D00, 0x0D7F),
    ("sinhala", 0x0D80, 0x0DFF),
    ("thai", 0x0E00, 0x0E7F),
    ("lao", 0x0E80, 0x0EFF),
    ("tibetan", 0x0F00, 0x0FFF),
    ("myanmar", 0x1000, 0x109F),
    ("georgian", 0x10A0, 0x10FF),
    ("hangul", 0x1100, 0x11FF),
    ("ethiopic", 0x1200, 0x137F),
    ("cherokee", 0x13A0, 0x13FF),
    ("cjk", 0x2E80, 0x9FFF),       # CJK + كانا ضمن النطاق
    ("cjk_ext", 0xF900, 0xFAFF),
)

# حروف فاراسية/أردية مميزة داخل الكتابة العربية
_FA_UR_CHARS = set("پچژگٹڈڑںھےۓۃ")

_AR_WS = re.compile(r"\s+")
# فاصلة عربية وفاصلة منقوطة وعلامة استفهام عربية وشرطة
_SPLIT_RE = re.compile(r"([،؛؟!.:()\[\]{}\"'«»\n]+)")

# أرقام عربية-هندية ٠-٩
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def script_of_char(ch: str) -> str:
    """يعيد اسم الكتابة (script) لحرف واحد — أو 'other'."""
    cp = ord(ch)
    for name, lo, hi in SCRIPT_RANGES:
        if lo <= cp <= hi:
            return name
    return "other"


def dominant_script(text: str) -> str:
    """الكتابة الغالبة في النص (تصويت حروف الكلمات لا الرموز)."""
    votes: dict[str, int] = {}
    for ch in text:
        if not ch.isalpha():
            continue
        s = script_of_char(ch)
        votes[s] = votes.get(s, 0) + 1
    return max(votes, key=votes.get) if votes else "latin"


def tokenize(text: str) -> List[str]:
    """تقسيم إلى كلمات مع الحفاظ على الكلمة العربية كوحدة (ضمائرها المتصلة داخلها)."""
    parts = _SPLIT_RE.split(text or "")
    out: List[str] = []
    for p in parts:
        for w in _AR_WS.split(p):
            if w:
                out.append(w)
    return out


def norm_for_match(s: str) -> str:
    """تطبيع للمطابقة فقط (لا يُستخدم للنص المعروض أبدًا).

    - إزالة التشكيل والتطويل.
    - توحيد الهمزات والألف والياء والنقاط العربية لغرض المقارنة.
    - توحيد الأرقام العربية-الهندية.
    """
    s = unicodedata.normalize("NFKC", s or "")
    s = s.translate(_AR_DIGITS)
    s = re.sub(r"[\u064B-\u0652\u0640]", "", s)          # تشكيل + تطويل
    repl = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ئ": "ي",
            "ؤ": "و", "ة": "ه", "ـ": ""}
    for a, b in repl.items():
        s = s.replace(a, b)
    s = s.lower()
    return re.sub(r"\s+", " ", s).strip()


def strip_ar_prefixes(w: str) -> Tuple[str, List[str]]:
    """يفصل سوابق عربية شائعة عن جذر الكلمة: و (عطف)، ف، ب/ل/ك (جر)، ال (تعريف).

    يعيد (الجذر_المرشح، السوابق_المزالة). لا يُطبَّق إلا على كلمات عربية
    ويعامل «ال» التعريف بحذر (لا يفصل أفعالًا مثل «الآخر» مبدئيًا — الفحص
    الدلالي لاحقًا هو من يقرر).
    """
    prefixes: List[str] = []
    while True:
        if w.startswith("ال") and len(w) > 4:
            prefixes.append("ال")
            w = w[2:]
        elif w[:1] in ("و", "ف", "ب", "ل", "ك") and len(w) > 3:
            prefixes.append(w[0])
            w = w[1:]
        else:
            break
    return w, prefixes


def has_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def has_latin(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]", text or ""))


def is_mixed_script_token(w: str) -> bool:
    """رمز واحد يجمع كتابتين — مثل «SMالنظام» أو «problemه» (تبديل شيفرة داخل كلمة)."""
    scripts = {script_of_char(c) for c in w if c.isalpha()}
    return len(scripts) > 1
