"""R-838: خط الأنابيب المتكامل — حلقة الوكيل الواحدة قبل القرار وبعد التوليد.

يربط كل مكون في حلقة واحدة (المعمارية 4.6-4.8):
analyze(text) → تحديث الجدول والذاكرة → حل الإحالات → سياق مجمع →
سؤال قائم بذاته للأدوات → (توليد الرد خارج هذه الحزمة) → validate_reply.

توافق عكسي كامل مع عقد context_resolver القديم:
{original, standalone, followup, kind} — نفس المفاتيح، فهم أعمق.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import detector as _det
from . import frame as _frame
from . import lexicon as _lex
from . import scripts as _sc
from .entity_table import EntityTable
from .memory import HierarchicalMemory
from .validator import validate_reply as _validate_reply

_tok = _sc.tokenize
_PRON_SUFFIXES = ("هما", "كما", "كم", "كن", "هم", "هن", "نا", "ها", "ه", "ك", "ي")
_BARE_PRONOUNS = set(_frame._DETACHED_PRON_AR) | set(_frame._DEMONSTRATIVES_AR) \
    | set(_frame._EN_PRONOUNS)


@dataclass
class ConversationState:
    """حالة محادثة كاملة: إطار + جدول كيانات + ذاكرة هرمية + تتبع."""
    table: EntityTable = field(default_factory=EntityTable)
    memory: HierarchicalMemory = field(default_factory=HierarchicalMemory)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    last_user_lang: str = "ar"

    # ------------------------------------------------------------------
    def process_user_message(self, text: str, utterance_id: str = "utt") -> Dict[str, Any]:
        """دور كامل قبل الرد: كشف، تحليل، تحديث، حل إحالات، تجميع سياق.

        يرجع: {frame, resolved, context_pack, retrieval, standalone, followup}
        """
        detection = _det.detect(text)
        self.last_user_lang = detection.languages[0] if detection.languages else "ar"
        frame = _frame.analyze(text, utterance_id)

        # تحديث الجدول والذاكرة (بروتوكول 5.4)
        self.table.advance_turn()
        turn = self.table.turn
        for ent in frame.get("entities", []):
            self.table.add_or_update(ent, utterance_id, "user", turn)
        self.memory.ingest_turn("user", text, frame, turn=turn)

        # حل الإحالات (بروتوكول 5.2)
        active_ids: List[str] = []
        resolved_refs: List[Dict] = []
        for ref in frame.get("references", []):
            resolved = self.table.resolve(ref)
            if resolved.get("resolved_id"):
                self.table.bind_reference(resolved, turn, utterance_id)
                active_ids.append(resolved["resolved_id"])
            resolved_refs.append(resolved)
        frame["references"] = resolved_refs

        # حذف الفاعل: استرجاع الفاعل الأبرز المتوافق أو المتكلم
        for ref in resolved_refs:
            if ref.get("type") == "ellipsis" and not ref.get("resolved_id"):
                ent = self.table.most_salient(
                    gender=ref.get("gender", "unknown"),
                    number=ref.get("number", "unknown"), person="3",
                    role="subject")
                if ent:
                    ref["resolved_id"] = ent.id
                    ref["confidence"] = 0.55
                    ref["ellipsis_recovered"] = True
                    active_ids.append(ent.id)

        # استرجاع دلالي عبر اللغات
        retrieval = self.memory.retrieve(frame, entity_ids=active_ids)

        # تجميع السياق (بروتوكول 5.1)
        context_pack = self.memory.context_pack()
        context_pack["entity_table"] = self.table.to_dict()
        context_pack["user_lang"] = self.last_user_lang

        # غموض مؤثر: مرجحان متقاربان ⇒ سؤال توضيحي واحد لا اختيار صامت
        clarification = None
        for ref in resolved_refs:
            if ref.get("ambiguous") and ref.get("type") != "ellipsis":
                cands = [self.table.entities[c].all_surfaces()[0]
                         for c in ref.get("candidate_entity_ids", [])[:2]
                         if c in self.table.entities and self.table.entities[c].all_surfaces()]
                if len(cands) >= 2:
                    clarification = (f"توضيح واحد: بأيٍّ تقصد «{cands[0]}» "
                                     f"أم «{cands[1]}»؟")
                    break

        standalone, followup = self._standalone(text, frame, retrieval)
        self.trace.append({
            "utterance_id": utterance_id, "analysis_path": frame.get("analysis_path"),
            "languages": frame.get("languages"), "entities_added": len(frame.get("entities", [])),
            "references_resolved": sum(1 for r in resolved_refs if r.get("resolved_id")),
            "references_ambiguous": sum(1 for r in resolved_refs if r.get("ambiguous")),
            "retrieval_hits": len(retrieval),
            "intermediate_translation": False,   # إثبات قابل للفحص
        })
        return {"frame": frame, "resolved": resolved_refs, "context_pack": context_pack,
                "retrieval": retrieval, "standalone": standalone, "followup": followup,
                "clarification": clarification, "active_entity_ids": active_ids}

    # ------------------------------------------------------------------
    def _standalone(self, text: str, frame: Dict, retrieval: List) -> tuple:
        """سؤال قائم بذاته للأدوات والبحث — من الفهم الأصيل لا من القوالب.

        قواعد البناء (ADR-002):
        - ضمير منفصل/إشارة (كلمة مستقلة) ⇒ يُستبدل بالاسم.
        - اسم + ضمير متصل («سكانها») ⇒ «جذر + اسم الكيان».
        - فعل + ضمير مفعول («وصلتها») ⇒ يبقى الفعل ويُضاف الكيان سياقًا
          في نهاية الجملة — لا تُبتر الأفعال.
        - حذف فاعل ⇒ يُبنى بالفاعل المسترجع.
        - لا إحالات (رسالة مكتملة) ⇒ النص كما هو.
        """
        refs = frame.get("references", [])
        followup = bool(refs)
        if not followup:
            return text, False

        lang = self.last_user_lang
        out = text
        context_notes: List[str] = []

        def _name_of(ent_id: str) -> Optional[str]:
            ent = self.table.entities.get(ent_id)
            if not ent:
                return None
            # R-838.4: كيان الرابط يُسمّى بالرابط نفسه في السؤال القائم بذاته —
            # الأسطح العربية الممتصة (المشروع/المستودع/المرفق) تعريفٌ للحوار
            # لا أسماء استبدال: «هل هو جاهز؟» يصبح «هل {الرابط} جاهز؟»
            if ent.type == "url":
                for surs in ent.surfaces.values():
                    for s in surs:
                        if "://" in s or s.startswith("http"):
                            return s
            surs = ent.surfaces.get(lang) or ent.all_surfaces()
            return surs[0] if surs else None

        for ref in refs:
            mention = ref.get("mention", "")
            name = _name_of(ref.get("resolved_id") or "")
            if not name:
                continue
            if ref.get("type") == "ellipsis":
                # حذف فاعل: «راجع التقرير» ⇒ «{الكيان} راجع التقرير»
                verb = mention.replace("[فاعل محذوف:", "").rstrip("]").strip()
                if verb in out:
                    out = out.replace(verb, f"{name} {verb}", 1)
                continue
            if mention.startswith("["):
                continue
            # ضمير مفعول متصل بفعل («وصلتها/راجعه») ⇒ لا بتر للفعل — سياق بالنهاية
            if ref.get("attached_to") == "verb":
                context_notes.append(name)
                continue
            # ضمير منفصل/إشارة: كلمة مستقلة معروفة ⇒ استبدال مباشر
            if ref.get("type") in ("pronoun", "demonstrative") and " " not in mention \
                    and mention in out and mention in _BARE_PRONOUNS:
                out = out.replace(mention, name, 1)
                continue
            # اسم + ضمير متصل: «سكانها» ⇒ «سكان اليابان»
            if ref.get("type") == "pronoun" and " " not in mention and mention in out:
                # R-838: «تعجبني/سألتني/تكويني» — ضمير «ني» متصل: لا جراحة نصية
                # إطلاقًا (فعل بمفعول أو اسم ملكية) — سياق آمن بالنهاية فقط
                if mention.endswith("ني") and len(mention) >= 5:
                    context_notes.append(name)
                    continue
                stem = None
                for suf in _PRON_SUFFIXES:
                    if mention.endswith(suf) and len(mention) - len(suf) >= 2:
                        stem = mention[: -len(suf)]
                        break
                if stem and len(stem) >= 3:
                    out = out.replace(mention, f"{stem} {name}", 1)
                    continue
                # فعل + ضمير مفعول: لا بتر — سياق في النهاية
                context_notes.append(name)
        for n in dict.fromkeys(context_notes):
            if n in out:      # R-838: الكيان مذكور صراحةً — لا تكرار في السياق
                continue
            out = f"{out.rstrip('؟?')} — المقصود: {n}؟"
        return out.strip(), followup

    # ------------------------------------------------------------------
    def process_assistant_reply(self, reply: str, frame: Dict,
                                active_entity_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """بعد التوليد: تحقق + تحديث ذاكرة بالدور."""
        rep = _validate_reply(reply, frame, self.table, self.last_user_lang,
                              active_entity_ids=active_entity_ids)
        final_reply = rep.repaired_reply or reply
        self.memory.ingest_turn("assistant", final_reply, frame)
        self.trace.append({"kind": "assistant_reply", "validation_passed": rep.passed,
                           "issues": [i.code for i in rep.issues],
                           "repaired": rep.repaired_reply is not None})
        return {"report": rep.to_dict(), "final_reply": final_reply}


# ---------------------------------------------------------------------------
# واجهة متوافقة مع context_resolver القديم (عقد {original, standalone, followup, kind})
# ---------------------------------------------------------------------------

def resolve(text: str, history: Optional[List[Dict]] = None,
            state: Optional[ConversationState] = None) -> Dict[str, Any]:
    """بديل direct لـ context_resolver.resolve — نفس العقد القديم + فهم دلالي.

    history: قائمة {role, content} — يُعاد بناء الحالة منها عند غيابها
    (مسار التكامل في app.py يمررها).
    """
    st = state or ConversationState()
    if history:
        # بناء الحالة من التاريخ: تحليل أدوار المستخدم السابقة فقط (بلا ردود)
        for i, h in enumerate(history):
            if h.get("role") == "user":
                st.process_user_message(h.get("content", ""), f"hist_{i}")
    out = st.process_user_message(text, "utt_current")
    frame = out["frame"]
    followup = out["followup"]
    kind = "semantic"
    if followup and any(r.get("type") == "ellipsis" for r in frame.get("references", [])):
        kind = "ellipsis_resolved"
    return {"original": text, "standalone": out["standalone"], "followup": followup,
            "kind": kind, "frame": frame, "state": st,
            "clarification": out.get("clarification")}
