# backend/predictive/predictive_controller.py
# 🧠 Predictive Controller — المتحكم الطبقي لطبقة التنبؤ
# الإصدار: 1.0.0 - نسخة نهائية جاهزة للدمج

"""
المتحكم الطبقي لطبقة التنبؤ.

المسؤوليات:
- تنسيق عمل محركات التنبؤ الأربعة:
    * predictive_engine (التنبؤ العميق)
    * predictive_scenarios (السيناريوهات)
    * predictive_simulation (المحاكاة التنبؤية)
    * predictive_risk_manager (إدارة المخاطر)
- تحويل حالة النظام إلى:
    * خريطة مستقبلية
    * سيناريوهات محتملة
    * محاكاة مركزة
    * تقييم مخاطر
- إنتاج قرار تنبؤي قابل للاستهلاك من قبل السيادة
"""

from __future__ import annotations

import json
import time
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

try:
    from ..memory.core import get_core
    from ..config import DATA_DIR
    from .predictive_engine import get_predictive_engine
    from .predictive_scenarios import get_predictive_scenario_engine
    from .predictive_simulation import get_predictive_simulation
    from .predictive_risk_manager import get_predictive_risk_manager
    from ..sovereign.controller import get_sovereign_controller
except ImportError:
    from memory.core import get_core
    from config import DATA_DIR
    from .predictive_engine import get_predictive_engine
    from .predictive_scenarios import get_predictive_scenario_engine
    from .predictive_simulation import get_predictive_simulation
    from .predictive_risk_manager import get_predictive_risk_manager
    from sovereign.controller import get_sovereign_controller

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت والإعدادات
# ============================================================

PCTRL_DIR = DATA_DIR / "predictive" / "controller"
PCTRL_DIR.mkdir(parents=True, exist_ok=True)
PCTRL_LOG = PCTRL_DIR / "predictive_controller_log.jsonl"
PCTRL_STATE_FILE = PCTRL_DIR / "predictive_controller_state.json"

# أوضاع التشغيل
PREDICTIVE_MODE_BALANCED = "balanced"       # متوازن (افتراضي)
PREDICTIVE_MODE_ADVISORY = "advisory"       # استشاري (توصيات فقط)
PREDICTIVE_MODE_INTEGRATED = "integrated"   # متكامل (يؤثر على النظام)
PREDICTIVE_MODE_CONSERVATIVE = "conservative"  # متحفظ (يقبل مخاطر أقل)
PREDICTIVE_MODE_AGGRESSIVE = "aggressive"     # عدائي (يقبل مخاطر أعلى)


def _now_iso() -> str:
    """إرجاع الوقت الحالي بصيغة ISO"""
    return datetime.now(timezone.utc).isoformat() + "Z"


@dataclass
class PredictiveDecisionSnapshot:
    """لقطة قرار تنبؤي - مخرجات المتحكم"""
    timestamp: str
    mode: str
    sensed_state: Dict[str, Any]
    future_map: Dict[str, Any]
    scenarios: List[Dict[str, Any]]
    simulation_summary: Dict[str, Any]
    risk_report: Dict[str, Any]
    predictive_decision: Dict[str, Any]
    sovereign_hint: Optional[Dict[str, Any]] = None
    raw: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# المتحكم الطبقي للتنبؤ
# ============================================================

class PredictiveController:
    """
    المتحكم الطبقي للتنبؤ - ينسق ويوحد محركات التنبؤ الأربعة.
    
    المبادئ:
    1. واجهة موحدة لكل قدرات التنبؤ
    2. تنسيق تدفق البيانات بين المحركات
    3. إنتاج قرارات تنبؤية قابلة للاستهلاك
    4. التكامل مع السيادة لمراجعة القرارات
    5. أوضاع تشغيل مختلفة تناسب حالات الاستخدام المختلفة
    """
    
    def __init__(self):
        self.core = get_core()
        
        # محركات التنبؤ
        self.engine = get_predictive_engine()
        self.scenarios = get_predictive_scenario_engine()
        self.simulation = get_predictive_simulation()
        self.risk_manager = get_predictive_risk_manager()
        
        # التكامل مع السيادة
        self.sovereign = get_sovereign_controller()
        
        # حالة المتحكم
        self.mode: str = PREDICTIVE_MODE_BALANCED
        self.last_decision: Optional[PredictiveDecisionSnapshot] = None
        
        # إحصائيات
        self.stats = {
            "total_cycles": 0,
            "decisions_made": 0,
            "advisory_signals": 0,
            "integrated_actions": 0
        }
        
        # حالة المحرك
        self.mode_state = "analysis"
        self.last_integrated_output = {}
        self.integration_history = []
        self._index = self._load_index()
        
        # السياسات
        self.policies = {
            "integration_confidence_threshold": 0.65,
            "max_integration_depth": 4,
            "noise_scale": 0.1,
        }
        
        # خلفيات التشغيل
        self._active = True
        self._continuous_cycle = threading.Thread(target=self._continuous_cycle_loop, daemon=True)
        self._continuous_cycle.start()
        
        # تحميل الحالة السابقة
        self._load_state()
        
        logger.info("🧠 المتحكم الطبقي للتنبؤ جاهز - ينسق محركات التنبؤ الأربعة")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمتحكم التنبؤ
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمتحكم التنبؤ.
        """
        # إعادة الوضع الافتراضي
        self.mode_state = "analysis"
        
        # مسح آخر نتائج التكامل
        self.last_integrated_output = {}
        self.integration_history = []
        
        # إعادة تعيين الإحصائيات
        self.stats = {
            "total_cycles": 0,
            "decisions_made": 0,
            "advisory_signals": 0,
            "integrated_actions": 0
        }
        
        # إعادة تعيين وضع التشغيل
        self.mode = PREDICTIVE_MODE_BALANCED
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # إعادة السياسات الافتراضية
        self.policies = {
            "integration_confidence_threshold": 0.65,
            "max_integration_depth": 4,
            "noise_scale": 0.1,
        }
        
        # إعادة تهيئة المحركات التابعة
        try:
            self.engine.reset()
        except:
            pass
        
        try:
            self.scenarios.reset()
        except:
            pass
        
        try:
            self.simulation.reset()
        except:
            pass
        
        try:
            self.risk_manager.reset()
        except:
            pass
        
        # تسجيل عملية إعادة التهيئة
        self.core.append_event(
            event_type="predictive::controller::reset",
            payload={
                "timestamp": _now_iso(),
                "status": "predictive_controller_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة المتحكم التنبؤي اكتملت")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"integrations": [], "last_updated": time.time()}
    
    # ============================================================
    # الدوال الأساسية
    # ============================================================
    
    def sense_state(self) -> Dict[str, Any]:
        """
        قراءة حالة النظام من جميع المصادر.
        
        يجمع من:
        - حالة النظام الحالية (من predictive_engine)
        - حالة السيادة
        - حالة الوعي (إن وجدت)
        """
        sensed = {}
        
        # من محرك التنبؤ
        try:
            sensed["predictive"] = self.engine.get_prediction_status()
        except Exception as e:
            logger.warning(f"فشل في قراءة حالة predictive_engine: {e}")
            sensed["predictive"] = {}
        
        # من محرك السيناريوهات
        try:
            scen_status = self.scenarios.get_scenario_status()
            sensed["scenarios"] = scen_status
        except Exception as e:
            logger.warning(f"فشل في قراءة حالة scenarios: {e}")
            sensed["scenarios"] = {}
        
        # من محاكاة التنبؤ
        try:
            sim_status = self.simulation.get_simulation_status()
            sensed["simulation"] = sim_status
        except Exception as e:
            logger.warning(f"فشل في قراءة حالة simulation: {e}")
            sensed["simulation"] = {}
        
        # من مدير المخاطر
        try:
            risk_status = self.risk_manager.get_risk_status()
            sensed["risk"] = risk_status
        except Exception as e:
            logger.warning(f"فشل في قراءة حالة risk_manager: {e}")
            sensed["risk"] = {}
        
        # من السيادة
        try:
            sov_status = self.sovereign.get_controller_status()
            sensed["sovereign"] = sov_status
        except Exception as e:
            logger.warning(f"فشل في قراءة حالة sovereign: {e}")
            sensed["sovereign"] = {}
        
        return sensed
    
    def build_future_map(self, sensed: Dict[str, Any]) -> Dict[str, Any]:
        """
        بناء خريطة المستقبل من حالة النظام.
        
        تستخدم predictive_engine لحساب الاتجاهات المستقبلية.
        """
        try:
            # استخدام predictive_engine لحساب خريطة المستقبل
            future_map = self.engine.compute_future_map()
        except Exception as e:
            logger.warning(f"فشل في بناء future_map: {e}")
            future_map = {
                "knowledge_growth": 0.5,
                "identity_stability": 0.5,
                "service_quality": 0.5,
                "threat_level": 0.3,
                "evolution_pace": 0.5
            }
        
        return future_map
    
    def generate_scenarios(self, sensed: Dict[str, Any], 
                           future_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        توليد السيناريوهات المحتملة.
        
        تستخدم predictive_scenarios لبناء سيناريوهات متعددة.
        """
        try:
            # تشغيل دورة السيناريوهات
            self.scenarios.scenario_cycle()
            scenarios = self.scenarios.get_scenarios()
        except Exception as e:
            logger.warning(f"فشل في توليد السيناريوهات: {e}")
            scenarios = []
        
        return scenarios
    
    def run_focus_simulation(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تشغيل محاكاة مركزة على السيناريوهات الأكثر أهمية.
        
        تستخدم predictive_simulation لمحاكاة المسارات المستقبلية.
        """
        max_scenarios = 5
        focus_scenarios = scenarios[:max_scenarios]
        
        try:
            # تشغيل محاكاة باستخدام predictive_simulation
            sim_snapshot = self.simulation.simulation_cycle(runs=100, steps=12)
            
            # استخراج الملخص
            sim_result = {
                "status": "completed",
                "total_runs": sim_snapshot.batch.runs,
                "avg_success": sim_snapshot.summary.get("avg_success_rate", 0),
                "scenarios_simulated": [s.get("name", "unknown") for s in focus_scenarios],
                "risk_analysis": sim_snapshot.batch.risk_analysis,
                "opportunity_analysis": sim_snapshot.batch.opportunity_analysis
            }
        except Exception as e:
            logger.warning(f"فشل في تشغيل المحاكاة: {e}")
            sim_result = {
                "status": "simulation_failed",
                "error": str(e),
                "scenarios_simulated": [s.get("name", "unknown") for s in focus_scenarios]
            }
        
        return sim_result
    
    def evaluate_risk(self, sensed: Dict[str, Any], 
                      future_map: Dict[str, Any],
                      scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تقييم المخاطر بناءً على السيناريوهات وخريطة المستقبل.
        
        تستخدم predictive_risk_manager لتحليل المخاطر.
        """
        try:
            # تشغيل دورة المخاطر
            self.risk_manager.risk_cycle()
            
            # استخراج التقرير
            risk_report = {
                "prioritized": self.risk_manager.get_prioritized_risks(limit=10),
                "overall_risk": self.risk_manager.get_risk_status().get("overall_risk_level", 0),
                "active_warnings": len(self.risk_manager.get_early_warnings_list()),
                "mitigation_plans": len(self.risk_manager.get_mitigation_plans())
            }
        except Exception as e:
            logger.warning(f"فشل في تقييم المخاطر: {e}")
            risk_report = {
                "prioritized": [],
                "overall_risk": 0.5,
                "active_warnings": 0,
                "mitigation_plans": 0,
                "error": str(e)
            }
        
        return risk_report
    
    def synthesize_decision(self, sensed: Dict[str, Any],
                           future_map: Dict[str, Any],
                           scenarios: List[Dict[str, Any]],
                           simulation_summary: Dict[str, Any],
                           risk_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        تركيب القرار التنبؤي النهائي.
        
        يجمع جميع المعلومات ويصدر قراراً موحداً.
        """
        decision = {
            "mode": self.mode,
            "timestamp": time.time(),
            "primary_scenario": None,
            "primary_risk": None,
            "recommended_action": None,
            "confidence": 0.5,
            "reasoning": []
        }
        
        # تحديد السيناريو الأساسي من المخاطر
        prioritized_risks = risk_report.get("prioritized", [])
        if prioritized_risks:
            top_risk = prioritized_risks[0]
            decision["primary_risk"] = {
                "name": top_risk.get("name"),
                "probability": top_risk.get("probability", 0),
                "priority": top_risk.get("priority", 0)
            }
            decision["primary_scenario"] = top_risk.get("name")
            decision["confidence"] = 1 - top_risk.get("probability", 0.5)
            decision["reasoning"].append(f"أولوية المخاطر: {top_risk.get('name')}")
        
        # إضافة توصيات من المحاكاة
        if simulation_summary.get("status") == "completed":
            avg_success = simulation_summary.get("avg_success", 0)
            decision["reasoning"].append(f"متوسط نجاح المحاكاة: {avg_success:.1%}")
            
            if avg_success < 0.4:
                decision["recommended_action"] = "تحسين أداء النظام"
            elif avg_success > 0.7:
                decision["recommended_action"] = "الحفاظ على الاستقرار"
        
        # إضافة توصيات من المخاطر
        if decision.get("primary_risk"):
            if decision["primary_risk"].get("probability", 0) > 0.6:
                decision["recommended_action"] = "تفعيل إجراءات تخفيف المخاطر"
        
        # إضافة توصيات من خريطة المستقبل
        threat_level = future_map.get("threat_level", 0.3)
        if threat_level > 0.6:
            decision["reasoning"].append(f"مستوى تهديد مرتفع: {threat_level:.1%}")
            if not decision["recommended_action"]:
                decision["recommended_action"] = "تعزيز الأمن والحماية"
        
        self.stats["decisions_made"] += 1
        
        return decision
    
    # ============================================================
    # دورة التحكم الرئيسية
    # ============================================================
    
    def predictive_controller_cycle(self) -> PredictiveDecisionSnapshot:
        """
        دورة تحكم تنبؤية كاملة.
        
        الخطوات:
        1. قراءة حالة النظام
        2. بناء خريطة المستقبل
        3. توليد السيناريوهات
        4. تشغيل المحاكاة المركزة
        5. تقييم المخاطر
        6. تركيب القرار النهائي
        """
        # 1) قراءة الحالة
        sensed = self.sense_state()
        
        # 2) بناء خريطة المستقبل
        future_map = self.build_future_map(sensed)
        
        # 3) توليد السيناريوهات
        scenarios = self.generate_scenarios(sensed, future_map)
        
        # 4) تشغيل المحاكاة
        simulation_summary = self.run_focus_simulation(scenarios)
        
        # 5) تقييم المخاطر
        risk_report = self.evaluate_risk(sensed, future_map, scenarios)
        
        # 6) تركيب القرار
        decision = self.synthesize_decision(
            sensed=sensed,
            future_map=future_map,
            scenarios=scenarios,
            simulation_summary=simulation_summary,
            risk_report=risk_report
        )
        
        # تلميح من السيادة (اختياري)
        try:
            sov_snapshot = self.sovereign.get_controller_status()
            sovereign_hint = {
                "system_mode": sov_snapshot.get("system_mode", "unknown"),
                "system_health": sov_snapshot.get("system_health", 0.5),
                "global_priority": sov_snapshot.get("global_priority", 0.5)
            }
        except Exception:
            sovereign_hint = None
        
        # إنشاء اللقطة
        snapshot = PredictiveDecisionSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            mode=self.mode,
            sensed_state=sensed,
            future_map=future_map,
            scenarios=scenarios[:10],  # أقصى 10 سيناريوهات
            simulation_summary=simulation_summary,
            risk_report=risk_report,
            predictive_decision=decision,
            sovereign_hint=sovereign_hint,
            raw={}
        )
        
        self.last_decision = snapshot
        self.stats["total_cycles"] += 1
        
        # تسجيل في السجل
        self.core.append_event(
            event_type="predictive::controller_cycle",
            payload={
                "mode": self.mode,
                "scenarios_count": len(scenarios),
                "primary_scenario": decision.get("primary_scenario"),
                "confidence": decision.get("confidence")
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    def _continuous_cycle_loop(self):
        """حلقة تشغيل مستمرة للدورة التنبؤية"""
        while self._active:
            try:
                self.predictive_controller_cycle()
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في حلقة التحكم المستمرة: {e}")
                time.sleep(30)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة المتحكم"""
        try:
            state = {
                "mode": self.mode,
                "stats": self.stats,
                "saved_at": time.time()
            }
            with open(PCTRL_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة المتحكم: {e}")
    
    def _load_state(self):
        """تحميل حالة المتحكم"""
        try:
            if PCTRL_STATE_FILE.exists():
                with open(PCTRL_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.mode = state.get("mode", PREDICTIVE_MODE_BALANCED)
                    self.stats = state.get("stats", self.stats)
                logger.info("📂 تم تحميل حالة المتحكم التنبؤي")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المتحكم: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_mode(self, mode: str) -> bool:
        """تعيين وضع التشغيل"""
        valid_modes = [
            PREDICTIVE_MODE_BALANCED,
            PREDICTIVE_MODE_ADVISORY,
            PREDICTIVE_MODE_INTEGRATED,
            PREDICTIVE_MODE_CONSERVATIVE,
            PREDICTIVE_MODE_AGGRESSIVE
        ]
        
        if mode not in valid_modes:
            return False
        
        old_mode = self.mode
        self.mode = mode
        
        self.core.append_event(
            event_type="predictive::mode_changed",
            payload={"old_mode": old_mode, "new_mode": mode}
        )
        
        logger.info(f"⚙️ تغيير وضع التنبؤ: {old_mode} → {mode}")
        
        return True
    
    def get_last_decision(self) -> Optional[PredictiveDecisionSnapshot]:
        """آخر قرار تنبؤي تم اتخاذه"""
        return self.last_decision
    
    def get_stats(self) -> Dict[str, int]:
        """إحصائيات المتحكم"""
        return self.stats.copy()
    
    def get_mode(self) -> str:
        """وضع التشغيل الحالي"""
        return self.mode
    
    def stop(self):
        """إيقاف المتحكم"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف المتحكم الطبقي للتنبؤ")


# ============================================================
# الـ Singleton
# ============================================================

_pctrl_instance: Optional[PredictiveController] = None
_pctrl_lock = threading.Lock()


def get_predictive_controller() -> PredictiveController:
    """الحصول على النسخة الوحيدة من المتحكم التنبؤي"""
    global _pctrl_instance
    if _pctrl_instance is None:
        with _pctrl_lock:
            if _pctrl_instance is None:
                _pctrl_instance = PredictiveController()
    return _pctrl_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧠 المتحكم الطبقي للتنبؤ - اختبار سريع")
    print("=" * 80 + "\n")
    
    pc = get_predictive_controller()
    
    # تغيير الوضع
    pc.set_mode(PREDICTIVE_MODE_BALANCED)
    print(f"وضع التشغيل: {pc.get_mode()}")
    
    # تشغيل دورة تحكم
    snap = pc.predictive_controller_cycle()
    print(f"اللقطة: {snap.timestamp}")
    print(f"عدد السيناريوهات: {len(snap.scenarios)}")
    print(f"القرار: {snap.predictive_decision.get('primary_scenario', 'لا يوجد')}")
    print(f"الثقة: {snap.predictive_decision.get('confidence', 0):.1%}")
    
    # إحصائيات
    print(f"\nإحصائيات المتحكم: {pc.get_stats()}")
    
    print("\n" + "=" * 80)
    print("✅ المتحكم الطبقي للتنبؤ جاهز - ينسق محركات التنبؤ الأربعة")
    print("=" * 80)
