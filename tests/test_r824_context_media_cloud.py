"""R-824: سياق المحادثة + استوديو الصور/الفيديو + العقل السحابي الاحتياطي — اختبارات بلا شبكة."""
import io

import pytest

import chat_agent
import cloud_brain
import context_resolver as cr
import media_studio as ms
import ollama_client
import world_search as w


# ---------------------------------------------------------------- محلل السياق
HIST_JP = [{"role": "user", "content": "ما هي عاصمة اليابان"},
           {"role": "assistant", "content": "عاصمة اليابان هي طوكيو [1]."}]


def test_followup_pronoun_resolves_to_entity():
    r = cr.resolve("وكم عدد سكانها", HIST_JP)
    assert r["followup"] is True
    assert "اليابان" in r["standalone"] and "سكان" in r["standalone"]


def test_followup_entity_swap_keeps_question_frame():
    r = cr.resolve("وماذا عن فرنسا", HIST_JP)
    assert r["kind"] == "entity_swap"
    assert "فرنسا" in r["standalone"] and "عاصمة" in r["standalone"]


def test_followup_english():
    hist = [{"role": "user", "content": "What is the capital of Japan"},
            {"role": "assistant", "content": "Tokyo [1]."}]
    assert "France" in cr.resolve("what about France", hist)["standalone"]
    assert "Japan" in cr.resolve("what is its population", hist)["standalone"]


def test_standalone_question_untouched():
    r = cr.resolve("ما هي عاصمة ألمانيا", HIST_JP)
    assert r["followup"] is False and r["standalone"] == r["original"]
    assert cr.resolve("مرحبا", None)["followup"] is False


def test_last_media_prompt_parsed_from_history():
    hist = [{"role": "assistant", "content": "تم إنشاء الصورة\nالوصف المستخدم: a cat in a garden, photo"}]
    assert cr.last_media_prompt(hist) == "a cat in a garden, photo"


# ---------------------------------------------------------------- استوديو الوسائط
def test_media_detect_image_video_and_excludes_non_media():
    assert ms.detect("صمم لي شعار لمطعم القمة")["kind"] == "image"
    assert ms.detect("اصنع فيديو قصير عن فوائد الرياضة")["kind"] == "video"
    assert ms.detect("draw a cat in a garden")["kind"] == "image"
    assert ms.detect("صمم لي موقع ويب لمتجري") is None
    assert ms.detect("ما هي عاصمة اليابان") is None


def test_media_edit_followup_uses_previous_prompt():
    hist = [{"role": "user", "content": "ارسم قطة في حديقة"},
            {"role": "assistant", "content": "تم إنشاء الصورة\nالوصف المستخدم: a cat in a garden, photo"}]
    req = ms.detect("اجعلها ليلية", hist)
    assert req and req["kind"] == "image" and req["edit_of"] == "a cat in a garden, photo"


def test_design_local_is_valid_png():
    from PIL import Image
    data, mime = ms.design_local("مطعم القمة", (512, 512), "logo", "الذكاء السيادي")
    assert mime == "image/png"
    im = Image.open(io.BytesIO(data))
    assert im.size == (512, 512)


def test_arabic_prompt_never_sent_to_ai_generators(monkeypatch):
    called = []
    monkeypatch.setenv("MEDIA_EXTERNAL_PROVIDERS", "pollinations,horde")
    monkeypatch.setattr(ms, "_gen_pollinations", lambda p, s: called.append(p))
    monkeypatch.setattr(ms, "_gen_horde", lambda p, s: called.append(p))
    monkeypatch.setattr(ms, "media_client_configured", lambda: False)
    g = ms.generate_image("قطة في حديقة, photo", "قطة في حديقة", "photo", (256, 256))
    assert called == [], "وصف عربي غير مترجم لا يصل لمولد قد يهلوس"
    assert g["provider"] == "local_design" and g["ai"] is False
    assert any(t["provider"] == "translation" for t in g["tried"])


def test_provider_chain_falls_through_to_local(monkeypatch):
    monkeypatch.setenv("MEDIA_EXTERNAL_PROVIDERS", "pollinations,horde")
    monkeypatch.setattr(ms, "media_client_configured", lambda: False)

    def boom(p, s):
        raise RuntimeError("HTTP 429")
    monkeypatch.setattr(ms, "_gen_pollinations", boom)
    monkeypatch.setattr(ms, "_gen_horde", lambda p, s: None)
    g = ms.generate_image("a cat in a garden, photo", "قطة", "photo", (256, 256))
    assert g["ok"] and g["provider"] == "local_design"
    assert [t["provider"] for t in g["tried"]][:1] == ["pollinations"]


def test_provider_chain_uses_first_working(monkeypatch):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 20, 30)).save(buf, "PNG")
    monkeypatch.setenv("MEDIA_EXTERNAL_PROVIDERS", "pollinations")
    monkeypatch.setattr(ms, "media_client_configured", lambda: False)
    monkeypatch.setattr(ms, "_gen_pollinations", lambda p, s: (buf.getvalue(), "image/png"))
    g = ms.generate_image("a cat, photo", "قطة", "photo", (64, 64))
    assert g["provider"] == "pollinations" and g["ai"] is True


@pytest.mark.skipif(not ms.ffmpeg_exe(), reason="ffmpeg غير متاح")
def test_compose_video_is_real_mp4():
    img, _ = ms.design_local("اختبار", (320, 180), "poster", "x")
    data = ms.compose_video(img, "عنوان", "وصف", size=(320, 180))
    assert data[4:8] == b"ftyp" and len(data) > 1000


def test_format_reply_grammar():
    base = {"ok": True, "seconds": 1, "provider": "local_design", "tried": [], "prompt": "p"}
    assert "معروضة أدناه" in ms.format_reply(dict(base, kind="image"))
    assert "معروض أدناه" in ms.format_reply(dict(base, kind="video"))


# ---------------------------------------------------------------- العقل السحابي
WORLD = {"points": [{"text": "نقطة موثقة", "source": 1}],
         "sources": [{"n": 1, "title": "NHS", "url": "https://www.nhs.uk/x"}], "user_lang": "ar"}


def test_grounded_rejects_invented_citations(monkeypatch):
    monkeypatch.setattr(cloud_brain, "chat", lambda *a, **k: "حقيقة مخترعة [7].")
    assert cloud_brain.grounded("س", WORLD) is None
    monkeypatch.setattr(cloud_brain, "chat", lambda *a, **k: "بلا أي استشهاد.")
    assert cloud_brain.grounded("س", WORLD) is None
    monkeypatch.setattr(cloud_brain, "chat", lambda *a, **k: "جواب موثق [1].")
    assert cloud_brain.grounded("س", WORLD)["text"] == "جواب موثق [1]."


def test_rate_limit_latch_honours_retry_after(monkeypatch):
    import httpx
    monkeypatch.setenv("CLOUD_BRAIN_ENABLED", "true")
    monkeypatch.setattr(cloud_brain, "_NEXT_ALLOWED", 0.0)
    sent = []

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            sent.append(json)
            return httpx.Response(429, text="Queue full. Retry after 300s",
                                  request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "Client", FakeClient)
    assert cloud_brain.chat("s", "u") is None
    assert cloud_brain.status()["next_available_in_seconds"] > 200
    assert cloud_brain.chat("s", "u") is None
    assert len(sent) == 1, "المزلاج يمنع طوفان طلبات مرفوضة"
    monkeypatch.setattr(cloud_brain, "_NEXT_ALLOWED", 0.0)


def test_cloud_brain_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CLOUD_BRAIN_ENABLED", raising=False)
    assert cloud_brain.chat("s", "u") is None


# ---------------------------------------------------------------- التكامل عبر /chat
@pytest.fixture
def client(monkeypatch, tmp_path):
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient
    from workspace.service import Workspace, reset_workspace
    from workspace.storage import LocalStorage
    reset_workspace(Workspace(LocalStorage(tmp_path / "files"), None, local_root=tmp_path / "idx"))
    chat_rate_limiter._requests.clear()
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
    monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: True)
    monkeypatch.setattr(ms, "media_client_configured", lambda: False)
    monkeypatch.setenv("MEDIA_EXTERNAL_PROVIDERS", "")
    monkeypatch.delenv("CLOUD_BRAIN_ENABLED", raising=False)
    with TestClient(fastapi_app) as c:
        yield c
    reset_workspace(None)


def test_media_create_registered():
    from app import app  # noqa: F401
    from tool_registry import get_registry
    tools = {t["name"] for t in get_registry().list_tools()}
    assert "media.create" in tools and "media.image" in tools


def test_chat_image_request_returns_signed_media(client):
    body = client.post("/chat", json={"text": "صمم لي شعار لمطعم القمة", "user_id": "t"}).json()
    assert body["agent_status"] == "media_created", body
    m = body["media"][0]
    assert m["type"] == "image" and m["url"].startswith("/media/file/F-")
    r = client.get(m["url"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/")
    bad = m["url"].rsplit("sig=", 1)[0] + "sig=" + "0" * 32
    assert client.get(bad).status_code == 404
    assert "الوصف المستخدم" in body["reply"]


def test_media_status_route_not_shadowed(client):
    assert client.get("/media/status").status_code == 200


def test_chat_followup_reaches_world_search_as_standalone(client, monkeypatch):
    import chat_tools
    seen = []
    monkeypatch.setattr(chat_tools, "gather", lambda t, c: {"context": "", "tools_used": [], "direct_reply": None})
    monkeypatch.setattr(w, "enabled", lambda: True)

    def fake_answer(question, target_lang=None):
        seen.append(question)
        return {"ok": True, "points": [{"text": "نحو 123 مليون", "source": 1, "translator": "identity", "lang": "ar"}],
                "sources": [{"n": 1, "title": "Wikidata", "url": "https://www.wikidata.org/wiki/Q17",
                             "credibility_label": "مرجع", "provider": "wikidata"}],
                "languages_searched": ["en"], "sources_considered": 1, "candidates_evaluated": 1,
                "user_lang": "ar", "method": "منهج"}
    monkeypatch.setattr(w, "answer", fake_answer)
    body = client.post("/chat", json={"text": "وكم عدد سكانها", "user_id": "t", "history": HIST_JP}).json()
    assert seen and "اليابان" in seen[0], seen
    assert "اليابان" in (body.get("resolved_question") or "")
    assert "123" in body["reply"]


def test_brain_status_reports_cloud_fallback(client):
    b = client.get("/brain/status").json()
    if b.get("enabled"):
        assert "cloud_fallback" in b


def test_evolution_initialises_stats_before_threads():
    import inspect
    from memory.biological.evolution import MemoryEvolution
    src = inspect.getsource(MemoryEvolution.__init__)
    assert src.index("self.stats") < src.index("start_managed"), "الحلقة الخلفية تكتب stats — تهيئتها أولًا"


def test_arabic_shaping_fallback_without_raqm():
    """بلا libraqm (منصة النشر قد تفتقده) يُشكَّل العربي ويُرتب بصريًا بدل حروف منفصلة معكوسة."""
    from PIL import ImageFont
    from workspace.video import shape
    vis = shape("مطعم القمة", ImageFont.Layout.BASIC)
    assert vis != "مطعم القمة" and any(0xFE70 <= ord(ch) <= 0xFEFF for ch in vis), "أشكال العرض المتصلة"
    assert shape("مطعم القمة", ImageFont.Layout.RAQM) == "مطعم القمة"
    assert shape("Hello", ImageFont.Layout.BASIC) == "Hello"


def test_remote_generators_race_and_fastest_wins(monkeypatch):
    """المولدات الخارجية تعمل بالتوازي: الأسرع يفوز ولا انتظار تسلسلي لمولّد محدود المعدل."""
    import time as _t
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 100, 50)).save(buf, "PNG")
    monkeypatch.setenv("MEDIA_EXTERNAL_PROVIDERS", "pollinations,horde")
    monkeypatch.setattr(ms, "media_client_configured", lambda: False)

    def slow(p, s):
        _t.sleep(1.5)
        raise RuntimeError("HTTP 402")
    monkeypatch.setattr(ms, "_gen_pollinations", slow)
    monkeypatch.setattr(ms, "_gen_horde", lambda p, s: (buf.getvalue(), "image/png"))
    t0 = _t.time()
    g = ms.generate_image("a cat, photo", "قطة", "photo", (64, 64))
    assert g["provider"] == "horde" and _t.time() - t0 < 1.4


def test_logo_gets_correct_local_typography_over_ai_art(monkeypatch):
    """رسمة الذكاء الاصطناعي بلا نص + الاسم بطباعة محلية صحيحة (المولدات تشوه الحروف — ثبت حيًا)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (512, 512), (30, 120, 200)).save(buf, "PNG")
    monkeypatch.setenv("MEDIA_EXTERNAL_PROVIDERS", "pollinations")
    monkeypatch.setattr(ms, "media_client_configured", lambda: False)
    monkeypatch.setattr(ms, "_gen_pollinations", lambda p, s: (buf.getvalue(), "image/png"))
    en, shown = ms.build_prompt({"kind": "image", "subject": "Al Qimma Restaurant", "style": "logo", "edit_of": None})
    assert "no text" in en
    g = ms.generate_image(en, "مطعم القمة", "logo", (512, 512))
    assert g["ai"] and g["typography"]
    im = Image.open(io.BytesIO(g["data"]))
    assert im.size == (512, 512) and im.getpixel((5, 5)) != (30, 120, 200), "لوحة الشعار لا الرسمة الخام"
    assert "طباعة محلية" in ms.format_reply({"ok": True, "kind": "image", "seconds": 1, "provider": "pollinations",
                                             "tried": g["tried"], "prompt": en, "ai": True, "typography": True})


def test_grounded_reply_lists_only_cited_sources(client, monkeypatch):
    """ثبت حيًا: قائمة المصادر ضمت أبحاثًا لا علاقة لها بالجواب — الآن المستشهد بها فقط."""
    import chat_tools
    monkeypatch.setattr(chat_tools, "gather", lambda t, c: {"context": "", "tools_used": [], "direct_reply": None})
    monkeypatch.setattr(w, "enabled", lambda: True)
    monkeypatch.setattr(w, "answer", lambda question, target_lang=None: {
        "ok": True, "points": [{"text": "378 ألف كم²", "source": 1, "translator": "identity", "lang": "ar"},
                               {"text": "داء السكري", "source": 2, "translator": "identity", "lang": "ar"}],
        "sources": [{"n": 1, "title": "اليابان", "url": "https://ar.wikipedia.org/wiki/JP", "credibility_label": "موسوعة"},
                    {"n": 2, "title": "Diabetes", "url": "https://pubmed.ncbi.nlm.nih.gov/9075599/",
                     "credibility_label": "بحث"}],
        "languages_searched": ["ar"], "sources_considered": 2, "candidates_evaluated": 2, "user_lang": "ar",
        "method": "منهج"})
    monkeypatch.setattr(cloud_brain, "enabled", lambda: True)
    monkeypatch.setattr(cloud_brain, "grounded", lambda q, world, history=None: {"text": "المساحة 378 ألف كم² [1].",
                                                                                 "model": "m"})
    body = client.post("/chat", json={"text": "كم مساحة اليابان", "user_id": "t"}).json()
    assert "ar.wikipedia.org/wiki/JP" in body["reply"]
    assert "pubmed" not in body["reply"], body["reply"]
