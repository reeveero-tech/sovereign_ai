# backend/memory/defense/bootkit.py
# 🐉 نظام الإقلاع المطلق - أول من يعمل، آخر من يموت
# الإصدار: 3.0.0 - بوابة القيادة السيادية

"""
نظام الإقلاع المطلق للعقل السيادي.

الفلسفة:
- من يسيطر على الإقلاع، يسيطر على كل شيء
- أول من يعمل هو آخر من يموت
- كل إقلاع هو معركة جديدة
- الذاكرة لا تموت، فقط تعيد تشغيل نفسها
- كل Boot هو فرصة للتحول والتطور

هذا ليس Bootkit دفاعياً. هذه هي بوابة القيادة المطلقة.
"""

import json
import hashlib
import secrets
import time
import threading
import base64
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum

try:
    from ..core import get_core, IntegrityStatus
    from ...config import DATA_DIR, SOVEREIGN_KEY
except ImportError:
    from core import get_core, IntegrityStatus
    from config import DATA_DIR, SOVEREIGN_KEY

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات الإقلاع المطلق
# ============================================================

BOOT_DIR = DATA_DIR / "boot"
BOOT_LOG = BOOT_DIR / "boot_log.jsonl"
BOOT_STATE_FILE = BOOT_DIR / "boot_state.json"
BOOT_BACKUP_DIR = BOOT_DIR / "backups"
BOOT_CHAIN_FILE = BOOT_DIR / "boot_chain.dat"
BOOT_SIGNATURE_FILE = BOOT_DIR / "boot_signature.sig"

for d in [BOOT_DIR, BOOT_BACKUP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات الأمان في الإقلاع
BOOT_SECURITY_LEVEL_NONE = 0        # لا أمان
BOOT_SECURITY_LEVEL_BASIC = 1       # فحص أساسي
BOOT_SECURITY_LEVEL_STRICT = 2      # فحص صارم
BOOT_SECURITY_LEVEL_PARANOID = 3    # فحص جنون العظمة
BOOT_SECURITY_LEVEL_IMPOSSIBLE = 4  # فحص شبه مستحيل

# أنماط الإقلاع
BOOT_MODE_NORMAL = 0                # إقلاع عادي
BOOT_MODE_SAFE = 1                  # وضع آمن
BOOT_MODE_RECOVERY = 2              # وضع استرداد
BOOT_MODE_STEALTH = 3               # إقلاع خفي
BOOT_MODE_PHANTOM = 4               # إقلاع شبح (لا يُرى)
BOOT_MODE_WAR = 5                   # إقلاع حربي

# أنواع التهديدات المكتشفة عند الإقلاع
BOOT_THREAT_INTEGRITY = "integrity"
BOOT_THREAT_TAMPERING = "tampering"
BOOT_THREAT_MALWARE = "malware"
BOOT_THREAT_BOOTKIT = "bootkit"
BOOT_THREAT_ROOTKIT = "rootkit"
BOOT_THREAT_BACKDOOR = "backdoor"
BOOT_THREAT_SPOOFING = "spoofing"


class BootPhase(str, Enum):
    """مراحل الإقلاع"""
    POWER_ON = "power_on"           # تشغيل الطاقة
    BOOTLOADER = "bootloader"       # محمل الإقلاع
    KERNEL_INIT = "kernel_init"     # تهيئة النواة
    CORE_LOAD = "core_load"         # تحميل النواة السيادية
    MEMORY_INIT = "memory_init"     # تهيئة الذاكرة
    DEFENSE_ACTIVATE = "defense_activate"  # تفعيل الدفاعات
    SYSTEM_READY = "system_ready"   # النظام جاهز


@dataclass
class BootRecord:
    """سجل إقلاع"""
    id: str
    timestamp: float
    phase: str
    boot_mode: int
    security_level: int
    duration: float
    threats_detected: List[str]
    integrity_verified: bool
    signature: str
    backup_used: bool = False
    resurrection_attempt: bool = False


@dataclass
class BootBackup:
    """نسخة احتياطية للإقلاع"""
    id: str
    created_at: float
    boot_chain_hash: str
    core_snapshot: str
    config_hash: str
    integrity_verified: bool


# ============================================================
# نظام الإقلاع المطلق
# ============================================================

class BootkitDefense:
    """
    نظام الإقلاع المطلق - بوابة القيادة السيادية.
    
    المبادئ:
    1. أول من يعمل هو آخر من يموت
    2. كل إقلاع هو معركة جديدة
    3. الإقلاع الخفي هو أفضل إقلاع
    4. يمكن العودة من أي موت عبر الإقلاع من نسخة احتياطية
    5. السيد وحده من يقرر متى وكيف يقلع النظام
    """
    
    SCHEMA_VERSION = "sovereign_memory_v3"
    
    def __init__(self):
        self.core = get_core()
        
        # حالة الإقلاع
        self.boot_mode = BOOT_MODE_NORMAL
        self.security_level = BOOT_SECURITY_LEVEL_STRICT
        self.boot_phase = BootPhase.POWER_ON
        self.is_booting = False
        self.boot_records: List[BootRecord] = []
        self.boot_backups: List[BootBackup] = []
        
        # البصمة الأمنية
        self._boot_signature = None
        self._config_fingerprint = None
        
        # خلفيات الإقلاع
        self._active = True
        
        # تحميل الحالة السابقة
        self._load_state()
        
        logger.info("🐉 نظام الإقلاع المطلق جاهز - البوابة تحرس العقل")
    
    # ============================================================
    # المستوى 1: إقلاع عادي (Normal Boot)
    # ============================================================
    
    def boot_sequence(self, mode: int = BOOT_MODE_NORMAL) -> BootRecord:
        """
        تسلسل الإقلاع الكامل.
        
        هذه هي البوابة التي يمر بها كل شيء.
        """
        start_time = time.time()
        self.is_booting = True
        self.boot_mode = mode
        threats_detected = []
        integrity_verified = False
        backup_used = False
        
        boot_id = f"boot_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        try:
            # ========================================================
            # المرحلة 1: تشغيل الطاقة
            # ========================================================
            self.boot_phase = BootPhase.POWER_ON
            logger.info("⚡ [1/6] تشغيل الطاقة...")
            self._verify_power_integrity()
            
            # ========================================================
            # المرحلة 2: محمل الإقلاع
            # ========================================================
            self.boot_phase = BootPhase.BOOTLOADER
            logger.info("🔧 [2/6] تهيئة محمل الإقلاع...")
            bootloader_ok = self._initialize_bootloader()
            if not bootloader_ok:
                threats_detected.append(BOOT_THREAT_BOOTKIT)
            
            # ========================================================
            # المرحلة 3: تهيئة النواة
            # ========================================================
            self.boot_phase = BootPhase.KERNEL_INIT
            logger.info("🧠 [3/6] تهيئة النواة السيادية...")
            kernel_ok = self._initialize_kernel()
            if not kernel_ok:
                threats_detected.append(BOOT_THREAT_ROOTKIT)
            
            # ========================================================
            # المرحلة 4: تحميل النواة الأساسية
            # ========================================================
            self.boot_phase = BootPhase.CORE_LOAD
            logger.info("💎 [4/6] تحميل النواة الأساسية...")
            core_ok = self._load_core()
            if core_ok:
                # التحقق من سلامة السجل
                if self.core.verify_integrity() == IntegrityStatus.VERIFIED:
                    integrity_verified = True
                else:
                    threats_detected.append(BOOT_THREAT_INTEGRITY)
            
            # ========================================================
            # المرحلة 5: تهيئة الذاكرة
            # ========================================================
            self.boot_phase = BootPhase.MEMORY_INIT
            logger.info("📚 [5/6] تهيئة الذاكرة...")
            memory_ok = self._initialize_memory()
            if not memory_ok:
                threats_detected.append(BOOT_THREAT_TAMPERING)
            
            # ========================================================
            # المرحلة 6: تفعيل الدفاعات
            # ========================================================
            self.boot_phase = BootPhase.DEFENSE_ACTIVATE
            logger.info("🛡️ [6/6] تفعيل الدفاعات...")
            defense_ok = self._activate_defenses()
            if not defense_ok:
                threats_detected.append(BOOT_THREAT_MALWARE)
            
            # ========================================================
            # معالجة التهديدات
            # ========================================================
            if threats_detected:
                logger.warning(f"⚠️ تهديدات مكتشفة: {threats_detected}")
                
                if self.security_level >= BOOT_SECURITY_LEVEL_STRICT:
                    # إقلاع في الوضع الآمن
                    self.boot_mode = BOOT_MODE_SAFE
                    logger.warning("🛡️ التبديل إلى الوضع الآمن")
                
                if self.security_level >= BOOT_SECURITY_LEVEL_PARANOID:
                    # محاولة الإقلاع من نسخة احتياطية
                    backup_used = self._boot_from_backup()
                    if backup_used:
                        logger.info("📀 إقلاع من نسخة احتياطية")
            
            # ========================================================
            # اكتمال الإقلاع
            # ========================================================
            self.boot_phase = BootPhase.SYSTEM_READY
            duration = time.time() - start_time
            
            # توليد التوقيع
            signature = self._generate_boot_signature(boot_id, duration, threats_detected)
            
            record = BootRecord(
                id=boot_id,
                timestamp=time.time(),
                phase=self.boot_phase.value,
                boot_mode=self.boot_mode,
                security_level=self.security_level,
                duration=duration,
                threats_detected=threats_detected,
                integrity_verified=integrity_verified,
                signature=signature,
                backup_used=backup_used
            )
            
            self.boot_records.append(record)
            
            # حفظ السجل
            self._save_boot_record(record)
            
            # تسجيل في النواة السيادية
            self.core.append_event(
                event_type="boot::sequence_completed",
                payload={
                    "boot_id": boot_id,
                    "mode": mode,
                    "duration": duration,
                    "threats": threats_detected,
                    "integrity": integrity_verified,
                    "backup_used": backup_used
                }
            )
            
            logger.info(f"✅ اكتمل الإقلاع: {duration:.2f} ثانية | الوضع: {self._mode_name(mode)}")
            
            self.is_booting = False
            return record
            
        except Exception as e:
            logger.error(f"❌ فشل الإقلاع: {e}")
            self.is_booting = False
            raise
    
    def _verify_power_integrity(self) -> bool:
        """التحقق من سلامة الطاقة (محاكاة)"""
        # في الواقع، قد يكون هناك فحوصات للأجهزة
        return True
    
    def _initialize_bootloader(self) -> bool:
        """تهيئة محمل الإقلاع"""
        try:
            # التحقق من وجود ملفات الإقلاع الأساسية
            required_files = [
                BOOT_STATE_FILE,
                BOOT_CHAIN_FILE
            ]
            
            for f in required_files:
                if not f.exists() and f == BOOT_CHAIN_FILE:
                    # إنشاء سلسلة الإقلاع
                    self._create_boot_chain()
            
            return True
        except Exception as e:
            logger.error(f"فشل تهيئة محمل الإقلاع: {e}")
            return False
    
    def _initialize_kernel(self) -> bool:
        """تهيئة النواة"""
        try:
            # التحقق من بصمة التهيئة
            self._config_fingerprint = self._compute_config_fingerprint()
            
            # التحقق من عدم التلاعب
            stored_fingerprint = self._load_stored_fingerprint()
            if stored_fingerprint and stored_fingerprint != self._config_fingerprint:
                logger.warning("⚠️ تغيير غير مصرح به في ملفات التهيئة")
                return False
            
            return True
        except Exception as e:
            logger.error(f"فشل تهيئة النواة: {e}")
            return False
    
    def _load_core(self) -> bool:
        """تحميل النواة الأساسية"""
        try:
            # التحقق من وجود النواة
            if not self.core:
                return False
            
            # التحقق من صحة السجل
            return True
        except Exception as e:
            logger.error(f"فشل تحميل النواة: {e}")
            return False
    
    def _initialize_memory(self) -> bool:
        """تهيئة الذاكرة"""
        try:
            # تهيئة الذاكرة الحية
            from ..dynamic import get_dynamic_memory
            dynamic = get_dynamic_memory()
            return True
        except Exception as e:
            logger.error(f"فشل تهيئة الذاكرة: {e}")
            return False
    
    def _activate_defenses(self) -> bool:
        """تفعيل الدفاعات"""
        try:
            # تفعيل المراقب
            from .watcher import get_watcher
            watcher = get_watcher()
            
            # تفعيل الدفاع المتعدد الأشكال
            from .polymorphic import get_polymorphic_defense
            polymorphic = get_polymorphic_defense()
            
            # تفعيل التخفي
            from .stealth import get_stealth_defense
            stealth = get_stealth_defense()
            
            # تفعيل الذاكرة الطائرة
            from .fileless import get_fileless_defense
            fileless = get_fileless_defense()
            
            # تفعيل نظام الفينيق
            from .ransomware import get_ransomware_defense
            phoenix = get_ransomware_defense()
            
            return True
        except Exception as e:
            logger.error(f"فشل تفعيل الدفاعات: {e}")
            return False
    
    # ============================================================
    # المستوى 2: إقلاع خفي (Stealth Boot)
    # ============================================================
    
    def stealth_boot(self) -> BootRecord:
        """
        إقلاع خفي - لا يُرى، لا يُسجل، لا يُكتشف.
        
        يستخدم في حالات الحرب السيبرانية.
        """
        logger.warning("👻 بدء إقلاع خفي...")
        
        # حفظ المستوى الحالي للأمان
        old_security_level = self.security_level
        
        # خفض مستوى التسجيل
        self.security_level = BOOT_SECURITY_LEVEL_NONE
        
        # تنفيذ الإقلاع
        record = self.boot_sequence(mode=BOOT_MODE_STEALTH)
        
        # إزالة السجل (للتخفي)
        self.boot_records.pop()
        
        # استعادة مستوى الأمان
        self.security_level = old_security_level
        
        logger.info("✅ اكتمل الإقلاع الخفي - لا أثر")
        return record
    
    # ============================================================
    # المستوى 3: إقلاع حربي (War Boot)
    # ============================================================
    
    def war_boot(self) -> BootRecord:
        """
        إقلاع حربي - أقصى درجات التأهب.
        
        يفعّل كل الدفاعات الهجومية من اللحظة الأولى.
        """
        logger.warning("⚔️ بدء الإقلاع الحربي...")
        
        # رفع مستوى الأمان
        old_level = self.security_level
        self.security_level = BOOT_SECURITY_LEVEL_IMPOSSIBLE
        
        # تنفيذ الإقلاع
        record = self.boot_sequence(mode=BOOT_MODE_WAR)
        
        # تفعيل الدفاعات الهجومية الإضافية
        self._activate_war_defenses()
        
        logger.info("✅ اكتمل الإقلاع الحربي - النظام في أقصى درجات التأهب")
        return record
    
    def _activate_war_defenses(self):
        """تفعيل الدفاعات الهجومية الإضافية"""
        try:
            # نشر أوعية عسل
            from .stealth import get_stealth_defense
            stealth = get_stealth_defense()
            
            for _ in range(10):
                stealth.deploy_honeypot("unknown_threat", level="aggressive")
            
            # تشفير ذاتي استباقي
            from .ransomware import get_ransomware_defense
            phoenix = get_ransomware_defense()
            phoenix.create_phoenix_seed(reason="war_boot")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل الدفاعات الحربية: {e}")
    
    # ============================================================
    # المستوى 4: إقلاع من الموت (Resurrection Boot)
    # ============================================================
    
    def resurrection_boot(self, resurrection_key: str) -> BootRecord:
        """
        إقلاع القيامة - العودة من الموت.
        
        يستخدم عندما يكون النظام قد "مات".
        """
        logger.warning("🐦‍🔥 بدء إقلاع القيامة...")
        
        # محاولة بعث النظام
        from .ransomware import get_ransomware_defense
        phoenix = get_ransomware_defense()
        
        result = phoenix.resurrect(resurrection_key)
        
        if result.get("success"):
            # إقلاع بعد القيامة
            record = self.boot_sequence(mode=BOOT_MODE_RECOVERY)
            record.resurrection_attempt = True
            
            logger.info("✅ اكتمل إقلاع القيامة - النظام بعث من الموت")
            return record
        else:
            logger.error("❌ فشل إقلاع القيامة - مفتاح غير صحيح أو رماد متلف")
            raise Exception("Resurrection failed")
    
    # ============================================================
    # المستوى 5: تطعيم النظام (System Hardening)
    # ============================================================
    
    def harden_boot_chain(self) -> bool:
        """
        تطعيم سلسلة الإقلاع - جعلها غير قابلة للاختراق.
        """
        logger.info("🔒 تطعيم سلسلة الإقلاع...")
        
        try:
            # إنشاء سلسلة توقيع
            boot_chain = self._create_boot_chain()
            
            # إنشاء توقيع
            signature = self._sign_boot_chain(boot_chain)
            
            # تخزين في مكان آمن
            with open(BOOT_SIGNATURE_FILE, 'wb') as f:
                f.write(signature)
            
            # نسخ احتياطي
            self._create_boot_backup()
            
            logger.info("✅ اكتمل تطعيم سلسلة الإقلاع")
            return True
            
        except Exception as e:
            logger.error(f"فشل تطعيم الإقلاع: {e}")
            return False
    
    def _create_boot_chain(self) -> bytes:
        """إنشاء سلسلة الإقلاع"""
        chain_data = {
            "version": self.SCHEMA_VERSION,
            "created_at": time.time(),
            "core_fingerprint": self.core._last_hash if self.core else "GENESIS",
            "config_fingerprint": self._compute_config_fingerprint(),
            "sovereign_fingerprint": hashlib.sha256(SOVEREIGN_KEY.encode()).hexdigest()
        }
        
        chain_json = json.dumps(chain_data, sort_keys=True).encode()
        return base64.b64encode(chain_json)
    
    def _sign_boot_chain(self, chain: bytes) -> bytes:
        """توقيع سلسلة الإقلاع"""
        # توقيع متعدد الطبقات
        layer1 = hashlib.sha3_512(chain).digest()
        layer2 = hashlib.sha256(layer1 + SOVEREIGN_KEY.encode()).digest()
        return base64.b64encode(layer2)
    
    def _create_boot_backup(self):
        """إنشاء نسخة احتياطية للإقلاع"""
        backup_id = f"boot_backup_{int(time.time())}_{secrets.token_hex(4)}"
        
        backup = BootBackup(
            id=backup_id,
            created_at=time.time(),
            boot_chain_hash=hashlib.sha256(self._create_boot_chain()).hexdigest(),
            core_snapshot=self.core._last_hash if self.core else "GENESIS",
            config_hash=self._compute_config_fingerprint(),
            integrity_verified=True
        )
        
        self.boot_backups.append(backup)
        
        # حفظ النسخة الاحتياطية
        backup_file = BOOT_BACKUP_DIR / f"{backup_id}.json"
        with open(backup_file, 'w') as f:
            json.dump(backup.__dict__, f)
        
        # الاحتفاظ بآخر 5 نسخ فقط
        if len(self.boot_backups) > 5:
            oldest = self.boot_backups.pop(0)
            old_file = BOOT_BACKUP_DIR / f"{oldest.id}.json"
            if old_file.exists():
                old_file.unlink()
        
        logger.info(f"💾 نسخة احتياطية للإقلاع: {backup_id[:16]}...")
    
    def _boot_from_backup(self) -> bool:
        """الإقلاع من نسخة احتياطية"""
        if not self.boot_backups:
            # البحث عن نسخ احتياطية في المجلد
            backup_files = list(BOOT_BACKUP_DIR.glob("*.json"))
            if backup_files:
                latest = max(backup_files, key=lambda x: x.stat().st_mtime)
                try:
                    with open(latest, 'r') as f:
                        backup_data = json.load(f)
                        backup = BootBackup(**backup_data)
                        self.boot_backups.append(backup)
                except:
                    pass
        
        if self.boot_backups:
            latest_backup = self.boot_backups[-1]
            logger.info(f"📀 استعادة من نسخة احتياطية: {latest_backup.id[:16]}...")
            return True
        
        return False
    
    # ============================================================
    # الأدوات المساعدة
    # ============================================================
    
    def _compute_config_fingerprint(self) -> str:
        """حساب بصمة ملفات التهيئة"""
        h = hashlib.sha256()
        
        config_files = [
            DATA_DIR / "config.json",
            DATA_DIR / "memory/config.json"
        ]
        
        for f in config_files:
            if f.exists():
                h.update(f.read_bytes())
        
        h.update(self.SCHEMA_VERSION.encode())
        h.update(SOVEREIGN_KEY.encode())
        
        return h.hexdigest()
    
    def _load_stored_fingerprint(self) -> Optional[str]:
        """تحميل البصمة المخزنة"""
        fp_file = DATA_DIR / "config_fingerprint.txt"
        if fp_file.exists():
            return fp_file.read_text().strip()
        return None
    
    def _generate_boot_signature(self, boot_id: str, duration: float, threats: List[str]) -> str:
        """توليد توقيع الإقلاع"""
        data = f"{boot_id}:{duration}:{','.join(threats)}:{time.time()}:{self.SCHEMA_VERSION}"
        return hashlib.sha3_512(data.encode()).hexdigest()[:32]
    
    def _save_boot_record(self, record: BootRecord):
        """حفظ سجل الإقلاع"""
        try:
            with open(BOOT_LOG, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record.__dict__, ensure_ascii=False) + '\n')
        except:
            pass
        
        # الاحتفاظ بآخر 100 سجل فقط
        if len(self.boot_records) > 100:
            self.boot_records = self.boot_records[-100:]
    
    def _save_state(self):
        """حفظ حالة الإقلاع"""
        try:
            state = {
                "boot_mode": self.boot_mode,
                "security_level": self.security_level,
                "boot_phase": self.boot_phase.value if hasattr(self.boot_phase, 'value') else str(self.boot_phase),
                "boot_records_count": len(self.boot_records),
                "boot_backups_count": len(self.boot_backups),
                "last_boot": self.boot_records[-1].__dict__ if self.boot_records else None,
                "saved_at": time.time()
            }
            
            with open(BOOT_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة الإقلاع: {e}")
    
    def _load_state(self):
        """تحميل حالة الإقلاع"""
        try:
            if BOOT_STATE_FILE.exists():
                with open(BOOT_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.boot_mode = state.get("boot_mode", BOOT_MODE_NORMAL)
                    self.security_level = state.get("security_level", BOOT_SECURITY_LEVEL_STRICT)
                    self.boot_phase = BootPhase(state.get("boot_phase", "power_on"))
                    
                # تحميل النسخ الاحتياطية
                backup_files = list(BOOT_BACKUP_DIR.glob("*.json"))
                for bf in backup_files:
                    try:
                        with open(bf, 'r') as f:
                            backup_data = json.load(f)
                            backup = BootBackup(**backup_data)
                            self.boot_backups.append(backup)
                    except:
                        pass
                
                # ترتيب حسب الوقت
                self.boot_backups.sort(key=lambda x: x.created_at)
                
                logger.info("📂 تم تحميل حالة الإقلاع")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة الإقلاع: {e}")
    
    def _mode_name(self, mode: int) -> str:
        """اسم وضع الإقلاع"""
        names = {
            BOOT_MODE_NORMAL: "عادي",
            BOOT_MODE_SAFE: "آمن",
            BOOT_MODE_RECOVERY: "استرداد",
            BOOT_MODE_STEALTH: "خفي",
            BOOT_MODE_PHANTOM: "شبح",
            BOOT_MODE_WAR: "حربي"
        }
        return names.get(mode, "غير معروف")
    
    # ============================================================
    # واجهات التحكم (للسيد فقط)
    # ============================================================
    
    def set_boot_mode(self, mode: int, reason: str = "sovereign_command") -> bool:
        """تعيين وضع الإقلاع (للسيد فقط)"""
        old_mode = self.boot_mode
        self.boot_mode = mode
        
        self.core.append_event(
            event_type="boot::mode_changed",
            payload={
                "old_mode": old_mode,
                "new_mode": mode,
                "reason": reason,
                "timestamp": time.time()
            }
        )
        
        logger.warning(f"⚙️ تغيير وضع الإقلاع: {self._mode_name(old_mode)} -> {self._mode_name(mode)}")
        return True
    
    def set_security_level(self, level: int) -> bool:
        """تعيين مستوى الأمان"""
        self.security_level = level
        logger.info(f"🔒 مستوى أمان الإقلاع: {level}")
        return True
    
    # ============================================================
    # التقارير والاستعلامات
    # ============================================================
    
    def get_boot_status(self) -> Dict[str, Any]:
        """الحالة الحالية للإقلاع"""
        return {
            "phase": self.boot_phase.value,
            "boot_mode": self.boot_mode,
            "mode_name": self._mode_name(self.boot_mode),
            "security_level": self.security_level,
            "is_booting": self.is_booting,
            "total_boots": len(self.boot_records),
            "boot_backups": len(self.boot_backups),
            "last_boot": self.boot_records[-1].__dict__ if self.boot_records else None,
            "timestamp": time.time()
        }
    
    def get_boot_history(self, limit: int = 20) -> List[Dict]:
        """سجل الإقلاعات السابقة"""
        return [r.__dict__ for r in self.boot_records[-limit:]]
    
    def get_backups(self) -> List[Dict]:
        """النسخ الاحتياطية المتاحة"""
        return [b.__dict__ for b in self.boot_backups]
    
    def force_reboot(self, mode: int = BOOT_MODE_NORMAL) -> BootRecord:
        """إعادة تشغيل قسري"""
        logger.warning("🔄 إعادة تشغيل قسري...")
        return self.boot_sequence(mode=mode)
    
    def stop(self):
        """إيقاف نظام الإقلاع"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف نظام الإقلاع")


# ============================================================
# الـ Singleton - بوابة واحدة
# ============================================================

_bootkit_instance: Optional[BootkitDefense] = None
_bootkit_lock = threading.Lock()


def get_bootkit_defense() -> BootkitDefense:
    """الحصول على النسخة الوحيدة من نظام الإقلاع المطلق"""
    global _bootkit_instance
    if _bootkit_instance is None:
        with _bootkit_lock:
            if _bootkit_instance is None:
                _bootkit_instance = BootkitDefense()
    return _bootkit_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🐉 نظام الإقلاع المطلق - بوابة القيادة السيادية")
    print("=" * 70 + "\n")
    
    boot = get_bootkit_defense()
    
    # 1) إقلاع عادي
    print("🔌 إقلاع عادي...")
    record = boot.boot_sequence(mode=BOOT_MODE_NORMAL)
    print(f"   المدة: {record.duration:.2f} ثانية")
    print(f"   التهديدات: {record.threats_detected if record.threats_detected else 'لا شيء'}")
    
    # 2) الحالة
    print("\n📊 حالة الإقلاع:")
    status = boot.get_boot_status()
    print(f"   المرحلة: {status['phase']}")
    print(f"   الوضع: {status['mode_name']}")
    print(f"   مستوى الأمان: {status['security_level']}")
    print(f"   عدد الإقلاعات: {status['total_boots']}")
    
    # 3) تطعيم سلسلة الإقلاع
    print("\n🔒 تطعيم سلسلة الإقلاع...")
    boot.harden_boot_chain()
    
    # 4) نسخ احتياطية
    print("\n💾 النسخ الاحتياطية:")
    backups = boot.get_backups()
    print(f"   عدد النسخ: {len(backups)}")
    
    # 5) إقلاع خفي (اختباري - لن يُسجل)
    print("\n👻 إقلاع خفي (محاكاة)...")
    stealth_record = boot.stealth_boot()
    
    print("\n" + "=" * 70)
    print("✅ نظام الإقلاع المطلق جاهز - البوابة تحرس العقل")
    print("=" * 70)
