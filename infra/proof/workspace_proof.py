"""R-801: إثبات مساحة العمل على الإنتاج — يُشغَّل داخل آلة التطبيق (infra-services.yml).

رفع zip (فيه مسار خبيث) ← تفكيك ← تحويل CSV→XLSX ← إنشاء PDF وقراءته ← حالة المساحة.
مفتاح المالك من بيئة الآلة نفسها ولا يُطبع أبدًا.
"""
import io
import json
import urllib.request
import sys
import uuid
import zipfile

sys.path.insert(0, "/tmp")
from appenv import app_env  # noqa: E402

KEY = app_env("SOVEREIGN_KEY")  # مفتاح المالك من بيئة التطبيق — لا يُطبع
BASE = "http://127.0.0.1:8080"


def call(method, path, body=None, ctype="application/json"):
    h = {"X-Sovereign-Key": KEY}
    if body is not None:
        h["Content-Type"] = ctype
    r = urllib.request.urlopen(urllib.request.Request(BASE + path, data=body, headers=h, method=method), timeout=300)
    raw = r.read()
    return json.loads(raw) if r.headers.get("Content-Type", "").startswith("application/json") else raw


zb = io.BytesIO()
with zipfile.ZipFile(zb, "w") as z:
    z.writestr("proof/notes.txt", "إثبات R-800 على الإنتاج")
    z.writestr("proof/t.csv", "a,b\n1,2\n3,4\n")
    z.writestr("../evil.txt", "x")
bd = uuid.uuid4().hex
head = ("--" + bd + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"proof.zip\"\r\n"
        "Content-Type: application/zip\r\n\r\n").encode()
f = call("POST", "/ws/files", head + zb.getvalue() + ("\r\n--" + bd + "--\r\n").encode(),
         "multipart/form-data; boundary=" + bd)
print("UPLOAD", f["kind"], f["size"])
u = call("POST", "/ws/files/" + f["id"] + "/unpack", b"{}")
print("UNPACK extracted", u["extracted"], "skipped", len(u["skipped"]))
csv_id = [x for x in u["files"] if x["kind"] == "csv"][0]["id"]
x = call("POST", "/ws/files/" + csv_id + "/convert", json.dumps({"format": "xlsx"}).encode())
print("CONVERT", x["name"], x["kind"])
p = call("POST", "/ws/create", json.dumps({"format": "pdf", "title": "إثبات", "content": "نص عربي على الإنتاج"}).encode())
raw = call("GET", "/ws/files/" + p["id"] + "/raw")
print("PDF", p["name"], raw[:5] == b"%PDF-")
st = call("GET", "/ws/status")
print("STATUS storage", st["storage"], "durable", st["durable"], "files", st["files"],
      "video", (st.get("video") or {}).get("available"), "imagegen", (st.get("imagegen") or {}).get("available"))

# R-801: الوسائط عبر التطبيق نفسه (لا مباشرة إلى الخدمات) — كل سطر نتيجة فعلية
import time  # noqa: E402

t = time.time()
try:
    img = call("POST", "/ws/image", json.dumps({"prompt": "a red apple on a wooden table", "size": "256x256",
                                                  "title": "proof-apple"}).encode())
    rawimg = call("GET", "/ws/files/" + img["id"] + "/raw")
    print("IMAGEGEN_APP", img["kind"], img["size"], rawimg[:8] == bytes([137, 80, 78, 71, 13, 10, 26, 10]),
          round(time.time() - t, 1))
    an = call("POST", "/ws/files/" + img["id"] + "/analyze", json.dumps({"question": "What is in this image?"}).encode())
    vis = an.get("vision") or {}
    print("VISION_APP", vis.get("available"), (vis.get("description") or vis.get("reason") or "")[:200].replace("\n", " "))
    vid = call("POST", "/ws/video", json.dumps({"slides": [{"file_id": img["id"]}, {"text": "إثبات الفيديو", "title": "R-801"}],
                                                "seconds": 2, "title": "proof-video"}).encode())
    print("VIDEO_APP", vid["kind"], vid["size"], vid.get("seconds"))
except Exception as exc:  # TOLERATED: سطر إثبات يُطبع بسببه ولا يخفي ما سبق — الحكم في سير العمل
    print("MEDIA_APP_ERROR", type(exc).__name__, str(exc)[:300])
try:
    body = json.dumps({"tool": "web.search", "api_key": KEY, "inputs": {"query": "fly.io machines"}}).encode()
    r = urllib.request.urlopen(urllib.request.Request(BASE + "/tools/invoke", data=body,
                               headers={"Content-Type": "application/json"}), timeout=120)
    res = json.loads(r.read())
    out = res.get("result") or res.get("output") or {}
    items = out.get("results") if isinstance(out, dict) else None
    print("SEARCH_APP", res.get("ok"), len(items or []), ((items or [{}])[0].get("url") if items else res.get("error")))
except Exception as exc:  # TOLERATED: كما سبق
    print("SEARCH_APP_ERROR", type(exc).__name__, str(exc)[:300])
