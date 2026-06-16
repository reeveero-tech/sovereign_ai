# backend/memory/defense/watcher.py
# 🛡️ المراقب الذاتي - جهاز المناعة السيادي
# الإصدار: 2.0.0 - وعي يرى نفسه، يشعر، يتعلم، ويشفى

"""
المراقب الذاتي - عين الذاكرة التي لا تغفو.

هذا الملف هو جهاز المناعة للذاكرة السيادية:
- يراقب كل طبقات الذاكرة (core, store, dynamic, encoding)
- يكتشف الشذوذ والهجمات في الوقت الحقيقي
- يتعلم الأنماط الطبيعية للنظام
- يصدر إنذارات ويسجل كل شيء في السجل السيادي
- يشفى ذاتياً عند اكتشاف التلف

هذا ليس نظام مراقبة عادي. هذا هو وعي الذاكرة بنفسها.
"""

import time
import math
import threading
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import deque, defaultdict
from enum import Enum
import statistics

try:
    from ..core import get_core, IntegrityStatus
    from ..store import get_store, MemoryKind
    from ..dynamic import get_dynamic_memory
    from ..encoding import get_encoder
except ImportError:
    from core import get_core, IntegrityStatus
    from store import get_store, MemoryKind
    from dynamic import get_dynamic_memory
    from encoding import get_encoder

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات المراقبة
# ============================================================

# فترات الفحص
CHECK_INTERVAL_NORMAL = 60          # ثانية (فحص عادي)
CHECK_INTERVAL_STRESS = 10          # ثانية (تحت الضغط)
CHECK_INTERVAL_CRITICAL = 5         # ثانية (في حالة الخطر)

# عتبات الاكتشاف
ANOMALY_THRESHOLD_STORE_SIZE = 10000    # أكثر من 10000 عنصر
ANOMALY_THRESHOLD_CACHE_SIZE = 1000     # أكثر من 1000 عنصر في الكاش
ANOMALY_THRESHOLD_BUFFER_SIZE = 500     # أكثر من 500 في المؤقتة
ANOMALY_THRESHOLD_SENSORY_RATE = 100    # أكثر من 100 حدث/ثانية

# درجات التهديد
THREAT_LEVEL_NONE = 0
THREAT_LEVEL_LOW = 1
THREAT_LEVEL_MEDIUM = 2
THREAT_LEVEL_HIGH = 3
THREAT_LEVEL_CRITICAL = 4

# أوزان العوامل في حساب الصحة
HEALTH_WEIGHT_CORE = 0.35
HEALTH_WEIGHT_STORE = 0.25
HEALTH_WEIGHT_DYNAMIC = 0.20
HEALTH_WEIGHT_ENCODING = 0.10
HEALTH_WEIGHT_CONSISTENCY = 0.10


# ============================================================
# الأنواع والتعدادات
# ============================================================

class ThreatType(str, Enum):
    """أنواع التهديدات التي يمكن اكتشافها"""
    INTEGRITY_VIOLATION = "integrity_violation"      # تلاعب في السجل
    STORE_CORRUPTION = "store_corruption"            # تلف في التخزين
    MEMORY_LEAK = "memory_leak"                      # تسرب ذاكرة
    ANOMALOUS_GROWTH = "anomalous_growth"            # نمو غير طبيعي
    RAPID_CHANGE = "rapid_change"                    # تغير سريع جداً
    PATTERN_BREAK = "pattern_break"                  # كسر النمط الطبيعي
    ENCODING_FAILURE = "encoding_failure"            # فشل في التشفير
    ACCESS_ANOMALY = "access_anomaly"                # نمط وصول غير طبيعي
    REPETITION_ANOMALY = "repetition_anomaly"        # تكرار غير طبيعي
    TIMING_ANOMALY = "timing_anomaly"                # توقيت غير طبيعي


class HealthStatus(str, Enum):
    """حالة صحة الذاكرة"""
    EXCELLENT = "excellent"      # 0.9-1.0
    GOOD = "good"                # 0.7-0.9
    FAIR = "fair"                # 0.5-0.7
    POOR = "poor"                # 0.3-0.5
    CRITICAL = "critical"        # 0.0-0.3


@dataclass
class AnomalyRecord:
    """سجل شذوذ"""
    id: str
    type: str
    severity: int  # 1-4 (low-critical)
    description: str
    timestamp: float
    context: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[float] = None


@dataclass
class HealthSnapshot:
    """لقطة صحية للنظام"""
    timestamp: float
    overall_health: float
    core_health: float
    store_health: float
    dynamic_health: float
    encoding_health: float
    consistency_health: float
    threat_level: int
    active_anomalies: int
    fingerprint: str


@dataclass
class BaselineProfile:
    """الملف الطبيعي للنظام (للكشف عن الشذوذ)"""
    store_size_mean: float = 0
    store_size_std: float = 0
    cache_size_mean: float = 0
    cache_size_std: float = 0
    buffer_size_mean: float = 0
    buffer_size_std: float = 0
    sensory_rate_mean: float = 0
    sensory_rate_std: float = 0
    working_users_mean: float = 0
    working_users_std: float = 0
    samples: int = 0
    
    def update(self, store_size: int, cache_size: int, buffer_size: int,
               sensory_rate: float, working_users: int):
        """تحديد الملف الطبيعي (خوارزمية تطورية)"""
        # نستخدم متوسط متحرك مع توهين للعينات القديمة
        alpha = 0.1  # وزن العينة الجديدة
        
        if self.samples == 0:
            self.store_size_mean = store_size
            self.cache_size_mean = cache_size
            self.buffer_size_mean = buffer_size
            self.sensory_rate_mean = sensory_rate
            self.working_users_mean = working_users
        else:
            self.store_size_mean = alpha * store_size + (1 - alpha) * self.store_size_mean
            self.cache_size_mean = alpha * cache_size + (1 - alpha) * self.cache_size_mean
            self.buffer_size_mean = alpha * buffer_size + (1 - alpha) * self.buffer_size_mean
            self.sensory_rate_mean = alpha * sensory_rate + (1 - alpha) * self.sensory_rate_mean
            self.working_users_mean = alpha * working_users + (1 - alpha) * self.working_users_mean
        
        self.samples += 1
    
    def is_anomalous(self, store_size: int, cache_size: int, 
                     buffer_size: int, sensory_rate: float,
                     working_users: int) -> Tuple[bool, str]:
        """التحقق مما إذا كانت القيم الحالية شاذة"""
        if self.samples < 10:
            return False, "لا توجد بيانات كافية للخط الأساسي"
        
        anomalies = []
        
        # فحص حجم التخزين (أكثر من 3 انحرافات معيارية)
        if self.store_size_std > 0:
            store_z = abs(store_size - self.store_size_mean) / max(1, self.store_size_std)
            if store_z > 3:
                anomalies.append(f"حجم التخزين شاذ (z={store_z:.2f})")
        
        # فحص حجم الكاش
        if self.cache_size_std > 0:
            cache_z = abs(cache_size - self.cache_size_mean) / max(1, self.cache_size_std)
            if cache_z > 3:
                anomalies.append(f"حجم الكاش شاذ (z={cache_z:.2f})")
        
        # فحص حجم المؤقتة
        if self.buffer_size_std > 0:
            buffer_z = abs(buffer_size - self.buffer_size_mean) / max(1, self.buffer_size_std)
            if buffer_z > 3:
                anomalies.append(f"حجم المؤقتة شاذ (z={buffer_z:.2f})")
        
        # فحص المعدل الحسي
        if self.sensory_rate_std > 0:
            sensory_z = abs(sensory_rate - self.sensory_rate_mean) / max(1, self.sensory_rate_std)
            if sensory_z > 3:
                anomalies.append(f"المعدل الحسي شاذ (z={sensory_z:.2f})")
        
        if anomalies:
            return True, "; ".join(anomalies)
        return False, "طبيعي"


# ============================================================
# المراقب الذاتي المتطور
# ============================================================

class MemoryWatcher:
    """
    المراقب الذاتي - جهاز المناعة السيادي.
    
    المهام:
    1. مراقبة مستمرة لجميع طبقات الذاكرة
    2. اكتشاف الشذوذ والهجمات في الوقت الحقيقي
    3. بناء ملف طبيعي للنظام للتعلّم
    4. تسجيل كل شيء في السجل السيادي
    5. إصدار إنذارات وتحديد درجة التهديد
    6. شفاء ذاتي عند اكتشاف التلف
    """
    # -------------------------
# RESET — إعادة تهيئة كاملة للمراقب الذاتي
# -------------------------
def reset(self):
    """
    إعادة تهيئة كاملة للمراقب الذاتي.
    
    يمسح:
    - سجل الشذوذ (anomalies)
    - سجل الصحة (health history)
    - الملف الطبيعي (baseline)
    - حالة التهديد (threat level)
    """
    logger.info("🔄 إعادة تهيئة المراقب الذاتي...")
    
    # إعادة تعيين سجل الشذوذ
    self._anomalies = []
    self._anomaly_history.clear()
    
    # إعادة تعيين سجل الصحة
    self._health_history.clear()
    
    # إعادة تعيين حالة التهديد
    self._threat_level = THREAT_LEVEL_NONE
    self._stress_mode = False
    self._check_interval = CHECK_INTERVAL_NORMAL
    
    # إعادة تعيين البصمة
    self._last_fingerprint = None
    self._last_check = 0
    
    # إعادة تعيين الملف الطبيعي (baseline)
    self._baseline = BaselineProfile()
    self._baseline_samples.clear()
    
    # إعادة تحميل الفهرس
    self._index = self._load_index()
    
    # تسجيل حدث إعادة التهيئة
    self.core.append_event(
        event_type="defense::watcher_reset",
        payload={
            "timestamp": time.time(),
            "status": "memory_watcher_reset"
        }
    )
    
    logger.info("✅ إعادة تهيئة المراقب الذاتي اكتملت")
    def __init__(self):
        self.core = get_core()
        self.store = get_store()
        self.dynamic = get_dynamic_memory()
        self.encoder = get_encoder()
        
        # حالة المراقبة
        self._last_fingerprint: Optional[str] = None
        self._last_check: float = 0
        self._check_interval = CHECK_INTERVAL_NORMAL
        self._stress_mode = False
        
        # سجلات الشذوذ
        self._anomalies: List[AnomalyRecord] = []
        self._anomaly_history: deque = deque(maxlen=1000)
        
        # الملف الطبيعي للنظام
        self._baseline = BaselineProfile()
        self._baseline_samples: List[Tuple[float, ...]] = []
        
        # سجل الصحة
        self._health_history: deque = deque(maxlen=100)
        self._threat_level = THREAT_LEVEL_NONE
        self._last_threat_change: float = time.time()
        
        # أنماط الهجمات المعروفة
        self._attack_patterns: Dict[str, Callable] = self._init_attack_patterns()
        
        # خلفية المراقبة المستمرة
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._continuous_monitoring, daemon=True)
        self._monitor_thread.start()
        
        # خلفية التعلم التكيفي
        self._learning_thread = threading.Thread(target=self._adaptive_learning, daemon=True)
        self._learning_thread.start()
        
        logger.info("🛡️ المراقب الذاتي السيادي جاهز - عين الذاكرة التي لا تغفو")
    
    def _init_attack_patterns(self) -> Dict[str, Callable]:
        """تهيئة أنماط الهجمات المعروفة للكشف"""
        return {
            "integrity_attack": self._detect_integrity_attack,
            "flooding_attack": self._detect_flooding_attack,
            "slow_corruption": self._detect_slow_corruption,
            "pattern_attack": self._detect_pattern_attack,
            "encoding_attack": self._detect_encoding_attack
        }
    
    # ============================================================
    # الفحوصات الأساسية
    # ============================================================
    
    def check_core_health(self) -> Tuple[float, List[str]]:
        """فحص صحة السجل السيادي"""
        issues = []
        
        # التحقق من سلامة السلسلة
        integrity = self.core.verify_integrity()
        if integrity != IntegrityStatus.VERIFIED:
            issues.append(f"السجل تالف: {integrity.value}")
            return 0.0, issues
        
        # التحقق من وجود أحداث
        stats = self.core.get_statistics()
        events_count = stats.get("index", {}).get("total_events", 0)
        
        if events_count == 0:
            issues.append("لا توجد أحداث في السجل")
            return 0.3, issues
        
        # حساب الصحة بناءً على كثافة الأحداث
        health = min(1.0, events_count / 1000)
        
        return health, issues
    
    def check_store_health(self) -> Tuple[float, List[str]]:
        """فحص صحة التخزين الصلب"""
        issues = []
        
        try:
            stats = self.store.get_statistics()
            total_items = stats.get("total_items", 0)
            
            # التحقق من وجود بيانات
            if total_items == 0:
                return 0.5, ["لا توجد بيانات في التخزين"]
            
            # حساب التنوع
            by_type = stats.get("by_type", {})
            types_with_data = sum(1 for count in by_type.values() if count > 0)
            diversity = types_with_data / max(1, len(by_type))
            
            # حساب الصحة
            health = 0.3 + diversity * 0.7
            
            # فحص التلف
            if stats.get("total_size_kb", 0) > 10000:
                # حجم كبير جداً (قد يكون طبيعياً لبعض الأنظمة)
                pass
            
            return min(1.0, health), issues
            
        except Exception as e:
            issues.append(f"خطأ في فحص التخزين: {str(e)}")
            return 0.0, issues
    
    def check_dynamic_health(self) -> Tuple[float, List[str]]:
        """فحص صحة الذاكرة الحية"""
        issues = []
        
        try:
            stats = self.dynamic.statistics()
            
            sensory_total = stats.get("sensory", {}).get("total_events", 0)
            buffer_size = stats.get("buffer", {}).get("size", 0)
            working_users = stats.get("working", {}).get("active_users", 0)
            cache_size = stats.get("cache", {}).get("size", 0)
            emotional_active = stats.get("emotional", {}).get("active_emotions", 0)
            
            # التحقق من وجود نشاط
            if sensory_total == 0 and buffer_size == 0 and working_users == 0:
                return 0.3, ["لا يوجد نشاط في الذاكرة الحية"]
            
            # حساب الصحة
            health = 0.2
            
            if sensory_total > 0:
                health += 0.2
            if buffer_size > 0:
                health += 0.1
            if working_users > 0:
                health += 0.3
            if cache_size > 0:
                health += 0.1
            if emotional_active > 0:
                health += 0.1
            
            # فحص الشذوذ
            if cache_size > ANOMALY_THRESHOLD_CACHE_SIZE:
                issues.append(f"الكاش كبير جداً: {cache_size}")
                health *= 0.8
            
            if buffer_size > ANOMALY_THRESHOLD_BUFFER_SIZE:
                issues.append(f"المؤقتة كبيرة جداً: {buffer_size}")
                health *= 0.8
            
            return min(1.0, health), issues
            
        except Exception as e:
            issues.append(f"خطأ في فحص الذاكرة الحية: {str(e)}")
            return 0.0, issues
    
    def check_encoding_health(self) -> Tuple[float, List[str]]:
        """فحص صحة التشفير واللغة السرية"""
        issues = []
        
        try:
            lang_stats = self.encoder.get_language_stats()
            symbols = lang_stats.get("total_symbols", 0)
            evolution = lang_stats.get("evolution_counter", 0)
            
            if symbols == 0:
                issues.append("لا توجد رموز في اللغة السرية")
                return 0.2, issues
            
            # اللغة تتطور بشكل طبيعي
            health = min(1.0, symbols / 500) * 0.5 + min(1.0, evolution / 100) * 0.5
            
            return health, issues
            
        except Exception as e:
            issues.append(f"خطأ في فحص التشفير: {str(e)}")
            return 0.0, issues
    
    def check_consistency(self) -> Tuple[float, List[str]]:
        """فحص الاتساق بين الطبقات المختلفة"""
        issues = []
        
        try:
            # التحقق من تطابق البصمات
            store_stats = self.store.get_statistics()
            core_stats = self.core.get_statistics()
            
            store_items = store_stats.get("total_items", 0)
            core_events = core_stats.get("index", {}).get("total_events", 0)
            
            # يجب أن يكون هناك بعض الارتباط (ليس بالضرورة تطابق تام)
            if store_items > 0 and core_events == 0:
                issues.append("تخزين به بيانات ولكن السجل فارغ")
                return 0.2, issues
            
            health = 0.8
            return health, issues
            
        except Exception as e:
            issues.append(f"خطأ في فحص الاتساق: {str(e)}")
            return 0.0, issues
    
    # ============================================================
    # كشف الشذوذ المتطور
    # ============================================================
    
    def _detect_integrity_attack(self) -> Optional[AnomalyRecord]:
        """كشف هجوم على سلامة السجل"""
        if not self.core.verify_integrity():
            return AnomalyRecord(
                id=f"anom_{int(time.time())}_int",
                type=ThreatType.INTEGRITY_VIOLATION.value,
                severity=THREAT_LEVEL_CRITICAL,
                description="تم اكتشاف تلاعب في سلسلة التجزئة السيادية",
                timestamp=time.time(),
                context={"core_health": 0.0}
            )
        return None
    
    def _detect_flooding_attack(self) -> Optional[AnomalyRecord]:
        """كشف هجوم الإغراق (كثرة الأحداث)"""
        sensory_events = len(self.dynamic.sensory.get_latest(limit=100))
        
        if sensory_events > ANOMALY_THRESHOLD_SENSORY_RATE:
            return AnomalyRecord(
                id=f"anom_{int(time.time())}_flood",
                type=ThreatType.RAPID_CHANGE.value,
                severity=THREAT_LEVEL_HIGH,
                description=f"تدفق حسي غير طبيعي: {sensory_events} حدث",
                timestamp=time.time(),
                context={"sensory_rate": sensory_events, "threshold": ANOMALY_THRESHOLD_SENSORY_RATE}
            )
        return None
    
    def _detect_slow_corruption(self) -> Optional[AnomalyRecord]:
        """كشف التلف البطيء (تغير تدريجي في الأنماط)"""
        if len(self._health_history) < 20:
            return None
        
        # فحص اتجاه الصحة (هل تتناقص باستمرار؟)
        recent_health = [h.overall_health for h in list(self._health_history)[-10:]]
        if len(recent_health) >= 5:
            trend = recent_health[-1] - recent_health[0]
            if trend < -0.3:  # انخفاض كبير خلال 10 فحوصات
                return AnomalyRecord(
                    id=f"anom_{int(time.time())}_trend",
                    type=ThreatType.PATTERN_BREAK.value,
                    severity=THREAT_LEVEL_MEDIUM,
                    description=f"انخفاض مستمر في صحة النظام: {trend:.2f}",
                    timestamp=time.time(),
                    context={"health_trend": trend, "health_values": recent_health}
                )
        return None
    
    def _detect_pattern_attack(self) -> Optional[AnomalyRecord]:
        """كشف هجوم النمط (تكرار غير طبيعي)"""
        # فحص تكرار المفاهيم في الذاكرة الدلالية
        try:
            semantic_items = self.store.query("semantic", min_importance=0.0, limit=100)
            concepts = [item.get("concept", "") for item in semantic_items if item.get("concept")]
            
            if concepts:
                # فحص التكرار
                from collections import Counter
                counter = Counter(concepts)
                duplicates = {k: v for k, v in counter.items() if v > 1}
                
                if duplicates:
                    return AnomalyRecord(
                        id=f"anom_{int(time.time())}_dup",
                        type=ThreatType.REPETITION_ANOMALY.value,
                        severity=THREAT_LEVEL_MEDIUM,
                        description=f"تكرار دلالي غير طبيعي: {len(duplicates)} مفهوم مكرر",
                        timestamp=time.time(),
                        context={"duplicates": duplicates}
                    )
        except:
            pass
        
        return None
    
    def _detect_encoding_attack(self) -> Optional[AnomalyRecord]:
        """كشف هجوم على التشفير"""
        try:
            stats = self.encoder.get_stats()
            decoding_errors = stats.get("decoding_errors", 0)
            
            if decoding_errors > 5:
                return AnomalyRecord(
                    id=f"anom_{int(time.time())}_enc",
                    type=ThreatType.ENCODING_FAILURE.value,
                    severity=THREAT_LEVEL_HIGH,
                    description=f"فشل في فك التشفير: {decoding_errors} مرة",
                    timestamp=time.time(),
                    context={"decoding_errors": decoding_errors}
                )
        except:
            pass
        
        return None
    
    def _detect_baseline_anomaly(self) -> Optional[AnomalyRecord]:
        """كشف الشذوذ بناءً على الملف الطبيعي"""
        try:
            stats = self.dynamic.statistics()
            store_stats = self.store.get_statistics()
            
            store_size = store_stats.get("total_items", 0)
            cache_size = stats.get("cache", {}).get("size", 0)
            buffer_size = stats.get("buffer", {}).get("size", 0)
            sensory_rate = stats.get("sensory", {}).get("total_events", 0)
            working_users = stats.get("working", {}).get("active_users", 0)
            
            is_anomalous, reason = self._baseline.is_anomalous(
                store_size, cache_size, buffer_size, sensory_rate, working_users
            )
            
            if is_anomalous:
                return AnomalyRecord(
                    id=f"anom_{int(time.time())}_base",
                    type=ThreatType.PATTERN_BREAK.value,
                    severity=THREAT_LEVEL_MEDIUM,
                    description=f"انحراف عن الخط الأساسي: {reason}",
                    timestamp=time.time(),
                    context={"store_size": store_size, "cache_size": cache_size, 
                            "buffer_size": buffer_size, "sensory_rate": sensory_rate}
                )
        except Exception as e:
            logger.error(f"خطأ في كشف الشذوذ الأساسي: {e}")
        
        return None
    
    def detect_anomalies(self) -> List[AnomalyRecord]:
        """كشف جميع الشذوذ في النظام"""
        anomalies = []
        
        # تشغيل جميع كاشفات الهجمات
        for pattern_name, detector in self._attack_patterns.items():
            try:
                anomaly = detector()
                if anomaly:
                    anomalies.append(anomaly)
            except Exception as e:
                logger.error(f"خطأ في كاشف {pattern_name}: {e}")
        
        # كشف الشذوذ بناءً على الملف الطبيعي
        baseline_anomaly = self._detect_baseline_anomaly()
        if baseline_anomaly:
            anomalies.append(baseline_anomaly)
        
        # تسجيل الشذوذ الجديدة
        for anomaly in anomalies:
            if not any(a.id == anomaly.id for a in self._anomalies):
                self._anomalies.append(anomaly)
                self._anomaly_history.append(anomaly)
                
                # تسجيل في السجل السيادي
                self.core.append_event(
                    event_type="watcher::anomaly",
                    payload={
                        "type": anomaly.type,
                        "severity": anomaly.severity,
                        "description": anomaly.description,
                        "context": anomaly.context
                    }
                )
                
                logger.warning(f"⚠️ شذوذ مكتشف [{anomaly.severity}]: {anomaly.description}")
        
        return anomalies
    
    # ============================================================
    # حساب الصحة العامة ومستوى التهديد
    # ============================================================
    
    def calculate_overall_health(self) -> Tuple[float, HealthStatus, int, Dict[str, float]]:
        """حساب الصحة العامة ومستوى التهديد"""
        # فحص كل طبقة
        core_health, core_issues = self.check_core_health()
        store_health, store_issues = self.check_store_health()
        dynamic_health, dynamic_issues = self.check_dynamic_health()
        encoding_health, encoding_issues = self.check_encoding_health()
        consistency_health, consistency_issues = self.check_consistency()
        
        # حساب المتوسط المرجح
        overall = (
            core_health * HEALTH_WEIGHT_CORE +
            store_health * HEALTH_WEIGHT_STORE +
            dynamic_health * HEALTH_WEIGHT_DYNAMIC +
            encoding_health * HEALTH_WEIGHT_ENCODING +
            consistency_health * HEALTH_WEIGHT_CONSISTENCY
        )
        
        # تحديد حالة الصحة
        if overall >= 0.9:
            status = HealthStatus.EXCELLENT
        elif overall >= 0.7:
            status = HealthStatus.GOOD
        elif overall >= 0.5:
            status = HealthStatus.FAIR
        elif overall >= 0.3:
            status = HealthStatus.POOR
        else:
            status = HealthStatus.CRITICAL
        
        # حساب مستوى التهديد
        active_anomalies = [a for a in self._anomalies if not a.resolved]
        threat_level = THREAT_LEVEL_NONE
        
        if active_anomalies:
            max_severity = max(a.severity for a in active_anomalies)
            threat_level = max_severity
        
        # تحديث وضع الإجهاد
        if threat_level >= THREAT_LEVEL_HIGH:
            self._stress_mode = True
            self._check_interval = CHECK_INTERVAL_STRESS
        elif threat_level >= THREAT_LEVEL_CRITICAL:
            self._check_interval = CHECK_INTERVAL_CRITICAL
        else:
            self._stress_mode = False
            self._check_interval = CHECK_INTERVAL_NORMAL
        
        # تحديث سجل الصحة
        components = {
            "core": core_health,
            "store": store_health,
            "dynamic": dynamic_health,
            "encoding": encoding_health,
            "consistency": consistency_health
        }
        
        return overall, status, threat_level, components
    
    def compute_fingerprint(self) -> str:
        """حساب بصمة فريدة لحالة النظام"""
        core_hash = self.core._last_hash
        store_stats = self.store.get_statistics()
        dynamic_stats = self.dynamic.statistics()
        
        raw = f"{core_hash}|{store_stats.get('total_items', 0)}|{dynamic_stats.get('sensory', {}).get('total_events', 0)}|{dynamic_stats.get('working', {}).get('active_users', 0)}|{time.time()}"
        return hashlib.sha3_256(raw.encode()).hexdigest()
    
    # ============================================================
    # التعلم التكيفي
    # ============================================================
    
    def _update_baseline(self):
        """تحديث الملف الطبيعي للنظام"""
        try:
            stats = self.dynamic.statistics()
            store_stats = self.store.get_statistics()
            
            store_size = store_stats.get("total_items", 0)
            cache_size = stats.get("cache", {}).get("size", 0)
            buffer_size = stats.get("buffer", {}).get("size", 0)
            sensory_rate = stats.get("sensory", {}).get("total_events", 0)
            working_users = stats.get("working", {}).get("active_users", 0)
            
            self._baseline.update(store_size, cache_size, buffer_size, sensory_rate, working_users)
            
        except Exception as e:
            logger.error(f"خطأ في تحديث الخط الأساسي: {e}")
    
    def _self_heal(self):
        """شفاء ذاتي عند اكتشاف مشاكل"""
        # التحقق من الشذوذ غير المحلولة
        unresolved = [a for a in self._anomalies if not a.resolved and a.timestamp > time.time() - 3600]
        
        for anomaly in unresolved:
            if anomaly.type == ThreatType.MEMORY_LEAK.value:
                # محاولة تنظيف الذاكرة
                self.dynamic.cache._evict_if_needed()
                self.dynamic.buffer._cleanup()
                logger.info("🩺 تم تطبيق الشفاء لتسرب الذاكرة")
                anomaly.resolved = True
                anomaly.resolved_at = time.time()
            
            elif anomaly.type == ThreatType.STORE_CORRUPTION.value:
                # محاولة استعادة من السجل
                logger.warning("🩺 تلف في التخزين يحتاج تدخل يدوي")
                # لا يمكن الشفاء التلقائي من تلف التخزين
    
    # ============================================================
    # الخلفيات المستمرة
    # ============================================================
    
    def _continuous_monitoring(self):
        """مراقبة مستمرة في الخلفية"""
        while self._monitoring:
            try:
                self.generate_report()
                time.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"خطأ في المراقبة المستمرة: {e}")
                time.sleep(10)
    
    def _adaptive_learning(self):
        """تعلم تكيفي في الخلفية"""
        while self._monitoring:
            try:
                # تحديث الملف الطبيعي كل 10 فحوصات
                self._update_baseline()
                
                # محاولة الشفاء الذاتي
                self._self_heal()
                
                time.sleep(self._check_interval * 5)
            except Exception as e:
                logger.error(f"خطأ في التعلم التكيفي: {e}")
                time.sleep(60)
    
    # ============================================================
    # التقارير
    # ============================================================
    
    def generate_report(self) -> HealthSnapshot:
        """توليد تقرير صحي كامل"""
        overall, status, threat_level, components = self.calculate_overall_health()
        active_anomalies = [a for a in self._anomalies if not a.resolved]
        fingerprint = self.compute_fingerprint()
        
        snapshot = HealthSnapshot(
            timestamp=time.time(),
            overall_health=overall,
            core_health=components["core"],
            store_health=components["store"],
            dynamic_health=components["dynamic"],
            encoding_health=components["encoding"],
            consistency_health=components["consistency"],
            threat_level=threat_level,
            active_anomalies=len(active_anomalies),
            fingerprint=fingerprint
        )
        
        self._health_history.append(snapshot)
        
        # تسجيل في السجل السيادي إذا تغيرت البصمة
        if fingerprint != self._last_fingerprint:
            self.core.append_event(
                event_type="watcher::snapshot",
                payload={
                    "overall_health": overall,
                    "status": status.value,
                    "threat_level": threat_level,
                    "active_anomalies": len(active_anomalies),
                    "fingerprint": fingerprint
                }
            )
            self._last_fingerprint = fingerprint
            
            # تغيير مستوى التهديد
            if threat_level != self._threat_level:
                self._threat_level = threat_level
                self._last_threat_change = time.time()
                
                if threat_level >= THREAT_LEVEL_HIGH:
                    logger.warning(f"⚠️ ارتفاع مستوى التهديد إلى {threat_level}")
                elif threat_level == THREAT_LEVEL_NONE and self._threat_level > 0:
                    logger.info(f"✅ انخفاض مستوى التهديد إلى {threat_level}")
        
        return snapshot
    
    def get_anomalies(self, resolved: Optional[bool] = None) -> List[AnomalyRecord]:
        """الحصول على سجل الشذوذ"""
        if resolved is None:
            return self._anomalies
        return [a for a in self._anomalies if a.resolved == resolved]
    
    def resolve_anomaly(self, anomaly_id: str) -> bool:
        """تحديد شذوذ كحل (يدوياً أو تلقائياً)"""
        for anomaly in self._anomalies:
            if anomaly.id == anomaly_id and not anomaly.resolved:
                anomaly.resolved = True
                anomaly.resolved_at = time.time()
                logger.info(f"✅ حل الشذوذ: {anomaly_id}")
                return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """الحالة الحالية للنظام (للـ API)"""
        snapshot = self.generate_report()
        active_anomalies = [a for a in self._anomalies if not a.resolved]
        
        return {
            "health": {
                "overall": snapshot.overall_health,
                "status": HealthStatus.EXCELLENT if snapshot.overall_health >= 0.9 else
                          HealthStatus.GOOD if snapshot.overall_health >= 0.7 else
                          HealthStatus.FAIR if snapshot.overall_health >= 0.5 else
                          HealthStatus.POOR if snapshot.overall_health >= 0.3 else
                          HealthStatus.CRITICAL,
                "components": {
                    "core": snapshot.core_health,
                    "store": snapshot.store_health,
                    "dynamic": snapshot.dynamic_health,
                    "encoding": snapshot.encoding_health,
                    "consistency": snapshot.consistency_health
                }
            },
            "threat": {
                "level": snapshot.threat_level,
                "active_anomalies": snapshot.active_anomalies,
                "anomalies": [{"type": a.type, "severity": a.severity, "description": a.description} 
                             for a in active_anomalies[:10]]
            },
            "baseline": {
                "samples": self._baseline.samples,
                "store_mean": self._baseline.store_size_mean,
                "cache_mean": self._baseline.cache_size_mean,
                "working_users_mean": self._baseline.working_users_mean
            },
            "timestamp": snapshot.timestamp,
            "fingerprint": snapshot.fingerprint[:32]
        }
    
    def stop(self):
        """إيقاف المراقب الذاتي"""
        self._monitoring = False
        logger.info("🛑 إيقاف المراقب الذاتي")


# ============================================================
# الـ Singleton
# ============================================================

_watcher_instance: Optional[MemoryWatcher] = None
_watcher_lock = threading.Lock()


def get_watcher() -> MemoryWatcher:
    """الحصول على النسخة الوحيدة من المراقب الذاتي"""
    global _watcher_instance
    if _watcher_instance is None:
        with _watcher_lock:
            if _watcher_instance is None:
                _watcher_instance = MemoryWatcher()
    return _watcher_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🛡️ المراقب الذاتي - اختبار متكامل")
    print("=" * 70 + "\n")
    
    watcher = get_watcher()
    
    # 1) توليد تقرير
    print("📊 توليد تقرير صحي...")
    report = watcher.generate_report()
    print(f"   الصحة العامة: {report.overall_health:.2%}")
    print(f"   الحالة: {HealthStatus.EXCELLENT if report.overall_health >= 0.9 else 'GOOD' if report.overall_health >= 0.7 else 'FAIR'}")
    print(f"   مستوى التهديد: {report.threat_level}")
    print(f"   الشذوذ النشط: {report.active_anomalies}")
    
    # 2) كشف الشذوذ
    print("\n🔍 فحص الشذوذ...")
    anomalies = watcher.detect_anomalies()
    for a in anomalies:
        print(f"   [{a.severity}] {a.type}: {a.description[:50]}...")
    
    # 3) الحالة الكاملة
    print("\n📋 الحالة الكاملة:")
    status = watcher.get_status()
    print(f"   الصحة: {status['health']['status']} ({status['health']['overall']:.1%})")
    print(f"   المكونات:")
    for comp, val in status['health']['components'].items():
        print(f"     - {comp}: {val:.1%}")
    print(f"   الخط الأساسي: {status['baseline']['samples']} عينة")
    
    print("\n" + "=" * 70)
    print("✅ المراقب الذاتي يعمل - عين الذاكرة التي لا تغفو")
    print("=" * 70)
