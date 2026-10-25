# -*- coding: utf-8 -*-
"""R-759 (ROADMAP_V5 ١.٥-ب — بأمر المالك 2026-10-25 «أسلمك المشروع»): استبدال XOR
بمفتاح مكرر بتشفير مصادَق AES-256-GCM في:
  - `backend/memory/encoding.py` (`QuantumLikeEncryption.encrypt/decrypt`)
  - `backend/consciousness/identity_core.py` (`_encrypt_seal/_decrypt_seal`)
مع ترحيل الحزم والأختام القائمة (XOR) دون فقد.

معيار القبول (الخارطة): النص المشفر لا يكشف بنية النص الأصلي، كشف التلاعب، ترحيل
الأختام والحزم القائمة دون فقد.
"""

import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

KEY = "r759-test-master-key"


def _enc():
    from backend.memory.encoding import QuantumLikeEncryption
    return QuantumLikeEncryption(master_key=KEY)


def _legacy_token(level: str, data: bytes) -> str:
    """الصيغة القديمة حرفيًا (XOR بمفتاح مكرر) — لبناء بيانات قائمة للترحيل."""
    mk = hashlib.sha3_512(KEY.encode()).digest()
    if level == "high":
        k1, k2, k3 = mk[:16], mk[16:32], mk[32:48]
        l1 = bytes(a ^ b for a, b in zip(data, k1 * (len(data) // 16 + 1)))
        l2 = bytes(a ^ b for a, b in zip(l1, k2 * (len(l1) // 16 + 1)))
        l3 = bytes(a ^ b for a, b in zip(l2, k3 * (len(l2) // 16 + 1)))
        return json.dumps({"type": "high", "data": l3.hex(), "salt": "00"})
    k = mk[:32]
    return json.dumps({"type": "standard",
                       "data": bytes(a ^ b for a, b in zip(data, k * (len(data) // 32 + 1))).hex()})


# ------------------------------------------------------------ memory/encoding
@pytest.mark.parametrize("level", ["standard", "high", "low", "medium"])
def test_ciphertext_hides_plaintext_structure(level):
    enc = _enc()
    plain = b"A" * 256                                     # بنية متكررة صريحة
    tok = json.loads(enc.encrypt(plain, level=level))
    ct = bytes.fromhex(tok["data"])
    assert tok["type"] == "aesgcm-v1"
    # XOR بمفتاح مكرر يكشف الدورية: ct[i] == ct[i+16] لنص متكرر — ممنوع
    assert ct[:16] != ct[16:32] and ct[:32] != ct[32:64]
    # تشفير مرتين لنفس النص يختلف (nonce عشوائي)
    assert json.loads(enc.encrypt(plain, level=level))["data"] != tok["data"]
    assert enc.decrypt(json.dumps(tok)) == plain


@pytest.mark.parametrize("field", ["data", "n", "level"])
def test_tampering_detected(field):
    enc = _enc()
    tok = json.loads(enc.encrypt(b"sovereign payload " * 4, level="high"))
    if field == "level":
        tok["level"] = "standard"                          # المستوى مربوط كـAAD
    else:
        raw = bytearray(bytes.fromhex(tok[field]))
        raw[0] ^= 0x01
        tok[field] = raw.hex()
    assert enc.decrypt(json.dumps(tok)) is None


def test_wrong_key_fails_closed():
    from backend.memory.encoding import QuantumLikeEncryption
    tok = _enc().encrypt(b"secret", level="standard")
    assert QuantumLikeEncryption(master_key="another-key").decrypt(tok) is None


@pytest.mark.parametrize("level", ["standard", "high"])
def test_legacy_packages_read_and_migrated_without_loss(level):
    enc = _enc()
    plain = "حزمة قائمة قبل R-759 — بلا فقد".encode("utf-8") * 3
    legacy = _legacy_token(level, plain)
    assert enc.decrypt(legacy) == plain                    # قراءة القديم مستمرة
    migrated = enc.migrate(legacy)
    assert json.loads(migrated)["type"] == "aesgcm-v1"
    assert json.loads(migrated)["level"] == level
    assert enc.decrypt(migrated) == plain                  # لا فقد
    assert enc.migrate(migrated) == migrated               # الحديث لا يُعاد


def test_quantum_level_authenticated_and_keeps_decoherence():
    enc = _enc()
    tok = enc.encrypt(b"q" * 100, level="quantum")
    d = json.loads(tok)
    assert d["type"] == "quantum-gcm-v1"
    assert enc.decrypt(tok) == b"q" * 100
    bad = dict(d)
    raw = bytearray(bytes.fromhex(bad["data"]))
    raw[-1] ^= 0x80
    bad["data"] = raw.hex()
    assert enc.decrypt(json.dumps(bad)) is None            # تلاعب مكشوف
    enc.quantum_states.clear()                             # انهيار الحالة
    assert b"QUANTUM_DECOHERED" in enc.decrypt(tok)


def test_encoder_roundtrip_still_works():
    from backend.memory.encoding import SovereignEncoder
    e = SovereignEncoder()
    out = e.decode(e.encode("مرحبا بالسيادة", encrypt_level="high"))
    assert out.get("_decoded") is True


def test_no_xor_in_write_paths():
    from backend.memory.encoding import QuantumLikeEncryption
    from backend.consciousness.identity_core import IdentityCore
    for fn in (QuantumLikeEncryption.encrypt, IdentityCore._encrypt_seal):
        src = inspect.getsource(fn)
        assert " ^ " not in src, f"{fn.__qualname__} ما زال يكتب بـXOR"


# ------------------------------------------------------------ identity seal
@pytest.fixture
def core(tmp_path, monkeypatch):
    from backend.consciousness import identity_core
    monkeypatch.setattr(identity_core, "IDENTITY_SEAL_FILE", tmp_path / "identity_seal.bin")
    return identity_core.IdentityCore(), identity_core


def test_seal_encrypted_authenticated(core):
    c, _ = core
    payload = json.dumps({"x": "A" * 200})
    blob = c._encrypt_seal(payload)
    assert blob[:4] == b"SVS1"
    body = blob[4 + 12:]
    assert body[:32] != body[32:64]                        # لا دورية
    assert c._encrypt_seal(payload) != blob                # nonce عشوائي
    assert c._decrypt_seal(blob) == payload
    tampered = bytearray(blob)
    tampered[-5] ^= 0x01
    with pytest.raises(ValueError):
        c._decrypt_seal(bytes(tampered))


def test_legacy_seal_file_migrated_on_load_without_loss(core):
    c, mod = core
    c.seal = None
    seal = c.create_seal()
    original = dict(seal.__dict__)
    # كتابة الختم بالصيغة القديمة (XOR بالمفتاح المشتق) كما كان على القرص قبل R-759
    raw = json.dumps(original, ensure_ascii=False).encode()
    key = mod.derive_key("encryption")
    legacy = bytes(a ^ b for a, b in zip(raw, key * (len(raw) // 32 + 1)))
    mod.IDENTITY_SEAL_FILE.write_bytes(legacy)
    c.seal, c.is_sealed = None, False
    c._load_seal()
    assert c.seal is not None and c.seal.__dict__ == original      # لا فقد
    assert mod.IDENTITY_SEAL_FILE.read_bytes()[:4] == b"SVS1"      # رُحّل على القرص
    c.seal = None
    c._load_seal()
    assert c.seal.__dict__ == original                             # يُقرأ بعد الترحيل
