"""
R-682 (Task 3.1): Synthetic ledger fixture for ledger-dependent tests.

Creates a small, signed, tamper-free ledger.jsonl + ledger.anchors.jsonl
so that invariant tests can run in a clean clone WITHOUT requiring the
45MB runtime ledger. This unblocks the 4 ledger-related skips.

Event format (from backend/sovereign/keys/verifier.py):
    extract_event_data = f"{hash}|{prev_hash}|{blob}|{time}|{type}|{key_id}"
    signature = HMAC-SHA256(private_key, event_data)

Usage (pytest fixture):
    @pytest.fixture
    def synthetic_ledger(tmp_path):
        return build_synthetic_ledger(tmp_path)

Test-the-test: feed a tampered event → verification MUST fail.
"""

import hashlib
import hmac
import json
import sys
import time as _time
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.sovereign.keys import KeyRing, SignatureVerifier, VerificationStatus
from backend.sovereign.ledger import LedgerAnchor


def _sign_event(event: Dict, private_key: str) -> Dict:
    """Sign an event dict in-place (same logic as verifier._compute_signature)."""
    event_data = (
        f"{event['hash']}|{event['prev_hash']}|{event['blob']}|"
        f"{event['time']}|{event['type']}|{event.get('key_id', '')}"
    )
    sig = hmac.new(private_key.encode("utf-8"), event_data.encode("utf-8"),
                  hashlib.sha256).hexdigest()
    event["signature"] = sig
    return event


def build_synthetic_ledger(base_dir: Path, event_count: int = 10,
                           reuse_existing: bool = False) -> Dict[str, Path]:
    """
    Build a synthetic ledger.jsonl + ledger.anchors.jsonl in base_dir.

    Returns {"ledger": Path, "anchors": Path, "keys_dir": Path, "keyring": KeyRing,
             "private_key": str, "key_id": str}

    (الجولة الإنشائية — تصويب المراجع الاعتراض 8: reuse_existing — إن وُجدت
    بنية سابقة كاملة في نفس الجذر تُعاد كما هي (لا إعادة بناء تمسح عبثًا
    مُحقونًا) — يستخدمه إثبات RED الذي يشغل الحارس على بيانات مُعبث بها.)
    """
    ledger_file = base_dir / "sovereign_core" / "ledger.jsonl"
    anchors_file = base_dir / "sovereign_core" / "ledger.anchors.jsonl"
    keys_dir = base_dir / "keys"
    marker = base_dir / ".synthetic_built"
    if (reuse_existing and ledger_file.exists() and anchors_file.exists()
            and marker.exists()):
        return {
            "ledger": ledger_file,
            "anchors": anchors_file,
            "keys_dir": keys_dir,
            "keyring": None,
            "private_key": None,
            "key_id": None,
        }
    ledger_dir = base_dir / "sovereign_core"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    keys_dir = base_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)

    # 1) KeyRing with one active key
    keyring = KeyRing(keys_dir=keys_dir)
    keyring.generate_new_key(reason="synthetic-fixture-r682")
    keyring.save_to_disk()
    active = keyring.get_active_key()
    assert active is not None and active.private_key is not None, \
        "fixture: no active key with private_key"
    private_key = active.private_key
    key_id = active.key_id

    # 2) Signed events (matches memory/core.py + verifier.py format)
    events: List[Dict] = []
    prev_hash = "0" * 64
    for i in range(event_count):
        payload = json.dumps({"seq": i, "fixture": True, "ts": 1792020000 + i},
                             sort_keys=True)
        ev = {
            "id": f"evt-{i:04d}",
            "type": "attention::snapshot",
            "time": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(1792020000 + i)),
            "prev_hash": prev_hash,
            "blob": hashlib.sha256(payload.encode()).hexdigest(),
            "key_id": key_id,
        }
        ev["hash"] = hashlib.sha256(
            f"{ev['prev_hash']}|{ev['blob']}|{ev['time']}|{ev['type']}".encode()
        ).hexdigest()
        _sign_event(ev, private_key)
        prev_hash = ev["hash"]
        events.append(ev)

    ledger_path = ledger_dir / "ledger.jsonl"
    with open(ledger_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # 3) Anchor covering all events (uses ACTUAL line strings as stored)
    # R-682: merkle root must be computed from the RAW line strings (not reserialized JSON).
    from backend.sovereign.ledger.anchor import compute_merkle_root
    raw_lines = [json.dumps(ev, ensure_ascii=False) for ev in events]
    merkle_root = compute_merkle_root(raw_lines)

    # R-682 (advisor): anchor must be v2 (sig_format + sig_data_v2 + signature)
    # so test_all_anchors_valid exercises the v2 signature branch.
    sig_data_v2 = (
        f"anchor_sig_v2|0|{event_count - 1}|{event_count}|"
        f"{merkle_root}|{key_id}"
    )
    anchor_signature = hmac.new(
        private_key.encode("utf-8"),
        sig_data_v2.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    anchor_record = {
        "anchor_id": hashlib.sha256(merkle_root.encode()).hexdigest()[:16],
        "batch_start": 0,
        "batch_end": event_count - 1,
        "event_count": event_count,
        "merkle_root": merkle_root,
        "reason": "SYNTHETIC_FIXTURE_R682",
        "key_id": key_id,
        "anchored_at": "2026-10-15T00:00:00Z",
        # R-682: v2 fields (matches anchor.py:246-248)
        "sig_format": "v2",
        "sig_data_v2": sig_data_v2,
        "signature": anchor_signature,
    }
    anchors_path = ledger_dir / "ledger.anchors.jsonl"
    with open(anchors_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(anchor_record, ensure_ascii=False) + "\n")

    (base_dir / ".synthetic_built").write_text("built", encoding="utf-8")
    return {
        "ledger": ledger_path,
        "anchors": anchors_path,
        "keys_dir": keys_dir,
        "keyring": keyring,
        "private_key": private_key,
        "key_id": key_id,
    }


def verify_fixture(ledger_path: Path, anchors_path: Path, keys_dir: Path) -> Dict:
    """
    Run the same verification logic as the invariant tests, against a fixture.
    Returns {"all_valid": bool, "invalid_events": [...], "root_verified": bool}
    """
    keyring = KeyRing(keys_dir=keys_dir)
    keyring.load_from_disk()
    verifier = SignatureVerifier(keyring)

    lines = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                lines.append(line.rstrip("\n"))

    invalid_events = []
    for i, line in enumerate(lines):
        try:
            event = json.loads(line)
        except Exception:
            invalid_events.append((i, "invalid_json"))
            continue
        res = verifier.verify_event(event)
        if res.status == VerificationStatus.INVALID:
            invalid_events.append((i, "INVALID (tampered)"))
        elif res.status not in (VerificationStatus.VERIFIED,
                                VerificationStatus.UNVERIFIABLE_MISSING_KEY):
            invalid_events.append((i, f"unknown_status:{res.status}"))

    anchor = LedgerAnchor(ledger_path=ledger_path, anchors_path=anchors_path)
    anchors = anchor.list_anchors()
    root_ok = bool(anchors) and all(
        anchor.verify_anchor_detailed(a, keyring=keyring)["root_verified"]
        for a in anchors
    )

    return {
        "all_valid": len(invalid_events) == 0,
        "invalid_events": invalid_events,
        "root_verified": root_ok,
    }


# NOTE: Test-the-test functions were moved to tests/test_synthetic_fixture.py
# (R-682 advisor fix: fixtures/ is not collected by pytest by default).
