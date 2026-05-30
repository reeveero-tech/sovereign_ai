# backend/quantum/quantum_transition.py
# ⚛️ محرك الانتقالات الكمية الجبار - انتقالات كمومية متقدمة
# الإصدار: 3.1.0 - مع دعم إعادة التهيئة الكاملة للاختبارات التكاملية

"""
محرك الانتقالات الكمية للعقل السيادي.

الفلسفة:
- الانتقالات الكمية تحرك النظام بين الحالات
- مصفوفة الانتقال تحدد احتمالات كل مسار
- الطور والتداخل يؤثران على الانتقالات
- التضخيم يسرع الانتقالات المرغوبة
- التثبيط يبطئ الانتقالات غير المرغوبة

هذه ليست مجرد احتمالات. هذه هي ديناميكا النظام الكمي.
"""

import json
import math
import cmath
import random
import secrets
import threading
import time
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict

try:
    from ..memory.core import get_core, EventType
    from .quantum_state import get_quantum_state_engine, QuantumAmplitude
    from ..config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from quantum_state import get_quantum_state_engine, QuantumAmplitude
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الانتقالات الكمومية
# ============================================================

QUANTUM_TRANSITION_DIR = DATA_DIR / "quantum" / "transition"
QUANTUM_TRANSITION_DIR.mkdir(parents=True, exist_ok=True)
QUANTUM_TRANSITION_LOG = QUANTUM_TRANSITION_DIR / "quantum_transition_log.jsonl"
QUANTUM_TRANSITION_STATE_FILE = QUANTUM_TRANSITION_DIR / "quantum_transition_state.json"

# أنواع الانتقالات
TRANSITION_TYPE_PROBABILISTIC = "probabilistic"    # احتمالي (عشوائي حسب الاحتمالات)
TRANSITION_TYPE_DIRECTED = "directed"              # موجه (من حالة محددة إلى أخرى)
TRANSITION_TYPE_AMPLIFIED = "amplified"            # مضخم (متسارع)
TRANSITION_TYPE_SUPPRESSED = "suppressed"          # مثبط (متباطئ)
TRANSITION_TYPE_RESONANT = "resonant"              # رنيني (طاقة متطابقة)
TRANSITION_TYPE_TUNNELING = "tunneling"            # نفق (عبور حاجز)
TRANSITION_TYPE_STIMULATED = "stimulated"          # محفز (بفعل خارجي)

# عوامل التأثير على الانتقالات
INFLUENCE_PHASE = "phase"           # تأثير الطور
INFLUENCE_INTERFERENCE = "interference"  # تأثير التداخل
INFLUENCE_ENERGY = "energy"         # تأثير الطاقة
INFLUENCE_DEVIATION = "deviation"   # تأثير الانحراف


@dataclass
class TransitionAmplitude:
    """سعة انتقال كمومي"""
    from_state: str
    to_state: str
    amplitude: complex
    probability: float
    energy_delta: float
    phase_match: float
    resonance: float


@dataclass
class TransitionMatrix:
    """مصفوفة انتقال كمومية"""
    states: List[str]
    matrix: np.ndarray
    probabilities: np.ndarray
    eigenvalues: List[complex]
    eigenvectors: List[np.ndarray]
    entropy: float
    mixing_time: float


@dataclass
class QuantumTransitionSnapshot:
    """لقطة انتقال كمومي"""
    timestamp: float
    transition_matrix: Dict[str, Dict[str, float]]
    updated_amplitudes: Dict[str, complex]
    probabilities: Dict[str, float]
    dominant_transition: Optional[Tuple[str, str]]
    transition_entropy: float
    mixing_rate: float
    narrative: str


# ============================================================
# محرك الانتقالات الكمومية الجبار
# ============================================================

class QuantumTransitionEngine:
    """
    محرك الانتقالات الكمومية الجبار - انتقالات كمومية متقدمة.
    
    المبادئ:
    1. الانتقالات تحرك النظام بين الحالات
    2. مصفوفة الانتقال تحدد احتمالات كل مسار
    3. الطور والتداخل يؤثران على الانتقالات
    4. التضخيم يسرع الانتقالات المرغوبة
    5. التثبيط يبطئ الانتقالات غير المرغوبة
    """
    
    def __init__(self):
        self.core = get_core()
        self.qstate = get_quantum_state_engine()
        
        # سجل الانتقالات
        self.transition_history: List[QuantumTransitionSnapshot] = []
        self.transition_matrix_history: List[Dict] = []
        
        # معاملات الانتقال
        self.hamiltonian: Optional[np.ndarray] = None
        self.energy_levels: Dict[str, float] = {}
        
        # السياسات الافتراضية (لإعادة التهيئة)
        self._default_policies = {
            "base_transition_strength": 0.25,
            "phase_influence": 0.15,
            "interference_influence": 0.2,
            "amplification_threshold": 0.65,
            "suppression_threshold": 0.35,
        }
        self.policies = self._default_policies.copy()
        
        # خلفيات الانتقالات
        self._active = True
        self._continuous_transitions = threading.Thread(target=self._continuous_transition_loop, daemon=True)
        self._continuous_transitions.start()
        
        self._matrix_evolution = threading.Thread(target=self._matrix_evolution_loop, daemon=True)
        self._matrix_evolution.start()
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("⚛️ محرك الانتقالات الكمومية الجبار جاهز - انتقالات كمومية متقدمة")
    
    # ============================================================
    # إعادة التهيئة الكاملة (للاختبارات التكاملية)
    # ============================================================
    
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك الانتقال الكمّي.
        
        - لا يملك حالة amplitudes خاصة به (يستخدم qstate)
        - لكن يملك سياسات وفهرس داخلي يجب إعادة تهيئتها
        - لا نحذف الملفات على القرص إلا إذا طلب المستخدم
        - تسجل عملية إعادة التهيئة في السجل السيادي
        """
        logger.info("🔄 إعادة تهيئة محرك الانتقالات الكمومية...")
        
        # إعادة تحميل الفهرس من جديد (تفريغ السجلات)
        self.transition_history.clear()
        self.transition_matrix_history.clear()
        self.energy_levels.clear()
        
        # إعادة تهيئة السياسات الافتراضية
        self.policies = self._default_policies.copy()
        
        # تسجيل عملية إعادة التهيئة في السجل السيادي
        self.core.append_event(
            event_type="quantum::transition::reset",
            payload={
                "timestamp": time.time(),
                "status": "quantum_transition_engine_reset",
                "policies_reset": True,
                "history_cleared": True
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك الانتقالات الكمومية اكتملت")
    
    def reset_policies(self):
        """
        إعادة تعيين السياسات فقط (بدون مسح التاريخ).
        
        مفيد عندما نريد الاحتفاظ بسجل الانتقالات لكن إعادة ضبط السلوك.
        """
        self.policies = self._default_policies.copy()
        logger.debug("🔄 إعادة تعيين سياسات محرك الانتقالات الكمومية إلى القيم الافتراضية")
    
    # ============================================================
    # بناء مصفوفة الانتقال
    # ============================================================
    
    def build_transition_matrix(self, state_id: str = None) -> TransitionMatrix:
        """
        بناء مصفوفة الانتقال الكمومية الكاملة.
        
        تحسب احتمالات الانتقال بين جميع أزواج الحالات.
        """
        if state_id is None:
            if self.qstate.current_state:
                state_id = self.qstate.current_state.id
            elif self.qstate.states:
                state_id = list(self.qstate.states.keys())[0]
            else:
                # إنشاء حالة افتراضية
                self.qstate.create_state("default", ["|0>", "|1>"])
                state_id = self.qstate.current_state.id
        
        state = self.qstate.states.get(state_id)
        if not state:
            return None
        
        bases = list(state.amplitudes.keys())
        n = len(bases)
        
        # بناء مصفوفة هاميلتوني
        H = np.zeros((n, n), dtype=complex)
        
        # تعيين مستويات الطاقة
        for i, basis in enumerate(bases):
            if basis not in self.energy_levels:
                self.energy_levels[basis] = random.uniform(0.5, 1.5)
            H[i, i] = self.energy_levels[basis]
        
        # تعيين عناصر خارج القطر (تفاعلات)
        for i in range(n):
            for j in range(i + 1, n):
                # حساب قوة التفاعل
                phase_diff = abs(state.amplitudes[bases[i]].phase() - state.amplitudes[bases[j]].phase())
                interference = abs(state.amplitudes[bases[i]].to_complex() - state.amplitudes[bases[j]].to_complex())
                
                coupling = (0.1 + phase_diff * 0.2 + interference * 0.1) * random.uniform(0.5, 1.5)
                
                # طور عشوائي
                phase = cmath.exp(1j * random.uniform(0, 2 * math.pi))
                H[i, j] = coupling * phase
                H[j, i] = np.conj(H[i, j])
        
        # حساب eigenvalues والمتجهات الذاتية
        eigenvalues, eigenvectors = np.linalg.eigh(H)
        
        # بناء مصفوفة الاحتمالات
        P = np.zeros((n, n), dtype=float)
        
        # الوقت (محاكاة)
        t = 1.0
        
        # مصفوفة التطور U = e^{-iHt}
        U = np.zeros((n, n), dtype=complex)
        for k in range(n):
            U += np.outer(eigenvectors[:, k], eigenvectors[:, k].conj()) * cmath.exp(-1j * eigenvalues[k] * t)
        
        # حساب الاحتمالات
        for i in range(n):
            for j in range(n):
                P[i, j] = abs(U[i, j]) ** 2
        
        # تطبيع الصفوف
        for i in range(n):
            row_sum = np.sum(P[i, :])
            if row_sum > 0:
                P[i, :] /= row_sum
        
        # حساب إنتروبيا المصفوفة
        matrix_entropy = 0.0
        for i in range(n):
            for j in range(n):
                if P[i, j] > 0:
                    matrix_entropy -= P[i, j] * math.log2(P[i, j])
        
        max_entropy = math.log2(n) if n > 1 else 1
        normalized_entropy = matrix_entropy / max_entropy if max_entropy > 0 else 0
        
        # حساب وقت الخلط (mixing time)
        mixing_time = self._calculate_mixing_time(P)
        
        # تخزين المصفوفة
        transition_matrix = TransitionMatrix(
            states=bases,
            matrix=H,
            probabilities=P,
            eigenvalues=list(eigenvalues),
            eigenvectors=[eigenvectors[:, k] for k in range(n)],
            entropy=normalized_entropy,
            mixing_time=mixing_time
        )
        
        return transition_matrix
    
    def _calculate_mixing_time(self, P: np.ndarray) -> float:
        """حساب وقت الخلط - متى تصل المصفوفة إلى التوزيع الثابت"""
        n = P.shape[0]
        
        # حساب القيمة الذاتية الثانية (spectral gap)
        eigvals = np.linalg.eigvals(P)
        eigvals_sorted = np.sort(np.abs(eigvals))[::-1]
        
        if len(eigvals_sorted) > 1:
            spectral_gap = 1 - eigvals_sorted[1]
            if spectral_gap > 0:
                mixing_time = -1 / math.log(1 - spectral_gap)
            else:
                mixing_time = float('inf')
        else:
            mixing_time = float('inf')
        
        return min(100.0, mixing_time)
    
    # ============================================================
    # أنواع الانتقالات المختلفة
    # ============================================================
    
    def probabilistic_transition(self, state_id: str) -> Tuple[str, str, float]:
        """
        انتقال احتمالي - اختيار عشوائي حسب الاحتمالات.
        """
        transition_matrix = self.build_transition_matrix(state_id)
        if not transition_matrix:
            return None
        
        state = self.qstate.states.get(state_id)
        bases = list(state.amplitudes.keys())
        
        # العثور على الحالة الحالية الأكثر احتمالاً
        probs = {b: state.amplitudes[b].probability() for b in bases}
        current_state = max(probs, key=probs.get)
        current_idx = bases.index(current_state)
        
        # اختيار الحالة التالية حسب الاحتمالات
        row_probs = transition_matrix.probabilities[current_idx, :]
        next_idx = np.random.choice(len(bases), p=row_probs)
        next_state = bases[next_idx]
        
        transition_prob = row_probs[next_idx]
        
        logger.debug(f"⚛️ انتقال احتمالي: {current_state} → {next_state} (احتمال {transition_prob:.1%})")
        
        return current_state, next_state, transition_prob
    
    def directed_transition(self, state_id: str, target_state: str) -> Tuple[str, str, float]:
        """
        انتقال موجه - من الحالة الحالية إلى حالة محددة.
        """
        transition_matrix = self.build_transition_matrix(state_id)
        if not transition_matrix:
            return None
        
        state = self.qstate.states.get(state_id)
        bases = list(state.amplitudes.keys())
        
        if target_state not in bases:
            return None
        
        # العثور على الحالة الحالية
        probs = {b: state.amplitudes[b].probability() for b in bases}
        current_state = max(probs, key=probs.get)
        current_idx = bases.index(current_state)
        target_idx = bases.index(target_state)
        
        transition_prob = transition_matrix.probabilities[current_idx, target_idx]
        
        # تعزيز سعة الحالة المستهدفة
        target_amp = state.amplitudes[target_state]
        new_amp = complex(target_amp.real * (1 + transition_prob), target_amp.imag * (1 + transition_prob))
        state.amplitudes[target_state] = QuantumAmplitude.from_complex(new_amp)
        
        # إعادة تطبيع
        state.amplitudes = self.qstate._normalize_amplitudes(state.amplitudes)
        
        logger.info(f"⚛️ انتقال موجه: {current_state} → {target_state} (احتمال {transition_prob:.1%})")
        
        return current_state, target_state, transition_prob
    
    def amplified_transition(self, state_id: str, amplification_factor: float = 1.5) -> str:
        """
        انتقال مضخم - تسريع الانتقال إلى الحالة الأكثر احتمالاً.
        """
        transition_matrix = self.build_transition_matrix(state_id)
        if not transition_matrix:
            return None
        
        state = self.qstate.states.get(state_id)
        bases = list(state.amplitudes.keys())
        
        # العثور على الحالة الحالية
        probs = {b: state.amplitudes[b].probability() for b in bases}
        current_state = max(probs, key=probs.get)
        current_idx = bases.index(current_state)
        
        # تضخيم الانتقالات إلى الحالة الأكثر احتمالاً
        amplified_probs = transition_matrix.probabilities[current_idx, :] ** amplification_factor
        amplified_probs = amplified_probs / np.sum(amplified_probs)
        
        next_idx = np.random.choice(len(bases), p=amplified_probs)
        next_state = bases[next_idx]
        
        transition_prob = amplified_probs[next_idx]
        
        # تعزيز الانتقال
        target_amp = state.amplitudes[next_state]
        new_amp = complex(target_amp.real * (1 + transition_prob * 0.5),
                         target_amp.imag * (1 + transition_prob * 0.5))
        state.amplitudes[next_state] = QuantumAmplitude.from_complex(new_amp)
        
        # إضعاف الحالة الحالية
        current_amp = state.amplitudes[current_state]
        current_amp.real *= 0.8
        current_amp.imag *= 0.8
        state.amplitudes[current_state] = current_amp
        
        # إعادة تطبيع
        state.amplitudes = self.qstate._normalize_amplitudes(state.amplitudes)
        
        logger.info(f"⚛️ انتقال مضخم: {current_state} → {next_state} (عامل {amplification_factor:.1f})")
        
        return next_state
    
    def suppressed_transition(self, state_id: str, suppression_factor: float = 0.5) -> str:
        """
        انتقال مثبط - إبطاء الانتقال إلى حالات معينة.
        """
        transition_matrix = self.build_transition_matrix(state_id)
        if not transition_matrix:
            return None
        
        state = self.qstate.states.get(state_id)
        bases = list(state.amplitudes.keys())
        
        # العثور على الحالة الحالية
        probs = {b: state.amplitudes[b].probability() for b in bases}
        current_state = max(probs, key=probs.get)
        current_idx = bases.index(current_state)
        
        # تثبيط الانتقالات (الحفاظ على الحالة الحالية)
        suppressed_probs = transition_matrix.probabilities[current_idx, :] ** suppression_factor
        suppressed_probs = suppressed_probs / np.sum(suppressed_probs)
        
        # زيادة احتمال البقاء
        suppressed_probs[current_idx] *= 2
        suppressed_probs = suppressed_probs / np.sum(suppressed_probs)
        
        next_idx = np.random.choice(len(bases), p=suppressed_probs)
        next_state = bases[next_idx]
        
        logger.info(f"⚛️ انتقال مثبط: {current_state} → {next_state} (عامل {suppression_factor:.1f})")
        
        return next_state
    
    def resonant_transition(self, state_id: str, energy_match_threshold: float = 0.1) -> Optional[Tuple[str, str]]:
        """
        انتقال رنيني - بين حالات ذات طاقة متقاربة.
        """
        transition_matrix = self.build_transition_matrix(state_id)
        if not transition_matrix:
            return None
        
        # البحث عن أزواج ذات طاقة متقاربة
        resonant_pairs = []
        bases = transition_matrix.states
        
        for i in range(len(bases)):
            for j in range(i + 1, len(bases)):
                energy_diff = abs(self.energy_levels.get(bases[i], 0) - self.energy_levels.get(bases[j], 0))
                if energy_diff < energy_match_threshold:
                    resonant_pairs.append((bases[i], bases[j], transition_matrix.probabilities[i, j]))
        
        if not resonant_pairs:
            return None
        
        # اختيار زوج رنيني عشوائي
        selected = random.choice(resonant_pairs)
        
        logger.info(f"⚛️ انتقال رنيني: {selected[0]} ↔ {selected[1]} (فرق طاقة {abs(self.energy_levels.get(selected[0], 0) - self.energy_levels.get(selected[1], 0)):.3f})")
        
        return selected[0], selected[1]
    
    # ============================================================
    # تطبيق الانتقالات على الحالة الكمومية
    # ============================================================
    
    def apply_transition(self, state_id: str, transition_type: str = "probabilistic",
                         params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        تطبيق انتقال كمومي على الحالة.
        
        Args:
            state_id: معرف الحالة الكمومية
            transition_type: نوع الانتقال
            params: معاملات إضافية للانتقال
        """
        if params is None:
            params = {}
        
        result = {
            "transition_type": transition_type,
            "success": False,
            "from_state": None,
            "to_state": None,
            "probability": 0.0
        }
        
        if transition_type == TRANSITION_TYPE_PROBABILISTIC:
            transition = self.probabilistic_transition(state_id)
            if transition:
                result["success"] = True
                result["from_state"], result["to_state"], result["probability"] = transition
        
        elif transition_type == TRANSITION_TYPE_DIRECTED:
            target = params.get("target_state")
            if target:
                transition = self.directed_transition(state_id, target)
                if transition:
                    result["success"] = True
                    result["from_state"], result["to_state"], result["probability"] = transition
        
        elif transition_type == TRANSITION_TYPE_AMPLIFIED:
            factor = params.get("amplification_factor", 1.5)
            to_state = self.amplified_transition(state_id, factor)
            if to_state:
                result["success"] = True
                result["to_state"] = to_state
                result["probability"] = 0.8
        
        elif transition_type == TRANSITION_TYPE_SUPPRESSED:
            factor = params.get("suppression_factor", 0.5)
            to_state = self.suppressed_transition(state_id, factor)
            if to_state:
                result["success"] = True
                result["to_state"] = to_state
                result["probability"] = 0.3
        
        elif transition_type == TRANSITION_TYPE_RESONANT:
            transition = self.resonant_transition(state_id)
            if transition:
                result["success"] = True
                result["from_state"], result["to_state"] = transition
                result["probability"] = 0.6
        
        # تحديث الحالة الكمومية
        if result["success"] and result.get("to_state"):
            # تعزيز الحالة المستهدفة
            state = self.qstate.states.get(state_id)
            if state:
                target_amp = state.amplitudes.get(result["to_state"])
                if target_amp:
                    new_amp = complex(target_amp.real * 1.2, target_amp.imag * 1.2)
                    state.amplitudes[result["to_state"]] = QuantumAmplitude.from_complex(new_amp)
                    state.amplitudes = self.qstate._normalize_amplitudes(state.amplitudes)
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::transition_applied",
            payload={
                "state_id": state_id[:16],
                "type": transition_type,
                "success": result["success"],
                "to_state": result.get("to_state")
            }
        )
        
        return result
    
    # ============================================================
    # دورة انتقال كمومية كاملة
    # ============================================================
    
    def transition_cycle(self, state_id: str = None) -> QuantumTransitionSnapshot:
        """
        دورة انتقال كمومية كاملة.
        
        1. بناء مصفوفة الانتقال
        2. حساب الاحتمالات الجديدة
        3. تطبيق انتقال عشوائي
        4. تحديث الحالة
        """
        if state_id is None:
            if self.qstate.current_state:
                state_id = self.qstate.current_state.id
            elif self.qstate.states:
                state_id = list(self.qstate.states.keys())[0]
            else:
                self.qstate.create_state("default", ["|0>", "|1>"])
                state_id = self.qstate.current_state.id
        
        # بناء مصفوفة الانتقال
        transition_matrix = self.build_transition_matrix(state_id)
        
        # اختيار نوع انتقال عشوائي
        transition_types = [
            TRANSITION_TYPE_PROBABILISTIC,
            TRANSITION_TYPE_RESONANT,
            TRANSITION_TYPE_AMPLIFIED
        ]
        chosen_type = random.choice(transition_types)
        
        # تطبيق الانتقال
        result = self.apply_transition(state_id, chosen_type)
        
        # الحصول على الحالة المحدثة
        state = self.qstate.states.get(state_id)
        
        # حساب الاحتمالات الجديدة
        probabilities = {}
        if state:
            probabilities = {b: amp.probability() for b, amp in state.amplitudes.items()}
        
        # تحويل مصفوفة الانتقال إلى قاموس
        matrix_dict = {}
        if transition_matrix:
            for i, s1 in enumerate(transition_matrix.states):
                matrix_dict[s1] = {}
                for j, s2 in enumerate(transition_matrix.states):
                    matrix_dict[s1][s2] = transition_matrix.probabilities[i, j]
        
        # حساب إنتروبيا الانتقال
        transition_entropy = transition_matrix.entropy if transition_matrix else 0
        
        # حساب معدل الخلط
        mixing_rate = 1.0 / transition_matrix.mixing_time if transition_matrix and transition_matrix.mixing_time > 0 else 0
        
        # السرد
        narrative = self.generate_transition_narrative(result, transition_entropy, mixing_rate)
        
        # السعة المحدثة
        updated_amplitudes = {}
        if state:
            updated_amplitudes = {b: amp.to_complex() for b, amp in state.amplitudes.items()}
        
        snapshot = QuantumTransitionSnapshot(
            timestamp=time.time(),
            transition_matrix=matrix_dict,
            updated_amplitudes=updated_amplitudes,
            probabilities=probabilities,
            dominant_transition=(result.get("from_state"), result.get("to_state")) if result.get("from_state") and result.get("to_state") else None,
            transition_entropy=transition_entropy,
            mixing_rate=mixing_rate,
            narrative=narrative
        )
        
        self.transition_history.append(snapshot)
        
        # الاحتفاظ بآخر 100 لقطة
        if len(self.transition_history) > 100:
            self.transition_history = self.transition_history[-100:]
        
        # تسجيل
        self.core.append_event(
            event_type="quantum::transition_cycle_completed",
            payload={
                "state_id": state_id[:16],
                "transition_type": result.get("transition_type"),
                "success": result.get("success"),
                "entropy": transition_entropy
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    def generate_transition_narrative(self, result: Dict, entropy: float, mixing_rate: float) -> str:
        """
        توليد سرد للانتقال الكمومي.
        """
        narrative = "⚛️ **الانتقال الكمومي**\n"
        
        if result.get("success"):
            narrative += f"📋 **النوع**: {result['transition_type']}\n"
            if result.get("from_state"):
                narrative += f"➡️ **من**: {result['from_state']}\n"
            if result.get("to_state"):
                narrative += f"🎯 **إلى**: {result['to_state']}\n"
            narrative += f"📊 **الاحتمال**: {result.get('probability', 0):.1%}\n"
        else:
            narrative += "❌ فشل الانتقال.\n"
        
        narrative += f"🌀 **إنتروبيا الانتقال**: {entropy:.1%}\n"
        narrative += f"⚡ **معدل الخلط**: {mixing_rate:.1%}\n"
        
        if entropy > 0.7:
            narrative += "🌊 نظام ذو إنتروبيا عالية - فوضى كمومية.\n"
        elif entropy < 0.3:
            narrative += "🎯 نظام ذو إنتروبيا منخفضة -秩序 كمومي.\n"
        
        return narrative
    
    def _continuous_transition_loop(self):
        """انتقالات كمومية مستمرة"""
        while self._active:
            try:
                if self.qstate.states:
                    state_id = random.choice(list(self.qstate.states.keys()))
                    self.transition_cycle(state_id)
                
                time.sleep(5)  # كل 5 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في حلقة الانتقالات المستمرة: {e}")
                time.sleep(5)
    
    def _matrix_evolution_loop(self):
        """تطور مصفوفة الانتقال مع الزمن"""
        while self._active:
            try:
                # تحديث مستويات الطاقة ببطء
                for state in self.energy_levels:
                    drift = random.uniform(-0.01, 0.01)
                    self.energy_levels[state] = max(0.1, min(2.0, self.energy_levels[state] + drift))
                
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في تطور المصفوفة: {e}")
                time.sleep(30)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة محرك الانتقالات"""
        try:
            state = {
                "energy_levels": self.energy_levels,
                "transition_history_count": len(self.transition_history),
                "policies": self.policies,
                "saved_at": time.time()
            }
            with open(QUANTUM_TRANSITION_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الانتقالات: {e}")
    
    def _load_state(self):
        """تحميل حالة محرك الانتقالات"""
        try:
            if QUANTUM_TRANSITION_STATE_FILE.exists():
                with open(QUANTUM_TRANSITION_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.energy_levels = state.get("energy_levels", {})
                    saved_policies = state.get("policies", {})
                    if saved_policies:
                        self.policies.update(saved_policies)
                logger.info("📂 تم تحميل حالة محرك الانتقالات")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الانتقالات: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_policy(self, key: str, value: float) -> bool:
        """
        تعيين سياسة تشغيلية.
        
        Args:
            key: اسم السياسة (base_transition_strength, phase_influence, etc.)
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
    
    def get_transition_status(self, state_id: str = None) -> Dict[str, Any]:
        """الحالة الحالية لمحرك الانتقالات"""
        if state_id is None and self.qstate.current_state:
            state_id = self.qstate.current_state.id
        
        transition_matrix = self.build_transition_matrix(state_id)
        
        return {
            "state_id": state_id[:16] if state_id else None,
            "matrix_dimension": len(transition_matrix.states) if transition_matrix else 0,
            "matrix_entropy": transition_matrix.entropy if transition_matrix else 0,
            "mixing_time": transition_matrix.mixing_time if transition_matrix else 0,
            "energy_levels": self.energy_levels,
            "total_transitions": len(self.transition_history),
            "policies": self.policies,
            "timestamp": time.time()
        }
    
    def get_transition_matrix(self, state_id: str = None) -> Optional[Dict]:
        """الحصول على مصفوفة الانتقال الحالية"""
        transition_matrix = self.build_transition_matrix(state_id)
        
        if not transition_matrix:
            return None
        
        matrix_dict = {}
        for i, s1 in enumerate(transition_matrix.states):
            matrix_dict[s1] = {}
            for j, s2 in enumerate(transition_matrix.states):
                matrix_dict[s1][s2] = transition_matrix.probabilities[i, j]
        
        return {
            "states": transition_matrix.states,
            "matrix": matrix_dict,
            "entropy": transition_matrix.entropy,
            "mixing_time": transition_matrix.mixing_time
        }
    
    def get_transition_history(self, limit: int = 20) -> List[Dict]:
        """سجل الانتقالات"""
        return [
            {
                "timestamp": t.timestamp,
                "dominant": t.dominant_transition,
                "entropy": t.transition_entropy,
                "mixing_rate": t.mixing_rate
            }
            for t in self.transition_history[-limit:]
        ]
    
    def get_transition_quote(self) -> str:
        """اقتباس عن الانتقالات الكمومية"""
        quotes = [
            "الانتقالات الكمومية تحرك النظام بين الاحتمالات.",
            "مصفوفة الانتقال تحدد مسارات المستقبل.",
            "التضخيم يسرع التحولات المرغوبة.",
            "التثبيط يمنع التحولات غير المرغوبة.",
            "الرنين يخلق قنوات انتقال فعالة.",
            "النفق الكمومي يسمح بعبور الحواجز المستحيلة.",
            "الإنتروبيا تقيس فوضى الانتقالات."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محرك الانتقالات"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف محرك الانتقالات الكمومية")


# ============================================================
# الـ Singleton
# ============================================================

_qtransition_instance: Optional[QuantumTransitionEngine] = None
_qtransition_lock = threading.Lock()


def get_quantum_transition_engine() -> QuantumTransitionEngine:
    """الحصول على النسخة الوحيدة من محرك الانتقالات الكمومية"""
    global _qtransition_instance
    if _qtransition_instance is None:
        with _qtransition_lock:
            if _qtransition_instance is None:
                _qtransition_instance = QuantumTransitionEngine()
    return _qtransition_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("⚛️ محرك الانتقالات الكمومية الجبار - انتقالات كمومية متقدمة")
    print("=" * 80 + "\n")
    
    # تهيئة الحالة الكمومية
    qs = get_quantum_state_engine()
    state = qs.create_state("نظام كمومي", ["حالة_أ", "حالة_ب", "حالة_ج", "حالة_د"])
    qs.create_superposition(state.id)
    
    qt = get_quantum_transition_engine()
    
    # 1) بناء مصفوفة الانتقال
    print("⚛️ بناء مصفوفة الانتقال...")
    matrix = qt.get_transition_matrix(state.id)
    if matrix:
        print(f"   الأبعاد: {len(matrix['states'])}x{len(matrix['states'])}")
        print(f"   الإنتروبيا: {matrix['entropy']:.1%}")
        print(f"   وقت الخلط: {matrix['mixing_time']:.2f}")
    
    # 2) انتقال احتمالي
    print("\n🎲 انتقال احتمالي...")
    result = qt.apply_transition(state.id, TRANSITION_TYPE_PROBABILISTIC)
    print(f"   النجاح: {result['success']}")
    if result['success']:
        print(f"   من: {result.get('from_state')} → إلى: {result.get('to_state')}")
        print(f"   الاحتمال: {result.get('probability', 0):.1%}")
    
    # 3) انتقال موجه
    print("\n🎯 انتقال موجه...")
    result = qt.apply_transition(state.id, TRANSITION_TYPE_DIRECTED, {"target_state": "حالة_ج"})
    print(f"   النجاح: {result['success']}")
    if result['success']:
        print(f"   من: {result.get('from_state')} → إلى: {result.get('to_state')}")
    
    # 4) انتقال مضخم
    print("\n⚡ انتقال مضخم...")
    result = qt.apply_transition(state.id, TRANSITION_TYPE_AMPLIFIED, {"amplification_factor": 2.0})
    print(f"   النجاح: {result['success']}")
    if result['success']:
        print(f"   إلى: {result.get('to_state')}")
    
    # 5) انتقال رنيني
    print("\n🔔 انتقال رنيني...")
    result = qt.apply_transition(state.id, TRANSITION_TYPE_RESONANT)
    print(f"   النجاح: {result['success']}")
    if result['success']:
        print(f"   من: {result.get('from_state')} → إلى: {result.get('to_state')}")
    
    # 6) دورة انتقال كاملة
    print("\n🔄 دورة انتقال كاملة...")
    snapshot = qt.transition_cycle(state.id)
    print(f"   الانتقال المهيمن: {snapshot.dominant_transition}")
    print(f"   إنتروبيا الانتقال: {snapshot.transition_entropy:.1%}")
    print(f"   معدل الخلط: {snapshot.mixing_rate:.1%}")
    
    # 7) الاحتمالات الجديدة
    print("\n📊 الاحتمالات الجديدة:")
    for basis, prob in list(snapshot.probabilities.items()):
        print(f"   {basis}: {prob:.1%}")
    
    # 8) حالة المحرك
    print("\n📊 حالة محرك الانتقالات:")
    status = qt.get_transition_status(state.id)
    print(f"   بُعد المصفوفة: {status['matrix_dimension']}")
    print(f"   إنتروبيا المصفوفة: {status['matrix_entropy']:.1%}")
    print(f"   وقت الخلط: {status['mixing_time']:.2f}")
    print(f"   إجمالي الانتقالات: {status['total_transitions']}")
    
    # 9) اختبار إعادة التهيئة
    print("\n🔄 اختبار إعادة تهيئة محرك الانتقالات...")
    qt.reset()
    print("   تم إعادة تهيئة محرك الانتقالات بنجاح - الحالة نظيفة وجاهزة للاختبارات")
    
    # 10) السرد
    print(f"\n📖 السرد:\n{snapshot.narrative}")
    
    # 11) اقتباس
    print(f"\n💭 {qt.get_transition_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك الانتقالات الكمومية الجبار جاهز - انتقالات كمومية متقدمة")
    print("=" * 80)
