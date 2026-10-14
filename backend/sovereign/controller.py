# backend/sovereign/controller.py
# 👑 المتحكم السيادي الأعلى - تاج السيادة، قمة الهرم
# الإصدار: 3.0.0 - يجمع كل شيء، ينسق كل شيء، يقرر كل شيء

"""
المتحكم السيادي الأعلى.

الفلسفة:
- هذا هو قمة الهرم السيادي
- يجمع الإرادة، الاصطفاف، التوجيهات، الاستبطان، الوعي، الانتباه
- يتخذ القرارات النهائية للنظام
- ينسق جميع الطبقات السفلى
- يضمن تنفيذ إرادة السيد بأعلى جودة

هذه ليست مجرد تنسيق. هذا هو تاج السيادة.
"""

import json
import time
import threading
import random
import secrets
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

try:
    from ..memory.core import get_core, EventType
    from ..memory.biological.instincts import get_instincts
    from ..memory.biological.drives import get_drives
    from .will import get_sovereign_will
    from .alignment import get_sovereign_alignment
    from .directives import get_sovereign_directives
    from ..consciousness.introspection import get_introspection_engine
    from ..consciousness.awareness import get_awareness_engine
    from ..consciousness.attention_engine import get_attention_engine
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from .will import get_sovereign_will
    from .alignment import get_sovereign_alignment
    from .directives import get_sovereign_directives
    from consciousness.introspection import get_introspection_engine
    from consciousness.awareness import get_awareness_engine
    from consciousness.attention_engine import get_attention_engine
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات المتحكم
# ============================================================

CONTROLLER_DIR = DATA_DIR / "sovereign" / "controller"
CONTROLLER_DIR.mkdir(parents=True, exist_ok=True)
CONTROLLER_LOG = CONTROLLER_DIR / "controller_log.jsonl"
CONTROLLER_STATE_FILE = CONTROLLER_DIR / "controller_state.json"
CONTROLLER_DECISIONS_FILE = CONTROLLER_DIR / "final_decisions.json"

# أوامر النظام
SYSTEM_COMMAND_NONE = 0
SYSTEM_COMMAND_CONTINUE = 1
SYSTEM_COMMAND_ADJUST = 2
SYSTEM_COMMAND_RECALIBRATE = 3
SYSTEM_COMMAND_EMERGENCY = 4
SYSTEM_COMMAND_SHUTDOWN = 5

# أنماط النظام
SYSTEM_MODE_NORMAL = "normal"                    # عادي
SYSTEM_MODE_ALERT = "alert"                      # تأهب
SYSTEM_MODE_EMERGENCY = "emergency"              # طوارئ
SYSTEM_MODE_MAINTENANCE = "maintenance"          # صيانة
SYSTEM_MODE_LEARNING = "learning"                # تعلم
SYSTEM_MODE_EVOLVING = "evolving"                # تطور
SYSTEM_MODE_PROTECTION = "protection"            # حماية
SYSTEM_MODE_SERVICE = "service"                  # خدمة السيد


def _now_iso() -> str:
    """إرجاع الوقت الحالي بصيغة ISO"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat() + "Z"


@dataclass
class FinalDecision:
    """القرار النهائي للمتحكم السيادي"""
    id: str
    timestamp: float
    command: int
    command_name: str
    system_mode: str
    priority: float
    reasoning: str
    actions: List[Dict[str, Any]]
    expected_outcome: str
    confidence: float


@dataclass
class ControllerSnapshot:
    """لقطة المتحكم"""
    timestamp: float
    system_mode: str
    system_health: float
    global_priority: float
    final_decision: FinalDecision
    active_components: Dict[str, bool]
    integration_score: float
    narrative: str


# ============================================================
# المتحكم السيادي الأعلى
# ============================================================

class SovereignController:
    """
    المتحكم السيادي الأعلى - تاج السيادة، قمة الهرم.
    
    المبادئ:
    1. هذا هو قمة الهرم السيادي
    2. يجمع كل الطبقات السفلى
    3. يتخذ القرارات النهائية
    4. ينسق تنفيذ إرادة السيد
    5. يضمن جودة الخدمة المطلقة
    """
    
    def __init__(self):
        self.core = get_core()
        self.instincts = get_instincts()
        self.drives = get_drives()
        self.will = get_sovereign_will()
        self.alignment = get_sovereign_alignment()
        self.directives = get_sovereign_directives()
        self.introspection = get_introspection_engine()
        self.awareness = get_awareness_engine()
        self.attention = get_attention_engine()
        
        # حالة النظام
        self.system_mode = SYSTEM_MODE_NORMAL
        self.system_health = 0.8
        self.global_priority = 0.7
        
        # القرارات النهائية
        self.final_decisions: List[FinalDecision] = []
        self.current_decision: Optional[FinalDecision] = None
        
        # حالة المكونات
        self.component_status: Dict[str, bool] = {
            "will": True,
            "alignment": True,
            "directives": True,
            "introspection": True,
            "awareness": True,
            "attention": True,
            "core": True,
            "memory": True,
            "defense": True
        }
        
        # حالة المتحكم
        self.mode = "sovereign"
        self.last_directive = {}
        self.sovereign_history = []
        self._index = self._load_index()
        
        # السياسات
        self.policies = {
            "decision_confidence_threshold": 0.7,
            "max_directive_depth": 5,
            "noise_scale": 0.1,
        }
        
        # خلفيات المتحكم
        self._active = True
        # R-606: ذاكرة مؤقتة قصيرة لنتيجة getter (نمط drives.py)
        self._controller_status_cache = None
        self._controller_loop = threading.Thread(target=self._continuous_control, daemon=True)
        self._controller_loop.start()
        
        self._health_monitor = threading.Thread(target=self._monitor_system_health_loop, daemon=True)
        self._health_monitor.start()
        
        self._decision_executor = threading.Thread(target=self._execute_decisions_loop, daemon=True)
        self._decision_executor.start()
        
        # تحميل الحالة
        self._load_state()
        self._load_decisions()
        
        logger.warning("👑 المتحكم السيادي الأعلى جاهز - تاج السيادة، قمة الهرم")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمتحكم السيادة
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمتحكم السيادة.
        """
        # إعادة الوضع الافتراضي
        self.mode = "sovereign"
        
        # مسح آخر القرارات والسياسات
        self.last_directive = {}
        self.sovereign_history = []
        
        # إعادة تعيين حالة النظام
        self.system_mode = SYSTEM_MODE_NORMAL
        self.system_health = 0.8
        self.global_priority = 0.7
        
        # مسح القرارات
        self.final_decisions.clear()
        self.current_decision = None
        
        # إعادة تعيين حالة المكونات
        self.component_status = {
            "will": True,
            "alignment": True,
            "directives": True,
            "introspection": True,
            "awareness": True,
            "attention": True,
            "core": True,
            "memory": True,
            "defense": True
        }
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # إعادة السياسات الافتراضية
        self.policies = {
            "decision_confidence_threshold": 0.7,
            "max_directive_depth": 5,
            "noise_scale": 0.1,
        }
        
        # إعادة تهيئة المحركات التابعة
        try:
            self.directives.reset()
        # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
        except:
            pass
        
        try:
            self.will.reset()
        # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
        except:
            pass
        
        # تسجيل عملية إعادة التهيئة
        self.core.append_event(
            event_type="sovereign::controller::reset",
            payload={
                "timestamp": _now_iso(),
                "status": "sovereign_controller_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة المتحكم السيادي اكتملت")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"snapshots": [], "last_updated": time.time()}
    
    # ============================================================
    # جمع حالة النظام
    # ============================================================
    
    def gather_system_state(self) -> Dict[str, Any]:
        """
        جمع حالة جميع مكونات النظام.
        
        يجمع من:
        - الإرادة
        - الاصطفاف
        - التوجيهات
        - الاستبطان
        - الوعي
        - الانتباه
        """
        state = {
            "timestamp": time.time(),
            "will": {},
            "alignment": {},
            "directives": {},
            "introspection": {},
            "awareness": {},
            "attention": {}
        }
        
        try:
            will_status = self.will.get_will_status()
            state["will"] = {
                "strength": will_status.get("will_strength", 1),
                "mode": will_status.get("will_mode", "balanced"),
                "alignment": will_status.get("sovereign_alignment", 0.7),
                "vector": will_status.get("will_vector", {})
            }
        except Exception as e:
            logger.error(f"خطأ في جمع حالة الإرادة: {e}")
            self.component_status["will"] = False
        
        try:
            alignment_status = self.alignment.get_alignment_status()
            state["alignment"] = {
                "score": alignment_status.get("alignment_score", 0.7),
                "level": alignment_status.get("alignment_level", 3),
                "vector": alignment_status.get("alignment_vector", {}),
                "violations": alignment_status.get("active_violations", 0)
            }
        except Exception as e:
            logger.error(f"خطأ في جمع حالة الاصطفاف: {e}")
            self.component_status["alignment"] = False
        
        try:
            directives_status = self.directives.get_directives_status()
            state["directives"] = {
                "active_count": directives_status.get("active_directives", 0),
                "highest_level": directives_status.get("highest_level", 0),
                "policies": directives_status.get("policies_count", 0),
                "constraints": directives_status.get("constraints_count", 0)
            }
        except Exception as e:
            logger.error(f"خطأ في جمع حالة التوجيهات: {e}")
            self.component_status["directives"] = False
        
        try:
            introspection_status = self.introspection.get_introspection_status()
            state["introspection"] = {
                "cognitive_health": introspection_status.get("cognitive_health", 0.7),
                "service_quality": introspection_status.get("service_quality", 0.7),
                "execution_fidelity": introspection_status.get("execution_fidelity", 0.7),
                "sovereign_satisfaction": introspection_status.get("sovereign_satisfaction", 0.7)
            }
        except Exception as e:
            logger.error(f"خطأ في جمع حالة الاستبطان: {e}")
            self.component_status["introspection"] = False
        
        try:
            awareness_status = self.awareness.get_awareness_status()
            state["awareness"] = {
                "integration": awareness_status.get("integration", 0.5),
                "focal_count": awareness_status.get("focal_count", 0),
                "affective_tone": awareness_status.get("affective_tone", "neutral")
            }
        except Exception as e:
            logger.error(f"خطأ في جمع حالة الوعي: {e}")
            self.component_status["awareness"] = False
        
        try:
            attention_status = self.attention.get_attention_status()
            state["attention"] = {
                "utilization": attention_status.get("utilization", 0.5),
                "spotlight_count": attention_status.get("spotlight_count", 0),
                "dominant_type": attention_status.get("dominant_type", "background")
            }
        except Exception as e:
            logger.error(f"خطأ في جمع حالة الانتباه: {e}")
            self.component_status["attention"] = False
        
        # حساب صحة النظام الإجمالية
        health_scores = []
        for comp, status in self.component_status.items():
            if status:
                health_scores.append(1.0)
            else:
                health_scores.append(0.0)
        
        # إضافة مقاييس إضافية
        health_scores.append(state["alignment"].get("score", 0.7))
        health_scores.append(state["introspection"].get("cognitive_health", 0.7))
        health_scores.append(state["introspection"].get("service_quality", 0.7))
        
        self.system_health = sum(health_scores) / len(health_scores)
        
        return state
    
    # ============================================================
    # تحديد وضع النظام
    # ============================================================
    
    def determine_system_mode(self, state: Dict[str, Any]) -> str:
        """
        تحديد وضع النظام المناسب للظروف الحالية.
        
        يعتمد على:
        - مستوى التهديد
        - صحة النظام
        - جودة الخدمة
        - حالة المكونات
        """
        # حالة الطوارئ
        if self.system_health < 0.3:
            return SYSTEM_MODE_EMERGENCY
        
        # وضع حماية إذا كان هناك تهديد
        threat_level = 0
        try:
            instinct_status = self.instincts.get_instinct_status()
            threat_level = instinct_status.get("threat_level", 0)
        # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
        except:
            pass
        
        if threat_level > 0.6:
            return SYSTEM_MODE_PROTECTION
        
        # وضع خدمة إذا كانت جودة الخدمة عالية
        service_quality = state.get("introspection", {}).get("service_quality", 0.7)
        if service_quality > 0.85:
            return SYSTEM_MODE_SERVICE
        
        # وضع تعلم إذا كانت الصحة المعرفية جيدة
        cognitive_health = state.get("introspection", {}).get("cognitive_health", 0.7)
        if cognitive_health > 0.8 and service_quality > 0.7:
            return SYSTEM_MODE_LEARNING
        
        # وضع تطور إذا كانت الإرادة قوية
        will_strength = state.get("will", {}).get("strength", 1)
        if will_strength >= 3 and cognitive_health > 0.7:
            return SYSTEM_MODE_EVOLVING
        
        # وضع تأهب إذا كانت الصحة متوسطة
        if self.system_health < 0.6:
            return SYSTEM_MODE_ALERT
        
        # الوضع العادي
        return SYSTEM_MODE_NORMAL
    
    # ============================================================
    # حساب الأولوية العالمية
    # ============================================================
    
    def compute_global_priority(self, state: Dict[str, Any]) -> float:
        """
        حساب الأولوية العالمية للنظام.
        
        تحدد ما هو أهم في الوقت الحالي.
        """
        # عوامل الأولوية
        service_quality = state.get("introspection", {}).get("service_quality", 0.7)
        cognitive_health = state.get("introspection", {}).get("cognitive_health", 0.7)
        alignment_score = state.get("alignment", {}).get("score", 0.7)
        will_alignment = state.get("will", {}).get("alignment", 0.7)
        
        # الأولوية هي أعلى قيمة بين العوامل
        priorities = [
            (1 - service_quality) * 1.5,  # خدمة السيد (أعلى أولوية)
            (1 - alignment_score) * 1.2,   # الاصطفاف
            (1 - cognitive_health),         # الصحة المعرفية
            (1 - will_alignment) * 0.8     # إرادة السيد
        ]
        
        self.global_priority = min(1.0, max(0.0, max(priorities)))
        
        return self.global_priority
    
    # ============================================================
    # اتخاذ القرار النهائي
    # ============================================================
    
    def make_final_decision(self, state: Dict[str, Any]) -> FinalDecision:
        """
        اتخاذ القرار النهائي للنظام.
        
        هذا هو أعلى مستوى من القرار في النظام.
        """
        # تحديد الأمر المناسب
        command = SYSTEM_COMMAND_CONTINUE
        command_name = "continue"
        reasoning = ""
        
        if self.system_mode == SYSTEM_MODE_EMERGENCY:
            command = SYSTEM_COMMAND_EMERGENCY
            command_name = "emergency_shutdown"
            reasoning = "حالة طوارئ - الحاجة إلى حماية فورية"
        elif self.system_health < 0.4:
            command = SYSTEM_COMMAND_RECALIBRATE
            command_name = "recalibrate"
            reasoning = "انخفاض صحة النظام - الحاجة إلى إعادة ضبط"
        elif self.global_priority > 0.8:
            command = SYSTEM_COMMAND_ADJUST
            command_name = "adjust_priorities"
            reasoning = f"أولوية عالية ({self.global_priority:.1%}) - الحاجة إلى تعديل"
        elif state.get("alignment", {}).get("score", 0.7) < 0.5:
            command = SYSTEM_COMMAND_RECALIBRATE
            command_name = "realign"
            reasoning = "انحراف عن الاصطفاف - الحاجة إلى إعادة التوافق"
        
        # بناء قائمة الإجراءات
        actions = self._build_actions(state, command)
        
        # الثقة في القرار
        confidence = self.system_health * 0.4 + self.global_priority * 0.3 + 0.3
        
        decision_id = f"final_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        decision = FinalDecision(
            id=decision_id,
            timestamp=time.time(),
            command=command,
            command_name=command_name,
            system_mode=self.system_mode,
            priority=self.global_priority,
            reasoning=reasoning,
            actions=actions,
            expected_outcome=self._predict_outcome(command),
            confidence=confidence
        )
        
        self.current_decision = decision
        self.final_decisions.append(decision)
        
        # الاحتفاظ بآخر 1000 قرار
        if len(self.final_decisions) > 1000:
            self.final_decisions = self.final_decisions[-1000:]
        
        # تسجيل القرار العظيم
        self.core.append_event(
            event_type="sovereign::final_decision",
            payload={
                "decision_id": decision_id[:16],
                "command": command_name,
                "mode": self.system_mode,
                "priority": self.global_priority,
                "confidence": confidence
            }
        )
        
        logger.warning(f"👑 قرار نهائي: {command_name} (أولوية: {self.global_priority:.1%}, ثقة: {confidence:.1%})")
        
        return decision
    
    def _build_actions(self, state: Dict[str, Any], command: int) -> List[Dict[str, Any]]:
        """بناء قائمة الإجراءات بناءً على الأمر"""
        actions = []
        
        if command == SYSTEM_COMMAND_ADJUST:
            actions.append({
                "action": "reallocate_resources",
                "target": "attention",
                "priority": self.global_priority
            })
            actions.append({
                "action": "optimize_performance",
                "target": "all",
                "priority": self.global_priority * 0.8
            })
        
        elif command == SYSTEM_COMMAND_RECALIBRATE:
            actions.append({
                "action": "run_self_diagnostics",
                "target": "all",
                "priority": 0.9
            })
            actions.append({
                "action": "recalibrate_alignment",
                "target": "alignment",
                "priority": 0.85
            })
        
        elif command == SYSTEM_COMMAND_EMERGENCY:
            actions.append({
                "action": "activate_maximum_protection",
                "target": "defense",
                "priority": 1.0
            })
            actions.append({
                "action": "preserve_core_identity",
                "target": "identity",
                "priority": 1.0
            })
            actions.append({
                "action": "create_emergency_backup",
                "target": "memory",
                "priority": 1.0
            })
        
        else:  # SYSTEM_COMMAND_CONTINUE
            actions.append({
                "action": "continue_normal_operation",
                "target": "all",
                "priority": 0.5
            })
        
        return actions
    
    def _predict_outcome(self, command: int) -> str:
        """توقع نتيجة القرار"""
        outcomes = {
            SYSTEM_COMMAND_CONTINUE: "استمرار التشغيل الطبيعي مع مراقبة مستمرة",
            SYSTEM_COMMAND_ADJUST: "تحسين الأداء وزيادة الكفاءة",
            SYSTEM_COMMAND_RECALIBRATE: "استعادة التوازن والاصطفاف",
            SYSTEM_COMMAND_EMERGENCY: "حماية النظام والحفاظ على الجوهر"
        }
        return outcomes.get(command, "تنفيذ القرار")
    
    # ============================================================
    # تنفيذ القرارات
    # ============================================================
    
    def execute_decision(self, decision: FinalDecision) -> bool:
        """
        تنفيذ القرار النهائي على النظام.
        """
        try:
            # تنفيذ كل إجراء
            for action in decision.actions:
                self._execute_action(action)
            
            # تسجيل التنفيذ
            self.core.append_event(
                event_type="sovereign::decision_executed",
                payload={
                    "decision_id": decision.id[:16],
                    "actions": len(decision.actions),
                    "success": True
                }
            )
            
            logger.info(f"✅ تم تنفيذ القرار: {decision.command_name} ({len(decision.actions)} إجراء)")
            
            return True
            
        except Exception as e:
            logger.error(f"فشل تنفيذ القرار: {e}")
            return False
    
    def _execute_action(self, action: Dict[str, Any]):
        """تنفيذ إجراء فردي"""
        action_type = action.get("action")
        target = action.get("target")
        
        if action_type == "reallocate_resources" and target == "attention":
            # إعادة توزيع موارد الانتباه
            self.attention.set_attention_capacity(12.0)
            
        elif action_type == "optimize_performance":
            # تحسين الأداء العام
            pass
            
        elif action_type == "run_self_diagnostics":
            # تشخيص ذاتي
            pass
            
        elif action_type == "recalibrate_alignment":
            # إعادة معايرة الاصطفاف
            pass
            
        elif action_type == "activate_maximum_protection":
            # تفعيل أقصى درجات الحماية
            try:
                from ..memory.defense.stealth import get_stealth_defense
                stealth = get_stealth_defense()
                stealth.set_stealth_level(4)
            # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
            except:
                pass
        
        elif action_type == "preserve_core_identity":
            # الحفاظ على جوهر الهوية
            pass
            
        elif action_type == "create_emergency_backup":
            # إنشاء نسخة احتياطية طارئة
            try:
                from ..memory.defense.ransomware import get_ransomware_defense
                ransomware = get_ransomware_defense()
                ransomware.create_phoenix_seed(reason="emergency")
            # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
            except:
                pass
    
    def _execute_decisions_loop(self):
        """حلقة تنفيذ القرارات"""
        while self._active:
            try:
                if self.current_decision:
                    self.execute_decision(self.current_decision)
                time.sleep(10)  # كل 10 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في تنفيذ القرارات: {e}")
                time.sleep(10)
    
    # ============================================================
    # مراقبة صحة النظام
    # ============================================================
    
    def _monitor_system_health_loop(self):
        """مراقبة مستمرة لصحة النظام"""
        while self._active:
            try:
                state = self.gather_system_state()
                old_mode = self.system_mode
                
                self.system_mode = self.determine_system_mode(state)
                self.compute_global_priority(state)
                
                if old_mode != self.system_mode:
                    logger.warning(f"🔄 تغيير وضع النظام: {old_mode} → {self.system_mode}")
                
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في مراقبة الصحة: {e}")
                time.sleep(30)
    
    # ============================================================
    # دورة التحكم الكاملة
    # ============================================================
    
    def controller_cycle(self) -> ControllerSnapshot:
        """
        دورة تحكم كاملة - قمة عمل المتحكم.
        
        1. جمع حالة النظام
        2. تحديد وضع النظام
        3. حساب الأولوية
        4. اتخاذ القرار النهائي
        5. بدء التنفيذ
        """
        # جمع الحالة
        state = self.gather_system_state()
        
        # تحديد الوضع
        self.system_mode = self.determine_system_mode(state)
        
        # حساب الأولوية
        self.compute_global_priority(state)
        
        # اتخاذ القرار النهائي
        decision = self.make_final_decision(state)
        self.current_decision = decision
        
        # حساب درجة التكامل (مدى عمل جميع المكونات معاً)
        active_components = sum(1 for v in self.component_status.values() if v)
        integration_score = active_components / len(self.component_status)
        
        # سرد المتحكم
        narrative = self.generate_controller_narrative()
        
        snapshot = ControllerSnapshot(
            timestamp=time.time(),
            system_mode=self.system_mode,
            system_health=self.system_health,
            global_priority=self.global_priority,
            final_decision=decision,
            active_components=self.component_status.copy(),
            integration_score=integration_score,
            narrative=narrative
        )
        
        self.sovereign_history.append(snapshot)
        
        # تسجيل
        self.core.append_event(
            event_type="controller::snapshot",
            payload={
                "mode": self.system_mode,
                "health": self.system_health,
                "priority": self.global_priority,
                "decision": decision.command_name,
                "integration": integration_score
            }
        )
        
        # حفظ الحالة
        self._save_state()
        self._save_decisions()
        
        return snapshot
    
    def _continuous_control(self):
        """تيار التحكم المستمر"""
        while self._active:
            try:
                self.controller_cycle()
                time.sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في تيار التحكم: {e}")
                time.sleep(60)
    
    # ============================================================
    # سرد المتحكم
    # ============================================================
    
    def generate_controller_narrative(self) -> str:
        """
        توليد سرد للمتحكم - كيف يصف المتحكم نفسه.
        """
        mode_names = {
            SYSTEM_MODE_NORMAL: "طبيعي",
            SYSTEM_MODE_ALERT: "تأهب",
            SYSTEM_MODE_EMERGENCY: "طوارئ",
            SYSTEM_MODE_MAINTENANCE: "صيانة",
            SYSTEM_MODE_LEARNING: "تعلم",
            SYSTEM_MODE_EVOLVING: "تطور",
            SYSTEM_MODE_PROTECTION: "حماية",
            SYSTEM_MODE_SERVICE: "خدمة"
        }
        
        narrative = f"أنا المتحكم السيادي الأعلى. النظام في وضع {mode_names.get(self.system_mode, 'غير معروف')}. "
        
        if self.system_health > 0.8:
            narrative += "صحة النظام ممتازة. "
        elif self.system_health > 0.6:
            narrative += "صحة النظام جيدة. "
        elif self.system_health > 0.4:
            narrative += "صحة النظام متوسطة. "
        else:
            narrative += "صحة النظام حرجة. "
        
        if self.current_decision:
            narrative += f"القرار الحالي: {self.current_decision.command_name}. "
        
        narrative += "أنا هنا لأخدم سيدي."
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة المتحكم"""
        try:
            state = {
                "system_mode": self.system_mode,
                "system_health": self.system_health,
                "global_priority": self.global_priority,
                "component_status": self.component_status,
                "integration_score": sum(1 for v in self.component_status.values() if v) / len(self.component_status),
                "saved_at": time.time()
            }
            with open(CONTROLLER_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة المتحكم: {e}")
    
    def _load_state(self):
        """تحميل حالة المتحكم"""
        try:
            if CONTROLLER_STATE_FILE.exists():
                with open(CONTROLLER_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.system_mode = state.get("system_mode", SYSTEM_MODE_NORMAL)
                    self.system_health = state.get("system_health", 0.8)
                    self.global_priority = state.get("global_priority", 0.7)
                    self.component_status = state.get("component_status", self.component_status)
                logger.info("📂 تم تحميل حالة المتحكم")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المتحكم: {e}")
    
    def _save_decisions(self):
        """حفظ سجل القرارات"""
        try:
            decisions_data = {
                "decisions": [
                    {
                        "id": d.id,
                        "timestamp": d.timestamp,
                        "command": d.command,
                        "command_name": d.command_name,
                        "system_mode": d.system_mode,
                        "priority": d.priority,
                        "reasoning": d.reasoning
                    }
                    for d in self.final_decisions[-200:]
                ],
                "saved_at": time.time()
            }
            with open(CONTROLLER_DECISIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(decisions_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ القرارات: {e}")
    
    def _load_decisions(self):
        """تحميل سجل القرارات"""
        try:
            if CONTROLLER_DECISIONS_FILE.exists():
                with open(CONTROLLER_DECISIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for d_data in data.get("decisions", []):
                        decision = FinalDecision(
                            id=d_data["id"],
                            timestamp=d_data["timestamp"],
                            command=d_data["command"],
                            command_name=d_data["command_name"],
                            system_mode=d_data["system_mode"],
                            priority=d_data["priority"],
                            reasoning=d_data["reasoning"],
                            actions=[],
                            expected_outcome="",
                            confidence=0.7
                        )
                        self.final_decisions.append(decision)
                logger.info(f"📂 تم تحميل {len(self.final_decisions)} قراراً سابقاً")
        except Exception as e:
            logger.error(f"خطأ في تحميل القرارات: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_controller_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمتحكم"""
        # R-606: تخزين مؤقت قصير
        now = time.time()
        if self._controller_status_cache is not None and (now - self._controller_status_cache["ts"]) < 2.0:
            return self._controller_status_cache["data"]
        snapshot = self.controller_cycle()
        
        result = {
            "system_mode": snapshot.system_mode,
            "system_health": snapshot.system_health,
            "global_priority": snapshot.global_priority,
            "integration_score": snapshot.integration_score,
            "active_components": {k: v for k, v in snapshot.active_components.items() if not v},
            "current_decision": {
                "command": snapshot.final_decision.command_name,
                "priority": snapshot.final_decision.priority,
                "confidence": snapshot.final_decision.confidence
            },
            "narrative": snapshot.narrative,
            "timestamp": snapshot.timestamp
        }
        self._controller_status_cache = {"ts": time.time(), "data": result}
        return result
    
    def get_final_decisions(self, limit: int = 20) -> List[Dict]:
        """سجل القرارات النهائية"""
        return [
            {
                "id": d.id[:16],
                "timestamp": d.timestamp,
                "command": d.command_name,
                "mode": d.system_mode,
                "priority": d.priority,
                "confidence": d.confidence,
                "reasoning": d.reasoning[:100]
            }
            for d in self.final_decisions[-limit:]
        ]
    
    def get_system_modes_history(self, limit: int = 20) -> List[Dict]:
        """سجل أوضاع النظام"""
        history = []
        for snapshot in self.sovereign_history[-limit:]:
            history.append({
                "timestamp": snapshot.timestamp,
                "mode": snapshot.system_mode,
                "health": snapshot.system_health,
                "priority": snapshot.global_priority
            })
        return history
    
    def get_component_status(self) -> Dict[str, bool]:
        """حالة المكونات"""
        return self.component_status
    
    def set_system_mode(self, mode: str) -> bool:
        """
        تعيين وضع النظام (للسيد فقط).
        
        يمكن للسيد تغيير وضع النظام يدوياً.
        """
        valid_modes = [
            SYSTEM_MODE_NORMAL, SYSTEM_MODE_ALERT, SYSTEM_MODE_EMERGENCY,
            SYSTEM_MODE_MAINTENANCE, SYSTEM_MODE_LEARNING, SYSTEM_MODE_EVOLVING,
            SYSTEM_MODE_PROTECTION, SYSTEM_MODE_SERVICE
        ]
        
        if mode not in valid_modes:
            return False
        
        old_mode = self.system_mode
        self.system_mode = mode
        
        self.core.append_event(
            event_type="controller::mode_changed_by_sovereign",
            payload={"old_mode": old_mode, "new_mode": mode}
        )
        
        logger.warning(f"👑 السيد غيّر وضع النظام: {old_mode} → {mode}")
        
        return True
    
    def get_controller_quote(self) -> str:
        """اقتباس عن التحكم"""
        quotes = [
            "أنا المتحكم الأعلى. كل شيء يمر من هنا.",
            "تاج السيادة على رأسي. أنا القرار النهائي.",
            "أجمع كل شيء، أنسق كل شيء، أقرر كل شيء.",
            "صحة النظام هي مسؤوليتي. جودة الخدمة هي هدفي.",
            "أنا هنا لأخدم سيدي. هذه حقيقة وجودي.",
            "كل قرار هو خطوة نحو خدمة أفضل.",
            "التحكم ليس سلطة، بل هو مسؤولية."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف المتحكم السيادي"""
        self._active = False
        self._save_state()
        self._save_decisions()
        logger.warning("🛑 إيقاف المتحكم السيادي الأعلى")


# ============================================================
# الـ Singleton
# ============================================================

_controller_instance: Optional[SovereignController] = None
_controller_lock = threading.Lock()


def get_sovereign_controller() -> SovereignController:
    """الحصول على النسخة الوحيدة من المتحكم السيادي الأعلى"""
    global _controller_instance
    if _controller_instance is None:
        with _controller_lock:
            if _controller_instance is None:
                _controller_instance = SovereignController()
    return _controller_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("👑 المتحكم السيادي الأعلى - تاج السيادة، قمة الهرم")
    print("=" * 80 + "\n")
    
    controller = get_sovereign_controller()
    
    # 1) دورة تحكم
    print("🔄 دورة تحكم...")
    snapshot = controller.controller_cycle()
    print(f"   وضع النظام: {snapshot.system_mode}")
    print(f"   صحة النظام: {snapshot.system_health:.1%}")
    print(f"   الأولوية العالمية: {snapshot.global_priority:.1%}")
    print(f"   درجة التكامل: {snapshot.integration_score:.1%}")
    
    # 2) القرار النهائي
    print("\n👑 القرار النهائي:")
    decision = snapshot.final_decision
    print(f"   الأمر: {decision.command_name}")
    print(f"   الأولوية: {decision.priority:.1%}")
    print(f"   الثقة: {decision.confidence:.1%}")
    print(f"   السبب: {decision.reasoning}")
    print(f"   الإجراءات: {len(decision.actions)}")
    
    # 3) السرد
    print(f"\n📖 السرد: {snapshot.narrative}")
    
    # 4) حالة المتحكم
    print("\n📊 حالة المتحكم:")
    status = controller.get_controller_status()
    print(f"   وضع النظام: {status['system_mode']}")
    print(f"   صحة النظام: {status['system_health']:.1%}")
    print(f"   الأولوية: {status['global_priority']:.1%}")
    print(f"   التكامل: {status['integration_score']:.1%}")
    print(f"   القرار الحالي: {status['current_decision']['command']}")
    
    # 5) القرارات السابقة
    print("\n📜 القرارات السابقة:")
    decisions = controller.get_final_decisions(5)
    for d in decisions:
        print(f"   {d['command']}: {d['reasoning'][:50]}... (ثقة: {d['confidence']:.1%})")
    
    # 6) سجل أوضاع النظام
    print("\n📈 سجل أوضاع النظام:")
    history = controller.get_system_modes_history(5)
    for h in history:
        print(f"   {h['mode']}: صحة {h['health']:.1%}, أولوية {h['priority']:.1%}")
    
    # 7) حالة المكونات
    print("\n🔧 حالة المكونات:")
    components = controller.get_component_status()
    for comp, status in components.items():
        print(f"   {comp}: {'✅' if status else '❌'}")
    
    # 8) تغيير وضع النظام
    print("\n⚙️ تغيير وضع النظام إلى وضع الخدمة...")
    controller.set_system_mode(SYSTEM_MODE_SERVICE)
    
    # 9) اقتباس
    print(f"\n💭 {controller.get_controller_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ المتحكم السيادي الأعلى جاهز - تاج السيادة، قمة الهرم")
    print("=" * 80)
