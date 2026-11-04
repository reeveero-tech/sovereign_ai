# -*- coding: utf-8 -*-
"""R-849 (الطبقة ٨ — المهارات الحقيقية): دوام المهارات عبر إعادة النشر.

RED على main (forensics/R-849_skills_RED.txt): مهارة معتمدة بكامل دورتها
(تقييم المؤلف + تقييم مستقل R-843 + اعتماد المالك بأثر) تُفقد مع كل إعادة
نشر — ``data/skills`` قرص مؤقت على Render يُمحى، والمخزن الدائم الموجود
في المشروع (SupabaseDisk، مثبت حيًا في R-719/801c) لا تلمسه المهارات،
والحالة لا تعلن الدوام (صدق غائب).

التصميم (فوق المكونات القائمة، لا إعادة بناء):
- **كتابة نافذة (write-through):** كل تحول في حزمة (propose/evaluate/
  evaluate_independent/approve/rollback) يُدفع فورًا للمخزن الدائم بمفتاح
  ``pkg:{name}:{version}``، وactive.json بمفتاح ``active:{name}``. الفشل لا
  يكسر العملية المحلية (المهارة تعمل) لكنه يُعلن في الحالة synced=false —
  تعافٍ محلي كامل عند غياب المخزن، لا وهم دوام.
- **استعادة عند الإقلاع:** الحزم البعيدة الغائبة محليًا تُكتب بعد فحص بصمة
  المحتوى (تلاعب بعيد = رفض وأثر)، والمحلية الصحيحة هي التي تغلب عند
  التعارض (سياسة موثقة: المحلي آخر ما عرفته هذه العملية، والكتابة النافذة
  تبقي البعيد طازجًا؛ active المحلي يغلب ويُدفع).
- **لا سر يغادر القرص:** الحمولة تُفحص بكتالوج R-848 قبل الدفع — سر ظاهر =
  رفض مغلق (لا رفع)، مع أثر. الحزم كذلك محمية ببصمة المحتوى عند الاستعادة.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("skills_durable")

NAMESPACE = "skills"
PKG_PREFIX = "pkg:"
ACTIVE_PREFIX = "active:"


def _has_secret(text: str) -> bool:
    """كتالوج R-848 الموحد — نفس القواعد التي تحرس المستودع."""
    try:
        from secret_guard.catalog import has_secret
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.secret_guard.catalog import has_secret
    return bool(has_secret(text))


def make_store() -> Optional[Any]:
    """المخزن الدائم من البيئة — None يعني بلا دوام (يُعلن صادقًا، لا يُدّعى)."""
    try:
        from sovereign.cloud_disk import get_cloud_disk
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.sovereign.cloud_disk import get_cloud_disk
    try:
        return get_cloud_disk()
    except Exception:  # TOLERATED (R-849): تعافٍ محلي — بلا مخزن لا دوام، إعلان لا انهيار
        return None


class SkillsDurable:
    """طبقة الدوام فوق SkillLibrary — بلا معرفة بكيفية دورة المهارة.

    ``store`` أي كائن بـ save_blob/load_blob/list_blobs (SupabaseDisk أو
    مزيف الاختبارات). ``audit(op, payload)`` يُستدعى بكل حدث (نجاحًا وفشلًا).
    """

    def __init__(self, root: Path, store: Any, audit=None) -> None:
        self.root = Path(root)
        self.store = store
        self.audit = audit or (lambda op, payload: None)
        self.last_error: Optional[str] = None
        self.backend = getattr(store, "backend_label", None) or _store_label(store)

    # ------------------------------------------------------------ دفع
    def push_pkg(self, name: str, version: str, pkg: Dict[str, Any]) -> bool:
        return self._push(f"{PKG_PREFIX}{name}:{version}", pkg,
                         {"op": "skills_durable.push", "skill": name,
                          "version": str(version)})

    def push_active(self, name: str, act: Dict[str, Any]) -> bool:
        return self._push(f"{ACTIVE_PREFIX}{name}", act,
                          {"op": "skills_durable.push_active", "skill": name})

    def _push(self, key: str, payload: Dict[str, Any], audit: Dict[str, Any]) -> bool:
        if self.store is None:
            self.last_error = None          # لا مخزن — ليس خطأ، وضع معلن
            return False
        try:
            blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                             default=str)
            if _has_secret(blob):           # لا سر يغادر القرص — رفض مغلق
                self.last_error = "secret_in_payload"
                self.audit("skills_durable.blocked",
                           {**audit, "key": key, "reason": "secret_in_payload"})
                return False
            ok = bool(self.store.save_blob(NAMESPACE, key, payload))
            if not ok:
                self.last_error = "save_failed"
            self.audit("skills_durable.push" if ok else "skills_durable.push_failed",
                       {**audit, "key": key})
            return ok
        except Exception as exc:  # noqa: BLE001 — التعافي المحلي أولًا
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.audit("skills_durable.push_failed", {**audit, "key": key,
                                                      "error": self.last_error})
            return False

    # ------------------------------------------------------------ سحب واستعادة
    def _remote(self) -> Optional[Dict[str, Any]]:
        if self.store is None:
            return None
        try:
            rows = self.store.list_blobs(NAMESPACE) or []
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"list_failed: {exc}"
            self.audit("skills_durable.pull_failed", {"error": self.last_error})
            return None
        return {r.get("key"): r.get("payload") for r in rows
                if isinstance(r, dict) and r.get("key")}

    @staticmethod
    def _pkg_ok(payload: Any) -> bool:
        """بصمة المحتوى تُعاد حسابها — الحزمة البعيدة المزوّرة لا تُكتب محليًا."""
        try:
            m = payload["manifest"]
            from skills import content_hash
            return content_hash(m) == payload.get("content_hash")
        except Exception:  # TOLERATED (R-849): حمولة تالفة تُرفض ولا تُنهار الاستعادة
            return False

    def _local_pkg(self, name: str, version: str) -> Optional[Dict[str, Any]]:
        p = self.root / name / f"{version}.json"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # TOLERATED (R-849): ملف محلي تالف يُعاد من البعيد لا انهيار
            return None

    def _write_local(self, name: str, rel: str, data: Dict[str, Any]) -> None:
        import os
        import tempfile
        p = self.root / name / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".durable-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=1, default=str))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)

    def restore(self) -> Dict[str, Any]:
        """عند الإقلاع: البعيد يرد الغائب المحلي، والمحلي الصحيح يغلب.

        سياسة التعارض (موثقة): حزمة موجودة في الاثنين — إن كان المحلي سليم
        البصمة يبقى (والكتابة النافذة أبقت البعيد نسخة منه)؛ إن كان المحلي
        تالفًا/مزوّرًا والبعيد سليمًا ⇒ استعادة من البعيد. active: البعيد
        يُستعمل فقط عند غياب المحلي، وإلا المحلي يغلب ويُدفع.
        """
        rep: Dict[str, Any] = {"backend": self.backend, "restored": [],
                              "repaired": [], "refused": [], "pushed": 0}
        remote = self._remote()
        if remote is None:
            rep["error"] = self.last_error or "no_store"
            return rep
        for key, payload in sorted(remote.items()):
            try:
                kind, rest = key.split(":", 1)
            except ValueError:  # TOLERATED (R-849): مفتاح أعجمي البنية يتخطى لا يُنهار
                continue
            if kind == "pkg":
                name, _, version = rest.partition(":")
                if not name or not version:
                    continue
                if not self._pkg_ok(payload):
                    rep["refused"].append(key)
                    self.audit("skills_durable.refused_remote",
                               {"key": key, "reason": "bad_content_hash"})
                    continue
                local = self._local_pkg(name, version)
                if local is None:
                    self._write_local(name, f"{version}.json", payload)
                    rep["restored"].append(key)
                elif not self._pkg_ok(local) and self._pkg_ok(payload):
                    self._write_local(name, f"{version}.json", payload)
                    rep["repaired"].append(key)
                    self.audit("skills_durable.repaired_local",
                               {"key": key, "reason": "tampered_local"})
            elif kind == "active":
                name = rest
                p = self.root / name / "active.json"
                if not p.exists():
                    self._write_local(name, "active.json", payload)
                    rep["restored"].append(key)
        return rep

    def sync(self) -> Dict[str, Any]:
        """استعادة ثم دفع كل ما هو محلي وغائب بعيدًا — تقرير كامل."""
        rep = self.restore()
        if self.store is None or rep.get("error"):
            return rep
        pushed = 0
        if self.root.exists():
            for d in sorted(p for p in self.root.iterdir() if p.is_dir()):
                for f in sorted(d.glob("*.json")):
                    if f.name == "active.json":
                        continue
                    try:
                        pkg = json.loads(f.read_text(encoding="utf-8"))
                    except Exception:  # TOLERATED (R-849): ملف تالف لا يُدفع — تخطٍّ موثق
                        continue
                    version = (pkg.get("manifest") or {}).get("version")
                    if not version:
                        continue
                    if self.push_pkg(d.name, str(version), pkg):
                        pushed += 1
                act_p = d / "active.json"
                if act_p.exists():
                    try:
                        act = json.loads(act_p.read_text(encoding="utf-8"))
                        if self.push_active(d.name, act):
                            pushed += 1
                    except Exception:  # TOLERATED (R-849): active تالف لا يُدفع — تخطٍّ موثق
                        continue
        rep["pushed"] = pushed
        return rep

    def status(self) -> Dict[str, Any]:
        return {"backend": self.backend, "namespace": NAMESPACE,
                "enabled": self.store is not None,
                "last_error": self.last_error,
                "note": "دوام المهارات عبر إعادة النشر — استعادة عند الإقلاع "
                        "وكتابة نافذة لكل تحول" if self.store is not None else
                        "لا مخزن دائم مضبوط — المهارات تعمل محليًا ولا تدوم "
                        "عبر إعادة النشر (إعلان صادق لا وهم دوام)"}


def _store_label(store: Any) -> Optional[str]:
    if store is None:
        return None
    for attr in ("backend", "label", "name"):
        v = getattr(store, attr, None)
        if isinstance(v, str):
            return v
    return type(store).__name__


def get_durable(root: Path, store: Any = None, audit=None) -> SkillsDurable:
    """store=None ⇒ من البيئة تلقائيًا (بلا دوام إن لم يضبط المالك)."""
    if store is None:
        store = make_store()
    return SkillsDurable(root, store, audit)
