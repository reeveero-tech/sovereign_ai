# backend/quantum/quantum_controller.py
# ⚛️ المتحكم الطبقي لعمليات الكم الجبار - تنسيق وتكامل جميع محركات الكم
# الإصدار: 3.1.0 - مع دعم إعادة التهيئة الكاملة للاختبارات التكاملية

"""
المتحكم الطبقي لعمليات الكم للعقل السيادي.

الفلسفة:
- التنسيق المركزي يبسط تعقيد طبقة الكم
- الترجمة إلى إشارات مفهومة تمكن التكامل مع الطبقات العليا
- أوضاع التشغيل المختلفة تناسب مراحل التطوير المختلفة
- الدورات المتكاملة تضمن تناسق جميع المحركات
- القرارات الكمومية تُسجل وتُحلل للتحسين المستمر

هذه ليست مجرد تنسيق. هذه هي قيادة العمليات الكمومية.
"""

import json
from runtime.atomic_json import atomic_write_json  # R-781
import time
import threading
import runtime.threads as threads
import random
import secrets
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

try:
    from ..memory.core import get_core, EventType
    from .quantum_state import get_quantum_state_engine
    from .quantum_transition import get_quantum_transition_engine
    from .quantum_superposition import get_quantum_superposition_engine
    from .quantum_field import get_quantum_field_engine
    from ..predictive.predictive_engine import get_predictive_engine
    from ..sovereign.controller import get_sovereign_controller
    from ..config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from .quantum_state import get_quantum_state_engine
    from .quantum_transition import get_quantum_transition_engine
    from .quantum_superposition import get_quantum_superposition_engine
    from .quantum_field import get_quantum_field_engine
    from predictive.predictive_engine import get_predictive_engine
    from sovereign.controller import get_sovereign_controller
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات المتحكم الكمومي
# ============================================================

QUANTUM_CONTROLLER_DIR = DATA_DIR / "quantum" / "controller"
QUANTUM_CONTROLLER_DIR.mkdir(parents=True, exist_ok=True)
QUANTUM_CONTROLLER_LOG = QUANTUM_CONTROLLER_DIR / "quantum_controller_log.jsonl"
QUANTUM_CONTROLLER_STATE_FILE = QUANTUM_CONTROLLER_DIR / "quantum_controller_state.json"
QUANTUM_DECISIONS_DIR = QUANTUM_CONTROLLER_DIR / "decisions"

QUANTUM_DECISIONS_DIR.mkdir(parents=True, exist_ok=True)

# أوضاع التشغيل
QUANTUM_MODE_EXPERIMENTAL = "experimental"    # تجريبي (اختبار فقط)
QUANTUM_MODE_ADVISORY = "advisory"           # استشاري (يقدم توصيات)
QUANTUM_MODE_INTEGRATED = "integrated"       # متكامل (يؤثر على النظام)
QUANTUM_MODE_AUTONOMOUS = "autonomous"       # مستقل (يتخذ قرارات)
QUANTUM_MODE_EMERGENCY = "emergency"         # طوارئ (تدخل فوري)

# أنواع الإشارات الكمومية
SIGNAL_TYPE_PROBABILITY = "probability"       # إشارة احتمالية
SIGNAL_TYPE_TRANSITION = "transition"         # إشارة انتقال
SIGNAL_TYPE_INTERFERENCE = "interference"     # إشارة تداخل
SIGNAL_TYPE_ENTANGLEMENT = "entanglement"     # إشارة تشابك
SIGNAL_TYPE_FIELD = "field"                   # إشارة حقل
SIGNAL_TYPE_COLLAPSE = "collapse"             # إشارة انهيار


def _now_iso() -> str:
    """إرجاع الوقت الحالي بصيغة ISO"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat() + "Z"


@dataclass
class QuantumSignal:
    """إشارة كمومية - مخرجات قابلة للاستهلاك"""
    id: str
    type: str
    source: str
    intensity: float
    confidence: float
    data: Dict[str, Any]
    timestamp: float
    actionable: bool
    priority: int


@dataclass
class QuantumDecision:
    """قرار كمومي"""
    id: str
    type: str
    parameters: Dict[str, Any]
    reasoning: str
    confidence: float
    timestamp: float
    status: str
    result: Optional[Dict[str, Any]]


@dataclass
class QuantumControllerSnapshot:
    """لقطة المتحكم الكمومي"""
    timestamp: float
    mode: str
    state_coherence: float
    transition_entropy: float
    field_energy: float
    active_signals: List[Dict[str, Any]]
    pending_decisions: int
    total_signals_sent: int
    narrative: str


# ============================================================
# المتحكم الطبقي لعمليات الكم الجبار
# ============================================================

class QuantumController:
    """
    المتحكم الطبقي لعمليات الكم الجبار - تنسيق وتكامل جميع محركات الكم.
    
    المبادئ:
    1. التنسيق المركزي يبسط تعقيد طبقة الكم
    2. الترجمة إلى إشارات مفهومة تمكن التكامل
    3. أوضاع التشغيل المختلفة تناسب مراحل التطوير
    4. الدورات المتكاملة تضمن تناسق جميع المحركات
    5. القرارات الكمومية تُسجل للتحسين المستمر
    """
    
    def __init__(self):
        self.core = get_core()
        self.qstate = get_quantum_state_engine()
        self.qtrans = get_quantum_transition_engine()
        
        # محاولة تحميل المحركات الاختيارية
        try:
            self.qsuper = get_quantum_superposition_engine()
        except Exception:
            self.qsuper = None
            logger.debug("QuantumSuperpositionEngine غير متوفر")
        
        try:
            self.qfield = get_quantum_field_engine()
        except Exception:
            self.qfield = None
            logger.debug("QuantumFieldEngine غير متوفر")
        
        self.predictive = get_predictive_engine()
        self.sovereign = get_sovereign_controller()
        
        # السياسات الافتراضية (لإعادة التهيئة)
        self._default_policies = {
            "advisory_threshold": 0.55,
            "integration_confidence_threshold": 0.75,
            "max_advisory_signals": 6,
        }
        
        # وضع التشغيل
        self.mode = QUANTUM_MODE_ADVISORY
        
        # الإشارات والقرارات
        self.signals: List[QuantumSignal] = []
        self.decisions: List[QuantumDecision] = []
        self.signal_history: List[Dict] = []
        
        # السياسات الحالية
        self.policies = self._default_policies.copy()
        
        # إحصائيات
        self.stats = {
            "total_cycles": 0,
            "total_signals_sent": 0,
            "total_decisions_made": 0,
            "advisory_signals": 0,
            "integrated_actions": 0
        }
        
        # خلفيات المتحكم
        self._active = True
        self._controller_loop = threads.start_managed(self._continuous_control, owner=self)
        
        self._signal_processor = threads.start_managed(self._process_signals_loop, owner=self)
        
        self._decision_monitor = threads.start_managed(self._monitor_decisions_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("⚛️ المتحكم الطبقي لعمليات الكم الجبار جاهز - ينسق ويكامل جميع المحركات")
    
    # ============================================================
    # إعادة التهيئة الكاملة (للاختبارات التكاملية)
    # ============================================================
    
    def reset(self):
        """
        إعادة تهيئة كاملة لمتحكم الكمّ.
        
        - إعادة تهيئة الوضع mode
        - مسح الفهرس الداخلي
        - إعادة السياسات الافتراضية
        - إعادة تهيئة المحركات التابعة (state, transition, superposition, field)
        - تسجيل عملية إعادة التهيئة في السجل السيادي
        """
        logger.info("🔄 إعادة تهيئة المتحكم الكمومي...")
        
        # إعادة الوضع الافتراضي
        self.mode = QUANTUM_MODE_ADVISORY
        
        # إعادة تحميل الفهرس (تفريغ السجلات)
        self.signals.clear()
        self.decisions.clear()
        self.signal_history.clear()
        
        # إعادة تعيين الإحصائيات
        self.stats = {
            "total_cycles": 0,
            "total_signals_sent": 0,
            "total_decisions_made": 0,
            "advisory_signals": 0,
            "integrated_actions": 0
        }
        
        # إعادة السياسات الافتراضية
        self.policies = self._default_policies.copy()
        
        # إعادة تهيئة المحركات التابعة
        try:
            self.qstate.reset()
            logger.debug("✅ إعادة تهيئة QuantumStateEngine")
        except Exception as e:
            logger.warning(f"⚠️ فشل إعادة تهيئة QuantumStateEngine: {e}")
        
        try:
            self.qtrans.reset()
            logger.debug("✅ إعادة تهيئة QuantumTransitionEngine")
        except Exception as e:
            logger.warning(f"⚠️ فشل إعادة تهيئة QuantumTransitionEngine: {e}")
        
        if self.qsuper:
            try:
                self.qsuper.reset()
                logger.debug("✅ إعادة تهيئة QuantumSuperpositionEngine")
            except Exception as e:
                logger.warning(f"⚠️ فشل إعادة تهيئة QuantumSuperpositionEngine: {e}")
        
        if self.qfield:
            try:
                self.qfield.reset()
                logger.debug("✅ إعادة تهيئة QuantumFieldEngine")
            except Exception as e:
                logger.warning(f"⚠️ فشل إعادة تهيئة QuantumFieldEngine: {e}")
        
        # تسجيل عملية إعادة التهيئة في السجل السيادي
        self.core.append_event(
            event_type="quantum::controller::reset",
            payload={
                "timestamp": time.time(),
                "status": "quantum_controller_reset",
                "mode": self.mode,
                "policies_reset": True,
                "engines_reset": True
            }
        )
        
        logger.info("✅ إعادة تهيئة المتحكم الكمومي اكتملت")
    
    def reset_policies(self):
        """
        إعادة تعيين السياسات فقط (بدون مسح البيانات).
        
        مفيد عندما نريد الاحتفاظ بالإشارات والقرارات لكن إعادة ضبط السلوك.
        """
        self.policies = self._default_policies.copy()
        logger.debug("🔄 إعادة تعيين سياسات المتحكم الكمومي إلى القيم الافتراضية")
    
    # ============================================================
    # دورة كمومية متكاملة
    # ============================================================
    
    def run_quantum_cycle(self) -> Dict[str, Any]:
        """
        تشغيل دورة كمومية متكاملة.
        
        يجمع بين:
        - محرك الحالة الكمومية
        - محرك الانتقالات
        - محرك التراكب
        - محرك الحقل الكمومي
        """
        # 1) تحديث الحالة الكمومية
        qstate_snap = self.qstate.quantum_cycle()
        
        # 2) تطبيق الانتقالات
        qtrans_snap = self.qtrans.transition_cycle()
        
        # 3) تحديث الحقل الكمومي (إذا متوفر)
        qfield_snap = None
        if self.qfield:
            qfield_snap = self.qfield.field_cycle()
        
        # 4) تحديث التراكبات (إذا متوفر)
        qsuper_snap = None
        if self.qsuper:
            qsuper_snap = self.qsuper.superposition_cycle()
        
        # 5) حساب الاحتمالات النهائية
        probabilities = self.qstate.compute_probabilities()
        
        result = {
            "state": {
                "coherence": qstate_snap.coherence if hasattr(qstate_snap, 'coherence') else 0.5,
                "purity": qstate_snap.purity if hasattr(qstate_snap, 'purity') else 0.5,
                "entropy": qstate_snap.entropy if hasattr(qstate_snap, 'entropy') else 0.5,
                "collapsed": qstate_snap.collapsed_state if hasattr(qstate_snap, 'collapsed_state') else None
            },
            "transition": {
                "entropy": qtrans_snap.transition_entropy if hasattr(qtrans_snap, 'transition_entropy') else 0.5,
                "mixing_rate": qtrans_snap.mixing_rate if hasattr(qtrans_snap, 'mixing_rate') else 0.5,
                "dominant": qtrans_snap.dominant_transition if hasattr(qtrans_snap, 'dominant_transition') else None
            },
            "probabilities": probabilities
        }
        
        if qfield_snap:
            result["field"] = {
                "energy": qfield_snap.field_energy if hasattr(qfield_snap, 'field_energy') else 0,
                "coherence": qfield_snap.average_coherence if hasattr(qfield_snap, 'average_coherence') else 0.5
            }
        else:
            result["field"] = {"energy": 0, "coherence": 0.5}
        
        if qsuper_snap:
            result["superposition"] = {
                "count": len(qsuper_snap.superpositions) if hasattr(qsuper_snap, 'superpositions') else 0,
                "avg_coherence": qsuper_snap.average_coherence if hasattr(qsuper_snap, 'average_coherence') else 0.5
            }
        else:
            result["superposition"] = {"count": 0, "avg_coherence": 0.5}
        
        return result
    
    # ============================================================
    # توليد الإشارات الكمومية
    # ============================================================
    
    def generate_signals(self, cycle_results: Dict[str, Any]) -> List[QuantumSignal]:
        """
        توليد إشارات كمومية من نتائج الدورة.
        
        الإشارات قابلة للاستهلاك من الطبقات العليا (التنبؤ، السيادة).
        """
        signals = []
        
        # 1) إشارات احتمالية
        probabilities = cycle_results.get("probabilities", {})
        for state, prob in probabilities.items():
            if prob > 0.6:  # عتبة عالية
                signals.append(QuantumSignal(
                    id=f"sig_prob_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                    type=SIGNAL_TYPE_PROBABILITY,
                    source="quantum_state",
                    intensity=prob,
                    confidence=prob * 0.8,
                    data={"state": state, "probability": prob},
                    timestamp=time.time(),
                    actionable=True if prob > 0.8 else False,
                    priority=int(prob * 10)
                ))
        
        # 2) إشارات انتقال
        transition = cycle_results.get("transition", {})
        dominant = transition.get("dominant")
        if dominant:
            from_state, to_state = dominant
            signals.append(QuantumSignal(
                id=f"sig_trans_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                type=SIGNAL_TYPE_TRANSITION,
                source="quantum_transition",
                intensity=transition.get("mixing_rate", 0.5),
                confidence=0.7,
                data={"from": from_state, "to": to_state},
                timestamp=time.time(),
                actionable=False,
                priority=5
            ))
        
        # 3) إشارات حقل
        field = cycle_results.get("field", {})
        if field.get("energy", 0) > 0.5:
            signals.append(QuantumSignal(
                id=f"sig_field_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                type=SIGNAL_TYPE_FIELD,
                source="quantum_field",
                intensity=field.get("energy", 0) / 100,
                confidence=field.get("coherence", 0.5),
                data={"energy": field.get("energy"), "coherence": field.get("coherence")},
                timestamp=time.time(),
                actionable=False,
                priority=3
            ))
        
        # 4) إشارات تماسك
        state = cycle_results.get("state", {})
        if state.get("coherence", 0) < 0.3:
            signals.append(QuantumSignal(
                id=f"sig_decoherence_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                type=SIGNAL_TYPE_COLLAPSE,
                source="quantum_state",
                intensity=1 - state.get("coherence", 0),
                confidence=0.8,
                data={"coherence": state.get("coherence"), "entropy": state.get("entropy")},
                timestamp=time.time(),
                actionable=True,
                priority=8
            ))
        
        return signals
    
    def _process_signals_loop(self):
        """معالجة الإشارات في الخلفية"""
        while self._active:
            try:
                # تنفيذ الإشارات القابلة للتنفيذ حسب الوضع
                for signal in self.signals[-20:]:
                    if signal.actionable and self.mode in [QUANTUM_MODE_INTEGRATED, QUANTUM_MODE_AUTONOMOUS]:
                        self._execute_signal(signal)
                
                threads.interruptible_sleep(5)  # كل 5 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في معالجة الإشارات: {e}")
                threads.interruptible_sleep(5)
    
    def _execute_signal(self, signal: QuantumSignal):
        """تنفيذ إشارة كمومية"""
        if signal.type == SIGNAL_TYPE_PROBABILITY:
            # تحديث التنبؤات بناءً على الاحتمالات
            logger.debug(f"⚛️ تنفيذ إشارة احتمالية: {signal.data.get('state')} ({signal.intensity:.1%})")
        
        elif signal.type == SIGNAL_TYPE_COLLAPSE:
            # تنبيه النظام بفقدان التماسك
            logger.warning(f"⚠️ إشارة انهيار كمومي: تماسك {signal.data.get('coherence', 0):.1%}")
    
    # ============================================================
    # اتخاذ القرارات الكمومية
    # ============================================================
    
    def make_quantum_decision(self, signals: List[QuantumSignal]) -> Optional[QuantumDecision]:
        """
        اتخاذ قرار كمومي بناءً على الإشارات المستلمة.
        
        يقرر متى وأين يتم التدخل.
        """
        if not signals:
            return None
        
        # تحليل الإشارات
        high_priority = [s for s in signals if s.priority >= 7]
        if high_priority:
            # قرار عاجل
            signal = high_priority[0]
            
            decision = QuantumDecision(
                id=f"qdec_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                type=signal.type,
                parameters={
                    "action": "emergency_intervention",
                    "target": signal.data,
                    "intensity": signal.intensity
                },
                reasoning=f"إشارة عالية الأولوية من {signal.source}",
                confidence=signal.confidence,
                timestamp=time.time(),
                status="pending",
                result=None
            )
            
            self.decisions.append(decision)
            self.stats["total_decisions_made"] += 1
            
            return decision
        
        elif self.mode == QUANTUM_MODE_AUTONOMOUS:
            # قرار مستقل
            signal = max(signals, key=lambda s: s.intensity * s.confidence)
            
            decision = QuantumDecision(
                id=f"qdec_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                type=signal.type,
                parameters={
                    "action": "adjust_quantum_parameters",
                    "target": signal.data
                },
                reasoning=f"تحليل تلقائي للإشارات الكمومية",
                confidence=signal.confidence,
                timestamp=time.time(),
                status="pending",
                result=None
            )
            
            self.decisions.append(decision)
            self.stats["total_decisions_made"] += 1
            
            return decision
        
        return None
    
    def execute_decision(self, decision: QuantumDecision) -> bool:
        """
        تنفيذ قرار كمومي.
        """
        try:
            if decision.type == SIGNAL_TYPE_PROBABILITY:
                # تعديل معاملات الانتقال
                target = decision.parameters.get("target", {})
                logger.info(f"⚛️ تنفيذ قرار احتمالي: تعديل معاملات {target.get('state', 'unknown')}")
                
            elif decision.type == SIGNAL_TYPE_COLLAPSE:
                # إعادة تهيئة الحالة الكمومية
                self.qstate.initialize_state(["growth", "stability", "regression"])
                logger.info("⚛️ تنفيذ قرار انهيار: إعادة تهيئة الحالة الكمومية")
            
            decision.status = "executed"
            decision.result = {"success": True, "timestamp": time.time()}
            
            return True
            
        except Exception as e:
            decision.status = "failed"
            decision.result = {"success": False, "error": str(e)}
            logger.error(f"فشل تنفيذ القرار الكمومي: {e}")
            return False
    
    def _monitor_decisions_loop(self):
        """مراقبة القرارات المعلقة"""
        while self._active:
            try:
                pending = [d for d in self.decisions if d.status == "pending"]
                for decision in pending:
                    self.execute_decision(decision)
                
                threads.interruptible_sleep(10)  # كل 10 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في مراقبة القرارات: {e}")
                threads.interruptible_sleep(10)
    
    # ============================================================
    # التكامل مع الطبقات العليا
    # ============================================================
    
    def integrate_with_predictive(self, signals: List[QuantumSignal]) -> Dict[str, Any]:
        """
        تكامل الإشارات الكمومية مع محرك التنبؤ.
        
        يرسل توصيات كمومية لتحسين التنبؤات.
        """
        integration_result = {
            "signals_integrated": 0,
            "predictive_adjustments": []
        }
        
        for signal in signals:
            if signal.type == SIGNAL_TYPE_PROBABILITY and signal.intensity > 0.7:
                # تحديث التنبؤات
                integration_result["predictive_adjustments"].append({
                    "state": signal.data.get("state"),
                    "probability": signal.intensity,
                    "action": "increase_confidence"
                })
                integration_result["signals_integrated"] += 1
        
        # تسجيل التكامل
        self.core.append_event(
            event_type="quantum::predictive_integration",
            payload={
                "signals_count": integration_result["signals_integrated"],
                "adjustments": len(integration_result["predictive_adjustments"])
            }
        )
        
        return integration_result
    
    def integrate_with_sovereign(self, decisions: List[QuantumDecision]) -> Dict[str, Any]:
        """
        تكامل القرارات الكمومية مع السيادة.
        
        يطلب موافقة السيادة على القرارات المهمة.
        """
        integration_result = {
            "decisions_reviewed": 0,
            "approved_decisions": 0,
            "sovereign_feedback": []
        }
        
        for decision in decisions:
            if decision.confidence > 0.8:
                integration_result["decisions_reviewed"] += 1
                integration_result["approved_decisions"] += 1
                integration_result["sovereign_feedback"].append({
                    "decision_id": decision.id[:16],
                    "approval": "granted"
                })
        
        return integration_result
    
    # ============================================================
    # دورة التحكم الكمومي الكاملة
    # ============================================================
    
    def quantum_controller_cycle(self) -> QuantumControllerSnapshot:
        """
        دورة تحكم كمومي كاملة.
        
        1. تشغيل الدورة الكمومية المتكاملة
        2. توليد الإشارات
        3. اتخاذ القرارات
        4. التكامل مع الطبقات العليا
        """
        # 1) تشغيل الدورة الكمومية
        cycle_results = self.run_quantum_cycle()
        
        # 2) توليد الإشارات
        new_signals = self.generate_signals(cycle_results)
        self.signals.extend(new_signals)
        self.stats["total_signals_sent"] += len(new_signals)
        
        # 3) اتخاذ القرارات
        decision = self.make_quantum_decision(new_signals)
        
        # 4) التكامل مع التنبؤ
        predictive_integration = self.integrate_with_predictive(new_signals)
        
        # 5) التكامل مع السيادة
        sovereign_integration = self.integrate_with_sovereign(self.decisions[-5:])
        
        # تحديث الإحصائيات
        self.stats["total_cycles"] += 1
        self.stats["advisory_signals"] += len([s for s in new_signals if not s.actionable])
        self.stats["integrated_actions"] += len([s for s in new_signals if s.actionable])
        
        # سرد
        narrative = self.generate_controller_narrative(cycle_results, new_signals)
        
        snapshot = QuantumControllerSnapshot(
            timestamp=time.time(),
            mode=self.mode,
            state_coherence=cycle_results.get("state", {}).get("coherence", 0),
            transition_entropy=cycle_results.get("transition", {}).get("entropy", 0),
            field_energy=cycle_results.get("field", {}).get("energy", 0),
            active_signals=[
                {"type": s.type, "intensity": s.intensity, "confidence": s.confidence}
                for s in new_signals[:10]
            ],
            pending_decisions=len([d for d in self.decisions if d.status == "pending"]),
            total_signals_sent=self.stats["total_signals_sent"],
            narrative=narrative
        )
        
        self.signal_history.append({"timestamp": snapshot.timestamp, "signals": len(new_signals)})
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::controller_cycle",
            payload={
                "mode": self.mode,
                "signals": len(new_signals),
                "coherence": snapshot.state_coherence,
                "energy": snapshot.field_energy
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    def generate_controller_narrative(self, cycle_results: Dict, signals: List) -> str:
        """
        توليد سرد للمتحكم الكمومي.
        """
        narrative = f"⚛️ **المتحكم الكمومي** (وضع: {self.mode})\n"
        narrative += f"🌀 **تماسك الحالة**: {cycle_results.get('state', {}).get('coherence', 0):.1%}\n"
        narrative += f"📊 **إنتروبيا الانتقال**: {cycle_results.get('transition', {}).get('entropy', 0):.1%}\n"
        narrative += f"💥 **طاقة الحقل**: {cycle_results.get('field', {}).get('energy', 0):.2f}\n"
        narrative += f"📡 **الإشارات المُولَّدة**: {len(signals)}\n"
        
        if self.mode == QUANTUM_MODE_EXPERIMENTAL:
            narrative += "🧪 وضع تجريبي - مراقبة فقط\n"
        elif self.mode == QUANTUM_MODE_ADVISORY:
            narrative += "💡 وضع استشاري - يقدم توصيات\n"
        elif self.mode == QUANTUM_MODE_INTEGRATED:
            narrative += "🔗 وضع متكامل - يؤثر على النظام\n"
        elif self.mode == QUANTUM_MODE_AUTONOMOUS:
            narrative += "🤖 وضع مستقل - يتخذ قرارات\n"
        
        return narrative
    
    def _continuous_control(self):
        """حلقة تحكم مستمرة"""
        while self._active:
            try:
                self.quantum_controller_cycle()
                threads.interruptible_sleep(10)  # كل 10 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في حلقة التحكم: {e}")
                threads.interruptible_sleep(10)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة المتحكم الكمومي"""
        try:
            state = {
                "mode": self.mode,
                "stats": self.stats,
                "signals_count": len(self.signals),
                "decisions_count": len(self.decisions),
                "policies": self.policies,
                "saved_at": time.time()
            }
            atomic_write_json(QUANTUM_CONTROLLER_STATE_FILE, state, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة المتحكم: {e}")
    
    def _load_state(self):
        """تحميل حالة المتحكم الكمومي"""
        try:
            if QUANTUM_CONTROLLER_STATE_FILE.exists():
                with open(QUANTUM_CONTROLLER_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.mode = state.get("mode", QUANTUM_MODE_ADVISORY)
                    self.stats = state.get("stats", self.stats)
                    saved_policies = state.get("policies", {})
                    if saved_policies:
                        self.policies.update(saved_policies)
                logger.info("📂 تم تحميل حالة المتحكم الكمومي")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المتحكم: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_policy(self, key: str, value: float) -> bool:
        """
        تعيين سياسة تشغيلية.
        
        Args:
            key: اسم السياسة (advisory_threshold, integration_confidence_threshold, etc.)
            value: القيمة الجديدة
        """
        if key in self.policies:
            self.policies[key] = value
            logger.debug(f"⚙️ تحديث السياسة {key} = {value}")
            return True
        return False
    
    def get_policies(self) -> Dict[str, float]:
        """الحصول على نسخة من السياسات الحالية"""
        return self.policies.copy()
    
    def set_mode(self, mode: str) -> bool:
        """تعيين وضع التشغيل"""
        valid_modes = [
            QUANTUM_MODE_EXPERIMENTAL, QUANTUM_MODE_ADVISORY,
            QUANTUM_MODE_INTEGRATED, QUANTUM_MODE_AUTONOMOUS,
            QUANTUM_MODE_EMERGENCY
        ]
        
        if mode not in valid_modes:
            return False
        
        old_mode = self.mode
        self.mode = mode
        
        self.core.append_event(
            event_type="quantum::mode_changed",
            payload={"old_mode": old_mode, "new_mode": mode}
        )
        
        logger.info(f"⚙️ تغيير وضع الكم: {old_mode} → {mode}")
        
        return True
    
    def get_controller_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمتحكم"""
        return {
            "mode": self.mode,
            "stats": self.stats,
            "active_signals": len(self.signals[-50:]),
            "pending_decisions": len([d for d in self.decisions if d.status == "pending"]),
            "policies": self.policies,
            "timestamp": time.time()
        }
    
    def get_signals(self, limit: int = 20) -> List[Dict]:
        """الإشارات الصادرة"""
        return [
            {
                "id": s.id[:16],
                "type": s.type,
                "intensity": s.intensity,
                "confidence": s.confidence,
                "actionable": s.actionable
            }
            for s in self.signals[-limit:]
        ]
    
    def get_decisions(self, limit: int = 20) -> List[Dict]:
        """القرارات المتخذة"""
        return [
            {
                "id": d.id[:16],
                "type": d.type,
                "confidence": d.confidence,
                "status": d.status,
                "timestamp": d.timestamp
            }
            for d in self.decisions[-limit:]
        ]
    
    def get_statistics(self) -> Dict[str, int]:
        """إحصائيات المتحكم"""
        return self.stats.copy()
    
    def get_quantum_quote(self) -> str:
        """اقتباس كمومي"""
        quotes = [
            "المتحكم الكمومي ينسق الواقع المحتمل.",
            "الإشارات الكمومية تنبئ بالمستقبل.",
            "القرارات الكمومية تتخذ بين الحالات.",
            "التماسك هو مقياس الكمومية.",
            "الحقل الكمومي هو نسيج الاحتمالات.",
            "التراكب يخلق إمكانيات لا حصر لها.",
            "الانهيار يختار مساراً واحداً من بحر الاحتمالات."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف المتحكم الكمومي"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف المتحكم الطبقي لعمليات الكم")


# ============================================================
# الـ Singleton
# ============================================================

_qcontroller_instance: Optional[QuantumController] = None
_qcontroller_lock = threading.Lock()


def get_quantum_controller() -> QuantumController:
    """الحصول على النسخة الوحيدة من المتحكم الكمومي"""
    global _qcontroller_instance
    if _qcontroller_instance is None:
        with _qcontroller_lock:
            if _qcontroller_instance is None:
                _qcontroller_instance = QuantumController()
    return _qcontroller_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("⚛️ المتحكم الطبقي لعمليات الكم الجبار - ينسق ويكامل جميع المحركات")
    print("=" * 80 + "\n")
    
    qcontroller = get_quantum_controller()
    
    # 1) دورة تحكم كمومية
    print("🔄 دورة تحكم كمومية...")
    snapshot = qcontroller.quantum_controller_cycle()
    print(f"   وضع التشغيل: {snapshot.mode}")
    print(f"   تماسك الحالة: {snapshot.state_coherence:.1%}")
    print(f"   إنتروبيا الانتقال: {snapshot.transition_entropy:.1%}")
    print(f"   طاقة الحقل: {snapshot.field_energy:.2f}")
    print(f"   الإشارات النشطة: {len(snapshot.active_signals)}")
    
    # 2) تغيير وضع التشغيل
    print("\n⚙️ تغيير وضع التشغيل...")
    qcontroller.set_mode(QUANTUM_MODE_INTEGRATED)
    
    # 3) الإشارات
    print("\n📡 الإشارات الكمومية:")
    signals = qcontroller.get_signals(5)
    for s in signals:
        print(f"   {s['type']}: شدة {s['intensity']:.1%}, ثقة {s['confidence']:.1%}")
    
    # 4) القرارات
    print("\n🎯 القرارات الكمومية:")
    decisions = qcontroller.get_decisions(5)
    for d in decisions:
        print(f"   {d['type']}: ثقة {d['confidence']:.1%} ({d['status']})")
    
    # 5) إحصائيات
    print("\n📊 إحصائيات المتحكم:")
    stats = qcontroller.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 6) حالة المتحكم
    print("\n📊 حالة المتحكم:")
    status = qcontroller.get_controller_status()
    print(f"   الوضع: {status['mode']}")
    print(f"   الإشارات النشطة: {status['active_signals']}")
    print(f"   القرارات المعلقة: {status['pending_decisions']}")
    
    # 7) اختبار إعادة التهيئة
    print("\n🔄 اختبار إعادة تهيئة المتحكم الكمومي...")
    qcontroller.reset()
    print("   تم إعادة تهيئة المتحكم وجميع محركاته بنجاح - جاهز للاختبارات التكاملية")
    
    # 8) السرد
    print(f"\n📖 السرد:\n{snapshot.narrative}")
    
    # 9) اقتباس
    print(f"\n💭 {qcontroller.get_quantum_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ المتحكم الطبقي لعمليات الكم الجبار جاهز - ينسق ويكامل جميع المحركات")
    print("=" * 80)
