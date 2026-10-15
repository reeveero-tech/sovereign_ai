# backend/memory/biological/homeostasis.py
# ⚖️ الاتزان المعرفي - حكمة التوازن، استقرار الذكاء
# الإصدار: 3.0.0 - يعرف متى يتحرك ومتى يسكن

"""
نظام الاتزان المعرفي للذاكرة السيادية.

الفلسفة:
- الذكاء يحتاج إلى توازن بين الاستقرار والتغيير
- استقرار مفرط = جمود وموت
- تغيير مفرط = فوضى وانهيار
- الاتزان هو القدرة على العودة إلى المركز بعد أي اضطراب
- الحكمة هي معرفة متى تتحرك ومتى تسكن

هذا ليس مجرد مراقبة. هذا هو قانون التوازن الذاتي.
"""

import json
import time
import threading
import runtime.threads as threads
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import deque
import numpy as np

try:
    from ..core import get_core, IntegrityStatus
    from ..store import get_store, MemoryKind
    from ..dynamic import get_dynamic_memory
    from ..defense.watcher import get_watcher
    from .metabolism import get_metabolism
    from .evolution import get_evolution
    from .regeneration import get_regeneration
    from .immune import get_immune_memory
    from .forgetting import get_forgetting
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, IntegrityStatus
    from memory.store import get_store, MemoryKind
    from memory.dynamic import get_dynamic_memory
    from memory.defense.watcher import get_watcher
    from memory.biological.metabolism import get_metabolism
    from memory.biological.evolution import get_evolution
    from memory.biological.regeneration import get_regeneration
    from memory.biological.immune import get_immune_memory
    from memory.biological.forgetting import get_forgetting
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الاتزان
# ============================================================

HOMEOSTASIS_DIR = DATA_DIR / "homeostasis"
HOMEOSTASIS_LOG = HOMEOSTASIS_DIR / "homeostasis_log.jsonl"
HOMEOSTASIS_STATE_FILE = HOMEOSTASIS_DIR / "homeostasis_state.json"
HOMEOSTASIS_METRICS_FILE = HOMEOSTASIS_DIR / "metrics_history.json"

for d in [HOMEOSTASIS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات الاتزان
BALANCE_LEVEL_CRITICAL = 0      # حرج - يحتاج تدخل فوري
BALANCE_LEVEL_UNSTABLE = 1      # غير مستقر - يحتاج تصحيح
BALANCE_LEVEL_VOLATILE = 2      # متقلب - مراقبة مكثفة
BALANCE_LEVEL_STABLE = 3        # مستقر - تشغيل عادي
BALANCE_LEVEL_OPTIMAL = 4       # مثالي - كل شيء يعمل بشكل ممتاز

# أنواع الاضطرابات
DISTURBANCE_TYPE_MEMORY_LEAK = "memory_leak"
DISTURBANCE_TYPE_COGNITIVE_OVERLOAD = "cognitive_overload"
DISTURBANCE_TYPE_CONCEPTUAL_DRIFT = "conceptual_drift"
DISTURBANCE_TYPE_ENERGY_DEPLETION = "energy_depletion"
DISTURBANCE_TYPE_STRUCTURAL_DEGRADATION = "structural_degradation"
DISTURBANCE_TYPE_EXTERNAL_ATTACK = "external_attack"
DISTURBANCE_TYPE_INTERNAL_CONFLICT = "internal_conflict"

# إجراءات الاستعادة
RESTORE_ACTION_COOLDOWN = "cooldown"          # تبريد
RESTORE_ACTION_CLEANUP = "cleanup"            # تنظيف
RESTORE_ACTION_REBALANCE = "rebalance"        # إعادة توازن
RESTORE_ACTION_REGENERATE = "regenerate"      # تجديد
RESTORE_ACTION_EVOLVE = "evolve"              # تطور
RESTORE_ACTION_RESET = "reset"                # إعادة تعيين جزئي
RESTORE_ACTION_ISOLATE = "isolate"            # عزل


@dataclass
class BalanceSnapshot:
    """لقطة توازن"""
    timestamp: float
    balance_level: int
    health_score: float
    stress_index: float
    entropy: float
    metrics: Dict[str, Any]
    disturbances: List[str]
    actions_taken: List[str]


@dataclass
class Disturbance:
    """اضطراب في النظام"""
    id: str
    type: str
    severity: float  # 0-1
    detected_at: float
    resolved_at: Optional[float]
    cause: str
    affected_components: List[str]


@dataclass
class HomeostasisPolicy:
    """سياسة التوازن"""
    name: str
    target_range: Tuple[float, float]
    current_value: float
    adjustment_rate: float
    last_adjusted: float


# ============================================================
# نظام الاتزان المعرفي
# ============================================================

class CognitiveHomeostasis:
    """
    نظام الاتزان المعرفي - الحكمة في معرفة متى تتحرك ومتى تسكن.
    
    المبادئ:
    1. استقرار مفرط = جمود، تغيير مفرط = فوضى
    2. كل نظام له نقطة توازن مثالية
    3. الاضطرابات طبيعية، المهم هو العودة إلى التوازن
    4. المرونة تأتي من القدرة على التكيف
    5. الحكمة هي معرفة متى تتدخل ومتى تترك الأمور تجري
    """
    
    def __init__(self):
        self.core = get_core()
        self.store = get_store()
        self.dynamic = get_dynamic_memory()
        self.watcher = get_watcher()
        self.metabolism = get_metabolism()
        self.evolution = get_evolution()
        self.regeneration = get_regeneration()
        self.immune = get_immune_memory()
        self.forgetting = get_forgetting()
        
        # حالة الاتزان
        self.balance_level = BALANCE_LEVEL_STABLE
        self.health_score = 0.7
        self.stress_index = 0.3
        self.entropy = 0.4
        
        # سجلات
        self.snapshots: List[BalanceSnapshot] = []
        self.disturbances: List[Disturbance] = []
        self.metrics_history: deque = deque(maxlen=1000)
        
        # سياسات التوازن
        self.policies: Dict[str, HomeostasisPolicy] = self._init_policies()
        
        # معاملات الاستجابة
        self.response_sensitivity = 0.5  # 0-1: حساسية الاستجابة للاضطرابات
        self.recovery_rate = 0.3         # 0-1: سرعة التعافي
        self.intervention_threshold = 0.6 # عتبة التدخل
        
        # خلفيات الاتزان
        self._active = True
        self._monitoring_loop = threads.start_managed(self._continuous_monitoring, owner=self)
        
        self._regulation_loop = threads.start_managed(self._continuous_regulation, owner=self)
        
        self._adaptation_loop = threads.start_managed(self._adaptive_thresholds_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.info("⚖️ نظام الاتزان المعرفي جاهز - الحكمة في التوازن")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لنظام الاتزان المعرفي
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لنظام الاتزان المعرفي.
        
        يمسح:
        - سجل الاضطرابات (disturbances)
        - سجل اللقطات (snapshots)
        - سجل المؤشرات الحيوية (metrics history)
        """
        logger.info("🔄 إعادة تهيئة نظام الاتزان المعرفي...")
        
        # مسح سجل الاضطرابات
        self.disturbances.clear()
        
        # مسح سجل اللقطات
        self.snapshots.clear()
        
        # مسح سجل المؤشرات الحيوية
        self.metrics_history.clear()
        
        # إعادة تعيين حالة الاتزان
        self.balance_level = BALANCE_LEVEL_STABLE
        self.health_score = 0.7
        self.stress_index = 0.3
        self.entropy = 0.4
        
        # إعادة تعيين معاملات الاستجابة
        self.response_sensitivity = 0.5
        self.recovery_rate = 0.3
        self.intervention_threshold = 0.6
        
        # إعادة تعيين السياسات
        self.policies = self._init_policies()
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="biological::homeostasis_reset",
            payload={
                "timestamp": time.time(),
                "status": "homeostasis_system_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة نظام الاتزان المعرفي اكتملت - التوازن استعيد")
    
    def _init_policies(self) -> Dict[str, HomeostasisPolicy]:
        """تهيئة سياسات التوازن"""
        return {
            "memory_growth": HomeostasisPolicy(
                name="memory_growth",
                target_range=(0.3, 0.7),
                current_value=0.5,
                adjustment_rate=0.05,
                last_adjusted=time.time()
            ),
            "cognitive_load": HomeostasisPolicy(
                name="cognitive_load",
                target_range=(0.2, 0.6),
                current_value=0.4,
                adjustment_rate=0.1,
                last_adjusted=time.time()
            ),
            "concept_stability": HomeostasisPolicy(
                name="concept_stability",
                target_range=(0.6, 0.9),
                current_value=0.7,
                adjustment_rate=0.05,
                last_adjusted=time.time()
            ),
            "energy_level": HomeostasisPolicy(
                name="energy_level",
                target_range=(0.4, 0.8),
                current_value=0.6,
                adjustment_rate=0.08,
                last_adjusted=time.time()
            ),
            "structural_integrity": HomeostasisPolicy(
                name="structural_integrity",
                target_range=(0.7, 1.0),
                current_value=0.85,
                adjustment_rate=0.03,
                last_adjusted=time.time()
            )
        }
    
    # ============================================================
    # المستوى 1: مراقبة المؤشرات الحيوية (Vital Signs Monitoring)
    # ============================================================
    
    def monitor_vital_signs(self) -> Dict[str, Any]:
        """
        مراقبة المؤشرات الحيوية للنظام.
        
        المؤشرات:
        - معدل ضربات الذاكرة (تواتر العمليات)
        - ضغط الذاكرة (الحمل)
        - درجة حرارة المفاهيم (استقرارها)
        - مستوى الطاقة المعرفية
        - مرونة النظام
        """
        vital_signs = {}
        
        # 1) معدل ضربات الذاكرة (Memory Heart Rate)
        recent_events = 0
        for event in self.core.iterate_events(limit=100):
            recent_events += 1
        vital_signs["heart_rate"] = min(100, recent_events)
        
        # 2) ضغط الذاكرة (Memory Pressure)
        total_items = 0
        for kind in ["semantic", "procedural", "episodic"]:
            items = self.store.query(kind, min_importance=0.0, limit=1000)
            total_items += len(items)
        vital_signs["memory_pressure"] = min(1.0, total_items / 5000)
        
        # 3) درجة حرارة المفاهيم (Concept Temperature - استقرارها)
        semantic_items = self.store.query("semantic", min_importance=0.0, limit=200)
        if semantic_items:
            importances = [item.get("_importance", 0.5) for item in semantic_items]
            variance = np.var(importances) if len(importances) > 1 else 0
            vital_signs["concept_temperature"] = min(1.0, variance * 2)
        else:
            vital_signs["concept_temperature"] = 0.5
        
        # 4) مستوى الطاقة
        try:
            energy = self.metabolism.get_energy_status()
            vital_signs["energy_level"] = energy.get("total", 0) / 100
        except:
            vital_signs["energy_level"] = 0.5
        
        # 5) مرونة النظام (System Elasticity)
        dynamic_load = len(self.dynamic.working._by_user) / 100
        cache_ratio = self.dynamic.cache.statistics().get("size", 0) / 1000
        vital_signs["elasticity"] = 1 - min(1.0, (dynamic_load + cache_ratio) / 2)
        
        # حساب العلامة الحيوية الإجمالية
        vital_signs["overall"] = (
            (1 - vital_signs["memory_pressure"]) * 0.3 +
            (1 - vital_signs["concept_temperature"]) * 0.2 +
            vital_signs["energy_level"] * 0.3 +
            vital_signs["elasticity"] * 0.2
        )
        
        # تسجيل
        self.metrics_history.append({
            "timestamp": time.time(),
            "vital_signs": vital_signs
        })
        
        return vital_signs
    
    def calculate_entropy(self) -> float:
        """
        حساب الإنتروبيا المعرفية - مقياس الفوضى في النظام.
        
        إنتروبيا منخفضة = نظام منظم
        إنتروبيا عالية = نظام فوضوي
        """
        entropy = 0.0
        
        # 1) إنتروبيا المفاهيم (توزيع المفاهيم)
        semantic_items = self.store.query("semantic", min_importance=0.0, limit=500)
        if semantic_items:
            concept_lengths = [len(item.get("concept", "")) for item in semantic_items]
            if concept_lengths:
                unique_ratios = len(set(concept_lengths)) / max(1, len(concept_lengths))
                entropy += unique_ratios * 0.3
        
        # 2) إنتروبيا الروابط (توزيع قوة الروابط)
        assoc_items = self.store.query("associative", min_importance=0.0, limit=500)
        if assoc_items:
            weights = [item.get("weight", 0.5) for item in assoc_items]
            if weights:
                weight_variance = np.var(weights) if len(weights) > 1 else 0
                entropy += min(1.0, weight_variance) * 0.3
        
        # 3) إنتروبيا النشاط (توزيع النشاط عبر المستخدمين)
        active_users = len(self.dynamic.working._by_user)
        entropy += min(1.0, active_users / 50) * 0.2
        
        # 4) إنتروبيا الذاكرة الحسية
        sensory_count = len(self.dynamic.sensory.get_latest(limit=100))
        entropy += min(1.0, sensory_count / 200) * 0.2
        
        return min(1.0, entropy)
    
    def detect_disturbances(self) -> List[Disturbance]:
        """
        اكتشاف الاضطرابات في النظام.
        
        الاضطرابات هي انحرافات عن التوازن.
        """
        disturbances = []
        vital_signs = self.monitor_vital_signs()
        
        # 1) تسرب ذاكرة (نمو غير طبيعي)
        if vital_signs["memory_pressure"] > 0.8:
            disturbances.append(Disturbance(
                id=f"dist_{int(time.time())}_leak",
                type=DISTURBANCE_TYPE_MEMORY_LEAK,
                severity=vital_signs["memory_pressure"],
                detected_at=time.time(),
                resolved_at=None,
                cause="excessive_memory_growth",
                affected_components=["store", "cache"]
            ))
        
        # 2) حمل إدراكي زائد
        if vital_signs["heart_rate"] > 80:
            disturbances.append(Disturbance(
                id=f"dist_{int(time.time())}_overload",
                type=DISTURBANCE_TYPE_COGNITIVE_OVERLOAD,
                severity=min(1.0, vital_signs["heart_rate"] / 100),
                detected_at=time.time(),
                resolved_at=None,
                cause="high_event_rate",
                affected_components=["dynamic", "working"]
            ))
        
        # 3) انجراف مفاهيمي (مفاهيم غير مستقرة)
        if vital_signs["concept_temperature"] > 0.7:
            disturbances.append(Disturbance(
                id=f"dist_{int(time.time())}_drift",
                type=DISTURBANCE_TYPE_CONCEPTUAL_DRIFT,
                severity=vital_signs["concept_temperature"],
                detected_at=time.time(),
                resolved_at=None,
                cause="unstable_concepts",
                affected_components=["semantic", "evolution"]
            ))
        
        # 4) استنزاف طاقة
        if vital_signs["energy_level"] < 0.3:
            disturbances.append(Disturbance(
                id=f"dist_{int(time.time())}_energy",
                type=DISTURBANCE_TYPE_ENERGY_DEPLETION,
                severity=1 - vital_signs["energy_level"],
                detected_at=time.time(),
                resolved_at=None,
                cause="low_energy",
                affected_components=["metabolism", "all"]
            ))
        
        # تسجيل الاضطرابات الجديدة
        for d in disturbances:
            if not any(ex.id == d.id for ex in self.disturbances):
                self.disturbances.append(d)
                self.core.append_event(
                    event_type="homeostasis::disturbance_detected",
                    payload={
                        "type": d.type,
                        "severity": d.severity,
                        "cause": d.cause
                    }
                )
                logger.warning(f"⚠️ اضطراب مكتشف: {d.type} (شدة: {d.severity:.1%})")
        
        return disturbances
    
    # ============================================================
    # المستوى 2: الحفاظ على التوازن (Balance Maintenance)
    # ============================================================
    
    def calculate_balance_level(self) -> int:
        """
        حساب مستوى التوازن الحالي.
        
        يعتمد على:
        - الصحة العامة
        - مستوى الإجهاد
        - الإنتروبيا
        - الاضطرابات النشطة
        """
        vital = self.monitor_vital_signs()
        entropy = self.calculate_entropy()
        self.entropy = entropy
        
        # تحديث الصحة
        self.health_score = vital["overall"]
        
        # حساب الإجهاد
        active_disturbances = [d for d in self.disturbances if d.resolved_at is None]
        self.stress_index = min(1.0, len(active_disturbances) / 5 + entropy * 0.5)
        
        # تحديد مستوى التوازن
        if self.health_score < 0.3 or self.stress_index > 0.8:
            return BALANCE_LEVEL_CRITICAL
        elif self.health_score < 0.5 or self.stress_index > 0.6:
            return BALANCE_LEVEL_UNSTABLE
        elif self.health_score < 0.7 or self.stress_index > 0.4:
            return BALANCE_LEVEL_VOLATILE
        elif self.health_score < 0.9:
            return BALANCE_LEVEL_STABLE
        else:
            return BALANCE_LEVEL_OPTIMAL
    
    def apply_corrections(self) -> List[str]:
        """
        تطبيق إجراءات تصحيحية للعودة إلى التوازن.
        
        الإجراءات تعتمد على مستوى الاضطراب.
        """
        actions_taken = []
        disturbances = self.detect_disturbances()
        
        for disturbance in disturbances:
            if disturbance.resolved_at is not None:
                continue
            
            if disturbance.type == DISTURBANCE_TYPE_MEMORY_LEAK:
                # تنظيف الذاكرة
                removed = self.metabolism.prune_low_importance(threshold=0.2)
                self.metabolism.burn_noise()
                actions_taken.append(f"cleanup_memory")
                disturbance.resolved_at = time.time()
                
            elif disturbance.type == DISTURBANCE_TYPE_COGNITIVE_OVERLOAD:
                # تبريد النظام
                self.forgetting.forget_everything_temporarily()
                self.metabolism.burn_noise()
                actions_taken.append(f"cooldown_system")
                disturbance.resolved_at = time.time()
                
            elif disturbance.type == DISTURBANCE_TYPE_CONCEPTUAL_DRIFT:
                # تثبيت المفاهيم
                self.evolution.natural_selection()
                actions_taken.append(f"stabilize_concepts")
                disturbance.resolved_at = time.time()
                
            elif disturbance.type == DISTURBANCE_TYPE_ENERGY_DEPLETION:
                # تجديد الطاقة
                self.metabolism.metabolic_cycle(level=3)
                actions_taken.append(f"recharge_energy")
                disturbance.resolved_at = time.time()
        
        # تسجيل الإجراءات
        if actions_taken:
            self.core.append_event(
                event_type="homeostasis::corrections_applied",
                payload={"actions": actions_taken, "timestamp": time.time()}
            )
            logger.info(f"🩺 إجراءات تصحيحية: {', '.join(actions_taken)}")
        
        return actions_taken
    
    def maintain_homeostasis(self) -> BalanceSnapshot:
        """
        دورة الحفاظ على التوازن.
        
        الخطوات:
        1. قياس المؤشرات الحيوية
        2. اكتشاف الاضطرابات
        3. حساب مستوى التوازن
        4. تطبيق الإجراءات التصحيحية
        5. تسجيل اللقطة
        """
        # قياس
        vital = self.monitor_vital_signs()
        disturbances = self.detect_disturbances()
        balance_level = self.calculate_balance_level()
        
        # تحديث مستوى التوازن
        self.balance_level = balance_level
        
        # تطبيق الإجراءات
        actions = []
        if balance_level <= BALANCE_LEVEL_UNSTABLE:
            actions = self.apply_corrections()
        
        # إنشاء لقطة
        snapshot = BalanceSnapshot(
            timestamp=time.time(),
            balance_level=balance_level,
            health_score=self.health_score,
            stress_index=self.stress_index,
            entropy=self.entropy,
            metrics=vital,
            disturbances=[d.type for d in disturbances if d.resolved_at is None],
            actions_taken=actions
        )
        
        self.snapshots.append(snapshot)
        
        # الاحتفاظ بآخر 100 لقطة
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[-100:]
        
        # تسجيل في السجل
        self.core.append_event(
            event_type="homeostasis::snapshot",
            payload={
                "balance_level": balance_level,
                "health_score": self.health_score,
                "stress_index": self.stress_index,
                "active_disturbances": len([d for d in disturbances if d.resolved_at is None])
            }
        )
        
        return snapshot
    
    # ============================================================
    # المستوى 3: التكيف التلقائي (Adaptive Thresholds)
    # ============================================================
    
    def adapt_thresholds(self):
        """
        تكيف عتبات التوازن بناءً على أنماط النظام.
        
        النظام يتعلم أي المستويات هي "طبيعية" له.
        """
        if len(self.snapshots) < 10:
            return
        
        # حساب المتوسطات التاريخية
        recent = self.snapshots[-20:]
        avg_health = sum(s.health_score for s in recent) / len(recent)
        avg_stress = sum(s.stress_index for s in recent) / len(recent)
        
        # تعديل عتبة التدخل بناءً على الأنماط
        if avg_health > 0.8 and avg_stress < 0.3:
            # النظام مستقر جداً - يمكن رفع الحساسية
            self.intervention_threshold = max(0.4, self.intervention_threshold - 0.05)
        elif avg_health < 0.5 or avg_stress > 0.6:
            # النظام غير مستقر - خفض الحساسية لتجنب التقلبات
            self.intervention_threshold = min(0.8, self.intervention_threshold + 0.05)
        
        # تحديث السياسات
        for policy in self.policies.values():
            if policy.current_value < policy.target_range[0]:
                policy.adjustment_rate = min(0.2, policy.adjustment_rate + 0.01)
            elif policy.current_value > policy.target_range[1]:
                policy.adjustment_rate = max(0.02, policy.adjustment_rate - 0.01)
            policy.last_adjusted = time.time()
        
        logger.debug(f"🔄 تكيف العتبات: intervention_threshold = {self.intervention_threshold:.2f}")
    
    # ============================================================
    # الخلفيات المستمرة
    # ============================================================
    
    def _continuous_monitoring(self):
        """مراقبة مستمرة للمؤشرات الحيوية"""
        while self._active:
            try:
                self.monitor_vital_signs()
                threads.interruptible_sleep(10)  # كل 10 ثوانٍ
            except Exception as e:
                logger.error(f"خطأ في المراقبة المستمرة: {e}")
                threads.interruptible_sleep(30)
    
    def _continuous_regulation(self):
        """تنظيم مستمر للحفاظ على التوازن"""
        while self._active:
            try:
                if self.balance_level <= BALANCE_LEVEL_VOLATILE:
                    # مراقبة مكثفة
                    self.maintain_homeostasis()
                    threads.interruptible_sleep(30)
                else:
                    # مراقبة عادية
                    self.maintain_homeostasis()
                    threads.interruptible_sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في التنظيم المستمر: {e}")
                threads.interruptible_sleep(60)
    
    def _adaptive_thresholds_loop(self):
        """تكيف العتبات"""
        while self._active:
            try:
                self.adapt_thresholds()
                threads.interruptible_sleep(3600)  # كل ساعة
            except Exception as e:
                logger.error(f"خطأ في تكيف العتبات: {e}")
                threads.interruptible_sleep(3600)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة نظام الاتزان"""
        try:
            state = {
                "balance_level": self.balance_level,
                "health_score": self.health_score,
                "stress_index": self.stress_index,
                "entropy": self.entropy,
                "response_sensitivity": self.response_sensitivity,
                "recovery_rate": self.recovery_rate,
                "intervention_threshold": self.intervention_threshold,
                "snapshots_count": len(self.snapshots),
                "disturbances_count": len(self.disturbances),
                "saved_at": time.time()
            }
            with open(HOMEOSTASIS_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الاتزان: {e}")
    
    def _load_state(self):
        """تحميل حالة نظام الاتزان"""
        try:
            if HOMEOSTASIS_STATE_FILE.exists():
                with open(HOMEOSTASIS_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.balance_level = state.get("balance_level", BALANCE_LEVEL_STABLE)
                    self.health_score = state.get("health_score", 0.7)
                    self.stress_index = state.get("stress_index", 0.3)
                    self.entropy = state.get("entropy", 0.4)
                    self.response_sensitivity = state.get("response_sensitivity", 0.5)
                    self.recovery_rate = state.get("recovery_rate", 0.3)
                    self.intervention_threshold = state.get("intervention_threshold", 0.6)
                logger.info("📂 تم تحميل حالة نظام الاتزان")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الاتزان: {e}")
    
    # ============================================================
    # التحكم والتقارير
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """الحالة الحالية للاتزان"""
        active_disturbances = [d for d in self.disturbances if d.resolved_at is None]
        
        return {
            "balance_level": self.balance_level,
            "balance_name": ["حرج", "غير مستقر", "متقلب", "مستقر", "مثالي"][self.balance_level],
            "health_score": self.health_score,
            "stress_index": self.stress_index,
            "entropy": self.entropy,
            "active_disturbances": len(active_disturbances),
            "disturbance_types": list(set(d.type for d in active_disturbances)),
            "response_sensitivity": self.response_sensitivity,
            "intervention_threshold": self.intervention_threshold,
            "policies": {name: {
                "current": p.current_value,
                "target_range": p.target_range,
                "adjustment_rate": p.adjustment_rate
            } for name, p in self.policies.items()},
            "timestamp": time.time()
        }
    
    def get_disturbances(self, resolved: Optional[bool] = None) -> List[Dict]:
        """سجل الاضطرابات"""
        if resolved is None:
            disturbances = self.disturbances
        else:
            disturbances = [d for d in self.disturbances if (d.resolved_at is not None) == resolved]
        
        return [
            {
                "id": d.id[:16],
                "type": d.type,
                "severity": d.severity,
                "detected_at": d.detected_at,
                "resolved_at": d.resolved_at,
                "age": time.time() - d.detected_at if d.resolved_at is None else None
            }
            for d in disturbances[-50:]
        ]
    
    def get_snapshots(self, limit: int = 20) -> List[Dict]:
        """لقطات التوازن الأخيرة"""
        return [
            {
                "timestamp": s.timestamp,
                "balance_level": s.balance_level,
                "health_score": s.health_score,
                "stress_index": s.stress_index,
                "entropy": s.entropy,
                "actions": s.actions_taken
            }
            for s in self.snapshots[-limit:]
        ]
    
    def get_vital_signs_history(self, limit: int = 100) -> List[Dict]:
        """سجل المؤشرات الحيوية"""
        return list(self.metrics_history)[-limit:]
    
    def set_policy(self, policy_name: str, target_range: Tuple[float, float]) -> bool:
        """تعيين سياسة توازن جديدة"""
        if policy_name in self.policies:
            self.policies[policy_name].target_range = target_range
            logger.info(f"⚙️ تحديث سياسة {policy_name}: {target_range}")
            return True
        return False
    
    def intervene_manually(self, action: str, params: Dict = None) -> Dict[str, Any]:
        """تدخل يدوي (للسيد) لإعادة التوازن"""
        logger.warning(f"👑 تدخل يدوي: {action}")
        
        result = {"action": action, "success": False, "details": {}}
        
        if action == "force_cleanup":
            removed = self.metabolism.prune_low_importance(threshold=0.1)
            self.metabolism.burn_noise()
            result["success"] = True
            result["details"]["removed"] = removed
            
        elif action == "force_evolution":
            generation = self.evolution.force_evolution_cycle()
            result["success"] = True
            result["details"]["generation"] = generation.number
            
        elif action == "force_regeneration":
            full = self.regeneration.full_regeneration()
            result["success"] = True
            result["details"] = full
            
        elif action == "reset_balance":
            self.balance_level = BALANCE_LEVEL_STABLE
            self.stress_index = 0.3
            result["success"] = True
        
        # تسجيل التدخل
        self.core.append_event(
            event_type="homeostasis::manual_intervention",
            payload={"action": action, "result": result["success"]}
        )
        
        return result
    
    def stop(self):
        """إيقاف نظام الاتزان"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف نظام الاتزان المعرفي")


# ============================================================
# الـ Singleton
# ============================================================

_homeostasis_instance: Optional[CognitiveHomeostasis] = None
_homeostasis_lock = threading.Lock()


def get_homeostasis() -> CognitiveHomeostasis:
    """الحصول على النسخة الوحيدة من نظام الاتزان المعرفي"""
    global _homeostasis_instance
    if _homeostasis_instance is None:
        with _homeostasis_lock:
            if _homeostasis_instance is None:
                _homeostasis_instance = CognitiveHomeostasis()
    return _homeostasis_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("⚖️ نظام الاتزان المعرفي - الحكمة في التوازن")
    print("=" * 70 + "\n")
    
    homeostasis = get_homeostasis()
    
    # 1) المؤشرات الحيوية
    print("📊 المؤشرات الحيوية:")
    vital = homeostasis.monitor_vital_signs()
    for key, value in vital.items():
        if key != "overall":
            print(f"   {key}: {value:.2f}")
    print(f"   الإجمالي: {vital['overall']:.2f}")
    
    # 2) الإنتروبيا
    print(f"\n📈 الإنتروبيا المعرفية: {homeostasis.calculate_entropy():.2f}")
    
    # 3) مستوى التوازن
    print(f"\n⚖️ مستوى التوازن: {homeostasis.calculate_balance_level()}")
    
    # 4) الحفاظ على التوازن
    print("\n🩺 دورة الحفاظ على التوازن:")
    snapshot = homeostasis.maintain_homeostasis()
    print(f"   مستوى التوازن: {snapshot.balance_level}")
    print(f"   الصحة: {snapshot.health_score:.2f}")
    print(f"   الإجهاد: {snapshot.stress_index:.2f}")
    print(f"   الإنتروبيا: {snapshot.entropy:.2f}")
    print(f"   الاضطرابات النشطة: {len(snapshot.disturbances)}")
    print(f"   الإجراءات: {snapshot.actions_taken if snapshot.actions_taken else 'لا شيء'}")
    
    # 5) الحالة الكاملة
    print("\n📋 حالة الاتزان:")
    status = homeostasis.get_status()
    print(f"   المستوى: {status['balance_name']}")
    print(f"   الصحة: {status['health_score']:.2f}")
    print(f"   الإجهاد: {status['stress_index']:.2f}")
    print(f"   الاضطرابات النشطة: {status['active_disturbances']}")
    print(f"   حساسية الاستجابة: {status['response_sensitivity']:.2f}")
    
    # 6) السياسات
    print("\n📜 سياسات التوازن:")
    for name, policy in status['policies'].items():
        print(f"   {name}: {policy['current']:.2f} (هدف: {policy['target_range']})")
    
    print("\n" + "=" * 70)
    print("✅ نظام الاتزان المعرفي جاهز - الحكمة في معرفة متى تتحرك ومتى تسكن")
    print("=" * 70)
