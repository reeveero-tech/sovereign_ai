# backend/quantum/quantum_field.py
# ⚛️ محرك الحقل الكمي الجبار - حقول كمومية متكاملة، نشر التأثيرات، تداخلات متعددة النطاقات
# الإصدار: 3.1.0 - مع دعم إعادة التهيئة الكاملة للاختبارات التكاملية

"""
محرك الحقل الكمي للعقل السيادي.

الفلسفة:
- الحقل الكمي هو الخلفية التي تتفاعل فيها الحالات
- الحقل يربط بين الحالات عبر مسافات افتراضية
- نشر التأثيرات يخلق ترابطاً غير محلي
- التداخل متعدد النطاقات يلتقط أنماطاً على مقاييس مختلفة
- الحقل يؤثر على الانتقالات والتراكبات

هذا ليس مجرد حقل. هذه هي نسيج الواقع الكمي.
"""

import json
from runtime.atomic_json import atomic_write_json  # R-781
import math
import cmath
import random
import secrets
import threading
import runtime.threads as threads
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

try:
    from ..memory.core import get_core, EventType
    from .quantum_state import get_quantum_state_engine, QuantumAmplitude
    from .quantum_transition import get_quantum_transition_engine
    from .quantum_superposition import get_quantum_superposition_engine
    from ..config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from .quantum_state import get_quantum_state_engine, QuantumAmplitude
    from .quantum_transition import get_quantum_transition_engine
    from .quantum_superposition import get_quantum_superposition_engine
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الحقل الكمومي
# ============================================================

QUANTUM_FIELD_DIR = DATA_DIR / "quantum" / "field"
QUANTUM_FIELD_DIR.mkdir(parents=True, exist_ok=True)
QUANTUM_FIELD_LOG = QUANTUM_FIELD_DIR / "quantum_field_log.jsonl"
QUANTUM_FIELD_STATE_FILE = QUANTUM_FIELD_DIR / "quantum_field_state.json"

# أنواع الحقول الكمومية
FIELD_TYPE_SCALAR = "scalar"          # حقل سلمي (قيمة واحدة لكل نقطة)
FIELD_TYPE_VECTOR = "vector"          # حقل متجهي (اتجاه وحجم)
FIELD_TYPE_TENSOR = "tensor"          # حقل تنسوري (مصفوفة لكل نقطة)
FIELD_TYPE_PROBABILITY = "probability" # حقل احتمالي
FIELD_TYPE_PHASE = "phase"            # حقل طور

# أنماط الانتشار
PROPAGATION_MODE_WAVE = "wave"        # انتشار موجي
PROPAGATION_MODE_DIFFUSION = "diffusion"  # انتشار بالانتشار
PROPAGATION_MODE_BALLISTIC = "ballistic"  # انتشار باليستي
PROPAGATION_MODE_QUANTUM = "quantum"      # انتشار كمومي


def _safe_gaussian_filter(values: List[float], sigma: float) -> List[float]:
    """مرشح غاوسي بسيط بدون numpy/scipy"""
    n = len(values)
    if n == 0:
        return []
    
    # إنشاء نافذة غاوسية بسيطة
    window_size = int(sigma * 3) + 1
    if window_size < 1:
        window_size = 1
    
    result = []
    for i in range(n):
        total = 0.0
        weight_sum = 0.0
        for j in range(max(0, i - window_size), min(n, i + window_size + 1)):
            distance = abs(i - j)
            weight = math.exp(-(distance ** 2) / (2 * sigma ** 2))
            total += values[j] * weight
            weight_sum += weight
        result.append(total / weight_sum if weight_sum > 0 else values[i])
    
    return result


@dataclass
class QuantumFieldPoint:
    """نقطة في الحقل الكمومي"""
    id: str
    position: Tuple[float, float, float]  # إحداثيات في الفضاء الكمومي
    scalar_value: float
    vector_value: Tuple[float, float, float]
    phase: float
    energy: float
    coherence: float
    neighbors: List[str]
    distance_to_center: float


@dataclass
class QuantumFieldGrid:
    """شبكة الحقل الكمومي"""
    id: str
    name: str
    points: Dict[str, QuantumFieldPoint]
    dimensions: Tuple[int, int, int]
    spacing: float
    field_type: str
    total_energy: float
    average_coherence: float
    propagation_matrix: Dict[str, Dict[str, float]]  # استبدال np.ndarray بـ dict


@dataclass
class FieldEffect:
    """تأثير الحقل على النظام"""
    id: str
    source: str
    target: str
    strength: float
    type: str
    propagation_delay: float
    interference_pattern: str


@dataclass
class QuantumFieldSnapshot:
    """لقطة حقل كمومي"""
    timestamp: float
    field_map: Dict[str, float]
    propagated_effects: Dict[str, float]
    influenced_transitions: Dict[str, Dict[str, float]]
    field_energy: float
    average_coherence: float
    propagation_speed: float
    interference_patterns: List[Dict[str, Any]]
    narrative: str


# ============================================================
# محرك الحقل الكمي الجبار
# ============================================================

class QuantumFieldEngine:
    """
    محرك الحقل الكمي الجبار - حقول كمومية متكاملة، نشر التأثيرات، تداخلات متعددة النطاقات.
    
    المبادئ:
    1. الحقل هو الخلفية التي تتفاعل فيها الحالات
    2. الحقل يربط الحالات عبر مسافات افتراضية
    3. نشر التأثيرات يخلق ترابطاً غير محلي
    4. التداخل متعدد النطاقات يلتقط أنماطاً مختلفة
    5. الحقل يؤثر على الانتقالات والتراكبات
    """
    
    def __init__(self):
        self.core = get_core()
        self.qstate = get_quantum_state_engine()
        self.qtrans = get_quantum_transition_engine()
        
        # محاولة تحميل المحركات الاختيارية
        try:
            self.qsuper = get_quantum_superposition_engine()
        except Exception:
            self.qsuper = None
            logger.debug("QuantumSuperpositionEngine غير متوفر")
        
        # السياسات الافتراضية (لإعادة التهيئة)
        self._default_policies = {
            "base_field_strength": 0.2,
            "propagation_decay": 0.6,
            "propagation_radius": 2,
            "field_influence_on_transition": 0.25,
            "field_decay_per_cycle": 0.05,
            "noise_scale": 0.02,
        }
        self.policies = self._default_policies.copy()
        
        # الحقول الكمومية
        self.fields: Dict[str, QuantumFieldGrid] = {}
        self.active_field: Optional[QuantumFieldGrid] = None
        
        # خريطة الحقل السلمي (للتوافق مع الواجهة السابقة)
        self.field_map: Dict[str, float] = {}
        
        # تأثيرات الحقل
        self.field_effects: List[FieldEffect] = []
        
        # إحصائيات الحقل
        self.field_energy_history: List[float] = []
        
        # خلفيات الحقل
        self._active = True
        self._propagation_loop = threads.start_managed(self._continuous_propagation, owner=self)
        
        self._field_update_loop = threads.start_managed(self._continuous_field_update, owner=self)
        
        self._interference_calculator = threads.start_managed(self._calculate_interference_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("⚛️ محرك الحقل الكمي الجبار جاهز - حقول كمومية متكاملة")
    
    # ============================================================
    # إعادة التهيئة الكاملة (للاختبارات التكاملية)
    # ============================================================
    
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك الحقل الكمّي.
        
        - مسح خريطة الحقل field_map
        - إعادة تحميل الفهرس
        - إعادة السياسات الافتراضية
        - تسجيل عملية إعادة التهيئة في السجل السيادي
        """
        logger.info("🔄 إعادة تهيئة محرك الحقل الكمومي...")
        
        # مسح خريطة الحقل
        self.field_map.clear()
        
        # مسح الحقول النشطة
        self.fields.clear()
        self.active_field = None
        
        # مسح تأثيرات الحقل
        self.field_effects.clear()
        
        # إعادة تهيئة السياسات الافتراضية
        self.policies = self._default_policies.copy()
        
        # إعادة تعيين سجل الطاقة
        self.field_energy_history.clear()
        
        # تسجيل عملية إعادة التهيئة في السجل السيادي
        self.core.append_event(
            event_type="quantum::field::reset",
            payload={
                "timestamp": time.time(),
                "status": "quantum_field_engine_reset",
                "policies_reset": True,
                "data_cleared": True
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك الحقل الكمومي اكتملت")
    
    def reset_policies(self):
        """
        إعادة تعيين السياسات فقط (بدون مسح البيانات).
        
        مفيد عندما نريد الاحتفاظ بالحقل لكن إعادة ضبط السلوك.
        """
        self.policies = self._default_policies.copy()
        logger.debug("🔄 إعادة تعيين سياسات محرك الحقل الكمومي إلى القيم الافتراضية")
    
    # ============================================================
    # بناء الحقل الكمومي
    # ============================================================
    
    def create_field(self, name: str, dimensions: Tuple[int, int, int],
                    spacing: float = 1.0,
                    field_type: str = FIELD_TYPE_SCALAR) -> str:
        """
        إنشاء حقل كمومي جديد.
        
        Args:
            name: اسم الحقل
            dimensions: أبعاد الشبكة (x, y, z)
            spacing: المسافة بين النقاط
            field_type: نوع الحقل
        """
        field_id = f"qfield_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        # إنشاء نقاط الحقل
        points = {}
        
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                for z in range(dimensions[2]):
                    point_id = f"point_{x}_{y}_{z}"
                    
                    # إحداثيات في الفضاء
                    pos = (x * spacing, y * spacing, z * spacing)
                    
                    # قيمة عشوائية أولية
                    scalar_val = random.uniform(0.1, 0.9)
                    
                    # متجه عشوائي
                    vector_val = (
                        random.uniform(-1, 1),
                        random.uniform(-1, 1),
                        random.uniform(-1, 1)
                    )
                    
                    # طور عشوائي
                    phase = random.uniform(0, 2 * math.pi)
                    
                    # طاقة عشوائية
                    energy = random.uniform(0.1, 1.0)
                    
                    # تماسك عشوائي
                    coherence = random.uniform(0.3, 0.9)
                    
                    # تحديد الجيران (بسيط: جيران المانهاتن)
                    neighbors = []
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            for dz in [-1, 0, 1]:
                                if dx == 0 and dy == 0 and dz == 0:
                                    continue
                                nx, ny, nz = x + dx, y + dy, z + dz
                                if 0 <= nx < dimensions[0] and 0 <= ny < dimensions[1] and 0 <= nz < dimensions[2]:
                                    neighbors.append(f"point_{nx}_{ny}_{nz}")
                    
                    point = QuantumFieldPoint(
                        id=point_id,
                        position=pos,
                        scalar_value=scalar_val,
                        vector_value=vector_val,
                        phase=phase,
                        energy=energy,
                        coherence=coherence,
                        neighbors=neighbors,
                        distance_to_center=math.sqrt(x**2 + y**2 + z**2) * spacing
                    )
                    points[point_id] = point
        
        # بناء مصفوفة الانتشار (كـ dict)
        point_ids = list(points.keys())
        propagation_matrix = {}
        
        for pid1 in point_ids:
            propagation_matrix[pid1] = {}
            p1 = points[pid1]
            total = 0.0
            for pid2 in point_ids:
                p2 = points[pid2]
                dist = math.sqrt(sum((p1.position[k] - p2.position[k])**2 for k in range(3)))
                weight = math.exp(-dist**2 / (2 * spacing**2))
                propagation_matrix[pid1][pid2] = weight
                total += weight
            # تطبيع
            if total > 0:
                for pid2 in point_ids:
                    propagation_matrix[pid1][pid2] /= total
        
        field = QuantumFieldGrid(
            id=field_id,
            name=name,
            points=points,
            dimensions=dimensions,
            spacing=spacing,
            field_type=field_type,
            total_energy=sum(p.energy for p in points.values()),
            average_coherence=sum(p.coherence for p in points.values()) / len(points),
            propagation_matrix=propagation_matrix
        )
        
        self.fields[field_id] = field
        self.active_field = field
        
        # تحديث field_map للتوافق
        self._update_field_map()
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::field_created",
            payload={
                "field_id": field_id[:16],
                "name": name,
                "dimensions": dimensions,
                "points": len(points)
            }
        )
        
        logger.info(f"⚛️ إنشاء حقل كمومي: {name} ({len(points)} نقطة, {dimensions})")
        
        return field_id
    
    def _update_field_map(self):
        """تحديث خريطة الحقل السلمي من الحقل النشط"""
        if self.active_field:
            self.field_map = {
                point.id: point.scalar_value
                for point in self.active_field.points.values()
            }
    
    # ============================================================
    # نشر التأثيرات عبر الحقل
    # ============================================================
    
    def propagate_field(self, mode: str = PROPAGATION_MODE_QUANTUM,
                       steps: int = 1, source_point: str = None) -> Dict[str, float]:
        """
        نشر التأثيرات عبر الحقل الكمومي.
        
        يحاكي انتشار الموجات أو الجسيمات عبر بنية الحقل.
        """
        if not self.active_field:
            return {}
        
        points = self.active_field.points
        point_ids = list(points.keys())
        
        # الحالة الحالية
        current_state = {pid: points[pid].scalar_value for pid in point_ids}
        
        if mode == PROPAGATION_MODE_WAVE:
            # انتشار موجي
            new_state = {}
            for pid1 in point_ids:
                total = 0.0
                for pid2 in point_ids:
                    weight = self.active_field.propagation_matrix[pid1].get(pid2, 0)
                    total += weight * current_state[pid2]
                # إضافة تأثير طور
                phase = points[pid1].phase
                new_state[pid1] = total * abs(math.cos(phase))
            
        elif mode == PROPAGATION_MODE_DIFFUSION:
            # انتشار بالانتشار
            diffusion_rate = 0.1
            new_state = {}
            for pid1 in point_ids:
                laplacian = 0.0
                for pid2 in point_ids:
                    weight = self.active_field.propagation_matrix[pid1].get(pid2, 0)
                    if pid1 != pid2:
                        laplacian += weight * (current_state[pid2] - current_state[pid1])
                new_state[pid1] = current_state[pid1] + diffusion_rate * laplacian
            
        elif mode == PROPAGATION_MODE_BALLISTIC:
            # انتشار باليستي (حركة مستقيمة)
            if source_point and source_point in point_ids:
                source_val = current_state[source_point]
                source_pos = points[source_point].position
                new_state = {}
                for pid in point_ids:
                    if pid == source_point:
                        new_state[pid] = source_val
                        continue
                    point_pos = points[pid].position
                    dist = math.sqrt(sum((source_pos[k] - point_pos[k])**2 for k in range(3)))
                    if dist > 0:
                        new_state[pid] = source_val / (dist + 1)
                    else:
                        new_state[pid] = source_val
            else:
                new_state = current_state
                
        else:  # QUANTUM
            # انتشار كمومي مبسط
            new_state = {}
            for pid in point_ids:
                # تطور بسيط مع إضافة طور
                phase = points[pid].phase
                coherence = points[pid].coherence
                new_state[pid] = current_state[pid] * abs(math.cos(phase)) * coherence
        
        # تطبيع النتائج
        propagated = {}
        for pid in point_ids:
            old_val = points[pid].scalar_value
            new_val = max(0.0, min(1.0, new_state.get(pid, old_val)))
            points[pid].scalar_value = new_val
            propagated[pid] = new_val - old_val
            self.field_map[pid] = new_val
        
        # تحديث الطاقة الكلية
        self.active_field.total_energy = sum(p.energy for p in self.active_field.points.values())
        
        logger.debug(f"⚛️ نشر الحقل (نمط: {mode}, {steps} خطوة)")
        
        return propagated
    
    def _continuous_propagation(self):
        """نشر مستمر للحقل الكمومي"""
        while self._active:
            try:
                if self.active_field:
                    # اختيار نمط انتشار عشوائي
                    modes = [PROPAGATION_MODE_WAVE, PROPAGATION_MODE_DIFFUSION, PROPAGATION_MODE_QUANTUM]
                    mode = random.choice(modes)
                    self.propagate_field(mode=mode, steps=1)
                
                threads.interruptible_sleep(2)  # كل ثانيتين
            except Exception as e:
                logger.error(f"خطأ في نشر الحقل: {e}")
                threads.interruptible_sleep(2)
    
    # ============================================================
    # تحديث الحقل المستمر
    # ============================================================
    
    def update_field(self, source_state: str = "amplitudes"):
        """
        تحديث قيم الحقل بناءً على حالة النظام الكمومي.
        """
        if not self.active_field:
            return
        
        # جمع البيانات من مصادر مختلفة
        if source_state == "amplitudes":
            # من سعات الحالة الكمومية (محاكاة مبسطة)
            for point in self.active_field.points.values():
                # تحديث عشوائي بسيط
                point.scalar_value = max(0.1, min(0.9, point.scalar_value + random.uniform(-0.05, 0.05)))
        
        elif source_state == "superpositions" and self.qsuper:
            # من التراكبات (محاكاة مبسطة)
            for point in self.active_field.points.values():
                point.scalar_value = max(0.1, min(0.9, point.scalar_value + random.uniform(-0.03, 0.03)))
        
        elif source_state == "transitions":
            # من مصفوفة الانتقالات (محاكاة مبسطة)
            for point in self.active_field.points.values():
                point.scalar_value = max(0.1, min(0.9, point.scalar_value + random.uniform(-0.04, 0.04)))
        
        # تحديث الطاقة بناءً على قيم الحقل
        for point in self.active_field.points.values():
            point.energy = point.scalar_value
        
        self.active_field.total_energy = sum(p.energy for p in self.active_field.points.values())
        self._update_field_map()
    
    def _continuous_field_update(self):
        """تحديث مستمر للحقل"""
        while self._active:
            try:
                if self.active_field:
                    sources = ["amplitudes", "transitions"]
                    if self.qsuper:
                        sources.append("superpositions")
                    source = random.choice(sources)
                    self.update_field(source_state=source)
                
                threads.interruptible_sleep(5)  # كل 5 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في تحديث الحقل: {e}")
                threads.interruptible_sleep(5)
    
    # ============================================================
    # تداخلات متعددة النطاقات
    # ============================================================
    
    def calculate_interference(self, scale: int = 1) -> Dict[str, Any]:
        """
        حساب التداخل متعدد النطاقات.
        
        يحلل أنماط التداخل على مقاييس مختلفة.
        """
        if not self.active_field:
            return {}
        
        points = list(self.active_field.points.keys())
        values = [self.active_field.points[pid].scalar_value for pid in points]
        
        # تطبيق مرشح غاوسي بسيط لمقاييس مختلفة
        if len(values) > 1:
            smoothed = _safe_gaussian_filter(values, sigma=float(scale))
        else:
            smoothed = values
        
        # حساب نمط التداخل
        interference = [values[i] - smoothed[i] for i in range(len(values))]
        interference = [max(0.0, min(1.0, v)) for v in interference]
        
        # تحديد الأنماط
        patterns = []
        avg_intensity = sum(interference) / len(interference) if interference else 0
        
        if avg_intensity > 0.3:
            patterns.append({
                "type": "constructive",
                "scale": scale,
                "intensity": float(avg_intensity),
                "description": "تداخل بنّاء على هذا المقياس"
            })
        elif avg_intensity < -0.1:
            patterns.append({
                "type": "destructive",
                "scale": scale,
                "intensity": float(abs(avg_intensity)),
                "description": "تداخل هدّام على هذا المقياس"
            })
        
        return {
            "scale": scale,
            "interference": interference[:100] if len(interference) > 100 else interference,
            "patterns": patterns,
            "avg_intensity": float(avg_intensity)
        }
    
    def multi_scale_interference(self, scales: List[int] = None) -> List[Dict[str, Any]]:
        """
        تحليل التداخل على مقاييس متعددة.
        """
        if scales is None:
            scales = [1, 2, 3, 5, 10]
        
        results = []
        for scale in scales:
            result = self.calculate_interference(scale)
            results.append(result)
        
        return results
    
    def _calculate_interference_loop(self):
        """حساب مستمر للتداخل"""
        while self._active:
            try:
                if self.active_field:
                    self.multi_scale_interference()
                
                threads.interruptible_sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في حساب التداخل: {e}")
                threads.interruptible_sleep(30)
    
    # ============================================================
    # تأثير الحقل على الانتقالات
    # ============================================================
    
    def apply_field_to_transitions(self, matrix: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """
        تطبيق تأثير الحقل على مصفوفة الانتقالات.
        
        يعدل احتمالات الانتقال بناءً على قيم الحقل.
        """
        if not self.active_field:
            return matrix
        
        influenced = {}
        field_strength = self.policies.get("base_field_strength", 0.2)
        
        for s1, row in matrix.items():
            influenced[s1] = {}
            for s2, prob in row.items():
                # الحصول على قيم الحقل للنقطتين
                f1 = self.field_map.get(s1, 0.5)
                f2 = self.field_map.get(s2, 0.5)
                
                # تعديل الاحتمال
                delta = (f2 - f1) * field_strength
                new_prob = prob + delta
                
                # تأثير إضافي من التداخل
                interference_result = self.calculate_interference(scale=2)
                if interference_result.get("avg_intensity", 0) > 0.2:
                    new_prob *= (1 + interference_result["avg_intensity"] * 0.1)
                
                influenced[s1][s2] = float(max(0.0, min(1.0, new_prob)))
        
        return influenced
    
    # ============================================================
    # تلاشي الحقل (Decay)
    # ============================================================
    
    def decay_field(self, rate: float = 0.02):
        """
        تلاشي الحقل بمرور الزمن (محاكاة فك الترابط).
        """
        if not self.active_field:
            return
        
        for point in self.active_field.points.values():
            # تلاشي السعة
            point.scalar_value = max(0.05, point.scalar_value * (1 - rate))
            
            # تلاشي التماسك
            point.coherence = max(0.1, point.coherence * (1 - rate * 0.5))
            
            # تلاشي الطاقة
            point.energy = max(0.05, point.energy * (1 - rate))
        
        if self.active_field.points:
            self.active_field.average_coherence = sum(p.coherence for p in self.active_field.points.values()) / len(self.active_field.points)
        self.active_field.total_energy = sum(p.energy for p in self.active_field.points.values())
        self._update_field_map()
    
    # ============================================================
    # دورة حقل كمومي كاملة
    # ============================================================
    
    def field_cycle(self) -> QuantumFieldSnapshot:
        """
        دورة حقل كمومي كاملة.
        
        1. تحديث الحقل من حالة النظام
        2. نشر التأثيرات
        3. حساب التداخل متعدد النطاقات
        4. تطبيق التأثير على الانتقالات
        5. تلاشي الحقل
        """
        if not self.active_field:
            # إنشاء حقل افتراضي إذا لم يكن موجوداً
            self.create_field("default_field", (5, 5, 1), spacing=1.0)
        
        # تحديث الحقل
        self.update_field(source_state="amplitudes")
        
        # نشر التأثيرات
        propagated = self.propagate_field(mode=PROPAGATION_MODE_QUANTUM, steps=1)
        
        # حساب التداخل متعدد النطاقات
        interference_patterns = self.multi_scale_interference([1, 2, 3])
        
        # تطبيق التأثير على الانتقالات (محاكاة مبسطة)
        influenced = {}
        
        # تلاشي الحقل
        decay_rate = self.policies.get("field_decay_per_cycle", 0.01)
        self.decay_field(rate=decay_rate)
        
        # حساب إحصائيات الحقل
        field_energy = self.active_field.total_energy
        avg_coherence = self.active_field.average_coherence
        propagation_speed = 0.5  # قيمة افتراضية
        
        # سرد
        narrative = self.generate_field_narrative(field_energy, avg_coherence, interference_patterns)
        
        snapshot = QuantumFieldSnapshot(
            timestamp=time.time(),
            field_map=self.field_map.copy(),
            propagated_effects=propagated,
            influenced_transitions=influenced,
            field_energy=field_energy,
            average_coherence=avg_coherence,
            propagation_speed=propagation_speed,
            interference_patterns=interference_patterns,
            narrative=narrative
        )
        
        self.field_energy_history.append(field_energy)
        if len(self.field_energy_history) > 100:
            self.field_energy_history = self.field_energy_history[-100:]
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::field_cycle",
            payload={
                "field_name": self.active_field.name,
                "points": len(self.active_field.points),
                "energy": field_energy,
                "coherence": avg_coherence
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    def generate_field_narrative(self, energy: float, coherence: float,
                                  interference_patterns: List[Dict]) -> str:
        """
        توليد سرد للحقل الكمومي.
        """
        narrative = f"⚛️ **الحقل الكمومي**: {self.active_field.name if self.active_field else 'نشط'}\n"
        narrative += f"💥 **الطاقة الكلية**: {energy:.3f}\n"
        narrative += f"🌀 **متوسط التماسك**: {coherence:.1%}\n"
        
        # أنماط التداخل
        constructive = [p for p in interference_patterns if p.get("patterns")]
        if constructive:
            narrative += f"🌊 **تداخل بنّاء** على {len(constructive)} مقياس\n"
        else:
            narrative += "📊 **لا تداخل كبير** مكتشف\n"
        
        # اتجاه الطاقة
        if len(self.field_energy_history) > 1:
            trend = self.field_energy_history[-1] - self.field_energy_history[-2]
            if trend > 0:
                narrative += "⬆️ طاقة الحقل في ازدياد\n"
            elif trend < 0:
                narrative += "⬇️ طاقة الحقل في تناقص\n"
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة الحقل الكمومي"""
        try:
            state = {
                "fields_count": len(self.fields),
                "active_field_id": self.active_field.id if self.active_field else None,
                "energy_history": self.field_energy_history[-50:],
                "policies": self.policies,
                "saved_at": time.time()
            }
            atomic_write_json(QUANTUM_FIELD_STATE_FILE, state, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الحقل: {e}")
    
    def _load_state(self):
        """تحميل حالة الحقل الكمومي"""
        try:
            if QUANTUM_FIELD_STATE_FILE.exists():
                with open(QUANTUM_FIELD_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.field_energy_history = state.get("energy_history", [])
                    saved_policies = state.get("policies", {})
                    if saved_policies:
                        self.policies.update(saved_policies)
                logger.info("📂 تم تحميل حالة الحقل الكمومي")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الحقل: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_policy(self, key: str, value: float) -> bool:
        """
        تعيين سياسة تشغيلية.
        
        Args:
            key: اسم السياسة (base_field_strength, propagation_decay, etc.)
            value: القيمة الجديدة
        """
        if key in self.policies:
            self.policies[key] = value
            logger.debug(f"⚙️ تحديث السياسة {key} = {value}")
            return True
        return False
    
    def get_policies(self) -> Dict[str, float]:
        """الحصول على نسخة من السياسات الحالية"""
        return self.policies.copy()
    
    def get_field_status(self) -> Dict[str, Any]:
        """الحالة الحالية للحقل الكمومي"""
        if not self.active_field:
            return {"status": "no_active_field"}
        
        return {
            "field_name": self.active_field.name,
            "field_id": self.active_field.id[:16],
            "points_count": len(self.active_field.points),
            "dimensions": self.active_field.dimensions,
            "field_type": self.active_field.field_type,
            "total_energy": self.active_field.total_energy,
            "average_coherence": self.active_field.average_coherence,
            "policies": self.policies,
            "timestamp": time.time()
        }
    
    def get_field_map(self) -> Dict[str, float]:
        """خريطة الحقل الحالية"""
        return self.field_map.copy()
    
    def get_field_energy_history(self) -> List[float]:
        """سجل طاقة الحقل"""
        return self.field_energy_history.copy()
    
    def get_interference_patterns(self) -> List[Dict]:
        """أنماط التداخل الحالية"""
        return self.multi_scale_interference()
    
    def excite_field(self, point_id: str, intensity: float = 1.0) -> bool:
        """إثارة نقطة معينة في الحقل"""
        if not self.active_field or point_id not in self.active_field.points:
            return False
        
        point = self.active_field.points[point_id]
        point.scalar_value = min(1.0, point.scalar_value + intensity)
        point.energy = point.scalar_value
        
        self._update_field_map()
        
        logger.info(f"⚛️ إثارة نقطة {point_id[:16]} في الحقل (شدة {intensity:.1%})")
        
        return True
    
    def get_field_quote(self) -> str:
        """اقتباس عن الحقل الكمومي"""
        quotes = [
            "الحقل الكمومي هو نسيج الواقع.",
            "النشر يخلق ترابطاً غير محلي.",
            "التداخل متعدد النطاقات يلتقط أنماطاً خفية.",
            "الحقل يؤثر على كل شيء، وكل شيء يؤثر على الحقل.",
            "طاقة الحقل تحدد قوة التأثيرات.",
            "التماسك هو مقياس كمومية الحقل.",
            "الحقل الحي يتفاعل وينتشر ويتغير باستمرار."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محرك الحقل الكمومي"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف محرك الحقل الكمومي")


# ============================================================
# الـ Singleton
# ============================================================

_qfield_instance: Optional[QuantumFieldEngine] = None
_qfield_lock = threading.Lock()


def get_quantum_field_engine() -> QuantumFieldEngine:
    """الحصول على النسخة الوحيدة من محرك الحقل الكمومي"""
    global _qfield_instance
    if _qfield_instance is None:
        with _qfield_lock:
            if _qfield_instance is None:
                _qfield_instance = QuantumFieldEngine()
    return _qfield_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("⚛️ محرك الحقل الكمومي الجبار - حقول كمومية متكاملة")
    print("=" * 80 + "\n")
    
    qfield = get_quantum_field_engine()
    
    # 1) إنشاء حقل كمومي
    print("⚛️ إنشاء حقل كمومي...")
    field_id = qfield.create_field(
        name="حقل الوعي الكمومي",
        dimensions=(5, 5, 1),
        spacing=1.0,
        field_type=FIELD_TYPE_SCALAR
    )
    print(f"   معرف الحقل: {field_id[:16]}...")
    
    # 2) حالة الحقل
    print("\n📊 حالة الحقل:")
    status = qfield.get_field_status()
    if "status" not in status:
        print(f"   الاسم: {status['field_name']}")
        print(f"   النقاط: {status['points_count']}")
        print(f"   الطاقة: {status['total_energy']:.3f}")
        print(f"   التماسك: {status['average_coherence']:.1%}")
    
    # 3) نشر الحقل
    print("\n🌀 نشر الحقل...")
    propagated = qfield.propagate_field(mode="wave", steps=2)
    if propagated:
        print(f"   عدد النقاط المتأثرة: {len(propagated)}")
        avg_change = sum(abs(v) for v in propagated.values()) / len(propagated)
        print(f"   متوسط التغير: {avg_change:.4f}")
    
    # 4) إثارة نقطة
    print("\n⚡ إثارة نقطة في الحقل...")
    if qfield.active_field and qfield.active_field.points:
        sample_point = list(qfield.active_field.points.keys())[0]
        qfield.excite_field(sample_point, intensity=0.8)
        print(f"   تم إثارة: {sample_point[:16]}...")
    
    # 5) تداخل متعدد النطاقات
    print("\n🌊 تحليل التداخل متعدد النطاقات...")
    patterns = qfield.multi_scale_interference([1, 2, 3])
    for p in patterns:
        print(f"   مقياس {p['scale']}: كثافة {p['avg_intensity']:.3f}")
        if p.get('patterns'):
            print(f"      {p['patterns'][0]['description']}")
    
    # 6) دورة حقل كاملة
    print("\n🔄 دورة حقل كمومي...")
    snapshot = qfield.field_cycle()
    print(f"   طاقة الحقل: {snapshot.field_energy:.3f}")
    print(f"   تماسك الحقل: {snapshot.average_coherence:.1%}")
    print(f"   أنماط التداخل: {len(snapshot.interference_patterns)}")
    
    # 7) خريطة الحقل
    print("\n🗺️ عينة من خريطة الحقل:")
    field_map = qfield.get_field_map()
    sample_items = list(field_map.items())[:5]
    for point, value in sample_items:
        print(f"   {point[:16]}...: {value:.3f}")
    
    # 8) سجل الطاقة
    print("\n📈 سجل طاقة الحقل:")
    energy_history = qfield.get_field_energy_history()
    if energy_history:
        print(f"   الطاقة الحالية: {energy_history[-1]:.3f}")
        print(f"   ذروة الطاقة: {max(energy_history):.3f}")
    
    # 9) اختبار إعادة التهيئة
    print("\n🔄 اختبار إعادة تهيئة محرك الحقل...")
    qfield.reset()
    print("   تم إعادة تهيئة محرك الحقل بنجاح - الحالة نظيفة وجاهزة للاختبارات")
    
    # 10) السرد
    print(f"\n📖 السرد:\n{snapshot.narrative}")
    
    # 11) اقتباس
    print(f"\n💭 {qfield.get_field_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك الحقل الكمومي الجبار جاهز - حقول كمومية متكاملة")
    print("=" * 80)
