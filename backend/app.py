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
    status, BackgroundTasks, Query, Header, File, UploadFile,
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
    # R-617: لا يُسجّل المفتاح نفسه أبدًا — فقط بصمته (أول 8 أحرف من sha256)
    _key_fingerprint = hashlib.sha256(SOVEREIGN_API_KEY.encode()).hexdigest()[:8]
    logger.info(f"🔑 مفتاح API للسيد (بصمة فقط): {_key_fingerprint}...")
    logger.info(f"📖 التوثيق: http://localhost:8000/docs")
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
    logger.info(f"⏱️ المجدول: {app.state.scheduler.reason}")
    
    yield
    
    # إيقاف التشغيل
    logger.info("🛑 إيقاف خادم Sovereign AI...")
    await app.state.scheduler.stop()
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
@app.get("/ledger/verify")
async def ledger_verify():
    """
    تقرير التحقق من اليدجر السيادي:
    - عدد الأحداث المُتحقَّق منها بالمفتاح (KeyRing)
    - عدد المراسي (Merkle Anchors)
    - عدد الأحداث المحمية بمرساة
    - عدد الأحداث المجهولة/الفاشلة
    """
    from backend.sovereign.ledger import LedgerAnchor
    from backend.sovereign.keys import KeyRing, SignatureVerifier

    # تحميل KeyRing
    keyring = KeyRing()
    keyring.load_from_disk()

    # تحميل اليدجر والمراسي
    anchor = LedgerAnchor()
    lines = anchor.read_ledger_lines()

    # تحليل كل الأحداث (تحقق من التوقيع)
    verifier = SignatureVerifier(keyring)

    # عدد الأحداث المُغطاة بالمراسي
    anchors_list = anchor.list_anchors()
    anchored_events = set()
    for a in anchors_list:
        for i in range(a["batch_start"], a["batch_end"] + 1):
            anchored_events.add(i)

    # تصنيف كل حدث
    stats = {
        "total_events": len(lines),
        "verified_with_key": 0,      # موقّع بمفتاح معروف وصالح
        "anchored_events": len(anchored_events),  # داخل مرساة
        "unverifiable": 0,          # لا نعرف (مفتاح فُقد أو LEGACY)
        "invalid": 0,               # مزوّر (التوقيع لا يطابق)
        "legacy_pre_keyring": 0,     # أحداث قديمة بدون key_id
    }

    import json as _json
    for i, line in enumerate(lines):
        try:
            event = _json.loads(line)
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

    # التحقق من كل المراسي
    # R-642/R-643: يُميّز التغطية الموثوقة تشخريًًا (trusted) من الاسمية
    anchors_verification = anchor.verify_all_anchors(keyring=keyring)

    return {
        "ledger_summary": stats,
        # R-647: توافق قديم — anchors["verified"] بمعناه السابق (فحص الجذر)
        # + حقول الثقة الجديدة (root_verified, trusted, details)
        "anchors": {
            "total": anchors_verification["total_anchors"],
            "verified": anchors_verification["root_verified_count"],  # توافق قديم (فحص الجذر)
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
            (len(anchored_events) / len(lines)) * 100, 2
        ) if lines else 0.0,
        "trusted_coverage_pct": round(
            anchors_verification["trusted_coverage"] * 100, 2
        ),
        "nominal_coverage_pct": round(
            anchors_verification["nominal_coverage"] * 100, 2
        ),
        "trusted_events_count": anchors_verification["trusted_events_count"],
        "total_events": anchors_verification["total_events"],
        "timestamp": time.time(),
    }


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


@app.get("/agent/ledger")
async def agent_ledger_report():
    """
    تقرير سجل أفعال الوكيل التقني (المرحلة 6 من ROADMAP_V2).
    يُوثّق كل تعديل قام به الوكيل — لا أفعال خفية.
    """
    from backend.sovereign.agent_ledger import AgentLedger

    ledger = AgentLedger()
    return ledger.full_report()


@app.get("/sovereignty/score")
async def sovereignty_score():
    """
    درجة السيادة (Sovereignty Score) — المرحلة 5 من ROADMAP_V2.
    يقيس المسافة بين 'يعمل' و 'سيادي' برقم واحد (0-100).

    R-680: يُعيد جدول المؤشرات الأولية (primitives) + المقياس
    المُركّب (composite) في آخر سطر مع علامة "قابل للجدل".
    """
    return _sovereignty_score_payload()


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
    enabled = bool(_config.OLLAMA_ENABLED and _config.OLLAMA_MODEL)
    outcome = _brain_client.last_outcome()
    if not enabled:
        return {"brain": "disabled", "enabled": False,
                "reply_source": "templates", "last_call": outcome}
    protocol = getattr(_config, "OLLAMA_PROTOCOL", "ollama")
    if protocol not in ("ollama", "openai"):
        protocol = "invalid"  # لا صدى للقيمة الخام (قد تحمل سرًا)
    # المرصود: مصدر آخر رد فعلي — لا ادعاء نجاح قبل أول استدلال ناجح
    if outcome.get("result") == "ok":
        reply_source = "model"
    elif outcome.get("result") == "none":
        reply_source = "unverified"
    else:
        reply_source = "templates-fallback"
    raw = urlsplit(str(_config.OLLAMA_BASE_URL))
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
        "model": _config.OLLAMA_MODEL,
        "base_url": safe_base,
        "timeout_seconds": _config.OLLAMA_TIMEOUT_SECONDS,
        "last_call": outcome,
    }


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
        return get_registry().invoke(request.tool, caller="owner",
                                      inputs=request.inputs)
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
        description="حالة القرص السحابي Supabase (نفس منطق /disk/status)",
        inputs={},
        outputs="cloud_disk/enabled/…",
        handler=_disk_status_payload,
    ))
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
        description="بحث ويب حي (searxng محلي أو tavily) — نتائج مستشهدة بمصادر",
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
        name="research.run",
        description="المنسّق: هدف → بحث ← قراءة مصادر ← استخراج ← استدلال ← تقرير مستشهد",
        inputs={"goal": "هدف البحث"}, outputs="report/sources/facts/steps",
        handler=_tool_research_run))

    registry.register(ToolSpec(
        name="sovereignty.score",
        description="تقرير درجة السيادة الكامل (نفس منطق /sovereignty/score)",
        inputs={},
        outputs="roadmap_v2/total_score/axes/primitives/composite",
        handler=_sovereignty_score_payload,
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


async def _compose_chat_reply(text: str, result, orchestrator, default: str) -> str:
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
            reply = await asyncio.to_thread(
                build_reply, intent_name, text, result, orchestrator=orchestrator
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
    
    # استخراج الرد من النتيجة — R-614/S-9: رد حقيقي مبني على حالة النظام الحية
    # R-715: منطق التركيب نُقل كما هو إلى _compose_chat_reply ليشترك فيه /chat و WebSocket
    reply = await _compose_chat_reply(
        message.text, result, orchestrator,
        default="تم استلام رسالتك. أنا الذكاء السيادي، جاهز لخدمتك.",
    )
    
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


# R-729 (البند ٣.١): تسجيل الأدوات الحقيقية — في نهاية الملف لأن دوال الحمولة
# المشتركة (آخرها _memory_stats_payload) معرّفة قبل هذا السطر.
_register_real_tools()

# R-738: بوابة MCP — تسجيل ديناميكي لأدوات خوادم MCP إن فعلها المالك
# (MCP_ENABLED) — فشل خادم يُسجل تحذيرًا صادقًا ويُتخطى (لا اتصال ضمني)
try:
    import mcp_gateway
    mcp_gateway.sync_into_registry(get_registry())
except Exception as _mcp_exc:  # لا يكسر الإقلاع أبدًا — تحذير صادق فقط
    logging.getLogger("sovereign.mcp").warning(
        "R-738 [MCP]: تعذر تسجيل أدوات MCP (%s) — تُعاد المحاولة عند "
        "إعادة الإقلاع", type(_mcp_exc).__name__)
