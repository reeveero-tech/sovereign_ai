"""
R-682 (تنفيذ حقيقي): اختبارات سلوكية لكل المواقع منخفضة الخطورة (return None)
+ خوارزمية فك تشفير بذرة الفينيق (RED → GREEN).

المنهجية: اختبار RED أولًا، ثم التنفيذ، ثم GREEN.

المواقع المغطاة (14 موقعًا منخفضة الخطورة — راجع forensics/RETURN_NONE_AUDIT_R682.md):
- backend/compat/nexus_lifecycle.py:85,112 (ensure_nexus_running_async)
- backend/compat/nexus_recommendations.py:43 (get_recommendation_engine)
- backend/memory/biological/evolution.py:411 (mutate_concept)
- backend/memory/core.py:720 (_get_current_signing_key_id)
- backend/memory/encoding.py:455 (decrypt)
- backend/orchestrator.py:288,301,314,431,450 (تحميل المكونات)
- nexus/data_pipeline/processor.py:55 (DataProcessor.process)
- nexus/performance/code_analyzer.py:51 (analyze_file)
- nexus/storage/long_term_store.py:51 (load)
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)


# ============================================================
# Part 1: خوارزمية فك تشفير البذرة (RED → GREEN)
# ============================================================

class TestPhoenixSeedDecryption:
    """فك تشفير بذرة الفينيق — خوارزمية حقيقية (كانت stub ترجع None)."""

    def _make_defense(self):
        from backend.memory.defense.ransomware import RansomwareDefense
        obj = RansomwareDefense.__new__(RansomwareDefense)
        obj.core = type("MockCore", (), {"append_event": lambda *a, **k: None})()
        obj.seeds = {}
        return obj

    def _make_seed(self, seed_id="phoenix_seed_test_001"):
        from backend.memory.defense.ransomware import PhoenixSeed
        return PhoenixSeed(
            id=seed_id,
            created_at=1000000.0,
            core_fingerprint="deadbeef1234",
            essential_memory={
                "core": {"last_hash": "a" * 64, "integrity_count": 5},
                "identity": {"sovereign_key_fingerprint": "b" * 16},
            },
            resurrection_key="cafe" * 16,
            expires_at=1000000.0 + 604800,
            phase="living",
        )

    def test_decrypt_seed_roundtrip(self):
        """RED: فك تشفير بذرة بمفتاحها الصحيح يجب أن يعيد البذرة الأصلية."""
        obj = self._make_defense()
        seed = self._make_seed()
        encrypted = obj._encrypt_seed(seed)
        result = obj._decrypt_seed(encrypted, resurrection_key=seed.resurrection_key)
        assert result is not None, "فك التشفير بمفتاح البذرة الصحيح يجب أن ينجح"
        assert result.id == seed.id
        assert result.essential_memory == seed.essential_memory
        assert result.resurrection_key == seed.resurrection_key
        assert result.core_fingerprint == seed.core_fingerprint

    def test_decrypt_seed_uses_in_memory_keys(self):
        """RED: بدون مفتاح صريح — تُجرَّب مفاتيح البذور المعروفة في الذاكرة."""
        obj = self._make_defense()
        seed = self._make_seed("phoenix_seed_mem_002")
        obj.seeds[seed.id] = seed
        encrypted = obj._encrypt_seed(seed)
        result = obj._decrypt_seed(encrypted)
        assert result is not None
        assert result.id == seed.id

    def test_decrypt_seed_wrong_key_fails_logged(self, caplog):
        """RED: مفتاح خاطئ → None + تسجيل خطأ (لا صمت)."""
        obj = self._make_defense()
        seed = self._make_seed()
        encrypted = obj._encrypt_seed(seed)
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed(encrypted, resurrection_key="wrong" * 8)
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records), \
            "الفشل بمفتاح خاطئ يجب أن يُسجَّل (لا صمت)"

    def test_decrypt_seed_tampered_payload_rejected(self, caplog):
        """RED: بذرة مُلاعب بها (بايت مقلوب في النص المشفر) → None + تسجيل."""
        obj = self._make_defense()
        seed = self._make_seed()
        encrypted = bytearray(obj._encrypt_seed(seed))
        encrypted[10] ^= 0xFF  # تلاعب بالبيانات المشفرة
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed(bytes(encrypted), resurrection_key=seed.resurrection_key)
        assert result is None, "البذرة المُلاعب بها يجب أن تُرفض"
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_decrypt_seed_truncated_payload_rejected(self, caplog):
        """RED: نص مشفر مقطوع → None + تسجيل."""
        obj = self._make_defense()
        seed = self._make_seed()
        encrypted = obj._encrypt_seed(seed)[:5]  # مقطوع
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed(encrypted, resurrection_key=seed.resurrection_key)
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_decrypt_seed_missing_required_field_rejected(self, caplog):
        """RED: JSON صالح لكنه ينقصه حقل إلزامي → None + تسجيل (رفض صريح).

        تُصنع البذرة بصيغة إرثية v1 (يدويًا) بعد حذف الحقل — لأن الغرض
        اختبار الرفض عند غياب الحقل، لا صيغة المظروف.
        """
        import base64 as _b64
        import hashlib as _hl
        import json as _json
        from backend.config import SOVEREIGN_KEY as _SK
        obj = self._make_defense()
        seed = self._make_seed()
        payload = _json.dumps({
            "id": seed.id,
            "created_at": seed.created_at,
            "core_fingerprint": seed.core_fingerprint,
            "essential_memory": seed.essential_memory,
            "expires_at": seed.expires_at,
            "phase": seed.phase,
            # resurrection_key محذوف عمدًا — حقل إلزامي
        }, ensure_ascii=False).encode()
        key1 = _hl.sha256(_SK.encode()).digest()
        key2 = _hl.sha256(seed.resurrection_key.encode()).digest()
        l1 = bytes(a ^ b for a, b in zip(payload, key1 * (len(payload) // 32 + 1)))
        l2 = bytes(a ^ b for a, b in zip(l1, key2 * (len(l1) // 32 + 1)))
        tampered_encrypted = _b64.b64encode(l2)
        # عبر مسار الترحيل الإرثي الصريح — الهدف: اختبار الرفض عند غياب
        # الحقل الإلزامي في التحقق (_validate_and_build_seed)، لا رفض الصيغة
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed_legacy_v1(
                tampered_encrypted, resurrection_key=seed.resurrection_key
            )
        assert result is None, "JSON بلا حقل إلزامي يجب أن يُرفض"
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_find_latest_seed_decrypts_from_disk(self, tmp_path, monkeypatch):
        """RED: _find_latest_seed يجب أن يفك تشفير أحدث بذرة من القرص عند توفر مفتاحها."""
        import backend.memory.defense.ransomware as rw
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", tmp_path)
        obj = self._make_defense()
        seed = self._make_seed("phoenix_seed_disk_003")
        encrypted = obj._encrypt_seed(seed)
        (tmp_path / f"{seed.id}.enc").write_bytes(encrypted)
        result = obj._find_latest_seed(resurrection_key=seed.resurrection_key)
        assert result is not None, "يجب أن تُفك البذرة من القرص عند توفير مفتاحها"
        assert result.id == seed.id

    def test_find_latest_seed_read_failure_logged(self, tmp_path, monkeypatch, caplog):
        """فشل قراءة ملف البذرة (OSError) → None + تسجيل استثناء (لا صمت)."""
        import backend.memory.defense.ransomware as rw
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", tmp_path)
        obj = self._make_defense()
        seed = self._make_seed("phoenix_seed_disk_004")
        (tmp_path / f"{seed.id}.enc").write_bytes(b"placeholder")
        def _boom(self):
            raise OSError("disk exploded (injected)")
        monkeypatch.setattr(Path, "read_bytes", _boom)
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._find_latest_seed(resurrection_key=seed.resurrection_key)
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records), \
            "فشل قراءة ملف البذرة يجب أن يُسجّل (لا صمت)"


# ============================================================
# Part 3: استمرارية القيامة + نزاهة البذرة (RED → GREEN)
# ============================================================

class TestPhoenixResurrectionContinuity:
    """R-682 (security v2): عقد المفتاح العام الموحد + منع التخفيض + إثبات الاستعادة
    + سياسة فساد الحالة الفاشلة الصريحة. AES-256-GCM معياري (لا XOR)."""

    def _make_core(self):
        core = MagicMock()
        core._last_hash = "a" * 64
        core.get_statistics.return_value = {"index": {"total_events": 3}}
        return core

    def _new_defense(self, monkeypatch):
        import backend.memory.defense.ransomware as rw
        obj = rw.RansomwareDefense.__new__(rw.RansomwareDefense)
        obj.core = self._make_core()
        obj.seeds = {}
        obj.ashes = {}
        obj.restored_seeds = {}
        obj.phoenix_phase = rw.PhoenixPhase.LIVING
        obj.resurrection_level = 0
        obj.is_transforming = False
        obj.last_resurrection = None
        obj.master_resurrection_key = obj._generate_master_key()
        obj._state_master_key_invalid = False
        obj._state_master_key_enc_original = None
        obj._extract_critical_items = lambda: []  # تبسيط حجم البيانات (ليس المسار الأمني)
        return obj

    def _setup_dirs(self, tmp_path, monkeypatch):
        import backend.memory.defense.ransomware as rw
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir()
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        return rw

    def _make_seed(self, essential=None):
        from backend.memory.defense.ransomware import PhoenixSeed
        return PhoenixSeed(
            id="phoenix_seed_ct_001",
            created_at=1000000.0,
            core_fingerprint="deadbeef1234",
            essential_memory=essential or {"core": {"integrity_count": 5, "last_hash": "x"}},
            resurrection_key="beef" * 16,
            expires_at=1000000.0 + 604800,
            phase="living",
        )

    # ── عقد المفتاح العام الموحد + إثبات الاستعادة بالبيانات ──

    def test_public_key_contract_and_data_proof_after_restart(self, tmp_path, monkeypatch):
        """العقد العام من طرف إلى طرف، بلا تفاصيل داخلية:

        key = first.get_resurrection_key()  →  restarted.resurrect(key)
        + إثبات الاستعادة بالبيانات: بيانات البذرة المقصودة موجودة فعليًا
        في مخزن الاستعادة (لا مجرد حدث مسجل).
        """
        rw = self._setup_dirs(tmp_path, monkeypatch)
        a = self._new_defense(monkeypatch)
        seed = a.create_phoenix_seed(reason="continuity-test")
        assert seed is not None
        seed_file = tmp_path / "seeds" / f"{seed.id}.enc"
        assert seed_file.exists(), "البذرة يجب أن تُكتب إلى القرص"
        assert (tmp_path / "phoenix_state.json").exists(), \
            "المفتاح الرئيسي يجب أن يكون محفوظًا بشكل متين قبل إعلان إنشاء البذرة"

        # مثيل B جديد (إعادة تشغيل) — تحميل الحالة ثم المفتاح العام
        b = self._new_defense(monkeypatch)
        assert b._load_state() is True
        assert b.master_resurrection_key == a.master_resurrection_key, \
            "المفتاح الرئيسي يجب أن يستمر عبر إعادة التشغيل"
        key = b.get_resurrection_key()  # المفتاح العام — لا اشتقاق يدوي
        b.phoenix_phase = rw.PhoenixPhase.DEAD
        result = b.resurrect(key)
        assert result.get("success") is True, \
            f"resurrect(get_resurrection_key()) يجب أن ينجح: {result}"
        assert b.phoenix_phase == rw.PhoenixPhase.REBORN
        # إثبات الاستعادة بالبيانات: نفس بيانات البذرة المقصودة
        assert seed.id in b.restored_seeds, \
            "البيانات المستعادة يجب أن تكون في مخزن الاستعادة — لا مجرد حدث"
        assert b.restored_seeds[seed.id] == seed.essential_memory

    def test_restore_failure_no_reborn_no_ash_clearing(self, tmp_path, monkeypatch):
        """فشل الاستعادة (حقن) → فشل صريح: لا REBORN، لا مسح للرماد، البذرة محفوظة."""
        rw = self._setup_dirs(tmp_path, monkeypatch)
        a = self._new_defense(monkeypatch)
        seed = a.create_phoenix_seed(reason="restore-failure-test")
        assert seed is not None
        a._save_state()
        b = self._new_defense(monkeypatch)
        assert b._load_state() is True
        # رماد موجود مسبقًا — يجب ألا يُمسح عند فشل الاستعادة
        ash = MagicMock()
        b.ashes["ash_1"] = ash
        key = b.get_resurrection_key()
        b.phoenix_phase = rw.PhoenixPhase.DEAD
        # حقن فشل الاستعادة في الاعتماد المقصود
        monkeypatch.setattr(b, "_restore_from_seed", lambda s: False)
        result = b.resurrect(key)
        assert result.get("success") is False, \
            "فشل الاستعادة يجب ألا يُعلن نجاحًا أبدًا"
        assert result.get("error"), "رسالة فشل صريحة"
        assert b.phoenix_phase == rw.PhoenixPhase.DEAD, \
            "لا REBORN بعد استعادة لم تحدث"
        assert "ash_1" in b.ashes, "الرماد (مواد الاسترداد) يجب ألا يُمسح عند الفشل"
        seed_file = tmp_path / "seeds" / f"{seed.id}.enc"
        assert seed_file.exists(), "البذرة يجب أن تبقى محفوظة عند الفشل"

    # ── منع التخفيض (downgrade) — لا مسار إرثي تلقائي ──

    def test_downgrade_stripped_envelope_rejected(self, tmp_path, monkeypatch, caplog):
        """نزع المظروف (تقديم النص الداخلي المجرد) يجب ألا يمر عبر المسار الإرثي."""
        import base64 as _b64
        import json as _json
        rw = self._setup_dirs(tmp_path, monkeypatch)
        obj = self._new_defense(monkeypatch)
        seed = self._make_seed()
        encrypted = obj._encrypt_seed(seed)
        env = _json.loads(_b64.b64decode(encrypted).decode("utf-8"))
        # المهاجم ينزع المظروف ويقدم النص المشفر الداخلي المجرد فقط
        inner_only = _b64.b64encode(_b64.b64decode(env["d"]))
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed(inner_only, resurrection_key=seed.resurrection_key)
        assert result is None, \
            "النص الداخلي المجرد (نزع المظروف) يجب أن يُرفض — منع التخفيض"
        matches = [r for r in caplog.records
                   if "downgrade" in r.getMessage() or "v3 envelope" in r.getMessage()]
        assert matches, "الرفض يجب أن يُسجَّل صراحة كمحاولة تخفيض"

    def test_downgrade_missing_tag_rejected(self, tmp_path, monkeypatch):
        """حذف حقل الوسم (t) من المظروف → رفض (لا انتقال لمسار إرثي)."""
        import base64 as _b64
        import json as _json
        rw = self._setup_dirs(tmp_path, monkeypatch)
        obj = self._new_defense(monkeypatch)
        seed = self._make_seed()
        encrypted = obj._encrypt_seed(seed)
        env = _json.loads(_b64.b64decode(encrypted).decode("utf-8"))
        del env["t"]
        tampered = _b64.b64encode(_json.dumps(env).encode())
        result = obj._decrypt_seed(tampered, resurrection_key=seed.resurrection_key)
        assert result is None, "مظروف بلا وسم مصادقة يجب أن يُرفض"

    def test_downgrade_wrong_version_rejected(self, tmp_path, monkeypatch):
        """تغيير الإصدار (v: 3 → 2) → رفض (لا انتقال لمسار إرثي)."""
        import base64 as _b64
        import json as _json
        rw = self._setup_dirs(tmp_path, monkeypatch)
        obj = self._new_defense(monkeypatch)
        seed = self._make_seed()
        encrypted = obj._encrypt_seed(seed)
        env = _json.loads(_b64.b64decode(encrypted).decode("utf-8"))
        env["v"] = 2
        tampered = _b64.b64encode(_json.dumps(env).encode())
        result = obj._decrypt_seed(tampered, resurrection_key=seed.resurrection_key)
        assert result is None, "إصدار مظروف غير مدعوم يجب أن يُرفض"

    def test_downgrade_corrupted_ciphertext_rejected(self, tmp_path, monkeypatch, caplog):
        """إفساد النص المشفر (d) → فشل مصادقة GCM صريح — لا فك غير موثق."""
        import base64 as _b64
        import json as _json
        rw = self._setup_dirs(tmp_path, monkeypatch)
        obj = self._new_defense(monkeypatch)
        seed = self._make_seed()
        encrypted = obj._encrypt_seed(seed)
        env = _json.loads(_b64.b64decode(encrypted).decode("utf-8"))
        ct = bytearray(_b64.b64decode(env["d"]))
        ct[0] ^= 0xFF  # إفساد بايت واحد
        env["d"] = _b64.b64encode(bytes(ct)).decode()
        tampered = _b64.b64encode(_json.dumps(env).encode())
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed(tampered, resurrection_key=seed.resurrection_key)
        assert result is None, "أي تعديل على النص المشفر يجب أن يُرفض (GCM)"
        matches = [r for r in caplog.records if "GCM authentication FAILED" in r.getMessage()]
        assert matches, "رفض التلاعب يجب أن يُسجَّل كفشل مصادقة GCM صريح"

    def test_tamper_any_ciphertext_change_rejected(self, tmp_path, monkeypatch, caplog):
        """AES-GCM يجعل التلاعب الذي يُبقي JSON صالحًا مستحيلًا بالبناء:
        أي تغيير في النص المشفر (ولو بايتًا واحدًا) = فشل وسم GCM = رفض.
        (في XOR المتكرر السابق كان تغيير 5→6 مع JSON صالح ممكنًا — v3 يغلقه بنيويًا)."""
        import base64 as _b64
        import json as _json
        rw = self._setup_dirs(tmp_path, monkeypatch)
        obj = self._new_defense(monkeypatch)
        seed = self._make_seed({"core": {"integrity_count": 5}})
        encrypted = obj._encrypt_seed(seed)
        env = _json.loads(_b64.b64decode(encrypted).decode("utf-8"))
        assert env.get("v") == 3, "الصيغة الحالية يجب أن تكون مظروف v3 (AES-GCM)"
        ct = bytearray(_b64.b64decode(env["d"]))
        ct[len(ct) // 2] ^= 0x01  # قلب بت واحد — أي تعديل مهما صغر
        env["d"] = _b64.b64encode(bytes(ct)).decode()
        tampered = _b64.b64encode(_json.dumps(env).encode())
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed(tampered, resurrection_key=seed.resurrection_key)
        assert result is None, "أي تعديل على النص المشفر يُرفض — مصادقة GCM"

    # ── سياسة فساد الحالة: فشل صريح يحافظ على الأصل ──

    def test_state_master_key_tamper_clear_failure_original_preserved(self, tmp_path, monkeypatch, caplog):
        """تعديل المفتاح المغلّف في الحالة → فشل صريح + الأصل محفوظ حرفيًا (لا استبدال صامت)."""
        import json as _json
        rw = self._setup_dirs(tmp_path, monkeypatch)
        a = self._new_defense(monkeypatch)
        a._save_state()
        state_file = tmp_path / "phoenix_state.json"
        state = _json.loads(state_file.read_text(encoding="utf-8"))
        original_enc = state["master_key_enc"]
        # تلاعب: إفساد النص المغلف
        state["master_key_enc"] = _json.dumps({"n": "AAAA", "d": "AAAA", "t": "AAAA"})
        tampered_enc = state["master_key_enc"]
        state_file.write_text(_json.dumps(state), encoding="utf-8")
        b = self._new_defense(monkeypatch)
        caplog.clear()
        with caplog.at_level(logging.CRITICAL, logger="backend.memory.defense.ransomware"):
            loaded = b._load_state()
        assert loaded is False, "فساد المفتاح المغلف = فشل تحميل صريح"
        assert b._state_master_key_invalid is True
        matches = [r for r in caplog.records if "SECURITY-FAIL" in r.getMessage()]
        assert matches, "فساد المفتاح يجب أن يُسجَّل كفشل أمني صريح (لا صمت)"
        # الحفظ اللاحق يحافظ على القيمة الموجودة (المتلاعب بها) حرفيًا —
        # لا استبدال صامت بمفتاح المثيل الجديد الذي قد يُتيه البذور نهائيًا
        b._save_state()
        after = _json.loads(state_file.read_text(encoding="utf-8"))
        assert after["master_key_enc"] == tampered_enc, \
            "القيمة الموجودة في الملف يجب أن تُحفظ كما هي — لا استبدال"
        assert after["master_key_enc"] != b._wrap_master_key(), \
            "يجب ألا يُستبدل صامتًا بمفتاح المثيل الجديد"
        assert after.get("master_key_enc_corrupt") is True
        # الأصل الحقيقي (قبل التلاعب) كان قيمة GCM صالحة — للتوثيق
        assert tampered_enc != original_enc

    def test_state_wrong_sovereign_key_clear_failure(self, tmp_path, monkeypatch, caplog):
        """تغيير مفتاح السيادة → فشل مصادقة GCM واضح (لا متابعة صامتة)."""
        import json as _json
        rw = self._setup_dirs(tmp_path, monkeypatch)
        a = self._new_defense(monkeypatch)
        a._save_state()
        state_file = tmp_path / "phoenix_state.json"
        assert state_file.exists()
        b = self._new_defense(monkeypatch)
        # مفتاح سيادة مختلف (كسلسلة مختلفة تمامًا)
        monkeypatch.setattr(rw, "SOVEREIGN_KEY", "a" * 128)
        caplog.clear()
        with caplog.at_level(logging.CRITICAL, logger="backend.memory.defense.ransomware"):
            loaded = b._load_state()
        assert loaded is False, "مفتاح سيادة مختلف = فشل صريح"
        matches = [r for r in caplog.records
                   if "SECURITY-FAIL" in r.getMessage()
                   and ("مفتاح سيادة" in r.getMessage() or "sovereign" in r.getMessage())]
        assert matches, "السبب (مفتاح سيادة مختلف/تلف) يجب أن يُوثَّق صراحة"

    # ── المسار الإرثي: صريح فقط (لا اكتشاف تلقائي) ──

    def test_legacy_v1_only_via_explicit_migration_with_warning(self, tmp_path, monkeypatch, caplog):
        """بذور v1 الإرثية: تُفك فقط عبر مسار الترحيل الصريح `_decrypt_seed_legacy_v1`
        مع تحذير صريح — والمسار الاعتيادي `_decrypt_seed` يرفضها (منع التخفيض)."""
        import base64 as _b64
        import hashlib as _hl
        import json as _json
        from backend.config import SOVEREIGN_KEY as _SK
        rw = self._setup_dirs(tmp_path, monkeypatch)
        obj = self._new_defense(monkeypatch)
        seed = self._make_seed({"core": {"last_hash": "x"}})
        # تشفير بالصيغة الإرثية v1 (خام — بلا مظروف)
        payload = _json.dumps({
            "id": seed.id, "created_at": seed.created_at,
            "core_fingerprint": seed.core_fingerprint,
            "essential_memory": seed.essential_memory,
            "resurrection_key": seed.resurrection_key,
            "expires_at": seed.expires_at, "phase": seed.phase,
        }, ensure_ascii=False).encode()
        key1 = _hl.sha256(_SK.encode()).digest()
        key2 = _hl.sha256(seed.resurrection_key.encode()).digest()
        l1 = bytes(x ^ y for x, y in zip(payload, key1 * (len(payload) // 32 + 1)))
        l2 = bytes(x ^ y for x, y in zip(l1, key2 * (len(l1) // 32 + 1)))
        legacy_encrypted = _b64.b64encode(l2)
        # 1) المسار الاعتيادي يرفضها (منع التخفيض — لا اكتشاف تلقائي)
        result = obj._decrypt_seed(legacy_encrypted, resurrection_key=seed.resurrection_key)
        assert result is None, \
            "المسار الاعتيادي يجب ألا يكتشف v1 ويكسرها تلقائيًا — منع التخفيض"
        # 2) مسار الترحيل الصريح يفكها مع تحذير مسجَّل
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="backend.memory.defense.ransomware"):
            migrated = obj._decrypt_seed_legacy_v1(
                legacy_encrypted, resurrection_key=seed.resurrection_key
            )
        assert migrated is not None, "الترحيل الصريح يجب أن يفك البذرة الإرثية"
        assert migrated.id == seed.id
        matches = [r for r in caplog.records
                   if "legacy v1 migration" in r.getMessage()
                   and "integrity NOT verifiable" in r.getMessage()]
        assert matches, "تحذير صريح: ترحيل إرثي — النزاهة غير قابلة للتحقق"


# ============================================================
# Part 2: المواقع منخفضة الخطورة — اختبارات سلوكية
# ============================================================

class TestNexusLifecycleSites:
    """backend/compat/nexus_lifecycle.py:85,112 — فشل تهيئة المحرك/المكونات."""

    def _reset(self, monkeypatch):
        import backend.compat.nexus_lifecycle as lc
        monkeypatch.setattr(lc, "_ENGINE", None)
        monkeypatch.setattr(lc, "_START_ERROR", None)
        monkeypatch.setattr(lc, "_LAST_START_TIME", 0.0)
        return lc

    def _assert_logged(self, caplog, expected_msg):
        matches = [r for r in caplog.records
                   if r.name == "backend.compat.nexus_lifecycle"
                   and expected_msg in r.getMessage()]
        assert matches, \
            f"يجب أن يُسجَّل من المسجّل الصحيح رسالة تحتوي '{expected_msg}'"

    def test_engine_init_failure_returns_none_logged(self, monkeypatch, caplog):
        lc = self._reset(monkeypatch)
        # حقن فشل في get_engine
        import nexus.core.engine as engine_mod
        def _boom():
            raise RuntimeError("engine init exploded (injected)")
        monkeypatch.setattr(engine_mod, "get_engine", _boom)
        caplog.clear()  # إزالة سجلات التهيئة
        with caplog.at_level(logging.ERROR, logger="backend.compat.nexus_lifecycle"):
            result = asyncio.run(lc.ensure_nexus_running_async())
        assert result is None
        self._assert_logged(caplog, "R-682")
        self._assert_logged(caplog, "engine init exploded")

    def test_component_init_failure_returns_none_logged(self, monkeypatch, caplog):
        lc = self._reset(monkeypatch)
        # محرك وهمي سليم + حقن فشل في initialize_nexus
        engine = MagicMock()
        engine._running = False
        engine.components = {}  # فارغ لتفعيل فرع تهيئة المكونات
        import nexus.core.engine as engine_mod
        monkeypatch.setattr(engine_mod, "get_engine", lambda: engine)
        import nexus.main as nexus_main
        def _boom2():
            raise RuntimeError("component init exploded (injected)")
        monkeypatch.setattr(nexus_main, "initialize_nexus", _boom2)
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.compat.nexus_lifecycle"):
            result = asyncio.run(lc.ensure_nexus_running_async())
        assert result is None
        self._assert_logged(caplog, "R-682")
        self._assert_logged(caplog, "component init exploded")

    def test_success_path_running_engine_returned(self, monkeypatch):
        """المسار السليم: محرك يعمل → يُعاد كما هو."""
        lc = self._reset(monkeypatch)
        engine = MagicMock()
        engine._running = True
        monkeypatch.setattr(lc, "_ENGINE", engine)
        result = asyncio.run(lc.ensure_nexus_running_async())
        assert result is engine


class TestNexusRecommendationsSite:
    """backend/compat/nexus_recommendations.py:43 — فشل جلب محرك التوصيات."""

    def test_get_recommendation_engine_failure_logged(self, monkeypatch, caplog):
        import nexus.core.engine as engine_mod
        def _boom():
            raise RuntimeError("recommendations engine exploded (injected)")
        monkeypatch.setattr(engine_mod, "get_engine", _boom)
        from backend.compat import nexus_recommendations as rec
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.compat.nexus_recommendations"):
            result = rec.get_recommendation_engine()
        assert result is None
        matches = [r for r in caplog.records
                   if r.name == "backend.compat.nexus_recommendations"
                   and "R-682" in r.getMessage()
                   and "recommendations engine exploded" in r.getMessage()]
        assert matches, "يجب تسجيل الرسالة المحقونة من المسجّل الصحيح"

    def test_success_path_recommender_returned(self, monkeypatch):
        """المسار السليم: مكوّن recommender مسجل → يُعاد كما هو."""
        import nexus.core.engine as engine_mod
        sentinel = object()
        engine = MagicMock()
        engine.get_component.return_value = sentinel
        monkeypatch.setattr(engine_mod, "get_engine", lambda: engine)
        from backend.compat import nexus_recommendations as rec
        result = rec.get_recommendation_engine()
        assert result is sentinel


class TestEvolutionMutationSite:
    """backend/memory/biological/evolution.py:411 — فشل إجراء طفرة في التطور."""

    def _make_evolution(self):
        """حالة سليمة كاملة الحد الأدنى (ليست كائنًا ناقص التهيئة)."""
        from backend.memory.biological.evolution import MemoryEvolution
        evo = MemoryEvolution.__new__(MemoryEvolution)
        evo.genome = {}                    # جينوم صالح (فارغ — الطفرة تُنشئ مفاهيم جديدة)
        evo.current_generation = 1
        evo.mutations = []
        evo.store = MagicMock()            # مخزن صالح
        evo._save_mutation = lambda m: None
        evo.core = type("MockCore", (), {"append_event": lambda *a, **k: None})()
        return evo

    def test_mutation_success_path(self):
        """المسار السليم: طفرة على مفهوم → مفهوم جديد + طفرة ناجحة في السجل."""
        from backend.memory.biological.evolution import MUTATION_TYPE_GENERALIZE
        evo = self._make_evolution()
        result = evo.mutate_concept("sovereignty", mutation_type=MUTATION_TYPE_GENERALIZE)
        assert result is not None, "الطفرة السليمة يجب أن تُنتج مفهومًا"
        assert len(evo.mutations) == 1
        assert evo.mutations[0].success is True
        assert len(evo.genome) == 1  # المفهوم الجديد أُنشئ فعلاً

    def test_mutation_failure_logged_and_returns_none(self, monkeypatch, caplog):
        """حقن فشل مستهدف في الاعتماد المقصود (_save_mutation) →
        None + تسجيل استثناء + طفرة فاشلة في السجل (لا صمت)."""
        evo = self._make_evolution()
        def _boom(mutation):
            raise RuntimeError("save_mutation exploded (injected)")
        monkeypatch.setattr(evo, "_save_mutation", _boom)
        from backend.memory.biological.evolution import MUTATION_TYPE_GENERALIZE
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.biological.evolution"):
            result = evo.mutate_concept("sovereignty", mutation_type=MUTATION_TYPE_GENERALIZE)
        assert result is None
        matches = [r for r in caplog.records
                   if r.name == "backend.memory.biological.evolution"
                   and "R-682" in r.getMessage()
                   and "save_mutation exploded" in r.getMessage()]
        assert matches, "يجب تسجيل الرسالة المحقونة من المسجّل الصحيح"
        # الطفرة الفاشلة تُسجَّل في سجل الطفرات
        # (الطفرة الأصلية تُسجّل قبل الحفظ، ثم يُضاف سجل الفشل بعد الاستثناء)
        assert len(evo.mutations) >= 1
        assert evo.mutations[-1].success is False, \
            "آخر طفرة يجب أن تكون الفاشلة (المسجلة بعد الاستثناء)"


class TestMemoryCoreSigningKeySite:
    """backend/memory/core.py:720 — فشل جلب مفتاح التوقيع النشط."""

    def _make_core(self, keyring):
        from backend.memory.core import SovereignCore
        core = SovereignCore.__new__(SovereignCore)
        core._keyring = keyring
        return core

    def test_signing_key_failure_logged(self, caplog):
        class BadKeyring:
            def get_active_key(self):
                raise RuntimeError("keyring exploded (injected)")
        core = self._make_core(BadKeyring())
        with caplog.at_level(logging.ERROR, logger="backend.memory.core"):
            result = core._get_current_signing_key_id()
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_signing_key_success_path(self):
        """المسار السليم: keyring سليم يعيد مفتاحًا نشطًا."""
        from backend.sovereign.keys.keyring import KeyStatus
        key = MagicMock()
        key.key_id = "active-key-1"
        key.status = KeyStatus.ACTIVE
        class GoodKeyring:
            def get_active_key(self):
                return key
        core = self._make_core(GoodKeyring())
        result = core._get_current_signing_key_id()
        assert result == "active-key-1"


class TestEncodingDecryptSite:
    """backend/memory/encoding.py:455 — فك تشفير بيانات تالفة/غير قابلة للفك."""

    def _make_encoder(self):
        from backend.memory.encoding import QuantumLikeEncryption
        return QuantumLikeEncryption()

    def test_decrypt_garbage_logged(self, caplog):
        enc = self._make_encoder()
        with caplog.at_level(logging.ERROR, logger="backend.memory.encoding"):
            result = enc.decrypt("not-valid-encrypted-token!!!")
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_decrypt_roundtrip_success_path(self):
        """المسار السليم: التشفير ثم فك التشفير يعيد البيانات الأصلية."""
        enc = self._make_encoder()
        original = b"sovereign memory payload - roundtrip"
        token = enc.encrypt(original)
        result = enc.decrypt(token)
        assert result == original


class TestOrchestratorLoadSites:
    """backend/orchestrator.py:288,301,314,431,450 — فشل تحميل المكونات."""

    def _make_orchestrator(self):
        from backend.orchestrator import SovereignOrchestrator
        orch = SovereignOrchestrator.__new__(SovereignOrchestrator)
        orch._update_component_health = lambda *a, **k: None
        return orch

    def _assert_failure_logged(self, caplog, result, injected_msg):
        assert result is None
        matches = [r for r in caplog.records
                   if r.name == "backend.orchestrator"
                   and injected_msg in r.getMessage()]
        assert matches, f"يجب تسجيل '{injected_msg}' من مسجّل orchestrator"

    def _patch_boom(self, monkeypatch, module, attr):
        def _boom():
            raise RuntimeError(f"{attr} exploded (injected)")
        monkeypatch.setattr(module, attr, _boom)
        return f"{attr} exploded (injected)"

    def test_load_memory_core_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import memory.core as mem_core
        msg = self._patch_boom(monkeypatch, mem_core, "get_core")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_memory_core()
        self._assert_failure_logged(caplog, result, msg)

    def test_load_memory_core_success_path(self, monkeypatch):
        """المسار السليم: get_core يعيد قيمة → تُعاد كما هي."""
        orch = self._make_orchestrator()
        import memory.core as mem_core
        sentinel = object()
        monkeypatch.setattr(mem_core, "get_core", lambda: sentinel)
        result = orch._load_memory_core()
        assert result is sentinel

    def test_load_memory_dynamic_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import memory.dynamic as dyn
        msg = self._patch_boom(monkeypatch, dyn, "get_dynamic_memory")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_memory_dynamic()
        self._assert_failure_logged(caplog, result, msg)

    def test_load_memory_dynamic_success_path(self, monkeypatch):
        orch = self._make_orchestrator()
        import memory.dynamic as dyn
        sentinel = object()
        monkeypatch.setattr(dyn, "get_dynamic_memory", lambda: sentinel)
        result = orch._load_memory_dynamic()
        assert result is sentinel

    def test_load_memory_store_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import memory.store as st
        msg = self._patch_boom(monkeypatch, st, "get_store")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_memory_store()
        self._assert_failure_logged(caplog, result, msg)

    def test_load_memory_store_success_path(self, monkeypatch):
        orch = self._make_orchestrator()
        import memory.store as st
        sentinel = object()
        monkeypatch.setattr(st, "get_store", lambda: sentinel)
        result = orch._load_memory_store()
        assert result is sentinel

    def test_load_quantum_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import quantum.quantum_controller as qc
        msg = self._patch_boom(monkeypatch, qc, "get_quantum_controller")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_quantum()
        self._assert_failure_logged(caplog, result, msg)

    def test_load_quantum_success_path(self, monkeypatch):
        orch = self._make_orchestrator()
        import quantum.quantum_controller as qc
        sentinel = object()
        monkeypatch.setattr(qc, "get_quantum_controller", lambda: sentinel)
        result = orch._load_quantum()
        assert result is sentinel

    def test_load_nexus_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import nexus.main as nmain
        msg = self._patch_boom(monkeypatch, nmain, "initialize_nexus")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_nexus()
        self._assert_failure_logged(caplog, result, msg)

    def test_load_nexus_success_path(self, monkeypatch):
        orch = self._make_orchestrator()
        import nexus.main as nmain
        sentinel = object()
        monkeypatch.setattr(nmain, "initialize_nexus", lambda: sentinel)
        result = orch._load_nexus()
        assert result is sentinel


class TestDataProcessorSite:
    """nexus/data_pipeline/processor.py:55 — فشل معالجة سجل بيانات."""

    def _make_processor(self):
        from nexus.data_pipeline.processor import DataProcessor
        return DataProcessor()

    def test_process_failure_logged_and_counted(self, caplog):
        """فشل المعالجة: None + تسجيل + عدّاد failed يزيد (لا صمت)."""
        p = self._make_processor()
        # حقن فشل عبر محول يرفع استثناء
        def _boom(data):
            raise RuntimeError("transformer exploded (injected)")
        p.register_transformer("failing_schema", _boom)
        with caplog.at_level(logging.ERROR, logger="nexus.data_pipeline.processor"):
            result = p.process({"a": 1}, source="test", schema="failing_schema")
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records)
        assert p.stats["failed"] == 1, "عدّاد الفشل يجب أن يزيد"

    def test_process_success_path(self):
        """المسار السليم: سجل صالح يُعاد كـ ProcessedRecord."""
        p = self._make_processor()
        result = p.process({"a": 1, "b": "text"})
        assert result is not None
        assert result.processed == {"a": 1, "b": "text"}
        assert p.stats["processed"] == 1


class TestCodeAnalyzerSite:
    """nexus/performance/code_analyzer.py:51 — تحليل ملف غير قابل للتحليل."""

    def _make_analyzer(self):
        from nexus.performance.code_analyzer import CodeAnalyzer
        return CodeAnalyzer()

    def test_analyze_invalid_python_logged(self, tmp_path, caplog):
        """ملف Python بتركيب غير صالح → None + تسجيل (لا صمت)."""
        bad = tmp_path / "bad.py"
        bad.write_text("def broken(:\n    pass\n", encoding="utf-8")
        analyzer = self._make_analyzer()
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="nexus.performance.code_analyzer"):
            result = analyzer.analyze_file(str(bad))
        assert result is None
        matches = [r for r in caplog.records
                   if r.name == "nexus.performance.code_analyzer"
                   and "bad.py" in r.getMessage()]
        assert matches, "يجب تسجيل اسم الملف المعطوب من المسجّل الصحيح"

    def test_analyze_valid_python_success_path(self, tmp_path):
        """المسار السليم: ملف صالح يعيد تحليلًا."""
        good = tmp_path / "good.py"
        good.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        analyzer = self._make_analyzer()
        result = analyzer.analyze_file(str(good))
        assert result is not None


class TestLongTermStoreSite:
    """nexus/storage/long_term_store.py:51 — تحميل سجل JSON تالف."""

    def _make_store(self, tmp_path):
        from nexus.storage.long_term_store import LongTermStore
        return LongTermStore(str(tmp_path))

    def test_load_corrupt_json_logged(self, tmp_path, caplog):
        """ملف JSON تالف → None + تسجيل (لا صمت)."""
        store = self._make_store(tmp_path)
        store.save("coll", "corrupt_key", {"x": 1})
        # تلف الملف بعد الحفظ
        (tmp_path / "coll" / "corrupt_key.json").write_text(
            '{"key": "corrupt_key", "data": [broken', encoding="utf-8")
        with caplog.at_level(logging.ERROR, logger="nexus.storage.long_term"):
            result = store.load("coll", "corrupt_key")
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_load_valid_json_success_path(self, tmp_path):
        """المسار السليم: سجل صالح يُحمَّل."""
        store = self._make_store(tmp_path)
        store.save("coll", "valid_key", {"data": [1, 2, 3]})
        result = store.load("coll", "valid_key")
        assert result == {"data": [1, 2, 3]}
