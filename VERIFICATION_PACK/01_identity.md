# القسم ١ — هوية المشروع وسياقه (على d56e24e)

الالتزام المرجعي: `d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad` — رأس main. جولة قراءة فقط.

## 1) README كاملًا

- المسار: `README.md` — الالتزام: `75a0b62e29f23ca7ae3c0e20be0f3748307e76c7`

```
# SOVRA · Sovereign Cognitive Operating System

> الاسم الرسمي: **Sovereign AI (SOVRA)** — نظام تشغيل معرفي سيادي (قرار R-202).

هذا المشروع يمثل نواة "ذكاء سيادي" تجريبي، يعمل على:
- GitHub (للكود)
- Railway (للتشغيل)
- Google(للتخزين المشفر)
- جهاز المستخدم (للسيادة الكاملة لاحقاً)

## هيكل المشروع

```
sovereign_ai/
├── backend/          # النواة (FastAPI): app.py, orchestrator.py, api.py, config.py
│   ├── consciousness/  # الوعي
│   ├── memory/         # الذاكرة (core, biological, defense, store)
│   ├── predictive/     # التنبؤ
│   ├── simulation/     # المحاكاة
│   ├── quantum/        # الكم
│   └── sovereign/      # السيادة
├── frontend/         # الواجهة (RTL عربي)
├── docs/             # الوثائق الحاكمة (15 ملفاً)
├── guardian/         # الحارس (أمان/نسخ احتياطي)
├── archive/          # الملفات المؤرشفة
├── nexus/            # منصة منفصلة (NexusCore)
├── main.py           # نقطة تشغيل بديلة
└── data/             # بيانات وقت التشغيل (غير متتبعة)
```
## الهدف
بناء عقل سيادي:
- يتعلم
- يتطور
- يطلب إذن السيد قبل أي تعديل
- يعمل على منصات خارجية مؤقتاً
- ينتقل لاحقاً إلى تشغيل سيادي كامل

---

## 📚 الوثائق الحاكمة (docs/)

هذا المشروع يخضع لقاعدة **الدفعة الذرية**: لا يُدفع/يُدمج أي شيء دون تحديث الحالة والوثائق والخارطة في نفس الدفعة.

- [PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md) — لماذا المشروع؟
- [PROJECT_STATE.md](docs/PROJECT_STATE.md) — أين نحن الآن؟
- [ROADMAP.md](docs/ROADMAP.md) — إلى أين نذهب؟
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — كيف بُني؟
- [GOVERNANCE.md](docs/GOVERNANCE.md) — الحوكمة وقاعدة الدفعة الذرية
- [RISKS.md](docs/RISKS.md) — المخاطر
- [OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) — الأسئلة المفتوحة
- [DECISIONS.md](docs/DECISIONS.md) — القرارات المعمارية
- [API.md](docs/API.md) — الواجهات
- [DATA_MODEL.md](docs/DATA_MODEL.md) — البيانات
- [OPERATIONS.md](docs/OPERATIONS.md) — التشغيل والنشر
- [SECURITY.md](docs/SECURITY.md) — الأمان
- [QUALITY.md](docs/QUALITY.md) — الجودة والاختبارات
- [DOMAIN.md](docs/DOMAIN.md) — منطق العمل
- [CHANGELOG.md](docs/CHANGELOG.md) — سجل التغييرات
```

## 2) وصف المشروع (5 أسطر)

- sovereign_ai نظام ذكاء اصطناعي سيادي شخصي (backend Python + FastAPI) يدير ذاكرة ووعيًا ومحاكاة لنظام واحد.
- المستخدم: مالك واحد (صاحب عمل، السعودية) — لا يوجد مستخدمون آخرون.
- الحساسية: مفاتيح توقيع (KeyRing/تدوير مفاتيح)، سجل أحداث مُوقَّع (ledger + مراسي Merkle)، أسرار في GitHub Actions (KEY_SECRET/KEY_OLD_SECRET) — ليست بيانات عملاء.
- ليس في إنتاج — الحالة: اختبارات وCI وتوثيق جنائي (forensics/) لمرحلة ما قبل الإنتاج.
- القاعدة الحاكمة: قاعدة «لا حذف بلا تدقيق في نفس الالتزام» (DELETED_LINES_AUDIT.md) وسياسة الاختبارات بلا تخطٍّ.

## 3) شجرة المستودع على d56e24e بعمق مستويين

الأمر: `git ls-tree -r --name-only d56e24e | awk -F/ '{if (NF<=2) print}'`

```
.dockerignore
.gitignore
.replit
Dockerfile
README.md
REPORT_V2.md
REPORT_V3.md
ROADMAP_V2.md
audit/dep_map.json
backend/Mr.py
backend/api.py
backend/app.py
backend/config.py
backend/orchestrator.py
backend/rate_limit.py
backend/requirements.txt
backend/safety.py
backend/sovereign_response.py
credentials/ROTATION_RECEIPT.json
docs/API.md
docs/ARCHITECTURE.md
docs/CHANGELOG.md
docs/DATA_MODEL.md
docs/DECISIONS.md
docs/DOMAIN.md
docs/GOVERNANCE.md
docs/KEY_STATE_MACHINE.md
docs/OPEN_QUESTIONS.md
docs/OPERATIONS.md
docs/PROJECT_CHARTER.md
docs/PROJECT_STATE.md
docs/QUALITY.md
docs/RISKS.md
docs/ROADMAP.md
docs/SECURITY.md
fly.toml
forensics/ADVISOR_SESSIONS_DISCLOSURE.md
forensics/AWARENESS_561_DECISION.md
forensics/CONTRACT_EXCEPTION_1.md
forensics/DELETED_LINES_AUDIT.md
forensics/FINAL_CLOSURE_R-682.md
forensics/FINAL_REPORT_R-681.md
forensics/FINAL_REPORT_R-682.md
forensics/FULL_DELETIONS_SWEEP.md
forensics/GITIGNORE_AUDIT.md
forensics/GOAL_DISCOVERY.md
forensics/KEY_LOSS_TIMELINE.md
forensics/LOCAL_ENV_DISCLOSURE.md
forensics/NEW_AGENT_INITIAL_AUDIT.md
forensics/OPERATIONAL_CLAIM_SCOPE.md
forensics/OPERATIONAL_TESTS.md
forensics/PY311_VERIFICATION.md
forensics/R681_VERIFICATION.md
forensics/RED_R-681.md
forensics/RETURN_NONE_AUDIT.md
forensics/RETURN_NONE_AUDIT_R682.md
forensics/SECURITY_FIXES_R682.md
forensics/SHA_RECONCILIATION.md
forensics/asymmetric_defense_audit.md
forensics/boolean_message_audit.md
forensics/clean_build_skips.md
forensics/final_clean_run.log
forensics/final_run_metadata.txt
forensics/final_run_sha256.txt
forensics/gate4_green.log
forensics/gate4_green_v3.log
forensics/gate4_red.log
forensics/gate4_red_v3.log
forensics/gate5_baseline.log
forensics/gate5_green.log
forensics/gate5_true_red.log
forensics/key_state_duality.md
forensics/keyring_rejection_count.json
forensics/pytest_results.xml
forensics/silent_failure_audit.md
frontend/index.html
guardian/__init__.py
guardian/emergency_breaker.py
guardian/integrity_checker.py
guardian/master_guardian.py
guardian/self_evolve.py
main.py
nexus/__init__.py
nexus/main.py
pytest.ini
requirements.txt
scripts/verify_new_key.py
scripts/verify_operational_auth.py
start.sh
tests/ci_run_selection.py
tests/conftest.py
tests/test_agent_ledger.py
tests/test_api.py
tests/test_api_key_rotation_gate1.py
tests/test_archive_inventory.py
tests/test_background_threads_shutdown.py
tests/test_ci_run_selection.py
tests/test_compat_layer.py
tests/test_compress_reset_r613.py
tests/test_config_security.py
tests/test_fail_closed_rotation.py
tests/test_gate1_actual_auth.py
tests/test_gate1_header_auth.py
tests/test_gate1_operational_auth.py
tests/test_health.py
tests/test_identity_persistence.py
tests/test_identity_seal.py
tests/test_key_selection_rotation.py
tests/test_ledger_anchor.py
tests/test_ledger_verify_endpoint.py
tests/test_loyalty_engine.py
tests/test_nexus_lifecycle_integration.py
tests/test_nexus_wiring_r612.py
tests/test_no_key_in_logs.py
tests/test_operational_flag_registration.py
tests/test_operational_no_leak_on_exception.py
tests/test_performance_r606.py
tests/test_predictive_perf_r613.py
tests/test_rate_limit.py
tests/test_return_none_lowrisk.py
tests/test_return_none_security.py
tests/test_safety_layer.py
tests/test_session_ledger_key_hygiene.py
tests/test_simulation_reset_r613.py
tests/test_sovereign_keys.py
tests/test_sovereign_response_r614.py
tests/test_sovereignty_score.py
tests/test_syntax.py
tests/test_synthetic_fixture.py
tests/test_trust_conditions_fingerprints.py
tests/test_writer_keyring_binding.py
verify.sh
```

## 4) حجم الكود: الأسطر لكل امتداد وملفات الاختبار

الأمر: `git ls-tree -r --name-only d56e24e | grep -E '\.(py|js|md|json|yml|sh)$' | xargs wc -l ...` (تجميع أدناه)

```
 135995 total
  11667 total
 128490 total
ملفات الاختبار (tests/ + backend/tests/):
51
```

## 5) git log --oneline --graph --all لآخر 40 التزامًا

```
* d56e24e R-682: التزام تصحيحي ثانٍ — معالجة عوائق المستشار الثلاثة الأخيرة
* 7164044 R-682: التزام تصحيحي تدقيقي — تصويبات خمسة طلبها المستشار قبل التوقيع
* d05a248 R-682: توثيق تشغيلات التحقق على الالتزام الختامي 10c2bf5 نفسه
* 10c2bf5 R-682: البنود ١١ و١٣ (الخاتمة) — PY311_VERIFICATION.md النهائية + FINAL_CLOSURE_R-682.md
* f2577ca R-682: إصلاح CI_STATUS غير المعرف في verify.sh — بقايا فحوص الحالة القديمة
* 20a81ce R-682: حزمة إصلاحات اعتراض المستشار — الفصل النهائي لمصادر رفض R-626 + تحصين دورة حياة الخيوط + نقل منطق اختيار CI لوحدة قابلة للاختبار
* f636bd5 R-682: البند ٨ — إعادة إصدار docs/KEY_STATE_MACHINE.md بملحق فحص مسار التحقق التاريخي
* 60053d4 R-682: إصلاح خطأ الانتقاء الذاتي في فحص حالة تشغيل CI داخل verify.sh
* a733ab8 R-682: البنود ١١ و١٢ — بوابة إصدار Python 3.11.x في verify.sh + مهمة verify-full على Actions + إفصاح بيئة CI
* b76e5a8 R-682: البنود ٧ و٩ و١٠ — تضييق الادعاء التشغيلي + إفصاح جلسات المستشار + إفصاح البيئة المحلية
* e21574a R-682: تصويب رقمي شفاف — المتبقي بعد الإصلاح 10 سجلات R-626 من مسار تحقق السجل (لا صفر)
* 5a7c8c0 R-682: البنود ٤-٦ — إدارة موحدة لخيوط الخلفية + إصلاح جذري لرفض KeyRing في بيئة الاختبار
* 9635886 R-682: البنود ١-٣ — المسح الشامل للحذوفات + مدخل تدقيق بأثر رجعي للتزام 182949f + تحديث استثناء العقد القابل للتوقيع
* 5264c80 R-682 (operational round 5): fix URL-encoded key leak in exception diagnostics (percent-encoding redaction)
* ed9128a R-682 (operational round 4): prove + fix auth-exception key leak (str(e) redaction), inspect operational JUnit artifact, record verification (partial delivery — NOT closure)
* fa67824 R-682 (operational round 3): move --run-operational registration to tests/conftest.py, restore guard, add stray-conftest behavioral test — advisor corrections
* 0c5143d R-682 (operational round 2): register --run-operational + define missing test helpers — fixes CI job that could never pass
* 182949f R-682 (operational): provision old rotated key via KEY_OLD_SECRET + safe secret passing + no key leakage in subprocess
* 2239fde R-682 (item 8): constitutional amendment — justified-deletion regime per owner's explicit decision
* 3a9d2d3 R-682 (docs): fix RED-distinction placement — moved from round-15 section to round-18 section
* 7c4e82a R-682 (docs): evidence corrections per advisor — count breakdown (+1 round-17 test) + explicit RED distinction + item 2b closure
* d47bd73 R-682 (security v18): record persists across save/reload + reflects reconciliation + distinguished upgrade diagnosis
* 6d5e965 R-682 (security v15): separate material commit from durability + unique op ids + exhaustive reconciliation
* 01cb711 R-682 (security v14): tri-state save outcome + event-log reconciliation of pending deaths
* 34648c2 R-682 (security v13): pending-outcome marker — undecided death is distinguishable and recoverable after reload
* e581b4d R-682 (security v12): save-before-event ordering + stale-transform settlement on load
* aadfb93 R-682 (security v11): final-state persistence + fail-closed death-event recording
* 96b9717 R-682 (security v10): initiate_death result contract — recovery failure = False + LIVING, no hanging transform
* 7f3f752 R-682 (security v9): protection model separated from recovery readiness + retroactive RED proof + literal log excerpt
* bfa64d0 R-682 (security v8): no success for incomplete restoration + GCM ash envelope + independent read-back proof + honest death protection
* ad4477c R-682 (build): real ash resurrection — content-hash-proven restoration + MAC-authenticated ashes
* b441989 R-682 (security v6): full-payload field preservation + fail-closed fingerprint gate + test proof fixes
* c4c1a05 R-682 (security v5): authenticated store encryption (AES-GCM) + partial-restoration honesty + real durability semantics
* 0e3ba69 R-682 (security v4): real-store restoration proof + store integrity fix + fail-closed paths
* 0c0d49f R-682 (security v3): fail-closed init + atomic durable state + real-store restoration
* 9c49080 R-682 (security v2): AES-256-GCM standard encryption + downgrade prevention + data-proven restoration
* 70cf6e4 R-682 (security fix): key-contract continuity + MAC-authenticated seed envelope (v2)
* 06f953e R-682 (execution): implement _decrypt_seed (RED→GREEN) + behavioral tests for all 14 low-risk sites
* 1a9ec07 R-682 (report fix): literal f075077 JUnit excerpt, per-row classification (2a/2b/2c DEFERRED), no retroactive-approval wording, real run times from log, new-commit deletions audited (0 .py changed)
* 4b3e1c0 R-682 (report): document verified source f075077 — full --full run from clean clone with its CI run 38667166304; honest 5 open boxes
```

## 6) سياسة المشروع المكتوبة

الملفات: `forensics/DELETED_LINES_AUDIT.md` (قاعدة الحذف)، `pytest.ini`، `.github/workflows/ci.yml`، `docs/`

### نص القاعدة من DELETED_LINES_AUDIT.md (المقطع الأول)

```
# DELETED_LINES_AUDIT.md — Open item 8 (R-681)

**التاريخ:** 2026-10-15
**المرجع:** أمر التسليم — البند المفتوح 8 ("لا حذف" — بعض حذف الأسطر انتهاك نصي للعقد)
**القاعدة:** كل سطر محذوف يحتاج تبريرًا مكتوبًا أو استرجاعًا.

---

## النتيجة

**20 سطرًا محذوفًا** في الالتزامات R-680 → R-680f (8 التزامات).

**كيفية إعادة الإنتاج بأمر واحد:**

```bash
cd sovereign_ai && git diff 3e2b46c~8 3e2b46c | python -c "
import sys
current_file=''
deletions=[]
for line in sys.stdin:
```
