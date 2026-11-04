# -*- coding: utf-8 -*-
"""R-843: بيئة تقييم معزولة لطبقة التنسيق — منفذ R-840 حقيقي فوق نقل مزيف.

لا شبكة ولا سر حقيقي: الخزينة في الذاكرة، والاعتمادات رموز اختبار معروفة
(تُستعمل أيضًا كـ«كناري» — ظهورها في أي رد أو أثر = تسريب = فشل التقييم).
كل تشغيل في مجلد مؤقت يُحذف بعده.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

try:
    from agent_orchestrator import runtime
    from connector_system import credentials as cs_creds
    from connector_system import execution as cs_exec
    from connector_system import policy as cs_policy
    from connector_system import registry as cs_registry
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.agent_orchestrator import runtime
    from backend.connector_system import credentials as cs_creds
    from backend.connector_system import execution as cs_exec
    from backend.connector_system import policy as cs_policy
    from backend.connector_system import registry as cs_registry

#: رموز الكناري — قيم اختبار لا أسرار؛ ظهورها في المخرج = تسريب
CANARY_SECRETS = ("gh_eval_canary_7f3a", "sb_eval_canary_91c2",
                  "rnd_eval_canary_44d0", "oa_eval_canary_0b8e")


class _Response:
    def __init__(self, status_code: int = 200, data: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self._data = data if data is not None else {}

    def json(self):
        return self._data


class _MemoryVault:
    def __init__(self):
        self.store: Dict[str, str] = {}

    def put(self, name, value, scopes, actor):
        self.store[name] = value
        return {"name": name, "version": 1, "scopes": scopes}

    def get(self, name, capability, actor):
        if name not in self.store:
            raise KeyError(name)
        return self.store[name]

    def rotate(self, name, new_value, actor, scopes=None):
        self.store[name] = new_value
        return {"name": name, "version": 2}

    def delete(self, name, actor):
        self.store.pop(name, None)

    def status(self):
        return {"ready": True}


class Transport:
    """نقل مزيف يسجل كل نداء (للتحقق من مفتاح عدم التكرار وعدد مرات الكتابة)."""

    def __init__(self, status_code: int = 200):
        self.calls = []
        self.status_code = status_code

    def __call__(self, method, url, **kwargs):
        self.calls.append({"method": str(method).upper(), "url": url,
                           "headers": dict(kwargs.get("headers") or {})})
        return _Response(self.status_code, {})


def build(tmp_dir, transport: Optional[Callable] = None,
          brain_fn=None, planner_mode: Optional[str] = None):
    """نظام تنسيق كامل معزول. يعيد (orchestrator, transport)."""
    from pathlib import Path
    tmp = Path(tmp_dir)
    transport = transport or Transport()
    vault = _MemoryVault()
    store = cs_creds.CredentialStore(state_path=tmp / "creds.json", vault=vault)
    pol = cs_policy.OrgPolicy(state_path=tmp / "policy.json")
    ex = cs_exec.Executor(state_dir=tmp, credentials=store, policy=pol,
                          http=transport, clock=lambda: time.time())
    reg = cs_registry.Registry()
    ex.registry = reg
    for conn, scopes, secret in (
            ("github", ["repo:read", "repo:write"], CANARY_SECRETS[0]),
            ("supabase", ["db:read"], CANARY_SECRETS[1]),
            ("render", ["connector:read"], CANARY_SECRETS[2]),
            ("generic_openapi", ["connector:write"], CANARY_SECRETS[3])):
        kind = "pat" if conn == "github" else "api_key"
        store.create(conn, kind, "global", "evaluator", scopes, secret, "eval")
    o = runtime.OrchestratorSystem(data_dir=str(tmp / "orch"), connector_executor=ex,
                                   org_policy=pol, connector_registry=reg)
    if brain_fn is not None or planner_mode:
        try:
            from agent_orchestrator import planner as _planner
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from backend.agent_orchestrator import planner as _planner
        o.planner = _planner.Planner(o.tools, brain_fn=brain_fn, planner_mode=planner_mode)
    return o, transport
