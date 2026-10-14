"""
سكربت تشغيلي — R-655: التحقق من الختم و الاعتماد (عملية منفصلة)

يُشغّل في عملية Python جديدة (دون monkeypatch أو reload) و يتحقق من:
1. الاعتماد الفعّال (data/key.secret) — المفتاح الجديد
2. المصادقة الفعلية (المفتاح الجديد 200، القديم 403)
3. مسار ختم الهوية (يُتبّع التعريف الفعلي من الكود)
4. فك تشفير الختم (بالمفتاح الحالي و القديم و الاختباري)

R-655: الفشل = فشل (لا نجاح زائف).
"""

import hashlib
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

# إلغاء متغيرات البيئة الاختبارية
os.environ.pop("SOVEREIGN_KEY", None)
os.environ.pop("SOVEREIGN_DATA_ROOT", None)
os.chdir(_REPO_ROOT)


def _fp(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def check_all() -> bool:
    failures = []
    print("=" * 60)
    print("R-655: OPERATIONAL VERIFICATION (separate process)")
    print("=" * 60)

    # 1) الاعتماد الفعّال
    print("\n--- 1) Effective credential ---")
    new_key_path = _REPO_ROOT / "data" / "key.secret"
    old_key_path = _REPO_ROOT / "data" / "key.secret.old_rotated_2026_10_14"

    if new_key_path.exists():
        new_key = new_key_path.read_text().strip()
        print(f"PASS: data/key.secret exists (fp={_fp(new_key)})")
    else:
        failures.append("FAIL: data/key.secret missing")

    if old_key_path.exists():
        old_key = old_key_path.read_text().strip()
        print(f"PASS: old key backup exists (fp={_fp(old_key)})")
    else:
        failures.append("FAIL: old key backup missing")

    # 2) المصادقة الفعلية (subprocess — لكن نحن بالفعل في subprocess)
    print("\n--- 2) Actual authentication ---")
    try:
        from fastapi.testclient import TestClient
        import app as app_module

        client = TestClient(app_module.app)
        r_new = client.get("/api-key", params={"master_key": new_key})
        r_old = client.get("/api-key", params={"master_key": old_key})

        if r_new.status_code == 200:
            print(f"PASS: new key accepted (200)")
        else:
            failures.append(
                f"FAIL: new key rejected (status={r_new.status_code}): {r_new.text[:100]}"
            )

        if r_old.status_code == 403:
            print(f"PASS: old key rejected (403)")
        else:
            failures.append(
                f"FAIL: old key accepted (status={r_old.status_code}) — MUST be 403"
            )

        # لا تسريب
        if new_key not in r_new.text and new_key[:10] not in r_new.text:
            print("PASS: response does not leak key material")
        else:
            failures.append("FAIL: response leaks key material")
    except Exception as e:
        failures.append(f"FAIL: auth test exception: {e}")

    # 3) مسار ختم الهوية (من التعريف الفعلي)
    print("\n--- 3) Identity seal path (from code) ---")
    try:
        from backend.consciousness import identity_core

        seal_file = identity_core.IDENTITY_SEAL_FILE
        if seal_file.exists():
            print(f"PASS: seal file exists at actual path: {seal_file}")
        else:
            failures.append(f"FAIL: seal file missing at: {seal_file}")
    except Exception as e:
        failures.append(f"FAIL: identity_core import error: {e}")

    # 4) فك تشفير الختم
    print("\n--- 4) Seal decryption ---")
    try:
        if seal_file.exists():
            encrypted = seal_file.read_bytes()

            # بالمفتاح الحالي (الجديد)
            key_new = hashlib.sha3_256(new_key.encode()).digest()
            dec_new = bytes(
                a ^ b for a, b in zip(encrypted, key_new * (len(encrypted) // 32 + 1))
            )
            try:
                seal_new = json.loads(dec_new)
                print(f"PASS: seal decrypts with CURRENT key (new)")
                print(f"     seal_id={seal_new.get('id')}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                # ليس بالمفتاح الحالي — جرب القديم
                key_old = hashlib.sha3_256(old_key.encode()).digest()
                dec_old = bytes(
                    a ^ b
                    for a, b in zip(encrypted, key_old * (len(encrypted) // 32 + 1))
                )
                try:
                    seal_old = json.loads(dec_old)
                    print(
                        f"WARN: seal decrypts with OLD key (not current) — "
                        f"needs re-encryption with new key"
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # ليس القديم — جرب الاختباري
                    test_key = "test_master_key_1234567890abcdef"
                    key_test = hashlib.sha3_256(test_key.encode()).digest()
                    dec_test = bytes(
                        a ^ b
                        for a, b in zip(
                            encrypted, key_test * (len(encrypted) // 32 + 1)
                        )
                    )
                    try:
                        seal_test = json.loads(dec_test)
                        print(
                            f"FAIL: seal decrypts with TEST key (conftest) — "
                            f"DATA POLLUTION from tests"
                        )
                        failures.append(
                            "FAIL: identity_seal.bin encrypted with TEST key "
                            "(conftest pollution) — not production key"
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        failures.append(
                            "FAIL: seal cannot be decrypted with any known key"
                        )
    except Exception as e:
        failures.append(f"FAIL: seal decryption error: {e}")

    # النتيجة
    print("\n" + "=" * 60)
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return False
    else:
        print("ALL CHECKS PASSED")
        return True


if __name__ == "__main__":
    ok = check_all()
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
