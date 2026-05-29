# backend/memory/dynamic/__init__.py
# 🌊 الذاكرة الحية - النسخة الجبارة
# الإصدار: 2.0.0 - ذاكرة تتنفس، تتذكر، تنسى، وتحلم

"""
الذاكرة الحية للعقل السيادي.

هذه الطبقة هي الوعي اللحظي للنظام:
- الحسية: ما يدخل الآن (تعيش للحظات)
- المؤقتة: طابور ذكي بين الحسية والعاملة
- العاملة: مسرح الوعي (7 ± 2 وحدات لكل مستخدم)
- المخبئية: توقع المستقبل (ما سنحتاجه قريباً)
- العاطفية اللحظية: المشاعر الآنية
- الحالمة: إعادة التنظيم أثناء الخمول

كل هذا يعمل في الذاكرة (RAM) بسرعة الضوء.
"""

import time
import math
import heapq
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Deque, Dict, List, Optional, Tuple, Set, Callable
from enum import Enum
from datetime import datetime
import random

try:
    from ..core import get_core, EventType
    from ..views import get_views
    from ..store import get_store
except ImportError:
    from core import get_core, EventType
    from views import get_views
    from store import get_store

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت والإعدادات
# ============================================================

# الذاكرة الحسية
SENSORY_MAX_EVENTS = 512
SENSORY_TTL_SECONDS = 5.0
SENSORY_CHANNELS = ["text", "audio", "vision", "touch", "thought", "emotion", "intuition"]

# الذاكرة المؤقتة
BUFFER_MAX_SIZE = 1024
BUFFER_PRIORITY_LEVELS = ["critical", "high", "normal", "low", "background"]
BUFFER_PRIORITY_WEIGHTS = {"critical": 1.0, "high": 0.8, "normal": 0.5, "low": 0.2, "background": 0.0}

# الذاكرة العاملة (قانون ميلر - 7 ± 2)
WORKING_MAX_PER_USER = 9
WORKING_ATTENTION_DECAY = 0.1  # 10% فقدان انتباه كل دقيقة
WORKING_IMPORTANCE_BOOST = 0.2

# الذاكرة المخبئية
CACHE_MAX_ITEMS = 2048
CACHE_DEFAULT_TTL = 300  # 5 دقائق
CACHE_HOT_TTL = 3600     # ساعة واحدة للعناصر الساخنة
CACHE_PRELOAD_THRESHOLD = 0.7  # توقع ما سنحتاج

# الحلم (إعادة التنظيم)
DREAMING_INTERVAL = 300  # 5 دقائق
DREAMING_DURATION = 60   # دقيقة واحدة
DREAMING_CONSOLIDATION_RATE = 0.3

# المعالجة الخلفية
BACKGROUND_PROCESSING_INTERVAL = 1.0  # ثانية
ATTENTION_CLEANUP_INTERVAL = 60       # دقيقة


# ============================================================
# الأنواع والتعدادات
# ============================================================

class SensoryChannel(str, Enum):
    """قنوات الذاكرة الحسية"""
    TEXT = "text"
    AUDIO = "audio"
    VISION = "vision"
    TOUCH = "touch"
    THOUGHT = "thought"
    EMOTION = "emotion"
    INTUITION = "intuition"
    INTERNAL = "internal"


class BufferPriority(str, Enum):
    """مستويات الأولوية في الذاكرة المؤقتة"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class AttentionState(str, Enum):
    """حالات الانتباه في الذاكرة العاملة"""
    FOCUSED = "focused"      # تركيز عالي
    AWARE = "aware"          # واعي
    PERIPHERAL = "peripheral" # هامشي
    DORMANT = "dormant"      # خامل


# ============================================================
# نماذج البيانات المتطورة
# ============================================================

@dataclass
class SensoryEvent:
    """حدث حسي - لحظة دخول المعلومة"""
    id: str
    channel: str
    payload: Dict[str, Any]
    timestamp: float
    intensity: float  # 0-1 شدة الإحساس
    novelty: float    # 0-1 مدى الجدة
    source: str
    attention_captured: bool = False
    
    def age(self) -> float:
        return time.time() - self.timestamp
    
    def is_expired(self) -> bool:
        return self.age() > SENSORY_TTL_SECONDS
    
    def should_capture_attention(self) -> bool:
        return self.intensity > 0.7 or self.novelty > 0.8


@dataclass
class BufferItem:
    """عنصر في الذاكرة المؤقتة"""
    id: str
    payload: Dict[str, Any]
    timestamp: float
    priority: str
    priority_score: float
    source: str
    retry_count: int = 0
    max_retries: int = 3
    
    def should_retry(self) -> bool:
        return self.retry_count < self.max_retries


@dataclass
class WorkingItem:
    """عنصر في الذاكرة العاملة (مسرح الوعي)"""
    id: str
    user_id: str
    role: str  # "user", "assistant", "system", "self"
    content: str
    timestamp: float
    importance: float
    attention_state: str
    associations: List[str]  # روابط إلى عناصر أخرى
    emotions: Dict[str, float]
    predicted_next: Optional[str] = None
    
    def attention_weight(self) -> float:
        """وزن الانتباه الحالي (يتلاشى مع الوقت)"""
        age = time.time() - self.timestamp
        decay = math.exp(-WORKING_ATTENTION_DECAY * age / 60)  # تلاشي كل دقيقة
        base = 1.0 if self.attention_state == AttentionState.FOCUSED.value else 0.7 if self.attention_state == AttentionState.AWARE.value else 0.4 if self.attention_state == AttentionState.PERIPHERAL.value else 0.1
        return base * decay


@dataclass
class CacheItem:
    """عنصر في الذاكرة المخبئية"""
    key: str
    value: Any
    score: float
    last_access: float
    access_count: int
    predicted_next_access: Optional[float] = None
    ttl: float = CACHE_DEFAULT_TTL
    
    def is_hot(self) -> bool:
        return self.access_count > 5 or self.score > 0.8
    
    def is_expired(self) -> bool:
        return time.time() - self.last_access > self.ttl


@dataclass
class EmotionalState:
    """الحالة العاطفية اللحظية"""
    emotion: str
    intensity: float
    valence: float  # -1 إلى +1
    arousal: float  # 0 إلى 1
    timestamp: float
    source: str
    
    def current_intensity(self) -> float:
        age = time.time() - self.timestamp
        decay = math.exp(-age / 60)  # تلاشي خلال دقيقة
        return self.intensity * decay


@dataclass
class DreamFragment:
    """جزء من الحلم - إعادة تنظيم الذاكرة"""
    id: str
    content: str
    associations: List[str]
    timestamp: float
    consolidation_score: float
    integrated: bool = False


# ============================================================
# الذاكرة الحسية (Sensory) - ما يدخل الآن
# ============================================================

class SensoryMemory:
    """
    الذاكرة الحسية - البوابة إلى العالم.
    
    تحاكي: العين ترمش، الأذن تسمع، الجلد يلمس.
    تعيش للحظات ثم تختفي (إلا ما يلتقط الانتباه).
    """
    
    def __init__(self, max_events: int = SENSORY_MAX_EVENTS):
        self.max_events = max_events
        self._events: Deque[SensoryEvent] = deque()
        self._attention_queue: Deque[SensoryEvent] = deque()
        self._lock = threading.RLock()
        self._event_counter = 0
        
        logger.info(f"👁️ الذاكرة الحسية جاهزة (سعة: {max_events})")
    
    def _next_id(self) -> str:
        self._event_counter += 1
        return f"sen_{self._event_counter}_{int(time.time()*1000)}"
    
    def add(self, channel: str, payload: Dict[str, Any],
            intensity: float = 0.5, novelty: float = 0.3,
            source: str = "external") -> Optional[str]:
        """إضافة حدث حسي جديد"""
        with self._lock:
            event_id = self._next_id()
            
            event = SensoryEvent(
                id=event_id,
                channel=channel,
                payload=payload,
                timestamp=time.time(),
                intensity=min(1.0, max(0.0, intensity)),
                novelty=min(1.0, max(0.0, novelty)),
                source=source
            )
            
            self._events.append(event)
            
            # هل يلتقط الانتباه؟
            if event.should_capture_attention():
                event.attention_captured = True
                self._attention_queue.append(event)
            
            # الحفاظ على الحجم
            while len(self._events) > self.max_events:
                self._events.popleft()
            
            while len(self._attention_queue) > self.max_events // 4:
                self._attention_queue.popleft()
            
            logger.debug(f"📥 حسية: [{channel}] {str(payload)[:50]}... (شدة: {intensity})")
            return event_id
    
    def get_latest(self, channel: Optional[str] = None, limit: int = 20) -> List[SensoryEvent]:
        """الحصول على أحدث الأحداث الحسية"""
        with self._lock:
            self._cleanup()
            
            events = list(self._events)
            if channel:
                events = [e for e in events if e.channel == channel]
            
            return events[-limit:][::-1]
    
    def get_attention_capturing(self) -> List[SensoryEvent]:
        """الحصول على الأحداث التي التقطت الانتباه"""
        with self._lock:
            self._cleanup()
            return list(self._attention_queue)
    
    def _cleanup(self):
        """إزالة الأحداث منتهية الصلاحية"""
        while self._events and self._events[0].is_expired():
            self._events.popleft()
        
        while self._attention_queue and self._attention_queue[0].is_expired():
            self._attention_queue.popleft()
    
    def clear(self):
        """مسح الذاكرة الحسية"""
        with self._lock:
            self._events.clear()
            self._attention_queue.clear()
            logger.info("🧹 الذاكرة الحسية مُسحت")
    
    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_events": len(self._events),
                "attention_events": len(self._attention_queue),
                "channels": list(set(e.channel for e in self._events))
            }


# ============================================================
# الذاكرة المؤقتة (Buffer) - طابور ذكي
# ============================================================

class BufferMemory:
    """
    الذاكرة المؤقتة - طابور أولويات ذكي.
    
    بين الحسية والعاملة. يقرر ما يستحق المعالجة الآن وما يتأخر.
    """
    
    def __init__(self, max_size: int = BUFFER_MAX_SIZE):
        self.max_size = max_size
        self._items: List[BufferItem] = []  # heap
        self._lock = threading.RLock()
        self._counter = 0
        self._processed_count = 0
        
        logger.info(f"📦 الذاكرة المؤقتة جاهزة (سعة: {max_size})")
    
    def _next_id(self) -> str:
        self._counter += 1
        return f"buf_{self._counter}_{int(time.time()*1000)}"
    
    def _get_priority_score(self, priority: str) -> float:
        """حساب درجة الأولوية"""
        base = BUFFER_PRIORITY_WEIGHTS.get(priority, 0.5)
        # إضافة عامل الزمن (الأقدم يزيد وزنه قليلاً)
        return base
    
    def push(self, payload: Dict[str, Any], 
             priority: str = "normal",
             source: str = "sensory") -> str:
        """إضافة عنصر إلى المؤقتة"""
        with self._lock:
            item_id = self._next_id()
            priority_score = self._get_priority_score(priority)
            
            item = BufferItem(
                id=item_id,
                payload=payload,
                timestamp=time.time(),
                priority=priority,
                priority_score=priority_score,
                source=source
            )
            
            # استخدام heap مع سالب الأولوية للأعلى أولاً
            heapq.heappush(self._items, (-priority_score, item.timestamp, item))
            
            # الحفاظ على الحجم
            while len(self._items) > self.max_size:
                heapq.heappop(self._items)
            
            logger.debug(f"📋 مؤقتة: [{priority}] {str(payload)[:50]}...")
            return item_id
    
    def pop(self) -> Optional[BufferItem]:
        """سحب العنصر ذو الأولوية الأعلى"""
        with self._lock:
            if not self._items:
                return None
            
            _, _, item = heapq.heappop(self._items)
            self._processed_count += 1
            logger.debug(f"🔄 معالجة: {item.id[:12]}... (أولوية: {item.priority})")
            return item
    
    def peek(self, limit: int = 10) -> List[BufferItem]:
        """النظر إلى العناصر دون سحبها"""
        with self._lock:
            items = sorted(self._items, key=lambda x: (-x[0], x[1]))
            return [item for _, _, item in items[:limit]]
    
    def retry(self, item: BufferItem, increase_priority: bool = True) -> bool:
        """إعادة محاولة معالجة عنصر فشل"""
        if not item.should_retry():
            return False
        
        item.retry_count += 1
        if increase_priority:
            # رفع الأولوية عند إعادة المحاولة
            new_priority = {
                "critical": "critical",
                "high": "critical",
                "normal": "high",
                "low": "normal",
                "background": "low"
            }.get(item.priority, "normal")
            item.priority = new_priority
            item.priority_score = self._get_priority_score(new_priority)
        
        heapq.heappush(self._items, (-item.priority_score, item.timestamp, item))
        return True
    
    def size(self) -> int:
        with self._lock:
            return len(self._items)
    
    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            priorities = [item.priority for _, _, item in self._items]
            return {
                "size": len(self._items),
                "processed_total": self._processed_count,
                "by_priority": {p: priorities.count(p) for p in BUFFER_PRIORITY_LEVELS}
            }


# ============================================================
# الذاكرة العاملة (Working) - مسرح الوعي
# ============================================================

class WorkingMemory:
    """
    الذاكرة العاملة - مسرح الوعي الحالي.
    
    تحاكي: ما تفكر فيه الآن. سعة محدودة (7 ± 2 وحدات).
    لكل مستخدم مسرح مستقل.
    """
    
    def __init__(self, max_per_user: int = WORKING_MAX_PER_USER):
        self.max_per_user = max_per_user
        self._by_user: Dict[str, Deque[WorkingItem]] = defaultdict(deque)
        self._lock = threading.RLock()
        self._counter = 0
        self._total_items = 0
        
        logger.info(f"🎭 الذاكرة العاملة جاهزة (سعة لكل مستخدم: {max_per_user})")
    
    def _next_id(self) -> str:
        self._counter += 1
        return f"wrk_{self._counter}_{int(time.time()*1000)}"
    
    def add(self, user_id: str, role: str, content: str,
            importance: float = 0.5,
            attention_state: str = "aware",
            associations: Optional[List[str]] = None,
            emotions: Optional[Dict[str, float]] = None) -> str:
        """إضافة عنصر إلى الذاكرة العاملة لمستخدم"""
        if associations is None:
            associations = []
        if emotions is None:
            emotions = {}
        
        with self._lock:
            item_id = self._next_id()
            
            item = WorkingItem(
                id=item_id,
                user_id=user_id,
                role=role,
                content=content[:500],  # حد أقصى
                timestamp=time.time(),
                importance=min(1.0, max(0.0, importance)),
                attention_state=attention_state,
                associations=associations,
                emotions=emotions
            )
            
            dq = self._by_user[user_id]
            dq.append(item)
            self._total_items += 1
            
            # الحفاظ على السعة
            while len(dq) > self.max_per_user:
                removed = dq.popleft()
                logger.debug(f"🧠 نسيان: {removed.id[:12]}... (خروج من الذاكرة العاملة)")
            
            # تحديث حالة الانتباه للعناصر الأخرى
            self._update_attention_states(user_id)
            
            logger.debug(f"🎭 عاملة [{user_id}]: {role} - {content[:50]}... (أهمية: {importance})")
            return item_id
    
    def _update_attention_states(self, user_id: str):
        """تحديث حالات الانتباه لجميع عناصر المستخدم"""
        dq = self._by_user.get(user_id, deque())
        items = list(dq)
        
        # العنصر الأحدث يحصل على أعلى انتباه
        for i, item in enumerate(reversed(items)):
            if i == 0:
                item.attention_state = AttentionState.FOCUSED.value
            elif i == 1:
                item.attention_state = AttentionState.AWARE.value
            elif i <= 3:
                item.attention_state = AttentionState.PERIPHERAL.value
            else:
                item.attention_state = AttentionState.DORMANT.value
    
    def context(self, user_id: str, limit: Optional[int] = None) -> List[WorkingItem]:
        """استرجاع سياق المستخدم الحالي"""
        with self._lock:
            items = list(self._by_user.get(user_id, deque()))
            
            # ترتيب حسب الوزن (الانتباه + الأهمية)
            items.sort(key=lambda x: x.attention_weight() * x.importance, reverse=True)
            
            if limit:
                return items[:limit]
            return items
    
    def get_focused(self, user_id: str) -> Optional[WorkingItem]:
        """الحصول على العنصر الذي يحظى بالتركيز الأعلى"""
        context = self.context(user_id)
        return context[0] if context else None
    
    def shift_attention(self, user_id: str, target_item_id: str) -> bool:
        """تحويل الانتباه إلى عنصر معين"""
        with self._lock:
            dq = self._by_user.get(user_id, deque())
            items = list(dq)
            
            for i, item in enumerate(items):
                if item.id == target_item_id:
                    # نقل إلى مقدمة الطابور
                    items.pop(i)
                    items.insert(0, item)
                    self._by_user[user_id] = deque(items)
                    self._update_attention_states(user_id)
                    logger.debug(f"🎯 تحويل الانتباه [{user_id}] -> {target_item_id[:12]}")
                    return True
            
            return False
    
    def clear_user(self, user_id: str):
        """مسح ذاكرة عامل لمستخدم"""
        with self._lock:
            if user_id in self._by_user:
                count = len(self._by_user[user_id])
                del self._by_user[user_id]
                logger.info(f"🧹 مسح عاملة [{user_id}]: {count} عنصر")
    
    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_users": len(self._by_user),
                "total_items": self._total_items,
                "by_user": {u: len(items) for u, items in self._by_user.items()}
            }


# ============================================================
# الذاكرة المخبئية (Cache) - توقع المستقبل
# ============================================================

class CacheMemory:
    """
    الذاكرة المخبئية - توقع ما سنحتاجه قريباً.
    
    تحاكي: لماذا نحفظ نتائج الحسابات؟ لأننا سنستخدمها مرة أخرى.
    مع خوارزمية توقع ذكية.
    """
    
    def __init__(self, max_items: int = CACHE_MAX_ITEMS):
        self.max_items = max_items
        self._items: Dict[str, CacheItem] = {}
        self._access_patterns: Dict[str, List[float]] = defaultdict(list)  # key -> timestamps
        self._predictions: Dict[str, float] = {}  # key -> predicted next access
        self._lock = threading.RLock()
        self._hit_count = 0
        self._miss_count = 0
        
        logger.info(f"⚡ الذاكرة المخبئية جاهزة (سعة: {max_items})")
    
    def _predict_next_access(self, key: str) -> Optional[float]:
        """توقع وقت الوصول التالي بناءً على الأنماط السابقة"""
        timestamps = self._access_patterns.get(key, [])
        if len(timestamps) < 2:
            return None
        
        # حساب متوسط الفرق بين الوصولات
        diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        avg_diff = sum(diffs) / len(diffs)
        
        return timestamps[-1] + avg_diff
    
    def set(self, key: str, value: Any, score: float = 0.5, ttl: Optional[float] = None) -> None:
        """تخزين قيمة في الكاش"""
        with self._lock:
            now = time.time()
            ttl = ttl or (CACHE_HOT_TTL if score > 0.8 else CACHE_DEFAULT_TTL)
            
            if key in self._items:
                item = self._items[key]
                item.value = value
                item.score = max(item.score, score)
                item.last_access = now
                item.access_count += 1
                item.ttl = ttl
            else:
                item = CacheItem(
                    key=key,
                    value=value,
                    score=score,
                    last_access=now,
                    access_count=1,
                    ttl=ttl
                )
                self._items[key] = item
            
            # تحديث أنماط الوصول
            self._access_patterns[key].append(now)
            if len(self._access_patterns[key]) > 10:
                self._access_patterns[key] = self._access_patterns[key][-10:]
            
            # توقع الوصول التالي
            self._predictions[key] = self._predict_next_access(key) or now + 60
            
            self._evict_if_needed()
    
    def get(self, key: str) -> Optional[Any]:
        """استرجاع قيمة من الكاش"""
        with self._lock:
            item = self._items.get(key)
            if not item:
                self._miss_count += 1
                return None
            
            if item.is_expired():
                del self._items[key]
                self._miss_count += 1
                return None
            
            # تحديث
            item.last_access = time.time()
            item.access_count += 1
            item.score = min(1.0, item.score + 0.05)
            
            # تحديث التوقع
            self._predictions[key] = self._predict_next_access(key) or time.time() + 60
            
            self._hit_count += 1
            return item.value
    
    def _evict_if_needed(self):
        """إزالة العناصر الأقل أهمية عند تجاوز السعة"""
        if len(self._items) <= self.max_items:
            return
        
        # حساب درجة الإخلاء (كلما قلت القيمة، زادت فرصة الإخلاء)
        now = time.time()
        items_with_score = []
        
        for key, item in self._items.items():
            # عناصر ساخنة لا تُطرد
            if item.is_hot():
                continue
            
            # درجة الإخلاء: كلما كانت القيمة أقل، كلما زادت
            eviction_score = (1 - item.score) * 0.5 + (item.last_access / now) * 0.3
            items_with_score.append((eviction_score, key))
        
        items_with_score.sort(reverse=True)
        
        # إزالة أسوأ 10%
        to_remove = int(len(self._items) * 0.1)
        for i in range(min(to_remove, len(items_with_score))):
            _, key = items_with_score[i]
            if key in self._items:
                del self._items[key]
    
    def preload(self, pattern: str, generator: Callable[[], Any]) -> Optional[Any]:
        """تحميل مسبق بناءً على نمط متوقع"""
        # التحقق مما إذا كنا نتوقع الحاجة لهذا النمط
        for key, pred_time in self._predictions.items():
            if pattern in key and pred_time < time.time() + 60:
                # نحتاج هذا قريباً
                if key not in self._items:
                    value = generator()
                    self.set(key, value, score=0.6)
                    return value
                return self.get(key)
        return None
    
    def hit_rate(self) -> float:
        """نسبة النجاح في الكاش"""
        total = self._hit_count + self._miss_count
        if total == 0:
            return 0.0
        return self._hit_count / total
    
    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._items),
                "hot_items": sum(1 for i in self._items.values() if i.is_hot()),
                "hit_rate": self.hit_rate(),
                "hits": self._hit_count,
                "misses": self._miss_count,
                "predictions": len(self._predictions)
            }


# ============================================================
# الذاكرة العاطفية اللحظية (Emotional) - المشاعر الآنية
# ============================================================

class EmotionalMemory:
    """
    الذاكرة العاطفية اللحظية - ما نشعر به الآن.
    
    تتغير مع الوقت، تؤثر على الانتباه واتخاذ القرارات.
    """
    
    def __init__(self):
        self._states: Dict[str, EmotionalState] = {}
        self._current_mood: Dict[str, float] = defaultdict(float)  # emotion -> intensity
        self._lock = threading.RLock()
        
        logger.info("💖 الذاكرة العاطفية اللحظية جاهزة")
    
    def feel(self, emotion: str, intensity: float, valence: float, arousal: float, source: str) -> None:
        """تسجيل شعور لحظي"""
        with self._lock:
            state = EmotionalState(
                emotion=emotion,
                intensity=min(1.0, max(0.0, intensity)),
                valence=min(1.0, max(-1.0, valence)),
                arousal=min(1.0, max(0.0, arousal)),
                timestamp=time.time(),
                source=source
            )
            self._states[emotion] = state
            self._current_mood[emotion] = state.current_intensity()
    
    def get_mood(self) -> Dict[str, float]:
        """الحصول على المزاج الحالي"""
        with self._lock:
            # تنظيف المشاعر القديمة
            for emotion, state in list(self._states.items()):
                if state.current_intensity() < 0.01:
                    del self._states[emotion]
            
            return {emotion: state.current_intensity() for emotion, state in self._states.items()}
    
    def dominant_emotion(self) -> Tuple[str, float]:
        """المشاعر السائدة حالياً"""
        mood = self.get_mood()
        if not mood:
            return ("neutral", 0.0)
        dominant = max(mood.items(), key=lambda x: x[1])
        return dominant
    
    def influence_importance(self, base_importance: float) -> float:
        """تأثير المشاعر على الأهمية"""
        mood = self.get_mood()
        # المشاعر الإيجابية تزيد الأهمية قليلاً، السلبية تزيد كثيراً (للتجنب)
        positive_boost = mood.get("joy", 0) * 0.1
        negative_boost = (mood.get("fear", 0) + mood.get("anger", 0)) * 0.3
        return min(1.0, base_importance + positive_boost + negative_boost)
    
    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_emotions": len(self._states),
                "current_mood": self.dominant_emotion(),
                "all_moods": self.get_mood()
            }


# ============================================================
# الذاكرة الحالمة (Dreaming) - إعادة التنظيم
# ============================================================

class DreamingMemory:
    """
    الذاكرة الحالمة - إعادة تنظيم أثناء الخمول.
    
    تحاكي: لماذا نحلم؟ لتثبيت الذكريات، ربطها، وخلق روابط جديدة.
    """
    
    def __init__(self, working_memory: WorkingMemory, store=None):
        self.working = working_memory
        self.store = store
        self._dreams: List[DreamFragment] = []
        self._dreaming = False
        self._last_dream = time.time()
        self._lock = threading.RLock()
        
        logger.info("🌙 الذاكرة الحالمة جاهزة")
    
    def should_dream(self) -> bool:
        """هل حان وقت الحلم؟"""
        return (time.time() - self._last_dream) > DREAMING_INTERVAL and not self._dreaming
    
    def dream(self):
        """بدء جلسة حلم - إعادة تنظيم الذاكرة"""
        if not self.should_dream():
            return
        
        with self._lock:
            self._dreaming = True
            logger.info("🌙 بدء جلسة حلم...")
            
            # جمع العناصر من الذاكرة العاملة
            fragments = []
            for user_id in list(self.working._by_user.keys()):
                for item in self.working.context(user_id):
                    # إنشاء حلم من الذاكرة العاملة
                    fragment = DreamFragment(
                        id=f"dream_{item.id}",
                        content=item.content,
                        associations=item.associations + [user_id],
                        timestamp=time.time(),
                        consolidation_score=item.importance * item.attention_weight()
                    )
                    fragments.append(fragment)
            
            # معالجة الأحلام - تثبيت الذكريات المهمة
            for fragment in fragments:
                if fragment.consolidation_score > DREAMING_CONSOLIDATION_RATE:
                    # تسجيل في الذاكرة طويلة المدى
                    if self.store:
                        self.store.save_episodic(
                            title=f"حلم: {fragment.content[:50]}",
                            description=fragment.content,
                            importance=fragment.consolidation_score
                        )
                    fragment.integrated = True
            
            self._dreams.extend(fragments)
            # الاحتفاظ بآخر 100 حلم
            if len(self._dreams) > 100:
                self._dreams = self._dreams[-100:]
            
            self._last_dream = time.time()
            self._dreaming = False
            logger.info(f"🌙 اكتمل الحلم: تم تثبيت {sum(1 for f in fragments if f.integrated)} عنصر")
    
    def get_last_dreams(self, limit: int = 10) -> List[DreamFragment]:
        """الحصول على آخر الأحلام"""
        with self._lock:
            return self._dreams[-limit:]


# ============================================================
# الواجهة الموحدة - الذاكرة الحية
# ============================================================

class DynamicMemory:
    """
    الذاكرة الحية الموحدة.
    
    تجمع:
    - الحسية (بوابة العالم)
    - المؤقتة (طابور الأولويات)
    - العاملة (مسرح الوعي)
    - المخبئية (توقع المستقبل)
    - العاطفية (المشاعر اللحظية)
    - الحالمة (إعادة التنظيم)
    """
    
    def __init__(self):
        self.core = get_core()
        self.views = get_views()
        self.store = get_store()
        
        # المكونات
        self.sensory = SensoryMemory()
        self.buffer = BufferMemory()
        self.working = WorkingMemory()
        self.cache = CacheMemory()
        self.emotional = EmotionalMemory()
        self.dreaming = DreamingMemory(self.working, self.store)
        
        # المعالجة الخلفية
        self._processing = True
        self._processor_thread = threading.Thread(target=self._background_processor, daemon=True)
        self._processor_thread.start()
        
        # معالج الانتباه
        self._attention_thread = threading.Thread(target=self._attention_cleaner, daemon=True)
        self._attention_thread.start()
        
        # الحالم
        self._dreamer_thread = threading.Thread(target=self._dreamer_loop, daemon=True)
        self._dreamer_thread.start()
        
        logger.info("🌊 الذاكرة الحية المتكاملة جاهزة")
    
    # ============================================================
    # الواجهات الرئيسية
    # ============================================================
    
    def ingest(self, user_id: str, text: str, 
               intensity: float = 0.5,
               priority: str = "normal") -> str:
        """
        إدخال نص جديد إلى الذاكرة الحية.
        
        المسار: حسية → مؤقتة → عاملة
        """
        # 1) دخول إلى الذاكرة الحسية
        sensory_id = self.sensory.add(
            channel="text",
            payload={"user_id": user_id, "text": text},
            intensity=intensity,
            source="user_input"
        )
        
        # 2) دفع إلى المؤقتة للمعالجة
        buffer_id = self.buffer.push(
            payload={"user_id": user_id, "text": text, "sensory_id": sensory_id},
            priority=priority,
            source="ingest"
        )
        
        # 3) إضافة مباشرة إلى العاملة (لأننا نعرف أنها مهمة)
        working_id = self.working.add(
            user_id=user_id,
            role="user",
            content=text,
            importance=intensity,
            attention_state="focused" if intensity > 0.7 else "aware"
        )
        
        # تحديث الحالة العاطفية بناءً على النص
        self._analyze_emotional_content(text)
        
        logger.info(f"📝 استيعاب [{user_id}]: {text[:50]}...")
        return working_id
    
    def _analyze_emotional_content(self, text: str):
        """تحليل المشاعر في النص (بسيط، يمكن تطويره)"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["شكر", "جميل", "رائع", "ممتاز"]):
            self.emotional.feel("joy", 0.6, 0.7, 0.4, "text_analysis")
        elif any(word in text_lower for word in ["خطر", "حذار", "اهرب", "خوف"]):
            self.emotional.feel("fear", 0.7, -0.6, 0.8, "text_analysis")
        elif any(word in text_lower for word in ["غضب", "سخط", "كره"]):
            self.emotional.feel("anger", 0.6, -0.7, 0.7, "text_analysis")
    
    def process_input(self) -> Optional[Dict[str, Any]]:
        """
        معالجة المدخلات في المؤقتة.
        يُستدعى بشكل دوري في الخلفية.
        """
        item = self.buffer.pop()
        if not item:
            return None
        
        # تحديث حالة الانتباه بناءً على الأولوية
        if item.priority in ["critical", "high"]:
            self.emotional.feel("anticipation", 0.5, 0.3, 0.6, "buffer_processing")
        
        return {
            "processed": True,
            "item_id": item.id,
            "priority": item.priority,
            "payload": item.payload
        }
    
    def get_context(self, user_id: str, limit: int = 7) -> List[Dict[str, Any]]:
        """
        استرجاع السياق الحالي للمستخدم.
        حاول من الكاش أولاً، ثم من العاملة.
        """
        cache_key = f"context::{user_id}"
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
        
        context = []
        for item in self.working.context(user_id, limit=limit):
            context.append({
                "role": item.role,
                "content": item.content,
                "importance": item.importance,
                "attention": item.attention_state
            })
        
        # تخزين في الكاش للاستخدام القادم
        self.cache.set(cache_key, context, score=0.7, ttl=30)
        
        return context
    
    def register_response(self, user_id: str, response: str, importance: float = 0.6):
        """تسجيل رد الذكاء في الذاكرة العاملة"""
        self.working.add(
            user_id=user_id,
            role="assistant",
            content=response,
            importance=importance,
            attention_state="focused"
        )
        
        # تحديث الكاش
        self.cache.set(f"response::{user_id}", response, score=importance)
        
        # إضافة إلى المؤقتة للمعالجة اللاحقة (ربما تحليل)
        self.buffer.push(
            payload={"user_id": user_id, "response": response, "type": "ai_response"},
            priority="low",
            source="response"
        )
    
    def get_mood(self) -> Dict[str, float]:
        """الحصول على المزاج الحالي للذكاء"""
        return self.emotional.get_mood()
    
    def preload_context(self, user_id: str):
        """تحميل السياق مسبقاً (توقع)"""
        cache_key = f"context::{user_id}"
        context = self.get_context(user_id)
        self.cache.set(cache_key, context, score=0.8)
    
    def forget_user(self, user_id: str):
        """نسيان مستخدم (إزالة من الذاكرة العاملة)"""
        self.working.clear_user(user_id)
        self.cache.set(f"context::{user_id}", [], score=0)
        logger.info(f"👋 نسيان المستخدم: {user_id}")
    
    # ============================================================
    # المعالجة الخلفية
    # ============================================================
    
    def _background_processor(self):
        """معالج خلفية للمؤقتة"""
        while self._processing:
            try:
                # معالجة العناصر في المؤقتة
                for _ in range(5):  # حتى 5 عناصر في كل دورة
                    self.process_input()
                
                # تحديث الكاش المسبق
                for user_id in list(self.working._by_user.keys()):
                    self.preload_context(user_id)
                
                time.sleep(BACKGROUND_PROCESSING_INTERVAL)
            except Exception as e:
                logger.error(f"خطأ في المعالجة الخلفية: {e}")
                time.sleep(1)
    
    def _attention_cleaner(self):
        """تنظيف الانتباه بشكل دوري"""
        while self._processing:
            try:
                time.sleep(ATTENTION_CLEANUP_INTERVAL)
                
                # تنظيف المستخدمين غير النشطين
                active_threshold = 300  # 5 دقائق
                now = time.time()
                
                for user_id, items in list(self.working._by_user.items()):
                    if items and (now - items[-1].timestamp) > active_threshold:
                        # المستخدم غير نشط
                        self.working.clear_user(user_id)
                        logger.debug(f"🧹 تنظيف مستخدم غير نشط: {user_id}")
                
                logger.debug("🧹 اكتمل تنظيف الانتباه")
            except Exception as e:
                logger.error(f"خطأ في تنظيف الانتباه: {e}")
    
    def _dreamer_loop(self):
        """حلقة الحلم الدورية"""
        while self._processing:
            try:
                if self.dreaming.should_dream():
                    self.dreaming.dream()
                time.sleep(30)  # فحص كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في الحلم: {e}")
                time.sleep(60)
    
    # ============================================================
    # الإحصائيات
    # ============================================================
    
    def statistics(self) -> Dict[str, Any]:
        return {
            "sensory": self.sensory.statistics(),
            "buffer": self.buffer.statistics(),
            "working": self.working.statistics(),
            "cache": self.cache.statistics(),
            "emotional": self.emotional.statistics(),
            "dreaming": {"last_dream": self.dreaming._last_dream, "dreams_count": len(self.dreaming._dreams)}
        }
    
    def stop(self):
        """إيقاف الذاكرة الحية"""
        self._processing = False
        logger.info("🛑 إيقاف الذاكرة الحية")


# ============================================================
# الـ Singleton
# ============================================================

_dynamic_instance: Optional[DynamicMemory] = None
_dynamic_lock = threading.Lock()


def get_dynamic_memory() -> DynamicMemory:
    """الحصول على النسخة الوحيدة من الذاكرة الحية"""
    global _dynamic_instance
    if _dynamic_instance is None:
        with _dynamic_lock:
            if _dynamic_instance is None:
                _dynamic_instance = DynamicMemory()
    return _dynamic_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🌊 الذاكرة الحية - اختبار متكامل")
    print("=" * 70 + "\n")
    
    memory = get_dynamic_memory()
    
    # 1) استيعاب نصوص
    print("📝 استيعاب نصوص:")
    memory.ingest("user1", "مرحباً، من أنت؟", intensity=0.8)
    memory.ingest("user1", "أريد بناء ذكاء سيادي", intensity=0.9)
    memory.ingest("user2", "كيف يعمل هذا النظام؟", intensity=0.6)
    
    # 2) السياق
    print("\n🎭 سياق user1:")
    for item in memory.get_context("user1"):
        print(f"   [{item['role']}] {item['content'][:50]}... (أهمية: {item['importance']})")
    
    # 3) المزاج
    print("\n💖 المزاج الحالي:")
    mood = memory.get_mood()
    for emotion, intensity in mood.items():
        print(f"   {emotion}: {intensity:.2f}")
    
    # 4) تسجيل ردود
    print("\n🤖 تسجيل ردود:")
    memory.register_response("user1", "أنا العقل السيادي، أساعدك في بناء نظام ذكاء متطور", importance=0.85)
    
    # 5) الإحصائيات
    print("\n📊 الإحصائيات:")
    stats = memory.statistics()
    print(f"   حسية: {stats['sensory']['total_events']} حدث")
    print(f"   مؤقتة: {stats['buffer']['size']} عنصر")
    print(f"   عاملة: {stats['working']['active_users']} مستخدم نشط")
    print(f"   كاش: {stats['cache']['size']} عنصر (نسبة نجاح: {stats['cache']['hit_rate']:.1%})")
    print(f"   عاطفية: {stats['emotional']['active_emotions']} شعور نشط")
    
    # 6) حلم
    print("\n🌙 بدء حلم...")
    memory.dreaming.dream()
    dreams = memory.dreaming.get_last_dreams(3)
    print(f"   عدد الأحلام المسجلة: {len(memory.dreaming._dreams)}")
    
    print("\n" + "=" * 70)
    print("✅ الذاكرة الحية تعمل - تتنفس، تتذكر، تنسى، وتحلم")
    print("=" * 70)
