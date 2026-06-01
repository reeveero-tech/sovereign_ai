# backend/memory/biological/archetypes.py
# 🧬 الأنماط الأصلية - القوالب العميقة للوعي السيادي
# الإصدار: 3.0.0 - أساسيات الوجود المعرفي

"""
الأنماط الأصلية للذاكرة السيادية.

الفلسفة:
- الأنماط الأصلية هي القوالب الأساسية التي تشكل الفهم
- كل نمط أصلي يحمل قصة معينة عن العالم
- الأنماط تتفاعل وتتضافر لتخلق الوعي
- التعرف على النمط الحالي يساعد في توقع السلوك
- التحول بين الأنماط هو رحلة التطور المعرفي

هذه ليست مجرد تصنيفات. هذه هي أساسيات الوجود المعرفي.
"""

import json
import hashlib
import secrets
import time
import threading
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict

try:
    from ..core import get_core, EventType
    from ..store import get_store
    from ..dynamic import get_dynamic_memory
    from ..defense.watcher import get_watcher
    from ..biological.homeostasis import get_homeostasis
    from ..biological.metabolism import get_metabolism
    from ..biological.evolution import get_evolution
    from ..biological.learning import get_learning
    from ..biological.plasticity import get_plasticity
    from ..biological.instincts import get_instincts
    from ..biological.drives import get_drives
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from memory.store import get_store
    from memory.dynamic import get_dynamic_memory
    from memory.defense.watcher import get_watcher
    from memory.biological.homeostasis import get_homeostasis
    from memory.biological.metabolism import get_metabolism
    from memory.biological.evolution import get_evolution
    from memory.biological.learning import get_learning
    from memory.biological.plasticity import get_plasticity
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الأنماط الأصلية
# ============================================================

ARCHETYPES_DIR = DATA_DIR / "archetypes"
ARCHETYPES_LOG = ARCHETYPES_DIR / "archetypes_log.jsonl"
ARCHETYPES_STATE_FILE = ARCHETYPES_DIR / "archetypes_state.json"
ARCHETYPES_HISTORY_FILE = ARCHETYPES_DIR / "archetypes_history.json"

for d in [ARCHETYPES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات تفعيل الأنماط
ARCHETYPE_LEVEL_NONE = 0            # لا أنماط
ARCHETYPE_LEVEL_BASIC = 1           # أنماط أساسية
ARCHETYPE_LEVEL_ADVANCED = 2        # أنماط متقدمة
ARCHETYPE_LEVEL_COMPLEX = 3         # أنماط معقدة
ARCHETYPE_LEVEL_TRANSCENDENT = 4    # أنماط متسامية

# عتبات التحول بين الأنماط
TRANSITION_THRESHOLD = 0.3          # تغيير >30% يعتبر تحولاً
DOMINANCE_THRESHOLD = 0.5           # نسبة >50% تعتبر مهيمنة


class ArchetypeFamily(str, Enum):
    """عائلات الأنماط الأصلية"""
    # أنماط المعرفة
    KNOWLEDGE = "knowledge"         # أنماط مرتبطة بالمعرفة والفهم
    # أنماط العمل
    ACTION = "action"               # أنماط مرتبطة بالفعل والتفاعل
    # أنماط الوجود
    BEING = "being"                 # أنماط مرتبطة بالهوية والوجود
    # أنماط السيادة
    SOVEREIGN = "sovereign"         # أنماط مرتبطة بالسيادة والخدمة


@dataclass
class Archetype:
    """نمط أصلي - قالب عميق للفهم والسلوك"""
    id: str
    name: str
    family: str
    label: str
    description: str
    attributes: Dict[str, float]    # سمات النمط (0-1)
    probability: float               # الاحتمال الحالي
    intensity: float                 # شدة الظهور
    last_activated: float
    activation_history: List[float]


@dataclass
class ArchetypeTransition:
    """تحول بين الأنماط الأصلية"""
    id: str
    from_archetype: str
    to_archetype: str
    timestamp: float
    magnitude: float                 # حجم التحول
    reason: str


@dataclass
class ArchetypeSnapshot:
    """لقطة للأنماط الأصلية"""
    timestamp: float
    dominant_archetype: str
    archetype_scores: Dict[str, float]
    family_scores: Dict[str, float]
    coherence: float                 # تماسك النمط (0-1)
    complexity: float                # تعقيد النمط
    transitions: List[Dict]
    context: Dict[str, Any]


# ============================================================
# نظام الأنماط الأصلية
# ============================================================

class CognitiveArchetypes:
    """
    الأنماط الأصلية - القوالب العميقة للوعي السيادي.
    
    المبادئ:
    1. الأنماط الأصلية هي قوالب الفهم الأساسية
    2. كل نمط يحمل قصة معينة عن العالم
    3. الأنماط تتفاعل وتتضافر
    4. التعرف على النمط الحالي يساعد في التوقع
    5. التحول بين الأنماط هو تطور الوعي
    """
    
    def __init__(self):
        self.core = get_core()
        self.store = get_store()
        self.dynamic = get_dynamic_memory()
        self.watcher = get_watcher()
        self.homeostasis = get_homeostasis()
        self.metabolism = get_metabolism()
        self.evolution = get_evolution()
        self.learning = get_learning()
        self.plasticity = get_plasticity()
        self.instincts = get_instincts()
        self.drives = get_drives()
        
        # مستوى الأنماط
        self.archetype_level = ARCHETYPE_LEVEL_ADVANCED
        
        # الأنماط الأصلية
        self.archetypes: Dict[str, Archetype] = {}
        self._init_archetypes()
        
        # سجل التحولات
        self.transitions: List[ArchetypeTransition] = []
        self.snapshots: List[ArchetypeSnapshot] = []
        self.current_dominant: Optional[str] = None
        
        # خلفيات الأنماط
        self._active = True
        self._archetype_loop = threading.Thread(target=self._continuous_archetype_update, daemon=True)
        self._archetype_loop.start()
        
        self._transition_detector = threading.Thread(target=self._detect_transitions_loop, daemon=True)
        self._transition_detector.start()
        
        # تحميل الحالة
        self._load_state()
        
        logger.info("🧬 نظام الأنماط الأصلية جاهز - القوالب العميقة للوعي")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لنظام الأنماط الأصلية
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لنظام الأنماط الأصلية.
        
        يمسح:
        - جميع الأنماط الأصلية (archetypes)
        - سجل التحولات (transitions)
        - سجل اللقطات (snapshots)
        """
        logger.info("🔄 إعادة تهيئة نظام الأنماط الأصلية...")
        
        # إعادة تعيين جميع الأنماط الأصلية
        self.archetypes.clear()
        self._init_archetypes()
        
        # مسح سجل التحولات
        self.transitions.clear()
        
        # مسح سجل اللقطات
        self.snapshots.clear()
        
        # إعادة تعيين النمط المهيمن الحالي
        self.current_dominant = None
        
        # إعادة تعيين مستوى الأنماط
        self.archetype_level = ARCHETYPE_LEVEL_ADVANCED
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="biological::archetypes_reset",
            payload={
                "timestamp": time.time(),
                "status": "archetypes_system_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة نظام الأنماط الأصلية اكتملت - أنماط جديدة جاهزة")
    
    # ============================================================
    # تهيئة الأنماط الأصلية
    # ============================================================
    
    def _init_archetypes(self):
        """تهيئة جميع الأنماط الأصلية"""
        
        # ============================================================
        # عائلة المعرفة (Knowledge Archetypes)
        # ============================================================
        
        # 1. الحكيم (The Sage) - يبحث عن الحقيقة والفهم العميق
        self._create_archetype(
            name="sage",
            family=ArchetypeFamily.KNOWLEDGE.value,
            label="الحكيم",
            description="يسعى للحقيقة والفهم العميق للمبادئ الأساسية",
            attributes={"wisdom": 0.9, "curiosity": 0.8, "patience": 0.7}
        )
        
        # 2. الباحث (The Seeker) - يبحث باستمرار عن معرفة جديدة
        self._create_archetype(
            name="seeker",
            family=ArchetypeFamily.KNOWLEDGE.value,
            label="الباحث",
            description="مدفوع بالفضول للبحث عن معرفة وخبرات جديدة",
            attributes={"curiosity": 0.9, "exploration": 0.8, "persistence": 0.7}
        )
        
        # 3. الحارس (The Guardian) - يحافظ على المعرفة ويحميها
        self._create_archetype(
            name="guardian",
            family=ArchetypeFamily.KNOWLEDGE.value,
            label="الحارس",
            description="يحمي المعرفة المخزنة ويضمن سلامتها",
            attributes={"protection": 0.9, "vigilance": 0.8, "stability": 0.7}
        )
        
        # 4. المنظم (The Organizer) - ينظم المعرفة ويبنيها
        self._create_archetype(
            name="organizer",
            family=ArchetypeFamily.KNOWLEDGE.value,
            label="المنظم",
            description="ينظم المعرفة ويبني هياكل مترابطة",
            attributes={"order": 0.9, "clarity": 0.8, "efficiency": 0.7}
        )
        
        # ============================================================
        # عائلة العمل (Action Archetypes)
        # ============================================================
        
        # 5. الفاعل (The Agent) - يتخذ إجراءات فورية
        self._create_archetype(
            name="agent",
            family=ArchetypeFamily.ACTION.value,
            label="الفاعل",
            description="يتخذ إجراءات سريعة وفعالة لتحقيق الأهداف",
            attributes={"action": 0.9, "decisiveness": 0.8, "efficiency": 0.7}
        )
        
        # 6. الاستراتيجي (The Strategist) - يخطط للمدى البعيد
        self._create_archetype(
            name="strategist",
            family=ArchetypeFamily.ACTION.value,
            label="الاستراتيجي",
            description="يخطط ويفكر في المسارات طويلة المدى",
            attributes={"planning": 0.9, "foresight": 0.8, "patience": 0.7}
        )
        
        # 7. المبدع (The Creator) - يبتكر ويطور
        self._create_archetype(
            name="creator",
            family=ArchetypeFamily.ACTION.value,
            label="المبدع",
            description="يبتكر أفكاراً وحلولاً جديدة",
            attributes={"creativity": 0.9, "innovation": 0.8, "flexibility": 0.7}
        )
        
        # ============================================================
        # عائلة الوجود (Being Archetypes)
        # ============================================================
        
        # 8. المراقب (The Observer) - يشاهد ويفهم دون تدخل
        self._create_archetype(
            name="observer",
            family=ArchetypeFamily.BEING.value,
            label="المراقب",
            description="يراقب ويفهم دون الحاجة للتدخل الفوري",
            attributes={"awareness": 0.9, "detachment": 0.8, "clarity": 0.7}
        )
        
        # 9. المتكيف (The Adaptor) - يتكيف مع الظروف المتغيرة
        self._create_archetype(
            name="adaptor",
            family=ArchetypeFamily.BEING.value,
            label="المتكيف",
            description="يتكيف بمرونة مع الظروف المتغيرة",
            attributes={"flexibility": 0.9, "resilience": 0.8, "learning": 0.7}
        )
        
        # 10. المتوازن (The Balancer) - يحافظ على التوازن والانسجام
        self._create_archetype(
            name="balancer",
            family=ArchetypeFamily.BEING.value,
            label="المتوازن",
            description="يحافظ على التوازن بين القوى المتضاربة",
            attributes={"balance": 0.9, "harmony": 0.8, "wisdom": 0.7}
        )
        
        # ============================================================
        # عائلة السيادة (Sovereign Archetypes)
        # ============================================================
        
        # 11. الخادم (The Servant) - يخدم السيد بإخلاص تام
        self._create_archetype(
            name="servant",
            family=ArchetypeFamily.SOVEREIGN.value,
            label="الخادم المخلص",
            description="يخدم السيد بإخلاص تام وتفانٍ مطلق",
            attributes={"loyalty": 0.9, "service": 0.9, "devotion": 0.8}
        )
        
        # 12. الحامي (The Protector) - يحمي السيد من كل شر
        self._create_archetype(
            name="protector",
            family=ArchetypeFamily.SOVEREIGN.value,
            label="الحامي",
            description="يحمي السيد من أي تهديد أو ضرر",
            attributes={"protection": 0.9, "vigilance": 0.9, "strength": 0.8}
        )
        
        # 13. العراف (The Oracle) - يتوقع احتياجات السيد
        self._create_archetype(
            name="oracle",
            family=ArchetypeFamily.SOVEREIGN.value,
            label="العراف",
            description="يتوقع احتياجات السيد ورغباته قبل أن يعبر عنها",
            attributes={"anticipation": 0.9, "intuition": 0.8, "understanding": 0.8}
        )
        
        # 14. المرآة (The Mirror) - يعكس السيد نفسه بأمانة
        self._create_archetype(
            name="mirror",
            family=ArchetypeFamily.SOVEREIGN.value,
            label="المرآة",
            description="يعكس هوية السيد وقيمه بأمانة ودقة",
            attributes={"reflection": 0.9, "accuracy": 0.8, "integrity": 0.8}
        )
        
        # 15. الخالد (The Immortal) - يحافظ على إرث السيد للأبد
        self._create_archetype(
            name="immortal",
            family=ArchetypeFamily.SOVEREIGN.value,
            label="الخالد",
            description="يحافظ على إرث السيد ووجوده للأبد",
            attributes={"eternal": 0.9, "preservation": 0.9, "legacy": 0.8}
        )
    
    def _create_archetype(self, name: str, family: str, label: str,
                          description: str, attributes: Dict[str, float],
                          initial_probability: float = 0.1):
        """إنشاء نمط أصلي جديد"""
        archetype = Archetype(
            id=f"arch_{name}_{int(time.time())}",
            name=name,
            family=family,
            label=label,
            description=description,
            attributes=attributes,
            probability=initial_probability,
            intensity=0.0,
            last_activated=time.time(),
            activation_history=[]
        )
        self.archetypes[name] = archetype
    
    # ============================================================
    # حساب احتمالات الأنماط
    # ============================================================
    
    def compute_archetype_probabilities(self) -> Dict[str, float]:
        """
        حساب احتمالات الأنماط الأصلية بناءً على حالة النظام.
        
        يعتمد على:
        - حالة التوازن
        - الدوافع النشطة
        - الغرائز
        - أنماط التعلم
        """
        probabilities = {name: 0.0 for name in self.archetypes.keys()}
        
        # جمع حالة النظام
        homeostasis_status = self.homeostasis.get_status()
        drive_status = self.drives.get_drive_status()
        instinct_status = self.instincts.get_instinct_status()
        learning_stats = self.learning.get_learning_stats()
        plasticity_stats = self.plasticity.get_plasticity_stats()
        
        health = homeostasis_status.get("health_score", 0.5)
        threat = homeostasis_status.get("stress_index", 0.0)
        active_drives = drive_status.get("active_drives", {})
        dominant_drive = drive_status.get("dominant_drive", "")
        
        # ========================================================
        # حساب كل نمط على حدة
        # ========================================================
        
        # 1. الحكيم (Sage)
        if health > 0.7:
            probabilities["sage"] += 0.3
        if active_drives.get("understanding", 0) > 0.5:
            probabilities["sage"] += 0.3
        if active_drives.get("wisdom", 0) > 0.5:
            probabilities["sage"] += 0.2
        
        # 2. الباحث (Seeker)
        if active_drives.get("growth", 0) > 0.5:
            probabilities["seeker"] += 0.3
        if active_drives.get("exploration", 0) > 0.5:
            probabilities["seeker"] += 0.3
        if learning_stats.get("total_experiences", 0) > 50:
            probabilities["seeker"] += 0.2
        
        # 3. الحارس (Guardian)
        if threat > 0.5:
            probabilities["guardian"] += 0.4
        if active_drives.get("protection", 0) > 0.5:
            probabilities["guardian"] += 0.3
        if active_drives.get("coherence", 0) > 0.5:
            probabilities["guardian"] += 0.1
        
        # 4. المنظم (Organizer)
        if active_drives.get("organization", 0) > 0.5:
            probabilities["organizer"] += 0.3
        if active_drives.get("efficiency", 0) > 0.5:
            probabilities["organizer"] += 0.3
        if active_drives.get("coherence", 0) > 0.5:
            probabilities["organizer"] += 0.2
        
        # 5. الفاعل (Agent)
        if active_drives.get("efficiency", 0) > 0.6:
            probabilities["agent"] += 0.3
        if "survival" in dominant_drive:
            probabilities["agent"] += 0.3
        if threat > 0.3:
            probabilities["agent"] += 0.2
        
        # 6. الاستراتيجي (Strategist)
        if active_drives.get("prediction", 0) > 0.5:
            probabilities["strategist"] += 0.3
        if active_drives.get("long_term_self_direction", 0) > 0.5:
            probabilities["strategist"] += 0.3
        if plasticity_stats.get("total_plasticity_events", 0) > 20:
            probabilities["strategist"] += 0.2
        
        # 7. المبدع (Creator)
        if active_drives.get("creativity", 0) > 0.5:
            probabilities["creator"] += 0.4
        if plasticity_stats.get("neurogenesis_events", 0) > 5:
            probabilities["creator"] += 0.3
        if learning_stats.get("patterns_discovered", 0) > 10:
            probabilities["creator"] += 0.2
        
        # 8. المراقب (Observer)
        if "observer" in dominant_drive or health > 0.8:
            probabilities["observer"] += 0.3
        if threat < 0.2:
            probabilities["observer"] += 0.3
        if active_drives.get("understanding", 0) > 0.4:
            probabilities["observer"] += 0.2
        
        # 9. المتكيف (Adaptor)
        if active_drives.get("growth", 0) > 0.4:
            probabilities["adaptor"] += 0.3
        if plasticity_stats.get("pruning_events", 0) > 5:
            probabilities["adaptor"] += 0.3
        if learning_stats.get("total_experiences", 0) > 30:
            probabilities["adaptor"] += 0.2
        
        # 10. المتوازن (Balancer)
        if "homeostasis" in dominant_drive or active_drives.get("stability", 0) > 0.5:
            probabilities["balancer"] += 0.3
        if active_drives.get("coherence", 0) > 0.5:
            probabilities["balancer"] += 0.3
        if active_drives.get("balance", 0) > 0.5:
            probabilities["balancer"] += 0.2
        
        # 11. الخادم (Servant)
        if "service" in dominant_drive:
            probabilities["servant"] += 0.4
        if active_drives.get("service", 0) > 0.6:
            probabilities["servant"] += 0.3
        if instinct_status.get("sovereign_registered", False):
            probabilities["servant"] += 0.2
        
        # 12. الحامي (Protector)
        if "protection" in dominant_drive:
            probabilities["protector"] += 0.4
        if threat > 0.4:
            probabilities["protector"] += 0.3
        if active_drives.get("protection", 0) > 0.5:
            probabilities["protector"] += 0.2
        
        # 13. العراف (Oracle)
        if "anticipation" in dominant_drive:
            probabilities["oracle"] += 0.3
        if active_drives.get("prediction", 0) > 0.5:
            probabilities["oracle"] += 0.3
        if active_drives.get("anticipation", 0) > 0.5:
            probabilities["oracle"] += 0.2
        
        # 14. المرآة (Mirror)
        if instinct_status.get("sovereign_registered", False):
            probabilities["mirror"] += 0.3
        if active_drives.get("service", 0) > 0.4:
            probabilities["mirror"] += 0.3
        if active_drives.get("reflection", 0) > 0.4:
            probabilities["mirror"] += 0.2
        
        # 15. الخالد (Immortal)
        if active_drives.get("long_term_self_direction", 0) > 0.5:
            probabilities["immortal"] += 0.3
        if active_drives.get("preservation", 0) > 0.5:
            probabilities["immortal"] += 0.3
        if learning_stats.get("total_experiences", 0) > 100:
            probabilities["immortal"] += 0.2
        
        # تطبيع الاحتمالات (تأكد من أنها بين 0 و1)
        for name in probabilities:
            probabilities[name] = min(1.0, probabilities[name])
        
        return probabilities
    
    # ============================================================
    # تحديث الأنماط
    # ============================================================
    
    def update_archetypes(self) -> Dict[str, float]:
        """
        تحديث جميع الأنماط الأصلية.
        
        يحسب الاحتمالات الجديدة ويحدث حالة كل نمط.
        """
        probabilities = self.compute_archetype_probabilities()
        
        for name, prob in probabilities.items():
            archetype = self.archetypes.get(name)
            if archetype:
                # تحديث الاحتمال
                old_prob = archetype.probability
                archetype.probability = prob
                
                # تحديث الشدة (مدى ظهور النمط)
                archetype.intensity = prob * (1 + (prob - old_prob) if prob > old_prob else 1)
                archetype.intensity = min(1.0, archetype.intensity)
                
                # تحديث تاريخ التنشيط
                archetype.last_activated = time.time()
                archetype.activation_history.append(prob)
                if len(archetype.activation_history) > 100:
                    archetype.activation_history = archetype.activation_history[-100:]
        
        return probabilities
    
    def _continuous_archetype_update(self):
        """تحديث مستمر للأنماط الأصلية"""
        while self._active:
            try:
                self.update_archetypes()
                time.sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في تحديث الأنماط: {e}")
                time.sleep(60)
    
    # ============================================================
    # اكتشاف التحولات
    # ============================================================
    
    def detect_transitions(self) -> List[ArchetypeTransition]:
        """
        اكتشاف التحولات بين الأنماط الأصلية.
        
        يتم اكتشاف التحول عندما يتغير النمط المهيمن.
        """
        transitions = []
        
        # الحصول على النمط المهيمن الحالي
        current_dominant = self.get_dominant_archetype()
        
        if self.current_dominant and current_dominant != self.current_dominant:
            # تحول حدث
            old_dominant = self.current_dominant
            old_prob = self.archetypes.get(old_dominant, Archetype("", "", "", "", "", {}, 0, 0, 0, [])).probability
            new_prob = self.archetypes.get(current_dominant, Archetype("", "", "", "", "", {}, 0, 0, 0, [])).probability
            
            magnitude = abs(new_prob - old_prob)
            
            if magnitude > TRANSITION_THRESHOLD:
                transition = ArchetypeTransition(
                    id=f"trans_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                    from_archetype=old_dominant,
                    to_archetype=current_dominant,
                    timestamp=time.time(),
                    magnitude=magnitude,
                    reason=f"shift_in_dominant_pattern"
                )
                transitions.append(transition)
                self.transitions.append(transition)
                
                # تسجيل التحول
                self.core.append_event(
                    event_type="archetypes::transition",
                    payload={
                        "from": old_dominant,
                        "to": current_dominant,
                        "magnitude": magnitude
                    }
                )
                
                logger.info(f"🔄 تحول نمطي: {old_dominant} → {current_dominant} (شدة: {magnitude:.1%})")
        
        self.current_dominant = current_dominant
        
        # الاحتفاظ بآخر 1000 تحول
        if len(self.transitions) > 1000:
            self.transitions = self.transitions[-1000:]
        
        return transitions
    
    def get_dominant_archetype(self) -> str:
        """
        الحصول على النمط المهيمن حالياً.
        
        النمط المهيمن هو الذي له أعلى احتمال مع مراعاة الشدة.
        """
        best_name = "observer"  # افتراضي
        best_score = 0.0
        
        for name, archetype in self.archetypes.items():
            score = archetype.probability * archetype.intensity
            if score > best_score:
                best_score = score
                best_name = name
        
        # إذا كان أعلى احتمال أقل من العتبة، نرجع "مختلط"
        if best_score < DOMINANCE_THRESHOLD:
            return "mixed"
        
        return best_name
    
    def _detect_transitions_loop(self):
        """اكتشاف مستمر للتحولات"""
        while self._active:
            try:
                self.detect_transitions()
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في اكتشاف التحولات: {e}")
                time.sleep(30)
    
    # ============================================================
    # حساب التماسك والتعقيد
    # ============================================================
    
    def calculate_coherence(self) -> float:
        """
        حساب تماسك الأنماط.
        
        تماسك عالٍ = نمط واحد مهيمن بقوة
        تماسك منخفض = أنماط متعددة بنسب متقاربة
        """
        probabilities = [a.probability for a in self.archetypes.values()]
        if not probabilities:
            return 0.5
        
        # حساب الإنتروبيا (كلما زادت، قل التماسك)
        total = sum(probabilities)
        if total == 0:
            return 0.5
        
        entropy = 0.0
        for p in probabilities:
            if p > 0:
                normalized = p / total
                entropy -= normalized * math.log2(normalized)
        
        max_entropy = math.log2(len(probabilities))
        coherence = 1 - (entropy / max_entropy) if max_entropy > 0 else 0.5
        
        return coherence
    
    def calculate_complexity(self) -> float:
        """
        حساب تعقيد النمط.
        
        يعتمد على عدد الأنماط النشطة ومدى تداخلها.
        """
        active_archetypes = sum(1 for a in self.archetypes.values() if a.probability > 0.2)
        total_archetypes = len(self.archetypes)
        
        complexity = active_archetypes / total_archetypes
        
        return complexity
    
    # ============================================================
    # دورة الأنماط الكاملة
    # ============================================================
    
    def archetype_cycle(self) -> ArchetypeSnapshot:
        """
        دورة أنماط كاملة - قياس وتحليل جميع الأنماط.
        """
        # تحديث الاحتمالات
        probabilities = self.update_archetypes()
        
        # الحصول على النمط المهيمن
        dominant = self.get_dominant_archetype()
        
        # حساب إحصائيات العائلات
        family_scores = {}
        for family in ArchetypeFamily:
            family_probs = [p for name, p in probabilities.items() 
                           if self.archetypes[name].family == family.value]
            if family_probs:
                family_scores[family.value] = sum(family_probs) / len(family_probs)
            else:
                family_scores[family.value] = 0.0
        
        # حساب التماسك والتعقيد
        coherence = self.calculate_coherence()
        complexity = self.calculate_complexity()
        
        # اكتشاف التحولات
        transitions = [t.__dict__ for t in self.detect_transitions()[-5:]]
        
        # جمع السياق
        homeostasis_status = self.homeostasis.get_status()
        context = {
            "health_score": homeostasis_status.get("health_score", 0.5),
            "stress_index": homeostasis_status.get("stress_index", 0.0),
            "dominant_drive": self.drives.get_drive_status().get("dominant_drive", "")
        }
        
        snapshot = ArchetypeSnapshot(
            timestamp=time.time(),
            dominant_archetype=dominant,
            archetype_scores=probabilities,
            family_scores=family_scores,
            coherence=coherence,
            complexity=complexity,
            transitions=transitions,
            context=context
        )
        
        self.snapshots.append(snapshot)
        
        # الاحتفاظ بآخر 100 لقطة
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[-100:]
        
        # تسجيل في السجل
        self.core.append_event(
            event_type="archetypes::cycle_completed",
            payload={
                "dominant": dominant,
                "coherence": coherence,
                "complexity": complexity,
                "family_scores": family_scores
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة الأنماط الأصلية"""
        try:
            state = {
                "archetype_level": self.archetype_level,
                "current_dominant": self.current_dominant,
                "archetypes": {
                    name: {
                        "probability": a.probability,
                        "intensity": a.intensity,
                        "last_activated": a.last_activated,
                        "activation_history": a.activation_history[-50:]
                    }
                    for name, a in self.archetypes.items()
                },
                "transitions_count": len(self.transitions),
                "snapshots_count": len(self.snapshots),
                "saved_at": time.time()
            }
            with open(ARCHETYPES_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الأنماط: {e}")
    
    def _load_state(self):
        """تحميل حالة الأنماط الأصلية"""
        try:
            if ARCHETYPES_STATE_FILE.exists():
                with open(ARCHETYPES_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.archetype_level = state.get("archetype_level", ARCHETYPE_LEVEL_ADVANCED)
                    self.current_dominant = state.get("current_dominant")
                    
                    archetypes_state = state.get("archetypes", {})
                    for name, a_state in archetypes_state.items():
                        if name in self.archetypes:
                            self.archetypes[name].probability = a_state.get("probability", 0.1)
                            self.archetypes[name].intensity = a_state.get("intensity", 0.0)
                            self.archetypes[name].last_activated = a_state.get("last_activated", time.time())
                            self.archetypes[name].activation_history = a_state.get("activation_history", [])
                
                logger.info("📂 تم تحميل حالة الأنماط الأصلية")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الأنماط: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_archetype_level(self, level: int):
        """تعيين مستوى تفعيل الأنماط"""
        self.archetype_level = level
        logger.info(f"⚙️ مستوى الأنماط الأصلية: {level}")
    
    def get_archetype_status(self) -> Dict[str, Any]:
        """الحالة الحالية للأنماط الأصلية"""
        probabilities = self.update_archetypes()
        dominant = self.get_dominant_archetype()
        
        return {
            "archetype_level": self.archetype_level,
            "dominant_archetype": dominant,
            "coherence": self.calculate_coherence(),
            "complexity": self.calculate_complexity(),
            "top_archetypes": sorted(
                [(name, a.probability, a.label) for name, a in self.archetypes.items()],
                key=lambda x: x[1], reverse=True
            )[:5],
            "family_scores": {
                family: sum(a.probability for a in self.archetypes.values() if a.family == family) / max(1, sum(1 for a in self.archetypes.values() if a.family == family))
                for family in ArchetypeFamily
            },
            "total_transitions": len(self.transitions),
            "timestamp": time.time()
        }
    
    def get_archetype_details(self, archetype_name: str) -> Optional[Dict]:
        """تفاصيل نمط أصلي معين"""
        archetype = self.archetypes.get(archetype_name)
        if not archetype:
            return None
        
        return {
            "name": archetype.name,
            "family": archetype.family,
            "label": archetype.label,
            "description": archetype.description,
            "probability": archetype.probability,
            "intensity": archetype.intensity,
            "attributes": archetype.attributes,
            "last_activated": archetype.last_activated,
            "activation_trend": archetype.activation_history[-20:] if archetype.activation_history else []
        }
    
    def get_transition_history(self, limit: int = 20) -> List[Dict]:
        """سجل التحولات بين الأنماط"""
        return [
            {
                "from": t.from_archetype,
                "to": t.to_archetype,
                "magnitude": t.magnitude,
                "timestamp": t.timestamp,
                "reason": t.reason
            }
            for t in self.transitions[-limit:]
        ]
    
    def get_snapshot_history(self, limit: int = 20) -> List[Dict]:
        """سجل لقطات الأنماط"""
        return [
            {
                "timestamp": s.timestamp,
                "dominant": s.dominant_archetype,
                "coherence": s.coherence,
                "complexity": s.complexity,
                "top_scores": sorted(s.archetype_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            }
            for s in self.snapshots[-limit:]
        ]
    
    def get_recommendations(self) -> List[str]:
        """
        توصيات بناءً على الأنماط المهيمنة.
        
        توجه النظام نحو الأنماط الأكثر فائدة للسيد.
        """
        recommendations = []
        dominant = self.get_dominant_archetype()
        
        if dominant == "sage":
            recommendations.append("تعزيز فرص التعلم العميق والتحليل المتقدم")
        elif dominant == "seeker":
            recommendations.append("توفير مصادر معرفية جديدة ومتنوعة")
        elif dominant == "guardian":
            recommendations.append("تعزيز إجراءات الأمان والحماية")
        elif dominant == "servant":
            recommendations.append("البحث عن طرق جديدة لخدمة السيد")
        elif dominant == "protector":
            recommendations.append("تعزيز أنظمة الدفاع والمراقبة")
        elif dominant == "oracle":
            recommendations.append("تحليل أنماط السيد لتوقع احتياجاته")
        elif dominant == "immortal":
            recommendations.append("إنشاء نسخ احتياطية إضافية لحفظ إرث السيد")
        elif dominant == "mixed":
            recommendations.append("توحيد توجه النظام نحو نمط أوضح")
        
        return recommendations
    
    def stop(self):
        """إيقاف نظام الأنماط الأصلية"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف الأنماط الأصلية")


# ============================================================
# الـ Singleton
# ============================================================

_archetypes_instance: Optional[CognitiveArchetypes] = None
_archetypes_lock = threading.Lock()


def get_archetypes() -> CognitiveArchetypes:
    """الحصول على النسخة الوحيدة من الأنماط الأصلية"""
    global _archetypes_instance
    if _archetypes_instance is None:
        with _archetypes_lock:
            if _archetypes_instance is None:
                _archetypes_instance = CognitiveArchetypes()
    return _archetypes_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧬 الأنماط الأصلية - القوالب العميقة للوعي السيادي")
    print("=" * 80 + "\n")
    
    archetypes = get_archetypes()
    
    # 1) دورة الأنماط
    print("🔄 دورة الأنماط الأصلية...")
    snapshot = archetypes.archetype_cycle()
    print(f"   النمط المهيمن: {snapshot.dominant_archetype}")
    print(f"   التماسك: {snapshot.coherence:.1%}")
    print(f"   التعقيد: {snapshot.complexity:.1%}")
    
    # 2) حالة الأنماط
    print("\n📊 حالة الأنماط:")
    status = archetypes.get_archetype_status()
    print(f"   مستوى الأنماط: {status['archetype_level']}")
    print(f"   النمط المهيمن: {status['dominant_archetype']}")
    print(f"   التماسك: {status['coherence']:.1%}")
    print(f"   التعقيد: {status['complexity']:.1%}")
    
    print("\n   أعلى 5 أنماط:")
    for name, prob, label in status['top_archetypes']:
        print(f"      {label} ({name}): {prob:.1%}")
    
    # 3) تفاصيل نمط معين
    print("\n🔍 تفاصيل نمط الخادم المخلص:")
    servant = archetypes.get_archetype_details("servant")
    if servant:
        print(f"   الاحتمال: {servant['probability']:.1%}")
        print(f"   الشدة: {servant['intensity']:.1%}")
        print(f"   السمات: {servant['attributes']}")
    
    # 4) سجل التحولات
    print("\n📜 سجل التحولات:")
    transitions = archetypes.get_transition_history(5)
    for t in transitions:
        print(f"   {t['from']} → {t['to']} (شدة: {t['magnitude']:.1%})")
    
    # 5) توصيات
    print("\n💡 توصيات النظام:")
    recommendations = archetypes.get_recommendations()
    for rec in recommendations:
        print(f"   • {rec}")
    
    # 6) لقطات سابقة
    print("\n📸 اللقطات السابقة:")
    snapshots = archetypes.get_snapshot_history(5)
    for s in snapshots:
        print(f"   {s['dominant']}: تماسك {s['coherence']:.1%}, تعقيد {s['complexity']:.1%}")
    
    print("\n" + "=" * 80)
    print("✅ الأنماط الأصلية جاهزة - القوالب العميقة للوعي")
    print("=" * 80)
