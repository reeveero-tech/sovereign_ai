"""R-838: اختبارات معايير القبول الخمسة عشر للنواة الدلالية متعددة اللغات.

كل اختبار هنا يقابل بندًا من معايير القبول في المهمة — لا يكتمل العمل إلا
بنجاحها كلها. الاختبارات حتمية بلا شبكة ولا خدمات خارجية (إثبات عدم وجود
ترجمة وسيطة يغطيه البند 12).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from multilingual import (ConversationState, analyze, detect,  # noqa: E402
                          resolve, validate_reply)

# ---------------------------------------------------------------------------


def _surfaces(state, eid):
    return state.table.entities[eid].all_surfaces()


def _find_entity(state, surface):
    for ent in state.table.entities.values():
        if any(s == surface for s in ent.all_surfaces()):
            return ent
    return None


# ===========================================================================
# ١) الضمائر العربية: منفصلة ومتصلة — ربط صحيح
# ===========================================================================

def test_pronouns_arabic_attached_and_detached():
    st = ConversationState()
    st.process_user_message("أرسل أحمد التقرير إلى سارة", "u1")
    out = st.process_user_message("وهل وصلتها؟", "u2")
    ref = next(r for r in out["frame"]["references"] if r["mention"] == "وصلتها")
    sara = _find_entity(st, "سارة")
    assert ref["resolved_id"] == sara.id, "ها في «وصلتها» يجب أن تعود على سارة"

    # ضمير منفصل مؤنث
    out = st.process_user_message("وهل هي موافقة؟", "u3")
    ref = next(r for r in out["frame"]["references"] if r["mention"] == "هي")
    assert ref["resolved_id"] == sara.id, "«هي» يجب أن تعود على سارة"

    # جمع: حضر الطلاب والمعلمون ⇒ «هم»
    st2 = ConversationState()
    st2.process_user_message("حضر الطلاب إلى المدرسة", "u1")
    out = st2.process_user_message("هل أعجبهم المكان؟", "u2")
    ref = next(r for r in out["frame"]["references"] if r["mention"] == "أعجبهم")
    assert ref["number"] == "pl"
    assert ref["resolved_id"], "«هم» يجب أن تُحل إلى كيان جمع"


# ===========================================================================
# ٢) حذف الفاعل — استرجاع الفاعل الصحيح من السياق
# ===========================================================================

def test_pro_drop_subject_recovery():
    st = ConversationState()
    st.process_user_message("أرسل أحمد التقرير إلى سارة", "u1")
    out = st.process_user_message("ثم راجعه ووافق عليه", "u2")
    ell = next(r for r in out["frame"]["references"]
               if r["type"] == "ellipsis" and "راجعه" in r["mention"])
    ahmad = _find_entity(st, "أحمد")
    assert ell["resolved_id"] == ahmad.id, "فاعل «راجع» المحذوف هو أحمد لا التقرير"
    # VSO: جملة تبدأ بفعل وفاعلها صريح بعده لا تُعد حذفًا
    st2 = ConversationState()
    out2 = st2.process_user_message("أرسل أحمد التقرير", "u1")
    assert not any(r["type"] == "ellipsis" for r in out2["frame"]["references"]), \
        "«أرسل أحمد التقرير» فاعله صريح (VSO) — لا حذف"


# ===========================================================================
# ٣) التعريف والتنكير — أثر «ال» على المرجع
# ===========================================================================

def test_definiteness_indef_then_def():
    st = ConversationState()
    st.process_user_message("استلم أحمد تقريرًا جديدًا", "u1")
    out = st.process_user_message("وهل انتهى التقرير؟", "u2")
    # «التقرير» المعرف إشارة إلى «تقريرًا» النكرة الأول — كيان واحد بسلسلة واحدة
    rep = _find_entity(st, "التقرير")
    assert rep is not None
    assert any(m["kind"] == "entity_mention" and m["surface"] in ("تقرير", "تقريرًا", "التقرير")
               for m in rep.coreference_chain), \
        "النكرة ثم المعرف يجب أن تكونا كيانًا واحدًا بسلسلة إحالة واحدة"
    entities = [e for e in st.table.entities.values()
                if "تقرير" in " ".join(e.all_surfaces())]
    assert len(entities) == 1, "«تقريرًا» و«التقرير» كيان واحد لا اثنان"


# ===========================================================================
# ٤) الجمع والمثنى — تمييز المفرد/المثنى/الجمع وأثره في الإحالة
# ===========================================================================

def test_dual_and_plural():
    st = ConversationState()
    st.process_user_message("حضر الطالبان أحمد وخالد إلى القاعة", "u1")
    out = st.process_user_message("وهل تحدثا مع المعلم؟", "u2")
    ref = next(r for r in out["frame"]["references"] if "تحدثا" in r["mention"])
    assert ref["number"] == "du", "«تحدثا» فاعله مثنى"

    # جمع سالم: «وصل الطلاب» ثم «هم»
    st2 = ConversationState()
    st2.process_user_message("وصل الطلاب مبكرين", "u1")
    out = st2.process_user_message("هل أعجبهم الحفل؟", "u2")
    ref = next(r for r in out["frame"]["references"] if r["mention"] == "أعجبهم")
    assert ref["number"] == "pl"
    # ضمير الجمع لا يحل إلى مفرد
    sg = _find_entity(st2, "الحفل")
    if sg and ref["resolved_id"] == sg.id:
        raise AssertionError("ضمير الجمع «هم» لا يجوز أن يحل إلى مفرد")


# ===========================================================================
# ٥) الانتقال اللغوي: عربي ← إنجليزي ← عربي — حفاظ على الكيانات والسياق
# ===========================================================================

def test_language_switching():
    st = ConversationState()
    st.process_user_message("حدثني عن اليابان", "u1")
    out = st.process_user_message("What is its capital?", "u2")
    japan = _find_entity(st, "اليابان")
    assert japan is not None
    assert "japan" in [s.lower() for s in japan.all_surfaces()], \
        "الكيان يربط اليابان وJapan عبر اللغات"
    ref = next(r for r in out["frame"]["references"] if r["mention"] == "its")
    assert ref["resolved_id"] == japan.id, "«its» الإنجليزية تعود على اليابان المذكورة بالعربية"
    out = st.process_user_message("وكم عدد سكانها؟", "u3")
    ref = next(r for r in out["frame"]["references"] if r["mention"] == "سكانها")
    assert ref["resolved_id"] == japan.id, "«سكانها» بعد التبديل تعود على اليابان"


# ===========================================================================
# ٦) الجملة المختلطة: عربي+إنجليزي في الجملة نفسها
# ===========================================================================

def test_code_switching_within_sentence():
    f = analyze("راجع الـPR ووافق على الـmerge بتاعهم")
    langs = set(f["languages"])
    assert "ar" in langs and "en" in langs, "الجملة المختلطة يجب أن تُقسم لغويًا"
    assert f["analysis_path"] == "original_text"
    assert any(e for e in f["entities"] if "PR" in e["surface"]), "PR كيان"
    assert any(e for e in f["entities"] if "merge" in e["surface"]), "merge كيان"
    # تبديل داخل جملة إنجليزية
    f2 = analyze("I will راجع the report غدًا")
    texts = [(s["text"], s["lang"]) for s in f2["segments"]]
    assert any(l == "en" for _, l in texts) and any(l == "ar" for _, l in texts)


# ===========================================================================
# ٧) الاسترجاع عبر اللغات: سؤال إنجليزي عن معلومة ذُكرت بالعربية
# ===========================================================================

def test_cross_lingual_retrieval():
    st = ConversationState()
    st.process_user_message("عاصمة اليابان هي طوكيو", "u1")
    out = st.process_user_message("What is the capital of Japan?", "u2")
    top = out["retrieval"][0]
    assert top["unit"]["subject"] == "COUNTRY:JAPAN"
    assert top["unit"]["relation"] == "PROP:CAPITAL"
    assert top["score"] >= 0.5
    assert top["reason"], "نتيجة الاسترجاع تعلل سببها"


# ===========================================================================
# ٨) السياق الطويل: الذاكرة الهرمية تحفظ المعنى عبر نافذة أكبر
# ===========================================================================

def test_long_context_hierarchical_memory():
    st = ConversationState()
    # دورات كثيرة تتجاوز نافذة العاملة (12) — الحقيقة القديمة تبقى مسترجعة
    st.process_user_message("عاصمة فرنسا هي باريس", "u1")
    for i in range(30):
        st.process_user_message(f"أرسل أحمد تقريرًا رقم {i}", f"fill_{i}")
    out = st.process_user_message("What is the capital of France?", "final")
    hits = [r for r in out["retrieval"]
            if r["unit"]["subject"] == "COUNTRY:FRANCE"]
    assert hits, "الحقيقة القديمة (فرنسا/باريس) يجب أن تُسترجع بعد 30 دورًا"
    # الطبقة العرضية فعلت — ملخصات موجودة
    assert st.memory.stats()["episodic_summaries"] > 0, \
        "التجاوز يجب أن يلف الأدوار القديمة في ملخصات عرضية"


# ===========================================================================
# ٩) تعارض الذاكرة: معلومة قديمة تخالف جديدة — حل بمصدر
# ===========================================================================

def test_memory_conflict_resolution():
    st = ConversationState()
    st.process_user_message("العملة الرسمية في السعودية هي الدولار", "u1")
    st.process_user_message("العملة الرسمية في السعودية هي الريال", "u2")
    out = st.process_user_message("What is the official currency of Saudi Arabia?", "u3")
    hits = [r for r in out["retrieval"]
            if r["unit"]["relation"] == "PROP:CURRENCY" and not r["unit"]["deprecated"]]
    assert hits, "الوحدة الجديدة يجب أن تكون نشطة"
    # القديمة ليست محذوفة — deprecated بمصدرها
    dep = [u for u in st.memory.semantic.values()
           if u.deprecated and u.relation == "PROP:CURRENCY"]
    assert dep, "القديمة تُوسم deprecated لا تُحذف صامتة"
    assert dep[0].provenance.get("utterance_id") == "u1", "المصدر محفوظ للقديمة"


# ===========================================================================
# ١٠) الغموض المؤثر: مرجحان متقاربان ⇒ سؤال توضيحي واحد أو صياغة آمنة
# ===========================================================================

def test_material_ambiguity_clarification():
    st = ConversationState()
    st.process_user_message("قابل أحمد خالد في المكتب", "u1")
    out = st.process_user_message("هل هو موافق؟", "u2")
    ref = next(r for r in out["frame"]["references"] if r["mention"] == "هو")
    assert ref.get("ambiguous") or out["clarification"], \
        "مرجحان مذكران متقاربان ⇒ غموض مسجل لا اختيار صامت"
    if out["clarification"]:
        assert out["clarification"].count("؟") == 1, "سؤال توضيحي واحد فقط"


# ===========================================================================
# ١١) التحقق بعد التوليد: رد فيه إحالة خاطئة ⇒ يرفض ويُصلح قبل الإخراج
# ===========================================================================

def test_post_generation_validation():
    st = ConversationState()
    # رد فيه كيان غير مثبت (هلوسة كيان)
    f = analyze("ما اسمك؟", "u1")
    rep = validate_reply("اتصل بـ Microsoft لتأكيد الطلب", f, st.table, "ar")
    assert not rep.passed
    assert any(i.code == "unproven_entity" for i in rep.issues)
    # رد فيه ضمير بلا أي كيان نشط في جدول فارغ
    st2 = ConversationState()
    f2 = analyze("مرحبًا", "u2")
    rep2 = validate_reply("نعم هو جاهز", f2, st2.table, "ar", active_entity_ids=[])
    assert not rep2.passed
    assert rep2.repaired_reply and "توضيح" in rep2.repaired_reply, \
        "الإصلاح يضيف سؤال توضيح آمن"
    # رد سليم بكيانات مثبتة
    st3 = ConversationState()
    st3.process_user_message("ما عاصمة اليابان؟", "u1")
    out = st3.process_user_message("وكم عدد سكانها؟", "u2")
    good = validate_reply("عدد سكان اليابان حوالي 125 مليون نسمة.",
                          out["frame"], st3.table, "ar",
                          active_entity_ids=out["active_entity_ids"])
    assert good.passed, [i.code for i in good.issues]


# ===========================================================================
# ١٢) عدم الترجمة الوسيطة: تتبع يثبت أن الفهم من النص الأصلي
# ===========================================================================

def test_no_intermediate_translation():
    st = ConversationState()
    st.process_user_message("حدثني عن طوكيو", "u1")
    out = st.process_user_message("How big is it?", "u2")
    assert out["frame"]["analysis_path"] == "original_text"
    for entry in st.trace:
        assert entry.get("intermediate_translation") is False
        assert entry.get("analysis_path") in (None, "original_text")
    # فحص ساكن: لا استيراد شبكة في الحزمة أصلًا
    pkg_dir = os.path.join(os.path.dirname(__file__), "..", "multilingual")
    for fn in os.listdir(pkg_dir):
        if fn.endswith(".py"):
            with open(os.path.join(pkg_dir, fn), encoding="utf-8") as fh:
                src = fh.read()
            for banned in ("import requests", "import urllib", "import http",
                           "socket.socket", "googleapis", "mymemory"):
                assert banned not in src, f"لا شبكة في المسار الأساسي: {fn}"


# ===========================================================================
# ١٣) الأداء: زمن استجابة مقبول تحت الحمل
# ===========================================================================

def test_performance_under_load():
    """R-838: النواة الدلالية زهيدة الكلفة مقابل دورة الوكيل (ثوانٍ).
    الحد 200ms/دور حارس انحدار صادق: محليًا القياس 21.4ms (هامش ~10×)
    لكن عمال CI المشتركة أبطأ 2-4× — الحد يظل يثبت أن الفهم الدلالي
    لا يضيف عمليًا شيئًا لزمن الرد (الأرقام المقيسة في تقرير الأداء)."""
    st = ConversationState()
    t0 = time.perf_counter()
    n = 300
    for i in range(n):
        st.process_user_message(f"أرسل أحمد التقرير رقم {i} إلى سارة", f"u{i}")
    elapsed = time.perf_counter() - t0
    per_turn_ms = elapsed / n * 1000
    assert per_turn_ms < 200, f"زمن الدور {per_turn_ms:.1f}ms يتجاوز 200ms (انحدار)"
    # حل الإحالات داخل الحمل كذلك
    t0 = time.perf_counter()
    for i in range(100):
        st.process_user_message("وهل وصلتها؟", f"f{i}")
    assert (time.perf_counter() - t0) / 100 * 1000 < 200


# ===========================================================================
# ١٤) الخصوصية: لا تسريب بيانات في السجلات أو الاسترجاع
# ===========================================================================

def test_privacy_no_leak_in_trace():
    secret_msg = "كلمة السر الخاصة بي هي Xy9$ecret"
    st = ConversationState()
    st.process_user_message(secret_msg, "u1")
    st.process_user_message("ما اسمك؟", "u2")
    trace_json = json.dumps(st.trace, ensure_ascii=False)
    assert "Xy9$ecret" not in trace_json, "سجل التتبع لا يحفظ المحتوى الحرفي"
    # الاسترجاع يعيد وحدات معنى بمصادرها لا نصوص خام بلا سياق
    for r in st.memory.retrieve(analyze("ما اسمك؟", "q")):
        assert "provenance" in r["unit"]


# ===========================================================================
# ١٥) العدائية: مدخلات ملتبسة/مشوشة/مختلطة ⇒ سلوك آمن متسق
# ===========================================================================

def test_adversarial_inputs():
    cases = ["", "؟؟؟", "!@#$%", "هو", "هي هي هي", "\x00\x01",
             "a" * 5000, "مرحبا 1234 !!", "ما ما ما ما", "الـ", "ـ",
             "أنا" * 500]
    for c in cases:
        st = ConversationState()
        out = st.process_user_message(c, "adv")   # لا استثناء أبدًا
        assert out["frame"] is not None
        assert out["frame"]["analysis_path"] == "original_text"
    # نص عربي محمّل بضمائر بلا كيانات ⇒ لا انهيار ولا اختيار صامت
    st = ConversationState()
    out = st.process_user_message("هو هو هم هم", "adv2")
    for r in out["frame"]["references"]:
        assert r.get("resolved_id") is None or r.get("ambiguous") is not None or \
            r.get("confidence", 0) > 0, "إما حل موثوق أو غموض معلن"


# ===========================================================================
# توافق الواجهة مع context_resolver القديم (عقد {original, standalone, followup, kind})
# ===========================================================================

def test_resolve_compat_interface():
    history = [{"role": "user", "content": "ما عاصمة اليابان؟"}]
    r = resolve("وكم عدد سكانها؟", history)
    assert r["original"] == "وكم عدد سكانها؟"
    assert r["followup"] is True
    assert "اليابان" in r["standalone"], "السؤال القائم بذاته يحمل الكيان"
    assert r["kind"] in ("semantic", "ellipsis_resolved")


def test_verb_with_object_pronoun_never_mangled():
    """R-838 (عودة): «تعجبني» فعل + مفعول «ني» — لا يُقطع الفعل ولا
    يُخلق كيان وهمي من جذره («تعجبن») ولا يكرر السياق إن ذُكر الكيان."""
    history = [{"role": "user", "content": "اليابان بلد جميل وسكانها مهذبون."},
               {"role": "assistant", "content": "رائع!"}]
    r = resolve("تعجبني كثيرًا", history)
    assert "تعجبني" in r["standalone"], "الفعل يبقى كاملًا غير مبتور"
    assert "تعجبن " not in r["standalone"], "لا كيان وهمي من جذر الفعل"
    # الفاعل المحذوف يُسترجع من الجدول
    assert r["standalone"].startswith("اليابان تعجبني")
    r2 = resolve("هي تعجبني", history)
    assert r2["standalone"] == "اليابان تعجبني", "لا تكرار للسياق بعد الاستبدال"
    r3 = resolve("ما رأيك بسكانها؟", history)
    assert r3["standalone"] == "ما رأيك بسكان اليابان؟"


def test_url_entity_and_anaphora_direction():
    """R-838 (عودة): الرابط كيان كامل لا تمزقه التقطيعة، واتجاه الإحالة
    يمنع خطف الضمير باسم لاحق في نفس الرسالة («هل هو جاهز للانتاج؟»)."""
    history = [{"role": "user", "content":
               "اريد معلومات كامله عن المشروع المرفق https://github.com/vooovg-ui/AMOS-Fedration"}]
    r = resolve("هل هو جاهز للانتاج ؟", history)
    assert "https://github.com/vooovg-ui/AMOS-Fedration" in r["standalone"], \
        "«هو» تعود على المستودع المذكور قبلها لا على «للانتاج» اللاحق"
    # الإحالة داخل الرسالة نفسها ما تزال تعمل (اتجاه الإحالة لا يقتلها)
    h2 = [{"role": "user", "content": "اليابان بلد جميل."}]
    r2 = resolve("وكم عدد سكانها؟", h2)
    assert "اليابان" in r2["standalone"]


def test_speech_acts_and_intents():
    assert analyze("ما عاصمة اليابان؟")["intent"]["label"] == "question"
    assert analyze("لخص الرد السابق")["intent"]["label"] == "request"
    assert analyze("اشرح أكثر")["intent"]["label"] == "request_more"
    assert analyze("The weather is nice today")["intent"]["label"] == "assertion"
    assert analyze("مرحبا")["intent"]["label"] == "greeting"
    # كشف اللغة
    d = detect("Bonjour, comment ça va?")
    assert d.languages[0] == "fr"
    d2 = detect("Hola, ¿cómo estás?")
    assert d2.languages[0] == "es"


def test_no_spurious_clarification_clear_request():
    """R-838.1 (عودة إنتاجية، لوحة المراقبة 2026-11-02): طلب واضح بلا غموض
    لا يولّد سؤالًا توضيحيًا وهميًا عند سقوط الطبقة اللغوية.

    الحالة الحرفية: «قم بتحليل المشروع واستكشافه واعطني عنه تحليل مفصل
    <رابط>» — سأل النظام «بأيٍّ تقصد بتحليل أم المشروع؟» رغم وضوح الطلب.
    العلل الثلاث المصلحة: (١) حداثة موقعية داخل الدور — أقرب مذكور سابق
    يفوز («واستكشافه» على «المشروع» المفعول المباشر لا «بتحليل»)،
    (٢) ضمائر المتكلم/المخاطب («واعطني») لا تنافس كيانات الجدول إطلاقًا،
    (٣) «اعطني» فعل أمر+«ني» لا كيان مشوه «واعطن» يخطف «عنه».
    """
    r = resolve("قم بتحليل المشروع واستكشافه واعطني عنه تحليل مفصل "
                "https://github.com/helallao/perplexity-ai")
    assert r["clarification"] is None, \
        "طلب واضح بلا غموض حقيقي — لا سؤال توضيحي وهمي"
    assert "المشروع" in r["standalone"], \
        "«واستكشافه» و«عنه» تعودان على المشروع المفعول المباشر"
    # «واعطني» مفعولها المتكلم — لا تُسند لكيان
    for ref in r["frame"]["references"]:
        if ref.get("person") in ("1", "2"):
            assert not ref.get("candidate_entity_ids"), \
                "ضمائر المتكلم/المخاطب لا تنافس كيانات الجدول"
            assert ref.get("resolved_to") in ("speaker", "listener")
