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
import json
import time
import uuid
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum

import os
import pathlib

from fastapi import (
    FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends,
    status, BackgroundTasks, Query,
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
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
# M1: يُقرأ من config (SOVEREIGN_KEY من متغير البيئة) بدلاً من توليد عشوائي غير محفوظ
from config import SOVEREIGN_KEY as SOVEREIGN_API_KEY

# إعدادات CORS (السماح بالاتصال من جميع المصادر)
# M1: CORS من config (متغير البيئة CORS_ORIGINS) — ليس مفتوحاً دائماً
from config import CORS_ORIGINS as ALLOWED_ORIGINS
from config import MAX_USER_MESSAGES_PER_MINUTE
from rate_limit import SlidingWindowRateLimiter
from safety import SafetyGuard, ActionType

chat_rate_limiter = SlidingWindowRateLimiter(MAX_USER_MESSAGES_PER_MINUTE)

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

class ChatMessage(BaseModel):
    """رسالة محادثة"""
    text: str = Field(..., min_length=1, max_length=10000, description="نص الرسالة")
    user_id: str = Field(default="anonymous", max_length=100, description="معرف المستخدم")
    session_id: Optional[str] = Field(default=None, description="معرف الجلسة")
    
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    دورة حياة التطبيق - يتم تنفيذها عند بدء وإيقاف الخادم.
    """
    # بدء التشغيل
    logger.info("🚀 بدء تشغيل خادم Sovereign AI...")
    
    # تهيئة Orchestrator
    orchestrator = get_orchestrator()
    app.state.orchestrator = orchestrator
    
    # تخزين وقت بدء التشغيل
    app.state.start_time = time.time()
    
    # تسجيل نجاح بدء التشغيل
    logger.info("✅ خادم Sovereign AI جاهز")
    logger.info(f"🔑 مفتاح API للسيد: {SOVEREIGN_API_KEY}")
    logger.info(f"📖 التوثيق: http://localhost:8000/docs")
    # طبقة توافق: تشغيل محرك NexusCore فعليًا (يصلح state=initializing الدائم)
    # انظر backend/compat/nexus_lifecycle.py — لا تعديل للأصل، بل استدعاء engine.start()
    # ملاحظة: تُستخدم النسخة غير المتزامنة لأننا داخل حلقة حدث نشطة (lifespan)
    try:
        await ensure_nexus_running_async()
    except Exception as _nexus_lifecycle_err:
        logger.warning(f"⚠️ NexusCore lifecycle: {_nexus_lifecycle_err}")
    
    yield
    
    # إيقاف التشغيل
    logger.info("🛑 إيقاف خادم Sovereign AI...")
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
@app.get("/guardian/status")
async def guardian_status():
    """حالة نظام الحارس (قراءة فقط) — إحياء guardian/ عبر طبقة توافق"""
    return guardian_status_snapshot()


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
# نقاط API العامة (بدون مصادقة)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """الصفحة الرئيسية - تقديم واجهة SOVRA الأمامية"""
    frontend_index = FRONTEND_DIR / "index.html"
    if frontend_index.exists():
        return HTMLResponse(content=frontend_index.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Sovereign AI</h1><p>Frontend not found</p>")


@app.get("/health")
async def health_check():
    """
    فحص صحة النظام - يستخدمه مراقبو الخدمات (Kubernetes, Docker, etc.)
    """
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
    
    # استخراج الرد من النتيجة — R-614/S-9: رد حقيقي مبني على حالة النظام الحية
    reply = "تم استلام رسالتك. أنا الذكاء السيادي، جاهز لخدمتك."
    intent_name = ""
    if result.decision:
        action = result.decision.get('action', 'continue')
        source = result.decision.get('source', 'orchestrator')
        
        # فهم NexusCore: لغة + مشاعر + نية
        nexus_perception = (result.perception or {}).get("nexus", {})
        sentiment_label = nexus_perception.get("sentiment", {}).get("label", "")
        intent_name = nexus_perception.get("intent", {}).get("name", "")
        
        # R-614: محرك الردود السيادي — يبني الرد من حالة النظام الحية
        try:
            from sovereign_response import build_reply
            reply = build_reply(intent_name, message.text, result)
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
    
    return ChatResponse(
        reply=reply,
        status="ok" if result.success else "error",
        cycle_id=result.cycle_id,
        processing_time_ms=round(processing_time, 2),
        timestamp=start_time
    )


# ============================================================
# نقاط API للسيد (تتطلب مصادقة)
# ============================================================

def verify_api_key(api_key: str) -> bool:
    """التحقق من صحة مفتاح API للسيد"""
    return api_key == SOVEREIGN_API_KEY


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
        core = get_core()
        dynamic = get_dynamic_memory()
        store = get_store()
        
        return {
            "core": core.get_statistics() if core else None,
            "dynamic": dynamic.statistics() if dynamic else None,
            "store": store.get_statistics() if store else None,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
async def get_security_log(limit: int = Query(50, ge=1, le=500)):
    """آخر أحداث سجل الأمان"""
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


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    نقطة WebSocket للمحادثة المباشرة.
    
    الاتصال: `ws://localhost:8000/ws/{user_id}`
    
    إرسال رسالة: `{"text": "مرحباً"}`
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
            
            try:
                message_data = json.loads(data)
                text = message_data.get("text", "")
            except:
                text = data
            
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
                    "type": "reply",
                    "message": safety_block,
                    "blocked": True,
                    "cycle_id": "safety-block",
                    "timestamp": time.time()
                }))
                continue
            
            result = orchestrator.run_cycle(input_data)
            
            # إرسال الرد — R-612: رد حقيقي مبني على فهم النص
            reply = f"تم استلام رسالتك: '{text}'. أنا الذكاء السيادي."
            if result.decision:
                action = result.decision.get('action', 'continue')
                source = result.decision.get('source', 'orchestrator')
                nexus_perception = (result.perception or {}).get("nexus", {})
                intent_name = nexus_perception.get("intent", {}).get("name", "")
                sentiment_label = nexus_perception.get("sentiment", {}).get("label", "")
                
                if source == "nexus_intent" and intent_name:
                    intent_ar = {
                        "greet": "تحية", "help": "مساعدة", "status": "حالة النظام",
                        "analyze": "تحليل", "forecast": "تنبؤ", "alert": "تنبيه", "stop": "إيقاف",
                    }.get(intent_name, intent_name)
                    reply = f"فهمت — نيتك: {intent_ar}. القرار: {action}."
                elif source == "sovereign_controller":
                    reply = f"قرار المتحكم السيادي: {action}."
                else:
                    reply = f"تم تنفيذ القرار: {action}."
                
                if sentiment_label and sentiment_label != "neutral":
                    sentiment_ar = {"positive": "إيجابية", "negative": "سلبية"}.get(sentiment_label, sentiment_label)
                    reply += f" (مشاعرك: {sentiment_ar})"
            
            await manager.send_message(session_id, json.dumps({
                "type": "reply",
                "message": reply,
                "cycle_id": result.cycle_id,
                "timestamp": time.time()
            }))
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected: {user_id}")


# ============================================================
# نقاط API إضافية
# ============================================================

@app.get("/api-key")
async def get_api_key(master_key: str = Query(None, description="مفتاح السيد للتحقق")):
    """
    حالة مفتاح API للسيد (R-614/S-5).
    لا يُكشف المفتاح نفسه أبداً — يُعاد فقط بصمة المفتاح (SHA-256) ومصدره
    ومدى ثباته عبر إعادة التشغيل. المفتاح الحقيقي يُدار عبر متغير البيئة
    SOVEREIGN_KEY أو ملف data/key.secret (مستثنى من git، صلاحيات 0600).
    """
    if not master_key or master_key != SOVEREIGN_API_KEY:
        raise HTTPException(status_code=403, detail="غير مصرح: مطلوب مفتاح السيد")
    from config import SOVEREIGN_KEY_FINGERPRINT, DATA_DIR, IS_DEVELOPMENT
    secret_file = DATA_DIR / "key.secret"
    return {
        "fingerprint": SOVEREIGN_KEY_FINGERPRINT,
        "persistent": secret_file.exists() or bool(os.getenv("SOVEREIGN_KEY")),
        "source": "env" if os.getenv("SOVEREIGN_KEY") else ("key.secret" if secret_file.exists() else "ephemeral"),
        "development": IS_DEVELOPMENT,
        "note": "المفتاح لا يُكشف عبر API. أعد تعيينه عبر SOVEREIGN_KEY أو data/key.secret.",
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
    print(f"\n🔑 مفتاح API للسيد: {SOVEREIGN_API_KEY}")
    print(f"📖 التوثيق: http://localhost:8000/docs")
    print(f"🏥 فحص الصحة: http://localhost:8000/health")
    print(f"📊 حالة النظام: http://localhost:8000/status")
    print(f"🔌 WebSocket: ws://localhost:8000/ws/{'user_id'}")
    print("\n" + "=" * 80 + "\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
