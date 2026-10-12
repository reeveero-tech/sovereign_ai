# backend/simulation/simulation_environment.py
# 🌐 مدير بيئات المحاكاة الجبار - إدارة البيئات والتكوينات المتقدمة
# الإصدار: 3.0.0 - بيئات محاكاة معقدة، تكوينات ديناميكية

"""
مدير بيئات المحاكاة للعقل السيادي.

الفلسفة:
- البيئة تحدد قواعد اللعبة
- التكوين الجيد هو نصف المحاكاة
- الحالة الابتدائية تحدد المسار
- التوليد التلقائي للتكوينات يوفر الوقت
- التحقق من الصلاحية يمنع الأخطاء

هذه ليست مجرد بيئات. هذه هي عوالم المحاكاة المتعددة.
"""

import json
import hashlib
import time
import threading
import math
import secrets
import random
import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict
import itertools

try:
    from ..memory.core import get_core, EventType
    from ...config import DATA_DIR
except ImportError:
    from memory.core import get_core, EventType
    from config import DATA_DIR

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت وإعدادات بيئات المحاكاة
# ============================================================

ENV_DIR = DATA_DIR / "simulation" / "environments"
ENV_DIR.mkdir(parents=True, exist_ok=True)
ENV_LOG = ENV_DIR / "environment_log.jsonl"
ENV_STATE_FILE = ENV_DIR / "environment_state.json"
ENV_TEMPLATES_DIR = ENV_DIR / "templates"
ENV_PARAMS_DIR = ENV_DIR / "parameters"

ENV_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
ENV_PARAMS_DIR.mkdir(parents=True, exist_ok=True)

# أنواع البيئات
ENV_TYPE_SYSTEM = "system"              # بيئة النظام الكامل
ENV_TYPE_COGNITIVE = "cognitive"        # بيئة معرفية
ENV_TYPE_MEMORY = "memory"              # بيئة ذاكرة
ENV_TYPE_DEFENSE = "defense"            # بيئة دفاعية
ENV_TYPE_SOVEREIGN = "sovereign"        # بيئة سيادية
ENV_TYPE_PREDICTIVE = "predictive"      # بيئة تنبؤية
ENV_TYPE_HYBRID = "hybrid"              # بيئة هجينة

# حالات البيئة
ENV_STATUS_ACTIVE = "active"
ENV_STATUS_INACTIVE = "inactive"
ENV_STATUS_DEPRECATED = "deprecated"
ENV_STATUS_ARCHIVED = "archived"


@dataclass
class EnvironmentTemplate:
    """قالب بيئة محاكاة"""
    id: str
    name: str
    type: str
    description: str
    version: int
    default_parameters: Dict[str, Any]
    parameter_constraints: Dict[str, Tuple[float, float]]
    initial_state: Dict[str, Any]
    state_variables: List[str]
    tags: List[str]
    status: str
    created_at: float
    updated_at: float
    created_by: str


@dataclass
class ParameterSet:
    """مجموعة معلمات"""
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    template_id: str
    created_at: float
    validated: bool
    validation_issues: List[str]


@dataclass
class EnvironmentInstance:
    """مثيل بيئة جاهز للمحاكاة"""
    id: str
    name: str
    template_id: str
    parameter_set_id: Optional[str]
    parameters: Dict[str, Any]
    initial_state: Dict[str, Any]
    state: Dict[str, Any]
    created_at: float
    last_used: Optional[float]
    metadata: Dict[str, Any]


@dataclass
class ValidationReport:
    """تقرير تحقق"""
    valid: bool
    issues: List[str]
    warnings: List[str]
    details: Dict[str, Any]
    timestamp: float


# ============================================================
# مدير بيئات المحاكاة الجبار
# ============================================================

class SimulationEnvironmentManager:
    """
    مدير بيئات المحاكاة الجبار - إدارة البيئات والتكوينات المتقدمة.
    
    المبادئ:
    1. البيئة تحدد قواعد اللعبة
    2. التكوين الجيد هو نصف المحاكاة
    3. الحالة الابتدائية تحدد المسار
    4. التوليد التلقائي للتكوينات يوفر الوقت
    5. التحقق من الصلاحية يمنع الأخطاء
    """
    # -------------------------
    # RESET — إعادة تهيئة كاملة لبيئة المحاكاة
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة لبيئة المحاكاة.
        """

        # مسح حالة البيئة
        self.environment_state = {}
        self.environment_history = []

        # إعادة تحميل الفهرس
        self._index = self._load_index()

        # إعادة السياسات الافتراضية
        self.policies = {
            "environment_noise": 0.1,
            "max_environment_changes": 10,
            "stability_threshold": 0.5,
        }

        # تسجيل عملية إعادة التهيئة
        self.core.append_event("simulation::environment::reset", {
            "timestamp": _now_iso(),
            "status": "simulation_environment_reset"
        })
    def __init__(self):
        self.core = get_core()
        
        # سجلات البيئات
        self.templates: Dict[str, EnvironmentTemplate] = {}
        self.parameter_sets: Dict[str, ParameterSet] = {}
        self.instances: Dict[str, EnvironmentInstance] = {}
        
        # الحالة الحالية
        self.active_template: Optional[str] = None
        self.active_parameter_set: Optional[str] = None
        
        # خلفيات الإدارة
        self._active = True
        self._validation_loop = threading.Thread(target=self._continuous_validation, daemon=True)
        self._validation_loop.start()
        
        self._backup_loop = threading.Thread(target=self._periodic_backup, daemon=True)
        self._backup_loop.start()
        
        # تحميل الحالة
        self._load_state()
        self._load_templates()
        self._load_parameter_sets()
        
        logger.warning("🌐 مدير بيئات المحاكاة الجبار جاهز - عوالم محاكاة متعددة")
    
    # ============================================================
    # إدارة القوالب
    # ============================================================
    
    def create_template(self, name: str, type: str, description: str,
                        default_parameters: Dict[str, Any],
                        initial_state: Dict[str, Any],
                        parameter_constraints: Dict[str, Tuple[float, float]] = None,
                        state_variables: List[str] = None,
                        tags: List[str] = None) -> EnvironmentTemplate:
        """
        إنشاء قالب بيئة جديد.
        """
        template_id = f"env_tpl_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        if parameter_constraints is None:
            parameter_constraints = {}
        if state_variables is None:
            state_variables = list(initial_state.keys())
        if tags is None:
            tags = []
        
        template = EnvironmentTemplate(
            id=template_id,
            name=name,
            type=type,
            description=description,
            version=1,
            default_parameters=default_parameters,
            parameter_constraints=parameter_constraints,
            initial_state=initial_state,
            state_variables=state_variables,
            tags=tags,
            status=ENV_STATUS_ACTIVE,
            created_at=time.time(),
            updated_at=time.time(),
            created_by="system"
        )
        
        self.templates[template_id] = template
        
        # حفظ القالب
        self._save_template(template)
        
        # تسجيل
        self.core.append_event(
            event_type="environment::template_created",
            payload={
                "template_id": template_id[:16],
                "name": name,
                "type": type
            }
        )
        
        logger.info(f"📋 قالب بيئة جديد: {name} (نوع: {type})")
        
        return template
    
    def update_template(self, template_id: str, **kwargs) -> Optional[EnvironmentTemplate]:
        """
        تحديث قالب بيئة.
        """
        template = self.templates.get(template_id)
        if not template:
            return None
        
        changed = False
        for key, value in kwargs.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)
                changed = True
        
        if changed:
            template.version += 1
            template.updated_at = time.time()
            self._save_template(template)
            
            logger.info(f"📝 تحديث قالب: {template.name} (نسخة {template.version})")
        
        return template
    
    def clone_template(self, template_id: str, new_name: str) -> Optional[EnvironmentTemplate]:
        """
        استنساخ قالب بيئة.
        """
        original = self.templates.get(template_id)
        if not original:
            return None
        
        # إنشاء نسخة عميقة
        clone = copy.deepcopy(original)
        clone.id = f"env_tpl_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        clone.name = new_name
        clone.version = 1
        clone.created_at = time.time()
        clone.updated_at = time.time()
        clone.status = ENV_STATUS_ACTIVE
        
        self.templates[clone.id] = clone
        self._save_template(clone)
        
        logger.info(f"📋 استنساخ قالب: {original.name} → {new_name}")
        
        return clone
    
    def delete_template(self, template_id: str) -> bool:
        """
        حذف قالب بيئة.
        """
        if template_id in self.templates:
            template = self.templates.pop(template_id)
            template.status = ENV_STATUS_ARCHIVED
            
            # حذف الملف
            template_file = ENV_TEMPLATES_DIR / f"{template_id}.json"
            if template_file.exists():
                template_file.unlink()
            
            logger.info(f"🗑️ حذف قالب: {template.name}")
            return True
        
        return False
    
    def list_templates(self, type_filter: str = None, tag_filter: str = None) -> List[Dict]:
        """
        قائمة القوالب المتاحة.
        """
        templates = self.templates.values()
        
        if type_filter:
            templates = [t for t in templates if t.type == type_filter]
        
        if tag_filter:
            templates = [t for t in templates if tag_filter in t.tags]
        
        return [
            {
                "id": t.id[:16],
                "name": t.name,
                "type": t.type,
                "version": t.version,
                "status": t.status,
                "tags": t.tags
            }
            for t in templates
        ]
    
    # ============================================================
    # إدارة مجموعات المعلمات
    # ============================================================
    
    def create_parameter_set(self, name: str, description: str,
                             parameters: Dict[str, Any],
                             template_id: str) -> ParameterSet:
        """
        إنشاء مجموعة معلمات جديدة.
        """
        param_id = f"env_ps_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        param_set = ParameterSet(
            id=param_id,
            name=name,
            description=description,
            parameters=parameters,
            template_id=template_id,
            created_at=time.time(),
            validated=False,
            validation_issues=[]
        )
        
        self.parameter_sets[param_id] = param_set
        
        # التحقق من الصلاحية
        validation = self.validate_parameter_set(param_id)
        param_set.validated = validation.valid
        param_set.validation_issues = validation.issues
        
        # حفظ مجموعة المعلمات
        self._save_parameter_set(param_set)
        
        logger.info(f"📊 مجموعة معلمات جديدة: {name} (صالح: {validation.valid})")
        
        return param_set
    
    def generate_parameter_grid(self, template_id: str, 
                                 sweep_spec: Dict[str, List[Any]],
                                 name_prefix: str = "grid") -> List[ParameterSet]:
        """
        توليد شبكة معلمات (جداء ديكارتي).
        
        مثال: sweep_spec = {"noise": [0.01, 0.05, 0.1], "steps": [10, 20, 50]}
        """
        template = self.templates.get(template_id)
        if not template:
            return []
        
        generated_sets = []
        
        # توليد جميع التركيبات
        keys = list(sweep_spec.keys())
        values = list(sweep_spec.values())
        
        for combination in itertools.product(*values):
            params = template.default_parameters.copy()
            for i, key in enumerate(keys):
                params[key] = combination[i]
            
            # إنشاء اسم فريد
            name = f"{name_prefix}_" + "_".join(f"{k}{v}" for k, v in zip(keys, combination))
            
            param_set = self.create_parameter_set(
                name=name,
                description=f"توليد تلقائي من قالب {template.name}",
                parameters=params,
                template_id=template_id
            )
            generated_sets.append(param_set)
        
        logger.info(f"📊 توليد {len(generated_sets)} مجموعة معلمات لقالب {template.name}")
        
        return generated_sets
    
    def update_parameter_set(self, param_id: str, parameters: Dict[str, Any]) -> Optional[ParameterSet]:
        """
        تحديث مجموعة معلمات.
        """
        param_set = self.parameter_sets.get(param_id)
        if not param_set:
            return None
        
        param_set.parameters.update(parameters)
        
        # إعادة التحقق
        validation = self.validate_parameter_set(param_id)
        param_set.validated = validation.valid
        param_set.validation_issues = validation.issues
        
        self._save_parameter_set(param_set)
        
        logger.info(f"📝 تحديث مجموعة معلمات: {param_set.name}")
        
        return param_set
    
    def delete_parameter_set(self, param_id: str) -> bool:
        """
        حذف مجموعة معلمات.
        """
        if param_id in self.parameter_sets:
            param_set = self.parameter_sets.pop(param_id)
            
            # حذف الملف
            param_file = ENV_PARAMS_DIR / f"{param_id}.json"
            if param_file.exists():
                param_file.unlink()
            
            logger.info(f"🗑️ حذف مجموعة معلمات: {param_set.name}")
            return True
        
        return False
    
    def list_parameter_sets(self, template_id: str = None) -> List[Dict]:
        """
        قائمة مجموعات المعلمات.
        """
        param_sets = self.parameter_sets.values()
        
        if template_id:
            param_sets = [p for p in param_sets if p.template_id == template_id]
        
        return [
            {
                "id": p.id[:16],
                "name": p.name,
                "parameters": p.parameters,
                "validated": p.validated,
                "template_id": p.template_id[:16]
            }
            for p in param_sets
        ]
    
    # ============================================================
    # التحقق من الصلاحية
    # ============================================================
    
    def validate_parameter_set(self, param_id: str) -> ValidationReport:
        """
        التحقق من صحة مجموعة معلمات.
        """
        param_set = self.parameter_sets.get(param_id)
        if not param_set:
            return ValidationReport(
                valid=False,
                issues=[f"مجموعة المعلمات غير موجودة: {param_id}"],
                warnings=[],
                details={},
                timestamp=time.time()
            )
        
        template = self.templates.get(param_set.template_id)
        if not template:
            return ValidationReport(
                valid=False,
                issues=[f"القالب غير موجود: {param_set.template_id}"],
                warnings=[],
                details={},
                timestamp=time.time()
            )
        
        issues = []
        warnings = []
        
        # التحقق من القيود
        for param, value in param_set.parameters.items():
            if param in template.parameter_constraints:
                min_val, max_val = template.parameter_constraints[param]
                if not (min_val <= value <= max_val):
                    issues.append(f"المعامل {param} = {value} خارج النطاق [{min_val}, {max_val}]")
        
        # التحقق من المعاملات المطلوبة
        for required_param in template.default_parameters.keys():
            if required_param not in param_set.parameters:
                warnings.append(f"المعامل المطلوب {required_param} غير موجود، سيتم استخدام الافتراضي")
        
        # تحذيرات إضافية
        for param, value in param_set.parameters.items():
            if isinstance(value, float):
                if value < 0 or value > 1:
                    warnings.append(f"المعامل {param} = {value} قد يكون خارج النطاق المتوقع (0-1)")
        
        valid = len(issues) == 0
        
        return ValidationReport(
            valid=valid,
            issues=issues,
            warnings=warnings,
            details={
                "param_set_id": param_id,
                "template_id": template.id,
                "parameters_count": len(param_set.parameters)
            },
            timestamp=time.time()
        )
    
    def validate_environment_instance(self, instance_id: str) -> ValidationReport:
        """
        التحقق من صحة مثيل بيئة.
        """
        instance = self.instances.get(instance_id)
        if not instance:
            return ValidationReport(
                valid=False,
                issues=[f"المثيل غير موجود: {instance_id}"],
                warnings=[],
                details={},
                timestamp=time.time()
            )
        
        issues = []
        warnings = []
        
        # التحقق من القالب
        template = self.templates.get(instance.template_id)
        if not template:
            issues.append(f"القالب غير موجود: {instance.template_id}")
        
        # التحقق من الحالة
        for var in template.state_variables if template else []:
            if var not in instance.state:
                warnings.append(f"متغير الحالة {var} غير موجود في المثيل")
        
        valid = len(issues) == 0
        
        return ValidationReport(
            valid=valid,
            issues=issues,
            warnings=warnings,
            details={
                "instance_id": instance_id,
                "template_id": instance.template_id,
                "state_size": len(instance.state)
            },
            timestamp=time.time()
        )
    
    def _continuous_validation(self):
        """تحقق مستمر من صحة البيئات"""
        while self._active:
            try:
                # التحقق من جميع مجموعات المعلمات
                for param_id in list(self.parameter_sets.keys()):
                    validation = self.validate_parameter_set(param_id)
                    if not validation.valid:
                        logger.warning(f"⚠️ مجموعة معلمات غير صالحة: {param_id[:16]} - {validation.issues}")
                
                time.sleep(300)  # كل 5 دقائق
            except Exception as e:
                logger.error(f"خطأ في التحقق المستمر: {e}")
                time.sleep(300)
    
    # ============================================================
    # بناء مثيلات البيئة
    # ============================================================
    
    def build_instance(self, template_id: str, param_set_id: str = None,
                       overrides: Dict[str, Any] = None,
                       instance_name: str = None) -> Optional[EnvironmentInstance]:
        """
        بناء مثيل بيئة جاهز للمحاكاة.
        """
        template = self.templates.get(template_id)
        if not template:
            logger.error(f"القالب غير موجود: {template_id}")
            return None
        
        # الحصول على المعلمات
        if param_set_id:
            param_set = self.parameter_sets.get(param_set_id)
            if not param_set:
                logger.error(f"مجموعة المعلمات غير موجودة: {param_set_id}")
                return None
            parameters = param_set.parameters.copy()
        else:
            parameters = template.default_parameters.copy()
        
        # تطبيق التجاوزات
        if overrides:
            parameters.update(overrides)
        
        # إنشاء المثيل
        instance_id = f"env_inst_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        instance = EnvironmentInstance(
            id=instance_id,
            name=instance_name or f"{template.name}_instance",
            template_id=template_id,
            parameter_set_id=param_set_id,
            parameters=parameters,
            initial_state=template.initial_state.copy(),
            state=template.initial_state.copy(),
            created_at=time.time(),
            last_used=None,
            metadata={
                "template_name": template.name,
                "template_version": template.version,
                "built_at": time.time()
            }
        )
        
        self.instances[instance_id] = instance
        
        # التحقق من الصلاحية
        validation = self.validate_environment_instance(instance_id)
        
        logger.info(f"🔧 بناء مثيل بيئة: {instance.name} (صالح: {validation.valid})")
        
        return instance
    
    def update_instance_state(self, instance_id: str, state_updates: Dict[str, Any]) -> bool:
        """
        تحديث حالة مثيل بيئة.
        """
        instance = self.instances.get(instance_id)
        if not instance:
            return False
        
        instance.state.update(state_updates)
        instance.last_used = time.time()
        
        return True
    
    def reset_instance(self, instance_id: str) -> bool:
        """
        إعادة تعيين مثيل بيئة إلى الحالة الابتدائية.
        """
        instance = self.instances.get(instance_id)
        if not instance:
            return False
        
        instance.state = instance.initial_state.copy()
        instance.last_used = time.time()
        
        logger.info(f"🔄 إعادة تعيين مثيل: {instance.name}")
        
        return True
    
    def delete_instance(self, instance_id: str) -> bool:
        """
        حذف مثيل بيئة.
        """
        if instance_id in self.instances:
            instance = self.instances.pop(instance_id)
            logger.info(f"🗑️ حذف مثيل: {instance.name}")
            return True
        
        return False
    
    def list_instances(self, template_id: str = None) -> List[Dict]:
        """
        قائمة مثيلات البيئة.
        """
        instances = self.instances.values()
        
        if template_id:
            instances = [i for i in instances if i.template_id == template_id]
        
        return [
            {
                "id": i.id[:16],
                "name": i.name,
                "template_id": i.template_id[:16],
                "state_size": len(i.state),
                "created_at": i.created_at,
                "last_used": i.last_used
            }
            for i in instances
        ]
    
    # ============================================================
    # إدارة الحالة
    # ============================================================
    
    def _save_template(self, template: EnvironmentTemplate):
        """حفظ قالب بيئة"""
        try:
            template_file = ENV_TEMPLATES_DIR / f"{template.id}.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template.__dict__, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ القالب: {e}")
    
    def _save_parameter_set(self, param_set: ParameterSet):
        """حفظ مجموعة معلمات"""
        try:
            param_file = ENV_PARAMS_DIR / f"{param_set.id}.json"
            with open(param_file, 'w', encoding='utf-8') as f:
                json.dump(param_set.__dict__, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ مجموعة المعلمات: {e}")
    
    def _load_templates(self):
        """تحميل القوالب"""
        try:
            for template_file in ENV_TEMPLATES_DIR.glob("*.json"):
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template = EnvironmentTemplate(**data)
                    self.templates[template.id] = template
            logger.info(f"📂 تم تحميل {len(self.templates)} قالباً")
        except Exception as e:
            logger.error(f"خطأ في تحميل القوالب: {e}")
    
    def _load_parameter_sets(self):
        """تحميل مجموعات المعلمات"""
        try:
            for param_file in ENV_PARAMS_DIR.glob("*.json"):
                with open(param_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    param_set = ParameterSet(**data)
                    self.parameter_sets[param_set.id] = param_set
            logger.info(f"📂 تم تحميل {len(self.parameter_sets)} مجموعة معلمات")
        except Exception as e:
            logger.error(f"خطأ في تحميل مجموعات المعلمات: {e}")
    
    def _save_state(self):
        """حفظ حالة مدير البيئات"""
        try:
            state = {
                "templates_count": len(self.templates),
                "parameter_sets_count": len(self.parameter_sets),
                "instances_count": len(self.instances),
                "active_template": self.active_template,
                "active_parameter_set": self.active_parameter_set,
                "saved_at": time.time()
            }
            # M1: كتابة ذرية عبر ملف مؤقت لتجنب قراءة ملف نصف مكتوب
            tmp = ENV_STATE_FILE.with_suffix('.json.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            tmp.replace(ENV_STATE_FILE)
        except Exception as e:
            logger.error(f"خطأ في حفظ حالة مدير البيئات: {e}")
    
    def _load_state(self):
        """تحميل حالة مدير البيئات"""
        try:
            if ENV_STATE_FILE.exists():
                with open(ENV_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.active_template = state.get("active_template")
                    self.active_parameter_set = state.get("active_parameter_set")
                logger.info("📂 تم تحميل حالة مدير البيئات")
        except Exception as e:
            logger.error(f"خطأ في تحميل حالة مدير البيئات: {e}")
    
    def _periodic_backup(self):
        """نسخ احتياطي دوري"""
        while self._active:
            try:
                self._save_state()
                time.sleep(3600)  # كل ساعة
            except Exception as e:
                logger.error(f"خطأ في النسخ الاحتياطي: {e}")
                time.sleep(3600)
    
    # ============================================================
    # دورة مدير البيئات
    # ============================================================
    
    def environment_cycle(self) -> Dict[str, Any]:
        """
        دورة مدير البيئات الكاملة.
        """
        return {
            "templates": len(self.templates),
            "parameter_sets": len(self.parameter_sets),
            "instances": len(self.instances),
            "active_template": self.active_template[:16] if self.active_template else None,
            "timestamp": time.time()
        }
    
    # ============================================================
    # واجهات التحكم
    # ============================================================
    
    def get_environment_status(self) -> Dict[str, Any]:
        """الحالة الحالية لمدير البيئات"""
        return {
            "total_templates": len(self.templates),
            "active_templates": len([t for t in self.templates.values() if t.status == ENV_STATUS_ACTIVE]),
            "total_parameter_sets": len(self.parameter_sets),
            "validated_parameter_sets": len([p for p in self.parameter_sets.values() if p.validated]),
            "total_instances": len(self.instances),
            "active_instances": len([i for i in self.instances.values() if i.last_used and time.time() - i.last_used < 3600]),
            "timestamp": time.time()
        }
    
    def get_templates_by_type(self) -> Dict[str, int]:
        """القوالب حسب النوع"""
        type_counts = defaultdict(int)
        for template in self.templates.values():
            type_counts[template.type] += 1
        return dict(type_counts)
    
    def export_environment(self, instance_id: str) -> Optional[Dict]:
        """تصدير بيئة كاملة"""
        instance = self.instances.get(instance_id)
        if not instance:
            return None
        
        return {
            "instance": instance.__dict__,
            "template": self.templates.get(instance.template_id).__dict__ if instance.template_id in self.templates else None,
            "parameter_set": self.parameter_sets.get(instance.parameter_set_id).__dict__ if instance.parameter_set_id in self.parameter_sets else None,
            "exported_at": time.time()
        }
    
    def get_environment_quote(self) -> str:
        """اقتباس عن البيئات"""
        quotes = [
            "البيئة تحدد قواعد اللعبة.",
            "التكوين الجيد هو نصف المحاكاة.",
            "الحالة الابتدائية تحدد المسار.",
            "عوالم متعددة للمحاكاة المتعددة.",
            "التحقق من الصلاحية يمنع الأخطاء.",
            "بيئات مختلفة لسيناريوهات مختلفة.",
            "التوليد التلقائي يوفر الوقت والجهد."
        ]
        return random.choice(quotes)
    
    def stop(self):
        """إيقاف مدير البيئات"""
        self._active = False
        self._save_state()
        logger.info("🛑 إيقاف مدير بيئات المحاكاة")


# ============================================================
# الـ Singleton
# ============================================================

_env_manager_instance: Optional[SimulationEnvironmentManager] = None
_env_manager_lock = threading.Lock()


def get_simulation_environment_manager() -> SimulationEnvironmentManager:
    """الحصول على النسخة الوحيدة من مدير بيئات المحاكاة"""
    global _env_manager_instance
    if _env_manager_instance is None:
        with _env_manager_lock:
            if _env_manager_instance is None:
                _env_manager_instance = SimulationEnvironmentManager()
    return _env_manager_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🌐 مدير بيئات المحاكاة الجبار - عوالم محاكاة متعددة")
    print("=" * 80 + "\n")
    
    env_manager = get_simulation_environment_manager()
    
    # 1) إنشاء قالب
    print("📋 إنشاء قالب بيئة...")
    template = env_manager.create_template(
        name="النظام السيادي القياسي",
        type=ENV_TYPE_SYSTEM,
        description="بيئة قياسية لمحاكاة النظام السيادي الكامل",
        default_parameters={
            "noise_scale": 0.05,
            "drift_rate": 0.02,
            "volatility": 0.1
        },
        initial_state={
            "stability": 0.7,
            "alignment": 0.8,
            "health": 0.75,
            "growth": 0.6
        },
        parameter_constraints={
            "noise_scale": (0.01, 0.2),
            "drift_rate": (0.0, 0.1),
            "volatility": (0.05, 0.3)
        },
        tags=["system", "standard"]
    )
    print(f"   معرف القالب: {template.id[:16]}...")
    print(f"   الاسم: {template.name}")
    print(f"   النوع: {template.type}")
    
    # 2) إنشاء مجموعة معلمات
    print("\n📊 إنشاء مجموعة معلمات...")
    param_set = env_manager.create_parameter_set(
        name="إعدادات منخفضة الضوضاء",
        description="معاملات لبيئة مستقرة",
        parameters={"noise_scale": 0.02, "drift_rate": 0.01},
        template_id=template.id
    )
    print(f"   معرف المجموعة: {param_set.id[:16]}...")
    print(f"   الاسم: {param_set.name}")
    print(f"   صالح: {param_set.validated}")
    
    # 3) توليد شبكة معلمات
    print("\n🔧 توليد شبكة معلمات...")
    grid_sets = env_manager.generate_parameter_grid(
        template_id=template.id,
        sweep_spec={
            "noise_scale": [0.01, 0.05, 0.1],
            "drift_rate": [0.01, 0.02, 0.05]
        },
        name_prefix="grid_test"
    )
    print(f"   تم توليد {len(grid_sets)} مجموعة")
    
    # 4) بناء مثيل بيئة
    print("\n🔧 بناء مثيل بيئة...")
    instance = env_manager.build_instance(
        template_id=template.id,
        param_set_id=param_set.id,
        instance_name="اختبار الأداء"
    )
    print(f"   معرف المثيل: {instance.id[:16]}...")
    print(f"   الاسم: {instance.name}")
    print(f"   الحالة الأولية: {instance.initial_state}")
    
    # 5) تحديث حالة المثيل
    print("\n🔄 تحديث حالة المثيل...")
    env_manager.update_instance_state(instance.id, {"stability": 0.85, "growth": 0.7})
    print(f"   الحالة الجديدة: {instance.state}")
    
    # 6) التحقق من الصلاحية
    print("\n✅ التحقق من الصلاحية...")
    validation = env_manager.validate_parameter_set(param_set.id)
    print(f"   صالح: {validation.valid}")
    if validation.warnings:
        print(f"   تحذيرات: {validation.warnings}")
    
    # 7) حالة مدير البيئات
    print("\n📊 حالة مدير البيئات:")
    status = env_manager.get_environment_status()
    print(f"   القوالب: {status['total_templates']}")
    print(f"   القوالب النشطة: {status['active_templates']}")
    print(f"   مجموعات المعلمات: {status['total_parameter_sets']}")
    print(f"   المجموعات الصالحة: {status['validated_parameter_sets']}")
    print(f"   مثيلات البيئة: {status['total_instances']}")
    
    # 8) القوالب حسب النوع
    print("\n📂 القوالب حسب النوع:")
    by_type = env_manager.get_templates_by_type()
    for t, count in by_type.items():
        print(f"   {t}: {count}")
    
    # 9) قائمة القوالب
    print("\n📋 قائمة القوالب:")
    templates = env_manager.list_templates()
    for t in templates[:3]:
        print(f"   {t['name']} ({t['type']}) - {t['status']}")
    
    # 10) قائمة مثيلات البيئة
    print("\n🔧 مثيلات البيئة:")
    instances = env_manager.list_instances()
    for i in instances:
        print(f"   {i['name']}: {i['id']}")
    
    # 11) تصدير بيئة
    print("\n📤 تصدير بيئة...")
    exported = env_manager.export_environment(instance.id)
    if exported:
        print(f"   تم تصدير مثيل {exported['instance']['name']}")
    
    # 12) اقتباس
    print(f"\n💭 {env_manager.get_environment_quote()}")
    
    print("\n" + "=" * 80)
    print("✅ مدير بيئات المحاكاة الجبار جاهز - عوالم محاكاة متعددة")
    print("=" * 80)
