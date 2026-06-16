"""
NexusCore — التنبؤ السلوكي
يتنبأ بالسلوك المستقبلي بناءً على الأنماط التاريخية.
"""
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.analytics.behavior")


@dataclass
class BehaviorProfile:
    entity_id: str
    observations: List[Dict] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)
    action_counts: Dict[str, int] = field(default_factory=dict)
    predicted_next: Optional[str] = None
    confidence: float = 0.0


class BehaviorPredictor:
    """يبني نماذج سلوكية ويتنبأ بالأفعال التالية"""

    def __init__(self, history_limit: int = 500):
        self.profiles: Dict[str, BehaviorProfile] = {}
        self.transitions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.history_limit = history_limit
        logger.info("🧠 BehaviorPredictor initialized")

    def observe(self, entity_id: str, action: str, context: Optional[Dict] = None) -> None:
        profile = self.profiles.setdefault(
            entity_id,
            BehaviorProfile(entity_id=entity_id)
        )
        # سجل الملاحظة
        obs = {"action": action, "context": context or {}, "ts": time.time()}
        profile.observations.append(obs)
        if len(profile.observations) > self.history_limit:
            profile.observations = profile.observations[-self.history_limit:]
        profile.last_seen = obs["ts"]
        profile.action_counts[action] = profile.action_counts.get(action, 0) + 1
        # سجل الانتقال (Markov chain)
        if len(profile.observations) >= 2:
            prev = profile.observations[-2]["action"]
            self.transitions[entity_id][prev + "→" + action] += 1

    def predict_next(self, entity_id: str) -> Dict:
        profile = self.profiles.get(entity_id)
        if not profile or not profile.observations:
            return {"entity_id": entity_id, "prediction": None, "confidence": 0.0}

        last_action = profile.observations[-1]["action"]
        # ابحث عن الانتقالات من الفعل الأخير
        transitions = {
            k.split("→")[1]: v
            for k, v in self.transitions[entity_id].items()
            if k.startswith(last_action + "→")
        }
        if not transitions:
            # التنبؤ بالفعل الأكثر شيوعاً
            most_common = max(profile.action_counts, key=profile.action_counts.get)
            total = sum(profile.action_counts.values())
            conf = profile.action_counts[most_common] / total
            return {"entity_id": entity_id, "prediction": most_common,
                    "confidence": round(conf, 3), "basis": "frequency"}

        best = max(transitions, key=transitions.get)
        total = sum(transitions.values())
        conf  = transitions[best] / total
        profile.predicted_next = best
        profile.confidence = conf
        return {"entity_id": entity_id, "prediction": best,
                "confidence": round(conf, 3), "basis": "markov"}

    def get_profile_summary(self, entity_id: str) -> Dict:
        p = self.profiles.get(entity_id)
        if not p:
            return {}
        return {
            "entity_id": entity_id,
            "total_observations": len(p.observations),
            "unique_actions": len(p.action_counts),
            "top_actions": sorted(p.action_counts.items(),
                                  key=lambda x: x[1], reverse=True)[:5],
            "last_seen": p.last_seen,
        }
