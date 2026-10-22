"""R-719 — قرص المشروع وذاكرته على Supabase (بأمر المالك 2026-10-22).

الطبقة: backend/sovereign/cloud_disk.py — SupabaseDisk فوق PostgREST:
- جدول `disk` (KV بالإدراج-التحديث) — «القرص» الدائم
- جدول `disk_log` (إلحاقي صرف) — «الذاكرة» الجارية
معطلة افتراضيًا؛ تُفعّل بـ SUPABASE_URL + SUPABASE_SECRET_KEY (نمط Ollama R-704).
المفتاح سر خدمة — لا يدخل git أبدًا. الحمولات المخزنة مشفرة AES-256-GCM قبل
الوصول للطبقة (عقد المخزن «دائم، مشفر» قائم).

الاختبارات بلا شبكة: httpx.MockTransport يلعب دور PostgREST.
"""

import os

import httpx
import pytest



# -------------------------
# الوحدة: backend/sovereign/cloud_disk.py
# -------------------------

def _make_disk(handler) -> "object":
    from backend.sovereign.cloud_disk import SupabaseDisk
    return SupabaseDisk(
        base_url="https://example.supabase.co",
        service_key="sb_secret_test",
        transport=httpx.MockTransport(handler),
    )


def test_module_exists_and_disabled_by_default(monkeypatch):
    """الطبقة معطلة بلا إعداد — get_cloud_disk() تعيد None (نمط Ollama)."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    from backend.sovereign import cloud_disk
    assert cloud_disk.cloud_disk_enabled() is False
    assert cloud_disk.get_cloud_disk() is None


def test_enabled_only_with_both_settings(monkeypatch):
    """العلم لا يكفي — المفتاح والرابط معًا أو لا شيء (fail-closed للإعداد)."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    from backend.sovereign import cloud_disk
    assert cloud_disk.cloud_disk_enabled() is False
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    assert cloud_disk.cloud_disk_enabled() is True
    disk = cloud_disk.get_cloud_disk()
    assert disk is not None
    assert disk.base_url == "https://example.supabase.co"


def test_save_blob_upsert_and_load_roundtrip():
    """القرص: حفظ (upsert عبر Prefer) ثم قراءة بالمفتاح المركّب."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if request.method == "POST" and "/rest/v1/disk" == request.url.path:
            assert request.headers.get("prefer") == "resolution=merge-duplicates"
            return httpx.Response(201, json=[])
        if request.method == "GET" and "/rest/v1/disk" == request.url.path:
            assert "namespace=eq.memory" in str(request.url)
            assert "key=eq.semantic" in str(request.url)
            return httpx.Response(200, json=[{"payload": {"items": [1, 2]}}])
        return httpx.Response(404)

    disk = _make_disk(handler)
    assert disk.save_blob("memory", "semantic", {"items": [1, 2]}) is True
    payload = disk.load_blob("memory", "semantic")
    assert payload == {"items": [1, 2]}
    assert ("POST", "https://example.supabase.co/rest/v1/disk") in calls


def test_load_blob_missing_returns_none():
    """لا نسخة في القرص → None (لا استثناء)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    disk = _make_disk(handler)
    assert disk.load_blob("memory", "nope") is None


def test_append_and_pull_log():
    """الذاكرة الجارية: إلحاق صرف + قراءة تدريجية (id=gt + order)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "/rest/v1/disk_log" == request.url.path:
            return httpx.Response(201, json=[])
        if request.method == "GET" and "/rest/v1/disk_log" == request.url.path:
            url = str(request.url)
            assert "namespace=eq.audit" in url and "id=gt.7" in url and "order=id.asc" in url
            return httpx.Response(200, json=[
                {"id": 8, "payload": {"m": "first"}},
                {"id": 9, "payload": {"m": "second"}},
            ])
        return httpx.Response(404)

    disk = _make_disk(handler)
    assert disk.append_log("audit", {"m": "first"}) is True
    rows = disk.pull_log("audit", since_id=7)
    assert [r["id"] for r in rows] == [8, 9]


def test_unreachable_disk_is_best_effort_not_fatal():
    """القرص السحابي بعيد/معطل → False وتحذير، لا استثناء يكسر الكتابة المحلية."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("cloud unreachable", request=request)

    disk = _make_disk(handler)
    assert disk.save_blob("memory", "semantic", {"x": 1}) is False
    assert disk.append_log("audit", {"x": 1}) is False
    assert disk.load_blob("memory", "semantic") is None


# -------------------------
# الوصل: مرآة المخزن الصلب (SolidMemoryStore)
# -------------------------

def test_store_save_mirrors_to_cloud_when_enabled(monkeypatch, tmp_path):
    """_save_kind يكتب محليًا ثم يرفع النسخة (المشفرة أصلًا) إلى القرص السحابي."""
    monkeypatch.setattr(
        "backend.memory.store.FILE_MAP",
        {k: tmp_path / f"{k}.json" for k in (
            "procedural", "semantic", "episodic", "spatial",
            "emotional", "associative", "index", "backup")},
    )
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path == "/rest/v1/disk" and request.method == "POST":
            return httpx.Response(201, json=[])
        return httpx.Response(200, json=[])

    from backend.memory import store as store_mod
    monkeypatch.setattr(store_mod, "_get_cloud_disk", lambda: _make_disk(handler))
    st = store_mod.SolidMemoryStore()
    st.save("semantic", {"concept": "قرص", "definition": "سحابي"})
    assert any("/rest/v1/disk" in s for s in seen), "لم تُرفع المرآة إلى القرص السحابي"


def test_store_save_noop_when_cloud_disabled(monkeypatch, tmp_path):
    """بلا إعداد: الكتابة المحلية تعمل كالمعتاد وصفر محاولات شبكة (لا كسر)."""
    monkeypatch.setattr(
        "backend.memory.store.FILE_MAP",
        {k: tmp_path / f"{k}.json" for k in (
            "procedural", "semantic", "episodic", "spatial",
            "emotional", "associative", "index", "backup")},
    )
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    from backend.memory import store as store_mod
    st = store_mod.SolidMemoryStore()
    st.save("semantic", {"concept": "محلي", "definition": "بلا سحابة"})
    # الملف المحلي كُتب
    assert (tmp_path / "semantic.json").exists()


def test_store_restores_from_cloud_when_local_missing(monkeypatch, tmp_path):
    """إقلاع على قرص فارغ (إعادة نشر) + نسخة سحابية موجودة → استرجاع قبل التحميل."""
    monkeypatch.setattr(
        "backend.memory.store.FILE_MAP",
        {k: tmp_path / f"{k}.json" for k in (
            "procedural", "semantic", "episodic", "spatial",
            "emotional", "associative", "index", "backup")},
    )
    from backend.memory import store as store_mod

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/disk" and request.method == "GET":
            return httpx.Response(200, json=[{"payload": {
                "kind": "semantic",
                "items": [],  # عناصر مشفرة فارغة — يكفي إثبات مسار الاسترجاع
            }}])
        return httpx.Response(200, json=[])

    monkeypatch.setattr(store_mod, "_get_cloud_disk", lambda: _make_disk(handler))
    st = store_mod.SolidMemoryStore()
    assert (tmp_path / "semantic.json").exists(), "لم يُسترجع الملف من القرص السحابي"


# -------------------------
# النقطة: /disk/status (قراءة فقط، بلا سر في المخرجات)
# -------------------------

def test_disk_status_endpoint_disabled(monkeypatch):
    """المعطّل (الافتراضي) → 200 مع enabled=False بلا أي تفاصيل."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        r = client.get("/disk/status")
        assert r.status_code == 200
        assert r.json() == {"cloud_disk": "disabled", "enabled": False}


def test_disk_status_endpoint_enabled_no_secret_leak(monkeypatch):
    """المفعّل → الحالة ببصمة المفتاح فقط — لا سر في المخرجات أبدًا."""
    import backend.sovereign.cloud_disk as cloud_disk_mod

    class _Stub:
        def status(self):
            return {
                "enabled": True,
                "base_url": "https://x.supabase.co",
                "key_fingerprint": "abc123def456",
                "timeout_seconds": 10.0,
                "reachable": True,
            }

    monkeypatch.setattr(cloud_disk_mod, "get_cloud_disk", lambda: _Stub())
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        r = client.get("/disk/status")
        assert r.status_code == 200
        data = r.json()
        assert data["cloud_disk"] == "enabled" and data["enabled"] is True
        assert data["key_fingerprint"] == "abc123def456"
        assert "sb_secret" not in r.text
        assert "SUPABASE_SECRET_KEY" not in r.text


# -------------------------
# R-721 (تصويبي) — مراجعة المراجع: عزل، ذاكرة клиент، استرجاع غير فارغ
# -------------------------

def test_supabase_env_falls_back_to_repo_root_dotenv(monkeypatch, tmp_path):
    """توثيق .env.example يقول إن .env بجذر المشروع يفعّل الطبقة — الكود كان
    يقرأ SUPABASE_ENV_FILE فقط (تناقض وثّقه المراجع). يجب أن يعود للجذر."""
    import backend.sovereign.cloud_disk as cloud_disk_mod
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ENV_FILE", raising=False)
    envfile = tmp_path / ".env"
    envfile.write_text(
        "SUPABASE_URL=https://from-dotenv.supabase.co\n"
        'SUPABASE_SECRET_KEY="sb_secret_dotenv"\n', encoding="utf-8")
    monkeypatch.setattr(cloud_disk_mod, "_DOTENV_PATH", envfile)
    disk = cloud_disk_mod.get_cloud_disk()
    assert disk is not None, "يجب أن يقرأ .env بجذر المشروع (كما يوثق .env.example)"
    assert disk.base_url == "https://from-dotenv.supabase.co"
    assert disk.service_key == "sb_secret_dotenv"


def test_cloud_disk_disabled_in_test_session(monkeypatch):
    """عزل بالبناء (نمط R-720 لـOllama): conftest يفرض SUPABASE_ENV_FILE على
    مسار غير موجود — حتى لو مُلئ .env الحقيقي بإعدادات المالك، الاختبارات
    لا تلمس السحابة الحقيقية أبدًا."""
    import os
    import backend.sovereign.cloud_disk as cloud_disk_mod
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    env_file = os.environ.get("SUPABASE_ENV_FILE")
    assert env_file, "conftest يجب أن يفرض SUPABASE_ENV_FILE (عزل الاختبارات)"
    assert not os.path.exists(env_file), (
        "مسار العزل يجب أن يكون غير موجود — ملف إعداد حقيقي هنا يعني أن "
        "الاختبارات تستطيع لمس سحابة المالك"
    )
    assert cloud_disk_mod.get_cloud_disk() is None, (
        "داخل جلسة الاختبار الطبقة يجب أن تكون معطلة مهذا كان في .env"
    )


def test_get_cloud_disk_caches_client(monkeypatch):
    """المراجع: مثيل جديد لكل استدعاء = تسريب اتصالات httpx. يجب تخزين
    المثيل (يتجدد فقط عند تغير الإعداد)."""
    import backend.sovereign.cloud_disk as cloud_disk_mod
    monkeypatch.setenv("SUPABASE_URL", "https://cache-test.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_cache")
    d1 = cloud_disk_mod.get_cloud_disk()
    d2 = cloud_disk_mod.get_cloud_disk()
    assert d1 is d2, "المثيل يجب أن يكون مخزنًا (لا عميل httpx جديد لكل استدعاء)"
    # تغير الإعداد → مثيل جديد
    monkeypatch.setenv("SUPABASE_URL", "https://other.supabase.co")
    d3 = cloud_disk_mod.get_cloud_disk()
    assert d3 is not d1 and d3.base_url == "https://other.supabase.co"


def test_store_roundtrip_via_cloud_nonempty(monkeypatch, tmp_path):
    """المراجع: استرجاع بقائمة فارغة لا يثبت استعادة ذاكرة مفيدة. الدورة
    الكاملة: حفظ حقيقي (مشفر) → المرآة ترفعه → مخزن جديد بجذر محلي فارغ
    يسترجعه → العنصر يُحمّل ويُفك تشفيره ويُسترجع فعلًا."""
    import json as _json
    from backend.memory import store as store_mod
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/disk" and request.method == "POST":
            body = _json.loads(request.content)
            captured[body["key"]] = body["payload"]
            return httpx.Response(201)
        if request.url.path == "/rest/v1/disk" and request.method == "GET":
            key = request.url.params.get("key", "").removeprefix("eq.")
            if key in captured:
                return httpx.Response(200, json=[{"payload": captured[key]}])
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[])

    def _fresh_map():
        return {k: tmp_path / f"{k}.json" for k in (
            "procedural", "semantic", "episodic", "spatial",
            "emotional", "associative", "index", "backup")}

    # ١) حفظ حقيقي في مخزن أول — المرآة تلتقط الحمولة المشفرة
    monkeypatch.setattr(store_mod, "FILE_MAP", _fresh_map())
    monkeypatch.setattr(store_mod, "_get_cloud_disk", lambda: _make_disk(handler))
    st1 = store_mod.SolidMemoryStore()
    st1.save("semantic", {"concept": "القرص", "definition": "دائم عبر السحابة"})
    assert "semantic" in captured, "المرآة يجب أن ترفع نوع الذاكرة"
    item_ids = [it["id"] for it in captured["semantic"]["items"]]
    assert item_ids, "الحمولة المرفوعة يجب أن تحوي عنصرًا فعليًا (غير فارغة)"
    # الحمولة مشفرة: لا نص صريح للتعريف داخل الحمولة المرفوعة
    dumped = _json.dumps(captured["semantic"], ensure_ascii=False)
    assert "دائم عبر السحابة" not in dumped, "الحمولة يجب أن تكون مشفرة قبل الرفع"

    # ٢) مخزن جديد بجذر محلي فارغ (قرص ضاع) — الاسترجاع من السحابة
    empty_dir = tmp_path / "fresh"
    empty_dir.mkdir()
    monkeypatch.setattr(store_mod, "FILE_MAP", {
        k: empty_dir / f"{k}.json" for k in store_mod.FILE_MAP})
    monkeypatch.setattr(store_mod, "_get_cloud_disk", lambda: _make_disk(handler))
    st2 = store_mod.SolidMemoryStore()
    loaded = st2._data.get("semantic", {})
    assert item_ids[0] in loaded, (
        "العنصر المحفوظ في المخزن الأول يجب أن يُسترجع في المخزن الجديد "
        "(_data مفهرسة بمعرف العنصر)"
    )
    # ٣) فك التشفير يعمل: العنصر المسترجع يقرأ قيمته الأصلية
    item = loaded[item_ids[0]]
    payload = st2._decrypt_payload(item.encrypted_payload, "semantic")
    assert payload["definition"] == "دائم عبر السحابة", (
        "الاسترجاع يجب أن يعيد القيمة الأصلية بعد فك التشفير"
    )
