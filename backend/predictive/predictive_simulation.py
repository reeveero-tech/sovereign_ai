# backend/predictive/predictive_simulation.py
# 🔮 محرك المحاكاة التنبؤية الجبار - محاكاة آلاف المسارات المستقبلية
# الإصدار: 3.0.0 - يحاكي كل احتمال، يحلل كل مسار

"""
محرك المحاكاة التنبؤية للعقل السيادي.

الفلسفة:
- المحاكاة هي مختبر المستقبل
- كل مسار محتمل يمكن محاكاته وتحليله
- آلاف المحاكاة تعطي صورة إحصائية دقيقة
- المحاكاة تكشف عن المخفي وتتنبأ بالمستقبل
- المحاكاة الجيدة تنقذ من المفاجآت

هذه ليست مجرد محاكاة. هذه هي معمليات المستقبل.
"""

import json
from runtime.atomic_json import atomic_write_json  # R-781
import time
import threading
import runtime.threads as threads
import random
import secrets
import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

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
    from .predictive_scenarios import get_predictive_scenario_engine
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
    from .predictive_scenarios import get_predictive_scenario_engine
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات المحاكاة
# ============================================================

SIMULATION_DIR = DATA_DIR / "predictive" / "simulation"
SIMULATION_DIR.mkdir(parents=True, exist_ok=True)
SIMULATION_LOG = SIMULATION_DIR / "simulation_log.jsonl"
SIMULATION_STATE_FILE = SIMULATION_DIR / "simulation_state.json"
SIMULATION_RESULTS_DIR = SIMULATION_DIR / "results"

SIMULATION_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# أنواع المحاكاة
SIMULATION_TYPE_MONTE_CARLO = "monte_carlo"      # مونت كارلو
SIMULATION_TYPE_BOOTSTRAP = "bootstrap"          # بوتستراب
SIMULATION_TYPE_MARKOV = "markov"                # ماركوف
SIMULATION_TYPE_BROWNIAN = "brownian"            # حركة براونية
SIMULATION_TYPE_AGENT_BASED = "agent_based"      # قائم على وكلاء
SIMULATION_TYPE_HYBRID = "hybrid"                # هجين

# آفاق المحاكاة
SIMULATION_HORIZON_SHORT = 1        # قصير (أيام)
SIMULATION_HORIZON_MEDIUM = 2       # متوسط (أسابيع)
SIMULATION_HORIZON_LONG = 3         # طويل (شهور)
SIMULATION_HORIZON_EPIC = 4         # ملحمي (سنوات)


@dataclass
class SimulationTrajectory:
    """مسار محاكاة واحد"""
    id: str
    run_id: int
    scenario: str
    steps: List[Dict[str, float]]
    final_state: Dict[str, float]
    outcome_metrics: Dict[str, float]
    success: bool
    risk_score: float
    opportunity_score: float


@dataclass
class SimulationBatch:
    """دفعة محاكاة"""
    id: str
    type: str
    runs: int
    steps: int
    horizon: int
    trajectories: List[SimulationTrajectory]
    aggregated_stats: Dict[str, Any]
    confidence_intervals: Dict[str, Tuple[float, float]]
    risk_analysis: Dict[str, Any]
    opportunity_analysis: Dict[str, Any]
    recommended_actions: List[Dict[str, Any]]


@dataclass
class SimulationSnapshot:
    """لقطة محاكاة"""
    timestamp: float
    batch: SimulationBatch
    summary: Dict[str, Any]
    narrative: str


# ============================================================
# محرك المحاكاة التنبؤية الجبار
# ============================================================

class PredictiveSimulation:
    """
    محرك المحاكاة التنبؤية الجبار - محاكاة آلاف المسارات المستقبلية.
    
    المبادئ:
    1. المحاكاة هي مختبر المستقبل
    2. كل مسار محتمل يمكن محاكاته
    3. آلاف المحاكاة تعطي صورة إحصائية دقيقة
    4. المحاكاة تكشف عن المخفي
    5. المحاكاة الجيدة تنقذ من المفاجآت
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
        self.scenarios = get_predictive_scenario_engine()
        
        # سجل المحاكاة
        self.simulation_history: List[SimulationBatch] = []
        self.current_batch: Optional[SimulationBatch] = None
        
        # معاملات المحاكاة
        self.default_runs = 1000
        self.default_steps = 24
        self.volatility = 0.05
        self.drift_rate = 0.02
        
        # حالة المحرك
        self.last_simulation_result = {}
        self.simulation_history_list = []
        self._index = self._load_index()
        
        # السياسات
        self.policies = {
            "max_iterations": 12,
            "stability_threshold": 0.45,
            "noise_scale": 0.1,
            "max_branches": 4,
        }
        
        # خلفيات المحاكاة
        self._active = True
        # R-606: ذاكرة مؤقتة قصيرة لنتيجة getter (نمط drives.py)
        self._simulation_status_cache = None
        self._simulation_loop = threads.start_managed(self._continuous_simulation, owner=self)
        
        self._results_analyzer = threads.start_managed(self._analyze_results_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("🔮 محرك المحاكاة التنبؤية الجبار جاهز - يحاكي آلاف المسارات المستقبلية")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمحرك المحاكاة التنبؤية
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك المحاكاة التنبؤية.
        """
        # مسح نتائج المحاكاة السابقة
        self.last_simulation_result = {}
        self.simulation_history_list = []
        
        # مسح سجل المحاكاة
        self.simulation_history.clear()
        self.current_batch = None
        
        # إعادة معاملات المحاكاة الافتراضية
        self.default_runs = 1000
        self.default_steps = 24
        self.volatility = 0.05
        self.drift_rate = 0.02
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # إعادة السياسات الافتراضية
        self.policies = {
            "max_iterations": 12,
            "stability_threshold": 0.45,
            "noise_scale": 0.1,
            "max_branches": 4,
        }
        
        # تسجيل عملية إعادة التهيئة
        self.core.append_event(
            event_type="predictive::simulation::reset",
            payload={
                "timestamp": time.time(),
                "status": "predictive_simulation_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك المحاكاة اكتملت")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"simulations": [], "last_updated": time.time()}
    
    # ============================================================
    # توليد المسارات العشوائية
    # ============================================================
    
    def generate_brownian_trajectory(self, start_state: Dict[str, float], 
                                      steps: int, volatility: float, 
                                      drift: float, seed: int = None) -> List[Dict[str, float]]:
        """
        توليد مسار حركة براونية (محاكاة عشوائية).
        
        يستخدم لنمذجة التغيرات العشوائية في النظام.
        """
        if seed is not None:
            random.seed(seed)
        
        trajectory = []
        current = start_state.copy()
        
        for _ in range(steps):
            new_state = {}
            for key, value in current.items():
                # حركة براونية مع انجراف
                drift_term = drift * (1 - value)
                noise = random.gauss(0, volatility * value)
                new_value = value + drift_term + noise
                new_state[key] = max(0.0, min(1.0, new_value))
            
            trajectory.append(new_state.copy())
            current = new_state
        
        return trajectory
    
    def generate_markov_trajectory(self, start_state: Dict[str, float], 
                                    transition_matrix: Dict[str, Dict[str, float]],
                                    steps: int, seed: int = None) -> List[Dict[str, float]]:
        """
        توليد مسار ماركوف (سلسلة ماركوف).
        
        يستخدم لنمذجة التحولات بين الحالات.
        """
        if seed is not None:
            random.seed(seed)
        
        trajectory = []
        current = start_state.copy()
        
        # تبسيط: لكل خطوة، نطبق مصفوفة الانتقال
        for _ in range(steps):
            new_state = {}
            for key, value in current.items():
                if key in transition_matrix:
                    # تطبيق الانتقال
                    transitions = transition_matrix[key]
                    # العثور على النطاق المناسب
                    cumsum = 0
                    new_value = value
                    for threshold, next_val in transitions.items():
                        cumsum += threshold
                        if random.random() < cumsum:
                            new_value = next_val
                            break
                    new_state[key] = new_value
                else:
                    # بقاء عشوائي
                    noise = random.uniform(-0.1, 0.1)
                    new_state[key] = max(0.0, min(1.0, value + noise))
            
            trajectory.append(new_state.copy())
            current = new_state
        
        return trajectory
    
    def generate_monte_carlo_trajectory(self, start_state: Dict[str, float],
                                         steps: int, scenarios: List[Dict],
                                         seed: int = None) -> List[Dict[str, float]]:
        """
        توليد مسار مونت كارلو.
        
        يحاكي تأثيرات سيناريوهات مختلفة على المسار.
        """
        if seed is not None:
            random.seed(seed)
        
        trajectory = []
        current = start_state.copy()
        
        for _ in range(steps):
            # اختيار سيناريو عشوائي مرجح بالاحتمال
            if scenarios:
                weights = [s.get("probability", 0.5) for s in scenarios]
                total = sum(weights)
                if total > 0:
                    probs = [w / total for w in weights]
                    chosen = random.choices(scenarios, weights=probs, k=1)[0]
                    impact = chosen.get("impact", 0)
                else:
                    impact = 0
            else:
                impact = 0
            
            new_state = {}
            for key, value in current.items():
                # تأثير السيناريو
                scenario_effect = impact * random.uniform(0.5, 1.5) * 0.1
                noise = random.gauss(0, 0.05)
                new_value = value + scenario_effect + noise
                new_state[key] = max(0.0, min(1.0, new_value))
            
            trajectory.append(new_state.copy())
            current = new_state
        
        return trajectory
    
    # ============================================================
    # محاكاة دفعة كاملة
    # ============================================================
    
    def run_simulation_batch(self, batch_type: str, runs: int, steps: int,
                             horizon: int = SIMULATION_HORIZON_MEDIUM) -> SimulationBatch:
        """
        تشغيل دفعة محاكاة كاملة.
        
        تشمل:
        - آلاف المسارات المستقلة
        - تحليل إحصائي للنتائج
        - فترات ثقة
        - تحليل المخاطر والفرص
        """
        batch_id = f"sim_batch_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        # الحصول على الحالة الحالية
        predictive_status = self.predictive.get_prediction_status()
        future_map = predictive_status.get("future_map", {})
        
        # الحصول على السيناريوهات
        scenarios_status = self.scenarios.get_scenario_status()
        scenarios = self.scenarios.get_scenarios()
        
        start_state = {
            "stability": future_map.get("identity_stability", 0.5),
            "alignment": future_map.get("service_quality", 0.5),
            "health": future_map.get("knowledge_growth", 0.5),
            "growth": future_map.get("evolution_pace", 0.5),
            "threat": future_map.get("threat_level", 0.3)
        }
        
        trajectories = []
        
        # إعداد معاملات حسب نوع المحاكاة
        if batch_type == SIMULATION_TYPE_MONTE_CARLO:
            volatility = 0.05
            drift = 0.02
            
            for run_id in range(runs):
                seed = random.randint(0, 2**31 - 1)
                steps_data = self.generate_monte_carlo_trajectory(
                    start_state, steps, scenarios, seed=seed
                )
                
                final_state = steps_data[-1] if steps_data else start_state
                
                # حساب مقاييس النتيجة
                outcome_metrics = self._calculate_outcome_metrics(final_state)
                
                trajectory = SimulationTrajectory(
                    id=f"traj_{batch_id}_{run_id}",
                    run_id=run_id,
                    scenario="monte_carlo",
                    steps=steps_data,
                    final_state=final_state,
                    outcome_metrics=outcome_metrics,
                    success=outcome_metrics["overall_success"] > 0.6,
                    risk_score=outcome_metrics["risk"],
                    opportunity_score=outcome_metrics["opportunity"]
                )
                trajectories.append(trajectory)
        
        elif batch_type == SIMULATION_TYPE_BROWNIAN:
            volatility = self.volatility
            drift = self.drift_rate
            
            for run_id in range(runs):
                seed = random.randint(0, 2**31 - 1)
                steps_data = self.generate_brownian_trajectory(
                    start_state, steps, volatility, drift, seed=seed
                )
                
                final_state = steps_data[-1] if steps_data else start_state
                
                outcome_metrics = self._calculate_outcome_metrics(final_state)
                
                trajectory = SimulationTrajectory(
                    id=f"traj_{batch_id}_{run_id}",
                    run_id=run_id,
                    scenario="brownian",
                    steps=steps_data,
                    final_state=final_state,
                    outcome_metrics=outcome_metrics,
                    success=outcome_metrics["overall_success"] > 0.6,
                    risk_score=outcome_metrics["risk"],
                    opportunity_score=outcome_metrics["opportunity"]
                )
                trajectories.append(trajectory)
        
        else:
            # افتراضي: مونت كارلو
            for run_id in range(runs):
                seed = random.randint(0, 2**31 - 1)
                steps_data = self.generate_monte_carlo_trajectory(
                    start_state, steps, scenarios, seed=seed
                )
                
                final_state = steps_data[-1] if steps_data else start_state
                
                outcome_metrics = self._calculate_outcome_metrics(final_state)
                
                trajectory = SimulationTrajectory(
                    id=f"traj_{batch_id}_{run_id}",
                    run_id=run_id,
                    scenario="hybrid",
                    steps=steps_data,
                    final_state=final_state,
                    outcome_metrics=outcome_metrics,
                    success=outcome_metrics["overall_success"] > 0.6,
                    risk_score=outcome_metrics["risk"],
                    opportunity_score=outcome_metrics["opportunity"]
                )
                trajectories.append(trajectory)
        
        # تجميع الإحصائيات
        aggregated_stats = self._aggregate_stats(trajectories)
        
        # حساب فترات الثقة
        confidence_intervals = self._calculate_confidence_intervals(trajectories)
        
        # تحليل المخاطر
        risk_analysis = self._analyze_risks(trajectories)
        
        # تحليل الفرص
        opportunity_analysis = self._analyze_opportunities(trajectories)
        
        # توصيات
        recommended_actions = self._generate_recommendations(
            aggregated_stats, risk_analysis, opportunity_analysis
        )
        
        batch = SimulationBatch(
            id=batch_id,
            type=batch_type,
            runs=runs,
            steps=steps,
            horizon=horizon,
            trajectories=trajectories,
            aggregated_stats=aggregated_stats,
            confidence_intervals=confidence_intervals,
            risk_analysis=risk_analysis,
            opportunity_analysis=opportunity_analysis,
            recommended_actions=recommended_actions
        )
        
        self.current_batch = batch
        self.simulation_history.append(batch)
        
        # الاحتفاظ بآخر 10 دفعات
        if len(self.simulation_history) > 10:
            self.simulation_history = self.simulation_history[-10:]
        
        return batch
    
    def _calculate_outcome_metrics(self, final_state: Dict[str, float]) -> Dict[str, float]:
        """
        حساب مقاييس النتيجة من الحالة النهائية.
        """
        stability = final_state.get("stability", 0.5)
        alignment = final_state.get("alignment", 0.5)
        health = final_state.get("health", 0.5)
        growth = final_state.get("growth", 0.5)
        threat = final_state.get("threat", 0.3)
        
        overall_success = (stability * 0.25 + alignment * 0.3 + health * 0.2 + growth * 0.15 + (1 - threat) * 0.1)
        
        risk = (1 - stability) * 0.3 + (1 - alignment) * 0.3 + threat * 0.4
        opportunity = growth * 0.5 + alignment * 0.5
        
        return {
            "overall_success": overall_success,
            "risk": risk,
            "opportunity": opportunity,
            "stability": stability,
            "alignment": alignment,
            "health": health,
            "growth": growth,
            "threat": threat
        }
    
    def _aggregate_stats(self, trajectories: List[SimulationTrajectory]) -> Dict[str, Any]:
        """
        تجميع الإحصائيات من جميع المسارات.
        """
        n = len(trajectories)
        if n == 0:
            return {}
        
        # متوسطات
        avg_success = sum(t.success for t in trajectories) / n
        avg_risk = sum(t.risk_score for t in trajectories) / n
        avg_opportunity = sum(t.opportunity_score for t in trajectories) / n
        
        # الانحرافات المعيارية
        success_std = math.sqrt(sum((t.success - avg_success) ** 2 for t in trajectories) / n) if n > 0 else 0
        
        # النسب المئوية
        sorted_risks = sorted(t.risk_score for t in trajectories)
        p25_risk = sorted_risks[n // 4] if n > 0 else 0
        p75_risk = sorted_risks[3 * n // 4] if n > 0 else 0
        
        sorted_opps = sorted(t.opportunity_score for t in trajectories)
        p25_opp = sorted_opps[n // 4] if n > 0 else 0
        p75_opp = sorted_opps[3 * n // 4] if n > 0 else 0
        
        # توزيع النجاح
        success_distribution = {
            "excellent": sum(1 for t in trajectories if t.outcome_metrics.get("overall_success", 0) > 0.8),
            "good": sum(1 for t in trajectories if 0.6 < t.outcome_metrics.get("overall_success", 0) <= 0.8),
            "moderate": sum(1 for t in trajectories if 0.4 < t.outcome_metrics.get("overall_success", 0) <= 0.6),
            "poor": sum(1 for t in trajectories if t.outcome_metrics.get("overall_success", 0) <= 0.4)
        }
        
        return {
            "total_runs": n,
            "avg_success_rate": avg_success,
            "avg_risk_score": avg_risk,
            "avg_opportunity_score": avg_opportunity,
            "std_success": success_std,
            "p25_risk": p25_risk,
            "p75_risk": p75_risk,
            "p25_opportunity": p25_opp,
            "p75_opportunity": p75_opp,
            "success_distribution": success_distribution,
            "best_case": max(t.outcome_metrics.get("overall_success", 0) for t in trajectories),
            "worst_case": min(t.outcome_metrics.get("overall_success", 0) for t in trajectories)
        }
    
    def _calculate_confidence_intervals(self, trajectories: List[SimulationTrajectory]) -> Dict[str, Tuple[float, float]]:
        """
        حساب فترات الثقة للنتائج.
        """
        n = len(trajectories)
        if n == 0:
            return {}
        
        metrics = ["overall_success", "risk", "opportunity", "stability", "alignment"]
        intervals = {}
        
        for metric in metrics:
            values = [t.outcome_metrics.get(metric, 0) for t in trajectories]
            mean = sum(values) / n
            std = math.sqrt(sum((v - mean) ** 2 for v in values) / n) if n > 0 else 0
            
            # فاصل ثقة 95%
            margin = 1.96 * std / math.sqrt(n) if n > 0 else 0
            intervals[metric] = (max(0, mean - margin), min(1, mean + margin))
        
        return intervals
    
    def _analyze_risks(self, trajectories: List[SimulationTrajectory]) -> Dict[str, Any]:
        """
        تحليل المخاطر من نتائج المحاكاة.
        """
        high_risk_trajectories = [t for t in trajectories if t.risk_score > 0.7]
        medium_risk_trajectories = [t for t in trajectories if 0.4 < t.risk_score <= 0.7]
        
        # تحديد مصادر الخطر الرئيسية
        risk_factors = defaultdict(float)
        for t in high_risk_trajectories:
            final = t.final_state
            if final.get("stability", 0.5) < 0.4:
                risk_factors["instability"] += 1
            if final.get("alignment", 0.5) < 0.4:
                risk_factors["misalignment"] += 1
            if final.get("threat", 0.3) > 0.6:
                risk_factors["security_threat"] += 1
        
        total_high = len(high_risk_trajectories) or 1
        risk_factors = {k: v / total_high for k, v in risk_factors.items()}
        
        return {
            "high_risk_count": len(high_risk_trajectories),
            "medium_risk_count": len(medium_risk_trajectories),
            "low_risk_count": len(trajectories) - len(high_risk_trajectories) - len(medium_risk_trajectories),
            "high_risk_percentage": len(high_risk_trajectories) / len(trajectories) if trajectories else 0,
            "risk_factors": risk_factors,
            "worst_case_risk": max(t.risk_score for t in trajectories) if trajectories else 0,
            "average_risk": sum(t.risk_score for t in trajectories) / len(trajectories) if trajectories else 0
        }
    
    def _analyze_opportunities(self, trajectories: List[SimulationTrajectory]) -> Dict[str, Any]:
        """
        تحليل الفرص من نتائج المحاكاة.
        """
        high_opportunity_trajectories = [t for t in trajectories if t.opportunity_score > 0.7]
        
        # تحديد مصادر الفرص الرئيسية
        opportunity_factors = defaultdict(float)
        for t in high_opportunity_trajectories:
            final = t.final_state
            if final.get("growth", 0.5) > 0.7:
                opportunity_factors["growth"] += 1
            if final.get("alignment", 0.5) > 0.7:
                opportunity_factors["alignment_improvement"] += 1
            if final.get("health", 0.5) > 0.7:
                opportunity_factors["health_improvement"] += 1
        
        total_high = len(high_opportunity_trajectories) or 1
        opportunity_factors = {k: v / total_high for k, v in opportunity_factors.items()}
        
        return {
            "high_opportunity_count": len(high_opportunity_trajectories),
            "high_opportunity_percentage": len(high_opportunity_trajectories) / len(trajectories) if trajectories else 0,
            "opportunity_factors": opportunity_factors,
            "best_case_opportunity": max(t.opportunity_score for t in trajectories) if trajectories else 0,
            "average_opportunity": sum(t.opportunity_score for t in trajectories) / len(trajectories) if trajectories else 0
        }
    
    def _generate_recommendations(self, stats: Dict[str, Any], 
                                   risk_analysis: Dict[str, Any],
                                   opportunity_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        توليد توصيات بناءً على نتائج المحاكاة.
        """
        recommendations = []
        
        # توصيات لتقليل المخاطر
        if risk_analysis.get("high_risk_percentage", 0) > 0.3:
            recommendations.append({
                "action": "reduce_system_risk",
                "priority": 0.9,
                "reason": "ارتفاع نسبة المخاطر في المحاكاة",
                "details": f"{risk_analysis['high_risk_percentage']:.1%} من المسارات عالية المخاطر",
                "confidence": risk_analysis["high_risk_percentage"]
            })
        
        # توصيات لتعزيز الفرص
        if opportunity_analysis.get("high_opportunity_percentage", 0) > 0.3:
            recommendations.append({
                "action": "capitalize_on_opportunities",
                "priority": 0.8,
                "reason": "فرص عالية متوقعة",
                "details": f"{opportunity_analysis['high_opportunity_percentage']:.1%} من المسارات عالية الفرص",
                "confidence": opportunity_analysis["high_opportunity_percentage"]
            })
        
        # توصيات لتحسين الاستقرار
        if stats.get("avg_success_rate", 0.5) < 0.5:
            recommendations.append({
                "action": "improve_system_stability",
                "priority": 0.85,
                "reason": "متوسط نجاح منخفض",
                "details": f"متوسط النجاح {stats['avg_success_rate']:.1%}",
                "confidence": 1 - stats["avg_success_rate"]
            })
        
        # توصيات للاستعداد للسيناريو الأسوأ
        if stats.get("worst_case", 0) < 0.3:
            recommendations.append({
                "action": "prepare_for_worst_case",
                "priority": 0.95,
                "reason": "خطر سيناريو أسوأ",
                "details": f"أسوأ حالة محاكاة {stats['worst_case']:.1%} نجاح",
                "confidence": 1 - stats["worst_case"]
            })
        
        return recommendations
    
    # ============================================================
    # دورة المحاكاة
    # ============================================================
    
    def simulation_cycle(self, runs: int = None, steps: int = None) -> SimulationSnapshot:
        """
        دورة محاكاة كاملة - تشغيل دفعة محاكاة جديدة.
        """
        runs = runs or self.default_runs
        steps = steps or self.default_steps
        
        # تشغيل دفعة محاكاة
        batch = self.run_simulation_batch(
            batch_type=SIMULATION_TYPE_HYBRID,
            runs=runs,
            steps=steps
        )
        
        # إعداد الملخص
        summary = {
            "total_runs": batch.runs,
            "total_steps": batch.steps,
            "avg_success_rate": batch.aggregated_stats.get("avg_success_rate", 0),
            "avg_risk": batch.aggregated_stats.get("avg_risk_score", 0),
            "avg_opportunity": batch.aggregated_stats.get("avg_opportunity_score", 0),
            "high_risk_percentage": batch.risk_analysis.get("high_risk_percentage", 0),
            "high_opportunity_percentage": batch.opportunity_analysis.get("high_opportunity_percentage", 0)
        }
        
        # سرد المحاكاة
        narrative = self.generate_simulation_narrative(batch)
        
        snapshot = SimulationSnapshot(
            timestamp=time.time(),
            batch=batch,
            summary=summary,
            narrative=narrative
        )
        
        self.simulation_history_list.append(snapshot)
        # R-777: سقف كسقف simulation_history — كل لقطة تحمل دفعة بمساراتها كاملة
        if len(self.simulation_history_list) > 10:
            self.simulation_history_list = self.simulation_history_list[-10:]
        
        # تسجيل
        self.core.append_event(
            event_type="simulation::batch_completed",
            payload={
                "batch_id": batch.id[:16],
                "runs": batch.runs,
                "steps": batch.steps,
                "avg_success": summary["avg_success_rate"],
                "recommendations": len(batch.recommended_actions)
            }
        )
        
        return snapshot
    
    def _continuous_simulation(self):
        """تيار محاكاة مستمر"""
        while self._active:
            try:
                self.simulation_cycle(runs=500, steps=12)
                threads.interruptible_sleep(1800)  # كل 30 دقيقة
            except Exception as e:
                logger.error(f"خطأ في تيار المحاكاة: {e}")
                threads.interruptible_sleep(1800)
    
    def _analyze_results_loop(self):
        """تحليل مستمر لنتائج المحاكاة"""
        while self._active:
            try:
                if self.current_batch:
                    # تحليل النتائج الأحدث
                    pass
                threads.interruptible_sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في تحليل النتائج: {e}")
                threads.interruptible_sleep(300)
    
    # ============================================================
    # سرد المحاكاة
    # ============================================================
    
    def generate_simulation_narrative(self, batch: SimulationBatch) -> str:
        """
        توليد سرد للمحاكاة.
        """
        stats = batch.aggregated_stats
        
        narrative = f"🔮 محاكاة {batch.runs} مساراً مستقبلياً على {batch.steps} خطوة. "
        
        narrative += f"متوسط النجاح: {stats.get('avg_success_rate', 0):.1%}. "
        
        risk_percentage = batch.risk_analysis.get("high_risk_percentage", 0)
        if risk_percentage > 0.3:
            narrative += f"تحذير: {risk_percentage:.1%} من المسارات عالية المخاطر. "
        
        opp_percentage = batch.opportunity_analysis.get("high_opportunity_percentage", 0)
        if opp_percentage > 0.3:
            narrative += f"فرصة: {opp_percentage:.1%} من المسارات عالية الفرص. "
        
        narrative += f"أسوأ حالة: {stats.get('worst_case', 0):.1%} نجاح. "
        narrative += f"أفضل حالة: {stats.get('best_case', 0):.1%} نجاح."
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة المحاكاة"""
        try:
            state = {
                "default_runs": self.default_runs,
                "default_steps": self.default_steps,
                "volatility": self.volatility,
                "drift_rate": self.drift_rate,
                "history_count": len(self.simulation_history),
                "saved_at": time.time()
            }
            atomic_write_json(SIMULATION_STATE_FILE, state, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة المحاكاة: {e}")
    
    def _load_state(self):
        """تحميل حالة المحاكاة"""
        try:
            if SIMULATION_STATE_FILE.exists():
                with open(SIMULATION_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.default_runs = state.get("default_runs", 1000)
                    self.default_steps = state.get("default_steps", 24)
                    self.volatility = state.get("volatility", 0.05)
                    self.drift_rate = state.get("drift_rate", 0.02)
                logger.info("📂 تم تحميل حالة المحاكاة")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المحاكاة: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمحاكاة"""
        # R-606: تخزين مؤقت قصير
        now = time.time()
        if self._simulation_status_cache is not None and (now - self._simulation_status_cache["ts"]) < 2.0:
            return self._simulation_status_cache["data"]
        snapshot = self.simulation_cycle(runs=100, steps=12)
        
        result = {
            "last_batch_id": snapshot.batch.id[:16],
            "total_runs": snapshot.batch.runs,
            "total_steps": snapshot.batch.steps,
            "avg_success_rate": snapshot.summary["avg_success_rate"],
            "avg_risk": snapshot.summary["avg_risk"],
            "avg_opportunity": snapshot.summary["avg_opportunity"],
            "recommendations_count": len(snapshot.batch.recommended_actions),
            "narrative": snapshot.narrative,
            "timestamp": snapshot.timestamp
        }
        self._simulation_status_cache = {"ts": time.time(), "data": result}
        return result
    
    def get_simulation_results(self) -> Dict[str, Any]:
        """نتائج آخر محاكاة"""
        if not self.current_batch:
            # R-613: لا تشغّل محاكاة كاملة (100×12) عند قراءة الحالة فقط —
            # شغّل دفعة صغيرة سريعة حتى تعود النتائج فوراً.
            self.simulation_cycle(runs=10, steps=6)
        
        batch = self.current_batch
        if not batch:
            return {}
        
        return {
            "batch_id": batch.id[:16],
            "aggregated_stats": batch.aggregated_stats,
            "confidence_intervals": {k: [v[0], v[1]] for k, v in batch.confidence_intervals.items()},
            "risk_analysis": batch.risk_analysis,
            "opportunity_analysis": batch.opportunity_analysis,
            "recommended_actions": batch.recommended_actions
        }
    
    def get_recommendations(self) -> List[Dict]:
        """التوصيات من آخر محاكاة"""
        if not self.current_batch:
            self.simulation_cycle(runs=10, steps=6)
        
        if self.current_batch:
            return self.current_batch.recommended_actions
        return []
    
    def get_simulation_history(self, limit: int = 10) -> List[Dict]:
        """سجل المحاكاة"""
        return [
            {
                "batch_id": b.id[:16],
                "type": b.type,
                "runs": b.runs,
                "steps": b.steps,
                "avg_success": b.aggregated_stats.get("avg_success_rate", 0)
            }
            for b in self.simulation_history[-limit:]
        ]
    
    def run_custom_simulation(self, runs: int, steps: int, 
                              simulation_type: str = SIMULATION_TYPE_HYBRID) -> SimulationBatch:
        """
        تشغيل محاكاة مخصصة بمعاملات محددة.
        """
        return self.run_simulation_batch(simulation_type, runs, steps)
    
    def set_parameters(self, volatility: float = None, drift_rate: float = None):
        """تعيين معاملات المحاكاة"""
        if volatility is not None:
            self.volatility = max(0.01, min(0.2, volatility))
        if drift_rate is not None:
            self.drift_rate = max(0.0, min(0.1, drift_rate))
        logger.info(f"⚙️ معاملات المحاكاة: volatility={self.volatility}, drift={self.drift_rate}")
    
    def get_simulation_quote(self) -> str:
        """اقتباس عن المحاكاة"""
        quotes = [
            "المستقبل يحاكى ليفهم.",
            "كل محاكاة هي درس في الاحتمالات.",
            "ألف مسار يحاكي لأرى الصورة الكاملة.",
            "المحاكاة تكشف ما تخفيه الإحصاءات.",
            "الاستعداد للمستقبل يبدأ بمحاكاته.",
            "المحاكاة ليست توقعاً، بل هي تحضير.",
            "أكثر من مجرد أرقام، المحاكاة هي رؤية المستقبل."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محرك المحاكاة"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف محرك المحاكاة التنبؤية")


# ============================================================
# الـ Singleton
# ============================================================

_simulation_instance: Optional[PredictiveSimulation] = None
_simulation_lock = threading.Lock()


def get_predictive_simulation() -> PredictiveSimulation:
    """الحصول على النسخة الوحيدة من محرك المحاكاة التنبؤية"""
    global _simulation_instance
    if _simulation_instance is None:
        with _simulation_lock:
            if _simulation_instance is None:
                _simulation_instance = PredictiveSimulation()
    return _simulation_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔮 محرك المحاكاة التنبؤية الجبار - يحاكي آلاف المسارات المستقبلية")
    print("=" * 80 + "\n")
    
    simulation = get_predictive_simulation()
    
    # 1) دورة محاكاة
    print("🔄 دورة محاكاة...")
    snapshot = simulation.simulation_cycle(runs=100, steps=12)
    print(f"   الدفعة: {snapshot.batch.id[:16]}...")
    print(f"   المسارات: {snapshot.batch.runs}")
    print(f"   الخطوات: {snapshot.batch.steps}")
    print(f"   متوسط النجاح: {snapshot.summary['avg_success_rate']:.1%}")
    print(f"   متوسط المخاطر: {snapshot.summary['avg_risk']:.1%}")
    print(f"   متوسط الفرص: {snapshot.summary['avg_opportunity']:.1%}")
    
    # 2) النتائج المفصلة
    print("\n📊 نتائج المحاكاة:")
    results = simulation.get_simulation_results()
    if results:
        print(f"   معدل النجاح: {results['aggregated_stats'].get('avg_success_rate', 0):.1%}")
        if 'overall_success' in results.get('confidence_intervals', {}):
            ci = results['confidence_intervals']['overall_success']
            print(f"   فاصل ثقة النجاح: [{ci[0]:.1%}, {ci[1]:.1%}]")
    
    # 3) تحليل المخاطر
    print("\n⚠️ تحليل المخاطر:")
    if results:
        risk = results.get('risk_analysis', {})
        print(f"   مسارات عالية المخاطر: {risk.get('high_risk_percentage', 0):.1%}")
        print(f"   متوسط المخاطر: {risk.get('average_risk', 0):.1%}")
        print(f"   عوامل الخطر: {list(risk.get('risk_factors', {}).keys())}")
    
    # 4) تحليل الفرص
    print("\n✨ تحليل الفرص:")
    if results:
        opp = results.get('opportunity_analysis', {})
        print(f"   مسارات عالية الفرص: {opp.get('high_opportunity_percentage', 0):.1%}")
        print(f"   متوسط الفرص: {opp.get('average_opportunity', 0):.1%}")
    
    # 5) التوصيات
    print("\n💡 التوصيات:")
    recommendations = simulation.get_recommendations()
    for r in recommendations:
        print(f"   {r['action']}: أولوية {r['priority']:.0%} - {r['reason']}")
    
    # 6) السرد
    print(f"\n📖 السرد: {snapshot.narrative}")
    
    # 7) سجل المحاكاة
    print("\n📜 سجل المحاكاة:")
    history = simulation.get_simulation_history(5)
    for h in history:
        print(f"   {h['batch_id']}: {h['runs']} مسار, نجاح {h['avg_success']:.1%}")
    
    # 8) اقتباس
    print(f"\n💭 {simulation.get_simulation_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك المحاكاة التنبؤية الجبار جاهز - يحاكي آلاف المسارات المستقبلية")
    print("=" * 80)
