# DEPLOYMENT_READY.md — قائمة مراجعة النشر إلى fly.io (R-698)

> ملف فقط — لا نشر فعلي (النشر من صلاحيات المالك حصرًا). هذه القائمة
> تُغطي كل ما يحتاجه المالك لتشغيل الإنتاج بأمان. القاعدة الثابتة:
> **الأسرار لا تدخل git ولا الصورة ولا fly.toml أبدًا** — فقط عبر
> `fly secrets set`.

---

## ١) الأسرار (إلزامية — التطبيق يرفض الإقلاع بدونها)

| السر | كيفية توليده | ملاحظة |
|---|---|---|
| `SOVEREIGN_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` | جذر الاشتقاق (HKDF — R-697) لكل مفاتيح التوقيع/التشفير/المصادقة. **لا يُولَّد في الصورة** — `fly secrets set SOVEREIGN_KEY=...` |
| `CORS_ORIGINS` | قائمة صريحة مفصولة بفواصل: `https://your-domain.example,https://admin.your-domain.example` | D-034: في الإنتاج ترفض `*` و`null` والقائمة الفارغة — فشل مغلق عند الإقلاع |

أوامر المالك (على جهاز بمصدر موثوق):

```bash
fly secrets set SOVEREIGN_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
fly secrets set CORS_ORIGINS="https://your-domain.example"
```

## ٢) حالة البيانات قبل أول نشر

- الصورة **لا تحوي بيانات تشغيل** (`.dockerignore` يستثني `data/`
  و`nexus_data/` و`logs/` و`credentials/` وكل الأسرار) — أي إقلاع نظيف.
- ماذا يعني هذا عمليًا:
  - `data/key.secret` يُولَّد تلقائيًا عند الإقلاع إن غاب (سلوك التطوير
    الموجود) — **لكن في الإنتاج مرِّر `SOVEREIGN_KEY` كسر** (أعلاه) ولا
    تعتمد على المولَّد داخل الجهاز (يضيع مع إعادة بناء الجهاز).
  - `data/keys/keyring.json` و`HISTORY.jsonl` — سجل المفاتيح الإلحافي: إن
    أردت استمرارية حلقة المفاتيح عبر عمليات إعادة النشر، ثبّتها بحجم دائم
    (`fly volumes create sovereign_data --size 1` + تحميله في
    `/app/data`) — وإلا فكل إعادة نشر تبدأ حلقة مفاتيح جديدة (التاريخ
    القديم يبقى محفوظًا في سجلات git المحلية، لا في الجهاز).
  - ledger (`data/sovereign_core/ledger.jsonl`) — نفس القرار: حجم دائم أو
    بداية نظيفة (قرار تشغيلي للمالك).

## ٢-ب) النشر عبر GitHub Actions (R-717 — بأمر المالك 2026-10-22)

الملف `.github/workflows/deploy-fly.yml` — **يدوي فقط** (Actions ← «Deploy — Fly.io (manual)» ← Run workflow،
مع كتابة اسم التطبيق للتأكيد). بواباته: تشغيل CI ناجح على نفس SHA، وجود سر المستودع `FLY_API_TOKEN`
(رمز نشر خاص بالتطبيق وحده: `fly tokens create deploy -a sovereign-ai-k20elq`)، ثم `flyctl deploy --remote-only`
وفحص `/health` على الرابط العام. أسرار التطبيق (`SOVEREIGN_KEY` و`CORS_ORIGINS`) تبقى في Fly لا في GitHub.
حارسه: `tests/test_deploy_workflow_fly.py`. بيئة الوكيل لا تبني الصورة (بنّاء Fly يتصل بغير HTTPS) — لذلك هذا الطريق.

## ٣) خطوات النشر

```bash
fly auth login
fly launch            # أول مرة فقط — يستخدم fly.toml الموجود (لا تعيد إنشاؤه)
fly secrets set SOVEREIGN_KEY=... CORS_ORIGINS=...
fly deploy
fly status
```

- فحص الحيوية: `fly checks status` — `/health` كل 10 ثوانٍ (موجود في
  fly.toml).
- الرفض المغلق يعمل: إن نسيت سرًا فالجهاز ينهار عند الإقلاع ولا يخدم —
  هذا مقصود (D-034 + جولة المجلس <1>).

## ٤) الحارس في الإنتاج (اختياري — قرار تشغيلي للمالك)

- systemd: `scripts/sovereign-supervisor.service` (التفعيل في
  docs/OPERATIONS.md §10).
- Docker Compose: `scripts/docker-compose.supervisor.yml`.
- الحارس لا يملك منفذًا — يراقب التطبيق عبر HTTP فقط.

## ٥) تحقق ما بعد النشر

- [ ] `fly checks status` — كل الفحوص خضراء (/health).
- [ ] `curl https://your-domain.example/health` — `{"status":"healthy",...}`.
- [ ] مصادقة API تعمل بمفتاح مشتق (R-697): توليد `api_auth` محليًا من
      `SOVEREIGN_KEY` نفسه واستدعاء مسار محمي — `200`، وبلا مفتاح `401`.
- [ ] `fly logs` — لا تحذير CORS ولا رفض إقلاع.

## ٦) ما لا يُفعل في هذه الجولة (حرفيًا)

- لا نشر فعلي، لا `fly deploy`، لا تشغيل حارس — كل ما في هذا الملف
  تجهيز موثق فقط. التنفيذ قرار المالك.

## تنبيه أمني — دوران المفاتيح وسلسلة ledger (تصويب R-698)

- قبل التزام تصويب R-698، كان `KeyRotation.rotate()` يُلحق سطر KEY_ROTATED
  خامًا (بلا سلسلة ولا توقيع) في ledger النواة فيجعله **CORRUPTED**. أُصلح:
  الحدث الآن موسلسل وموقّع، والنواة تعيد مزامنة آخر تجزئة من القرص قبل كل
  إلحاق. التفصيل: `forensics/R-698_ED25519.md` §٦.
- **لا تنقل إلى الإنتاج ledger دار عليه مفتاح بنسخة سابقة للتصويب** دون
  فحص `verify_content_integrity` أولًا — السطر الخام لا يُصلح تلقائيًا
  (قرار البيانات للمالك).
- الدوران على المؤسسة الحية: `core = get_core(); KeyRotation(core._keyring, core=core)`
  — بحلقة مفاتيح النواة نفسها (كاتب واحد؛ الحلقة المختلفة تُرفض بـValueError).
