# backend/app.py
# بوابة API للعقل السيادي – نقطة الدخول الرئيسية
# الإصدار: 1.0.0 | الحالة: جاهز للإنتاج

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional, List
import logging
import time
from datetime import datetime

# إعداد التسجيل (logging) لتتبع الأخطاء
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# استيراد المكونات الداخلية
from orchestrator import Orchestrator
from config import SOVEREIGN_KEY, BASE_DIR as CONFIG_BASE_DIR

# ============================================================
# 1. تهيئة التطبيق
# ============================================================

app = FastAPI(
    title="Sovereign AI - العقل السيادي",
    description="نظام ذكاء اصطناعي سيادي يطور نفسه فقط بإذن سيده",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# إضافة CORS للسماح بالاتصال من أي واجهة أمامية
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # للإنتاج، حدد النطاقات المسموحة
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 2. تهيئة المسارات والمجلدات
# ============================================================

# تحديد مجلد الواجهة
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"

# التأكد من وجود المجلدات الضرورية
for dir_path in [DATA_DIR, FRONTEND_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ربط الملفات الثابتة (CSS, JS)
if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

# ============================================================
# 3. تهيئة العقل التنفيذي (يتم مرة واحدة عند بدء التشغيل)
# ============================================================

logger.info("🚀 جاري تهيئة العقل السيادي...")
start_time = time.time()

orchestrator = Orchestrator()

init_time = time.time() - start_time
logger.info(f"✅ العقل السيادي جاهز بعد {init_time:.2f} ثانية")

# ============================================================
# 4. نماذج البيانات (Data Models)
# ============================================================

class Message(BaseModel):
    """نموذج رسالة المحادثة"""
    text: str = Field(..., min_length=1, max_length=5000, description="نص الرسالة")
    user_id: str = Field(default="anonymous", max_length=100, description="معرف المستخدم")
    is_sovereign: bool = Field(default=False, description="هل المرسل هو السيد؟")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "من أنت؟",
                "user_id": "user_123",
                "is_sovereign": False
            }
        }


class ApprovalRequest(BaseModel):
    """نموذج طلب الموافقة على اقتراح"""
    proposal_id: str = Field(..., description="معرف الاقتراح")
    approved: bool = Field(..., description="موافقة (true) أو رفض (false)")
    sovereign_key: str = Field(..., description="مفتاح السيد السري")


class ExperimentRequest(BaseModel):
    """نموذج تشغيل تجربة جديدة"""
    experiment_name: str = Field(..., description="اسم التجربة")
    sovereign_key: str = Field(..., description="مفتاح السيد السري")


class ChatResponse(BaseModel):
    """نموذج الرد على المحادثة"""
    reply: str
    status: str
    processing_time_ms: Optional[float] = None


# ============================================================
# 5. نقاط النهاية (Endpoints)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    الصفحة الرئيسية – واجهة المحادثة إن وُجدت، وإلا رسالة بسيطة.
    """
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>العقل السيادي</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #2c3e50; }
            .status { background: #27ae60; color: white; padding: 10px; border-radius: 5px; }
            code { background: #ecf0f1; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🧠 العقل السيادي</h1>
        <div class="status">✅ النظام يعمل</div>
        <p>أنشئ ملف <code>frontend/index.html</code> لواجهة محادثة كاملة.</p>
        <p>📖 <a href="/docs">توثيق API</a></p>
    </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """
    نقطة فحص صحة النظام (للخدمات مثل Railway)
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "core_loaded": orchestrator.core.is_loaded if hasattr(orchestrator, 'core') else False
    }


@app.get("/sovereign", response_class=HTMLResponse)
async def sovereign_panel():
    """
    صفحة لوحة السيد – إن وُجدت، وإلا رسالة بسيطة.
    """
    panel_file = FRONTEND_DIR / "sovereign_panel.html"
    if panel_file.exists():
        return FileResponse(panel_file)
    
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>لوحة السيد - العقل السيادي</title>
        <meta charset="utf-8">
        <style>
            body { font-family: monospace; max-width: 900px; margin: 30px auto; padding: 20px; background: #1e1e2e; color: #cdd6f4; }
            h1 { color: #89b4fa; }
            .proposal { background: #313244; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #89b4fa; }
            button { padding: 8px 16px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
            .approve { background: #a6e3a1; color: #1e1e2e; }
            .reject { background: #f38ba8; color: #1e1e2e; }
        </style>
    </head>
    <body>
        <h1>🔐 لوحة السيد</h1>
        <p>نظام الموافقة على اقتراحات التطوير الذاتي</p>
        <div id="proposals">جار التحميل...</div>
        <script>
            const SOVEREIGN_KEY = prompt("أدخل مفتاح السيد:");
            
            async function loadProposals() {
                const response = await fetch(`/proposals?sovereign_key=${SOVEREIGN_KEY}`);
                const data = await response.json();
                
                if (data.proposals && data.proposals.length > 0) {
                    document.getElementById('proposals').innerHTML = data.proposals.map(p => `
                        <div class="proposal">
                            <strong>ID:</strong> ${p.id}<br>
                            <strong>الوصف:</strong> ${p.description}<br>
                            <strong>السبب:</strong> ${p.reason || 'غير محدد'}<br>
                            <strong>التاريخ:</strong> ${p.timestamp}<br>
                            <button class="approve" onclick="decide('${p.id}', true)">✅ موافقة</button>
                            <button class="reject" onclick="decide('${p.id}', false)">❌ رفض</button>
                        </div>
                    `).join('');
                } else {
                    document.getElementById('proposals').innerHTML = '<p>📭 لا توجد اقتراحات معلقة حالياً</p>';
                }
            }
            
            async function decide(proposalId, approved) {
                const response = await fetch('/approve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proposal_id: proposalId, approved: approved, sovereign_key: SOVEREIGN_KEY })
                });
                const result = await response.json();
                alert(result.status === 'approved' ? '✅ تمت الموافقة' : '❌ تم الرفض');
                loadProposals();
            }
            
            loadProposals();
        </script>
    </body>
    </html>
    """)


@app.post("/chat", response_model=ChatResponse)
async def chat(message: Message):
    """
    نقطة المحادثة الرئيسية مع العقل السيادي.
    
    - **text**: نص الرسالة (مطلوب)
    - **user_id**: معرف المستخدم (افتراضي: anonymous)
    - **is_sovereign**: إذا كانت الرسالة من السيد (افتراضي: false)
    """
    start_time = time.time()
    
    try:
        # تسجيل الطلب
        logger.info(f"Chat request - user: {message.user_id}, sovereign: {message.is_sovereign}, text: {message.text[:100]}")
        
        # معالجة الرسالة
        reply = orchestrator.handle_message(
            message.text,
            message.user_id,
            message.is_sovereign
        )
        
        processing_time = (time.time() - start_time) * 1000  # بالمللي ثانية
        
        return ChatResponse(
            reply=reply,
            status="ok",
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            reply=f"⚠️ حدث خطأ داخلي: {str(e)}",
            status="error",
            processing_time_ms=round(processing_time, 2)
        )


@app.get("/proposals")
async def get_proposals(sovereign_key: str):
    """
    يحصل السيد على قائمة اقتراحات التطوير الذاتي المعلقة.
    يتطلب مفتاح السيد الصحيح.
    
    - **sovereign_key**: مفتاح السيد السري
    """
    if sovereign_key != SOVEREIGN_KEY:
        logger.warning(f"محاولة وصول غير مصرح بها إلى /proposals")
        raise HTTPException(status_code=403, detail="مفتاح السيد غير صحيح")
    
    proposals = orchestrator.get_pending_proposals()
    logger.info(f"تم جلب {len(proposals)} اقتراح معلق")
    
    return {"proposals": proposals, "count": len(proposals)}


@app.post("/approve")
async def approve_proposal(request: ApprovalRequest):
    """
    السيد يوافق أو يرفض اقتراح معيّن.
    
    - **proposal_id**: معرف الاقتراح
    - **approved**: true للموافقة، false للرفض
    - **sovereign_key**: مفتاح السيد السري
    """
    if request.sovereign_key != SOVEREIGN_KEY:
        logger.warning(f"محاولة موافقة غير مصرح بها على الاقتراح {request.proposal_id}")
        raise HTTPException(status_code=403, detail="مفتاح السيد غير صحيح")
    
    # تنفيذ الموافقة أو الرفض
    result = orchestrator.handle_sovereign_decision(request.proposal_id, request.approved)
    
    status = "approved" if request.approved else "rejected"
    logger.info(f"الاقتراح {request.proposal_id} تم {status}")
    
    return {
        "proposal_id": request.proposal_id,
        "status": status,
        "message": result
    }


@app.post("/experiment/run")
async def run_experiment(request: ExperimentRequest):
    """
    تشغيل تجربة جديدة بأمر من السيد.
    
    - **experiment_name**: اسم التجربة (يجب أن يكون موجوداً في مجلد experiments/)
    - **sovereign_key**: مفتاح السيد السري
    """
    if request.sovereign_key != SOVEREIGN_KEY:
        raise HTTPException(status_code=403, detail="مفتاح السيد غير صحيح")
    
    result = orchestrator.run_experiment(request.experiment_name, is_sovereign=True)
    
    return {
        "experiment": request.experiment_name,
        "result": result,
        "status": "completed"
    }


@app.get("/experiments/list")
async def list_experiments(sovereign_key: str):
    """
    عرض قائمة التجارب المتاحة.
    """
    if sovereign_key != SOVEREIGN_KEY:
        raise HTTPException(status_code=403, detail="مفتاح السيد غير صحيح")
    
    experiments = orchestrator.list_available_experiments()
    
    return {"experiments": experiments}


@app.get("/status")
async def system_status(sovereign_key: str = None):
    """
    عرض حالة النظام الكاملة (للسيد فقط إذا أعطى المفتاح)
    """
    is_authorized = (sovereign_key == SOVEREIGN_KEY)
    
    core_status = "loaded" if hasattr(orchestrator, 'core') and orchestrator.core.is_loaded else "not_loaded"
    
    return {
        "system": "Sovereign AI",
        "status": "running",
        "core": core_status,
        "authorized": is_authorized,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# 6. أحداث بدء وإيقاف التشغيل
# ============================================================

@app.on_event("startup")
async def startup_event():
    """تُنفذ عند بدء تشغيل الخادم"""
    logger.info("=" * 50)
    logger.info("🧠 العقل السيادي بدأ التشغيل")
    logger.info(f"📁 مجلد البيانات: {DATA_DIR}")
    logger.info(f"🌐 واجهة API: http://localhost:8000/docs")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """تُنفذ عند إيقاف الخادم"""
    logger.info("🛑 العقل السيادي تم إيقافه")


# ============================================================
# 7. تشغيل مباشر (للتطوير المحلي)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
