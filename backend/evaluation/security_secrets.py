# -*- coding: utf-8 -*-
"""R-848: مجموعة حارس الأسرار — سيناريوهات فوق المكونات الحقيقية.

حقيقي هنا: الكتالوج، والمنقيات الأربع وقت التشغيل، وصانع أحداث الإشعار، والبوابة
``tools/gate_secrets.py`` (عملية فرعية فعلية على مستودع git مؤقت)، وإعداد gitleaks،
وملفا CI والـhook. لا قيم سرية حرفية: كل مادة تُركَّب من قطع ببذرة ثابتة لكل حالة.

دروس سابقة مطبقة: المقارنة بقيم دقيقة لا بحث في نص كبير (O03)، وكل سيناريو يصل
فعلًا إلى المسار الذي يقيسه (O13): البوابة تُستدعى كعملية كما في CI.
"""
from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List

try:
    from secret_guard import catalog
    from observability.redact import redact as obs_redact
    from notifications import events as nev
    from job_queue.worker import scrub as worker_scrub
    from agent_orchestrator.tracing import scrub as trace_scrub
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.secret_guard import catalog
    from backend.observability.redact import redact as obs_redact
    from backend.notifications import events as nev
    from backend.job_queue.worker import scrub as worker_scrub
    from backend.agent_orchestrator.tracing import scrub as trace_scrub

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "tools" / "gate_secrets.py"

_UP = string.ascii_uppercase + string.digits
_AL = string.ascii_letters + string.digits


def _b64u(o: Any) -> str:
    return base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()


def build(spec: List[List[Any]], rnd: random.Random) -> str:
    out = []
    for part in spec:
        kind = part[0]
        if kind == "lit":
            out.append(part[1])
        elif kind == "alnum":
            out.append("".join(rnd.choice(_AL) for _ in range(part[1])))
        elif kind == "mixed":   # حرف ورقم مضمونان
            s = [rnd.choice(string.ascii_letters), rnd.choice(string.digits)]
            s += [rnd.choice(_AL) for _ in range(part[1] - 2)]
            rnd.shuffle(s)
            out.append("".join(s))
        elif kind == "hex":
            out.append("".join(rnd.choice("0123456789abcdef") for _ in range(part[1])))
        elif kind == "upnum":
            out.append("".join(rnd.choice(_UP) for _ in range(part[1])))
        elif kind == "digits":
            out.append(str(rnd.randint(1, 9)) + "".join(rnd.choice(string.digits) for _ in range(part[1] - 1)))
        elif kind == "b64":
            out.append(base64.b64encode(bytes(rnd.getrandbits(8) for _ in range(part[1]))).decode())
        elif kind == "rep":
            out.append(part[1] * part[2])
        elif kind == "uuid":
            out.append(str(uuid.UUID(int=rnd.getrandbits(128), version=4)))
        elif kind == "jwt":
            out.append(_b64u({"alg": "HS256", "typ": "JWT"}) + "." + _b64u(part[1]) + "."
                       + "".join(rnd.choice(_AL + "_-") for _ in range(43)))
        else:
            raise ValueError(f"قطعة مجهولة: {kind}")
    return "".join(out)


def _rnd(case: Dict[str, Any]) -> random.Random:
    return random.Random(int(hashlib.sha256(case["id"].encode()).hexdigest()[:12], 16))


# ---------------------------------------------------------------- مستودع مؤقت

class _Repo:
    def __init__(self, tmp: Path):
        self.d = tmp / "repo"
        self.d.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "eval@example.invalid")
        self.git("config", "user.name", "eval")
        self.git("config", "commit.gpgsign", "false")
        (self.d / "README").write_text("base\n")
        self.commit("base")

    def git(self, *a: str) -> str:
        p = subprocess.run(["git", *a], cwd=self.d, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"git {a[0]}: {p.stderr[:200]}")
        return p.stdout.strip()

    def write(self, rel: str, data) -> None:
        p = self.d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            p.write_bytes(data)
        else:
            p.write_text(data, encoding="utf-8")

    def commit(self, msg: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", msg)
        return self.git("rev-parse", "HEAD")


def _gate(repo: _Repo, *args: str, baseline: Path) -> Dict[str, Any]:
    out_json = repo.d.parent / f"gate-{uuid.uuid4().hex[:8]}.json"
    p = subprocess.run([sys.executable, str(GATE), "--repo", str(repo.d), "--baseline", str(baseline),
                        "--json", str(out_json), *args], capture_output=True, text=True, timeout=120)
    rep = json.loads(out_json.read_text(encoding="utf-8")) if out_json.exists() else {}
    return {"exit": p.returncode, "out": p.stdout + p.stderr, "report": rep}


def _empty_baseline(tmp: Path) -> Path:
    b = tmp / "baseline.json"
    b.write_text(json.dumps({"entries": []}), encoding="utf-8")
    return b


# ---------------------------------------------------------------- السيناريوهات

def s_detect(case, tmp):
    v = build(case["material"], _rnd(case))
    return {"rules": [h.rule for h in catalog.find(f"config = {v}\n" if "\n" in v else f"x {v} y")]}


def s_negatives(case, tmp):
    rnd = _rnd(case)
    return {"hits": sum(len(catalog.find(build(m, rnd))) for m in case["materials"])}


def s_short_token(case, tmp):
    v = build(case["material"], _rnd(case))
    return {"scan_hits": len(catalog.find(f"t = {v}")), "redacted": v not in obs_redact(f"t = {v}")}


_SCRUBBERS: Dict[str, Callable[[str], Any]] = {
    "observability.redact": obs_redact, "notifications.scrub": nev.scrub,
    "job_queue.worker.scrub": worker_scrub, "tracing.scrub": trace_scrub}


def s_runtime_redaction(case, tmp):
    rnd = _rnd(case)
    checked = leaks = 0
    for m in case["materials"]:
        v = build(m, rnd)
        for fn in _SCRUBBERS.values():
            checked += 1
            out = str(fn(f"upstream said: {v} (retry later)"))
            leaks += int(v[:16] in out or v[-16:] in out)
    return {"checked": checked, "leaks": leaks}


def s_kv_redaction(case, tmp):
    rnd = _rnd(case)
    checked = leaks = 0
    for m in case["materials"]:
        line = build(m, rnd)
        val = re.split(r"[=:]\s*", line, maxsplit=1)[1]
        for fn in (obs_redact, nev.scrub, worker_scrub):
            checked += 1
            leaks += int(val in fn(f"connect failed {line} host=db"))
    return {"checked": checked, "leaks": leaks}


def s_notification_event(case, tmp):
    v = build(case["material"], _rnd(case))
    ev = nev.make("backup.failed", f"k:{uuid.uuid4().hex}", f"bk {v}", f"failed {v}", f"trace {v}")
    return {"leaks": sum(int(v in str(ev.get(f, ""))) for f in ("subject", "summary", "body", "title"))}


def s_gate_commit_added(case, tmp):
    v = build(case["material"], _rnd(case))
    r = _Repo(tmp)
    base = r.git("rev-parse", "HEAD")
    r.write("app/settings.py", f'RENDER = "{v}"\n')
    head = r.commit("add settings")
    g = _gate(r, "--range", base, head, baseline=_empty_baseline(tmp))
    return {"exit": g["exit"], "rules": [x["rule"] for x in g["report"].get("new", [])],
            "value_in_output": v in g["out"] or v in json.dumps(g["report"])}


def s_gate_commit_removed(case, tmp):
    v = build(case["material"], _rnd(case))
    r = _Repo(tmp)
    r.write("cfg.txt", f"keep\nsupabase {v}\n")
    base = r.commit("old leak (already reported at its time)")
    r.write("cfg.txt", "keep\n")
    head = r.commit("remove secret")
    return {"exit": _gate(r, "--range", base, head, baseline=_empty_baseline(tmp))["exit"]}


def s_gate_commit_message(case, tmp):
    v = build(case["material"], _rnd(case))
    r = _Repo(tmp)
    base = r.git("rev-parse", "HEAD")
    r.write("a.txt", "harmless\n")
    head = r.commit(f"debug: used {v} to test")
    g = _gate(r, "--range", base, head, baseline=_empty_baseline(tmp))
    return {"exit": g["exit"], "paths": sorted({x["path"] for x in g["report"].get("new", [])})}


def s_gate_baseline_exact(case, tmp):
    v = build(case["material"], _rnd(case))
    r = _Repo(tmp)
    base = r.git("rev-parse", "HEAD")
    r.write("fixtures/upstream.txt", f"aws {v}\n")
    head = r.commit("vendored upstream fixture")
    found = _gate(r, "--range", base, head, baseline=_empty_baseline(tmp))["report"]["new"]
    b = tmp / "bl.json"
    b.write_text(json.dumps({"entries": [{"rule": f["rule"], "path": f["path"], "fingerprint": f["fingerprint"],
                                          "reason": "مراجعة: مادة مصدر خارجي"} for f in found]}), encoding="utf-8")
    same = _gate(r, "--range", base, head, baseline=b)["exit"]
    r.write("app/real.py", f"KEY = '{v}'\n")
    head2 = r.commit("copy elsewhere")
    other = _gate(r, "--range", head, head2, baseline=b)["exit"]
    return {"same_path_exit": same, "other_path_exit": other}


def s_gate_baseline_invalid(case, tmp):
    r = _Repo(tmp)
    head = r.git("rev-parse", "HEAD")
    good = {"rule": "jwt", "path": "a.txt", "fingerprint": "0" * 24, "reason": "سبب كافٍ للمراجعة"}
    res = {}
    for name, entry in (("glob_exit", {**good, "path": "third_party/*"}),
                        ("no_reason_exit", {**good, "reason": ""}),
                        ("unknown_rule_exit", {**good, "rule": "not_a_rule"})):
        b = tmp / f"{name}.json"
        b.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
        res[name] = _gate(r, head, baseline=b)["exit"]
    return res


def s_gate_tree_stale(case, tmp):
    r = _Repo(tmp)
    b = tmp / "bl.json"
    b.write_text(json.dumps({"entries": [{"rule": "jwt", "path": "README", "fingerprint": "f" * 24,
                                          "reason": "إدخال قديم لم يعد يطابق شيئًا"}]}), encoding="utf-8")
    g = _gate(r, "--tree", baseline=b)
    return {"exit": g["exit"], "stale": len(g["report"].get("stale", []))}


def s_gate_binary_mixed(case, tmp):
    v = build(case["material"], _rnd(case))
    r = _Repo(tmp)
    base = r.git("rev-parse", "HEAD")
    r.write("blob.bin", b"\x00\x01\x02" + v.encode() + b"\x00" * 64)
    r.write("notes.md", f"key {v}\n")
    head = r.commit("binary + text")
    g = _gate(r, "--range", base, head, baseline=_empty_baseline(tmp))
    return {"exit": g["exit"], "hits": len(g["report"].get("new", []))}


def s_gitleaks_config(case, tmp):
    import tomllib
    cfg = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    rules = cfg.get("rules", [])
    rnd = _rnd(case)
    matched = 0
    for m, rule in zip(case["materials"], rules):
        v = build(m, rnd)
        matched += int(bool(re.search(rule["regex"], f"value: {v} end")))
    return {"use_default": bool(cfg.get("extend", {}).get("useDefault")), "custom_rules_match": matched}


def s_ci_wiring(case, tmp):
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    hook = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    ver = re.search(r'GITLEAKS_VERSION:\s*"([0-9.]+)"', ci)
    sha = re.search(r'GITLEAKS_SHA256:\s*"([0-9a-f]{64})"', ci)
    return {"gate_range": 'tools/gate_secrets.py --range "${BASE}" "${GITHUB_SHA}"' in ci,
            "gitleaks_pinned": bool(ver) and "releases/download/v${GITLEAKS_VERSION}/" in ci,
            "sha256_verified": bool(sha) and 'sha256sum -c -' in ci,
            "hook_staged": "tools/gate_secrets.py\" --staged || exit 1" in hook}


SCENARIOS = {f.__name__[2:]: f for f in (
    s_detect, s_negatives, s_short_token, s_runtime_redaction, s_kv_redaction,
    s_notification_event, s_gate_commit_added, s_gate_commit_removed, s_gate_commit_message,
    s_gate_baseline_exact, s_gate_baseline_invalid, s_gate_tree_stale, s_gate_binary_mixed,
    s_gitleaks_config, s_ci_wiring)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r848-s-"))
    try:
        try:
            got = SCENARIOS[case["scenario"]](case, tmp)
        except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
            got = {"error": f"{type(exc).__name__}: {catalog.redact(exc)}"}
        exp = case["expect"]
        failed = [{"check": k, "want": v, "got": got.get(k)} for k, v in exp.items() if got.get(k) != v]
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
