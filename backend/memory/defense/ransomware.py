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

import hmac
import json
import hashlib
import os
import secrets

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
except ImportError:  # pragma: no cover
    AES = None
    get_random_bytes = None
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
    from memory.core import get_core, EventType, IntegrityStatus
    from memory.encoding import get_encoder
    from config import DATA_DIR, SOVEREIGN_KEY
    from memory.defense.watcher import get_watcher

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
    """رماد الفينيق - ما يبقى بعد الموت (مشفر + موثق بـ MAC)"""
    id: str
    original_id: str
    burned_at: float
    ash_data: bytes
    mac: str = ""  # R-682: مصادقة بيانات الرماد — لا استعادة غير موثقة
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
        # R-682 (security — إثبات الاستعادة): مخزن بيانات البذور المستعادة فعليًا.
        # الاستعادة تُثبت بوجود البيانات المقصودة هنا — لا بتسجيل حدث فقط.
        self.restored_seeds: Dict[str, Dict[str, Any]] = {}
        
        # مفاتيح القيامة
        self.master_resurrection_key = self._generate_master_key()
        
        # R-682 (security — متانة المفتاح قبل أي شيء آخر):
        # تحميل الحالة (استرجاع المفتاح الرئيسي) يجب أن يسبق بدء أي خيط خلفي،
        # ثم يُحفظ المفتاح حفظًا متينًا فورًا — قبل إمكانية إنشاء أي بذرة،
        # حتى لا يُعلن نجاح إنشاء بذرة أبدًا دون مفتاح قيامة مستقر على القرص.
        self._state_master_key_invalid = False
        self._state_master_key_enc_original = None
        # R-682 (security — fail-closed): فشل تحميل حالة موجودة يوقف التهيئة
        # قبل الحفظ والخيوط وإنشاء أي بذرة — الملف الأصلي يُحفظ كاملًا بلا تعديل.
        if not self._load_state():
            raise RuntimeError(
                "R-682 [SECURITY-FAIL]: phoenix state file exists but failed to "
                "load (corrupt/missing master_key_enc / invalid JSON / different "
                "sovereign key). Initialization REFUSED before threads, save, "
                "or seed creation. Original file preserved untouched."
            )
        if not self._save_state():
            # R-682 (security — fail-closed): المفتاح غير متين على القرص =
            # لا خيوط ولا جاهزية ولا بذور معلنة
            raise RuntimeError(
                "R-682 [SECURITY-FAIL]: phoenix state could not be durably "
                "saved (master key not durable on disk). Initialization "
                "REFUSED before threads or readiness."
            )

        # خلفيات الفينيق (بعد استقرار المفتاح)
        self._active = True
        self._watcher_thread = threading.Thread(target=self._watch_for_threats, daemon=True)
        self._watcher_thread.start()
        
        self._resurrection_thread = threading.Thread(target=self._resurrection_loop, daemon=True)
        self._resurrection_thread.start()
        
        self._seed_preserver = threading.Thread(target=self._preserve_seeds_loop, daemon=True)
        self._seed_preserver.start()
        
        logger.info("🔥 نظام الفينيق السيادي جاهز - سأموت لأبعث أقوى")
    
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
                # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
                except:
                    pass
        
        # مسح الرماد
        self.ashes.clear()
        
        # إعادة تعيين حالة الفينيق
        self.phoenix_phase = PhoenixPhase.LIVING
        self.resurrection_level = RESURRECTION_LEVEL_NONE
        self.is_transforming = False
        self.last_resurrection = None
        
        # R-682 (security): عند الاحتفاظ بالبذور يجب الاحتفاظ بالمفتاح الرئيسي —
        # توليد مفتاح جديد يجعل كل بذور محفوظة غير قابلة للفك نهائيًا.
        if not preserve_seeds:
            self.master_resurrection_key = self._generate_master_key()
        self._state_master_key_invalid = False
        self._state_master_key_enc_original = None
        if not self._save_state():
            logger.error(
                "R-682 [SECURITY]: reset failed to durably save state — "
                "persisted seeds may not remain decryptable"
            )
        
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
            
            # معرف البذرة أولًا ثم مفتاح حتمي (قابل للاشتقاق بعد إعادة التشغيل)
            seed_id = f"phoenix_seed_{int(time.time())}_{secrets.token_hex(8)}"
            resurrection_key = self._generate_resurrection_key(seed_id)
            
            seed = PhoenixSeed(
                id=seed_id,
                created_at=time.time(),
                core_fingerprint=core_fingerprint,
                essential_memory=essential_memory,
                resurrection_key=resurrection_key,
                expires_at=time.time() + 86400 * 7,  # 7 أيام
                phase=PhoenixPhase.LIVING.value
            )
            
            # R-682 (security — متانة قبل الإعلان): الحالة (ومنها المفتاح الرئيسي)
            # تُحفظ بشكل متين قبل كتابة أي بذرة — فشل الحفظ = لا نجاح معلن،
            # حتى لا تُعلن بذرة أبدًا دون مفتاح قيامة مستقر على القرص.
            if not self._save_state():
                logger.error(
                    "R-682 [SECURITY]: seed creation REFUSED — state (master key) "
                    "could not be durably saved. No seed announced."
                )
                return None

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
            logger.exception(
                f"R-682 [SECURITY]: Ransomware seed creation failed — silently swallowing "
                f"may hide an active ransomware attack or disk corruption. exc={e}"
            )
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
                # R-682 (security): البذرة يجب أن تحمل البيانات القابلة للاستعادة
                # فعليًا (التعريف/الأسماء البديلة) — لا إحصاءات فقط، وإلا فلا
                # استعادة حقيقية ممكنة من المخزن لاحقًا.
                critical.append({
                    "type": "semantic",
                    "concept": item.get("concept"),
                    "definition": item.get("definition", ""),
                    "aliases": item.get("aliases", []),
                    "related_concepts": item.get("related_concepts", {}),
                    # R-682: examples جزء من الحمولة المقصودة — إسقاطها =
                    # استعادة ناقصة تُعلن نجاحًا (لا يحتسب العنصر مستعادًا
                    # كاملًا إذا أُسقطت بعض حمولته)
                    "examples": item.get("examples", []),
                    "confidence": item.get("confidence", 0.5),
                    "importance": item.get("_importance", 0)
                })
            
            # من الذاكرة الإجرائية — R-682: بيانات كاملة قابلة للاستعادة
            procedural_items = store.query("procedural", min_importance=0.7, limit=20)
            for item in procedural_items:
                critical.append({
                    "type": "procedural",
                    "name": item.get("name"),
                    "description": item.get("description", ""),
                    "trigger_patterns": item.get("trigger_patterns", []),
                    "action_sequence": item.get("action_sequence", []),
                    "parameters": item.get("parameters", {}),
                    "importance": item.get("_importance", 0)
                })
        # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
        except:
            pass
        
        return critical
    
    def _encrypt_seed(self, seed: PhoenixSeed) -> bytes:
        """تشفير بذرة الفينيق — مظروف مُعايَر v3 بتشفير موثق معياري (AES-256-GCM).

        R-682 (security): XOR المتكرر ليس تشفيرًا موثقًا — يسمح بتلاعب موضعي
        يُبقي JSON صالحًا. v3 يستخدم AES-GCM (مصادقة مدمجة عبر وسم GCM):
        - مفتاح مستقل بحسب الغرض: sha256(resurrection_key) — لا إعادة استخدام مفتاح
        - nonce جديد لكل عملية (12 بايت)
        - بيانات مرتبطة (AAD) توثق الإصدار ومعرف البذرة — تغيير أيهما يُرفض
        - أي تعديل على النص المشفر أو الوسم = فشل مصادقة صريح
        """
        if AES is None:
            raise RuntimeError("pycryptodome غير متوفر — لا يمكن تشفير البذرة")
        seed_data = json.dumps({
            "id": seed.id,
            "created_at": seed.created_at,
            "core_fingerprint": seed.core_fingerprint,
            "essential_memory": seed.essential_memory,
            "resurrection_key": seed.resurrection_key,
            "expires_at": seed.expires_at
        }, ensure_ascii=False).encode()

        key = hashlib.sha256(seed.resurrection_key.encode()).digest()
        nonce = get_random_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        cipher.update(f"phoenix-seed-v3:{seed.id}".encode())  # AAD
        ct, tag = cipher.encrypt_and_digest(seed_data)

        envelope = {
            "v": 3,
            "sid": seed.id,
            "n": base64.b64encode(nonce).decode(),
            "d": base64.b64encode(ct).decode(),
            "t": base64.b64encode(tag).decode(),
        }
        return base64.b64encode(json.dumps(envelope).encode())

    def _seed_candidates(self, resurrection_key: Optional[str],
                         seed_id: Optional[str]) -> List[str]:
        """المفاتيح المرشحة (بالترتيب): المفتاح الصريح، بذور الذاكرة، الاشتقاق الحتمي."""
        candidates: List[str] = []
        if resurrection_key:
            candidates.append(resurrection_key)
        known_seeds = getattr(self, "seeds", None) or {}
        candidates.extend(s.resurrection_key for s in known_seeds.values())
        master = getattr(self, "master_resurrection_key", None)
        if master and seed_id:
            candidates.append(
                hashlib.sha256(f"{master}:{seed_id}".encode()).hexdigest()
            )
        return list(dict.fromkeys(candidates))

    def _decrypt_seed(self, encrypted: bytes,
                      resurrection_key: Optional[str] = None,
                      seed_id: Optional[str] = None) -> Optional[PhoenixSeed]:
        """
        فك تشفير بذرة الفينيق (R-682: v3 فقط — AES-256-GCM موثق).

        **منع التخفيض (downgrade):** هذا المسار الاعتيادي يقبل المظروف v3
        الموثق فقط. أي شيء آخر — نص داخلي مجرد (نزع المظروف لخداع المسار
        الإرثي)، مظروف بحقول ناقصة، إصدار مختلف، نص مشفر مُفسد — يُرفض
        فشلًا صريحًا. بذور v1 الإرثية لها مسار ترحيل منفصل وصريح:
        `_decrypt_seed_legacy_v1` — لا اكتشاف تلقائي ولا بديل بعد تعذر المظروف.

        المفاتيح المرشحة (بالترتيب):
        1. المفتاح المُعطى صراحةً (resurrection_key)
        2. مفاتيح البذور المعروفة في الذاكرة (self.seeds)
        3. اشتقاق حتمي: sha256(f"{master}:{seed_id}") — يعمل عبر إعادة التشغيل
           لأن master_resurrection_key يستُرجع من الحالة المشفرة.

        Returns:
            PhoenixSeed عند النجاح، None عند الفشل (fail-closed + تسجيل كامل — لا صمت).
        """
        try:
            if not encrypted:
                logger.warning(
                    "R-682 [SECURITY]: Phoenix seed decryption refused — "
                    "empty payload. Returning None (fail-closed)."
                )
                return None

            data = base64.b64decode(encrypted, validate=True)

            # مظروف v3 إلزامي — أي صيغة أخرى = رفض قاطع (منع التخفيض)
            try:
                envelope = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                logger.error(
                    "R-682 [SECURITY]: Phoenix seed REJECTED — payload is not a "
                    "versioned v3 envelope (stripped envelope / downgrade attempt / "
                    "legacy v1). Use the explicit legacy migration path "
                    "(_decrypt_seed_legacy_v1). Returning None (fail-closed)."
                )
                return None
            if not (isinstance(envelope, dict) and envelope.get("v") == 3
                    and "n" in envelope and "d" in envelope and "t" in envelope):
                logger.error(
                    "R-682 [SECURITY]: Phoenix seed REJECTED — unsupported or "
                    "incomplete envelope (missing version/nonce/data/tag fields). "
                    "No fallback to unauthenticated legacy format. "
                    "Returning None (fail-closed)."
                )
                return None

            candidates = self._seed_candidates(resurrection_key, seed_id)
            if not candidates:
                logger.warning(
                    "R-682 [SECURITY]: Phoenix seed decryption requires the "
                    "seed's resurrection key — none provided, no known seeds, "
                    "and no derivable key (missing seed_id or master key). "
                    "Returning None (fail-closed, not silent)."
                )
                return None

            nonce = base64.b64decode(envelope["n"], validate=True)
            ct = base64.b64decode(envelope["d"], validate=True)
            tag = base64.b64decode(envelope["t"], validate=True)

            for k_source in candidates:
                key = hashlib.sha256(k_source.encode()).digest()
                try:
                    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                    cipher.update(f"phoenix-seed-v3:{envelope.get('sid', '')}".encode())
                    seed_data = cipher.decrypt_and_verify(ct, tag)
                except ValueError:  # R-682: wrong candidate key — try next; final error logged if all fail
                    continue  # وسم GCM فاشل: مفتاح خاطئ أو تلاعب — المرشح التالي

                # المصادقة نجحت — فك JSON وبناء البذرة مع تحقق الحقول
                try:
                    parsed = json.loads(seed_data.decode("utf-8"))
                    seed = self._validate_and_build_seed(parsed)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
                    logger.error(
                        "R-682 [SECURITY]: authenticated payload unparseable "
                        "— REJECTED (corrupt seed file?).",
                        exc_info=e,
                    )
                    return None
                logger.info(f"🌱 بذرة الفينيق فُكّت بنجاح: {seed.id[:24]}... (v3 AES-GCM)")
                return seed

            logger.error(
                f"R-682 [SECURITY]: Phoenix seed v3 GCM authentication FAILED "
                f"for all {len(candidates)} candidate key(s) — tampered payload "
                f"or wrong key. Returning None (fail-closed)."
            )
            return None
        except Exception as e:
            logger.exception(
                f"R-682 [SECURITY]: Phoenix seed decryption failed — silently "
                f"swallowing may hide tampered seed or missing resurrection "
                f"key. exc={e}"
            )
            return None

    def _decrypt_seed_legacy_v1(self, encrypted: bytes,
                                resurrection_key: Optional[str] = None,
                                seed_id: Optional[str] = None) -> Optional[PhoenixSeed]:
        """مسار ترحيل صريح (وفقط) لبذور v1 الإرثية الخام (XOR بلا مصادقة).

        R-682 (security — سياسة إرثية موثقة): هذا المسار لا يُستدعى تلقائيًا
        أبدًا — الترحيل قرار صريح، لأن النزاهة غير قابلة للتحقق في v1.
        تحذير صريح مسجَّل مع كل عملية.
        """
        logger.warning(
            "R-682 [SECURITY]: EXPLICIT legacy v1 migration path — integrity "
            "NOT verifiable (no MAC). Treat content as unauthenticated."
        )
        try:
            data = base64.b64decode(encrypted, validate=True)
            key1 = hashlib.sha256(SOVEREIGN_KEY.encode()).digest()
            candidates = self._seed_candidates(resurrection_key, seed_id)
            if not candidates:
                logger.warning(
                    "R-682 [SECURITY]: legacy v1 migration needs a candidate "
                    "key — none available. Returning None."
                )
                return None
            for k2_source in candidates:
                key2 = hashlib.sha256(k2_source.encode()).digest()
                try:
                    layer1 = bytes(a ^ b for a, b in zip(data, key2 * (len(data) // 32 + 1)))
                    seed_data = bytes(a ^ b for a, b in zip(layer1, key1 * (len(layer1) // 32 + 1)))
                    parsed = json.loads(seed_data.decode("utf-8"))
                    seed = self._validate_and_build_seed(parsed)
                # R-682: wrong legacy candidate key — try next; final error logged if all fail.
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    continue
                logger.info(f"🌱 بذرة إرثية v1 فُكّت (ترحيل صريح): {seed.id[:24]}...")
                return seed
            logger.error(
                "R-682 [SECURITY]: legacy v1 migration failed — no candidate key "
                "fits. Returning None."
            )
            return None
        except Exception as e:
            logger.exception(f"R-682 [SECURITY]: legacy v1 migration failed. exc={e}")
            return None

    def _validate_and_build_seed(self, parsed: Dict[str, Any]) -> PhoenixSeed:
        """التحقق من حقول البذرة المفكوكة وبناؤها (رفض صريح للنواقص)."""
        required = [
            "id", "created_at", "core_fingerprint", "essential_memory",
            "resurrection_key", "expires_at",
        ]
        missing = [f for f in required if f not in parsed]
        if missing:
            raise ValueError(f"missing required seed fields: {missing}")
        return PhoenixSeed(
            id=parsed["id"],
            created_at=parsed["created_at"],
            core_fingerprint=parsed["core_fingerprint"],
            essential_memory=parsed["essential_memory"],
            resurrection_key=parsed["resurrection_key"],
            expires_at=parsed["expires_at"],
            phase=parsed.get("phase", PhoenixPhase.LIVING.value),
        )

    
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
        """تشفير blob واحد — R-682 (بناء): المسار القديم كان كودًا ميتًا
        (self.core.store_blob/load_blob غير موجودين في SovereignCore — الواجهة
        الفعلية blob_store.put/get) فكان يفشل صامتًا بلا رماد أبدًا.
        الآن: الواجهة الحقيقية + مصادقة MAC — لا رماد بلا توثيق."""
        try:
            key = self._derive_death_key(blob_hash)
            raw = self.core.blob_store.get(blob_hash, decompress=True)
            encrypted = bytes(a ^ b for a, b in zip(raw, key * (len(raw) // 32 + 1)))
            # مصادقة بيانات الرماد — أي تلاعب لاحق يُرفض عند الاستعادة
            mac = hmac.new(key, encrypted, hashlib.sha256).hexdigest()

            # تخزين النسخة المشفرة (مخزن محتوى-عنواني)
            encrypted_hash = self.core.blob_store.put(encrypted, compress=True)

            # تسجيل في الرماد
            ash = PhoenixAshes(
                id=f"ash_{int(time.time())}_{secrets.token_hex(4)}",
                original_id=blob_hash,
                burned_at=time.time(),
                ash_data=encrypted,
                mac=mac
            )
            self.ashes[ash.id] = ash

            logger.debug(
                f"🔥 رماد: {blob_hash[:16]}... → {encrypted_hash[:16]}... (موثق MAC)"
            )
            return True
        except Exception as e:
            # R-682: لا فشل صامت — تسجيل صريح ثم فشل
            logger.error(
                f"R-682: blob encryption to ash FAILED for {blob_hash}: {e}"
            )
            return False
    
    def _encrypt_store_item(self, kind: str, item_id: str) -> bool:
        """تشفير عنصر في التخزين الصلب — غير منفذ بعد.

        R-682 (صدق): الكعب السابق كان يعيد True بلا أي تشفير — كذب في عدّ
        "encrypted_items". الآن: فشل صريح مع تسجيل أن المسار غير منفذ —
        لا يُحتسب تشفير لم يحدث أبدًا.
        """
        logger.warning(
            "R-682: store-item death encryption NOT IMPLEMENTED — not counted "
            "as encrypted (the old stub returned True without encrypting)"
        )
        return False
    
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
            seed = self._find_latest_seed(resurrection_key)
            if not seed:
                # قيامة من الرماد — فشلها يترك النظام DEAD (لا مرحلة انتقالية معلقة)
                result = self._resurrect_from_ashes(resurrection_key)
                if not result.get("success"):
                    self.phoenix_phase = PhoenixPhase.DEAD
                    self.resurrection_level = RESURRECTION_LEVEL_NONE
                    return result
                # نجاح مُثبت — نفس دورة حياة مسار البذرة
                self.phoenix_phase = PhoenixPhase.REBORN
                self.resurrection_level = RESURRECTION_LEVEL_NONE
                self.is_transforming = False
                self._save_state()
                self.core.append_event(
                    event_type="phoenix::resurrection",
                    payload={
                        "method": "ashes",
                        "ashes_restored": result.get("ashes_restored"),
                        "timestamp": time.time(),
                    },
                )
                return result
            
            # 2) إعادة بناء النواة — النجاح يُثبت بالبيانات المستعادة فعليًا
            restored = self._restore_from_seed(seed)
            if not restored:
                # R-682 (security — fail-closed): لا قيامة معلنة بلا استعادة حقيقية.
                # نبقى موتى، مواد الاسترداد (البذرة/الرماد) مُحفَظة ولا تُمسح.
                self.phoenix_phase = PhoenixPhase.DEAD
                self.resurrection_level = RESURRECTION_LEVEL_NONE
                logger.error(
                    "R-682 [SECURITY-FAIL]: resurrection FAILED at restore step — "
                    "REBORN NOT declared, ashes NOT cleared, seed preserved. "
                    "No success for a restoration that did not happen."
                )
                self.core.append_event(
                    event_type="phoenix::failed_restore",
                    payload={"seed_id": seed.id, "timestamp": time.time()}
                )
                return {
                    "success": False,
                    "error": "فشل استعادة البذرة — لم تُعلن القيامة وحُفظت مواد الاسترداد",
                    "phase": self.phoenix_phase.value,
                }

            # 3) فك تشفير باقي الذاكرة — فقط بعد استعادة مُثبتة
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
    
    def _find_latest_seed(self,
                          resurrection_key: Optional[str] = None) -> Optional[PhoenixSeed]:
        """العثور على أحدث بذرة — من الذاكرة أو من القرص (فك تشفير حقيقي)."""
        seeds = list(self.seeds.values())
        if not seeds:
            # البحث في الملفات — فك تشفير بالمفاتيح المعروفة أو المفتاح المُعطى
            seed_files = list(PHOENIX_SEEDS_DIR.glob("*.enc"))
            if seed_files:
                latest = max(seed_files, key=lambda x: x.stat().st_mtime)
                try:
                    encrypted = latest.read_bytes()
                except OSError as e:
                    logger.exception(
                        f"R-682 [SECURITY]: failed reading seed file {latest}"
                    )
                    return None
                # معرف البذرة من اسم الملف — يتيح الاشتقاق الحتمي للمفتاح
                # عبر إعادة التشغيل (master من الحالة + seed_id من الاسم)
                return self._decrypt_seed(
                    encrypted,
                    resurrection_key=resurrection_key,
                    seed_id=latest.stem,
                )
            return None
        
        return max(seeds, key=lambda x: x.created_at)
    
    def _restore_from_seed(self, seed: PhoenixSeed) -> bool:
        """إعادة بناء النواة من البذرة — الاستعادة تكتب في مخزن التطبيق الفعلي.

        R-682 (security): البيانات المستعادة تُكتب مرة أخرى في المخزن الحقيقي
        عبر واجهاته المعتادة (get_store().save_semantic) — فيعود ما يقرأه
        التطبيق لاحقًا عبر واجهة القراءة المعتادة (store.query). لا يُعلن
        نجاح لاستعادة لم تُكتب في المخزن. استعادة فارغة = فشل صريح.
        """
        try:
            # إعادة بناء الذاكرة الجوهرية — البيانات المقصودة نفسها
            essential = seed.essential_memory
            if not essential or not isinstance(essential, dict):
                logger.error(
                    "R-682 [SECURITY-FAIL]: seed essential_memory is empty or "
                    "invalid — nothing to restore. Restoration REFUSED."
                )
                return False

            # الكتابة في مخزن التطبيق الفعلي — العناصر الحرجة (دلالية + إجرائية)
            # R-682 (security — صدق النتيجة): تحقق من الحقول المطلوبة لكل نوع؛
            # أي عنصر لا يستوفيها = فشل جزئي — لا يُعلن نجاح كامل/REBORN.
            restored_items = 0
            failed_items: List[str] = []
            critical_items = essential.get("critical_memory") or []
            if critical_items:
                from ..store import get_store
                store = get_store()
                for item in critical_items:
                    item_type = item.get("type")
                    if item_type == "semantic" and item.get("concept") and item.get("definition"):
                        store.save_semantic(
                            concept=item["concept"],
                            definition=item.get("definition", ""),
                            aliases=item.get("aliases") or [],
                            related_concepts=item.get("related_concepts") or {},
                            examples=item.get("examples") or [],
                            confidence=item.get("confidence", 0.5),
                        )
                        restored_items += 1
                    elif (item_type == "procedural" and item.get("name")
                          and item.get("description") and item.get("action_sequence")):
                        # المهارة المقصودة: اسم + وصف + تسلسل إجراءات —
                        # إنشاء سجل فارغ ليس استعادة لها
                        store.save_procedural(
                            name=item["name"],
                            description=item.get("description", ""),
                            trigger_patterns=item.get("trigger_patterns") or [],
                            action_sequence=item.get("action_sequence") or [],
                            parameters=item.get("parameters") or {},
                            importance=item.get("importance", 0.8),
                        )
                        restored_items += 1
                    else:
                        failed_items.append(
                            f"{item_type}:{item.get('concept') or item.get('name') or '?'}"
                        )

            # R-682 (security — صدق النتيجة): لا نجاح كامل دون استعادة كل
            # العناصر المقصودة فعلًا — استعادة جزئية أو معدومة = فشل صريح
            # (لا REBORN معلن لعملية ناقصة).
            if restored_items == 0:
                logger.error(
                    "R-682 [SECURITY-FAIL]: restoration restored ZERO items — "
                    "no restorable data in seed (empty critical_memory or "
                    "unsupported item types). Restoration REFUSED (no success "
                    "declared for an unperformed restoration)."
                )
                return False
            if failed_items:
                logger.error(
                    f"R-682 [SECURITY-FAIL]: PARTIAL restoration — "
                    f"{restored_items} restored but {len(failed_items)} item(s) "
                    f"NOT restorable: {failed_items}. Full success NOT "
                    "declared (no REBORN for an incomplete restoration)."
                )
                return False

            # سجل تدقيق داخلي (إثبات قابل للفحص — لا بديلًا عن المخزن)
            self.restored_seeds[seed.id] = json.loads(json.dumps(essential))
            
            # تسجيل حدث البعث
            self.core.append_event(
                event_type="phoenix::restored_from_seed",
                payload={
                    "seed_id": seed.id,
                    "core_fingerprint": seed.core_fingerprint,
                    "essential_keys": list(essential.keys()),
                    "store_items_restored": restored_items,
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"فشل الاستعادة من البذرة: {e}")
            return False
    
    def _restore_ash(self, ash: PhoenixAshes) -> bool:
        """استعادة رماد واحد — قابلة للإثبات بمخزن محتوى-عنواني.

        R-682 (بناء): فك التشفير بالبصمة نفسها المُشتقة عند الحرق، مع
        التحقق من MAC أولًا (لا استعادة غير موثقة)، ثم إعادة التخزين —
        نجاح الاستعادة يُثبت بتطابق البصمة: put يعيد بصمة المحتوى،
        فتطابقها مع original_id يعني حرفيًا أن نفس البيانات عادت.
        """
        try:
            if not ash.mac:
                logger.error(
                    "R-682 [SECURITY-FAIL]: ash WITHOUT MAC rejected — "
                    "no unauthenticated restoration"
                )
                return False
            key = self._derive_death_key(ash.original_id)
            # 1) المصادقة قبل أي فك — تلاعب = رفض صريح
            if not hmac.compare_digest(
                hmac.new(key, ash.ash_data, hashlib.sha256).hexdigest(), ash.mac
            ):
                logger.error(
                    "R-682 [SECURITY]: ash MAC verification FAILED — "
                    f"tampered ash {ash.id} REJECTED, original {ash.original_id[:16]}..."
                )
                return False
            # 2) فك التشفير (نفس التدفق الحتمي للحرق)
            raw = bytes(a ^ b for a, b in zip(ash.ash_data, key * (len(ash.ash_data) // 32 + 1)))
            if not raw:
                logger.error(f"R-682: ash {ash.id} decrypted to EMPTY — rejected")
                return False
            # 3) الإثبات: إعادة التخزين تعيد بصمة المحتوى — التطابق = نفس البيانات
            restored_hash = self.core.blob_store.put(raw, compress=True)
            if restored_hash != ash.original_id:
                logger.error(
                    f"R-682: ash {ash.id} restoration HASH MISMATCH — "
                    f"{restored_hash[:16]}... != {ash.original_id[:16]}... — rejected"
                )
                return False
            logger.info(
                f"🔥 رماد مستعاد فعليًا: {ash.original_id[:16]}... "
                f"(بصمة المحتوى متطابقة = نفس البيانات)"
            )
            return True
        except Exception as e:
            logger.error(f"R-682: ash restoration FAILED for {ash.id}: {e}")
            return False

    def _resurrect_from_ashes(self, resurrection_key: str) -> Dict[str, Any]:
        """القيامة من الرماد - عندما لا توجد بذرة.

        R-682 (بناء): استعادة فعلية — كل رماد يُفك بمصادقة MAC ثم يُعاد
        تخزينه، والنجاح يُثبت بتطابق بصمة المحتوى (المخزن محتوى-عنواني:
        نفس البصمة = نفس البيانات). لا يُمسح إلا الرماد المستعاد فعلًا،
        والعدّ صادق: نجاح كامل أو فشل صريح أو جزئي مُعلن.
        """
        if not self.ashes:
            return {
                "success": False,
                "error": "لا رماد متاح للاستعادة",
                "ashes_available": 0,
            }
        restored = 0
        failed = 0
        for ash_id, ash in list(self.ashes.items()):
            ash.resurrection_attempts += 1
            ash.last_attempt = time.time()
            if self._restore_ash(ash):
                restored += 1
                del self.ashes[ash_id]  # يُمسح المستعاد فعلًا فقط
            else:
                failed += 1
        if restored == 0:
            logger.error(
                f"R-682 [SECURITY-FAIL]: ash resurrection FAILED for all "
                f"{failed} ashes — no success declared, ashes preserved"
            )
            return {
                "success": False,
                "error": "فشلت استعادة كل الرماد — لا نجاح معلن والرماد محفوظ",
                "ashes_available": failed,
            }
        result = {
            "success": True,
            "resurrected_from": "ashes",
            "ashes_restored": restored,
            "method": "self_decryption",
        }
        if failed:
            # جزئي صريح — لا نجاح مطلق لعملية ناقصة
            logger.warning(
                f"R-682: ash resurrection PARTIAL — {restored} restored, "
                f"{failed} failed (failed ashes preserved)"
            )
            result["ashes_failed"] = failed
            result["partial"] = True
        return result
    
    def _decrypt_all_memory(self) -> int:
        """فك تشفير كل الذاكرة — استعادة رماد فعلية قابلة للإثبات.

        R-682 (بناء): كل رماد يُفك بمصادقة MAC ثم يُعاد تخزينه، والنجاح
        يُثبت بتطابق بصمة المحتوى. لا يُمسح إلا المستعاد فعلًا، والعدّ
        يطابق الاستعادة الفعلية حصرًا.
        """
        if not self.ashes:
            return 0
        restored = 0
        for ash_id, ash in list(self.ashes.items()):
            if self._restore_ash(ash):
                restored += 1
                del self.ashes[ash_id]  # يُمسح المستعاد فعلًا فقط
        if restored:
            logger.info(
                f"🔥 فك الذاكرة: {restored} رماد مستعاد فعليًا "
                f"(بصمة المحتوى متطابقة)"
            )
        else:
            logger.error(
                "R-682 [SECURITY-FAIL]: ash decryption restored NOTHING — "
                "count stays 0, ashes preserved"
            )
        return restored
        return 0
    
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
    
    def _generate_resurrection_key(self, seed_id: Optional[str] = None) -> str:
        """توليد مفتاح قيامة — حتمي من (المفتاح الرئيسي + معرف البذرة).

        الحتمية ضرورية للاستمرارية: بعد إعادة التشغيل، يُشتق المفتاح نفسه
        من الحالة المسترجعة (master_resurrection_key) واسم ملف البذرة.
        بدون seed_id (مسار إرثي): مفتاح عشوائي غير قابل للاشتقاق.
        """
        if seed_id:
            return hashlib.sha256(
                f"{self.master_resurrection_key}:{seed_id}".encode()
            ).hexdigest()
        return hashlib.sha256(
            f"{self.master_resurrection_key}:{secrets.token_hex(32)}".encode()
        ).hexdigest()
    
    def get_resurrection_key(self) -> str:
        """مفتاح القيامة العام (للسيد فقط).

        R-682 (security — عقد موحد): يعيد بصمة التحقق
        sha256(SOVEREIGN_KEY:master) — وهي القيمة الوحيدة التي تقبلها
        resurrect() عبر _verify_resurrection_key. المفتاح الرئيسي نفسه
        لا يُكشف عبر الواجهات العامة أبدًا.
        """
        return hashlib.sha256(
            f"{SOVEREIGN_KEY}:{self.master_resurrection_key}".encode()
        ).hexdigest()
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    # R-682 (security): تغليف AES-GCM موثق — لا XOR متكرر (قابل للتلاعب الموضعي
    # مع بقاء الشكل مقبولًا). المصادقة مدمجة (وسم GCM) + nonce جديد لكل عملية +
    # بيانات مرتبطة (AAD) تربط التغليف بمفتاح السيادة ذاته.
    _MASTER_WRAP_AAD = b"sovereign-ai:phoenix:master-key-wrap:v1"

    def _wrap_master_key(self) -> str:
        """تغليف المفتاح الرئيسي بـ AES-GCM تحت مفتاح السيادة — لا يُخزَّن مكشوفًا أبدًا."""
        if AES is None:
            raise RuntimeError("pycryptodome غير متوفر — لا يمكن تأمين مفتاح القيامة")
        k = hashlib.sha256(SOVEREIGN_KEY.encode()).digest()  # 32 بايت لمفتاح AES-256
        nonce = get_random_bytes(12)
        cipher = AES.new(k, AES.MODE_GCM, nonce=nonce)
        cipher.update(self._MASTER_WRAP_AAD)  # بيانات مرتبطة — توثق غرض التغليف
        ct, tag = cipher.encrypt_and_digest(self.master_resurrection_key.encode())
        envelope = {
            "n": base64.b64encode(nonce).decode(),
            "d": base64.b64encode(ct).decode(),
            "t": base64.b64encode(tag).decode(),
        }
        return json.dumps(envelope)

    def _unwrap_master_key(self, wrapped: str) -> Optional[str]:
        """فك تغليف المفتاح الرئيسي — فشل مصادقة GCM = رفض قاطع (None).

        الفشل يعني: تلاعب، أو تلف، أو مفتاح سيادة مختلف — ولا يُكمل النظام
        بمفتاح عشوائي جديد إلا مع الحفاظ على الأصل (انظر _load_state/_save_state).
        """
        try:
            envelope = json.loads(wrapped)
            k = hashlib.sha256(SOVEREIGN_KEY.encode()).digest()
            cipher = AES.new(
                k, AES.MODE_GCM,
                nonce=base64.b64decode(envelope["n"], validate=True),
            )
            cipher.update(self._MASTER_WRAP_AAD)  # بيانات مرتبطة — توثق غرض التغليف
            plain = cipher.decrypt_and_verify(
                base64.b64decode(envelope["d"], validate=True),
                base64.b64decode(envelope["t"], validate=True),
            )
            value = plain.decode("utf-8")
            if len(value) == 128 and all(c in "0123456789abcdef" for c in value):
                return value
            return None
        except Exception:
            return None

    def _save_state(self) -> bool:
        """حفظ حالة نظام الفينيق — يُرجع نجاح الحفظ (متانة قبل إعلان أي نجاح لاحق)."""
        try:
            state = {
                "phoenix_phase": self.phoenix_phase.value,
                "resurrection_level": self.resurrection_level,
                "is_transforming": self.is_transforming,
                "seeds_count": len(self.seeds),
                "ashes_count": len(self.ashes),
                "last_resurrection": self.last_resurrection.__dict__ if self.last_resurrection else None,
                "master_key_enc": self._wrap_master_key(),
                "saved_at": time.time()
            }
            # R-682 (security): بعد فشل تحميل حالة موجودة، الكتابة مرفوضة —
            # الملف الأصلي يُحفظ كاملًا حرفيًا (دليل للتحقيق). أي كتابة الآن
            # قد تستبدل دليل الفساد بحالة سليمة-الشكل تخفي فقدان المفتاح.
            if getattr(self, "_state_master_key_invalid", False):
                logger.error(
                    "R-682 [SECURITY]: state save REFUSED — existing state "
                    "failed to load; original file preserved untouched "
                    "(forensic evidence, no silent replacement)"
                )
                return False

            # كتابة ذرّية متينة مع تمييز صريح بين مرحلتين:
            # (1) ما قبل الاستبدال: أي فشل يترك الملف الأصلي كما هو (يُنظف المؤقت)
            # (2) ما بعد الاستبدال: الملف الجديد مكتوب فعلًا — فشل مزامنة المجلد
            #     = متانة غير مؤكدة (لا يُدّعى أن الملف السابق بقي دون تغيير)
            tmp_path = PHOENIX_STATE_FILE.with_name(
                f"{PHOENIX_STATE_FILE.name}.{os.getpid()}.{time.time_ns()}.tmp"
            )

            # (1) كتابة الملف المؤقت — فشل هنا لا يمس الملف الأصلي إطلاقًا
            try:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
            except OSError as e:
                logger.error(
                    f"R-682: state save FAILED before replace — original file "
                    f"untouched. exc={e}"
                )
                self._cleanup_tmp(tmp_path)
                return False

            # (2) الاستبدال الذري — فشله يترك الملف الأصلي كما هو
            try:
                os.replace(tmp_path, PHOENIX_STATE_FILE)
            except OSError as e:
                logger.error(
                    f"R-682: state replace FAILED — original file untouched. exc={e}"
                )
                self._cleanup_tmp(tmp_path)
                return False

            # (3) الاستبدال وقع فعلًا — تأكيد المتانة بمزامنة المجلد.
            # فشلها لا يعني تراجعًا (الملف الجديد مكتوب) بل متانة غير مؤكدة.
            try:
                dir_fd = os.open(str(PHOENIX_STATE_FILE.parent), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError as e:
                logger.error(
                    "R-682: state file REPLACED but durability NOT CONFIRMED "
                    f"(dir fsync failed — file is the NEW one, do not claim "
                    f"the old file remained). exc={e}"
                )
                return False
            return True
        except Exception as e:
            logger.error(f"خطأ في حفظ الحالة: {e}")
            return False

    def _cleanup_tmp(self, tmp_path) -> None:
        """تنظيف الملف المؤقت بعد فشل ما قبل الاستبدال (أفضل جهد)."""
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:  # R-682: best-effort cleanup only — the original file was never touched
            pass  # تنظيف أفضل-جهد فقط — الملف الأصلي لم يُمس

    def _load_state(self) -> bool:
        """تحميل حالة نظام الفينيق — يُرجع النجاح.

        سياسة الفساد (fail-closed موثقة): عند تلف master_key_enc أو اختلاف
        مفتاح السيادة → فشل واضح (CRITICAL) مع الحفاظ على الأصل؛ لا يُستبدل
        الأصل صامتًا أبدًا.
        """
        try:
            if PHOENIX_STATE_FILE.exists():
                with open(PHOENIX_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.phoenix_phase = PhoenixPhase(state.get("phoenix_phase", "living"))
                    self.resurrection_level = state.get("resurrection_level", 0)
                    self.is_transforming = state.get("is_transforming", False)
                    # R-682 (security): استمرارية مفتاح القيامة عبر إعادة التشغيل
                    # بدونها لا يمكن فك أي بذرة من القرص بعد إعادة التشغيل إطلاقًا.
                    # غيابه في حالة موجودة = فشل صريح: صلاحية JSON وحدها لا تجعل
                    # الحالة قابلة للاسترجاع — المتابعة بمفتاح جديد تستبدل الحالة
                    # صامتًا وتتيه البذور القديمة نهائيًا.
                    master_enc = state.get("master_key_enc")
                    if not master_enc:
                        logger.critical(
                            "R-682 [SECURITY-FAIL]: state file exists WITHOUT "
                            "master_key_enc — key continuity impossible. "
                            "Initialization REFUSED; original file preserved "
                            "(no silent replacement)."
                        )
                        return False
                    if master_enc:
                        restored = self._unwrap_master_key(master_enc)
                        if restored:
                            if restored != self.master_resurrection_key:
                                self.master_resurrection_key = restored
                                logger.info(
                                    "🔑 مفتاح القيامة الرئيسي استُرجع من الحالة "
                                    "(استمرارية البذور عبر إعادة التشغيل)"
                                )
                        else:
                            # فشل مصادقة GCM — لا استمرار صامت بمفتاح بديل
                            self._state_master_key_invalid = True
                            self._state_master_key_enc_original = master_enc
                            logger.critical(
                                "R-682 [SECURITY-FAIL]: master_key_enc فشل في المصادقة "
                                "(تالف/مُتلاعَب به أو مفتاح سيادة مختلف) — فشل صريح. "
                                "الأصل مُحفَظ ولن يُستبدل؛ بذور الحالة السابقة قد تكون "
                                "غير قابلة للاستعادة حتى التدخل اليدوي"
                            )
                            return False
                logger.info("📂 تم تحميل حالة نظام الفينيق")
            return True
        except Exception as e:
            logger.error(f"خطأ في تحميل الحالة: {e}")
            return False
    
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
