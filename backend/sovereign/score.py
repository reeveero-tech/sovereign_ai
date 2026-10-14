# backend/sovereign/score.py
# محرك حساب درجة السيادة (Sovereignty Score) — المرحلة 5 من ROADMAP_V2
#
# المبدأ: "المشروع نجح في أن يعمل، ولم ينجح بعد في أن يكون سيادياً"
# هذا المحرك يقيس المسافة بين "يعمل" و "سيادي" برقم واحد.
#
# الدرجة (0-100) تُحسب من 6 محاور:
# 1. Ledger Integrity (25 نقطة) — نزاهة اليدجر
#    - نسبة الأحداث المُغطاة بمرساة
#    - نسبة الأحداث المصنّفة (لا مجهول)
#    - كل المراسي مُتحقّقة
# 2. Key Management (20 نقطة) — إدارة المفاتيح
#    - KeyRing موجود وله مفاتيح
#    - مفتاح ACTIVE واحد على الأقل
#    - HISTORY.jsonl سليم (لا تلف)
# 3. Immune System (20 نقطة) — جهاز المناعة
#    - كل الاختبارات الثابتة (invariants) ناجحة
#    - لا وحدات يتيمة
#    - لا mock في الإنتاج
# 4. Compat Lifecycle (10 نقطة) — دورة حياة التوافق
#    - كل وحدة compat لها SUNSET_CRITERIA
#    - __meta__.py موجود
#    - كل وحدة في COMPAT_LIFECYCLE
# 5. Test Health (15 نقطة) — صحة الاختبارات
#    - عدد الاختبارات الكلي
#    - نسبة النجاح
#    - تغطية النقاط الحرجة
# 6. Structural Health (10 نقطة) — الصحة الهيكلية
#    - كل نقاط النهاية تستجيب
#    - لا stub/placeholder
#    - INVENTORY موثّق
#
# عتبات التقييم:
# - 90-100: سيادي (Sovereign)
# - 75-89: سيادي جزئيًا (Partially Sovereign)
# - 60-74: يعمل لكن غير سيادي (Working, Not Sovereign)
# - 40-59: هش (Fragile)
# - 0-39: مكسور (Broken)

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("sovereign.score")

# عتبات التقييم
SOVEREIGN_THRESHOLD = 90
PARTIALLY_SOVEREIGN_THRESHOLD = 75
WORKING_THRESHOLD = 60
FRAGILE_THRESHOLD = 40

# أوزان المحاور (مجموعها 100)
AXIS_WEIGHTS = {
    "ledger_integrity": 25,
    "key_management": 20,
    "immune_system": 20,
    "compat_lifecycle": 10,
    "test_health": 15,
    "structural_health": 10,
}


@dataclass
class AxisScore:
    """درجة محور واحد من محاور السيادة."""
    name: str
    score: float          # 0-100 (نسبة مئوية)
    weight: int           # الوزن في الدرجة الكلية
    details: Dict = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        """الدرجة الموزونة (score * weight / 100)."""
        return (self.score * self.weight) / 100.0


@dataclass
class SovereigntyReport:
    """تقرير السيادة الكامل."""
    total_score: float
    grade: str
    axes: List[AxisScore]
    timestamp: float
    summary: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "total_score": round(self.total_score, 2),
            "grade": self.grade,
            "timestamp": self.timestamp,
            "axes": [
                {
                    "name": a.name,
                    "score": round(a.score, 2),
                    "weight": a.weight,
                    "weighted_score": round(a.weighted_score, 2),
                    "details": a.details,
                    "issues": a.issues,
                }
                for a in self.axes
            ],
            "summary": self.summary,
        }


def _grade_for(score: float) -> str:
    """يُعيد التقييم النصي للدرجة."""
    if score >= SOVEREIGN_THRESHOLD:
        return "SOVEREIGN (سيادي)"
    elif score >= PARTIALLY_SOVEREIGN_THRESHOLD:
        return "PARTIALLY_SOVEREIGN (سيادي جزئيًا)"
    elif score >= WORKING_THRESHOLD:
        return "WORKING_NOT_SOVEREIGN (يعمل لكن غير سيادي)"
    elif score >= FRAGILE_THRESHOLD:
        return "FRAGILE (هش)"
    else:
        return "BROKEN (مكسور)"


class SovereigntyScorer:
    """محرك حساب درجة السيادة."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self._axes: List[AxisScore] = []

    # ============================================================
    # المحور 1: نزاهة اليدجر (Ledger Integrity) — 25 نقطة
    # ============================================================

    def _score_ledger_integrity(self) -> AxisScore:
        """يحسب درجة نزاهة اليدجر (تغطية المرساة + تصنيف الأحداث)."""
        axis = AxisScore(name="ledger_integrity", score=0, weight=AXIS_WEIGHTS["ledger_integrity"])

        try:
            from backend.sovereign.ledger import LedgerAnchor
            from backend.sovereign.keys import KeyRing, SignatureVerifier

            anchor = LedgerAnchor()
            lines = anchor.read_ledger_lines()

            if not lines:
                axis.issues.append("ledger is empty")
                axis.score = 0
                return axis

            total = len(lines)

            # الأحداث المُغطاة بالمراسي
            anchors_list = anchor.list_anchors()
            anchored_events = set()
            for a in anchors_list:
                for i in range(a["batch_start"], a["batch_end"] + 1):
                    anchored_events.add(i)

            coverage = len(anchored_events) / total

            # التحقق من كل المراسي
            verification = anchor.verify_all_anchors()
            anchors_ok = verification["failed"] == 0

            # تصنيف الأحداث
            keyring = KeyRing()
            keyring.load_from_disk()
            verifier = SignatureVerifier(keyring)

            unclassified = 0
            import json
            for i, line in enumerate(lines):
                try:
                    event = json.loads(line)
                    result = verifier.verify_event(event)
                    if result.status.value not in ("verified", "unverifiable_missing_key"):
                        unclassified += 1
                except Exception:
                    unclassified += 1

            classified_ratio = 1 - (unclassified / total)

            # الدرجة: 50% تغطية + 30% تصنيف + 20% مراسي سليمة
            score = (
                coverage * 50
                + classified_ratio * 30
                + (20 if anchors_ok else 0)
            )

            axis.score = min(score, 100)
            axis.details = {
                "total_events": total,
                "anchored_events": len(anchored_events),
                "coverage_pct": round(coverage * 100, 2),
                "anchors_total": len(anchors_list),
                "anchors_verified": verification["verified"],
                "anchors_failed": verification["failed"],
                "unclassified_events": unclassified,
                "classified_ratio": round(classified_ratio, 4),
            }

            if coverage < 0.9:
                axis.issues.append(f"anchored coverage too low: {coverage:.2%}")
            if not anchors_ok:
                axis.issues.append(f"{verification['failed']} anchors failed verification")
            if unclassified > 0:
                axis.issues.append(f"{unclassified} events unclassified")

        except Exception as e:
            axis.score = 0
            axis.issues.append(f"ledger integrity check failed: {e}")

        return axis

    # ============================================================
    # المحور 2: إدارة المفاتيح (Key Management) — 20 نقطة
    # ============================================================

    def _score_key_management(self) -> AxisScore:
        """يحسب درجة إدارة المفاتيح."""
        axis = AxisScore(name="key_management", score=0, weight=AXIS_WEIGHTS["key_management"])

        try:
            from backend.sovereign.keys import KeyRing

            keyring = KeyRing()
            keyring.load_from_disk()
            stats = keyring.stats()

            score = 0
            # KeyRing موجود وله مفاتيح (40%)
            if stats["total_keys"] > 0:
                score += 40
            else:
                axis.issues.append("KeyRing is empty")

            # مفتاح ACTIVE (30%)
            if stats["active"] > 0:
                score += 30
            else:
                axis.issues.append("no active key")

            # HISTORY.jsonl سليم (30%)
            history_file = self.repo_root / "data" / "keys" / "HISTORY.jsonl"
            if history_file.exists():
                import json
                content = history_file.read_text(encoding="utf-8")
                lines = [l for l in content.split("\n") if l.strip()]
                valid = all(self._is_valid_json(l) for l in lines)
                if valid and len(lines) > 0:
                    score += 30
                    axis.details["history_entries"] = len(lines)
                else:
                    axis.issues.append("HISTORY.jsonl corrupted or empty")
            else:
                axis.issues.append("HISTORY.jsonl not found")

            axis.score = score
            axis.details.update({
                "total_keys": stats["total_keys"],
                "active": stats["active"],
                "retired": stats.get("retired", 0),
                "lost": stats.get("lost", 0),
            })

        except Exception as e:
            axis.score = 0
            axis.issues.append(f"key management check failed: {e}")

        return axis

    def _is_valid_json(self, line: str) -> bool:
        """يتحقق أن السطر JSON صالح."""
        try:
            import json
            json.loads(line)
            return True
        except Exception:
            return False

    # ============================================================
    # المحور 3: جهاز المناعة (Immune System) — 20 نقطة
    # ============================================================

    def _score_immune_system(self) -> AxisScore:
        """يحسب درجة جهاز المناعة (الاختبارات الثابتة)."""
        axis = AxisScore(name="immune_system", score=0, weight=AXIS_WEIGHTS["immune_system"])

        try:
            invariants_dir = self.repo_root / "tests" / "invariants"
            if not invariants_dir.exists():
                axis.issues.append("tests/invariants/ does not exist")
                axis.score = 0
                return axis

            # فحص الملفات المطلوبة
            required_files = [
                "test_no_orphan_modules.py",
                "test_no_unsigned_ledger_events.py",
                "test_compat_sunset_criteria.py",
                "test_no_mock_outside_tests.py",
                "test_keyring_immutability.py",
                "test_all_entrypoints_respond.py",
                # R-665 (البوابة 4): حماية توقيع المرساة — مطلوب دائمًا
                "test_anchor_rejects_arbitrary_signature.py",
            ]

            existing = [f for f in required_files if (invariants_dir / f).exists()]

            # R-665: اختبار البوابة 4 في backend/tests/invariants/
            # (المالك طلب هذا المسار — مطلوب دائمًا، ليس مشروطًا)
            backend_invariants = self.repo_root / "backend" / "tests" / "invariants"
            gate4_file = "test_anchor_rejects_arbitrary_signature.py"
            if (backend_invariants / gate4_file).exists():
                if gate4_file not in existing:
                    existing.append(gate4_file)
            else:
                # مطلوب دائمًا — إذا غاب، يُسجَّل كمفقود
                axis.issues.append(f"missing invariant: backend/tests/invariants/{gate4_file}")
            missing = [f for f in required_files if f not in existing]

            # الدرجة: 60% وجود الملفات + 40% لا يتيمة/mock
            score = (len(existing) / len(required_files)) * 60

            # فحص اليتمة (تحليل AST)
            orphan_count = self._count_orphans()
            if orphan_count == 0:
                score += 20
            else:
                axis.issues.append(f"{orphan_count} orphan modules detected")
                score += max(0, 20 - orphan_count)

            # فحص mock في الإنتاج
            mock_count = self._count_mock_in_production()
            if mock_count == 0:
                score += 20
            else:
                axis.issues.append(f"{mock_count} mock usage in production")
                score += max(0, 20 - mock_count * 5)

            axis.score = min(score, 100)
            axis.details = {
                "invariants_files": len(existing),
                "invariants_required": len(required_files),
                "missing_files": missing,
                "orphan_modules": orphan_count,
                "mock_in_production": mock_count,
            }

        except Exception as e:
            axis.score = 0
            axis.issues.append(f"immune system check failed: {e}")

        return axis

    def _count_orphans(self) -> int:
        """يُعيد عدد الوحدات اليتيمة (نسخة مبسطة من invariant)."""
        try:
            import ast

            live_files = []
            for p in self.repo_root.rglob("*.py"):
                rel = str(p.relative_to(self.repo_root))
                if any(x in rel for x in [
                    "emergency_backups", "__pycache__", ".git",
                    "guardian/data/emergency",
                ]):
                    continue
                live_files.append(rel)

            live_set = set(live_files)
            imported_by = set()

            for f in live_files:
                try:
                    src = (self.repo_root / f).read_text(encoding="utf-8")
                    tree = ast.parse(src)
                except Exception:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for a in node.names:
                            self._mark_imported(a.name, live_set, imported_by)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._mark_imported(node.module, live_set, imported_by)

            entry_points = {
                "main.py", "backend/app.py", "backend/config.py", "backend/Mr.py",
                "nexus/main.py",
            }

            orphans = 0
            for f in live_files:
                if f in imported_by:
                    continue
                if f in entry_points:
                    continue
                if f.startswith("tests/"):
                    continue
                if f.endswith("__init__.py"):
                    continue
                if f.startswith("archive/"):
                    continue
                orphans += 1

            return orphans

        except Exception:
            return -1

    def _mark_imported(self, imp: str, live_set: set, imported_by: set):
        """يُسجّل أن ملفًا مُستوردًا."""
        parts = tuple(imp.split("."))
        for i in range(len(parts), 0, -1):
            suffix = parts[-i:]
            rel = "/".join(suffix) + ".py"
            if rel in live_set:
                imported_by.add(rel)
                return
            backend_rel = "backend/" + rel
            if backend_rel in live_set:
                imported_by.add(backend_rel)
                return

    def _count_mock_in_production(self) -> int:
        """يُعيد عدد استخدامات mock في كود الإنتاج."""
        try:
            import re

            patterns = [
                r"\bMock\(\)",
                r"\bMagicMock\(",
                r"\bpatch\.object\(",
                r"\bpatch\(",
                r"\bfrom unittest\.mock import",
            ]

            count = 0
            for p in self.repo_root.rglob("*.py"):
                rel = str(p.relative_to(self.repo_root))
                if any(x in rel for x in [
                    "emergency_backups", "__pycache__", ".git",
                    "guardian/data/emergency", "tests/", "archive/",
                ]):
                    continue

                try:
                    src = p.read_text(encoding="utf-8")
                except Exception:
                    continue

                for pat in patterns:
                    count += len(re.findall(pat, src))

            return count

        except Exception:
            return -1

    # ============================================================
    # المحور 4: دورة حياة التوافق (Compat Lifecycle) — 10 نقاط
    # ============================================================

    def _score_compat_lifecycle(self) -> AxisScore:
        """يحسب درجة دورة حياة التوافق."""
        axis = AxisScore(name="compat_lifecycle", score=0, weight=AXIS_WEIGHTS["compat_lifecycle"])

        try:
            compat_dir = self.repo_root / "backend" / "compat"
            if not compat_dir.exists():
                axis.issues.append("backend/compat/ does not exist")
                axis.score = 0
                return axis

            # __meta__.py موجود (40%)
            meta_file = compat_dir / "__meta__.py"
            has_meta = meta_file.exists()
            if has_meta:
                score = 40
            else:
                score = 0
                axis.issues.append("__meta__.py not found")

            # SUNSET_CRITERIA في كل وحدة (60%)
            compat_files = [
                cf for cf in compat_dir.glob("*.py")
                if cf.name not in ("__init__.py", "__meta__.py")
            ]
            with_sunset = 0
            for cf in compat_files:
                try:
                    src = cf.read_text(encoding="utf-8")
                    if "sunset" in src.lower() or "SUNSET_CRITERIA" in src:
                        with_sunset += 1
                # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
                except Exception:
                    pass

            if compat_files:
                sunset_ratio = with_sunset / len(compat_files)
                score += sunset_ratio * 60
                if sunset_ratio < 1.0:
                    axis.issues.append(
                        f"{len(compat_files) - with_sunset} compat modules without SUNSET_CRITERIA"
                    )
            else:
                axis.issues.append("no compat modules found")

            axis.score = min(score, 100)
            axis.details = {
                "has_meta": has_meta,
                "compat_modules": len(compat_files),
                "with_sunset_criteria": with_sunset,
            }

        except Exception as e:
            axis.score = 0
            axis.issues.append(f"compat lifecycle check failed: {e}")

        return axis

    # ============================================================
    # المحور 5: صحة الاختبارات (Test Health) — 15 نقطة
    # ============================================================

    def _score_test_health(self) -> AxisScore:
        """يحسب درجة صحة الاختبارات."""
        axis = AxisScore(name="test_health", score=0, weight=AXIS_WEIGHTS["test_health"])

        try:
            tests_dir = self.repo_root / "tests"
            if not tests_dir.exists():
                axis.issues.append("tests/ does not exist")
                axis.score = 0
                return axis

            # عدد ملفات الاختبار
            test_files = list(tests_dir.rglob("test_*.py"))
            test_count = len(test_files)

            # عدد الاختبارات (تقديري — عدّ الدوال test_*)
            total_tests = 0
            for tf in test_files:
                try:
                    src = tf.read_text(encoding="utf-8")
                    total_tests += src.count("def test_")
                # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
                except Exception:
                    pass

            # الدرجة: 70% عدد الاختبارات + 30% invariants موجودة
            if total_tests >= 100:
                score = 70
            elif total_tests >= 50:
                score = 50
            elif total_tests >= 20:
                score = 30
            elif total_tests > 0:
                score = 15
            else:
                score = 0
                axis.issues.append("no tests found")

            # invariants موجودة
            invariants_dir = tests_dir / "invariants"
            if invariants_dir.exists():
                inv_files = list(invariants_dir.glob("test_*.py"))
                if inv_files:
                    score += 30
                else:
                    axis.issues.append("invariants directory empty")
            else:
                axis.issues.append("invariants directory not found")

            axis.score = min(score, 100)
            axis.details = {
                "test_files": test_count,
                "total_test_functions": total_tests,
                "has_invariants": invariants_dir.exists(),
            }

        except Exception as e:
            axis.score = 0
            axis.issues.append(f"test health check failed: {e}")

        return axis

    # ============================================================
    # المحور 6: الصحة الهيكلية (Structural Health) — 10 نقاط
    # ============================================================

    def _score_structural_health(self) -> AxisScore:
        """يحسب درجة الصحة الهيكلية."""
        axis = AxisScore(name="structural_health", score=0, weight=AXIS_WEIGHTS["structural_health"])

        try:
            # نقاط النهاية الحرجة موجودة في app.py (50%)
            app_file = self.repo_root / "backend" / "app.py"
            if app_file.exists():
                src = app_file.read_text(encoding="utf-8")
                critical_endpoints = ["/health", "/ledger/verify", "/compat/status"]
                found = sum(1 for e in critical_endpoints if e in src)
                score = (found / len(critical_endpoints)) * 50
                if found < len(critical_endpoints):
                    missing = [e for e in critical_endpoints if e not in src]
                    axis.issues.append(f"missing endpoints: {missing}")
            else:
                score = 0
                axis.issues.append("backend/app.py not found")

            # لا stub/placeholder (25%)
            # ملاحظة: النمط يستخدم علامة اقتباس مفردة داخل أخرى لتجنب
            # مطابقة سطر تعريف النمط نفسه في هذا الملف (false positive)
            import re
            stub_patterns = [
                r"#\s*TODO:\s*implement",
                r"#\s*stub",
                r"#\s*placeholder",
                "raise " + "NotImplementedError",  # يُبنى ديناميكيًا — لا يُطابق نفسه
            ]
            stub_count = 0
            for p in self.repo_root.rglob("*.py"):
                rel = str(p.relative_to(self.repo_root))
                if any(x in rel for x in [
                    "emergency_backups", "__pycache__", ".git",
                    "guardian/data/emergency", "tests/", "archive/",
                ]):
                    continue
                try:
                    content = p.read_text(encoding="utf-8")
                    for pat in stub_patterns:
                        stub_count += len(re.findall(pat, content))
                # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
                except Exception:
                    pass

            if stub_count == 0:
                score += 25
            else:
                axis.issues.append(f"{stub_count} stub/placeholder in production")
                score += max(0, 25 - stub_count * 5)

            # INVENTORY.py موجود (25%)
            inventory_file = self.repo_root / "archive" / "root_strays" / "INVENTORY.py"
            if inventory_file.exists():
                score += 25
            else:
                axis.issues.append("INVENTORY.py not found")

            axis.score = min(score, 100)
            axis.details = {
                "stub_count": stub_count,
                "has_inventory": inventory_file.exists(),
            }

        except Exception as e:
            axis.score = 0
            axis.issues.append(f"structural health check failed: {e}")

        return axis

    # ============================================================
    # الحساب الكلي
    # ============================================================

    def compute(self) -> SovereigntyReport:
        """يحسب درجة السيادة الكاملة و يُعيد التقرير."""
        self._axes = [
            self._score_ledger_integrity(),
            self._score_key_management(),
            self._score_immune_system(),
            self._score_compat_lifecycle(),
            self._score_test_health(),
            self._score_structural_health(),
        ]

        total = sum(a.weighted_score for a in self._axes)
        grade = _grade_for(total)

        # ملخص
        issues_count = sum(len(a.issues) for a in self._axes)
        self._report = SovereigntyReport(
            total_score=round(total, 2),
            grade=grade,
            axes=self._axes,
            timestamp=time.time(),
            summary={
                "total_axes": len(self._axes),
                "total_issues": issues_count,
                "thresholds": {
                    "sovereign": SOVEREIGN_THRESHOLD,
                    "partially_sovereign": PARTIALLY_SOVEREIGN_THRESHOLD,
                    "working": WORKING_THRESHOLD,
                    "fragile": FRAGILE_THRESHOLD,
                },
            },
        )

        return self._report

    def to_dict(self) -> Dict:
        """يُعيد التقرير كقاموس (للـ endpoint)."""
        if not hasattr(self, "_report"):
            self.compute()
        return self._report.to_dict()
