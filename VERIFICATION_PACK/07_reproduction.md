# القسم ٧ — التحقق المستقل (على d56e24e)

## 32) أوامر إعادة إنتاج كاملة (من الصفر على جهاز نظيف)

المتطلبات: git، Python 3.11.x (بوابة verify.sh ترفض غيره)، وgh مصادق عليه لهذا المستودع.

```bash
# 1. الاستنساخ والتثبيت
git clone https://github.com/reeverero-tech/sovereign_ai.git
cd sovereign_ai
git checkout d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. الحزمة الاعتيادية (يجب أن تكون: 424 passed, 1 deselected, 0 failed)
timeout 600 python -m pytest tests/ backend/tests/ -q -m "not operational"

# 3. قياس R-626 وأخطاء التسجيل (قبض كامل)
timeout 900 python -m pytest tests/ backend/tests/ -m "not operational" --log-file=/tmp/ledger.log -q > /tmp/stdout.txt 2> /tmp/stderr.txt; echo "exit=$?"
grep -c "R-626" /tmp/ledger.log; grep -c -- "--- Logging error ---" /tmp/stderr.txt /tmp/stdout.txt

# 4. دورة التحقق الكاملة (تتطلب CI أخضر على نفس الـSHA مسبقًا)
bash verify.sh --full
echo "exit=$?"  # النجاح = 0

# 5. الوظيفة التشغيلية (تتطلب السرين KEY_SECRET وKEY_OLD_SECRET)
gh workflow run ci.yml --repo reeveero-tech/sovereign_ai --ref main -f run_operational=true
gh run list --repo reeveero-tech/sovereign_ai --limit 1   # انتظر conclusion: success

# 6. التحقق الحرفي عبر Actions (يتطلب CI_RUN_ID لتشغيل push مكتمل على الـSHA)
gh workflow run ci.yml --repo reeveero-tech/sovereign_ai --ref main -f run_verify_full=true -f ci_run_id=<push_run_id>
```

## 33) شروط مسبقة لا يستطيع المالك تلبيتها

1. مادة المفتاح القديم الأصلي (إن فُقدت فلا إثبات تاريخي لواقعة التدوير — توليد قيمة بديلة يُضعف الاختبار إلى إثبات رفض قيمة مهيأة فقط).
2. لا شيء آخر خارجي: CI والأسرار الموجودة والوظائف متاحة للمالك بصفته مالك المستودع.

## 34) ادعاءات غير قابلة للتحقق من قِبل المالك

1. توقيعات المراجع (advisor) — جرت في جلسة داخلية؛ نصوصها الأصلية محفوظة خارج المستودع (مضمّنة كنسخ في ADVISOR_SESSIONS_DISCLOSURE.md).
2. القياسات المحلية التي أجريتها (صفر R-626 بقبض كامل) — قابلة لإعادة الإنتاج بالأمر رقم 3 أعلاه لكن لا يمكن للمالك رؤية ملفاتي الخام نفسها.
3. القيم الخام للسرين — غير مرئية لأي طرف (بالتصميم)؛ التحقق سلوكي فقط.
4. ملف ledger.jsonl الخام (11,777→116,910 حدث) — غائب عن clone نظيف (غير متتبع) — لا يمكن للمالك فحص الأحداث التاريخية مفردة.
5. الادعاء التاريخي «التشغيلية لم تنجح قبل هذه الجولة» — تاريخي؛ دليله حالة الكود عند 182949f (قابلة للفحص بـgit show 182949f:tests/test_gate1_operational_auth.py).
