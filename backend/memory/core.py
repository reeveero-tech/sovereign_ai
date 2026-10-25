# backend/memory/core.py
# نواة الذاكرة السيادية الحقيقية
# سجل لا يُمحى، سلسلة تجزئة، تخزين بالمحتوى، توزيع، تحقق، وتوقيع
# الإصدار: 1.0.0 — نواة نظام تجريبي (R-702: ادعاء «جاهز للإنتاج» السابق غير مثبت؛ إعلان الجاهزية للمالك وحده)

"""
هذا الملف هو قلب السيادة.

المبادئ:
1. لا حذف. لا تعديل. فقط إضافة. (Append-only)
2. كل حدث مرتبط بالحدث السابق عبر تجزئة تشفيرية. (Hash Chain)
3. كل محتوى يُخزن بتجزئته، والإشارة إليه عبر التجزئة. (Content-Addressable)
4. كل حدث مُوقّع بتوقيع HMAC لا يمكن تزويره.
5. السجل كامل قابل للتحقق والتدقيق.
6. يمكن تصديره، استعادته، وتوزيعه على عقد متعددة.

هذه ليست تجربة. هذا هو الأساس.
"""

import json
import os
import hashlib
import hmac
import zlib
import base64
import shutil
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Iterator, Tuple, BinaryIO
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# إعداد التسجيل المهني
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# استيراد الإعدادات السيادية
try:
    from config import DATA_DIR, SOVEREIGN_KEY  # LEGACY-ROOT-KEY (read-only): تحقق أحداث ledger التاريخية فقط
except ImportError:
    # للاستخدام المستقل للملف
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    SOVEREIGN_KEY = os.getenv("SOVEREIGN_KEY", "يجب_تغيير_هذا_المفتاح_فوراً")  # LEGACY-ROOT-KEY (read-only)
    logger.warning("تم استخدام إعدادات افتراضية للـ config")


# ============================================================
# الثوابت والتكوين
# ============================================================

class EventType(str, Enum):
    """أنواع الأحداث في السجل السيادي"""
    INTERACTION = "interaction"      # تفاعل مستخدم
    RESPONSE = "response"            # رد الذكاء
    EXPERIMENT = "experiment"        # تجربة
    APPROVAL = "approval"            # موافقة السيد
    SELF_MODIFY = "self_modify"      # تعديل ذاتي
    SNAPSHOT = "snapshot"            # لقطة من السجل
    REPLICATION = "replication"      # حدث توزيع
    VERIFICATION = "verification"    # حدث تحقق
    GENESIS = "genesis"              # الحدث الأول
    TOOL_INVOKED = "tool_invoked"    # R-729 (البند ٣.١): استدعاء أداة مسجلة
    VAULT_ACCESS = "vault_access"    # R-752 (V5 ١.٥): فعل على خزينة الأسرار (بصمة فقط)
    AGENT_RUN = "agent_run"          # R-753 (V5 §٢): بدء/نهاية تشغيل حلقة الوكيل
    CONNECTOR_CALL = "connector_call"  # R-756 (V5 ٤.١): منحة/سحب/استدعاء موصل
    FLEET_EVENT = "fleet_event"        # R-758 (V5 §٥): إنشاء/إيقاف/تسليم عامل أسطول
    SKILL_LIFECYCLE = "skill_lifecycle"  # R-757 (V5 ٤.٢): اقتراح/تقييم/اعتماد/تراجع مهارة


class IntegrityStatus(str, Enum):
    """حالة سلامة السجل"""
    VERIFIED = "verified"
    CORRUPTED = "corrupted"
    PARTIAL = "partial"
    NOT_CHECKED = "not_checked"


# R-699: قيم مفتاح جذر علنية (فارغ، أو افتراضيات مكتوبة في الكود) — لا تصلح
# مفتاح تحقق: أي أحد يحسب HMAC بها. وجودها = لا مفتاح تاريخي (fail-closed).
_PUBLIC_WEAK_ROOT_KEYS = frozenset({
    b'',
    b'you_must_change_this_key_immediately',
    b'new_generated_key_here',
    'يجب_تغيير_هذا_المفتاح_فوراً'.encode('utf-8'),
})

# إعدادات التشفير
HASH_ALGORITHM = hashlib.sha256
HASH_SIZE = 32  # بايت
HMAC_ALGORITHM = hashlib.sha256
COMPRESSION_LEVEL = 6
MAX_BLOB_SIZE = 100 * 1024 * 1024  # 100 ميغابايت

# المسارات
CORE_DIR = DATA_DIR / "sovereign_core"

# R-771: لقطات حالة دورية تكتبها حلقات الخلفية ولا يقرؤها أي كود من السجل (مُتحقق:
# كل نوع له كاتب واحد ولا قارئ). على الإنتاج أغرقت السجل (~1 حدث/ث، 46,511 في يوم)
# فأنفدت ذاكرة الآلة (R-770). تُدمج: حدث واحد لكل نوع كل
# SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS (الافتراضي 300؛ 0 يعطّل)، والحدث المكتوب
# التالي يحمل عدد ما دُمج في `_coalesced_since_last`. أي نوع خارج القائمة لا يتأثر.
TELEMETRY_COALESCE_TYPES = frozenset({
    "defense::full_mutation", "attention::snapshot", "watcher::snapshot",
    "awareness::moment", "consciousness::moment",
    "self::snapshot", "introspection::snapshot", "identity::snapshot",
    "sovereign::will_snapshot", "alignment::snapshot", "controller::snapshot",
    "directives::snapshot", "homeostasis::snapshot", "predictive::snapshot",
    "risk::snapshot", "scenario::snapshot",
    "quantum::transition_applied", "quantum::transition_cycle_completed",
    "quantum::cycle_completed", "quantum::field_cycle", "quantum::superposition_cycle",
    "quantum::predictive_integration", "quantum::controller_cycle",
    "predictive::controller_cycle", "plasticity::cycle_completed",
    "instinct::cycle_completed", "drives::cycle_completed",
    "archetypes::cycle_completed", "biological::metabolic_cycle",
})
TELEMETRY_DEFAULT_MIN_INTERVAL_SECONDS = 300.0
BLOBS_DIR = CORE_DIR / "blobs"
LOG_FILE = CORE_DIR / "ledger.jsonl"
INDEX_FILE = CORE_DIR / "index.json"
META_FILE = CORE_DIR / "meta.json"
INTEGRITY_FILE = CORE_DIR / "integrity.json"
LOCK_FILE = CORE_DIR / ".lock"

# إنشاء المجلدات
for d in [CORE_DIR, BLOBS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ============================================================
# أدوات تشفيرية محترفة
# ============================================================

def utc_now_iso() -> str:
    """الوقت الحالي بتنسيق ISO 8601 مع UTC"""
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def sha256_hash(data: bytes) -> str:
    """تجزئة SHA-256 مع إرجاع hex"""
    return HASH_ALGORITHM(data).hexdigest()


def sha256_hash_bytes(data: bytes) -> bytes:
    """تجزئة SHA-256 مع إرجاع bytes"""
    return HASH_ALGORITHM(data).digest()


def compute_hmac(data: bytes, key: bytes) -> str:
    """حساب HMAC-SHA256"""
    return hmac.new(key, data, HMAC_ALGORITHM).hexdigest()


def verify_hmac(data: bytes, key: bytes, signature: str) -> bool:
    """التحقق من HMAC بشكل آمن (مقاوم للهجمات الزمنية)"""
    expected = compute_hmac(data, key)
    return hmac.compare_digest(expected, signature)


def compress_data(data: bytes) -> bytes:
    """ضغط البيانات مع zlib"""
    return zlib.compress(data, level=COMPRESSION_LEVEL)


def decompress_data(data: bytes) -> bytes:
    """فك ضغط البيانات"""
    return zlib.decompress(data)


def safe_json_dumps(obj: Any) -> str:
    """تحويل آمن إلى JSON مع ترتيب المفاتيح للتجزئة المتسقة"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


# ============================================================
# ملف القفل (للوصول الآمن في بيئة متعددة الخيوط/العمليات)
# ============================================================

class FileLock:
    """قفل بسيط للملفات لمنع الوصول المتزامن"""
    
    # M1: مدة صلاحية القفل — إذا كان القفل أقدم من هذا، يُعتبر قديماً (عملية انهارت)
    STALE_AFTER_SECONDS = 30.0
    
    def __init__(self, lock_file: Path, timeout: float = 30.0):
        self.lock_file = lock_file
        self.timeout = timeout
        self._acquired = False
    
    def __enter__(self):
        start = time.time()
        while True:
            try:
                self.lock_file.touch(exist_ok=False)
                self._acquired = True
                break
            except FileExistsError:
                # M1: كشف الأقفال القديمة (عملية انهارت وتركت القفل)
                try:
                    age = time.time() - self.lock_file.stat().st_mtime
                    if age > self.STALE_AFTER_SECONDS:
                        logger.warning(f"🧹 إزالة قفل قديم ({age:.0f}s) — عملية سابقة انهارت")
                        self.lock_file.unlink()
                        continue
                # TOLERATED: lock file vanished mid-check (race) — retry loop handles it (R-680)
                except FileNotFoundError:
                    continue
                # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
                except OSError:
                    pass
                if time.time() - start > self.timeout:
                    raise TimeoutError(f"لا يمكن الحصول على القفل: {self.lock_file}")
                time.sleep(0.1)
        return self
    
    def __exit__(self, *args):
        if self._acquired:
            try:
                self.lock_file.unlink()
            # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
            except FileNotFoundError:
                pass
            self._acquired = False


# ============================================================
# إدارة التخزين (Blobs) - المحتوى الموجه بالتجزئة
# ============================================================

class BlobStore:
    """تخزين المحتوى بتوجه التجزئة (Content-Addressable Storage)"""
    
    def __init__(self, blobs_dir: Path):
        self.blobs_dir = blobs_dir
        # M1: عدّادات مخزنة لتجنب فحص الدليل الكامل في كل عملية كتابة
        self._count = 0
        self._size = 0
        self._count_loaded = False
        self._scan()
    
    def _blob_path(self, blob_hash: str) -> Path:
        """مسار blob بناءً على أول حرفين من التجزئة"""
        prefix = blob_hash[:2]
        return self.blobs_dir / prefix / blob_hash
    
    def _ensure_prefix_dir(self, blob_hash: str) -> Path:
        """إنشاء دليل البادئة عند الكتابة فقط (M1: تجنب mkdir في كل قراءة)"""
        prefix = blob_hash[:2]
        prefix_dir = self.blobs_dir / prefix
        prefix_dir.mkdir(parents=True, exist_ok=True)
        return prefix_dir
    
    def put(self, data: bytes, compress: bool = True) -> str:
        """
        تخزين البيانات وإعادة التجزئة.
        إذا كانت البيانات موجودة مسبقاً، لا تُعيد التخزين.
        """
        # ضغط البيانات
        to_store = compress_data(data) if compress else data
        blob_hash = sha256_hash(to_store)
        
        path = self._blob_path(blob_hash)
        self._ensure_prefix_dir(blob_hash)
        
        # الكتابة الذرية (الكتابة في ملف مؤقت ثم النقل)
        if not path.exists():
            tmp_path = path.with_suffix('.tmp')
            with open(tmp_path, 'wb') as f:
                f.write(to_store)
                # R-763: تثبيت المحتوى قبل النقل — توقف الآلة لا يترك blob فارغًا
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            # M1: تحديث العدّادات المخزنة
            self._count += 1
            self._size += len(to_store)
            logger.debug(f"تم تخزين blob جديد: {blob_hash[:16]}... ({len(to_store)} بايت)")
        else:
            logger.debug(f"blob موجود مسبقاً: {blob_hash[:16]}...")
        
        return blob_hash
    
    def get(self, blob_hash: str, decompress: bool = True) -> bytes:
        """استرجاع البيانات من التجزئة"""
        path = self._blob_path(blob_hash)
        if not path.exists():
            raise FileNotFoundError(f"الـ blob غير موجود: {blob_hash}")
        
        with open(path, 'rb') as f:
            data = f.read()
        
        return decompress_data(data) if decompress else data
    
    def exists(self, blob_hash: str) -> bool:
        """التحقق من وجود blob"""
        return self._blob_path(blob_hash).exists()
    
    def verify_content_hash(self, blob_hash: str) -> bool:
        """
        R-648: التحقق من أن محتوى blob يُطابق تجزئته.
        
        يقرأ البيانات المضغوطة و يُعيد حساب التجزئة — إذا تغيّر المحتوى
        (تزييف)، التجزئة لن تُطابق blob_hash المُسجل.
        """
        path = self._blob_path(blob_hash)
        if not path.exists():
            return False
        try:
            with open(path, "rb") as f:
                stored = f.read()
            actual_hash = sha256_hash(stored)
            return actual_hash == blob_hash
        except Exception:
            return False
    
    def delete(self, blob_hash: str) -> bool:
        """حذف blob (نادراً ما يُستخدم، السيادة تعني عدم الحذف)"""
        path = self._blob_path(blob_hash)
        if path.exists():
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            path.unlink()
            # M1: تحديث العدّادات المخزنة
            self._count = max(0, self._count - 1)
            self._size = max(0, self._size - size)
            logger.warning(f"تم حذف blob: {blob_hash[:16]}... (هذا نادر في النظام السيادي)")
            return True
        return False
    
    def _scan(self):
        """فحص كامل للدليل (مرة واحدة عند التهيئة)"""
        count = 0
        size = 0
        for blob_dir in self.blobs_dir.iterdir():
            if blob_dir.is_dir():
                for blob_file in blob_dir.iterdir():
                    count += 1
                    try:
                        size += blob_file.stat().st_size
                    # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
                    except OSError:
                        pass
        self._count = count
        self._size = size
        self._count_loaded = True
    
    def size(self) -> int:
        """الحجم الإجمالي للتخزين بالبايت (مخزّن، O(1))"""
        if not self._count_loaded:
            self._scan()
        return self._size
    
    def count(self) -> int:
        """عدد الـ blobs (مخزّن، O(1))"""
        if not self._count_loaded:
            self._scan()
        return self._count


# ============================================================
# الفهرس (للبحث السريع)
# ============================================================

INDEX_SAVE_INTERVAL_ENV = "SOVEREIGN_INDEX_SAVE_INTERVAL"
_DEFAULT_INDEX_SAVE_INTERVAL = 5.0


def _index_save_interval() -> float:
    """R-762: أقصى فاصل (ثوانٍ) بين حفظات الفهرس. 0 = حفظ مع كل حدث (السلوك القديم)."""
    raw = os.environ.get(INDEX_SAVE_INTERVAL_ENV)
    if raw is None or raw.strip() == "":
        return _DEFAULT_INDEX_SAVE_INTERVAL
    try:
        return max(0.0, float(raw))
    except ValueError:
        logger.warning(f"R-762: قيمة {INDEX_SAVE_INTERVAL_ENV} غير صالحة ({raw!r}) — الافتراضي")
        return _DEFAULT_INDEX_SAVE_INTERVAL


import weakref as _weakref
import atexit as _atexit

_LIVE_INDEXES: "_weakref.WeakSet" = _weakref.WeakSet()


def _flush_all_indexes() -> None:
    """R-762: عند إيقاف العملية تُفرَّغ كل الفهارس المعلّقة (لا فقد عند الإيقاف النظيف)."""
    for idx in list(_LIVE_INDEXES):
        try:
            idx.flush()
        except Exception as e:  # TOLERATED: إيقاف — الإقلاع التالي يعيد البناء من السجل
            logger.error(f"R-762: فشل تفريغ الفهرس عند الإيقاف: {e}")


_atexit.register(_flush_all_indexes)


class SovereignIndex:
    """فهرس متطور للبحث السريع في السجل السيادي"""
    
    def __init__(self, index_file: Path):
        self.index_file = index_file
        self.data: Dict[str, Any] = {}
        # R-762: خنق حفظ الفهرس — كان يُعاد كتابته كاملًا مع كل حدث (O(n) لكل
        # إلحاق) فأشبع المعالج على الإنتاج. الفهرس ذاكرة مؤقتة قابلة لإعادة
        # البناء من السجل (والإقلاع يعيد بناءه إن تأخر)، فالخنق لا يفقد شيئًا.
        self._dirty = False
        self._last_save = 0.0
        self._save_interval = _index_save_interval()
        self._load()
        _LIVE_INDEXES.add(self)
    
    def _load(self):
        """تحميل الفهرس من القرص"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"فشل تحميل الفهرس: {e}")
                self.data = self._empty_index()
        else:
            self.data = self._empty_index()
    
    def _empty_index(self) -> Dict[str, Any]:
        return {
            "by_hash": {},
            "by_type": {},
            "by_user": {},
            "by_time_range": [],
            "events_count": 0,
            "first_event": None,
            "last_event": None,
            "last_hash": None,
            "updated_at": utc_now_iso()
        }
    
    def save(self):
        """حفظ الفهرس إلى القرص — R-762: ذري (tmp + replace) ومضغوط بلا indent."""
        self.data["updated_at"] = utc_now_iso()
        tmp = self.index_file.with_name(self.index_file.name + ".tmp")
        # R-772: مرمّز C دفعة واحدة (json.dumps) لا المتدفق (json.dump) — المتدفق مكتوب بـ
        # Python ويتخلى عن قفل المفسّر بين القطع، فامتد دقائق على الإنتاج وقفل السجل محتجز
        # (73× محليًا تحت 60 خيطًا). وfsync قبل الاستبدال: بلاه ترك قتلُ العملية فهرسًا صفريًا.
        payload = json.dumps(self.data, ensure_ascii=False, separators=(",", ":"))
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.index_file)
        self._dirty = False
        self._last_save = time.monotonic()

    def flush(self):
        """R-762: حفظ أي تغييرات معلّقة (يُستدعى عند الإيقاف وبعد إعادة البناء)."""
        if self._dirty:
            self.save()

    def _maybe_save(self):
        self._dirty = True
        if time.monotonic() - self._last_save >= self._save_interval:
            self.save()
    
    def add_event(self, event_hash: str, event_type: str, event_time: str, 
                  prev_hash: str, user: Optional[str] = None):
        """إضافة حدث إلى الفهرس"""
        # حسب التجزئة
        self.data["by_hash"][event_hash] = {
            "type": event_type,
            "time": event_time,
            "prev_hash": prev_hash,
            "user": user
        }
        
        # حسب النوع
        self.data["by_type"].setdefault(event_type, []).append(event_hash)
        
        # حسب المستخدم
        if user:
            self.data["by_user"].setdefault(user, []).append(event_hash)
        
        # إحصائيات
        self.data["events_count"] += 1
        
        if self.data["first_event"] is None:
            self.data["first_event"] = event_hash
        
        self.data["last_event"] = event_hash
        
        # الحد من طول القوائم (الاحتفاظ بآخر 10,000 لكل نوع)
        for t in self.data["by_type"]:
            if len(self.data["by_type"][t]) > 10000:
                self.data["by_type"][t] = self.data["by_type"][t][-10000:]
        
        # R-762: حفظ مخنوق بدل إعادة كتابة كاملة مع كل حدث
        self._maybe_save()
    
    def get_event(self, event_hash: str) -> Optional[Dict[str, Any]]:
        """الحصول على معلومات الحدث من الفهرس"""
        return self.data["by_hash"].get(event_hash)
    
    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[str]:
        """الحصول على قائمة تجزئات الأحداث حسب النوع"""
        hashes = self.data["by_type"].get(event_type, [])
        return hashes[-limit:] if limit > 0 else hashes
    
    def get_events_by_user(self, user: str, limit: int = 100) -> List[str]:
        """الحصول على قائمة تجزئات الأحداث حسب المستخدم"""
        hashes = self.data["by_user"].get(user, [])
        return hashes[-limit:] if limit > 0 else hashes
    
    def get_statistics(self) -> Dict[str, Any]:
        """إحصائيات الفهرس"""
        return {
            "total_events": self.data["events_count"],
            "total_types": len(self.data["by_type"]),
            "total_users": len(self.data["by_user"]),
            "first_event": self.data["first_event"],
            "last_event": self.data["last_event"],
            "updated_at": self.data["updated_at"]
        }


# ============================================================
# السجل السيادي (القلب)
# ============================================================

class SovereignCore:
    """
    قلب الذاكرة السيادية.
    
    هذا الملف هو هوية الذاكرة نفسها.
    لا يمكن تعديله. لا يمكن حذفه. فقط يمكن إضافة أحداث إليه.
    """
    
    def __init__(self, 
                 log_file: Path = LOG_FILE,
                 blobs_dir: Path = BLOBS_DIR,
                 index_file: Path = INDEX_FILE,
                 meta_file: Path = META_FILE,
                 integrity_file: Path = INTEGRITY_FILE,
                 sovereign_key: str = SOVEREIGN_KEY,  # LEGACY-ROOT-KEY (read-only): تحقق الأحداث التاريخية فقط
                 keyring=None):
        
        self.log_file = log_file
        self.meta_file = meta_file
        self.integrity_file = integrity_file

        # المكونات الداخلية
        self.blob_store = BlobStore(blobs_dir)
        self.index = SovereignIndex(index_file)

        # مفتاح التوقيع — R-697: LEGACY-ROOT-KEY (read-only). هذا المفتاح لا يوقّع
        # أحداثًا جديدة قطعًا (التوقيع الجديد fail-closed عبر KeyRing — R-626)؛ يُستخدم
        # فقط في التحقق من أحداث ledger التاريخية الموقعة بالجذر قبل R-697.
        # R-699 (fail-closed): مفتاح جذر فارغ أو قيمة افتراضية علنية من الكود →
        # لا مفتاح تحقق تاريخي إطلاقًا (None). كان يُستبدل بثابت علني
        # فيُعلن verify_integrity حدثًا تاريخيًا مزوّرًا VERIFIED.
        _root = sovereign_key.encode('utf-8') if sovereign_key else b''
        if _root in _PUBLIC_WEAK_ROOT_KEYS:
            logger.warning(
                "R-699: لا مفتاح جذر تاريخي حقيقي — الأحداث التاريخية (بلا key_id) "
                "لن تُعلن VERIFIED (PARTIAL)"
            )
            self.signing_key = None
        else:
            self.signing_key = _root

        # R-618/R-629: KeyRing — ربط الأحداث الجديدة بمفتاحها في KeyRing
        # (حتى تكون قابلة للتحقق لاحقًا، بدل unverifiable_missing_key)
        # R-629: حقن صريح — إذا مُرر keyring، يُستخدم (لا تحميل تلقائي).
        # إذا لم يُمرر، يُحمّل من المسار الافتراضي (fallback R-621 معطل في الاختبارات
        # عبر تعطيل SOVEREIGN_KEYRING_FALLBACK).  # LEGACY-ROOT-KEY (read-only): اسم متغير بيئة لا مفتاح
        self._keyring = None
        self._keyring_key_id = None
        if keyring is not None:
            # R-629: حقن صريح — KeyRing مُمرر (لا تحميل تلقائي، لا fallback)
            self._keyring = keyring
            active = keyring.get_active_key()
            if active is not None:
                self._keyring_key_id = active.key_id
                logger.info(f"🔑 KeyRing injected: {active.key_id}")
            else:
                logger.warning("⚠️ Injected KeyRing has no active key — events will be unverifiable")
        elif not os.environ.get("SOVEREIGN_KEYRING_FALLBACK_DISABLED"):  # LEGACY-ROOT-KEY (read-only): إعداد تحميل لا مفتاح
            # التحميل الافتراضي (التشغيل العادي — fallback R-621 يقرأ من المسار الحقيقي)
            try:
                from backend.sovereign.keys import KeyRing
                kr = KeyRing()
                kr.load_from_disk()
                active = kr.get_active_key()
                if active is not None:
                    self._keyring = kr
                    self._keyring_key_id = active.key_id
                    logger.info(f"🔑 KeyRing linked: {active.key_id}")
                else:
                    logger.warning("⚠️ KeyRing has no active key — events will be unverifiable")
            except Exception as e:
                logger.warning(f"⚠️ KeyRing not available: {e}")
        else:
            # R-629: fallback معطل (بيئة اختبار) — لا تحميل تلقائي
            logger.info("🔑 KeyRing fallback disabled (SOVEREIGN_KEYRING_FALLBACK_DISABLED) — no auto-load")  # LEGACY-ROOT-KEY (read-only): إعداد تحميل

        # حالة السجل
        self._last_hash = self._load_last_hash()
        # R-762: الفهرس مخنوق الحفظ — إن تأخر عن السجل (انقطاع قبل التفريغ)
        # يُعاد بناؤه من السجل عند الإقلاع (السجل هو الحقيقة، الفهرس ذاكرة مؤقتة)
        self._reconcile_index_with_ledger()
        # M1: ذاكرة مؤقتة لنتيجة التحقق من سلامة السجل
        self._integrity_cache = None
        self._integrity_prefix = None  # R-768: نقطة استئناف التحقق (بصمة البادئة)
        # R-769: فحص واحد في وقت واحد — المتصلون المتزامنون ينتظرون النتيجة المخزنة
        self._integrity_lock = threading.RLock()
        self._genesis_created = self._load_genesis_status()
        
        logger.info(f"✅ نواة الذاكرة السيادية جاهزة")
        logger.info(f"   - السجل: {self.log_file}")
        logger.info(f"   - آخر تجزئة: {self._last_hash[:16]}...")
        logger.info(f"   - عدد الأحداث: {self.index.data['events_count']}")
        logger.info(f"   - عدد الـ blobs: {self.blob_store.count()}")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة للسجل السيادي
    # -------------------------
    def reset(self, preserve_events: bool = False):
        """
        إعادة تهيئة كاملة للسجل السيادي.
        
        Args:
            preserve_events: إذا True، يحتفظ بالأحداث ولا يمسحها
        """
        logger.info("🔄 إعادة تهيئة السجل السيادي...")
        
        if not preserve_events:
            # مسح ملف السجل
            if self.log_file.exists():
                # نسخ احتياطي قبل المسح
                backup_file = self.log_file.with_suffix('.jsonl.bak')
                import shutil
                shutil.copy2(self.log_file, backup_file)
                self.log_file.unlink()
                logger.debug(f"📁 تم حذف ملف السجل، نسخة احتياطية في {backup_file}")
            
            # إعادة إنشاء ملف فارغ
            self.log_file.touch()
            
            # إعادة تعيين الحالة الداخلية
            self._last_hash = "GENESIS"
            self._genesis_created = False
            
            # إعادة إنشاء حدث البداية
            self._create_genesis_event()
        
        # إعادة تعيين الفهرس — R-606: إعادة بناء من السجل بدل تحميل فهرس قديم
        self.index = self._rebuild_index()
        
        # إعادة تعيين الميتا
        self._save_meta()
        
        # تسجيل حدث إعادة التهيئة
        self.append_event(
            event_type=EventType.SELF_MODIFY,
            payload={
                "timestamp": time.time(),
                "preserve_events": preserve_events,
                "status": "sovereign_core_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة السجل السيادي اكتملت")
    
    def _load_last_hash(self) -> str:
        """تحميل آخر تجزئة من السجل (مصدر الحقيقة) أو الميتا"""
        # M1: السجل هو مصدر الحقيقة — الميتا قد تكون قديمة
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    last_hash = "GENESIS"
                    corrupt = 0
                    blank = 0
                    for line in f:
                        line = line.strip()
                        if not line:
                            blank += 1
                            continue
                        # R-763: سطر تالف (كتابة ممزقة) لا يُسقط السجل كله إلى الميتا —
                        # آخر حدث سليم هو الحقيقة، والسطر التالف يبقى مرئيًا (invalid)
                        try:
                            last_event = json.loads(line)
                        except ValueError:
                            corrupt += 1
                            continue
                        last_hash = last_event.get('hash', last_hash)
                    self._ledger_nonevent_lines = corrupt + blank
                    if corrupt:
                        logger.error(
                            f"R-763: {corrupt} سطر تالف في السجل (كتابة ممزقة؟) — "
                            f"السلسلة تستمر من آخر حدث سليم؛ الأسطر التالفة باقية كما هي"
                        )
                    return last_hash
            # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
            except:
                pass
        
        # إذا لم يوجد سجل، نقرأ من الميتا
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    return meta.get('last_hash', 'GENESIS')
            # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
            except:
                pass
        
        return 'GENESIS'
    def _tail_last_hash(self) -> Optional[str]:
        """R-698 (تصويب): آخر تجزئة من ذيل الملف على القرص (قراءة عكسية
        بأجزاء — لا مسح كامل). يُعيد "GENESIS" لملف غائب/فارغ، وNone إن
        تعذّرت القراءة أو كان السطر الأخير بلا تجزئة (يُبقي المستدعي قيمته)."""
        try:
            if not self.log_file.exists():
                return "GENESIS"
            with open(self.log_file, 'rb') as f:
                f.seek(0, 2)
                pos = f.tell()
                buf = b""
                while pos > 0:
                    step = min(65536, pos)
                    pos -= step
                    f.seek(pos)
                    buf = f.read(step) + buf
                    lines = [l for l in buf.split(b"\n") if l.strip()]
                    # سطر كامل مضمون: إما وصلنا البداية أو يوجد سطران فأكثر
                    if lines and (pos == 0 or len(lines) >= 2):
                        return json.loads(lines[-1].decode('utf-8')).get('hash')
                return "GENESIS"
        # TOLERATED: tail read failure → caller keeps its cached hash (R-698)
        except Exception as e:
            logger.warning(f"R-698: tail last-hash read failed: {e}")
            return None

    def _ledger_contains_hash(self, event_hash: str) -> bool:
        """R-701: هل تجزئة الحدث موجودة في الملف؟ (GENESIS دائمًا) — مسح كامل،
        يُستدعى فقط حين يختلف ذيل القرص عن الذاكرة (كاتب آخر — حالة نادرة)."""
        if event_hash == "GENESIS":
            return True
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        if json.loads(line).get('hash') == event_hash:
                            return True
                    # TOLERATED: malformed line — not a match; verify_* reports it (R-701)
                    except ValueError:
                        continue
        except OSError as e:
            logger.error(f"R-701: ledger scan failed: {e}")
        return False

    def _load_genesis_status(self) -> bool:
        """التحقق من وجود حدث البداية"""
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    return meta.get('genesis_created', False)
            # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
            except:
                pass
        return self.log_file.exists()
    
    def _create_genesis_event(self):
        """إنشاء حدث البداية (الحدث الأول في السجل)"""
        logger.info("🌱 إنشاء حدث البداية (Genesis)...")
        
        genesis_payload = {
            "message": "بداية السجل السيادي",
            "version": "1.0.0",
            "created_at": utc_now_iso(),
            "creator": "sovereign_core"
        }
        
        event = self.append_event(
            event_type=EventType.GENESIS,
            payload=genesis_payload
        )
        
        logger.info(f"✅ تم إنشاء حدث البداية: {event['hash'][:16]}...")
    
    def _save_meta(self):
        """حفظ البيانات الوصفية"""
        meta = {
            "last_hash": self._last_hash,
            "genesis_created": True,
            "last_updated": utc_now_iso(),
            "events_count": self.index.data['events_count'],
            "blobs_count": self.blob_store.count(),
            "blobs_size_bytes": self.blob_store.size()
        }
        
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    
    def _compute_event_hash(self, prev_hash: str, blob_hash: str, 
                            event_time: str, event_type: str) -> str:
        """حساب تجزئة الحدث (هوية الحدث)"""
        canonical = f"{prev_hash}|{blob_hash}|{event_time}|{event_type}"
        return sha256_hash(canonical.encode('utf-8'))
    
    def _compute_event_signature(self, event_hash: str, prev_hash: str, 
                                  blob_hash: str, event_time: str, 
                                  event_type: str,
                                  key_id: Optional[str] = None) -> str:
        """حساب توقيع الحدث (لضمان عدم التلاعب)
        
        R-625: التوقيع يُشتق من مفتاح KeyRing المحدد في key_id —
        - للكتابة: key_id = المفتاح النشط (self._keyring_key_id)
        - للتحقق: key_id = event['key_id'] (وليس المفتاح النشط الحالي)
        هذا يضمن أن أحداث المفتاح A تُتحقق بنجاح بعد الدوران إلى B.
        
        R-626: إذا تعذر الحصول على مفتاح KeyRing صالح، يُرفض الإلحاق
        (لا fallback إلى مفتاح الإعدادات تحت هوية مفتاح KeyRing).
        """
        key_id_part = key_id if key_id is not None else ""
        data = f"{event_hash}|{prev_hash}|{blob_hash}|{event_time}|{event_type}|{key_id_part}"
        
        # R-625: تحديد المفتاح المستخدم — من key_id المُمرر (وليس المفتاح النشط)
        _use_key_id = key_id if key_id is not None else self._keyring_key_id
        
        if self._keyring is not None and _use_key_id:
            try:
                key_record = self._keyring.get_key(_use_key_id)
                if key_record is not None and hasattr(key_record, 'private_key') and key_record.private_key is not None:
                    # R-698: توقيع حسب نوع المفتاح — Ed25519 للمفاتيح الجديدة،
                    # HMAC للمفاتيح التاريخية (نفس البيانات المعيارية — لا تغيير صيغة)
                    if getattr(key_record, 'key_type', 'hmac') == 'ed25519':
                        try:
                            from backend.sovereign.keys import ed25519_verifier as _ed
                        except ImportError:
                            from sovereign.keys import ed25519_verifier as _ed
                        return _ed.sign_hex(data.encode('utf-8'), key_record.private_key)
                    # توقيع HMAC بالمفتاح الخاص من KeyRing
                    import hmac as _hmac
                    key_bytes = key_record.private_key.encode('utf-8') if isinstance(key_record.private_key, str) else key_record.private_key
                    return _hmac.new(key_bytes, data.encode('utf-8'), __import__('hashlib').sha256).hexdigest()
                else:
                    # R-626: مفتاح KeyRing غير صالح (غير موجود أو بدون private_key)
                    # — فشل مُغلق (لا fallback إلى مفتاح الإعدادات تحت هوية KeyRing)
                    raise KeyError(
                        f"R-626: KeyRing key {_use_key_id} not available for signing "
                        f"(not found or private_key is None) — refusing to sign "
                        f"with config key under KeyRing identity"
                    )
            except KeyError:
                # R-626: إعادة رفع فشل التوقيع (فشل مُغلق — لا fallback)
                raise
            except Exception as e:
                logger.warning(f"⚠️ KeyRing signing failed: {e}")
                # R-626: فشل مُغلق — لا fallback إلى مفتاح الإعدادات
                raise
        
        # R-626: لا مفتاح KeyRing متاح — فشل مُغلق
        # (لا يُوقّع بمفتاح الإعدادات تحت هوية مفتاح KeyRing)
        raise RuntimeError(
            "R-626: No KeyRing key available for signing — refusing to sign "
            "with config key (fail-closed). Initialize KeyRing with an active key "
            "before appending events."
        )
    
    def _get_current_signing_key_id(self) -> Optional[str]:
        """
        R-632: يُعيد المفتاح النشط الحالي من KeyRing (في كل كتابة).
        
        - يتحقق من صلاحية المفتاح للكتابة (ACTIVE، غير COMPROMISED/RETIRED)
        - يُعيد None إذا لم يوجد مفتاح صالح (فشل مُغلق في التوقيع)
        """
        if self._keyring is None:
            return None
        
        try:
            active = self._keyring.get_active_key()
            if active is None:
                return None
            
            # R-632: تحقق من صلاحية المفتاح للكتابة
            # (ACTIVE فقط — COMPROMISED/RETIRED/LOST/EXPIRED لا يُستخدم للكتابة)
            from backend.sovereign.keys.keyring import KeyStatus
            if active.status != KeyStatus.ACTIVE:
                logger.warning(
                    f"⚠️ Key {active.key_id} status={active.status} — not valid for writing"
                )
                return None
            
            # تحديث المفتاح المخزّن (يلتقط الدوران)
            self._keyring_key_id = active.key_id
            return active.key_id
        except Exception as e:
            logger.exception(f"R-682: Failed to get current signing key — silently swallowing. exc={e}")
            return None
    
    def _telemetry_gate(self, event_type_str: str) -> Optional[int]:
        """R-771: None = يُدمج (لا يُكتب)؛ عدد ≥ 0 = يُكتب ومعه عدد ما دُمج قبله."""
        try:
            interval = float(os.getenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS",
                                       TELEMETRY_DEFAULT_MIN_INTERVAL_SECONDS))
        except ValueError:
            interval = TELEMETRY_DEFAULT_MIN_INTERVAL_SECONDS
        if interval <= 0:
            return 0
        lock = self.__dict__.setdefault("_telemetry_lock", threading.Lock())
        with lock:
            last = self.__dict__.setdefault("_telemetry_last", {})
            suppressed = self.__dict__.setdefault("_telemetry_suppressed", {})
            now = time.monotonic()
            prev = last.get(event_type_str)
            if prev is not None and now - prev < interval:
                suppressed[event_type_str] = suppressed.get(event_type_str, 0) + 1
                return None
            last[event_type_str] = now
            return suppressed.pop(event_type_str, 0)

    def append_event(self, event_type: EventType, payload: Dict[str, Any],
                     user: Optional[str] = None) -> Dict[str, Any]:
        # M1: قبول EventType أو سلسلة نصية (كان ينهار على السلاسل)
        if isinstance(event_type, EventType):
            event_type_str = event_type.value
        else:
            event_type_str = str(event_type)
        # R-771: دمج اللقطات الدورية — قبل أي توقيع أو قفل أو كتابة
        if event_type_str in TELEMETRY_COALESCE_TYPES:
            coalesced = self._telemetry_gate(event_type_str)
            if coalesced is None:
                return {"hash": None, "coalesced": True, "type": event_type_str}
            if coalesced:
                payload = {**payload, "_coalesced_since_last": coalesced}
        """
        إضافة حدث جديد إلى السجل السيادي.
        
        هذه هي الطريقة الوحيدة لإضافة أي شيء إلى الذاكرة.
        لا حذف. لا تعديل. فقط إضافة.
        """
        with FileLock(LOCK_FILE):
            # 0) R-635: حارس الإلحاق — اختيار مفتاح صالح قبل أي حفظ دائم
            # (قبل blob_store.put — لا يُحفظ blob إذا فشل اختيار المفتاح)
            _current_key_id = self._get_current_signing_key_id()
            if _current_key_id is None:
                raise RuntimeError(
                    "R-635: No active signing key available (compromised/retired/lost "
                    "or no KeyRing) — refusing to append event BEFORE any persistent "
                    "save (fail-closed, guard before blob_store.put). "
                    "Generate or rotate an active key first."
                )
            
            # R-635: تحقق من مادة المفتاح غير الفارغة (قبل أي حفظ)
            _key_record = self._keyring.get_key(_current_key_id) if self._keyring else None
            if _key_record is None or not getattr(_key_record, 'private_key', None):
                raise RuntimeError(
                    f"R-635: Key {_current_key_id} has no private_key material — "
                    f"refusing to append event BEFORE any persistent save (fail-closed)."
                )
            
            # 1) تحويل الـ payload إلى JSON وتخزينه كـ blob
            payload_json = safe_json_dumps(payload)
            payload_bytes = payload_json.encode('utf-8')
            blob_hash = self.blob_store.put(payload_bytes, compress=True)
            
            # 1.5) R-698 (تصويب): مزامنة آخر تجزئة من القرص تحت القفل — كاتب
            # آخر (مثل KeyRotation أو نسخة نواة أخرى) قد ألحق حدثًا موسلسلًا؛
            # البناء على تجزئة الذاكرة القديمة كان يكسر سلسلة prev_hash.
            # R-701: المزامنة للأمام فقط — تُقبل التجزئة من القرص إن كانت
            # تجزئتنا المعروفة موجودة في الملف (الملف تقدّم بكاتب مشروع). ملف
            # تراجع (اقتُطع/أُعيدت كتابته) لا يُقبل: نُبقي التجزئة القديمة فيبقى
            # الكسر دليلًا (كان تصويب R-698 يقبله فيمحو دليل الاقتطاع).
            _disk_last = self._tail_last_hash()
            if _disk_last is not None and _disk_last != self._last_hash:
                if self._ledger_contains_hash(self._last_hash):
                    logger.info(
                        f"R-698: ledger advanced by another writer — resync "
                        f"{self._last_hash[:12]}… → {_disk_last[:12]}…"
                    )
                    self._last_hash = _disk_last
                else:
                    logger.error(
                        f"R-701 [SECURITY]: ledger rewound or rewritten — known last "
                        f"hash {self._last_hash[:12]}… not in file; NOT resyncing "
                        f"(chain break preserved as tamper evidence)"
                    )

            # 2) تحديد الوقت الحالي
            event_time = utc_now_iso()
            
            # 3) حساب تجزئة الحدث
            event_hash = self._compute_event_hash(
                self._last_hash, blob_hash, event_time, event_type_str
            )
            
            # 4) حساب التوقيع (R-632: بالمفتاح النشط الحالي — المُختار في الخطوة 0)
            signature = self._compute_event_signature(
                event_hash, self._last_hash, blob_hash, event_time, event_type_str,
                key_id=_current_key_id
            )
            
            # 5) بناء حدث السجل
            event = {
                "hash": event_hash,
                "prev_hash": self._last_hash,
                "blob": blob_hash,
                "time": event_time,
                "type": event_type_str,
                "signature": signature
            }
            # R-618/R-632: ربط الحدث بمفتاحه في KeyRing (المفتاح المستخدم فعليًا للتوقيع)
            # — يضمن أن key_id يطابق المفتاح المستخدم للتوقيع (لا هوية مزيّفة)
            if _current_key_id:
                event["key_id"] = _current_key_id
            # R-698: مؤشر نوع التوقيع للأحداث الجديدة الموقعة Ed25519 —
            # غيابه يعني المسار التاريخي HMAC (لا يُكتب للـhmac — الحدث
            # التاريخي يظل بصيغته تمامًا)
            if _key_record is not None and getattr(_key_record, 'key_type', 'hmac') == 'ed25519':
                event["sig_type"] = "ed25519"
            
            # 6) كتابة الحدث إلى السجل (JSONL)
            event_line = json.dumps(event, ensure_ascii=False)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(event_line + '\n')
                # R-763: تثبيت السطر قبل الميتا/الفهرس — حادثة إنتاج: توقف الآلة
                # ترك 2059 بايت NUL وفقد أحداثًا والميتا تشير إليها
                f.flush()
                os.fsync(f.fileno())
            
            # 7) تحديث الحالة الداخلية
            self._last_hash = event_hash
            # R-613: لا نبطل ذاكرة التحقق عند كل إضافة — السجل يتغير باستمرار
            # (لقطات الخلفية كل ثوانٍ)، والإبطال يجعل كل استدعاء يعيد فحص
            # السجل كاملاً (9141+ حدثاً ≈ 2.5 ثانية). مهلة الـ 60 ثانية
            # في verify_integrity تكفي لضمان عدم تقديم نتيجة قديمة أكثر من دقيقة.
            
            # 8) تحديث الفهرس
            self.index.add_event(
                event_hash=event_hash,
                event_type=event_type_str,
                event_time=event_time,
                prev_hash=event["prev_hash"],
                user=user
            )
            
            # 9) حفظ الميتا بعد الفهرس (R-606: عدّاد الأحداث متسق)
            self._save_meta()
            
            logger.info(f"📝 حدث جديد: {event_type_str} | {event_hash[:16]}... | المستخدم: {user or 'system'}")
            
            return event
    
    @staticmethod
    def _parse_ledger_line(line: str) -> Optional[Dict[str, Any]]:
        """R-766: تحليل سطر سجل واحد — السطر التالف (كتابة ممزقة/NUL/جزئي) يعيد None.

        القرّاء يتخطونه ولا يمسّونه (إلحاقي — سياسة R-763). كان `json.loads` المباشر
        يُسقط `iterate_events` فتفشل `MemoryViews` ونحو 20 مكونًا عند الإقلاع.
        """
        try:
            obj = json.loads(line)
        except ValueError:
            return None
        return obj if isinstance(obj, dict) else None

    def get_event(self, event_hash: str) -> Optional[Dict[str, Any]]:
        """استرجاع حدث من السجل"""
        if not self.log_file.exists():
            return None
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = self._parse_ledger_line(line)
                if event is not None and event.get('hash') == event_hash:
                    return event
        return None
    
    def get_payload(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """استرجاع الـ payload الفعلي للحدث"""
        blob_hash = event.get('blob')
        if not blob_hash:
            return {"_error": "لا يوجد blob في الحدث"}
        
        try:
            data = self.blob_store.get(blob_hash, decompress=True)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            return {"_error": f"فشل استرجاع الـ payload: {str(e)}"}
    
    def iterate_events(self, reverse: bool = False, 
                       from_hash: Optional[str] = None,
                       limit: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        """التكرار عبر الأحداث في السجل"""
        if not self.log_file.exists():
            return
        
        # R-606: مسار سريع — قراءة الذيل فقط عند طلب الأحدث (reverse + limit)
        # يتجنب قراءة السجل الكامل في الذاكرة في كل استدعاء (كان O(n) لكل استدعاء)
        if reverse and limit is not None and not from_hash:
            try:
                with open(self.log_file, 'rb') as f:
                    f.seek(0, 2)
                    size = f.tell()
                    # اقرأ آخر ~64KB كافية لعدد limit من الأحداث (كل حدث ~400 بايت)
                    read_size = min(size, max(4096, limit * 1024))
                    f.seek(size - read_size)
                    tail = f.read().decode('utf-8', errors='replace')
                lines = [l for l in tail.split('\n') if l.strip()]
                # R-766: السطر الجزئي الأول والأسطر التالفة تُتخطى (لا تُسقط المسار)
                events = [e for e in map(self._parse_ledger_line, lines) if e is not None]
                # قد نكون بدأنا في منتصف سطر — تجاهل أول عنصر غير مكتمل
                if len(events) > limit:
                    events = events[-limit:]
                for event in reversed(events):
                    yield event
                return
            # TOLERATED: fast-path read failure → fall back to full read (R-680d)
            except Exception:
                pass
        
        events = []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = self._parse_ledger_line(line)
                if event is not None:  # R-766: السطر التالف يُتخطى
                    events.append(event)
        
        if reverse:
            events.reverse()
        
        start_index = 0
        if from_hash:
            for i, e in enumerate(events):
                if e.get('hash') == from_hash:
                    start_index = i + (0 if reverse else 1)
                    break
        
        # M1: دعم حد أقصى لعدد الأحداث
        end_index = None
        if limit is not None:
            end_index = start_index + limit
        
        for event in events[start_index:end_index]:
            yield event
    
    def verify_content_integrity(self) -> "IntegrityStatus":
        """
        R-639: سلامة المحتوى فقط — فصل سلامة المحتوى عن قابلية توثيق التوقيع.
        
        يتحقق من:
        - سلسلة التجزئة (prev_hash متصل)
        - تجزئة الحدث (hash متطابقة)
        - وجود الـ blobs
        
        لا يتحقق من التوقيعات (غياب المفتاح التاريخي ليس إثبات تلاعب —
        راجع verify_signatures_report للتقرير المنفصل).
        """
        if not self.log_file.exists():
            logger.warning("السجل غير موجود")
            return IntegrityStatus.NOT_CHECKED
        
        prev_hash = "GENESIS"
        event_count = 0
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    event = json.loads(line)
                    event_count += 1
                    
                    # 1) التحقق من prev_hash (سلسلة متصلة)
                    if event.get('prev_hash') != prev_hash:
                        logger.error(f"❌ فشل في السطر {line_num}: prev_hash غير متطابق")
                        return IntegrityStatus.CORRUPTED
                    
                    # 2) التحقق من تجزئة الحدث
                    expected_hash = self._compute_event_hash(
                        event['prev_hash'], event['blob'], event['time'], event['type']
                    )
                    if event['hash'] != expected_hash:
                        logger.error(f"❌ فشل في السطر {line_num}: تجزئة الحدث غير متطابقة")
                        return IntegrityStatus.CORRUPTED
                    
                    # 3) التحقق من وجود الـ blob و محتواه (R-648 — hash)
                    if not self.blob_store.verify_content_hash(event['blob']):
                        logger.error(f"❌ فشل في السطر {line_num}: blob غير موجود أو محتواه مُعدّل: {event['blob'][:16]}...")
                        return IntegrityStatus.CORRUPTED
                    
                    prev_hash = event['hash']
                except json.JSONDecodeError:
                    logger.error(f"❌ فشل في السطر {line_num}: JSON غير صالح")
                    return IntegrityStatus.CORRUPTED
                except KeyError as e:
                    logger.error(f"❌ فشل في السطر {line_num}: حقل مفقود {e}")
                    return IntegrityStatus.CORRUPTED
        
        if event_count == 0:
            logger.warning("السجل فارغ")
            return IntegrityStatus.NOT_CHECKED
        
        logger.info(f"✅ سلامة المحتوى: {event_count} حدث، السلسلة متصلة")
        return IntegrityStatus.VERIFIED
    
    def verify_signatures_report(self) -> dict:
        """
        R-639: تقرير التوقيعات المنفصل — فصل قابلية توثيق التوقيع عن سلامة المحتوى.
        
        يُعيد تقريرًا (وليس IntegrityStatus):
        - total: إجمالي الأحداث
        - verified: أحداث مُتحقّقة (مفتاح معروف، توقيع صحيح)
        - unverifiable_missing_key: أحداث بمفتاح غير معروف (ليس إثبات تلاعب)
        - invalid: أحداث بمفتاح معروف لكن التوقيع لا يطابق (مؤشر تلاعب)
        - legacy_pre_keyring: أحداث تاريخية (بلا key_id)
        """
        report = {
            "total": 0,
            "verified": 0,
            "unverifiable_missing_key": 0,
            "invalid": 0,
            "legacy_pre_keyring": 0,
            "malformed_json": 0,
            "execution_errors": 0,
        }
        
        if not self.log_file.exists():
            logger.warning("السجل غير موجود")
            return report
        
        # تحميل KeyRing (إن وُجد)
        keyring = None
        if self._keyring is not None:
            keyring = self._keyring
        else:
            try:
                from backend.sovereign.keys import KeyRing as _KR
                kr = _KR()
                kr.load_from_disk()
                if kr.get_active_key() is not None:
                    keyring = kr
            # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
            except Exception:
                pass
        
        from backend.sovereign.keys import SignatureVerifier
        verifier = SignatureVerifier(keyring) if keyring else None
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                report["total"] += 1
                
                # R-645: تصنيف منفصل للأخطاء (ليس كلها مفتاح مفقود)
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    # JSON غير صالح — حالة بنيوية (ليست مفتاح مفقود)
                    report["malformed_json"] += 1
                    continue
                
                try:
                    if verifier is None:
                        # لا KeyRing — كل الأحداث unverifiable (ليس إثبات تلاعب)
                        if "key_id" in event:
                            report["unverifiable_missing_key"] += 1
                        else:
                            report["legacy_pre_keyring"] += 1
                        continue
                    
                    result = verifier.verify_event(event)
                    status_val = result.status.value
                    if status_val == "verified":
                        report["verified"] += 1
                    elif status_val == "unverifiable_missing_key":
                        if "key_id" in event:
                            report["unverifiable_missing_key"] += 1
                        else:
                            report["legacy_pre_keyring"] += 1
                    elif status_val == "invalid":
                        report["invalid"] += 1
                except KeyError as e:
                    # حقل مفقود في الحدث — حالة بنيوية
                    report["malformed_json"] += 1
                except Exception:
                    # خطأ تنفيذ (ليس مفتاح مفقود)
                    report["execution_errors"] += 1
        
        logger.info(
            f"📋 تقرير التوقيعات: {report['total']} إجمالي، "
            f"{report['verified']} مُتحقّق، {report['invalid']} غير صالح، "
            f"{report['unverifiable_missing_key']} بمفتاح غير معروف، "
            f"{report['legacy_pre_keyring']} تاريخي"
        )
        return report
    
    def verify_integrity(self, verbose: bool = False) -> IntegrityStatus:
        """
        التحقق من سلامة السجل بأكمله.
        - يتحقق من سلسلة التجزئة.
        - يتحقق من التوقيعات.
        - يتحقق من وجود الـ blobs.
        """
        # M1: تخزين مؤقت للتحقق — لا نعيد فحص السجل الكامل في كل استعلام حالة
        # R-606: يُعاد التحقق فقط إذا تغيّر السجل (آخر تجزئة) أو انقضت المهلة (60 ثانية)
        # R-701: المهلة وحدها تحكم الذاكرة — كان تطابق _last_hash في الذاكرة
        # يعيد النتيجة بلا حد زمني، فتعديل سطر سابق أو إلحاق كاتب آخر لا يُرى أبدًا.
        # R-768: كل نتيجة تُخزَّن للمهلة (كانت VERIFIED وحدها — فـCORRUPTED يعيد فحص كل
        # التوقيعات في كل استدعاء ويُشبع المعالج على الإنتاج)، وبعدها يُستأنف من آخر موضع
        # متحقق منه ما دامت بصمة البادئة والمفاتيح لم تتغير. verbose=True فحص كامل دائمًا.
        if not verbose and self._integrity_cache is not None:
            if (time.time() - self._integrity_cache.get("ts", 0)) < 60.0:
                return self._integrity_cache["status"]
        # R-769: بلا قفل كان كل خيط (drives/instincts/watcher...) يبدأ الفحص نفسه بالتوازي
        # عند الإقلاع أو انقضاء المهلة — قطيع متزاحم أشبع معالج الإنتاج بعد R-768.
        with self._integrity_lock:
            if not verbose and self._integrity_cache is not None:
                if (time.time() - self._integrity_cache.get("ts", 0)) < 60.0:
                    return self._integrity_cache["status"]  # أنجزه خيط سبقنا
            resume = None if verbose else self._integrity_resume_point()
            if resume is not None and resume["status"] is not None:
                # البادئة نفسها (حتى السطر الفاشل) لم تتغير → النتيجة نفسها، بلا إعادة تحقق
                return self._remember_integrity(resume["status"])
            status = self._verify_walk(verbose, resume)
            if status is None:  # الاستئناف لم يرَ آخر تجزئة معروفة في الذيل → فحص كامل
                status = self._verify_walk(verbose, None)
            return status

    def _keyring_fingerprint(self) -> str:
        """R-768: بصمة المفاتيح التي يعتمد عليها التحقق (تغيّرها يُبطل نقطة الاستئناف)."""
        parts = [f"root:{self.signing_key is not None}"]
        try:
            for rec in (self._keyring.list_keys() if self._keyring else []):
                parts.append(f"{getattr(rec, 'key_id', '')}|{getattr(rec, 'key_type', '')}|"
                             f"{getattr(rec, 'public_key', '')}")
        except Exception as e:  # TOLERATED: بلا بصمة مفاتيح → لا استئناف (فحص كامل)
            parts.append(f"err:{type(e).__name__}")
        return hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()

    def _prefix_sha256(self, length: int) -> Optional[str]:
        h = hashlib.sha256()
        remaining = length
        with open(self.log_file, 'rb') as fh:
            while remaining > 0:
                chunk = fh.read(min(1 << 20, remaining))
                if not chunk:
                    return None
                h.update(chunk)
                remaining -= len(chunk)
        return h.hexdigest()

    def _integrity_resume_point(self) -> Optional[Dict[str, Any]]:
        """R-768: نقطة استئناف صالحة فقط إن كانت البادئة المتحقق منها بايتًا ببايت كما هي."""
        st = getattr(self, "_integrity_prefix", None)
        if not st or not self.log_file.exists():
            return None
        try:
            if self.log_file.stat().st_size < st["offset"]:
                return None  # اقتطاع → فحص كامل
            if st["keys"] != self._keyring_fingerprint():
                return None
            if self._prefix_sha256(st["offset"]) != st["sha256"]:
                return None  # تعديل في البادئة → فحص كامل
        except OSError:
            return None
        return st

    def _remember_integrity(self, status: "IntegrityStatus") -> "IntegrityStatus":
        self._integrity_cache = {"status": status, "last_hash": self._last_hash,
                                 "checked_at": utc_now_iso(), "ts": time.time()}
        return status

    def _record_prefix(self, offset: int, prev_hash: str, count: int, line_num: int,
                       status: Optional["IntegrityStatus"]) -> None:
        try:
            self._integrity_prefix = {
                "offset": offset, "sha256": self._prefix_sha256(offset), "prev_hash": prev_hash,
                "count": count, "line_num": line_num, "status": status,
                "keys": self._keyring_fingerprint()}
        except OSError:
            self._integrity_prefix = None

    def _verify_walk(self, verbose: bool, resume: Optional[Dict[str, Any]]) -> Optional["IntegrityStatus"]:
        """جسم التحقق (R-768: يبدأ من نقطة الاستئناف إن وُجدت). None = أعد فحصًا كاملًا."""

        logger.info("🔍 بدء التحقق من سلامة السجل...")
        
        if not self.log_file.exists():
            logger.warning("السجل غير موجود")
            return IntegrityStatus.NOT_CHECKED
        
        prev_hash = resume["prev_hash"] if resume else "GENESIS"
        event_count = resume["count"] if resume else 0
        start_offset = resume["offset"] if resume else 0
        line_num = resume["line_num"] if resume else 0
        offset = start_offset
        _fail = None
        _partial_tail = False  # سطر أخير بلا \n — لا تُسجَّل نقطة استئناف عليه
        # R-701: تجزئتنا المعروفة يجب أن تكون ضمن السلسلة (كشف الاقتطاع) — لا أن
        # تكون آخرها بالضرورة (كاتب مشروع آخر قد يكون مدّ السلسلة بعدها).
        _known_last = self._last_hash
        _seen_known = _known_last == "GENESIS" or _known_last == prev_hash
        
        with open(self.log_file, 'rb') as f:
            f.seek(start_offset)
            for raw in f:
                line_num += 1
                if not raw.endswith(b"\n"):
                    # سطر أخير غير مكتمل (كاتب في منتصف الإلحاق): يُحكم عليه ولا يدخل البادئة
                    _line_end = offset
                    _partial_tail = True
                else:
                    _line_end = offset + len(raw)
                try:
                    line = raw.decode('utf-8').strip()
                except UnicodeDecodeError:
                    line = raw.decode('utf-8', errors='replace').strip()
                if not line:
                    offset = _line_end
                    continue
                
                try:
                    event = json.loads(line)
                    event_count += 1
                    
                    # 1) التحقق من prev_hash
                    if event.get('prev_hash') != prev_hash:
                        logger.error(f"❌ فشل في السطر {line_num}: prev_hash غير متطابق")
                        _fail = IntegrityStatus.CORRUPTED
                        break
                    
                    # 2) التحقق من تجزئة الحدث
                    expected_hash = self._compute_event_hash(
                        event['prev_hash'],
                        event['blob'],
                        event['time'],
                        event['type']
                    )
                    if event['hash'] != expected_hash:
                        logger.error(f"❌ فشل في السطر {line_num}: تجزئة الحدث غير متطابقة")
                        _fail = IntegrityStatus.CORRUPTED
                        break
                    
                    # 3) التحقق من التوقيع
                    # R-620: حدثان بصيغتين مختلفتين —
                    # - الأحداث الجديدة (تحمل key_id): تُوقّع بمفتاح KeyRing
                    #   وتشمل key_id في بيانات التوقيع (صيغة _compute_event_signature).
                    # - الأحداث التاريخية (بلا key_id): تُتحقق بالصيغة القديمة
                    #   (مفتاح الإعدادات، بيانات بلا key_id) — لا إعادة توقيع للتاريخ.
                    if 'key_id' in event:
                        if event.get('sig_type') == 'ed25519':
                            # R-698: تحقق Ed25519 بالمفتاح العام — لا إعادة توقيع
                            # بالمفتاح الخاص (التحقق يعمل حتى بغياب مادة التوقيع الخاصة).
                            # مفتاح غير معروف أو نوعه ليس ed25519 → فساد صريح.
                            try:
                                from backend.sovereign.keys import ed25519_verifier as _ed
                            except ImportError:
                                from sovereign.keys import ed25519_verifier as _ed
                            _kr_rec = self._keyring.get_key(event.get('key_id')) if self._keyring else None
                            if _kr_rec is None or getattr(_kr_rec, 'key_type', 'hmac') != 'ed25519':
                                logger.error(f"❌ فشل في السطر {line_num}: حدث ed25519 بمفتاح غير معروف أو نوع غير مطابق")
                                _fail = IntegrityStatus.CORRUPTED
                                break
                            _event_data = (
                                f"{event['hash']}|{event['prev_hash']}|{event['blob']}|"
                                f"{event['time']}|{event['type']}|{event.get('key_id', '')}"
                            )
                            if not _ed.verify_hex(
                                _kr_rec.public_key, _event_data.encode('utf-8'),
                                event['signature']
                            ):
                                logger.error(f"❌ فشل في السطر {line_num}: توقيع Ed25519 غير صحيح")
                                _fail = IntegrityStatus.CORRUPTED
                                break
                        else:
                            # R-625: التحقق يستخدم key_id من الحدث نفسه (وليس المفتاح النشط)
                            # — يضمن أن أحداث المفتاح A تُتحقق بنجاح بعد الدوران إلى B
                            expected_signature = self._compute_event_signature(
                                event['hash'],
                                event['prev_hash'],
                                event['blob'],
                                event['time'],
                                event['type'],
                                key_id=event.get('key_id')
                            )
                            # R-625: مقارنة آمنة (hmac.compare_digest)
                            import hmac as _hmac
                            if not _hmac.compare_digest(event['signature'], expected_signature):
                                logger.error(f"❌ فشل في السطر {line_num}: التوقيع غير صحيح (صيغة KeyRing)")
                                _fail = IntegrityStatus.CORRUPTED
                                break
                    else:
                        # صيغة تاريخية — تحقق بالمفتاح القديم
                        # R-699: بلا مفتاح جذر حقيقي لا تحقق ممكن — PARTIAL (لا VERIFIED
                        # ولا ادعاء تلاعب). HMAC بمفتاح فارغ/علني يحسبه أي أحد.
                        if self.signing_key is None:
                            logger.error(
                                f"❌ السطر {line_num}: حدث تاريخي ولا مفتاح جذر حقيقي "
                                f"للتحقق — R-699: PARTIAL"
                            )
                            _fail = IntegrityStatus.PARTIAL
                            break
                        if not verify_hmac(
                            f"{event['hash']}|{event['prev_hash']}|{event['blob']}|{event['time']}|{event['type']}".encode('utf-8'),
                            self.signing_key,
                            event['signature']
                        ):
                            logger.error(f"❌ فشل في السطر {line_num}: التوقيع غير صحيح")
                            _fail = IntegrityStatus.CORRUPTED
                            break
                    
                    # 4) التحقق من وجود الـ blob
                    if not self.blob_store.exists(event['blob']):
                        logger.error(f"❌ فشل في السطر {line_num}: blob غير موجود: {event['blob'][:16]}...")
                        _fail = IntegrityStatus.PARTIAL
                        break
                    
                    prev_hash = event['hash']
                    offset = _line_end
                    if prev_hash == _known_last:
                        _seen_known = True
                    
                    if verbose and event_count % 1000 == 0:
                        logger.info(f"   تم التحقق من {event_count} حدث...")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ فشل في السطر {line_num}: خطأ في JSON - {e}")
                    _fail = IntegrityStatus.CORRUPTED
                    break
                except Exception as e:
                    logger.error(f"❌ فشل في السطر {line_num}: {e}")
                    _fail = IntegrityStatus.CORRUPTED
                    break
        
        if _fail is not None:
            # R-768: البادئة حتى نهاية السطر الفاشل تُبصم — ما دامت كما هي فالنتيجة نفسها
            if _partial_tail:
                self._integrity_prefix = None  # الحكم على سطر قد يكتمل — لا يُبصم
            else:
                self._record_prefix(_line_end, prev_hash, event_count, line_num, _fail)
            return self._remember_integrity(_fail)

        # التحقق من أن آخر تجزئة معروفة لهذه النسخة ما زالت في السلسلة
        # (R-701: عضوية لا مساواة — الاقتطاع يُكشف، وتمديد كاتب مشروع لا يُدان)
        if not _seen_known and resume is not None:
            return None  # آخر تجزئتنا في البادئة (كاتب آخر مدّ السلسلة) — تحقق كامل يحكم
        if not _seen_known:
            logger.error(f"❌ آخر تجزئة معروفة غير موجودة في السلسلة (اقتطاع/إعادة كتابة): {_known_last[:16]}... (ذيل الملف {prev_hash[:16]}...)")
            return self._remember_integrity(IntegrityStatus.CORRUPTED)
        
        if _partial_tail:
            self._integrity_prefix = None
        else:
            self._record_prefix(offset, prev_hash, event_count, line_num, None)
        # حفظ نتيجة التحقق
        integrity_record = {
            "status": IntegrityStatus.VERIFIED.value,
            "events_checked": event_count,
            "last_hash": self._last_hash,
            "checked_at": utc_now_iso()
        }
        with open(self.integrity_file, 'w', encoding='utf-8') as f:
            json.dump(integrity_record, f, ensure_ascii=False, indent=2)
        
        # M1: حفظ نتيجة التحقق في الذاكرة
        self._integrity_cache = {
            "status": IntegrityStatus.VERIFIED,
            "last_hash": self._last_hash,
            "checked_at": utc_now_iso(),
            "ts": time.time()
        }
        
        logger.info(f"✅ السجل سليم! تم التحقق من {event_count} حدث.")
        return IntegrityStatus.VERIFIED
    
    def export_snapshot(self, target_dir: Path, include_blobs: bool = True) -> Path:
        """
        تصدير لقطة كاملة للسجل السيادي.
        
        تستخدم للنسخ الاحتياطي أو النقل إلى عقدة أخرى.
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        snapshot_dir = target_dir / f"snapshot_{int(time.time())}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 1) نسخ السجل
        if self.log_file.exists():
            shutil.copy2(self.log_file, snapshot_dir / "ledger.jsonl")
        
        # 2) نسخ blobs (اختياري)
        if include_blobs:
            blobs_dir = snapshot_dir / "blobs"
            shutil.copytree(self.blob_store.blobs_dir, blobs_dir, dirs_exist_ok=True)
        
        # 3) نسخ الفهرس والميتا
        if self.index_file.exists():
            shutil.copy2(self.index_file, snapshot_dir / "index.json")
        if self.meta_file.exists():
            shutil.copy2(self.meta_file, snapshot_dir / "meta.json")
        
        # 4) إنشاء ملف وصف اللقطة
        manifest = {
            "snapshot_id": sha256_hash(str(time.time()).encode())[:16],
            "created_at": utc_now_iso(),
            "source_last_hash": self._last_hash,
            "events_count": self.index.data['events_count'],
            "blobs_count": self.blob_store.count(),
            "blobs_included": include_blobs
        }
        
        with open(snapshot_dir / "manifest.json", 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📦 تم تصدير اللقطة إلى: {snapshot_dir}")
        return snapshot_dir
    
    def get_statistics(self) -> Dict[str, Any]:
        """إحصائيات كاملة عن السجل السيادي"""
        return {
            "core": {
                "last_hash": self._last_hash,
                "genesis_created": self._genesis_created
            },
            "index": self.index.get_statistics(),
            "storage": {
                "blobs_count": self.blob_store.count(),
                "blobs_size_bytes": self.blob_store.size(),
                "blobs_size_mb": round(self.blob_store.size() / (1024 * 1024), 2)
            },
            "files": {
                "log_file": str(self.log_file),
                "log_exists": self.log_file.exists(),
                "log_size_mb": round(self.log_file.stat().st_size / (1024 * 1024), 2) if self.log_file.exists() else 0
            }
        }
    
    def get_event_by_sequence(self, index: int) -> Optional[Dict[str, Any]]:
        """استرجاع حدث حسب ترتيبه (الحدث رقم n)"""
        if not self.log_file.exists():
            return None
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                if i == index:
                    return self._parse_ledger_line(line)  # R-766: تالف → None
        return None
    
    def _ledger_line_count(self) -> int:
        if not self.log_file.exists():
            return 0
        n = 0
        with open(self.log_file, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                n += chunk.count(b'\n')
        return n

    def _reconcile_index_with_ledger(self) -> None:
        """R-762: يعيد بناء الفهرس إن خالف عدّاده عدد أسطر السجل."""
        try:
            ledger_n = self._ledger_line_count()
            # R-763: الأسطر غير الحدثية (تالفة/فارغة) لا تُفهرس — تُطرح من المتوقع
            # (وإلا أعيد البناء مع كل إقلاع بعد كتابة ممزقة)
            expected = ledger_n - getattr(self, "_ledger_nonevent_lines", 0)
            seen = self.index.data.get("events_count", 0)
            if seen != expected:
                logger.warning(
                    f"R-762: الفهرس ({seen}) "
                    f"لا يطابق السجل ({expected} حدثًا سليمًا) — إعادة بناء من السجل"
                )
                self.index = self._rebuild_index()
        except Exception as e:  # TOLERATED: الفهرس ذاكرة مؤقتة؛ السجل لم يُمس
            logger.error(f"R-762: فشل مطابقة الفهرس بالسجل: {e}")

    def _load_index(self) -> SovereignIndex:
        """تحميل أو إعادة إنشاء الفهرس"""
        # R-606: إصلاح — المسار في self.index.index_file وليس self.index_file
        return SovereignIndex(self.index.index_file)

    def _rebuild_index(self) -> SovereignIndex:
        """R-606: إعادة بناء الفهرس بالكامل من السجل (للاسترداد من فهرس قديم/تالف)."""
        new_index = SovereignIndex(self.index.index_file)
        new_index.data = new_index._empty_index()
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        new_index.add_event(
                            event_hash=event.get('hash', ''),
                            event_type=event.get('type', ''),
                            event_time=event.get('time', ''),
                            prev_hash=event.get('prev_hash', ''),
                            user=None
                        )
                    except Exception as e:
                        logger.error(f"فشل إعادة بناء الفهرس عند حدث: {e}")
        new_index.save()
        return new_index


# ============================================================
# الـ Singleton للاستخدام من بقية النظام
# ============================================================

_core_instance: Optional[SovereignCore] = None
_core_lock = threading.Lock()


def get_core() -> SovereignCore:
    """الحصول على النسخة الوحيدة من النواة السيادية"""
    global _core_instance
    if _core_instance is None:
        with _core_lock:
            if _core_instance is None:
                _core_instance = SovereignCore()
    return _core_instance


# ============================================================
# اختبار تشغيلي (يُشغّل فقط عند تنفيذ الملف مباشرة)
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧠 اختبار نواة الذاكرة السيادية")
    print("=" * 60 + "\n")
    
    core = get_core()
    
    # إضافة بعض الأحداث التجريبية
    print("📝 إضافة أحداث تجريبية...")
    
    event1 = core.append_event(
        EventType.INTERACTION,
        {"user": "test_user", "message": "من أنت؟", "context": "first_contact"},
        user="test_user"
    )
    print(f"   ✅ الحدث 1: {event1['hash'][:16]}...")
    
    event2 = core.append_event(
        EventType.RESPONSE,
        {"user": "test_user", "response": "أنا الذاكرة السيادية، سجل لا يُمحى"},
        user="test_user"
    )
    print(f"   ✅ الحدث 2: {event2['hash'][:16]}...")
    
    # عرض الإحصائيات
    print("\n📊 إحصائيات السجل:")
    stats = core.get_statistics()
    print(f"   - عدد الأحداث: {stats['index']['total_events']}")
    print(f"   - عدد الـ blobs: {stats['storage']['blobs_count']}")
    print(f"   - حجم الـ blobs: {stats['storage']['blobs_size_mb']} MB")
    print(f"   - آخر تجزئة: {stats['core']['last_hash'][:16]}...")
    
    # التحقق من السلامة
    print("\n🔍 التحقق من سلامة السجل...")
    integrity = core.verify_integrity(verbose=True)
    print(f"   - حالة السلامة: {integrity.value}")
    
    print("\n✅ اختبار نواة الذاكرة السيادية اكتمل بنجاح")
    print("=" * 60)
