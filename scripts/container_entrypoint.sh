#!/bin/sh
# R-760 (ROADMAP_V5 ١.٣ + ١.٧ — بأمر المالك D-044): نقطة دخول الحاوية.
#
# Fly ينشئ الحجم الدائم المركّب على /app/data مملوكًا للجذر. هذه النقطة تبدأ
# جذرًا فقط لتملّك الحجم للمستخدم 1001 ثم تُسقط الامتياز بـsetpriv قبل تشغيل
# التطبيق — التطبيق لا يعمل جذرًا أبدًا. أي فشل (set -e) يوقف الإقلاع (فشل مغلق).
#
# R-815 (أمر المالك 2026-10-29 «إحياء كل ما هو ميت»): الحارس المعزول
# (backend/supervisor_daemon.py) كان ملفًّا حيًّا بلا مشغِّل في الإنتاج —
# نبضه غائب دائمًا (العيب الوحيد المفتوح في defects.scan). الآن: عند ضبط
# SOVEREIGN_SUPERVISOR=1 تُطلق نقطة الدخول الحارس كعملية مرافقة كمستخدم
# التطبيق (لا جذر)، قبل تنفيذ أمر التطبيق نفسه. العقد R-687 محفوظ: الحارس
# يراقب التطبيق عبر HTTP فقط (لا استيراد متبادل ولا مشاركة عملية)، وموت
# الحارس لا يوقف الإقلاع — الإطلاق بجهده الأقصى (best-effort) بلا set -e.
set -eu
DATA_DIR="${SOVEREIGN_CONTAINER_DATA:-/app/data}"
APP_UID="${SOVEREIGN_APP_UID:-1001}"
APP_ROOT="${SOVEREIGN_APP_ROOT:-/app}"
if [ "$#" -eq 0 ]; then
  echo "R-760: لا أمر لتشغيله — رفض" >&2
  exit 64
fi

start_supervisor() {
  # R-815: لا شيء يُفعل إلا بقرار صريح من البيئة (الافتراضي: معطّل محليًا).
  [ "${SOVEREIGN_SUPERVISOR:-0}" = "1" ] || return 0
  # لا حارس بلا ملف الحارس — غيابه لا يكسر الإقلاع.
  [ -f "${APP_ROOT}/backend/supervisor_daemon.py" ] || return 0
  mkdir -p "${DATA_DIR}/supervisor" 2>/dev/null || return 0
  # R-815b (درس النشر الأول 2026-10-30): في مسار الجذر يُستدعى هذا التابع بعد
  # تملّك جذر البيانات للمستخدم — المجلد الجديد يُنشأ هنا بملكية الجذر، وإعادة
  # توجيه سجل الحارس (يعمل بمستخدم التطبيق عبر setpriv) تفشل قبله أصلًا فلا ينطلق
  # الحارس أبدًا (النبض غاب في النشر الأول رغم نجاح الفحوص). تملّك المجلد للمستخدم
  # هنا يضمن نجاح الإطلاق من أول إقلاع، والفشل يُبلع (best-effort) كالعادة.
  if [ "$(id -u)" = "0" ]; then
    chown -R "$APP_UID:$APP_UID" "${DATA_DIR}/supervisor" 2>/dev/null || true
  fi
  # فاصل الحارس (0، 60] ثانية هو النطاق الذي يقبل /n نبضه — خارجه يُعدّ تالفًا.
  SUP_CMD="cd '${APP_ROOT}' && nohup python3 -m backend.supervisor_daemon --url 'http://127.0.0.1:${PORT:-8080}' --interval '${SOVEREIGN_SUPERVISOR_INTERVAL:-30}' >> '${DATA_DIR}/supervisor/supervisor_stdout.log' 2>&1 &"
  if [ "$(id -u)" = "0" ]; then
    # جذر: الامتياز مسقوط للحارس أيضًا — لا عملية جذر أبدًا (عقد R-760).
    setpriv --reuid="$APP_UID" --regid="$APP_UID" --clear-groups -- \
      sh -c "$SUP_CMD" || true
  else
    # تشغيل غير جذري (--user): الهوية صحيحة أصلًا — إطلاق مباشر.
    sh -c "$SUP_CMD" || true
  fi
}

apply_restore() {
  # R-847 (D-062): استعادة مجهزة تُطبق هنا قبل التطبيق والحارس (لا اتصال SQLite
  # مفتوح). الفشل يتراجع داخليًا إلى نسخة ما قبل الاستعادة ويُسجل ويُشعر؛ والإقلاع
  # يكمل في كل الأحوال حتى يبقى المالك قادرًا على الوصول (بلا set -e هنا).
  [ -f "${DATA_DIR}/.restore/PENDING.json" ] || return 0
  R_CMD="cd '${APP_ROOT}/backend' && python3 -m backup apply-pending"
  if [ "$(id -u)" = "0" ]; then
    setpriv --reuid="$APP_UID" --regid="$APP_UID" --clear-groups -- \
      sh -c "$R_CMD" || echo "R-847: تطبيق الاستعادة لم ينجح — انظر .restore/LAST.json" >&2
  else
    sh -c "$R_CMD" || echo "R-847: تطبيق الاستعادة لم ينجح — انظر .restore/LAST.json" >&2
  fi
}

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_DIR"
  chown -R "$APP_UID:$APP_UID" "$DATA_DIR"
  chmod 0750 "$DATA_DIR"
  apply_restore
  start_supervisor
  exec setpriv --reuid="$APP_UID" --regid="$APP_UID" --clear-groups -- "$@"
fi
apply_restore
start_supervisor
exec "$@"
