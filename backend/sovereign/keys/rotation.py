# backend/sovereign/keys/rotation.py
# KeyRotation — تدوير المفاتيح (المرحلة 1 من ROADMAP_V2)
#
# الغرض: واجهة برمجية لتدوير المفاتيح السيادية بأمان.
# عند التدوير:
# 1. يُنشأ مفتاح جديد
# 2. يُقعد المفتاح القديم (لا يُحذف — يُسجّل سبب التقاعد)
# 3. يُكتب حدث KEY_ROTATED في ledger موقّعًا بالمفتاح الجديد
#
# القاعدة الصارمة: المفتاح القديم لا يُحذف أبدًا — يُقعد ويُسجّل.

import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional

from .keyring import KeyRing, KeyRecord, KeyStatus

logger = logging.getLogger("sovereign.keys.rotation")


class KeyRotation:
    """
    واجهة تدوير المفاتيح السيادية.

    rotate(reason) → يُنشئ مفتاحًا جديدًا، يُقعد القديم، يسجّل KEY_ROTATED.
    """

    def __init__(self, keyring: KeyRing, ledger_path: Optional[Path] = None):
        self.keyring = keyring
        if ledger_path is None:
            # المسار الافتراضي (يُحترم SOVEREIGN_DATA_ROOT)
            import os
            data_root = os.getenv("SOVEREIGN_DATA_ROOT")
            if data_root:
                ledger_path = Path(data_root) / "sovereign_core" / "ledger.jsonl"
            else:
                repo_root = Path(__file__).resolve().parent.parent.parent.parent
                ledger_path = repo_root / "data" / "sovereign_core" / "ledger.jsonl"
        self.ledger_path = Path(ledger_path)

    def rotate(self, reason: str = "scheduled_rotation") -> Optional[KeyRecord]:
        """
        يُنفّذ تدوير مفتاح كامل:
        1. يُنشأ مفتاح جديد
        2. يُقعد المفتاح النشط الحالي (إن وُجد) بسب "rotated"
        3. يُحفظ الـ KeyRing
        4. يُكتب حدث KEY_ROTATED في ledger (موقّعًا بالمفتاح الجديد)

        يُعيد KeyRecord للمفتاح الجديد أو None إذا فشل.
        """
        try:
            # 1) المفتاح النشط الحالي (إن وُجد)
            old_key = self.keyring.get_active_key()

            # 2) إنشاء مفتاح جديد
            new_key = self.keyring.generate_new_key(reason=f"rotation: {reason}")

            # 3) تقاعد المفتاح القديم (لا حذف — فقط تغيير حالة)
            if old_key is not None and old_key.key_id != new_key.key_id:
                self.keyring.retire_key(
                    old_key.key_id,
                    reason="rotated",
                    notes=f"rotated to {new_key.key_id} ({reason})"
                )

            # 4) حفظ الحالة
            if not self.keyring.save_to_disk():
                logger.error("❌ فشل حفظ KeyRing بعد التدوير")
                return None

            # 5) كتابة حدث KEY_ROTATED في ledger (موقّعًا بالمفتاح الجديد)
            self._write_rotation_event(new_key, old_key, reason)

            logger.info(
                f"🔄 KeyRotation: rotated {old_key.key_id if old_key else 'None'} → {new_key.key_id} ({reason})"
            )
            return new_key

        except Exception as e:
            logger.exception(
                f"R-682 [SECURITY]: KeyRotation failed — silently swallowing may hide "
                f"a real key compromise. exc={e}"
            )
            return None

    def _write_rotation_event(
        self, new_key: KeyRecord, old_key: Optional[KeyRecord], reason: str
    ) -> None:
        """
        يكتب حدث KEY_ROTATED في ledger — موقّعًا بالمفتاح الجديد.
        (يحمل key_id الجديد — أي حدث جديد يجب أن يحمل key_id.)
        """
        now = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        rotation_event = {
            "type": "KEY_ROTATED",
            "new_key_id": new_key.key_id,
            "old_key_id": old_key.key_id if old_key else None,
            "reason": reason,
            "rotated_at": now,
            "key_id": new_key.key_id,  # القاعدة الصارمة: كل حدث جديد يحمل key_id
        }

        try:
            # إلحاق إلى ledger (append-only)
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rotation_event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"❌ فشل كتابة KEY_ROTATED في ledger: {e}")

    def get_rotation_history(self) -> list:
        """
        يُعيد سجل التدويرات من HISTORY.jsonl (كل أحداث KEY_RETIRED).
        """
        history_file = self.keyring.history_file
        if not history_file.exists():
            return []

        rotations = []
        with open(history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("action") in ("KEY_RETIRED", "KEY_CREATED"):
                        rotations.append(entry)
                # TOLERATED: malformed HISTORY.jsonl line — skip, not raise (R-680)
                except Exception:
                    continue
        return rotations
