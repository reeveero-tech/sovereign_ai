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
