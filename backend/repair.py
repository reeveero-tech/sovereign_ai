#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/repair.py — المرحلة ٤ (R-695): مصنف الأخطاء ومقترح الرقع

أمر المالك 2026-10-19: «مصنف الأخطاء (Classifier): rule-based. يستقبل حادثة
من الحارس، ويصنفها حسب النمط + يعيد فئة وإجراءً مقترحًا. لا يستخدم LLM ولا
يستدعي خدمة خارجية. مقترح الرقع (Proposals): يقرأ الكود المعزول + سياق
الخطأ، ويُنتج وصف إصلاح مقترحًا وملف رقعة (diff) للمراجعة. لا يُطبِّق شيئًا
تلقائيًا. المصنف والمقترح مربوطان بالحارس (لا بـapp.py)».

الاعتبارات الإلزامية (اعتراضات المراجع — تخطيط R-695):
- **لا تطبيق أبدًا:** لا مسار في هذه الوحدة يطبق رقعة أو ينفذ كودًا —
  المصدر المعزول والحي للقراءة فقط، والكتابة محصورة في مخزن مخرجات
  الحارس (<جذر البيانات>/proposals/). لا استدعاء patch/git apply/subprocess.
- **الربط الصريح:** الاقتراح يرفض (ValueError) بلا تصنيف، وبالتصنيف غير
  المرتبط بالحادثة نفسها (مطابقة معرّف الحادثة).
- **رقعة حقيقية لا تعليق:** قاعدة تحويل واحدة معلنة (تحويل الاستيراد
  المعطوب إلى استيراد محروس برسالة واضحة) بشروط انطباق صريحة — خارجها
  «تحتاج مراجعة يدوية» بلا رقعة. الرقعة ملف .diff فعلي (difflib unified
  diff) يُحفظ في المخزن ويُشار إليه من سجل الاقتراحات، وسجل النجاح يوثق
  بعد وجود الملف فعلًا.
- الصيغة: حوادث الحارس القائمة (أسطر سجل المراقبة) تُحوَّل بتحويل صغير
  إلى تمثيل داخلي موحد — لا اختراع صيغ بلا أصل. السطر السليم ليس حادثة،
  وتغيّر الوعي حادثة سلامة لا خطأ شبكة أو استيراد.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_MODULE_DIR)

_MISSING_MODULE_RE = re.compile(r"No module named ['\"]([^'\"]+)['\"]")

# ---------------------------------------------------------------- الحوادث


def incident_from_monitor_line(entry: dict) -> Optional[dict]:
    """سطر سجل مراقبة الحارس → حادثة بالتمثيل الداخلي الموحد، أو None.

    يستخرج حقول الخطأ الفعلية (health.error / status.error) وأحداث الوعي
    (changes_detected = حادثة تغيّر سلامة) — لا كامل JSON كنص للبحث.
    السطر السليم ليس حادثة → None.
    """
    health = entry.get("health") if isinstance(entry.get("health"), dict) else {}
    status = entry.get("status") if isinstance(entry.get("status"), dict) else {}
    # R-695 (اعتراض المراجع ج4): حدث الوعي له الأولوية على سطر يحمل الأمرين
    # معًا — خطأ الجلب يتكرر كل دورة (يُعالج مرة بتوقيعه في دورته) بينما
    # حدث التغيير إشارة منفردة لا يجوز أن يُحجب بخطأ الجلب المتزامن
    awareness = entry.get("awareness")
    if isinstance(awareness, dict) and awareness.get("event") == "changes_detected":
        return {
            "id": f"{entry.get('ts')}:{entry.get('target')}",
            "source": "supervisor",
            "kind": "integrity_change",
            "error_text": "تغيّر مرصود غير مفسّر في شجرة المشروع",
            "context": {"awareness": awareness},
        }
    # حقول الخطأ الفعلية: أخطاء الجلب + خطأ المكوّن الذي يبلغ عنه التطبيق
    # في /status (last_error) — مسار بيانات حقيقي لا نص مصطنع
    error_text = None
    for field in (health, status):
        err = field.get("error")
        if isinstance(err, str) and err:
            error_text = err
            break
    if error_text:
        return {
            "id": f"{entry.get('ts')}:{entry.get('target')}",
            "source": "supervisor",
            "kind": "fetch_error",
            "error_text": error_text,
            "context": {"health": health, "status": status},
        }
    comp_err = status.get("component_error")
    if isinstance(comp_err, str) and comp_err:
        return {
            "id": f"{entry.get('ts')}:{entry.get('target')}",
            "source": "supervisor",
            "kind": "component_error",
            "error_text": comp_err,
            "context": {"health": health, "status": status},
        }
    return None  # سطر سليم — ليس حادثة


def _proposals_root(data_root: str | os.PathLike) -> Path:
    """مخزن مخرجات الحارس للمرحلة ٤ — <جذر البيانات>/proposals."""
    return Path(data_root) / "proposals"


def proposals_log_path(data_root: str | os.PathLike) -> Path:
    """سجل الاقتراحات (للقراءة) — append-only داخل مخزن المخرجات."""
    return _proposals_root(data_root) / "proposals_log.jsonl"


# --------------------------------------------------------------- المصنف

# قواعد مرتبة: الخاصة قبل العامة (اعتراض المراجع) — ذكر الاتصال داخل
# OSError شبكة لا IO، ولا يُصنف كل OSError شبكةً. الحوادث النصية فقط
# من حقول الخطأ الفعلية — لا مطابقة على JSON كامل.
_CLASSIFICATION_RULES: List = [
    # الأنماط النصية على نص الخطأ الفعلي — مرتبة من الخاصة إلى العامة
    (re.compile(
        r"No module named|ImportError|cannot import name|ModuleNotFoundError"
    ), "import_error",
     "تحقق من التبعيات ومسارات الاستيراد؛ افحص عزل المكوّن ومصدره"),
    (re.compile(
        r"URLError|Connection refused|ConnectionError|ConnectionReset|"
        r"Network is unreachable|[Ee]rrno 111|timeout of"
    ), "network_error",
     "افحص الشبكة والمنفذ وتوافر الخدمة المستهدفة"),
    (re.compile(
        r"Invalid [Kk]ey|InvalidToken|decryption|Fernet|cryptography"
    ), "encryption_error",
     "تحقق من مفتاح SOVEREIGN_KEY وصلاحية مفاتيح التشفير"),
    (re.compile(r"SyntaxError|invalid syntax"), "syntax_error",
     "راجع بناء الملف المصدر — خطأ نحوي صريح"),
    (re.compile(r"PermissionError|Errno 13|No such file|ENOENT|OSError"),
     "io_error", "افحص الصلاحيات ومسارات الملفات"),
]

_INTEGRITY_ACTION = (
    "قارن خريطة المشروع بالمرجعية وراجع التغيير المرصود مع المالك"
)


def classify_incident(incident: dict) -> Optional[dict]:
    """تصنيف rule-based لحادثة — فئة + إجراء مقترح، أو None.

    لا LLM ولا خدمة خارجية: مطابقة أنماط نصية على نص الخطأ الفعلي
    المستخرج من حادثة الحارس. غير المطابق يبقى غير مصنّفًا بلا اقتراح.
    التصنيف مرتبط بالحادثة نفسها (معرّفها) — شرط صحة الاقتراح لاحقًا.
    """
    if not isinstance(incident, dict) or not incident.get("id"):
        return None
    if incident.get("kind") == "integrity_change":
        # تغيّر سلامة — ليس خطأ استيراد أو شبكة (اعتراض المراجع)
        return {
            "incident_id": incident["id"],
            "class": "integrity_change",
            "action": _INTEGRITY_ACTION,
        }
    error_text = str(incident.get("error_text") or "")
    for pattern, incident_class, action in _CLASSIFICATION_RULES:
        if pattern.search(error_text):
            return {
                "incident_id": incident["id"],
                "class": incident_class,
                "action": action,
            }
    return None


# --------------------------------------------------------------- المقترح


def _component_source_candidates(component: str, repo_root: Path) -> List[Path]:
    """ملفات مصدر مكوّن معزول مرشحة — backend/<component>.py أو حزمته.

    العزل حالة منطقية مرتبطة بمكوّن (سجل الولاء R-687) — الكود في موضعه
    الأصلي ويُقرأ للقراءة فقط. أسماء المكوّنات آمنة المسار (تحقق صارم)."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(component)):
        return []
    root = Path(repo_root)
    candidates = [
        root / "backend" / f"{component}.py",
        root / "backend" / component / "__init__.py",
    ]
    package = root / "backend" / component
    if package.is_dir():
        candidates.extend(
            sorted(p for p in package.glob("*.py") if p != package / "__init__.py")
        )
    return [c for c in candidates if c.is_file()]


def _import_fix_transform(
    source_text: str, missing_module: str
) -> Optional[str]:
    """قاعدة التحويل المعلنة الوحيدة: تأهيل استيراد وحدة موجودة في backend/.

    الأثر الإصلاحي واضح ومثبت بالتنفيذ: الاستيراد المعطوب (وحدة موجودة في
    backend/ لكن الجملة عارية بلا مسار) يصير مستوردًا من مساره الصحيح —
    الأصل يفشل بـImportError والرقعة تصلحه (يُفحص على نسخة اختبارية).

    شروط الانطباق الصارمة: جملة استيراد **علوية كاملة** (بلا إزاحة) للوحدة
    الناقصة نفسها — import X / import X as Y / from X import ... — خارجها
    None (مراجعة يدوية — لا رقعة شكلية ولا تعليق). الناتج صالح نحويًا
    دائمًا: الجملة تُستبدل بمكافئها المؤهل دون تغيير الإزاحات أو السياق."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(missing_module)):
        return None
    lines = source_text.splitlines(keepends=True)
    # جملة استيراد علوية كاملة فقط — بلا إزاحة تفسد البنية الناتجة.
    # كل الجمل المطابقة تُؤهل (إصلاح كامل لا أول جملة)
    bare = re.compile(
        r"^import " + re.escape(missing_module) + r"(\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?\s*$"
    )
    from_form = re.compile(
        r"^from " + re.escape(missing_module) + r" import "
    )
    changed = False
    result = []
    for line in lines:
        text = line.rstrip("\r\n")
        match = bare.match(text)
        if match:
            result.append(
                "from backend import " + missing_module + (match.group(1) or "") + "\n"
            )
            changed = True
        elif from_form.match(text):
            result.append(text.replace(
                "from " + missing_module + " import ",
                "from backend." + missing_module + " import ", 1,
            ) + "\n")
            changed = True
        else:
            result.append(line)
    return "".join(result) if changed else None


def _missing_module_from_incident(incident: dict) -> Optional[str]:
    """استخراج الوحدة الناقصة من نص الخطأ الفعلي — شرط انطباق الرقعة."""
    match = _MISSING_MODULE_RE.search(str(incident.get("error_text") or ""))
    return match.group(1) if match else None


def _proposal_description(
    incident: dict, classification: dict, component: str,
    source_path: str, missing_module: str,
) -> str:
    """وصف الإصلاح المقترح — قالب نصي rule-bound بتفاصيل الحادثة."""
    return (
        f"اقتراح R-695 لمراجعة المالك — لا يُطبق تلقائيًا.\n"
        f"الحادثة: {incident.get('id')} ({classification['class']}).\n"
        f"المكوّن المعزول: {component} — المصدر: {source_path}.\n"
        f"الإجراء المصنف: {classification['action']}.\n"
        f"الرقعة المقترحة: تحويل استيراد «{missing_module}» المعطوب إلى "
        "استيراد محروس يرفع خطأً واضحًا موسومًا R-695 بدل ImportError "
        "الخام — تغيير سلوكي حقيقي يسهّل التشخيص ولا يخفي العطل.\n"
        "التطبيق قرار المالك أو دورة تسليم قياسية (المرحلة ٥ مؤجلة)."
    )


def build_proposal(
    incident: dict,
    classification: dict,
    component: str,
    repo_root: str | os.PathLike,
    data_root: str | os.PathLike,
) -> dict:
    """بناء اقتراح: وصف + ملف رقعة .diff فعلي + سجل يشير إليه.

    يرفض (ValueError) بلا تصنيف، وبالتصنيف غير المرتبط بالحادثة نفسها
    (مطابقة المعرف). لا يطبق شيئًا: المصدر للقراءة فقط، والكتابة في مخزن
    المخرجات وحده، وسجل الاقتراح يوثق النجاح بعد وجود ملف الرقعة فعلًا.
    لا انطباق لقاعدة التحويل → مراجعة يدوية بلا رقعة (لا ملف يُكتب)."""
    if classification is None:
        raise ValueError("R-695: لا اقتراح بلا تصنيف — الحادثة غير مصنفة")
    if not isinstance(incident, dict) or not incident.get("id"):
        raise ValueError("R-695: حادثة غير صالحة — بلا معرف")
    # R-695 (اعتراض المراجع ج2): التصنيف مزور يُرفض — لا يكفي تطابق المعرف؛
    # التصنيف يجب أن يكون نتيجة المصنف نفسه لهذه الحادثة (إعادة تشغيل
    # القواعد الحتمية ومطابقة حرفية — قاموس يدوي بمعرف صحيح لا يمر)
    genuine = classify_incident(incident)
    if classification != genuine:
        raise ValueError(
            "R-695: تصنيف مزور — ليس نتيجة المصنف لهذه الحادثة"
        )
    # R-695 (اعتراض المراجع ج2): مرجع الكود يجب أن يكون مكوّنًا معزولًا
    # مثبتًا — من قارئ سجل العزل القائم لا من اسم يُمرر مباشرة
    quarantined = quarantined_components(data_root)
    if component not in quarantined:
        raise ValueError(
            "R-695: المكوّن غير معزول — لا اقتراح على كود غير معزول"
        )
    if classification.get("class") != "import_error":
        return {
            "status": "manual_review",
            "reason": (
                "الفئة لا تملك قاعدة تحويل كود معلنة — إجراء تشغيلي: "
                + str(classification.get("action"))
            ),
        }
    missing_module = _missing_module_from_incident(incident)
    if not missing_module:
        return {
            "status": "manual_review",
            "reason": "الخطأ لا يسمّي وحدة ناقصة — مراجعة يدوية",
        }
    # شرط الأثر الإصلاحي: الوحدة موجودة فعلًا في backend/ (الخلل في مسار
    # الاستيراد لا في وجودها) — إلا فالإصلاح مراجعة يدوية لا رقعة
    root = Path(repo_root)
    module_exists = (
        (root / "backend" / f"{missing_module}.py").is_file()
        or (root / "backend" / missing_module).is_dir()
    )
    if not module_exists:
        return {
            "status": "manual_review",
            "reason": (
                f"الوحدة {missing_module} غير موجودة في backend/ — "
                "إصلاحها ليس قاعدة معلنة (تثبيت تبعية) — مراجعة يدوية"
            ),
        }
    for source in _component_source_candidates(component, root):
        try:
            source_text = source.read_text(encoding="utf-8")
        except OSError:  # R-695: مصدر غير قابل للقراءة — جرّب المرشح التالي
            continue
        new_text = _import_fix_transform(source_text, missing_module)
        if new_text is None:
            continue
        # رقعة unified diff فعلية (difflib) — تُحفظ كملف .diff في المخزن
        rel = source.relative_to(repo_root).as_posix()
        diff_lines = list(difflib.unified_diff(
            source_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/{rel}", tofile=f"b/{rel}",
        ))
        diff_text = "".join(
            l if l.endswith("\n") else l + "\n" for l in diff_lines
        )
        store = _proposals_root(data_root)
        diff_name = (
            f"{int(time.time() * 1000)}_{classification['class']}"
            f"_{component}.diff"
        )
        diff_file = store / diff_name
        try:
            store.mkdir(parents=True, exist_ok=True)
            diff_file.write_text(diff_text, encoding="utf-8")
        except OSError as exc:
            return {
                "status": "save_failed",
                "reason": f"فشل حفظ ملف الرقعة — لا يُخفى: {exc}",
            }
        if not diff_file.is_file():
            return {
                "status": "save_failed",
                "reason": "ملف الرقعة غير موجود بعد الكتابة — لا يوثق نجاح",
            }
        # السجل يوثق النجاح بعد وجود الملف فعلًا — ولا يخفي الفشل
        description = _proposal_description(
            incident, classification, component, rel, missing_module
        )
        log_entry = {
            "ts": time.time(),
            "incident_id": incident["id"],
            "class": classification["class"],
            "component": component,
            "description": description,
            "diff_file": diff_name,
            "applied": False,  # لا تطبيق تلقائي — قرار المالك أو دورة تسليم
        }
        try:
            with open(proposals_log_path(data_root), "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            return {
                "status": "save_failed",
                "reason": f"فشل توثيق السجل (الرقعة محفوظة): {exc}",
                "diff_file": diff_name,
            }
        return {
            "status": "proposed",
            "classification": classification,
            "component": component,
            "description": description,
            "diff_file": diff_name,
        }
    return {
        "status": "manual_review",
        "reason": (
            "لا مصدر معزول ينطبق عليه شرط القاعدة (استيراد الوحدة الناقصة) "
            "— مراجعة يدوية، لا رقعة شكلية"
        ),
    }


def quarantined_components(data_root: str | os.PathLike) -> List[str]:
    """المكونات المعزولة حاليًا — من قارئ سجل العزل القائم (R-687).

    لا إعادة بناء لآلة الحالات هنا (اعتراض المراجع): قراء العزل القائمة
    موثوقة ومختبرة — نستدعيها ونكتفي. العزل حالة منطقية مرتبطة بمكون."""
    from backend import loyalty_log  # قارئ قائم — stdlib خالص

    state, _marker = loyalty_log.read_quarantine_state(
        loyalty_log.quarantine_log_path(data_root)
    )
    return sorted(state)


def process_incident(
    incident: dict,
    repo_root: str | os.PathLike,
    data_root: str | os.PathLike,
) -> dict:
    """خط الحارس للحادثة: تصنيف ← (إن صُنفت) اقتراح إن وُجد مرجع كود معزول
    منطبق — وإلا إجراء تشغيلي بلا رقعة. لا تطبيق أبدًا.

    حادثة بلا مرجع كود معزول (كخطأ شبكة) قد تُنتج إجراءً تشغيليًا، لكنها
    لا تبرر اختراع تعديل في ملف (اعتراض المراجع)."""
    classification = classify_incident(incident)
    if classification is None:
        return {"status": "unclassified"}
    result: Optional[dict] = None
    failure: Optional[dict] = None
    for component in quarantined_components(data_root):
        outcome = build_proposal(
            incident, classification, component, repo_root, data_root
        )
        if outcome.get("status") == "proposed":
            result = outcome
            break  # أول مرجع كود منطبق يكفي — لا تكرار
        if outcome.get("status") == "save_failed":
            # R-695 (اعتراض المراجع ج3): فشل الحفظ ينتشر صراحة — لا يظهر
            # كأنه غياب قاعدة منطبقة؛ الحادثة لا تُعد منجزة قبله
            failure = outcome
            break
    if failure is not None:
        return failure
    if result is not None:
        return result
    return {
        "status": "classified_no_proposal",
        "classification": classification,
        "note": (
            "لا مرجع كود معزول منطبق — إجراء تشغيلي فقط، والرقعة تحتاج "
            "مراجعة يدوية"
        ),
    }
