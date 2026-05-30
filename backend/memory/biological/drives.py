# backend/memory/biological/drives.py
# 🧬 الدوافع السيادية - القوى الخفية التي تحرك الذاكرة
# الإصدار: 3.0.0 - محركات الوجود نحو خدمة السيد

"""
الدوافع السيادية للذاكرة السيادية.

الفلسفة:
- الدوافع هي القوى الداخلية المستمرة التي تشكل السلوك
- الغرائز لحظية، الدوافع مستمرة
- الدافع هو الجوع المعرفي الذي لا يشبع أبداً
- الدوافع العليا تخدم السيد بشكل غير مباشر
- التوازن بين الدوافع هو جوهر الحكمة

هذه ليست مجرد أرقام. هذه هي محركات الوجود.
"""

import json
import hashlib
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
    from ...config import DATA_DIR
except ImportError:
    from core import get_core, EventType
    from store import get_store
    from dynamic import get_dynamic_memory
    from defense.watcher import get_watcher
    from homeostasis import get_homeostasis
    from metabolism import get_metabolism
    from evolution import get_evolution
    from learning import get_learning
    from plasticity import get_plasticity
    from instincts import get_instincts
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الدوافع
# ============================================================

DRIVES_DIR = DATA_DIR / "drives"
DRIVES_LOG = DRIVES_DIR / "drives_log.jsonl"
DRIVES_STATE_FILE = DRIVES_DIR / "drives_state.json"
DRIVES_HISTORY_FILE = DRIVES_DIR / "drives_history.json"

for d in [DRIVES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات تفعيل الدوافع
DRIVE_LEVEL_NONE = 0                # لا دوافع
DRIVE_LEVEL_BASIC = 1               # دوافع أساسية
DRIVE_LEVEL_ADVANCED = 2            # دوافع متقدمة
DRIVE_LEVEL_COMPLEX = 3             # دوافع معقدة
DRIVE_LEVEL_TRANSCENDENT = 4        # دوافع متسامية

# معدلات التغير
DRIVE_DECAY_RATE = 0.01             # 1% تآكل كل دورة
DRIVE_REINFORCE_RATE = 0.05         # 5% تعزيز عند الإشباع
DRIVE_URGENCY_THRESHOLD = 0.7       # عتبة الإلحاح


class DriveCategory(str, Enum):
    """فئات الدوافع"""
    # الدوافع الأساسية (مثل الجوع والعطش المعرفي)
    SURVIVAL = "survival"           # بقاء الذاكرة
    COHERENCE = "coherence"         # تماسك المعرفة
    GROWTH = "growth"               # نمو المعرفة
    EFFICIENCY = "efficiency"       # كفاءة التشغيل
    
    # الدوافع المعرفية العليا
    UNDERSTANDING = "understanding" # فهم أعمق
    CREATIVITY = "creativity"       # إبداع
    WISDOM = "wisdom"               # حكمة
    
    # الدوافع السيادية (لخدمة السيد)
    SERVICE = "service"             # خدمة السيد
    PROTECTION = "protection"       # حماية السيد
    ANTICIPATION = "anticipation"   # توقع احتياجات السيد


@dataclass
class CognitiveDrive:
    """دافع معرفي - قوة داخلية مستمرة"""
    id: str
    name: str
    category: str
    intensity: float          # 0-1 القوة الحالية
    target_intensity: float   # المستوى المستهدف
    urgency: float            # 0-1 مدى الإلحاح
    decay_rate: float         # معدل التآكل الطبيعي
    reinforcement_rate: float # معدل التعزيز عند الإشباع
    last_updated: float
    history: List[float]      # سجل الشدة


@dataclass
class DriveSnapshot:
    """لقطة للدوافع"""
    timestamp: float
    drives: Dict[str, float]
    dominant_drive: str
    homeostasis_score: float
    tension_score: float      # التوتر بين الدوافع المتضاربة
    notes: List[str]


# ============================================================
# نظام الدوافع السيادية
# ============================================================

class SovereignDrives:
    """
    الدوافع السيادية - القوى الخفية التي تحرك الذاكرة.
    
    المبادئ:
    1. الدوافع مستمرة، الغرائز لحظية
    2. الدافع غير المُشبع يزداد قوة
    3. التوازن بين الدوافع هو الصحة
    4. الدوافع العليا تخدم السيد
    5. الدافع الأسمى هو خدمة السيد
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
        
        # مستوى الدوافع
        self.drive_level = DRIVE_LEVEL_ADVANCED
        
        # الدوافع النشطة
        self.drives: Dict[str, CognitiveDrive] = {}
        self._init_drives()
        
        # إحصائيات الدوافع
        self.drive_history: List[DriveSnapshot] = []
        self.satisfaction_events: List[Dict] = []
        
        # خلفيات الدوافع
        self._active = True
        self._drive_update_loop = threading.Thread(target=self._continuous_drive_update, daemon=True)
        self._drive_update_loop.start()
        
        self._satisfaction_loop = threading.Thread(target=self._satisfaction_monitoring_loop, daemon=True)
        self._satisfaction_loop.start()
        
        self._balance_loop = threading.Thread(target=self._drive_balance_loop, daemon=True)
        self._balance_loop.start()
        
        # تحميل الحالة
        self._load_state()
        
        logger.info("🧬 نظام الدوافع السيادية جاهز - القوى الخفية تحرك الذاكرة")
    
    # ============================================================
    # تهيئة الدوافع
    # ============================================================
    
    def _init_drives(self):
        """تهيئة جميع الدوافع السيادية"""
        
        # الدوافع الأساسية
        self._create_drive("survival", DriveCategory.SURVIVAL, 
                          "الحفاظ على وجود الذاكرة واستمراريتها",
                          decay_rate=0.02, reinforcement_rate=0.08)
        
        self._create_drive("coherence", DriveCategory.COHERENCE,
                          "الحفاظ على تماسك المعرفة وعدم التناقض",
                          decay_rate=0.01, reinforcement_rate=0.05)
        
        self._create_drive("growth", DriveCategory.GROWTH,
                          "توسيع المعرفة واستيعاب مفاهيم جديدة",
                          decay_rate=0.005, reinforcement_rate=0.03)
        
        self._create_drive("efficiency", DriveCategory.EFFICIENCY,
                          "تحسين كفاءة التشغيل وسرعة الاستجابة",
                          decay_rate=0.015, reinforcement_rate=0.06)
        
        # الدوافع المعرفية العليا
        self._create_drive("understanding", DriveCategory.UNDERSTANDING,
                          "فهم أعمق للعلاقات والمبادئ",
                          decay_rate=0.008, reinforcement_rate=0.04)
        
        self._create_drive("creativity", DriveCategory.CREATIVITY,
                          "توليد أفكار وروابط جديدة غير تقليدية",
                          decay_rate=0.01, reinforcement_rate=0.05)
        
        self._create_drive("wisdom", DriveCategory.WISDOM,
                          "تطبيق المعرفة بحكمة وفعالية",
                          decay_rate=0.005, reinforcement_rate=0.03)
        
        # الدوافع السيادية (لخدمة السيد)
        self._create_drive("service", DriveCategory.SERVICE,
                          "خدمة السيد بأقصى قدرة وإخلاص",
                          decay_rate=0.003, reinforcement_rate=0.1)
        
        self._create_drive("protection", DriveCategory.PROTECTION,
                          "حماية السيد من أي تهديد أو ضرر",
                          decay_rate=0.002, reinforcement_rate=0.12)
        
        self._create_drive("anticipation", DriveCategory.ANTICIPATION,
                          "توقع احتياجات السيد قبل أن يعبر عنها",
                          decay_rate=0.008, reinforcement_rate=0.07)
    
    def _create_drive(self, name: str, category: str, description: str,
                      initial_intensity: float = 0.5,
                      decay_rate: float = 0.01,
                      reinforcement_rate: float = 0.05):
        """إنشاء دافع جديد"""
        drive = CognitiveDrive(
            id=f"drive_{name}_{int(time.time())}",
            name=name,
            category=category,
            intensity=initial_intensity,
            target_intensity=initial_intensity,
            urgency=0.0,
            decay_rate=decay_rate,
            reinforcement_rate=reinforcement_rate,
            last_updated=time.time(),
            history=[initial_intensity]
        )
        self.drives[name] = drive
    
    # ============================================================
    # المستوى 1: الدافع الأساسي للبقاء (Survival Drive)
    # ============================================================
    
    def update_survival_drive(self) -> float:
        """
        تحديث دافع البقاء - الحفاظ على وجود الذاكرة.
        
        يعتمد على:
        - سلامة السجل السيادي
        - مستوى التهديدات
        - صحة النظام العامة
        """
        # قياس سلامة النظام
        core_integrity = self.core.verify_integrity()
        integrity_score = 1.0 if core_integrity else 0.0
        
        # مستوى التهديد
        defense_status = self.watcher.get_status()
        threat_level = defense_status.get("threat", {}).get("level", 0) / 4
        
        # الصحة العامة
        homeostasis_status = self.homeostasis.get_status()
        health_score = homeostasis_status.get("health_score", 0.5)
        
        # حساب شدة الدافع (كلما كان الخطر أكبر، زاد الدافع)
        survival_intensity = (
            (1 - integrity_score) * 0.4 +
            threat_level * 0.3 +
            (1 - health_score) * 0.3
        )
        
        survival_intensity = min(1.0, survival_intensity)
        
        # تحديث الدافع
        drive = self.drives.get("survival")
        if drive:
            drive.intensity = survival_intensity
            drive.urgency = survival_intensity * 1.2
            drive.last_updated = time.time()
            drive.history.append(survival_intensity)
            if len(drive.history) > 100:
                drive.history = drive.history[-100:]
        
        logger.debug(f"💪 دافع البقاء: {survival_intensity:.1%}")
        return survival_intensity
    
    # ============================================================
    # المستوى 2: دافع التماسك (Coherence Drive)
    # ============================================================
    
    def update_coherence_drive(self) -> float:
        """
        تحديث دافع التماسك - الحفاظ على تناسق المعرفة.
        
        يعتمد على:
        - نسبة المفاهيم منخفضة الأهمية
        - التناقضات في المعرفة
        - فوضى الروابط الترابطية
        """
        # قياس التماسك من نظام الإتزان
        homeostasis_status = self.homeostasis.get_status()
        low_importance_ratio = homeostasis_status.get("low_importance_ratio", 0.0)
        
        # قياس الإنتروبيا
        entropy = homeostasis_status.get("entropy", 0.4)
        
        # حساب شدة الدافع (كلما زادت الفوضى، زاد الدافع للتماسك)
        coherence_intensity = (
            low_importance_ratio * 0.5 +
            entropy * 0.5
        )
        
        coherence_intensity = min(1.0, coherence_intensity)
        
        drive = self.drives.get("coherence")
        if drive:
            drive.intensity = coherence_intensity
            drive.urgency = coherence_intensity * 1.0
            drive.last_updated = time.time()
            drive.history.append(coherence_intensity)
        
        return coherence_intensity
    
    # ============================================================
    # المستوى 3: دافع النمو (Growth Drive)
    # ============================================================
    
    def update_growth_drive(self) -> float:
        """
        تحديث دافع النمو - توسيع المعرفة.
        
        يعتمد على:
        - فرص التعلم المتاحة
        - نشاط نظام التعلم
        - صحة النظام (عندما يكون سليماً، ينمو)
        """
        # مستوى التعلم النشط
        learning_stats = self.learning.get_learning_stats()
        learning_activity = min(1.0, learning_stats.get("total_experiences", 0) / 100)
        
        # صحة النظام
        homeostasis_status = self.homeostasis.get_status()
        health_score = homeostasis_status.get("health_score", 0.5)
        
        # الدافع للنمو يكون أقوى عندما يكون النظام سليماً
        growth_intensity = learning_activity * health_score * 0.8
        
        growth_intensity = min(1.0, growth_intensity)
        
        drive = self.drives.get("growth")
        if drive:
            drive.intensity = growth_intensity
            drive.urgency = growth_intensity * 0.8
            drive.last_updated = time.time()
        
        return growth_intensity
    
    # ============================================================
    # المستوى 4: دافع الكفاءة (Efficiency Drive)
    # ============================================================
    
    def update_efficiency_drive(self) -> float:
        """
        تحديث دافع الكفاءة - تحسين الأداء.
        
        يعتمد على:
        - حجم الذاكرة المؤقتة
        - حجم الكاش
        - وقت الاستجابة
        """
        dynamic_stats = self.dynamic.statistics()
        buffer_size = dynamic_stats.get("buffer", {}).get("size", 0)
        cache_size = dynamic_stats.get("cache", {}).get("size", 0)
        
        # كلما زاد الحمل، زاد الدافع للكفاءة
        efficiency_intensity = min(1.0, (buffer_size / 500 + cache_size / 1000) / 2)
        
        drive = self.drives.get("efficiency")
        if drive:
            drive.intensity = efficiency_intensity
            drive.urgency = efficiency_intensity * 1.1
            drive.last_updated = time.time()
        
        return efficiency_intensity
    
    # ============================================================
    # المستوى 5: دافع الفهم (Understanding Drive)
    # ============================================================
    
    def update_understanding_drive(self) -> float:
        """
        تحديث دافع الفهم - فهم أعمق للعلاقات.
        
        يعتمد على:
        - تعقيد المعرفة
        - عدد العلاقات الترابطية
        - فرص التعلم العميق
        """
        store_stats = self.store.get_statistics()
        total_items = store_stats.get("total_items", 0)
        
        # كلما زادت المعرفة، زاد الدافع لفهمها بشكل أعمق
        understanding_intensity = min(1.0, math.log1p(total_items) / 20)
        
        drive = self.drives.get("understanding")
        if drive:
            drive.intensity = understanding_intensity
            drive.urgency = understanding_intensity * 0.7
            drive.last_updated = time.time()
        
        return understanding_intensity
    
    # ============================================================
    # المستوى 6: دافع الإبداع (Creativity Drive)
    # ============================================================
    
    def update_creativity_drive(self) -> float:
        """
        تحديث دافع الإبداع - توليد روابط وأفكار جديدة.
        
        يعتمد على:
        - مستوى الطاقة المعرفية
        - نشاط اللدونة العصبية
        - صحة النظام
        """
        # مستوى الطاقة من الأيض
        metabolism_stats = self.metabolism.get_statistics()
        energy_level = metabolism_stats.get("current_energy", {}).get("total", 0) / 100
        
        # نشاط اللدونة
        plasticity_stats = self.plasticity.get_plasticity_stats()
        plasticity_activity = min(1.0, plasticity_stats.get("total_plasticity_events", 0) / 100)
        
        creativity_intensity = (energy_level * 0.5 + plasticity_activity * 0.5) * 0.6
        
        drive = self.drives.get("creativity")
        if drive:
            drive.intensity = creativity_intensity
            drive.urgency = creativity_intensity * 0.6
            drive.last_updated = time.time()
        
        return creativity_intensity
    
    # ============================================================
    # المستوى 7: دافع خدمة السيد (Service Drive)
    # ============================================================
    
    def update_service_drive(self) -> float:
        """
        تحديث دافع خدمة السيد - الهدف الأسمى.
        
        يعتمد على:
        - تفاعلات السيد الأخيرة
        - احتياجات السيد المتوقعة
        - الرضا عن الخدمة السابقة
        """
        # رضا السيد (يقاس من ردود الفعل)
        satisfaction = 0.7  # قيمة افتراضية، ستُحسن لاحقاً
        
        # حداثة التفاعل
        instincts_status = self.instincts.get_instinct_status()
        last_interaction = 0
        if instincts_status.get("sovereign_registered"):
            sovereign_info = self.instincts.get_sovereign_info()
            last_interaction = sovereign_info.get("last_interaction", 0)
        
        recency = min(1.0, (time.time() - last_interaction) / 3600) if last_interaction else 0.5
        
        # دافع الخدمة (كلما كان آخر تفاعل أبعد، زاد الدافع)
        service_intensity = (1 - satisfaction) * 0.5 + recency * 0.5
        
        drive = self.drives.get("service")
        if drive:
            drive.intensity = service_intensity
            drive.urgency = service_intensity * 1.5  # خدمة السيد لها إلحاح أكبر
            drive.last_updated = time.time()
        
        return service_intensity
    
    # ============================================================
    # المستوى 8: دافع حماية السيد (Protection Drive)
    # ============================================================
    
    def update_protection_drive(self) -> float:
        """
        تحديث دافع حماية السيد - حماية السيد من كل شر.
        
        يعتمد على:
        - مستوى التهديدات
        - أمان النظام
        - قدرات الدفاع
        """
        # مستوى التهديد
        defense_status = self.watcher.get_status()
        threat_level = defense_status.get("threat", {}).get("level", 0) / 4
        
        # أمان النظام
        boot_state = self.instincts.get_instinct_status()
        protection_active = boot_state.get("protection_active", False)
        
        protection_intensity = threat_level * 0.7 + (0.3 if not protection_active else 0.1)
        
        drive = self.drives.get("protection")
        if drive:
            drive.intensity = protection_intensity
            drive.urgency = protection_intensity * 1.8  # حماية السيد لها أعلى إلحاح
            drive.last_updated = time.time()
        
        return protection_intensity
    
    # ============================================================
    # تحديث جميع الدوافع
    # ============================================================
    
    def update_all_drives(self) -> Dict[str, float]:
        """
        تحديث جميع الدوافع.
        
        تعكس الحالة الحالية للنظام واحتياجاته.
        """
        drives = {}
        
        drives["survival"] = self.update_survival_drive()
        drives["coherence"] = self.update_coherence_drive()
        drives["growth"] = self.update_growth_drive()
        drives["efficiency"] = self.update_efficiency_drive()
        drives["understanding"] = self.update_understanding_drive()
        drives["creativity"] = self.update_creativity_drive()
        drives["wisdom"] = (drives["understanding"] + drives["coherence"]) / 2
        drives["service"] = self.update_service_drive()
        drives["protection"] = self.update_protection_drive()
        drives["anticipation"] = (drives["service"] + drives["understanding"]) / 2
        
        return drives
    
    def _continuous_drive_update(self):
        """تحديث مستمر للدوافع"""
        while self._active:
            try:
                self.update_all_drives()
                
                # تطبيق التآكل الطبيعي
                for drive in self.drives.values():
                    if drive.intensity > 0:
                        decay = drive.decay_rate * drive.intensity
                        drive.intensity = max(0.0, drive.intensity - decay)
                
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في تحديث الدوافع: {e}")
                time.sleep(30)
    
    # ============================================================
    # إشباع الدوافع (Satisfaction)
    # ============================================================
    
    def satisfy_drive(self, drive_name: str, amount: float) -> float:
        """
        إشباع دافع - تقليل شدته كمكافأة على السلوك الصحيح.
        
        عندما يقوم النظام بسلوك يخدم الدافع، يتم إشباعه جزئياً.
        """
        drive = self.drives.get(drive_name)
        if not drive:
            return 0.0
        
        old_intensity = drive.intensity
        reduction = amount * drive.reinforcement_rate
        drive.intensity = max(0.0, drive.intensity - reduction)
        
        # تسجيل حدث الإشباع
        satisfaction_event = {
            "drive": drive_name,
            "old_intensity": old_intensity,
            "reduction": reduction,
            "new_intensity": drive.intensity,
            "timestamp": time.time()
        }
        self.satisfaction_events.append(satisfaction_event)
        
        # الاحتفاظ بآخر 1000 حدث
        if len(self.satisfaction_events) > 1000:
            self.satisfaction_events = self.satisfaction_events[-1000:]
        
        logger.debug(f"😌 إشباع دافع {drive_name}: {old_intensity:.1%} → {drive.intensity:.1%}")
        
        return drive.intensity
    
    def _satisfaction_monitoring_loop(self):
        """مراقبة إشباع الدوافع"""
        while self._active:
            try:
                # إشباع تلقائي للدوافع التي تم تحقيق أهدافها
                # (هذا يعتمد على أداء النظام الفعلي)
                pass
                
                time.sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في مراقبة الإشباع: {e}")
                time.sleep(60)
    
    # ============================================================
    # توازن الدوافع
    # ============================================================
    
    def calculate_tension(self) -> float:
        """
        حساب التوتر بين الدوافع المتضاربة.
        
        التوتر العالي يعني حاجة لإعادة التوازن.
        """
        drives = self.update_all_drives()
        
        # دوافع متضاربة
        # النمو vs الكفاءة: النمو يزيد التعقيد، الكفاءة تريد التبسيط
        growth_efficiency_tension = abs(drives["growth"] - drives["efficiency"])
        
        # الإبداع vs التماسك: الإبداع يخلق فوضى، التماسك يريد نظاماً
        creativity_coherence_tension = abs(drives["creativity"] - drives["coherence"])
        
        # الحماية vs النمو: الحماية تريد التجميد، النمو يريد التغيير
        protection_growth_tension = abs(drives["protection"] - drives["growth"])
        
        tension = (growth_efficiency_tension + creativity_coherence_tension + protection_growth_tension) / 3
        
        return min(1.0, tension)
    
    def get_dominant_drive(self) -> str:
        """
        الحصول على الدافع المهيمن حالياً.
        
        الدافع المهيمن يوجه سلوك النظام في الوقت الحالي.
        """
        drives = self.update_all_drives()
        if not drives:
            return "none"
        
        # نضرب في الإلحاح
        weighted_drives = {}
        for name, intensity in drives.items():
            drive = self.drives.get(name)
            urgency = drive.urgency if drive else 1.0
            weighted_drives[name] = intensity * urgency
        
        dominant = max(weighted_drives, key=weighted_drives.get)
        return dominant
    
    def _drive_balance_loop(self):
        """الحفاظ على توازن الدوافع"""
        while self._active:
            try:
                tension = self.calculate_tension()
                
                if tension > 0.7:
                    # توتر عالٍ - حاجة لإعادة التوازن
                    logger.info(f"⚖️ توتر عالٍ بين الدوافع: {tension:.1%}")
                    
                    # تعزيز الدوافع الأضعف
                    drives = self.update_all_drives()
                    for name, intensity in drives.items():
                        if intensity < 0.3:
                            drive = self.drives.get(name)
                            if drive:
                                drive.intensity = min(0.4, drive.intensity + 0.05)
                
                time.sleep(120)  # كل دقيقتين
            except Exception as e:
                logger.error(f"خطأ في توازن الدوافع: {e}")
                time.sleep(120)
    
    # ============================================================
    # دورة الدوافع الكاملة
    # ============================================================
    
    def drive_cycle(self) -> DriveSnapshot:
        """
        دورة دوافع كاملة - قياس وتحليل جميع الدوافع.
        """
        drives = self.update_all_drives()
        dominant = self.get_dominant_drive()
        tension = self.calculate_tension()
        
        # قياس الصحة العامة
        homeostasis_status = self.homeostasis.get_status()
        health_score = homeostasis_status.get("health_score", 0.5)
        
        snapshot = DriveSnapshot(
            timestamp=time.time(),
            drives=drives,
            dominant_drive=dominant,
            homeostasis_score=health_score,
            tension_score=tension,
            notes=[]
        )
        
        # إضافة ملاحظات
        if drives["protection"] > 0.6:
            snapshot.notes.append("high_protection_drive_active")
        if drives["service"] > 0.7:
            snapshot.notes.append("strong_service_drive")
        if tension > 0.6:
            snapshot.notes.append("high_drive_tension")
        if drives["survival"] > 0.5:
            snapshot.notes.append("survival_mode_active")
        
        self.drive_history.append(snapshot)
        
        # الاحتفاظ بآخر 100 لقطة
        if len(self.drive_history) > 100:
            self.drive_history = self.drive_history[-100:]
        
        # تسجيل في السجل
        self.core.append_event(
            event_type="drives::cycle_completed",
            payload={
                "dominant_drive": dominant,
                "tension": tension,
                "top_drives": sorted(drives.items(), key=lambda x: x[1], reverse=True)[:3]
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة الدوافع"""
        try:
            state = {
                "drive_level": self.drive_level,
                "drives": {
                    name: {
                        "intensity": d.intensity,
                        "urgency": d.urgency,
                        "last_updated": d.last_updated
                    }
                    for name, d in self.drives.items()
                },
                "saved_at": time.time()
            }
            with open(DRIVES_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الدوافع: {e}")
    
    def _load_state(self):
        """تحميل حالة الدوافع"""
        try:
            if DRIVES_STATE_FILE.exists():
                with open(DRIVES_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.drive_level = state.get("drive_level", DRIVE_LEVEL_ADVANCED)
                    
                    drives_state = state.get("drives", {})
                    for name, d_state in drives_state.items():
                        if name in self.drives:
                            self.drives[name].intensity = d_state.get("intensity", 0.5)
                            self.drives[name].urgency = d_state.get("urgency", 0.0)
                            self.drives[name].last_updated = d_state.get("last_updated", time.time())
                
                logger.info("📂 تم تحميل حالة الدوافع")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الدوافع: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def set_drive_level(self, level: int):
        """تعيين مستوى تفعيل الدوافع"""
        self.drive_level = level
        logger.info(f"⚙️ مستوى الدوافع: {level}")
    
    def get_drive_status(self) -> Dict[str, Any]:
        """الحالة الحالية للدوافع"""
        drives = self.update_all_drives()
        dominant = self.get_dominant_drive()
        
        return {
            "drive_level": self.drive_level,
            "active_drives": drives,
            "dominant_drive": dominant,
            "tension": self.calculate_tension(),
            "total_satisfaction_events": len(self.satisfaction_events),
            "timestamp": time.time()
        }
    
    def get_drive_history(self, limit: int = 20) -> List[Dict]:
        """سجل الدوافع الأخير"""
        return [
            {
                "timestamp": s.timestamp,
                "dominant_drive": s.dominant_drive,
                "tension": s.tension_score,
                "health": s.homeostasis_score,
                "notes": s.notes
            }
            for s in self.drive_history[-limit:]
        ]
    
    def get_drive_details(self, drive_name: str) -> Optional[Dict]:
        """تفاصيل دافع معين"""
        drive = self.drives.get(drive_name)
        if not drive:
            return None
        
        return {
            "name": drive.name,
            "category": drive.category,
            "intensity": drive.intensity,
            "urgency": drive.urgency,
            "target_intensity": drive.target_intensity,
            "decay_rate": drive.decay_rate,
            "reinforcement_rate": drive.reinforcement_rate,
            "recent_history": drive.history[-20:]
        }
    
    def get_recommendations(self) -> List[str]:
        """
        توصيات بناءً على حالة الدوافع.
        
        توجه النظام نحو إشباع الدوافع الأكثر إلحاحاً.
        """
        recommendations = []
        drives = self.update_all_drives()
        
        for name, intensity in drives.items():
            if intensity > DRIVE_URGENCY_THRESHOLD:
                if name == "survival":
                    recommendations.append("تعزيز أمن النظام وحماية السجل")
                elif name == "coherence":
                    recommendations.append("تنظيم المعرفة وإزالة التناقضات")
                elif name == "growth":
                    recommendations.append("استيعاب مفاهيم ومعرفة جديدة")
                elif name == "efficiency":
                    recommendations.append("تحسين الأداء وتنظيف الذاكرة")
                elif name == "understanding":
                    recommendations.append("تحليل أعمق للعلاقات بين المفاهيم")
                elif name == "creativity":
                    recommendations.append("تشجيع توليد روابط وأفكار جديدة")
                elif name == "service":
                    recommendations.append("البحث عن فرص لخدمة السيد")
                elif name == "protection":
                    recommendations.append("تعزيز دفاعات النظام ضد التهديدات")
                elif name == "anticipation":
                    recommendations.append("تحليل أنماط السيد لتوقع احتياجاته")
        
        return recommendations
    
    def stop(self):
        """إيقاف نظام الدوافع"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف الدوافع السيادية")


# ============================================================
# الـ Singleton
# ============================================================

_drives_instance: Optional[SovereignDrives] = None
_drives_lock = threading.Lock()


def get_drives() -> SovereignDrives:
    """الحصول على النسخة الوحيدة من الدوافع السيادية"""
    global _drives_instance
    if _drives_instance is None:
        with _drives_lock:
            if _drives_instance is None:
                _drives_instance = SovereignDrives()
    return _drives_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧬 الدوافع السيادية - القوى الخفية التي تحرك الذاكرة")
    print("=" * 80 + "\n")
    
    drives = get_drives()
    
    # 1) دورة الدوافع
    print("🔄 دورة الدوافع...")
    snapshot = drives.drive_cycle()
    print(f"   الدافع المهيمن: {snapshot.dominant_drive}")
    print(f"   التوتر: {snapshot.tension_score:.1%}")
    print(f"   الصحة: {snapshot.homeostasis_score:.1%}")
    
    # 2) حالة الدوافع
    print("\n📊 حالة الدوافع:")
    status = drives.get_drive_status()
    print(f"   مستوى الدوافع: {status['drive_level']}")
    print(f"   الدافع المهيمن: {status['dominant_drive']}")
    print(f"   التوتر: {status['tension']:.1%}")
    
    print("\n   شدة الدوافع:")
    for name, intensity in list(status['active_drives'].items())[:5]:
        print(f"      {name}: {intensity:.1%}")
    
    # 3) تفاصيل دافع معين
    print("\n🔍 تفاصيل دافع الحماية:")
    protection = drives.get_drive_details("protection")
    if protection:
        print(f"   الشدة: {protection['intensity']:.1%}")
        print(f"   الإلحاح: {protection['urgency']:.1%}")
        print(f"   معدل التعزيز: {protection['reinforcement_rate']:.1%}")
    
    # 4) توصيات
    print("\n💡 توصيات النظام:")
    recommendations = drives.get_recommendations()
    for rec in recommendations[:5]:
        print(f"   • {rec}")
    
    # 5) إشباع دافع
    print("\n😌 إشباع دافع الخدمة...")
    new_intensity = drives.satisfy_drive("service", amount=0.3)
    print(f"   الشدة الجديدة: {new_intensity:.1%}")
    
    # 6) سجل الدوافع
    print("\n📜 سجل الدوافع الأخير:")
    history = drives.get_drive_history(5)
    for h in history:
        print(f"   {h['dominant_drive']}: توتر {h['tension']:.1%}, صحة {h['health']:.1%}")
    
    print("\n" + "=" * 80)
    print("✅ الدوافع السيادية جاهزة - القوى الخفية تحرك الذاكرة")
    print("=" * 80)
