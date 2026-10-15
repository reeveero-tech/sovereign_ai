# backend/orchestrator.py
# 👑 Sovereign Orchestrator - العقل المنسق الأعلى
# الإصدار: 4.0.0 - التيتانيوم، البلاتين، الألماس

"""
Sovereign Orchestrator - العقل المنسق الأعلى
---------------------------------------------

هذا الملف هو قلب النظام النابض، الحلقة العصبية العليا التي تربط كل شيء.

الفلسفة:
- Orchestrator لا يعرف التفاصيل الداخلية للطبقات، بل يتعامل معها عبر واجهات ذكية
- يتحمل الفشل ولا ينهار أبداً
- خفيف كالتيتانيوم، قوي كالبلاتين، حاد كالألماس
- يتكيف مع أي بنية، ولا يفترض شيئاً

المبادئ:
1. كل طبقة قد تكون موجودة أو لا - Orchestrator يتكيف
2. كل دالة قد تكون موجودة أو لا - Orchestrator يتحقق بذكاء
3. كل خطأ قد يحدث - Orchestrator يتعامل معه برشاقة
4. Orchestrator لا يموت أبداً - دائماً هناك مسار بديل
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union
from enum import Enum
from collections import deque
import traceback

# TOLERATED: optional modules unavailable — degraded mode, not crash (R-680d)
try:
    from memory.core import get_core
    from memory.dynamic import get_dynamic_memory
    from memory.store import get_store
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from memory.biological.archetypes import get_archetypes
    from consciousness.field import get_consciousness_field
    from consciousness.identity_core import get_identity_core
    from consciousness.self_model import get_self_model
    from consciousness.awareness import get_awareness_engine
    from consciousness.attention_engine import get_attention_engine
    from consciousness.introspection import get_introspection_engine
    from predictive.predictive_engine import get_predictive_engine
    from predictive.predictive_controller import get_predictive_controller
    from predictive.predictive_risk_manager import get_predictive_risk_manager
    from simulation.simulation_controller import get_simulation_controller
    from simulation.simulation_analyzer import get_simulation_analyzer
    from sovereign.will import get_sovereign_will
    from sovereign.alignment import get_sovereign_alignment
    from sovereign.directives import get_sovereign_directives
    from sovereign.controller import get_sovereign_controller
    from quantum.quantum_controller import get_quantum_controller
except ImportError:
    pass

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت والتعدادات
# ============================================================

class OrchestratorMode(str, Enum):
    """أوضاع تشغيل الـ Orchestrator"""
    NORMAL = "normal"           # عادي
    SAFE = "safe"               # آمن (معالجة أقل)
    RECOVERY = "recovery"       # استرداد (محاولة إصلاح)
    EMERGENCY = "emergency"     # طوارئ (حماية فقط)
    DEBUG = "debug"             # تصحيح (تسجيل مفصل)
    SILENT = "silent"           # صامت (لا تسجيل)


class CyclePriority(int, Enum):
    """أولويات دورة المعالجة"""
    CRITICAL = 0    # حرج
    HIGH = 1        # عالي
    NORMAL = 2      # عادي
    LOW = 3         # منخفض
    BACKGROUND = 4  # خلفية


@dataclass
class OrchestratorConfig:
    """إعدادات Orchestrator المتقدمة"""
    loop_interval: float = 0.0
    enable_logging: bool = True
    max_history: int = 10000
    mode: str = OrchestratorMode.NORMAL.value
    default_priority: int = CyclePriority.NORMAL.value
    error_threshold: int = 5
    recovery_attempts: int = 3
    timeout_seconds: float = 30.0
    enable_parallel_processing: bool = True
    max_parallel_workers: int = 4
    enable_caching: bool = True
    cache_ttl: int = 300
    enable_sandbox_mode: bool = False


@dataclass
class CycleResult:
    """نتيجة دورة معالجة"""
    cycle_id: str
    timestamp: float
    success: bool
    mode: str
    duration: float
    perception: Dict[str, Any]
    future_analysis: Dict[str, Any]
    sovereign_eval: Dict[str, Any]
    decision: Dict[str, Any]
    execution_result: Dict[str, Any]
    memory_update: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


@dataclass
class ComponentHealth:
    """صحة مكون"""
    name: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    last_success: float
    last_error: Optional[str]
    error_count: int
    response_time: float


# ============================================================
# Sovereign Orchestrator - العقل المنسق الأعلى
# ============================================================

class SovereignOrchestrator:
    """
    Sovereign Orchestrator - العقل المنسق الأعلى.
    
    المبادئ:
    1. لا ينهار أبداً - كل خطأ يُلتقط ويتعامل معه
    2. يتكيف مع أي بنية - لا يفترض وجود أي شيء
    3. سريع كالبرق - معالجة متوازية وتخزين مؤقت
    4. شفاف - تسجيل كامل وتاريخ
    5. آمن - وضع الحماية (sandbox) للتجارب
    """
    
    def __init__(
        self,
        # المكونات الأساسية (يتم حقنها أو تحميلها تلقائياً)
        consciousness: Any = None,
        memory_core: Any = None,
        memory_dynamic: Any = None,
        memory_store: Any = None,
        biological: Any = None,
        predictive: Any = None,
        simulation: Any = None,
        sovereign: Any = None,
        quantum: Any = None,
        nexus: Any = None,
        # إعدادات
        config: Optional[OrchestratorConfig] = None,
        # تسجيل
        external_logger: Optional[Any] = None,
    ):
        # ✅ التعديل: تهيئة المتغيرات أولاً (قبل تحميل المكونات)
        self._component_health: Dict[str, ComponentHealth] = {}
        self._session_id: str = hashlib.sha256(f"{time.time()}{secrets.token_hex(16)}".encode()).hexdigest()[:16]
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self._cache_lock = threading.RLock()
        
        # العدادات والإحصائيات
        self._stats = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "avg_cycle_duration": 0.0,
            "last_cycle_id": None,
            "last_error": None,
            "started_at": time.time(),
            "mode_changes": []
        }
        
        # الإعدادات
        self.config = config or OrchestratorConfig()
        self.external_logger = external_logger
        
        # الحالة الداخلية
        self._history: deque = deque(maxlen=self.config.max_history)
        
        # الإعدادات المتقدمة
        self._recovery_mode = False
        self._recovery_attempts_left = self.config.recovery_attempts
        self._error_counter = 0
        
        # تهيئة المكونات (تلقائياً أو محقونة) - الآن self._component_health موجود
        self.consciousness = consciousness or self._load_consciousness()
        self.memory_core = memory_core or self._load_memory_core()
        self.memory_dynamic = memory_dynamic or self._load_memory_dynamic()
        self.memory_store = memory_store or self._load_memory_store()
        self.biological = biological or self._load_biological()
        self.predictive = predictive or self._load_predictive()
        self.simulation = simulation or self._load_simulation()
        self.sovereign = sovereign or self._load_sovereign()
        self.quantum = quantum or self._load_quantum()
        self.nexus = nexus or self._load_nexus()
        
        # خلفيات التشغيل
        self._active = True
        self._background_processor: Optional[threading.Thread] = None
        self._start_background_processor()
        
        # تسجيل بدء التشغيل
        self._log("info", "🚀 Sovereign Orchestrator بدأ التشغيل", {
            "session_id": self._session_id,
            "mode": self.config.mode,
            "components": self._get_component_status()
        })
        
        logger.warning(f"👑 Sovereign Orchestrator جاهز - العقل المنسق الأعلى (session: {self._session_id})")
    
    # ============================================================
    # تحميل المكونات التلقائي
    # ============================================================
    
    def _load_consciousness(self) -> Dict[str, Any]:
        """تحميل مكونات الوعي"""
        components = {}
        try:
            from consciousness.field import get_consciousness_field
            components["field"] = get_consciousness_field()
            self._update_component_health("consciousness_field", True)
        except Exception as e:
            self._update_component_health("consciousness_field", False, str(e))
        
        try:
            from consciousness.identity_core import get_identity_core
            components["identity"] = get_identity_core()
            self._update_component_health("consciousness_identity", True)
        except Exception as e:
            self._update_component_health("consciousness_identity", False, str(e))
        
        try:
            from consciousness.self_model import get_self_model
            components["self_model"] = get_self_model()
            self._update_component_health("consciousness_self_model", True)
        except Exception as e:
            self._update_component_health("consciousness_self_model", False, str(e))
        
        try:
            from consciousness.awareness import get_awareness_engine
            components["awareness"] = get_awareness_engine()
            self._update_component_health("consciousness_awareness", True)
        except Exception as e:
            self._update_component_health("consciousness_awareness", False, str(e))
        
        try:
            from consciousness.attention_engine import get_attention_engine
            components["attention"] = get_attention_engine()
            self._update_component_health("consciousness_attention", True)
        except Exception as e:
            self._update_component_health("consciousness_attention", False, str(e))
        
        try:
            from consciousness.introspection import get_introspection_engine
            components["introspection"] = get_introspection_engine()
            self._update_component_health("consciousness_introspection", True)
        except Exception as e:
            self._update_component_health("consciousness_introspection", False, str(e))
        
        return components
    
    def _load_memory_core(self) -> Optional[Any]:
        """تحميل نواة الذاكرة"""
        try:
            from memory.core import get_core
            core = get_core()
            self._update_component_health("memory_core", True)
            return core
        except Exception as e:
            self._update_component_health("memory_core", False, str(e))
            # R-682 [open item 2]: warn on silent failure
            logger.warning(f"R-682: memory_core init failed — returning None. exc={e}")
            return None
    
    def _load_memory_dynamic(self) -> Optional[Any]:
        """تحميل الذاكرة الديناميكية"""
        try:
            from memory.dynamic import get_dynamic_memory
            dynamic = get_dynamic_memory()
            self._update_component_health("memory_dynamic", True)
            return dynamic
        except Exception as e:
            self._update_component_health("memory_dynamic", False, str(e))
            # R-682 [open item 2]: warn on silent failure
            logger.warning(f"R-682: memory_dynamic init failed — returning None. exc={e}")
            return None
    
    def _load_memory_store(self) -> Optional[Any]:
        """تحميل تخزين الذاكرة"""
        try:
            from memory.store import get_store
            store = get_store()
            self._update_component_health("memory_store", True)
            return store
        except Exception as e:
            self._update_component_health("memory_store", False, str(e))
            # R-682 [open item 2]: warn on silent failure
            logger.warning(f"R-682: memory_store init failed — returning None. exc={e}")
            return None
    
    def _load_biological(self) -> Dict[str, Any]:
        """تحميل المكونات البيولوجية"""
        components = {}
        try:
            from memory.biological.instincts import get_instincts
            components["instincts"] = get_instincts()
            self._update_component_health("biological_instincts", True)
        except Exception as e:
            self._update_component_health("biological_instincts", False, str(e))
        
        try:
            from memory.biological.drives import get_drives
            components["drives"] = get_drives()
            self._update_component_health("biological_drives", True)
        except Exception as e:
            self._update_component_health("biological_drives", False, str(e))
        
        try:
            from memory.biological.archetypes import get_archetypes
            components["archetypes"] = get_archetypes()
            self._update_component_health("biological_archetypes", True)
        except Exception as e:
            self._update_component_health("biological_archetypes", False, str(e))
        
        return components
    
    def _load_predictive(self) -> Dict[str, Any]:
        """تحميل المكونات التنبؤية"""
        components = {}
        try:
            from predictive.predictive_engine import get_predictive_engine
            components["engine"] = get_predictive_engine()
            self._update_component_health("predictive_engine", True)
        except Exception as e:
            self._update_component_health("predictive_engine", False, str(e))
        
        try:
            from predictive.predictive_controller import get_predictive_controller
            components["controller"] = get_predictive_controller()
            self._update_component_health("predictive_controller", True)
        except Exception as e:
            self._update_component_health("predictive_controller", False, str(e))
        
        try:
            from predictive.predictive_risk_manager import get_predictive_risk_manager
            components["risk_manager"] = get_predictive_risk_manager()
            self._update_component_health("predictive_risk_manager", True)
        except Exception as e:
            self._update_component_health("predictive_risk_manager", False, str(e))
        
        return components
    
    def _load_simulation(self) -> Dict[str, Any]:
        """تحميل مكونات المحاكاة"""
        components = {}
        try:
            from simulation.simulation_controller import get_simulation_controller
            components["controller"] = get_simulation_controller()
            self._update_component_health("simulation_controller", True)
        except Exception as e:
            self._update_component_health("simulation_controller", False, str(e))
        
        try:
            from simulation.simulation_analyzer import get_simulation_analyzer
            components["analyzer"] = get_simulation_analyzer()
            self._update_component_health("simulation_analyzer", True)
        except Exception as e:
            self._update_component_health("simulation_analyzer", False, str(e))
        
        return components
    
    def _load_sovereign(self) -> Dict[str, Any]:
        """تحميل مكونات السيادة"""
        components = {}
        try:
            from sovereign.will import get_sovereign_will
            components["will"] = get_sovereign_will()
            self._update_component_health("sovereign_will", True)
        except Exception as e:
            self._update_component_health("sovereign_will", False, str(e))
        
        try:
            from sovereign.alignment import get_sovereign_alignment
            components["alignment"] = get_sovereign_alignment()
            self._update_component_health("sovereign_alignment", True)
        except Exception as e:
            self._update_component_health("sovereign_alignment", False, str(e))
        
        try:
            from sovereign.directives import get_sovereign_directives
            components["directives"] = get_sovereign_directives()
            self._update_component_health("sovereign_directives", True)
        except Exception as e:
            self._update_component_health("sovereign_directives", False, str(e))
        
        try:
            from sovereign.controller import get_sovereign_controller
            components["controller"] = get_sovereign_controller()
            self._update_component_health("sovereign_controller", True)
        except Exception as e:
            self._update_component_health("sovereign_controller", False, str(e))
        
        return components
    
    def _load_quantum(self) -> Optional[Any]:
        """تحميل المكونات الكمومية"""
        try:
            from quantum.quantum_controller import get_quantum_controller
            controller = get_quantum_controller()
            self._update_component_health("quantum_controller", True)
            return controller
        except Exception as e:
            self._update_component_health("quantum_controller", False, str(e))
            # R-682 [open item 2]: warn on silent failure
            logger.warning(f"R-682: quantum_controller init failed — returning None. exc={e}")
            return None
    
    def _load_nexus(self) -> Optional[Any]:
        """تحميل منصة NexusCore (مدمجة في R-301)"""
        try:
            import os, sys
            # nexus/ في جذر المستودع — أضف الجذر إلى مسار الاستيراد
            _backend_dir = os.path.dirname(os.path.abspath(__file__))
            _repo_root = os.path.dirname(_backend_dir)
            if _repo_root not in sys.path:
                sys.path.insert(0, _repo_root)
            from nexus.main import initialize_nexus
            engine = initialize_nexus()
            self._update_component_health("nexus_engine", True)
            return engine
        except Exception as e:
            self._update_component_health("nexus_engine", False, str(e))
            # R-682 [open item 2]: warn on silent failure
            logger.warning(f"R-682: nexus_engine init failed — returning None. exc={e}")
            return None
    
    def _update_component_health(self, name: str, success: bool, error: str = None):
        """تحديث صحة المكون"""
        now = time.time()
        if name not in self._component_health:
            self._component_health[name] = ComponentHealth(
                name=name,
                status="unknown",
                last_success=now if success else 0,
                last_error=error,
                error_count=0,
                response_time=0
            )
        
        health = self._component_health[name]
        if success:
            health.status = "healthy"
            health.last_success = now
            health.error_count = max(0, health.error_count - 1)
        else:
            health.error_count += 1
            health.last_error = error
            if health.error_count >= self.config.error_threshold:
                health.status = "unhealthy"
            elif health.error_count >= self.config.error_threshold // 2:
                health.status = "degraded"
    
    def _get_component_status(self) -> Dict[str, str]:
        """الحصول على حالة جميع المكونات"""
        return {name: h.status for name, h in self._component_health.items()}
    
    # ============================================================
    # التخزين المؤقت الذكي (Caching)
    # ============================================================
    
    def _cache_get(self, key: str) -> Optional[Any]:
        """استرجاع من الكاش"""
        if not self.config.enable_caching:
            return None
        
        with self._cache_lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                else:
                    del self._cache[key]
        return None
    
    def _cache_set(self, key: str, value: Any, ttl: int = None):
        """تخزين في الكاش"""
        if not self.config.enable_caching:
            return
        
        ttl = ttl or self.config.cache_ttl
        with self._cache_lock:
            self._cache[key] = (value, time.time() + ttl)
    
    def _cache_clear(self):
        """مسح الكاش"""
        with self._cache_lock:
            self._cache.clear()
    
    # ============================================================
    # التسجيل الذكي
    # ============================================================
    
    def _log(self, level: str, message: str, payload: Dict[str, Any] = None):
        """تسجيل الأحداث بشكل ذكي"""
        if not self.config.enable_logging and level != "error":
            return
        
        entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "payload": payload or {},
            "session_id": self._session_id,
            "mode": self.config.mode
        }
        
        self._history.append(entry)
        
        # تسجيل في logger
        if level == "error":
            logger.error(f"[Orchestrator] {message}")
        elif level == "warning":
            logger.warning(f"[Orchestrator] {message}")
        elif level == "debug" and self.config.mode == OrchestratorMode.DEBUG.value:
            logger.debug(f"[Orchestrator] {message}")
        else:
            logger.info(f"[Orchestrator] {message}")
        
        # تسجيل في core إن وجد
        if self.memory_core and hasattr(self.memory_core, "append_event"):
            try:
                self.memory_core.append_event("orchestrator::log", entry)
            # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
            except:
                pass
    
    # ============================================================
    # معالجة الخلفية
    # ============================================================
    
    def _start_background_processor(self):
        """بدء معالج الخلفية"""
        self._background_processor = threading.Thread(target=self._background_loop, daemon=True)
        self._background_processor.start()
    
    def _background_loop(self):
        """حلقة المعالجة الخلفية"""
        while self._active:
            try:
                # تنظيف الكاش القديم
                if self.config.enable_caching:
                    with self._cache_lock:
                        now = time.time()
                        expired = [k for k, (_, exp) in self._cache.items() if exp < now]
                        for k in expired:
                            del self._cache[k]
                
                # مراقبة صحة المكونات وإعادة المحاولة
                if self._recovery_mode:
                    self._attempt_recovery()
                
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في المعالجة الخلفية: {e}")
                time.sleep(60)
    
    def _attempt_recovery(self):
        """محاولة استرداد المكونات المتعثرة"""
        if self._recovery_attempts_left <= 0:
            self._log("error", "استنفاد محاولات الاسترداد، الدخول في وضع الطوارئ", {})
            self.config.mode = OrchestratorMode.EMERGENCY.value
            self._recovery_mode = False
            return
        
        self._recovery_attempts_left -= 1
        self._log("warning", f"محاولة استرداد {self.config.recovery_attempts - self._recovery_attempts_left}", {})
        
        # إعادة تعيين المكونات المتعثرة
        for name, health in self._component_health.items():
            if health.status == "unhealthy":
                self._log("info", f"محاولة إعادة تعيين المكون {name}", {})
                # محاولة استدعاء reset إن وجد
                # (يتم ذلك في الدورة الرئيسية)
    
    # ============================================================
    # استدعاء آمن للدوال
    # ============================================================
    
    def _safe_call(self, obj: Any, method_name: str, *args, default: Any = None, **kwargs) -> Any:
        """
        استدعاء آمن لدالة - لا ينهار أبداً.
        
        1. يتحقق من وجود الكائن والدالة
        2. يلتقط أي استثناء
        3. يسجل الخطأ
        4. يعيد قيمة افتراضية
        """
        if obj is None:
            return default
        
        if not hasattr(obj, method_name):
            return default
        
        try:
            result = getattr(obj, method_name)(*args, **kwargs)
            return result
        except Exception as e:
            self._log("warning", f"فشل استدعاء {method_name}", {"error": str(e)})
            return default
    
    # ============================================================
    # دورة المعالجة الرئيسية
    # ============================================================
    
    def run_cycle(self, input_data: Dict[str, Any] = None, 
                  priority: int = CyclePriority.NORMAL.value) -> CycleResult:
        """
        تنفيذ دورة معالجة سيادية كاملة.
        
        المراحل:
        1. الإدراك (Perception) - جمع المعلومات من الوعي والذاكرة
        2. التحليل (Analysis) - تحليل المستقبل والتنبؤات
        3. التقييم (Evaluation) - تقييم السيادة والإرادة
        4. القرار (Decision) - اتخاذ القرار
        5. التنفيذ (Execution) - تنفيذ القرار
        6. التحديث (Update) - تحديث الذاكرة
        """
        cycle_id = hashlib.md5(f"{time.time()}{secrets.token_hex(8)}".encode()).hexdigest()[:16]
        start_time = time.time()
        errors = []
        warnings = []
        
        self._stats["total_cycles"] += 1
        self._stats["last_cycle_id"] = cycle_id
        
        self._log("info", f"🔄 بدء دورة المعالجة {cycle_id}", {"priority": priority})
        
        try:
            # ====================================================
            # 1) الإدراك (Perception)
            # ====================================================
            perception = self._gather_perception(input_data or {}, cycle_id)
            
            # ====================================================
            # 2) تحليل المستقبل (Future Analysis)
            # ====================================================
            future_analysis = self._analyze_future(perception, cycle_id)
            
            # ====================================================
            # 3) تقييم السيادة (Sovereign Evaluation)
            # ====================================================
            sovereign_eval = self._evaluate_sovereign(perception, future_analysis, cycle_id)
            
            # ====================================================
            # 4) اتخاذ القرار (Decision Making)
            # ====================================================
            decision = self._make_decision(sovereign_eval, perception, future_analysis, cycle_id)
            
            # ====================================================
            # 5) التنفيذ (Execution)
            # ====================================================
            execution_result = self._execute_decision(decision, cycle_id)
            
            # ====================================================
            # 6) تحديث الذاكرة (Memory Update)
            # ====================================================
            memory_update = self._update_memory(perception, decision, execution_result, cycle_id)
            
            duration = time.time() - start_time
            self._stats["successful_cycles"] += 1
            self._error_counter = 0
            
            # تحديث متوسط المدة
            self._stats["avg_cycle_duration"] = (
                self._stats["avg_cycle_duration"] * (self._stats["successful_cycles"] - 1) + duration
            ) / self._stats["successful_cycles"]
            
            result = CycleResult(
                cycle_id=cycle_id,
                timestamp=start_time,
                success=True,
                mode=self.config.mode,
                duration=duration,
                perception=perception,
                future_analysis=future_analysis,
                sovereign_eval=sovereign_eval,
                decision=decision,
                execution_result=execution_result,
                memory_update=memory_update,
                errors=errors,
                warnings=warnings
            )
            
            self._log("info", f"✅ اكتملت دورة {cycle_id}", {"duration": duration})
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self._stats["failed_cycles"] += 1
            self._error_counter += 1
            self._stats["last_error"] = str(e)
            errors.append(str(e))
            errors.append(traceback.format_exc())
            
            # تفعيل وضع الاسترداد إذا تكررت الأخطاء
            if self._error_counter >= self.config.error_threshold:
                self._recovery_mode = True
                self.config.mode = OrchestratorMode.RECOVERY.value
                self._log("warning", "تفعيل وضع الاسترداد بسبب تكرار الأخطاء", {"error_count": self._error_counter})
            
            self._log("error", f"❌ فشلت دورة {cycle_id}", {"error": str(e), "duration": duration})
            
            return CycleResult(
                cycle_id=cycle_id,
                timestamp=start_time,
                success=False,
                mode=self.config.mode,
                duration=duration,
                perception={},
                future_analysis={},
                sovereign_eval={},
                decision={},
                execution_result={},
                memory_update={},
                errors=errors,
                warnings=warnings
            )
    
    # ============================================================
    # مراحل الدورة التفصيلية
    # ============================================================
    
    def _gather_perception(self, input_data: Dict[str, Any], cycle_id: str) -> Dict[str, Any]:
        """
        جمع الإدراك من جميع المصادر.
        
        يشمل:
        - الوعي (حقل الوعي، الانتباه، الاستبطان)
        - الذاكرة (السجل، الذاكرة الحية، التخزين)
        - المكونات البيولوجية (الغرائز، الدوافع)
        """
        perception = {
            "cycle_id": cycle_id,
            "input": input_data,
            "timestamp": time.time(),
            "consciousness": {},
            "memory": {},
            "biological": {},
            "quantum": {}
        }
        
        # ===== الوعي =====
        if self.consciousness:
            # حقل الوعي
            consciousness_field = self.consciousness.get("field")
            if consciousness_field:
                field_status = self._safe_call(consciousness_field, "get_consciousness_status", default={})
                perception["consciousness"]["field"] = field_status
            
            # الوعي (awareness)
            awareness = self.consciousness.get("awareness")
            if awareness:
                awareness_status = self._safe_call(awareness, "get_awareness_status", default={})
                perception["consciousness"]["awareness"] = awareness_status
            
            # الانتباه
            attention = self.consciousness.get("attention")
            if attention:
                attention_status = self._safe_call(attention, "get_attention_status", default={})
                perception["consciousness"]["attention"] = attention_status
            
            # الاستبطان
            introspection = self.consciousness.get("introspection")
            if introspection:
                introspection_status = self._safe_call(introspection, "get_introspection_status", default={})
                perception["consciousness"]["introspection"] = introspection_status
            
            # الهوية
            identity = self.consciousness.get("identity")
            if identity:
                identity_status = self._safe_call(identity, "get_identity_status", default={})
                perception["consciousness"]["identity"] = identity_status
            
            # نموذج الذات
            self_model = self.consciousness.get("self_model")
            if self_model:
                self_status = self._safe_call(self_model, "get_self_status", default={})
                perception["consciousness"]["self_model"] = self_status
        
        # ===== الذاكرة =====
        # السجل السيادي
        if self.memory_core:
            core_status = self._safe_call(self.memory_core, "get_statistics", default={})
            perception["memory"]["core"] = core_status
        
        # الذاكرة الحية
        if self.memory_dynamic:
            dynamic_status = self._safe_call(self.memory_dynamic, "statistics", default={})
            perception["memory"]["dynamic"] = dynamic_status
        
        # التخزين
        if self.memory_store:
            store_status = self._safe_call(self.memory_store, "get_statistics", default={})
            perception["memory"]["store"] = store_status
        
        # ===== المكونات البيولوجية =====
        if self.biological:
            # الغرائز
            instincts = self.biological.get("instincts")
            if instincts:
                instincts_status = self._safe_call(instincts, "get_instinct_status", default={})
                perception["biological"]["instincts"] = instincts_status
            
            # الدوافع
            drives = self.biological.get("drives")
            if drives:
                drives_status = self._safe_call(drives, "get_drive_status", default={})
                perception["biological"]["drives"] = drives_status
            
            # الأنماط الأصلية
            archetypes = self.biological.get("archetypes")
            if archetypes:
                archetypes_status = self._safe_call(archetypes, "get_archetype_status", default={})
                perception["biological"]["archetypes"] = archetypes_status
        
        # ===== الكم =====
        if self.quantum:
            quantum_status = self._safe_call(self.quantum, "get_controller_status", default={})
            perception["quantum"] = quantum_status
        
        # ========================================================
        # R-612: فهم النص عبر NexusCore (S-7) — الذكاء السيادي
        # يقرأ ما يقوله السيد فعلياً: اللغة، المشاعر، النية، الكلمات
        # ========================================================
        if self.nexus:
            text = ""
            if isinstance(input_data, dict):
                text = input_data.get("text", "") or ""
            if text:
                nexus_perception = {}
                
                # معالجة النص (تنظيف + ترميز + كلمات مفتاحية)
                text_proc = self.nexus.get_component("text_proc")
                if text_proc:
                    processed = self._safe_call(text_proc, "process", text, default=None)
                    if processed is not None:
                        nexus_perception["processed"] = {
                            "word_count": getattr(processed, "word_count", 0),
                            "char_count": getattr(processed, "char_count", 0),
                            "keywords": getattr(processed, "keywords", []),
                            "sentences": getattr(processed, "sentences", []),
                            "language": getattr(processed, "language", ""),
                        }
                
                # كشف اللغة
                lang_detect = self.nexus.get_component("lang_detect")
                if lang_detect:
                    lang = self._safe_call(lang_detect, "detect", text, default=None)
                    if lang is not None:
                        nexus_perception["language"] = {
                            "code": getattr(lang, "language", ""),
                            "confidence": getattr(lang, "confidence", 0.0),
                            "script": getattr(lang, "script", ""),
                            "mixed": getattr(lang, "mixed", False),
                        }
                
                # تحليل المشاعر
                sentiment = self.nexus.get_component("sentiment")
                if sentiment:
                    senti = self._safe_call(sentiment, "analyze", text, default=None)
                    if senti is not None:
                        nexus_perception["sentiment"] = {
                            "score": getattr(senti, "score", 0.0),
                            "label": getattr(senti, "label", "neutral"),
                            "confidence": getattr(senti, "confidence", 0.0),
                            "language": getattr(senti, "language", ""),
                        }
                
                # كشف النية
                intent = self.nexus.get_component("intent")
                if intent:
                    detected = self._safe_call(intent, "recognize", text, default=None)
                    if detected is not None:
                        nexus_perception["intent"] = {
                            "name": getattr(detected, "name", "unknown"),
                            "confidence": getattr(detected, "confidence", 0.0),
                            "matched_patterns": getattr(detected, "matched_patterns", []),
                            "entities": getattr(detected, "entities", {}),
                        }
                
                # استخراج الكيانات
                if text_proc:
                    entities = self._safe_call(text_proc, "extract_entities", text, default={})
                    if entities:
                        nexus_perception["entities"] = entities
                
                # تسجيل الحدث في NexusCore (المجمع + السجل)
                collector = self.nexus.get_component("collector")
                if collector:
                    self._safe_call(collector, "ingest", "orchestrator", {
                        "text": text[:500],
                        "cycle_id": cycle_id,
                        "perception": nexus_perception,
                    }, {"source": "orchestrator_cycle"})
                
                perception["nexus"] = nexus_perception
                self._log("info", "🧠 NexusCore فهم النص", {
                    "language": nexus_perception.get("language", {}).get("code", ""),
                    "sentiment": nexus_perception.get("sentiment", {}).get("label", ""),
                    "intent": nexus_perception.get("intent", {}).get("name", ""),
                })
        
        return perception
    
    def _analyze_future(self, perception: Dict[str, Any], cycle_id: str) -> Dict[str, Any]:
        """
        تحليل المستقبل والتنبؤات.
        
        يشمل:
        - التنبؤات العميقة
        - السيناريوهات
        - تحليل المخاطر
        """
        future_analysis = {
            "cycle_id": cycle_id,
            "timestamp": time.time(),
            "predictions": {},
            "scenarios": {},
            "risks": {},
            "opportunities": {}
        }
        
        # ===== التنبؤات =====
        if self.predictive:
            predictive_engine = self.predictive.get("engine")
            if predictive_engine:
                # خريطة المستقبل
                future_map = self._safe_call(predictive_engine, "compute_future_map", default={})
                future_analysis["predictions"]["future_map"] = future_map
                
                # التنبؤات الاحتمالية
                prob_forecast = self._safe_call(predictive_engine, "compute_probability_forecast", default={})
                future_analysis["predictions"]["probability_forecast"] = prob_forecast
            
            # مدير المخاطر
            risk_manager = self.predictive.get("risk_manager")
            if risk_manager:
                risk_status = self._safe_call(risk_manager, "get_risk_status", default={})
                future_analysis["risks"] = risk_status
            
            # متحكم التنبؤ
            predictive_controller = self.predictive.get("controller")
            if predictive_controller:
                controller_snap = self._safe_call(predictive_controller, "predictive_controller_cycle", default={})
                if hasattr(controller_snap, "scenarios"):
                    future_analysis["scenarios"] = controller_snap.scenarios
                elif isinstance(controller_snap, dict):
                    future_analysis["scenarios"] = controller_snap.get("scenarios", [])
        
        # ===== المحاكاة =====
        if self.simulation:
            sim_controller = self.simulation.get("controller")
            if sim_controller:
                sim_status = self._safe_call(sim_controller, "get_controller_status", default={})
                future_analysis["simulation"] = sim_status
            
            sim_analyzer = self.simulation.get("analyzer")
            if sim_analyzer:
                analyzer_status = self._safe_call(sim_analyzer, "get_analyzer_status", default={})
                future_analysis["analysis"] = analyzer_status
        
        # حساب الفرص من المخاطر (عكسياً)
        risks = future_analysis.get("risks", {})
        if risks:
            # كلما زاد الخطر، قلت الفرصة
            risk_level = risks.get("overall_risk", 0.5)
            future_analysis["opportunities"]["overall"] = 1 - risk_level
        
        return future_analysis
    
    def _evaluate_sovereign(self, perception: Dict[str, Any], 
                            future_analysis: Dict[str, Any],
                            cycle_id: str) -> Dict[str, Any]:
        """
        تقييم السيادة والإرادة.
        
        يشمل:
        - الإرادة السيادية
        - الاصطفاف
        - التوجيهات
        """
        sovereign_eval = {
            "cycle_id": cycle_id,
            "timestamp": time.time(),
            "will": {},
            "alignment": {},
            "directives": {},
            "controller": {}
        }
        
        if not self.sovereign:
            # قرار افتراضي إن لم توجد سيادة
            sovereign_eval["decision"] = {
                "action": "continue",
                "confidence": 0.5,
                "reason": "no_sovereign_layer"
            }
            return sovereign_eval
        
        # ===== الإرادة =====
        will = self.sovereign.get("will")
        if will:
            will_status = self._safe_call(will, "get_will_status", default={})
            sovereign_eval["will"] = will_status
            
            # استخراج الإرادة المهيمنة
            if isinstance(will_status, dict):
                sovereign_eval["dominant_will"] = will_status.get("will_mode", "balanced")
        
        # ===== الاصطفاف =====
        alignment = self.sovereign.get("alignment")
        if alignment:
            alignment_status = self._safe_call(alignment, "get_alignment_status", default={})
            sovereign_eval["alignment"] = alignment_status
        
        # ===== التوجيهات =====
        directives = self.sovereign.get("directives")
        if directives:
            directives_status = self._safe_call(directives, "get_directives_status", default={})
            sovereign_eval["directives"] = directives_status
        
        # ===== المتحكم السيادي =====
        controller = self.sovereign.get("controller")
        if controller:
            controller_status = self._safe_call(controller, "get_controller_status", default={})
            sovereign_eval["controller"] = controller_status
        
        return sovereign_eval
    
    def _make_decision(self, sovereign_eval: Dict[str, Any],
                       perception: Dict[str, Any],
                       future_analysis: Dict[str, Any],
                       cycle_id: str) -> Dict[str, Any]:
        """
        اتخاذ القرار النهائي.
        
        يدعم:
        - قرارات من السيادة
        - قرارات منفردة
        - قرارات اندماجية
        """
        decision = {
            "cycle_id": cycle_id,
            "timestamp": time.time(),
            "action": "noop",
            "confidence": 0.5,
            "reasoning": [],
            "source": "orchestrator",
            "priority": "normal"
        }
        
        # محاولة الحصول على قرار من متحكم السيادة
        controller = self.sovereign.get("controller") if self.sovereign else None
        if controller:
            controller_decision = self._safe_call(controller, "controller_cycle", default=None)
            if controller_decision:
                # R-612: ControllerSnapshot يحمل final_decision (FinalDecision)
                # وليس sovereign_decision — كان القرار السيادي يُتجاهل دائماً
                final_decision = getattr(controller_decision, "final_decision", None)
                if final_decision is not None:
                    command_name = getattr(final_decision, "command_name", "continue")
                    # خريطة أوامر المتحكم السيادي إلى إجراءات المنسق
                    _controller_action_map = {
                        "continue": "continue",
                        "emergency_shutdown": "activate_defense",
                        "recalibrate": "monitor",
                        "adjust_priorities": "monitor",
                        "realign": "monitor",
                    }
                    decision["action"] = _controller_action_map.get(command_name, "continue")
                    decision["confidence"] = getattr(controller_decision, "global_priority", 0.5)
                    decision["source"] = "sovereign_controller"
                    decision["reasoning"].append(f"قرار من متحكم السيادة: {command_name}")
        
        # R-612: توجيه القرار بنية المستخدم (NexusCore) — إذا طلب السيد
        # تحليلاً أو تنبؤاً أو حالة، يستجيب الذكاء السيادي مباشرة
        if decision["action"] == "continue":
            nexus_perception = perception.get("nexus", {})
            intent_name = nexus_perception.get("intent", {}).get("name", "")
            if intent_name == "analyze":
                decision["action"] = "explore"
                decision["confidence"] = max(decision["confidence"], 0.7)
                decision["source"] = "nexus_intent"
                decision["reasoning"].append("نية المستخدم: تحليل — تفعيل الاستكشاف")
            elif intent_name == "forecast":
                decision["action"] = "monitor"
                decision["confidence"] = max(decision["confidence"], 0.65)
                decision["source"] = "nexus_intent"
                decision["reasoning"].append("نية المستخدم: تنبؤ — تفعيل المراقبة")
            elif intent_name == "status":
                decision["action"] = "monitor"
                decision["confidence"] = max(decision["confidence"], 0.6)
                decision["source"] = "nexus_intent"
                decision["reasoning"].append("نية المستخدم: حالة — تفعيل المراقبة")
            elif intent_name == "alert":
                decision["action"] = "activate_defense"
                decision["confidence"] = max(decision["confidence"], 0.8)
                decision["source"] = "nexus_intent"
                decision["reasoning"].append("نية المستخدم: تنبيه — تفعيل الدفاع")
        
        # إذا لم يكن هناك قرار من السيادة، استخدم التحليل
        if decision["action"] == "noop":
            # تحليل المستقبل
            risks = future_analysis.get("risks", {})
            risk_level = risks.get("overall_risk", 0.5)
            
            if risk_level > 0.7:
                decision["action"] = "activate_defense"
                decision["confidence"] = risk_level
                decision["reasoning"].append(f"مستوى خطر مرتفع: {risk_level:.1%}")
            elif risk_level > 0.4:
                decision["action"] = "monitor"
                decision["confidence"] = 0.6
                decision["reasoning"].append(f"مستوى خطر متوسط: {risk_level:.1%}")
            else:
                decision["action"] = "continue"
                decision["confidence"] = 0.7
                decision["reasoning"].append(f"مستوى خطر منخفض: {risk_level:.1%}")
            
            # فرص
            opportunities = future_analysis.get("opportunities", {})
            opp_level = opportunities.get("overall", 0.5)
            if opp_level > 0.7:
                decision["action"] = "explore"
                decision["confidence"] = opp_level
                decision["reasoning"].append(f"فرصة عالية: {opp_level:.1%}")
        
        # تخزين القرار في الكاش للاستخدام السريع
        cache_key = f"decision_{hashlib.md5(str(decision).encode()).hexdigest()[:16]}"
        self._cache_set(cache_key, decision, ttl=60)
        
        return decision
    
    def _execute_decision(self, decision: Dict[str, Any], cycle_id: str) -> Dict[str, Any]:
        """
        تنفيذ القرار.
        
        يشمل:
        - تنفيذ مباشر
        - تمرير إلى المحاكاة
        - تطبيق التوجيهات
        """
        execution_result = {
            "cycle_id": cycle_id,
            "timestamp": time.time(),
            "status": "pending",
            "action": decision.get("action", "noop"),
            "details": {}
        }
        
        action = decision.get("action", "noop")
        
        # تنفيذ الإجراء حسب النوع
        if action == "activate_defense":
            # تفعيل الدفاعات
            if self.memory_core:
                self._safe_call(self.memory_core, "append_event", "orchestrator::defense_activated", 
                               {"action": action, "cycle_id": cycle_id})
            execution_result["status"] = "executed"
            execution_result["details"] = {"defense_activated": True}
            
        elif action == "monitor":
            # مراقبة مكثفة
            execution_result["status"] = "executed"
            execution_result["details"] = {"monitoring_intensified": True}
            
        elif action == "explore":
            # تفعيل الاستكشاف
            execution_result["status"] = "executed"
            execution_result["details"] = {"exploration_enabled": True}
            
        elif action == "continue":
            # استمرار عادي
            execution_result["status"] = "executed"
            execution_result["details"] = {"continued": True}
        
        else:
            # إجراء غير معروف
            execution_result["status"] = "unknown_action"
            execution_result["details"] = {"action_received": action}
        
        return execution_result
    
    def _update_memory(self, perception: Dict[str, Any], decision: Dict[str, Any],
                       execution_result: Dict[str, Any], cycle_id: str) -> Dict[str, Any]:
        """
        تحديث الذاكرة بناءً على الدورة.
        """
        memory_update = {
            "cycle_id": cycle_id,
            "timestamp": time.time(),
            "status": "pending",
            "details": {}
        }
        
        record = {
            "cycle_id": cycle_id,
            "perception": perception,
            "decision": decision,
            "execution": execution_result,
            "timestamp": time.time()
        }
        
        # تخزين في السجل السيادي
        if self.memory_core and hasattr(self.memory_core, "append_event"):
            self._safe_call(self.memory_core, "append_event", "orchestrator::cycle", record)
            memory_update["status"] = "stored_in_core"
        
        # تخزين في الذاكرة الحية
        if self.memory_dynamic and hasattr(self.memory_dynamic, "ingest"):
            self._safe_call(self.memory_dynamic, "ingest", "system", str(record), intensity=0.5)
            memory_update["status"] = "stored_in_dynamic"
        
        # ========================================================
        # الضغط الأسطوري (R-608) — إحياء memory/compress.py
        # ضغط دوري للسجل السيادي كل 50 دورة
        # ========================================================
        try:
            if self._stats.get("total_cycles", 0) % 50 == 0:
                from memory.compress import get_compressor
                compressor = get_compressor()
                compression = compressor.compress_from_core(limit=200)
                memory_update["compression"] = {
                    "active": True,
                    "consciousness": compression.get("consciousness", "")[:32],
                    "dimensions": compression.get("dimensions", []),
                    "events_compressed": compression.get("events_compressed", 0),
                    "stats": compressor.get_stats()
                }
                self._log("info", "🧬 الضغط الأسطوري: تم ضغط السجل السيادي", 
                          {"consciousness": compression.get("consciousness", "")[:16]})
        except Exception as _compress_err:
            memory_update["compression"] = {"active": False, "error": str(_compress_err)[:100]}
        
        # ========================================================
        # R-612: تخزين الدورة في NexusCore (S-7) — الذاكرة الطويلة
        # + سجل التدقيق الموقّع
        # ========================================================
        if self.nexus:
            store = self.nexus.get_component("store")
            if store:
                self._safe_call(store, "save", "cycles", cycle_id, record,
                                {"source": "orchestrator", "action": decision.get("action", "")})
                memory_update["status"] = "stored_in_nexus"
            
            audit = self.nexus.get_component("audit")
            if audit:
                self._safe_call(audit, "log", "orchestrator", "cycle", f"cycle:{cycle_id}",
                                {"action": decision.get("action", ""), "success": execution_result.get("status", "")})
        
        memory_update["details"] = {"record_size": len(str(record))}
        
        return memory_update
    
    # ============================================================
    # دورة مستمرة (للتشغيل التلقائي)
    # ============================================================
    
    def run_continuous(self, callback: Callable[[CycleResult], None] = None):
        """
        تشغيل دورات مستمرة في حلقة.
        
        Args:
            callback: دالة تُستدعى بعد كل دورة
        """
        self._log("info", "▶️ بدء التشغيل المستمر", {})
        
        while self._active:
            try:
                result = self.run_cycle()
                
                if callback:
                    try:
                        callback(result)
                    except Exception as e:
                        self._log("warning", "فشل استدعاء callback", {"error": str(e)})
                
                if self.config.loop_interval > 0:
                    time.sleep(self.config.loop_interval)
                    
            except KeyboardInterrupt:
                self._log("info", "⚠️ تم إيقاف التشغيل بواسطة المستخدم", {})
                break
            except Exception as e:
                self._log("error", f"خطأ في الحلقة المستمرة: {e}", {})
                time.sleep(1)
    
    # ============================================================
    # إعادة التهيئة
    # ============================================================
    
    def reset_all(self, preserve_session: bool = False):
        """
        إعادة تهيئة شاملة لجميع المكونات.
        
        Args:
            preserve_session: إذا True، يحتفظ بمعرف الجلسة
        """
        self._log("warning", "🔄 بدء إعادة التهيئة الشاملة", {"preserve_session": preserve_session})
        
        # إعادة تعيين الحالة الداخلية
        if not preserve_session:
            self._session_id = hashlib.sha256(f"{time.time()}{secrets.token_hex(16)}".encode()).hexdigest()[:16]
        
        self._history.clear()
        self._cache_clear()
        self._error_counter = 0
        self._recovery_mode = False
        self._recovery_attempts_left = self.config.recovery_attempts
        
        self._stats = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "avg_cycle_duration": 0.0,
            "last_cycle_id": None,
            "last_error": None,
            "started_at": time.time(),
            "mode_changes": self._stats.get("mode_changes", [])
        }
        
        # إعادة تعيين المكونات
        # الوعي
        if self.consciousness:
            for name, component in self.consciousness.items():
                if hasattr(component, "reset"):
                    self._safe_call(component, "reset")
        
        # الذاكرة
        if self.memory_core and hasattr(self.memory_core, "reset"):
            self._safe_call(self.memory_core, "reset")
        
        if self.memory_dynamic and hasattr(self.memory_dynamic, "reset"):
            self._safe_call(self.memory_dynamic, "reset")
        
        if self.memory_store and hasattr(self.memory_store, "reset"):
            self._safe_call(self.memory_store, "reset")
        
        # المكونات البيولوجية
        if self.biological:
            for name, component in self.biological.items():
                if hasattr(component, "reset"):
                    self._safe_call(component, "reset")
        
        # التنبؤ والمحاكاة
        if self.predictive:
            for name, component in self.predictive.items():
                if hasattr(component, "reset"):
                    self._safe_call(component, "reset")
        
        if self.simulation:
            for name, component in self.simulation.items():
                if hasattr(component, "reset"):
                    self._safe_call(component, "reset")
        
        # السيادة
        if self.sovereign:
            for name, component in self.sovereign.items():
                if hasattr(component, "reset"):
                    self._safe_call(component, "reset")
        
        # الكم
        if self.quantum and hasattr(self.quantum, "reset"):
            self._safe_call(self.quantum, "reset")
        
        # تسجيل
        self._log("info", "✅ إعادة التهيئة الشاملة اكتملت", {
            "new_session_id": self._session_id,
            "preserved": preserve_session
        })
        
        logger.warning(f"🔄 Sovereign Orchestrator تمت إعادة التهيئة - جلسة جديدة: {self._session_id}")
    
    def reset_component(self, component_name: str) -> bool:
        """
        إعادة تهيئة مكون معين فقط.
        
        Args:
            component_name: اسم المكون (مثل "consciousness_field", "memory_core")
        
        Returns:
            True إذا تم إعادة التهيئة بنجاح
        """
        component = None
        
        # البحث عن المكون
        if component_name.startswith("consciousness_") and self.consciousness:
            key = component_name.replace("consciousness_", "")
            component = self.consciousness.get(key)
        elif component_name == "memory_core":
            component = self.memory_core
        elif component_name == "memory_dynamic":
            component = self.memory_dynamic
        elif component_name == "memory_store":
            component = self.memory_store
        elif component_name.startswith("biological_") and self.biological:
            key = component_name.replace("biological_", "")
            component = self.biological.get(key)
        elif component_name.startswith("predictive_") and self.predictive:
            key = component_name.replace("predictive_", "")
            component = self.predictive.get(key)
        elif component_name.startswith("simulation_") and self.simulation:
            key = component_name.replace("simulation_", "")
            component = self.simulation.get(key)
        elif component_name.startswith("sovereign_") and self.sovereign:
            key = component_name.replace("sovereign_", "")
            component = self.sovereign.get(key)
        elif component_name == "quantum":
            component = self.quantum
        
        if component and hasattr(component, "reset"):
            self._safe_call(component, "reset")
            self._log("info", f"✅ إعادة تهيئة المكون {component_name}", {})
            return True
        
        self._log("warning", f"❌ فشل إعادة تهيئة المكون {component_name} (غير موجود أو لا يدعم reset)", {})
        return False
    
    # ============================================================
    # واجهات الاستعلام والتشخيص
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمنسق"""
        return {
            "session_id": self._session_id,
            "mode": self.config.mode,
            "active": self._active,
            "recovery_mode": self._recovery_mode,
            "stats": self._stats,
            "components": self._get_component_status(),
            "cache_size": len(self._cache),
            "history_size": len(self._history),
            "timestamp": time.time()
        }
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """آخر الأحداث المسجلة"""
        return list(self._history)[-limit:]
    
    def get_component_health(self) -> Dict[str, Dict[str, Any]]:
        """صحة جميع المكونات"""
        return {
            name: {
                "status": h.status,
                "error_count": h.error_count,
                "last_error": h.last_error,
                "last_success": h.last_success
            }
            for name, h in self._component_health.items()
        }
    
    def set_mode(self, mode: str) -> bool:
        """تغيير وضع التشغيل"""
        if mode not in [m.value for m in OrchestratorMode]:
            return False
        
        old_mode = self.config.mode
        self.config.mode = mode
        self._stats["mode_changes"].append({
            "from": old_mode,
            "to": mode,
            "timestamp": time.time()
        })
        
        self._log("warning", f"⚙️ تغيير وضع التشغيل: {old_mode} → {mode}", {})
        
        return True
    
    def stop(self):
        """إيقاف المنسق"""
        self._active = False
        self._log("info", "🛑 إيقاف Sovereign Orchestrator", {})
        logger.warning("🛑 Sovereign Orchestrator تم إيقافه")


# ============================================================
# الـ Singleton
# ============================================================

_orchestrator_instance: Optional[SovereignOrchestrator] = None
_orchestrator_lock = threading.Lock()


def get_orchestrator() -> SovereignOrchestrator:
    """الحصول على النسخة الوحيدة من المنسق السيادي"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        with _orchestrator_lock:
            if _orchestrator_instance is None:
                _orchestrator_instance = SovereignOrchestrator()
    return _orchestrator_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("👑 Sovereign Orchestrator - العقل المنسق الأعلى")
    print("=" * 80 + "\n")
    
    orchestrator = get_orchestrator()
    
    # 1) تشغيل دورة واحدة
    print("🔄 تشغيل دورة معالجة...")
    result = orchestrator.run_cycle({"test": "hello_world"})
    print(f"   الدورة: {result.cycle_id}")
    print(f"   النجاح: {result.success}")
    print(f"   المدة: {result.duration:.3f} ثانية")
    print(f"   القرار: {result.decision.get('action', 'unknown')}")
    
    # 2) الحالة
    print("\n📊 حالة المنسق:")
    status = orchestrator.get_status()
    print(f"   الجلسة: {status['session_id']}")
    print(f"   الوضع: {status['mode']}")
    print(f"   الدورات: {status['stats']['total_cycles']}")
    print(f"   النجاح: {status['stats']['successful_cycles']}")
    
    # 3) صحة المكونات
    print("\n🩺 صحة المكونات:")
    health = orchestrator.get_component_health()
    for name, h in list(health.items())[:5]:
        print(f"   {name}: {h['status']}")
    
    # 4) إعادة تهيئة شاملة
    print("\n🔄 إعادة تهيئة شاملة...")
    orchestrator.reset_all()
    
    # 5) إعادة تشغيل
    print("\n🔄 تشغيل دورة بعد إعادة التهيئة...")
    result2 = orchestrator.run_cycle({"test": "after_reset"})
    print(f"   الدورة: {result2.cycle_id}")
    print(f"   النجاح: {result2.success}")
    
    print("\n" + "=" * 80)
    print("✅ Sovereign Orchestrator جاهز - العقل المنسق الأعلى")
    print("=" * 80)
