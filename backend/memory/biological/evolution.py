# backend/memory/biological/evolution.py
# 🧬 التطور الذاتي - داروين الرقمي، بقاء الأصلح
# الإصدار: 3.0.0 - الانتقاء الطبيعي للمفاهيم، طفرة المعنى، تكيف الذكاء

"""
نظام التطور الذاتي للذاكرة السيادية.

الفلسفة:
- الذكاء الذي لا يتطور يموت
- المفاهيم تخضع للانتقاء الطبيعي: الأصلح يبقى، الأضعف يندثر
- الطفرات المعرفية تولد أفكاراً جديدة
- التكيف مع البيئة (الاستخدام) يغير البنية
- التطور ليس عشوائياً، بل موجه نحو الهدف

هذا ليس مجرد تحسين. هذه هي نظرية التطور الرقمي.
"""

import json
import hashlib
import secrets
import time
import threading
import random
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict
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
# الثوابت وإعدادات التطور
# ============================================================

EVOLUTION_DIR = DATA_DIR / "evolution"
EVOLUTION_LOG = EVOLUTION_DIR / "evolution_log.jsonl"
EVOLUTION_STATE_FILE = EVOLUTION_DIR / "evolution_state.json"
EVOLUTION_GENOME_FILE = EVOLUTION_DIR / "genome.json"
EVOLUTION_MUTATIONS_DIR = EVOLUTION_DIR / "mutations"

for d in [EVOLUTION_DIR, EVOLUTION_MUTATIONS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات التطور
EVOLUTION_LEVEL_NONE = 0            # لا تطور
EVOLUTION_LEVEL_PASSIVE = 1         # تطور سلبي (مراقبة فقط)
EVOLUTION_LEVEL_ACTIVE = 2          # تطور نشط (تحسينات صغيرة)
EVOLUTION_LEVEL_ADAPTIVE = 3        # تطور تكيفي (يتغير مع البيئة)
EVOLUTION_LEVEL_MUTATIVE = 4        # تطور طفري (يخلق مفاهيم جديدة)
EVOLUTION_LEVEL_EVOLUTIONARY = 5    # تطور ثوري (إعادة هيكلة كاملة)

# أنماط الانتقاء الطبيعي
SELECTION_TYPE_FITNESS = "fitness"          # اللياقة: الأكثر استخداماً
SELECTION_TYPE_RECENCY = "recency"          # الحداثة: الأحدث
SELECTION_TYPE_COHERENCE = "coherence"      # الترابط: الأكثر ارتباطاً
SELECTION_TYPE_NOVELTY = "novelty"          # الجدة: الأكثر ابتكاراً
SELECTION_TYPE_COMPLEXITY = "complexity"    # التعقيد: الأفكار العميقة
SELECTION_TYPE_HYBRID = "hybrid"            # هجين: مزيج من العوامل

# أنواع الطفرات
MUTATION_TYPE_SPLIT = "split"              # تقسيم المفهوم
MUTATION_TYPE_MERGE = "merge"              # دمج المفاهيم
MUTATION_TYPE_GENERALIZE = "generalize"    # تعميم
MUTATION_TYPE_SPECIALIZE = "specialize"    # تخصص
MUTATION_TYPE_ABSTRACT = "abstract"        # تجريد
MUTATION_TYPE_INSTANTIATE = "instantiate"  # تجسيد
MUTATION_TYPE_REVERSE = "reverse"          # عكس العلاقة
MUTATION_TYPE_ANALOGY = "analogy"          # تماثل (قياس)
MUTATION_TYPE_CREATE = "create"            # خلق جديد


@dataclass
class ConceptGene:
    """جين مفهومي - الوحدة الأساسية للتطور"""
    id: str
    name: str
    definition: str
    fitness: float                    # 0-1: مدى نجاح هذا المفهوم
    age: float                        # العمر بالثواني
    generation: int                   # جيل التطور
    parents: List[str]                # المفاهيم الأم
    mutations: List[str]              # الطفرات التي مر بها
    use_count: int                    # عدد مرات الاستخدام
    last_used: float
    connections: int                  # عدد المفاهيم المرتبطة
    complexity: float                 # 0-1: مدى تعقيد المفهوم
    novelty: float                    # 0-1: مدى ابتكار المفهوم


@dataclass
class EvolutionMutation:
    """طفرة تطورية"""
    id: str
    mutation_type: str
    source_concept: str
    target_concept: Optional[str]
    result_concept: Optional[str]
    timestamp: float
    success: bool
    description: str


@dataclass
class GenerationStats:
    """إحصائيات جيل تطوري"""
    number: int
    timestamp: float
    total_concepts: int
    avg_fitness: float
    avg_complexity: float
    mutations_count: int
    new_concepts: int
    extinct_concepts: int


# ============================================================
# نظام التطور الذاتي
# ============================================================

class MemoryEvolution:
    """
    نظام التطور الذاتي - داروين الرقمي.
    
    المبادئ:
    1. المفاهيم تخضع للانتقاء الطبيعي
    2. الطفرات تولد أفكاراً جديدة
    3. اللياقة تحدد البقاء
    4. التطور موجه بالبيئة (الاستخدام)
    5. الأجيال تتحسن مع الوقت
    """
    
    def __init__(self):
        self.core = get_core()
        self.store = get_store()
        self.dynamic = get_dynamic_memory()
        
        # حالة التطور
        self.evolution_level = EVOLUTION_LEVEL_ADAPTIVE
        self.current_generation = 0
        self.genome: Dict[str, ConceptGene] = {}
        self.mutations: List[EvolutionMutation] = []
        self.generations: List[GenerationStats] = []
        
        # معاملات التطور
        self.mutation_rate = 0.1          # 10% فرصة طفرة
        self.crossover_rate = 0.3         # 30% فرصة تزاوج
        self.elite_percent = 0.2          # 20% من الأفضل يبقون
        self.extinction_threshold = 0.1    # أقل من 10% لياقة -> انقراض
        
        # خلفيات التطور
        self._active = True
        self._evolution_loop = threading.Thread(target=self._continuous_evolution, daemon=True)
        self._evolution_loop.start()
        
        self._mutation_generator = threading.Thread(target=self._random_mutation_loop, daemon=True)
        self._mutation_generator.start()
        
        # تحميل الحالة
        self._load_state()
        self._load_genome()
        
        logger.info("🧬 نظام التطور الذاتي جاهز - داروين الرقمي يتحكم")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لنظام التطور الذاتي
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لنظام التطور الذاتي (داروين الرقمي).
        
        يمسح:
        - الجينوم (genome) - جميع المفاهيم
        - سجل الطفرات (mutations)
        - سجل الأجيال (generations)
        """
        logger.info("🔄 إعادة تهيئة نظام التطور الذاتي...")
        
        # مسح الجينوم (جميع المفاهيم)
        self.genome.clear()
        
        # مسح سجل الطفرات
        self.mutations.clear()
        
        # مسح سجل الأجيال
        self.generations.clear()
        
        # إعادة تعيين الجيل الحالي
        self.current_generation = 0
        
        # إعادة تعيين معاملات التطور
        self.mutation_rate = 0.1
        self.crossover_rate = 0.3
        self.elite_percent = 0.2
        self.extinction_threshold = 0.1
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="biological::evolution_reset",
            payload={
                "timestamp": time.time(),
                "status": "evolution_system_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة نظام التطور الذاتي اكتملت - الحياة تبدأ من جديد")
    
    # ============================================================
    # المستوى 1: حساب اللياقة (Fitness Calculation)
    # ============================================================
    
    def calculate_fitness(self, concept_name: str) -> float:
        """
        حساب لياقة المفهوم - مدى نجاحه في البيئة.
        
        عوامل اللياقة:
        - التكرار: كم مرة تم استخدامه
        - الحداثة: متى آخر مرة استخدم
        - الترابط: كم عدد المفاهيم المرتبطة به
        - الأهمية: الأهمية المخزنة
        """
        # من الذاكرة الدلالية
        semantic_items = self.store.query("semantic", search_text=concept_name, limit=5)
        importance = 0.5
        for item in semantic_items:
            importance = item.get("_importance", 0.5)
            break
        
        # عدد الارتباطات
        associations = self.store.query("associative", search_text=concept_name, limit=50)
        connections = len(associations)
        
        # تكرار الاستخدام من السجل
        use_count = 0
        for event in self.core.iterate_events(limit=500):
            payload = self.core.get_payload(event)
            if concept_name.lower() in str(payload).lower():
                use_count += 1
        
        # حساب اللياقة المركبة
        fitness = (
            importance * 0.3 +
            min(1.0, connections / 20) * 0.2 +
            min(1.0, use_count / 100) * 0.3 +
            0.2  # عامل أساسي
        )
        
        return min(1.0, fitness)
    
    def calculate_genome_fitness(self) -> Dict[str, float]:
        """حساب لياقة جميع الجينات في الجينوم"""
        fitness_map = {}
        for concept_id, gene in self.genome.items():
            fitness_map[concept_id] = self.calculate_fitness(gene.name)
        return fitness_map
    
    # ============================================================
    # المستوى 2: الانتقاء الطبيعي (Natural Selection)
    # ============================================================
    
    def natural_selection(self, selection_type: str = SELECTION_TYPE_HYBRID) -> List[str]:
        """
        الانتقاء الطبيعي - اختيار المفاهيم الأصلح للبقاء.
        
        المفاهيم الضعيفة تنقرض، القوية تتكاثر.
        """
        logger.info(f"🦖 بدء الانتقاء الطبيعي (نوع: {selection_type})")
        
        # حساب اللياقة لكل مفهوم
        fitness_scores = []
        for concept_id, gene in self.genome.items():
            fitness = self.calculate_fitness(gene.name)
            fitness_scores.append((fitness, concept_id, gene))
        
        # ترتيب حسب اللياقة
        fitness_scores.sort(key=lambda x: x[0], reverse=True)
        
        # تحديد المفاهيم المنقرضة (أسفل العتبة)
        extinct = []
        survivors = []
        
        for i, (fitness, concept_id, gene) in enumerate(fitness_scores):
            if fitness < self.extinction_threshold and i > len(fitness_scores) * 0.3:
                extinct.append(concept_id)
                logger.debug(f"💀 انقراض: {gene.name} (لياقة: {fitness:.1%})")
            else:
                survivors.append(concept_id)
        
        # تسجيل الانقراضات
        for concept_id in extinct:
            if concept_id in self.genome:
                del self.genome[concept_id]
        
        # تسجيل الحدث
        self.core.append_event(
            event_type="evolution::natural_selection",
            payload={
                "selection_type": selection_type,
                "survivors": len(survivors),
                "extinct": len(extinct),
                "avg_fitness": sum(f for f, _, _ in fitness_scores) / len(fitness_scores) if fitness_scores else 0
            }
        )
        
        logger.info(f"✅ الانتقاء الطبيعي: {len(survivors)} باقٍ, {len(extinct)} منقرض")
        return survivors
    
    # ============================================================
    # المستوى 3: الطفرات التطورية (Evolutionary Mutations)
    # ============================================================
    
    def mutate_concept(self, concept_name: str, 
                       mutation_type: str = None) -> Optional[str]:
        """
        طفرة تطورية - تغيير جذري في المفهوم.
        
        أنواع الطفرات:
        - تقسيم: مفهوم واحد → مفهومان متخصصان
        - دمج: مفهومان → مفهوم واحد أعم
        - تعميم: مفهوم → مفهوم أوسع
        - تخصص: مفهوم → مفهوم أضيق
        - تجريد: استخراج المبدأ المجرد
        - عكس: قلب العلاقة
        - تماثل: قياس إلى مجال آخر
        """
        if mutation_type is None:
            mutation_type = random.choice([
                MUTATION_TYPE_SPLIT, MUTATION_TYPE_GENERALIZE,
                MUTATION_TYPE_SPECIALIZE, MUTATION_TYPE_ABSTRACT,
                MUTATION_TYPE_ANALOGY
            ])
        
        mutation_id = f"mut_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        logger.info(f"🧬 طفرة: {mutation_type} على {concept_name}")
        
        result_concept = None
        
        try:
            if mutation_type == MUTATION_TYPE_SPLIT:
                # تقسيم المفهوم إلى مفهومين متخصصين
                result_concept = f"{concept_name}_subtype_{random.randint(1, 100)}"
                self._create_new_concept(result_concept, f"نوع متخصص من {concept_name}")
                
            elif mutation_type == MUTATION_TYPE_GENERALIZE:
                # تعميم المفهوم
                result_concept = f"general_{concept_name}"
                self._create_new_concept(result_concept, f"تعميم لـ {concept_name}")
                
            elif mutation_type == MUTATION_TYPE_SPECIALIZE:
                # تخصص
                result_concept = f"specialized_{concept_name}_{random.randint(1, 100)}"
                self._create_new_concept(result_concept, f"تخصص من {concept_name}")
                
            elif mutation_type == MUTATION_TYPE_ABSTRACT:
                # تجريد
                result_concept = f"abstract_{concept_name}"
                self._create_new_concept(result_concept, f"المبدأ المجرد لـ {concept_name}")
                
            elif mutation_type == MUTATION_TYPE_ANALOGY:
                # تماثل (قياس)
                analogies = ["system", "network", "organism", "ecosystem", "brain"]
                analogy = random.choice(analogies)
                result_concept = f"{concept_name}_as_{analogy}"
                self._create_new_concept(result_concept, f"{concept_name} يشبه {analogy}")
            
            # تسجيل الطفرة
            mutation = EvolutionMutation(
                id=mutation_id,
                mutation_type=mutation_type,
                source_concept=concept_name,
                target_concept=None,
                result_concept=result_concept,
                timestamp=time.time(),
                success=True,
                description=f"طفرة {mutation_type} على {concept_name} -> {result_concept}"
            )
            self.mutations.append(mutation)
            
            # حفظ الطفرة
            self._save_mutation(mutation)
            
            # تسجيل في السجل
            self.core.append_event(
                event_type="evolution::mutation",
                payload={
                    "mutation_id": mutation_id,
                    "type": mutation_type,
                    "source": concept_name,
                    "result": result_concept
                }
            )
            
            return result_concept
            
        except Exception as e:
            logger.exception(f"R-682: فشل الطفرة — silently swallowing. exc={e}")
            mutation = EvolutionMutation(
                id=mutation_id,
                mutation_type=mutation_type,
                source_concept=concept_name,
                target_concept=None,
                result_concept=None,
                timestamp=time.time(),
                success=False,
                description=str(e)
            )
            self.mutations.append(mutation)
            return None
    
    def _create_new_concept(self, name: str, definition: str) -> bool:
        """إنشاء مفهوم جديد في الجينوم"""
        if name in self.genome:
            return False
        
        concept_id = hashlib.sha256(name.encode()).hexdigest()[:16]
        
        gene = ConceptGene(
            id=concept_id,
            name=name,
            definition=definition,
            fitness=0.5,
            age=0,
            generation=self.current_generation,
            parents=[],
            mutations=[],
            use_count=0,
            last_used=time.time(),
            connections=0,
            complexity=0.3,
            novelty=0.7
        )
        
        self.genome[concept_id] = gene
        
        # حفظ في التخزين الصلب
        self.store.save_semantic(
            concept=name,
            definition=definition,
            confidence=0.5,
            related_concepts={}
        )
        
        logger.debug(f"🌱 مفهوم جديد: {name}")
        return True
    
    # ============================================================
    # المستوى 4: التزاوج والتكاثر (Crossover & Reproduction)
    # ============================================================
    
    def crossover_concepts(self, concept_a: str, concept_b: str) -> Optional[str]:
        """
        تزاوج مفهومين - إنتاج مفهوم هجين.
        
        يجمع خصائص الوالدين لخلق مفهوم جديد أقوى.
        """
        logger.info(f"🧬 تزاوج: {concept_a} × {concept_b}")
        
        # استخراج خصائص الوالدين
        fitness_a = self.calculate_fitness(concept_a)
        fitness_b = self.calculate_fitness(concept_b)
        
        # توليد الاسم الهجين
        name_parts = [concept_a.split('_')[0], concept_b.split('_')[0]]
        hybrid_name = f"{name_parts[0]}_{name_parts[1]}_hybrid_{random.randint(1, 1000)}"
        
        # توليد التعريف
        definition = f"هجين بين {concept_a} و {concept_b} يجمع خصائصهما"
        
        # إنشاء المفهوم الجديد
        success = self._create_new_concept(hybrid_name, definition)
        
        if success:
            # تسجيل التزاوج
            self.core.append_event(
                event_type="evolution::crossover",
                payload={
                    "parent_a": concept_a,
                    "parent_b": concept_b,
                    "offspring": hybrid_name,
                    "fitness_a": fitness_a,
                    "fitness_b": fitness_b
                }
            )
            
            logger.info(f"✅ تزاوج ناجح: {hybrid_name}")
            return hybrid_name
        
        return None
    
    # ============================================================
    # المستوى 5: تكيف مع البيئة (Environmental Adaptation)
    # ============================================================
    
    def adapt_to_environment(self) -> Dict[str, Any]:
        """
        تكيف مع البيئة - تعديل المفاهيم بناءً على أنماط الاستخدام.
        
        المفاهيم التي يتم استخدامها بكثرة تصبح أكثر بروزاً.
        المفاهيم المهملة تندثر.
        """
        logger.info("🌍 بدء التكيف مع البيئة")
        
        adaptations = {
            "strengthened": [],
            "weakened": [],
            "created": [],
            "extinct": []
        }
        
        # تحليل أنماط الاستخدام من السجل
        usage_patterns = defaultdict(int)
        for event in self.core.iterate_events(limit=1000):
            payload = self.core.get_payload(event)
            text = str(payload).lower()
            
            for concept_id, gene in self.genome.items():
                if gene.name.lower() in text:
                    usage_patterns[concept_id] += 1
                    gene.use_count += 1
                    gene.last_used = time.time()
        
        # تحديث اللياقة بناءً على الاستخدام
        for concept_id, gene in self.genome.items():
            old_fitness = gene.fitness
            usage_score = min(1.0, usage_patterns.get(concept_id, 0) / 100)
            gene.fitness = old_fitness * 0.7 + usage_score * 0.3
            
            if gene.fitness > old_fitness + 0.1:
                adaptations["strengthened"].append(gene.name)
            elif gene.fitness < old_fitness - 0.1:
                adaptations["weakened"].append(gene.name)
        
        # تطبيق الانتقاء الطبيعي
        survivors = self.natural_selection()
        extinct = [g.name for g in self.genome.values() if g.id not in survivors]
        adaptations["extinct"] = extinct
        
        # توليد مفاهيم جديدة بتكيفية
        if len(adaptations["strengthened"]) > 3:
            for concept in adaptations["strengthened"][:2]:
                if random.random() < self.mutation_rate:
                    new_concept = self.mutate_concept(concept)
                    if new_concept:
                        adaptations["created"].append(new_concept)
        
        # تسجيل
        self.core.append_event(
            event_type="evolution::adaptation",
            payload={
                "strengthened": len(adaptations["strengthened"]),
                "weakened": len(adaptations["weakened"]),
                "created": len(adaptations["created"]),
                "extinct": len(adaptations["extinct"])
            }
        )
        
        logger.info(f"✅ التكيف: {len(adaptations['strengthened'])} تقوية, "
                   f"{len(adaptations['extinct'])} انقراض")
        
        return adaptations
    
    # ============================================================
    # المستوى 6: التطور التلقائي المستمر
    # ============================================================
    
    def evolve_generation(self) -> GenerationStats:
        """
        جيل تطوري جديد - دورة كاملة من الانتقاء والطفرة والتكاثر.
        """
        self.current_generation += 1
        start_time = time.time()
        
        logger.info(f"🌟 الجيل التطوري {self.current_generation}")
        
        # 1) التكيف مع البيئة
        adaptations = self.adapt_to_environment()
        
        # 2) الانتقاء الطبيعي
        survivors = self.natural_selection()
        
        # 3) الطفرات على المفاهيم القوية
        mutations_count = 0
        strong_concepts = [g.name for g in self.genome.values() if g.fitness > 0.7][:10]
        for concept in strong_concepts:
            if random.random() < self.mutation_rate:
                self.mutate_concept(concept)
                mutations_count += 1
        
        # 4) تزاوج بين المفاهيم القوية
        crossovers_count = 0
        if len(strong_concepts) >= 2:
            for i in range(0, len(strong_concepts)-1, 2):
                if random.random() < self.crossover_rate:
                    self.crossover_concepts(strong_concepts[i], strong_concepts[i+1])
                    crossovers_count += 1
        
        # 5) إحصائيات الجيل
        all_fitness = [g.fitness for g in self.genome.values()]
        avg_fitness = sum(all_fitness) / len(all_fitness) if all_fitness else 0
        avg_complexity = sum(g.complexity for g in self.genome.values()) / len(self.genome) if self.genome else 0
        
        generation_stats = GenerationStats(
            number=self.current_generation,
            timestamp=time.time(),
            total_concepts=len(self.genome),
            avg_fitness=avg_fitness,
            avg_complexity=avg_complexity,
            mutations_count=mutations_count,
            new_concepts=len(adaptations["created"]),
            extinct_concepts=len(adaptations["extinct"])
        )
        
        self.generations.append(generation_stats)
        
        # حفظ الجينوم
        self._save_genome()
        
        # تسجيل
        self.core.append_event(
            event_type="evolution::generation_completed",
            payload={
                "generation": self.current_generation,
                "total_concepts": generation_stats.total_concepts,
                "avg_fitness": generation_stats.avg_fitness,
                "duration": time.time() - start_time
            }
        )
        
        logger.info(f"✅ الجيل {self.current_generation}: {generation_stats.total_concepts} مفهوم, "
                   f"متوسط اللياقة: {generation_stats.avg_fitness:.1%}")
        
        return generation_stats
    
    def _continuous_evolution(self):
        """حلقة التطور المستمر"""
        while self._active:
            try:
                if self.evolution_level >= EVOLUTION_LEVEL_ACTIVE:
                    # جيل جديد كل ساعة
                    self.evolve_generation()
                    time.sleep(3600)
                else:
                    time.sleep(3600)
            except Exception as e:
                logger.error(f"خطأ في حلقة التطور: {e}")
                time.sleep(3600)
    
    def _random_mutation_loop(self):
        """توليد طفرات عشوائية"""
        while self._active:
            try:
                if self.evolution_level >= EVOLUTION_LEVEL_MUTATIVE:
                    # اختيار مفهوم عشوائي للطفرة
                    if self.genome:
                        concept = random.choice(list(self.genome.values()))
                        if random.random() < 0.3:
                            self.mutate_concept(concept.name)
                    time.sleep(600)  # كل 10 دقائق
                else:
                    time.sleep(600)
            except Exception as e:
                logger.error(f"خطأ في توليد الطفرات: {e}")
                time.sleep(600)
    
    # ============================================================
    # الأدوات المساعدة
    # ============================================================
    
    def _save_genome(self):
        """حفظ الجينوم"""
        try:
            genome_data = {
                "current_generation": self.current_generation,
                "genes": [
                    {
                        "id": g.id,
                        "name": g.name,
                        "definition": g.definition,
                        "fitness": g.fitness,
                        "age": g.age,
                        "generation": g.generation,
                        "parents": g.parents,
                        "mutations": g.mutations,
                        "use_count": g.use_count,
                        "last_used": g.last_used,
                        "connections": g.connections,
                        "complexity": g.complexity,
                        "novelty": g.novelty
                    }
                    for g in self.genome.values()
                ],
                "saved_at": time.time()
            }
            
            with open(EVOLUTION_GENOME_FILE, 'w', encoding='utf-8') as f:
                json.dump(genome_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الجينوم: {e}")
    
    def _load_genome(self):
        """تحميل الجينوم"""
        try:
            if EVOLUTION_GENOME_FILE.exists():
                with open(EVOLUTION_GENOME_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_generation = data.get("current_generation", 0)
                    for gene_data in data.get("genes", []):
                        gene = ConceptGene(**gene_data)
                        self.genome[gene.id] = gene
                logger.info(f"📂 تم تحميل {len(self.genome)} جيناً")
        except Exception as e:
            logger.error(f"خطأ في تحميل الجينوم: {e}")
    
    def _save_mutation(self, mutation: EvolutionMutation):
        """حفظ طفرة"""
        try:
            mut_file = EVOLUTION_MUTATIONS_DIR / f"{mutation.id}.json"
            with open(mut_file, 'w', encoding='utf-8') as f:
                json.dump(mutation.__dict__, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الطفرة: {e}")
    
    def _save_state(self):
        """حفظ حالة نظام التطور"""
        try:
            state = {
                "evolution_level": self.evolution_level,
                "current_generation": self.current_generation,
                "mutation_rate": self.mutation_rate,
                "crossover_rate": self.crossover_rate,
                "generations_count": len(self.generations),
                "mutations_count": len(self.mutations),
                "saved_at": time.time()
            }
            with open(EVOLUTION_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة التطور: {e}")
    
    def _load_state(self):
        """تحميل حالة نظام التطور"""
        try:
            if EVOLUTION_STATE_FILE.exists():
                with open(EVOLUTION_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.evolution_level = state.get("evolution_level", EVOLUTION_LEVEL_ADAPTIVE)
                    self.mutation_rate = state.get("mutation_rate", 0.1)
                    self.crossover_rate = state.get("crossover_rate", 0.3)
                logger.info("📂 تم تحميل حالة نظام التطور")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة التطور: {e}")
    
    # ============================================================
    # التحكم في التطور
    # ============================================================
    
    def set_evolution_level(self, level: int):
        """تعيين مستوى التطور"""
        self.evolution_level = level
        logger.info(f"⚙️ مستوى التطور: {level}")
    
    def force_evolution_cycle(self) -> GenerationStats:
        """فرض دورة تطورية فورية"""
        logger.info("⚡ فرض دورة تطورية")
        return self.evolve_generation()
    
    def get_fittest_concepts(self, limit: int = 10) -> List[Dict]:
        """الحصول على أكثر المفاهيم لياقة"""
        concepts = [(g.fitness, g.name, g) for g in self.genome.values()]
        concepts.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {
                "name": name,
                "fitness": fitness,
                "generation": gene.generation,
                "use_count": gene.use_count,
                "complexity": gene.complexity
            }
            for fitness, name, gene in concepts[:limit]
        ]
    
    def get_mutation_history(self, limit: int = 50) -> List[Dict]:
        """سجل الطفرات التطورية"""
        return [
            {
                "id": m.id[:16],
                "type": m.mutation_type,
                "source": m.source_concept,
                "result": m.result_concept,
                "success": m.success,
                "timestamp": m.timestamp
            }
            for m in self.mutations[-limit:]
        ]
    
    def get_evolution_statistics(self) -> Dict[str, Any]:
        """إحصائيات التطور الكاملة"""
        all_fitness = [g.fitness for g in self.genome.values()]
        
        return {
            "current_generation": self.current_generation,
            "total_concepts": len(self.genome),
            "avg_fitness": sum(all_fitness) / len(all_fitness) if all_fitness else 0,
            "max_fitness": max(all_fitness) if all_fitness else 0,
            "min_fitness": min(all_fitness) if all_fitness else 0,
            "total_mutations": len(self.mutations),
            "successful_mutations": sum(1 for m in self.mutations if m.success),
            "generations_count": len(self.generations),
            "evolution_level": self.evolution_level,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate
        }
    
    def stop(self):
        """إيقاف نظام التطور"""
        self._active = False
        self._save_state()
        self._save_genome()
        logger.info("🛑 إيقاف نظام التطور الذاتي")


# ============================================================
# الـ Singleton
# ============================================================

_evolution_instance: Optional[MemoryEvolution] = None
_evolution_lock = threading.Lock()


def get_evolution() -> MemoryEvolution:
    """الحصول على النسخة الوحيدة من نظام التطور"""
    global _evolution_instance
    if _evolution_instance is None:
        with _evolution_lock:
            if _evolution_instance is None:
                _evolution_instance = MemoryEvolution()
    return _evolution_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧬 التطور الذاتي - داروين الرقمي، بقاء الأصلح")
    print("=" * 70 + "\n")
    
    evolution = get_evolution()
    
    # 1) إنشاء مفاهيم أولية
    print("🌱 إنشاء مفاهيم أولية...")
    evolution._create_new_concept("الذكاء", "قدرة النظام على التعلم والتكيف")
    evolution._create_new_concept("السيادة", "التحكم الكامل والاستقلالية")
    evolution._create_new_concept("الوعي", "الإدراك الذاتي والتفاعل مع البيئة")
    evolution._create_new_concept("الذاكرة", "تخزين واسترجاع المعلومات")
    print(f"   تم إنشاء {len(evolution.genome)} مفهوم")
    
    # 2) حساب اللياقة
    print("\n📊 حساب اللياقة:")
    for gene in evolution.genome.values():
        fitness = evolution.calculate_fitness(gene.name)
        print(f"   {gene.name}: {fitness:.1%}")
    
    # 3) طفرة
    print("\n🧬 طفرة تطورية:")
    new_concept = evolution.mutate_concept("الذكاء", MUTATION_TYPE_SPECIALIZE)
    if new_concept:
        print(f"   تم إنشاء: {new_concept}")
    
    # 4) تزاوج
    print("\n💞 تزاوج مفاهيم:")
    hybrid = evolution.crossover_concepts("الذكاء", "السيادة")
    if hybrid:
        print(f"   هجين: {hybrid}")
    
    # 5) جيل تطوري
    print("\n🌟 جيل تطوري جديد:")
    generation = evolution.evolve_generation()
    print(f"   المفاهيم: {generation.total_concepts}")
    print(f"   متوسط اللياقة: {generation.avg_fitness:.1%}")
    print(f"   الطفرات: {generation.mutations_count}")
    
    # 6) أقوى المفاهيم
    print("\n🏆 أقوى المفاهيم:")
    fittest = evolution.get_fittest_concepts(5)
    for i, concept in enumerate(fittest, 1):
        print(f"   {i}. {concept['name']} (لياقة: {concept['fitness']:.1%})")
    
    # 7) الإحصائيات
    print("\n📈 إحصائيات التطور:")
    stats = evolution.get_evolution_statistics()
    print(f"   الجيل الحالي: {stats['current_generation']}")
    print(f"   إجمالي المفاهيم: {stats['total_concepts']}")
    print(f"   متوسط اللياقة: {stats['avg_fitness']:.1%}")
    print(f"   الطفرات الناجحة: {stats['successful_mutations']}/{stats['total_mutations']}")
    print(f"   مستوى التطور: {stats['evolution_level']}")
    
    print("\n" + "=" * 70)
    print("✅ نظام التطور الذاتي جاهز - داروين الرقمي يتحكم")
    print("=" * 70)
