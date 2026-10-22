"""R-717 — حارس ملف النشر على Fly.io عبر GitHub Actions (بأمر المالك 2026-10-22).

بيئة الوكيل لا تستطيع بناء صورة Docker (بنّاء Fly البعيد يتصل بغير HTTPS)، فاختار
المالك النشر عبر GitHub Actions. هذا الحارس يثبت أن الملف آمن بالبناء:

1. يدوي فقط (workflow_dispatch) — لا نشر تلقائي عند كل push.
2. اسمه لا يحوي «CI» — وإلا التقطه منطق اختيار التشغيل المرجعي في verify.sh
   (tests/ci_run_selection.py يتحقق أن اسم workflow يحوي «CI»).
3. الرمز من أسرار المستودع فقط — لا رمز Fly حرفي في الملف.
4. صلاحيات GITHUB_TOKEN مقيدة (contents: read، actions: read).
5. بوابة: لا نشر لالتزام بلا تشغيل CI ناجح على نفس SHA.
6. اسم التطبيق مطابق لـ fly.toml، وفحص /health بعد النشر.
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-fly.yml"
FLY_TOML = REPO_ROOT / "fly.toml"


def _load():
    assert WORKFLOW.exists(), f"ملف النشر غير موجود: {WORKFLOW.relative_to(REPO_ROOT)}"
    text = WORKFLOW.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    # PyYAML يقرأ المفتاح on كقيمة منطقية True
    triggers = data.get("on", data.get(True))
    return text, data, triggers


def _fly_app_name():
    m = re.search(r"^app\s*=\s*'([^']+)'", FLY_TOML.read_text(encoding="utf-8"), re.M)
    assert m, "لم يُعثر على app في fly.toml"
    return m.group(1)


def test_deploy_is_manual_only():
    _, _, triggers = _load()
    keys = set(triggers) if isinstance(triggers, dict) else {triggers}
    assert keys == {"workflow_dispatch"}, f"النشر يجب أن يكون يدويًا فقط، المشغلات: {keys}"


def test_workflow_name_not_selected_as_ci_reference():
    _, data, _ = _load()
    assert "CI" not in str(data.get("name", "")), "اسم ملف النشر يحوي CI — سيلتقطه اختيار التشغيل المرجعي"


def test_token_only_from_secrets_no_literal():
    text, _, _ = _load()
    assert "secrets.FLY_API_TOKEN" in text, "الرمز يجب أن يأتي من secrets.FLY_API_TOKEN"
    prefix = "Fly" + "V1 "
    macaroon = "fm" + "2_"
    assert prefix not in text and macaroon not in text, "رمز Fly حرفي داخل ملف النشر"


def test_token_permissions_restricted():
    _, data, _ = _load()
    perms = data.get("permissions")
    assert perms == {"contents": "read", "actions": "read"}, f"صلاحيات غير مقيدة: {perms}"


def test_requires_green_ci_on_same_sha():
    text, _, _ = _load()
    assert "gh run list" in text and "github.sha" in text and "success" in text, \
        "لا توجد بوابة CI ناجح على نفس SHA قبل النشر"


def test_targets_fly_toml_app_and_checks_health():
    text, _, _ = _load()
    app = _fly_app_name()
    assert f"-a {app}" in text or f"--app {app}" in text, f"النشر لا يستهدف تطبيق fly.toml ({app})"
    assert "/health" in text, "لا فحص /health بعد النشر"


def test_starts_stopped_machines_after_deploy():
    """R-718: سجل النشر الفاشل أثبت أن flyctl deploy يحدّث الآلة ويتركها stopped
    (d891e26ea24d38 «reached stopped state») — خطوة صريحة تبدأ الآلات المتوقفة
    قبل فحص الدخان، وإلا بقي التطبيق بلا سجل DNS وفشل الفحص دومًا."""
    text, _, _ = _load()
    assert "flyctl machine start" in text, \
        "لا توجد خطوة تشغيل الآلات المتوقفة بعد النشر (دليل R-718 — الآلة انتهت stopped)"


def test_resumes_suspended_app_before_starting_machines():
    """R-718 (تكملة): بدء الآلة وحده لم يكفِ — الآلة بدأت (سجل التشغيل 39749764649:
    «d891e26ea24d38 has been started») وبقي التطبيق بلا سجل DNS بعد 8 دقائق.
    تطبيق suspended (حالة موثقة في R-717) لا يُخدم حتى يُستأنف.
    التشغيل الثالث (39752410556) أثبت أن `flyctl apps resume` مهجور في flyctl 0.4.120
    («Command resume is deprecated, use fly scale count instead») — الخطوة تستخدم
    الأمر البديل الحديث `flyctl scale count` المشروط بقراءة الحالة قبل بدء الآلات."""
    text, _, _ = _load()
    assert "flyctl scale count" in text, \
        "لا توجد خطوة استئناف التطبيق المعلق بالأمر الحديث (دليل التشغيلين 39749764649 و39752410556)"
    assert "flyctl apps resume" not in text, \
        "flyctl apps resume مهجور في flyctl 0.4.120 — فشل به في التشغيل 39752410556"""


# -------------------------
# R-718 (السبب الجذري الثالث) + R-719 — توسعة الحارس
# -------------------------

def test_ensure_public_ips_step_present():
    """R-718: تطبيق بلا IPv4 عام لا ينشر سجل fly.dev (مجتمع Fly — الحل
    allocate-v4 --shared). الحارس يثبت وجود خطوة تقرأ ips list وتخصص عند
    الغياب — لا افتراض أن العنوان موجود."""
    text, _, _ = _load()
    assert "flyctl ips list" in text, "خطوة ضمان عناوين IP العامة يجب أن تقرأ ips list"
    assert "flyctl ips allocate-v4 --shared" in text, (
        "الخطوة يجب أن تخصص IPv4 مشترك عند غيابه (جذر سجل fly.dev DNS)"
    )


def test_supabase_secrets_sync_step_conditional():
    """R-719 (بأمر المالك: Supabase قرص المشروع وذاكرته): خطوة مزامنة أسرار
    Supabase إلى Fly — مشروطة بوجودهما في أسرار المستودع (تخطي صامت عند
    الغياب — الطبقة تبقى معطلة افتراضيًا، لا فشل للنشر)."""
    text, _, _ = _load()
    assert "secrets.SUPABASE_URL" in text and "secrets.SUPABASE_SECRET_KEY" in text, (
        "الأسرار يجب أن تأتي من secrets.SUPABASE_URL/SUPABASE_SECRET_KEY"
    )
    assert "flyctl secrets set" in text, "المزامنة عبر flyctl secrets set"
    # مشروطة: فحص فراغ قبل المزامنة (لا فشل نشر عند غياب الأسرار)
    assert re.search(r'\[ -z "\$SUPABASE_URL" \]', text), (
        "المزامنة يجب أن تتخطى عند غياب الأسرار (الطبقة معطلة افتراضيًا)"
    )


def test_smoke_window_covers_dns_ttl():
    """R-718: فحص الدخان كان ينتظر 3 دقائق فقط — سجل fly.dev الجديد يحتاج
    وقت نشر DNS (TTL 5 دقائق وفق توثيق Fly). النافذة يجب أن تغطي ≥ 10 دقائق."""
    text, _, _ = _load()
    m = re.search(r"for i in \$\(seq 1 (\d+)\); do", text)
    assert m, "حلقة فحص الدخان (seq) غير موجودة"
    attempts = int(m.group(1))
    m2 = re.search(r"sleep (\d+)", text)
    assert m2, "مهلة النوم داخل الحلقة غير موجودة"
    window = attempts * int(m2.group(1))
    assert window >= 600, (
        f"نافذة الفحص {window}s قصيرة — DNS TTL لسجل fly.dev يصل 300s؛ المطلوب ≥ 600s"
    )


def test_ips_read_failure_not_treated_as_absence():
    """R-721 (تصويبي — مراجعة): فشل قراءة ips list ليس دليل غياب العناوين —
    `|| echo "[]"` يحوّل فشل القراءة إلى تخصيص أعمى. يجب ألا يكون في الملف."""
    text, _, _ = _load()
    assert "|| echo \"[]\"" not in text, (
        "فشل قراءة ips list يجب ألا يعامل كغياب عناوين (تخصيص أعمى)"
    )
