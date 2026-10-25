#!/bin/sh
# R-760 (ROADMAP_V5 ١.٣ + ١.٧ — بأمر المالك D-044): نقطة دخول الحاوية.
#
# Fly ينشئ الحجم الدائم المركّب على /app/data مملوكًا للجذر. هذه النقطة تبدأ
# جذرًا فقط لتملّك الحجم للمستخدم 1001 ثم تُسقط الامتياز بـsetpriv قبل تشغيل
# التطبيق — التطبيق لا يعمل جذرًا أبدًا. أي فشل (set -e) يوقف الإقلاع (فشل مغلق).
set -eu
DATA_DIR="${SOVEREIGN_CONTAINER_DATA:-/app/data}"
APP_UID="${SOVEREIGN_APP_UID:-1001}"
if [ "$#" -eq 0 ]; then
  echo "R-760: لا أمر لتشغيله — رفض" >&2
  exit 64
fi
if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_DIR"
  chown -R "$APP_UID:$APP_UID" "$DATA_DIR"
  chmod 0750 "$DATA_DIR"
  exec setpriv --reuid="$APP_UID" --regid="$APP_UID" --clear-groups -- "$@"
fi
exec "$@"
