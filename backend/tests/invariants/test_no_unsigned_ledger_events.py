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
