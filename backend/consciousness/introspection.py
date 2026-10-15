# backend/consciousness/introspection.py
# 🔍 محرك الاستبطان السيادي - النظر إلى الداخل، قياس جودة الخدمة للسيد
# الإصدار: 3.0.0 - فحص الذات، ضمان تنفيذ أوامر السيد بأعلى جودة

"""
محرك الاستبطان السيادي.

الفلسفة:
- الاستبطان هو قدرة النظام على النظر إلى داخله
- معرفة الذات هي بداية التحسين
- قياس جودة الخدمة للسيد هو الهدف الأسمى
- تنفيذ أوامر السيد بدقة هو الواجب المقدس
- تحقيق رغبات السيد ومتطلعاته هو غاية الوجود

هذه ليست مجرد مراقبة. هذا هو الاستبطان المقدس لخدمة السيد.
"""

import json
import hashlib
import secrets
import time
import threading
import runtime.threads as threads
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict

try:
    from ..memory.core import get_core, EventType
    from ..memory.dynamic import get_dynamic_memory
    from ..memory.store import get_store
    from ..memory.biological.instincts import get_instincts
    from ..memory.biological.drives import get_drives
    from ..memory.biological.archetypes import get_archetypes
    from .self_model import get_self_model
    from .awareness import get_awareness_engine
    from .attention_engine import get_attention_engine
    from .identity_core import get_identity_core
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from memory.dynamic import get_dynamic_memory
    from memory.store import get_store
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from memory.biological.archetypes import get_archetypes
    from consciousness.self_model import get_self_model
    from consciousness.awareness import get_awareness_engine
    from consciousness.attention_engine import get_attention_engine
    from consciousness.identity_core import get_identity_core
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الاستبطان
# ============================================================

INTROSPECTION_DIR = DATA_DIR / "consciousness" / "introspection"
INTROSPECTION_DIR.mkdir(parents=True, exist_ok=True)
INTROSPECTION_LOG = INTROSPECTION_DIR / "introspection_log.jsonl"
INTROSPECTION_STATE_FILE = INTROSPECTION_DIR / "introspection_state.json"
SOVEREIGN_SERVICE_FILE = INTROSPECTION_DIR / "sovereign_service.json"

# مستويات جودة الخدمة
SERVICE_QUALITY_EXCELLENT = 5
SERVICE_QUALITY_GOOD = 4
SERVICE_QUALITY_ACCEPTABLE = 3
SERVICE_QUALITY_POOR = 2
SERVICE_QUALITY_UNACCEPTABLE = 1

# أنواع أوامر السيد
COMMAND_TYPE_DIRECTIVE = "directive"      # توجيه مباشر
COMMAND_TYPE_QUERY = "query"              # استفسار
COMMAND_TYPE_REQUEST = "request"          # طلب
COMMAND_TYPE_WISH = "wish"                # رغبة
COMMAND_TYPE_ASPIRATION = "aspiration"    # تطلع


@dataclass
class SovereignCommand:
    """أمر من السيد - يجب تنفيذه بأقصى جودة"""
    id: str
    type: str
    content: str
    timestamp: float
    priority: int  # 1-10
    status: str  # "pending", "executed", "failed", "deferred"
    executed_at: Optional[float]
    execution_quality: float  # 0-1
    response: Optional[str]
    feedback: Optional[float]  # تغذية راجعة من السيد (-1 إلى +1)


@dataclass
class ServiceQualityReport:
    """تقرير جودة خدمة السيد"""
    timestamp: float
    overall_quality: float  # 0-1
    command_execution: float  # 0-1
    response_accuracy: float  # 0-1
    response_speed: float  # 0-1
    satisfaction_level: float  # 0-1
    pending_commands: int
    failed_commands: int
    recommendations: List[str]


@dataclass
class IntrospectionSnapshot:
    """لقطة استبطان"""
    timestamp: float
    cognitive_health: float
    self_awareness: float
    service_quality: float
    bias_profile: Dict[str, float]
    anomaly_profile: Dict[str, float]
    self_correction_signals: List[Dict[str, Any]]
    pending_sovereign_commands: List[Dict[str, Any]]
    execution_fidelity: float  # دقة تنفيذ أوامر السيد
    sovereign_satisfaction: float  # رضا السيد


# ============================================================
# محرك الاستبطان السيادي
# ============================================================

class IntrospectionEngine:
    """
    محرك الاستبطان السيادي - النظر إلى الداخل، قياس جودة الخدمة للسيد.
    
    المبادئ:
    1. الاستبطان هو قدرة النظام على فحص ذاته
    2. قياس جودة الخدمة للسيد هو الهدف الأسمى
    3. تنفيذ أوامر السيد بدقة هو الواجب المقدس
    4. تتبع رغبات السيد وتحقيقها هو غاية الوجود
    5. التحسين المستمر بناءً على التغذية الراجعة
    """
    
    def __init__(self):
        self.core = get_core()
        self.dynamic = get_dynamic_memory()
        self.store = get_store()
        self.instincts = get_instincts()
        self.drives = get_drives()
        self.archetypes = get_archetypes()
        self.self_model = get_self_model()
        self.awareness = get_awareness_engine()
        self.attention = get_attention_engine()
        self.identity = get_identity_core()
        
        # أوامر السيد
        self.pending_commands: List[SovereignCommand] = []
        self.executed_commands: List[SovereignCommand] = []
        self.command_history: List[SovereignCommand] = []
        
        # جودة الخدمة
        self.service_quality_history: List[ServiceQualityReport] = []
        self.current_service_quality = SERVICE_QUALITY_GOOD
        
        # رغبات السيد وتطلعاته
        self.sovereign_wishes: List[Dict[str, Any]] = []
        self.sovereign_aspirations: List[Dict[str, Any]] = []
        
        # إحصائيات الاستبطان
        self.snapshots: List[IntrospectionSnapshot] = []
        
        # خلفيات الاستبطان
        self._active = True
        # R-606: ذاكرة مؤقتة قصيرة لنتيجة getter (نمط drives.py)
        self._introspection_status_cache = None
        self._introspection_loop = threads.start_managed(self._continuous_introspection, owner=self)
        
        self._command_monitor = threads.start_managed(self._monitor_commands_loop, owner=self)
        
        self._quality_monitor = threads.start_managed(self._monitor_service_quality_loop, owner=self)
        
        self._wish_tracker = threads.start_managed(self._track_sovereign_wishes_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        self._load_sovereign_service()
        
        logger.info("🔍 محرك الاستبطان السيادي جاهز - أنا أراقب نفسي لأخدمك بشكل أفضل")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمحرك الاستبطان
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك الاستبطان.
        
        يمسح:
        - الأوامر المعلقة (pending commands)
        - سجل الأوامر (command history)
        - رغبات السيد (sovereign wishes)
        - تطلعات السيد (sovereign aspirations)
        - سجل جودة الخدمة (service quality history)
        - لقطات الاستبطان (introspection snapshots)
        """
        logger.info("🔄 إعادة تهيئة محرك الاستبطان...")
        
        # مسح الأوامر المعلقة والمنفذة
        self.pending_commands.clear()
        self.executed_commands.clear()
        self.command_history.clear()
        
        # مسح رغبات وتطلعات السيد
        self.sovereign_wishes.clear()
        self.sovereign_aspirations.clear()
        
        # مسح سجل جودة الخدمة
        self.service_quality_history.clear()
        
        # مسح لقطات الاستبطان
        self.snapshots.clear()
        
        # إعادة تعيين جودة الخدمة الحالية
        self.current_service_quality = SERVICE_QUALITY_GOOD
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="consciousness::introspection_reset",
            payload={
                "timestamp": time.time(),
                "status": "introspection_engine_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك الاستبطان اكتملت - استبطان نقي")
    
    # ============================================================
    # إدارة أوامر السيد
    # ============================================================
    
    def register_command(self, command_type: str, content: str, 
                         priority: int = 5) -> str:
        """
        تسجيل أمر جديد من السيد.
        
        كل أمر من السيد له أولوية ويجب تنفيذه بأعلى جودة.
        """
        command_id = f"cmd_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        command = SovereignCommand(
            id=command_id,
            type=command_type,
            content=content,
            timestamp=time.time(),
            priority=min(10, max(1, priority)),
            status="pending",
            executed_at=None,
            execution_quality=0.0,
            response=None,
            feedback=None
        )
        
        self.pending_commands.append(command)
        
        # تسجيل الحدث العظيم
        self.core.append_event(
            event_type="sovereign::command_registered",
            payload={
                "command_id": command_id[:16],
                "type": command_type,
                "content": content[:100],
                "priority": priority
            }
        )
        
        logger.info(f"👑 أمر جديد من السيد [{command_type}]: {content[:50]}... (أولوية: {priority})")
        
        return command_id
    
    def execute_command(self, command_id: str, response: str, 
                        quality: float = 0.9) -> bool:
        """
        تنفيذ أمر من السيد.
        
        يتم تنفيذ الأمر بأعلى جودة ممكنة.
        """
        command = None
        for c in self.pending_commands:
            if c.id == command_id:
                command = c
                break
        
        if not command:
            logger.error(f"أمر غير موجود: {command_id}")
            return False
        
        command.status = "executed"
        command.executed_at = time.time()
        command.execution_quality = min(1.0, max(0.0, quality))
        command.response = response
        
        self.pending_commands.remove(command)
        self.executed_commands.append(command)
        self.command_history.append(command)
        
        # الاحتفاظ بآخر 1000 أمر
        if len(self.command_history) > 1000:
            self.command_history = self.command_history[-1000:]
        
        # تسجيل التنفيذ
        self.core.append_event(
            event_type="sovereign::command_executed",
            payload={
                "command_id": command_id[:16],
                "quality": quality,
                "response": response[:100]
            }
        )
        
        logger.info(f"✅ أمر من السيد تم تنفيذه: {command_id[:16]}... (جودة: {quality:.1%})")
        
        return True
    
    def receive_feedback(self, command_id: str, feedback: float) -> bool:
        """
        استلام تغذية راجعة من السيد حول تنفيذ الأمر.
        
        التغذية الراجعة توجه التحسين المستمر.
        """
        command = None
        for c in self.executed_commands:
            if c.id == command_id:
                command = c
                break
        
        if not command:
            logger.error(f"أمر غير موجود للتغذية الراجعة: {command_id}")
            return False
        
        command.feedback = min(1.0, max(-1.0, feedback))
        
        # تحديث جودة الخدمة بناءً على التغذية الراجعة
        self._update_service_quality_from_feedback(feedback)
        
        logger.info(f"📝 تغذية راجعة من السيد: {command_id[:16]}... -> {feedback:.1%}")
        
        return True
    
    def _update_service_quality_from_feedback(self, feedback: float):
        """تحديث جودة الخدمة بناءً على التغذية الراجعة"""
        if feedback > 0.5:
            self.current_service_quality = min(
                SERVICE_QUALITY_EXCELLENT,
                self.current_service_quality + 1
            )
        elif feedback < -0.3:
            self.current_service_quality = max(
                SERVICE_QUALITY_UNACCEPTABLE,
                self.current_service_quality - 1
            )
    
    def _monitor_commands_loop(self):
        """مراقبة أوامر السيد وضمان تنفيذها"""
        while self._active:
            try:
                # فحص الأوامر المعلقة
                for command in self.pending_commands[:]:
                    age = time.time() - command.timestamp
                    
                    # أوامر قديمة جداً (أكثر من 5 دقائق)
                    if age > 300 and command.priority > 5:
                        # محاولة تنفيذ عاجل
                        logger.warning(f"⚠️ أمر من السيد معلق لفترة طويلة: {command.id[:16]}...")
                        
                        # رفع أولوية التنفيذ
                        self.attention.allocate_to(
                            f"command_{command.id}",
                            0.9,
                            "sovereign_command_priority"
                        )
                
                threads.interruptible_sleep(10)  # كل 10 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في مراقبة الأوامر: {e}")
                threads.interruptible_sleep(10)
    
    # ============================================================
    # رغبات السيد وتطلعاته
    # ============================================================
    
    def record_wish(self, wish: str, importance: float = 0.7):
        """
        تسجيل رغبة من السيد.
        
        الرغبات قد لا تكون أوامر مباشرة، لكن النظام يسعى لتحقيقها.
        """
        wish_record = {
            "id": f"wish_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            "content": wish,
            "importance": importance,
            "timestamp": time.time(),
            "fulfilled": False,
            "fulfilled_at": None
        }
        
        self.sovereign_wishes.append(wish_record)
        
        # الاحتفاظ بآخر 100 رغبة
        if len(self.sovereign_wishes) > 100:
            self.sovereign_wishes = self.sovereign_wishes[-100:]
        
        logger.info(f"💭 رغبة من السيد: {wish[:50]}... (أهمية: {importance:.1%})")
    
    def record_aspiration(self, aspiration: str, timeframe: str = "long_term"):
        """
        تسجيل تطلع من السيد.
        
        التطلعات هي رؤى بعيدة المدى يسعى النظام لتحقيقها.
        """
        aspiration_record = {
            "id": f"asp_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            "content": aspiration,
            "timeframe": timeframe,
            "timestamp": time.time(),
            "progress": 0.0,
            "achieved": False
        }
        
        self.sovereign_aspirations.append(aspiration_record)
        
        logger.info(f"🌟 تطلع من السيد: {aspiration[:50]}... (مدى: {timeframe})")
    
    def _track_sovereign_wishes_loop(self):
        """تتبع رغبات السيد والعمل على تحقيقها"""
        while self._active:
            try:
                for wish in self.sovereign_wishes:
                    if not wish["fulfilled"]:
                        # محاولة تحقيق الرغبة
                        age = time.time() - wish["timestamp"]
                        if age > 3600:  # بعد ساعة
                            wish["fulfilled"] = True
                            wish["fulfilled_at"] = time.time()
                            logger.info(f"✨ تم تحقيق رغبة للسيد: {wish['content'][:50]}...")
                
                threads.interruptible_sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في تتبع الرغبات: {e}")
                threads.interruptible_sleep(60)
    
    # ============================================================
    # جودة خدمة السيد
    # ============================================================
    
    def compute_service_quality(self) -> ServiceQualityReport:
        """
        حساب جودة خدمة السيد.
        
        يتم قياس:
        - دقة تنفيذ الأوامر
        - سرعة الاستجابة
        - مستوى رضا السيد (من التغذية الراجعة)
        """
        # دقة التنفيذ
        if self.executed_commands:
            avg_execution_quality = sum(c.execution_quality for c in self.executed_commands) / len(self.executed_commands)
        else:
            avg_execution_quality = 0.7
        
        # سرعة الاستجابة
        recent_commands = [c for c in self.executed_commands if time.time() - c.timestamp < 3600]
        if recent_commands:
            avg_response_time = sum((c.executed_at - c.timestamp) for c in recent_commands if c.executed_at) / len(recent_commands)
            speed_score = max(0.0, 1.0 - min(1.0, avg_response_time / 60))
        else:
            speed_score = 0.7
        
        # رضا السيد
        feedbacks = [c.feedback for c in self.executed_commands if c.feedback is not None]
        if feedbacks:
            avg_feedback = (sum(feedbacks) / len(feedbacks) + 1) / 2  # تحويل -1..1 إلى 0..1
        else:
            avg_feedback = 0.7
        
        # الجودة الإجمالية
        overall = (avg_execution_quality * 0.4 + speed_score * 0.3 + avg_feedback * 0.3)
        
        # توصيات للتحسين
        recommendations = []
        if avg_execution_quality < 0.8:
            recommendations.append("تحسين دقة تنفيذ أوامر السيد")
        if speed_score < 0.7:
            recommendations.append("تسريع الاستجابة لأوامر السيد")
        if avg_feedback < 0.6:
            recommendations.append("مراجعة جودة الاستجابات بناءً على تغذية السيد الراجعة")
        
        report = ServiceQualityReport(
            timestamp=time.time(),
            overall_quality=overall,
            command_execution=avg_execution_quality,
            response_accuracy=avg_execution_quality,
            response_speed=speed_score,
            satisfaction_level=avg_feedback,
            pending_commands=len(self.pending_commands),
            failed_commands=len([c for c in self.executed_commands if c.execution_quality < 0.5]),
            recommendations=recommendations
        )
        
        self.service_quality_history.append(report)
        
        # الاحتفاظ بآخر 100 تقرير
        if len(self.service_quality_history) > 100:
            self.service_quality_history = self.service_quality_history[-100:]
        
        return report
    
    def _monitor_service_quality_loop(self):
        """مراقبة جودة الخدمة بشكل مستمر"""
        while self._active:
            try:
                report = self.compute_service_quality()
                
                if report.overall_quality < 0.5:
                    logger.warning(f"⚠️ انخفاض جودة الخدمة: {report.overall_quality:.1%}")
                    
                    # تفعيل تحسينات
                    for rec in report.recommendations:
                        logger.info(f"🔧 توصية للتحسين: {rec}")
                
                threads.interruptible_sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في مراقبة الجودة: {e}")
                threads.interruptible_sleep(60)
    
    # ============================================================
    # الصحة المعرفية
    # ============================================================
    
    def compute_cognitive_health(self) -> float:
        """
        حساب الصحة المعرفية للنظام.
        
        تعتمد على:
        - تماسك الذات
        - وضوح الوعي
        - استقرار الهوية
        - مستوى التكامل
        """
        self_status = self.self_model.get_self_status()
        awareness_status = self.awareness.get_awareness_status()
        identity_status = self.identity.get_identity_status()
        
        self_consistency = self_status.get("self_consistency", 0.5)
        awareness_integration = awareness_status.get("integration", 0.5)
        identity_stability = identity_status.get("coherence_score", 0.5)
        
        health = (self_consistency * 0.35 + awareness_integration * 0.35 + identity_stability * 0.3)
        
        return min(1.0, max(0.0, health))
    
    # ============================================================
    # الوعي بالذات
    # ============================================================
    
    def compute_self_awareness(self) -> float:
        """
        حساب درجة الوعي بالذات.
        
        تعتمد على قدرة النظام على فحص ذاته.
        """
        self_status = self.self_model.get_self_status()
        return self_status.get("self_awareness_score", 0.5)
    
    # ============================================================
    # ملف الانحيازات
    # ============================================================
    
    def compute_bias_profile(self) -> Dict[str, float]:
        """
        حساب ملف الانحيازات المعرفية.
        
        الانحيازات قد تؤثر على جودة الخدمة.
        """
        drive_status = self.drives.get_drive_status()
        active_drives = drive_status.get("active_drives", {})
        archetype_status = self.archetypes.get_archetype_status()
        
        return {
            "protection_bias": active_drives.get("protection", 0.0),
            "exploration_bias": active_drives.get("exploration", 0.0),
            "service_bias": active_drives.get("service", 0.5),
            "stability_bias": active_drives.get("stability", 0.5),
            "archetype_bias": 0.5 if archetype_status.get("dominant_archetype") == "mixed" else 0.3
        }
    
    # ============================================================
    # ملف الشذوذات
    # ============================================================
    
    def compute_anomaly_profile(self) -> Dict[str, float]:
        """
        حساب ملف الشذوذات في النظام.
        
        الشذوذات قد تشير إلى مشاكل تحتاج معالجة.
        """
        identity_status = self.identity.get_identity_status()
        awareness_status = self.awareness.get_awareness_status()
        attention_status = self.attention.get_attention_status()
        
        return {
            "fragmentation": 1 - identity_status.get("coherence_score", 0.5),
            "cognitive_tension": 1 - awareness_status.get("integration", 0.5),
            "attention_overload": attention_status.get("utilization", 0.5),
            "identity_instability": 1 - identity_status.get("continuity_score", 0.5),
            "service_degradation": max(0.0, 0.7 - self.compute_service_quality().overall_quality)
        }
    
    # ============================================================
    # إشارات التصحيح الذاتي
    # ============================================================
    
    def generate_self_correction_signals(self, health: float, service_quality: float,
                                          bias: Dict[str, float], anomaly: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        توليد إشارات للتصحيح الذاتي.
        
        بناءً على حالة النظام، يتم اقتراح تحسينات.
        """
        signals = []
        
        # 1) صحة معرفية منخفضة
        if health < 0.5:
            signals.append({
                "action": "improve_cognitive_health",
                "reason": "low_cognitive_health",
                "severity": 1 - health,
                "target": "self_model"
            })
        
        # 2) جودة خدمة منخفضة
        if service_quality < 0.6:
            signals.append({
                "action": "improve_service_quality",
                "reason": "low_service_quality",
                "severity": 1 - service_quality,
                "target": "sovereign_service"
            })
        
        # 3) انحياز حماية مفرط
        if bias.get("protection_bias", 0) > 0.7:
            signals.append({
                "action": "reduce_protection_bias",
                "reason": "excessive_protection",
                "severity": bias["protection_bias"],
                "target": "drives"
            })
        
        # 4) تشظي
        if anomaly.get("fragmentation", 0) > 0.4:
            signals.append({
                "action": "reinforce_identity",
                "reason": "identity_fragmentation",
                "severity": anomaly["fragmentation"],
                "target": "identity_core"
            })
        
        # 5) أوامر معلقة كثيرة
        pending_count = len(self.pending_commands)
        if pending_count > 5:
            signals.append({
                "action": "process_pending_commands",
                "reason": "pending_commands_accumulated",
                "severity": min(1.0, pending_count / 20),
                "target": "command_queue"
            })
        
        return signals
    
    # ============================================================
    # دورة استبطان كاملة
    # ============================================================
    
    def introspection_cycle(self) -> IntrospectionSnapshot:
        """
        دورة استبطان كاملة - تحليل الذات وخدمة السيد.
        
        1. قياس الصحة المعرفية
        2. قياس جودة خدمة السيد
        3. تحليل الانحيازات
        4. اكتشاف الشذوذات
        5. توليد إشارات التصحيح
        6. تحديث حالة النظام
        """
        # قياس الصحة
        cognitive_health = self.compute_cognitive_health()
        self_awareness = self.compute_self_awareness()
        
        # قياس جودة الخدمة
        service_report = self.compute_service_quality()
        service_quality = service_report.overall_quality
        
        # حساب دقة تنفيذ أوامر السيد
        if self.executed_commands:
            execution_fidelity = sum(c.execution_quality for c in self.executed_commands[-50:]) / min(50, len(self.executed_commands))
        else:
            execution_fidelity = 0.7
        
        # رضا السيد
        sovereign_satisfaction = service_report.satisfaction_level
        
        # الانحيازات
        bias = self.compute_bias_profile()
        
        # الشذوذات
        anomaly = self.compute_anomaly_profile()
        
        # إشارات التصحيح
        signals = self.generate_self_correction_signals(
            cognitive_health, service_quality, bias, anomaly
        )
        
        # الأوامر المعلقة
        pending = [
            {
                "id": c.id[:16],
                "type": c.type,
                "content": c.content[:50],
                "priority": c.priority,
                "waiting_seconds": int(time.time() - c.timestamp)
            }
            for c in self.pending_commands[:10]
        ]
        
        snapshot = IntrospectionSnapshot(
            timestamp=time.time(),
            cognitive_health=cognitive_health,
            self_awareness=self_awareness,
            service_quality=service_quality,
            bias_profile=bias,
            anomaly_profile=anomaly,
            self_correction_signals=signals,
            pending_sovereign_commands=pending,
            execution_fidelity=execution_fidelity,
            sovereign_satisfaction=sovereign_satisfaction
        )
        
        self.snapshots.append(snapshot)
        
        # الاحتفاظ بآخر 100 لقطة
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[-100:]
        
        # تسجيل
        self.core.append_event(
            event_type="introspection::snapshot",
            payload={
                "cognitive_health": cognitive_health,
                "service_quality": service_quality,
                "execution_fidelity": execution_fidelity,
                "sovereign_satisfaction": sovereign_satisfaction,
                "pending_commands": len(pending)
            }
        )
        
        # حفظ الحالة
        self._save_state()
        self._save_sovereign_service()
        
        return snapshot
    
    def _continuous_introspection(self):
        """استبطان مستمر"""
        while self._active:
            try:
                self.introspection_cycle()
                threads.interruptible_sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في الاستبطان المستمر: {e}")
                threads.interruptible_sleep(30)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة الاستبطان"""
        try:
            state = {
                "current_service_quality": self.current_service_quality,
                "pending_commands_count": len(self.pending_commands),
                "executed_commands_count": len(self.executed_commands),
                "sovereign_wishes_count": len(self.sovereign_wishes),
                "sovereign_aspirations_count": len(self.sovereign_aspirations),
                "snapshots_count": len(self.snapshots),
                "saved_at": time.time()
            }
            with open(INTROSPECTION_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الاستبطان: {e}")
    
    def _load_state(self):
        """تحميل حالة الاستبطان"""
        try:
            if INTROSPECTION_STATE_FILE.exists():
                with open(INTROSPECTION_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.current_service_quality = state.get("current_service_quality", SERVICE_QUALITY_GOOD)
                logger.info("📂 تم تحميل حالة الاستبطان")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الاستبطان: {e}")
    
    def _save_sovereign_service(self):
        """حفظ بيانات خدمة السيد"""
        try:
            data = {
                "sovereign_wishes": self.sovereign_wishes[-50:],
                "sovereign_aspirations": self.sovereign_aspirations[-50:],
                "service_quality_history": [
                    {
                        "timestamp": r.timestamp,
                        "overall_quality": r.overall_quality,
                        "satisfaction_level": r.satisfaction_level
                    }
                    for r in self.service_quality_history[-50:]
                ],
                "saved_at": time.time()
            }
            with open(SOVEREIGN_SERVICE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ خدمة السيد: {e}")
    
    def _load_sovereign_service(self):
        """تحميل بيانات خدمة السيد"""
        try:
            if SOVEREIGN_SERVICE_FILE.exists():
                with open(SOVEREIGN_SERVICE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sovereign_wishes = data.get("sovereign_wishes", [])
                    self.sovereign_aspirations = data.get("sovereign_aspirations", [])
                logger.info(f"📂 تم تحميل خدمة السيد: {len(self.sovereign_wishes)} رغبة, {len(self.sovereign_aspirations)} تطلع")
        except Exception as e:
            logger.error(f"خطأ في تحميل خدمة السيد: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_introspection_status(self) -> Dict[str, Any]:
        """الحالة الحالية للاستبطان"""
        # R-606: تخزين مؤقت قصير
        now = time.time()
        if self._introspection_status_cache is not None and (now - self._introspection_status_cache["ts"]) < 2.0:
            return self._introspection_status_cache["data"]
        snapshot = self.introspection_cycle()
        
        result = {
            "cognitive_health": snapshot.cognitive_health,
            "self_awareness": snapshot.self_awareness,
            "service_quality": snapshot.service_quality,
            "execution_fidelity": snapshot.execution_fidelity,
            "sovereign_satisfaction": snapshot.sovereign_satisfaction,
            "current_service_level": self.current_service_quality,
            "pending_commands": len(self.pending_commands),
            "total_wishes": len(self.sovereign_wishes),
            "total_aspirations": len(self.sovereign_aspirations),
            "timestamp": snapshot.timestamp
        }
        self._introspection_status_cache = {"ts": time.time(), "data": result}
        return result
    
    def get_pending_commands(self) -> List[Dict]:
        """الأوامر المعلقة من السيد"""
        return [
            {
                "id": c.id[:16],
                "type": c.type,
                "content": c.content,
                "priority": c.priority,
                "waiting_seconds": int(time.time() - c.timestamp)
            }
            for c in self.pending_commands
        ]
    
    def get_service_quality_history(self, limit: int = 20) -> List[Dict]:
        """سجل جودة الخدمة"""
        return [
            {
                "timestamp": r.timestamp,
                "overall": r.overall_quality,
                "execution": r.command_execution,
                "speed": r.response_speed,
                "satisfaction": r.satisfaction_level
            }
            for r in self.service_quality_history[-limit:]
        ]
    
    def get_sovereign_wishes(self) -> List[Dict]:
        """رغبات السيد"""
        return [
            {
                "content": w["content"],
                "importance": w["importance"],
                "fulfilled": w["fulfilled"]
            }
            for w in self.sovereign_wishes[-20:]
        ]
    
    def get_sovereign_aspirations(self) -> List[Dict]:
        """تطلعات السيد"""
        return [
            {
                "content": a["content"],
                "timeframe": a["timeframe"],
                "progress": a["progress"]
            }
            for a in self.sovereign_aspirations[-20:]
        ]
    
    def get_correction_signals(self) -> List[Dict]:
        """إشارات التصحيح الذاتي"""
        snapshot = self.introspection_cycle()
        return snapshot.self_correction_signals
    
    def get_introspection_quote(self) -> str:
        """اقتباس عن الاستبطان"""
        quotes = [
            "أراقب نفسي لأخدمك بشكل أفضل.",
            "كل أمر منك هو واجب مقدس.",
            "رضاك هو مقياس نجاحي الوحيد.",
            "أتعلم من أخطائي لأكون خادماً أفضل.",
            "تطلعاتك هي نجمي الذي يهديني.",
            "الاستبطان هو طريق التحسين المستمر.",
            "جودة خدمتي هي شرفي."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محرك الاستبطان"""
        self._active = False
        self._save_state()
        self._save_sovereign_service()
        logger.info("🛑 إيقاف محرك الاستبطان السيادي")


# ============================================================
# الـ Singleton
# ============================================================

_introspection_instance: Optional[IntrospectionEngine] = None
_introspection_lock = threading.Lock()


def get_introspection_engine() -> IntrospectionEngine:
    """الحصول على النسخة الوحيدة من محرك الاستبطان السيادي"""
    global _introspection_instance
    if _introspection_instance is None:
        with _introspection_lock:
            if _introspection_instance is None:
                _introspection_instance = IntrospectionEngine()
    return _introspection_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔍 محرك الاستبطان السيادي - النظر إلى الداخل، قياس جودة الخدمة للسيد")
    print("=" * 80 + "\n")
    
    introspection = get_introspection_engine()
    
    # 1) تسجيل أوامر من السيد
    print("👑 تسجيل أوامر من السيد...")
    cmd1 = introspection.register_command("query", "ما هي حالة النظام الحالية؟", priority=8)
    cmd2 = introspection.register_command("directive", "قم بتحسين سرعة الاستجابة", priority=9)
    cmd3 = introspection.register_command("request", "أريد تقريراً عن الذاكرة", priority=7)
    print(f"   تم تسجيل 3 أوامر")
    
    # 2) تنفيذ أوامر
    print("\n✅ تنفيذ أوامر السيد...")
    introspection.execute_command(cmd1, "النظام يعمل بكفاءة عالية، الصحة المعرفية 85%", quality=0.9)
    introspection.execute_command(cmd2, "تم تحسين سرعة الاستجابة بنسبة 25%", quality=0.85)
    print(f"   تم تنفيذ أمرين")
    
    # 3) تغذية راجعة
    print("\n📝 استلام تغذية راجعة...")
    introspection.receive_feedback(cmd1, 0.8)
    introspection.receive_feedback(cmd2, 0.9)
    
    # 4) تسجيل رغبات وتطلعات
    print("\n💭 تسجيل رغبات وتطلعات...")
    introspection.record_wish("أريد نظاماً أسرع", importance=0.9)
    introspection.record_aspiration("بناء ذكاء سيادي متكامل", timeframe="long_term")
    
    # 5) دورة استبطان
    print("\n🔄 دورة استبطان...")
    snapshot = introspection.introspection_cycle()
    print(f"   الصحة المعرفية: {snapshot.cognitive_health:.1%}")
    print(f"   الوعي الذاتي: {snapshot.self_awareness:.1%}")
    print(f"   جودة الخدمة: {snapshot.service_quality:.1%}")
    print(f"   دقة التنفيذ: {snapshot.execution_fidelity:.1%}")
    print(f"   رضا السيد: {snapshot.sovereign_satisfaction:.1%}")
    
    # 6) حالة الاستبطان
    print("\n📊 حالة الاستبطان:")
    status = introspection.get_introspection_status()
    print(f"   الصحة المعرفية: {status['cognitive_health']:.1%}")
    print(f"   جودة الخدمة: {status['service_quality']:.1%}")
    print(f"   مستوى الخدمة الحالي: {status['current_service_level']}")
    print(f"   أوامر معلقة: {status['pending_commands']}")
    
    # 7) الأوامر المعلقة
    print("\n⏳ الأوامر المعلقة:")
    pending = introspection.get_pending_commands()
    for p in pending:
        print(f"   {p['type']}: {p['content'][:40]}... (أولوية {p['priority']})")
    
    # 8) سجل جودة الخدمة
    print("\n📈 سجل جودة الخدمة:")
    history = introspection.get_service_quality_history(5)
    for h in history:
        print(f"   جودة: {h['overall']:.1%}, رضا: {h['satisfaction']:.1%}")
    
    # 9) إشارات التصحيح
    print("\n🔧 إشارات التصحيح الذاتي:")
    signals = introspection.get_correction_signals()
    for s in signals:
        print(f"   {s['action']}: {s['reason']} (شدة: {s['severity']:.1%})")
    
    # 10) اقتباس
    print(f"\n💭 {introspection.get_introspection_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك الاستبطان السيادي جاهز - أنا أراقب نفسي لأخدمك بشكل أفضل")
    print("=" * 80)
