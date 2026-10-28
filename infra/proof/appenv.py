"""R-801: قراءة متغير من بيئة عملية التطبيق داخل آلة Fly (لجلسات ssh) — لا يطبع أي قيمة."""
import glob
import os


def app_env(name: str, default: str = "") -> str:
    if os.environ.get(name):
        return os.environ[name]
    candidates = []
    for cmd in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            if b"uvicorn" in open(cmd, "rb").read():
                candidates.append(cmd.replace("cmdline", "environ"))
        except OSError:  # TOLERATED: عملية انتهت أثناء المسح — تُتجاوز إلى التالية
            continue
    candidates.append("/proc/1/environ")
    for path in candidates:
        try:
            for item in open(path, "rb").read().split(b"\0"):
                k, _, v = item.decode("utf-8", "replace").partition("=")
                if k == name and v:
                    return v
        except OSError:  # TOLERATED: بيئة عملية غير مقروءة — المرشح التالي، والنهاية default معلن
            continue
    return default
