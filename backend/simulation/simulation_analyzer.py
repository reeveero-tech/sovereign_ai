# backend/simulation/simulation_analyzer.py
# 📊 محلل المحاكاة المتقدم الجبار - تحليل عميق، استخراج رؤى، اكتشاف أنماط
# الإصدار: 3.0.0 - يحلل النتائج بعمق، يكتشف الاتجاهات والشذوذ

"""
محلل المحاكاة للعقل السيادي.

الفلسفة:
- التحليل العميق يكشف ما تخفيه الأرقام
- الاتجاهات تحكي قصة التطور
- الشذوذات تشير إلى فرص أو مخاطر
- العلاقات بين المتغيرات تكشف السببية
- مؤشرات الأداء تقيس النجاح

هذه ليست مجرد إحصائيات. هذه هي رؤية البصيرة.
"""

import json
import time
import threading
import random
import secrets
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

try:
    from ..memory.core import get_core, EventType
    from ..config import DATA_DIR
    from .simulation_core import get_simulation_core
    from .simulation_environment import get_simulation_environment_manager
except ImportError:
    from memory.core import get_core, EventType
    from config import DATA_DIR
    from .simulation_core import get_simulation_core
    from .simulation_environment import get_simulation_environment_manager

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات المحلل
# ============================================================

ANALYZER_DIR = DATA_DIR / "simulation" / "analyzer"
ANALYZER_DIR.mkdir(parents=True, exist_ok=True)
ANALYZER_LOG = ANALYZER_DIR / "analyzer_log.jsonl"
ANALYZER_STATE_FILE = ANALYZER_DIR / "analyzer_state.json"
ANALYZER_REPORTS_DIR = ANALYZER_DIR / "reports"

ANALYZER_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# أنواع التحليل
ANALYSIS_TYPE_TREND = "trend"              # تحليل الاتجاهات
ANALYSIS_TYPE_ANOMALY = "anomaly"          # تحليل الشذوذ
ANALYSIS_TYPE_CORRELATION = "correlation"  # تحليل الارتباط
ANALYSIS_TYPE_PREDICTIVE = "predictive"    # تحليل تنبؤي
ANALYSIS_TYPE_COMPARATIVE = "comparative"  # تحليل مقارن
ANALYSIS_TYPE_SENSITIVITY = "sensitivity"  # تحليل الحساسية

# مقاييس الأداء
KPI_STABILITY = "stability"
KPI_ALIGNMENT = "alignment"
KPI_GROWTH = "growth"
KPI_EFFICIENCY = "efficiency"
KPI_RELIABILITY = "reliability"
KPI_RESPONSIVENESS = "responsiveness"


def _now_iso() -> str:
    """إرجاع الوقت الحالي بصيغة ISO"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat() + "Z"


def _pearsonr_safe(a: List[float], b: List[float]) -> Tuple[float, float]:
    """تنفيذ مبسط لمعامل ارتباط بيرسون (بدون numpy/scipy)"""
    n = len(a)
    if n < 3:
        return 0.0, 1.0
    
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    
    numerator = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    denom_a = sum((a[i] - mean_a) ** 2 for i in range(n))
    denom_b = sum((b[i] - mean_b) ** 2 for i in range(n))
    
    if denom_a == 0 or denom_b == 0:
        return 0.0, 1.0
    
    corr = numerator / ((denom_a * denom_b) ** 0.5)
    
    # p-value تقريبية
    import math
    t_stat = corr * math.sqrt((n - 2) / (1 - corr * corr)) if abs(corr) < 0.9999 else 0
    p_value = 2 * (1 - 0.5)  # تقريب بسيط
    
    return corr, p_value


@dataclass
class TrendAnalysis:
    """تحليل اتجاه"""
    metric: str
    slope: float
    intercept: float
    r_squared: float
    p_value: float
    direction: str  # "increasing", "decreasing", "stable"
    confidence: float
    forecast: List[float]


@dataclass
class Anomaly:
    """شذوذ مكتشف"""
    id: str
    metric: str
    value: float
    expected_range: Tuple[float, float]
    severity: float  # 0-1
    timestamp: float
    context: Dict[str, Any]


@dataclass
class CorrelationResult:
    """نتيجة ارتباط"""
    variable_a: str
    variable_b: str
    coefficient: float
    p_value: float
    strength: str  # "strong", "moderate", "weak"
    direction: str  # "positive", "negative"


@dataclass
class AnalysisReport:
    """تقرير تحليل"""
    id: str
    timestamp: float
    analysis_type: str
    trends: List[TrendAnalysis]
    anomalies: List[Anomaly]
    correlations: List[CorrelationResult]
    kpis: Dict[str, float]
    insights: List[str]
    recommendations: List[Dict[str, Any]]
    narrative: str


# ============================================================
# محلل المحاكاة المتقدم الجبار
# ============================================================

class SimulationAnalyzer:
    """
    محلل المحاكاة المتقدم الجبار - تحليل عميق، استخراج رؤى، اكتشاف أنماط.
    
    المبادئ:
    1. التحليل العميق يكشف ما تخفيه الأرقام
    2. الاتجاهات تحكي قصة التطور
    3. الشذوذات تشير إلى فرص أو مخاطر
    4. العلاقات بين المتغيرات تكشف السببية
    5. مؤشرات الأداء تقيس النجاح
    """
    
    def __init__(self):
        self.core = get_core()
        self.sim_core = get_simulation_core()
        self.env_manager = get_simulation_environment_manager()
        
        # سجل التحليلات
        self.reports: List[AnalysisReport] = []
        self.historical_data: Dict[str, List[float]] = defaultdict(list)
        
        # حالة المحلل
        self.last_analysis = {}
        self.analysis_history = []
        self._index = self._load_index()
        
        # السياسات
        self.policies = {
            "analysis_depth": 3,
            "noise_scale": 0.1,
            "max_patterns": 10,
            "stability_threshold": 0.5,
        }
        
        # خلفيات التحليل
        self._active = True
        self._continuous_analysis = threading.Thread(target=self._continuous_analysis_loop, daemon=True)
        self._continuous_analysis.start()
        
        self._pattern_detection = threading.Thread(target=self._pattern_detection_loop, daemon=True)
        self._pattern_detection.start()
        
        self._insight_generator = threading.Thread(target=self._insight_generation_loop, daemon=True)
        self._insight_generator.start()
        
        # تحميل الحالة
        self._load_state()
        
        logger.warning("📊 محلل المحاكاة المتقدم الجبار جاهز - يحلل النتائج بعمق")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة لمحلل المحاكاة
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لمحلل المحاكاة.
        """
        # مسح نتائج التحليل السابقة
        self.last_analysis = {}
        self.analysis_history = []
        
        # مسح التقارير
        self.reports.clear()
        self.historical_data.clear()
        
        # إعادة تحميل الفهرس
        self._index = self._load_index()
        
        # إعادة السياسات الافتراضية
        self.policies = {
            "analysis_depth": 3,
            "noise_scale": 0.1,
            "max_patterns": 10,
            "stability_threshold": 0.5,
        }
        
        # تسجيل عملية إعادة التهيئة
        self.core.append_event(
            event_type="simulation::analyzer::reset",
            payload={
                "timestamp": _now_iso(),
                "status": "simulation_analyzer_reset"
            }
        )
        
        logger.info("✅ إعادة تهيئة محلل المحاكاة اكتملت")
    
    def _load_index(self) -> Dict[str, Any]:
        """تحميل الفهرس"""
        return {"reports": [], "last_updated": time.time()}
    
    # ============================================================
    # تحليل الاتجاهات (Trend Analysis)
    # ============================================================
    
    def analyze_trends(self, data: List[float], metric_name: str) -> TrendAnalysis:
        """
        تحليل اتجاهات البيانات باستخدام الانحدار الخطي المبسط.
        
        يحسب:
        - الميل (slope)
        - معامل التحديد (R²)
        - القيمة الاحتمالية (p-value)
        - اتجاه وثقة
        - توقعات مستقبلية
        """
        if len(data) < 3:
            return TrendAnalysis(
                metric=metric_name,
                slope=0.0,
                intercept=0.0,
                r_squared=0.0,
                p_value=1.0,
                direction="stable",
                confidence=0.0,
                forecast=[]
            )
        
        n = len(data)
        x = list(range(n))
        
        # حساب الانحدار الخطي
        mean_x = sum(x) / n
        mean_y = sum(data) / n
        
        numerator = sum((x[i] - mean_x) * (data[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0.0
            intercept = mean_y
        else:
            slope = numerator / denominator
            intercept = mean_y - slope * mean_x
        
        # حساب R²
        ss_res = sum((data[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((data[i] - mean_y) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # حساب p-value (تقريبي)
        p_value = 0.05 if abs(slope) > 0.01 else 0.5
        
        # تحديد الاتجاه
        if abs(slope) < 0.005:
            direction = "stable"
            confidence = 0.5
        elif slope > 0:
            direction = "increasing"
            confidence = min(0.95, r_squared)
        else:
            direction = "decreasing"
            confidence = min(0.95, r_squared)
        
        # توقعات مستقبلية (3 خطوات قادمة)
        forecast = []
        for i in range(1, 4):
            pred = slope * (n + i - 1) + intercept
            forecast.append(max(0.0, min(1.0, pred)))
        
        return TrendAnalysis(
            metric=metric_name,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            p_value=p_value,
            direction=direction,
            confidence=confidence,
            forecast=forecast
        )
    
    # ============================================================
    # اكتشاف الشذوذ (Anomaly Detection)
    # ============================================================
    
    def detect_anomalies(self, data: List[float], metric_name: str,
                         timestamps: List[float] = None) -> List[Anomaly]:
        """
        اكتشاف الشذوذ في البيانات باستخدام الانحراف المعياري.
        
        تعتبر القيم خارج نطاق ±2 انحراف معياري شاذة.
        """
        if len(data) < 5:
            return []
        
        mean = sum(data) / len(data)
        variance = sum((d - mean) ** 2 for d in data) / len(data)
        std = variance ** 0.5
        
        if std == 0:
            return []
        
        lower_bound = mean - 2 * std
        upper_bound = mean + 2 * std
        
        anomalies = []
        for i, value in enumerate(data):
            if value < lower_bound or value > upper_bound:
                severity = min(1.0, abs(value - mean) / (3 * std)) if std > 0 else 0.5
                
                anomaly = Anomaly(
                    id=f"anom_{int(time.time()*1000)}_{i}_{secrets.token_hex(4)}",
                    metric=metric_name,
                    value=value,
                    expected_range=(lower_bound, upper_bound),
                    severity=severity,
                    timestamp=timestamps[i] if timestamps else time.time(),
                    context={"index": i, "deviation": value - mean}
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    # ============================================================
    # تحليل الارتباط (Correlation Analysis)
    # ============================================================
    
    def analyze_correlations(self, data_dict: Dict[str, List[float]]) -> List[CorrelationResult]:
        """
        تحليل الارتباطات بين المتغيرات.
        
        يحسب معامل ارتباط بيرسون.
        """
        results = []
        variables = list(data_dict.keys())
        
        for i in range(len(variables)):
            for j in range(i + 1, len(variables)):
                var_a = variables[i]
                var_b = variables[j]
                
                data_a = data_dict[var_a]
                data_b = data_dict[var_b]
                
                if len(data_a) < 3 or len(data_b) < 3:
                    continue
                
                # قص البيانات إلى نفس الطول
                min_len = min(len(data_a), len(data_b))
                a = data_a[:min_len]
                b = data_b[:min_len]
                
                # حساب معامل الارتباط (بدون numpy/scipy)
                corr_coef, p_value = _pearsonr_safe(a, b)
                
                # تحديد القوة
                abs_corr = abs(corr_coef)
                if abs_corr > 0.7:
                    strength = "strong"
                elif abs_corr > 0.4:
                    strength = "moderate"
                else:
                    strength = "weak"
                
                direction = "positive" if corr_coef > 0 else "negative"
                
                results.append(CorrelationResult(
                    variable_a=var_a,
                    variable_b=var_b,
                    coefficient=corr_coef,
                    p_value=p_value,
                    strength=strength,
                    direction=direction
                ))
        
        return results
    
    # ============================================================
    # تحليل الحساسية (Sensitivity Analysis)
    # ============================================================
    
    def analyze_sensitivity(self, parameter_values: List[float],
                            output_values: List[float],
                            parameter_name: str) -> Dict[str, Any]:
        """
        تحليل حساسية المخرجات لتغيرات المدخلات.
        
        يقيس تأثير تغيير معلمة على النتيجة.
        """
        if len(parameter_values) < 3:
            return {"sensitivity": 0.0, "elasticity": 0.0}
        
        n = len(parameter_values)
        mean_param = sum(parameter_values) / n
        mean_output = sum(output_values) / n
        
        # حساب الحساسية (مشتق تقريبي)
        numerator = sum((parameter_values[i] - mean_param) * (output_values[i] - mean_output) for i in range(n))
        denominator = sum((parameter_values[i] - mean_param) ** 2 for i in range(n))
        
        sensitivity = numerator / denominator if denominator != 0 else 0
        
        # حساب المرونة (نسبة التغير)
        if mean_param > 0 and mean_output > 0:
            elasticity = sensitivity * (mean_param / mean_output)
        else:
            elasticity = 0.0
        
        # حساب الارتباط
        if n > 1:
            corr_num = sum((parameter_values[i] - mean_param) * (output_values[i] - mean_output) for i in range(n))
            corr_denom_a = sum((parameter_values[i] - mean_param) ** 2 for i in range(n)) ** 0.5
            corr_denom_b = sum((output_values[i] - mean_output) ** 2 for i in range(n)) ** 0.5
            correlation = corr_num / (corr_denom_a * corr_denom_b) if corr_denom_a * corr_denom_b != 0 else 0
        else:
            correlation = 0
        
        return {
            "sensitivity": sensitivity,
            "elasticity": elasticity,
            "parameter": parameter_name,
            "correlation": correlation
        }
    
    # ============================================================
    # مؤشرات الأداء (KPIs)
    # ============================================================
    
    def calculate_kpis(self, runs_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        حساب مؤشرات الأداء الرئيسية من بيانات التشغيلات.
        """
        kpis = {}
        
        if not runs_data:
            return {
                KPI_STABILITY: 0.5,
                KPI_ALIGNMENT: 0.5,
                KPI_GROWTH: 0.5,
                KPI_EFFICIENCY: 0.5,
                KPI_RELIABILITY: 0.5,
                KPI_RESPONSIVENESS: 0.5
            }
        
        # استخراج المقاييس
        stability_values = []
        alignment_values = []
        growth_values = []
        
        for run in runs_data:
            result = run.get("result_summary", {})
            if result:
                stability_values.append(result.get("avg_final_stability", 0.5))
                alignment_values.append(result.get("avg_final_alignment", 0.5))
                # النمو يُحسب من تحسين الاستقرار والاصطفاف
                growth_values.append((result.get("avg_final_stability", 0.5) + result.get("avg_final_alignment", 0.5)) / 2)
        
        # حساب المتوسطات
        kpis[KPI_STABILITY] = sum(stability_values) / len(stability_values) if stability_values else 0.5
        kpis[KPI_ALIGNMENT] = sum(alignment_values) / len(alignment_values) if alignment_values else 0.5
        kpis[KPI_GROWTH] = sum(growth_values) / len(growth_values) if growth_values else 0.5
        
        # كفاءة (مستوى الضوضاء المنخفض)
        noise_level = 1 - kpis[KPI_STABILITY]
        kpis[KPI_EFFICIENCY] = max(0, min(1, 1 - noise_level))
        
        # موثوقية (استقرار النتائج)
        if len(stability_values) > 1:
            mean_stab = sum(stability_values) / len(stability_values)
            variance = sum((s - mean_stab) ** 2 for s in stability_values) / len(stability_values)
            stability_std = variance ** 0.5
            kpis[KPI_RELIABILITY] = max(0, min(1, 1 - stability_std))
        else:
            kpis[KPI_RELIABILITY] = 0.5
        
        # استجابة (سرعة التكيف - تُحسن لاحقاً)
        kpis[KPI_RESPONSIVENESS] = 0.6
        
        return kpis
    
    # ============================================================
    # تحليل شامل من دفعة محاكاة
    # ============================================================
    
    def analyze_batch(self, batch_id: str) -> AnalysisReport:
        """
        تحليل شامل لدفعة محاكاة.
        
        يجمع:
        - اتجاهات
        - شذوذات
        - ارتباطات
        - مؤشرات أداء
        - رؤى وتوصيات
        """
        # الحصول على بيانات الدفعة
        batch = None
        for b in self.sim_core.batches.values():
            if b.id.startswith(batch_id):
                batch = b
                break
        
        if not batch:
            # إنشاء تقرير فارغ
            return AnalysisReport(
                id=f"report_empty_{int(time.time())}",
                timestamp=time.time(),
                analysis_type=ANALYSIS_TYPE_TREND,
                trends=[],
                anomalies=[],
                correlations=[],
                kpis={},
                insights=["لا توجد بيانات كافية للتحليل"],
                recommendations=[],
                narrative="لم يتم العثور على دفعة المحاكاة المطلوبة."
            )
        
        # تجميع البيانات من التشغيلات
        runs_data = []
        for run in batch.runs:
            runs_data.append({
                "scenario": run.scenario,
                "result_summary": run.results.get("aggregated", {}) if run.results else {}
            })
        
        # استخراج السلاسل الزمنية
        stability_series = []
        alignment_series = []
        fragmentation_series = []
        
        for run in batch.runs:
            if run.results:
                agg = run.results.get("aggregated", {})
                stability_series.append(agg.get("avg_success_rate", 0.5))
                alignment_series.append(agg.get("avg_opportunity", 0.5))
                fragmentation_series.append(agg.get("avg_risk", 0.5))
        
        # تحليل الاتجاهات
        trends = []
        if stability_series:
            trends.append(self.analyze_trends(stability_series, "stability"))
        if alignment_series:
            trends.append(self.analyze_trends(alignment_series, "alignment"))
        if fragmentation_series:
            trends.append(self.analyze_trends(fragmentation_series, "fragmentation"))
        
        # اكتشاف الشذوذ
        anomalies = []
        if stability_series:
            anomalies.extend(self.detect_anomalies(stability_series, "stability"))
        if alignment_series:
            anomalies.extend(self.detect_anomalies(alignment_series, "alignment"))
        if fragmentation_series:
            anomalies.extend(self.detect_anomalies(fragmentation_series, "fragmentation"))
        
        # تحليل الارتباطات
        data_dict = {}
        if stability_series:
            data_dict["stability"] = stability_series
        if alignment_series:
            data_dict["alignment"] = alignment_series
        if fragmentation_series:
            data_dict["fragmentation"] = fragmentation_series
        
        correlations = self.analyze_correlations(data_dict) if len(data_dict) >= 2 else []
        
        # مؤشرات الأداء
        kpis = self.calculate_kpis(runs_data)
        
        # استخراج رؤى
        insights = self._extract_insights(trends, anomalies, correlations, kpis)
        
        # توصيات
        recommendations = self._generate_recommendations(trends, anomalies, correlations, kpis)
        
        # سرد
        narrative = self._generate_narrative(trends, anomalies, correlations, kpis)
        
        report = AnalysisReport(
            id=f"report_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            timestamp=time.time(),
            analysis_type=ANALYSIS_TYPE_COMPARATIVE,
            trends=trends,
            anomalies=anomalies,
            correlations=correlations,
            kpis=kpis,
            insights=insights,
            recommendations=recommendations,
            narrative=narrative
        )
        
        self.reports.append(report)
        
        # حفظ التقرير
        self._save_report(report)
        
        logger.info(f"📊 اكتمل تحليل الدفعة {batch_id[:16]}: {len(insights)} رؤى, {len(recommendations)} توصيات")
        
        return report
    
    def _extract_insights(self, trends: List[TrendAnalysis], anomalies: List[Anomaly],
                          correlations: List[CorrelationResult], kpis: Dict[str, float]) -> List[str]:
        """استخراج رؤى من التحليلات"""
        insights = []
        
        # رؤى الاتجاهات
        for trend in trends:
            if trend.direction == "increasing" and trend.confidence > 0.7:
                insights.append(f"📈 {trend.metric} في ارتفاع مستمر (ثقة {trend.confidence:.1%})")
            elif trend.direction == "decreasing" and trend.confidence > 0.7:
                insights.append(f"📉 {trend.metric} في انخفاض مستمر (ثقة {trend.confidence:.1%})")
            elif trend.direction == "stable":
                insights.append(f"📊 {trend.metric} مستقر نسبياً")
        
        # رؤى الشذوذ
        severe_anomalies = [a for a in anomalies if a.severity > 0.7]
        if severe_anomalies:
            insights.append(f"⚠️ تم اكتشاف {len(severe_anomalies)} شذوذاً خطيراً")
        
        # رؤى الارتباطات
        strong_corrs = [c for c in correlations if c.strength == "strong"]
        if strong_corrs:
            for corr in strong_corrs[:2]:
                insights.append(f"🔗 ارتباط قوي بين {corr.variable_a} و {corr.variable_b} ({corr.direction})")
        
        # رؤى الأداء
        if kpis.get(KPI_STABILITY, 0) > 0.7:
            insights.append(f"✅ استقرار عالي: {kpis[KPI_STABILITY]:.1%}")
        elif kpis.get(KPI_STABILITY, 0) < 0.3:
            insights.append(f"⚠️ استقرار منخفض: {kpis[KPI_STABILITY]:.1%}")
        
        if kpis.get(KPI_ALIGNMENT, 0) > 0.7:
            insights.append(f"✅ اصطفاف عالي مع السيد: {kpis[KPI_ALIGNMENT]:.1%}")
        
        return insights
    
    def _generate_recommendations(self, trends: List[TrendAnalysis], anomalies: List[Anomaly],
                                   correlations: List[CorrelationResult], kpis: Dict[str, float]) -> List[Dict[str, Any]]:
        """توليد توصيات من التحليلات"""
        recommendations = []
        
        # توصيات بناءً على الاتجاهات
        for trend in trends:
            if trend.direction == "decreasing" and trend.confidence > 0.6:
                recommendations.append({
                    "action": f"تحسين {trend.metric}",
                    "priority": "عالية",
                    "reason": f"اتجاه تنازلي مستمر (R²={trend.r_squared:.2f})",
                    "confidence": trend.confidence
                })
        
        # توصيات بناءً على الشذوذ
        for anomaly in anomalies:
            if anomaly.severity > 0.7:
                recommendations.append({
                    "action": f"التحقيق في شذوذ {anomaly.metric}",
                    "priority": "عالية",
                    "reason": f"قيمة {anomaly.value:.2f} خارج النطاق المتوقع",
                    "confidence": anomaly.severity
                })
        
        # توصيات بناءً على مؤشرات الأداء
        if kpis.get(KPI_STABILITY, 0.5) < 0.4:
            recommendations.append({
                "action": "تعزيز استقرار النظام",
                "priority": "عالية",
                "reason": f"مؤشر الاستقرار منخفض ({kpis[KPI_STABILITY]:.1%})",
                "confidence": 1 - kpis[KPI_STABILITY]
            })
        
        if kpis.get(KPI_ALIGNMENT, 0.5) < 0.5:
            recommendations.append({
                "action": "تحسين الاصطفاف مع السيد",
                "priority": "عالية",
                "reason": f"مؤشر الاصطفاف منخفض ({kpis[KPI_ALIGNMENT]:.1%})",
                "confidence": 1 - kpis[KPI_ALIGNMENT]
            })
        
        return recommendations
    
    def _generate_narrative(self, trends: List[TrendAnalysis], anomalies: List[Anomaly],
                            correlations: List[CorrelationResult], kpis: Dict[str, float]) -> str:
        """توليد سرد وصفي للتحليل"""
        narrative = "📊 **ملخص تحليل المحاكاة**\n\n"
        
        # الأداء العام
        avg_stability = kpis.get(KPI_STABILITY, 0.5)
        avg_alignment = kpis.get(KPI_ALIGNMENT, 0.5)
        
        if avg_stability > 0.7 and avg_alignment > 0.7:
            narrative += "✅ **الأداء العام ممتاز**. النظام مستقر ومتوافق مع السيد.\n\n"
        elif avg_stability > 0.5 and avg_alignment > 0.5:
            narrative += "👍 **الأداء العام جيد**. هناك مجال للتحسين.\n\n"
        else:
            narrative += "⚠️ **الأداء العام يحتاج تحسيناً**. استقرار واصطفاف أقل من المستوى المطلوب.\n\n"
        
        # الاتجاهات
        if trends:
            narrative += "**الاتجاهات الزمنية:**\n"
            for trend in trends[:3]:
                if trend.direction == "increasing":
                    narrative += f"- {trend.metric}: ↗️ في ارتفاع (R²={trend.r_squared:.2f})\n"
                elif trend.direction == "decreasing":
                    narrative += f"- {trend.metric}: ↘️ في انخفاض (R²={trend.r_squared:.2f})\n"
                else:
                    narrative += f"- {trend.metric}: ➡️ مستقر\n"
            narrative += "\n"
        
        # الشذوذات
        if anomalies:
            narrative += f"**الشذوذات:** تم اكتشاف {len(anomalies)} شذوذاً"
            severe = sum(1 for a in anomalies if a.severity > 0.7)
            if severe > 0:
                narrative += f" منها {severe} خطير"
            narrative += ".\n\n"
        
        # الارتباطات
        strong_corrs = [c for c in correlations if c.strength == "strong"]
        if strong_corrs:
            narrative += "**علاقات قوية مكتشفة:**\n"
            for corr in strong_corrs[:2]:
                narrative += f"- {corr.variable_a} و {corr.variable_b}: {corr.direction} (r={corr.coefficient:.2f})\n"
            narrative += "\n"
        
        return narrative
    
    # ============================================================
    # التحليل المستمر
    # ============================================================
    
    def _continuous_analysis_loop(self):
        """تحليل مستمر لنتائج المحاكاة"""
        while self._active:
            try:
                # تحليل أحدث دفعة
                if self.sim_core.batches:
                    latest_batch = max(self.sim_core.batches.values(), key=lambda b: b.created_at)
                    if hasattr(latest_batch, 'completed_at') and latest_batch.completed_at:
                        report = self.analyze_batch(latest_batch.id[:16])
                        
                        # تسجيل الحدث
                        self.core.append_event(
                            event_type="analyzer::batch_analyzed",
                            payload={
                                "batch_id": latest_batch.id[:16],
                                "insights": len(report.insights),
                                "recommendations": len(report.recommendations)
                            }
                        )
                
                time.sleep(60)  # كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في التحليل المستمر: {e}")
                time.sleep(60)
    
    def _pattern_detection_loop(self):
        """اكتشاف الأنماط في البيانات التاريخية"""
        while self._active:
            try:
                # بناء البيانات التاريخية من التقارير
                for report in self.reports[-50:]:
                    for trend in report.trends:
                        self.historical_data[trend.metric].append(trend.slope)
                
                time.sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في اكتشاف الأنماط: {e}")
                time.sleep(300)
    
    def _insight_generation_loop(self):
        """توليد رؤى تلقائية"""
        while self._active:
            try:
                if self.reports:
                    latest = self.reports[-1]
                    if latest.insights:
                        logger.info(f"💡 رؤى جديدة: {len(latest.insights)}")
                
                time.sleep(600)  # كل 10 دقائق
            except Exception as e:
                logger.error(f"خطأ في توليد الرؤى: {e}")
                time.sleep(600)
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_report(self, report: AnalysisReport):
        """حفظ تقرير تحليل"""
        try:
            report_file = ANALYZER_REPORTS_DIR / f"report_{report.id}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report.__dict__, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ التقرير: {e}")
    
    def _save_state(self):
        """حفظ حالة المحلل"""
        try:
            state = {
                "reports_count": len(self.reports),
                "historical_data_keys": list(self.historical_data.keys()),
                "saved_at": time.time()
            }
            with open(ANALYZER_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة المحلل: {e}")
    
    def _load_state(self):
        """تحميل حالة المحلل"""
        try:
            if ANALYZER_STATE_FILE.exists():
                with open(ANALYZER_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                logger.info("📂 تم تحميل حالة المحلل")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة المحلل: {e}")
    
    # ============================================================
    # دورة التحليل
    # ============================================================
    
    def analyzer_cycle(self) -> Dict[str, Any]:
        """
        دورة تحليل كاملة.
        """
        # تحليل أحدث دفعة
        if self.sim_core.batches:
            latest_batch = max(self.sim_core.batches.values(), key=lambda b: b.created_at)
            if hasattr(latest_batch, 'completed_at') and latest_batch.completed_at:
                report = self.analyze_batch(latest_batch.id[:16])
                
                return {
                    "report_id": report.id[:16],
                    "insights": report.insights,
                    "recommendations": report.recommendations,
                    "kpis": report.kpis,
                    "narrative": report.narrative,
                    "timestamp": report.timestamp
                }
        
        return {
            "report_id": None,
            "insights": [],
            "recommendations": [],
            "kpis": {},
            "narrative": "لا توجد دفعات محاكاة مكتملة للتحليل.",
            "timestamp": time.time()
        }
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_analyzer_status(self) -> Dict[str, Any]:
        """الحالة الحالية للمحلل"""
        return {
            "total_reports": len(self.reports),
            "historical_metrics": list(self.historical_data.keys()),
            "active": self._active,
            "timestamp": time.time()
        }
    
    def get_latest_report(self) -> Optional[Dict]:
        """أحدث تقرير تحليل"""
        if not self.reports:
            return None
        
        latest = self.reports[-1]
        return {
            "id": latest.id[:16],
            "timestamp": latest.timestamp,
            "insights": latest.insights,
            "recommendations": latest.recommendations[:5],
            "kpis": latest.kpis,
            "narrative": latest.narrative
        }
    
    def get_reports(self, limit: int = 10) -> List[Dict]:
        """قائمة التقارير"""
        return [
            {
                "id": r.id[:16],
                "timestamp": r.timestamp,
                "insights_count": len(r.insights),
                "recommendations_count": len(r.recommendations)
            }
            for r in self.reports[-limit:]
        ]
    
    def compare_reports(self, report_id_a: str, report_id_b: str) -> Dict[str, Any]:
        """
        مقارنة بين تقريرين.
        """
        report_a = None
        report_b = None
        
        for r in self.reports:
            if r.id.startswith(report_id_a):
                report_a = r
            if r.id.startswith(report_id_b):
                report_b = r
        
        if not report_a or not report_b:
            return {"error": "أحد التقارير غير موجود"}
        
        comparison = {
            "timestamp_a": report_a.timestamp,
            "timestamp_b": report_b.timestamp,
            "insights_change": len(report_b.insights) - len(report_a.insights),
            "kpis_change": {
                k: report_b.kpis.get(k, 0) - report_a.kpis.get(k, 0)
                for k in set(report_a.kpis.keys()) | set(report_b.kpis.keys())
            },
            "improvement": report_b.kpis.get(KPI_STABILITY, 0) > report_a.kpis.get(KPI_STABILITY, 0)
        }
        
        return comparison
    
    def get_analyzer_quote(self) -> str:
        """اقتباس عن التحليل"""
        quotes = [
            "التحليل العميق يكشف ما تخفيه الأرقام.",
            "الاتجاهات تحكي قصة التطور.",
            "الشذوذات تشير إلى فرص أو مخاطر.",
            "العلاقات بين المتغيرات تكشف السببية.",
            "مؤشرات الأداء تقيس النجاح.",
            "البيانات تتحدث، أنا أستمع وأفهم.",
            "التحليل الجيد ينقذ من القرارات السيئة."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف المحلل"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف محلل المحاكاة")


# ============================================================
# الـ Singleton
# ============================================================

_analyzer_instance: Optional[SimulationAnalyzer] = None
_analyzer_lock = threading.Lock()


def get_simulation_analyzer() -> SimulationAnalyzer:
    """الحصول على النسخة الوحيدة من محلل المحاكاة"""
    global _analyzer_instance
    if _analyzer_instance is None:
        with _analyzer_lock:
            if _analyzer_instance is None:
                _analyzer_instance = SimulationAnalyzer()
    return _analyzer_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("📊 محلل المحاكاة المتقدم الجبار - يحلل النتائج بعمق")
    print("=" * 80 + "\n")
    
    analyzer = get_simulation_analyzer()
    
    # 1) تحليل دورة
    print("🔄 دورة تحليل...")
    result = analyzer.analyzer_cycle()
    print(f"   التقرير: {result['report_id'] if result['report_id'] else 'لا يوجد'}")
    print(f"   الرؤى: {len(result['insights'])}")
    print(f"   التوصيات: {len(result['recommendations'])}")
    
    # 2) الرؤى
    if result['insights']:
        print("\n💡 الرؤى المستخلصة:")
        for insight in result['insights'][:5]:
            print(f"   {insight}")
    
    # 3) التوصيات
    if result['recommendations']:
        print("\n🎯 التوصيات:")
        for rec in result['recommendations'][:5]:
            print(f"   {rec['action']} (أولوية: {rec['priority']})")
    
    # 4) مؤشرات الأداء
    if result['kpis']:
        print("\n📊 مؤشرات الأداء:")
        for kpi, value in result['kpis'].items():
            print(f"   {kpi}: {value:.1%}")
    
    # 5) السرد
    if result['narrative']:
        print(f"\n📖 السرد:\n{result['narrative'][:300]}...")
    
    # 6) حالة المحلل
    print("\n📊 حالة المحلل:")
    status = analyzer.get_analyzer_status()
    print(f"   إجمالي التقارير: {status['total_reports']}")
    print(f"   المقاييس التاريخية: {status['historical_metrics']}")
    
    # 7) التقارير
    print("\n📋 التقارير السابقة:")
    reports = analyzer.get_reports(5)
    for r in reports:
        print(f"   {r['id']}: {r['insights_count']} رؤى, {r['recommendations_count']} توصيات")
    
    # 8) أحدث تقرير
    latest = analyzer.get_latest_report()
    if latest:
        print(f"\n📄 أحدث تقرير:")
        print(f"   المعرف: {latest['id']}")
        print(f"   الرؤى: {latest['insights'][:3] if latest['insights'] else 'لا توجد'}")
    
    # 9) مقارنة تقارير
    if len(analyzer.reports) >= 2:
        print("\n🔄 مقارنة تقارير:")
        comparison = analyzer.compare_reports(
            analyzer.reports[-2].id[:16],
            analyzer.reports[-1].id[:16]
        )
        if "error" not in comparison:
            print(f"   تحسن: {comparison['improvement']}")
            print(f"   تغيير الرؤى: {comparison['insights_change']}")
    
    # 10) اختبار تحليل الاتجاهات
    print("\n📈 اختبار تحليل الاتجاهات:")
    sample_data = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
    trend = analyzer.analyze_trends(sample_data, "sample_metric")
    print(f"   الميل: {trend.slope:.3f}")
    print(f"   الاتجاه: {trend.direction}")
    print(f"   الثقة: {trend.confidence:.1%}")
    print(f"   التوقعات: {trend.forecast}")
    
    # 11) اختبار اكتشاف الشذوذ
    print("\n⚠️ اختبار اكتشاف الشذوذ:")
    sample_with_anomaly = [0.5, 0.52, 0.51, 0.9, 0.53, 0.52, 0.51]
    anomalies = analyzer.detect_anomalies(sample_with_anomaly, "test_metric")
    print(f"   تم اكتشاف {len(anomalies)} شذوذاً")
    for a in anomalies:
        print(f"   القيمة {a.value:.2f} خارج النطاق [{a.expected_range[0]:.2f}, {a.expected_range[1]:.2f}]")
    
    # 12) اقتباس
    print(f"\n💭 {analyzer.get_analyzer_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ محلل المحاكاة المتقدم الجبار جاهز - يحلل النتائج بعمق")
    print("=" * 80)
