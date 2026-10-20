# -*- coding: utf-8 -*-
"""
R-703 — حاجز الإجراءات الآلية القصوى + كاشف سلامة صريح.

السياق (OWNER_REQUIRED بند ١٥): ثلاثة فحوص لسلامة السجل كانت تختبر
`not core.verify_integrity()`. والدالة تعيد `IntegrityStatus`، وهو تعداد نصي
قيمه غير فارغة، فالفحص لا يرى CORRUPTED أبدًا. إصلاحه وحده كان سيطلق سلسلة
استجابة آلية (تخفٍّ من المستوى 4، وبذرة phoenix، وتشفير عبر `encrypt_blob`
وهي دالة غير موجودة). أمر المالك في R-703: أن يكتشف النظام الخطر ويسجله،
دون أن يتحرك تلقائيًا.

هذه الوحدة:
- `integrity_compromised(status)`: تحكم بالقيمة الصريحة، لا بالصدق المنطقي.
- `report_integrity_violation(...)`: تسجيل حرج (logging) لكل كشف.
- `block_drastic_action(...)`: كل مسار آلي يتفاعل مع التهديد (تخفٍّ،
  phoenix، تشفير، محو آثار) يمر هنا أولًا. ما دام
  `AUTOMATED_DRASTIC_ACTIONS_ENABLED = False` يُمنع الإجراء ويُسجَّل.

الثابت **ليس** متغير بيئة عمدًا: إعادة التفعيل قرار مالك، ولا تتم إلا
بالتزام صريح يغيّر هذا السطر ويحسم `encrypt_blob` (لا تفعيل صامت من البيئة).
الواجهات اليدوية الصريحة (مثل `create_phoenix_seed` إذا استدعاها المالك
مباشرة) لا يمسها هذا الحاجز. هو يمنع التفاعل الآلي فقط.
"""

import logging
import threading
import time
from collections import deque
from typing import Any, Dict, List

logger = logging.getLogger("sovereign.safety.automation_guard")

# قرار مالك (R-703). لا متغير بيئة، ولا تفعيل إلا بالتزام صريح.
AUTOMATED_DRASTIC_ACTIONS_ENABLED = False

_LOG_INTERVAL_SECONDS = 60.0  # منع إغراق السجل: سطر واحد لكل (إجراء، مصدر) في الدقيقة
_lock = threading.Lock()
_blocked: deque = deque(maxlen=500)
_counts: Dict[str, int] = {}
_last_logged: Dict[str, float] = {}


def integrity_compromised(status: Any) -> bool:
    """هل تعني نتيجة verify_integrity تلفًا؟

    `IntegrityStatus` تعداد نصي، فـ`bool(CORRUPTED)` يساوي True. لذلك نحكم
    بالقيمة. نقبل أيضًا القيمة النصية، و`False` المنطقية (واجهات قديمة)، و
    tuple يكون عنصره الأول هو الحالة.
    """
    if isinstance(status, tuple) and status:
        status = status[0]
    if status is False:
        return True
    value = getattr(status, "value", status)
    return isinstance(value, str) and value.lower() == "corrupted"


def report_integrity_violation(source: str, status: Any) -> None:
    """تسجيل حرج لكشف تلف السجل. يكشف ويسجل، ولا يتخذ أي إجراء."""
    value = getattr(status, "value", status)
    logger.critical(
        "R-703 [INTEGRITY]: تلف في سلسلة السجل السيادي اكتشفه %s (الحالة=%s) — "
        "تم التسجيل؛ لا إجراء آلي (قرار مالك)", source, value,
    )


def block_drastic_action(action: str, source: str, /, **context: Any) -> bool:
    """يعيد True إذا مُنع الإجراء، وعلى المستدعي حينها ألا ينفذه."""
    if AUTOMATED_DRASTIC_ACTIONS_ENABLED:
        return False
    key = f"{source}:{action}"
    now = time.time()
    with _lock:
        _counts[key] = _counts.get(key, 0) + 1
        count = _counts[key]
        _blocked.append({"action": action, "source": source,
                         "context": {k: str(v)[:200] for k, v in context.items()},
                         "timestamp": now})
        should_log = now - _last_logged.get(key, 0.0) >= _LOG_INTERVAL_SECONDS
        if should_log:
            _last_logged[key] = now
    if should_log:
        logger.warning(
            "R-703 [SAFETY]: إجراء آلي قصوي مُنع: %s (المصدر=%s، المرات=%d) — "
            "الكشف مسجل، والتنفيذ الآلي معطل حتى قرار المالك",
            action, source, count,
        )
    return True


def blocked_actions() -> List[Dict[str, Any]]:
    """نسخة من سجل المنع (للتشخيص والاختبار)."""
    with _lock:
        return list(_blocked)


def _reset_for_tests() -> None:
    with _lock:
        _blocked.clear()
        _counts.clear()
        _last_logged.clear()
