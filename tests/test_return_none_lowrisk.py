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
        return obj

    def _setup_dirs(self, tmp_path, monkeypatch):
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir()
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        # عزل المخزن (واجهة get_store نفسها) بسجل مميز قابل للاستعادة
        iso = _IsolatedStore()
        iso.save_semantic(
            concept="continuity_proof_record",
            definition="سجل استمرارية",
            confidence=0.9,
        )
        monkeypatch.setattr(store_mod, "get_store", lambda: iso)
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
        # الحفظ اللاحق مرفوض بالكامل — الملف يُحفظ كاملًا حرفيًا بلا أي تعديل
        # (دليل للتحقيق؛ أي كتابة قد تستبدل دليل الفساد بحالة تخفي فقدان المفتاح)
        raw_before = state_file.read_bytes()
        assert b._save_state() is False, \
            "الكتابة بعد فشل التحميل يجب أن تُرفض — حفظ الملف الأصلي"
        assert state_file.read_bytes() == raw_before, \
            "الملف الأصلي يجب أن يبقى كاملًا حرفيًا — لا تعديل ولا استبدال"
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
# Part 1b: التهيئة الحقيقية — عقد كامل من طرف إلى طرف (R-682 security v3)
# ============================================================

class _IsolatedStore:
    """مخزن معزول بواجهة التطبيق نفسها (get_store/save_semantic/query)."""

    def __init__(self):
        self.items = {}  # (kind, key) -> item

    def save_semantic(self, concept, definition, aliases=None,
                      related_concepts=None, examples=None, confidence=0.5):
        self.items[("semantic", concept)] = {
            "_id": concept,
            "concept": concept,
            "definition": definition,
            "aliases": aliases or [],
            "related_concepts": related_concepts or {},
            "confidence": confidence,
            "_importance": max(confidence, 0.9),
        }
        return concept

    def query(self, kind, tag=None, min_importance=0.0, limit=50,
              search_text=None):
        return [v for (k, _), v in self.items.items()
                if k == kind and v["_importance"] >= min_importance][:limit]

    def save_procedural(self, name, description, trigger_patterns,
                        action_sequence, parameters=None, importance=0.8):
        self.items[("procedural", name)] = {
            "_id": name,
            "name": name,
            "description": description,
            "trigger_patterns": trigger_patterns,
            "action_sequence": action_sequence,
            "parameters": parameters or {},
            "_importance": importance,
        }
        return name

    def delete(self, concept):
        self.items.pop(("semantic", concept), None)


class _NoThreads:
    """خيط معطّل (مسموح في الاختبار) — منطق التهيئة نفسه لا يُتجاوز."""

    def __init__(self, *a, **k):
        pass

    def start(self):
        pass


class TestRealInitSecurity:
    """R-682 (security v3): عقد المفتاح العام عبر التهيئة الحقيقية (لا __new__
    ولا تحميل/حفظ يدوي) + فشل الحالة يوقف التهيئة (fail-closed) + تلاعب
    موضعي 5→6 مرفوض + reset(preserve_seeds=True) لا يُفقد المفاتيح."""

    def _mock_core(self):
        core = MagicMock()
        core._last_hash = "a" * 64
        core.get_statistics.return_value = {"index": {"total_events": 3}}
        return core

    def _patch_env(self, tmp_path, monkeypatch, store):
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        monkeypatch.setattr(rw, "get_core", self._mock_core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        monkeypatch.setattr(store_mod, "get_store", lambda: store)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)
        return rw

    def test_public_contract_real_init_end_to_end(self, tmp_path, monkeypatch):
        """العقد من طرف إلى طرف عبر التهيئة الحقيقية + إثبات الاستعادة عبر
        واجهة القراءة المعتادة للمخزن (لا مخزن جانبي):

        first = RansomwareDefense()  (تهيئة حقيقية، تخزين معزول)
        seed = first.create_phoenix_seed(...)
        key = first.get_resurrection_key()
        restarted = RansomwareDefense()  (تهيئة حقيقية — بلا تحميل/حفظ يدوي)
        result = restarted.resurrect(key)  → نجاح + البيانات عادت للمخزن فعليًا
        """
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        # سجل مميز في المخزن (عبر واجهة الكتابة المعتادة)
        concept = "sovereign_ai_r682_restore_proof"
        store.save_semantic(
            concept=concept,
            definition="دليل استعادة عبر المخزن الحقيقي",
            confidence=0.95,
        )
        # 1) المثيل الأول — تهيئة حقيقية + بذرة تحمل السجل المميز
        first = rw.RansomwareDefense()
        seed = first.create_phoenix_seed(reason="e2e-contract-test")
        assert seed is not None
        carried = [i for i in seed.essential_memory.get("critical_memory", [])
                   if i.get("concept") == concept]
        assert carried, "البذرة يجب أن تحمل السجل المميز قابلًا للاستعادة"
        key = first.get_resurrection_key()
        # 2) فقدان البيانات من المخزن بعد البذرة
        store.delete(concept)
        assert not store.query("semantic", min_importance=0.7), "السجل مفقود الآن"
        # 3) إعادة تشغيل — تهيئة حقيقية (بلا أي استدعاء يدوي لتحميل/حفظ)
        restarted = rw.RansomwareDefense()
        assert restarted.master_resurrection_key == first.master_resurrection_key
        # 4) القيامة عبر الواجهة العامة (resurrect يتطلب DEAD — أقصى ما يسمح به
        #    تسلسل advisor المطلوب دون اختبار الموت نفسه)
        restarted.phoenix_phase = rw.PhoenixPhase.DEAD
        result = restarted.resurrect(key)
        assert result.get("success") is True, f"القيامة يجب أن تنجح: {result}"
        assert restarted.phoenix_phase == rw.PhoenixPhase.REBORN
        # 5) الإثبات عبر واجهة القراءة المعتادة للمخزن — البيانات عادت فعليًا
        restored = [i for i in store.query("semantic", min_importance=0.7)
                    if i.get("concept") == concept]
        assert restored, \
            "السجل المميز يجب أن يعود إلى المخزن عبر واجهة القراءة المعتادة"
        assert restored[0]["definition"] == "دليل استعادة عبر المخزن الحقيقي"

    def test_truncated_state_fails_init_and_preserves_file(self, tmp_path, monkeypatch):
        """JSON مبتور في الحالة → التهيئة تفشل (fail-closed) قبل الحفظ والخيوط،
        والملف الأصلي يبقى كاملًا حرفيًا دون أي تعديل."""
        import pytest as _pytest
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        state_file = tmp_path / "phoenix_state.json"
        truncated = b'{"phoenix_phase": "dead", "master_key_e'  # مبتور
        state_file.write_bytes(truncated)
        with _pytest.raises(RuntimeError, match="R-682"):
            rw.RansomwareDefense()
        assert state_file.read_bytes() == truncated, \
            "الملف الأصلي يجب أن يُحفظ كاملًا حرفيًا — لا تعديل ولا استبدال"

    def test_corrupt_wrapped_key_fails_init(self, tmp_path, monkeypatch):
        """مفتاح مغلّف فاسد في الحالة → التهيئة تفشل (fail-closed) والملف محفوظ."""
        import json as _json
        import pytest as _pytest
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        state_file = tmp_path / "phoenix_state.json"
        state_file.write_text(_json.dumps({
            "phoenix_phase": "dead",
            "master_key_enc": _json.dumps({"n": "AAAA", "d": "AAAA", "t": "AAAA"}),
        }), encoding="utf-8")
        raw = state_file.read_bytes()
        with _pytest.raises(RuntimeError, match="R-682"):
            rw.RansomwareDefense()
        assert state_file.read_bytes() == raw, "الملف محفوظ كاملًا دون تعديل"

    def test_positional_tamper_5_to_6_rejected(self, tmp_path, monkeypatch, caplog):
        """تلاعب موضعي مقصود: تغيير '5'→'6' في النص الصريح عبر بايت النص
        المشفر المقابل (CTR يحفظ المواضع — لولاه لَصار JSON صالحًا بقيمة 6)،
        مع إبقاء وسم GCM — الرفض فشل مصادقة صريح (المصادقة تمنع قبول النص
        المعدّل؛ القول بأن التعديل نفسه مستحيل غير دقيق)."""
        import base64 as _b64
        import json as _json
        rw = self._patch_env(tmp_path, monkeypatch, _IsolatedStore())
        obj = rw.RansomwareDefense.__new__(rw.RansomwareDefense)
        obj.seeds = {}
        obj.master_resurrection_key = "b" * 128
        from backend.memory.defense.ransomware import PhoenixSeed
        seed = PhoenixSeed(
            id="phoenix_seed_pos_001",
            created_at=1000000.0,
            core_fingerprint="deadbeef1234",
            essential_memory={"core": {"integrity_count": 5}},
            resurrection_key="beef" * 16,
            expires_at=1000000.0 + 604800,
            phase="living",
        )
        encrypted = obj._encrypt_seed(seed)
        env = _json.loads(_b64.b64decode(encrypted).decode("utf-8"))
        ct = _b64.b64decode(env["d"])
        # النص الصريح المعروف — نفس بناء _encrypt_seed (CTR يحفظ المواضع)
        plaintext = _json.dumps({
            "id": seed.id, "created_at": seed.created_at,
            "core_fingerprint": seed.core_fingerprint,
            "essential_memory": seed.essential_memory,
            "resurrection_key": seed.resurrection_key,
            "expires_at": seed.expires_at,
        }, ensure_ascii=False).encode()
        target = b'"integrity_count": 5'
        idx = plaintext.find(target)
        assert idx >= 0, "القيمة المستهدفة موجودة في النص الصريح المعروف"
        pos = idx + len(b'"integrity_count": ')  # موضع بايت '5'
        assert len(ct) == len(plaintext), "CTR: طول النص المشفر = طول النص الصريح"
        # قلب البايت المقابل: يغيّر '5'→'6' في النص المفكوك لو غاب الوسم
        ct2 = bytearray(ct)
        ct2[pos] ^= ord("5") ^ ord("6")
        env["d"] = _b64.b64encode(bytes(ct2)).decode()
        # الوسم يبقى كما هو — هذا هو التلاعب
        tampered = _b64.b64encode(_json.dumps(env).encode())
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed(tampered, resurrection_key=seed.resurrection_key)
        assert result is None, \
            "تلاعب 5→6 الموضعي (JSON يبقى صالحًا) يجب أن يُرفض بفشل مصادقة GCM"
        matches = [r for r in caplog.records if "GCM authentication FAILED" in r.getMessage()]
        assert matches

    def _make_real_store(self, store_dir, monkeypatch, encoder=None):
        """SolidMemoryStore حقيقي (لا بديل قاموسي) بملفات معزولة تحت tmp_path.
        encoder=None → المفرد؛ أو مشفر محدد (لاختبار استمرارية المشتق)."""
        import backend.memory.store as store_mod
        from backend.memory.store import SolidMemoryStore
        from backend.memory.encoding import get_encoder
        store_dir.mkdir(parents=True, exist_ok=True)
        file_map = {"index": store_dir / "index.json"}
        for kind in store_mod.MemoryKind:
            file_map[kind.value] = store_dir / f"{kind.value}.json"
        monkeypatch.setattr(store_mod, "FILE_MAP", file_map)
        monkeypatch.setattr(store_mod, "get_core", self._mock_core)
        if encoder is None:
            monkeypatch.setattr(store_mod, "get_encoder", get_encoder)
        else:
            monkeypatch.setattr(store_mod, "get_encoder", lambda: encoder)
        return SolidMemoryStore()

    def test_real_store_e2e_restoration(self, tmp_path, monkeypatch):
        """إثبات الاستعادة عبر مخزن التطبيق الفعلي (SolidMemoryStore الحقيقي
        بملفات معزولة) — لا بديل قاموسيًا: سجل مميز → بذرة → فقدان (مخزن
        فارغ جديد) → إعادة تشغيل حقيقية → resurrect → السجل عاد عبر واجهة
        القراءة المعتادة، وبعد إعادة فتح المخزن (إثبات استمرار على القرص)."""
        store = _IsolatedStore()  # لا يُستخدم — فقط لتوافق _patch_env
        rw = self._patch_env(tmp_path, monkeypatch, store)
        import backend.memory.store as store_mod
        concept = "sovereign_ai_r682_real_store_proof"
        definition = "دليل استعادة عبر SolidMemoryStore الحقيقي"
        # 1) المخزن الحقيقي الأول (ملفات معزولة) + السجل المميز
        store1 = self._make_real_store(tmp_path / "store_a", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store1)
        store1.save_semantic(concept=concept, definition=definition, confidence=0.95)
        assert any(i.get("concept") == concept
                   for i in store1.query("semantic", min_importance=0.7))
        # 2) تهيئة حقيقية + بذرة تحمل السجل
        first = rw.RansomwareDefense()
        seed = first.create_phoenix_seed(reason="real-store-e2e")
        assert seed is not None
        carried = [i for i in seed.essential_memory.get("critical_memory", [])
                   if i.get("concept") == concept]
        assert carried, "البذرة يجب أن تحمل السجل المميز"
        key = first.get_resurrection_key()
        # 3) الفقدان: مخزن جديد فارغ تمامًا (ملفات جديدة) — البيانات ضاعت
        store2 = self._make_real_store(tmp_path / "store_b", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store2)
        assert not store2.query("semantic", min_importance=0.7), "المخزن الجديد فارغ"
        # 4) إعادة تشغيل حقيقية (بلا تحميل/حفظ يدوي) + قيامة عبر الواجهة العامة
        restarted = rw.RansomwareDefense()
        assert restarted.master_resurrection_key == first.master_resurrection_key
        restarted.phoenix_phase = rw.PhoenixPhase.DEAD
        result = restarted.resurrect(key)
        assert result.get("success") is True, f"القيامة يجب أن تنجح: {result}"
        # 5) الإثبات عبر واجهة القراءة المعتادة للمخزن الحقيقي
        restored = [i for i in store2.query("semantic", min_importance=0.7)
                    if i.get("concept") == concept]
        assert restored, "السجل عاد عبر واجهة القراءة المعتادة للمخزن الحقيقي"
        assert restored[0].get("definition") == definition
        # 6) إعادة فتح المخزن من القرص — إثبات الاستمرار (لا ذاكرة فقط)
        store3 = self._make_real_store(tmp_path / "store_b", monkeypatch)
        reopened = [i for i in store3.query("semantic", min_importance=0.7)
                    if i.get("concept") == concept]
        assert reopened, "السجل مستمر على القرص — عاد بعد إعادة فتح المخزن"

    def test_restore_empty_critical_memory_fails(self, tmp_path, monkeypatch):
        """بذرة بلا بيانات قابلة للاستعادة → لا يُعلن نجاح استعادة (فشل صريح)."""
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        obj = rw.RansomwareDefense.__new__(rw.RansomwareDefense)
        obj.core = self._mock_core()
        obj.seeds = {}
        obj.ashes = {}
        obj.restored_seeds = {}
        obj.master_resurrection_key = "c" * 128
        from backend.memory.defense.ransomware import PhoenixSeed
        seed = PhoenixSeed(
            id="phoenix_seed_empty_001",
            created_at=1000000.0,
            core_fingerprint="deadbeef1234",
            essential_memory={"core": {"last_hash": "x"}, "critical_memory": []},
            resurrection_key="beef" * 16,
            expires_at=1000000.0 + 604800,
            phase="living",
        )
        assert obj._restore_from_seed(seed) is False, \
            "لا يجوز إعلان نجاح استعادة دون أي بيانات مستعادة فعليًا"

    def test_restore_procedural_item_restored(self, tmp_path, monkeypatch):
        """عنصر إجرائي في البذرة يجب أن يُستعاد فعليًا في المخزن الحقيقي —
        لا يُعلن نجاح عام مع تخطي البيانات المقصودة."""
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        import backend.memory.store as store_mod
        store1 = self._make_real_store(tmp_path / "store_p", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store1)
        store1.save_procedural(
            name="sovereign_r682_skill",
            description="مهارة إثبات الاستعادة الإجرائية",
            trigger_patterns=["proof"],
            action_sequence=["verify"],
            importance=0.9,
        )
        assert any(i.get("name") == "sovereign_r682_skill"
                   for i in store1.query("procedural", min_importance=0.7))
        first = rw.RansomwareDefense()
        seed = first.create_phoenix_seed(reason="procedural-restore")
        assert seed is not None
        carried = [i for i in seed.essential_memory.get("critical_memory", [])
                   if i.get("type") == "procedural"]
        assert carried, "البذرة يجب أن تحمل العنصر الإجرائي (ببياناته القابلة للاستعادة)"
        key = first.get_resurrection_key()
        # الفقدان: مخزن فارغ جديد
        store2 = self._make_real_store(tmp_path / "store_q", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store2)
        restarted = rw.RansomwareDefense()
        restarted.phoenix_phase = rw.PhoenixPhase.DEAD
        result = restarted.resurrect(key)
        assert result.get("success") is True, f"القيامة يجب أن تنجح: {result}"
        restored = [i for i in store2.query("procedural", min_importance=0.7)
                    if i.get("name") == "sovereign_r682_skill"]
        assert restored, \
            "العنصر الإجرائي يجب أن يعود عبر واجهة القراءة المعتادة للمخزن الحقيقي"
        assert restored[0].get("description") == "مهارة إثبات الاستعادة الإجرائية"

    def test_state_missing_master_key_fails_init(self, tmp_path, monkeypatch):
        """JSON صالح لكن master_key_enc محذوف → التهيئة تفشل (صلاحية JSON
        وحدها لا تجعل الحالة قابلة للاسترجاع) والملف محفوظ دون تعديل."""
        import json as _json
        import pytest as _pytest
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        state_file = tmp_path / "phoenix_state.json"
        state_file.write_text(_json.dumps({
            "phoenix_phase": "dead",
            "seeds_count": 1,
        }), encoding="utf-8")
        raw = state_file.read_bytes()
        with _pytest.raises(RuntimeError, match="R-682"):
            rw.RansomwareDefense()
        assert state_file.read_bytes() == raw, \
            "الملف محفوظ كاملًا — لا استبدال صامت بحالة جديدة تخفي فقدان المفتاح"

    def test_init_save_failure_stops_init(self, tmp_path, monkeypatch):
        """فشل حفظ الحالة الأولي يوقف التهيئة قبل الخيوط وإعلان الجاهزية."""
        import pytest as _pytest
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        import os as _os
        def _boom(src, dst):
            raise OSError("replace exploded (injected)")
        monkeypatch.setattr(_os, "replace", _boom)
        with _pytest.raises(RuntimeError, match="R-682"):
            rw.RansomwareDefense()

    def test_sovereign_key_differs_real_init_fails(self, tmp_path, monkeypatch):
        """مفتاح سيادة مختلف عبر التهيئة الحقيقية → فشل صريح + الملف محفوظ."""
        import pytest as _pytest
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        first = rw.RansomwareDefense()  # يكتب الحالة بالمفتاح الأصلي
        state_file = tmp_path / "phoenix_state.json"
        assert state_file.exists()
        raw = state_file.read_bytes()
        monkeypatch.setattr(rw, "SOVEREIGN_KEY", "z" * 128)
        with _pytest.raises(RuntimeError, match="R-682"):
            rw.RansomwareDefense()
        assert state_file.read_bytes() == raw, "الملف محفوظ دون تعديل"

    def test_ash_failure_returns_dead_phase(self, tmp_path, monkeypatch):
        """مفتاح صحيح، لا بذرة قابلة للاستعادة، رماد موجود → فشل + المرحلة
        DEAD (لا مرحلة انتقالية معلقة) + الرماد محفوظ — بلا سجل نجاح."""
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        obj = rw.RansomwareDefense()
        ash = MagicMock()
        obj.ashes["ash_e2e"] = ash
        obj.phoenix_phase = rw.PhoenixPhase.DEAD
        key = obj.get_resurrection_key()
        result = obj.resurrect(key)
        assert result.get("success") is False, \
            "لا نجاح معلن لاستعادة رماد غير منفذة"
        assert obj.phoenix_phase == rw.PhoenixPhase.DEAD, \
            "الفشل يجب أن يعيد النظام إلى DEAD — لا مرحلة RESURRECTING معلقة"
        assert "ash_e2e" in obj.ashes, "الرماد محفوظ — لا مسح"
        assert obj.last_resurrection is None or obj.last_resurrection.success is False, \
            "لا سجل قيامة ناجح لعملية فاشلة"

    def test_save_failure_before_replace_preserves_file_no_seed(self, tmp_path, monkeypatch):
        """فشل الحفظ قبل الاستبدال: الملف السابق يبقى بايت-مطابقًا، ولا يُعلن
        نجاح إنشاء بذرة (create_phoenix_seed يرفض)."""
        import os as _os
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        obj = rw.RansomwareDefense()
        state_file = tmp_path / "phoenix_state.json"
        raw = state_file.read_bytes()
        def _boom(src, dst):
            raise OSError("replace exploded (injected)")
        monkeypatch.setattr(_os, "replace", _boom)
        assert obj._save_state() is False, "فشل الحفظ يجب أن يُعاد False"
        assert state_file.read_bytes() == raw, \
            "الملف السابق بايت-مطابق — الفشل قبل الاستبدال يتركه كما هو"
        seed = obj.create_phoenix_seed(reason="save-failure-test")
        assert seed is None, "لا يُعلن نجاح بذرة دون حفظ متين للحالة"

    def test_store_tamper_detected_on_reopen(self, tmp_path, monkeypatch, caplog):
        """تلاعب موضعي في نص حمولة مخزنة (يُبقي JSON صالحًا) ثم إعادة فتح
        المخزن وقراءته: يجب ألا تُقبل القيمة المعدلة صامتًا — إما كشف
        التلاعب (فشل مصادقة/بصمة) أو رفض العنصر، لا قبول صامت."""
        import json as _json
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        import backend.memory.store as store_mod
        concept = "tamper_proof_concept"
        definition = "قيمة 5 الأصلية للإثبات"
        store1 = self._make_real_store(tmp_path / "store_t", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store1)
        store1.save_semantic(
            concept=concept,
            definition=definition,
            aliases=["alias1"],
            related_concepts={},
            examples=["example1"],
            confidence=0.95,
        )
        sem_file = store_mod.FILE_MAP["semantic"]
        assert sem_file.exists()
        items_data = _json.loads(sem_file.read_text(encoding="utf-8"))
        assert items_data, "العنصر مخزَّن على القرص"
        item = items_data[0]
        enc_str = item["encrypted_payload"]
        # قراءة الأصل قبل التعديل — يثبت أن السجل كان يُقرأ سليمًا
        store_pre = self._make_real_store(tmp_path / "store_t", monkeypatch)
        pre = [r for r in store_pre.query("semantic", min_importance=0.7)
               if r.get("concept") == concept]
        assert pre, "السجل الأصلي يجب أن يُقرأ سليمًا قبل التلاعب"
        assert pre[0].get("definition") == "قيمة 5 الأصلية للإثبات"
        # تلاعب موضعي مقصود: قلب بايت النص المشفر المقابل لموضع '5' في
        # النص الصريح المعروف — يغيّرها إلى '6' مع بقاء JSON صالحًا تمامًا
        # (التشفير الطبقي XOR موضعي؛ لولا المصادقة لَقُبلت القيمة المعدلة)
        envelope = _json.loads(enc_str)
        payload_dict = {
            "concept": concept,
            "definition": definition,
            "aliases": ["alias1"],
            "confidence": 0.95,
            "related_concepts": {},
            "examples": ["example1"],
            "counter_examples": [],
        }
        plaintext = _json.dumps(payload_dict, ensure_ascii=False).encode()
        idx = plaintext.find("قيمة 5".encode())
        assert idx >= 0
        pos = idx + len("قيمة ".encode())  # موضع بايت '5'
        # الصيغة الحالية مظروف v1 (AES-GCM): "d" = base64(ciphertext)
        import base64 as _b64
        ct = bytearray(_b64.b64decode(envelope["d"], validate=True))
        assert len(ct) == len(plaintext), "GCM (CTR داخليًا) موضعي: نفس الطول"
        # قلب بايت النص المشفر المقابل لموضع '5': يغيّر '5'→'6' في النص
        # الصريح مع بقاء JSON صالحًا — لولا وسم GCM لَقُبلت القيمة المعدلة
        ct[pos] ^= ord("5") ^ ord("6")
        envelope["d"] = _b64.b64encode(bytes(ct)).decode()
        item["encrypted_payload"] = _json.dumps(envelope)
        sem_file.write_text(_json.dumps(items_data), encoding="utf-8")
        # إعادة فتح المخزن من القرص بعد التلاعب ثم القراءة المعتادة
        store2 = self._make_real_store(tmp_path / "store_t", monkeypatch)
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.store"):
            results = store2.query("semantic", min_importance=0.7)
        # 1) السجل المعدل مرفوض — لا يُعاد كبيانات سليمة
        accepted = [r for r in results
                    if r.get("concept") == concept and not r.get("_error")]
        assert not accepted, \
            "الحمولة المعدلة قُبلت صامتة — لا مصادقة في تخزين المخزن"
        # 2) رفضه مُسجَّل كفشل مصادقة صريح
        matches = [r for r in caplog.records
                   if "GCM authentication FAILED" in r.getMessage()]
        assert matches, "الرفض يجب أن يُسجَّل كفشل مصادقة GCM صريح"
        # 3) سجله المشفر يبقى على القرص (دليل — لا حذف)
        items_after = _json.loads(sem_file.read_text(encoding="utf-8"))
        assert any(i.get("id") == item.get("id") for i in items_after), \
            "السجل المشفر المعدل يبقى على القرص — دليل، لا حذف"

    def test_fingerprint_gate_fail_closed(self, tmp_path, monkeypatch, caplog):
        """بوابة البصمة لا تفشل مفتوحة: تعذر حساب البصمة أو غياب البصمة
        المحفوظة = رفض السجل مع تسجيل السبب — لا إرجاعه دون تحقق."""
        import backend.memory.store as store_mod
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        store1 = self._make_real_store(tmp_path / "store_fp", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store1)
        store1.save_semantic(
            concept="fp_gate_proof", definition="دليل بوابة البصمة", confidence=0.9,
        )
        # 1) حقن فشل حساب البصمة عند القراءة
        def _boom(data):
            raise RuntimeError("fingerprint computation exploded (injected)")
        monkeypatch.setattr(store1.encoder, "fingerprint", _boom)
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.store"):
            results = store1.query("semantic", min_importance=0.7)
        assert not [r for r in results if r.get("concept") == "fp_gate_proof"], \
            "تعذر حساب البصمة = رفض السجل — لا فشل مفتوح"
        matches = [r for r in caplog.records if "fingerprint" in r.getMessage().lower()]
        assert matches, "سبب الرفض (تعذر البصمة) يجب أن يُسجَّل صراحة"
        # 2) غياب البصمة المحفوظة (عنصر بلا بصمة) = رفض بالسياسة نفسها
        for item in store1._data.get("semantic", {}).values():
            item.fingerprint = None
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.store"):
            results2 = store1.query("semantic", min_importance=0.7)
        assert not [r for r in results2 if r.get("concept") == "fp_gate_proof"], \
            "غياب البصمة المحفوظة = رفض السجل — لا فشل مفتوح"

    def test_restoration_preserves_all_payload_fields(self, tmp_path, monkeypatch):
        """الاستعادة تحفظ كل حقول الحمولة المقصودة — لا يُحتسب العنصر
        مستعادًا كاملًا إذا أُسقطت بعض حمولته (aliases/related/examples/
        confidence + محفزات/تسلسل/معاملات الإجرائية)."""
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        import backend.memory.store as store_mod
        concept = "full_fields_proof"
        store1 = self._make_real_store(tmp_path / "store_f", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store1)
        store1.save_semantic(
            concept=concept,
            definition="تعريف كامل الحقول",
            aliases=["alias_a", "alias_b"],
            related_concepts={"related_x": 0.7},
            examples=["example_1", "example_2"],
            confidence=0.88,
        )
        store1.save_procedural(
            name="full_fields_skill",
            description="مهارة كاملة الحقول",
            trigger_patterns=["trigger_a", "trigger_b"],
            action_sequence=["step_1", "step_2", "step_3"],
            parameters={"param_x": 42},
            importance=0.9,
        )
        first = rw.RansomwareDefense()
        seed = first.create_phoenix_seed(reason="full-fields")
        assert seed is not None
        key = first.get_resurrection_key()
        # الفقدان: مخزن فارغ جديد
        store2 = self._make_real_store(tmp_path / "store_g", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store2)
        restarted = rw.RansomwareDefense()
        restarted.phoenix_phase = rw.PhoenixPhase.DEAD
        result = restarted.resurrect(key)
        assert result.get("success") is True, f"القيامة يجب أن تنجح: {result}"
        # إعادة فتح المخزن من القرص ثم مقارنة كل الحقول المقصودة
        store3 = self._make_real_store(tmp_path / "store_g", monkeypatch)
        sem = [i for i in store3.query("semantic", min_importance=0.7)
               if i.get("concept") == concept]
        assert sem, "السجل الدلالي عاد"
        it = sem[0]
        assert it.get("definition") == "تعريف كامل الحقول"
        assert it.get("aliases") == ["alias_a", "alias_b"], \
            "الأسماء البديلة يجب أن تُستعاد — لا إسقاط حمولة"
        assert it.get("related_concepts") == {"related_x": 0.7}, \
            "العلاقات يجب أن تُستعاد — لا إسقاط حمولة"
        assert it.get("examples") == ["example_1", "example_2"], \
            "الأمثلة يجب أن تُستعاد — لا إسقاط حمولة"
        assert it.get("confidence") == 0.88, "الثقة يجب أن تُستعاد"
        proc = [i for i in store3.query("procedural", min_importance=0.7)
                if i.get("name") == "full_fields_skill"]
        assert proc, "المهارة الإجرائية عادت"
        pr = proc[0]
        assert pr.get("description") == "مهارة كاملة الحقول"
        assert pr.get("trigger_patterns") == ["trigger_a", "trigger_b"], \
            "المحفزات يجب أن تُستعاد — لا إسقاط حمولة"
        assert pr.get("action_sequence") == ["step_1", "step_2", "step_3"], \
            "تسلسل الإجراءات يجب أن يُستعاد — لا إسقاط حمولة"
        assert pr.get("parameters") == {"param_x": 42}, \
            "المعاملات يجب أن تُستعاد — لا إسقاط حمولة"

    def test_new_encoder_instance_key_continuity(self, tmp_path, monkeypatch):
        """استمرارية اشتقاق المفتاح: بيانات كتبها مشفّر تُفك بمشفّر جديد
        تمامًا (ليس المفرد الوحيد) — المشتق حتمي من مفتاح السيادة."""
        import backend.memory.store as store_mod
        from backend.memory.encoding import SovereignEncoder
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        store1 = self._make_real_store(tmp_path / "store_k", monkeypatch)
        monkeypatch.setattr(store_mod, "get_store", lambda: store1)
        store1.save_semantic(
            concept="key_continuity_proof", definition="دليل استمرارية المشتق",
            confidence=0.95,
        )
        # مشفّر جديد كليًا (ليس get_encoder المفرد) — يُمرر للمساعد مباشرة
        fresh_encoder = SovereignEncoder()
        store2 = self._make_real_store(
            tmp_path / "store_k", monkeypatch, encoder=fresh_encoder
        )
        # التوكيدات المطلوبة: المخزن الثاني يستخدم المشفر الجديد فعلًا
        assert store2.encoder is fresh_encoder, \
            "المخزن الثاني يجب أن يستخدم المشفر الجديد — لا المفرد"
        assert store2.encoder is not store1.encoder, \
            "المشفران مختلفان فعلًا — وإلا فالاختبار لا يثبت الاستمرارية"
        restored = [i for i in store2.query("semantic", min_importance=0.7)
                    if i.get("concept") == "key_continuity_proof"]
        assert restored, \
            "مشفّر جديد كليًا يجب أن يفك بيانات القديم — المشتق حتمي من مفتاح السيادة"
        assert restored[0].get("definition") == "دليل استمرارية المشتق"

    def test_mixed_seed_no_full_success(self, tmp_path, monkeypatch):
        """بذرة مختلطة (عنصر قابل للاستعادة + آخر غير قابل) → لا يُعلن
        استعادة كاملة/REBORN — نتيجة فاشلة أو جزئية صريحة فقط."""
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        obj = rw.RansomwareDefense.__new__(rw.RansomwareDefense)
        obj.core = self._mock_core()
        obj.seeds = {}
        obj.ashes = {}
        obj.restored_seeds = {}
        obj.master_resurrection_key = "d" * 128
        from backend.memory.defense.ransomware import PhoenixSeed
        seed = PhoenixSeed(
            id="phoenix_seed_mixed_001",
            created_at=1000000.0,
            core_fingerprint="deadbeef1234",
            essential_memory={"core": {"last_hash": "x"}, "critical_memory": [
                {"type": "semantic", "concept": "valid_one",
                 "definition": "قابل للاستعادة", "aliases": [],
                 "related_concepts": {}, "confidence": 0.9, "importance": 0.9},
                {"type": "unknown_type", "name": "unsupported"},
            ]},
            resurrection_key="beef" * 16,
            expires_at=1000000.0 + 604800,
            phase="living",
        )
        assert obj._restore_from_seed(seed) is False, \
            "عنصر واحد غير قابل للاستعادة يمنع إعلان استعادة كاملة"

    def test_procedural_missing_payload_not_counted(self, tmp_path, monkeypatch):
        """عنصر إجرائي باسم فقط (بلا وصف/تسلسل إجراءات) لا يُحتسب مستعادًا —
        إنشاء سجل فارغ ليس استعادة للمهارة المقصودة."""
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        obj = rw.RansomwareDefense.__new__(rw.RansomwareDefense)
        obj.core = self._mock_core()
        obj.seeds = {}
        obj.ashes = {}
        obj.restored_seeds = {}
        obj.master_resurrection_key = "e" * 128
        from backend.memory.defense.ransomware import PhoenixSeed
        seed = PhoenixSeed(
            id="phoenix_seed_proc_001",
            created_at=1000000.0,
            core_fingerprint="deadbeef1234",
            essential_memory={"core": {"last_hash": "x"}, "critical_memory": [
                {"type": "procedural", "name": "broken_skill",
                 "description": "", "trigger_patterns": [],
                 "action_sequence": [], "parameters": {}, "importance": 0.9},
            ]},
            resurrection_key="beef" * 16,
            expires_at=1000000.0 + 604800,
            phase="living",
        )
        assert obj._restore_from_seed(seed) is False, \
            "مهارة ناقصة الحمولة لا تُحتسب مستعادة — لا نجاح لعملية لم تحدث"

    def test_dir_fsync_failure_after_replace(self, tmp_path, monkeypatch, caplog):
        """فشل مزامنة المجلد بعد نجاح الاستبدال: فشل معلن + توثيق أن الملف
        استُبدل لكن متانته لم تُؤكد (لا ادعاء أن الملف السابق بقي) + لا بذرة."""
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        obj = rw.RansomwareDefense()
        state_file = tmp_path / "phoenix_state.json"
        assert state_file.exists()
        import os as _os
        import stat as _stat
        real_fsync = _os.fsync
        def _dir_only_flaky(fd):
            # يفشل فقط على واصف المجلد (مزامنة المجلد) — ملف الحالة يُزامن طبيعيًا
            st = _os.fstat(fd)
            if _stat.S_ISDIR(st.st_mode):
                raise OSError("dir fsync exploded (injected)")
            return real_fsync(fd)
        monkeypatch.setattr(_os, "fsync", _dir_only_flaky)
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            ok = obj._save_state()
        assert ok is False, "فشل تأكيد المتانة = فشل معلن"
        matches = [r for r in caplog.records
                   if "REPLACED" in r.getMessage()
                   and "durability" in r.getMessage().lower()]
        assert matches, \
            "يجب توثيق أن الملف استُبدل لكن متانته لم تُؤكد — لا ادعاء تراجع لم يحدث"
        # الملف استُبدل فعلًا (المحتوى الجديد موجود) — ولا يُدّعى أنه كما كان
        assert state_file.exists()
        content_before_seed = state_file.read_text(encoding="utf-8")
        # إنشاء البذرة يفشل عند مزامنة المجلد تحديدًا (لا عند مزامنة الملف)
        seed = obj.create_phoenix_seed(reason="dir-fsync-failure")
        assert seed is None, "لا بذرة معلنة دون حفظ متين مؤكد"
        assert state_file.read_text(encoding="utf-8") != content_before_seed, \
            "محاولة البذرة وصلت لمرحلة الاستبدال فعلًا — الفشل عند تأكيد المتانة"

    def test_reset_preserve_seeds_keeps_master_key(self, tmp_path, monkeypatch):
        """reset(preserve_seeds=True) يجب ألا يولّد مفتاحًا جديدًا — توليده
        يجعل كل بذور محفوظة غير قابلة للفك نهائيًا."""
        store = _IsolatedStore()
        rw = self._patch_env(tmp_path, monkeypatch, store)
        first = rw.RansomwareDefense()
        seed = first.create_phoenix_seed(reason="reset-preserve-test")
        assert seed is not None
        old_master = first.master_resurrection_key
        first.reset(preserve_seeds=True)
        assert first.master_resurrection_key == old_master, \
            "الاحتفاظ بالبذور يستلزم الاحتفاظ بالمفتاح الرئيسي"
        # والبذرة ما زالت قابلة للفك بعد إعادة تشغيل (تهيئة حقيقية)
        restarted = rw.RansomwareDefense()
        found = restarted._find_latest_seed()
        assert found is not None, "البذرة المحفوظة يجب أن تبقى قابلة للفك"
        assert found.id == seed.id


# ============================================================
# Part 1c: دورة الرماد — موت/قيامة حقيقية قابلة للإثبات (R-682 بناء)
# ============================================================

class TestAshResurrection:
    """R-682 (بناء): تنفيذ استعادة الرماد فعليًا. الفحصة كشفت أن المسار كله
    كان كودًا ميتًا: `self.core.store_blob/load_blob` غير موجودين في SovereignCore
    (الواجهة الفعلية blob_store.put/get) → كل استدعاء فشل صامتًا بلا رماد أبدًا،
    و`_encrypt_store_item` كعب كاذب يعيد True بلا تشفير."""

    def _mock_core_with_blobs(self, tmp_path, events=None):
        from backend.memory.core import BlobStore
        blob_dir = tmp_path / "blobs"
        blob_dir.mkdir(exist_ok=True)
        core = MagicMock()
        core._last_hash = "a" * 64
        core.get_statistics.return_value = {"index": {"total_events": 3}}
        core.blob_store = BlobStore(blob_dir)  # مخزن حقيقي (محتوى-عنواني)
        core.iterate_events = lambda limit=1000, **k: (events or [])
        return core

    def _setup(self, tmp_path, monkeypatch, events=None):
        store = _IsolatedStore()
        iso = _IsolatedStore()
        iso.save_semantic(concept="ash_cycle_record", definition="سجل دورة الرماد",
                          confidence=0.9)
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        core = self._mock_core_with_blobs(tmp_path, events)
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        monkeypatch.setattr(store_mod, "get_store", lambda: iso)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)
        return rw, core

    def test_death_and_ash_resurrection_cycle(self, tmp_path, monkeypatch):
        """دورة كاملة قابلة للإثبات: بيانات → موت (رماد مشفر موثق) → فقدان
        الأصل → قيامة من الرماد → البيانات عادت بنفس البصمة والمحتوى
        (المخزن محتوى-عنواني: نفس البصمة = نفس البيانات)."""
        # (الإعداد أدناه يدويًا لأحدّث الأحداث بعد تخزين الأصل)
        store = _IsolatedStore()
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        core = self._mock_core_with_blobs(tmp_path)
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        iso = _IsolatedStore()
        monkeypatch.setattr(store_mod, "get_store", lambda: iso)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)

        # 1) بيانات أصلية في مخزن النواة (محتوى-عنواني)
        original = b"sovereign_r682_ash_proof_data_" * 8
        original_hash = core.blob_store.put(original, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": original_hash}]

        # 2) الموت → رماد مشفر موثق
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="ash-cycle-test") is True
        assert obj.phoenix_phase == rw.PhoenixPhase.DEAD
        assert len(obj.ashes) >= 1, \
            "الموت يجب أن يُنشئ رمادًا فعليًا (المسار القديم كان كودًا ميتًا)"
        ash = next(iter(obj.ashes.values()))
        assert ash.original_id == original_hash
        # مظروف GCM موثق (لا XOR) — الرماد بلا مصادقة يُرفض عند الاستعادة
        assert ash.ash_data.startswith(b"ASHV2"), \
            "الرماد يجب أن يكون مظروف AES-GCM موثقًا"
        # النسخة المشفرة مختلفة عن الأصل
        assert ash.ash_data != original

        # 3) فقدان الأصل + إزالة البذور (إجبار مسار الرماد)
        core.blob_store.delete(original_hash)
        assert not core.blob_store.exists(original_hash), "الأصل فُقد فعلًا"
        for f in seeds_dir.glob("*.enc"):
            f.unlink()
        obj.seeds.clear()

        # 4) القيامة من الرماد عبر الواجهة العامة
        key = obj.get_resurrection_key()
        result = obj.resurrect(key)
        assert result.get("success") is True, f"القيامة من الرماد يجب أن تنجح: {result}"

        # 5) الإثبات: البيانات عادت بنفس البصمة والمحتوى
        assert core.blob_store.exists(original_hash), \
            "البصمة الأصلية يجب أن تعود — البيانات استُعيدت فعليًا"
        assert core.blob_store.get(original_hash) == original, \
            "المحتوى المستعاد يجب أن يطابق الأصل تمامًا"

    def test_ash_tamper_rejected(self, tmp_path, monkeypatch, caplog):
        """تلاعب في بيانات الرماد → رفض بفشل MAC — لا استعادة غير موثقة."""
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        core = self._mock_core_with_blobs(tmp_path)
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        iso = _IsolatedStore()
        monkeypatch.setattr(store_mod, "get_store", lambda: iso)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)

        original = b"tamper_proof_ash_data_" * 6
        original_hash = core.blob_store.put(original, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": original_hash}]
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="ash-tamper-test") is True
        ash_id, ash = next(iter(obj.ashes.items()))
        # تلاعب: قلب بايت في بيانات الرماد (الوسم يبقى — هذا هو التلاعب)
        tampered = bytearray(ash.ash_data)
        tampered[20] ^= 0xFF  # داخل النص المشفر — يفشل وسم GCM
        ash.ash_data = bytes(tampered)
        core.blob_store.delete(original_hash)
        for f in seeds_dir.glob("*.enc"):
            f.unlink()
        obj.seeds.clear()
        key = obj.get_resurrection_key()
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj.resurrect(key)
        assert result.get("success") is False, \
            "الرماد المُلاعب به يجب ألا يُستعاد — فشل مصادقة GCM"
        matches = [r for r in caplog.records if "GCM authentication FAILED" in r.getMessage()]
        assert matches, "رفض التلاعب يجب أن يُسجَّل كفشل مصادقة GCM صريح"
        assert ash_id in obj.ashes, "الرماد المرفوض يبقى محفوظًا (لا مسح)"

    def test_encrypt_store_item_honest(self, tmp_path, monkeypatch, caplog):
        """الكعب القديم كان يعيد True بلا تشفير (كذب في العد). الآن: يعيد False
        صراحة مع تسجيل أن المسار غير منفذ — لا يُحتسب تشفير لم يحدث."""
        import backend.memory.defense.ransomware as rw
        obj = rw.RansomwareDefense.__new__(rw.RansomwareDefense)
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="backend.memory.defense.ransomware"):
            result = obj._encrypt_store_item("semantic", "item_x")
        assert result is False, \
            "غير المنفذ يعيد False — لا يُعلن تشفير لم يحدث أبدًا"
        matches = [r for r in caplog.records if "NOT IMPLEMENTED" in r.getMessage()]
        assert matches, "عدم التنفيذ يُسجَّل صراحة (لا صمت ولا كذب)"


# ============================================================
# Part 1d: جولة 8 — لا نجاح لاستعادة ناقصة + إثبات بالقراءة المستقلة
# ============================================================

class TestAshResurrectionStrict:
    """R-682 (جولة 8 — اعتراض advisor الرابع على بناء الرماد):
    1) استعادة جزئية (رماد صالح + تالف) = لا success ولا REBORN — بلا بذرة ومع بذرة.
    2) إثبات التخزين بالقراءة المستقلة: ملف تالف قائم تحت بصمة صحيحة يُكشف
       ويُصلح (حذف + إعادة تخزين + تحقق قراءة) — لا نجاح شكلي.
    3) المصادقة تُختبر بعد إثبات الحالة السليمة، مع إثبات عدم استدعاء
       التخزين عند فشل المصادقة.
    4) مسار حقيقي كامل مع SovereignCore فعلية (لا واجهة مفترضة)."""

    def _env(self, tmp_path, monkeypatch, events=None):
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        from backend.memory.core import BlobStore
        blob_dir = tmp_path / "blobs"
        blob_dir.mkdir(exist_ok=True)
        core = MagicMock()
        core._last_hash = "a" * 64
        core.get_statistics.return_value = {"index": {"total_events": 3}}
        core.blob_store = BlobStore(blob_dir)
        core.iterate_events = lambda limit=1000, **k: (events or [])
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        iso = _IsolatedStore()
        iso.save_semantic(concept="ash_strict_record", definition="سجل",
                          confidence=0.9)
        monkeypatch.setattr(store_mod, "get_store", lambda: iso)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)
        return rw, core, iso

    def _two_blobs(self, core):
        h1 = core.blob_store.put(b"valid_blob_payload_" * 6, compress=True)
        h2 = core.blob_store.put(b"doomed_blob_payload_" * 6, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h1}, {"blob": h2}]
        return h1, h2

    def test_partial_ash_restoration_no_reborn(self, tmp_path, monkeypatch):
        """رماد صالح + رماد مُلاعب، بلا بذرة: المستعاد يُحصى لكن لا نجاح
        ولا REBORN — والفاشل يبقى محفوظًا."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        iso.items.clear()  # مخزن فارغ — جاهزية الاسترداد ممكنة
        h1, h2 = self._two_blobs(core)
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="partial-test") is True
        assert len(obj.ashes) == 2
        # تلاعب في رماد واحد فقط
        for ash in obj.ashes.values():
            if ash.original_id == h2:
                tampered = bytearray(ash.ash_data)
                tampered[-3] ^= 0xFF  # داخل الوسم
                ash.ash_data = bytes(tampered)
        for f in (tmp_path / "seeds").glob("*.enc"):
            f.unlink()
        obj.seeds.clear()
        result = obj.resurrect(obj.get_resurrection_key())
        assert result.get("success") is False, \
            f"استعادة ناقصة يجب ألا تنجح: {result}"
        assert result.get("partial") is True
        assert result.get("ashes_restored") == 1
        assert result.get("ashes_failed") == 1
        assert obj.phoenix_phase == rw.PhoenixPhase.DEAD, \
            "لا REBORN لاستعادة ناقصة"
        # الفاشل محفوظ — الصالح استُهلك فعلًا
        assert len(obj.ashes) == 1
        assert next(iter(obj.ashes.values())).original_id == h2

    def test_seed_path_partial_ash_no_reborn(self, tmp_path, monkeypatch):
        """بذرة سليمة + رماد مختلط: البذرة تستعاد لكن فك الرماد ناقص —
        لا REBORN، والنتيجة تعكس الجزئية، والفاشل محفوظ."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        h1, h2 = self._two_blobs(core)
        obj = rw.RansomwareDefense()
        # بذرة مسبقة بمحتوى (المخزن فيه سجل الآن)
        pre_seed = obj.create_phoenix_seed(reason="pre-death")
        assert pre_seed is not None
        pre_created = pre_seed.created_at
        iso.items.clear()  # مخزن فارغ — الموت ينجح والبذرة النهائية فارغة
        assert obj.initiate_death(reason="seed-partial-test") is True
        assert len(obj.ashes) == 2
        # إزالة بذرة الموت الفارغة (الأحدث) — تبقى البذرة المسبقة بالمحتوى
        for sid in list(obj.seeds):
            if obj.seeds[sid].created_at > pre_created:
                obj.seeds.pop(sid)
                seed_file = (tmp_path / "seeds") / f"{sid}.enc"
                if seed_file.exists():
                    seed_file.unlink()
        for ash in obj.ashes.values():
            if ash.original_id == h2:
                tampered = bytearray(ash.ash_data)
                tampered[-3] ^= 0xFF
                ash.ash_data = bytes(tampered)
        # البذرة تبقى (المسار الطبيعي: بذرة + رماد)
        result = obj.resurrect(obj.get_resurrection_key())
        assert result.get("success") is False, \
            f"مسار البذرة مع رماد ناقص يجب ألا ينجح: {result}"
        assert result.get("partial") is True
        assert result.get("seed_restored") is True
        assert result.get("ashes_failed") == 1
        assert obj.phoenix_phase == rw.PhoenixPhase.DEAD, \
            "لا REBORN لاستعادة ناقصة حتى مع بذرة سليمة"
        assert len(obj.ashes) == 1  # الفاشل محفوظ

    def test_ash_restore_corrupted_existing_blob(self, tmp_path, monkeypatch):
        """ملف تالف قائم تحت البصمة الصحيحة: put يتجاوز الكتابة فيعيد
        البصمة المتوقعة — النجاح الشكلي مرفوض. الإثبات بالقراءة المستقلة:
        يُكشف التلف ويُصلح (حذف + إعادة تخزين + تحقق) والمحتوى يعود سليمًا."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        iso.items.clear()
        original = b"corrupt_path_proof_payload_" * 7
        h = core.blob_store.put(original, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="corrupt-test") is True
        assert len(obj.ashes) == 1
        # تلف الملف القائم (يبقى المسار موجودًا — put سيتجاوز الكتابة)
        blob_file = core.blob_store._blob_path(h)
        blob_file.write_bytes(b"CORRUPTED_GARBAGE_NOT_THE_BLOB")
        for f in (tmp_path / "seeds").glob("*.enc"):
            f.unlink()
        obj.seeds.clear()
        result = obj.resurrect(obj.get_resurrection_key())
        assert result.get("success") is True, \
            f"الإصلاح بعد كشف التلف يجب أن ينجح: {result}"
        # الإثبات الفعلي: المحتوى المقروء من القرص سليم — لا نجاح شكلي
        assert core.blob_store.get(h) == original, \
            "الملف التالف يجب أن يُصلح فعلًا — قراءة مستقلة مطابقة"
        assert core.blob_store.verify_content_hash(h)
        assert len(obj.ashes) == 0  # استُهلك الرماد بعد إثبات فعلي

    def test_tamper_rejected_without_storage(self, tmp_path, monkeypatch):
        """إثبات بوابة المصادقة: الحالة السليمة تستعاد (تخزين يُستدعى)،
        ثم التلاعب يُرفض قبل أي تخزين (لا استدعاء put للرماد المرفوض)."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        iso.items.clear()
        h = core.blob_store.put(b"auth_gate_proof_" * 8, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="auth-test") is True
        ash_id, ash = next(iter(obj.ashes.items()))

        # 1) الحالة السليمة (ضابط): الاستعادة تعمل والتخزين يُستدعى
        calls_before = {"n": 0}
        real_put = core.blob_store.put
        def counting_put(data, compress=True):
            calls_before["n"] += 1
            return real_put(data, compress=compress)
        core.blob_store.put = counting_put
        for f in (tmp_path / "seeds").glob("*.enc"):
            f.unlink()
        obj.seeds.clear()
        ok = obj.resurrect(obj.get_resurrection_key())
        assert ok.get("success") is True, f"الضابط: الرماد السليم يستعاد: {ok}"
        assert calls_before["n"] >= 1, "الضابط: التخزين يجب أن يُستدعى للحالة السليمة"

        # 2) التلاعب: رفض قبل أي تخزين (العداد لا يزيد بعد الرفض)
        obj2 = rw.RansomwareDefense()
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        assert obj2.initiate_death(reason="auth-test-2") is True
        ash2 = next(iter(obj2.ashes.values()))
        tampered = bytearray(ash2.ash_data)
        tampered[-3] ^= 0xFF
        ash2.ash_data = bytes(tampered)
        for f in (tmp_path / "seeds").glob("*.enc"):
            f.unlink()
        obj2.seeds.clear()
        core.blob_store.delete(h)  # الأصل غير موجود — أي put لاحق لافت
        calls_after = {"n": 0}
        def strict_put(data, compress=True):
            calls_after["n"] += 1
            return real_put(data, compress=compress)
        core.blob_store.put = strict_put
        result = obj2.resurrect(obj2.get_resurrection_key())
        assert result.get("success") is False
        assert calls_after["n"] == 0, \
            "الرماد المرفوض مصادقةً لا يجب أن يصل إلى التخزين أصلًا"
        assert len(obj2.ashes) == 1  # محفوظ

    def test_death_resurrection_real_core(self, tmp_path, monkeypatch):
        """مسار حقيقي كامل مع SovereignCore فعلية — لا واجهة مفترضة:
        الأحداث الحقيقية تحمل blobs فعلية، والموت يشفّرها، والقيامة من
        الرماد تعيدها بنفس المحتوى."""
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        from backend.memory.core import SovereignCore

        core_dir = tmp_path / "core"
        core_dir.mkdir()
        (core_dir / "blobs").mkdir()
        core = SovereignCore(
            log_file=core_dir / "ledger.jsonl",
            blobs_dir=core_dir / "blobs",
            index_file=core_dir / "index.json",
            meta_file=core_dir / "meta.json",
            integrity_file=core_dir / "integrity.json",
        )
        assert core._keyring is not None, "بيئة الاختبار توفر KeyRing نشطًا"

        # حدثان حقيقيان → payload blobs حقيقية
        core.append_event("phoenix::ash_test_1", {"data": "first_real_payload"}, user="test")
        core.append_event("phoenix::ash_test_2", {"data": "second_real_payload"}, user="test")
        event_blobs = [e["blob"] for e in core.iterate_events(limit=100)]
        assert len(event_blobs) == 2, "الأحداث الحقيقية تحمل blobs فعلية"

        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        iso = _IsolatedStore()
        monkeypatch.setattr(store_mod, "get_store", lambda: iso)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)

        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="real-core-test") is True
        # فصل الحماية عن الاسترداد: جاهزية نعم (نسخ كاملة بلا فشل) —
        # لكن الحماية ليست مكتملة والأصل مقروء
        assert obj.last_death_protection["recovery_ready"] is True
        assert obj.last_death_protection["assets_hidden"] is False
        assert obj.last_death_protection["protection_complete"] is False
        # 3 blobs: حدثا الاختبار + حدث بذرة الفينيق (يُنشأ قبل التشفير)
        assert obj.last_death_protection["blobs_encrypted"] == 3
        assert obj.last_death_protection["blob_failures"] == 0
        assert len(obj.ashes) == 3, "الرماد نشأ من الأحداث الحقيقية فعلًا"

        # فقدان الأصول + إزالة البذور → مسار الرماد
        original_contents = {h: core.blob_store.get(h) for h in event_blobs}
        for h in event_blobs:
            core.blob_store.delete(h)
        for f in seeds_dir.glob("*.enc"):
            f.unlink()
        obj.seeds.clear()

        result = obj.resurrect(obj.get_resurrection_key())
        assert result.get("success") is True, f"القيامة من رماد حقيقي: {result}"
        # الإثبات: كل blob عاد بنفس المحتوى الحرفي
        for h in event_blobs:
            assert core.blob_store.exists(h), f"البصمة {h[:12]}... يجب أن تعود"
            assert core.blob_store.get(h) == original_contents[h], \
                "المحتوى المستعاد يجب أن يطابق الأصل حرفيًا"

    def test_initiate_death_honest_protection_reporting(self, tmp_path, monkeypatch):
        """الحدث نفسه يحمل الأعداد الصادقة: لا ادعاء encrypted_items كامل،
        بل blobs_encrypted + store_items_unprotected + protection_complete."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        h = core.blob_store.put(b"honest_reporting_" * 5, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        obj = rw.RansomwareDefense()
        # عنصر مخزن غير محمي → الموت نفسه يفشل والحدث death_failed
        assert obj.initiate_death(reason="honest-test") is False
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        failed_calls = [c for c in core.append_event.call_args_list
                        if c.kwargs.get("event_type") == "phoenix::death_failed"]
        assert failed_calls, "حدث فشل الموت يجب أن يُسجل"
        payload = failed_calls[0].kwargs["payload"]
        assert payload["blobs_encrypted"] == 1
        assert payload["store_items_unprotected"] >= 1, \
            "عنصر المخزن غير المحمي يُعلن صراحة لا يُخفى"
        assert payload["recovery_ready"] is False
        assert payload["protection_complete"] is False, \
            "لا ادعاء حماية كاملة والمسار ناقص"
        # والسجل نفسه متسق مع الفشل
        assert obj.last_death_record.success is False


# ============================================================
# Part 1e: جولة 9 — صدق حماية الموت منفصل عن جاهزية الاسترداد
# ============================================================

class _BigStore:
    """مخزن يعيد 500 عنصرًا — لإثبات كشف الاقتطاع (حد الاستعلام)."""
    def query(self, kind, tag=None, min_importance=0.0, limit=50,
              search_text=None):
        return [{"_id": f"{kind}_{i}"} for i in range(500)][:limit]


class TestDeathProtectionHonesty:
    """R-682 (جولة 9 — اعتراض advisor الخامس على بناء الرماد):
    فصل نجاح إنشاء نسخ استرداد مشفرة عن نجاح حماية الأصول:
    - فشل تشفير كل العناصر لا يُعلن حماية مكتملة.
    - فشل استعلام المخزن يُصرَّح به لا يُبتلع.
    - حدود الفحص (1000 حدث / 500 عنصر) تُعلن اقتطاعًا — ما لم يُفحص لا يُفترض محميًا.
    - إنشاء النسخ المشفرة وحده ليس حماية مكتملة: الأصل يبقى مقروءًا.
    - عدّ العناصر غير المحمية لا يتجاهل عنصرًا بلا معرّف."""

    def _env(self, tmp_path, monkeypatch, events=None):
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        from backend.memory.core import BlobStore
        blob_dir = tmp_path / "blobs"
        blob_dir.mkdir(exist_ok=True)
        core = MagicMock()
        core._last_hash = "a" * 64
        core.get_statistics.return_value = {"index": {"total_events": 3}}
        core.blob_store = BlobStore(blob_dir)
        core.iterate_events = lambda limit=1000, **k: (events or [])
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        iso = _IsolatedStore()
        iso.save_semantic(concept="protection_record", definition="سجل",
                           confidence=0.9)
        monkeypatch.setattr(store_mod, "get_store", lambda: iso)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)
        return rw, core, iso

    def test_death_blob_failures_not_recovery_ready(self, tmp_path, monkeypatch):
        """فشل تشفير كل العناصر: النسخ لم تُنشأ — لا جاهزية استرداد ولا
        حماية مكتملة، والفشل معلن صراحة لا مصفوم."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        iso.items.clear()
        h = core.blob_store.put(b"will_fail_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        # حقن فشل قراءة النواة → فشل إنشاء كل نسخ الاسترداد
        core.blob_store.get = MagicMock(side_effect=RuntimeError("inject: read failed"))
        obj = rw.RansomwareDefense()
        # العقد الكامل: فشل الجاهزية = فشل العملية ذاتها (لا "العملية جرت")
        assert obj.initiate_death(reason="blob-fail-test") is False, \
            "فشل إنشاء نسخ الاسترداد = فشل الموت، لا نجاح"
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING, \
            "النظام لم يمت — العملية فشلت"
        assert obj.is_transforming is False, "لا تحول معلق بعد انتهاء العملية"
        assert obj.last_death_record.success is False, \
            "السجل نفسه يفشل — لا يكذب على النتيجة"
        prot = obj.last_death_protection
        assert prot["blob_failures"] == 1, "فشل الإنشاء يُعدّ صراحة"
        assert prot["blobs_encrypted"] == 0
        assert prot["recovery_ready"] is False, \
            "لا جاهزية استرداد والنسخ لم تُنشأ"
        assert prot["protection_complete"] is False

    def test_death_store_query_failure_not_recovery_ready(self, tmp_path, monkeypatch):
        """فشل استعلام المخزن يُصرَّح به (store_scan_failed) — لا يُعلن
        اكتمال لأن العدّ بقي صفرًا صدفةً."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        iso.items.clear()
        h = core.blob_store.put(b"store_fail_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        import backend.memory.store as store_mod
        broken = MagicMock()
        broken.query.side_effect = RuntimeError("inject: store query failed")
        monkeypatch.setattr(store_mod, "get_store", lambda: broken)
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="store-fail-test") is False, \
            "تعذر فحص المخزن = فشل الموت (لا نجاح بصفر عدّاد)"
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        assert obj.is_transforming is False
        assert obj.last_death_record.success is False
        prot = obj.last_death_protection
        assert prot["store_scan_failed"] is True, \
            "تعذر فحص المخزن يُعلن صراحة لا يُبتلع"
        assert prot["recovery_ready"] is False
        assert prot["protection_complete"] is False

    def test_death_empty_store_copy_not_full_protection(self, tmp_path, monkeypatch):
        """مخزن فارغ + نسخة مشفرة أُنشئت: جاهزية الاسترداد نعم — لكن
        الحماية ليست مكتملة: الأصل يبقى مقروءًا (النسخة استرداد لا إخفاء)."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        iso.items.clear()
        original = b"readable_original_" * 6
        h = core.blob_store.put(original, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        # مخزن فارغ فعلًا (لا عناصر إطلاقًا)
        empty = _IsolatedStore()
        import backend.memory.store as store_mod
        monkeypatch.setattr(store_mod, "get_store", lambda: empty)
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="empty-store-test") is True
        prot = obj.last_death_protection
        assert prot["blobs_encrypted"] == 1
        assert prot["recovery_ready"] is True, "نسخة الاسترداد أُنشئت بلا فشل"
        assert prot["assets_hidden"] is False, \
            "الأصل لم يُخفَ — النسخة المشفرة استرداد لا حماية إخفاء"
        assert prot["protection_complete"] is False, \
            "إنشاء النسخة وحده ليس حماية مكتملة — الأصل ما زال مقروءًا"
        # الأصل مقروء فعلًا (دليل مباشر على عدم الإخفاء)
        assert core.blob_store.get(h) == original

    def test_death_counts_real_store_items(self, tmp_path, monkeypatch):
        """المخزن الحقيقي (SolidMemoryStore): الاستعلام الفعلي يُعاد منه
        عنصر حقيقي واحد — يُعد غير محمي (المسار غير منفذ). لا افتراض
        واجهة؛ وعدّ العناصر لا يتجاهل عنصرًا بلا معرّف."""
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        from backend.memory.core import BlobStore
        blob_dir = tmp_path / "blobs"
        blob_dir.mkdir()
        core = MagicMock()
        core._last_hash = "a" * 64
        core.get_statistics.return_value = {"index": {"total_events": 1}}
        core.blob_store = BlobStore(blob_dir)
        h = core.blob_store.put(b"real_store_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir()
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)
        # المخزن الحقيقي بملفات معزولة
        store_dir = tmp_path / "real_store"
        store_dir.mkdir()
        file_map = {"index": store_dir / "index.json"}
        for kind in store_mod.MemoryKind:
            file_map[kind.value] = store_dir / f"{kind.value}.json"
        monkeypatch.setattr(store_mod, "FILE_MAP", file_map)
        monkeypatch.setattr(store_mod, "get_core", lambda: core)
        from backend.memory.encoding import get_encoder
        monkeypatch.setattr(store_mod, "get_encoder", get_encoder)
        real_store = store_mod.SolidMemoryStore()
        real_store.save_semantic(concept="real_protection_item",
                                 definition="عنصر حقيقي للموت", confidence=0.9)
        monkeypatch.setattr(store_mod, "get_store", lambda: real_store)

        obj = rw.RansomwareDefense()
        # العقد: عنصر حقيقي غير محمي = الموت نفسه يفشل (لا نجاح)
        assert obj.initiate_death(reason="real-store-test") is False, \
            "عنصر مخزن غير محمي = فشل الموت، لا نجاح معلن"
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        assert obj.is_transforming is False
        assert obj.last_death_record.success is False
        prot = obj.last_death_protection
        assert prot["store_items_unprotected"] >= 1, \
            "العنصر الحقيقي من الاستعلام الفعلي يُعد غير محمي"
        assert prot["recovery_ready"] is False, \
            "عنصر مخزن غير محمي = جاهزية الاسترداد ناقصة"

    def test_death_events_truncated_flag(self, tmp_path, monkeypatch):
        """حد فحص الأحداث (1000): ما بعده غير مفحوص — اقتطاع معلن
        يمنع ادعاء جاهزية الاسترداد الكاملة."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        iso.items.clear()
        h = core.blob_store.put(b"truncation_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}] * 1000
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="truncation-test") is False, \
            "اقتطاع الفحص = فشل الموت"
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        assert obj.is_transforming is False
        assert obj.last_death_record.success is False
        prot = obj.last_death_protection
        assert prot["events_truncated"] is True, \
            "الوصول لحد الفحص يُعلن اقتطاعًا — لا افتراض اكتمال"
        assert prot["recovery_ready"] is False

    def test_death_store_truncated_flag(self, tmp_path, monkeypatch):
        """حد استعلام المخزن (500): اقتطاع معلن يمنع جاهزية الاسترداد."""
        rw, core, iso = self._env(tmp_path, monkeypatch)
        h = core.blob_store.put(b"store_trunc_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        import backend.memory.store as store_mod
        big = _BigStore()
        monkeypatch.setattr(store_mod, "get_store", lambda: big)
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="store-truncation-test") is False, \
            "اقتطاع استعلام المخزن = فشل الموت"
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        assert obj.is_transforming is False
        assert obj.last_death_record.success is False
        prot = obj.last_death_protection
        assert prot["store_truncated"] is True, \
            "امتلاء حد الاستعلام يُعلن اقتطاعًا"
        assert prot["recovery_ready"] is False


# ============================================================
# Part 1f: جولة 11 — بقاء الحالة النهائية بعد إعادة التحميل + اتساق فشل التسجيل
# ============================================================

class TestDeathStatePersistence:
    """R-682 (جولة 11 — اعتراض advisor السادس):
    1) الحالة النهائية يجب أن تُحفظ — علم التحول القديم (is_transforming=True
       المحفوظ أثناء DYING عبر create_phoenix_seed) لا يمنع إعادة المحاولة بعد
       إعادة تهيئة من نفس ملفات الحالة.
    2) فشل تسجيل حدث الموت لا يُبتلع ثم يُعلن نجاح: النتيجة والسجل والحالة
       والعلم متسقون، والرماد والبذور محفوظة."""

    def _env(self, tmp_path, monkeypatch):
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        from backend.memory.core import BlobStore
        blob_dir = tmp_path / "blobs"
        blob_dir.mkdir(exist_ok=True)
        core = MagicMock()
        core._last_hash = "a" * 64
        core.get_statistics.return_value = {"index": {"total_events": 1}}
        core.blob_store = BlobStore(blob_dir)
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        empty = _IsolatedStore()
        monkeypatch.setattr(store_mod, "get_store", lambda: empty)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)
        return rw, core

    def test_retry_after_reload_not_blocked(self, tmp_path, monkeypatch):
        """فشل موت → الحالة النهائية (LIVING + لا تحول) محفوظة على القرص →
        مثيل جديد من نفس الملفات → إعادة المحاولة لا يمنعها العلم القديم."""
        rw, core = self._env(tmp_path, monkeypatch)
        h = core.blob_store.put(b"retry_reload_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        real_get = core.blob_store.get

        obj = rw.RansomwareDefense()
        # فشل الموت: حقن فشل قراءة → لا نسخ استرداد
        core.blob_store.get = MagicMock(side_effect=RuntimeError("inject: read failed"))
        assert obj.initiate_death(reason="first-attempt") is False
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        assert obj.is_transforming is False

        # إعادة تهيئة من نفس ملفات الحالة (كما بعد إعادة تشغيل)
        core.blob_store.get = real_get  # إصلاح البيئة — الفشل كان محقونًا
        obj2 = rw.RansomwareDefense()
        assert obj2.is_transforming is False, \
            "العلم القديم (المحفوظ أثناء DYING) لا يمنع إعادة المحاولة"
        # إعادة المحاولة تنجح فعلًا — الحارس لا يحبس
        assert obj2.initiate_death(reason="second-attempt") is True, \
            "المثيل الجديد يستطيع الموت — لا تحول معلق من المحاولة الفاشلة"
        assert obj2.phoenix_phase == rw.PhoenixPhase.DEAD

    def test_death_event_recording_failure_consistent(self, tmp_path, monkeypatch):
        """فشل تسجيل حدث الموت تحديدًا: لا يُبتلع ثم يُعلن نجاح — النتيجة
        False، الحالة LIVING، لا تحول معلق، السجل فاشل، والرماد/البذور محفوظة."""
        rw, core = self._env(tmp_path, monkeypatch)
        h = core.blob_store.put(b"event_fail_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        real_append = core.append_event

        def failing_append(*args, **kwargs):
            et = kwargs.get("event_type") or (args[0] if args else None)
            if et in ("phoenix::death", "phoenix::death_failed"):
                raise RuntimeError("inject: death event recording failed")
            return real_append(*args, **kwargs)
        core.append_event = failing_append

        obj = rw.RansomwareDefense()
        result = obj.initiate_death(reason="event-fail-test")
        # اتساق كامل: النتيجة فشل (لا استثناء يهرب ولا نجاح يُعلن)
        assert result is False, \
            "فشل تسجيل حدث الموت = فشل العملية — لا يُبتلع ثم يُعلن نجاح"
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        assert obj.is_transforming is False
        assert obj.last_death_record.success is False
        # مواد الاسترداد محفوظة: الرماد أُنشئ (النسخ نجحت) ولم يُستهلك
        assert len(obj.ashes) >= 1
        assert len(obj.seeds) >= 1


# ============================================================
# Part 1g: جولة 12 — فشل الحفظ المزدوج + تسوية الحالة عند التحميل
# ============================================================

class TestDeathDoubleSaveFailure:
    """R-682 (جولة 12 — اعتراض advisor السابع): عند فشل الحفظ النهائي
    وتراجع الحفظ معًا، يبقى على القرص DYING + is_transforming=True (محفوظان
    أثناء إنشاء البذرة). تصحيح الذاكرة لا يصلح القرص — الحل: (1) لا يُعلن حدث
    إكمال لعملية فشلت (الحفظ قبل الحدث)، (2) الحالة الانتقالية المعلقة تُسوّى
    عند التحميل كعملية منقطعة لا كتحول جارٍ يمنع المحاولة."""

    def _env(self, tmp_path, monkeypatch):
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        from backend.memory.core import BlobStore
        blob_dir = tmp_path / "blobs"
        blob_dir.mkdir(exist_ok=True)
        core = MagicMock()
        core._last_hash = "a" * 64
        core.get_statistics.return_value = {"index": {"total_events": 1}}
        core.blob_store = BlobStore(blob_dir)
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        empty = _IsolatedStore()
        monkeypatch.setattr(store_mod, "get_store", lambda: empty)
        import threading as _th
        monkeypatch.setattr(_th, "Thread", _NoThreads)
        return rw, core

    def test_double_save_failure_settled_on_reload(self, tmp_path, monkeypatch):
        """الحفظ الانتقالي (أثناء البذرة) ينجح؛ الحفظ النهائي والتراجع يفشلان
        معًا: لا موت معلن (False)، لا حدث إكمال (phoenix::death غير موجود)،
        حدث فشل صريح بمرحلة الفشل — وبعد إعادة التهيئة من نفس الملفات تُعامل
        الحالة المعلقة كعملية منقطعة والمحاولة تنجح."""
        rw, core = self._env(tmp_path, monkeypatch)
        h = core.blob_store.put(b"double_save_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]

        obj = rw.RansomwareDefense()
        # الحفظ الانتقالي (استدعاء 1 — داخل create_phoenix_seed) ينجح؛
        # كل حفظ لاحق (النهائي + التراجع) يفشل
        orig_save = obj._save_state
        calls = {"n": 0}
        def flaky_save():
            calls["n"] += 1
            if calls["n"] >= 2:
                return False
            return orig_save()
        obj._save_state = flaky_save

        result = obj.initiate_death(reason="double-save-fail")
        assert result is False, "فشل الحفظ النهائي = لا موت معلن"
        assert calls["n"] >= 3, "التراجع حاول الحفظ فعلًا (لا يكتفي بالتحذير)"
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        assert obj.is_transforming is False
        assert obj.last_death_record.success is False
        # لا حدث إكمال لعملية فشلت — فقط حدث فشل بمرحلة معلنة
        death_events = [c for c in core.append_event.call_args_list
                        if c.kwargs.get("event_type") == "phoenix::death"]
        assert not death_events, \
            "لا يُعلن حدث موت ناجح لعملية فشل حفظها النهائي"
        failed_events = [c for c in core.append_event.call_args_list
                         if c.kwargs.get("event_type") == "phoenix::death_failed"]
        assert failed_events, "حدث الفشل يُسجل صراحة"
        assert failed_events[0].kwargs["payload"].get("failure_stage") == \
            "final state save failed"

        # إعادة التهيئة من نفس الملفات: الحالة المعلقة (DYING + تحول) تُعامل
        # كعملية منقطعة — لا كتحول جارٍ يمنع المحاولة
        obj2 = rw.RansomwareDefense()
        assert obj2.is_transforming is False, \
            "العلم المعلق من عملية منقطعة يُصفَّر عند التحميل"
        assert obj2.phoenix_phase == rw.PhoenixPhase.LIVING, \
            "DYING المعلق يُسوّى إلى LIVING — عملية منقطعة لا موت مكتمل"
        # المحاولة تنجح فعلًا (بعد إصلاح الحفظ)
        assert obj2.initiate_death(reason="retry-after-settlement") is True
        assert obj2.phoenix_phase == rw.PhoenixPhase.DEAD

    def test_death_failed_event_recording_consistent(self, tmp_path, monkeypatch):
        """مسار death_failed نفسه (جاهزية ناقصة): فشل تسجيل حدث الفشل أيضًا
        فاشل-مغلق — النتيجة False والحالة LIVING والسجل فاشل والمواد محفوظة.
        (تصويح تغطية الجولة 11: المساران كلاهما مختبر الآن.)"""
        rw, core = self._env(tmp_path, monkeypatch)
        h = core.blob_store.put(b"event_fail_path2_blob_" * 4, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        # عنصر مخزن غير محمي → recovery_ready=False → مسار death_failed
        import backend.memory.store as store_mod
        iso = _IsolatedStore()
        iso.save_semantic(concept="unprotected_item", definition="سجل",
                           confidence=0.9)
        monkeypatch.setattr(store_mod, "get_store", lambda: iso)
        real_append = core.append_event
        def failing_append(*args, **kwargs):
            et = kwargs.get("event_type") or (args[0] if args else None)
            if et in ("phoenix::death", "phoenix::death_failed"):
                raise RuntimeError("inject: death-failed event recording failed")
            return real_append(*args, **kwargs)
        core.append_event = failing_append

        obj = rw.RansomwareDefense()
        result = obj.initiate_death(reason="death-failed-event-fail")
        assert result is False
        assert obj.phoenix_phase == rw.PhoenixPhase.LIVING
        assert obj.is_transforming is False
        assert obj.last_death_record.success is False
        assert len(obj.ashes) >= 1  # مواد الاسترداد محفوظة
        assert len(obj.seeds) >= 1


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
