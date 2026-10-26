# backend/memory/biological/plasticity.py
# 🧠 اللدونة العصبية - إعادة تشكيل الذات، المرونة المعرفية
# الإصدار: 3.0.0 - يتغير ليتكيف، يتكيف لينمو

"""
نظام اللدونة العصبية للذاكرة السيادية.

الفلسفة:
- الدماغ يتغير، والذاكرة السيادية يجب أن تتغير أيضاً
- اللدونة هي قدرة النظام على إعادة تشكيل نفسه
- المرونة تأتي من القدرة على تكوين روابط جديدة بسرعة
- القوة تأتي من القدرة على التخلص من الروابط الضعيفة
- التخصص يأتي من تعزيز المسارات المستخدمة بكثرة

هذا ليس تحديث أوزان. هذه هي المرونة العصبية الحقيقية.
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
# الثوابت وإعدادات اللدونة
# ============================================================

PLASTICITY_DIR = DATA_DIR / "plasticity"
PLASTICITY_LOG = PLASTICITY_DIR / "plasticity_log.jsonl"
PLASTICITY_STATE_FILE = PLASTICITY_DIR / "plasticity_state.json"
PLASTICITY_SYNAPSES_FILE = PLASTICITY_DIR / "synapses.json"
PLASTICITY_NETWORKS_DIR = PLASTICITY_DIR / "networks"

for d in [PLASTICITY_DIR, PLASTICITY_NETWORKS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات اللدونة
PLASTICITY_LEVEL_NONE = 0           # لا لدونة
PLASTICITY_LEVEL_LOW = 1            # لدونة منخفضة (تغييرات طفيفة)
PLASTICITY_LEVEL_MODERATE = 2       # لدونة متوسطة
PLASTICITY_LEVEL_HIGH = 3           # لدونة عالية
PLASTICITY_LEVEL_EXTREME = 4        # لدونة شديدة (إعادة تشكيل جذرية)

# آليات اللدونة
MECHANISM_LTP = "ltp"               # تقوية طويلة المدى
MECHANISM_LTD = "ltd"               # إضعاف طويل المدى
MECHANISM_SPROUTING = "sprouting"   # تشعب عصبي (روابط جديدة)
MECHANISM_PRUNING = "pruning"       # تقليم عصبي (إزالة روابط)
MECHANISM_REWIRING = "rewiring"     # إعادة توصيل
MECHANISM_NEUROGENESIS = "neurogenesis" # تكوين خلايا عصبية جديدة (مفاهيم جديدة)
MECHANISM_SYNAPTIC_TAGGING = "synaptic_tagging" # توسيم مشبكي


@dataclass
class Synapse:
    """مشبك عصبي - رابط بين مفهومين"""
    id: str
    source: str
    target: str
    weight: float          # قوة الاتصال (0-1)
    plasticity: float      # قابلية التغيير (0-1)
    created_at: float
    last_activated: float
    activation_count: int
    tags: List[str]        # علامات مشبكية
    strength_history: List[float]  # سجل القوة


@dataclass
class NeuralNetwork:
    """شبكة عصبية - مجموعة من المفاهيم والروابط"""
    id: str
    name: str
    neurons: List[str]     # المفاهيم
    synapses: List[str]    # المعرفات المشبكية
    activation: float      # مستوى التنشيط الحالي
    created_at: float
    last_modified: float


@dataclass
class PlasticityEvent:
    """حدث لدونة"""
    id: str
    mechanism: str
    target: str
    delta: float
    timestamp: float
    success: bool
    description: str


# ============================================================
# نظام اللدونة العصبية
# ============================================================

class NeuralPlasticity:
    """
    نظام اللدونة العصبية - إعادة تشكيل الذات، المرونة المعرفية.
    
    المبادئ:
    1. الخلايا التي تشتغل معاً ترتبط معاً (Hebbian learning)
    2. استخدمها أو تفقدها (use it or lose it)
    3. المرونة تأتي من التغيير
    4. التخصص يأتي من التقوية
    5. الإبداع يأتي من إعادة التوصيل
    """
    
    def __init__(self):
        self.core = get_core()
        self.store = get_store()
        self.dynamic = get_dynamic_memory()
        
        # حالة اللدونة
        self.plasticity_level = PLASTICITY_LEVEL_MODERATE
        self.synapses: Dict[str, Synapse] = {}
        self.networks: Dict[str, NeuralNetwork] = {}
        self.plasticity_events: List[PlasticityEvent] = []
        
        # إحصائيات اللدونة
        self.plasticity_stats = {
            "total_synapses": 0,
            "ltp_events": 0,
            "ltd_events": 0,
            "sprouting_events": 0,
            "pruning_events": 0,
            "rewiring_events": 0,
            "neurogenesis_events": 0
        }
        
        # خلفيات اللدونة
        self._active = True
        self._ltp_loop = threads.start_managed(self._continuous_ltp, owner=self)
        
        self._pruning_loop = threads.start_managed(self._continuous_pruning, owner=self)
        
        self._rewiring_loop = threads.start_managed(self._continuous_rewiring, owner=self)
        
        self._neurogenesis_loop = threads.start_managed(self._continuous_neurogenesis, owner=self)
        
        # تحميل الحالة
        self._load_state()
        self._load_synapses()
        
        logger.info("🧠 نظام اللدونة العصبية جاهز - إعادة تشكيل الذات، المرونة المعرفية")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لنظام اللدونة العصبية
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لنظام اللدونة العصبية.
        
        يمسح:
        - جميع المشابك العصبية (synapses)
        - الشبكات العصبية (networks)
        - سجل أحداث اللدونة (plasticity events)
        - إحصائيات اللدونة
        """
        logger.info("🔄 إعادة تهيئة نظام اللدونة العصبية...")
        
        # مسح جميع المشابك العصبية
        self.synapses.clear()
        
        # مسح الشبكات العصبية
        self.networks.clear()
        
        # مسح سجل أحداث اللدونة
        self.plasticity_events.clear()
        
        # إعادة تعيين إحصائيات اللدونة
        self.plasticity_stats = {
            "total_synapses": 0,
            "ltp_events": 0,
            "ltd_events": 0,
            "sprouting_events": 0,
            "pruning_events": 0,
            "rewiring_events": 0,
            "neurogenesis_events": 0
        }
        
        # إعادة تعيين مستوى اللدونة
        self.plasticity_level = PLASTICITY_LEVEL_MODERATE
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="biological::plasticity_reset",
            payload={
                "timestamp": time.time(),
                "status": "plasticity_system_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة نظام اللدونة العصبية اكتملت - شبكة عصبية جديدة")
    
    # ============================================================
    # المستوى 1: التقوية طويلة المدى (LTP - Long Term Potentiation)
    # ============================================================
    
    def long_term_potentiation(self, source: str, target: str, 
                               intensity: float = 0.1) -> bool:
        """
        تقوية طويلة المدى - تعزيز قوة الارتباط بين مفهومين.
        
        Hebbian learning: الخلايا التي تشتغل معاً ترتبط معاً.
        """
        # البحث عن المشبك الموجود
        synapse = self._find_synapse(source, target)
        
        if synapse:
            # تقوية المشبك الموجود
            old_weight = synapse.weight
            delta = intensity * (1 - synapse.weight) * synapse.plasticity
            synapse.weight = min(1.0, synapse.weight + delta)
            synapse.last_activated = time.time()
            synapse.activation_count += 1
            synapse.strength_history.append(synapse.weight)
            if len(synapse.strength_history) > 10:
                synapse.strength_history = synapse.strength_history[-10:]
            
            self.plasticity_stats["ltp_events"] += 1
            
            logger.debug(f"⚡ LTP: {source} → {target} [{old_weight:.2f} → {synapse.weight:.2f}]")
        else:
            # إنشاء مشبك جديد
            return self.synaptic_sprouting(source, target, initial_weight=0.5 + intensity)
        
        # تحديث الارتباط في التخزين
        self._update_association_in_store(source, target, synapse.weight)
        
        # تسجيل الحدث
        event = PlasticityEvent(
            id=f"ltp_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            mechanism=MECHANISM_LTP,
            target=f"{source}→{target}",
            delta=synapse.weight - (old_weight if synapse else 0),
            timestamp=time.time(),
            success=True,
            description=f"تقوية الرابط بين {source} و {target}"
        )
        self.plasticity_events.append(event)
        
        return True
    
    def _find_synapse(self, source: str, target: str) -> Optional[Synapse]:
        """البحث عن مشبك بين مفهومين"""
        for synapse in self.synapses.values():
            if (synapse.source == source and synapse.target == target) or \
               (synapse.source == target and synapse.target == source):
                return synapse
        return None
    
    def _continuous_ltp(self):
        """تطبيق LTP مستمر على المسارات المستخدمة بكثرة"""
        while self._active:
            try:
                if self.plasticity_level >= PLASTICITY_LEVEL_LOW:
                    # تحليل أنماط الاستخدام من السجل
                    usage_patterns = self._analyze_usage_patterns()
                    
                    for (source, target), count in usage_patterns.items():
                        if count > 5:
                            intensity = min(0.5, count / 20)
                            self.long_term_potentiation(source, target, intensity)
                
                threads.interruptible_sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في LTP المستمر: {e}")
                threads.interruptible_sleep(300)
    
    def _analyze_usage_patterns(self) -> Dict[Tuple[str, str], int]:
        """تحليل أنماط الاستخدام من السجل"""
        patterns = defaultdict(int)
        
        for event in self.core.iterate_events(reverse=True, limit=500):
            payload = self.core.get_payload(event)
            text = str(payload).lower()
            
            # البحث عن مفاهيم متزامنة
            semantic_items = self.store.query("semantic", min_importance=0.0, limit=50)
            concepts = [item.get("concept", "").lower() for item in semantic_items]
            
            for i in range(len(concepts)):
                for j in range(i+1, len(concepts)):
                    if concepts[i] and concepts[j] and concepts[i] in text and concepts[j] in text:
                        patterns[(concepts[i], concepts[j])] += 1
        
        return patterns
    
    # ============================================================
    # المستوى 2: الإضعاف طويل المدى (LTD - Long Term Depression)
    # ============================================================
    
    def long_term_depression(self, source: str, target: str, 
                             intensity: float = 0.05) -> bool:
        """
        إضعاف طويل المدى - تقليل قوة الارتباط بين مفهومين.
        
        "استخدمها أو تفقدها" - الروابط غير المستخدمة تضعف.
        """
        synapse = self._find_synapse(source, target)
        
        if not synapse:
            return False
        
        old_weight = synapse.weight
        delta = intensity * synapse.weight * synapse.plasticity
        synapse.weight = max(0.0, synapse.weight - delta)
        synapse.last_activated = time.time()
        synapse.strength_history.append(synapse.weight)
        
        self.plasticity_stats["ltd_events"] += 1
        
        # تحديث الارتباط في التخزين
        if synapse.weight < 0.05:
            # رابط ضعيف جداً - يمكن إزالته
            self.synaptic_pruning(synapse.id)
        else:
            self._update_association_in_store(source, target, synapse.weight)
        
        logger.debug(f"📉 LTD: {source} → {target} [{old_weight:.2f} → {synapse.weight:.2f}]")
        
        event = PlasticityEvent(
            id=f"ltd_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            mechanism=MECHANISM_LTD,
            target=f"{source}→{target}",
            delta=synapse.weight - old_weight,
            timestamp=time.time(),
            success=True,
            description=f"إضعاف الرابط بين {source} و {target}"
        )
        self.plasticity_events.append(event)
        
        return True
    
    # ============================================================
    # المستوى 3: التشعب العصبي (Synaptic Sprouting)
    # ============================================================
    
    def synaptic_sprouting(self, source: str, target: str, 
                           initial_weight: float = 0.5) -> bool:
        """
        تشعب عصبي - إنشاء روابط جديدة بين المفاهيم.
        
        روابط جديدة = قدرات جديدة.
        """
        # التحقق من وجود الرابط مسبقاً
        if self._find_synapse(source, target):
            return False
        
        synapse_id = f"syn_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        synapse = Synapse(
            id=synapse_id,
            source=source,
            target=target,
            weight=initial_weight,
            plasticity=0.7,  # قابلية عالية للتغيير
            created_at=time.time(),
            last_activated=time.time(),
            activation_count=1,
            tags=[],
            strength_history=[initial_weight]
        )
        
        self.synapses[synapse_id] = synapse
        self.plasticity_stats["sprouting_events"] += 1
        self.plasticity_stats["total_synapses"] += 1
        
        # إنشاء الارتباط في التخزين
        self.store.save_associative(
            source=source,
            target=target,
            relation_type="synaptic",
            strength=initial_weight
        )
        
        logger.info(f"🌱 تشعب عصبي: {source} → {target} (قوة: {initial_weight:.2f})")
        
        event = PlasticityEvent(
            id=f"sprout_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            mechanism=MECHANISM_SPROUTING,
            target=f"{source}→{target}",
            delta=initial_weight,
            timestamp=time.time(),
            success=True,
            description=f"إنشاء رابط جديد بين {source} و {target}"
        )
        self.plasticity_events.append(event)
        
        return True
    
    # ============================================================
    # المستوى 4: التقليم العصبي (Synaptic Pruning)
    # ============================================================
    
    def synaptic_pruning(self, synapse_id: str) -> bool:
        """
        تقليم عصبي - إزالة الروابط الضعيفة أو غير المستخدمة.
        
        التقليم يزيد الكفاءة ويقلل الضوضاء.
        """
        if synapse_id not in self.synapses:
            return False
        
        synapse = self.synapses[synapse_id]
        
        # تسجيل الإزالة
        logger.info(f"✂️ تقليم عصبي: {synapse.source} → {synapse.target} (قوة: {synapse.weight:.2f})")
        
        # إزالة من الذاكرة المحلية
        del self.synapses[synapse_id]
        self.plasticity_stats["pruning_events"] += 1
        
        # إزالة من التخزين (بوضع علامة)
        assoc_items = self.store.query("associative", limit=500)
        for item in assoc_items:
            if (item.get("source") == synapse.source and item.get("target") == synapse.target) or \
               (item.get("source") == synapse.target and item.get("target") == synapse.source):
                # وضع علامة للإزالة
                item["_metadata"] = item.get("_metadata", {})
                item["_metadata"]["pruned"] = True
                item["_metadata"]["pruned_at"] = time.time()
                item["weight"] = 0.0
                break
        
        event = PlasticityEvent(
            id=f"prune_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            mechanism=MECHANISM_PRUNING,
            target=f"{synapse.source}→{synapse.target}",
            delta=-synapse.weight,
            timestamp=time.time(),
            success=True,
            description=f"إزالة الرابط بين {synapse.source} و {synapse.target}"
        )
        self.plasticity_events.append(event)
        
        return True
    
    def _continuous_pruning(self):
        """تقليم مستمر للروابط الضعيفة"""
        while self._active:
            try:
                if self.plasticity_level >= PLASTICITY_LEVEL_MODERATE:
                    # إزالة الروابط الأضعف
                    weak_synapses = [(sid, s) for sid, s in self.synapses.items() 
                                    if s.weight < 0.1 and s.activation_count < 3]
                    
                    # إزالة نسبة من الروابط الضعيفة
                    to_prune = weak_synapses[:max(1, len(weak_synapses) // 10)]
                    for sid, _ in to_prune:
                        self.synaptic_pruning(sid)
                
                threads.interruptible_sleep(600)  # كل 10 دقائق
            except Exception as e:
                logger.error(f"خطأ في التقليم المستمر: {e}")
                threads.interruptible_sleep(600)
    
    # ============================================================
    # المستوى 5: إعادة التوصيل (Rewiring)
    # ============================================================
    
    def rewiring(self, source: str, target: str, new_target: str) -> bool:
        """
        إعادة توصيل عصبي - تغيير وجهة رابط.
        
        إعادة التوصيل تخلق مسارات معرفية جديدة.
        """
        synapse = self._find_synapse(source, target)
        
        if not synapse:
            return False
        
        old_target = synapse.target
        
        # إنشاء رابط جديد
        self.synaptic_sprouting(source, new_target, initial_weight=synapse.weight * 0.8)
        
        # إضعاف الرابط القديم
        self.long_term_depression(source, old_target, intensity=0.3)
        
        self.plasticity_stats["rewiring_events"] += 1
        
        logger.info(f"🔄 إعادة توصيل: {source} → {old_target} → {new_target}")
        
        event = PlasticityEvent(
            id=f"rewire_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            mechanism=MECHANISM_REWIRING,
            target=f"{source}→{old_target}→{new_target}",
            delta=0,
            timestamp=time.time(),
            success=True,
            description=f"إعادة توجيه الرابط من {old_target} إلى {new_target}"
        )
        self.plasticity_events.append(event)
        
        return True
    
    def _continuous_rewiring(self):
        """إعادة توصيل مستمرة للمسارات غير المثلى"""
        while self._active:
            try:
                if self.plasticity_level >= PLASTICITY_LEVEL_HIGH:
                    # البحث عن مسارات غير مثلى
                    for synapse in list(self.synapses.values())[:20]:
                        if synapse.weight < 0.3 and synapse.activation_count > 10:
                            # رابط ضعيف لكن مستخدم - يحتاج إعادة توصيل
                            related = self._find_related_concepts(synapse.source)
                            if related:
                                new_target = random.choice(related)
                                self.rewiring(synapse.source, synapse.target, new_target)
                
                threads.interruptible_sleep(1800)  # كل 30 دقيقة
            except Exception as e:
                logger.error(f"خطأ في إعادة التوصيل: {e}")
                threads.interruptible_sleep(1800)
    
    def _find_related_concepts(self, concept: str) -> List[str]:
        """العثور على مفاهيم مرتبطة بمفهوم"""
        related = []
        for synapse in self.synapses.values():
            if synapse.source == concept:
                related.append(synapse.target)
            elif synapse.target == concept:
                related.append(synapse.source)
        return related
    
    # ============================================================
    # المستوى 6: تكوين خلايا عصبية جديدة (Neurogenesis)
    # ============================================================
    
    def neurogenesis(self, concept_name: str, definition: str) -> bool:
        """
        تكوين خلية عصبية جديدة - إنشاء مفهوم جديد.
        
        تكوين مفاهيم جديدة = توسيع القدرات المعرفية.
        """
        # التحقق من وجود المفهوم
        semantic_items = self.store.query("semantic", search_text=concept_name, limit=5)
        for item in semantic_items:
            if item.get("concept") == concept_name:
                return False  # المفهوم موجود مسبقاً
        
        # إنشاء المفهوم
        self.store.save_semantic(
            concept=concept_name,
            definition=definition,
            confidence=0.6,
            related_concepts={}
        )
        
        self.plasticity_stats["neurogenesis_events"] += 1
        
        logger.info(f"🧠 تكوين خلية عصبية جديدة: {concept_name}")
        
        event = PlasticityEvent(
            id=f"neuro_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            mechanism=MECHANISM_NEUROGENESIS,
            target=concept_name,
            delta=0,
            timestamp=time.time(),
            success=True,
            description=f"إنشاء مفهوم جديد: {concept_name}"
        )
        self.plasticity_events.append(event)
        
        return True
    
    def _continuous_neurogenesis(self):
        """تكوين خلايا عصبية جديدة بشكل مستمر"""
        while self._active:
            try:
                if self.plasticity_level >= PLASTICITY_LEVEL_EXTREME:
                    # استخراج مفاهيم محتملة من النصوص
                    candidate_concepts = self._extract_candidate_concepts()
                    
                    for concept in candidate_concepts[:3]:
                        self.neurogenesis(concept, f"مفهوم مستخلص تلقائياً: {concept}")
                
                threads.interruptible_sleep(3600)  # كل ساعة
            except Exception as e:
                logger.error(f"خطأ في تكوين الخلايا: {e}")
                threads.interruptible_sleep(3600)
    
    def _extract_candidate_concepts(self) -> List[str]:
        """استخراج مفاهيم مرشحة من الأحداث الأخيرة"""
        candidates = set()
        
        for event in self.core.iterate_events(reverse=True, limit=200):
            payload = self.core.get_payload(event)
            text = str(payload).lower()
            
            # استخراج كلمات طويلة وفريدة
            words = text.split()
            for word in words:
                if len(word) > 6 and word.isalpha() and word not in ["المستخدم", "النظام", "الذاكرة", "السيادي"]:
                    candidates.add(word[:30])
        
        # استبعاد المفاهيم الموجودة
        semantic_items = self.store.query("semantic", min_importance=0.0, limit=200)
        existing = set(item.get("concept", "").lower() for item in semantic_items)
        
        new_candidates = [c for c in candidates if c not in existing]
        
        return new_candidates[:10]
    
    # ============================================================
    # المستوى 7: إعادة تشكيل الشبكة (Network Reshaping)
    # ============================================================
    
    def reshape_network(self) -> Dict[str, Any]:
        """
        إعادة تشكيل الشبكة العصبية بالكامل.
        
        أعلى مستوى من اللدونة - إعادة هيكلة جذرية.
        """
        result = {
            "synapses_before": len(self.synapses),
            "synapses_after": 0,
            "pruned": 0,
            "sprouted": 0,
            "rewired": 0
        }
        
        # 1) تقليم الروابط الضعيفة جداً
        to_prune = [sid for sid, s in self.synapses.items() if s.weight < 0.05]
        for sid in to_prune:
            self.synaptic_pruning(sid)
            result["pruned"] += 1
        
        # 2) تعزيز الروابط القوية
        for synapse in self.synapses.values():
            if synapse.weight > 0.7:
                self.long_term_potentiation(synapse.source, synapse.target, intensity=0.05)
        
        # 3) إنشاء روابط جديدة بين المفاهيم المتقاربة
        semantic_items = self.store.query("semantic", min_importance=0.0, limit=100)
        concepts = [item.get("concept", "") for item in semantic_items if item.get("concept")]
        
        for i in range(len(concepts)):
            for j in range(i+1, min(i+5, len(concepts))):
                if not self._find_synapse(concepts[i], concepts[j]):
                    self.synaptic_sprouting(concepts[i], concepts[j], initial_weight=0.3)
                    result["sprouted"] += 1
        
        result["synapses_after"] = len(self.synapses)
        
        logger.info(f"🔄 إعادة تشكيل الشبكة: {result['synapses_before']} → {result['synapses_after']}")
        
        return result
    
    # ============================================================
    # دورة اللدونة الكاملة
    # ============================================================
    
    def plasticity_cycle(self) -> Dict[str, Any]:
        """
        دورة لدونة كاملة - تطبيق جميع آليات اللدونة.
        """
        logger.info("🔄 بدء دورة اللدونة الكاملة")
        
        results = {
            "ltp": 0,
            "ltd": 0,
            "sprouting": 0,
            "pruning": 0,
            "rewiring": 0,
            "neurogenesis": 0,
            "reshaping": None
        }
        
        # 1) تعزيز المسارات المستخدمة
        usage_patterns = self._analyze_usage_patterns()
        for (source, target), count in usage_patterns.items():
            if count > 3:
                self.long_term_potentiation(source, target, intensity=min(0.3, count / 30))
                results["ltp"] += 1
        
        # 2) إضعاف المسارات غير المستخدمة
        for synapse in self.synapses.values():
            if synapse.last_activated < time.time() - 86400:  # أكثر من يوم
                self.long_term_depression(synapse.source, synapse.target, intensity=0.1)
                results["ltd"] += 1
        
        # 3) تشعب عشوائي
        if len(self.synapses) < 100:
            semantic_items = self.store.query("semantic", min_importance=0.0, limit=50)
            concepts = [item.get("concept", "") for item in semantic_items if item.get("concept")]
            for i in range(min(5, len(concepts)-1)):
                self.synaptic_sprouting(concepts[i], concepts[i+1], initial_weight=0.4)
                results["sprouting"] += 1
        
        # 4) تقليم
        weak_synapses = sum(1 for s in self.synapses.values() if s.weight < 0.1)
        if weak_synapses > 10:
            for synapse in list(self.synapses.values())[:weak_synapses//2]:
                self.synaptic_pruning(synapse.id)
                results["pruning"] += 1
        
        # 5) إعادة توصيل
        if random.random() < 0.3:
            for synapse in list(self.synapses.values())[:5]:
                related = self._find_related_concepts(synapse.source)
                if related and len(related) > 1:
                    new_target = random.choice([r for r in related if r != synapse.target])
                    if new_target:
                        self.rewiring(synapse.source, synapse.target, new_target)
                        results["rewiring"] += 1
        
        # 6) تكوين خلايا جديدة
        if self.plasticity_level >= PLASTICITY_LEVEL_HIGH:
            candidates = self._extract_candidate_concepts()
            for concept in candidates[:3]:
                if self.neurogenesis(concept, f"مستخلص من دورة اللدونة: {concept}"):
                    results["neurogenesis"] += 1
        
        # 7) إعادة تشكيل الشبكة (كل 5 دورات)
        if len(self.plasticity_events) % 50 == 0:
            results["reshaping"] = self.reshape_network()
        
        self.core.append_event(
            event_type="plasticity::cycle_completed",
            payload={
                "ltp": results["ltp"],
                "ltd": results["ltd"],
                "sprouting": results["sprouting"],
                "pruning": results["pruning"],
                "neurogenesis": results["neurogenesis"],
                "total_synapses": len(self.synapses)
            }
        )
        
        logger.info(f"✅ دورة اللدونة اكتملت: {results['ltp']} LTP, {results['ltd']} LTD, "
                   f"{results['sprouting']} تشعب, {results['pruning']} تقليم")
        
        return results
    
    # ============================================================
    # الأدوات المساعدة
    # ============================================================
    
    def _update_association_in_store(self, source: str, target: str, weight: float):
        """تحديث الارتباط في التخزين"""
        assoc_items = self.store.query("associative", limit=500)
        for item in assoc_items:
            if (item.get("source") == source and item.get("target") == target) or \
               (item.get("source") == target and item.get("target") == source):
                item["weight"] = weight
                item["_importance"] = weight
                break
    
    def _save_state(self):
        """حفظ حالة اللدونة"""
        try:
            state = {
                "plasticity_level": self.plasticity_level,
                "plasticity_stats": self.plasticity_stats,
                "synapses_count": len(self.synapses),
                "networks_count": len(self.networks),
                "events_count": len(self.plasticity_events),
                "saved_at": time.time()
            }
            with open(PLASTICITY_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة اللدونة: {e}")
    
    def _load_state(self):
        """تحميل حالة اللدونة"""
        try:
            if PLASTICITY_STATE_FILE.exists():
                with open(PLASTICITY_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.plasticity_level = state.get("plasticity_level", PLASTICITY_LEVEL_MODERATE)
                    self.plasticity_stats = state.get("plasticity_stats", self.plasticity_stats)
                logger.info("📂 تم تحميل حالة نظام اللدونة")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة اللدونة: {e}")
    
    def _save_synapses(self):
        """حفظ المشابك العصبية"""
        try:
            synapses_data = {
                "synapses": [
                    {
                        "id": s.id,
                        "source": s.source,
                        "target": s.target,
                        "weight": s.weight,
                        "plasticity": s.plasticity,
                        "created_at": s.created_at,
                        "last_activated": s.last_activated,
                        "activation_count": s.activation_count,
                        "tags": s.tags,
                        "strength_history": s.strength_history
                    }
                    for s in self.synapses.values()
                ],
                "saved_at": time.time()
            }
            with open(PLASTICITY_SYNAPSES_FILE, 'w', encoding='utf-8') as f:
                json.dump(synapses_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ المشابك: {e}")
    
    def _load_synapses(self):
        """تحميل المشابك العصبية"""
        try:
            if PLASTICITY_SYNAPSES_FILE.exists():
                with open(PLASTICITY_SYNAPSES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for s_data in data.get("synapses", []):
                        synapse = Synapse(**s_data)
                        self.synapses[synapse.id] = synapse
                logger.info(f"📂 تم تحميل {len(self.synapses)} مشبكاً")
        except Exception as e:
            logger.error(f"خطأ في تحميل المشابك: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_plasticity_level(self, level: int):
        """تعيين مستوى اللدونة"""
        self.plasticity_level = level
        logger.info(f"⚙️ مستوى اللدونة: {level}")
    
    def get_plasticity_stats(self) -> Dict[str, Any]:
        """إحصائيات اللدونة"""
        return {
            "plasticity_level": self.plasticity_level,
            "total_synapses": len(self.synapses),
            "avg_synapse_weight": sum(s.weight for s in self.synapses.values()) / len(self.synapses) if self.synapses else 0,
            "ltp_events": self.plasticity_stats["ltp_events"],
            "ltd_events": self.plasticity_stats["ltd_events"],
            "sprouting_events": self.plasticity_stats["sprouting_events"],
            "pruning_events": self.plasticity_stats["pruning_events"],
            "rewiring_events": self.plasticity_stats["rewiring_events"],
            "neurogenesis_events": self.plasticity_stats["neurogenesis_events"],
            "total_plasticity_events": len(self.plasticity_events)
        }
    
    def get_synapses(self, limit: int = 50) -> List[Dict]:
        """المشابك العصبية"""
        sorted_synapses = sorted(self.synapses.values(), key=lambda x: x.weight, reverse=True)
        return [
            {
                "id": s.id[:16],
                "source": s.source[:30],
                "target": s.target[:30],
                "weight": s.weight,
                "activation_count": s.activation_count,
                "last_activated": s.last_activated
            }
            for s in sorted_synapses[:limit]
        ]
    
    def get_plasticity_events(self, limit: int = 20) -> List[Dict]:
        """أحداث اللدونة الأخيرة"""
        return [
            {
                "id": e.id[:16],
                "mechanism": e.mechanism,
                "target": e.target[:50],
                "delta": e.delta,
                "timestamp": e.timestamp,
                "success": e.success
            }
            for e in self.plasticity_events[-limit:]
        ]
    
    def stop(self):
        """إيقاف نظام اللدونة"""
        self._active = False
        self._save_state()
        self._save_synapses()
        logger.info("🛑 إيقاف نظام اللدونة العصبية")


# ============================================================
# الـ Singleton
# ============================================================

_plasticity_instance: Optional[NeuralPlasticity] = None
_plasticity_lock = threading.Lock()


def get_plasticity() -> NeuralPlasticity:
    """الحصول على النسخة الوحيدة من نظام اللدونة العصبية"""
    global _plasticity_instance
    if _plasticity_instance is None:
        with _plasticity_lock:
            if _plasticity_instance is None:
                _plasticity_instance = NeuralPlasticity()
    return _plasticity_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧠 نظام اللدونة العصبية - إعادة تشكيل الذات، المرونة المعرفية")
    print("=" * 70 + "\n")
    
    plasticity = get_plasticity()
    
    # 1) إنشاء مشابك جديدة
    print("🌱 إنشاء مشابك عصبية...")
    plasticity.synaptic_sprouting("الذكاء", "التعلم", initial_weight=0.7)
    plasticity.synaptic_sprouting("التعلم", "التكيف", initial_weight=0.6)
    plasticity.synaptic_sprouting("الذاكرة", "الاسترجاع", initial_weight=0.8)
    print(f"   إجمالي المشابك: {len(plasticity.synapses)}")
    
    # 2) LTP - تقوية
    print("\n⚡ تقوية الروابط (LTP)...")
    plasticity.long_term_potentiation("الذكاء", "التعلم", intensity=0.2)
    print(f"   قوة الرابط: {plasticity._find_synapse('الذكاء', 'التعلم').weight:.2f}")
    
    # 3) LTD - إضعاف
    print("\n📉 إضعاف الروابط (LTD)...")
    plasticity.long_term_depression("الذكاء", "التعلم", intensity=0.05)
    print(f"   قوة الرابط: {plasticity._find_synapse('الذكاء', 'التعلم').weight:.2f}")
    
    # 4) تكوين خلايا جديدة
    print("\n🧠 تكوين مفاهيم جديدة...")
    plasticity.neurogenesis("اللدونة العصبية", "قدرة النظام على إعادة تشكيل نفسه")
    print(f"   تم إنشاء مفهوم جديد")
    
    # 5) إعادة توصيل
    print("\n🔄 إعادة توصيل...")
    plasticity.rewiring("التعلم", "التكيف", "المرونة")
    
    # 6) دورة لدونة كاملة
    print("\n🔄 دورة لدونة كاملة...")
    results = plasticity.plasticity_cycle()
    print(f"   LTP: {results['ltp']}, LTD: {results['ltd']}")
    print(f"   تشعب: {results['sprouting']}, تقليم: {results['pruning']}")
    print(f"   خلايا جديدة: {results['neurogenesis']}")
    
    # 7) الإحصائيات
    print("\n📊 إحصائيات اللدونة:")
    stats = plasticity.get_plasticity_stats()
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            print(f"   {key}: {value}")
    
    # 8) أقوى المشابك
    print("\n🔗 أقوى المشابك:")
    synapses = plasticity.get_synapses(5)
    for s in synapses:
        print(f"   {s['source']} → {s['target']}: {s['weight']:.2f} (استخدام: {s['activation_count']})")
    
    print("\n" + "=" * 70)
    print("✅ نظام اللدونة العصبية جاهز - إعادة تشكيل الذات، المرونة المعرفية")
    print("=" * 70)
