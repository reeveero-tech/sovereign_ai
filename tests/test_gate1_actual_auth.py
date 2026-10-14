"""
اختبار البوابة 1 (إثبات المصادقة الفعلي) — R-652

يختبر المسار الفعلي للمصادقة عبر نقطة نهاية محمية (/api-key):
1. المفتاح الجديد: 200 (يُقبل)
2. المفتاح القديم: 403 (يُرفض)
3. مفتاح خاطئ: 403 (يُرفض)
4. لا اعتماد: 403 (يُرفض)
5. الإجابة لا تُفصح عن المفتاح أو بادئته
6. السجلات لا تحتوي المفتاح

R-652: يستخدم أسرارًا داخل tmp_path (لا يقرأ أسرار المضيف في
مجموعة الاختبارات الاعتيادية). اختبار القبول التشغيلي المنفصل
(test_api_key_rotation_gate1.py) هو مكان التحقق من الاعتماد الحقيقي.

R-653: لا يُستخدم importlib.reload — يُنشئ ConsciousnessField جديدًا
(خيوط خلفية جديدة) و يحوّل app.state إلى كائن جديد، يُكسر اختبارات
أخرى (test_health). بدلاً من ذلك، نُحدّث app_module.SOVEREIGN_API_KEY
مباشرة (متغير module-level).
"""

import hashlib
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from fastapi.testclient import TestClient

# R-652: عزل كامل — جذر مؤقت + مفتاح اختباري
if not os.environ.get("SOVEREIGN_DATA_ROOT"):
    _test_root = tempfile.mkdtemp(prefix="sovereign_auth_test_")
    os.environ["SOVEREIGN_DATA_ROOT"] = _test_root

import app as _app_module
from app import app


class TestActualAuthentication:
    """اختبارات المصادقة الفعلية عبر نقطة نهاية محمية."""

    def _setup_app_key(self, monkeypatch, new_key: str):
        """يُحدّث مفتاح API في app module مباشرة.

        R-653: `importlib.reload` يُنشئ ConsciousnessField جديدًا
        (خيوط خلفية جديدة) في كل اختبار — يسبب أخطاء logging
        و يحوّل app.state إلى كائن جديد. بدلاً من ذلك، نُحدّث
        `app_module.SOVEREIGN_API_KEY` مباشرة (متغير module-level).
        """
        monkeypatch.setattr(
            _app_module, "SOVEREIGN_API_KEY", new_key, raising=False
        )
        return _app_module

    def _load_test_keys(self, tmp_path):
        """يُنشئ مفتاحين اختباريين (جديد و قديم) داخل tmp_path."""
        import secrets
        new_key = secrets.token_urlsafe(32)
        old_key = secrets.token_urlsafe(32)
        # التأكد أنهما مختلفان
        assert new_key != old_key
        return new_key, old_key

    def test_new_key_accepted_200(self, tmp_path, monkeypatch):
        """المفتاح الجديد: 200 (يُقبل عبر نقطة نهاية محمية)."""
        new_key, old_key = self._load_test_keys(tmp_path)
        # R-653: تعيين مفتاح API مباشرة (بدون reload)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        r = client.get("/api-key", params={"master_key": new_key})
        assert r.status_code == 200, (
            f"new key must be accepted (200), got {r.status_code}: {r.text[:100]}"
        )
        # الإجابة لا تُفصح عن المفتاح
        assert new_key not in r.text, "response must not contain the key"
        assert new_key[:10] not in r.text, "response must not contain key prefix"

    def test_old_key_rejected_403(self, tmp_path, monkeypatch):
        """المفتاح القديم: 403 (يُرفض عبر نقطة نهاية محمية)."""
        new_key, old_key = self._load_test_keys(tmp_path)
        # R-653: المفتاح الجديد هو الاعتماد الفعّال
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        # المفتاح القديم يُرفض (403)
        r = client.get("/api-key", params={"master_key": old_key})
        assert r.status_code == 403, (
            f"old key must be rejected (403), got {r.status_code}"
        )
        # الإجابة لا تُفصح عن المفتاح القديم
        assert old_key not in r.text, "response must not contain old key"

    def test_wrong_key_rejected_403(self, tmp_path, monkeypatch):
        """مفتاح خاطئ: 403 (يُرفض)."""
        new_key, _ = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        wrong_keys = ["wrong_key_123", "", "x", "a" * 43]
        for wk in wrong_keys:
            r = client.get("/api-key", params={"master_key": wk})
            assert r.status_code == 403, (
                f"wrong key must be rejected (403), got {r.status_code} for {wk[:10]}"
            )

    def test_no_credential_rejected_403(self, tmp_path, monkeypatch):
        """لا اعتماد: 403 (يُرفض)."""
        new_key, _ = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        # لا master_key
        r = client.get("/api-key")
        assert r.status_code == 403, (
            f"no credential must be rejected (403), got {r.status_code}"
        )

    def test_response_does_not_leak_key(self, tmp_path, monkeypatch):
        """الإجابة لا تُفصح عن المفتاح أو بادئته (في أي حالة)."""
        new_key, old_key = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        # نجاح (200) — لا يُفصح عن المفتاح
        r_ok = client.get("/api-key", params={"master_key": new_key})
        assert r_ok.status_code == 200
        assert new_key not in r_ok.text
        assert new_key[:10] not in r_ok.text
        assert new_key[-10:] not in r_ok.text

        # فشل (403) — لا يُفصح عن المفتاح
        r_fail = client.get("/api-key", params={"master_key": old_key})
        assert r_fail.status_code == 403
        assert old_key not in r_fail.text
        assert new_key not in r_fail.text

    def test_http_codes_only_no_key_material(self, tmp_path, monkeypatch):
        """تسجيل رموز HTTP فقط — لا مفاتيح أو بادئات في السجلات.

        R-653: httpx (TestClient) يُسجّل رابط الطلب (يحتوي master_key)
        في سجلات httpx — هذا تسريب من المكتبة، ليس من التطبيق.
        نُسكِت سجلات httpx في هذا الاختبار (التطبيق نفسه لا يُسجّل المفتاح).
        """
        new_key, old_key = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        # R-653: إسكات سجلات httpx (يُسجّل رابط الطلب — يحتوي master_key)
        # R-681: httpx >=0.28 uses logger name "httpx2" instead of "httpx".
        # Silence both names to cover old and new httpx versions.
        for logger_name in ("httpx", "httpx2"):
            httpx_logger = logging.getLogger(logger_name)
            httpx_logger.setLevel(logging.WARNING)
            httpx_logger.propagate = False

        import io
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        # نُسجّل من الجذر (التطبيق) — httpx مُسكَت
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        try:
            client = TestClient(app_module.app)
            # نجاح و فشل
            client.get("/api-key", params={"master_key": new_key})
            client.get("/api-key", params={"master_key": old_key})

            log_content = log_capture.getvalue()
            # لا مفاتيح في السجلات
            assert new_key not in log_content, "logs must not contain new key"
            assert old_key not in log_content, "logs must not contain old key"
            assert new_key[:10] not in log_content, "logs must not contain key prefix"
        finally:
            root_logger.removeHandler(handler)
            # استعادة httpx (R-681: كلا الاسمين httpx و httpx2)
            for logger_name in ("httpx", "httpx2"):
                logging.getLogger(logger_name).propagate = True
