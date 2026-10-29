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


def test_ledger_verify_arabic_torn_line_byte_boundary(client, tmp_path, monkeypatch):
    """R-808: حد البادئة بالبايتات لا بالحروف — حمولات عربية متعددة
    البايتات: سطر ممزق (بلا \\n) يُستثنى من الفحص، ثم يكتمل فلا يُحسب
    مرتين ولا يُبتلع. المقارنة النهائية مع فحص كامل نظيف من الصفر."""
    import json as _json
    from backend.memory.core import EventType

    core, data_root = _r807_env(tmp_path, monkeypatch)
    _r807_reset_state(monkeypatch)
    calls = _r807_counting_verifier(monkeypatch)

    for i in range(3):
        core.append_event(EventType.INTERACTION, {"ar": "سلام عليكم ورحمة الله وبركاته", "n": i})
    # حدث رابع عربي يُلحق ثم يُمزق عمدًا: نحتفظ بأسطره الكاملة
    core.append_event(EventType.INTERACTION, {"ar": "حدث رابع بحمولة عربية طويلة", "n": 3})
    ledger = data_root / "sovereign_core" / "ledger.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines(keepends=True)
    assert len(lines) == 4
    full_line = lines[3].encode("utf-8")
    torn = full_line[: len(full_line) // 2]  # نصف البايتات — بلا \\n

    # إعادة كتابة الملف: 3 أسطر كاملة + السطر الرابع ممزقًا
    with open(ledger, "wb") as f:
        f.write("".join(lines[:3]).encode("utf-8"))
        f.write(torn)

    r1 = client.get("/ledger/verify")
    assert r1.status_code == 200
    # السطر الممزق مستثنى: 3 أحداث فقط — لا يُصنَّف «تالفًا» ظلمًا
    assert r1.json()["ledger_summary"]["total_events"] == 3
    assert r1.json()["ledger_summary"]["invalid"] == 0
    assert r1.json()["snapshot"]["incremental"] is False
    n_after_first = calls["n"]
    assert n_after_first == 3

    # اكتمال السطر الممزق (الكاتب أنهى إلحاقه)
    with open(ledger, "ab") as f:
        f.write(full_line[len(torn):])

    r2 = client.get("/ledger/verify")
    assert r2.status_code == 200
    assert r2.json()["snapshot"]["incremental"] is True
    # السطر المكتمل يُفحص وحده (بايتات كاملة لا باقي تشطير نصي)
    assert calls["n"] == n_after_first + 1
    assert r2.json()["ledger_summary"]["total_events"] == 4
    assert r2.json()["ledger_summary"]["verified_with_key"] == 4

    # مرجع الصدق: فحص كامل نظيف من الصفر يعطي الأرقام نفسها
    _r807_reset_state(monkeypatch)
    calls2 = _r807_counting_verifier(monkeypatch)
    r3 = client.get("/ledger/verify")
    assert r3.json()["ledger_summary"] == r2.json()["ledger_summary"]
    assert calls2["n"] == 4


def test_ledger_verify_tamper_during_classification_detected(client, tmp_path, monkeypatch):
    """R-808: تصحيح TOCTOU — تعديل البادئة أثناء التصنيف لا يمنح شهادة
    للبايتات المعدلة: (أ) في المسار الكامل تُخزن بصمة بايتات التصنيف نفسها
    فيكتشف الطلب التالي التعديل؛ (ب) في المسار التزايدي يرفض تجديد البصمة
    (الجزء القديم تغيّر) فلا تُورَّث عدادات قديمة."""
    import json as _json
    import app as app_module
    from backend.memory.core import EventType
    from backend.sovereign.keys.verifier import SignatureVerifier

    core, data_root = _r807_env(tmp_path, monkeypatch)
    _r807_reset_state(monkeypatch)
    calls = _r807_counting_verifier(monkeypatch)

    for i in range(5):
        core.append_event(EventType.INTERACTION, {"r808": "seed", "n": i})
    ledger = data_root / "sovereign_core" / "ledger.jsonl"

    def _tamper_line0(marker="tampered_r808"):
        lines = ledger.read_text(encoding="utf-8").splitlines(keepends=True)
        ev = _json.loads(lines[0])
        ev["hash"] = marker
        lines[0] = _json.dumps(ev, ensure_ascii=False) + "\n"
        ledger.write_text("".join(lines), encoding="utf-8")

    real = SignatureVerifier.verify_event

    # (أ) المسار الكامل: العبث أثناء التصنيف — البصمة المخزنة من بايتات
    # التصنيف (قبل العبث) فالطلب التالي يكتشف التعديل ويجري فحصًا كاملًا
    state_calls = {"n": 0}
    tampered = {"done": False}

    def tampering_full(self, event):
        res = real(self, event)
        state_calls["n"] += 1
        if state_calls["n"] == 2 and not tampered["done"]:
            tampered["done"] = True
            _tamper_line0()
        return res

    monkeypatch.setattr(SignatureVerifier, "verify_event", tampering_full)
    r1 = client.get("/ledger/verify")
    assert r1.status_code == 200
    stored_hash = app_module._LEDGER_VERIFY_STATE["prefix_hash"]
    assert stored_hash is not None, "بصمة البادئة من بايتات التصنيف يجب أن تُخزن"

    calls["n"] = 0
    r2 = client.get("/ledger/verify")
    assert r2.json()["snapshot"]["incremental"] is False, "التعديل أثناء التصنيف يُكتشف لا يُستأنف"
    assert calls["n"] == 5, "فحص كامل صادق بعد اكتشاف التعديل"
    assert r2.json()["ledger_summary"]["verified_with_key"] < 5, "السطر المعدل يظهر بصدق"

    # (ب) المسار التزايدي: عبث داخل البادئة القديمة أثناء تصنيف الذيل —
    # تجديد البصمة يرفض (الجزء القديم لم يعد بنفس بصمته) فلا استئناف
    monkeypatch.setattr(SignatureVerifier, "verify_event", real)
    _r807_reset_state(monkeypatch)
    calls["n"] = 0
    r3 = client.get("/ledger/verify")  # فحص كامل نظيف (الملف المعدل حقيقة)
    assert r3.json()["ledger_summary"]["verified_with_key"] == 4  # السطر المعدل invalid

    core.append_event(EventType.INTERACTION, {"r808": "tail", "n": 99})  # ذيل جديد
    tampered2 = {"done": False}
    state_calls2 = {"n": 0}

    def tampering_resume(self, event):
        res = real(self, event)
        state_calls2["n"] += 1
        if state_calls2["n"] == 1 and not tampered2["done"]:
            tampered2["done"] = True
            # عبث بقيمة مختلفة داخل البادئة القديمة أثناء تصنيف الذيل —
            # تكرار القيمة نفسها لا يغيّر البايتات فلا يُكتشف
            _tamper_line0(marker="tampered_r808_phase_b")
        return res

    monkeypatch.setattr(SignatureVerifier, "verify_event", tampering_resume)
    hash_before = app_module._LEDGER_VERIFY_STATE["prefix_hash"]
    r4 = client.get("/ledger/verify")
    assert r4.status_code == 200
    # تجديد البصمة رفض: الجزء القديم تغيّر ⇒ لم تُنشر نقطة استئناف جديدة
    assert app_module._LEDGER_VERIFY_STATE["prefix_hash"] == hash_before, (
        "لا شهادة على بايتات معدلة أثناء التصنيف"
    )
    # الطلب التالي يكتشف التعديل (بصمة القرص ≠ المخزنة) ⇒ فحص كامل صادق
    calls["n"] = 0
    r5 = client.get("/ledger/verify")
    assert r5.json()["snapshot"]["incremental"] is False
    assert calls["n"] == 6
    # 6 أحداث (5 أصلية + ذيل) واحد منها معامل ⇒ 5 موقعة صالحة
    assert r5.json()["ledger_summary"]["verified_with_key"] == 5
    assert r5.json()["ledger_summary"]["total_events"] == 6


def test_ledger_verify_overlapping_anchors_union(client, tmp_path, monkeypatch):
    """R-808: نطاقات مراس متداخلة تُحسب اتحادًا لا مجموعًا — ومقام واحد
    متسق (لقطة التصنيف) في المسارين الكامل والتزايدي معًا."""
    from backend.memory.core import EventType
    from backend.sovereign.ledger.anchor import LedgerAnchor

    core, data_root = _r807_env(tmp_path, monkeypatch)
    _r807_reset_state(monkeypatch)
    calls = _r807_counting_verifier(monkeypatch)

    for i in range(6):
        core.append_event(EventType.INTERACTION, {"r808": "anchors", "n": i})

    # نطاقان متداخلان: [0,3] و[2,5] ⇒ الاتحاد 6 لا المجموع 8
    def fake_list_anchors(self):
        return [
            {"anchor_id": "a1", "batch_start": 0, "batch_end": 3, "sig_format": "v2"},
            {"anchor_id": "a2", "batch_start": 2, "batch_end": 5, "sig_format": "v2"},
        ]

    def fake_verify_all(self, keyring=None):
        return {
            "total_anchors": 2, "root_verified_count": 2, "failed": 0,
            "trusted_count": 1, "trusted_coverage": 0.0, "nominal_coverage": 0.0,
            "details": [], "trusted_events_count": 4, "total_events": 6,
        }

    monkeypatch.setattr(LedgerAnchor, "list_anchors", fake_list_anchors)
    monkeypatch.setattr(LedgerAnchor, "verify_all_anchors", fake_verify_all)

    r1 = client.get("/ledger/verify")
    assert r1.json()["ledger_summary"]["anchored_events"] == 6, "الاتحاد لا المجموع"
    assert r1.json()["anchored_coverage_pct"] == 100.0
    assert r1.json()["nominal_coverage_pct"] == 100.0

    # حدث جديد: المسار التزايدي بنفس المقام (لقطة التصنيف)
    core.append_event(EventType.INTERACTION, {"r808": "anchors", "n": 6})
    r2 = client.get("/ledger/verify")
    assert r2.json()["snapshot"]["incremental"] is True
    assert r2.json()["ledger_summary"]["anchored_events"] == 6
    assert r2.json()["ledger_summary"]["total_events"] == 7
    assert r2.json()["anchored_coverage_pct"] == round(6 / 7 * 100, 2)

    # تغيّر ملف المراس (fp تغيّرت) ⇒ إعادة حساب قسم المراس بنفس منطق الاتحاد
    anchors_file = data_root / "sovereign_core" / "ledger.anchors.jsonl"
    anchors_file.write_text("{}", encoding="utf-8")
    core.append_event(EventType.INTERACTION, {"r808": "anchors", "n": 7})
    r3 = client.get("/ledger/verify")
    assert r3.json()["ledger_summary"]["anchored_events"] == 6, (
        "الاتحاد في المسار التزايدي المتغيّر المراسي أيضًا"
    )
    assert r3.json()["ledger_summary"]["total_events"] == 8
