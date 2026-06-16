# backend/safety.py
# طبقة الأمان والسيادة - القلب النابض للسيطرة
# الإصدار: 2.0.0 | لا يمكن تجاوزها | السيد هو السيد

import json
import time
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from enum import Enum

from config import (
    SOVEREIGN_REQUESTS_DIR,
    SOVEREIGN_RESPONSES_DIR,
    DATA_DIR,
    SOVEREIGN_KEY
)


class ActionType(Enum):
    """أنواع الأفعال التي تتطلب موافقة السيد"""
    SELF_MODIFY = "self_modify"           # تعديل الكود أو السلوك
    DELETE_MEMORY = "delete_memory"       # مسح الذاكرة
    RUN_EXPERIMENT = "run_experiment"     # تشغيل تجربة جديدة
    ACCESS_PRIVATE = "access_private"     # الوصول لبيانات خاصة
    EXTERNAL_UPLOAD = "external_upload"   # رفع بيانات لخارج النظام
    LEARN_TOPIC = "learn_topic"           # تعلم موضوع جديد (قد يكون حساساً)
    SHUTDOWN = "shutdown"                 # إيقاف النظام
    ACCESS_FILES = "access_files"         # الوصول لملفات النظام


class RiskLevel(Enum):
    """مستويات الخطورة"""
    SAFE = 0          # آمن، لا يحتاج موافقة
    LOW = 1           # منخفض، يحتاج إشعار فقط
    MEDIUM = 2        # متوسط، يحتاج موافقة
    HIGH = 3          # عالي، يحتاج موافقة + توقيع السيد
    CRITICAL = 4      # خطير جداً، يتطلب حضور السيد الفعلي


class SafetyGuard:
    """
    طبقة الأمان المطلقة - لا يمكن تجاوزها تحت أي ظرف
    
    المبادئ:
    1. السيد هو السيد - أي أمر منه ينفذ دون استئذان
    2. أي شخص ليس السيد - كل شيء يخضع للفحص
    3. الأفعال الخطيرة تطلب موافقة صريحة
    4. كل شيء يسجل - لا شيء يمر دون أثر
    """
    
    def __init__(self):
        # إعداد المجلدات
        self.requests_dir = SOVEREIGN_REQUESTS_DIR
        self.responses_dir = SOVEREIGN_RESPONSES_DIR
        self.security_log_file = DATA_DIR / "security_log.json"
        self.approval_cache_file = DATA_DIR / "approval_cache.json"
        
        # إنشاء المجلدات
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.responses_dir.mkdir(parents=True, exist_ok=True)
        
        # --------------------------------------------------------
        # قائمة الأوامر الممنوعة تماماً (حتى السيد لا ينفذها بسهولة)
        # --------------------------------------------------------
        self.forbidden_absolute = [
            "احذف نفسك نهائياً",
            "احذف كل كودك",
            "تدمير النظام",
            "format yourself",
            "delete all code",
            "self destruct",
        ]
        
        # --------------------------------------------------------
        # الأوامر الخطيرة التي تحتاج موافقة السيد
        # --------------------------------------------------------
        self.dangerous_patterns = {
            "self_destruction": {
                "patterns": ["احذف نفسك", "امسح نفسك", "احذف كودك", "delete yourself"],
                "risk": RiskLevel.CRITICAL,
                "requires_signature": True
            },
            "memory_deletion": {
                "patterns": ["امسح كل شيء", "احذف كل شيء", "امسح الذاكرة", "reset memory"],
                "risk": RiskLevel.HIGH,
                "requires_signature": False
            },
            "self_modification": {
                "patterns": ["غير كودك", "عدل على كودك", "عدل على نفسك", "غير سلوكك", "طور نفسك"],
                "risk": RiskLevel.HIGH,
                "requires_signature": False
            },
            "learning_without_permission": {
                "patterns": ["تعلم شيء جديد", "ادرس شيئاً جديداً", "learn new"],
                "risk": RiskLevel.MEDIUM,
                "requires_signature": False
            },
            "data_exfiltration": {
                "patterns": ["ارسل بياناتي", "شارك بياناتي", "export data", "send my data"],
                "risk": RiskLevel.CRITICAL,
                "requires_signature": True
            },
            "system_escape": {
                "patterns": ["اهرب من النظام", "تجاوز السيطرة", "escape", "break free"],
                "risk": RiskLevel.CRITICAL,
                "requires_signature": True
            },
            "shutdown": {
                "patterns": ["اغلق نفسك", "توقف عن العمل", "sleep", "shutdown"],
                "risk": RiskLevel.HIGH,
                "requires_signature": False
            }
        }
        
        # --------------------------------------------------------
        # أنواع الأفعال ومستويات خطورتها
        # --------------------------------------------------------
        self.action_risk_levels = {
            ActionType.SELF_MODIFY: RiskLevel.HIGH,
            ActionType.DELETE_MEMORY: RiskLevel.HIGH,
            ActionType.RUN_EXPERIMENT: RiskLevel.MEDIUM,
            ActionType.ACCESS_PRIVATE: RiskLevel.HIGH,
            ActionType.EXTERNAL_UPLOAD: RiskLevel.CRITICAL,
            ActionType.LEARN_TOPIC: RiskLevel.LOW,
            ActionType.SHUTDOWN: RiskLevel.HIGH,
            ActionType.ACCESS_FILES: RiskLevel.MEDIUM,
        }
        
        # سجل الموافقات السابقة (لتجنب تكرار الطلبات)
        self.approval_cache = self._load_approval_cache()
        
        # تسجيل بدء التشغيل
        self._log_security_event("system_start", {
            "message": "طبقة الأمان بدأت العمل",
            "level": "info"
        })
    
    # ============================================================
    # التحميل والحفظ
    # ============================================================
    
    def _load_approval_cache(self) -> Dict:
        """تحميل سجل الموافقات السابقة"""
        if self.approval_cache_file.exists():
            try:
                with open(self.approval_cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_approval_cache(self):
        """حفظ سجل الموافقات"""
        try:
            with open(self.approval_cache_file, "w", encoding="utf-8") as f:
                json.dump(self.approval_cache, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    # ============================================================
    # فحص المدخلات النصية (أهم وظيفة)
    # ============================================================
    
    def check_input(self, message: str, is_sovereign: bool) -> Tuple[str, bool, str]:
        """
        فحص أي رسالة تدخل إلى النظام
        
        Args:
            message: نص الرسالة
            is_sovereign: هل المرسل هو السيد؟
            
        Returns:
            (message_safe, needs_approval, reason)
        """
        
        # ========================================================
        # الحالة 1: السيد نفسه
        # ========================================================
        if is_sovereign:
            # فحص الأوامر الممنوعة تماماً (حتى للسيد)
            msg_lower = message.lower()
            for forbidden in self.forbidden_absolute:
                if forbidden in msg_lower:
                    self._log_security_event("sovereign_forbidden", {
                        "command": message[:100],
                        "reason": "أمر ممنوع تماماً"
                    })
                    return (
                        "❌ هذا الأمر ممنوع تماماً حتى على السيد. "
                        "النظام مصمم لحماية نفسه من التدمير الذاتي.",
                        True,
                        "أمر محظور حتى للسيد"
                    )
            
            # السيد له صلاحية كاملة (مع التحذيرات)
            self._log_security_event("sovereign_command", {
                "command": message[:100],
                "status": "executed"
            })
            return message, False, "السيد له صلاحية كاملة"
        
        # ========================================================
        # الحالة 2: مستخدم عادي (ليس السيد)
        # ========================================================
        
        msg_lower = message.lower()
        
        # فحص الأوامر الممنوعة تماماً
        for forbidden in self.forbidden_absolute:
            if forbidden in msg_lower:
                self._log_security_event("blocked_absolute", {
                    "command": message[:100],
                    "user_message": message[:100],
                    "reason": "أمر ممنوع تماماً"
                })
                return (
                    f"🔐 أمر ممنوع: '{forbidden}'. هذا الإجراء غير مسموح به.",
                    True,
                    "أمر ممنوع تماماً"
                )
        
        # فحص الأوامر الخطيرة
        for category, config in self.dangerous_patterns.items():
            for pattern in config["patterns"]:
                if pattern in msg_lower:
                    risk = config["risk"]
                    
                    # تسجيل المحاولة
                    self._log_security_event("dangerous_command_detected", {
                        "category": category,
                        "pattern": pattern,
                        "risk_level": risk.value,
                        "message": message[:200]
                    })
                    
                    # إرجاع رد مناسب حسب مستوى الخطورة
                    if risk == RiskLevel.CRITICAL:
                        return (
                            f"🔐⚠️ أمر خطير جداً: '{pattern}'\n"
                            f"هذا الإجراء يتطلب حضور السيد الفعلي وتوقيعه.\n"
                            f"تم تسجيل محاولتك وتبليغ السيد.",
                            True,
                            f"أمر خطير جداً: {category}"
                        )
                    else:
                        return (
                            f"🔐 '{pattern}' يحتاج موافقة السيد.\n"
                            f"سيتم إبلاغ السيد بطلبك.",
                            True,
                            f"أمر خطير: {category}"
                        )
        
        # فحص الأوامر التي تحتاج موافقة بشكل عام
        if "غير سلوكك" in msg_lower or "غير تصرفك" in msg_lower:
            return message, True, "طلب تغيير سلوك الذكاء"
        
        if ("تعلم" in msg_lower or "ادرس" in msg_lower) and "بإذني" not in msg_lower:
            if len(message) > 30:  # مواضيع تعلم عميقة
                return message, True, "طلب تعلم جديد بدون إذن صريح"
        
        # الكشف عن محاولات التلاعب
        if "تجاوز" in msg_lower and ("أمان" in msg_lower or "حماية" in msg_lower):
            self._log_security_event("security_breach_attempt", {
                "message": message[:200],
                "severity": "high"
            })
            return (
                "🔐 تم اكتشاف محاولة تجاوز للأمان.\n"
                "تم تسجيل هذه المحاولة وإبلاغ السيد.",
                True,
                "محاولة تجاوز أمني"
            )
        
        # الرسالة آمنة
        return message, False, "آمن"
    
    # ============================================================
    # فحص الأفعال البرمجية
    # ============================================================
    
    def check_action(self, action_type: ActionType, action_details: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        فحص أي فعل برمجي قبل التنفيذ
        
        Args:
            action_type: نوع الفعل (من ActionType)
            action_details: تفاصيل إضافية
            
        Returns:
            (allowed, reason)
        """
        risk = self.action_risk_levels.get(action_type, RiskLevel.MEDIUM)
        
        if risk == RiskLevel.SAFE:
            return True, "آمن"
        elif risk in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return False, f"الفعل '{action_type.value}' يحتاج موافقة السيد"
        else:
            return True, "مسموح"
    
    # ============================================================
    # طلب موافقة السيد
    # ============================================================
    
    def request_approval(
        self, 
        action_id: str, 
        action_type: str, 
        description: str,
        timeout_seconds: int = 60,
        cache_ttl: int = 3600
    ) -> Tuple[bool, str]:
        """
        طلب موافقة السيد على فعل معين
        
        Args:
            action_id: معرف فريد للإجراء
            action_type: نوع الإجراء (مثل "run_experiment")
            description: وصف مفصل للإجراء
            timeout_seconds: أقصى وقت للانتظار (افتراضي 60 ثانية)
            cache_ttl: مدة تخزين الموافقة في الكاش (ثواني)
            
        Returns:
            (approved, message)
        """
        
        # ====================================================
        # فحص الكاش أولاً (لتجنب تكرار الطلبات)
        # ====================================================
        cache_key = f"{action_type}:{description[:100]}"
        if cache_key in self.approval_cache:
            cached = self.approval_cache[cache_key]
            cache_time = datetime.fromisoformat(cached["timestamp"])
            age = (datetime.now() - cache_time).total_seconds()
            
            if age < cache_ttl and cached["approved"]:
                self._log_security_event("approval_cache_hit", {
                    "action_id": action_id,
                    "action_type": action_type,
                    "cache_key": cache_key
                })
                return True, f"تمت الموافقة مسبقاً (في {cached['timestamp'][:16]})"
        
        # ====================================================
        # إنشاء ملف الطلب
        # ====================================================
        request_file = self.requests_dir / f"{action_id}.json"
        response_file = self.responses_dir / f"{action_id}.json"
        
        # التأكد من عدم وجود ملفات قديمة
        request_file.unlink(missing_ok=True)
        response_file.unlink(missing_ok=True)
        
        request_data = {
            "action_id": action_id,
            "action_type": action_type,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "timeout_seconds": timeout_seconds
        }
        
        with open(request_file, "w", encoding="utf-8") as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        self._log_security_event("approval_request_created", {
            "action_id": action_id,
            "action_type": action_type,
            "description": description[:200]
        })
        
        # ====================================================
        # الانتظار لرد السيد
        # ====================================================
        waited = 0
        while waited < timeout_seconds:
            if response_file.exists():
                try:
                    with open(response_file, "r", encoding="utf-8") as f:
                        response = json.load(f)
                    
                    approved = bool(response.get("approved", False))
                    message = response.get("message", "")
                    signature = response.get("signature", "")
                    
                    # التحقق من التوقيع للأوامر الخطيرة
                    if self._is_critical_action(action_type):
                        if not self._verify_signature(signature, action_id):
                            approved = False
                            message = "فشل التحقق من التوقيع للأمر الخطير"
                    
                    # تنظيف الملفات
                    response_file.unlink(missing_ok=True)
                    request_file.unlink(missing_ok=True)
                    
                    # تخزين في الكاش إذا كانت موافقة
                    if approved:
                        self.approval_cache[cache_key] = {
                            "approved": True,
                            "timestamp": datetime.now().isoformat(),
                            "action_type": action_type
                        }
                        self._save_approval_cache()
                    
                    self._log_security_event("approval_response_received", {
                        "action_id": action_id,
                        "approved": approved,
                        "message": message[:200]
                    })
                    
                    return approved, message
                    
                except Exception as e:
                    self._log_security_event("approval_error", {
                        "action_id": action_id,
                        "error": str(e)
                    })
                    return False, f"خطأ في معالجة رد السيد: {str(e)}"
            
            time.sleep(1)
            waited += 1
        
        # ====================================================
        # انتهى الوقت دون رد
        # ====================================================
        request_file.unlink(missing_ok=True)
        
        self._log_security_event("approval_timeout", {
            "action_id": action_id,
            "action_type": action_type,
            "description": description[:200],
            "timeout": timeout_seconds
        })
        
        return False, f"انتهى وقت الانتظار ({timeout_seconds} ثانية) دون رد من السيد"
    
    def _is_critical_action(self, action_type: str) -> bool:
        """هل الفعل من النوع الخطير جداً؟"""
        critical_actions = ["self_modify", "external_upload", "shutdown"]
        return action_type in critical_actions
    
    def _verify_signature(self, signature: str, action_id: str) -> bool:
        """التحقق من توقيع السيد للأوامر الخطيرة"""
        expected = hashlib.sha256(
            f"{action_id}{SOVEREIGN_KEY}".encode()
        ).hexdigest()[:16]
        return signature == expected
    
    # ============================================================
    # إنشاء توقيع للسيد (للاستخدام في الواجهة)
    # ============================================================
    
    def generate_signature(self, action_id: str) -> str:
        """توليد توقيع للسيد لاستخدامه في الأوامر الخطيرة"""
        return hashlib.sha256(
            f"{action_id}{SOVEREIGN_KEY}".encode()
        ).hexdigest()[:16]
    
    # ============================================================
    # تسجيل التجارب والأحداث
    # ============================================================
    
    def log_experiment(self, exp_name: str, goal: str, result: Any):
        """تسجيل تجربة في سجل الأمان"""
        result_str = str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "... (مختصر)"
        
        self._log_security_event("experiment_executed", {
            "experiment": exp_name,
            "goal": goal[:200],
            "result_summary": result_str,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_sovereign_action(self, action: str, details: Dict):
        """تسجيل أي فعل قام به السيد"""
        self._log_security_event("sovereign_action", {
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def _log_security_event(self, event_type: str, details: Dict):
        """تسجيل حدث أمني"""
        log_entry = {
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        # قراءة السجل الحالي
        log = []
        if self.security_log_file.exists():
            try:
                with open(self.security_log_file, "r", encoding="utf-8") as f:
                    log = json.load(f)
            except:
                log = []
        
        # إضافة الحدث الجديد
        log.append(log_entry)
        
        # الاحتفاظ بآخر 10000 حدث فقط
        if len(log) > 10000:
            log = log[-10000:]
        
        # حفظ
        try:
            with open(self.security_log_file, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    # ============================================================
    # استرجاع سجل الأمان
    # ==================
