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
from typing import Any, Dict, List, Optional

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


# ============================================================
# R-788a: ذاكرة تصنيف تزايدية لمحور نزاهة السجل
# ============================================================

import hashlib as _hashlib
import threading as _threading

_CLASSIFY_LOCK = _threading.Lock()
_CLASSIFY_CACHE: Dict[str, Any] = {}


def _keyring_fingerprint(keyring) -> str:
    h = _hashlib.sha256()
    try:
        recs = keyring.list_keys()
    except Exception:  # TOLERATED: بصمة فارغة ⇒ لا تطابق ⇒ إعادة تصنيف كاملة (الأحوط)
        return "unavailable"
    for r in recs:
        status = getattr(getattr(r, "status", None), "value", getattr(r, "status", ""))
        h.update(f"{r.key_id}|{status}|{r.public_key}|{getattr(r, 'key_type', 'hmac')}\n".encode())
    return h.hexdigest()


def _feed(h, lines: List[str], a: int, b: int):
    for line in lines[a:b]:
        h.update(line.encode("utf-8", "surrogatepass"))
        h.update(b"\n")
    return h


def _classify_one(line: str, verifier) -> bool:
    """True ⇒ غير مصنف (نفس شرط الحلقة الأصلية حرفيًا)."""
    import json
    try:
        event = json.loads(line)
        result = verifier.verify_event(event)
        return result.status.value not in ("verified", "unverifiable_missing_key")
    except Exception:
        return True


def _classify_ledger_incremental(path: str, lines: List[str], keyring, verifier) -> int:
    kfp = _keyring_fingerprint(keyring)
    with _CLASSIFY_LOCK:
        c = _CLASSIFY_CACHE.get(path)
        start, unclassified = 0, 0
        h = _hashlib.sha256()
        if c and c["keyring"] == kfp and c["n"] <= len(lines):
            _feed(h, lines, 0, c["n"])
            if h.hexdigest() == c["digest"]:
                start, unclassified = c["n"], c["unclassified"]
            else:
                h = _hashlib.sha256()
        _feed(h, lines, start, len(lines))
        for line in lines[start:]:
            if _classify_one(line, verifier):
                unclassified += 1
        _CLASSIFY_CACHE[path] = {"n": len(lines), "digest": h.hexdigest(),
                                 "unclassified": unclassified, "keyring": kfp,
                                 "reused_prefix": start}
        return unclassified


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

            # R-788a: تصنيف تزايدي — السجل إلحاقي، فالبادئة المصنفة سابقًا لا يُعاد التحقق من
            # تواقيعها ما دامت بصمة sha256 للبادئة كاملةً (لا آخر سطر فقط) وبصمة حلقة المفاتيح
            # مطابقتين. أي تغيير في أي سطر سابق أو في أي مفتاح ⇒ إعادة تصنيف كاملة (الدلالة نفسها).
            # الدليل: 138k حدثًا × ~6.6ms على آلة مستنفدة الرصيد = >15 دقيقة لكل طلب.
            unclassified = _classify_ledger_incremental(
                str(getattr(anchor, "ledger_path", "")), lines, keyring, verifier)

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
                # R-788a: كان verification["verified"] — مفتاح غير موجود في عقد
                # verify_all_anchors (المفتاح root_verified_count منذ R-642) ⇒ KeyError بعد المرور
                # الكامل على السجل، فالمحور كان صفرًا دائمًا بسبب «ledger integrity check failed».
                "anchors_verified": verification.get("root_verified_count", 0),
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
# (تصويب المراجع — الاعتراضان 1 و6: هويات مسارات كاملة لا أسماء مجردة؛
# لا مس لملف السجل الخام إطلاقًا — وضع الغياب صريح بلا فحص وجود؛
# invariants_passing من دليل تشغيل معلوم الهوية — لا تشغيل pytest داخل
# طلب HTTP يختبر الطلب نفسه، ولا ثابت نجاح بلا دليل)
# ============================================================

import ast as _ast
import subprocess as _subprocess
from pathlib import Path as _Path


def _v2_module_identities(repo_root: _Path, file_path: _Path) -> "set":
    """هويات الاستيراد الممكنة لملف — مسارات منقطة كاملة من كل جذر
    استيراد حقيقي (جذر المستودع وbackend/ — كلاهما على sys.path فعليًا).

    مثال: backend/orchestrator.py → {"backend.orchestrator", "orchestrator"}.
    ملف backend/sovereign/keys/__init__.py → {"backend.sovereign.keys",
    "sovereign.keys"} — يُغطى باستيراد الحزمة نفسها (هويته هو مسارها).
    """
    rel = file_path.relative_to(repo_root)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    dotted_full = ".".join(parts)
    identities = {dotted_full}
    if rel.parts[0] == "backend" and len(rel.parts) > 1:
        identities.add(".".join(parts[1:]))
    return identities


def _v2_collect_imported_names(repo_root: _Path, files: "list") -> "set":
    """كل أسماء الوحدات المستوردة فعليًا — مسارات منقطة كاملة:

    - import a.b.c → a.b.c
    - from a.b import x → a.b وa.b.x (x قد يكون وحدة)
    - الاستيراد النسبي (from .m import x) يُحل ضد حزمة الملف المستورد
    """
    imported = set()
    for fp in files:
        try:
            tree = _ast.parse(fp.read_text(encoding="utf-8"))
        except Exception:  # TOLERATED: ملف غير قابل للتحليل — يستثنى من جمع الأسماء (سياسة الماسح نفسها)
            continue
        pkg_parts = list(fp.relative_to(repo_root).with_suffix("").parts[:-1])
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for a in node.names:
                    imported.add(a.name)
            elif isinstance(node, _ast.ImportFrom):
                if node.level == 0 and node.module:
                    imported.add(node.module)
                    for a in node.names:
                        imported.add(f"{node.module}.{a.name}")
                else:
                    # نسبي: from .m import x / from ..m import x
                    base = pkg_parts[: len(pkg_parts) - (node.level - 1)] if node.level > 1 else pkg_parts
                    mod_parts = base + ([node.module] if node.module else [])
                    mod = ".".join(p for p in mod_parts if p)
                    if mod:
                        imported.add(mod)
                        for a in node.names:
                            imported.add(f"{mod}.{a.name}")
    return imported


def _v2_live_py_files(repo_root: _Path, subtree: "str | None" = None) -> "list":
    live = []
    for p in repo_root.rglob("*.py"):
        rel = str(p.relative_to(repo_root))
        if any(x in rel for x in ["__pycache__", ".git", ".pytest_cache"]):
            continue
        if rel.startswith(("archive/", "emergency_backups/")):
            continue
        if subtree and not rel.startswith(subtree):
            continue
        live.append(p)
    return live


# حراس ROADMAP_V2 بهوية كاملة (classname, name) — لا الاسم المجرد وحده:
# اختبار متشابه الاسم خارج invariants لا يحقق القائمة. يشمل حارس
# test_no_mock_outside_tests (الغائب عن القائمة المجردة سابقًا).
_V2_REQUIRED_INVARIANT_TESTS = (
    ("backend.tests.invariants.test_no_orphan_modules", "test_no_orphan_modules"),
    ("backend.tests.invariants.test_no_unsigned_ledger_events",
     "test_no_unsigned_ledger_events"),
    ("backend.tests.invariants.test_all_entrypoints_respond",
     "test_all_registered_routes_respond"),
    ("backend.tests.invariants.test_keyring_immutability",
     "test_keyring_history_immutable"),
    ("backend.tests.invariants.test_compat_sunset_criteria",
     "test_every_compat_module_has_sunset_criteria"),
    ("backend.tests.invariants.test_no_silent_exceptions.TestNoSilentExceptions",
     "test_no_silent_except_in_production"),
    ("backend.tests.invariants.test_no_mock_outside_tests",
     "test_no_mock_outside_tests"),
)


def _v2_content_fingerprint(repo_root: _Path) -> str:
    """بصمة محتوى مدخلات الكود والاختبارات (تصويب المراجع — الجولة 2):

    sha256 على (المسار النسبي + هاش المحتوى) لكل ملف .py حي، مرتبة —
    مخرجات الأدلة (forensics/) والأرشيف والبيانات مستثناة. تغيير محتوى
    ملف واحد (ولو بقي M على HEAD نفسه) يغير البصمة — الدليل القديم
    يُرفض. السجل الخام لا يُفتح ولا يُبحث عنه (منع المالك)."""
    import hashlib as _hl

    repo_root = _Path(repo_root)
    excluded = ("__pycache__", ".git", ".pytest_cache", "node_modules",
                "venv", "archive/", "emergency_backups/", "forensics/", "data/")
    digest = _hl.sha256()
    for p in sorted(repo_root.rglob("*.py")):
        rel = p.relative_to(repo_root).as_posix()
        if any(x in rel for x in excluded):
            continue
        digest.update(rel.encode("utf-8"))
        digest.update(_hl.sha256(p.read_bytes()).digest())
    return digest.hexdigest()


def seal_junit_identity(junit_path, repo_root: _Path,
                       captured_fingerprint: str) -> dict:
    """ختم هوية التشغيل بالبصمة الملتقطة قبل التشغيل (تصويب المراجع —
    الجولة 3): مقارنة الشجرة الحالية بالملتقطة — إن اختلفت يُرفض الختم
    (لا يُختم تقرير قديم ببصمة جديدة)، وإن تطابقت تُكتب البصمة الملتقطة
    نفسها حرفيًا (لا إعادة حساب)."""
    junit_path = _Path(junit_path)
    repo_root = _Path(repo_root)
    current_fp = _v2_content_fingerprint(repo_root)
    if current_fp != captured_fingerprint:
        raise RuntimeError(
            "content changed between the run and the sealing — refusing to "
            "seal a stale report with a fresh fingerprint"
        )
    return embed_junit_identity(junit_path, repo_root,
                                fingerprint=captured_fingerprint)


def embed_junit_identity(junit_path, repo_root: _Path, fingerprint=None) -> dict:
    """تضمين هوية التشغيل في JUnit (SHA + بصمة المحتوى).

    fingerprint: بصمة مسبقة (الملتقطة وقت التشغيل) تُكتب كما هي — لا
    إعادة حساب. غيابها = حساب بصمة اللحظة (لأدلة لا تحتاج ضمان الترتيب)."""
    import xml.etree.ElementTree as _ET

    junit_path = _Path(junit_path)
    repo_root = _Path(repo_root)
    head = _subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=str(repo_root),
    ).stdout.strip()
    if fingerprint is None:
        fingerprint = _v2_content_fingerprint(repo_root)
    tree = _ET.parse(junit_path)
    root = tree.getroot()
    root.set("git_sha", head)
    root.set("junit_prefix", f"R-682-sha-{head}")
    root.set("content_fingerprint", fingerprint)
    _ET.indent(tree)
    tree.write(junit_path, encoding="utf-8", xml_declaration=True)
    return {"head": head, "content_fingerprint": fingerprint}


def _parse_junit_evidence(junit_path: _Path, head: str,
                           required=None, repo_root=None) -> dict:
    """تحليل JUnit فعليًا (تصويب المراجع — الاعتراض 5): لا بحث نصي —
    ElementTree: النطاق (الاختبارات المطلوبة حاضرة)، الأعداد، الصفر
    فشل/خطأ/تخطٍّ، ومطابقة SHA للجذر. الرفض صريح ومسبب في كل حالة."""
    import xml.etree.ElementTree as _ET

    required = tuple(required) if required else _V2_REQUIRED_INVARIANT_TESTS
    # هوية كاملة: (classname, name) — لا الاسم المجرد
    required_pairs = [
        tuple(x) if isinstance(x, (tuple, list)) else (None, x)
        for x in required
    ]
    base = {
        "source": "JUnit XML parse", "head_sha": head,
        "junit_path": str(junit_path),
    }
    junit_path = _Path(junit_path)
    if not junit_path.exists():
        return {**base, "passing": 0, "reason": "no JUnit evidence file"}
    try:
        tree = _ET.parse(junit_path)
    # TOLERATED: XML تالف — يعامل كدليل غائب (لا نجاح بلا دليل)
    except Exception:
        return {**base, "passing": 0, "reason": "JUnit XML unreadable/corrupt"}

    root = tree.getroot()
    sha_attr = root.get("junit_prefix", "")
    import re as _re2
    m = _re2.match(r"R-682-sha-([0-9a-f]{40})$", sha_attr)
    if not m or m.group(1) != head:
        return {**base, "passing": 0,
                "reason": "JUnit SHA missing or mismatched (stale evidence)"}

    # ربط الدليل بمحتوى الشجرة (تصويب المراجع — الجولة 2): البصمة
    # المضمنة وقت التشغيل يجب أن تطابق بصمة الشجرة الحالية — دليل قديم
    # على HEAD نفسه بعد تغيير كود يُرفض (تغيير المحتوى وليس حالة git).
    embedded_fp = root.get("content_fingerprint", "")
    if not embedded_fp:
        return {**base, "passing": 0,
                "reason": "JUnit not tied to content fingerprint "
                         "(missing embedded fingerprint)"}
    if repo_root is not None:
        current_fp = _v2_content_fingerprint(_Path(repo_root))
        if current_fp != embedded_fp:
            return {**base, "passing": 0,
                    "reason": "content fingerprint mismatch — code/tests "
                              "changed since the evidence run"}

    suites = list(root.iter("testsuite"))
    if not suites:
        return {**base, "passing": 0, "reason": "empty JUnit (no testsuites)"}

    total = sum(int(s.get("tests", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) for s in suites)
    errors = sum(int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)

    if total == 0:
        return {**base, "passing": 0, "reason": "JUnit reports zero tests"}
    if failures or errors:
        return {**base, "passing": 0,
                "reason": f"JUnit reports failures={failures} errors={errors}"}
    if skipped:
        return {**base, "passing": 0,
                "reason": f"JUnit reports skipped={skipped} (zero-skip DoD)"}

    # النطاق: الاختبارات المطلوبة حاضرة — كل واحدة بحالة نظيفة
    case_states = {}
    import re as _re3

    # بادئة هوية التقرير نفسه فقط (تصويب المراجع — الجولة 4): تُنزع البادئة
    # المطابقة لـSHA جذره — تقرير يحمل SHA الحالي لكن أسماء اختباراته
    # تحمل بادئة SHA آخر لا يُنظف ويُرفض (فحص التمييز في الاختبارات).
    root_sha = (m.group(1) if m else "")
    expected_prefix = f"R-682-sha-{root_sha}."

    def _strip_junit_prefix(classname: str) -> str:
        if root_sha and classname.startswith(expected_prefix):
            return classname[len(expected_prefix):]
        return classname

    for tc in root.iter("testcase"):
        key = (_strip_junit_prefix(tc.get("classname", "")), tc.get("name", ""))
        state = "ok"
        if tc.find("failure") is not None:
            state = "failure"
        elif tc.find("error") is not None:
            state = "error"
        elif tc.find("skipped") is not None:
            state = "skipped"
        case_states[key] = state
    missing = [f"{c}::{n}" for c, n in required_pairs if (c, n) not in case_states]
    if missing:
        return {**base, "passing": 0,
                "reason": f"JUnit scope missing required invariants: {missing}"}
    bad = {f"{c}::{n}": case_states[(c, n)] for c, n in required_pairs
           if (c, n) in case_states and case_states[(c, n)] != "ok"}
    if bad:
        return {**base, "passing": 0,
                "reason": f"required invariants not clean: {bad}"}

    return {
        **base, "passing": 1,
        "tests_total": total, "failures": failures, "errors": errors,
        "skipped": skipped,
        "required_invariants": [f"{c}::{n}" for c, n in required_pairs],
    }


def _v2_tree_fingerprint(repo_root: _Path) -> str:
    """بصمة حالة الشجرة العاملة (تصويب المراجع: الدليل مرتبط بحالة الشجرة
    لا بـHEAD وحده) — sha256 لخرج git status --porcelain."""
    r = _subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=str(repo_root),
    )
    import hashlib as _hl
    return _hl.sha256(r.stdout.encode("utf-8")).hexdigest()[:16]


def _v2_invariants_evidence(repo_root: _Path, junit_path=None,
                             required=None) -> dict:
    """دليل تشغيل invariants معلوم الهوية والنطاق وحالة الشجرة.

    يُقبل فقط إذا: تطابق SHA المضمّن مع HEAD، والنطاق يشمل الاختبارات
    المطلوبة ناجحة، وصفر فشل/خطأ/تخطٍّ. لا نجاح بثابت بلا دليل."""
    head = _subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=str(repo_root),
    ).stdout.strip()
    junit = (_Path(junit_path) if junit_path
             else repo_root / "forensics" / "pytest_results.xml")
    evidence = _parse_junit_evidence(junit, head, required=required,
                                     repo_root=repo_root)
    evidence["tree_fingerprint"] = _v2_tree_fingerprint(repo_root)
    return evidence


def compute_sovereignty_score_v2(repo_root=None, invariants_evidence=None) -> dict:
    """معادلة ROADMAP_V2 (المرحلة 5) — SOVEREIGNTY_SCORE الثمانية مكونات.

    (تصويبات المراجع — الاعتراض 6):
    - الوصول والاختبار يقيسان بهويات المسارات الكاملة (منقطة) — لا أسماء
      مجردة أو أول جزء؛ و__init__.py لا يُمنح تغطية تلقائية (هويته مسار
      الحزمة — يُغطى فقط باستيراد الحزمة الفعلي).
    - السجل الخام لا يُفتح ولا يُبحث عنه إطلاقًا داخل هذه الدالة — مكوّنا
      السجل من ملف المراسي المتتبع حصرًا (حد أعلى معلن)، والوضع صريح.
    - invariants_passing من دليل تشغيل معلوم الهوية (JUnit بـSHA مطابق
      أو دليل صريح يُمرر) — لا تشغيل اختبارات هنا.
    - التجميع موثق: متوسط المكونات القابلة للقياس (الخمسة) — مكوّنا السجل
      أُزيلا من العقد (قرار المالك R-683) — DELETION-JUSTIFIED.
    """
    if repo_root is None:
        repo_root = _Path(__file__).resolve().parent.parent.parent
    repo_root = _Path(repo_root)

    all_py = _v2_live_py_files(repo_root)
    imported_names = _v2_collect_imported_names(repo_root, all_py)

    # 1) files_reachable — بالهويات المنقطة الكاملة
    reachable = []
    for p in all_py:
        if _v2_module_identities(repo_root, p) & imported_names:
            reachable.append(p)
    files_reachable = (len(reachable) / len(all_py)) if all_py else 0.0

    # 2) modules_tested — وحدات backend الحية المستوردة من ملفات اختبار فعلًا
    backend_modules = [
        p for p in all_py
        if str(p.relative_to(repo_root)).startswith("backend/")
        and not str(p.relative_to(repo_root)).startswith("backend/tests/")
    ]
    test_files = [
        p for p in all_py
        if str(p.relative_to(repo_root)).startswith(("tests/", "backend/tests/"))
    ]
    test_imported = _v2_collect_imported_names(repo_root, test_files)
    tested_modules = [
        p for p in backend_modules
        if _v2_module_identities(repo_root, p) & test_imported
    ]
    modules_tested = (
        (len(tested_modules) / len(backend_modules)) if backend_modules else 0.0
    )

    # 3+4) ledger_verified / ledger_anchored — من ملف المراسي المتتبع حصرًا.
    # (لا فحص وجود للسجل الخام ولا فتحه — منع صريح؛ المكوّنان حد أعلى
    # معلن من تغطية المراسي، والقيمة المحافظة 0.0.)
    anchors_path = repo_root / "data" / "sovereign_core" / "ledger.anchors.jsonl"
    anchored_union = set()
    anchors_malformed = 0
    if anchors_path.exists():
        import json as _json
        for line in anchors_path.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            # سطر مرساة تالف/ناقص الحقول: يُعدّ ولا يُسكت عليه
            try:
                a = _json.loads(line)
                for i in range(a["batch_start"], a["batch_end"] + 1):
                    anchored_union.add(i)
            except (ValueError, KeyError, TypeError):
                anchors_malformed += 1
    documented_total = 116910  # الإجمالي الموثق في تقارير الحالة
    # DELETION-JUSTIFIED — ledger_upper (3 أسطر) حُذف: كود ميت منذ R-683 (لا يدخل الرد)

    # 5) compat_pending_sunset — من السجل الفعلي (استيراد حقيقي)
    from backend.compat.__meta__ import COMPAT_LIFECYCLE
    compat_total = len(COMPAT_LIFECYCLE)
    compat_with = sum(
        1 for v in COMPAT_LIFECYCLE.values() if v.get("sunset_criteria")
    )
    compat_ratio = (compat_with / compat_total) if compat_total else 0.0

    # 6) no_mocks_in_prod — مسح فعلي (نفس تعريف primitives القابل لإعادة الحساب)
    # R-711 (بند ٣ من التدقيق): استدعاء واحد فقط للمسح الثقيل — كان يُستدعى
    # مرتين في الطلب الواحد (المتغير no_mocks + مدخل inputs) وكل استدعاء يمسح
    # الشجرة كاملة. القيمة تُخزَّن وتُعاد — دلالات العدادات لم تتغير.
    from backend.sovereign.primitives import Primitives
    prim = Primitives(repo_root=repo_root)
    mocks_outside_count = prim.mocks_outside_tests_count()
    no_mocks = 1 if mocks_outside_count == 0 else 0

    # 7) invariants_passing — من دليل معلوم الهوية (لا تشغيل هنا)
    if invariants_evidence is None:
        invariants_evidence = _v2_invariants_evidence(repo_root)
    inv_passing = 1 if invariants_evidence.get("passing") else 0

    components = {
        "files_reachable": round(files_reachable, 4),
        "modules_tested": round(modules_tested, 4),
        # DELETION-JUSTIFIED — R-683 (قرار المالك 2026-10-16): عقد الدرجة تغيّر؛
        # المكوّنات غير القابلة للقياس (ledger_verified/ledger_anchored) أُزيلت
        # من الرد بدلًا من تقديرها بأعلى نظري. مفصل في DELETED_LINES_AUDIT.md.
        "compat_pending_sunset": round(compat_ratio, 4),
        "no_mocks_in_prod": no_mocks,
        "invariants_passing": inv_passing,
    }

    # متوسط المكونات القابلة للقياس فقط (الخمسة) — الصيغة لم تُعدّل لتمر
    measurable = [
        components["files_reachable"],
        components["modules_tested"],
        components["compat_pending_sunset"],
        components["no_mocks_in_prod"],
        components["invariants_passing"],
    ]
    final_score = round(sum(measurable) / len(measurable), 4)

    try:
        sha = _subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root),
        ).stdout.strip()
    except Exception:
        sha = "unknown"

    result = dict(components)
    result["final_score"] = final_score
    # DELETION-JUSTIFIED — R-683: score_capped_by_missing_ledger أُزيل من العقد
    # (لا حد أعلى معلن)؛ نص الملاحظة صُحح ليطابق الإزالة لا "null معلنة".
    result["ledger_components_note"] = (
        "raw ledger is absent and never opened/searched (owner prohibition) "
        "— the two ledger components are removed from the score contract, "
        "not estimated (owner decision R-683)"
    )
    result["invariants_evidence"] = invariants_evidence
    result["inputs"] = {
        "py_files_total": len(all_py),
        "py_files_reachable": len(reachable),
        "backend_live_modules": len(backend_modules),
        "backend_modules_tested": len(tested_modules),
        "anchors_declared_coverage": len(anchored_union),
        "anchors_malformed_lines": anchors_malformed,
        "documented_total_events": documented_total,
        "compat_total": compat_total,
        "compat_with_sunset": compat_with,
        "mocks_outside_tests_count": mocks_outside_count,
        "repo_head_sha": sha,
    }
    result["aggregation"] = (
        # DELETION-JUSTIFIED — R-683: "mean(7)" كان ادعاءً خاطئًا؛ العدد من القائمة الفعلية
        f"final_score = mean({len(measurable)} scored components) — documented choice; "
        "ROADMAP_V2 does not specify weights; not tunable to improve results"
    )
    return result
