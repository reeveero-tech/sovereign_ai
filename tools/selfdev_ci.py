#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-796: منفّذ التطوير الذاتي في CI — يحوّل مسودات المحرك إلى فروع مختبرة RED→GREEN.

يعمل في GitHub Actions (.github/workflows/self-develop.yml) — بيئة معزولة مؤقتة،
لا في الإنتاج (D-041 قائم: الإنتاج لا يكتب ملفًا ولا ينفذ شيفرة).

لكل مهمة بحالة drafted لم تُختبر محاولتها بعد (من disk_log namespace «selfdev»):
  1. فرع work/selfdev-<id>-a<n> من origin/main.
  2. إعادة التحقق بنفس validate_draft (الملف تغيّر منذ الصياغة ⇒ stale).
  3. كتابة الاختبار في tests/selfdev/ وتشغيله على الكود الأصلي: يجب أن يفشل (RED).
  4. تطبيق التعديل وتشغيل الاختبار: يجب أن ينجح (GREEN).
  5. وثائق في نفس الالتزام (CHANGELOG/PROJECT_STATE/الخارطة النشطة) + تدقيق الحذف
     (DELETED_LINES_AUDIT + # DELETION-JUSTIFIED) إن استُبدلت أسطر.
  6. بوابة الحذف + بوابة الوثائق + المجموعة الكاملة.
  7. أخضر ⇒ دفع الفرع وتشغيل ci.yml عليه (دفع GITHUB_TOKEN لا يطلق CI تلقائيًا).
  8. النتيجة الحرفية (rc وذيل السجل) تُلحق بـ namespace «selfdev_ci» — المحرك يقرأها
     فيعيد الصياغة مع سبب الفشل أو ينتظر ترقية المالك.

الترقية إلى main: R-797 (قرار المالك 2026-10-28 «فعّل الترقية الآلية») — حين يكون متغير
المستودع SELFDEV_AUTO_PROMOTE='1': ينتظر CI أخضر على نفس بصمة الفرع ⇒ تقدم سريع فقط
إلى main (لا دمج/لا إعادة كتابة) ⇒ deploy-fly.yml (بوابة CI + فحص /health) ⇒ النتيجة
في السجل. قاطع دائرة: نشر آلي فاشل يوقف الترقيات حتى إعادة الضبط. بدون المتغير يرصد
المنفّذ فقط إن صارت بصمة الفرع في main (ترقية يدوية) فيسجل «promoted».

stdlib خالص (+ backend/self_develop.py للتحقق المشترك). اكتمال الدورة = خروج 0
(النتائج في السجل)؛ خلل تنفيذ = استثناء يحمرّ به التشغيل (لا مسار إنهاء صريح — R-686).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import self_develop as sd  # noqa: E402

TEST_DIR = "tests/selfdev"


class RestDisk:
    """disk_log عبر Supabase REST (نفس جدول sovereign/cloud_disk.py) — stdlib."""

    def __init__(self, url: str, key: str) -> None:
        self.base = url.rstrip("/") + "/rest/v1/disk_log"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"}

    def pull_log(self, ns: str, since_id: int = 0, limit: int = 1000) -> List[Dict[str, Any]]:
        q = urllib.parse.urlencode({"select": "id,payload,created_at", "namespace": f"eq.{ns}",
                                    "id": f"gt.{since_id}", "order": "id.asc",
                                    "limit": str(limit)})
        req = urllib.request.Request(f"{self.base}?{q}", headers=self.headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def append_log(self, ns: str, payload: Dict[str, Any]) -> bool:
        body = json.dumps({"namespace": ns, "payload": payload}).encode("utf-8")
        h = dict(self.headers, Prefer="return=minimal")
        req = urllib.request.Request(self.base, data=body, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status in (200, 201, 204)


def pull_all(disk, ns: str) -> List[Dict[str, Any]]:
    out, since = [], 0
    for _ in range(50):
        rows = disk.pull_log(ns, since_id=since, limit=1000) or []
        out.extend(rows)
        if rows:
            since = max(int(r.get("id") or 0) for r in rows)
        if len(rows) < 1000:
            break
    return out


def latest_tasks(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    tasks: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        t = (r.get("payload") or {}).get("task")
        if isinstance(t, dict) and t.get("id"):
            tasks[t["id"]] = t
    return tasks


def _run(cmd: List[str], cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(cmd, 124, exc.stdout or "", (exc.stderr or "") + "\nTIMEOUT")


def _git(repo: Path, *args: str, check: bool = True) -> str:
    r = _run(["git", *args], repo, timeout=120)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def _tail(r: subprocess.CompletedProcess, n: int = 1500) -> str:
    return ((r.stdout or "") + "\n" + (r.stderr or ""))[-n:]


def test_path(task: Dict[str, Any]) -> str:
    return f"{TEST_DIR}/test_selfdev_{task['id'][3:].lower()}_a{task.get('attempts', 1)}.py"


def branch_name(task: Dict[str, Any]) -> str:
    return f"work/selfdev-{task['id'][3:].lower()}-a{task.get('attempts', 1)}"


def test_file_content(task: Dict[str, Any]) -> str:
    d = task["draft"]
    return (f"# R-796 تطوير ذاتي: {task['id']} محاولة {task.get('attempts', 1)} — صاغه العقل؛ "
            "RED→GREEN مثبت بـ tools/selfdev_ci.py\n"
            "import sys as _sd_sys\n"
            "import pathlib as _sd_pathlib\n"
            "_sd_sys.path.insert(0, str(_sd_pathlib.Path(__file__).resolve().parents[2] / \"backend\"))\n\n"
            + d["test_code"].rstrip() + "\n")


def _insert_after_first_rule(text: str, block: str) -> str:
    marker = "\n---\n"
    i = text.find(marker)
    if i < 0:
        return text.rstrip("\n") + "\n\n" + block
    j = i + len(marker)
    return text[:j] + block + "\n---\n" + text[j:]


def write_docs(repo: Path, task: Dict[str, Any], red_rc: int, removed: List[str],
               today: str) -> None:
    d = task["draft"]
    tp, br = test_path(task), branch_name(task)
    tag = f"{task['id']} a{task.get('attempts', 1)}"
    deletion = (f"{len(removed)} سطرًا مستبدلًا — مدقق في forensics/DELETED_LINES_AUDIT.md"
                if removed else "صفر حذف")
    entry = (f"## [{tag}] — {today} — تطوير ذاتي: {d.get('summary') or task['title']}\n\n"
             f"- المصدر: {task.get('source')} ({task.get('ref') or '—'}) — المهمة: {task['title']}\n"
             f"- الملف: `{d['file']}`؛ الاختبار: `{tp}` — RED (rc={red_rc} على الكود الأصلي) ثم GREEN.\n"
             f"- {deletion}.\n"
             f"- **ينتظر الترقية:** الفرع `{br}`؛ الترقية إلى main قرار المالك (المادة ٦).\n")
    ch = repo / "docs" / "CHANGELOG.md"
    ch.write_text(_insert_after_first_rule(ch.read_text(encoding="utf-8"), entry), encoding="utf-8")
    ps = repo / "docs" / "PROJECT_STATE.md"
    ps.write_text(ps.read_text(encoding="utf-8").rstrip("\n") +
                  f"\n\n- R-796 تطوير ذاتي [{tag}] ({today}): `{d['file']}` — "
                  f"{d.get('summary') or task['title']} — RED→GREEN على `{br}`، ينتظر ترقية المالك.\n",
                  encoding="utf-8")
    pointer = repo / "docs" / "ROADMAP_ACTIVE.txt"
    rm_rel = (pointer.read_text(encoding="utf-8").strip() if pointer.is_file()
              else "docs/ROADMAP_V6.md")
    rm = repo / rm_rel
    rm.write_text(rm.read_text(encoding="utf-8").rstrip("\n") +
                  f"\n\n- ٦.١٠ (R-796) تطوير ذاتي [{tag}]: {task['title']} — مختبر RED→GREEN، "
                  "ينتظر ترقية المالك.\n", encoding="utf-8")
    if removed:
        au = repo / "forensics" / "DELETED_LINES_AUDIT.md"
        lines = "\n".join(f"    {ln}" for ln in removed[:200])
        au.write_text(au.read_text(encoding="utf-8").rstrip("\n") +
                      f"\n\n## {today} — {tag}: أسطر مستبدلة (تطوير ذاتي)\n"
                      f"- **# DELETION-JUSTIFIED** — استبدال بتعديل اختُبر RED→GREEN: "
                      f"{d.get('summary') or task['title']}\n"
                      f"  - `{d['file']}` — الأسطر الأصلية حرفيًا:\n\n{lines}\n", encoding="utf-8")


def process(task: Dict[str, Any], repo: Path, base: str = "origin/main",
            run_suite: bool = True, push: bool = False,
            today: Optional[str] = None) -> Dict[str, Any]:
    """دورة مهمة واحدة — يعيد نتيجة تُلحق بـ selfdev_ci (لا يرمي على فشل الاختبار)."""
    today = today or _dt.date.today().isoformat()
    d = task.get("draft") or {}
    attempt = int(task.get("attempts") or 1)
    res: Dict[str, Any] = {"task_id": task["id"], "attempt": attempt, "at": time.time(),
                           "branch": None, "sha": None, "ci_dispatched": False}
    br = branch_name(task)
    _git(repo, "checkout", "-q", "-f", "-B", br, base)
    target = repo / d.get("file", "")
    original = target.read_text(encoding="utf-8") if target.is_file() else None
    if original is None or original.count(d.get("search") or "\0") != 1:
        return dict(res, result="stale", reason="الملف تغيّر منذ الصياغة — إعادة صياغة")
    errors = sd.validate_draft(d, original)
    if errors:
        return dict(res, result="red", reason="validation:" + ",".join(errors))
    tp = repo / test_path(task)
    tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text(test_file_content(task), encoding="utf-8")
    py = sys.executable
    # -B: بلا bytecode — تعديل بنفس الحجم في نفس الثانية كان يُختبر بـ .pyc القديم
    # (عيب اكتشفه اختبار الدورة: GREEN زائف/أحمر زائف)
    red = _run([py, "-B", "-m", "pytest", str(tp), "-q", "-p", "no:cacheprovider"], repo, timeout=300)
    res["red_rc"] = red.returncode
    if red.returncode == 0:
        _cleanup(repo, tp, base)
        return dict(res, result="red", reason="not_red_first: الاختبار نجح على الكود الأصلي "
                    "— لا يثبت العيب", log_tail=_tail(red))
    target.write_text(original.replace(d["search"], d["replace"], 1), encoding="utf-8")
    green = _run([py, "-B", "-m", "pytest", str(tp), "-q", "-p", "no:cacheprovider"], repo, timeout=300)
    res["green_rc"] = green.returncode
    if green.returncode != 0:
        _cleanup(repo, tp, base)
        return dict(res, result="red", reason="not_green_after_fix", log_tail=_tail(green))
    removed = sd.removed_lines(d["search"], d["replace"])
    write_docs(repo, task, red.returncode, removed, today)
    _git(repo, "add", "-A", "--", d["file"], TEST_DIR, "docs", "forensics")
    msg = (f"{task['id']} a{attempt}: {d.get('summary') or task['title']} [selfdev R-796]\n\n"
           f"Source: {task.get('source')} {task.get('ref') or ''}\nTask: {task['title']}\n"
           f"RED rc={red.returncode} on original; GREEN rc=0 after change ({test_path(task)}).\n")
    if removed:
        msg += (f"\n# DELETION-JUSTIFIED: {len(removed)} replaced line(s) listed verbatim in "
                f"forensics/DELETED_LINES_AUDIT.md ({task['id']} a{attempt})\n")
    _git(repo, "commit", "-q", "-m", msg)
    sha = _git(repo, "rev-parse", "HEAD")
    res.update(branch=br, sha=sha)
    for gate in (["tools/gate_deletions.py", "HEAD"], ["tools/gate_docs_sync.py", "HEAD"]):
        g = _run([py, *gate], repo, timeout=120)
        if g.returncode != 0:
            return dict(res, result="red", reason=f"gate_failed:{gate[0]}", log_tail=_tail(g))
    if run_suite:
        suite = _run([py, "-B", "-m", "pytest", "tests/", "backend/tests/", "-q", "-m",
                      "not operational", "-p", "no:cacheprovider"], repo, timeout=2400)
        res["suite_rc"] = suite.returncode
        if suite.returncode != 0:
            return dict(res, result="red", reason="full_suite_failed", log_tail=_tail(suite))
    if push:
        p = _run(["git", "push", "-q", "origin", f"{br}:{br}"], repo, timeout=120)
        if p.returncode != 0:
            return dict(res, result="red", reason="push_failed", log_tail=_tail(p))
        c = _run(["gh", "workflow", "run", "ci.yml", "--ref", br], repo, timeout=60)
        res["ci_dispatched"] = c.returncode == 0
    return dict(res, result="green", reason="RED→GREEN + gates + suite")


def _cleanup(repo: Path, tp: Path, base: str) -> None:
    if tp.is_file():
        tp.unlink()  # ملف مولَّد في هذه الدورة نفسها لم يُلتزم — ليس حذفًا من المستودع
    _git(repo, "checkout", "-q", "-f", base, check=False)


def promotions(repo: Path, ci_rows: List[Dict[str, Any]], base: str = "origin/main") -> List[Dict[str, Any]]:
    seen = {(r.get("payload") or {}).get("task_id") for r in ci_rows
            if (r.get("payload") or {}).get("result") == "promoted"}
    out = []
    for r in ci_rows:
        p = r.get("payload") or {}
        if p.get("result") != "green" or not p.get("sha") or p.get("task_id") in seen:
            continue
        ok = _run(["git", "merge-base", "--is-ancestor", p["sha"], base], repo, timeout=60)
        if ok.returncode == 0:
            seen.add(p["task_id"])
            out.append({"task_id": p["task_id"], "attempt": p.get("attempt"),
                        "result": "promoted", "sha": p["sha"], "at": time.time(),
                        "reason": "البصمة صارت في main"})
    return out


# ---------- R-797: الترقية الآلية (بأمر المالك 2026-10-28 «فعّل الترقية الآلية») ----------
FLY_APP = "sovereign-ai-k20elq"


def circuit_open(ci_rows: List[Dict[str, Any]]) -> Optional[str]:
    """قاطع الدائرة: آخر نشر آلي لم ينجح ⇒ لا ترقية آلية جديدة حتى يُعاد الضبط
    (تشغيل يدوي لـ self-develop.yml بالمدخل reset_circuit=true، أو نشر آلي ناجح)."""
    last = None
    for r in ci_rows:
        p = r.get("payload") or {}
        if "deploy" in p:
            last = p
    if last is None or last.get("deploy") in ("success", "reset"):
        return None
    return f"circuit_open: آخر نشر آلي ({last.get('task_id')}) = {last.get('deploy')}"


def gh_wait_ci(sha: str, repo: Path, timeout: int = 2400, poll: int = 20) -> str:
    """ينتظر تشغيل ci.yml على البصمة نفسها — يعيد success/failure/.../timeout."""
    end = time.time() + timeout
    while time.time() < end:
        r = _run(["gh", "run", "list", "--workflow", "ci.yml", "--commit", sha, "--limit", "5",
                  "--json", "status,conclusion"], repo, timeout=60)
        try:
            runs = json.loads(r.stdout or "[]")
        except ValueError:  # TOLERATED: رد غير صالح مؤقت — يُعاد الاستطلاع
            runs = []
        done = [x for x in runs if x.get("status") == "completed"]
        if any(x.get("conclusion") == "success" for x in done):
            return "success"
        if done and not [x for x in runs if x.get("status") != "completed"]:
            return str(done[0].get("conclusion") or "failure")
        time.sleep(poll)
    return "timeout"


def gh_deploy(sha: str, repo: Path, timeout: int = 2400, poll: int = 20) -> str:
    """يشغّل deploy-fly.yml على main (بوابته تتحقق من CI أخضر على نفس SHA وفحص /health)."""
    d = _run(["gh", "workflow", "run", "deploy-fly.yml", "--ref", "main",
              "-f", f"confirm_app={FLY_APP}"], repo, timeout=60)
    if d.returncode != 0:
        return "dispatch_failed"
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(poll)
        r = _run(["gh", "run", "list", "--workflow", "deploy-fly.yml", "--commit", sha,
                  "--limit", "1", "--json", "status,conclusion"], repo, timeout=60)
        try:
            runs = json.loads(r.stdout or "[]")
        except ValueError:  # TOLERATED: رد غير صالح مؤقت — يُعاد الاستطلاع
            runs = []
        if runs and runs[0].get("status") == "completed":
            return str(runs[0].get("conclusion") or "failure")
    return "timeout"


def promote(res: Dict[str, Any], repo: Path, ci_rows: List[Dict[str, Any]],
            base: str = "origin/main", wait_ci=gh_wait_ci, deploy=gh_deploy) -> Dict[str, Any]:
    """ترقية آلية لفرع أخضر: CI أخضر على نفس البصمة ⇒ تقدم سريع فقط إلى main ⇒ نشر.
    لا دمج ولا إعادة كتابة تاريخ؛ main تقدّم ⇒ stale (إعادة صياغة على الأحدث)."""
    sha = res.get("sha")
    out = {"task_id": res["task_id"], "attempt": res.get("attempt"), "sha": sha,
           "branch": res.get("branch"), "at": time.time()}
    reason = circuit_open(ci_rows)
    if reason:
        return dict(out, result="promote_skipped", reason=reason)
    ci = wait_ci(sha, repo)
    if ci != "success":
        return dict(out, result="red", reason=f"ci_on_branch:{ci}")
    _git(repo, "fetch", "-q", "origin", "main", check=False)
    ff = _run(["git", "merge-base", "--is-ancestor", base, sha], repo, timeout=60)
    if ff.returncode != 0:
        return dict(out, result="stale", reason="main تقدّم منذ الفرع — لا تقدم سريع؛ إعادة صياغة")
    p = _run(["git", "push", "-q", "origin", f"{sha}:refs/heads/main"], repo, timeout=120)
    if p.returncode != 0:
        return dict(out, result="promote_skipped", reason="push_main_rejected",
                    log_tail=_tail(p, 600))
    dep = deploy(sha, repo)
    return dict(out, result="promoted", deploy=dep,
                reason=f"ترقية آلية R-797: main ← {sha[:12]}؛ النشر: {dep}")


def run_cycle(disk, repo: Path, max_tasks: int = 1, base: str = "origin/main",
              run_suite: bool = True, push: bool = False, auto_promote: bool = False,
              wait_ci=gh_wait_ci, deploy=gh_deploy) -> Dict[str, Any]:
    tasks = latest_tasks(pull_all(disk, sd.NAMESPACE))
    ci_rows = pull_all(disk, sd.CI_NAMESPACE)
    done = {((r.get("payload") or {}).get("task_id"), (r.get("payload") or {}).get("attempt"))
            for r in ci_rows}
    report: Dict[str, Any] = {"tasks_seen": len(tasks), "processed": [], "promoted": []}
    for p in promotions(repo, ci_rows, base):
        disk.append_log(sd.CI_NAMESPACE, p)
        report["promoted"].append(p["task_id"])
    todo = [t for t in tasks.values() if t.get("status") == "drafted" and t.get("draft")
            and (t["id"], t.get("attempts")) not in done]
    todo.sort(key=lambda t: t.get("updated_at") or 0)
    for t in todo[:max_tasks]:
        try:
            r = process(t, repo, base=base, run_suite=run_suite, push=push)
        except Exception as exc:  # TOLERATED: خلل تنفيذ يُسجل نتيجة حمراء بسببه الحرفي
            r = {"task_id": t["id"], "attempt": t.get("attempts"), "at": time.time(),
                 "result": "red", "reason": f"runner_error:{type(exc).__name__}: {exc}"[:300]}
        disk.append_log(sd.CI_NAMESPACE, r)
        report["processed"].append({k: r.get(k) for k in ("task_id", "attempt", "result",
                                                           "reason", "branch", "sha")})
        ci_rows.append({"payload": r})
        if auto_promote and r.get("result") == "green" and r.get("sha"):
            try:
                pr = promote(r, repo, ci_rows, base=base, wait_ci=wait_ci, deploy=deploy)
            except Exception as exc:  # TOLERATED: خلل الترقية يُسجل ويبقى الفرع ينتظر
                pr = {"task_id": r["task_id"], "attempt": r.get("attempt"), "sha": r.get("sha"),
                      "at": time.time(), "result": "promote_skipped",
                      "reason": f"promote_error:{type(exc).__name__}: {exc}"[:300]}
            disk.append_log(sd.CI_NAMESPACE, pr)
            ci_rows.append({"payload": pr})
            report.setdefault("auto_promotion", []).append(
                {k: pr.get(k) for k in ("task_id", "result", "reason", "deploy", "sha")})
    return report


def main() -> int:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        print("R-796: SUPABASE_URL/SUPABASE_SECRET_KEY غير مضبوطين — لا مصدر للمسودات (لا عمل)")
        return 0
    try:
        max_tasks = max(1, min(int(os.environ.get("SELFDEV_MAX_TASKS", "1")), 5))
    except ValueError:  # TOLERATED: قيمة غير رقمية → الافتراضي المعلن
        max_tasks = 1
    _git(ROOT, "fetch", "-q", "origin", "main")
    disk = RestDisk(url, key)
    if os.environ.get("SELFDEV_RESET_CIRCUIT") == "true":
        disk.append_log(sd.CI_NAMESPACE, {"task_id": None, "deploy": "reset", "at": time.time(),
                                          "result": "circuit_reset", "reason": "إعادة ضبط يدوية"})
    auto = os.environ.get("SELFDEV_AUTO_PROMOTE") == "1"
    print(f"R-796/R-797: الترقية الآلية {'مفعلة' if auto else 'معطلة'} (SELFDEV_AUTO_PROMOTE)")
    report = run_cycle(disk, ROOT, max_tasks=max_tasks,
                       push=os.environ.get("SELFDEV_PUSH") == "1",
                       run_suite=os.environ.get("SELFDEV_SKIP_SUITE") != "1",
                       auto_promote=auto)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    # بلا مسار إنهاء صريح (R-686): الدورة تكتمل بـ 0؛ خلل التنفيذ يرفع استثناءً فيحمرّ التشغيل
    main()
