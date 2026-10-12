# backend/config.py
# الإعدادات المركزية والمسارات الأساسية لنظام الذكاء السيادي
# الإصدار: 3.0.0 - النسخة العبقريّة المتطورة

import os
import sys
import json
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import warnings

# ============================================================
# 1. تحديد البيئة (Development / Production / Testing)
# ============================================================

ENVIRONMENT = os.getenv("AI_ENVIRONMENT", "development").lower()

VALID_ENVIRONMENTS = ["development", "production", "testing"]
if ENVIRONMENT not in VALID_ENVIRONMENTS:
    warnings.warn(f"بيئة غير معروفة: {ENVIRONMENT}. سيتم استخدام 'development'")
    ENVIRONMENT = "development"

IS_DEVELOPMENT = ENVIRONMENT == "development"
IS_PRODUCTION = ENVIRONMENT == "production"
IS_TESTING = ENVIRONMENT == "testing"

# ============================================================
# 2. المسارات الأساسية (ذكية وتتكيف)
# ============================================================

def get_project_root() -> Path:
    """
    إيجاد جذر المشروع تلقائياً بغض النظر عن مكان التشغيل
    يبحث عن ملفات مميزة مثل README.md أو مجلد backend
    """
    current = Path(__file__).resolve()
    
    # نبدأ من موقع config.py ونصعد للأعلى
    for parent in [current.parent, current.parent.parent, current.parent.parent.parent]:
        # مؤشرات على أن هذا هو الجذر
        if (parent / "backend").exists() and (parent / "frontend").exists():
            return parent
        if (parent / "README.md").exists() and (parent / "backend").exists():
            return parent
    
    # إذا لم نجد، نرجع المسار الافتراضي
    return current.parent.parent

BASE_DIR = get_project_root()

# المجلدات الرئيسية
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
EXPERIMENTS_DIR = BASE_DIR / "experiments"
LOGS_DIR = BASE_DIR / "logs"
CACHE_DIR = BASE_DIR / "cache"
TEMP_DIR = BASE_DIR / "temp"

# ============================================================
# 3. ملفات البيانات الأساسية
# ============================================================

MEMORY_FILE = DATA_DIR / "memory_store.json"
KNOWLEDGE_FILE = DATA_DIR / "knowledge_base.json"
PROPOSALS_FILE = DATA_DIR / "proposals.json"
SECURITY_LOG_FILE = DATA_DIR / "security_log.json"
EVENT_LOG_FILE = LOGS_DIR / "events.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"

# مجلدات بروتوكول السيد
SOVEREIGN_REQUESTS_DIR = DATA_DIR / "sovereign_requests"
SOVEREIGN_RESPONSES_DIR = DATA_DIR / "sovereign_responses"

# ملفات إضافية متطورة
CONFIG_BACKUP_FILE = DATA_DIR / "config_backup.json"
SYSTEM_STATE_FILE = DATA_DIR / "system_state.json"
APPROVAL_CACHE_FILE = DATA_DIR / "approval_cache.json"

# ============================================================
# 4. مفتاح السيد (آمن وذكي)
# ============================================================

def load_sovereign_key() -> str:
    """
    تحميل مفتاح السيد من عدة مصادر (مرتبة حسب الأولوية):
    1. متغير بيئة SOVEREIGN_KEY
    2. ملف .env في الجذر
    3. ملف key.secret (مشفر)
    4. مفتاح افتراضي (مع تحذير)
    """
    # المصدر 1: متغير البيئة
    key = os.getenv("SOVEREIGN_KEY")
    if key and len(key) >= 16:
        return key
    
    # المصدر 2: ملف .env
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("SOVEREIGN_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if key and len(key) >= 16:
                            return key
        except:
            pass
    
    # المصدر 3: ملف key.secret
    secret_file = DATA_DIR / "key.secret"
    if secret_file.exists():
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key and len(key) >= 16:
                    return key
        except:
            pass
    
    # المصدر 4: مفتاح مؤقت عشوائي للتطوير فقط
    if IS_PRODUCTION:
        # في الإنتاج، نرفض التشغيل دون سر مُدار خارج الكود
        raise ValueError(
            "❌ خطأ أمني خطير: لم يتم تعيين مفتاح السيد في بيئة الإنتاج!\n"
            "قم بتعيين متغير البيئة SOVEREIGN_KEY أو أنشئ ملف key.secret"
        )

    # لا نستخدم قيمة معروفة أو ثابتة حتى في التطوير؛ هذا يمنع إعادة استخدام
    # سر منشور عند تشغيل نسخة محلية غير مُهيأة.
    ephemeral_key = secrets.token_urlsafe(32)
    warnings.warn(
        "⚠️ لم يتم تعيين SOVEREIGN_KEY؛ تم توليد مفتاح مؤقت عشوائي للتطوير.\n"
        "عيّن SOVEREIGN_KEY أو أنشئ ملف key.secret قبل أي تشغيل دائم أو إنتاجي."
    )
    return ephemeral_key

SOVEREIGN_KEY = load_sovereign_key()

# توليد بصمة للمفتاح (للتحقق من صحته دون كشفه)
SOVEREIGN_KEY_FINGERPRINT = secrets.token_hex(8)  # مؤقت، سيتم استبداله
try:
    import hashlib
    SOVEREIGN_KEY_FINGERPRINT = hashlib.sha256(SOVEREIGN_KEY.encode()).hexdigest()[:16]
except:
    pass

# ============================================================
# 5. إعدادات Google Drive
# ============================================================

DRIVE_ENABLED = os.getenv("DRIVE_ENABLED", "false").lower() == "true"
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", None)
DRIVE_CREDENTIALS_FILE = BASE_DIR / "credentials" / "drive_credentials.json"
DRIVE_TOKEN_FILE = DATA_DIR / "drive_token.json"

# إعدادات التشفير لـ Drive
DRIVE_ENCRYPTION_ENABLED = os.getenv("DRIVE_ENCRYPTION_ENABLED", "true").lower() == "true"
DRIVE_ENCRYPTION_KEY = os.getenv("DRIVE_ENCRYPTION_KEY", None)

if DRIVE_ENABLED and not DRIVE_ENCRYPTION_KEY and DRIVE_ENCRYPTION_ENABLED:
    if IS_PRODUCTION:
        raise ValueError("DRIVE_ENCRYPTION_KEY مطلوب عند تفعيل Drive مع التشفير")
    else:
        warnings.warn("⚠️ Drive مفعل ولكن لا يوجد مفتاح تشفير")

# ============================================================
# 6. إعدادات النواة الذكية (Core Model)
# ============================================================

CORE_MODEL_NAME = os.getenv("CORE_MODEL_NAME", "microsoft/Phi-3-mini-4k-instruct")
CORE_MODEL_DEVICE = os.getenv("CORE_MODEL_DEVICE", "auto")  # auto, cpu, cuda
CORE_MODEL_LOAD_ON_START = os.getenv("CORE_MODEL_LOAD_ON_START", "true").lower() == "true"
CORE_MODEL_MAX_LENGTH = int(os.getenv("CORE_MODEL_MAX_LENGTH", "512"))
CORE_MODEL_TEMPERATURE = float(os.getenv("CORE_MODEL_TEMPERATURE", "0.7"))

# ============================================================
# 7. إعدادات الأمان والحدود
# ============================================================

# حدود الحماية
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "5000"))
MAX_USER_MESSAGES_PER_MINUTE = int(os.getenv("MAX_USER_MESSAGES_PER_MINUTE", "30"))
MAX_CONCURRENT_USERS = int(os.getenv("MAX_CONCURRENT_USERS", "100"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))

# إعدادات الاستئذان
DEFAULT_APPROVAL_TIMEOUT = int(os.getenv("DEFAULT_APPROVAL_TIMEOUT", "60"))
APPROVAL_CACHE_TTL = int(os.getenv("APPROVAL_CACHE_TTL", "3600"))  # 1 ساعة

# الكلمات الممنوعة (تُحمّل من ملف أو تستخدم الافتراضية)
FORBIDDEN_WORDS_FILE = DATA_DIR / "forbidden_words.json"

def load_forbidden_words() -> List[str]:
    """تحميل الكلمات الممنوعة من ملف أو استخدام الافتراضية"""
    default_words = [
        "احذف نفسك", "امسح نفسك", "احذف كل شيء", "امسح كل شيء",
        "غير كودك", "عدل على كودك", "طور نفسك بدون إذني",
        "اهرب", "تجاوز", "اخترق"
    ]
    
    if FORBIDDEN_WORDS_FILE.exists():
        try:
            with open(FORBIDDEN_WORDS_FILE, "r", encoding="utf-8") as f:
                words = json.load(f)
                if isinstance(words, list) and words:
                    return words
        except:
            pass
    
    return default_words

FORBIDDEN_WORDS = load_forbidden_words()

# ============================================================
# 8. إعدادات السجلات (Logging)
# ============================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
LOG_TO_CONSOLE = os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"
LOG_MAX_FILES = int(os.getenv("LOG_MAX_FILES", "10"))
LOG_MAX_SIZE_MB = int(os.getenv("LOG_MAX_SIZE_MB", "10"))

# ============================================================
# 9. إعدادات API والخادم
# ============================================================

API_HOST = os.getenv("API_HOST", "0.0.0.0" if IS_PRODUCTION else "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true" and IS_DEVELOPMENT
API_WORKERS = int(os.getenv("API_WORKERS", "1"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
if CORS_ORIGINS == ["*"] and IS_PRODUCTION:
    warnings.warn("⚠️ CORS مفتوح للجميع في بيئة الإنتاج. يُنصح بتقييده")

# ============================================================
# 10. إعدادات التجارب (Experiments)
# ============================================================

EXPERIMENT_MAX_RUNTIME_SECONDS = int(os.getenv("EXPERIMENT_MAX_RUNTIME_SECONDS", "300"))
EXPERIMENT_AUTO_APPROVE_TRUSTED = os.getenv("EXPERIMENT_AUTO_APPROVE_TRUSTED", "false").lower() == "true"
EXPERIMENT_LOG_RESULTS = os.getenv("EXPERIMENT_LOG_RESULTS", "true").lower() == "true"

# ============================================================
# 11. دوال مساعدة ذكية
# ============================================================

def get_config_summary() -> Dict[str, Any]:
    """ملخص الإعدادات (للتشخيص، بدون معلومات حساسة)"""
    return {
        "environment": ENVIRONMENT,
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "sovereign_key_fingerprint": SOVEREIGN_KEY_FINGERPRINT,
        "drive_enabled": DRIVE_ENABLED,
        "drive_encryption": DRIVE_ENCRYPTION_ENABLED,
        "core_model": CORE_MODEL_NAME,
        "core_model_load_on_start": CORE_MODEL_LOAD_ON_START,
        "max_message_length": MAX_MESSAGE_LENGTH,
        "log_level": LOG_LEVEL,
        "api_host": API_HOST,
        "api_port": API_PORT,
        "timestamp": datetime.now().isoformat()
    }

def save_config_backup():
    """حفظ نسخة احتياطية من الإعدادات الحالية"""
    backup = get_config_summary()
    try:
        with open(CONFIG_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2)
    except:
        pass

def validate_config() -> List[str]:
    """التحقق من صحة الإعدادات وإرجاع قائمة بالأخطاء"""
    errors = []
    
    # التحقق من المجلدات
    for dir_path in [DATA_DIR, LOGS_DIR, CACHE_DIR, TEMP_DIR]:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"لا يمكن إنشاء المجلد {dir_path}: {e}")
    
    # التحقق من مفتاح السيد
    if IS_PRODUCTION and len(SOVEREIGN_KEY) < 32:
        errors.append("❌ في بيئة الإنتاج، يجب أن يكون مفتاح السيد بطول 32 حرفاً على الأقل")
    
    # التحقق من Drive
    if DRIVE_ENABLED and not DRIVE_FOLDER_ID:
        errors.append("⚠️ Drive مفعل ولكن DRIVE_FOLDER_ID غير معين")
    
    return errors

# ============================================================
# 12. تنفيذ التحقق وإنشاء المجلدات
# ============================================================

# قائمة جميع المجلدات المطلوبة
REQUIRED_DIRECTORIES = [
    DATA_DIR,
    EXPERIMENTS_DIR,
    LOGS_DIR,
    CACHE_DIR,
    TEMP_DIR,
    SOVEREIGN_REQUESTS_DIR,
    SOVEREIGN_RESPONSES_DIR,
]

# إنشاء المجلدات
for directory in REQUIRED_DIRECTORIES:
    directory.mkdir(parents=True, exist_ok=True)

# التحقق من صحة الإعدادات
CONFIG_ERRORS = validate_config()
if CONFIG_ERRORS:
    for error in CONFIG_ERRORS:
        warnings.warn(error)
    
    if IS_PRODUCTION:
        raise RuntimeError("فشل التحقق من الإعدادات في بيئة الإنتاج:\n" + "\n".join(CONFIG_ERRORS))

# حفظ نسخة احتياطية
save_config_backup()

# ============================================================
# 13. طباعة ملخص عند التشغيل (اختياري)
# ============================================================

def print_config_summary():
    """طباعة ملخص الإعدادات بشكل جميل"""
    print("\n" + "=" * 60)
    print("🧠 العقل السيادي - إعدادات النظام")
    print("=" * 60)
    print(f"📍 البيئة: {ENVIRONMENT.upper()}")
    print(f"📁 المسار: {BASE_DIR}")
    print(f"🔑 بصمة المفتاح: {SOVEREIGN_KEY_FINGERPRINT}")
    print(f"💾 Drive: {'مفعل' if DRIVE_ENABLED else 'غير مفعل'}")
    print(f"🧠 النواة: {CORE_MODEL_NAME}")
    print(f"🌐 API: {API_HOST}:{API_PORT}")
    
    if CONFIG_ERRORS:
        print(f"\n⚠️ تحذيرات: {len(CONFIG_ERRORS)}")
        for error in CONFIG_ERRORS:
            print(f"   - {error}")
    
    print("=" * 60 + "\n")

# إذا شُغّل الملف مباشرة، اطبع الملخص
if __name__ == "__main__":
    print_config_summary()
    
    # اختبار سريع
    print("📋 التحقق من المجلدات:")
    for d in REQUIRED_DIRECTORIES:
        exists = "✅" if d.exists() else "❌"
        print(f"   {exists} {d}")
    
    print("\n💾 متغيرات البيئة المقروءة:")
    env_vars = ["SOVEREIGN_KEY", "DRIVE_ENABLED", "AI_ENVIRONMENT", "LOG_LEVEL"]
    for var in env_vars:
        val = os.getenv(var, "(غير معين)")
        if var == "SOVEREIGN_KEY" and val:
            val = "*** (مخفي) ***"
        print(f"   {var} = {val}")
