# backend/config.py
# الإعدادات المركزية والمسارات الأساسية لنظام الذكاء السيادي
# الإصدار: 3.0.0 - النسخة العبقريّة المتطورة

import os
import sys
import json
from runtime.atomic_json import atomic_write_json  # R-781
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

# عزل بيانات الاختبار (R-615): يسمح بإعادة توجيه مجلد البيانات إلى جذر مؤقت
# عبر متغير البيئة SOVEREIGN_DATA_ROOT — تستخدمه الاختبارات لعزل بياناتها
# عن بيانات التشغيل الحقيقية (data/). يجب تعيينه قبل استيراد هذا الملف.
# ملاحظة: لا يُلمس هذا المتغير في التشغيل العادي — القيمة الافتراضية هي
# BASE_DIR / 'data' كما هو الأصل. لا حذف، لا تعديل للسلوك الأصلي.
_TEST_DATA_ROOT = os.getenv("SOVEREIGN_DATA_ROOT")
if _TEST_DATA_ROOT:
    # عزل فعلي: كل المسارات المشتقة من DATA_DIR ستشير إلى الجذر المؤقت
    DATA_DIR = Path(_TEST_DATA_ROOT)
    # مجلدات إضافية تُعزل أيضًا (logs, cache, temp) لتجنب أي كتابة خارج الجذر
    _ISOLATED_ROOT = DATA_DIR.parent
    LOGS_DIR = _ISOLATED_ROOT / "logs"
    CACHE_DIR = _ISOLATED_ROOT / "cache"
    TEMP_DIR = _ISOLATED_ROOT / "temp"
else:
    # المسارات الأصلية (التشغيل العادي — لا تغيير)
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    CACHE_DIR = BASE_DIR / "cache"
    TEMP_DIR = BASE_DIR / "temp"

# المجلدات الرئيسية
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
# ملاحظة: DATA_DIR محدد أعلاه (أصلي أو معزول)
EXPERIMENTS_DIR = BASE_DIR / "experiments"

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
    3. ملف key.secret (نص صريح — وضع 0600 إلزامي)
    4. توليد مفتاح دائم في التطوير (R-610) — يُحفظ في data/key.secret (مستثنى من git)
    5. مفتاح مؤقت عشوائي (تطوير فقط) / رفض (إنتاج)
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
        # TOLERATED: .env file exists but is unreadable/malformed — fall through to next source (R-680)
        except:
            pass
    
    # المصدر 3: ملف key.secret
    secret_file = DATA_DIR / "key.secret"
    if secret_file.exists():
        try:
            # ⚠️ SECURITY (جولة المجلس <1> — أمين 2.4/بصير BAS-S16/حكيم):
            # ملف سر قابل للقراءة من غير صاحبه = تهيئة مكشوفة.
            # الإنتاج: رفض صريح. التطوير: تحذير + تضييق إلى 0600.
            import stat as _stat
            file_mode = _stat.S_IMODE(os.stat(secret_file).st_mode)
            if file_mode & 0o077:
                if IS_DEVELOPMENT:
                    warnings.warn(
                        f"⚠️ key.secret بأذونات واسعة ({oct(file_mode)}) — يُضيّق الآن إلى 0600"
                    )
                    os.chmod(secret_file, 0o600)
                else:
                    raise ValueError(
                        f"❌ خطأ أمني: key.secret بأذونات مكشوفة ({oct(file_mode)}) "
                        f"— يُرفض البدء في الإنتاج (جولة المجلس <1>)"
                    )
            with open(secret_file, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key and len(key) >= 16:
                    return key
        # TOLERATED: key.secret exists but is unreadable — skip to next source (R-680)
        except ValueError:
            raise
        except Exception:  # TOLERATED: key.secret unreadable — skip to next source (R-680)
            pass
    
    # المصدر 4 (R-610): توليد مفتاح سيد دائم في التطوير — الهوية السيادية تستمر عبر إعادة التشغيل
    if IS_DEVELOPMENT:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            persistent_key = secrets.token_urlsafe(32)
            # حماية الملف: 0600 (المالك فقط) — الملف مستثنى من git (.gitignore)
            fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(persistent_key)
            warnings.warn(
                "🔑 تم توليد مفتاح سيد دائم للتطوير وحفظه في data/key.secret (مستثنى من git).\n"
                "الهوية السيادية (ختم الهوية + توقيعات السجل) ستستمر عبر عمليات إعادة التشغيل."
            )
            return persistent_key
        except FileExistsError:
            # سباق: ملف أُنشئ للتو — أعد قراءته
            try:
                with open(secret_file, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                    if key and len(key) >= 16:
                        return key
            # TOLERATED: race-condition re-read failed — treat as generation failure (R-680)
            except Exception:
                pass
        # TOLERATED: persistent key generation failed — fall through to ephemeral/production check (R-680)
        except Exception:
            pass

    # المصدر 5: مفتاح مؤقت عشوائي للتطوير فقط
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
# TOLERATED: fingerprint computation is cosmetic-only (debug logging) — fallback value retained (R-680)
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
# 6. إعدادات Ollama (خادم LLM محلي — عقل السيادي R-704)
# ============================================================

def _ollama_env(name: str, default=None):
    """قراءة إعداد Ollama: متغير البيئة أولًا ثم ملف .env (القراءة مخصصة
    لإعدادات Ollama ولا تغيّر قواعد مفتاح السيد). مسار الملف قابل للعزل
    عبر OLLAMA_ENV_FILE للاختبارات. البيئة تعلو على الملف دائمًا."""
    val = os.getenv(name)
    if val is not None:
        return val
    env_file = os.getenv("OLLAMA_ENV_FILE") or (BASE_DIR / ".env")
    try:
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(name + "="):
                        v = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if v:
                            return v
    # TOLERATED: ملف .env غير موجود/غير مقروء — القيمة الافتراضية (نمط R-680)
    except Exception:
        pass
    return default


# العقل معطل افتراضيًا — يُفعّل صراحة في إعداد التشغيل (لا اتصال ضمني في الاختبارات)
OLLAMA_ENABLED = _ollama_env("OLLAMA_ENABLED", "false").lower() == "true"

# عنوان خادم Ollama — المنفذ 11434 هو منفذ Ollama المعياري.
# مثال لخادم على شبكة محلية (في .env المستثنى من git): OLLAMA_BASE_URL=http://ollama-server:11434
OLLAMA_BASE_URL = _ollama_env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

# النموذج صريح لا افتراضي — لا يُفترض نموذج غير مثبت على خادم المالك
# (مثال: OLLAMA_MODEL=qwen2.5:7b — مناسب للعربية).
OLLAMA_MODEL = _ollama_env("OLLAMA_MODEL", None)

# R-736 (البند ٢.١ — عقل المنشور): بروتوكول العقل على السلك —
# "ollama" (الافتراضي: POST {base}/api/chat — النفق المحلي/Ollama Cloud)
# أو "openai" (متوافق OpenAI: POST {base}/chat/completions — Groq/OpenRouter/
# أي مزود متوافق). في وضع openai تكون BASE_URL بادئة الإصدار كاملة
# (مثال: https://api.groq.com/openai/v1 أو https://openrouter.ai/api/v1)
# ويُلحق بها /chat/completions مرة واحدة. القيمة المجهولة تُغلق fail-closed.
OLLAMA_PROTOCOL = (_ollama_env("OLLAMA_PROTOCOL", "ollama") or "ollama").strip().lower() or "ollama"

# مفتاح API اختياري — Ollama المحلي لا يتطلب توثيقًا (يبقى None).
OLLAMA_API_KEY = _ollama_env("OLLAMA_API_KEY", None)

# مهلة توليد الرد بالثواني — بعدها سقوط آمن للمحرك القالبي
OLLAMA_TIMEOUT_SECONDS = float(_ollama_env("OLLAMA_TIMEOUT_SECONDS", "60"))
# R-787: نافذة سياق العقل (0 = افتراض الخادم) — نتائج الأدوات تحتاج نافذة أوسع
OLLAMA_NUM_CTX = int(_ollama_env("OLLAMA_NUM_CTX", "0") or 0)

# ============================================================
# R-810 (المالك — ٢ و٣ من أمر التشغيل): طبقة إعدادات العقل عند التشغيل
# ============================================================
# دوافع المالك (2026-10-29): «لا يوجد إمكانية تبديل النماذج، اذ ان اولاما فيه
# عدة نماذج…» و«النظام يعتمد كليا على اولاما ولا مجال لإضافة مفاتيح API».
# البيئة تبقى الافتراض عند الإقلاع (النشر يضبطها)، والتعديل الحي من الواجهة
# (المالك فقط) يُكتب في ملف تشغيل محلي يقرؤه العقل في كل استدعاء — بلا إعادة
# تشغيل وبلا مساس بأسرار المستودع. ملاحظة نشر حاسمة: OLLAMA_MODEL كسر
# مستودع يتزامن مع fly.toml أثناء النشر — التبديل الحي يُحفظ في هذه الطبقة
# فقط ولا يُلمس، فيبقى إقلاع النشر سليمًا دائمًا.

BRAIN_RUNTIME_FILE = Path(os.getenv("BRAIN_RUNTIME_FILE") or (BASE_DIR / "data" / "brain_runtime.json"))
_BRAIN_RUNTIME_KEYS = ("OLLAMA_MODEL", "OLLAMA_PROTOCOL", "OLLAMA_BASE_URL", "OLLAMA_API_KEY", "OLLAMA_NUM_CTX")


def brain_runtime_read() -> dict:
    """قراءة طبقة إعدادات التشغيل (فارغة عند غيابها — البيئة تكفي).

    تُقرأ عند كل استدعاء (ملف صغير) — التعديل من الواجهة يسري على الطلب التالي
    مباشرة بلا إعادة تشغيل وبلا حالة عملية عابرة.
    """
    try:
        raw = json.loads(BRAIN_RUNTIME_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {k: raw[k] for k in _BRAIN_RUNTIME_KEYS if raw.get(k) not in (None, "")}
    # TOLERATED: ملف غير موجود/تالف — طبقة فارغة، البيئة هي الفعالة (نمط R-680)
    except (OSError, ValueError):
        pass
    return {}


def brain_get(name: str, default=None):
    """القيمة الفعالة لإعداد العقل: طبقة التشغيل أولًا ثم قيمة البيئة المحمّلة.

    هذا هو مسار القراءة الوحيد للعقل الحي (ollama_client) — مصدر واحد للحقيقة.
    استثناء المفتاح السري (OLLAMA_API_KEY): يُقرأ من الخزينة المشفرة (R-813) —
    لا نص صريح على القرص أبدًا؛ قيمته في البيئة تبقى احتياطًا عند غيابه.
    """
    if name == "OLLAMA_API_KEY":
        vault_value = brain_api_key_get()
        if vault_value:
            return vault_value
        return getattr(sys.modules[__name__], name, default)
    runtime = brain_runtime_read()
    if name in runtime:
        return runtime[name]
    return getattr(sys.modules[__name__], name, default)


# R-813 (مراجعة المستشار): مفتاح مزود العقل سرٌّ مشفَّر في الخزينة (AES-256-GCM)
# لا نص صريح في ملف التشغيل — الخزينة مفعلة حيًا (‏/vault/status) وتدقق كل فعل
# في السجل الموقّع. القراءة مخزنة مؤقتًا في الذاكرة: تدقيق الخزينة يكتب حدثًا
# موقّعًا لكل قراءة، وقراءة المفتاح عند كل استدلال كانت ستفيض السجل.
BRAIN_API_KEY_SECRET = "brain.provider_api_key"
BRAIN_API_KEY_SCOPE = "brain.provider"
_BRAIN_API_KEY_CACHE: dict = {}


def brain_api_key_get() -> Optional[str]:
    """مفتاح مزود العقل من الخزينة (مخزن مؤقتًا) — أو None عند غيابه/تعطلها."""
    if _BRAIN_API_KEY_CACHE.get("value"):
        return _BRAIN_API_KEY_CACHE["value"]
    try:
        try:
            from backend.sovereign.secrets_vault import get_vault
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from sovereign.secrets_vault import get_vault
        value = get_vault().get(BRAIN_API_KEY_SECRET, capability=BRAIN_API_KEY_SCOPE,
                                actor="brain_runtime")
        _BRAIN_API_KEY_CACHE["value"] = value
        return value
    except Exception:
        # غياب السر (لم يُضبط بعد) أو خزينة معطلة — قيمة البيئة هي الفعالة
        return None


def brain_api_key_set(value, actor: str = "owner") -> bool:
    """ضبط مفتاح مزود العقل في الخزينة — True إذا تغير، False إذا طُلب إلغاء غير موجود.

    القيمة الفارغة تحذفه صراحةً (عودة لقيمة البيئة). الفشل يرتفع استثناءً صادقًا —
    لا نجاح كاذبًا أبدًا.
    """
    try:
        try:
            from backend.sovereign.secrets_vault import get_vault
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from sovereign.secrets_vault import get_vault
        vault = get_vault()
    except Exception as exc:
        raise RuntimeError(f"الخزينة غير متاحة — لا تخزين مفتاح مزود: {type(exc).__name__}") from exc
    if vault is None or not getattr(vault, "enabled", False):
        raise RuntimeError("الخزينة غير متاحة — لا تخزين مفتاح مزود: VaultDisabled")
    if value is None or value == "":
        vault.delete(BRAIN_API_KEY_SECRET, actor=actor)  # إلغاء صريح
        _BRAIN_API_KEY_CACHE.pop("value", None)
        return False
    try:
        vault.put(BRAIN_API_KEY_SECRET, str(value), scopes=[BRAIN_API_KEY_SCOPE], actor=actor)
    except Exception as exc:
        if "موجود" not in str(exc):
            raise
        vault.rotate(BRAIN_API_KEY_SECRET, str(value), actor=actor)  # تحديث قائم
    _BRAIN_API_KEY_CACHE["value"] = str(value)
    return True


def brain_set(values: dict) -> dict:
    """كتابة تعديلات إعدادات العقل في ملف التشغيل (كتابة ذرّية R-781، وضع 0600).

    R-813 (مراجعة المستشار): الحقل غير المرسل لا يُمس أبدًا — التحديث الجزئي
    حفظ للمرسل فقط (كان مسحًا ضمنيًا لكل ما لم يُرسل). القيمة الفارغة للمرسل
    تحذفه من الطبقة فتعود قيمة البيئة. المفتاح السري (OLLAMA_API_KEY) لا
    يمر من هنا — الخزينة المشفرة مساره (brain_api_key_set). فشل الكتابة يرتفع
    استثناءً — لا نجاح كاذبًا.
    """
    layer = brain_runtime_read()
    written = False
    for k in _BRAIN_RUNTIME_KEYS:
        if k == "OLLAMA_API_KEY" or k not in values:
            continue  # السر مساره الخزينة؛ غير المرسل لا يُمس (R-813)
        v = values[k]
        if v is None or (isinstance(v, str) and v == ""):
            layer.pop(k, None)
        else:
            layer[k] = v
        written = True
    if not written:
        return layer  # لا كتابة بلا داعٍ
    BRAIN_RUNTIME_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(BRAIN_RUNTIME_FILE, layer, file_mode=0o600)
    return layer

# ============================================================
# R-737 (البند ٢.٣ — أذنان): إعدادات السمع (تحويل كلام لنص)
# ============================================================
# معطل افتراضيًا (نمط Ollama R-704/R-736 — لا اتصال ضمني).
STT_ENABLED = _ollama_env("STT_ENABLED", "false").lower() == "true"
# أساس متوافق مع OpenAI لتحويل الكلام — البروتوكول واحد للسحابي والمحلي:
# POST {base}/audio/transcriptions. مثال سحابي (Groq):
# https://api.groq.com/openai/v1 — ومثال محلي (خادم whisper.cpp): العنوان
# الافتراضي أدناه (الخادم يقرر النموذج بنفسه فلا STT_MODEL مطلوب).
STT_BASE_URL = _ollama_env("STT_BASE_URL", "http://127.0.0.1:8080/v1")
# النموذج — None للخادم المحلي (يقرر بنفسه)، أو صريح للخدمة السحابية
# (مثال Groq: whisper-large-v3).
STT_MODEL = _ollama_env("STT_MODEL", None)
STT_API_KEY = _ollama_env("STT_API_KEY", None)
STT_TIMEOUT_SECONDS = float(_ollama_env("STT_TIMEOUT_SECONDS", "60"))
# حد حجم الرفع (25MiB — حد whisper-large-v3 المعتاد) — لا قراءة اعتباطية
STT_MAX_AUDIO_BYTES = int(_ollama_env("STT_MAX_AUDIO_BYTES", str(25 * 1024 * 1024)))

# ============================================================
# R-738 (البند ٣.٢ + ٢.٥ — بأمر المالك «ترسانة عالمية»): أدوات الويب
# والاستدلال وبوابة MCP والمنسّق
# ============================================================
# معطل افتراضيًا (نمط R-704/R-736/R-737 — لا اتصال ضمني)
WEB_TOOLS_ENABLED = _ollama_env("WEB_TOOLS_ENABLED", "false").lower() == "true"
# مزود البحث: searxng (ذاتي الاستضافة — افتراضي) أو tavily (سحابي)
SEARCH_PROVIDER = _ollama_env("SEARCH_PROVIDER", "searxng")
SEARCH_BASE_URL = _ollama_env("SEARCH_BASE_URL", "http://127.0.0.1:8888")
SEARCH_API_KEY = _ollama_env("SEARCH_API_KEY", None)
SEARCH_TIMEOUT_SECONDS = float(_ollama_env("SEARCH_TIMEOUT_SECONDS", "30"))
SEARCH_MAX_RESULTS = int(_ollama_env("SEARCH_MAX_RESULTS", "5"))
# جلب الصفحات: مهلة وحد حجم وسقف تحويلات (حارس SSRF داخل web_tools)
WEB_FETCH_TIMEOUT_SECONDS = float(_ollama_env("WEB_FETCH_TIMEOUT_SECONDS", "30"))
WEB_FETCH_MAX_BYTES = int(_ollama_env("WEB_FETCH_MAX_BYTES", str(2 * 1024 * 1024)))
WEB_FETCH_MAX_REDIRECTS = int(_ollama_env("WEB_FETCH_MAX_REDIRECTS", "3"))
# المنسّق (research.run): عدد المصادر التي تُقرأ في كل دورة بحث
RESEARCH_MAX_SOURCES = int(_ollama_env("RESEARCH_MAX_SOURCES", "3"))

# ============================================================
# R-740 (البند ٢.٤ — صوت): إعدادات النطق (TTS)
# ============================================================
# معطل افتراضيًا (نمط R-704/R-736/R-737/R-739 — لا اتصال ضمني).
TTS_ENABLED = _ollama_env("TTS_ENABLED", "false").lower() == "true"
# عقد OpenAI speech القياسي: POST {base}/audio/speech → بايتات صوت.
# سحابي (Groq: playai-tts) أو محلي متوافق (piper/kokoro بغلاف OpenAI).
TTS_BASE_URL = _ollama_env("TTS_BASE_URL", "http://127.0.0.1:8880/v1")
TTS_MODEL = _ollama_env("TTS_MODEL", None)
TTS_API_KEY = _ollama_env("TTS_API_KEY", None)
# صوت اختياري — None: الخادم المحلي يقرر
TTS_VOICE = _ollama_env("TTS_VOICE", None)
TTS_TIMEOUT_SECONDS = float(_ollama_env("TTS_TIMEOUT_SECONDS", "60"))
# حد طول النص المنطوق (2000 حرف) — لا نطق اعتباطي
TTS_MAX_TEXT_CHARS = int(_ollama_env("TTS_MAX_TEXT_CHARS", "2000"))

# ============================================================
# R-747 (البند ٣.٥ — أدوات الوسائط): توليد الصور — ذاتي الاستضافة فقط
# ============================================================
# بأمر المالك: «خدمة وسائط لا تتطلب إرسال البيانات لطرف ثالث» — LocalAI
# (عقد OpenAI Images). معطل افتراضيًا؛ والعميل يرفض أي مضيف عام قبل الاتصال
# (media_client.is_self_hosted): loopback/خاص/.internal/.flycast/.local/اسم خدمة.
MEDIA_ENABLED = _ollama_env("MEDIA_ENABLED", "false").lower() == "true"
MEDIA_BASE_URL = _ollama_env("MEDIA_BASE_URL", "http://127.0.0.1:8080/v1")
MEDIA_MODEL = _ollama_env("MEDIA_MODEL", None)
MEDIA_API_KEY = _ollama_env("MEDIA_API_KEY", None)
MEDIA_TIMEOUT_SECONDS = float(_ollama_env("MEDIA_TIMEOUT_SECONDS", "120"))
MEDIA_IMAGE_SIZE = _ollama_env("MEDIA_IMAGE_SIZE", "512x512")
MEDIA_ALLOWED_SIZES = ("256x256", "512x512", "768x768", "1024x1024")
MEDIA_MAX_IMAGE_BYTES = int(_ollama_env("MEDIA_MAX_IMAGE_BYTES", str(10 * 1024 * 1024)))
MEDIA_MAX_PROMPT_CHARS = int(_ollama_env("MEDIA_MAX_PROMPT_CHARS", "1000"))

# ============================================================
# R-739 (البند ٢.٢ — عينان): إعدادات الرؤية (تحليل الصور)
# ============================================================
# معطل افتراضيًا (نمط R-704/R-736/R-737 — لا اتصال ضمني).
VISION_ENABLED = _ollama_env("VISION_ENABLED", "false").lower() == "true"
# نموذج متعدد الوسائط (رؤية) — منفصل عن نموذج المحادثة؛ أمثلة:
# llava / qwen2.5vl (محلي)، أو نموذج رؤية لدى مزود متوافق OpenAI.
VISION_MODEL = _ollama_env("VISION_MODEL", None)
# حد حجم الصورة المرفوعة (10MiB) — لا قراءة اعتباطية
VISION_MAX_IMAGE_BYTES = int(_ollama_env("VISION_MAX_IMAGE_BYTES", str(10 * 1024 * 1024)))

# بوابة MCP — وصول منظومة آلاف أدوات الصناعة بعقد واحد (stdio/http).
# معطلة افتراضيًا؛ الخوادم بصيغة JSON في MCP_SERVERS:
# [{"name":"fs","transport":"stdio","command":"npx","args":[...]},
#  {"name":"remote","transport":"http","url":"https://..."}]
MCP_ENABLED = _ollama_env("MCP_ENABLED", "false").lower() == "true"
MCP_SERVERS = _ollama_env("MCP_SERVERS", "[]")

# ============================================================
# 7. إعدادات النواة الذكية (Core Model)
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
        # TOLERATED: malformed forbidden-words JSON — fall back to hardcoded default list (R-680)
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
# D-034 (قرار المالك 2026-10-17): في الإنتاج قائمة مصادر صريحة إلزامية —
# لا "*" ولا "null" (منفردة أو داخل قائمة) ولا قائمة فارغة. الرفض
# يُنفَّذ في validate_config() أدناه (فشل مغلق: RuntimeError عند الإقلاع).
# التطوير: تحذير فقط — القيد للإنتاج حصرًا.
if CORS_ORIGINS == ["*"] and not IS_PRODUCTION:
    warnings.warn("⚠️ CORS مفتوح للجميع — مقبول في التطوير فقط (D-034)")

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
        atomic_write_json(CONFIG_BACKUP_FILE, backup, ensure_ascii=False, indent=2)
    # TOLERATED: config backup is best-effort diagnostic — not required for correct startup (R-680)
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
    
    # التحقق من CORS في الإنتاج (D-034 — فشل مغلق)
    # قرار المالك: «CORS_ORIGINS في الإنتاج يجب أن يكون قائمة صريحة.
    # لا * ولا null. إذا كان ENV=production وCORS_ORIGINS="*" — التطبيق
    # يرفض الإقلاع (fail-closed)». "null" أصل يُصدره المتصفح للطلبات
    # غير المتجانسة ويُستخدم للتحايل على سياسات الأصل — يُرفض مثله.
    # الفحص على مستوى عناصر القائمة بعد تجريد المسافات: النجمة أو null
    # في أي موضع (منفردة أو داخل قائمة مختلطة) والقائمة الفارغة تُرفض.
    if IS_PRODUCTION:
        _origins = [o.strip() for o in CORS_ORIGINS]
        if (
            "*" in _origins
            or "null" in _origins
            or not any(_origins)
        ):
            errors.append(
                "❌ CORS في الإنتاج (D-034): قائمة مصادر صريحة مطلوبة — "
                "لا \"*\" ولا \"null\" (ولو داخل قائمة) ولا قائمة فارغة. "
                "اضبط CORS_ORIGINS بقائمة صريحة "
                "(مثال: CORS_ORIGINS=https://app.example.com)"
            )
    
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
