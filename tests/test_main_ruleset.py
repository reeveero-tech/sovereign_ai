"""R-773 — القاعدة الحاكمة مفروضة على الخادم: لا دفع إلى main إلا بالتزام اجتاز بوابة الوثائق.

قبل R-773: البوابة (D-040) في CI تُفشل الدفعة المخالفة **بعد** دخولها main (الحماية من الدفع
نفسه كانت معلنة غير متحققة في V5 ١.١)، وحارس pre-commit محلي يُتجاوز بـ`--no-verify`.
المالك: «لا دفع إلى المستودع … إلا بتوثيق … العمل يدفع وفي نفس الدفعة يدفع التوثيق».

الآن: قاعدة GitHub على main (`tools/github/main_ruleset.json`، تطبيقها
`tools/github/apply_main_ruleset.sh`) تشترط نجاح فحص `Tests + Atomic Batch Gate` على
الالتزام نفسه قبل تحديث main — بلا مستثنين — وتمنع force-push والحذف (المادة الثالثة).
فالمسار: دفع إلى `work/<البند>` → CI أخضر على SHA → دفع SHA نفسه إلى main (تقديم سريع).
وفرع العمل الجديد يُفحص التزامًا التزامًا من نقطة افتراقه عن main، لا رأسه وحده.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CI = ROOT / ".github" / "workflows" / "ci.yml"
RULESET = ROOT / "tools" / "github" / "main_ruleset.json"


def _ci():
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def _gate_job_name():
    return _ci()["jobs"]["test"]["name"]


def test_ruleset_requires_the_gate_job_on_main_without_bypass():
    rs = json.loads(RULESET.read_text(encoding="utf-8"))
    assert rs["enforcement"] == "active"
    assert rs["bypass_actors"] == []
    assert rs["conditions"]["ref_name"]["include"] == ["refs/heads/main"]
    types = {r["type"]: r for r in rs["rules"]}
    assert {"deletion", "non_fast_forward", "required_status_checks"} <= set(types)
    checks = types["required_status_checks"]["parameters"]["required_status_checks"]
    assert [c["context"] for c in checks] == [_gate_job_name()]


def test_ci_runs_on_work_branches_so_main_can_require_it():
    on = _ci().get("on") or _ci().get(True)  # PyYAML يقرأ on كـ True
    assert "work/**" in on["push"]["branches"]
    assert "main" in on["push"]["branches"]


def test_new_branch_push_checks_every_commit_since_fork_point():
    text = CI.read_text(encoding="utf-8")
    for gate in ("tools/gate_deletions.py", "tools/gate_docs_sync.py"):
        assert f'python {gate} --range "${{BASE}}" "${{GITHUB_SHA}}"' in text, gate
    assert text.count('git merge-base origin/main "${GITHUB_SHA}"') == 2


def test_apply_script_reads_the_single_spec():
    sh = (ROOT / "tools" / "github" / "apply_main_ruleset.sh").read_text(encoding="utf-8")
    assert "main_ruleset.json" in sh and "rulesets" in sh
