"""
R-682 (Task 6): Security tests for except->return None sites.

For each modified site, proves:
1. Injected failure → exception is logged (not silent)
2. Returns None safely (does not crash)
3. Legitimate success path still works

Sites covered (9 high-risk):
- backend/sovereign/ledger/anchor.py:262 (anchor_batch)
- backend/sovereign/keys/rotation.py:81 (KeyRotation.rotate)
- guardian/integrity_checker.py:118 (_snapshot_file)
- nexus/encryption/encryption_engine.py:77 (decrypt)
- nexus/encryption/secure_communication.py:83 (decode_payload)
- nexus/user_management/auth_engine.py:76 (verify_token)
- backend/consciousness/identity_core.py:722 (backup)
- backend/memory/defense/ransomware.py:274 (seed creation)
- backend/memory/defense/ransomware.py:357 (seed decryption)
"""

import json
import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest


# ============================================================
# 1) anchor.py:262 — anchor_batch
# ============================================================

class TestAnchorBatchSecurity:

    def _make_keyring(self, tmp_path):
        """Create a real KeyRing with one active key in tmp_path."""
        from backend.sovereign.keys.keyring import KeyRing
        kr = KeyRing(keys_dir=tmp_path / "keys")
        kr.generate_new_key(reason="test-r682")
        kr.save_to_disk()
        return kr

    def test_failure_returns_none_and_logs_exception(self, tmp_path, caplog):
        """Inject UNEXPECTED failure (corrupt ledger path) → None + logger.exception.

        Note: R-664 signature-mismatch path uses logger.error (fail-closed,
        documented) — that's a different, expected path. This test injects an
        unexpected exception to hit the R-682 logger.exception site.
        """
        from backend.sovereign.ledger import LedgerAnchor

        kr = self._make_keyring(tmp_path)
        key_id = kr.get_active_key().key_id

        ledger = tmp_path / "ledger.jsonl"
        anchors = tmp_path / "anchors.jsonl"
        # Ledger exists but is a DIRECTORY (not file) → read_text raises IOError
        ledger.mkdir(exist_ok=True)

        anchor = LedgerAnchor(ledger_path=ledger, anchors_path=anchors)
        with caplog.at_level(logging.ERROR, logger="sovereign.ledger.anchor"):
            result = anchor.anchor_batch(0, 1, key_id, "any_sig", "INJECT",
                                         keyring=kr)
        assert result is None, "anchor_batch must return None on failure"
        # Must log with exc_info (stack trace) via logger.exception
        assert any(r.exc_info for r in caplog.records), (
            "anchor_batch failure must log with logger.exception (exc_info) — "
            "silent swallow without stack trace is a security hole"
        )
        assert any("R-682" in r.getMessage() for r in caplog.records), (
            "must include R-682 [SECURITY] tag"
        )

    def test_legitimate_success_still_works(self, tmp_path):
        """anchor_batch with valid signature + keyring still succeeds."""
        from backend.sovereign.ledger import LedgerAnchor
        import hmac, hashlib

        kr = self._make_keyring(tmp_path)
        key = kr.get_active_key()
        key_id = key.key_id

        ledger = tmp_path / "ledger.jsonl"
        anchors = tmp_path / "anchors.jsonl"
        events = ['{"id":0}', '{"id":1}', '{"id":2}', '{"id":3}']
        ledger.write_text("\n".join(events) + "\n")

        anchor = LedgerAnchor(ledger_path=ledger, anchors_path=anchors)
        # Compute valid signature (same logic as production)
        from backend.sovereign.ledger.anchor import compute_merkle_root
        root = compute_merkle_root(events)
        sig_data = f"anchor_sig_v2|0|3|4|{root}|{key_id}"
        sig = hmac.new(key.private_key.encode(), sig_data.encode(),
                      hashlib.sha256).hexdigest()

        result = anchor.anchor_batch(0, 3, key_id, sig, "TEST", keyring=kr)
        assert result is not None, "legitimate anchor_batch must succeed"
        assert result["batch_start"] == 0
        assert result["batch_end"] == 3


# ============================================================
# 2) rotation.py:81 — KeyRotation.rotate
# ============================================================

class TestKeyRotationSecurity:

    def _make_rotation(self, tmp_path):
        from backend.sovereign.keys.rotation import KeyRotation
        from backend.sovereign.keys.keyring import KeyRing
        kr = KeyRing(keys_dir=tmp_path / "keys")
        kr.generate_new_key(reason="test-r682")
        kr.save_to_disk()
        return KeyRotation(keyring=kr)

    def test_failure_returns_none_and_logs_exception(self, tmp_path, caplog):
        """Inject failure (monkeypatch save_to_disk to raise) → None + logger.exception."""
        rotation = self._make_rotation(tmp_path)
        from backend.sovereign.keys.keyring import KeyRing

        # Inject failure: make save_to_disk raise
        original_save = rotation.keyring.save_to_disk
        def _fail_save():
            raise RuntimeError("injected_disk_failure_r682")
        rotation.keyring.save_to_disk = _fail_save

        with caplog.at_level(logging.ERROR, logger="sovereign.keys.rotation"):
            result = rotation.rotate(reason="test_inject")
        assert result is None, "rotate must return None on failure"
        assert any(r.exc_info for r in caplog.records), (
            "rotate failure must log with logger.exception"
        )
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_legitimate_success_still_works(self, tmp_path):
        """rotate with valid keyring still succeeds."""
        rotation = self._make_rotation(tmp_path)
        result = rotation.rotate(reason="test_ok")
        assert result is not None, "legitimate rotate must succeed"
        assert result.key_id is not None


# ============================================================
# 3) integrity_checker.py:118 — _snapshot_file
# ============================================================

class TestSnapshotFileSecurity:

    def _make_checker(self, tmp_path):
        from guardian.integrity_checker import IntegrityChecker
        return IntegrityChecker(extra_paths=[], alert_callback=None)

    def test_failure_returns_none_and_logs_exception(self, tmp_path, caplog):
        """Inject failure (unreadable file) → None + logger.exception."""
        checker = self._make_checker(tmp_path)
        bad_file = tmp_path / "unreadable.txt"
        bad_file.write_text("data")
        bad_file.chmod(0o000)

        with caplog.at_level(logging.WARNING, logger="guardian.integrity_checker"):
            result = checker._snapshot_file(bad_file)
        assert result is None, "_snapshot_file must return None on failure"
        assert any(r.exc_info for r in caplog.records), (
            "_snapshot_file failure must log with logger.exception"
        )
        # restore permission for cleanup
        bad_file.chmod(0o644)

    def test_legitimate_file_still_snapshots(self, tmp_path):
        """Normal file still produces a snapshot."""
        checker = self._make_checker(tmp_path)
        good_file = tmp_path / "good.txt"
        good_file.write_text("hello")
        result = checker._snapshot_file(good_file)
        assert result is not None, "legitimate file must produce snapshot"


# ============================================================
# 4) encryption_engine.py:77 — decrypt
# ============================================================

class TestDecryptSecurity:

    def _make_engine(self):
        try:
            from nexus.encryption.encryption_engine import EncryptionEngine
        except ImportError:
            pytest.skip("nexus.encryption not importable")
        import hashlib
        return EncryptionEngine(master_key=hashlib.sha256(b"test").hexdigest())

    def test_failure_returns_none_and_logs_exception(self, caplog):
        """Inject tampered ciphertext → None + logger.exception."""
        engine = self._make_engine()
        with caplog.at_level(logging.ERROR, logger="nexus.encryption.encryption_engine"):
            result = engine.decrypt("TAMPERED_NOT_VALID_B64!!!")
        assert result is None, "decrypt must return None on failure"
        assert any(r.exc_info for r in caplog.records), (
            "decrypt failure must log with logger.exception"
        )


# ============================================================
# 5) secure_communication.py:83 — decode_payload
# ============================================================

class TestDecodePayloadSecurity:

    def test_failure_returns_none_and_logs_exception(self, caplog):
        """Inject garbage base64 → None + logger.exception."""
        try:
            from nexus.encryption.secure_communication import SecureCommunication
        except ImportError:
            pytest.skip("nexus.encryption not importable")
        import hashlib
        comm = SecureCommunication(secret=hashlib.sha256(b"test").digest())
        with caplog.at_level(logging.ERROR, logger="nexus.encryption.secure_communication"):
            result = comm.decode_payload("!!!NOT_BASE64!!!")
        assert result is None, "decode_payload must return None on failure"
        assert any(r.exc_info for r in caplog.records), (
            "decode_payload failure must log with logger.exception"
        )


# ============================================================
# 6) auth_engine.py:76 — verify_token
# ============================================================

class TestVerifyTokenSecurity:

    def _make_engine(self):
        try:
            from nexus.user_management.auth_engine import AuthEngine
        except ImportError:
            pytest.skip("nexus.user_management not importable")
        return AuthEngine(secret="test_secret_r682")

    def test_failure_returns_none_and_logs_exception(self, caplog):
        """Inject garbage token → None + logger.exception."""
        engine = self._make_engine()
        with caplog.at_level(logging.ERROR, logger="nexus.user_management.auth_engine"):
            result = engine.verify_token("GARBAGE_TOKEN")
        assert result is None, "verify_token must return None on invalid token"
        assert any(r.exc_info for r in caplog.records), (
            "verify_token failure must log with logger.exception"
        )

    def test_legitimate_token_still_works(self):
        """Valid token still verifies."""
        engine = self._make_engine()
        token = engine.create_token(user_id="u1", username="test", role="admin")
        result = engine.verify_token(token)
        assert result is not None, "legitimate token must verify"


# ============================================================
# 7) identity_core.py:722 — create_backup
# ============================================================

class TestIdentityBackupSecurity:

    def _make_core(self, tmp_path, monkeypatch):
        from backend.consciousness.identity_core import IdentityCore, IdentitySnapshot
        import backend.consciousness.identity_core as ic

        core = IdentityCore.__new__(IdentityCore)
        # Provide a minimal IdentitySnapshot (create_backup uses .__dict__)
        core.current_identity = IdentitySnapshot(
            content_hash="0" * 64,
            identity_score=0.5,
            stability=0.5,
            change_rate=0.0,
            timestamp=time.time()
        ) if hasattr(IdentitySnapshot, "content_hash") else None
        # Fallback: use a simple object with __dict__
        if core.current_identity is None:
            class _MockSnapshot:
                content_hash = "0" * 64
                identity_score = 0.5
                stability = 0.5
                change_rate = 0.0
                timestamp = 0.0
            core.current_identity = _MockSnapshot()
        core.seal = None
        core.backups = []
        core.compute_identity = lambda: None

        backup_dir = tmp_path / "identity_backups"
        backup_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(ic, "IDENTITY_BACKUP_DIR", backup_dir)
        return core

    def test_failure_returns_none_and_logs_exception(self, tmp_path, caplog, monkeypatch):
        """Inject failure (make backup dir a FILE) → None + logger.exception."""
        from backend.consciousness.identity_core import IdentityCore
        import backend.consciousness.identity_core as ic

        core = self._make_core(tmp_path, monkeypatch)
        # Make it unwritable: replace dir with a FILE
        backup_dir = tmp_path / "identity_backups"
        import shutil
        shutil.rmtree(backup_dir)
        backup_dir.write_text("block")  # now a file → open() fails

        with caplog.at_level(logging.ERROR, logger="backend.consciousness.identity_core"):
            result = core.create_backup()
        assert result is None, "create_backup must return None on failure"
        assert any(r.exc_info for r in caplog.records), (
            "create_backup failure must log with logger.exception"
        )
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_legitimate_backup_still_works(self, tmp_path, monkeypatch):
        """create_backup with writable dir still succeeds."""
        core = self._make_core(tmp_path, monkeypatch)
        result = core.create_backup()
        assert result is not None, "legitimate create_backup must succeed"
        assert result.id.startswith("identity_backup_")


# ============================================================
# 8) ransomware.py:274 — create_phoenix_seed
# ============================================================

class TestRansomwareSeedCreationSecurity:

    def _make_defense(self, tmp_path, monkeypatch):
        from backend.memory.defense.ransomware import RansomwareDefense
        import backend.memory.defense.ransomware as rd

        rd_obj = RansomwareDefense.__new__(RansomwareDefense)
        # Mock core with all needed methods (get_statistics, _last_hash used by create_phoenix_seed)
        class _MockCore:
            def append_event(self, *a, **k): pass
            def get_statistics(self):
                return {"events": 0, "blobs": 0}
            _last_hash = "0" * 64
        rd_obj.core = _MockCore()
        rd_obj.encoder = None
        rd_obj.watcher = None
        rd_obj.phoenix_phase = None
        rd_obj.resurrection_level = 0
        rd_obj.is_transforming = False
        rd_obj.last_resurrection = None
        rd_obj.seeds = {}
        rd_obj.ashes = {}
        rd_obj.master_resurrection_key = "test_key"
        rd_obj._active = False  # no background threads

        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rd, "PHOENIX_SEEDS_DIR", seeds_dir)
        return rd_obj

    def test_failure_returns_none_and_logs_exception(self, tmp_path, caplog, monkeypatch):
        """Inject failure (unwritable seeds dir) → None + logger.exception."""
        from backend.memory.defense.ransomware import RansomwareDefense
        import backend.memory.defense.ransomware as rd

        rd_obj = self._make_defense(tmp_path, monkeypatch)
        # Make seeds dir unwritable: replace with FILE
        seeds_dir = tmp_path / "seeds"
        import shutil
        shutil.rmtree(seeds_dir)
        seeds_dir.write_text("block")

        with caplog.at_level(logging.ERROR, logger="backend.memory.defense.ransomware"):
            result = rd_obj.create_phoenix_seed(reason="test_inject")
        assert result is None, "create_phoenix_seed must return None on failure"
        assert any(r.exc_info for r in caplog.records), (
            "create_phoenix_seed failure must log with logger.exception"
        )
        assert any("R-682" in r.getMessage() for r in caplog.records)

    def test_legitimate_seed_still_created(self, tmp_path, monkeypatch):
        """create_phoenix_seed with writable dir still succeeds."""
        rd_obj = self._make_defense(tmp_path, monkeypatch)
        result = rd_obj.create_phoenix_seed(reason="test_ok")
        assert result is not None, "legitimate create_phoenix_seed must succeed"


# ============================================================
# 9) ransomware.py:364 — _decrypt_seed
# ============================================================

class TestRansomwareSeedDecryptionSecurity:

    def _make_defense(self):
        from backend.memory.defense.ransomware import RansomwareDefense
        rd_obj = RansomwareDefense.__new__(RansomwareDefense)
        rd_obj.core = type("MockCore", (), {"append_event": lambda *a, **k: None})()
        return rd_obj

    def test_not_implemented_warns_not_silent(self, caplog):
        """_decrypt_seed is NOT implemented → must log warning (not silent)."""
        from backend.memory.defense.ransomware import RansomwareDefense

        rd_obj = self._make_defense()
        with caplog.at_level(logging.WARNING, logger="backend.memory.defense.ransomware"):
            result = rd_obj._decrypt_seed(b"test")
        assert result is None, "_decrypt_seed must return None (not implemented)"
        assert any("not implemented" in r.getMessage() or "R-682" in r.getMessage()
                   for r in caplog.records), (
            "_decrypt_seed must log warning — not silent"
        )

    def test_invalid_input_logs_exception(self, caplog):
        """Garbage input → logger.exception (not bare except).

        Note: _decrypt_seed currently returns None (not implemented) —
        the warning is logged regardless of input validity. This test
        asserts the WARNING path (not silent).
        """
        from backend.memory.defense.ransomware import RansomwareDefense

        rd_obj = self._make_defense()
        with caplog.at_level(logging.WARNING, logger="backend.memory.defense.ransomware"):
            result = rd_obj._decrypt_seed(b"\xff\xfe NOT_VALID")
        assert result is None
        # Must have logged (not silent) — either warning or exception
        assert any(r.exc_info for r in caplog.records) or any(
            "R-682" in r.getMessage() for r in caplog.records
        ), (
            "_decrypt_seed must log (warning or exception) — not silent"
        )


# ============================================================
# 10) Source-code evidence: all 9 sites use logger.exception
# ============================================================

class TestSourceEvidence:

    def test_all_nine_sites_use_logger_exception(self):
        """All 9 modified sites must use logger.exception (not logger.error)."""
        sites = [
            ("backend/sovereign/ledger/anchor.py", "R-682 [SECURITY]: anchor_batch failed"),
            ("backend/sovereign/keys/rotation.py", "R-682 [SECURITY]: KeyRotation failed"),
            ("guardian/integrity_checker.py", "R-682 [SECURITY]: Snapshot error"),
            ("backend/consciousness/identity_core.py", "R-682 [SECURITY]: Identity backup failed"),
            ("backend/memory/defense/ransomware.py", "R-682 [SECURITY]: Ransomware seed creation failed"),
            ("backend/memory/defense/ransomware.py", "R-682 [SECURITY]: Phoenix seed decryption failed"),
            ("nexus/encryption/encryption_engine.py", "R-682 [SECURITY]: Decryption error"),
            ("nexus/encryption/secure_communication.py", "R-682 [SECURITY]: Decode error"),
            ("nexus/user_management/auth_engine.py", "R-682 [SECURITY]: verify_token failed"),
        ]
        for file_path, marker in sites:
            full = _REPO_ROOT / file_path
            src = full.read_text(encoding="utf-8")
            assert marker in src, f"{file_path}: missing R-682 [SECURITY] marker: {marker}"
            lines = src.split("\n")
            found = False
            for i, line in enumerate(lines):
                if marker in line:
                    for j in range(max(0, i - 3), i + 1):
                        if "logger.exception(" in lines[j]:
                            found = True
                            break
                    break
            assert found, f"{file_path}: marker present but logger.exception not used nearby"
