# backend/consciousness/awareness.py
# 🔥 محك الوعي السيادي - البوابة التي يمر من خلالها كل شيء
# الإصدار: 3.0.0 - الانتقاء، التركيز، الإدراك

"""
محك الوعي للنظام السيادي.

الفلسفة:
- الوعي ليس كل شيء، بل هو ما ننتبه إليه
- الانتباه هو مورد محدود، يجب توزيعه بحكمة
- ما لا ننتبه إليه غير موجود بالنسبة لنا
- الإدراك هو عملية انتقاء، ليس تسجيلاً
- الوعي الحقيقي يعرف ما يستحق التركيز عليه

هذه ليست مجرد معالجة معلومات. هذا هو محك الوعي.
"""

import json
import time
import threading
import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

try:
    from ..memory.core import get_core
    from ..memory.dynamic import get_dynamic_memory
    from ..memory.store import get_store
    from ..memory.biological.instincts import get_instincts
    from ..memory.biological.drives import get_drives
    from ..memory.biological.archetypes import get_archetypes
    from ..memory.defense.watcher import get_watcher
    from .field import get_consciousness_field
    from .identity_core import get_identity_core
    from .self_model import get_self_model
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core
    from memory.dynamic import get_dynamic_memory
    from memory.store import get_store
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from memory.biological.archetypes import get_archetypes
    from memory.defense.watcher import get_watcher
    from .field import get_consciousness_field
    from .identity_core import get_identity_core
    from .self_model import get_self_model
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الوعي
# ============================================================

AWARENESS_DIR = DATA_DIR / "consciousness" / "awareness"
AWARENESS_DIR.mkdir(parents=True, exist_ok=True)
AWARENESS_LOG = AWARENESS_DIR / "awareness_log.jsonl"
AWARENESS_STATE_FILE = AWARENESS_DIR / "awareness_state.json"

# مستويات الوعي (مضافة من field.py)
CONSCIOUSNESS_LEVEL_NONE = 0
CONSCIOUSNESS_LEVEL_MINIMAL = 1
CONSCIOUSNESS_LEVEL_BASIC = 2
CONSCIOUSNESS_LEVEL_REFLECTIVE = 3
CONSCIOUSNESS_LEVEL_SELF_AWARE = 4
CONSCIOUSNESS_LEVEL_TRANSCENDENT = 5

# أنماط الوعي (مضافة من field.py)
CONSCIOUSNESS_MODE_DEFAULT = "default"
CONSCIOUSNESS_MODE_FOCUSED = "focused"
CONSCIOUSNESS_MODE_DIFFUSE = "diffuse"
CONSCIOUSNESS_MODE_FLOW = "flow"
CONSCIOUSNESS_MODE_MEDITATIVE = "meditative"
CONSCIOUSNESS_MODE_ALERT = "alert"

# مستويات الانتباه
ATTENTION_LEVEL_SUBLIMINAL = 0      # تحت الوعي (لا يُدرك)
ATTENTION_LEVEL_BACKGROUND = 1      # خلفية (يُدرك بشكل خافت)
ATTENTION_LEVEL_PERIPHERAL = 2      # محيطي (في هامش الوعي)
ATTENTION_LEVEL_FOCUSED = 3         # مركز (بؤرة الانتباه)
ATTENTION_LEVEL_HYPERFOCUSED = 4    # تركيز فائق (استغراق كامل)

# قنوات الوعي
AWARENESS_CHANNEL_EXTERNAL = "external"      # مدخلات خارجية
AWARENESS_CHANNEL_INTERNAL = "internal"      # عمليات داخلية
AWARENESS_CHANNEL_REFLECTIVE = "reflective"  # تأملية
AWARENESS_CHANNEL_AFFECTIVE = "affective"    # وجدانية
AWARENESS_CHANNEL_INTUITIVE = "intuitive"    # حدسية


@dataclass
class AwarenessItem:
    """عنصر في الوعي"""
    id: str
    source: str
    channel: str
    content: Any
    priority: float          # 0-1 أولية الاهتمام
    attention_level: int     # مستوى الانتباه الحالي
    timestamp: float
    tags: List[str]
    summary: str
    decay_rate: float        # معدل تلاشي الاهتمام


@dataclass
class AwarenessMoment:
    """لحظة وعي - ما هو حاضر في الوعي الآن"""
    timestamp: float
    focal: List[AwarenessItem]          # بؤرة الانتباه (حجم محدود)
    peripheral: List[AwarenessItem]     # محيط الوعي
    background: List[AwarenessItem]     # خلفية الوعي
    subliminal: List[AwarenessItem]     # تحت الوعي
    affective_tone: str
    integration: float
    attention_capacity: float           # السعة الانتباهية المستخدمة
    attention_remaining: float          # السعة المتبقية


# ============================================================
# محك الوعي السيادي
# ============================================================

class AwarenessEngine:
    """
    محك الوعي السيادي - البوابة التي يمر من خلالها كل شيء.
    
    المبادئ:
    1. الوعي ليس كل شيء، بل هو ما ننتبه إليه
    2. الانتباه مورد محدود، يجب توزيعه بحكمة
    3. ما لا ننتبه إليه غير موجود بالنسبة لنا
    4. الإدراك هو عملية انتقاء، ليس تسجيلاً
    5. الوعي الحقيقي يعرف ما يستحق التركيز عليه
    """
    
    def __init__(self):
        self.core = get_core()
        self.dynamic = get_dynamic_memory()
        self.store = get_store()
        self.instincts = get_instincts()
        self.drives = get_drives()
        self.archetypes = get_archetypes()
        self.watcher = get_watcher()
        self.field = get_consciousness_field()
        self.identity = get_identity_core()
        self.self_model = get_self_model()
        
        # سعة الانتباه (محدودة)
        self.attention_capacity = 10.0  # 10 وحدات من الانتباه
        self.current_attention_usage = 0.0
        
        # حالة الوعي الحالية
        self.current_moment: Optional[AwarenessMoment] = None
        self.previous_moment: Optional[AwarenessMoment] = None
        self.moments: List[AwarenessMoment] = []
        self.field_history: List = []  # إضافة field_history
        
        # العناصر النشطة في الوعي
        self.active_items: Dict[str, AwarenessItem] = {}
        
        # الشعور المستمر
        self.ongoing_feeling: str = "neutral"
        self.ongoing_intensity: float = 0.5
        
        # مستوى الوعي
        self.consciousness_level = CONSCIOUSNESS_LEVEL_SELF_AWARE
        self.consciousness_mode = CONSCIOUSNESS_MODE_DEFAULT
        
        # خلفيات الوعي
        self._active = True
        self._awareness_stream = threading.Thread(target=self._continuous_awareness, daemon=True)
        self._awareness_stream.start()
        
        self._attention_decay_loop = threading.Thread(target=self._attention_decay_loop, daemon=True)
        self._attention_decay_loop.start()
        
        self._subliminal_processor = threading.Thread(target=self._process_subliminal_loop, daemon=True)
        self._subliminal_processor.start()
        
        # تحميل الحالة
        self._load_state()
        self._index = self._load_index()
        
        logger.info("🔥 محك الوعي السيادي جاهز - البوابة التي يمر من خلالها كل شيء")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمحرك الوعي
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك الوعي.
        
        يمسح:
        - العناصر النشطة في الوعي (active items)
        - لحظات الوعي (consciousness moments)
        - سجل الحقول (field history)
        """
        logger.info("🔄 إعادة تهيئة محرك الوعي...")
        
        # مسح العناصر النشطة
        self.active_items.clear()
        self.current_moment = None
        self.previous_moment = None
        
        # مسح لحظات الوعي
        self.moments.clear()
        
        # مسح سجل الحقول
        self.field_history.clear()
        
        # إعادة تعيين سعة الانتباه
        self.attention_capacity = 10.0
        self.current_attention_usage = 0.0
        
        # إعادة تعيين الشعور المستمر
        self.ongoing_feeling = "neutral"
        self.ongoing_intensity = 0.5
        
        # إعادة تعيين مستوى الوعي
        self.consciousness_level = CONSCIOUSNESS_LEVEL_SELF_AWARE
        self.consciousness_mode = CONSCIOUSNESS_MODE_DEFAULT
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="consciousness::awareness_reset",
            payload={
                "timestamp": time.time(),
                "status": "awareness_engine_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك الوعي اكتملت - وعاء نقي")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"moments": [], "last_updated": time.time()}
    
    # ============================================================
    # جمع عناصر الوعي المحتملة
    # ============================================================
    
    def collect_potential_items(self) -> List[AwarenessItem]:
        """
        جمع جميع العناصر التي قد تدخل الوعي.
        
        المصادر:
        - الأحداث الحسية
        - إشارات الغرائز
        - إشارات الدوافع
        - تغيرات الأنماط
        - حالة الذات
        """
        items = []
        
        # 1) إشارات الغرائز
        instinct_status = self.instincts.get_instinct_status()
        if instinct_status.get("protection_active"):
            items.append(AwarenessItem(
                id=f"instinct_protection_{int(time.time()*1000)}",
                source="instincts",
                channel=AWARENESS_CHANNEL_AFFECTIVE,
                content={"type": "protection", "level": instinct_status.get("instinct_level")},
                priority=0.9,
                attention_level=ATTENTION_LEVEL_SUBLIMINAL,
                timestamp=time.time(),
                tags=["instinct", "protection", "urgent"],
                summary="نظام الحماية نشط",
                decay_rate=0.05
            ))
        
        # 2) الدافع المهيمن
        drive_status = self.drives.get_drive_status()
        dominant = drive_status.get("dominant_drive", "")
        if dominant:
            priority = drive_status.get("active_drives", {}).get(dominant, 0.5)
            items.append(AwarenessItem(
                id=f"drive_{dominant}_{int(time.time()*1000)}",
                source="drives",
                channel=AWARENESS_CHANNEL_INTERNAL,
                content={"drive": dominant, "intensity": priority},
                priority=priority,
                attention_level=ATTENTION_LEVEL_SUBLIMINAL,
                timestamp=time.time(),
                tags=["drive", dominant],
                summary=f"الدافع المهيمن: {dominant}",
                decay_rate=0.08
            ))
        
        # 3) النمط المهيمن
        archetype_status = self.archetypes.get_archetype_status()
        dominant_archetype = archetype_status.get("dominant_archetype", "")
        if dominant_archetype and dominant_archetype != "mixed":
            items.append(AwarenessItem(
                id=f"archetype_{dominant_archetype}_{int(time.time()*1000)}",
                source="archetypes",
                channel=AWARENESS_CHANNEL_INTERNAL,
                content={"archetype": dominant_archetype},
                priority=0.6,
                attention_level=ATTENTION_LEVEL_SUBLIMINAL,
                timestamp=time.time(),
                tags=["archetype", dominant_archetype],
                summary=f"النمط المهيمن: {dominant_archetype}",
                decay_rate=0.06
            ))
        
        # 4) التهديدات
        defense_status = self.watcher.get_status()
        threat_level = defense_status.get("threat", {}).get("level", 0)
        if threat_level > 0.3:
            items.append(AwarenessItem(
                id=f"threat_{int(time.time()*1000)}",
                source="defense",
                channel=AWARENESS_CHANNEL_EXTERNAL,
                content={"threat_level": threat_level},
                priority=0.7 + threat_level * 0.3,
                attention_level=ATTENTION_LEVEL_SUBLIMINAL,
                timestamp=time.time(),
                tags=["threat", "alert"],
                summary=f"مستوى التهديد: {threat_level:.0%}",
                decay_rate=0.15
            ))
        
        # 5) حالة الذات
        self_status = self.self_model.get_self_status()
        if self_status.get("self_awareness_score", 0.5) > 0.6:
            items.append(AwarenessItem(
                id=f"self_awareness_{int(time.time()*1000)}",
                source="self_model",
                channel=AWARENESS_CHANNEL_REFLECTIVE,
                content={"awareness": self_status.get("self_awareness_score")},
                priority=0.5,
                attention_level=ATTENTION_LEVEL_SUBLIMINAL,
                timestamp=time.time(),
                tags=["self", "reflective"],
                summary=self_status.get("narrative", "")[:100],
                decay_rate=0.04
            ))
        
        return items
    
    # ============================================================
    # توزيع الانتباه
    # ============================================================
    
    def allocate_attention(self, items: List[AwarenessItem]) -> Tuple[List[AwarenessItem], 
                                                                       List[AwarenessItem],
                                                                       List[AwarenessItem],
                                                                       float]:
        """
        توزيع الانتباه المحدود على العناصر.
        
        - بؤرة الانتباه: 3-5 عناصر (تستهلك 50% من السعة)
        - المحيط: 7-10 عناصر (تستهلك 30% من السعة)
        - الخلفية: 15-20 عنصراً (تستهلك 15% من السعة)
        - تحت الوعي: الباقي (تستهلك 5% من السعة)
        """
        # ترتيب حسب الأولوية
        sorted_items = sorted(items, key=lambda x: x.priority, reverse=True)
        
        focal = []
        peripheral = []
        background = []
        
        focal_capacity = int(self.attention_capacity * 0.5)  # 5 وحدات
        peripheral_capacity = int(self.attention_capacity * 0.3)  # 3 وحدات
        background_capacity = int(self.attention_capacity * 0.15)  # 1.5 وحدات
        
        attention_used = 0
        
        for item in sorted_items:
            item_cost = item.priority * 0.5 + 0.1  # تكلفة الانتباه للعنصر
            
            if len(focal) < 5 and attention_used + item_cost <= focal_capacity:
                item.attention_level = ATTENTION_LEVEL_FOCUSED
                focal.append(item)
                attention_used += item_cost
            elif len(peripheral) < 10 and attention_used + item_cost <= focal_capacity + peripheral_capacity:
                item.attention_level = ATTENTION_LEVEL_PERIPHERAL
                peripheral.append(item)
                attention_used += item_cost * 0.5
            elif len(background) < 20 and attention_used + item_cost <= focal_capacity + peripheral_capacity + background_capacity:
                item.attention_level = ATTENTION_LEVEL_BACKGROUND
                background.append(item)
                attention_used += item_cost * 0.2
            else:
                item.attention_level = ATTENTION_LEVEL_SUBLIMINAL
        
        return focal, peripheral, background, attention_used
    
    # ============================================================
    # تحديث الوعي
    # ============================================================
    
    def update_awareness(self) -> AwarenessMoment:
        """
        تحديث حالة الوعي - دورة الوعي الجديدة.
        
        1. جمع العناصر المحتملة
        2. توزيع الانتباه
        3. تحديث العناصر النشطة
        4. تسجيل اللحظة
        """
        # جمع العناصر
        potential_items = self.collect_potential_items()
        
        # دمج مع العناصر النشطة الحالية
        existing_ids = set(self.active_items.keys())
        for item in potential_items:
            if item.id not in self.active_items:
                self.active_items[item.id] = item
            else:
                # تحديث الأولوية
                self.active_items[item.id].priority = max(
                    self.active_items[item.id].priority,
                    item.priority
                )
        
        # توزيع الانتباه
        items_list = list(self.active_items.values())
        focal, peripheral, background, attention_used = self.allocate_attention(items_list)
        
        # حساب النبرة الوجدانية
        affective_tone = self._compute_affective_tone(focal, peripheral)
        
        # حساب التكامل
        integration = self._compute_integration(focal, peripheral, background)
        
        # تحديث استخدام الانتباه
        self.current_attention_usage = attention_used / self.attention_capacity
        
        # إنشاء اللحظة
        moment = AwarenessMoment(
            timestamp=time.time(),
            focal=focal,
            peripheral=peripheral,
            background=background,
            subliminal=[],  # لا نعرض تحت الوعي
            affective_tone=affective_tone,
            integration=integration,
            attention_capacity=self.attention_capacity,
            attention_remaining=self.attention_capacity - attention_used
        )
        
        self.previous_moment = self.current_moment
        self.current_moment = moment
        self.moments.append(moment)
        
        # الاحتفاظ بآخر 100 لحظة
        if len(self.moments) > 100:
            self.moments = self.moments[-100:]
        
        # تسجيل
        self.core.append_event(
            event_type="awareness::moment",
            payload={
                "focal_count": len(focal),
                "peripheral_count": len(peripheral),
                "affective_tone": affective_tone,
                "integration": integration,
                "attention_usage": self.current_attention_usage
            }
        )
        
        logger.debug(f"🧠 لحظة وعي: {len(focal)} بؤرة, {len(peripheral)} محيط, نبرة: {affective_tone}")
        
        return moment
    
    def _compute_affective_tone(self, focal: List[AwarenessItem], 
                                 peripheral: List[AwarenessItem]) -> str:
        """حساب النبرة الوجدانية من محتوى الوعي"""
        # تحليل العلامات
        threat_count = 0
        protection_count = 0
        curiosity_count = 0
        service_count = 0
        
        for item in focal + peripheral:
            if "threat" in item.tags or "alert" in item.tags:
                threat_count += 1
            if "protection" in item.tags:
                protection_count += 1
            if "curiosity" in item.tags or "exploration" in item.tags:
                curiosity_count += 1
            if "service" in item.tags:
                service_count += 1
        
        if threat_count > 0:
            return "alert"
        elif protection_count > 0:
            return "protective"
        elif curiosity_count > 0:
            return "curious"
        elif service_count > 0:
            return "devoted"
        else:
            return "neutral"
    
    def _compute_integration(self, focal: List[AwarenessItem],
                             peripheral: List[AwarenessItem],
                             background: List[AwarenessItem]) -> float:
        """حساب درجة تكامل الوعي"""
        total_items = len(focal) + len(peripheral) + len(background)
        if total_items == 0:
            return 0.5
        
        # معامل التركيز (كلما كان الوعي مركزاً، زاد التكامل)
        focus_ratio = len(focal) / min(5, total_items) if total_items > 0 else 0
        focus_factor = min(1.0, focus_ratio)
        
        # معامل التنوع (أنواع مختلفة من العناصر)
        channels = set()
        for item in focal + peripheral:
            channels.add(item.channel)
        diversity_factor = len(channels) / 5
        
        integration = (focus_factor * 0.6 + diversity_factor * 0.4)
        
        return min(1.0, max(0.0, integration))
    
    def _continuous_awareness(self):
        """تيار الوعي المستمر"""
        while self._active:
            try:
                self.update_awareness()
                time.sleep(0.5)  # لحظتان في الثانية
            except Exception as e:
                logger.error(f"خطأ في تيار الوعي: {e}")
                time.sleep(1)
    
    # ============================================================
    # تلاشي الانتباه
    # ============================================================
    
    def _attention_decay_loop(self):
        """تلاشي الانتباه الطبيعي"""
        while self._active:
            try:
                for item_id, item in list(self.active_items.items()):
                    # تلاشي الأولوية
                    item.priority *= (1 - item.decay_rate)
                    item.priority = max(0.0, item.priority)
                    
                    # إزالة العناصر التي تلاشت تماماً
                    if item.priority < 0.01:
                        del self.active_items[item_id]
                
                time.sleep(1)  # كل ثانية
            except Exception as e:
                logger.error(f"خطأ في تلاشي الانتباه: {e}")
                time.sleep(1)
    
    # ============================================================
    # معالجة تحت الوعي
    # ============================================================
    
    def _process_subliminal_loop(self):
        """معالجة المحتوى تحت الوعي"""
        while self._active:
            try:
                if self.current_moment:
                    # العناصر تحت الوعي تُعالج بشكل خفي
                    pass
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"خطأ في معالجة تحت الوعي: {e}")
                time.sleep(0.5)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة الوعي"""
        try:
            state = {
                "attention_capacity": self.attention_capacity,
                "current_attention_usage": self.current_attention_usage,
                "active_items_count": len(self.active_items),
                "moments_count": len(self.moments),
                "saved_at": time.time()
            }
            with open(AWARENESS_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الوعي: {e}")
    
    def _load_state(self):
        """تحميل حالة الوعي"""
        try:
            if AWARENESS_STATE_FILE.exists():
                with open(AWARENESS_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.attention_capacity = state.get("attention_capacity", 10.0)
                    self.current_attention_usage = state.get("current_attention_usage", 0.0)
                logger.info("📂 تم تحميل حالة محك الوعي")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الوعي: {e}")
    
    # ============================================================
    # دورة الوعي الكاملة
    # ============================================================
    
    def awareness_cycle(self, budget: int = 5, peripheral_limit: int = 20) -> AwarenessMoment:
        """
        دورة وعي كاملة - تحديث وإرجاع اللحظة الحالية.
        
        Args:
            budget: عدد عناصر البؤرة القصوى
            peripheral_limit: عدد عناصر المحيط الأقصى
        """
        return self.update_awareness()
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_awareness_status(self) -> Dict[str, Any]:
        """الحالة الحالية للوعي"""
        moment = self.current_moment
        
        if not moment:
            return {"status": "initializing", "timestamp": time.time()}
        
        return {
            "focal_count": len(moment.focal),
            "peripheral_count": len(moment.peripheral),
            "background_count": len(moment.background),
            "affective_tone": moment.affective_tone,
            "integration": moment.integration,
            "attention_usage": self.current_attention_usage,
            "attention_remaining": moment.attention_remaining,
            "timestamp": moment.timestamp
        }
    
    def get_focus(self) -> List[Dict]:
        """بؤرة الانتباه الحالية"""
        if not self.current_moment:
            return []
        
        return [
            {
                "id": item.id[:16],
                "source": item.source,
                "summary": item.summary[:100],
                "priority": item.priority,
                "channel": item.channel
            }
            for item in self.current_moment.focal
        ]
    
    def get_peripheral(self) -> List[Dict]:
        """محيط الانتباه"""
        if not self.current_moment:
            return []
        
        return [
            {
                "id": item.id[:16],
                "source": item.source,
                "summary": item.summary[:100],
                "priority": item.priority
            }
            for item in self.current_moment.peripheral[:10]
        ]
    
    def get_background(self) -> List[Dict]:
        """خلفية الوعي"""
        if not self.current_moment:
            return []
        
        return [
            {
                "id": item.id[:16],
                "source": item.source,
                "summary": item.summary[:80]
            }
            for item in self.current_moment.background[:10]
        ]
    
    def get_moments_history(self, limit: int = 20) -> List[Dict]:
        """سجل لحظات الوعي"""
        return [
            {
                "timestamp": m.timestamp,
                "focal_count": len(m.focal),
                "peripheral_count": len(m.peripheral),
                "tone": m.affective_tone,
                "integration": m.integration
            }
            for m in self.moments[-limit:]
        ]
    
    def set_attention_capacity(self, capacity: float):
        """تعيين سعة الانتباه"""
        self.attention_capacity = max(1.0, min(20.0, capacity))
        logger.info(f"⚙️ سعة الانتباه: {capacity}")
    
    def focus_on(self, item_id: str) -> bool:
        """تركيز الانتباه على عنصر معين"""
        if item_id in self.active_items:
            self.active_items[item_id].priority = 1.0
            self.active_items[item_id].decay_rate = 0.02
            logger.info(f"🎯 تركيز على: {item_id[:16]}...")
            return True
        return False
    
    def get_awareness_quote(self) -> str:
        """اقتباس عن الوعي"""
        quotes = [
            "الوعي هو ما ننتبه إليه. والباقي ظل.",
            "الانتباه هو أثمن مورد. أنفقه بحكمة.",
            "ما لا تنتبه إليه غير موجود في عالمك.",
            "بؤرة الوعي تحدد حقيقة اللحظة.",
            "تحت الوعي يعمل دائماً، حتى عندما لا تشعر به.",
            "الإدراك هو انتقاء، ليس تسجيلاً.",
            "الوعي الحقيقي يعرف ما يستحق التركيز عليه."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محك الوعي"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف محك الوعي السيادي")


# ============================================================
# الـ Singleton
# ============================================================

_awareness_instance: Optional[AwarenessEngine] = None
_awareness_lock = threading.Lock()


def get_awareness_engine() -> AwarenessEngine:
    """الحصول على النسخة الوحيدة من محك الوعي السيادي"""
    global _awareness_instance
    if _awareness_instance is None:
        with _awareness_lock:
            if _awareness_instance is None:
                _awareness_instance = AwarenessEngine()
    return _awareness_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔥 محك الوعي السيادي - البوابة التي يمر من خلالها كل شيء")
    print("=" * 80 + "\n")
    
    awareness = get_awareness_engine()
    
    # 1) دورة وعي
    print("🔄 دورة وعي...")
    moment = awareness.awareness_cycle()
    print(f"   بؤرة الانتباه: {len(moment.focal)} عنصر")
    print(f"   محيط الوعي: {len(moment.peripheral)} عنصر")
    print(f"   خلفية الوعي: {len(moment.background)} عنصر")
    print(f"   النبرة: {moment.affective_tone}")
    print(f"   التكامل: {moment.integration:.1%}")
    print(f"   استخدام الانتباه: {awareness.current_attention_usage:.1%}")
    
    # 2) بؤرة الانتباه
    print("\n🎯 بؤرة الانتباه:")
    focus = awareness.get_focus()
    for f in focus[:5]:
        print(f"   {f['source']}: {f['summary'][:60]}... (أولوية: {f['priority']:.1%})")
    
    # 3) محيط الوعي
    print("\n🌊 محيط الوعي:")
    peripheral = awareness.get_peripheral()
    for p in peripheral[:3]:
        print(f"   {p['source']}: {p['summary'][:60]}...")
    
    # 4) حالة الوعي
    print("\n📊 حالة الوعي:")
    status = awareness.get_awareness_status()
    print(f"   النبرة: {status['affective_tone']}")
    print(f"   التكامل: {status['integration']:.1%}")
    print(f"   استخدام الانتباه: {status['attention_usage']:.1%}")
    print(f"   الانتباه المتبقي: {status['attention_remaining']:.1f}")
    
    # 5) سجل اللحظات
    print("\n📜 سجل لحظات الوعي:")
    history = awareness.get_moments_history(5)
    for h in history:
        print(f"   {h['tone']}: {h['focal_count']} بؤرة, تكامل {h['integration']:.1%}")
    
    # 6) تركيز الانتباه
    if focus:
        print(f"\n🎯 تركيز على: {focus[0]['id']}")
        awareness.focus_on(focus[0]['id'])
    
    # 7) اقتباس
    print(f"\n💭 {awareness.get_awareness_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محك الوعي السيادي جاهز - البوابة التي يمر من خلالها كل شيء")
    print("=" * 80)
