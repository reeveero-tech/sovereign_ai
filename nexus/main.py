"""
NexusCore — نقطة الدخول الرئيسية
يُهيئ جميع مكونات المنصة ويسجلها في المحرك الرئيسي.
"""
import asyncio
import logging
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nexus.main")


def initialize_nexus(config: Optional[dict] = None) -> "CoreEngine":  # noqa
    """يُهيئ NexusCore ويُعيد المحرك الرئيسي"""
    from nexus.core.engine import get_engine
    from nexus.data_pipeline.collector import DataCollector
    from nexus.data_pipeline.processor import DataProcessor
    from nexus.data_pipeline.sentiment_analyzer import SentimentAnalyzer
    from nexus.storage.cache_manager import CacheManager
    from nexus.storage.long_term_store import LongTermStore
    from nexus.storage.audit_logger import AuditLogger
    from nexus.storage.indexer import Indexer
    from nexus.analytics.pattern_mapper import PatternMapper
    from nexus.analytics.relationship_finder import RelationshipFinder
    from nexus.analytics.behavior_predictor import BehaviorPredictor
    from nexus.forecasting.trend_predictor import TrendPredictor
    from nexus.forecasting.market_analyzer import MarketAnalyzer
    from nexus.decision_engine.path_selector import PathSelector
    from nexus.decision_engine.risk_calculator import RiskCalculator
    from nexus.decision_engine.emergency_fallback import EmergencyFallback
    from nexus.connectors.api_connector import APIConnector
    from nexus.connectors.data_connector import DataConnector
    from nexus.connectors.database_connector import DatabaseConnector
    from nexus.automation.budget_analyzer import BudgetAnalyzer
    from nexus.automation.market_data_analyzer import MarketDataAnalyzer
    from nexus.automation.recommendation_engine import RecommendationEngine
    from nexus.automation.report_generator import ReportGenerator
    from nexus.security.security_audit import SecurityAudit
    from nexus.security.threat_analyzer import ThreatAnalyzer
    from nexus.security.backup_manager import BackupManager
    from nexus.security.health_monitor import HealthMonitor
    from nexus.resource_manager.device_orchestrator import DeviceOrchestrator
    from nexus.resource_manager.energy_optimizer import EnergyOptimizer
    from nexus.resource_manager.resource_allocator import ResourceAllocator
    from nexus.user_management.user_manager import UserManager
    from nexus.user_management.profile_manager import ProfileManager
    from nexus.user_management.auth_engine import AuthEngine
    from nexus.encryption.encryption_engine import EncryptionEngine
    from nexus.encryption.key_manager import KeyManager
    from nexus.encryption.secure_communication import SecureCommunication
    from nexus.performance.performance_optimizer import PerformanceOptimizer
    from nexus.performance.code_analyzer import CodeAnalyzer
    from nexus.performance.learning_engine import LearningEngine
    from nexus.nlp.text_processor import TextProcessor
    from nexus.nlp.intent_recognizer import IntentRecognizer
    from nexus.nlp.language_detector import LanguageDetector
    from nexus.visualization.chart_engine import ChartEngine
    from nexus.visualization.data_exporter import DataExporter
    from nexus.file_manager.file_handler import FileHandler
    from nexus.task_scheduler.scheduler import TaskScheduler
    from nexus.task_scheduler.task_registry import TaskRegistry
    from nexus.dashboard.analytics_api import AnalyticsDashboard

    engine = get_engine(config or {})

    components = {
        # خط الأنابيب
        "collector":       DataCollector(),
        "processor":       DataProcessor(),
        "sentiment":       SentimentAnalyzer(),
        # التخزين
        "cache":           CacheManager(),
        "store":           LongTermStore(),
        "audit":           AuditLogger(),
        "indexer":         Indexer(),
        # التحليلات
        "pattern_mapper":  PatternMapper(),
        "rel_finder":      RelationshipFinder(),
        "behavior":        BehaviorPredictor(),
        # التنبؤات
        "trend":           TrendPredictor(),
        "market":          MarketAnalyzer(),
        # محرك القرار
        "path_selector":   PathSelector(),
        "risk_calc":       RiskCalculator(),
        "fallback":        EmergencyFallback(),
        # الموصلات
        "api_conn":        APIConnector(),
        "data_conn":       DataConnector(),
        "db_conn":         DatabaseConnector(),
        # الأتمتة
        "budget":          BudgetAnalyzer(),
        "market_data":     MarketDataAnalyzer(),
        "recommender":     RecommendationEngine(),
        "reporter":        ReportGenerator(),
        # الأمان
        "sec_audit":       SecurityAudit(),
        "threat":          ThreatAnalyzer(),
        "backup":          BackupManager(),
        "health":          HealthMonitor(),
        # الموارد
        "devices":         DeviceOrchestrator(),
        "energy":          EnergyOptimizer(),
        "resources":       ResourceAllocator(),
        # المستخدمون
        "users":           UserManager(),
        "profiles":        ProfileManager(),
        "auth":            AuthEngine(),
        # التشفير
        "crypto":          EncryptionEngine(),
        "keys":            KeyManager(),
        "secure_comm":     SecureCommunication(),
        # الأداء
        "perf":            PerformanceOptimizer(),
        "code_analyzer":   CodeAnalyzer(),
        "learning":        LearningEngine(),
        # NLP
        "text_proc":       TextProcessor(),
        "intent":          IntentRecognizer(),
        "lang_detect":     LanguageDetector(),
        # التصور
        "charts":          ChartEngine(),
        "exporter":        DataExporter(),
        # الملفات والمهام
        "files":           FileHandler(),
        "scheduler":       TaskScheduler(),
        "tasks":           TaskRegistry(),
        # لوحة التحليلات
        "dashboard":       AnalyticsDashboard(),
    }

    for name, instance in components.items():
        engine.register_component(name, instance)

    logger.info(
        f"✅ NexusCore initialized successfully — "
        f"{len(components)} components registered"
    )
    return engine


def initialize_guardian(master_passphrase: Optional[str] = None) -> dict:
    """يُهيئ نظام الحارس"""
    from guardian.master_guardian import MasterGuardian
    from guardian.self_evolve import GuardianSelfEvolver
    from guardian.emergency_breaker import EmergencyBreaker
    from guardian.integrity_checker import IntegrityChecker

    guardian  = MasterGuardian(master_passphrase=master_passphrase)
    evolver   = GuardianSelfEvolver(master_guardian=guardian)
    breaker   = EmergencyBreaker(master_guardian=guardian)
    checker   = IntegrityChecker()

    # ربط الحارس بكسر الزجاج
    def on_emergency(event):
        breaker.activate(
            reason=event.details.get("reason", "critical_threat"),
            actor=event.actor,
        )

    guardian.on("on_emergency", on_emergency)

    # بناء baseline أولي إذا لم يكن موجوداً
    from pathlib import Path
    from guardian.integrity_checker import INTEGRITY_DB
    if not INTEGRITY_DB.exists():
        checker.build_baseline()
        logger.info("📸 Initial integrity baseline built")

    logger.info("🛡️ Guardian System fully initialized")
    return {
        "guardian": guardian,
        "evolver":  evolver,
        "breaker":  breaker,
        "checker":  checker,
    }


if __name__ == "__main__":
    print("🚀 Initializing NexusCore...")
    engine  = initialize_nexus()
    systems = initialize_guardian()
    print(f"✅ NexusCore: {len(engine.components)} components")
    print(f"🛡️ Guardian: ACTIVE")
    print(engine.get_status())
