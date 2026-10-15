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
        """RED: JSON صالح لكنه ينقصه حقل إلزامي → None + تسجيل (رفض صريح)."""
        obj = self._make_defense()
        seed = self._make_seed()
        encrypted = obj._encrypt_seed(seed)
        # فك التشفير اليدوي بالطبقتين ثم إعادة تشفير نسخة ناقصة الحقول
        import base64 as _b64
        import hashlib as _hl
        from backend.config import SOVEREIGN_KEY as _SK
        key1 = _hl.sha256(_SK.encode()).digest()
        key2 = _hl.sha256(seed.resurrection_key.encode()).digest()
        raw = _b64.b64decode(encrypted)
        layer1 = bytes(a ^ b for a, b in zip(raw, key2 * (len(raw) // 32 + 1)))
        plain = bytes(a ^ b for a, b in zip(layer1, key1 * (len(layer1) // 32 + 1)))
        parsed = json.loads(plain.decode("utf-8"))
        del parsed["resurrection_key"]  # حذف حقل إلزامي
        tampered_plain = json.dumps(parsed).encode("utf-8")
        l1 = bytes(a ^ b for a, b in zip(tampered_plain, key1 * (len(tampered_plain) // 32 + 1)))
        l2 = bytes(a ^ b for a, b in zip(l1, key2 * (len(l1) // 32 + 1)))
        tampered_encrypted = _b64.b64encode(l2)
        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = obj._decrypt_seed(tampered_encrypted, resurrection_key=seed.resurrection_key)
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

    def test_engine_init_failure_returns_none_logged(self, monkeypatch, caplog):
        lc = self._reset(monkeypatch)
        # حقن فشل في get_engine
        import nexus.core.engine as engine_mod
        def _boom():
            raise RuntimeError("engine init exploded (injected)")
        monkeypatch.setattr(engine_mod, "get_engine", _boom)
        with caplog.at_level(logging.ERROR, logger="backend.compat.nexus_lifecycle"):
            result = asyncio.run(lc.ensure_nexus_running_async())
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records), \
            "فشل تهيئة المحرك يجب أن يُسجَّل (لا صمت)"

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
        with caplog.at_level(logging.ERROR, logger="backend.compat.nexus_lifecycle"):
            result = asyncio.run(lc.ensure_nexus_running_async())
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records), \
            "فشل تهيئة المكونات يجب أن يُسجَّل (لا صمت)"


class TestNexusRecommendationsSite:
    """backend/compat/nexus_recommendations.py:43 — فشل جلب محرك التوصيات."""

    def test_get_recommendation_engine_failure_logged(self, monkeypatch, caplog):
        import nexus.core.engine as engine_mod
        def _boom():
            raise RuntimeError("recommendations engine exploded (injected)")
        monkeypatch.setattr(engine_mod, "get_engine", _boom)
        from backend.compat import nexus_recommendations as rec
        with caplog.at_level(logging.ERROR, logger="backend.compat.nexus_recommendations"):
            result = rec.get_recommendation_engine()
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records)


class TestEvolutionMutationSite:
    """backend/memory/biological/evolution.py:411 — فشل إجراء طفرة في التطور."""

    def _make_evolution(self):
        from backend.memory.biological.evolution import MemoryEvolution
        evo = MemoryEvolution.__new__(MemoryEvolution)
        # الحد الأدنى الذي يلمسه معالج الاستثناء
        evo.mutations = []
        evo._save_mutation = lambda m: None
        evo.core = type("MockCore", (), {"append_event": lambda *a, **k: None})()
        return evo

    def test_mutation_failure_logged_and_returns_none(self, caplog):
        """فشل الطفرة (حقن خطأ) → None + تسجيل استثناء + طفرة فاشلة في السجل."""
        evo = self._make_evolution()
        with caplog.at_level(logging.ERROR, logger="backend.memory.biological.evolution"):
            result = evo.mutate_concept("nonexistent_concept")
        assert result is None
        assert any("R-682" in r.getMessage() for r in caplog.records), \
            "فشل الطفرة يجب أن يُسجَّل (لا صمت)"
        # الطفرة الفاشلة تُسجَّل في سجل الطفرات
        assert len(evo.mutations) == 1
        assert evo.mutations[0].success is False


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

    def _assert_failure_logged(self, caplog, result):
        assert result is None
        assert len(caplog.records) > 0, "فشل تحميل المكون يجب أن يُسجَّل (لا صمت)"

    def test_load_memory_core_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import memory.core as mem_core
        def _boom():
            raise RuntimeError("memory core exploded (injected)")
        monkeypatch.setattr(mem_core, "get_core", _boom)
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_memory_core()
        self._assert_failure_logged(caplog, result)

    def test_load_memory_dynamic_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import memory.dynamic as dyn
        def _boom():
            raise RuntimeError("dynamic exploded (injected)")
        monkeypatch.setattr(dyn, "get_dynamic_memory", _boom)
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_memory_dynamic()
        self._assert_failure_logged(caplog, result)

    def test_load_memory_store_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import memory.store as st
        def _boom():
            raise RuntimeError("store exploded (injected)")
        monkeypatch.setattr(st, "get_store", _boom)
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_memory_store()
        self._assert_failure_logged(caplog, result)

    def test_load_quantum_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import quantum.quantum_controller as qc
        def _boom():
            raise RuntimeError("quantum exploded (injected)")
        monkeypatch.setattr(qc, "get_quantum_controller", _boom)
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_quantum()
        self._assert_failure_logged(caplog, result)

    def test_load_nexus_failure_logged(self, monkeypatch, caplog):
        orch = self._make_orchestrator()
        import nexus.main as nmain
        def _boom():
            raise RuntimeError("nexus exploded (injected)")
        monkeypatch.setattr(nmain, "initialize_nexus", _boom)
        with caplog.at_level(logging.WARNING, logger="backend.orchestrator"):
            result = orch._load_nexus()
        self._assert_failure_logged(caplog, result)


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
        with caplog.at_level(logging.WARNING, logger="nexus.performance.code_analyzer"):
            result = analyzer.analyze_file(str(bad))
        assert result is None
        assert len(caplog.records) > 0

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
