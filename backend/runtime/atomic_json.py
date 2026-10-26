"""كتابة JSON ذرية موحدة — R-781 (ROADMAP_V6 ٦.١.٨).

`with open(p, "w") as f: json.dump(obj, f)` يقتطع الملف أولًا ثم يكتب تدريجيًا؛ أي فشل في
المنتصف (قيمة غير قابلة للتسلسل، OOM، قتل العملية) يترك ملفًا نصف مكتوب فتضيع الحالة عند
الإقلاع التالي. هنا: التسلسل كاملًا في الذاكرة أولًا (فالفشل لا يلمس القرص)، ثم ملف مؤقت في
الدليل نفسه، ثم fsync، ثم os.replace (ذري على POSIX)، ثم fsync للدليل.

يحافظ على أذونات الملف القائم؛ والملف الجديد 0644 كما كان ينتج `open(p, "w")` تحت umask 022.
لا ينشئ الدليل الأب — السلوك السابق نفسه (`open` كان يفشل أيضًا).
"""
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

_NEW_FILE_MODE = 0o644


def atomic_write_json(path: Union[str, Path], obj: Any, *, file_mode: Optional[int] = None,
                      **dumps_kwargs: Any) -> None:
    """اكتب `obj` إلى `path` ذريًا. `dumps_kwargs` تُمرَّر إلى `json.dumps` كما هي."""
    path = Path(path)
    data = json.dumps(obj, **dumps_kwargs).encode("utf-8")
    if file_mode is None:
        try:
            file_mode = stat.S_IMODE(path.stat().st_mode)
        except FileNotFoundError:
            file_mode = _NEW_FILE_MODE
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, file_mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:  # R-781: المؤقت أُزيل أو لم يُنشأ — الاستثناء الأصلي يُرفع بعدها
            pass
        raise
    try:
        dfd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dfd)
    except OSError:  # R-781: بعض الأنظمة لا تدعم fsync الدليل؛ الاستبدال تم فعلًا
        pass
    finally:
        os.close(dfd)
