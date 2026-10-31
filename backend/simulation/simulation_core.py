# backend/simulation/simulation_core.py
# 🔁 نواة المحاكاة الداخلية الجبارة - تنسيق وتشغيل محاكاة متعددة المستويات
# الإصدار: 3.0.0 - تدير آلاف التشغيلات، تحلل كل نتيجة

"""
نواة المحاكاة الداخلية للنظام السيادي.

الفلسفة:
- المحاكاة هي مختبر النظام السري
- تشغيلات متعددة تكشف الأنماط الخفية
- التجميع الذكي للنتائج يعطي صورة كاملة
- التقارير الواضحة توجه القرارات
- التكامل مع كل طبقات النظام يعطي دقة عالية

هذه ليست مجرد محاكاة. هذه هي معمليات المستقبل الداخلية.
"""

import json
from runtime.atomic_json import atomic_write_json  # R-781
import time
import threading
import runtime.threads as threads
import random
import secrets
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from ..memory.core import get_core, EventType
    from ..memory.biological.instincts import get_instincts
    from ..memory.biological.drives import get_drives
    from ..memory.biological.archetypes import get_archetypes
    from ..consciousness.identity_core import get_identity_core
    from ..consciousness.self_model import get_self_model
    from ..consciousness.introspection import get_introspection_engine
    from ..consciousness.awareness import get_awareness_engine
    from ..consciousness.attention_engine import get_attention_engine
    from ..sovereign.will import get_sovereign_will
    from ..sovereign.alignment import get_sovereign_alignment
    from ..sovereign.directives import get_sovereign_directives
    from ..sovereign.controller import get_sovereign_controller
    from ..predictive.predictive_engine import get_predictive_engine
    from ..predictive.predictive_scenarios import get_predictive_scenario_engine
    from ..predictive.predictive_simulation import get_predictive_simulation
    from ..predictive.predictive_risk_manager import get_predictive_risk_manager
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from memory.biological.archetypes import get_archetypes
    from consciousness.identity_core import get_identity_core
    from consciousness.self_model import get_self_model
    from consciousness.introspection import get_introspection_engine
    from consciousness.awareness import get_awareness_engine
    from consciousness.attention_engine import get_attention_engine
    from sovereign.will import get_sovereign_will
    from sovereign.alignment import get_sovereign_alignment
    from sovereign.directives import get_sovereign_directives
    from sovereign.controller import get_sovereign_controller
    from predictive.predictive_engine import get_predictive_engine
    from predictive.predictive_scenarios import get_predictive_scenario_engine
    from predictive.predictive_simulation import get_predictive_simulation
    from predictive.predictive_risk_manager import get_predictive_risk_manager
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات نواة المحاكاة
# ============================================================

SIMCORE_DIR = DATA_DIR / "simulation" / "core"
SIMCORE_DIR.mkdir(parents=True, exist_ok=True)
SIMCORE_LOG = SIMCORE_DIR / "simulation_core_log.jsonl"
SIMCORE_STATE_FILE = SIMCORE_DIR / "simulation_core_state.json"
SIMCORE_RESULTS_DIR = SIMCORE_DIR / "results"

SIMCORE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# مستويات المحاكاة
SIMULATION_LEVEL_MICRO = 0          # ميكرو (تفصيلي، عدد قليل من الخطوات)
SIMULATION_LEVEL_MESO = 1           # ميسو (متوسط، عدد متوسط من الخطوات)
SIMULATION_LEVEL_MACRO = 2          # ماكرو (إجمالي، عدد كبير من الخطوات)
SIMULATION_LEVEL_META = 3           # ميتا (تحليلي، محاكاة للمحاكاة)

# حالات التشغيل
RUN_STATUS_PENDING = "pending"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELLED = "cancelled"


def _now_iso() -> str:
    """إرجاع الوقت الحالي بصيغة ISO"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat() + "Z"


@dataclass
class SimulationRun:
    """تشغيل محاكاة فردي"""
    id: str
    name: str
    level: int
    scenario: str
    parameters: Dict[str, Any]
    status: str
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    results: Optional[Dict[str, Any]]
    metrics: Dict[str, float]
    logs: List[str]


@dataclass
class SimulationBatch:
    """دفعة محاكاة"""
    id: str
    name: str
    runs: List[SimulationRun]
    created_at: float
    completed_at: Optional[float]
    aggregated_metrics: Dict[str, Any]
    summary: Dict[str, Any]


@dataclass
class SimulationReport:
    """تقرير محاكاة"""
    timestamp: float
    batch_id: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    aggregated_metrics: Dict[str, Any]
    insights: List[str]
    recommendations: List[Dict[str, Any]]
    narrative: str


# ============================================================
# نواة المحاكاة الداخلية الجبارة
# ============================================================

class SimulationCore:
    """
    نواة المحاكاة الداخلية الجبارة - تنسيق وتشغيل محاكاة متعددة المستويات.
    
    المبادئ:
    1. المحاكاة هي مختبر النظام السري
    2. تشغيلات متعددة تكشف الأنماط الخفية
    3. التجميع الذكي يعطي صورة كاملة
    4. التقارير الواضحة توجه القرارات
    5. التكامل مع كل طبقات النظام يعطي دقة عالية
    """
    
    def __init__(self):
        self.core = get_core()
        self.instincts = get_instincts()
        self.drives = get_drives()
        self.archetypes = get_archetypes()
        self.identity = get_identity_core()
        self.self_model = get_self_model()
        self.introspection = get_introspection_engine()
        self.awareness = get_awareness_engine()
        self.attention = get_attention_engine()
        self.will = get_sovereign_will()
        self.alignment = get_sovereign_alignment()
        self.directives = get_sovereign_directives()
        self.controller = get_sovereign_controller()
        self.predictive = get_predictive_engine()
        self.scenarios = get_predictive_scenario_engine()
        self.simulation = get_predictive_simulation()
        self.risk_manager = get_predictive_risk_manager()
        
        # سجل التشغيلات
        self.runs: Dict[str, SimulationRun] = {}
        self.batches: Dict[str, SimulationBatch] = {}
        self.reports: List[SimulationReport] = []
        
        # حالة المحرك
        self.last_environment_state = {}
        self.last_simulation_output = {}
        self.cycle_history = []
        self._index = self._load_index()
        
        # السياسات
        self.policies = {
            "max_cycles": 20,
            "stability_threshold": 0.5,
            "noise_scale": 0.1,
            "environment_sync": True,
        }
        
        # إعدادات التشغيل المتوازي
        self.max_workers = 4
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # خلفيات المحاكاة
        self._active = True
        self._batch_processor = threads.start_managed(self._process_batches_loop, owner=self)
        
        self._result_analyzer = threads.start_managed(self._analyze_results_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("🔁 نواة المحاكاة الداخلية الجبارة جاهزة - تدير آلاف التشغيلات")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لنواة المحاكاة
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لنواة المحاكاة.
        """
        # مسح الحالة الداخلية
        self.last_environment_state = {}
        self.last_simulation_output = {}
        self.cycle_history = []
        
        # مسح التشغيلات والدُفعات
        self.runs.clear()
        self.batches.clear()
        self.reports.clear()
        
        # إعادة تعيين الإعدادات
        self.max_workers = 4
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # إعادة السياسات الافتراضية
        self.policies = {
            "max_cycles": 20,
            "stability_threshold": 0.5,
            "noise_scale": 0.1,
            "environment_sync": True,
        }
        
        # تسجيل عملية إعادة التهيئة
        self.core.append_event(
            event_type="simulation::core::reset",
            payload={
                "timestamp": _now_iso(),
                "status": "simulation_core_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة نواة المحاكاة اكتملت")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"runs": [], "batches": [], "last_updated": time.time()}
    
    # ============================================================
    # إدارة التشغيلات
    # ============================================================
    
    def create_run(self, name: str, scenario: str, level: int = SIMULATION_LEVEL_MESO,
                   parameters: Dict[str, Any] = None) -> str:
        """
        إنشاء تشغيل محاكاة جديد.
        """
        if parameters is None:
            parameters = {}
        
        run_id = f"sim_run_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        run = SimulationRun(
            id=run_id,
            name=name,
            level=level,
            scenario=scenario,
            parameters=parameters,
            status=RUN_STATUS_PENDING,
            created_at=time.time(),
            started_at=None,
            completed_at=None,
            results=None,
            metrics={},
            logs=[]
        )
        
        self.runs[run_id] = run
        
        logger.info(f"📋 تشغيل محاكاة جديد: {name} (سيناريو: {scenario})")
        
        return run_id
    
    def execute_run(self, run_id: str) -> bool:
        """
        تنفيذ تشغيل محاكاة.
        """
        run = self.runs.get(run_id)
        if not run or run.status != RUN_STATUS_PENDING:
            return False
        
        run.status = RUN_STATUS_RUNNING
        run.started_at = time.time()
        
        try:
            # تحديد نوع المحاكاة حسب المستوى
            if run.level == SIMULATION_LEVEL_MICRO:
                results = self._run_micro_simulation(run)
            elif run.level == SIMULATION_LEVEL_MACRO:
                results = self._run_macro_simulation(run)
            elif run.level == SIMULATION_LEVEL_META:
                results = self._run_meta_simulation(run)
            else:
                results = self._run_meso_simulation(run)
            
            run.results = results
            run.status = RUN_STATUS_COMPLETED
            run.completed_at = time.time()
            
            # حساب المقاييس
            run.metrics = self._calculate_run_metrics(run)
            
            # تسجيل
            self.core.append_event(
                event_type="simulation::run_completed",
                payload={
                    "run_id": run_id[:16],
                    "name": run.name,
                    "scenario": run.scenario,
                    "duration": run.completed_at - run.started_at
                }
            )
            
            logger.info(f"✅ اكتمل تشغيل: {run.name} ({run.completed_at - run.started_at:.2f} ثانية)")
            
            return True
            
        except Exception as e:
            run.status = RUN_STATUS_FAILED
            run.completed_at = time.time()
            run.logs.append(f"ERROR: {str(e)}")
            logger.error(f"❌ فشل تشغيل {run.name}: {e}")
            return False
    
    def _run_micro_simulation(self, run: SimulationRun) -> Dict[str, Any]:
        """محاكاة ميكرو (تفصيلية)"""
        steps = run.parameters.get("steps", 12)
        runs_count = run.parameters.get("runs", 100)
        
        # الحصول على السيناريو
        # R-817 إحياء: حالة السيناريوهات تُمرر للجري (عددها المتاح للمحاكاة)
        scenarios_status = self.scenarios.get_scenario_status()
        scenarios = self.scenarios.get_scenarios()
        run.parameters.setdefault("scenarios_available", len(scenarios))
        run.parameters.setdefault("scenarios_last_updated", scenarios_status.get("last_updated", 0))
        
        target_scenario = None
        for s in scenarios:
            if s.get("name") == run.scenario:
                target_scenario = s
                break
        
        if not target_scenario:
            target_scenario = {"name": run.scenario, "impact": 0}
        
        # تشغيل المحاكاة
        sim_batch = self.simulation.run_custom_simulation(runs_count, steps)
        
        return {
            "type": "micro",
            "steps": steps,
            "runs": runs_count,
            "aggregated": sim_batch.aggregated_stats if hasattr(sim_batch, 'aggregated_stats') else {},
            "risk_analysis": sim_batch.risk_analysis if hasattr(sim_batch, 'risk_analysis') else {},
            "opportunity_analysis": sim_batch.opportunity_analysis if hasattr(sim_batch, 'opportunity_analysis') else {}
        }
    
    def _run_meso_simulation(self, run: SimulationRun) -> Dict[str, Any]:
        """محاكاة ميسو (متوسطة)"""
        steps = run.parameters.get("steps", 24)
        runs_count = run.parameters.get("runs", 500)
        
        # تشغيل المحاكاة
        sim_batch = self.simulation.run_custom_simulation(runs_count, steps)
        
        # دمج مع تحليل السيناريوهات
        scenario_status = self.scenarios.get_scenario_status()
        
        return {
            "type": "meso",
            "steps": steps,
            "runs": runs_count,
            "aggregated": sim_batch.aggregated_stats if hasattr(sim_batch, 'aggregated_stats') else {},
            "risk_analysis": sim_batch.risk_analysis if hasattr(sim_batch, 'risk_analysis') else {},
            "opportunity_analysis": sim_batch.opportunity_analysis if hasattr(sim_batch, 'opportunity_analysis') else {},
            "scenario_integration": scenario_status
        }
    
    def _run_macro_simulation(self, run: SimulationRun) -> Dict[str, Any]:
        """محاكاة ماكرو (إجمالية)"""
        steps = run.parameters.get("steps", 48)
        runs_count = run.parameters.get("runs", 1000)
        
        # تشغيل المحاكاة
        sim_batch = self.simulation.run_custom_simulation(runs_count, steps)
        
        # دمج مع تحليل المخاطر
        risk_status = self.risk_manager.get_risk_status()
        
        return {
            "type": "macro",
            "steps": steps,
            "runs": runs_count,
            "aggregated": sim_batch.aggregated_stats if hasattr(sim_batch, 'aggregated_stats') else {},
            "risk_analysis": sim_batch.risk_analysis if hasattr(sim_batch, 'risk_analysis') else {},
            "opportunity_analysis": sim_batch.opportunity_analysis if hasattr(sim_batch, 'opportunity_analysis') else {},
            "risk_integration": risk_status
        }
    
    def _run_meta_simulation(self, run: SimulationRun) -> Dict[str, Any]:
        """محاكاة ميتا (تحليلية)"""
        # محاكاة للمحاكاة - تحليل أداء المحاكاة نفسها
        return {
            "type": "meta",
            "analysis": "تحليل أداء المحاكاة",
            "recommendations": [
                "زيادة عدد التشغيلات للحصول على دقة أعلى",
                "تقليل عدد الخطوات للسرعة",
                "استخدام محاكاة موزعة للتوسع"
            ]
        }
    
    def _calculate_run_metrics(self, run: SimulationRun) -> Dict[str, float]:
        """حساب مقاييس التشغيل"""
        metrics = {}
        
        if run.results:
            agg = run.results.get("aggregated", {})
            metrics["success_rate"] = agg.get("avg_success_rate", 0)
            metrics["avg_risk"] = agg.get("avg_risk_score", 0)
            metrics["avg_opportunity"] = agg.get("avg_opportunity_score", 0)
        
        if run.started_at and run.completed_at:
            metrics["duration_seconds"] = run.completed_at - run.started_at
        
        return metrics
    
    # ============================================================
    # إدارة الدفعات
    # ============================================================
    
    def create_batch(self, name: str, runs_config: List[Tuple[str, str, Dict]]) -> str:
        """
        إنشاء دفعة محاكاة جديدة.
        
        runs_config: قائمة من (اسم_التشغيل, السيناريو, المعاملات)
        """
        batch_id = f"sim_batch_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        runs = []
        for run_name, scenario, params in runs_config:
            run_id = self.create_run(run_name, scenario, SIMULATION_LEVEL_MESO, params)
            runs.append(self.runs[run_id])
        
        batch = SimulationBatch(
            id=batch_id,
            name=name,
            runs=runs,
            created_at=time.time(),
            completed_at=None,
            aggregated_metrics={},
            summary={}
        )
        
        self.batches[batch_id] = batch
        
        logger.info(f"📦 دفعة محاكاة جديدة: {name} ({len(runs)} تشغيل)")
        
        return batch_id
    
    def execute_batch(self, batch_id: str, parallel: bool = True) -> bool:
        """
        تنفيذ دفعة محاكاة كاملة.
        
        يمكن تنفيذها بشكل متوازي أو متسلسل.
        """
        batch = self.batches.get(batch_id)
        if not batch:
            return False
        
        if parallel:
            # تنفيذ متوازي
            futures = []
            for run in batch.runs:
                future = self.executor.submit(self.execute_run, run.id)
                futures.append(future)
            
            for future in as_completed(futures):
                pass
        else:
            # تنفيذ متسلسل
            for run in batch.runs:
                self.execute_run(run.id)
        
        batch.completed_at = time.time()
        
        # تجميع المقاييس
        batch.aggregated_metrics = self._aggregate_batch_metrics(batch)
        
        # إنشاء الملخص
        batch.summary = self._create_batch_summary(batch)
        
        # تسجيل
        self.core.append_event(
            event_type="simulation::batch_completed",
            payload={
                "batch_id": batch_id[:16],
                "name": batch.name,
                "runs": len(batch.runs),
                "duration": batch.completed_at - batch.created_at
            }
        )
        
        logger.info(f"✅ اكتملت دفعة {batch.name}: {len(batch.runs)} تشغيل في {batch.completed_at - batch.created_at:.2f} ثانية")
        
        return True
    
    def _aggregate_batch_metrics(self, batch: SimulationBatch) -> Dict[str, Any]:
        """تجميع مقاييس الدفعة"""
        successful = [r for r in batch.runs if r.status == RUN_STATUS_COMPLETED]
        
        if not successful:
            return {}
        
        metrics = {
            "total_runs": len(batch.runs),
            "successful_runs": len(successful),
            "failed_runs": len([r for r in batch.runs if r.status == RUN_STATUS_FAILED]),
            "avg_success_rate": sum(r.metrics.get("success_rate", 0) for r in successful) / len(successful),
            "avg_risk": sum(r.metrics.get("avg_risk", 0) for r in successful) / len(successful),
            "avg_opportunity": sum(r.metrics.get("avg_opportunity", 0) for r in successful) / len(successful),
            "by_scenario": {}
        }
        
        # تجميع حسب السيناريو
        for run in successful:
            scen = run.scenario
            if scen not in metrics["by_scenario"]:
                metrics["by_scenario"][scen] = {
                    "count": 0,
                    "success_rate_sum": 0,
                    "risk_sum": 0,
                    "opportunity_sum": 0
                }
            metrics["by_scenario"][scen]["count"] += 1
            metrics["by_scenario"][scen]["success_rate_sum"] += run.metrics.get("success_rate", 0)
            metrics["by_scenario"][scen]["risk_sum"] += run.metrics.get("avg_risk", 0)
            metrics["by_scenario"][scen]["opportunity_sum"] += run.metrics.get("avg_opportunity", 0)
        
        # حساب المتوسطات لكل سيناريو
        for scen, data in metrics["by_scenario"].items():
            count = data["count"]
            data["avg_success_rate"] = data["success_rate_sum"] / count
            data["avg_risk"] = data["risk_sum"] / count
            data["avg_opportunity"] = data["opportunity_sum"] / count
        
        return metrics
    
    def _create_batch_summary(self, batch: SimulationBatch) -> Dict[str, Any]:
        """إنشاء ملخص للدفعة"""
        summary = {
            "best_run": None,
            "worst_run": None,
            "fastest_run": None,
            "recommendations": []
        }
        
        successful = [r for r in batch.runs if r.status == RUN_STATUS_COMPLETED]
        
        if successful:
            # أفضل تشغيل (أعلى معدل نجاح)
            best = max(successful, key=lambda x: x.metrics.get("success_rate", 0))
            summary["best_run"] = {
                "name": best.name,
                "success_rate": best.metrics.get("success_rate", 0)
            }
            
            # أسوأ تشغيل (أقل معدل نجاح)
            worst = min(successful, key=lambda x: x.metrics.get("success_rate", 0))
            summary["worst_run"] = {
                "name": worst.name,
                "success_rate": worst.metrics.get("success_rate", 0)
            }
            
            # أسرع تشغيل
            fastest = min(successful, key=lambda x: x.metrics.get("duration_seconds", 999999))
            summary["fastest_run"] = {
                "name": fastest.name,
                "duration": fastest.metrics.get("duration_seconds", 0)
            }
        
        return summary
    
    def _process_batches_loop(self):
        """معالجة الدفعات في الخلفية"""
        while self._active:
            try:
                # معالجة الدفعات المعلقة
                for batch in self.batches.values():
                    if batch.completed_at is None:
                        self.execute_batch(batch.id, parallel=True)
                
                threads.interruptible_sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في معالجة الدفعات: {e}")
                threads.interruptible_sleep(60)
    
    # ============================================================
    # تحليل النتائج
    # ============================================================
    
    def generate_report(self, batch_id: str):
        """
        توليد تقرير مفصل عن دفعة محاكاة.
        """
        batch = self.batches.get(batch_id)
        if not batch:
            return None
        
        insights = self._generate_insights(batch)
        recommendations = self._generate_recommendations(batch)
        narrative = self._generate_report_narrative(batch)
        
        report = SimulationReport(
            timestamp=time.time(),
            batch_id=batch_id[:16],
            total_runs=len(batch.runs),
            successful_runs=len([r for r in batch.runs if r.status == RUN_STATUS_COMPLETED]),
            failed_runs=len([r for r in batch.runs if r.status == RUN_STATUS_FAILED]),
            aggregated_metrics=batch.aggregated_metrics,
            insights=insights,
            recommendations=recommendations,
            narrative=narrative
        )
        
        self.reports.append(report)
        
        # حفظ التقرير
        self._save_report(report)
        
        return report
    
    def _generate_insights(self, batch: SimulationBatch) -> List[str]:
        """توليد رؤى من نتائج المحاكاة"""
        insights = []
        metrics = batch.aggregated_metrics
        
        if metrics.get("avg_success_rate", 0) > 0.7:
            insights.append("نسبة نجاح عالية للمحاكاة - النظام في حالة جيدة")
        elif metrics.get("avg_success_rate", 0) < 0.4:
            insights.append("نسبة نجاح منخفضة - الحاجة إلى تحسينات عاجلة")
        
        if metrics.get("avg_risk", 0) > 0.6:
            insights.append("مستوى مخاطر مرتفع - الاستعداد للطوارئ مطلوب")
        
        if metrics.get("avg_opportunity", 0) > 0.6:
            insights.append("فرص كبيرة متوقعة - استغلالها قد يحقق مكاسب")
        
        # تحليل حسب السيناريو
        by_scenario = metrics.get("by_scenario", {})
        if by_scenario:
            best_scenario = max(by_scenario.items(), key=lambda x: x[1].get("avg_success_rate", 0))
            worst_scenario = min(by_scenario.items(), key=lambda x: x[1].get("avg_success_rate", 0))
            
            if best_scenario[0]:
                insights.append(f"أفضل سيناريو: {best_scenario[0]} (نجاح {best_scenario[1]['avg_success_rate']:.1%})")
            
            if worst_scenario[0]:
                insights.append(f"أسوأ سيناريو: {worst_scenario[0]} (نجاح {worst_scenario[1]['avg_success_rate']:.1%})")
        
        return insights
    
    def _generate_recommendations(self, batch: SimulationBatch) -> List[Dict[str, Any]]:
        """توليد توصيات من نتائج المحاكاة"""
        recommendations = []
        metrics = batch.aggregated_metrics
        
        if metrics.get("avg_success_rate", 0) < 0.5:
            recommendations.append({
                "action": "تحسين أداء النظام",
                "priority": "عالية",
                "reason": "نتائج المحاكاة تشير إلى ضعف عام",
                "confidence": 1 - metrics.get("avg_success_rate", 0.5)
            })
        
        if metrics.get("avg_risk", 0) > 0.5:
            recommendations.append({
                "action": "تفعيل إجراءات تخفيف المخاطر",
                "priority": "عالية",
                "reason": "مستوى مخاطر مرتفع في المحاكاة",
                "confidence": metrics.get("avg_risk", 0)
            })
        
        # توصيات حسب السيناريو
        by_scenario = metrics.get("by_scenario", {})
        for scenario, data in by_scenario.items():
            if data.get("avg_risk", 0) > 0.6:
                recommendations.append({
                    "action": f"الاستعداد لسيناريو {scenario}",
                    "priority": "متوسطة",
                    "reason": "مخاطر عالية في هذا السيناريو",
                    "confidence": data.get("avg_risk", 0)
                })
        
        return recommendations
    
    def _generate_report_narrative(self, batch: SimulationBatch) -> str:
        """توليد سرد للتقرير"""
        metrics = batch.aggregated_metrics
        
        narrative = f"📊 تقرير محاكاة: {batch.name}\n"
        narrative += f"إجمالي التشغيلات: {len(batch.runs)}\n"
        narrative += f"نسبة النجاح: {metrics.get('avg_success_rate', 0):.1%}\n"
        narrative += f"مستوى المخاطر: {metrics.get('avg_risk', 0):.1%}\n"
        narrative += f"مستوى الفرص: {metrics.get('avg_opportunity', 0):.1%}\n"
        
        if metrics.get('avg_success_rate', 0) > 0.7:
            narrative += "✅ النظام في حالة جيدة.\n"
        elif metrics.get('avg_success_rate', 0) < 0.4:
            narrative += "⚠️ النظام يحتاج إلى تحسينات عاجلة.\n"
        
        return narrative
    
    def _analyze_results_loop(self):
        """تحليل مستمر لنتائج المحاكاة"""
        while self._active:
            try:
                for batch in self.batches.values():
                    if batch.completed_at and not self._is_batch_analyzed(batch):
                        report = self.generate_report(batch.id)
                        if report:
                            logger.info(f"📊 تم تحليل دفعة {batch.name}: {len(report.insights)} رؤى")
                
                threads.interruptible_sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في تحليل النتائج: {e}")
                threads.interruptible_sleep(60)
    
    def _is_batch_analyzed(self, batch: SimulationBatch) -> bool:
        """التحقق مما إذا كانت الدفعة قد حللت"""
        return any(r.batch_id == batch.id[:16] for r in self.reports)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة نواة المحاكاة"""
        try:
            state = {
                "runs_count": len(self.runs),
                "batches_count": len(self.batches),
                "reports_count": len(self.reports),
                "max_workers": self.max_workers,
                "saved_at": time.time()
            }
            atomic_write_json(SIMCORE_STATE_FILE, state, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة نواة المحاكاة: {e}")
    
    def _load_state(self):
        """تحميل حالة نواة المحاكاة"""
        try:
            if SIMCORE_STATE_FILE.exists():
                with open(SIMCORE_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.max_workers = state.get("max_workers", 4)
                    self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
                logger.info("📂 تم تحميل حالة نواة المحاكاة")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة نواة المحاكاة: {e}")
    
    def _save_report(self, report: SimulationReport):
        """حفظ تقرير محاكاة"""
        try:
            report_file = SIMCORE_RESULTS_DIR / f"report_{report.batch_id}_{int(report.timestamp)}.json"
            atomic_write_json(report_file, report.__dict__, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ التقرير: {e}")
    
    # ============================================================
    # دورة نواة المحاكاة
    # ============================================================
    
    def core_cycle(self):
        """
        دورة نواة محاكاة كاملة.
        
        تشغيل دفعة قياسية وتحليل النتائج.
        """
        # إنشاء دفعة قياسية
        batch_id = self.create_batch(
            name="standard_benchmark",
            runs_config=[
                ("growth_test", "النمو المتسارع", {"steps": 12, "runs": 100}),
                ("stability_test", "الاستقرار والتوازن", {"steps": 12, "runs": 100}),
                ("regression_test", "التدهور التدريجي", {"steps": 12, "runs": 100}),
                ("fragmentation_test", "تشظي الهوية", {"steps": 12, "runs": 100})
            ]
        )
        
        # تنفيذ الدفعة
        self.execute_batch(batch_id, parallel=True)
        
        # إنشاء التقرير
        report = self.generate_report(batch_id)
        
        return report
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_core_status(self) -> Dict[str, Any]:
        """الحالة الحالية لنواة المحاكاة"""
        return {
            "total_runs": len(self.runs),
            "completed_runs": len([r for r in self.runs.values() if r.status == RUN_STATUS_COMPLETED]),
            "failed_runs": len([r for r in self.runs.values() if r.status == RUN_STATUS_FAILED]),
            "total_batches": len(self.batches),
            "completed_batches": len([b for b in self.batches.values() if b.completed_at]),
            "total_reports": len(self.reports),
            "max_workers": self.max_workers,
            "timestamp": time.time()
        }
    
    def get_runs(self, status: str = None) -> List[Dict]:
        """الحصول على التشغيلات"""
        runs = self.runs.values()
        if status:
            runs = [r for r in runs if r.status == status]
        
        return [
            {
                "id": r.id[:16],
                "name": r.name,
                "scenario": r.scenario,
                "status": r.status,
                "duration": r.metrics.get("duration_seconds", 0) if r.completed_at else None,
                "success_rate": r.metrics.get("success_rate", 0)
            }
            for r in runs
        ]
    
    def get_batches(self) -> List[Dict]:
        """الحصول على الدفعات"""
        return [
            {
                "id": b.id[:16],
                "name": b.name,
                "runs_count": len(b.runs),
                "completed": b.completed_at is not None,
                "avg_success": b.aggregated_metrics.get("avg_success_rate", 0)
            }
            for b in self.batches.values()
        ]
    
    def get_reports(self, limit: int = 10) -> List[Dict]:
        """الحصول على التقارير"""
        return [
            {
                "timestamp": r.timestamp,
                "batch_id": r.batch_id,
                "total_runs": r.total_runs,
                "success_rate": r.aggregated_metrics.get("avg_success_rate", 0),
                "insights": r.insights[:3]
            }
            for r in self.reports[-limit:]
        ]
    
    def run_custom_batch(self, name: str, scenarios: List[str], 
                         runs_per_scenario: int = 100, steps: int = 12) -> str:
        """
        تشغيل دفعة مخصصة.
        """
        runs_config = []
        for scenario in scenarios:
            runs_config.append((f"{scenario}_test", scenario, {"steps": steps, "runs": runs_per_scenario}))
        
        batch_id = self.create_batch(name, runs_config)
        self.execute_batch(batch_id, parallel=True)
        
        return batch_id[:16]
    
    def get_simulation_quote(self) -> str:
        """اقتباس عن المحاكاة"""
        quotes = [
            "المحاكاة هي مختبر النظام السري.",
            "تشغيلات متعددة تكشف الأنماط الخفية.",
            "التجميع الذكي يعطي صورة كاملة.",
            "التقارير الواضحة توجه القرارات.",
            "المحاكاة ليست تنبؤاً، بل هي استعداد.",
            "آلاف التشغيلات تخبرك ما لا تعرفه.",
            "المحاكاة الجيدة تنقذ من المفاجآت."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف نواة المحاكاة"""
        self._active = False
        self.executor.shutdown(wait=False)
        self._save_state()
        logger.info("🛑 إيقاف نواة المحاكاة الداخلية")


# ============================================================
# الـ Singleton
# ============================================================

_simcore_instance: Optional[SimulationCore] = None
_simcore_lock = threading.Lock()


def get_simulation_core() -> SimulationCore:
    """الحصول على النسخة الوحيدة من نواة المحاكاة الداخلية"""
    global _simcore_instance
    if _simcore_instance is None:
        with _simcore_lock:
            if _simcore_instance is None:
                _simcore_instance = SimulationCore()
    return _simcore_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔁 نواة المحاكاة الداخلية الجبارة - تدير آلاف التشغيلات")
    print("=" * 80 + "\n")
    
    simcore = get_simulation_core()
    
    # 1) دورة نواة
    print("🔄 دورة نواة محاكاة...")
    report = simcore.core_cycle()
    print(f"   التقرير: {report.batch_id}")
    print(f"   إجمالي التشغيلات: {report.total_runs}")
    print(f"   الناجحة: {report.successful_runs}")
    print(f"   الفاشلة: {report.failed_runs}")
    print(f"   معدل النجاح: {report.aggregated_metrics.get('avg_success_rate', 0):.1%}")
    
    # 2) الرؤى
    print("\n💡 الرؤى المستخلصة:")
    for insight in report.insights:
        print(f"   • {insight}")
    
    # 3) التوصيات
    print("\n🎯 التوصيات:")
    for rec in report.recommendations:
        print(f"   • {rec['action']} (أولوية: {rec['priority']})")
    
    # 4) السرد
    print(f"\n📖 السرد:\n{report.narrative}")
    
    # 5) حالة نواة المحاكاة
    print("\n📊 حالة نواة المحاكاة:")
    status = simcore.get_core_status()
    print(f"   إجمالي التشغيلات: {status['total_runs']}")
    print(f"   التشغيلات الناجحة: {status['completed_runs']}")
    print(f"   إجمالي الدفعات: {status['total_batches']}")
    print(f"   الدفعات المكتملة: {status['completed_batches']}")
    print(f"   التقارير: {status['total_reports']}")
    
    # 6) التشغيلات
    print("\n📋 التشغيلات:")
    runs = simcore.get_runs()
    for r in runs[:5]:
        print(f"   {r['name']}: {r['status']} (نجاح {r['success_rate']:.1%})")
    
    # 7) الدفعات
    print("\n📦 الدفعات:")
    batches = simcore.get_batches()
    for b in batches:
        print(f"   {b['name']}: {b['runs_count']} تشغيل, نجاح {b['avg_success']:.1%}")
    
    # 8) تشغيل دفعة مخصصة
    print("\n⚙️ تشغيل دفعة مخصصة...")
    batch_id = simcore.run_custom_batch(
        name="security_focus",
        scenarios=["اختراق أمني محتمل", "انحراف عن إرادة السيد"],
        runs_per_scenario=50,
        steps=8
    )
    print(f"   معرف الدفعة: {batch_id}")
    
    # 9) اقتباس
    print(f"\n💭 {simcore.get_simulation_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ نواة المحاكاة الداخلية الجبارة جاهزة - تدير آلاف التشغيلات")
    print("=" * 80)
