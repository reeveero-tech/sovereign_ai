# -*- coding: utf-8 -*-
"""R-840: جسر الوكيل — بطاقة «يتطلب اتصالًا» ومراجعة الصلاحية قبل التنفيذ.

عندما يحتاج الوكيل أداة غير متصلة، لا يفشل بصمت: يعيد بطاقة اتصال واضحة
تعرض للمستخدم في المحادثة مع زر إعداد مباشر. والعمليات الكتابية تمر بمراجعة
صلاحية قبل التنفيذ مع رسائل فشل عربية واضحة وإجراء محدد.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def requirement_card(connector_id: str, operation: str,
                      registry=None) -> Dict[str, Any]:
    """بطاقة «يتطلب اتصالًا» — ما يعرضه الوكيل عند غياب الاتصال."""
    if registry is None:
        from .registry import default_registry
        registry = default_registry()
    d = registry.get(connector_id)
    op = d.operation(operation)
    return {
        "type": "requires_connection",
        "connector": connector_id,
        "connector_name": d.name,
        "operation": operation,
        "needed_scopes": sorted(op.scopes),
        "auth_types": list(d.auth_types),
        "setup_path": f"/connectors/system/catalog?connector={connector_id}",
        "message": f"يتطلب اتصالًا بـ{d.name} — الصلاحيات المطلوبة: {sorted(op.scopes)}",
    }


def precheck(executor, connector_id: str, operation: str,
             actor: str = "agent") -> Dict[str, Any]:
    """فحص قبل التنفيذ: جاهزية الاتصال والنطاقات — بلا تنفيذ فعلي."""
    from .execution import RequiresConnectionError, ScopeDeniedError
    d = executor._definition(connector_id)
    op = d.operation(operation)
    try:
        cred = executor.credentials.find_valid(
            connector_id, sorted(op.scopes))
    except Exception as exc:  # TOLERATED: أخطاء المخزن تُعرض كما هي
        return {"ok": False, "reason": str(exc)[:200]}
    if cred is None:
        existing = executor.credentials.list_for_connector(connector_id)
        if not existing:
            return {"ok": False, "card": requirement_card(connector_id, operation),
                    "reason": "لا اتصال قائم"}
        return {"ok": False, "missing_scopes": sorted(op.scopes),
                "reason": "صلاحية غير كافية — اطلب توسيع النطاق"}
    return {"ok": True, "connector": connector_id, "operation": operation,
            "scopes": sorted(cred.scopes)}


def failure_message(kind: str, connector_name: str = "") -> Dict[str, str]:
    """رسائل فشل واضحة مع إجراء — لكل حالة فشل رسالة."""
    messages = {
        "expired": "انتهت صلاحية التوكن — أعد الاتصال من صفحة الموصلات",
        "revoked": "الاتصال مُبطل — أعد الإعداد من صفحة الموصلات",
        "insufficient_scope": "صلاحية غير كافية — اطلب توسيع النطاق من صفحة الإدارة",
        "unavailable": f"الخدمة غير متاحة حاليًا ({connector_name}) — قاطع الدائرة مفتوح",
        "rate_limited": "تجاوز حد المعدل — انتظر قليلًا ثم أعد المحاولة",
        "network": "فشل شبكي — تحقق من الاتصال أو أعد المحاولة",
    }
    action = {"expired": "reconnect", "revoked": "reconnect",
              "insufficient_scope": "widen_scopes",
              "unavailable": "wait", "rate_limited": "wait",
              "network": "retry"}.get(kind, "retry")
    return {"message": messages.get(kind, messages["network"]), "action": action}
