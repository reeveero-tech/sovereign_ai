"""R-824: استوديو الوسائط — تصميم الصور والفيديوهات من المحادثة مباشرة (بعقل أو بدونه).

بأمر المالك (2026-10-31): «لا يستطيع تصميم صور وفيديوهات».

ما كان: أداتا files.image / files.video موجودتان لكن شبه ميتتين — الصورة تتطلب خادم توليد
ذاتي الاستضافة غير موجود، والمحادثة لا تصل إليهما إلا عبر وكيل العقل (المتعذر حاليًا).

ما صار — سلسلة مزودات بإعلان صادق لمن ولّد فعلًا:
١) self_hosted: خادم المالك (media_client — LocalAI/SD) إن ضُبط — لا يغادر الوصف الشبكة الخاصة.
٢) pollinations: توليد بالذكاء الاصطناعي (Flux) مجاني بلا مفتاح (حد: صورة كل 45ث لكل IP).
٣) horde: AI Horde (شبكة تطوعية مفتوحة، Stable Diffusion) — أبطأ (طابور) لكنه مستقل.
٤) local_design: مصمم محلي حتمي (Pillow) — بطاقة/ملصق/شعار بخط عربي مشكّل — يعمل دائمًا
   بلا أي طرف ثالث، ويُعلن أنه تصميم قالبي لا توليد ذكاء اصطناعي.
المزودات الخارجية (٢،٣) لا تُستعمل إلا بإذن صريح: MEDIA_EXTERNAL_PROVIDERS (مثل pollinations,horde)
— فالوصف يُرسل لطرف ثالث، وهذا معلن في الرد.

الفيديو: MP4 حقيقي (H.264) بـ ffmpeg: بطاقة عنوان ⇒ الصورة المولدة بحركة كاميرا (Ken Burns تقريب
وانزياح) ⇒ بطاقة ختام، بانتقالات تلاشي. حد صادق: ليس توليد فيديو بنموذج فيديو من النص.

الناتج يُحفظ في مساحة العمل (Supabase Storage — دائم) ويُعرض في المحادثة برابط موقّع.
"""
from __future__ import annotations

import hashlib
import io
import logging
import math
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

logger = logging.getLogger("sovereign.media_studio")

_AR = re.compile(r"[\u0600-\u06FF]")
_VERBS = (r"(?:صمم|صمّم|ارسم|إرسم|أرسم|انشئ|أنشئ|انشيء|إنشاء|انشاء|اصنع|إصنع|ولد|ولّد|توليد|اعمل|سوي|سوّي|"
          r"جهز|جهّز|حضر|ابغى|أبغى|ابي|أبي|اريد|أريد|ابغا|بدي|عايز|اعطني|أعطني|create|make|generate|draw|"
          r"design|render|produce|paint|i want|give me)")
_IMG_NOUNS = (r"(?:صور[ةه]?|صوره|رسم[ةه]?|رسمه|لوح[ةه]|تصميم|شعار|لوجو|لوغو|بوستر|ملصق|إعلان|اعلان|"
              r"بطاق[ةه]|غلاف|خلفي[ةه]|أيقون[ةه]|ايقون[ةه]|انفوجرافيك|إنفوجرافيك|image|picture|photo|"
              r"illustration|logo|poster|banner|wallpaper|icon|drawing|artwork|flyer|cover)")
_VID_NOUNS = r"(?:فيديو|فديو|مقطع|انيميشن|أنيميشن|رسوم متحركة|موشن|video|clip|animation|reel)"
_DETECT_IMG = re.compile(_VERBS + r"\s+(?:لي\s+|لنا\s+|me\s+|us\s+)?(?:an?\s+|ال)?" + _IMG_NOUNS, re.I)
_DETECT_VID = re.compile(_VERBS + r"\s+(?:لي\s+|لنا\s+|me\s+|us\s+)?(?:an?\s+|ال)?" + _VID_NOUNS, re.I)
_BARE = re.compile(r"^(?:" + _IMG_NOUNS + "|" + _VID_NOUNS + r")\s+(?:لـ|ل|عن|of|for)\s*(?=\S)", re.I)
# فعل الرسم وحده يعني صورة: «ارسم قطة في حديقة» / «draw a cat»
_DRAW = re.compile(r"^(?:ارسم|أرسم|إرسم|draw|paint|sketch|illustrate)\s+(?:لي\s+|لنا\s+|me\s+|us\s+)?(?=\S)", re.I)
_EDIT = re.compile(r"^(?:و\s*)?(?:اجعل|إجعل|خلي|خلّي|غير|غيّر|بدل|بدّل|أضف|اضف|زد|كبر|صغر|حول|حوّل|"
                   r"نفس(?:ها)?|make it|change|add|turn it|same)", re.I)
_STRIP_LEAD = re.compile(r"^.*?" + r"(?:" + _IMG_NOUNS + "|" + _VID_NOUNS + r")\s*", re.I)
_NOT_MEDIA = re.compile(r"^(?:ال)?(?:موقع|تطبيق|برنامج|برمج|قاعد[ةه]|خط[ةه]|نظام|كود|جدول|مخطط قاعدة|"
                        r"website|web ?site|app|application|database|schema|plan|system|api|code)\b", re.I)
_LOGO = re.compile(r"شعار|لوجو|لوغو|logo|icon|أيقون|ايقون", re.I)
_POSTER = re.compile(r"بوستر|ملصق|إعلان|اعلان|بطاق|غلاف|انفوجرافيك|إنفوجرافيك|poster|banner|flyer|cover", re.I)


def _env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or default).strip()


def external_providers() -> List[str]:
    return [p.strip().lower() for p in _env("MEDIA_EXTERNAL_PROVIDERS").split(",") if p.strip()]


def capabilities() -> Dict[str, Any]:
    import media_client
    ff = ffmpeg_exe()
    return {"image": True, "video": bool(ff), "ffmpeg": bool(ff),
            "providers": (["self_hosted"] if media_client_configured() else []) + external_providers()
            + ["local_design"], "ai_text_to_video": False}


def media_client_configured() -> bool:
    try:
        import config
        return bool(getattr(config, "MEDIA_ENABLED", False))
    except Exception:  # TOLERATED: بلا إعداد ⇒ غير مضبوط
        return False


def ffmpeg_exe() -> Optional[str]:
    """ffmpeg النظام أو الثنائي المضمّن (imageio-ffmpeg) — كي يعمل الفيديو على أي حاوية."""
    import shutil
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # TOLERATED: لا ffmpeg ⇒ الفيديو يُعلن غير متاح
        return None


# ---------------------------------------------------------------- فهم الطلب
def detect(text: str, history=None) -> Optional[Dict[str, Any]]:
    """طلب تصميم صورة/فيديو؟ ⇒ {kind, subject, style, edit_of} أو None."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if not t or len(t) > 600:
        return None
    is_vid = bool(_DETECT_VID.search(t))
    is_img = bool(_DETECT_IMG.search(t)) or bool(_BARE.match(t)) or (not is_vid and bool(_DRAW.match(t)))
    prev_prompt = None
    if not (is_vid or is_img):
        # متابعة تعديل على آخر وسائط: «اجعلها ليلية» / «أضف قمرًا»
        import context_resolver
        prev_prompt = context_resolver.last_media_prompt(history)
        if not (prev_prompt and _EDIT.search(t) and len(t.split()) <= 14):
            return None
        is_vid = bool(re.search(_VID_NOUNS, t, re.I))
    m = _DETECT_VID.search(t) if is_vid else (_DETECT_IMG.search(t) or _BARE.match(t) or _DRAW.match(t))
    subject = t[m.end():] if m else t
    subject = re.sub(r"^\s*(?:an?\s+|the\s+)?(?:لـ|ل(?=\S)|عن|يوضح|توضح|تبين|يبين|فيها|فيه|بها|of|for|about|showing|with)?\s*",
                     "", subject, flags=re.I).strip(" :،,.؟?")
    if _NOT_MEDIA.match(subject):
        return None  # «صمم تصميم موقع/تطبيق/خطة» ليس طلب صورة
    kind = "video" if is_vid else "image"
    style = "logo" if _LOGO.search(t) else ("poster" if _POSTER.search(t) else "photo")
    return {"kind": kind, "subject": subject or t, "style": style, "edit_of": prev_prompt, "request": t}


def translate_prompt(text: str) -> Optional[str]:
    """ترجمة وصف عربي للإنجليزية: مترجمات البحث العالمي ⇒ العقل السحابي ⇒ المعجم البصري المدمج.
    None = لا ترجمة موثوقة (والمولد لا يُستدعى بوصف عربي — حارس الهلوسة)."""
    try:
        import world_search
        en, tr = world_search.translate(text, "en", "ar")
        if tr and en and not _AR.search(en):
            return en
    except Exception:  # TOLERATED: المرحلة التالية
        pass
    try:
        import cloud_brain
        if cloud_brain.enabled():
            out = cloud_brain.chat("Translate the user's image description to concise English for an image "
                                   "generator. Output only the English description.", text, max_tokens=120)
            if out and not _AR.search(out):
                return out.strip().strip('"')[:400]
    except Exception:  # TOLERATED: المرحلة التالية
        pass
    import visual_lexicon
    en, cov = visual_lexicon.translate(text)
    return en if en and cov >= 0.6 else None


def build_prompt(req: Dict[str, Any]) -> Tuple[str, str]:
    """(وصف إنجليزي للتوليد، وصف بلغة المستخدم للعرض)."""
    subject = req["subject"]
    shown = subject
    en = subject
    if _AR.search(subject):
        en = translate_prompt(subject) or subject
    if req.get("edit_of"):
        en = f"{req['edit_of']}, {en}"
        shown = f"{req['edit_of']} + {subject}"
    # R-824c: المولدات تكتب النصوص حروفًا مشوهة (ثُبت حيًا) ⇒ تُطلب الرسمة بلا أي نص، والاسم يُكتب محليًا صحيحًا
    style = {"logo": ", minimalist flat vector emblem icon, centered symbol, plain background, professional "
                     "branding, no text, no letters, no words, no watermark",
             "poster": ", professional poster artwork, bold composition, vibrant colors, high detail, "
                       "no text, no letters, no words, no watermark",
             "photo": ", highly detailed, professional photography, sharp focus, beautiful lighting"}[req["style"]]
    if req.get("edit_of"):
        style = ""
    return (en.strip() + style)[:900], shown


# ---------------------------------------------------------------- المزودات
def _valid_image(data: bytes) -> Optional[Tuple[bytes, str]]:
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im.load()
        if im.width < 64 or im.height < 64:
            return None
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "PNG", optimize=True)
        return buf.getvalue(), "image/png"
    except Exception:  # TOLERATED: ليست صورة حقيقية ⇒ تُرفض
        return None


def _gen_self_hosted(prompt: str, size: Tuple[int, int]) -> Optional[Tuple[bytes, str]]:
    if not media_client_configured():
        raise RuntimeError("غير مضبوط")
    import media_client
    got = media_client.generate_image(prompt, f"{min(size)}x{min(size)}")
    if not got:
        raise RuntimeError(str(media_client.last_outcome().get("result")))
    return got


def _gen_pollinations(prompt: str, size: Tuple[int, int]) -> Optional[Tuple[bytes, str]]:
    import httpx
    w, h = size
    scale = min(1.0, 768.0 / max(w, h))
    seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:6], 16) % 100000
    url = (f"https://image.pollinations.ai/prompt/{quote(prompt[:700])}?width={int(w * scale)}"
           f"&height={int(h * scale)}&seed={seed}&nologo=true&model=flux&safe=true")
    for attempt in range(2):
        with httpx.Client(timeout=httpx.Timeout(float(_env("MEDIA_POLLINATIONS_TIMEOUT_SECONDS", "90")),
                                                connect=10.0), follow_redirects=True) as c:
            r = c.get(url, headers={"Accept": "image/jpeg,image/png,application/json",
                                    "User-Agent": "SovereignAI/1.0 (+media_studio)"})
        ctype = r.headers.get("content-type", "")
        if r.status_code == 200 and ctype.startswith("image/"):
            v = _valid_image(r.content)
            if v:
                return v
            raise RuntimeError("صورة غير صالحة")
        if r.status_code in (402, 429, 503) and attempt == 0:
            m = re.search(r"[Rr]etry after (\d+)", r.text or "") or re.search(r"(\d+)", r.headers.get("retry-after", ""))
            wait = int(m.group(1)) + 1 if m else 46
            if wait <= int(_env("MEDIA_POLLINATIONS_MAX_WAIT_SECONDS", "50")):
                time.sleep(wait)
                continue
        raise RuntimeError(f"HTTP {r.status_code}")
    raise RuntimeError("حد المعدل")


def _gen_horde(prompt: str, size: Tuple[int, int], cancel=None) -> Optional[Tuple[bytes, str]]:
    import httpx
    key = _env("HORDE_API_KEY", "0000000000")
    hdr = {"apikey": key, "Client-Agent": "sovereign_ai:1.0:" + _env("WORLD_SEARCH_CONTACT_EMAIL", "anon")}
    w, h = (int(x / 64) * 64 for x in size)
    body = {"prompt": prompt[:900], "params": {"width": min(w, 768), "height": min(h, 768), "steps": 20, "n": 1},
            "nsfw": False, "censor_nsfw": True, "r2": True, "shared": False}
    max_wait = float(_env("MEDIA_HORDE_MAX_WAIT_SECONDS", "150"))
    with httpx.Client(timeout=30) as c:
        r = c.post("https://aihorde.net/api/v2/generate/async", headers=hdr, json=body)
        if r.status_code not in (200, 202):
            raise RuntimeError(f"HTTP {r.status_code}")
        jid = r.json().get("id")
        t0 = time.time()
        while time.time() - t0 < max_wait and not (cancel is not None and cancel.is_set()):
            time.sleep(6)
            chk = c.get(f"https://aihorde.net/api/v2/generate/check/{jid}", headers=hdr).json()
            if chk.get("faulted"):
                raise RuntimeError("فشل العامل")
            if chk.get("done"):
                st = c.get(f"https://aihorde.net/api/v2/generate/status/{jid}", headers=hdr).json()
                gens = st.get("generations") or []
                if not gens or gens[0].get("censored"):
                    raise RuntimeError("لا ناتج")
                img = c.get(gens[0]["img"], follow_redirects=True)
                v = _valid_image(img.content)
                if v:
                    return v
                raise RuntimeError("صورة غير صالحة")
        try:
            c.delete(f"https://aihorde.net/api/v2/generate/status/{jid}", headers=hdr)
        except Exception:  # TOLERATED: إلغاء مجاملة للطابور
            pass
        raise RuntimeError("أُلغي" if cancel is not None and cancel.is_set() else f"الطابور تجاوز {int(max_wait)}ث")


def _palette(seed_text: str) -> List[Tuple[int, int, int]]:
    hsh = hashlib.sha256(seed_text.encode("utf-8")).digest()
    import colorsys
    base = hsh[0] / 255.0
    out = []
    for i, (dh, s, v) in enumerate(((0, 0.65, 0.35), (0.08, 0.7, 0.75), (0.5, 0.55, 0.95), (0.92, 0.35, 0.98))):
        r, g, b = colorsys.hsv_to_rgb((base + dh) % 1.0, s, v)
        out.append((int(r * 255), int(g * 255), int(b * 255)))
    return out


def design_local(title: str, size: Tuple[int, int] = (1024, 1024), style: str = "poster",
                 subtitle: str = "") -> Tuple[bytes, str]:
    """مصمم محلي حتمي: خلفية متدرجة + أشكال + عنوان عربي مشكّل — بلا أي طرف ثالث."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    from workspace.video import _font, _wrap, shape
    W, H = size
    c0, c1, c2, c3 = _palette(title)
    grad = Image.linear_gradient("L").resize((W, H))  # تدرج رأسي c0 ⇒ c1
    im = Image.composite(Image.new("RGB", (W, H), c1), Image.new("RGB", (W, H), c0), grad)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    hsh = hashlib.sha256((title + style).encode()).digest()
    for i in range(9):
        r = int((0.08 + hsh[i] / 255 * 0.22) * min(W, H))
        cx, cy = int(hsh[i + 9] / 255 * W), int(hsh[i + 18] / 255 * H)
        dl.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c2 + (40 + hsh[i] % 50,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=max(6, min(W, H) // 60)))
    im = Image.alpha_composite(im.convert("RGBA"), layer)
    dr = ImageDraw.Draw(im)
    if style == "logo":
        R = int(min(W, H) * 0.28)
        cx, cy = W // 2, int(H * 0.42)
        dr.ellipse((cx - R, cy - R, cx + R, cy + R), fill=c3 + (255,), outline=c2 + (255,), width=max(4, R // 18))
        dr.ellipse((cx - int(R * .8), cy - int(R * .8), cx + int(R * .8), cy + int(R * .8)), outline=c0 + (255,),
                   width=max(2, R // 30))
        _generic = {"شركة", "شركه", "مؤسسة", "مؤسسه", "مجموعة", "متجر", "مطعم", "مكتب", "مركز", "company",
                    "corp", "the", "group", "store", "shop"}
        words = [w for w in title.split() if w.lower() not in _generic] or title.split() or ["S"]
        w0 = words[0][2:] if words[0].startswith("ال") and len(words[0]) > 3 else words[0]
        mono = w0[0].upper()
        font, layout = _font(int(R * 0.9), mono)
        kw = {"direction": "rtl"} if layout == ImageFont.Layout.RAQM and _AR.search(mono) else {}
        mono_v = shape(mono, layout)
        bx = dr.textbbox((0, 0), mono_v, font=font, **kw)
        dr.text((cx - (bx[0] + bx[2]) / 2, cy - (bx[1] + bx[3]) / 2), mono_v, font=font, fill=c0 + (255,), **kw)
        ty = cy + R + int(H * 0.05)
    else:
        pad = int(W * 0.07)
        box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle((pad, int(H * 0.30), W - pad, int(H * 0.70)),
                                              radius=int(W * 0.04), fill=(0, 0, 0, 95))
        im = Image.alpha_composite(im, box)
        dr = ImageDraw.Draw(im)
    tsize = int(min(W, H) * (0.075 if len(title) < 40 else 0.055))
    font, layout = _font(tsize, title)
    kw = {"direction": "rtl"} if layout == ImageFont.Layout.RAQM and _AR.search(title) else {}
    lines_t = _wrap(dr, title, font, kw, int(W * 0.74))[:5]
    if style != "logo":
        ty = int(H * 0.5 - len(lines_t) * tsize * 1.5 / 2)
    for line in lines_t:
        vis = shape(line, layout)
        tw = dr.textlength(vis, font=font, **kw)
        dr.text(((W - tw) / 2, ty), vis, font=font, fill=(255, 255, 255, 255), **kw)
        ty += int(tsize * 1.5)
    if subtitle:
        sf, sl = _font(int(tsize * 0.45), subtitle)
        skw = {"direction": "rtl"} if sl == ImageFont.Layout.RAQM and _AR.search(subtitle) else {}
        sub_v = shape(subtitle, sl)
        sw = dr.textlength(sub_v, font=sf, **skw)
        dr.text(((W - sw) / 2, H - int(H * 0.09)), sub_v, font=sf, fill=(255, 255, 255, 200), **skw)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue(), "image/png"


_PROVIDER_LABEL = {"self_hosted": "خادم التوليد الذاتي للمالك", "pollinations": "Pollinations (Flux — ذكاء اصطناعي)",
                   "horde": "AI Horde (Stable Diffusion — شبكة مفتوحة)",
                   "local_design": "المصمم المحلي (تصميم قالبي بلا ذكاء اصطناعي)"}


def brand_overlay(art: bytes, title: str, style: str, size: Tuple[int, int]) -> Tuple[bytes, str]:
    """R-824c: رسمة الذكاء الاصطناعي + طباعة محلية صحيحة للاسم (عربي مشكّل) — شعار/بوستر قابل للاستخدام."""
    from PIL import Image, ImageDraw, ImageOps
    from workspace.video import _font, _wrap, shape
    W, H = size
    src = Image.open(io.BytesIO(art)).convert("RGB")
    title = (title or "").strip()[:120]
    if style == "logo":
        c0, c1, c2, c3 = _palette(title or "logo")
        im = Image.new("RGBA", (W, H), (250, 250, 248, 255))
        side = int(min(W, H) * 0.62)
        emb = ImageOps.fit(src, (side, side), method=Image.LANCZOS)
        mask = Image.new("L", (side, side), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, side, side), radius=side // 6, fill=255)
        x0, y0 = (W - side) // 2, int(H * 0.08)
        im.paste(emb, (x0, y0), mask)
        dr = ImageDraw.Draw(im)
        tsize = int(min(W, H) * (0.085 if len(title) < 24 else 0.06))
        color = c0 + (255,)
        top, band = y0 + side + int(H * 0.04), H - (y0 + side + int(H * 0.04))
    else:
        im = ImageOps.fit(src, (W, H), method=Image.LANCZOS).convert("RGBA")
        shade = Image.new("L", (1, 256))
        for i in range(256):
            shade.putpixel((0, i), min(235, int(max(0, i - 90) * 1.6)))
        shade = shade.resize((W, H))
        im = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), im, shade)
        dr = ImageDraw.Draw(im)
        tsize = int(min(W, H) * (0.075 if len(title) < 40 else 0.055))
        color = (255, 255, 255, 255)
        top, band = int(H * 0.66), int(H * 0.30)
    font, layout = _font(tsize, title or " ")
    kw = {"direction": "rtl"} if layout.name == "RAQM" and _AR.search(title) else {}
    lines = _wrap(dr, title, font, kw, int(W * 0.86))[:3] if title else []
    y = top + max(0, (band - len(lines) * int(tsize * 1.45)) // 2)
    for line in lines:
        vis = shape(line, layout)
        tw = dr.textlength(vis, font=font, **kw)
        dr.text(((W - tw) / 2, y), vis, font=font, fill=color, **kw)
        y += int(tsize * 1.45)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue(), "image/png"


def generate_image(prompt_en: str, shown: str, style: str, size: Tuple[int, int]) -> Dict[str, Any]:
    tried: List[Dict[str, str]] = []
    chain = []
    if media_client_configured():
        chain.append(("self_hosted", _gen_self_hosted))
    ext = external_providers()
    if style != "logo" or "pollinations" in ext:
        if "pollinations" in ext:
            chain.append(("pollinations", _gen_pollinations))
        if "horde" in ext:
            chain.append(("horde", _gen_horde))
    if _AR.search(prompt_en.split(",")[0]):
        # حارس الهلوسة (لوحظ حيًا): وصف عربي غير مترجم ⇒ المولدات تنتج صورة لا علاقة لها بالطلب
        tried.append({"provider": "translation", "result": "تعذرت ترجمة الوصف — لم يُرسل لمولّد قد يسيء فهمه",
                      "seconds": "0"})
        chain = []
    def _attempt(name, fn):
        t0 = time.time()
        try:
            got = fn(prompt_en, size)
            if got:
                return got, {"provider": name, "result": "ok", "seconds": f"{time.time() - t0:.1f}"}
            return None, {"provider": name, "result": "لا ناتج", "seconds": f"{time.time() - t0:.1f}"}
        except Exception as e:  # TOLERATED: المزود التالي — والسبب معلن في tried
            return None, {"provider": name, "result": str(e)[:120] or type(e).__name__,
                          "seconds": f"{time.time() - t0:.1f}"}

    def _finish(name, got):
        data, mime, typo = got[0], got[1], False
        # «+» = طلب تعديل (الوصف المعروض يحوي الوصف الإنجليزي السابق) ⇒ لا اسم يُطبع فوق الرسمة
        if style in ("logo", "poster") and shown and "+" not in shown:
            try:  # الاسم بطباعة محلية صحيحة فوق رسمة الذكاء الاصطناعي
                data, mime = brand_overlay(data, shown, style, size)
                typo = True
            except Exception as e:  # TOLERATED: تبقى الرسمة الأصلية والسبب في السجل
                logger.warning("R-824c: تعذر تركيب الطباعة (%s)", type(e).__name__)
        return {"ok": True, "data": data, "mime": mime, "provider": name, "tried": tried, "ai": True,
                "typography": typo}

    # الخادم الذاتي أولًا (تسلسلي)، ثم المولدات الخارجية في سباق متوازٍ: أول ناتج صالح يفوز
    local = [c for c in chain if c[0] == "self_hosted"]
    remote = [c for c in chain if c[0] != "self_hosted"]
    for name, fn in local:
        got, entry = _attempt(name, fn)
        tried.append(entry)
        if got:
            return _finish(name, got)
    if len(remote) == 1:
        got, entry = _attempt(*remote[0])
        tried.append(entry)
        if got:
            return _finish(remote[0][0], got)
    elif remote:
        import concurrent.futures as cf
        import threading
        stop = threading.Event()  # يوقف طابور Horde الخاسر (ويحذف مهمته مجاملةً) بدل استهلاكه 150ث
        ex = cf.ThreadPoolExecutor(max_workers=len(remote), thread_name_prefix="media-race")
        import inspect

        def _cancellable(f):
            if "cancel" in inspect.signature(f).parameters:
                return lambda p, z: f(p, z, cancel=stop)
            return f
        futs = {ex.submit(_attempt, n, _cancellable(f)): n for n, f in remote}
        try:
            for fut in cf.as_completed(futs):
                got, entry = fut.result()
                tried.append(entry)
                if got:
                    for other, n in futs.items():
                        if other is not fut and not other.done():
                            tried.append({"provider": n, "result": "أُلغي (سبقه مولّد آخر)", "seconds": "-"})
                    return _finish(futs[fut], got)
        finally:
            stop.set()
            ex.shutdown(wait=False, cancel_futures=True)
    data, mime = design_local(shown, size, "logo" if style == "logo" else "poster", "الذكاء السيادي")
    tried.append({"provider": "local_design", "result": "ok", "seconds": "0"})
    return {"ok": True, "data": data, "mime": mime, "provider": "local_design", "tried": tried, "ai": False}


# ---------------------------------------------------------------- الفيديو
def _run_ff(args: List[str], cwd: str, timeout: int = 420) -> None:
    ff = ffmpeg_exe()
    if not ff:
        raise RuntimeError("ffmpeg غير متاح")
    r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y"] + args, cwd=cwd,
                       capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg: " + r.stderr.decode("utf-8", "replace")[-300:])


def compose_video(image_png: bytes, title: str, caption: str, size: Tuple[int, int] = (960, 540),
                  fps: int = 24) -> bytes:
    """MP4: بطاقة عنوان (2.5ث) ⇒ الصورة بتقريب بطيء (5ث) ⇒ انزياح (4ث) ⇒ بطاقة ختام (2.5ث)."""
    from PIL import Image
    W, H = size
    with tempfile.TemporaryDirectory(prefix="sov-studio-") as td:
        tdp = Path(td)
        im = Image.open(io.BytesIO(image_png)).convert("RGB")
        # تكبير لملء الإطار بنسبة الصورة ثم مساحة حركة 1.6x
        big = (int(W * 1.6), int(H * 1.6))
        sc = max(big[0] / im.width, big[1] / im.height)
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))))
        left, top = (im.width - big[0]) // 2, (im.height - big[1]) // 2
        im.crop((left, top, left + big[0], top + big[1])).save(tdp / "img.png")
        (tdp / "title.png").write_bytes(design_local(title, size, "poster", "")[0])
        (tdp / "end.png").write_bytes(design_local(caption, size, "poster", "الذكاء السيادي")[0])
        segs = [("title.png", 2.5, None), ("img.png", 5.0, "in"), ("img.png", 4.0, "pan"), ("end.png", 2.5, None)]
        names = []
        for i, (src, dur, motion) in enumerate(segs):
            n = int(dur * fps)
            if motion == "in":
                vf = (f"zoompan=z='min(1+0.45*on/{n},1.45)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                      f":d={n}:s={W}x{H}:fps={fps}")
            elif motion == "pan":
                vf = (f"zoompan=z='1.35':x='(iw-iw/zoom)*on/{n}':y='(ih-ih/zoom)/2':d={n}:s={W}x{H}:fps={fps}")
            else:
                vf = f"scale={W}:{H},fps={fps}"
            vf += f",fade=t=in:st=0:d=0.5,fade=t=out:st={dur - 0.5:.2f}:d=0.5,format=yuv420p"
            out = f"seg{i}.mp4"
            loop = ["-loop", "1"] if motion is None else []
            _run_ff(loop + ["-i", src, "-vf", vf, "-t", f"{dur:.2f}", "-r", str(fps), "-c:v", "libx264",
                            "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", out], td)
            names.append(out)
        (tdp / "list.txt").write_text("".join(f"file '{n}'\n" for n in names), encoding="utf-8")
        _run_ff(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "-movflags", "+faststart",
                 "final.mp4"], td)
        return (tdp / "final.mp4").read_bytes()


# ---------------------------------------------------------------- نقطة الدخول
def create(req: Dict[str, Any], save=None) -> Dict[str, Any]:
    """ينفذ طلب الوسائط: يولّد ويحفظ ويعيد {ok, kind, provider, file, prompt, shown, tried, notes}."""
    t0 = time.time()
    prompt_en, shown = build_prompt(req)
    kind = req["kind"]
    size = (1024, 1024) if kind == "image" and req["style"] != "poster" else (1024, 576)
    if kind == "image" and req["style"] == "poster":
        size = (768, 1024)
    img = generate_image(prompt_en, shown, req["style"], size)
    out = {"ok": False, "kind": kind, "provider": img["provider"], "ai": img["ai"], "prompt": prompt_en,
           "typography": bool(img.get("typography")),
           "shown": shown, "tried": img["tried"], "notes": []}
    data, mime, ext = img["data"], img["mime"], "png"
    if kind == "video":
        if not ffmpeg_exe():
            out["error"] = "ffmpeg غير متاح على هذا الخادم — لا يمكن تركيب فيديو"
            return out
        try:
            data = compose_video(img["data"], shown, "من إنتاج الذكاء السيادي")
            mime, ext = "video/mp4", "mp4"
        except Exception as e:  # TOLERATED: فشل التركيب يُعلن بسببه
            out["error"] = f"تعذر تركيب الفيديو: {str(e)[:200]}"
            return out
    if save is not None:
        name = re.sub(r"[^\w\u0600-\u06FF\- ]+", "", shown)[:40].strip() or kind
        out["file"] = save(f"{name}.{ext}", data, mime)
    out.update(ok=True, mime=mime, bytes=len(data), seconds=round(time.time() - t0, 1))
    out["data"] = data
    return out


def format_reply(res: Dict[str, Any]) -> str:
    kind_ar = "الفيديو" if res.get("kind") == "video" else "الصورة"
    if not res.get("ok"):
        return f"لم أتمكن من إنشاء {kind_ar}: {res.get('error') or 'سبب غير معروف'}."
    shown_ar = "معروض" if res.get("kind") == "video" else "معروضة"
    lines = [f"تم إنشاء {kind_ar} ({res.get('seconds')} ث) — {shown_ar} أدناه."]
    lines.append(f"المولّد: {_PROVIDER_LABEL.get(res['provider'], res['provider'])}.")
    failed = [t for t in res.get("tried", []) if t["result"] != "ok" and t.get("seconds") != "-"]
    if failed:
        lines.append("مزودات جُرّبت قبله وتعذرت: " + "، ".join(f"{t['provider']} ({t['result']})" for t in failed) + ".")
    if res.get("kind") == "video":
        lines.append("الفيديو MP4 حقيقي مركّب من الصورة بحركة كاميرا وبطاقات عنوان (ليس فيديو مولّدًا بنموذج فيديو).")
    if not res.get("ai"):
        lines.append("تنبيه: هذا تصميم محلي قالبي لأن مزودات التوليد بالذكاء الاصطناعي لم تُتح الآن — أعد الطلب "
                     "بعد دقيقة لنسخة مولّدة.")
    if res.get("typography"):
        lines.append("الاسم مكتوب بطباعة محلية صحيحة فوق رسمة الذكاء الاصطناعي (المولدات تشوّه الحروف).")
    if res.get("ai") and res["provider"] in ("pollinations", "horde"):
        lines.append("ملاحظة خصوصية: الوصف أُرسل إلى مزود توليد خارجي (مفعّل بإذن MEDIA_EXTERNAL_PROVIDERS).")
    lines.append(f"الوصف المستخدم: {res.get('prompt')}")
    lines.append("لتعديلها اكتب مثلًا: «اجعلها ليلية» أو «أضف بحرًا في الخلفية».")
    return "\n".join(lines)
