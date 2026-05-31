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
import math
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
    from memory.core import get_core, EventType
    from memory.encoding import get_encoder
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
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة للتخزين الصلب
    # -------------------------
    def reset(self, preserve_data: bool = False):
        """
        إعادة تهيئة كاملة للتخزين الصلب.
        
        Args:
            preserve_data: إذا True، يحتفظ بالبيانات ولا يمسحها
        """
        logger.info("🔄 إعادة تهيئة التخزين الصلب...")
        
        if not preserve_data:
            # مسح جميع البيانات في الذاكرة
            for kind in self._data:
                self._data[kind].clear()
            
            # حذف ملفات التخزين
            for kind, path in FILE_MAP.items():
                if path.exists():
                    # نسخ احتياطي قبل الحذف
                    backup_file = path.with_suffix('.json.bak')
                    import shutil
                    shutil.copy2(path, backup_file)
                    path.unlink()
                    logger.debug(f"📁 تم حذف ملف {kind}، نسخة احتياطية في {backup_file}")
                    
                    # إعادة إنشاء ملف فارغ
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump([], f)
        
        # إعادة تحميل الفهرس
        self.index = MemoryIndex(FILE_MAP["index"])
        
        # إعادة تحميل البيانات من الملفات (إذا كانت موجودة)
        for kind in MemoryKind:
            self._load_kind(kind.value)
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="memory::store_reset",
            payload={
                "timestamp": time.time(),
                "preserve_data": preserve_data,
                "status": "memory_store_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة التخزين الصلب اكتملت")
    
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
                "access_count": item.access_count
            }
            
            return payload
    
    def query(self, kind: Union[str, MemoryKind], 
              tag: Optional[str] = None,
              min_importance: float = 0.0,
              limit: int = 50,
              search_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        استعلام متقدم عن الذاكرة.
        
        Args:
            kind: نوع الذاكرة
            tag: تصفية بالعلامة
            min_importance: الحد الأدنى للأهمية
            limit: الحد الأقصى للنتائج
            search_text: بحث نصي
        """
        if isinstance(kind, MemoryKind):
            kind = kind.value
        
        with self._lock:
            # البحث في الفهرس إذا كان هناك نص بحث
            if search_text:
                item_ids = self.index.search(search_text, kind=kind, tag=tag, limit=limit)
            else:
                # استخدام الفهرس حسب الأهمية أو الوقت
                if min_importance > 0:
                    item_ids = self.index.get_by_importance(limit * 2)
                else:
                    item_ids = self.index.get_by_time(limit * 2)
                
                # تصفية حسب النوع والعلامة
                if kind:
                    type_items = self.index.type_index.get(kind, set())
                    item_ids = [id for id in item_ids if id in type_items]
                if tag:
                    tag_items = self.index.tag_index.get(tag, set())
                    item_ids = [id for id in item_ids if id in tag_items]
            
            # جمع النتائج
            results = []
            for item_id in item_ids[:limit]:
                item = self._data.get(kind, {}).get(item_id)
                if item and item.importance >= min_importance:
                    payload = self._decrypt_payload(item.encrypted_payload, kind)
                    payload["_id"] = item.id
                    payload["_importance"] = item.importance
                    payload["_tags"] = item.tags
                    results.append(payload)
            
            return results
    
    def delete(self, kind: Union[str, MemoryKind], item_id: str, 
               reason: str = "user_request") -> bool:
        """حذف عنصر من الذاكرة (نادراً ما يُستخدم)"""
        if isinstance(kind, MemoryKind):
            kind = kind.value
        
        with self._lock:
            if item_id not in self._data.get(kind, {}):
                return False
            
            # تسجيل الحذف في السجل السيادي
            self.core.append_event(
                event_type=f"delete::{kind}",
                payload={"id": item_id, "reason": reason}
            )
            
            # حذف
            del self._data[kind][item_id]
            self._save_kind(kind)
            
            logger.info(f"🗑️ حذف من {kind}: {item_id[:12]}...")
            return True
    
    def update_importance(self, kind: Union[str, MemoryKind], 
                          item_id: str, delta: float) -> bool:
        """تحديث أهمية عنصر (تعزيز أو إضعاف)"""
        if isinstance(kind, MemoryKind):
            kind = kind.value
        
        with self._lock:
            item = self._data.get(kind, {}).get(item_id)
            if not item:
                return False
            
            item.importance = min(1.0, max(0.0, item.importance + delta))
            item.updated_at = time.time()
            self._save_kind(kind)
            return True
    
    # ============================================================
    # واجهات متخصصة لكل نوع ذاكرة
    # ============================================================
    
    def save_procedural(self, name: str, description: str,
                        trigger_patterns: List[str], action_sequence: List[str],
                        parameters: Optional[Dict] = None,
                        importance: float = 0.8) -> str:
        """حفظ مهارة إجرائية"""
        if parameters is None:
            parameters = {}
        
        payload = {
            "name": name,
            "description": description,
            "trigger_patterns": trigger_patterns,
            "action_sequence": action_sequence,
            "parameters": parameters
        }
        
        return self.save("procedural", payload, importance=importance, 
                        tags=["skill", name])
    
    def save_semantic(self, concept: str, definition: str,
                      aliases: Optional[List[str]] = None,
                      related_concepts: Optional[Dict[str, float]] = None,
                      examples: Optional[List[str]] = None,
                      confidence: float = 0.5) -> str:
        """حفظ مفهوم دلالي"""
        if aliases is None:
            aliases = []
        if related_concepts is None:
            related_concepts = {}
        if examples is None:
            examples = []
        
        payload = {
            "concept": concept,
            "definition": definition,
            "aliases": aliases,
            "confidence": confidence,
            "related_concepts": related_concepts,
            "examples": examples,
            "counter_examples": []
        }
        
        return self.save("semantic", payload, importance=confidence,
                        tags=["concept", concept])
    
    def save_episodic(self, title: str, description: str,
                      timestamp: Optional[float] = None,
                      location: str = "",
                      participants: Optional[List[str]] = None,
                      emotions: Optional[Dict[str, float]] = None,
                      importance: float = 0.7) -> str:
        """حفظ حدث (ذاكرة سيرة ذاتية)"""
        if timestamp is None:
            timestamp = time.time()
        if participants is None:
            participants = []
        if emotions is None:
            emotions = {}
        
        payload = {
            "title": title,
            "description": description,
            "timestamp": timestamp,
            "location": location,
            "participants": participants,
            "emotions": emotions,
            "linked_events": []
        }
        
        return self.save("episodic", payload, importance=importance,
                        tags=["episode", title[:20]])
    
    def save_associative(self, source: str, target: str,
                         relation_type: str, strength: float = 0.5,
                         metadata: Optional[Dict] = None) -> str:
        """حفظ رابط ترابطي بين مفهومين"""
        if metadata is None:
            metadata = {}
        
        payload = {
            "source": source,
            "target": target,
            "relation_type": relation_type,
            "strength": strength,
            "metadata": metadata
        }
        
        return self.save("associative", payload, importance=strength,
                        tags=["association", relation_type])
    
    def save_emotional(self, target_id: str, target_type: str,
                       emotion: str, intensity: float,
                       valence: float, arousal: float,
                       reason: str, source: str = "system") -> str:
        """حفظ علامة عاطفية"""
        payload = {
            "target_id": target_id,
            "target_type": target_type,
            "emotion": emotion,
            "intensity": min(1.0, max(0.0, intensity)),
            "valence": min(1.0, max(-1.0, valence)),
            "arousal": min(1.0, max(0.0, arousal)),
            "reason": reason,
            "source": source
        }
        
        return self.save("emotional", payload, importance=intensity,
                        tags=["emotion", emotion])
    
    # ============================================================
    # الاستعلامات المتقدمة
    # ============================================================
    
    def find_related(self, concept: str, relation_type: Optional[str] = None,
                     limit: int = 10) -> List[Dict[str, Any]]:
        """العثور على مفاهيم مرتبطة بمفهوم معين"""
        results = self.query("associative", search_text=concept, limit=limit)
        
        filtered = []
        for r in results:
            if relation_type and r.get("relation_type") != relation_type:
                continue
            filtered.append(r)
        
        return filtered
    
    def get_emotional_context(self, target_id: str) -> Dict[str, float]:
        """الحصول على السياق العاطفي لهدف معين"""
        results = self.query("emotional", search_text=target_id, limit=20)
        
        emotions = {}
        for r in results:
            emotion = r.get("emotion")
            intensity = r.get("intensity", 0)
            if emotion:
                emotions[emotion] = max(emotions.get(emotion, 0), intensity)
        
        return emotions
    
    def get_statistics(self) -> Dict[str, Any]:
        """إحصائيات التخزين"""
        total_items = sum(len(items) for items in self._data.values())
        total_size = 0
        
        for kind, path in FILE_MAP.items():
            if path.exists():
                total_size += path.stat().st_size
        
        return {
            "total_items": total_items,
            "total_size_kb": total_size / 1024,
            "by_type": {kind: len(items) for kind, items in self._data.items()},
            "index_size": len(self.index.inverted_index),
            "timestamp": time.time()
        }
    
    def create_backup(self) -> Path:
        """إنشاء نسخة احتياطية"""
        backup_file = STORE_DIR / f"backup_{int(time.time())}.json"
        
        with self._lock:
            all_data = {}
            for kind, items in self._data.items():
                all_data[kind] = [item.to_dict() for item in items.values()]
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        # تنظيف النسخ القديمة
        backups = sorted(STORE_DIR.glob("backup_*.json"))
        for old_backup in backups[:-MAX_BACKUPS]:
            old_backup.unlink()
        
        logger.info(f"💾 نسخة احتياطية: {backup_file.name}")
        return backup_file
    
    def rebuild_index(self):
        """إعادة بناء الفهرس بالكامل"""
        logger.info("🔄 إعادة بناء الفهرس...")
        
        new_index = MemoryIndex(FILE_MAP["index"])
        
        for kind, items in self._data.items():
            for item in items.values():
                payload = self._decrypt_payload(item.encrypted_payload, kind)
                text_content = self._extract_text_content(payload, kind)
                new_index.add_item(
                    item.id, kind, item.tags,
                    text_content, item.importance, item.created_at
                )
        
        self.index = new_index
        self.index.save()
        logger.info("✅ إعادة بناء الفهرس اكتملت")
    
    def vacuum(self):
        """تنظيف وتجميع التخزين"""
        logger.info("🧹 بدء تنظيف التخزين...")
        
        for kind in MemoryKind:
            self._save_kind(kind.value)
        
        self.rebuild_index()
        logger.info("✅ اكتمل تنظيف التخزين")


# ============================================================
# الـ Singleton
# ============================================================

_store_instance: Optional[SolidMemoryStore] = None
_store_lock = threading.Lock()


def get_store() -> SolidMemoryStore:
    """الحصول على النسخة الوحيدة من الطبقات الصلبة"""
    global _store_instance
    if _store_instance is None:
        with _store_lock:
            if _store_instance is None:
                _store_instance = SolidMemoryStore()
    return _store_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("📀 الطبقات الصلبة للذاكرة السيادية - اختبار متكامل")
    print("=" * 70 + "\n")
    
    store = get_store()
    
    # 1) حفظ مفهوم دلالي
    print("📚 حفظ مفهوم دلالي...")
    concept_id = store.save_semantic(
        concept="الذكاء السيادي",
        definition="نظام ذكاء اصطناعي يتحكم بنفسه وبسجله، لا يُخترق ولا يُسيطر عليه",
        aliases=["AI سيادي", "ذكاء حر", "Sovereign AI"],
        related_concepts={"سيادة": 0.9, "أمن": 0.8, "وعي": 0.7},
        confidence=0.85
    )
    print(f"   ID: {concept_id[:16]}...")
    
    # 2) حفظ مهارة إجرائية
    print("\n🦿 حفظ مهارة إجرائية...")
    skill_id = store.save_procedural(
        name="معالجة الأوامر السيادية",
        description="معالجة أوامر السيد والتحقق من هويته",
        trigger_patterns=["أمر السيد", "وافق", "ارفض", "حالة النظام"],
        action_sequence=["verify_identity", "process_command", "log_action"],
        importance=0.95
    )
    print(f"   ID: {skill_id[:16]}...")
    
    # 3) حفظ حدث
    print("\n📅 حفظ حدث...")
    episode_id = store.save_episodic(
        title="بداية النظام",
        description="تم تشغيل الذاكرة السيادية لأول مرة",
        location="الخادم الرئيسي",
        participants=["السيد", "النظام"],
        emotions={"joy": 0.8, "anticipation": 0.9},
        importance=1.0
    )
    print(f"   ID: {episode_id[:16]}...")
    
    # 4) حفظ رابط ترابطي
    print("\n🔗 حفظ رابط ترابطي...")
    assoc_id = store.save_associative(
        source="الذكاء السيادي",
        target="السيادة",
        relation_type="similar",
        strength=0.95
    )
    print(f"   ID: {assoc_id[:16]}...")
    
    # 5) حفظ علامة عاطفية
    print("\n💖 حفظ علامة عاطفية...")
    emotion_id = store.save_emotional(
        target_id=concept_id,
        target_type="semantic",
        emotion="trust",
        intensity=0.9,
        valence=0.8,
        arousal=0.3,
        reason="هذا المفهوم يمثل جوهر النظام"
    )
    print(f"   ID: {emotion_id[:16]}...")
    
    # 6) استعلام
    print("\n🔍 استعلام:")
    results = store.query("semantic", search_text="سيادي", limit=5)
    for r in results:
        print(f"   - {r.get('concept', 'N/A')}: {r.get('definition', '')[:50]}...")
    
    # 7) إحصائيات
    print("\n📊 الإحصائيات:")
    stats = store.get_statistics()
    print(f"   إجمالي العناصر: {stats['total_items']}")
    print(f"   الحجم الإجمالي: {stats['total_size_kb']:.2f} KB")
    for kind, count in stats['by_type'].items():
        if count > 0:
            print(f"   - {kind}: {count} عنصر")
    
    # 8) السياق العاطفي
    print("\n💖 السياق العاطفي للمفهوم:")
    emotions = store.get_emotional_context(concept_id)
    for emotion, intensity in emotions.items():
        print(f"   {emotion}: {intensity:.2f}")
    
    print("\n" + "=" * 70)
    print("✅ الطبقات الصلبة جاهزة - تخزين حقيقي متكامل")
    print("=" * 70)
