"""R-829: نزاهة الكود المدمج من مشاريع مفتوحة المصدر (third_party/).

الحراس الثابتة (لا مسارات إنهاء / لا Mock / لا وحدات يتيمة) تستثني third_party/ لأنه كود طرف ثالث
بنسخته الأصلية — وهذا الاستثناء مشروط بتحقق، لا مفتوح:
1) كل مجلد في third_party/ مسجّل في MANIFEST.json (لا كود مجهول المصدر)، والعكس.
2) الترخيص متساهل يسمح بالدمج (MIT/Apache/BSD/CC0) وملف الترخيص الأصلي موجود — لا GPL/AGPL صامت.
3) بصمة الشجرة تطابق المسجّل حرفيًا ⇒ لم يُعدَّل سطر واحد محليًا (أي تعديل يجب أن يمر بكود المشروع).
4) كل مشروع مربوط بقدرة في محرك البحث (backend/search_agents.registry) — لا شيء للزينة.
"""
import hashlib
import json
import importlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_TP = _ROOT / "third_party"
_ALLOWED = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0"}


def _manifest():
    return json.loads((_TP / "MANIFEST.json").read_text(encoding="utf-8"))


def _generated(target: Path, q: Path) -> bool:
    """مخرجات التثبيت/التشغيل (pip install ./third_party/X يبني في مكانه) — ليست من الأصل ولا تدخل البصمة."""
    parts = q.relative_to(target).parts
    return parts[0] == "build" or any(x == "__pycache__" or x.endswith(".egg-info") for x in parts)


def _tree_sha256(target: Path) -> str:
    h = hashlib.sha256()
    for q in sorted(x for x in target.rglob("*") if x.is_file() and not x.is_symlink() and not _generated(target, x)):
        h.update(q.relative_to(target).as_posix().encode() + b"\0" + hashlib.sha256(q.read_bytes()).hexdigest().encode()
                 + b"\n")
    return h.hexdigest()


def test_every_vendored_dir_is_registered_and_vice_versa():
    dirs = {p.name for p in _TP.iterdir() if p.is_dir()}
    paths = {Path(p["path"]).name for p in _manifest()["projects"]}
    assert dirs == paths, f"غير مسجّل: {sorted(dirs - paths)} — مسجّل بلا مجلد: {sorted(paths - dirs)}"


def test_licenses_permissive_and_present():
    for p in _manifest()["projects"]:
        assert p["license"] in _ALLOWED, f"{p['repo']}: ترخيص {p['license']} يحتاج قرار المالك قبل الدمج"
        d = _ROOT / p["path"]
        lic = [x for x in d.iterdir() if x.is_file() and x.name.lower().startswith(("license", "licence", "copying"))]
        assert lic, f"{p['repo']}: ملف الترخيص الأصلي مفقود"
        assert len(p["commit"]) == 40, f"{p['repo']}: الإصدار غير مثبت"


def test_vendored_trees_unmodified():
    for p in _manifest()["projects"]:
        assert _tree_sha256(_ROOT / p["path"]) == p["tree_sha256"], (
            f"{p['repo']}: النسخة المدمجة عُدّلت محليًا — التعديل مكانه كود المشروع (backend/search_agents)، "
            "أو أعد المزامنة بـ scripts/vendor_sync.py")


def test_every_project_wired_to_a_search_capability():
    sys.path.insert(0, str(_ROOT / "backend"))
    import search_agents
    caps = search_agents.registry()
    for p in _manifest()["projects"]:
        c = caps.get(p["repo"])
        assert c and c.get("capability") and c.get("mode") in ("runtime", "ported", "source"), \
            f"{p['repo']}: غير مربوط بقدرة في محرك البحث"
        if c["mode"] in ("runtime", "ported"):  # يعمل/منقول ⇒ وحدة حقيقية في كود المشروع تستورد
            assert c["module"] and importlib.import_module(c["module"]), f"{p['repo']}: وحدة الربط مفقودة"
        if c["mode"] in ("ported", "source"):  # المرجع المنقول عنه/الموصوف موجود فعلًا في النسخة المسحوبة
            assert (_ROOT / p["path"] / c["reference"]).exists(), f"{p['repo']}: المرجع {c['reference']} غير موجود"
    assert set(caps) == {p["repo"] for p in _manifest()["projects"]}, "سجل القدرات لا يطابق المشاريع المسحوبة"


def test_runtime_libraries_load_from_vendored_copy():
    """runtime = الكود المسحوب نفسه يعمل: كل وحدة تُحمَّل وملفها داخل third_party/ (لا نسخة PyPI أخرى)."""
    sys.path.insert(0, str(_ROOT / "backend"))
    from search_agents import vendored
    for name, st in vendored.status().items():
        assert st["loaded"], f"{name}: {st['error']}"
        f = Path(st["file"]).resolve()
        assert "third_party" in f.parts or (vendored.ROOT / vendored._PATHS[name]).name in str(f) \
            or _same_tree(name, f), f"{name} حُمّلت من {f} لا من النسخة المسحوبة"


def _same_tree(name: str, f: Path) -> bool:
    """حزمة مثبتة من third_party (pip install ./third_party/X) ⇒ ملفها مطابق بايتيًا لنظيره المسحوب."""
    from search_agents import vendored
    base = vendored.ROOT / vendored._PATHS[name]
    rel = [q for q in base.rglob(f.name) if q.parent.name == f.parent.name]
    return any(q.read_bytes() == f.read_bytes() for q in rel)
