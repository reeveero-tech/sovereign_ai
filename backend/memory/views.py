# backend/memory/views.py
# 👁️ نوافذ الوعي والسياق والذاكرة المتعددة الطبقات
# الإصدار: 2.0.0 - النسخة المتكاملة الجبارة

"""
هذا الملف هو بوابات العقل السيادي.

إنه يترجم السجل الخام (core.py) إلى وعي حي:
- الذاكرة الحسية: ما يدخل الآن ويختفي
- الذاكرة العاملة: ما يُفكر فيه الآن (مسرح الوعي)
- الذاكرة الإجرائية: المهارات التلقائية
- الذاكرة الدلالية: المفاهيم والمعرفة
- الذاكرة الحدثية: السيرة الذاتية والزمن
- الذاكرة المكانية: أين تقع الأشياء
- الذاكرة الترابطية: ما يشبه ما
- الذاكرة العاطفية: المشاعر المرتبطة
- الذاكرة طويلة المدى: الدمج النهائي

كل هذه النوافذ تنظر إلى نفس السجل (core.py)، ولكن بزوايا مختلفة.
"""

import json
import math
import heapq
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple, Set, Iterator
from enum import Enum
from pathlib import Path
import threading
import runtime.threads as threads
import time
import hashlib

try:
    from .core import get_core, EventType, IntegrityStatus
    from config import DATA_DIR
except ImportError:
    from core import get_core, EventType, IntegrityStatus
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت والإعدادات
# ============================================================

# أقصى عمر للذاكرة الحسية (بالثواني)
SENSORY_TTL_SECONDS = 30

# حجم الذاكرة العاملة (7 ± 2 وحدات معرفية)
WORKING_MEMORY_CAPACITY = 7

# وزن العوامل في الترابط (TF-IDF-like)
ASSOCIATION_WEIGHT_RECENCY = 0.4
ASSOCIATION_WEIGHT_FREQUENCY = 0.3
ASSOCIATION_WEIGHT_SEMANTIC = 0.3

# منحنى النسيان (Ebbinghaus)
FORGETTING_CURVE_RATE = 0.5  # نسبة النسيان بعد يوم

# أقصى حجم للذاكرة الطويلة المدى (قبل الضغط)
LONG_TERM_MAX_UNCOMPRESSED_EVENTS = 10000


# ============================================================
# نماذج البيانات الأساسية
# ============================================================

class MemoryType(str, Enum):
    """أنواع الذاكرة في النظام السيادي"""
    SENSORY = "sensory"           # حسية (عابرة)
    WORKING = "working"           # عاملة (الوعي الحالي)
    PROCEDURAL = "procedural"     # إجرائية (مهارات)
    SEMANTIC = "semantic"         # دلالية (مفاهيم)
    EPISODIC = "episodic"         # حدثية (سيرة ذاتية)
    SPATIAL = "spatial"           # مكانية (خريطة المعرفة)
    ASSOCIATIVE = "associative"   # ترابطية (علاقات)
    EMOTIONAL = "emotional"       # عاطفية (علامات)
    LONG_TERM = "long_term"       # طويلة المدى (دمج كل شيء)


@dataclass
class SensoryItem:
    """عنصر في الذاكرة الحسية"""
    id: str
    timestamp: float
    event_hash: str
    event_type: str
    user_id: Optional[str]
    input_text: Optional[str]
    output_text: Optional[str]
    raw_payload: Dict[str, Any]
    
    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > SENSORY_TTL_SECONDS


@dataclass
class WorkingMemoryItem:
    """عنصر في الذاكرة العاملة"""
    event_hash: str
    event_type: str
    timestamp: float
    user_id: str
    content: str  # الملخص النصي
    importance: float  # 0-1، مدى أهمية هذا العنصر
    attention_weight: float  # 0-1، مدى التركيز عليه حالياً


@dataclass
class ProceduralSkill:
    """مهارة في الذاكرة الإجرائية (تلقائية)"""
    name: str
    trigger_patterns: List[str]
    action_sequence: List[str]
    execution_count: int
    last_executed: float
    success_rate: float
    is_automatic: bool  # هل أصبحت تلقائية؟


@dataclass
class SemanticConcept:
    """مفهوم في الذاكرة الدلالية"""
    name: str
    aliases: List[str]
    definition: str
    related_concepts: Dict[str, float]  # concept -> weight
    occurrences: int
    last_seen: float
    confidence: float  # 0-1


@dataclass
class EpisodicMemory:
    """ذاكرة حدثية (سيرة ذاتية)"""
    event_id: str
    timestamp: float
    user_id: str
    what: str  # ماذا حدث؟
    where: str  # أين؟ (سياق معرفي)
    when: str  # متى؟ (زمن)
    who: str  # من؟ (المشاركون)
    emotions: Dict[str, float]  # عاطفة -> شدة
    importance: float
    linked_events: List[str]  # أحداث مرتبطة


@dataclass
class SpatialNode:
    """عقدة في الذاكرة المكانية (خريطة المعرفة)"""
    id: str
    label: str
    coordinates: Tuple[float, ...]  # إحداثيات في الفضاء المعرفي
    neighbors: Dict[str, float]  # node_id -> distance
    concept: Optional[str]
    event_hash: Optional[str]


@dataclass
class AssociativeLink:
    """رابط ترابطي بين مفهومين"""
    source: str
    target: str
    strength: float  # 0-1
    type: str  # "similar", "causal", "temporal", "opposite", "part_of", "example_of"
    count: int
    last_updated: float


@dataclass
class EmotionalMark:
    """علامة عاطفية مرتبطة بمعلومة"""
    concept_id: str
    emotion: str  # "joy", "fear", "importance", "danger", "trust", "curiosity", "sadness", "anger"
    intensity: float  # 0-1
    timestamp: float
    source: str  # من أين أتت هذه العاطفة؟


# ============================================================
# الذاكرة الحسية (Sensory Memory) - ما يدخل الآن ويختفي
# ============================================================

class SensoryMemory:
    """
    الذاكرة الحسية: تخزن المدخلات الخام للحظات ثم تتبدد.
    تحاكي: الذاكرة الأيقونية (بصرية)، الصدوية (سمعية)، اللمسية.
    """
    
    def __init__(self, ttl_seconds: int = SENSORY_TTL_SECONDS):
        self._items: List[SensoryItem] = []
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._bg_stop = threading.Event()
        self._cleanup_thread = threads.start_managed(
            self._auto_cleanup, owner=self, stop_event=self._bg_stop
        )
        logger.info(f"🔄 الذاكرة الحسية جاهزة (TTL: {ttl_seconds} ثانية)")
    
    def add(self, event_hash: str, event_type: str, payload: Dict[str, Any], 
            user_id: Optional[str] = None):
        """إضافة حدث جديد إلى الذاكرة الحسية"""
        with self._lock:
            item = SensoryItem(
                id=hashlib.md5(f"{event_hash}{time.time()}".encode()).hexdigest()[:12],
                timestamp=time.time(),
                event_hash=event_hash,
                event_type=event_type,
                user_id=user_id or payload.get("user") or payload.get("user_id"),
                input_text=payload.get("input") or payload.get("text"),
                output_text=payload.get("output") or payload.get("reply"),
                raw_payload=payload
            )
            self._items.append(item)
            logger.debug(f"📥 حسية: {event_type[:10]}...")
    
    def get_latest(self, limit: int = 10) -> List[SensoryItem]:
        """الحصول على أحدث العناصر الحسية (التي لم تنته صلاحيتها بعد)"""
        self._cleanup()
        with self._lock:
            valid = [i for i in self._items if not i.is_expired()]
            return valid[-limit:][::-1]
    
    def _cleanup(self):
        """إزالة العناصر منتهية الصلاحية"""
        with self._lock:
            self._items = [i for i in self._items if not i.is_expired()]
    
    def _auto_cleanup(self):
        """تنظيف تلقائي دوري"""
        while not self._bg_stop.is_set():
            if self._bg_stop.wait(self._ttl):
                break
            self._cleanup()
    
    def clear(self):
        """مسح الذاكرة الحسية بالكامل"""
        with self._lock:
            self._items.clear()
            logger.info("🧹 الذاكرة الحسية مُسحت")


# ============================================================
# الذاكرة العاملة (Working Memory) - مسرح الوعي
# ============================================================

class WorkingMemory:
    """
    الذاكرة العاملة: ما يُفكر فيه الآن.
    تحاكي: الحلقة الفونولوجية، اللوحة البصرية المكانية، المنسق المركزي.
    السعة: 7 ± 2 وحدات معرفية (قانون ميلر الشهير).
    """
    
    def __init__(self, capacity: int = WORKING_MEMORY_CAPACITY):
        self._items: Dict[str, WorkingMemoryItem] = {}  # user_id -> item
        self._capacity = capacity
        self._lock = threading.Lock()
        logger.info(f"🧠 الذاكرة العاملة جاهزة (السعة: {capacity} وحدات)")
    
    def focus(self, user_id: str, event_hash: str, event_type: str, 
              content: str, importance: float = 0.5):
        """
        تركيز الانتباه على عنصر معين (وضعه في الذاكرة العاملة)
        """
        with self._lock:
            # إذا كان المستخدم لديه بالفعل عناصر، نضيف الجديد
            # ولكن نحافظ على السعة المحدودة
            if user_id in self._items:
                # تحديث العنصر الحالي
                self._items[user_id].attention_weight = 1.0
                self._items[user_id].timestamp = time.time()
            else:
                # إضافة عنصر جديد
                item = WorkingMemoryItem(
                    event_hash=event_hash,
                    event_type=event_type,
                    timestamp=time.time(),
                    user_id=user_id,
                    content=content[:500],
                    importance=importance,
                    attention_weight=1.0
                )
                self._items[user_id] = item
                
                # تطبيق آلية النسيان إذا تجاوزنا السعة
                self._forget_if_needed()
    
    def get_context(self, user_id: str) -> Optional[WorkingMemoryItem]:
        """الحصول على السياق الحالي لمستخدم"""
        with self._lock:
            item = self._items.get(user_id)
            if item:
                # تخفيف الانتباه بمرور الوقت
                elapsed = time.time() - item.timestamp
                item.attention_weight = max(0.3, 1.0 - elapsed / 60.0)
            return item
    
    def shift_attention(self, from_user: str, to_user: str, content: str):
        """تحويل الانتباه من مستخدم إلى آخر"""
        with self._lock:
            # نقل السياق
            if from_user in self._items:
                context = self._items.pop(from_user)
                context.user_id = to_user
                context.content = content
                context.timestamp = time.time()
                self._items[to_user] = context
    
    def _forget_if_needed(self):
        """نسيان أقدم العناصر إذا تجاوزنا السعة"""
        if len(self._items) > self._capacity:
            # نجد أقل العناصر أهمية وأقل انتباه
            to_remove = min(self._items.items(), 
                           key=lambda x: x[1].importance * x[1].attention_weight)
            del self._items[to_remove[0]]
            logger.debug(f"🧠 تم نسيان عنصر من الذاكرة العاملة: {to_remove[0]}")
    
    def get_all_contexts(self) -> Dict[str, WorkingMemoryItem]:
        """الحصول على جميع السياقات النشطة"""
        with self._lock:
            return self._items.copy()


# ============================================================
# الذاكرة الإجرائية (Procedural Memory) - المهارات التلقائية
# ============================================================

class ProceduralMemory:
    """
    الذاكرة الإجرائية: كيف تعمل الأشياء. مهارات تصبح تلقائية.
    تحاكي: تعلم ركوب الدراجة - لا تفكر فيها، فقط تفعلها.
    """
    
    def __init__(self):
        self._skills: Dict[str, ProceduralSkill] = {}
        self._lock = threading.Lock()
        logger.info("🦿 الذاكرة الإجرائية جاهزة")
    
    def learn_skill(self, name: str, trigger_patterns: List[str], 
                    action_sequence: List[str]):
        """تعلم مهارة جديدة (أو تحديث مهارة موجودة)"""
        with self._lock:
            if name in self._skills:
                # تحديث
                skill = self._skills[name]
                skill.trigger_patterns = list(set(skill.trigger_patterns + trigger_patterns))
                skill.action_sequence = action_sequence
            else:
                # جديد
                skill = ProceduralSkill(
                    name=name,
                    trigger_patterns=trigger_patterns,
                    action_sequence=action_sequence,
                    execution_count=0,
                    last_executed=0,
                    success_rate=0.0,
                    is_automatic=False
                )
                self._skills[name] = skill
            logger.info(f"🎯 تم تعلم المهارة: {name}")
    
    def execute(self, trigger: str, context: Dict[str, Any]) -> Optional[str]:
        """تنفيذ مهارة تلقائياً إذا كان المحفز مناسباً"""
        with self._lock:
            best_skill = None
            best_score = 0
            
            for skill in self._skills.values():
                for pattern in skill.trigger_patterns:
                    if pattern in trigger:
                        score = (skill.execution_count * skill.success_rate) / 100.0
                        if score > best_score:
                            best_score = score
                            best_skill = skill
            
            if best_skill:
                best_skill.execution_count += 1
                best_skill.last_executed = time.time()
                best_skill.is_automatic = best_skill.execution_count > 10 and best_skill.success_rate > 0.8
                
                # محاكاة تنفيذ المهارة (في الواقع، ستدعو وظائف أخرى)
                result = f"🎯 تنفيذ المهارة '{best_skill.name}' (تلقائي: {best_skill.is_automatic})"
                logger.debug(result)
                return result
            
            return None
    
    def mark_success(self, skill_name: str, success: bool):
        """تحديث معدل نجاح المهارة"""
        with self._lock:
            if skill_name in self._skills:
                skill = self._skills[skill_name]
                total = skill.execution_count
                if total > 0:
                    current_success = skill.success_rate * (total - 1)
                    new_success = current_success + (1 if success else 0)
                    skill.success_rate = new_success / total
    
    def get_all_skills(self) -> List[ProceduralSkill]:
        """الحصول على جميع المهارات"""
        with self._lock:
            return list(self._skills.values())


# ============================================================
# الذاكرة الدلالية (Semantic Memory) - المفاهيم والمعرفة
# ============================================================

class SemanticMemory:
    """
    الذاكرة الدلالية: المفاهيم، الحقائق، القوانين.
    تحاكي: الموسوعة الداخلية للذكاء.
    """
    
    def __init__(self):
        self._concepts: Dict[str, SemanticConcept] = {}
        self._lock = threading.Lock()
        logger.info("📚 الذاكرة الدلالية جاهزة")
    
    def add_concept(self, name: str, definition: str, 
                    aliases: Optional[List[str]] = None,
                    related_concepts: Optional[Dict[str, float]] = None):
        """إضافة مفهوم جديد أو تحديث مفهوم موجود"""
        with self._lock:
            name_lower = name.lower()
            
            if name_lower in self._concepts:
                concept = self._concepts[name_lower]
                concept.occurrences += 1
                concept.last_seen = time.time()
                concept.confidence = min(1.0, concept.confidence + 0.1)
                
                # تحديث المرادفات
                if aliases:
                    concept.aliases.extend([a.lower() for a in aliases if a.lower() not in concept.aliases])
                
                # تحديث المفاهيم المرتبطة
                if related_concepts:
                    for rc, weight in related_concepts.items():
                        rc_lower = rc.lower()
                        concept.related_concepts[rc_lower] = concept.related_concepts.get(rc_lower, 0) + weight
            else:
                concept = SemanticConcept(
                    name=name_lower,
                    aliases=[a.lower() for a in (aliases or [])],
                    definition=definition,
                    related_concepts={k.lower(): v for k, v in (related_concepts or {}).items()},
                    occurrences=1,
                    last_seen=time.time(),
                    confidence=0.5
                )
                self._concepts[name_lower] = concept
            logger.debug(f"📖 مفهوم: {name}")
    
    def get_concept(self, name: str) -> Optional[SemanticConcept]:
        """استرجاع مفهوم"""
        with self._lock:
            name_lower = name.lower()
            
            # البحث بالاسم
            if name_lower in self._concepts:
                return self._concepts[name_lower]
            
            # البحث بالمرادفات
            for concept in self._concepts.values():
                if name_lower in concept.aliases:
                    return concept
            
            return None
    
    def find_related(self, concept_name: str, limit: int = 5) -> List[Tuple[str, float]]:
        """العثور على مفاهيم مرتبطة"""
        concept = self.get_concept(concept_name)
        if not concept:
            return []
        
        related = list(concept.related_concepts.items())
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """إحصائيات الذاكرة الدلالية"""
        with self._lock:
            return {
                "total_concepts": len(self._concepts),
                "average_confidence": sum(c.confidence for c in self._concepts.values()) / len(self._concepts) if self._concepts else 0,
                "most_frequent": sorted(self._concepts.values(), key=lambda x: x.occurrences, reverse=True)[:5]
            }


# ============================================================
# الذاكرة الحدثية (Episodic Memory) - السيرة الذاتية
# ============================================================

class EpisodicMemoryStore:
    """
    الذاكرة الحدثية: سجل الأحداث الشخصية للذكاء.
    تحاكي: كيف تتذكر ما حدث لك يوم أمس.
    """
    
    def __init__(self, max_size: int = 10000):
        self._events: Dict[str, EpisodicMemory] = {}
        self._timeline: List[str] = []  # قائمة بمعرفات الأحداث مرتبة زمنياً
        self._max_size = max_size
        self._lock = threading.Lock()
        logger.info("📅 الذاكرة الحدثية جاهزة")
    
    def record_event(self, event_hash: str, user_id: str, what: str,
                     where: str = "", when: str = "", who: str = "",
                     emotions: Optional[Dict[str, float]] = None,
                     importance: float = 0.5):
        """تسجيل حدث في الذاكرة الحدثية"""
        with self._lock:
            event = EpisodicMemory(
                event_id=event_hash,
                timestamp=time.time(),
                user_id=user_id,
                what=what[:500],
                where=where,
                when=when or datetime.now().isoformat(),
                who=who,
                emotions=emotions or {},
                importance=importance,
                linked_events=[]
            )
            self._events[event_hash] = event
            self._timeline.append(event_hash)
            
            # ضغط الذاكرة إذا تجاوزت الحجم
            if len(self._timeline) > self._max_size:
                oldest = self._timeline.pop(0)
                del self._events[oldest]
                logger.debug(f"🗜️ تم ضغط الذاكرة الحدثية: حذف الحدث {oldest[:12]}")
    
    def recall(self, event_hash: str) -> Optional[EpisodicMemory]:
        """استرجاع حدث معين"""
        with self._lock:
            return self._events.get(event_hash)
    
    def recall_recent(self, user_id: Optional[str] = None, limit: int = 10) -> List[EpisodicMemory]:
        """استرجاع الأحداث الأخيرة لمستخدم معين (أو الكل)"""
        with self._lock:
            recent = []
            for eid in reversed(self._timeline[-limit:]):
                event = self._events[eid]
                if user_id is None or event.user_id == user_id:
                    recent.append(event)
            return recent
    
    def recall_by_emotion(self, emotion: str, min_intensity: float = 0.5) -> List[EpisodicMemory]:
        """استرجاع الأحداث بناءً على المشاعر المرتبطة بها"""
        with self._lock:
            result = []
            for event in self._events.values():
                intensity = event.emotions.get(emotion, 0)
                if intensity >= min_intensity:
                    result.append(event)
            return sorted(result, key=lambda x: x.emotions.get(emotion, 0), reverse=True)


# ============================================================
# الذاكرة الترابطية (Associative Memory) - ما يشبه ما
# ============================================================

class AssociativeMemory:
    """
    الذاكرة الترابطية: الروابط بين المفاهيم والأحداث.
    تحاكي: كيف ترى تشابهاً بين فكرتين مختلفتين.
    """
    
    def __init__(self):
        self._links: Dict[str, Dict[str, AssociativeLink]] = {}  # source -> target -> link
        self._lock = threading.Lock()
        logger.info("🔗 الذاكرة الترابطية جاهزة")
    
    def add_link(self, source: str, target: str, link_type: str, strength: float = 0.5):
        """إضافة رابط ترابطي بين مفهومين"""
        with self._lock:
            if source not in self._links:
                self._links[source] = {}
            
            if target in self._links[source]:
                link = self._links[source][target]
                link.strength = min(1.0, link.strength + strength * 0.3)
                link.count += 1
                link.last_updated = time.time()
            else:
                link = AssociativeLink(
                    source=source,
                    target=target,
                    strength=strength,
                    type=link_type,
                    count=1,
                    last_updated=time.time()
                )
                self._links[source][target] = link
            
            # الرابط ثنائي الاتجاه (إن لم يكن معكوساً)
            if link_type != "opposite" and target not in self._links.get(target, {}).get(source, {}):
                self.add_link(target, source, link_type, strength * 0.7)
    
    def find_similar(self, concept: str, limit: int = 5) -> List[Tuple[str, float]]:
        """العثور على مفاهيم مشابهة لمفهوم معين"""
        with self._lock:
            similar = []
            for target, link in self._links.get(concept, {}).items():
                if link.type == "similar":
                    similar.append((target, link.strength))
            similar.sort(key=lambda x: x[1], reverse=True)
            return similar[:limit]
    
    def find_related_by_type(self, concept: str, link_type: str) -> List[Tuple[str, float]]:
        """العثور على مفاهيم مرتبطة بنوع معين من العلاقات"""
        with self._lock:
            result = []
            for target, link in self._links.get(concept, {}).items():
                if link.type == link_type:
                    result.append((target, link.strength))
            result.sort(key=lambda x: x[1], reverse=True)
            return result


# ============================================================
# الذاكرة العاطفية (Emotional Memory) - العلامات والمشاعر
# ============================================================

class EmotionalMemory:
    """
    الذاكرة العاطفية: مشاعر مرتبطة بالمعلومات.
    تحاكي: الخوف من شيء أذى في الماضي، الثقة بشيء نفع.
    """
    
    def __init__(self):
        self._marks: Dict[str, List[EmotionalMark]] = {}  # concept_id -> marks
        self._lock = threading.Lock()
        logger.info("💖 الذاكرة العاطفية جاهزة")
    
    def mark(self, concept_id: str, emotion: str, intensity: float, source: str = "system"):
        """توسيم مفهوم بمشاعر معينة"""
        with self._lock:
            mark = EmotionalMark(
                concept_id=concept_id,
                emotion=emotion,
                intensity=min(1.0, max(0.0, intensity)),
                timestamp=time.time(),
                source=source
            )
            
            if concept_id not in self._marks:
                self._marks[concept_id] = []
            self._marks[concept_id].append(mark)
            
            # الاحتفاظ بآخر 20 علامة لكل مفهوم
            if len(self._marks[concept_id]) > 20:
                self._marks[concept_id] = self._marks[concept_id][-20:]
    
    def get_emotion(self, concept_id: str, emotion: str) -> float:
        """الحصول على شدة مشاعر معينة لمفهوم"""
        with self._lock:
            marks = self._marks.get(concept_id, [])
            relevant = [m for m in marks if m.emotion == emotion]
            if not relevant:
                return 0.0
            
            # المتوسط المرجح (الأحدث أهم)
            total_weight = 0
            weighted_sum = 0
            for mark in relevant:
                age = time.time() - mark.timestamp
                weight = math.exp(-age / 86400)  # يتلاشى بيوم واحد
                weighted_sum += mark.intensity * weight
                total_weight += weight
            
            return weighted_sum / total_weight if total_weight > 0 else 0
    
    def get_dominant_emotion(self, concept_id: str) -> Tuple[str, float]:
        """الحصول على المشاعر السائدة لمفهوم"""
        emotions = ["joy", "fear", "importance", "danger", "trust", "curiosity", "sadness", "anger"]
        best_emotion = "neutral"
        best_intensity = 0
        
        for e in emotions:
            intensity = self.get_emotion(concept_id, e)
            if intensity > best_intensity:
                best_intensity = intensity
                best_emotion = e
        
        return best_emotion, best_intensity


# ============================================================
# الذاكرة طويلة المدى (Long Term Memory) - الدمج النهائي
# ============================================================

class LongTermMemory:
    """
    الذاكرة طويلة المدى: دمج جميع أنواع الذاكرة في كل متماسك.
    هذه هي الذاكرة التي تحدد هوية الذكاء السيادي.
    """
    
    def __init__(self):
        self.semantic = SemanticMemory()
        self.episodic = EpisodicMemoryStore()
        self.associative = AssociativeMemory()
        self.emotional = EmotionalMemory()
        self._lock = threading.Lock()
        self._last_consolidation = time.time()
        logger.info("🗃️ الذاكرة طويلة المدى جاهزة")
    
    def consolidate(self, working_item: WorkingMemoryItem):
        """
        دمج عنصر من الذاكرة العاملة إلى الذاكرة طويلة المدى.
        هذه هي عملية "التعلم".
        """
        with self._lock:
            # استخراج المفاهيم من المحتوى
            content = working_item.content
            words = content.split()
            
            # إضافة المفاهيم الأساسية
            for word in words[:20]:  # نأخذ أول 20 كلمة
                if len(word) > 3:  # نتجاهل الكلمات القصيرة جداً
                    self.semantic.add_concept(
                        name=word,
                        definition=f"مفهوم مرتبط بـ: {content[:100]}",
                        aliases=[],
                        related_concepts={}
                    )
            
            # تسجيل حدث في الذاكرة الحدثية
            self.episodic.record_event(
                event_hash=working_item.event_hash,
                user_id=working_item.user_id,
                what=f"تفاعل: {working_item.content[:100]}",
                where="working_memory",
                when=datetime.fromtimestamp(working_item.timestamp).isoformat(),
                emotions={"importance": working_item.importance},
                importance=working_item.importance
            )
            
            # إضافة علامة عاطفية
            if working_item.importance > 0.7:
                self.emotional.mark(
                    concept_id=working_item.event_hash,
                    emotion="importance",
                    intensity=working_item.importance,
                    source="consolidation"
                )
            
            logger.debug(f"💾 تم دمج {working_item.event_hash[:12]} إلى الذاكرة طويلة المدى")
    
    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        استرجاع من الذاكرة طويلة المدى بناءً على استعلام.
        هذه هي عملية "التذكر".
        """
        results = []
        
        # بحث في الذاكرة الدلالية
        concept = self.semantic.get_concept(query)
        if concept:
            results.append({
                "type": "semantic",
                "name": concept.name,
                "definition": concept.definition,
                "confidence": concept.confidence
            })
        
        # بحث في الذاكرة الحدثية
        recent_events = self.episodic.recall_recent(limit=limit)
        for event in recent_events:
            results.append({
                "type": "episodic",
                "what": event.what,
                "when": event.when,
                "importance": event.importance
            })
        
        # بحث ترابطي
        similar = self.associative.find_similar(query, limit=limit)
        for sim, strength in similar:
            results.append({
                "type": "associative",
                "concept": sim,
                "strength": strength
            })
        
        return results[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """إحصائيات الذاكرة طويلة المدى"""
        return {
            "semantic": self.semantic.get_statistics(),
            "episodic": {"total_events": len(self.episodic._events)},
            "associative": {"total_links": sum(len(links) for links in self.associative._links.values())},
            "emotional": {"total_marks": sum(len(marks) for marks in self.emotional._marks.values())}
        }


# ============================================================
# الواجهة الموحدة (MemoryViews) - الجسر بين core.py وملفات الذاكرة الأخرى
# ============================================================

class MemoryViews:
    """
    الواجهة الموحدة لجميع أنواع الذاكرة.
    هذا هو الجسر بين السجل السيادي (core.py) ونظام الذاكرة الحي.
    """
    
    def __init__(self):
        self.core = get_core()
        self._bg_stop = threading.Event()
        
        # تهيئة جميع أنواع الذاكرة
        self.sensory = SensoryMemory()
        self.working = WorkingMemory()
        self.procedural = ProceduralMemory()
        self.long_term = LongTermMemory()
        
        # تسجيل المهارات الأساسية
        self._register_base_skills()
        
        # تحميل الأحداث السابقة (إذا وجدت)
        self._load_from_core()
        
        # بدء خيط الخلفية للتكامل المستمر
        self._background_thread = threads.start_managed(
            self._background_integration, owner=self, stop_event=self._bg_stop
        )
        
        logger.info("✅ واجهة الذاكرة الموحدة جاهزة - جميع أنواع الذاكرة تعمل")
    
    def _register_base_skills(self):
        """تسجيل المهارات الأساسية في الذاكرة الإجرائية"""
        self.procedural.learn_skill(
            name="greet_user",
            trigger_patterns=["مرحب", "السلام", "hello", "hi", "أهلاً", "يا ذكاء"],
            action_sequence=["recognize_user", "generate_greeting", "log_interaction"]
        )
        
        self.procedural.learn_skill(
            name="answer_who_are_you",
            trigger_patterns=["من أنت", "who are you", "ما اسمك", "what are you"],
            action_sequence=["fetch_identity", "format_introduction", "respond"]
        )
        
        self.procedural.learn_skill(
            name="handle_help_request",
            trigger_patterns=["ساعدني", "help", "مساعدة", "أرشدني", "how to"],
            action_sequence=["determine_help_type", "fetch_help_content", "present_options"]
        )
    
    def _load_from_core(self):
        """تحميل الأحداث من السجل السيادي إلى الذاكرة الحية"""
        logger.info("🔄 جاري تحميل السجل السيادي إلى الذاكرة الحية...")
        
        # R-770: الحدثية تبقي آخر max_size فقط، فتحميل ما قبلها كان يُفك ثم يُرمى —
        # وعلى سجل 46k حدث أنفد ذاكرة آلة الإنتاج (512MB) عند كل إقلاع. نقرأ الذيل
        # نفسه الذي كانت ستبقيه (مسار الذيل السريع) بالترتيب الأصلي. السجل لا يُمس.
        cap = getattr(self.long_term.episodic, "_max_size", LONG_TERM_MAX_UNCOMPRESSED_EVENTS)
        tail = list(self.core.iterate_events(reverse=True, limit=cap))
        tail.reverse()
        sensory_window = getattr(self.sensory, "_ttl", SENSORY_TTL_SECONDS)
        now = time.time()

        event_count = 0
        for event in tail:
            try:
                payload = self.core.get_payload(event)
                event_hash = event.get("hash", "")
                event_type = event.get("type", "")
                event_time_str = event.get("time", "")
                
                # تحويل الوقت إلى timestamp
                try:
                    parsed = datetime.fromisoformat(event_time_str)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    event_time = parsed.timestamp()
                except Exception:
                    event_time = now
                
                # R-770: الحسية للحاضر فقط — حدث قديم لا يُعاد «إحساسًا» بتوقيت الآن
                user = payload.get("user") or payload.get("user_id")
                if now - event_time <= sensory_window:
                    self.sensory.add(event_hash, event_type, payload, user)
                
                # إضافة إلى الذاكرة الحدثية
                self.long_term.episodic.record_event(
                    event_hash=event_hash,
                    user_id=user or "system",
                    what=f"حدث من السجل: {event_type}",
                    when=event_time_str,
                    importance=0.3  # الأحداث القديمة أقل أهمية
                )
                
                event_count += 1
                if event_count % 1000 == 0:
                    logger.info(f"   تم تحميل {event_count} حدث...")
                
            except Exception as e:
                logger.debug(f"خطأ في تحميل الحدث: {e}")
        
        logger.info(f"✅ تم تحميل {event_count} حدث من السجل السيادي")
    
    def _background_integration(self):
        """
        خلفية: تكامل مستمر بين السجل السيادي والذاكرة الحية.
        يقرأ الأحداث الجديدة ويضيفها إلى الذاكرة.
        """
        last_hash = self.core._last_hash
        
        while not self._bg_stop.is_set():
            try:
                # التحقق من الأحداث الجديدة
                # R-606: حد أقصى 1000 حدث حديث — يكفي لفاصل ثانية واحدة ويتجنب
                # قراءة السجل الكامل في كل دورة (كان O(n) لكل ثانية)
                # R-777: اجمع الجديد حتى المؤشر ثم عالجه بالترتيب الزمني، والمؤشر = الأحدث.
                # # DELETION-JUSTIFIED: كان المؤشر يُحدَّث لكل حدث أثناء المشي من الأحدث للأقدم
                # فينتهي عند الأقدم، فتعيد كل دورة الدفعة كلها (55k SensoryItem حية محليًا).
                fresh = []
                for event in self.core.iterate_events(reverse=True, limit=1000):
                    if event.get("hash") == last_hash:
                        break
                    fresh.append(event)
                if fresh:
                    last_hash = fresh[0].get("hash")
                fresh.reverse()
                for event in fresh:
                    payload = self.core.get_payload(event)
                    event_hash = event.get("hash", "")
                    event_type = event.get("type", "")
                    
                    # إضافة إلى الذاكرة الحسية
                    user = payload.get("user") or payload.get("user_id")
                    self.sensory.add(event_hash, event_type, payload, user)
                    
                    # إضافة إلى الذاكرة العاملة (فقط للأحداث الحديثة)
                    if event_type in ["interaction", "response"]:
                        content = payload.get("input") or payload.get("text") or payload.get("output") or payload.get("reply") or ""
                        self.working.focus(
                            user_id=user or "system",
                            event_hash=event_hash,
                            event_type=event_type,
                            content=content[:200],
                            importance=0.6
                        )
                    
                    # محاولة تنفيذ مهارة تلقائية
                    trigger_text = payload.get("input") or payload.get("text") or ""
                    self.procedural.execute(trigger_text, payload)
                    
                    # دمج إلى الذاكرة طويلة المدى
                    working_item = self.working.get_context(user or "system")
                    if working_item:
                        self.long_term.consolidate(working_item)
                
                # ننتظر ثانية قبل التحقق مرة أخرى — قابل للمقاطعة عند الإيقاف
                if self._bg_stop.wait(1):
                    break
                
            except Exception as e:
                logger.error(f"خطأ في خلفية التكامل: {e}")
                if self._bg_stop.wait(5):
                    break
    
    # ============================================================
    # واجهات الوصول العامة
    # ============================================================
    
    def get_sensory_latest(self, limit: int = 10) -> List[SensoryItem]:
        """الحصول على أحدث المدخلات الحسية"""
        return self.sensory.get_latest(limit)
    
    def get_working_context(self, user_id: str) -> Optional[WorkingMemoryItem]:
        """الحصول على السياق الحالي لمستخدم"""
        return self.working.get_context(user_id)
    
    def get_long_term_recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """استرجاع من الذاكرة طويلة المدى"""
        return self.long_term.recall(query, limit)
    
    def get_semantic_concept(self, concept: str) -> Optional[SemanticConcept]:
        """الحصول على مفهوم من الذاكرة الدلالية"""
        return self.long_term.semantic.get_concept(concept)
    
    def get_episodic_recent(self, user_id: Optional[str] = None, limit: int = 10) -> List[EpisodicMemory]:
        """الحصول على الأحداث الأخيرة"""
        return self.long_term.episodic.recall_recent(user_id, limit)
    
    def get_associative_similar(self, concept: str, limit: int = 5) -> List[Tuple[str, float]]:
        """الحصول على مفاهيم مشابهة"""
        return self.long_term.associative.find_similar(concept, limit)
    
    def get_emotional_state(self, concept_id: str) -> Tuple[str, float]:
        """الحصول على الحالة العاطفية لمفهوم"""
        return self.long_term.emotional.get_dominant_emotion(concept_id)
    
    def get_procedural_skills(self) -> List[ProceduralSkill]:
        """الحصول على جميع المهارات الإجرائية"""
        return self.procedural.get_all_skills()
    
    def get_statistics(self) -> Dict[str, Any]:
        """إحصائيات جميع أنواع الذاكرة"""
        return {
            "sensory": {"active_items": len(self.sensory.get_latest(100))},
            "working": {"active_contexts": len(self.working._items)},
            "procedural": {"skills_count": len(self.procedural._skills)},
            "long_term": self.long_term.get_statistics()
        }
    
    def force_consolidation(self):
        """فرض دمج الذاكرة العاملة إلى الذاكرة طويلة المدى"""
        for user_id, item in self.working.get_all_contexts().items():
            self.long_term.consolidate(item)
        logger.info("💾 تم فرض دمج الذاكرة")


# ============================================================
# Singleton للاستخدام من بقية النظام
# ============================================================

_views_instance: Optional[MemoryViews] = None
_views_lock = threading.Lock()


def get_views() -> MemoryViews:
    """الحصول على النسخة الوحيدة من واجهة الذاكرة الموحدة"""
    global _views_instance
    if _views_instance is None:
        with _views_lock:
            if _views_instance is None:
                _views_instance = MemoryViews()
    return _views_instance


# ============================================================
# تشغيل تجريبي
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧠 اختبار الذاكرة السيادية المتكاملة (جميع الأنواع)")
    print("=" * 70 + "\n")
    
    # تهيئة الذاكرة
    views = get_views()
    
    # 1. الذاكرة الحسية
    print("📥 1. الذاكرة الحسية:")
    print(f"   - أحدث العناصر الحسية: {len(views.get_sensory_latest(5))}")
    
    # 2. الذاكرة العاملة
    print("\n🧠 2. الذاكرة العاملة:")
    test_user = "test_user_001"
    views.working.focus(test_user, "test_hash_001", "interaction", "مرحباً، من أنت؟", importance=0.8)
    context = views.get_working_context(test_user)
    if context:
        print(f"   - سياق {test_user}: {context.content[:50]}... (أهمية: {context.importance})")
    
    # 3. الذاكرة الإجرائية
    print("\n🦿 3. الذاكرة الإجرائية:")
    skills = views.get_procedural_skills()
    print(f"   - عدد المهارات: {len(skills)}")
    for skill in skills[:3]:
        print(f"     • {skill.name} (تلقائي: {skill.is_automatic})")
    
    # 4. الذاكرة الدلالية
    print("\n📚 4. الذاكرة الدلالية:")
    views.long_term.semantic.add_concept("ذكاء سيادي", "نظام ذكاء اصطناعي يتحكم بنفسه وبسجله", aliases=["ذكاء حر", "AI سيادي"])
    concept = views.get_semantic_concept("ذكاء سيادي")
    if concept:
        print(f"   - مفهوم: {concept.name} -> {concept.definition[:50]}...")
    
    # 5. الذاكرة الترابطية
    print("\n🔗 5. الذاكرة الترابطية:")
    views.long_term.associative.add_link("ذكاء سيادي", "سيادة", "related", 0.9)
    similar = views.get_associative_similar("ذكاء سيادي", 3)
    print(f"   - مفاهيم مشابهة: {similar}")
    
    # 6. الذاكرة الحدثية
    print("\n📅 6. الذاكرة الحدثية:")
    events = views.get_episodic_recent(limit=5)
    print(f"   - آخر الأحداث: {len(events)}")
    for event in events[:2]:
        print(f"     • {event.what[:50]}... (أهمية: {event.importance})")
    
    # 7. الذاكرة العاطفية
    print("\n💖 7. الذاكرة العاطفية:")
    views.long_term.emotional.mark("ذكاء سيادي", "trust", 0.9, "system")
    emotion, intensity = views.get_emotional_state("ذكاء سيادي")
    print(f"   - المشاعر السائدة لـ 'ذكاء سيادي': {emotion} ({intensity:.2f})")
    
    # 8. الاسترجاع من الذاكرة طويلة المدى
    print("\n🔍 8. الذاكرة طويلة المدى (الاسترجاع):")
    results = views.get_long_term_recall("سيادة", 5)
    for r in results:
        print(f"   - [{r.get('type')}] {r.get('name', r.get('what', str(r)))[:50]}...")
    
    # 9. الإحصائيات الكاملة
    print("\n📊 9. إحصائيات النظام:")
    stats = views.get_statistics()
    print(f"   - الذاكرة الحسية: {stats['sensory']['active_items']} عنصر نشط")
    print(f"   - الذاكرة العاملة: {stats['working']['active_contexts']} سياق نشط")
    print(f"   - الذاكرة الإجرائية: {stats['procedural']['skills_count']} مهارة")
    print(f"   - الذاكرة الدلالية: {stats['long_term']['semantic']['total_concepts']} مفهوم")
    
    print("\n" + "=" * 70)
    print("✅ اختبار الذاكرة السيادية المتكاملة اكتمل بنجاح")
    print("=" * 70)
