# backend/simulation/simulation_scheduler.py
# ⏱ مجدول تشغيلات المحاكاة الجبار - جدولة متقدمة، أولويات ديناميكية
# الإصدار: 3.0.0 - يدير آلاف التشغيلات المجدولة بذكاء

"""
مجدول تشغيلات المحاكاة للعقل السيادي.

الفلسفة:
- الجدولة الذكية توفر الوقت والموارد
- الأولويات تحدد الأهمية
- إعادة المحاولة الذكية تزيد الموثوقية
- الجدولة المتكررة تمكن المراقبة المستمرة
- التكامل مع المحاكاة يضمن التنفيذ السلس

هذه ليست مجرد جدولة. هذه هي إدارة وقت المحاكاة.
"""

import json
import time
import threading
import random
import secrets
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import heapq
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from ..memory.core import get_core, EventType
    from ..config import DATA_DIR
    from .simulation_core import get_simulation_core
except ImportError:
    from memory.core import get_core, EventType
    from config import DATA_DIR
    from .simulation_core import get_simulation_core

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات المجدول
# ============================================================

SCHEDULER_DIR = DATA_DIR / "simulation" / "scheduler"
SCHEDULER_DIR.mkdir(parents=True, exist_ok=True)
SCHEDULER_LOG = SCHEDULER_DIR / "scheduler_log.jsonl"
SCHEDULER_STATE_FILE = SCHEDULER_DIR / "scheduler_state.json"
SCHEDULER_JOBS_DIR = SCHEDULER_DIR / "jobs"

SCHEDULER_JOBS_DIR.mkdir(parents=True, exist_ok=True)

# حالات الوظائف
JOB_STATUS_PENDING = "pending"          # في انتظار الجدولة
JOB_STATUS_SCHEDULED = "scheduled"      # مجدولة
JOB_STATUS_RUNNING = "running"          # قيد التشغيل
JOB_STATUS_PAUSED = "paused"            # متوقفة مؤقتاً
JOB_STATUS_COMPLETED = "completed"      # مكتملة
JOB_STATUS_FAILED = "failed"            # فاشلة
JOB_STATUS_CANCELLED = "cancelled"      # ملغاة
JOB_STATUS_RETRYING = "retrying"        # قيد إعادة المحاولة

# أنواع الجدولة
SCHEDULE_TYPE_IMMEDIATE = "immediate"   # فوري
SCHEDULE_TYPE_ONCE = "once"             # لمرة واحدة في وقت محدد
SCHEDULE_TYPE_RECURRING = "recurring"   # متكرر
SCHEDULE_TYPE_CRON = "cron"             # كرون (مثل cron)
SCHEDULE_TYPE_DELAYED = "delayed"       # مؤجل

# أولويات الوظائف
PRIORITY_CRITICAL = 10
PRIORITY_HIGH = 8
PRIORITY_NORMAL = 5
PRIORITY_LOW = 3
PRIORITY_BACKGROUND = 1


def _now_iso() -> str:
    """إرجاع الوقت الحالي بصيغة ISO"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat() + "Z"


@dataclass
class ScheduledJob:
    """وظيفة مجدولة"""
    id: str
    name: str
    schedule_type: str
    cron_expression: Optional[str]  # لـ cron
    interval_seconds: Optional[int]  # لـ recurring
    scheduled_time: Optional[float]  # لـ once/delayed
    priority: int
    scenario: str
    parameters: Dict[str, Any]
    status: str
    created_at: float
    last_run: Optional[float]
    next_run: Optional[float]
    run_count: int
    success_count: int
    failure_count: int
    max_retries: int
    retry_delay: int
    tags: List[str]
    metadata: Dict[str, Any]


@dataclass
class JobExecution:
    """تنفيذ وظيفة"""
    id: str
    job_id: str
    started_at: float
    completed_at: Optional[float]
    status: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    retry_count: int


@dataclass
class SchedulerSnapshot:
    """لقطة المجدول"""
    timestamp: float
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    next_execution: Optional[float]
    queue_depth: int
    active_workers: int


# ============================================================
# مجدول تشغيلات المحاكاة الجبار
# ============================================================

class SimulationScheduler:
    """
    مجدول تشغيلات المحاكاة الجبار - جدولة متقدمة، أولويات ديناميكية.
    
    المبادئ:
    1. الجدولة الذكية توفر الوقت والموارد
    2. الأولويات تحدد الأهمية
    3. إعادة المحاولة الذكية تزيد الموثوقية
    4. الجدولة المتكررة تمكن المراقبة المستمرة
    5. التكامل مع المحاكاة يضمن التنفيذ السلس
    """
    
    def __init__(self):
        self.core = get_core()
        self.sim_core = get_simulation_core()
        
        # سجل الوظائف
        self.jobs: Dict[str, ScheduledJob] = {}
        self.executions: Dict[str, JobExecution] = {}
        
        # قائمة انتظار الأولويات (heap)
        self._priority_queue: List[Tuple[float, int, str]] = []  # (next_run, priority, job_id)
        self._queue_lock = threading.Lock()
        
        # التنفيذ المتوازي
        self.max_workers = 4
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.active_futures: Dict[str, Any] = {}
        
        # حالة المجدول
        self.scheduled_tasks = []
        self.last_schedule_result = {}
        self._index = self._load_index()
        
        # السياسات
        self.policies = {
            "max_tasks": 10,
            "task_priority_decay": 0.2,
            "noise_scale": 0.1,
            "auto_balance": True,
        }
        
        # خلفيات المجدول
        self._active = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        self._worker_monitor = threading.Thread(target=self._monitor_workers_loop, daemon=True)
        self._worker_monitor.start()
        
        self._persistence_thread = threading.Thread(target=self._persistence_loop, daemon=True)
        self._persistence_thread.start()
        
        # تحميل الحالة
        self._load_state()
        self._load_jobs()
        
        logger.warning("⏱ مجدول تشغيلات المحاكاة الجبار جاهز - يدير آلاف التشغيلات المجدولة")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لجدولة المحاكاة
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لجدولة المحاكاة.
        """
        # مسح قائمة المهام المجدولة
        self.scheduled_tasks = []
        self.last_schedule_result = {}
        
        # مسح الوظائف
        self.jobs.clear()
        self.executions.clear()
        
        # إعادة تعيين قائمة الانتظار
        with self._queue_lock:
            self._priority_queue.clear()
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # إعادة السياسات الافتراضية
        self.policies = {
            "max_tasks": 10,
            "task_priority_decay": 0.2,
            "noise_scale": 0.1,
            "auto_balance": True,
        }
        
        # تسجيل عملية إعادة التهيئة
        self.core.append_event(
            event_type="simulation::scheduler::reset",
            payload={
                "timestamp": _now_iso(),
                "status": "simulation_scheduler_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة مجدول المحاكاة اكتملت")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"jobs": [], "last_updated": time.time()}
    
    # ============================================================
    # إدارة الوظائف
    # ============================================================
    
    def schedule_job(self, name: str, scenario: str, 
                     schedule_type: str = SCHEDULE_TYPE_IMMEDIATE,
                     scheduled_time: float = None,
                     interval_seconds: int = None,
                     cron_expression: str = None,
                     priority: int = PRIORITY_NORMAL,
                     parameters: Dict[str, Any] = None,
                     max_retries: int = 3,
                     retry_delay: int = 60,
                     tags: List[str] = None) -> str:
        """
        جدولة وظيفة محاكاة جديدة.
        
        أنواع الجدولة:
        - فوري: تنفيذ فوراً
        - لمرة واحدة: في وقت محدد
        - متكرر: كل X ثانية
        - كرون: وفق تعبير cron
        - مؤجل: بعد X ثانية من الآن
        """
        job_id = f"sim_job_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        if parameters is None:
            parameters = {}
        if tags is None:
            tags = []
        
        # حساب وقت التشغيل التالي
        next_run = None
        if schedule_type == SCHEDULE_TYPE_IMMEDIATE:
            next_run = time.time()
        elif schedule_type == SCHEDULE_TYPE_ONCE and scheduled_time:
            next_run = scheduled_time
        elif schedule_type == SCHEDULE_TYPE_DELAYED and interval_seconds:
            next_run = time.time() + interval_seconds
        elif schedule_type == SCHEDULE_TYPE_RECURRING and interval_seconds:
            next_run = time.time()
        
        job = ScheduledJob(
            id=job_id,
            name=name,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            scheduled_time=scheduled_time,
            priority=priority,
            scenario=scenario,
            parameters=parameters,
            status=JOB_STATUS_SCHEDULED,
            created_at=time.time(),
            last_run=None,
            next_run=next_run,
            run_count=0,
            success_count=0,
            failure_count=0,
            max_retries=max_retries,
            retry_delay=retry_delay,
            tags=tags,
            metadata={}
        )
        
        self.jobs[job_id] = job
        
        # إضافة إلى قائمة الانتظار
        if next_run:
            with self._queue_lock:
                heapq.heappush(self._priority_queue, (next_run, -priority, job_id))
        
        # حفظ الوظيفة
        self._save_job(job)
        
        # تسجيل
        self.core.append_event(
            event_type="scheduler::job_scheduled",
            payload={
                "job_id": job_id[:16],
                "name": name,
                "schedule_type": schedule_type,
                "priority": priority
            }
        )
        
        logger.info(f"📅 وظيفة مجدولة: {name} (نوع: {schedule_type}, أولوية: {priority})")
        
        return job_id
    
    def cancel_job(self, job_id: str) -> bool:
        """
        إلغاء وظيفة مجدولة.
        """
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        job.status = JOB_STATUS_CANCELLED
        
        # إلغاء من قائمة الانتظار إذا كانت معلقة
        with self._queue_lock:
            self._priority_queue = [(t, p, jid) for t, p, jid in self._priority_queue if jid != job_id]
            heapq.heapify(self._priority_queue)
        
        self._save_job(job)
        
        logger.info(f"🗑️ إلغاء وظيفة: {job.name}")
        
        return True
    
    def pause_job(self, job_id: str) -> bool:
        """
        إيقاف وظيفة مؤقتاً.
        """
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        job.status = JOB_STATUS_PAUSED
        
        # إزالة من قائمة الانتظار
        with self._queue_lock:
            self._priority_queue = [(t, p, jid) for t, p, jid in self._priority_queue if jid != job_id]
            heapq.heapify(self._priority_queue)
        
        self._save_job(job)
        
        logger.info(f"⏸️ إيقاف وظيفة مؤقتاً: {job.name}")
        
        return True
    
    def resume_job(self, job_id: str) -> bool:
        """
        استئناف وظيفة متوقفة.
        """
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        job.status = JOB_STATUS_SCHEDULED
        
        # إعادة الحساب لوقت التشغيل التالي
        if job.schedule_type == SCHEDULE_TYPE_RECURRING and job.last_run:
            job.next_run = job.last_run + job.interval_seconds
        elif job.schedule_type == SCHEDULE_TYPE_IMMEDIATE:
            job.next_run = time.time()
        elif job.schedule_type == SCHEDULE_TYPE_DELAYED and job.interval_seconds:
            job.next_run = time.time() + job.interval_seconds
        
        # إضافة إلى قائمة الانتظار
        if job.next_run:
            with self._queue_lock:
                heapq.heappush(self._priority_queue, (job.next_run, -job.priority, job_id))
        
        self._save_job(job)
        
        logger.info(f"▶️ استئناف وظيفة: {job.name}")
        
        return True
    
    def list_jobs(self, status: str = None, tag: str = None) -> List[Dict]:
        """
        قائمة الوظائف.
        """
        jobs = self.jobs.values()
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        if tag:
            jobs = [j for j in jobs if tag in j.tags]
        
        return [
            {
                "id": j.id[:16],
                "name": j.name,
                "schedule_type": j.schedule_type,
                "priority": j.priority,
                "status": j.status,
                "run_count": j.run_count,
                "success_count": j.success_count,
                "failure_count": j.failure_count,
                "next_run": j.next_run
            }
            for j in jobs
        ]
    
    # ============================================================
    # حلقة الجدولة
    # ============================================================
    
    def _scheduler_loop(self):
        """حلقة الجدولة الرئيسية"""
        while self._active:
            try:
                self._process_queue()
                time.sleep(0.5)  # فحص كل نصف ثانية
            except Exception as e:
                logger.error(f"خطأ في حلقة الجدولة: {e}")
                time.sleep(1)
    
    def _process_queue(self):
        """معالجة قائمة الانتظار وتشغيل الوظائف المستحقة"""
        now = time.time()
        jobs_to_run = []
        
        with self._queue_lock:
            # جمع الوظائف المستحقة
            while self._priority_queue and self._priority_queue[0][0] <= now:
                next_run, neg_priority, job_id = heapq.heappop(self._priority_queue)
                job = self.jobs.get(job_id)
                if job and job.status == JOB_STATUS_SCHEDULED:
                    jobs_to_run.append(job)
        
        # تشغيل الوظائف مع احترام الحد الأقصى للموازاة
        running_count = len(self.active_futures)
        available_slots = self.max_workers - running_count
        
        for job in jobs_to_run[:available_slots]:
            self._execute_job(job)
    
    def _execute_job(self, job: ScheduledJob):
        """
        تنفيذ وظيفة مجدولة.
        """
        job.status = JOB_STATUS_RUNNING
        job.run_count += 1
        job.last_run = time.time()
        
        # تحديث وقت التشغيل التالي للوظائف المتكررة
        if job.schedule_type == SCHEDULE_TYPE_RECURRING and job.interval_seconds:
            job.next_run = time.time() + job.interval_seconds
            # إعادة الإضافة إلى قائمة الانتظار
            with self._queue_lock:
                heapq.heappush(self._priority_queue, (job.next_run, -job.priority, job.id))
        
        # إنشاء سجل تنفيذ
        execution_id = f"exec_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        execution = JobExecution(
            id=execution_id,
            job_id=job.id,
            started_at=time.time(),
            completed_at=None,
            status="running",
            result=None,
            error=None,
            retry_count=0
        )
        self.executions[execution_id] = execution
        
        # تنفيذ في خيط منفصل
        future = self.executor.submit(self._run_job, job, execution)
        self.active_futures[execution_id] = future
        
        logger.info(f"▶️ بدء تنفيذ وظيفة: {job.name}")
    
    def _run_job(self, job: ScheduledJob, execution: JobExecution):
        """
        تنفيذ وظيفة المحاكاة الفعلية.
        """
        try:
            # استدعاء نواة المحاكاة
            runs = job.parameters.get("runs", 100)
            steps = job.parameters.get("steps", 12)
            
            # تشغيل الدفعة
            batch_id = self.sim_core.run_custom_batch(
                name=f"job_{job.id[:16]}",
                scenarios=[job.scenario],
                runs_per_scenario=runs,
                steps=steps
            )
            
            execution.completed_at = time.time()
            execution.status = "completed"
            execution.result = {
                "batch_id": batch_id,
                "runs": runs,
                "steps": steps,
                "scenario": job.scenario
            }
            
            job.success_count += 1
            job.status = JOB_STATUS_SCHEDULED if job.schedule_type == SCHEDULE_TYPE_RECURRING else JOB_STATUS_COMPLETED
            
            # تسجيل النجاح
            self.core.append_event(
                event_type="scheduler::job_succeeded",
                payload={
                    "job_id": job.id[:16],
                    "name": job.name,
                    "duration": execution.completed_at - execution.started_at
                }
            )
            
            logger.info(f"✅ اكتملت وظيفة: {job.name} ({execution.completed_at - execution.started_at:.2f} ثانية)")
            
        except Exception as e:
            execution.completed_at = time.time()
            execution.status = "failed"
            execution.error = str(e)
            
            job.failure_count += 1
            
            # إعادة المحاولة
            if job.run_count <= job.max_retries:
                job.status = JOB_STATUS_RETRYING
                # جدولة إعادة المحاولة
                retry_time = time.time() + job.retry_delay
                with self._queue_lock:
                    heapq.heappush(self._priority_queue, (retry_time, -job.priority, job.id))
                
                logger.warning(f"🔄 إعادة محاولة وظيفة: {job.name} (محاولة {job.run_count}/{job.max_retries})")
            else:
                job.status = JOB_STATUS_FAILED
                logger.error(f"❌ فشلت وظيفة: {job.name} - {e}")
            
            self.core.append_event(
                event_type="scheduler::job_failed",
                payload={
                    "job_id": job.id[:16],
                    "name": job.name,
                    "error": str(e),
                    "retry_count": job.run_count
                }
            )
        
        finally:
            # حفظ التغييرات
            self._save_job(job)
            self._save_execution(execution)
            
            # إزالة من المستقبلات النشطة
            if execution.id in self.active_futures:
                del self.active_futures[execution.id]
    
    def _monitor_workers_loop(self):
        """مراقبة العمال وتنظيف المستقبلات المكتملة"""
        while self._active:
            try:
                # تنظيف المستقبلات المكتملة
                completed = []
                for exec_id, future in self.active_futures.items():
                    if future.done():
                        completed.append(exec_id)
                
                for exec_id in completed:
                    if exec_id in self.active_futures:
                        del self.active_futures[exec_id]
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"خطأ في مراقبة العمال: {e}")
                time.sleep(1)
    
    # ============================================================
    # استمرارية البيانات
    # ============================================================
    
    def _save_job(self, job: ScheduledJob):
        """حفظ وظيفة"""
        try:
            job_file = SCHEDULER_JOBS_DIR / f"{job.id}.json"
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job.__dict__, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الوظيفة: {e}")
    
    def _save_execution(self, execution: JobExecution):
        """حفظ تنفيذ"""
        try:
            exec_file = SCHEDULER_JOBS_DIR / f"exec_{execution.id}.json"
            with open(exec_file, 'w', encoding='utf-8') as f:
                json.dump(execution.__dict__, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ التنفيذ: {e}")
    
    def _load_jobs(self):
        """تحميل الوظائف"""
        try:
            for job_file in SCHEDULER_JOBS_DIR.glob("sim_job_*.json"):
                with open(job_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    job = ScheduledJob(**data)
                    self.jobs[job.id] = job
                    
                    # إعادة بناء قائمة الانتظار للوظائف النشطة
                    if job.status == JOB_STATUS_SCHEDULED and job.next_run and job.next_run > time.time():
                        with self._queue_lock:
                            heapq.heappush(self._priority_queue, (job.next_run, -job.priority, job.id))
            
            logger.info(f"📂 تم تحميل {len(self.jobs)} وظيفة")
        except Exception as e:
            logger.error(f"خطأ في تحميل الوظائف: {e}")
    
    def _save_state(self):
        """حفظ حالة المجدول"""
        try:
            state = {
                "max_workers": self.max_workers,
                "total_jobs": len(self.jobs),
                "total_executions": len(self.executions),
                "queue_size": len(self._priority_queue),
                "saved_at": time.time()
            }
            # M1: كتابة ذرية عبر ملف مؤقت لتجنب قراءة ملف نصف مكتوب
            tmp = SCHEDULER_STATE_FILE.with_suffix('.json.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            tmp.replace(SCHEDULER_STATE_FILE)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة المجدول: {e}")
    
    def _load_state(self):
        """تحميل حالة المجدول"""
        try:
            if SCHEDULER_STATE_FILE.exists():
                with open(SCHEDULER_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.max_workers = state.get("max_workers", 4)
                    self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
                logger.info("📂 تم تحميل حالة المجدول")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المجدول: {e}")
    
    def _persistence_loop(self):
        """حفظ دوري للحالة"""
        while self._active:
            try:
                self._save_state()
                time.sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في حفظ الحالة الدوري: {e}")
                time.sleep(300)
    
    # ============================================================
    # دورة المجدول
    # ============================================================
    
    def scheduler_cycle(self) -> SchedulerSnapshot:
        """
        دورة مجدول كاملة.
        """
        pending = len([j for j in self.jobs.values() if j.status == JOB_STATUS_SCHEDULED])
        running = len(self.active_futures)
        completed = len([j for j in self.jobs.values() if j.status == JOB_STATUS_COMPLETED])
        failed = len([j for j in self.jobs.values() if j.status == JOB_STATUS_FAILED])
        
        # أقرب وقت تنفيذ تالي
        next_exec = None
        with self._queue_lock:
            if self._priority_queue:
                next_exec = self._priority_queue[0][0]
        
        return SchedulerSnapshot(
            timestamp=time.time(),
            total_jobs=len(self.jobs),
            pending_jobs=pending,
            running_jobs=running,
            completed_jobs=completed,
            failed_jobs=failed,
            next_execution=next_exec,
            queue_depth=len(self._priority_queue),
            active_workers=len(self.active_futures)
        )
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمجدول"""
        snapshot = self.scheduler_cycle()
        
        return {
            "total_jobs": snapshot.total_jobs,
            "pending_jobs": snapshot.pending_jobs,
            "running_jobs": snapshot.running_jobs,
            "completed_jobs": snapshot.completed_jobs,
            "failed_jobs": snapshot.failed_jobs,
            "queue_depth": snapshot.queue_depth,
            "active_workers": snapshot.active_workers,
            "next_execution": snapshot.next_execution,
            "timestamp": snapshot.timestamp
        }
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """تفاصيل وظيفة"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return {
            "id": job.id[:16],
            "name": job.name,
            "schedule_type": job.schedule_type,
            "priority": job.priority,
            "status": job.status,
            "run_count": job.run_count,
            "success_count": job.success_count,
            "failure_count": job.failure_count,
            "last_run": job.last_run,
            "next_run": job.next_run,
            "scenario": job.scenario,
            "parameters": job.parameters,
            "tags": job.tags
        }
    
    def get_job_executions(self, job_id: str, limit: int = 20) -> List[Dict]:
        """سجل تنفيذات وظيفة"""
        executions = [e for e in self.executions.values() if e.job_id == job_id]
        executions.sort(key=lambda x: x.started_at, reverse=True)
        
        return [
            {
                "id": e.id[:16],
                "started_at": e.started_at,
                "completed_at": e.completed_at,
                "duration": e.completed_at - e.started_at if e.completed_at else None,
                "status": e.status,
                "error": e.error[:100] if e.error else None
            }
            for e in executions[:limit]
        ]
    
    def set_max_workers(self, workers: int):
        """تعيين الحد الأقصى للعمال المتوازيين"""
        self.max_workers = max(1, min(16, workers))
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        logger.info(f"⚙️ الحد الأقصى للعمال: {self.max_workers}")
    
    def get_scheduler_quote(self) -> str:
        """اقتباس عن الجدولة"""
        quotes = [
            "الجدولة الذكية توفر الوقت والموارد.",
            "الأولويات تحدد الأهمية.",
            "إعادة المحاولة الذكية تزيد الموثوقية.",
            "الجداول المتكررة تمكن المراقبة المستمرة.",
            "الوقت أثمن مورد، أدارته بحكمة.",
            "المجدول الجيد يرى المستقبل.",
            "التنفيذ المتوازي يضاعف الإنتاجية."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف المجدول"""
        self._active = False
        self.executor.shutdown(wait=False)
        self._save_state()
        logger.info("🛑 إيقاف مجدول تشغيلات المحاكاة")


# ============================================================
# الـ Singleton
# ============================================================

_scheduler_instance: Optional[SimulationScheduler] = None
_scheduler_lock = threading.Lock()


def get_simulation_scheduler() -> SimulationScheduler:
    """الحصول على النسخة الوحيدة من مجدول تشغيلات المحاكاة"""
    global _scheduler_instance
    if _scheduler_instance is None:
        with _scheduler_lock:
            if _scheduler_instance is None:
                _scheduler_instance = SimulationScheduler()
    return _scheduler_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("⏱ مجدول تشغيلات المحاكاة الجبار - يدير آلاف التشغيلات المجدولة")
    print("=" * 80 + "\n")
    
    scheduler = get_simulation_scheduler()
    
    # 1) جدولة وظائف
    print("📅 جدولة وظائف...")
    
    job1 = scheduler.schedule_job(
        name="اختبار النمو الفوري",
        scenario="النمو المتسارع",
        schedule_type=SCHEDULE_TYPE_IMMEDIATE,
        priority=PRIORITY_HIGH,
        parameters={"runs": 50, "steps": 10}
    )
    print(f"   وظيفة فورية: {job1[:16]}...")
    
    job2 = scheduler.schedule_job(
        name="مراقبة الاستقرار المتكررة",
        scenario="الاستقرار والتوازن",
        schedule_type=SCHEDULE_TYPE_RECURRING,
        interval_seconds=30,
        priority=PRIORITY_NORMAL,
        parameters={"runs": 30, "steps": 8},
        tags=["monitoring", "stability"]
    )
    print(f"   وظيفة متكررة (كل 30 ثانية): {job2[:16]}...")
    
    job3 = scheduler.schedule_job(
        name="اختبار الأمان المؤجل",
        scenario="اختراق أمني محتمل",
        schedule_type=SCHEDULE_TYPE_DELAYED,
        interval_seconds=10,
        priority=PRIORITY_CRITICAL,
        parameters={"runs": 100, "steps": 15}
    )
    print(f"   وظيفة مؤجلة (10 ثوانٍ): {job3[:16]}...")
    
    # 2) قائمة الوظائف
    print("\n📋 قائمة الوظائف:")
    jobs = scheduler.list_jobs()
    for j in jobs:
        print(f"   {j['name']}: {j['status']} (أولوية {j['priority']})")
    
    # 3) حالة المجدول
    print("\n📊 حالة المجدول:")
    status = scheduler.get_scheduler_status()
    print(f"   إجمالي الوظائف: {status['total_jobs']}")
    print(f"   وظائف معلقة: {status['pending_jobs']}")
    print(f"   وظائف قيد التشغيل: {status['running_jobs']}")
    print(f"   الوظائف الناجحة: {status['completed_jobs']}")
    print(f"   الوظائف الفاشلة: {status['failed_jobs']}")
    print(f"   عمق قائمة الانتظار: {status['queue_depth']}")
    print(f"   العمال النشطون: {status['active_workers']}")
    
    # 4) تفاصيل وظيفة
    print("\n🔍 تفاصيل وظيفة:")
    details = scheduler.get_job_details(job2)
    if details:
        print(f"   الاسم: {details['name']}")
        print(f"   النوع: {details['schedule_type']}")
        print(f"   الحالة: {details['status']}")
        print(f"   مرات التشغيل: {details['run_count']}")
    
    # 5) انتظار قليلاً لرؤية التنفيذ
    print("\n⏳ انتظار التنفيذ (5 ثوانٍ)...")
    time.sleep(5)
    
    # 6) إيقاف وظيفة مؤقتاً
    print("\n⏸️ إيقاف وظيفة مؤقتاً...")
    scheduler.pause_job(job2)
    
    # 7) تحديث الحالة
    print("\n📊 تحديث الحالة:")
    status = scheduler.get_scheduler_status()
    print(f"   وظائف معلقة: {status['pending_jobs']}")
    print(f"   وظائف قيد التشغيل: {status['running_jobs']}")
    
    # 8) استئناف وظيفة
    print("\n▶️ استئناف وظيفة...")
    scheduler.resume_job(job2)
    
    # 9) إلغاء وظيفة
    print("\n🗑️ إلغاء وظيفة...")
    scheduler.cancel_job(job3)
    
    # 10) حالة نهائية
    print("\n📊 الحالة النهائية للمجدول:")
    status = scheduler.get_scheduler_status()
    print(f"   إجمالي الوظائف: {status['total_jobs']}")
    print(f"   وظائف معلقة: {status['pending_jobs']}")
    print(f"   وظائف قيد التشغيل: {status['running_jobs']}")
    print(f"   الوظائف الناجحة: {status['completed_jobs']}")
    
    # 11) اقتباس
    print(f"\n💭 {scheduler.get_scheduler_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ مجدول تشغيلات المحاكاة الجبار جاهز - يدير آلاف التشغيلات المجدولة")
    print("=" * 80)
