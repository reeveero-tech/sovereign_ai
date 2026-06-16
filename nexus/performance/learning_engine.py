"""
NexusCore — محرك التعلم
يتعلم من سجل البيانات لتحسين التنبؤات (بدون تعديل كود السيد).
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nexus.performance.learning")


@dataclass
class LearningExample:
    features: Dict[str, float]
    label: Any
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class LearningModel:
    name: str
    model_type: str
    weights: Dict[str, float]
    bias: float
    training_examples: int
    accuracy: float
    trained_at: float = field(default_factory=time.time)


class LearningEngine:
    """محرك تعلم آلي بسيط (Perceptron + Naive Bayes) بدون مكتبات خارجية"""

    def __init__(self):
        self.models: Dict[str, LearningModel] = {}
        self.examples: List[LearningExample] = []
        self._class_probs: Dict[str, Dict] = {}
        logger.info("🎓 LearningEngine initialized")

    def add_example(self, features: Dict[str, float],
                    label: Any, weight: float = 1.0) -> None:
        self.examples.append(LearningExample(features=features,
                                              label=label, weight=weight))
        if len(self.examples) > 100_000:
            self.examples = self.examples[-100_000:]

    def train_linear(self, model_name: str, feature_keys: List[str],
                     target_key: str = "label",
                     learning_rate: float = 0.01,
                     epochs: int = 100) -> LearningModel:
        """تدريب نموذج انحدار خطي بسيط"""
        weights = {k: 0.0 for k in feature_keys}
        bias = 0.0
        data = [(ex.features, ex.label) for ex in self.examples
                if isinstance(ex.label, (int, float))
                and all(k in ex.features for k in feature_keys)]
        if not data:
            logger.warning("No valid training data")
            return LearningModel(model_name, "linear", {}, 0.0, 0, 0.0)

        for _ in range(epochs):
            for features, label in data:
                pred = sum(weights[k] * features.get(k, 0) for k in feature_keys) + bias
                err  = float(label) - pred
                for k in feature_keys:
                    weights[k] += learning_rate * err * features.get(k, 0)
                bias += learning_rate * err

        # حساب R²
        preds = [sum(weights[k] * f.get(k, 0) for k in feature_keys) + bias
                 for f, _ in data]
        labels = [float(l) for _, l in data]
        mean_l = sum(labels) / len(labels)
        ss_tot = sum((l - mean_l) ** 2 for l in labels)
        ss_res = sum((l - p) ** 2 for l, p in zip(labels, preds))
        r2 = max(0.0, 1 - ss_res / ss_tot) if ss_tot else 1.0

        model = LearningModel(
            name=model_name, model_type="linear",
            weights=weights, bias=bias,
            training_examples=len(data), accuracy=round(r2, 3),
        )
        self.models[model_name] = model
        logger.info(f"✅ Model '{model_name}' trained (R²={r2:.3f}, n={len(data)})")
        return model

    def predict(self, model_name: str, features: Dict[str, float]) -> Optional[float]:
        model = self.models.get(model_name)
        if not model or model.model_type != "linear":
            return None
        return sum(model.weights.get(k, 0) * v for k, v in features.items()) + model.bias

    def get_model_info(self, model_name: str) -> Optional[Dict]:
        m = self.models.get(model_name)
        if not m:
            return None
        return {"name": m.name, "type": m.model_type,
                "accuracy": m.accuracy, "examples": m.training_examples,
                "trained_at": m.trained_at}
