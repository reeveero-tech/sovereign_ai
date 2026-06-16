"""
NexusCore — FastAPI Router
يوفر REST API لجميع مكونات NexusCore.
"""
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger("nexus.api_gateway.router")

router = APIRouter(prefix="/nexus", tags=["NexusCore"])


# ── Models ────────────────────────────────────
class AnalyzeTextRequest(BaseModel):
    text: str
    tasks: List[str] = ["sentiment", "intent", "language"]


class ForecastRequest(BaseModel):
    metric: str
    horizon_hours: int = 24


class IngestRequest(BaseModel):
    source: str
    data: Any
    metadata: Optional[Dict] = None


class BudgetItem(BaseModel):
    category: str
    allocated: float
    spent: float
    currency: str = "USD"


# ── Lazy imports ─────────────────────────────
_nexus_engine = None


def get_nexus():
    global _nexus_engine
    if _nexus_engine is None:
        from nexus.core.engine import get_engine
        _nexus_engine = get_engine()
    return _nexus_engine


# ── Endpoints ─────────────────────────────────
@router.get("/status")
def get_status():
    """حالة محرك NexusCore"""
    engine = get_nexus()
    return engine.get_status()


@router.post("/analyze/text")
def analyze_text(req: AnalyzeTextRequest):
    """تحليل نص (مشاعر، نية، لغة)"""
    results: Dict[str, Any] = {}
    if "sentiment" in req.tasks:
        from nexus.data_pipeline.sentiment_analyzer import SentimentAnalyzer
        sa = SentimentAnalyzer()
        r  = sa.analyze(req.text)
        results["sentiment"] = {
            "label": r.label, "score": r.score,
            "confidence": r.confidence, "language": r.language,
        }
    if "intent" in req.tasks:
        from nexus.nlp.intent_recognizer import IntentRecognizer
        ir = IntentRecognizer()
        intent = ir.recognize(req.text)
        results["intent"] = {
            "name": intent.name if intent else None,
            "confidence": intent.confidence if intent else 0.0,
        }
    if "language" in req.tasks:
        from nexus.nlp.language_detector import LanguageDetector
        ld = LanguageDetector()
        lang = ld.detect(req.text)
        results["language"] = {"code": lang.language, "confidence": lang.confidence}
    return {"text": req.text[:200], "results": results}


@router.post("/ingest")
def ingest_data(req: IngestRequest):
    """استيعاب بيانات جديدة"""
    from nexus.data_pipeline.collector import DataCollector
    dc = DataCollector()
    record = dc.ingest(req.source, req.data, req.metadata)
    return {"status": "ingested", "source": record.source,
            "timestamp": record.timestamp}


@router.get("/health")
def health():
    """فحص صحة NexusCore"""
    return {
        "status": "healthy",
        "nexus_version": "1.0.0",
        "timestamp": time.time(),
    }


@router.post("/budget/analyze")
def analyze_budget(items: List[BudgetItem]):
    """تحليل الميزانية"""
    from nexus.automation.budget_analyzer import BudgetAnalyzer
    ba = BudgetAnalyzer()
    for item in items:
        ba.add_item(item.category, item.allocated, item.spent, item.currency)
    report = ba.generate_report()
    return {
        "total_allocated": report.total_allocated,
        "total_spent": report.total_spent,
        "utilization_pct": round(report.utilization_rate * 100, 1),
        "over_budget": report.over_budget_items,
        "recommendations": report.recommendations,
        "breakdown": ba.get_breakdown(),
    }


@router.get("/recommendations")
def get_recommendations():
    """الحصول على التوصيات المعلقة"""
    return {"recommendations": [], "note": "Register engine first"}


class NexusRouter:
    """مغلّف للـ router"""
    router = router
