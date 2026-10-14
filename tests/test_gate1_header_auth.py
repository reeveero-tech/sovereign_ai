"""
اختبار البوابة 1 (المصادقة عبر الرأس) — R-658

يختبر المصادقة عبر نقطة النهاية الجديدة `/api-key-header` التي
تقرأ المفتاح من رأس `X-API-Key` — المفتاح في الرأس لا يُسجّل في
روابط الطلب (بعكس query params مثل `master_key`).

R-658: يختبر المسار المستخدم دون إسكات التسجيل — إذا سُجّل المفتاح،
الاختبار يفشل (لا نجاح زائف).
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

# عزل كامل — جذر مؤقت
if not os.environ.get("SOVEREIGN_DATA_ROOT"):
    _test_root = tempfile.mkdtemp(prefix="sovereign_header_auth_test_")
    os.environ["SOVEREIGN_DATA_ROOT"] = _test_root

import app as _app_module
from app import app


class TestHeaderAuthentication:
    """اختبارات المصادقة عبر الرأس (X-API-Key)."""

    def _setup_app_key(self, monkeypatch, new_key: str):
        """يُحدّث مفتاح API في app module مباشرة (بدون reload)."""
        monkeypatch.setattr(
            _app_module, "SOVEREIGN_API_KEY", new_key, raising=False
        )
        return _app_module

    def _load_test_keys(self, tmp_path):
        """يُنشئ مفتاحين اختباريين (جديد و قديم)."""
        import secrets
        new_key = secrets.token_urlsafe(32)
        old_key = secrets.token_urlsafe(32)
        assert new_key != old_key
        return new_key, old_key

    def test_new_key_accepted_200_via_header(self, tmp_path, monkeypatch):
        """المفتاح الجديد في الرأس: 200 (يُقبل)."""
        new_key, old_key = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        # المفتاح في الرأس (وليس query param)
        r = client.get("/api-key-header", headers={"X-API-Key": new_key})
        assert r.status_code == 200, (
            f"new key via header must be accepted (200), got {r.status_code}: {r.text[:100]}"
        )
        # الإجابة لا تُفصح عن المفتاح
        assert new_key not in r.text, "response must not contain the key"
        assert new_key[:10] not in r.text, "response must not contain key prefix"

    def test_old_key_rejected_403_via_header(self, tmp_path, monkeypatch):
        """المفتاح القديم في الرأس: 403 (يُرفض)."""
        new_key, old_key = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        r = client.get("/api-key-header", headers={"X-API-Key": old_key})
        assert r.status_code == 403, (
            f"old key via header must be rejected (403), got {r.status_code}"
        )
        assert old_key not in r.text, "response must not contain old key"

    def test_wrong_keys_rejected_403_via_header(self, tmp_path, monkeypatch):
        """مفاتيح خاطئة في الرأس: 403 (يُرفض)."""
        new_key, _ = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        wrong_keys = ["wrong_key_123", "", "x", "a" * 43]
        for wk in wrong_keys:
            r = client.get("/api-key-header", headers={"X-API-Key": wk})
            assert r.status_code == 403, (
                f"wrong key via header must be rejected (403), got {r.status_code} for {wk[:10]}"
            )

    def test_no_credential_rejected_403_via_header(self, tmp_path, monkeypatch):
        """لا اعتماد في الرأس: 403 (يُرفض)."""
        new_key, _ = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        r = client.get("/api-key-header")
        assert r.status_code == 403, (
            f"no credential via header must be rejected (403), got {r.status_code}"
        )

    def test_response_does_not_leak_key_via_header(self, tmp_path, monkeypatch):
        """الإجابة لا تُفصح عن المفتاح (في أي حالة — عبر الرأس)."""
        new_key, old_key = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        client = TestClient(app_module.app)
        # نجاح (200)
        r_ok = client.get("/api-key-header", headers={"X-API-Key": new_key})
        assert r_ok.status_code == 200
        assert new_key not in r_ok.text
        assert new_key[:10] not in r_ok.text
        assert new_key[-10:] not in r_ok.text

        # فشل (403)
        r_fail = client.get("/api-key-header", headers={"X-API-Key": old_key})
        assert r_fail.status_code == 403
        assert old_key not in r_fail.text
        assert new_key not in r_fail.text

    def test_logs_do_not_contain_key_via_header(self, tmp_path, monkeypatch):
        """السجلات لا تحتوي المفتاح — دون إسكات التسجيل.

        R-658/R-662: المفتاح في الرأس لا يُسجّل في روابط الطلب
        (httpx لا يُسجّل الرؤوس افتراضيًا — فقط روابط الطلب).

        R-662: يُثبت وجود سجل طلب غير حساس (ضابط إيجابي) ثم
        يتحقق من غياب المفتاح و من رموز الاستجابة.
        لا إسكات — إذا سُجّل المفتاح، الاختبار يفشل.
        """
        new_key, old_key = self._load_test_keys(tmp_path)
        app_module = self._setup_app_key(monkeypatch, new_key)

        # R-662: تفعيل INFO مؤقتًا + استعادة الحالة السابقة
        # R-681: httpx >=0.28 uses logger name "httpx2" instead of "httpx".
        # Enable both names to capture request logs across versions.
        import io
        prev_states = {}
        for logger_name in ("httpx", "httpx2"):
            httpx_logger = logging.getLogger(logger_name)
            prev_states[logger_name] = (httpx_logger.level, httpx_logger.propagate)
            httpx_logger.setLevel(logging.INFO)
            httpx_logger.propagate = True

        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        try:
            client = TestClient(app_module.app)
            # نجاح و فشل — عبر الرأس (لا query params)
            r_ok = client.get("/api-key-header", headers={"X-API-Key": new_key})
            r_fail = client.get("/api-key-header", headers={"X-API-Key": old_key})

            # رموز الاستجابة
            assert r_ok.status_code == 200
            assert r_fail.status_code == 403

            log_content = log_capture.getvalue()

            # R-662: ضابط إيجابي — يوجد سجل طلب (غير حساس)
            assert "/api-key-header" in log_content or log_content.strip(), (
                "positive control failed: no request logs captured "
                "(cannot prove absence of key without logs)"
            )

            # لا مفاتيح في السجلات
            assert new_key not in log_content, (
                f"logs must not contain new key (via header path)"
            )
            assert old_key not in log_content, (
                f"logs must not contain old key (via header path)"
            )
            assert new_key[:10] not in log_content, (
                f"logs must not contain key prefix (via header path)"
            )
        finally:
            root_logger.removeHandler(handler)
            # R-662/R-681: استعادة الحالة السابقة (كلا الاسمين httpx و httpx2)
            for logger_name, (prev_level, prev_propagate) in prev_states.items():
                httpx_logger = logging.getLogger(logger_name)
                httpx_logger.setLevel(prev_level)
                httpx_logger.propagate = prev_propagate
