# -*- coding: utf-8 -*-
"""R-840: عقد الموصل الموحد — تعريف واحد لكل موصل بغض النظر عن المنصة.

العقد يفصل: تعريف الموصل (ثابت، في السجل) عن الاعتماد (لكل مالك) عن
التنفيذ (محرك واحد للجميع). الصلاحيات مفصولة قراءة/كتابة على مستوى العملية.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

READ_KINDS = ("query", "sync")
WRITE_KINDS = ("execute", "webhook")


@dataclass(frozen=True)
class Operation:
    """عملية واحدة — kind يحدد سلوك المحرك (idempotency للكتابة مثلًا)."""
    name: str
    kind: str                      # query|execute|sync|webhook
    scopes: frozenset
    description: str = ""
    idempotent: bool = False
    inputs: Dict[str, str] = field(default_factory=dict)

    @property
    def is_write(self) -> bool:
        return self.kind in WRITE_KINDS


# معالج العملية: (مادة الاعتماد، المدخلات، نداء http) → نتيجة
Handler = Callable[..., Dict]


@dataclass
class ConnectorDefinition:
    id: str
    name: str
    version: str
    description: str
    icon: str = "plug"
    category: str = "saas"          # saas|dev|database|internal|generic
    platform_class: str = "oauth"   # oauth|key_only|custom
    auth_types: List[str] = field(default_factory=list)
    operations: Dict[str, Operation] = field(default_factory=dict)
    handlers: Dict[str, Handler] = field(default_factory=dict)
    base_url: str = ""
    timeout_s: float = 20.0
    retry_max_attempts: int = 3
    retry_backoff_base_s: float = 0.5
    rate_limit_rps: float = 10.0
    lifecycle: str = "ga"          # preview|ga|deprecated|removed
    owner: str = "core-team"
    docs_url: str = ""

    def operation(self, name: str) -> Operation:
        try:
            return self.operations[name]
        except KeyError:
            raise KeyError(f"عملية غير معروفة للموصل {self.id}: {name}")

    def scopes_for(self, name: str) -> frozenset:
        return self.operation(name).scopes

    def public(self) -> Dict[str, object]:
        """حمولة الواجهة — لا أسرار ولا معالجات."""
        return {
            "id": self.id, "name": self.name, "version": self.version,
            "description": self.description, "icon": self.icon,
            "category": self.category, "platform_class": self.platform_class,
            "auth_types": list(self.auth_types),
            "operations": {n: {"kind": o.kind, "scopes": sorted(o.scopes),
                              "description": o.description,
                              "is_write": o.is_write, "idempotent": o.idempotent}
                           for n, o in self.operations.items()},
            "base_url": self.base_url, "timeout_s": self.timeout_s,
            "rate_limit_rps": self.rate_limit_rps,
            "lifecycle": self.lifecycle, "owner": self.owner,
            "docs_url": self.docs_url,
        }


def read_only(operations: Dict[str, Operation]) -> bool:
    """موصل قراءة فقط إذا لم تكن أي عملية منه كتابة."""
    return all(not o.is_write for o in operations.values())
