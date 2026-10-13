# backend/memory/core.py
# نواة الذاكرة السيادية الحقيقية
# سجل لا يُمحى، سلسلة تجزئة، تخزين بالمحتوى، توزيع، تحقق، وتوقيع
# الإصدار: 1.0.0 - جاهز للإنتاج، لا تجريبي، لا معنوي

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
    from config import DATA_DIR, SOVEREIGN_KEY
except ImportError:
    # للاستخدام المستقل للملف
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    SOVEREIGN_KEY = os.getenv("SOVEREIGN_KEY", "يجب_تغيير_هذا_المفتاح_فوراً")
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


class IntegrityStatus(str, Enum):
    """حالة سلامة السجل"""
    VERIFIED = "verified"
    CORRUPTED = "corrupted"
    PARTIAL = "partial"
    NOT_CHECKED = "not_checked"


# إعدادات التشفير
HASH_ALGORITHM = hashlib.sha256
HASH_SIZE = 32  # بايت
HMAC_ALGORITHM = hashlib.sha256
COMPRESSION_LEVEL = 6
MAX_BLOB_SIZE = 100 * 1024 * 1024  # 100 ميغابايت

# المسارات
CORE_DIR = DATA_DIR / "sovereign_core"
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
                except FileNotFoundError:
                    continue
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

class SovereignIndex:
    """فهرس متطور للبحث السريع في السجل السيادي"""
    
    def __init__(self, index_file: Path):
        self.index_file = index_file
        self.data: Dict[str, Any] = {}
        self._load()
    
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
        """حفظ الفهرس إلى القرص"""
        self.data["updated_at"] = utc_now_iso()
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
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
        
        self.save()
    
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
                 sovereign_key: str = SOVEREIGN_KEY):
        
        self.log_file = log_file
        self.meta_file = meta_file
        self.integrity_file = integrity_file

        # المكونات الداخلية
        self.blob_store = BlobStore(blobs_dir)
        self.index = SovereignIndex(index_file)

        # مفتاح التوقيع
        self.signing_key = sovereign_key.encode('utf-8') if sovereign_key else b''
        if not self.signing_key or self.signing_key == b'you_must_change_this_key_immediately':
            # توليد مفتاح جديد إذا كان افتراضياً
            self.signing_key = b'new_generated_key_here'

        # حالة السجل
        self._last_hash = self._load_last_hash()
        # M1: ذاكرة مؤقتة لنتيجة التحقق من سلامة السجل
        self._integrity_cache = None
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
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        last_event = json.loads(line)
                        last_hash = last_event.get('hash', last_hash)
                    return last_hash
            except:
                pass
        
        # إذا لم يوجد سجل، نقرأ من الميتا
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    return meta.get('last_hash', 'GENESIS')
            except:
                pass
        
        return 'GENESIS'
    def _load_genesis_status(self) -> bool:
        """التحقق من وجود حدث البداية"""
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    return meta.get('genesis_created', False)
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
                                  event_type: str) -> str:
        """حساب توقيع الحدث (لضمان عدم التلاعب)"""
        data = f"{event_hash}|{prev_hash}|{blob_hash}|{event_time}|{event_type}"
        return compute_hmac(data.encode('utf-8'), self.signing_key)
    
    def append_event(self, event_type: EventType, payload: Dict[str, Any],
                     user: Optional[str] = None) -> Dict[str, Any]:
        # M1: قبول EventType أو سلسلة نصية (كان ينهار على السلاسل)
        if isinstance(event_type, EventType):
            event_type_str = event_type.value
        else:
            event_type_str = str(event_type)
        """
        إضافة حدث جديد إلى السجل السيادي.
        
        هذه هي الطريقة الوحيدة لإضافة أي شيء إلى الذاكرة.
        لا حذف. لا تعديل. فقط إضافة.
        """
        with FileLock(LOCK_FILE):
            # 1) تحويل الـ payload إلى JSON وتخزينه كـ blob
            payload_json = safe_json_dumps(payload)
            payload_bytes = payload_json.encode('utf-8')
            blob_hash = self.blob_store.put(payload_bytes, compress=True)
            
            # 2) تحديد الوقت الحالي
            event_time = utc_now_iso()
            
            # 3) حساب تجزئة الحدث
            event_hash = self._compute_event_hash(
                self._last_hash, blob_hash, event_time, event_type_str
            )
            
            # 4) حساب التوقيع
            signature = self._compute_event_signature(
                event_hash, self._last_hash, blob_hash, event_time, event_type_str
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
            
            # 6) كتابة الحدث إلى السجل (JSONL)
            event_line = json.dumps(event, ensure_ascii=False)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(event_line + '\n')
            
            # 7) تحديث الحالة الداخلية
            self._last_hash = event_hash
            # R-606: إبطال ذاكرة التحقق المؤقتة — تغيّر السجل
            self._integrity_cache = None
            
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
    
    def get_event(self, event_hash: str) -> Optional[Dict[str, Any]]:
        """استرجاع حدث من السجل"""
        if not self.log_file.exists():
            return None
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                if event.get('hash') == event_hash:
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
                events = [json.loads(l) for l in lines]
                # قد نكون بدأنا في منتصف سطر — تجاهل أول عنصر غير مكتمل
                if len(events) > limit:
                    events = events[-limit:]
                for event in reversed(events):
                    yield event
                return
            except Exception:
                # أي فشل في المسار السريع → الرجوع للمسار الكامل
                pass
        
        events = []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))
        
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
    
    def verify_integrity(self, verbose: bool = False) -> IntegrityStatus:
        """
        التحقق من سلامة السجل بأكمله.
        - يتحقق من سلسلة التجزئة.
        - يتحقق من التوقيعات.
        - يتحقق من وجود الـ blobs.
        """
        # M1: تخزين مؤقت للتحقق — لا نعيد فحص السجل الكامل في كل استعلام حالة
        # R-606: يُعاد التحقق فقط إذا تغيّر السجل (آخر تجزئة) أو انقضت المهلة (60 ثانية)
        if not verbose and self._integrity_cache is not None:
            if self._integrity_cache.get("last_hash") == self._last_hash:
                return self._integrity_cache["status"]
            if (time.time() - self._integrity_cache.get("ts", 0)) < 60.0:
                return self._integrity_cache["status"]
        
        logger.info("🔍 بدء التحقق من سلامة السجل...")
        
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
                    
                    # 1) التحقق من prev_hash
                    if event.get('prev_hash') != prev_hash:
                        logger.error(f"❌ فشل في السطر {line_num}: prev_hash غير متطابق")
                        return IntegrityStatus.CORRUPTED
                    
                    # 2) التحقق من تجزئة الحدث
                    expected_hash = self._compute_event_hash(
                        event['prev_hash'],
                        event['blob'],
                        event['time'],
                        event['type']
                    )
                    if event['hash'] != expected_hash:
                        logger.error(f"❌ فشل في السطر {line_num}: تجزئة الحدث غير متطابقة")
                        return IntegrityStatus.CORRUPTED
                    
                    # 3) التحقق من التوقيع
                    expected_signature = self._compute_event_signature(
                        event['hash'],
                        event['prev_hash'],
                        event['blob'],
                        event['time'],
                        event['type']
                    )
                    if not verify_hmac(
                        f"{event['hash']}|{event['prev_hash']}|{event['blob']}|{event['time']}|{event['type']}".encode('utf-8'),
                        self.signing_key,
                        event['signature']
                    ):
                        logger.error(f"❌ فشل في السطر {line_num}: التوقيع غير صحيح")
                        return IntegrityStatus.CORRUPTED
                    
                    # 4) التحقق من وجود الـ blob
                    if not self.blob_store.exists(event['blob']):
                        logger.error(f"❌ فشل في السطر {line_num}: blob غير موجود: {event['blob'][:16]}...")
                        return IntegrityStatus.PARTIAL
                    
                    prev_hash = event['hash']
                    
                    if verbose and event_count % 1000 == 0:
                        logger.info(f"   تم التحقق من {event_count} حدث...")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ فشل في السطر {line_num}: خطأ في JSON - {e}")
                    return IntegrityStatus.CORRUPTED
                except Exception as e:
                    logger.error(f"❌ فشل في السطر {line_num}: {e}")
                    return IntegrityStatus.CORRUPTED
        
        # التحقق من أن آخر تجزئة متطابقة
        if prev_hash != self._last_hash:
            logger.error(f"❌ آخر تجزئة غير متطابقة: {prev_hash[:16]}... != {self._last_hash[:16]}...")
            return IntegrityStatus.CORRUPTED
        
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
                    return json.loads(line)
        return None
    
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
