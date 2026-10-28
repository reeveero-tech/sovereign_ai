"""R-801: سحب نموذج إلى العقل (Ollama على آلة خاصة) من داخل آلة التطبيق، ثم سرد النماذج."""
import json
import sys
import urllib.request

sys.path.insert(0, "/tmp")
from appenv import app_env  # noqa: E402

model = sys.argv[1]
base = app_env("OLLAMA_BASE_URL").rstrip("/")
req = urllib.request.Request(base + "/api/pull", data=json.dumps({"name": model, "stream": False}).encode(),
                             headers={"Content-Type": "application/json"})
print("PULL", urllib.request.urlopen(req, timeout=2400).read().decode()[:300])
tags = json.load(urllib.request.urlopen(base + "/api/tags", timeout=30))
print("TAGS", " ".join(m["name"] for m in tags.get("models", [])))
