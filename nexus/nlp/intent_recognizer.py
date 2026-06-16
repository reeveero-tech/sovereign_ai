"""
NexusCore — كاشف النية
يتعرف على النية من الجمل (نهج قاموسي قابل للتوسيع).
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("nexus.nlp.intent")


@dataclass
class Intent:
    name: str
    confidence: float
    matched_patterns: List[str]
    entities: Dict = field(default_factory=dict)


DEFAULT_INTENTS = {
    "greet":       ["مرحبا", "أهلا", "السلام", "hello", "hi", "hey"],
    "help":        ["مساعدة", "help", "أحتاج", "need", "كيف", "how"],
    "status":      ["حالة", "status", "تقرير", "report", "نتائج", "results"],
    "analyze":     ["حلل", "analyze", "تحليل", "analysis", "افحص", "check"],
    "forecast":    ["توقع", "forecast", "تنبؤ", "predict", "مستقبل", "future"],
    "alert":       ["تنبيه", "alert", "خطر", "danger", "طارئ", "emergency"],
    "stop":        ["إيقاف", "stop", "وقف", "halt", "إلغاء", "cancel"],
}


class IntentRecognizer:
    """يتعرف على نية المستخدم من الجمل الطبيعية"""

    def __init__(self):
        self._intents: Dict[str, List[str]] = dict(DEFAULT_INTENTS)
        logger.info("🎯 IntentRecognizer initialized")

    def add_intent(self, name: str, patterns: List[str]) -> None:
        self._intents[name] = patterns

    def recognize(self, text: str) -> Optional[Intent]:
        tokens = set(re.findall(r'\w+', text.lower()))
        best: Optional[Tuple[str, float, List[str]]] = None
        for intent_name, patterns in self._intents.items():
            matched = [p for p in patterns if p.lower() in tokens or p.lower() in text.lower()]
            if matched:
                conf = min(1.0, len(matched) / max(len(patterns) * 0.3, 1))
                if best is None or conf > best[1]:
                    best = (intent_name, conf, matched)
        if best:
            return Intent(name=best[0], confidence=round(best[1], 3),
                          matched_patterns=best[2])
        return None

    def recognize_all(self, text: str) -> List[Intent]:
        tokens = set(re.findall(r'\w+', text.lower()))
        intents: List[Intent] = []
        for name, patterns in self._intents.items():
            matched = [p for p in patterns if p.lower() in tokens or p.lower() in text.lower()]
            if matched:
                conf = min(1.0, len(matched) / max(len(patterns) * 0.3, 1))
                intents.append(Intent(name=name, confidence=round(conf, 3),
                                      matched_patterns=matched))
        return sorted(intents, key=lambda x: x.confidence, reverse=True)
