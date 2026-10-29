"""R-800: خدمة مساحة العمل — الملفات والمحادثات والمشاريع فوق التخزين والفهرس."""

from __future__ import annotations

import csv
import io
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import analysis, archives, readers, video, writers
from .storage import MAX_UPLOAD_BYTES, Index, default_backends, new_id, sha256

MAX_MESSAGES = 400


class WorkspaceError(ValueError):
    pass


def _brief(ex: Dict[str, Any]) -> Dict[str, Any]:
    st = ex.get("structure") or {}
    keep = {k: st[k] for k in ("pages", "rows", "columns", "sheets", "slides", "width", "height",
                               "files", "format", "lines", "words", "paragraphs") if k in st}
    if "sheets" in keep:
        keep["sheets"] = [s["name"] for s in keep["sheets"]]
    return {"supported": ex.get("supported"), "chars": ex.get("chars"),
            "truncated": ex.get("truncated"), "error": ex.get("error"), "structure": keep}


class Workspace:
    def __init__(self, storage, disk=None, local_root: Optional[Path] = None, brain=None,
                 vision=None, stt=None) -> None:
        self.storage = storage
        lr = Path(local_root) if local_root else None
        self.files = Index("ws_files", disk, lr / "ws_files.json" if lr else None)
        self.extracts = Index("ws_extract", disk, lr / "ws_extract.json" if lr else None)
        self.conversations = Index("ws_conversations", disk, lr / "ws_conversations.json" if lr else None)
        self.projects = Index("ws_projects", disk, lr / "ws_projects.json" if lr else None)
        self._brain, self._vision, self._stt = brain, vision, stt
        self._lock = threading.Lock()

    # ---------------- الملفات ----------------
    def add_file(self, name: str, data: bytes, content_type: str = "", project_id: Optional[str] = None,
                 source: str = "upload", parent: Optional[str] = None,
                 path: Optional[str] = None) -> Dict[str, Any]:
        name = (Path(str(name or "file").replace("\\", "/")).name or "file")[:200]
        if len(data) > MAX_UPLOAD_BYTES:
            raise WorkspaceError(f"الملف أكبر من {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")
        fid = new_id("F")
        key = f"{fid}/{re.sub(r'[^A-Za-z0-9._-]', '_', name)}"
        if not self.storage.put(key, data, content_type):
            raise WorkspaceError(f"فشل التخزين: {getattr(self.storage, 'last_error', None)}")
        ex = readers.extract(name, data)
        self.extracts.put({"id": fid, "text": ex.get("text") or "", "meta": ex.get("meta") or {},
                           "structure": ex.get("structure") or {}, "kind": ex["kind"],
                           "supported": ex["supported"], "error": ex.get("error"),
                           "chars": ex.get("chars"), "truncated": ex.get("truncated")})
        rec = {"id": fid, "name": name, "path": path or name, "size": len(data), "sha256": sha256(data),
               "kind": ex["kind"], "content_type": content_type or "", "project_id": project_id,
               "source": source, "parent": parent, "storage_key": key, "created_at": time.time(),
               "archived": False, "extract": _brief(ex), "analyses": []}
        return self.files.put(rec)

    def get_file(self, fid: str) -> Dict[str, Any]:
        rec = self.files.get(fid)
        if not rec:
            raise WorkspaceError(f"لا ملف بالمعرف {fid}")
        return rec

    def raw(self, fid: str) -> bytes:
        rec = self.get_file(fid)
        data = self.storage.get(rec["storage_key"])
        if data is None:
            raise WorkspaceError(f"بايتات الملف غير متاحة من التخزين: {getattr(self.storage, 'last_error', None)}")
        return data

    def read(self, fid: str, offset: int = 0, limit: int = 20000) -> Dict[str, Any]:
        rec = self.get_file(fid)
        ex = self.extracts.get(fid) or {}
        text = ex.get("text") or ""
        return {"file": rec, "kind": ex.get("kind"), "supported": ex.get("supported"),
                "error": ex.get("error"), "meta": ex.get("meta"), "structure": ex.get("structure"),
                "text": text[offset: offset + limit], "offset": offset, "total_chars": len(text),
                "more": offset + limit < len(text), "truncated_at_extract": ex.get("truncated")}

    def list_files(self, project_id: Optional[str] = None, kind: Optional[str] = None,
                   parent: Optional[str] = None, include_archived: bool = False) -> List[Dict[str, Any]]:
        out = []
        for r in self.files.all():
            if r.get("archived") and not include_archived:
                continue
            if project_id is not None and r.get("project_id") != project_id:
                continue
            if kind and r.get("kind") != kind:
                continue
            if parent is not None and r.get("parent") != parent:
                continue
            out.append(r)
        return out

    def search(self, q: str, project_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
        q = (q or "").strip()
        if not q:
            return []
        ql = q.lower()
        hits = []
        for r in self.list_files(project_id=project_id):
            score, snippet = 0, None
            if ql in r["name"].lower():
                score += 5
            ex = self.extracts.get(r["id"]) or {}
            t = ex.get("text") or ""
            i = t.lower().find(ql)
            if i >= 0:
                score += 1 + t.lower().count(ql)
                snippet = t[max(0, i - 120): i + 200]
            if score:
                hits.append({"file": r, "score": score, "snippet": snippet})
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:limit]

    def analyze(self, fid: str, question: Optional[str] = None) -> Dict[str, Any]:
        rec = self.get_file(fid)
        data = self.raw(fid)
        ex = self.extracts.get(fid) or readers.extract(rec["name"], data)
        res = analysis.analyze(rec["name"], data, ex, question=question, brain=self._brain,
                               vision=self._vision, stt=self._stt, content_type=rec.get("content_type", ""))
        res["at"] = time.time()
        res["question"] = question
        rec["analyses"] = (rec.get("analyses") or [])[-4:] + [
            {k: res.get(k) for k in ("at", "question", "findings", "summary", "vision", "transcript", "media")}]
        self.files.put(rec)
        return res

    def unpack(self, fid: str) -> Dict[str, Any]:
        rec = self.get_file(fid)
        if rec["kind"] != "archive":
            raise WorkspaceError("الملف ليس أرشيفًا")
        try:
            res = archives.unpack(rec["name"], self.raw(fid))
        except archives.ArchiveError as exc:
            raise WorkspaceError(str(exc))
        children = []
        for path, blob in res["entries"]:
            children.append(self.add_file(Path(path).name, blob, "", project_id=rec.get("project_id"),
                                          source="unpack", parent=fid, path=path))
        return {"archive": fid, "format": res["format"], "extracted": len(children),
                "skipped": res["skipped"], "files": children}

    def zip(self, ids: List[str], name: str = "bundle.zip", project_id: Optional[str] = None) -> Dict[str, Any]:
        if not ids:
            raise WorkspaceError("لا ملفات للضغط")
        entries = []
        for fid in ids:
            r = self.get_file(fid)
            entries.append((r.get("path") or r["name"], self.raw(fid)))
        blob = archives.make_zip(entries)
        name = name if name.lower().endswith(".zip") else name + ".zip"
        return self.add_file(name, blob, "application/zip", project_id=project_id, source="zip")

    def create(self, fmt: str, title: str = "", content: str = "", table=None, data=None,
               project_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            fname, blob, mime = writers.create(fmt, title, content, table, data)
        except ValueError as exc:
            raise WorkspaceError(str(exc))
        return self.add_file(fname, blob, mime, project_id=project_id, source="create")

    def make_video(self, slides: List[Dict[str, Any]], seconds: float = 3.0, audio_id: Optional[str] = None,
              title: str = "video", project_id: Optional[str] = None) -> Dict[str, Any]:
        """R-801: فيديو MP4 حقيقي بـ ffmpeg من شرائح (file_id لصورة، أو text/title) وصوت اختياري."""
        _video = video
        built: List[Dict[str, Any]] = []
        parents: List[str] = []
        for i, s in enumerate(slides or []):
            if s.get("file_id"):
                rec = self.get_file(s["file_id"])
                if rec["kind"] != "image":
                    raise WorkspaceError(f"الشريحة {i + 1}: الملف {rec['name']} ليس صورة ({rec['kind']})")
                built.append({"image": self.raw(rec["id"])})
                parents.append(rec["id"])
            else:
                built.append({"text": str(s.get("text") or ""), "title": str(s.get("title") or "")})
        audio = audio_name = None
        if audio_id:
            arec = self.get_file(audio_id)
            if arec["kind"] not in ("audio", "video"):
                raise WorkspaceError(f"الملف {arec['name']} ليس صوتًا")
            audio, audio_name = self.raw(arec["id"]), arec["name"]
        try:
            blob = _video.make_video(built, seconds, audio, audio_name or "audio")
        except _video.VideoError as exc:
            raise WorkspaceError(str(exc))
        name = writers.safe_filename(title or "video", "mp4")
        rec = self.add_file(name, blob, "video/mp4", project_id=project_id, source="video",
                            parent=parents[0] if parents else None)
        rec["slides"] = len(built)
        rec["seconds"] = len(built) * max(0.5, min(float(seconds or 3.0), _video.MAX_SECONDS))
        return rec

    def generate_image(self, prompt: str, size: str = "512x512", title: str = "",
                       project_id: Optional[str] = None) -> Dict[str, Any]:
        """R-801: صورة مولدة بالذكاء الاصطناعي من خادم التوليد الذاتي (media_client — SD-Turbo على
        آلة خاصة). غير مُهيأ أو فاشل = خطأ معلن بسببه، لا صورة مختلقة."""
        import media_client
        prompt = str(prompt or "").strip()
        if not prompt:
            raise WorkspaceError("الوصف فارغ")
        got = media_client.generate_image(prompt, size or None)
        if not got:
            reason = media_client.last_outcome().get("result")
            hint = {"disabled": "توليد الصور غير مفعّل (MEDIA_ENABLED)",
                    "host_not_self_hosted": "مضيف التوليد ليس ذاتي الاستضافة — رُفض"}.get(reason, reason)
            raise WorkspaceError(f"لم تُولَّد صورة: {hint}")
        data, mime = got
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}.get(mime, "png")
        rec = self.add_file(writers.safe_filename(title or prompt[:40], ext), data, mime,
                            project_id=project_id, source="imagegen")
        rec["prompt"] = prompt[:500]
        return rec

    def convert(self, fid: str, fmt: str) -> Dict[str, Any]:
        rec = self.get_file(fid)
        ex = self.extracts.get(fid) or {}
        text = ex.get("text") or ""
        table = None
        if ex.get("kind") == "csv":
            table = list(csv.reader(io.StringIO(text), delimiter=(ex.get("structure") or {}).get("delimiter", ",")))
            text = ""
        elif ex.get("kind") == "xlsx":
            table = [l.split("\t") for l in text.splitlines() if l and not l.startswith("### ")]
            text = ""
        if not text and not table:
            raise WorkspaceError("لا محتوى مستخرج للتحويل (الملف غير مدعوم أو فارغ)")
        title = Path(rec["name"]).stem
        out = self.create(fmt, title, text, table, project_id=rec.get("project_id"))
        out["parent"] = fid
        out["source"] = "convert"
        return self.files.put(out)

    def set_archived(self, fid: str, archived: bool = True) -> Dict[str, Any]:
        rec = self.get_file(fid)
        rec["archived"] = bool(archived)
        return self.files.put(rec)

    def assign(self, fid: str, project_id: Optional[str]) -> Dict[str, Any]:
        rec = self.get_file(fid)
        rec["project_id"] = project_id
        return self.files.put(rec)

    # ---------------- المحادثات ----------------
    def save_conversation(self, cid: Optional[str], title: str, messages: List[Dict[str, Any]],
                          project_id: Optional[str] = None,
                          model: Optional[str] = None) -> Dict[str, Any]:
        old = self.conversations.get(cid) if cid else None
        clean = []
        for m in (messages or [])[-MAX_MESSAGES:]:
            if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
                continue
            clean.append({"role": m["role"], "content": str(m.get("content") or "")[:20000],
                          "ts": m.get("ts"), "tools": m.get("tools"), "files": m.get("files"),
                          # R-814b: علامة الفشل وتحفظ المراجع يعبران جولة الخادم
                          # كما عبران التخزين المحلي — العرض الصادق لا يضيع بالحفظ
                          "err": bool(m.get("err")), "rev": m.get("rev") or None})
        rec = {"id": cid or (old or {}).get("id") or new_id("C"),
               "title": (title or (clean[0]["content"][:60] if clean else "محادثة"))[:120],
               "messages": clean, "project_id": project_id if project_id is not None else (old or {}).get("project_id"),
               # R-810/813 (البند ٢): نموذج المحادثة يُحفظ مع سجلها ويُستعاد عند فتحها
               "model": model if model is not None else (old or {}).get("model"),
               "created_at": (old or {}).get("created_at") or time.time(), "archived": False}
        return self.conversations.put(rec)

    def list_conversations(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for r in self.conversations.all():
            if r.get("archived") or (project_id is not None and r.get("project_id") != project_id):
                continue
            out.append({k: r.get(k) for k in ("id", "title", "project_id", "created_at", "updated_at")}
                       | {"messages": len(r.get("messages") or []), "model": r.get("model")})
        return out

    def get_conversation(self, cid: str) -> Dict[str, Any]:
        r = self.conversations.get(cid)
        if not r:
            raise WorkspaceError(f"لا محادثة {cid}")
        return r

    def archive_conversation(self, cid: str) -> Dict[str, Any]:
        r = self.get_conversation(cid)
        r["archived"] = True
        return self.conversations.put(r)

    # ---------------- المشاريع ----------------
    def save_project(self, pid: Optional[str], name: str, description: str = "",
                     instructions: str = "", links: Optional[List[str]] = None) -> Dict[str, Any]:
        old = self.projects.get(pid) if pid else None
        if pid and not old:
            raise WorkspaceError(f"لا مشروع {pid}")
        if not (name or "").strip():
            raise WorkspaceError("اسم المشروع مطلوب")
        rec = {"id": pid or new_id("P"), "name": name.strip()[:120], "description": (description or "")[:4000],
               "instructions": (instructions or "")[:8000],
               "links": [str(l)[:500] for l in (links or [])][:50],
               "created_at": (old or {}).get("created_at") or time.time(), "archived": False}
        return self.projects.put(rec)

    def list_projects(self) -> List[Dict[str, Any]]:
        files = self.list_files()
        convs = self.list_conversations()
        out = []
        for p in self.projects.all():
            if p.get("archived"):
                continue
            out.append(p | {"files": sum(1 for f in files if f.get("project_id") == p["id"]),
                            "conversations": sum(1 for c in convs if c.get("project_id") == p["id"])})
        return out

    def get_project(self, pid: str) -> Dict[str, Any]:
        p = self.projects.get(pid)
        if not p:
            raise WorkspaceError(f"لا مشروع {pid}")
        return p | {"files": self.list_files(project_id=pid),
                    "conversations": self.list_conversations(project_id=pid)}

    @staticmethod
    def _imagegen_status() -> Dict[str, Any]:
        import config
        import media_client
        ready = bool(config.MEDIA_ENABLED) and media_client.is_self_hosted(str(config.MEDIA_BASE_URL))
        return {"available": ready, "last": media_client.last_outcome().get("result"),
                "reason": None if ready else "MEDIA_ENABLED/MEDIA_BASE_URL غير مضبوطين على خادم ذاتي"}

    def status(self) -> Dict[str, Any]:
        files = self.files.all()
        kinds: Dict[str, int] = {}
        for f in files:
            kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
        return {"engine": "R-800 workspace", "storage": getattr(self.storage, "backend", "?"),
                "durable": bool(getattr(self.storage, "durable", False) and self.files.durable),
                "files": len(files), "kinds": kinds, "bytes": sum(f.get("size") or 0 for f in files),
                "conversations": len(self.conversations.all()), "projects": len(self.projects.all()),
                "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
                "create_formats": sorted(writers.FORMATS),
                "video": video.available(),
                "imagegen": self._imagegen_status(),
                "archive_formats": ["zip", "tar", "tar.gz", "tgz", "tar.bz2", "tar.xz", "gz", "bz2", "xz", "7z"],
                "persist_errors": self.files.persist_errors + self.extracts.persist_errors}


_WS: Optional[Workspace] = None
_WS_LOCK = threading.Lock()


def get_workspace() -> Workspace:
    global _WS
    with _WS_LOCK:
        if _WS is None:
            import config
            root = Path(getattr(config, "DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
            storage, disk = default_backends(root)
            _WS = Workspace(storage, disk, local_root=None if disk else root / "workspace")
        return _WS


def reset_workspace(ws: Optional[Workspace] = None) -> None:
    global _WS
    with _WS_LOCK:
        _WS = ws
