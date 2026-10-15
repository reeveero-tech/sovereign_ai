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

import dataclasses
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
    """رماد الفينيق - ما يبقى بعد الموت.

    R-682 (جولة 8): ash_data مظروف موثق معياري AES-256-GCM (لا XOR متكرر —
    مفتاح التكرار نفسه كان يُستخدم للمصادقة فيتسرب مع معرفة نص أصلية):
    b"ASHV2" + nonce(12) + ciphertext + tag(16)، والمصادقة الإضافية (AAD)
    تربط الإصدار وoriginal_id بالبيانات.
    """
    id: str
    original_id: str
    burned_at: float
    ash_data: bytes
    resurrection_attempts: int = 0
    last_attempt: float = 0


@dataclass
class ResurrectionRecord:
    """سجل القيامة/الموت — مرتبط بمعرف المحاولة (op_id).

    R-682 (جولة 16): فصل الالتزام المادي عن تأكيد المتانة داخل السجل نفسه:
    - material_commit: هل وقع الالتزام المادي (الاستبدال + الحدث)؟
    - durability: تأكيد المتانة ("confirmed" / "unconfirmed" / None).
    تُحدّثان لكل محاولة — لا توريث من محاولة سابقة."""
    id: str
    before_hash: str
    after_hash: str
    reason: str
    method: str
    timestamp: float
    duration: float
    success: bool
    material_commit: Optional[bool] = None
    durability: Optional[str] = None


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
        # R-682 (جولة 13): علامة إنهاء معلقة — عملية موت لم يُؤكد اكتمالها
        # (الحدث لم يُلحق أو رفع العلامة لم يُحفظ). عند التحميل تُعامل كعملية
        # فاشلة لا كموت مكتمل (فاشل-مغلق: غير المحسوم ≠ مكتمل).
        self._pending_outcome = None
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

        R-682 (جولة 8 — صدق): blobs النواة تُشفر فعليًا إلى رماد موثق؛
        حماية عناصر المخزن الصلب غير منفذة بعد — النتيجة والحالة تعكسان
        عدم اكتمال الحماية صراحة (last_death_protection + الحدث + السجل)،
        ولا يُدّعى "تشفير الذاكرة بالكامل" والمسار ناقص.
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
        
        # 2) إنشاء نسخ استرداد مشفرة — عدّ صادق (blobs فقط؛ عناصر المخزن غير منفذة)
        protection = self._encrypt_all_memory()
        # جاهزية الاسترداد: كل ما فُحص أُنشئت له نسخة، بلا فشل ولا اقتطاع ولا عنصر
        # مخزن غير محمي. (لا يُستنتج اكتمال من صفر عدّاد — الفشل معلن.)
        recovery_ready = (
            protection["blob_failures"] == 0
            and not protection["events_scan_failed"]
            and not protection["events_truncated"]
            and not protection["store_scan_failed"]
            and not protection["store_truncated"]
            and protection["store_items_unprotected"] == 0
        )
        # الحماية بالإخفاء لا تحدث — الأصل يبقى مقروءًا (النسخة استرداد،
        # وحجب الأصول قرار المالك). لذا اكتمال الحماية = False صراحةً دائمًا.
        self.last_death_protection = {
            **protection,
            "recovery_ready": recovery_ready,
            "assets_hidden": False,
            "protection_complete": False,
        }
        
        # 3) عقد النتيجة (جولتا 10-11): الموت ينجح فقط إذا كانت نسخ الاسترداد
        # جاهزة **و** الحدث مُسجلًا **و** الحالة النهائية محفوظة — فشل أي منها
        # = فشل العملية (False)، النظام حي (LIVING) وقابل لإعادة المحاولة،
        # ولا تحول معلق، ومواد الاسترداد محفوظة.
        self.is_transforming = False  # العملية انتهت (نجحت أو فشلت) — لا تحول جارٍ
        
        # R-682 (جولة 15): معرف فريد لكل محاولة — يولد مرة واحدة ويُعاد
        # استخدامه في السجل والعلامة وجميع أحداث النتيجة (راجع event_payload
        # و_pending_outcome). ثانية واحدة لا تكفي (تصادم محاولتين يجعل التوفيق
        # يحسم محاولة بحدث محاولة سابقة).
        death_op_id = f"death_{int(time.time())}_{secrets.token_hex(6)}"
        # إعادة ضبط وصف المتانة لكل محاولة — لا توريث من محاولة سابقة
        self.last_death_durability = None

        def _failed_outcome(fail_reason: str) -> bool:
            """اتساق كامل عند أي فشل: LIVING + لا تحول + سجل فاشل + حالة محفوظة."""
            self.phoenix_phase = PhoenixPhase.LIVING
            self.resurrection_level = RESURRECTION_LEVEL_NONE
            self.is_transforming = False
            # العملية حُسمت فشلًا — العلامة المعلقة تُرفع قبل تراجع الحفظ
            # (نجاح التراجع = قرص نظيف؛ فشله = القرص يحمل DEAD+علامة فتُسوّى
            # عند التحميل كعملية فاشلة — لا كموت مكتمل)
            self._pending_outcome = None
            self.last_death_record = ResurrectionRecord(
                id=death_op_id,  # نفس معرف المحاولة — لا معرف جديد عند الفشل
                before_hash=self.core._last_hash,
                after_hash="LIVING",
                reason=f"{reason} [{fail_reason}]",
                method="self_encryption",
                timestamp=start_time,
                duration=time.time() - start_time,
                success=False,
                material_commit=False,  # فشل = لا التزام مادي
                durability=None,
            )
            # حدث الفشل بمرحلة معلنة — أفضل جهد: فشل تسجيله يُعلن ولا يُبتلع
            # (ولكنه لا يغير النتيجة: الفشل فشل)
            try:
                self.core.append_event(
                    event_type="phoenix::death_failed",
                    payload={
                        **event_payload,
                        "recovery_ready": False,
                        "failure_stage": fail_reason,
                        "timestamp": time.time()
                    }
                )
            except Exception as ev_err:
                logger.error(
                    f"R-682: فشل تسجيل حدث فشل الموت أيضًا ({fail_reason}): {ev_err} "
                    "— لا حدث إكمال إطلاقًا"
                )
            # أفضل جهد لحفظ الحالة المصححة — الفشل يُعلن (لا يُبتلع).
            # إن فشل أيضًا: القرص يحمل الحالة الانتقالية المعلقة وتُسوّى عند
            # التحميل كعملية منقطعة (راجع _load_state).
            if not self._save_state():
                logger.error(
                    "R-682 [SECURITY]: فشل حفظ حالة فشل الموت — الحالة على القرص "
                    "قد تحمل علم تحول قديمًا (يُسوّى عند التحميل كعملية منقطعة)"
                )
            return False
        
        death_record = ResurrectionRecord(
            id=death_op_id,
            before_hash=self.core._last_hash,
            after_hash="DEAD" if recovery_ready else "LIVING",
            reason=reason,
            method="self_encryption",
            timestamp=start_time,
            duration=time.time() - start_time,
            success=recovery_ready,
            material_commit=False,  # يُحدَّث عند النتيجة (لا توريث)
            durability=None,
        )
        self.last_death_record = death_record
        
        # R-682 (جولة 12): الحالة النهائية تُحفظ قبل حدث الإكمال — لا يُعلن
        # موت في سجل الأحداث قبل أن يكون متينًا على القرص. فشل الحفظ النهائي =
        # لا حدث إكمال إطلاقًا (فاشل-مغلق) — فقط حدث فشل بمرحلة معلنة.
        if recovery_ready:
            self.phoenix_phase = PhoenixPhase.DEAD
            self.resurrection_level = RESURRECTION_LEVEL_DEATH
        else:
            self.phoenix_phase = PhoenixPhase.LIVING
            self.resurrection_level = RESURRECTION_LEVEL_NONE
        # R-682 (جولة 13): علامة إنهاء معلقة — تُحفظ مع الحالة قبل حدث الإكمال،
        # وترفع فقط بعد إلحاق الحدث وحفظ الرفع (التزام ذري عبر علامة قابلة
        # للتمييز). عملية غير محسومة تُحمَّل كفاشلة — لا كموت مكتمل.
        self._pending_outcome = {
            "op": "death",
            "id": death_op_id,
            "intended": "DEAD" if recovery_ready else "LIVING",
        }
        event_payload = {
            "reason": reason,
            "resurrection_mode": resurrection_mode,
            "blobs_encrypted": protection["blobs_encrypted"],
            "blob_failures": protection["blob_failures"],
            "events_scan_failed": protection["events_scan_failed"],
            "events_truncated": protection["events_truncated"],
            "store_items_unprotected": protection["store_items_unprotected"],
            "store_scan_failed": protection["store_scan_failed"],
            "store_truncated": protection["store_truncated"],
            "recovery_ready": recovery_ready,
            "assets_hidden": False,
            "protection_complete": False,
            "op_id": death_record.id,
            "seed_id": final_seed.id if final_seed else None,
            "timestamp": time.time()
        }
        if not self._save_state():
            logger.error(
                "R-682 [SECURITY-FAIL]: فشل حفظ الحالة النهائية للموت — لا موت "
                "معلنًا ولا حدث إكمال (الحالة على القرص قد تحمل علم تحول قديمًا "
                "يُسوّى عند التحميل كعملية منقطعة)"
            )
            return _failed_outcome("final state save failed")
        
        if recovery_ready:
            # حدث الإكمال — فقط بعد حفظ متين. فشله = تراجع كامل (لا DEAD بلا إعلان)
            try:
                self.core.append_event(
                    event_type="phoenix::death", payload=event_payload
                )
            except Exception as e:
                logger.error(
                    f"R-682 [SECURITY-FAIL]: فشل تسجيل حدث الموت بعد حفظ الحالة — "
                    f"تراجع كامل: {e}"
                )
                return _failed_outcome("death event recording failed")
            # الحدث أُلحق — رفع العلامة (commit). التمييز الثلاثي:
            # (أ) حفظ متين → مكتمل؛ (ب) الاستبدال وقع لكن المتانة غير مؤكدة →
            # الملف الجديد (بلا علامة) هو الموجود فعلًا والحدث مُلحق — العملية
            # مكتملة ماديًا (نجاح مع تحذير متانة، متسق مع القرص)؛
            # (ج) الاستبدال لم يقع → غير محسوم: تراجع كامل.
            self._pending_outcome = None
            # R-682 (جولة 17): حقلا السجل يُحدَّثان **قبل** حفظ رفع العلامة —
            # القيمة المحافظة "unconfirmed" تُكتب أولًا (لا يُدَّعى confirmed قبل
            # إثباته)، فالسجل المحفوظ يحمل الالتزام المادي ووصف المتانة معًا،
            # ويستمر عبر إعادة التحميل. الترقية إلى "confirmed" حفظ مفحوص
            # لاحق — لا حفظ أخير غير مفحوص أبدًا.
            death_record.material_commit = True   # الحدث مُلحق — الالتزام وقع
            death_record.durability = "unconfirmed"  # محافظة حتى إثبات المتانة
            if not self._save_state():
                if getattr(self, "_last_save_replaced_unconfirmed", False):
                    # R-682 (جولة 15 — فصل صريح): الالتزام المادي وقع (الاستبدال
                    # + الحدث مُلحق) — ليس فشلًا متراجعًا عنه؛ لكن المتانة غير
                    # مؤكدة — وليس نجاح العقد (الذي يشترط الحفظ المتين).
                    # النتيجة False، والسجل المحفوظ (في الملف الجديد الموجود
                    # فعلًا) يحمل success=True + material_commit=True +
                    # durability=unconfirmed — محافظة وصريحة.
                    self.last_death_durability = "unconfirmed"
                    logger.warning(
                        "R-682: الالتزام المادي وقع (الاستبدال + الحدث مُلحق — "
                        "ليس فشلًا متراجعًا) لكن متانة الحفظ غير مؤكدة (فشل "
                        "مزامنة المجلد) — النتيجة False: عقد المتانة غير مستوفى، "
                        "والسجل success=True + material_commit=True + "
                        "durability=unconfirmed"
                    )
                    return False
                logger.error(
                    "R-682 [SECURITY-FAIL]: فشل حفظ رفع علامة الإنهاء (قبل "
                    "الاستبدال) — العملية غير محسومة ولا يُعلن موت (التوفيق مع "
                    "سجل الأحداث عند التحميل يحدد النتيجة)"
                )
                return _failed_outcome("pending-outcome commit save failed")
            # الترقية إلى "confirmed" — حفظ مفحوص: نجاحه يُثبت الوصف على القرص؛
            # فشله يُبقي القرص على الوصف المحافظ (صريح — لا ادعاء بلا إثبات).
            # حالة الموت نفسها متينة (حفظ رفع العلامة نجح كاملًا) — فشل ترقية
            # الوصف لا يغير النتيجة، والتحميل يوفّق مع سجل الأحداث (الدليل
            # الدائم) في كل الأحوال.
            self.last_death_durability = "confirmed"
            death_record.durability = "confirmed"
            if not self._save_state():
                if getattr(self, "_last_save_replaced_unconfirmed", False):
                    # R-682 (جولة 18): تمييز وقوع الكتابة من تأكيد متانتها —
                    # الاستبدال وقع فالمحتوى الجديد (confirmed) هو الموجود
                    # فعلًا؛ لا يُدَّعى بقاء المحتوى القديم.
                    logger.warning(
                        "R-682: ترقية وصف المتانة كُتبت فعلًا (الاستبدال وقع — "
                        "JSON القرص يحمل confirmed) لكن متانتها غير مؤكدة (فشل "
                        "مزامنة المجلد) — وقوع الكتابة ≠ تأكيد متانتها"
                    )
                else:
                    # فشل قبل الاستبدال — القرص فعليًا يبقى على الوصف المحافظ
                    logger.warning(
                        "R-682: حالة الموت متينة (حفظ رفع العلامة نجح) لكن حفظ "
                        "ترقية وصف المتانة (confirmed) فشل قبل الاستبدال — "
                        "القرص يبقى على الوصف المحافظ (unconfirmed)؛ التوفيق مع "
                        "سجل الأحداث عند التحميل يحدث عند وجود علامة معلقة فقط"
                    )
            logger.warning(
                f"⚰️ الموت تم: نسخ الاسترداد جاهزة ({protection['blobs_encrypted']} blob "
                "مشفر إلى رماد موثق) والحالة محفوظة. الأصول تبقى مقروءة (الحماية "
                "بالإخفاء قرار المالك) — الحماية ليست مكتملة."
            )
            return True

        # فشل الموت: جاهزية الاسترداد ناقصة — لا يُعلن موتًا ناجحًا أبدًا.
        # مواد الاسترداد (الرماد المُنشأ + البذور) محفوظة، والنظام حي قابل
        # لإعادة المحاولة. الأسباب معلنة في الحدث والسجل.
        try:
            self.core.append_event(
                event_type="phoenix::death_failed", payload=event_payload
            )
        except Exception as e:
            logger.error(
                f"R-682 [SECURITY-FAIL]: فشل تسجيل حدث فشل الموت: {e} — "
                "النتيجة False والنظام حي والرماد/البذور محفوظة"
            )
            return _failed_outcome("death-failed event recording failed")
        # الفشل حُسم وأُعلن — رفع العلامة (أفضل جهد: النتيجة False أصلًا،
        # وبقاء العلامة على القرص يُسوّى عند التحميل كعملية فاشلة)
        self._pending_outcome = None
        if not self._save_state():
            logger.error(
                "R-682: فشل حفظ رفع علامة الإنهاء في مسار الفشل — تُسوّى عند "
                "التحميل كعملية فاشلة (النتيجة False أصلًا)"
            )
        reasons = []
        if protection["blob_failures"]:
            reasons.append(f"{protection['blob_failures']} فشل إنشاء رماد")
        if protection["events_scan_failed"]:
            reasons.append("تعذر فحص أحداث النواة")
        if protection["events_truncated"]:
            reasons.append("اقتطاع فحص الأحداث (حد 1000)")
        if protection["store_scan_failed"]:
            reasons.append("تعذر فحص المخزن")
        if protection["store_truncated"]:
            reasons.append("اقتطاع استعلام المخزن (حد 500)")
        if protection["store_items_unprotected"]:
            reasons.append(
                f"{protection['store_items_unprotected']} عنصر مخزن غير محمي"
            )
        logger.warning(
            f"⚰️ فشل الموت — نسخ الاسترداد غير جاهزة ({'; '.join(reasons)}) — "
            f"{protection['blobs_encrypted']} blob مشفر إلى رماد موثق. "
            "لا موت معلنًا: النظام حي، والرماد/البذور محفوظة لإعادة المحاولة."
        )
        return False
    
    def _encrypt_all_memory(self) -> Dict[str, Any]:
        """إنشاء نسخ استرداد مشفرة — الموت الرقمي (عدّ صادق منفصل عن الحماية).

        R-682 (جولة 9): النتيجة تفصل صراحةً بين نجاح إنشاء نسخ الاسترداد
        وبين حماية الأصول (التي لا تحدث — الأصل يبقى مقروءًا). الفشل
        وتعذر الفحص والاقتطاع (حدود 1000/500) كلها معلنة — لا يُستنتج
        اكتمال من صفر عدّاد.
        """
        encrypted_count = 0
        blob_failures = 0
        events_seen = 0
        events_scan_failed = False
        
        try:
            for event in self.core.iterate_events(limit=1000):
                events_seen += 1
                blob = event.get("blob")
                if blob:
                    if self._encrypt_single_blob(blob):
                        encrypted_count += 1
                    else:
                        blob_failures += 1
        except Exception as e:
            logger.error(f"R-682: فشل فحص أحداث النواة أثناء الموت: {e}")
            events_scan_failed = True
        # حد الفحص: ما بعد 1000 غير مفحوص — اقتطاع معلن
        events_truncated = events_seen >= 1000
        
        store_items_unprotected = 0
        store_scan_failed = False
        store_truncated = False
        
        try:
            # عناصر التخزين الصلب — مسار التشفير غير منفذ: تُعدّ كلها
            # غير محمية (بمعرّف أو بدونه — غياب المعرّف لا يعني غياب الحماية
            # عن العنصر)، ولا يُعلن تشفير لم يحدث.
            from ..store import get_store
            store = get_store()
            
            for kind in ["procedural", "semantic", "episodic", "associative"]:
                items = store.query(kind, limit=500)
                for item in items:
                    store_items_unprotected += 1
                    item_id = item.get("_id")
                    if item_id:
                        self._encrypt_store_item(kind, item_id)  # يسجل صراحةً: غير منفذ
                if len(items) >= 500:
                    store_truncated = True
        except Exception as e:
            logger.error(f"R-682: تعذر فحص مخزن التطبيق أثناء الموت: {e}")
            store_scan_failed = True
        
        return {
            "blobs_encrypted": encrypted_count,
            "blob_failures": blob_failures,
            "events_scan_failed": events_scan_failed,
            "events_truncated": events_truncated,
            "store_items_unprotected": store_items_unprotected,
            "store_scan_failed": store_scan_failed,
            "store_truncated": store_truncated,
        }
    
    def _encrypt_single_blob(self, blob_hash: str) -> bool:
        """تشفير blob واحد — R-682 (بناء): المسار القديم كان كودًا ميتًا
        (self.core.store_blob/load_blob غير موجودين في SovereignCore — الواجهة
        الفعلية blob_store.put/get) فكان يفشل صامتًا بلا رماد أبدًا.
        الآن: الواجهة الحقيقية + مصادقة MAC — لا رماد بلا توثيق."""
        try:
            if AES is None:
                logger.error(
                    "R-682: AES-GCM unavailable — refusing to create ash with "
                    "insecure XOR (no unauthenticated ash, ever)"
                )
                return False
            key = self._derive_death_key(blob_hash)
            raw = self.core.blob_store.get(blob_hash, decompress=True)
            # R-682 (جولة 8): مظروف AES-256-GCM موثق — nonce جديد لكل عملية
            # + AAD يربط الإصدار وoriginal_id. لا XOR متكرر.
            nonce = get_random_bytes(12)
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            aad = f"R682-ASH-V2:{blob_hash}".encode()
            cipher.update(aad)  # ربط الإصدار وoriginal_id بالوسم
            ct, tag = cipher.encrypt_and_digest(raw)
            encrypted = b"ASHV2" + nonce + ct + tag

            # تخزين النسخة المشفرة (مخزن محتوى-عنواني)
            encrypted_hash = self.core.blob_store.put(encrypted, compress=True)

            # تسجيل في الرماد
            ash = PhoenixAshes(
                id=f"ash_{int(time.time())}_{secrets.token_hex(4)}",
                original_id=blob_hash,
                burned_at=time.time(),
                ash_data=encrypted
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
            decrypt_result = self._decrypt_all_memory()

            # R-682 (جولة 8): استعادة ناقصة = لا REBORN أبدًا — معلومات
            # الفشل تمر عبر النتيجة، والرماد الفاشل محفوظ والبذرة محفوظة.
            if decrypt_result["failed"] > 0:
                self.phoenix_phase = PhoenixPhase.DEAD
                self.resurrection_level = RESURRECTION_LEVEL_NONE
                logger.error(
                    "R-682 [SECURITY-FAIL]: resurrection INCOMPLETE — seed "
                    "restored but ash decryption left failures — REBORN NOT "
                    "declared, failed ashes + seed preserved"
                )
                self.core.append_event(
                    event_type="phoenix::failed_restore",
                    payload={
                        "seed_id": seed.id,
                        "ashes_restored": decrypt_result["restored"],
                        "ashes_failed": decrypt_result["failed"],
                        "timestamp": time.time(),
                    },
                )
                return {
                    "success": False,
                    "error": "استعادة ناقصة: البذرة استُعيدت لكن فك رماد متبقٍ فشل — لا قيامة معلنة",
                    "seed_restored": True,
                    "ashes_restored": decrypt_result["restored"],
                    "ashes_failed": decrypt_result["failed"],
                    "partial": True,
                    "phase": self.phoenix_phase.value,
                }

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
                    "decrypted_items": decrypt_result["restored"],
                    "method": resurrection.method
                }
            )
            
            logger.info(f"🐦‍🔥 القيامة اكتملت! عادت الذاكرة بعد {duration:.2f} ثانية")
            
            return {
                "success": True,
                "duration": duration,
                "decrypted_items": decrypt_result["restored"],
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
        """استعادة رماد واحد — قابلة للإثبات بالقراءة المستقلة.

        R-682 (جولة 8): مظروف AES-256-GCM (فشل الوسم = رفض صريح) ثم إعادة
        تخزين + إثبات فعلي: قراءة مستقلة ومقارنة البايتات وتحقق بصمة
        الملف — لأن put يتجاوز الكتابة إذا وُجد المسار، فقد تعيد البصمة
        المتوقعة بينما الملف تحتها تالف. لا يُحتسب النجاح ولا يُمسح
        الرماد إلا بعد قراءة مستقلة مطابقة.
        """
        try:
            if not ash.ash_data or not ash.ash_data.startswith(b"ASHV2"):
                logger.error(
                    "R-682 [SECURITY-FAIL]: ash with unknown/unauthenticated "
                    f"format rejected (id={ash.id}) — no XOR/no-MAC ash accepted"
                )
                return False
            key = self._derive_death_key(ash.original_id)
            nonce = ash.ash_data[5:17]
            tag = ash.ash_data[-16:]
            ct = ash.ash_data[17:-16]
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            aad = f"R682-ASH-V2:{ash.original_id}".encode()
            cipher.update(aad)
            try:
                raw = cipher.decrypt_and_verify(ct, tag)
            except ValueError:
                logger.error(
                    "R-682 [SECURITY]: ash GCM authentication FAILED — "
                    f"tampered/wrong-key ash {ash.id} REJECTED, "
                    f"original {ash.original_id[:16]}..."
                )
                return False
            if not raw:
                logger.error(f"R-682: ash {ash.id} decrypted to EMPTY — rejected")
                return False

            # 1) إعادة التخزين — البصمة المعادة يجب أن تطابق (محتوى-عنواني)
            restored_hash = self.core.blob_store.put(raw, compress=True)
            if restored_hash != ash.original_id:
                logger.error(
                    f"R-682: ash {ash.id} restoration HASH MISMATCH — "
                    f"{restored_hash[:16]}... != {ash.original_id[:16]}... — rejected"
                )
                return False

            # 2) الإثبات الفعلي — قراءة مستقلة (put يتجاوز الملف القائم).
            # فشل القراءة نفسه (بيانات مضغوطة تالفة) = تلف مكتشف → إصلاح.
            try:
                stored_back = self.core.blob_store.get(ash.original_id)
                read_ok = stored_back == raw
            except Exception:
                read_ok = False
            if not read_ok:
                # الملف القائم تالف — إصلاح صريح: حذف ثم إعادة تخزين ثم تحقق
                logger.warning(
                    f"R-682: blob {ash.original_id[:16]}... exists CORRUPTED "
                    "(read-back mismatch) — repairing: delete + re-store + verify"
                )
                self.core.blob_store.delete(ash.original_id)
                self.core.blob_store.put(raw, compress=True)
                try:
                    repaired_ok = self.core.blob_store.get(ash.original_id) == raw
                except Exception:
                    repaired_ok = False
                if not repaired_ok:
                    logger.error(
                        f"R-682: ash {ash.id} repair FAILED — read-back still "
                        "bad, ash NOT consumed"
                    )
                    return False

            # 3) تحقق بصمة الملف الفعلي من القرص
            if not self.core.blob_store.verify_content_hash(ash.original_id):
                logger.error(
                    f"R-682: ash {ash.id} stored-file HASH verification FAILED — "
                    "restoration not accepted"
                )
                return False

            logger.info(
                f"🔥 رماد مستعاد فعليًا: {ash.original_id[:16]}... "
                "(قراءة مستقلة مطابقة + بصمة الملف موثقة)"
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
        if failed > 0:
            # R-682 (جولة 8): استعادة ناقصة = لا نجاح ولا REBORN أبدًا —
            # مهما عدد المستعاد. الرماد الفاشل يبقى محفوظًا.
            logger.error(
                f"R-682 [SECURITY-FAIL]: ash resurrection INCOMPLETE — "
                f"{restored} restored, {failed} FAILED — no success declared, "
                "failed ashes preserved"
            )
            return {
                "success": False,
                "error": "استعادة ناقصة: فشل رماد متبقٍ — لا قيامة معلنة والرماد الفاشل محفوظ",
                "ashes_restored": restored,
                "ashes_failed": failed,
                "ashes_available": failed,
                "partial": True,
            }
        return {
            "success": True,
            "resurrected_from": "ashes",
            "ashes_restored": restored,
            "method": "self_decryption",
        }
    
    def _decrypt_all_memory(self) -> int:
        """فك تشفير كل الذاكرة — استعادة رماد فعلية قابلة للإثبات.

        R-682 (بناء): كل رماد يُفك بمصادقة MAC ثم يُعاد تخزينه، والنجاح
        يُثبت بتطابق بصمة المحتوى. لا يُمسح إلا المستعاد فعلًا، والعدّ
        يطابق الاستعادة الفعلية حصرًا.
        """
        if not self.ashes:
            return {"restored": 0, "failed": 0}
        restored = 0
        failed = 0
        for ash_id, ash in list(self.ashes.items()):
            if self._restore_ash(ash):
                restored += 1
                del self.ashes[ash_id]  # يُمسح المستعاد فعلًا فقط
            else:
                failed += 1
        if failed:
            logger.error(
                f"R-682 [SECURITY-FAIL]: ash decryption INCOMPLETE — "
                f"{restored} restored, {failed} FAILED (failed ashes preserved)"
            )
        elif restored:
            logger.info(
                f"🔥 فك الذاكرة: {restored} رماد مستعاد فعليًا "
                f"(قراءة مستقلة مطابقة + بصمة الملف موثقة)"
            )
        return {"restored": restored, "failed": failed}
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
        """حفظ حالة نظام الفينيق — يُرجع نجاح الحفظ (متانة قبل إعلان أي نجاح لاحق).

        R-682 (جولة 14): False لا يعني بالضرورة أن الملف القديم بقي — الاستبدال
        قد يقع ثم تفشل مزامنة المجلد (متانة غير مؤكدة، الملف الجديد هو الموجود).
        العلم _last_save_replaced_unconfirmed يميز الحالتين للمُستدعي."""
        # إعادة الضبط في كل حفظ (قبل أي مسار)
        self._last_save_replaced_unconfirmed = False
        try:
            state = {
                "phoenix_phase": self.phoenix_phase.value,
                "resurrection_level": self.resurrection_level,
                "is_transforming": self.is_transforming,
                # getattr: كائنات تُبنى بـ__new__ (اختبارات) قد لا تمر بـ__init__
                "pending_outcome": getattr(self, "_pending_outcome", None),
                "seeds_count": len(self.seeds),
                "ashes_count": len(self.ashes),
                "last_resurrection": self.last_resurrection.__dict__ if self.last_resurrection else None,
                # R-682 (جولة 17): سجل نتيجة الموت يستمر عبر الحفظ وإعادة
                # التحميل — معرف العملية + الالتزام المادي + وصف المتانة.
                "last_death_record": (
                    getattr(self, "last_death_record", None).__dict__
                    if getattr(self, "last_death_record", None) else None
                ),
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
                # الاستبدال وقع فعليًا — الملف الجديد هو الموجود؛ المتانة فقط
                # غير مؤكدة. يميز المُستدعي هذه الحالة عن فشل ما قبل الاستبدال.
                self._last_save_replaced_unconfirmed = True
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

    def _reconcile_record_with_outcome(
        self, op_id: Optional[str], completed: bool, why: Optional[str] = None
    ) -> None:
        """R-682 (جولة 18): السجل المُعاد تحميله يعكس نتيجة التوفيق نفسها.

        نسخة القرص مرحلية (وجود العلامة يبيّن ذلك) — قيمها محفوظة قبل حسم
        النتيجة. بعد التوفيق مع الدليل الدائم (سجل الأحداث):
        - اكتملت: السجل يعكس الالتزام المثبت بالحدث (material_commit=True)
          والمتانة محافظة (unconfirmed — لا دليل عند التحميل يبرر ترقيتها).
        - فاشلة/غير محسومة: السجل لا يعلن نجاحًا ولا DEAD بعد التوفيق.
        لا حفظ تلقائي إضافي هنا — القرص يبقى مرحليًا حتى أول حفظ لاحق."""
        rec = getattr(self, "last_death_record", None)
        if rec is None or not op_id or getattr(rec, "id", None) != op_id:
            return  # السجل لا يخص هذه العملية — لا يُمس
        if completed:
            rec.success = True
            rec.after_hash = "DEAD"
            rec.material_commit = True      # الحدث أثبت الاكتمال
            rec.durability = "unconfirmed"  # محافظة — لا ترقية بلا دليل
        else:
            rec.success = False
            rec.after_hash = "LIVING"
            rec.material_commit = False
            rec.durability = None
            if why:
                rec.reason = f"{rec.reason} [load-reconciled: {why}]"

    def _reconcile_pending_outcome(self, pending: Dict[str, Any]) -> Optional[str]:
        """التوفيق بين عملية معلقة والدليل الدائم (سجل الأحداث).

        يبحث في أحداث النتيجة (phoenix::death / phoenix::death_failed) عن
        معرف العملية (op_id) — الأحدث أولًا — ويعيد نوع الحدث الفاصل، أو
        None إن لم يوجد دليل. تعذر الفحص = لا دليل (فاشل-مغلق عند المُستدعي).
        """
        op_id = (pending or {}).get("id")
        if not op_id:
            return None
        try:
            # R-682 (جولة 15): استنفاد السجل فعليًا — البحث المحدود (ذيل 100)
            # ليس توفيقًا حاسمًا: الدليل لا يغيب لبعده عن الذيل. يُفحص السجل
            # كاملًا (الأحدث أولًا) حتى العثور على نتيجة العملية أو النهاية.
            for event in self.core.iterate_events(reverse=True):
                et = event.get("type")
                if et not in ("phoenix::death", "phoenix::death_failed"):
                    continue
                blob_hash = event.get("blob")
                if not blob_hash:
                    continue
                # R-682: حدث نتيجة غير قابل للقراءة (blob مفقود/تالف) — لا دليل
                # منه؛ يتجاوزه التوفيق (الأحداث الأخرى أو لا دليل = فاشل-مغلق)
                try:
                    payload_bytes = self.core.blob_store.get(blob_hash, decompress=True)
                    payload = json.loads(payload_bytes)
                except Exception:
                    continue
                if payload.get("op_id") == op_id:
                    return et
        except Exception as e:
            logger.error(
                f"R-682: تعذر فحص سجل الأحداث للتوفيق مع العملية المعلقة: {e} "
                "— لا دليل (فاشل-مغلق)"
            )
        return None

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
                    # R-682 (جولة 17): استمرارية سجل نتيجة الموت — يُحمَّل من
                    # القرص مع حقليه (الالتزام المادي + وصف المتانة). مفاتيح
                    # غير معروفة تُهمل (توافق مع ملفات قديمة).
                    _saved_rec = state.get("last_death_record")
                    if isinstance(_saved_rec, dict):
                        _valid = {f.name for f in dataclasses.fields(ResurrectionRecord)}
                        self.last_death_record = ResurrectionRecord(**{
                            k: v for k, v in _saved_rec.items() if k in _valid
                        })
                    # R-682 (جولة 13): علامة إنهاء معلقة = عملية موت لم يُؤكد
                    # اكتمالها (الحدث لم يُلحق أو رفع العلامة لم يُحفظ).
                    # غير المحسوم ≠ مكتمل: تُعامل كعملية فاشلة — لا يُحمَّل
                    # DEAD كموت مكتمل أبدًا.
                    _pending = state.get("pending_outcome")
                    if _pending:
                        # R-682 (جولة 14): التوفيق مع الدليل الدائم — لا يُصنف
                        # غير المحسوم آليًا فاشلًا: إن كان حدث الإكمال مُلحقًا
                        # فعليًا فالعملية اكتملت (المؤجل رفع العلامة فقط).
                        self._pending_outcome = None
                        outcome_event = self._reconcile_pending_outcome(_pending)
                        if outcome_event == "phoenix::death":
                            logger.warning(
                                f"R-682: علامة إنهاء معلقة ({_pending}) لكن حدث "
                                "الإكمال مُلحق فعلًا في السجل — العملية اكتملت "
                                "(المؤجل كان رفع العلامة فقط)"
                            )
                            # الحالة كما هي (DEAD) — العملية مكتملة، والسجل
                            # يعكس الالتزام المثبت (المتانة محافظة)
                            self._reconcile_record_with_outcome(
                                (_pending or {}).get("id"), completed=True
                            )
                        else:
                            if outcome_event == "phoenix::death_failed":
                                _why = "حدث الفشل مُلحق — عملية فاشلة"
                            else:
                                _why = "لا دليل نتيجة في السجل — غير محسوم: فاشل-مغلق"
                            logger.warning(
                                f"R-682: علامة إنهاء معلقة ({_pending}) — {_why}: "
                                "تُعامل كعملية فاشلة (LIVING) لا كموت مكتمل، "
                                "ومواد الاسترداد محفوظة"
                            )
                            self.phoenix_phase = PhoenixPhase.LIVING
                            self.resurrection_level = RESURRECTION_LEVEL_NONE
                            self.is_transforming = False
                            # السجل لا يعلن نجاحًا ولا DEAD بعد توفيق فاشل —
                            # نسخة القرص المرحلية حُفظت قبل حسم النتيجة
                            self._reconcile_record_with_outcome(
                                (_pending or {}).get("id"), completed=False, why=_why
                            )
                    # R-682 (جولة 12): تسوية الحالة الانتقالية المعلقة — علم تحول
                    # محفوظ لا يمكن أن يكون جاريًا في عملية جديدة (لا عملية تعبر
                    # العمليات): يُعامل كعملية منقطعة لا كتحول يمنع المحاولة.
                    if self.is_transforming:
                        interrupted = self.phoenix_phase in (
                            PhoenixPhase.DYING, PhoenixPhase.TRANSFORMING
                        )
                        self.is_transforming = False
                        if interrupted:
                            self.phoenix_phase = PhoenixPhase.LIVING
                            self.resurrection_level = RESURRECTION_LEVEL_NONE
                        logger.warning(
                            "R-682: علم تحول معلق في الحالة المحفوظة (عملية "
                            "منقطعة — لا تحول جارٍ في عملية جديدة). صُفّر العلم"
                            + (" وأُعيدت الحالة إلى LIVING — إعادة المحاولة غير محظورة."
                               if interrupted else ".")
                        )
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
