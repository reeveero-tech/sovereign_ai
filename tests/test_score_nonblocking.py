"""R-788: /sovereignty/score لا يحجب الخادم + تحقق Ed25519 سريع بالدلالة نفسها.

الدليل الحي (2026-10-27): طلب واحد GET /sovereignty/score على الإنتاج ⇒ /health بلا رد
دقائق، فحص Fly «critical»، حمل 3.3 على نواة مشتركة واحدة؛ py-spy: MainThread داخل
_score_ledger_integrity → verify_event → pycryptodome eddsa (حساب نقاط بـPython) لكل
حدث من 138k. الإصلاح: نمط R-762 (دالة متزامنة + single-flight) + تخزين مؤقت + مسار OpenSSL.
"""

import inspect
import threading
import time

import pytest


def _client():
    from app import app as fastapi_app
    from fastapi.testclient import TestClient
    return TestClient(fastapi_app)


@pytest.fixture
def slow_score(monkeypatch):
    import app as app_mod
    calls = []

    def slow():
        calls.append(time.time())
        time.sleep(1.5)
        return {"total_score": 42, "calls": len(calls)}

    monkeypatch.setattr(app_mod, "_sovereignty_score_payload", slow)
    monkeypatch.setitem(app_mod._SCORE_STATE, "result", None)
    monkeypatch.setitem(app_mod._SCORE_STATE, "ts", 0.0)
    return calls


def test_score_endpoint_is_not_a_coroutine():
    import app as app_mod
    assert not inspect.iscoroutinefunction(app_mod.sovereignty_score), \
        "async def runs the O(n) ledger walk inside the event loop"


def test_health_stays_responsive_while_score_computes(slow_score):
    with _client() as c:
        t = threading.Thread(target=lambda: c.get("/sovereignty/score"))
        t.start()
        time.sleep(0.2)
        start = time.perf_counter()
        r = c.get("/health")
        elapsed = time.perf_counter() - start
        t.join()
    assert r.status_code == 200
    assert elapsed < 1.0, f"/health blocked {elapsed:.2f}s behind /sovereignty/score"


def test_concurrent_score_requests_single_flight_then_cached(slow_score):
    results = []
    with _client() as c:
        ts = [threading.Thread(target=lambda: results.append(c.get("/sovereignty/score").json()))
              for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        again = c.get("/sovereignty/score").json()
    assert len(slow_score) == 1, f"expected one computation, got {len(slow_score)}"
    assert all(r["total_score"] == 42 for r in results) and again["total_score"] == 42


def test_score_cache_expires(slow_score, monkeypatch):
    monkeypatch.setenv("SOVEREIGNTY_SCORE_TTL", "0")
    with _client() as c:
        c.get("/sovereignty/score")
        c.get("/sovereignty/score")
    assert len(slow_score) == 2


# ---------------------------------------------------------------------------
# المسار السريع: الدلالة نفسها حرفيًا
# ---------------------------------------------------------------------------

def _ed():
    from backend.sovereign.keys import ed25519_verifier as ed
    return ed


def test_fast_path_available_and_matches_legacy_semantics():
    ed = _ed()
    assert ed.FAST_ED25519, "cryptography must be installed (requirements.txt)"
    seed = ed.generate_seed_hex()
    pub = ed.public_from_seed_hex(seed)
    data = "hash|prev|blob|time|type|kid".encode()
    sig = ed.sign_hex(data, seed)
    assert ed._fast_verify(pub, data, sig) is True
    assert ed.verify_hex(pub, data, sig) is True
    tampered = sig[:-2] + ("00" if sig[-2:] != "00" else "11")
    assert ed.verify_hex(pub, data, tampered) is False
    assert ed.verify_hex(pub, data + b"x", sig) is False
    assert ed.verify_hex(pub, data, "zz") is False
    assert ed.verify_hex("00", data, sig) is False
    other = ed.public_from_seed_hex(ed.generate_seed_hex())
    assert ed.verify_hex(other, data, sig) is False


def test_legacy_path_alone_when_fast_unavailable(monkeypatch):
    ed = _ed()
    monkeypatch.setattr(ed, "FAST_ED25519", False)
    seed = ed.generate_seed_hex()
    pub = ed.public_from_seed_hex(seed)
    sig = ed.sign_hex(b"abc", seed)
    assert ed._fast_verify(pub, b"abc", sig) is False
    assert ed.verify_hex(pub, b"abc", sig) is True
    assert ed.verify_hex(pub, b"abd", sig) is False


def test_fast_path_is_materially_faster():
    ed = _ed()
    seed = ed.generate_seed_hex()
    pub = ed.public_from_seed_hex(seed)
    sig = ed.sign_hex(b"x" * 200, seed)
    t = time.perf_counter()
    for _ in range(200):
        assert ed.verify_hex(pub, b"x" * 200, sig)
    per_ms = (time.perf_counter() - t) / 200 * 1000
    assert per_ms < 1.0, f"{per_ms:.3f}ms per verify — fast path not in use"
