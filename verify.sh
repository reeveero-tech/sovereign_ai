#!/usr/bin/env bash
# R-682 (Task 4.2): One-command reproduction of all numbers.
# Usage: ./verify.sh [--ci]
#
# Produces:
#   1. Local run: pytest tests/ backend/tests/ -m "not operational"
#   2. JUnit XML with git SHA embedded
#   3. Zero-skips verification (DoD hard requirement)
#
# Exit code: 0 = all checks pass, 1 = any failure

set -euo pipefail

echo "=========================================="
echo " R-682 Verification Script"
echo "=========================================="

# --- 1) Capture SHA ---
SHA=$(git rev-parse HEAD)
SHORT_SHA=$(git rev-parse --short HEAD)
echo "HEAD: $SHA"

# --- 2) Ensure data/key.secret exists (local; CI generates it) ---
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

# --- 6) Summary ---
echo ""
echo "=========================================="
echo " VERIFICATION COMPLETE"
echo " HEAD: $SHA"
echo " JUnit: forensics/pytest_results.xml (git_sha embedded)"
echo "=========================================="
