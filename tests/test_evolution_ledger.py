"""R-744 (البند ٤.٢ — سجل التطور): كل دورة تطور ذاتي تترك مدخلًا إلحاقيًا
قابلًا للتدقيق في جدول disk_log الإلحاقي (R-719).

الدورة الذاتية القائمة اليوم: defects.scan (R-743). كل دورة → مدخل:
ماذا اكتشف (opened) / ماذا زال (resolved) / أين كانت وأين صارت (open_before
→ open_after) / بأي دليل (report_fingerprint = بصمة السجل الموقّع نفسها).
وما غيّر: النظام لا يعدّل نفسه — changed=[] صادقًا.

1. مدخل لكل دورة — حتى بلا تغيير (لا دورة صامتة).
2. سلسلة تجزئة: prev_hash/entry_hash — العبث بأي مدخل يكشفه verify().
3. Supabase مفعّل → إلحاق في disk_log namespace=evolution (POST فقط، لا
   PATCH/DELETE أبدًا)؛ معطل → durable=False معلن لا ادعاء دوام.
4. قرص بعيد/رافض → المدخل يبقى مع cloud_error، والدورة لا تنهار.
5. حلقة حقيقية: defects.scan عبر السجل → مدخل بصمته = result_fingerprint
   في حدث tool_invoked الموقّع، ويظهر في /evolution/ledger بلا سر.
"""

import importlib
import json
import sys
from pathlib import Path

import httpx
import pytest

BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _report(open_ids, resolved_ids=(), n=1):
    defects = [{"id": i, "status": "open", "severity": "low"} for i in open_ids]
    defects += [{"id": i, "status": "resolved", "severity": "low"} for i in resolved_ids]
    return {"scans": n, "open_count": len(open_ids),
            "resolved_count": len(resolved_ids), "defects": defects,
            "generated_at": float(n)}


@pytest.fixture
def ev(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    import evolution_ledger
    importlib.reload(evolution_ledger)
    return evolution_ledger


def test_every_cycle_records_entry_even_without_change(ev):
    led = ev.EvolutionLedger(disk_factory=lambda: None)
    led.record_cycle("defects.scan", _report(["a"], n=1), now=1.0)
    e = led.record_cycle("defects.scan", _report(["a"], n=2), now=2.0)
    assert len(led.entries()) == 2
    assert e["discovered"] == [] and e["resolved"] == []
    assert e["open_before"] == 1 and e["open_after"] == 1
    assert e["changed"] == []


def test_entry_captures_discovered_resolved_before_after(ev):
    led = ev.EvolutionLedger(disk_factory=lambda: None)
    led.record_cycle("defects.scan", _report(["a", "b"], n=1), now=1.0)
    e = led.record_cycle("defects.scan", _report(["c"], ["a", "b"], n=2), now=2.0)
    assert e["discovered"] == ["c"]
    assert e["resolved"] == ["a", "b"]
    assert (e["open_before"], e["open_after"]) == (2, 1)
    assert len(e["report_fingerprint"]) == 16


def test_hash_chain_detects_tampering(ev):
    led = ev.EvolutionLedger(disk_factory=lambda: None)
    for n in range(1, 4):
        led.record_cycle("defects.scan", _report(["x"] if n % 2 else [], n=n), now=float(n))
    assert led.verify()["ok"] is True
    entries = led.entries()
    assert entries[1]["prev_hash"] == entries[0]["entry_hash"]
    led._entries[1]["open_after"] = 99  # عبث مقصود
    v = led.verify()
    assert v["ok"] is False and v["broken_at"] == 1


def test_disabled_cloud_is_declared_not_durable(ev):
    led = ev.EvolutionLedger(disk_factory=lambda: None)
    e = led.record_cycle("defects.scan", _report([]), now=1.0)
    assert e["durable"] is False
    assert led.status()["durable"] is False and "reason" in led.status()


def _disk(handler):
    from sovereign.cloud_disk import SupabaseDisk
    return SupabaseDisk("https://x.supabase.co", "sk_test_secret_value",
                        transport=httpx.MockTransport(handler))


def test_enabled_cloud_appends_only_to_disk_log(ev):
    seen = []

    def handler(req):
        seen.append((req.method, req.url.path, json.loads(req.content or b"{}")))
        return httpx.Response(201, json=[])

    disk = _disk(handler)
    led = ev.EvolutionLedger(disk_factory=lambda: disk)
    e = led.record_cycle("defects.scan", _report(["a"]), now=1.0)
    assert e["durable"] is True
    assert [(m, p) for m, p, _ in seen] == [("POST", "/rest/v1/disk_log")]
    body = seen[0][2]
    assert body["namespace"] == "evolution"
    assert body["payload"]["entry_hash"] == e["entry_hash"]
    assert "sk_test_secret_value" not in json.dumps(body)


def test_unreachable_cloud_keeps_entry_with_error(ev):
    def handler(req):
        raise httpx.ConnectError("down")

    led = ev.EvolutionLedger(disk_factory=lambda: _disk(handler))
    e = led.record_cycle("defects.scan", _report(["a"]), now=1.0)
    assert e["durable"] is False and e["cloud_error"]
    assert len(led.entries()) == 1


def test_real_loop_entry_matches_signed_trace():
    from fastapi.testclient import TestClient
    import app as app_module
    import tool_registry
    with TestClient(app_module.app) as client:
        before = len(client.get("/evolution/ledger").json()["entries"])
        out = tool_registry.get_registry().invoke("defects.scan", caller="test_r744")
        assert out["ok"] is True
        body = client.get("/evolution/ledger").json()
        assert len(body["entries"]) == before + 1
        last = body["entries"][-1]
        assert last["cycle"] == "defects.scan"
        assert last["report_fingerprint"] == out["trace"]["result_fingerprint"], (
            "بصمة المدخل يجب أن تطابق بصمة حدث tool_invoked الموقّع")
        assert body["verify"]["ok"] is True
        # لا قيمة سرية ولا ترويسة مصادقة (اسم المتغير في رسالة السبب مقبول —
        # يرشد المالك؛ القيمة لا تظهر أبدًا)
        import os
        text = json.dumps(body, ensure_ascii=False)
        for w in ("Bearer ", "apikey", "private_key", "service_key"):
            assert w not in text
        secret = os.getenv("SUPABASE_SECRET_KEY")
        if secret:
            assert secret not in text
