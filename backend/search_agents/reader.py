"""R-829: قراءة الصفحات بـ trafilatura (adbar) المسحوبة كاملة — النص الرئيسي وتاريخ النشر والعنوان.

trafilatura تفصل متن المقال عن القوائم والإعلانات والتذييل، وتستخرج تاريخ النشر عبر htmldate —
فتدخل الصفحة المقروءة إلى التقييم بنص أنظف وتاريخ يُحسب في الحداثة. المحوِّل القديم
(web_tools._html_to_text) يبقى احتياطًا حين لا تجد trafilatura متنًا.
"""

import json
from typing import Any, Dict, Optional

from . import vendored


def extract(html: str, url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """{"text","title","date","author","sitename"} أو None (لا متن/المكتبة غير محمّلة)."""
    tf = vendored.load("trafilatura")
    if tf is None or not html or "<" not in html[:2000]:
        return None
    raw = tf.extract(html, url=url, output_format="json", with_metadata=True, include_comments=False,
                     include_tables=True, deduplicate=True)
    if not raw:
        return None
    data = json.loads(raw)
    text = (data.get("text") or "").strip()
    if len(text) < 80:
        return None
    return {"text": text, "title": (data.get("title") or "").strip(), "date": data.get("date") or None,
            "author": data.get("author") or None, "sitename": data.get("sitename") or None}
