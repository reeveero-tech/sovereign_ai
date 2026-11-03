# -*- coding: utf-8 -*-
"""R-840: نظام الموصلات الشامل — التجميع والتوصيل.

مبدأ البناء: سجل موصلات + نمط محول + طبقة اعتماد موحدة — لا كود منفصل
لكل منصة. الأسرار في خزينة R-752 (مشفر AES-256-GCM، fail-closed)، ولا سر
في السجلات أو المخرجات أو النموذج أبدًا.
"""
from __future__ import annotations

import os
import threading
from typing import Optional

from . import (auth_engine, auth_types, contract, credentials, execution, policy,
               registry, runtime_bridge, webhook_gateway)

_SYSTEM: Optional["ConnectorSystem"] = None
_LOCK = threading.Lock()


class ConnectorSystem:
    """التجميع: سجل + اعتمادات + سياسة + محرك + بوابة — مثيل واحد."""

    def __init__(self, data_dir: str, vault=None):
        self.data_dir = data_dir
        cs_dir = os.path.join(data_dir, "connector_system")
        os.makedirs(cs_dir, exist_ok=True)
        self.vault = vault if vault is not None else self._default_vault()
        self.registry = registry.default_registry()
        self.credentials = credentials.CredentialStore(
            state_path=os.path.join(cs_dir, "credentials.json"), vault=self.vault)
        self.policy = policy.OrgPolicy(
            state_path=os.path.join(cs_dir, "org_policy.json"))
        self.executor = execution.Executor(
            state_dir=cs_dir, credentials=self.credentials, policy=self.policy,
            registry=self.registry)
        self.webhooks = webhook_gateway.WebhookGateway(state_dir=cs_dir)

    def _default_vault(self):
        try:
            from backend.sovereign.secrets_vault import get_vault
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from sovereign.secrets_vault import get_vault
        return get_vault()

    def vault_ready(self) -> bool:
        try:
            self.vault.status()
            return True
        except Exception:
            return False


def _data_dir() -> str:
    try:
        from backend.config import DATA_DIR
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج
        try:
            from config import DATA_DIR
        except ImportError:
            return os.path.join(os.getcwd(), "data")
    return str(DATA_DIR)


def get_system() -> ConnectorSystem:
    global _SYSTEM
    with _LOCK:
        if _SYSTEM is None:
            _SYSTEM = ConnectorSystem(data_dir=_data_dir())
        return _SYSTEM


def reset_system_for_tests() -> None:
    """إعادة التهيئة في الاختبارات (بلا كتابة في data الحقيقية)."""
    global _SYSTEM
    with _LOCK:
        _SYSTEM = None


__all__ = ["ConnectorSystem", "get_system", "reset_system_for_tests",
           "auth_engine", "auth_types", "contract", "credentials", "execution",
           "policy", "registry", "runtime_bridge", "webhook_gateway"]
