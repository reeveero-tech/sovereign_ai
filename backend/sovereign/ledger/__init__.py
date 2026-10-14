# backend/sovereign/ledger/__init__.py
# الوحدة السيادية لليدجر — مراسي تشفيرية (المرحلة 2 من ROADMAP_V2)
#
# الغرض: تثبيت الأحداث القديمة (فاشلة التوقيع) بمرساة تشفيرية (Merkle root)
# تجعل التلاعب مستحيلًا دون كشف. لا إعادة توقيع (تزوير)، لا حذف (إنكار).

from .anchor import (
    LedgerAnchor,
    compute_merkle_root,
    verify_merkle_root,
    hash_leaf,
)

__all__ = [
    "LedgerAnchor",
    "compute_merkle_root",
    "verify_merkle_root",
    "hash_leaf",
]
