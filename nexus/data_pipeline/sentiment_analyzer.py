"""
NexusCore — محلل المشاعر
يحلل المشاعر في النصوص العربية والإنجليزية (نهج قاموسي بدون نماذج خارجية).
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.data_pipeline.sentiment")

_POS_AR = {"ممتاز","رائع","جميل","مذهل","نجاح","سعيد","جيد","مفيد","إيجابي",
            "تقدم","أفضل","حل","فرصة","نمو","متميز","قوي","إبداع","ابتكار"}
_NEG_AR = {"سيء","فشل","مشكلة","خطأ","ضعيف","سلبي","خسارة","صعب",
            "عقبة","تراجع","أزمة","رفض","خطر","ضار","تعطل","انهيار"}
_POS_EN = {"good","great","excellent","amazing","positive","success","happy",
            "helpful","progress","better","solution","opportunity","strong","innovative"}
_NEG_EN = {"bad","fail","failure","problem","error","weak","negative","loss",
            "difficult","obstacle","crisis","risk","reject","broken","crash"}


@dataclass
class SentimentResult:
    text: str
    score: float        # -1.0 … +1.0
    label: str          # positive / negative / neutral
    confidence: float
    positive_hits: int
    negative_hits: int
    language: str


class SentimentAnalyzer:
    """محلل مشاعر النصوص (عربي + إنجليزي)"""

    def __init__(self, extra_positive: Optional[List[str]] = None,
                 extra_negative: Optional[List[str]] = None):
        self.positive = _POS_AR | _POS_EN
        self.negative = _NEG_AR | _NEG_EN
        if extra_positive:
            self.positive.update(w.lower() for w in extra_positive)
        if extra_negative:
            self.negative.update(w.lower() for w in extra_negative)
        logger.info("💬 SentimentAnalyzer initialized")

    def analyze(self, text: str) -> SentimentResult:
        if not text or not text.strip():
            return SentimentResult(text=text, score=0.0, label="neutral",
                                   confidence=0.0, positive_hits=0,
                                   negative_hits=0, language="unknown")
        tokens = re.findall(r'\w+', text.lower())
        lang   = self._detect_language(text)
        pos = sum(1 for t in tokens if t in self.positive)
        neg = sum(1 for t in tokens if t in self.negative)
        total = pos + neg
        if total == 0:
            score, confidence = 0.0, 0.1
        else:
            score      = (pos - neg) / total
            confidence = min(1.0, total / max(len(tokens), 1) * 5)
        label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
        return SentimentResult(text=text[:200], score=round(score, 3),
                               label=label, confidence=round(confidence, 3),
                               positive_hits=pos, negative_hits=neg, language=lang)

    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        return [self.analyze(t) for t in texts]

    def _detect_language(self, text: str) -> str:
        ar = len(re.findall(r'[\u0600-\u06FF]', text))
        en = len(re.findall(r'[a-zA-Z]', text))
        return "ar" if ar > en else "en" if en > ar else "mixed"

    def summary(self, results: List[SentimentResult]) -> Dict:
        if not results:
            return {}
        avg    = sum(r.score for r in results) / len(results)
        labels = {}
        for r in results:
            labels[r.label] = labels.get(r.label, 0) + 1
        return {
            "total": len(results), "avg_score": round(avg, 3),
            "distribution": labels,
            "overall": "positive" if avg > 0.1 else "negative" if avg < -0.1 else "neutral",
        }
