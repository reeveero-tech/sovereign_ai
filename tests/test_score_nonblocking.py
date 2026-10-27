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
    _reset_state(app_mod, monkeypatch)
    return calls


def _reset_state(app_mod, monkeypatch):
    for k, v in (("result", None), ("ts", 0.0), ("computing", False),
                 ("started", 0.0), ("error", None)):
        monkeypatch.setitem(app_mod._SCORE_STATE, k, v)


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


# ---------------------------------------------------------------------------
# R-788a: الطلب لا ينتظر حسابًا طويلًا + المحور لم يعد صفرًا بخطأ مفتاح + تصنيف تزايدي
# ---------------------------------------------------------------------------

def test_request_returns_202_computing_instead_of_hanging(slow_score, monkeypatch):
    monkeypatch.setenv("SOVEREIGNTY_SCORE_WAIT", "0.1")
    with _client() as c:
        t = time.perf_counter()
        r = c.get("/sovereignty/score")
        elapsed = time.perf_counter() - t
        assert r.status_code == 202 and r.json()["status"] == "computing"
        assert elapsed < 1.0, f"request waited {elapsed:.2f}s"
        time.sleep(1.8)  # الخيط الخلفي ينهي الحساب
        r2 = c.get("/sovereignty/score")
    assert r2.status_code == 200 and r2.json()["total_score"] == 42
    assert r2.json()["cache"]["stale"] is False
    assert len(slow_score) == 1


def test_stale_result_served_with_age_while_refreshing(slow_score, monkeypatch):
    import app as app_mod
    monkeypatch.setenv("SOVEREIGNTY_SCORE_WAIT", "0.05")
    monkeypatch.setitem(app_mod._SCORE_STATE, "result", {"total_score": 7})
    monkeypatch.setitem(app_mod._SCORE_STATE, "ts", time.time() - 10_000)
    with _client() as c:
        body = c.get("/sovereignty/score").json()
        time.sleep(1.8)
    assert body["total_score"] == 7
    assert body["cache"]["stale"] is True and body["cache"]["refreshing"] is True
    assert body["cache"]["age_s"] >= 9_000


def test_compute_error_is_reported_not_hidden(monkeypatch):
    import app as app_mod

    def boom():
        raise RuntimeError("disk gone")

    monkeypatch.setattr(app_mod, "_sovereignty_score_payload", boom)
    _reset_state(app_mod, monkeypatch)
    with _client() as c:
        r = c.get("/sovereignty/score")
    assert r.status_code == 503 and "disk gone" in r.json()["detail"]


def test_score_tool_uses_cache_not_direct_compute(slow_score):
    import app as app_mod  # noqa: F401  (تسجيل الأدوات عند الاستيراد)
    from tool_registry import get_registry
    spec = get_registry()._tools["sovereignty.score"]
    a = spec.handler()
    b = spec.handler()
    assert a["total_score"] == b["total_score"] == 42
    assert len(slow_score) == 1, "the tool must reuse the shared cache"


class _FakeStatus:
    def __init__(self, v):
        self.value = v


class _FakeResult:
    def __init__(self, v):
        self.status = _FakeStatus(v)


class _CountingVerifier:
    def __init__(self):
        self.calls = 0

    def verify_event(self, ev):
        self.calls += 1
        return _FakeResult("verified" if ev.get("ok") else "invalid")


class _FakeKeyring:
    def __init__(self, status="active"):
        self.status = status

    def list_keys(self):
        class R:
            key_id, public_key, key_type = "k1", "pub", "ed25519"
        r = R()
        r.status = _FakeStatus(self.status)
        return [r]


def _lines(n, bad=()):
    import json
    return [json.dumps({"i": i, "ok": i not in bad}) for i in range(n)]


def test_incremental_classification_reuses_only_identical_prefix():
    from backend.sovereign import score as sc
    path = f"/tmp/r788a-{time.time()}"
    kr = _FakeKeyring()
    v = _CountingVerifier()
    lines = _lines(100, bad={5})
    assert sc._classify_ledger_incremental(path, lines, kr, v) == 1 and v.calls == 100
    lines += _lines(110, bad={105})[100:]
    assert sc._classify_ledger_incremental(path, lines, kr, v) == 2 and v.calls == 110
    # عبث بسطر قديم ⇒ إعادة تصنيف كاملة (لا تُخفيه الذاكرة)
    import json
    lines[7] = json.dumps({"i": 7, "ok": False})
    assert sc._classify_ledger_incremental(path, lines, kr, v) == 3 and v.calls == 220
    # تغيّر حالة مفتاح ⇒ إعادة كاملة
    assert sc._classify_ledger_incremental(path, lines, _FakeKeyring("compromised"), v) == 3
    assert v.calls == 330


def test_ledger_axis_no_longer_crashes_on_missing_verified_key(monkeypatch):
    from backend.sovereign import score as sc
    import backend.sovereign.ledger as ledger_mod
    import backend.sovereign.keys as keys_mod

    class FakeAnchor:
        ledger_path = f"/tmp/r788a-axis-{time.time()}"

        def read_ledger_lines(self):
            return _lines(10)

        def list_anchors(self):
            return []

        def verify_all_anchors(self):  # العقد الحقيقي (R-642) — بلا مفتاح "verified"
            return {"total_anchors": 0, "root_verified_count": 0, "trusted_count": 0,
                    "failed": 0, "details": []}

    class FakeKR(_FakeKeyring):
        def load_from_disk(self):
            pass

    monkeypatch.setattr(ledger_mod, "LedgerAnchor", FakeAnchor)
    monkeypatch.setattr(keys_mod, "KeyRing", FakeKR)
    monkeypatch.setattr(keys_mod, "SignatureVerifier", lambda kr: _CountingVerifier())
    axis = sc.SovereigntyScorer()._score_ledger_integrity()
    assert not any("ledger integrity check failed" in i for i in axis.issues), axis.issues
    assert axis.details["unclassified_events"] == 0
    assert axis.details["anchors_verified"] == 0
    assert axis.score == 50  # 0 تغطية + 30 تصنيف + 20 مراسٍ سليمة (لا فشل)
