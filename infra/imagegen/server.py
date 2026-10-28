"""R-801: خادم توليد صور ذاتي الاستضافة (stable-diffusion.cpp على المعالج) — بلا مزود خارجي (D-045).

عقد OpenAI Images الذي يتكلمه backend/media_client.py:
  POST /v1/images/generations {"prompt", "size": "512x512", "n": 1, "response_format": "b64_json"}
  → {"created", "data": [{"b64_json"}], "model", "seconds"}
  GET  /health → {"status": "ok"|"loading"|"error", "model", "error"}

النموذج: SD-Turbo (GGUF q8) — خطوة واحدة، cfg=1. يُنزَّل مرة واحدة إلى /models (قرص الآلة)
ويُتحقق من حجمه. الخادم داخل الشبكة الخاصة فقط (لا منفذ عام)؛ IMAGEGEN_TOKEN اختياري.
"""
import base64
import io
import json
import os
import socket
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_URL = os.environ.get("IMAGEGEN_MODEL_URL",
                           "https://huggingface.co/Green-Sky/SD-Turbo-GGUF/resolve/main/sd_turbo-f16-q8_0.gguf")
MODEL_PATH = os.environ.get("IMAGEGEN_MODEL_PATH", "/models/sd_turbo-f16-q8_0.gguf")
MODEL_MIN_BYTES = int(os.environ.get("IMAGEGEN_MODEL_MIN_BYTES", str(1_500_000_000)))
THREADS = int(os.environ.get("IMAGEGEN_THREADS", str(os.cpu_count() or 2)))
TOKEN = os.environ.get("IMAGEGEN_TOKEN") or None
SIZES = {"256x256", "512x512", "768x768"}
STATE = {"status": "loading", "error": None, "model": os.path.basename(MODEL_PATH), "generated": 0}
_SD = None
_LOCK = threading.Lock()


def _download() -> None:
    if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) >= MODEL_MIN_BYTES:
        return
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    tmp = MODEL_PATH + ".part"
    with urllib.request.urlopen(MODEL_URL, timeout=600) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    if os.path.getsize(tmp) < MODEL_MIN_BYTES:
        raise RuntimeError(f"تنزيل ناقص: {os.path.getsize(tmp)} بايت")
    os.replace(tmp, MODEL_PATH)


def _load() -> None:
    global _SD
    try:
        _download()
        from stable_diffusion_cpp import StableDiffusion
        _SD = StableDiffusion(model_path=MODEL_PATH, n_threads=THREADS, verbose=False)
        STATE["status"] = "ok"
    except Exception as exc:  # الحالة تُعلن الخطأ بدل الادعاء بالجاهزية
        STATE["status"], STATE["error"] = "error", f"{type(exc).__name__}: {str(exc)[:300]}"


def generate(prompt: str, size: str, seed: int) -> bytes:
    w, h = (int(x) for x in size.split("x"))
    with _LOCK:  # المعالج واحد — طلب واحد في كل مرة
        imgs = _SD.generate_image(prompt=prompt, width=w, height=h, sample_steps=1, cfg_scale=1.0, seed=seed)
    buf = io.BytesIO()
    imgs[0].save(buf, "PNG")
    STATE["generated"] += 1
    return buf.getvalue()


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("imagegen:", fmt % args, flush=True)

    def do_GET(self):
        if self.path.rstrip("/") in ("/health", "/v1/health"):
            return self._send(200, {**STATE, "threads": THREADS})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") not in ("/v1/images/generations", "/images/generations"):
            return self._send(404, {"error": "not found"})
        if TOKEN and self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self._send(401, {"error": "unauthorized"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(min(n, 100_000)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "JSON غير صالح"})
        prompt = str(req.get("prompt") or "").strip()[:1000]
        size = str(req.get("size") or "512x512")
        if not prompt:
            return self._send(400, {"error": "prompt فارغ"})
        if size not in SIZES:
            return self._send(400, {"error": f"المقاسات المتاحة: {sorted(SIZES)}"})
        if STATE["status"] != "ok":
            return self._send(503, {"error": f"النموذج غير جاهز: {STATE['status']} {STATE['error'] or ''}".strip()})
        t = time.time()
        png = generate(prompt, size, int(req.get("seed") or int(t) % 2_000_000_000))
        return self._send(200, {"created": int(t), "model": STATE["model"], "seconds": round(time.time() - t, 1),
                                "data": [{"b64_json": base64.b64encode(png).decode()}]})


def main():
    threading.Thread(target=_load, daemon=True).start()
    port = int(os.environ.get("PORT", "8080"))
    class Srv6(ThreadingHTTPServer):
        address_family = socket.AF_INET6  # شبكة Fly الخاصة IPv6 (.internal)
    try:
        srv = Srv6(("::", port), H)
    except OSError:  # بيئة بلا IPv6 (اختبار محلي)
        srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    print(f"imagegen listening on {srv.server_address}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
