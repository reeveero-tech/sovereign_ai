"""الجولة <2> — قرار المالك (القسم ٢): تثبيت إصدارات الويب.

أثر البيئة المحلي (FastAPI 0.143.3 مقابل 0.115.0 المثبت) تسبب فشل
test_all_registered_routes_respond محليًا بينما CI أخضر — انحراف صامت
بين البيئات. الحل: تثبيت صريح في requirements.txt + حارس يرفض الترقية
الصامتة: الإصدار المثبّت فعليًا في بيئة التشغيل يجب أن يطابق المثبت في
requirements.txt حرفيًا — أي انحراف = فشل صريح لا نجاح زائف.
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _pinned(req_line_prefix: str) -> str:
    req = (_REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    for line in req.splitlines():
        line = line.strip()
        if line.startswith(req_line_prefix + "=="):
            return line.split("==", 1)[1]
    raise AssertionError(
        f"requirements.txt must pin {req_line_prefix}==<version> explicitly"
    )


def test_fastapi_version_pinned():
    """fastapi وstarlette: المثبّت الفعلي يطابق المثبت في requirements.txt.

    يرفض الترقية الصامتة: بيئة محلية (أو CI) بإصدار مختلف عن المثبت
    تفشل فورًا — لا نجاح زائف عبر اختلاف سلوك الإصدارات (_IncludedRouter
    في FastAPI الحديثة كمثال موثق من الجولة <2>)."""
    import fastapi
    import starlette

    pinned_fastapi = _pinned("fastapi")
    pinned_starlette = _pinned("starlette")
    assert fastapi.__version__ == pinned_fastapi, (
        f"fastapi {fastapi.__version__} is installed but requirements.txt "
        f"pins {pinned_fastapi} — silent upgrade detected (install: "
        f"pip install -r requirements.txt)"
    )
    assert starlette.__version__ == pinned_starlette, (
        f"starlette {starlette.__version__} is installed but requirements.txt "
        f"pins {pinned_starlette} — silent upgrade detected"
    )
