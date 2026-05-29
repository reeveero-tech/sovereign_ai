# backend/memory/store/__init__.py
# 📀 الطبقات الصلبة للذاكرة السيادية - النسخة الجبارة
# الإصدار: 2.0.0 - تخزين حقيقي بطبقات متعددة، استعلامات متطورة، تكامل كامل

"""
هذا الملف هو العمود الفقري للتخزين الدائم.

يجمع بين:
- الذاكرة الإجرائية (المهارات التلقائية)
- الذاكرة الدلالية (المفاهيم والحقائق)
- الذاكرة الحدثية (السيرة الذاتية)
- الذاكرة المكانية (خرائط المعرفة)
- الذاكرة العاطفية (المشاعر والعلامات)
- الذاكرة الترابطية (العلاقات بين المفاهيم)

كل هذه الطبقات تخزن بشكل دائم، مشفر، ومتكامل مع السجل السيادي.
"""

import json
import uuid
import time
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, Iterator, Union
from enum import Enum
from collections import defaultdict
import heapq

try:
    from ..core import get_core, EventType
    from ..encoding import get_encoder
    from ...config import DATA_DIR
except ImportError:
    from core import get_core, EventType
    from encoding import get_encoder
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت والإعدادات
# ============================================================

STORE_DIR = DATA_DIR / "memory_store"
STORE_DIR.mkdir(parents=True, exist_ok=True)

# مسارات الملفات لكل نوع ذاكرة
FILE_MAP = {
    "procedural": STORE_DIR / "procedural.json",
    "semantic": STORE_DIR / "semantic.json",
    "episodic": STORE_DIR / "episodic.json",
    "spatial": STORE_DIR / "spatial.json",
    "emotional": STORE_DIR / "emotional.json",
    "associative": STORE_DIR / "associative.json",
    "index": STORE_DIR / "index.json",
    "backup": STORE_DIR / "backup.json"
}

# إعدادات التخزين
MAX_BACKUPS = 5
AUTO_BACKUP_INTERVAL = 3600  # ساعة واحدة
INDEX_REBUILD_INTERVAL = 86400  # 24 ساعة
QUERY_CACHE_SIZE = 1000
QUERY_CACHE_TTL = 300  # 5 دقائق


# ============================================================
# نماذج البيانات المتطورة
# ============================================================

class MemoryKind(str, Enum):
    """أنواع الذاكرة في النظام"""
    PROCEDURAL = "procedural"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    SPATIAL = "spatial"
    EMOTIONAL = "emotional"
    ASSOCIATIVE = "associative"


class RelationType(str, Enum):
    """أنواع العلاقات الترابطية"""
    SIMILAR = "similar"
    CAUSAL = "causal"
    TEMPORAL = "temporal"
    OPPOSITE = "opposite"
    PART_OF = "part_of"
    EXAMPLE_OF = "example_of"
    LEADS_TO = "leads_to"
    CONFLICTS_WITH = "conflicts_with"
    DERIVED_FROM = "derived_from"
    PARADOX = "paradox"


@dataclass
class BaseMemoryItem:
    """العنصر الأساسي للذاكرة - موحد لجميع الأنواع"""
    id: str
    kind: str
    created_at: float
    updated_at: float
    importance: float
    access_count: int
    last_accessed: float
    tags: List[str]
    fingerprint: str
    encrypted_payload: str
    encoding_version: int = 2
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict) -> 'BaseMemoryItem':
        return BaseMemoryItem(**data)


@dataclass
class ProceduralMemory:
    """الذاكرة الإجرائية - المهارات والإجراءات التلقائية"""
    name: str
    description: str
    trigger_patterns: List[str]
    action_sequence: List[str]
    parameters: Dict[str, Any]
    execution_count: int = 0
    success_count: int = 0
    last_execution: Optional[float] = None
    average_duration: float = 0.0
    
    def success_rate(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count
    
    def is_automatic(self) -> bool:
        return self.execution_count > 10 and self.success_rate() > 0.8


@dataclass
class SemanticMemory:
    """الذاكرة الدلالية - المفاهيم والحقائق"""
    concept: str
    definition: str
    aliases: List[str]
    confidence: float
    source: str
    related_concepts: Dict[str, float]  # concept -> weight
    examples: List[str]
    counter_examples: List[str]
    certainty_history: List[Tuple[float, float]]  # (timestamp, confidence)
    
    def add_evidence(self, confidence_delta: float):
        self.confidence = min(1.0, max(0.0, self.confidence + confidence_delta))
        self.certainty_history.append((time.time(), self.confidence))
        if len(self.certainty_history) > 100:
            self.certainty_history = self.certainty_history[-100:]


@dataclass
class EpisodicMemory:
    """الذاكرة الحدثية - السيرة الذاتية"""
    title: str
    description: str
    timestamp: float
    location: str
    participants: List[str]
    emotions: Dict[str, float]  # emotion -> intensity
    importance: float
    linked_events: List[str]  # IDs of related events
    context: Dict[str, Any]
    sensory_data: Optional[Dict[str, Any]] = None  # روابط إلى بيانات حسية


@dataclass
class SpatialMemory:
    """الذاكرة المكانية - خريطة المعرفة"""
    anchor: str
    coordinates: Tuple[float, ...]
    neighbors: Dict[str, float]  # node_id -> distance
    region: str
    landmarks: List[str]
    pathways: Dict[str, List[str]]  # destination -> path
    embeddings: Optional[bytes] = None


@dataclass
class EmotionalMemory:
    """الذاكرة العاطفية - المشاعر والعلامات"""
    target_id: str
    target_type: str
    emotion: str
    intensity: float
    valence: float  # -1 (سلبي) إلى +1 (إيجابي)
    arousal: float  # 0 (هادئ) إلى 1 (مثير)
    reason: str
    source: str
    timestamp: float
    decay_rate: float = 0.01  # تتلاشى المشاعر مع الوقت
    
    def current_intensity(self) -> float:
        """حساب الشدة الحالية مع مراعاة التلاشي"""
        age = time.time() - self.timestamp
        decay = math.exp(-self.decay_rate * age / 86400)  # تلاشي يومي
        return self.intensity * decay


@dataclass
class AssociativeMemory:
    """الذاكرة الترابطية - الروابط بين المفاهيم"""
    source: str
    target: str
    relation_type: str
    strength: float
    count: int
    first_seen: float
    last_seen: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def reinforce(self, delta: float = 0.1):
        """تقوية الرابط الترابطي"""
        self.strength = min(1.0, self.strength + delta)
        self.count += 1
        self.last_seen = time.time()
    
    def weaken(self, delta: float = 0.05):
        """إضعاف الرابط الترابطي"""
        self.strength = max(0.0, self.strength - delta)


# ============================================================
# الفهرس المتطور (Fast Search)
# ============================================================

class MemoryIndex:
    """
    فهرس متطور للبحث السريع في جميع أنواع الذاكرة.
    يدعم البحث النصي، البحث بالعلامات، البحث بالتشابه.
    """
    
    def __init__(self, index_file: Path):
        self.index_file = index_file
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)  # term -> item_ids
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)      # tag -> item_ids
        self.type_index: Dict[str, Set[str]] = defaultdict(set)     # kind -> item_ids
        self.importance_index: List[Tuple[float, str]] = []         # (importance, id)
        self.time_index: List[Tuple[float, str]] = []               # (timestamp, id)
        
        self._lock = threading.Lock()
        self._load()
    
    def _load(self):
        """تحميل الفهرس من القرص"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    self.inverted_index = {k: set(v) for k, v in data.get("inverted", {}).items()}
                    self.tag_index = {k: set(v) for k, v in data.get("tags", {}).items()}
                    self.type_index = {k: set(v) for k, v in data.get("types", {}).items()}
                    self.importance_index = [(imp, id) for imp, id in data.get("importance", [])]
                    self.time_index = [(ts, id) for ts, id in data.get("time", [])]
                    
                    logger.info(f"📇 تم تحميل الفهرس: {len(self.inverted_index)} مصطلح")
            except Exception as e:
                logger.error(f"فشل تحميل الفهرس: {e}")
    
    def save(self):
        """حفظ الفهرس إلى القرص"""
        with self._lock:
            data = {
                "inverted": {k: list(v) for k, v in self.inverted_index.items()},
                "tags": {k: list(v) for k, v in self.tag_index.items()},
                "types": {k: list(v) for k, v in self.type_index.items()},
                "importance": self.importance_index,
                "time": self.time_index,
                "updated_at": time.time()
            }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_item(self, item_id: str, kind: str, tags: List[str], 
                 text_content: str, importance: float, timestamp: float):
        """إضافة عنصر إلى الفهرس"""
        with self._lock:
            # فهرس النص
            words = text_content.lower().split()
            for word in words[:50]:  # أقصى 50 كلمة لكل عنصر
                if len(word) > 2:
                    self.inverted_index[word].add(item_id)
            
            # فهرس العلامات
            for tag in tags:
                self.tag_index[tag].add(item_id)
            
            # فهرس النوع
            self.type_index[kind].add(item_id)
            
            # فهرس الأهمية (الحفاظ على الترتيب)
            heapq.heappush(self.importance_index, (-importance, item_id))  # سالب للترتيب التنازلي
            if len(self.importance_index) > 10000:
                self.importance_index = heapq.nlargest(5000, self.importance_index)
            
            # فهرس الوقت
            heapq.heappush(self.time_index, (-timestamp, item_id))
            if len(self.time_index) > 10000:
                self.time_index = heapq.nlargest(5000, self.time_index)
    
    def search(self, query: str, kind: Optional[str] = None, 
               tag: Optional[str] = None, limit: int = 50) -> List[str]:
        """البحث في الفهرس"""
        with self._lock:
            words = query.lower().split()
            if not words:
                return []
            
            # جمع النتائج من كل كلمة
            results = None
            for word in words[:5]:
                if len(word) > 2:
                    word_results = self.inverted_index.get(word, set())
                    if results is None:
                        results = word_results.copy()
                    else:
                        results &= word_results
            
            if results is None:
                return []
            
            # تصفية حسب النوع
            if kind:
                kind_results = self.type_index.get(kind, set())
                results &= kind_results
            
            # تصفية حسب العلامة
            if tag:
                tag_results = self.tag_index.get(tag, set())
                results &= tag_results
            
            return list(results)[:limit]
    
    def get_by_importance(self, limit: int = 50) -> List[str]:
        """الحصول على العناصر الأكثر أهمية"""
        with self._lock:
            return [id for _, id in self.importance_index[:limit]]
    
    def get_by_time(self, limit: int = 50) -> List[str]:
        """الحصول على أحدث العناصر"""
        with self._lock:
            return [id for _, id in self.time_index[:limit]]


# ============================================================
# الطبقات الصلبة - النواة
# ============================================================

class SolidMemoryStore:
    """
    الطبقات الصلبة للذاكرة السيادية.
    
    تخزن جميع أنواع الذاكرة بشكل دائم، مشفر، ومتكامل.
    """
    
    def __init__(self):
        self.core = get_core()
        self.encoder = get_encoder()
        self.index = MemoryIndex(FILE_MAP["index"])
        
        # تحميل البيانات الموجودة
        self._data: Dict[str, Dict[str, BaseMemoryItem]] = {}
        self._lock = threading.RLock()
        
        for kind in MemoryKind:
            self._data[kind.value] = {}
            self._load_kind(kind.value)
        
        # خلفية للنسخ الاحتياطي التلقائي
        self._backup_thread = threading.Thread(target=self._auto_backup_loop, daemon=True)
        self._backup_thread.start()
        
        # خلفية لإعادة بناء الفهرس
        self._rebuild_thread = threading.Thread(target=self._auto_rebuild_loop, daemon=True)
        self._rebuild_thread.start()
        
        logger.info(f"📀 الطبقات الصلبة جاهزة")
        self._log_statistics()
    
    def _load_kind(self, kind: str):
        """تحميل نوع معين من الذاكرة من القرص"""
        path = FILE_MAP.get(kind)
        if not path or not path.exists():
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                items_data = json.load(f)
                
            for item_data in items_data:
                try:
                    item = BaseMemoryItem.from_dict(item_data)
                    self._data[kind][item.id] = item
                    
                    # إعادة بناء فهرس سريع
                    if hasattr(self, 'index'):
                        payload = self._decrypt_payload(item.encrypted_payload, kind)
                        text_content = self._extract_text_content(payload, kind)
                        self.index.add_item(
                            item.id, kind, item.tags,
                            text_content, item.importance, item.created_at
                        )
                except Exception as e:
                    logger.error(f"خطأ في تحميل العنصر {kind}: {e}")
                    
            logger.info(f"📁 تحميل {kind}: {len(self._data[kind])} عنصر")
        except Exception as e:
            logger.error(f"فشل تحميل {kind}: {e}")
    
    def _save_kind(self, kind: str):
        """حفظ نوع معين من الذاكرة إلى القرص"""
        path = FILE_MAP.get(kind)
        if not path:
            return
        
        with self._lock:
            items_data = [item.to_dict() for item in self._data[kind].values()]
            
            # كتابة ذرية
            tmp_path = path.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(items_data, f, ensure_ascii=False, indent=2)
            tmp_path.replace(path)
    
    def _encrypt_payload(self, payload: Dict, kind: str) -> str:
        """تشفير الـ payload للتخزين"""
        # استخدام التشفير السيادي
        encoded = self.encoder.encode(payload, importance=0.5)
        return encoded
    
    def _decrypt_payload(self, encrypted: str, kind: str) -> Dict:
        """فك تشفير الـ payload"""
        decoded = self.encoder.decode(encrypted)
        if decoded and decoded.get("_decoded"):
            # محاولة استرجاع البيانات
            content = decoded.get("content", "")
            return {"_decoded_content": content, "_fingerprint": decoded.get("_fingerprint")}
        return {"_error": "فشل فك التشفير"}
    
    def _extract_text_content(self, payload: Dict, kind: str) -> str:
        """استخراج النص من الـ payload للفهرسة"""
        if kind == "semantic":
            return payload.get("concept", "") + " " + payload.get("definition", "")
        elif kind == "episodic":
            return payload.get("title", "") + " " + payload.get("description", "")
        elif kind == "procedural":
            return payload.get("name", "") + " " + " ".join(payload.get("trigger_patterns", []))
        elif kind == "associative":
            return payload.get("source", "") + " " + payload.get("target", "")
        else:
            return json.dumps(payload)
    
    def _log_statistics(self):
        """تسجيل إحصائيات التخزين"""
        stats = self.get_statistics()
        logger.info(f"📊 إحصائيات التخزين: {stats['total_items']} عنصر, {stats['total_size_kb']:.2f} KB")
    
    def _auto_backup_loop(self):
        """نسخ احتياطي تلقائي دوري"""
        while True:
            time.sleep(AUTO_BACKUP_INTERVAL)
            self.create_backup()
    
    def _auto_rebuild_loop(self):
        """إعادة بناء الفهرس التلقائي"""
        while True:
            time.sleep(INDEX_REBUILD_INTERVAL)
            self.rebuild_index()
    
    # ============================================================
    # الواجهات العامة
    # ============================================================
    
    def save(self, kind: Union[str, MemoryKind], payload: Dict[str, Any],
             importance: float = 0.5, tags: Optional[List[str]] = None,
             store_in_core: bool = True) -> str:
        """
        حفظ عنصر في الذاكرة.
        
        Args:
            kind: نوع الذاكرة
            payload: المحتوى
            importance: الأهمية (0-1)
            tags: العلامات
            store_in_core: هل نسجل في السجل السيادي؟
        
        Returns:
            ID العنصر المحفوظ
        """
        if isinstance(kind, MemoryKind):
            kind = kind.value
        
        if kind not in [k.value for k in MemoryKind]:
            raise ValueError(f"نوع ذاكرة غير معروف: {kind}")
        
        if tags is None:
            tags = []
        
        with self._lock:
            # إنشاء العنصر
            item_id = hashlib.blake2b(f"{kind}:{time.time()}:{uuid.uuid4()}".encode(), digest_size=16).hexdigest()
            timestamp = time.time()
            
            # تشفير الـ payload
            encrypted = self._encrypt_payload(payload, kind)
            
            # بصمة للمحتوى
            fingerprint = self.encoder.fingerprint(payload)
            
            item = BaseMemoryItem(
                id=item_id,
                kind=kind,
                created_at=timestamp,
                updated_at=timestamp,
                importance=min(1.0, max(0.0, importance)),
                access_count=0,
                last_accessed=timestamp,
                tags=tags,
                fingerprint=fingerprint,
                encrypted_payload=encrypted,
                encoding_version=2
            )
            
            # تخزين
            self._data[kind][item_id] = item
            
            # تحديث الفهرس
            text_content = self._extract_text_content(payload, kind)
            self.index.add_item(item_id, kind, tags, text_content, importance, timestamp)
            
            # حفظ إلى القرص
            self._save_kind(kind)
            
            # تسجيل في السجل السيادي
            if store_in_core:
                self.core.append_event(
                    event_type=f"store::{kind}",
                    payload={
                        "id": item_id,
                        "kind": kind,
                        "importance": importance,
                        "tags": tags,
                        "fingerprint": fingerprint[:16]
                    }
                )
            
            logger.debug(f"💾 حفظ في {kind}: {item_id[:12]}... (أهمية: {importance})")
            return item_id
    
    def get(self, kind: Union[str, MemoryKind], item_id: str) -> Optional[Dict[str, Any]]:
        """استرجاع عنصر من الذاكرة"""
        if isinstance(kind, MemoryKind):
            kind = kind.value
        
        with self._lock:
            item = self._data.get(kind, {}).get(item_id)
            if not item:
                return None
            
            # تحديث إحصائيات الوصول
            item.access_count += 1
            item.last_accessed = time.time()
            self._save_kind(kind)
            
            # فك التشفير
            payload = self._decrypt_payload(item.encrypted_payload, kind)
            payload["_metadata"] = {
                "id": item.id,
                "importance": item.importance,
                "tags": item.tags,
                "created_at": item.created_at,
    
