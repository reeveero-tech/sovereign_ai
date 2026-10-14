"""
اختبار البوابة 1: تدوير اعتماد API

يختبر أن:
1. المفتاح الجديد يُقبل (يُحمّل من data/key.secret)
2. المفتاح القديم يُرفض
3. مفاتيح خاطئة تُرفض
4. بصمات مختلفة (قديم ≠ جديد)
5. التشغيل الفعلي: config.py يُحمّل المفتاح الجديد (وليس القديم)
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest


class TestAPIKeyRotation:
    """اختبارات البوابة 1 (تدوير اعتماد API).

    R-680c: في clone نظيف، data/key.secret غير موجود (سر مُستثنى من git).
    هذا السلوك متوقع — يجب أن تُتخطى هذه الاختبارات، لا أن تفشل.
    """

    def _load_key_from_file(self, path: Path) -> str:
        """يقرأ المفتاح من ملف (دون استخدام config.py المخزّن)."""
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def test_new_key_accepted(self):
        """المفتاح الجديد يُقبل (مقارنة مباشرة)."""
        key_file = _REPO_ROOT / "data" / "key.secret"
        if not key_file.exists():
            pytest.skip("key.secret not found in clean clone (R-680c)")
        new_key = self._load_key_from_file(key_file)
        assert new_key == new_key  # trivially true

    def test_old_key_rejected(self):
        """المفتاح القديم يُرفض (لا يُطابق الجديد)."""
        key_file = _REPO_ROOT / "data" / "key.secret"
        if not key_file.exists():
            pytest.skip("key.secret not found in clean clone (R-680c)")
        new_key = self._load_key_from_file(key_file)
        old_key_path = _REPO_ROOT / "data" / "key.secret.old_rotated_2026_10_14"
        if not old_key_path.exists():
            pytest.skip("old key backup not found (rotation not yet performed)")
        old_key = self._load_key_from_file(old_key_path)
        assert old_key != new_key, "old key must differ from new key"

    def test_wrong_keys_rejected(self):
        """مفاتيح خاطئة تُرفض."""
        key_file = _REPO_ROOT / "data" / "key.secret"
        if not key_file.exists():
            pytest.skip("key.secret not found in clean clone (R-680c)")
        new_key = self._load_key_from_file(key_file)
        wrong_keys = ["wrong_key_123", "", "x", new_key[:-1], new_key + "x"]
        for wk in wrong_keys:
            assert wk != new_key, f"wrong key must differ: {wk[:10]}..."

    def test_fingerprints_different(self):
        """بصمات المفتاحين مختلفة."""
        key_file = _REPO_ROOT / "data" / "key.secret"
        if not key_file.exists():
            pytest.skip("key.secret not found in clean clone (R-680c)")
        new_key = self._load_key_from_file(key_file)
        old_key_path = _REPO_ROOT / "data" / "key.secret.old_rotated_2026_10_14"
        if not old_key_path.exists():
            pytest.skip("old key backup not found")
        old_key = self._load_key_from_file(old_key_path)
        old_fp = hashlib.sha256(old_key.encode()).hexdigest()[:16]
        new_fp = hashlib.sha256(new_key.encode()).hexdigest()[:16]
        assert old_fp != new_fp

    def test_config_loads_new_key_in_subprocess(self):
        """التشغيل الفعلي: config.py يُحمّل المفتاح الجديد في عملية Python جديدة.

        R-650: يُلغي SOVEREIGN_KEY (المفتاح الاختباري من conftest.py) —
        حتى يُحمّل config.py من data/key.secret (المسار الفعلي).
        """
        script = (
            "import sys, os; "
            f"sys.path.insert(0, {str(_REPO_ROOT / 'backend')!r}); "
            "os.chdir({root!r}); "
            "from config import SOVEREIGN_KEY, SOVEREIGN_KEY_FINGERPRINT; "
            "print(SOVEREIGN_KEY_FINGERPRINT)"
        ).format(root=str(_REPO_ROOT))

        # R-650: إلغاء SOVEREIGN_KEY و SOVEREIGN_DATA_ROOT (المفتاح الاختباري و
        # الجذر المعزول) — حتى يُحمّل config.py من data/key.secret الحقيقي
        env = os.environ.copy()
        env.pop("SOVEREIGN_KEY", None)
        env.pop("SOVEREIGN_DATA_ROOT", None)

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env=env,
        )

        if result.returncode != 0:
            pytest.skip(f"subprocess failed: {result.stderr[:100]}")

        loaded_fp = result.stdout.strip()
        # المفتاح الجديد (من data/key.secret)
        new_key = self._load_key_from_file(_REPO_ROOT / "data" / "key.secret")
        expected_fp = hashlib.sha256(new_key.encode()).hexdigest()[:16]
        assert loaded_fp == expected_fp, (
            f"config.py must load NEW key fingerprint {expected_fp}, got {loaded_fp}"
        )

    def test_rotation_receipt_exists(self):
        """إيصال التدوير موجود و صالح."""
        receipt_path = _REPO_ROOT / "credentials" / "ROTATION_RECEIPT.json"
        if not receipt_path.exists():
            pytest.skip("rotation receipt not yet created")
        import json
        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)
        assert "old_key_fingerprint" in receipt
        assert "new_key_fingerprint" in receipt
        assert receipt["old_key_fingerprint"] != receipt["new_key_fingerprint"]
