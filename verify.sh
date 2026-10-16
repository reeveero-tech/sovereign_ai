#!/usr/bin/env bash
# R-682 (Task 4.2): One-command reproduction of all numbers.
# Usage: ./verify.sh [--full]
#
# Default (local only):
#   ./verify.sh
#   → Runs pytest, generates JUnit with SHA, verifies zero skips.
#
# Full (local + CI + clean clone comparison):
#   ./verify.sh --full
#   → Local run + CI run comparison + clean clone run.
#
# Exit code: 0 = all checks pass, 1 = any failure

set -euo pipefail

FULL_MODE="${1:-}"

# --- 0) R-682 (البند ١٢): بوابة إصدار Python — 3.11.x فقط، كل الأنماط، بلا علم تجاوز ---
PY_GATE=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [ "$PY_GATE" != "3.11" ]; then
    echo "❌ [بوابة الإصدار] Python $PY_GATE مكتشف — هذا المشروع يتطلب Python 3.11.x (بيئة CI المعلنة)."
    echo "   البند ١٢ من جولة R-682: ترفض البوابة أي Python آخر في كل الأنماط — لا علم تجاوز."
    python3 -VV || true
    exit 1
fi
echo "✅ [بوابة الإصدار] Python $PY_GATE — مقبول (3.11.x)"

echo "=========================================="
echo " R-682 Verification Script"
echo "=========================================="

# --- 1) Capture SHA ---
SHA=$(git rev-parse HEAD)
SHORT_SHA=$(git rev-parse --short HEAD)
echo "HEAD: $SHA"

# --- 2) Ensure data/key.secret exists ---
if [ ! -f data/key.secret ]; then
    mkdir -p data
    python3 -c "import secrets; print(secrets.token_urlsafe(32))" > data/key.secret
    chmod 600 data/key.secret
    echo "[info] Generated ephemeral data/key.secret (not committed)"
fi

# --- 3) Run test suite via the TRUSTED gate wrapper (unified path) ---
# (تصويب المراجع — الجولة 4: المسار الموحد — الغلاف نفسه يلتقط بصمة
# المحتوى قبل التشغيل، يشغل الأمر الفعلي نفسه (بادئة SHA حقيقية)،
# يقارن بعد التشغيل، ويختم بالبصمة الملتقطة حرفيًا — لا يُلحق تقرير
# قديم ببصمة جديدة — ويوثق الفعل كاملًا عبر run_logged في build_actions)
echo ""
echo "[1/2] Running test suite via tools/run_gate.py (actual command, sealed identity)..."
python3 tools/run_gate.py || { echo "❌ gate FAILED"; exit 1; }

# --- 5) Verify zero skips (DoD) ---
echo ""
echo "[2/2] Verifying zero skips (DoD hard requirement)..."
python3 - <<'EOF'
import xml.etree.ElementTree as ET
tree = ET.parse("forensics/pytest_results.xml")
root = tree.getroot()
skipped = sum(int(ts.get("skipped", 0)) for ts in root.iter("testsuite"))
failed = sum(int(ts.get("failures", 0)) + int(ts.get("errors", 0)) for ts in root.iter("testsuite"))
passed = sum(int(ts.get("tests", 0)) - skipped - failed for ts in root.iter("testsuite"))
if skipped != 0:
    print(f"❌ DoD violated: {skipped} skipped tests found — must be 0")
    for tc in root.iter("testcase"):
        if tc.find("skipped") is not None:
            s = tc.find("skipped")
            print(f"   SKIPPED: {tc.get('classname')}.{tc.get('name')}: {s.get('message')}")
    raise SystemExit(1)
if failed != 0:
    print(f"❌ {failed} test failures/errors — must be 0")
    raise SystemExit(1)
print(f"✅ بوابة الاختبارات ناجحة: {passed} passed, {skipped} skipped, {failed} failed")
EOF

# --- 6) Full mode: compare with CI + clean clone ---
if [ "$FULL_MODE" = "--full" ]; then
    echo ""
    echo "=========================================="
    echo " [FULL MODE] CI + Clean Clone comparison"
    echo "=========================================="

    # 6a) Find CI run for THIS EXACT SHA — عبر وحدة الاختيار المشتركة القابلة
    # للاختبار (tests/ci_run_selection.py): اختيار صريح اختياري يمنع الانتقاء
    # الذاتي، والافتراضي يفضل تشغيل push للـ SHA، مع فحص هوية workflow ci.yml.
    echo ""
    echo "[3/4] Fetching CI run for HEAD SHA=$SHORT_SHA..."
    CI_RUNS=$(gh run list --repo reeveero-tech/sovereign_ai --limit 50 --json databaseId,headSha,status,conclusion,event,workflowName)
    if ! CI_RUN_ID=$(echo "$CI_RUNS" | python3 tests/ci_run_selection.py --sha "$SHA" ${CI_RUN_ID:+--explicit "$CI_RUN_ID"}); then
        echo "❌ CI run selection failed"
        exit 1
    fi

    # 6a-2) الفحوص الحتمية: مكتمل + ناجح + من workflow ci.yml (نفس الوحدة المشتركة)
    if ! echo "$CI_RUNS" | python3 tests/ci_run_selection.py --sha "$SHA" --explicit "$CI_RUN_ID" --require-completed > /dev/null; then
        exit 1
    fi
    echo "CI Run: $CI_RUN_ID (completed/success — اختيار صريح + فحص هوية workflow)"

    # 6b) Download JUnit artifact and COMPARE with local
    ARTIFACT_ID=$(gh api repos/reeveero-tech/sovereign_ai/actions/runs/$CI_RUN_ID/artifacts --jq '.artifacts[] | select(.name | startswith("junit-with-sha")) | .id' | head -1)
    if [ -z "$ARTIFACT_ID" ]; then
        echo "❌ No junit-with-sha artifact found for CI run $CI_RUN_ID"
        exit 1
    fi

    TMPDIR_VERIFY=$(mktemp -d)
    gh api repos/reeveero-tech/sovereign_ai/actions/artifacts/$ARTIFACT_ID/zip > "$TMPDIR_VERIFY/junit.zip" || {
        echo "❌ Failed to download artifact $ARTIFACT_ID"
        rm -rf "$TMPDIR_VERIFY"; exit 1
    }
    python3 -c "
import zipfile
with zipfile.ZipFile('$TMPDIR_VERIFY/junit.zip') as z:
    z.extractall('$TMPDIR_VERIFY')
" || { echo "❌ Failed to extract artifact"; rm -rf "$TMPDIR_VERIFY"; exit 1; }

    # Compare local vs CI (SHA + test counts + per-testcase identity)
    python3 - "$TMPDIR_VERIFY/pytest_results.xml" "forensics/pytest_results.xml" << 'PYEOF'
import sys, xml.etree.ElementTree as ET

ci_tree = ET.parse(sys.argv[1])
local_tree = ET.parse(sys.argv[2])
ci_root = ci_tree.getroot()
local_root = local_tree.getroot()

def stats(root):
    tests = sum(int(ts.get("tests", 0)) for ts in root.iter("testsuite"))
    failed = sum(int(ts.get("failures", 0)) + int(ts.get("errors", 0)) for ts in root.iter("testsuite"))
    skipped = sum(int(ts.get("skipped", 0)) for ts in root.iter("testsuite"))
    return tests, failed, skipped

# Compare (normalized_classname, name) — classname contains junit_prefix which differs by environment.
# Strip ONLY the junit_prefix from the head of classname — keep module + class intact.
from collections import Counter
import re
def test_ids(root):
    ids = Counter()
    prefix = root.get("junit_prefix", "")
    for tc in root.iter("testcase"):
        cls = tc.get("classname", "")
        name = tc.get("name", "")
        if prefix and cls.startswith(prefix + "."):
            cls = cls[len(prefix) + 1:]
        ids[(cls, name)] += 1
    return ids

ci_sha = ci_root.get("git_sha", "MISSING")
ci_tests, ci_failed, ci_skipped = stats(ci_root)
ci_ids = test_ids(ci_root)
local_sha = local_root.get("git_sha", "MISSING")
local_tests, local_failed, local_skipped = stats(local_root)
local_ids = test_ids(local_root)

print(f"CI:     sha={ci_sha[:12]}... tests={ci_tests} failed={ci_failed} skipped={ci_skipped} unique_ids={len(ci_ids)}")
print(f"Local:  sha={local_sha[:12]}... tests={local_tests} failed={local_failed} skipped={local_skipped} unique_ids={len(local_ids)}")

errors = []
if ci_sha != local_sha:
    errors.append(f"SHA mismatch: CI={ci_sha} vs Local={local_sha}")
if ci_sha == "MISSING" or local_sha == "MISSING":
    errors.append("git_sha missing in JUnit")
if ci_tests != local_tests:
    errors.append(f"Test count mismatch: CI={ci_tests} vs Local={local_tests}")
if ci_ids != local_ids:
    only_ci = (ci_ids - local_ids).most_common(5)
    only_local = (local_ids - ci_ids).most_common(5)
    errors.append(f"Testcase identity mismatch (normalized_classname,name): only_in_CI={only_ci} only_local={only_local}")
if ci_failed != 0 or local_failed != 0:
    errors.append(f"Failures: CI={ci_failed} Local={local_failed} (must be 0)")
if ci_skipped != 0 or local_skipped != 0:
    errors.append(f"Skipped: CI={ci_skipped} Local={local_skipped} (must be 0)")

if errors:
    for e in errors:
        print(f"❌ {e}")
    sys.exit(1)
print("✅ CI + Local MATCH (SHA + test counts + (normalized_classname,name) Counter + zero failures + zero skips)")
PYEOF
    COMPARE_EXIT=$?
    rm -rf "$TMPDIR_VERIFY"
    if [ $COMPARE_EXIT -ne 0 ]; then
        echo "❌ CI vs Local comparison FAILED"
        exit 1
    fi

    # 6c) Clean clone verification (pinned via git checkout to EXACT SHA)
    echo ""
    echo "[4/4] Clean clone verification (git checkout pinned to SHA=$SHORT_SHA)..."
    LOCAL_JUNIT_ABS="$PWD/forensics/pytest_results.xml"
    TMP_CLONE=$(mktemp -d)
    git clone -q https://github.com/reeveero-tech/sovereign_ai.git "$TMP_CLONE/clone"
    cd "$TMP_CLONE/clone"
    git checkout -q "$SHA"
    CLONE_SHA=$(git rev-parse HEAD)
    if [ "$CLONE_SHA" != "$SHA" ]; then
        echo "❌ Clone checkout HEAD ($CLONE_SHA) != Local HEAD ($SHA)"
        cd - > /dev/null; rm -rf "$TMP_CLONE"; exit 1
    fi
    CLONE_JUNIT=$(mktemp -d)/pytest_results.xml
    # R-682 (advisor final): clone needs ephemeral key.secret — same as verify.sh step 2
    if [ ! -f data/key.secret ]; then
        mkdir -p data
        python3 -c "import secrets; print(secrets.token_urlsafe(32))" > data/key.secret
        chmod 600 data/key.secret
        echo "[info] Generated ephemeral data/key.secret in clone (not committed)"
    fi
    timeout 900 python3 -m pytest tests/ backend/tests/ -q -m "not operational" \
        --junitxml="$CLONE_JUNIT" \
        --junit-prefix="R-682-sha-${SHA}" 2>&1 | tail -5
    CLONE_EXIT=$?
    if [ $CLONE_EXIT -ne 0 ]; then
        echo "❌ Clean clone test run FAILED"
        cd - > /dev/null; rm -rf "$TMP_CLONE"; exit 1
    fi
    # Embed SHA into clone JUnit
    python3 -c "
import xml.etree.ElementTree as ET
import sys
sha = '$SHA'
tree = ET.parse('$CLONE_JUNIT')
root = tree.getroot()
root.set('git_sha', sha)
root.set('junit_prefix', f'R-682-sha-{sha}')
ET.indent(tree)
tree.write('$CLONE_JUNIT', encoding='utf-8', xml_declaration=True)
print('✅ SHA embedded in clone JUnit:', sha)
"
    # Compare clone JUnit vs local JUnit (use LOCAL_JUNIT_ABS — not path inside clone)
    python3 - "$CLONE_JUNIT" "$LOCAL_JUNIT_ABS" << 'PYEOF2'
import sys, xml.etree.ElementTree as ET
from collections import Counter
clone_tree = ET.parse(sys.argv[1])
local_tree = ET.parse(sys.argv[2])
clone_root = clone_tree.getroot()
local_root = local_tree.getroot()
def stats(root):
    tests = sum(int(ts.get("tests", 0)) for ts in root.iter("testsuite"))
    failed = sum(int(ts.get("failures", 0)) + int(ts.get("errors", 0)) for ts in root.iter("testsuite"))
    skipped = sum(int(ts.get("skipped", 0)) for ts in root.iter("testsuite"))
    return tests, failed, skipped
def test_ids(root):
    ids = Counter()
    prefix = root.get("junit_prefix", "")
    for tc in root.iter("testcase"):
        cls = tc.get("classname", "")
        name = tc.get("name", "")
        if prefix and cls.startswith(prefix + "."):
            cls = cls[len(prefix) + 1:]
        ids[(cls, name)] += 1
    return ids
c_t, c_f, c_s = stats(clone_root); c_ids = test_ids(clone_root)
l_t, l_f, l_s = stats(local_root); l_ids = test_ids(local_root)
print(f"Clone:  tests={c_t} failed={c_f} skipped={c_s} unique_ids={len(c_ids)}")
print(f"Local:  tests={l_t} failed={l_f} skipped={l_s} unique_ids={len(l_ids)}")
if c_t != l_t or c_f != l_f or c_s != l_s or c_ids != l_ids:
    only_clone = (c_ids - l_ids).most_common(5)
    only_local = (l_ids - c_ids).most_common(5)
    print(f"❌ Clone vs Local JUnit mismatch. only_clone={only_clone} only_local={only_local}")
    sys.exit(1)
print("✅ Clean clone JUnit MATCHES Local (count + (normalized_classname,name) Counter + zero failures + zero skips)")
PYEOF2
    CLONE_COMPARE=$?
    cd - > /dev/null
    rm -rf "$TMP_CLONE"
    if [ $CLONE_COMPARE -ne 0 ]; then
        echo "❌ Clean clone verification failed"
        exit 1
    fi
fi

# --- 7) Summary ---
echo ""
echo "=========================================="
echo " VERIFICATION COMPLETE"
echo " HEAD: $SHA"
echo " JUnit: forensics/pytest_results.xml (git_sha embedded)"
echo " Mode: ${FULL_MODE:-local-only}"
echo "=========================================="
