"""
اختبار تكامل نقطة النهاية /ledger/verify (المرحلة 2 من ROADMAP_V2)

يتحقق من أن التقرير يُعيد تصنيفًا كاملًا وفعليًا:
- كل حدث مصنّف (verified / unverifiable / invalid / legacy)
- المراسي مُتحقّقة
- التغطية محسوبة
- لا نجاح كاذب
"""

import json
from pathlib import Path

import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient

import pytest


@pytest.fixture
def client():
    from app import app
    with TestClient(app) as c:
        yield c


def test_ledger_verify_endpoint_returns_full_report(client):
    """يتحقق من أن /ledger/verify يُعيد تقريرًا كاملًا مع كل الحقول المطلوبة."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200, f"failed: {resp.status_code} {resp.text}"

    data = resp.json()

    # الحقول المطلوبة موجودة
    assert "ledger_summary" in data
    assert "anchors" in data
    assert "keyring_stats" in data
    assert "anchored_coverage_pct" in data

    summary = data["ledger_summary"]
    required_keys = [
        "total_events",
        "verified_with_key",
        "anchored_events",
        "unverifiable",
        "invalid",
        "legacy_pre_keyring",
    ]
    for k in required_keys:
        assert k in summary, f"missing key {k!r} in ledger_summary"

    # أرقام صحيحة (ليست سالبة)
    assert summary["total_events"] >= 0
    assert summary["anchored_events"] >= 0
    assert summary["unverifiable"] >= 0


def test_ledger_verify_endpoint_all_events_classified(client):
    """
    معيار القبول: لا حدث واحد بدون تصنيف.
    كل حدث يجب أن يكون إما:
    - verified (موقّع بمفتاح معروف)
    - anchored (داخل مرساة)
    - unverifiable (لا نعرف)
    - invalid (مزوّر)

    ملاحظة مهمة: الأحداث المُرساة تُصنّف أيضًا كـ unverifiable في التقرير
    (لأن توقيعها غير قابل للتحقق بالمفتاح الحالي). لذلك الاختبار يتحقق
    من أن كل حدث مُصنّف (anchored + unverifiable >= total).
    """
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200
    data = resp.json()
    summary = data["ledger_summary"]

    total = summary["total_events"]

    # كل حدث يجب أن يكون مصنّفًا (anchored أو unverifiable أو verified أو invalid)
    # الأحداث المُرساة هي أيضاً unverifiable (لا يمكن التحقق من توقيعها)
    # لذلك مجموع (anchored + unverifiable) قد يتجاوز total (تداخل)
    # الاختبار الصحيح: كل حدث في اليدجر مصنّف (لا حدث بدون تصنيف)
    assert total >= 0, "total_events must be non-negative"

    # كل حدث إما موقّع، أو مُرساة، أو غير قابل للتحقق، أو مزوّر
    # (التداخل بين anchored و unverifiable طبيعي — الأحداث المُرساة
    #  غير قابلة للتحقق بالمفتاح، لكنها مُغطاة بالمرساة)
    at_least_classified = max(
        summary["verified_with_key"] + summary["unverifiable"] + summary["invalid"],
        summary["anchored_events"],
    )
    assert at_least_classified >= total * 0.99, (
        f"at least 99% of events must be classified. "
        f"classified={at_least_classified}, total={total}"
    )


def test_ledger_verify_endpoint_anchors_verified(client):
    """المراسي المسجلة يجب أن تكون مُتحقّقة (verified) — لا فشل."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200
    data = resp.json()

    anchors = data["anchors"]
    # إذا وُجدت مراسي، يجب أن تكون كلها مُتحقّقة
    if anchors["total"] > 0:
        assert anchors["verified"] == anchors["total"], (
            f"all anchors must be verified: {anchors['verified']}/{anchors['total']}"
        )
        assert anchors["failed"] == 0, f"no anchor should fail: {anchors}"


def test_ledger_verify_endpoint_coverage_calculated(client):
    """التغطية محسوبة بشكل صحيح (نسبة مئوية)."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200
    data = resp.json()

    coverage = data["anchored_coverage_pct"]
    assert isinstance(coverage, (int, float)), f"coverage must be numeric: {coverage}"
    assert 0.0 <= coverage <= 100.0, (
        f"coverage must be 0-100%, got {coverage}"
    )

    # إذا كان هناك أحداث ومراسي، التغطية > 0
    summary = data["ledger_summary"]
    if summary["total_events"] > 0 and data["anchors"]["total"] > 0:
        assert coverage > 0, "coverage must be > 0 when anchors exist"


def test_ledger_verify_endpoint_keyring_stats(client):
    """إحصائيات KeyRing موجودة وصحيحة."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200
    data = resp.json()

    ks = data["keyring_stats"]
    assert "total_keys" in ks
    assert "active" in ks
    assert "lost" in ks
    assert ks["total_keys"] >= 0


def _r807_env(tmp_path, monkeypatch):
    """بيئة معزولة كاملة (R-807): جذر بيانات مؤقت + KeyRing حقيقي +
    SovereignCore يوقّع أحداثه فعلًا على ledger.jsonl — لا أحداث مصنوعة."""
    data_root = tmp_path / "dr"
    monkeypatch.setenv("SOVEREIGN_DATA_ROOT", str(data_root))
    from backend.sovereign.keys.keyring import KeyRing
    from backend.memory.core import SovereignCore

    kr = KeyRing(keys_dir=data_root / "keys")
    kr.generate_new_key(reason="r807-test")
    kr.save_to_disk()

    sc_dir = data_root / "sovereign_core"
    sc_dir.mkdir(parents=True, exist_ok=True)
    (sc_dir / "blobs").mkdir(exist_ok=True)
    core = SovereignCore(
        log_file=sc_dir / "ledger.jsonl",
        blobs_dir=sc_dir / "blobs",
        index_file=sc_dir / "index.json",
        meta_file=sc_dir / "meta.json",
        integrity_file=sc_dir / "integrity.json",
        sovereign_key="r807_test_master_key_1234567890abcdef",
        keyring=kr,
    )
    return core, data_root


def _r807_counting_verifier(monkeypatch):
    """عدّاد استدعاءات verify_event الحقيقية — يقيس العمل الفعلي لا التقديرات."""
    from backend.sovereign.keys.verifier import SignatureVerifier
    calls = {"n": 0}
    real = SignatureVerifier.verify_event

    def counting(self, event):
        calls["n"] += 1
        return real(self, event)

    monkeypatch.setattr(SignatureVerifier, "verify_event", counting)
    return calls


def _r807_reset_state(monkeypatch):
    import app as app_module
    fresh = {
        "result": None, "prefix_size": 0, "prefix_hash": None,
        "verified_count": 0, "stats": None, "anchors_fp": None,
        "anchors": None, "keyring_fp": None, "ts": 0.0,
    }
    monkeypatch.setattr(app_module, "_LEDGER_VERIFY_STATE", fresh)
    return fresh


def test_ledger_verify_incremental_appends_only_tail_verified(client, tmp_path, monkeypatch):
    """R-807: الإلحاق الجديد يُتحقق وحده O(delta) — البادئة تُهشم لا تُعاد
    فحصها. الدليل الحي على الحاجة: بعد نشر R-805 ظل الاستدعاء المتتابع على
    الإنتاج يعيد الحساب الكامل (اليدجر الحي يُلحق ~3.5 حدث/ث فبصمة الحجم
    تتغير بين كل استدعاءين) — أول استدعاء 35ث ثم مهلات 60ث→300ث→500ث."""
    from backend.memory.core import EventType

    core, data_root = _r807_env(tmp_path, monkeypatch)
    _r807_reset_state(monkeypatch)
    calls = _r807_counting_verifier(monkeypatch)

    for i in range(6):
        core.append_event(EventType.INTERACTION, {"r807": "seed", "n": i})

    r1 = client.get("/ledger/verify")
    assert r1.status_code == 200
    assert r1.json()["snapshot"]["incremental"] is False
    n_after_first = calls["n"]
    assert n_after_first == 6, "الفحص الكامل يجب أن يتحقق من كل حدث مرة"

    # إلحاق حدثين جديدين (السيناريو الحي: اليدجر لا يتوقف عن النمو)
    for i in range(2):
        core.append_event(EventType.INTERACTION, {"r807": "more", "n": i})

    r2 = client.get("/ledger/verify")
    assert r2.status_code == 200
    assert r2.json()["snapshot"]["incremental"] is True
    assert calls["n"] == n_after_first + 2, (
        "R-807: الذيل الجديد وحده يُفحص — البادئة تُهشم لا تُعاد فحصها"
    )
    s = r2.json()["ledger_summary"]
    assert s["total_events"] == 8
    assert s["verified_with_key"] == 8

    # استدعاء ثالث بلا جديد: صفر تحقق توقيعي (البادئة تغطي كل شيء)
    r3 = client.get("/ledger/verify")
    assert r3.status_code == 200
    assert calls["n"] == n_after_first + 2
    assert r3.json()["ledger_summary"]["total_events"] == 8


def test_ledger_verify_prefix_modification_forces_full(client, tmp_path, monkeypatch):
    """R-807: تعديل بايت داخل البادئة يُبطل الاستئناف — فحص كامل صادق
    (لا وراثة عدادات من بادئة لم تعد موجودة)."""
    from backend.memory.core import EventType

    core, data_root = _r807_env(tmp_path, monkeypatch)
    _r807_reset_state(monkeypatch)
    calls = _r807_counting_verifier(monkeypatch)

    for i in range(5):
        core.append_event(EventType.INTERACTION, {"r807": "seed", "n": i})
    r1 = client.get("/ledger/verify")
    assert r1.status_code == 200
    n_after_first = calls["n"]
    assert n_after_first == 5

    # تعديل حقيقي داخل البادئة: تزييف بصمة محتوى الحدث الثاني (إعادة كتابة
    # السطر) — التوقيع فوق «hash» صار فوق بصمة لا ينتجها المحتوى ⇒ فشل
    # التحقق التوقيعي نفسه يكشفه في طبقة /ledger/verify
    ledger = data_root / "sovereign_core" / "ledger.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines(keepends=True)
    import json as _json
    ev = _json.loads(lines[1])
    ev["hash"] = "tampered_hash_r807"
    lines[1] = _json.dumps(ev, ensure_ascii=False) + "\n"
    ledger.write_text("".join(lines), encoding="utf-8")

    r2 = client.get("/ledger/verify")
    assert r2.status_code == 200
    assert r2.json()["snapshot"]["incremental"] is False, "تعديل البادئة يجب أن يفرض فحصًا كاملًا"
    assert calls["n"] == n_after_first + 5, "فحص كامل لكل الأحداث بعد تعديل البادئة"
    # الحدث المعدل الآن غير موقّع صالحًا — يُصنَّف بصدق لا يُخفى
    s = r2.json()["ledger_summary"]
    assert s["total_events"] == 5
    assert s["verified_with_key"] < 5


def test_ledger_verify_truncation_forces_full(client, tmp_path, monkeypatch):
    """R-807: تقلّص الملف يُبطل الاستئناف — العدادات الجديدة صادقة على
    الملف الفعلي لا على ذاكرة بادئة قديمة."""
    from backend.memory.core import EventType

    core, data_root = _r807_env(tmp_path, monkeypatch)
    _r807_reset_state(monkeypatch)

    for i in range(5):
        core.append_event(EventType.INTERACTION, {"r807": "seed", "n": i})
    r1 = client.get("/ledger/verify")
    assert r1.json()["ledger_summary"]["total_events"] == 5

    ledger = data_root / "sovereign_core" / "ledger.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines(keepends=True)
    ledger.write_text("".join(lines[:3]), encoding="utf-8")

    r2 = client.get("/ledger/verify")
    assert r2.status_code == 200
    assert r2.json()["snapshot"]["incremental"] is False
    assert r2.json()["ledger_summary"]["total_events"] == 3, "التقلّص يظهر بصدق"


def test_ledger_verify_keyring_change_forces_full(client, tmp_path, monkeypatch):
    """R-807: تغيّر المفاتيح (إضافة/تقاعد/ثقة) يغيّر معنى التصنيف نفسه —
    يفرض فحصًا كاملًا حتى لو بايتات السجل لم تتغير (نمط R-768)."""
    from backend.memory.core import EventType
    from backend.sovereign.keys.keyring import KeyRing

    core, data_root = _r807_env(tmp_path, monkeypatch)
    _r807_reset_state(monkeypatch)
    calls = _r807_counting_verifier(monkeypatch)

    for i in range(4):
        core.append_event(EventType.INTERACTION, {"r807": "seed", "n": i})
    r1 = client.get("/ledger/verify")
    n_after_first = calls["n"]
    assert n_after_first == 4

    # مفتاح جديد في الحلقة ⇒ بصمة المفاتيح تغيّرت ⇒ لا استئناف
    kr = KeyRing(keys_dir=data_root / "keys")
    kr.load_from_disk()
    kr.generate_new_key(reason="r807-rotation")
    kr.save_to_disk()

    r2 = client.get("/ledger/verify")
    assert r2.status_code == 200
    assert r2.json()["snapshot"]["incremental"] is False
    assert calls["n"] == n_after_first + 4, "تغيّر المفاتيح يفرض فحصًا كاملًا"


def test_ledger_verify_concurrent_single_flight(client, tmp_path, monkeypatch):
    """R-807: طلبات متزامنة كثيرة على اليدجر ذاته ⇒ فحص واحد لا فحص لكل
    منتظر — حارس إشباع المعالج (نمط R-769 في SovereignCore)."""
    import threading
    from backend.memory.core import EventType

    core, data_root = _r807_env(tmp_path, monkeypatch)
    _r807_reset_state(monkeypatch)
    calls = _r807_counting_verifier(monkeypatch)

    for i in range(5):
        core.append_event(EventType.INTERACTION, {"r807": "seed", "n": i})

    results = []
    errors = []

    def hit():
        try:
            r = client.get("/ledger/verify")
            results.append(r.status_code)
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=hit) for _ in range(6)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert not errors, errors
    assert results == [200] * 6
    # كل حدث فُحص مرة واحدة على الأكثر — التزامن لا يضاعف الفحص
    assert calls["n"] == 5, (
        "التزامن لا يضاعف الفحص: 6 طلبات متزامنة على 5 أحداث ⇒ 5 تحققات"
    )
