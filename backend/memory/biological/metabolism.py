# backend/memory/biological/metabolism.py
# 🔥 الأيض المعرفي - حرق الضوضاء، توليد الطاقة الذهنية
# الإصدار: 3.0.0 - تحويل الفوضى إلى نظام، الضوضاء إلى إشارة

"""
نظام الأيض المعرفي للذاكرة السيادية.

الفلسفة:
- الذاكرة تحتاج إلى طاقة لتعمل
- الطاقة تأتي من حرق ما هو غير مفيد
- الضوضاء تحترق لتتحول إلى وضوح
- التكرار يحترق ليتحول إلى جوهر
- الارتباطات الضعيفة تحترق لتتحول إلى قوة

هذا ليس تنظيفاً. هذا هو الأيض - تحويل المادة إلى طاقة.
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
# الثوابت وإعدادات الأيض المعرفي
# ============================================================

METABOLISM_DIR = DATA_DIR / "metabolism"
METABOLISM_LOG = METABOLISM_DIR / "metabolism_log.jsonl"
METABOLISM_STATE_FILE = METABOLISM_DIR / "metabolism_state.json"
METABOLISM_ENERGY_FILE = METABOLISM_DIR / "energy_level.json"

for d in [METABOLISM_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات الأيض
METABOLISM_LEVEL_NONE = 0           # لا أيض
METABOLISM_LEVEL_LIGHT = 1          # أيض خفيف (تنظيف سطحي)
METABOLISM_LEVEL_MODERATE = 2       # أيض متوسط (تنظيف منتظم)
METABOLISM_LEVEL_INTENSE = 3        # أيض مكثف (تنظيف عميق)
METABOLISM_LEVEL_MAXIMUM = 4        # أقصى أيض (حرق كل شيء غير ضروري)

# أنواع الوقود المعرفي
FUEL_TYPE_NOISE = "noise"           # ضوضاء
FUEL_TYPE_REDUNDANCY = "redundancy" # تكرار
FUEL_TYPE_WEAK_LINKS = "weak_links" # روابط ضعيفة
FUEL_TYPE_LOW_VALUE = "low_value"   # قيمة منخفضة
FUEL_TYPE_OLD_MEMORY = "old_memory" # ذاكرة قديمة
FUEL_TYPE_CONFLICT = "conflict"     # تناقضات
FUEL_TYPE_ORPHAN = "orphan"         # يتيمة (بلا روابط)

# أنواع الطاقة المنتجة
ENERGY_TYPE_CLARITY = "clarity"        # وضوح
ENERGY_TYPE_SPEED = "speed"            # سرعة
ENERGY_TYPE_FOCUS = "focus"            # تركيز
ENERGY_TYPE_CREATIVITY = "creativity"  # إبداع
ENERGY_TYPE_COHERENCE = "coherence"    # تماسك
ENERGY_TYPE_ORDER = "order"            # نظام


@dataclass
class MetabolicCycle:
    """دورة أيضية"""
    id: str
    timestamp: float
    level: int
    fuel_consumed: Dict[str, int]
    energy_produced: Dict[str, float]
    duration: float
    efficiency: float


@dataclass
class EnergyReservoir:
    """خزان الطاقة المعرفية"""
    clarity: float = 0.0      # وضوح (0-100)
    speed: float = 0.0        # سرعة الاسترجاع
    focus: float = 0.0        # قوة التركيز
    creativity: float = 0.0   # قدرة الإبداع
    coherence: float = 0.0    # تماسك المعرفة
    order: float = 0.0        # مستوى التنظيم
    
    def total_energy(self) -> float:
        return sum([self.clarity, self.speed, self.focus, 
                   self.creativity, self.coherence, self.order])
    
    def to_dict(self) -> Dict:
        return {
            "clarity": self.clarity,
            "speed": self.speed,
            "focus": self.focus,
            "creativity": self.creativity,
            "coherence": self.coherence,
            "order": self.order,
            "total": self.total_energy()
        }


# ============================================================
# نظام الأيض المعرفي
# ============================================================

class CognitiveMetabolism:
    """
    نظام الأيض المعرفي - حرق الضوضاء، إنتاج الطاقة.
    
    المبادئ:
    1. الذاكرة تحتاج إلى طاقة لتعمل
    2. الطاقة تأتي من حرق ما هو غير مفيد
    3. الأيض المنتظم يمنع التسمم المعرفي
    4. الطاقة المنتجة تحسن جودة الذاكرة
    5. التوازن هو مفتاح الاستدامة
    """
    
    def __init__(self):
        self.core = get_core()
        self.store = get_store()
        self.dynamic = get_dynamic_memory()
        
        # حالة الأيض
        self.metabolism_level = METABOLISM_LEVEL_MODERATE
        self.energy = EnergyReservoir()
        self.cycles: List[MetabolicCycle] = []
        self.current_cycle: Optional[MetabolicCycle] = None
        
        # إحصائيات الوقود والطاقة
        self.total_fuel_consumed: Dict[str, int] = defaultdict(int)
        self.total_energy_produced: Dict[str, float] = defaultdict(float)
        
        # خلفيات الأيض
        self._active = True
        self._metabolic_loop = threads.start_managed(self._continuous_metabolism, owner=self)
        
        self._energy_monitor = threads.start_managed(self._energy_monitoring_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        self._load_energy()
        
        logger.info("🔥 نظام الأيض المعرفي جاهز - حرق الضوضاء، إنتاج الطاقة")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لنظام الأيض المعرفي
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لنظام الأيض المعرفي.
        
        يمسح:
        - خزان الطاقة (energy reservoir)
        - سجل الدورات الأيضية (metabolic cycles)
        - إحصائيات الوقود والطاقة
        """
        logger.info("🔄 إعادة تهيئة نظام الأيض المعرفي...")
        
        # إعادة تعيين خزان الطاقة
        self.energy = EnergyReservoir()
        
        # مسح سجل الدورات الأيضية
        self.cycles.clear()
        self.current_cycle = None
        
        # إعادة تعيين إحصائيات الوقود والطاقة
        self.total_fuel_consumed.clear()
        self.total_energy_produced.clear()
        
        # إعادة تعيين مستوى الأيض
        self.metabolism_level = METABOLISM_LEVEL_MODERATE
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="biological::metabolism_reset",
            payload={
                "timestamp": time.time(),
                "status": "metabolism_system_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة نظام الأيض المعرفي اكتملت - الطاقة أعيد ضبطها")
    
    # ============================================================
    # المستوى 1: تحديد الوقود المعرفي (Fuel Detection)
    # ============================================================
    
    def detect_noise(self) -> List[str]:
        """
        اكتشاف الضوضاء المعرفية - المعلومات عديمة القيمة.
        
        الضوضاء هي:
        - رسائل فارغة أو قصيرة جداً
        - تكرارات مملة
        - معلومات بدون سياق
        """
        noise_items = []
        
        # في الذاكرة الحسية
        for event in self.dynamic.sensory.get_latest(limit=100):
            payload = event.payload
            text = str(payload)
            if len(text) < 10:  # قصيرة جداً
                noise_items.append(f"sensory_{event.id}")
            elif text.count(' ') < 2:  # كلمتان أو أقل
                noise_items.append(f"sensory_{event.id}")
        
        # في الذاكرة العاملة
        for user_id, items in self.dynamic.working._by_user.items():
            for item in items:
                if len(item.content) < 5:
                    noise_items.append(f"working_{item.id}")
        
        logger.debug(f"📡 ضوضاء مكتشفة: {len(noise_items)} عنصر")
        return noise_items
    
    def detect_redundancy(self) -> List[Tuple[str, str]]:
        """
        اكتشاف التكرار المعرفي - نفس المعلومات في أماكن متعددة.
        
        التكرار يستهلك طاقة التخزين دون فائدة.
        """
        redundancies = []
        
        # في الذاكرة الدلالية
        concepts = {}
        semantic_items = self.store.query("semantic", min_importance=0.0, limit=500)
        for item in semantic_items:
            concept = item.get("concept", "")
            if concept:
                # تجزئة المفهوم للمقارنة
                fp = hashlib.md5(concept.lower().encode()).hexdigest()[:8]
                if fp in concepts:
                    redundancies.append((concepts[fp], concept))
                else:
                    concepts[fp] = concept
        
        # في الذاكرة الترابطية
        associations = {}
        assoc_items = self.store.query("associative", min_importance=0.0, limit=500)
        for item in assoc_items:
            a = item.get("source", "")
            b = item.get("target", "")
            pair = f"{a}<->{b}"
            fp = hashlib.md5(pair.encode()).hexdigest()[:8]
            if fp in associations:
                redundancies.append((associations[fp], pair))
            else:
                associations[fp] = pair
        
        logger.debug(f"🔄 تكرار مكتشف: {len(redundancies)} زوج")
        return redundancies
    
    def detect_weak_links(self) -> List[Tuple[str, str, float]]:
        """
        اكتشاف الروابط الضعيفة - علاقات ترابطية منخفضة القوة.
        
        الروابط الضعيفة تستهلك طاقة دون فائدة.
        """
        weak_links = []
        
        assoc_items = self.store.query("associative", min_importance=0.0, limit=500)
        for item in assoc_items:
            weight = item.get("weight", 0.5)
            if weight < 0.2:  # أقل من 20% قوة
                weak_links.append((
                    item.get("source", ""),
                    item.get("target", ""),
                    weight
                ))
        
        logger.debug(f"🔗 روابط ضعيفة: {len(weak_links)} رابط")
        return weak_links
    
    def detect_conflicts(self) -> List[Tuple[str, str, str]]:
        """
        اكتشاف التناقضات المعرفية - معلومات متعارضة.
        
        التناقضات تسبب ارتباكاً في النظام.
        """
        conflicts = []
        
        semantic_items = self.store.query("semantic", min_importance=0.0, limit=300)
        concepts = {item.get("concept", ""): item for item in semantic_items if item.get("concept")}
        
        # البحث عن مفاهيم متعارضة (مثل "حار" و"بارد")
        opposites = [("حار", "بارد"), ("كبير", "صغير"), ("سريع", "بطيء"), 
                     ("ذكي", "غبي"), ("جيد", "سيء"), ("قوي", "ضعيف")]
        
        for a, b in opposites:
            if a in concepts and b in concepts:
                conflicts.append((a, b, "opposite"))
        
        logger.debug(f"⚡ تناقضات: {len(conflicts)} زوج")
        return conflicts
    
    # ============================================================
    # المستوى 2: حرق الوقود (Fuel Combustion)
    # ============================================================
    
    def burn_noise(self, intensity: float = 1.0) -> Dict[str, Any]:
        """
        حرق الضوضاء - إزالة المعلومات عديمة القيمة.
        
        الضوضاء تحترق → تتحول إلى وضوح.
        """
        noise_items = self.detect_noise()
        removed = 0
        
        for noise_id in noise_items:
            if noise_id.startswith("sensory_"):
                # حرق من الذاكرة الحسية
                for event in list(self.dynamic.sensory._events):
                    if f"sensory_{event.id}" == noise_id:
                        self.dynamic.sensory._events.remove(event)
                        removed += 1
                        break
            
            elif noise_id.startswith("working_"):
                # حرق من الذاكرة العاملة
                item_id = noise_id.replace("working_", "")
                for user_id, items in self.dynamic.working._by_user.items():
                    for item in list(items):
                        if item.id == item_id:
                            items.remove(item)
                            removed += 1
                            break
        
        # حرق الكاش
        cache_keys_to_remove = []
        for key, item in self.dynamic.cache._items.items():
            if len(str(item.value)) < 10:
                cache_keys_to_remove.append(key)
        
        for key in cache_keys_to_remove:
            del self.dynamic.cache._items[key]
            removed += 1
        
        # إنتاج الطاقة: وضوح
        clarity_gain = min(10.0, removed * 0.5)
        self.energy.clarity = min(100.0, self.energy.clarity + clarity_gain)
        self.total_energy_produced[ENERGY_TYPE_CLARITY] += clarity_gain
        
        logger.info(f"🔥 حرق ضوضاء: {removed} عنصر → وضوح +{clarity_gain:.1f}")
        
        return {
            "removed": removed,
            "energy_gained": clarity_gain,
            "energy_type": ENERGY_TYPE_CLARITY
        }
    
    def burn_redundancy(self, intensity: float = 1.0) -> Dict[str, Any]:
        """
        حرق التكرار - دمج المعلومات المكررة.
        
        التكرار يحترق → يتحول إلى سرعة.
        """
        redundancies = self.detect_redundancy()
        merged = 0
        
        for dup1, dup2 in redundancies:
            # دمج المفهومين
            result = self._merge_concepts(dup1, dup2)
            if result:
                merged += 1
        
        # إنتاج الطاقة: سرعة
        speed_gain = min(10.0, merged * 0.3)
        self.energy.speed = min(100.0, self.energy.speed + speed_gain)
        self.total_energy_produced[ENERGY_TYPE_SPEED] += speed_gain
        
        logger.info(f"🔥 حرق تكرار: {merged} زوج مدمج → سرعة +{speed_gain:.1f}")
        
        return {
            "merged": merged,
            "energy_gained": speed_gain,
            "energy_type": ENERGY_TYPE_SPEED
        }
    
    def _merge_concepts(self, concept1: str, concept2: str) -> bool:
        """دمج مفهومين مكررين"""
        try:
            # العثور على المفهومين
            items = self.store.query("semantic", min_importance=0.0, limit=500)
            found1 = None
            found2 = None
            
            for item in items:
                if item.get("concept") == concept1:
                    found1 = item
                elif item.get("concept") == concept2:
                    found2 = item
            
            if found1 and found2:
                # دمج الأهمية
                importance1 = found1.get("_importance", 0.5)
                importance2 = found2.get("_importance", 0.5)
                merged_importance = max(importance1, importance2)
                
                # تحديث المفهوم المتبقي
                found1["_importance"] = merged_importance
                
                # وضع علامة على المفهوم المدمج
                found2["_metadata"] = found2.get("_metadata", {})
                found2["_metadata"]["merged_into"] = concept1
                found2["_metadata"]["merged_at"] = time.time()
                
                # حفظ التغييرات
                path = self.store.FILE_MAP["semantic"]
                raw = [i.__dict__ for i in items]
                tmp = path.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(raw, f, ensure_ascii=False, indent=2)
                tmp.replace(path)
                
                return True
        except Exception as e:
            logger.error(f"فشل دمج المفاهيم: {e}")
        
        return False
    
    def burn_weak_links(self, intensity: float = 1.0) -> Dict[str, Any]:
        """
        حرق الروابط الضعيفة - إزالة العلاقات منخفضة القوة.
        
        الروابط الضعيفة تحترق → تتحول إلى تركيز.
        """
        weak_links = self.detect_weak_links()
        removed = 0
        
        assoc_items = self.store.query("associative", min_importance=0.0, limit=500)
        
        for source, target, weight in weak_links:
            for item in assoc_items:
                if item.get("source") == source and item.get("target") == target:
                    # وضع علامة للإزالة بدلاً من الحذف الفوري
                    item["_metadata"] = item.get("_metadata", {})
                    item["_metadata"]["burned"] = True
                    item["_metadata"]["burned_at"] = time.time()
                    removed += 1
                    break
        
        # حفظ التغييرات
        path = self.store.FILE_MAP["associative"]
        raw = [i.__dict__ for i in assoc_items]
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
        
        # إنتاج الطاقة: تركيز
        focus_gain = min(10.0, removed * 0.2)
        self.energy.focus = min(100.0, self.energy.focus + focus_gain)
        self.total_energy_produced[ENERGY_TYPE_FOCUS] += focus_gain
        
        logger.info(f"🔥 حرق روابط ضعيفة: {removed} رابط → تركيز +{focus_gain:.1f}")
        
        return {
            "removed": removed,
            "energy_gained": focus_gain,
            "energy_type": ENERGY_TYPE_FOCUS
        }
    
    def burn_low_value(self, threshold: float = 0.3) -> Dict[str, Any]:
        """
        حرق العناصر منخفضة القيمة.
        
        القيمة المنخفضة تحترق → تتحول إلى إبداع.
        """
        removed = 0
        
        for kind, path in self.store.FILE_MAP.items():
            items = self.store.query(kind, min_importance=0.0, limit=1000)
            kept = []
            
            for item in items:
                importance = item.get("_importance", 0.5)
                if importance < threshold and kind != "semantic":  # نحتفظ بالمفاهيم الدلالية
                    removed += 1
                else:
                    kept.append(item)
            
            raw = [i.__dict__ for i in kept]
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
            tmp.replace(path)
        
        # إنتاج الطاقة: إبداع
        creativity_gain = min(10.0, removed * 0.1)
        self.energy.creativity = min(100.0, self.energy.creativity + creativity_gain)
        self.total_energy_produced[ENERGY_TYPE_CREATIVITY] += creativity_gain
        
        logger.info(f"🔥 حرق قيمة منخفضة: {removed} عنصر → إبداع +{creativity_gain:.1f}")
        
        return {
            "removed": removed,
            "energy_gained": creativity_gain,
            "energy_type": ENERGY_TYPE_CREATIVITY
        }
    
    def burn_conflicts(self) -> Dict[str, Any]:
        """
        حرق التناقضات - حل التعارضات المعرفية.
        
        التناقضات تحترق → تتحول إلى تماسك.
        """
        conflicts = self.detect_conflicts()
        resolved = 0
        
        for a, b, conflict_type in conflicts:
            # حل التناقض بتحديد المفهوم الأقوى
            fitness_a = self._calculate_concept_fitness(a)
            fitness_b = self._calculate_concept_fitness(b)
            
            if fitness_a > fitness_b:
                # a أقوى، b يتم دمجها كاستثناء
                self._add_exception(b, a)
            else:
                self._add_exception(a, b)
            
            resolved += 1
        
        # إنتاج الطاقة: تماسك
        coherence_gain = min(10.0, resolved * 0.5)
        self.energy.coherence = min(100.0, self.energy.coherence + coherence_gain)
        self.total_energy_produced[ENERGY_TYPE_COHERENCE] += coherence_gain
        
        logger.info(f"🔥 حرق تناقضات: {resolved} زوج → تماسك +{coherence_gain:.1f}")
        
        return {
            "resolved": resolved,
            "energy_gained": coherence_gain,
            "energy_type": ENERGY_TYPE_COHERENCE
        }
    
    def _calculate_concept_fitness(self, concept: str) -> float:
        """حساب لياقة المفهوم"""
        # من الذاكرة
        items = self.store.query("semantic", search_text=concept, limit=5)
        for item in items:
            if item.get("concept") == concept:
                return item.get("_importance", 0.5)
        
        # من الاستخدام في السجل
        use_count = 0
        for event in self.core.iterate_events(limit=500):
            payload = self.core.get_payload(event)
            if concept.lower() in str(payload).lower():
                use_count += 1
        
        return min(1.0, use_count / 50)
    
    def _add_exception(self, weak_concept: str, strong_concept: str):
        """إضافة استثناء لمفهوم ضعيف تحت مفهوم قوي"""
        # تسجيل العلاقة كاستثناء
        self.store.save_associative(
            source=weak_concept,
            target=strong_concept,
            relation_type="exception_of",
            strength=0.3
        )
    
    # ============================================================
    # المستوى 3: إنتاج وتوزيع الطاقة (Energy Distribution)
    # ============================================================
    
    def distribute_energy(self) -> Dict[str, Any]:
        """
        توزيع الطاقة المنتجة على النظام.
        
        الطاقة تحسن أداء الذاكرة:
        - وضوح: تحسين الاسترجاع
        - سرعة: تسريع المعالجة
        - تركيز: تحسين الانتباه
        - إبداع: توليد روابط جديدة
        - تماسك: تنظيم المعرفة
        - نظام: ترتيب المعلومات
        """
        distribution = {
            "clarity_boost": self.energy.clarity * 0.1,
            "speed_boost": self.energy.speed * 0.1,
            "focus_boost": self.energy.focus * 0.1,
            "creativity_boost": self.energy.creativity * 0.1,
            "coherence_boost": self.energy.coherence * 0.1
        }
        
        # تطبيق التحسينات على النظام
        # (تأثير فعلي يتطلب تكامل مع أجزاء أخرى)
        
        logger.info(f"⚡ توزيع الطاقة: وضوح {self.energy.clarity:.1f}%, "
                   f"سرعة {self.energy.speed:.1f}%, تركيز {self.energy.focus:.1f}%")
        
        return distribution
    
    # ============================================================
    # المستوى 4: الدورة الأيضية الكاملة
    # ============================================================
    
    def metabolic_cycle(self, level: int = None) -> MetabolicCycle:
        """
        دورة أيضية كاملة - حرق جميع أنواع الوقود، إنتاج كل أنواع الطاقة.
        
        هذه هي heartbeat النظام - تنظيف وتحسين مستمر.
        """
        if level is None:
            level = self.metabolism_level
        
        cycle_id = f"cycle_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        start_time = time.time()
        
        logger.info(f"🔄 بدء الدورة الأيضية (المستوى {level})")
        
        # تحديد شدة الحرق حسب المستوى
        intensity = level / METABOLISM_LEVEL_MAXIMUM
        
        # حرق جميع أنواع الوقود
        fuel_consumed = {}
        
        # 1) حرق الضوضاء
        noise_result = self.burn_noise(intensity)
        fuel_consumed[FUEL_TYPE_NOISE] = noise_result["removed"]
        
        # 2) حرق التكرار (في المستويات المتوسطة فما فوق)
        if level >= METABOLISM_LEVEL_MODERATE:
            redundancy_result = self.burn_redundancy(intensity)
            fuel_consumed[FUEL_TYPE_REDUNDANCY] = redundancy_result["merged"]
        
        # 3) حرق الروابط الضعيفة
        if level >= METABOLISM_LEVEL_MODERATE:
            weak_result = self.burn_weak_links(intensity)
            fuel_consumed[FUEL_TYPE_WEAK_LINKS] = weak_result["removed"]
        
        # 4) حرق القيمة المنخفضة
        if level >= METABOLISM_LEVEL_INTENSE:
            low_value_result = self.burn_low_value(threshold=0.3)
            fuel_consumed[FUEL_TYPE_LOW_VALUE] = low_value_result["removed"]
        
        # 5) حرق التناقضات
        if level >= METABOLISM_LEVEL_INTENSE:
            conflicts_result = self.burn_conflicts()
            fuel_consumed[FUEL_TYPE_CONFLICT] = conflicts_result["resolved"]
        
        # إنتاج الطاقة
        energy_produced = {
            ENERGY_TYPE_CLARITY: self.energy.clarity,
            ENERGY_TYPE_SPEED: self.energy.speed,
            ENERGY_TYPE_FOCUS: self.energy.focus,
            ENERGY_TYPE_CREATIVITY: self.energy.creativity,
            ENERGY_TYPE_COHERENCE: self.energy.coherence,
            ENERGY_TYPE_ORDER: self.energy.order
        }
        
        # توزيع الطاقة
        self.distribute_energy()
        
        # حساب الكفاءة
        total_fuel = sum(fuel_consumed.values())
        total_energy = self.energy.total_energy()
        efficiency = total_energy / (total_fuel + 1) * 10
        
        duration = time.time() - start_time
        
        cycle = MetabolicCycle(
            id=cycle_id,
            timestamp=start_time,
            level=level,
            fuel_consumed=fuel_consumed,
            energy_produced=energy_produced,
            duration=duration,
            efficiency=min(100.0, efficiency)
        )
        
        self.cycles.append(cycle)
        
        # الاحتفاظ بآخر 100 دورة
        if len(self.cycles) > 100:
            self.cycles = self.cycles[-100:]
        
        # تسجيل في السجل
        self.core.append_event(
            event_type="biological::metabolic_cycle",
            payload={
                "cycle_id": cycle_id,
                "level": level,
                "fuel_consumed": total_fuel,
                "energy_total": total_energy,
                "efficiency": efficiency,
                "duration": duration
            }
        )
        
        logger.info(f"✅ الدورة الأيضية اكتملت: حرق {total_fuel} وقود, "
                   f"طاقة {total_energy:.1f}, كفاءة {efficiency:.1f}%")
        
        # حفظ الحالة
        self._save_state()
        self._save_energy()
        
        return cycle
    
    def _continuous_metabolism(self):
        """دورة أيضية مستمرة في الخلفية"""
        while self._active:
            try:
                if self.metabolism_level > METABOLISM_LEVEL_NONE:
                    # دورة كل ساعة في المستوى العادي، كل 10 دقائق في المستوى المكثف
                    interval = 600 if self.metabolism_level >= METABOLISM_LEVEL_INTENSE else 3600
                    self.metabolic_cycle(self.metabolism_level)
                    threads.interruptible_sleep(interval)
                else:
                    threads.interruptible_sleep(3600)
            except Exception as e:
                logger.error(f"خطأ في الدورة الأيضية: {e}")
                threads.interruptible_sleep(3600)
    
    def _energy_monitoring_loop(self):
        """مراقبة مستويات الطاقة"""
        while self._active:
            try:
                # تسوس الطاقة الطبيعي (تستهلك مع الاستخدام)
                decay_rate = 0.01  # 1% كل ساعة
                
                self.energy.clarity *= (1 - decay_rate)
                self.energy.speed *= (1 - decay_rate)
                self.energy.focus *= (1 - decay_rate)
                self.energy.creativity *= (1 - decay_rate)
                self.energy.coherence *= (1 - decay_rate)
                self.energy.order *= (1 - decay_rate)
                
                threads.interruptible_sleep(3600)  # كل ساعة
            except Exception as e:
                logger.error(f"خطأ في مراقبة الطاقة: {e}")
                threads.interruptible_sleep(3600)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة الأيض"""
        try:
            state = {
                "metabolism_level": self.metabolism_level,
                "cycles_count": len(self.cycles),
                "total_fuel_consumed": dict(self.total_fuel_consumed),
                "total_energy_produced": dict(self.total_energy_produced),
                "saved_at": time.time()
            }
            with open(METABOLISM_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الأيض: {e}")
    
    def _load_state(self):
        """تحميل حالة الأيض"""
        try:
            if METABOLISM_STATE_FILE.exists():
                with open(METABOLISM_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.metabolism_level = state.get("metabolism_level", METABOLISM_LEVEL_MODERATE)
                    self.total_fuel_consumed = defaultdict(int, state.get("total_fuel_consumed", {}))
                    self.total_energy_produced = defaultdict(float, state.get("total_energy_produced", {}))
                logger.info("📂 تم تحميل حالة الأيض")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الأيض: {e}")
    
    def _save_energy(self):
        """حفظ مستويات الطاقة"""
        try:
            with open(METABOLISM_ENERGY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.energy.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الطاقة: {e}")
    
    def _load_energy(self):
        """تحميل مستويات الطاقة"""
        try:
            if METABOLISM_ENERGY_FILE.exists():
                with open(METABOLISM_ENERGY_FILE, 'r', encoding='utf-8') as f:
                    energy_data = json.load(f)
                    self.energy = EnergyReservoir(
                        clarity=energy_data.get("clarity", 0),
                        speed=energy_data.get("speed", 0),
                        focus=energy_data.get("focus", 0),
                        creativity=energy_data.get("creativity", 0),
                        coherence=energy_data.get("coherence", 0),
                        order=energy_data.get("order", 0)
                    )
                logger.info(f"📂 تم تحميل الطاقة: {self.energy.total_energy():.1f}")
        except Exception as e:
            logger.error(f"خطأ في تحميل الطاقة: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_metabolism_level(self, level: int):
        """تعيين مستوى الأيض"""
        self.metabolism_level = level
        logger.info(f"⚙️ مستوى الأيض: {level}")
    
    def force_metabolic_cycle(self, level: int = None) -> MetabolicCycle:
        """فرض دورة أيضية فورية"""
        return self.metabolic_cycle(level)
    
    def get_energy_status(self) -> Dict[str, Any]:
        """حالة الطاقة الحالية"""
        return self.energy.to_dict()
    
    def get_cycle_history(self, limit: int = 20) -> List[Dict]:
        """سجل الدورات الأيضية"""
        return [
            {
                "id": c.id[:16],
                "level": c.level,
                "fuel": sum(c.fuel_consumed.values()),
                "energy": sum(c.energy_produced.values()),
                "efficiency": c.efficiency,
                "duration": c.duration
            }
            for c in self.cycles[-limit:]
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """إحصائيات الأيض الكاملة"""
        return {
            "metabolism_level": self.metabolism_level,
            "current_energy": self.energy.to_dict(),
            "total_fuel_consumed": dict(self.total_fuel_consumed),
            "total_energy_produced": dict(self.total_energy_produced),
            "cycles_completed": len(self.cycles),
            "avg_efficiency": sum(c.efficiency for c in self.cycles) / len(self.cycles) if self.cycles else 0
        }
    
    def stop(self):
        """إيقاف نظام الأيض"""
        self._active = False
        self._save_state()
        self._save_energy()
        logger.info("🛑 إيقاف نظام الأيض المعرفي")


# ============================================================
# الـ Singleton
# ============================================================

_metabolism_instance: Optional[CognitiveMetabolism] = None
_metabolism_lock = threading.Lock()


def get_metabolism() -> CognitiveMetabolism:
    """الحصول على النسخة الوحيدة من نظام الأيض المعرفي"""
    global _metabolism_instance
    if _metabolism_instance is None:
        with _metabolism_lock:
            if _metabolism_instance is None:
                _metabolism_instance = CognitiveMetabolism()
    return _metabolism_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔥 الأيض المعرفي - حرق الضوضاء، توليد الطاقة الذهنية")
    print("=" * 70 + "\n")
    
    metabolism = get_metabolism()
    
    # 1) اكتشاف الضوضاء
    print("📡 اكتشاف الضوضاء...")
    noise = metabolism.detect_noise()
    print(f"   عناصر ضوضاء: {len(noise)}")
    
    # 2) حرق الضوضاء
    print("\n🔥 حرق الضوضاء...")
    result = metabolism.burn_noise()
    print(f"   تم حرق {result['removed']} عنصر → {result['energy_type']} +{result['energy_gained']:.1f}")
    
    # 3) حرق التكرار
    print("\n🔄 حرق التكرار...")
    result = metabolism.burn_redundancy()
    print(f"   تم دمج {result['merged']} زوج → {result['energy_type']} +{result['energy_gained']:.1f}")
    
    # 4) حرق الروابط الضعيفة
    print("\n🔗 حرق الروابط الضعيفة...")
    result = metabolism.burn_weak_links()
    print(f"   تم حرق {result['removed']} رابط → {result['energy_type']} +{result['energy_gained']:.1f}")
    
    # 5) حرق التناقضات
    print("\n⚡ حرق التناقضات...")
    result = metabolism.burn_conflicts()
    print(f"   تم حل {result['resolved']} تناقض → {result['energy_type']} +{result['energy_gained']:.1f}")
    
    # 6) دورة أيضية كاملة
    print("\n🔄 دورة أيضية كاملة...")
    cycle = metabolism.metabolic_cycle(level=3)
    print(f"   الوقود المحروق: {sum(cycle.fuel_consumed.values())}")
    print(f"   الطاقة المنتجة: {sum(cycle.energy_produced.values()):.1f}")
    print(f"   الكفاءة: {cycle.efficiency:.1f}%")
    print(f"   المدة: {cycle.duration:.2f} ثانية")
    
    # 7) حالة الطاقة
    print("\n⚡ حالة الطاقة الحالية:")
    energy = metabolism.get_energy_status()
    for e_type, value in energy.items():
        if e_type != "total":
            print(f"   {e_type}: {value:.1f}")
    print(f"   الإجمالي: {energy['total']:.1f}")
    
    # 8) إحصائيات
    print("\n📊 إحصائيات الأيض:")
    stats = metabolism.get_statistics()
    print(f"   مستوى الأيض: {stats['metabolism_level']}")
    print(f"   دورات مكتملة: {stats['cycles_completed']}")
    print(f"   متوسط الكفاءة: {stats['avg_efficiency']:.1f}%")
    
    print("\n" + "=" * 70)
    print("✅ نظام الأيض المعرفي جاهز - حرق الضوضاء، إنتاج الطاقة")
    print("=" * 70)
