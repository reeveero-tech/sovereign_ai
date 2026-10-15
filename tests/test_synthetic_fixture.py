"""
R-682 (advisor): Test-the-test for synthetic ledger fixture.

Moved from tests/fixtures/synthetic_ledger.py to a proper test_*.py file
so pytest collects it by default (was not collected under fixtures/).

Tests:
1. Fixture builds + verifies (GREEN)
2. Fixture detects event tampering (tamper → INVALID)
3. Fixture detects anchor signature corruption (tamper → sig fails)
4. v2 anchor signature exercises the signature branch
"""

import importlib.util as _ilu
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

_synthetic_path = _REPO_ROOT / "tests" / "fixtures" / "synthetic_ledger.py"
_spec = _ilu.spec_from_file_location("synthetic_ledger", str(_synthetic_path))
_sl = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_sl)
build_synthetic_ledger = _sl.build_synthetic_ledger
verify_fixture = _sl.verify_fixture


@pytest.fixture
def fx(tmp_path):
    return build_synthetic_ledger(tmp_path / "data")


def test_fixture_builds_and_verifies(fx):
    """GREEN: fixture builds + all events verify + anchor root verifies."""
    assert fx["ledger"].exists()
    assert fx["anchors"].exists()
    result = verify_fixture(fx["ledger"], fx["anchors"], fx["keys_dir"])
    assert result["all_valid"], f"invalid events: {result['invalid_events']}"
    assert result["root_verified"]


def test_fixture_anchor_is_v2(fx):
    """Fixture anchor must be sig_format=v2 (exercises v2 signature branch)."""
    with open(fx["anchors"]) as f:
        anchor = json.loads(f.read().strip())
    assert anchor.get("sig_format") == "v2", (
        "fixture anchor must be v2 — v1 anchors skip signature verification"
    )
    assert anchor.get("sig_data_v2", "").startswith("anchor_sig_v2|")
    assert "signature" in anchor


def test_fixture_detects_event_tampering(fx):
    """Tamper one event's blob → verification must flag it."""
    with open(fx["ledger"]) as f:
        lines = f.readlines()
    ev = json.loads(lines[0])
    ev["blob"] = "0" * 64  # tamper
    lines[0] = json.dumps(ev, ensure_ascii=False) + "\n"
    with open(fx["ledger"], "w") as f:
        f.writelines(lines)
    result = verify_fixture(fx["ledger"], fx["anchors"], fx["keys_dir"])
    assert result["invalid_events"], "Tampering NOT detected — fixture broken"


def test_fixture_detects_anchor_signature_corruption(fx):
    """Corrupt the anchor's signature → v2 signature verification must fail."""
    # Load anchor, corrupt signature, write back
    with open(fx["anchors"]) as f:
        anchor = json.loads(f.read().strip())
    anchor["signature"] = "0" * 64  # corrupt
    with open(fx["anchors"], "w") as f:
        f.write(json.dumps(anchor, ensure_ascii=False) + "\n")

    # Verify with the real LedgerAnchor (v2 signature branch)
    from backend.sovereign.ledger import LedgerAnchor
    from backend.sovereign.keys.keyring import KeyRing
    kr = KeyRing(keys_dir=fx["keys_dir"])
    kr.load_from_disk()
    la = LedgerAnchor(ledger_path=fx["ledger"], anchors_path=fx["anchors"])
    anchors = la.list_anchors()
    assert anchors, "no anchors to verify"
    for a in anchors:
        detailed = la.verify_anchor_detailed(a, keyring=kr)
        # Root should still verify (content unchanged)
        assert detailed["root_verified"], "root must still verify"
        # v2 signature must FAIL (corrupted)
        if a.get("sig_format") == "v2":
            assert detailed["signature_verified"] is False, (
                "Corrupted v2 signature must FAIL verification"
            )


def test_fixture_detects_merkle_root_tampering(fx):
    """Corrupt the merkle_root in the anchor → root verification must fail."""
    with open(fx["anchors"]) as f:
        anchor = json.loads(f.read().strip())
    anchor["merkle_root"] = "sha256:" + "f" * 64  # wrong root
    with open(fx["anchors"], "w") as f:
        f.write(json.dumps(anchor, ensure_ascii=False) + "\n")

    from backend.sovereign.ledger import LedgerAnchor
    from backend.sovereign.keys.keyring import KeyRing
    kr = KeyRing(keys_dir=fx["keys_dir"])
    kr.load_from_disk()
    la = LedgerAnchor(ledger_path=fx["ledger"], anchors_path=fx["anchors"])
    anchors = la.list_anchors()
    for a in anchors:
        detailed = la.verify_anchor_detailed(a, keyring=kr)
        assert detailed["root_verified"] is False, (
            "Wrong merkle_root must FAIL root verification"
        )
