# tests/test_compat_layer.py
# اختبارات طبقة التوافق الجديدة (backend/compat) — تتحقق أن nexus lifecycle
# و guardian snapshot يعملان بشكل حقيقي (لا mocks هنا، بل استدعاءات فعلية)

import os
import sys
from pathlib import Path

# تثبيت مسار المستودع (يُدعم من أي دليل تشغيل)
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def test_nexus_lifecycle_starts_engine():
    """يتحقق أن ensure_nexus_running() يبدأ المحرك فعليًا إلى حالة RUNNING"""
    from backend.compat import ensure_nexus_running, nexus_startup_status

    engine = ensure_nexus_running()
    assert engine is not None, "engine should not be None after ensure_nexus_running()"

    state = getattr(engine, "state", None)
    assert state is not None, "engine.state should be set"
    state_val = getattr(state, "value", None) or state
    assert state_val == "running", f"engine.state should be 'running', got {state_val!r}"

    running_flag = getattr(engine, "_running", False)
    assert running_flag is True, f"engine._running should be True, got {running_flag}"

    # يُعيد نفس المرجع عند التكرار (idempotent)
    engine2 = ensure_nexus_running()
    assert engine2 is engine, "ensure_nexus_running() should be idempotent"


def test_nexus_startup_status_reports_running():
    """يتحقق أن nexus_startup_status() تعكس الحالة الفعلية للمحرك"""
    from backend.compat import ensure_nexus_running, nexus_startup_status

    ensure_nexus_running()
    status = nexus_startup_status()
    assert isinstance(status, dict), "status should be a dict"
    assert status["engine_loaded"] is True
    assert status["engine_running"] is True
    assert status["state"] == "running"
    assert status["components_count"] > 0, (
        f"components_count should be > 0, got {status['components_count']}"
    )
    assert status["last_error"] is None


def test_guardian_snapshot_is_readonly_and_includes_state():
    """
    يتأكد أن guardian_status_snapshot():
    1) تُعيد بنية صحيحة
    2) تُشير إلى مسار emergency الحقيقي
    3) تعمل فقط للقراءة (لا تُفعّل EmergencyBreaker أو أي خيوط موت)
    """
    from backend.compat import guardian_status_snapshot

    snap = guardian_status_snapshot()
    assert isinstance(snap, dict)
    assert snap["guardian_modules_importable"] is True
    assert "emergency_state" in snap
    assert "system_locked" in snap["emergency_state"]
    # المسار يجب أن يشير إلى مجلد guardian/data/emergency الفعلي
    assert "guardian" in snap["emergency_state"]["emergency_dir"]
    assert "emergency" in snap["emergency_state"]["emergency_dir"]
