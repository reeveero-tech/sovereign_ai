# -*- coding: utf-8 -*-
"""R-752 (ROADMAP_V5 ١.٥ — بأمر المالك 2026-10-25 «أسلمك المشروع»): خزينة أسرار
الموصلات العامة — حفظ أسرار كما يفعل وكيل حقيقي.

معيار الإغلاق: سر يُكتب ويُقرأ ويُدوّر بأثر تدقيق لكل فعل، ولا سر في الملف
المخزّن ولا مخرجات القائمة ولا أحداث التدقيق ولا السجلات (بصمة فقط)، وحصر
نطاقي (كل قدرة ترى أسرارها فقط)، وتشفير مصادَق حقيقي (AES-256-GCM — لا XOR)
يكشف أي تلاعب بالنص المشفر أو بالبيانات الوصفية (النطاق مربوط كـAAD).
لا أثر = لا تنفيذ: تعذر كتابة حدث التدقيق يرفض الفعل ولا يغير الخزينة.
"""

import base64
import json
import logging
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

SECRET = "sk-test-VALUE-0123456789abcdef"  # قيمة اختبار — ليست سرًا حقيقيًا
NEW_SECRET = "sk-test-ROTATED-fedcba9876543210"


def _mk(tmp_path, audit=None, key=None):
    from sovereign.secrets_vault import SecretsVault
    events = [] if audit is None else audit
    k = key if key is not None else base64.b64encode(os.urandom(32)).decode()
    v = SecretsVault(path=tmp_path / "vault.json", master_key_b64=k,
                     audit=lambda ev, payload: events.append((ev, payload)))
    return v, events, k


def test_put_get_roundtrip_with_scope(tmp_path):
    v, events, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    assert v.get("openai", capability="brain", actor="agent") == SECRET
    assert [e[0] for e in events] == ["vault.put", "vault.get"]


def test_scope_denied_for_other_capability(tmp_path):
    from sovereign.secrets_vault import ScopeDenied
    v, events, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    with pytest.raises(ScopeDenied):
        v.get("openai", capability="media", actor="agent")
    assert events[-1][0] == "vault.denied"  # الرفض نفسه مُدقق


def test_no_plaintext_on_disk_or_listing_or_audit(tmp_path):
    v, events, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    v.get("openai", capability="brain", actor="agent")
    raw = (tmp_path / "vault.json").read_text(encoding="utf-8")
    assert SECRET not in raw
    assert base64.b64encode(SECRET.encode()).decode() not in raw
    listing = json.dumps(v.list(), ensure_ascii=False)
    assert SECRET not in listing and "fingerprint" in listing
    assert SECRET not in json.dumps(events, ensure_ascii=False)


def test_real_aead_tamper_ciphertext_detected(tmp_path):
    from sovereign.secrets_vault import VaultIntegrityError
    v, _, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    p = tmp_path / "vault.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    ct = bytearray(base64.b64decode(data["secrets"]["openai"]["ciphertext"]))
    ct[0] ^= 0x01
    data["secrets"]["openai"]["ciphertext"] = base64.b64encode(bytes(ct)).decode()
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(VaultIntegrityError):
        v.get("openai", capability="brain", actor="agent")


def test_scope_widening_on_disk_detected(tmp_path):
    """توسيع النطاق بتعديل الملف يُكشف — النطاق مربوط بالتشفير (AAD)."""
    from sovereign.secrets_vault import VaultIntegrityError
    v, _, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    p = tmp_path / "vault.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["secrets"]["openai"]["scopes"] = ["brain", "media"]
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(VaultIntegrityError):
        v.get("openai", capability="media", actor="agent")


def test_wrong_master_key_cannot_read(tmp_path):
    from sovereign.secrets_vault import VaultIntegrityError
    v, _, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    v2, _, _ = _mk(tmp_path)  # مفتاح رئيسي مختلف
    with pytest.raises(VaultIntegrityError):
        v2.get("openai", capability="brain", actor="agent")


def test_rotation_versions_and_replaces_value(tmp_path):
    v, events, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    fp1 = v.list()[0]["fingerprint"]
    v.rotate("openai", NEW_SECRET, actor="owner")
    meta = v.list()[0]
    assert meta["version"] == 2 and meta["fingerprint"] != fp1
    assert v.get("openai", capability="brain", actor="agent") == NEW_SECRET
    assert "vault.rotate" in [e[0] for e in events]
    assert SECRET not in (tmp_path / "vault.json").read_text(encoding="utf-8")


def test_audit_failure_refuses_operation(tmp_path):
    """لا أثر = لا تنفيذ (نمط R-635): تعذر التدقيق يرفض الكتابة ولا يغير الملف."""
    from sovereign.secrets_vault import SecretsVault, VaultAuditError

    def broken(ev, payload):
        raise RuntimeError("ledger cannot sign")
    k = base64.b64encode(os.urandom(32)).decode()
    v = SecretsVault(path=tmp_path / "vault.json", master_key_b64=k, audit=broken)
    with pytest.raises(VaultAuditError):
        v.put("openai", SECRET, scopes=["brain"], actor="owner")
    assert not (tmp_path / "vault.json").exists() or \
        "openai" not in (tmp_path / "vault.json").read_text(encoding="utf-8")


def test_no_master_key_means_disabled_fail_closed(tmp_path):
    from sovereign.secrets_vault import SecretsVault, VaultDisabled
    v = SecretsVault(path=tmp_path / "vault.json", master_key_b64=None,
                     audit=lambda e, p: None)
    assert v.enabled is False
    with pytest.raises(VaultDisabled):
        v.put("openai", SECRET, scopes=["brain"], actor="owner")


def test_weak_master_key_rejected(tmp_path):
    from sovereign.secrets_vault import SecretsVault, VaultDisabled
    v = SecretsVault(path=tmp_path / "vault.json",
                     master_key_b64=base64.b64encode(b"short").decode(),
                     audit=lambda e, p: None)
    assert v.enabled is False
    with pytest.raises(VaultDisabled):
        v.put("x", SECRET, scopes=["brain"], actor="owner")


def test_redaction_filter_scrubs_logs(tmp_path, caplog):
    v, _, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    assert SECRET not in v.redact(f"calling with {SECRET} now")
    logger = logging.getLogger("vault-redaction-test")
    logger.addFilter(v.log_filter())
    with caplog.at_level(logging.INFO, logger="vault-redaction-test"):
        logger.info("token=%s", SECRET)
    assert SECRET not in caplog.text


def test_delete_removes_and_audits(tmp_path):
    from sovereign.secrets_vault import SecretNotFound
    v, events, _ = _mk(tmp_path)
    v.put("openai", SECRET, scopes=["brain"], actor="owner")
    v.delete("openai", actor="owner")
    with pytest.raises(SecretNotFound):
        v.get("openai", capability="brain", actor="agent")
    assert events[-1][0] in ("vault.delete", "vault.get_missing")


def test_status_tool_registered_and_inventory_moves(tmp_path):
    """أداة vault.status مسجلة فعلًا → الجرد ينقل الخزينة من «غير مبني»."""
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        names = {t["name"] for t in client.get("/tools/list").json()["tools"]}
        assert "vault.status" in names
        caps = {c["id"]: c for c in client.get("/capabilities").json()["capabilities"]}
        assert caps["secrets_vault"]["level"] != "missing"
        r = client.get("/vault/status")
        assert r.status_code == 200
        body = r.json()
        assert "enabled" in body and "secrets" in body
        assert SECRET not in r.text


def test_live_vault_audits_through_signed_ledger(tmp_path, monkeypatch):
    """الخزينة الحية تدقق عبر السجل السيادي (vault_access) — وبلا مفتاح توقيع
    (RuntimeError من حارس R-635) يُرفض الفعل: الاعتماد على ١.٣ صريح."""
    import memory.core as core_mod
    import sovereign.secrets_vault as sv
    calls = []

    class FakeCore:
        def __init__(self, fail):
            self.fail = fail

        def append_event(self, event_type, payload, user=None):
            if self.fail:
                raise RuntimeError("R-635: No active signing key available")
            calls.append((event_type, payload, user))

    monkeypatch.setenv(sv.MASTER_KEY_ENV, base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv(sv.VAULT_PATH_ENV, str(tmp_path / "live.json"))
    monkeypatch.setattr(sv, "_VAULT", None)
    monkeypatch.setattr(core_mod, "get_core", lambda: FakeCore(fail=True))
    with pytest.raises(sv.VaultAuditError):
        sv.get_vault().put("openai", SECRET, scopes=["brain"], actor="owner")
    assert not (tmp_path / "live.json").exists()

    monkeypatch.setattr(core_mod, "get_core", lambda: FakeCore(fail=False))
    sv.get_vault().put("openai", SECRET, scopes=["brain"], actor="owner")
    assert calls and calls[0][0] == "vault_access" and calls[0][1]["op"] == "vault.put"
    assert SECRET not in json.dumps(calls, ensure_ascii=False)
    monkeypatch.setattr(sv, "_VAULT", None)


def test_inventory_enabled_only_with_master_key_and_signing():
    import capability_inventory as ci
    names = ["vault.status"]
    def lvl(flags, signing):
        inv = ci.build_inventory(names, flags, signing_ok=signing, cloud_disk_enabled=False)
        return {c["id"]: c for c in inv["capabilities"]}["secrets_vault"]["level"]
    assert lvl({"vault": False}, True) == "implemented_disabled"
    assert lvl({"vault": True}, False) == "blocked"
    assert lvl({"vault": True}, True) == "enabled"
