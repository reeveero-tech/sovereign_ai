# -*- coding: utf-8 -*-
"""R-852 (٦.١.٤): احتفاظ السجل — تكامل الواجهة والأداة.

المنطق نفسه مغطى بالمجموعة المجمّدة ledger.retention (20 حالة)؛ هنا: الربط
بالنقاط الحية على نواة معزولة — الحالة علنية بلا حمولة، التحقق بنطاق read،
والأرشفة للمفتاح الرئيسي وحده (رمز بكل النطاقات لا يؤرشف)، ورفض 409 صريح.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(1, str(REPO_ROOT / "backend"))


@pytest.fixture
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app as app_mod
    import scoped_tokens
    import skills_durable
    from backend.memory import retention as R
    from backend.memory.core import SovereignCore
    from backend.sovereign.keys import KeyRing

    kr = KeyRing(keys_dir=tmp_path / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-852 test")
    kr.save_to_disk()
    sc = tmp_path / "sovereign_core"
    (sc / "blobs").mkdir(parents=True)
    R._ORIGIN_CACHE.clear()
    core = SovereignCore(log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
                         index_file=sc / "index.json", meta_file=sc / "meta.json",
                         integrity_file=sc / "integrity.json", keyring=kr)
    for i in range(12):
        core.append_event("test::r852", {"n": i})
    monkeypatch.setattr(app_mod, "_retention_core", lambda: (core, R))
    monkeypatch.setattr(skills_durable, "make_store", lambda: None)
    mgr = scoped_tokens.TokenManager(tmp_path / "auth", key=b"t" * 32, store=None,
                                     audit=lambda e, p: None)
    monkeypatch.setattr(scoped_tokens, "_MGR", mgr)
    master = app_mod._derive_api_auth("api_auth")
    with TestClient(app_mod.app) as client:
        yield client, core, master, mgr, sc
    R._ORIGIN_CACHE.clear()


def test_r852_status_public_and_payload_free(env):
    client, _, _, _, _ = env
    r = client.get("/ledger/retention")
    assert r.status_code == 200
    body = r.json()
    assert body["live_events"] == 12
    assert body["archive"]["segments"] == 0 and body["archive"]["origin"] == "GENESIS"
    assert body["auto"] is False and body["durable"] is None
    assert '"n"' not in r.text  # لا حمولة أحداث في الحالة


def test_r852_archive_master_only(env):
    client, _, master, mgr, sc = env
    body = {"keep_last": 4}
    assert client.post("/ledger/retention/archive", json=body).status_code == 401
    tok = mgr.issue(sorted(mgr.status()["scopes"]), 3600)["token"]
    assert client.post("/ledger/retention/archive",
                       json={**body, "api_key": tok}).status_code == 401
    assert not (sc / "archive").exists()
    plan = client.post("/ledger/retention/archive",
                       json={**body, "api_key": master, "dry_run": True})
    assert plan.status_code == 200 and plan.json()["would_archive"] == 8
    assert not (sc / "archive").exists()
    done = client.post("/ledger/retention/archive", json={**body, "api_key": master})
    assert done.status_code == 200, done.text
    res = done.json()
    assert res["ok"] and res["archived"] == 8 and res["live_status"] == "verified"
    st = client.get("/ledger/retention").json()
    assert st["archive"]["archived_events"] == 8 and st["archive"]["ok"]


def test_r852_verify_requires_read_scope(env):
    client, _, master, mgr, _ = env
    assert client.get("/ledger/retention/verify").status_code == 401
    client.post("/ledger/retention/archive", json={"keep_last": 3, "api_key": master})
    tok = mgr.issue(["read"], 3600)["token"]
    r = client.get("/ledger/retention/verify", params={"deep": True},
                   headers={"X-Sovereign-Key": tok})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] and body["archive"]["events_checked"] == 9
    assert body["durable"] == {"available": False}


def test_r852_refusal_is_409(env):
    client, _, master, _, sc = env
    with open(sc / "ledger.jsonl", "ab") as fh:
        fh.write(b"{torn\n")
    core = env[1]
    core._integrity_cache = None
    r = client.post("/ledger/retention/archive", json={"keep_last": 2, "api_key": master})
    assert r.status_code == 409
    assert not (sc / "archive").exists()
    assert client.post("/ledger/retention/archive",
                       json={"keep_last": 0, "api_key": master}).status_code == 422


def test_r852_tool_registered_read_only(env):
    from tool_registry import get_registry
    reg = get_registry()
    assert "ledger.retention" in reg._tools
    res = reg.invoke("ledger.retention", caller="owner", inputs={})
    assert res["ok"] and "archive" in res["result"] and res["result"]["auto"] is False
