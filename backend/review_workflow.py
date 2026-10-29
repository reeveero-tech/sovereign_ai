"""R-812 (المالك — البندان ٤ و٥ و٦ من أمر التشغيل): سير عمل التفتيش الذاتي.

الدافع (2026-10-29): «النظام يعتمد كليا على الذكاء الاصطناعي بينما يجب أن يكون
الذكاء الاصطناعي مساعد أو بترول يساعد المشروع، ويجب ان يستخدم كمرجع فقط، بينما
المشروع بنفسه يقوم بكل شي» و«لا يوجد وكلاء ذكاء اصطناعي مدمجين في المشروع
يستخدمون كمراجعين ومنفذين».

الفصل الصارم للدورين (البندان ٤ و٥):
- المنفّذ = التطبيق نفسه: يجمع الأدلة حتميًا من الأدوات المسجلة (صحة/ذاكرة/
  قرص/خزينة) — لا ذكاء اصطناعي في التنفيذ أبدًا — ويبني تقريرًا مهيكلًا.
- المراجع = الذكاء الاصطناعي: يراجع التقرير بعقد JSON صارم ويصدر حكمًا
  مسجلًا في السجل — ولا ينفّذ شيئًا بنفسه، مرجع فقط.
- التطبيق هو الحاكم: يقرر الحالة النهائية من أدلته هو أولًا ثم حكم المراجع،
  ويوثق كل شيء بأثر موقّع. مع عقل معطل يعمل السير كاملًا بحكم «بلا مراجع» —
  إثبات أن المشروع يقوم بكل شيء بنفسه والذكاء مساعد فقط (البند ٤).

البند ٦: أدوات هذا السير (system.self_review) أدوات حقيقية مطلوبة لغاية،
لا لأجل العدد — كل مكون من التقرير أداة مسجلة قائمة فعلًا في السجل.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List

logger = logging.getLogger("sovereign.review_workflow")

#: الأدوات الحتمية التي يجمعها المنفّذ — كلها مسجلة في سجل الأدوات
EXECUTOR_TOOLS: tuple = (
    "health.snapshot",
    "memory.stats",
    "disk.status",
    "vault.status",
)

#: المهلة القصوى لتوليد حكم المراجع (ثانية) — التفتيش لا يعلّق النظام
_REVIEWER_TIMEOUT = 60.0


def _gather_findings() -> Dict[str, Any]:
    """دور المنفّذ (التطبيق): أدلة حتمية — بلا أي ذكاء اصطناعي.

    كل أداة تُستدعى عبر السجل الموحد (invoke) فيوثَّق أثرها الموقّع؛ فشل أداة
    لا يوقف السير — يُسجل كعيب في التقرير نفسه (أدلة صادقة لا انهيار).
    """
    from tool_registry import get_registry

    registry = get_registry()
    findings: List[Dict[str, Any]] = []
    for name in EXECUTOR_TOOLS:
        entry: Dict[str, Any] = {"tool": name}
        try:
            outcome = registry.invoke(name, caller="self_review_executor")
            entry["ok"] = bool(outcome.get("ok"))
            # R-813 (مراجعة المستشار): الدليل الكامل يُجمع — المراجع يرى النتائج الفعلية
            # (صحة المكونات/القرص/الذاكرة) لا مجرد نجاح الاستدعاء
            entry["result"] = outcome.get("result")
            if outcome.get("error"):
                entry["error"] = str(outcome["error"])[:200]
        except RuntimeError:
            # fail-closed (نمط R-635): فشل توقيع السجل يوقف السير كله — لا يُبتلع
            # كعيب مكون ويستمر التنفيذ بلا أثر صادق
            raise
        except Exception as exc:  # أداة غير مسجلة/تعطلت — دليل يوثق لا يكسر
            entry["ok"] = False
            entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
        findings.append(entry)
    return findings


def _derive_checks(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """التحقق الحتمي (التطبيق يحكم بنفسه): كل أداة → فحص سليم/معطوب.

    لا تفسير ذكاء اصطناعي هنا — قواعد صريحة يمتلكها التطبيق.
    R-813 (مراجعة المستشار): الصحة تُقرأ من نتيجة الأداة نفسها (حالة المكون/
    القرص/الذاكرة داخل الحمولة) لا من نجاح الاستدعاء فقط — استدعاء ناجح
    يُبلّغ عن مكون معطوب يجب أن يفشل الفحص.
    """
    checks = []
    for f in findings:
        result = f.get("result")
        passed = bool(f.get("ok")) and not f.get("error")
        if passed and isinstance(result, dict):
            # أي مفتاح صريح غير سليم في الحمولة يفشل الفحص — قاعدة يمتلكها التطبيق
            for key in ("status", "healthy", "ok", "reachable", "enabled"):
                v = result.get(key)
                if v is False or (isinstance(v, str) and v.lower() in ("unhealthy", "error", "down", "false")):
                    passed = False
                    break
            errors = result.get("errors") or result.get("error_count")
            if isinstance(errors, (int, float)) and errors > 0:
                passed = False
        checks.append({
            "tool": f.get("tool"),
            "passed": passed,
            # الدليل المرفق: ما رُجعت منه الحمولة (مضغوط) — المراجع يرى الحقيقة لا أعلامًا فقط
            "evidence": _compact(result if result is not None else f.get("error")),
        })
    return checks


def _compact(value: Any, limit: int = 600) -> str:
    """ضغط الدليل لعرضه — الأرقام والحالات لا المحتوى الكامل (لا سر أبدًا)."""
    try:
        import json as _json
        blob = _json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        blob = str(value)
    return blob[:limit]


def _review_with_brain(report: Dict[str, Any]) -> Dict[str, Any]:
    """دور المراجع (الذكاء الاصطناعي — مرجع فقط): حكم JSON مسجل.

    - العقل معطل → reviewer=skipped_brain_off (السير يكتمل بلا مراجع — البند ٤).
    - رد غير JSON/فاسد → reviewer=invalid_review_reply — لا حكم مختلق أبدًا
      (المادة ١: لا ادعاء بلا دليل).
    """
    import config
    import ollama_client

    enabled = bool(config.brain_get("OLLAMA_ENABLED") and config.brain_get("OLLAMA_MODEL"))
    if not enabled:
        return {"reviewer": "skipped_brain_off", "ok": None, "issues": [], "summary": None}

    checks_blob = json.dumps(report.get("checks", []), ensure_ascii=False)
    reply = ollama_client.chat(
        "أنت مراجع تقني. راجع نتائج فحص النظام وأعد JSON فقط (بلا سياج كود) "
        "بالمفاتيح: ok (منطقي إلزامي)، issues (قائمة نصوص قصيرة للمشاكل المرصودة "
        "فقط — لا اختراع)، summary (خلاصة سطر واحد). لا تنفذ أي شيء.",
        f"تقرير الفحص (checks): {checks_blob}",
        timeout=_REVIEWER_TIMEOUT,
        json_mode=True,  # R-813: عقد صارم — الخرج JSON لا نص حر
    )
    if not reply:
        return {"reviewer": "no_reply", "ok": None, "issues": [], "summary": None}
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    if not match:
        return {"reviewer": "invalid_review_reply", "ok": None, "issues": [], "summary": None}
    try:
        verdict = json.loads(match.group(0))
    except ValueError:
        return {"reviewer": "invalid_review_reply", "ok": None, "issues": [], "summary": None}
    # R-813 (مراجعة المستشار): تحقق مستقل صارم — ok منطقي حرفي وإلا لا حكم أبدًا
    if not isinstance(verdict.get("ok"), bool):
        return {"reviewer": "invalid_review_reply", "ok": None, "issues": [], "summary": None}
    issues = verdict.get("issues")
    if not isinstance(issues, list):
        issues = []
    issues = [str(i)[:200] for i in issues[:20]]
    return {
        "reviewer": "brain",
        "ok": verdict["ok"],
        "issues": issues,
        "summary": str(verdict.get("summary") or "")[:300] or None,
    }


def run_self_review(caller: str = "owner") -> Dict[str, Any]:
    """السير الكامل: المنفّذ يجمع ← التطبيق يحكم ← المراجع يراجع ← أثر موقّع.

    الترتيب مقصود: الأدلة والحكم الأساسي من التطبيق أولًا (لا انتظار للعقل)،
    ثم مراجعة الذكاء تُسجل ولا تُنفّذ — البند ٤ حرفيًا: المشروع يقوم بكل
    شيء، والذكاء مرجع يُستشار.
    """
    started = time.time()
    findings = _gather_findings()
    checks = _derive_checks(findings)
    app_failures = [c["tool"] for c in checks if not c["passed"]]

    report = {
        "components": [f.get("tool") for f in findings],
        "checks": checks,
        "app_failures": app_failures,
    }
    verdict = _review_with_brain(report)

    # التطبيق هو الحاكم: عيوبه الحتمية تحسم «completed_with_issues»؛ وحكم
    # المراجع يُسجل ويُعرض — لا يقلب حكم التطبيق (المراجع مرجع لا منفّذ)
    reviewer_rejected = verdict.get("ok") is False
    status = "completed_with_issues" if (app_failures or reviewer_rejected) else "completed"

    # R-813 (مراجعة المستشار): أثر حكم المراجع — رفضه لا يغير تسمية فقط؛
    # التطبيق ينفّذ إعادة فحص واحدة محدودة للمكونات ويعيد الحسم منها. هذا
    # «تنفيذ يتحكم فيه الحكم» بيد التطبيق (الميزانية محدودة — لا حلقة مفتوحة)
    recheck = None
    if reviewer_rejected:
        recheck_findings = _gather_findings()
        recheck_checks = _derive_checks(recheck_findings)
        recheck_failures = [c["tool"] for c in recheck_checks if not c["passed"]]
        recheck = {
            "trigger": "reviewer_rejected",
            "app_failures": recheck_failures,
            "checks": [{"tool": c["tool"], "passed": c["passed"]} for c in recheck_checks],
        }
        # الحسم النهائي: رفض المراجع يبقى مسجلًا في الحالة (قضية تستحق النظر)،
        # وإعادة الفحص تحسم ما يؤكده التطبيق من أعطاب — التطبيق يحكم، لا المراجع
        status = "completed_with_issues" if (recheck_failures or reviewer_rejected) else "completed"

    outcome = {
        "workflow": "self_review",
        "status": status,
        "executor": "application",          # المنفّذ: التطبيق (البند ٤)
        "executor_findings": report,
        "reviewer_verdict": verdict,        # المراجع: الذكاء (مرجع فقط)
        "recheck": recheck,                 # R-813: أثر الحكم — إعادة فحص موقعة
        "duration_ms": round((time.time() - started) * 1000, 2),
    }
    from memory.core import get_core
    get_core().append_event("self_review", {
        "status": status,
        "app_failures": app_failures,
        "reviewer": verdict.get("reviewer"),
        "reviewer_ok": verdict.get("ok"),
        "recheck_triggered": bool(recheck),
        "duration_ms": outcome["duration_ms"],
    }, user=caller)
    return outcome
