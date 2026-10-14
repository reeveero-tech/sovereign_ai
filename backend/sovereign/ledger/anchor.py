# backend/sovereign/ledger/anchor.py
# Merkle Anchoring — مرساة اليدجر (المرحلة 2 من ROADMAP_V2)
#
# المبدأ الحاكم: "لا نُصلح الماضي، بل نُثبّته. لا نُخفي الجرح، بل
# نُطوّقه بختم جديد."
#
# 11,777 حدثًا في ledger.jsonl بتوقيعات فاشلة ليست "بيانات تالفة" — هي
# دليل جنائي. المفتاح الأصلي فُقد. إعادة التوقيع = تزوير. الحذف = إنكار.
# الحل السيادي: نُبقيها كما هي، ونُضيف فوقها **مرساة تشفيرية** (Merkle root)
# تُثبّت محتواها بدقة. أي تعديل مستقبلي على أي بايت في النطاق المُرسى
# سيُغيّر الـ Merkle root ويُكشف فورًا.
#
# هذا هو الحل: لم "نُصلح" التوقيعات القديمة، لكن التلاعب بها صار
# مستحيلًا دون كشفه.

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("sovereign.ledger.anchor")


def hash_leaf(data: str) -> str:
    """يُجزّئ سطرًا واحدًا (حدثًا) بـ sha256."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_merkle_root(lines: List[str]) -> str:
    """
    يبني شجرة Merkle من قائمة أسطر (أحداث) ويُعيد الجذر.

    الخوارزمية:
    1. كل سطر يُجزّئ بـ sha256 (leaf)
    2. يُدمج كل زوج متجاور (leaf_i + leaf_i+1) → sha256 (عقدة)
    3. إذا كان العدد فرديًا، يُكرر الأخير
    4. يُكرر حتى يتبقى جذر واحد

    أي تغيير في أي بايت في أي سطر سيُغيّر الجذر بالكامل.
    """
    if not lines:
        raise ValueError("cannot compute Merkle root of empty list")

    # المستوى 0: الأوراق (leaves)
    level = [hash_leaf(line) for line in lines]

    # بناء الشجرة صعودًا
    while len(level) > 1:
        # إذا فردي، كرر الأخير
        if len(level) % 2 == 1:
            level.append(level[-1])
        # دمج كل زوج
        next_level = []
        for i in range(0, len(level), 2):
            combined = level[i] + level[i + 1]
            next_level.append(
                hashlib.sha256(combined.encode("utf-8")).hexdigest()
            )
        level = next_level

    return level[0]


def verify_merkle_root(lines: List[str], expected_root: str) -> bool:
    """
    يتحقق أن قائمة أسطر تُنتج نفس Merkle root المتوقع.
    إذا تغيّر أي بايت في أي سطر، سيفشل التحقق.
    """
    try:
        actual_root = compute_merkle_root(lines)
        return actual_root == expected_root
    except Exception as e:
        logger.error(f"❌ Merkle verification error: {e}")
        return False


class LedgerAnchor:
    """
    يُدير مراسي اليدجر (anchors) — تثبيت نطاقات من الأحداث بمرساة تشفيرية.

    التخزين: data/sovereign_core/ledger.anchors.jsonl (سجل إلحاقي — لا حذف)
    """

    def __init__(
        self,
        ledger_path: Optional[Path] = None,
        anchors_path: Optional[Path] = None,
    ):
        import os

        # المسارات الافتراضية (تُحترم SOVEREIGN_DATA_ROOT للعزل)
        data_root = os.getenv("SOVEREIGN_DATA_ROOT")
        if data_root:
            base = Path(data_root) / "sovereign_core"
        else:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            base = repo_root / "data" / "sovereign_core"

        self.ledger_path = ledger_path or (base / "ledger.jsonl")
        self.anchors_path = anchors_path or (base / "ledger.anchors.jsonl")

        # ضمان المجلد
        self.anchors_path.parent.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # قراءة اليدجر
    # ============================================================

    def read_ledger_lines(self) -> List[str]:
        """يقرأ كل أسطر اليدجر (بدون معالجة — النص الخام)."""
        if not self.ledger_path.exists():
            return []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip()]

    # ============================================================
    # إنشاء مرساة
    # ============================================================

    def anchor_batch(
        self,
        batch_start: int,
        batch_end: int,
        key_id: str,
        signature: str,
        reason: str = "PRE_KEYRING_UNSIGNED_BATCH",
        notes: str = "",
    ) -> Optional[Dict]:
        """
        يُثبّت نطاقًا من الأحداث بمرساة تشفيرية.

        1. يقرأ الأسطر في النطاق [batch_start, batch_end]
        2. يحسب Merkle root
        3. يُنتج سجل مرساة في ledger.anchors.jsonl
        4. المرساة موقّعة بالمفتاح الجديد (key_id) — ليست إعادة توقيع
           للأحداث القديمة، بل توقيع مستقل للمرساة.

        يُعيد سجل المرساة أو None إذا فشل.
        """
        try:
            lines = self.read_ledger_lines()
            total = len(lines)

            # التحقق من النطاق
            if batch_start < 0 or batch_end >= total or batch_start > batch_end:
                logger.error(
                    f"❌ anchor_batch: invalid range [{batch_start}, {batch_end}] "
                    f"(total={total})"
                )
                return None

            batch_lines = lines[batch_start : batch_end + 1]
            merkle_root = compute_merkle_root(batch_lines)

            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            anchor_id = hashlib.sha256(
                f"{batch_start}:{batch_end}:{merkle_root}".encode("utf-8")
            ).hexdigest()[:16]

            anchor_record = {
                "anchor_id": anchor_id,
                "batch_start": batch_start,
                "batch_end": batch_end,
                "event_count": len(batch_lines),
                "merkle_root": f"sha256:{merkle_root}",
                "reason": reason,
                "key_id": key_id,
                "signature": signature,
                "anchored_at": now,
                "notes": notes
                or (
                    f"{len(batch_lines)} events with unverifiable signatures "
                    f"due to lost key. Merkle root anchors their exact content. "
                    f"Any future modification of any event in this range will "
                    f"change the root and be detectable."
                ),
            }

            # كتابة المرساة (إلحافية — لا حذف)
            with open(self.anchors_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(anchor_record, ensure_ascii=False) + "\n")

            logger.info(
                f"✅ Anchored [{batch_start}, {batch_end}] "
                f"({len(batch_lines)} events) — root={merkle_root[:16]}..."
            )
            return anchor_record

        except Exception as e:
            logger.error(f"❌ anchor_batch failed: {e}")
            return None

    # ============================================================
    # التحقق من مرساة
    # ============================================================

    def verify_anchor(self, anchor: Dict) -> Tuple[bool, str]:
        """
        يتحقق أن الأحداث في نطاق المرساة لا تزال تُنتج نفس Merkle root.

        يُعيد (success, message):
        - (True, "verified") إذا تطابق الجذر
        - (False, reason) إذا فشل (تغيّر المحتوى أو خطأ)
        """
        try:
            lines = self.read_ledger_lines()
            start = anchor["batch_start"]
            end = anchor["batch_end"]

            if end >= len(lines):
                return False, (
                    f"ledger has only {len(lines)} lines, anchor range "
                    f"[{start}, {end}] exceeds it"
                )

            batch_lines = lines[start : end + 1]
            expected_root = anchor["merkle_root"].replace("sha256:", "")

            if verify_merkle_root(batch_lines, expected_root):
                return True, "verified"
            else:
                actual_root = compute_merkle_root(batch_lines)
                return False, (
                    f"Merkle root mismatch: expected {expected_root[:16]}..., "
                    f"got {actual_root[:16]}... — content was modified"
                )

        except Exception as e:
            return False, f"verification error: {e}"

    def verify_all_anchors(self) -> Dict:
        """
        يتحقق من كل المراسي المسجلة ويُعيد تقريرًا كاملًا.
        """
        anchors = self.list_anchors()
        results = {
            "total_anchors": len(anchors),
            "verified": 0,
            "failed": 0,
            "details": [],
        }

        for anchor in anchors:
            ok, msg = self.verify_anchor(anchor)
            if ok:
                results["verified"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "anchor_id": anchor["anchor_id"],
                "batch": [anchor["batch_start"], anchor["batch_end"]],
                "status": "verified" if ok else "failed",
                "message": msg,
            })

        return results

    # ============================================================
    # قائمة المراسي
    # ============================================================

    def list_anchors(self) -> List[Dict]:
        """يُعيد كل المراسي المسجلة."""
        if not self.anchors_path.exists():
            return []
        anchors = []
        with open(self.anchors_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    anchors.append(json.loads(line))
                except Exception:
                    continue
        return anchors

    # ============================================================
    # تقرير شامل
    # ============================================================

    def full_report(self) -> Dict:
        """
        يُعيد تقريرًا شاملًا: عدد الأحداث المُرساة، عدد المراسي،
        حالة كل مرساة، والتغطية.
        """
        lines = self.read_ledger_lines()
        anchors = self.list_anchors()
        verification = self.verify_all_anchors()

        # حساب الأحداث المُغطاة بالمراسي
        anchored_events = set()
        for a in anchors:
            for i in range(a["batch_start"], a["batch_end"] + 1):
                anchored_events.add(i)

        return {
            "total_events": len(lines),
            "total_anchors": len(anchors),
            "anchored_events_count": len(anchored_events),
            "anchored_coverage_pct": round(
                (len(anchored_events) / len(lines)) * 100, 2
            ) if lines else 0.0,
            "anchors_verified": verification["verified"],
            "anchors_failed": verification["failed"],
            "anchor_details": verification["details"],
        }
