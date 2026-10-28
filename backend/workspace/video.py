"""R-801: إنشاء فيديو حقيقي بـ ffmpeg (ذاتي، داخل الحاوية) — شرائح صور و/أو نصوص + صوت اختياري.

حد صادق: هذا تركيب فيديو من صور ونصوص وصوت (عرض شرائح/فيديو توضيحي)، **ليس** توليد فيديو
بالذكاء الاصطناعي من وصف نصي — ذلك يحتاج نموذج فيديو وعتادًا غير موجود، ويُعلن كذلك.
"""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .writers import FONTS

MAX_SLIDES = 60
MAX_SECONDS = 20.0
_AR = re.compile(r"[\u0600-\u06FF]")
_NOTO_OK = re.compile(r"[\u0600-\u06FF\s0-9.,:;!?()\-]*")


class VideoError(Exception):
    pass


def available() -> Dict[str, Any]:
    ff = shutil.which("ffmpeg")
    return {"available": bool(ff), "ffmpeg": ff,
            "reason": None if ff else "ffmpeg غير مثبت في هذه البيئة",
            "kind": "slideshow", "ai_text_to_video": False}


def _font(size: int, text: str):
    from PIL import ImageFont, features
    layout = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
    # Noto العربي لا يغطي اللاتيني ولا علامات مثل «—»؛ DejaVu يغطي العربية واللاتيني معًا
    name = "NotoSansArabic-Regular.ttf" if _NOTO_OK.fullmatch(text or "") else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONTS / name), size, layout_engine=layout), layout


def _wrap(dr, text: str, font, kw, width: int) -> List[str]:
    out: List[str] = []
    for para in text.splitlines() or [""]:
        line = ""
        for word in para.split():
            cand = (line + " " + word).strip()
            if line and dr.textlength(cand, font=font, **kw) > width:
                out.append(line)
                line = word
            else:
                line = cand
        out.append(line)
    return out


def text_slide(text: str, size: Tuple[int, int] = (1280, 720), title: str = "") -> bytes:
    """شريحة نصية مُشكَّلة وملتفة الأسطر — صورة PNG حقيقية."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    im = Image.new("RGB", (W, H), (15, 23, 42))
    dr = ImageDraw.Draw(im)
    y = 80
    for chunk, sz, color in ([(title, 58, (248, 250, 252))] if title else []) + [(text, 40, (226, 232, 240))]:
        if not chunk:
            continue
        font, layout = _font(sz, chunk)
        kw = {"direction": "rtl"} if layout == ImageFont.Layout.RAQM and _AR.search(chunk) else {}
        for line in _wrap(dr, chunk, font, kw, W - 160):
            if y > H - 70:
                break
            w = dr.textlength(line, font=font, **kw)
            x = (W - w) / 2
            dr.text((x, y), line, font=font, fill=color, **kw)
            y += int(sz * 1.55)
        y += 20
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _fit(img_bytes: bytes, size: Tuple[int, int]) -> bytes:
    from PIL import Image, ImageOps
    W, H = size
    im = Image.open(io.BytesIO(img_bytes))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((W, H))
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    buf = io.BytesIO()
    canvas.save(buf, "PNG")
    return buf.getvalue()


def make_video(slides: List[Dict[str, Any]], seconds: float = 3.0, audio: Optional[bytes] = None,
               audio_name: str = "audio", size: Tuple[int, int] = (1280, 720), fps: int = 25) -> bytes:
    """slides: [{"image": bytes} | {"text": str, "title": str}] → بايتات MP4 (H.264/yuv420p)."""
    if not shutil.which("ffmpeg"):
        raise VideoError("ffmpeg غير مثبت — لا يمكن إنشاء فيديو")
    if not slides:
        raise VideoError("لا شرائح — أعط صورًا أو نصوصًا")
    if len(slides) > MAX_SLIDES:
        raise VideoError(f"الحد {MAX_SLIDES} شريحة")
    seconds = max(0.5, min(float(seconds or 3.0), MAX_SECONDS))
    with tempfile.TemporaryDirectory(prefix="sov-video-") as td:
        tdp = Path(td)
        lines = []
        for i, s in enumerate(slides):
            if s.get("image") is not None:
                try:
                    png = _fit(s["image"], size)
                except Exception as exc:  # TOLERATED: صورة تالفة تُعلن بسببها ولا تُسقط الفيديو بصمت
                    raise VideoError(f"الشريحة {i + 1}: صورة غير صالحة ({type(exc).__name__})") from exc
            else:
                png = text_slide(str(s.get("text") or ""), size, str(s.get("title") or ""))
            p = tdp / f"s{i:03d}.png"
            p.write_bytes(png)
            lines += [f"file '{p.name}'", f"duration {seconds}"]
        (tdp / "list.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
               "-i", "list.txt"]
        if audio:
            ext = Path(audio_name).suffix or ".bin"
            (tdp / f"audio{ext}").write_bytes(audio)
            cmd += ["-i", f"audio{ext}"]
        enc = "libx264" if b"libx264" in subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, timeout=30).stdout else "mpeg4"
        total = seconds * len(slides)
        cmd += ["-vf", f"fps={fps},format=yuv420p", "-c:v", enc, "-t", f"{total:.2f}"]
        if enc == "libx264":
            cmd += ["-preset", "veryfast", "-crf", "23"]
        if audio:
            cmd += ["-c:a", "aac", "-b:a", "128k", "-shortest"]
        cmd += ["-movflags", "+faststart", "out.mp4"]
        r = subprocess.run(cmd, cwd=td, capture_output=True, timeout=600)
        out = tdp / "out.mp4"
        if r.returncode != 0 or not out.exists():
            raise VideoError("فشل ffmpeg: " + r.stderr.decode("utf-8", "replace")[-400:])
        return out.read_bytes()
