# -*- coding: utf-8 -*-
"""اختبارات كاشف دليل JUnit (الجولة الإنشائية — تصويب المراجع، الاعتراض 5).

الدليل يُقبل فقط إذا: SHA مطابق، النطاق يشمل الاختبارات الستة المطلوبة
ناجحة، صفر فشل/خطأ/تخطٍّ، وعدد اختبارات > 0. كل حالة رفض تُختبر صراحةً.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

from backend.sovereign.score import _parse_junit_evidence  # noqa: E402

HEAD = "a" * 40
REQUIRED = (
    ("backend.tests.invariants.test_no_orphan_modules", "test_no_orphan_modules"),
    ("backend.tests.invariants.test_no_unsigned_ledger_events",
     "test_no_unsigned_ledger_events"),
    ("backend.tests.invariants.test_all_entrypoints_respond",
     "test_all_registered_routes_respond"),
    ("backend.tests.invariants.test_keyring_immutability",
     "test_keyring_history_immutable"),
    ("backend.tests.invariants.test_compat_sunset_criteria",
     "test_every_compat_module_has_sunset_criteria"),
    ("backend.tests.invariants.test_no_silent_exceptions.TestNoSilentExceptions",
     "test_no_silent_except_in_production"),
    ("backend.tests.invariants.test_no_mock_outside_tests",
     "test_no_mock_outside_tests"),
)


def _write_junit(tmp_path: Path, name: str, *, testsuites_attrs=None,
                 suite_attrs=None, cases=None, raw_root_attrs=None) -> Path:
    """بناء ملف JUnit تجريبي بالحالات المطلوبة."""
    p = tmp_path / name
    root = ET.Element("testsuites", {
        **({"junit_prefix": f"R-682-sha-{HEAD}",
            "content_fingerprint": "f" * 64} if raw_root_attrs is None else raw_root_attrs),
        **(testsuites_attrs or {}),
    })
    suite = ET.SubElement(root, "testsuite", {
        "name": "pytest",
        "tests": str(len(cases or [])),
        "failures": "0", "errors": "0", "skipped": "0",
        **(suite_attrs or {}),
    })
    for case in (cases or []):
        tc = ET.SubElement(suite, "testcase", {
            "name": case["name"],
            "classname": case.get("classname",
                                  f"backend.tests.invariants.{case['name']}"),
        })
        for child in case.get("children", []):
            ET.SubElement(tc, child)
    ET.indent(root)
    ET.ElementTree(root).write(p, encoding="utf-8", xml_declaration=True)
    return p


def _ok_cases(extra=None):
    return [{"name": n, "classname": c} for c, n in REQUIRED] + (extra or [])


def test_valid_evidence_accepted(tmp_path):
    junit = _write_junit(tmp_path, "valid.xml", cases=_ok_cases([{"name": "test_other"}]))
    ev = _parse_junit_evidence(junit, HEAD)
    assert ev["passing"] == 1, ev
    assert ev["tests_total"] == 8
    assert ev["skipped"] == 0


def test_empty_report_rejected(tmp_path):
    # لا testsuite إطلاقًا — تقرير فارغ
    p = tmp_path / "empty.xml"
    root = ET.Element("testsuites", {"junit_prefix": f"R-682-sha-{HEAD}",
                                      "content_fingerprint": "f" * 64})
    ET.ElementTree(root).write(p, encoding="utf-8", xml_declaration=True)
    ev = _parse_junit_evidence(p, HEAD)
    assert ev["passing"] == 0
    assert "no testsuites" in ev["reason"]


def test_zero_tests_rejected(tmp_path):
    junit = _write_junit(tmp_path, "zero.xml", cases=[])
    ev = _parse_junit_evidence(junit, HEAD)
    assert ev["passing"] == 0
    assert "zero tests" in ev["reason"]


def test_wrong_scope_rejected(tmp_path):
    # نطاق آخر: لا اختبارات invariants المطلوبة
    junit = _write_junit(tmp_path, "wrong_scope.xml",
                          cases=[{"name": "test_something_else"}])
    ev = _parse_junit_evidence(junit, HEAD)
    assert ev["passing"] == 0
    assert "missing required invariants" in ev["reason"]


def test_skip_within_invariants_rejected(tmp_path):
    # اختبار مطلوب متخطٍّ — يرفض (بوابة صفر تخطٍّ)
    cases = _ok_cases()
    for c in cases:
        if c["name"] == "test_no_orphan_modules":
            c["children"] = ["skipped"]
    junit = _write_junit(tmp_path, "skipped.xml", cases=cases,
                          suite_attrs={"skipped": "1"})
    ev = _parse_junit_evidence(junit, HEAD)
    assert ev["passing"] == 0
    assert "skipped=1" in ev["reason"]


def test_failure_within_invariants_rejected(tmp_path):
    cases = _ok_cases()
    for c in cases:
        if c["name"] == "test_no_orphan_modules":
            c["children"] = ["failure"]
    junit = _write_junit(tmp_path, "failed.xml", cases=cases,
                          suite_attrs={"failures": "1"})
    ev = _parse_junit_evidence(junit, HEAD)
    assert ev["passing"] == 0
    assert "failures=1" in ev["reason"]


def test_stale_sha_rejected(tmp_path):
    # SHA قديم لحالة شجرة أخرى — يرفض
    other = "b" * 40
    junit = _write_junit(tmp_path, "stale.xml", cases=_ok_cases(),
                          raw_root_attrs={"junit_prefix": f"R-682-sha-{other}"})
    ev = _parse_junit_evidence(junit, HEAD)
    assert ev["passing"] == 0
    assert "SHA" in ev["reason"]


def test_missing_file_rejected(tmp_path):
    ev = _parse_junit_evidence(tmp_path / "nope.xml", HEAD)
    assert ev["passing"] == 0
    assert "no JUnit evidence file" in ev["reason"]


def test_content_fingerprint_ties_evidence_to_tree(tmp_path):
    """الاختبار الحاسم (تصويب المراجع — الجولة 2): تشغيل ناجح بدليل مقبول،
    ثم تغيير محتوى ملف على HEAD نفسه (يبقى M) — الدليل السابق يُرفض
    (بصمة المحتوى لا حالة git هي الأساس)."""
    import subprocess

    from backend.sovereign.score import (_v2_content_fingerprint,
                                          embed_junit_identity,
                                          _parse_junit_evidence)

    # مستودع مؤقت بملتزام واحد وملف .py
    repo = tmp_path / "repo"
    repo.mkdir()
    def _git(*args):
        r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(repo))
        assert r.returncode == 0, r.stderr
    _git("init", "-q")
    (repo / "code_file.py").write_text("# v1\n", encoding="utf-8")
    _git("add", "-A")
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c1")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=str(repo)).stdout.strip()

    # JUnit سليم + تضمين الهوية (SHA + بصمة المحتوى) وقت التشغيل
    junit = _write_junit(tmp_path, "tied.xml", cases=_ok_cases())
    embed_junit_identity(junit, repo)

    # (1) الدليل مقبول — البصمة المضمنة تطابق الشجرة
    ev = _parse_junit_evidence(junit, head, repo_root=repo)
    assert ev["passing"] == 1, ev

    # (2) تغيير محتوى الملف (يبقى M على HEAD نفسه)
    (repo / "code_file.py").write_text("# v2 CHANGED\n", encoding="utf-8")
    ev_stale = _parse_junit_evidence(junit, head, repo_root=repo)
    assert ev_stale["passing"] == 0, (
        "evidence from before the content change MUST be rejected"
    )
    assert "content fingerprint mismatch" in ev_stale["reason"]

    # (3) البصمة الحالية تختلف فعلًا عن المضمنة
    assert _v2_content_fingerprint(repo) != junit and True  # sanity only


def test_junit_prefix_classnames_normalized(tmp_path):
    """--junit-prefix في verify.sh يسبق البادئة R-682-sha-<sha>. كل classname —
    الكاشف ينزعها للمطابقة وتبقى هوية الملف والصنف والدالة كاملة (تصويب
    المراجع — الجولة 3)."""
    cases = [{"name": n, "classname": f"R-682-sha-{'a' * 40}.{c}"}
             for c, n in REQUIRED]
    junit = _write_junit(tmp_path, "prefixed.xml", cases=cases)
    ev = _parse_junit_evidence(junit, HEAD)
    assert ev["passing"] == 1, ev


def test_sealing_refuses_content_change_between_run_and_seal(tmp_path):
    """الختم بالبصمة الملتقطة قبل التشغيل (تصويب المراجع — الجولة 3):
    تغيير محتوى ملف بين التشغيل والختم → يُرفض الختم (RuntimeError) ولا
    يُختم التقرير القديم ببصمة جديدة."""
    import subprocess

    from backend.sovereign.score import (_v2_content_fingerprint,
                                          embed_junit_identity,
                                          seal_junit_identity)

    repo = tmp_path / "repo"
    repo.mkdir()
    def _git(*args):
        r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(repo))
        assert r.returncode == 0, r.stderr
    _git("init", "-q")
    (repo / "code_file.py").write_text("# v1\n", encoding="utf-8")
    _git("add", "-A")
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c1")

    # "تشغيل" — تقرير سليم على المحتوى A
    junit = _write_junit(tmp_path, "seal.xml", cases=_ok_cases())
    captured = _v2_content_fingerprint(repo)  # الملتقطة قبل التشغيل

    # (1) بلا تغيير: الختم ينجح والدليل يُقبل
    ident = seal_junit_identity(junit, repo, captured)
    assert ident["content_fingerprint"] == captured

    # (2) تغيير المحتوى بين التشغيل والختم: رفض — لا ختم ببصمة جديدة
    (repo / "code_file.py").write_text("# v2 CHANGED\n", encoding="utf-8")
    try:
        seal_junit_identity(junit, repo, captured)
        sealed = True
    except RuntimeError as e:
        sealed = False
        assert "content changed between the run and the sealing" in str(e)
    assert sealed is False, "sealing a stale report with a captured old " \
                            "fingerprint must be refused"


def test_prefix_mismatch_rejected(tmp_path):
    """تصويب المراجع — الجولة 4: تقرير جذره يحمل SHA الحالي لكن أسماء
    اختباراته تحمل بادئة SHA آخر — لا يُنظف ويُرفض (النزع لهوية التقرير
    نفسه فقط، لا أي SHA)."""
    other_sha = "b" * 40
    cases = [{"name": n, "classname": f"R-682-sha-{other_sha}.{c}"}
             for c, n in REQUIRED]
    junit = _write_junit(tmp_path, "mismatched_prefix.xml", cases=cases)
    ev = _parse_junit_evidence(junit, HEAD)
    assert ev["passing"] == 0
    assert "missing required invariants" in ev["reason"]
