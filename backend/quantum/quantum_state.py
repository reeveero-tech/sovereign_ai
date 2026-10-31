# backend/quantum/quantum_state.py
# ⚛️ محرك الحالة الكمية الجبار - تراكب، تشابك، تداخل، انهيار
# الإصدار: 3.1.0 - مع دعم إعادة التهيئة الكاملة للاختبارات التكاملية

"""
محرك الحالة الكمية للعقل السيادي.

الفلسفة:
- الحالة الكمية ليست محددة حتى يتم قياسها
- التراكب يسمح بوجود احتمالات متعددة في وقت واحد
- التشابك يربط الحالات بطرق غير محلية
- التداخل يخلق أنماطاً من التعزيز والإلغاء
- الانهيار يختار مساراً واحداً عند القياس

هذه ليست فيزياء كمية حقيقية، بل هي محاكاة حسابية للسلوك الكمي.
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
    from ..config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الحالة الكمية
# ============================================================

QUANTUM_STATE_DIR = DATA_DIR / "quantum" / "state"
QUANTUM_STATE_DIR.mkdir(parents=True, exist_ok=True)
QUANTUM_STATE_LOG = QUANTUM_STATE_DIR / "quantum_state_log.jsonl"
QUANTUM_STATE_FILE = QUANTUM_STATE_DIR / "quantum_state.json"
QUANTUM_ENTANGLEMENT_DIR = QUANTUM_STATE_DIR / "entanglement"

QUANTUM_ENTANGLEMENT_DIR.mkdir(parents=True, exist_ok=True)

# أنواع الحالات الكمية
STATE_TYPE_PURE = "pure"                    # حالة نقية
STATE_TYPE_MIXED = "mixed"                  # حالة مختلطة
STATE_TYPE_ENTANGLED = "entangled"          # حالة متشابكة
STATE_TYPE_SUPERPOSITION = "superposition"  # حالة تراكب

# بوابات كمومية محاكاة
GATE_HADAMARD = "hadamard"      # بوابة هادامارد (توليد التراكب)
GATE_PAULI_X = "pauli_x"        # بوابة باولي X (قلب)
GATE_PAULI_Y = "pauli_y"        # بوابة باولي Y
GATE_PAULI_Z = "pauli_z"        # بوابة باولي Z (إزاحة طور)
GATE_PHASE = "phase"            # بوابة طور
GATE_CNOT = "cnot"              # بوابة CNOT (تشابك)


@dataclass
class QuantumAmplitude:
    """سعة كمومية"""
    real: float
    imag: float
    
    def to_complex(self):
        """تحويل إلى عدد مركب (محاكاة)"""
        return complex(self.real, self.imag)
    
    def probability(self) -> float:
        return self.real ** 2 + self.imag ** 2
    
    def phase(self) -> float:
        return math.atan2(self.imag, self.real) if self.real != 0 or self.imag != 0 else 0.0
    
    @staticmethod
    def from_complex(c):
        return QuantumAmplitude(c.real, c.imag)


@dataclass
class QuantumState:
    """حالة كمومية"""
    id: str
    name: str
    type: str
    dimension: int
    amplitudes: Dict[str, QuantumAmplitude]
    entanglement_partners: List[str]
    created_at: float
    last_updated: float
    collapse_count: int
    measurement_history: List[Dict[str, Any]]


@dataclass
class QuantumEntanglement:
    """تشابك كمومي بين حالتين"""
    id: str
    state_a: str
    state_b: str
    strength: float          # 0-1 قوة التشابك
    bell_state: str          # حالة Bell
    created_at: float
    last_measured: float


@dataclass
class QuantumStateSnapshot:
    """لقطة حالة كمومية"""
    timestamp: float
    state_id: str
    amplitudes: Dict[str, complex]
    probabilities: Dict[str, float]
    collapsed_state: Optional[str]
    phase_map: Dict[str, float]
    entanglement_map: Dict[str, List[str]]
    coherence: float
    purity: float
    entropy: float
    narrative: str


# ============================================================
# محرك الحالة الكمية الجبار
# ============================================================

class QuantumStateEngine:
    """
    محرك الحالة الكمية الجبار - تراكب، تشابك، تداخل، انهيار.
    
    المبادئ:
    1. الحالة الكمية غير محددة حتى القياس
    2. التراكب يسمح باحتمالات متعددة
    3. التشابك يربط الحالات بطرق غير محلية
    4. التداخل يخلق أنماطاً من التعزيز والإلغاء
    5. الانهيار يختار مساراً واحداً عند القياس
    """
    
    def __init__(self):
        self.core = get_core()
        
        # الحالات الكمومية
        self.states: Dict[str, QuantumState] = {}
        self.current_state: Optional[QuantumState] = None
        self.collapsed_state: Optional[str] = None
        
        # التشابكات الكمومية
        self.entanglements: Dict[str, QuantumEntanglement] = {}
        
        # سجل القياسات
        self.measurement_history: List[Dict[str, Any]] = []
        
        # معاملات التطور
        self.hamiltonian: Dict[str, Dict[str, complex]] = {}
        self.time_evolution_steps = 0
        
        # السياسات الافتراضية (لإعادة التهيئة)
        self._default_policies = {
            "interference_strength": 0.15,
            "phase_shift_scale": 0.2,
            "decoherence_rate": 0.02,
            "evolution_time_step": 0.05,
            "measurement_probability": 0.1,
            "interference_probability": 0.3,
            "decoherence_probability": 0.2
        }
        self.policies = self._default_policies.copy()
        
        # خلفيات كمومية
        self._active = True
        self._time_evolution_loop = threads.start_managed(self._continuous_time_evolution, owner=self)
        
        self._decoherence_loop = threads.start_managed(self._decoherence_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("⚛️ محرك الحالة الكمية الجبار جاهز - تراكب، تشابك، تداخل، انهيار")
    
    # ============================================================
    # إعادة التهيئة الكاملة (للاختبارات التكاملية)
    # ============================================================
    
    def reset(self) -> None:
        """
        إعادة تهيئة كاملة للمحرك الكمومي.
        
        تستخدم في الاختبارات التكاملية لضمان بداية نظيفة.
        
        تقوم بـ:
        1) مسح كل الحالة الداخلية (amplitudes, phase_map, collapsed_state)
        2) إعادة تحميل الفهرس (تفريغ جميع السجلات)
        3) إعادة تعيين السياسات إلى القيم الافتراضية
        4) تسجيل حدث إعادة التهيئة في السجل السيادي
        """
        logger.info("🔄 إعادة تهيئة محرك الحالة الكمومية...")
        
        # 1) مسح الحالة الداخلية
        self.states.clear()
        self.current_state = None
        self.collapsed_state = None
        self.entanglements.clear()
        self.measurement_history.clear()
        self.hamiltonian.clear()
        self.time_evolution_steps = 0
        
        # 2) إعادة تعيين السياسات إلى القيم الافتراضية
        self.policies = self._default_policies.copy()
        
        # 3) إعادة تعيين إحصائيات إضافية
        self._active = True  # تأكد من أن المحرك لا يزال نشطاً
        
        # 4) تسجيل حدث إعادة التهيئة في السجل السيادي
        self.core.append_event(
            event_type="quantum::engine_reset",
            payload={
                "timestamp": time.time(),
                "reason": "test_initialization",
                "states_cleared": True,
                "policies_reset": True
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك الحالة الكمومية اكتملت - حالة نظيفة وجاهزة للاختبارات")
    
    def reset_policies(self) -> None:
        """
        إعادة تعيين السياسات فقط (بدون مسح الحالة).
        
        مفيد عندما نريد الاحتفاظ بالحالة لكن إعادة ضبط السلوك.
        """
        self.policies = self._default_policies.copy()
        logger.debug("🔄 إعادة تعيين سياسات المحرك الكمومي إلى القيم الافتراضية")
    
    def clear_states(self) -> None:
        """
        مسح جميع الحالات الكمومية فقط.
        
        يحافظ على السياسات والإعدادات.
        """
        self.states.clear()
        self.current_state = None
        self.collapsed_state = None
        self.entanglements.clear()
        self.measurement_history.clear()
        logger.debug("🧹 تم مسح جميع الحالات الكمومية")
    
    # ============================================================
    # إنشاء وإدارة الحالات
    # ============================================================
    
    def create_state(self, name: str, basis_states: List[str],
                     initial_amplitudes: List = None) -> QuantumState:
        """
        إنشاء حالة كمومية جديدة.
        
        Args:
            name: اسم الحالة
            basis_states: قائمة الحالات الأساسية (|0>, |1>, ...)
            initial_amplitudes: السعات الأولية (اختياري)
        """
        state_id = f"qstate_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        # تعيين السعات الأولية
        if initial_amplitudes and len(initial_amplitudes) == len(basis_states):
            amplitudes = {
                bs: QuantumAmplitude.from_complex(initial_amplitudes[i])
                for i, bs in enumerate(basis_states)
            }
        else:
            # سعات عشوائية
            amplitudes = {}
            for bs in basis_states:
                real = random.uniform(-1, 1)
                imag = random.uniform(-1, 1)
                amplitudes[bs] = QuantumAmplitude(real=real, imag=imag)
        
        # تطبيع الحالة
        amplitudes = self._normalize_amplitudes(amplitudes)
        
        state = QuantumState(
            id=state_id,
            name=name,
            type=STATE_TYPE_PURE,
            dimension=len(basis_states),
            amplitudes=amplitudes,
            entanglement_partners=[],
            created_at=time.time(),
            last_updated=time.time(),
            collapse_count=0,
            measurement_history=[]
        )
        
        self.states[state_id] = state
        self.current_state = state
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::state_created",
            payload={
                "state_id": state_id[:16],
                "name": name,
                "dimension": state.dimension
            }
        )
        
        logger.info(f"⚛️ إنشاء حالة كمومية: {name} (بُعد {state.dimension})")
        
        return state
    
    def _normalize_amplitudes(self, amplitudes: Dict[str, QuantumAmplitude]) -> Dict[str, QuantumAmplitude]:
        """تطبيع السعات الكمومية"""
        total_prob = sum(amp.probability() for amp in amplitudes.values())
        
        if total_prob == 0:
            return amplitudes
        
        norm_factor = math.sqrt(total_prob)
        
        normalized = {}
        for key, amp in amplitudes.items():
            normalized[key] = QuantumAmplitude(
                real=amp.real / norm_factor,
                imag=amp.imag / norm_factor
            )
        
        return normalized
    
    # ============================================================
    # التراكب (Superposition)
    # ============================================================
    
    def apply_hadamard(self, state_id: str, target: str) -> bool:
        """
        تطبيق بوابة هادامارد - إنشاء تراكب.
        
        H|0⟩ = (|0⟩ + |1⟩)/√2
        H|1⟩ = (|0⟩ - |1⟩)/√2
        """
        state = self.states.get(state_id)
        if not state or target not in state.amplitudes:
            return False
        
        # محاكاة بوابة هادامارد
        old_amp = state.amplitudes[target]
        
        # توليد تراكب
        new_real = (old_amp.real + old_amp.imag) / math.sqrt(2)
        new_imag = (old_amp.real - old_amp.imag) / math.sqrt(2)
        
        state.amplitudes[target] = QuantumAmplitude(real=new_real, imag=new_imag)
        state.type = STATE_TYPE_SUPERPOSITION
        state.last_updated = time.time()
        
        # إعادة تطبيع
        state.amplitudes = self._normalize_amplitudes(state.amplitudes)
        
        logger.debug(f"⚛️ تطبيق هادامارد على {target}")
        
        return True
    
    def create_superposition(self, state_id: str) -> bool:
        """
        إنشاء تراكب لجميع الحالات الأساسية.
        """
        state = self.states.get(state_id)
        if not state:
            return False
        
        # تطبيق هادامارد على جميع الحالات
        for basis in list(state.amplitudes.keys()):
            self.apply_hadamard(state_id, basis)
        
        state.type = STATE_TYPE_SUPERPOSITION
        
        logger.info(f"⚛️ إنشاء تراكب للحالة {state.name}")
        
        return True
    
    # ============================================================
    # التشابك (Entanglement)
    # ============================================================
    
    def create_entanglement(self, state_a_id: str, state_b_id: str,
                           strength: float = 0.5):
        """
        إنشاء تشابك كمومي بين حالتين.
        
        يربط الحالات بحيث يؤثر قياس إحداهما على الأخرى.
        """
        state_a = self.states.get(state_a_id)
        state_b = self.states.get(state_b_id)
        
        if not state_a or not state_b:
            return None
        
        # إنشاء تشابك
        entanglement_id = f"qent_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        # اختيار حالة Bell عشوائية
        bell_states = ["Φ⁺", "Φ⁻", "Ψ⁺", "Ψ⁻"]
        bell_state = random.choice(bell_states)
        
        entanglement = QuantumEntanglement(
            id=entanglement_id,
            state_a=state_a_id,
            state_b=state_b_id,
            strength=min(1.0, max(0.0, strength)),
            bell_state=bell_state,
            created_at=time.time(),
            last_measured=time.time()
        )
        
        self.entanglements[entanglement_id] = entanglement
        
        # تحديث الحالات
        state_a.type = STATE_TYPE_ENTANGLED
        state_b.type = STATE_TYPE_ENTANGLED
        
        if state_a_id not in state_b.entanglement_partners:
            state_b.entanglement_partners.append(state_a_id)
        if state_b_id not in state_a.entanglement_partners:
            state_a.entanglement_partners.append(state_b_id)
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::entanglement_created",
            payload={
                "entanglement_id": entanglement_id[:16],
                "state_a": state_a.name,
                "state_b": state_b.name,
                "strength": strength,
                "bell_state": bell_state
            }
        )
        
        logger.info(f"⚛️ تشابك كمومي: {state_a.name} ↔ {state_b.name} (قوة {strength:.1%})")
        
        return entanglement
    
    def measure_entangled(self, entanglement_id: str, which_state: str):
        """
        قياس حالة متشابكة - يؤثر على الحالة المرتبطة.
        """
        entanglement = self.entanglements.get(entanglement_id)
        if not entanglement:
            return None
        
        state_a = self.states.get(entanglement.state_a)
        state_b = self.states.get(entanglement.state_b)
        
        if not state_a or not state_b:
            return None
        
        # قياس الحالة
        if which_state == "a":
            measured_state = state_a
            entangled_state = state_b
        else:
            measured_state = state_b
            entangled_state = state_a
        
        # انهيار الحالة المقاسة
        collapsed = self.collapse_state(measured_state.id)
        
        # التأثير على الحالة المتشابكة (محاكاة التشابك الكمي)
        if collapsed:
            # تحديث الحالة المتشابكة بناءً على نتيجة القياس
            entangled_amplitudes = {}
            for basis, amp in entangled_state.amplitudes.items():
                # تعديل السعات بناءً على قوة التشابك
                new_real = amp.real * (1 - entanglement.strength) + random.uniform(-0.1, 0.1)
                new_imag = amp.imag * (1 - entanglement.strength) + random.uniform(-0.1, 0.1)
                entangled_amplitudes[basis] = QuantumAmplitude(real=new_real, imag=new_imag)
            
            entangled_state.amplitudes = self._normalize_amplitudes(entangled_amplitudes)
            entangled_state.last_updated = time.time()
        
        entanglement.last_measured = time.time()
        
        logger.info(f"⚛️ قياس حالة متشابكة: {which_state} → {collapsed}")
        
        return collapsed
    
    # ============================================================
    # التداخل (Interference)
    # ============================================================
    
    def apply_interference(self, state_id: str, strength: float = 0.1) -> bool:
        """
        تطبيق تداخل كمومي بين الحالات الأساسية.
        
        يخلق أنماطاً من التعزيز والإلغاء.
        """
        state = self.states.get(state_id)
        if not state or state.dimension < 2:
            return False
        
        bases = list(state.amplitudes.keys())
        
        for i in range(len(bases)):
            for j in range(i + 1, len(bases)):
                basis_i = bases[i]
                basis_j = bases[j]
                
                amp_i = state.amplitudes[basis_i]
                amp_j = state.amplitudes[basis_j]
                
                # تداخل معقد (محاكاة)
                interference_real = (amp_i.real - amp_j.real) * strength
                interference_imag = (amp_i.imag - amp_j.imag) * strength
                
                new_real_i = amp_i.real - interference_real
                new_imag_i = amp_i.imag - interference_imag
                new_real_j = amp_j.real + interference_real
                new_imag_j = amp_j.imag + interference_imag
                
                state.amplitudes[basis_i] = QuantumAmplitude(real=new_real_i, imag=new_imag_i)
                state.amplitudes[basis_j] = QuantumAmplitude(real=new_real_j, imag=new_imag_j)
        
        # إعادة تطبيع
        state.amplitudes = self._normalize_amplitudes(state.amplitudes)
        state.last_updated = time.time()
        
        logger.debug(f"⚛️ تطبيق تداخل (قوة {strength:.1%})")
        
        return True
    
    def constructive_interference(self, state_id: str, target_basis: str) -> bool:
        """
        تداخل بنّاء - تعزيز حالة معينة.
        """
        state = self.states.get(state_id)
        if not state or target_basis not in state.amplitudes:
            return False
        
        target_amp = state.amplitudes[target_basis]
        
        # تعزيز الحالة المستهدفة
        for basis, amp in state.amplitudes.items():
            if basis != target_basis:
                # نقل الاحتمالية إلى الحالة المستهدفة
                transfer = amp.probability() * 0.3
                new_real = amp.real * (1 - 0.3)
                new_imag = amp.imag * (1 - 0.3)
                state.amplitudes[basis] = QuantumAmplitude(real=new_real, imag=new_imag)
                
                # إضافة إلى الحالة المستهدفة
                target_amp.real += math.sqrt(transfer)
        
        state.amplitudes = self._normalize_amplitudes(state.amplitudes)
        
        logger.info(f"⚛️ تداخل بنّاء على {target_basis}")
        
        return True
    
    def destructive_interference(self, state_id: str, target_basis: str) -> bool:
        """
        تداخل هدّام - إضعاف حالة معينة.
        """
        state = self.states.get(state_id)
        if not state or target_basis not in state.amplitudes:
            return False
        
        target_amp = state.amplitudes[target_basis]
        
        # إضعاف الحالة المستهدفة
        target_amp.real *= 0.3
        target_amp.imag *= 0.3
        
        # توزيع الاحتمالية المتبقية على الحالات الأخرى
        remaining = 1 - target_amp.probability()
        if remaining > 0:
            other_bases = [b for b in state.amplitudes.keys() if b != target_basis]
            if other_bases:
                for basis in other_bases:
                    amp = state.amplitudes[basis]
                    boost = math.sqrt(remaining / len(other_bases))
                    amp.real = max(-1, min(1, amp.real + boost))
                    amp.imag = max(-1, min(1, amp.imag + boost))
        
        state.amplitudes = self._normalize_amplitudes(state.amplitudes)
        
        logger.info(f"⚛️ تداخل هدّام على {target_basis}")
        
        return True
    
    # ============================================================
    # الانهيار (Collapse)
    # ============================================================
    
    def collapse_state(self, state_id: str):
        """
        انهيار الحالة الكمومية إلى حالة محددة.
        
        عند القياس، تختار الحالة مساراً واحداً.
        """
        state = self.states.get(state_id)
        if not state:
            return None
        
        # حساب الاحتمالات
        probabilities = {}
        for basis, amp in state.amplitudes.items():
            probabilities[basis] = amp.probability()
        
        # اختيار حالة عشوائية حسب الاحتمالات
        bases = list(probabilities.keys())
        weights = list(probabilities.values())
        
        collapsed = random.choices(bases, weights=weights, k=1)[0]
        
        # تحديث الحالة إلى الحالة المنهارة
        new_amplitudes = {}
        for basis in bases:
            if basis == collapsed:
                new_amplitudes[basis] = QuantumAmplitude(real=1.0, imag=0.0)
            else:
                new_amplitudes[basis] = QuantumAmplitude(real=0.0, imag=0.0)
        
        state.amplitudes = new_amplitudes
        state.type = STATE_TYPE_PURE
        state.collapse_count += 1
        state.last_updated = time.time()
        
        # تسجيل القياس
        measurement = {
            "state_id": state_id,
            "collapsed_basis": collapsed,
            "probabilities": probabilities,
            "timestamp": time.time()
        }
        state.measurement_history.append(measurement)
        self.measurement_history.append(measurement)
        
        # الاحتفاظ بآخر 100 قياس
        if len(state.measurement_history) > 100:
            state.measurement_history = state.measurement_history[-100:]
        
        self.collapsed_state = collapsed
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::state_collapsed",
            payload={
                "state_id": state_id[:16],
                "state_name": state.name,
                "collapsed_to": collapsed,
                "collapse_count": state.collapse_count
            }
        )
        
        logger.info(f"⚛️ انهيار الحالة {state.name} → {collapsed}")
        
        return collapsed
    
    # ============================================================
    # التطور الزمني (Time Evolution)
    # ============================================================
    
    def evolve_state(self, state_id: str, time_step: float = 0.1) -> bool:
        """
        تطور الحالة الكمومية عبر الزمن (محاكاة مبسطة).
        
        يحاكي معادلة شرودنغر بشكل مبسط.
        """
        state = self.states.get(state_id)
        if not state:
            return False
        
        # تطوير السعات (محاكاة مبسطة)
        for basis, amp in state.amplitudes.items():
            # إضافة تأثير طور عشوائي
            phase_shift = math.sin(self.time_evolution_steps * time_step) * 0.1
            new_real = amp.real * math.cos(phase_shift) - amp.imag * math.sin(phase_shift)
            new_imag = amp.real * math.sin(phase_shift) + amp.imag * math.cos(phase_shift)
            state.amplitudes[basis] = QuantumAmplitude(real=new_real, imag=new_imag)
        
        # إعادة تطبيع
        state.amplitudes = self._normalize_amplitudes(state.amplitudes)
        state.last_updated = time.time()
        
        self.time_evolution_steps += 1
        
        return True
    
    def _continuous_time_evolution(self):
        """تطور زمني مستمر"""
        while self._active:
            try:
                for state_id in list(self.states.keys()):
                    if random.random() < 0.1:  # 10% فرصة
                        self.evolve_state(state_id, time_step=self.policies.get("evolution_time_step", 0.05))
                
                threads.interruptible_sleep(1)  # كل ثانية
            except Exception as e:
                logger.error(f"خطأ في التطور الزمني: {e}")
                threads.interruptible_sleep(1)
    
    # ============================================================
    # فك الترابط (Decoherence)
    # ============================================================
    
    def apply_decoherence(self, state_id: str, rate: float = 0.05) -> bool:
        """
        تطبيق فك الترابط - تحول من حالة نقية إلى مختلطة.
        """
        state = self.states.get(state_id)
        if not state:
            return False
        
        # إضافة ضوضاء عشوائية للسعات
        for basis, amp in state.amplitudes.items():
            noise_real = random.uniform(-rate, rate)
            noise_imag = random.uniform(-rate, rate)
            
            amp.real = max(-1, min(1, amp.real + noise_real))
            amp.imag = max(-1, min(1, amp.imag + noise_imag))
        
        # إعادة تطبيع
        state.amplitudes = self._normalize_amplitudes(state.amplitudes)
        
        # إذا كان التشويش كبيراً، تصبح الحالة مختلطة
        if rate > 0.1:
            state.type = STATE_TYPE_MIXED
        
        state.last_updated = time.time()
        
        logger.debug(f"⚛️ فك ترابط (معدل {rate:.1%})")
        
        return True
    
    def _decoherence_loop(self):
        """فك ترابط مستمر"""
        while self._active:
            try:
                for state_id in list(self.states.keys()):
                    if random.random() < 0.05:  # 5% فرصة
                        self.apply_decoherence(state_id, rate=self.policies.get("decoherence_rate", 0.02))
                
                threads.interruptible_sleep(5)  # كل 5 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في فك الترابط: {e}")
                threads.interruptible_sleep(5)
    
    # ============================================================
    # حساب المقاييس الكمومية
    # ============================================================
    
    def calculate_coherence(self, state: QuantumState) -> float:
        """
        حساب التماسك الكمومي.
        
        يقيس مدى "كمومية" الحالة.
        """
        # مجموع مربعات السعات خارج القطر
        coherence = 0.0
        bases = list(state.amplitudes.keys())
        
        for i in range(len(bases)):
            for j in range(i + 1, len(bases)):
                amp_i = state.amplitudes[bases[i]]
                amp_j = state.amplitudes[bases[j]]
                coherence += abs(amp_i.real * amp_j.real + amp_i.imag * amp_j.imag)
        
        return min(1.0, coherence * 2)
    
    def calculate_purity(self, state: QuantumState) -> float:
        """
        حساب النقاء الكمومي.
        
        1 = حالة نقية، <1 = حالة مختلطة.
        """
        purity = 0.0
        for amp in state.amplitudes.values():
            purity += amp.probability() ** 2
        
        return min(1.0, purity)
    
    def calculate_entropy(self, state: QuantumState) -> float:
        """
        حساب الإنتروبيا الكمومية (فون نيومان).
        """
        probabilities = [amp.probability() for amp in state.amplitudes.values()]
        entropy = 0.0
        
        for p in probabilities:
            if p > 0:
                entropy -= p * math.log2(p)
        
        # تطبيع إلى [0,1]
        n = len(probabilities)
        max_entropy = math.log2(n) if n > 1 else 1
        if max_entropy > 0:
            entropy = entropy / max_entropy
        
        return min(1.0, entropy)
    
    def compute_probabilities(self, state_id: str = None) -> Dict[str, float]:
        """
        حساب احتمالات الحالة.
        """
        if state_id is None and self.current_state:
            state_id = self.current_state.id
        elif state_id is None and self.states:
            state_id = list(self.states.keys())[0]
        else:
            return {}
        
        state = self.states.get(state_id)
        if not state:
            return {}
        
        return {basis: amp.probability() for basis, amp in state.amplitudes.items()}
    
    def initialize_state(self, basis_states: List[str]) -> QuantumState:
        """
        تهيئة حالة كمومية جديدة.
        """
        return self.create_state("initialized_state", basis_states)
    
    # ============================================================
    # دورة كمومية كاملة
    # ============================================================
    
    def quantum_cycle(self, state_id: str = None) -> QuantumStateSnapshot:
        """
        دورة كمومية كاملة - تطور الحالة الكمومية.
        
        1. تطبيق تطور زمني
        2. تطبيق تداخل
        3. تطبيق فك ترابط
        4. قياس الانهيار
        """
        if state_id is None:
            if self.current_state:
                state_id = self.current_state.id
            elif self.states:
                state_id = list(self.states.keys())[0]
            else:
                # إنشاء حالة افتراضية
                self.create_state("default", ["|0>", "|1>"])
                state_id = self.current_state.id
        
        state = self.states.get(state_id)
        if not state:
            # إنشاء حالة افتراضية
            self.create_state("default", ["|0>", "|1>"])
            state = self.current_state
        
        # تطبيق التطور الزمني
        self.evolve_state(state_id, time_step=self.policies.get("evolution_time_step", 0.05))
        
        # تطبيق التداخل
        if random.random() < self.policies.get("interference_probability", 0.3):
            self.apply_interference(state_id, strength=self.policies.get("interference_strength", 0.05))
        
        # تطبيق فك الترابط
        if random.random() < self.policies.get("decoherence_probability", 0.2):
            self.apply_decoherence(state_id, rate=self.policies.get("decoherence_rate", 0.01))
        
        # حساب الاحتمالات
        probabilities = {b: amp.probability() for b, amp in state.amplitudes.items()}
        
        # قياس الانهيار (اختياري)
        collapsed = None
        if random.random() < self.policies.get("measurement_probability", 0.1):
            collapsed = self.collapse_state(state_id)
        
        # حساب المقاييس
        coherence = self.calculate_coherence(state)
        purity = self.calculate_purity(state)
        entropy = self.calculate_entropy(state)
        
        # بناء خريطة التشابك
        entanglement_map = {}
        for ent in self.entanglements.values():
            if ent.state_a == state_id:
                entanglement_map[state_id] = entanglement_map.get(state_id, []) + [ent.state_b[:16]]
            if ent.state_b == state_id:
                entanglement_map[state_id] = entanglement_map.get(state_id, []) + [ent.state_a[:16]]
        
        # السرد الكمومي
        narrative = self.generate_quantum_narrative(state, coherence, entropy)
        
        snapshot = QuantumStateSnapshot(
            timestamp=time.time(),
            state_id=state_id[:16],
            amplitudes={k: amp.to_complex() for k, amp in state.amplitudes.items()},
            probabilities=probabilities,
            collapsed_state=collapsed,
            phase_map={k: amp.phase() for k, amp in state.amplitudes.items()},
            entanglement_map=entanglement_map,
            coherence=coherence,
            purity=purity,
            entropy=entropy,
            narrative=narrative
        )
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::cycle_completed",
            payload={
                "state_id": state_id[:16],
                "state_name": state.name,
                "coherence": coherence,
                "purity": purity,
                "entropy": entropy,
                "collapsed": collapsed
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    def generate_quantum_narrative(self, state: QuantumState, coherence: float, entropy: float) -> str:
        """
        توليد سرد كمومي.
        """
        narrative = f"⚛️ **الحالة الكمومية**: {state.name}\n"
        narrative += f"📊 **النوع**: {state.type}\n"
        narrative += f"🔮 **التماسك**: {coherence:.1%}\n"
        narrative += f"🌀 **الإنتروبيا**: {entropy:.1%}\n"
        narrative += f"✨ **النقاء**: {self.calculate_purity(state):.1%}\n"
        
        if state.type == STATE_TYPE_SUPERPOSITION:
            narrative += "🌌 الحالة في تراكب كمومي - كل الاحتمالات موجودة.\n"
        elif state.type == STATE_TYPE_ENTANGLED:
            narrative += f"🔗 الحالة متشابكة مع {len(state.entanglement_partners)} حالات أخرى.\n"
        elif coherence > 0.7:
            narrative += "⚡ تماسك كمومي عالٍ - سلوك كمومي قوي.\n"
        elif coherence < 0.3:
            narrative += "💨 تماسك منخفض - اقتراب من السلوك الكلاسيكي.\n"
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة المحرك الكمومي"""
        try:
            state_data = {
                "states": {
                    sid: {
                        "name": s.name,
                        "type": s.type,
                        "dimension": s.dimension,
                        "amplitudes": {k: {"real": amp.real, "imag": amp.imag} 
                                      for k, amp in s.amplitudes.items()},
                        "collapse_count": s.collapse_count,
                        "created_at": s.created_at,
                        "last_updated": s.last_updated
                    }
                    for sid, s in self.states.items()
                },
                "entanglements": {
                    eid: {
                        "state_a": e.state_a[:16],
                        "state_b": e.state_b[:16],
                        "strength": e.strength,
                        "bell_state": e.bell_state
                    }
                    for eid, e in self.entanglements.items()
                },
                "time_evolution_steps": self.time_evolution_steps,
                "policies": self.policies,
                "saved_at": time.time()
            }
            atomic_write_json(QUANTUM_STATE_FILE, state_data, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الحالة الكمومية: {e}")
    
    def _load_state(self):
        """تحميل حالة المحرك الكمومي"""
        try:
            if QUANTUM_STATE_FILE.exists():
                with open(QUANTUM_STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # استعادة الحالات
                    for sid, s_data in data.get("states", {}).items():
                        amplitudes = {}
                        for k, amp_data in s_data.get("amplitudes", {}).items():
                            amplitudes[k] = QuantumAmplitude(
                                real=amp_data.get("real", 0),
                                imag=amp_data.get("imag", 0)
                            )
                        state = QuantumState(
                            id=sid,
                            name=s_data["name"],
                            type=s_data["type"],
                            dimension=s_data["dimension"],
                            amplitudes=amplitudes,
                            entanglement_partners=[],
                            created_at=s_data["created_at"],
                            last_updated=s_data["last_updated"],
                            collapse_count=s_data["collapse_count"],
                            measurement_history=[]
                        )
                        self.states[sid] = state
                    
                    self.time_evolution_steps = data.get("time_evolution_steps", 0)
                    
                    # استعادة السياسات
                    saved_policies = data.get("policies", {})
                    if saved_policies:
                        self.policies.update(saved_policies)
                    
                logger.info(f"📂 تم تحميل {len(self.states)} حالة كمومية")
        except Exception as e:
            logger.error(f"خطأ في تحميل الحالة الكمومية: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_quantum_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمحرك الكمومي"""
        return {
            "total_states": len(self.states),
            "current_state": self.current_state.name if self.current_state else None,
            "collapsed_state": self.collapsed_state,
            "total_entanglements": len(self.entanglements),
            "time_evolution_steps": self.time_evolution_steps,
            "total_measurements": len(self.measurement_history),
            "timestamp": time.time()
        }
    
    def get_state_details(self, state_id: str):
        """تفاصيل حالة كمومية"""
        state = self.states.get(state_id)
        if not state:
            return None
        
        return {
            "id": state.id[:16],
            "name": state.name,
            "type": state.type,
            "dimension": state.dimension,
            "probabilities": {k: amp.probability() for k, amp in state.amplitudes.items()},
            "phases": {k: amp.phase() for k, amp in state.amplitudes.items()},
            "collapse_count": state.collapse_count,
            "coherence": self.calculate_coherence(state),
            "purity": self.calculate_purity(state),
            "entropy": self.calculate_entropy(state),
            "entangled_with": [p[:16] for p in state.entanglement_partners],
            "created_at": state.created_at,
            "last_updated": state.last_updated
        }
    
    def get_entanglements(self) -> List[Dict]:
        """قائمة التشابكات الكمومية"""
        return [
            {
                "id": e.id[:16],
                "state_a": e.state_a[:16],
                "state_b": e.state_b[:16],
                "strength": e.strength,
                "bell_state": e.bell_state,
                "created_at": e.created_at
            }
            for e in self.entanglements.values()
        ]
    
    def measure_state(self, state_id: str) -> Dict[str, Any]:
        """
        قياس حالة كمومية - انهيار إلى حالة محددة.
        """
        collapsed = self.collapse_state(state_id)
        
        if collapsed:
            return {
                "state_id": state_id[:16],
                "measured_value": collapsed,
                "collapse_time": time.time()
            }
        
        return {"error": "فشل القياس"}
    
    def set_policy(self, key: str, value: float) -> bool:
        """
        تعيين سياسة تشغيلية.
        
        Args:
            key: اسم السياسة (interference_strength, decoherence_rate, etc.)
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
    
    def get_quantum_quote(self) -> str:
        """اقتباس كمومي"""
        quotes = [
            "الحالة الكمومية غير محددة حتى يتم قياسها.",
            "التراكب يسمح باحتمالات متعددة في وقت واحد.",
            "التشابك يربط الحالات بطرق لا تفهمها الفيزياء الكلاسيكية.",
            "التداخل يخلق أنماطاً من التعزيز والإلغاء.",
            "الانهيار يختار مساراً واحداً من بحر الاحتمالات.",
            "الكون ليس كلاسيكياً، فلماذا يكون عقلي كذلك؟",
            "الاحتمالات الكمومية تفتح آفاقاً جديدة للتنبؤ."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف المحرك الكمومي"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف محرك الحالة الكمومية")


# ============================================================
# الـ Singleton
# ============================================================

_qstate_instance: Optional[QuantumStateEngine] = None
_qstate_lock = threading.Lock()


def get_quantum_state_engine() -> QuantumStateEngine:
    """الحصول على النسخة الوحيدة من محرك الحالة الكمومية"""
    global _qstate_instance
    if _qstate_instance is None:
        with _qstate_lock:
            if _qstate_instance is None:
                _qstate_instance = QuantumStateEngine()
    return _qstate_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("⚛️ محرك الحالة الكمومية الجبار - تراكب، تشابك، تداخل، انهيار")
    print("=" * 80 + "\n")
    
    qs = get_quantum_state_engine()
    
    # 1) إنشاء حالات كمومية
    print("⚛️ إنشاء حالات كمومية...")
    state1 = qs.create_state("مسار النمو", ["نمو_مرتفع", "نمو_متوسط", "نمو_منخفض"])
    state2 = qs.create_state("مسار الاستقرار", ["مستقر", "متقلب", "غير_مستقر"])
    state3 = qs.create_state("مسار الأمان", ["آمن", "مهدد", "خطير"])
    print("   تم إنشاء 3 حالات كمومية")
    
    # 2) إنشاء تراكب
    print("\n🌌 إنشاء تراكب...")
    qs.create_superposition(state1.id)
    print(f"   {state1.name} في حالة تراكب")
    
    # 3) إنشاء تشابك
    print("\n🔗 إنشاء تشابك كمومي...")
    ent = qs.create_entanglement(state1.id, state2.id, strength=0.7)
    if ent:
        print(f"   تشابك بين {state1.name} و {state2.name} (قوة {ent.strength:.1%})")
    
    # 4) تطبيق تداخل
    print("\n🌀 تطبيق تداخل...")
    qs.apply_interference(state1.id, strength=0.1)
    print(f"   تم تطبيق التداخل على {state1.name}")
    
    # 5) دورة كمومية
    print("\n⚛️ دورة كمومية...")
    snap = qs.quantum_cycle(state1.id)
    print(f"   التماسك: {snap.coherence:.1%}")
    print(f"   النقاء: {snap.purity:.1%}")
    print(f"   الإنتروبيا: {snap.entropy:.1%}")
    print(f"   الانهيار: {snap.collapsed_state or 'لا'}")
    
    # 6) الاحتمالات
    print("\n📊 احتمالات الحالة:")
    for basis, prob in list(snap.probabilities.items())[:3]:
        print(f"   {basis}: {prob:.1%}")
    
    # 7) قياس حالة
    print("\n📏 قياس حالة...")
    measurement = qs.measure_state(state1.id)
    print(f"   القيمة المقاسة: {measurement.get('measured_value', 'N/A')}")
    
    # 8) حالة المحرك
    print("\n📊 حالة المحرك الكمومي:")
    status = qs.get_quantum_status()
    print(f"   إجمالي الحالات: {status['total_states']}")
    print(f"   التشابكات: {status['total_entanglements']}")
    print(f"   خطوات التطور: {status['time_evolution_steps']}")
    print(f"   إجمالي القياسات: {status['total_measurements']}")
    
    # 9) تفاصيل حالة
    print("\n🔍 تفاصيل حالة كمومية:")
    details = qs.get_state_details(state1.id)
    if details:
        print(f"   الاسم: {details['name']}")
        print(f"   النوع: {details['type']}")
        print(f"   التماسك: {details['coherence']:.1%}")
        print(f"   متشابكة مع: {details['entangled_with']}")
    
    # 10) السرد
    print(f"\n📖 السرد:\n{snap.narrative}")
    
    # 11) اختبار إعادة التهيئة
    print("\n🔄 اختبار إعادة تهيئة المحرك...")
    qs.reset()
    print("   تم إعادة تهيئة المحرك بنجاح - الحالة نظيفة وجاهزة للاختبارات")
    
    # 12) اقتباس
    print(f"\n💭 {qs.get_quantum_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك الحالة الكمومية الجبار جاهز - تراكب، تشابك، تداخل، انهيار")
    print("=" * 80)
