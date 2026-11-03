# -*- coding: utf-8 -*-
"""R-840: سجل الموصلات — تعريف واحد لكل منصة + دورة حياة موثقة.

يضبط GitHub وGitLab وRender وSupabase والموصل العام (OpenAPI). دورة الحياة:
preview → ga → deprecated → removed، مع إشعارات وخطة ترحيل موثقة في الأحداث.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .connectors import generic_openapi, github_connector, gitlab_connector, \
    render_connector, supabase_connector
from .contract import ConnectorDefinition


class RegistryError(Exception):
    pass


class Registry:
    def __init__(self):
        self._defs: Dict[str, ConnectorDefinition] = {}
        self._events: List[Dict] = []
        self._lock = threading.Lock()
        for d in (github_connector.definition(),
                  gitlab_connector.definition(),
                  render_connector.definition(),
                  supabase_connector.definition(),
                  generic_openapi.definition()):
            self.register(d)

    def register(self, d: ConnectorDefinition) -> ConnectorDefinition:
        with self._lock:
            old = self._defs.get(d.id)
            if old is not None and old.version == d.version:
                raise RegistryError(f"موصل مسجل مرتين بنفس الإصدار: {d.id}")
            if old is not None:
                self._events.append({"connector": d.id, "event": "upgraded",
                                     "from_version": old.version,
                                     "to_version": d.version,
                                     "ts": __import__("time").time()})
            self._defs[d.id] = d
        return d

    def get(self, connector_id: str) -> ConnectorDefinition:
        with self._lock:
            d = self._defs.get(connector_id)
        if d is None:
            raise RegistryError(f"موصل غير مسجل: {connector_id}")
        if d.lifecycle == "removed":
            raise RegistryError(f"موصل مُزال: {connector_id}")
        return d

    def all(self) -> List[ConnectorDefinition]:
        with self._lock:
            return list(self._defs.values())

    def catalog(self) -> List[Dict]:
        return [d.public() for d in self.all()]

    def auth_type(self, auth_type_id: str):
        from . import auth_types
        return auth_types.auth_type(auth_type_id)

    # ------------------------------------------------------------ دورة الحياة
    def set_lifecycle(self, connector_id: str, lifecycle: str,
                      message: str = "") -> Dict:
        valid = ("preview", "ga", "deprecated", "removed")
        if lifecycle not in valid:
            raise RegistryError(f"حالة دورة حياة غير صالحة: {lifecycle}")
        d = self.get(connector_id)
        old = d.lifecycle
        d.lifecycle = lifecycle
        event = {"connector": connector_id, "from": old, "to": lifecycle,
                 "message": message, "ts": __import__("time").time()}
        self._events.append(event)
        return event

    def deprecate(self, connector_id: str, new_version: str, message: str) -> Dict:
        event = self.set_lifecycle(connector_id, "deprecated", message)
        event["event"] = "deprecated"
        event["deprecated"] = True
        event["migration"] = new_version
        return event

    def lifecycle_events(self) -> List[Dict]:
        return list(self._events)


_REGISTRY: Optional[Registry] = None


def default_registry() -> Registry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = Registry()
    return _REGISTRY
