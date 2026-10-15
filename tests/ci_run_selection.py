#!/usr/bin/env python3
"""
R-682 — منطق اختيار تشغيل CI المرجعي (مشترك بين verify.sh والاختبارات).

لماذا وحدة مستقلة؟
- قبل R-682 كان المنطق داخل verify.sh فقط — غير قابل للاختبار الحتمي.
- أول تشغيل لمهمة verify-full كشف خطأ انتقاء ذاتيًا حقيقيًا: فحص الحالة
  كان يمسح بأول تشغيل مطابق للـ headSha فالتقط تشغيل verify-full نفسه
  (قيد التنفيذ) بدل التشغيل المرجعي المكتمل.

القواعد (حتمية، قابلة للاختبار):
1. إن حُدد معرّف صريح (--explicit): يُستخدم هو — مع التحقق من تطابق
   headSha والـ workflow. لا انتقاء ذاتي إطلاقًا.
2. وإلا: يُفضل تشغيل push على الـ SHA نفسه؛ فإن لم يوجد فأول تشغيل
   للـ SHA (سلوك توافقي مع ما قبل R-682).
3. فحص الهوية: الـ workflow يجب أن يكون ci.yml (اسمه يحتوي "CI").
4. مع --require-completed: يجب أن يكون مكتملًا وناجحًا.
"""
import argparse
import json
import sys

REQUIRED_WORKFLOW_HINT = "CI"  # اسم workflow ci.yml يبدأ بـ "CI"


def select_ci_run(runs, target_sha, explicit_run_id=None, require_completed=False):
    """يعيد (run_id, run) أو يرفع ValueError برسالة عربية واضحة."""
    if explicit_run_id:
        try:
            explicit_id = int(explicit_run_id)
        except (TypeError, ValueError):
            raise ValueError(f"معرّف صريح غير رقمي: {explicit_run_id!r}")
        for r in runs:
            if r.get("databaseId") == explicit_id:
                if r.get("headSha") != target_sha:
                    raise ValueError(
                        f"التشغيل الصريح {explicit_id} لا يطابق HEAD SHA {target_sha[:10]} "
                        f"(headSha={str(r.get('headSha'))[:10]})"
                    )
                run = r
                break
        else:
            raise ValueError(f"التشغيل الصريح {explicit_id} غير موجود في التشغيلات الحديثة")
    else:
        run = None
        for r in runs:
            if r.get("headSha") == target_sha and r.get("event") == "push":
                run = r
                break
        if run is None:
            for r in runs:
                if r.get("headSha") == target_sha:
                    run = r
                    break
        if run is None:
            raise ValueError(f"لا يوجد أي تشغيل CI للـ SHA {target_sha[:10]}")

    # فحص الهوية: workflow ci.yml
    workflow = str(run.get("workflowName") or run.get("workflow") or "")
    if REQUIRED_WORKFLOW_HINT not in workflow:
        raise ValueError(
            f"التشغيل {run.get('databaseId')} ليس من workflow ci.yml "
            f"(workflow={workflow!r}) — لا يُقارن سجل JUnit إلا من ci.yml"
        )

    if require_completed:
        if run.get("status") != "completed":
            raise ValueError(
                f"التشغيل {run.get('databaseId')} غير مكتمل (status={run.get('status')!r})"
            )
        if run.get("conclusion") != "success":
            raise ValueError(
                f"التشغيل {run.get('databaseId')} نتيجته {run.get('conclusion')!r} (يجب success)"
            )

    return run.get("databaseId"), run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", required=True)
    ap.add_argument("--explicit", default=None)
    ap.add_argument("--require-completed", action="store_true")
    args = ap.parse_args()

    runs = json.load(sys.stdin)

    try:
        run_id, run = select_ci_run(
            runs, args.sha, args.explicit, require_completed=args.require_completed
        )
    except ValueError as e:
        print(f"❌ [اختيار تشغيل CI] {e}", file=sys.stderr)
        sys.exit(1)

    print(run_id)


if __name__ == "__main__":
    main()
