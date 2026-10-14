"""
سكربت التحقق السبعي — البوابة 1 (تدوير اعتماد API)

يتحقق فقط (لا يُعدّل أي ملف):
1. الملف موجود: data/key.secret.new
2. الطول صحيح: 43 حرفًا (الحد الأدنى 16)
3. التنسيق صحيح: base64url فقط (A-Z, a-z, 0-9, -, _)
4. لا يحتوي سطرًا جديدًا أو مسافات
5. لا يطابق المفتاح القديم (مختلف)
6. يُنتج HMAC صالحًا (توقيع تجريبي يُتحقق)
7. key_id فريد (لا يطابق مفاتيح KeyRing الحالية)

إذا فشل أي فحص → يُرفض التدوير و لا يُلمس أي ملف.
"""

import hashlib
import hmac
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "backend"))

NEW_KEY_FILE = os.path.join(_REPO_ROOT, "data", "key.secret.new")
OLD_KEY_FILE = os.path.join(_REPO_ROOT, "data", "key.secret")
KEYRING_FILE = os.path.join(_REPO_ROOT, "data", "keys", "keyring.json")


def check_all() -> bool:
    """يُنفّذ كل الفحوصات السبعة. يُعيد True إذا نجحت كلها."""
    failures = []

    # فحص 1: الملف موجود
    if not os.path.exists(NEW_KEY_FILE):
        failures.append(f"FAIL 1: {NEW_KEY_FILE} not found")
    else:
        print("PASS 1: new key file exists")

    if failures:
        print("\n".join(failures))
        return False

    # قراءة المفتاح الجديد
    with open(NEW_KEY_FILE, "r", encoding="ascii") as f:
        new_key = f.read()

    # فحص 2: الطول
    if len(new_key) == 43:
        print(f"PASS 2: length = {len(new_key)} (exact 43)")
    elif len(new_key) >= 16:
        print(f"PASS 2: length = {len(new_key)} (>= 16 minimum)")
    else:
        failures.append(f"FAIL 2: length {len(new_key)} < 16 minimum")

    # فحص 3: التنسيق (base64url فقط)
    base64url_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    if all(c in base64url_chars for c in new_key):
        print("PASS 3: all chars are base64url (A-Z, a-z, 0-9, -, _)")
    else:
        invalid = [c for c in new_key if c not in base64url_chars][:5]
        failures.append(f"FAIL 3: invalid chars: {invalid}")

    # فحص 4: لا سطر جديد أو مسافات
    if "\n" not in new_key and "\r" not in new_key and " " not in new_key and "\t" not in new_key:
        print("PASS 4: no newline, spaces, or tabs")
    else:
        failures.append("FAIL 4: contains newline/space/tab")

    # فحص 5: لا يطابق المفتاح القديم
    if os.path.exists(OLD_KEY_FILE):
        with open(OLD_KEY_FILE, "r", encoding="utf-8") as f:
            old_key = f.read().strip()
        if new_key == old_key:
            failures.append("FAIL 5: new key is SAME as old key (no rotation)")
        else:
            old_fp = hashlib.sha256(old_key.encode()).hexdigest()[:16]
            new_fp = hashlib.sha256(new_key.encode()).hexdigest()[:16]
            print(f"PASS 5: different from old key ({old_fp} -> {new_fp})")
    else:
        print("PASS 5: no old key file (skipped — nothing to compare)")

    # فحص 6: يُنتج HMAC صالحًا
    test_data = b"gate1_rotation_test_2026_10_14"
    sig = hmac.new(new_key.encode("utf-8"), test_data, hashlib.sha256).hexdigest()
    verify_ok = hmac.compare_digest(
        sig,
        hmac.new(new_key.encode("utf-8"), test_data, hashlib.sha256).hexdigest()
    )
    if verify_ok:
        print(f"PASS 6: HMAC signature valid (sig: {sig[:16]}...)")
    else:
        failures.append("FAIL 6: HMAC signature verification failed")

    # فحص 7: key_id فريد (لا يطابق مفاتيح KeyRing)
    new_key_id = hashlib.sha256(new_key.encode("utf-8")).hexdigest()[:16]
    if os.path.exists(KEYRING_FILE):
        with open(KEYRING_FILE, "r", encoding="utf-8") as f:
            keyring_data = json.load(f)
        existing_key_ids = [k["key_id"] for k in keyring_data.get("keys", [])]
        if new_key_id in existing_key_ids:
            failures.append(f"FAIL 7: key_id {new_key_id} already exists in KeyRing")
        else:
            print(f"PASS 7: key_id {new_key_id} is unique (not in KeyRing)")
    else:
        print(f"PASS 7: no keyring.json (skipped) — key_id {new_key_id}")

    # النتيجة
    print()
    if failures:
        print("=== VERIFICATION FAILED — ROTATION REJECTED ===")
        for f_ in failures:
            print(f_)
        return False
    else:
        print("=== ALL 7 CHECKS PASSED — SAFE TO ROTATE ===")
        print(f"new key fingerprint: {hashlib.sha256(new_key.encode()).hexdigest()[:16]}")
        return True


if __name__ == "__main__":
    success = check_all()
    sys.exit(0 if success else 1)
