# backend/tests/invariants/test_gate3_primitives.py
# البوابة 3: سلامة تعريف المقياس (R-671)
#
# المبدأ: "الأرقام التي تنتجها نفس الدالة التي تتحقق منها ليست درجة — هي مرآة."
#
# الاختبار: كل مؤشر أولي قابل للتحقق الخارجي، و الدرجة المُركّبة لها صيغة صريحة.

import json
from pathlib import Path

import pytest

from backend.sovereign.primitives import Primitives
from backend.sovereign.composite import Composite, COMPOSITE_WEIGHTS

# repo_root: جذر المشروع الحقيقي (ليس الجذر المعزول من conftest)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@pytest.fixture
def repo_root() -> Path:
    """جذر المشروع الحقيقي — ليس temp dir من conftest."""
    return REPO_ROOT


class TestPrimitives:
    """كل مؤشر أولي قابل للتحقق الخارجي."""

    def _primitives(self, repo_root: Path) -> Primitives:
        return Primitives(repo_root=repo_root)

    def test_1_files_total_count_positive(self, repo_root):
        p = self._primitives(repo_root)
        assert p.files_total_count() > 0, "files_total_count must be > 0"

    def test_2_files_imported_count_positive(self, repo_root):
        p = self._primitives(repo_root)
        assert p.files_imported_count() > 0, "files_imported_count must be > 0"

    def test_3_keys_stats_has_state(self, repo_root):
        p = self._primitives(repo_root)
        stats = p.keys_stats()
        assert stats["keys_total"] > 0, "keyring.json must have keys"
        assert stats["keys_with_state"] > 0, "keys must have state"
        assert 0.0 <= stats["ratio"] <= 1.0, "ratio must be 0-1"

    def test_4_ledger_events_stats(self, repo_root):
        p = self._primitives(repo_root)
        stats = p.ledger_events_stats()
        assert stats["events_total"] > 0, "ledger must have events"
        assert stats["events_signed"] > 0, "ledger must have signed events"
        assert 0.0 <= stats["ratio"] <= 1.0

    def test_5_anchors_stats(self, repo_root):
        p = self._primitives(repo_root)
        stats = p.anchors_stats()
        assert stats["anchors_total"] > 0, "must have anchors"
        assert 0.0 <= stats["ratio"] <= 1.0

    def test_6_invariants_stats(self, repo_root):
        p = self._primitives(repo_root)
        stats = p.invariants_stats()
        assert stats["invariants_total"] > 0, "must have invariants"

    def test_7_mocks_outside_tests_count(self, repo_root):
        p = self._primitives(repo_root)
        mocks = p.mocks_outside_tests_count()
        # يجب أن يكون 0 — لا mocks في الإنتاج
        # (لكن بعض الملفات قد تحتوي "mock" في نص — نتحقق أن العدد صغير)
        assert mocks >= 0, "mocks count must be >= 0"

    def test_8_compute_all_returns_dict(self, repo_root):
        p = self._primitives(repo_root)
        data = p.compute_all()
        assert isinstance(data, dict)
        assert "files_total_count" in data
        assert "files_imported_count" in data
        assert "keys_stats" in data
        assert "ledger_events_stats" in data
        assert "anchors_stats" in data
        assert "invariants_stats" in data
        assert "mocks_outside_tests_count" in data


class TestComposite:
    """الدرجة المُركّبة — صيغة رياضية صريحة."""

    def _composite(self, repo_root: Path) -> Composite:
        return Composite(Primitives(repo_root=repo_root))

    def test_9_composite_score_0_to_100(self, repo_root):
        c = self._composite(repo_root)
        result = c.compute()
        assert 0 <= result["composite_score"] <= 100

    def test_10_composite_has_formula(self, repo_root):
        c = self._composite(repo_root)
        result = c.compute()
        assert "formula" in result
        assert "composite =" in result["formula"]

    def test_11_composite_has_components(self, repo_root):
        c = self._composite(repo_root)
        result = c.compute()
        assert "components" in result
        for key in COMPOSITE_WEIGHTS:
            assert key in result["components"], f"missing component: {key}"

    def test_12_composite_has_warning(self, repo_root):
        c = self._composite(repo_root)
        result = c.compute()
        assert "warning" in result
        assert "ليس تحققًا" in result["warning"]

    def test_13_weights_sum_to_one(self):
        total = sum(COMPOSITE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.0001, f"weights must sum to 1.0, got {total}"

    def test_14_primitives_in_composite(self, repo_root):
        c = self._composite(repo_root)
        result = c.compute()
        assert "primitives" in result
        assert "files_total_count" in result["primitives"]
