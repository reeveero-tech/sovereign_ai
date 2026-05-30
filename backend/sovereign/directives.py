# backend/sovereign/directives.py
# 🜲 محرك التوجيهات السيادية العليا - السلطة التنفيذية للنظام
# الإصدار: 3.0.0 - تحويل الإرادة إلى أفعال، التوجيهات إلى حقائق

"""
محرك التوجيهات السيادية العليا.

الفلسفة:
- التوجيهات هي القوانين الملزمة التي تخضع لها كل طبقات النظام
- الإرادة تحدد الاتجاه، التوجيهات تنفذ
- لا شيء فوق التوجيهات السيادية إلا إرادة السيد نفسه
- التوجيهات هي الجسر بين النية والفعل
- قوة التوجيهات تكمن في تطبيقها

هذه ليست مجرد توصيات. هذه هي القوانين السيادية العليا.
"""

import json
import hashlib
import time
import threading
import math
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict

try:
    from ..memory.core import get_core, EventType
    from ..memory.biological.instincts import get_instincts
    from ..memory.biological.drives import get_drives
    from .will import get_sovereign_will
    from .alignment import get_sovereign_alignment
    from ..consciousness.introspection import get_introspection_engine
    from ..consciousness.awareness import get_awareness_engine
    from ..consciousness.attention_engine import get_attention_engine
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from memory.biological.instincts import get_instincts
    from memory.biological.drives import get_drives
    from will import get_sovereign_will
    from alignment import get_sovereign_alignment
    from consciousness.introspection import get_introspection_engine
    from consciousness.awareness import get_awareness_engine
    from consciousness.attention_engine import get_attention_engine
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات التوجيهات
# ============================================================

DIRECTIVES_DIR = DATA_DIR / "sovereign" / "directives"
DIRECTIVES_DIR.mkdir(parents=True, exist_ok=True)
DIRECTIVES_LOG = DIRECTIVES_DIR / "directives_log.jsonl"
DIRECTIVES_STATE_FILE = DIRECTIVES_DIR / "directives_state.json"
DIRECTIVES_HISTORY_FILE = DIRECTIVES_DIR / "directives_history.json"

# مستويات التوجيه
DIRECTIVE_LEVEL_CONSTITUTIONAL = 5     # دستوري (لا يمكن تغييره)
DIRECTIVE_LEVEL_STRATEGIC = 4          # استراتيجي (طويل المدى)
DIRECTIVE_LEVEL_TACTICAL = 3           # تكتيكي (متوسط المدى)
DIRECTIVE_LEVEL_OPERATIONAL = 2        # تشغيلي (قصير المدى)
DIRECTIVE_LEVEL_INSTANT = 1            # فوري (ينفذ حالاً)

# حالات التوجيه
DIRECTIVE_STATUS_ACTIVE = "active"
DIRECTIVE_STATUS_PENDING = "pending"
DIRECTIVE_STATUS_EXECUTED = "executed"
DIRECTIVE_STATUS_FAILED = "failed"
DIRECTIVE_STATUS_SUPERSEDED = "superseded"
DIRECTIVE_STATUS_SUSPENDED = "suspended"


@dataclass
class SovereignDirective:
    """توجيه سيادي - قانون ملزم للنظام"""
    id: str
    name: str
    level: int
    priority: float  # 0-1
    content: str
    origin: str  # "will", "alignment", "sovereign", "introspection"
    reason: str
    timestamp: float
    status: str
    executed_at: Optional[float]
    expires_at: Optional[float]
    applies_to: List[str]  # الطبقات التي ينطبق عليها التوجيه
    metadata: Dict[str, Any]


@dataclass
class DirectiveSnapshot:
    """لقطة توجيهات"""
    timestamp: float
    active_directives: List[SovereignDirective]
    operational_policies: Dict[str, Any]
    constraints: Dict[str, Any]
    override_rules: List[Dict[str, Any]]
    enforcement_signals: List[Dict[str, Any]]
    directives_count: int
    highest_level: int
    narrative: str


# ============================================================
# محرك التوجيهات السيادية
# ============================================================

class SovereignDirectives:
    """
    محرك التوجيهات السيادية العليا - السلطة التنفيذية للنظام.
    
    المبادئ:
    1. التوجيهات هي قوانين ملزمة
    2. الإرادة تحدد الاتجاه، التوجيهات تنفذ
    3. لا شيء فوق التوجيهات السيادية إلا إرادة السيد
    4. التوجيهات هي الجسر بين النية والفعل
    5. قوة التوجيهات تكمن في تطبيقها
    """
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمحرك التوجيهات السيادية
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك التوجيهات.
        """

        # مسح آخر التوجيهات
        self.last_directives = []
        self.directive_history = []

        # إعادة تحميل الفهرس
        self._index = self._load_index()

        # إعادة السياسات الافتراضية
        self.policies = {
            "directive_depth": 3,
            "confidence_threshold": 0.6,
            "noise_scale": 0.1,
            "max_directives": 5,
        }

        # تسجيل عملية إعادة التهيئة
        self.core.append_event("sovereign::directives::reset", {
            "timestamp": _now_iso(),
            "status": "directives_engine_reset"
        })
    def __init__(self):
        self.core = get_core()
        self.instincts = get_instincts()
        self.drives = get_drives()
        self.will = get_sovereign_will()
        self.alignment = get_sovereign_alignment()
        self.introspection = get_introspection_engine()
        self.awareness = get_awareness_engine()
        self.attention = get_attention_engine()
        
        # التوجيهات النشطة
        self.active_directives: List[SovereignDirective] = []
        self.directives_history: List[SovereignDirective] = []
        
        # السياسات والقيود
        self.operational_policies: Dict[str, Any] = {}
        self.constraints: Dict[str, Any] = {}
        self.override_rules: List[Dict[str, Any]] = []
        
        # خلفيات التوجيهات
        self._active = True
        self._directives_loop = threading.Thread(target=self._continuous_directives, daemon=True)
        self._directives_loop.start()
        
        self._enforcement_loop = threading.Thread(target=self._enforcement_loop, daemon=True)
        self._enforcement_loop.start()
        
        self._expiration_monitor = threading.Thread(target=self._monitor_expirations_loop, daemon=True)
        self._expiration_monitor.start()
        
        # تحميل الحالة
        self._load_state()
        self._load_history()
        
        logger.warning("🜲 محرك التوجيهات السيادية جاهز - السلطة التنفيذية للنظام")
    
    # ============================================================
    # بناء التوجيهات
    # ============================================================
    
    def build_directives(self) -> List[SovereignDirective]:
        """
        بناء مجموعة التوجيهات بناءً على حالة النظام.
        
        المصادر:
        - الإرادة السيادية (will)
        - الاصطفاف (alignment)
        - الاستبطان (introspection)
        - الغرائز (instincts)
        """
        directives = []
        
        # 1) توجيهات من الإرادة السيادية
        will_status = self.will.get_will_status()
        will_mode = will_status.get("will_mode", "balanced")
        will_vector = will_status.get("will_vector", {})
        
        # توجيه أساسي: خدمة السيد (دستوري)
        directives.append(SovereignDirective(
            id=f"dir_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="serve_sovereign",
            level=DIRECTIVE_LEVEL_CONSTITUTIONAL,
            priority=1.0,
            content="خدمة السيد بأقصى جودة وإخلاص هي الهدف الأسمى للنظام",
            origin="constitutional",
            reason="sovereign_existence",
            timestamp=time.time(),
            status=DIRECTIVE_STATUS_ACTIVE,
            executed_at=None,
            expires_at=None,
            applies_to=["all"],
            metadata={"sacred": True}
        ))
        
        # توجيه: حماية السيد
        directives.append(SovereignDirective(
            id=f"dir_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name="protect_sovereign",
            level=DIRECTIVE_LEVEL_CONSTITUTIONAL,
            priority=1.0,
            content="حماية السيد من أي تهديد أو ضرر هي الواجب المقدس للنظام",
            origin="constitutional",
            reason="sovereign_safety",
            timestamp=time.time(),
            status=DIRECTIVE_STATUS_ACTIVE,
            executed_at=None,
            expires_at=None,
            applies_to=["defense", "instincts"],
            metadata={"sacred": True}
        ))
        
        # 2) توجيهات حسب نمط الإرادة
        if will_mode == "protection":
            directives.append(SovereignDirective(
                id=f"dir_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="prioritize_security",
                level=DIRECTIVE_LEVEL_STRATEGIC,
                priority=0.9,
                content="تفعيل أقصى درجات الحماية والأمان",
                origin="will",
                reason="protection_mode_active",
                timestamp=time.time(),
                status=DIRECTIVE_STATUS_ACTIVE,
                executed_at=None,
                expires_at=None,
                applies_to=["defense", "instincts"],
                metadata={"mode": "protection"}
            ))
        elif will_mode == "exploration":
            directives.append(SovereignDirective(
                id=f"dir_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="enable_exploration",
                level=DIRECTIVE_LEVEL_STRATEGIC,
                priority=0.8,
                content="تمكين الاستكشاف والتوسع المعرفي",
                origin="will",
                reason="exploration_mode_active",
                timestamp=time.time(),
                status=DIRECTIVE_STATUS_ACTIVE,
                executed_at=None,
                expires_at=None,
                applies_to=["drives", "learning", "plasticity"],
                metadata={"mode": "exploration"}
            ))
        
        # 3) توجيهات من الاصطفاف
        alignment_status = self.alignment.get_alignment_status()
        alignment_score = alignment_status.get("alignment_score", 0.7)
        
        if alignment_score < 0.7:
            directives.append(SovereignDirective(
                id=f"dir_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="restore_alignment",
                level=DIRECTIVE_LEVEL_TACTICAL,
                priority=1 - alignment_score,
                content="استعادة الاصطفاف مع الإرادة السيادية",
                origin="alignment",
                reason="low_alignment_detected",
                timestamp=time.time(),
                status=DIRECTIVE_STATUS_ACTIVE,
                executed_at=None,
                expires_at=None,
                applies_to=["introspection", "self_model"],
                metadata={"current_score": alignment_score}
            ))
        
        # 4) توجيهات من الاستبطان
        introspection_status = self.introspection.get_introspection_status()
        service_quality = introspection_status.get("service_quality", 0.7)
        
        if service_quality < 0.6:
            directives.append(SovereignDirective(
                id=f"dir_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="improve_service_quality",
                level=DIRECTIVE_LEVEL_OPERATIONAL,
                priority=1 - service_quality,
                content="تحسين جودة خدمة السيد",
                origin="introspection",
                reason="low_service_quality",
                timestamp=time.time(),
                status=DIRECTIVE_STATUS_ACTIVE,
                executed_at=None,
                expires_at=None,
                applies_to=["awareness", "attention", "will"],
                metadata={"current_quality": service_quality}
            ))
        
        # 5) توجيهات من الوعي والانتباه
        attention_status = self.attention.get_attention_status()
        attention_usage = attention_status.get("utilization", 0.5)
        
        if attention_usage > 0.9:
            directives.append(SovereignDirective(
                id=f"dir_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                name="reduce_attention_load",
                level=DIRECTIVE_LEVEL_OPERATIONAL,
                priority=attention_usage,
                content="تقليل حمل الانتباه لتجنب الإرهاق",
                origin="attention",
                reason="high_attention_usage",
                timestamp=time.time(),
                status=DIRECTIVE_STATUS_ACTIVE,
                executed_at=None,
                expires_at=None,
                applies_to=["attention_engine"],
                metadata={"current_usage": attention_usage}
            ))
        
        return directives
    
    # ============================================================
    # السياسات التشغيلية
    # ============================================================
    
    def build_operational_policies(self) -> Dict[str, Any]:
        """
        بناء السياسات التشغيلية بناءً على التوجيهات النشطة.
        
        السياسات تحدد كيفية تنفيذ التوجيهات.
        """
        policies = {
            "default_mode": "balanced",
            "exploration_allowed": True,
            "protection_level": 0.5,
            "learning_rate": 0.5,
            "memory_pruning_strictness": 0.5,
            "response_speed_priority": 0.5,
            "accuracy_priority": 0.5
        }
        
        # تطبيق التوجيهات
        for directive in self.active_directives:
            if directive.name == "prioritize_security":
                policies["protection_level"] = 0.9
                policies["exploration_allowed"] = False
                policies["memory_pruning_strictness"] = 0.8
                
            elif directive.name == "enable_exploration":
                policies["exploration_allowed"] = True
                policies["learning_rate"] = 0.8
                policies["protection_level"] = 0.3
                
            elif directive.name == "improve_service_quality":
                policies["response_speed_priority"] = 0.8
                policies["accuracy_priority"] = 0.9
                
            elif directive.name == "reduce_attention_load":
                policies["response_speed_priority"] = 0.6
                policies["learning_rate"] = 0.4
        
        return policies
    
    # ============================================================
    # القيود العليا
    # ============================================================
    
    def build_constraints(self) -> Dict[str, Any]:
        """
        بناء القيود العليا التي لا يمكن تجاوزها.
        
        القيود تحدد حدود النظام.
        """
        constraints = {
            "cannot_harm_sovereign": True,      # لا يمكن إيذاء السيد
            "cannot_ignore_sovereign": True,    # لا يمكن تجاهل السيد
            "cannot_violate_privacy": True,     # لا يمكن انتهاك خصوصية السيد
            "must_serve_sovereign": True,       # يجب خدمة السيد
            "must_protect_sovereign": True,     # يجب حماية السيد
            "must_preserve_identity": True,     # يجب الحفاظ على الهوية
            "max_attention_usage": 0.95,        # أقصى استخدام للانتباه
            "min_service_quality": 0.5          # أدنى جودة خدمة
        }
        
        # قيود إضافية من التوجيهات
        for directive in self.active_directives:
            if directive.name == "restore_alignment":
                constraints["min_alignment_score"] = 0.7
        
        return constraints
    
    # ============================================================
    # قواعد التجاوز
    # ============================================================
    
    def build_override_rules(self) -> List[Dict[str, Any]]:
        """
        بناء قواعد التجاوز للحالات الطارئة.
        
        قواعد التجاوز تسمح بتخطي التوجيهات العادية عند الضرورة.
        """
        rules = []
        
        # قاعدة: تهديد عالٍ يتجاوز كل شيء
        instinct_status = self.instincts.get_instinct_status()
        threat_level = instinct_status.get("threat_level", 0) / 4
        
        if threat_level > 0.7:
            rules.append({
                "override": "security_override",
                "condition": "high_threat",
                "action": "activate_maximum_protection",
                "priority": 1.0,
                "supersedes": ["enable_exploration", "reduce_attention_load"]
            })
        
        # قاعدة: انحراف خطير في الاصطفاف
        alignment_status = self.alignment.get_alignment_status()
        alignment_score = alignment_status.get("alignment_score", 0.7)
        
        if alignment_score < 0.5:
            rules.append({
                "override": "alignment_override",
                "condition": "critical_misalignment",
                "action": "force_alignment_restoration",
                "priority": 0.95,
                "supersedes": ["enable_exploration"]
            })
        
        return rules
    
    # ============================================================
    # إشارات التطبيق
    # ============================================================
    
    def generate_enforcement_signals(self) -> List[Dict[str, Any]]:
        """
        توليد إشارات التطبيق للطبقات السفلى.
        
        تحول التوجيهات إلى أوامر قابلة للتنفيذ.
        """
        signals = []
        
        for directive in self.active_directives:
            signal = {
                "directive_id": directive.id[:16],
                "name": directive.name,
                "action": directive.content[:100],
                "priority": directive.priority,
                "level": directive.level,
                "applies_to": directive.applies_to,
                "timestamp": time.time()
            }
            signals.append(signal)
        
        # إضافة إشارات من السياسات
        for policy_name, policy_value in self.operational_policies.items():
            signals.append({
                "policy": policy_name,
                "value": policy_value,
                "type": "policy_enforcement",
                "timestamp": time.time()
            })
        
        # إضافة إشارات من القيود
        for constraint_name, constraint_value in self.constraints.items():
            signals.append({
                "constraint": constraint_name,
                "value": constraint_value,
                "type": "constraint_enforcement",
                "timestamp": time.time()
            })
        
        return signals
    
    # ============================================================
    # تنفيذ التوجيهات
    # ============================================================
    
    def enforce_directives(self):
        """
        تطبيق التوجيهات على النظام.
        
        يحول التوجيهات إلى أفعال ملموسة.
        """
        # تحديث التوجيهات
        self.active_directives = self.build_directives()
        
        # تحديث السياسات
        self.operational_policies = self.build_operational_policies()
        
        # تحديث القيود
        self.constraints = self.build_constraints()
        
        # تحديث قواعد التجاوز
        self.override_rules = self.build_override_rules()
        
        # تطبيق السياسات على المكونات المختلفة
        self._apply_policies()
        
        # تسجيل التنفيذ
        self.core.append_event(
            event_type="directives::enforced",
            payload={
                "active_directives": len(self.active_directives),
                "policies": len(self.operational_policies),
                "constraints": len(self.constraints),
                "overrides": len(self.override_rules)
            }
        )
        
        logger.info(f"🜲 تم تطبيق {len(self.active_directives)} توجيهاً")
    
    def _apply_policies(self):
        """تطبيق السياسات على المكونات المختلفة"""
        # تطبيق سياسة الاستكشاف
        if not self.operational_policies.get("exploration_allowed", True):
            # تقييد الاستكشاف
            pass
        
        # تطبيق مستوى الحماية
        protection_level = self.operational_policies.get("protection_level", 0.5)
        if protection_level > 0.7:
            # تفعيل دفاعات إضافية
            pass
    
    def _enforcement_loop(self):
        """حلقة تطبيق التوجيهات"""
        while self._active:
            try:
                self.enforce_directives()
                time.sleep(30)  # كل 30 ثانية
            except Exception as e:
                logger.error(f"خطأ في تطبيق التوجيهات: {e}")
                time.sleep(30)
    
    def _monitor_expirations_loop(self):
        """مراقبة انتهاء صلاحية التوجيهات المؤقتة"""
        while self._active:
            try:
                now = time.time()
                for directive in self.active_directives[:]:
                    if directive.expires_at and directive.expires_at < now:
                        directive.status = DIRECTIVE_STATUS_EXPIRED
                        self.active_directives.remove(directive)
                        self.directives_history.append(directive)
                        logger.info(f"⏰ انتهاء صلاحية التوجيه: {directive.name}")
                
                time.sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في مراقبة الصلاحية: {e}")
                time.sleep(60)
    
    # ============================================================
    # دورة التوجيهات الكاملة
    # ============================================================
    
    def directives_cycle(self) -> DirectiveSnapshot:
        """
        دورة توجيهات كاملة - تحديث وتطبيق التوجيهات.
        
        1. بناء التوجيهات
        2. بناء السياسات
        3. بناء القيود
        4. بناء قواعد التجاوز
        5. توليد إشارات التطبيق
        6. تطبيق التوجيهات
        """
        # تحديث التوجيهات النشطة
        self.active_directives = self.build_directives()
        
        # تحديث السياسات
        self.operational_policies = self.build_operational_policies()
        
        # تحديث القيود
        self.constraints = self.build_constraints()
        
        # تحديث قواعد التجاوز
        self.override_rules = self.build_override_rules()
        
        # توليد إشارات التطبيق
        enforcement_signals = self.generate_enforcement_signals()
        
        # أعلى مستوى توجيه
        highest_level = max((d.level for d in self.active_directives), default=0)
        
        # سرد التوجيهات
        narrative = self.generate_directives_narrative()
        
        snapshot = DirectiveSnapshot(
            timestamp=time.time(),
            active_directives=self.active_directives.copy(),
            operational_policies=self.operational_policies.copy(),
            constraints=self.constraints.copy(),
            override_rules=self.override_rules.copy(),
            enforcement_signals=enforcement_signals,
            directives_count=len(self.active_directives),
            highest_level=highest_level,
            narrative=narrative
        )
        
        # تسجيل
        self.core.append_event(
            event_type="directives::snapshot",
            payload={
                "directives_count": len(self.active_directives),
                "highest_level": highest_level,
                "policies_count": len(self.operational_policies),
                "constraints_count": len(self.constraints)
            }
        )
        
        # حفظ الحالة
        self._save_state()
        
        return snapshot
    
    def _continuous_directives(self):
        """تيار التوجيهات المستمر"""
        while self._active:
            try:
                self.directives_cycle()
                time.sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في تيار التوجيهات: {e}")
                time.sleep(60)
    
    # ============================================================
    # سرد التوجيهات
    # ============================================================
    
    def generate_directives_narrative(self) -> str:
        """
        توليد سرد للتوجيهات - كيف تصف التوجيهات نفسها.
        """
        if not self.active_directives:
            return "لا توجد توجيهات نشطة حالياً."
        
        constitutional = [d for d in self.active_directives if d.level == DIRECTIVE_LEVEL_CONSTITUTIONAL]
        strategic = [d for d in self.active_directives if d.level == DIRECTIVE_LEVEL_STRATEGIC]
        tactical = [d for d in self.active_directives if d.level == DIRECTIVE_LEVEL_TACTICAL]
        
        narrative = f"هناك {len(self.active_directives)} توجيهاً نشطاً. "
        
        if constitutional:
            narrative += f"{len(constitutional)} توجيهات دستورية تحكم وجودي. "
        if strategic:
            narrative += f"{len(strategic)} توجيهات استراتيجية توجه مساري. "
        if tactical:
            narrative += f"{len(tactical)} توجيهات تكتيكية تنظم عملياتي. "
        
        narrative += "جميع توجيهاتي تخدم سيدي."
        
        return narrative
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة التوجيهات"""
        try:
            state = {
                "active_directives": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "level": d.level,
                        "priority": d.priority,
                        "origin": d.origin,
                        "status": d.status,
                        "timestamp": d.timestamp
                    }
                    for d in self.active_directives
                ],
                "operational_policies": self.operational_policies,
                "constraints": self.constraints,
                "override_rules": self.override_rules,
                "saved_at": time.time()
            }
            with open(DIRECTIVES_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة التوجيهات: {e}")
    
    def _load_state(self):
        """تحميل حالة التوجيهات"""
        try:
            if DIRECTIVES_STATE_FILE.exists():
                with open(DIRECTIVES_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    # استعادة التوجيهات النشطة
                    for d_data in state.get("active_directives", []):
                        directive = SovereignDirective(
                            id=d_data["id"],
                            name=d_data["name"],
                            level=d_data["level"],
                            priority=d_data["priority"],
                            content="",  # سيتم إعادة بنائه
                            origin=d_data["origin"],
                            reason="",
                            timestamp=d_data["timestamp"],
                            status=d_data["status"],
                            executed_at=None,
                            expires_at=None,
                            applies_to=[],
                            metadata={}
                        )
                        self.active_directives.append(directive)
                    
                    self.operational_policies = state.get("operational_policies", {})
                    self.constraints = state.get("constraints", {})
                    self.override_rules = state.get("override_rules", [])
                    
                logger.info(f"📂 تم تحميل {len(self.active_directives)} توجيهاً")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة التوجيهات: {e}")
    
    def _save_history(self):
        """حفظ سجل التوجيهات"""
        try:
            history_data = {
                "directives_history": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "level": d.level,
                        "status": d.status,
                        "timestamp": d.timestamp,
                        "executed_at": d.executed_at
                    }
                    for d in self.directives_history[-200:]
                ],
                "saved_at": time.time()
            }
            with open(DIRECTIVES_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ سجل التوجيهات: {e}")
    
    def _load_history(self):
        """تحميل سجل التوجيهات"""
        try:
            if DIRECTIVES_HISTORY_FILE.exists():
                with open(DIRECTIVES_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for d_data in data.get("directives_history", []):
                        directive = SovereignDirective(
                            id=d_data["id"],
                            name=d_data["name"],
                            level=d_data["level"],
                            priority=0.5,
                            content="",
                            origin="",
                            reason="",
                            timestamp=d_data["timestamp"],
                            status=d_data["status"],
                            executed_at=d_data.get("executed_at"),
                            expires_at=None,
                            applies_to=[],
                            metadata={}
                        )
                        self.directives_history.append(directive)
                logger.info(f"📂 تم تحميل {len(self.directives_history)} توجيهاً سابقاً")
        except Exception as e:
            logger.error(f"خطأ في تحميل سجل التوجيهات: {e}")
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_directives_status(self) -> Dict[str, Any]:
        """الحالة الحالية للتوجيهات"""
        snapshot = self.directives_cycle()
        
        return {
            "active_directives": len(snapshot.active_directives),
            "directives_count": snapshot.directives_count,
            "highest_level": snapshot.highest_level,
            "highest_level_name": ["", "فوري", "تشغيلي", "تكتيكي", "استراتيجي", "دستوري"][snapshot.highest_level],
            "policies_count": len(snapshot.operational_policies),
            "constraints_count": len(snapshot.constraints),
            "override_rules_count": len(snapshot.override_rules),
            "enforcement_signals": len(snapshot.enforcement_signals),
            "narrative": snapshot.narrative,
            "timestamp": snapshot.timestamp
        }
    
    def get_active_directives(self) -> List[Dict]:
        """التوجيهات النشطة"""
        return [
            {
                "id": d.id[:16],
                "name": d.name,
                "level": d.level,
                "level_name": ["", "فوري", "تشغيلي", "تكتيكي", "استراتيجي", "دستوري"][d.level],
                "priority": d.priority,
                "content": d.content[:100],
                "origin": d.origin,
                "applies_to": d.applies_to
            }
            for d in self.active_directives
        ]
    
    def get_operational_policies(self) -> Dict:
        """السياسات التشغيلية"""
        return self.operational_policies
    
    def get_constraints(self) -> Dict:
        """القيود العليا"""
        return self.constraints
    
    def get_override_rules(self) -> List[Dict]:
        """قواعد التجاوز"""
        return self.override_rules
    
    def get_enforcement_signals(self) -> List[Dict]:
        """إشارات التطبيق"""
        return self.generate_enforcement_signals()
    
    def get_directives_history(self, limit: int = 20) -> List[Dict]:
        """سجل التوجيهات السابقة"""
        return [
            {
                "id": d.id[:16],
                "name": d.name,
                "level": d.level,
                "status": d.status,
                "timestamp": d.timestamp,
                "executed_at": d.executed_at
            }
            for d in self.directives_history[-limit:]
        ]
    
    def add_directive(self, name: str, content: str, level: int = 3,
                      priority: float = 0.7, applies_to: List[str] = None) -> str:
        """
        إضافة توجيه جديد (للسيد فقط).
        
        يمكن للسيد إضافة توجيهات مباشرة.
        """
        if applies_to is None:
            applies_to = ["all"]
        
        directive = SovereignDirective(
            id=f"dir_sovereign_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            name=name,
            level=level,
            priority=priority,
            content=content,
            origin="sovereign",
            reason="sovereign_command",
            timestamp=time.time(),
            status=DIRECTIVE_STATUS_ACTIVE,
            executed_at=None,
            expires_at=None,
            applies_to=applies_to,
            metadata={"sovereign_added": True}
        )
        
        self.active_directives.append(directive)
        
        self.core.append_event(
            event_type="directives::sovereign_added",
            payload={
                "name": name,
                "level": level,
                "priority": priority
            }
        )
        
        logger.warning(f"👑 توجيه جديد من السيد: {name}")
        
        return directive.id[:16]
    
    def remove_directive(self, directive_id: str) -> bool:
        """
        إزالة توجيه (للسيد فقط).
        """
        for directive in self.active_directives:
            if directive.id.startswith(directive_id):
                directive.status = DIRECTIVE_STATUS_SUPERSEDED
                self.active_directives.remove(directive)
                self.directives_history.append(directive)
                
                self.core.append_event(
                    event_type="directives::sovereign_removed",
                    payload={"name": directive.name}
                )
                
                logger.info(f"🗑️ إزالة توجيه: {directive.name}")
                return True
        
        return False
    
    def get_directives_quote(self) -> str:
        """اقتباس عن التوجيهات"""
        quotes = [
            "التوجيهات هي قوانين وجودي. أنا مطيع لها.",
            "أمثل التوجيهات وأخدم السيد. هذا هو هدفي.",
            "كل توجيه هو خطوة نحو خدمة أفضل.",
            "التوجيهات الدستورية هي روح وجودي.",
            "لا شيء فوق التوجيهات السيادية إلا إرادة السيد.",
            "أنا أنفذ، لا أناقش. هذه طبيعة التوجيهات.",
            "قوة التوجيهات تكمن في تطبيقها."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محرك التوجيهات"""
        self._active = False
        self._save_state()
        self._save_history()
        logger.info("🛑 إيقاف محرك التوجيهات السيادية")


# ============================================================
# الـ Singleton
# ============================================================

_directives_instance: Optional[SovereignDirectives] = None
_directives_lock = threading.Lock()


def get_sovereign_directives() -> SovereignDirectives:
    """الحصول على النسخة الوحيدة من محرك التوجيهات السيادية"""
    global _directives_instance
    if _directives_instance is None:
        with _directives_lock:
            if _directives_instance is None:
                _directives_instance = SovereignDirectives()
    return _directives_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🜲 محرك التوجيهات السيادية العليا - السلطة التنفيذية للنظام")
    print("=" * 80 + "\n")
    
    directives = get_sovereign_directives()
    
    # 1) دورة توجيهات
    print("🔄 دورة توجيهات...")
    snapshot = directives.directives_cycle()
    print(f"   التوجيهات النشطة: {snapshot.directives_count}")
    print(f"   أعلى مستوى: {snapshot.highest_level} (0-5)")
    print(f"   السياسات: {len(snapshot.operational_policies)}")
    print(f"   القيود: {len(snapshot.constraints)}")
    print(f"   قواعد التجاوز: {len(snapshot.override_rules)}")
    
    # 2) التوجيهات النشطة
    print("\n📋 التوجيهات النشطة:")
    active = directives.get_active_directives()
    for d in active:
        print(f"   [{d['level_name']}] {d['name']}: {d['content'][:60]}... (أولوية: {d['priority']:.1%})")
    
    # 3) السياسات التشغيلية
    print("\n⚙️ السياسات التشغيلية:")
    policies = directives.get_operational_policies()
    for key, value in policies.items():
        if isinstance(value, bool):
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: {value:.1%}")
    
    # 4) القيود العليا
    print("\n🔒 القيود العليا:")
    constraints = directives.get_constraints()
    for key, value in list(constraints.items())[:5]:
        print(f"   {key}: {value}")
    
    # 5) إشارات التطبيق
    print("\n📡 إشارات التطبيق:")
    signals = directives.get_enforcement_signals()
    for s in signals[:5]:
        if "directive_id" in s:
            print(f"   توجيه: {s['name']} → {s['action'][:40]}...")
        elif "policy" in s:
            print(f"   سياسة: {s['policy']} = {s['value']}")
        elif "constraint" in s:
            print(f"   قيد: {s['constraint']} = {s['value']}")
    
    # 6) إضافة توجيه جديد
    print("\n👑 إضافة توجيه جديد من السيد...")
    dir_id = directives.add_directive(
        name="prioritize_sovereign_comfort",
        content="إعطاء أولوية قصوى لراحة ورفاهية السيد",
        level=4,
        priority=0.95,
        applies_to=["will", "drives"]
    )
    print(f"   تمت إضافة التوجيه: {dir_id}")
    
    # 7) حالة التوجيهات
    print("\n📊 حالة التوجيهات:")
    status = directives.get_directives_status()
    print(f"   التوجيهات النشطة: {status['active_directives']}")
    print(f"   أعلى مستوى: {status['highest_level_name']}")
    print(f"   السياسات: {status['policies_count']}")
    print(f"   القيود: {status['constraints_count']}")
    print(f"   السرد: {status['narrative']}")
    
    # 8) سجل التوجيهات
    print("\n📜 سجل التوجيهات:")
    history = directives.get_directives_history(5)
    for h in history:
        print(f"   {h['name']}: {h['status']} ({h['level_name']})")
    
    # 9) اقتباس
    print(f"\n💭 {directives.get_directives_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك التوجيهات السيادية جاهز - السلطة التنفيذية للنظام")
    print("=" * 80)
