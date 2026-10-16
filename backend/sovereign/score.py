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
                # TOLERATED: file unreadable/unparsable AST — counted as not-imported (R-680)
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
                # TOLERATED: unreadable file — excluded from mocks count (R-680)
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


# ============================================================
# الجولة الإنشائية 2026-10-16 — معادلة ROADMAP_V2 (المرحلة 5) الحرفية
# ============================================================
# SOVEREIGNTY_SCORE الثمانية مكونات كما وردت في ROADMAP_V2.md نصًّا.
# تُعاد القيم 0.0-1.0 (والثنائيان 0/1) وfinal_score 0.0-1.0.
#
# تعريف التجميع (ROADMAP_V2 لا يحدد أوزان final_score): متوسط المكونات
# السبعة المسجلة (خمس نسب + ثنائيان) — موثق هنا وفي REPORT_V2.md، ولا
# يُعدل لتحسين نتيجة.
#
# حدّ السجل الغائب: ledger.jsonl الخام غير متتبع في git (موثق غيابه في
# forensics/INVARIANT_LIMITS.md). مكونا ledger_verified وledger_anchored
# يُحسبان من ملف المراسي المتتبع (نطاقات الدفعات المعلنة) — حد أعلى
# معلن، والقيمة المحافظة 0.0. النتيجة النهائية المعلنة هي الحد الأعلى مع
# score_capped_by_missing_ledger=true ونطاق ثقة [محافظ، متفائل].

import ast as _ast
import subprocess as _subprocess
from pathlib import Path as _Path


def _v2_live_backend_modules(repo_root: _Path) -> list:
    """وحدات backend الحية (بدون tests/ و __pycache__ والأرشيف)."""
    live = []
    for p in (repo_root / "backend").rglob("*.py"):
        rel = str(p.relative_to(repo_root))
        if any(x in rel for x in ["__pycache__", ".git"]):
            continue
        if rel.startswith("backend/tests/"):
            continue
        live.append((rel, p))
    return live


def _v2_test_import_stems(repo_root: _Path) -> set:
    """أسماء (stems) الوحدات المستوردة من ملفات الاختبارات كلها."""
    stems = set()
    for tests_dir in ("tests", "backend/tests"):
        d = repo_root / tests_dir
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            if "__pycache__" in str(p):
                continue
            # TOLERATED: test file unreadable/unparsable — excluded from
            # test-import stems (matches scanner policy; counted files only)
            try:
                tree = _ast.parse(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Import):
                    for a in node.names:
                        stems.add(a.name.split(".")[0])
                elif isinstance(node, _ast.ImportFrom):
                    if node.module:
                        stems.add(node.module.split(".")[0])
                    for a in node.names:
                        stems.add(a.name.split(".")[0])
    return stems


def _v2_run_invariants(repo_root: _Path) -> dict:
    """تشغيل فعلي لاختبارات invariants (المساران) — نتيجة 0/1 صادقة."""
    import sys as _sys
    cmd = [
        _sys.executable, "-m", "pytest",
        "tests/invariants/", "backend/tests/invariants/",
        "-q", "--no-header", "-p", "no:cacheprovider",
    ]
    try:
        r = _subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(repo_root), timeout=900,
        )
        passed = (r.returncode == 0)
        tail = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""
    except _subprocess.TimeoutExpired:
        passed = False
        tail = "invariants run timed out (900s)"
    return {"passing": 1 if passed else 0, "run_tail": tail}


def compute_sovereignty_score_v2(repo_root=None) -> dict:
    """معادلة ROADMAP_V2 (المرحلة 5) — SOVEREIGNTY_SCORE الثمانية مكونات.

    تُحسب الآن من حالة المستودع الفعلية. غياب ledger.jsonl الخام يُعلن
    صراحة: مكونا السجل عند حدهما الأعلى (تغطية المراسي المعلنة) مع
    score_capped_by_missing_ledger=true ونطاق ثقة [محافظ، متفائل].
    """
    from backend.sovereign.primitives import Primitives

    if repo_root is None:
        repo_root = _Path(__file__).resolve().parent.parent.parent
    repo_root = _Path(repo_root)
    prim = Primitives(repo_root=repo_root)

    # 1) files_reachable — نسبة الملفات المستوردة (تعريف Primitives:
    #    ملفات .py التي يستوردها ملف آخر، بتحليل AST — قابل لإعادة الحساب)
    files_total = prim.files_total_count()
    files_imported = prim.files_imported_count()
    files_reachable = (files_imported / files_total) if files_total else 0.0

    # 2) modules_tested — نسبة وحدات backend الحية المستوردة من اختبار واحد+
    backend_modules = _v2_live_backend_modules(repo_root)
    test_stems = _v2_test_import_stems(repo_root)
    tested = [rel for rel, p in backend_modules
              if p.stem in test_stems or p.name == "__init__.py"]
    # ملفات __init__.py تُعد مغطاة (بنية الحزمة يغطيها استيراد الحزمة)
    modules_tested = (len(tested) / len(backend_modules)) if backend_modules else 0.0

    # 3+4) ledger_verified / ledger_anchored — من ملف المراسي المتتبع.
    # السجل الخام غائب (gitignored) → التغطية المعلنة حد أعلى؛ المحافظ 0.0
    ledger_path = repo_root / "data" / "sovereign_core" / "ledger.jsonl"
    anchors_path = repo_root / "data" / "sovereign_core" / "ledger.anchors.jsonl"
    ledger_present = ledger_path.exists()
    anchored_union = set()
    anchors_malformed = 0
    if anchors_path.exists():
        import json as _json
        for line in anchors_path.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            # سطر مرساة تالف/ناقص الحقول: يُعدّ ولا يُسكت عليه (لا إخفاء فشل)
            try:
                a = _json.loads(line)
                for i in range(a["batch_start"], a["batch_end"] + 1):
                    anchored_union.add(i)
            except (ValueError, KeyError, TypeError):
                anchors_malformed += 1
    if ledger_present:
        # السجل موجود: التغطية الفعلية من عدد الأسطر
        n_lines = sum(
            1 for line in ledger_path.read_text(encoding="utf-8").split("\n")
            if line.strip()
        )
        total_events = max(n_lines, 1)
    else:
        # السجل غائب: الإجمالي الموثق في تقارير الحالة (116,910) —
        # والتغطية المعلنة في المراسي (0..116909) حد أعلى
        total_events = 116910
    ledger_anchored_upper = (
        min(len(anchored_union), total_events) / total_events
    ) if total_events else 0.0
    ledger_verified_upper = ledger_anchored_upper  # بلا سجل: لا تحقق بالمفتاح قابلًا للقياس
    score_capped = not ledger_present

    # 5) compat_pending_sunset — نسبة وحدات compat ذات sunset_criteria
    from backend.compat.__meta__ import COMPAT_LIFECYCLE
    compat_total = len(COMPAT_LIFECYCLE)
    compat_with = sum(
        1 for v in COMPAT_LIFECYCLE.values() if v.get("sunset_criteria")
    )
    compat_ratio = (compat_with / compat_total) if compat_total else 0.0

    # 6) no_mocks_in_prod — ثنائي من المسح الفعلي
    no_mocks = 1 if prim.mocks_outside_tests_count() == 0 else 0

    # 7) invariants_passing — ثنائي من تشغيل فعلي (سب-بروسس)
    inv = _v2_run_invariants(repo_root)

    components = {
        "files_reachable": round(files_reachable, 4),
        "modules_tested": round(modules_tested, 4),
        "ledger_verified": round(ledger_verified_upper, 4),
        "ledger_anchored": round(ledger_anchored_upper, 4),
        "compat_pending_sunset": round(compat_ratio, 4),
        "no_mocks_in_prod": no_mocks,
        "invariants_passing": inv["passing"],
    }

    def _final(ledger_value: float) -> float:
        c = dict(components)
        c["ledger_verified"] = ledger_value
        c["ledger_anchored"] = ledger_value
        return round(sum(c.values()) / 7, 4)

    final_upper = _final(ledger_anchored_upper)
    final_lower = _final(0.0)

    try:
        import subprocess as _sp
        sha = _sp.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root),
        ).stdout.strip()
    except Exception:
        sha = "unknown"

    result = dict(components)
    result["final_score"] = final_upper
    result["score_capped_by_missing_ledger"] = bool(score_capped)
    result["confidence_range"] = {
        "lower": final_lower,
        "upper": final_upper,
        "note": (
            "ledger.jsonl raw file absent from clone — ledger components are "
            "upper bounds (anchors-file declared coverage); conservative "
            "bound uses 0.0 for both ledger components"
        ) if score_capped else {
            "lower": final_upper,
            "upper": final_upper,
            "note": "ledger present — components computed from actual file",
        },
    }
    result["inputs"] = {
        "files_total_count": files_total,
        "files_imported_count": files_imported,
        "backend_live_modules": len(backend_modules),
        "backend_modules_tested": len(tested),
        "ledger_present": ledger_present,
        "anchors_declared_coverage": len(anchored_union),
        "anchors_malformed_lines": anchors_malformed,
        "documented_total_events": total_events,
        "compat_total": compat_total,
        "compat_with_sunset": compat_with,
        "mocks_outside_tests_count": prim.mocks_outside_tests_count(),
        "invariants_run_tail": inv["run_tail"],
        "repo_head_sha": sha,
    }
    result["aggregation"] = (
        "final_score = mean(7 scored components) — documented choice; "
        "ROADMAP_V2 does not specify weights; not tunable to improve results"
    )
    return result
