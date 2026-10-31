"""R-824: معجم بصري عربي⇒إنجليزي مدمج — آخر احتياط لترجمة أوصاف الصور بلا أي خدمة خارجية.

السبب (لوحظ حيًا): وصف عربي غير مترجم أُرسل لمولد الصور فأنتج صورة لا علاقة لها بالطلب
(قطة في حديقة ⇒ صورة فتاة). مولدات الصور تفهم الإنجليزية؛ ومزودات الترجمة المجانية قد تُحجب
أو تنفد حصتها. هذا المعجم يغطي مفردات الوصف البصري الشائعة (كائنات، أماكن، ألوان، أزمنة،
أنماط) مع تجريد صرفي خفيف (ال/و/ب/ل/ك، ة/ات/ون/ين/ها) — ترجمة كلمة بكلمة تكفي للمولدات.
translate(text) يعيد (النص الإنجليزي، نسبة التغطية) — والمستدعي يقرر بالحد الأدنى للتغطية.
"""
from __future__ import annotations

import re
from typing import Dict, Tuple

LEX: Dict[str, str] = {
    # كائنات حية
    "فوائد": "benefits", "فائدة": "benefit", "قمة": "summit", "القمة": "summit",  # R-824
    "قط": "cat", "قطة": "cat", "قطط": "cats", "كلب": "dog", "كلاب": "dogs", "حصان": "horse", "خيول": "horses",
    "خيل": "horses", "جمل": "camel", "جمال": "camels", "أسد": "lion", "اسد": "lion", "نمر": "tiger",
    "فيل": "elephant", "طائر": "bird", "طير": "bird", "طيور": "birds", "صقر": "falcon", "نسر": "eagle",
    "حمامة": "dove", "سمك": "fish", "سمكة": "fish", "أسماك": "fish", "حوت": "whale", "دلفين": "dolphin",
    "فراشة": "butterfly", "نحلة": "bee", "غزال": "gazelle", "ذئب": "wolf", "ثعلب": "fox", "دب": "bear",
    "أرنب": "rabbit", "ارنب": "rabbit", "بقرة": "cow", "خروف": "sheep", "ماعز": "goat", "دجاجة": "chicken",
    "تنين": "dragon", "روبوت": "robot", "رجل": "man", "رجال": "men", "امرأة": "woman", "امراة": "woman",
    "نساء": "women", "طفل": "child", "أطفال": "children", "اطفال": "children", "ولد": "boy", "بنت": "girl",
    "فتاة": "girl", "شاب": "young man", "شخص": "person", "ناس": "people", "عائلة": "family", "رياضي": "athlete",
    "لاعب": "player", "طبيب": "doctor", "مهندس": "engineer", "معلم": "teacher", "طالب": "student",
    "فارس": "knight", "ملك": "king", "ملكة": "queen", "أميرة": "princess", "اميرة": "princess",
    "شجرة": "tree", "أشجار": "trees", "اشجار": "trees", "نخلة": "palm tree", "نخيل": "palm trees",
    "زهرة": "flower", "زهور": "flowers", "ورد": "roses", "وردة": "rose", "عشب": "grass", "غابة": "forest",
    # أماكن وطبيعة
    "حديقة": "garden", "بستان": "orchard", "منزل": "house", "بيت": "house", "قصر": "palace", "قلعة": "castle",
    "مسجد": "mosque", "مدينة": "city", "مدن": "cities", "قرية": "village", "شارع": "street", "سوق": "market",
    "مكتب": "office", "مطبخ": "kitchen", "غرفة": "room", "مطعم": "restaurant", "مقهى": "cafe", "مدرسة": "school",
    "مستشفى": "hospital", "ملعب": "stadium", "صالة": "hall", "نادي": "gym", "جسر": "bridge", "برج": "tower",
    "أبراج": "towers", "ناطحات": "skyscrapers", "ناطحة": "skyscraper", "صحراء": "desert", "كثبان": "dunes",
    "رمال": "sand", "رمل": "sand", "جبل": "mountain", "جبال": "mountains", "بحر": "sea", "بحار": "seas",
    "محيط": "ocean", "شاطئ": "beach", "نهر": "river", "بحيرة": "lake", "شلال": "waterfall", "واحة": "oasis",
    "وادي": "valley", "جزيرة": "island", "سماء": "sky", "سحاب": "clouds", "سحب": "clouds", "غيوم": "clouds",
    "شمس": "sun", "قمر": "moon", "نجوم": "stars", "نجمة": "star", "فضاء": "space", "كوكب": "planet",
    "مجرة": "galaxy", "ثلج": "snow", "ثلوج": "snow", "مطر": "rain", "عاصفة": "storm", "برق": "lightning",
    "ضباب": "fog", "نار": "fire", "ماء": "water", "موج": "waves", "أمواج": "waves", "امواج": "waves",
    "طريق": "road", "مزرعة": "farm", "حقل": "field", "كهف": "cave", "بركان": "volcano", "مكة": "Mecca",
    "جدة": "Jeddah", "الرياض": "Riyadh", "رياض": "Riyadh", "دبي": "Dubai", "القاهرة": "Cairo", "باريس": "Paris",
    "لندن": "London", "طوكيو": "Tokyo", "السعودية": "Saudi Arabia", "سعودية": "Saudi",
    # أشياء
    "سيارة": "car", "سيارات": "cars", "طائرة": "airplane", "سفينة": "ship", "قارب": "boat", "قطار": "train",
    "دراجة": "bicycle", "كتاب": "book", "كتب": "books", "قلم": "pen", "حاسوب": "computer", "كمبيوتر": "computer",
    "هاتف": "phone", "جوال": "smartphone", "ساعة": "clock", "كرسي": "chair", "طاولة": "table", "مصباح": "lamp",
    "فانوس": "lantern", "قهوة": "coffee", "شاي": "tea", "تمر": "dates", "طعام": "food", "أكل": "food",
    "اكل": "food", "وجبة": "meal", "طبق": "plate", "صحن": "plate", "دجاج": "chicken", "لحم": "meat",
    "خضار": "vegetables", "خضروات": "vegetables", "فواكه": "fruits", "فاكهة": "fruit", "تفاح": "apples",
    "خبز": "bread", "كعكة": "cake", "حلويات": "desserts", "سلطة": "salad", "رز": "rice", "أرز": "rice",
    "صحي": "healthy", "صحية": "healthy", "كرة": "ball", "قدم": "football", "أثقال": "weights", "اثقال": "weights",
    "تمارين": "exercise", "رياضة": "sport", "الرياضة": "sports", "لياقة": "fitness", "ذهب": "gold",
    "تاج": "crown", "سيف": "sword", "علم": "flag", "خريطة": "map", "هدية": "gift", "بالون": "balloon",
    "شمعة": "candle", "مفتاح": "key", "باب": "door", "نافذة": "window", "شعار": "logo", "شركة": "company",
    "متجر": "store", "تقنية": "technology", "التقنية": "technology", "ذكاء": "intelligence", "اصطناعي": "artificial",
    # ألوان وصفات
    "أحمر": "red", "احمر": "red", "حمراء": "red", "أزرق": "blue", "ازرق": "blue", "زرقاء": "blue",
    "أخضر": "green", "اخضر": "green", "خضراء": "green", "أصفر": "yellow", "اصفر": "yellow", "صفراء": "yellow",
    "أسود": "black", "اسود": "black", "سوداء": "black", "أبيض": "white", "ابيض": "white", "بيضاء": "white",
    "برتقالي": "orange", "بنفسجي": "purple", "وردي": "pink", "ذهبي": "golden", "ذهبية": "golden",
    "فضي": "silver", "بني": "brown", "رمادي": "gray", "كبير": "big", "كبيرة": "big", "صغير": "small",
    "صغيرة": "small", "جميل": "beautiful", "جميلة": "beautiful", "قديم": "ancient", "قديمة": "ancient",
    "حديث": "modern", "حديثة": "modern", "مستقبلي": "futuristic", "مستقبلية": "futuristic", "سعيد": "happy",
    "سعيدة": "happy", "حزين": "sad", "مضيء": "glowing", "مضيئة": "glowing", "مغطاة": "covered", "مغطى": "covered",
    "هادئ": "calm", "هادئة": "calm", "ضخم": "giant", "ضخمة": "giant", "طائر": "flying", "يطير": "flying",
    "تطير": "flying", "يلعب": "playing", "تلعب": "playing", "يلعبون": "playing", "يجري": "running",
    "تجري": "running", "يركض": "running", "تركض": "running", "يأكل": "eating", "تأكل": "eating",
    "يقرأ": "reading", "تقرأ": "reading", "يمشي": "walking", "تمشي": "walking", "يسبح": "swimming",
    "تسبح": "swimming", "نائم": "sleeping", "نائمة": "sleeping", "تنام": "sleeping", "يجلس": "sitting",
    "تجلس": "sitting", "جالس": "sitting", "واقف": "standing", "يبتسم": "smiling", "تبتسم": "smiling",
    "يحمل": "holding", "تحمل": "holding", "يرفع": "lifting", "يتمرن": "working out",
    # زمن وإضاءة وأنماط
    "الغروب": "sunset", "غروب": "sunset", "الشروق": "sunrise", "شروق": "sunrise", "ليل": "night",
    "الليل": "night", "ليلية": "at night", "ليلي": "at night", "ليلا": "at night", "نهار": "daytime",
    "صباح": "morning", "فجر": "dawn", "شتاء": "winter", "صيف": "summer", "ربيع": "spring", "خريف": "autumn",
    "رمضان": "Ramadan", "عيد": "Eid", "كرتون": "cartoon", "كرتوني": "cartoon style", "كرتونية": "cartoon style",
    "واقعي": "photorealistic", "واقعية": "photorealistic", "رسم": "drawing", "زيتي": "oil painting",
    "مائي": "watercolor", "مائية": "watercolor", "ثلاثي": "3D", "ثلاثية": "3D", "أبعاد": "dimensional",
    "انمي": "anime", "أنمي": "anime", "بكسل": "pixel art", "سينمائي": "cinematic", "سينمائية": "cinematic",
    "بسيط": "minimalist", "بسيطة": "minimalist", "فاخر": "luxury", "فاخرة": "luxury", "إسلامي": "islamic",
    "اسلامي": "islamic", "إسلامية": "islamic", "اسلامية": "islamic", "عربي": "arabic", "عربية": "arabic",
    "تقليدي": "traditional", "تقليدية": "traditional", "خلفية": "background", "الخلفية": "background",
    "أضف": "add", "اضف": "add", "مع": "with", "في": "in", "على": "on", "تحت": "under", "فوق": "above",
    "بجانب": "next to", "أمام": "in front of", "امام": "in front of", "خلف": "behind", "بين": "between",
    "عند": "at", "و": "and", "من": "of", "بدون": "without", "كثير": "many", "كثيرة": "many",
}
_DROP = {"لي", "لنا", "صورة", "صوره", "اجعلها", "اجعله", "خليها", "خليه", "اريد", "أريد", "ابي", "أبي",
         "ال", "هذه", "هذا", "التي", "الذي", "جدا", "جداً", "تكون", "يكون", "فيها", "فيه", "بها", "به",
         "ها", "أن", "ان", "بشكل", "بأسلوب", "باسلوب", "أسلوب", "اسلوب", "نمط", "ستايل"}
_PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال", "و", "ب", "ل", "ك", "ف")
_SUFFIXES = ("ها", "هم", "ات", "ون", "ين", "ية", "ي", "ة", "ه")


def _lookup(w: str):
    if w in LEX:
        return LEX[w]
    for p in _PREFIXES:
        if w.startswith(p) and len(w) - len(p) >= 2:
            b = w[len(p):]
            if b in LEX:
                return LEX[b]
            for s in _SUFFIXES:
                if b.endswith(s) and len(b) - len(s) >= 2 and b[: -len(s)] in LEX:
                    return LEX[b[: -len(s)]]
                if b.endswith(s) and len(b) - len(s) >= 2 and b[: -len(s)] + "ة" in LEX:
                    return LEX[b[: -len(s)] + "ة"]
    for s in _SUFFIXES:
        if w.endswith(s) and len(w) - len(s) >= 2:
            b = w[: -len(s)]
            if b in LEX:
                return LEX[b]
            if b + "ة" in LEX:
                return LEX[b + "ة"]
    return None


def translate(text: str) -> Tuple[str, float]:
    """(English, coverage 0..1) — كلمة بكلمة؛ الكلمات المجهولة تُسقط وتخفض التغطية."""
    words = [w for w in re.findall(r"[\u0600-\u06FF]+|[A-Za-z0-9]+", str(text or ""))]
    out, known, total = [], 0, 0
    for w in words:
        if w in _DROP:
            continue
        if re.match(r"[A-Za-z0-9]+$", w):
            out.append(w)
            known += 1
            total += 1
            continue
        total += 1
        t = _lookup(w)
        if t:
            known += 1
            if not (out and out[-1] == t):
                out.append(t)
    # «and/of/in» المعلقة في الأطراف تُحذف
    while out and out[0] in ("and", "of", "in", "with", "on", "at"):
        out.pop(0)
    while out and out[-1] in ("and", "of", "in", "with", "on", "at"):
        out.pop()
    return " ".join(out), (known / total if total else 0.0)
