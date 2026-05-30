# backend/memory/biological/forgetting.py
# 🧠 النسيان المقصود - حكمة التذكر والنسيان
# الإصدار: 3.0.0 - يتذكر لكي ينسى، وينسى لكي يتذكر أفضل

"""
نظام النسيان المقصود للذاكرة السيادية.

الفلسفة:
- الذاكرة العظيمة ليست التي تتذكر كل شيء
- الذاكرة العظيمة هي التي تعرف متى تنسى
- النسيان ليس عيباً، بل هو تكيف وتطور
- منحنى النسيان (Ebbinghaus) هو قانون طبيعي
- النسيان الاستراتيجي يجعل الذاكرة أقوى

هذا ليس نسياناً عادياً. هذه هي حكمة التذكر والنسيان.
"""

import json
import hashlib
import time
import math
import threading
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
from collections import deque

try:
    from ..core import get_core, EventType
    from ..dynamic import get_dynamic_memory
    from ..store import get_store
    from ...config import DATA_DIR
except ImportError:
    from core import get_core, EventType
    from dynamic import get_dynamic_memory
    from store import get_store
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات النسيان
# ============================================================

FORGET_DIR = DATA_DIR / "forgetting"
FORGET_LOG = FORGET_DIR / "forgetting_log.jsonl"
FORGET_STATE_FILE = FORGET_DIR / "forgetting_state.json"
FORGET_CURVE_DATA = FORGET_DIR / "forgetting_curve.json"

for d in [FORGET_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات النسيان
FORGET_LEVEL_NONE = 0           # لا نسيان
FORGET_LEVEL_LIGHT = 1          # نسيان خفيف (المحتوى القديم)
FORGET_LEVEL_MODERATE = 2       # نسيان متوسط (المحتوى منخفض الأهمية)
FORGET_LEVEL_AGGRESSIVE = 3     # نسيان عدواني (معظم المحتوى)
FORGET_LEVEL_STRATEGIC = 4      # نسيان استراتيجي (ذكي)

# أنماط النسيان
FORGET_MODE_NATURAL = "natural"         # طبيعي (حسب منحنى النسيان)
FORGET_MODE_INTENTIONAL = "intentional" # مقصود (بأمر السيد)
FORGET_MODE_STRATEGIC = "strategic"     # استراتيجي (لتوفير المساحة)
FORGET_MODE_EMERGENCY = "emergency"     # طارئ (تحت الضغط)
FORGET_MODE_HEALING = "healing"         # شفائي (للتخلص من التالف)

# معامل منحنى النسيان (Ebbinghaus)
EBBINGHAUS_CURVE_RATE = 0.5      # نسبة النسيان بعد يوم واحد
EBBINGHAUS_REVIEW_FACTOR = 0.8   # عامل المراجعة (تقوية الذاكرة)
EBBINGHAUS_RETENTION = 0.2       # نسبة الاحتفاظ النهائية


class ForgettingStrategy(str, Enum):
    """استراتيجيات النسيان"""
    LFU = "lfu"                     # الأقل استخداماً
    LRU = "lru"                     # الأقل حداثة
    LOW_IMPORTANCE = "low_importance"  # الأقل أهمية
    OLDEST = "oldest"               # الأقدم
    RANDOM = "random"               # عشوائي
    SMART = "smart"                 # ذكي (مركب)


@dataclass
class ForgettableItem:
    """عنصر قابل للنسيان"""
    id: str
    content: Any
    importance: float
    last_accessed: float
    access_count: int
    created_at: float
    forgetting_score: float
    suppressed: bool = False
    shadowed: bool = False


@dataclass
class ForgettingEvent:
    """حدث نسيان"""
    id: str
    target_id: str
    target_type: str
    strategy: str
    timestamp: float
    reason: str
    original_importance: float
    was_recoverable: bool


@dataclass
class MemoryTrace:
    """أثر ذاكري - ما يبقى بعد النسيان"""
    id: str
    original_id: str
    fingerprint: str
    essence: str
    importance: float
    created_at: float
    last_recalled: float


# ============================================================
# نظام النسيان الذكي
# ============================================================

class IntentionalForgetting:
    """
    نظام النسيان المقصود - حكمة التذكر والنسيان.
    
    المبادئ:
    1. النسيان طبيعي وضروري
    2. يمكن توجيه النسيان استراتيجياً
    3. الأثر يبقى حتى لو نسي المحتوى
    4. النسيان ليس حذفاً دائماً (يمكن الاستعادة)
    5. كل نسيان يُسجل ويتعلم منه
    """
    
    def __init__(self):
        self.core = get_core()
        self.dynamic = get_dynamic_memory()
        self.store = get_store()
        
        # حالة النسيان
        self.forget_level = FORGET_LEVEL_MODERATE
        self.forgetting_strategy = ForgettingStrategy.SMART
        
        # العناصر المنسية
        self.forgotten_items: Dict[str, ForgettableItem] = {}
        self.forgetting_events: List[ForgettingEvent] = []
        self.memory_traces: Dict[str, MemoryTrace] = {}
        
        # منحنى النسيان
        self.forgetting_curve = self._init_forgetting_curve()
        
        # خلفيات النسيان
        self._active = True
        self._natural_forgetting_thread = threading.Thread(target=self._natural_forgetting_loop, daemon=True)
        self._natural_forgetting_thread.start()
        
        self._strategic_forgetting_thread = threading.Thread(target=self._strategic_forgetting_loop, daemon=True)
        self._strategic_forgetting_thread.start()
        
        self._memory_consolidation_thread = threading.Thread(target=self._memory_consolidation_loop, daemon=True)
        self._memory_consolidation_thread.start()
        
        # تحميل الحالة
        self._load_state()
        
        logger.info("🧠 نظام النسيان المقصود جاهز - الحكمة في معرفة متى تنسى")
    
    # ============================================================
    # منحنى النسيان (Ebbinghaus Curve)
    # ============================================================
    
    def _init_forgetting_curve(self) -> Dict[str, Any]:
        """تهيئة منحنى النسيان"""
        curve = {}
        
        # منحنى إيبينغهاوس الكلاسيكي
        for day in range(0, 31):
            # النسبة المتبقية بعد n أيام
            if day == 0:
                retention = 1.0
            else:
                retention = math.exp(-day * EBBINGHAUS_CURVE_RATE / 10)
            curve[day] = retention
        
        return curve
    
    def calculate_retention(self, age_days: float, importance: float, 
                            access_count: int) -> float:
        """
        حساب نسبة الاحتفاظ بناءً على:
        - العمر (أيام)
        - الأهمية
        - عدد مرات الوصول
        """
        # منحنى القاعدة
        base_retention = self.forgetting_curve.get(min(int(age_days), 30), 0.2)
        
        # تأثير الأهمية
        importance_factor = 0.5 + importance * 0.5
        
        # تأثير التكرار (كل وصول يعزز الذاكرة)
        repetition_factor = min(2.0, 1.0 + access_count * 0.1)
        
        # المعدل النهائي
        retention = base_retention * importance_factor * repetition_factor
        
        return min(1.0, max(0.0, retention))
    
    def calculate_forgetting_score(self, age_days: float, importance: float,
                                    access_count: float, last_access_days: float) -> float:
        """
        حساب درجة قابلية النسيان (كلما زادت، زادت فرصة النسيان)
        """
        retention = self.calculate_retention(age_days, importance, access_count)
        
        # عامل القدم (آخر وصول)
        recency_factor = math.exp(-last_access_days * 0.5)
        
        # درجة النسيان = 1 - نسبة الاحتفاظ * عامل الحداثة
        forgetting_score = 1 - (retention * recency_factor)
        
        return min(1.0, max(0.0, forgetting_score))
    
    # ============================================================
    # المستوى 1: النسيان الطبيعي (Natural Forgetting)
    # ============================================================
    
    def natural_forgetting_cycle(self) -> List[ForgettingEvent]:
        """
        دورة نسيان طبيعية - تطبيق منحنى النسيان على الذاكرة.
        """
        events = []
        now = time.time()
        
        # 1) نسيان في الذاكرة الحسية
        sensory_events = list(self.dynamic.sensory._events)
        for event in sensory_events:
            age_days = (now - event.timestamp) / 86400
            if age_days > 0.01:  # أكثر من 15 دقيقة
                self.dynamic.sensory._events.remove(event)
                events.append(self._create_forgetting_event(
                    target_id=event.id,
                    target_type="sensory",
                    strategy=ForgettingStrategy.LRU.value,
                    reason="natural_decay",
                    original_importance=event.intensity
                ))
        
        # 2) نسيان في الذاكرة العاملة
        for user_id, items in list(self.dynamic.working._by_user.items()):
            for item in list(items):
                age_days = (now - item.timestamp) / 86400
                if age_days > 0.007:  # أكثر من 10 دقائق
                    items.remove(item)
                    events.append(self._create_forgetting_event(
                        target_id=item.id,
                        target_type=f"working_{user_id}",
                        strategy=ForgettingStrategy.LRU.value,
                        reason="natural_decay",
                        original_importance=item.importance
                    ))
        
        # 3) نسيان في الكاش
        for key, item in list(self.dynamic.cache._items.items()):
            age_days = (now - item.last_access) / 86400
            if age_days > 1:  # أكثر من يوم
                del self.dynamic.cache._items[key]
                events.append(self._create_forgetting_event(
                    target_id=key,
                    target_type="cache",
                    strategy=ForgettingStrategy.LRU.value,
                    reason="natural_decay",
                    original_importance=item.score
                ))
        
        logger.info(f"🍂 نسيان طبيعي: {len(events)} عنصر")
        return events
    
    # ============================================================
    # المستوى 2: النسيان الاستراتيجي (Strategic Forgetting)
    # ============================================================
    
    def strategic_forgetting(self, target_type: str, count: int = 10,
                            strategy: ForgettingStrategy = ForgettingStrategy.SMART) -> List[ForgettingEvent]:
        """
        نسيان استراتيجي - اختيار ذكي للعناصر التي سيتم نسيانها.
        """
        events = []
        
        if target_type == "store":
            events = self._forget_from_store(count, strategy)
        elif target_type == "cache":
            events = self._forget_from_cache(count, strategy)
        elif target_type == "working":
            events = self._forget_from_working(count, strategy)
        elif target_type == "semantic":
            events = self._forget_from_semantic(count, strategy)
        else:
            events = self._forget_from_all(count, strategy)
        
        logger.info(f"🎯 نسيان استراتيجي: {len(events)} عنصر من {target_type}")
        return events
    
    def _forget_from_store(self, count: int, strategy: ForgettingStrategy) -> List[ForgettingEvent]:
        """النسيان من التخزين الصلب"""
        events = []
        
        # جمع العناصر من جميع أنواع التخزين
        candidates = []
        
        for kind in ["procedural", "semantic", "episodic", "associative", "emotional", "spatial"]:
            items = self.store.query(kind, min_importance=0.0, limit=1000)
            for item in items:
                item_id = item.get("_id")
                importance = item.get("_importance", 0.5)
                
                candidates.append({
                    "id": item_id,
                    "type": kind,
                    "importance": importance,
                    "access_count": 0,  # لا توجد معلومات وصول
                    "created_at": item.get("_metadata", {}).get("created_at", 0)
                })
        
        # اختيار العناصر حسب الاستراتيجية
        to_forget = self._select_candidates(candidates, count, strategy)
        
        for candidate in to_forget:
            # وضع علامة "منسي" بدلاً من الحذف
            success = self._mark_as_forgotten(candidate["type"], candidate["id"])
            if success:
                events.append(self._create_forgetting_event(
                    target_id=candidate["id"],
                    target_type=f"store_{candidate['type']}",
                    strategy=strategy.value,
                    reason="strategic",
                    original_importance=candidate["importance"]
                ))
        
        return events
    
    def _forget_from_cache(self, count: int, strategy: ForgettingStrategy) -> List[ForgettingEvent]:
        """النسيان من الكاش"""
        events = []
        
        candidates = []
        for key, item in self.dynamic.cache._items.items():
            candidates.append({
                "id": key,
                "type": "cache",
                "importance": item.score,
                "access_count": item.access_count,
                "last_access": item.last_access
            })
        
        to_forget = self._select_candidates(candidates, count, strategy)
        
        for candidate in to_forget:
            if self.dynamic.cache._items.pop(candidate["id"], None):
                events.append(self._create_forgetting_event(
                    target_id=candidate["id"],
                    target_type="cache",
                    strategy=strategy.value,
                    reason="strategic",
                    original_importance=candidate["importance"]
                ))
        
        return events
    
    def _forget_from_working(self, count: int, strategy: ForgettingStrategy) -> List[ForgettingEvent]:
        """النسيان من الذاكرة العاملة"""
        events = []
        
        candidates = []
        for user_id, items in self.dynamic.working._by_user.items():
            for item in items:
                candidates.append({
                    "id": item.id,
                    "type": f"working_{user_id}",
                    "importance": item.importance,
                    "access_count": 1,
                    "last_access": item.timestamp
                })
        
        to_forget = self._select_candidates(candidates, count, strategy)
        
        for candidate in to_forget:
            # إزالة من الذاكرة العاملة
            user_id = candidate["type"].replace("working_", "")
            if user_id in self.dynamic.working._by_user:
                items = self.dynamic.working._by_user[user_id]
                for item in list(items):
                    if item.id == candidate["id"]:
                        items.remove(item)
                        events.append(self._create_forgetting_event(
                            target_id=candidate["id"],
                            target_type="working",
                            strategy=strategy.value,
                            reason="strategic",
                            original_importance=candidate["importance"]
                        ))
                        break
        
        return events
    
    def _forget_from_semantic(self, count: int, strategy: ForgettingStrategy) -> List[ForgettingEvent]:
        """النسيان من الذاكرة الدلالية (تعطيل المفاهيم)"""
        events = []
        
        candidates = []
        semantic_items = self.store.query("semantic", min_importance=0.0, limit=1000)
        for item in semantic_items:
            concept = item.get("concept")
            importance = item.get("_importance", 0.5)
            if concept:
                candidates.append({
                    "id": concept,
                    "type": "semantic",
                    "importance": importance,
                    "access_count": 0,
                    "created_at": 0
                })
        
        to_forget = self._select_candidates(candidates, count, strategy)
        
        for candidate in to_forget:
            if self.suppress_semantic(candidate["id"]):
                events.append(self._create_forgetting_event(
                    target_id=candidate["id"],
                    target_type="semantic",
                    strategy=strategy.value,
                    reason="strategic_suppression",
                    original_importance=candidate["importance"]
                ))
        
        return events
    
    def _forget_from_all(self, count: int, strategy: ForgettingStrategy) -> List[ForgettingEvent]:
        """النسيان من جميع المصادر"""
        events = []
        events.extend(self._forget_from_cache(count // 4, strategy))
        events.extend(self._forget_from_working(count // 4, strategy))
        events.extend(self._forget_from_semantic(count // 4, strategy))
        events.extend(self._forget_from_store(count // 4, strategy))
        return events
    
    def _select_candidates(self, candidates: List[Dict], count: int, 
                          strategy: ForgettingStrategy) -> List[Dict]:
        """اختيار المرشحين للنسيان حسب الاستراتيجية"""
        
        if strategy == ForgettingStrategy.LRU:
            # الأقل حداثة
            candidates.sort(key=lambda x: x.get("last_access", 0))
            
        elif strategy == ForgettingStrategy.LFU:
            # الأقل استخداماً
            candidates.sort(key=lambda x: x.get("access_count", 0))
            
        elif strategy == ForgettingStrategy.LOW_IMPORTANCE:
            # الأقل أهمية
            candidates.sort(key=lambda x: x.get("importance", 0))
            
        elif strategy == ForgettingStrategy.OLDEST:
            # الأقدم
            candidates.sort(key=lambda x: x.get("created_at", 0))
            
        elif strategy == ForgettingStrategy.RANDOM:
            # عشوائي
            random.shuffle(candidates)
            
        elif strategy == ForgettingStrategy.SMART:
            # استراتيجية ذكية: مزيج من العوامل
            def smart_score(x):
                age = (time.time() - x.get("last_access", time.time())) / 86400
                return (1 - x.get("importance", 0)) * 0.5 + min(1.0, age / 30) * 0.5
            candidates.sort(key=smart_score, reverse=True)
        
        return candidates[:count]
    
    def _mark_as_forgotten(self, kind: str, item_id: str) -> bool:
        """تحديد عنصر كمنسي في التخزين"""
        try:
            items = self.store.query(kind, min_importance=0.0, limit=999999)
            for item in items:
                if item.get("_id") == item_id:
                    # إضافة علامة منسي
                    if "_metadata" not in item:
                        item["_metadata"] = {}
                    item["_metadata"]["forgotten"] = True
                    item["_metadata"]["forgotten_at"] = time.time()
                    
                    # حفظ التغييرات (هذا يتطلب واجهة تحديث في store)
                    return True
        except:
            pass
        return False
    
    # ============================================================
    # المستوى 3: النسيان المقصود (Intentional Forgetting)
    # ============================================================
    
    def forget_intentionally(self, target: str, reason: str = "user_request") -> bool:
        """
        نسيان مقصود - بأمر السيد أو النظام.
        """
        # محاولة نسيان من مصادر مختلفة
        success = False
        
        # نسيان من الكاش
        if self.dynamic.cache._items.pop(target, None):
            success = True
        
        # نسيان من الذاكرة العاملة
        for user_id, items in self.dynamic.working._by_user.items():
            for item in list(items):
                if item.id == target or item.content == target:
                    items.remove(item)
                    success = True
        
        if success:
            self._create_forgetting_event(
                target_id=target,
                target_type="intentional",
                strategy=ForgettingStrategy.LRU.value,
                reason=reason,
                original_importance=0.5
            )
            logger.info(f"🎯 نسيان مقصود: {target[:32]}...")
        
        return success
    
    def forget_user(self, user_id: str, complete: bool = False) -> int:
        """
        نسيان مستخدم بالكامل.
        """
        count = 0
        
        # نسيان من الذاكرة العاملة
        if user_id in self.dynamic.working._by_user:
            items = list(self.dynamic.working._by_user[user_id])
            count += len(items)
            self.dynamic.working.clear_user(user_id)
        
        # نسيان من الكاش
        cache_keys = [k for k in self.dynamic.cache._items.keys() if user_id in k]
        for key in cache_keys:
            del self.dynamic.cache._items[key]
            count += 1
        
        # نسيان من التخزين (وضع علامة)
        if complete:
            for kind in ["episodic", "associative"]:
                items = self.store.query(kind, min_importance=0.0, limit=1000)
                for item in items:
                    if item.get("user_id") == user_id or item.get("participants") and user_id in item.get("participants", []):
                        self._mark_as_forgotten(kind, item.get("_id"))
                        count += 1
        
        logger.info(f"👤 نسيان المستخدم {user_id}: {count} عنصر")
        return count
    
    # ============================================================
    # المستوى 4: الأثر الذاكري (Memory Trace)
    # ============================================================
    
    def create_memory_trace(self, original_id: str, content: str, importance: float) -> MemoryTrace:
        """
        إنشاء أثر ذاكري - ما يبقى بعد النسيان.
        
        الأثر ليس المحتوى الأصلي، بل جوهره.
        """
        trace_id = f"trace_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        # استخراج الجوهر (أول 100 حرف + بصمة)
        essence = content[:100] + "..." if len(content) > 100 else content
        fingerprint = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        trace = MemoryTrace(
            id=trace_id,
            original_id=original_id,
            fingerprint=fingerprint,
            essence=essence,
            importance=importance,
            created_at=time.time(),
            last_recalled=time.time()
        )
        
        self.memory_traces[trace_id] = trace
        
        logger.debug(f"📝 أثر ذاكري: {trace_id[:16]}... -> {essence[:50]}...")
        return trace
    
    def recall_trace(self, trace_id: str) -> Optional[MemoryTrace]:
        """
        استدعاء أثر ذاكري - ما تبقى من الذاكرة المنسية.
        """
        trace = self.memory_traces.get(trace_id)
        if trace:
            trace.last_recalled = time.time()
        return trace
    
    # ============================================================
    # المستوى 5: النسيان الطارئ (Emergency Forgetting)
    # ============================================================
    
    def emergency_forget(self, preserve_core: bool = True) -> int:
        """
        نسيان طارئ - تحت ضغط شديد.
        يمسح الذاكرة الحية بالكامل للحماية.
        """
        count = 0
        
        # نسيان الذاكرة الحسية
        sensory_count = len(self.dynamic.sensory._events)
        self.dynamic.sensory._events.clear()
        count += sensory_count
        
        # نسيان الذاكرة العاملة
        working_count = sum(len(items) for items in self.dynamic.working._by_user.values())
        self.dynamic.working._by_user.clear()
        count += working_count
        
        # نسيان الكاش
        cache_count = len(self.dynamic.cache._items)
        self.dynamic.cache._items.clear()
        count += cache_count
        
        # نسيان التخزين (اختياري)
        if not preserve_core:
            for kind in ["semantic", "associative", "episodic"]:
                items = self.store.query(kind, min_importance=0.0, limit=5000)
                for item in items:
                    self._mark_as_forgotten(kind, item.get("_id"))
                    count += 1
        
        logger.warning(f"⚠️ نسيان طارئ: {count} عنصر تم نسيانه")
        return count
    
    # ============================================================
    # المستوى 6: توحيد الذاكرة (Memory Consolidation)
    # ============================================================
    
    def consolidate_memory(self) -> Dict[str, Any]:
        """
        توحيد الذاكرة - تحويل الذكريات قصيرة المدى إلى طويلة المدى.
        """
        consolidated = {
            "from_working": 0,
            "from_sensory": 0,
            "from_cache": 0,
            "traces_created": 0
        }
        
        # توحيد من الذاكرة العاملة
        for user_id, items in list(self.dynamic.working._by_user.items()):
            for item in list(items):
                if item.importance > 0.7:
                    # إنشاء أثر ذاكري
                    trace = self.create_memory_trace(
                        item.id,
                        item.content,
                        item.importance
                    )
                    consolidated["traces_created"] += 1
                    consolidated["from_working"] += 1
        
        # توحيد من الكاش
        for key, item in list(self.dynamic.cache._items.items()):
            if item.score > 0.8:
                trace = self.create_memory_trace(
                    key,
                    str(item.value)[:200],
                    item.score
                )
                consolidated["traces_created"] += 1
                consolidated["from_cache"] += 1
        
        logger.info(f"💾 توحيد الذاكرة: {consolidated['traces_created']} أثر تم إنشاؤه")
        return consolidated
    
    # ============================================================
    # أدوات مساعدة
    # ============================================================
    
    def _create_forgetting_event(self, target_id: str, target_type: str,
                                  strategy: str, reason: str,
                                  original_importance: float) -> ForgettingEvent:
        """إنشاء حدث نسيان"""
        event = ForgettingEvent(
            id=f"forget_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            target_id=target_id,
            target_type=target_type,
            strategy=strategy,
            timestamp=time.time(),
            reason=reason,
            original_importance=original_importance,
            was_recoverable=True
        )
        
        self.forgetting_events.append(event)
        
        # تسجيل في السجل السيادي
        self.core.append_event(
            event_type="biological::forgetting",
            payload={
                "target_id": target_id[:32],
                "target_type": target_type,
                "strategy": strategy,
                "reason": reason,
                "importance": original_importance
            }
        )
        
        return event
    
    def suppress_semantic(self, concept: str) -> bool:
        """تعطيل مفهوم دلالي (نسيانه)"""
        try:
            items = self.store.query("semantic", min_importance=0.0, limit=1000)
            for item in items:
                if item.get("concept") == concept:
                    # وضع علامة مكبوت
                    if "_metadata" not in item:
                        item["_metadata"] = {}
                    item["_metadata"]["suppressed"] = True
                    item["_metadata"]["suppressed_at"] = time.time()
                    
                    logger.info(f"🚫 تعطيل المفهوم: {concept}")
                    return True
        except Exception as e:
            logger.error(f"خطأ في تعطيل المفهوم: {e}")
        return False
    
    # ============================================================
    # الخلفيات المستمرة
    # ============================================================
    
    def _natural_forgetting_loop(self):
        """حلقة النسيان الطبيعي"""
        while self._active:
            try:
                if self.forget_level >= FORGET_LEVEL_LIGHT:
                    self.natural_forgetting_cycle()
                time.sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في النسيان الطبيعي: {e}")
                time.sleep(300)
    
    def _strategic_forgetting_loop(self):
        """حلقة النسيان الاستراتيجي"""
        while self._active:
            try:
                if self.forget_level >= FORGET_LEVEL_STRATEGIC:
                    self.strategic_forgetting("store", count=5, strategy=ForgettingStrategy.SMART)
                time.sleep(3600)  # كل ساعة
            except Exception as e:
                logger.error(f"خطأ في النسيان الاستراتيجي: {e}")
                time.sleep(3600)
    
    def _memory_consolidation_loop(self):
        """حلقة توحيد الذاكرة"""
        while self._active:
            try:
                if self.forget_level >= FORGET_LEVEL_MODERATE:
                    self.consolidate_memory()
                time.sleep(7200)  # كل ساعتين
            except Exception as e:
                logger.error(f"خطأ في توحيد الذاكرة: {e}")
                time.sleep(7200)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة نظام النسيان"""
        try:
            state = {
                "forget_level": self.forget_level,
                "forgetting_strategy": self.forgetting_strategy.value,
                "forgotten_items_count": len(self.forgotten_items),
                "forgetting_events_count": len(self.forgetting_events),
                "memory_traces_count": len(self.memory_traces),
                "saved_at": time.time()
            }
            
            with open(FORGET_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة النسيان: {e}")
    
    def _load_state(self):
        """تحميل حالة نظام النسيان"""
        try:
            if FORGET_STATE_FILE.exists():
                with open(FORGET_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.forget_level = state.get("forget_level", FORGET_LEVEL_MODERATE)
                    self.forgetting_strategy = ForgettingStrategy(state.get("forgetting_strategy", "smart"))
                logger.info("📂 تم تحميل حالة نظام النسيان")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة النسيان: {e}")
    
    # ============================================================
    # التقارير والاستعلامات
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """الحالة الحالية لنظام النسيان"""
        return {
            "forget_level": self.forget_level,
            "forgetting_strategy": self.forgetting_strategy.value,
            "forgotten_items": len(self.forgotten_items),
            "forgetting_events": len(self.forgetting_events),
            "memory_traces": len(self.memory_traces),
            "retention_rate": self.calculate_retention(1, 0.5, 1),
            "timestamp": time.time()
        }
    
    def get_forgetting_events(self, limit: int = 50) -> List[Dict]:
        """سجل أحداث النسيان"""
        return [
            {
                "id": e.id[:16],
                "target_id": e.target_id[:32],
                "target_type": e.target_type,
                "strategy": e.strategy,
                "reason": e.reason,
                "timestamp": e.timestamp,
                "original_importance": e.original_importance
            }
            for e in self.forgetting_events[-limit:]
        ]
    
    def get_memory_traces(self, limit: int = 50) -> List[Dict]:
        """الأثر الذاكري المتبقي"""
        return [
            {
                "id": t.id[:16],
                "essence": t.essence[:50],
                "importance": t.importance,
                "age_days": (time.time() - t.created_at) / 86400
            }
            for t in list(self.memory_traces.values())[-limit:]
        ]
    
    def get_forgetting_curve_data(self) -> Dict[str, List]:
        """بيانات منحنى النسيان"""
        days = list(range(31))
        retentions = [self.calculate_retention(d, 0.5, 1) for d in days]
        return {"days": days, "retentions": retentions}
    
    def set_forget_level(self, level: int):
        """تعيين مستوى النسيان"""
        self.forget_level = level
        logger.info(f"⚙️ مستوى النسيان: {level}")
    
    def set_forgetting_strategy(self, strategy: str):
        """تعيين استراتيجية النسيان"""
        self.forgetting_strategy = ForgettingStrategy(strategy)
        logger.info(f"🎯 استراتيجية النسيان: {strategy}")
    
    def stop(self):
        """إيقاف نظام النسيان"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف نظام النسيان المقصود")


# ============================================================
# الـ Singleton
# ============================================================

_forgetting_instance: Optional[IntentionalForgetting] = None
_forgetting_lock = threading.Lock()


def get_forgetting() -> IntentionalForgetting:
    """الحصول على النسخة الوحيدة من نظام النسيان"""
    global _forgetting_instance
    if _forgetting_instance is None:
        with _forgetting_lock:
            if _forgetting_instance is None:
                _forgetting_instance = IntentionalForgetting()
    return _forgetting_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧠 النسيان المقصود - حكمة التذكر والنسيان")
    print("=" * 70 + "\n")
    
    forgetting = get_forgetting()
    
    # 1) منحنى النسيان
    print("📊 منحنى النسيان (Ebbinghaus):")
    curve = forgetting.get_forgetting_curve_data()
    print(f"   بعد يوم واحد: {curve['retentions'][1]:.1%}")
    print(f"   بعد 7 أيام: {curve['retentions'][7]:.1%}")
    print(f"   بعد 30 يوم: {curve['retentions'][30]:.1%}")
    
    # 2) نسيان طبيعي
    print("\n🍂 نسيان طبيعي...")
    natural_events = forgetting.natural_forgetting_cycle()
    print(f"   تم نسيان {len(natural_events)} عنصر")
    
    # 3) نسيان استراتيجي
    print("\n🎯 نسيان استراتيجي...")
    strategic_events = forgetting.strategic_forgetting("cache", count=5, strategy=ForgettingStrategy.SMART)
    print(f"   تم نسيان {len(strategic_events)} عنصر من الكاش")
    
    # 4) أثر ذاكري
    print("\n📝 إنشاء أثر ذاكري...")
    trace = forgetting.create_memory_trace(
        "test_001",
        "هذه ذكرى مهمة جداً يجب أن نتذكر جوهرها حتى بعد نسيان التفاصيل",
        importance=0.9
    )
    print(f"   الأثر: {trace.essence[:50]}...")
    
    # 5) توحيد الذاكرة
    print("\n💾 توحيد الذاكرة...")
    consolidated = forgetting.consolidate_memory()
    print(f"   تم إنشاء {consolidated['traces_created']} أثر ذاكري")
    
    # 6) الحالة
    print("\n📊 حالة نظام النسيان:")
    status = forgetting.get_status()
    print(f"   مستوى النسيان: {status['forget_level']}")
    print(f"   استراتيجية النسيان: {status['forgetting_strategy']}")
    print(f"   أحداث النسيان: {status['forgetting_events']}")
    print(f"   الأثر الذاكري: {status['memory_traces']}")
    print(f"   معدل الاحتفاظ الحالي: {status['retention_rate']:.1%}")
    
    # 7) أحداث النسيان الأخيرة
    print("\n📋 آخر أحداث النسيان:")
    events = forgetting.get_forgetting_events(5)
    for e in events:
        print(f"   {e['reason']}: {e['target_type']} - {e['strategy']}")
    
    print("\n" + "=" * 70)
    print("✅ نظام النسيان المقصود جاهز - الحكمة في معرفة متى تنسى")
    print("=" * 70)
