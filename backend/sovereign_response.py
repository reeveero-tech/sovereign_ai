"""
Sovereign Response Engine (R-614 / S-9)
=======================================
محرك ردود سيادي حقيقي — يبني الردود من حالة النظام الفعلية، لا من قوالب ثابتة.

المبدأ: كل رد يستند إلى بيانات حية (ذاكرة، تنبؤات، مخاطر، محاكاة، وعي، متحكم سيادي)
ويُرفق دليلاً (evidence) قابلاً للتحقق. لا يدّعي ذكاءً غير موجود — يقرأ الحالة
الحقيقية ويصوغها بلغة السيد.

الوظائف:
- build_reply(intent, text, orchestrator_result) → رد مبني على حالة حية
- gather_evidence() → لقطة من الحالة الحالية (ذاكرة + تنبؤ + مخاطر + محاكاة + سيادة)
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sovereign.response")

# ============================================================
# جمع الأدلة الحية — كلها try/except: لا ينهار الرد أبداً
# ============================================================

def _safe(fn, default=None):
    """تنفيذ آمن لأي getter — أي خطأ يعيد القيمة الافتراضية."""
    try:
        return fn()
    except Exception as e:
        logger.debug(f"evidence getter failed: {e}")
        return default


def _gated(orchestrator, component: str) -> bool:
    """R-692 (اعتراض المراجع ج5): بوابة عزل مسار الرد — المعزول (أو الحالة
    المجهولة) لا يُستدعى من بناء الرد؛ الأداة الآمنة تعيد False فتُتخطى
    الشهادة ويبقى الرد يُبنى (التطبيق حي)."""
    if orchestrator is None:
        return True  # لا منسق متاح (مسار قديم) — سلوك سابق
    try:
        return bool(orchestrator._use(component))
    except Exception:
        return False  # تعذر الفحص — منع (لا إذنًا صامتًا)


def gather_evidence(orchestrator: Any = None) -> Dict[str, Any]:
    """لقطة من الحالة الحالية للنظام — أساس كل رد حقيقي. R-692: كل مكوّن
    يُجمع استشارته عبر بوابة عزله (المعزول/المجهول → الشهادة متخطاة، لا
    استدعاء) — المنع قبل استعمال المرجع في مسار الرد أيضًا."""
    evidence: Dict[str, Any] = {"timestamp": time.time()}

    # الذاكرة
    if _gated(orchestrator, "memory"):
        try:
            from memory.core import get_core
            core = get_core()
            stats = _safe(core.get_statistics, {})
            evidence["memory"] = {
                "total_events": stats.get("total_events", 0),
                "total_types": stats.get("total_types", 0),
                "total_users": stats.get("total_users", 0),
            }
        except Exception:
            evidence["memory"] = None
    else:
        evidence["memory"] = None

    # التنبؤ (ومدير المخاطر من منظومته)
    if _gated(orchestrator, "predictive"):
        try:
            from predictive.predictive_engine import get_predictive_engine
            engine = get_predictive_engine()
            status = _safe(engine.get_prediction_status, {})
            evidence["predictive"] = {
                "active_predictions": status.get("active_predictions", 0),
                "overall_risk": status.get("overall_risk", 0.5),
                "overall_opportunity": status.get("overall_opportunity", 0.5),
                "avg_accuracy": status.get("avg_accuracy", 0.5),
            }
        except Exception:
            evidence["predictive"] = None
        try:
            from predictive.predictive_risk_manager import get_predictive_risk_manager
            risk = get_predictive_risk_manager()
            rstatus = _safe(risk.get_risk_status, {})
            evidence["risk"] = {
                "active_risks": rstatus.get("active_risks", 0),
                "high_priority_risks": rstatus.get("high_priority_risks", 0),
                "overall_risk_level": rstatus.get("overall_risk_level", "low"),
                "early_warnings": rstatus.get("early_warnings", 0),
            }
        except Exception:
            evidence["risk"] = None
    else:
        evidence["predictive"] = None
        evidence["risk"] = None

    # المحاكاة
    if _gated(orchestrator, "simulation"):
        try:
            from predictive.predictive_simulation import get_predictive_simulation
            sim = get_predictive_simulation()
            sstatus = _safe(sim.get_simulation_results, {})
            agg = sstatus.get("aggregated_stats", {}) if sstatus else {}
            evidence["simulation"] = {
                "batch_id": sstatus.get("batch_id", ""),
                "avg_success_rate": agg.get("avg_success_rate", 0),
                "recommended_actions": len(sstatus.get("recommended_actions", [])),
            }
        except Exception:
            evidence["simulation"] = None
    else:
        evidence["simulation"] = None

    # المتحكم السيادي
    if _gated(orchestrator, "sovereign"):
        try:
            from sovereign.controller import get_sovereign_controller
            controller = get_sovereign_controller()
            cstatus = _safe(controller.get_controller_status, {})
            evidence["sovereign"] = {
                "system_mode": cstatus.get("system_mode", "normal"),
                "system_health": cstatus.get("system_health", 0.8),
                "global_priority": cstatus.get("global_priority", 0.7),
                "current_decision": cstatus.get("current_decision", {}),
            }
        except Exception:
            evidence["sovereign"] = None
    else:
        evidence["sovereign"] = None

    # الوعي
    if _gated(orchestrator, "consciousness"):
        try:
            from consciousness.field import get_consciousness_field
            field = get_consciousness_field()
            fstatus = _safe(field.get_consciousness_status, {})
            evidence["consciousness"] = {
                "coherence": fstatus.get("coherence", 0) if isinstance(fstatus, dict) else 0,
                "active": bool(fstatus) if fstatus else False,
            }
        except Exception:
            evidence["consciousness"] = None
    else:
        evidence["consciousness"] = None

    return evidence


# ============================================================
# صياغة الردود — كل رد مبني على أدلة حية
# ============================================================

def _pct(x: float) -> str:
    return f"{round(x * 100, 1)}%"


def _health_label(h: float) -> str:
    if h >= 0.8:
        return "ممتازة"
    if h >= 0.6:
        return "جيدة"
    if h >= 0.4:
        return "متوسطة"
    return "منخفضة"


def _risk_label(level) -> str:
    if isinstance(level, str):
        return {"low": "منخفض", "medium": "متوسط", "high": "مرتفع", "critical": "حرج"}.get(level, level)
    return str(level)


def _llm_reply(intent_name: str, text: str, ev: Dict[str, Any], history=None,
               tool_context: str = "") -> Optional[str]:
    """R-704: الرد عبر عقل Ollama المحلي إن كان مفعّلًا — سقوط آمن للقوالب.

    النموذج يولّد النص فقط: يُرسل له سياق مسموح (النية المكتشفة + لقطة
    الحالة الحية المدمجة أدناه) — لا كائن المنسق ولا أي صلاحية تنفيذ.
    معطل افتراضيًا (OLLAMA_ENABLED=False) — لا اتصال ضمني إلا بضبط صريح.
    """
    try:
        import config as _config
        if not (_config.OLLAMA_ENABLED and _config.OLLAMA_MODEL):
            return None
        import ollama_client
        # R-786: كان النص «استند فقط إلى حالة النظام» فيرفض النموذج الأسئلة العامة
        # أو يحشوها بأرقام النظام، وكان يخلط حروفًا صينية (مشاهد حيًا: «ي模仿»).
        # الآن: معرفة عامة مسموحة، الحالة الحية مرجع أسئلة النظام وحدها، ولغة واحدة.
        system_prompt = (
            "أنت 'الذكاء السيادي' — مساعد شخصي ذاتي الاستضافة لمالكك. "
            "أجب عن أي سؤال بمعرفتك العامة بوضوح وإيجاز وبتنظيم (نقاط عند الحاجة). "
            "اكتب بالعربية الفصحى فقط إلا إن كتب السيد بلغة أخرى فأجب بلغته، "
            "ولا تستخدم أبدًا حروفًا صينية أو يابانية أو كورية. "
            "عند السؤال عن النظام نفسه أو قدراته استند فقط إلى حالة النظام الحية أدناه "
            "ولا تدّعِ بيانات أو قدرات ليست فيها؛ ولا تذكر أرقام النظام في غير ذلك. "
            f"النية المكتشفة للرسالة: {intent_name or 'غير محددة'}."
        )
        system_prompt += "\nحالة النظام الحية (JSON):\n" + json.dumps(
            ev, ensure_ascii=False, default=str
        )
        # R-787: الهوية الحقيقية — النموذج ليس هو المشروع، بل «عقله اللغوي» فقط
        system_prompt += (
            "\nهويتك الحقيقية: أنت واجهة محادثة مشروع sovereign_ai (نظام سيادي ذاتي الاستضافة "
            "بسجل موقّع غير قابل للمحو، وذاكرة دائمة، وأدوات مسجلة). النموذج اللغوي "
            f"«{_config.OLLAMA_MODEL}» هو عقلك اللغوي فقط وليس هويتك. "
            "النظام يستدعي أدواته الحقيقية قبل أن يصلك السؤال: جرد القدرات الحي، وقراءة "
            "الروابط ومستودعات GitHub العامة. إن وُجدت أدناه «نتائج أدوات النظام» فهي محتوى "
            "حقيقي جُلب الآن — حلّله واستند إليه، ولا تقل أبدًا إنك لا تستطيع الوصول إلى "
            "الإنترنت أو إلى الرابط. إن لم توجد نتائج لرابط فقل إن القراءة لم تتم ولا تختلق."
        )
        if tool_context:
            system_prompt += "\nنتائج أدوات النظام (حقيقية، جُلبت الآن):\n" + tool_context
        if history:
            return ollama_client.chat(system_prompt, text, history=history)
        return ollama_client.chat(system_prompt, text)
    except Exception:
        # العقل مكمّل لا أساس — أي خلل يعيد القوالب القائمة
        return None


def build_reply(
    intent_name: str, text: str, orchestrator_result: Any = None,
    orchestrator: Any = None,
    history: Any = None,
    tool_context: str = "",
) -> str:
    """
    بناء رد حقيقي مبني على حالة النظام الحية.
    intent_name: النية المكتشفة (greet/help/status/analyze/forecast/alert/stop/...)
    text: نص السيد الأصلي
    orchestrator_result: نتيجة دورة المنسق (اختياري — تُستخدم إن وُجدت)
    """
    ev = gather_evidence(orchestrator)
    mem = ev.get("memory") or {}
    pred = ev.get("predictive") or {}
    risk = ev.get("risk") or {}
    sim = ev.get("simulation") or {}
    sov = ev.get("sovereign") or {}
    con = ev.get("consciousness") or {}

    # القرار من دورة المنسق إن وُجد
    decision_action = None
    if orchestrator_result is not None:
        try:
            decision_action = (orchestrator_result.decision or {}).get("action")
        # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
        except Exception:
            pass

    # R-704: عقل Ollama المحلي إن فُعّل — نص النموذج هو الرد؛
    # عند التعطل أو التعطيل تسقط المسارات القالبية القائمة أدناه كما هي
    _kw = {}
    if history:
        _kw["history"] = history
    if tool_context:
        _kw["tool_context"] = tool_context  # R-787: نتائج أدوات النظام الحقيقية
    llm = _llm_reply(intent_name, text, ev, **_kw)
    if llm:
        return llm

    # --- تحية: رد شخصي بحالة النظام ---
    if intent_name == "greet":
        health = _health_label(sov.get("system_health", 0.8))
        events = mem.get("total_events", 0)
        line = f"أهلاً بك. أنا الذكاء السيادي — جاهز لخدمتك."
        if events:
            line += f" سجلت {events} حدثاً في ذاكرتي، وصحة النظام {health}."
        if pred:
            line += f" لدي {pred.get('active_predictions', 0)} تنبؤاً نشطاً بدقة {_pct(pred.get('avg_accuracy', 0.5))}."
        return line

    # --- حالة النظام: أرقام حقيقية ---
    if intent_name == "status":
        lines = ["حالة النظام الحالية (من بيانات حية):"]
        if mem:
            lines.append(f"• الذاكرة: {mem.get('total_events', 0)} حدثاً، {mem.get('total_types', 0)} نوعاً")
        if pred:
            lines.append(f"• التنبؤ: {pred.get('active_predictions', 0)} نشطاً، دقة {_pct(pred.get('avg_accuracy', 0.5))}")
        if risk:
            lines.append(f"• المخاطر: {risk.get('active_risks', 0)} نشطة ({risk.get('high_priority_risks', 0)} عالية الأولوية)، المستوى {_risk_label(risk.get('overall_risk_level'))}")
        if sim:
            lines.append(f"• المحاكاة: معدل نجاح {_pct(sim.get('avg_success_rate', 0))}، {sim.get('recommended_actions', 0)} توصية")
        if sov:
            lines.append(f"• المتحكم السيادي: وضع {sov.get('system_mode', 'normal')}، صحة {_health_label(sov.get('system_health', 0.8))}")
        if con:
            lines.append(f"• الوعي: {'نشط' if con.get('active') else 'خامل'}")
        if decision_action:
            lines.append(f"• آخر قرار: {decision_action}")
        return "\n".join(lines)

    # --- تحليل: من التنبؤ والمحاكاة ---
    if intent_name == "analyze":
        lines = ["التحليل (من التنبؤ والمحاكاة الحية):"]
        if pred:
            lines.append(f"• المخاطر الكلية {_pct(pred.get('overall_risk', 0.5))} مقابل فرصة {_pct(pred.get('overall_opportunity', 0.5))}")
        if risk:
            lines.append(f"• {risk.get('active_risks', 0)} خطراً نشطاً، {risk.get('early_warnings', 0)} إنذاراً مبكراً")
        if sim:
            lines.append(f"• المحاكاة: نجاح {_pct(sim.get('avg_success_rate', 0))}، {sim.get('recommended_actions', 0)} توصية جاهزة")
        if not lines[1:]:
            lines.append("• لا توجد بيانات تحليل كافية بعد — شغّل دورة أولاً.")
        return "\n".join(lines)

    # --- تنبؤ: أرقام التنبؤ الحية ---
    if intent_name == "forecast":
        if not pred:
            return "لا توجد تنبؤات نشطة بعد. أرسل رسالة لبدء دورة تنبؤ."
        return (
            f"التنبؤ الحالي: {pred.get('active_predictions', 0)} تنبؤاً نشطاً "
            f"بدقة {_pct(pred.get('avg_accuracy', 0.5))}. "
            f"المخاطر الكلية {_pct(pred.get('overall_risk', 0.5))}، "
            f"الفرصة {_pct(pred.get('overall_opportunity', 0.5))}."
        )

    # --- تنبيه: المخاطر العالية ---
    if intent_name == "alert":
        if risk and risk.get("high_priority_risks", 0) > 0:
            return (
                f"⚠️ تنبيه: {risk.get('high_priority_risks', 0)} خطراً عالي الأولوية نشطاً. "
                f"المستوى الكلي {_risk_label(risk.get('overall_risk_level'))}. "
                f"أوصي بمراجعة خطة التخفيف فوراً."
            )
        return f"لا توجد مخاطر عالية حالياً — المستوى {_risk_label(risk.get('overall_risk_level', 'low'))}."

    # --- مساعدة: قدرات حقيقية ---
    if intent_name == "help":
        return (
            "يمكنني: قراءة حالة النظام (status)، تحليل التنبؤ والمخاطر (analyze)، "
            "التنبؤ بالمستقبل (forecast)، مراقبة التنبيهات (alert)، "
            "وتنفيذ قرارات المتحكم السيادي. كل رد مبني على بيانات حية."
        )

    # --- إيقاف ---
    if intent_name == "stop":
        return "تم استلام أمر الإيقاف. سأوقف دورة المعالجة الحالية."

    # --- افتراضي: رد مبني على القرار الفعلي ---
    if decision_action:
        return f"تم تنفيذ القرار: {decision_action}."
    return "تم استلام رسالتك. أنا الذكاء السيادي، جاهز لخدمتك."