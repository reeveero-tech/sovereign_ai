"""R-800 (أمر المالك 2026-10-28): مساحة العمل — ملفات حقيقية بكل أنواعها.

المثبت هنا (كله سلوك حقيقي، لا أجوبة مزروعة):
1. القراءة: نص/CSV/JSON/PDF/DOCX/XLSX/PPTX/صورة/أرشيف تُستخرج فعلًا؛ غير المدعوم يُعلن صراحة.
2. الأرشيفات: تفكيك zip/tar/7z مع رفض zip-slip والروابط الرمزية وقنابل الضغط.
3. الإنشاء والتصدير: كل صيغة تُنتج ملفًا يُعاد فتحه بمكتبته (ذهاب وإياب).
4. الخدمة: رفع/قراءة/بحث/تحويل/ضغط/تفكيك/أرشفة بلا حذف + محادثات ومشاريع دائمة.
5. الواجهة البرمجية /ws: مفتاح المالك إلزامي (401)، والإعدادات لا تكشف أي قيمة سرية.
6. المحادثة: المرفقات والمشروع النشط يصلان الوكيل كسياق حقيقي من مساحة العمل.
7. أدوات السجل files.* و workspace.status مسجلة للوكيل.
8. الواجهة: التطبيق الكامل على / والواجهة السابقة محفوظة على /classic.
"""

import io
import json
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from workspace import archives, readers, writers  # noqa: E402
from workspace.service import Workspace, WorkspaceError, reset_workspace  # noqa: E402
from workspace.storage import LocalStorage  # noqa: E402

KEY = "r800-owner-key-test"


def _zip(entries):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in entries:
            z.writestr(n, d)
    return b.getvalue()


@pytest.fixture
def ws(tmp_path):
    w = Workspace(LocalStorage(tmp_path / "files"), None, local_root=tmp_path / "idx")
    reset_workspace(w)
    yield w
    reset_workspace(None)


# ---------------- 1. القراءة ----------------
def test_read_text_csv_json():
    t = readers.extract("a.txt", "سطر أول\nسطر ثانٍ".encode())
    assert t["kind"] == "text" and t["supported"] and "سطر ثانٍ" in t["text"]
    c = readers.extract("d.csv", "name,score\nعلي,5\nسارة,9\n".encode())
    assert c["kind"] == "csv" and c["structure"]["rows"] == 2 and c["structure"]["header"] == ["name", "score"]
    assert c["structure"]["column_stats"][1]["mean"] == 7.0
    j = readers.extract("x.json", json.dumps({"a": [1, 2, 3]}).encode())
    assert j["kind"] == "json" and j["supported"]


def test_read_office_and_pdf_roundtrip():
    for fmt, kind in (("pdf", "pdf"), ("docx", "docx"), ("xlsx", "xlsx"), ("pptx", "pptx")):
        name, blob, _ = writers.create(fmt, "تقرير", "# قسم\nنص-مميز-800 للتجربة",
                                       [["المدينة", "السكان"], ["جدة", "4.7"]] if fmt == "xlsx" else None)
        ex = readers.extract(name, blob)
        assert ex["kind"] == kind and ex["supported"], (fmt, ex.get("error"))
        if fmt == "xlsx":
            assert "جدة" in ex["text"]
        elif fmt == "pdf" and not shutil.which("pdftotext"):
            assert "نص-مميز" in ex["text"]  # pypdf وحده يُسقط مقطع الأرقام المختلط (لذا poppler في الحاوية)
        else:
            assert "800" in ex["text"], (fmt, ex["text"][:200])


def test_read_image_metadata():
    name, blob, mime = writers.create("png", "عنوان", "سطر")
    ex = readers.extract(name, blob)
    assert mime == "image/png" and ex["kind"] == "image" and ex["structure"]["width"] > 0


def test_unsupported_declared_not_faked():
    ex = readers.extract("song.mp3", b"ID3\x00\x00fake")
    assert ex["kind"] == "audio" and ex["supported"] is False and not ex.get("text")
    ex = readers.extract("blob.bin", bytes(range(256)) * 4)
    assert ex["supported"] is False


# ---------------- 2. الأرشيفات ----------------
def test_unpack_zip_rejects_zip_slip():
    data = _zip([("ok/a.txt", "آمن"), ("../evil.txt", "x"), ("/abs.txt", "y")])
    res = archives.unpack("a.zip", data)
    paths = [p for p, _ in res["entries"]]
    assert paths == ["ok/a.txt"]
    assert len(res["skipped"]) == 2


def test_unpack_tar_skips_symlink_and_bomb_ratio():
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode="w:gz") as t:
        info = tarfile.TarInfo("link"); info.type = tarfile.SYMTYPE; info.linkname = "/etc/passwd"; t.addfile(info)
        d = "محتوى".encode(); info = tarfile.TarInfo("f.txt"); info.size = len(d); t.addfile(info, io.BytesIO(d))
    res = archives.unpack("a.tar.gz", b.getvalue())
    assert [p for p, _ in res["entries"]] == ["f.txt"] and res["skipped"]
    bomb = _zip([("z.txt", "0" * (30 * 1024 * 1024))])
    with pytest.raises(archives.ArchiveError):
        archives.unpack("bomb.zip", bomb)


def test_make_zip_and_7z_roundtrip():
    blob = archives.make_zip([("a/b.txt", "نص".encode()), ("c.csv", b"x,y\n")])
    assert sorted(m["name"] for m in archives.list_members("x.zip", blob)["members"]) == ["a/b.txt", "c.csv"]
    import py7zr
    b = io.BytesIO()
    with py7zr.SevenZipFile(b, "w") as z:
        z.writestr("سبعة".encode(), "s.txt")
    res = archives.unpack("s.7z", b.getvalue())
    assert res["entries"][0][1] == "سبعة".encode()


# ---------------- 3. الإنشاء ----------------
@pytest.mark.parametrize("fmt", sorted(writers.FORMATS))
def test_every_create_format_produces_real_file(fmt):
    name, blob, mime = writers.create(fmt, "ملف", "# عنوان\nمحتوى", [["a", "b"], ["1", "2"]])
    assert name.endswith("." + fmt) and len(blob) > 10 and mime
    if fmt in ("docx", "xlsx", "pptx"):
        assert zipfile.is_zipfile(io.BytesIO(blob))
    if fmt == "pdf":
        assert blob[:5] == b"%PDF-"
    if fmt == "png":
        assert blob[:8] == b"\x89PNG\r\n\x1a\n"


def test_unknown_format_rejected():
    with pytest.raises(ValueError):
        writers.create("exe", "x", "y")


# ---------------- 4. الخدمة ----------------
def test_service_upload_read_search_convert_zip_unpack(ws):
    z = ws.add_file("pack.zip", _zip([("docs/a.txt", "كلمة-سرية-البحث"), ("t.csv", "x,y\n1,2\n")]))
    assert z["kind"] == "archive" and z["sha256"]
    out = ws.unpack(z["id"])
    assert out["extracted"] == 2 and all(f["parent"] == z["id"] for f in out["files"])
    hits = ws.search("كلمة-سرية-البحث")
    assert hits and hits[0]["file"]["name"] == "a.txt"
    csv_id = [f for f in out["files"] if f["kind"] == "csv"][0]["id"]
    x = ws.convert(csv_id, "xlsx")
    assert x["kind"] == "xlsx" and x["parent"] == csv_id and ws.raw(x["id"])[:2] == b"PK"
    bundle = ws.zip([f["id"] for f in out["files"]], "out")
    assert bundle["name"] == "out.zip" and archives.list_members("out.zip", ws.raw(bundle["id"]))["files"] == 2
    r = ws.read(out["files"][0]["id"], 0, 5)
    assert r["offset"] == 0 and len(r["text"]) <= 5


def test_archive_hides_never_deletes(ws):
    f = ws.add_file("a.txt", b"x")
    ws.set_archived(f["id"], True)
    assert f["id"] not in [r["id"] for r in ws.list_files()]
    assert ws.raw(f["id"]) == b"x"  # البايتات باقية — لا حذف
    assert f["id"] in [r["id"] for r in ws.list_files(include_archived=True)]


def test_upload_size_limit(ws, monkeypatch):
    import workspace.service as svc
    monkeypatch.setattr(svc, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(WorkspaceError):
        ws.add_file("big.txt", b"0" * 11)


def test_conversations_projects_persist(ws, tmp_path):
    p = ws.save_project(None, "مشروع", "وصف", "تعليمات", ["https://github.com/a/b"])
    c = ws.save_conversation(None, "", [{"role": "user", "content": "مرحبا"},
                                        {"role": "system", "content": "يُرفض"}], p["id"])
    assert c["title"] == "مرحبا" and len(c["messages"]) == 1
    w2 = Workspace(LocalStorage(tmp_path / "files"), None, local_root=tmp_path / "idx")
    assert w2.get_conversation(c["id"])["project_id"] == p["id"]
    assert w2.get_project(p["id"])["instructions"] == "تعليمات"


def test_analyze_deterministic_without_brain_is_honest(ws):
    f = ws.add_file("d.csv", "a,b\n1,2\n3,4\n".encode())
    res = ws.analyze(f["id"], "ما المتوسط؟")
    assert res["findings"]
    assert res["summary"]["available"] is False and res["summary"]["reason"]


def test_analyze_uses_real_brain_when_given(tmp_path):
    seen = []

    def brain(system, user):
        seen.append(user)
        return "خلاصة-من-العقل"
    w = Workspace(LocalStorage(tmp_path / "f"), None, local_root=tmp_path / "i", brain=brain)
    f = w.add_file("n.txt", "نص للتحليل-800".encode())
    res = w.analyze(f["id"], "لخص")
    assert res["summary"]["available"] and "خلاصة-من-العقل" in res["summary"]["text"]
    assert "800" in json.dumps(seen, ensure_ascii=False)


# ---------------- 5. الواجهة البرمجية ----------------
@pytest.fixture
def client(ws, monkeypatch):
    import app as app_mod
    from fastapi.testclient import TestClient
    monkeypatch.setattr(app_mod, "SOVEREIGN_API_KEY", KEY)
    app_mod.chat_rate_limiter._requests.clear()
    with TestClient(app_mod.app) as c:
        reset_workspace(ws)  # الإقلاع قد يهيئ مساحة العمل الافتراضية — نثبت مساحة الاختبار
        yield c


def test_ws_api_requires_owner_key(client):
    for m, u in (("get", "/ws/status"), ("get", "/ws/files"), ("get", "/ws/settings"), ("get", "/ws/projects")):
        assert getattr(client, m)(u).status_code == 401
        assert getattr(client, m)(u, headers={"X-Sovereign-Key": "wrong"}).status_code == 401
    assert client.get("/ws/status", headers={"X-Sovereign-Key": KEY}).status_code == 200


def test_ws_api_full_flow(client):
    h = {"X-Sovereign-Key": KEY}
    r = client.post("/ws/files", headers=h, files={"file": ("p.zip", _zip([("a.txt", "أ"), ("../x", "y")]))})
    assert r.status_code == 200, r.text
    fid = r.json()["id"]
    u = client.post(f"/ws/files/{fid}/unpack", headers=h).json()
    assert u["extracted"] == 1 and u["skipped"]
    c = client.post("/ws/create", headers=h, json={"format": "pdf", "title": "ت", "content": "نص"}).json()
    raw = client.get(f"/ws/files/{c['id']}/raw", headers=h)
    assert raw.status_code == 200 and raw.content[:5] == b"%PDF-"
    rd = client.get(f"/ws/files/{u['files'][0]['id']}", headers=h).json()
    assert rd["text"] == "أ"
    assert client.patch(f"/ws/files/{fid}", headers=h, json={"archived": True}).json()["archived"] is True


def test_settings_never_exposes_secret_values(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "super-secret-value-800")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret800")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen-test")
    body = client.get("/ws/settings", headers={"X-Sovereign-Key": KEY}).text
    assert "super-secret-value-800" not in body and "ghp_secret800" not in body and KEY not in body
    d = json.loads(body)
    env = {e["name"]: e for e in d["env"]}
    assert env["SUPABASE_SECRET_KEY"]["set"] is True and env["SUPABASE_SECRET_KEY"]["value"] is None
    assert env["OLLAMA_MODEL"]["value"] == "qwen-test"
    ids = {i["id"] for i in d["integrations"]}
    assert {"github", "web_fetch", "web_search", "supabase", "brain", "vision", "media", "ffmpeg"} <= ids
    assert all(isinstance(i["ready"], bool) for i in d["integrations"])


# ---------------- 6. المحادثة ----------------
def test_chat_passes_attachments_and_project_to_agent(client, ws, monkeypatch):
    import app as app_mod
    import chat_agent
    seen = {}

    def fake_respond(text, history=None, owner=False):
        seen["text"], seen["owner"] = text, owner
        return {"reply": "تم", "tools_used": []}
    monkeypatch.setattr(app_mod, "_chat_agent_mode", lambda: True)
    monkeypatch.setattr(chat_agent, "respond", fake_respond)
    f = ws.add_file("ملاحظات.txt", "محتوى-المرفق-800".encode())
    p = ws.save_project(None, "مشروع-800", "", "اكتب بإيجاز-800")
    r = client.post("/chat", json={"text": "اقرأ", "api_key": KEY, "file_ids": [f["id"]], "project_id": p["id"]})
    assert r.status_code == 200, r.text
    assert seen["owner"] and f["id"] in seen["text"] and "محتوى-المرفق-800" in seen["text"]
    assert "اكتب بإيجاز-800" in seen["text"]
    # الضيف لا يرى مرفقات ولا مشروعًا
    client.post("/chat", json={"text": "اقرأ", "file_ids": [f["id"]], "project_id": p["id"]})
    assert seen["owner"] is False and "محتوى-المرفق-800" not in seen["text"]


# ---------------- 7. الأدوات ----------------
def test_workspace_tools_registered_and_work(ws):
    from tool_registry import get_registry
    import app  # noqa: F401 — يسجل الأدوات
    names = {t["name"] for t in get_registry().list_tools()}
    assert {"workspace.status", "files.list", "files.search", "files.read", "files.analyze",
            "files.unpack", "files.zip", "files.create", "files.convert", "projects.list"} <= names


# ---------------- 8. الواجهة ----------------
def test_root_serves_full_app_and_classic_preserved(client):
    html = client.get("/").text
    for view in ("view-chat", "view-tasks", "view-projects", "view-files", "view-agents",
                 "view-connect", "view-settings"):
        assert f'id="{view}"' in html
    assert "/ws/files" in html and "X-Sovereign-Key" in html and "file_ids" in html
    classic = client.get("/classic")
    assert classic.status_code == 200 and 'id="ownerKey"' in classic.text
