#!/usr/bin/env python3
"""R-829: مزامنة المشاريع مفتوحة المصدر المدمجة في محرك البحث (third_party/).

بأمر المالك (2026-11-02): «ابحث عن وكلاء مفتوحي المصدر مخصصين في البحث والاستنتاج والتنقيح
ومحركات بحث مفتوحة المصدر، واسحب جميع أكوادها وملفاتها وأدواتها وادمجها في المشروع».

ما تفعله الأداة (قابلة للإعادة — تحديث أي مشروع إلى أحدث إصدار بأمر واحد):
1) تستنسخ كل مستودع في SOURCES بعمق 1 وتسجّل رقم الإصدار (commit) الدقيق.
2) تنسخ **كل** ملفات الكود والأدوات والإعدادات والنصوص إلى third_party/<owner>__<repo>/ بلا .git.
3) تستثني فقط ما لا يصلح داخل مستودع كود: وسائط ثقيلة (فيديو/صور متحركة/أرشيفات/PDF/خطوط > 200KB)،
   أي ملف > 2MB، ومجلدات صفحات اختبار ضخمة (CORPUS_DIRS). كل ملف مستثنى يُسجَّل في MANIFEST.json
   بمساره وحجمه وبصمته sha256 — يمكن استرجاعه حرفيًا من المستودع الأصلي عند ذلك الإصدار.
4) تكتب third_party/MANIFEST.json: المستودع، الترخيص، الإصدار، الدور في محرك البحث، عدد الملفات، المستثنى.
5) أمر المالك HIST-02 (لا عنوان شبكة داخلية في أي ملف متتبع، بلا استثناء): كل عنوان يطابق
   tools/private_ip_guard.py في الأصل يُقنَّع (10.0.0.x / fexx::1) ويُسجَّل في «masked» بالسطر والنوع وبصمة
   الملف الأصلي — العنوان الأصلي لا يُكتب في أي مكان. ملف ثنائي يحوي عنوانًا يوقف المزامنة لقرار يدوي.

الاستخدام:  GH_TOKEN=... python scripts/vendor_sync.py [owner/repo ...]
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "third_party"

# (المستودع، الفئة، الترخيص، الدور في محرك البحث السيادي)
SOURCES = [
    # ── وكلاء البحث العميق والاستنتاج والتنقيح ──
    ("assafelovic/gpt-researcher", "agent", "Apache-2.0",
     "تفكيك السؤال إلى أسئلة فرعية + بحث متوازٍ + تقرير مستشهد (planner/execution/publisher)"),
    ("stanford-oval/storm", "agent", "MIT",
     "اكتشاف المنظورات من مقالات ويكيبيديا المرتبطة ثم أسئلة لكل منظور ومخطط تقرير"),
    ("langchain-ai/open_deep_research", "agent", "MIT",
     "تخطيط أقسام ← بحث لكل قسم ← تأمّل (reflection) لاكتشاف الفجوات ← استعلامات متابعة"),
    ("dzhng/deep-research", "agent", "MIT",
     "بحث تكراري بعرض/عمق: استعلامات SERP ← تعلّمات ← اتجاهات متابعة ← تعمّق"),
    ("jina-ai/node-DeepResearch", "agent", "Apache-2.0",
     "حلقة بحث/قراءة/تأمّل/إجابة حتى ميزانية رموز مع تقييم الإجابة قبل قبولها"),
    ("InternLM/MindSearch", "agent", "Apache-2.0",
     "مخطِّط يبني رسمًا بيانيًا للأسئلة الفرعية (WebPlanner) وباحث لكل عقدة (WebSearcher)"),
    ("huggingface/smolagents", "agent", "Apache-2.0",
     "وكلاء الكود/الأدوات ومثال open_deep_research (أدوات بحث وقراءة نصية)"),
    ("togethercomputer/open_deep_research", "agent", "MIT",
     "تخطيط استعلامات ← بحث ← تقييم كفاية ← تكرار ← تقرير"),
    ("mshumer/OpenDeepResearcher", "agent", "MIT",
     "حلقة بحث غير متزامنة: استعلامات ← صفحات ← تقييم الصلة ← استخلاص ← قرار المتابعة"),
    ("zamalali/DeepGit", "agent", "MIT", "بحث عميق في مستودعات GitHub وترتيبها دلاليًا"),
    ("MiroMindAI/MiroThinker", "agent", "Apache-2.0", "وكيل بحث استنتاجي بأدوات (بحث/قراءة/تنفيذ)"),
    ("SkyworkAI/DeepResearchAgent", "agent", "MIT", "وكيل تخطيط هرمي يوزع المهام على وكلاء بحث فرعيين"),
    ("NVIDIA-AI-Blueprints/deep-researcher-agent", "agent", "Apache-2.0",
     "مخطط بحث عميق: تخطيط ← بحث ← تقييم ← تقرير مع طبقة معرفة"),
    ("jordan-gibbs/hyperresearch", "agent", "MIT", "بحث متعدد المراحل مع تحقق متقاطع"),
    ("kidzik/web-research-agent", "agent", "Apache-2.0", "وكيل بحث ويب بسيط: بحث ← قراءة ← تلخيص"),
    ("Alibaba-NLP/DeepResearch", "agent", "Apache-2.0", "Tongyi DeepResearch: WebSailor/WebWalker/WebDancer"),
    # ── محركات بحث بالذكاء الاصطناعي (واجهات وخلفيات) ──
    ("rashadphz/farfalle", "ai_search", "Apache-2.0", "محرك إجابات: بحث ← إعادة ترتيب ← إجابة مستشهدة"),
    ("ItzCrazyKns/Vane", "ai_search", "MIT", "Perplexica (Vane): أوضاع تركيز البحث وإعادة الترتيب بالتشابه"),
    ("mckaywrigley/clarity-ai", "ai_search", "MIT", "محرك إجابات مختصر مستشهد"),
    # ── محركات بحث وفهرسة وترتيب ──
    ("dorianbrown/rank_bm25", "engine", "Apache-2.0", "ترتيب Okapi BM25 / BM25L / BM25+ للجمل المرشحة"),
    ("xhluca/bm25s", "engine", "MIT", "BM25 سريع بمصفوفات متفرقة"),
    ("Sygil-Dev/whoosh-reloaded", "engine", "BSD-2-Clause", "محرك فهرسة بحث نصي كامل بلغة Python"),
    ("deedy5/ddgs", "engine", "MIT", "بحث فوقي متعدد المحركات (Bing/Brave/DuckDuckGo/Google/Mojeek/Yahoo/Yandex/Wikipedia)"),
    ("benbusby/whoogle-search", "engine", "MIT", "وسيط بحث Google بلا تتبع وتحليل نتائجه"),
    ("mat-1/metasearch2", "engine", "CC0-1.0", "محرك بحث فوقي يدمج النتائج من عدة محركات"),
    ("quickwit-oss/tantivy", "engine", "MIT", "محرك بحث نصي كامل (Rust) — مرجع Lucene-مثله"),
    ("toshi-search/Toshi", "engine", "MIT", "خادم بحث نصي كامل فوق tantivy"),
    ("tinysearch/tinysearch", "engine", "Apache-2.0", "فهرس بحث ثابت مضغوط بمرشحات Bloom"),
    ("SeekStorm/SeekStorm", "engine", "Apache-2.0", "محرك بحث نصي كامل عالي الأداء"),
    ("lucaong/minisearch", "engine", "MIT", "بحث نصي كامل داخل المتصفح (JavaScript)"),
    # ── أدوات قراءة الصفحات واستخراج النص ──
    ("adbar/trafilatura", "tool", "Apache-2.0", "استخراج النص الرئيسي والتاريخ والمؤلف من صفحات الويب"),
    ("codelucas/newspaper", "tool", "MIT", "استخراج المقالات الإخبارية (العنوان/النص/التاريخ)"),
]

MEDIA = {".tar", ".gz", ".tgz", ".zip", ".7z", ".mp4", ".mov", ".webm", ".gif", ".pdf", ".ttf", ".otf", ".woff",
         ".woff2", ".png", ".jpg", ".jpeg", ".webp", ".ico", ".svg", ".mp3", ".wav", ".bin", ".pt", ".onnx", ".pkl",
         ".parquet", ".jsonl", ".npy", ".whl", ".so", ".dll", ".exe", ".jar", ".psd"}
MAX_FILE = 2 * 1024 * 1024
MAX_MEDIA = 200 * 1024
# مجلدات صفحات HTML محفوظة لاختبارات المكتبة الأصلية — بيانات لا كود
CORPUS_DIRS = ("adbar/trafilatura:tests/cache", "adbar/trafilatura:tests/eval", "codelucas/newspaper:tests/data")


def _excluded(repo: str, rel: str, size: int) -> str:
    for spec in CORPUS_DIRS:
        r, d = spec.split(":", 1)
        if r == repo and (rel == d or rel.startswith(d + "/")):
            return "corpus"
    if size > MAX_FILE:
        return "size>2MB"
    if Path(rel).suffix.lower() in MEDIA and size > MAX_MEDIA:
        return "media>200KB"
    return ""


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _generated(target: Path, q: Path) -> bool:
    """مخرجات التثبيت/التشغيل (pip install ./third_party/X يبني في مكانه) — ليست من الأصل ولا تدخل البصمة."""
    parts = q.relative_to(target).parts
    return parts[0] == "build" or any(x == "__pycache__" or x.endswith(".egg-info") for x in parts)


def tree_sha256(target: Path) -> str:
    """بصمة الشجرة المنسوخة: sha256 فوق (المسار + بصمة كل ملف) مرتبة — تثبت أن النسخة لم تُعدَّل محليًا."""
    h = hashlib.sha256()
    for q in sorted(x for x in target.rglob("*") if x.is_file() and not x.is_symlink() and not _generated(target, x)):
        h.update(q.relative_to(target).as_posix().encode() + b"\0" + _sha256(q).encode() + b"\n")
    return h.hexdigest()


def _load_ip_guard():
    """نواة حارس العناوين (tools/private_ip_guard.py) — المصدر الوحيد لأنماط HIST-02."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("private_ip_guard", ROOT / "tools" / "private_ip_guard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mask_private_addresses(text: str):
    """أمر المالك HIST-02 (لا عنوان شبكة داخلية في أي ملف متتبع، بلا استثناء): كل عنوان يطابق الحارس
    في الأصل يُقنَّع — IPv4 آخر مقطع ⇒ x (الصيغة المقنعة المعتمدة)، IPv6 آخر خانتين من المقطع الأول ⇒ xx.
    لا يُكتب العنوان الأصلي في أي مكان (ولا في البيان) — يُسجَّل السطر والنوع والقيمة المقنعة فقط."""
    guard = _load_ip_guard()
    hits = []
    for _ in range(10):  # التقنيع قد يكشف تطابقًا متداخلًا — جولات حتى لا يبقى شيء (كل جولة تقنّع كل المطابقات)
        found = guard.scan_text(text)
        if not found:
            return text, sorted(hits, key=lambda h: h["line"])
        for kind, pos, val in sorted(found, key=lambda f: -f[1]):  # من الآخر كي لا تنزاح المواضع
            masked = val.rsplit(".", 1)[0] + ".x" if kind == "ipv4" else val[:2] + "xx" + val[4:]
            hits.append({"line": text[:pos].count("\n") + 1, "kind": kind, "masked": masked})
            text = text[:pos] + masked + text[pos + len(val):]
    raise RuntimeError("تقنيع العناوين لم يستقر بعد ١٠ جولات")


def sync_one(repo: str, category: str, license_: str, role: str, work: Path) -> dict:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
    url = f"https://{'x-access-token:' + token + '@' if token else ''}github.com/{repo}.git"
    clone = work / repo.replace("/", "__")
    if not clone.exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", url, str(clone)], check=True)
    commit = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], check=True,
                            capture_output=True, text=True).stdout.strip()
    target = DEST / repo.replace("/", "__")
    # أمر المالك «يمنع الحذف»: إعادة المزامنة تكتب فوق الملفات ولا تحذف؛ ما اختفى من الأصل يُسجَّل «stale»
    before = {q.relative_to(target).as_posix() for q in target.rglob("*")
              if q.is_file() and not _generated(target, q)} if target.exists() else set()
    kept, kept_bytes, skipped, seen, masked = 0, 0, [], set(), []
    for src in sorted(clone.rglob("*")):
        rel = src.relative_to(clone).as_posix()
        if rel == ".git" or rel.startswith(".git/") or not src.is_file() or src.is_symlink():
            continue
        size = src.stat().st_size
        why = _excluded(repo, rel, size)
        if why:
            skipped.append({"path": rel, "bytes": size, "sha256": _sha256(src), "reason": why})
            continue
        dst = target / rel
        seen.add(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        raw = src.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        if text is not None:
            new, hits = mask_private_addresses(text)
            if hits:
                dst.write_text(new, encoding="utf-8", newline="")
                masked.append({"path": rel, "original_sha256": hashlib.sha256(raw).hexdigest(), "hits": hits})
        elif _load_ip_guard().scan_text(raw.decode(errors="ignore")):
            raise RuntimeError(f"{repo}/{rel}: ملف ثنائي يحوي عنوانًا داخليًا — لا يُقنَّع آليًا، قرار يدوي")
        kept += 1
        kept_bytes += size
    return {"repo": repo, "url": f"https://github.com/{repo}", "commit": commit, "category": category,
            "license": license_, "role_ar": role, "path": f"third_party/{target.name}", "files": kept,
            "bytes": kept_bytes, "tree_sha256": tree_sha256(target), "excluded": skipped, "masked": masked,
            "stale": sorted(before - seen), "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def main(argv) -> int:
    only = set(argv[1:])
    DEST.mkdir(exist_ok=True)
    man_path = DEST / "MANIFEST.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {"projects": []}
    by_repo = {p["repo"]: p for p in manifest.get("projects", [])}
    work = Path(os.getenv("VENDOR_WORKDIR") or tempfile.mkdtemp(prefix="vendor_"))
    for repo, cat, lic, role in SOURCES:
        if only and repo not in only:
            continue
        entry = sync_one(repo, cat, lic, role, work)
        by_repo[repo] = entry
        print(f"{repo}\t{entry['commit'][:10]}\t{entry['files']} ملف\t{len(entry['excluded'])} مستثنى", flush=True)
    order = [r for r, *_ in SOURCES]
    manifest = {"schema": 1, "policy_ar": __doc__.split("ما تفعله الأداة")[1].split("الاستخدام")[0].strip(),
                "projects": sorted(by_repo.values(), key=lambda p: order.index(p["repo"]) if p["repo"] in order else 999)}
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_readme(manifest)
    return 0


_CAT_AR = {"agent": "وكلاء البحث والاستنتاج والتنقيح", "ai_search": "محركات بحث بالذكاء الاصطناعي",
           "engine": "محركات البحث والفهرسة والترتيب", "tool": "أدوات القراءة والاستخراج"}


def write_readme(manifest) -> None:
    """third_party/README.md من البيان نفسه — فهرس مقروء لا يُكتب يدويًا فلا ينحرف عن الواقع."""
    lines = ["# المشاريع مفتوحة المصدر المسحوبة (R-829)", "",
             "مولَّد آليًا من `MANIFEST.json` بواسطة `scripts/vendor_sync.py` — لا تعدّله يدويًا.", "",
             "كل مشروع منسوخ بكامل كوده عند commit محدد مع رخصته الأصلية. الربط بمحرك البحث وأوضاعه",
             "(runtime يعمل / ported منقول / source محفوظ) في `backend/search_agents/__init__.py`.", ""]
    for cat in ("agent", "ai_search", "engine", "tool"):
        rows = [p for p in manifest["projects"] if p["category"] == cat]
        if not rows:
            continue
        lines += [f"## {_CAT_AR[cat]}", "", "| المشروع | الرخصة | commit | الملفات | الدور |", "|---|---|---|---|---|"]
        lines += [f"| [{p['repo']}](https://github.com/{p['repo']}) | {p['license']} | `{p['commit'][:10]}` | "
                  f"{p['files']} | {p['role_ar']} |" for p in rows]
        lines.append("")
    (DEST / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
