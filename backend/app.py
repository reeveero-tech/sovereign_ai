# backend/app.py
# 🌐 Sovereign AI Web Server - الخادم السيادي الكامل
# الإصدار: 4.0.0 - بوابة الوصول إلى الذكاء السيادي

"""
خادم الويب السيادي - نقطة الوصول الرئيسية للنظام.

الميزات:
- REST API كامل لجميع وظائف النظام
- WebSockets للمحادثة المباشرة والتفاعل الحي
- لوحة تحكم للسيد (Sovereign Control Panel)
- توثيق تلقائي (Swagger UI / ReDoc)
- مراقبة الحالة والصحة
- دعم CORS للاتصال من واجهات أمامية مختلفة
- تسجيل متقدم وتتبع الأخطاء
- أمان مع مفاتيح API وتحديد الصلاحيات
"""

import asyncio
import hashlib
import hmac
import json
import re  # R-824: تمييز الطلبات الإنشائية في مسار المحادثة
import time
import threading
import uuid
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum

import os
import shutil
import pathlib

from fastapi import (
    FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends,
    status, BackgroundTasks, Query, Header, File, UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, validator
import uvicorn

# مسار مجلد الواجهة الأمامية
_BACKEND_DIR = pathlib.Path(__file__).parent
_PROJECT_ROOT = _BACKEND_DIR.parent
FRONTEND_DIR = _PROJECT_ROOT / "frontend"

# استيراد Orchestrator وجميع المكونات
from orchestrator import get_orchestrator, SovereignOrchestrator, CycleResult, OrchestratorMode
from memory.core import get_core
from memory.dynamic import get_dynamic_memory
from memory.store import get_store
from memory.defense.stealth import get_stealth_defense
from memory.defense.polymorphic import get_polymorphic_defense
from consciousness.field import get_consciousness_field
from consciousness.identity_core import get_identity_core
from consciousness.self_model import get_self_model
from consciousness.awareness import get_awareness_engine
from consciousness.attention_engine import get_attention_engine
from consciousness.introspection import get_introspection_engine
from predictive.predictive_engine import get_predictive_engine
from predictive.predictive_controller import get_predictive_controller
from predictive.predictive_risk_manager import get_predictive_risk_manager
from simulation.simulation_controller import get_simulation_controller
from simulation.simulation_analyzer import get_simulation_analyzer
from sovereign.will import get_sovereign_will
from sovereign.alignment import get_sovereign_alignment
from sovereign.directives import get_sovereign_directives
from sovereign.controller import get_sovereign_controller
from quantum.quantum_controller import get_quantum_controller

import logging
logger = logging.getLogger(__name__)

# ============================================================
# التكوين والإعدادات
# ============================================================

# مفتاح السيد (للمصادقة)
# M1: يُقرأ من config (SOVEREIGN_KEY من متغير البيئة) بدلاً من توليد عشوائي غير محفوظ (LEGACY-ROOT-KEY read-only: عرض/حالة)
from config import SOVEREIGN_KEY as SOVEREIGN_API_KEY  # LEGACY-ROOT-KEY (read-only): بيانات اعتماد تاريخية
try:
    from backend.sovereign.keys.derivation import derive_key_hex as _derive_api_auth  # R-697 (D-033)
except ImportError:
    from sovereign.keys.derivation import derive_key_hex as _derive_api_auth  # R-697 (D-033)  # R-697 (D-033): مفتاح api_auth مشتق

# إعدادات CORS (السماح بالاتصال من جميع المصادر)
# M1: CORS من config (متغير البيئة CORS_ORIGINS) — ليس مفتوحاً دائماً
from config import CORS_ORIGINS as ALLOWED_ORIGINS
from config import MAX_USER_MESSAGES_PER_MINUTE
from rate_limit import SlidingWindowRateLimiter
from safety import SafetyGuard, ActionType

chat_rate_limiter = SlidingWindowRateLimiter(MAX_USER_MESSAGES_PER_MINUTE)
# R-737 (البند ٢.٣): حد السمع بحد المحادثة نفسه لكل IP — الرفع باهظ فلا باب مفتوح
stt_rate_limiter = SlidingWindowRateLimiter(MAX_USER_MESSAGES_PER_MINUTE)
# R-739 (البند ٢.٢): حد الرؤية بحد المحادثة نفسه لكل IP — الرفع باهظ فلا باب مفتوح
vision_rate_limiter = SlidingWindowRateLimiter(MAX_USER_MESSAGES_PER_MINUTE)
# R-740 (البند ٢.٤): حد النطق بحد المحادثة نفسه لكل IP — لا باب مفتوح
tts_rate_limiter = SlidingWindowRateLimiter(MAX_USER_MESSAGES_PER_MINUTE)
# R-747 (البند ٣.٥): حد معدل توليد الصور — نفس حد /chat
media_rate_limiter = SlidingWindowRateLimiter(MAX_USER_MESSAGES_PER_MINUTE)

# ============================================================
# طبقة الأمان السيادية (R-608) — إحياء safety.py
# ============================================================
safety_guard = SafetyGuard()

def enforce_input_safety(message_text: str, is_sovereign: bool = False) -> Optional[str]:
    """
    فحص أي رسالة تدخل النظام عبر طبقة الأمان.
    تُرجع رسالة الرفض إذا كانت خطيرة، أو None إذا كانت آمنة.
    """
    safe_text, needs_approval, reason = safety_guard.check_input(message_text, is_sovereign)
    if needs_approval:
        return safe_text
    return None

def enforce_chat_rate_limit(request: Request) -> None:
    """Throttle chat by the connection's direct client IP, without trusting forwarded headers."""
    client_host = request.client.host if request.client else "unknown"
    retry_after = chat_rate_limiter.check(client_host)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تم تجاوز حد رسائل المحادثة؛ أعد المحاولة بعد انتهاء فترة التقييد.",
            headers={"Retry-After": str(retry_after)},
        )

# ============================================================
# نماذج البيانات (Data Models)
# ============================================================

class ChatTurn(BaseModel):
    """R-786: دور سابق في المحادثة — سياق للعقل فقط (لا صلاحية تنفيذ)."""
    role: str = Field(..., pattern="^(user|assistant)$", description="user أو assistant")
    content: str = Field(..., min_length=1, max_length=4000, description="نص الدور")


class ChatMessage(BaseModel):
    """رسالة محادثة"""
    text: str = Field(..., min_length=1, max_length=10000, description="نص الرسالة")
    user_id: str = Field(default="anonymous", max_length=100, description="معرف المستخدم")
    session_id: Optional[str] = Field(default=None, description="معرف الجلسة")
    # R-786: آخر أدوار المحادثة (اختياري) — بدونها كان كل سؤال يصل العقل يتيمًا بلا سياق
    history: Optional[List[ChatTurn]] = Field(default=None, max_length=20, description="أدوار سابقة (حتى 20)")
    # R-789: مفتاح المالك (اختياري) — يوسّع أدوات المحادثة من القراءة إلى كل السجل؛ لا يُسجل
    api_key: Optional[str] = Field(default=None, max_length=512, description="مفتاح المالك (اختياري)", repr=False)
    # R-810/813 (البند ٢): اختيار النموذج لهذه المحادثة — يصل فعليًا نداء العقل
    # (بلا قيمة: النموذج الفعّال العام). يُحفظ مع سجل المحادثة ويُستعاد عند فتحها.
    model: Optional[str] = Field(default=None, max_length=100, description="النموذج لهذه المحادثة (اختياري)", repr=False)
    # R-800: ملفات مساحة العمل المرفقة بالرسالة (للمالك) — الوكيل يقرؤها بأدوات files.*
    file_ids: Optional[List[str]] = Field(default=None, max_length=10, description="معرفات ملفات مرفقة")
    # R-800: المشروع النشط — تعليماته وروابطه تُمرَّر للوكيل (للمالك فقط)
    project_id: Optional[str] = Field(default=None, max_length=40, description="معرف المشروع النشط")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "من أنت؟",
                "user_id": "user_123",
                "session_id": None
            }
        }
    )


class ChatResponse(BaseModel):
    """رد المحادثة"""
    reply: str
    status: str
    cycle_id: str
    processing_time_ms: float
    timestamp: float
    # R-787: أدوات النظام الحقيقية التي استُدعيت لهذا الرد (أثر موقّع لكل منها)
    tools_used: List[str] = []
    # R-789: حالة حلقة الوكيل (completed/answered_from_results/planner_failed/...) — None في المسار القديم
    agent_status: Optional[str] = None
    # R-817 إحياء: زمن دورة المنسق وحدها (قبل تكوين الرد) — تمييز عن الزمن الكلي
    cycle_time_ms: Optional[float] = None
    # R-814 (البند ٥): حكم المراجع المستقل (brain/skipped_*/no_reply/invalid_review_reply)
    # يُسجَّل ويُعرض — لا يقلب نتيجة التطبيق أبدًا
    reviewer: Optional[Dict[str, Any]] = None
    # R-824: وسائط أنشأها النظام لهذا الرد (صورة/فيديو) — روابط موقّعة قابلة للعرض مباشرة
    media: List[Dict[str, Any]] = []
    # R-824: السؤال كما فهمه النظام من سياق المحادثة (متابعة «وكم سكانها؟» ⇒ سؤال مكتمل)
    resolved_question: Optional[str] = None


class SovereignCommand(BaseModel):
    """أمر من السيد"""
    command: str = Field(..., description="اسم الأمر")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="معاملات الأمر")
    api_key: str = Field(..., description="مفتاح API الخاص بالسيد")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "command": "reset",
                "parameters": {},
                "api_key": "your_api_key_here"
            }
        }
    )


class SovereignCommandResponse(BaseModel):
    """رد أمر السيد"""
    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float


class SystemStatusResponse(BaseModel):
    """حالة النظام"""
    status: str
    version: str
    orchestrator: Dict[str, Any]
    components: Dict[str, Any]
    uptime_seconds: float
    timestamp: float


class ResetRequest(BaseModel):
    """طلب إعادة تهيئة"""
    component: Optional[str] = Field(default=None, description="اسم المكون (إذا كان None، يعيد تهيئة الكل)")
    preserve_data: bool = Field(default=False, description="الحفاظ على البيانات")
    api_key: str = Field(..., description="مفتاح API الخاص بالسيد")


# ============================================================
# دورة حياة التطبيق (Lifespan)
# ============================================================

def _bootstrap_signing_key() -> None:
    """R-818 (أمر المالك «إحياء كل ما هو ميت»): أول إقلاع على قرص جديد.

    KeyRing فارغ ⇒ كل أحداث السجل تُرفض فشلًا مغلقًا (R-635) — النظام يبدو
    حيًا (health=healthy) لكن لُبّه المعرفي معطّل (المراقبة/الأيض/التطور كلها
    تُخطئ). الإحياء: إن لم يوجد مفتاح نشاط، يُولَّد مفتاح Ed25519 أولي
    ويُحفظ ويُسجل في التاريخ — مرة واحدة فقط (الاقتلاعات التالية تجد مفتاحًا
    ولا تفعل شيئًا). التعطيل الصريح للاختبارات المعزولة:
    KEYRING_AUTOBOOTSTRAP=0
    """
    if str(os.getenv("KEYRING_AUTOBOOTSTRAP", "1")).strip().lower() in (
        "0", "false", "no", "off",
    ):
        return
    try:
        from backend.sovereign.keys import KeyRing

        _kr = KeyRing()
        _kr.load_from_disk()
        if _kr.get_active_key() is not None:
            return  # المفتاح موجود سلفًا — لا إعادة توليد أبدًا
        _rec = _kr.generate_new_ed25519_key(reason="initial-auto-bootstrap")
        if not _kr.save_to_disk():
            logger.error("❌ R-818: فشل حفظ KeyRing بعد توليد المفتاح الأولي")
            return
        logger.info(
            "🔑 R-818: مفتاح توقيع أولي مولَّد (%s) — السجل السيادي حي الآن",
            _rec.key_id,
        )
    except Exception as _bk_exc:  # TOLERATED: لا يكسر الإقلاع أبدًا
        logger.warning(f"R-818: تعذر تهيئة مفتاح التوقيع الأول: {_bk_exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    دورة حياة التطبيق - يتم تنفيذها عند بدء وإيقاف الخادم.
    """
    # بدء التشغيل
    logger.info("🚀 بدء تشغيل خادم Sovereign AI...")

    # R-818: إحياء مفتاح التوقيع قبل تهيئة أي مكوّن يعتمد السجل
    _bootstrap_signing_key()

    # تهيئة Orchestrator
    orchestrator = get_orchestrator()
    app.state.orchestrator = orchestrator
    
    # تخزين وقت بدء التشغيل
    app.state.start_time = time.time()
    
    # تسجيل نجاح بدء التشغيل
    logger.info("✅ خادم Sovereign AI جاهز")
    # R-617: لا يُسجّل المفتاح نفسه أبدًا — فقط بصمته (أول 8 أحرف من sha256)
    _key_fingerprint = hashlib.sha256(SOVEREIGN_API_KEY.encode()).hexdigest()[:8]
    logger.info(f"🔑 مفتاح API للسيد (بصمة فقط): {_key_fingerprint}...")
    logger.info("📖 التوثيق: http://localhost:8000/docs")
    # طبقة توافق: تشغيل محرك NexusCore فعليًا (يصلح state=initializing الدائم)
    # انظر backend/compat/nexus_lifecycle.py — لا تعديل للأصل، بل استدعاء engine.start()
    # ملاحظة: تُستخدم النسخة غير المتزامنة لأننا داخل حلقة حدث نشطة (lifespan)
    try:
        await ensure_nexus_running_async()
    except Exception as _nexus_lifecycle_err:
        logger.warning(f"⚠️ NexusCore lifecycle: {_nexus_lifecycle_err}")

    # R-732 (البند ٣.٦): المجدول — يُبنى من البيئة عند كل إقلاع (معطل افتراضيًا)
    from scheduler import build_from_env as _build_scheduler
    app.state.scheduler = _build_scheduler()
    app.state.scheduler.start()
    try:  # R-798: النواة تقرأ حالة المجدول الحية
        from selfdev import wiring as _sd_wiring
        _sd_wiring.bind_scheduler(app.state.scheduler.status)
    except Exception as exc:  # TOLERATED: بلا ربط يُعلن مصدر المجدول فارغًا فقط
        logger.warning("R-798: تعذر ربط المجدول بالنواة: %s", exc)
    logger.info(f"⏱️ المجدول: {app.state.scheduler.reason}")
    # R-791 (V6 ٦.٩.٤): حلقة الاستقلال — أهداف دائمة يعمل عليها العقل بلا طلب
    try:
        import goals as _goals_mod
        app.state.autonomy = _goals_mod.build_from_env()
        app.state.autonomy.start()
        logger.info(f"🧭 الاستقلال: {app.state.autonomy.reason}")
    except Exception as _auto_exc:  # TOLERATED: الحلقة إضافة؛ فشل بنائها يُعلن ولا يكسر الإقلاع
        logger.warning("R-791: تعذر بناء حلقة الاستقلال (%s)", type(_auto_exc).__name__)
    
    # R-816 (أمر المالك «إحياء كل ما هو ميت»): عقد الولاء المعقّم حي —
    # backend/Mr.py (R-686: نزع الفتيل) كان غير مربوط بالنظام الحي بأمر
    # المرحلة ١؛ أمر الإحياء الجديد يوصله: تهيئة + ربط بالسيد عند الإقلاع.
    # الربط بمادة مفتاح السيد المشتق (بصمة الهاش فقط تُخزن داخل العقد — لا
    # خام)، ومحاولة الربط المزدوج مستحيلة (يُربط فقط إذا كان العقد بلا سيد)،
    # وفشل الإحياء لا يكسر الإقلاع أبدًا (عزل لا موت — عقد R-686 نفسه).
    try:
        from Mr import initialize_loyalty_core
        _loyalty_contract = initialize_loyalty_core()
        if _loyalty_contract.get_status().get("master_bound"):
            logger.info("🛡️ عقد الولاء: مربوط بالسيد سلفًا (بلا إعادة ربط)")
        else:
            _loyalty_bound = _loyalty_contract.bind_master(
                _derive_api_auth("api_auth")
            )
            logger.info(
                "🛡️ عقد الولاء: %s",
                "مربوط بالسيد (SEALED)" if _loyalty_bound else "بلا ربط — يُعلن بصدق",
            )
        app.state.loyalty = _loyalty_contract
    except Exception as _loyalty_exc:  # TOLERATED: الإحياء إضافة؛ فشله يُعلن ولا يوقف الخادم
        logger.warning("R-816: تعذر إحياء عقد الولاء (%s)", type(_loyalty_exc).__name__)

    yield
    
    # إيقاف التشغيل
    logger.info("🛑 إيقاف خادم Sovereign AI...")
    await app.state.scheduler.stop()
    if getattr(app.state, "autonomy", None) is not None:
        app.state.autonomy.stop()
    app.state.orchestrator.stop()
    logger.info("✅ تم إيقاف الخادم")


# ============================================================
# إنشاء تطبيق FastAPI
# ============================================================

app = FastAPI(
    title="Sovereign AI - الذكاء السيادي",
    description="""
    ## خادم الذكاء السيادي
    
    هذا الخادم يوفر واجهة برمجة تطبيقات (API) للتفاعل مع الذكاء السيادي.
    
    ### الميزات الرئيسية:
    - **محادثة ذكية** - تحدث مع الذكاء السيادي عبر `/chat`
    - **تحكم السيد** - أوامر خاصة للسيد عبر `/sovereign/command`
    - **مراقبة النظام** - عرض حالة النظام والمكونات
    - **إعادة تهيئة** - إعادة ضبط النظام أو مكوناته
    - **WebSocket** - محادثة مباشرة في الوقت الفعلي
    
    ### المصادقة:
    - أوامر السيد تتطلب مفتاح API
    - يمكن للمستخدمين العاديين استخدام `/chat` بدون مصادقة
    """,
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# ============================================================
# إضافة CORS Middleware
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ضغط الاستجابات الكبيرة لتحسين زمن النقل (R-502)
app.add_middleware(
    GZipMiddleware,
    minimum_size=1024,
    compresslevel=6,
)
from api import get_api_router
app.include_router(get_api_router())

# ============================================================
# NexusCore REST API (R-608) — إحياء nexus/api_gateway
# ============================================================
try:
    import sys as _sys
    _repo_root = _BACKEND_DIR.parent
    if str(_repo_root) not in _sys.path:
        _sys.path.insert(0, str(_repo_root))
    from nexus.api_gateway import NexusRouter
    app.include_router(NexusRouter.router)
    logger.info("✅ NexusCore REST API مفعّل (/nexus/*)")
except Exception as _nexus_err:
    logger.warning(f"⚠️ NexusCore REST API غير مفعّل: {_nexus_err}")

# ============================================================
# طبقة توافق: ربط دورة حياة NexusCore (يُصلح state=initializing الدائم)
# + إحياء guardian عبر /guardian/status (قراءة فقط)
# لا يُحذف أو يُعدَّل أي ملف أصلي — هذه إضافات توافقية فقط.
# ============================================================
from backend.compat import (
    ensure_nexus_running_async,
    guardian_status_snapshot,
    generate_live_recommendations,
    get_pending_recommendations,
)
from backend.compat.nexus_router_compat import register_compat_router

# إضافة نقطة /guardian/status — إحياء guardian/ بشكل قابل للتشخيص دون تفعيل EmergencyBreaker
def _resources_disk_path():
    """R-734: مجلد البيانات الفعلي (config.DATA_DIR) — يُقاس قرصه؛ إن لم يوجد
    بعد يُقاس أقرب أصل موجود (نفس نظام الملفات)."""
    from pathlib import Path as _Path
    from config import DATA_DIR
    path = _Path(DATA_DIR)
    while not path.exists() and path != path.parent:
        path = path.parent
    return path


@app.get("/system/resources")
async def system_resources_endpoint():
    """R-734 (البند ٢.٧): موارد النظام مقاسة من نظام التشغيل — لا تقدير ولا سر،
    ولا مسار مطلق (تسمية «data» فقط)."""
    import system_resources
    return system_resources.snapshot(disk_path=_resources_disk_path(), disk_label="data")


@app.get("/scheduler/status")
async def scheduler_status():
    """R-732 (البند ٣.٦): حالة المجدول — تفعيل/سبب/مهام/آخر تشغيل وبصمته (لا سر)."""
    sched = getattr(app.state, "scheduler", None)
    if sched is None:
        return {"enabled": False, "running": False,
                "reason": "المجدول لم يُبنَ بعد (الخادم لم يكمل الإقلاع)", "tasks": []}
    return sched.status()


@app.get("/defects/report")
async def defects_report():
    """R-743 (البند ٤.٣): آخر تقرير عيوب أنتجته دورة defects.scan — قراءة فقط.

    لا يشغّل فحصًا (التشغيل عبر السجل فقط: المجدول أو /tools/invoke — كل
    تشغيل يترك أثرًا موقّعًا). بلا دورة سابقة يعلن ذلك بصدق مع السبب."""
    import defect_scan
    report = defect_scan.get_worklist().last_report()
    if report is None:
        return {"report": None,
                "reason": "لم تُشغَّل دورة فحص بعد — المهمة self_defect_scan "
                          "تعمل عند تفعيل المجدول (SOVEREIGN_SCHEDULER=1 — قرار "
                          "المالك) أو باستدعاء defects.scan عبر /tools/invoke"}
    return {"report": report}


def _defect_scan_payload() -> Dict[str, Any]:
    """R-743: مصادر حقيقية → قائمة العيوب. تُستدعى من داخل run_due (والمجدول
    ممسك بقفله) فتقرأ المهام مباشرة لا عبر status() — لا قفل مزدوج."""
    import defect_scan
    try:
        health = _health_payload()
    except Exception:  # R-743: تعذر اللقطة نفسه عيب يُرصد (health_unavailable) لا انهيار
        health = None
    sched = getattr(app.state, "scheduler", None)
    sched_snapshot = ({"tasks": [t.to_dict() for t in list(sched.tasks)]}
                      if sched is not None else None)
    hb = _load_heartbeat()
    if hb is not None:
        threshold = min(max(10.0, 3.0 * hb["interval"]), 120.0)
        if time.time() - hb["epoch"] > threshold:
            hb = None  # منتهي المهلة = غائب (نفس حكم /supervisor/status)
    now = time.time()
    report = defect_scan.get_worklist().scan(
        health=health, scheduler=sched_snapshot, heartbeat=hb, now=now)
    # R-744 (البند ٤.٢): كل دورة تترك مدخلًا إلحاقيًا في سجل التطور (disk_log
    # namespace=evolution). best-effort: لا يمس التقرير المُعاد — فبصمته تطابق
    # result_fingerprint في حدث tool_invoked الموقّع.
    import evolution_ledger
    evolution_ledger.get_ledger().record_cycle("defects.scan", report, now=now)
    # R-745 (البند ٤.٥): العيوب المفتوحة → اقتراحات تنتظر قرار المالك (لا تنفيذ ذاتي)
    import improvement_proposals
    improvement_proposals.get_book().ingest(report, now=now)
    return report


def _self_monitor_payload() -> Dict[str, Any]:
    """R-794 (٤.٦): مراقبة ذاتية موسّعة — قرص/أدوات/سجل التطور/الاستقلال/الأهداف/
    الاقتراحات → عيوب بنفس شكل defect_scan → اقتراحات تنتظر المالك (لا تنفيذ ذاتي)."""
    import experience
    import evolution_ledger
    import goals as _goals
    import improvement_proposals
    import self_monitor

    def _autonomy():
        loop = getattr(app.state, "autonomy", None)
        return loop.status() if loop is not None else None

    sources = {
        "disk": _local_volume_status,
        "tool_stats": lambda: experience.get_store().tool_stats(),
        "ledger_verify": lambda: evolution_ledger.get_ledger().verify(),
        "autonomy": _autonomy,
        "goals": lambda: _goals.GoalStore().state(),
        "proposals": lambda: improvement_proposals.get_book().list(),
    }
    now = time.time()
    report = self_monitor.get_monitor().run(sources, now=now)
    improvement_proposals.get_book().ingest_scoped(report, now=now, prefix="selfmon:")
    return report


def _benchmark_payload() -> Dict[str, Any]:
    """R-746 (البند ٤.٤): دورة المقارنة بالمراجع العامة — زمن/جودة/تغطية.

    التغطية من السجل الفعلي والأعلام (لا ادعاء)؛ الجودة فقط إن كان العقل مفعّلًا
    (BENCHMARK_QUALITY_N مسائل، افتراضي 3، حد 10)؛ الفجوات القابلة للقياس
    تغذي اقتراحات ٤.٥ (التنفيذ بموافقة المالك فقط)."""
    import config
    import external_benchmark
    import improvement_proposals
    from tool_registry import get_registry
    names = {t["name"] for t in get_registry().list_tools()}
    flags = {"web_tools": bool(getattr(config, "WEB_TOOLS_ENABLED", False)),
             "media": bool(getattr(config, "MEDIA_ENABLED", False))}
    mind = None
    if config.OLLAMA_ENABLED and config.OLLAMA_MODEL:
        import ollama_client
        mind = lambda system, question: ollama_client.chat(system, question)  # noqa: E731
    try:
        n = max(1, min(int(os.getenv("BENCHMARK_QUALITY_N", "3")), 10))
    except ValueError:  # TOLERATED: قيمة غير رقمية → الافتراضي المعلن
        n = 3
    now = time.time()
    report = external_benchmark.run(_health_payload, names, flags, mind=mind,
                                    quality_n=n, now=now)
    external_benchmark.get_store().save(report)
    improvement_proposals.get_book().ingest(
        external_benchmark.gaps_as_defects(report), now=now)
    return report


@app.get("/benchmark/report")
async def benchmark_report():
    """R-746 (البند ٤.٤): آخر تقرير مقارنة بالمراجع العامة — قراءة فقط."""
    import external_benchmark
    report = external_benchmark.get_store().last()
    if report is None:
        return {"report": None,
                "reason": "لم تُشغَّل دورة مقارنة بعد — المهمة external_benchmark "
                          "تعمل عند تفعيل المجدول (SOVEREIGN_SCHEDULER=1 — قرار المالك) "
                          "أو باستدعاء benchmark.run عبر /tools/invoke",
                "references": external_benchmark.REFERENCES}
    return {"report": report}


def _proposal_decide(proposal_id: str, decision: str, note: str = None,
                     commit: str = None) -> Dict[str, Any]:
    """R-745: المرحلة الأولى لقرار المالك — تحضير بلا تغيير حالة؛ التطبيق
    في _proposal_apply بعد نجاح الأثر الموقّع (لا أثر = لا تنفيذ)."""
    import improvement_proposals
    return improvement_proposals.get_book().prepare(
        proposal_id, decision, note=note, commit=commit, now=time.time())


def _proposal_apply(prepared: Dict[str, Any]) -> Dict[str, Any]:
    import improvement_proposals
    return improvement_proposals.get_book().apply_prepared(prepared)


@app.get("/proposals")
async def proposals_list():
    """R-745 (البند ٤.٥): اقتراحات التحسين — قراءة فقط. القرار عبر /tools/invoke
    (proposals.decide بمفتاح المالك وأثر موقّع)، والتنفيذ بالدورة الذرية لا هنا."""
    import improvement_proposals
    items = improvement_proposals.get_book().list()
    return {"proposals": items,
            "counts": {s: sum(1 for i in items if i["status"] == s)
                       for s in ("proposed", "approved", "rejected",
                                 "implemented", "suppressed")}}


@app.get("/proposals/{proposal_id}/file")
async def proposal_file(proposal_id: str):
    """R-745: ملف التوصية (markdown) — يُحفظ ويُنفَّذ بالدورة الذرية المعتادة."""
    import improvement_proposals
    try:
        md = improvement_proposals.get_book().render_markdown(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"اقتراح غير موجود: {proposal_id}")
    return Response(content=md, media_type="text/markdown; charset=utf-8")


@app.get("/self/monitor")
async def self_monitor_report():
    """R-794 (٤.٦): آخر تقرير مراقبة ذاتية — قراءة فقط (التشغيل عبر السجل/المجدول)."""
    import self_monitor
    report = self_monitor.get_monitor().last_report()
    if report is None:
        return {"report": None,
                "reason": "لم تُشغَّل دورة مراقبة ذاتية بعد — المهمة self_monitor تعمل عند "
                          "تفعيل المجدول (SOVEREIGN_SCHEDULER=1 — قرار المالك) أو باستدعاء "
                          "self.monitor عبر /tools/invoke"}
    return {"report": report}


@app.get("/selfdev/status")
async def selfdev_status():
    """R-796: محرك التطوير الذاتي — مهام/حالات/نتائج CI (بيانات وصفية فقط، لا شيفرة ولا سر).

    الصياغة عبر الأداة selfdev.tick (المجدول أو /tools/invoke)؛ التطبيق والاختبار RED→GREEN
    في CI على فرع work/selfdev-*؛ الترقية إلى main قرار المالك."""
    import self_develop
    return await asyncio.to_thread(self_develop.get_engine().status)


def _selfdev_tick_payload() -> Dict[str, Any]:
    """R-796: دورة تطوير ذاتي — تسحب نتائج CI، تستوعب اقتراحات ٤.٥ القابلة للإصلاح،
    وتصوغ مسودة واحدة بالعقل (لا كتابة ملفات في الإنتاج).

    R-798: صارت دورة كاملة موحدة: النواة (جمع كل الإشارات ⇒ أولوية ⇒ عقل الاقتراح ⇒
    توجيه) ثم المحرك ثم محرك الأهداف المتعذرة. حقول R-796 العليا محفوظة."""
    from selfdev import wiring
    return wiring.full_cycle(now=time.time())


def _attachments_note(file_ids: List[str]) -> str:
    """R-800: وصف حقيقي للمرفقات + مقتطف قصير؛ الوكيل يكمل بـ files.read/files.analyze."""
    from workspace.service import get_workspace, WorkspaceError
    ws = get_workspace()
    lines = []
    for fid in file_ids[:5]:
        try:
            r = ws.read(fid, 0, 1200)
        except WorkspaceError as exc:
            lines.append(f"- {fid}: {exc}")
            continue
        f = r["file"]
        lines.append(f"- {f['id']} «{f['name']}» نوع {f['kind']} ({f['size']} بايت، {r['total_chars']} حرف مستخرج)"
                     f"\n  مقتطف: {r['text'][:1200]!r}")
    return ("\n\n[ملفات مرفقة في مساحة العمل — استعمل files.read (offset للمتابعة) أو files.analyze "
            "أو files.unpack للأرشيف أو files.convert/files.create للتصدير]\n" + "\n".join(lines))


def _project_note(project_id: str) -> str:
    """R-800: سياق المشروع النشط (اسم/وصف/تعليمات/روابط) — من مساحة العمل الحقيقية لا نص مزروع."""
    from workspace.service import get_workspace, WorkspaceError
    try:
        p = get_workspace().get_project(project_id)
    except WorkspaceError:
        return ""
    parts = [f"\n\n[المشروع النشط {p['id']} «{p['name']}»]"]
    if p.get("description"):
        parts.append(f"الوصف: {p['description'][:800]}")
    if p.get("instructions"):
        parts.append(f"تعليمات المالك للمشروع: {p['instructions'][:2000]}")
    if p.get("links"):
        parts.append("روابط المشروع: " + ", ".join(p["links"][:10]))
    parts.append(f"ملفات المشروع: استعمل files.list مع project_id={p['id']}")
    return "\n".join(parts)


@app.get("/ws/settings")
async def ws_settings(x_sovereign_key: Optional[str] = Header(None)):
    """R-800: كل ما يخص المشروع للوحة الإعدادات — بلا أي قيمة سرية (أسماء المتغيرات المضبوطة فقط)."""
    if not x_sovereign_key or not verify_api_key(x_sovereign_key):
        raise HTTPException(status_code=401, detail="مفتاح المالك مطلوب (X-Sovereign-Key)")

    def build():
        import config
        from workspace.service import get_workspace
        caps = _capabilities_payload()
        import tool_registry
        names = sorted(t["name"] for t in tool_registry.get_registry().list_tools())
        secret_like = ("KEY", "SECRET", "TOKEN", "PASSWORD")
        env_names = ["SUPABASE_URL", "SUPABASE_SECRET_KEY", "OLLAMA_BASE_URL",
                     "OLLAMA_MODEL", "OLLAMA_PROTOCOL", "OLLAMA_TIMEOUT_SECONDS", "OLLAMA_NUM_CTX",
                     "CORS_ORIGINS", "WEB_TOOLS_ENABLED", "SOVEREIGN_SCHEDULER", "SOVEREIGN_AUTONOMY",
                     "SOVEREIGN_AUTONOMY_INTERVAL", "SOVEREIGN_SELFDEV_INTERVAL", "VISION_ENABLED",
                     "VISION_MODEL", "STT_ENABLED", "TTS_ENABLED", "MEDIA_ENABLED", "MEDIA_BASE_URL",
                     "SEARCH_PROVIDER", "SEARCH_BASE_URL", "SEARCH_API_KEY", "STT_BASE_URL",
                     "TTS_BASE_URL", "GITHUB_TOKEN", "AI_ENVIRONMENT",
                     # R-824: العقل السحابي الاحتياطي واستوديو الوسائط والبحث العالمي
                     "CLOUD_BRAIN_ENABLED", "CLOUD_BRAIN_URL", "CLOUD_BRAIN_MODEL", "CLOUD_BRAIN_API_KEY",
                     "MEDIA_EXTERNAL_PROVIDERS", "WORLD_SEARCH_ENABLED", "WORLD_SEARCH_LANGS"]
        # مفتاح المالك: يُعلن ضبطه فقط عبر المحمّل القائم (لا قراءة مباشرة للجذر — حارس الاشتقاق)
        env = [{"name": "OWNER_KEY (مفتاح المالك)", "set": bool(SOVEREIGN_API_KEY), "value": None}]
        for n in env_names:
            v = os.getenv(n)
            env.append({"name": n, "set": bool(v),
                        "value": (None if any(t in n for t in secret_like) else (v[:120] if v else None))})
        try:
            connectors = _connectors_status_payload()
        except Exception as exc:  # TOLERATED: حالة الموصلات تُعلن خطأها
            connectors = {"error": type(exc).__name__}
        def _cfg(n, d=None):
            return getattr(config, n, d)

        def _local(url):
            return not url or "127.0.0.1" in str(url) or "localhost" in str(url)
        ws_status = get_workspace().status()
        # R-800: الموصلات والتكاملات الفعلية — الحالة مشتقة من الإعداد الحي لا من قائمة مزروعة
        integrations = [
            {"id": "github", "name": "GitHub (مستودعات عامة)", "tool": "github.repo",
             "ready": True, "detail": "قراءة أي مستودع عام عبر واجهة GitHub العامة"
             + ("" if not os.getenv("GITHUB_TOKEN") else " — برمز GITHUB_TOKEN")},
            {"id": "web_fetch", "name": "الاتصال بأي موقع", "tool": "web.fetch",
             "ready": bool(_cfg("WEB_TOOLS_ENABLED")), "detail": "جلب وقراءة أي رابط HTTP(S) عام"},
            {"id": "web_search", "name": "البحث في الويب", "tool": "web.search",
             "ready": bool(_cfg("WEB_TOOLS_ENABLED")) and not _local(_cfg("SEARCH_BASE_URL"))
             or (str(_cfg("SEARCH_PROVIDER")) == "tavily" and bool(_cfg("SEARCH_API_KEY"))),
             "detail": f"المزود {_cfg('SEARCH_PROVIDER')}" + (" — لا خادم بحث مضبوط" if _local(_cfg("SEARCH_BASE_URL")) else "")},
            {"id": "supabase", "name": "Supabase (القرص والتخزين)", "tool": "disk.status",
             "ready": bool(ws_status.get("durable")), "detail": f"تخزين الملفات: {ws_status.get('storage')}"},
            {"id": "brain", "name": "العقل (Ollama ذاتي الاستضافة)", "tool": "brain.status",
             "ready": bool(_cfg("OLLAMA_ENABLED")), "detail": str(_cfg("OLLAMA_MODEL") or "")},
            {"id": "vision", "name": "تحليل الصور (نموذج رؤية)", "tool": "files.analyze",
             "ready": bool(_cfg("VISION_ENABLED") and _cfg("VISION_MODEL")), "detail": str(_cfg("VISION_MODEL") or "VISION_MODEL غير مضبوط")},
            {"id": "media", "name": "توليد الصور", "tool": "media.image",
             "ready": bool(_cfg("MEDIA_ENABLED")) and not _local(_cfg("MEDIA_BASE_URL")), "detail": "خادم توليد ذاتي الاستضافة (MEDIA_BASE_URL)"},
            # R-824: استوديو الوسائط — جاهز دائمًا (المصمم المحلي حتمي) ويعلن سلسلة مولداته الفعلية
            {"id": "media_studio", "name": "استوديو الصور والفيديو", "tool": "media.create",
             "ready": True, "detail": _media_studio_detail()},
            {"id": "cloud_brain", "name": "العقل السحابي الاحتياطي", "tool": None,
             "ready": bool(_cloud_brain_status().get("enabled")),
             "detail": str(_cloud_brain_status().get("model") or "CLOUD_BRAIN_ENABLED غير مفعّل")},
            {"id": "stt", "name": "تفريغ الصوت", "tool": "files.analyze",
             "ready": bool(_cfg("STT_ENABLED")), "detail": "STT_BASE_URL"},
            {"id": "tts", "name": "تحويل النص إلى صوت", "tool": None,
             "ready": bool(_cfg("TTS_ENABLED")), "detail": "TTS_BASE_URL"},
            {"id": "ffmpeg", "name": "معالجة الفيديو والصوت (ffmpeg)", "tool": "files.analyze",
             "ready": bool(shutil.which("ffprobe") or _media_ffmpeg()), "detail": "ffprobe/ffmpeg في الحاوية أو imageio-ffmpeg المضمّن"},
        ]
        return {
            "integrations": integrations,
            "project": {"name": "Sovereign AI", "version": getattr(config, "VERSION", None) or "4.0.0",
                        "repo": "https://github.com/reeveero-tech/sovereign_ai",
                        "app": os.getenv("FLY_APP_NAME"), "region": os.getenv("FLY_REGION"),
                        "image": os.getenv("FLY_IMAGE_REF"), "machine": os.getenv("FLY_MACHINE_ID"),
                        "environment": os.getenv("AI_ENVIRONMENT")},
            "capabilities": caps.get("capabilities"), "summary": caps.get("summary"),
            "tools": names, "env": env, "connectors": connectors,
            "brain": {"model": getattr(config, "OLLAMA_MODEL", None),
                      "protocol": getattr(config, "OLLAMA_PROTOCOL", None),
                      "enabled": bool(getattr(config, "OLLAMA_ENABLED", False))},
            "workspace": ws_status,
        }
    return await asyncio.to_thread(build)


@app.get("/selfdev/nucleus")
async def selfdev_nucleus_view():
    """R-798: النواة — الإشارات النشطة وتكرارها، آخر التحليلات ومساراتها (بلا شيفرة ولا سر)."""
    from selfdev import wiring
    return await asyncio.to_thread(lambda: wiring.get_nucleus().status())


@app.get("/selfdev/unmet")
async def selfdev_unmet_view():
    """R-798: محرك الأهداف المتعذرة — كل هدف عجز عنه النظام وسلّم تصعيده (بلا شيفرة ولا سر)."""
    from selfdev import wiring
    return await asyncio.to_thread(lambda: wiring.get_unmet().status())


@app.get("/evolution/ledger")
async def evolution_ledger_view(limit: int = 50):
    """R-744 (البند ٤.٢): سجل التطور — قراءة فقط، بلا سر (أعداد ومعرّفات وبصمات).

    durable يعلن بصدق هل المداخل تُلحق بـ disk_log (Supabase) أم في الذاكرة فقط."""
    import evolution_ledger
    led = evolution_ledger.get_ledger()
    limit = max(1, min(int(limit), evolution_ledger.BUFFER_SIZE))
    return {"status": led.status(), "verify": led.verify(),
            "entries": led.entries()[-limit:]}


@app.get("/guardian/status")
async def guardian_status():
    """حالة نظام الحارس (قراءة فقط) — إحياء guardian/ عبر طبقة توافق"""
    return guardian_status_snapshot()


# ============================================================
# R-816: عقد الولاء حي — نقاط وصول عقد الولاء المعقّم (backend/Mr.py)
# الحالة علنية صادقة (لا سر فيها)، ورفع العزل للسيد وحده بمفتاحه.
# ============================================================

@app.get("/loyalty/status")
async def loyalty_status():
    """حالة عقد الولاء — علنية صادقة (لقطة سلبية، بلا أي سر)"""
    try:
        from Mr import get_loyalty_status
        s = get_loyalty_status()
        return {
            "status": "success",
            "data": {
                "state": s.get("state"),
                "loyal": s.get("loyal"),
                "master_bound": s.get("master_bound"),
                "quarantined": s.get("quarantined"),
                "quarantine_reason": s.get("quarantine_reason"),
                "violations_count": s.get("violations_count"),
                "death_paths": s.get("death_paths"),
            },
        }
    except Exception as _exc:  # عقد العزل لا موت — الفشل يُعلن بصدق
        return {"status": "error", "detail": f"{type(_exc).__name__}: {_exc}"}


@app.post("/loyalty/release")
async def loyalty_release(request: Request, x_sovereign_key: Optional[str] = Header(None)):
    """رفع عزل عقد الولاء — للسيد وحده (X-Sovereign-Key) بقرار موثق"""
    if not x_sovereign_key or not verify_api_key(x_sovereign_key):
        raise HTTPException(status_code=401, detail="مفتاح المالك مطلوب (X-Sovereign-Key)")
    try:
        body = await request.json()
    except Exception:
        body = {}
    decision = str(body.get("decision") or "رفع عزل عقد الولاء — قرار السيد")
    try:
        from Mr import get_contract
        ok = get_contract().release_quarantine(x_sovereign_key, decision)
        s = get_contract().get_status()
        return {
            "status": "success" if ok else "rejected",
            "released": ok,
            "state": s.get("state"),
            "quarantined": s.get("quarantined"),
        }
    except Exception as _exc:
        return {"status": "error", "detail": f"{type(_exc).__name__}: {_exc}"}


# إضافة نقطة /nexus/recommendations/live — إصلاح فجوة حقيقية:
# النقطة الأصلية /nexus/recommendations تعيد قائمة فارغة ثابتة رغم أن
# RecommendationEngine مسجل فعلاً في المحرك (كموّن recommender).
# هذه النقطة الجديدة تُولّد توصيات فعلية من المكوّن المسجل.
# (لا يُحذف أو يُعدّل الملف الأصلي — هذه إضافة توافقية فقط.)
from pydantic import BaseModel as _BM

class RecommendationContext(_BM):
    """سياق التوصية — يُمرر إلى RecommendationEngine.generate()"""
    confidence: float = 1.0
    trend: str = "neutral"
    anomaly_count: int = 0
    model_config = {"extra": "allow"}  # يسمح بحقول إضافية في السياق


@app.post("/nexus/recommendations/live")
async def nexus_recommendations_live(context: RecommendationContext):
    """توليد توصيات فعلية من RecommendationEngine المسجل في NexusCore"""
    return generate_live_recommendations(context.model_dump())


# إضافة نقطة /nexus/recommendations/pending — يصلح فجوة المسار الأصلي
# GET /nexus/recommendations (يعيد قائمة فارغة ثابتة). هذه النقطة تُعيد
# التوصيات المعلقة الفعلية من المكوّن المشترك (accepted is None).
@app.get("/nexus/recommendations/pending")
async def nexus_recommendations_pending():
    """التوصيات المعلقة من RecommendationEngine المسجل في NexusCore"""
    return get_pending_recommendations()


# إصلاح المسار الأصلي GET /nexus/recommendations (R-615):
# المسار الأصلي في nexus/api_gateway/router.py يعيد قائمة فارغة ثابتة رغم
# أن RecommendationEngine مسجل. هذه الطبقة تُسجّل route جديد لنفس المسار
# يُعيد التوصيات المعلقة الفعلية. (FastAPI يُطابق آخر route مسجّل أولاً —
# لذلك هذا يُصلح المسار الأصلي دون تعديل الملف الأصلي.)
register_compat_router(app)

# ============================================================
# مدخل التوجيه (R-687 — المرحلة ٢ من META_SYSTEM): يقرأ سجل العزل الدائم
# ويرفض توجيه الطلبات للمكونات المعزولة (503 محدد + جسم خطأ صريح) بينما
# تستمر بقية المكونات بالعمل. لا يستورد Mr إطلاقًا (قيد R-686) — الفصل
# عبر ملف السجل؛ والحارس المعزول عملية مستقلة لا تُستورد هنا (أمر المالك).
# ============================================================
from backend.circuit_breaker import register_circuit_breaker

register_circuit_breaker(app)


# ============================================================
# المرحلة 2 (ROADMAP_V2): نقطة نهاية /ledger/verify — تقرير التحقق
# من اليدجر (KeyRing + Merkle Anchors). للقراءة فقط.
# ============================================================
_LEDGER_VERIFY_LOCK = threading.Lock()
# R-807: حالة التحقق التزايدي — نفس نمط R-768 في SovereignCore
# (بصمة بادئة sha256 + بصمة مفاتيح + بصمة مراس): البادئة المغطاة بالتحقق
# تبقى صالحة ما دامت بايتاتها لم تتغير والمفاتيح التي تعتمد عليها
# التصنيفات كما هي؛ الإلحاقات الجديدة تُتحقق وحدها O(delta) والبادئة
# تتمدد. أي تعديل في البادئة/تقلّص/تغيّر مفاتيح ⇒ فحص كامل صادق.
# R-805 علّمنا أن بصمة (الحجم+mtime) لا تكفي: اليدجر الحي إلحاقي بكثافة
# (~3.5 حدث/ث على الإنتاج) فالبصمة تتغير بين كل استدعاءين ⇒ الكاش لا
# يصيب أبدًا وكل استدعاء أعاد حساب O(n) كاملًا (مثبت حيًا بعد نشر R-805:
# أول استدعاء 35ث ثم مهلات 60ث و300ث و500ث متتابعة).
_LEDGER_VERIFY_STATE: Dict[str, Any] = {
    "result": None,
    "prefix_size": 0,        # بايتات سجل الأحداث المغطاة بالتحقق (على حد سطر مكتمل)
    "prefix_hash": None,     # sha256 لهذه البادئة
    "verified_count": 0,      # عدد أحداث البادئة
    "stats": None,           # عدادات البادئة التراكمية (القابلة للجمع)
    "anchors_fp": None,     # بصمة ملف المراسي
    "anchors": None,         # (anchored_count, trusted_count, nominal_count, anchors_verification)
    "keyring_fp": None,
    "ts": 0.0,
}


def _ledger_keyring_fingerprint(keyring) -> str:
    """R-807: بصمة المفاتيح التي يعتمد عليها تصنيف كل حدث (نمط R-768) —
    تغيّرها (إضافة/تقاعد/ثقة) يُبطل الاستئناف ويفرض فحصًا كاملًا."""
    parts = []
    try:
        for rec in keyring.list_keys():
            parts.append(
                f"{rec.key_id}|{getattr(rec, 'key_type', '')}|{rec.public_key}"
                f"|{rec.status.value}|{rec.valid_from}|{rec.valid_until}"
            )
    except Exception:  # TOLERATED: بصمة فاشلة = لا استئناف (فحص كامل)
        return ""
    return hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()


def _ledger_stream_read(ledger_path, prefix_size):
    """R-807: قراءة السجل مرة واحدة بثلاث نواتج صادقة:

    - (prefix_hash, tail_bytes, True) إذا كانت أول prefix_size بايت قابلة
      للقراءة كاملة (البادئة المرشحة للاستئناف — صلاحيتها تُقارن بالمخزنة).
    - (whole_hash, whole_bytes, False) إذا لا بادئة صالحة ⇒ فحص كامل.
    - (None, b"", False) عند فشل القراءة (الملف غائب/خلل) ⇒ لا استئناف ولا
      ادعاء؛ المتصل يعالج الملف الغائب كحالة صادقة (سجل فارغ).

    السطر الأخير غير المكتمل (بلا \\n — كاتب أثناء القراءة) يُستثنى لاحقًا
    من الفحص ومن حد البادئة الجديدة: يُرى في الاستدعاء القادم مكتملًا."""
    try:
        if ledger_path is None or not pathlib.Path(ledger_path).exists():
            return None, b"", False
        size = pathlib.Path(ledger_path).stat().st_size
        with open(ledger_path, "rb") as f:
            if 0 < prefix_size <= size:
                h = hashlib.sha256()
                remaining = prefix_size
                while remaining > 0:
                    chunk = f.read(min(1 << 16, remaining))
                    if not chunk:
                        break
                    h.update(chunk)
                    remaining -= len(chunk)
                if remaining == 0:
                    return h.hexdigest(), f.read(), True
                f.seek(0)  # الملف أقصر من البادئة (تقلّص) ⇒ فحص كامل
            data = f.read()
        return hashlib.sha256(data).hexdigest(), data, False
    except Exception:  # TOLERATED: قراءة فاشلة = لا استئناف ولا تعطل النقطة
        return None, b"", False


def _ledger_prefix_hash(ledger_path, prefix_size, old_prefix_size=0,
                        old_prefix_hash=None, tail=None) -> Optional[str]:
    """R-807/808: بصمة أول prefix_size بايت كنقطة استئناف — مع شهادة
    اتساق (تصحيح TOCTOU من مراجعة المستشار): البادئة الجديدة تُقرأ من
    القرص مرة أخرى ولا تُنشر بصمتها إلا إذا (١) ظل جزؤها القديم بنفس
    البصمة المخزنة (لم يتغير أثناء التصنيف) و(٢) ذيلها بايت-لطابق الأسطر
    المصنفة فعلاً — لا شهادة على بايتات لم تُفحص. أي اختلاف = None
    (لا استئناف للنقطة الجديدة، والفحص الكامل صادق في كل الأحوال)."""
    try:
        if ledger_path is None or prefix_size is None or prefix_size <= 0:
            return None
        if not pathlib.Path(ledger_path).exists():
            return None
        if pathlib.Path(ledger_path).stat().st_size < prefix_size:
            return None  # تقلّص بعد التصنيف — لا شهادة على ما لم يُقرأ
        h = hashlib.sha256()
        old_part = 0
        # (١) الجزء القديم: إن تغيّرت بصمته فقد تعدل الملف أثناء التصنيف
        if old_prefix_hash and old_prefix_size and 0 < old_prefix_size < prefix_size:
            ho = hashlib.sha256()
            with open(ledger_path, "rb") as f:
                remaining = old_prefix_size
                while remaining > 0:
                    chunk = f.read(min(1 << 16, remaining))
                    if not chunk:
                        return None
                    ho.update(chunk)
                    h.update(chunk)
                    remaining -= len(chunk)
            if ho.hexdigest() != old_prefix_hash:
                return None
            old_part = old_prefix_size
        # (٢) باقي البادئة الجديدة: بايت-لطابقة للأسطر المصنفة من الذيل
        with open(ledger_path, "rb") as f:
            f.seek(old_part)
            remaining = prefix_size - old_part
            offset = 0
            while remaining > 0:
                chunk = f.read(min(1 << 16, remaining))
                if not chunk:
                    return None
                if tail is not None:
                    if tail[offset:offset + len(chunk)] != chunk:
                        return None  # ذيل القرص ≠ الذيل المصنف — لا شهادة
                    offset += len(chunk)
                h.update(chunk)
                remaining -= len(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _ledger_classify_lines(lines, verifier) -> Dict[str, int]:
    """R-807: تصنيف أسطر أحداث (قابل للجمع) — قلب الفحص الكامل والتزايدي
    معًا: كل حدث يُصنف مرة واحدة (verified/unverifiable/invalid/legacy)."""
    stats = {
        "total_events": len(lines),
        "verified_with_key": 0,
        "unverifiable": 0,
        "invalid": 0,
        "legacy_pre_keyring": 0,
    }
    for line in lines:
        try:
            event = json.loads(line)
        except Exception:
            stats["invalid"] += 1
            continue
        if "key_id" not in event:
            stats["legacy_pre_keyring"] += 1
        result = verifier.verify_event(event)
        status_val = result.status.value
        if status_val == "verified":
            stats["verified_with_key"] += 1
        elif status_val == "unverifiable_missing_key":
            stats["unverifiable"] += 1
        elif status_val == "invalid":
            stats["invalid"] += 1
    return stats


def _ledger_merge_stats(base: Dict[str, int], delta: Dict[str, int]) -> Dict[str, int]:
    """R-807: دمج عدادات قابلة للجمع (البادئة + الذيل الجديد)."""
    return {k: (base.get(k, 0) + delta.get(k, 0)) for k in
            ("total_events", "verified_with_key", "unverifiable", "invalid", "legacy_pre_keyring")}

def _ledger_complete_lines_bytes(data: bytes):
    """R-807/808: أسطر مكتملة فقط من كتلة بايتات — يُقصّ السطر الأخير غير
    المكتمل (بلا فاصل سطر — كاتب أثناء القراءة) ويعيد (نص الأسطر
    المكتملة، بايتاتها). R-808: الحد يُبحث في البايتات لا في النص — إزاحة
    الحرف (حمولات عربية متعددة البايتات) لا تساوي إزاحة البايت، وإرجاع
    حد نصي كعدد بايتات كان يضع نقطة الاستئناف داخل سطر محسوب."""
    cut = data.rfind(b"\n")
    if cut < 0:
        return "", 0
    return data[:cut + 1].decode("utf-8", errors="replace"), cut + 1


def _ledger_verify_store_state(state, ctx, kfp, anchors_fp, new_prefix_hash):
    """R-807: تخزين نقطة الاستئناف بعد فحص ناجح — فشل البصمة = لا
    استئناف (يبقى القديم؛ الفحص الكامل صادق في كل الأحوال)."""
    if new_prefix_hash is not None:
        state["prefix_size"] = ctx["complete_bytes"]
        state["prefix_hash"] = new_prefix_hash
        state["verified_count"] = ctx["total_events"]
        state["stats"] = dict(ctx["stats"])
        state["anchors_fp"] = anchors_fp
        state["anchors"] = (ctx["anchored_count"], ctx["trusted_count"],
                            ctx["nominal_count"], ctx["anchors_verification"])
        state["keyring_fp"] = kfp
        state["ts"] = time.time()



@app.get("/ledger/verify")
def ledger_verify():
    """R-762: دالة متزامنة ⇒ FastAPI ينفّذها في مجمّع الخيوط لا في حلقة الأحداث
    (كانت async تتحقق من كل توقيع داخل الحلقة فتحجب /health وكل الطلبات).
    single-flight: القفل يجعل الطلبات المتزامنة تنتظر الحساب الجاري وتأخذ
    نتيجته بدل إطلاق حساب جديد لكل طلب.

    R-807: تحقق تزايدي صادق (نمط R-768 في SovereignCore) — البادئة
    المتحقق منها تُهشم فقط (sha256) لا تُعاد فحصها ما دامت بايتاتها
    ومفاتيح التصنيف ومراسيه لم تتغير؛ أحداث الذيل الجديدة وحدها تُفحص
    O(delta). الدليل الحي على حاجة التزايدي: بعد نشر R-805 (كاش بصمة
    الحجم+mtime) ظل الاستدعاء المتتابع على الإنتاج يعيد الحساب الكامل —
    اليدجر الحي يُلحق ~3.5 حدث/ث فبصمة الحجم تتغير بين كل استدعاءين،
    وأول استدعاء بعد النشر أخذ 35ث ثم مهلات 60ث→300ث→500ث متتابعة على
    معالج مشترك مستقطَع. أي تقلّص/تعديل بادئة/تغيّر مفاتيح ⇒ فحص كامل.
    النتيجة تصف لقطة صادقة: snapshot.prefix_bytes وsnapshot.incremental."""
    with _LEDGER_VERIFY_LOCK:
        from backend.sovereign.ledger import LedgerAnchor
        from backend.sovereign.keys import KeyRing, SignatureVerifier

        anchor = LedgerAnchor()
        keyring = KeyRing()
        keyring.load_from_disk()
        verifier = SignatureVerifier(keyring)
        kfp = _ledger_keyring_fingerprint(keyring)
        state = _LEDGER_VERIFY_STATE

        # بصمة المراس (تغيّرها يعيد فحص قسم المراس؛ البادئة تبقى صالحة)
        try:
            if anchor.anchors_path is not None and pathlib.Path(anchor.anchors_path).exists():
                st = pathlib.Path(anchor.anchors_path).stat()
                anchors_fp = (st.st_size, st.st_mtime)
            else:
                anchors_fp = None
        except Exception:
            anchors_fp = None

        prefix_hash, tail, prefix_ok = _ledger_stream_read(
            anchor.ledger_path, state.get("prefix_size", 0)
        )
        # R-808: بصمة مفاتيح فاشلة (سلسلة فارغة) لا تُفعّل الاستئناف —
        # فشل قراءة المفاتيح يعني أن التصنيفات غير معلومة، لا أنها ثابتة
        resume = (
            prefix_ok
            and prefix_hash is not None
            and bool(kfp)
            and state.get("prefix_hash") == prefix_hash
            and state.get("stats") is not None
            and state.get("keyring_fp") == kfp
        )

        if resume:
            # استئناف: البادئة صالحة ⇒ نفحص الذيل الجديد وحده (O(delta)).
            # السطر الأخير غير المكتمل يُستثنى (بلا \n) — يُرى لاحقًا مكتملًا.
            tail_text, complete_bytes = _ledger_complete_lines_bytes(tail)
            tail_lines = [l for l in tail_text.split("\n") if l.strip()]
            delta = _ledger_classify_lines(tail_lines, verifier)
            stats = _ledger_merge_stats(state["stats"], delta)
            total_events = stats["total_events"]
            new_prefix_size = state["prefix_size"] + complete_bytes

            if state.get("anchors_fp") == anchors_fp and state.get("anchors") is not None:
                anchored_count, trusted_count, nominal_count, anchors_verification = state["anchors"]
                # التغطيات نسب على الإجمالي الجديد (المراسي نفسها لكن الإجمالي نما)
                anchors_verification = dict(anchors_verification)
                anchors_verification["total_events"] = total_events
                if total_events > 0:
                    anchors_verification["trusted_coverage"] = trusted_count / total_events
                    anchors_verification["nominal_coverage"] = nominal_count / total_events
            else:
                # R-808: اتحاد النطاقات (لا مجموع الأطوال — التداخل يُحسب
                # مرة) + مقام لقطة التصنيف نفسها لا قراءة أخرى
                anchors_list = anchor.list_anchors()
                anchored_set = set()
                nominal_set = set()
                for a in anchors_list:
                    for i in range(a["batch_start"], a["batch_end"] + 1):
                        anchored_set.add(i)
                        nominal_set.add(i)
                anchored_count = len(anchored_set)
                nominal_count = len(nominal_set)
                anchors_verification = anchor.verify_all_anchors(keyring=keyring)
                trusted_count = anchors_verification.get("trusted_events_count", 0)
                anchors_verification = dict(anchors_verification)
                anchors_verification["total_events"] = total_events
                if total_events > 0:
                    anchors_verification["trusted_coverage"] = trusted_count / total_events
                    anchors_verification["nominal_coverage"] = nominal_count / total_events
                else:
                    anchors_verification["trusted_coverage"] = 0.0
                    anchors_verification["nominal_coverage"] = 0.0
            incremental = True
        else:
            # فحص كامل صادق: لا بادئة صالحة (أول مرة/تقلّص/تعديل/مفاتيح تغيّرت).
            # R-807: المحرك الموحّد _ledger_verify_compute (أُحيي بهذا الاستدعاء —
            # كان منطق الفحص الكامل مكررًا داخليًا) — نفس انضباط الأسطر المكتملة.
            # الملف كاملًا لا «الذيل» — فشل الاستئناف لا يعني أن البادئة القديمة
            # لا تزال تُقرأ من القرص؛ نقرأ الكل قراءة واحدة صادقة.
            _, whole, _ = _ledger_stream_read(anchor.ledger_path, 0)
            full_result, ctx = _ledger_verify_compute(data=whole, incremental=False)
            state["result"] = full_result
            # R-808: بصمة من بايتات التصنيف نفسها (ctx) — لا إعادة قراءة
            _ledger_verify_store_state(state, ctx, kfp, anchors_fp, ctx.get("prefix_hash"))
            return full_result

        result = {
            "ledger_summary": {
                "total_events": total_events,
                "verified_with_key": stats["verified_with_key"],
                "anchored_events": anchored_count,
                "unverifiable": stats["unverifiable"],
                "invalid": stats["invalid"],
                "legacy_pre_keyring": stats["legacy_pre_keyring"],
            },
            "anchors": {
                "total": anchors_verification["total_anchors"],
                "verified": anchors_verification["root_verified_count"],
                "failed": anchors_verification["failed"],
                "root_verified": anchors_verification["root_verified_count"],
                "trusted": anchors_verification["trusted_count"],
                "details": [
                    {
                        "anchor_id": d["anchor_id"],
                        "batch": d["batch"],
                        "sig_format": d["sig_format"],
                        "root_verified": d["root_verified"],
                        "signature_verified": d["signature_verified"],
                        "key_trusted": d["key_trusted"],
                        "trusted": d["trusted"],
                    }
                    for d in anchors_verification["details"]
                ],
            },
            "keyring_stats": keyring.stats(),
            "anchored_coverage_pct": round(
                (anchored_count / total_events) * 100, 2
            ) if total_events else 0.0,
            "trusted_coverage_pct": round(
                anchors_verification["trusted_coverage"] * 100, 2
            ),
            "nominal_coverage_pct": round(
                anchors_verification["nominal_coverage"] * 100, 2
            ),
            "trusted_events_count": anchors_verification["trusted_events_count"],
            "total_events": anchors_verification["total_events"],
            "timestamp": time.time(),
            # R-807: وصف اللقطة بصراحة — ما غطاه التحقق وكيف (لا ادعاء «الآن»)
            "snapshot": {
                "prefix_bytes": new_prefix_size,
                "incremental": incremental,
                "verified_prefix_events": total_events,
            },
        }

        # تخزين نقطة الاستئناف الجديدة (فشل البصمة = لا استئناف، لا تعطيل)
        ctx = {
            "stats": stats,
            "total_events": total_events,
            "anchored_count": anchored_count,
            "trusted_count": trusted_count,
            "nominal_count": nominal_count,
            "anchors_verification": anchors_verification,
            "complete_bytes": new_prefix_size,
        }
        # R-808: تجديد البصمة بشهادة اتساق — الجزء القديم بنفس بصمته والذيل
        # بايت-لطابق الأسطر المصنفة؛ وإلا فلا نقطة استئناف جديدة (لا شهادة
        # على بايتات لم تُفحص — تصحيح TOCTOU)
        _ledger_verify_store_state(state, ctx, kfp, anchors_fp,
                                   _ledger_prefix_hash(anchor.ledger_path, new_prefix_size,
                                                       state["prefix_size"], state["prefix_hash"], tail))
        state["result"] = result
        return result


def _ledger_verify_compute(data: Optional[bytes] = None, incremental: bool = False):
    """
    تقرير التحقق من اليدجر السيادي (R-807: محرك الفحص الكامل الموحّد —
    يستدعيه ledger_verify حين لا بادئة صالحة للاستئناف؛ أُحيي بهذا الدور
    بعد أن كان منطق الفحص الكامل سيتكرر داخليًا):

    - عدد الأحداث المُتحقَّق منها بالمفتاح (KeyRing)
    - عدد المراسي (Merkle Anchors)
    - عدد الأحداث المحمية بمرساة
    - عدد الأحداث المجهولة/الفاشلة

    R-807: نفس انضباط الأسطر المكتملة — السطر الأخير الممزق (كاتب أثناء
    القراءة) لا يُصنَّف «تالفًا»؛ يُرى في الاستدعاء القادم مكتملًا.
    يعيد (النتيجة، سياق التخزين) — السياق يحمل عدادات البادئة للاستئناف.
    """
    from backend.sovereign.ledger import LedgerAnchor
    from backend.sovereign.keys import KeyRing, SignatureVerifier

    # تحميل KeyRing
    keyring = KeyRing()
    keyring.load_from_disk()

    # تحميل اليدجر والمراسي
    anchor = LedgerAnchor()
    if data is None:
        _, data, _ = _ledger_stream_read(anchor.ledger_path, 0)

    # أسطر مكتملة فقط (انضباط R-807)
    whole_text, complete_bytes = _ledger_complete_lines_bytes(data)
    lines = [l for l in whole_text.split("\n") if l.strip()]

    # تحليل كل الأحداث (تحقق من التوقيع)
    verifier = SignatureVerifier(keyring)
    stats = _ledger_classify_lines(lines, verifier)
    total_events = stats["total_events"]

    # عدد الأحداث المُغطاة بالمراسي — اتحاد النطاقات (R-808: النطاقات
    # المتداخلة لا تُحسب مرتين؛ مجموع الأطوال كان يبالغ في التغطية)
    anchors_list = anchor.list_anchors()
    anchored_events = set()
    nominal_events = set()
    for a in anchors_list:
        for i in range(a["batch_start"], a["batch_end"] + 1):
            anchored_events.add(i)
            nominal_events.add(i)

    # التحقق من كل المراسي
    # R-642/R-643: يُميّز التغطية الموثوقة تشخريًًا (trusted) من الاسمية
    anchors_verification = anchor.verify_all_anchors(keyring=keyring)
    trusted_count = anchors_verification.get("trusted_events_count", 0)
    nominal_count = len(nominal_events)
    # R-808: مقام واحد متسق — تغطيات المراس على لقطة التصنيف نفسها لا
    # على قراءة أخرى داخل verify_all_anchors (الملف ينمو بين القراءتين)
    anchors_verification["total_events"] = total_events
    if total_events > 0:
        anchors_verification["trusted_coverage"] = trusted_count / total_events
        anchors_verification["nominal_coverage"] = nominal_count / total_events
    else:
        anchors_verification["trusted_coverage"] = 0.0
        anchors_verification["nominal_coverage"] = 0.0

    result = {
        "ledger_summary": {
            "total_events": total_events,
            "verified_with_key": stats["verified_with_key"],
            "anchored_events": len(anchored_events),
            "unverifiable": stats["unverifiable"],
            "invalid": stats["invalid"],
            "legacy_pre_keyring": stats["legacy_pre_keyring"],
        },
        # R-647: توافق قديم — anchors["verified"] بمعناه السابق (فحص الجذر)
        # + حقول الثقة الجديدة (root_verified, trusted, details)
        "anchors": {
            "total": anchors_verification["total_anchors"],
            "verified": anchors_verification["root_verified_count"],
            "failed": anchors_verification["failed"],
            "root_verified": anchors_verification["root_verified_count"],
            "trusted": anchors_verification["trusted_count"],
            "details": [
                {
                    "anchor_id": d["anchor_id"],
                    "batch": d["batch"],
                    "sig_format": d["sig_format"],
                    "root_verified": d["root_verified"],
                    "signature_verified": d["signature_verified"],
                    "key_trusted": d["key_trusted"],
                    "trusted": d["trusted"],
                }
                for d in anchors_verification["details"]
            ],
        },
        "keyring_stats": keyring.stats(),
        "anchored_coverage_pct": round(
            (len(anchored_events) / total_events) * 100, 2
        ) if total_events else 0.0,
        "trusted_coverage_pct": round(
            anchors_verification["trusted_coverage"] * 100, 2
        ),
        "nominal_coverage_pct": round(
            anchors_verification["nominal_coverage"] * 100, 2
        ),
        "trusted_events_count": anchors_verification["trusted_events_count"],
        "total_events": anchors_verification["total_events"],
        "timestamp": time.time(),
        # R-807: وصف اللقطة بصراحة — ما غطاه التحقق وكيف (لا ادعاء «الآن»)
        "snapshot": {
            "prefix_bytes": complete_bytes,
            "incremental": incremental,
            "verified_prefix_events": total_events,
        },
    }
    ctx = {
        "stats": stats,
        "total_events": total_events,
        "anchored_count": len(anchored_events),
        "trusted_count": trusted_count,
        "nominal_count": nominal_count,
        "anchors_verification": anchors_verification,
        "complete_bytes": complete_bytes,
        # R-808: الشهادة من بايتات التصنيف نفسها في الذاكرة — لا إعادة قراءة
        # (تصحيح TOCTOU): البادئة المخزنة هي حرفيًا ما صُنف
        "prefix_hash": (hashlib.sha256(data[:complete_bytes]).hexdigest()
                        if complete_bytes > 0 else None),
    }
    return result, ctx


# ============================================================
# نقاط API العامة (بدون مصادقة)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """الصفحة الرئيسية — R-786: واجهة المحادثة النظيفة (frontend/chat/).

    الواجهة القديمة (لوحة SOVRA) باقية بلا تعديل على /console.
    """
    chat_index = FRONTEND_DIR / "chat" / "index.html"
    if chat_index.exists():
        return HTMLResponse(content=chat_index.read_text(encoding="utf-8"))
    return await console()


@app.get("/classic", response_class=HTMLResponse)
async def classic_chat():
    """R-800: واجهة المحادثة السابقة (R-786..R-799) محفوظة كما هي — الجذر صار التطبيق الكامل."""
    classic = FRONTEND_DIR / "chat" / "classic.html"
    if classic.exists():
        return HTMLResponse(content=classic.read_text(encoding="utf-8"))
    return await console()


@app.get("/console", response_class=HTMLResponse)
async def console():
    """R-786: لوحة SOVRA التقنية القديمة — كما كانت على الجذر قبل R-786."""
    frontend_index = FRONTEND_DIR / "index.html"
    if frontend_index.exists():
        return HTMLResponse(content=frontend_index.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Sovereign AI</h1><p>Frontend not found</p>")


@app.get("/agent/ledger")
async def agent_ledger_report():
    """
    تقرير سجل أفعال الوكيل التقني (المرحلة 6 من ROADMAP_V2).
    يُوثّق كل تعديل قام به الوكيل — لا أفعال خفية.
    """
    from backend.sovereign.agent_ledger import AgentLedger

    ledger = AgentLedger()
    return ledger.full_report()


# R-788: كانت async تحسب الدرجة داخل حلقة الأحداث — التحقق من كل توقيع في السجل
# (138k حدثًا حيًا) حجب /health وكل الطلبات دقائق (Fly أعلن الفحص critical، py-spy:
# MainThread في _score_ledger_integrity). الآن نمط R-762: دالة متزامنة (مجمّع الخيوط)
# + single-flight + نتيجة مخزنة SOVEREIGNTY_SCORE_TTL ثانية (افتراضي 300) — طلب عام
# واحد لم يعد يوقف الخادم، وطلبات متزامنة لا تطلق حسابًا O(n) لكل منها.
_SCORE_LOCK = threading.Lock()
_SCORE_STATE: Dict[str, Any] = {"ts": 0.0, "result": None, "computing": False,
                                "started": 0.0, "error": None}
_SCORE_DONE = threading.Event()


def _score_worker() -> None:
    """R-788a: الحساب في خيط خلفي واحد — لا طلب HTTP ينتظره أكثر من مهلة قصيرة."""
    st = _SCORE_STATE
    try:
        result = _sovereignty_score_payload()
        with _SCORE_LOCK:
            st["result"], st["ts"], st["error"] = result, time.time(), None
    except Exception as e:  # TOLERATED: يُعرض نصًا في الرد التالي، لا يُبتلع
        with _SCORE_LOCK:
            st["error"] = f"{type(e).__name__}: {e}"
    finally:
        with _SCORE_LOCK:
            st["computing"] = False
        _SCORE_DONE.set()


def _sovereignty_score_cached(wait_s: Optional[float] = None) -> Dict[str, Any]:
    """R-788/R-788a: single-flight + تخزين + انتظار محدود.

    الدليل الحي بعد R-788: الحساب على آلة shared-cpu-1x مستنفدة رصيد الدفع (سرقة معالج 95%،
    `forensics/R-788a_live_evidence.txt`) استغرق >20 دقيقة — دالة متزامنة وحدها تحمي حلقة
    الأحداث لكنها تُبقي الطلب معلقًا وتحتجز خيطًا. الآن: الحساب في خيط خلفي واحد؛ الطلب
    ينتظر حتى SOVEREIGNTY_SCORE_WAIT ثانية (20)؛ إن لم ينته ⇒ آخر نتيجة مخزنة معلّمة بعمرها
    (`cache.stale`) أو `status=computing` صريحًا — لا رقم مختلق أبدًا.
    """
    ttl = float(os.getenv("SOVEREIGNTY_SCORE_TTL", "300") or 300)
    if wait_s is None:
        wait_s = float(os.getenv("SOVEREIGNTY_SCORE_WAIT", "20") or 20)
    st = _SCORE_STATE
    with _SCORE_LOCK:
        fresh = st["result"] is not None and (time.time() - st["ts"]) < ttl
        if not fresh and not st["computing"]:
            st["computing"], st["started"] = True, time.time()
            _SCORE_DONE.clear()
            threading.Thread(target=_score_worker, name="sovereignty-score",
                             daemon=True).start()
    if not fresh:
        _SCORE_DONE.wait(timeout=max(0.0, wait_s))
    with _SCORE_LOCK:
        result, ts, computing = st["result"], st["ts"], st["computing"]
        error, started = st["error"], st["started"]
    if result is None:
        out: Dict[str, Any] = {
            "status": "computing" if computing else "error",
            "detail": ("الحساب يجري في الخلفية — أعد الطلب بعد قليل" if computing
                       else f"فشل الحساب: {error}"),
            "computing_for_s": round(time.time() - started, 1) if computing else None,
        }
        return out
    out = dict(result)
    age = round(time.time() - ts, 1)
    out["cache"] = {"computed_at_unix": round(ts, 3), "age_s": age,
                    "stale": age >= ttl, "refreshing": computing,
                    "last_error": error}
    if "composite" in out:  # R-680: المُركّب يبقى آخر مفتاح (عقد «قابل للجدل»)
        out["composite"] = out.pop("composite")
    return out


@app.get("/sovereignty/score")
def sovereignty_score():
    """
    درجة السيادة (Sovereignty Score) — المرحلة 5 من ROADMAP_V2.
    يقيس المسافة بين 'يعمل' و 'سيادي' برقم واحد (0-100).

    R-680: يُعيد جدول المؤشرات الأولية (primitives) + المقياس
    المُركّب (composite) في آخر سطر مع علامة "قابل للجدل".
    R-788: متزامنة عمدًا (مجمّع الخيوط) + single-flight + تخزين مؤقت.
    R-788a: الحساب في خيط خلفي؛ الطلب لا ينتظر أكثر من SOVEREIGNTY_SCORE_WAIT —
    إن لم تتوفر نتيجة بعد ⇒ 202 مع `status=computing` (لا رقم مختلق).
    """
    out = _sovereignty_score_cached()
    if out.get("status") == "computing":
        return JSONResponse(status_code=202, content=out)
    if out.get("status") == "error":
        return JSONResponse(status_code=503, content=out)
    return out


def _sovereignty_score_payload() -> Dict[str, Any]:
    """حمولة /sovereignty/score — تخدم النقطة وأداة السجل sovereignty.score
    (R-729 — البند ٣.١) بنفس المنطق: مصدر واحد لا نسختين تتباعدان."""
    from backend.sovereign.score import SovereigntyScorer
    from backend.sovereign.primitives import Primitives
    from backend.sovereign.composite import Composite

    scorer = SovereigntyScorer()
    report = scorer.compute()

    # R-680f: ربط فعلي بـ pytest من خلال تقرير JUnit (provenance).
    # الملف يُولّده CI أو المستخدم بـ: python -m pytest --junitxml=forensics/pytest_results.xml
    # إذا الملف غير موجود → tests_passing_ratio = 0 (غير متاح، لا يمنح نقاطاً مجاناً).
    # R-680f: مسار واحد قياسي فقط — لا اعتماد على أثر محلي (مثل /tmp/...)
    _junit_path = None
    _junit_std = pathlib.Path(__file__).resolve().parent.parent / "forensics" / "pytest_results.xml"
    if _junit_std.exists():
        _junit_path = str(_junit_std)

    # R-680: إضافة المؤشرات الأولية + الرقم المُركّب مع علامة "قابل للجدل"
    # تُحسب المؤشرات الأولية من ملفات المستودع (لا من تشغيل pytest).
    # يُحسب الرقم المُركّب باستخدام composite.py (المُعدّل بـ R-680).
    primitives_obj = Primitives()
    composite_obj = Composite(primitives_obj, junit_xml_path=_junit_path)
    composite_result = composite_obj.compute()

    # الجولة الإنشائية 2026-10-16: معادلة ROADMAP_V2 خمسة مكونات قابلة للقياس —
    # مربوطة بالاستجابة الفعلية (تصويب المراجع — الاعتراض 1). الدالة لا
    # تشغل pytest (فصل الحاسبة عن مشغل الاختبارات): invariants_passing
    # من دليل JUnit معلوم الهوية (SHA مطابق) — لا ثابت نجاح بلا دليل.
    from backend.sovereign.score import compute_sovereignty_score_v2
    roadmap_v2 = compute_sovereignty_score_v2()

    return {
        "roadmap_v2": roadmap_v2,
        "total_score": report.total_score,
        "grade": report.grade,
        "timestamp": report.timestamp,
        "axes": [
            {
                "name": a.name,
                "score": round(a.score, 2),
                "weight": a.weight,
                "weighted_score": round(a.weighted_score, 2),
                "details": a.details,
                "issues": a.issues,
            }
            for a in report.axes
        ],
        "summary": report.summary,
        # R-680: المؤشرات الأولية — كل واحد قابل للتحقق الخارجي.
        "primitives": {
            "tests_passing_count": composite_result["primitives"]["tests_passing_count"],
            "files_total_count": composite_result["primitives"]["files_total_count"],
            "files_imported_count": composite_result["primitives"]["files_imported_count"],
            "mocks_outside_tests_count": composite_result["primitives"]["mocks_outside_tests_count"],
            "keys_stats": composite_result["primitives"]["keys_stats"],
            "ledger_events_stats": composite_result["primitives"]["ledger_events_stats"],
            "anchors_stats": composite_result["primitives"]["anchors_stats"],
            "invariants_stats": composite_result["primitives"]["invariants_stats"],
        },
        # R-680: الرقم المُركّب — في آخر سطر مع علامة "* قابل للجدل".
        "composite": {
            "score": composite_result["composite_score"],
            "score_label": "* قابل للجدل",  # R-680d: العلامة الحرفية من العقد
            "formula": composite_result["formula"],
            "components": composite_result["components"],
            "tests_passing": composite_result["tests_passing"],
            "tests_total": composite_result["tests_total"],
            "tests_passing_count_ratio": composite_result["tests_passing_count_ratio"],
            "hard_kill_factor": composite_result["hard_kill_factor"],
            "mocks_outside_tests_count": composite_result["mocks_outside_tests_count"],
            "disputed": True,  # ⚠️ قابل للجدل — راجع forensics/silent_failure_audit.md
        },
    }


@app.get("/compat/status")
async def compat_status():
    """
    تقرير حالة طبقة التوافق (نمط التين الخانق — المرحلة 4 من ROADMAP_V2).
    يُعيد lifecycle لكل وحدة compat: عدد الاستدعاءات + معيار الإزالة.
    """
    from backend.compat.__meta__ import (
        COMPAT_LIFECYCLE, evaluate_pending_sunset, get_lifecycle_summary,
        load_call_log,
    )

    from datetime import datetime, timezone
    entries = load_call_log()
    # الحكم الزمني الفعلي (قاعدة الـ30 يومًا — ROADMAP_V2 المرحلة 4):
    # يُحسب من السجل المثبَّت الحقيقي للاستدعاءات — المستدعي الإنتاجي
    # لـevaluate_pending_sunset (تصويب المراجع — الاعتراض 4).
    evaluation = evaluate_pending_sunset(
        now=datetime.now(timezone.utc).isoformat(),
        lifecycle=COMPAT_LIFECYCLE,
        entries=entries,
    )
    # العرض والعدّادات من دورة الحياة المُقيَّمة نفسها (تصويب المراجع —
    # الجولة 2): الوحدة الظاهرة في pending_sunset_transitions يجب أن
    # تظهر حالتها pending_sunset في modules وتُحتسب في العدّادات — لا
    # أن يعرض الاقتراح بينما الحالة المعروضة active.
    evaluated = evaluation["lifecycle"]
    active = sum(1 for v in evaluated.values() if v["status"] == "active")
    pending = sum(1 for v in evaluated.values() if v["status"] == "pending_sunset")
    legacy = sum(1 for v in evaluated.values() if v["status"] == "legacy_retained")
    return {
        "total_modules": len(evaluated),
        "active": active,
        "pending_sunset": pending,
        "legacy_retained": legacy,
        "modules": evaluated,
        "sunset_evaluation": {
            "evaluated_at": evaluation["now"],
            "threshold_days": evaluation["threshold_days"],
            "pending_sunset_transitions": evaluation["transitions"],
            "call_log_entries": len(entries),
        },
        "policy": "لا يُحذف أي وحدة compat أبدًا — تُنقل إلى _legacy/ فقط",
    }


@app.get("/health")
async def health_check():
    """
    فحص صحة النظام - يستخدمه مراقبو الخدمات (Kubernetes, Docker, etc.)
    """
    return _health_payload()


def _health_payload() -> Dict[str, Any]:
    """حمولة /health الحقيقية — تخدم النقطة وأداة السجل health.snapshot
    (R-729 — البند ٣.١) بنفس المنطق: مصدر واحد لا نسختين تتباعدان."""
    orchestrator = app.state.orchestrator
    
    # التحقق من صحة المكونات الرئيسية
    components_healthy = all(
        h["status"] == "healthy" 
        for name, h in orchestrator.get_component_health().items()
        if "core" in name or "controller" in name
    )
    
    return {
        "status": "healthy" if components_healthy else "degraded",
        "version": "4.0.0",
        "timestamp": time.time(),
        "uptime_seconds": time.time() - app.state.start_time,
        "components": orchestrator.get_component_health()
    }


def _load_heartbeat() -> Optional[dict]:
    """قراءة ملف نبض الحارس (R-696 — الربط الآمن) والتحقق من عقده.

    القناة الوحيدة: ملف في جذر البيانات يكتبه الحارس كل دورة — لا استيراد
    لكود الحارس ولا خيوط ولا منفذ ثانٍ. أي خلل → None: قيمة تالفة لا
    تمنح حالة صحية، ولا تنعكس نصوص الأخطاء أبدًا.
    نطاق موثق ومحدود (اعتراض المراجع): الفاصل (0، 60] ومهلة النبض
    min(max(10s، 3×الفاصل)، 120s) — قيمة ضخمة كـ1e308 لا تشتري صلاحية
    أبدية، والتحويلات الرقمية تفشل إلى None لا إلى استثناء (epoch ضخم
    كـ10**400 يرفع OverflowError عند float() فيُلتقط)."""
    import math

    from config import DATA_DIR
    path = DATA_DIR / "supervisor" / "status.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    epoch = data.get("epoch")
    interval = data.get("interval")
    alerts = data.get("active_alerts")
    try:
        # التحويلات تفشل بأمان — رقم ضخم يرفع OverflowError لا استجابة مكسورة
        if (
            not isinstance(epoch, (int, float)) or isinstance(epoch, bool)
            or not math.isfinite(epoch := float(epoch))
        ):
            return None
        if (
            not isinstance(interval, (int, float)) or isinstance(interval, bool)
            or not math.isfinite(interval := float(interval))
        ):
            return None
    except (OverflowError, ValueError, TypeError):
        return None
    # النطاق الموثق: فاصل الحارس الحقيقي (0، 60] ثانية — خارجه تالف
    if not (0.0 < interval <= 60.0):
        return None
    if epoch > time.time() + 5.0:  # طابع مستقبلي — مرفوض
        return None
    if not (
        isinstance(alerts, int) and not isinstance(alerts, bool)
        and alerts >= 0
    ):
        return None
    return {"epoch": epoch, "interval": interval, "active_alerts": alerts}


@app.get("/supervisor/status")
async def supervisor_status():
    """حالة الحارس — قراءة فقط (R-696: الربط الآمن).

    يقرأ ملف النبض الذي يكتبه الحارس كل دورة؛ النبض الصالح حديثًا (ضمن
    min(max(10s، 3×الفاصل)، 120s) — نطاق موثق) = up. الملف الغائب/التالف
    أو النبض المنتهي = down مع 503 — اكتشاف موت الحارس بعد انتهاء مهلة
    النبض لا فور توقفه، وفشل الحارس لا يُسقط التطبيق: لا استيراد ولا
    خيوط ولا كتابة. last_heartbeat مشتق من الطابع المتحقق منه (epoch)
    لا منسوخ من نص الملف — فلا يمكنه مخالفة الطابع."""
    data = _load_heartbeat()
    if data is None:
        return JSONResponse(
            status_code=503,
            content={"supervisor": "down", "reason": "invalid"},
        )
    age = time.time() - data["epoch"]
    threshold = min(max(10.0, 3.0 * data["interval"]), 120.0)
    if age > threshold:
        return JSONResponse(
            status_code=503,
            content={"supervisor": "down", "reason": "stale"},
        )
    from datetime import datetime, timezone
    return {
        "supervisor": "up",
        "last_heartbeat": datetime.fromtimestamp(
            data["epoch"], tz=timezone.utc
        ).isoformat(),
        "active_alerts": data["active_alerts"],
    }


@app.get("/disk/status")
async def disk_status():
    """حالة القرص السحابي (R-719 — بأمر المالك: Supabase قرص المشروع وذاكرته).

    قراءة فقط. المعطّل (الافتراضي — لا SUPABASE_URL/SUPABASE_SECRET_KEY) يعيد
    enabled=False بلا أي تفاصيل. المفعّل يعيد الحالة ببصمة المفتاح فقط —
    لا سر في المخرجات أبدًا (نمط بصمة /api-key — R-614)."""
    return _disk_status_payload()


def _disk_status_payload() -> Dict[str, Any]:
    """حمولة /disk/status — تخدم النقطة وأداة السجل disk.status (R-729)."""
    try:
        from backend.sovereign.cloud_disk import get_cloud_disk  # استيراد كسول — نمط المتجر
    except ImportError:
        from sovereign.cloud_disk import get_cloud_disk
    disk = get_cloud_disk()
    if disk is None:
        return {"cloud_disk": "disabled", "enabled": False}
    return {"cloud_disk": "enabled", **disk.status()}


def _disk_tool_payload() -> Dict[str, Any]:
    """R-792: أداة disk.status = حمولة /disk/status كما هي + القرص المحلي (مساحة وعُقد).
    عقد النقطة /disk/status لا يتغير (المعطّل بلا تفاصيل)."""
    return {**_disk_status_payload(), "local_volume": _local_volume_status()}


def _local_volume_status(path=None) -> Dict[str, Any]:
    """R-792: مساحة وعُقد (inodes) القرص المحلي للبيانات من os.statvfs — قراءة فعلية.
    حيًا 2026-10-27 سقط الخادم بـENOSPC والمساحة 29% فقط لأن العُقد 100%."""
    import os as _os
    try:
        from config import DATA_DIR as _dd
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج
        from backend.config import DATA_DIR as _dd
    p = str(path or _dd)
    try:
        st = _os.statvfs(p)
    except OSError as e:
        return {"path": p, "error": str(e)[:200]}
    def _pct(total, free):
        return round(100.0 * (total - free) / total, 1) if total else None
    bytes_pct = _pct(st.f_blocks, st.f_bavail)
    inodes_pct = _pct(st.f_files, st.f_favail)
    worst = max(x for x in (bytes_pct or 0, inodes_pct or 0))
    return {
        "path": p,
        "bytes_total": st.f_blocks * st.f_frsize,
        "bytes_free": st.f_bavail * st.f_frsize,
        "bytes_used_pct": bytes_pct,
        "inodes_total": st.f_files,
        "inodes_free": st.f_favail,
        "inodes_used_pct": inodes_pct,
        # R-792a: قيم محسوبة جاهزة — حيًا قرأ العقل البايتات 86.3 GB بدل 8.63
        "kind": "قرص محلي للبيانات (ليس السحابي)",
        "total_gb": round(st.f_blocks * st.f_frsize / 1e9, 2),
        "free_gb": round(st.f_bavail * st.f_frsize / 1e9, 2),
        "state": "critical" if worst >= 95 else ("warning" if worst >= 85 else "ok"),
    }


@app.get("/vault/status")
async def vault_status():
    """R-752 (ROADMAP_V5 ١.٥): حالة خزينة الأسرار — قراءة فقط: التمكين
    والبيانات الوصفية والبصمات. لا قيمة سر ولا نص مشفر في المخرجات أبدًا."""
    return _vault_status_payload()


def _vault_status_payload() -> Dict[str, Any]:
    """حمولة /vault/status — تخدم النقطة وأداة السجل vault.status (R-752)."""
    try:
        from backend.sovereign.secrets_vault import get_vault
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم في /disk/status
        from sovereign.secrets_vault import get_vault
    return get_vault().status()


# ============================================================
# R-756 (ROADMAP_V5 ٤.١): عقد الموصل المعزول — الحالة والمنح والسحب
# ============================================================
class ConnectorGrantRequest(BaseModel):
    """منحة/سحب تفويض موصل — أمر مالك (مفتاح API) بأثر في السجل السيادي."""
    connector: str = Field(..., min_length=1, max_length=64)
    actions: List[str] = Field(default_factory=list)
    ttl_s: Optional[float] = Field(None, description="مدة المنحة بالثواني (غيابها = حتى السحب)")
    api_key: Optional[str] = Field(None, description="مفتاح API للسيد — غيابه رفض 401")


def _connectors_status_payload() -> Dict[str, Any]:
    """حمولة /connectors/status — تخدم النقطة وأداة connectors.status (R-756)."""
    import connectors
    return connectors.get_hub().status()


@app.get("/connectors/status")
async def connectors_status():
    """R-756: الموصلات المضبوطة ومنحها وقواطعها — لا سر في المخرجات أبدًا."""
    return _connectors_status_payload()


def _connector_owner_op(request: "ConnectorGrantRequest", op: str) -> Dict[str, Any]:
    if not verify_api_key(request.api_key or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="مفتاح API غير صحيح")
    import connectors
    hub = connectors.get_hub()
    try:
        if op == "grant":
            return {"ok": True, "grant": hub.grant(request.connector, request.actions,
                                                   actor="owner", ttl_s=request.ttl_s)}
        hub.revoke(request.connector, actor="owner")
        return {"ok": True, "revoked": request.connector}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"موصل غير مضبوط: {request.connector}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:  # السجل لا يوقّع — لا أثر = لا تنفيذ
        raise HTTPException(status_code=503,
                            detail=f"السجل السيادي لا يوقّع — مرفوض (fail-closed): {exc}")


# ============================================================
# R-757 (ROADMAP_V5 ٤.٢ + ٤.٣): اكتساب المهارات — الاعتماد والتراجع للمالك وحده
# ============================================================
class SkillOwnerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    version: Optional[str] = Field(None, max_length=32)
    api_key: Optional[str] = Field(None, description="مفتاح API للسيد — غيابه رفض 401")


def _skill_owner_op(request: "SkillOwnerRequest", op: str) -> Dict[str, Any]:
    if not verify_api_key(request.api_key or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="مفتاح API غير صحيح")
    import skills
    lib = skills.get_library()
    try:
        if op == "approve":
            return lib.approve(request.name, request.version or "", actor="owner")
        return lib.rollback(request.name, actor="owner")
    except skills.SkillError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:  # السجل لا يوقّع — لا أثر = لا تفعيل
        raise HTTPException(status_code=503,
                            detail=f"السجل السيادي لا يوقّع — مرفوض (fail-closed): {exc}")


@app.post("/skills/approve")
async def skills_approve(request: SkillOwnerRequest):
    """اعتماد مهارة مُقيّمة بنجاح — يشترط تطابق بصمة المحتوى مع المُقيّم."""
    return _skill_owner_op(request, "approve")


@app.post("/skills/rollback")
async def skills_rollback(request: SkillOwnerRequest):
    return _skill_owner_op(request, "rollback")


@app.post("/connectors/grant")
async def connectors_grant(request: ConnectorGrantRequest):
    return _connector_owner_op(request, "grant")


@app.post("/connectors/revoke")
async def connectors_revoke(request: ConnectorGrantRequest):
    """سحب فوري: الاستدعاء التالي يُرفض (الحالة تُقرأ من القرص عند كل استدعاء)."""
    return _connector_owner_op(request, "revoke")


@app.get("/media/file/{fid}")
async def media_file(fid: str, sig: str = ""):
    """R-824: عرض وسائط الاستوديو برابط موقّع (HMAC مشتق) — للمحادثة بلا مفتاح المالك في المتصفح."""
    from urllib.parse import quote
    from workspace.service import get_workspace
    if not re.fullmatch(r"F-[0-9a-f]{12}", fid or "") or not _media_sig_ok(fid, sig):
        raise HTTPException(status_code=404, detail="غير موجود")
    ws = get_workspace()
    try:
        rec = await asyncio.to_thread(ws.get_file, fid)
        if rec.get("source") != "media_studio":
            raise HTTPException(status_code=404, detail="غير موجود")
        data = await asyncio.to_thread(ws.raw, fid)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="غير موجود")
    return Response(content=data, media_type=rec.get("content_type") or "application/octet-stream",
                    headers={"Cache-Control": "private, max-age=86400",
                             "Content-Disposition": f"inline; filename*=UTF-8''{quote(rec.get('name') or fid)}"})


@app.get("/brain/status")
async def brain_status():
    """حالة عقل Ollama ومصدر الردود (R-726 — البند ١.٦ بأمر المالك).

    شفافية صريحة لا انتحال: يعاد enabled=False مع reply_source="templates"
    عندما لا عقل — المالك يرى بالضبط ماذا يجيبه: قوالب أم نموذج.
    لا سر في المخرجات أبدًا (نمط /api-key — R-614)."""
    return _brain_status_payload()


def _brain_status_payload() -> Dict[str, Any]:
    """حمولة /brain/status — تخدم النقطة وأداة السجل brain.status (R-729).

    R-736 (البند ٢.١): يُعلن البروتوكول الضابط (ollama/openai — أو «invalid»
    لقيمة مجهولة بلا صدى للقيمة الخام) وآخر نتيجة استدعاء (last_call).
    R-736 (دقة): reply_source «المرصود» لا «المضبوط» — «model» فقط بعد
    استدلال ناجح فعلاً و«unverified» بعده (لا ادعاء قبل الدليل). والعنوان
    يُعرض معقّمًا: بلا بيانات اعتماد ولا استعلام ولا شبيه سلسلة (نمط
    لا-سر في المخرجات — /api-key و/disk/status).
    """
    import ollama_client as _brain_client
    import config as _config
    from urllib.parse import urlsplit
    enabled = bool(_config.brain_get("OLLAMA_ENABLED") and _config.brain_get("OLLAMA_MODEL"))
    outcome = _brain_client.last_outcome()
    if not enabled:
        return {"brain": "disabled", "enabled": False,
                "reply_source": "templates", "last_call": outcome}
    protocol = str(_config.brain_get("OLLAMA_PROTOCOL", "ollama") or "ollama").strip().lower() or "ollama"
    if protocol not in ("ollama", "openai"):
        protocol = "invalid"  # لا صدى للقيمة الخام (قد تحمل سرًا)
    # المرصود: مصدر آخر رد فعلي — لا ادعاء نجاح قبل أول استدلال ناجح
    if outcome.get("result") == "ok":
        reply_source = "model"
    elif outcome.get("result") == "none":
        reply_source = "unverified"
    else:
        reply_source = "templates-fallback"
    raw = urlsplit(str(_config.brain_get("OLLAMA_BASE_URL")))
    netloc = raw.hostname or ""
    try:
        if raw.port is not None:
            netloc = f"{netloc}:{raw.port}"
        scheme = f"{raw.scheme}://" if (raw.scheme and netloc) else ""
        safe_base = f"{scheme}{netloc}{raw.path}"
    except ValueError:
        # منفذ مشوه (مثل :bad) — لا 500 ولا صدى للعنوان الخام أبدًا
        safe_base = "<عنوان مضبوط غير قابل للعرض>"
    return {
        "brain": "enabled",
        "enabled": True,
        "reply_source": reply_source,
        "protocol": protocol,
        "model": _config.brain_get("OLLAMA_MODEL"),
        "base_url": safe_base,
        "timeout_seconds": _config.brain_get("OLLAMA_TIMEOUT_SECONDS", 60),
        "last_call": outcome,
        "cloud_fallback": _cloud_brain_status(),  # R-824: العقل السحابي الاحتياطي (حالة مستقلة صادقة)
    }


def _media_studio_detail() -> str:
    try:
        import media_studio
        c = media_studio.capabilities()
        return "المولدات: " + " ← ".join(c.get("providers") or ["local_design"]) + (" — فيديو MP4" if c.get("video") else "")
    except Exception as e:  # TOLERATED: التفصيل يعلن خطأه
        return type(e).__name__


def _media_ffmpeg():
    try:
        import media_studio
        return media_studio.ffmpeg_exe()
    except Exception:  # TOLERATED: غياب المحلّل = غير جاهز
        return None


def _cloud_brain_status():
    try:
        import cloud_brain
        return cloud_brain.status()
    except Exception as e:  # TOLERATED: الحالة تعلن خطأها
        return {"enabled": False, "error": type(e).__name__}


# ============================================================
# R-810 (المالك — البندان ٢ و٣ من أمر التشغيل): النماذج والمزودون
# ============================================================
# «لا يوجد إمكانية تبديل النماذج…» و«لا مجال لإضافة مفاتيح API لنماذج أخرى
# سحابيًا» — اكتشاف حي للنماذج من المزود المُعد (بلا قائمة مختلَقة)، وتبديل
# حي يُحفظ في طبقة التشغيل (config.brain_set) بلا إعادة تشغيل وبلا مساس
# بأسرار المستودع. مزود OpenAI المتوافق (Groq/OpenRouter/…) صار قابلًا
# للضبط من الواجهة بمفتاحه — يُخزن على القرص بوضع 0600 ولا يُعاد أبدًا.


@app.get("/brain/models")
def brain_models(x_sovereign_key: Optional[str] = Header(None)):
    """R-810 (البند ٢): النماذج المتاحة من العقل المُعد فعليًا — اكتشاف حي (المالك فقط)."""
    if not x_sovereign_key or not verify_api_key(x_sovereign_key):
        raise HTTPException(status_code=401, detail="مفتاح المالك مطلوب (X-Sovereign-Key)")
    import ollama_client as _brain_client

    return _brain_client.list_models()


@app.get("/brain/settings")
def brain_settings_get(x_sovereign_key: Optional[str] = Header(None)):
    """R-810: الإعدادات الفعالة للعقل (المالك فقط) — بلا أي سر في المخرجات.

    api_key لا يُعاد أبدًا — منطقية «مضبوط/غير مضبوط» فقط (نمط لا-سر، R-614).
    المصدر يُعلن لكل حقل: runtime (طبقة التشغيل الحية) أو env (إعداد النشر).
    """
    if not x_sovereign_key or not verify_api_key(x_sovereign_key):
        raise HTTPException(status_code=401, detail="مفتاح المالك مطلوب (X-Sovereign-Key)")
    import config as _config

    runtime = _config.brain_runtime_read()

    def _src(name):
        return "runtime" if name in runtime else "env"

    return {
        "enabled": bool(_config.brain_get("OLLAMA_ENABLED")),
        "model": _config.brain_get("OLLAMA_MODEL"),
        "model_source": _src("OLLAMA_MODEL"),
        "protocol": _config.brain_get("OLLAMA_PROTOCOL", "ollama"),
        "protocol_source": _src("OLLAMA_PROTOCOL"),
        "base_url": _config.brain_get("OLLAMA_BASE_URL"),
        "base_url_source": _src("OLLAMA_BASE_URL"),
        "api_key_set": bool(_config.brain_get("OLLAMA_API_KEY")),
        "api_key_source": _src("OLLAMA_API_KEY"),
        "num_ctx": _config.brain_get("OLLAMA_NUM_CTX", 0),
        "timeout_seconds": _config.brain_get("OLLAMA_TIMEOUT_SECONDS", 60),
    }


@app.put("/brain/settings")
async def brain_settings_put(request: Request, x_sovereign_key: Optional[str] = Header(None)):
    """R-810 (البندان ٢ و٣): تعديل حي لإعدادات العقل (المالك فقط).

    القيم الفارغة تعيد الحقل إلى إعداد النشر (يُحذف من طبقة التشغيل).
    التحقق الصارم قبل الكتابة: البروتوكول أحد اثنين، والعنوان http(s) صالح،
    والنموذج نص غير فارغ — لا تمرير قيمة مشوهة تعطّل العقل الحي.
    """
    if not x_sovereign_key or not verify_api_key(x_sovereign_key):
        raise HTTPException(status_code=401, detail="مفتاح المالك مطلوب (X-Sovereign-Key)")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="حمولة JSON مطلوبة")
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="الحمولة كائن JSON")
    import config as _config

    allowed = {"model", "protocol", "base_url", "api_key", "num_ctx"}
    unknown = set(body) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail=f"حقول غير معروفة: {sorted(unknown)}")
    values = {}
    if "model" in body:
        m = body["model"]
        if m is None or m == "":
            values["OLLAMA_MODEL"] = None
        elif isinstance(m, str) and m.strip():
            values["OLLAMA_MODEL"] = m.strip()
        else:
            raise HTTPException(status_code=422, detail="model نص غير فارغ أو فارغ للإلغاء")
    if "protocol" in body:
        p = body["protocol"]
        if p is None or (isinstance(p, str) and p.strip() == ""):
            values["OLLAMA_PROTOCOL"] = None  # إلغاء حي — عودة لإعداد النشر
        else:
            p = str(p).strip().lower()
            if p not in ("ollama", "openai"):
                raise HTTPException(status_code=422, detail="protocol أحد: ollama أو openai")
            values["OLLAMA_PROTOCOL"] = p
    if "base_url" in body:
        b = body["base_url"]
        if b is None or str(b).strip() == "":
            values["OLLAMA_BASE_URL"] = None
        else:
            from urllib.parse import urlsplit

            raw = urlsplit(str(b).strip())
            if raw.scheme not in ("http", "https") or not raw.netloc:
                raise HTTPException(status_code=422, detail="base_url عنوان http(s) صالح مطلوب")
            values["OLLAMA_BASE_URL"] = str(b).strip().rstrip("/")
    if "api_key" in body:
        k = body["api_key"]
        if k is None or (isinstance(k, str) and k == ""):
            values["OLLAMA_API_KEY"] = None  # إلغاء صريح — حذف من الخزينة
        elif isinstance(k, str):
            values["OLLAMA_API_KEY"] = k
        else:
            raise HTTPException(status_code=422, detail="api_key نص أو فارغ للإلغاء")
    if "num_ctx" in body:
        n = body["num_ctx"]
        if n is None or n == "":
            values["OLLAMA_NUM_CTX"] = None
        else:
            try:
                values["OLLAMA_NUM_CTX"] = int(n)
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail="num_ctx عدد صحيح")
    # R-813 (مراجعة المستشار): المفتاح السري مساره الخزينة المشفرة (AES-256-GCM)
    # — لا يمر من ملف التشغيل أبدًا؛ وفشل الحفظ يُرفض صادقًا (لا نجاح كاذبًا).
    # الكتابة على القرص/الخزينة تخرج من حلقة التنفيذ (threadpool) — لا حجب
    if "OLLAMA_API_KEY" in values:
        try:
            await asyncio.to_thread(_config.brain_api_key_set,
                                    values.pop("OLLAMA_API_KEY"), actor="owner")
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"تعذر تخزين المفتاح في الخزينة: {type(exc).__name__}")
    try:
        layer = await asyncio.to_thread(_config.brain_set, values)
    except OSError:
        raise HTTPException(status_code=503, detail="تعذر حفظ إعدادات التشغيل (القرص)")
    # النتيجة للعرض فقط — أسماء الحقول المكتوبة، بلا أي قيمة سرية
    return {"ok": True, "runtime_keys": sorted(layer), "effective": {
        "model": await asyncio.to_thread(_config.brain_get, "OLLAMA_MODEL"),
        "protocol": await asyncio.to_thread(_config.brain_get, "OLLAMA_PROTOCOL", "ollama"),
        "api_key_set": bool(await asyncio.to_thread(_config.brain_get, "OLLAMA_API_KEY")),
    }}


# ============================================================
# R-737 (البند ٢.٣ — بأمر المالك «ابدأ»): أذنان — تحويل الكلام لنص
# ============================================================
# قائمة أنواع صوتية صارمة — لا قبول ملفات اعتباطية
STT_ALLOWED_CONTENT_TYPES = {
    "audio/wav", "audio/x-wav", "audio/webm", "audio/mpeg", "audio/mp4",
    "audio/x-m4a", "audio/ogg", "application/ogg",
}


@app.post("/stt")
async def stt(request: Request, file: UploadFile = File(...)):
    """R-737 (البند ٢.٣): مقطع صوتي → نص (معيار الإغلاق في الخارطة).

    fail-closed بصدق في كل حالة: معطل → 503 بالسبب، فشل الخدمة → 502،
    حجم زائد → 413، نوع غير صوتي → 415، تجاوز المعدل → 429. لا نص مختلق
    ولا نجاح كاذب (المادة ١).
    """
    # حد المعدل (حد /chat نفسه لكل IP مباشر — لا ثقة بترويسات التمرير)
    client_host = request.client.host if request.client else "unknown"
    retry_after = stt_rate_limiter.check(client_host)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={"error": "rate_limited",
                     "reason": "تم تجاوز حد طلبات السمع؛ أعد المحاولة لاحقًا"},
        )
    import config
    if not config.STT_ENABLED:
        return JSONResponse(
            status_code=503,
            content={"error": "stt_disabled",
                     "reason": "السمع معطل افتراضيًا — التفعيل بيد المالك "
                              "(STT_ENABLED عبر أسرار المنصة)"},
        )
    if file.content_type not in STT_ALLOWED_CONTENT_TYPES:
        return JSONResponse(
            status_code=415,
            content={"error": "unsupported_media_type",
                     "reason": f"النوع المسموح صوتي فقط — وصل: {file.content_type}"},
        )
    # قراءة بحد + 1 بايت: لا قراءة اعتباطية في الذاكرة (حد 25MiB افتراضيًا)
    data = await file.read(config.STT_MAX_AUDIO_BYTES + 1)
    if len(data) > config.STT_MAX_AUDIO_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "audio_too_large",
                     "reason": f"الحد {config.STT_MAX_AUDIO_BYTES} بايت"},
        )
    import stt_client
    text = stt_client.transcribe(data, file.filename or "audio",
                                 file.content_type)
    if text is None:
        return JSONResponse(
            status_code=502,
            content={"error": "transcription_failed",
                     "reason": "خدمة السمع لم تُرجع نصًا (معطلة لديها أو فاشلة) — "
                              "لا نص مختلق"},
        )
    return {"text": text}


@app.get("/stt/status")
async def stt_status():
    """R-737: حالة السمع — لا سر أبدًا (العنوان معقّم بنمط /brain/status)."""
    import config
    from urllib.parse import urlsplit
    enabled = bool(config.STT_ENABLED)
    raw = urlsplit(str(config.STT_BASE_URL))
    netloc = raw.hostname or ""
    try:
        if raw.port is not None:
            netloc = f"{netloc}:{raw.port}"
        scheme = f"{raw.scheme}://" if (raw.scheme and netloc) else ""
        safe_base = f"{scheme}{netloc}{raw.path}"
    except ValueError:
        safe_base = "<عنوان مضبوط غير قابل للعرض>"
    return {
        "enabled": enabled,
        "model": config.STT_MODEL,
        "base_url": safe_base,
        "timeout_seconds": config.STT_TIMEOUT_SECONDS,
        "max_audio_bytes": config.STT_MAX_AUDIO_BYTES,
    }


# ============================================================
# R-739 (البند ٢.٢ — بأمر المالك «ابدأ»): عينان — تحليل الصور
# ============================================================
# قائمة أنواع صور صارمة — لا قبول ملفات اعتباطية
VISION_ALLOWED_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp",
}


@app.post("/vision")
async def vision(request: Request, file: UploadFile = File(...)):
    """R-739 (البند ٢.٢): صورة → وصف نصي موثق (معيار الإغلاق في الخارطة).

    fail-closed بصدق في كل حالة: معطل → 503 بالسبب، فشل الخدمة → 502،
    حجم زائد → 413، نوع غير صورة → 415، تجاوز المعدل → 429. لا وصف
    مختلق ولا نجاح كاذب (المادة ١).
    """
    # حد المعدل (حد /chat نفسه لكل IP مباشر — لا ثقة بترويسات التمرير)
    client_host = request.client.host if request.client else "unknown"
    retry_after = vision_rate_limiter.check(client_host)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={"error": "rate_limited",
                     "reason": "تم تجاوز حد طلبات الرؤية؛ أعد المحاولة لاحقًا"},
        )
    import config
    if not (config.VISION_ENABLED and config.VISION_MODEL):
        return JSONResponse(
            status_code=503,
            content={"error": "vision_disabled",
                     "reason": "الرؤية معطلة افتراضيًا — التفعيل بيد المالك "
                              "(VISION_ENABLED + VISION_MODEL عبر أسرار المنصة)"},
        )
    if file.content_type not in VISION_ALLOWED_CONTENT_TYPES:
        return JSONResponse(
            status_code=415,
            content={"error": "unsupported_media_type",
                     "reason": f"النوع المسموح صور فقط — وصل: {file.content_type}"},
        )
    # قراءة بحد + 1 بايت: لا قراءة اعتباطية في الذاكرة (حد 10MiB افتراضيًا)
    data = await file.read(config.VISION_MAX_IMAGE_BYTES + 1)
    if len(data) > config.VISION_MAX_IMAGE_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "image_too_large",
                     "reason": f"الحد {config.VISION_MAX_IMAGE_BYTES} بايت"},
        )
    import vision_client
    description = vision_client.describe(data, file.content_type)
    if description is None:
        return JSONResponse(
            status_code=502,
            content={"error": "vision_failed",
                     "reason": "خدمة الرؤية لم تُرجع وصفًا (نموذج غير متاح أو "
                              "فاشل) — لا وصف مختلق"},
        )
    return {"description": description}


@app.get("/vision/status")
async def vision_status():
    """R-739: حالة الرؤية — لا سر أبدًا (العنوان معقّم بنمط /brain/status)."""
    import config
    from urllib.parse import urlsplit
    enabled = bool(config.VISION_ENABLED and config.VISION_MODEL)
    raw = urlsplit(str(config.OLLAMA_BASE_URL))
    netloc = raw.hostname or ""
    try:
        if raw.port is not None:
            netloc = f"{netloc}:{raw.port}"
        scheme = f"{raw.scheme}://" if (raw.scheme and netloc) else ""
        safe_base = f"{scheme}{netloc}{raw.path}"
    except ValueError:
        safe_base = "<عنوان مضبوط غير قابل للعرض>"
    return {
        "enabled": enabled,
        "model": config.VISION_MODEL,
        "base_url": safe_base,
        "timeout_seconds": config.OLLAMA_TIMEOUT_SECONDS,
        "max_image_bytes": config.VISION_MAX_IMAGE_BYTES,
    }


# ============================================================
# R-740 (البند ٢.٤ — بأمر المالك «ابدأ»): صوت — نطق الردود (TTS)
# ============================================================


class TtsRequest(BaseModel):
    """R-740 (البند ٢.٤): طلب نطق نص — نص → مقطع صوتي."""
    text: str = Field(..., min_length=1, max_length=10000,
                      description="النص المطلوب نطقه")


@app.post("/tts")
async def tts(request: Request, body: TtsRequest):
    """R-740 (البند ٢.٤): نص → مقطع صوتي (معيار الإغلاق — النصف الأول).

    fail-closed بصدق في كل حالة: معطل → 503 بالسبب، فشل الخدمة → 502،
    نص فارغ → 400، تجاوز حد الطول → 413، تجاوز المعدل → 429. لا صوت
    مختلق ولا نجاح كاذب (المادة ١).
    """
    client_host = request.client.host if request.client else "unknown"
    retry_after = tts_rate_limiter.check(client_host)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={"error": "rate_limited",
                     "reason": "تم تجاوز حد طلبات النطق؛ أعد المحاولة لاحقًا"},
        )
    import config
    if not (config.TTS_ENABLED and config.TTS_MODEL):
        return JSONResponse(
            status_code=503,
            content={"error": "tts_disabled",
                     "reason": "النطق معطل افتراضيًا — التفعيل بيد المالك "
                              "(TTS_ENABLED + TTS_MODEL عبر أسرار المنصة)"},
        )
    text = (body.text or "").strip()
    if not text:
        return JSONResponse(
            status_code=400,
            content={"error": "empty_text",
                     "reason": "نص فارغ — لا نطق"},
        )
    if len(text) > config.TTS_MAX_TEXT_CHARS:
        return JSONResponse(
            status_code=413,
            content={"error": "text_too_long",
                     "reason": f"الحد {config.TTS_MAX_TEXT_CHARS} حرفًا"},
        )
    import tts_client
    spoken = tts_client.speak(text)
    if spoken is None:
        return JSONResponse(
            status_code=502,
            content={"error": "tts_failed",
                     "reason": "خدمة النطق لم تُرجع صوتًا (نموذج غير متاح أو "
                              "فاشل) — لا صوت مختلق"},
        )
    audio, ctype = spoken
    return Response(content=audio, media_type=ctype)


# ============================================================
# R-747 (البند ٣.٥ — أدوات الوسائط): توليد صور ذاتي الاستضافة
# ============================================================


class MediaImageRequest(BaseModel):
    """R-747 (البند ٣.٥): طلب توليد صورة — وصف → صورة."""
    prompt: str = Field(..., max_length=20000, description="وصف الصورة")
    size: Optional[str] = Field(None, description="256x256 | 512x512 | 768x768 | 1024x1024")


def _media_validate(prompt: str, size: Optional[str]):
    """حدود الطلب قبل أي اتصال — يعيد (prompt, size) أو (None, JSONResponse)."""
    import config
    import media_client
    if not config.MEDIA_ENABLED:
        return None, JSONResponse(status_code=503, content={
            "error": "media_disabled",
            "reason": "توليد الصور معطل افتراضيًا — التفعيل بيد المالك "
                      "(MEDIA_ENABLED + MEDIA_BASE_URL لخادم LocalAI ذاتي الاستضافة)"})
    if not media_client.is_self_hosted(config.MEDIA_BASE_URL):
        return None, JSONResponse(status_code=503, content={
            "error": "media_host_not_self_hosted",
            "reason": "MEDIA_BASE_URL يشير إلى مضيف عام — مرفوض بأمر المالك (لا بيانات "
                      "لطرف ثالث). المسموح: loopback/عنوان خاص/.internal/.flycast/.local/اسم خدمة"})
    text = (prompt or "").strip()
    if not text:
        return None, JSONResponse(status_code=400, content={
            "error": "empty_prompt", "reason": "وصف فارغ — لا توليد"})
    if len(text) > config.MEDIA_MAX_PROMPT_CHARS:
        return None, JSONResponse(status_code=413, content={
            "error": "prompt_too_long", "reason": f"الحد {config.MEDIA_MAX_PROMPT_CHARS} حرفًا"})
    size = size or config.MEDIA_IMAGE_SIZE
    if size not in config.MEDIA_ALLOWED_SIZES:
        return None, JSONResponse(status_code=400, content={
            "error": "size_not_allowed", "reason": f"المسموح: {list(config.MEDIA_ALLOWED_SIZES)}"})
    return (text, size), None


def _media_result(img: bytes, mime: str, size: str) -> Dict[str, Any]:
    import base64
    import hashlib
    return {"image_b64": base64.b64encode(img).decode("ascii"), "mime": mime,
            "bytes": len(img), "sha256": hashlib.sha256(img).hexdigest(), "size": size}


@app.post("/media/image")
async def media_image(request: Request, body: MediaImageRequest):
    """R-747 (البند ٣.٥): وصف → صورة عبر خدمة ذاتية الاستضافة (LocalAI).

    fail-closed بصدق: معطل 503، مضيف عام 503 (بلا اتصال)، وصف فارغ 400،
    طويل 413، مقاس غير مسموح 400، فشل الخدمة 502، المعدل 429. لا صورة مختلقة."""
    client_host = request.client.host if request.client else "unknown"
    retry_after = media_rate_limiter.check(client_host)
    if retry_after is not None:
        return JSONResponse(status_code=429, headers={"Retry-After": str(retry_after)},
                            content={"error": "rate_limited",
                                     "reason": "تم تجاوز حد طلبات توليد الصور"})
    ok, err = _media_validate(body.prompt, body.size)
    if err is not None:
        return err
    prompt, size = ok
    import media_client
    out = media_client.generate_image(prompt, size=size)
    if out is None:
        return JSONResponse(status_code=502, content={
            "error": "media_failed",
            "reason": f"خدمة الوسائط لم تُرجع صورة صالحة ({media_client.last_outcome()['result']}) "
                      "— لا صورة مختلقة"})
    return _media_result(out[0], out[1], size)


def _media_tool(prompt: str, size: str = None) -> Dict[str, Any]:
    """R-747: أداة media.image — نفس الحدود والحارس، وكل استدعاء بأثر موقّع."""
    ok, err = _media_validate(prompt, size)
    if err is not None:
        raise RuntimeError(json.loads(err.body)["error"])
    import media_client
    out = media_client.generate_image(ok[0], size=ok[1])
    if out is None:
        raise RuntimeError(f"media_failed: {media_client.last_outcome()['result']}")
    return _media_result(out[0], out[1], ok[1])


@app.get("/media/status")
async def media_status():
    """R-747: حالة الوسائط — لا سر أبدًا (العنوان معقّم)."""
    import config
    import media_client
    from urllib.parse import urlsplit
    raw = urlsplit(str(config.MEDIA_BASE_URL))
    netloc = raw.hostname or ""
    try:
        if raw.port is not None:
            netloc = f"{netloc}:{raw.port}"
        scheme = f"{raw.scheme}://" if (raw.scheme and netloc) else ""
        safe_base = f"{scheme}{netloc}{raw.path}"
    except ValueError:
        safe_base = "<عنوان مضبوط غير قابل للعرض>"
    return {"enabled": bool(config.MEDIA_ENABLED),
            "self_hosted": media_client.is_self_hosted(config.MEDIA_BASE_URL),
            "base_url": safe_base, "model": config.MEDIA_MODEL,
            "default_size": config.MEDIA_IMAGE_SIZE,
            "allowed_sizes": list(config.MEDIA_ALLOWED_SIZES),
            "max_image_bytes": config.MEDIA_MAX_IMAGE_BYTES,
            "last_outcome": media_client.last_outcome()}


@app.get("/tts/status")
async def tts_status():
    """R-740: حالة النطق — لا سر أبدًا (العنوان معقّم بنمط /brain/status)."""
    import config
    from urllib.parse import urlsplit
    enabled = bool(config.TTS_ENABLED and config.TTS_MODEL)
    raw = urlsplit(str(config.TTS_BASE_URL))
    netloc = raw.hostname or ""
    try:
        if raw.port is not None:
            netloc = f"{netloc}:{raw.port}"
        scheme = f"{raw.scheme}://" if (raw.scheme and netloc) else ""
        safe_base = f"{scheme}{netloc}{raw.path}"
    except ValueError:
        safe_base = "<عنوان مضبوط غير قابل للعرض>"
    return {
        "enabled": enabled,
        "model": config.TTS_MODEL,
        "voice": config.TTS_VOICE,
        "base_url": safe_base,
        "timeout_seconds": config.TTS_TIMEOUT_SECONDS,
        "max_text_chars": config.TTS_MAX_TEXT_CHARS,
    }


class ToolInvokeRequest(BaseModel):
    """R-729 (البند ٣.١): طلب استدعاء أداة من سجل الأدوات الحقيقي.

    الاستدعاء أمر مالك — يتطلب مفتاح API (نمط /sovereign/command) ويترك
    أثرًا إلزاميًا في السجل السيادي (TOOL_INVOKED) أو يُرفض (fail-closed)."""
    tool: str = Field(..., min_length=1, max_length=100, description="اسم الأداة المسجلة")
    api_key: Optional[str] = Field(None, description="مفتاح API للسيد — غيابه رفض 401")
    inputs: Dict[str, str] = Field(default_factory=dict, description=(
        "R-738: مدخلات الأداة — المفاتيح المعلنة في السجل حصرًا "
        "(مفتاح غير معلن → استدعاء فاشل مُسجل ولا تنفيذ)"))

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"tool": "health.snapshot", "api_key": "<مفتاح السيد>"}
        }
    )


@app.get("/tools/list")
async def tools_list():
    """R-729 (البند ٣.١ — بأمر المالك): سجل الأدوات الحقيقي.

    يُعيد الأدوات المسجلة فعلًا في backend (اسم/وصف/مدخلات/مخرجات/صلاحية)
    — لا معالجات ولا أسرار في المخرجات (المادة ٩). هذا هو الاستبدال
    الحقيقي لـruntime-capability-registry.js الزخرفي: بيانات من النظام لا
    قدرات وهمية مزروعة."""
    from tool_registry import get_registry
    tools = get_registry().list_tools()
    return {"tools": tools, "count": len(tools)}


def _signing_ok() -> bool:
    """R-750: هل يوجد مفتاح توقيع نشط الآن؟ (نفس حارس R-635 في append_event).
    تعذر الفحص يُعلن «لا» — الجرد لا يدّعي قدرة لا يستطيع إثباتها."""
    try:
        return get_core()._get_current_signing_key_id() is not None
    except Exception:  # TOLERATED: فحص تعذر → «محجوب» بصدق (fail-closed للإعلان)
        logger.warning("R-750: تعذر فحص مفتاح التوقيع — يُعلن محجوبًا")
        return False


def _autonomy_enabled() -> bool:
    """R-791: حلقة الاستقلال تعمل فعلًا (مبنية من البيئة ومفعّلة) — لا ادعاء بالعلم وحده."""
    try:
        import goals as _g
        return bool(_g.get_loop().enabled)
    except Exception:  # TOLERATED: تعذر القراءة ⇒ غير مفعّلة
        return False


def _search_configured() -> bool:
    """R-789c: مزود بحث فعلي — المصدر الواحد chat_tools.search_configured."""
    try:
        import chat_tools
        return bool(chat_tools.search_configured())
    except Exception:  # TOLERATED: بلا تأكيد ⇒ غير مفعّل (لا ادعاء)
        return False


def _capabilities_payload():
    """R-787: الجرد الحي نفسه كدالة متزامنة — يستعمله /capabilities وجسر المحادثة."""
    import capability_inventory
    import config
    from tool_registry import get_registry
    try:
        from backend.sovereign.cloud_disk import cloud_disk_enabled
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم في /disk/status
        from sovereign.cloud_disk import cloud_disk_enabled
    names = [t["name"] for t in get_registry().list_tools()]
    flags = {
        "brain": bool(config.OLLAMA_ENABLED and config.OLLAMA_MODEL),
        "web_tools": bool(getattr(config, "WEB_TOOLS_ENABLED", False)),
        "media": bool(getattr(config, "MEDIA_ENABLED", False)),
        "vision": bool(config.VISION_ENABLED and config.VISION_MODEL),
        "stt": bool(config.STT_ENABLED),
        "tts": bool(config.TTS_ENABLED and config.TTS_MODEL),
        "mcp": bool(getattr(config, "MCP_ENABLED", False)),
        "vault": _vault_status_payload()["enabled"],
    }
    flags["web_search"] = flags["web_tools"] and _search_configured()  # R-789c
    flags["autonomy"] = _autonomy_enabled()  # R-791
    return capability_inventory.build_inventory(
        names, flags, signing_ok=_signing_ok(),
        cloud_disk_enabled=cloud_disk_enabled())


@app.get("/capabilities")
async def capabilities():
    """R-750 (ROADMAP_V5 §١.٢): جرد القدرات الصادق من الحالة الحية — سجل
    الأدوات الفعلي + الأعلام + مفتاح التوقيع + القرص السحابي. قدرة معطلة أو
    محجوبة أو غير مبنية لا تُعلن متاحة؛ ولا «مثبت حيًا» من داخل العملية."""
    import capability_inventory
    import config
    from tool_registry import get_registry
    try:
        from backend.sovereign.cloud_disk import cloud_disk_enabled
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم في /disk/status
        from sovereign.cloud_disk import cloud_disk_enabled
    names = [t["name"] for t in get_registry().list_tools()]
    flags = {
        "brain": bool(config.OLLAMA_ENABLED and config.OLLAMA_MODEL),
        "web_tools": bool(getattr(config, "WEB_TOOLS_ENABLED", False)),
        "media": bool(getattr(config, "MEDIA_ENABLED", False)),
        "vision": bool(config.VISION_ENABLED and config.VISION_MODEL),
        "stt": bool(config.STT_ENABLED),
        "tts": bool(config.TTS_ENABLED and config.TTS_MODEL),
        "mcp": bool(getattr(config, "MCP_ENABLED", False)),
        "vault": _vault_status_payload()["enabled"],
    }
    flags["web_search"] = flags["web_tools"] and _search_configured()  # R-789c
    flags["autonomy"] = _autonomy_enabled()  # R-791
    return capability_inventory.build_inventory(
        names, flags, signing_ok=_signing_ok(),
        cloud_disk_enabled=cloud_disk_enabled())


@app.post("/tools/invoke")
async def tools_invoke(request: ToolInvokeRequest):
    """R-729 (البند ٣.١): استدعاء أداة مسجلة — أمر مالك (مفتاح API) وأثر
    إلزامي في السجل السيادي: كل استدعاء يترك حدث TOOL_INVOKED ببصمة
    النتيجة، أو يُرفض كاملًا (fail-closed بنمط R-635 — لا أثر = لا تنفيذ)."""
    if not verify_api_key(request.api_key or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="مفتاح API غير صحيح"
        )
    from tool_registry import get_registry, UnknownToolError
    try:
        # R-764: تنفيذ الأداة في خيط عام — أدوات العقل/الوكيل/المهام تستدعي
        # استدلالًا HTTP طويلًا؛ تنفيذها داخل الحلقة كان يحجب /health (صنف R-762)
        registry = get_registry()
        return await asyncio.to_thread(registry.invoke, request.tool,
                                       caller="owner", inputs=request.inputs)
    except UnknownToolError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"أداة غير مسجلة في السجل: {request.tool}"
        )
    except RuntimeError as exc:
        # fail-closed (R-635): السجل السيادي لا يوقّع — لا أثر = لا تنفيذ
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"السجل السيادي لا يوقّع — الاستدعاء مرفوض (fail-closed): {exc}"
        )


def _brain_unreachable_now() -> bool:
    """R-822: مزلاج وصول العقل (R-821) مفتوح — آخر اتصال فشل وفترة الهدوء جارية."""
    try:
        import ollama_client
        return bool(ollama_client._brain_latch_open())
    except Exception:  # TOLERATED: غياب المزلاج = لا سقوط إضافي (السلوك القديم)
        return False


def _world_answer_for_chat(text: str, raw: bool = False):
    """R-823: البحث العالمي عبر السجل (أثر TOOL_INVOKED موقّع) — (الرد، الحالة) أو None إن لم يُتح."""
    try:
        import world_search
        if not world_search.enabled():
            return None
        from tool_registry import get_registry
        out = get_registry().invoke("world.answer", caller="chat", inputs={"question": text})
        if not out.get("ok"):
            logger.warning("R-823: فشل world.answer (%s)", str(out.get("error"))[:160])
            return None
        res = out.get("result") or {}
        if raw:  # R-824: النتيجة الخام للصياغة المقيدة بالمصادر
            return res
        status = "brain_unreachable_world_search" if res.get("ok") else "brain_unreachable_unanswered"
        return world_search.format_reply(res), status
    except Exception as e:  # TOLERATED: يبقى الإعلان الصادق R-822c — يُسجل
        logger.warning("R-823: تعذر البحث العالمي (%s)", type(e).__name__)
        return None


def _is_unanswered(reply) -> bool:
    """R-822c: الرد هو الإعلان الصادق بتعذر الجواب (لا جواب حقيقي)."""
    try:
        import sovereign_response
        # R-824d: ملحق المشاعر «(مشاعرك: …)» يُضاف بعد الإعلان ⇒ المساواة التامة كانت تُسقط البحث العالمي
        # (ثُبت حيًا: سؤال النظام الغذائي بمشاعر «إيجابية» أعاد الإعلان في ثانية بلا بحث)
        return str(reply or "").startswith(sovereign_response.UNREACHABLE_UNANSWERED.rstrip())
    except Exception:  # TOLERATED: تعذر المقارنة ⇒ الحالة كما هي
        return False


# ============================================================
# R-824: السياق + الوسائط + العقل السحابي الاحتياطي — منظومة واحدة من المحادثة
# ============================================================
_CREATIVE = re.compile(
    r"^(?:من فضلك\s+|لو سمحت\s+)?(?:اكتب|أكتب|صغ|اصغ|ألف|الف|أنشئ نص|اقترح|برمج|ارسل|حرر|حرّر|راجع|صحح|"
    r"اعد صياغة|أعد صياغة|ترجم|لخص|write|draft|compose|code|program|suggest|rewrite|fix|edit|translate)"
    r"|(?:قصيدة|قصة|رسالة|ايميل|إيميل|مقال|تغريدة|منشور|سيناريو|كود|دالة|سكربت|خطة|جدول|برنامج تدريبي|"
    r"poem|story|email|essay|tweet|script|function|plan)", re.I)


def _media_link(fid: str) -> str:
    """R-824: رابط موقّع لعرض وسائط مولدة بلا مفتاح المالك في المتصفح (HMAC مشتق — لا تخمين)."""
    # مفتاح api_auth المشتق مع وسم غرض منفصل في الرسالة (الأغراض المعتمدة للاشتقاق محصورة)
    sig = hmac.new(_derive_api_auth("api_auth").encode("utf-8"), ("media_link:" + str(fid)).encode("utf-8"),
                   hashlib.sha256).hexdigest()[:32]
    return f"/media/file/{fid}?sig={sig}"


def _media_sig_ok(fid: str, sig: str) -> bool:
    good = _media_link(fid).rsplit("sig=", 1)[1]
    return hmac.compare_digest(str(sig or "").encode("utf-8"), good.encode("utf-8"))


def _media_for_chat(req: Dict[str, Any]):
    """R-824: ينفذ طلب صورة/فيديو عبر السجل (أثر موقّع) ⇒ (الرد، [وسائط]، الحالة)."""
    import media_studio
    try:
        from tool_registry import get_registry
        out = get_registry().invoke("media.create", caller="chat",
                                    inputs={"request": req.get("request") or req.get("subject"),
                                            "kind": req.get("kind"), "base_prompt": req.get("edit_of") or ""})
        res = out.get("result") if out.get("ok") else {"ok": False, "kind": req.get("kind"),
                                                        "error": str(out.get("error"))[:200]}
    except Exception as e:  # TOLERATED: الفشل يُعلن بسببه في الرد
        res = {"ok": False, "kind": req.get("kind"), "error": type(e).__name__}
    media = []
    if res.get("ok") and res.get("file"):
        f = res["file"]
        media.append({"type": res["kind"], "url": _media_link(f["id"]), "file_id": f["id"],
                      "name": f.get("name"), "mime": res.get("mime"), "provider": res.get("provider"),
                      "ai": res.get("ai"), "prompt": res.get("prompt")})
    return media_studio.format_reply(res), media, ("media_created" if media else "media_failed")


def _tool_media_create(request: str, kind: str = None, base_prompt: str = ""):
    import media_studio
    hist = [{"role": "assistant", "content": f"الوصف المستخدم: {base_prompt}"}] if base_prompt else None
    req = media_studio.detect(request, hist) or {"kind": (kind or "image"), "subject": request,
                                                 "style": "photo", "edit_of": None, "request": request}
    if base_prompt:
        req["edit_of"] = base_prompt
    if kind in ("image", "video"):
        req["kind"] = kind

    from workspace.service import get_workspace

    def _save(name, data, mime):
        rec = get_workspace().add_file(name, data, mime, source="media_studio")
        return {"id": rec["id"], "name": rec.get("name")}
    res = media_studio.create(req, save=_save)
    res.pop("data", None)
    return res


def _prev_op_reply(resolved: Dict[str, Any]) -> Optional[str]:
    """R-824: «ترجمه/لخصه» على الرد السابق — حتمي بلا نموذج (ترجمة آلية/تلخيص استخلاصي)."""
    import context_resolver
    prev = str(resolved.get("previous_answer") or "")
    if not prev:
        return None
    if resolved.get("op") == "summarize":
        return "ملخص الرد السابق (تلخيص استخلاصي):\n" + context_resolver.summarize_extractive(prev)
    import world_search
    target = resolved.get("target_lang") or "en"
    body = re.split(r"\n\s*المصادر", prev, maxsplit=1)[0]
    parts, used = [], set()
    for para in [p for p in body.split("\n") if p.strip()][:40]:
        tr, who = world_search.translate(para, target)
        parts.append(tr if who else para)
        if who:
            used.add(who)
    if not used:
        return "تعذرت ترجمة الرد السابق الآن (مزودات الترجمة غير متاحة) — أعد المحاولة بعد قليل."
    return "\n".join(parts) + f"\n\n(ترجمة آلية إلى {target} عبر {', '.join(sorted(used))})"


def _sources_block(res: Dict[str, Any], answer: str = "") -> str:
    """المصادر المرقمة — مع نص جواب: المستشهد بها فقط (مصدر غير مستشهد به في القائمة يوهم بدعم غير موجود)."""
    cited = {int(n) for n in re.findall(r"\[(\d{1,3})\]", answer or "")}
    lines = ["المصادر:"]
    for s_ in res.get("sources") or []:
        if cited and s_.get("n") not in cited:
            continue
        lines.append(f"[{s_['n']}] {s_.get('title', '')} — {s_.get('credibility_label', '')} — {s_.get('url', '')}")
    return "\n".join(lines)


def _chat_answer_without_brain(text: str, history, resolved: Dict[str, Any]):
    """R-823/824: الطلب المفتوح والعقل الأساسي متعذر ⇒ (الرد، الحالة، الأدوات) أو None.
    ١) طلب إنشائي (اكتب/لخص/خطة/كود) ⇒ العقل السحابي مع سياق المحادثة.
    ٢) سؤال معرفي ⇒ البحث العالمي ⇒ صياغة سحابية مقيّدة بالمصادر (حارس الاستشهاد) أو الرد الحتمي.
    ٣) فشل البحث ⇒ العقل السحابي العام (معلن) ⇒ وإلا None (يبقى الإعلان الصادق)."""
    import cloud_brain
    import world_search
    tools = []
    lang = world_search.detect_lang(text) if text else "ar"
    note = (f"فهمت سؤالك في سياق المحادثة: «{resolved['standalone']}»\n\n"
            if resolved.get("followup") and resolved.get("kind") != "prev_op" else "")
    if _CREATIVE.search(str(resolved.get("original") or text)) and cloud_brain.enabled():
        g = cloud_brain.general(text, history=history, lang=lang)
        if g:
            return (g["text"] + f"\n\n— صياغة: نموذج سحابي احتياطي ({g['model']}) لأن العقل الأساسي غير متصل.",
                    "cloud_brain_general", ["العقل السحابي الاحتياطي"])
    world = _world_answer_for_chat(text, raw=True)
    if world is not None and world.get("ok"):
        tools.append("بحث عالمي متعدد اللغات (بلا نموذج لغوي)")
        if cloud_brain.enabled():
            g = cloud_brain.grounded(text, world, history=history)
            if g:
                tools.append("صياغة سحابية مقيّدة بالمصادر")
                reply = (note + g["text"] + "\n\n" + _sources_block(world, g["text"])
                         + f"\n\nالمنهج: بحث عالمي متعدد اللغات وتقييم حتمي للمصادر، ثم صياغة بنموذج سحابي "
                           f"احتياطي ({g['model']}) مقيّد بالنقاط المرقمة فقط — أي استشهاد خارج المصادر يُرفض.")
                return reply, "brain_unreachable_world_search", tools
        return note + world_search.format_reply(world), "brain_unreachable_world_search", tools
    if cloud_brain.enabled():
        g = cloud_brain.general(text, history=history, lang=lang)
        if g:
            return (note + g["text"] + f"\n\n— تنبيه: لم أجد مصادر موثوقة كافية؛ هذا جواب نموذج سحابي احتياطي "
                    f"({g['model']}) بلا تحقق من مصادر — تحقق من الحقائق المهمة.",
                    "cloud_brain_general", ["العقل السحابي الاحتياطي"])
    if world is not None:
        return note + world_search.format_reply(world), "brain_unreachable_unanswered", tools
    return None


def _chat_agent_mode() -> bool:
    """R-789: المحادثة عبر حلقة الوكيل حين يكون العقل مفعّلًا (CHAT_AGENT_MODE=0 يعيد المسار
    القديم صراحةً). بلا عقل يبقى المسار القائم كما هو."""
    if str(os.getenv("CHAT_AGENT_MODE", "1")).strip().lower() in ("0", "false", "no", "off"):
        return False
    import chat_agent
    return chat_agent.brain_enabled()


def _github_repo_tool(url: str = "", repo: str = "", **_ignored) -> str:
    """R-789: معالج github.repo — يقبل رابطًا كاملًا أو owner/repo.
    R-789b: يقبل الاسم البديل repo (قياس حي: العقل أرسل {"repo": "owner/name"})."""
    import re as _re
    import chat_tools
    m = _re.search(r"(?:github\.com/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/?#]|$)",
                   str(url or repo or "").strip())
    if not m:
        raise ValueError("صيغة غير مفهومة — المطلوب رابط github.com/owner/repo أو owner/repo")
    return chat_tools.github_context(m.group(1), m.group(2))


def _register_real_tools() -> None:
    """R-729 (البند ٣.١): تسجيل القدرات الحقيقية الموجودة فعلًا في النظام.

    لا وهم: كل معالج يستدعي نفس منطق النقاط الحية (مصدر واحد — دوال
    الحمولة المشتركة). الأدوات الجديدة (بحث/تنفيذ كود/موصلات — ٣.٢+)
    تُسجل هنا عند بنائها، فيصبح هذا السجل مصدر الحقيقة الوحيد للقدرات."""
    from tool_registry import ToolSpec, get_registry
    registry = get_registry()
    if registry.list_tools():
        return  # مسجلة فعلًا (إعادة استيراد) — لا ازدواج
    registry.register(ToolSpec(
        name="health.snapshot",
        description="لقطة صحة النظام الكاملة (نفس منطق /health)",
        inputs={},
        outputs="status/version/timestamp/uptime/components",
        handler=_health_payload,
    ))
    registry.register(ToolSpec(
        name="memory.stats",
        description="إحصاءات الذاكرة الثلاث (نفس منطق /components/memory)",
        inputs={},
        outputs="core/dynamic/store/timestamp",
        handler=_memory_stats_payload,
    ))
    registry.register(ToolSpec(
        name="disk.status",
        description="حالة القرص السحابي Supabase (نفس منطق /disk/status) + القرص المحلي: "
                    "المساحة والعُقد (inodes) وحالتها",
        inputs={},
        outputs="cloud_disk/enabled/…/local_volume",
        handler=_disk_tool_payload,
    ))
    registry.register(ToolSpec(
        name="vault.status",
        description="حالة خزينة الأسرار AES-256-GCM (نفس منطق /vault/status) — بصمات فقط",
        inputs={},
        outputs="enabled/cipher/secrets[] (name/scopes/version/fingerprint)",
        handler=_vault_status_payload,
    ))
    registry.register(ToolSpec(
        name="agent.run",
        description="حلقة الوكيل (R-753): هدف → خطوة من العقل → أداة مسجلة → تحقق → "
                    "استمرار أو توقف صادق، بميزانيات وأثر موقّع — تتطلب العقل الحي (١.٦)",
        inputs={"goal": "الهدف", "max_steps": "سقف الخطوات (افتراضي 8، أقصى 32)"},
        outputs="run_id/status/steps[]/answer (answer فقط عند completed)",
        handler=lambda goal, max_steps=8: __import__("agent_loop").run_goal(goal, max_steps),
    ))
    # R-756 (V5 ٤.١): الموصلات — الحالة + أفعال كل موصل مضبوط كأدوات
    registry.register(ToolSpec(
        name="connectors.status",
        description="حالة الموصلات ومنحها وقواطعها (نفس منطق /connectors/status)",
        inputs={}, outputs="connectors{name: actions/granted/revoked/breaker}",
        handler=_connectors_status_payload))
    try:
        import connectors as _connectors_mod
        _hub = _connectors_mod.get_hub()
        for _cname in _hub.names():
            _cspec = _hub.spec(_cname)
            for _act in sorted(_cspec.actions):
                registry.register(ToolSpec(
                    name=f"connector.{_cname}.{_act}",
                    description=f"{_cspec.description} — فعل {_act} (منحة المالك شرط)",
                    inputs=dict(_cspec.inputs.get(_act, {})), outputs="ok/result/error",
                    handler=(lambda _n, _a: lambda **kw: _hub.call(_n, _a, kw))(_cname, _act)))
    except Exception as _conn_exc:  # TOLERATED: موصل معطوب لا يكسر الإقلاع — تحذير صادق
        logger.warning("R-756: تعذر تسجيل أفعال الموصلات (%s)", type(_conn_exc).__name__)
    # R-757 (V5 ٤.٢): اكتساب المهارات — الاقتراح والتقييم أداة؛ الاعتماد للمالك
    def _run_self_review_tool():
        """R-812: أداة سير التفتيش الذاتي — تنفيذ التطبيق + مراجعة الذكاء المرجعية."""
        import review_workflow
        return review_workflow.run_self_review(caller="agent")

    def _skills_install(manifest):
        import skills
        lib = skills.get_library()
        proposed = lib.propose(manifest, actor="agent")
        return {**lib.evaluate(proposed["skill"], proposed["version"]),
                "content_hash": proposed["content_hash"],
                "next": "اعتماد المالك عبر POST /skills/approve (لا تفعيل ذاتي)"}

    registry.register(ToolSpec(
        name="skills.install",
        description="اقتراح حزمة مهارة وتقييمها بحالاتها المرجعية (R-757) — التفعيل باعتماد المالك",
        inputs={"manifest": "حزمة المهارة (name/version/source/description/inputs/"
                            "permissions/steps/output/eval)"},
        outputs="state/passed/total/results/content_hash", handler=_skills_install))
    # R-812 (البندان ٤ و٥ و٦): سير عمل مدمج — المنفّذ هو التطبيق (حتمي)،
    # والمراجع هو الذكاء (عقد JSON، أثر موقّع، لا تنفيذ بيده أبدًا)
    registry.register(ToolSpec(
        name="system.self_review",
        description="تفتيش ذاتي مدمج: التطبيق ينفّذ الفحص حتميًا والذكاء الاصطناعي يراجعه كمرجع فقط — "
                    "يعمل كاملًا حتى مع عقل معطل (المشروع يقوم بكل شيء بنفسه)",
        inputs={},
        outputs="status/executor_findings/reviewer_verdict/duration_ms", handler=_run_self_review_tool))
    registry.register(ToolSpec(
        name="skills.status",
        description="المهارات وإصداراتها وحالاتها + الأدوات المكتشفة «متاحة غير مُتعلمة» (٤.٣)",
        inputs={}, outputs="skills[]/discovered[]",
        handler=lambda: __import__("skills").get_library().status()))
    # R-754 (V5 §٣): مهام دائمة — نقطة تفتيش بعد كل خطوة، استئناف بعد إعادة التشغيل
    def _tasks_start(goal):
        import durable_tasks
        runner = durable_tasks.get_runner()
        tid = runner.create(goal, {"kind": "brain"})
        return runner.run(tid)

    registry.register(ToolSpec(
        name="tasks.start",
        description="بدء مهمة دائمة بالعقل الحي (R-754) — نقطة تفتيش على القرص بعد كل خطوة",
        inputs={"goal": "الهدف"}, outputs="task_id/status/steps[]",
        handler=_tasks_start))
    registry.register(ToolSpec(
        name="tasks.resume",
        description="استئناف مهمة دائمة من آخر نقطة تفتيش (R-754) — فعل خارجي لا يتكرر",
        inputs={"task_id": "معرف المهمة"}, outputs="task_id/status/resumed/steps[]",
        handler=lambda task_id: __import__("durable_tasks").get_runner().run(task_id)))
    registry.register(ToolSpec(
        name="tasks.progress",
        description="تقدم مهمة من نقاط التفتيش على القرص حرفيًا (R-754 — ٣.٣)",
        inputs={"task_id": "معرف المهمة"}, outputs="status/done_steps/steps[]/pending_intents",
        handler=lambda task_id: __import__("durable_tasks").get_runner().progress(task_id)))
    # R-758 (V5 §٥): أسطول — عمال بأدوار وأهداف جزئية بسقف تزامن مُعلن
    registry.register(ToolSpec(
        name="fleet.spawn",
        description="أسطول وكلاء (R-758): هدف جزئي لكل عامل، سقف تزامن (FLEET_MAX_CONCURRENCY)، "
                    "عزل وإعادة جدولة الفاشل، تقرير صادق — يتطلب العقل الحي (١.٦)",
        inputs={"goals": "الأهداف الجزئية: قائمة JSON نصًا أو هدف في كل سطر",
                "max_concurrency": "سقف التزامن (افتراضي 4)"},
        outputs="status/registered/measured_peak_concurrency/completed/failed[]/results[]",
        handler=lambda goals, max_concurrency=4: __import__("fleet").spawn_goals(
            goals, int(max_concurrency))))
    # R-790 (V6 ٦.٩): المدير ينشئ الوكلاء بنفسه + الخبرة والمعرفة المكتسبة
    registry.register(ToolSpec(
        name="agent.manage",
        description="مدير الوكلاء (R-790): العقل يقرر بنفسه كم وكيلًا يلزم ودور كل منهم وهدفه، "
                    "ينشئهم وينظم عملهم ويجمع نتائجهم ويتعلم من التجربة — يتطلب العقل الحي",
        inputs={"goal": "الهدف", "max_agents": "سقف الوكلاء (افتراضي 4)"},
        outputs="status/plan/agents_created/agents[]/answer",
        handler=lambda goal, max_agents=None: __import__("manager").manage(goal, max_agents)))
    registry.register(ToolSpec(
        name="experience.stats",
        description="الخبرة المكتسبة: عدد التجارب والحقائق، توزيع النتائج، سلامة السلسلة، "
                    "ونسبة نجاح كل أداة من الوقائع المسجلة (R-790)",
        inputs={}, outputs="experiences/facts/by_status/chain/tools{}",
        handler=lambda: {**__import__("experience").get_store().stats(),
                         "tools": __import__("experience").get_store().tool_stats()}))
    registry.register(ToolSpec(
        name="experience.recall",
        description="أقرب التجارب السابقة لهدف: ما الأدوات التي استُخدمت وما النتيجة والخطأ (R-790)",
        inputs={"goal": "الهدف أو السؤال", "k": "العدد (افتراضي 5)"},
        outputs="items[] (goal/status/tools/error/score)",
        handler=lambda goal, k=5: {"items": __import__("experience").get_store().recall(goal, int(k))}))
    registry.register(ToolSpec(
        name="knowledge.remember",
        description="حفظ حقيقة تعلمها الوكيل مع مصدرها في المعرفة الدائمة (إلحاق فقط، R-790)",
        inputs={"fact": "الحقيقة", "source": "المصدر (رابط أو أداة)", "topic": "الموضوع"},
        outputs="id/hash/duplicate",
        handler=lambda fact, source="", topic="": __import__("experience").get_store().remember(
            fact, source, topic=topic)))
    registry.register(ToolSpec(
        name="knowledge.recall",
        description="استرجاع حقائق محفوظة في المعرفة الدائمة بالسؤال، مع مصادرها (R-790)",
        inputs={"query": "السؤال", "k": "العدد (افتراضي 5)"},
        outputs="facts[] (fact/source/score)",
        handler=lambda query, k=5: {"facts": __import__("experience").get_store().recall_facts(
            query, int(k))}))
    # R-791 (V6 ٦.٩.٣/٦.٩.٤): أهداف وخطط دائمة + حلقة الاستقلال
    registry.register(ToolSpec(
        name="goals.add",
        description="إضافة هدف دائم يعمل عليه العقل بنفسه (يخطط وينشئ وكلاء وينفذ ويتعلم) — R-791",
        inputs={"title": "الهدف", "priority": "الأولوية 1 (أعلى) إلى 5", "why": "السبب"},
        outputs="id/title/status/priority",
        handler=lambda title, priority=3, why="": __import__("goals").GoalStore().add(
            title, origin="owner", why=why, priority=int(priority or 3))))
    registry.register(ToolSpec(
        name="goals.list",
        description="الأهداف الدائمة: من وضعها (المالك أو العقل نفسه)، حالتها، خطتها، "
                    "وما أُنجز فيها فعلًا (R-791)",
        inputs={}, outputs="goals[] (id/title/origin/status/plan/runs/summary)",
        handler=lambda: {"goals": [{**g, "runs": g["runs"][-5:], "runs_total": len(g["runs"])}
                                   for g in __import__("goals").GoalStore().state().values()]}))
    registry.register(ToolSpec(
        name="goals.work",
        description="خطوة عمل واحدة الآن على هدف: العقل يقرر (عمل/إعادة تخطيط/تحقق/تعذر) "
                    "وينفذ بوكلاء ينشئهم — R-791",
        inputs={"goal_id": "معرف الهدف"}, outputs="status/task/answer/agents_created",
        handler=lambda goal_id: __import__("goals").GoalEngine().work(goal_id)))
    registry.register(ToolSpec(
        name="autonomy.status",
        description="حالة حلقة الاستقلال: مفعّلة أم لا ولماذا، الفاصل، عدد الدورات، آخر دورة (R-791)",
        inputs={}, outputs="enabled/reason/interval_s/ticks/last",
        handler=lambda: __import__("goals").get_loop().status()))
    registry.register(ToolSpec(
        name="autonomy.tick",
        description="تشغيل دورة استقلال واحدة الآن (عمل على أعلى هدف أو تأمل واقتراح أهداف) — R-791",
        inputs={}, outputs="tick/status/...",
        handler=lambda: __import__("goals").get_loop().run_once()))
    registry.register(ToolSpec(
        name="brain.status",
        description="حالة عقل Ollama ومصدر الرد (نفس منطق /brain/status)",
        inputs={},
        outputs="brain/enabled/reply_source/model",
        handler=_brain_status_payload,
    ))
    # ============================================================
    # R-738 (بأمر المالك «ترسانة عالمية»): أدوات الويب والاستدلال والمنسّق
    # ============================================================
    def _tool_research_run(goal):
        import research_orchestrator
        return research_orchestrator.run_research(goal)

    registry.register(ToolSpec(
        name="web.search",
        description=("بحث ويب حي — محرك world (R-825: Bing + أخبار Bing/Google + الفهرس الذاتي + "
                     "ويكيبيديا…) أو searxng/tavily إن ضُبطا — نتائج مستشهدة بمصادر وتواريخ"),
        inputs={"query": "سؤال البحث"}, outputs="results[] (title/url/snippet)",
        handler=lambda query: __import__("web_tools").search(query)))
    registry.register(ToolSpec(
        name="web.fetch",
        description="جلب صفحة وتحويلها لنص — محروس ضد SSRF (قفزات وحجم وأنواع)",
        inputs={"url": "عنوان الصفحة"}, outputs="url/title/text/content_type",
        handler=lambda url: __import__("web_tools").fetch(url)))
    registry.register(ToolSpec(
        name="web.summarize",
        description="استخلاص نص عبر عقل المنشور — بلا اختراع",
        inputs={"text": "النص المطلوب تلخيصه"}, outputs="summary",
        handler=lambda text: __import__("web_tools").summarize(text)))
    for _rname, _rdesc, _rinputs in (
        ("extract", "استخراج منظّم: نص → JSON بالحقول المطلوبة",
         {"text": "النص", "schema": "وصف الحقول"}),
        ("infer", "استنتاج: وقائع → استنتاجات صريحة",
         {"premises": "الوقائع (نص أو قائمة)"}),
        ("deduce", "استنباط: فرضيات واستنتاجات ضمنية من السياق",
         {"question": "السؤال", "context": "السياق (اختياري)"}),
        ("verify", "تنقيح: حكم على ادعاء مقابل دليل",
         {"claim": "الادعاء", "evidence": "الدليل"}),
        ("reason", "استدلال: خطوات منطقية وصولًا إلى استنتاج",
         {"question": "السؤال", "context": "السياق (اختياري)"}),
    ):
        def _make_reasoning_handler(fn_name):
            def _handler(**kwargs):
                import reasoning_tools
                return getattr(reasoning_tools, fn_name)(**kwargs)
            return _handler
        registry.register(ToolSpec(
            name=f"reasoning.{_rname}", description=_rdesc,
            inputs=_rinputs, outputs="حسب الأداة",
            handler=_make_reasoning_handler(_rname)))
    registry.register(ToolSpec(
        name="world.answer",
        description=("R-823: بحث عالمي بكل اللغات بلا نموذج لغوي — ترجمة السؤال ← بحث متعدد المزودات "
                     "(ويب/ويكيبيديا/أبحاث محكّمة) ← تقييم حتمي (صلة/موثوقية/توافق) ← ترجمة الجواب مع مصادره"),
        inputs={"question": "السؤال بأي لغة", "target_lang": "لغة الجواب (اختياري — لغة السؤال افتراضيًا)"},
        outputs="points[]/sources[]/providers/method",
        handler=lambda question, target_lang=None: __import__("world_search").answer(question, target_lang)))
    registry.register(ToolSpec(
        name="search.status",
        description=("R-825: حالة محرك البحث — آخر نتيجة حقيقية لكل مزود (Bing/الأخبار/ويكيبيديا/الأبحاث/…) "
                     "وحجم الفهرس الذاتي في Supabase وعدادات الذاكرة المؤقتة"),
        inputs={}, outputs="enabled/providers_last_run/index",
        handler=lambda: __import__("world_search").engine_status()))
    registry.register(ToolSpec(
        name="media.create",
        description=("R-824: استوديو الوسائط — تصميم صورة أو فيديو MP4 من وصف بأي لغة (خادم ذاتي ⇒ مولدات "
                     "ذكاء اصطناعي مأذونة ⇒ مصمم محلي) وحفظه في مساحة العمل"),
        inputs={"request": "الطلب/الوصف", "kind": "image أو video (اختياري)",
                "base_prompt": "وصف صورة سابقة لتعديلها (اختياري)"},
        outputs="ok/kind/provider/file/prompt/tried",
        handler=_tool_media_create))
    registry.register(ToolSpec(
        name="research.run",
        description="المنسّق: هدف → بحث ← قراءة مصادر ← استخراج ← استدلال ← تقرير مستشهد",
        inputs={"goal": "هدف البحث"}, outputs="report/sources/facts/steps",
        handler=_tool_research_run))

    registry.register(ToolSpec(
        name="defects.scan",
        description="R-743 (٤.٣): فحص ذاتي للعيوب — الصحة/المجدول/الحارس → قائمة عمل",
        inputs={},
        outputs="open_count/resolved_count/defects[]/health_history",
        handler=_defect_scan_payload,
    ))
    registry.register(ToolSpec(
        name="self.monitor",
        description="R-794 (٤.٦): مراقبة ذاتية موسّعة — القرص واتجاهه/أدوات فاشلة/سلسلة سجل التطور/"
                    "الاستقلال/أهداف عالقة/تراجع التطوير → اقتراحات للمالك (بلا تنفيذ ذاتي)",
        inputs={},
        outputs="open_count/defects[]/vitals/history",
        handler=_self_monitor_payload,
    ))
    registry.register(ToolSpec(
        name="selfdev.tick",
        description="R-796: دورة تطوير ذاتي — نتائج CI ← اقتراحات قابلة للإصلاح ← مسودة كود+اختبار "
                    "بالعقل (تحقق بنيوي؛ التطبيق RED→GREEN في CI؛ الترقية قرار المالك)",
        inputs={}, outputs="tick/status/task/errors/brain_seconds",
        handler=_selfdev_tick_payload,
    ))
    registry.register(ToolSpec(
        name="selfdev.request",
        description="R-796: طلب تطوير ذاتي من المالك — عنوان وتفصيل لما يجب إصلاحه أو إضافته في الكود",
        inputs={"title": "عنوان المهمة", "detail": "التفصيل (اختياري)"},
        outputs="id/status/title",
        handler=lambda title, detail="": __import__("self_develop").get_engine().request(
            title, detail, source="owner"),
    ))
    registry.register(ToolSpec(
        name="selfdev.status",
        description="R-796: حالة محرك التطوير الذاتي — المهام وحالاتها ونتائج CI (بلا شيفرة)",
        inputs={}, outputs="counts/tasks/last_tick/brain/durable",
        handler=lambda: __import__("self_develop").get_engine().status(),
    ))
    # R-800: أدوات مساحة العمل (ملفات/أرشيفات/تحليل/إنشاء/تحويل/مشاريع)
    from workspace import tools as _ws_tools
    _ws_tools.register(registry, ToolSpec)
    registry.register(ToolSpec(
        name="selfdev.nucleus",
        description="R-798: نواة التطوير الذاتي — الإشارات من كل أجزاء النظام وتحليلها وتوجيهها",
        inputs={}, outputs="active_signals/journal/last_cycle/brain",
        handler=lambda: __import__("selfdev.wiring", fromlist=["wiring"]).get_nucleus().status(),
    ))
    registry.register(ToolSpec(
        name="selfdev.unmet",
        description="R-798: الأهداف التي عجز عنها النظام (إصلاح/طلب مالك/هدف/خلل مكوّن) وسلّم تصعيدها",
        inputs={}, outputs="counts/goals/ladder",
        handler=lambda: __import__("selfdev.wiring", fromlist=["wiring"]).get_unmet().status(),
    ))
    registry.register(ToolSpec(
        name="media.image",
        description="R-747 (٣.٥): توليد صورة عبر خدمة ذاتية الاستضافة (LocalAI) — لا طرف ثالث",
        inputs={"prompt": "وصف الصورة", "size": "اختياري: 256x256|512x512|768x768|1024x1024"},
        outputs="image_b64/mime/bytes/sha256/size",
        handler=_media_tool,
    ))
    registry.register(ToolSpec(
        name="benchmark.run",
        description="R-746 (٤.٤): مقارنة دورية بمراجع عامة — زمن الرد/الجودة/تغطية الأدوات",
        inputs={},
        outputs="latency/quality/coverage/gaps/references",
        handler=_benchmark_payload,
    ))
    registry.register(ToolSpec(
        name="proposals.decide",
        description="R-745 (٤.٥): قرار المالك في اقتراح تحسين — approved/rejected/implemented",
        inputs={"proposal_id": "P-xxxxxxxx", "decision": "approved|rejected|implemented",
                "note": "اختياري", "commit": "SHA — إلزامي لـ implemented"},
        outputs="الاقتراح بعد القرار (status/history/commit)",
        handler=_proposal_decide,
        apply=_proposal_apply,
    ))
    registry.register(ToolSpec(
        name="sovereignty.score",
        description="تقرير درجة السيادة الكامل (نفس منطق /sovereignty/score)",
        inputs={},
        outputs="roadmap_v2/total_score/axes/primitives/composite",
        # R-788a: عبر المخزن نفسه — الأداة لم تعد تطلق حسابًا O(n) لكل نداء
        handler=lambda: _sovereignty_score_cached(),
    ))
    # R-789: أداتان حقيقيتان للمحادثة — كانتا جسرًا حتميًا يسبق العقل (R-787)، الآن يختارهما
    # العقل بنفسه عبر حلقة الوكيل كأي أداة مسجلة (أثر موقّع لكل نداء).
    registry.register(ToolSpec(
        name="system.capabilities",
        description="جرد قدرات النظام الحي: المستويات والأدوات والمعطل والمؤجل (نفس منطق /capabilities)",
        inputs={},
        outputs="levels/tools/deferred/disabled",
        handler=_capabilities_payload,
    ))
    registry.register(ToolSpec(
        name="github.repo",
        description="قراءة مستودع GitHub عام: الوصف واللغات والملفات وآخر الالتزامات وREADME",
        inputs={"url": "رابط المستودع أو owner/repo"},
        outputs="نص بيانات المستودع",
        handler=_github_repo_tool,
    ))


@app.get("/status", response_model=SystemStatusResponse)
async def system_status():
    """
    الحالة التفصيلية للنظام.
    
    تعرض:
    - حالة Orchestrator
    - صحة جميع المكونات
    - إحصائيات الأداء
    """
    orchestrator = app.state.orchestrator
    orchestrator_status = orchestrator.get_status()
    
    return SystemStatusResponse(
        status="operational",
        version="4.0.0",
        orchestrator=orchestrator_status,
        components=orchestrator.get_component_health(),
        uptime_seconds=time.time() - app.state.start_time,
        timestamp=time.time()
    )


async def _compose_chat_reply(text: str, result, orchestrator, default: str, history=None,
                              tool_context: str = "") -> str:
    """
    R-715: تركيب الرد المشترك بين POST /chat و WebSocket.
    منقول حرفيًا من /chat (R-614/S-9، R-704) — لا تغيير سلوكي لـ /chat.
    """
    reply = default
    intent_name = ""
    if result.decision:
        action = result.decision.get('action', 'continue')
        source = result.decision.get('source', 'orchestrator')
        
        # فهم NexusCore: لغة + مشاعر + نية
        nexus_perception = (result.perception or {}).get("nexus", {})
        sentiment_label = nexus_perception.get("sentiment", {}).get("label", "")
        intent_name = nexus_perception.get("intent", {}).get("name", "")
        
        # R-614: محرك الردود السيادي — يبني الرد من حالة النظام الحية
        # R-704: الاستدعاء في خيط عام — توليد عقل Ollama (HTTP) لا يحجب حلقة الأحداث
        try:
            from sovereign_response import build_reply
            # R-786: السياق يُمرَّر فقط عند وجوده — النداء بلا سياق كما كان حرفيًا
            _extra = {"history": history} if history else {}
            if tool_context:
                _extra["tool_context"] = tool_context  # R-787
            reply = await asyncio.to_thread(
                build_reply, intent_name, text, result, orchestrator=orchestrator, **_extra
            )
        except Exception as e:
            logger.warning(f"sovereign_response failed, falling back: {e}")
            if source == "nexus_intent" and intent_name:
                intent_ar = {
                    "greet": "تحية",
                    "help": "مساعدة",
                    "status": "حالة النظام",
                    "analyze": "تحليل",
                    "forecast": "تنبؤ",
                    "alert": "تنبيه",
                    "stop": "إيقاف",
                }.get(intent_name, intent_name)
                reply = f"فهمت — نيتك: {intent_ar}. القرار: {action}."
            elif source == "sovereign_controller":
                reply = f"قرار المتحكم السيادي: {action}."
            else:
                reply = f"تم تنفيذ القرار: {action}."
        
        # إضافة فهم المشاعر إن وُجد (فقط إن لم يضفها المحرك)
        if sentiment_label and sentiment_label != "neutral" and "مشاعرك" not in reply:
            sentiment_ar = {"positive": "إيجابية", "negative": "سلبية"}.get(sentiment_label, sentiment_label)
            reply += f" (مشاعرك: {sentiment_ar})"
    return reply


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={429: {"description": "Rate limit exceeded"}},
    dependencies=[Depends(enforce_chat_rate_limit)],
)
async def chat(message: ChatMessage, background_tasks: BackgroundTasks):
    """
    نقطة المحادثة الرئيسية.
    
    أرسل رسالة نصية وتلقى رداً ذكياً من الذكاء السيادي.
    
    **المعلمات:**
    - `text`: نص الرسالة (مطلوب)
    - `user_id`: معرف المستخدم (اختياري)
    - `session_id`: معرف الجلسة (اختياري، يتم إنشاؤه تلقائياً)
    """
    start_time = time.time()
    
    # ========================================================
    # فحص الأمان (R-608): فحص الرسالة قبل المعالجة
    # ========================================================
    safety_block = enforce_input_safety(message.text, is_sovereign=False)
    if safety_block is not None:
        safety_guard.log_sovereign_action("chat_blocked", {
            "user_id": message.user_id,
            "reason": safety_block[:100]
        })
        return ChatResponse(
            reply=safety_block,
            status="blocked",
            cycle_id="safety-block",
            processing_time_ms=round((time.time() - start_time) * 1000, 2),
            timestamp=start_time
        )
    
    # إنشاء session_id إذا لم يكن موجوداً
    session_id = message.session_id or str(uuid.uuid4())
    
    orchestrator = app.state.orchestrator
    
    # تحضير بيانات الإدراك
    input_data = {
        "type": "chat",
        "text": message.text,
        "user_id": message.user_id,
        "session_id": session_id,
        "timestamp": start_time
    }
    
    # تنفيذ دورة المعالجة في الخلفية (لتسريع الاستجابة)
    def process_in_background():
        orchestrator.run_cycle(input_data)
    
    background_tasks.add_task(process_in_background)
    
    # تنفيذ دورة فورية للحصول على الرد (نستخدم cache أو تنفيذ سريع)
    # ملاحظة: هذا مبسط، في الإنتاج سنستخدم استجابة غير متزامنة كاملة
    result = orchestrator.run_cycle(input_data)
    
    processing_time = (time.time() - start_time) * 1000
    # R-817 إحياء: زمن دورة المنسق وحدها (قبل تكوين الرد) — يُعاد مع الزمن الكلي
    cycle_time_ms = round(processing_time, 2)
    
    # استخراج الرد من النتيجة — R-614/S-9: رد حقيقي مبني على حالة النظام الحية
    # R-715: منطق التركيب نُقل كما هو إلى _compose_chat_reply ليشترك فيه /chat و WebSocket
    # R-786: سياق المحادثة — أدوار المستخدم السابقة تمر بطبقة الأمان نفسها؛ ما يُرفض يسقط
    history = []
    for turn in (message.history or []):
        if turn.role == "user" and enforce_input_safety(turn.content, is_sovereign=False) is not None:
            continue
        history.append({"role": turn.role, "content": turn.content})
    # R-824 (أمر المالك: «المشروع ينسى سياق المحادثة»): المتابعة تُحل إلى سؤال مكتمل حتميًا —
    # الجسر والبحث العالمي والوسائط ترى «كم عدد سكان اليابان» لا «وكم عدد سكانها» وحدها
    try:
        import context_resolver
        resolved = context_resolver.resolve(message.text, history)
    except Exception as e:  # TOLERATED: بلا محلل ⇒ الرسالة كما هي (يُسجل)
        logger.warning("R-824: تعذر حل السياق (%s)", type(e).__name__)
        resolved = {"original": message.text, "standalone": message.text, "followup": False, "kind": "none"}
    eff_text = resolved.get("standalone") or message.text
    _resolved_q = eff_text if resolved.get("followup") and resolved.get("kind") != "prev_op" else None

    def _early(reply_text, status_, tools_, media_=None):
        _ok = status_ in ("media_created", "prev_op_done")
        return ChatResponse(
            reply=reply_text, status="ok" if (result.success and _ok) else "error", cycle_id=result.cycle_id,
            processing_time_ms=round((time.time() - start_time) * 1000, 2), cycle_time_ms=cycle_time_ms,
            timestamp=start_time, tools_used=tools_, agent_status=status_, media=media_ or [],
            resolved_question=_resolved_q)

    # R-824 (أمر المالك: «لا يستطيع تصميم صور وفيديوهات»): طلب الوسائط يُنفذ مباشرة بالاستوديو —
    # بعقل أو بدونه — والناتج ملف حقيقي في مساحة العمل يُعرض في المحادثة برابط موقّع
    try:
        import media_studio
        media_req = media_studio.detect(eff_text if resolved.get("kind") != "prev_op" else "", history)
    except Exception as e:  # TOLERATED: كشف الوسائط مكمّل — فشله يُسجل والمحادثة تكمل
        logger.warning("R-824: تعذر كشف طلب الوسائط (%s)", type(e).__name__)
        media_req = None
    if media_req:
        m_reply, m_media, m_status = await asyncio.to_thread(_media_for_chat, media_req)
        _tools = ["استوديو الوسائط (" + ("فيديو" if media_req["kind"] == "video" else "صورة") + ")"]
        return _early(m_reply, m_status, _tools, m_media)
    if resolved.get("kind") == "prev_op" and _brain_unreachable_now():
        op_reply = await asyncio.to_thread(_prev_op_reply, resolved)
        if op_reply:
            return _early(op_reply, "prev_op_done",
                          ["ترجمة آلية" if resolved.get("op") == "translate" else "تلخيص استخلاصي"])
    # R-787: جسر المحادثة ↔ الأدوات — جرد القدرات وقراءة الروابط عبر السجل (أثر موقّع)
    tools_used: List[str] = []
    tool_context = ""
    direct_reply = None
    # R-822: العقل مفعّل لكن غير قابل للوصول (مزلاج R-821 مفتوح) ⇒ وضع الوكيل
    # لا يُجرَّب أصلًا — المحادثة تمر بالجسر الحتمي (أدوات حقيقية: GitHub/روابط/جرد)
    _use_agent = _chat_agent_mode() and not _brain_unreachable_now()

    async def _run_bridge():
        try:
            import chat_tools
            bridged = await asyncio.to_thread(chat_tools.gather, eff_text, _capabilities_payload)  # R-824
            return (bridged.get("context") or "", list(bridged.get("tools_used") or []),
                    bridged.get("direct_reply"))
        except Exception as e:  # TOLERATED: الجسر مكمّل — فشله لا يسقط المحادثة ويُسجل
            logger.warning("R-787: فشل جسر الأدوات (%s)", type(e).__name__)
            return "", [], None

    if not _use_agent:  # R-789: في وضع الوكيل العقل يقرر ما يُجلب، لا الجسر
        tool_context, tools_used, direct_reply = await _run_bridge()
    _bridge_kw = {"tool_context": tool_context} if tool_context else {}
    agent_status = None
    agent_reviewer = None
    if _chat_agent_mode() and not _use_agent:
        agent_status = "brain_unreachable_fallback"  # R-822: إعلان صادق للمسار المستخدم
    if _use_agent:
        # R-789 (أمر المالك: لا أجوبة مزروعة): العقل يفهم الرسالة ويختار الأدوات الحقيقية
        # بنفسه ويجيب من نتائجها؛ الجسر الحتمي والقوالب لا يُستعملان في هذا المسار.
        import chat_agent
        owner = bool(message.api_key) and verify_api_key(message.api_key)
        agent_text = message.text
        if owner and message.file_ids:
            agent_text = message.text + await asyncio.to_thread(_attachments_note, message.file_ids)
        if owner and message.project_id:
            agent_text = agent_text + await asyncio.to_thread(_project_note, message.project_id)
        # R-810/813 (البند ٢): اختيار النموذج يصل نداء العقل فعليًا (توجيهًا وجوابًا)
        agent_out = await asyncio.to_thread(chat_agent.respond, agent_text,
                                            history or None, owner=owner,
                                            model=message.model)
        reply = agent_out["reply"]
        tools_used = list(agent_out.get("tools_used") or [])
        agent_status = agent_out.get("status")
        agent_reviewer = agent_out.get("reviewer")
        # R-822: فشل المخطط لأن العقل غير قابل للوصول (فشل اتصال فتح المزلاج الآن) ⇒
        # لا رسالة فشل للمالك؛ الجسر الحتمي يجيب من الأدوات الحقيقية في نفس الطلب
        if agent_status == "planner_failed" and _brain_unreachable_now():
            tool_context, tools_used, direct_reply = await _run_bridge()
            _bridge_kw = {"tool_context": tool_context} if tool_context else {}
            agent_status = "brain_unreachable_fallback"
            if direct_reply:
                reply = direct_reply
            else:
                reply = await _compose_chat_reply(
                    message.text, result, orchestrator,
                    default="تم استلام رسالتك. أنا الذكاء السيادي، جاهز لخدمتك.",
                    history=history or None,
                    **_bridge_kw,
                )
    elif direct_reply:
        reply = direct_reply  # R-787b: سؤال القدرات يُجاب من الجرد الحي حرفيًا بلا نموذج
    else:
        reply = await _compose_chat_reply(
            message.text, result, orchestrator,
            default="تم استلام رسالتك. أنا الذكاء السيادي، جاهز لخدمتك.",
            history=history or None,
            **_bridge_kw,
        )
    
    # R-814: عقد الحالة الصادق — لا «ok» وحلقة الوكيل فشلت فعلًا؛ نجاح الجواب
    # في وضع الوكيل هو completed/answered_from_results فقط (وأي حالة أخرى فشل
    # يُعلن في الحالة العلوية مع بقاء النص الصادق). المسار القديم كما كان.
    # R-822c: العقل غير قابل للوصول والطلب مفتوح بلا أدوات ⇒ لم يُجب فعلًا (عقد R-814: لا ok)
    if agent_status == "brain_unreachable_fallback" and _is_unanswered(reply):
        agent_status = "brain_unreachable_unanswered"
        # R-823 (أمر المالك: «البحث في مواقع العالم بكل اللغات وتقييم أصدق إجابة وترجمتها لا
        # يتطلب نموذجًا لغويًا»): الطلب المفتوح يُجاب بالبحث العالمي الحتمي بأثر موقّع
        # R-824: بالسؤال المحلول من السياق، مع صياغة سحابية مقيدة بالمصادر أو عقل سحابي للمهام الإنشائية
        world = await asyncio.to_thread(_chat_answer_without_brain, eff_text, history or None, resolved)
        if world is not None:
            reply, agent_status, _wt = world
            tools_used = tools_used + _wt
    # R-823: العقل معطّل كليًا (لا وضع وكيل) والرد قالب قرار داخلي لا يجيب الطلب ⇒ البحث العالمي
    if agent_status is None and not direct_reply and str(reply or "").startswith("تم تنفيذ القرار:"):
        world = await asyncio.to_thread(_chat_answer_without_brain, eff_text, history or None, resolved)
        if world is not None:
            reply = world[0]
            agent_status = {"brain_unreachable_world_search": "world_search",
                            "cloud_brain_general": "cloud_brain_general"}.get(world[1], "world_search_unanswered")
            tools_used = tools_used + world[2]
    # R-822: brain_unreachable_fallback = جواب حقيقي من الأدوات/الحالة الحية (معلن في agent_status)
    _agent_ok = agent_status in (None, "completed", "answered_from_results",
                                 "brain_unreachable_fallback",
                                 "brain_unreachable_world_search", "world_search",  # R-823: جواب مستشهد من مصادر حقيقية
                                 "cloud_brain_general")  # R-824: عقل سحابي احتياطي معلن في الرد
    return ChatResponse(
        reply=reply,
        status="ok" if (result.success and _agent_ok) else "error",
        cycle_id=result.cycle_id,
        # R-789: الزمن بعد تكوين الرد (كان يُقاس قبله فلا يشمل العقل)
        processing_time_ms=round((time.time() - start_time) * 1000, 2),
        cycle_time_ms=cycle_time_ms,
        timestamp=start_time,
        tools_used=tools_used,
        agent_status=agent_status,
        reviewer=agent_reviewer,
        resolved_question=_resolved_q,
    )


# ============================================================
# نقاط API للسيد (تتطلب مصادقة)
# ============================================================

def verify_api_key(api_key: str) -> bool:
    """التحقق من صحة مفتاح API للسيد

    ⚠️ SECURITY (جولة المجلس <1> — أمين 1.6): مقارنة ثابتة الزمن — لا تسريب توقيت.
    R-697 (D-033): المفتاح القياسي مشتق (api_auth). الجذر legacy مقبول للقراءة فقط.
    """
    if not api_key:
        return False
    # مقارنة بايتات UTF-8 (اعتراض المراجع): المدخلات غير-ASCII تُرفض لا
    # تتحول إلى خطأ خادم.
    key_bytes = str(api_key).encode("utf-8")
    return hmac.compare_digest(
        key_bytes, _derive_api_auth("api_auth").encode("utf-8")
    ) or hmac.compare_digest(
        key_bytes, str(SOVEREIGN_API_KEY).encode("utf-8")  # LEGACY-ROOT-KEY (read-only)
    )


@app.post("/sovereign/command", response_model=SovereignCommandResponse)
async def sovereign_command(command: SovereignCommand):
    """
    تنفيذ أمر من السيد.
    
    **الأوامر المدعومة:**
    - `reset` - إعادة تهيئة النظام
    - `reset_component` - إعادة تهيئة مكون معين
    - `set_mode` - تغيير وضع التشغيل
    - `get_status` - الحصول على حالة مفصلة
    - `get_components` - الحصول على حالة المكونات
    - `get_history` - الحصول على سجل الأحداث
    - `get_health` - الحصول على صحة المكونات
    """
    if not verify_api_key(command.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="مفتاح API غير صحيح"
        )
    
    # ========================================================
    # فحص الأمان (R-608): حتى السيد تُفحص الأوامر الممنوعة تماماً
    # ========================================================
    safety_block = enforce_input_safety(command.command, is_sovereign=True)
    if safety_block is not None:
        return SovereignCommandResponse(
            success=False,
            message=safety_block,
            data={"blocked_by": "safety_guard"},
            timestamp=time.time()
        )
    
    orchestrator = app.state.orchestrator
    cmd = command.command.lower()
    params = command.parameters
    
    try:
        if cmd == "reset":
            preserve_data = params.get("preserve_data", False)
            orchestrator.reset_all(preserve_session=preserve_data)
            return SovereignCommandResponse(
                success=True,
                message="تم إعادة تهيئة النظام بنجاح",
                data={"preserve_data": preserve_data},
                timestamp=time.time()
            )
        
        elif cmd == "reset_component":
            component_name = params.get("component")
            if not component_name:
                return SovereignCommandResponse(
                    success=False,
                    message="يرجى تحديد اسم المكون (component)",
                    data={},
                    timestamp=time.time()
                )
            success = orchestrator.reset_component(component_name)
            return SovereignCommandResponse(
                success=success,
                message=f"تم إعادة تهيئة {component_name}" if success else f"فشل إعادة تهيئة {component_name}",
                data={"component": component_name},
                timestamp=time.time()
            )
        
        elif cmd == "set_mode":
            mode = params.get("mode", "normal")
            success = orchestrator.set_mode(mode)
            return SovereignCommandResponse(
                success=success,
                message=f"تم تغيير الوضع إلى {mode}" if success else f"الوضع {mode} غير صالح",
                data={"mode": mode},
                timestamp=time.time()
            )
        
        elif cmd == "get_status":
            system_status = orchestrator.get_status()
            return SovereignCommandResponse(
                success=True,
                message="حالة النظام",
                data=system_status,
                timestamp=time.time()
            )
        
        elif cmd == "get_components":
            components = orchestrator.get_component_health()
            return SovereignCommandResponse(
                success=True,
                message="حالة المكونات",
                data={"components": components},
                timestamp=time.time()
            )
        
        elif cmd == "get_history":
            limit = params.get("limit", 100)
            history = orchestrator.get_history(limit=limit)
            return SovereignCommandResponse(
                success=True,
                message=f"آخر {len(history)} حدث",
                data={"history": history},
                timestamp=time.time()
            )
        
        elif cmd == "get_health":
            health = orchestrator.get_component_health()
            return SovereignCommandResponse(
                success=True,
                message="صحة المكونات",
                data={"health": health},
                timestamp=time.time()
            )
        
        else:
            return SovereignCommandResponse(
                success=False,
                message=f"أمر غير معروف: {cmd}",
                data={"supported_commands": ["reset", "reset_component", "set_mode", "get_status", "get_components", "get_history", "get_health"]},
                timestamp=time.time()
            )
    
    except Exception as e:
        logger.error(f"خطأ في تنفيذ الأمر {cmd}: {e}")
        return SovereignCommandResponse(
            success=False,
            message=f"خطأ: {str(e)}",
            data={},
            timestamp=time.time()
        )


@app.post("/sovereign/reset")
async def sovereign_reset(request: ResetRequest):
    """
    إعادة تهيئة النظام أو مكون معين.
    
    **الاستخدام:**
    - إعادة تهيئة الكل: `{"component": null, "preserve_data": false, "api_key": "..."}`
    - إعادة تهيئة مكون: `{"component": "memory_core", "preserve_data": true, "api_key": "..."}`
    """
    if not verify_api_key(request.api_key):
        raise HTTPException(status_code=401, detail="مفتاح API غير صحيح")
    
    # ========================================================
    # فحص الأمان (R-608): إعادة التهيئة فعل خطير — يُفحص دائماً
    # ========================================================
    safety_block = enforce_input_safety("reset system", is_sovereign=True)
    if safety_block is not None:
        raise HTTPException(status_code=403, detail=safety_block)
    
    orchestrator = app.state.orchestrator
    
    if request.component:
        success = orchestrator.reset_component(request.component)
        return {
            "success": success,
            "message": f"تم إعادة تهيئة {request.component}" if success else f"فشل إعادة تهيئة {request.component}",
            "component": request.component,
            "timestamp": time.time()
        }
    else:
        orchestrator.reset_all(preserve_session=request.preserve_data)
        return {
            "success": True,
            "message": "تم إعادة تهيئة النظام بالكامل",
            "preserve_data": request.preserve_data,
            "timestamp": time.time()
        }


# ============================================================
# نقاط API للمكونات الفردية
# ============================================================

@app.get("/components/consciousness")
async def get_consciousness_status():
    """الحصول على حالة الوعي"""
    try:
        field = get_consciousness_field()
        identity = get_identity_core()
        self_model = get_self_model()
        awareness = get_awareness_engine()
        attention = get_attention_engine()
        introspection = get_introspection_engine()
        
        return {
            "field": field.get_consciousness_status() if field else None,
            "identity": identity.get_identity_status() if identity else None,
            "self_model": self_model.get_self_status() if self_model else None,
            "awareness": awareness.get_awareness_status() if awareness else None,
            "attention": attention.get_attention_status() if attention else None,
            "introspection": introspection.get_introspection_status() if introspection else None,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/components/memory")
async def get_memory_status():
    """الحصول على حالة الذاكرة"""
    try:
        return _memory_stats_payload()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _memory_stats_payload() -> Dict[str, Any]:
    """حمولة /components/memory — تخدم النقطة وأداة السجل memory.stats (R-729)."""
    core = get_core()
    dynamic = get_dynamic_memory()
    store = get_store()
    return {
        "core": core.get_statistics() if core else None,
        "dynamic": dynamic.statistics() if dynamic else None,
        "store": store.get_statistics() if store else None,
        "timestamp": time.time()
    }


@app.get("/components/predictive")
async def get_predictive_status():
    """الحصول على حالة التنبؤ"""
    try:
        engine = get_predictive_engine()
        controller = get_predictive_controller()
        risk_manager = get_predictive_risk_manager()
        
        return {
            "engine": engine.get_prediction_status() if engine else None,
            "controller": {
                "stats": controller.get_stats() if controller else None,
                "mode": controller.get_mode() if controller else None,
                "last_decision": controller.get_last_decision() if controller else None,
            } if controller else None,
            "risk_manager": risk_manager.get_risk_status() if risk_manager else None,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/components/simulation")
async def get_simulation_status():
    """الحصول على حالة المحاكاة"""
    try:
        controller = get_simulation_controller()
        analyzer = get_simulation_analyzer()
        
        return {
            "controller": controller.get_controller_status() if controller else None,
            "analyzer": analyzer.get_analyzer_status() if analyzer else None,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/components/sovereign")
async def get_sovereign_status():
    """الحصول على حالة السيادة"""
    try:
        will = get_sovereign_will()
        alignment = get_sovereign_alignment()
        directives = get_sovereign_directives()
        controller = get_sovereign_controller()
        
        return {
            "will": will.get_will_status() if will else None,
            "alignment": alignment.get_alignment_status() if alignment else None,
            "directives": directives.get_directives_status() if directives else None,
            "controller": controller.get_controller_status() if controller else None,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/components/quantum")
async def get_quantum_status():
    """الحصول على حالة الكم"""
    try:
        controller = get_quantum_controller()
        
        return {
            "controller": controller.get_controller_status() if controller else None,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/components/nexus")
async def get_nexus_status():
    """الحصول على حالة منصة NexusCore (مدمجة في R-301)"""
    try:
        orchestrator = app.state.orchestrator
        nexus = getattr(orchestrator, "nexus", None)
        health = orchestrator.get_component_health().get("nexus_engine", {})
        return {
            "nexus": {
                "loaded": nexus is not None,
                "health": health,
                "engine_id": getattr(nexus, "engine_id", None) if nexus else None,
                "state": getattr(nexus, "state", None).value if nexus and hasattr(getattr(nexus, "state", None), "value") else None,
                "components": list(getattr(nexus, "components", {}).keys()) if nexus else []
            },
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# نقاط الأمان (R-608) — طبقة الأمان السيادية
# ============================================================

@app.get("/security/status")
async def get_security_status():
    """حالة طبقة الأمان السيادية"""
    return {
        "safety_guard": {
            "active": True,
            "forbidden_absolute": len(safety_guard.forbidden_absolute),
            "dangerous_patterns": list(safety_guard.dangerous_patterns.keys()),
            "approval_cache_entries": len(safety_guard.approval_cache),
            "security_log_file": str(safety_guard.security_log_file),
        },
        "rate_limiter": {
            "active": True,
            "max_per_minute": MAX_USER_MESSAGES_PER_MINUTE,
        },
        "nexus_api": {
            "active": True,
            "endpoints": ["/nexus/status", "/nexus/analyze/text", "/nexus/ingest", "/nexus/health", "/nexus/budget/analyze", "/nexus/recommendations"],
        },
        "timestamp": time.time()
    }


@app.get("/security/log")
async def get_security_log(limit: int = Query(50, ge=1, le=500),
                          x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """آخر أحداث سجل الأمان

    ⚠️ SECURITY (جولة المجلس <1> — أمين 1.4/بصير BAS-S10/حكيم):
    سجل الأمان يكشف أوامر السيد — يتطلب مفتاح السيد (X-API-Key).
    """
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="مفتاح السيد مطلوب لقراءة سجل الأمان")
    log_file = safety_guard.security_log_file
    if not log_file.exists():
        return {"events": [], "total": 0}
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            log = json.load(f)
        return {"events": log[-limit:], "total": len(log)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/components/defense")
async def get_defense_status():
    """الحصول على حالة الدفاع"""
    try:
        stealth = get_stealth_defense()
        polymorphic = get_polymorphic_defense()
        
        return {
            "stealth": stealth.get_status() if stealth else None,
            "polymorphic": polymorphic.get_status() if polymorphic else None,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# WebSocket للمحادثة المباشرة
# ============================================================

class ConnectionManager:
    """مدير اتصالات WebSocket"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        session_id = str(uuid.uuid4())
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        return session_id
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        # إزالة من user_sessions
        for user_id, sid in list(self.user_sessions.items()):
            if sid == session_id:
                del self.user_sessions[user_id]
                break
    
    async def send_message(self, session_id: str, message: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)


manager = ConnectionManager()


_WS_PING_TYPES = {"ping", "heartbeat"}
_WS_CHAT_TYPES = {"chat_message", "chat"}
_WS_SOVEREIGN_TYPES = {"sovereign_command"}


def _parse_ws_frame(raw: str) -> dict:
    """
    R-715: تصنيف إطار WebSocket الوارد.

    - مغلّف الواجهة: {"type": "...", "payload": {...}}
      * ping/heartbeat ← kind=ping (بلا دورة)
      * chat_message ← kind=chat (النص من payload.text)
      * sovereign_command ← kind=sovereign_refused (يتطلب مفتاح السيد عبر HTTP)
      * غير ذلك (hello، run_cycle، ...) ← kind=ignored (بلا دورة)
    - الصيغة القديمة: {"text": "..."} ← kind=chat (envelope=False)
    - نص خام غير JSON ← kind=chat (سلوك سابق محفوظ)
    - JSON ليس كائنًا ← kind=invalid
    """
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        text = (raw or "").strip()
        if not text:
            return {"kind": "invalid", "reason": "رسالة فارغة."}
        return {"kind": "chat", "text": text, "envelope": False}

    if not isinstance(obj, dict):
        return {"kind": "invalid", "reason": "صيغة الإطار غير صالحة: يُتوقع كائن JSON."}

    if "type" in obj:
        frame_type = str(obj.get("type") or "")
        payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
        if frame_type in _WS_PING_TYPES:
            return {"kind": "ping"}
        if frame_type in _WS_SOVEREIGN_TYPES:
            return {"kind": "sovereign_refused"}
        if frame_type in _WS_CHAT_TYPES:
            text = payload.get("text", obj.get("text", ""))
            text = text.strip() if isinstance(text, str) else ""
            if not text:
                return {"kind": "invalid", "reason": "رسالة فارغة."}
            return {"kind": "chat", "text": text, "envelope": True}
        return {"kind": "ignored", "received_type": frame_type[:64]}

    text = obj.get("text", "")
    text = text.strip() if isinstance(text, str) else ""
    if not text:
        return {"kind": "invalid", "reason": "رسالة فارغة."}
    return {"kind": "chat", "text": text, "envelope": False}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    نقطة WebSocket للمحادثة المباشرة.
    
    الاتصال: `ws://localhost:8000/ws/{user_id}`
    
    إرسال رسالة: `{"text": "مرحباً"}` (يُرد بالنوع "reply")
    أو مغلّف الواجهة: `{"type": "chat_message", "payload": {"text": "مرحباً"}}`
    (يُرد بالنوع "chat_reply"). ping ← pong بلا دورة (R-715).
    """
    session_id = await manager.connect(websocket, user_id)
    
    try:
        # رسالة ترحيب
        await manager.send_message(session_id, json.dumps({
            "type": "welcome",
            "message": f"مرحباً {user_id}، أنا الذكاء السيادي. كيف أستطيع مساعدتك؟",
            "session_id": session_id,
            "timestamp": time.time()
        }))
        
        orchestrator = app.state.orchestrator
        
        while True:
            # استقبال رسالة
            data = await websocket.receive_text()
            
            # R-715: فك الإطار — يدعم مغلّف الواجهة {"type","payload"} والصيغة القديمة {"text"}
            frame = _parse_ws_frame(data)
            kind = frame["kind"]
            
            if kind == "ping":
                # نبض الواجهة كل بضع ثوانٍ — لا دورة منسّق
                await manager.send_message(session_id, json.dumps({
                    "type": "pong", "timestamp": time.time()
                }))
                continue
            
            if kind == "ignored":
                await manager.send_message(session_id, json.dumps({
                    "type": "system",
                    "event": "ignored",
                    "received_type": frame["received_type"],
                    "message": "نوع الإطار لا يُعالَج عبر WebSocket — لم تُشغَّل دورة.",
                    "timestamp": time.time()
                }))
                continue
            
            if kind == "sovereign_refused":
                await manager.send_message(session_id, json.dumps({
                    "type": "error",
                    "message": "الأوامر السيادية لا تُقبل عبر WebSocket. استخدم POST /sovereign/command مع مفتاح السيد.",
                    "timestamp": time.time()
                }))
                continue
            
            if kind == "invalid":
                await manager.send_message(session_id, json.dumps({
                    "type": "error",
                    "message": frame["reason"],
                    "timestamp": time.time()
                }))
                continue
            
            text = frame["text"]
            reply_type = "chat_reply" if frame["envelope"] else "reply"
            
            # معالجة الرسالة
            input_data = {
                "type": "chat_websocket",
                "text": text,
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": time.time()
            }
            
            # فحص الأمان السيادي (R-608) — حماية مدخلات WebSocket
            safety_block = enforce_input_safety(text, is_sovereign=False)
            if safety_block is not None:
                safety_guard.log_sovereign_action("ws_chat_blocked", {
                    "user_id": user_id,
                    "reason": safety_block[:100]
                })
                await manager.send_message(session_id, json.dumps({
                    "type": reply_type,
                    "message": safety_block,
                    "payload": {"text": safety_block},
                    "blocked": True,
                    "cycle_id": "safety-block",
                    "timestamp": time.time()
                }))
                continue
            
            result = orchestrator.run_cycle(input_data)
            
            # R-715: نفس محرك الردود الذي يستخدمه POST /chat (build_reply/Ollama)
            reply = await _compose_chat_reply(
                text, result, orchestrator,
                default=f"تم استلام رسالتك: '{text}'. أنا الذكاء السيادي.",
            )
            
            await manager.send_message(session_id, json.dumps({
                "type": reply_type,
                "message": reply,
                "payload": {"text": reply},
                "cycle_id": result.cycle_id,
                "timestamp": time.time()
            }))
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected: {user_id}")


# ============================================================
# نقاط API إضافية
# ============================================================

# R-658: دعم الاعتماد في الرأس (X-API-Key) — دون حذف الواجهة القديمة
# المفتاح في الرأس لا يُسجّل في روابط الطلب (مثل query params)
from fastapi import Header

@app.get("/api-key-header")
async def get_api_key_header(
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """
    حالة مفتاح API للسيد (R-658) — نسخة الرأس.
    المفتاح في الرأس X-API-Key لا يُسجّل في روابط الطلب
    (بعكس query params مثل master_key في /api-key).
    لا يُكشف المفتاح نفسه أبداً — يُعاد فقط بصمة المفتاح (SHA-256).
    """
    # ⚠️ SECURITY (جولة المجلس <1> — أمين 1.6 + اعتراض المراجع): مقارنة
    # ثابتة الزمن عبر verify_api_key — لا مقارنة مباشرة
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=403, detail="غير مصرح: مطلوب مفتاح السيد")
    from config import SOVEREIGN_KEY_FINGERPRINT  # LEGACY-ROOT-KEY (read-only): بصمة عرض
    return {
        "fingerprint": SOVEREIGN_KEY_FINGERPRINT,  # LEGACY-ROOT-KEY (read-only): بصمة عرض
        "source": "header (X-API-Key) — not logged in URLs",
        "note": "المفتاح لا يُكشف عبر API. أعد تعيينه عبر SOVEREIGN_KEY أو data/key.secret.",  # LEGACY-ROOT-KEY (read-only): نص إرشادي
        "timestamp": time.time()
    }


@app.get("/api-key")
async def get_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """
    حالة مفتاح API للسيد (R-614/S-5).

    ⚠️ SECURITY (جولة المجلس <1> — أمين 1.5/بصير BAS-C05/حكيم):
    المفتاح يُستقبل في الرأس X-API-Key فقط — صيغة الاستعلام (master_key)
    أُزيلت لأنها تُسجّل في سجلات الوصول (uvicorn access log).
    لا يُكشف المفتاح نفسه أبداً — يُعاد فقط بصمة المفتاح (SHA-256) ومصدره
    ومدى ثباته عبر إعادة التشغيل. المفتاح الحقيقي يُدار عبر متغير البيئة
    SOVEREIGN_KEY أو ملف data/key.secret (مستثنى من git، صلاحيات 0600).  # LEGACY-ROOT-KEY (read-only): نص إرشادي
    """
    if not x_api_key or not verify_api_key(x_api_key):
        raise HTTPException(status_code=403, detail="غير مصرح: مطلوب مفتاح السيد في الرأس X-API-Key")
    from config import SOVEREIGN_KEY_FINGERPRINT, DATA_DIR, IS_DEVELOPMENT  # LEGACY-ROOT-KEY (read-only): بصمة عرض
    secret_file = DATA_DIR / "key.secret"
    return {
        "fingerprint": SOVEREIGN_KEY_FINGERPRINT,  # LEGACY-ROOT-KEY (read-only): بصمة عرض
        "persistent": secret_file.exists() or bool(os.getenv("SOVEREIGN_KEY")),  # LEGACY-ROOT-KEY (read-only): حالة عرض
        "source": "env" if os.getenv("SOVEREIGN_KEY") else ("key.secret" if secret_file.exists() else "ephemeral"),  # LEGACY-ROOT-KEY (read-only): حالة عرض
        "development": IS_DEVELOPMENT,
        "note": "المفتاح لا يُكشف عبر API. أعد تعيينه عبر SOVEREIGN_KEY أو data/key.secret.",  # LEGACY-ROOT-KEY (read-only): نص إرشادي
        "timestamp": time.time()
    }


@app.post("/orchestrator/cycle")
async def run_orchestrator_cycle(input_data: Dict[str, Any] = None):
    """
    تشغيل دورة Orchestrator يدوياً.
    
    M1: يتطلب مفتاح API في الرأس X-API-Key (كان مفتوحاً بدون مصادقة).
    مفيد للاختبار والتشخيص.
    """
    api_key = input_data.get("api_key") if input_data else None
    if not api_key or not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="مفتاح API غير صحيح")
    orchestrator = app.state.orchestrator
    result = orchestrator.run_cycle(input_data or {})
    
    return {
        "cycle_id": result.cycle_id,
        "success": result.success,
        "duration": result.duration,
        "decision": result.decision,
        "errors": result.errors,
        "timestamp": time.time()
    }


# R-817: توافر وحدات المنسق — إحياء الاستيرادات العلوية بخريطة تشخيص حية
@app.get("/orchestrator/modules")
async def orchestrator_module_availability(x_api_key: str = Header(None, alias="X-API-Key")):
    """خريطة الوحدات المتاحة/المعطلة عند تحميل المنسق (R-817)."""
    if not x_api_key or not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="مفتاح API غير صحيح")
    from orchestrator import get_module_availability
    availability = get_module_availability()
    return {
        "modules": availability,
        "available_count": sum(1 for v in availability.values() if v),
        "total_count": len(availability),
        "timestamp": time.time(),
    }


# R-800: مساحة العمل (ملفات/أرشيفات/تحليل/إنشاء/تصدير/محادثات/مشاريع) — بمفتاح المالك
from workspace.api import make_router as _ws_make_router  # noqa: E402
app.include_router(_ws_make_router(verify_api_key))

# ============================================================
# تقديم الملفات الثابتة للواجهة الأمامية
# ============================================================

if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")

if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

if (FRONTEND_DIR / "ui").exists():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR / "ui")), name="ui")

if (FRONTEND_DIR / "themes").exists():
    app.mount("/themes", StaticFiles(directory=str(FRONTEND_DIR / "themes")), name="themes")

if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

# ============================================================
# تشغيل الخادم (عند تنفيذ الملف مباشرة)
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🌐 Sovereign AI Web Server - الخادم السيادي الكامل")
    print("=" * 80)
    # R-617: لا يُسجّل المفتاح نفسه أبدًا — فقط بصمته (أول 8 أحرف من sha256)
    _fp = hashlib.sha256(SOVEREIGN_API_KEY.encode()).hexdigest()[:8]
    print(f"\n🔑 مفتاح API للسيد (بصمة فقط): {_fp}...")
    print("📖 التوثيق: http://localhost:8000/docs")
    print("🏥 فحص الصحة: http://localhost:8000/health")
    print("📊 حالة النظام: http://localhost:8000/status")
    print(f"🔌 WebSocket: ws://localhost:8000/ws/{'user_id'}")
    print("\n" + "=" * 80 + "\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


# R-729 (البند ٣.١): تسجيل الأدوات الحقيقية — في نهاية الملف لأن دوال الحمولة
# المشتركة (آخرها _memory_stats_payload) معرّفة قبل هذا السطر.
_register_real_tools()

# R-738: بوابة MCP — تسجيل ديناميكي لأدوات خوادم MCP إن فعلها المالك
# (MCP_ENABLED) — فشل خادم يُسجل تحذيرًا صادقًا ويُتخطى (لا اتصال ضمني)
try:
    import mcp_gateway
    # R-755: get_registry لم يُستورد في نطاق الوحدة قط (NameError مبتلع منذ R-738)
    from tool_registry import get_registry as _mcp_get_registry
    mcp_gateway.sync_into_registry(_mcp_get_registry())
except Exception as _mcp_exc:  # لا يكسر الإقلاع أبدًا — تحذير صادق فقط
    logging.getLogger("sovereign.mcp").warning(
        "R-738 [MCP]: تعذر تسجيل أدوات MCP (%s) — تُعاد المحاولة عند "
        "إعادة الإقلاع", type(_mcp_exc).__name__)

# R-757: المهارات المفعلة تُحمّل من القرص عند الإقلاع (بصمة تُفحص — لا إعادة تعلم)
try:
    import skills as _skills_mod
    _skills_mod.get_library().load_active()
except Exception as _skills_exc:  # TOLERATED: مهارة معطوبة لا تكسر الإقلاع — تحذير صادق
    logging.getLogger("sovereign.skills").warning(
        "R-757: تعذر تحميل المهارات المفعلة (%s)", type(_skills_exc).__name__)
