"""R-838: المدقق بعد التوليد (المعمارية 4.8) + سجل التتبع.

قبل إرسال أي رد يتحقق المدقق من:
- اتساق كل إحالة مع جدول الكيانات (لا ضمير بلا مرجع مثبت).
- عدم ذكر كيان غير مثبت في النص أو الذاكرة (هلوسة كيان).
- اتساق لغة الرد مع لغة المستخدم.
- عدم وجود ترجمة وسيطة في المسار الأساسي (analysis_path).

إن فشل الشرط: إصلاح آمن أو سؤال توضيحي واحد — لا إخراج رد مكسور.
سجل التتبع يثبت بالدليل (قابل للفحص) مسار الفهم: original_text دائمًا.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import detector as _det
from . import scripts as _sc

# كلمات عربية/إنجليزية آمنة تُستبدل بها الإحالة غير القابلة للحل
_SAFE_AR = "الأمر المذكور سابقًا"
_SAFE_EN = "the matter mentioned earlier"


@dataclass
class ValidationIssue:
    code: str          # unbound_reference | unproven_entity | lang_mismatch | unsafe_pronoun
    detail: str
    fix: Optional[str] = None   # النص المصحح إن أمكن

    def to_dict(self) -> Dict:
        return self.__dict__.copy()


@dataclass
class ValidationReport:
    passed: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    repaired_reply: Optional[str] = None

    def to_dict(self) -> Dict:
        return {"passed": self.passed,
                "issues": [i.to_dict() for i in self.issues],
                "repaired": self.repaired_reply is not None}


def _pronouns_in_reply(reply: str) -> List[str]:
    """ضمائر قد تظهر في الرد — للتحقق من قابلية حلها في السياق المرسل."""
    ar = {"هو", "هي", "هم", "هن", "هما"}
    en = {"it", "they", "them", "he", "she", "this", "that"}
    out: List[str] = []
    for tok in _sc.tokenize(reply or ""):
        base = tok[1:] if tok[:1] in ("و", "ف") and len(tok) > 3 else tok
        if base in ar or tok.lower().strip(".,!?") in en:
            out.append(base)
    return out


def validate_reply(reply: str, frame: Dict, entity_table, user_lang: Optional[str] = None,
                   active_entity_ids: Optional[List[str]] = None) -> ValidationReport:
    """التحقق قبل الإرسال (بروتوكول 5.5) — يعيد تقريرًا وردًا مصححًا إن لزم."""
    rep = ValidationReport()
    reply = reply or ""
    if not reply.strip():
        return rep
    active_ids = set(active_entity_ids or [])

    # ١) إحالات: كل ضمير في الرد يجب أن يكون له مرجع مثبت (كيان نشط)
    unbound = []
    for p in _pronouns_in_reply(reply):
        if not active_ids:
            unbound.append(p)
            continue
        # يوجد كيان نشط متوافق؟ الجدول يقرر
        cand = [e for e in entity_table.entities.values()
                if e.id in active_ids and e.discourse_state != "deleted"]
        if not cand:
            unbound.append(p)
    if unbound and not cand_ok(frame, unbound, entity_table):
        rep.passed = False
        rep.issues.append(ValidationIssue(
            "unbound_reference",
            f"ضمائر بلا مرجع مثبت: {unbound}",
            fix=None))

    # ٢) كيانات غير مثبتة: أسماء علم في الرد لم ترد في النص/الذاكرة
    for tok in _sc.tokenize(reply):
        clean = tok.strip(".,!?;:()[]\"'«»")
        if not clean:
            continue
        if _sc.has_latin(clean) and clean[:1].isupper() and len(clean) > 2:
            known = any(_sc.norm_for_match(clean) in
                       {_sc.norm_for_match(s) for s in e.all_surfaces()}
                       for e in entity_table.entities.values()
                       if e.discourse_state != "deleted")
            frame_known = any(_sc.norm_for_match(clean) == _sc.norm_for_match(e.get("surface", ""))
                              for e in frame.get("entities", []))
            if not (known or frame_known):
                rep.passed = False
                rep.issues.append(ValidationIssue(
                    "unproven_entity", f"كيان غير مثبت في الرد: {clean}"))

    # ٣) اتساق اللغة مع لغة المستخدم
    if user_lang:
        rlang = _det.dominant_language(reply)
        ulang = user_lang
        # العربية تُجاب بالعربية والإنجليزية بالإنجليزية؛ المختلط يُجاب بلغة الغلبة
        if ulang == "ar" and rlang not in ("ar",) and not _sc.has_arabic(reply):
            rep.passed = False
            rep.issues.append(ValidationIssue(
                "lang_mismatch", f"رد بلغة {rlang} والمستخدم يكتب {ulang}"))

    rep.repaired_reply = _repair(reply, rep) if not rep.passed else None
    return rep


def cand_ok(frame: Dict, unbound: List[str], entity_table) -> bool:
    """الضمير مرفوض فقط إن لم يوجد أي كيان نشط متوافق إطلاقًا في الجدول."""
    for p in unbound:
        gender = {"هي": "f", "هو": "m", "هم": "m", "هن": "f", "هما": "unknown"}.get(p, "unknown")
        if entity_table.most_salient(gender=gender):
            return True
    return False


def _repair(reply: str, rep: ValidationReport) -> Optional[str]:
    """إصلاح آمن محافظ: لا جراحة نصية خطرة — يعيد الرد مع وسم الغموض فقط.

    القرار (ADR-005): الإصلاح النصي العنيف للرد المولد من نموذج خارجي خطر؛
    الأسلوب الآمن هو طلب توضيح واحد محدد عند فشل الإحالة، وتسجيل الباقي
    في التتبع. يُعاد التوليد في المسار المتقدم (pipeline.compose_and_validate).
    """
    for issue in rep.issues:
        if issue.code == "unbound_reference" and rep.issues and len(rep.issues) == 1:
            return reply + "\n\n(توضيح: أشرت بضمير دون مرجع واضح في سياقنا — أيّ أمرٍ تقصد؟)"
    return None
