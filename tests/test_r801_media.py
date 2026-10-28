"""R-801 (أمر المالك 2026-10-28): أدوات الوسائط — فيديو حقيقي، صور مولدة ذاتيًا، وبنية الخدمات.

المثبت هنا (سلوك حقيقي، لا أجوبة مزروعة):
1. الفيديو: ffmpeg يركّب MP4 فعليًا (مدة/ترميز/أبعاد مقروءة بـ ffprobe) من شرائح نص أو صور.
2. الخط: النص العربي يُرسم بـ Noto، وما فيه رموز خارجه (مثل «—») يُرسم بـ DejaVu.
3. الخدمة: شريحة بملف غير صورة تُرفض صراحة؛ الصوت غير الصوتي يُرفض.
4. توليد الصور: معطل = خطأ معلن بسببه (لا صورة مختلقة)؛ مفعّل = ملف PNG حقيقي في المساحة.
5. الواجهة البرمجية /ws/image و /ws/video: مفتاح المالك إلزامي، والمسار يعمل.
6. أدوات الوكيل files.image و files.video مسجلة.
7. خادم توليد الصور الذاتي: يتحقق من المدخلات (400) ويعلن حالته بصدق.
8. سير البنية: يدوي فقط، تأكيد اسم التطبيق، الأسرار لا تُضبط إلا بعد الإثبات، ولا يُطبع سر.
"""

import base64
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from workspace import video, writers  # noqa: E402
from workspace.service import Workspace, WorkspaceError, reset_workspace  # noqa: E402
from workspace.storage import LocalStorage  # noqa: E402

KEY = "r801-owner-key-test"
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
WF = REPO_ROOT / ".github" / "workflows" / "infra-services.yml"


def _png(color=(200, 30, 30), size=(320, 200)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()


def _probe(blob: bytes, tmp_path: Path):
    p = tmp_path / "v.mp4"
    p.write_bytes(blob)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height",
                          "-of", "json", str(p)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


@pytest.fixture
def ws(tmp_path):
    w = Workspace(LocalStorage(tmp_path / "files"), None, local_root=tmp_path / "idx")
    reset_workspace(w)
    yield w
    reset_workspace(None)


# ---------------- 1. الفيديو ----------------
@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg غير مثبت — الفيديو يعلن عدم التوفر")
def test_make_video_real_mp4(tmp_path):
    blob = video.make_video([{"text": "مرحبا بالعالم", "title": "عنوان"}, {"image": _png()}], 1.5)
    info = _probe(blob, tmp_path)
    assert abs(float(info["format"]["duration"]) - 3.0) < 0.4
    s = info["streams"][0]
    assert s["codec_name"] in ("h264", "mpeg4") and (s["width"], s["height"]) == (1280, 720)


def test_video_available_reports_truth():
    st = video.available()
    assert st["available"] == bool(shutil.which("ffmpeg")) and st["ai_text_to_video"] is False


def test_video_rejects_empty():
    with pytest.raises(video.VideoError):
        video.make_video([], 2)


# ---------------- 2. الخط ----------------
def test_text_slide_renders_png_with_symbols():
    from PIL import Image
    for t in ("نص عربي 123", "Mixed — symbols «quote» ✓"):
        img = Image.open(io.BytesIO(video.text_slide(t, (640, 360), "ع")))
        assert img.size == (640, 360)
        assert len(set(img.convert("L").getdata())) > 2  # رُسم نص فعلًا لا خلفية فارغة
    assert video._NOTO_OK.fullmatch("نص عربي 123")
    assert not video._NOTO_OK.fullmatch("Mixed — symbols")


# ---------------- 3. الخدمة ----------------
def test_service_video_rejects_non_image(ws):
    f = ws.add_file("a.txt", "نص".encode(), "text/plain")
    with pytest.raises(WorkspaceError, match="ليس صورة"):
        ws.make_video([{"file_id": f["id"]}], 2)
    img = ws.add_file("p.png", _png(), "image/png")
    with pytest.raises(WorkspaceError, match="ليس صوتًا"):
        ws.make_video([{"file_id": img["id"]}], 2, audio_id=f["id"])


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg غير مثبت")
def test_service_video_stored(ws, tmp_path):
    img = ws.add_file("p.png", _png(), "image/png")
    rec = ws.make_video([{"file_id": img["id"]}, {"text": "خاتمة"}], 1, title="عرضي")
    assert rec["kind"] == "video" and rec["name"].endswith(".mp4") and rec["slides"] == 2
    assert rec["source"] == "video" and rec["parent"] == img["id"]
    assert abs(float(_probe(ws.raw(rec["id"]), tmp_path)["format"]["duration"]) - 2.0) < 0.4


# ---------------- 4. توليد الصور ----------------
def test_generate_image_disabled_is_honest(ws, monkeypatch):
    import config
    monkeypatch.setattr(config, "MEDIA_ENABLED", False)
    with pytest.raises(WorkspaceError, match="غير مفعّل"):
        ws.generate_image("منارة عند الغروب")
    assert ws.list_files() == []  # لا ملف مختلق
    with pytest.raises(WorkspaceError, match="فارغ"):
        ws.generate_image("  ")


def test_generate_image_from_selfhosted_server(ws, monkeypatch):
    """خادم توليد محلي حقيقي (HTTP) يعيد PNG — media_client يتصل به فعليًا."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import config
    png = _png((10, 120, 220), (64, 64))
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen["path"] = self.path
            out = json.dumps({"data": [{"b64_json": base64.b64encode(png).decode()}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            return

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(config, "MEDIA_ENABLED", True)
        monkeypatch.setattr(config, "MEDIA_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
        rec = ws.generate_image("منارة عند الغروب", "256x256", title="منارة")
    finally:
        srv.shutdown()
    assert seen["path"] == "/v1/images/generations" and seen["body"]["prompt"] == "منارة عند الغروب"
    assert seen["body"]["size"] == "256x256"
    assert rec["kind"] == "image" and rec["source"] == "imagegen" and ws.raw(rec["id"]) == png


# ---------------- 5. الواجهة البرمجية ----------------
@pytest.fixture
def client(ws, monkeypatch):
    import app as app_mod
    from fastapi.testclient import TestClient
    monkeypatch.setattr(app_mod, "SOVEREIGN_API_KEY", KEY)
    app_mod.chat_rate_limiter._requests.clear()
    with TestClient(app_mod.app) as c:
        reset_workspace(ws)
        yield c


def test_media_api_requires_owner_key(client):
    assert client.post("/ws/image", json={"prompt": "x"}).status_code == 401
    assert client.post("/ws/video", json={"slides": [{"text": "x"}]}).status_code == 401


def test_media_api_flow(client, monkeypatch):
    import config
    h = {"X-Sovereign-Key": KEY}
    monkeypatch.setattr(config, "MEDIA_ENABLED", False)
    r = client.post("/ws/image", headers=h, json={"prompt": "قطة"})
    assert r.status_code == 400 and "غير مفعّل" in r.text
    st = client.get("/ws/status", headers=h).json()
    assert st["video"]["available"] == HAS_FFMPEG and st["imagegen"]["available"] is False
    if HAS_FFMPEG:
        v = client.post("/ws/video", headers=h, json={"slides": [{"text": "شريحة"}], "seconds": 1}).json()
        raw = client.get(f"/ws/files/{v['id']}/raw", headers=h)
        assert raw.status_code == 200 and raw.content[4:8] == b"ftyp"


# ---------------- 6. أدوات الوكيل ----------------
def test_media_tools_registered():
    import app  # noqa: F401
    from tool_registry import get_registry
    names = {t["name"] for t in get_registry().list_tools()}
    assert {"files.image", "files.video"} <= names


# ---------------- 7. خادم توليد الصور ----------------
def _load_server():
    spec = importlib.util.spec_from_file_location("imagegen_server", REPO_ROOT / "infra" / "imagegen" / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_imagegen_server_validates_and_reports_state():
    from http.server import ThreadingHTTPServer
    mod = _load_server()
    mod.STATE["status"] = "loading"
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mod.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"

    def post(body):
        req = urllib.request.Request(base + "/v1/images/generations", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            return urllib.request.urlopen(req, timeout=10).status
        except urllib.error.HTTPError as e:
            return e.code
    try:
        assert json.load(urllib.request.urlopen(base + "/health", timeout=10))["status"] == "loading"
        assert post({"prompt": ""}) == 400
        assert post({"prompt": "x", "size": "999x999"}) == 400
        assert post({"prompt": "x", "size": "256x256"}) == 503  # غير جاهز — لا صورة مختلقة
    finally:
        srv.shutdown()


# ---------------- 8. سير البنية ----------------
def test_infra_workflow_guards():
    import yaml
    text = WF.read_text(encoding="utf-8")
    d = yaml.safe_load(text)
    on = d.get("on", d.get(True))
    assert list(on) == ["workflow_dispatch"]
    assert "confirm_app" in on["workflow_dispatch"]["inputs"]
    steps = d["jobs"][next(iter(d["jobs"]))]["steps"]
    names = [s.get("name") for s in steps]
    secrets_at = names.index("Set app secrets (only for proven services)")
    for proof in ("Prove SearXNG answers from inside the app machine",
                  "Prove imagegen generates a real image from inside the app machine",
                  "Pull vision model into the brain (Ollama)"):
        assert names.index(proof) < secrets_at
    run = steps[secrets_at]["run"]
    for flag in ("SEARCH_READY", "VISION_READY", "IMAGEGEN_READY"):
        assert flag in run
    assert "flyctl secrets set" in text and text.count("flyctl secrets set") == 1
    assert "${ARGS[@]%%=*}" in run  # يطبع الأسماء فقط
    assert "echo \"$SOVEREIGN_KEY" not in text and "FLY_API_TOKEN }}" in text
    assert "CI" not in d["name"]


def test_proof_scripts_compile():
    for p in (REPO_ROOT / "infra" / "proof").glob("*.py"):
        compile(p.read_text(encoding="utf-8"), str(p), "exec")
    assert "print(KEY" not in (REPO_ROOT / "infra" / "proof" / "workspace_proof.py").read_text(encoding="utf-8")
