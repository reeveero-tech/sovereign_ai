# backend/sovereign/agent_ledger.py
# سجل أفعال الوكيل (Agent Ledger) — المرحلة 6 من ROADMAP_V2
#
# المبدأ: كل جولة من الوكيل التقني يجب أن تُوثّق — لا أفعال خفية.
#
# هذا السجل يسجل كل تعديل يقوم به الوكيل التقني على المشروع:
# - الملفات المُضافة/المُعدّلة
# - الاختبارات المُضافة
# - الالتزامات (commits)
# - النتيجة (نجاح/فشل)
#
# القاعدة الصارمة: السجل إلحافي (append-only) — لا يُحذف منه سطر
# أبدًا (نفس قاعدة HISTORY.jsonl و ledger.jsonl).
#
# التخزين: data/sovereign_core/agent_ledger.jsonl

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("sovereign.agent_ledger")

# أنواع الأفعال
ACTION_TYPES = [
    "FILE_CREATED",       # ملف جديد
    "FILE_MODIFIED",       # ملف معدّل
    "FILE_DELETED",       # ملف محذوف (ممنوع — لكن يُسجل إذا حدث)
    "TEST_ADDED",         # اختبار جديد
    "TEST_MODIFIED",      # اختبار معدّل
    "COMMIT_CREATED",     # التزام جديد
    "PUSH_EXECUTED",      # دفع إلى remote
    "ENDPOINT_ADDED",     # نقطة نهاية جديدة
    "ENDPOINT_MODIFIED",  # نقطة نهاية معدّلة
    "MODULE_CREATED",     # وحدة جديدة
    "BUG_FIXED",          # إصلاح خطأ
    "FEATURE_ADDED",      # ميزة جديدة
    "INVARIANT_ADDED",    # اختبار ثابت جديد
    "CONFIG_CHANGED",      # تغيير إعدادات
    "OTHER",              # غير مصنف
]


@dataclass
class AgentAction:
    """فعل واحد قام به الوكيل التقني."""
    action_id: str           # sha256 أول 16 حرفًا
    action_type: str         # نوع الفعل (من ACTION_TYPES)
    description: str         # وصف الفعل
    files_affected: List[str] = field(default_factory=list)  # الملفات المتأثرة
    tests_added: int = 0     # عدد الاختبارات المُضافة
    tests_passed: int = 0    # عدد الاختبارات الناجحة
    commit_hash: Optional[str] = None  # hash الالتزام (إذا وُجد)
    timestamp: float = 0.0   # وقت الفعل
    result: str = "success"  # success / failure / partial
    metadata: Dict = field(default_factory=dict)  # بيانات إضافية

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentAction":
        return cls(**data)


class AgentLedger:
    """سجل أفعال الوكيل التقني (إلحافي — لا حذف)."""

    def __init__(self, ledger_path: Optional[Path] = None):
        if ledger_path is None:
            # المسار الافتراضي — يحترم SOVEREIGN_DATA_ROOT للعزل
            import os
            data_root = os.getenv("SOVEREIGN_DATA_ROOT")
            if data_root:
                base = Path(data_root)
            else:
                # جذر المستودع
                repo_root = Path(__file__).resolve().parent.parent.parent
                base = repo_root / "data"

            self.ledger_path = base / "sovereign_core" / "agent_ledger.jsonl"
        else:
            self.ledger_path = ledger_path

        # ضمان وجود المجلد
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # ضمان وجود الملف (إنشاء فارغ إذا لم يوجد)
        if not self.ledger_path.exists():
            self.ledger_path.touch()
            logger.info("✅ Agent Ledger initialized: %s", self.ledger_path)

    # ============================================================
    # تسجيل الأفعال
    # ============================================================

    def record_action(
        self,
        action_type: str,
        description: str,
        files_affected: Optional[List[str]] = None,
        tests_added: int = 0,
        tests_passed: int = 0,
        commit_hash: Optional[str] = None,
        result: str = "success",
        metadata: Optional[Dict] = None,
    ) -> AgentAction:
        """
        يُسجّل فعلًا جديدًا في السجل (إلحافي — لا حذف).

        Args:
            action_type: نوع الفعل (من ACTION_TYPES)
            description: وصف الفعل
            files_affected: الملفات المتأثرة
            tests_added: عدد الاختبارات المُضافة
            tests_passed: عدد الاختبارات الناجحة
            commit_hash: hash الالتزام (إذا وُجد)
            result: نتيجة الفعل (success/failure/partial)
            metadata: بيانات إضافية

        Returns:
            AgentAction: الفعل المُسجّل
        """
        if action_type not in ACTION_TYPES:
            logger.warning(
                "⚠️ Unknown action_type %r — using OTHER", action_type
            )
            action_type = "OTHER"

        # حساب action_id (sha256 من المحتوى)
        content = json.dumps({
            "action_type": action_type,
            "description": description,
            "timestamp": time.time(),
            "files": files_affected or [],
        }, sort_keys=True)
        action_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        action = AgentAction(
            action_id=action_id,
            action_type=action_type,
            description=description,
            files_affected=files_affected or [],
            tests_added=tests_added,
            tests_passed=tests_passed,
            commit_hash=commit_hash,
            timestamp=time.time(),
            result=result,
            metadata=metadata or {},
        )

        # الإلحاق (append-only)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(action.to_dict(), ensure_ascii=False) + "\n")

        logger.info(
            "📝 Agent action recorded: %s (%s) — %s",
            action_id, action_type, description[:50]
        )

        return action

    # ============================================================
    # قراءة السجل
    # ============================================================

    def read_actions(self) -> List[AgentAction]:
        """يُعيد كل الأفعال المسجلة (مرتبة زمنيًا)."""
        actions = []

        if not self.ledger_path.exists():
            return actions

        content = self.ledger_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.rstrip()
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                actions.append(AgentAction.from_dict(data))
            except json.JSONDecodeError as e:
                logger.error("❌ Agent ledger corrupted line: %s", e)

        # ترتيب زمني
        actions.sort(key=lambda a: a.timestamp)
        return actions

    def get_stats(self) -> Dict:
        """يُعيد إحصائيات السجل."""
        actions = self.read_actions()

        stats = {
            "total_actions": len(actions),
            "by_type": {},
            "by_result": {},
            "total_files_affected": 0,
            "total_tests_added": 0,
            "total_tests_passed": 0,
            "total_commits": 0,
            "first_action": None,
            "last_action": None,
        }

        for action in actions:
            # حسب النوع
            stats["by_type"][action.action_type] = (
                stats["by_type"].get(action.action_type, 0) + 1
            )

            # حسب النتيجة
            stats["by_result"][action.result] = (
                stats["by_result"].get(action.result, 0) + 1
            )

            # الملفات
            stats["total_files_affected"] += len(action.files_affected)

            # الاختبارات
            stats["total_tests_added"] += action.tests_added
            stats["total_tests_passed"] += action.tests_passed

            # الالتزامات
            if action.commit_hash:
                stats["total_commits"] += 1

        # أول و آخر فعل
        if actions:
            stats["first_action"] = actions[0].timestamp
            stats["last_action"] = actions[-1].timestamp

        return stats

    def get_actions_by_type(self, action_type: str) -> List[AgentAction]:
        """يُعيد كل الأفعال من نوع معين."""
        return [
            a for a in self.read_actions()
            if a.action_type == action_type
        ]

    def get_recent_actions(self, limit: int = 10) -> List[AgentAction]:
        """يُعيد آخر N فعل."""
        actions = self.read_actions()
        return actions[-limit:]

    # ============================================================
    # فحص النزاهة
    # ============================================================

    def verify_integrity(self) -> Dict:
        """
        يتحقق من نزاهة السجل:
        - كل سطر JSON صالح
        - كل action_id فريد
        - لا أفعال بدون timestamp
        """
        issues = []

        if not self.ledger_path.exists():
            return {"valid": False, "issues": ["ledger file not found"]}

        content = self.ledger_path.read_text(encoding="utf-8")
        lines = [l for l in content.split("\n") if l.strip()]

        action_ids = set()
        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                issues.append(f"line {i+1} corrupted: {e}")
                continue

            # فحص action_id
            aid = data.get("action_id")
            if not aid:
                issues.append(f"line {i+1} missing action_id")
            elif aid in action_ids:
                issues.append(f"line {i+1} duplicate action_id: {aid}")
            else:
                action_ids.add(aid)

            # فحص timestamp
            if not data.get("timestamp"):
                issues.append(f"line {i+1} missing timestamp")

        return {
            "valid": len(issues) == 0,
            "total_lines": len(lines),
            "unique_ids": len(action_ids),
            "issues": issues,
        }

    # ============================================================
    # تقرير
    # ============================================================

    def full_report(self) -> Dict:
        """يُعيد تقريرًا شاملًا عن السجل."""
        stats = self.get_stats()
        integrity = self.verify_integrity()
        recent = self.get_recent_actions(10)

        return {
            "stats": stats,
            "integrity": integrity,
            "recent_actions": [
                {
                    "action_id": a.action_id,
                    "action_type": a.action_type,
                    "description": a.description,
                    "timestamp": a.timestamp,
                    "result": a.result,
                }
                for a in recent
            ],
            "ledger_path": str(self.ledger_path),
        }
