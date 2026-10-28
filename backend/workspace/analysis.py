"""R-800: التحليل العميق لملف — طبقتان صادقتان:

1. حتمية (دائمًا، بلا عقل): إحصاءات وبنية واكتشافات قابلة للتحقق من البايتات نفسها
   (لغة النص، كثافة الأسطر، أعمدة رقمية، صفحات بلا نص، أعضاء أرشيف خطرة…).
2. معرفية (إن توفر): العقل يلخّص ويجيب عن سؤال المالك من النص المستخرج حرفيًا؛
   الرؤية تصف الصورة؛ STT يفرّغ الصوت؛ ffprobe يقرأ بيانات الفيديو. كل طبقة غير متاحة
   تُعلن {"available": false, "reason": ...} — لا ملخص مختلق.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

BRAIN_CHARS = 6000
SYSTEM = ("أنت محلل ملفات دقيق. حلّل المحتوى المعطى حرفيًا فقط بالعربية: ما هو، بنيته، "
          "أهم ما فيه، أي مشكلات أو أخطاء أو تناقضات، وخلاصة عملية. لا تخترع ما ليس في النص؛ "
          "إن كان المقتطف مقصوصًا فقل ذلك.")


def _lang(text: str) -> Dict[str, Any]:
    ar = len(re.findall(r"[\u0600-\u06FF]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    tot = ar + lat or 1
    return {"arabic_ratio": round(ar / tot, 3), "latin_ratio": round(lat / tot, 3)}


def findings(name: str, ex: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    st = ex.get("structure") or {}
    kind = ex.get("kind")
    if not ex.get("supported"):
        out.append(f"غير مدعوم للقراءة المباشرة: {ex.get('error')}")
    if ex.get("truncated"):
        out.append(f"النص طويل ({ex.get('chars')} حرف) — الاستخراج مقصوص عند الحد")
    if kind == "pdf" and st.get("pages_without_text"):
        out.append(f"{st['pages_without_text']} من {st['pages']} صفحة بلا نص قابل للاستخراج")
    if kind == "pdf" and st.get("encrypted"):
        out.append("الملف مشفر")
    if kind == "csv":
        nums = [c["name"] for c in st.get("column_stats", []) if c.get("numeric")]
        out.append(f"{st.get('rows')} صف × {st.get('columns')} عمود؛ أعمدة رقمية: {nums or 'لا شيء'}")
        empty = [c["name"] for c in st.get("column_stats", []) if c.get("non_empty", 0) < (st.get("rows") or 0)]
        if empty:
            out.append(f"أعمدة فيها خانات فارغة: {empty[:10]}")
    if kind == "archive":
        risky = [m["name"] for m in st.get("members", [])
                 if m.get("link") or m.get("special") or m["name"].startswith("/") or ".." in m["name"]]
        if risky:
            out.append(f"أعضاء خطرة لن تُفك: {risky[:10]}")
        exts = Counter((m["name"].rsplit(".", 1)[-1].lower() if "." in m["name"] else "-")
                       for m in st.get("members", []) if not m.get("dir"))
        out.append(f"{st.get('files')} ملف، {st.get('total_size')} بايت؛ الامتدادات: {dict(exts.most_common(8))}")
    if kind in ("text", "markup") and ex.get("text"):
        t = ex["text"]
        lines = t.splitlines()
        long_lines = sum(1 for l in lines if len(l) > 200)
        if long_lines:
            out.append(f"{long_lines} سطر أطول من 200 حرف")
        todo = len(re.findall(r"\b(TODO|FIXME|XXX|HACK)\b", t))
        if todo:
            out.append(f"{todo} علامة TODO/FIXME")
        secrets = re.findall(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}", t)
        if secrets:
            out.append(f"تحذير: {len(secrets)} نمط يشبه سرًا مكشوفًا ({sorted(set(s.lower() for s in secrets))})")
    if kind == "image":
        out.append(f"{st.get('width')}×{st.get('height')} بكسل، {st.get('frames')} إطار")
    return out


def _ffprobe(data: bytes) -> Dict[str, Any]:
    if not shutil.which("ffprobe"):
        return {"available": False, "reason": "ffprobe غير مثبت"}
    with tempfile.NamedTemporaryFile(suffix=".bin") as f:
        f.write(data)
        f.flush()
        p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
                            "-show_streams", f.name], capture_output=True, timeout=60)
    if p.returncode != 0:
        return {"available": True, "error": p.stderr.decode("utf-8", "replace")[:300]}
    d = json.loads(p.stdout or b"{}")
    fmt = d.get("format") or {}
    return {"available": True, "duration": fmt.get("duration"), "format": fmt.get("format_name"),
            "streams": [{k: s.get(k) for k in ("codec_type", "codec_name", "width", "height",
                                                "r_frame_rate", "sample_rate", "channels")}
                        for s in d.get("streams") or []]}


def _brain_default(system: str, user: str) -> Optional[str]:
    import ollama_client
    return ollama_client.chat(system, user, max_tokens=900)


def _brain_ready() -> Dict[str, Any]:
    try:
        import config
        ok = bool(config.OLLAMA_ENABLED and config.OLLAMA_MODEL)
        return {"available": ok, "reason": None if ok else "العقل غير مفعّل"}
    except Exception as exc:  # TOLERATED: بلا إعدادات — العقل غير متاح معلن
        return {"available": False, "reason": f"{type(exc).__name__}"}


def analyze(name: str, data: bytes, ex: Dict[str, Any], question: Optional[str] = None,
            brain: Optional[Callable[[str, str], Optional[str]]] = None,
            vision: Optional[Callable[[bytes, str, Optional[str]], Optional[str]]] = None,
            stt: Optional[Callable[[bytes, str, str], Optional[str]]] = None,
            content_type: str = "") -> Dict[str, Any]:
    text = ex.get("text") or ""
    out: Dict[str, Any] = {"file": name, "kind": ex.get("kind"), "bytes": len(data),
                           "findings": findings(name, ex), "structure": ex.get("structure"),
                           "language": _lang(text) if text else None}
    kind = ex.get("kind")
    if kind == "image":
        if vision is None:
            import vision_client
            vision = vision_client.describe
        try:
            desc = vision(data, content_type or "image/png", question)
        except Exception as exc:  # TOLERATED: فشل الرؤية يُعلن حرفيًا
            desc, out["vision_error"] = None, f"{type(exc).__name__}: {str(exc)[:200]}"
        out["vision"] = ({"available": True, "description": desc} if desc else
                         {"available": False, "reason": out.get("vision_error") or
                          "نموذج الرؤية غير مفعّل (VISION_ENABLED/VISION_MODEL) أو لم يُرجع وصفًا"})
        if desc:
            text = desc
    if kind == "audio":
        if stt is None:
            import stt_client
            stt = stt_client.transcribe
        try:
            tr = stt(data, name, content_type or "audio/mpeg")
        except Exception as exc:  # TOLERATED: فشل التفريغ يُعلن حرفيًا
            tr = None
            out["stt_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        out["transcript"] = ({"available": True, "text": tr} if tr else
                             {"available": False, "reason": out.get("stt_error") or
                              "محرك STT غير مفعّل (STT_ENABLED)"})
        if tr:
            text = tr
    if kind in ("video", "audio"):
        out["media"] = _ffprobe(data)
    if not text.strip():
        out["summary"] = {"available": False, "reason": "لا نص مستخرج لتحليله"}
        return out
    if brain is None:
        ready = _brain_ready()
        if not ready["available"]:
            out["summary"] = ready
            return out
        brain = _brain_default
    excerpt = text[:BRAIN_CHARS]
    user = (f"الملف: {name} (نوع: {kind})\nحقائق محسوبة: {json.dumps(out['findings'], ensure_ascii=False)}\n"
            f"{'المقتطف مقصوص: أول ' + str(BRAIN_CHARS) + ' حرف من ' + str(len(text)) if len(text) > BRAIN_CHARS else ''}\n"
            f"--- المحتوى ---\n{excerpt}\n--- نهاية ---\n"
            + (f"سؤال المالك: {question}" if question else "قدّم التحليل."))
    try:
        reply = brain(SYSTEM, user)
    except Exception as exc:  # TOLERATED: فشل العقل يُعلن حرفيًا
        reply = None
        out["brain_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    out["summary"] = ({"available": True, "text": reply, "input_chars": len(excerpt),
                       "truncated_input": len(text) > BRAIN_CHARS} if reply else
                      {"available": False, "reason": out.get("brain_error") or "العقل لم يرد"})
    return out
