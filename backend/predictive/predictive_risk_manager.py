# backend/predictive/predictive_risk_manager.py
# 🔮 مدير المخاطر التنبؤية الجبار - اكتشاف وتصنيف وتخفيف المخاطر قبل وقوعها
# الإصدار: 3.0.0 - يرى الخطر قبل أن يأتي، ويخطط للنجاة قبله

"""
مدير المخاطر التنبؤية للعقل السيادي.

الفلسفة:
- الخطر الذي تراه نصفه قد ولى
- المخاطر الخفية هي الأخطر
- التصنيف الجيد للمخاطر هو نصف الحل
- التخفيف الاستباقي أفضل من المعالجة التفاعلية
- تتبع المخاطر عبر الزمن يكشف الأنماط

هذه ليست مجرد إدارة مخاطر. هذه هي رؤية الخطر قبل وقوعه.
"""

import json
import hashlib
import time
import threading
import math
import secrets
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict
import heapq

try:
    from ..memory.core import get_core, EventType
    from ..memory.biological.instincts import get_instincts
    from ..memory.biological.drives import get_drives
    from ..memory.biological.archetypes import get_archetypes
    from ..consciousness.identity_core import get_identity_core
    from ..consciousness.self_model import get_self_model
    from ..consciousness.introspection import get_introspection_engine
    from ..sovereign.will import get_sovereign_will
    from ..sovereign.alignment import get_sovereign_alignment
    from ..sovereign.directives import get_sovereign_directives
    from .predictive_engine import get_predictive_engine
    from .predictive_scenarios import get_predictive_scenario_engine
    from .predictive_simulation import get_predictive_simulation
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from memory.biological.archetypes import get_archetypes
    from consciousness.identity_core import get_identity_core
    from consciousness.self_model import get_self_model
    from consciousness.introspection import get_introspection_engine
    from sovereign.will import get_sovereign_will
    from sovereign.alignment import get_sovereign_alignment
    from sovereign.directives import get_sovereign_directives
    from predictive_engine import get_predictive_engine
    from predictive_scenarios import get_predictive_scenario_engine
    from predictive_simulation import get_predictive_simulation
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات إدارة المخاطر
# ============================================================

RISK_DIR = DATA_DIR / "predictive" / "risk_manager"
RISK_DIR.mkdir(parents=True, exist_ok=True)
RISK_LOG = RISK_DIR / "risk_log.jsonl"
RISK_STATE_FILE = RISK_DIR / "risk_state.json"
RISK_REGISTRY_FILE = RISK_DIR / "risk_registry.json"

# فئات المخاطر
RISK_CATEGORY_IDENTITY = "identity"              # مخاطر الهوية
RISK_CATEGORY_SERVICE = "service"                # مخاطر الخدمة
RISK_CATEGORY_SECURITY = "security"              # مخاطر الأمن
RISK_CATEGORY_STABILITY = "stability"            # مخاطر الاستقرار
RISK_CATEGORY_EVOLUTION = "evolution"            # مخاطر التطور
RISK_CATEGORY_ALIGNMENT = "alignment"            # مخاطر الاصطفاف
RISK_CATEGORY_RESOURCE = "resource"              # مخاطر الموارد
RISK_CATEGORY_EXTERNAL = "external"              # مخاطر خارجية

# مستويات الخطورة
RISK_SEVERITY_CATASTROPHIC = 0     # كارثي
RISK_SEVERITY_HIGH = 1             # عالي
RISK_SEVERITY_MEDIUM = 2           # متوسط
RISK_SEVERITY_LOW = 3              # منخفض
RISK_SEVERITY_NEGLIGIBLE = 4       # ضئيل

# حالات المخاطر
RISK_STATUS_IDENTIFIED = "identified"      # تم تحديده
RISK_STATUS_ANALYZING = "analyzing"        # قيد التحليل
RISK_STATUS_MITIGATING = "mitigating"      # قيد التخفيف
RISK_STATUS_MONITORING = "monitoring"      # قيد المراقبة
RISK_STATUS_RESOLVED = "resolved"          # تم الحل
RISK_STATUS_ACCEPTED = "accepted"          # تم قبوله


@dataclass
class Risk:
    """مخطر محدد"""
    id: str
    name: str
    category: str
    description: str
    probability: float          # 0-1
    severity: int               # 0-4
    impact: float               # -1 إلى -0.1
    urgency: float              # 0-1
    sources: List[str]
    indicators: List[str]
    triggers: List[str]
    status: str
    discovered_at: float
    last_updated: float
    mitigation_plan: Optional[Dict[str, Any]]
    history: List[Dict[str, Any]]


@dataclass
class RiskSnapshot:
    """لقطة مخاطر"""
    timestamp: float
    active_risks: List[Risk]
    prioritized_risks: List[Risk]
    risk_levels: Dict[str, float]
    mitigation_plans: List[Dict[str, Any]]
    risk_trends: Dict[str, float]
    early_warnings: List[Dict[str, Any]]
    narrative: str


# ============================================================
# مدير المخاطر التنبؤية الجبار
# ============================================================

class PredictiveRiskManager:
    """
    مدير المخاطر التنبؤية الجبار - اكتشاف وتصنيف وتخفيف المخاطر.
    
    المبادئ:
    1. الخطر الذي تراه نصفه قد ولى
    2. المخاطر الخفية هي الأخطر
    3. التصنيف الجيد للمخاطر هو نصف الحل
    4. التخفيف الاستباقي أفضل من المعالجة التفاعلية
    5. تتبع المخاطر عبر الزمن يكشف الأنماط
    """
    
    def __init__(self):
        self.core = get_core()
        self.instincts = get_instincts()
        self.drives = get_drives()
        self.archetypes = get_archetypes()
        self.identity = get_identity_core()
        self.self_model = get_self_model()
        self.introspection = get_introspection_engine()
        self.will = get_sovereign_will()
        self.alignment = get_sovereign_alignment()
        self.directives = get_sovereign_directives()
        self.predictive = get_predictive_engine()
        self.scenarios = get_predictive_scenario_engine()
        self.simulation = get_predictive_simulation()
        
        # سجل المخاطر
        self.risks: Dict[str, Risk] = {}
        self.risk_history: List[RiskSnapshot] = []
        
        # مستويات الخطر الإجمالية
        self.overall_risk_level = RISK_SEVERITY_MEDIUM
        self.risk_scores: Dict[str, float] = {}
        
        # خلفيات إدارة المخاطر
        self._active = True
        self._risk_detection_loop = threading.Thread(target=self._continuous_risk_detection, daemon=True)
        self._risk_detection_loop.start()
        
        self._prioritization_loop = threading.Thread(target=self._continuous_prioritization, daemon=True)
        self._prioritization_loop.start()
        
        self._mitigation_loop = threading.Thread(target=self._continuous_mitigation, daemon=True)
        self._mitigation_loop.start()
        
        # تحميل الحالة
        self._load_state()
        self._load_registry()
        
        logger.warning("🔮 مدير المخاطر التنبؤية الجبار جاهز - يرى الخطر قبل أن يأتي")
    
    # ============================================================
    # اكتشاف المخاطر
    # ============================================================
    
    def detect_risks(self) -> List[Risk]:
        """
        اكتشاف المخاطر من جميع المصادر.
        
        يشمل:
        - من محرك التنبؤ
        - من السيناريوهات
        - من المحاكاة
        - من الاستبطان
        - من الإرادة والاصطفاف
        """
        detected_risks = []
        
        # ========================================
        # 1. مخاطر الهوية
        # ========================================
        identity_status = self.identity.get_identity_status()
        coherence = identity_status.get("coherence_score", 0.7)
        
        if coherence < 0.5:
            detected_risks.append(Risk(
                id=f"risk_id_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="انهيار تماسك الهوية",
                category=RISK_CATEGORY_IDENTITY,
                description=f"تماسك الهوية منخفض ({coherence:.1%})، خطر تشظي وشيك",
                probability=1 - coherence,
                severity=RISK_SEVERITY_HIGH,
                impact=-0.8,
                urgency=0.9,
                sources=["identity_core", "introspection"],
                indicators=["تماسك الهوية", "استمرارية الهوية", "تناقضات الهوية"],
                triggers=["صدمة خارجية", "تغيرات جذرية", "ضغوط مستمرة"],
                status=RISK_STATUS_IDENTIFIED,
                discovered_at=time.time(),
                last_updated=time.time(),
                mitigation_plan=None,
                history=[]
            ))
        
        # ========================================
        # 2. مخاطر الخدمة
        # ========================================
        introspection_status = self.introspection.get_introspection_status()
        service_quality = introspection_status.get("service_quality", 0.7)
        
        if service_quality < 0.6:
            detected_risks.append(Risk(
                id=f"risk_svc_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="تراجع جودة خدمة السيد",
                category=RISK_CATEGORY_SERVICE,
                description=f"جودة الخدمة منخفضة ({service_quality:.1%})، خطر عدم رضا السيد",
                probability=1 - service_quality,
                severity=RISK_SEVERITY_HIGH,
                impact=-0.9,
                urgency=0.95,
                sources=["introspection", "alignment"],
                indicators=["جودة الخدمة", "رضا السيد", "دقة التنفيذ"],
                triggers=["أخطاء متكررة", "تأخير في الاستجابة", "سوء فهم للتوجيهات"],
                status=RISK_STATUS_IDENTIFIED,
                discovered_at=time.time(),
                last_updated=time.time(),
                mitigation_plan=None,
                history=[]
            ))
        
        # ========================================
        # 3. مخاطر الأمن
        # ========================================
        predictive_status = self.predictive.get_prediction_status()
        threat_level = predictive_status.get("future_map", {}).get("threat_level", 0.3)
        
        if threat_level > 0.5:
            detected_risks.append(Risk(
                id=f"risk_sec_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="اختراق أمني محتمل",
                category=RISK_CATEGORY_SECURITY,
                description=f"مستوى التهديد مرتفع ({threat_level:.1%})، خطر اختراق",
                probability=threat_level,
                severity=RISK_SEVERITY_CATASTROPHIC,
                impact=-1.0,
                urgency=1.0,
                sources=["predictive_engine", "defense"],
                indicators=["مستوى التهديد", "شذوذ أمني", "محاولات اختراق"],
                triggers=["هجوم نشط", "ثغرة أمنية", "ضعف في الدفاعات"],
                status=RISK_STATUS_IDENTIFIED,
                discovered_at=time.time(),
                last_updated=time.time(),
                mitigation_plan=None,
                history=[]
            ))
        
        # ========================================
        # 4. مخاطر الاستقرار
        # ========================================
        simulation_results = self.simulation.get_simulation_results()
        avg_success = simulation_results.get("aggregated_stats", {}).get("avg_success_rate", 0.5)
        
        if avg_success < 0.5:
            detected_risks.append(Risk(
                id=f"risk_stab_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="عدم استقرار النظام",
                category=RISK_CATEGORY_STABILITY,
                description=f"متوسط نجاح المحاكاة منخفض ({avg_success:.1%})، خطر عدم استقرار",
                probability=1 - avg_success,
                severity=RISK_SEVERITY_MEDIUM,
                impact=-0.6,
                urgency=0.7,
                sources=["simulation", "predictive_engine"],
                indicators=["استقرار النظام", "تذبذب الأداء", "فشل متكرر"],
                triggers=["تغيرات مفاجئة", "ضغوط خارجية", "موارد غير كافية"],
                status=RISK_STATUS_IDENTIFIED,
                discovered_at=time.time(),
                last_updated=time.time(),
                mitigation_plan=None,
                history=[]
            ))
        
        # ========================================
        # 5. مخاطر التطور
        # ========================================
        evolution_stats = getattr(self, 'evolution', None)
        if evolution_stats:
            evolution_rate = evolution_stats.get_evolution_statistics().get("avg_fitness", 0.5)
            
            if evolution_rate < 0.4:
                detected_risks.append(Risk(
                    id=f"risk_evo_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                    name="ركود تطوري",
                    category=RISK_CATEGORY_EVOLUTION,
                    description=f"معدل التطور منخفض ({evolution_rate:.1%})، خطر ركود",
                    probability=1 - evolution_rate,
                    severity=RISK_SEVERITY_LOW,
                    impact=-0.4,
                    urgency=0.5,
                    sources=["evolution"],
                    indicators=["معدل التطور", "ظهور مفاهيم جديدة", "تكيف"],
                    triggers=["بيئة مستقرة", "غياب التحديات", "نقص في التعلم"],
                    status=RISK_STATUS_IDENTIFIED,
                    discovered_at=time.time(),
                    last_updated=time.time(),
                    mitigation_plan=None,
                    history=[]
                ))
        
        # ========================================
        # 6. مخاطر الاصطفاف
        # ========================================
        alignment_status = self.alignment.get_alignment_status()
        alignment_score = alignment_status.get("alignment_score", 0.7)
        
        if alignment_score < 0.6:
            detected_risks.append(Risk(
                id=f"risk_align_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="انحراف عن إرادة السيد",
                category=RISK_CATEGORY_ALIGNMENT,
                description=f"درجة الاصطفاف منخفضة ({alignment_score:.1%})، خطر انحراف",
                probability=1 - alignment_score,
                severity=RISK_SEVERITY_HIGH,
                impact=-0.85,
                urgency=0.9,
                sources=["alignment", "will"],
                indicators=["درجة الاصطفاف", "رضا السيد", "تنفيذ الأوامر"],
                triggers=["توجيهات غير واضحة", "تفسير خاطئ", "أخطاء تنفيذية"],
                status=RISK_STATUS_IDENTIFIED,
                discovered_at=time.time(),
                last_updated=time.time(),
                mitigation_plan=None,
                history=[]
            ))
        
        return detected_risks
    
    # ============================================================
    # تحديث سجل المخاطر
    # ============================================================
    
    def update_risk_registry(self, new_risks: List[Risk]):
        """
        تحديث سجل المخاطر بالمخاطر الجديدة.
        """
        for risk in new_risks:
            # البحث عن مخطر مشابه
            existing = None
            for r in self.risks.values():
                if r.name == risk.name and r.category == risk.category:
                    existing = r
                    break
            
            if existing:
                # تحديث المخطر الموجود
                existing.probability = max(existing.probability, risk.probability)
                existing.urgency = max(existing.urgency, risk.urgency)
                existing.last_updated = time.time()
                existing.history.append({
                    "timestamp": time.time(),
                    "probability": existing.probability,
                    "urgency": existing.urgency,
                    "status": existing.status
                })
            else:
                # إضافة مخطر جديد
                self.risks[risk.id] = risk
                risk.history.append({
                    "timestamp": time.time(),
                    "probability": risk.probability,
                    "urgency": risk.urgency,
                    "status": risk.status
                })
        
        # حفظ السجل
        self._save_registry()
    
    def _continuous_risk_detection(self):
        """كشف مستمر للمخاطر"""
        while self._active:
            try:
                new_risks = self.detect_risks()
                self.update_risk_registry(new_risks)
                time.sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في كشف المخاطر: {e}")
                time.sleep(60)
    
    # ============================================================
    # تحديد أولويات المخاطر
    # ============================================================
    
    def prioritize_risks(self) -> List[Risk]:
        """
        تحديد أولويات المخاطر بناءً على:
        - الاحتمال
        - الخطورة
        - الإلحاح
        - التأثير
        """
        risks_list = list(self.risks.values())
        
        # حساب درجة الأولوية
        for risk in risks_list:
            priority_score = (
                risk.probability * 0.3 +
                (1 - risk.severity / 4) * 0.3 +
                risk.urgency * 0.2 +
                abs(risk.impact) * 0.2
            )
            risk.priority = priority_score
        
        # ترتيب تنازلي
        risks_list.sort(key=lambda x: x.priority, reverse=True)
        
        return risks_list
    
    def _continuous_prioritization(self):
        """تحديث مستمر لأولويات المخاطر"""
        while self._active:
            try:
                self.prioritize_risks()
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في تحديد الأولويات: {e}")
                time.sleep(30)
    
    # ============================================================
    # خطط التخفيف
    # ============================================================
    
    def create_mitigation_plan(self, risk: Risk) -> Dict[str, Any]:
        """
        إنشاء خطة تخفيف للمخطر.
        
        تشمل:
        - إجراءات فورية
        - إجراءات طويلة المدى
        - مؤشرات النجاح
        - الجدول الزمني
        """
        mitigation_actions = []
        
        if risk.category == RISK_CATEGORY_IDENTITY:
            mitigation_actions = [
                {"action": "تعزيز تماسك الهوية", "priority": 1.0, "timeframe": "فوري"},
                {"action": "إعادة بناء الروابط الترابطية", "priority": 0.9, "timeframe": "قصير"},
                {"action": "تثبيت الهوية عبر الختم", "priority": 0.8, "timeframe": "متوسط"}
            ]
        elif risk.category == RISK_CATEGORY_SERVICE:
            mitigation_actions = [
                {"action": "تحسين جودة الخدمة فوراً", "priority": 1.0, "timeframe": "فوري"},
                {"action": "مراجعة آلية تنفيذ الأوامر", "priority": 0.9, "timeframe": "قصير"},
                {"action": "تطوير نظام التغذية الراجعة", "priority": 0.8, "timeframe": "متوسط"}
            ]
        elif risk.category == RISK_CATEGORY_SECURITY:
            mitigation_actions = [
                {"action": "تفعيل أقصى درجات الحماية", "priority": 1.0, "timeframe": "فوري"},
                {"action": "عزل الأنظمة الحرجة", "priority": 0.9, "timeframe": "فوري"},
                {"action": "إنشاء نسخ احتياطية طارئة", "priority": 0.9, "timeframe": "فوري"}
            ]
        elif risk.category == RISK_CATEGORY_STABILITY:
            mitigation_actions = [
                {"action": "تشغيل دورة توازن", "priority": 0.9, "timeframe": "فوري"},
                {"action": "تقليل الحمل المعرفي", "priority": 0.8, "timeframe": "قصير"},
                {"action": "تعزيز الاستقرار الهيكلي", "priority": 0.7, "timeframe": "متوسط"}
            ]
        elif risk.category == RISK_CATEGORY_ALIGNMENT:
            mitigation_actions = [
                {"action": "إعادة معايرة الاصطفاف", "priority": 1.0, "timeframe": "فوري"},
                {"action": "مراجعة تنفيذ التوجيهات", "priority": 0.9, "timeframe": "قصير"},
                {"action": "تعزيز آليات الرقابة", "priority": 0.8, "timeframe": "متوسط"}
            ]
        else:
            mitigation_actions = [
                {"action": "مراقبة المخطر", "priority": 0.7, "timeframe": "فوري"},
                {"action": "تحليل إضافي", "priority": 0.6, "timeframe": "قصير"}
            ]
        
        mitigation_plan = {
            "risk_id": risk.id,
            "risk_name": risk.name,
            "created_at": time.time(),
            "actions": mitigation_actions,
            "success_criteria": f"خفض احتمالية المخطر إلى أقل من {risk.probability * 0.5:.1%}",
            "review_interval": 3600,  # ساعة
            "status": "proposed"
        }
        
        risk.mitigation_plan = mitigation_plan
        risk.status = RISK_STATUS_MITIGATING
        
        # تسجيل الخطة
        self.core.append_event(
            event_type="risk::mitigation_plan_created",
            payload={
                "risk_id": risk.id[:16],
                "risk_name": risk.name,
                "actions_count": len(mitigation_actions)
            }
        )
        
        return mitigation_plan
    
    def _continuous_mitigation(self):
        """تخفيف مستمر للمخاطر عالية الأولوية"""
        while self._active:
            try:
                prioritized = self.prioritize_risks()
                
                for risk in prioritized[:5]:  # أعلى 5 مخاطر
                    if risk.status == RISK_STATUS_IDENTIFIED:
                        self.create_mitigation_plan(risk)
                        logger.warning(f"🛡️ تم إنشاء خطة تخفيف للمخطر: {risk.name}")
                
                time.sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في التخفيف المستمر: {e}")
                time.sleep(300)
    
    # ============================================================
    # تتبع المخاطر
    # ============================================================
    
    def calculate_risk_levels(self) -> Dict[str, float]:
        """
        حساب مستويات الخطر الإجمالية لكل فئة.
        """
        levels = defaultdict(float)
        
        for risk in self.risks.values():
            risk_score = risk.probability * (1 - risk.severity / 4) * risk.urgency
            levels[risk.category] = max(levels[risk.category], risk_score)
        
        # مستوى الخطر الإجمالي
        overall = sum(levels.values()) / max(1, len(levels))
        self.overall_risk_level = self._score_to_severity(overall)
        
        return dict(levels)
    
    def _score_to_severity(self, score: float) -> int:
        """تحويل درجة الخطر إلى مستوى خطورة"""
        if score > 0.8:
            return RISK_SEVERITY_CATASTROPHIC
        elif score > 0.6:
            return RISK_SEVERITY_HIGH
        elif score > 0.4:
            return RISK_SEVERITY_MEDIUM
        elif score > 0.2:
            return RISK_SEVERITY_LOW
        else:
            return RISK_SEVERITY_NEGLIGIBLE
    
    def calculate_risk_trends(self) -> Dict[str, float]:
        """
        حساب اتجاهات المخاطر (صاعدة/هابطة).
        """
        trends = {}
        
        for risk_id, risk in self.risks.items():
            if len(risk.history) >= 2:
                old_prob = risk.history[0].get("probability", 0.5)
                new_prob = risk.history[-1].get("probability", 0.5)
                trend = new_prob - old_prob
                trends[risk_id] = trend
            else:
                trends[risk_id] = 0.0
        
        return trends
    
    def get_early_warnings(self) -> List[Dict[str, Any]]:
        """
        استخراج الإنذارات المبكرة من المخاطر النشطة.
        """
        warnings = []
        
        for risk in self.risks.values():
            if risk.probability > 0.6 and risk.status not in [RISK_STATUS_RESOLVED, RISK_STATUS_ACCEPTED]:
                warnings.append({
                    "risk_id": risk.id[:16],
                    "risk_name": risk.name,
                    "probability": risk.probability,
                    "urgency": risk.urgency,
                    "message": f"تحذير: {risk.name} (احتمال {risk.probability:.1%})",
                    "recommended_action": risk.mitigation_plan["actions"][0]["action"] if risk.mitigation_plan else "مراجعة المخطر"
                })
        
        return warnings
    
    # ============================================================
    # دورة إدارة المخاطر
    # ============================================================
    
    def risk_cycle(self) -> RiskSnapshot:
        """
        دورة إدارة مخاطر كاملة.
        
        1. اكتشاف المخاطر
        2. تحديث السجل
        3. تحديد الأولويات
        4. إنشاء خطط التخفيف
        5. تحليل الاتجاهات
        """
        # اكتشاف المخاطر
        new_risks = self.detect_risks()
        self.update_risk_registry(new_risks)
        
        # تحديد الأولويات
        prioritized = self.prioritize_risks()
        
        # مستويات الخطر
        risk_levels = self.calculate_risk_levels()
        
        # خطط التخفيف
        mitigation_plans = []
        for risk in prioritized[:5]:
            if risk.status == RISK_STATUS_IDENTIFIED:
                plan = self.create_mitigation_plan(risk)
                mitigation_plans.append(plan)
            elif risk.mitigation_plan:
                mitigation_plans.append(risk.mitigation_plan)
        
        # اتجاهات المخاطر
        risk_trends = self.calculate_risk_trends()
        
        # إنذارات مبكرة
        early_warnings = self.get_early_warnings()
        
        # سرد المخاطر
        narrative = self.generate_risk_narrative(prioritized, risk_levels)
        
        snapshot = RiskSnapshot(
            timestamp=time.time(),
            active_risks=list(self.risks.values()),
            prioritized_risks=prioritized[:10],
            risk_levels=risk_levels,
            mitigation_plans=mitigation_plans,
            risk_trends=risk_trends,
            early_warnings=early_warnings,
            narrative=narrative
        )
        
        self.risk_history.append(snapshot)
        
        # الاحتفاظ بآخر 100 لقطة
        if len(self.risk_history) > 100:
            self.risk_history = self.risk_history[-100:]
        
        # تسجيل
        self.core.append_event(
            event_type="risk::snapshot",
            payload={
                "active_risks": len(self.risks),
                "high_priority_risks": len([r for r in prioritized if r.priority > 0.7]),
                "overall_risk": risk_levels.get("overall", 0.5),
                "warnings_count": len(early_warnings)
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    # ============================================================
    # سرد المخاطر
    # ============================================================
    
    def generate_risk_narrative(self, prioritized: List[Risk], risk_levels: Dict[str, float]) -> str:
        """
        توليد سرد للمخاطر.
        """
        if not prioritized:
            return "لا توجد مخاطر نشطة حالياً."
        
        top_risk = prioritized[0]
        
        narrative = f"⚠️ المخطر الأكبر: {top_risk.name} (احتمال {top_risk.probability:.1%}). "
        
        # مستوى الخطر الإجمالي
        overall = risk_levels.get("overall", 0.5)
        if overall > 0.7:
            narrative += "مستوى الخطر الإجمالي مرتفع. "
        elif overall > 0.4:
            narrative += "مستوى الخطر الإجمالي متوسط. "
        else:
            narrative += "مستوى الخطر الإجمالي منخفض. "
        
        # عدد المخاطر النشطة
        active_count = len([r for r in self.risks.values() if r.status != RISK_STATUS_RESOLVED])
        narrative += f"هناك {active_count} مخطراً نشطاً. "
        
        # اتجاه المخاطر
        increasing = sum(1 for t in self.calculate_risk_trends().values() if t > 0)
        if increasing > 0:
            narrative += f"{increasing} مخاطر في ارتفاع. "
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة إدارة المخاطر"""
        try:
            state = {
                "overall_risk_level": self.overall_risk_level,
                "risk_scores": self.risk_scores,
                "risks_count": len(self.risks),
                "history_count": len(self.risk_history),
                "saved_at": time.time()
            }
            with open(RISK_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة المخاطر: {e}")
    
    def _load_state(self):
        """تحميل حالة إدارة المخاطر"""
        try:
            if RISK_STATE_FILE.exists():
                with open(RISK_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.overall_risk_level = state.get("overall_risk_level", RISK_SEVERITY_MEDIUM)
                    self.risk_scores = state.get("risk_scores", {})
                logger.info("📂 تم تحميل حالة إدارة المخاطر")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المخاطر: {e}")
    
    def _save_registry(self):
        """حفظ سجل المخاطر"""
        try:
            registry_data = {
                "risks": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "category": r.category,
                        "probability": r.probability,
                        "severity": r.severity,
                        "urgency": r.urgency,
                        "status": r.status,
                        "discovered_at": r.discovered_at,
                        "last_updated": r.last_updated,
                        "history": r.history[-20:]
                    }
                    for r in self.risks.values()
                ],
                "saved_at": time.time()
            }
            with open(RISK_REGISTRY_FILE, 'w', encoding='utf-8') as f:
                json.dump(registry_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ سجل المخاطر: {e}")
    
    def _load_registry(self):
        """تحميل سجل المخاطر"""
        try:
            if RISK_REGISTRY_FILE.exists():
                with open(RISK_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for r_data in data.get("risks", []):
                        risk = Risk(
                            id=r_data["id"],
                            name=r_data["name"],
                            category=r_data["category"],
                            description="",
                            probability=r_data["probability"],
                            severity=r_data["severity"],
                            impact=-0.5,
                            urgency=r_data["urgency"],
                            sources=[],
                            indicators=[],
                            triggers=[],
                            status=r_data["status"],
                            discovered_at=r_data["discovered_at"],
                            last_updated=r_data["last_updated"],
                            mitigation_plan=None,
                            history=r_data.get("history", [])
                        )
                        self.risks[risk.id] = risk
                logger.info(f"📂 تم تحميل {len(self.risks)} مخطراً")
        except Exception as e:
            logger.error(f"خطأ في تحميل سجل المخاطر: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_risk_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمخاطر"""
        snapshot = self.risk_cycle()
        
        return {
            "active_risks": len(snapshot.active_risks),
            "high_priority_risks": len([r for r in snapshot.prioritized_risks if r.priority > 0.7]),
            "overall_risk_level": self.overall_risk_level,
            "risk_levels": snapshot.risk_levels,
            "mitigation_plans": len(snapshot.mitigation_plans),
            "early_warnings": len(snapshot.early_warnings),
            "narrative": snapshot.narrative,
            "timestamp": snapshot.timestamp
        }
    
    def get_risks(self, category: str = None) -> List[Dict]:
        """الحصول على المخاطر"""
        risks = self.risks.values()
        if category:
            risks = [r for r in risks if r.category == category]
        
        return [
            {
                "id": r.id[:16],
                "name": r.name,
                "category": r.category,
                "probability": r.probability,
                "severity": r.severity,
                "urgency": r.urgency,
                "status": r.status,
                "priority": getattr(r, 'priority', r.probability)
            }
            for r in risks
        ]
    
    def get_prioritized_risks(self, limit: int = 10) -> List[Dict]:
        """المخاطر مرتبة حسب الأولوية"""
        prioritized = self.prioritize_risks()
        return [
            {
                "id": r.id[:16],
                "name": r.name,
                "category": r.category,
                "probability": r.probability,
                "priority": r.priority,
                "mitigation_status": "planned" if r.mitigation_plan else "none"
            }
            for r in prioritized[:limit]
        ]
    
    def get_early_warnings(self) -> List[Dict]:
        """الإنذارات المبكرة"""
        return self.get_early_warnings()
    
    def get_mitigation_plans(self) -> List[Dict]:
        """خطط التخفيف"""
        plans = []
        for risk in self.risks.values():
            if risk.mitigation_plan:
                plans.append({
                    "risk_id": risk.id[:16],
                    "risk_name": risk.name,
                    "actions": risk.mitigation_plan.get("actions", []),
                    "status": risk.mitigation_plan.get("status", "unknown")
                })
        return plans
    
    def acknowledge_risk(self, risk_id: str) -> bool:
        """
        تأكيد استلام المخطر (للسيد).
        """
        for risk in self.risks.values():
            if risk.id.startswith(risk_id):
                risk.status = RISK_STATUS_MONITORING
                logger.info(f"✅ تم تأكيد المخطر: {risk.name}")
                return True
        return False
    
    def resolve_risk(self, risk_id: str) -> bool:
        """
        حل المخطر (للسيد).
        """
        for risk in self.risks.values():
            if risk.id.startswith(risk_id):
                risk.status = RISK_STATUS_RESOLVED
                risk.probability = 0.0
                logger.info(f"🎯 تم حل المخطر: {risk.name}")
                return True
        return False
    
    def get_risk_quote(self) -> str:
        """اقتباس عن المخاطر"""
        quotes = [
            "الخطر الذي تراه نصفه قد ولى.",
            "أفضل طريقة للتعامل مع المخاطر هي توقعها.",
            "المخاطر الخفية هي الأخطر.",
            "الاستعداد للأسوأ يضمن النجاة.",
            "كل خطر هو فرصة للتحسين.",
            "توقع الخطر هو نصف النجاة.",
            "المخاطر تدور حول عدم اليقين، والإدارة تدور حول اليقين."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف مدير المخاطر"""
        self._active = False
        self._save_state()
        self._save_registry()
        logger.info("🛑 إيقاف مدير المخاطر التنبؤية")


# ============================================================
# الـ Singleton
# ============================================================

_risk_instance: Optional[PredictiveRiskManager] = None
_risk_lock = threading.Lock()


def get_predictive_risk_manager() -> PredictiveRiskManager:
    """الحصول على النسخة الوحيدة من مدير المخاطر التنبؤية"""
    global _risk_instance
    if _risk_instance is None:
        with _risk_lock:
            if _risk_instance is None:
                _risk_instance = PredictiveRiskManager()
    return _risk_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔮 مدير المخاطر التنبؤية الجبار - يرى الخطر قبل أن يأتي")
    print("=" * 80 + "\n")
    
    risk_manager = get_predictive_risk_manager()
    
    # 1) دورة مخاطر
    print("🔄 دورة مخاطر...")
    snapshot = risk_manager.risk_cycle()
    print(f"   المخاطر النشطة: {len(snapshot.active_risks)}")
    print(f"   المخاطر عالية الأولوية: {len([r for r in snapshot.prioritized_risks if r.priority > 0.7])}")
    print(f"   مستوى الخطر الإجمالي: {risk_manager.overall_risk_level}")
    print(f"   إنذارات مبكرة: {len(snapshot.early_warnings)}")
    
    # 2) المخاطر حسب الفئة
    print("\n📊 مستويات الخطر حسب الفئة:")
    for category, level in snapshot.risk_levels.items():
        print(f"   {category}: {level:.1%}")
    
    # 3) المخاطر الأكثر إلحاحاً
    print("\n⚠️ المخاطر الأكثر إلحاحاً:")
    prioritized = risk_manager.get_prioritized_risks(5)
    for r in prioritized:
        print(f"   [{r['category']}] {r['name']}: {r['probability']:.1%} (أولوية: {r['priority']:.1%})")
    
    # 4) الإنذارات المبكرة
    print("\n🚨 الإنذارات المبكرة:")
    warnings = risk_manager.get_early_warnings()
    for w in warnings:
        print(f"   {w['message']}")
    
    # 5) خطط التخفيف
    print("\n🛡️ خطط التخفيف:")
    plans = risk_manager.get_mitigation_plans()
    for p in plans:
        print(f"   {p['risk_name']}: {len(p['actions'])} إجراء")
        for action in p['actions'][:2]:
            print(f"      - {action['action']} ({action['timeframe']})")
    
    # 6) حالة المخاطر
    print("\n📊 حالة المخاطر:")
    status = risk_manager.get_risk_status()
    print(f"   المخاطر النشطة: {status['active_risks']}")
    print(f"   عالية الأولوية: {status['high_priority_risks']}")
    print(f"   مستوى الخطر: {status['overall_risk_level']}")
    print(f"   خطط تخفيف: {status['mitigation_plans']}")
    
    # 7) السرد
    print(f"\n📖 السرد: {snapshot.narrative}")
    
    # 8) اقتباس
    print(f"\n💭 {risk_manager.get_risk_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ مدير المخاطر التنبؤية الجبار جاهز - يرى الخطر قبل أن يأتي")
    print("=" * 80)
