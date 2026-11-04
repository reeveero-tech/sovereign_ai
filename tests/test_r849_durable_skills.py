# -*- coding: utf-8 -*-
"""اختبارات R-849 — دوام المهارات عبر إعادة النشر (الطبقة ٨، D-064).

RED على main أثبت (forensics/R-849_skills_RED.txt): مهارة معتمدة تُفقد مع
محو القرص المؤقت، والمخزن الدائم الموجود لا تلمسه المهارات، والحالة لا تعلن
الدوام. هنا GREEN: كتابة نافذة، استعادة بفحص البصمة، رفض مغلق للأسرار،
تعافٍ محلي عند غياب المخزن، وسياسة تعارض موثقة.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from test_skills import ctx, _manifest  # noqa: E402,F401  عدة R-757 نفسها
ctx  # noqa: B018,F841  (المُعلمة تحمل الاسم نفسه في التواقيع أدناه)

OWNER_KEY = "test_master_key_1234567890abcdef"


# ===================================================================== عدة
class FakeStore:
    """مخزن دائم مزيف — ذاكرة فقط، يحاكي SupabaseDisk بثلاث دوال."""

    backend = "fake-memory"

    def __init__(self, fail=False):
        self.blobs: dict = {}
        self.fail = fail
        self.saved = []

    def save_blob(self, namespace, key, payload):
        if self.fail:
            return False
        self.blobs[f"{namespace}/{key}"] = json.loads(json.dumps(payload))
        self.saved.append(key)
        return True

    def load_blob(self, namespace, key):
        return self.blobs.get(f"{namespace}/{key}")

    def list_blobs(self, namespace, limit=1000, offset=0):
        if self.fail:
            raise RuntimeError("store unreachable")
        return [{"key": k.split("/", 1)[1], "payload": v}
                for k, v in self.blobs.items() if k.startswith(f"{namespace}/")]


def _durable_lib(ctx, store, root=None):
    from skills import SkillLibrary
    from skills_durable import SkillsDurable
    reg, fc, tmp = ctx
    root = root or (tmp / "skills")
    dur = SkillsDurable(root, store, audit=lambda op, p: fc.events.append((op, p)))
    return SkillLibrary(root, reg, durable=dur)


def _full_cycle(lib, version="1.0.0", expect=10, actor="author"):
    lib.propose(_manifest(version, expect), actor=actor)
    lib.evaluate("add_then_double", version)
    lib.evaluate_independent(
        "add_then_double", version,
        [{"inputs": {"a": 5, "b": 1}, "expect": 12},
         {"inputs": {"a": -1, "b": 4}, "expect": 6}], actor="owner")
    return lib.approve("add_then_double", version, actor="owner")


def _pkg_file(root, version):
    return Path(root) / "add_then_double" / f"{version}.json"


# ===================================================================== الدوام
def test_r849_skill_survives_disk_wipe(ctx):
    """العيبة D1: دورة كاملة ثم محو القرص المؤقت (إعادة نشر) ⇒ المهارة تعود."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    out = _full_cycle(lib)
    assert out["active"] == "1.0.0"
    shutil.rmtree(lib.root)                       # إعادة النشر: القرص المؤقت يُمحى
    lib2 = _durable_lib(ctx, store, root=lib.root)
    loaded = lib2.load_active()                   # إقلاع جديد
    assert loaded == ["skill.add_then_double"]
    assert lib2.status()["skills"][0]["active"] == "1.0.0"


def test_r849_write_through_on_every_transition(ctx):
    """الكتابة النافذة: propose ثم كل تقييم ثم الاعتماد — البعيد طازج دائمًا."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    lib.propose(_manifest(), actor="author")
    assert "pkg:add_then_double:1.0.0" in store.saved
    lib.evaluate("add_then_double", "1.0.0")
    remote = store.blobs["skills/pkg:add_then_double:1.0.0"]
    assert remote["state"] == "evaluated"
    lib.evaluate_independent(
        "add_then_double", "1.0.0",
        [{"inputs": {"a": 5, "b": 1}, "expect": 12},
         {"inputs": {"a": -1, "b": 4}, "expect": 6}], actor="owner")
    remote = store.blobs["skills/pkg:add_then_double:1.0.0"]
    assert remote["state"] == "independently_evaluated"
    lib.approve("add_then_double", "1.0.0", actor="owner")
    remote = store.blobs["skills/pkg:add_then_double:1.0.0"]
    assert remote["state"] == "active"
    assert store.blobs["skills/active:add_then_double"]["active"] == "1.0.0"


def test_r849_tampered_remote_refused(ctx):
    """البعيد المزوّر (بصمة لا تطابق المحتوى) لا يُكتب محليًا — رفض وأثر."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    _full_cycle(lib)
    remote = store.blobs["skills/pkg:add_then_double:1.0.0"]
    remote["manifest"]["steps"][0]["tool"] = "math.mul"   # تلاعب بلا تحديث البصمة
    shutil.rmtree(lib.root)
    lib2 = _durable_lib(ctx, store, root=lib.root)
    rep = lib2.durable.restore()
    assert rep["refused"] == ["pkg:add_then_double:1.0.0"]
    assert not _pkg_file(lib.root, "1.0.0").exists()
    ops = [e[0] for e in ctx[1].events]
    assert "skills_durable.refused_remote" in ops


def test_r849_tampered_local_repaired_from_remote(ctx):
    """المحلي التالف يُعاد من البعيد السليم — إصلاح ذاتي بأثر."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    _full_cycle(lib)
    p = _pkg_file(lib.root, "1.0.0")
    pkg = json.loads(p.read_text(encoding="utf-8"))
    pkg["manifest"]["steps"][0]["tool"] = "math.mul"      # تلاعب محلي
    p.write_text(json.dumps(pkg, ensure_ascii=False), encoding="utf-8")
    lib2 = _durable_lib(ctx, store, root=lib.root)
    rep = lib2.durable.restore()
    assert rep["repaired"] == ["pkg:add_then_double:1.0.0"]
    fixed = json.loads(p.read_text(encoding="utf-8"))
    assert fixed["manifest"]["steps"][0]["tool"] == "math.add"


def test_r849_valid_local_not_overwritten(ctx):
    """المحلي السليم لا يُستبدل بالبعيد — الاستعادة للغائب والتالف فقط."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    _full_cycle(lib)
    lib2 = _durable_lib(ctx, store, root=lib.root)
    rep = lib2.durable.restore()
    assert rep["restored"] == [] and rep["repaired"] == [] and rep["refused"] == []


def test_r849_no_store_local_recovery_honest(ctx):
    """غياب المخزن: المهارة تعمل محليًا، لا انهيار، والحالة تعلن بلا دوام."""
    store = FakeStore(fail=True)
    lib = _durable_lib(ctx, store)
    out = _full_cycle(lib)                       # الدورة كاملة رغم المخزن المعطوب
    assert out["active"] == "1.0.0"
    st = lib.status()["durable"]
    assert st["enabled"] is True and st["last_error"] is not None
    lib2 = _durable_lib(ctx, store, root=lib.root)
    rep = lib2.durable.restore()
    assert rep.get("error")                       # إعلان صادق لا استثناء


def test_r849_durable_false_disables(ctx):
    """durable=False تعطيل صريح: سلوك main القديم، والحالة تعلن None."""
    from skills import SkillLibrary
    reg, _, tmp = ctx
    lib = SkillLibrary(tmp / "skills2", reg, durable=False)
    assert lib.durable is None
    assert lib.status()["durable"] is None
    assert lib.sync()["error"] == "no_durable"


def test_r849_secret_never_leaves_disk(ctx):
    """سر في الحمولة ⇒ رفض مغلق للدفع، أثر، والمهارة تعمل محليًا."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    m = _manifest()
    import uuid
    m["source"] = f"owner token rnd_{uuid.uuid4().hex}"  # سر Render يُبنى وقت التشغيل (مبدأ R-848: لا مادة حقيقية في المستودع)
    lib.propose(m, actor="author")
    assert store.blobs == {}                      # لا شيء غادر القرص
    st = lib.status()["durable"]
    assert st["last_error"] == "secret_in_payload"
    ops = [e[0] for e in ctx[1].events]
    assert "skills_durable.blocked" in ops
    assert _pkg_file(lib.root, "1.0.0").exists()   # محليًا تعمل


def test_r849_rollback_syncs_remote(ctx):
    """التراجع يحدث البعيد — لا عودة للإصدار القديم بعد إعادة نشر."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    _full_cycle(lib, version="1.0.0")
    lib.propose(_manifest("2.0.0", expect=10), actor="author")
    lib.evaluate("add_then_double", "2.0.0")
    lib.evaluate_independent(
        "add_then_double", "2.0.0",
        [{"inputs": {"a": 7, "b": 2}, "expect": 18},
         {"inputs": {"a": 3, "b": 3}, "expect": 12}], actor="owner")
    lib.approve("add_then_double", "2.0.0", actor="owner")
    assert store.blobs["skills/active:add_then_double"]["active"] == "2.0.0"
    lib.rollback("add_then_double", actor="owner")
    assert store.blobs["skills/active:add_then_double"]["active"] == "1.0.0"


def test_r849_active_conflict_local_wins(ctx):
    """سياسة التعارض الموثقة: active المحلي يغلب عند وجود الاثنين، ثم يُدفع."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    _full_cycle(lib, version="1.0.0")
    lib.propose(_manifest("2.0.0", expect=10), actor="author")
    lib.evaluate("add_then_double", "2.0.0")
    lib.evaluate_independent(
        "add_then_double", "2.0.0",
        [{"inputs": {"a": 7, "b": 2}, "expect": 18},
         {"inputs": {"a": 3, "b": 3}, "expect": 12}], actor="owner")
    lib.approve("add_then_double", "2.0.0", actor="owner")      # المحلي 2.0.0
    store.blobs["skills/active:add_then_double"] = {"active": "1.0.0", "history": []}
    lib2 = _durable_lib(ctx, store, root=lib.root)
    lib2.durable.restore()                     # الاستعادة لا تمس active القائم
    act = json.loads((lib.root / "add_then_double" / "active.json")
                     .read_text(encoding="utf-8"))
    assert act["active"] == "2.0.0"
    lib2.sync()  # الدفع يعيد البعيد طازجًا
    assert store.blobs["skills/active:add_then_double"]["active"] == "2.0.0"


def test_r849_sync_pushes_local_missing_remote(ctx):
    """sync يدفع كل ما هو محلي وغائب بعيدًا — تقرير موثق بعدد المدفوع."""
    store = FakeStore()
    lib = _durable_lib(ctx, store, root=ctx[2] / "skills_sync")
    _full_cycle(lib)
    store.blobs.clear()                          # البعيد فقد كل شيء
    rep = lib.sync()
    assert rep["pushed"] == 2                    # حزمة 1.0.0 + active
    assert "skills/pkg:add_then_double:1.0.0" in store.blobs


def test_r849_status_declares_durability(ctx):
    """الصدق: الحالة تعلن المخزن واسمه — لا وهم دوام بلا مخزن."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    st = lib.status()["durable"]
    assert st["backend"] == "fake-memory" and st["enabled"] is True
    from skills import SkillLibrary
    reg, _, tmp = ctx
    plain = SkillLibrary(tmp / "skills_plain", reg, durable=False)
    assert plain.status()["durable"] is None


def test_r849_load_active_boot_integration(ctx):
    """إقلاع كامل: قرص محايد + بعيد سليم ⇒ الأداة مسجلة وتعمل."""
    from tool_registry import ToolRegistry, ToolSpec
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    _full_cycle(lib)
    reg2 = ToolRegistry()
    reg2.register(ToolSpec(name="math.add", description="", inputs={"a": "", "b": ""},
                           outputs="sum", handler=lambda a, b: {"sum": int(a) + int(b)}))
    reg2.register(ToolSpec(name="math.mul", description="", inputs={"a": "", "b": ""},
                           outputs="product", handler=lambda a, b: {"product": int(a) * int(b)}))
    from skills_durable import SkillsDurable
    dur = SkillsDurable(lib.root, store)
    from skills import SkillLibrary
    lib2 = SkillLibrary(lib.root, reg2, durable=dur)
    shutil.rmtree(lib.root)                      # نشر جديد: قرص نظيف
    loaded = lib2.load_active()
    assert loaded == ["skill.add_then_double"]
    out = reg2.invoke("skill.add_then_double", caller="owner",
                      inputs={"a": 2, "b": 3})
    assert out["ok"] and out["result"]["output"] == 10
    assert lib2.status()["skills"][0]["active"] == "1.0.0"


def test_r849_restore_verifies_content_hash_before_write(ctx):
    """حزمة بعيدة بلا بصمة صالحة لا تُكتب حتى لو غابت محليًا."""
    store = FakeStore()
    lib = _durable_lib(ctx, store)
    _full_cycle(lib)
    remote = store.blobs["skills/pkg:add_then_double:1.0.0"]
    del remote["content_hash"]                   # سجل بلا بصمة
    shutil.rmtree(lib.root)
    lib2 = _durable_lib(ctx, store, root=lib.root)
    rep = lib2.durable.restore()
    assert rep["refused"] == ["pkg:add_then_double:1.0.0"]


# ===================================================================== الواجهة
def test_r849_sync_endpoint_owner_only(monkeypatch, ctx):
    from fastapi.testclient import TestClient
    import app as app_mod
    with TestClient(app_mod.app) as client:
        assert client.post("/skills/sync", json={}).status_code == 401
        assert client.post("/skills/sync", json={"api_key": "wrong"}).status_code == 401


def test_r849_sync_endpoint_calls_sync(monkeypatch, ctx):
    from fastapi.testclient import TestClient
    import app as app_mod
    monkeypatch.setattr(app_mod, "verify_api_key", lambda k: True)
    called = {}
    import skills as skills_mod

    class FakeLib:
        def sync(self):
            called["yes"] = True
            return {"backend": "fake", "pushed": 0, "restored": []}

    monkeypatch.setattr(skills_mod, "get_library", lambda: FakeLib())
    with TestClient(app_mod.app) as client:
        r = client.post("/skills/sync", json={"api_key": OWNER_KEY})
        assert r.status_code == 200 and called["yes"] is True
        assert r.json()["backend"] == "fake"


def test_r849_suite_registered_and_green():
    from evaluation import suites
    s = suites.get("skills.durability")
    assert s.floor == 1.0 and s.data_path.name == "skills_cases.json"
    assert suites.file_sha256(s.data_path) == \
        "60c52e31db13b24c4a8200acdeb29b65564286b0ca274f5ca3db489db9253761"
    r = s.runner(s.data_path)
    assert r["score"] == 1.0 and r["n"] == 15, r["failures"]
