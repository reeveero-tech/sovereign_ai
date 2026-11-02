"""R-838: جدول الكيانات ومحرك الإحالة والضمائر (المعمارية 4.3).

لكل محادثة جدول كيانات: معرف ثابت، أسماء/مرادفات بأي لغة، النوع والجنس
والعدد والشخص، التعريف، الحالة الخطابية (مذكور/نشط/مهمل/محذوف)، البروز
(salience) والحداثة (recency)، سلسلة الإحالة، والمصدر (provenance).

يعالج: الضمائر المنفصلة والمتصلة، حذف الفاعل، التعريف/التنكير، الجمع
والمثنى والمفرد، agreement الإنجليزية، الإشارات، والأسماء المتكررة بأكثر
من لغة (Japan = اليابان عبر المعجم المفاهيمي).

قاعدة إلزامية: لا يُولَّد رد يحتوي إحالة قبل التحقق من هذا الجدول
(ينفذها validator + pipeline).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import lexicon as _lex
from . import scripts as _sc

# R-838.4: أسماء «الأشياء» التي يحتملها الرابط — اسم معرف منها في حوار
# فيه كيان رابط (مرساة الحوار) هو سطح لمرساة الرابط لا كيان منافس:
# «ماهو المشروع؟» بعد رابط مستودع — «المشروع» والرابط مرجع واحد
# (وإلا وُلد توضيح وهمي لاحقًا: «بأيٍّ تقصد الرابط أم المشروع؟»)
_ANCHOR_NOUN_AR = {"مشروع", "مستودع", "مستودعات", "رابط", "روابط", "موقع",
                   "مواقع", "ريبو", "حساب", "منظمة", "منظمات", "شركة",
                   "شركات", "فريق", "فرق", "نظام", "أنظمة", "انظمة", "أداة",
                   "ادوات", "أدوات", "مكتبة", "مكتبات", "تطبيق", "تطبيقات",
                   "خدمة", "خدمات", "صفحة", "صفحات", "ملف", "ملفات", "كود",
                   "برنامج", "برامج", "باقة", "حزمة", "مستند"}

# هوامش قرار الإحالة
AMBIGUITY_MARGIN = 0.15
MIN_RESOLVE_CONFIDENCE = 0.35


@dataclass
class Entity:
    id: str
    type: str = "unknown"
    concept_key: Optional[str] = None
    # أسطح بأي لغة/خط: lang => قائمة أسطح
    surfaces: Dict[str, List[str]] = field(default_factory=dict)
    gender: str = "unknown"
    number: str = "unknown"
    person: str = "3"
    discourse_state: str = "mentioned"      # mentioned|active|suppressed|deleted
    salience: float = 1.0
    last_turn: int = -1
    first_turn: int = -1
    last_role: str = "unknown"             # subject|object (للإحالة النحوية)
    # R-838: آخر ذكر (دور، موقع) — الإحالة لا تشير إلا لما قبلها
    last_mention: tuple = (-1, -1)
    # R-838.1: معرف بـ«ال» — الضمير يحتاج مرجعًا معرفًا (مبدأ المعرفة)
    definite: bool = False
    coreference_chain: List[Dict] = field(default_factory=list)
    provenance: Dict = field(default_factory=dict)  # {utterance_id, role, source}

    def all_surfaces(self) -> List[str]:
        out: List[str] = []
        for lst in self.surfaces.values():
            out.extend(lst)
        return out

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "type": self.type, "concept_key": self.concept_key,
            "surfaces": self.surfaces, "gender": self.gender, "number": self.number,
            "person": self.person, "discourse_state": self.discourse_state,
            "salience": round(self.salience, 3), "last_turn": self.last_turn,
            "first_turn": self.first_turn,
            "coreference_chain": self.coreference_chain, "provenance": self.provenance,
        }


class EntityTable:
    """جدول كيانات المحادثة + محرك الإحالة (بروتوكول 5.2)."""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self._next_id = 1
        self.turn = 0

    # ------------------------------------------------------------------
    def _find_by_surface(self, surface: str, lang: Optional[str] = None) -> Optional[Entity]:
        """بحث كيان بسطح لغوي (تطبيع + كل اللغات أو لغة محددة)."""
        n = _sc.norm_for_match(surface)
        if not n:
            return None
        for ent in self.entities.values():
            if ent.discourse_state == "deleted":
                continue
            if lang:
                for s in ent.surfaces.get(lang, []):
                    if _sc.norm_for_match(s) == n:
                        return ent
            else:
                for s in ent.all_surfaces():
                    if _sc.norm_for_match(s) == n:
                        return ent
        return None

    def _find_by_concept(self, concept_key: str) -> Optional[Entity]:
        """ربط عبر اللغات: نفس مفتاح المفهوم ⇒ نفس الكيان (Japan = اليابان)."""
        for ent in self.entities.values():
            if ent.concept_key == concept_key and ent.discourse_state != "deleted":
                return ent
        return None

    # ------------------------------------------------------------------
    def add_or_update(self, ent_data: Dict, utterance_id: str, role: str,
                      turn: int) -> Entity:
        """دمج كيان من الإطار الدلالي في الجدول (منشأ جديد أو تحديث قائم).

        - الاسم المعروف بكيان قائم ⇒ تحديث البروز والحداثة لا كيان جديد.
        - مفتاح مفهوم مشترك (معجم) ⇒ نفس الكيان عبر اللغات.
        - R-838.4: اسم معرف يدل على «الشيء» الذي يحتمله الرابط (المشروع/
          المستودع/الريبو…) في حوار فيه كيان رابط ⇒ سطح لمرساة الرابط لا
          كيان منافس: «ماهو المشروع؟» بعد ذكر رابط — «المشروع» والرابط
          مرجع واحد، لا كيانان يولدان لاحقًا توضيحًا وهميًا على الضمائر
          («منهو منشؤه؟» ⇐ «بأيٍّ تقصد الرابط أم المشروع؟»).
        """
        surface = ent_data.get("surface", "")
        lang = ent_data.get("lang", "unknown")
        ck = ent_data.get("concept_key")

        ent = self._find_by_surface(surface)
        if ent is None and ck:
            ent = self._find_by_concept(ck)
        if ent is None and surface.startswith("ال") and len(surface) > 4 \
                and surface[2:] in _ANCHOR_NOUN_AR:
            anchor = next((e for e in self.entities.values()
                           if e.type == "url" and e.discourse_state != "deleted"
                           and e.first_turn <= turn), None)
            if anchor is not None:
                ent = anchor
                ent.surfaces.setdefault("ar", [])
                if surface not in ent.surfaces["ar"]:
                    ent.surfaces["ar"].append(surface)
        if ent is None:
            ent = Entity(id=f"e{self._next_id}", type=ent_data.get("type", "unknown"),
                         concept_key=ck)
            self._next_id += 1
            self.entities[ent.id] = ent
            ent.first_turn = turn

        # سطوح جديدة بأي لغة
        ent.surfaces.setdefault(lang, [])
        if surface not in ent.surfaces[lang]:
            ent.surfaces[lang].append(surface)
        # R-838.4: أسطح عطف البيان — الاسم المعرف الملاصق للرابط (قبله أو
        # بعده مباشرة في الرسالة نفسها) سطح آخر لكيان الرابط لا كيان منافس:
        # «شرح مفصل عن المستودع <الرابط>» مرجع واحد، فلا يولد لاحقًا تنافس
        # كاذب على الضمائر (توضيح وهمي «بأيٍّ تقصد الرابط أم المستودع؟»)
        for alias in ent_data.get("aliases") or []:
            if isinstance(alias, str) and alias:
                ent.surfaces.setdefault("ar", [])
                if alias not in ent.surfaces["ar"]:
                    ent.surfaces["ar"].append(alias)
        # أسطح المعجم بكل اللغات (مرادفات عبر اللغات)
        if ck:
            for l, surs in _lex.all_langs_for(ck).items():
                lst = ent.surfaces.setdefault(l, [])
                for s in surs:
                    if s not in lst:
                        lst.append(s)

        # خصائص أعدل معلومة على الأدق
        for f in ("gender", "number", "person"):
            v = ent_data.get(f)
            if v and v != "unknown" and ent.__dict__[f] in ("unknown", None):
                setattr(ent, f, v)
            elif v and v != "unknown":
                # تحديث الخصائص من آخر ذكر صريح (أسماء صريحة أدق من الضمائر)
                setattr(ent, f, v)
        if ent_data.get("type", "unknown") != "unknown":
            ent.type = ent_data["type"]
        if ent_data.get("role") in ("subject", "object"):
            ent.last_role = ent_data["role"]
        # R-838.1: التعريف صفة دائمة — «المشروع» معرفة ولو ذُكرت نكرةً سابقًا
        if ent_data.get("definiteness") == "def":
            ent.definite = True

        ent.discourse_state = "active"
        ent.salience += 1.0
        ent.last_turn = turn
        # R-838: آخر ذكر (دور، موقع الرمز) — أساس اتجاه الإحالة
        ent.last_mention = (turn, ent_data.get("pos", 0))
        ent.provenance = {"utterance_id": utterance_id, "role": role,
                          "source": "conversation"}
        ent.coreference_chain.append({
            "turn": turn, "utterance_id": utterance_id, "surface": surface,
            "kind": "entity_mention",
        })
        return ent

    # ------------------------------------------------------------------
    def advance_turn(self) -> None:
        """تليين البروز مع الوقت — بروز الأحدث أعلى عند التعادل."""
        self.turn += 1
        for ent in self.entities.values():
            if ent.discourse_state in ("deleted",):
                continue
            ent.salience = max(0.2, ent.salience * 0.85)
            if self.turn - ent.last_turn > 8 and ent.discourse_state == "mentioned":
                ent.discourse_state = "suppressed"

    # ------------------------------------------------------------------
    def _agreement_ok(self, ent: Entity, ref: Dict) -> bool:
        """فلترة توافق النوع/الجنس/العدد/الشخص (بروتوكول 5.2 خطوة 3)."""
        rg, rn, rp = ref.get("gender", "unknown"), ref.get("number", "unknown"), ref.get("person", "unknown")
        if rg not in ("unknown", None) and ent.gender not in ("unknown",) and rg != ent.gender:
            # استثناء: «هي» للمؤنث الجمعي/الجموع غير العاقبة تُعامل مذكرًا لغويًا
            return False
        if rn not in ("unknown", None) and ent.number not in ("unknown",) and rn != ent.number:
            # جمع قد يشير لمفرد مجازًا — نسمح بثقة منخفضة عبر الهامش لا الحجب
            if not (rn == "pl" and ent.number in ("sg", "du")):
                return False
        if rp not in ("unknown", None, "1", "2") and ent.person not in ("unknown",) and rp != ent.person:
            return False
        return True

    def resolve(self, ref: Dict) -> Dict:
        """حل إحالة واحدة — يعيد مرجعًا معززًا بالمرشحين والثقة والغموض.

        الترتيب: فلترة الاتفاق ثم درجة = 0.45×بروز + 0.35×حداثة + 0.2×دور الخطاب.
        مرشحان متقاربان ⇒ غموض مسجل لا اختيار صامت (بروتوكول 5.2 خطوة 5-6).
        """
        candidates: List[tuple] = []
        # R-838.1: ضمائر المتكلم/المخاطب (ني/ك/نا/كم…) لا تنافس كيانات
        # الجدول أبدًا — تعود على المتكلم أو المخاطب مباشرة. إسنادها لكيان
        # (كما حدث إنتاجيًا: «واعطني» نافست «بتحليل» و«المشروع») خطأ تصاعدي:
        # ربط خاطئ يرفع بروز الكيان الخاطف ويخطف الإحالات التالية.
        if ref.get("person") in ("1", "2"):
            out = dict(ref)
            out["candidate_entity_ids"] = []
            out["resolved_id"] = None
            out["confidence"] = 0.9
            out["ambiguous"] = False
            out["resolved_to"] = "speaker" if ref.get("person") == "1" else "listener"
            return out
        # R-838: اتجاه الإحالة — الضمير/الإشارة لا تشير إلا لكيان ذُكر قبلها
        # («هل هو جاهز للانتاج؟» — «للانتاج» بعد الضمير لا يخطفه). مرتان:
        # صارمة أولًا، وإن خلت فبلا فلتر الاتجاه (لا نقتل الحل كله).
        ref_pos = ref.get("pos")
        _strict = ref.get("type") in ("pronoun", "demonstrative") and ref_pos is not None
        _now = (self.turn, ref_pos)
        for _pass_strict in (True, False) if _strict else (False,):
            for ent in self.entities.values():
                if ent.discourse_state == "deleted":
                    continue
                if _pass_strict and not ent.last_mention < _now:
                    continue
                # خصائص/أفعال المعجم (PROP:*/ACT:*) مسندات سؤال لا مراجع تنازع
                # («سكانها» تعود على اليابان لا على «عاصمة»)
                if ent.concept_key and ent.concept_key.split(":")[0] in ("PROP", "ACT"):
                    continue
                if not self._agreement_ok(ent, ref):
                    continue
                recency = 1.0 / (1 + max(0, self.turn - ent.last_turn))
                # R-838.1: الحداثة داخل الدور الواحد موقعية — تُستبدل لا تُدمى
                # (حداثة الدور 1.0 للجميع؛ الفاصل موقعه من الضمير):
                # «بتحليل المشروع واستكشافه» — الضمير على المشروع المفعول
                # المباشر الأقرب، لا على «بتحليل» الأبعد. والمذكور السابق
                # مباشرة هو الافتراضي البراغماتي (+0.3).
                _pos_bonus = 0.0
                if ref_pos is not None and ent.last_mention \
                        and ent.last_mention[0] == self.turn:
                    _dist = ref_pos - ent.last_mention[1]
                    if _dist > 0:
                        recency = 1.0 / (1 + _dist)
                        if _dist == 1:
                            _pos_bonus = 0.3
                sal = min(1.0, ent.salience / 5.0)
                score = 0.45 * sal + 0.35 * recency + 0.2 * (0.6 if ent.discourse_state == "active" else 0.2) + _pos_bonus
                # R-838.1: المعرفة خير مرجع — لكن تزداد قيمتها بثراء الكيان في
                # الخطاب (بروزه): نكرة حديثة لا تخطف الضمير بتعريفها اللغوي
                # وحده («المكتب» لا يفوز بـ«هو» على أحمد وخالد المتنافسين)
                if getattr(ent, "definite", False):
                    score += 0.15 * min(1.0, ent.salience / 3.0)
                # R-838.4: مرساة الحوار — كيان الرابط موضوع الحوار الصريح،
                # والضمائر تفضل مركز الحوار (Centering) على المرشحين
                # العرضيين («ما عمله؟» بعد رابط — «عمله» على المشروع لا على
                # صفة عابرة مثل «مفصل» من «شرح مفصل»)
                if ent.type == "url":
                    score += 0.2
                # ضمير حرف جر («عليه/فيها») أو مفعول متصل بفعل («راجعه»)
                # ⇒ تفضيل الكيان الذي دوره مفعول (براغماتيا عربية)
                if (ref.get("prep") or ref.get("attached_to") == "verb") \
                        and ent.last_role == "object":
                    score += 0.5
                # حذف الفاعل: الفاعل المحذوف وكيل — يُفضل الكيان الذي دوره فاعل
                # R-838.1: عُزز 0.4→0.6 — مفعول مُخدوم حديثًا بضمير (بروز +1.5)
                # لا يهزم استرجاع الفاعل («راجعه» فاعلها أحمد لا التقرير)
                if ref.get("type") == "ellipsis" and ent.last_role == "subject":
                    score += 0.6
                # مرشح بضد الاسم المذكور صراحة في الإحالة (definite_np)
                if ref.get("type") == "definite_np" and ref.get("surface_norm"):
                    if ref["surface_norm"] in {_sc.norm_for_match(s) for s in ent.all_surfaces()}:
                        score += 2.0
                candidates.append((score, ent))
            if candidates and _pass_strict:
                break   # المرور الصارم كفى — لا حل بلا اتجاه الإحالة
        candidates.sort(key=lambda x: -x[0])

        out = dict(ref)
        if not candidates:
            out["candidate_entity_ids"] = []
            out["resolved_id"] = None
            out["confidence"] = 0.0
            return out
        top_score, top_ent = candidates[0]
        out["candidate_entity_ids"] = [e.id for _, e in candidates[:3]]
        out["resolved_id"] = top_ent.id
        out["confidence"] = round(min(1.0, 0.4 + top_score / 3.0), 3)
        # غموض: مرشحان متقاربان
        if len(candidates) > 1 and top_score - candidates[1][0] < AMBIGUITY_MARGIN:
            out["ambiguous"] = True
            out["confidence"] = round(min(out["confidence"], 0.45), 3)
        else:
            out["ambiguous"] = False
        return out

    # ------------------------------------------------------------------
    def bind_reference(self, resolved_ref: Dict, turn: int, utterance_id: str) -> Optional[str]:
        """يربط إحالة محلولة بكيانها: تحديث السلسلة والبروز."""
        eid = resolved_ref.get("resolved_id")
        if not eid or eid not in self.entities:
            return None
        ent = self.entities[eid]
        ent.salience += 1.5 if resolved_ref.get("type") == "pronoun" else 1.0
        ent.last_turn = turn
        ent.discourse_state = "active"
        ent.coreference_chain.append({
            "turn": turn, "utterance_id": utterance_id,
            "surface": resolved_ref.get("mention", ""), "kind": resolved_ref.get("type", ""),
        })
        return eid

    # ------------------------------------------------------------------
    def most_salient(self, gender: str = "unknown", number: str = "unknown",
                     person: str = "3", role: str = "unknown") -> Optional[Entity]:
        """أبرز كيان متوافق — لحل حذف الفاعل والاسترجاع الآمن.

        role="subject" يفضل الفاعل (الفاعل المحذوف وكيل فعل).
        """
        best, best_score = None, -1.0
        for ent in self.entities.values():
            if ent.discourse_state == "deleted":
                continue
            ref = {"gender": gender, "number": number, "person": person}
            if not self._agreement_ok(ent, ref):
                continue
            recency = 1.0 / (1 + max(0, self.turn - ent.last_turn))
            sal = min(1.0, ent.salience / 5.0)
            score = 0.6 * sal + 0.4 * recency
            if role in ("subject", "object") and ent.last_role == role:
                score += 0.3
            if score > best_score:
                best, best_score = ent, score
        return best

    def to_dict(self) -> Dict:
        return {"turn": self.turn,
                "entities": [e.to_dict() for e in self.entities.values()]}

    def stats(self) -> Dict:
        return {"count": len(self.entities),
                "active": sum(1 for e in self.entities.values() if e.discourse_state == "active")}
