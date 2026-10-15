# backend/memory/biological/learning.py
# 🧠 التعلم التكيفي - قلب الذكاء النابض، النمو من خلال الخبرة
# الإصدار: 3.0.0 - التحول المعرفي عبر الزمن

"""
نظام التعلم التكيفي للذاكرة السيادية.

الفلسفة:
- التعلم ليس إضافة معلومات، بل هو تحول في البنية
- كل تجربة تغير النظام بشكل دائم
- التكرار يولد التلقائية
- الندرة تخلق العمق
- السياق يعيد تعريف المعنى

هذا ليس تحديث أوزان. هذا هو النمو المعرفي الحقيقي.
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
from collections import defaultdict, deque
import heapq

try:
    from ..core import get_core, EventType
    from ..store import get_store, MemoryKind
    from ..dynamic import get_dynamic_memory
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from memory.store import get_store, MemoryKind
    from memory.dynamic import get_dynamic_memory
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات التعلم
# ============================================================

LEARNING_DIR = DATA_DIR / "learning"
LEARNING_LOG = LEARNING_DIR / "learning_log.jsonl"
LEARNING_STATE_FILE = LEARNING_DIR / "learning_state.json"
LEARNING_PATTERNS_FILE = LEARNING_DIR / "patterns.json"
LEARNING_MODELS_DIR = LEARNING_DIR / "models"

for d in [LEARNING_DIR, LEARNING_MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات التعلم
LEARNING_LEVEL_NONE = 0             # لا تعلم
LEARNING_LEVEL_PASSIVE = 1          # تعلم سلبي (مراقبة فقط)
LEARNING_LEVEL_ACTIVE = 2           # تعلم نشط (تحديثات فورية)
LEARNING_LEVEL_DEEP = 3             # تعلم عميق (استخراج أنماط)
LEARNING_LEVEL_GENERATIVE = 4       # تعلم توليدي (خلق معرفة جديدة)
LEARNING_LEVEL_TRANSFORMATIVE = 5   # تعلم تحويلي (إعادة هيكلة)

# أنواع التعلم
LEARNING_TYPE_SUPERVISED = "supervised"     # تعلم موجّه
LEARNING_TYPE_UNSUPERVISED = "unsupervised" # تعلم غير موجّه
LEARNING_TYPE_REINFORCEMENT = "reinforcement" # تعلم معزز
LEARNING_TYPE_IMITATION = "imitation"       # تعلم بالمحاكاة
LEARNING_TYPE_TRANSFER = "transfer"         # تعلم انتقالي
LEARNING_TYPE_METACOGNITIVE = "metacognitive" # تعلم ما وراء معرفي

# آليات التعلم
MECHANISM_ASSOCIATION = "association"       # تكوين ارتباطات
MECHANISM_GENERALIZATION = "generalization" # تعميم
MECHANISM_DISCRIMINATION = "discrimination" # تمييز
MECHANISM_ABSTRACTION = "abstraction"       # تجريد
MECHANISM_ANALOGY = "analogy"               # قياس
MECHANISM_COMPOSITION = "composition"       # تركيب
MECHANISM_DECOMPOSITION = "decomposition"   # تحليل


@dataclass
class LearningExperience:
    """تجربة تعلم - وحدة الخبرة الأساسية"""
    id: str
    timestamp: float
    input_data: Any
    output_data: Any
    context: Dict[str, Any]
    importance: float
    outcome: str  # "success", "failure", "partial"
    feedback: Optional[float]  # -1 إلى +1


@dataclass
class LearnedPattern:
    """نمط متعلم - معرفة مستخرجة من الخبرات"""
    id: str
    pattern_type: str
    content: Dict[str, Any]
    confidence: float
    occurrences: int
    last_updated: float
    source_experiences: List[str]


@dataclass
class CognitiveSchema:
    """مخطط معرفي - بنية معرفية عليا"""
    id: str
    name: str
    description: str
    elements: List[str]  # مفاهيم أو علاقات
    relations: Dict[Tuple[str, str], float]
    activation: float
    last_used: float


# ============================================================
# نظام التعلم التكيفي
# ============================================================

class AdaptiveLearning:
    """
    نظام التعلم التكيفي - النمو المعرفي عبر الخبرة.
    
    المبادئ:
    1. كل تجربة تغير النظام
    2. التكرار يولد التلقائية
    3. الندرة تخلق العمق
    4. السياق يعيد تعريف المعنى
    5. التعلم لا يتوقف أبداً
    """
    
    def __init__(self):
        self.core = get_core()
        self.store = get_store()
        self.dynamic = get_dynamic_memory()
        
        # حالة التعلم
        self.learning_level = LEARNING_LEVEL_ACTIVE
        self.learning_type = LEARNING_TYPE_UNSUPERVISED
        
        # خبرات التعلم
        self.experiences: List[LearningExperience] = []
        self.experience_buffer: deque = deque(maxlen=1000)
        
        # الأنماط المتعلمة
        self.patterns: Dict[str, LearnedPattern] = {}
        self.pattern_discovery_counters: Dict[str, int] = defaultdict(int)
        
        # المخططات المعرفية
        self.schemas: Dict[str, CognitiveSchema] = {}
        
        # إحصائيات التعلم
        self.learning_stats = {
            "total_experiences": 0,
            "patterns_discovered": 0,
            "schemas_formed": 0,
            "associations_formed": 0,
            "generalizations_made": 0
        }
        
        # خلفيات التعلم
        self._active = True
        self._experience_processor = threads.start_managed(self._process_experiences_loop, owner=self)
        
        self._pattern_discovery = threads.start_managed(self._discover_patterns_loop, owner=self)
        
        self._schema_builder = threads.start_managed(self._build_schemas_loop, owner=self)
        
        self._reinforcement_learner = threads.start_managed(self._reinforcement_learning_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        self._load_patterns()
        
        logger.info("🧠 نظام التعلم التكيفي جاهز - النمو المعرفي عبر الخبرة")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لنظام التعلم التكيفي
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لنظام التعلم التكيفي.
        
        يمسح:
        - سجل الخبرات (experiences)
        - الأنماط المتعلمة (patterns)
        - المخططات المعرفية (schemas)
        - إحصائيات التعلم
        """
        logger.info("🔄 إعادة تهيئة نظام التعلم التكيفي...")
        
        # مسح سجل الخبرات
        self.experiences.clear()
        self.experience_buffer.clear()
        
        # مسح الأنماط المتعلمة
        self.patterns.clear()
        self.pattern_discovery_counters.clear()
        
        # مسح المخططات المعرفية
        self.schemas.clear()
        
        # إعادة تعيين إحصائيات التعلم
        self.learning_stats = {
            "total_experiences": 0,
            "patterns_discovered": 0,
            "schemas_formed": 0,
            "associations_formed": 0,
            "generalizations_made": 0
        }
        
        # إعادة تعيين مستوى ونوع التعلم
        self.learning_level = LEARNING_LEVEL_ACTIVE
        self.learning_type = LEARNING_TYPE_UNSUPERVISED
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="biological::learning_reset",
            payload={
                "timestamp": time.time(),
                "status": "learning_system_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة نظام التعلم التكيفي اكتملت - صفحة بيضاء جديدة")
    
    # ============================================================
    # المستوى 1: تسجيل الخبرات (Experience Recording)
    # ============================================================
    
    def record_experience(self, input_data: Any, output_data: Any, 
                          context: Dict[str, Any] = None,
                          importance: float = 0.5,
                          outcome: str = "success",
                          feedback: Optional[float] = None) -> str:
        """
        تسجيل تجربة تعلم جديدة.
        
        كل تفاعل هو فرصة للتعلم.
        """
        if context is None:
            context = {}
        
        exp_id = f"exp_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        experience = LearningExperience(
            id=exp_id,
            timestamp=time.time(),
            input_data=input_data,
            output_data=output_data,
            context=context,
            importance=importance,
            outcome=outcome,
            feedback=feedback
        )
        
        self.experience_buffer.append(experience)
        self.learning_stats["total_experiences"] += 1
        
        # تسجيل في السجل
        self.core.append_event(
            event_type="learning::experience_recorded",
            payload={
                "exp_id": exp_id[:16],
                "outcome": outcome,
                "importance": importance
            }
        )
        
        logger.debug(f"📝 تجربة مسجلة: {exp_id[:16]}... (نتيجة: {outcome})")
        return exp_id
    
    def _process_experiences_loop(self):
        """معالجة التجارب في الخلفية"""
        while self._active:
            try:
                if self.experience_buffer:
                    # معالجة دفعة من التجارب
                    batch = []
                    while self.experience_buffer and len(batch) < 10:
                        exp = self.experience_buffer.popleft()
                        batch.append(exp)
                    
                    self._process_batch(batch)
                
                threads.interruptible_sleep(5)  # كل 5 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في معالجة التجارب: {e}")
                threads.interruptible_sleep(10)
    
    def _process_batch(self, experiences: List[LearningExperience]):
        """معالجة دفعة من التجارب"""
        for exp in experiences:
            # 1) تحديث الارتباطات بناءً على التجربة
            self._update_associations_from_experience(exp)
            
            # 2) استخراج أنماط محتملة
            self._extract_patterns_from_experience(exp)
            
            # 3) تحديث المخططات المعرفية
            self._update_schemas_from_experience(exp)
            
            # 4) تعزيز التعلم المعزز
            if exp.feedback is not None:
                self._apply_reinforcement(exp)
    
    # ============================================================
    # المستوى 2: تكوين الارتباطات (Association Formation)
    # ============================================================
    
    def _update_associations_from_experience(self, experience: LearningExperience):
        """تحديث الارتباطات الترابطية بناءً على التجربة"""
        
        # استخراج المفاهيم من المدخلات والمخرجات
        concepts = self._extract_concepts(experience.input_data)
        concepts.extend(self._extract_concepts(experience.output_data))
        concepts = list(set(concepts))
        
        # تقوية الارتباطات بين المفاهيم المتزامنة
        for i in range(len(concepts)):
            for j in range(i+1, len(concepts)):
                a = concepts[i]
                b = concepts[j]
                
                # حساب شدة التحديث
                delta = experience.importance * 0.1
                if experience.outcome == "success":
                    delta *= 1.5
                elif experience.outcome == "failure":
                    delta *= 0.5
                
                self._strengthen_association(a, b, delta)
                self.learning_stats["associations_formed"] += 1
    
    def _strengthen_association(self, a: str, b: str, delta: float):
        """تقوية ارتباط بين مفهومين"""
        # البحث عن الارتباط الموجود
        assoc_items = self.store.query("associative", search_text=f"{a} {b}", limit=100)
        
        found = False
        for item in assoc_items:
            if item.get("source") == a and item.get("target") == b:
                weight = item.get("weight", 0.5)
                new_weight = min(1.0, weight + delta)
                item["weight"] = new_weight
                found = True
                break
            elif item.get("source") == b and item.get("target") == a:
                weight = item.get("weight", 0.5)
                new_weight = min(1.0, weight + delta)
                item["weight"] = new_weight
                found = True
                break
        
        if not found:
            # إنشاء ارتباط جديد
            self.store.save_associative(
                source=a,
                target=b,
                relation_type="related",
                strength=0.5 + delta
            )
    
    def _extract_concepts(self, data: Any) -> List[str]:
        """استخراج المفاهيم من البيانات"""
        concepts = []
        data_str = str(data).lower()
        
        # البحث عن مفاهيم موجودة في الذاكرة الدلالية
        semantic_items = self.store.query("semantic", min_importance=0.0, limit=200)
        for item in semantic_items:
            concept = item.get("concept", "").lower()
            if concept and concept in data_str:
                concepts.append(concept)
        
        # إضافة كلمات مهمة كمفاهيم محتملة
        words = data_str.split()
        for word in words:
            if len(word) > 4 and word.isalpha() and word not in concepts:
                # كلمة مهمة - مرشح لمفهوم جديد
                concepts.append(word[:30])
        
        return list(set(concepts))[:20]
    
    # ============================================================
    # المستوى 3: اكتشاف الأنماط (Pattern Discovery)
    # ============================================================
    
    def _extract_patterns_from_experience(self, experience: LearningExperience):
        """استخراج أنماط محتملة من التجربة"""
        
        # نمط النجاح
        if experience.outcome == "success" and experience.importance > 0.7:
            pattern_key = f"success_pattern_{hashlib.md5(str(experience.input_data).encode()).hexdigest()[:12]}"
            self.pattern_discovery_counters[pattern_key] += 1
        
        # نمط الفشل
        elif experience.outcome == "failure" and experience.importance > 0.7:
            pattern_key = f"failure_pattern_{hashlib.md5(str(experience.input_data).encode()).hexdigest()[:12]}"
            self.pattern_discovery_counters[pattern_key] += 1
    
    def _discover_patterns_loop(self):
        """اكتشاف الأنماط بشكل دوري"""
        while self._active:
            try:
                if self.learning_level >= LEARNING_LEVEL_DEEP:
                    self._discover_patterns()
                threads.interruptible_sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في اكتشاف الأنماط: {e}")
                threads.interruptible_sleep(300)
    
    def _discover_patterns(self):
        """اكتشاف أنماط جديدة من التجارب المتراكمة"""
        new_patterns = []
        
        for pattern_key, count in list(self.pattern_discovery_counters.items()):
            if count > 5 and pattern_key not in self.patterns:
                # نمط جديد مكتشف
                pattern = LearnedPattern(
                    id=f"pattern_{int(time.time())}_{secrets.token_hex(4)}",
                    pattern_type="behavioral" if "success" in pattern_key else "avoidance",
                    content={"key": pattern_key, "confidence": min(1.0, count / 20)},
                    confidence=min(1.0, count / 20),
                    occurrences=count,
                    last_updated=time.time(),
                    source_experiences=[]
                )
                self.patterns[pattern.id] = pattern
                new_patterns.append(pattern.id)
                
                logger.info(f"🔍 نمط مكتشف: {pattern_key[:20]}... (ثقة: {pattern.confidence:.1%})")
        
        if new_patterns:
            self.learning_stats["patterns_discovered"] += len(new_patterns)
            self._save_patterns()
    
    # ============================================================
    # المستوى 4: بناء المخططات (Schema Building)
    # ============================================================
    
    def _update_schemas_from_experience(self, experience: LearningExperience):
        """تحديث المخططات المعرفية بناءً على التجربة"""
        
        # استخراج العناصر الرئيسية
        elements = self._extract_concepts(experience.input_data)
        elements.extend(self._extract_concepts(experience.output_data))
        
        if len(elements) < 2:
            return
        
        # البحث عن مخطط موجود
        for schema in self.schemas.values():
            # التحقق من التداخل
            overlap = set(schema.elements) & set(elements)
            if len(overlap) >= len(elements) * 0.5:
                # تحديث المخطط الموجود
                for elem in elements:
                    if elem not in schema.elements:
                        schema.elements.append(elem)
                schema.last_used = time.time()
                schema.activation = min(1.0, schema.activation + 0.1)
                return
        
        # إنشاء مخطط جديد
        schema_id = f"schema_{int(time.time())}_{secrets.token_hex(4)}"
        schema = CognitiveSchema(
            id=schema_id,
            name=f"schema_{len(self.schemas)}",
            description=f"مخطط مستخلص من تجربة: {str(experience.input_data)[:50]}",
            elements=elements,
            relations={},
            activation=0.5,
            last_used=time.time()
        )
        self.schemas[schema_id] = schema
        self.learning_stats["schemas_formed"] += 1
        
        logger.info(f"📐 مخطط معرفي جديد: {schema_id[:16]}... ({len(elements)} عنصر)")
    
    def _build_schemas_loop(self):
        """بناء المخططات بشكل دوري"""
        while self._active:
            try:
                if self.learning_level >= LEARNING_LEVEL_DEEP:
                    self._consolidate_schemas()
                threads.interruptible_sleep(600)  # كل 10 دقائق
            except Exception as e:
                logger.error(f"خطأ في بناء المخططات: {e}")
                threads.interruptible_sleep(600)
    
    def _consolidate_schemas(self):
        """دمج المخططات المتشابهة"""
        to_merge = []
        
        # البحث عن مخططات متشابهة
        schema_list = list(self.schemas.values())
        for i in range(len(schema_list)):
            for j in range(i+1, len(schema_list)):
                s1 = schema_list[i]
                s2 = schema_list[j]
                
                overlap = set(s1.elements) & set(s2.elements)
                if len(overlap) > len(s1.elements) * 0.7:
                    to_merge.append((s1.id, s2.id))
        
        # دمج المخططات
        for s1_id, s2_id in to_merge:
            if s1_id in self.schemas and s2_id in self.schemas:
                s1 = self.schemas[s1_id]
                s2 = self.schemas[s2_id]
                
                # دمج العناصر
                s1.elements = list(set(s1.elements + s2.elements))
                s1.activation = max(s1.activation, s2.activation)
                s1.last_used = max(s1.last_used, s2.last_used)
                
                # إزالة المخطط المدمج
                del self.schemas[s2_id]
                
                logger.debug(f"🔄 دمج مخططات: {s1_id[:12]} + {s2_id[:12]}")
    
    # ============================================================
    # المستوى 5: التعلم المعزز (Reinforcement Learning)
    # ============================================================
    
    def _apply_reinforcement(self, experience: LearningExperience):
        """تطبيق التعلم المعزز بناءً على التغذية الراجعة"""
        if experience.feedback is None:
            return
        
        # شدة التحديث تعتمد على قيمة التغذية الراجعة
        intensity = abs(experience.feedback) * experience.importance
        
        if experience.feedback > 0:
            # تعزيز إيجابي
            self._reinforce_positive(experience, intensity)
        else:
            # تعزيز سلبي
            self._reinforce_negative(experience, intensity)
    
    def _reinforce_positive(self, experience: LearningExperience, intensity: float):
        """تعزيز إيجابي - تقوية السلوك الناجح"""
        concepts = self._extract_concepts(experience.input_data)
        
        for concept in concepts:
            # رفع أهمية المفهوم
            semantic_items = self.store.query("semantic", search_text=concept, limit=5)
            for item in semantic_items:
                if item.get("concept") == concept:
                    old_importance = item.get("_importance", 0.5)
                    new_importance = min(1.0, old_importance + intensity * 0.1)
                    item["_importance"] = new_importance
                    break
    
    def _reinforce_negative(self, experience: LearningExperience, intensity: float):
        """تعزيز سلبي - إضعاف السلوك الفاشل"""
        concepts = self._extract_concepts(experience.input_data)
        
        for concept in concepts:
            semantic_items = self.store.query("semantic", search_text=concept, limit=5)
            for item in semantic_items:
                if item.get("concept") == concept:
                    old_importance = item.get("_importance", 0.5)
                    new_importance = max(0.1, old_importance - intensity * 0.05)
                    item["_importance"] = new_importance
                    break
    
    def _reinforcement_learning_loop(self):
        """حلقة التعلم المعزز المستمر"""
        while self._active:
            try:
                if self.learning_level >= LEARNING_LEVEL_ACTIVE:
                    # مراجعة التجارب السابقة وتعزيزها
                    for exp in self.experiences[-100:]:
                        if exp.feedback is not None:
                            self._apply_reinforcement(exp)
                threads.interruptible_sleep(3600)  # كل ساعة
            except Exception as e:
                logger.error(f"خطأ في التعلم المعزز: {e}")
                threads.interruptible_sleep(3600)
    
    # ============================================================
    # المستوى 6: التعلم التوليدي (Generative Learning)
    # ============================================================
    
    def generate_new_knowledge(self, seed: str, depth: int = 3) -> Dict[str, Any]:
        """
        توليد معرفة جديدة من الأنماط والمخططات الموجودة.
        
        أعلى مستوى من التعلم - خلق شيء جديد من القديم.
        """
        generated = {
            "seed": seed,
            "new_concepts": [],
            "new_associations": [],
            "confidence": 0.0
        }
        
        # توليد مفاهيم جديدة
        related_concepts = []
        for pattern in self.patterns.values():
            if seed.lower() in str(pattern.content).lower():
                related_concepts.append(pattern.id)
        
        if related_concepts:
            generated["new_concepts"] = related_concepts[:depth]
            generated["confidence"] = 0.6
        
        # توليد ارتباطات جديدة
        for schema in self.schemas.values():
            if seed in schema.elements:
                for elem in schema.elements:
                    if elem != seed:
                        generated["new_associations"].append((seed, elem))
        
        # تسجيل
        self.core.append_event(
            event_type="learning::knowledge_generated",
            payload={
                "seed": seed[:32],
                "new_concepts": len(generated["new_concepts"]),
                "new_associations": len(generated["new_associations"])
            }
        )
        
        return generated
    
    # ============================================================
    # المستوى 7: التعلم التحويلي (Transformative Learning)
    # ============================================================
    
    def transform_knowledge(self, target_area: str) -> Dict[str, Any]:
        """
        تعلم تحويلي - إعادة هيكلة المعرفة في منطقة معينة.
        
        أعلى مستوى من التطور المعرفي.
        """
        transformation = {
            "target_area": target_area,
            "schemas_reorganized": 0,
            "patterns_merged": 0,
            "new_insights": []
        }
        
        # إعادة هيكلة المخططات
        schemas_to_reorganize = []
        for schema in self.schemas.values():
            if target_area.lower() in schema.description.lower():
                schemas_to_reorganize.append(schema.id)
        
        transformation["schemas_reorganized"] = len(schemas_to_reorganize)
        
        # دمج الأنماط
        patterns_to_merge = []
        for pattern in self.patterns.values():
            if target_area.lower() in str(pattern.content).lower():
                patterns_to_merge.append(pattern.id)
        
        transformation["patterns_merged"] = len(patterns_to_merge) // 2
        
        # توليد رؤى جديدة
        transformation["new_insights"] = [
            f"تم إعادة تنظيم {len(schemas_to_reorganize)} مخطط في {target_area}",
            f"تم دمج {transformation['patterns_merged']} نمط"
        ]
        
        # تسجيل
        self.core.append_event(
            event_type="learning::transformative",
            payload={
                "target_area": target_area,
                "schemas_reorganized": transformation["schemas_reorganized"],
                "patterns_merged": transformation["patterns_merged"]
            }
        )
        
        logger.info(f"🔄 تعلم تحويلي في {target_area}: {transformation['schemas_reorganized']} مخطط, {transformation['patterns_merged']} نمط")
        
        return transformation
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة نظام التعلم"""
        try:
            state = {
                "learning_level": self.learning_level,
                "learning_type": self.learning_type,
                "learning_stats": self.learning_stats,
                "experiences_count": len(self.experiences),
                "patterns_count": len(self.patterns),
                "schemas_count": len(self.schemas),
                "saved_at": time.time()
            }
            with open(LEARNING_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة التعلم: {e}")
    
    def _load_state(self):
        """تحميل حالة نظام التعلم"""
        try:
            if LEARNING_STATE_FILE.exists():
                with open(LEARNING_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.learning_level = state.get("learning_level", LEARNING_LEVEL_ACTIVE)
                    self.learning_type = state.get("learning_type", LEARNING_TYPE_UNSUPERVISED)
                    self.learning_stats = state.get("learning_stats", self.learning_stats)
                logger.info("📂 تم تحميل حالة نظام التعلم")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة التعلم: {e}")
    
    def _save_patterns(self):
        """حفظ الأنماط المتعلمة"""
        try:
            patterns_data = {
                "patterns": [
                    {
                        "id": p.id,
                        "pattern_type": p.pattern_type,
                        "content": p.content,
                        "confidence": p.confidence,
                        "occurrences": p.occurrences,
                        "last_updated": p.last_updated
                    }
                    for p in self.patterns.values()
                ],
                "saved_at": time.time()
            }
            with open(LEARNING_PATTERNS_FILE, 'w', encoding='utf-8') as f:
                json.dump(patterns_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الأنماط: {e}")
    
    def _load_patterns(self):
        """تحميل الأنماط المتعلمة"""
        try:
            if LEARNING_PATTERNS_FILE.exists():
                with open(LEARNING_PATTERNS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for p_data in data.get("patterns", []):
                        pattern = LearnedPattern(**p_data)
                        self.patterns[pattern.id] = pattern
                logger.info(f"📂 تم تحميل {len(self.patterns)} نمطاً")
        except Exception as e:
            logger.error(f"خطأ في تحميل الأنماط: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_learning_level(self, level: int):
        """تعيين مستوى التعلم"""
        self.learning_level = level
        logger.info(f"⚙️ مستوى التعلم: {level}")
    
    def set_learning_type(self, learning_type: str):
        """تعيين نوع التعلم"""
        self.learning_type = learning_type
        logger.info(f"📚 نوع التعلم: {learning_type}")
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """إحصائيات التعلم"""
        return {
            "learning_level": self.learning_level,
            "learning_type": self.learning_type,
            "total_experiences": self.learning_stats["total_experiences"],
            "patterns_discovered": self.learning_stats["patterns_discovered"],
            "schemas_formed": self.learning_stats["schemas_formed"],
            "associations_formed": self.learning_stats["associations_formed"],
            "active_patterns": len(self.patterns),
            "active_schemas": len(self.schemas)
        }
    
    def get_recent_experiences(self, limit: int = 20) -> List[Dict]:
        """آخر التجارب"""
        return [
            {
                "id": e.id[:16],
                "timestamp": e.timestamp,
                "outcome": e.outcome,
                "importance": e.importance,
                "feedback": e.feedback
            }
            for e in self.experiences[-limit:]
        ]
    
    def get_patterns(self) -> List[Dict]:
        """الأنماط المتعلمة"""
        return [
            {
                "id": p.id[:16],
                "type": p.pattern_type,
                "confidence": p.confidence,
                "occurrences": p.occurrences
            }
            for p in self.patterns.values()
        ]
    
    def get_schemas(self) -> List[Dict]:
        """المخططات المعرفية"""
        return [
            {
                "id": s.id[:16],
                "name": s.name,
                "elements_count": len(s.elements),
                "activation": s.activation,
                "last_used": s.last_used
            }
            for s in self.schemas.values()
        ]
    
    def stop(self):
        """إيقاف نظام التعلم"""
        self._active = False
        self._save_state()
        self._save_patterns()
        logger.info("🛑 إيقاف نظام التعلم التكيفي")


# ============================================================
# الـ Singleton
# ============================================================

_learning_instance: Optional[AdaptiveLearning] = None
_learning_lock = threading.Lock()


def get_learning() -> AdaptiveLearning:
    """الحصول على النسخة الوحيدة من نظام التعلم التكيفي"""
    global _learning_instance
    if _learning_instance is None:
        with _learning_lock:
            if _learning_instance is None:
                _learning_instance = AdaptiveLearning()
    return _learning_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧠 نظام التعلم التكيفي - النمو المعرفي عبر الخبرة")
    print("=" * 70 + "\n")
    
    learning = get_learning()
    
    # 1) تسجيل تجارب
    print("📝 تسجيل تجارب تعلم...")
    for i in range(5):
        exp_id = learning.record_experience(
            input_data=f"سؤال {i}",
            output_data=f"إجابة {i}",
            context={"topic": "test"},
            importance=0.5 + i * 0.1,
            outcome="success" if i % 2 == 0 else "failure"
        )
        print(f"   تجربة {i+1}: {exp_id[:16]}...")
    
    # 2) إحصائيات التعلم
    print("\n📊 إحصائيات التعلم:")
    stats = learning.get_learning_stats()
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            print(f"   {key}: {value}")
    
    # 3) الأنماط المكتشفة
    print("\n🔍 الأنماط المتعلمة:")
    patterns = learning.get_patterns()
    for p in patterns[:5]:
        print(f"   {p['type']}: {p['confidence']:.1%} ({p['occurrences']} مرات)")
    
    # 4) المخططات المعرفية
    print("\n📐 المخططات المعرفية:")
    schemas = learning.get_schemas()
    for s in schemas[:5]:
        print(f"   {s['name']}: {s['elements_count']} عنصر, تنشيط: {s['activation']:.1%}")
    
    # 5) توليد معرفة جديدة
    print("\n✨ توليد معرفة جديدة:")
    generated = learning.generate_new_knowledge("learning", depth=3)
    print(f"   مفاهيم جديدة: {len(generated['new_concepts'])}")
    print(f"   ارتباطات جديدة: {len(generated['new_associations'])}")
    print(f"   الثقة: {generated['confidence']:.1%}")
    
    # 6) تجارب حديثة
    print("\n🕒 آخر التجارب:")
    experiences = learning.get_recent_experiences(5)
    for exp in experiences:
        print(f"   {exp['outcome']}: أهمية {exp['importance']:.1%}")
    
    print("\n" + "=" * 70)
    print("✅ نظام التعلم التكيفي جاهز - النمو المعرفي عبر الخبرة")
    print("=" * 70)
