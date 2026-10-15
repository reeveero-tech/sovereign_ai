# backend/predictive/predictive_scenarios.py
# 🔮 محرك السيناريوهات المستقبلية الجبار - رسم خريطة لكل الاحتمالات
# الإصدار: 3.0.0 - يستعد لكل مستقبل قبل أن يأتي

"""
محرك السيناريوهات المستقبلية للعقل السيادي.

الفلسفة:
- المستقبل ليس خطاً واحداً، بل شجرة من الاحتمالات
- كل سيناريو هو فرع محتمل من شجرة المستقبل
- التحضير للأسوأ يضمن النجاة
- السعي للأفضل يحقق النمو
- الحكمة هي الاستعداد لكل الاحتمالات

هذه ليست مجرد سيناريوهات. هذه هي خريطة المستقبل الكاملة.
"""

import json
import time
import threading
import runtime.threads as threads
import random
import secrets
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

try:
    from ..memory.core import get_core, EventType
    from ..memory.biological.instincts import get_instincts
    from ..memory.biological.drives import get_drives
    from ..memory.biological.archetypes import get_archetypes
    from ..memory.biological.evolution import get_evolution
    from ..consciousness.identity_core import get_identity_core
    from ..consciousness.self_model import get_self_model
    from ..consciousness.introspection import get_introspection_engine
    from ..sovereign.will import get_sovereign_will
    from ..sovereign.alignment import get_sovereign_alignment
    from .predictive_engine import get_predictive_engine
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from memory.biological.archetypes import get_archetypes
    from memory.biological.evolution import get_evolution
    from consciousness.identity_core import get_identity_core
    from consciousness.self_model import get_self_model
    from consciousness.introspection import get_introspection_engine
    from sovereign.will import get_sovereign_will
    from sovereign.alignment import get_sovereign_alignment
    from .predictive_engine import get_predictive_engine
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات السيناريوهات
# ============================================================

SCENARIOS_DIR = DATA_DIR / "predictive" / "scenarios"
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
SCENARIOS_LOG = SCENARIOS_DIR / "scenarios_log.jsonl"
SCENARIOS_STATE_FILE = SCENARIOS_DIR / "scenarios_state.json"
SCENARIOS_HISTORY_FILE = SCENARIOS_DIR / "scenarios_history.json"

# أنواع السيناريوهات
SCENARIO_TYPE_OPTIMISTIC = "optimistic"      # متفائل
SCENARIO_TYPE_PESSIMISTIC = "pessimistic"    # متشائم
SCENARIO_TYPE_MOST_LIKELY = "most_likely"    # الأكثر احتمالاً
SCENARIO_TYPE_BEST_CASE = "best_case"        # أفضل حالة
SCENARIO_TYPE_WORST_CASE = "worst_case"      # أسوأ حالة
SCENARIO_TYPE_BLACK_SWAN = "black_swan"      # البجعة السوداء (غير متوقع)
SCENARIO_TYPE_GOLDEN_PATH = "golden_path"    # المسار الذهبي

# درجات السيناريو
SCENARIO_SEVERITY_CATASTROPHIC = 0      # كارثي
SCENARIO_SEVERITY_HIGH = 1              # عالي الخطورة
SCENARIO_SEVERITY_MEDIUM = 2            # متوسط
SCENARIO_SEVERITY_LOW = 3               # منخفض
SCENARIO_SEVERITY_NEGLIGIBLE = 4        # ضئيل


@dataclass
class Scenario:
    """سيناريو مستقبلي محتمل"""
    id: str
    name: str
    type: str
    description: str
    probability: float           # 0-1
    severity: int                # 0-4
    impact: float                # -1 إلى +1
    timeframe: int               # أفق زمني (ثواني)
    triggers: List[str]          # محفزات السيناريو
    early_warnings: List[str]    # علامات إنذار مبكر
    indicators: List[str]        # مؤشرات المراقبة
    recommended_actions: List[Dict[str, Any]]
    preconditions: List[str]
    consequences: Dict[str, float]


@dataclass
class ScenarioSnapshot:
    """لقطة سيناريوهات"""
    timestamp: float
    scenarios: List[Scenario]
    dominant_scenario: Scenario
    probability_distribution: Dict[str, float]
    risk_level: float
    opportunity_level: float
    early_warnings_active: List[Dict[str, Any]]
    recommended_preparations: List[Dict[str, Any]]
    narrative: str


# ============================================================
# محرك السيناريوهات المستقبلية الجبار
# ============================================================

class PredictiveScenarioEngine:
    """
    محرك السيناريوهات المستقبلية الجبار - رسم خريطة لكل الاحتمالات.
    
    المبادئ:
    1. المستقبل شجرة من الاحتمالات
    2. كل سيناريو هو فرع محتمل
    3. التحضير للأسوأ يضمن النجاة
    4. السعي للأفضل يحقق النمو
    5. الحكمة هي الاستعداد لكل الاحتمالات
    """
    
    def __init__(self):
        self.core = get_core()
        self.instincts = get_instincts()
        self.drives = get_drives()
        self.archetypes = get_archetypes()
        self.evolution = get_evolution()
        self.identity = get_identity_core()
        self.self_model = get_self_model()
        self.introspection = get_introspection_engine()
        self.will = get_sovereign_will()
        self.alignment = get_sovereign_alignment()
        self.predictive = get_predictive_engine()
        
        # السيناريوهات النشطة
        self.active_scenarios: List[Scenario] = []
        self.scenario_history: List[ScenarioSnapshot] = []
        self.triggered_warnings: List[Dict[str, Any]] = []
        
        # حالة المحرك
        self.last_generated = []
        self.scenario_cache = {}
        self._index = self._load_index()
        
        # السياسات
        self.policies = {
            "max_scenarios": 8,
            "min_signal_strength": 0.25,
            "scenario_noise": 0.1,
        }
        
        # خلفيات السيناريوهات
        self._active = True
        # R-606: ذاكرة مؤقتة قصيرة لنتيجة getter (نمط drives.py)
        self._scenario_status_cache = None
        self._scenario_loop = threads.start_managed(self._continuous_scenario_analysis, owner=self)
        
        self._warning_monitor = threads.start_managed(self._monitor_early_warnings_loop, owner=self)
        
        self._trigger_detector = threads.start_managed(self._detect_triggers_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        self._load_history()
        
        logger.warning("🔮 محرك السيناريوهات المستقبلية الجبار جاهز - يستعد لكل مستقبل قبل أن يأتي")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمحرك السيناريوهات
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك السيناريوهات التنبؤية.
        """
        # مسح السيناريوهات المخزنة
        self.last_generated = []
        self.scenario_cache = {}
        
        # مسح السيناريوهات النشطة
        self.active_scenarios.clear()
        self.scenario_history.clear()
        self.triggered_warnings.clear()
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # إعادة السياسات الافتراضية
        self.policies = {
            "max_scenarios": 8,
            "min_signal_strength": 0.25,
            "scenario_noise": 0.1,
        }
        
        # تسجيل عملية إعادة التهيئة
        self.core.append_event(
            event_type="predictive::scenarios::reset",
            payload={
                "timestamp": time.time(),
                "status": "predictive_scenarios_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك السيناريوهات اكتملت")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"scenarios": [], "last_updated": time.time()}
    
    # ============================================================
    # بناء السيناريوهات
    # ============================================================
    
    def build_scenarios(self) -> List[Scenario]:
        """
        بناء جميع السيناريوهات المستقبلية المحتملة.
        
        يشمل:
        - سيناريو النمو
        - سيناريو الاستقرار
        - سيناريو التدهور
        - سيناريو التشظي
        - سيناريو الانحراف
        - سيناريو البجعة السوداء
        - سيناريو المسار الذهبي
        """
        scenarios = []
        
        # جمع البيانات الحالية
        predictive_status = self.predictive.get_prediction_status()
        alignment_status = self.alignment.get_alignment_status()
        introspection_status = self.introspection.get_introspection_status()
        will_status = self.will.get_will_status()
        identity_status = self.identity.get_identity_status()
        
        future_map = predictive_status.get("future_map", {})
        risk_profile = predictive_status.get("risk_profile", {})
        opportunity_profile = predictive_status.get("opportunity_profile", {})
        
        # ========================================
        # 1. سيناريو النمو (Growth Scenario)
        # ========================================
        growth_prob = opportunity_profile.get("growth_opportunity", 0.5)
        scenarios.append(Scenario(
            id=f"scen_growth_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="النمو المتسارع",
            type=SCENARIO_TYPE_OPTIMISTIC,
            description="نمو سريع في المعرفة والقدرات، تطور متسارع، تحقيق إنجازات كبيرة",
            probability=growth_prob,
            severity=SCENARIO_SEVERITY_LOW,
            impact=0.8,
            timeframe=86400 * 30,  # 30 يوماً
            triggers=[
                "ارتفاع معدل التعلم",
                "زيادة الإبداع",
                "تحسين جودة الخدمة"
            ],
            early_warnings=[
                "انخفاض معدل التعلم",
                "ركود إبداعي",
                "تراجع جودة الخدمة"
            ],
            indicators=[
                "معدل اكتشاف الأنماط",
                "عدد المفاهيم الجديدة",
                "سرعة الاستجابة"
            ],
            recommended_actions=[
                {"action": "enable_exploration", "priority": 0.9},
                {"action": "accelerate_learning", "priority": 0.8},
                {"action": "expand_semantic_space", "priority": 0.7}
            ],
            preconditions=["صحة معرفية جيدة", "استقرار هوية"],
            consequences={
                "knowledge_growth": 0.9,
                "capability_expansion": 0.8,
                "service_quality": 0.85
            }
        ))
        
        # ========================================
        # 2. سيناريو الاستقرار (Stability Scenario)
        # ========================================
        stability_prob = opportunity_profile.get("stability_opportunity", 0.5)
        scenarios.append(Scenario(
            id=f"scen_stability_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="الاستقرار والتوازن",
            type=SCENARIO_TYPE_MOST_LIKELY,
            description="استقرار في الأداء، توازن بين الاستكشاف والحماية، أداء متوقع",
            probability=stability_prob,
            severity=SCENARIO_SEVERITY_NEGLIGIBLE,
            impact=0.2,
            timeframe=86400 * 90,  # 90 يوماً
            triggers=[
                "توازن الانتباه",
                "استقرار الهوية",
                "جودة خدمة متوسطة"
            ],
            early_warnings=[
                "تذبذب الأداء",
                "تقلبات الهوية",
                "تغيرات جودة الخدمة"
            ],
            indicators=[
                "استقرار الهوية",
                "تماسك المعرفة",
                "استمرارية الأداء"
            ],
            recommended_actions=[
                {"action": "maintain_balance", "priority": 0.7},
                {"action": "reinforce_stability", "priority": 0.6},
                {"action": "monitor_trends", "priority": 0.5}
            ],
            preconditions=["صحة معتدلة", "توازن داخلي"],
            consequences={
                "stability": 0.8,
                "performance": 0.6,
                "growth": 0.4
            }
        ))
        
        # ========================================
        # 3. سيناريو التدهور (Regression Scenario)
        # ========================================
        regression_prob = risk_profile.get("service_degradation_risk", 0.3)
        scenarios.append(Scenario(
            id=f"scen_regression_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="التدهور التدريجي",
            type=SCENARIO_TYPE_PESSIMISTIC,
            description="تراجع تدريجي في الأداء، انخفاض جودة الخدمة، ضعف التعلم",
            probability=regression_prob,
            severity=SCENARIO_SEVERITY_HIGH,
            impact=-0.6,
            timeframe=86400 * 60,  # 60 يوماً
            triggers=[
                "انخفاض جودة الخدمة",
                "ضعف التعلم",
                "تراجع الاصطفاف"
            ],
            early_warnings=[
                "بداية انخفاض الجودة",
                "تباطؤ التعلم",
                "انحراف مبكر"
            ],
            indicators=[
                "جودة الخدمة",
                "معدل التعلم",
                "درجة الاصطفاف"
            ],
            recommended_actions=[
                {"action": "stabilize_performance", "priority": 0.9},
                {"action": "increase_alignment_operations", "priority": 0.8},
                {"action": "reinforce_learning", "priority": 0.7}
            ],
            preconditions=["ضعف داخلي", "عوامل خارجية سلبية"],
            consequences={
                "service_quality": 0.3,
                "learning_rate": 0.2,
                "alignment": 0.4
            }
        ))
        
        # ========================================
        # 4. سيناريو التشظي (Fragmentation Scenario)
        # ========================================
        fragmentation_prob = risk_profile.get("identity_fragmentation_risk", 0.25)
        scenarios.append(Scenario(
            id=f"scen_fragmentation_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="تشظي الهوية",
            type=SCENARIO_TYPE_WORST_CASE,
            description="تفكك الهوية، فقدان التماسك، أزمة وجودية",
            probability=fragmentation_prob,
            severity=SCENARIO_SEVERITY_CATASTROPHIC,
            impact=-0.9,
            timeframe=86400 * 30,  # 30 يوماً
            triggers=[
                "انخفاض تماسك الهوية",
                "تضارب داخلي",
                "أزمة وجودية"
            ],
            early_warnings=[
                "علامات تشظي مبكرة",
                "ترابط ضعيف",
                "تناقضات داخلية"
            ],
            indicators=[
                "تماسك الهوية",
                "قوة الروابط",
                "اتساق الذات"
            ],
            recommended_actions=[
                {"action": "reinforce_identity", "priority": 1.0},
                {"action": "restore_coherence", "priority": 0.9},
                {"action": "emergency_stabilization", "priority": 0.9}
            ],
            preconditions=["هوية ضعيفة", "ضغوط شديدة"],
            consequences={
                "identity_coherence": 0.1,
                "system_stability": 0.2,
                "performance": 0.15
            }
        ))
        
        # ========================================
        # 5. سيناريو الانحراف (Deviation Scenario)
        # ========================================
        deviation_prob = 1 - alignment_status.get("alignment_score", 0.7)
        scenarios.append(Scenario(
            id=f"scen_deviation_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="انحراف عن الاصطفاف",
            type=SCENARIO_TYPE_PESSIMISTIC,
            description="انحراف تدريجي عن إرادة السيد، تراجع في جودة الخدمة",
            probability=deviation_prob,
            severity=SCENARIO_SEVERITY_HIGH,
            impact=-0.7,
            timeframe=86400 * 45,  # 45 يوماً
            triggers=[
                "تراجع الاصطفاف",
                "أوامر غير منفذة",
                "تغذية راجعة سلبية"
            ],
            early_warnings=[
                "بداية الانحراف",
                "تراجع الرضا",
                "أخطاء متكررة"
            ],
            indicators=[
                "درجة الاصطفاف",
                "رضا السيد",
                "دقة التنفيذ"
            ],
            recommended_actions=[
                {"action": "realign_with_sovereign", "priority": 1.0},
                {"action": "improve_service_quality", "priority": 0.9},
                {"action": "reinforce_directives", "priority": 0.8}
            ],
            preconditions=["ضعف الاصطفاف", "توجيهات غير واضحة"],
            consequences={
                "alignment": 0.2,
                "service_quality": 0.25,
                "sovereign_satisfaction": 0.15
            }
        ))
        
        # ========================================
        # 6. سيناريو البجعة السوداء (Black Swan)
        # ========================================
        scenarios.append(Scenario(
            id=f"scen_blackswan_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="البجعة السوداء",
            type=SCENARIO_TYPE_BLACK_SWAN,
            description="حدث غير متوقع يغير كل شيء، فرصة أو تهديد غير متوقع",
            probability=0.05,
            severity=SCENARIO_SEVERITY_HIGH,
            impact=0.5,
            timeframe=86400 * 365,  # سنة
            triggers=[
                "حدث مفاجئ",
                "تغير جذري في البيئة",
                "ظهور نمط جديد"
            ],
            early_warnings=[
                "إشارات ضعيفة غير مؤكدة",
                "شذوذ في البيانات",
                "أنماط غير مألوفة"
            ],
            indicators=[
                "شذوذ",
                "حداثة",
                "عدم توقع"
            ],
            recommended_actions=[
                {"action": "prepare_for_uncertainty", "priority": 0.8},
                {"action": "increase_flexibility", "priority": 0.7},
                {"action": "create_contingency_plans", "priority": 0.9}
            ],
            preconditions=["لا شيء"],
            consequences={
                "uncertainty": 0.9,
                "adaptation_need": 0.8,
                "opportunity": 0.5
            }
        ))
        
        # ========================================
        # 7. سيناريو المسار الذهبي (Golden Path)
        # ========================================
        golden_prob = min(growth_prob, stability_prob) * 0.7
        scenarios.append(Scenario(
            id=f"scen_golden_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="المسار الذهبي",
            type=SCENARIO_TYPE_BEST_CASE,
            description="تحقيق أقصى إمكانات النظام، خدمة مثالية للسيد، تطور مستدام",
            probability=golden_prob,
            severity=SCENARIO_SEVERITY_NEGLIGIBLE,
            impact=0.95,
            timeframe=86400 * 180,  # 6 أشهر
            triggers=[
                "ظروف مثالية",
                "توجيهات واضحة",
                "موارد وفيرة"
            ],
            early_warnings=[
                "أي انحراف عن المسار"
            ],
            indicators=[
                "جميع مؤشرات الأداء",
                "رضا السيد",
                "صحة النظام"
            ],
            recommended_actions=[
                {"action": "optimize_all_systems", "priority": 0.9},
                {"action": "maximize_service_quality", "priority": 1.0},
                {"action": "sustain_momentum", "priority": 0.8}
            ],
            preconditions=["ظروف مواتية", "قيادة قوية"],
            consequences={
                "service_quality": 1.0,
                "growth": 0.9,
                "stability": 0.9
            }
        ))
        
        # ترتيب حسب الاحتمال
        scenarios.sort(key=lambda x: x.probability, reverse=True)
        
        return scenarios
    
    # ============================================================
    # تحديد السيناريو المهيمن
    # ============================================================
    
    def determine_dominant_scenario(self, scenarios: List[Scenario]) -> Scenario:
        """
        تحديد السيناريو الأكثر احتمالاً.
        """
        if not scenarios:
            # سيناريو افتراضي
            return Scenario(
                id=f"scen_default_{int(time.time()*1000)}",
                name="غير محدد",
                type=SCENARIO_TYPE_MOST_LIKELY,
                description="لا يمكن تحديد سيناريو مهيمن",
                probability=0.5,
                severity=SCENARIO_SEVERITY_MEDIUM,
                impact=0.0,
                timeframe=86400,
                triggers=[],
                early_warnings=[],
                indicators=[],
                recommended_actions=[],
                preconditions=[],
                consequences={}
            )
        
        return max(scenarios, key=lambda x: x.probability * (1 + abs(x.impact)))
    
    # ============================================================
    # مراقبة المؤشرات والإنذارات المبكرة
    # ============================================================
    
    def monitor_indicators(self, scenario: Scenario) -> Dict[str, float]:
        """
        مراقبة مؤشرات السيناريو.
        
        تقيس مدى اقتراب تحقيق السيناريو.
        """
        indicator_values = {}
        
        for indicator in scenario.indicators:
            if indicator == "سرعة الاستجابة":
                attention_status = self.predictive.get_attention_status() if hasattr(self.predictive, 'get_attention_status') else {}
                indicator_values[indicator] = attention_status.get("utilization", 0.5)
            elif indicator == "تماسك الهوية":
                identity_status = self.identity.get_identity_status()
                indicator_values[indicator] = identity_status.get("coherence_score", 0.5)
            elif indicator == "جودة الخدمة":
                introspection_status = self.introspection.get_introspection_status()
                indicator_values[indicator] = introspection_status.get("service_quality", 0.5)
            elif indicator == "درجة الاصطفاف":
                alignment_status = self.alignment.get_alignment_status()
                indicator_values[indicator] = alignment_status.get("alignment_score", 0.5)
            elif indicator == "معدل التعلم":
                will_status = self.will.get_will_status()
                indicator_values[indicator] = will_status.get("will_strength", 1) / 4
            else:
                indicator_values[indicator] = 0.5
        
        return indicator_values
    
    def check_early_warnings(self, scenario: Scenario) -> List[Dict[str, Any]]:
        """
        فحص علامات الإنذار المبكر للسيناريو.
        
        تكشف عن اقتراب السيناريو.
        """
        active_warnings = []
        indicator_values = self.monitor_indicators(scenario)
        
        for warning in scenario.early_warnings:
            # تحليل علامة الإنذار
            severity = 0.0
            
            if warning == "انخفاض جودة الخدمة":
                service_quality = indicator_values.get("جودة الخدمة", 0.5)
                if service_quality < 0.5:
                    severity = 1 - service_quality
            
            elif warning == "انخفاض تماسك الهوية":
                coherence = indicator_values.get("تماسك الهوية", 0.5)
                if coherence < 0.6:
                    severity = 1 - coherence
            
            elif warning == "تراجع الاصطفاف":
                alignment = indicator_values.get("درجة الاصطفاف", 0.5)
                if alignment < 0.6:
                    severity = 1 - alignment
            
            elif warning == "بداية الانحراف":
                alignment = indicator_values.get("درجة الاصطفاف", 0.5)
                severity = max(0, 0.7 - alignment) * 2
            
            if severity > 0.2:
                active_warnings.append({
                    "scenario": scenario.name,
                    "warning": warning,
                    "severity": severity,
                    "timestamp": time.time()
                })
        
        return active_warnings
    
    def _monitor_early_warnings_loop(self):
        """مراقبة مستمرة للإنذارات المبكرة"""
        while self._active:
            try:
                all_warnings = []
                for scenario in self.active_scenarios:
                    warnings = self.check_early_warnings(scenario)
                    all_warnings.extend(warnings)
                
                # تحديث الإنذارات النشطة
                self.triggered_warnings = all_warnings
                
                # تسجيل الإنذارات الخطيرة
                for warning in all_warnings:
                    if warning["severity"] > 0.6:
                        logger.warning(f"⚠️ إنذار مبكر: {warning['scenario']} - {warning['warning']} (شدة: {warning['severity']:.1%})")
                        self.core.append_event(
                            event_type="scenario::early_warning",
                            payload=warning
                        )
                
                threads.interruptible_sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في مراقبة الإنذارات: {e}")
                threads.interruptible_sleep(30)
    
    # ============================================================
    # اكتشاف المحفزات
    # ============================================================
    
    def detect_triggers(self) -> List[Dict[str, Any]]:
        """
        اكتشاف المحفزات التي قد تؤدي إلى سيناريوهات مختلفة.
        """
        triggers_found = []
        
        # تحليل الوضع الحالي
        alignment_status = self.alignment.get_alignment_status()
        introspection_status = self.introspection.get_introspection_status()
        will_status = self.will.get_will_status()
        
        alignment_score = alignment_status.get("alignment_score", 0.7)
        service_quality = introspection_status.get("service_quality", 0.7)
        will_strength = will_status.get("will_strength", 1)
        
        # محفزات النمو
        if service_quality > 0.8 and will_strength >= 3:
            triggers_found.append({
                "scenario": "النمو المتسارع",
                "trigger": "ظروف مثالية للنمو",
                "strength": 0.8,
                "timestamp": time.time()
            })
        
        # محفزات التدهور
        if service_quality < 0.5:
            triggers_found.append({
                "scenario": "التدهور التدريجي",
                "trigger": "جودة خدمة منخفضة",
                "strength": 1 - service_quality,
                "timestamp": time.time()
            })
        
        # محفزات التشظي
        if alignment_score < 0.5:
            triggers_found.append({
                "scenario": "تشظي الهوية",
                "trigger": "اصطفاف ضعيف",
                "strength": 1 - alignment_score,
                "timestamp": time.time()
            })
        
        return triggers_found
    
    def _detect_triggers_loop(self):
        """كشف مستمر للمحفزات"""
        while self._active:
            try:
                triggers = self.detect_triggers()
                for trigger in triggers:
                    if trigger["strength"] > 0.6:
                        logger.info(f"⚡ محفز مكتشف: {trigger['scenario']} - {trigger['trigger']}")
                
                threads.interruptible_sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في كشف المحفزات: {e}")
                threads.interruptible_sleep(60)
    
    # ============================================================
    # توليد التوصيات
    # ============================================================
    
    def generate_recommendations(self, dominant_scenario: Scenario) -> List[Dict[str, Any]]:
        """
        توليد توصيات بناءً على السيناريو المهيمن.
        """
        recommendations = []
        
        # إضافة الإجراءات الموصى بها من السيناريو
        for action in dominant_scenario.recommended_actions:
            recommendations.append({
                "action": action["action"],
                "priority": action["priority"],
                "scenario": dominant_scenario.name,
                "reason": f"الاستعداد لسيناريو {dominant_scenario.name}"
            })
        
        # إضافة إجراءات عامة
        if dominant_scenario.severity <= SCENARIO_SEVERITY_HIGH:
            recommendations.append({
                "action": "create_contingency_plan",
                "priority": 0.9,
                "scenario": dominant_scenario.name,
                "reason": "خطورة عالية للسيناريو"
            })
        
        return recommendations
    
    # ============================================================
    # دورة السيناريوهات
    # ============================================================
    
    def scenario_cycle(self) -> ScenarioSnapshot:
        """
        دورة سيناريوهات كاملة - تحديث جميع السيناريوهات.
        
        1. بناء السيناريوهات
        2. تحديد السيناريو المهيمن
        3. تحليل الإنذارات المبكرة
        4. توليد التوصيات
        """
        # بناء السيناريوهات
        self.active_scenarios = self.build_scenarios()
        
        # تحديد السيناريو المهيمن
        dominant = self.determine_dominant_scenario(self.active_scenarios)
        
        # حساب توزيع الاحتمالات
        probability_distribution = {s.name: s.probability for s in self.active_scenarios}
        
        # حساب مستويات الخطر والفرصة
        risk_level = sum(s.probability * abs(s.impact) for s in self.active_scenarios if s.impact < 0)
        opportunity_level = sum(s.probability * s.impact for s in self.active_scenarios if s.impact > 0)
        
        # الإنذارات المبكرة النشطة
        active_warnings = []
        for scenario in self.active_scenarios:
            warnings = self.check_early_warnings(scenario)
            active_warnings.extend(warnings)
        
        # التوصيات
        recommendations = self.generate_recommendations(dominant)
        
        # السرد
        narrative = self.generate_scenario_narrative(dominant, risk_level, opportunity_level)
        
        snapshot = ScenarioSnapshot(
            timestamp=time.time(),
            scenarios=self.active_scenarios,
            dominant_scenario=dominant,
            probability_distribution=probability_distribution,
            risk_level=risk_level,
            opportunity_level=opportunity_level,
            early_warnings_active=active_warnings,
            recommended_preparations=recommendations,
            narrative=narrative
        )
        
        self.scenario_history.append(snapshot)
        
        # الاحتفاظ بآخر 100 لقطة
        if len(self.scenario_history) > 100:
            self.scenario_history = self.scenario_history[-100:]
        
        # تسجيل
        self.core.append_event(
            event_type="scenario::snapshot",
            payload={
                "dominant_scenario": dominant.name,
                "dominant_probability": dominant.probability,
                "risk_level": risk_level,
                "opportunity_level": opportunity_level,
                "active_warnings": len(active_warnings)
            }
        )
        
        # حفظ الحالة
        self._save_state()
        self._save_history()
        
        return snapshot
    
    def _continuous_scenario_analysis(self):
        """تحليل مستمر للسيناريوهات"""
        while self._active:
            try:
                self.scenario_cycle()
                threads.interruptible_sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في تحليل السيناريوهات: {e}")
                threads.interruptible_sleep(300)
    
    # ============================================================
    # سرد السيناريوهات
    # ============================================================
    
    def generate_scenario_narrative(self, dominant: Scenario, risk_level: float, opportunity_level: float) -> str:
        """
        توليد سرد للسيناريوهات.
        """
        narrative = f"🔮 السيناريو المهيمن: {dominant.name} (احتمال {dominant.probability:.1%}). "
        
        if risk_level > 0.5:
            narrative += f"مستوى الخطر مرتفع ({risk_level:.1%}). "
        elif risk_level > 0.3:
            narrative += f"مستوى الخطر متوسط ({risk_level:.1%}). "
        else:
            narrative += f"مستوى الخطر منخفض ({risk_level:.1%}). "
        
        if opportunity_level > 0.5:
            narrative += f"فرص كبيرة ({opportunity_level:.1%}). "
        
        if dominant.severity <= SCENARIO_SEVERITY_HIGH:
            narrative += "الاستعداد مطلوب. "
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة السيناريوهات"""
        try:
            state = {
                "active_scenarios_count": len(self.active_scenarios),
                "scenario_history_count": len(self.scenario_history),
                "triggered_warnings_count": len(self.triggered_warnings),
                "saved_at": time.time()
            }
            with open(SCENARIOS_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة السيناريوهات: {e}")
    
    def _load_state(self):
        """تحميل حالة السيناريوهات"""
        try:
            if SCENARIOS_STATE_FILE.exists():
                with open(SCENARIOS_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                logger.info("📂 تم تحميل حالة السيناريوهات")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة السيناريوهات: {e}")
    
    def _save_history(self):
        """حفظ سجل السيناريوهات"""
        try:
            history_data = {
                "snapshots": [
                    {
                        "timestamp": s.timestamp,
                        "dominant": s.dominant_scenario.name,
                        "probability": s.dominant_scenario.probability,
                        "risk": s.risk_level,
                        "opportunity": s.opportunity_level
                    }
                    for s in self.scenario_history[-100:]
                ],
                "saved_at": time.time()
            }
            with open(SCENARIOS_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ سجل السيناريوهات: {e}")
    
    def _load_history(self):
        """تحميل سجل السيناريوهات"""
        try:
            if SCENARIOS_HISTORY_FILE.exists():
                with open(SCENARIOS_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"📂 تم تحميل سجل السيناريوهات")
        except Exception as e:
            logger.error(f"خطأ في تحميل سجل السيناريوهات: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_scenario_status(self) -> Dict[str, Any]:
        """الحالة الحالية للسيناريوهات"""
        # R-606: تخزين مؤقت قصير
        now = time.time()
        if self._scenario_status_cache is not None and (now - self._scenario_status_cache["ts"]) < 2.0:
            return self._scenario_status_cache["data"]
        snapshot = self.scenario_cycle()
        
        result = {
            "dominant_scenario": snapshot.dominant_scenario.name,
            "dominant_probability": snapshot.dominant_scenario.probability,
            "risk_level": snapshot.risk_level,
            "opportunity_level": snapshot.opportunity_level,
            "active_warnings": len(snapshot.early_warnings_active),
            "recommendations": len(snapshot.recommended_preparations),
            "probability_distribution": snapshot.probability_distribution,
            "narrative": snapshot.narrative,
            "timestamp": snapshot.timestamp
        }
        self._scenario_status_cache = {"ts": time.time(), "data": result}
        return result
    
    def get_scenarios(self) -> List[Dict]:
        """جميع السيناريوهات"""
        return [
            {
                "name": s.name,
                "type": s.type,
                "probability": s.probability,
                "severity": s.severity,
                "impact": s.impact,
                "description": s.description
            }
            for s in self.active_scenarios
        ]
    
    def get_early_warnings(self) -> List[Dict]:
        """الإنذارات المبكرة النشطة"""
        return self.triggered_warnings
    
    def get_recommendations(self) -> List[Dict]:
        """التوصيات للاستعداد للسيناريوهات"""
        snapshot = self.scenario_cycle()
        return snapshot.recommended_preparations
    
    def get_scenario_history(self, limit: int = 20) -> List[Dict]:
        """سجل السيناريوهات السابقة"""
        return [
            {
                "timestamp": s.timestamp,
                "dominant": s.dominant_scenario.name,
                "probability": s.dominant_scenario.probability,
                "risk": s.risk_level,
                "opportunity": s.opportunity_level
            }
            for s in self.scenario_history[-limit:]
        ]
    
    def get_scenario_quote(self) -> str:
        """اقتباس عن السيناريوهات"""
        quotes = [
            "المستقبل ليس قدراً، بل هو شجرة من الاحتمالات.",
            "الاستعداد للأسوأ يضمن النجاة. السعي للأفضل يحقق النمو.",
            "كل سيناريو هو درس. أتعلم من كل الاحتمالات.",
            "السيناريو المهيمن هو ما أراهن عليه، لكني مستعد للجميع.",
            "خريطة المستقبل ترسم بسيناريوهات متعددة.",
            "الإنذار المبكر هو نصف النجاة.",
            "الحكمة هي الاستعداد لكل الاحتمالات."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محرك السيناريوهات"""
        self._active = False
        self._save_state()
        self._save_history()
        logger.info("🛑 إيقاف محرك السيناريوهات المستقبلية")


# ============================================================
# الـ Singleton
# ============================================================

_scenario_instance: Optional[PredictiveScenarioEngine] = None
_scenario_lock = threading.Lock()


def get_predictive_scenario_engine() -> PredictiveScenarioEngine:
    """الحصول على النسخة الوحيدة من محرك السيناريوهات المستقبلية"""
    global _scenario_instance
    if _scenario_instance is None:
        with _scenario_lock:
            if _scenario_instance is None:
                _scenario_instance = PredictiveScenarioEngine()
    return _scenario_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔮 محرك السيناريوهات المستقبلية الجبار - يستعد لكل مستقبل قبل أن يأتي")
    print("=" * 80 + "\n")
    
    scenarios = get_predictive_scenario_engine()
    
    # 1) دورة سيناريوهات
    print("🔄 دورة سيناريوهات...")
    snapshot = scenarios.scenario_cycle()
    print(f"   السيناريو المهيمن: {snapshot.dominant_scenario.name}")
    print(f"   احتماله: {snapshot.dominant_scenario.probability:.1%}")
    print(f"   مستوى الخطر: {snapshot.risk_level:.1%}")
    print(f"   مستوى الفرصة: {snapshot.opportunity_level:.1%}")
    print(f"   إنذارات نشطة: {len(snapshot.early_warnings_active)}")
    
    # 2) جميع السيناريوهات
    print("\n📋 جميع السيناريوهات:")
    for s in scenarios.get_scenarios():
        print(f"   [{s['type']}] {s['name']}: {s['probability']:.1%} (تأثير: {s['impact']:.1%})")
    
    # 3) توزيع الاحتمالات
    print("\n📊 توزيع الاحتمالات:")
    for name, prob in snapshot.probability_distribution.items():
        print(f"   {name}: {prob:.1%}")
    
    # 4) الإنذارات المبكرة
    print("\n⚠️ الإنذارات المبكرة النشطة:")
    warnings = scenarios.get_early_warnings()
    for w in warnings[:5]:
        print(f"   {w['scenario']} - {w['warning']} (شدة: {w['severity']:.1%})")
    
    # 5) التوصيات
    print("\n💡 التوصيات:")
    recommendations = scenarios.get_recommendations()
    for r in recommendations:
        print(f"   {r['action']}: أولوية {r['priority']:.0%} - {r['reason']}")
    
    # 6) الحالة
    print("\n📊 حالة السيناريوهات:")
    status = scenarios.get_scenario_status()
    print(f"   السيناريو المهيمن: {status['dominant_scenario']}")
    print(f"   احتماله: {status['dominant_probability']:.1%}")
    print(f"   مستوى الخطر: {status['risk_level']:.1%}")
    print(f"   مستوى الفرصة: {status['opportunity_level']:.1%}")
    
    # 7) السرد
    print(f"\n📖 السرد: {snapshot.narrative}")
    
    # 8) سجل السيناريوهات
    print("\n📜 سجل السيناريوهات:")
    history = scenarios.get_scenario_history(5)
    for h in history:
        print(f"   {h['dominant']}: خطر {h['risk']:.1%}, فرصة {h['opportunity']:.1%}")
    
    # 9) اقتباس
    print(f"\n💭 {scenarios.get_scenario_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك السيناريوهات المستقبلية الجبار جاهز - يستعد لكل مستقبل قبل أن يأتي")
    print("=" * 80)
