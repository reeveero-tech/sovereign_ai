"""
اختبار البوابة 1: تدوير اعتماد API

يختبر أن:
1. المفتاح الجديد يُقبل (مسار التطبيق الفعلي: /api-key مع data/key.secret)
2. المفتاح القديم يُرفض
3. مفاتيح خاطئة تُرفض
4. بصمات مختلفة (قديم ≠ جديد)
5. التشغيل الفعلي: config.py يُحمّل المفتاح الجديد (وليس القديم)

B-1 (2026-10-20، أمر المالك — إصلاح الاختبارات الزائفة الأربعة من
EXHAUSTIVE_AUDIT_2026-10-20 البنود ١ و٢ و٥ و٦):
- test_new_key_accepted: كانت `assert new_key == new_key` (مقارنة ذاتية) —
  صارت مسار تطبيق فعلي (TestClient على التطبيق الحقيقي في عملية معزولة).
- test_config_loads_new_key_in_subprocess: فشل العملية الفرعية كان يتحول إلى
  pytest.skip (قناع أخضر) — صار فشلًا صريحًا برسالة تفصيلية تحوي stderr.
- test_old_key_rejected_via_app_auth_path: كانت تقارن مفاتيح عشوائية ولا
  تستدعي أي كود تطبيق — صارت تطلب /api-key فعليًا وتتحقق من 403 للمفتاح
  القديم مع ضابط إيجابي (200 للمفتاح الجديد) في العملية نفسها.
- test_old_key_rejected_via_real_auth_path: كتلة «الضابط» كانت تحسب نتيجة
  بلا assert (كود ميت) — صارت ضابطًا فعليًا يثبت أن الرفض من بوابة توقيع
  HMAC (تسجيل جلسة الرمز القديم في المحرك الجديد ثم إثبات استمرار الرفض).
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import secrets as _secrets

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest


# R-682 (Task 3.2): synthetic key-secret fixture — replaces runtime data dependency.
@pytest.fixture
def synthetic_keys(tmp_path):
    """Create a synthetic key.secret + old_rotated backup in tmp_path."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    new_key = _secrets.token_urlsafe(32)
    old_key = _secrets.token_urlsafe(32)  # different random key
    (data_dir / "key.secret").write_text(new_key)
    (data_dir / "key.secret.old_rotated_2026_10_14").write_text(old_key)
    os.chmod(data_dir / "key.secret", 0o600)  # وضع 0600 إلزامي (config يرفض/يحذر دونها)
    return {"new_key": new_key, "old_key": old_key, "data_dir": data_dir}


def _run_app_auth_subprocess(data_dir: Path, new_key: str, old_key: str):
    """مسار المصادقة الحقيقي للتطبيق في عملية معزولة — نبضتان في تشغيل واحد.

    يشغّل التطبيق الفعلي (from app import app) مع جذر بيانات معزول يحوي
    key.secret الاصطناعي، ثم يطلب /api-key مرتين عبر TestClient: بالمفتاح
    الجديد وبالمفتاح القديم. يعيد (رمز الخروج، stdout، stderr) — stdout
    يحمل الأسطر STATUS_NEW / STATUS_OLD / BODY_NEW / BODY_OLD.

    TestClient بلا context-manager (بلا lifespan): النقطة /api-key لا تحتاج
    المنسق — الاستدعاء الحقيقي لـ verify_api_key + config يكفي ولا يلوث
    شيئًا (كل شيء في العملية المعزولة وجذرها المؤقت).
    """
    script = f"""
import sys, os
sys.path.insert(0, {str(_REPO_ROOT)!r})
sys.path.insert(0, {str(_REPO_ROOT / 'backend')!r})
os.environ['SOVEREIGN_DATA_ROOT'] = {str(data_dir)!r}
os.environ.pop('SOVEREIGN_KEY', None)
os.environ['SOVEREIGN_DISABLE_BACKGROUND_THREADS'] = '1'
from app import app
from fastapi.testclient import TestClient
client = TestClient(app)
r_new = client.get('/api-key', headers={{'X-API-Key': {new_key!r}}})
r_old = client.get('/api-key', headers={{'X-API-Key': {old_key!r}}})
print('STATUS_NEW:', r_new.status_code)
print('STATUS_OLD:', r_old.status_code)
print('BODY_NEW:', r_new.text)
print('BODY_OLD:', r_old.text)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True,
        cwd=str(_REPO_ROOT),
        timeout=300,
    )
    return result.returncode, result.stdout, result.stderr


class TestAPIKeyRotation:
    """اختبارات البوابة 1 (تدوير اعتماد API).

    B-1 (2026-10-20): لا اختبار في هذه الفئة يتخطى عند فشل المسار — الفشل
    فشل صريح. الاعتماد على data/key.secret الاصطناعي (لا سر التشغيل الحقيقي).
    """

    def _load_key_from_file(self, path: Path) -> str:
        """يقرأ المفتاح من ملف (دون استخدام config.py المخزّن)."""
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def test_new_key_accepted(self, synthetic_keys):
        """المفتاح الجديد يُقبل عبر مسار المصادقة الفعلي للتطبيق (200).

        B-1 (بند ١ من التدقيق): النسخة السابقة كانت `assert new_key ==
        new_key` — مقارنة القيمة بنفسها لا تختبر شيئًا. الآن: التطبيق
        الفعلي في عملية معزولة + طلب /api-key بالمفتاح الجديد من الملف
        الاصطناعي — القبول يعني 200 + بصمة المفتاح + المصدر key.secret.
        """
        rc, out, err = _run_app_auth_subprocess(
            synthetic_keys["data_dir"],
            synthetic_keys["new_key"],
            synthetic_keys["old_key"],
        )
        assert rc == 0, (
            f"مسار التطبيق الفعلي فشل (فشل صريح لا تخطي): {err[:500]}"
        )
        assert "STATUS_NEW: 200" in out, (
            "المفتاح الجديد (من key.secret) يجب أن يُقبل عبر /api-key — "
            f"الاستجابة الفعلية:\n{out[-800:]}\nstderr:{err[:300]}"
        )
        expected_fp = hashlib.sha256(
            synthetic_keys["new_key"].encode()
        ).hexdigest()[:16]
        compact = out.replace(" ", "")
        assert f'"fingerprint":"{expected_fp}"' in compact, (
            f"بصمة الاستجابة يجب أن تطابق بصمة المفتاح الجديد {expected_fp} — "
            f"الاستجابة:\n{out[-500:]}"
        )
        assert '"source":"key.secret"' in compact, (
            "المصدر يجب أن يكون key.secret — يثبت أن التطبيق حمّل المفتاح "
            f"من الملف لا من مصدر آخر. الاستجابة:\n{out[-500:]}"
        )

    def test_old_key_rejected_via_real_auth_path(self, synthetic_keys, monkeypatch):
        """المفتاح القديم يُرفض عبر مسار المصادقة الفعلي (AuthEngine).

        R-682 (advisor + Task 3.2): Uses REAL auth code path + control test.
        Control: if HMAC is disabled, this test MUST FAIL (proves it tests HMAC).
        """
        try:
            from nexus.user_management.auth_engine import AuthEngine
        except ImportError:
            pytest.fail("nexus.user_management must be importable (advisor: no skip)")

        new_engine = AuthEngine(secret=synthetic_keys["new_key"])
        old_engine = AuthEngine(secret=synthetic_keys["old_key"])

        # Token signed with OLD key → must be REJECTED by NEW engine
        old_token = old_engine.create_token(user_id="u1", username="test", role="admin")
        result = new_engine.verify_token(old_token)
        assert result is None, "token signed with OLD key must be REJECTED"

        # Control: token from NEW engine verifies with NEW engine
        new_token = new_engine.create_token(user_id="u1", username="test", role="admin")
        assert new_engine.verify_token(new_token) is not None, "new key must be accepted"

        # CONTROL (B-1 بند ٦ — إعادة كتابة كتلة كانت كودًا ميتًا بلا assert):
        # إثبات أن الرفض أعلاه سببه بوابة توقيع HMAC تحديدًا لا بحث الجلسة —
        # نسجّل جلسة الرمز القديم في المحرك الجديد: لو كان بحث الجلسة وحده
        # سبب الرفض لَقُبل الرمز؛ استمرار الرفض مع وجود الجلسة وصلاحيتها
        # يثبت أن البوابة الفعلية هي مطابقة التوقيع.
        import base64 as _b64
        import json as _json
        decoded = _b64.urlsafe_b64decode(old_token.encode()).decode()
        old_payload = _json.loads(decoded.rsplit(".", 1)[0])
        old_session = old_engine.sessions[old_payload["sid"]]
        assert not old_session.is_expired, "عين الضابط: جلسة الرمز القديم ما زالت صالحة"
        new_engine.sessions[old_payload["sid"]] = old_session
        result_with_session_present = new_engine.verify_token(old_token)
        assert result_with_session_present is None, (
            "رمز المفتاح القديم يجب أن يُرفض حتى مع وجود جلسته في المحرك "
            "الجديد — يثبت أن الرفض من بوابة توقيع HMAC لا من بحث الجلسة"
        )

    def test_app_auth_path_loads_key_from_secret_file(self, synthetic_keys):
        """مسار التطبيق الأصلي: config.py يُحمّل المفتاح من data/key.secret.

        This is the REAL gate1 path — proves the app's actual auth code
        loads the key from the secret file (not just AuthEngine).
        """
        import subprocess
        import os

        # Write new key to temp data dir with key.secret
        data_dir = synthetic_keys["data_dir"]
        assert (data_dir / "key.secret").exists(), "fixture must create key.secret"

        # Run the app's actual key loader in a subprocess (no pollution)
        repo_root_str = str(_REPO_ROOT)
        backend_str = str(_REPO_ROOT / "backend")
        data_dir_str = str(data_dir)
        key_file_str = str(data_dir / "key.secret")
        script = f"""
import sys, os

sys.path.insert(0, {repo_root_str!r})
sys.path.insert(0, {backend_str!r})
os.chdir({repo_root_str!r})
os.environ['SOVEREIGN_DATA_ROOT'] = {data_dir_str!r}
os.environ.pop('SOVEREIGN_KEY', None)
from backend.config import load_sovereign_key
key = load_sovereign_key()
assert key, "load_sovereign_key must return a key"
with open({key_file_str!r}) as f:
    expected = f.read().strip()
assert key == expected, f"app must load key from fixture key.secret: got {{key[:8]}}... vs {{expected[:8]}}..."
print(f"APP_KEY_LOADED: {{key[:8]}}...")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True,
            cwd=str(_REPO_ROOT),
        )
        assert "APP_KEY_LOADED" in result.stdout, (
            f"app auth path failed: {result.stderr[:300]}"
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr[:200]}"

    def test_old_key_rejected_via_app_auth_path(self, synthetic_keys):
        """المفتاح القديم يُرفض عبر مسار التطبيق الفعلي — 403 من /api-key.

        B-1 (بند ٥ من التدقيق): النسخة السابقة كانت تقارن مفاتيح عشوائية
        مختلفة (`old_key != new_key`) ولا تستدعي أي كود تطبيق. الآن: طلبان
        فعليان إلى /api-key على التطبيق الحقيقي في العملية نفسها — القديم
        403 والجديد 200 (الضابط الإيجابي يثبت أن الرفض سببه المفتاح لا
        تعطل المسار).
        """
        rc, out, err = _run_app_auth_subprocess(
            synthetic_keys["data_dir"],
            synthetic_keys["new_key"],
            synthetic_keys["old_key"],
        )
        assert rc == 0, (
            f"مسار التطبيق الفعلي فشل (فشل صريح لا تخطي): {err[:500]}"
        )
        assert "STATUS_OLD: 403" in out, (
            "المفتاح القديم يجب أن يُرفض (403) عبر /api-key على التطبيق "
            f"الفعلي — الاستجابة الفعلية:\n{out[-800:]}\nstderr:{err[:300]}"
        )
        assert "STATUS_NEW: 200" in out, (
            "ضابط إيجابي في العملية نفسها: المفتاح الجديد يجب أن يُقبل (200) "
            "وإلا فالرفض أعلاه قد يكون لتعطل المسار لا للمفتاح — "
            f"الاستجابة:\n{out[-800:]}"
        )

    def test_fingerprints_different(self, synthetic_keys):
        """بصمات المفتاحين مختلفة.

        R-682 (Task 3.2): uses synthetic fixture.
        """
        new_key = synthetic_keys["new_key"]
        old_key = synthetic_keys["old_key"]
        old_fp = hashlib.sha256(old_key.encode()).hexdigest()[:16]
        new_fp = hashlib.sha256(new_key.encode()).hexdigest()[:16]
        assert old_fp != new_fp

    def test_config_loads_new_key_in_subprocess(self):
        """التشغيل الفعلي: config.py يُحمّل المفتاح الجديد في عملية Python جديدة.

        R-650: يُلغي SOVEREIGN_KEY (المفتاح الاختباري من conftest.py) —
        حتى يُحمّل config.py من data/key.secret (المسار الفعلي).

        B-1 (بند ٢ من التدقيق): فشل العملية الفرعية كان يتحول إلى pytest.skip
        — قناع أخضر يخفي الانكسار الحقيقي في التشغيل اليدوي. الآن فشل
        صريح برسالة تفصيلية تحوي stderr كاملًا قدر الإمكان.
        """
        script = (
            "import sys, os; "
            f"sys.path.insert(0, {str(_REPO_ROOT / 'backend')!r}); "
            "os.chdir({root!r}); "
            "from config import SOVEREIGN_KEY, SOVEREIGN_KEY_FINGERPRINT; "
            "print(SOVEREIGN_KEY_FINGERPRINT)"
        ).format(root=str(_REPO_ROOT))

        # R-650: إلغاء SOVEREIGN_KEY و SOVEREIGN_DATA_ROOT (المفتاح الاختباري و
        # الجذر المعزول) — حتى يُحمّل config.py من data/key.secret الحقيقي
        env = os.environ.copy()
        env.pop("SOVEREIGN_KEY", None)
        env.pop("SOVEREIGN_DATA_ROOT", None)

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env=env,
        )

        # B-1 (بند ٢): فشل العملية الفرعية = فشل الاختبار صراحة — لا تخطي.
        # التخطي كان يخفي الانكسار الحقيقي (مثال واقعي: بيئة إنتاج بلا مفتاح
        # تفشل مغلقة — يجب أن يظهر الفشل لا أن يختفي).
        assert result.returncode == 0, (
            "فشلت عملية تحميل config.py الفرعية — فشل حقيقي لا تخطي "
            "(B-1 بند ٢: رفع قناع التخطي). stderr الكامل:\n"
            f"{result.stderr[-1000:]}"
        )

        loaded_fp = result.stdout.strip()
        # المفتاح الجديد (من data/key.secret)
        new_key = self._load_key_from_file(_REPO_ROOT / "data" / "key.secret")
        expected_fp = hashlib.sha256(new_key.encode()).hexdigest()[:16]
        assert loaded_fp == expected_fp, (
            f"config.py must load NEW key fingerprint {expected_fp}, got {loaded_fp}"
        )

    def test_rotation_receipt_exists(self):
        """إيصال التدوير موجود و صالح."""
        receipt_path = _REPO_ROOT / "credentials" / "ROTATION_RECEIPT.json"
        if not receipt_path.exists():
            pytest.skip("rotation receipt not yet created")
        import json
        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)
        assert "old_key_fingerprint" in receipt
        assert "new_key_fingerprint" in receipt
        assert receipt["old_key_fingerprint"] != receipt["new_key_fingerprint"]
