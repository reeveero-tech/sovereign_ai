"""R-802: إصلاح مرساة المسودة — ربط نص «search» من العقل بالنص الحقيقي في الملف.

الدليل الحي (الإنتاج 2026-10-28، /selfdev/status): كل المسودات رُفضت بـ
`search_occurs_0_times` — العقل (qwen2.5:3b) ينسخ النافذة بإزاحة مسافات أو بفراغات
زائدة أو بحرف مختلف، فلا يصل أي تعديل إلى CI (3 مهام exhausted، 0 tested_red).

القاعدة: الإصلاح حتمي ومعلن، ولا يخترع نصًا:
  exact       — النص موجود مرة واحدة كما هو.
  rstrip      — يطابق بعد إزالة الفراغات في أواخر الأسطر (و\\r).
  indent      — يطابق بعد إزالة الإزاحة بفارق إزاحة ثابت ⇒ يُزاح البديل بنفس الفارق.
  context     — يظهر أكثر من مرة ⇒ يوسَّع بأسطر سياق من نافذة المهمة حتى يصير فريدًا.
  fuzzy:0.97  — كتلة واحدة فقط بنفس عدد الأسطر تشابهها ≥ FUZZY_MIN وتتقدم على الثانية بهامش.
والنتيجة تعود إلى validate_draft نفسه (الإنتاج و CI) ثم RED→GREEN — المرساة لا تتجاوز أي فحص.
"""

from __future__ import annotations

import difflib
from typing import Any, Dict, List, Optional, Tuple

FUZZY_MIN = 0.92
FUZZY_MARGIN = 0.03
MAX_CONTEXT = 6


def _lines(text: str) -> List[str]:
    return text.splitlines(keepends=True)


def _norm_r(line: str) -> str:
    return line.rstrip(" \t\r\n")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block(lines: List[str], i: int, n: int) -> str:
    return "".join(lines[i:i + n])


def _match_starts(orig: List[str], pat: List[str], key) -> List[int]:
    n = len(pat)
    want = [key(x) for x in pat]
    return [i for i in range(0, len(orig) - n + 1) if [key(x) for x in orig[i:i + n]] == want]


def _trim(search: str) -> List[str]:
    pat = _lines(search)
    while pat and not pat[0].strip():
        pat.pop(0)
    while pat and not pat[-1].strip():
        pat.pop()
    return pat


def _shift(text: str, delta: int) -> str:
    """إزاحة كل سطر غير فارغ بـ delta مسافة (موجب = إضافة)."""
    out = []
    for ln in _lines(text):
        if not ln.strip():
            out.append(ln)
        elif delta >= 0:
            out.append(" " * delta + ln)
        else:
            cut = min(-delta, _indent(ln))
            out.append(ln[cut:])
    return "".join(out)


def _with_eol(block: str, replace: str) -> str:
    """البديل ينتهي بسطر جديد إن كانت الكتلة الأصلية تنتهي به (لا التصاق بالسطر التالي)."""
    if block.endswith("\n") and replace and not replace.endswith("\n"):
        return replace + "\n"
    return replace


def anchor(original: str, search: str, replace: str,
           window: Optional[Tuple[int, int]] = None) -> Optional[Dict[str, Any]]:
    """يعيد {search, replace, method, score} بنص حقيقي يظهر مرة واحدة، أو None."""
    if not isinstance(search, str) or not search.strip() or not isinstance(replace, str):
        return None
    count = original.count(search)
    if count == 1:
        return {"search": search, "replace": replace, "method": "exact", "score": 1.0}
    orig = _lines(original)
    pat = _trim(search)
    if not pat:
        return None
    n = len(pat)

    if count > 1:
        return _disambiguate(original, orig, search, replace, window)

    starts = _match_starts(orig, pat, _norm_r)
    if len(starts) == 1:
        blk = _block(orig, starts[0], n)
        return {"search": blk, "replace": _with_eol(blk, replace), "method": "rstrip", "score": 1.0}

    starts = _match_starts(orig, pat, lambda x: x.strip())
    if len(starts) == 1:
        i = starts[0]
        deltas = {_indent(o) - _indent(p) for o, p in zip(orig[i:i + n], pat) if p.strip()}
        if len(deltas) == 1:
            blk = _block(orig, i, n)
            return {"search": blk, "replace": _with_eol(blk, _shift(replace, deltas.pop())),
                    "method": "indent", "score": 1.0}

    return _fuzzy(orig, pat, replace)


def _disambiguate(original: str, orig: List[str], search: str, replace: str,
                  window: Optional[Tuple[int, int]]) -> Optional[Dict[str, Any]]:
    """النص يظهر أكثر من مرة: نختار ما يقع داخل نافذة المهمة ونوسعه بالسياق حتى يصير فريدًا."""
    if window is None:
        return None
    lo, hi = window
    offsets, pos = [], original.find(search)
    while pos != -1:
        offsets.append(pos)
        pos = original.find(search, pos + 1)
    starts_line = [original.count("\n", 0, p) for p in offsets]
    inside = [(p, ln) for p, ln in zip(offsets, starts_line) if lo <= ln < hi]
    if len(inside) != 1:
        return None
    p, ln = inside[0]
    if not (p == 0 or original[p - 1] == "\n"):
        return None  # توسيع السياق بأسطر كاملة فقط
    for k in range(1, MAX_CONTEXT + 1):
        before = "".join(orig[max(0, ln - k):ln])
        cand = before + search
        if original.count(cand) == 1:
            return {"search": cand, "replace": before + replace, "method": "context", "score": 1.0}
    return None


def _fuzzy(orig: List[str], pat: List[str], replace: str) -> Optional[Dict[str, Any]]:
    n = len(pat)
    if n == 0 or n > len(orig):
        return None
    target = "".join(_norm_r(x).strip() + "\n" for x in pat)
    scored = []
    for i in range(0, len(orig) - n + 1):
        blk = "".join(_norm_r(x).strip() + "\n" for x in orig[i:i + n])
        sm = difflib.SequenceMatcher(None, target, blk, autojunk=False)
        if sm.real_quick_ratio() < FUZZY_MIN or sm.quick_ratio() < FUZZY_MIN:
            continue
        scored.append((sm.ratio(), i))
    scored.sort(reverse=True)
    if not scored or scored[0][0] < FUZZY_MIN:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < FUZZY_MARGIN:
        return None
    score, i = scored[0]
    blk = _block(orig, i, n)
    first_p = next((p for p in pat if p.strip()), "")
    first_o = next((o for o in orig[i:i + n] if o.strip()), "")
    delta = _indent(first_o) - _indent(first_p)
    if delta:
        replace = _shift(replace, delta)
    return {"search": blk, "replace": _with_eol(blk, replace), "method": f"fuzzy:{score:.2f}",
            "score": round(score, 3)}


def nearest(original: str, search: str, max_lines: int = 15) -> Optional[str]:
    """أقرب كتلة حقيقية لنص search (للتغذية الراجعة في المحاولة التالية) — نص من الملف حرفيًا."""
    orig = _lines(original)
    pat = _trim(search or "")
    if not pat or not orig:
        return None
    n = min(len(pat), len(orig), max_lines)
    target = "".join(x.strip() + "\n" for x in pat[:n])
    best, best_i = 0.0, None
    for i in range(0, len(orig) - n + 1):
        blk = "".join(x.strip() + "\n" for x in orig[i:i + n])
        r = difflib.SequenceMatcher(None, target, blk, autojunk=False).ratio()
        if r > best:
            best, best_i = r, i
    if best_i is None or best < 0.3:
        return None
    return _block(orig, best_i, n)
