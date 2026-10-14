# GOAL_DISCOVERY.md — اكتشاف الغاية الحقيقية للمشروع

**التاريخ:** 2026-10-14 (مُحدّث 2026-10-15 بعد R-680d — مراجعة المستشار)
**المنهج:** اتباع سلسلة الاستدعاءات الفعلية (start.sh → app.lifespan → orchestrator → مسار طلب)،
قراءة أجسام الاختبارات المعقدة (لا عناوينها)، وقراءة أفعال ledger الفعلية.

---

## الغاية المعلنة (من docs/)

> **"بناء عقل سيادي — نظام ذكاء اصطناعي يتعلم ويتطور ذاتياً، يطلب إذن السيد (المالك) قبل أي تعديل ذاتي، يعمل على منصات خارجية مؤقتاً، وينتقل لاحقاً إلى تشغيل سيادي كامل على جهاز المستخدم."**

المصدر: `docs/PROJECT_CHARTER.md` (القسم 1).

---

## الغاية الفعلية (من الكود — سلسلة الاستدعاءات)

> **"نظام حوكمة (governance) + إثبات نزاهة (integrity proof) — عقل يفهم أمر السيد، يرفض ما يخالف
> إرادته، ويسجّل كل فعل في سجل مُوقَّع لا يمكن التلاعب به (Merkle anchors + KeyRing + state machine)."**

### سلسلة الاستدعاءات الفعلية (من start.sh)

```
start.sh
  → cd backend; python -m uvicorn app:app
    → app.py: app = FastAPI(lifespan=lifespan)
      → lifespan() يبدأ Orchestrator
      → app.state.orchestrator = orchestrator
```

### مسار طلب فعلي (chat):

```
backend/app.py:623 @app.post("/chat")
  → app.py:639 enforce_input_safety(message.text, is_sovereign=False)
    → backend/safety.py: SafetyGuard.check_action() (R-608)
      → يفحص نص الرسالة ضد FORBIDDEN_WORDS و يمنع self_modify
  → app.py:670 process_in_background()
    → orchestrator.run_cycle(input_data)
      → backend/orchestrator.py — يُشغّل كل مكون (consciousness, memory, sovereign, ...)
```

### مخرجات النظام الفعلية:

| المسار | يُنتج | الخدمة الفعلية |
|---|---|---|
| `/chat` | ChatResponse(reply, status, cycle_id) | الرد على أمر السيد |
| `/sovereign/command` | SovereignCommandResponse | تنفيذ أمر سيادي (بعد safety check) |
| `/health` | status, components | مراقبة صحة النظام |
| `/sovereignty/score` | primitives + composite | قياس السيادة (قابل للجدل) |
| `/agent/ledger` | AgentLedger report | سجل أفعال الوكيل |
| `/ledger/verify` | verify report | إثبات نزاهة ledger |
| `/guardian/status` | guardian report | حالة الحارس |

---

## أجسام الاختبارات المعقدة (5 — الأهم)

### 1. `tests/test_trust_conditions_fingerprints.py` (453 سطراً)
```python
# tests/test_trust_conditions_fingerprints.py:30
class TestFullFingerprints:
    """R-646: بصمات كاملة — sha256 كامل، لا ابتلاع أخطاء القراءة."""
    def _collect_fingerprints_strict(self, root: Path) -> dict:
        # sha256 كامل لكل ملف — يفشل عند خطأ قراءة (لا يبتلع)
```
**ماذا تختبر:** أن أي عملية مرفوضة لا تُغيّر أي ملف (بصمات sha256 كاملة قبل/بعد).
**ماذا تعتبر مهماً:** نزاهة الملفات — لا تلاعب حتى في حالة الرفض.

### 2. `tests/test_fail_closed_rotation.py` (452 سطراً)
```python
# يختبر فشلًا مُغلقًا: إذا فشل تدوير المفتاح → لا تُكمل العملية (fail-closed)
```
**ماذا تعتبر مهماً:** فشل التدوير = رفض، لا تجاهل.

### 3. `tests/test_ledger_anchor.py` (346 سطراً)
```python
# test_merkle_root_deterministic, test_verify_anchor_detects_tampering
```
**ماذا تعتبر مهماً:** أن Merkle root قابل للتحقق، وأن أي تلاعب يُكتشف.

### 4. `tests/test_sovereign_keys.py` (311 سطراً)
**ماذا تعتبر مهماً:** أن KeyRing يرفض المفتاح المخترق (COMPROMISED) — لا يوقّع به.

### 5. `tests/test_agent_ledger.py` (278 سطراً)
```python
# test_append_only_never_deletes
```
**ماذا تعتبر مهماً:** أن سجل أفعال الوكيل append-only — لا حذف أبداً.

---

## أفعال ledger الفعلية

**ملاحظة صادقة (R-680d):** `data/sovereign_core/ledger.jsonl` **غير متاح** في clone نظيف
(سر/بيانات تشغيل — غير مُتتبعة). التاريخ يقول 11,777 حدث (من `forensics/KEY_LOSS_TIMELINE.md`).
**`agent_ledger.jsonl` سجل آخر** (31 حدثاً — أفعال الوكيل التقني)، ليس بديلاً عنه.

آخر 20 حدثاً في `data/sovereign_core/agent_ledger.jsonl` (سجل الوكيل):
كل حدث مُوثَّق بـ R-XXX (رقم قرار) و يُسجّل: تدوير مفتاح، إصلاح ثغرة، إضافة اختبار.

---

## الفجوة بين الغايتين

| البند | الغاية المعلنة | الغاية الفعلية |
|---|---|---|
| **الجوهر** | "عقل يتعلم ويتطور ذاتياً" | **"نظام حوكمة + إثبات نزاهة"** |
| **الذكاء** | "يتعلم ويتطور" | **قواعد قرارات rule-based** (مُعلَن بصدق) |
| **الاستقلالية** | "تشغيل سيادي كامل لاحقاً" | **موجودة جزئياً (HMAC + KeyRing)** |
| **التوثيق** | "وثائق حاكمة" | **سجل جنائي + مفاتيح + مراسي** (أقوى) |

**الحكم:** المشروع يفعل ما يُعلن (عبداً للسيد) — لكن **الغاية الفعلية أضيق وأعمق**:
المشروع هو **نظام حوكمة + إثبات نزاهة**، وليس "عقل يتطور". التعلم موجود
(`backend/memory/biological/learning.py`) لكنه ثانوي.

---

## الأدلة (10 مسارات ملف/أسطر)

| # | المسار | السطر/القسم | الدليل |
|---|---|---|---|
| 1 | `start.sh` | 1-5 | نقطة التشغيل الفعلية |
| 2 | `backend/app.py` | 623-670 | مسار chat الفعلي (safety → orchestrator) |
| 3 | `backend/safety.py` | 1-30 | طبقة الأمان (SafetyGuard) |
| 4 | `tests/test_trust_conditions_fingerprints.py` | 30-60 | نزاهة الملفات (R-646) |
| 5 | `tests/test_fail_closed_rotation.py` | كامل | فشل مُغلق للتدوير |
| 6 | `tests/test_ledger_anchor.py` | 1-50 | Merkle root قابل للتحقق |
| 7 | `tests/test_sovereign_keys.py` | كامل | رفض المفتاح المخترق |
| 8 | `backend/sovereign/controller.py` | 1-14 | "تاج السيادة" |
| 9 | `backend/sovereign/ledger/anchor.py` | 1-30 | "لا تزوير للتاريخ" |
| 10 | `data/sovereign_core/agent_ledger.jsonl` | آخر 20 | أفعال الوكيل (R-XXX) |

---

## خطة العمل (الجزء السابع — الإكمال)

### ما هو حي بالفعل (لا يحتاج عمل):
- ✅ KeyRing + State Machine + Merkle Anchors — تعمل.
- ✅ SafetyGuard مربوط في كل مسارات الإدخال (chat, sovereign/command, ws).
- ✅ 280 اختبار ناجح (لا فشل) — 7 skips موثقة.
- ✅ Guardian + EmergencyBreaker موجودان.
- ✅ Clone نظيف يعمل (273 passed + 10 skipped = 283 — 0 failed).

### ما أُنجز (R-680/R-680b/R-680c/R-680d):
1. ✅ composite.py — مُصلّح (أوزان 1.00، JUnit provenance، حد 100، `no_orphans` نسبة)
2. ✅ clean_build_skips.md — مُحدّث (10 skips موثقة)
3. ✅ silent_failure_audit.md — مُحدّث (TOLERATED comments + AST-based test)
4. ✅ test_no_silent_exceptions.py — يعمل (يُفحص except:pass + except:continue)
5. ✅ /sovereignty/score — يُعيد primitives + composite مع `* قابل للجدل`

### ما يجب أن يُستمر:
كل ملف، كل دالة، كل مسار — يجب أن يخدم الغاية (حوكمة + إثبات نزاهة).
