# R-752 — خزينة الأسرار (ROADMAP_V5 ١.٥)

> بأمر المالك 2026-10-25: «أسلمك المشروع ابدء ولا تتوقف إلى بعد تحقيق الهدف».

## ما بُني
- `backend/sovereign/secrets_vault.py` — `SecretsVault`:
  - **تشفير مصادَق حقيقي AES-256-GCM** (pycryptodome، nonce عشوائي ١٢ بايت لكل كتابة).
  - المفتاح الرئيسي من البيئة `SOVEREIGN_VAULT_MASTER_KEY` (٣٢ بايت base64) بيد المالك — لا يُكتب في المستودع. غيابه أو ضعفه → الخزينة معطلة (`VaultDisabled`، fail-closed).
  - مفتاحا البيانات والبصمة مشتقان منفصلين عبر HKDF-SHA256.
  - **AAD = الاسم + النطاقات + الإصدار**: توسيع النطاق بتعديل الملف يكسر التحقق (`VaultIntegrityError`).
  - حصر نطاقي: `get(name, capability)` يرفض أي قدرة خارج النطاق (`ScopeDenied`) والرفض نفسه مُدقق.
  - تدوير بإصدار متزايد؛ القيمة القديمة لا تبقى في الملف.
  - **تدقيق إلزامي قبل الأثر**: كل فعل (put/get/rotate/delete/denied/get_missing) يمر بدالة تدقيق؛ في الخزينة الحية هي `append_event("vault_access", …)` في السجل السيادي الموقّع — فشلها (مثل حارس R-635 بلا مفتاح توقيع) يرفض الفعل ولا يغير الملف.
  - تنقية: `redact()` و`log_filter()` تستبدلان القيم المعروفة بـ`[secret:name:fingerprint]`.
  - الكتابة ذرية (ملف مؤقت + `os.replace`) بصلاحية 0600.
- `EventType.VAULT_ACCESS` في `backend/memory/core.py`.
- `/vault/status` وأداة السجل `vault.status` في `backend/app.py` (بصمات وبيانات وصفية فقط).
- الجرد: `secrets_vault` صار مرتبطًا بعلم `vault` (= مفتاح رئيسي صالح) + مفتاح التوقيع.
- `.gitignore`: `data/vault/`.

## الدليل
- RED: `forensics/R-752_evidence_RED.txt` (13 failed — قبل وجود الوحدة).
- GREEN: `tests/test_secrets_vault.py` 15/15 (13 + اختبار ربط السجل الحي + اختبار مستويات الجرد).

## الحالة الصادقة
- محليًا وفي الإنتاج الآن: لا مفتاح رئيسي ولا مفتاح توقيع → الجرد يعلن `implemented_disabled` (لا `enabled`).
- التمكين الحي = المالك يضبط `SOVEREIGN_VAULT_MASTER_KEY` كسر بيئة + إغلاق ١.٣ + النشر (١.٧).
- لا نقاط HTTP للكتابة بعد — الكتابة عبر الكود (الموصلات في §٤ ستستهلك `get` بنطاقها).

## فجوة مكتشفة (١.٥-ب — تُسجل لا تُغلق)
`encrypt` في `backend/memory/encoding.py` و`_encrypt_seal` في `backend/consciousness/identity_core.py` تستخدمان XOR بمفتاح مكرر — ليس تشفيرًا. لم تُستخدما في الخزينة.
