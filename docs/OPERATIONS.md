# OPERATIONS.md — التشغيل والنشر

> كيف يُشغَّل المشروع ويُنشر؟ الحالة الفعلية كما رُصدت.
> آخر تحديث: 2026-10-13 (الدفعة M6 — R-603)

---

## 1) التشغيل المحلي

### الطريقة الوحيدة التي تعمل حالياً
```bash
cd backend
pip install -r requirements.txt   # أو من الجذر
uvicorn app:app --host 0.0.0.0 --port 8000
```

### الطرق المكسورة
- ❌ `python main.py` من الجذر → `No module named 'orchestrator'` (يجب التشغيل من داخل backend).
- ❌ `docker build` + `uvicorn backend.app:app` → `No module named 'orchestrator'` (استيراد نسبي).

---

## 2) تعارض المنافذ

| نقطة | المنفذ | الحالة |
|---|---|---|
| `start.sh` (Replit) | 5000 | يعمل |
| `fly.toml` (Fly.io) | 8080 | app: sovereign-ai-k20elq, region ams |
| `Dockerfile` | 8080 | ⚠️ يفشل (استيراد) |
| `app.py` (مباشر) | 8000 | يعمل |
| `.replit` | 5000→80 | يعمل |

> بند R-104: توحيد المنافذ.

---

## 3) متغيرات البيئة (config.py)

| المتغير | الافتراضي | ملاحظة |
|---|---|---|
| `SOVEREIGN_KEY` | لا افتراضي ثابت؛ التطوير يولّد مفتاحًا **دائمًا** يُحفظ في `data/key.secret` (0600، مستثنى من git — R-610)، والإنتاج يفشل مغلقاً دون سر | ✅ راجع SECURITY.md |
| `DRIVE_ENABLED` | false | — |
| `AI_ENVIRONMENT` | — | — |
| `CORE_MODEL_NAME` | microsoft/Phi-3-mini-4k-instruct | لا يُستخدم فعلياً |
| `CORE_MODEL_LOAD_ON_START` | true | لا يُستخدم فعلياً |
| `MAX_USER_MESSAGES_PER_MINUTE` | 30 | ✅ حد `/chat` لكل IP مباشر؛ process-local (R-603) |
| `MAX_CONCURRENT_USERS` | 100 | — |
| `CORS_ORIGINS` | `*` | 🔴 يرفض الإقلاع في الإنتاج (D-034 — فشل مغلق) |

---

## 4) النشر

### Fly.io
- `fly.toml`: app `sovereign-ai-k20elq`, region `ams`, health check `/health`, 512MB/1CPU.
- ⚠️ Dockerfile الحالي لا يبني (R-105).

### Replit
- `.replit`: python-3.12, nodejs-20, port 5000→80.

### GitHub/Railway/Google/device
- مذكورة في README كمنصات مستهدفة، دون إعدادات نشر موثقة.

---

## 5) سجل التحديثات

| التاريخ | التغيير | الدفعة |
|---|---|---|
| 2026-10-12 | توثيق التشغيل والنشر من مسح M0 | M0 |

## ملاحظات M1 (R-112)

- `.gitignore` أُنشئ — يمنع تتبع `__pycache__` وبيانات وقت التشغيل.
- إزالة 2233 ملف بيانات متتبع سابقاً قرار منفصل (M2).

## 6) الأداء (R-502)

### تحسين مطبّق
- أُضيف `GZipMiddleware` إلى `backend/app.py` للاستجابات الأكبر من 1,024 بايت، بمستوى ضغط 6.
- استجابة الصفحة الرئيسية `/`: **35,240 بايت → 4,727 بايت** مع `Accept-Encoding: gzip` (خفض 86.6%).

### قياسات warm محلية
| المسار | median | p95 |
|---|---:|---:|
| `/health` | 3.71 ms | 10.31 ms |
| `/status` | 1.34 ms | 9.50 ms |
| `/components/nexus` | 1.31 ms | 6.21 ms |

> القياسات محلية على بيئة التطوير، وليست SLA إنتاجياً. أعد القياس بعد النشر على بيئة الإنتاج.

## 7) حد الطلبات (R-603)

- `MAX_USER_MESSAGES_PER_MINUTE` يضبط عدد طلبات `/chat` لكل IP مباشر خلال 60 ثانية (الافتراضي 30).
- تجاوز الحد يعيد HTTP 429 مع `Retry-After`.
- الحالة في الذاكرة bounded ولكل عملية؛ عند تشغيل عدة workers/نسخ، لكل واحدة حد مستقل. لا تُمرر عناوين `X-Forwarded-For` غير الموثوقة إلى المحدد.

---

## 8) بوابة CI للحذوفات (قرار المالك — Issue #8، التزام f8526e1)

- **اسم الخط في `.github/workflows/ci.yml`:** `Owner rule (Issue #8): reject commits deleting lines without # DELETION-JUSTIFIED` (في وظيفة `Tests + Atomic Batch Gate`، قبل التشغيل مباشرة بعد checkout).
- **ما يفحصه بالضبط:** الالتزام المدفوع نفسه (`${GITHUB_SHA}`): مجموع أسطر الحذف من `git show --numstat` (تُستثنى الملفات الثنائية)، والالتزامات الدمجية (merge) تُتخطى صراحةً.
- **شرط الفشل:** إذا كان مجموع الحذوفات > 0 **و** لا توجد العلامة `# DELETION-JUSTIFIED` في نفس الالتزام (رسالة الالتزام أو الفرق نفسه) → الخط يفشل (`exit 1`) فتفشل وظيفة CI ويُرفض الالتزام تلقائيًا.
- **نتائج الاختبار الفعلي:** (1) نجاح على التزام بصفر حذوفات — فحص محلي على `a5df86c` (deletions: 0 → PASS) + تشغيل فعلي في CI على `f8526e1` («أسطر الحذف في هذا الالتزام: 0» — تشغيل 38833180631)؛ (2) رفض على حذوفات بلا علامة — فحص محلي على `d56e24e` (12 سطرًا محذوفًا بلا `# DELETION-JUSTIFIED` → FAIL برمز خروج 1).
- **حد صريح:** البوابة تفحص **الالتزامات المدفوعة بعد `f8526e1` فقط** — لا تفحص التاريخ السابق، والتاريخ أُغلق بقرار المالك بأثر رجعي (Issue #8) لا بهذه البوابة.


---

## 9) بوابة التحقق الموحدة tools/run_gate.py (قرار D-026)

- **كيف يعمل**: يلتقط بصمة محتوى الكود والاختبارات قبل تشغيل pytest (sha256 على كل ملف .py حي — forensics/ والأرشيف والبيانات مستثناة)، يشغل الأمر الفعلي (بادئة junit-prefix بـSHA حقيقي)، يقارن البصمة بعد التشغيل (تغيير = فشل)، ثم يختم تقرير JUnit بالبصمة الملتقطة حرفيًا ويسجل الفعل كاملًا في forensics/build_actions.jsonl (الأمر + رمز الخروج + الهوية + وقتا البدء والنهاية).
- **كيف يتحقق المالك من أن البوابة لم تُتلاعب بها**: `python3 -c "import sys, subprocess; sys.path.insert(0,'.'); sys.path.insert(0,'backend'); from backend.sovereign.score import _v2_content_fingerprint, _v2_invariants_evidence; head=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip(); print('tree:', _v2_content_fingerprint('.')); ev=_v2_invariants_evidence('.', junit_path='forensics/pytest_results.xml'); print(ev)"` — `passing: 1` يعني أن تقرير JUnit مقبول ومربوط بمحتوى الشجرة الحالية (بصمته المضمّنة تطابق بصمة الشجرة الآن)؛ أي رفض يعني عدم قبول الدليل — قد يكون لتغيّر الكود بعد التشغيل، أو أن التقرير من شجرة أخرى، أو لفشل الاختبارات أو نقص الدليل نفسه. حد معلن: البصمة 78fc736b7ed9f204... قابلة لإعادة الإنتاج عند الالتزامين 6f9553c و5753ab8 (تحقق فعلي في worktree نظيف) وغير قابلة عند HEAD بعد التزام الإغلاق — لأن جولة الإغلاق نفسها عدّلت backend/sovereign/score.py بأمر المالك (القسم ٢) فتغيّرت بصمة الشجرة.

---

## 10) تشغيل الحارس كخدمة (R-698 — ملفات فقط، لا تشغيل)

> الحارس المعزول (`backend/supervisor_daemon.py` — R-687): عملية مستقلة
> تقرأ `/health` و`/status` من التطبيق عبر HTTP وتكتب سجل مراقبة
> append-only. **لا يملك منفذ استماع خاصًا إطلاقًا** — كل منافذ التشغيل
> تبقى للتطبيق (8080 في الصورة / 8000 محليًا). لا يستورده التطبيق ولا
> يستورد التطبيق — موت أي طرف لا يمس الآخر.

### systemd (الخيار الأول)

الملف: `scripts/sovereign-supervisor.service` — قبل التفعيل عدّل:

| البند | القيمة الافتراضية في الملف | ملاحظة |
|---|---|---|
| جذر المستودع | `/opt/sovereign_ai` | WorkingDirectory — يلزم مسار النشر الفعلي |
| عنوان التطبيق | `http://127.0.0.1:8000` | عدّله إن كان التطبيق على 8080 أو مضيف آخر |
| جذر البيانات | `/var/lib/sovereign` | قابل للكتابة للمستخدم `sovereign` — السجل في `<الجذر>/supervisor/monitor_log.jsonl` |
| فترة الدورة | 2.0 ثانية | `--interval` |
| إعادة التشغيل | `Restart=always` (بعد 5 ثوانٍ، حد 5 محاولات/دقيقة) | systemd ينهض الحارس تلقائيًا |

التفعيل (من صلاحيات المالك): نسخ الوحدة إلى `/etc/systemd/system/` ثم
`systemctl daemon-reload` ثم `systemctl enable --now sovereign-supervisor`.

### Docker Compose (البديل)

الملف: `scripts/docker-compose.supervisor.yml` — خدمتان: `app` (نفس صورة
Dockerfile، المنفذ 8080) و`supervisor` (الأمر: `python -m
backend.supervisor_daemon --url http://app:8080` عبر شبكة Compose —
**127.0.0.1 داخل حاوية الحارس لا تشير إلى حاوية التطبيق**؛ الاسم الداخلي
`app` هو العنوان الصحيح). إعادة التشغيل التلقائية `unless-stopped`، وسجل
المراقبة في وحدة تخزين `supervisor-data` (append-only).

### قواعد ثابتة للحارس في أي وضع تشغيل

- لا استيراد للحارس داخل `app.py` (حارس بنيوي يمنع ذلك — R-687).
- سجل المراقبة append-only: `<جذر البيانات>/supervisor/monitor_log.jsonl`.
- فشل قراءة التطبيق لا يوقف الحارس — يُسجل الخطأ ويستمر (المراقب لا يموت
  مع المراقَب).
- خريطة الوعي: أول فحص عند الإقلاع ثم كل 60 ثانية (`--map-interval`).
