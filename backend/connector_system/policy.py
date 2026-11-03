# -*- coding: utf-8 -*-
"""R-840: سياسة المؤسسة والحوكمة — من يسمح بماذا قبل أي إعداد أو تنفيذ.

- قائمة سماح/حظر للموصلات، وموافقة إدارية قبل السماح للمستخدمين.
- قائمة أنواع المصادقة المسموحة على مستوى المؤسسة.
- سجل تدقيق مركزي لكل قرار (سماح/حظر/موافقة/رفض).
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class PolicyError(Exception):
    pass


class PolicyDenied(PolicyError):
    pass


class ApprovalRequired(PolicyError):
    pass


@dataclass
class OrgPolicy:
    state_path: str
    default_mode: str = "allowlist_registry"  # كل المسجل مسموح إلا المحظور/المعلق
    clock: Any = field(default=time.time)

    def __post_init__(self):
        self._lock = threading.Lock()
        if not os.path.exists(self.state_path):
            self._save({
                "blocked_connectors": [],
                "require_approval": [],
                "approved": [],
                "allowed_auth_types": None,   # None = كل الأنواع المسجلة
                "audit": [],
            })

    # ------------------------------------------------------------ الحالة
    def _load(self) -> Dict[str, Any]:
        with open(self.state_path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
        try:
            from runtime.atomic_json import atomic_write_json
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج
            from backend.runtime.atomic_json import atomic_write_json
        atomic_write_json(self.state_path, data, ensure_ascii=False, indent=1)

    def _update(self, fn) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
            fn(data)
            self._save(data)
        return data

    def _audit(self, event: str, payload: Dict[str, Any]) -> None:
        def fn(data):
            data["audit"].append({"ts": self.clock(), "event": event, **payload})
            data["audit"] = data["audit"][-500:]  # حد أقصى
        self._update(fn)

    # ------------------------------------------------------------ الأوامر (إدارية)
    def block_connector(self, connector_id: str, actor: str) -> None:
        def fn(data):
            data["blocked_connectors"].append(connector_id)
        self._update(fn)
        self._audit("policy.block", {"connector": connector_id, "actor": actor})

    def unblock_connector(self, connector_id: str, actor: str) -> None:
        def fn(data):
            data["blocked_connectors"] = [c for c in data["blocked_connectors"]
                                          if c != connector_id]
        self._update(fn)
        self._audit("policy.unblock", {"connector": connector_id, "actor": actor})

    def require_approval(self, connector_id: str, actor: str) -> None:
        def fn(data):
            if connector_id not in data["require_approval"]:
                data["require_approval"].append(connector_id)
        self._update(fn)
        self._audit("policy.require_approval",
                    {"connector": connector_id, "actor": actor})

    def approve(self, connector_id: str, actor: str) -> None:
        def fn(data):
            if connector_id not in data["approved"]:
                data["approved"].append(connector_id)
        self._update(fn)
        self._audit("policy.approve", {"connector": connector_id, "actor": actor})

    def allow_auth_types(self, types, actor: str) -> None:
        def fn(data):
            data["allowed_auth_types"] = sorted(types)
        self._update(fn)
        self._audit("policy.allow_auth_types",
                    {"types": sorted(types), "actor": actor})

    # ------------------------------------------------------------ الفحوص
    def check_setup(self, connector_id: str, auth_type: str) -> None:
        """قبل إنشاء اعتماد — ترفض PolicyDenied أو تطلب ApprovalRequired."""
        data = self._load()
        if connector_id in data["blocked_connectors"]:
            raise PolicyDenied(f"موصل محظور بسياسة المؤسسة: {connector_id}")
        if connector_id in data["require_approval"] \
                and connector_id not in data["approved"]:
            raise ApprovalRequired(f"يتطلب موافقة إدارية قبل الإعداد: {connector_id}")
        allowed = data.get("allowed_auth_types")
        if allowed is not None and auth_type not in allowed:
            raise PolicyDenied(f"نوع مصادقة غير مسموح: {auth_type}")

    def check_execution(self, connector_id: str, operation: str, actor: str) -> None:
        data = self._load()
        if connector_id in data["blocked_connectors"]:
            raise PolicyDenied(f"موصل محظور بسياسة المؤسسة: {connector_id}")
        if connector_id in data["require_approval"] \
                and connector_id not in data["approved"]:
            raise ApprovalRequired(f"يتطلب موافقة إدارية: {connector_id}")

    def audit_log(self) -> List[Dict[str, Any]]:
        return list(self._load()["audit"])

    def public(self) -> Dict[str, Any]:
        d = self._load()
        return {"blocked_connectors": d["blocked_connectors"],
                "require_approval": d["require_approval"],
                "approved": d["approved"],
                "allowed_auth_types": d["allowed_auth_types"],
                "audit_count": len(d["audit"])}
