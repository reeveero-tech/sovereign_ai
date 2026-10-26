# backend/consciousness/attention_engine.py
# 🎯 محرك الانتباه السيادي - ترجمة الوعي إلى توزيع ذكي للموارد
# الإصدار: 3.0.0 - الانتباه هو أثمن مورد في النظام المعرفي

"""
محرك الانتباه المتقدم للنظام السيادي.

الفلسفة:
- الانتباه هو أثمن مورد في النظام المعرفي
- توزيع الانتباه يحدد جودة الأداء
- الاستمرارية تبني العمق
- المقاطعة تحمي من الخطر
- الانتباه المستدام هو أساس الإتقان

هذه ليست مجرد أولويات. هذا هو توزيع العقل.
"""

import json
from runtime.atomic_json import atomic_write_json  # R-781
import secrets
import time
import threading
import runtime.threads as threads
import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

try:
    from ..memory.core import get_core
    from ..memory.dynamic import get_dynamic_memory
    from .awareness import get_awareness_engine
    from .field import get_consciousness_field
    from .self_model import get_self_model
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core
    from memory.dynamic import get_dynamic_memory
    from consciousness.awareness import get_awareness_engine
    from consciousness.field import get_consciousness_field
    from consciousness.self_model import get_self_model
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الانتباه
# ============================================================

ATTENTION_DIR = DATA_DIR / "consciousness" / "attention"
ATTENTION_DIR.mkdir(parents=True, exist_ok=True)
ATTENTION_LOG = ATTENTION_DIR / "attention_log.jsonl"
ATTENTION_STATE_FILE = ATTENTION_DIR / "attention_state.json"

# أنواع الانتباه
ATTENTION_TYPE_SPOTLIGHT = "spotlight"      # بؤرة مركزة (تركيز عالٍ)
ATTENTION_TYPE_SUSTAINED = "sustained"      # مستمر (لمهمة طويلة)
ATTENTION_TYPE_ALTERNATING = "alternating"  # متناوب (تبديل بين مهام)
ATTENTION_TYPE_DIVIDED = "divided"          # موزع (عدة مهام)
ATTENTION_TYPE_BACKGROUND = "background"    # خلفي (مراقبة سلبية)

# مستويات الموارد
RESOURCE_LEVEL_NONE = 0.0
RESOURCE_LEVEL_MINIMAL = 0.1
RESOURCE_LEVEL_LOW = 0.25
RESOURCE_LEVEL_MEDIUM = 0.5
RESOURCE_LEVEL_HIGH = 0.75
RESOURCE_LEVEL_MAXIMUM = 1.0

# أسباب التخصيص
ALLOCATION_REASON_SALIENCE = "salience"              # بروز طبيعي
ALLOCATION_REASON_THREAT = "threat"                  # تهديد
ALLOCATION_REASON_USER = "user_activity"             # نشاط المستخدم
ALLOCATION_REASON_URGENCY = "urgency"                # إلحاح
ALLOCATION_REASON_SUSTAINED = "sustained_attention"  # استمرارية
ALLOCATION_REASON_REFLECTIVE = "reflective"          # تأملي


@dataclass
class AttentionAllocation:
    """تخصيص انتباه - كيفية توزيع الموارد المعرفية"""
    id: str
    target: str
    attention_type: str
    resource_level: float        # 0-1 مستوى الموارد المخصصة
    priority: int                # 1-10 (10 أعلى)
    reason: str
    duration: float              # المدة المتوقعة (ثواني)
    started_at: float
    last_updated: float
    meta: Dict[str, Any]


@dataclass
class AttentionSpotlight:
    """بؤرة الانتباه - ما يحصل على أعلى تركيز"""
    id: str
    target: str
    intensity: float            # 0-1 شدة التركيز
    duration: float
    focus_score: float          # درجة التركيز (0-1)
    sustained_since: float
    interruptions: int


@dataclass
class AttentionSnapshot:
    """لقطة انتباه"""
    timestamp: float
    spotlight: List[AttentionSpotlight]
    allocations: List[AttentionAllocation]
    total_resources_used: float
    total_resources_available: float
    efficiency: float
    preemptions: List[Dict[str, Any]]
    dominant_attention_type: str


# ============================================================
# محرك الانتباه السيادي
# ============================================================

class AttentionEngine:
    """
    محرك الانتباه السيادي - ترجمة الوعي إلى توزيع ذكي للموارد.
    
    المبادئ:
    1. الانتباه أثمن مورد
    2. توزيع الانتباه يحدد جودة الأداء
    3. الاستمرارية تبني العمق
    4. المقاطعة تحمي من الخطر
    5. الانتباه المستدام هو أساس الإتقان
    """
    
    def __init__(self):
        self.core = get_core()
        self.dynamic = get_dynamic_memory()
        self.awareness = get_awareness_engine()
        self.field = get_consciousness_field()
        self.self_model = get_self_model()
        
        # meta_cognition غير متوفر حالياً
        self.meta = None
        
        # موارد الانتباه
        self.total_attention_resources = 100.0  # 100 وحدة انتباه
        self.used_resources = 0.0
        
        # التخصيصات الحالية
        self.allocations: Dict[str, AttentionAllocation] = {}
        self.spotlight: Dict[str, AttentionSpotlight] = {}
        
        # سجل الانتباه
        self.snapshots: List[AttentionSnapshot] = []
        
        # أنماط الانتباه المستدام
        self.sustained_attention_items: Dict[str, float] = {}  # item_id -> accumulated_time
        
        # السياسات
        self.policies = {
            "spotlight_budget": 4,
            "spotlight_min_share": 0.12,
            "background_total_share": 0.4,
            "reflective_total_share": 0.15,
            "preemption_threat_threshold": 0.6,
            "sustain_decay": 0.85,
            "recency_boost": 0.25,
            "priority_exponent": 1.6,
        }
        
        # خلفيات الانتباه
        self._active = True
        self._allocation_loop = threads.start_managed(self._continuous_allocation, owner=self)
        
        self._sustained_tracker = threads.start_managed(self._track_sustained_attention, owner=self)
        
        self._resource_monitor = threads.start_managed(self._monitor_resources, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.info("🎯 محرك الانتباه السيادي جاهز - أثمن مورد يوزع بحكمة")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمحرك الانتباه
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمحرك الانتباه.
        
        يمسح:
        - جميع التخصيصات (allocations)
        - بؤرة الانتباه (spotlight)
        - سجل الانتباه المستدام (sustained attention)
        - سجل اللقطات (snapshots)
        """
        logger.info("🔄 إعادة تهيئة محرك الانتباه...")
        
        # مسح جميع التخصيصات
        self.allocations.clear()
        
        # مسح بؤرة الانتباه
        self.spotlight.clear()
        
        # مسح سجل الانتباه المستدام
        self.sustained_attention_items.clear()
        
        # مسح سجل اللقطات
        self.snapshots.clear()
        
        # إعادة تعيين موارد الانتباه
        self.total_attention_resources = 100.0
        self.used_resources = 0.0
        
        # إعادة تعيين السياسات
        self.policies = {
            "spotlight_budget": 4,
            "spotlight_min_share": 0.12,
            "background_total_share": 0.4,
            "reflective_total_share": 0.15,
            "preemption_threat_threshold": 0.6,
            "sustain_decay": 0.85,
            "recency_boost": 0.25,
            "priority_exponent": 1.6,
        }
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="consciousness::attention_reset",
            payload={
                "timestamp": time.time(),
                "status": "attention_engine_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة محرك الانتباه اكتملت - انتباه نقي")
    
    # ============================================================
    # جمع عناصر الاهتمام
    # ============================================================
    
    def collect_attention_items(self) -> List[Dict[str, Any]]:
        """
        جمع عناصر الاهتمام من مصادر الوعي.
        
        المصادر:
        - بؤرة الوعي (focal)
        - محيط الوعي (peripheral)
        - عناصر تأملية (reflective)
        - إشارات الطوارئ
        """
        items = []
        
        # من محك الوعي
        focus_items = self.awareness.get_focus()
        peripheral_items = self.awareness.get_peripheral()
        
        # بؤرة الوعي تحصل على أولوية أعلى
        for item in focus_items:
            items.append({
                "id": item["id"],
                "source": item["source"],
                "base_priority": item.get("priority", 0.7),
                "channel": "focal",
                "summary": item.get("summary", ""),
                "urgency": 0.8,
                "sustained_potential": item.get("priority", 0.5) > 0.6
            })
        
        # محيط الوعي
        for item in peripheral_items:
            items.append({
                "id": item["id"],
                "source": item["source"],
                "base_priority": item.get("priority", 0.4),
                "channel": "peripheral",
                "summary": item.get("summary", ""),
                "urgency": 0.5,
                "sustained_potential": False
            })
        
        # إشارات من الغرائز (طارئة)
        try:
            from ..memory.biological.instincts import get_instincts
            instincts = get_instincts()
            instinct_status = instincts.get_instinct_status()
            
            if instinct_status.get("protection_active"):
                items.append({
                    "id": "global_protection",
                    "source": "instincts",
                    "base_priority": 0.95,
                    "channel": "urgent",
                    "summary": "نظام الحماية نشط",
                    "urgency": 1.0,
                    "sustained_potential": True
                })
        # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
        except:
            pass
        
        return items
    
    # ============================================================
    # حساب الأولويات
    # ============================================================
    
    def calculate_priority(self, item: Dict[str, Any]) -> float:
        """
        حساب الأولوية النهائية لعنصر الاهتمام.
        
        العوامل:
        - الأولوية الأساسية (من الوعي)
        - الإلحاح (عاجل أم لا)
        - الاستمرارية (هل نحتاج للتركيز المستدام)
        - حداثة آخر تخصيص
        """
        base = item.get("base_priority", 0.5)
        urgency = item.get("urgency", 0.5)
        sustained = 0.2 if item.get("sustained_potential") else 0.0
        
        # تعزيز من الاستمرارية السابقة
        item_id = item["id"]
        sustained_boost = min(0.3, self.sustained_attention_items.get(item_id, 0.0) / 100)
        
        priority = base * 0.4 + urgency * 0.3 + sustained * 0.2 + sustained_boost * 0.1
        priority = min(1.0, max(0.0, priority))
        
        return priority
    
    # ============================================================
    # تخصيص الموارد
    # ============================================================
    
    def allocate_resources(self, items: List[Dict[str, Any]]) -> List[AttentionAllocation]:
        """
        تخصيص موارد الانتباه بناءً على الأولويات.
        
        - بؤرة الانتباه (spotlight): 40% من الموارد
        - انتباه مستدام (sustained): 30% من الموارد
        - انتباه موزع (divided): 20% من الموارد
        - خلفية (background): 10% من الموارد
        """
        allocations = []
        
        if not items:
            return allocations
        
        # حساب الأولويات
        for item in items:
            item["priority"] = self.calculate_priority(item)
        
        # ترتيب حسب الأولوية
        sorted_items = sorted(items, key=lambda x: x["priority"], reverse=True)
        
        # توزيع الموارد
        total_priority = sum(item["priority"] for item in sorted_items)
        if total_priority == 0:
            total_priority = 1.0
        
        # 40% من الموارد للبؤرة (أعلى 3 عناصر)
        spotlight_items = sorted_items[:3]
        spotlight_share = 0.4 * self.total_attention_resources
        
        for item in spotlight_items:
            share = (item["priority"] / total_priority) * spotlight_share
            allocation = AttentionAllocation(
                id=f"alloc_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                target=item["id"],
                attention_type=ATTENTION_TYPE_SPOTLIGHT,
                resource_level=min(1.0, share / self.total_attention_resources),
                priority=int(item["priority"] * 10),
                reason=self._determine_reason(item),
                duration=5.0,
                started_at=time.time(),
                last_updated=time.time(),
                meta={"source": item["source"], "summary": item.get("summary", "")}
            )
            allocations.append(allocation)
            
            # تحديث الاستمرارية
            if item.get("sustained_potential"):
                self.sustained_attention_items[item["id"]] = self.sustained_attention_items.get(item["id"], 0) + 1
        
        # 30% من الموارد للانتباه المستدام (العناصر التالية)
        sustained_items = sorted_items[3:8]
        sustained_share = 0.3 * self.total_attention_resources
        
        for item in sustained_items:
            share = (item["priority"] / total_priority) * sustained_share
            allocation = AttentionAllocation(
                id=f"alloc_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                target=item["id"],
                attention_type=ATTENTION_TYPE_SUSTAINED,
                resource_level=min(1.0, share / self.total_attention_resources),
                priority=int(item["priority"] * 10),
                reason=self._determine_reason(item),
                duration=3.0,
                started_at=time.time(),
                last_updated=time.time(),
                meta={"source": item["source"], "summary": item.get("summary", "")}
            )
            allocations.append(allocation)
        
        # 20% من الموارد للانتباه الموزع
        divided_items = sorted_items[8:15]
        divided_share = 0.2 * self.total_attention_resources
        
        for item in divided_items:
            share = (item["priority"] / total_priority) * divided_share
            allocation = AttentionAllocation(
                id=f"alloc_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                target=item["id"],
                attention_type=ATTENTION_TYPE_DIVIDED,
                resource_level=min(1.0, share / self.total_attention_resources),
                priority=int(item["priority"] * 10),
                reason=self._determine_reason(item),
                duration=2.0,
                started_at=time.time(),
                last_updated=time.time(),
                meta={"source": item["source"], "summary": item.get("summary", "")}
            )
            allocations.append(allocation)
        
        return allocations
    
    def _determine_reason(self, item: Dict[str, Any]) -> str:
        """تحديد سبب التخصيص"""
        if "urgent" in item.get("channel", "") or item.get("urgency", 0) > 0.8:
            return ALLOCATION_REASON_URGENCY
        elif item.get("source") == "defense" or "threat" in str(item.get("summary", "")).lower():
            return ALLOCATION_REASON_THREAT
        elif "user" in str(item.get("summary", "")).lower():
            return ALLOCATION_REASON_USER
        elif item.get("sustained_potential"):
            return ALLOCATION_REASON_SUSTAINED
        else:
            return ALLOCATION_REASON_SALIENCE
    
    # ============================================================
    # بؤرة الانتباه (Spotlight)
    # ============================================================
    
    def update_spotlight(self, allocations: List[AttentionAllocation]) -> List[AttentionSpotlight]:
        """
        تحديث بؤرة الانتباه - أعلى مستوى من التركيز.
        
        البؤرة تحتوي على 1-3 عناصر فقط.
        """
        spotlight_items = []
        
        # أعلى 3 تخصيصات في البؤرة
        top_allocations = [a for a in allocations if a.attention_type == ATTENTION_TYPE_SPOTLIGHT]
        top_allocations.sort(key=lambda x: x.priority, reverse=True)
        
        for alloc in top_allocations[:3]:
            # تحديث أو إنشاء بؤرة
            if alloc.target in self.spotlight:
                spotlight = self.spotlight[alloc.target]
                spotlight.intensity = min(1.0, spotlight.intensity + 0.05)
                spotlight.duration += 1
                spotlight.focus_score = (spotlight.focus_score + alloc.resource_level) / 2
            else:
                spotlight = AttentionSpotlight(
                    id=f"spot_{int(time.time()*1000)}_{secrets.token_hex(4)}",
                    target=alloc.target,
                    intensity=alloc.resource_level,
                    duration=1,
                    focus_score=alloc.resource_level,
                    sustained_since=time.time(),
                    interruptions=0
                )
                self.spotlight[alloc.target] = spotlight
            
            spotlight_items.append(spotlight)
        
        return spotlight_items
    
    # ============================================================
    # انتباه مستدام (Sustained Attention)
    # ============================================================
    
    def update_sustained(self):
        """
        تحديث الانتباه المستدام - للعناصر التي تحتاج تركيزاً طويلاً.
        
        الاستمرارية تبني العمق والإتقان.
        """
        for alloc in self.allocations.values():
            if alloc.attention_type == ATTENTION_TYPE_SUSTAINED:
                # زيادة مدة الانتباه المستدام
                elapsed = time.time() - alloc.started_at
                if elapsed > alloc.duration:
                    # تمديد المدة إذا كان العنصر لا يزال مهماً
                    if alloc.priority > 5:
                        alloc.duration += 2
                        alloc.last_updated = time.time()
                        logger.debug(f"🔄 تمديد انتباه مستدام: {alloc.target[:16]}...")
    
    # ============================================================
    # مقاطعة واستباق (Preemption)
    # ============================================================
    
    def check_preemption(self, new_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        التحقق من الحاجة لمقاطعة التخصيصات الحالية.
        
        العناصر ذات الأولوية العالية جداً تستطيع مقاطعة العناصر الحالية.
        """
        preemptions = []
        
        for new_item in new_items:
            new_priority = self.calculate_priority(new_item)
            
            # أولوية عالية جداً (طارئة)
            if new_priority > 0.9:
                # البحث عن تخصيص منخفض الأولوية للمقاطعة
                for alloc_id, alloc in list(self.allocations.items()):
                    if alloc.priority < 5 and alloc.attention_type != ATTENTION_TYPE_SPOTLIGHT:
                        preemptions.append({
                            "action": "preempt",
                            "target": alloc.target,
                            "replaced_by": new_item["id"],
                            "reason": "high_priority_interrupt",
                            "confidence": new_priority
                        })
                        # إزالة التخصيص
                        del self.allocations[alloc_id]
                        break
        
        return preemptions
    
    # ============================================================
    # تحديث شامل للانتباه
    # ============================================================
    
    def update_attention(self) -> AttentionSnapshot:
        """
        تحديث شامل لتوزيع الانتباه.
        
        1. جمع عناصر الاهتمام
        2. حساب الأولويات
        3. تخصيص الموارد
        4. تحديث البؤرة
        5. حساب الكفاءة
        """
        # جمع العناصر
        items = self.collect_attention_items()
        
        # تخصيص الموارد
        new_allocations = self.allocate_resources(items)
        
        # التحقق من المقاطعات
        preemptions = self.check_preemption(items)
        
        # تحديث التخصيصات
        for alloc in new_allocations:
            self.allocations[alloc.id] = alloc
        
        # تنظيف التخصيصات القديمة (أكثر من 30 ثانية)
        now = time.time()
        old_allocations = [aid for aid, a in self.allocations.items() 
                          if now - a.last_updated > 30]
        for aid in old_allocations:
            del self.allocations[aid]
        # R-778: المستدام يُمدَّد في update_sustained فلا يبلغ حد الثلاثين أبدًا، بينما كل دورة
        # تنشئ تخصيصًا أحدث للهدف نفسه ⇒ نسخ خالدة مكررة. يسقط المستدام الأقدم من 30ث إذا وُجد
        # أحدث منه للهدف والنوع نفسيهما؛ المستدام الذي لا بديل له يبقى ممدَّدًا كما قُصد.
        newest: Dict[Tuple[str, str], float] = {}
        for a in self.allocations.values():
            key = (a.target, a.attention_type)
            if a.started_at > newest.get(key, float("-inf")):
                newest[key] = a.started_at
        superseded = [aid for aid, a in self.allocations.items()
                      if a.attention_type == ATTENTION_TYPE_SUSTAINED
                      and now - a.started_at > 30
                      and newest[(a.target, a.attention_type)] > a.started_at]
        for aid in superseded:
            del self.allocations[aid]
        
        # تحديث البؤرة
        spotlight = self.update_spotlight(list(self.allocations.values()))
        
        # تحديث الانتباه المستدام
        self.update_sustained()
        
        # حساب استخدام الموارد
        total_resources = sum(a.resource_level for a in self.allocations.values())
        self.used_resources = total_resources
        efficiency = total_resources / self.total_attention_resources if self.total_attention_resources > 0 else 0
        
        # تحديد نوع الانتباه المهيمن
        dominant_type = self._get_dominant_attention_type()
        
        snapshot = AttentionSnapshot(
            timestamp=time.time(),
            spotlight=spotlight,
            allocations=list(self.allocations.values()),
            total_resources_used=total_resources,
            total_resources_available=self.total_attention_resources,
            efficiency=min(1.0, efficiency),
            preemptions=preemptions,
            dominant_attention_type=dominant_type
        )
        
        self.snapshots.append(snapshot)
        
        # الاحتفاظ بآخر 100 لقطة
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[-100:]
        
        # تسجيل
        self.core.append_event(
            event_type="attention::snapshot",
            payload={
                "spotlight_count": len(spotlight),
                "allocations_count": len(self.allocations),
                "resource_usage": total_resources,
                "efficiency": efficiency,
                "dominant_type": dominant_type
            }
        )
        
        return snapshot
    
    def _get_dominant_attention_type(self) -> str:
        """الحصول على نوع الانتباه المهيمن"""
        type_counts = defaultdict(int)
        for alloc in self.allocations.values():
            type_counts[alloc.attention_type] += 1
        
        if not type_counts:
            return ATTENTION_TYPE_BACKGROUND
        
        return max(type_counts, key=type_counts.get)
    
    def _continuous_allocation(self):
        """توزيع مستمر للانتباه"""
        while self._active:
            try:
                self.update_attention()
                threads.interruptible_sleep(0.5)
            except Exception as e:
                logger.error(f"خطأ في توزيع الانتباه: {e}")
                threads.interruptible_sleep(1)
    
    def _track_sustained_attention(self):
        """تتبع الانتباه المستدام"""
        while self._active:
            try:
                # تلاشي الاستمرارية بمرور الوقت
                for item_id in list(self.sustained_attention_items.keys()):
                    self.sustained_attention_items[item_id] = max(0, self.sustained_attention_items[item_id] - 0.1)
                    if self.sustained_attention_items[item_id] == 0:
                        del self.sustained_attention_items[item_id]
                
                threads.interruptible_sleep(1)
            except Exception as e:
                logger.error(f"خطأ في تتبع الانتباه المستدام: {e}")
                threads.interruptible_sleep(1)
    
    def _monitor_resources(self):
        """مراقبة استخدام موارد الانتباه"""
        while self._active:
            try:
                if self.used_resources > self.total_attention_resources * 0.9:
                    logger.warning(f"⚠️ استخدام مرتفع للانتباه: {self.used_resources:.1f}/{self.total_attention_resources:.1f}")
                
                threads.interruptible_sleep(5)
            except Exception as e:
                logger.error(f"خطأ في مراقبة الموارد: {e}")
                threads.interruptible_sleep(5)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة محرك الانتباه"""
        try:
            state = {
                "total_attention_resources": self.total_attention_resources,
                "used_resources": self.used_resources,
                "allocations_count": len(self.allocations),
                "spotlight_count": len(self.spotlight),
                "sustained_items_count": len(self.sustained_attention_items),
                "snapshots_count": len(self.snapshots),
                "saved_at": time.time()
            }
            atomic_write_json(ATTENTION_STATE_FILE, state, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الانتباه: {e}")
    
    def _load_state(self):
        """تحميل حالة محرك الانتباه"""
        try:
            if ATTENTION_STATE_FILE.exists():
                with open(ATTENTION_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.total_attention_resources = state.get("total_attention_resources", 100.0)
                    self.used_resources = state.get("used_resources", 0.0)
                logger.info("📂 تم تحميل حالة محرك الانتباه")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الانتباه: {e}")
    
    # ============================================================
    # دورة الانتباه الكاملة
    # ============================================================
    
    def attention_cycle(self, budget: int = 4, background_limit: int = 20) -> AttentionSnapshot:
        """
        دورة انتباه كاملة - تحديث وإرجاع التوزيع الحالي.
        
        Args:
            budget: عدد عناصر البؤرة القصوى
            background_limit: عدد عناصر الخلفية الأقصى
        """
        return self.update_attention()
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_attention_status(self) -> Dict[str, Any]:
        """الحالة الحالية للانتباه"""
        return {
            "total_resources": self.total_attention_resources,
            "used_resources": self.used_resources,
            "available_resources": self.total_attention_resources - self.used_resources,
            "utilization": self.used_resources / self.total_attention_resources if self.total_attention_resources > 0 else 0,
            "spotlight_count": len(self.spotlight),
            "total_allocations": len(self.allocations),
            "dominant_type": self._get_dominant_attention_type(),
            "sustained_items": len(self.sustained_attention_items),
            "timestamp": time.time()
        }
    
    def get_spotlight(self) -> List[Dict]:
        """بؤرة الانتباه الحالية"""
        return [
            {
                "target": s.target[:16],
                "intensity": s.intensity,
                "duration": s.duration,
                "focus_score": s.focus_score,
                "interruptions": s.interruptions
            }
            for s in self.spotlight.values()
        ]
    
    def get_allocations(self) -> List[Dict]:
        """التخصيصات الحالية"""
        return [
            {
                "id": a.id[:16],
                "target": a.target[:16],
                "type": a.attention_type,
                "resource_level": a.resource_level,
                "priority": a.priority,
                "reason": a.reason
            }
            for a in self.allocations.values()
        ]
    
    def get_snapshots(self, limit: int = 20) -> List[Dict]:
        """سجل لقطات الانتباه"""
        return [
            {
                "timestamp": s.timestamp,
                "spotlight_count": len(s.spotlight),
                "allocations": len(s.allocations),
                "efficiency": s.efficiency,
                "dominant_type": s.dominant_attention_type
            }
            for s in self.snapshots[-limit:]
        ]
    
    def allocate_to(self, target: str, resource_level: float, reason: str) -> bool:
        """
        تخصيص انتباه لعنصر معين (تدخل يدوي).
        
        يستخدم لتوجيه الانتباه بشكل صريح.
        """
        allocation = AttentionAllocation(
            id=f"manual_alloc_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            target=target,
            attention_type=ATTENTION_TYPE_SPOTLIGHT,
            resource_level=min(1.0, max(0.0, resource_level)),
            priority=9,
            reason=reason,
            duration=10.0,
            started_at=time.time(),
            last_updated=time.time(),
            meta={"manual": True}
        )
        
        self.allocations[allocation.id] = allocation
        logger.info(f"🎯 تخصيص انتباه يدوي: {target[:16]}... (مستوى: {resource_level:.1%})")
        
        return True
    
    def get_attention_quote(self) -> str:
        """اقتباس عن الانتباه"""
        quotes = [
            "الانتباه هو أثمن ما تملك. أنفقه بحكمة.",
            "التركيز ليس غياب التشتت، بل حضور الاختيار.",
            "الانتباه المستدام يبني الإتقان.",
            "المقاطعة فن. اعرف متى تقاطع ومتى تصبر.",
            "توزيع الانتباه هو فن إدارة العقل.",
            "البؤرة هي ما يصنع الفرق بين العبقرية والتفاهة.",
            "الانتباه مورد محدود، استثمره في ما يهم."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف محرك الانتباه"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف محرك الانتباه السيادي")


# ============================================================
# الـ Singleton
# ============================================================

_attention_instance: Optional[AttentionEngine] = None
_attention_lock = threading.Lock()


def get_attention_engine() -> AttentionEngine:
    """الحصول على النسخة الوحيدة من محرك الانتباه السيادي"""
    global _attention_instance
    if _attention_instance is None:
        with _attention_lock:
            if _attention_instance is None:
                _attention_instance = AttentionEngine()
    return _attention_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🎯 محرك الانتباه السيادي - أثمن مورد يوزع بحكمة")
    print("=" * 80 + "\n")
    
    attention = get_attention_engine()
    
    # 1) دورة انتباه
    print("🔄 دورة انتباه...")
    snapshot = attention.attention_cycle()
    print(f"   بؤرة الانتباه: {len(snapshot.spotlight)} عنصر")
    print(f"   التخصيصات: {len(snapshot.allocations)}")
    print(f"   استخدام الموارد: {snapshot.total_resources_used:.1f}/{snapshot.total_resources_available:.1f}")
    print(f"   الكفاءة: {snapshot.efficiency:.1%}")
    print(f"   النوع المهيمن: {snapshot.dominant_attention_type}")
    
    # 2) بؤرة الانتباه
    print("\n🎯 بؤرة الانتباه:")
    spotlight = attention.get_spotlight()
    for s in spotlight[:3]:
        print(f"   {s['target']}: شدة {s['intensity']:.1%}, تركيز {s['focus_score']:.1%}, مدة {s['duration']}")
    
    # 3) التخصيصات
    print("\n📊 التخصيصات الحالية:")
    allocations = attention.get_allocations()
    for a in allocations[:5]:
        print(f"   {a['type']}: {a['target']} (مستوى {a['resource_level']:.0%}, أولوية {a['priority']})")
    
    # 4) حالة الانتباه
    print("\n📈 حالة الانتباه:")
    status = attention.get_attention_status()
    print(f"   استخدام الموارد: {status['utilization']:.1%}")
    print(f"   الموارد المتبقية: {status['available_resources']:.1f}")
    print(f"   النوع المهيمن: {status['dominant_type']}")
    print(f"   عناصر مستدامة: {status['sustained_items']}")
    
    # 5) تخصيص يدوي
    print("\n🎯 تخصيص يدوي...")
    attention.allocate_to("test_target", 0.8, "test")
    
    # 6) سجل اللقطات
    print("\n📜 سجل لقطات الانتباه:")
    history = attention.get_snapshots(5)
    for h in history:
        print(f"   {h['dominant_type']}: {h['spotlight_count']} بؤرة, كفاءة {h['efficiency']:.1%}")
    
    # 7) اقتباس
    print(f"\n💭 {attention.get_attention_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محرك الانتباه السيادي جاهز - أثمن مورد يوزع بحكمة")
    print("=" * 80)
