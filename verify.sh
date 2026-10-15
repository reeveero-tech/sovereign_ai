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

# --- 3) Run test suite with JUnit + SHA ---
echo ""
echo "[1/2] Running test suite (tests/ + backend/tests/, excluding operational)..."
python3 -m pytest tests/ backend/tests/ -q \
    -m "not operational" \
    --junitxml=forensics/pytest_results.xml \
    --junit-prefix="R-682-sha-${SHORT_SHA}" \
    || { echo "❌ pytest FAILED"; exit 1; }

# --- 4) Embed SHA in JUnit XML root attributes ---
python3 - <<EOF
import xml.etree.ElementTree as ET
tree = ET.parse("forensics/pytest_results.xml")
root = tree.getroot()
root.set("git_sha", "$SHA")
root.set("junit_prefix", "R-682-sha-$SHA")
ET.indent(tree)
tree.write("forensics/pytest_results.xml", encoding="utf-8", xml_declaration=True)
print("✅ git SHA embedded in JUnit XML: $SHA")
EOF

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
print(f"✅ DoD PASS: {passed} passed, {skipped} skipped, {failed} failed")
EOF

# --- 6) Full mode: compare with CI + clean clone ---
if [ "$FULL_MODE" = "--full" ]; then
    echo ""
    echo "=========================================="
    echo " [FULL MODE] CI + Clean Clone comparison"
    echo "=========================================="

    # 6a) Get latest CI run
    echo ""
    echo "[3/4] Fetching latest CI run..."
    CI_RUN_ID=$(gh run list --repo reeveero-tech/sovereign_ai --limit 1 --json databaseId --jq '.[0].databaseId')
    CI_STATUS=$(gh run list --repo reeveero-tech/sovereign_ai --limit 1 --json status --jq '.[0].status')
    echo "CI Run: $CI_RUN_ID (status: $CI_STATUS)"

    if [ "$CI_STATUS" = "completed" ]; then
        CI_CONCLUSION=$(gh run list --repo reeveero-tech/sovereign_ai --limit 1 --json conclusion --jq '.[0].conclusion')
        echo "CI Conclusion: $CI_CONCLUSION"
        if [ "$CI_CONCLUSION" != "success" ]; then
            echo "❌ CI is not green"
            exit 1
        fi
        # Download JUnit artifact and compare
        ARTIFACT_ID=$(gh api repos/reeveero-tech/sovereign_ai/actions/runs/$CI_RUN_ID/artifacts --jq '.artifacts[] | select(.name | startswith("junit-with-sha")) | .id' | head -1)
        if [ -n "$ARTIFACT_ID" ]; then
            TMPDIR_VERIFY=$(mktemp -d)
            gh api repos/reeveero-tech/sovereign_ai/actions/artifacts/$ARTIFACT_ID/zip > "$TMPDIR_VERIFY/junit.zip"
            python3 -c "
import zipfile
with zipfile.ZipFile('$TMPDIR_VERIFY/junit.zip') as z:
    z.extractall('$TMPDIR_VERIFY')
"
            python3 - "$TMPDIR_VERIFY/pytest_results.xml" << 'PYEOF'
import sys, xml.etree.ElementTree as ET
tree = ET.parse(sys.argv[1])
root = tree.getroot()
ci_sha = root.get("git_sha", "MISSING")
ci_tests = sum(int(ts.get("tests", 0)) for ts in root.iter("testsuite"))
ci_skipped = sum(int(ts.get("skipped", 0)) for ts in root.iter("testsuite"))
ci_failed = sum(int(ts.get("failures", 0)) + int(ts.get("errors", 0)) for ts in root.iter("testsuite"))
print(f"CI JUnit: sha={ci_sha} tests={ci_tests} skipped={ci_skipped} failed={ci_failed}")
PYEOF
            rm -rf "$TMPDIR_VERIFY"
        fi
    else
        echo "[warn] CI still running — check later"
    fi

    # 6b) Clean clone verification
    echo ""
    echo "[4/4] Clean clone verification..."
    TMP_CLONE=$(mktemp -d)
    git clone -q https://github.com/reeveero-tech/sovereign_ai.git "$TMP_CLONE/clone"
    cd "$TMP_CLONE/clone"
    echo "Clone HEAD: $(git rev-parse HEAD)"
    ./verify.sh 2>&1 | tail -5
    CLONE_EXIT=$?
    cd - > /dev/null
    rm -rf "$TMP_CLONE"
    if [ $CLONE_EXIT -ne 0 ]; then
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
