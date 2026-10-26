"""R-774 (ROADMAP_V6 ٦.١.١) — مراقب خارجي لـ/health يعمل من خارج Fly ويفتح Issue عند العطل.

السبب: انقطاع R-770 (OOM عند كل إقلاع منذ 2026-10-25T17:18Z) لم يُكتشف ~6 ساعات —
لا شيء يراقب الإنتاج من خارجه. المراقب: GitHub Actions مجدول كل 15 دقيقة (مصدر
مستقل عن Fly — المادة الخاصة بالتحقق من /health من مصدر مستقل)، يحكم على الاستجابة،
ويفتح Issue واحدة موسومة عند العطل، ويعلّق عند استمراره، ويغلقها عند التعافي.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import yaml

from tools import uptime_monitor as um

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows" / "uptime.yml"


def _serve(status, body, delay=0.0):
    import time

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(delay)
            raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/health"


def test_healthy_200_is_up():
    srv, url = _serve(200, {"status": "healthy"})
    try:
        r = um.probe(url, timeout=5)
    finally:
        srv.shutdown()
    assert r["ok"] is True and r["http"] == 200 and r["status"] == "healthy"


def test_degraded_is_down_even_with_200():
    # R-766: /health أعاد 200 بحالة degraded و~20 مكونًا معطلًا — هذا عطل.
    srv, url = _serve(200, {"status": "degraded"})
    try:
        r = um.probe(url, timeout=5)
    finally:
        srv.shutdown()
    assert r["ok"] is False and r["status"] == "degraded"


def test_5xx_and_non_json_are_down():
    srv, url = _serve(502, "bad gateway")
    try:
        r = um.probe(url, timeout=5)
    finally:
        srv.shutdown()
    assert r["ok"] is False and r["http"] == 502


def test_timeout_is_down():
    srv, url = _serve(200, {"status": "healthy"}, delay=2.0)
    try:
        r = um.probe(url, timeout=0.5)
    finally:
        srv.shutdown()
    assert r["ok"] is False and r["http"] is None and r["error"]


def test_unreachable_is_down():
    r = um.probe("http://127.0.0.1:9/health", timeout=1)
    assert r["ok"] is False and r["error"]


def test_decide_opens_once_comments_while_down_closes_on_recovery():
    assert um.decide(ok=False, open_issue=None) == "open"
    assert um.decide(ok=False, open_issue=17) == "comment"
    assert um.decide(ok=True, open_issue=17) == "close"
    assert um.decide(ok=True, open_issue=None) is None


def test_confirms_failure_with_retry_before_alerting():
    calls = []

    def fake(url, timeout):
        calls.append(1)
        return {"ok": len(calls) >= 2, "http": 200, "status": "healthy", "error": None, "seconds": 0.1}

    r = um.probe_confirmed("http://x/health", timeout=1, attempts=3, pause=0, probe_fn=fake)
    assert r["ok"] is True and r["attempts"] == 2


def test_workflow_is_scheduled_every_15_minutes_with_minimal_permissions():
    wf = yaml.safe_load(WF.read_text(encoding="utf-8"))
    on = wf.get("on", wf.get(True))
    assert {"cron": "7,22,37,52 * * * *"} in on["schedule"]  # R-776: كل 15 دقيقة بدقائق غير دائرية
    assert "workflow_dispatch" in on
    assert wf["permissions"] == {"issues": "write", "contents": "read"}
    text = WF.read_text(encoding="utf-8")
    assert "python tools/uptime_monitor.py" in text
    assert "secrets." not in text.replace("secrets.GITHUB_TOKEN", "")
