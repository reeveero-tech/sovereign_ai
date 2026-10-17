"""
Invariant 2: لا أحداث بدون تصنيف في اليدجر (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل حدث في ledger.jsonl إما:
- موقّع بمفتاح في KeyRing (VERIFIED)
- داخل نطاق مرساة موثقة (ANCHORED)
- مُصنّف كـ UNVERIFIABLE_MISSING_KEY (LEGACY_PRE_KEYRING)

أي حدث لا ينتمي لأي من الثلاثة = فشل.
"""

import json
import sys
from pathlib import Path

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from backend.sovereign.ledger import LedgerAnchor
from backend.sovereign.keys import KeyRing, SignatureVerifier, VerificationStatus


# R-682 (Task 3.1): synthetic ledger fixture — replaces 45MB runtime data dependency.
# (استيراد مباشر — لا يعتمد على tests/__init__.py لأنه يكسر جمع backend/tests)
import importlib.util as _ilu
_synthetic_path = _REPO_ROOT / "tests" / "fixtures" / "synthetic_ledger.py"
_spec = _ilu.spec_from_file_location("synthetic_ledger", str(_synthetic_path))
_sl_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_sl_mod)
build_synthetic_ledger = _sl_mod.build_synthetic_ledger


@pytest.fixture
def synthetic_ledger(tmp_path):
    """Build a small signed ledger + anchors + keys in tmp_path.

    (تصويب المراجع — الاعتراض 8: يحترم SOVEREIGN_SYNTHETIC_LEDGER_DIR —
    دليل جاهز يُعاد استخدامه كما هو — يستخدمه إثبات RED لتشغيل الحارس
    على بيانات مُعبث بها عبر سب-بروسس فعلية.)
    """
    import os as _os
    env_dir = _os.environ.get("SOVEREIGN_SYNTHETIC_LEDGER_DIR")
    if env_dir:
        from pathlib import Path as _P
        return build_synthetic_ledger(_P(env_dir) / "data", reuse_existing=True)
    return build_synthetic_ledger(tmp_path / "data")


def test_no_unsigned_ledger_events(synthetic_ledger):
    """
    Invariant: كل حدث في اليدجر يجب أن يكون مصنّفًا (signed/anchored/unverifiable).
    لا حدث 'مجهول' بدون تصنيف.

    R-682 (Task 3.1): uses synthetic_ledger fixture instead of 45MB runtime data.
    """
    _real_ledger = synthetic_ledger["ledger"]
    _real_anchors = synthetic_ledger["anchors"]
    _keys_dir = synthetic_ledger["keys_dir"]

    # قراءة الأسطر مباشرة
    lines = []
    with open(_real_ledger, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                lines.append(line)

    assert lines, "fixture: empty ledger"

    # تحميل KeyRing (من الـ fixture dir — ليس من data/keys الحقيقي)
    keyring = KeyRing(keys_dir=_keys_dir)
    keyring.load_from_disk()
    verifier = SignatureVerifier(keyring)

    anchor = LedgerAnchor(ledger_path=_real_ledger, anchors_path=_real_anchors)

    # الأحداث المُغطاة بالمراسي
    anchors_list = anchor.list_anchors()
    anchored_events = set()
    for a in anchors_list:
        for i in range(a["batch_start"], a["batch_end"] + 1):
            anchored_events.add(i)

    # فحص كل حدث — بالبدائل الثلاث الحرفية من ROADMAP_V2:
    # (1) موقّع بمفتاح في KeyRing وتوقيعه يُتحقق فعلًا
    # (2) داخل نطاق مرساة (تغطية مستخدمة في القرار — لا تُحسب ثم تُهمل)
    # (3) مُعلَّم legacy_unverified: true صراحةً
    # أي حدث خارج الثلاثة = غير مصنف = فشل. INVALID (مزوّر) = فشل دائمًا.
    # (تصويب المراجع — الاعتراض 2: UNVERIFIABLE_MISSING_KEY وحده ليس بديلًا
    # مقبولًا — غياب المفتاح ليس تصنيفًا؛ الحدث غير الموقع يجب أن يكون
    # مرسى أو موسومًا legacy، وإلا رُفض.)
    # التغطية المقبولة تأتي من مراسٍ اجتازت التحقق فعلًا (تصويب المراجع —
    # الاعتراض 2): جذر صحيح + توقيع v2 متحقق. مرساة غير متحققة لا تمنح
    # تغطية — وإلا لَمُزوّر أمن أي حدث داخل نطاقها.
    _anchor_tool = LedgerAnchor(ledger_path=synthetic_ledger["ledger"],
                                anchors_path=synthetic_ledger["anchors"])
    anchored_events = set()
    for a in anchors_list:
        detailed = _anchor_tool.verify_anchor_detailed(a, keyring=keyring)
        if not detailed["root_verified"]:
            continue  # جذر غير متحقق — لا تغطية
        # (تصويب المراجع — الجولة 3): التغطية تُمنح فقط لمرساة متحققة
        # صراحةً — توقيع موثوق ناجح. مرساة v1 بلا توقيع (أو توقيع فاشل)
        # لا تمنح تغطية أبدًا: سجل نطاق وجذر لا يكفي.
        if detailed.get("signature_verified") is not True:
            continue
        for i in range(a["batch_start"], a["batch_end"] + 1):
            anchored_events.add(i)

    unclassified = []
    for i, line in enumerate(lines):
        try:
            event = json.loads(line)
        except Exception:
            # حدث غير قابل للقراءة (JSON تالف) — غير مصنّف
            unclassified.append((i, "invalid_json"))
            continue

        result = verifier.verify_event(event)
        status = result.status

        if status == VerificationStatus.VERIFIED:
            continue  # (1) موقّع ومتحقق — مصنّف
        if status == VerificationStatus.INVALID:
            # مزوّر — رفض دائمًا (ليس له بديل مقبول أبدًا)
            unclassified.append((i, "INVALID (tampered)"))
            continue
        # غير متحقق التوقيع (أي حالة أخرى، بما فيها UNVERIFIABLE_MISSING_KEY):
        # لا يُقبل إلا بديلاه: مرسى (2) أو موسوم legacy (3)
        if i in anchored_events:
            continue  # (2) داخل نطاق مرساة — مصنّف
        if event.get("legacy_unverified") is True:
            continue  # (3) موسوم صراحةً — مصنّف
        unclassified.append((i, f"unclassified(status={status})"))

    # لا حدث غير مصنف إطلاقًا (INVALID أو خارج البدائل الثلاثة)
    assert len(unclassified) == 0, (
        f"Found {len(unclassified)} unclassified events (must be signed, "
        f"anchored, or legacy_unverified:true): {unclassified[:5]}"
    )


def test_all_anchors_valid(synthetic_ledger):
    """كل المراسي المسجلة يجب أن تكون مُتحقّقة (المحتوى لم يتغير).

    R-682 (Task 3.1): uses synthetic_ledger fixture.
    """
    _real_ledger = synthetic_ledger["ledger"]
    _real_anchors = synthetic_ledger["anchors"]
    _keys_dir = synthetic_ledger["keys_dir"]

    anchor = LedgerAnchor(ledger_path=_real_ledger, anchors_path=_real_anchors)
    anchors = anchor.list_anchors()

    assert anchors, "fixture: no anchors to verify"

    # R-682: تحميل KeyRing من الـ fixture dir
    from backend.sovereign.keys.keyring import KeyRing as _KeyRing
    real_keyring = _KeyRing(keys_dir=_keys_dir)
    real_keyring.load_from_disk()
    if not real_keyring._keys:
        real_keyring = None

    for a in anchors:
        # التفاصيل — لتمييز v1 (لا توقيع) من v2 (مع توقيع)
        detailed = anchor.verify_anchor_detailed(a, keyring=real_keyring)
        # الجذر يجب أن ينجح (المحتوى لم يتغير)
        assert detailed["root_verified"] is True, (
            f"Anchor {a['anchor_id']} root failed: {detailed['message']}"
        )
        # v2: التوقيع يجب أن يُتحقق (إذا وُجد keyring)
        if a.get("sig_format") == "v2" and real_keyring is not None:
            assert detailed["signature_verified"] is True, (
                f"Anchor {a['anchor_id']} v2 signature failed: {detailed['message']}"
            )
        # v1: التوقيع لا يُوثّق (موثق في REPORT_V2.md — ليست موثوقة تشفيريًا)
        if a.get("sig_format") != "v2":
            # v1 — لا توقيع v2، لا نطلب توثيق التوقيع
            pass


def test_anchored_coverage(synthetic_ledger):
    """التغطية بالمراسي — كل الأحداث القديمة يجب أن تكون مُغطاة.

    R-682 (Task 3.1): uses synthetic_ledger fixture.
    """
    _real_ledger = synthetic_ledger["ledger"]
    _real_anchors = synthetic_ledger["anchors"]

    lines = []
    with open(_real_ledger, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                lines.append(line)

    assert lines, "fixture: empty ledger"

    anchor = LedgerAnchor(ledger_path=_real_ledger, anchors_path=_real_anchors)
    anchors = anchor.list_anchors()
    anchored_events = set()
    for a in anchors:
        for i in range(a["batch_start"], a["batch_end"] + 1):
            anchored_events.add(i)

    # التغطية يجب أن تكون عالية (> 90% للأحداث القديمة)
    coverage = len(anchored_events) / len(lines)
    assert coverage > 0.9, (
        f"Anchored coverage too low: {coverage:.2%} "
        f"({len(anchored_events)}/{len(lines)} events)"
    )


def test_anchor_detects_single_byte_tamper(synthetic_ledger):
    """إثبات RED سلوكي دائم (قاعدة الجولة الإنشائية 2026-10-16):

    تغيير بايت واحد في حدث مُرسى يجعل التحقق يفشل — الحارس يكشف العبث.
    (سجل تجريبي داخل مجلد مؤقت عبر واجهات التوقيع والإرساء الحقيقية —
    السجل التاريخي الحقيقي غائب عن الـclone وموثق غيابه في
    forensics/INVARIANT_LIMITS.md.)
    """
    _real_ledger = synthetic_ledger["ledger"]
    _real_anchors = synthetic_ledger["anchors"]

    anchor = LedgerAnchor(ledger_path=_real_ledger, anchors_path=_real_anchors)
    anchors_list = anchor.list_anchors()
    assert anchors_list, "fixture: no anchors"

    # الحالة السليمة: الجذر يُتحقق
    ok = anchor.verify_anchor_detailed(anchors_list[0])
    assert ok["root_verified"] is True, (
        f"fixture must verify cleanly before tampering: {ok['message']}"
    )

    # تغيير بايت واحد داخل نطاق المرساة (الحدث الأول — داخل النطاق حكمًا)
    lines = _real_ledger.read_text(encoding="utf-8").split("\n")
    non_empty = [i for i, l in enumerate(lines) if l.strip()]
    target_idx = non_empty[0]
    original = lines[target_idx]
    assert len(original) > 0
    # قلب بايت واحد (حرف واحد) في منتصف السطر — لا يتلف البنية، فقط المحتوى
    mid = len(original) // 2
    flipped = original[:mid] + ("X" if original[mid] != "X" else "Y") + original[mid + 1:]
    assert flipped != original, "tamper must actually change a byte"
    lines[target_idx] = flipped
    _real_ledger.write_text("\n".join(lines), encoding="utf-8")

    # بعد العبث: الجذر يفشل — الحارس يكشف تغيير البايت الواحد
    tampered = anchor.verify_anchor_detailed(anchors_list[0])
    assert tampered["root_verified"] is False, (
        "single-byte tamper inside anchored range MUST be detected "
        "(merkle root mismatch)"
    )


def test_invalid_signature_event_detected(synthetic_ledger):
    """إثبات RED سلوكي دائم: حدث بتوقيع مزوّر (تغيير محتوى مع إبقاء التوقيع)
    يُصنَّف INVALID — لا يُقبل أبدًا كموثق.

    الحارس (test_no_unsigned_ledger_events) يفشل عند وجود أي حدث INVALID —
    هذا الاختبار يثبت أن آلية الكشف نفسها تعمل.
    """
    _real_ledger = synthetic_ledger["ledger"]
    _keys_dir = synthetic_ledger["keys_dir"]

    keyring = KeyRing(keys_dir=_keys_dir)
    keyring.load_from_disk()
    verifier = SignatureVerifier(keyring)

    # أول حدث موقّع صالح
    lines = [l for l in _real_ledger.read_text(encoding="utf-8").split("\n") if l.strip()]
    event = json.loads(lines[0])

    # الحالة السليمة: يُصنَّف (VERIFIED أو UNVERIFIABLE_MISSING_KEY — كلاهما معروف)
    result_ok = verifier.verify_event(event)
    assert result_ok.status in (
        VerificationStatus.VERIFIED,
        VerificationStatus.UNVERIFIABLE_MISSING_KEY,
    ), f"fixture event must be classifiable, got {result_ok.status}"

    # التزوير: تغيير المحتوى الموقّع (blob) مع إبقاء التوقيع القديم
    # (التوقيع يغطي hash|prev_hash|blob|time|type|key_id — راجع verifier.py)
    event["blob"] = event["blob"] + "TAMPERED"
    result_bad = verifier.verify_event(event)
    assert result_bad.status == VerificationStatus.INVALID, (
        f"content-modified event with stale signature must be INVALID, "
        f"got {result_bad.status}"
    )


def test_unclassified_event_rejected(tmp_path):
    """RED سلوكي عبر الحارس الحقيقي نفسه (تصويب المراجع — الاعتراض 2):
    حدث غير موقع وغير مرسى وبلا علامة legacy يُلحق بالسجل التجريبي في
    دليل معزول، ثم يُشغَّل الحارس الفعلي (test_no_unsigned_ledger_events)
    عبر سب-بروسس: يجب أن يفشل بسبب الحدث غير المصنف لا بسبب خطأ جمع؛
    وبعد إزالة الحدث يعود الحارس للنجاح — في كل تشغيل."""
    import os as _os
    import subprocess as _sp

    data_dir = tmp_path / "probe_root"
    built = build_synthetic_ledger(data_dir / "data")
    ledger_file = built["ledger"]
    anchors_file = built["anchors"]

    original_lines = [
        l for l in ledger_file.read_text(encoding="utf-8").split("\n") if l.strip()
    ]
    # مرساة التجربة تغطي كل الأحداث الأصلية — الحدث الدخيل خارج التغطية
    rogue = json.dumps({
        "id": "evt-rogue",
        "type": "attention::snapshot",
        "time": 1792029999,
        "hash": "0" * 64,
        "prev_hash": "0" * 64,
        "blob": "rogue unsigned unanchored event",
    })
    assert rogue not in original_lines

    env = dict(_os.environ)
    env["SOVEREIGN_SYNTHETIC_LEDGER_DIR"] = str(data_dir)
    cmd = [
        sys.executable, "-m", "pytest",
        "backend/tests/invariants/test_no_unsigned_ledger_events.py"
        "::test_no_unsigned_ledger_events",
        "-q", "--no-header",
    ]

    def _run_guard():
        return _sp.run(cmd, capture_output=True, text=True,
                       cwd=str(_REPO_ROOT), env=env, timeout=600)

    # الحارس سليم قبل الإلحاق
    r_clean = _run_guard()
    assert r_clean.returncode == 0, (
        f"guard must pass on clean synthetic ledger: {r_clean.stdout[-300:]}"
    )

    # إلحاق الحدث الدخيل (غير موقع، خارج المراسي، بلا علامة legacy)
    ledger_file.write_text(
        "\n".join(original_lines + [rogue]) + "\n", encoding="utf-8"
    )
    r_rogue = _run_guard()
    assert r_rogue.returncode != 0, (
        "guard MUST FAIL when an unsigned+unanchored+unflagged event exists"
    )
    assert "unclassified" in r_rogue.stdout, (
        "guard failure must be caused by the unclassified event, not a "
        f"collection/import error: {r_rogue.stdout[-400:]}"
    )

    # إزالة الحدث الدخيل تعيد النجاح
    ledger_file.write_text("\n".join(original_lines) + "\n", encoding="utf-8")
    r_restored = _run_guard()
    assert r_restored.returncode == 0, (
        f"guard must pass again after rogue removal: {r_restored.stdout[-300:]}"
    )


def test_single_byte_tamper_run_log(tmp_path):
    """إثبات RED بسجل تشغيل فعلي (تصويب المراجع — الاعتراض 8):

    - يُبنى سجل تجريبي سليم، ثم يُقلب بايت ASCII واحد معلوم داخل حدث
      مُرسى (الفرق المُثبت = بايت واحد بالضبط، والسطر يبقى JSON صالحًا).
    - يُشغَّل الحارس نفسه (test_all_anchors_valid) عبر سب-بروسس على الدليل
      المعبوث: يفشل بسبب عدم تطابق جذر ميركل (لا خطأ جمع) — الخرج ورمز
      الخروج مُلتقطان.
    - يُستعاد البايت، ويُعاد تشغيل الحارس: ينجح.
    الدورة كاملة تُعاد في كل تشغيل — لا تعتمد على تشغيل تاريخي، والأثر
    الموثق أيضًا في forensics/TAMPER_RED_RUN_LOG.md.
    """
    import os as _os
    import subprocess as _sp

    data_dir = tmp_path / "probe_root"
    built = build_synthetic_ledger(data_dir / "data")
    ledger_file = built["ledger"]

    original_bytes = ledger_file.read_bytes()

    env = dict(_os.environ)
    env["SOVEREIGN_SYNTHETIC_LEDGER_DIR"] = str(data_dir)
    cmd = [
        sys.executable, "-m", "pytest",
        "backend/tests/invariants/test_no_unsigned_ledger_events.py"
        "::test_all_anchors_valid",
        "-q", "--no-header",
    ]
    r_clean = _sp.run(
        cmd, capture_output=True, text=True, cwd=str(_REPO_ROOT),
        env=env, timeout=600,
    )
    assert r_clean.returncode == 0, (
        f"guard must pass on clean synthetic ledger: {r_clean.stdout[-300:]}"
    )

    # قلب بايت ASCII واحد داخل السطر الأول (داخل نطاق المرساة) —
    # استبدال رقم برقم آخر: الفرق بايت واحد والسطر يبقى JSON صالحًا
    text = original_bytes.decode("utf-8")
    lines = text.split("\n")
    target_idx = next(i for i, l in enumerate(lines) if l.strip())
    line = lines[target_idx]
    digit_pos = next(i for i, ch in enumerate(line) if ch.isdigit())
    old_ch = line[digit_pos]
    new_ch = "9" if old_ch != "9" else "8"
    assert new_ch != old_ch
    tampered_line = line[:digit_pos] + new_ch + line[digit_pos + 1:]
    lines[target_idx] = tampered_line
    tampered_bytes = "\n".join(lines).encode("utf-8")
    diff_count = sum(
        1 for a, b in zip(original_bytes, tampered_bytes) if a != b
    ) + abs(len(original_bytes) - len(tampered_bytes))
    assert diff_count == 1, (
        f"tamper must be EXACTLY one byte, diff={diff_count}"
    )
    import json as _json_probe
    _json_probe.loads(tampered_line)

    ledger_file.write_bytes(tampered_bytes)

    r_tampered = _sp.run(
        cmd, capture_output=True, text=True, cwd=str(_REPO_ROOT),
        env=env, timeout=600,
    )
    assert r_tampered.returncode != 0, (
        "guard MUST FAIL on single-byte tampered anchored ledger — "
        f"run log: {r_tampered.stdout[-400:]}"
    )
    assert "root failed" in r_tampered.stdout or "root mismatch" in r_tampered.stdout, (
        "guard failure must be caused by the tamper (root mismatch), "
        f"not a collection/import error: {r_tampered.stdout[-400:]}"
    )

    # الاستعادة تعيد النجاح
    ledger_file.write_bytes(original_bytes)
    r_restored = _sp.run(
        cmd, capture_output=True, text=True, cwd=str(_REPO_ROOT),
        env=env, timeout=600,
    )
    assert r_restored.returncode == 0, (
        f"guard must pass again after byte restoration: {r_restored.stdout[-300:]}"
    )


def test_unsigned_event_not_covered_by_unverified_anchor(tmp_path):
    """RED معزول مميّز (تصويب المراجع — الجولة 4): الحدث غير الموقع غير
    الموسوم داخل نطاق مرساة، بجذر صحيح محسوب للمحتوى الجديد:

    - مرساة بنفس الجذر والنطاق لكن بلا توقيع موثوق (v1) → لا تغطية →
      الحارس الحقيقي يفشل بسبب unclassified.
    - مرساة موثوقة (v2 موقعة على الجذر الجديد) → التغطية تُمنح → الحارس
      ينجح.

    الشرط المميّز: root_verified == True في الحالتين، والفرق الوحيد هو
    التوقيع الموثوق — الرفض سببه غياب التوقيع لا كسر الجذر. بيانات
    تجريبية فقط، عبر الحارس الحقيقي في سب-بروسس."""
    import hashlib
    import hmac as _hmac
    import json as _json
    import os as _os
    import subprocess as _sp

    from backend.sovereign.ledger.anchor import compute_merkle_root

    data_dir = tmp_path / "probe_root"
    built = build_synthetic_ledger(data_dir / "data")
    ledger_file = built["ledger"]
    anchors_file = built["anchors"]
    private_key = built["private_key"]
    key_id = built["key_id"]

    original_ledger = ledger_file.read_text(encoding="utf-8")
    original_anchors = anchors_file.read_text(encoding="utf-8")
    original_lines = [l for l in original_ledger.split("\n") if l.strip()]
    base_anchor = _json.loads(original_anchors.strip().split("\n")[0])

    # (1) حدث غير موقع وغير موسوم (وليس INVALID: لا key_id معروف ولا توقيع)
    # داخل نطاق المرساة — يستبدل حدثًا موقعًا
    in_range_idx = base_anchor["batch_start"] + 1
    assert base_anchor["batch_start"] <= in_range_idx <= base_anchor["batch_end"]
    rogue = {
        "id": "evt-rogue-in-range",
        "type": "attention::snapshot",
        "time": "2026-10-16T00:00:00Z",
        "prev_hash": "0" * 64,
        "hash": "1" * 64,
        "blob": "rogue unsigned unflagged event inside anchor range",
    }
    assert "key_id" not in rogue and "signature" not in rogue
    assert rogue.get("legacy_unverified") is not True
    new_lines = list(original_lines)
    new_lines[in_range_idx] = _json.dumps(rogue, ensure_ascii=False)

    # (2) الجذر الصحيح للمحتوى الجديد — محسوب بأدوات المشروع نفسها
    new_root = compute_merkle_root(new_lines)

    env = dict(_os.environ)
    env["SOVEREIGN_SYNTHETIC_LEDGER_DIR"] = str(data_dir)
    cmd = [
        sys.executable, "-m", "pytest",
        "backend/tests/invariants/test_no_unsigned_ledger_events.py"
        "::test_no_unsigned_ledger_events",
        "-q", "--no-header",
    ]

    def _run_guard():
        return _sp.run(cmd, capture_output=True, text=True,
                       cwd=str(_REPO_ROOT), env=env, timeout=600)

    # (3) الحالة أ: مرساة غير موثوقة (v1) — نفس الجذر والنطاق، بلا توقيع
    ledger_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    v1_anchor = {
        "anchor_id": base_anchor["anchor_id"],
        "batch_start": base_anchor["batch_start"],
        "batch_end": base_anchor["batch_end"],
        "event_count": base_anchor["event_count"],
        "merkle_root": new_root,          # الجذر صحيح للمحتوى الجديد
        "reason": base_anchor["reason"],
        "anchored_at": base_anchor["anchored_at"],
        # بلا sig_format/signature/key_id — v1 بلا توقيع موثوق
    }
    anchors_file.write_text(_json.dumps(v1_anchor) + "\n", encoding="utf-8")

    r_v1 = _run_guard()
    assert r_v1.returncode != 0, (
        "guard MUST FAIL when an unsigned+unflagged in-range event is covered "
        "only by an unverified (v1) anchor — root is correct, so the failure "
        "must come from the missing trusted signature"
    )
    assert "unclassified" in r_v1.stdout, (
        f"failure must be caused by unclassified event: {r_v1.stdout[-400:]}"
    )

    # (4) الحالة ب: مرساة موثوقة (v2 موقعة على الجذر الجديد) — نفس المحتوى
    # ونفس الجذر ونطاق المرساة نفسه: التغطية تُمنح والحارس ينجح
    sig_data_v2 = (
        f"anchor_sig_v2|{v1_anchor['batch_start']}|{v1_anchor['batch_end']}"
        f"|{v1_anchor['event_count']}|{new_root}|{key_id}"
    )
    v2_anchor = dict(v1_anchor)
    v2_anchor.update({
        "key_id": key_id,
        "sig_format": "v2",
        "sig_data_v2": sig_data_v2,
        "signature": _hmac.new(
            private_key.encode("utf-8"),
            sig_data_v2.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    })
    anchors_file.write_text(_json.dumps(v2_anchor) + "\n", encoding="utf-8")

    r_v2 = _run_guard()
    assert r_v2.returncode == 0, (
        f"trusted (v2-signed) anchor over the same root must grant coverage "
        f"and the guard must pass: {r_v2.stdout[-400:]}"
    )

    # (5) الاستعادة
    ledger_file.write_text(original_ledger, encoding="utf-8")
    anchors_file.write_text(original_anchors, encoding="utf-8")
    r_ok = _run_guard()
    assert r_ok.returncode == 0, (
        f"guard must pass on the restored fixture: {r_ok.stdout[-300:]}"
    )


def test_merkle_root_boundary_distinctness():
    """الجولة <2> — مسبار تصادم البادئة (ادعاء مطلوب فحصه عدائيًا):

    هل compute_merkle_root يمنع تصادم البادئة/تقسيم الأسطر؟ البنية:
    (1) كل سطر ورقة مستقلة (hash_leaf = sha256 للسطر كاملًا) — حدود
        الأسطر مثبتة ببنية القائمة، لا بتقسيم داخل السطر.
    (2) العقد الداخلية تدمج سلسلتي هَكس ثابتتي الطول (64 حرفًا لكل
        منهما) — الدمج غير قابل للالتباس بطول ثابت.
    (3) توقيع المراسي HMAC — غير معرض لهجوم length extension.

    الإثبات السلوكي: أي إعادة تقسيم لنفس المحتوى عبر حدود أسطر مختلفة
    تعطي جذورًا مختلفة — لا يوجد تصادم بادئة بين قوائم مختلفة التقسيم.
    وكل تغيير بايت في سطر يغير الجذر (مغطى بمسبارات العبث الأحادية)."""
    from backend.sovereign.ledger.anchor import compute_merkle_root, hash_leaf

    # نفس المحتوى المتراكم بتقسيمات أسطر مختلفة — جذور مختلفة بالضرورة
    a = compute_merkle_root(["ab", "c"])
    b = compute_merkle_root(["a", "bc"])
    c = compute_merkle_root(["abc"])
    d = compute_merkle_root(["a", "b", "c"])
    roots = [a, b, c, d]
    assert len(set(roots)) == len(roots), (
        f"different line splits must never collide: {roots}"
    )

    # بادئة مشتركة بين قائمتين — الجذر يتغير حالًا (لا وراثة بادئة)
    base = ["x1", "x2", "x3"]
    extended = base + ["x4"]
    assert compute_merkle_root(base) != compute_merkle_root(extended), (
        "extending a list must change the root (no prefix-collision)"
    )

    # إعادة ترتيب نفس الأسطر — جذر مختلف (ترتيب الأسطر ملزم)
    assert compute_merkle_root(base) != compute_merkle_root(list(reversed(base))), (
        "reordering lines must change the root"
    )

    # ورقة مكررة (عدد فردي يكرر الأخير) — حقيقة رياضية موثقة لا اخفاء:
    # root([1,2,3]) == root([1,2,3,3]) بالتصميم (قاعدة تكرار الأخير).
    # التطابق الجذري غير قابل للاستغلال لأن توقيع v2 يغطي event_count
    # والنطاق — بيانات التوقيع تختلف، فلا يمكن إعادة تشغيل مرساة عدد ٣
    # على قائمة عدد ٤. الإثبات أدناه بدالة الإنتاج الفعلية (لا نص يدوي):
    # compute_anchor_signature_data يفرّق بين العددين والنطاقين.
    odd = compute_merkle_root(["1", "2", "3"])
    even = compute_merkle_root(["1", "2", "3", "3"])
    assert odd == even, (
        "odd-duplication property: root([1,2,3]) must equal "
        "root([1,2,3,3]) by the duplicate-last rule — if this changes, "
        "the algorithm changed and this test must be revisited"
    )
    anchor_mgr = LedgerAnchor(ledger_path=Path("/nonexistent-ledger-for-sig-data"))
    sig_data_3 = anchor_mgr.compute_anchor_signature_data(
        0, 2, 3, odd, "probe-key"
    )
    sig_data_4 = anchor_mgr.compute_anchor_signature_data(
        0, 3, 4, even, "probe-key"
    )
    assert sig_data_3 != sig_data_4, (
        f"production signature data must distinguish the two colliding "
        f"roots (event_count and range are covered): "
        f"{sig_data_3!r} vs {sig_data_4!r}"
    )
    assert sig_data_3.split("|")[3] == "3" and sig_data_4.split("|")[3] == "4", (
        "production signature data must embed event_count exactly (v2 format)"
    )
    assert compute_merkle_root(["1", "2", "3"]) != compute_merkle_root(["1", "2", "4"]), (
        "content change must change the root"
    )

    # فصل نطاق الأوراق عن العقد (اعتراض المراجع أمين) — الحقيقة موثقة بصدق:
    # جذر الورقة المفردة بلا فصل نطاق في الخوارزمية الحالية —
    # root([x, y]) == root([h(x)+h(y)]) رياضيًا (الورقة المفردة تُتجزأ
    # sha256(سطر) — وسطر يمكن أن يكون هو نص العقدة نفسه). هذا التباس
    # بنيوي معروف (غياب domain separation) — تغيير الخوارزمية يُبطل جذور
    # المراسي التاريخية الملتزمة، لذا يوثّق ولا يُغيّر بصمت (قرار نسخة
    # مستقبلية للمراسي = للمالك). الإثبات أدناه أن الاستغلال محجوب عبر
    # مسار التحقق الفعلي: مرساة عدد ٢ يُرفض ضد يدجر سطر واحد (فحص الطول
    # يسبق كل شيء) — فلا يمكن إعادة تفسير الجذر بعدد أصغر.
    x, y = "a", "b"
    node_text = hash_leaf(x) + hash_leaf(y)
    assert compute_merkle_root([x, y]) == compute_merkle_root([node_text]), (
        "documented structural ambiguity (no leaf/node domain separation): "
        "root([x,y]) equals root([node_text]) — if this changes, the "
        "algorithm changed and committed anchor roots are affected"
    )
    # الإثبات السلوكي لعدم القابلية للاستغلال: مسار التحقق الفعلي يرفض
    # مرساة عدد ٢ (نطاق [0,1]) ضد يدجر سطر واحد — فحص الطول أولًا
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "ledger.jsonl"
        ledger.write_text(node_text + "\n", encoding="utf-8")
        mgr = LedgerAnchor(ledger_path=ledger)
        anchor2 = {
            "batch_start": 0, "batch_end": 1,
            "merkle_root": f"sha256:{compute_merkle_root([x, y])}",
            "sig_format": "v2", "key_id": "any", "signature": "x",
            "event_count": 2,
        }
        res = mgr.verify_anchor_detailed(anchor2)
        assert not res["root_verified"], (
            f"verification must reject a 2-event anchor against a 1-line "
            f"ledger (length check) — the ambiguity must not be exploitable: "
            f"{res['message']}"
        )


def test_anchor_signature_blocks_count_reinterpretation(tmp_path):
    """مسبار تكاملي (الجولة <2> — اعتراض المراجع بصير): الالتباس البنيوي
    لجذر الورقة المفردة (root([e1,e2,e3]) == root([e1,e2,e3,e3])) يجب ألا
    يكون قابلًا للاستغلال عبر مسار التحقق الفعلي.

    الهجوم المُحاكى: مرساة صحيحة موقّعة لثلاثة أحداث تُقبل أولًا (الأساس)،
    ثم يُلحق مكرر الحدث الأخير لليدجر وتُعدّل نسخة المرساة إلى عدد ٤
    (batch_end=3) مع إبقاء التوقيع القديم. الجذر المتصادم يُطابق (لا
    اكتشاف بالجذر) — لكن التوقيع v2 يغطي event_count والنطاق فيجب أن
    يُرفض: signature_verified=False وtrusted=False وverify_anchor رفضًا.
    هذا يختبر الحماية المدعاة بدل رفض مدخل ناقص أصلًا."""
    import sys
    _repo = Path(__file__).resolve().parent.parent.parent.parent
    for p in [str(_repo), str(_repo / "backend")]:
        if p not in sys.path:
            sys.path.insert(0, p)
    import importlib.util as _ilu
    _synthetic_path = _repo / "tests" / "fixtures" / "synthetic_ledger.py"
    _spec = _ilu.spec_from_file_location("synthetic_ledger", str(_synthetic_path))
    _sl_mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_sl_mod)

    built = _sl_mod.build_synthetic_ledger(tmp_path / "data", event_count=3)
    ledger_path = Path(built["ledger"])
    anchors_path = Path(built["anchors"])
    keyring = built["keyring"]
    private_key = built["private_key"]
    key_id = built["key_id"]
    assert keyring is not None and private_key, "synthetic fixture must provide keyring"

    manager = LedgerAnchor(ledger_path=ledger_path, anchors_path=anchors_path)
    lines = manager.read_ledger_lines()
    assert len(lines) == 3, f"expected 3 synthetic events, got {len(lines)}"

    from backend.sovereign.ledger.anchor import compute_merkle_root
    import hmac as _hmac
    import hashlib as _hashlib

    merkle_root = compute_merkle_root(lines)
    sig_data = manager.compute_anchor_signature_data(
        0, 2, 3, merkle_root, key_id
    )
    signature = _hmac.new(
        private_key.encode("utf-8"), sig_data.encode("utf-8"),
        _hashlib.sha256,
    ).hexdigest()

    valid_anchor = {
        "anchor_id": "probe_count_3",
        "batch_start": 0, "batch_end": 2, "event_count": 3,
        "merkle_root": f"sha256:{merkle_root}",
        "reason": "PROBE_ROUND2", "key_id": key_id, "signature": signature,
        "anchored_at": "2026-10-17T00:00:00Z", "notes": "probe",
        "sig_format": "v2",
    }

    # الأساس: المرساة الصحيحة تُقبل كاملةً (root + signature + trusted)
    base = manager.verify_anchor_detailed(valid_anchor, keyring=keyring)
    assert base["root_verified"] and base["signature_verified"] and base["trusted"], (
        f"valid signed 3-event anchor must be fully accepted: {base}"
    )

    # الهجوم: إلحاق مكرر الحدث الأخير — الجذر المتصادم يُطابق
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(lines[-1] + "\n")
    lines4 = manager.read_ledger_lines()
    assert len(lines4) == 4
    colliding_root = compute_merkle_root(lines4[0:4])
    assert colliding_root == merkle_root, (
        "the odd-duplication collision must hold for this probe to be valid"
    )

    # نسخة المرساة المعدّلة: عدد ٤ ونطاق [0,3] بالتوقيع القديم
    forged = dict(valid_anchor)
    forged["batch_end"] = 3
    forged["event_count"] = 4
    res = manager.verify_anchor_detailed(forged, keyring=keyring)
    assert res["root_verified"], (
        f"the colliding root must MATCH (that is the documented ambiguity): "
        f"{res['message']}"
    )
    assert not res["signature_verified"], (
        f"signature must be REJECTED for the reinterpreted count: {res}"
    )
    assert not res["trusted"], "forged anchor must not be trusted"
    ok, msg = manager.verify_anchor(forged, keyring=keyring)
    assert not ok, f"verify_anchor must reject: {msg}"


def test_real_anchors_full_coverage():
    """الجولة <2> — فحص على البيانات الحقيقية المتتبعة (لا الاصطناعية):

    ledger.anchors.jsonl المتتبع يحمل مراسي الإنتاج الحقيقية. المتاح في
    النسخة هو هذا الملف فقط — أسطر اليدجر (116,910 أحداثًا) بيانات تشغيلية
    غير متتبعة، ومفتاح المراسي الخاص غير متتبع (keyring.json بيانات تشغيل).
    لذا الفحص الممكن على الحقيقة: البنية والتغطية — كل نطاق [0, 116909]
    مغطى بمراسٍ متجاورة بلا فجوات ولا تداخل، وevent_count يطابق النطاق،
    وتوجد مرساة تغطية كاملة بصيغة v2 موقعة. التحقق من المحتوى (الجذر ضد
    الأسطر) والتوقيع (ضد المفتاح الخاص) متعذر في النسخة — موثق كبند مالك
    (OWNER_REQUIRED R2-1)."""
    anchors_path = _REPO_ROOT / "data" / "sovereign_core" / "ledger.anchors.jsonl"
    assert anchors_path.exists(), (
        "tracked real anchors file data/sovereign_core/ledger.anchors.jsonl "
        "must exist in the clone"
    )
    records = []
    with open(anchors_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    assert records, "real anchors file must not be empty"

    # مراسات التغطية الجزئية (التجميعية الكاملة تُفحص منفصلة أدناه)
    total_end = 0
    for r in records:
        start, end = r["batch_start"], r["batch_end"]
        count = r["event_count"]
        # event_count يطابق النطاق حرفيًا (بنية سليمة)
        assert count == end - start + 1, (
            f"anchor {r.get('anchor_id')} event_count {count} != range "
            f"[{start},{end}] size {end - start + 1}"
        )
    # التغطية الكاملة v2 موجودة وتطابق النطاق الكامل
    full = [r for r in records if r.get("sig_format") == "v2"
            and r["batch_start"] == 0]
    assert any(r["batch_end"] == 116909 and r["event_count"] == 116910
               for r in full), (
        "a v2 full-coverage anchor [0,116909] (116,910 events) must exist"
    )
    # النطاقات الجزئية تغطي [0, 116909] بلا فجوات (مرتبة، متجاورة) —
    # نطاقات متكررة (نفس النطاق بسببين: R640 ثم R641 بتوقيع v2) مشروعة:
    # الإصدار الأحدث v2 يعلو، والتكرار لا يترك فجوة
    partial = sorted(
        [r for r in records if not (r["batch_start"] == 0
                                    and r["batch_end"] == 116909)],
        key=lambda r: (r["batch_start"], r["batch_end"]),
    )
    covered = 0
    for r in partial:
        if r["batch_start"] < covered:
            # تكرار نطاق سابق — مشروع فقط بصيغة أحدث (v2 فوق v1)
            assert r.get("sig_format") == "v2", (
                f"repeated range [{r['batch_start']},{r['batch_end']}] must be "
                "a v2 re-anchor, not a stale duplicate"
            )
            continue
        assert r["batch_start"] == covered, (
            f"coverage gap at [{r['batch_start']},{r['batch_end']}] — "
            f"expected start {covered}"
        )
        covered = r["batch_end"] + 1
    assert covered == 116910, (
        f"partial anchors must tile [0,116909] exactly — covered up to "
        f"{covered - 1}"
    )


def test_merkle_v1_v2_differ():
    """الجولة <2> — قرار المالك R2-4 (D-036): v2 بفصل النطاق.

    compute_merkle_root_v2 يجب أن يخالف v1 في كل الحالات — وبخاصة الحالة
    الخطرة (length extension / إعادة التفسير): جذر v1 لقائمة لا يجوز أن
    يساوي جذر v2 لنفس القائمة، وجذر v1 لقائمة لا يجوز أن يُعاد إنتاجه
    بجذر v2 لقائمة أخرى. RED قبل التنفيذ: الدالة غير موجودة أصلًا."""
    from backend.sovereign.ledger.anchor import (
        compute_merkle_root, compute_merkle_root_v2,
    )

    for lines in (["a", "b"], ["1", "2", "3"], ["x"], ["ab", "c", "d", "e"]):
        v1 = compute_merkle_root(lines)
        v2 = compute_merkle_root_v2(lines)
        assert v1 != v2, (
            f"v2 must differ from v1 (domain separation) for {lines}"
        )
    # الحالة الخطرة تحديدًا: جذر v1 لزوج يساوي جذر v1 لسطر نصه نص العقدة —
    # جذر v2 للزوج يجب ألا يساوي جذر v1 لأي من القائمتين (لا وراثة التباس)
    x, y = "a", "b"
    node_text = compute_merkle_root([x, y])  # نص عقدة v1 كسطر
    v2_pair = compute_merkle_root_v2([x, y])
    assert v2_pair != compute_merkle_root([node_text]), (
        "v2 root must not be reproducible by any v1 root (no ambiguity "
        "inheritance)"
    )
    assert v2_pair != compute_merkle_root_v2([node_text]), (
        "v2 must not reproduce the v1 ambiguity: a single line whose content "
        "is a node digest string must not collide with the two-leaf root "
        "(domain separation 0x00/0x01)"
    )


def test_merkle_v2_domain_separation():
    """الجولة <2> — قرار المالك R2-4 (D-036): فصل نطاق الورقة عن العقدة.

    في v2: الورقة sha256(0x00||data) والعقدة sha256(0x01||left||right) —
    البادئات تمنع خلط النطاقين بنيويًا. الإثبات: جذر ورقة مفردة لا يساوي
    جذر أي عقدة، وسطر قيمته نص عقدة لا يُنتج جذر العقدة (عكس التباس v1
    الموثق)."""
    from backend.sovereign.ledger.anchor import (
        compute_merkle_root, compute_merkle_root_v2,
    )

    x, y = "a", "b"
    two_leaf = compute_merkle_root_v2([x, y])
    # جذر القائمة المفردة ذات نص عقدة v1 — لا تصادم مع جذر الزوج
    node_text = compute_merkle_root([x, y])
    assert two_leaf != compute_merkle_root_v2([node_text]), (
        "v2 domain separation: single-leaf roots and node structures must "
        "never collide (0x00 leaf vs 0x01 node prefixes)"
    )
    # كل التقسيمات المختلفة لنفس المحتوى جذور مختلفة في v2
    roots = [
        compute_merkle_root_v2(p)
        for p in (["ab", "c"], ["a", "bc"], ["abc"], ["a", "b", "c"])
    ]
    assert len(set(roots)) == len(roots), (
        f"v2 different splits must never collide: {roots}"
    )
