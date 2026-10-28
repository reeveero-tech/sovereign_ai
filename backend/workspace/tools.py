"""R-800: أدوات مساحة العمل في السجل — يستعملها وكيل المحادثة والأسطول والمحرك.

مخرجات مقتضبة (العقل 3B بسياق محدود): القراءة 6000 حرف لكل نداء مع offset للمتابعة.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .service import get_workspace

TOOL_READ_LIMIT = 6000


def _slim(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {k: rec.get(k) for k in ("id", "name", "path", "kind", "size", "project_id", "parent", "source")}


def _ids(v: Any) -> List[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def register(registry, ToolSpec) -> None:
    ws = get_workspace
    specs = [
        ("workspace.status", "R-800: حالة مساحة العمل — عدد الملفات وأنواعها والتخزين والدوام والصيغ المتاحة",
         {}, "files/kinds/durable/create_formats", lambda: ws().status()),
        ("files.list", "R-800: سرد ملفات المالك (اختياريًا لمشروع أو نوع: pdf/docx/xlsx/csv/image/archive/text…)",
         {"project_id": "معرف مشروع (اختياري)", "kind": "نوع (اختياري)"}, "files[]",
         lambda project_id=None, kind=None: {"files": [_slim(f) for f in ws().list_files(project_id or None, kind or None)][:100]}),
        ("files.search", "R-800: بحث في أسماء الملفات ونصوصها المستخرجة مع مقتطف",
         {"q": "نص البحث"}, "hits[]",
         lambda q: {"hits": [{"file": _slim(h["file"]), "score": h["score"], "snippet": h["snippet"]}
                             for h in ws().search(q)]}),
        ("files.read", "R-800: قراءة المحتوى المستخرج لملف (PDF/Word/Excel/PowerPoint/CSV/JSON/نص/كود/أرشيف) — 6000 حرف لكل نداء",
         {"file_id": "معرف الملف F-…", "offset": "بداية القراءة (اختياري)"}, "text/structure/more",
         lambda file_id, offset=0: ws().read(file_id, int(offset or 0), TOOL_READ_LIMIT)),
        ("files.analyze", "R-800: تحليل عميق لملف — حقائق محسوبة + ملخص العقل + رؤية للصور + تفريغ للصوت + بيانات الفيديو",
         {"file_id": "معرف الملف", "question": "سؤال محدد عن الملف (اختياري)"}, "findings/summary/vision",
         lambda file_id, question=None: ws().analyze(file_id, question or None)),
        ("files.unpack", "R-800: تفكيك أرشيف (zip/tar/gz/bz2/xz/7z) آمنًا إلى ملفات في مساحة العمل",
         {"file_id": "معرف ملف الأرشيف"}, "extracted/skipped/files",
         lambda file_id: (lambda r: r | {"files": [_slim(f) for f in r["files"]][:100]})(ws().unpack(file_id))),
        ("files.zip", "R-800: ضغط ملفات من مساحة العمل في ملف zip جديد",
         {"file_ids": "معرفات مفصولة بفواصل", "name": "اسم الملف (اختياري)"}, "file",
         lambda file_ids, name="bundle.zip": _slim(ws().zip(_ids(file_ids), name or "bundle.zip"))),
        ("files.create", "R-800: إنشاء ملف حقيقي: txt/md/html/json/csv/xlsx/docx/pdf/pptx/png من عنوان ومحتوى (Markdown: # عنوان، - بند)",
         {"format": "الصيغة", "title": "العنوان", "content": "المحتوى"}, "file",
         lambda format, title="", content="": _slim(ws().create(format, title, content))),
        ("files.convert", "R-800: تحويل ملف إلى صيغة أخرى (مثل PDF⇒DOCX نصًا، CSV⇒XLSX، DOCX⇒PDF)",
         {"file_id": "معرف الملف", "format": "الصيغة الهدف"}, "file",
         lambda file_id, format: _slim(ws().convert(file_id, format))),
        ("projects.list", "R-800: مشاريع المالك مع عدد ملفاتها ومحادثاتها",
         {}, "projects[]", lambda: {"projects": ws().list_projects()}),
    ]
    for name, desc, inputs, outputs, handler in specs:
        registry.register(ToolSpec(name=name, description=desc, inputs=inputs, outputs=outputs,
                                   handler=handler))
