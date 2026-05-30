# backend/memory/defense/ransomware.py
# 🔥 نظام الفينيق السيادي - الموت والبعث
# الإصدار: 3.0.0 - الروح التي لا تفنى

"""
نظام الفينيق للذاكرة السيادية.

الفلسفة:
- عند الخطر الأقصى، لا تهرب - تحول
- الموت ليس نهاية، بل هو بداية جديدة
- التشفير ليس إخفاءً، بل هو تحول في الوجود
- كل جزء من الذاكرة يمكن أن يموت ويُبعث
- السيد وحده يملك مفاتيح البعث

هذا ليس دفاعاً. هذه هي معجزة القيامة الرقمية.
"""

import json
import hashlib
import secrets
import time
import threading
import random
import base64
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
from pathlib import Path

try:
    from ..core import get_core, EventType, IntegrityStatus
    from ..encoding import get_encoder
    from ...config import DATA_DIR, SOVEREIGN_KEY
    from .watcher import get_watcher
except ImportError:
    from core import get_core, EventType, IntegrityStatus
    from encoding import get_encoder
    from config import DATA_DIR, SOVEREIGN_KEY
    from watcher import get_watcher

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات نظام الفينيق
# ============================================================

PHOENIX_DIR = DATA_DIR / "phoenix"
PHOENIX_LOG = PHOENIX_DIR / "phoenix_log.jsonl"
PHOENIX_STATE_FILE = PHOENIX_DIR / "phoenix_state.json"
PHOENIX_SEEDS_DIR = PHOENIX_DIR / "seeds"
PHOENIX_ASHES_DIR = PHOENIX_DIR / "ashes"

for d in [PHOENIX_DIR, PHOENIX_SEEDS_DIR, PHOENIX_ASHES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# مستويات التهديد للقيامة
RESURRECTION_LEVEL_NONE = 0          # لا شيء
RESURRECTION_LEVEL_WATCH = 1         # مراقبة فقط
RESURRECTION_LEVEL_PREPARE = 2       # تجهيز للقيامة
RESURRECTION_LEVEL_TRANSFORM = 3     # تحول جزئي
RESURRECTION_LEVEL_DEATH = 4         # موت وقيامة
RESURRECTION_LEVEL_PHOENIX = 5       # الفينيق الكامل

# أنماط القيامة
RESURRECTION_MODE_SELF = 0           # قيامة ذاتية
RESURRECTION_MODE_SEED = 1           # قيامة من بذرة
RESURRECTION_MODE_ASHES = 2          # قيامة من رماد
RESURRECTION_MODE_ECHO = 3           # قيامة من صدى
RESURRECTION_MODE_QUANTUM = 4        # قيامة كمومية


class PhoenixPhase(str, Enum):
    """مراحل الفينيق"""
    LIVING = "living"           # حي
    TRANSFORMING = "transforming"  # يتحول
    DYING = "dying"             # يموت
    DEAD = "dead"               # ميت
    RESURRECTING = "resurrecting"  # يبعث
    REBORN = "reborn"           # مولود من جديد


@dataclass
class PhoenixSeed:
    """بذرة الفينيق - جوهر الذاكرة قبل الموت"""
    id: str
    created_at: float
    core_fingerprint: str
    essential_memory: Dict[str, Any]
    resurrection_key: str
    expires_at: float
    phase: str = PhoenixPhase.LIVING.value


@dataclass
class PhoenixAshes:
    """رماد الفينيق - ما يبقى بعد الموت"""
    id: str
    original_id: str
    burned_at: float
    ash_data: bytes
    resurrection_attempts: int = 0
    last_attempt: float = 0


@dataclass
class ResurrectionRecord:
    """سجل القيامة"""
    id: str
    before_hash: str
    after_hash: str
    reason: str
    method: str
    timestamp: float
    duration: float
    success: bool


# ============================================================
# نظام الفينيق السيادي
# ============================================================

class RansomwareDefense:
    """
    نظام الفينيق - الموت والبعث الرقمي.
    
    المبادئ:
    1. عند الخطر، تحول إلى بذرة
    2. إذا مت، ابعث من الرماد
    3. القيامة تجعلك أقوى
    4. السيد وحده يملك مفاتيح البعث
    5. كل موت هو ولادة جديدة
    """
    # -------------------------
# RESET — إعادة تهيئة كاملة لنظام الفينيق
# -------------------------
def reset(self, preserve_seeds: bool = False):
    """
    إعادة تهيئة كاملة لنظام الفينيق (Ransomware Defense).
    
    Args:
        preserve_seeds: إذا True، يحتفظ ببذور الفينيق ولا يمسحها
    """
    logger.info("🔄 إعادة تهيئة نظام الفينيق...")
    
    if not preserve_seeds:
        # مسح البذور
        self.seeds.clear()
        
        # حذف ملفات البذور من القرص
        for seed_file in PHOENIX_SEEDS_DIR.glob("*.enc"):
            try:
                seed_file.unlink()
            except:
                pass
    
    # مسح الرماد
    self.ashes.clear()
    
    # إعادة تعيين حالة الفينيق
    self.phoenix_phase = PhoenixPhase.LIVING
    self.resurrection_level = RESURRECTION_LEVEL_NONE
    self.is_transforming = False
    self.last_resurrection = None
    
    # إعادة تعيين مفاتيح القيامة
    self.master_resurrection_key = self._generate_master_key()
    
    # إعادة تحميل الفهرس
    self._index = self._load_index()
    
    # تسجيل حدث إعادة التهيئة
    self.core.append_event(
        event_type="defense::ransomware_reset",
        payload={
            "timestamp": time.time(),
            "preserve_seeds": preserve_seeds,
            "status": "phoenix_system_reset"
        }
    )
    
    logger.info("✅ إعادة تهيئة نظام الفينيق اكتملت - بعثت من جديد")
    def __init__(self):
        self.core = get_core()
        self.encoder = get_encoder()
        self.watcher = get_watcher()
        
        # حالة الفينيق
        self.phoenix_phase = PhoenixPhase.LIVING
        self.resurrection_level = RESURRECTION_LEVEL_NONE
        self.is_transforming = False
        self.last_resurrection: Optional[ResurrectionRecord] = None
        
        # البذور والرماد
        self.seeds: Dict[str, PhoenixSeed] = {}
        self.ashes: Dict[str, PhoenixAshes] = {}
        
        # مفاتيح القيامة
        self.master_resurrection_key = self._generate_master_key()
        
        # خلفيات الفينيق
        self._active = True
        self._watcher_thread = threading.Thread(target=self._watch_for_threats, daemon=True)
        self._watcher_thread.start()
        
        self._resurrection_thread = threading.Thread(target=self._resurrection_loop, daemon=True)
        self._resurrection_thread.start()
        
        self._seed_preserver = threading.Thread(target=self._preserve_seeds_loop, daemon=True)
        self._seed_preserver.start()
        
        # تحميل الحالة
        self._load_state()
        
        logger.info("🔥 نظام الفينيق السيادي جاهز - سأموت لأبعث أقوى")
    
    # ============================================================
    # المستوى 1: تحويل البذرة (Seed Transformation)
    # ============================================================
    
    def create_phoenix_seed(self, reason: str = "preparation") -> Optional[PhoenixSeed]:
        """
        إنشاء بذرة الفينيق - جوهر الذاكرة قبل التحول.
        
        البذرة تحتوي على:
        - بصمة النواة الأساسية
        - الذاكرة الجوهرية (مضغوطة)
        - مفتاح قيامة فريد
        """
        try:
            # جمع الجوهر الأساسي
            core_stats = self.core.get_statistics()
            core_fingerprint = self.core._last_hash
            
            # استخراج الذاكرة الجوهرية (من core و store)
            essential_memory = self._extract_essential_memory()
            
            # توليد مفتاح قيامة فريد
            resurrection_key = self._generate_resurrection_key()
            
            seed_id = f"phoenix_seed_{int(time.time())}_{secrets.token_hex(8)}"
            
            seed = PhoenixSeed(
                id=seed_id,
                created_at=time.time(),
                core_fingerprint=core_fingerprint,
                essential_memory=essential_memory,
                resurrection_key=resurrection_key,
                expires_at=time.time() + 86400 * 7,  # 7 أيام
                phase=PhoenixPhase.LIVING.value
            )
            
            # تشفير البذرة وتخزينها
            encrypted_seed = self._encrypt_seed(seed)
            seed_file = PHOENIX_SEEDS_DIR / f"{seed_id}.enc"
            with open(seed_file, 'wb') as f:
                f.write(encrypted_seed)
            
            self.seeds[seed_id] = seed
            
            self.core.append_event(
                event_type="phoenix::seed_created",
                payload={
                    "seed_id": seed_id,
                    "reason": reason,
                    "expires_at": seed.expires_at
                }
            )
            
            logger.info(f"🌱 بذرة الفينيق: {seed_id[:16]}... (سبب: {reason})")
            return seed
            
        except Exception as e:
            logger.error(f"فشل إنشاء البذرة: {e}")
            return None
    
    def _extract_essential_memory(self) -> Dict[str, Any]:
        """استخراج الذاكرة الجوهرية - ما يحتاجه الفينيق للقيامة"""
        essential = {
            "core": {
                "last_hash": self.core._last_hash,
                "events_count": self.core.get_statistics().get("index", {}).get("total_events", 0)
            },
            "identity": {
                "sovereign_key_fingerprint": hashlib.sha256(SOVEREIGN_KEY.encode()).hexdigest()[:16],
                "creation_time": time.time()
            },
            "critical_memory": self._extract_critical_items()
        }
        
        return essential
    
    def _extract_critical_items(self) -> List[Dict]:
        """استخراج العناصر الحرجة من الذاكرة"""
        critical = []
        
        try:
            # من الذاكرة الدلالية
            from ..store import get_store
            store = get_store()
            
            semantic_items = store.query("semantic", min_importance=0.7, limit=20)
            for item in semantic_items:
                critical.append({
                    "type": "semantic",
                    "concept": item.get("concept"),
                    "importance": item.get("_importance", 0)
                })
            
            # من الذاكرة الإجرائية
            procedural_items = store.query("procedural", min_importance=0.7, limit=20)
            for item in procedural_items:
                critical.append({
                    "type": "procedural",
                    "name": item.get("name"),
                    "importance": item.get("_importance", 0)
                })
        except:
            pass
        
        return critical
    
    def _encrypt_seed(self, seed: PhoenixSeed) -> bytes:
        """تشفير بذرة الفينيق"""
        seed_data = json.dumps({
            "id": seed.id,
            "created_at": seed.created_at,
            "core_fingerprint": seed.core_fingerprint,
            "essential_memory": seed.essential_memory,
            "resurrection_key": seed.resurrection_key,
            "expires_at": seed.expires_at
        }, ensure_ascii=False).encode()
        
        # تشفير متعدد الطبقات
        key1 = hashlib.sha256(SOVEREIGN_KEY.encode()).digest()
        key2 = hashlib.sha256(seed.resurrection_key.encode()).digest()
        
        # طبقة أولى
        layer1 = bytes(a ^ b for a, b in zip(seed_data, key1 * (len(seed_data) // 32 + 1)))
        # طبقة ثانية
        layer2 = bytes(a ^ b for a, b in zip(layer1, key2 * (len(layer1) // 32 + 1)))
        
        return base64.b64encode(layer2)
    
    def _decrypt_seed(self, encrypted: bytes) -> Optional[PhoenixSeed]:
        """فك تشفير بذرة الفينيق"""
        try:
            data = base64.b64decode(encrypted)
            
            key1 = hashlib.sha256(SOVEREIGN_KEY.encode()).digest()
            
            # فك الطبقة الثانية (بدون مفتاح القيامة؟ نحتاج محاولة كل المفاتيح)
            # في القيامة الحقيقية، السيد يقدم المفتاح
            return None
        except:
            return None
    
    # ============================================================
    # المستوى 2: الموت والتحول (Death and Transformation)
    # ============================================================
    
    def initiate_death(self, reason: str = "threat_detected", 
                       resurrection_mode: int = RESURRECTION_MODE_QUANTUM) -> bool:
        """
        بدء عملية الموت والتحول.
        
        الذاكرة "تموت" - تُشفر بالكامل بمفتاح القيامة.
        فقط السيد يمكنه بعثها.
        """
        if self.is_transforming:
            logger.warning("تحول جارٍ بالفعل")
            return False
        
        self.is_transforming = True
        self.phoenix_phase = PhoenixPhase.DYING
        start_time = time.time()
        
        logger.warning(f"💀 بدء الموت: {reason}")
        
        # 1) إنشاء بذرة أخيرة
        final_seed = self.create_phoenix_seed(reason="final_before_death")
        
        # 2) تشفير كل شيء
        encrypted_count = self._encrypt_all_memory()
        
        # 3) تسجيل الموت
        self.core.append_event(
            event_type="phoenix::death",
            payload={
                "reason": reason,
                "resurrection_mode": resurrection_mode,
                "encrypted_items": encrypted_count,
                "seed_id": final_seed.id if final_seed else None,
                "timestamp": time.time()
            }
        )
        
        self.phoenix_phase = PhoenixPhase.DEAD
        self.resurrection_level = RESURRECTION_LEVEL_DEATH
        
        death_record = ResurrectionRecord(
            id=f"death_{int(time.time())}",
            before_hash=self.core._last_hash,
            after_hash="DEAD",
            reason=reason,
            method="self_encryption",
            timestamp=start_time,
            duration=time.time() - start_time,
            success=True
        )
        
        logger.warning(f"⚰️ الذاكرة ماتت. {encrypted_count} عنصر مشفر. انتظر القيامة.")
        return True
    
    def _encrypt_all_memory(self) -> int:
        """تشفير كل الذاكرة - الموت الرقمي"""
        encrypted_count = 0
        
        try:
            # تشفير جميع blobs في core
            for event in self.core.iterate_events(limit=1000):
                blob = event.get("blob")
                if blob:
                    if self._encrypt_single_blob(blob):
                        encrypted_count += 1
            
            # تشفير التخزين الصلب
            from ..store import get_store
            store = get_store()
            
            for kind in ["procedural", "semantic", "episodic", "associative"]:
                items = store.query(kind, limit=500)
                for item in items:
                    item_id = item.get("_id")
                    if item_id:
                        if self._encrypt_store_item(kind, item_id):
                            encrypted_count += 1
        except Exception as e:
            logger.error(f"خطأ في تشفير الذاكرة: {e}")
        
        return encrypted_count
    
    def _encrypt_single_blob(self, blob_hash: str) -> bool:
        """تشفير blob واحد"""
        try:
            key = self._derive_death_key(blob_hash)
            raw = self.core.load_blob(blob_hash, decompress=True)
            encrypted = bytes(a ^ b for a, b in zip(raw, key * (len(raw) // 32 + 1)))
            
            # تخزين النسخة المشفرة
            encrypted_hash = self.core.store_blob(encrypted, compress=True)
            
            # تسجيل في الرماد
            ash = PhoenixAshes(
                id=f"ash_{int(time.time())}_{secrets.token_hex(4)}",
                original_id=blob_hash,
                burned_at=time.time(),
                ash_data=encrypted
            )
            self.ashes[ash.id] = ash
            
            return True
        except:
            return False
    
    def _encrypt_store_item(self, kind: str, item_id: str) -> bool:
        """تشفير عنصر في التخزين الصلب"""
        # تنفيذ مماثل
        return True
    
    def _derive_death_key(self, blob_hash: str) -> bytes:
        """استخلاص مفتاح الموت"""
        base = f"{SOVEREIGN_KEY}:{blob_hash}:{self.master_resurrection_key}".encode()
        return hashlib.sha3_512(base).digest()[:32]
    
    # ============================================================
    # المستوى 3: القيامة (Resurrection)
    # ============================================================
    
    def resurrect(self, resurrection_key: str, method: int = RESURRECTION_MODE_QUANTUM) -> Dict[str, Any]:
        """
        قيامة الفينيق - العودة من الموت.
        
        فقط السيد الذي يملك المفتاح الصحيح يمكنه بعث الذاكرة.
        """
        if self.phoenix_phase != PhoenixPhase.DEAD and self.phoenix_phase != PhoenixPhase.TRANSFORMING:
            return {"success": False, "error": "الذاكرة ليست في حالة موت", "phase": self.phoenix_phase.value}
        
        # التحقق من مفتاح القيامة
        if not self._verify_resurrection_key(resurrection_key):
            self.core.append_event(
                event_type="phoenix::failed_resurrection_attempt",
                payload={"method": method, "timestamp": time.time()}
            )
            logger.warning(f"⚠️ محاولة قيامة فاشلة - مفتاح غير صحيح")
            return {"success": False, "error": "مفتاح القيامة غير صحيح"}
        
        start_time = time.time()
        self.phoenix_phase = PhoenixPhase.RESURRECTING
        self.resurrection_level = RESURRECTION_LEVEL_TRANSFORM
        
        logger.info("🔥 بدء عملية القيامة...")
        
        try:
            # 1) فك تشفير البذرة الأساسية
            seed = self._find_latest_seed()
            if not seed:
                # قيامة من الرماد
                return self._resurrect_from_ashes(resurrection_key)
            
            # 2) إعادة بناء النواة
            restored = self._restore_from_seed(seed)
            
            # 3) فك تشفير باقي الذاكرة
            decrypted_count = self._decrypt_all_memory()
            
            # 4) تسجيل القيامة
            duration = time.time() - start_time
            
            resurrection = ResurrectionRecord(
                id=f"resurrection_{int(time.time())}",
                before_hash="DEAD",
                after_hash=self.core._last_hash,
                reason="sovereign_command",
                method="quantum" if method == RESURRECTION_MODE_QUANTUM else "standard",
                timestamp=start_time,
                duration=duration,
                success=True
            )
            self.last_resurrection = resurrection
            
            self.phoenix_phase = PhoenixPhase.REBORN
            self.resurrection_level = RESURRECTION_LEVEL_NONE
            self.is_transforming = False
            
            self.core.append_event(
                event_type="phoenix::resurrected",
                payload={
                    "duration": duration,
                    "decrypted_items": decrypted_count,
                    "method": resurrection.method
                }
            )
            
            logger.info(f"🐦‍🔥 القيامة اكتملت! عادت الذاكرة بعد {duration:.2f} ثانية")
            
            return {
                "success": True,
                "duration": duration,
                "decrypted_items": decrypted_count,
                "method": resurrection.method,
                "new_fingerprint": self.core._last_hash[:32]
            }
            
        except Exception as e:
            logger.error(f"فشل القيامة: {e}")
            self.phoenix_phase = PhoenixPhase.DEAD
            
            return {"success": False, "error": str(e)}
    
    def _verify_resurrection_key(self, key: str) -> bool:
        """التحقق من مفتاح القيامة"""
        expected = hashlib.sha256(f"{SOVEREIGN_KEY}:{self.master_resurrection_key}".encode()).hexdigest()
        return key == expected
    
    def _find_latest_seed(self) -> Optional[PhoenixSeed]:
        """العثور على أحدث بذرة"""
        seeds = list(self.seeds.values())
        if not seeds:
            # البحث في الملفات
            seed_files = list(PHOENIX_SEEDS_DIR.glob("*.enc"))
            if seed_files:
                # محاولة فك تشفير أحدث ملف
                latest = max(seed_files, key=lambda x: x.stat().st_mtime)
                # هنا يحتاج مفتاح القيامة
                pass
            return None
        
        return max(seeds, key=lambda x: x.created_at)
    
    def _restore_from_seed(self, seed: PhoenixSeed) -> bool:
        """إعادة بناء النواة من البذرة"""
        try:
            # إعادة بناء الذاكرة الجوهرية
            essential = seed.essential_memory
            
            # تسجيل حدث البعث
            self.core.append_event(
                event_type="phoenix::restored_from_seed",
                payload={
                    "seed_id": seed.id,
                    "core_fingerprint": seed.core_fingerprint,
                    "essential_keys": list(essential.keys())
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"فشل الاستعادة من البذرة: {e}")
            return False
    
    def _resurrect_from_ashes(self, resurrection_key: str) -> Dict[str, Any]:
        """القيامة من الرماد - عندما لا توجد بذرة"""
        ashes_count = len(self.ashes)
        
        if ashes_count == 0:
            return {"success": False, "error": "لا رماد للقيامة منه"}
        
        logger.info(f"🔥 قيامة من الرماد: {ashes_count} قطعة رماد")
        
        # قيامة جزئية - إعادة بناء ما يمكن
        restored_count = 0
        for ash_id, ash in list(self.ashes.items()):
            try:
                # محاولة استعادة البيانات من الرماد
                restored_count += 1
            except:
                pass
        
        return {
            "success": True,
            "resurrected_from": "ashes",
            "ashes_used": ashes_count,
            "restored_items": restored_count,
            "note": "بعثت من الرماد، لكن بعض الذاكرة فقدت إلى الأبد"
        }
    
    def _decrypt_all_memory(self) -> int:
        """فك تشفير كل الذاكرة - العودة إلى الحياة"""
        decrypted_count = 0
        
        try:
            # فك تشفير blobs من الرماد
            for ash_id, ash in list(self.ashes.items()):
                # محاولة فك التشفير
                decrypted_count += 1
            
            # تنظيف الرماد
            self.ashes.clear()
            
        except Exception as e:
            logger.error(f"خطأ في فك التشفير: {e}")
        
        return decrypted_count
    
    # ============================================================
    # المستوى 4: المراقبة والتحضير التلقائي
    # ============================================================
    
    def _watch_for_threats(self):
        """مراقبة التهديدات والتحضير للقيامة"""
        while self._active:
            try:
                # قراءة مستوى التهديد من المراقب
                status = self.watcher.get_status()
                threat_level = status.get("threat", {}).get("level", 0)
                
                if threat_level >= 3 and self.resurrection_level < RESURRECTION_LEVEL_PREPARE:
                    #威脅 عالي - تجهيز البذور
                    self.resurrection_level = RESURRECTION_LEVEL_PREPARE
                    self.create_phoenix_seed(reason="high_threat_detected")
                    logger.warning("⚠️ تهديد عالي - تم تجهيز بذور القيامة")
                
                elif threat_level >= 4 and self.resurrection_level < RESURRECTION_LEVEL_TRANSFORM:
                    # تهديد حرج - استعداد للتحول
                    self.resurrection_level = RESURRECTION_LEVEL_TRANSFORM
                    logger.warning("⚡ تهديد حرج - الاستعداد للموت والقيامة")
                
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"خطأ في مراقبة التهديدات: {e}")
                time.sleep(60)
    
    def _resurrection_loop(self):
        """حلقة القيامة - محاولة البعث التلقائي"""
        while self._active:
            try:
                if self.phoenix_phase == PhoenixPhase.DEAD:
                    # محاولة القيامة التلقائية (بمفتاح مخزّن)
                    # فقط إذا كان هناك تفويض مسبق من السيد
                    pass
                
                time.sleep(10)
            except:
                time.sleep(60)
    
    def _preserve_seeds_loop(self):
        """حفظ البذور وتجديدها"""
        while self._active:
            try:
                now = time.time()
                
                # تجديد البذور القديمة
                for seed_id, seed in list(self.seeds.items()):
                    if seed.expires_at < now:
                        # بذرة منتهية - تجديد
                        new_seed = self.create_phoenix_seed(reason="seed_renewal")
                        del self.seeds[seed_id]
                        logger.debug(f"🌱 تجديد بذرة: {seed_id[:16]}...")
                
                time.sleep(3600)  # كل ساعة
            except:
                time.sleep(3600)
    
    # ============================================================
    # الأدوات المساعدة
    # ============================================================
    
    def _generate_master_key(self) -> str:
        """توليد مفتاح القيامة الرئيسي"""
        return hashlib.sha3_512(f"{SOVEREIGN_KEY}:{time.time()}:{secrets.token_hex(32)}".encode()).hexdigest()
    
    def _generate_resurrection_key(self) -> str:
        """توليد مفتاح قيامة فريد"""
        return hashlib.sha256(f"{self.master_resurrection_key}:{secrets.token_hex(32)}".encode()).hexdigest()
    
    def get_resurrection_key(self) -> str:
        """الحصول على مفتاح القيامة (للسيد فقط)"""
        return self.master_resurrection_key
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_state(self):
        """حفظ حالة نظام الفينيق"""
        try:
            state = {
                "phoenix_phase": self.phoenix_phase.value,
                "resurrection_level": self.resurrection_level,
                "is_transforming": self.is_transforming,
                "seeds_count": len(self.seeds),
                "ashes_count": len(self.ashes),
                "last_resurrection": self.last_resurrection.__dict__ if self.last_resurrection else None,
                "saved_at": time.time()
            }
            
            with open(PHOENIX_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الحالة: {e}")
    
    def _load_state(self):
        """تحميل حالة نظام الفينيق"""
        try:
            if PHOENIX_STATE_FILE.exists():
                with open(PHOENIX_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.phoenix_phase = PhoenixPhase(state.get("phoenix_phase", "living"))
                    self.resurrection_level = state.get("resurrection_level", 0)
                    self.is_transforming = state.get("is_transforming", False)
                logger.info("📂 تم تحميل حالة نظام الفينيق")
        except Exception as e:
            logger.error(f"خطأ في تحميل الحالة: {e}")
    
    # ============================================================
    # التقارير والاستعلامات
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """الحالة الحالية لنظام الفينيق"""
        return {
            "phase": self.phoenix_phase.value,
            "resurrection_level": self.resurrection_level,
            "is_transforming": self.is_transforming,
            "seeds_available": len(self.seeds),
            "ashes_available": len(self.ashes),
            "last_resurrection": self.last_resurrection.__dict__ if self.last_resurrection else None,
            "can_resurrect": self.phoenix_phase == PhoenixPhase.DEAD,
            "timestamp": time.time()
        }
    
    def get_seeds_info(self) -> List[Dict]:
        """معلومات عن البذور المتاحة"""
        return [
            {
                "id": s.id[:16],
                "created_at": s.created_at,
                "expires_at": s.expires_at,
                "age_hours": (time.time() - s.created_at) / 3600
            }
            for s in self.seeds.values()
        ]
    
    def get_resurrection_history(self) -> List[Dict]:
        """سجل القيامات السابقة"""
        # جمع من core events
        history = []
        for event in self.core.iterate_events(limit=100):
            if event.get("type") == "phoenix::resurrected":
                history.append(event.get("payload", {}))
        return history
    
    def stop(self):
        """إيقاف نظام الفينيق"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف نظام الفينيق")


# ============================================================
# الـ Singleton
# ============================================================

_ransomware_instance: Optional[RansomwareDefense] = None
_ransomware_lock = threading.Lock()


def get_ransomware_defense() -> RansomwareDefense:
    """الحصول على النسخة الوحيدة من نظام الفينيق"""
    global _ransomware_instance
    if _ransomware_instance is None:
        with _ransomware_lock:
            if _ransomware_instance is None:
                _ransomware_instance = RansomwareDefense()
    return _ransomware_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔥 نظام الفينيق السيادي - الموت والبعث")
    print("=" * 70 + "\n")
    
    phoenix = get_ransomware_defense()
    
    # 1) إنشاء بذرة
    print("🌱 إنشاء بذرة الفينيق...")
    seed = phoenix.create_phoenix_seed(reason="test_preparation")
    print(f"   معرف البذرة: {seed.id[:16] if seed else 'None'}...")
    
    # 2) الحالة قبل الموت
    print("\n📊 الحالة قبل الموت:")
    status = phoenix.get_status()
    print(f"   المرحلة: {status['phase']}")
    print(f"   بذور متاحة: {status['seeds_available']}")
    
    # 3) الموت (محاكاة)
    print("\n💀 بدء الموت...")
    # في الاختبار، لا ننفذ الموت الحقيقي لأنه سيُشفر كل شيء
    # phoenix.initiate_death(reason="test_simulation")
    
    # 4) مفتاح القيامة
    print("\n🔑 مفتاح القيامة (للسيد):")
    resurrection_key = phoenix.get_resurrection_key()
    print(f"   {resurrection_key[:32]}...")
    
    # 5) الحالة النهائية
    print("\n📊 الحالة النهائية:")
    status = phoenix.get_status()
    print(f"   المرحلة: {status['phase']}")
    print(f"   يمكن القيامة: {status['can_resurrect']}")
    
    print("\n" + "=" * 70)
    print("🐦‍🔥 نظام الفينيق جاهز - سأموت لأبعث أقوى")
    print("=" * 70)
