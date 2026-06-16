# backend/simulation/simulation_controller.py
# 🎛 المتحكم الأعلى لطبقة المحاكاة الجبار - يوحد كل مكونات المحاكاة
# الإصدار: 3.0.0 - قيادة موحدة لكل عمليات المحاكاة

"""
المتحكم الأعلى لطبقة المحاكاة.

الفلسفة:
- التحكم المركزي يبسط التعقيد
- الواجهة الموحدة تقلل من تكرار الكود
- القرارات الذكية تعتمد على التحليل
- التكامل السلس يسرع التنفيذ
- المراقبة المستمرة تضمن الجودة

هذه ليست مجرد تنسيق. هذه هي قيادة المحاكاة الموحدة.
"""

import json
import time
import threading
import random
import secrets
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

try:
    from ..memory.core import get_core, EventType
    from ..config import DATA_DIR
    from .simulation_core import get_simulation_core
    from .simulation_environment import get_simulation_environment_manager
    from .simulation_scheduler import get_simulation_scheduler
    from .simulation_analyzer import get_simulation_analyzer
except ImportError:
    from memory.core import get_core, EventType
    from config import DATA_DIR
    from .simulation_core import get_simulation_core
    from .simulation_environment import get_simulation_environment_manager
    from .simulation_scheduler import get_simulation_scheduler
    from .simulation_analyzer import get_simulation_analyzer

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات المتحكم
# ============================================================

CONTROLLER_DIR = DATA_DIR / "simulation" / "controller"
CONTROLLER_DIR.mkdir(parents=True, exist_ok=True)
CONTROLLER_LOG = CONTROLLER_DIR / "controller_log.jsonl"
CONTROLLER_STATE_FILE = CONTROLLER_DIR / "controller_state.json"
CONTROLLER_DECISIONS_DIR = CONTROLLER_DIR / "decisions"

CONTROLLER_DECISIONS_DIR.mkdir(parents=True, exist_ok=True)

# أوامر التحكم
CONTROL_COMMAND_RUN_BATCH = "run_batch"
CONTROL_COMMAND_SCHEDULE = "schedule"
CONTROL_COMMAND_ANALYZE = "analyze"
CONTROL_COMMAND_OPTIMIZE = "optimize"
CONTROL_COMMAND_REPORT = "report"
CONTROL_COMMAND_EMERGENCY = "emergency"

# حالات المتحكم
CONTROLLER_STATUS_IDLE = "idle"
CONTROLLER_STATUS_RUNNING = "running"
CONTROLLER_STATUS_ANALYZING = "analyzing"
CONTROLLER_STATUS_OPTIMIZING = "optimizing"
CONTROLLER_STATUS_ERROR = "error"


def _now_iso() -> str:
    """إرجاع الوقت الحالي بصيغة ISO"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat() + "Z"


@dataclass
class ControlDecision:
    """قرار تحكم"""
    id: str
    command: str
    parameters: Dict[str, Any]
    reason: str
    timestamp: float
    status: str
    result: Optional[Dict[str, Any]]
    execution_time: Optional[float]


@dataclass
class ControlSnapshot:
    """لقطة تحكم"""
    timestamp: float
    status: str
    active_batches: int
    scheduled_jobs: int
    total_analyses: int
    pending_decisions: int
    last_action: Optional[str]
    recommendations: List[Dict[str, Any]]
    system_health: float
    narrative: str


# ============================================================
# المتحكم الأعلى لطبقة المحاكاة الجبار
# ============================================================

class SimulationController:
    """
    المتحكم الأعلى لطبقة المحاكاة الجبار - يوحد كل مكونات المحاكاة.
    
    المبادئ:
    1. التحكم المركزي يبسط التعقيد
    2. الواجهة الموحدة تقلل من تكرار الكود
    3. القرارات الذكية تعتمد على التحليل
    4. التكامل السلس يسرع التنفيذ
    5. المراقبة المستمرة تضمن الجودة
    """
    
    def __init__(self):
        self.core = get_core()
        self.sim_core = get_simulation_core()
        self.env_manager = get_simulation_environment_manager()
        self.scheduler = get_simulation_scheduler()
        self.analyzer = get_simulation_analyzer()
        
        # حالة المتحكم
        self.status = CONTROLLER_STATUS_IDLE
        self.decisions: List[ControlDecision] = []
        self.recommendations: List[Dict[str, Any]] = []
        
        # حالة التكامل
        self.mode = "simulation"
        self.last_output = {}
        self.controller_history = []
        self._index = self._load_index()
        
        # السياسات
        self.policies = {
            "max_controller_depth": 5,
            "stability_threshold": 0.5,
            "noise_scale": 0.1,
            "auto_balance": True,
        }
        
        # إحصائيات
        self.stats = {
            "total_batches_run": 0,
            "total_jobs_scheduled": 0,
            "total_analyses_performed": 0,
            "total_decisions_made": 0
        }
        
        # خلفيات التحكم
        self._active = True
        self._control_loop = threading.Thread(target=self._continuous_control, daemon=True)
        self._control_loop.start()
        
        self._decision_executor = threading.Thread(target=self._execute_decisions_loop, daemon=True)
        self._decision_executor.start()
        
        self._health_monitor = threading.Thread(target=self._monitor_health_loop, daemon=True)
        self._health_monitor.start()
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("🎛 المتحكم الأعلى لطبقة المحاكاة الجبار جاهز - قيادة موحدة لكل عمليات المحاكاة")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمتحكم المحاكاة
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمتحكم المحاكاة.
        """
        # إعادة الوضع الافتراضي
        self.mode = "simulation"
        
        # مسح نتائج التكامل السابقة
        self.last_output = {}
        self.controller_history = []
        
        # إعادة تعيين حالة المتحكم
        self.status = CONTROLLER_STATUS_IDLE
        self.decisions = []
        self.recommendations = []
        
        # إعادة تعيين الإحصائيات
        self.stats = {
            "total_batches_run": 0,
            "total_jobs_scheduled": 0,
            "total_analyses_performed": 0,
            "total_decisions_made": 0
        }
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # إعادة السياسات الافتراضية
        self.policies = {
            "max_controller_depth": 5,
            "stability_threshold": 0.5,
            "noise_scale": 0.1,
            "auto_balance": True,
        }
        
        # إعادة تهيئة المحركات التابعة
        try:
            self.sim_core.reset()
        except:
            pass
        
        try:
            self.env_manager.reset()
        except:
            pass
        
        try:
            self.scheduler.reset()
        except:
            pass
        
        try:
            self.analyzer.reset()
        except:
            pass
        
        # تسجيل عملية إعادة التهيئة
        self.core.append_event(
            event_type="simulation::controller::reset",
            payload={
                "timestamp": _now_iso(),
                "status": "simulation_controller_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة متحكم المحاكاة اكتملت")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"decisions": [], "last_updated": time.time()}
    
    # ============================================================
    # الأوامر عالية المستوى
    # ============================================================
    
    def run_simulation_batch(self, scenarios: List[str], runs: int = 100,
                             steps: int = 12, name: str = None) -> Dict[str, Any]:
        """
        تشغيل دفعة محاكاة فورية.
        """
        if name is None:
            name = f"batch_{int(time.time())}"
        
        command_id = f"cmd_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        decision = ControlDecision(
            id=command_id,
            command=CONTROL_COMMAND_RUN_BATCH,
            parameters={
                "scenarios": scenarios,
                "runs": runs,
                "steps": steps,
                "name": name
            },
            reason="تنفيذ فوري بأمر المستخدم",
            timestamp=time.time(),
            status="pending",
            result=None,
            execution_time=None
        )
        
        self.decisions.append(decision)
        self.stats["total_batches_run"] += 1
        self.stats["total_decisions_made"] += 1
        
        # تنفيذ فوري
        result = self._execute_batch(scenarios, runs, steps, name)
        decision.status = "completed"
        decision.result = result
        decision.execution_time = time.time() - decision.timestamp
        
        # تسجيل
        self.core.append_event(
            event_type="controller::batch_executed",
            payload={
                "batch_name": name,
                "scenarios": scenarios,
                "runs": runs,
                "steps": steps
            }
        )
        
        logger.info(f"🎛 تشغيل دفعة محاكاة: {name} ({len(scenarios)} سيناريو, {runs} تشغيل)")
        
        return result
    
    def _execute_batch(self, scenarios: List[str], runs: int, steps: int, name: str) -> Dict[str, Any]:
        """تنفيذ دفعة محاكاة"""
        # تشغيل الدفعة
        batch_id = self.sim_core.run_custom_batch(name, scenarios, runs, steps)
        
        # انتظار اكتمال الدفعة
        batch = None
        for b in self.sim_core.batches.values():
            if b.id.startswith(batch_id):
                batch = b
                break
        
        # تحليل النتائج
        if batch and hasattr(batch, 'completed_at') and batch.completed_at:
            report = self.analyzer.analyze_batch(batch_id)
            
            return {
                "batch_id": batch_id,
                "batch_name": name,
                "scenarios": scenarios,
                "runs": runs,
                "steps": steps,
                "success_rate": report.kpis.get("stability", 0),
                "report_id": report.id[:16],
                "insights": report.insights[:5],
                "recommendations": report.recommendations[:5]
            }
        
        return {
            "batch_id": batch_id,
            "batch_name": name,
            "status": "processing",
            "message": "الدفعة قيد المعالجة"
        }
    
    def schedule_simulation(self, scenarios: List[str], schedule_type: str,
                            interval: int = None, scheduled_time: float = None,
                            runs: int = 100, steps: int = 12,
                            priority: int = 5) -> List[str]:
        """
        جدولة محاكاة (فورية، متكررة، لمرة واحدة، مؤجلة).
        """
        job_ids = []
        
        for scenario in scenarios:
            job_id = self.scheduler.schedule_job(
                name=f"scheduled_{scenario}_{int(time.time())}",
                scenario=scenario,
                schedule_type=schedule_type,
                interval_seconds=interval,
                scheduled_time=scheduled_time,
                priority=priority,
                parameters={"runs": runs, "steps": steps}
            )
            job_ids.append(job_id)
            self.stats["total_jobs_scheduled"] += 1
        
        # تسجيل
        self.core.append_event(
            event_type="controller::simulations_scheduled",
            payload={
                "job_ids": [jid[:16] for jid in job_ids],
                "schedule_type": schedule_type,
                "scenarios": scenarios
            }
        )
        
        logger.info(f"🎛 جدولة {len(scenarios)} محاكاة (نوع: {schedule_type})")
        
        return job_ids
    
    def analyze_results(self, batch_id: str = None) -> Dict[str, Any]:
        """
        تحليل نتائج المحاكاة.
        """
        self.status = CONTROLLER_STATUS_ANALYZING
        
        if batch_id:
            report = self.analyzer.analyze_batch(batch_id)
        else:
            # تحليل أحدث دفعة
            if self.sim_core.batches:
                latest = max(self.sim_core.batches.values(), key=lambda b: b.created_at)
                report = self.analyzer.analyze_batch(latest.id[:16])
            else:
                report = None
        
        self.stats["total_analyses_performed"] += 1
        self.status = CONTROLLER_STATUS_IDLE
        
        if report:
            return {
                "report_id": report.id[:16],
                "insights": report.insights,
                "recommendations": report.recommendations,
                "kpis": report.kpis,
                "narrative": report.narrative
            }
        
        return {"error": "لا توجد نتائج للتحليل"}
    
    def optimize_next_batch(self, based_on: str = "latest_analysis") -> Dict[str, Any]:
        """
        تحسين الدفعة التالية بناءً على التحليلات السابقة.
        """
        self.status = CONTROLLER_STATUS_OPTIMIZING
        
        # الحصول على أحدث تحليل
        latest_analysis = self.analyzer.get_latest_report()
        
        if not latest_analysis:
            return {"error": "لا توجد تحليلات سابقة للتحسين"}
        
        # استخراج التوصيات
        recommendations = latest_analysis.get("recommendations", [])
        
        # تحديد السيناريوهات المحسنة
        optimized_scenarios = ["النمو المتسارع", "الاستقرار والتوازن"]
        
        # تحديد المعاملات المحسنة
        if recommendations:
            for rec in recommendations:
                if "تحسين" in rec.get("action", ""):
                    optimized_scenarios.append("تحسين الأداء")
        
        # تشغيل الدفعة المحسنة
        result = self.run_simulation_batch(
            scenarios=optimized_scenarios,
            runs=150,
            steps=15,
            name=f"optimized_batch_{int(time.time())}"
        )
        
        self.status = CONTROLLER_STATUS_IDLE
        
        return {
            "optimized_scenarios": optimized_scenarios,
            "based_on": based_on,
            "recommendations_used": len(recommendations),
            "batch_result": result
        }
    
    def get_system_health(self) -> float:
        """
        حساب صحة نظام المحاكاة بأكمله.
        """
        # صحة النواة
        core_status = self.sim_core.get_core_status()
        core_health = 1.0 if core_status.get("total_runs", 0) > 0 else 0.5
        
        # صحة المجدول
        scheduler_status = self.scheduler.get_scheduler_status()
        scheduler_health = 1.0 if scheduler_status.get("pending_jobs", 0) == 0 else 0.7
        
        # صحة المحلل
        analyzer_status = self.analyzer.get_analyzer_status()
        analyzer_health = 1.0 if analyzer_status.get("total_reports", 0) > 0 else 0.6
        
        # متوسط الصحة
        health = (core_health + scheduler_health + analyzer_health) / 3
        
        return min(1.0, health)
    
    # ============================================================
    # اتخاذ القرارات الذكية
    # ============================================================
    
    def make_control_decision(self) -> ControlDecision:
        """
        اتخاذ قرار تحكم ذكي بناءً على حالة النظام.
        
        يعتمد على:
        - نتائج التحليلات السابقة
        - حالة الجدولة
        - صحة النظام
        """
        # الحصول على أحدث تحليل
        latest_analysis = self.analyzer.get_latest_report()
        
        # الحصول على حالة النظام
        scheduler_status = self.scheduler.get_scheduler_status()
        health = self.get_system_health()
        
        # اختيار القرار المناسب
        if health < 0.5:
            # صحة منخفضة - تشغيل دفعة تشخيصية
            command = CONTROL_COMMAND_RUN_BATCH
            parameters = {
                "scenarios": ["الاستقرار والتوازن", "التشخيص"],
                "runs": 50,
                "steps": 8,
                "name": f"diagnostic_{int(time.time())}"
            }
            reason = "صحة النظام منخفضة، الحاجة لتشخيص"
            
        elif scheduler_status.get("pending_jobs", 0) > 5:
            # قائمة انتظار طويلة - تحليل الأداء
            command = CONTROL_COMMAND_ANALYZE
            parameters = {"focus": "performance"}
            reason = "قائمة انتظار طويلة، تحليل الأداء مطلوب"
            
        elif latest_analysis and latest_analysis.get("recommendations"):
            # هناك توصيات - تحسين
            command = CONTROL_COMMAND_OPTIMIZE
            parameters = {"based_on": "latest_analysis"}
            reason = "تطبيق توصيات التحليل"
            
        else:
            # عملية عادية - تقرير
            command = CONTROL_COMMAND_REPORT
            parameters = {"level": "summary"}
            reason = "تقرير دوري"
        
        decision = ControlDecision(
            id=f"ctrl_dec_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            command=command,
            parameters=parameters,
            reason=reason,
            timestamp=time.time(),
            status="pending",
            result=None,
            execution_time=None
        )
        
        self.decisions.append(decision)
        self.stats["total_decisions_made"] += 1
        
        return decision
    
    def execute_decision(self, decision: ControlDecision) -> Dict[str, Any]:
        """
        تنفيذ قرار تحكم.
        """
        result = {}
        
        if decision.command == CONTROL_COMMAND_RUN_BATCH:
            params = decision.parameters
            result = self.run_simulation_batch(
                scenarios=params.get("scenarios", []),
                runs=params.get("runs", 100),
                steps=params.get("steps", 12),
                name=params.get("name", f"auto_batch_{int(time.time())}")
            )
            
        elif decision.command == CONTROL_COMMAND_ANALYZE:
            result = self.analyze_results()
            
        elif decision.command == CONTROL_COMMAND_OPTIMIZE:
            result = self.optimize_next_batch()
            
        elif decision.command == CONTROL_COMMAND_REPORT:
            result = self.control_cycle().__dict__
        
        decision.result = result
        decision.status = "completed"
        decision.execution_time = time.time() - decision.timestamp
        
        # تسجيل
        self.core.append_event(
            event_type="controller::decision_executed",
            payload={
                "command": decision.command,
                "execution_time": decision.execution_time
            }
        )
        
        return result
    
    def _execute_decisions_loop(self):
        """تنفيذ القرارات المعلقة"""
        while self._active:
            try:
                pending = [d for d in self.decisions if d.status == "pending"]
                for decision in pending:
                    self.execute_decision(decision)
                
                time.sleep(5)  # كل 5 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في تنفيذ القرارات: {e}")
                time.sleep(5)
    
    # ============================================================
    # دورة التحكم المستمرة
    # ============================================================
    
    def _continuous_control(self):
        """حلقة تحكم مستمرة"""
        while self._active:
            try:
                # اتخاذ قرار تحكم
                decision = self.make_control_decision()
                
                # تسجيل
                logger.info(f"🎛 قرار تحكم: {decision.command} - {decision.reason}")
                
                time.sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في حلقة التحكم: {e}")
                time.sleep(60)
    
    def _monitor_health_loop(self):
        """مراقبة صحة النظام"""
        while self._active:
            try:
                health = self.get_system_health()
                
                if health < 0.4:
                    logger.warning(f"⚠️ صحة النظام منخفضة: {health:.1%}")
                
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في مراقبة الصحة: {e}")
                time.sleep(30)
    
    # ============================================================
    # دورة التحكم الكاملة
    # ============================================================
    
    def control_cycle(self) -> ControlSnapshot:
        """
        دورة تحكم كاملة.
        
        تجمع:
        - حالة البيئات
        - حالة الجدولة
        - أحدث التحليلات
        - توصيات عالية المستوى
        """
        # جمع البيانات
        templates = self.env_manager.list_templates()
        scheduler_status = self.scheduler.get_scheduler_status()
        latest_analysis = self.analyzer.get_latest_report()
        
        # حساب صحة النظام
        health = self.get_system_health()
        
        # توليد توصيات
        recommendations = []
        if latest_analysis:
            recommendations = latest_analysis.get("recommendations", [])
        
        # سرد التحكم
        narrative = self.generate_control_narrative(health, scheduler_status)
        
        snapshot = ControlSnapshot(
            timestamp=time.time(),
            status=self.status,
            active_batches=len([b for b in self.sim_core.batches.values() if not hasattr(b, 'completed_at') or not b.completed_at]),
            scheduled_jobs=scheduler_status.get("pending_jobs", 0),
            total_analyses=self.stats["total_analyses_performed"],
            pending_decisions=len([d for d in self.decisions if d.status == "pending"]),
            last_action=self.decisions[-1].command if self.decisions else None,
            recommendations=recommendations[:10],
            system_health=health,
            narrative=narrative
        )
        
        self.controller_history.append(snapshot)
        
        # تسجيل
        self.core.append_event(
            event_type="controller::snapshot",
            payload={
                "status": snapshot.status,
                "active_batches": snapshot.active_batches,
                "scheduled_jobs": snapshot.scheduled_jobs,
                "system_health": snapshot.system_health
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    def generate_control_narrative(self, health: float, scheduler_status: Dict) -> str:
        """
        توليد سرد للتحكم.
        """
        narrative = f"🎛 **حالة المتحكم**: {self.status}\n"
        narrative += f"🏥 **صحة النظام**: {health:.1%}\n"
        narrative += f"📊 **دفعات نشطة**: {len([b for b in self.sim_core.batches.values() if not hasattr(b, 'completed_at') or not b.completed_at])}\n"
        narrative += f"⏱ **وظائف مجدولة**: {scheduler_status.get('pending_jobs', 0)}\n"
        narrative += f"📈 **إجمالي التحليلات**: {self.stats['total_analyses_performed']}\n"
        
        if health > 0.8:
            narrative += "✅ النظام في حالة ممتازة.\n"
        elif health > 0.6:
            narrative += "👍 النظام في حالة جيدة.\n"
        elif health > 0.4:
            narrative += "⚠️ النظام يحتاج إلى مراقبة.\n"
        else:
            narrative += "🚨 النظام في حالة حرجة!\n"
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة المتحكم"""
        try:
            state = {
                "status": self.status,
                "stats": self.stats,
                "decisions_count": len(self.decisions),
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
                    self.status = state.get("status", CONTROLLER_STATUS_IDLE)
                    self.stats = state.get("stats", self.stats)
                logger.info("📂 تم تحميل حالة المتحكم")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المتحكم: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_controller_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمتحكم"""
        snapshot = self.control_cycle()
        
        return {
            "status": snapshot.status,
            "active_batches": snapshot.active_batches,
            "scheduled_jobs": snapshot.scheduled_jobs,
            "total_analyses": snapshot.total_analyses,
            "pending_decisions": snapshot.pending_decisions,
            "system_health": snapshot.system_health,
            "last_action": snapshot.last_action,
            "recommendations": snapshot.recommendations[:5],
            "narrative": snapshot.narrative,
            "timestamp": snapshot.timestamp
        }
    
    def get_decisions(self, limit: int = 20) -> List[Dict]:
        """سجل القرارات"""
        return [
            {
                "id": d.id[:16],
                "command": d.command,
                "reason": d.reason,
                "status": d.status,
                "execution_time": d.execution_time,
                "timestamp": d.timestamp
            }
            for d in self.decisions[-limit:]
        ]
    
    def get_statistics(self) -> Dict[str, int]:
        """إحصائيات المتحكم"""
        return self.stats.copy()
    
    def emergency_stop(self) -> Dict[str, Any]:
        """
        إيقاف طارئ لجميع عمليات المحاكاة.
        """
        self.status = CONTROLLER_STATUS_ERROR
        
        # إلغاء جميع الوظائف المجدولة
        jobs = self.scheduler.list_jobs()
        for job in jobs:
            self.scheduler.cancel_job(job["id"])
        
        # إنهاء الدفعات النشطة
        for batch in self.sim_core.batches.values():
            if not hasattr(batch, 'completed_at') or not batch.completed_at:
                # وضع علامة كمكتمل بالقوة
                if hasattr(batch, 'completed_at'):
                    batch.completed_at = time.time()
        
        result = {
            "emergency_stop": True,
            "cancelled_jobs": len(jobs),
            "stopped_batches": len([b for b in self.sim_core.batches.values() if hasattr(b, 'completed_at') and b.completed_at]),
            "timestamp": time.time()
        }
        
        self.core.append_event(
            event_type="controller::emergency_stop",
            payload=result
        )
        
        logger.warning("🚨 إيقاف طارئ لجميع عمليات المحاكاة")
        
        return result
    
    def reset_controller(self) -> bool:
        """
        إعادة تعيين المتحكم.
        """
        self.status = CONTROLLER_STATUS_IDLE
        self.decisions = []
        self.recommendations = []
        self.stats = {
            "total_batches_run": 0,
            "total_jobs_scheduled": 0,
            "total_analyses_performed": 0,
            "total_decisions_made": 0
        }
        
        self._save_state()
        
        logger.info("🔄 إعادة تعيين المتحكم")
        
        return True
    
    def get_controller_quote(self) -> str:
        """اقتباس عن التحكم"""
        quotes = [
            "التحكم المركزي يبسط التعقيد.",
            "القرارات الذكية تعتمد على التحليل.",
            "التكامل السلس يسرع التنفيذ.",
            "المراقبة المستمرة تضمن الجودة.",
            "القيادة الموحدة تحقق الكفاءة.",
            "التحكم الجيد يسبق التنفيذ الجيد.",
            "العين التي ترى كل شيء تتحكم في كل شيء."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف المتحكم"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف المتحكم الأعلى للمحاكاة")


# ============================================================
# الـ Singleton
# ============================================================

_controller_instance: Optional[SimulationController] = None
_controller_lock = threading.Lock()


def get_simulation_controller() -> SimulationController:
    """الحصول على النسخة الوحيدة من المتحكم الأعلى للمحاكاة"""
    global _controller_instance
    if _controller_instance is None:
        with _controller_lock:
            if _controller_instance is None:
                _controller_instance = SimulationController()
    return _controller_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🎛 المتحكم الأعلى لطبقة المحاكاة الجبار - قيادة موحدة لكل عمليات المحاكاة")
    print("=" * 80 + "\n")
    
    controller = get_simulation_controller()
    
    # 1) تشغيل دفعة محاكاة
    print("🎛 تشغيل دفعة محاكاة...")
    batch_result = controller.run_simulation_batch(
        scenarios=["النمو المتسارع", "الاستقرار والتوازن"],
        runs=50,
        steps=10,
        name="اختبار_الأداء"
    )
    print(f"   معرف الدفعة: {batch_result.get('batch_id', 'N/A')}")
    print(f"   السيناريوهات: {batch_result.get('scenarios', [])}")
    
    # 2) جدولة محاكاة
    print("\n📅 جدولة محاكاة...")
    job_ids = controller.schedule_simulation(
        scenarios=["اختبار الأمان"],
        schedule_type="delayed",
        interval=5,
        runs=30,
        steps=8,
        priority=7
    )
    print(f"   تم جدولة {len(job_ids)} وظيفة")
    
    # 3) تحليل النتائج
    print("\n📊 تحليل النتائج...")
    analysis = controller.analyze_results()
    print(f"   الرؤى: {len(analysis.get('insights', []))}")
    print(f"   التوصيات: {len(analysis.get('recommendations', []))}")
    
    # 4) تحسين الدفعة التالية
    print("\n⚙️ تحسين الدفعة التالية...")
    optimized = controller.optimize_next_batch()
    print(f"   السيناريوهات المحسنة: {optimized.get('optimized_scenarios', [])}")
    print(f"   التوصيات المستخدمة: {optimized.get('recommendations_used', 0)}")
    
    # 5) حالة المتحكم
    print("\n📊 حالة المتحكم:")
    status = controller.get_controller_status()
    print(f"   الحالة: {status['status']}")
    print(f"   الدفعات النشطة: {status['active_batches']}")
    print(f"   الوظائف المجدولة: {status['scheduled_jobs']}")
    print(f"   صحة النظام: {status['system_health']:.1%}")
    print(f"   آخر إجراء: {status['last_action']}")
    
    # 6) إحصائيات
    print("\n📈 إحصائيات المتحكم:")
    stats = controller.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 7) سجل القرارات
    print("\n📜 سجل القرارات:")
    decisions = controller.get_decisions(5)
    for d in decisions:
        print(f"   {d['command']}: {d['reason'][:50]}... ({d['status']})")
    
    # 8) صحة النظام
    print("\n🏥 صحة النظام:")
    health = controller.get_system_health()
    print(f"   الصحة الإجمالية: {health:.1%}")
    
    # 9) السرد
    print(f"\n📖 السرد:\n{status['narrative']}")
    
    # 10) إيقاف طارئ (اختبار)
    print("\n🚨 اختبار الإيقاف الطارئ...")
    emergency = controller.emergency_stop()
    print(f"   تم إلغاء {emergency['cancelled_jobs']} وظيفة")
    
    # 11) إعادة تعيين
    print("\n🔄 إعادة تعيين المتحكم...")
    controller.reset_controller()
    
    # 12) اقتباس
    print(f"\n💭 {controller.get_controller_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ المتحكم الأعلى لطبقة المحاكاة الجبار جاهز - قيادة موحدة لكل عمليات المحاكاة")
    print("=" * 80)
