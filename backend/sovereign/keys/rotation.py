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
#
# R-698 (التزام التصويب الأمني): حدث KEY_ROTATED يُكتب عبر
# SovereignCore.append_event — حدث سلسلة كامل (hash/prev_hash/blob/time/
# signature/key_id) موقّع بالمفتاح النشط الجديد، ومحتواه (old/new/reason)
# داخل blob المُجزّأ. كان يُلحق سطرًا خامًا بلا سلسلة ولا توقيع فيُفسد
# سلامة ledger النواة (CORRUPTED) — التفصيل: forensics/R-698_ED25519.md §٦.

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

    def __init__(self, keyring: KeyRing, ledger_path: Optional[Path] = None,
                 core=None):
        self.keyring = keyring
        # R-698 (تصويب): نواة محقونة اختيارية — كاتب واحد للسلسلة. يجب أن
        # تشارك حلقة المفاتيح نفسها (وإلا لوقّعت بحلقة غير التي دارت).
        self.core = core
        if core is not None:
            if getattr(core, "_keyring", None) is not keyring:
                raise ValueError(
                    "R-698: injected core must share the rotating KeyRing "
                    "(refusing to sign KEY_ROTATED with a different keyring)"
                )
            if ledger_path is not None and Path(ledger_path) != Path(core.log_file):
                raise ValueError(
                    "R-698: ledger_path conflicts with injected core.log_file"
                )
            ledger_path = core.log_file
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

    def rotate(self, reason: str = "scheduled_rotation",
               key_type: str = "hmac") -> Optional[KeyRecord]:
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

            # 2) إنشاء مفتاح جديد — R-698: نوع المفتاح صريح (hmac تاريخي
            # أو ed25519 الجديد) — الدوران إلى ed25519 لا يمس التاريخ
            if key_type == "ed25519":
                new_key = self.keyring.generate_new_ed25519_key(
                    reason=f"rotation: {reason}"
                )
            else:
                new_key = self.keyring.generate_new_key(
                    reason=f"rotation: {reason}"
                )

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

    def _ledger_core(self):
        """النواة التي تكتب KEY_ROTATED: المحقونة، أو نواة مربوطة بـledger_path
        بتخطيط sovereign_core نفسه (blobs/index/meta/integrity بجواره)
        وبحلقة المفاتيح التي دارت."""
        if self.core is None:
            from backend.memory.core import SovereignCore
            d = self.ledger_path.parent
            (d / "blobs").mkdir(parents=True, exist_ok=True)
            self.core = SovereignCore(
                log_file=self.ledger_path,
                blobs_dir=d / "blobs",
                index_file=d / "index.json",
                meta_file=d / "meta.json",
                integrity_file=d / "integrity.json",
                keyring=self.keyring,
            )
        return self.core

    def _write_rotation_event(
        self, new_key: KeyRecord, old_key: Optional[KeyRecord], reason: str
    ) -> None:
        """
        يكتب حدث KEY_ROTATED في ledger — حدث سلسلة موقّع بالمفتاح الجديد.
        R-698 (تصويب): عبر SovereignCore.append_event (سلسلة prev_hash +
        توقيع + key_id) — لا إلحاق خام. المحتوى داخل blob المُجزّأ.
        """
        now = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        payload = {
            "new_key_id": new_key.key_id,
            "old_key_id": old_key.key_id if old_key else None,
            "reason": reason,
            "rotated_at": now,
        }
        try:
            self._ledger_core().append_event("KEY_ROTATED", payload)
        except Exception as e:
            # لا سطر جزئي ولا خام: الفشل يُبقي السلسلة سليمة، لكنه فجوة تدقيق
            # (دوران بلا سجل) — يُسجَّل أمنيًا بصوت عالٍ لا بصمت.
            logger.exception(
                f"R-698 [SECURITY]: failed to record KEY_ROTATED in ledger "
                f"(rotation persisted, audit gap): {e}"
            )

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
