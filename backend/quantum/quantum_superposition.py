# backend/quantum/quantum_superposition.py
# ⚛️ محرك التراكب الكمي الجبار - تراكبات متعددة المستويات، دمج، تقسيم، تداخل جماعي
# الإصدار: 3.1.0 - مع دعم إعادة التهيئة الكاملة للاختبارات التكاملية

"""
محرك التراكب الكمي للعقل السيادي.

الفلسفة:
- التراكب يسمح بوجود متزامن في حالات متعددة
- التراكبات المتداخلة تخلق هياكل هرمية من الاحتمالات
- الدمج يسمح بتجميع التراكبات الفرعية
- القياس الجزئي يسمح باستخراج معلومات دون انهيار كامل
- التداخل الجماعي يخلق أنماطاً تعاونية بين الحالات

هذه ليست مجرد تراكبات. هذه هي عوالم الاحتمالات المتداخلة.
"""

import json
from runtime.atomic_json import atomic_write_json  # R-781
import math
import random
import secrets
import threading
import runtime.threads as threads
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

try:
    from ..memory.core import get_core, EventType
    from .quantum_state import get_quantum_state_engine, QuantumAmplitude
    from .quantum_transition import get_quantum_transition_engine
    from ..config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from .quantum_state import get_quantum_state_engine, QuantumAmplitude
    from .quantum_transition import get_quantum_transition_engine
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات التراكب الكمومي
# ============================================================

QUANTUM_SUPERPOSITION_DIR = DATA_DIR / "quantum" / "superposition"
QUANTUM_SUPERPOSITION_DIR.mkdir(parents=True, exist_ok=True)
QUANTUM_SUPERPOSITION_LOG = QUANTUM_SUPERPOSITION_DIR / "quantum_superposition_log.jsonl"
QUANTUM_SUPERPOSITION_STATE_FILE = QUANTUM_SUPERPOSITION_DIR / "quantum_superposition_state.json"

# مستويات التراكب
SUPERPOSITION_LEVEL_BASIC = 1       # مستوى أساسي (حالات بسيطة)
SUPERPOSITION_LEVEL_NESTED = 2      # مستوى متداخل (تراكبات داخل تراكبات)
SUPERPOSITION_LEVEL_COMPLEX = 3     # مستوى معقد (تراكبات هرمية متعددة)
SUPERPOSITION_LEVEL_HIERARCHICAL = 4  # مستوى هرمي (هياكل شجرية)
SUPERPOSITION_LEVEL_QUANTUM_FIELD = 5  # مستوى حقل كمومي (كل شيء متراكب)

# أنواع الدمج
MERGE_TYPE_ADDITIVE = "additive"        # جمعي (مجموع السعات)
MERGE_TYPE_MULTIPLICATIVE = "multiplicative"  # ضربي (جداء السعات)
MERGE_TYPE_INTERFERING = "interfering"  # تداخلي (مع حساب التداخل)
MERGE_TYPE_COHERENT = "coherent"        # متماسك (حفظ الطور النسبي)


@dataclass
class NestedSuperposition:
    """تراكب متداخل"""
    id: str
    name: str
    level: int
    parent_id: Optional[str]
    children: List[str]
    amplitudes: Dict[str, QuantumAmplitude]
    phase_coherence: float
    entanglement_degree: float


@dataclass
class SuperpositionGroup:
    """مجموعة تراكب للتداخل الجماعي"""
    id: str
    name: str
    members: List[str]
    interference_strength: float
    collective_phase: float
    synergy: float


@dataclass
class PartialMeasurementResult:
    """نتيجة قياس جزئي"""
    id: str
    superposition_id: str
    measured_states: List[str]
    outcomes: Dict[str, float]
    collapse_occurred: bool
    collapsed_state: Optional[str]
    remaining_coherence: float
    timestamp: float


@dataclass
class SuperpositionSnapshot:
    """لقطة تراكب"""
    timestamp: float
    superpositions: Dict[str, Dict[str, float]]
    nested_superpositions: List[Dict[str, Any]]
    active_groups: List[Dict[str, Any]]
    partial_measurements: List[Dict[str, Any]]
    total_amplitude: float
    average_coherence: float
    entanglement_entropy: float
    narrative: str


# ============================================================
# محرك التراكب الكمي الجبار
# ============================================================

class QuantumSuperpositionEngine:
    """
    محرك التراكب الكمي الجبار - تراكبات متعددة المستويات، دمج، تقسيم، تداخل جماعي.
    
    المبادئ:
    1. التراكب يسمح بوجود متزامن في حالات متعددة
    2. التراكبات المتداخلة تخلق هياكل هرمية
    3. الدمج يسمح بتجميع التراكبات الفرعية
    4. القياس الجزئي يستخرج معلومات دون انهيار كامل
    5. التداخل الجماعي يخلق أنماطاً تعاونية
    """
    
    def __init__(self):
        self.core = get_core()
        self.qstate = get_quantum_state_engine()
        self.qtrans = get_quantum_transition_engine()
        
        # السياسات الافتراضية (لإعادة التهيئة)
        self._default_policies = {
            "group_interference_strength": 0.12,
            "partial_measure_base_collapse": 0.35,
            "merge_normalize": True,
        }
        self.policies = self._default_policies.copy()
        
        # التراكبات
        self.superpositions: Dict[str, Dict[str, QuantumAmplitude]] = {}
        self.nested_superpositions: Dict[str, NestedSuperposition] = {}
        self.superposition_groups: Dict[str, SuperpositionGroup] = {}
        
        # سجل القياسات الجزئية
        self.partial_measurements: List[PartialMeasurementResult] = []
        
        # خلفيات التراكب
        self._active = True
        self._coherence_maintenance = threads.start_managed(self._maintain_coherence_loop, owner=self)
        
        self._interference_loop = threads.start_managed(self._continuous_interference_loop, owner=self)
        
        self._nesting_optimizer = threads.start_managed(self._optimize_nesting_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("⚛️ محرك التراكب الكمي الجبار جاهز - تراكبات متعددة المستويات")
    
    # ============================================================
    # إعادة التهيئة الكاملة (للاختبارات التكاملية)
    # ============================================================
    
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك التراكب الكمّي.
        
        - مسح جميع التراكبات
        - مسح المجموعات النشطة
        - مسح تاريخ القياسات الجزئية
        - إعادة تحميل الفهرس
        - إعادة السياسات الافتراضية
        - تسجيل عملية إعادة التهيئة في السجل السيادي
        """
        logger.info("🔄 إعادة تهيئة محرك التراكب الكمومي...")
        
        # مسح التراكبات بالكامل
        self.superpositions.clear()
        
        # مسح المجموعات النشطة
        self.superposition_groups.clear()
        self.nested_superpositions.clear()
        
        # مسح تاريخ القياسات الجزئية
        self.partial_measurements.clear()
        
        # إعادة تهيئة السياسات الافتراضية
        self.policies = self._default_policies.copy()
        
        # تسجيل عملية إعادة التهيئة في السجل السيادي
        self.core.append_event(
            event_type="quantum::superposition::reset",
            payload={
                "timestamp": time.time(),
                "status": "quantum_superposition_engine_reset",
                "policies_reset": True,
                "data_cleared": True
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك التراكب الكمومي اكتملت")
    
    def reset_policies(self):
        """
        إعادة تعيين السياسات فقط (بدون مسح البيانات).
        
        مفيد عندما نريد الاحتفاظ بالتراكبات لكن إعادة ضبط السلوك.
        """
        self.policies = self._default_policies.copy()
        logger.debug("🔄 إعادة تعيين سياسات محرك التراكب الكمومي إلى القيم الافتراضية")
    
    # ============================================================
    # إدارة التراكبات الأساسية
    # ============================================================
    
    def create_superposition(self, name: str, amplitudes: Dict[str, complex]) -> str:
        """
        إنشاء تراكب كمومي جديد.
        
        Args:
            name: اسم التراكب
            amplitudes: قاموس الحالات -> السعة المركبة
        """
        super_id = f"super_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        # تحويل السعات إلى كائنات QuantumAmplitude
        quantum_amps = {}
        for state, amp in amplitudes.items():
            quantum_amps[state] = QuantumAmplitude.from_complex(amp)
        
        # تطبيع التراكب
        quantum_amps = self._normalize_amplitudes(quantum_amps)
        
        self.superpositions[super_id] = quantum_amps
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::superposition_created",
            payload={
                "super_id": super_id[:16],
                "name": name,
                "dimension": len(quantum_amps)
            }
        )
        
        logger.info(f"⚛️ إنشاء تراكب: {name} (بُعد {len(quantum_amps)})")
        
        return super_id
    
    def _normalize_amplitudes(self, amplitudes: Dict[str, QuantumAmplitude]) -> Dict[str, QuantumAmplitude]:
        """تطبيع سعات التراكب"""
        total_prob = sum(amp.probability() for amp in amplitudes.values())
        
        if total_prob == 0:
            return amplitudes
        
        norm_factor = math.sqrt(total_prob)
        
        normalized = {}
        for state, amp in amplitudes.items():
            normalized[state] = QuantumAmplitude(
                real=amp.real / norm_factor,
                imag=amp.imag / norm_factor
            )
        
        return normalized
    
    def get_superposition(self, super_id: str) -> Optional[Dict[str, float]]:
        """الحصول على احتمالات التراكب"""
        sp = self.superpositions.get(super_id)
        if not sp:
            return None
        
        return {state: amp.probability() for state, amp in sp.items()}
    
    # ============================================================
    # تراكبات متداخلة (Nested Superpositions)
    # ============================================================
    
    def create_nested_superposition(self, name: str, super_ids: List[str],
                                    weights: List[float] = None) -> str:
        """
        إنشاء تراكب متداخل - تراكب من تراكبات فرعية.
        
        يسمح بتركيب هرمي للحالات الكمومية.
        """
        if weights is None:
            weights = [1.0 / len(super_ids)] * len(super_ids)
        
        nested_id = f"nested_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        # جمع السعات من التراكبات الفرعية
        total_amplitudes = {}
        for sup_id, weight in zip(super_ids, weights):
            sp = self.superpositions.get(sup_id)
            if sp:
                for state, amp in sp.items():
                    weighted_amp = QuantumAmplitude(
                        real=amp.real * weight,
                        imag=amp.imag * weight
                    )
                    if state in total_amplitudes:
                        total_amplitudes[state] = QuantumAmplitude(
                            real=total_amplitudes[state].real + weighted_amp.real,
                            imag=total_amplitudes[state].imag + weighted_amp.imag
                        )
                    else:
                        total_amplitudes[state] = weighted_amp
        
        # تطبيع
        total_amplitudes = self._normalize_amplitudes(total_amplitudes)
        
        # إنشاء التراكب المتداخل
        nested = NestedSuperposition(
            id=nested_id,
            name=name,
            level=SUPERPOSITION_LEVEL_NESTED,
            parent_id=None,
            children=super_ids,
            amplitudes=total_amplitudes,
            phase_coherence=0.7,
            entanglement_degree=0.5
        )
        
        self.nested_superpositions[nested_id] = nested
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::nested_superposition_created",
            payload={
                "nested_id": nested_id[:16],
                "name": name,
                "children": len(super_ids)
            }
        )
        
        logger.info(f"⚛️ إنشاء تراكب متداخل: {name} (مكون من {len(super_ids)} تراكب)")
        
        return nested_id
    
    def add_to_nested(self, parent_id: str, child_id: str, weight: float = 0.5) -> bool:
        """
        إضافة تراكب فرعي إلى تراكب متداخل موجود.
        """
        parent = self.nested_superpositions.get(parent_id)
        if not parent:
            return False
        
        child_sp = self.superpositions.get(child_id)
        if not child_sp:
            return False
        
        # دمج سعات الطفل
        for state, amp in child_sp.items():
            weighted_amp = QuantumAmplitude(
                real=amp.real * weight,
                imag=amp.imag * weight
            )
            if state in parent.amplitudes:
                parent.amplitudes[state] = QuantumAmplitude(
                    real=parent.amplitudes[state].real + weighted_amp.real,
                    imag=parent.amplitudes[state].imag + weighted_amp.imag
                )
            else:
                parent.amplitudes[state] = weighted_amp
        
        # تحديث القائمة
        if child_id not in parent.children:
            parent.children.append(child_id)
        
        # إعادة تطبيع
        parent.amplitudes = self._normalize_amplitudes(parent.amplitudes)
        parent.level = min(SUPERPOSITION_LEVEL_QUANTUM_FIELD, parent.level + 1)
        
        logger.info(f"⚛️ إضافة تراكب إلى متداخل: {child_id[:16]} → {parent.name}")
        
        return True
    
    # ============================================================
    # دمج وتقسيم التراكبات
    # ============================================================
    
    def merge_superpositions(self, target_id: str, source_ids: List[str],
                            merge_type: str = MERGE_TYPE_ADDITIVE) -> bool:
        """
        دمج عدة تراكبات في تراكب واحد.
        """
        target_sp = self.superpositions.get(target_id)
        if not target_sp:
            target_sp = {}
        
        for src_id in source_ids:
            src_sp = self.superpositions.get(src_id)
            if not src_sp:
                continue
            
            for state, amp in src_sp.items():
                if merge_type == MERGE_TYPE_ADDITIVE:
                    if state in target_sp:
                        target_sp[state] = QuantumAmplitude(
                            real=target_sp[state].real + amp.real,
                            imag=target_sp[state].imag + amp.imag
                        )
                    else:
                        target_sp[state] = QuantumAmplitude(amp.real, amp.imag)
                
                elif merge_type == MERGE_TYPE_MULTIPLICATIVE:
                    if state in target_sp:
                        target_sp[state] = QuantumAmplitude(
                            real=target_sp[state].real * amp.real,
                            imag=target_sp[state].imag * amp.imag
                        )
                    else:
                        target_sp[state] = QuantumAmplitude(amp.real, amp.imag)
                
                elif merge_type == MERGE_TYPE_INTERFERING:
                    # تداخل مع حساب الطور النسبي
                    target_amp = target_sp.get(state, QuantumAmplitude(0, 0))
                    phase_diff = amp.phase() - target_amp.phase()
                    interference = math.cos(phase_diff)
                    if state in target_sp:
                        target_sp[state] = QuantumAmplitude(
                            real=target_sp[state].real + amp.real * interference,
                            imag=target_sp[state].imag + amp.imag * interference
                        )
                    else:
                        target_sp[state] = QuantumAmplitude(amp.real * interference, amp.imag * interference)
        
        # تطبيع
        target_sp = self._normalize_amplitudes(target_sp)
        self.superpositions[target_id] = target_sp
        
        logger.info(f"⚛️ دمج {len(source_ids)} تراكب في {target_id[:16]} (نوع: {merge_type})")
        
        return True
    
    def split_superposition(self, super_id: str, partition: Dict[str, List[str]]) -> List[str]:
        """
        تقسيم تراكب إلى عدة تراكبات فرعية حسب التقسيم.
        
        partition: {new_super_name: [states]}
        """
        sp = self.superpositions.get(super_id)
        if not sp:
            return []
        
        new_ids = []
        
        for new_name, states in partition.items():
            new_amps = {}
            for state in states:
                if state in sp:
                    new_amps[state] = QuantumAmplitude(sp[state].real, sp[state].imag)
            
            if new_amps:
                new_id = self.create_superposition(new_name, 
                    {s: complex(new_amps[s].real, new_amps[s].imag) for s in new_amps})
                new_ids.append(new_id)
        
        logger.info(f"⚛️ تقسيم التراكب {super_id[:16]} إلى {len(new_ids)} تراكب فرعي")
        
        return new_ids
    
    # ============================================================
    # المجموعات والتداخل الجماعي
    # ============================================================
    
    def define_group(self, name: str, member_ids: List[str],
                    interference_strength: float = 0.1) -> str:
        """
        تعريف مجموعة تراكب للتداخل الجماعي.
        """
        group_id = f"group_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        group = SuperpositionGroup(
            id=group_id,
            name=name,
            members=member_ids,
            interference_strength=interference_strength,
            collective_phase=random.uniform(0, 2 * math.pi),
            synergy=0.5
        )
        
        self.superposition_groups[group_id] = group
        
        logger.info(f"⚛️ تعريف مجموعة تراكب: {name} ({len(member_ids)} عضو)")
        
        return group_id
    
    def apply_group_interference(self, group_id: str) -> bool:
        """
        تطبيق تداخل جماعي على مجموعة تراكبات.
        
        يخلق أنماطاً تعاونية بين التراكبات في المجموعة.
        """
        group = self.superposition_groups.get(group_id)
        if not group:
            return False
        
        # حساب متوسط الطور الجماعي
        phases = []
        for member_id in group.members:
            sp = self.superpositions.get(member_id)
            if sp:
                avg_phase = sum(amp.phase() for amp in sp.values()) / len(sp) if sp else 0
                phases.append(avg_phase)
        
        if phases:
            group.collective_phase = sum(phases) / len(phases)
        
        # تطبيق التداخل على كل عضو
        for member_id in group.members:
            sp = self.superpositions.get(member_id)
            if sp:
                for state, amp in sp.items():
                    # تعديل الطور نحو الطور الجماعي
                    phase_diff = group.collective_phase - amp.phase()
                    phase_shift = phase_diff * group.interference_strength
                    new_real = amp.real * math.cos(phase_shift) - amp.imag * math.sin(phase_shift)
                    new_imag = amp.real * math.sin(phase_shift) + amp.imag * math.cos(phase_shift)
                    sp[state] = QuantumAmplitude(new_real, new_imag)
                
                # إعادة تطبيع
                sp = self._normalize_amplitudes(sp)
                self.superpositions[member_id] = sp
        
        # زيادة التآزر
        group.synergy = min(1.0, group.synergy + 0.05)
        
        logger.debug(f"⚛️ تداخل جماعي على {group.name} (قوة {group.interference_strength:.1%})")
        
        return True
    
    def _continuous_interference_loop(self):
        """تطبيق تداخل جماعي مستمر"""
        while self._active:
            try:
                for group in self.superposition_groups.values():
                    if random.random() < 0.3:
                        self.apply_group_interference(group.id)
                
                threads.interruptible_sleep(10)  # كل 10 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في حلقة التداخل الجماعي: {e}")
                threads.interruptible_sleep(10)
    
    # ============================================================
    # قياسات جزئية
    # ============================================================
    
    def partial_measure(self, super_id: str, states_to_measure: List[str],
                        collapse_probability: float = 0.3) -> Optional[PartialMeasurementResult]:
        """
        قياس جزئي - قياس مجموعة فرعية من الحالات دون انهيار كامل.
        """
        sp = self.superpositions.get(super_id)
        if not sp:
            return None
        
        # حساب احتمالات الحالات المطلوب قياسها
        probs = {state: sp[state].probability() for state in states_to_measure if state in sp}
        total_prob = sum(probs.values())
        
        if total_prob == 0:
            return None
        
        # تطبيع الاحتمالات
        normalized_probs = {s: p / total_prob for s, p in probs.items()}
        
        # قرار الانهيار
        collapse_occurred = random.random() < collapse_probability
        collapsed_state = None
        
        if collapse_occurred:
            # اختيار حالة عشوائية حسب الاحتمالات
            states = list(normalized_probs.keys())
            weights = list(normalized_probs.values())
            collapsed_state = random.choices(states, weights=weights, k=1)[0]
            
            # تحديث السعات: الحالة المختارة تصبح 1، الباقي 0
            for state in states_to_measure:
                if state in sp:
                    if state == collapsed_state:
                        sp[state] = QuantumAmplitude(1.0, 0.0)
                    else:
                        sp[state] = QuantumAmplitude(0.0, 0.0)
        else:
            # تحديث الطور للحالات المقاسة (تأثير القياس دون انهيار)
            for state in states_to_measure:
                if state in sp:
                    phase_shift = random.uniform(-0.1, 0.1)
                    amp = sp[state]
                    new_real = amp.real * math.cos(phase_shift) - amp.imag * math.sin(phase_shift)
                    new_imag = amp.real * math.sin(phase_shift) + amp.imag * math.cos(phase_shift)
                    sp[state] = QuantumAmplitude(new_real, new_imag)
        
        # إعادة تطبيع
        sp = self._normalize_amplitudes(sp)
        self.superpositions[super_id] = sp
        
        # حساب التماسك المتبقي
        remaining_coherence = self._calculate_coherence(sp)
        
        result = PartialMeasurementResult(
            id=f"pm_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            superposition_id=super_id,
            measured_states=states_to_measure,
            outcomes=normalized_probs,
            collapse_occurred=collapse_occurred,
            collapsed_state=collapsed_state,
            remaining_coherence=remaining_coherence,
            timestamp=time.time()
        )
        
        self.partial_measurements.append(result)
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::partial_measurement",
            payload={
                "super_id": super_id[:16],
                "states": states_to_measure,
                "collapsed": collapse_occurred,
                "result": collapsed_state
            }
        )
        
        logger.info(f"⚛️ قياس جزئي على {super_id[:16]}: {len(states_to_measure)} حالة, {'انهيار' if collapse_occurred else 'لا انهيار'}")
        
        return result
    
    def _calculate_coherence(self, amplitudes: Dict[str, QuantumAmplitude]) -> float:
        """حساب التماسك الكمي للتراكب"""
        if len(amplitudes) < 2:
            return 1.0
        
        coherence = 0.0
        states = list(amplitudes.keys())
        
        for i in range(len(states)):
            for j in range(i + 1, len(states)):
                amp_i = amplitudes[states[i]]
                amp_j = amplitudes[states[j]]
                coherence += abs(amp_i.real * amp_j.real + amp_i.imag * amp_j.imag)
        
        max_coherence = len(states) * (len(states) - 1) / 2
        if max_coherence > 0:
            coherence /= max_coherence
        
        return min(1.0, coherence)
    
    # ============================================================
    # صيانة التماسك
    # ============================================================
    
    def _maintain_coherence_loop(self):
        """صيانة مستمرة لتماسك التراكبات"""
        while self._active:
            try:
                for super_id, sp in self.superpositions.items():
                    coherence = self._calculate_coherence(sp)
                    
                    # فك الترابط الطبيعي
                    if coherence > 0:
                        decay = 0.01
                        for state, amp in sp.items():
                            amp.real *= (1 - decay)
                            amp.imag *= (1 - decay)
                        
                        sp = self._normalize_amplitudes(sp)
                        self.superpositions[super_id] = sp
                
                threads.interruptible_sleep(5)  # كل 5 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في صيانة التماسك: {e}")
                threads.interruptible_sleep(5)
    
    def _optimize_nesting_loop(self):
        """تحسين هيكل التراكبات المتداخلة"""
        while self._active:
            try:
                for nested in self.nested_superpositions.values():
                    # حساب درجة التشابك
                    if len(nested.children) > 1:
                        entanglement = 0.0
                        for child in nested.children:
                            sp = self.superpositions.get(child)
                            if sp:
                                entropy = 0.0
                                probs = [amp.probability() for amp in sp.values()]
                                for p in probs:
                                    if p > 0:
                                        entropy -= p * math.log2(p)
                                entanglement += entropy
                        
                        nested.entanglement_degree = min(1.0, entanglement / len(nested.children))
                
                threads.interruptible_sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في تحسين التداخل: {e}")
                threads.interruptible_sleep(60)
    
    # ============================================================
    # دورة تراكب كاملة
    # ============================================================
    
    def superposition_cycle(self) -> SuperpositionSnapshot:
        """
        دورة تراكب كاملة.
        
        1. تحديث التراكبات
        2. تطبيق تداخل جماعي
        3. قياسات جزئية عشوائية
        4. حساب المقاييس
        """
        # تطبيق تداخل جماعي عشوائي
        for group in self.superposition_groups.values():
            if random.random() < 0.2:
                self.apply_group_interference(group.id)
        
        # قياسات جزئية عشوائية
        for super_id in list(self.superpositions.keys()):
            if random.random() < 0.1:
                states = list(self.superpositions[super_id].keys())
                if len(states) > 1:
                    subset = random.sample(states, max(1, len(states) // 3))
                    self.partial_measure(super_id, subset, collapse_probability=0.2)
        
        # إعداد اللقطة
        super_data = {}
        for super_id, sp in self.superpositions.items():
            super_data[super_id[:16]] = {s: amp.probability() for s, amp in sp.items()}
        
        nested_data = []
        for nested in self.nested_superpositions.values():
            nested_data.append({
                "id": nested.id[:16],
                "name": nested.name,
                "level": nested.level,
                "children": len(nested.children),
                "entanglement": nested.entanglement_degree
            })
        
        group_data = []
        for group in self.superposition_groups.values():
            group_data.append({
                "id": group.id[:16],
                "name": group.name,
                "members": len(group.members),
                "synergy": group.synergy
            })
        
        # حساب المقاييس الكلية
        total_amplitude = 0.0
        for sp in self.superpositions.values():
            for amp in sp.values():
                total_amplitude += abs(amp.real + amp.imag)
        
        avg_coherence = 0.0
        for sp in self.superpositions.values():
            avg_coherence += self._calculate_coherence(sp)
        if self.superpositions:
            avg_coherence /= len(self.superpositions)
        
        # إنتروبيا التشابك
        entanglement_entropy = 0.0
        for nested in self.nested_superpositions.values():
            entanglement_entropy += nested.entanglement_degree
        if self.nested_superpositions:
            entanglement_entropy = min(1.0, entanglement_entropy / len(self.nested_superpositions))
        else:
            entanglement_entropy = 0.0
        
        # سرد
        narrative = self.generate_superposition_narrative(len(self.superpositions), avg_coherence, entanglement_entropy)
        
        snapshot = SuperpositionSnapshot(
            timestamp=time.time(),
            superpositions=super_data,
            nested_superpositions=nested_data,
            active_groups=group_data,
            partial_measurements=[pm.__dict__ for pm in self.partial_measurements[-20:]],
            total_amplitude=total_amplitude,
            average_coherence=avg_coherence,
            entanglement_entropy=entanglement_entropy,
            narrative=narrative
        )
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::superposition_cycle",
            payload={
                "total_superpositions": len(self.superpositions),
                "total_nested": len(self.nested_superpositions),
                "total_groups": len(self.superposition_groups),
                "avg_coherence": avg_coherence
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    def generate_superposition_narrative(self, count: int, coherence: float, entropy: float) -> str:
        """توليد سرد للتراكب"""
        narrative = f"⚛️ **التراكبات الكمومية**: {count} تراكباً نشطاً\n"
        narrative += f"🌀 **متوسط التماسك**: {coherence:.1%}\n"
        narrative += f"🔗 **إنتروبيا التشابك**: {entropy:.1%}\n"
        
        if coherence > 0.7:
            narrative += "🌌 تماسك عالٍ - سلوك كمومي قوي\n"
        elif coherence < 0.3:
            narrative += "💨 تماسك منخفض - اقتراب من السلوك الكلاسيكي\n"
        
        if entropy > 0.6:
            narrative += "🕸️ تشابك مرتفع - حالات مترابطة بقوة\n"
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة محرك التراكب"""
        try:
            state = {
                "superpositions_count": len(self.superpositions),
                "nested_count": len(self.nested_superpositions),
                "groups_count": len(self.superposition_groups),
                "measurements_count": len(self.partial_measurements),
                "policies": self.policies,
                "saved_at": time.time()
            }
            atomic_write_json(QUANTUM_SUPERPOSITION_STATE_FILE, state, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة التراكب: {e}")
    
    def _load_state(self):
        """تحميل حالة محرك التراكب"""
        try:
            if QUANTUM_SUPERPOSITION_STATE_FILE.exists():
                with open(QUANTUM_SUPERPOSITION_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    saved_policies = state.get("policies", {})
                    if saved_policies:
                        self.policies.update(saved_policies)
                logger.info("📂 تم تحميل حالة محرك التراكب")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة التراكب: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_policy(self, key: str, value: float) -> bool:
        """
        تعيين سياسة تشغيلية.
        
        Args:
            key: اسم السياسة (group_interference_strength, partial_measure_base_collapse, etc.)
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
    
    def get_superposition_status(self) -> Dict[str, Any]:
        """الحالة الحالية لمحرك التراكب"""
        return {
            "total_superpositions": len(self.superpositions),
            "total_nested": len(self.nested_superpositions),
            "total_groups": len(self.superposition_groups),
            "total_measurements": len(self.partial_measurements),
            "policies": self.policies,
            "timestamp": time.time()
        }
    
    def list_superpositions(self) -> List[Dict]:
        """قائمة التراكبات"""
        return [
            {
                "id": sid[:16],
                "dimension": len(sp),
                "coherence": self._calculate_coherence(sp)
            }
            for sid, sp in self.superpositions.items()
        ]
    
    def get_superposition_quote(self) -> str:
        """اقتباس عن التراكب"""
        quotes = [
            "التراكب يسمح بوجود متزامن في حالات متعددة.",
            "القياس الجزئي يستخرج معلومات دون انهيار كامل.",
            "التراكبات المتداخلة تخلق هياكل هرمية من الاحتمالات.",
            "التداخل الجماعي يخلق أنماطاً تعاونية.",
            "التماسك هو مقياس كمومية النظام.",
            "التشابك يربط الحالات عبر التراكبات المختلفة.",
            "التراكب هو مصدر القوة الكمومية."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محرك التراكب"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف محرك التراكب الكمي")


# ============================================================
# الـ Singleton
# ============================================================

_qsuper_instance: Optional[QuantumSuperpositionEngine] = None
_qsuper_lock = threading.Lock()


def get_quantum_superposition_engine() -> QuantumSuperpositionEngine:
    """الحصول على النسخة الوحيدة من محرك التراكب الكمي"""
    global _qsuper_instance
    if _qsuper_instance is None:
        with _qsuper_lock:
            if _qsuper_instance is None:
                _qsuper_instance = QuantumSuperpositionEngine()
    return _qsuper_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("⚛️ محرك التراكب الكمي الجبار - تراكبات متعددة المستويات")
    print("=" * 80 + "\n")
    
    qsuper = get_quantum_superposition_engine()
    
    # 1) إنشاء تراكبات أساسية
    print("⚛️ إنشاء تراكبات أساسية...")
    sp1 = qsuper.create_superposition("مسار النمو", {
        "نمو_مرتفع": complex(0.7, 0.1),
        "نمو_متوسط": complex(0.5, -0.2),
        "نمو_منخفض": complex(0.3, 0.0)
    })
    sp2 = qsuper.create_superposition("مسار الاستقرار", {
        "مستقر": complex(0.8, 0.0),
        "متقلب": complex(0.4, 0.3),
        "غير_مستقر": complex(0.2, -0.1)
    })
    sp3 = qsuper.create_superposition("مسار الأمان", {
        "آمن": complex(0.9, 0.0),
        "مهدد": complex(0.3, 0.2),
        "خطير": complex(0.1, -0.05)
    })
    print("   تم إنشاء 3 تراكبات")
    
    # 2) إنشاء تراكب متداخل
    print("\n🌌 إنشاء تراكب متداخل...")
    nested = qsuper.create_nested_superposition(
        "نظام_متكامل",
        [sp1, sp2, sp3],
        weights=[0.5, 0.3, 0.2]
    )
    print(f"   معرف التراكب المتداخل: {nested[:16]}...")
    
    # 3) تعريف مجموعة تداخل
    print("\n🔗 تعريف مجموعة تداخل جماعي...")
    group = qsuper.define_group("مجموعة_الأنظمة", [sp1, sp2, sp3], interference_strength=0.15)
    print(f"   معرف المجموعة: {group[:16]}...")
    
    # 4) تطبيق تداخل جماعي
    print("\n🌀 تطبيق تداخل جماعي...")
    qsuper.apply_group_interference(group)
    print("   تم تطبيق التداخل")
    
    # 5) قياس جزئي
    print("\n📏 قياس جزئي...")
    result = qsuper.partial_measure(sp1, ["نمو_مرتفع", "نمو_متوسط"], collapse_probability=0.3)
    if result:
        print(f"   الحالات المقاسة: {result.measured_states}")
        print(f"   النتائج: {result.outcomes}")
        print(f"   انهيار: {result.collapse_occurred}")
        if result.collapsed_state:
            print(f"   الحالة المنهارة: {result.collapsed_state}")
    
    # 6) دورة تراكب
    print("\n🔄 دورة تراكب...")
    snapshot = qsuper.superposition_cycle()
    print(f"   التراكبات النشطة: {len(snapshot.superpositions)}")
    print(f"   متوسط التماسك: {snapshot.average_coherence:.1%}")
    print(f"   إنتروبيا التشابك: {snapshot.entanglement_entropy:.1%}")
    
    # 7) قائمة التراكبات
    print("\n📋 قائمة التراكبات:")
    for sp in qsuper.list_superpositions():
        print(f"   {sp['id']}: بُعد {sp['dimension']}, تماسك {sp['coherence']:.1%}")
    
    # 8) دمج تراكبات
    print("\n🔀 دمج تراكبات...")
    merged = qsuper.create_superposition("مدمج", {})
    qsuper.merge_superpositions(merged, [sp1, sp2], merge_type="interfering")
    merged_probs = qsuper.get_superposition(merged)
    if merged_probs:
        print(f"   احتمالات التراكب المدمج: {list(merged_probs.items())[:3]}...")
    
    # 9) اختبار إعادة التهيئة
    print("\n🔄 اختبار إعادة تهيئة محرك التراكب...")
    qsuper.reset()
    print("   تم إعادة تهيئة محرك التراكب بنجاح - الحالة نظيفة وجاهزة للاختبارات")
    
    # 10) السرد
    print(f"\n📖 السرد:\n{snapshot.narrative}")
    
    # 11) اقتباس
    print(f"\n💭 {qsuper.get_superposition_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك التراكب الكمي الجبار جاهز - تراكبات متعددة المستويات")
    print("=" * 80)
