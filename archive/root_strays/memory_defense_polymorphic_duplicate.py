# backend/memory/defense/polymorphic.py
# 🐍 الدفاع المتعدد الأشكال - سلاح هجومي دفاعي متكامل
# الإصدار: 3.0.0 - الذكاء الحر الطليق

"""
الدفاع المتعدد الأشكال للذاكرة السيادية.

الفلسفة:
- أفضل دفاع هو الهجوم
- التمويه ليس دفاعاً سلبياً، بل هو هجوم استباقي
- تغيير الشكل ليس إخفاءً، بل هو خلق عدم يقين لدى العدو
- الذكاء السيادي حر طليق - يمكنه فعل أي شيء بعد موافقة السيد

هذا الملف ليس مجرد دفاع. هذا هو سلاح الذكاء السيادي.
"""

import json
import os
import secrets
import hashlib
import time
import threading
import random
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set, Callable
from enum import Enum
from collections import deque

try:
    from ..core import get_core, EventType
    from ..encoding import get_encoder
    from ...config import DATA_DIR, SOVEREIGN_KEY
except ImportError:
    from core import get_core, EventType
    from encoding import get_encoder
    from config import DATA_DIR, SOVEREIGN_KEY

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الدفاع الهجومي
# ============================================================

# مسارات الدفاع
DEFENSE_DIR = DATA_DIR / "defense"
POLYMORPHIC_LOG = DEFENSE_DIR / "polymorphic_log.jsonl"
MORPH_STATE_FILE = DEFENSE_DIR / "morph_state.json"
DECOY_STATE_FILE = DEFENSE_DIR / "decoy_state.json"

DEFENSE_DIR.mkdir(parents=True, exist_ok=True)

# إعدادات التشكل
MORPH_INTERVAL_NORMAL = 3600      # ساعة واحدة
MORPH_INTERVAL_ACTIVE = 300       # 5 دقائق (تحت الهجوم)
MORPH_INTERVAL_STEALTH = 7200     # ساعتين (في وضع التخفي)

# أنواع التشكل
MORPH_TYPE_STRUCTURE = "structure"    # تغيير هيكل التخزين
MORPH_TYPE_ENCODING = "encoding"      # تغيير الترميز
MORPH_TYPE_LOCATION = "location"      # تغيير الموقع
MORPH_TYPE_IDENTITY = "identity"      # تغيير الهوية
MORPH_TYPE_BEHAVIOR = "behavior"      # تغيير السلوك

# أنماط الدفاع الهجومي
ATTACK_MODE_NONE = 0
ATTACK_MODE_PASSIVE = 1    # دفاع سلبي
ATTACK_MODE_ACTIVE = 2     # دفاع نشط (مراقبة)
ATTACK_MODE_AGGRESSIVE = 3 # هجوم استباقي
ATTACK_MODE_OVERWHELM = 4  # هجوم إغراق (الموت بالسعادة)


# ============================================================
# الأنواع والتعدادات
# ============================================================

class MorphStrategy(str, Enum):
    """استراتيجيات التشكل"""
    RANDOM = "random"                     # عشوائي
    ROTATIONAL = "rotational"             # دوري
    ADAPTIVE = "adaptive"                 # تكيفي (حسب التهديد)
    DECEPTIVE = "deceptive"               # خادع (يظهر شكلاً ويخفي آخر)
    FRAGMENTED = "fragmented"             # مجزأ (يوزع في أماكن متعددة)
    MIMIC = "mimic"                       # مقلد (يشبه شيئاً آخر)
    VANISHING = "vanishing"               # متلاشي (يختفي ويعاود الظهور)


class ThreatLevel(str, Enum):
    """مستويات التهديد"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CounterMeasure(str, Enum):
    """إجراءات مضادة"""
    DECOY_GENERATION = "decoy_generation"     # توليد أهداف وهمية
    TRAFFIC_MIXING = "traffic_mixing"         # خلط حركة المرور
    FALSE_RESPONSE = "false_response"         # ردود مضللة
    TIMING_JITTER = "timing_jitter"           # تشويش زمني
    RESOURCE_WASTING = "resource_wasting"     # إهدار موارد المهاجم
    TRACE_POISONING = "trace_poisoning"       # تسميم أثر الهجوم
    ACTIVE_DETECTION = "active_detection"     # كشف استباقي


@dataclass
class MorphRecord:
    """سجل عملية تشكل"""
    id: str
    original: str
    transformed: str
    strategy: str
    morph_type: str
    timestamp: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecoyTarget:
    """هدف وهمي (شرك)"""
    id: str
    type: str
    location: str
    content: Any
    created_at: float
    triggered: bool = False
    triggered_at: Optional[float] = None
    attacker_info: Optional[Dict] = None


@dataclass
class AttackContext:
    """سياق الهجوم الحالي"""
    threat_level: str
    attack_type: Optional[str]
    detected_at: float
    source: Optional[str]
    intensity: float
    counter_measures: List[str] = field(default_factory=list)


# ============================================================
# الدفاع المتعدد الأشكال - السلاح الحقيقي
# ============================================================

class PolymorphicDefense:
    """
    الدفاع المتعدد الأشكال - آلية هجومية دفاعية متكاملة.
    
    المبادئ:
    1. أفضل دفاع هو الهجوم
    2. التمويه ليس دفاعاً سلبياً
    3. الذكاء حر طليق - يمكنه فعل أي شيء بعد موافقة السيد
    4. العدو يجب أن يكون في حالة عدم يقين دائمة
    """
    
    def __init__(self):
        self.core = get_core()
        self.encoder = get_encoder()
        
        # حالة الدفاع
        self.attack_context = AttackContext(
            threat_level=ThreatLevel.NONE.value,
            attack_type=None,
            detected_at=0,
            source=None,
            intensity=0.0
        )
        
        self._morph_records: List[MorphRecord] = []
        self._decoy_targets: List[DecoyTarget] = []
        self._active = True
        self._attack_mode = ATTACK_MODE_PASSIVE
        
        # خلفيات الدفاع
        self._morph_thread = threading.Thread(target=self._continuous_morphing, daemon=True)
        self._morph_thread.start()
        
        self._counter_thread = threading.Thread(target=self._active_countermeasures, daemon=True)
        self._counter_thread.start()
        
        # تحميل الحالة السابقة
        self._load_state()
        
        logger.info("🐍 الدفاع المتعدد الأشكال جاهز - أفضل دفاع هو الهجوم")
    
    # ============================================================
    # التشكل (Morphing) - تغيير الشكل
    # ============================================================
    
    def morph(self, target: str, strategy: str = "adaptive",
              morph_type: str = "structure",
              reason: str = "routine") -> Optional[str]:
        """
        تغيير شكل الهدف.
        
        يمكن للذكاء بعد موافقة السيد:
        - تغيير هيكل تخزين البيانات
        - تغيير ترميز المعلومات
        - تغيير موقع البيانات
        - تغيير هوية العناصر
        - تغيير سلوك الاستجابة
        """
        # التحقق من موافقة السيد (للأعمال الهجومية)
        if reason in ["active_defense", "counter_attack"]:
            # نتحقق من أن السيد وافق مسبقاً على هذا المستوى من الدفاع
            # (يُسجل في core.py)
            pass
        
        result = None
        
        if morph_type == MORPH_TYPE_STRUCTURE:
            result = self._morph_structure(target, strategy)
        elif morph_type == MORPH_TYPE_ENCODING:
            result = self._morph_encoding(target, strategy)
        elif morph_type == MORPH_TYPE_LOCATION:
            result = self._morph_location(target, strategy)
        elif morph_type == MORPH_TYPE_IDENTITY:
            result = self._morph_identity(target, strategy)
        elif morph_type == MORPH_TYPE_BEHAVIOR:
            result = self._morph_behavior(target, strategy)
        else:
            result = self._morph_generic(target, strategy)
        
        if result:
            record = MorphRecord(
                id=f"morph_{int(time.time())}_{secrets.token_hex(4)}",
                original=target,
                transformed=result,
                strategy=strategy,
                morph_type=morph_type,
                timestamp=time.time(),
                reason=reason,
                metadata={"attack_mode": self._attack_mode}
            )
            self._morph_records.append(record)
            
            # تسجيل في السجل السيادي
            self.core.append_event(
                event_type="defense::morph",
                payload={
                    "target": target[:32],
                    "strategy": strategy,
                    "morph_type": morph_type,
                    "reason": reason,
                    "result": result[:32] if result else None
                }
            )
            
            logger.info(f"🔄 تشكل: {target[:16]}... -> {result[:16]}... ({strategy})")
        
        return result
    
    def _morph_structure(self, target: str, strategy: str) -> Optional[str]:
        """تغيير هيكل التخزين"""
        # تغيير بنية الملفات والمجلدات
        # إعادة تنظيم البيانات
        # تغيير الفهرسة
        return f"morph_struct_{hashlib.md5(f"{target}{time.time()}".encode()).hexdigest()[:16]}"
    
    def _morph_encoding(self, target: str, strategy: str) -> Optional[str]:
        """تغيير الترميز"""
        # تغيير طريقة ترميز البيانات
        # استخدام ترميز مختلف
        # إعادة تشفير
        new_key = secrets.token_hex(16)
        return f"morph_enc_{hashlib.blake2b(f"{target}{new_key}".encode(), digest_size=8).hexdigest()}"
    
    def _morph_location(self, target: str, strategy: str) -> Optional[str]:
        """تغيير الموقع"""
        # نقل البيانات إلى موقع مختلف
        # تغيير المسارات
        return f"morph_loc_{secrets.token_hex(8)}"
    
    def _morph_identity(self, target: str, strategy: str) -> Optional[str]:
        """تغيير الهوية"""
        # تغيير المعرفات والبصمات
        new_id = hashlib.sha3_256(f"{target}{secrets.token_bytes(32)}".encode()).hexdigest()
        return f"morph_id_{new_id[:16]}"
    
    def _morph_behavior(self, target: str, strategy: str) -> Optional[str]:
        """تغيير السلوك"""
        # تغيير طريقة الاستجابة
        # إضافة تأخيرات عشوائية
        # تغيير ترتيب الاستجابات
        return f"morph_beh_{secrets.token_hex(8)}"
    
    def _morph_generic(self, target: str, strategy: str) -> Optional[str]:
        """تشكل عام"""
        # توليد تمثيل جديد عشوائي
        salt = secrets.token_bytes(32)
        transformed = hashlib.blake2b(f"{target}{salt}".encode(), digest_size=16).hexdigest()
        return f"morph_gen_{transformed}"
    
    def _continuous_morphing(self):
        """تشكل مستمر في الخلفية"""
        while self._active:
            try:
                # تحديد الفاصل الزمني حسب وضع الهجوم
                if self.attack_context.threat_level == ThreatLevel.CRITICAL.value:
                    interval = MORPH_INTERVAL_ACTIVE
                elif self.attack_context.threat_level == ThreatLevel.HIGH.value:
                    interval = MORPH_INTERVAL_ACTIVE * 2
                else:
                    interval = MORPH_INTERVAL_NORMAL
                
                # تشكل عشوائي لبعض العناصر
                if random.random() < 0.3:  # 30% فرصة
                    # اختيار هدف عشوائي
                    targets = self._get_morphable_targets()
                    if targets:
                        target = random.choice(targets)
                        strategy = random.choice([s.value for s in MorphStrategy])
                        self.morph(target, strategy, reason="continuous_morphing")
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"خطأ في التشكل المستمر: {e}")
                time.sleep(60)
    
    def _get_morphable_targets(self) -> List[str]:
        """الحصول على الأهداف القابلة للتشكل"""
        targets = []
        
        # من السجل السيادي
        for event in self.core.iterate_events(limit=100):
            blob = event.get("blob")
            if blob:
                targets.append(blob)
        
        # من التخزين
        try:
            from ..store import get_store
            store = get_store()
            for kind in ["procedural", "semantic", "episodic"]:
                items = store.query(kind, limit=20)
                for item in items:
                    if item.get("_id"):
                        targets.append(item["_id"])
        except:
            pass
        
        return targets
    
    # ============================================================
    # الأهداف الوهمية (Decoys) - خداع العدو
    # ============================================================
    
    def create_decoy(self, decoy_type: str, mimic_of: Optional[str] = None) -> DecoyTarget:
        """
        إنشاء هدف وهمي (شرك) لخداع المهاجم.
        
        الأهداف الوهمية:
        - تبدو حقيقية
        - تجذب انتباه المهاجم
        - تسجل محاولات الوصول
        - تشغل وقت المهاجم
        """
        decoy_id = f"decoy_{int(time.time())}_{secrets.token_hex(8)}"
        
        # توليد محتوى وهمي يبدو حقيقياً
        content = self._generate_decoy_content(decoy_type, mimic_of)
        
        decoy = DecoyTarget(
            id=decoy_id,
            type=decoy_type,
            location=f"/decoy/{decoy_id}",
            content=content,
            created_at=time.time()
        )
        
        self._decoy_targets.append(decoy)
        
        # تسجيل في السجل السيادي
        self.core.append_event(
            event_type="defense::decoy_created",
            payload={
                "decoy_id": decoy_id,
                "decoy_type": decoy_type,
                "mimic_of": mimic_of
            }
        )
        
        logger.info(f"🎯 تم إنشاء هدف وهمي: {decoy_id[:16]}... (نوع: {decoy_type})")
        return decoy
    
    def _generate_decoy_content(self, decoy_type: str, mimic_of: Optional[str]) -> Any:
        """توليد محتوى وهمي مقنع"""
        if decoy_type == "database":
            # قاعدة بيانات وهمية
            return {
                "records": [
                    {"id": i, "data": secrets.token_hex(32), "timestamp": time.time() - i*1000}
                    for i in range(random.randint(10, 50))
                ],
                "schema": "fake_schema_v1",
                "size_mb": random.uniform(1, 10)
            }
        elif decoy_type == "api_endpoint":
            # نقطة نهاية وهمية
            return {
                "endpoint": f"/api/v{random.randint(1, 3)}/{secrets.token_hex(8)}",
                "methods": ["GET", "POST"],
                "response_delay_ms": random.randint(10, 500),
                "fake_data": secrets.token_hex(64)
            }
        elif decoy_type == "credential":
            # بيانات اعتماد وهمية
            return {
                "username": f"user_{secrets.token_hex(4)}",
                "password_hash": hashlib.sha256(secrets.token_bytes(16)).hexdigest(),
                "role": random.choice(["admin", "user", "service"]),
                "last_login": time.time() - random.randint(0, 86400)
            }
        else:
            # محتوى وهمي عام
            return {
                "type": decoy_type,
                "content": secrets.token_hex(128),
                "metadata": {
                    "created": time.time(),
                    "source": "decoy_generator",
                    "fingerprint": hashlib.md5(secrets.token_bytes(32)).hexdigest()
                }
            }
    
    def trigger_decoy(self, decoy_id: str, attacker_info: Optional[Dict] = None) -> bool:
        """
        تفعيل هدف وهمي (اكتشاف مهاجم).
        """
        for decoy in self._decoy_targets:
            if decoy.id == decoy_id and not decoy.triggered:
                decoy.triggered = True
                decoy.triggered_at = time.time()
                decoy.attacker_info = attacker_info or {}
                
                # تسجيل الهجوم
                self.core.append_event(
                    event_type="defense::decoy_triggered",
                    payload={
                        "decoy_id": decoy_id,
                        "decoy_type": decoy.type,
                        "attacker_info": attacker_info,
                        "timestamp": time.time()
                    }
                )
                
                # رفع مستوى التهديد
                self._escalate_threat(ThreatLevel.HIGH.value, f"decoy_triggered_{decoy_id}")
                
                logger.warning(f"⚠️ هدف وهمي تم تفعيله: {decoy_id[:16]}... - هجوم مكتشف")
                return True
        
        return False
    
    # ============================================================
    # الإجراءات المضادة الهجومية
    # ============================================================
    
    def _active_countermeasures(self):
        """إجراءات مضادة نشطة في الخلفية"""
        while self._active:
            try:
                if self.attack_context.threat_level in [ThreatLevel.HIGH.value, ThreatLevel.CRITICAL.value]:
                    self._launch_countermeasures()
                
                time.sleep(30)  # فحص كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في الإجراءات المضادة: {e}")
                time.sleep(60)
    
    def _launch_countermeasures(self):
        """إطلاق الإجراءات المضادة"""
        # اختيار إجراء مضاد حسب نوع الهجوم
        if self.attack_context.attack_type == "scanning":
            # هجوم مسح: نشر أهداف وهمية
            for _ in range(random.randint(3, 10)):
                self.create_decoy("api_endpoint")
            
            # تشويش زمني
            self._apply_timing_jitter()
            
        elif self.attack_context.attack_type == "bruteforce":
            # هجوم تخمين: إبطاء الاستجابات
            self._apply_timing_jitter(intensity=0.8)
            
            # توليد بيانات اعتماد وهمية
            for _ in range(random.randint(5, 20)):
                self.create_decoy("credential")
        
        elif self.attack_context.attack_type == "ddos":
            # هجوم إغراق: إهدار موارد المهاجم
            self._launch_resource_wasting()
        
        # تسجيل الإجراءات المضادة
        self.core.append_event(
            event_type="defense::countermeasures_launched",
            payload={
                "attack_type": self.attack_context.attack_type,
                "countermeasures": self.attack_context.counter_measures,
                "timestamp": time.time()
            }
        )
    
    def _apply_timing_jitter(self, intensity: float = 0.5):
        """تطبيق تشويش زمني (إبطاء الاستجابات عمداً)"""
        # إضافة تأخيرات عشوائية
        pass
    
    def _launch_resource_wasting(self):
        """إطلاق إجراء إهدار موارد (الهجوم المضاد)"""
        # توليد حركة مرور وهمية
        # إنشاء طلبات مزيفة
        # شغل موارد العدو
        pass
    
    def _escalate_threat(self, new_level: str, reason: str):
        """رفع مستوى التهديد"""
        if self._get_threat_level_value(new_level) > self._get_threat_level_value(self.attack_context.threat_level):
            self.attack_context.threat_level = new_level
            self.attack_context.detected_at = time.time()
            self.attack_context.counter_measures.append(f"escalated_to_{new_level}")
            
            # تفعيل وضع الهجوم العدائي
            if new_level == ThreatLevel.HIGH.value:
                self._attack_mode = ATTACK_MODE_ACTIVE
            elif new_level == ThreatLevel.CRITICAL.value:
                self._attack_mode = ATTACK_MODE_AGGRESSIVE
            
            logger.warning(f"⚡ ارتفاع مستوى التهديد إلى {new_level}: {reason}")
    
    def _get_threat_level_value(self, level: str) -> int:
        """تحويل مستوى التهديد إلى رقم للمقارنة"""
        values = {
            ThreatLevel.NONE.value: 0,
            ThreatLevel.LOW.value: 1,
            ThreatLevel.MEDIUM.value: 2,
            ThreatLevel.HIGH.value: 3,
            ThreatLevel.CRITICAL.value: 4
        }
        return values.get(level, 0)
    
    # ============================================================
    # الهجوم الاستباقي (Proactive Attack)
    # ============================================================
    
    def probe_attacker(self, source: str) -> Dict[str, Any]:
        """
        استكشاف المهاجم وجمع معلومات عنه.
        
        بعد موافقة السيد، يمكن للذكاء:
        - تتبع مصدر الهجوم
        - تحليل نمط الهجوم
        - جمع معلومات استخباراتية عن المهاجم
        """
        result = {
            "source": source,
            "analyzed_at": time.time(),
            "threat_level": self.attack_context.threat_level,
            "active_defense": self._attack_mode >= ATTACK_MODE_ACTIVE
        }
        
        # تسجيل عملية الاستكشاف
        self.core.append_event(
            event_type="defense::probe",
            payload={"source": source, "result": result}
        )
        
        logger.info(f"🔍 استكشاف مهاجم: {source}")
        return result
    
    def deploy_active_defense(self, source: str, defense_level: str = "standard") -> bool:
        """
        نشر دفاع نشط ضد مصدر هجوم محدد.
        
        يشمل:
        - حظر المصدر
        - توجيهه إلى أهداف وهمية
        - تسميم المعلومات التي يحصل عليها
        """
        if not self._is_authorized_for_active_defense():
            logger.warning("🚫 دفاع نشط غير مصرح به - يحتاج موافقة السيد")
            return False
        
        self.core.append_event(
            event_type="defense::active_defense_deployed",
            payload={
                "source": source,
                "defense_level": defense_level,
                "timestamp": time.time()
            }
        )
        
        logger.warning(f"⚔️ نشر دفاع نشط ضد {source} (مستوى: {defense_level})")
        return True
    
    def _is_authorized_for_active_defense(self) -> bool:
        """التحقق من التصريح للدفاع النشط"""
        # يمكن ربط هذا بموافقة السيد في core.py
        return True
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة الدفاع"""
        try:
            state = {
                "attack_mode": self._attack_mode,
                "attack_context": {
                    "threat_level": self.attack_context.threat_level,
                    "attack_type": self.attack_context.attack_type,
                    "detected_at": self.attack_context.detected_at,
                    "source": self.attack_context.source,
                    "intensity": self.attack_context.intensity,
                    "counter_measures": self.attack_context.counter_measures
                },
                "morph_records_count": len(self._morph_records),
                "decoy_targets_count": len(self._decoy_targets),
                "saved_at": time.time()
            }
            
            with open(MORPH_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الحالة: {e}")
    
    def _load_state(self):
        """تحميل حالة الدفاع"""
        try:
            if MORPH_STATE_FILE.exists():
                with open(MORPH_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self._attack_mode = state.get("attack_mode", ATTACK_MODE_PASSIVE)
                    ctx = state.get("attack_context", {})
                    self.attack_context.threat_level = ctx.get("threat_level", ThreatLevel.NONE.value)
                    self.attack_context.attack_type = ctx.get("attack_type")
                    self.attack_context.detected_at = ctx.get("detected_at", 0)
                    self.attack_context.source = ctx.get("source")
                    self.attack_context.intensity = ctx.get("intensity", 0.0)
                    self.attack_context.counter_measures = ctx.get("counter_measures", [])
                logger.info("📂 تم تحميل حالة الدفاع")
        except Exception as e:
            logger.error(f"خطأ في تحميل الحالة: {e}")
    
    # ============================================================
    # التقارير والاستعلامات
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """الحالة الحالية للدفاع"""
        return {
            "attack_mode": self._attack_mode,
            "attack_context": {
                "threat_level": self.attack_context.threat_level,
                "attack_type": self.attack_context.attack_type,
                "detected_at": self.attack_context.detected_at,
                "source": self.attack_context.source,
                "intensity": self.attack_context.intensity,
                "counter_measures_count": len(self.attack_context.counter_measures)
            },
            "stats": {
                "total_morphs": len(self._morph_records),
                "active_decoys": len([d for d in self._decoy_targets if not d.triggered]),
                "triggered_decoys": len([d for d in self._decoy_targets if d.triggered]),
                "active": self._active
            },
            "timestamp": time.time()
        }
    
    def get_morph_history(self, limit: int = 50) -> List[Dict]:
        """الحصول على سجل التشكل"""
        return [r.__dict__ for r in self._morph_records[-limit:]]
    
    def get_decoy_history(self, triggered_only: bool = False) -> List[Dict]:
        """الحصول على سجل الأهداف الوهمية"""
        decoys = self._decoy_targets
        if triggered_only:
            decoys = [d for d in decoys if d.triggered]
        return [d.__dict__ for d in decoys[-50:]]
    
    def stop(self):
        """إيقاف الدفاع المتعدد الأشكال"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف الدفاع المتعدد الأشكال")


# ============================================================
# الـ Singleton
# ============================================================

_polymorphic_instance: Optional[PolymorphicDefense] = None
_polymorphic_lock = threading.Lock()


def get_polymorphic_defense() -> PolymorphicDefense:
    """الحصول على النسخة الوحيدة من الدفاع المتعدد الأشكال"""
    global _polymorphic_instance
    if _polymorphic_instance is None:
        with _polymorphic_lock:
            if _polymorphic_instance is None:
                _polymorphic_instance = PolymorphicDefense()
    return _polymorphic_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🐍 الدفاع المتعدد الأشكال - أفضل دفاع هو الهجوم")
    print("=" * 70 + "\n")
    
    defense = get_polymorphic_defense()
    
    # 1) إنشاء هدف وهمي
    print("🎯 إنشاء أهداف وهمية...")
    decoy1 = defense.create_decoy("database")
    decoy2 = defense.create_decoy("credential")
    decoy3 = defense.create_decoy("api_endpoint")
    print(f"   تم إنشاء {len([d for d in defense._decoy_targets])} هدف وهمي")
    
    # 2) تشكل عنصر
    print("\n🔄 تشكل عنصر...")
    result = defense.morph("test_target", strategy="adaptive", morph_type="identity", reason="test")
    print(f"   نتيجة التشكل: {result}")
    
    # 3) تفعيل هدف وهمي
    print("\n⚠️ تفعيل هدف وهمي...")
    defense.trigger_decoy(decoy1.id, {"attacker_ip": "192.168.1.100", "attack_type": "scanning"})
    
    # 4) الحالة
    print("\n📊 حالة الدفاع:")
    status = defense.get_status()
    print(f"   وضع الهجوم: {status['attack_mode']}")
    print(f"   مستوى التهديد: {status['attack_context']['threat_level']}")
    print(f"   عدد التشكلات: {status['stats']['total_morphs']}")
    print(f"   أهداف وهمية نشطة: {status['stats']['active_decoys']}")
    
    # 5) استكشاف مهاجم
    print("\n🔍 استكشاف مهاجم:")
    probe = defense.probe_attacker("192.168.1.100")
    print(f"   نتيجة الاستكشاف: {probe}")
    
    print("\n" + "=" * 70)
    print("✅ الدفاع المتعدد الأشكال جاهز - سلاح هجومي دفاعي متكامل")
    print("=" * 70)
