#!/usr/bin/env bash
# R-814b — فحص جذر المنشور: 200 مضمون من المنادي؛ هنا: غير فارغ وبلا كلمة المالك الممنوعة.
# سكربت مستقل يختبره pytest على عينات موجبة وسالبة (درس أول تشغيل: rg غائبة عن
# مشغلات GitHub و«فشل الأداة» داخل if ظهر نجاحًا كاذبًا — هنا grep بفشل صريح).
# الاستعمال: live_check_root.sh FILE  — خروج 0 سليم، 1 عيب، 2 خلل فحص.
set -euo pipefail
FILE="${1:?المطلوب مسار ملف الصفحة}"
[ -s "$FILE" ] || { echo "::error::الصفحة فارغة — لا يُفحص فراغ"; exit 1; }
if grep -q "سيادي" "$FILE"; then
  echo "::error::الصفحة الرئيسية تحوي كلمة ممنوعة بأمر المالك (البند ٧)"
  exit 1
fi
echo "OK root page (nonempty, no forbidden word)"
