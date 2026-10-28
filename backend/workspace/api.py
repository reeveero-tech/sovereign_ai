"""R-800: واجهة HTTP لمساحة العمل — كلها بمفتاح المالك (ترويسة X-Sovereign-Key).

الملفات والمحادثات والمشاريع بيانات المالك الخاصة: لا قراءة بلا مفتاح (401).
كل عمل ثقيل (تخزين/استخراج/تحليل) في خيط — حلقة الحدث و/health لا تُحجب (درس R-796).
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .service import WorkspaceError, get_workspace
from .storage import MAX_UPLOAD_BYTES


class VideoBody(BaseModel):
    slides: List[Dict[str, Any]] = Field(..., max_length=60)
    seconds: float = 3.0
    audio_id: Optional[str] = None
    title: str = "video"
    project_id: Optional[str] = None


class ImageBody(BaseModel):
    prompt: str = Field(..., max_length=1000)
    size: str = "512x512"
    title: str = ""
    project_id: Optional[str] = None


class CreateBody(BaseModel):
    format: str
    title: str = ""
    content: str = Field("", max_length=500_000)
    table: Optional[List[List[Any]]] = None
    data: Optional[Any] = None
    project_id: Optional[str] = None


class ZipBody(BaseModel):
    ids: List[str]
    name: str = "bundle.zip"
    project_id: Optional[str] = None


class ConvertBody(BaseModel):
    format: str


class AnalyzeBody(BaseModel):
    question: Optional[str] = Field(None, max_length=4000)


class FilePatch(BaseModel):
    project_id: Optional[str] = None
    archived: Optional[bool] = None


class ConversationBody(BaseModel):
    title: str = ""
    messages: List[Dict[str, Any]] = []
    project_id: Optional[str] = None


class ProjectBody(BaseModel):
    name: str
    description: str = ""
    instructions: str = ""
    links: List[str] = []


def make_router(verify: Callable[[str], bool]) -> APIRouter:
    r = APIRouter(prefix="/ws", tags=["workspace"])

    def owner(key: Optional[str]) -> None:
        if not key or not verify(key):
            raise HTTPException(status_code=401, detail="مفتاح المالك مطلوب (X-Sovereign-Key)")

    async def run(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except WorkspaceError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @r.get("/status")
    async def ws_status(x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().status())

    @r.post("/files")
    async def upload(file: UploadFile = File(...), project_id: Optional[str] = Form(None),
                     x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"الحد {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")
        return await run(lambda: get_workspace().add_file(file.filename or "file", data,
                                                          file.content_type or "", project_id=project_id or None))

    @r.get("/files")
    async def list_files(project_id: Optional[str] = None, kind: Optional[str] = None,
                         parent: Optional[str] = None, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return {"files": await run(lambda: get_workspace().list_files(project_id, kind, parent))}

    @r.get("/files/search")
    async def search(q: str, project_id: Optional[str] = None, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return {"q": q, "hits": await run(lambda: get_workspace().search(q, project_id))}

    @r.get("/files/{fid}")
    async def read(fid: str, offset: int = 0, limit: int = 20000,
                   x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().read(fid, max(0, offset), max(1, min(limit, 200000))))

    @r.get("/files/{fid}/raw")
    async def raw(fid: str, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        ws = get_workspace()
        rec = await run(lambda: ws.get_file(fid))
        data = await run(lambda: ws.raw(fid))
        return Response(content=data, media_type=rec.get("content_type") or "application/octet-stream",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(rec['name'])}"})

    @r.api_route("/files/{fid}", methods=["PATCH"])
    async def update_file(fid: str, body: FilePatch, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        ws = get_workspace()
        if body.archived is not None:
            await run(lambda: ws.set_archived(fid, body.archived))
        if "project_id" in body.model_fields_set:
            await run(lambda: ws.assign(fid, body.project_id))
        return await run(lambda: ws.get_file(fid))

    @r.post("/files/{fid}/analyze")
    async def analyze(fid: str, body: AnalyzeBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().analyze(fid, body.question))

    @r.post("/files/{fid}/unpack")
    async def unpack(fid: str, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().unpack(fid))

    @r.post("/files/{fid}/convert")
    async def convert(fid: str, body: ConvertBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().convert(fid, body.format))

    @r.post("/zip")
    async def make_zip(body: ZipBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().zip(body.ids, body.name, body.project_id))

    @r.post("/create")
    async def create(body: CreateBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().create(body.format, body.title, body.content,
                                                        body.table, body.data, body.project_id))

    @r.post("/image")
    async def image(body: ImageBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().generate_image(body.prompt, body.size, body.title,
                                                                body.project_id))

    @r.post("/video")
    async def video(body: VideoBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().make_video(body.slides, body.seconds, body.audio_id,
                                                            body.title, body.project_id))

    @r.get("/conversations")
    async def convs(project_id: Optional[str] = None, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return {"conversations": await run(lambda: get_workspace().list_conversations(project_id))}

    @r.post("/conversations")
    async def new_conv(body: ConversationBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().save_conversation(None, body.title, body.messages, body.project_id))

    @r.get("/conversations/{cid}")
    async def get_conv(cid: str, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().get_conversation(cid))

    @r.put("/conversations/{cid}")
    async def put_conv(cid: str, body: ConversationBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().save_conversation(cid, body.title, body.messages, body.project_id))

    @r.post("/conversations/{cid}/archive")
    async def arch_conv(cid: str, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().archive_conversation(cid))

    @r.get("/projects")
    async def projects(x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return {"projects": await run(lambda: get_workspace().list_projects())}

    @r.post("/projects")
    async def new_project(body: ProjectBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().save_project(None, body.name, body.description,
                                                              body.instructions, body.links))

    @r.get("/projects/{pid}")
    async def get_project(pid: str, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().get_project(pid))

    @r.put("/projects/{pid}")
    async def put_project(pid: str, body: ProjectBody, x_sovereign_key: Optional[str] = Header(None)):
        owner(x_sovereign_key)
        return await run(lambda: get_workspace().save_project(pid, body.name, body.description,
                                                              body.instructions, body.links))

    return r
