#!/usr/bin/env python3
# backend/main.py
# 🚀 Sovereign AI - نقطة التشغيل الرئيسية (النسخة الجبارة الكاملة)
# الإصدار: 2.0.0 - تشغيل كامل مع جميع الميزات

"""
Sovereign AI - العقل السيادي
----------------------------

هذا هو ملف التشغيل الرئيسي للنظام.
يقوم بـ:
1. تهيئة جميع مكونات الذكاء السيادي
2. تشغيل خادم الويب (FastAPI) أو واجهة سطر الأوامر (CLI)
3. تشغيل وضع المراقبة الحي
4. تشغيل وضع الخدمة (daemon)
5. إدارة دورة حياة النظام
6. مهام مجدولة تلقائية
7. تنبيهات وإشعارات

الاستخدام:
    python main.py                    # تشغيل خادم الويب (الوضع العادي)
    python main.py --cli              # تشغيل واجهة سطر الأوامر
    python main.py --monitor          # تشغيل وضع المراقبة الحية
    python main.py --daemon           # تشغيل كخدمة في الخلفية
    python main.py --test             # تشغيل اختبار سريع
    python main.py --config config.json  # استخدام ملف إعدادات مخصص
"""

import argparse
import asyncio
import signal
import sys
import time
import uuid
import threading
import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

# إعداد المسار
# يعمل من الجذر أو من داخل backend (M1)
import os
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if os.path.isdir(_BACKEND_DIR):
    sys.path.insert(0, _BACKEND_DIR)
else:
    sys.path.insert(0, '.')

# استيراد المكونات الرئيسية
try:
    from orchestrator import get_orchestrator, OrchestratorMode
    from app import app as web_app
    import uvicorn
except ImportError as e:
    print(f"❌ خطأ في الاستيراد: {e}")
    print("تأكد من تشغيل هذا الملف من مجلد backend")
    sys.exit(1)

import logging

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SovereignAI")


# ============================================================
# الإعدادات والتكوين
# ============================================================

@dataclass
class SovereignConfig:
    """إعدادات النظام الرئيسية"""
    # التشغيل
    mode: str = "web"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # المراقبة
    monitor_interval: int = 5  # ثوانٍ
    monitor_history_size: int = 100
    
    # المهام المجدولة
    enable_scheduler: bool = True
    health_check_interval: int = 60  # ثوانٍ
    backup_interval: int = 3600  # ساعة
    report_interval: int = 86400  # يوم
    
    # الإنذارات
    enable_alerts: bool = True
    alert_threshold_health: float = 0.5
    alert_cooldown: int = 300  # ثوانٍ
    
    # التصدير
    export_dir: str = "exports"
    log_dir: str = "logs"
    
    # الاسترداد
    auto_recovery: bool = True
    max_recovery_attempts: int = 3
    
    # الحالة
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_time: float = field(default_factory=time.time)


# ============================================================
# نظام التنبيهات
# ============================================================

class AlertLevel(Enum):
    """مستويات التنبيه"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """تنبيه"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: float
    acknowledged: bool = False


class AlertManager:
    """مدير التنبيهات"""
    
    def __init__(self, config: SovereignConfig):
        self.config = config
        self.alerts: List[Alert] = []
        self._last_alert_time: Dict[str, float] = {}
        self._callbacks: List = []
    
    def add_alert(self, level: AlertLevel, title: str, message: str) -> Alert:
        """إضافة تنبيه جديد"""
        # التحقق من فترة التهدئة
        alert_key = f"{level.value}_{title}"
        now = time.time()
        
        if alert_key in self._last_alert_time:
            if now - self._last_alert_time[alert_key] < self.config.alert_cooldown:
                return None
        
        self._last_alert_time[alert_key] = now
        
        alert = Alert(
            id=str(uuid.uuid4())[:8],
            level=level,
            title=title,
            message=message,
            timestamp=now
        )
        
        self.alerts.append(alert)
        
        # الاحتفاظ بآخر 1000 تنبيه
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        
        # طباعة التنبيه
        emoji = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "💀"
        }.get(level, "🔔")
        
        print(f"\n{emoji} [{level.value.upper()}] {title}: {message}")
        
        # استدعاء الـ callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except:
                pass
        
        return alert
    
    def register_callback(self, callback):
        """تسجيل دالة للاستدعاء عند التنبيه"""
        self._callbacks.append(callback)
    
    def get_alerts(self, unacknowledged_only: bool = False) -> List[Alert]:
        """الحصول على التنبيهات"""
        alerts = self.alerts
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        return alerts[-100:]
    
    def acknowledge(self, alert_id: str) -> bool:
        """تأكيد تنبيه"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False


# ============================================================
# المهام المجدولة
# ============================================================

class TaskScheduler:
    """مج دول المهام"""
    
    def __init__(self, orchestrator, alert_manager: AlertManager, config: SovereignConfig):
        self.orchestrator = orchestrator
        self.alert_manager = alert_manager
        self.config = config
        self.running = True
        self.tasks = []
        self._thread = None
    
    def start(self):
        """بدء المجدول"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("⏰ مجدول المهام بدأ العمل")
    
    def stop(self):
        """إيقاف المجدول"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("⏰ مجدول المهام توقف")
    
    def _run(self):
        """حلقة المهام المجدولة"""
        last_health_check = 0
        last_backup = 0
        last_report = 0
        
        while self.running:
            now = time.time()
            
            # فحص الصحة الدوري
            if now - last_health_check >= self.config.health_check_interval:
                self._health_check()
                last_health_check = now
            
            # نسخ احتياطي دوري
            if now - last_backup >= self.config.backup_interval:
                self._backup()
                last_backup = now
            
            # تقرير دوري
            if now - last_report >= self.config.report_interval:
                self._generate_report()
                last_report = now
            
            time.sleep(1)
    
    def _health_check(self):
        """فحص صحة النظام"""
        try:
            status = self.orchestrator.get_status()
            health_score = self._calculate_health_score(status)
            
            if health_score < self.config.alert_threshold_health:
                self.alert_manager.add_alert(
                    AlertLevel.WARNING,
                    "انخفاض صحة النظام",
                    f"درجة الصحة: {health_score:.1%}"
                )
            
            # تفعيل الاسترداد التلقائي
            if self.config.auto_recovery and health_score < 0.3:
                self.alert_manager.add_alert(
                    AlertLevel.CRITICAL,
                    "تفعيل وضع الاسترداد",
                    "الصحة منخفضة جداً، تفعيل الاسترداد التلقائي"
                )
                self.orchestrator.reset_all()
            
        except Exception as e:
            logger.error(f"خطأ في فحص الصحة: {e}")
    
    def _calculate_health_score(self, status: Dict) -> float:
        """حساب درجة الصحة"""
        components = status.get('components', {})
        healthy = sum(1 for h in components.values() if h == 'healthy')
        total = len(components)
        
        if total == 0:
            return 0.5
        
        return healthy / total
    
    def _backup(self):
        """إنشاء نسخة احتياطية"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.config.export_dir, f"backup_{timestamp}.json")
            
            os.makedirs(self.config.export_dir, exist_ok=True)
            
            status = self.orchestrator.get_status()
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 نسخة احتياطية: {backup_file}")
            
        except Exception as e:
            logger.error(f"خطأ في النسخ الاحتياطي: {e}")
    
    def _generate_report(self):
        """توليد تقرير دوري"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            report_file = os.path.join(self.config.export_dir, f"report_{timestamp}.json")
            
            status = self.orchestrator.get_status()
            history = self.orchestrator.get_history(limit=100)
            
            report = {
                "timestamp": time.time(),
                "status": status,
                "history": history,
                "alerts": [a.__dict__ for a in self.alert_manager.get_alerts()]
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 تقرير دوري: {report_file}")
            
        except Exception as e:
            logger.error(f"خطأ في توليد التقرير: {e}")


# ============================================================
# واجهة المراقبة الحية
# ============================================================

class MonitorUI:
    """واجهة مراقبة حية للنظام"""
    
    def __init__(self, orchestrator, alert_manager: AlertManager, config: SovereignConfig):
        self.orchestrator = orchestrator
        self.alert_manager = alert_manager
        self.config = config
        self.running = True
        self.history = deque(maxlen=config.monitor_history_size)
    
    def run(self):
        """تشغيل واجهة المراقبة"""
        self._clear_screen()
        self._print_header()
        
        while self.running:
            try:
                self._update_display()
                time.sleep(self.config.monitor_interval)
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                logger.error(f"خطأ في المراقبة: {e}")
    
    def _clear_screen(self):
        """مسح الشاشة"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _print_header(self):
        """طباعة رأس الشاشة"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         🎛️ لوحة مراقبة الذكاء السيادي                         ║
║                              Sovereign AI Monitor                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
    
    def _update_display(self):
        """تحديث العرض"""
        status = self.orchestrator.get_status()
        
        # حفظ في التاريخ
        self.history.append({
            "timestamp": time.time(),
            "status": status
        })
        
        # المعلومات الأساسية
        print(f"\n📌 الجلسة: {status['session_id']}")
        print(f"🎯 الوضع: {status['mode'].upper()}")
        print(f"⏱️ وقت التشغيل: {status['uptime_seconds']:.0f} ثانية")
        print(f"🔄 الدورات: {status['stats']['total_cycles']} (نجاح: {status['stats']['successful_cycles']})")
        
        # المكونات
        print("\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│                           🧩 حالة المكونات                                 │")
        print("├─────────────────────────────────────────────────────────────────────────────┤")
        
        components = status.get('components', {})
        for name, health in list(components.items())[:10]:
            icon = "🟢" if health == "healthy" else "🟡" if health == "degraded" else "🔴"
            print(f"│ {icon} {name:<40} : {health:<12}                              │")
        
        print("└─────────────────────────────────────────────────────────────────────────────┘")
        
        # التنبيهات الأخيرة
        alerts = self.alert_manager.get_alerts(unacknowledged_only=True)[-5:]
        if alerts:
            print("\n┌─────────────────────────────────────────────────────────────────────────────┐")
            print("│                           ⚠️ آخر التنبيهات                                  │")
            print("├─────────────────────────────────────────────────────────────────────────────┤")
            for alert in alerts:
                emoji = "ℹ️" if alert.level == AlertLevel.INFO else "⚠️" if alert.level == AlertLevel.WARNING else "❌"
                print(f"│ {emoji} [{alert.level.value.upper()}] {alert.title[:50]}                        │")
            print("└─────────────────────────────────────────────────────────────────────────────┘")
        
        # مساعدة
        print("\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ 💡 الأوامر: q=خروج, r=إعادة تعيين, s=حالة, c=مسح                          │")
        print("└─────────────────────────────────────────────────────────────────────────────┘")
        
        # قراءة الإدخال (غير محظور)
        import select
        import sys
        
        if select.select([sys.stdin], [], [], 0)[0]:
            cmd = sys.stdin.read(1).lower()
            if cmd == 'q':
                self.running = False
            elif cmd == 'r':
                self.orchestrator.reset_all()
                print("\n🔄 جاري إعادة التهيئة...")
            elif cmd == 's':
                self._show_detailed_status()
            elif cmd == 'c':
                self._clear_screen()
                self._print_header()


# ============================================================
# واجهة سطر الأوامر المتقدمة
# ============================================================

class SovereignCLI:
    """واجهة سطر الأوامر المتقدمة للذكاء السيادي"""
    
    def __init__(self, orchestrator, alert_manager: AlertManager, config: SovereignConfig):
        self.orchestrator = orchestrator
        self.alert_manager = alert_manager
        self.config = config
        self.running = True
        self.commands = self._init_commands()
    
    def _init_commands(self) -> Dict[str, Dict]:
        """تهيئة الأوامر المتاحة"""
        return {
            "help": {"func": self._cmd_help, "desc": "عرض المساعدة"},
            "h": {"func": self._cmd_help, "desc": "عرض المساعدة"},
            "?": {"func": self._cmd_help, "desc": "عرض المساعدة"},
            "status": {"func": self._cmd_status, "desc": "عرض حالة النظام"},
            "s": {"func": self._cmd_status, "desc": "عرض حالة النظام"},
            "reset": {"func": self._cmd_reset, "desc": "إعادة تهيئة النظام"},
            "history": {"func": self._cmd_history, "desc": "عرض آخر الأحداث"},
            "hist": {"func": self._cmd_history, "desc": "عرض آخر الأحداث"},
            "mode": {"func": self._cmd_set_mode, "desc": "تغيير وضع التشغيل: mode [normal|safe|recovery|emergency|debug|silent]"},
            "components": {"func": self._cmd_components, "desc": "عرض حالة المكونات"},
            "comp": {"func": self._cmd_components, "desc": "عرض حالة المكونات"},
            "alerts": {"func": self._cmd_alerts, "desc": "عرض التنبيهات"},
            "alert": {"func": self._cmd_alerts, "desc": "عرض التنبيهات"},
            "export": {"func": self._cmd_export, "desc": "تصدير الحالة: export [filename]"},
            "run": {"func": self._cmd_run_cycle, "desc": "تشغيل دورة معالجة: run [text]"},
            "chat": {"func": self._cmd_chat, "desc": "محادثة: chat [text]"},
            "clear": {"func": self._cmd_clear, "desc": "مسح الشاشة"},
            "cls": {"func": self._cmd_clear, "desc": "مسح الشاشة"},
            "exit": {"func": self._cmd_exit, "desc": "الخروج من النظام"},
            "quit": {"func": self._cmd_exit, "desc": "الخروج من النظام"},
            "q": {"func": self._cmd_exit, "desc": "الخروج من النظام"},
        }
    
    def run(self):
        """تشغيل واجهة CLI"""
        self._print_banner()
        self._cmd_help()
        
        while self.running:
            try:
                user_input = input("\n┌─[Sovereign CLI]─\n└─> ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd in self.commands:
                    self.commands[cmd]["func"](args)
                else:
                    # محادثة افتراضية
                    self._cmd_chat(user_input)
                    
            except KeyboardInterrupt:
                self._cmd_exit("")
            except Exception as e:
                print(f"❌ خطأ: {e}")
    
    def _print_banner(self):
        """طباعة شعار الترحيب"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ███████╗ ██████╗ ██╗   ██╗███████╗██████╗ ███████╗██╗ ██████╗ ███╗   ██╗    ║
║   ██╔════╝██╔═══██╗██║   ██║██╔════╝██╔══██╗██╔════╝██║██╔═══██╗████╗  ██║    ║
║   ███████╗██║   ██║██║   ██║█████╗  ██████╔╝█████╗  ██║██║   ██║██╔██╗ ██║    ║
║   ╚════██║██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██╔══╝  ██║██║   ██║██║╚██╗██║    ║
║   ███████║╚██████╔╝ ╚████╔╝ ███████╗██║  ██║██║     ██║╚██████╔╝██║ ╚████║    ║
║   ╚══════╝ ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝    ║
║                                                                               ║
║                     الذكاء السيادي - العقل المطلق                             ║
║                           Sovereign AI v2.0                                   ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        print(f"\n📌 الجلسة: {self.config.session_id}")
        print(f"📌 وقت البدء: {datetime.fromtimestamp(self.config.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📌 وضع التشغيل: {self.orchestrator.config.mode}")
    
    def _cmd_help(self, args: str = ""):
        """عرض المساعدة"""
        print("\n" + "═" * 70)
        print("📖 الأوامر المتاحة")
        print("═" * 70)
        
        for cmd, info in sorted(self.commands.items()):
            if len(cmd) <= 5:
                print(f"  {cmd:<12} - {info['desc']}")
        
        print("\n" + "═" * 70)
        print("💡 يمكنك أيضاً كتابة أي نص للمحادثة مع الذكاء")
        print("═" * 70)
    
    def _cmd_status(self, args: str = ""):
        """عرض حالة النظام"""
        status = self.orchestrator.get_status()
        
        print("\n" + "═" * 70)
        print("📊 حالة النظام")
        print("═" * 70)
        print(f"  الجلسة: {status['session_id']}")
        print(f"  الوضع: {status['mode']}")
        print(f"  وقت التشغيل: {status['uptime_seconds']:.0f} ثانية")
        print(f"  الدورات الكلية: {status['stats']['total_cycles']}")
        print(f"  الدورات الناجحة: {status['stats']['successful_cycles']}")
        print(f"  الدورات الفاشلة: {status['stats']['failed_cycles']}")
        print(f"  متوسط المدة: {status['stats']['avg_cycle_duration']*1000:.2f} مللي ثانية")
        print(f"  حجم الكاش: {status['cache_size']}")
        print(f"  حجم السجل: {status['history_size']}")
        print("═" * 70)
    
    def _cmd_reset(self, args: str = ""):
        """إعادة تهيئة النظام"""
        print("\n🔄 جاري إعادة تهيئة النظام...")
        self.orchestrator.reset_all()
        
        self.alert_manager.add_alert(
            AlertLevel.INFO,
            "إعادة تهيئة النظام",
            "تمت إعادة تهيئة النظام بنجاح"
        )
        print("✅ تم إعادة تهيئة النظام بنجاح")
    
    def _cmd_history(self, args: str = ""):
        """عرض آخر الأحداث"""
        limit = int(args) if args.isdigit() else 20
        history = self.orchestrator.get_history(limit=limit)
        
        print("\n" + "═" * 70)
        print(f"📜 آخر {len(history)} حدث")
        print("═" * 70)
        
        for entry in history[-limit:]:
            ts = datetime.fromtimestamp(entry['timestamp']).strftime('%H:%M:%S')
            print(f"  [{ts}] [{entry['level']}] {entry['message'][:60]}")
        
        print("═" * 70)
    
    def _cmd_set_mode(self, args: str = ""):
        """تغيير وضع التشغيل"""
        mode = args.strip()
        valid_modes = ["normal", "safe", "recovery", "emergency", "debug", "silent"]
        
        if not mode:
            print(f"⚠️ الوضع الحالي: {self.orchestrator.config.mode}")
            print(f"   الأوضاع المتاحة: {', '.join(valid_modes)}")
            return
        
        if mode not in valid_modes:
            print(f"❌ وضع غير صالح. الأوضاع المتاحة: {', '.join(valid_modes)}")
            return
        
        self.orchestrator.set_mode(mode)
        
        self.alert_manager.add_alert(
            AlertLevel.INFO,
            "تغيير وضع التشغيل",
            f"تم تغيير الوضع إلى {mode}"
        )
        print(f"✅ تم تغيير الوضع إلى: {mode}")
    
    def _cmd_components(self, args: str = ""):
        """عرض حالة المكونات"""
        status = self.orchestrator.get_status()
        components = status.get('components', {})
        
        print("\n" + "═" * 70)
        print("🧩 حالة المكونات")
        print("═" * 70)
        
        healthy = 0
        degraded = 0
        unhealthy = 0
        
        for name, health in components.items():
            icon = "🟢" if health == "healthy" else "🟡" if health == "degraded" else "🔴"
            print(f"  {icon} {name:<40} : {health}")
            
            if health == "healthy":
                healthy += 1
            elif health == "degraded":
                degraded += 1
            else:
                unhealthy += 1
        
        print("═" * 70)
        print(f"  🟢 صحي: {healthy} | 🟡 متدهور: {degraded} | 🔴 معطل: {unhealthy}")
        print("═" * 70)
    
    def _cmd_alerts(self, args: str = ""):
        """عرض التنبيهات"""
        alerts = self.alert_manager.get_alerts()
        
        print("\n" + "═" * 70)
        print(f"⚠️ التنبيهات ({len(alerts)})")
        print("═" * 70)
        
        for alert in alerts[-20:]:
            ts = datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            emoji = "ℹ️" if alert.level == AlertLevel.INFO else "⚠️" if alert.level == AlertLevel.WARNING else "❌" if alert.level == AlertLevel.ERROR else "💀"
            print(f"  {emoji} [{ts}] {alert.title}: {alert.message}")
        
        print("═" * 70)
    
    def _cmd_export(self, args: str = ""):
        """تصدير الحالة"""
        filename = args.strip() or f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = os.path.join(self.config.export_dir, filename)
        os.makedirs(self.config.export_dir, exist_ok=True)
        
        status = self.orchestrator.get_status()
        history = self.orchestrator.get_history(limit=500)
        
        export_data = {
            "timestamp": time.time(),
            "session_id": self.config.session_id,
            "status": status,
            "history": history,
            "alerts": [a.__dict__ for a in self.alert_manager.get_alerts()]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ تم التصدير إلى: {filepath}")
    
    def _cmd_run_cycle(self, args: str = ""):
        """تشغيل دورة معالجة"""
        text = args.strip()
        if not text:
            text = "cycle"
        
        print("\n🔄 جاري تشغيل دورة معالجة...")
        
        input_data = {
            "type": "cli_command",
            "text": text,
            "user_id": "sovereign",
            "session_id": self.config.session_id,
            "timestamp": time.time()
        }
        
        result = self.orchestrator.run_cycle(input_data)
        
        if result.success:
            print(f"\n✅ الدورة {result.cycle_id[:8]}... اكتملت في {result.duration*1000:.2f} مللي ثانية")
            print(f"   القرار: {result.decision.get('action', 'continue')}")
            print(f"   الثقة: {result.decision.get('confidence', 0.5):.1%}")
        else:
            print(f"\n❌ فشلت الدورة: {result.errors[0] if result.errors else 'غير معروف'}")
    
    def _cmd_chat(self, text: str):
        """محادثة مع الذكاء"""
        if not text:
            return
        
        print("\n🤔 [الذكاء السيادي يفكر...]")
        
        input_data = {
            "type": "cli_chat",
            "text": text,
            "user_id": "sovereign",
            "session_id": self.config.session_id,
            "timestamp": time.time()
        }
        
        result = self.orchestrator.run_cycle(input_data)
        
        if result.success:
            print(f"\n🧠 [الذكاء السيادي]:")
            print(f"   القرار: {result.decision.get('action', 'continue')}")
            print(f"   الثقة: {result.decision.get('confidence', 0.5):.1%}")
        else:
            print(f"\n⚠️ [الذكاء السيادي]: حدث خطأ")
    
    def _cmd_clear(self, args: str = ""):
        """مسح الشاشة"""
        os.system('cls' if os.name == 'nt' else 'clear')
        self._print_banner()
        self._cmd_help()
    
    def _cmd_exit(self, args: str = ""):
        """الخروج من النظام"""
        print("\n👋 إيقاف الذكاء السيادي...")
        self.orchestrator.stop()
        self.running = False
        print("✅ تم إيقاف النظام. وداعاً!")


# ============================================================
# وضع الخدمة (Daemon)
# ============================================================

def run_daemon(config: SovereignConfig):
    """تشغيل النظام كخدمة في الخلفية"""
    print("🔄 تشغيل النظام كخدمة في الخلفية...")
    
    # إنشاء ملف PID
    pid_file = "sovereign.pid"
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    
    # إعادة توجيه الإخراج
    sys.stdout = open(os.path.join(config.log_dir, "sovereign.out"), 'w')
    sys.stderr = open(os.path.join(config.log_dir, "sovereign.err"), 'w')
    
    orchestrator = get_orchestrator()
    alert_manager = AlertManager(config)
    scheduler = TaskScheduler(orchestrator, alert_manager, config)
    
    scheduler.start()
    
    # حلقة رئيسية
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()
        orchestrator.stop()
        os.unlink(pid_file)


# ============================================================
# التشغيل الرئيسي
# ============================================================

def load_config(config_file: str) -> SovereignConfig:
    """تحميل الإعدادات من ملف"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return SovereignConfig(**data)
    except Exception as e:
        print(f"⚠️ خطأ في تحميل الإعدادات: {e}")
        return SovereignConfig()


def save_config(config: SovereignConfig, config_file: str):
    """حفظ الإعدادات إلى ملف"""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config.__dict__, f, ensure_ascii=False, indent=2)
        print(f"✅ تم حفظ الإعدادات إلى {config_file}")
    except Exception as e:
        print(f"❌ خطأ في حفظ الإعدادات: {e}")


def run_web_server(config: SovereignConfig):
    """تشغيل خادم الويب"""
    print(f"\n🌐 تشغيل خادم الويب على http://{config.host}:{config.port}")
    print(f"📖 التوثيق: http://{config.host}:{config.port}/docs")
    print(f"🏥 فحص الصحة: http://{config.host}:{config.port}/health")
    print(f"🔌 WebSocket: ws://{config.host}:{config.port}/ws/{{user_id}}")
    print("\n⚠️ اضغط Ctrl+C لإيقاف الخادم\n")
    
    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level="info"
    )


def run_cli(config: SovereignConfig):
    """تشغيل واجهة سطر الأوامر"""
    orchestrator = get_orchestrator()
    alert_manager = AlertManager(config)
    
    cli = SovereignCLI(orchestrator, alert_manager, config)
    cli.run()


def run_monitor(config: SovereignConfig):
    """تشغيل واجهة المراقبة"""
    orchestrator = get_orchestrator()
    alert_manager = AlertManager(config)
    
    monitor = MonitorUI(orchestrator, alert_manager, config)
    monitor.run()


def run_test(config: SovereignConfig):
    """تشغيل اختبار سريع"""
    print("\n🧪 تشغيل اختبار سريع...\n")
    
    orchestrator = get_orchestrator()
    alert_manager = AlertManager(config)
    
    # 1) اختبار دورة واحدة
    print("1) اختبار دورة معالجة...")
    result = orchestrator.run_cycle({"test": True})
    print(f"   ✅ دورة {result.cycle_id[:8]}... {'نجاح' if result.success else 'فشل'}")
    
    # 2) اختبار حالة النظام
    print("\n2) اختبار حالة النظام...")
    status = orchestrator.get_status()
    print(f"   ✅ الجلسة: {status['session_id']}")
    print(f"   ✅ الوضع: {status['mode']}")
    print(f"   ✅ المكونات الصحية: {sum(1 for h in status['components'].values() if h == 'healthy')}")
    
    # 3) اختبار التنبيهات
    print("\n3) اختبار التنبيهات...")
    alert_manager.add_alert(AlertLevel.INFO, "اختبار", "هذا تنبيه اختباري")
    print(f"   ✅ تم إضافة تنبيه")
    
    # 4) اختبار إعادة التهيئة
    print("\n4) اختبار إعادة التهيئة...")
    orchestrator.reset_all()
    print(f"   ✅ تم إعادة التهيئة بنجاح")
    
    print("\n✅ جميع الاختبارات اجتازت بنجاح!")


def generate_default_config():
    """توليد ملف إعدادات افتراضي"""
    config = SovereignConfig()
    save_config(config, "sovereign_config.json")
    return config


def main():
    """الدالة الرئيسية"""
    parser = argparse.ArgumentParser(
        description="Sovereign AI - العقل السيادي (النسخة الجبارة الكاملة)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                    أمثلة                                     ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  python main.py                              # تشغيل خادم الويب              ║
║  python main.py --cli                        # تشغيل واجهة سطر الأوامر       ║
║  python main.py --monitor                    # تشغيل وضع المراقبة الحية       ║
║  python main.py --daemon                     # تشغيل كخدمة في الخلفية        ║
║  python main.py --test                       # تشغيل اختبار سريع              ║
║  python main.py --config config.json         # استخدام ملف إعدادات مخصص      ║
║  python main.py --generate-config            # توليد ملف إعدادات افتراضي      ║
║  python main.py --host 0.0.0.0 --port 8080   # خادم ويب على منفذ مختلف       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """
    )
    
    # أوضاع التشغيل
    parser.add_argument("--cli", "-c", action="store_true", help="تشغيل واجهة سطر الأوامر")
    parser.add_argument("--monitor", "-m", action="store_true", help="تشغيل وضع المراقبة الحية")
    parser.add_argument("--daemon", "-d", action="store_true", help="تشغيل كخدمة في الخلفية")
    parser.add_argument("--test", "-t", action="store_true", help="تشغيل اختبار سريع")
    parser.add_argument("--generate-config", action="store_true", help="توليد ملف إعدادات افتراضي")
    
    # إعدادات الخادم
    parser.add_argument("--host", default="0.0.0.0", help="عنوان خادم الويب (افتراضي: 0.0.0.0)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="منفذ خادم الويب (افتراضي: 8000)")
    parser.add_argument("--reload", "-r", action="store_true", help="إعادة تحميل تلقائي (للتطوير فقط)")
    
    # إعدادات عامة
    parser.add_argument("--config", "-cfg", default="sovereign_config.json", help="ملف الإعدادات")
    parser.add_argument("--export-dir", default="exports", help="مجلد التصدير")
    parser.add_argument("--log-dir", default="logs", help="مجلد السجلات")
    
    args = parser.parse_args()
    
    # إنشاء المجلدات
    os.makedirs(args.export_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    
    # توليد ملف إعدادات
    if args.generate_config:
        generate_default_config()
        return
    
    # تحميل الإعدادات
    config = load_config(args.config)
    
    # تحديث الإعدادات من معاملات سطر الأوامر
    config.host = args.host
    config.port = args.port
    config.reload = args.reload
    config.export_dir = args.export_dir
    config.log_dir = args.log_dir
    
    # معالجة إشارة الإيقاف
    def signal_handler(sig, frame):
        print("\n\n🛑 استلام إشارة إيقاف...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تشغيل الوضع المطلوب
    if args.test:
        run_test(config)
    elif args.cli:
        run_cli(config)
    elif args.monitor:
        run_monitor(config)
    elif args.daemon:
        run_daemon(config)
    else:
        run_web_server(config)


if __name__ == "__main__":
    main()
