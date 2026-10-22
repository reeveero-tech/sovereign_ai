"""R-401: فحص صياغة Python + JS"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _py_files():
    for dirpath, _, files in os.walk(os.path.join(ROOT, "backend")):
        if "__pycache__" in dirpath:
            continue
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def _js_files():
    for dirpath, _, files in os.walk(os.path.join(ROOT, "frontend")):
        if "node_modules" in dirpath:
            continue
        for f in files:
            if f.endswith(".js"):
                yield os.path.join(dirpath, f)


def test_python_syntax():
    """كل ملفات backend سليمة نحوياً"""
    files = list(_py_files())
    assert len(files) > 50, f"متوقع >50 ملف Python، وجد {len(files)}"
    for f in files:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", f],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"خطأ صياغة في {f}: {result.stderr}"


def test_js_syntax():
    """كل ملفات frontend سليمة نحوياً"""
    files = list(_js_files())
    # R-724/R-725 (بند ١.٢): أزيلت 22 وحدة زخرفية (111→~100 ملف) — أرضية
    # العدد خُفّت من >100 إلى >=70. الحماية الحقيقية من الانكماش الصامت
    # انتقلت إلى حارس الجرد tests/test_frontend_inventory.py (كل وحدة
    # يجب أن تكون مجرودة، وأي وحدة محذوفة تعود = رفض).
    assert len(files) >= 70, f"متوقع >=70 ملف JS، وجد {len(files)}"
    for f in files:
        result = subprocess.run(
            ["node", "--check", f],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"خطأ صياغة في {f}: {result.stderr}"
