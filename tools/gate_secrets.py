#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-848 (D-063): بوابة الأسرار — لا سر يدخل المستودع.

الأنماط من المصدر الوحيد ``backend/secret_guard/catalog.py`` (يُحمَّل بالمسار، بلا
اعتمادات التطبيق). ثلاثة أوضاع:

  --range BASE HEAD   الأسطر المضافة ورسالة كل التزام في المدى (CI)
  <SHA>               التزام واحد (رجوع CI الموثق حين لا قاعدة دفع)
  --staged            محتوى الفهرس (hook pre-commit)
  --tree              كل الملفات المتتبعة مقابل خط الأساس، مع كشف الإدخالات المتعفنة

خط الأساس ``tools/secrets_baseline.json``: إدخالات (قاعدة، مسار حرفي، بصمة، سبب).
لا قيم، ولا أنماط مسارات (``*?[`` مرفوضة)، فلا ثقب شامل. البصمة تربط القيمة
بالمسار، فنقل السر نفسه إلى ملف آخر كشف جديد.

المخرجات: القاعدة والمسار والسطر والبصمة فقط — القيمة لا تُطبع أبدًا.
رموز الخروج: 0 نظيف، 1 كشوف أو خط أساس متعفن، 2 خطأ استعمال أو خط أساس غير صالح.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "secrets_baseline.json"
MAX_FILE_BYTES = 2 * 1024 * 1024
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _load_catalog():
    spec = importlib.util.spec_from_file_location(
        "_sg_catalog", ROOT / "backend" / "secret_guard" / "catalog.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod     # dataclasses تحتاج الوحدة مسجلة
    spec.loader.exec_module(mod)
    return mod


catalog = _load_catalog()


class BaselineError(Exception):
    pass


def load_baseline(path: Path = BASELINE) -> Dict[Tuple[str, str, str], str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise BaselineError(f"خط الأساس غير مقروء: {type(e).__name__}") from e
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise BaselineError("خط الأساس: الحقل entries مفقود")
    out: Dict[Tuple[str, str, str], str] = {}
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or set(e) != {"rule", "path", "fingerprint", "reason"}:
            raise BaselineError(f"إدخال {i}: الحقول المطلوبة بالضبط rule/path/fingerprint/reason")
        if e["rule"] not in catalog.RULE_IDS:
            raise BaselineError(f"إدخال {i}: قاعدة مجهولة {e['rule']!r}")
        if any(c in e["path"] for c in "*?[") or e["path"].startswith("/") or ".." in e["path"].split("/"):
            raise BaselineError(f"إدخال {i}: المسار يجب أن يكون حرفيًا نسبيًا (لا أنماط)")
        if len(str(e["fingerprint"])) != 24:
            raise BaselineError(f"إدخال {i}: بصمة غير صالحة")
        if len(str(e["reason"]).strip()) < 10:
            raise BaselineError(f"إدخال {i}: السبب إلزامي (≥ 10 أحرف)")
        key = (e["rule"], e["path"], e["fingerprint"])
        if key in out:
            raise BaselineError(f"إدخال {i}: مكرر")
        out[key] = e["reason"]
    return out


Finding = Tuple[str, str, int, str, str]     # rule, path, line, fingerprint, where


def scan_text(path: str, text: str, where: str = "", line_offsets: Optional[List[int]] = None
              ) -> List[Finding]:
    out: List[Finding] = []
    for idx, line in enumerate(text.splitlines()):
        for h in catalog.find(line):
            ln = line_offsets[idx] if line_offsets else idx + 1
            out.append((h.rule, path, ln, h.fingerprint(path), where))
    return out


def _git(*args: str, cwd: Path = ROOT) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {args[0]} فشل: {p.stderr.decode('utf-8', 'replace')[:200]}")
    return p.stdout.decode("utf-8", "replace")


def parse_added(diff: str) -> Iterable[Tuple[str, List[str], List[int]]]:
    """من diff بـ--unified=0: (المسار، الأسطر المضافة، أرقامها)."""
    path: Optional[str] = None
    lines: List[str] = []
    nums: List[int] = []
    cur = 0
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            if path is not None and lines:
                yield path, lines, nums
            path, lines, nums = None, [], []
        elif raw.startswith("+++ "):
            t = raw[4:]
            path = t[2:] if t.startswith("b/") else (None if t == "/dev/null" else t)
        elif raw.startswith("@@"):
            try:
                cur = int(raw.split("+", 1)[1].split(" ", 1)[0].split(",", 1)[0])
            except (IndexError, ValueError):
                cur = 0
        elif raw.startswith("+") and not raw.startswith("+++") and path is not None:
            lines.append(raw[1:])
            nums.append(cur)
            cur += 1
    if path is not None and lines:
        yield path, lines, nums


def scan_commit(sha: str, cwd: Path = ROOT) -> List[Finding]:
    parents = _git("rev-list", "--parents", "-n", "1", sha, cwd=cwd).split()[1:]
    base = parents[0] if parents else EMPTY_TREE
    diff = _git("diff", "--unified=0", "--no-color", "--no-ext-diff", "--no-renames",
                base, sha, cwd=cwd)
    out: List[Finding] = []
    for path, lines, nums in parse_added(diff):
        out.extend(scan_text(path, "\n".join(lines), sha[:12], nums))
    msg = _git("log", "-1", "--format=%B", sha, cwd=cwd)
    out.extend(scan_text("<commit-message>", msg, sha[:12]))
    return out


def scan_range(base: str, head: str, cwd: Path = ROOT) -> List[Finding]:
    shas = _git("rev-list", "--reverse", f"{base}..{head}", cwd=cwd).split()
    out: List[Finding] = []
    for s in shas:
        out.extend(scan_commit(s, cwd))
    return out


def scan_staged(cwd: Path = ROOT) -> List[Finding]:
    diff = _git("diff", "--cached", "--unified=0", "--no-color", "--no-ext-diff",
                "--no-renames", cwd=cwd)
    out: List[Finding] = []
    for path, lines, nums in parse_added(diff):
        out.extend(scan_text(path, "\n".join(lines), "staged", nums))
    return out


def scan_tree(cwd: Path = ROOT) -> Tuple[List[Finding], List[str]]:
    files = [f for f in _git("ls-files", "-z", cwd=cwd).split("\0") if f]
    out: List[Finding] = []
    skipped: List[str] = []
    for f in files:
        p = cwd / f
        try:
            if p.is_symlink() or not p.is_file():
                continue
            if p.stat().st_size > MAX_FILE_BYTES:
                skipped.append(f)
                continue
            data = p.read_bytes()
        except OSError:
            skipped.append(f)
            continue
        if b"\0" in data[:8192]:
            continue    # ثنائي
        out.extend(scan_text(f, data.decode("utf-8", "replace"), "tree"))
    return out, skipped


def judge(findings: List[Finding], baseline: Dict[Tuple[str, str, str], str]
          ) -> List[Finding]:
    return [f for f in findings if (f[0], f[1], f[3]) not in baseline]


def stale_entries(findings: List[Finding], baseline: Dict[Tuple[str, str, str], str]
                  ) -> List[Tuple[str, str, str]]:
    seen: Set[Tuple[str, str, str]] = {(f[0], f[1], f[3]) for f in findings}
    return sorted(k for k in baseline if k not in seen)


def baseline_entries(findings: List[Finding], reason: str) -> List[Dict[str, str]]:
    uniq = sorted({(f[0], f[1], f[3]) for f in findings})
    return [{"rule": r, "path": p, "fingerprint": fp, "reason": reason} for r, p, fp in uniq]


def _report(new: List[Finding], stale: List[Tuple[str, str, str]], skipped: List[str],
            mode: str, json_path: Optional[str]) -> int:
    for rule, path, line, fp, where in new:
        print(f"❌ سر محتمل [{rule}] {path}:{line} بصمة={fp} {('@' + where) if where else ''}".rstrip())
    for rule, path, fp in stale:
        print(f"❌ خط أساس متعفن (لا كشف يطابقه): [{rule}] {path} بصمة={fp}")
    if skipped:
        print(f"[info] تُخطّي {len(skipped)} ملفًا (أكبر من {MAX_FILE_BYTES // 1024 // 1024}MiB أو غير مقروء)")
    if json_path:
        Path(json_path).write_text(json.dumps({
            "mode": mode,
            "new": [{"rule": r, "path": p, "line": ln, "fingerprint": fp, "where": w}
                    for r, p, ln, fp, w in new],
            "stale": [{"rule": r, "path": p, "fingerprint": fp} for r, p, fp in stale],
            "skipped": skipped}, ensure_ascii=False, indent=1), encoding="utf-8")
    if new or stale:
        print("الإصلاح: أزل السر ودوّره فورًا (وجوده في التاريخ يكفي لاعتباره مسرّبًا). "
              "إن كان اصطناعيًا فولّده وقت التشغيل، أو أضف بصمته إلى tools/secrets_baseline.json بسبب.")
        return 1
    print(f"✅ بوابة الأسرار ({mode}): لا سر جديد")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="بوابة الأسرار R-848")
    ap.add_argument("sha", nargs="?")
    ap.add_argument("--range", nargs=2, metavar=("BASE", "HEAD"))
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--tree", action="store_true")
    ap.add_argument("--baseline", default=str(BASELINE))
    ap.add_argument("--json")
    ap.add_argument("--repo", default=str(ROOT), help="مستودع آخر (للاختبار)")
    ap.add_argument("--print-baseline", metavar="REASON",
                    help="مع --tree: اطبع إدخالات خط أساس لكل الكشوف الحالية (للمراجعة اليدوية)")
    a = ap.parse_args(argv)
    modes = sum(bool(x) for x in (a.sha, a.range, a.staged, a.tree))
    if modes != 1:
        ap.error("اختر وضعًا واحدًا: SHA أو --range أو --staged أو --tree")
    repo = Path(a.repo).resolve()
    try:
        baseline = load_baseline(Path(a.baseline))
    except BaselineError as e:
        print(f"❌ {e}")
        return 2
    try:
        if a.tree:
            found, skipped = scan_tree(repo)
            if a.print_baseline:
                print(json.dumps({"entries": baseline_entries(found, a.print_baseline)},
                                 ensure_ascii=False, indent=1))
                return 0
            return _report(judge(found, baseline), stale_entries(found, baseline), skipped,
                           "tree", a.json)
        if a.range:
            found = scan_range(*a.range, cwd=repo)
            mode = f"range {a.range[0][:12]}..{a.range[1][:12]}"
        elif a.staged:
            found, mode = scan_staged(repo), "staged"
        else:
            found, mode = scan_commit(a.sha, repo), f"commit {a.sha[:12]}"
    except RuntimeError as e:
        print(f"❌ {e}")
        return 2
    return _report(judge(found, baseline), [], [], mode, a.json)


if __name__ == "__main__":
    sys.exit(main())
