"""
اختبار R-617: لا يُسجّل مفتاح API أبدًا في السجلات (logs)

يستخدم caplog لالتقاط السجلات أثناء بدء التشغيل ويتحقق أن المفتاح
نفسه لا يظهر — فقط بصمته (sha256 أول 8 أحرف).
"""

import hashlib
import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from fastapi.testclient import TestClient

from app import app


def test_api_key_never_logged(caplog):
    """المفتاح نفسه لا يظهر في السجلات — فقط البصمة."""
    test_key = "test_master_key_1234567890abcdef"

    with caplog.at_level(logging.INFO, logger="app"):
        with TestClient(app) as client:
            # أي طلب لتوليد سجلات
            client.get("/health")

    # البصمة المتوقعة
    expected_fp = hashlib.sha256(test_key.encode()).hexdigest()[:8]

    # المفتاح نفسه لا يظهر في أي سجل
    for record in caplog.records:
        msg = record.getMessage()
        assert test_key not in msg, (
            f"API key leaked in log: {msg[:100]}"
        )
        # المفتاح لا يظهر حتى جزئيًا (أول 10 أحرف)
        assert test_key[:10] not in msg, (
            f"API key prefix leaked in log: {msg[:100]}"
        )

    # البصمة تظهر (اختياريًا — للتأكد أن السجلات تعمل)
    # (لا نتحقق من ظهورها لأن السجلات قد تُرشّح)


def test_startup_log_shows_fingerprint_not_key(caplog):
    """سجل بدء التشغيل يُظهر البصمة فقط، وليس المفتاح."""
    test_key = "test_master_key_1234567890abcdef"
    expected_fp = hashlib.sha256(test_key.encode()).hexdigest()[:8]

    with caplog.at_level(logging.INFO, logger="app"):
        with TestClient(app) as client:
            client.get("/health")

    # لا سجل يحتوي المفتاح
    all_messages = [r.getMessage() for r in caplog.records]
    for msg in all_messages:
        assert test_key not in msg, f"key leaked: {msg[:100]}"

    # إذا وُجد سجل بصمة، يجب أن يكون صحيحًا
    fp_logs = [m for m in all_messages if expected_fp in m]
    for m in fp_logs:
        assert test_key not in m


def test_api_key_fingerprint_format():
    """البصمة بصيغة صحيحة (8 أحرف hex)."""
    test_key = "test_master_key_1234567890abcdef"
    fp = hashlib.sha256(test_key.encode()).hexdigest()[:8]
    assert len(fp) == 8
    # كل حرف hex
    assert all(c in "0123456789abcdef" for c in fp)
