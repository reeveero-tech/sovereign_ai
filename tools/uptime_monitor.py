#!/usr/bin/env python3
"""R-774 (ROADMAP_V6 ٦.١.١) — مراقب خارجي لـ/health على الإنتاج.

يعمل من GitHub Actions (مصدر مستقل عن Fly) كل 15 دقيقة:
- يفحص `/health` ويعيد المحاولة قبل الإنذار (لا إنذار من خطأ شبكة عابر).
- «سليم» = HTTP 200 + JSON + `status == "healthy"`؛ `degraded` عطل (حادثة R-766).
- عطل ولا Issue مفتوحة بالوسم → يفتح واحدة؛ عطل مستمر → تعليق؛ تعافٍ → تعليق + إغلاق.
- الحالة في GitHub Issues وحدها (لا ملف حالة، لا سر غير GITHUB_TOKEN).

الاستخدام: python tools/uptime_monitor.py [--url URL] [--dry-run]
رمز الخروج: 0 سليم، 1 عطل (فيظهر التشغيل أحمر في Actions أيضًا).
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = "https://sovereign-ai-k20elq.fly.dev/health"
LABEL = "uptime-incident"


def probe(url, timeout=20.0):
    t0 = time.monotonic()
    out = {"ok": False, "http": None, "status": None, "error": None, "seconds": None}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "sovereign-uptime/1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out["http"] = r.status
            raw = r.read(65536)
    except urllib.error.HTTPError as e:
        out["http"] = e.code
        out["error"] = f"HTTP {e.code}"
        out["seconds"] = round(time.monotonic() - t0, 3)
        return out
    except Exception as e:  # مهلة، رفض اتصال، DNS، TLS
        out["error"] = f"{type(e).__name__}: {e}"
        out["seconds"] = round(time.monotonic() - t0, 3)
        return out
    out["seconds"] = round(time.monotonic() - t0, 3)
    try:
        body = json.loads(raw.decode("utf-8", "replace"))
        out["status"] = body.get("status") if isinstance(body, dict) else None
    except ValueError:
        out["error"] = "non-JSON body"
        return out
    out["ok"] = out["http"] == 200 and out["status"] == "healthy"
    if not out["ok"] and not out["error"]:
        out["error"] = f"status={out['status']!r}"
    return out


def probe_confirmed(url, timeout=20.0, attempts=3, pause=20.0, probe_fn=probe):
    r = {}
    for i in range(1, attempts + 1):
        r = probe_fn(url, timeout)
        r["attempts"] = i
        if r["ok"]:
            return r
        if i < attempts:
            time.sleep(pause)
    return r


def decide(ok, open_issue):
    if ok:
        return "close" if open_issue else None
    return "comment" if open_issue else "open"


def _gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def find_open_issue():
    out = _gh("issue", "list", "--label", LABEL, "--state", "open", "--json", "number", "--limit", "1")
    items = json.loads(out or "[]")
    return items[0]["number"] if items else None


def _summary(url, r):
    return (f"- URL: `{url}`\n- HTTP: `{r.get('http')}`\n- status: `{r.get('status')}`\n"
            f"- error: `{r.get('error')}`\n- seconds: `{r.get('seconds')}`\n"
            f"- attempts: `{r.get('attempts')}`\n- checked_at (UTC): `{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`\n"
            f"- run: {os.environ.get('RUN_URL', 'local')}")


def act(action, url, r, issue):
    if action == "open":
        _gh("label", "create", LABEL, "--color", "B60205", "--force",
            "--description", "R-774: /health فشل من مصدر خارجي")
        _gh("issue", "create", "--label", LABEL,
            "--title", f"الإنتاج متوقف: /health ({r.get('error') or r.get('status')})",
            "--body", "فشل `/health` من مصدر مستقل (GitHub Actions، R-774).\n\n" + _summary(url, r))
    elif action == "comment":
        _gh("issue", "comment", str(issue), "--body", "ما زال متوقفًا.\n\n" + _summary(url, r))
    elif action == "close":
        _gh("issue", "comment", str(issue), "--body", "تعافى `/health`.\n\n" + _summary(url, r))
        _gh("issue", "close", str(issue))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("UPTIME_URL") or DEFAULT_URL)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    r = probe_confirmed(a.url)
    issue = None if a.dry_run else find_open_issue()
    action = decide(r["ok"], issue)
    print(json.dumps({"url": a.url, "result": r, "open_issue": issue, "action": action}, ensure_ascii=False))
    if action and not a.dry_run:
        act(action, a.url, r, issue)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
