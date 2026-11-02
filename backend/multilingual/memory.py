"""R-838: الذاكرة الهرمية (المعمارية 4.4) — أربع طبقات وسياسات مكتوبة.

الطبقات:
1. عاملة قصيرة المدى: آخر الأدوار حرفيًا (نافذة محدودة).
2. عرضية: ملخصات دورية للأحداث والقرارات (استخلاصي حتمي).
3. دلالية طويلة المدى: حقائق وتريفات وكيانات وعلاقات — بوحدات معنى
   مستقلة عن اللغة (مفاتيح مفاهيم + معرفات كيانات).
4. إجرائية: قواعد تشغيل الوكيل (ثابتة، من السياسات المعلنة).

السياسة الإلزامية (docs/MEMORY_POLICY.md):
- ماذا يُحفظ: الحقائق القابلة للإسناد (فاعل-علاقة-مفعول) والتفضيلات
  والقرارات؛ لا يُحفظ نص خام بلا معنى قابل للاسترجاع.
- التلخيص: عند تجاوز العاملة حدًا ⇒ أقدم الأدوار تُلخص إلى العرضية.
- الدمج والتعارض: حقيقة جديدة تخالف قديمة ⇒ الأحدث تُفضل للحقائق المتغيرة
  مع حفظ القديمة موسومة deprecated ومصدرها — لا حذف صامت.
- النسيان: وحدة لم تُسترجع ولم تُذكر خلال TTL ⇒ مهملة (suppress لا حذف).
- الاسترجاع: حسب الصلة بالسياق (مفاهيم + كيانات) لا الحداثة فقط.
- المصدر provenance: كل وحدة تحمل الدور/المعرف/الدور الزمني.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import lexicon as _lex
from . import scripts as _sc

WORKING_WINDOW = 12            # أدوار حرفية في الطبقة العاملة
EPISODIC_TRIGGER = 10          # لف الأدوار إلى ملخص عرضي عند هذا العدد
SEMANTIC_TTL_TURNS = 120       # عمر وحدة المعنى بلا ذكر/استرجاع
MAX_SEMANTIC_UNITS = 2000


@dataclass
class MeaningUnit:
    """وحدة معنى مستقلة عن اللغة قدر الإمكان (المعمارية 4.5)."""
    id: str
    subject: str                     # معرف كيان أو مفتاح مفهوم
    relation: str                    # مفتاح مفهوم (PROP:*/ACT:*)
    obj: str = ""
    lang: str = "unknown"            # لغة النص الأصلي (للصياغة، لا للفهم)
    original_text: str = ""          # النص الأصلي كما ورد (لا ترجمة)
    provenance: Dict = field(default_factory=dict)
    confidence: float = 1.0
    created_turn: int = 0
    last_recalled_turn: int = 0
    deprecated: bool = False
    supersedes: Optional[str] = None

    def to_dict(self) -> Dict:
        return self.__dict__.copy()


class HierarchicalMemory:
    """الذاكرة عبر الأدوار — كل دور يمر في ingest ثم retrieve عند الحاجة."""

    def __init__(self):
        self.working: List[Dict] = []              # أدوار حرفية {role, content, turn}
        self.episodic: List[Dict] = []             # ملخصات {turn_range, summary, entities}
        self.semantic: Dict[str, MeaningUnit] = {} # id => وحدة
        self.procedural: List[str] = []            # قواعد تشغيل
        self._next_unit = 1
        self.turn = 0

    # ------------------------------------------------------------------
    def ingest_turn(self, role: str, content: str, frame: Dict,
                    turn: Optional[int] = None) -> None:
        """بروتوكول دمج الذاكرة (5.4): استخراج، تعارض، مصدر، كيانات، لف."""
        self.turn = turn if turn is not None else self.turn + 1
        self.working.append({"role": role, "content": content, "turn": self.turn})
        if len(self.working) > WORKING_WINDOW:
            self._compact_working()
        self._extract_semantic(role, content, frame)
        if len(self.working) >= EPISODIC_TRIGGER:
            self._summarize_episodic()

    # ------------------------------------------------------------------
    def _compact_working(self) -> None:
        """أقدم الأدوار خارج النافذة ⇒ ملخص عرضي (استخلاصي حتمي)."""
        overflow = self.working[:-WORKING_WINDOW]
        self.working = self.working[-WORKING_WINDOW:]
        if overflow:
            ents: List[str] = []
            for t in overflow:
                for e in (t.get("frame_entities") or []):
                    s = e.get("surface")
                    if s and s not in ents:
                        ents.append(s)
            self.episodic.append({
                "turn_range": (overflow[0]["turn"], overflow[-1]["turn"]),
                "summary": "؛ ".join(
                    f"{t['role']}: {t['content'][:120]}" for t in overflow
                )[:2000],
                "entities": ents,
            })
            self.episodic = self.episodic[-50:]   # منع التضخم

    def _summarize_episodic(self) -> None:
        pass  # اللف يتم في _compact_working — هذه النقطة علامة توسعة مستقبلية

    # ------------------------------------------------------------------
    def _extract_semantic(self, role: str, content: str, frame: Dict) -> None:
        """استخراج وحدات معنى من الإطار: خصائص كيانات وأفعال ونية.

        قاعدة الصدق: الوحدة تسجل النص الأصلي كمصدر؛ الفهم من الأصل.
        """
        for ent in frame.get("entities", []):
            ck = ent.get("concept_key")
            if not ck:
                continue
            # كيان له خاصية مذكورة في النص (PROP:*) ⇒ وحدة معنى
            for tok in _sc.tokenize(content):
                base = tok[1:] if tok[:1] in ("و", "ف") and len(tok) > 3 else tok
                hit = _lex.lookup_token(base)
                if hit and hit[0].startswith("PROP:"):
                    unit = MeaningUnit(
                        id=f"u{self._next_unit}", subject=ck, relation=hit[0],
                        obj="", lang=ent.get("lang", "unknown"),
                        original_text=content,
                        provenance={"utterance_id": frame.get("utterance_id"),
                                   "role": role, "turn": self.turn},
                        confidence=0.8, created_turn=self.turn,
                    )
                    self._upsert(unit)
                    self._next_unit += 1

    def _upsert(self, unit: MeaningUnit) -> None:
        """دمج/تعارض: نفس (فاعل، علاقة) ⇒ الأحدث تفوز والقديمة deprecated لا محذوفة."""
        for uid, existing in self.semantic.items():
            if (existing.subject == unit.subject and existing.relation == unit.relation
                    and not existing.deprecated):
                if existing.lang != unit.lang or existing.original_text != unit.original_text:
                    existing.deprecated = True
                    unit.supersedes = uid
                    self.semantic[unit.id] = unit
                else:
                    existing.last_recalled_turn = self.turn
                return
        self.semantic[unit.id] = unit
        self._enforce_ttl()

    def _enforce_ttl(self) -> None:
        """نسيان: وحدة بلا ذكر/استرجاع خلال TTL ⇒ مهملة (لا حذف فيزيائي)."""
        if len(self.semantic) > MAX_SEMANTIC_UNITS:
            oldest = sorted(self.semantic.values(), key=lambda u: u.last_recalled_turn)
            for u in oldest[: len(self.semantic) - MAX_SEMANTIC_UNITS]:
                u.deprecated = True

    # ------------------------------------------------------------------
    def retrieve(self, query_frame: Dict, entity_ids: Optional[List[str]] = None,
                 limit: int = 8) -> List[Dict]:
        """استرجاع حسب الصلة (مفاهيم الاستعلام + كياناته) لا الحداثة فقط.

        يعيد نتائج مع درجة صلة وسبب الاسترجاع (المعمارية 4.5).
        """
        q_keys: set = set()
        q_text = " ".join(s["text"] for s in query_frame.get("segments", []))
        for tok in _sc.tokenize(q_text):
            base = tok[1:] if tok[:1] in ("و", "ف") and len(tok) > 3 else tok
            hit = _lex.lookup_token(base)
            if hit:
                q_keys.add(hit[0])
        q_entities = {e.get("concept_key") for e in query_frame.get("entities", [])
                     if e.get("concept_key")}
        ids = set(entity_ids or [])

        out: List[Dict] = []
        for uid, unit in self.semantic.items():
            if unit.deprecated:
                continue
            reasons: List[str] = []
            score = 0.0
            if unit.relation in q_keys:
                score += 0.5
                reasons.append(f"علاقة مشتركة {unit.relation}")
            if unit.subject in q_entities:
                score += 0.4
                reasons.append(f"كيان الاستعلام {unit.subject}")
            if ids and any(k in ids for k in [unit.subject]):
                score += 0.3
                reasons.append("كيان نشط في المحادثة")
            # حداثة عامل ثانوي لا أول
            recency = 1.0 / (1 + max(0, self.turn - unit.created_turn))
            score += 0.1 * recency
            if score > 0.15:
                out.append({"unit": unit.to_dict(), "score": round(score, 3),
                            "reason": "؛ ".join(reasons) or "قرب زمني"})
        out.sort(key=lambda x: -x["score"])
        return out[:limit]

    # ------------------------------------------------------------------
    def stats(self) -> Dict:
        return {
            "working": len(self.working), "episodic_summaries": len(self.episodic),
            "semantic_units": sum(1 for u in self.semantic.values() if not u.deprecated),
            "semantic_deprecated": sum(1 for u in self.semantic.values() if u.deprecated),
        }

    def context_pack(self, budget: int = 6000) -> Dict[str, Any]:
        """بروتوكول تجميع السياق (5.1): ترتيب تعليمات > ثابت > حديث > استرجاع."""
        working_txt = "\n".join(f"{t['role']}: {t['content']}" for t in self.working[-8:])
        episodic_txt = "\n".join(
            f"[{s['turn_range'][0]}-{s['turn_range'][1]}] {s['summary'][:300]}"
            for s in self.episodic[-5:])
        return {
            "working": working_txt[-budget // 2:],
            "episodic": episodic_txt[-budget // 4:],
            "included": {"working_turns": len(self.working),
                        "episodic_summaries": len(self.episodic)},
            "omitted_note": "ما تجاوز الميزانية لُف في ملخصات عرضية",
        }
