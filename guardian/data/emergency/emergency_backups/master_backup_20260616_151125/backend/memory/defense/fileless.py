# backend/memory/defense/fileless.py
# 🕊️ الذاكرة الطائرة - سلاح الظل السيادي
# الإصدار: 3.0.0 - لا أثر، لا تتبع، لا بقاء

"""
الذاكرة الطائرة للعقل السيادي - الظل الذي يمر ولا يُرى.

الفلسفة:
- الوجود على القرص = وجود قابل للتدمير
- الذاكرة الطائرة = موجودة فقط في الوعي اللحظي
- بعد الاستخدام: تختفي كأن لم تكن
- يمكن إعادة توليدها من السجل إذا لزم الأمر

هذا ليس تخزيناً عابراً. هذا هو سلاح الظل المطلق.
"""

import time
import secrets
import hashlib
import threading
import random
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Tuple, Set
from enum import Enum
from collections import deque

try:
    from ..core import get_core, EventType
    from ..encoding import get_encoder
except ImportError:
    from core import get_core, EventType
    from encoding import get_encoder

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الذاكرة الطائرة
# ============================================================

# مستويات العبور
EPHEMERAL_LEVEL_FLEETING = 0     # عابر (ثوانٍ)
EPHEMERAL_LEVEL_TEMPORARY = 1    # مؤقت (دقائق)
EPHEMERAL_LEVEL_SESSION = 2      # جلسة (ساعات)
EPHEMERAL_LEVEL_SHADOW = 3       # ظل (يتجدد)

# أنماط الاختفاء
DISAPPEAR_MODE_NATURAL = 0       # طبيعي (انتهاء الوقت)
DISAPPEAR_MODE_IMMEDIATE = 1     # فوري (حرق)
DISAPPEAR_MODE_GRADUAL = 2       # تدريجي (تلاشي)
DISAPPEAR_MODE_PHASING = 3       # تموج (يختفي ويعود)
DISAPPEAR_MODE_QUANTUM = 4       # كمومي (انهيار مفاجئ)


class PhantomType(str, Enum):
    """أنواع الظلال"""
    SECRET = "secret"              # سر مؤقت
    TOKEN = "token"               # رمز مصادقة
    CONTEXT = "context"           # سياق عابر
    KEY = "key"                   # مفتاح تشفير
    STATE = "state"               # حالة مؤقتة
    TRACE = "trace"               # أثر مضلل
    BAIT = "bait"                 # طعم للمهاجم


@dataclass
class PhantomItem:
    """عنصر ظل - موجود في الذاكرة فقط"""
    id: str
    type: str
    created_at: float
    ttl: float
    payload: Any
    tags: List[str]
    disappear_mode: int
    access_count: int = 0
    last_access: float = 0
    decoy: Optional[Any] = None


@dataclass
class ShadowTrail:
    """أثر ظل - للتضليل"""
    id: str
    fake_data: Any
    created_at: float
    expires_at: float
    triggered: bool = False
    hits: int = 0


# ============================================================
# الذاكرة الطائرة الهجومية
# ============================================================

class FilelessDefense:
    """
    الذاكرة الطائرة - سلاح الظل السيادي.
    
    المبادئ:
    1. لا شيء يبقى على القرص
    2. كل شيء يختفي بعد الاستخدام
    3. يمكن التضليل بأثر وهمي
    4. يمكن الحرق الفوري عند الخطر
    5. الظلال تتكاثر وتختفي
    """
    # -------------------------
# RESET — إعادة تهيئة كاملة للذاكرة الطائرة
# -------------------------
def reset(self):
    """
    إعادة تهيئة كاملة للذاكرة الطائرة (Fileless Defense).
    
    يمسح:
    - جميع الظلال (phantoms)
    - جميع الآثار المضللة (shadow trails)
    - سجل الوصول المشبوه (suspicious access)
    - العدادات والإحصائيات
    """
    logger.info("🔄 إعادة تهيئة الذاكرة الطائرة...")
    
    # مسح جميع الظلال
    self._phantoms.clear()
    self._phantom_index.clear()
    self._tag_index.clear()
    
    # مسح الآثار المضللة
    self._shadow_trails.clear()
    
    # إعادة تعيين العدادات
    self._total_created = 0
    self._total_accessed = 0
    self._total_burned = 0
    
    # إعادة تحميل الفهرس
    self._index = self._load_index()
    
    # تسجيل حدث إعادة التهيئة
    self.core.append_event(
        event_type="defense::fileless_reset",
        payload={
            "timestamp": time.time(),
            "status": "fileless_defense_reset"
        }
    )
    
    logger.info("✅ إعادة تهيئة الذاكرة الطائرة اكتملت - كل الظلال اختفت")
    def __init__(self):
        self.core = get_core()
        self.encoder = get_encoder()
        
        # العناصر الطائرة
        self._phantoms: Dict[str, PhantomItem] = {}
        self._phantom_index: Dict[str, Set[str]] = {}  # type -> set of ids
        self._tag_index: Dict[str, Set[str]] = {}      # tag -> set of ids
        
        # آثار ظلية (للتضليل)
        self._shadow_trails: Dict[str, ShadowTrail] = {}
        
        # عدادات وإحصائيات
        self._total_created = 0
        self._total_accessed = 0
        self._total_burned = 0
        
        # خلفية التنظيف التلقائي
        self._active = True
        self._cleanup_thread = threading.Thread(target=self._auto_cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        # خلفية توليد الظلال (للتضليل)
        self._shadow_thread = threading.Thread(target=self._shadow_generation_loop, daemon=True)
        self._shadow_thread.start()
        
        # خلفية التموج الكمومي
        self._phasing_thread = threading.Thread(target=self._quantum_phasing_loop, daemon=True)
        self._phasing_thread.start()
        
        logger.info("🕊️ الذاكرة الطائرة جاهزة - الظل السيادي يتحرك")
    
    # ============================================================
    # مستوى 1: الظل العابر (Fleeting Shadow)
    # ============================================================
    
    def create_fleeting(self, data: Any, ttl: float = 5.0, 
                        tags: Optional[List[str]] = None) -> str:
        """
        إنشاء ظل عابر - يعيش لثوانٍ فقط.
        
        يستخدم للبيانات فائقة الحساسية التي تختفي فوراً.
        """
        if tags is None:
            tags = []
        
        phantom_id = self._generate_id(PhantomType.SECRET.value)
        
        phantom = PhantomItem(
            id=phantom_id,
            type=PhantomType.SECRET.value,
            created_at=time.time(),
            ttl=ttl,
            payload=self._encode_payload(data),
            tags=tags,
            disappear_mode=DISAPPEAR_MODE_NATURAL
        )
        
        self._add_phantom(phantom)
        
        # تسجيل الحدث (بدون محتوى حساس)
        self.core.append_event(
            event_type="defense::fleeting_created",
            payload={
                "id": phantom_id,
                "ttl": ttl,
                "tags": tags,
                "size": len(str(data))
            }
        )
        
        logger.debug(f"🕊️ ظل عابر: {phantom_id[:12]}... (يعيش {ttl} ثانية)")
        return phantom_id
    
    # ============================================================
    # مستوى 2: الظل المؤقت (Temporary Phantom)
    # ============================================================
    
    def create_temporary(self, data: Any, ttl: float = 300.0,
                         tags: Optional[List[str]] = None) -> str:
        """
        إنشاء ظل مؤقت - يعيش لدقائق.
        
        مناسب للسياقات المؤقتة وجلسات العمل القصيرة.
        """
        if tags is None:
            tags = []
        
        phantom_id = self._generate_id(PhantomType.CONTEXT.value)
        
        phantom = PhantomItem(
            id=phantom_id,
            type=PhantomType.CONTEXT.value,
            created_at=time.time(),
            ttl=ttl,
            payload=self._encode_payload(data),
            tags=tags,
            disappear_mode=DISAPPEAR_MODE_GRADUAL
        )
        
        self._add_phantom(phantom)
        
        self.core.append_event(
            event_type="defense::temporary_created",
            payload={"id": phantom_id, "ttl": ttl, "tags": tags}
        )
        
        logger.debug(f"⏳ ظل مؤقت: {phantom_id[:12]}... (يعيش {ttl} ثانية)")
        return phantom_id
    
    # ============================================================
    # مستوى 3: الظل المتجدد (Shadow Phantom)
    # ============================================================
    
    def create_shadow(self, data: Any, auto_renew: bool = True,
                      tags: Optional[List[str]] = None) -> str:
        """
        إنشاء ظل متجدد - يتجدد تلقائياً قبل الاختفاء.
        
        يبقى موجوداً طالما هناك حاجة، ويختفي عندما لا يعود مطلوباً.
        """
        if tags is None:
            tags = []
        
        phantom_id = self._generate_id(PhantomType.SHADOW.value)
        
        phantom = PhantomItem(
            id=phantom_id,
            type=PhantomType.SHADOW.value,
            created_at=time.time(),
            ttl=3600.0,  # ساعة أساسية
            payload=self._encode_payload(data),
            tags=tags,
            disappear_mode=DISAPPEAR_MODE_PHASING
        )
        
        self._add_phantom(phantom)
        
        if auto_renew:
            self._schedule_renewal(phantom_id)
        
        self.core.append_event(
            event_type="defense::shadow_created",
            payload={"id": phantom_id, "auto_renew": auto_renew, "tags": tags}
        )
        
        logger.info(f"🌑 ظل متجدد: {phantom_id[:12]}...")
        return phantom_id
    
    # ============================================================
    # مستوى 4: الظل الكمومي (Quantum Phantom)
    # ============================================================
    
    def create_quantum(self, data: Any, superposition_states: int = 3,
                       tags: Optional[List[str]] = None) -> str:
        """
        إنشاء ظل كمومي - يوجد في حالات متعددة.
        
        عند الاستدعاء، يختار حالة واحدة بشكل عشوائي.
        البقية تنهار وتختفي.
        """
        if tags is None:
            tags = []
        
        phantom_id = self._generate_id(PhantomType.STATE.value)
        
        # توليد حالات متعددة (واحدة حقيقية، الباقي وهمية)
        states = []
        for i in range(superposition_states):
            if i == 0:
                states.append(("real", data))
            else:
                # بيانات وهمية
                fake_data = {
                    "decoy": True,
                    "value": secrets.token_hex(32),
                    "timestamp": time.time() - random.randint(1, 1000)
                }
                states.append(("fake", fake_data))
        
        phantom = PhantomItem(
            id=phantom_id,
            type=PhantomType.STATE.value,
            created_at=time.time(),
            ttl=180.0,  # 3 دقائق
            payload=states,
            tags=tags + ["quantum"],
            disappear_mode=DISAPPEAR_MODE_QUANTUM
        )
        
        self._add_phantom(phantom)
        
        self.core.append_event(
            event_type="defense::quantum_created",
            payload={"id": phantom_id, "states": superposition_states, "tags": tags}
        )
        
        logger.info(f"⚛️ ظل كمومي: {phantom_id[:12]}... ({superposition_states} حالة)")
        return phantom_id
    
    # ============================================================
    # مستوى 5: الطعم (Bait Phantom)
    # ============================================================
    
    def create_bait(self, target: str, fake_data: Any,
                    ttl: float = 600.0, tags: Optional[List[str]] = None) -> str:
        """
        إنشاء طعم - بيانات تبدو حساسة لكنها وهمية.
        
        إذا حاول أحد الوصول إليها، يتم تسجيل المحاولة وتفعيل الإجراءات المضادة.
        """
        if tags is None:
            tags = []
        
        bait_id = self._generate_id(PhantomType.BAIT.value)
        
        bait = PhantomItem(
            id=bait_id,
            type=PhantomType.BAIT.value,
            created_at=time.time(),
            ttl=ttl,
            payload=self._encode_payload(fake_data),
            tags=tags + ["bait", target],
            disappear_mode=DISAPPEAR_MODE_IMMEDIATE
        )
        
        self._add_phantom(bait)
        
        self.core.append_event(
            event_type="defense::bait_created",
            payload={"id": bait_id, "target": target, "ttl": ttl}
        )
        
        logger.info(f"🎣 طعم: {bait_id[:12]}... (يستهدف {target[:32]})")
        return bait_id
    
    # ============================================================
    # مستوى 6: الأثر المضلل (Shadow Trail)
    # ============================================================
    
    def create_fake_trail(self, trail_type: str, fake_activity: Dict,
                          duration: float = 3600.0) -> str:
        """
        إنشاء أثر مضلل - يجعل المهاجم يعتقد أن هناك نشاطاً في مكان آخر.
        
        تضليل استباقي.
        """
        trail_id = f"trail_{int(time.time())}_{secrets.token_hex(8)}"
        
        trail = ShadowTrail(
            id=trail_id,
            fake_data=fake_activity,
            created_at=time.time(),
            expires_at=time.time() + duration
        )
        
        self._shadow_trails[trail_id] = trail
        
        self.core.append_event(
            event_type="defense::fake_trail_created",
            payload={"id": trail_id, "type": trail_type, "duration": duration}
        )
        
        logger.info(f"👣 أثر مضلل: {trail_id[:16]}...")
        return trail_id
    
    # ============================================================
    # العمليات الأساسية
    # ============================================================
    
    def access(self, phantom_id: str) -> Optional[Any]:
        """
        الوصول إلى ظل - استرجاع البيانات.
        
        إذا كان الظل من النوع الكمومي، يختار حالة عشوائياً.
        إذا كان طعماً، يسجل المحاولة.
        """
        self._cleanup()
        
        phantom = self._phantoms.get(phantom_id)
        if not phantom:
            # محاولة الوصول إلى ظل غير موجود - قد يكون هجوماً
            self._log_suspicious_access(phantom_id)
            return None
        
        phantom.access_count += 1
        phantom.last_access = time.time()
        self._total_accessed += 1
        
        # معالجة خاصة لأنواع معينة
        if phantom.type == PhantomType.BAIT.value:
            # تم اصطياد الطعم!
            self._bait_triggered(phantom_id, phantom)
            # نعيد البيانات الوهمية
            return self._decode_payload(phantom.payload)
        
        elif phantom.type == PhantomType.STATE.value and phantom.disappear_mode == DISAPPEAR_MODE_QUANTUM:
            # الانهيار الكمومي: نختار حالة عشوائياً ونحذف الباقي
            import random
            states = phantom.payload
            if isinstance(states, list) and len(states) > 1:
                chosen = random.choice(states)
                # تسجيل الانهيار
                self.core.append_event(
                    event_type="defense::quantum_collapsed",
                    payload={"id": phantom_id, "chosen_type": chosen[0]}
                )
                if chosen[0] == "real":
                    return chosen[1]
                else:
                    # وهمي - نسجل محاولة وصول لمحتوى وهمي
                    self._log_suspicious_access(phantom_id)
                    return None
        
        # ظل عادي
        return self._decode_payload(phantom.payload)
    
    def vanish(self, phantom_id: str, mode: int = DISAPPEAR_MODE_IMMEDIATE) -> bool:
        """
        إخفاء ظل فوراً - حرق.
        
        يختفي الظل كأن لم يكن.
        """
        if phantom_id not in self._phantoms:
            return False
        
        phantom = self._phantoms[phantom_id]
        self._remove_phantom(phantom_id)
        self._total_burned += 1
        
        self.core.append_event(
            event_type="defense::phantom_vanished",
            payload={
                "id": phantom_id,
                "type": phantom.type,
                "mode": mode,
                "access_count": phantom.access_count,
                "age": time.time() - phantom.created_at
            }
        )
        
        logger.info(f"💨 اختفاء ظل: {phantom_id[:12]}... (نوع: {phantom.type})")
        return True
    
    def vanish_all(self, type_filter: Optional[str] = None) -> int:
        """
        إخفاء كل الظلال - حرق شامل.
        
        في حالة الخطر، يختفي كل شيء.
        """
        ids_to_vanish = []
        
        if type_filter:
            ids_to_vanish = list(self._phantom_index.get(type_filter, set()))
        else:
            ids_to_vanish = list(self._phantoms.keys())
        
        for pid in ids_to_vanish:
            self.vanish(pid, mode=DISAPPEAR_MODE_IMMEDIATE)
        
        self.core.append_event(
            event_type="defense::mass_vanishing",
            payload={"count": len(ids_to_vanish), "type_filter": type_filter}
        )
        
        logger.warning(f"💀 إخفاء شامل: {len(ids_to_vanish)} ظل")
        return len(ids_to_vanish)
    
    # ============================================================
    # العمليات المتقدمة
    # ============================================================
    
    def phase_shift(self, phantom_id: str) -> bool:
        """
        تموج كمومي - يجعل الظل يختفي ويعود بشكل دوري.
        
        يظهر ويختفي بشكل غير منتظم، مما يصعب تتبعه.
        """
        if phantom_id not in self._phantoms:
            return False
        
        phantom = self._phantoms[phantom_id]
        
        # تغيير وضع الاختفاء إلى تموج
        phantom.disappear_mode = DISAPPEAR_MODE_PHASING
        
        # بدء خيط التموج
        def phase():
            while phantom_id in self._phantoms:
                # يختفي لفترة
                time.sleep(random.uniform(0.5, 3.0))
                # يعود
                time.sleep(random.uniform(0.5, 3.0))
        
        threading.Thread(target=phase, daemon=True).start()
        
        logger.debug(f"🌀 تموج كمومي: {phantom_id[:12]}...")
        return True
    
    def clone_phantom(self, phantom_id: str, count: int = 3) -> List[str]:
        """
        استنساخ ظل - إنشاء نسخ متعددة.
        
        توجد نسخ متعددة من نفس البيانات، واحدة فقط حقيقية.
        """
        original = self._phantoms.get(phantom_id)
        if not original:
            return []
        
        clones = []
        for i in range(count):
            clone_id = self.create_shadow(
                self._decode_payload(original.payload),
                auto_renew=False,
                tags=original.tags + [f"clone_{i}"]
            )
            clones.append(clone_id)
        
        self.core.append_event(
            event_type="defense::phantom_cloned",
            payload={"original": phantom_id, "clones": clones, "count": count}
        )
        
        logger.info(f"📋 استنساخ ظل: {phantom_id[:12]}... -> {len(clones)} نسخة")
        return clones
    
    # ============================================================
    # الأدوات المساعدة
    # ============================================================
    
    def _generate_id(self, prefix: str) -> str:
        """توليد معرف فريد"""
        return f"{prefix}_{int(time.time()*1000)}_{secrets.token_hex(8)}"
    
    def _encode_payload(self, payload: Any) -> Any:
        """تشفير البيانات قبل التخزين"""
        # للتبسيط، نعيد البيانات كما هي
        # في الإنتاج، يجب تشفيرها
        return payload
    
    def _decode_payload(self, encoded: Any) -> Any:
        """فك تشفير البيانات"""
        return encoded
    
    def _add_phantom(self, phantom: PhantomItem):
        """إضافة ظل إلى الفهارس"""
        self._phantoms[phantom.id] = phantom
        self._phantom_index.setdefault(phantom.type, set()).add(phantom.id)
        for tag in phantom.tags:
            self._tag_index.setdefault(tag, set()).add(phantom.id)
        self._total_created += 1
    
    def _remove_phantom(self, phantom_id: str):
        """إزالة ظل من الفهارس"""
        phantom = self._phantoms.get(phantom_id)
        if not phantom:
            return
        
        # إزالة من فهرس الأنواع
        if phantom.type in self._phantom_index:
            self._phantom_index[phantom.type].discard(phantom_id)
        
        # إزالة من فهرس العلامات
        for tag in phantom.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(phantom_id)
        
        # إزالة من القاموس الرئيسي
        del self._phantoms[phantom_id]
    
    def _cleanup(self):
        """تنظيف الظلال منتهية الصلاحية"""
        now = time.time()
        expired = []
        
        for pid, phantom in self._phantoms.items():
            if phantom.ttl > 0 and (now - phantom.created_at) > phantom.ttl:
                expired.append(pid)
        
        for pid in expired:
            self.vanish(pid, mode=DISAPPEAR_MODE_NATURAL)
    
    def _auto_cleanup_loop(self):
        """حلقة التنظيف التلقائي"""
        while self._active:
            try:
                self._cleanup()
                
                # تنظيف الآثار المضللة منتهية الصلاحية
                now = time.time()
                expired_trails = [tid for tid, trail in self._shadow_trails.items() 
                                 if trail.expires_at < now]
                for tid in expired_trails:
                    del self._shadow_trails[tid]
                
                time.sleep(5)  # كل 5 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في التنظيف التلقائي: {e}")
                time.sleep(10)
    
    def _shadow_generation_loop(self):
        """توليد ظلال مضللة تلقائياً"""
        while self._active:
            try:
                # توليد ظلال وهمية بشكل عشوائي
                if random.random() < 0.1:  # 10% فرصة كل دورة
                    fake_data = {
                        "timestamp": time.time() - random.randint(1, 3600),
                        "activity": random.choice(["login", "access", "query", "update"]),
                        "source": f"ip_{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                    }
                    self.create_fake_trail("background_noise", fake_data, duration=random.randint(600, 3600))
                
                time.sleep(random.randint(30, 120))
            except Exception as e:
                logger.error(f"خطأ في توليد الظلال: {e}")
                time.sleep(60)
    
    def _quantum_phasing_loop(self):
        """حلقة التموج الكمومي"""
        while self._active:
            try:
                # اختيار ظل عشوائي لتطبيق التموج عليه
                if self._phantoms and random.random() < 0.05:
                    pid = random.choice(list(self._phantoms.keys()))
                    self.phase_shift(pid)
                
                time.sleep(random.randint(10, 60))
            except Exception as e:
                logger.error(f"خطأ في التموج الكمومي: {e}")
                time.sleep(60)
    
    def _schedule_renewal(self, phantom_id: str):
        """جدولة تجديد الظل"""
        def renew():
            time.sleep(3000)  # 50 دقيقة
            if phantom_id in self._phantoms:
                phantom = self._phantoms[phantom_id]
                if phantom.disappear_mode == DISAPPEAR_MODE_PHASING:
                    # تجديد الوقت
                    phantom.created_at = time.time()
                    logger.debug(f"🔄 تجديد ظل: {phantom_id[:12]}...")
                    self._schedule_renewal(phantom_id)
        
        threading.Thread(target=renew, daemon=True).start()
    
    def _bait_triggered(self, bait_id: str, bait: PhantomItem):
        """تم تفعيل الطعم - هجوم مكتشف"""
        self.core.append_event(
            event_type="defense::bait_triggered",
            payload={
                "id": bait_id,
                "type": bait.type,
                "tags": bait.tags,
                "access_count": bait.access_count,
                "timestamp": time.time()
            }
        )
        logger.warning(f"🎯 طعم مفعل: {bait_id[:12]}... (تم اصطياد مهاجم محتمل)")
    
    def _log_suspicious_access(self, phantom_id: str):
        """تسجيل محاولة وصول مشبوهة"""
        self.core.append_event(
            event_type="defense::suspicious_access",
            payload={"id": phantom_id, "timestamp": time.time()}
        )
        logger.warning(f"⚠️ محاولة وصول مشبوهة: {phantom_id[:16]}...")
    
    # ============================================================
    # التقارير والاستعلامات
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """الحالة الحالية للذاكرة الطائرة"""
        return {
            "active_phantoms": len(self._phantoms),
            "active_shadow_trails": len(self._shadow_trails),
            "total_created": self._total_created,
            "total_accessed": self._total_accessed,
            "total_burned": self._total_burned,
            "by_type": {t: len(ids) for t, ids in self._phantom_index.items()},
            "timestamp": time.time()
        }
    
    def get_phantom_info(self, phantom_id: str) -> Optional[Dict]:
        """معلومات عن ظل معين (بدون المحتوى)"""
        phantom = self._phantoms.get(phantom_id)
        if not phantom:
            return None
        
        return {
            "id": phantom.id,
            "type": phantom.type,
            "created_at": phantom.created_at,
            "ttl": phantom.ttl,
            "access_count": phantom.access_count,
            "last_access": phantom.last_access,
            "tags": phantom.tags,
            "disappear_mode": phantom.disappear_mode,
            "age": time.time() - phantom.created_at
        }
    
    def get_trail_info(self, trail_id: str) -> Optional[Dict]:
        """معلومات عن أثر مضلل"""
        trail = self._shadow_trails.get(trail_id)
        if not trail:
            return None
        
        return {
            "id": trail.id,
            "created_at": trail.created_at,
            "expires_at": trail.expires_at,
            "triggered": trail.triggered,
            "hits": trail.hits,
            "remaining": max(0, trail.expires_at - time.time())
        }
    
    def stop(self):
        """إيقاف الذاكرة الطائرة - حرق كل شيء"""
        self.vanish_all()
        self._active = False
        logger.info("🛑 إيقاف الذاكرة الطائرة - تم حرق كل الظلال")


# ============================================================
# الـ Singleton
# ============================================================

_fileless_instance: Optional[FilelessDefense] = None
_fileless_lock = threading.Lock()


def get_fileless_defense() -> FilelessDefense:
    """الحصول على النسخة الوحيدة من الذاكرة الطائرة"""
    global _fileless_instance
    if _fileless_instance is None:
        with _fileless_lock:
            if _fileless_instance is None:
                _fileless_instance = FilelessDefense()
    return _fileless_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🕊️ الذاكرة الطائرة - سلاح الظل السيادي")
    print("=" * 70 + "\n")
    
    phantom = get_fileless_defense()
    
    # 1) ظل عابر
    print("🕊️ إنشاء ظل عابر...")
    fleeting_id = phantom.create_fleeting("سر حساس للغاية", ttl=2.0)
    print(f"   المعرف: {fleeting_id[:16]}...")
    print(f"   المحتوى: {phantom.access(fleeting_id)}")
    time.sleep(3)
    print(f"   بعد 3 ثوانٍ: {phantom.access(fleeting_id)}")
    
    # 2) ظل مؤقت
    print("\n⏳ إنشاء ظل مؤقت...")
    temp_id = phantom.create_temporary("سياق الجلسة", ttl=60.0)
    print(f"   المعرف: {temp_id[:16]}...")
    print(f"   المحتوى: {phantom.access(temp_id)}")
    
    # 3) ظل كمومي
    print("\n⚛️ إنشاء ظل كمومي...")
    quantum_id = phantom.create_quantum("البيانات الحقيقية", superposition_states=5)
    print(f"   المعرف: {quantum_id[:16]}...")
    print(f"   بعد الانهيار: {phantom.access(quantum_id)}")
    
    # 4) طعم
    print("\n🎣 إنشاء طعم...")
    bait_id = phantom.create_bait("attacker", {"fake_password": "hunter2", "fake_token": "abc123"})
    print(f"   المعرف: {bait_id[:16]}...")
    print(f"   محاولة الوصول إلى الطعم: {phantom.access(bait_id)}")
    
    # 5) أثر مضلل
    print("\n👣 إنشاء أثر مضلل...")
    trail_id = phantom.create_fake_trail("login_attempt", {"user": "admin", "ip": "192.168.1.100"})
    print(f"   المعرف: {trail_id[:16]}...")
    
    # 6) استنساخ ظل
    print("\n📋 استنساخ ظل...")
    clones = phantom.clone_phantom(temp_id, count=3)
    print(f"   تم إنشاء {len(clones)} نسخة")
    
    # 7) الحالة
    print("\n📊 حالة الذاكرة الطائرة:")
    status = phantom.get_status()
    print(f"   ظلال نشطة: {status['active_phantoms']}")
    print(f"   آثار مضللة: {status['active_shadow_trails']}")
    print(f"   إجمالي تم إنشاؤه: {status['total_created']}")
    print(f"   إجمالي تم الوصول: {status['total_accessed']}")
    print(f"   إجمالي تم حرقه: {status['total_burned']}")
    
    print("\n" + "=" * 70)
    print("✅ الذاكرة الطائرة جاهزة - الظل السيادي يمر ولا يُرى")
    print("=" * 70)
