# -*- coding: utf-8 -*-
"""R-838.4: أسهم الحوار لا تخطف الضمائر — لا توضيح وهمي بعد رابط.

المشهد من الإنتاج (حوار حقيقي عن Infrasys-AI/AISystem):
- «ماهو المشروع ؟ ما عمله ؟» بعد رابط ⇒ توضيح وهمي «بأيٍّ تقصد الرابط أم المستودع؟»
- «منهو منشؤه ؟» ⇒ توضيح وهمي «بأيٍّ تقصد «منهو» أم الرابط؟» (منهو استفهامية!)
- «قم باستيراده» ⇒ توضيح وهمي «بأيٍّ تقصد «منهو» أم الرابط؟»

الجذور الأربعة التي صُلحت:
1. الاستفهاميات اللهجية (منهو/منو/شنو/وين/امتى) ليست كيانات.
2. عطف البيان: «المستودع» الملاصق للرابط سطحٌ لمرساة الرابط لا كيان منافس.
3. الاسم الخطابي بضمير مخاطب («سؤالك») إشارة للحوار نفسه لا كيان ينافس.
4. أسماء «الأشياء» (المشروع/المستودع/الريبو…) تمتصها مرساة الرابط،
   وكيان الرابط مركز الحوار (Centering) فلا تخطفه الصفات العابرة («مفصل»).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from multilingual.pipeline import ConversationState, resolve  # noqa: E402
from multilingual.frame import analyze  # noqa: E402


def test_production_dialogue_no_spurious_clarifications():
    """الحوار الحرفي من الإنتاج — لا توضيح واحد في أي دور من الأدوار الخمسة."""
    st = ConversationState()
    turns = [
        "اريد شرح مفصل عن المستودع https://github.com/Infrasys-AI/AISystem",
        "ماهو المشروع ؟ ما عمله ؟",
        "لم افهم سؤالك ماذا تقصد ؟",
        "منهو منشؤه ؟",
        "قم باستيراده",
    ]
    for i, t in enumerate(turns, 1):
        out = st.process_user_message(t, f"utt_{i}")
        cl = out.get("clarification")
        assert cl is None, f"دور {i} («{t}») ولّد توضيحًا وهميًا: {cl}"


def test_dialectal_interrogatives_are_never_entities():
    """«منهو/منو/شنو/وين/امتى» استفهامات لهجية — لا كيانات تنافس الضمائر."""
    for w in ("منهو", "منو", "شنو", "وين", "امتى"):
        fr = analyze(f"{w} منشؤه ؟")
        surfaces = [e["surface"] for e in fr.get("entities", [])]
        assert w not in surfaces, f"«{w}» صار كيانًا يخطف الضمائر"


def test_apposition_alias_absorbed_into_url_anchor():
    """«المستودع» الملاصق للرابط سطح لمرساة الرابط لا كيان منفصل."""
    st = ConversationState()
    st.process_user_message("اشرح المستودع https://github.com/x/y", "u1")
    ents = [e for e in st.table.entities.values() if e.type == "url"]
    assert len(ents) == 1, "الرابط مرساة واحدة"
    assert "المستودع" in ents[0].surfaces.get("ar", []), "عطف البيان سطح للمرساة"


def test_discourse_deictic_with_attached_you_not_entity():
    """«سؤالك» إشارة إلى الحوار نفسه — ليست كيانًا ينافس على الضمائر."""
    fr = analyze("لم افهم سؤالك ماذا تقصد ؟")
    surfaces = [e["surface"] for e in fr.get("entities", [])]
    assert "سؤال" not in surfaces, "«سؤالك» خطابي لا كيان"


def test_anchor_noun_in_later_turn_absorbed_into_url():
    """«ماهو المشروع؟» بعد رابط — «المشروع» والرابط مرجع واحد لا كيانان."""
    st = ConversationState()
    st.process_user_message("اشرح https://github.com/x/y", "u1")
    st.process_user_message("ماهو المشروع ؟ ما عمله ؟", "u2")
    assert not any(e.type == "unknown" and "مشروع" in e.all_surfaces()
                   for e in st.table.entities.values()), "«المشروع» كيان منافس للرابط"
    url = next(e for e in st.table.entities.values() if e.type == "url")
    assert "المشروع" in url.surfaces.get("ar", [])


def test_url_topic_centering_beats_ephemeral_adjective():
    """«ما عمله؟» بعد «شرح مفصل عن الرابط» — الضمير على الرابط لا على «مفصل»."""
    h = [{"role": "user", "content":
          "اريد شرح مفصل عن المستودع https://github.com/a/b"}]
    r = resolve("ماهو المشروع ؟ ما عمله ؟", h)
    assert r["clarification"] is None, "توضيح وهمي ضد صفة عابرة"
    assert "https://github.com/a/b" in r["standalone"], \
        "«عمله» على المشروع=الرابط، والسؤال القائم بذاته يحمل الرابط"


def test_standalone_names_url_entity_by_its_url():
    """السؤال القائم بذاته يستبدل الضمير بالرابط نفسه لا بالسطح العربي الممتص."""
    h = [{"role": "user", "content":
          "اريد معلومات عن المشروع المرفق https://github.com/vooovg-ui/AMOS-Fedration"}]
    r = resolve("هل هو جاهز للانتاج ؟", h)
    assert "https://github.com/vooovg-ui/AMOS-Fedration" in r["standalone"]


def test_multiple_urls_still_distinguishable():
    """الامتصاص لا يدمج روابط متعددة — كل رابط كيانه الخاص."""
    st = ConversationState()
    st.process_user_message("قارن https://github.com/a/one و https://github.com/a/two", "u1")
    urls = [e for e in st.table.entities.values() if e.type == "url"]
    assert len(urls) == 2, "كل رابط مرساة مستقلة"
