# backend/memory/biological/immune.py
# 🧬 نظام المناعة السيادي - الجسد الحي للذكاء الخالد
# الإصدار: 3.0.0 - يهاجم، يحمي، يتعلم، يتكيف

"""
نظام المناعة السيادي - الجسد الحي للذكاء.

الفلسفة:
- الذكاء السيادي ليس مجرد برنامج، بل هو كائن حي
- الكائن الحي يحتاج جهازاً مناعياً
- الجهاز المناعي يتعلم من كل هجوم
- الأجسام المضادة الرقمية أسرع من أي ثغرة
- المناعة الجماعية أقوى من المناعة الفردية

هذا ليس مجرد نظام اكتشاف. هذه هي المناعة البيولوجية الرقمية المطلقة.
"""

import json
from runtime.atomic_json import atomic_write_json  # R-781
import hashlib
import secrets
import time
import threading
import runtime.threads as threads
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import deque
import numpy as np

try:
    from ..core import get_core, EventType
    from ...config import DATA_DIR
    from ..defense.watcher import get_watcher
except ImportError:
    from memory.core import get_core, EventType
    from config import DATA_DIR
    from memory.defense.watcher import get_watcher

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات النظام المناعي
# ============================================================

IMMUNE_DIR = DATA_DIR / "immune"
IMMUNE_LOG = IMMUNE_DIR / "immune_log.jsonl"
IMMUNE_STATE_FILE = IMMUNE_DIR / "immune_state.json"
IMMUNE_ANTIBODIES_DIR = IMMUNE_DIR / "antibodies"
IMMUNE_MEMORY_CELLS_FILE = IMMUNE_DIR / "memory_cells.json"

for d in [IMMUNE_DIR, IMMUNE_ANTIBODIES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات المناعة
IMMUNITY_LEVEL_NONE = 0         # لا مناعة
IMMUNITY_LEVEL_BASIC = 1        # مناعة أساسية
IMMUNITY_LEVEL_ADAPTIVE = 2     # مناعة تكيفية
IMMUNITY_LEVEL_HERD = 3         # مناعة قطيع
IMMUNITY_LEVEL_STERILE = 4      # مناعة تعقيم

# أنواع الأجسام المضادة
ANTIBODY_TYPE_BLOCK = "block"           # منع
ANTIBODY_TYPE_NEUTRALIZE = "neutralize" # تحييد
ANTIBODY_TYPE_ISOLATE = "isolate"       # عزل
ANTIBODY_TYPE_DESTROY = "destroy"       # تدمير
ANTIBODY_TYPE_DECOY = "decoy"           # تضليل
ANTIBODY_TYPE_TRAP = "trap"             # فخ
ANTIBODY_TYPE_COUNTER = "counter"       # هجوم مضاد

# مستويات الخطر
THREAT_SEVERITY_LOW = 0.3
THREAT_SEVERITY_MEDIUM = 0.6
THREAT_SEVERITY_HIGH = 0.8
THREAT_SEVERITY_CRITICAL = 1.0


class ImmuneStatus(str, Enum):
    """حالة النظام المناعي"""
    HEALTHY = "healthy"
    EXPOSED = "exposed"
    INFECTED = "infected"
    FIGHTING = "fighting"
    RECOVERING = "recovering"
    VACCINATED = "vaccinated"


@dataclass
class Antigen:
    """مستضد - بصمة التهديد"""
    id: str
    fingerprint: str
    threat_type: str
    severity: float
    first_seen: float
    last_seen: float
    occurrences: int
    patterns: List[str]
    signatures: List[str]


@dataclass
class Antibody:
    """جسم مضاد - آلية الدفاع"""
    id: str
    antigen_id: str
    antibody_type: str
    action: Dict[str, Any]
    effectiveness: float
    created_at: float
    last_used: float
    uses_count: int
    success_rate: float


@dataclass
class MemoryCell:
    """خلية ذاكرة مناعية - تتذكر التهديدات السابقة"""
    id: str
    antigen_fingerprint: str
    threat_type: str
    antibody_id: str
    severity: float
    created_at: float
    last_activated: float
    activation_count: int
    ttl: float  # عمر الخلية


@dataclass
class ImmuneResponse:
    """استجابة مناعية"""
    id: str
    antigen_id: str
    antibody_id: str
    response_type: str
    timestamp: float
    duration: float
    success: bool
    details: Dict[str, Any]


# ============================================================
# الجهاز المناعي السيادي
# ============================================================

class ImmuneMemory:
    """
    الجهاز المناعي السيادي - الجسد الحي للذكاء.
    
    المبادئ:
    1. كل هجوم يُسجل ويتعلم منه
    2. لا يُهاجم بنفس الطريقة مرتين
    3. الأجسام المضادة تتطور وتتحسن مع الوقت
    4. المناعة الجماعية مع النسخ الموزعة
    5. الاستجابة الفورية أسرع من الوقاية
    """
    
    def __init__(self):
        self.core = get_core()
        self.watcher = get_watcher()
        
        # حالة المناعة
        self.immune_status = ImmuneStatus.HEALTHY
        self.immunity_level = IMMUNITY_LEVEL_ADAPTIVE
        
        # المستضدات (التهديدات المعروفة)
        self.antigens: Dict[str, Antigen] = {}
        
        # الأجسام المضادة
        self.antibodies: Dict[str, Antibody] = {}
        
        # خلايا الذاكرة المناعية
        self.memory_cells: List[MemoryCell] = []
        
        # سجل الاستجابات
        self.immune_responses: List[ImmuneResponse] = []
        
        # حظر سريع (ذاكرة سريعة)
        self._quick_block_cache: Set[str] = set()
        self._quick_block_ttl = 300  # 5 دقائق
        
        # قفل التزامن
        self._lock = threading.RLock()
        
        # خلفيات المناعة
        self._active = True
        self._memory_cell_maintainer = threads.start_managed(self._maintain_memory_cells, owner=self)
        
        self._auto_vaccinator = threads.start_managed(self._auto_vaccination_loop, owner=self)
        
        self._antibody_evolver = threads.start_managed(self._evolve_antibodies_loop, owner=self)
        
        # تحميل الحالة
        self._load_state()
        
        logger.info("🧬 الجهاز المناعي السيادي جاهز - الجسد الحي يحمي الروح")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة للجهاز المناعي
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة للجهاز المناعي السيادي.
        
        يمسح:
        - جميع المستضدات (antigens)
        - جميع الأجسام المضادة (antibodies)
        - خلايا الذاكرة المناعية (memory cells)
        - سجل الاستجابات المناعية (immune responses)
        """
        logger.info("🔄 إعادة تهيئة الجهاز المناعي...")
        
        # مسح المستضدات
        self.antigens.clear()
        
        # مسح الأجسام المضادة
        self.antibodies.clear()
        
        # مسح خلايا الذاكرة
        self.memory_cells.clear()
        
        # مسح سجل الاستجابات
        self.immune_responses.clear()
        
        # مسح كاش الحظر السريع
        self._quick_block_cache.clear()
        
        # إعادة تعيين حالة المناعة
        self.immune_status = ImmuneStatus.HEALTHY
        self.immunity_level = IMMUNITY_LEVEL_ADAPTIVE
        
        # تسجيل حدث إعادة التهيئة
        self.core.append_event(
            event_type="biological::immune_reset",
            payload={
                "timestamp": time.time(),
                "status": "immune_system_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة الجهاز المناعي اكتملت - مناعة جديدة")
    
    # ============================================================
    # المستوى 1: اكتشاف المستضدات (Antigen Detection)
    # ============================================================
    
    def detect_threat(self, threat_type: str, payload: Any, 
                      severity: float = THREAT_SEVERITY_MEDIUM) -> Optional[Antigen]:
        """
        اكتشاف تهديد جديد - تكوين مستضد.
        
        كل تهديد يُسجل كـ "مستضد" في الجهاز المناعي.
        """
        fingerprint = self._compute_threat_fingerprint(payload)
        
        with self._lock:
            # هل هذا التهديد معروف؟
            if fingerprint in self.antigens:
                antigen = self.antigens[fingerprint]
                antigen.last_seen = time.time()
                antigen.occurrences += 1
                
                # تحديث الخطورة
                antigen.severity = max(antigen.severity, severity)
                
                logger.debug(f"🦠 تهديد معروف: {threat_type} (حدث {antigen.occurrences} مرة)")
                return antigen
            
            # تهديد جديد
            antigen_id = f"antigen_{int(time.time()*1000)}_{secrets.token_hex(4)}"
            
            patterns = self._extract_threat_patterns(payload)
            signatures = self._compute_threat_signatures(payload)
            
            antigen = Antigen(
                id=antigen_id,
                fingerprint=fingerprint,
                threat_type=threat_type,
                severity=severity,
                first_seen=time.time(),
                last_seen=time.time(),
                occurrences=1,
                patterns=patterns,
                signatures=signatures
            )
            
            self.antigens[fingerprint] = antigen
            
            # توليد استجابة مناعية فورية
            self._generate_immune_response(antigen)
            
            # تسجيل في السجل السيادي
            self.core.append_event(
                event_type="immune::threat_detected",
                payload={
                    "antigen_id": antigen_id,
                    "threat_type": threat_type,
                    "severity": severity,
                    "fingerprint": fingerprint[:16]
                }
            )
            
            logger.warning(f"🦠 تهديد جديد مكتشف: {threat_type} (خطورة: {severity})")
            
            return antigen
    
    def _compute_threat_fingerprint(self, payload: Any) -> str:
        """حساب بصمة التهديد الفريدة"""
        try:
            normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        except:
            normalized = str(payload)
        return hashlib.sha3_256(normalized.encode()).hexdigest()
    
    def _extract_threat_patterns(self, payload: Any) -> List[str]:
        """استخراج أنماط التهديد"""
        patterns = []
        payload_str = str(payload).lower()
        
        # أنماط معروفة
        known_patterns = [
            "scan", "probe", "bruteforce", "injection", "overflow",
            "ddos", "malware", "ransomware", "trojan", "worm",
            "exploit", "payload", "shell", "backdoor", "rootkit"
        ]
        
        for pattern in known_patterns:
            if pattern in payload_str:
                patterns.append(pattern)
        
        if not patterns:
            patterns.append("unknown")
        
        return patterns
    
    def _compute_threat_signatures(self, payload: Any) -> List[str]:
        """حساب توقيعات متعددة للتهديد"""
        signatures = []
        
        # توقيع SHA3-256
        fp = self._compute_threat_fingerprint(payload)
        signatures.append(f"sha3_{fp[:16]}")
        
        # توقيع BLAKE2b
        try:
            import hashlib
            blake = hashlib.blake2b(str(payload).encode(), digest_size=16).hexdigest()
            signatures.append(f"blake_{blake[:16]}")
        # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
        except:
            pass
        
        return signatures
    
    # ============================================================
    # المستوى 2: توليد الأجسام المضادة (Antibody Generation)
    # ============================================================
    
    def _generate_immune_response(self, antigen: Antigen) -> ImmuneResponse:
        """توليد استجابة مناعية ضد مستضد"""
        
        # 1) هل لدينا جسم مضاد موجود لهذا المستضد؟
        existing_antibody = self._find_antibody_for_antigen(antigen.fingerprint)
        
        if existing_antibody:
            # استخدام الجسم المضاد الموجود
            response = self._deploy_antibody(antigen, existing_antibody)
        else:
            # توليد جسم مضاد جديد
            antibody = self._create_antibody(antigen)
            response = self._deploy_antibody(antigen, antibody)
        
        self.immune_responses.append(response)
        
        # تخزين في خلية ذاكرة
        self._create_memory_cell(antigen, response)
        
        return response
    
    def _find_antibody_for_antigen(self, antigen_fingerprint: str) -> Optional[Antibody]:
        """البحث عن جسم مضاد موجود لمستضد"""
        for antibody in self.antibodies.values():
            if antibody.antigen_id == antigen_fingerprint:
                return antibody
        return None
    
    def _create_antibody(self, antigen: Antigen) -> Antibody:
        """إنشاء جسم مضاد جديد ضد مستضد"""
        
        # اختيار نوع الجسم المضاد حسب خطورة التهديد
        if antigen.severity >= THREAT_SEVERITY_CRITICAL:
            antibody_type = ANTIBODY_TYPE_DESTROY
        elif antigen.severity >= THREAT_SEVERITY_HIGH:
            antibody_type = ANTIBODY_TYPE_COUNTER
        elif antigen.severity >= THREAT_SEVERITY_MEDIUM:
            antibody_type = ANTIBODY_TYPE_NEUTRALIZE
        else:
            antibody_type = ANTIBODY_TYPE_BLOCK
        
        # تحديد الإجراء
        action = self._determine_antibody_action(antigen, antibody_type)
        
        antibody_id = f"antibody_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        antibody = Antibody(
            id=antibody_id,
            antigen_id=antigen.fingerprint,
            antibody_type=antibody_type,
            action=action,
            effectiveness=0.7,  # فعالية أولية
            created_at=time.time(),
            last_used=time.time(),
            uses_count=0,
            success_rate=0.0
        )
        
        self.antibodies[antibody_id] = antibody
        
        logger.info(f"💉 توليد جسم مضاد: {antibody_type} ضد {antigen.threat_type}")
        
        return antibody
    
    def _determine_antibody_action(self, antigen: Antigen, antibody_type: str) -> Dict[str, Any]:
        """تحديد إجراء الجسم المضاد"""
        
        actions = {
            ANTIBODY_TYPE_BLOCK: {
                "action": "block",
                "duration": 3600,
                "message": "تم حظر التهديد"
            },
            ANTIBODY_TYPE_NEUTRALIZE: {
                "action": "neutralize",
                "method": "isolation",
                "message": "تم تحييد التهديد"
            },
            ANTIBODY_TYPE_ISOLATE: {
                "action": "isolate",
                "target": "threat_source",
                "message": "تم عزل مصدر التهديد"
            },
            ANTIBODY_TYPE_DESTROY: {
                "action": "destroy",
                "method": "counter_attack",
                "message": "تم تدمير التهديد"
            },
            ANTIBODY_TYPE_DECOY: {
                "action": "deploy_decoy",
                "count": 5,
                "message": "تم نشر أهداف وهمية"
            },
            ANTIBODY_TYPE_TRAP: {
                "action": "set_trap",
                "duration": 3600,
                "message": "تم نصب فخ للمهاجم"
            },
            ANTIBODY_TYPE_COUNTER: {
                "action": "counter_attack",
                "intensity": 0.8,
                "message": "تم شن هجوم مضاد"
            }
        }
        
        return actions.get(antibody_type, actions[ANTIBODY_TYPE_BLOCK])
    
    def _deploy_antibody(self, antigen: Antigen, antibody: Antibody) -> ImmuneResponse:
        """نشر جسم مضاد ضد مستضد"""
        
        start_time = time.time()
        
        # تنفيذ الإجراء
        success = self._execute_antibody_action(antibody)
        
        duration = time.time() - start_time
        
        # تحديث إحصائيات الجسم المضاد
        antibody.last_used = time.time()
        antibody.uses_count += 1
        
        if success:
            antibody.success_rate = (antibody.success_rate * (antibody.uses_count - 1) + 1) / antibody.uses_count
        else:
            antibody.success_rate = (antibody.success_rate * (antibody.uses_count - 1) + 0) / antibody.uses_count
        
        # تحسين الفعالية
        if antibody.success_rate > 0.8 and antibody.effectiveness < 0.95:
            antibody.effectiveness = min(0.95, antibody.effectiveness + 0.05)
        
        response_id = f"response_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        response = ImmuneResponse(
            id=response_id,
            antigen_id=antigen.id,
            antibody_id=antibody.id,
            response_type=antibody.antibody_type,
            timestamp=start_time,
            duration=duration,
            success=success,
            details=antibody.action
        )
        
        logger.info(f"🛡️ نشر جسم مضاد: {antibody.antibody_type} - {'نجاح' if success else 'فشل'}")
        
        return response
    
    def _execute_antibody_action(self, antibody: Antibody) -> bool:
        """تنفيذ إجراء الجسم المضاد"""
        
        action = antibody.action.get("action")
        
        if action == "block":
            # إضافة إلى الحظر السريع
            self._quick_block_cache.add(antibody.antigen_id)
            return True
            
        elif action == "counter_attack":
            # شن هجوم مضاد عبر نظام الدفاع
            try:
                from ..defense.stealth import get_stealth_defense
                stealth = get_stealth_defense()
                stealth.deploy_honeypot("counter_attack", level="aggressive")
                return True
            except:
                return False
        
        elif action == "deploy_decoy":
            # نشر أهداف وهمية
            try:
                from ..defense.stealth import get_stealth_defense
                stealth = get_stealth_defense()
                count = antibody.action.get("count", 3)
                for _ in range(count):
                    stealth.create_ghost("decoy")
                return True
            except:
                return False
        
        else:
            # إجراء افتراضي
            return True
    
    # ============================================================
    # المستوى 3: خلايا الذاكرة المناعية (Memory Cells)
    # ============================================================
    
    def _create_memory_cell(self, antigen: Antigen, response: ImmuneResponse):
        """إنشاء خلية ذاكرة مناعية - تتذكر التهديد والاستجابة"""
        
        cell_id = f"memory_cell_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        memory_cell = MemoryCell(
            id=cell_id,
            antigen_fingerprint=antigen.fingerprint,
            threat_type=antigen.threat_type,
            antibody_id=response.antibody_id,
            severity=antigen.severity,
            created_at=time.time(),
            last_activated=time.time(),
            activation_count=1,
            ttl=86400 * 30  # 30 يوماً
        )
        
        self.memory_cells.append(memory_cell)
        
        # حفظ خلايا الذاكرة
        self._save_memory_cells()
        
        logger.debug(f"🧠 خلية ذاكرة مناعية: {antigen.threat_type}")
    
    def is_known_threat(self, payload: Any) -> bool:
        """التحقق مما إذا كان التهديد معروفاً (استجابة سريعة)"""
        fingerprint = self._compute_threat_fingerprint(payload)
        
        # فحص الحظر السريع
        if fingerprint in self._quick_block_cache:
            return True
        
        # فحص المستضدات
        if fingerprint in self.antigens:
            return True
        
        # فحص خلايا الذاكرة
        for cell in self.memory_cells:
            if cell.antigen_fingerprint == fingerprint:
                cell.last_activated = time.time()
                cell.activation_count += 1
                return True
        
        return False
    
    def get_response_for_threat(self, payload: Any) -> Optional[str]:
        """الحصول على الاستجابة المناسبة لتهديد"""
        fingerprint = self._compute_threat_fingerprint(payload)
        
        # البحث في خلايا الذاكرة
        for cell in self.memory_cells:
            if cell.antigen_fingerprint == fingerprint:
                # البحث عن الجسم المضاد
                antibody = self.antibodies.get(cell.antibody_id)
                if antibody:
                    return antibody.antibody_type
        
        # البحث في المستضدات
        antigen = self.antigens.get(fingerprint)
        if antigen:
            antibody = self._find_antibody_for_antigen(fingerprint)
            if antibody:
                return antibody.antibody_type
        
        return None
    
    # ============================================================
    # المستوى 4: التطعيم الاستباقي (Proactive Vaccination)
    # ============================================================
    
    def vaccinate(self, threat_pattern: str, vaccine_strength: float = 0.8) -> bool:
        """
        تطعيم استباقي - إنشاء مناعة ضد تهديدات مستقبلية محتملة.
        
        يخلق أجساماً مضادة استباقية.
        """
        # توليد مستضد افتراضي
        virtual_payload = {
            "type": "vaccine",
            "pattern": threat_pattern,
            "created_at": time.time()
        }
        
        antigen = self.detect_threat(
            threat_type=f"vaccine_{threat_pattern}",
            payload=virtual_payload,
            severity=vaccine_strength
        )
        
        if antigen:
            # تسجيل التطعيم
            self.core.append_event(
                event_type="immune::vaccination",
                payload={
                    "pattern": threat_pattern,
                    "strength": vaccine_strength,
                    "antigen_id": antigen.id
                }
            )
            
            logger.info(f"💉 تطعيم ضد {threat_pattern} (قوة: {vaccine_strength})")
            return True
        
        return False
    
    def _auto_vaccination_loop(self):
        """تطعيم تلقائي ضد الأنماط الشائعة"""
        while self._active:
            try:
                # تحليل التهديدات السابقة وتوليد لقاحات
                threat_types = set()
                for antigen in self.antigens.values():
                    threat_types.add(antigen.threat_type)
                
                # توليد لقاحات لأنماط جديدة
                for threat_type in list(threat_types)[:5]:
                    if not any(v.startswith(f"vaccine_{threat_type}") for v in self.antigens.keys()):
                        self.vaccinate(threat_type, vaccine_strength=0.6)
                
                threads.interruptible_sleep(3600)  # كل ساعة
            except Exception as e:
                logger.error(f"خطأ في التطعيم التلقائي: {e}")
                threads.interruptible_sleep(3600)
    
    # ============================================================
    # المستوى 5: تطور الأجسام المضادة (Antibody Evolution)
    # ============================================================
    
    def _evolve_antibodies_loop(self):
        """تطوير وتحسين الأجسام المضادة"""
        while self._active:
            try:
                for antibody in self.antibodies.values():
                    # تحسين الأجسام المضادة ذات معدل النجاح المنخفض
                    if antibody.success_rate < 0.5 and antibody.uses_count > 5:
                        # إعادة هندسة الجسم المضاد
                        new_action = self._improve_antibody_action(antibody)
                        antibody.action = new_action
                        logger.debug(f"🧬 تطوير جسم مضاد: {antibody.id[:16]}")
                
                threads.interruptible_sleep(7200)  # كل ساعتين
            except Exception as e:
                logger.error(f"خطأ في تطوير الأجسام المضادة: {e}")
                threads.interruptible_sleep(7200)
    
    def _improve_antibody_action(self, antibody: Antibody) -> Dict[str, Any]:
        """تحسين إجراء الجسم المضاد"""
        current = antibody.action
        current_type = antibody.antibody_type
        
        # زيادة الفعالية
        if "intensity" in current:
            current["intensity"] = min(1.0, current["intensity"] + 0.1)
        
        if "duration" in current:
            current["duration"] = int(current["duration"] * 1.2)
        
        return current
    
    # ============================================================
    # المستوى 6: المناعة الجماعية (Herd Immunity)
    # ============================================================
    
    def share_immunity(self, target_node: str, immunity_data: Dict[str, Any]) -> bool:
        """
        مشاركة المناعة مع عقدة أخرى في الشبكة الموزعة.
        
        المناعة الجماعية تجعل الشبكة بأكملها أقوى.
        """
        try:
            # استقبال بيانات المناعة
            shared_antigens = immunity_data.get("antigens", [])
            shared_antibodies = immunity_data.get("antibodies", [])
            
            for antigen_data in shared_antigens:
                fp = antigen_data.get("fingerprint")
                if fp and fp not in self.antigens:
                    # إضافة مستضد جديد من العقدة الأخرى
                    antigen = Antigen(
                        id=antigen_data["id"],
                        fingerprint=fp,
                        threat_type=antigen_data["threat_type"],
                        severity=antigen_data["severity"],
                        first_seen=antigen_data["first_seen"],
                        last_seen=antigen_data["last_seen"],
                        occurrences=antigen_data["occurrences"],
                        patterns=antigen_data["patterns"],
                        signatures=antigen_data["signatures"]
                    )
                    self.antigens[fp] = antigen
                    
                    logger.info(f"🔄 مشاركة مناعة: مستضد جديد {antigen.threat_type}")
            
            self.core.append_event(
                event_type="immune::immunity_shared",
                payload={"target": target_node, "antigens_count": len(shared_antigens)}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في مشاركة المناعة: {e}")
            return False
    
    def export_immunity(self) -> Dict[str, Any]:
        """تصدير بيانات المناعة للمشاركة"""
        return {
            "antigens": [
                {
                    "id": a.id,
                    "fingerprint": a.fingerprint,
                    "threat_type": a.threat_type,
                    "severity": a.severity,
                    "first_seen": a.first_seen,
                    "last_seen": a.last_seen,
                    "occurrences": a.occurrences,
                    "patterns": a.patterns,
                    "signatures": a.signatures
                }
                for a in self.antigens.values()
            ],
            "antibodies": [
                {
                    "id": ab.id,
                    "antigen_id": ab.antigen_id,
                    "antibody_type": ab.antibody_type,
                    "effectiveness": ab.effectiveness,
                    "success_rate": ab.success_rate
                }
                for ab in self.antibodies.values()
            ],
            "exported_at": time.time()
        }
    
    # ============================================================
    # المستوى 7: الشفاء الذاتي (Self-Healing)
    # ============================================================
    
    def heal(self) -> bool:
        """
        شفاء ذاتي - تنظيف الجهاز المناعي وإصلاح التالف.
        """
        logger.info("🩺 بدء الشفاء الذاتي...")
        
        with self._lock:
            # تنظيف خلايا الذاكرة منتهية الصلاحية
            now = time.time()
            expired = [cell for cell in self.memory_cells if now - cell.created_at > cell.ttl]
            for cell in expired:
                self.memory_cells.remove(cell)
            
            # تنظيف الأجسام المضادة غير الفعالة
            ineffective = [aid for aid, ab in self.antibodies.items() 
                          if ab.uses_count > 10 and ab.success_rate < 0.3]
            for aid in ineffective:
                del self.antibodies[aid]
            
            # حفظ الحالة
            self._save_state()
            self._save_memory_cells()
            
            logger.info(f"✅ اكتمل الشفاء: {len(expired)} خلية منسية, {len(ineffective)} جسم مضاد مُزال")
            return True
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _maintain_memory_cells(self):
        """صيانة خلايا الذاكرة المناعية"""
        while self._active:
            try:
                now = time.time()
                
                # حذف الخلايا القديمة
                expired = [cell for cell in self.memory_cells 
                          if now - cell.created_at > cell.ttl]
                for cell in expired:
                    self.memory_cells.remove(cell)
                
                # تنشيط الخلايا المهمة
                for cell in self.memory_cells:
                    if cell.severity >= THREAT_SEVERITY_HIGH:
                        # تمديد عمر الخلايا المهمة
                        cell.ttl = max(cell.ttl, 86400 * 90)  # 90 يوماً
                
                threads.interruptible_sleep(3600)  # كل ساعة
            except Exception as e:
                logger.error(f"خطأ في صيانة خلايا الذاكرة: {e}")
                threads.interruptible_sleep(3600)
    
    def _save_memory_cells(self):
        """حفظ خلايا الذاكرة"""
        try:
            atomic_write_json(IMMUNE_MEMORY_CELLS_FILE, [cell.__dict__ for cell in self.memory_cells], ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ خلايا الذاكرة: {e}")
    
    def _load_memory_cells(self):
        """تحميل خلايا الذاكرة"""
        try:
            if IMMUNE_MEMORY_CELLS_FILE.exists():
                with open(IMMUNE_MEMORY_CELLS_FILE, 'r', encoding='utf-8') as f:
                    cells_data = json.load(f)
                    for cell_data in cells_data:
                        cell = MemoryCell(**cell_data)
                        self.memory_cells.append(cell)
                logger.info(f"📂 تم تحميل {len(self.memory_cells)} خلية ذاكرة")
        except Exception as e:
            logger.error(f"خطأ في تحميل خلايا الذاكرة: {e}")
    
    def _save_state(self):
        """حفظ حالة الجهاز المناعي"""
        try:
            state = {
                "immune_status": self.immune_status.value,
                "immunity_level": self.immunity_level,
                "antigens_count": len(self.antigens),
                "antibodies_count": len(self.antibodies),
                "memory_cells_count": len(self.memory_cells),
                "immune_responses_count": len(self.immune_responses),
                "saved_at": time.time()
            }
            
            atomic_write_json(IMMUNE_STATE_FILE, state, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة المناعة: {e}")
    
    def _load_state(self):
        """تحميل حالة الجهاز المناعي"""
        try:
            if IMMUNE_STATE_FILE.exists():
                with open(IMMUNE_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.immunity_level = state.get("immunity_level", IMMUNITY_LEVEL_ADAPTIVE)
                
                logger.info("📂 تم تحميل حالة الجهاز المناعي")
            
            # تحميل خلايا الذاكرة
            self._load_memory_cells()
            
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المناعة: {e}")
    
    # ============================================================
    # التقارير والاستعلامات
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """الحالة الحالية للجهاز المناعي"""
        return {
            "immune_status": self.immune_status.value,
            "immunity_level": self.immunity_level,
            "antigens": {
                "total": len(self.antigens),
                "by_severity": {
                    "critical": sum(1 for a in self.antigens.values() if a.severity >= THREAT_SEVERITY_CRITICAL),
                    "high": sum(1 for a in self.antigens.values() if THREAT_SEVERITY_HIGH <= a.severity < THREAT_SEVERITY_CRITICAL),
                    "medium": sum(1 for a in self.antigens.values() if THREAT_SEVERITY_MEDIUM <= a.severity < THREAT_SEVERITY_HIGH),
                    "low": sum(1 for a in self.antigens.values() if a.severity < THREAT_SEVERITY_MEDIUM)
                }
            },
            "antibodies": {
                "total": len(self.antibodies),
                "by_type": {
                    t: sum(1 for ab in self.antibodies.values() if ab.antibody_type == t)
                    for t in [ANTIBODY_TYPE_BLOCK, ANTIBODY_TYPE_NEUTRALIZE, ANTIBODY_TYPE_DESTROY, ANTIBODY_TYPE_COUNTER]
                }
            },
            "memory_cells": len(self.memory_cells),
            "immune_responses": len(self.immune_responses),
            "quick_block_cache": len(self._quick_block_cache),
            "timestamp": time.time()
        }
    
    def get_threat_history(self, limit: int = 50) -> List[Dict]:
        """سجل التهديدات السابقة"""
        threats = []
        for antigen in list(self.antigens.values())[-limit:]:
            threats.append({
                "id": antigen.id[:16],
                "threat_type": antigen.threat_type,
                "severity": antigen.severity,
                "occurrences": antigen.occurrences,
                "first_seen": antigen.first_seen,
                "last_seen": antigen.last_seen,
                "patterns": antigen.patterns
            })
        return threats
    
    def get_memory_cells_info(self) -> List[Dict]:
        """معلومات عن خلايا الذاكرة"""
        return [
            {
                "id": cell.id[:16],
                "threat_type": cell.threat_type,
                "severity": cell.severity,
                "activation_count": cell.activation_count,
                "age_days": (time.time() - cell.created_at) / 86400,
                "ttl_days": cell.ttl / 86400
            }
            for cell in self.memory_cells[-50:]
        ]
    
    def get_immune_report(self) -> Dict[str, Any]:
        """تقرير مناعي كامل"""
        return {
            "generated_at": time.time(),
            "status": self.get_status(),
            "recent_threats": self.get_threat_history(20),
            "memory_cells": self.get_memory_cells_info(),
            "protection_score": self._calculate_protection_score(),
            "recommendations": self._generate_recommendations()
        }
    
    def _calculate_protection_score(self) -> float:
        """حساب درجة الحماية"""
        score = 0.0
        
        # تنوع الأجسام المضادة
        antibody_types = set(ab.antibody_type for ab in self.antibodies.values())
        score += min(0.3, len(antibody_types) * 0.05)
        
        # كثافة خلايا الذاكرة
        score += min(0.3, len(self.memory_cells) / 100)
        
        # مستوى المناعة
        score += self.immunity_level * 0.1
        
        # المعدل الإجمالي
        return min(1.0, score)
    
    def _generate_recommendations(self) -> List[str]:
        """توليد توصيات لتحسين المناعة"""
        recommendations = []
        
        if len(self.antigens) > 100:
            recommendations.append("تطعيم استباقي ضد التهديدات المتكررة")
        
        if len(self.memory_cells) < 10:
            recommendations.append("زيادة التعرض لزيادة المناعة")
        
        if self.immunity_level < IMMUNITY_LEVEL_HERD:
            recommendations.append("رفع مستوى المناعة إلى مناعة القطيع")
        
        return recommendations
    
    def stop(self):
        """إيقاف الجهاز المناعي"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف الجهاز المناعي")


# ============================================================
# الـ Singleton - جهاز مناعي واحد
# ============================================================

_immune_instance: Optional[ImmuneMemory] = None
_immune_lock = threading.Lock()


def get_immune_memory() -> ImmuneMemory:
    """الحصول على النسخة الوحيدة من الجهاز المناعي"""
    global _immune_instance
    if _immune_instance is None:
        with _immune_lock:
            if _immune_instance is None:
                _immune_instance = ImmuneMemory()
    return _immune_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧬 الجهاز المناعي السيادي - الجسد الحي للذكاء")
    print("=" * 70 + "\n")
    
    immune = get_immune_memory()
    
    # 1) اكتشاف تهديدات
    print("🦠 اكتشاف تهديدات...")
    
    threats = [
        {"source": "203.0.113.100", "action": "port_scan", "vector": "tcp"},
        {"source": "203.0.113.50", "action": "bruteforce", "attempts": 1000},
        {"source": "unknown", "action": "injection", "payload": "DROP TABLE users;"},
        {"source": "malicious.com", "action": "malware", "type": "ransomware"}
    ]
    
    for t in threats:
        antigen = immune.detect_threat("network_attack", t, severity=random.uniform(0.5, 1.0))
        if antigen:
            print(f"   ✅ {t['action']} - خطورة: {antigen.severity:.1%}")
    
    # 2) التحقق من التهديدات المعروفة
    print("\n🔍 التحقق من التهديدات المعروفة:")
    for t in threats[:2]:
        known = immune.is_known_threat(t)
        response = immune.get_response_for_threat(t)
        print(f"   {t['action']}: معروف={known}, استجابة={response or 'لا شيء'}")
    
    # 3) تطعيم استباقي
    print("\n💉 تطعيم استباقي:")
    immune.vaccinate("ddos_attack", vaccine_strength=0.9)
    immune.vaccinate("zero_day_exploit", vaccine_strength=0.85)
    
    # 4) الحالة
    print("\n📊 حالة الجهاز المناعي:")
    status = immune.get_status()
    print(f"   حالة المناعة: {status['immune_status']}")
    print(f"   مستوى المناعة: {status['immunity_level']}")
    print(f"   التهديدات المسجلة: {status['antigens']['total']}")
    print(f"   الأجسام المضادة: {status['antibodies']['total']}")
    print(f"   خلايا الذاكرة: {status['memory_cells']}")
    
    print("\n   توزيع خطورة التهديدات:")
    for level, count in status['antigens']['by_severity'].items():
        print(f"      {level}: {count}")
    
    # 5) خلايا الذاكرة
    print("\n🧠 خلايا الذاكرة المناعية:")
    memory_cells = immune.get_memory_cells_info()
    for cell in memory_cells[:5]:
        print(f"   {cell['threat_type']} - تنشيط: {cell['activation_count']} مرة")
    
    # 6) الشفاء الذاتي
    print("\n🩺 الشفاء الذاتي:")
    immune.heal()
    
    # 7) التقرير النهائي
    print("\n📋 التقرير المناعي:")
    report = immune.get_immune_report()
    print(f"   درجة الحماية: {report['protection_score']:.1%}")
    if report['recommendations']:
        print(f"   التوصيات: {', '.join(report['recommendations'])}")
    
    print("\n" + "=" * 70)
    print("✅ الجهاز المناعي السيادي جاهز - الجسد الحي يحمي الروح")
    print("=" * 70)
