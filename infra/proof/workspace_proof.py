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
