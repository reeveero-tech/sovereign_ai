"""R-745 (البند ٤.٥ — التحسين بموافقة): اقتراح → موافقة مالك → التزام ذري.

«لا تطوير ذاتي غير مقيّد بموافقة المالك». لذلك:
1. الاقتراح يُولَّد من العيوب المفتوحة (٤.٣) بدليلها، بمعرّف ثابت ولا تكرار.
2. ما يصطدم بقرار مالك يُحجب بسببه لا يُقترح (المادة ٦): نبض الحارس ← ٤.٧.
3. دليل R-635 ← اقتراح «إجراء مالك» لا إصلاح كود.
4. آلة حالات صارمة: proposed → approved|rejected (المالك) → implemented
   (فقط من approved وبرقم التزام صالح). المرفوض لا يُعاد اقتراحه.
5. لا تعديل ذاتي: الوحدة لا تكتب ملفات ولا تشغّل أوامر ولا تلمس git.
6. ملف التوصية (markdown) يحمل الدليل وقائمة الدورة الذرية.
7. حلقة حقيقية: defects.scan → اقتراحات في /proposals؛ القرار عبر
   /tools/invoke (proposals.decide) بمفتاح المالك فقط وبأثر موقّع.
"""

import importlib
import os
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _report(*defects):
    return {"defects": [{"id": i, "status": "open", "severity": sev, "area": "x",
                         "title": i, "evidence": ev} for i, sev, ev in defects]}


@pytest.fixture
def ip():
    import improvement_proposals
    importlib.reload(improvement_proposals)
    return improvement_proposals


def test_proposals_from_open_defects_stable_and_deduped(ip):
    book = ip.ProposalBook()
    rep = _report(("component_unhealthy:core", "high", "status=unhealthy error=boom"))
    book.ingest(rep, now=1.0)
    book.ingest(rep, now=2.0)
    items = book.list()
    assert len(items) == 1
    p = items[0]
    assert p["defect_id"] == "component_unhealthy:core"
    assert p["status"] == "proposed" and p["evidence"] == "status=unhealthy error=boom"
    assert re.fullmatch(r"P-[0-9a-f]{8}", p["id"])
    assert ip.ProposalBook().ingest(rep, now=1.0)[0]["id"] == p["id"], "المعرّف ثابت"


def test_owner_decision_conflict_is_suppressed_with_reason(ip):
    book = ip.ProposalBook()
    book.ingest(_report(("supervisor_heartbeat_missing", "low", "غائب")), now=1.0)
    p = book.list()[0]
    assert p["status"] == "suppressed"
    assert "٤.٧" in p["suppressed_reason"]


def test_signing_key_evidence_becomes_owner_action(ip):
    book = ip.ProposalBook()
    book.ingest(_report(("scheduled_task_failed:self_health_check", "medium",
                         "RuntimeError: R-635: No active signing key")), now=1.0)
    p = book.list()[0]
    assert p["kind"] == "owner_action" and "R-635" in p["recommendation"]


def test_state_machine_is_strict(ip):
    book = ip.ProposalBook()
    book.ingest(_report(("component_unhealthy:core", "high", "e")), now=1.0)
    pid = book.list()[0]["id"]
    with pytest.raises(ValueError):
        book.decide(pid, "implemented", commit="abc1234", now=2.0)  # قبل الموافقة
    with pytest.raises(ValueError):
        book.decide(pid, "bogus", now=2.0)
    with pytest.raises(KeyError):
        book.decide("P-00000000", "approved", now=2.0)
    p = book.decide(pid, "approved", note="نفّذ", now=3.0)
    assert p["status"] == "approved" and p["decided_at"] == 3.0
    with pytest.raises(ValueError):
        book.decide(pid, "implemented", commit="not-a-sha", now=4.0)
    p = book.decide(pid, "implemented", commit="f36c99b", now=5.0)
    assert p["status"] == "implemented" and p["commit"] == "f36c99b"
    assert [h["to"] for h in p["history"]] == ["proposed", "approved", "implemented"]


def test_rejected_is_not_reproposed(ip):
    book = ip.ProposalBook()
    rep = _report(("component_unhealthy:core", "high", "e"))
    book.ingest(rep, now=1.0)
    pid = book.list()[0]["id"]
    book.decide(pid, "rejected", note="لا", now=2.0)
    book.ingest(rep, now=3.0)
    assert book.list()[0]["status"] == "rejected"
    assert len(book.list()) == 1


def test_module_has_no_self_modification_paths():
    src = (BACKEND / "improvement_proposals.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    code = re.sub(r'""".*?"""', "", code, flags=re.S)
    for forbidden in ("subprocess", "os.system", "open(", "write_text", "Popen",
                      "exec(", "eval(", "git ", "shutil"):
        assert forbidden not in code, f"مسار تعديل ذاتي محظور: {forbidden}"


def test_recommendation_file_carries_evidence_and_atomic_checklist(ip):
    book = ip.ProposalBook()
    book.ingest(_report(("component_unhealthy:core", "high", "status=unhealthy")), now=1.0)
    pid = book.list()[0]["id"]
    md = book.render_markdown(pid)
    assert md.startswith(f"# {pid}")
    assert "status=unhealthy" in md
    for must in ("RED", "verify.sh --full", "PROJECT_STATE", "CHANGELOG", "DELETION-JUSTIFIED"):
        assert must in md, must


def _key():
    return os.environ.get("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


def test_real_loop_scan_propose_owner_decides_signed(monkeypatch):
    from fastapi.testclient import TestClient
    import app as app_module
    import tool_registry
    import defect_scan
    import improvement_proposals
    monkeypatch.setattr(app_module, "_health_payload", lambda: {
        "status": "degraded",
        "components": {"core": {"status": "unhealthy", "error": "r745"}}})
    with TestClient(app_module.app) as client:
        monkeypatch.setattr(defect_scan, "_WORKLIST", defect_scan.DefectWorklist())
        monkeypatch.setattr(improvement_proposals, "_BOOK", improvement_proposals.ProposalBook())
        assert tool_registry.get_registry().invoke("defects.scan", caller="test")["ok"]
        items = client.get("/proposals").json()["proposals"]
        p = next(i for i in items if i["defect_id"] == "component_unhealthy:core")
        assert p["status"] == "proposed"

        bad = client.post("/tools/invoke", json={
            "tool": "proposals.decide", "api_key": "wrong",
            "inputs": {"proposal_id": p["id"], "decision": "approved"}})
        assert bad.status_code == 401
        still = next(i for i in client.get("/proposals").json()["proposals"]
                     if i["id"] == p["id"])
        assert still["status"] == "proposed", "مفتاح خاطئ لا يغيّر الحالة"

        ok = client.post("/tools/invoke", json={
            "tool": "proposals.decide", "api_key": _key(),
            "inputs": {"proposal_id": p["id"], "decision": "approved", "note": "اختبار"}})
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["ok"] is True and body["trace"]["result_fingerprint"]
        assert body["result"]["status"] == "approved"

        f = client.get(f"/proposals/{p['id']}/file")
        assert f.status_code == 200 and "text/markdown" in f.headers["content-type"]
        assert "approved" in f.text
        assert client.get("/proposals/P-00000000/file").status_code == 404


def test_decision_not_applied_when_ledger_cannot_sign(monkeypatch):
    """لا أثر = لا تنفيذ: أداة تغيّر حالة لا تطبّق القرار إن رفض السجل التوقيع.

    كشف R-745: ToolRegistry.invoke ينفّذ المعالج قبل كتابة الأثر — مقبول
    لأدوات القراءة، لكنه يترك قرارًا مطبّقًا بلا أثر. الحل: مرحلتان
    (handler يحضّر، apply يطبّق بعد نجاح الأثر الموقّع)."""
    import improvement_proposals
    import tool_registry
    from fastapi.testclient import TestClient
    import app as app_module
    with TestClient(app_module.app):
        book = improvement_proposals.ProposalBook()
        monkeypatch.setattr(improvement_proposals, "_BOOK", book)
        book.ingest(_report(("component_unhealthy:core", "high", "e")), now=1.0)
        pid = book.list()[0]["id"]
        import memory.core as mc

        class _Refusing:
            def append_event(self, *a, **k):
                raise RuntimeError("R-635: No active signing key (محاكاة)")

        monkeypatch.setattr(mc, "get_core", lambda: _Refusing())
        with pytest.raises(RuntimeError):
            tool_registry.get_registry().invoke(
                "proposals.decide", caller="owner",
                inputs={"proposal_id": pid, "decision": "approved"})
        assert book.get(pid)["status"] == "proposed", "قرار طُبّق بلا أثر موقّع"
