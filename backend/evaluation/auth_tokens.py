# -*- coding: utf-8 -*-
"""R-851: مجموعة مجمّدة auth.scoped_tokens — رموز محدودة النطاق (٦.٧.٢).

كل سيناريو يبني TokenManager معزولًا (مفتاح ثابت، ساعة يتحكم بها، مخزن مزيف،
سجل مزيف). التوقعات في data/auth_tokens_cases.json مكتوبة من القاعدة قبل أول
تشغيل ومجمّدة ببصمة sha256 (suites.py).
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import scoped_tokens as st  # noqa: E402

KEY = b"k" * 32


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


class Store:
    def __init__(self):
        self.blobs: Dict[str, Dict[str, Any]] = {}
        self.down = False

    def save_blob(self, ns, key, payload):
        if self.down:
            return False
        self.blobs[f"{ns}/{key}"] = json.loads(json.dumps(payload))
        return True

    def list_blobs(self, ns, limit=1000, offset=0):
        if self.down:
            return None
        return [{"key": k.split("/", 1)[1], "payload": v}
                for k, v in sorted(self.blobs.items()) if k.startswith(ns + "/")]


class Audit:
    def __init__(self, fail=False):
        self.events: List[Any] = []
        self.fail = fail

    def __call__(self, event, payload):
        if self.fail:
            raise RuntimeError("ledger not signing")
        self.events.append((event, payload))


def _mgr(tmp, *, store=None, clock=None, audit=None, key=KEY):
    return st.TokenManager(tmp, key=key, store=store, audit=audit or Audit(),
                           clock=clock or Clock())


# ---------------------------------------------------------------- السيناريوهات
def s_own_scope(tmp):
    m = _mgr(tmp)
    t = m.issue(["read"], 3600, "phone")
    return {"ok": m.check(t["token"], "read")["ok"], "scopes": t["scopes"],
            "prefix": t["token"].split(".")[0]}


def s_other_scope(tmp):
    m = _mgr(tmp)
    t = m.issue(["read"], 3600)["token"]
    return {"tools": m.check(t, "tools")["reason"], "skills": m.check(t, "skills.approve")["reason"]}


def s_expired(tmp):
    c = Clock()
    m = _mgr(tmp, clock=c)
    t = m.issue(["chat"], 60)["token"]
    before = m.check(t, "chat")["ok"]
    c.t += 60
    return {"before": before, "after": m.check(t, "chat")["reason"]}


def s_revoked(tmp):
    m = _mgr(tmp)
    t = m.issue(["tools"], 3600)
    r = m.revoke(t["jti"])
    return {"reason": m.check(t["token"], "tools")["reason"], "known": r["known"],
            "again": m.revoke(t["jti"])["already"]}


def s_tampered_claims(tmp):
    m = _mgr(tmp)
    tok = m.issue(["read"], 3600)["token"]
    p, body, sig = tok.split(".")
    claims = json.loads(st._b64d(body))
    claims["scp"] = sorted(st.SCOPES)
    forged = ".".join([p, st._b64e(json.dumps(claims, separators=(",", ":"),
                                              sort_keys=True).encode()), sig])
    return {"reason": m.check(forged, "tools")["reason"]}


def s_foreign_key(tmp):
    other = _mgr(tmp / "o", key=b"z" * 32).issue(["read"], 3600)["token"]
    return {"reason": _mgr(tmp).check(other, "read")["reason"]}


def s_master_only(tmp):
    m = _mgr(tmp)
    t = m.issue(sorted(st.SCOPES), 3600)["token"]
    out = {"admin_check": m.check(t, "admin")["reason"],
           "reset_check": m.check(t, "sovereign.reset")["reason"]}
    try:
        m.issue(["admin"], 3600)
        out["admin_issue"] = "accepted"
    except st.TokenError:
        out["admin_issue"] = "rejected"
    return out


def s_ttl_bounds(tmp):
    m = _mgr(tmp)
    rejected = 0
    for bad in (59, st.MAX_TTL + 1, True, "60", 0, -5):
        try:
            m.issue(["read"], bad)
        except st.TokenError:
            rejected += 1
    ok = [bool(m.issue(["read"], v)["token"]) for v in (st.MIN_TTL, st.MAX_TTL)]
    return {"rejected": rejected, "edges_ok": ok}


def s_empty_scopes(tmp):
    m = _mgr(tmp)
    res = []
    for bad in ([], ["read", "nope"], None):
        try:
            m.issue(bad, 3600)
            res.append("accepted")
        except st.TokenError:
            res.append("rejected")
    return {"results": res}


def s_malformed(tmp):
    m = _mgr(tmp)
    return {"reasons": [m.check(x, "read")["reason"] for x in
                        ("", "sct1.x", "abc.def.ghi", "sct1." + "a" * 3000, "sct1.!!.??", None, 42)]}


def s_revocation_durable(tmp):
    store = Store()
    m1 = _mgr(tmp / "a", store=store)
    t = m1.issue(["read"], 3600)
    rv = m1.revoke(t["jti"])
    m2 = _mgr(tmp / "b", store=store)          # إعادة نشر: قرص محلي جديد فارغ
    before = m2.check(t["token"], "read")["reason"]
    loaded = m2.load_remote()["loaded"]
    return {"durable": rv["durable"], "before_load": before, "loaded": loaded,
            "after_load": m2.check(t["token"], "read")["reason"]}


def s_fail_closed(tmp):
    store, c = Store(), Clock()
    m1 = _mgr(tmp / "a", store=store, clock=c)
    tok = m1.issue(["read"], 3600)["token"]
    store.down = True
    m2 = _mgr(tmp / "b", store=store, clock=c)
    first = m2.load_remote()["loaded"]
    down = m2.check(tok, "read")["reason"]
    store.down = False
    c.t += 10
    still = m2.check(tok, "read")["reason"]     # قبل مضي 30 ثانية: لا إعادة محاولة
    c.t += 30
    return {"first_load": first, "down": down, "within_30s": still,
            "recovered": m2.check(tok, "read")["ok"]}


def s_audit_fail(tmp):
    m = _mgr(tmp, audit=Audit(fail=True))
    try:
        m.issue(["read"], 3600)
        raised = False
    except RuntimeError:
        raised = True
    return {"raised": raised, "issued": len(m.list())}


def s_secret_not_stored(tmp):
    store = Store()
    m = _mgr(tmp, store=store)
    t = m.issue(["read", "chat"], 3600, "laptop")
    sig = t["token"].split(".")[2]
    local = (tmp / "auth" / "tokens.json").read_text(encoding="utf-8")
    remote = json.dumps(store.blobs)
    aud = json.dumps(m.audit.events)
    return {"in_local": sig in local, "in_store": sig in remote, "in_audit": sig in aud,
            "jti_in_audit": t["jti"] in aud}


def s_secret_guard(tmp):
    from secret_guard.catalog import redact, find
    tok = _mgr(tmp).issue(["read"], 3600)["token"]
    red = redact(f"leaked {tok} here")
    return {"detected": any(f.rule == "sovereign_scoped_token" for f in find(tok)),
            "redacted": tok not in red}


def s_list_states(tmp):
    c = Clock()
    m = _mgr(tmp, clock=c)
    m.issue(["read"], 60)
    b = m.issue(["chat"], 3600)
    m.issue(["tools"], 7200)
    m.revoke(b["jti"])
    c.t += 120
    return {"tokens": m.status()["tokens"]}


def s_introspect(tmp):
    m = _mgr(tmp)
    t = m.issue(["skills", "read"], 3600)
    ok = m.introspect(t["token"])
    m.revoke(t["jti"])
    return {"valid": ok["valid"], "scopes": ok["scopes"],
            "after_revoke": m.introspect(t["token"]).get("reason")}


def s_local_restart(tmp):
    m1 = _mgr(tmp)
    t = m1.issue(["read"], 3600)
    m1.revoke(t["jti"])
    m2 = _mgr(tmp)                              # نفس القرص، بلا مخزن دائم
    return {"reason": m2.check(t["token"], "read")["reason"],
            "loaded": m2.status()["revocations_loaded"]}


def s_unknown_scope_check(tmp):
    m = _mgr(tmp)
    t = m.issue(["read"], 3600)["token"]
    return {"reason": m.check(t, "read.everything")["reason"]}


def s_scope_catalog(tmp):
    s = _mgr(tmp).status()
    return {"scopes": sorted(s["scopes"]), "master_only_count": len(s["master_only"]),
            "ttl": [s["ttl_seconds"]["min"], s["ttl_seconds"]["max"]]}


SCENARIOS = {f.__name__[2:]: f for f in (
    s_own_scope, s_other_scope, s_expired, s_revoked, s_tampered_claims, s_foreign_key,
    s_master_only, s_ttl_bounds, s_empty_scopes, s_malformed, s_revocation_durable,
    s_fail_closed, s_audit_fail, s_secret_not_stored, s_secret_guard, s_list_states,
    s_introspect, s_local_restart, s_unknown_scope_check, s_scope_catalog)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r851-e-"))
    try:
        try:
            got = SCENARIOS[case["scenario"]](tmp)
        except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
            got = {"error": f"{type(exc).__name__}: {exc}"}
        failed = [{"check": k, "want": v, "got": got.get(k)}
                  for k, v in case["expect"].items() if got.get(k) != v]
        return {"id": case["id"], "rule": case["rule"], "pass": not failed,
                "got": got, "failed_checks": failed}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [run_case(c) for c in cases]
    passed = sum(r["pass"] for r in results)
    return {"score": round(passed / len(results), 4) if results else 0.0,
            "passed": passed, "n": len(results),
            "failures": [r for r in results if not r["pass"]]}
