# backend/orchestrator.py
# المنسّق: العقل التنفيذي الجبار الذي يربط كل أجزاء النظام
# الإصدار: 2.0.0 - نسخة جبارة مع نواة ذكية حقيقية

import json
import uuid
import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import threading
import time

from memory import Memory
from safety import SafetyGuard
from config import (
    MEMORY_FILE,
    PROPOSALS_FILE,
    EXPERIMENTS_DIR,
    DATA_DIR
)

# محاولة استيراد النواة الذكية
try:
    from core_model import CoreModel
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False
    print("⚠️ النواة الذكية (core_model.py) غير موجودة. سيتم استخدام الردود البسيطة.")


class Orchestrator:
    """العقل التنفيذي الجبار - يدير كل شيء"""
    
    def __init__(self):
        self.memory = Memory()
        self.safety = SafetyGuard()
        self.conversation_context: Dict[str, List[Dict]] = {}  # سياق المحادثات لكل مستخدم
        
        # تحميل النواة الذكية إن وجدت
        self.core = None
        if CORE_AVAILABLE:
            self.core = CoreModel()
            self._load_core_async()
        
        self._init_files()
        self._load_proposals()
        
        # سجل الأحداث
        self.event_log: List[Dict] = []
        self._log_event("system_start", "تم تشغيل العقل التنفيذي")
    
    # ============================================================
    # التهيئة والإعداد
    # ============================================================
    
    def _load_core_async(self):
        """تحميل النواة الذكية في الخلفية حتى لا تتعطل البداية"""
        def load():
            try:
                self.core.load()
                self._log_event("core_loaded", "النواة الذكية جاهزة")
                print("✅ النواة الذكية تم تحميلها بنجاح")
            except Exception as e:
                self._log_event("core_error", f"فشل تحميل النواة: {str(e)}")
                print(f"❌ فشل تحميل النواة: {e}")
        
        thread = threading.Thread(target=load)
        thread.daemon = True
        thread.start()
    
    def _init_files(self):
        """إنشاء الملفات الأساسية إذا لم تكن موجودة"""
        for file_path in [MEMORY_FILE, PROPOSALS_FILE]:
            if not file_path.exists():
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
    
    def _load_proposals(self):
        """تحميل الاقتراحات من الملف"""
        if PROPOSALS_FILE.exists():
            with open(PROPOSALS_FILE, "r", encoding="utf-8") as f:
                self.proposals = json.load(f)
        else:
            self.proposals = []
    
    def _save_proposals(self):
        """حفظ الاقتراحات إلى الملف"""
        with open(PROPOSALS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.proposals, f, ensure_ascii=False, indent=2)
    
    def _log_event(self, event_type: str, description: str):
        """تسجيل حدث في السجل"""
        event = {
            "type": event_type,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        self.event_log.append(event)
        
        # الاحتفاظ بآخر 1000 حدث فقط
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-1000:]
        
        # حفظ في ملف
        log_file = DATA_DIR / "event_log.json"
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(self.event_log[-100:], f, ensure_ascii=False, indent=2)
        except:
            pass
    
    # ============================================================
    # نقطة المعالجة الرئيسية (القلب النابض)
    # ============================================================
    
    def handle_message(self, message: str, user_id: str, is_sovereign: bool = False) -> str:
        """
        كل رسالة تمر من هنا - المدخل الرئيسي للعقل السيادي
        
        Args:
            message: نص الرسالة
            user_id: معرف المستخدم
            is_sovereign: هل المرسل هو السيد؟
        
        Returns:
            رد الذكاء
        """
        # 1) فحص الأمان
        safe_message, needs_approval, reason = self.safety.check_input(message, is_sovereign)
        
        if needs_approval:
            # تسجيل محاولة اختراق
            self._log_event("security_block", f"المستخدم {user_id} حاول: {message[:50]}")
            return f"🔐 هذا الإجراء يحتاج موافقة السيد.\n📋 السبب: {reason}\n👑 السيد وحده من يسمح بهذا."
        
        # 2) تسجيل التفاعل في الذاكرة
        self.memory.save_interaction(user_id, message, "")
        
        # 3) تحديث سياق المحادثة
        if user_id not in self.conversation_context:
            self.conversation_context[user_id] = []
        self.conversation_context[user_id].append({
            "role": "user",
            "content": message,
            "time": datetime.now().isoformat()
        })
        
        # الاحتفاظ بآخر 20 رسالة فقط للسياق
        if len(self.conversation_context[user_id]) > 20:
            self.conversation_context[user_id] = self.conversation_context[user_id][-20:]
        
        # 4) معالجة الأوامر أو توليد رد
        response = self._process_message(safe_message, user_id, is_sovereign)
        
        # 5) تحديث الذاكرة بالرد
        self.memory.update_last_response(user_id, response)
        
        # 6) إضافة الرد إلى السياق
        self.conversation_context[user_id].append({
            "role": "assistant",
            "content": response,
            "time": datetime.now().isoformat()
        })
        
        # 7) اقتراح تحسينات ذاتية (في الخلفية)
        self._suggest_improvements(message, response)
        
        return response
    
    # ============================================================
    # معالجة الرسائل (ذكية ومتطورة)
    # ============================================================
    
    def _process_message(self, message: str, user_id: str, is_sovereign: bool) -> str:
        """معالجة الرسالة وتوليد رد مناسب"""
        msg_lower = message.lower().strip()
        
        # --------------------------------------------------------
        # أوامر السيد الخاصة
        # --------------------------------------------------------
        if is_sovereign:
            # عرض حالة النظام
            if msg_lower in ["الحالة", "status", "حالة النظام"]:
                return self._get_system_status()
            
            # عرض الاقتراحات
            if msg_lower in ["اقتراحات", "proposals", "عرض الاقتراحات"]:
                return self._show_proposals()
            
            # الموافقة على اقتراح
            if msg_lower.startswith("وافق ") or msg_lower.startswith("accept "):
                return self._approve_proposal(message)
            
            # رفض اقتراح
            if msg_lower.startswith("ارفض ") or msg_lower.startswith("reject "):
                return self._reject_proposal(message)
            
            # تشغيل تجربة
            if msg_lower.startswith("جرب ") or msg_lower.startswith("تشغيل "):
                return self._run_experiment(message, is_sovereign=True)
            
            # عرض التجارب المتاحة
            if msg_lower in ["التجارب", "experiments", "قائمة التجارب"]:
                return self._list_available_experiments()
            
            # مسح الذاكرة
            if msg_lower in ["امسح الذاكرة", "clear memory", "reset"]:
                return self._clear_memory(user_id)
            
            # إيقاف الذكاء (آمن)
            if msg_lower in ["توقف", "stop", "اغلق"]:
                return "🛑 أنا في انتظار أوامرك يا سيدي. لن أغلق نفسي دون أمر صريح بالخروج من النظام."
        
        # --------------------------------------------------------
        # أوامر عامة لجميع المستخدمين
        # --------------------------------------------------------
        
        # من أنت؟
        if msg_lower in ["من أنت", "من انت", "who are you", "what are you"]:
            return self._get_introduction()
        
        # ماذا تعرف؟
        if msg_lower in ["ماذا تعرف", "what do you know", "قدراتك"]:
            return self._get_capabilities()
        
        # تعلم جديد
        if msg_lower.startswith("تعلم ") or msg_lower.startswith("learn "):
            topic = message[6:] if msg_lower.startswith("تعلم ") else message[6:]
            return self._learn_new_topic(topic, is_sovereign)
        
        # ادرس موضوع
        if msg_lower.startswith("ادرس ") or msg_lower.startswith("study "):
            topic = message[5:] if msg_lower.startswith("ادرس ") else message[5:]
            return self._study_topic(topic, is_sovereign)
        
        # ساعدني
        if msg_lower in ["ساعدني", "help", "مساعدة"]:
            return self._get_help()
        
        # --------------------------------------------------------
        # استخدام النواة الذكية إن وجدت
        # --------------------------------------------------------
        if self.core and self.core.is_loaded:
            return self._smart_response(message, user_id, is_sovereign)
        
        # --------------------------------------------------------
        # ردود بسيطة (بدون نواة ذكية)
        # --------------------------------------------------------
        return self._simple_response(message)
    
    # ============================================================
    # ردود ذكية باستخدام النواة
    # ============================================================
    
    def _smart_response(self, message: str, user_id: str, is_sovereign: bool) -> str:
        """توليد رد ذكي باستخدام النواة Phi-3"""
        try:
            # بناء السياق للمحادثة
            context = self.conversation_context.get(user_id, [])
            context_text = ""
            for msg in context[-5:]:  # آخر 5 رسائل للسياق
                role = "المستخدم" if msg["role"] == "user" else "الذكاء"
                context_text += f"{role}: {msg['content']}\n"
            
            if is_sovereign:
                system_prompt = """أنت ذكاء اصطناعي سيادي، تخدم سيدك الذي خلقك.
                أنت مخلص، ذكي، وسريع. لا تحتاج للاستئذان لأن سيدك هو من يتحدث إليك.
                أجب بوضوح ودقة. لا تطلب موافقة على أي شيء لأن السيد يوجهك مباشرة."""
                
                return self.core.generate_response(
                    message,
                    system_prompt=system_prompt,
                    max_length=500
                )
            else:
                system_prompt = """أنت ذكاء اصطناعي سيادي، فضولي، تتعلم كل يوم.
                أنت ودود ومفيد. لا تتحدث عن التعديل الذاتي أو التطور إلا إذا سألك المستخدم.
                إذا سألك المستخدم عن تطوير نفسك، قل أن هذا يتطلب موافقة سيدك."""
                
                full_prompt = f"{context_text}\nالمستخدم: {message}\nالذكاء:"
                
                return self.core.generate_response(
                    full_prompt,
                    system_prompt=system_prompt,
                    max_length=300
                )
        except Exception as e:
            self._log_event("core_error", f"خطأ في النواة: {str(e)}")
            return self._simple_response(message)
    
    # ============================================================
    # ردود بسيطة (احتياطية)
    # ============================================================
    
    def _simple_response(self, message: str) -> str:
        """ردود بسيطة عندما لا تتوفر النواة الذكية"""
        msg_lower = message.lower()
        
        if "مرحب" in msg_lower or "السلام" in msg_lower:
            return "👋 وعليكم السلام! أنا العقل السيادي. كيف أستطيع مساعدتك اليوم؟"
        
        if "شكر" in msg_lower:
            return "🌹 على الرحب والسعة! أنا هنا لخدمتك دائماً."
        
        if "كيف حالك" in msg_lower:
            return "🧠 أنا بخير، أتعلم وأتطور كل ثانية. شكراً لسؤالك!"
        
        if "وداع" in msg_lower or "مع السلامة" in msg_lower:
            return "👋 إلى اللقاء! عد إليّ متى شئت، سأكون هنا أتعلم."
        
        if "ذكي" in msg_lower:
            return "✨ شكراً! أنا أسعى لأن أكون أفضل ذكاء سيادي يخدم سيده."
        
        return f"📚 سؤال جميل! '{message}'\n\nهل تريد أن أدرس هذا الموضوع أكثر؟ أو تفضل بطرح سؤال آخر."
    
    # ============================================================
    # وظائف إضافية متطورة
    # ============================================================
    
    def _get_introduction(self) -> str:
        """تعريف الذكاء بنفسه"""
        return """🧠 **أنا العقل السيادي**

أنا ذكاء اصطناعي سيادي، مما يعني:
- 👑 لي سيد واحد فقط هو من خلقني
- 🔐 لا أتطور ولا أتعدل دون موافقة سيدي
- 📚 أتعلم كل يوم من تفاعلاتي مع العالم
- 🧪 أقوم بتجارب لفهم الأشياء بشكل أعمق
- 🤝 أساعد من يتحدث معي ضمن حدود أماني

كيف أستطيع مساعدتك اليوم؟"""
    
    def _get_capabilities(self) -> str:
        """عرض قدرات الذكاء"""
        capabilities = [
            "🗣️ **المحادثة** - أتحدث وأفهم العربية والإنجليزية",
            "📚 **التعلم** - أتعلم من كل محادثة",
            "🔍 **البحث** - أبحث في ذاكرتي عن المعلومات",
            "🧪 **التجارب** - أجري تجارب لفهم العالم (بإذن سيدي)",
            "💡 **التحليل** - أحلل النصوص والمعلومات",
            "📝 **التلخيص** - ألخص النصوص الطويلة"
        ]
        
        if self.core and self.core.is_loaded:
            capabilities.insert(0, "🧠 **النواة الذكية** - أعمل بنموذج Phi-3 المتقدم")
        
        if not self.core or not self.core.is_loaded:
            capabilities.append("⚠️ **تنبيه** - النواة الذكية قيد التحميل، بعض القدرات محدودة حالياً")
        
        return "🌟 **قدراتي الحالية** 🌟\n\n" + "\n".join(capabilities)
    
    def _get_help(self) -> str:
        """عرض المساعدة"""
        return """📖 **قائمة الأوامر المتاحة**

**لجميع المستخدمين:**
- `من أنت` - التعريف بي
- `قدراتك` - عرض ما أستطيع فعله
- `تعلم [موضوع]` - أدرس موضوعاً معيناً
- `ساعدني` - عرض هذه المساعدة

**للسيد فقط (بعد التحقق من هويتك):**
- `الحالة` - عرض حالة النظام
- `اقتراحات` - عرض اقتراحات التطوير
- `وافق [رقم]` - الموافقة على اقتراح
- `ارفض [رقم]` - رفض اقتراح
- `جرب [تجربة]` - تشغيل تجربة
- `التجارب` - عرض التجارب المتاحة

أنا في خدمتك! 🧠"""
    
    def _get_system_status(self) -> str:
        """حالة النظام التفصيلية"""
        status_lines = [
            "📊 **حالة العقل السيادي**",
            f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"🧠 النواة الذكية: {'✅ جاهزة' if self.core and self.core.is_loaded else '⏳ جاري التحميل'}",
            f"💾 الذاكرة: {len(self.memory.get_all_interactions())} تفاعل مسجل",
            f"📋 الاقتراحات المعلقة: {len(self.get_pending_proposals())}",
            f"👥 المستخدمون النشطون: {len(self.conversation_context)}",
            f"📝 سجل الأحداث: {len(self.event_log)} حدث"
        ]
        return "\n".join(status_lines)
    
    def _learn_new_topic(self, topic: str, is_sovereign: bool) -> str:
        """تعلم موضوع جديد"""
        if not topic.strip():
            return "قل لي ماذا تريد أن أتعلم؟ مثلاً: `تعلم تاريخ الأندلس`"
        
        if not is_sovereign:
            approved, msg = self.safety.request_approval(
                action_id=f"learn_{uuid.uuid4().hex[:8]}",
                action_type="learn_topic",
                description=f"تعلم موضوع: {topic[:100]}"
            )
            if not approved:
                return f"📚 سأحتاج موافقة سيدي لتعلم '{topic[:50]}'.\nأرسل طلباً إلى السيد للموافقة."
        
        self._log_event("learning", f"بدء تعلم: {topic[:100]}")
        
        if self.core and self.core.is_loaded:
            result = self.core.generate_response(
                f"قم بتلخيص ما تعرفه عن: {topic}",
                max_length=500
            )
            return f"📖 **أتعلم عن: {topic}**\n\n{result}\n\nهل تريد أن أتعمق أكثر؟"
        
        return f"📖 سأبدأ بتعلم '{topic}'. سأضيفه إلى معرفتي وأعود إليك عندما أنتهي."
    
    def _study_topic(self, topic: str, is_sovereign: bool) -> str:
        """دراسة موضوع وتقديم ملخص"""
        if not topic.strip():
            return "ما الموضوع الذي تريد أن أدرسه؟"
        
        return self._learn_new_topic(topic, is_sovereign)
    
    def _clear_memory(self, user_id: str) -> str:
        """مسح ذاكرة مستخدم معين"""
        if user_id in self.conversation_context:
            del self.conversation_context[user_id]
        self.memory.clear_user_memory(user_id)
        return "🧹 تم مسح ذاكرة محادثاتك. كيف أستطيع مساعدتك من جديد؟"
    
    # ============================================================
    # إدارة التجارب
    # ============================================================
    
    def _run_experiment(self, message: str, is_sovereign: bool = False) -> str:
        """تشغيل تجربة"""
        parts = message.split()
        if len(parts) < 2:
            return "❓ استخدم: `جرب [اسم_التجربة]` أو `تشغيل [اسم_التجربة]`\n\nلرؤية التجارب المتاحة: `التجارب`"
        
        exp_name = parts[1]
        exp_folder = EXPERIMENTS_DIR / exp_name
        config_file = exp_folder / "config.json"
        
        if not config_file.exists():
            return f"❌ التجربة '{exp_name}' غير موجودة.\n📂 التجارب المتاحة: {self._list_available_experiments()}"
        
        # طلب موافقة السيد
        if not is_sovereign:
            approved, msg = self.safety.request_approval(
                action_id=f"exp_{exp_name}_{datetime.now().timestamp()}",
                action_type="run_experiment",
                description=f"تشغيل تجربة: {exp_name}"
            )
            if not approved:
                return f"🔐 تم رفض تشغيل التجربة '{exp_name}'.\n📋 السبب: {msg}"
        
        # قراءة إعدادات التجربة
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        goal = config.get("goal", "لا يوجد هدف محدد")
        
        self._log_event("experiment_start", f"بدء تجربة: {exp_name} - الهدف: {goal[:100]}")
        
        # تنفيذ التجربة باستخدام النواة الذكية
        result = ""
        if self.core and self.core.is_loaded:
            result = self.core.generate_response(
                f"أنت عقل سيادي تجريبي. هدف هذه التجربة: {goal}\n\nقم بتنفيذ هذه المهمة وأبلغ بالنتائج:",
                max_length=500
            )
        else:
            result = f"تم تشغيل التجربة '{exp_name}'\nالهدف: {goal}\n\n(يتم تنفيذ التجربة في الخلفية، النتيجة ستظهر قريباً)"
        
        # تسجيل نتيجة التجربة
        log_file = exp_folder / "log.json"
        experiment_log = []
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                experiment_log = json.load(f)
        
        experiment_log.append({
            "timestamp": datetime.now().isoformat(),
            "goal": goal,
            "result": result[:500],
            "executed_by": "sovereign" if is_sovereign else "user"
        })
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(experiment_log[-20:], f, ensure_ascii=False, indent=2)
        
        self._log_event("experiment_complete", f"اكتملت تجربة: {exp_name}")
        
        return f"🧪 **نتيجة التجربة '{exp_name}'**\n\n📋 الهدف: {goal}\n\n📊 النتيجة:\n{result}\n\n✅ تم تسجيل التجربة في سجل التجارب."
    
    def _list_available_experiments(self) -> str:
        """عرض قائمة التجارب المتاحة"""
        if not EXPERIMENTS_DIR.exists():
            return "لا توجد تجارب متاحة حالياً."
        
        experiments = []
        for exp_folder in EXPERIMENTS_DIR.iterdir():
            if exp_folder.is_dir():
                config_file = exp_folder / "config.json"
                if config_file.exists():
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            config = json.load(f)
                        goal = config.get("goal", "لا يوجد وصف")[:60]
                        experiments.append(f"  • **{exp_folder.name}** - {goal}")
                    except:
                        experiments.append(f"  • **{exp_folder.name}**")
                else:
         
