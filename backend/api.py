# backend/api.py
# 🌐 Sovereign AI API - الطبقة الوسيطة بين الواجهة والذكاء السيادي
# الإصدار: 3.0.0 - نسخة Router جاهزة للدمج مع app.py

"""
هذا الملف هو الجسر الحي بين الواجهة السيادية والذكاء السيادي.
تم تحويله إلى APIRouter ليدمج بسهولة مع app.py الرئيسي.

المسارات تصبح تحت /api:
- /api/run       → تشغيل دورة سيادية
- /api/reset     → إعادة تهيئة النظام
- /api/state     → حالة النظام
- /api/history   → سجل الأحداث
- /api/event     → إرسال حدث مخصص
- /api/components→ حالة المكونات
- /api/ws        → WebSocket (قناة الاتصال الحي)
- /api/docs      → توثيق API (Swagger)
- /api/redoc     → توثيق API (ReDoc)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import time
import uuid
import asyncio
from datetime import datetime

# استيراد Orchestrator
try:
    from orchestrator import get_orchestrator, OrchestratorMode
except ImportError:
    import sys
    sys.path.append('.')
    from orchestrator import get_orchestrator, OrchestratorMode

# طبقة الأمان السيادية (R-608)
try:
    from safety import SafetyGuard
    _ws_safety = SafetyGuard()
except Exception:
    _ws_safety = None

import logging
logger = logging.getLogger("SovereignAPI")

# ============================================================
# 1. إنشاء Router (بدلاً من FastAPI application)
# ============================================================

api_router = APIRouter(
    prefix="/api",
    tags=["Sovereign AI API"],
    responses={404: {"description": "Not found"}}
)

# ============================================================
# 2. نماذج البيانات (Data Models)
# ============================================================

class RunCycleRequest(BaseModel):
    """طلب تشغيل دورة سيادية"""
    event_type: str = "manual_run"
    payload: Dict[str, Any] = {}
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "manual_run",
                "payload": {"source": "user", "command": "status"}
            }
        }

class ResetRequest(BaseModel):
    """طلب إعادة تهيئة"""
    preserve_data: bool = False
    component: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "preserve_data": False,
                "component": None
            }
        }

class EventRequest(BaseModel):
    """طلب إرسال حدث"""
    type: str
    payload: Dict[str, Any] = {}
    source: str = "api"
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "user_action",
                "payload": {"action": "click", "target": "reset_button"},
                "source": "web_ui"
            }
        }

# ============================================================
# 3. مدير اتصالات WebSocket
# ============================================================

class ConnectionManager:
    """إدارة اتصالات WebSocket النشطة"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        await websocket.accept()
        if client_id is None:
            client_id = str(uuid.uuid4())[:8]
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = {
            "connected_at": time.time(),
            "last_activity": time.time(),
            "messages_sent": 0,
            "messages_received": 0
        }
        logger.info(f"WebSocket متصل: {client_id}")
        return client_id
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.connection_info:
            del self.connection_info[client_id]
        logger.info(f"WebSocket مفصول: {client_id}")
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
                if client_id in self.connection_info:
                    self.connection_info[client_id]["messages_sent"] += 1
                    self.connection_info[client_id]["last_activity"] = time.time()
            except Exception as e:
                logger.error(f"فشل إرسال رسالة إلى {client_id}: {e}")
    
    async def broadcast(self, message: Dict[str, Any], exclude: List[str] = None):
        if exclude is None:
            exclude = []
        for client_id, connection in self.active_connections.items():
            if client_id not in exclude:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"فشل broadcast إلى {client_id}: {e}")
    
    def get_connections_count(self) -> int:
        return len(self.active_connections)
    
    def get_connection_info(self) -> Dict:
        return {
            client_id: {
                "connected_at": info["connected_at"],
                "last_activity": info["last_activity"],
                "messages_sent": info["messages_sent"],
                "messages_received": info["messages_received"]
            }
            for client_id, info in self.connection_info.items()
        }

# ============================================================
# 4. تهيئة Orchestrator ومدير الاتصالات
# ============================================================

orchestrator = None
manager = ConnectionManager()

def get_orch():
    """الحصول على Orchestrator (مع lazy initialization)"""
    global orchestrator
    if orchestrator is None:
        orchestrator = get_orchestrator()
    return orchestrator

# ============================================================
# 5. نقاط API (REST)
# ============================================================

@api_router.get("/health")
async def health_check():
    """
    فحص صحة API.
    
    Returns:
        حالة API و Orchestrator واتصالات WebSocket
    """
    orch = get_orch()
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "3.0.0",
        "orchestrator_status": orch._active if hasattr(orch, '_active') else True,
        "websocket_connections": manager.get_connections_count()
    }


@api_router.post("/run", response_model=Dict[str, Any])
async def run_cycle(request: RunCycleRequest = None):
    """
    تشغيل دورة سيادية كاملة.
    
    - بدون بيانات: `/api/run` (دورة يدوية)
    - مع حدث مخصص: `/api/run` مع `event_type` و `payload`
    
    Returns:
        نتيجة الدورة (cycle_id, success, duration, decision)
    """
    orch = get_orch()
    
    input_data = {
        "type": request.event_type if request else "manual_run",
        "source": "api",
        "timestamp": time.time(),
        "payload": request.payload if request else {}
    }
    
    try:
        result = orch.run_cycle(input_data)
        
        # إرسال broadcast للمشتركين
        await manager.broadcast({
            "type": "cycle_completed",
            "payload": {
                "cycle_id": result.cycle_id,
                "success": result.success,
                "duration": result.duration
            }
        })
        
        return {
            "status": "success",
            "cycle_id": result.cycle_id,
            "success": result.success,
            "duration": result.duration,
            "decision": result.decision,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"خطأ في تشغيل الدورة: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/reset")
async def reset_system(request: ResetRequest = None):
    """
    إعادة تهيئة النظام بالكامل أو مكون معين.
    
    - الكل: `/api/reset`
    - مكون محدد: `/api/reset` مع `component` (مثل: memory_core, quantum_controller)
    - الحفاظ على البيانات: `/api/reset` مع `preserve_data=true`
    
    Returns:
        نتيجة إعادة التهيئة
    """
    orch = get_orch()
    
    try:
        if request and request.component:
            success = orch.reset_component(request.component)
            message = f"تم إعادة تهيئة {request.component}" if success else f"فشل إعادة تهيئة {request.component}"
        else:
            preserve = request.preserve_data if request else False
            orch.reset_all(preserve_session=preserve)
            message = "تم إعادة تهيئة النظام بالكامل"
            success = True
        
        # إرسال broadcast للمشتركين
        await manager.broadcast({
            "type": "system_reset",
            "payload": {"success": success, "message": message}
        })
        
        return {
            "status": "success",
            "success": success,
            "message": message,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"خطأ في إعادة التهيئة: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/state")
async def get_system_state():
    """
    الحصول على حالة النظام الكاملة.
    
    تشمل:
    - حالة Orchestrator (الجلسة، الوضع، الإحصائيات)
    - صحة المكونات
    - معلومات الأداء
    
    Returns:
        حالة النظام الكاملة
    """
    orch = get_orch()
    
    try:
        state = orch.get_status()
        return {
            "status": "success",
            "data": state,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"خطأ في جلب الحالة: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/history")
async def get_system_history(limit: int = 100, level: str = None):
    """
    الحصول على سجل أحداث النظام.
    
    Parameters:
        limit: عدد الأحداث (max 500)
        level: تصفية حسب المستوى (info, warning, error)
    
    Returns:
        قائمة الأحداث
    """
    orch = get_orch()
    
    try:
        history = orch.get_history(limit=min(limit, 500))
        
        if level:
            history = [h for h in history if h.get('level') == level]
        
        return {
            "status": "success",
            "data": history,
            "count": len(history),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"خطأ في جلب السجل: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/event")
async def send_event(request: EventRequest):
    """
    إرسال حدث مخصص إلى الذكاء السيادي.
    
    يمكن استخدامه لأي نوع من الأحداث:
    - تفاعل مستخدم (نقر، إدخال)
    - إشارة من نظام خارجي
    - أمر مباشر
    
    Returns:
        نتيجة معالجة الحدث
    """
    orch = get_orch()
    
    input_data = {
        "type": request.type,
        "source": request.source,
        "timestamp": time.time(),
        **request.payload
    }
    
    try:
        result = orch.run_cycle(input_data)
        
        return {
            "status": "success",
            "cycle_id": result.cycle_id,
            "success": result.success,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"خطأ في معالجة الحدث: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/components")
async def get_components_status():
    """
    الحصول على حالة جميع المكونات.
    
    Returns:
        حالة كل مكون (healthy/degraded/unhealthy)
    """
    orch = get_orch()
    
    try:
        components = orch.get_component_health()
        return {
            "status": "success",
            "data": components,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"خطأ في جلب حالة المكونات: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/connections")
async def get_ws_connections():
    """
    الحصول على معلومات اتصالات WebSocket النشطة.
    
    Returns:
        عدد الاتصالات ومعلوماتها
    """
    return {
        "status": "success",
        "connections_count": manager.get_connections_count(),
        "connections": manager.get_connection_info(),
        "timestamp": time.time()
    }


@api_router.get("/mode")
async def get_current_mode():
    """
    الحصول على وضع التشغيل الحالي للـ Orchestrator.
    
    Returns:
        وضع التشغيل (normal, safe, recovery, emergency, debug, silent)
    """
    orch = get_orch()
    
    return {
        "status": "success",
        "mode": orch.config.mode if hasattr(orch, 'config') else "normal",
        "timestamp": time.time()
    }


@api_router.post("/mode/{mode}")
async def set_operation_mode(mode: str):
    """
    تغيير وضع التشغيل.
    
    Parameters:
        mode: normal, safe, recovery, emergency, debug, silent
    
    Returns:
        نتيجة تغيير الوضع
    """
    orch = get_orch()
    
    valid_modes = ["normal", "safe", "recovery", "emergency", "debug", "silent"]
    
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"وضع غير صالح. الأوضاع المتاحة: {', '.join(valid_modes)}")
    
    try:
        success = orch.set_mode(mode)
        
        # إرسال broadcast للمشتركين
        await manager.broadcast({
            "type": "mode_changed",
            "payload": {"mode": mode, "success": success}
        })
        
        return {
            "status": "success" if success else "failed",
            "mode": mode,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"خطأ في تغيير الوضع: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 6. WebSocket - القناة الحيوية
# ============================================================

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket - قناة الاتصال الحي.
    
    أنواع الرسائل المستقبلة:
    - `sir_command`: أمر من السيد
    - `chat_message`: رسالة حوار
    - `run_cycle`: تشغيل دورة
    - `get_state`: طلب الحالة
    - `ping`: نبض القلب
    
    أنواع الرسائل المرسلة:
    - `welcome`: ترحيب
    - `ai_message`: رد الذكاء
    - `command_response`: نتيجة أمر السيد
    - `state_update`: تحديث الحالة
    - `pong`: رد على ping
    - `error`: خطأ
    """
    client_id = await manager.connect(websocket)
    
    # رسالة ترحيب
    await manager.send_message(client_id, {
        "type": "welcome",
        "message": "مرحباً أيها السيد. قناة الاتصال الحي جاهزة.",
        "client_id": client_id,
        "timestamp": time.time()
    })
    
    # إشعار للمشتركين الآخرين
    await manager.broadcast({
        "type": "connection_status",
        "payload": {
            "client_id": client_id, 
            "status": "connected", 
            "connections": manager.get_connections_count()
        }
    }, exclude=[client_id])
    
    orch = get_orch()
    
    try:
        while True:
            # استقبال رسالة
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")
                payload = message.get("payload", {})
                
                # تحديث إحصائيات الاستقبال
                if client_id in manager.connection_info:
                    manager.connection_info[client_id]["messages_received"] += 1
                    manager.connection_info[client_id]["last_activity"] = time.time()
                
                # ================================================
                # معالجة: أمر من السيد
                # ================================================
                if msg_type == "sir_command":
                    command_text = payload.get("text", "")
                    
                    # فحص الأمان (R-608): حتى السيد تُفحص الأوامر الممنوعة تماماً
                    if _ws_safety is not None:
                        safe_text, needs_approval, reason = _ws_safety.check_input(command_text, is_sovereign=True)
                        if needs_approval:
                            await manager.send_message(client_id, {
                                "type": "command_response",
                                "payload": {
                                    "command": command_text,
                                    "success": False,
                                    "cycle_id": "safety-block",
                                    "decision": {"action": "blocked", "reason": reason, "message": safe_text}
                                },
                                "timestamp": time.time()
                            })
                            logger.warning(f"أمر محظور من السيد [{client_id}]: {command_text[:50]} — {reason}")
                            continue
                    
                    input_data = {
                        "type": "sir_command",
                        "source": "websocket",
                        "client_id": client_id,
                        "command": command_text,
                        "timestamp": time.time()
                    }
                    
                    result = orch.run_cycle(input_data)
                    
                    await manager.send_message(client_id, {
                        "type": "command_response",
                        "payload": {
                            "command": command_text,
                            "success": result.success,
                            "cycle_id": result.cycle_id,
                            "decision": result.decision
                        },
                        "timestamp": time.time()
                    })
                    
                    logger.info(f"أمر من السيد [{client_id}]: {command_text[:50]}")
                
                # ================================================
                # معالجة: رسالة حوار
                # ================================================
                elif msg_type == "chat_message":
                    text = payload.get("text", "")
                    
                    # فحص الأمان (R-608): فحص رسالة الحوار قبل المعالجة
                    if _ws_safety is not None:
                        safe_text, needs_approval, reason = _ws_safety.check_input(text, is_sovereign=False)
                        if needs_approval:
                            await manager.send_message(client_id, {
                                "type": "ai_message",
                                "payload": {
                                    "text": safe_text,
                                    "cycle_id": "safety-block",
                                    "blocked": True,
                                    "reason": reason
                                },
                                "timestamp": time.time()
                            })
                            logger.warning(f"رسالة محظورة من [{client_id}]: {text[:50]} — {reason}")
                            continue
                    
                    input_data = {
                        "type": "chat_message",
                        "source": "websocket",
                        "client_id": client_id,
                        "text": text,
                        "timestamp": time.time()
                    }
                    
                    result = orch.run_cycle(input_data)
                    
                    # توليد رد الذكاء
                    reply = "تم استلام رسالتك. الذكاء السيادي يعالج طلبك."
                    if result.success and result.decision:
                        reply = f"تم تنفيذ القرار: {result.decision.get('action', 'continue')}"
                    
                    await manager.send_message(client_id, {
                        "type": "ai_message",
                        "payload": {
                            "text": reply,
                            "cycle_id": result.cycle_id
                        },
                        "timestamp": time.time()
                    })
                    
                    logger.info(f"رسالة حوار من [{client_id}]: {text[:50]}")
                
                # ================================================
                # معالجة: تشغيل دورة
                # ================================================
                elif msg_type == "run_cycle":
                    result = orch.run_cycle({
                        "type": "manual_cycle",
                        "source": "websocket",
                        "client_id": client_id,
                        "timestamp": time.time()
                    })
                    
                    await manager.send_message(client_id, {
                        "type": "state_update",
                        "payload": {
                            "cycle_id": result.cycle_id,
                            "success": result.success,
                            "duration": result.duration,
                            "decision": result.decision
                        },
                        "timestamp": time.time()
                    })
                    
                    # تحديث جميع العملاء
                    await manager.broadcast({
                        "type": "state_update",
                        "payload": {"cycles_incremented": True, "cycle_id": result.cycle_id}
                    }, exclude=[client_id])
                
                # ================================================
                # معالجة: طلب الحالة
                # ================================================
                elif msg_type == "get_state":
                    state = orch.get_status()
                    await manager.send_message(client_id, {
                        "type": "state_response",
                        "payload": state,
                        "timestamp": time.time()
                    })
                
                # ================================================
                # معالجة: نبض القلب (Ping)
                # ================================================
                elif msg_type == "ping":
                    await manager.send_message(client_id, {
                        "type": "pong",
                        "timestamp": time.time()
                    })
                
                # ================================================
                # معالجة: أمر مخصص
                # ================================================
                else:
                    result = orch.run_cycle({
                        "type": msg_type,
                        "source": "websocket",
                        "client_id": client_id,
                        "payload": payload,
                        "timestamp": time.time()
                    })
                    
                    await manager.send_message(client_id, {
                        "type": "response",
                        "payload": {"success": result.success, "cycle_id": result.cycle_id},
                        "timestamp": time.time()
                    })
                
            except json.JSONDecodeError as e:
                await manager.send_message(client_id, {
                    "type": "error",
                    "payload": {"message": "خطأ في تنسيق JSON", "error": str(e)},
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"خطأ في معالجة رسالة WebSocket: {e}")
                await manager.send_message(client_id, {
                    "type": "error",
                    "payload": {"message": "خطأ داخلي", "error": str(e)},
                    "timestamp": time.time()
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في WebSocket: {e}")
    finally:
        manager.disconnect(client_id)
        await manager.broadcast({
            "type": "connection_status",
            "payload": {
                "client_id": client_id, 
                "status": "disconnected", 
                "connections": manager.get_connections_count()
            }
        })


# ============================================================
# 7. دوال مساعدة للتكامل مع app.py
# ============================================================

def get_api_router() -> APIRouter:
    """
    إرجاع الـ Router للتكامل مع app.py.
    
    الاستخدام في app.py:
        from api import get_api_router
        app.include_router(get_api_router())
    """
    return api_router


# ============================================================
# 8. التشغيل المباشر (للاختبار فقط)
# ============================================================

if __name__ == "__main__":
    # هذا الجزء يُستخدم فقط للاختبار المنفرد
    # في الإنتاج، يتم استيراد الـ Router إلى app.py
    import uvicorn
    from fastapi import FastAPI
    
    test_app = FastAPI(title="Sovereign AI API (Test)")
    test_app.include_router(api_router)
    
    print("\n" + "=" * 60)
    print("🌐 Sovereign AI API - وضع الاختبار المنفرد")
    print("=" * 60)
    print(f"📖 API Docs: http://localhost:8001/api/docs")
    print(f"🔌 WebSocket: ws://localhost:8001/api/ws")
    print(f"🏥 Health: http://localhost:8001/api/health")
    print("⚠️ للتكامل مع الواجهة الكاملة، استخدم app.py")
    print("=" * 60 + "\n")
    
    uvicorn.run(test_app, host="0.0.0.0", port=8001, log_level="info")
